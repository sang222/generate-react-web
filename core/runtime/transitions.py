from __future__ import annotations

from core.runtime.node_result import NodeResult
from core.runtime.state import RuntimeState


class TransitionTable:
    def next_phase(self, state: RuntimeState, result: NodeResult) -> str:
        if result.next_node:
            return result.next_node
        if result.status == "BLOCKED":
            return "blocked"
        if result.status == "DONE":
            return "done"
        return state.execution.phase
