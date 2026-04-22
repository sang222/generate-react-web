from __future__ import annotations

from core.agents.role_registry import RoleRegistry
from core.agents.subagent_runner import SubagentRunner


def create_subagent_runner() -> SubagentRunner:
    return SubagentRunner(role_registry=RoleRegistry())
