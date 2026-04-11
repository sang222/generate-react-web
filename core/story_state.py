from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List

from core.config import get_system_target, load_module_config

PROJECT_STATE_DIR = Path("project_state")


def _safe_story_name(story_id: str) -> str:
    return story_id


def project_state_root(project_id: str) -> Path:
    return PROJECT_STATE_DIR / project_id


def epic_context_path(project_id: str) -> Path:
    return project_state_root(project_id) / "epic_context.json"


def delivery_index_path(project_id: str) -> Path:
    return project_state_root(project_id) / "delivery_index.json"


def artifact_locks_path(project_id: str) -> Path:
    return project_state_root(project_id) / 'artifact_locks.json'


def _default_story(project_id: str, epic_id: str, story_id: str, story_name: str, depends_on: List[str] | None = None) -> Dict[str, Any]:
    return {
        'project_id': project_id,
        'epic_id': epic_id,
        'story_id': story_id,
        'story_name': story_name or _safe_story_name(story_id),
        'story_type': 'feature',
        'business_goal': f'Deliver {story_name or story_id}',
        'status': 'pending',
        'ready_status': 'draft',
        'depends_on': depends_on or [],
        'in_scope': [],
        'out_of_scope': [],
        'acceptance_criteria': [
            f'{story_id} is implemented on top of the current baseline.',
            'Build passes.',
        ],
    }


def ensure_epic_context(project_id: str, epic_id: str, story_id: str, story_name: str, depends_on: List[str] | None = None) -> Dict[str, Any]:
    path = epic_context_path(project_id)
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.exists():
        data = json.loads(path.read_text(encoding='utf-8'))
    else:
        data = {
            'project_id': project_id,
            'epic_id': epic_id,
            'epic_name': epic_id,
            'epic_goal': '',
            'stories': [],
        }
    stories = data.setdefault('stories', [])
    found = None
    for story in stories:
        if story.get('story_id') == story_id:
            found = story
            break
    if found is None:
        found = _default_story(project_id, epic_id, story_id, story_name, depends_on)
        stories.append(found)
    else:
        found.setdefault('story_name', story_name or _safe_story_name(story_id))
        found.setdefault('story_type', 'feature')
        found.setdefault('business_goal', f'Deliver {story_name or story_id}')
        found.setdefault('status', 'pending')
        found.setdefault('ready_status', 'draft')
        found.setdefault('acceptance_criteria', [f'{story_id} is implemented on top of the current baseline.', 'Build passes.'])
        found.setdefault('in_scope', [])
        found.setdefault('out_of_scope', [])
        if story_name:
            found['story_name'] = story_name
        if depends_on is not None:
            found['depends_on'] = depends_on
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding='utf-8')
    return data


def load_epic_context(project_id: str) -> Dict[str, Any]:
    path = epic_context_path(project_id)
    if not path.exists():
        return {}
    return json.loads(path.read_text(encoding='utf-8'))


def get_story_definition(project_id: str, story_id: str) -> Dict[str, Any]:
    epic = load_epic_context(project_id)
    for story in epic.get('stories', []):
        if story.get('story_id') == story_id:
            return story
    return {}


def ensure_delivery_index(project_id: str, epic_id: str, epic_context: Dict[str, Any]) -> Dict[str, Any]:
    path = delivery_index_path(project_id)
    path.parent.mkdir(parents=True, exist_ok=True)
    stories = []
    for story in epic_context.get('stories', []):
        stories.append({
            'story_id': story.get('story_id', ''),
            'story_name': story.get('story_name', ''),
            'status': story.get('status', 'pending'),
            'manifest_path': None,
            'depends_on': story.get('depends_on', []),
        })
    if path.exists():
        data = json.loads(path.read_text(encoding='utf-8'))
        existing = {s.get('story_id'): s for s in data.get('stories', [])}
        merged = []
        for story in stories:
            merged.append({**story, **existing.get(story['story_id'], {})})
        data['stories'] = merged
    else:
        data = {
            'project_id': project_id,
            'epic_id': epic_id,
            'current_delivered_story': None,
            'delivered_story_count': 0,
            'total_story_count': len(stories),
            'next_ready_story': None,
            'stories': stories,
        }
    data['total_story_count'] = len(data.get('stories', []))
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding='utf-8')
    return data


def update_delivery_index(project_id: str, epic_id: str, story_id: str, story_name: str, manifest_path: str) -> Dict[str, Any]:
    epic = load_epic_context(project_id)
    data = ensure_delivery_index(project_id, epic_id, epic)
    stories = data.setdefault('stories', [])
    found = None
    for story in stories:
        if story.get('story_id') == story_id:
            found = story
            break
    if found is None:
        found = {'story_id': story_id, 'story_name': story_name, 'status': 'delivered', 'manifest_path': manifest_path, 'depends_on': []}
        stories.append(found)
    found['story_name'] = story_name
    found['status'] = 'delivered'
    found['manifest_path'] = manifest_path
    data['current_delivered_story'] = {
        'story_id': story_id,
        'story_name': story_name,
        'delivered_at': datetime.now().isoformat(timespec='seconds'),
    }
    delivered = [s for s in stories if s.get('status') == 'delivered']
    data['delivered_story_count'] = len(delivered)
    next_ready = None
    delivered_ids = {s['story_id'] for s in delivered}
    for story in epic.get('stories', []):
        if story.get('story_id') in delivered_ids:
            continue
        deps = set(story.get('depends_on', []) or [])
        if deps.issubset(delivered_ids):
            next_ready = {'story_id': story.get('story_id'), 'story_name': story.get('story_name')}
            break
    data['next_ready_story'] = next_ready
    path = delivery_index_path(project_id)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding='utf-8')
    return data


def resolve_story_dependencies(project_id: str, story_id: str) -> List[str]:
    story = get_story_definition(project_id, story_id)
    return list(story.get('depends_on', []) or [])


def find_baseline_from_dependencies(project_id: str, story_id: str, deliveries_dir: Path) -> str:
    deps = resolve_story_dependencies(project_id, story_id)
    for dep in reversed(deps):
        candidate = deliveries_dir / project_id / dep / 'source'
        if candidate.exists():
            return str(candidate)
    return ''


def ensure_artifact_locks(project_id: str) -> Dict[str, Any]:
    path = artifact_locks_path(project_id)
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.exists():
        return json.loads(path.read_text(encoding='utf-8'))
    data = {'project_id': project_id, 'locked_artifacts': []}
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding='utf-8')
    return data


def lock_artifacts(project_id: str, story_id: str, gate_name: str, artifact_paths: List[str]) -> Dict[str, Any]:
    data = ensure_artifact_locks(project_id)
    locked = data.setdefault('locked_artifacts', [])
    for p in artifact_paths:
        if not any(item.get('path') == p for item in locked):
            locked.append({
                'path': p,
                'story_id': story_id,
                'gate': gate_name,
                'state': 'locked',
                'locked_at': datetime.now().isoformat(timespec='seconds'),
            })
    path = artifact_locks_path(project_id)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding='utf-8')
    return data


def classify_project_level(story: Dict[str, Any], system_target: Dict[str, Any], baseline_path: str = "") -> Dict[str, Any]:
    in_scope = story.get("in_scope", []) or []
    acceptance = story.get("acceptance_criteria", []) or []
    deps = story.get("depends_on", []) or []
    backend = system_target.get("backend_framework") or ""
    system_type = system_target.get("system_type", "web_app")

    score = 0
    reasons: List[str] = []
    if system_type == "fullstack_website":
        score += 2
        reasons.append("fullstack target")
    if baseline_path:
        score += 1
        reasons.append("existing baseline")
    if backend:
        score += 1
        reasons.append(f"backend={backend}")
    if len(in_scope) >= 4:
        score += 1
        reasons.append("broad in-scope set")
    if len(acceptance) >= 4:
        score += 1
        reasons.append("many acceptance criteria")
    if deps:
        score += 1
        reasons.append("story has dependencies")

    if score <= 1:
        level = 0
        profile = "micro"
    elif score == 2:
        level = 1
        profile = "small"
    elif score == 3:
        level = 2
        profile = "standard"
    elif score <= 5:
        level = 3
        profile = "large"
    else:
        level = 4
        profile = "enterprise"

    return {"level": level, "profile": profile, "reasoning": reasons}


def default_story_packet(project_id: str, epic_id: str, story_id: str, story_name: str, baseline_path: str, ownership_map_path: str, task: str) -> Dict[str, Any]:
    story = get_story_definition(project_id, story_id)
    system_target = get_system_target(load_module_config())
    sizing = classify_project_level(story, system_target, baseline_path)
    return {
        'project_id': project_id,
        'epic_id': epic_id,
        'story_id': story_id,
        'story_name': story_name,
        'story_type': story.get('story_type', 'feature'),
        'business_goal': story.get('business_goal', task),
        'request_type': 'story_delivery',
        'baseline_path': baseline_path,
        'delivery_target': f'deliveries/{project_id}/{story_id}/source',
        'ownership_map_path': ownership_map_path,
        'goal': task,
        'depends_on': story.get('depends_on', []),
        'acceptance_criteria': story.get('acceptance_criteria', []),
        'in_scope': story.get('in_scope', []),
        'out_of_scope': story.get('out_of_scope', []),
        'regression_requirements': [
            'Do not break delivered baseline behavior.',
            'Preserve required files and shared layout.',
        ],
        'implementation_constraints': [
            'Modify the current baseline instead of regenerating from scratch when baseline exists.',
            'Respect ownership map and locked artifacts.',
        ],
        'system_target': system_target,
        'project_level': sizing['level'],
        'delivery_profile': sizing['profile'],
        'level_reasoning': sizing['reasoning'],
        'frontend': {'stack': system_target['frontend_stack']},
        'backend': {
            'language': system_target['backend_language'],
            'framework': system_target['backend_framework'],
            'build_tool': system_target['backend_build_tool'],
        },
        'database': {
            'engine': system_target['database_engine'],
            'orm': system_target['database_orm'],
        },
    }
