from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict

from core.llm import call_role_llm
from core.utils.json_utils import extract_json_object

RUBRIC_PATH = Path("skills") / "skill-reviewer" / "rubric.md"


def _load_rubric() -> str:
    if RUBRIC_PATH.exists():
        return RUBRIC_PATH.read_text(encoding="utf-8")
    return ""


def build_cross_review_prompt(context: Dict[str, Any], candidate: Dict[str, Any], risk_assessment: Dict[str, Any]) -> str:
    evidence = {
        "project_mode": context.get("project_mode", ""),
        "story_packet": context.get("story_packet", {}),
        "execution_error": context.get("execution_error", ""),
        "qa_detail": context.get("qa_detail", {}),
        "recent_failures": (context.get("history", []) or [])[-2:],
    }
    rubric = _load_rubric()
    return f"""
You are the Skill Reviewer Agent.
Review the proposed adaptive recovery candidate independently.
Do not trust the candidate summary by default. Use the evidence and rubric.

Rubric:
{rubric}

Deterministic risk assessment from the policy engine:
{json.dumps(risk_assessment, ensure_ascii=False, indent=2)}

Evidence:
{json.dumps(evidence, ensure_ascii=False, indent=2)}

Candidate proposal:
{json.dumps(candidate, ensure_ascii=False, indent=2)}

Return ONLY valid JSON with this schema:
{{
  "review_result": "approved_runtime_override|approved_project_only|core_candidate_only|reject",
  "risk_level": "low|medium|high",
  "apply_scope": "runtime_override|project_only|core_candidate_only|reject",
  "confidence": "low|medium|high",
  "issues": ["list of concerns"],
  "reasoning_summary": "short explanation",
  "rubric_scores": {{
    "scope_safety": 0|1|2,
    "contract_safety": 0|1|2,
    "brownfield_boundary_safety": 0|1|2,
    "regression_likelihood": 0|1|2,
    "patch_target_correctness": 0|1|2
  }}
}}
""".strip()


def cross_review_candidate(context: Dict[str, Any], candidate: Dict[str, Any], risk_assessment: Dict[str, Any]) -> Dict[str, Any]:
    raw = call_role_llm("skill_reviewer", build_cross_review_prompt(context, candidate, risk_assessment))
    review = extract_json_object(raw)
    if review:
        return review

    default_scope = risk_assessment.get("apply_scope", "reject")
    review_result = {
        "runtime_override": "approved_runtime_override",
        "project_only": "approved_project_only",
        "core_candidate_only": "core_candidate_only",
        "reject": "reject",
    }.get(default_scope, "reject")
    return {
        "review_result": review_result,
        "risk_level": risk_assessment.get("risk_level", "high"),
        "apply_scope": default_scope,
        "confidence": "low",
        "issues": ["Fallback reviewer used due to invalid reviewer output."],
        "reasoning_summary": "Fallback reviewer followed deterministic risk policy.",
        "rubric_scores": {
            "scope_safety": 1,
            "contract_safety": 1,
            "brownfield_boundary_safety": 1,
            "regression_likelihood": 1,
            "patch_target_correctness": 1,
        },
    }
