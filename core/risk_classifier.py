from __future__ import annotations

from typing import Any, Dict, Literal

RiskLevel = Literal["low", "medium", "high"]
ApplyScope = Literal["runtime_override", "project_only", "core_candidate_only", "reject"]

CORE_SENSITIVE_HINTS = {
    "SKILL.md",
    "contracts.md",
    "gate_rules.md",
    "change_request_rules.md",
    "forbidden scope",
    "forbidden_scope",
    "ownership",
    "artifact lock",
    "release",
    "state machine",
    "gate semantics",
    "contract",
}

SOFT_OVERRIDE_KEYS = {
    "fix_suggestion_append",
    "implementation_constraints_append",
    "regression_requirements_append",
    "forbidden_change_scope_append",
}


def classify_candidate_risk(context: Dict[str, Any], candidate: Dict[str, Any]) -> Dict[str, Any]:
    affected_files = [str(x) for x in (candidate.get("affected_files") or [])]
    override = candidate.get("runtime_override") if isinstance(candidate.get("runtime_override"), dict) else {}
    override_keys = set(override.keys())
    reason_codes: list[str] = []
    normalized_hints = " ".join(affected_files + [str(candidate.get("summary", "")), str(candidate.get("reason", ""))]).lower()

    if any(hint.lower() in normalized_hints for hint in CORE_SENSITIVE_HINTS):
        return {
            "risk_level": "high",
            "apply_scope": "core_candidate_only",
            "reason_codes": ["RISK_CORE_SEMANTICS_TARGETED"],
            "rerun_allowed": False,
        }

    if not override_keys:
        return {
            "risk_level": "high",
            "apply_scope": "reject",
            "reason_codes": ["RISK_NO_SAFE_OVERRIDE"],
            "rerun_allowed": False,
        }

    if not override_keys.issubset(SOFT_OVERRIDE_KEYS):
        return {
            "risk_level": "high",
            "apply_scope": "core_candidate_only",
            "reason_codes": ["RISK_UNSUPPORTED_OVERRIDE_KEYS"],
            "rerun_allowed": False,
        }

    if context.get("project_mode") == "existing_project":
        forbidden = context.get("story_packet", {}).get("forbidden_change_scope", []) or []
        if forbidden and override.get("forbidden_change_scope_append"):
            reason_codes.append("RISK_BROWNFIELD_SCOPE_TOUCH")
            return {
                "risk_level": "medium",
                "apply_scope": "project_only",
                "reason_codes": reason_codes,
                "rerun_allowed": True,
            }

    reason_codes.append("RISK_SAFE_RUNTIME_OVERRIDE")
    return {
        "risk_level": "low",
        "apply_scope": "runtime_override",
        "reason_codes": reason_codes,
        "rerun_allowed": True,
    }
