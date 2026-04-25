from __future__ import annotations

from typing import Any, Dict, List


DEVELOPER_SELF_RETRY_REASONS = {
    "missing_required_files",
    "build_failure",
    "build_failed",
    "preflight_failure",
    "execution_error",
    "invalid_project_json",
    "invalid_json_parallel",
    "invalid_file_paths",
    "missing_package_script",
    "structural_validation_failed",
    "lane_runtime_error",
    "ownership_conflict",
    "allowed_scope_violation",
    "protected_scope_violation",
    "shared_path_override",
    "locked_artifact_change",
}

HIGH_RISK_RETRY_REASONS = {
    "ownership_conflict",
    "allowed_scope_violation",
    "protected_scope_violation",
    "shared_path_override",
    "locked_artifact_change",
}


def get_retry_reason(context: Dict[str, Any]) -> str:
    return str(context.get("retry_reason") or "").strip()


def get_retry_history(context: Dict[str, Any]) -> List[Dict[str, Any]]:
    value = context.get("retry_history")
    return value if isinstance(value, list) else []


def append_retry_history(context: Dict[str, Any]) -> None:
    reason = get_retry_reason(context)
    if not reason:
        return

    context.setdefault("retry_history", []).append(
        {
            "loop_count": context.get("loop_count"),
            "retry_reason": reason,
            "execution_error": context.get("execution_error", ""),
            "severity": context.get("severity", ""),
            "release_status": context.get("release_status", ""),
        }
    )


def count_same_retry_reason(context: Dict[str, Any], reason: str | None = None) -> int:
    target = str(reason or get_retry_reason(context) or "").strip()
    if not target:
        return 0

    return sum(1 for item in get_retry_history(context) if item.get("retry_reason") == target)


def is_frontend_only_new_project(context: Dict[str, Any]) -> bool:
    return (
        context.get("project_mode") == "new_project"
        and context.get("story_packet", {}).get("execution_mode") == "frontend_only"
        and context.get("active_lanes") == ["frontend"]
    )


def is_developer_self_retry_allowed(context: Dict[str, Any], max_self_retries: int = 2) -> bool:
    reason = get_retry_reason(context)
    if not reason:
        return False

    if reason not in DEVELOPER_SELF_RETRY_REASONS:
        return False

    # Count includes the current failure if append_retry_history() has already run.
    return count_same_retry_reason(context, reason) < max_self_retries


def is_stuck_after_retries(context: Dict[str, Any], max_self_retries: int = 2) -> bool:
    reason = get_retry_reason(context)
    if not reason:
        return False

    if context.get("release_status") != "RETRY":
        return False

    if count_same_retry_reason(context, reason) >= max_self_retries:
        return True

    return int(context.get("loop_count") or 0) >= max_self_retries and bool(context.get("execution_error"))


def should_run_ai_review(context: Dict[str, Any], lane: str, validation_passed: bool = True) -> bool:
    """
    AI reviewer is escalation, not the default phase for low-risk new projects.

    Rules:
    - existing_project/brownfield keeps AI review.
    - backend/multi-lane changes keep AI review.
    - stuck after developer self-retries triggers AI review.
    - new_project + frontend_only + validation passed skips deep AI review.
    """
    if context.get("project_mode") == "existing_project":
        return True

    if is_stuck_after_retries(context):
        return True

    if lane == "backend" or lane == "integration":
        return True

    if not validation_passed:
        return is_stuck_after_retries(context)

    if is_frontend_only_new_project(context) and lane == "frontend":
        return False

    return True


def should_run_lead(context: Dict[str, Any], max_loop: int) -> bool:
    """
    Lead is needed for final decision, stuck escalation, or max-loop closure.
    It is skipped for deterministic developer self-retry cases.
    """
    if context.get("release_status") == "DONE":
        return True

    if context.get("release_status") != "RETRY":
        return True

    if is_stuck_after_retries(context):
        return True

    if int(context.get("loop_count") or 0) >= max_loop:
        return True

    if is_developer_self_retry_allowed(context):
        return False

    return True
