from __future__ import annotations

import argparse
import json
from pathlib import Path


def _story_root(root: Path, story_id: str) -> Path:
    return root / "stories" / story_id


def _read_yamlish(path: Path) -> dict:
    data = {}
    if not path.exists():
        return data
    for raw in path.read_text(encoding='utf-8').splitlines():
        line = raw.strip()
        if line and ':' in line and not line.startswith('#'):
            k, v = line.split(':', 1)
            data[k.strip()] = v.strip().strip('"')
    return data


def _load_gate_state(state_dir: Path, story_id: str) -> dict:
    story_path = state_dir / 'gates' / f'{story_id}.json'
    if story_path.exists():
        return json.loads(story_path.read_text(encoding='utf-8'))
    summary_path = state_dir / 'gate_state.json'
    if summary_path.exists():
        return json.loads(summary_path.read_text(encoding='utf-8'))
    return {}


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument('--project-id', required=True)
    args = parser.parse_args()
    state_dir = Path('project_state') / args.project_id
    delivery_index = state_dir / 'delivery_index.json'
    epic_context = state_dir / 'epic_context.json'
    workflow_status = state_dir / 'workflow_status.yaml'
    if not delivery_index.exists():
        print('No delivery index found.')
        return 1
    idx = json.loads(delivery_index.read_text(encoding='utf-8'))
    epic = json.loads(epic_context.read_text(encoding='utf-8')) if epic_context.exists() else {}
    status_lines = _read_yamlish(workflow_status)
    current_story_id = status_lines.get('story_id', '') or (idx.get('current_delivered_story') or {}).get('story_id', '')
    gate = _load_gate_state(state_dir, current_story_id) if current_story_id else {}
    print(f"Project: {idx.get('project_id', '')}")
    print(f"Epic: {idx.get('epic_id', '')}")
    print(f"Total stories: {idx.get('total_story_count', len(idx.get('stories', [])))}")
    print(f"Delivered stories: {idx.get('delivered_story_count', 0)}")
    current = idx.get('current_delivered_story') or {}
    print(f"Current delivered story: {current.get('story_id', '')} {current.get('story_name', '')}")
    next_ready = idx.get('next_ready_story') or {}
    print(f"Next ready story: {next_ready.get('story_id', '')} {next_ready.get('story_name', '')}")
    if status_lines:
        print(f"Project level: {status_lines.get('project_level', '')} ({status_lines.get('delivery_profile', '')})")
        print(f"Recommendation: {status_lines.get('recommendation', '')}")
    if gate:
        print(f"Current gate: {gate.get('current_gate', '')}")
        print(f"Passed gates: {', '.join(gate.get('passed_gates', []))}")
        print(f"Last failed gate: {gate.get('last_failed_gate', '')}")
    print('Stories:')
    story_defs = {s.get('story_id'): s for s in epic.get('stories', [])}
    for story in idx.get('stories', []):
        sid = story.get('story_id', '')
        meta = story_defs.get(sid, {})
        deps = ', '.join(meta.get('depends_on', []) or [])
        gate_state = _load_gate_state(state_dir, sid)
        print(f"- {sid}: {story.get('status', '')} | ready_status={meta.get('ready_status', '')} | deps=[{deps}] | gate={gate_state.get('current_gate', '')} | manifest={story.get('manifest_path')}")
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
