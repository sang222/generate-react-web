from __future__ import annotations

from pathlib import Path
from typing import Any, Dict

from core.recovery_engine import run_recovery_engine


def should_trigger_adaptive_recovery(context: Dict[str, Any]) -> bool:
    return int(context.get("loop_count", 0) or 0) >= 2 and not bool(context.get("adaptive_recovery_triggered"))


def run_adaptive_recovery(context: Dict[str, Any], root: str | Path = ".") -> Dict[str, Any]:
    return run_recovery_engine(context, root)
