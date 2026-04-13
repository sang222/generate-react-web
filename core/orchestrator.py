from __future__ import annotations

import json
import uuid
from pathlib import Path
from typing import Any, Dict, List, Tuple

from agents.architect import run_architect
from agents.pm import run_pm
from core.change_request import create_change_request
from core.config import get_system_target, load_module_config
from core.executor import run_system_check
from core.file_manager import (
    OUTPUT_DIR,
    summarize_project_tree,
    summarize_project_tree_for,
    write_project,
)
from core.gates import fail_gate, load_gate_state, pass_gate, save_gate_state
from core.memory import save_run
from core.ownership import detect_cross_lane_conflicts, ensure_ownership_map, ownership_map_path
from core.story_state import (
    default_story_packet,
    ensure_artifact_locks,
    ensure_delivery_index,
    ensure_epic_context,
    find_baseline_from_dependencies,
    get_story_definition,
)
from core.utils.json_utils import dedupe_files
from core.orchestrator_helpers.brownfield import prepare_existing_project_artifacts
from core.orchestrator_helpers.context import (
    append_history,
    build_workflow_context,
    log_step,
    make_empty_qa_detail,
    merge_qa_details,
    prepare_baseline,
    write_run_state,
    write_workflow_status,
)
from core.orchestrator_helpers.delivery import (
    create_story_delivery,
    find_missing_required_files_in_output,
)
from core.orchestrator_helpers.lanes import (
    build_lane_code,
    detect_needed_lanes,
    run_lane_developer,
    run_lane_review,
    run_lead_and_store_summary,
)
from memory.manager import AgentMemoryManager

MODULE_CONFIG = load_module_config()
SYSTEM_TARGET = get_system_target(MODULE_CONFIG)
MAX_LOOP = int(MODULE_CONFIG.get("devteam", {}).get("max_retry_loops", 3))
OUTPUT_PROJECT_DIR = MODULE_CONFIG.get("devteam", {}).get("output_project_dir", "output_project")
STATE_DIR = Path(MODULE_CONFIG.get("devteam", {}).get("state_dir", "state"))
RUN_STATE_PATH = STATE_DIR / "run_state.json"
DELIVERIES_DIR = Path(MODULE_CONFIG.get("devteam", {}).get("deliveries_dir", "deliveries"))


def classify_release_status(context: Dict[str, Any]) -> Tuple[str, str, str]:
    execution_error = (context.get("execution_error") or "").strip()
    qa_detail = context.get("qa_detail") or {}
    structural_bugs = qa_detail.get("structural_bugs") or []
    functional_bugs = qa_detail.get("functional_bugs") or []
    prd_gaps = qa_detail.get("prd_gaps") or []
    regression_bugs = qa_detail.get("regression_bugs") or []
    ui_gaps = qa_detail.get("ui_gaps") or []

    if execution_error or structural_bugs or functional_bugs or prd_gaps or regression_bugs:
        return ("RETRY", "BLOCKER", "Build failed, ownership/integration failed, or story acceptance criteria are incomplete.")
    if ui_gaps:
        return ("DONE", "MINOR", "Build and current story requirements passed, with only minor UI gaps remaining.")
    return ("DONE", "NONE", "Build passed and no important QA gaps remain for the current story.")


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
        "artifact_locks_path": str(Path('project_state') / project_id / 'artifact_locks.json'),
        "change_requests": [],
        "story_packet": story_packet,
        "fe_files": [],
        "be_files": [],
        "integration_conflicts": [],
        "integration_notes": [],
        "next_story": "",
        "delivery_index": delivery_index,
        "system_target": SYSTEM_TARGET,
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
    pm_ctx = memory_manager.load_context("pm", context["task"], build_workflow_context(context, SYSTEM_TARGET))
    context["prd"] = run_pm(task=f"{context['task']}\n\nStory packet:\n{json.dumps(context['story_packet'], ensure_ascii=False, indent=2)}", agent_context=pm_ctx)
    context['gate_state'] = pass_gate(context['gate_state'], 'GATE_1_RESEARCH', 'Research/brief context captured.', ['docs/brief.md'])
    context['gate_state'] = pass_gate(
        context['gate_state'],
        'GATE_2_SPECIFICATION',
        'Specification captured for current story.',
        [f'docs/prd.md', f'project_state/{context["project_id"]}/epic_context.json'],
    )
    save_gate_state(context['gate_state'])
    write_workflow_status(context, 'Proceed to architecture for the current story.')


def _run_architecture_phase(context: Dict[str, Any], memory_manager: AgentMemoryManager, ownership_map: Dict[str, Any]) -> None:
    architect_ctx = memory_manager.load_context("architect", context["task"], build_workflow_context(context, SYSTEM_TARGET))
    context["design"] = run_architect(
        task=f"{context['task']}\n\nCurrent story packet:\n{json.dumps(context['story_packet'], ensure_ascii=False, indent=2)}\n\nOwnership map:\n{json.dumps(ownership_map, ensure_ascii=False, indent=2)}",
        prd=context["prd"],
        agent_context=architect_ctx,
        story_packet=context["story_packet"],
    )
    if context["baseline_tree"]:
        context["design"] += f"\n\nBaseline project tree:\n{context['baseline_tree']}"
    context['gate_state'] = pass_gate(context['gate_state'], 'GATE_3_DESIGN', 'Architecture and ownership map prepared.', ['docs/architecture.md', context['ownership_map_path']])
    save_gate_state(context['gate_state'])


def _handle_brownfield_readiness(context: Dict[str, Any], ownership_map: Dict[str, Any], memory_manager: AgentMemoryManager) -> Dict[str, Any] | None:
    if context['project_mode'] != 'existing_project':
        return None
    brownfield = prepare_existing_project_artifacts(context, ownership_map, SYSTEM_TARGET)
    context.update(brownfield)
    context['story_packet'].update({
        'existing_system_summary_path': brownfield['existing_system_summary_path'],
        'change_impact_report_path': brownfield['change_impact_report_path'],
        'integration_strategy_path': brownfield['integration_strategy_path'],
        'readiness_report_path': brownfield['readiness_report_path'],
        'allowed_change_scope': brownfield['impact_report'].get('affected_modules', []),
        'forbidden_change_scope': brownfield['impact_report'].get('protected_modules', []),
        'regression_requirements': [
            'Do not break the delivered baseline behavior.',
            'Do not rewrite protected/shared modules without a change request.',
            'Do not regenerate the baseline project from scratch.',
        ],
        'implementation_constraints': [
            'Patch existing modules in place.',
            'Prefer additive changes.',
            'Reuse current route and service contracts when possible.',
        ],
    })
    ready = bool(brownfield['readiness_report'].get('ready'))
    if ready:
        context['gate_state'] = pass_gate(
            context['gate_state'],
            'BROWNFIELD_READINESS_GATE',
            'Existing project summary, impact report, strategy, and readiness report are ready.',
            [
                brownfield['existing_system_summary_path'],
                brownfield['change_impact_report_path'],
                brownfield['integration_strategy_path'],
                brownfield['readiness_report_path'],
            ],
        )
        from core.story_state import lock_artifacts
        lock_artifacts(context['project_id'], context['story_id'], 'BROWNFIELD_READINESS_GATE', [
            brownfield['existing_system_summary_path'],
            brownfield['change_impact_report_path'],
            brownfield['integration_strategy_path'],
            brownfield['readiness_report_path'],
        ])
        save_gate_state(context['gate_state'])
        write_workflow_status(context, 'Proceed to implementation for the current story.')
        return None

    context['gate_state'] = fail_gate(context['gate_state'], 'BROWNFIELD_READINESS_GATE', 'Existing project readiness is incomplete.')
    save_gate_state(context['gate_state'])
    context['execution_error'] = '[brownfield readiness failed]\nMissing information: ' + ', '.join(brownfield['readiness_report'].get('missing_information', []))
    context['release_status'] = 'BLOCKED'
    context['severity'] = 'BLOCKER'
    context['final_decision'] = 'BLOCKED'
    write_run_state(context, STATE_DIR, RUN_STATE_PATH, OUTPUT_PROJECT_DIR, SYSTEM_TARGET)
    write_workflow_status(context, 'Brownfield readiness must pass before implementation can start.')
    save_run(context)
    memory_manager.remember_run(context)
    log_step(f"Finished with final decision: {context['final_decision']}")
    return context


def _run_parallel_lanes(context: Dict[str, Any], memory_manager: AgentMemoryManager, ownership_map: Dict[str, Any]) -> None:
    active_lanes = detect_needed_lanes(context["story_packet"], context["task"])
    fe_files: List[Dict[str, str]] = []
    be_files: List[Dict[str, str]] = []
    if "backend" in active_lanes:
        be_files, _ = run_lane_developer(context, memory_manager, "backend", "be_developer", ownership_map, SYSTEM_TARGET, MAX_LOOP)
    if "frontend" in active_lanes:
        fe_files, _ = run_lane_developer(context, memory_manager, "frontend", "fe_developer", ownership_map, SYSTEM_TARGET, MAX_LOOP)
    context["active_lanes"] = active_lanes
    context["fe_files"] = fe_files
    context["be_files"] = be_files


def _handle_empty_lane_output(context: Dict[str, Any], memory_manager: AgentMemoryManager) -> bool:
    if context.get("fe_files") or context.get("be_files"):
        return False
    context["execution_error"] = "Both FE and BE developers returned empty or invalid JSON"
    context["retry_reason"] = "invalid_json_parallel"
    context["qa_detail"] = {
        "structural_bugs": [context["execution_error"]],
        "functional_bugs": [],
        "prd_gaps": [],
        "ui_gaps": [],
        "regression_bugs": [],
    }
    context["fix_suggestion"] = "At least one implementation lane must return valid JSON with files."
    context["bugs"] = context["qa_detail"]["structural_bugs"]
    context["release_status"], context["severity"], reason = classify_release_status(context)
    run_lead_and_store_summary(context, memory_manager, reason, MAX_LOOP, SYSTEM_TARGET)
    append_history(context)
    write_workflow_status(context, "Retry required for the current story.")
    return True


def _merge_and_check_outputs(context: Dict[str, Any], ownership_map: Dict[str, Any], memory_manager: AgentMemoryManager) -> bool:
    active = set(context.get("active_lanes", []))
    conflicts = detect_cross_lane_conflicts(context["fe_files"], context["be_files"], ownership_map) if active == {"frontend", "backend"} else []
    context["integration_conflicts"] = conflicts
    if conflicts:
        context["execution_error"] = "[integration conflict]\n" + "\n".join(conflicts)
        context["retry_reason"] = "ownership_conflict"
        cr_path = create_change_request(context['project_id'], context['story_id'], context['ownership_map_path'], 'Cross-lane ownership conflict detected during integration.', conflicts)
        context.setdefault('change_requests', []).append(cr_path)

    merged_files = dedupe_files(context["be_files"] + context["fe_files"])
    context["code"] = {"files": merged_files}
    write_project(merged_files)

    missing_required_files = find_missing_required_files_in_output(SYSTEM_TARGET)
    if not missing_required_files:
        return False

    context["execution_error"] = "Missing required files after applying this story: " + ", ".join(missing_required_files)
    context["retry_reason"] = "missing_required_files"
    context["qa_detail"] = {
        "structural_bugs": [f"Missing required file: {path}" for path in missing_required_files],
        "functional_bugs": [],
        "prd_gaps": [],
        "ui_gaps": [],
        "regression_bugs": [],
    }
    context["fix_suggestion"] = "Generate or preserve the minimum required file set before adding extra features."
    context["bugs"] = context["qa_detail"]["structural_bugs"]
    context["release_status"], context["severity"], reason = classify_release_status(context)
    run_lead_and_store_summary(context, memory_manager, reason, MAX_LOOP, SYSTEM_TARGET)
    append_history(context)
    write_workflow_status(context, "Retry required for the current story.")
    return True


def _run_reviews(context: Dict[str, Any], memory_manager: AgentMemoryManager, ownership_map: Dict[str, Any]) -> None:
    empty_review = make_empty_qa_detail() | {"fix_suggestion": ""}
    merged_files = context["code"]["files"]
    fe_review = run_lane_review(context, memory_manager, "frontend", "fe_reviewer", build_lane_code(merged_files, 'frontend', ownership_map), SYSTEM_TARGET) if "frontend" in context.get("active_lanes", []) else empty_review
    be_review = run_lane_review(context, memory_manager, "backend", "be_reviewer", build_lane_code(merged_files, 'backend', ownership_map), SYSTEM_TARGET) if "backend" in context.get("active_lanes", []) else empty_review
    integration_review = run_lane_review(context, memory_manager, "integration", "integration_qa", context["code"], SYSTEM_TARGET) if len(context.get("active_lanes", [])) > 1 else empty_review
    context["fe_review"] = fe_review
    context["be_review"] = be_review
    context["integration_review"] = integration_review
    context["qa_detail"] = merge_qa_details(fe_review, be_review, integration_review)
    for conflict in context.get("integration_conflicts", []):
        if conflict not in context["qa_detail"]["structural_bugs"]:
            context["qa_detail"]["structural_bugs"].append(conflict)
    context["fix_suggestion"] = " ".join(filter(None, [
        fe_review.get("fix_suggestion", ""),
        be_review.get("fix_suggestion", ""),
        integration_review.get("fix_suggestion", ""),
    ])).strip()
    context["bugs"] = [
        *context["qa_detail"]["structural_bugs"],
        *context["qa_detail"]["functional_bugs"],
        *context["qa_detail"]["prd_gaps"],
        *context["qa_detail"]["regression_bugs"],
    ]


def _finalize_loop(context: Dict[str, Any], memory_manager: AgentMemoryManager) -> bool:
    success, error_message = run_system_check(system_target=SYSTEM_TARGET)
    if context["execution_error"]:
        success = False
    if not success and not context["execution_error"]:
        context["execution_error"] = error_message or "build failed"
    context["retry_reason"] = "" if success else (context.get("retry_reason") or "build_failure")
    context["release_status"], context["severity"], reason = classify_release_status(context)
    context["operation"] = "release"
    write_run_state(context, STATE_DIR, RUN_STATE_PATH, OUTPUT_PROJECT_DIR, SYSTEM_TARGET)
    run_lead_and_store_summary(context, memory_manager, reason, MAX_LOOP, SYSTEM_TARGET)
    append_history(context)
    if context["release_status"] == "DONE":
        context['gate_state'] = pass_gate(context['gate_state'], 'GATE_4_IMPLEMENTATION', 'Implementation, reviews, and integration checks passed.', ['output_project'])
        context['gate_state'] = pass_gate(context['gate_state'], 'RELEASE_GATE', 'Release checklist approved for current story.', ['output_project'])
        save_gate_state(context['gate_state'])
        return True

    context['gate_state'] = fail_gate(context['gate_state'], 'GATE_4_IMPLEMENTATION', context.get('execution_error', '') or 'Implementation gate failed.')
    save_gate_state(context['gate_state'])
    write_workflow_status(context, "Retry required for the current story.")
    return False


def run_orchestrator(task: str, project_mode: str = "new_project", project_id: str | None = None, epic_id: str | None = None, story_id: str | None = None, story_name: str | None = None, resume_from: str | None = None, depends_on: List[str] | None = None) -> Dict[str, Any]:
    memory_manager = AgentMemoryManager()
    memory_manager.ensure_bootstrap()

    context, _story_packet, ownership_map, _effective_mode = _initialize_story_context(
        task, project_mode, project_id, epic_id, story_id, story_name, resume_from, depends_on
    )

    context["first_breath"] = memory_manager.ensure_first_breath(task, build_workflow_context(context, SYSTEM_TARGET))
    context['gate_state'] = load_gate_state(context["project_id"], context["epic_id"], context["story_id"])
    write_run_state(context, STATE_DIR, RUN_STATE_PATH, OUTPUT_PROJECT_DIR, SYSTEM_TARGET)

    _run_pm_phase(context, memory_manager)
    _run_architecture_phase(context, memory_manager, ownership_map)

    blocked = _handle_brownfield_readiness(context, ownership_map, memory_manager)
    if blocked is not None:
        return blocked

    save_gate_state(context['gate_state'])
    write_workflow_status(context, 'Proceed to implementation for the current story.')

    for loop in range(1, MAX_LOOP + 1):
        context["loop_count"] = loop
        context["execution_error"] = ""
        context["qa_detail"] = make_empty_qa_detail()
        context["operation"] = "generate"
        write_run_state(context, STATE_DIR, RUN_STATE_PATH, OUTPUT_PROJECT_DIR, SYSTEM_TARGET)
        prepare_baseline(context)
        if context.get("baseline_path"):
            context["baseline_tree"] = summarize_project_tree_for(context["baseline_path"])
        else:
            context["baseline_tree"] = ""

        _run_parallel_lanes(context, memory_manager, ownership_map)
        if _handle_empty_lane_output(context, memory_manager):
            continue
        if _merge_and_check_outputs(context, ownership_map, memory_manager):
            continue
        _run_reviews(context, memory_manager, ownership_map)
        if _finalize_loop(context, memory_manager):
            break

    context["project_tree"] = summarize_project_tree()
    if context["release_status"] == "DONE":
        delivery = create_story_delivery(context, DELIVERIES_DIR)
        context.update(delivery)
        write_workflow_status(context, "Current story delivered. Move to the next ready story if any.")
        context["next_story"] = context.get("lead_summary", {}).get("improvement", "")
        context["final_decision"] = "DELIVER_STORY"
    else:
        context["final_decision"] = context["release_status"]

    write_run_state(context, STATE_DIR, RUN_STATE_PATH, OUTPUT_PROJECT_DIR, SYSTEM_TARGET)
    save_run(context)
    memory_manager.remember_run(context)
    log_step(f"Finished with final decision: {context['final_decision']}")
    return context
