from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List

PHASE_ORDER = [
    "GATE_1_RESEARCH",
    "GATE_2_SPECIFICATION",
    "GATE_3_DESIGN",
    "BROWNFIELD_READINESS_GATE",
    "GATE_4_IMPLEMENTATION",
    "RECOVERY_GATE",
    "RELEASE_GATE",
]


def gate_states_root(project_id: str) -> Path:
    return Path("project_state") / project_id / "gates"


def gate_state_path(project_id: str, story_id: str) -> Path:
    return gate_states_root(project_id) / f"{story_id}.json"


def gate_summary_path(project_id: str) -> Path:
    return Path("project_state") / project_id / "gate_state.json"


def default_gate_state(project_id: str, epic_id: str, story_id: str) -> Dict[str, Any]:
    return {
        "project_id": project_id,
        "epic_id": epic_id,
        "story_id": story_id,
        "current_gate": PHASE_ORDER[0],
        "passed_gates": [],
        "gate_statuses": {gate: "pending" for gate in PHASE_ORDER},
        "last_failed_gate": "",
        "history": [],
    }


def load_gate_state(project_id: str, epic_id: str, story_id: str) -> Dict[str, Any]:
    path = gate_state_path(project_id, story_id)
    if path.exists():
        return json.loads(path.read_text(encoding="utf-8"))
    return default_gate_state(project_id, epic_id, story_id)


def _write_project_gate_summary(state: Dict[str, Any]) -> None:
    root = gate_states_root(state["project_id"])
    root.mkdir(parents=True, exist_ok=True)
    gate_files = sorted(p.name for p in root.glob("*.json"))
    summary = {
        "project_id": state["project_id"],
        "latest_story_id": state["story_id"],
        "current_gate": state.get("current_gate", ""),
        "passed_gates": state.get("passed_gates", []),
        "last_failed_gate": state.get("last_failed_gate", ""),
        "gate_statuses": state.get("gate_statuses", {}),
        "gate_files": gate_files,
        "history_tail": state.get("history", [])[-10:],
    }
    gate_summary_path(state["project_id"]).write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")


def save_gate_state(state: Dict[str, Any]) -> str:
    path = gate_state_path(state["project_id"], state["story_id"])
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(state, ensure_ascii=False, indent=2), encoding="utf-8")
    _write_project_gate_summary(state)
    return str(path)


def pass_gate(state: Dict[str, Any], gate_name: str, summary: str, artifacts: List[str] | None = None) -> Dict[str, Any]:
    if gate_name not in PHASE_ORDER:
        return state
    gate_statuses = state.setdefault("gate_statuses", {gate: "pending" for gate in PHASE_ORDER})
    gate_statuses[gate_name] = "passed"
    if gate_name not in state["passed_gates"]:
        state["passed_gates"].append(gate_name)
    idx = PHASE_ORDER.index(gate_name)
    next_gate = PHASE_ORDER[min(idx + 1, len(PHASE_ORDER) - 1)]
    state["current_gate"] = next_gate if gate_name != "RELEASE_GATE" else "RELEASE_APPROVED"
    if state.get("last_failed_gate") == gate_name:
        state["last_failed_gate"] = ""
    state["history"].append({
        "gate": gate_name,
        "status": "passed",
        "summary": summary,
        "artifacts": artifacts or [],
        "timestamp": datetime.now().isoformat(timespec="seconds"),
    })
    return state


def fail_gate(state: Dict[str, Any], gate_name: str, summary: str, reason_code: str = "") -> Dict[str, Any]:
    gate_statuses = state.setdefault("gate_statuses", {gate: "pending" for gate in PHASE_ORDER})
    gate_statuses[gate_name] = "failed"
    if gate_name in state.get("passed_gates", []):
        state["passed_gates"] = [g for g in state["passed_gates"] if g != gate_name]
    # invalidate later gates because this story is no longer cleanly advanced
    if gate_name in PHASE_ORDER:
        idx = PHASE_ORDER.index(gate_name)
        for later_gate in PHASE_ORDER[idx + 1:]:
            if later_gate in state.get("passed_gates", []):
                state["passed_gates"] = [g for g in state["passed_gates"] if g != later_gate]
            if gate_statuses.get(later_gate) == "passed":
                gate_statuses[later_gate] = "pending"
    state["current_gate"] = gate_name
    state["last_failed_gate"] = gate_name
    state["history"].append({
        "gate": gate_name,
        "status": "failed",
        "summary": summary,
        "reason_code": reason_code,
        "timestamp": datetime.now().isoformat(timespec="seconds"),
    })
    return state
