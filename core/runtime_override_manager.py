from __future__ import annotations

from typing import Any, Dict, Literal

ApplyScope = Literal["runtime_override", "project_only", "core_candidate_only", "reject"]


def apply_runtime_override(context: Dict[str, Any], candidate: Dict[str, Any], scope: ApplyScope) -> Dict[str, Any]:
    runtime_override = candidate.get("runtime_override") if isinstance(candidate.get("runtime_override"), dict) else {}
    applied = False
    blocked_reason = ""

    if scope not in {"runtime_override", "project_only"}:
        blocked_reason = {
            "core_candidate_only": "BLOCKED_RISK_TOO_HIGH",
            "reject": "BLOCKED_REVIEWER_REJECTED",
        }.get(scope, "BLOCKED_REVIEWER_REJECTED")
        return {
            "apply_scope": scope,
            "auto_applied": False,
            "rerun_allowed": False,
            "blocked_reason": blocked_reason,
        }

    try:
        fix_append = runtime_override.get("fix_suggestion_append", "")
        if isinstance(fix_append, str) and fix_append.strip():
            base = str(context.get("fix_suggestion", "") or "").strip()
            context["fix_suggestion"] = (base + " " + fix_append.strip()).strip()
            applied = True

        mapping = {
            "implementation_constraints_append": "implementation_constraints",
            "regression_requirements_append": "regression_requirements",
            "forbidden_change_scope_append": "forbidden_change_scope",
        }
        packet = context.setdefault("story_packet", {})
        for source_key, target_key in mapping.items():
            value = runtime_override.get(source_key, [])
            if isinstance(value, list):
                target_list = packet.setdefault(target_key, [])
                if isinstance(target_list, list):
                    for item in value:
                        text = str(item).strip()
                        if text and text not in target_list:
                            target_list.append(text)
                            applied = True
    except Exception:
        return {
            "apply_scope": scope,
            "auto_applied": False,
            "rerun_allowed": False,
            "blocked_reason": "BLOCKED_OVERRIDE_APPLY_FAILED",
        }

    return {
        "apply_scope": scope,
        "auto_applied": applied,
        "rerun_allowed": True,
        "blocked_reason": "",
    }
