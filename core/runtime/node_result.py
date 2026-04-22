from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Literal

NodeStatus = Literal["PASS", "RETRY", "BLOCKED", "SKIP", "DONE"]


@dataclass
class NodeResult:
    status: NodeStatus
    next_node: str | None = None
    updates: dict[str, Any] = field(default_factory=dict)
    artifacts: dict[str, str] = field(default_factory=dict)
    block_reason: str = ""
    retry_reason: str = ""
    raw_context: dict[str, Any] | None = None
