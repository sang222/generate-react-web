from __future__ import annotations

from core.runtime.node_result import NodeResult
from core.runtime.nodes.base import RuntimeNode
from core.runtime.state import RuntimeState


class LegacyOrchestratorNode(RuntimeNode):
    """Compatibility node that delegates to the current BMAD orchestrator.

    This is the migration bridge: the runtime graph/checkpoint layer exists now,
    while phase nodes can be extracted gradually without breaking old behavior.
    """

    name = "legacy_orchestrator"

    def run(self, state: RuntimeState) -> NodeResult:
        from core.orchestrator import run_orchestrator

        result = run_orchestrator(
            task=state.task,
            project_mode=state.project_mode,
            project_id=state.identity.project_id,
            epic_id=state.identity.epic_id,
            story_id=state.identity.story_id,
            story_name=state.raw_context.get("story_name") or state.identity.story_id,
            resume_from=state.raw_context.get("resume_from"),
            depends_on=state.raw_context.get("depends_on") or [],
            execution_mode=state.execution_mode,
        )
        status = "DONE" if result.get("final_decision") else "PASS"
        if result.get("release_status") == "BLOCKED" or result.get("final_decision") == "BLOCKED":
            status = "BLOCKED"
        return NodeResult(
            status=status,  # type: ignore[arg-type]
            next_node="done" if status != "BLOCKED" else "blocked",
            raw_context=result,
            block_reason=str(result.get("blocked_reason", result.get("block_reason", "")) or ""),
        )
