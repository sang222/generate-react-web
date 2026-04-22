from __future__ import annotations

import json
import os
import threading
import time
from pathlib import Path
from typing import Any, Dict

TOKEN_USAGE_DIRNAME = "token_usage"
DEFAULT_STORY_TOKEN_BUDGET = int(os.getenv("STORY_TOKEN_BUDGET", "0") or 0)
DEFAULT_ROLE_BUDGETS = {
    "developer": int(os.getenv("ROLE_TOKEN_BUDGET_DEVELOPER", "0") or 0),
    "fe_developer": int(os.getenv("ROLE_TOKEN_BUDGET_DEVELOPER", "0") or 0),
    "be_developer": int(os.getenv("ROLE_TOKEN_BUDGET_DEVELOPER", "0") or 0),
    "qa": int(os.getenv("ROLE_TOKEN_BUDGET_QA", "0") or 0),
    "fe_reviewer": int(os.getenv("ROLE_TOKEN_BUDGET_QA", "0") or 0),
    "be_reviewer": int(os.getenv("ROLE_TOKEN_BUDGET_QA", "0") or 0),
    "integration_qa": int(os.getenv("ROLE_TOKEN_BUDGET_QA", "0") or 0),
}

_LOCK = threading.RLock()
_CURRENT: Dict[str, Any] = {}
_TOTALS: Dict[str, int] = {"prompt": 0, "completion": 0, "total": 0}
_ROLE_TOTALS: Dict[str, int] = {}


class TokenBudgetExceeded(RuntimeError):
    def __init__(self, message: str, *, role: str = "", used: int = 0, budget: int = 0) -> None:
        super().__init__(message)
        self.role = role
        self.used = used
        self.budget = budget
        self.reason_code = "BLOCKED_TOKEN_BUDGET_EXCEEDED"


def estimate_tokens(text: str) -> int:
    if not text:
        return 0
    return max(1, len(text) // 4)


def set_token_context(context: Dict[str, Any]) -> None:
    with _LOCK:
        _CURRENT.clear()
        _CURRENT.update(
            {
                "project_id": context.get("project_id", "unknown_project"),
                "story_id": context.get("story_id", "unknown_story"),
                "run_id": context.get("run_id", "unknown_run"),
            }
        )
        _TOTALS["prompt"] = int(context.get("prompt_tokens_used", 0) or 0)
        _TOTALS["completion"] = int(context.get("completion_tokens_used", 0) or 0)
        _TOTALS["total"] = int(context.get("total_tokens_used", 0) or 0)
        _ROLE_TOTALS.clear()
        _ROLE_TOTALS.update(context.get("role_tokens_used", {}) or {})


def sync_token_usage_to_context(context: Dict[str, Any]) -> None:
    with _LOCK:
        context["prompt_tokens_used"] = _TOTALS["prompt"]
        context["completion_tokens_used"] = _TOTALS["completion"]
        context["total_tokens_used"] = _TOTALS["total"]
        context["role_tokens_used"] = dict(_ROLE_TOTALS)


def _usage_path(project_id: str, story_id: str) -> Path:
    return Path("project_state") / project_id / "stories" / story_id / "token_usage.jsonl"


def _budget_for_role(role: str) -> int:
    env_key = f"ROLE_TOKEN_BUDGET_{role.upper()}"
    value = int(os.getenv(env_key, "0") or 0)
    if value > 0:
        return value
    return DEFAULT_ROLE_BUDGETS.get(role, 0)


def check_budget_before_call(role: str, prompt_tokens: int) -> None:
    story_budget = int(os.getenv("STORY_TOKEN_BUDGET", str(DEFAULT_STORY_TOKEN_BUDGET)) or 0)
    role_budget = _budget_for_role(role)
    with _LOCK:
        if story_budget > 0 and _TOTALS["total"] + prompt_tokens > story_budget:
            raise TokenBudgetExceeded(
                f"Token budget exceeded before {role}: {_TOTALS['total'] + prompt_tokens}/{story_budget}",
                role=role,
                used=_TOTALS["total"] + prompt_tokens,
                budget=story_budget,
            )
        current_role = _ROLE_TOTALS.get(role, 0)
        if role_budget > 0 and current_role + prompt_tokens > role_budget:
            raise TokenBudgetExceeded(
                f"Role token budget exceeded before {role}: {current_role + prompt_tokens}/{role_budget}",
                role=role,
                used=current_role + prompt_tokens,
                budget=role_budget,
            )


def record_llm_usage(
    *,
    role: str,
    model: str,
    prompt: str,
    completion: str,
    duration_ms: int,
    provider: str = "ollama",
) -> Dict[str, Any]:
    prompt_tokens = estimate_tokens(prompt)
    completion_tokens = estimate_tokens(completion)
    total = prompt_tokens + completion_tokens
    with _LOCK:
        _TOTALS["prompt"] += prompt_tokens
        _TOTALS["completion"] += completion_tokens
        _TOTALS["total"] += total
        _ROLE_TOTALS[role] = _ROLE_TOTALS.get(role, 0) + total
        project_id = str(_CURRENT.get("project_id", "unknown_project"))
        story_id = str(_CURRENT.get("story_id", "unknown_story"))
        run_id = str(_CURRENT.get("run_id", "unknown_run"))
        entry = {
            "timestamp_ms": int(time.time() * 1000),
            "project_id": project_id,
            "story_id": story_id,
            "run_id": run_id,
            "role": role,
            "model": model,
            "provider": provider,
            "estimated_prompt_tokens": prompt_tokens,
            "estimated_completion_tokens": completion_tokens,
            "estimated_total_tokens": total,
            "story_total_tokens_after_call": _TOTALS["total"],
            "duration_ms": duration_ms,
        }
        path = _usage_path(project_id, story_id)
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(entry, ensure_ascii=False) + "\n")
        return entry
