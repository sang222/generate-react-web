from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from core.config import get_model_for_role


@dataclass(frozen=True)
class RoleConfig:
    role: str
    model: str
    skills: list[str] = field(default_factory=list)
    max_prompt_tokens: int = 0


class RoleRegistry:
    DEFAULT_SKILLS = {
        "pm": ["dev-team-workflow"],
        "architect": ["dev-team-workflow"],
        "fe_developer": ["fe-ui-implementation"],
        "be_developer": ["dev-team-workflow"],
        "fe_reviewer": ["fe-visual-review"],
        "qa": ["dev-team-workflow"],
        "lead": ["dev-team-workflow"],
        "recovery_meta": ["skill-reviewer"],
        "skill_reviewer": ["skill-reviewer"],
    }

    def get(self, role: str) -> RoleConfig:
        return RoleConfig(
            role=role,
            model=get_model_for_role(role),
            skills=list(self.DEFAULT_SKILLS.get(role, [])),
        )
