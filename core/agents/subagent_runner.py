from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable

from core.agents.role_registry import RoleRegistry
from core.llm import call_role_llm
from core.token_budget import estimate_tokens


@dataclass
class SubagentResult:
    role: str
    model: str
    content: str
    estimated_prompt_tokens: int
    artifacts: dict[str, str] | None = None


class SubagentRunner:
    """Thin role runner used by future runtime nodes.

    Existing agent functions can keep their current prompts during migration; this
    interface gives new nodes a consistent way to call role LLMs with bounded
    context and model routing.
    """

    def __init__(self, role_registry: RoleRegistry | None = None, caller: Callable[..., str] = call_role_llm) -> None:
        self.role_registry = role_registry or RoleRegistry()
        self.caller = caller

    def run(self, *, role: str, task: str, context: dict[str, Any], output_contract: str = "") -> SubagentResult:
        config = self.role_registry.get(role)
        prompt = self._build_prompt(role=role, task=task, context=context, output_contract=output_contract)
        content = self.caller(role, prompt)
        return SubagentResult(
            role=role,
            model=config.model,
            content=content,
            estimated_prompt_tokens=estimate_tokens(prompt),
        )

    def _build_prompt(self, *, role: str, task: str, context: dict[str, Any], output_contract: str) -> str:
        return (
            f"Role: {role}\n"
            f"Task: {task}\n"
            f"Output contract: {output_contract or 'Follow role contract.'}\n"
            f"Context:\n{context}\n"
        )
