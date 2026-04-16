from __future__ import annotations

import json
import uuid
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List

CR_TYPES = {
    "cross_lane_conflict",
    "protected_scope_violation",
    "shared_path_override",
    "locked_artifact_change",
    "ownership_override",
}

CR_STATUSES = {"pending", "approved", "rejected", "applied", "resolved"}


def change_request_root(project_id: str) -> Path:
    return Path("project_state") / project_id / "change_requests"


def _cr_path(project_id: str, change_request_id: str) -> Path:
    return change_request_root(project_id) / f"{change_request_id}.json"


def create_change_request(
    project_id: str,
    story_id: str,
    target_artifact: str,
    reason: str,
    impact_scope: List[str] | None = None,
    request_type: str = "cross_lane_conflict",
    details: Dict[str, Any] | None = None,
) -> str:
    root = change_request_root(project_id)
    root.mkdir(parents=True, exist_ok=True)
    cr_id = f"CR-{uuid.uuid4().hex[:8]}"
    normalized_type = request_type if request_type in CR_TYPES else "cross_lane_conflict"
    payload: Dict[str, Any] = {
        "change_request_id": cr_id,
        "project_id": project_id,
        "story_id": story_id,
        "request_type": normalized_type,
        "target_artifact": target_artifact,
        "reason": reason,
        "impact_scope": impact_scope or [],
        "details": details or {},
        "approval_status": "pending",
        "created_at": datetime.now().isoformat(timespec="seconds"),
        "updated_at": datetime.now().isoformat(timespec="seconds"),
        "status_history": [
            {
                "status": "pending",
                "timestamp": datetime.now().isoformat(timespec="seconds"),
                "note": "change request created",
            }
        ],
    }
    path = _cr_path(project_id, cr_id)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    return str(path)


def load_change_request(project_id: str, change_request_id: str) -> Dict[str, Any]:
    path = _cr_path(project_id, change_request_id)
    if not path.exists():
        return {}
    return json.loads(path.read_text(encoding="utf-8"))


def update_change_request_status(project_id: str, change_request_id: str, status: str, note: str = "") -> Dict[str, Any]:
    if status not in CR_STATUSES:
        raise ValueError(f"Unsupported change request status: {status}")
    payload = load_change_request(project_id, change_request_id)
    if not payload:
        raise FileNotFoundError(change_request_id)
    payload["approval_status"] = status
    payload["updated_at"] = datetime.now().isoformat(timespec="seconds")
    payload.setdefault("status_history", []).append(
        {
            "status": status,
            "timestamp": payload["updated_at"],
            "note": note,
        }
    )
    _cr_path(project_id, change_request_id).write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    return payload


def list_change_requests(project_id: str) -> List[Dict[str, Any]]:
    root = change_request_root(project_id)
    if not root.exists():
        return []
    items: List[Dict[str, Any]] = []
    for path in sorted(root.glob('*.json')):
        try:
            items.append(json.loads(path.read_text(encoding='utf-8')))
        except Exception:
            continue
    return items


def _paths_match(candidate_path: str, scope_paths: List[str]) -> bool:
    clean = candidate_path.replace('\\', '/').lstrip('./')
    for raw in scope_paths or []:
        prefix = str(raw).replace('\\', '/').lstrip('./')
        if clean == prefix or clean.startswith(prefix.rstrip('/') + '/'):
            return True
    return False


def find_approved_change_requests(project_id: str, story_id: str, request_type: str, changed_paths: List[str]) -> List[Dict[str, Any]]:
    approved: List[Dict[str, Any]] = []
    for item in list_change_requests(project_id):
        if item.get('approval_status') != 'approved':
            continue
        if item.get('request_type') != request_type:
            continue
        if item.get('story_id') not in {'', story_id}:
            continue
        impact_scope = item.get('impact_scope', []) or []
        if not changed_paths:
            approved.append(item)
            continue
        if all(_paths_match(path, impact_scope) for path in changed_paths):
            approved.append(item)
    return approved
