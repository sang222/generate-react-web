from __future__ import annotations

import json
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Any, Dict, List

from agents.developer import run_developer
from agents.lead import run_lead
from agents.qa import run_qa
from memory.manager import AgentMemoryManager

from core.ownership import lane_files
from core.utils.json_utils import extract_json_object, normalize_files
from .context import build_planned_changes, build_workflow_context, log_step
from core.runtime_log import log_event
from core.debug_outputs import persist_bad_llm_output
from core.effective_target import derive_effective_target
from core.orchestrator_helpers.delivery import normalize_files_for_target


from core.lane_detection import detect_needed_lanes

def run_lead_and_store_summary(
    context: Dict[str, Any],
    memory_manager: AgentMemoryManager,
    rule_reason: str,
    max_loop: int,
    system_target: Dict[str, Any],
) -> None:
    if context.get("retry_reason") == "missing_required_files":
        execution_error = context.get("execution_error", "") or (
            "Missing required files after applying this story."
        )

        fix_suggestion = context.get("fix_suggestion", "") or (
            "Regenerate the implementation using the active runtime file contract. "
            "For frontend_only new_project, generate a root Vite app with: "
            "package.json, index.html, src/main.jsx, src/App.jsx, src/index.css."
        )

        context["lead_summary"] = {
            "decision": "RETRY",
            "release_status": "RETRY",
            "severity": "BLOCKER",
            "reason": execution_error,
            "fix_suggestion": fix_suggestion,
            "deterministic": True,
            "retry_reason": "missing_required_files",
        }

        context["release_status"] = "RETRY"
        context["severity"] = "BLOCKER"
        context["execution_error"] = execution_error
        context["fix_suggestion"] = fix_suggestion

        log_event(
            "RELEASE",
            "DECISION",
            "RETRY",
            severity="BLOCKER",
            reason="missing_required_files",
            deterministic=True,
        )

        return

    log_step(
        f"Loop {context['loop_count']}/{max_loop} - Running Lead "
        f"(status={context['release_status']}, severity={context['severity']})"
    )

    lead_ctx = memory_manager.load_context(
        "lead",
        task=context["task"],
        workflow_context=build_workflow_context(context, system_target),
    )

    lead_raw = run_lead(
        task=context["task"],
        prd=context["prd"],
        design=context["design"],
        code=context["code"],
        qa_detail=context["qa_detail"],
        execution_error=context["execution_error"],
        loop_count=context["loop_count"],
        max_loop=max_loop,
        rule_result={
            "release_status": context["release_status"],
            "severity": context["severity"],
            "reason": rule_reason,
        },
        history=context["history"],
        agent_context=lead_ctx,
        story_packet=context.get("story_packet", {}),
    )

    context["lead_summary"] = extract_json_object(lead_raw)

def run_lane_developer(context: Dict[str, Any], memory_manager: AgentMemoryManager, lane: str, role: str, ownership_map: Dict[str, Any], system_target: Dict[str, Any], max_loop: int) -> tuple[list[dict], dict]:
    effective_target = context.get("effective_target") or derive_effective_target(system_target, context.get("active_lanes", []))
    dev_ctx = memory_manager.load_context(role, context["task"], build_workflow_context(context, effective_target))
    log_step(f"Loop {context['loop_count']}/{max_loop} - Running {role}")
    log_event("LANE", lane, "START", role=role, loop=context.get("loop_count", 0))
    task = context["task"]
    if context.get("baseline_tree"):
        task += f"\n\nExisting baseline tree:\n{context['baseline_tree']}"
    raw = run_developer(
        task=task,
        prd=context["prd"],
        design=context["design"],
        bugs=context["bugs"],
        fix_suggestion=context["fix_suggestion"],
        execution_error=context["execution_error"],
        history=context["history"],
        planned_changes=build_planned_changes(context, lane),
        agent_context=dev_ctx,
        project_mode=context["project_mode"],
        role=role,
        lane=lane,
        ownership_map=ownership_map,
        story_packet=context["story_packet"],
        system_target=effective_target,
        compact_context=bool(context.get("compact_fe_context") and lane == "frontend"),
    )
    result = extract_json_object(raw)
    files = normalize_files(result)
    files = normalize_files_for_target(files, effective_target)

    result["__lane"] = lane
    result["__role"] = role
    result["__raw_output_chars"] = len(raw or "")
    result["__parsed_files"] = len(files)
    result["__parsed_paths"] = [item.get("path", "") for item in files[:12]]

    if raw and not files:
        debug_path = persist_bad_llm_output(
            context=context,
            role=role,
            raw_output=raw,
            reason="no_files_extracted",
        )
        result["__debug_output_path"] = debug_path
        log_event(
            "VALIDATION",
            lane,
            "FAIL",
            reason="invalid_project_json",
            role=role,
            output_chars=len(raw),
            debug_output=debug_path,
        )
    else:
        log_event(
            "LANE",
            lane,
            "PARSE",
            role=role,
            parsed_files=len(files),
            paths=",".join(result["__parsed_paths"][:8]),
        )

    log_event("LANE", lane, "DONE", role=role, files=len(files))
    return files, result

def run_lane_developers_parallel(context: Dict[str, Any], memory_manager: AgentMemoryManager, ownership_map: Dict[str, Any], system_target: Dict[str, Any], max_loop: int) -> Dict[str, tuple[list[dict], dict]]:
    active_lanes = detect_needed_lanes(context["story_packet"], context["task"])
    lane_specs = []
    if "frontend" in active_lanes:
        lane_specs.append(("frontend", "fe_developer"))
    if "backend" in active_lanes:
        lane_specs.append(("backend", "be_developer"))

    if len(lane_specs) <= 1:
        results: Dict[str, tuple[list[dict], dict]] = {}
        for lane, role in lane_specs:
            results[lane] = run_lane_developer(context, memory_manager, lane, role, ownership_map, system_target, max_loop)
        return results

    results: Dict[str, tuple[list[dict], dict]] = {}
    with ThreadPoolExecutor(max_workers=len(lane_specs)) as executor:
        future_map = {
            executor.submit(run_lane_developer, context, memory_manager, lane, role, ownership_map, system_target, max_loop): lane
            for lane, role in lane_specs
        }
        for future in as_completed(future_map):
            lane = future_map[future]
            try:
                results[lane] = future.result()
            except Exception as exc:
                log_event("LANE", lane, "ERROR", error=str(exc))
                raise
    return results


def run_lane_review(context: Dict[str, Any], memory_manager: AgentMemoryManager, lane: str, role: str, code: dict, system_target: Dict[str, Any]) -> dict:
    qa_ctx = memory_manager.load_context(role, context["task"], build_workflow_context(context, system_target))
    log_event("LLM", role, "START", phase="lane_review", lane=lane)
    raw = run_qa(
        task=context["task"],
        prd=context["prd"],
        design=context["design"],
        code=code,
        extra_bugs=[],
        agent_context=qa_ctx,
        role=role,
        lane=lane,
        story_packet=context["story_packet"],
    )
    res = extract_json_object(raw)
    log_event("LLM", role, "DONE", phase="lane_review", lane=lane)
    return {
        "structural_bugs": res.get("structural_bugs", []) or [],
        "functional_bugs": res.get("functional_bugs", []) or [],
        "prd_gaps": res.get("prd_gaps", []) or [],
        "ui_gaps": res.get("ui_gaps", []) or [],
        "regression_bugs": res.get("regression_bugs", []) or [],
        "fix_suggestion": res.get("fix_suggestion", "") or "",
    }


def build_lane_code(files: list[dict], lane: str, ownership_map: dict) -> dict:
    return {"files": lane_files(files, lane, ownership_map)}
