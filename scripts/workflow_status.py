from __future__ import annotations

import argparse
import json
from pathlib import Path


def _read_json(path: Path) -> dict:
    if not path.exists():
        return {}
    return json.loads(path.read_text(encoding="utf-8"))


def _story_root(root: Path, story_id: str) -> Path:
    return root / "stories" / story_id


def _read_yamlish(path: Path) -> dict:
    data = {}
    if not path.exists():
        return data
    for raw in path.read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if not line or line.startswith('#') or ':' not in line:
            continue
        key, value = line.split(':', 1)
        data[key.strip()] = value.strip().strip('"')
    return data


def _load_story_gate(root: Path, story_id: str) -> dict:
    story_path = root / 'gates' / f'{story_id}.json'
    if story_path.exists():
        return _read_json(story_path)
    return _read_json(root / 'gate_state.json')


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument('--project-id', required=True)
    args = parser.parse_args()
    root = Path('project_state') / args.project_id
    if not root.exists():
        print('No project state found.')
        return 1

    epic = _read_json(root / 'epic_context.json')
    delivery = _read_json(root / 'delivery_index.json')
    locks = _read_json(root / 'artifact_locks.json')
    status = _read_yamlish(root / 'workflow_status.yaml')
    current_story_id = status.get('story_id', '')
    story_root = _story_root(root, current_story_id) if current_story_id else root
    readiness = _read_json(story_root / 'brownfield_readiness_report.json')
    impact = _read_json(story_root / 'change_impact_report.json')
    gates = _load_story_gate(root, current_story_id) if current_story_id else _read_json(root / 'gate_state.json')

    print(f"Project: {args.project_id}")
    print(f"Epic: {epic.get('epic_id', '')} {epic.get('epic_name', '')}")
    print(f"Current story: {status.get('story_id', '')} {status.get('story_name', '')}")
    print(f"Project level: {status.get('project_level', '')} ({status.get('delivery_profile', '')})")
    print(f"Current gate: {status.get('current_gate', gates.get('current_gate', ''))}")
    print(f"Last failed gate: {gates.get('last_failed_gate', '')}")
    current = delivery.get('current_delivered_story') or {}
    print(f"Current delivered story: {current.get('story_id', '')} {current.get('story_name', '')}")
    next_story = delivery.get('next_ready_story') or {}
    print(f"Next ready story: {next_story.get('story_id', '')} {next_story.get('story_name', '')}")
    print(f"Locked artifacts: {len((locks.get('locked_artifacts') or locks.get('artifacts') or []))}")
    print(f"Recommendation: {status.get('recommendation', '')}")
    if readiness:
        print(f"Brownfield ready: {readiness.get('ready', False)}")
        if readiness.get('missing_information'):
            print(f"Missing info: {', '.join(readiness.get('missing_information', []))}")
    if impact:
        print(f"Affected modules: {len(impact.get('affected_modules', []) or [])}")
    print('Story statuses:')
    story_defs = {s.get('story_id'): s for s in epic.get('stories', [])}
    for story in (delivery.get('stories') or []):
        sid = story.get('story_id', '')
        meta = story_defs.get(sid, {})
        deps = ', '.join(meta.get('depends_on', []) or [])
        gate_state = _load_story_gate(root, sid)
        print(f"- {sid}: {story.get('status', '')} | ready_status={meta.get('ready_status', '')} | deps=[{deps}] | gate={gate_state.get('current_gate', '')} | last_failed={gate_state.get('last_failed_gate', '')}")
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
