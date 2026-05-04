from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, List

from core.story_state import project_state_root


def ownership_map_path(project_id: str) -> Path:
    return project_state_root(project_id) / 'ownership_map.json'


def ensure_ownership_map(project_id: str) -> Dict[str, Any]:
    path = ownership_map_path(project_id)
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.exists():
        return json.loads(path.read_text(encoding='utf-8'))
    data = {
        'teams': {
            'backend': {'owned_paths': ['backend/', 'api/', 'db/', 'server/', 'shared/contracts/']},
            'frontend': {'owned_paths': ['frontend/', 'web/', 'src/', 'public/', 'shared/ui/', '*-web/']},
        },
        'shared_paths': ['shared/', 'docs/'],
        'lock_rules': {'shared_requires_change_request': True},
    }
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding='utf-8')
    return data


def infer_lane_for_path(path: str, ownership: Dict[str, Any]) -> str:
    clean = path.replace('\\', '/').lstrip('./')
    for lane, info in (ownership.get('teams', {}) or {}).items():
        for prefix in info.get('owned_paths', []) or []:
            if clean.startswith(prefix):
                return lane
    for prefix in ownership.get('shared_paths', []) or []:
        if clean.startswith(prefix):
            return 'shared'
    if clean in {'package.json', 'index.html'} or clean.startswith(('src/', 'public/', 'frontend/', 'web/')) or clean.split('/', 1)[0].endswith('-web'):
        return 'frontend'
    if clean.startswith(('api/', 'backend/', 'server/', 'db/')):
        return 'backend'
    return 'shared'


def lane_files(files: List[Dict[str, str]], lane: str, ownership: Dict[str, Any]) -> List[Dict[str, str]]:
    return [item for item in files if infer_lane_for_path(item.get('path',''), ownership) in {lane, 'shared'}]


def detect_cross_lane_conflicts(fe_files: List[Dict[str, str]], be_files: List[Dict[str, str]], ownership: Dict[str, Any]) -> List[str]:
    conflicts = []
    be_map = {item['path']: item['content'] for item in be_files}
    for item in fe_files:
        path = item['path']
        if path in be_map and be_map[path] != item['content']:
            lane = infer_lane_for_path(path, ownership)
            conflicts.append(f'Both FE and BE changed {path} (ownership={lane})')
    return conflicts
