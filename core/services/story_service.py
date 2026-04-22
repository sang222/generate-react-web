from __future__ import annotations

from typing import Any

from core.story_state import default_story_packet, get_story_definition
from core.runtime.state import RuntimeState


class StoryService:
    def get_story_definition(self, state: RuntimeState) -> dict[str, Any]:
        return get_story_definition(state.identity.project_id, state.identity.epic_id, state.identity.story_id)

    def default_story_packet(self, state: RuntimeState, *, story_name: str | None = None) -> dict[str, Any]:
        return default_story_packet(
            project_id=state.identity.project_id,
            epic_id=state.identity.epic_id,
            story_id=state.identity.story_id,
            story_name=story_name or state.identity.story_id,
            task=state.task,
            project_mode=state.project_mode,
            execution_mode=state.execution_mode,
        )
