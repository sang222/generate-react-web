from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import argparse
import json
from pathlib import Path

STORE_DIR = Path('.memory_store')
PROFILES_PATH = STORE_DIR / 'agent_profiles.json'
MEMORIES_PATH = STORE_DIR / 'agent_memories.jsonl'


def _load_profiles() -> dict:
    if not PROFILES_PATH.exists():
        return {}
    try:
        return json.loads(PROFILES_PATH.read_text(encoding='utf-8'))
    except Exception:
        return {}


def _load_memories() -> list[dict]:
    if not MEMORIES_PATH.exists():
        return []
    out = []
    for line in MEMORIES_PATH.read_text(encoding='utf-8').splitlines():
        if not line.strip():
            continue
        try:
            out.append(json.loads(line))
        except Exception:
            continue
    return out


def main() -> int:
    parser = argparse.ArgumentParser(description='Inspect agent profile and memories')
    parser.add_argument('agent_id', help='Agent ID, e.g. developer')
    parser.add_argument('--project-mode', default='new_project', choices=['new_project', 'existing_project'])
    parser.add_argument('--limit', type=int, default=10)
    args = parser.parse_args()

    profiles = _load_profiles()
    profile = profiles.get(args.agent_id, {})
    memories = [m for m in _load_memories() if m.get('agent_id') == args.agent_id and m.get('project_mode') == args.project_mode]
    memories.sort(key=lambda m: (m.get('importance', 0), m.get('title', '')), reverse=True)
    print(json.dumps({'profile': profile, 'memories': memories[:args.limit]}, ensure_ascii=False, indent=2))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
