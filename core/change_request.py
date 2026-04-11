from __future__ import annotations

import json
import uuid
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List


def change_request_root(project_id: str) -> Path:
    return Path('project_state') / project_id / 'change_requests'


def create_change_request(project_id: str, story_id: str, target_artifact: str, reason: str, impact_scope: List[str] | None = None) -> str:
    root = change_request_root(project_id)
    root.mkdir(parents=True, exist_ok=True)
    cr_id = f"CR-{uuid.uuid4().hex[:8]}"
    payload: Dict[str, Any] = {
        'change_request_id': cr_id,
        'project_id': project_id,
        'story_id': story_id,
        'target_artifact': target_artifact,
        'reason': reason,
        'impact_scope': impact_scope or [],
        'approval_status': 'pending',
        'created_at': datetime.now().isoformat(timespec='seconds'),
    }
    path = root / f'{cr_id}.json'
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding='utf-8')
    return str(path)
