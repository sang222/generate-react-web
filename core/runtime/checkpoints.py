from __future__ import annotations

import json
import time
from pathlib import Path
from typing import Any

from core.runtime.state import RuntimeState


class Checkpointer:
    def __init__(self, root: str | Path = "project_state") -> None:
        self.root = Path(root)

    def checkpoint_dir(self, state: RuntimeState) -> Path:
        return (
            self.root
            / state.identity.project_id
            / "stories"
            / state.identity.story_id
            / "checkpoints"
            / state.identity.run_id
        )

    def save(self, state: RuntimeState, event: str) -> Path:
        path = self.checkpoint_dir(state)
        path.mkdir(parents=True, exist_ok=True)
        safe_event = event.replace(":", "_").replace("/", "_")
        file_path = path / f"{int(time.time() * 1000)}_{safe_event}.json"
        payload: dict[str, Any] = {
            "event": event,
            "timestamp_ms": int(time.time() * 1000),
            "state": state.to_dict(),
        }
        file_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
        latest = path / "latest.json"
        latest.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
        return file_path
