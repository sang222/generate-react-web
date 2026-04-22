from __future__ import annotations

from typing import Any

from core.runtime.state import RuntimeState


def build_state_view(state: RuntimeState, *, node: str) -> dict[str, Any]:
    """Return a node-scoped context view.

    This keeps the graph runtime from handing the full state to every node.
    More precise views should be added as nodes are extracted from the legacy path.
    """
    base = {
        "project_id": state.identity.project_id,
        "epic_id": state.identity.epic_id,
        "story_id": state.identity.story_id,
        "run_id": state.identity.run_id,
        "task": state.task,
        "project_mode": state.project_mode,
        "execution_mode": state.execution_mode,
        "phase": state.execution.phase,
    }
    if node in {"implementation", "review", "candidate_learning"}:
        base.update(
            {
                "story_packet": state.story_packet,
                "active_lanes": state.active_lanes,
                "effective_target": state.effective_target,
                "retry_reason": state.execution.retry_reason,
                "execution_error": state.execution.execution_error,
            }
        )
    return base
