from __future__ import annotations

from typing import Mapping

from core.runtime.checkpoints import Checkpointer
from core.runtime.node_result import NodeResult
from core.runtime.nodes.base import RuntimeNode
from core.runtime.state import RuntimeState
from core.runtime.transitions import TransitionTable


class RuntimeGraph:
    def __init__(
        self,
        *,
        nodes: Mapping[str, RuntimeNode],
        transitions: TransitionTable | None = None,
        checkpointer: Checkpointer | None = None,
    ) -> None:
        self.nodes = dict(nodes)
        self.transitions = transitions or TransitionTable()
        self.checkpointer = checkpointer or Checkpointer()

    def run(self, state: RuntimeState) -> RuntimeState:
        while state.execution.phase not in {"done", "blocked"}:
            self.checkpointer.save(state, event=f"before:{state.execution.phase}")
            node = self.nodes.get(state.execution.phase)
            if node is None:
                state.execution.block_reason = f"NO_NODE_FOR_PHASE:{state.execution.phase}"
                state.execution.phase = "blocked"
                self.checkpointer.save(state, event="blocked:no_node")
                break
            result = node.run(state)
            self.apply_result(state, result)
            self.checkpointer.save(state, event=f"after:{node.name}")
            state.execution.phase = self.transitions.next_phase(state, result)  # type: ignore[assignment]
        self.checkpointer.save(state, event="final")
        return state

    @staticmethod
    def apply_result(state: RuntimeState, result: NodeResult) -> None:
        for key, value in result.updates.items():
            if hasattr(state, key):
                setattr(state, key, value)
            else:
                state.raw_context[key] = value
        state.artifacts.artifacts.update(result.artifacts)
        if result.retry_reason:
            state.execution.retry_reason = result.retry_reason
        if result.block_reason:
            state.execution.block_reason = result.block_reason
        if result.raw_context is not None:
            state.raw_context.update(result.raw_context)
            refreshed = RuntimeState.from_legacy_context(state.raw_context)
            state.identity = refreshed.identity
            state.execution.loop_count = refreshed.execution.loop_count
            state.execution.retry_reason = refreshed.execution.retry_reason
            state.execution.execution_error = refreshed.execution.execution_error
            state.execution.block_reason = refreshed.execution.block_reason
            state.execution.final_decision = refreshed.execution.final_decision
            state.review = refreshed.review
            state.artifacts = refreshed.artifacts
            state.gates = refreshed.gates
            state.active_lanes = refreshed.active_lanes
            state.story_packet = refreshed.story_packet
            state.effective_target = refreshed.effective_target
