from __future__ import annotations

from pathlib import Path
from typing import Any

from core.orchestrator_helpers.delivery import create_story_delivery
from core.runtime.state import RuntimeState


class DeliveryService:
    def create_delivery(self, state: RuntimeState, context: dict[str, Any], *, deliveries_dir: str | Path = "deliveries") -> dict[str, Any]:
        return create_story_delivery(context, Path(deliveries_dir))
