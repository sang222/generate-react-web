from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List

from core.file_manager import load_baseline_project, reset_output_dir


def log_step(message: str) -> None:
    now = datetime.now().strftime("%H:%M:%S")
    print(f"[{now}] [orchestrator] {message}", flush=True)


def workflow_status_path(project_id: str) -> Path:
    return Path("project_state") / project_id / "workflow_status.yaml"


def write_workflow_status(context: Dict[str, Any], recommendation: str = "") -> None:
    path = workflow_status_path(context['project_id'])
    path.parent.mkdir(parents=True, exist_ok=True)
    current = {}
    if isinstance(context.get('delivery_index'), dict):
        current = context.get('delivery_index', {}).get('current_delivered_story', {}) or {}
    gate_state = context.get('gate_state', {}) or {}
    lines = [
        f"project_id: {context.get('project_id','')}",
        f"epic_id: {context.get('epic_id','')}",
        f"story_id: {context.get('story_id','')}",
        f"story_name: {json.dumps(context.get('story_name',''), ensure_ascii=False)}",
        f"project_mode: {context.get('project_mode','')}",
        f"project_level: {context.get('story_packet',{}).get('project_level','')}",
        f"delivery_profile: {context.get('story_packet',{}).get('delivery_profile','')}",
        f"current_gate: {gate_state.get('current_gate','')}",
        f"final_decision: {context.get('final_decision','')}",
        f"release_status: {context.get('release_status','')}",
        f"current_delivered_story_id: {current.get('story_id','')}",
        f"current_delivered_story_name: {json.dumps(current.get('story_name',''), ensure_ascii=False)}",
        f"next_story: {context.get('next_story','')}",
        f"recommendation: {json.dumps(recommendation, ensure_ascii=False)}",
        f"readiness_report_path: {context.get('readiness_report_path','')}",
    ]
    path.write_text("\n".join(lines) + "\n", encoding='utf-8')


def make_empty_qa_detail() -> Dict[str, List[str]]:
    return {
        "structural_bugs": [],
        "functional_bugs": [],
        "prd_gaps": [],
        "ui_gaps": [],
        "regression_bugs": [],
    }


def merge_qa_details(*details: Dict[str, List[str]]) -> Dict[str, List[str]]:
    result = make_empty_qa_detail()
    for detail in details:
        for key in result.keys():
            for item in detail.get(key, []) or []:
                if item not in result[key]:
                    result[key].append(item)
    return result


def append_history(context: Dict[str, Any]) -> None:
    context["history"].append(
        {
            "loop": context.get("loop_count", 0),
            "epic_id": context.get("epic_id", ""),
            "story_id": context.get("story_id", "story_1"),
            "story_name": context.get("story_name", context.get("story_id", "story_1")),
            "release_status": context.get("release_status", ""),
            "severity": context.get("severity", ""),
            "execution_error": context.get("execution_error", ""),
            "qa_detail": context.get("qa_detail", make_empty_qa_detail()),
            "fix_suggestion": context.get("fix_suggestion", ""),
        }
    )


def build_planned_changes(context: Dict[str, Any], lane: str = "integration") -> Dict[str, Any]:
    return {
        "project_mode": context.get("project_mode", "new_project"),
        "goal": context.get("task", ""),
        "project_id": context.get("project_id", ""),
        "epic_id": context.get("epic_id", ""),
        "story_id": context.get("story_id", "story_1"),
        "story_name": context.get("story_name", context.get("story_id", "story_1")),
        "resume_from": context.get("baseline_path", ""),
        "lane": lane,
        "parallel_mode": True,
        "gate_state": context.get("gate_state", {}),
        "change_requests": context.get("change_requests", []),
    }


def build_workflow_context(context: Dict[str, Any], system_target: Dict[str, Any]) -> Dict[str, Any]:
    return {
        "task": context.get("task", ""),
        "project_mode": context.get("project_mode", "new_project"),
        "project_id": context.get("project_id", ""),
        "epic_id": context.get("epic_id", ""),
        "story_id": context.get("story_id", "story_1"),
        "story_name": context.get("story_name", context.get("story_id", "story_1")),
        "delivery_mode": context.get("delivery_mode", "story_based"),
        "baseline_path": context.get("baseline_path", ""),
        "baseline_tree": context.get("baseline_tree", ""),
        "story_packet": context.get("story_packet", {}),
        "system_target": context.get("system_target", system_target),
        "existing_system_summary_path": context.get("existing_system_summary_path", ""),
        "change_impact_report_path": context.get("change_impact_report_path", ""),
        "integration_strategy_path": context.get("integration_strategy_path", ""),
        "readiness_report_path": context.get("readiness_report_path", ""),
        "prd": context.get("prd", ""),
        "design": context.get("design", ""),
        "bugs": context.get("bugs", []),
        "fix_suggestion": context.get("fix_suggestion", ""),
        "execution_error": context.get("execution_error", ""),
        "history": context.get("history", []),
        "qa_detail": context.get("qa_detail", {}),
        "release_status": context.get("release_status", ""),
        "severity": context.get("severity", ""),
        "retry_reason": context.get("retry_reason", ""),
        "operation": context.get("operation", "generate"),
    }


def write_run_state(context: Dict[str, Any], state_dir: Path, run_state_path: Path, output_project_dir: str, system_target: Dict[str, Any]) -> str:
    state_dir.mkdir(parents=True, exist_ok=True)
    state = {
        "run_id": context.get("run_id", ""),
        "project_id": context.get("project_id", ""),
        "epic_id": context.get("epic_id", ""),
        "story_id": context.get("story_id", "story_1"),
        "story_name": context.get("story_name", context.get("story_id", "story_1")),
        "delivery_mode": context.get("delivery_mode", "story_based"),
        "task": context.get("task", ""),
        "project_mode": context.get("project_mode", "new_project"),
        "baseline_path": context.get("baseline_path", ""),
        "loop_count": context.get("loop_count", 0),
        "operation": context.get("operation", "generate"),
        "retry_reason": context.get("retry_reason", ""),
        "release_status": context.get("release_status", ""),
        "severity": context.get("severity", ""),
        "execution_error": context.get("execution_error", ""),
        "qa_detail": context.get("qa_detail", {}),
        "story_packet": context.get("story_packet", {}),
        "system_target": context.get("system_target", system_target),
        "existing_system_summary_path": context.get("existing_system_summary_path", ""),
        "change_impact_report_path": context.get("change_impact_report_path", ""),
        "integration_strategy_path": context.get("integration_strategy_path", ""),
        "readiness_report_path": context.get("readiness_report_path", ""),
        "history_tail": context.get("history", [])[-3:],
        "output_project_dir": output_project_dir,
        "gate_state": context.get("gate_state", {}),
        "artifact_locks_path": context.get("artifact_locks_path", ""),
        "change_requests": context.get("change_requests", []),
    }
    run_state_path.write_text(json.dumps(state, ensure_ascii=False, indent=2), encoding="utf-8")
    return str(run_state_path)


def prepare_baseline(context: Dict[str, Any]) -> None:
    baseline_path = context.get("baseline_path", "")
    if baseline_path:
        log_step(f"Loading baseline from {baseline_path}")
        load_baseline_project(baseline_path)
    else:
        reset_output_dir()
