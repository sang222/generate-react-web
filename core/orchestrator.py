from __future__ import annotations

import json
import uuid
from pathlib import Path
from typing import Any, Dict, List

from agents.architect import run_architect
from agents.pm import run_pm
from core.adaptive_recovery import run_adaptive_recovery, should_trigger_adaptive_recovery
from core.config import get_system_target, load_module_config
from core.decision_service import decide_final_decision
from core.effective_target import derive_effective_target
from core.runtime_log import log_event
from core.executor import run_preflight_checks, run_system_check
from core.file_manager import summarize_project_tree, summarize_project_tree_for
from core.gates import fail_gate, load_gate_state, pass_gate, save_gate_state
from core.integration_service import integrate_and_validate_outputs
from core.memory import save_run
from core.ownership import detect_cross_lane_conflicts, ensure_ownership_map, ownership_map_path
from core.orchestrator_helpers.brownfield import prepare_existing_project_artifacts
from core.orchestrator_helpers.context import (
    append_history,
    build_workflow_context,
    log_step,
    make_empty_qa_detail,
    prepare_baseline,
    write_run_state,
    write_workflow_status,
)
from core.orchestrator_helpers.delivery import create_story_delivery
from core.orchestrator_helpers.lanes import (
    detect_needed_lanes,
    run_lane_developers_parallel,
    run_lead_and_store_summary,
)
from core.release_rules import classify_release_status
from core.review_service import review_merged_output
from core.retry_policy import append_retry_history, is_developer_self_retry_allowed, should_run_lead
from core.story_sizing import evaluate_story_size, format_story_split
from core.token_budget import TokenBudgetExceeded, set_token_context, sync_token_usage_to_context
from core.story_state import (
    default_story_packet,
    ensure_artifact_locks,
    ensure_delivery_index,
    ensure_epic_context,
    find_baseline_from_dependencies,
    get_story_definition,
)
from memory.manager import AgentMemoryManager

MODULE_CONFIG = load_module_config()
SYSTEM_TARGET = get_system_target(MODULE_CONFIG)
MAX_LOOP = int(MODULE_CONFIG.get("devteam", {}).get("max_retry_loops", 3))
OUTPUT_PROJECT_DIR = MODULE_CONFIG.get("devteam", {}).get("output_project_dir", "output_project")
STATE_DIR = Path(MODULE_CONFIG.get("devteam", {}).get("state_dir", "state"))
RUN_STATE_PATH = STATE_DIR / "run_state.json"
DELIVERIES_DIR = Path(MODULE_CONFIG.get("devteam", {}).get("deliveries_dir", "deliveries"))


def _base_context(
    *,
    task: str,
    project_id: str,
    epic_id: str,
    story_id: str,
    story_name: str,
    project_mode: str,
    baseline_path: str,
    depends_on: List[str],
    story_packet: Dict[str, Any],
    delivery_index: Dict[str, Any],
    ownership_path: str,
) -> Dict[str, Any]:
    return {
        "run_id": str(uuid.uuid4()),
        "project_id": project_id,
        "epic_id": epic_id,
        "story_id": story_id,
        "story_name": story_name,
        "delivery_mode": "story_based",
        "baseline_path": baseline_path,
        "baseline_tree": summarize_project_tree_for(baseline_path) if baseline_path else "",
        "story_goal": f"Deliver story {story_id} as a runnable baseline for project {project_id}.",
        "task": task,
        "project_mode": project_mode,
        "prd": "",
        "design": "",
        "code": {},
        "bugs": [],
        "fix_suggestion": "",
        "execution_error": "",
        "history": [],
        "loop_count": 0,
        "final_decision": "",
        "release_status": "",
        "severity": "",
        "qa_detail": make_empty_qa_detail(),
        "lead_summary": {},
        "project_tree": "",
        "retry_reason": "initial_generation",
        "operation": "plan",
        "run_state_path": str(RUN_STATE_PATH),
        "delivery_manifest": "",
        "delivery_source": "",
        "delivery_root": "",
        "resume_from": baseline_path,
        "depends_on": depends_on,
        "story_acceptance_criteria": story_packet.get("acceptance_criteria", []),
        "ownership_map_path": ownership_path,
        "artifact_locks_path": str(Path("project_state") / project_id / "artifact_locks.json"),
        "story_state_root": str(Path("project_state") / project_id / "stories" / story_id),
        "change_requests": [],
        "story_packet": story_packet,
        "fe_files": [],
        "be_files": [],
        "integration_conflicts": [],
        "integration_notes": [],
        "next_story": "",
        "delivery_index": delivery_index,
        "system_target": SYSTEM_TARGET,
        "adaptive_recovery_triggered": False,
        "adaptive_recovery_candidate_id": "",
        "adaptive_recovery_scope": "",
        "runtime_override_applied": False,
        "adaptive_recovery_block_reason": "",
        "skill_candidate_ids": [],
        "working_output_dir": OUTPUT_PROJECT_DIR,
        "effective_target": SYSTEM_TARGET,
        "execution_mode": story_packet.get("execution_mode", "auto"),
        "compact_fe_context": False,
    }


def _initialize_story_context(
    task: str,
    project_mode: str,
    project_id: str | None,
    epic_id: str | None,
    story_id: str | None,
    story_name: str | None,
    resume_from: str | None,
    depends_on: List[str] | None,
    execution_mode: str | None,
) -> tuple[Dict[str, Any], Dict[str, Any], Dict[str, Any], str]:
    story_id = (story_id or "story_1").strip() or "story_1"
    story_name = (story_name or story_id).strip() or story_id
    project_id = (project_id or f"project_{uuid.uuid4().hex[:8]}").strip()
    epic_id = (epic_id or f"{project_id}-epic").strip()
    depends_on = depends_on or []

    epic_context = ensure_epic_context(project_id, epic_id, story_id, story_name, depends_on)
    story_def = get_story_definition(project_id, story_id)
    delivery_index = ensure_delivery_index(project_id, epic_id, epic_context)
    ensure_artifact_locks(project_id)
    ownership_map = ensure_ownership_map(project_id)
    ownership_path = str(ownership_map_path(project_id))
    inferred_baseline = resume_from or find_baseline_from_dependencies(project_id, story_id, DELIVERIES_DIR)
    effective_project_mode = "existing_project" if inferred_baseline else project_mode

    story_packet = default_story_packet(
        project_id,
        epic_id,
        story_id,
        story_name,
        inferred_baseline or "",
        ownership_path,
        task,
        effective_project_mode,
        execution_mode or 'auto',
    )
    story_packet["depends_on"] = depends_on or story_packet.get("depends_on", [])
    story_packet["acceptance_criteria"] = story_def.get("acceptance_criteria", story_packet.get("acceptance_criteria", []))
    story_packet["in_scope"] = story_def.get("in_scope", story_packet.get("in_scope", []))
    story_packet["out_of_scope"] = story_def.get("out_of_scope", story_packet.get("out_of_scope", []))
    if story_packet.get("depends_on"):
        story_packet["baseline_story_id"] = story_packet["depends_on"][-1]

    context = _base_context(
        task=task,
        project_id=project_id,
        epic_id=epic_id,
        story_id=story_id,
        story_name=story_name,
        project_mode=effective_project_mode,
        baseline_path=inferred_baseline or "",
        depends_on=depends_on,
        story_packet=story_packet,
        delivery_index=delivery_index,
        ownership_path=ownership_path,
    )
    return context, story_packet, ownership_map, effective_project_mode


def _run_pm_phase(context: Dict[str, Any], memory_manager: AgentMemoryManager) -> None:
    log_event("PHASE", "planning", "START")
    pm_ctx = memory_manager.load_context("pm", context["task"], build_workflow_context(context, context.get("effective_target", SYSTEM_TARGET)))
    context["prd"] = run_pm(task=f"{context['task']}\n\nStory packet:\n{json.dumps(context['story_packet'], ensure_ascii=False, indent=2)}", agent_context=pm_ctx, story_packet=context["story_packet"])
    context["gate_state"] = pass_gate(context["gate_state"], "GATE_1_RESEARCH", "Research/brief context captured.", ["docs/brief.md"])
    context["gate_state"] = pass_gate(
        context["gate_state"],
        "GATE_2_SPECIFICATION",
        "Specification captured for current story.",
        ["docs/prd.md", f"project_state/{context['project_id']}/epic_context.json"],
    )
    save_gate_state(context["gate_state"])
    write_workflow_status(context, "Proceed to architecture for the current story.")
    log_event("GATE", "GATE_1_RESEARCH", "PASS")
    log_event("GATE", "GATE_2_SPECIFICATION", "PASS")
    log_event("PHASE", "planning", "DONE")


def _run_architecture_phase(context: Dict[str, Any], memory_manager: AgentMemoryManager, ownership_map: Dict[str, Any]) -> None:
    log_event("PHASE", "design", "START")
    architect_ctx = memory_manager.load_context("architect", context["task"], build_workflow_context(context, context.get("effective_target", SYSTEM_TARGET)))
    context["design"] = run_architect(
        task=f"{context['task']}\n\nCurrent story packet:\n{json.dumps(context['story_packet'], ensure_ascii=False, indent=2)}\n\nOwnership map:\n{json.dumps(ownership_map, ensure_ascii=False, indent=2)}",
        prd=context["prd"],
        agent_context=architect_ctx,
        story_packet=context["story_packet"],
    )
    if context["baseline_tree"]:
        context["design"] += f"\n\nBaseline project tree:\n{context['baseline_tree']}"
    context["gate_state"] = pass_gate(
        context["gate_state"],
        "GATE_3_DESIGN",
        "Architecture and ownership map prepared.",
        ["docs/architecture.md", context["ownership_map_path"]],
    )
    save_gate_state(context["gate_state"])
    log_event("GATE", "GATE_3_DESIGN", "PASS")
    log_event("PHASE", "design", "DONE")


def _handle_brownfield_readiness(context: Dict[str, Any], ownership_map: Dict[str, Any], memory_manager: AgentMemoryManager) -> Dict[str, Any] | None:
    log_event("PHASE", "brownfield_readiness", "START")
    if context["project_mode"] != "existing_project":
        context["gate_state"] = pass_gate(context["gate_state"], "BROWNFIELD_READINESS_GATE", "Skipped for new_project.", [])
        context["current_gate"] = "GATE_4_IMPLEMENTATION"
        save_gate_state(context["gate_state"])
        write_run_state(context, STATE_DIR, RUN_STATE_PATH, OUTPUT_PROJECT_DIR, context.get("effective_target", SYSTEM_TARGET))
        write_workflow_status(context, "Brownfield readiness skipped for new_project. Proceed to implementation.")
        log_event("GATE", "BROWNFIELD_READINESS_GATE", "SKIP", "Skipped for new_project")
        log_event("PHASE", "brownfield_readiness", "DONE")
        return None
    brownfield = prepare_existing_project_artifacts(context, ownership_map, SYSTEM_TARGET)
    context.update(brownfield)
    context["story_packet"].update(
        {
            "existing_system_summary_path": brownfield["existing_system_summary_path"],
            "change_impact_report_path": brownfield["change_impact_report_path"],
            "integration_strategy_path": brownfield["integration_strategy_path"],
            "readiness_report_path": brownfield["readiness_report_path"],
            "allowed_change_scope": brownfield["impact_report"].get("affected_modules", []),
            "forbidden_change_scope": brownfield["impact_report"].get("protected_modules", []),
            "regression_requirements": [
                "Do not break the delivered baseline.",
                "Do not modify protected modules without a change request.",
                "Do not regenerate the project from scratch.",
            ],
        }
    )
    if brownfield["readiness_report"].get("ready"):
        context["gate_state"] = pass_gate(
            context["gate_state"],
            "BROWNFIELD_READINESS_GATE",
            "Existing project is ready for safe implementation.",
            [
                brownfield["existing_system_summary_path"],
                brownfield["change_impact_report_path"],
                brownfield["integration_strategy_path"],
                brownfield["readiness_report_path"],
            ],
        )
        save_gate_state(context["gate_state"])
        write_workflow_status(context, "Proceed to implementation for the current story.")
        log_event("GATE", "BROWNFIELD_READINESS_GATE", "PASS")
        log_event("PHASE", "brownfield_readiness", "DONE")
        return None

    context["gate_state"] = fail_gate(context["gate_state"], "BROWNFIELD_READINESS_GATE", "Existing project readiness is incomplete.", reason_code="BROWNFIELD_READINESS_INCOMPLETE")
    save_gate_state(context["gate_state"])
    context["execution_error"] = "[brownfield readiness failed]\nMissing information: " + ", ".join(
        brownfield["readiness_report"].get("missing_information", [])
    )
    context["release_status"] = "BLOCKED"
    context["severity"] = "BLOCKER"
    context["final_decision"] = "BLOCKED"
    write_run_state(context, STATE_DIR, RUN_STATE_PATH, OUTPUT_PROJECT_DIR, context.get("effective_target", SYSTEM_TARGET))
    write_workflow_status(context, "Brownfield readiness must pass before implementation can start.")
    log_event("GATE", "BROWNFIELD_READINESS_GATE", "FAIL", reason="BROWNFIELD_READINESS_INCOMPLETE")
    save_run(context)
    memory_manager.remember_run(context)
    log_step(f"Finished with final decision: {context['final_decision']}")
    return context



def _handle_story_sizing_gate(context: Dict[str, Any], memory_manager: AgentMemoryManager) -> Dict[str, Any] | None:
    result = evaluate_story_size(
        task=context["task"],
        project_mode=context.get("project_mode", "new_project"),
        execution_mode=context.get("story_packet", {}).get("execution_mode", context.get("execution_mode", "auto")),
        story_packet=context.get("story_packet", {}),
    )
    context["story_sizing"] = result.to_dict()

    if not getattr(result, "should_block", False):
        event_status = getattr(result, "status", "PASS") or "PASS"
        log_event(
            "STORY_SIZE",
            "CHECK",
            event_status,
            reason=result.reason_code,
            estimated_files=result.estimated_files,
            estimated_sections=result.estimated_sections,
            estimated_apps=result.estimated_apps,
        )
        if event_status == "WARN":
            context.setdefault("runtime_warnings", []).append(format_story_split(result))
        return None

    message = format_story_split(result)
    context["execution_error"] = message
    context["retry_reason"] = result.reason_code
    context["release_status"] = "BLOCKED"
    context["severity"] = result.severity
    context["final_decision"] = "BLOCKED"
    context["fix_suggestion"] = "Split this request into smaller story-sized implementation tasks before running developer lanes."
    context["qa_detail"] = {
        "structural_bugs": [message],
        "functional_bugs": [],
        "prd_gaps": [],
        "ui_gaps": [],
        "regression_bugs": [],
    }
    context["bugs"] = context["qa_detail"]["structural_bugs"]
    context["gate_state"] = fail_gate(
        context["gate_state"],
        "STORY_SIZING_GATE",
        result.summary,
        reason_code=result.reason_code,
    )
    save_gate_state(context["gate_state"])
    write_run_state(context, STATE_DIR, RUN_STATE_PATH, OUTPUT_PROJECT_DIR, context.get("effective_target", SYSTEM_TARGET))
    write_workflow_status(context, message)
    log_event(
        "STORY_SIZE",
        "CHECK",
        "FAIL",
        reason=result.reason_code,
        estimated_files=result.estimated_files,
        estimated_sections=result.estimated_sections,
        estimated_apps=result.estimated_apps,
    )
    save_run(context)
    memory_manager.remember_run(context)
    return context


def _run_parallel_lanes(context: Dict[str, Any], memory_manager: AgentMemoryManager, ownership_map: Dict[str, Any]) -> None:
    active_lanes = detect_needed_lanes(context["story_packet"], context["task"])
    context["active_lanes"] = active_lanes
    context["story_packet"]["active_lanes"] = active_lanes
    context["effective_target"] = derive_effective_target(SYSTEM_TARGET, active_lanes)
    context["story_packet"]["system_target"] = context["effective_target"]
    context["compact_fe_context"] = (
        context.get("project_mode") == "new_project"
        and context.get("story_packet", {}).get("execution_mode") == "frontend_only"
        and int(context.get("story_packet", {}).get("project_level", 2) or 2) <= 2
    )
    log_event("PHASE", "implementation", "START", lanes=','.join(active_lanes), compact_fe_context=context.get("compact_fe_context"))
    try:
        results = run_lane_developers_parallel(context, memory_manager, ownership_map, context["effective_target"], MAX_LOOP)
        context["lane_results"] = results
    except Exception as exc:
        context["execution_error"] = f"lane runtime error: {exc}"
        context["retry_reason"] = "lane_runtime_error"
        context["release_status"] = "RETRY"
        context["severity"] = "BLOCKER"
        context["qa_detail"] = {"structural_bugs": [context["execution_error"]], "functional_bugs": [], "prd_gaps": [], "ui_gaps": [], "regression_bugs": []}
        write_run_state(context, STATE_DIR, RUN_STATE_PATH, OUTPUT_PROJECT_DIR, context.get("effective_target", SYSTEM_TARGET))
        write_workflow_status(context, f"Implementation lane failed safely: {context['execution_error']}")
        log_event("LANE", "implementation", "ERROR", error=str(exc))
        return
    context["fe_files"] = results.get("frontend", ([], {}))[0]
    context["be_files"] = results.get("backend", ([], {}))[0]
    log_event("PHASE", "implementation", "DONE", fe_files=len(context.get("fe_files", [])), be_files=len(context.get("be_files", [])))


def _handle_empty_lane_output(context: Dict[str, Any], memory_manager: AgentMemoryManager) -> bool:
    if context.get("execution_error") and context.get("retry_reason", "").endswith("_runtime_error"):
        append_history(context)
        return True
    if context.get("fe_files") or context.get("be_files"):
        return False

    active_lanes = context.get("active_lanes", []) or []
    lane_results = context.get("lane_results", {}) or {}
    details: list[str] = []
    debug_paths: list[str] = []

    for lane in active_lanes:
        files, result = lane_results.get(lane, ([], {}))
        role = result.get("__role", f"{lane}_developer") if isinstance(result, dict) else f"{lane}_developer"
        raw_chars = result.get("__raw_output_chars", 0) if isinstance(result, dict) else 0
        debug_path = result.get("__debug_output_path", "") if isinstance(result, dict) else ""
        if debug_path:
            debug_paths.append(debug_path)
        details.append(f"{lane}:{role}: files={len(files)} raw_output_chars={raw_chars}" + (f" debug={debug_path}" if debug_path else ""))

    if active_lanes == ["frontend"]:
        context["execution_error"] = (
            "Frontend developer returned output but no valid files could be extracted. "
            "Likely invalid/truncated project JSON or wrong output contract. "
            + " | ".join(details)
        )
        context["retry_reason"] = "invalid_project_json"
        context["fix_suggestion"] = (
            "Return ONLY valid JSON with a top-level files array. No markdown, no prose, no code fences. "
            "For frontend_only root Vite, include package.json, index.html, src/main.jsx, src/App.jsx, src/index.css. "
            "If the story is too large, reduce scope instead of returning truncated JSON."
        )
    elif active_lanes == ["backend"]:
        context["execution_error"] = (
            "Backend developer returned output but no valid files could be extracted. "
            "Likely invalid/truncated project JSON or wrong output contract. "
            + " | ".join(details)
        )
        context["retry_reason"] = "invalid_project_json"
        context["fix_suggestion"] = "Return ONLY valid JSON with a top-level files array for backend-owned files."
    else:
        context["execution_error"] = (
            "All active implementation lanes returned empty or invalid JSON. "
            + " | ".join(details)
        )
        context["retry_reason"] = "invalid_json_parallel"
        context["fix_suggestion"] = "Each active lane must return valid JSON with files scoped to its lane."

    context["qa_detail"] = {
        "structural_bugs": [context["execution_error"]],
        "functional_bugs": [],
        "prd_gaps": [],
        "ui_gaps": [],
        "regression_bugs": [],
    }
    context["bugs"] = context["qa_detail"]["structural_bugs"]
    context["release_status"], context["severity"], reason = classify_release_status(context)
    append_retry_history(context)
    if should_run_lead(context, MAX_LOOP):
        run_lead_and_store_summary(context, memory_manager, reason, MAX_LOOP, SYSTEM_TARGET)
    else:
        log_event(
            "RELEASE",
            "SKIP",
            "developer_self_retry",
            reason=context.get("retry_reason", ""),
            loop=context.get("loop_count"),
        )
    append_history(context)
    write_workflow_status(context, "Retry required for the current story: invalid developer output JSON.")
    return True

def _apply_integration_result(context: Dict[str, Any], integration_result: Dict[str, Any], memory_manager: AgentMemoryManager) -> bool:
    context["integration_conflicts"] = integration_result["integration_conflicts"]
    context["effective_target"] = integration_result.get("effective_target", derive_effective_target(SYSTEM_TARGET, context.get("active_lanes", [])))
    if integration_result["change_requests"]:
        context.setdefault("change_requests", []).extend(integration_result["change_requests"])

    context["code"] = {"files": integration_result["merged_files"]}

    if not integration_result["has_blocking_issue"]:
        return False

    context["execution_error"] = integration_result["execution_error"]
    context["retry_reason"] = integration_result["retry_reason"]
    if integration_result["qa_detail"]:
        context["qa_detail"] = integration_result["qa_detail"]
    context["fix_suggestion"] = integration_result["fix_suggestion"]
    context["bugs"] = integration_result["bugs"]
    context["release_status"], context["severity"], reason = classify_release_status(context)
    append_retry_history(context)
    if should_run_lead(context, MAX_LOOP):
        run_lead_and_store_summary(context, memory_manager, reason, MAX_LOOP, SYSTEM_TARGET)
    else:
        log_event(
            "RELEASE",
            "SKIP",
            "developer_self_retry",
            reason=context.get("retry_reason", ""),
            loop=context.get("loop_count"),
        )
    append_history(context)
    write_workflow_status(context, "Retry required for the current story.")
    return True


def _apply_review_result(context: Dict[str, Any], review_result: Dict[str, Any]) -> None:
    context["fe_review"] = review_result["fe_review"]
    context["be_review"] = review_result["be_review"]
    context["integration_review"] = review_result["integration_review"]
    context["qa_detail"] = review_result["qa_detail"]
    context["fix_suggestion"] = review_result["fix_suggestion"]
    context["bugs"] = review_result["bugs"]




def _apply_preflight_failure(context: Dict[str, Any], preflight_error: str) -> None:
    context["execution_error"] = preflight_error
    context["retry_reason"] = "preflight_failure"
    context["qa_detail"] = {
        "structural_bugs": [preflight_error],
        "functional_bugs": [],
        "prd_gaps": [],
        "ui_gaps": [],
        "regression_bugs": [],
    }
    context["fix_suggestion"] = "Fix deterministic file/import/package issues before running reviewer LLMs."
    context["bugs"] = context["qa_detail"]["structural_bugs"]


def _run_preflight_before_reviews(context: Dict[str, Any]) -> bool:
    log_event("PHASE", "preflight", "START")
    ok, message = run_preflight_checks(output_dir=OUTPUT_PROJECT_DIR, system_target=context.get("effective_target", SYSTEM_TARGET), active_lanes=context.get("active_lanes", []))
    if ok:
        log_event("PHASE", "preflight", "DONE")
        return False
    _apply_preflight_failure(context, message)
    write_workflow_status(context, "Retry required for the current story (deterministic preflight failed).")
    return True

def _finalize_loop(context: Dict[str, Any], memory_manager: AgentMemoryManager) -> bool:
    log_event("PHASE", "build_validation", "START")
    success, error_message = run_system_check(output_dir=OUTPUT_PROJECT_DIR, system_target=context.get("effective_target", SYSTEM_TARGET), active_lanes=context.get("active_lanes", []))
    if context["execution_error"]:
        success = False
    if not success and not context["execution_error"]:
        context["execution_error"] = error_message or "build failed"
    context["retry_reason"] = "" if success else (context.get("retry_reason") or "build_failure")
    context["release_status"], context["severity"], reason = classify_release_status(context)
    context["operation"] = "release"
    write_run_state(context, STATE_DIR, RUN_STATE_PATH, OUTPUT_PROJECT_DIR, context.get("effective_target", SYSTEM_TARGET))
    if context["release_status"] == "RETRY":
        append_retry_history(context)
    if should_run_lead(context, MAX_LOOP):
        run_lead_and_store_summary(context, memory_manager, reason, MAX_LOOP, SYSTEM_TARGET)
    else:
        log_event(
            "RELEASE",
            "SKIP",
            "developer_self_retry",
            reason=context.get("retry_reason", ""),
            loop=context.get("loop_count"),
        )
    append_history(context)
    log_event("PHASE", "build_validation", "DONE" if success else "ERROR", error=error_message or context.get("execution_error", ""))
    if context["release_status"] == "DONE":
        context["gate_state"] = pass_gate(context["gate_state"], "GATE_4_IMPLEMENTATION", "Implementation, reviews, and integration checks passed.", ["output_project"])
        context["gate_state"] = pass_gate(context["gate_state"], "RELEASE_GATE", "Release checklist approved for current story.", ["output_project"])
        save_gate_state(context["gate_state"])
        return True

    context["gate_state"] = fail_gate(context["gate_state"], "GATE_4_IMPLEMENTATION", context.get("execution_error", "") or "Implementation gate failed.", reason_code=context.get("retry_reason", "IMPLEMENTATION_FAILED"))
    save_gate_state(context["gate_state"])
    write_workflow_status(context, "Retry required for the current story.")
    return False


def _handle_token_budget_exceeded(context: Dict[str, Any], exc: TokenBudgetExceeded) -> Dict[str, Any]:
    context["execution_error"] = str(exc)
    context["release_status"] = "BLOCKED"
    context["severity"] = "BLOCKER"
    context["retry_reason"] = exc.reason_code
    context["adaptive_recovery_block_reason"] = exc.reason_code
    context["gate_state"] = fail_gate(
        context["gate_state"],
        "RECOVERY_GATE",
        str(exc),
        reason_code=exc.reason_code,
    )
    save_gate_state(context["gate_state"])
    write_workflow_status(context, "Blocked because token budget was exceeded.")
    sync_token_usage_to_context(context)
    return context


def _maybe_run_adaptive_recovery(context: Dict[str, Any]) -> bool:
    if not should_trigger_adaptive_recovery(context):
        return False
    recovery = run_adaptive_recovery(context)
    context["adaptive_recovery"] = recovery
    scope = recovery.get("apply_record", {}).get("apply_scope", "") if isinstance(recovery, dict) else ""
    blocked_reason = recovery.get("apply_record", {}).get("blocked_reason", "") if isinstance(recovery, dict) else ""
    write_workflow_status(context, f"Adaptive recovery generated candidate {recovery.get('candidate_id', '')} with scope {scope}.")
    if blocked_reason:
        context["release_status"] = "BLOCKED"
        context["severity"] = "BLOCKER"
        context["execution_error"] = context.get("execution_error") or blocked_reason
        context["gate_state"] = fail_gate(context["gate_state"], "RECOVERY_GATE", blocked_reason, reason_code=blocked_reason)
        save_gate_state(context["gate_state"])
        return True
    if int(context.get("loop_count", 0) or 0) >= MAX_LOOP:
        budget_reason = "BLOCKED_NO_RECOVERY_RERUN_BUDGET"
        context["release_status"] = "BLOCKED"
        context["severity"] = "BLOCKER"
        context["adaptive_recovery_block_reason"] = budget_reason
        context["execution_error"] = context.get("execution_error") or budget_reason
        context["gate_state"] = fail_gate(context["gate_state"], "RECOVERY_GATE", "Adaptive recovery had no rerun budget.", reason_code=budget_reason)
        save_gate_state(context["gate_state"])
        return True
    return False


def run_orchestrator(
    task: str,
    project_mode: str = "new_project",
    project_id: str | None = None,
    epic_id: str | None = None,
    story_id: str | None = None,
    story_name: str | None = None,
    resume_from: str | None = None,
    depends_on: List[str] | None = None,
    execution_mode: str | None = None,
) -> Dict[str, Any]:
    log_event("PHASE", "bootstrap", "START")
    memory_manager = AgentMemoryManager()
    memory_manager.ensure_bootstrap()

    context, _story_packet, ownership_map, _effective_mode = _initialize_story_context(
        task, project_mode, project_id, epic_id, story_id, story_name, resume_from, depends_on, execution_mode
    )
    initial_lanes = detect_needed_lanes(context["story_packet"], context["task"])
    context["active_lanes"] = initial_lanes
    context["story_packet"]["active_lanes"] = initial_lanes
    context["effective_target"] = derive_effective_target(SYSTEM_TARGET, initial_lanes)
    context["story_packet"]["system_target"] = context["effective_target"]
    set_token_context(context)

    context["first_breath"] = memory_manager.ensure_first_breath(task, build_workflow_context(context, context.get("effective_target", SYSTEM_TARGET)))
    context["gate_state"] = load_gate_state(context["project_id"], context["epic_id"], context["story_id"])
    write_run_state(context, STATE_DIR, RUN_STATE_PATH, OUTPUT_PROJECT_DIR, context.get("effective_target", SYSTEM_TARGET))
    log_event("PHASE", "bootstrap", "DONE")

    sizing_blocked = _handle_story_sizing_gate(context, memory_manager)
    if sizing_blocked is not None:
        return sizing_blocked

    try:
        _run_pm_phase(context, memory_manager)
        _run_architecture_phase(context, memory_manager, ownership_map)
    except TokenBudgetExceeded as exc:
        _handle_token_budget_exceeded(context, exc)
        context["final_decision"] = decide_final_decision(context)
        sync_token_usage_to_context(context)
        write_run_state(context, STATE_DIR, RUN_STATE_PATH, OUTPUT_PROJECT_DIR, context.get("effective_target", SYSTEM_TARGET))
        save_run(context)
        memory_manager.remember_run(context)
        return context

    blocked = _handle_brownfield_readiness(context, ownership_map, memory_manager)
    if blocked is not None:
        return blocked

    save_gate_state(context["gate_state"])
    write_workflow_status(context, "Proceed to implementation for the current story.")

    for loop in range(1, MAX_LOOP + 1):
        context["loop_count"] = loop
        context["story_packet"]["loop_count"] = loop
        context["execution_error"] = ""
        context["qa_detail"] = make_empty_qa_detail()
        context["operation"] = "generate"
        write_run_state(context, STATE_DIR, RUN_STATE_PATH, OUTPUT_PROJECT_DIR, context.get("effective_target", SYSTEM_TARGET))
        prepare_baseline(context)
        context["baseline_tree"] = summarize_project_tree_for(context["baseline_path"]) if context.get("baseline_path") else ""

        try:
            _run_parallel_lanes(context, memory_manager, ownership_map)
            if _handle_empty_lane_output(context, memory_manager):
                continue

            integration_result = integrate_and_validate_outputs(
                context=context,
                ownership_map=ownership_map,
                detect_cross_lane_conflicts=detect_cross_lane_conflicts,
                system_target=context.get("effective_target", SYSTEM_TARGET),
            )
            if _apply_integration_result(context, integration_result, memory_manager):
                continue

            if _run_preflight_before_reviews(context):
                context["release_status"], context["severity"], reason = classify_release_status(context)
                append_retry_history(context)
                log_event(
                    "AI_REVIEW",
                    "SKIP",
                    "developer_self_retry",
                    reason=context.get("retry_reason", ""),
                    loop=context.get("loop_count"),
                )
                append_history(context)
                continue

            review_result = review_merged_output(
                context=context,
                memory_manager=memory_manager,
                ownership_map=ownership_map,
                active_lanes=context["active_lanes"],
                merged_files=context["code"]["files"],
                system_target=context.get("effective_target", SYSTEM_TARGET),
            )
            _apply_review_result(context, review_result)

            if _finalize_loop(context, memory_manager):
                break
            if _maybe_run_adaptive_recovery(context):
                break
        except TokenBudgetExceeded as exc:
            _handle_token_budget_exceeded(context, exc)
            break
    context["project_tree"] = summarize_project_tree()
    if context["release_status"] == "DONE":
        delivery = create_story_delivery(context, DELIVERIES_DIR)
        context.update(delivery)
        write_workflow_status(context, "Current story delivered. Move to the next ready story if any.")
        context["next_story"] = context.get("lead_summary", {}).get("improvement", "")

    context["final_decision"] = decide_final_decision(context)

    sync_token_usage_to_context(context)
    write_run_state(context, STATE_DIR, RUN_STATE_PATH, OUTPUT_PROJECT_DIR, context.get("effective_target", SYSTEM_TARGET))
    save_run(context)
    memory_manager.remember_run(context)
    log_step(f"Finished with final decision: {context['final_decision']}")
    return context
