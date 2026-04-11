from __future__ import annotations

import json
import re
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List

from core.config import ROLE_MODEL_MAP
from core.db import get_runs_collection


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def _normalize_text(text: str) -> str:
    return re.sub(r"\s+", " ", (text or "").strip())


def _safe_list(value: Any) -> List[Any]:
    return value if isinstance(value, list) else []


def _safe_dict(value: Any) -> Dict[str, Any]:
    return value if isinstance(value, dict) else {}


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
    collection = get_runs_collection()
    doc = build_run_document(result)
    collection.replace_one({"run_id": doc["run_id"]}, doc, upsert=True)
    return doc["run_id"]


def get_recent_runs(limit: int = 20) -> List[Dict[str, Any]]:
    cursor = get_runs_collection().find({}, {"_id": 0}).sort("created_at", -1).limit(limit)
    return list(cursor)


def find_runs_by_task(task: str, limit: int = 10) -> List[Dict[str, Any]]:
    task = _normalize_text(task)
    if not task:
        return []
    cursor = (
        get_runs_collection()
        .find({"task": {"$regex": re.escape(task), "$options": "i"}}, {"_id": 0})
        .sort("created_at", -1)
        .limit(limit)
    )
    return list(cursor)


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
