from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path
from typing import Any, Iterable, Literal, TypedDict

CandidateDecision = Literal[
    "reject",
    "revise",
    "approve_for_project_only",
    "promote_to_core",
]

VALID_DECISIONS: tuple[CandidateDecision, ...] = (
    "reject",
    "revise",
    "approve_for_project_only",
    "promote_to_core",
)


class SkillCandidateMetadata(TypedDict, total=False):
    candidate_id: str
    target: str
    change_type: str
    summary: str
    reason: str
    affected_files: list[str]
    source_runs: list[str]
    status: str
    created_at: str


class ReviewDecisionRecord(TypedDict, total=False):
    candidate_id: str
    decision: CandidateDecision
    reviewed_by: str
    reviewed_at: str
    note: str
    applied: bool
    apply_mode: str


class PromotionLogRecord(TypedDict, total=False):
    candidate_id: str
    decision: CandidateDecision
    reviewed_by: str
    reviewed_at: str
    note: str
    applied: bool
    apply_mode: str
    target: str
    summary: str


def _now_iso() -> str:
    return datetime.now().astimezone().isoformat()


def _read_json(path: Path, default: Any) -> Any:
    if not path.exists():
        return default
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return default


def _write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def skill_candidates_root(root: str | Path = ".") -> Path:
    return Path(root) / "skill_candidates"


def skill_registry_root(root: str | Path = ".") -> Path:
    return Path(root) / "skill_registry"


def candidate_dir(candidate_id: str, root: str | Path = ".") -> Path:
    return skill_candidates_root(root) / candidate_id


def candidate_metadata_path(candidate_id: str, root: str | Path = ".") -> Path:
    return candidate_dir(candidate_id, root) / "metadata.json"


def candidate_summary_path(candidate_id: str, root: str | Path = ".") -> Path:
    return candidate_dir(candidate_id, root) / "summary.md"


def candidate_patch_path(candidate_id: str, root: str | Path = ".") -> Path:
    return candidate_dir(candidate_id, root) / "patch.diff"


def candidate_structured_patch_path(candidate_id: str, root: str | Path = ".") -> Path:
    return candidate_dir(candidate_id, root) / "structured_patch.json"


def candidate_evaluation_path(candidate_id: str, root: str | Path = ".") -> Path:
    return candidate_dir(candidate_id, root) / "evaluation.json"


def candidate_review_decision_path(candidate_id: str, root: str | Path = ".") -> Path:
    return candidate_dir(candidate_id, root) / "review_decision.json"


def promotion_log_path(root: str | Path = ".") -> Path:
    return skill_registry_root(root) / "promotion_log.json"


def list_skill_candidates(root: str | Path = ".") -> list[SkillCandidateMetadata]:
    items: list[SkillCandidateMetadata] = []
    candidates_dir = skill_candidates_root(root)
    if not candidates_dir.exists():
        return items

    for item in sorted(candidates_dir.iterdir()):
        if not item.is_dir():
            continue
        meta = _read_json(item / "metadata.json", {})
        if isinstance(meta, dict):
            if "candidate_id" not in meta:
                meta["candidate_id"] = item.name
            items.append(meta)
    return items


def load_skill_candidate(candidate_id: str, root: str | Path = ".") -> dict[str, Any]:
    base = candidate_dir(candidate_id, root)
    if not base.exists():
        raise FileNotFoundError(f"Skill candidate not found: {candidate_id}")

    metadata = _read_json(base / "metadata.json", {})
    evaluation = _read_json(base / "evaluation.json", {})
    review_decision = _read_json(base / "review_decision.json", {})
    summary = (base / "summary.md").read_text(encoding="utf-8") if (base / "summary.md").exists() else ""
    patch_diff = (base / "patch.diff").read_text(encoding="utf-8") if (base / "patch.diff").exists() else ""
    structured_patch = _read_json(base / "structured_patch.json", {})

    return {
        "candidate_id": candidate_id,
        "metadata": metadata,
        "summary": summary,
        "patch_diff": patch_diff,
        "structured_patch": structured_patch,
        "evaluation": evaluation,
        "review_decision": review_decision,
        "dir": str(base),
    }


def create_skill_candidate(
    *,
    candidate_id: str,
    target: str,
    change_type: str,
    summary: str,
    reason: str,
    affected_files: list[str] | None = None,
    source_runs: list[str] | None = None,
    summary_markdown: str = "",
    patch_diff: str = "",
    evaluation: dict[str, Any] | None = None,
    structured_patch: dict[str, Any] | None = None,
    root: str | Path = ".",
) -> Path:
    base = candidate_dir(candidate_id, root)
    base.mkdir(parents=True, exist_ok=True)

    metadata: SkillCandidateMetadata = {
        "candidate_id": candidate_id,
        "target": target,
        "change_type": change_type,
        "summary": summary,
        "reason": reason,
        "affected_files": affected_files or [],
        "source_runs": source_runs or [],
        "status": "proposed",
        "created_at": _now_iso(),
    }
    _write_json(base / "metadata.json", metadata)

    if summary_markdown:
        (base / "summary.md").write_text(summary_markdown, encoding="utf-8")
    if patch_diff:
        (base / "patch.diff").write_text(patch_diff, encoding="utf-8")
    if evaluation is not None:
        _write_json(base / "evaluation.json", evaluation)
    if structured_patch is not None:
        _write_json(base / "structured_patch.json", structured_patch)
    return base


def _apply_replace_patch(root: Path, file_path: str, changes: Iterable[dict[str, Any]]) -> bool:
    target = root / file_path
    if not target.exists():
        return False

    content = target.read_text(encoding="utf-8")
    original = content
    for change in changes:
        if change.get("type") != "replace":
            continue
        find = str(change.get("find", ""))
        replace = str(change.get("replace", ""))
        if not find:
            continue
        content = content.replace(find, replace, 1)

    if content != original:
        target.write_text(content, encoding="utf-8")
        return True
    return False


def apply_structured_candidate_patch(candidate_id: str, root: str | Path = ".") -> tuple[bool, list[str]]:
    candidate = load_skill_candidate(candidate_id, root)
    structured = candidate.get("structured_patch") or {}
    if not isinstance(structured, dict):
        return False, []

    project_root = Path(root)
    applied_files: list[str] = []

    patches = structured.get("patches", [])
    if not isinstance(patches, list):
        return False, []

    for patch in patches:
        if not isinstance(patch, dict):
            continue
        file_path = patch.get("file")
        changes = patch.get("changes", [])
        if isinstance(file_path, str) and isinstance(changes, list):
            if _apply_replace_patch(project_root, file_path, changes):
                applied_files.append(file_path)

    return bool(applied_files), applied_files


def review_skill_candidate(
    candidate_id: str,
    decision: CandidateDecision,
    *,
    reviewed_by: str = "human",
    note: str = "",
    root: str | Path = ".",
) -> ReviewDecisionRecord:
    if decision not in VALID_DECISIONS:
        raise ValueError(f"Invalid decision: {decision}")

    candidate = load_skill_candidate(candidate_id, root)
    metadata = candidate.get("metadata", {}) if isinstance(candidate.get("metadata"), dict) else {}

    applied = False
    apply_mode = "none"
    if decision in {"approve_for_project_only", "promote_to_core"}:
        applied, applied_files = apply_structured_candidate_patch(candidate_id, root)
        if applied:
            apply_mode = "structured_patch"
            if note:
                note = f"{note}\nApplied files: {', '.join(applied_files)}"
            else:
                note = f"Applied files: {', '.join(applied_files)}"

    record: ReviewDecisionRecord = {
        "candidate_id": candidate_id,
        "decision": decision,
        "reviewed_by": reviewed_by,
        "reviewed_at": _now_iso(),
        "note": note,
        "applied": applied,
        "apply_mode": apply_mode,
    }
    _write_json(candidate_review_decision_path(candidate_id, root), record)

    if metadata:
        metadata["status"] = {
            "reject": "rejected",
            "revise": "revision_requested",
            "approve_for_project_only": "approved_for_project_only",
            "promote_to_core": "promoted_to_core",
        }[decision]
        _write_json(candidate_metadata_path(candidate_id, root), metadata)

    if decision in {"approve_for_project_only", "promote_to_core"}:
        log_path = promotion_log_path(root)
        log_payload = _read_json(log_path, {"records": []})
        records = log_payload.get("records", []) if isinstance(log_payload, dict) else []
        if not isinstance(records, list):
            records = []
        records.append(
            PromotionLogRecord(
                candidate_id=candidate_id,
                decision=decision,
                reviewed_by=reviewed_by,
                reviewed_at=record["reviewed_at"],
                note=note,
                applied=applied,
                apply_mode=apply_mode,
                target=str(metadata.get("target", "")),
                summary=str(metadata.get("summary", "")),
            )
        )
        _write_json(log_path, {"records": records})

    return record


def render_skill_candidate(candidate_id: str, root: str | Path = ".") -> str:
    candidate = load_skill_candidate(candidate_id, root)
    metadata = candidate.get("metadata", {}) if isinstance(candidate.get("metadata"), dict) else {}
    evaluation = candidate.get("evaluation", {}) if isinstance(candidate.get("evaluation"), dict) else {}
    review_decision = candidate.get("review_decision", {}) if isinstance(candidate.get("review_decision"), dict) else {}

    lines = [
        f"Candidate: {candidate_id}",
        f"Target: {metadata.get('target', '')}",
        f"Status: {metadata.get('status', '')}",
        f"Type: {metadata.get('change_type', '')}",
        f"Summary: {metadata.get('summary', '')}",
        f"Reason: {metadata.get('reason', '')}",
        "",
        "Affected files:",
    ]
    for file_path in metadata.get("affected_files", []) or []:
        lines.append(f"- {file_path}")

    if metadata.get("source_runs"):
        lines.extend(["", "Source runs:"])
        for run_id in metadata.get("source_runs", []):
            lines.append(f"- {run_id}")

    if evaluation:
        lines.extend(["", "Evaluation:", json.dumps(evaluation, ensure_ascii=False, indent=2)])

    if review_decision:
        lines.extend(["", "Review decision:", json.dumps(review_decision, ensure_ascii=False, indent=2)])

    summary_text = str(candidate.get("summary", "") or "").strip()
    if summary_text:
        lines.extend(["", "Summary markdown:", summary_text])

    patch_diff = str(candidate.get("patch_diff", "") or "").strip()
    if patch_diff:
        lines.extend(["", "Patch diff:", patch_diff])

    return "\n".join(lines).strip() + "\n"
