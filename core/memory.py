from __future__ import annotations

import json
import re
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List

from core.config import ROLE_MODEL_MAP

RUNS_DIR = Path('.runs')
RUNS_INDEX = RUNS_DIR / 'index.jsonl'


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def _normalize_text(text: str) -> str:
    return re.sub(r"\s+", " ", (text or "").strip())


def _safe_list(value: Any) -> List[Any]:
    return value if isinstance(value, list) else []


def _safe_dict(value: Any) -> Dict[str, Any]:
    return value if isinstance(value, dict) else {}


def _ensure_runs_dir() -> None:
    RUNS_DIR.mkdir(parents=True, exist_ok=True)


def _run_path(run_id: str) -> Path:
    return RUNS_DIR / f"{run_id}.json"


def _load_run(path: Path) -> Dict[str, Any]:
    try:
        return json.loads(path.read_text(encoding='utf-8'))
    except Exception:
        return {}


def build_run_summary(result: Dict[str, Any]) -> str:
    task = _normalize_text(result.get("task", ""))
    final_decision = result.get("final_decision", "")
    release_status = result.get("release_status", "")
    severity = result.get("severity", "")
    loop_count = result.get("loop_count", 0)
    execution_error = _normalize_text(result.get("execution_error", ""))

    qa_detail = _safe_dict(result.get("qa_detail"))
    structural_bugs = _safe_list(qa_detail.get("structural_bugs"))
    functional_bugs = _safe_list(qa_detail.get("functional_bugs"))
    prd_gaps = _safe_list(qa_detail.get("prd_gaps"))
    ui_gaps = _safe_list(qa_detail.get("ui_gaps"))

    parts = [
        f"Task: {task}",
        f"Final decision: {final_decision}",
        f"Release status: {release_status}",
        f"Severity: {severity}",
        f"Loop count: {loop_count}",
    ]

    if execution_error:
        parts.append(f"Last execution error: {execution_error}")
    if structural_bugs:
        parts.append(f"Structural bugs: {', '.join(map(str, structural_bugs[:5]))}")
    if functional_bugs:
        parts.append(f"Functional bugs: {', '.join(map(str, functional_bugs[:5]))}")
    if prd_gaps:
        parts.append(f"PRD gaps: {', '.join(map(str, prd_gaps[:5]))}")
    if ui_gaps:
        parts.append(f"UI gaps: {', '.join(map(str, ui_gaps[:5]))}")

    return "\n".join(parts)


def build_run_document(result: Dict[str, Any]) -> Dict[str, Any]:
    qa_detail = _safe_dict(result.get("qa_detail"))
    lead_summary = _safe_dict(result.get("lead_summary"))
    doc: Dict[str, Any] = {
        "run_id": result.get("run_id") or str(uuid.uuid4()),
        "task": _normalize_text(result.get("task", "")),
        "project_mode": result.get("project_mode", "new_project"),
        "project_id": result.get("project_id", ""),
        "epic_id": result.get("epic_id", ""),
        "story_id": result.get("story_id", "story_1"),
        "story_name": result.get("story_name", result.get("story_id", "story_1")),
        "delivery_mode": result.get("delivery_mode", "single_run"),
        "baseline_path": result.get("baseline_path", ""),
        "prd": result.get("prd", ""),
        "design": result.get("design", ""),
        "final_decision": result.get("final_decision", ""),
        "release_status": result.get("release_status", ""),
        "severity": result.get("severity", ""),
        "loop_count": result.get("loop_count", 0),
        "execution_error": _normalize_text(result.get("execution_error", "")),
        "fix_suggestion": result.get("fix_suggestion", ""),
        "qa_detail": {
            "structural_bugs": _safe_list(qa_detail.get("structural_bugs")),
            "functional_bugs": _safe_list(qa_detail.get("functional_bugs")),
            "prd_gaps": _safe_list(qa_detail.get("prd_gaps")),
            "ui_gaps": _safe_list(qa_detail.get("ui_gaps")),
            "regression_bugs": _safe_list(qa_detail.get("regression_bugs")),
        },
        "lead_summary": lead_summary,
        "history": _safe_list(result.get("history")),
        "summary": build_run_summary(result),
        "models": dict(ROLE_MODEL_MAP),
        "project_tree": result.get("project_tree", ""),
        "delivery_manifest": result.get("delivery_manifest", ""),
        "delivery_source": result.get("delivery_source", ""),
        "delivery_root": result.get("delivery_root", ""),
        "next_story": result.get("next_story", ""),
        "created_at": result.get("created_at") or utc_now_iso(),
        "updated_at": utc_now_iso(),
    }
    if result.get("code"):
        doc["code"] = result["code"]
    return doc


def save_run(result: Dict[str, Any]) -> str:
    _ensure_runs_dir()
    doc = build_run_document(result)
    run_id = doc['run_id']
    _run_path(run_id).write_text(json.dumps(doc, ensure_ascii=False, indent=2), encoding='utf-8')

    index = []
    if RUNS_INDEX.exists():
        for line in RUNS_INDEX.read_text(encoding='utf-8').splitlines():
            if not line.strip():
                continue
            try:
                rec = json.loads(line)
            except Exception:
                continue
            if rec.get('run_id') != run_id:
                index.append(rec)
    index.insert(0, {
        'run_id': run_id,
        'created_at': doc.get('created_at', ''),
        'project_id': doc.get('project_id', ''),
        'epic_id': doc.get('epic_id', ''),
        'story_id': doc.get('story_id', ''),
        'task': doc.get('task', ''),
        'final_decision': doc.get('final_decision', ''),
        'release_status': doc.get('release_status', ''),
        'severity': doc.get('severity', ''),
        'summary': doc.get('summary', ''),
    })
    RUNS_INDEX.write_text('\n'.join(json.dumps(item, ensure_ascii=False) for item in index) + ('\n' if index else ''), encoding='utf-8')
    return run_id


def get_recent_runs(limit: int = 20) -> List[Dict[str, Any]]:
    _ensure_runs_dir()
    records: List[Dict[str, Any]] = []
    if RUNS_INDEX.exists():
        for line in RUNS_INDEX.read_text(encoding='utf-8').splitlines():
            if not line.strip():
                continue
            try:
                index_item = json.loads(line)
            except Exception:
                continue
            run = _load_run(_run_path(index_item.get('run_id', '')))
            if run:
                records.append(run)
            if len(records) >= limit:
                break
    if records:
        return records
    files = sorted(RUNS_DIR.glob('*.json'), key=lambda p: p.stat().st_mtime, reverse=True)
    return [_load_run(p) for p in files[:limit] if _load_run(p)]


def find_run_by_id(run_id: str) -> Dict[str, Any] | None:
    path = _run_path(run_id)
    if not path.exists():
        return None
    run = _load_run(path)
    return run or None


def clear_runs() -> int:
    _ensure_runs_dir()
    count = 0
    for path in RUNS_DIR.glob('*.json'):
        path.unlink(missing_ok=True)
        count += 1
    RUNS_INDEX.unlink(missing_ok=True)
    return count


def find_runs_by_task(task: str, limit: int = 10) -> List[Dict[str, Any]]:
    task = _normalize_text(task).lower()
    if not task:
        return []
    matched: List[Dict[str, Any]] = []
    for run in get_recent_runs(limit=200):
        if task in _normalize_text(run.get('task', '')).lower():
            matched.append(run)
        if len(matched) >= limit:
            break
    return matched


def summarize_runs_for_debug(task: str, limit: int = 5) -> str:
    runs = find_runs_by_task(task, limit=limit)
    if not runs:
        return "[]"
    compact = []
    for run in runs:
        compact.append(
            {
                "task": run.get("task", ""),
                "final_decision": run.get("final_decision", ""),
                "release_status": run.get("release_status", ""),
                "severity": run.get("severity", ""),
                "loop_count": run.get("loop_count", 0),
                "execution_error": run.get("execution_error", ""),
                "summary": run.get("summary", ""),
            }
        )
    return json.dumps(compact, ensure_ascii=False, indent=2)
