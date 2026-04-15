from __future__ import annotations

from typing import Any, Dict


def decide_final_decision(context: Dict[str, Any]) -> str:
    if context.get("release_status") == "DONE":
        return "DELIVER_STORY"

    if context.get("adaptive_recovery_triggered"):
        block_reason = context.get("adaptive_recovery_block_reason", "")
        if block_reason:
            return str(block_reason)
        if context.get("execution_error"):
            return "BLOCKED_RECOVERY_RERUN_FAILED"

    return str(context.get("release_status", ""))
