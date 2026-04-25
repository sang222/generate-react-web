from __future__ import annotations

from pathlib import Path
from typing import Any, Dict


def _safe_token(value: Any) -> str:
    text = str(value or "unknown")
    return "".join(ch if ch.isalnum() or ch in {"-", "_"} else "_" for ch in text)[:80]


def persist_bad_llm_output(
    *,
    context: Dict[str, Any],
    role: str,
    raw_output: str,
    reason: str,
    root: str | Path = ".runs/debug_outputs",
) -> str:
    target_root = Path(root)
    target_root.mkdir(parents=True, exist_ok=True)

    run_id = _safe_token(context.get("run_id"))
    story_id = _safe_token(context.get("story_id"))
    loop_count = _safe_token(context.get("loop_count"))
    role_token = _safe_token(role)
    reason_token = _safe_token(reason)

    path = target_root / f"{run_id}_{story_id}_{role_token}_loop{loop_count}_{reason_token}.txt"
    path.write_text(raw_output or "", encoding="utf-8")
    return str(path)
