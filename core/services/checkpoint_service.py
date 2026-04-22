from __future__ import annotations

from core.runtime.checkpoints import Checkpointer
from core.runtime.state import RuntimeState


class CheckpointService:
    def __init__(self, checkpointer: Checkpointer | None = None) -> None:
        self.checkpointer = checkpointer or Checkpointer()

    def save(self, state: RuntimeState, event: str) -> str:
        return str(self.checkpointer.save(state, event))
