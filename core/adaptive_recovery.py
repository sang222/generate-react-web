from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Literal

from core.debug import log_step
from core.llm import call_role_llm
from core.skill_candidates import create_skill_candidate, candidate_dir
from core.utils.json_utils import extract_json_object

ApplyScope = Literal["runtime_override", "project_only", "core_candidate_only", "reject"]


def _now_iso() -> str:
    return datetime.now().astimezone().isoformat()


def recovery_history_root(root: str | Path = ".") -> Path:
    return Path(root) / "skill_history"


def candidate_history_path(root: str | Path = ".") -> Path:
    return recovery_history_root(root) / "candidate_runs.jsonl"


def review_history_path(root: str | Path = ".") -> Path:
    return recovery_history_root(root) / "candidate_reviews.jsonl"


def auto_apply_history_path(root: str | Path = ".") -> Path:
    return recovery_history_root(root) / "auto_applied.jsonl"


def _append_jsonl(path: Path, payload: Dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as fh:
        fh.write(json.dumps(payload, ensure_ascii=False) + "\n")


def should_trigger_adaptive_recovery(context: Dict[str, Any]) -> bool:
    return int(context.get("loop_count", 0) or 0) >= 2 and not bool(context.get("adaptive_recovery_triggered"))


def _recent_failure_snapshot(context: Dict[str, Any]) -> list[dict[str, Any]]:
    history = context.get("history", [])
    if not isinstance(history, list):
        return []
    recent = history[-2:]
    return [item for item in recent if isinstance(item, dict)]


def _build_recovery_prompt(context: Dict[str, Any]) -> str:
    recent = _recent_failure_snapshot(context)
    return f"""
You are the Recovery Meta-Agent.
Your job:
- Read the last 2 failed attempts for the current story.
- Identify the most likely root cause.
- Propose a SMALL runtime recovery patch that is safe.
- Prefer prompt/helper/checklist/runtime override changes.
- Do NOT propose changes to gate logic, release semantics, artifact lock semantics, or state machine semantics.
- If the problem appears to require such high-risk changes, mark apply_scope as core_candidate_only.

Return ONLY valid JSON with this schema:
{{
  "summary": "short summary",
  "reason": "why this candidate is proposed",
  "change_type": "runtime_override|project_only_rule|core_candidate_only",
  "target": "developer_skill|qa_skill|workflow_skill|brownfield_skill",
  "risk_level": "low|medium|high",
  "apply_scope": "runtime_override|project_only|core_candidate_only|reject",
  "runtime_override": {{
    "fix_suggestion_append": "optional string",
    "implementation_constraints_append": ["optional list"],
    "regression_requirements_append": ["optional list"],
    "forbidden_change_scope_append": ["optional list"]
  }},
  "affected_files": ["optional conceptual files or resources"],
  "evaluation": {{
    "confidence": "low|medium|high",
    "notes": ["optional notes"]
  }}
}}

Current story packet:
{json.dumps(context.get('story_packet', {}), ensure_ascii=False, indent=2)}

Current execution_error:
{context.get('execution_error', '')}

Current qa_detail:
{json.dumps(context.get('qa_detail', {}), ensure_ascii=False, indent=2)}

Current fix suggestion:
{context.get('fix_suggestion', '')}

Recent failed attempts:
{json.dumps(recent, ensure_ascii=False, indent=2)}
""".strip()


def _build_cross_review_prompt(context: Dict[str, Any], candidate: Dict[str, Any]) -> str:
    return f"""
You are the Skill Reviewer Agent.
Review the proposed recovery candidate.

Rules:
- Approve runtime_override only for low-risk, temporary changes.
- Approve project_only only for medium-risk localized changes.
- Use core_candidate_only for anything touching core semantics, gate behavior, release behavior, artifact lock semantics, or ownership/state semantics.
- Reject low-quality or irrelevant candidates.
- No human approval is available during runtime.

Return ONLY valid JSON with this schema:
{{
  "review_result": "approved_runtime_override|approved_project_only|core_candidate_only|reject",
  "risk_level": "low|medium|high",
  "apply_scope": "runtime_override|project_only|core_candidate_only|reject",
  "confidence": "low|medium|high",
  "issues": ["list of concerns"],
  "reasoning_summary": "short explanation"
}}

Current story packet:
{json.dumps(context.get('story_packet', {}), ensure_ascii=False, indent=2)}

Candidate proposal:
{json.dumps(candidate, ensure_ascii=False, indent=2)}
""".strip()


def propose_recovery_candidate(context: Dict[str, Any]) -> Dict[str, Any]:
    prompt = _build_recovery_prompt(context)
    raw = call_role_llm("recovery_meta", prompt)
    data = extract_json_object(raw)
    if not data:
        data = {
            "summary": "Fallback runtime recovery candidate",
            "reason": "Model did not return valid JSON; apply a minimal runtime override to reinforce current constraints.",
            "change_type": "runtime_override",
            "target": "brownfield_skill" if context.get("project_mode") == "existing_project" else "developer_skill",
            "risk_level": "low",
            "apply_scope": "runtime_override",
            "runtime_override": {
                "fix_suggestion_append": "Preserve the baseline, stay strictly within allowed change scope, and prioritize buildable minimal changes.",
                "implementation_constraints_append": [
                    "Do not regenerate the project from scratch.",
                    "Prefer additive and local changes only.",
                ],
                "regression_requirements_append": [
                    "Do not break the delivered baseline behavior."
                ],
                "forbidden_change_scope_append": [],
            },
            "affected_files": ["skills/safe-implementation-lane/SKILL.md"],
            "evaluation": {"confidence": "low", "notes": ["Fallback proposal used."]},
        }
    return data


def cross_review_candidate(context: Dict[str, Any], candidate: Dict[str, Any]) -> Dict[str, Any]:
    prompt = _build_cross_review_prompt(context, candidate)
    raw = call_role_llm("skill_reviewer", prompt)
    review = extract_json_object(raw)
    if not review:
        scope = str(candidate.get("apply_scope", "core_candidate_only"))
        review = {
            "review_result": "approved_runtime_override" if scope == "runtime_override" else "approved_project_only" if scope == "project_only" else "core_candidate_only",
            "risk_level": candidate.get("risk_level", "medium"),
            "apply_scope": scope,
            "confidence": "low",
            "issues": ["Fallback cross-review used due to invalid reviewer output."],
            "reasoning_summary": "Fallback reviewer accepted the candidate with conservative scope.",
        }
    return review


def _build_structured_patch_from_candidate(candidate: Dict[str, Any], review: Dict[str, Any]) -> Dict[str, Any]:
    # Keep project/core patching disabled by default in autonomous mode unless explicit safe replacements are later added.
    if review.get("apply_scope") not in {"project_only", "runtime_override"}:
        return {}
    return {"patches": []}


def persist_candidate_and_review(context: Dict[str, Any], candidate: Dict[str, Any], review: Dict[str, Any], root: str | Path = ".") -> str:
    candidate_id = f"cand_{context.get('project_id', 'project')}_{context.get('story_id', 'story')}_{context.get('loop_count', 0)}_{datetime.now().strftime('%Y%m%d%H%M%S')}"
    summary_md = (
        f"# Adaptive Recovery Candidate\n\n"
        f"- Story: {context.get('story_id', '')}\n"
        f"- Project: {context.get('project_id', '')}\n"
        f"- Trigger: failed_twice\n"
        f"- Summary: {candidate.get('summary', '')}\n"
        f"- Reason: {candidate.get('reason', '')}\n"
    )
    evaluation = {
        "trigger": "failed_twice",
        "source_runs": [str(context.get('run_id', ''))],
        "candidate": candidate,
        "cross_review": review,
    }
    patch_diff = (
        f"# runtime_override\n"
        f"apply_scope: {review.get('apply_scope', candidate.get('apply_scope', 'reject'))}\n"
        f"fix_suggestion_append: {((candidate.get('runtime_override') or {}).get('fix_suggestion_append', ''))}\n"
    )
    create_skill_candidate(
        candidate_id=candidate_id,
        target=str(candidate.get("target", "workflow_skill")),
        change_type=str(candidate.get("change_type", "runtime_override")),
        summary=str(candidate.get("summary", "Adaptive recovery candidate")),
        reason=str(candidate.get("reason", "Auto-generated after repeated failures.")),
        affected_files=list(candidate.get("affected_files", []) or []),
        source_runs=[str(context.get("run_id", ""))],
        summary_markdown=summary_md,
        patch_diff=patch_diff,
        evaluation=evaluation,
        structured_patch=_build_structured_patch_from_candidate(candidate, review),
        root=root,
    )
    review_record = {
        "candidate_id": candidate_id,
        "reviewed_by_agent": "skill_reviewer",
        "review_result": review.get("review_result", "reject"),
        "confidence": review.get("confidence", "low"),
        "risk_level": review.get("risk_level", "medium"),
        "issues": review.get("issues", []),
        "apply_scope": review.get("apply_scope", "reject"),
        "reasoning_summary": review.get("reasoning_summary", ""),
        "reviewed_at": _now_iso(),
    }
    (candidate_dir(candidate_id, root) / "cross_review.json").write_text(json.dumps(review_record, ensure_ascii=False, indent=2), encoding="utf-8")
    _append_jsonl(candidate_history_path(root), {
        "candidate_id": candidate_id,
        "timestamp": _now_iso(),
        "project_id": context.get("project_id", ""),
        "story_id": context.get("story_id", ""),
        "trigger": "failed_twice",
        "candidate_summary": candidate.get("summary", ""),
    })
    _append_jsonl(review_history_path(root), review_record)
    return candidate_id


def apply_reviewed_candidate(context: Dict[str, Any], candidate_id: str, candidate: Dict[str, Any], review: Dict[str, Any], root: str | Path = ".") -> Dict[str, Any]:
    scope: ApplyScope = str(review.get("apply_scope", "reject"))  # type: ignore[assignment]
    runtime_override = candidate.get("runtime_override", {}) if isinstance(candidate.get("runtime_override"), dict) else {}
    applied = False
    if scope in {"runtime_override", "project_only"}:
        fix_append = runtime_override.get("fix_suggestion_append", "")
        if isinstance(fix_append, str) and fix_append.strip():
            base = str(context.get("fix_suggestion", "") or "").strip()
            context["fix_suggestion"] = (base + " " + fix_append.strip()).strip()
            applied = True

        for key in ["implementation_constraints_append", "regression_requirements_append", "forbidden_change_scope_append"]:
            value = runtime_override.get(key, [])
            if isinstance(value, list) and value:
                if key == "implementation_constraints_append":
                    target_list = context.setdefault("story_packet", {}).setdefault("implementation_constraints", [])
                elif key == "regression_requirements_append":
                    target_list = context.setdefault("story_packet", {}).setdefault("regression_requirements", [])
                else:
                    target_list = context.setdefault("story_packet", {}).setdefault("forbidden_change_scope", [])
                if isinstance(target_list, list):
                    for item in value:
                        text = str(item).strip()
                        if text and text not in target_list:
                            target_list.append(text)
                            applied = True
    auto_apply_record = {
        "candidate_id": candidate_id,
        "timestamp": _now_iso(),
        "project_id": context.get("project_id", ""),
        "story_id": context.get("story_id", ""),
        "apply_scope": scope,
        "auto_applied": applied,
        "rerun_allowed": scope in {"runtime_override", "project_only"},
        "review_result": review.get("review_result", "reject"),
    }
    _append_jsonl(auto_apply_history_path(root), auto_apply_record)
    context["adaptive_recovery_triggered"] = True
    context["adaptive_recovery_candidate_id"] = candidate_id
    context["adaptive_recovery_scope"] = scope
    context["runtime_override_applied"] = applied
    context.setdefault("skill_candidate_ids", []).append(candidate_id)
    return auto_apply_record


def run_adaptive_recovery(context: Dict[str, Any], root: str | Path = ".") -> Dict[str, Any]:
    log_step("orchestrator", "Adaptive recovery triggered after repeated failures")
    candidate = propose_recovery_candidate(context)
    review = cross_review_candidate(context, candidate)
    candidate_id = persist_candidate_and_review(context, candidate, review, root)
    apply_record = apply_reviewed_candidate(context, candidate_id, candidate, review, root)
    return {
        "candidate_id": candidate_id,
        "candidate": candidate,
        "cross_review": review,
        "apply_record": apply_record,
    }
