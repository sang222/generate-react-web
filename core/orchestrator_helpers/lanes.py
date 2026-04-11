from __future__ import annotations

import json
from typing import Any, Dict, List

from agents.developer import run_developer
from agents.lead import run_lead
from agents.qa import run_qa
from memory.manager import AgentMemoryManager

from core.ownership import lane_files
from core.utils.json_utils import extract_json_object, normalize_files
from .context import build_planned_changes, build_workflow_context, log_step


def detect_needed_lanes(story_packet: Dict[str, Any], task: str) -> List[str]:
    packet_text = (task + "\n" + json.dumps(story_packet, ensure_ascii=False)).lower()
    level = int(story_packet.get("project_level", 2) or 2)
    backend_markers = ["backend", "api", "spring", "controller", "repository", "database", "postgres", "jpa", "auth", "service"]
    needs_backend = any(marker in packet_text for marker in backend_markers)
    if level <= 1 and not needs_backend:
        return ["frontend"]
    if needs_backend or story_packet.get("system_target", {}).get("system_type") == "fullstack_website":
        return ["frontend", "backend"]
    return ["frontend"]


def run_lead_and_store_summary(context: Dict[str, Any], memory_manager: AgentMemoryManager, rule_reason: str, max_loop: int, system_target: Dict[str, Any]) -> None:
    log_step(f"Loop {context['loop_count']}/{max_loop} - Running Lead (status={context['release_status']}, severity={context['severity']})")
    lead_ctx = memory_manager.load_context("lead", task=context["task"], workflow_context=build_workflow_context(context, system_target))
    lead_raw = run_lead(
        task=context["task"],
        prd=context["prd"],
        design=context["design"],
        code=context["code"],
        qa_detail=context["qa_detail"],
        execution_error=context["execution_error"],
        loop_count=context["loop_count"],
        max_loop=max_loop,
        rule_result={"release_status": context["release_status"], "severity": context["severity"], "reason": rule_reason},
        history=context["history"],
        agent_context=lead_ctx,
        story_packet=context.get("story_packet", {}),
    )
    context["lead_summary"] = extract_json_object(lead_raw)


def run_lane_developer(context: Dict[str, Any], memory_manager: AgentMemoryManager, lane: str, role: str, ownership_map: Dict[str, Any], system_target: Dict[str, Any], max_loop: int) -> tuple[list[dict], dict]:
    dev_ctx = memory_manager.load_context(role, context["task"], build_workflow_context(context, system_target))
    log_step(f"Loop {context['loop_count']}/{max_loop} - Running {role}")
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
    )
    result = extract_json_object(raw)
    return normalize_files(result), result


def run_lane_review(context: Dict[str, Any], memory_manager: AgentMemoryManager, lane: str, role: str, code: dict, system_target: Dict[str, Any]) -> dict:
    qa_ctx = memory_manager.load_context(role, context["task"], build_workflow_context(context, system_target))
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
