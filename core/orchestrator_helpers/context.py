from __future__ import annotations

import json
import shutil
from pathlib import Path
from typing import Any, Dict, List, TypedDict

from core.debug import log_step


class ReviewResult(TypedDict, total=False):
    structural_bugs: List[str]
    functional_bugs: List[str]
    prd_gaps: List[str]
    ui_gaps: List[str]
    regression_bugs: List[str]
    integration_issues: List[str]
    fix_suggestion: str


QA_LIST_FIELDS = [
    "structural_bugs",
    "functional_bugs",
    "prd_gaps",
    "ui_gaps",
    "regression_bugs",
]


def make_empty_qa_detail() -> dict[str, list[str]]:
    return {key: [] for key in QA_LIST_FIELDS}


def merge_qa_details(*details: ReviewResult) -> dict[str, list[str]]:
    merged = make_empty_qa_detail()

    for detail in details:
        for key in QA_LIST_FIELDS:
            value = detail.get(key)
            if isinstance(value, list):
                merged[key].extend(str(item) for item in value if item)

    return merged


def append_history(context: Dict[str, Any]) -> None:
    history = context.setdefault("history", [])
    if not isinstance(history, list):
        context["history"] = []
        history = context["history"]

    history.append(
        {
            "loop_count": context.get("loop_count", 0),
            "release_status": context.get("release_status", ""),
            "severity": context.get("severity", ""),
            "execution_error": context.get("execution_error", ""),
            "qa_detail": context.get("qa_detail", make_empty_qa_detail()),
            "fix_suggestion": context.get("fix_suggestion", ""),
            "retry_reason": context.get("retry_reason", ""),
        }
    )


def build_workflow_context(
    context: Dict[str, Any],
    system_target: Dict[str, Any] | None = None,
) -> Dict[str, Any]:
    packet = context.get("story_packet", {}) or {}

    return {
        "project_id": context.get("project_id"),
        "epic_id": context.get("epic_id"),
        "story_id": context.get("story_id"),
        "story_name": context.get("story_name"),
        "project_mode": context.get("project_mode"),
        "delivery_mode": context.get("delivery_mode"),
        "system_type": context.get("system_type"),
        "project_level": context.get("project_level"),
        "delivery_profile": context.get("delivery_profile"),
        "retry_reason": context.get("retry_reason"),
        "operation": context.get("operation"),
        "baseline_path": context.get("baseline_path"),
        "depends_on": context.get("depends_on", []),
        "story_packet": packet,
        "system_target": system_target or context.get("system_target", {}),
    }


def _json_safe_payload(context: Dict[str, Any]) -> Dict[str, Any]:
    return {
        "run_id": context.get("run_id"),
        "project_id": context.get("project_id"),
        "epic_id": context.get("epic_id"),
        "story_id": context.get("story_id"),
        "story_name": context.get("story_name"),
        "delivery_mode": context.get("delivery_mode"),
        "project_mode": context.get("project_mode"),
        "system_type": context.get("system_type"),
        "project_level": context.get("project_level"),
        "delivery_profile": context.get("delivery_profile"),
        "loop_count": context.get("loop_count"),
        "release_status": context.get("release_status"),
        "final_decision": context.get("final_decision"),
        "severity": context.get("severity"),
        "task": context.get("task"),
        "story_goal": context.get("story_goal"),
        "baseline_path": context.get("baseline_path"),
        "depends_on": context.get("depends_on", []),
        "retry_reason": context.get("retry_reason"),
        "operation": context.get("operation"),
        "execution_error": context.get("execution_error"),
        "fix_suggestion": context.get("fix_suggestion"),
        "qa_detail": context.get("qa_detail", make_empty_qa_detail()),
        "change_requests": context.get("change_requests", []),
        "integration_conflicts": context.get("integration_conflicts", []),
        "next_story": context.get("next_story", ""),
        "story_packet": context.get("story_packet", {}),
        "system_target": context.get("system_target", {}),
    }


def write_run_state(
    context: Dict[str, Any],
    state_dir: str | Path,
    run_state_path: str | Path,
    output_project_dir: str,
    system_target: Dict[str, Any] | None = None,
) -> None:
    del output_project_dir  # kept for signature compatibility
    del system_target

    state_root = Path(state_dir)
    state_root.mkdir(parents=True, exist_ok=True)

    target = Path(run_state_path)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(
        json.dumps(_json_safe_payload(context), ensure_ascii=False, indent=2),
        encoding="utf-8",
    )


def write_workflow_status(context: Dict[str, Any], next_step: str) -> None:
    project_id = str(context.get("project_id") or "").strip()
    if not project_id:
        return

    status_path = Path("project_state") / project_id / "workflow_status.yaml"
    status_path.parent.mkdir(parents=True, exist_ok=True)

    gate_state = context.get("gate_state", {}) or {}
    gates = gate_state.get("gates", []) if isinstance(gate_state, dict) else []
    last_successful_gate = ""
    failed_gate = ""

    if isinstance(gates, list):
        for gate in gates:
            if not isinstance(gate, dict):
                continue
            status = str(gate.get("status", ""))
            gate_name = str(gate.get("gate", ""))
            if status == "passed":
                last_successful_gate = gate_name
            elif status == "failed":
                failed_gate = gate_name

    qa_detail = context.get("qa_detail", {}) or {}
    affected_modules = []
    if context.get("change_impact_report"):
        impact = context["change_impact_report"]
        if isinstance(impact, dict):
            affected_modules = impact.get("affected_modules", []) or []

    lines = [
        f"project_id: {context.get('project_id', '')}",
        f"epic_id: {context.get('epic_id', '')}",
        f"story_id: {context.get('story_id', '')}",
        f"story_name: {context.get('story_name', '')}",
        f"project_mode: {context.get('project_mode', '')}",
        f"project_level: {context.get('project_level', '')}",
        f"delivery_profile: {context.get('delivery_profile', '')}",
        f"release_status: {context.get('release_status', '')}",
        f"final_decision: {context.get('final_decision', '')}",
        f"severity: {context.get('severity', '')}",
        f"current_delivered_story: {context.get('delivery_index', {}).get('current_delivered_story', {}).get('story_id', '') if isinstance(context.get('delivery_index'), dict) else ''}",
        f"last_successful_gate: {last_successful_gate}",
        f"failed_gate: {failed_gate}",
        f"brownfield_ready: {str((context.get('brownfield_readiness_report') or {}).get('ready', False)).lower() if isinstance(context.get('brownfield_readiness_report'), dict) else 'false'}",
        f"next_step: {next_step}",
        f"blocked_reason: {context.get('execution_error', '')}",
        "affected_modules:",
    ]

    for module in affected_modules:
        lines.append(f"  - {module}")

    lines.extend(
        [
            "structural_bugs:",
            *[f"  - {item}" for item in qa_detail.get("structural_bugs", [])],
            "functional_bugs:",
            *[f"  - {item}" for item in qa_detail.get("functional_bugs", [])],
            "prd_gaps:",
            *[f"  - {item}" for item in qa_detail.get("prd_gaps", [])],
            "regression_bugs:",
            *[f"  - {item}" for item in qa_detail.get("regression_bugs", [])],
        ]
    )

    status_path.write_text("\n".join(lines).strip() + "\n", encoding="utf-8")


def prepare_baseline(context: Dict[str, Any]) -> None:
    baseline_path = str(context.get("baseline_path") or "").strip()
    if not baseline_path:
        return

    source = Path(baseline_path)
    if not source.exists():
        context["execution_error"] = f"[baseline missing]\nCould not find baseline path: {baseline_path}"
        return

    target = Path(context.get("working_output_dir") or "output_project")

    if target.exists():
        shutil.rmtree(target)

    shutil.copytree(source, target)
    log_step("orchestrator", f"Prepared baseline from {source} -> {target}")