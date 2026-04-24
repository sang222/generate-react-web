from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path
from typing import Any, Dict

from core.cross_reviewer import cross_review_candidate
from core.llm import call_role_llm
from core.risk_classifier import classify_candidate_risk
from core.runtime_override_manager import apply_runtime_override, resolve_final_apply_scope
from core.skill_candidates import create_skill_candidate, candidate_dir
from core.recovery_history import log_auto_applied, log_candidate_review, log_candidate_run
from core.utils.json_utils import extract_json_object


def _now_suffix() -> str:
    return datetime.now().strftime('%Y%m%d%H%M%S')


def _recent_failure_snapshot(context: Dict[str, Any]) -> list[dict[str, Any]]:
    history = context.get('history', [])
    if not isinstance(history, list):
        return []
    return [item for item in history[-2:] if isinstance(item, dict)]


def _build_recovery_prompt(context: Dict[str, Any]) -> str:
    return f"""
You are the Recovery Meta-Agent.
Read the last 2 failed attempts and propose a SMALL, SAFE recovery candidate.
Prefer runtime overrides or project-only guidance.
Do not propose gate logic changes, release semantic changes, artifact lock semantic changes, or forbidden scope mutations.

Return ONLY valid JSON:
{{
  "summary": "short summary",
  "reason": "why this candidate is proposed",
  "change_type": "runtime_override|project_only_rule|core_candidate_only",
  "target": "developer_skill|qa_skill|workflow_skill|brownfield_skill",
  "runtime_override": {{
    "fix_suggestion_append": "optional string",
    "implementation_constraints_append": ["optional list"],
    "regression_requirements_append": ["optional list"],
    "forbidden_change_scope_append": ["optional list"]
  }},
  "affected_files": ["optional conceptual files or resources"],
  "evaluation": {{"confidence": "low|medium|high", "notes": ["optional notes"]}}
}}

Story packet:
{json.dumps(context.get('story_packet', {}), ensure_ascii=False, indent=2)}

Execution error:
{context.get('execution_error', '')}

QA detail:
{json.dumps(context.get('qa_detail', {}), ensure_ascii=False, indent=2)}

Recent failures:
{json.dumps(_recent_failure_snapshot(context), ensure_ascii=False, indent=2)}
""".strip()


def propose_recovery_candidate(context: Dict[str, Any]) -> Dict[str, Any]:
    raw = call_role_llm('recovery_meta', _build_recovery_prompt(context))
    data = extract_json_object(raw)
    if data:
        return data
    return {
        'summary': 'Fallback runtime recovery candidate',
        'reason': 'Model did not return valid JSON; reinforce baseline-preserving constraints.',
        'change_type': 'runtime_override',
        'target': 'brownfield_skill' if context.get('project_mode') == 'existing_project' else 'developer_skill',
        'runtime_override': {
            'fix_suggestion_append': 'Preserve the baseline, stay within allowed scope, and prefer minimal buildable changes.',
            'implementation_constraints_append': [
                'Do not regenerate the project from scratch.',
                'Prefer additive and local changes only.',
            ],
            'regression_requirements_append': ['Do not break delivered baseline behavior.'],
            'forbidden_change_scope_append': [],
        },
        'affected_files': ['skills/safe-implementation-lane/SKILL.md'],
        'evaluation': {'confidence': 'low', 'notes': ['Fallback proposal used.']},
    }


def _persist_candidate(context: Dict[str, Any], candidate: Dict[str, Any], review: Dict[str, Any], risk: Dict[str, Any], root: str | Path = '.') -> str:
    candidate_id = f"cand_{context.get('project_id','project')}_{context.get('story_id','story')}_{context.get('loop_count',0)}_{_now_suffix()}"
    summary_md = (
        f"# Adaptive Recovery Candidate\n\n"
        f"- Story: {context.get('story_id','')}\n"
        f"- Project: {context.get('project_id','')}\n"
        f"- Summary: {candidate.get('summary','')}\n"
        f"- Reason: {candidate.get('reason','')}\n"
    )
    patch_diff = (
        f"# runtime_override\n"
        f"apply_scope: {review.get('apply_scope', risk.get('apply_scope','reject'))}\n"
        f"fix_suggestion_append: {((candidate.get('runtime_override') or {}).get('fix_suggestion_append',''))}\n"
    )
    evaluation = {
        'trigger': 'failed_twice',
        'source_runs': [str(context.get('run_id',''))],
        'risk_assessment': risk,
        'candidate': candidate,
        'cross_review': review,
    }
    create_skill_candidate(
        candidate_id=candidate_id,
        target=str(candidate.get('target', 'workflow_skill')),
        change_type=str(candidate.get('change_type', 'runtime_override')),
        summary=str(candidate.get('summary', 'Adaptive recovery candidate')),
        reason=str(candidate.get('reason', 'Auto-generated after repeated failures.')),
        affected_files=list(candidate.get('affected_files', []) or []),
        source_runs=[str(context.get('run_id',''))],
        summary_markdown=summary_md,
        patch_diff=patch_diff,
        evaluation=evaluation,
        structured_patch={'patches': []},
        root=root,
    )
    (candidate_dir(candidate_id, root) / 'cross_review.json').write_text(json.dumps(review, ensure_ascii=False, indent=2), encoding='utf-8')
    return candidate_id


def run_recovery_engine(context: Dict[str, Any], root: str | Path = ".") -> Dict[str, Any]:
    candidate = propose_recovery_candidate(context)
    risk = classify_candidate_risk(context, candidate)
    review = cross_review_candidate(context, candidate, risk)
    candidate_id = _persist_candidate(context, candidate, review, risk, root)

    risk_scope = str(risk.get("apply_scope", "reject"))
    review_scope = str(review.get("apply_scope", risk_scope))
    final_scope = resolve_final_apply_scope(risk_scope, review_scope)

    log_candidate_run(
        {
            "candidate_id": candidate_id,
            "project_id": context.get("project_id", ""),
            "story_id": context.get("story_id", ""),
            "failure_pattern": context.get("execution_error", ""),
            "target_skill": candidate.get("target", "workflow_skill"),
            "risk_level": risk.get("risk_level", "high"),
            "reason_codes": risk.get("reason_codes", []),
        },
        root,
    )

    log_candidate_review(
        {
            "candidate_id": candidate_id,
            "project_id": context.get("project_id", ""),
            "story_id": context.get("story_id", ""),
            "reviewer_verdict": review.get("review_result", "reject"),
            "fallback_reason_code": review.get("fallback_reason_code", ""),
            "risk_scope": risk_scope,
            "review_scope": review_scope,
            "final_resolved_scope": final_scope,
            "risk_level": review.get("risk_level", risk.get("risk_level", "high")),
            "reasoning_summary": review.get("reasoning_summary", ""),
        },
        root,
    )

    applied = apply_runtime_override(context, candidate, final_scope)

    log_auto_applied(
        {
            "candidate_id": candidate_id,
            "project_id": context.get("project_id", ""),
            "story_id": context.get("story_id", ""),
            "risk_scope": risk_scope,
            "review_scope": review_scope,
            "final_resolved_scope": applied.get("apply_scope", final_scope),
            "override_result": "applied" if applied.get("auto_applied") else "not_applied",
            "rerun_allowed": bool(applied.get("rerun_allowed", False)),
            "blocked_reason": applied.get("blocked_reason", "")
            or review.get("fallback_reason_code", ""),
        },
        root,
    )

    context["adaptive_recovery_triggered"] = True
    context["adaptive_recovery_candidate_id"] = candidate_id
    context["adaptive_recovery_scope"] = applied.get("apply_scope", "reject")
    context["runtime_override_applied"] = bool(applied.get("auto_applied", False))
    context.setdefault("skill_candidate_ids", []).append(candidate_id)
    context["adaptive_recovery_block_reason"] = applied.get("blocked_reason", "")

    return {
        "candidate_id": candidate_id,
        "candidate": candidate,
        "risk_assessment": risk,
        "cross_review": review,
        "apply_record": applied,
    }
