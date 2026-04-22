from __future__ import annotations

from typing import Any

from core.gates import fail_gate as _fail_gate, load_gate_state, pass_gate as _pass_gate, save_gate_state
from core.runtime.state import RuntimeState


class GateService:
    def load(self, state: RuntimeState) -> dict[str, Any]:
        return load_gate_state(state.identity.project_id, state.identity.epic_id, state.identity.story_id)

    def pass_gate(self, state: RuntimeState, gate: str, artifacts: list[str] | None = None) -> None:
        gate_state = state.gates or self.load(state)
        _pass_gate(gate_state, gate, artifacts or [])
        save_gate_state(gate_state)
        state.gates = gate_state

    def fail_gate(self, state: RuntimeState, gate: str, reason: str, artifacts: list[str] | None = None) -> None:
        gate_state = state.gates or self.load(state)
        _fail_gate(gate_state, gate, reason, artifacts or [])
        save_gate_state(gate_state)
        state.gates = gate_state
