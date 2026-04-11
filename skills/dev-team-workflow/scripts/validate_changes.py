from __future__ import annotations

import json
import sys
from pathlib import Path


def main() -> int:
    if len(sys.argv) != 2:
        print('Usage: python validate_changes.py <changes.json>')
        return 2
    path = Path(sys.argv[1])
    if not path.exists():
        print('changes.json not found')
        return 1
    try:
        data = json.loads(path.read_text(encoding='utf-8'))
    except Exception as exc:
        print(f'invalid json: {exc}')
        return 1
    if not isinstance(data, dict):
        print('changes.json must be a JSON object')
        return 1
    required = ['project_mode', 'goal', 'planned_updates']
    missing = [k for k in required if k not in data]
    if missing:
        print('missing keys: ' + ', '.join(missing))
        return 1
    updates = data.get('planned_updates')
    if not isinstance(updates, list):
        print('planned_updates must be a list')
        return 1
    print('changes.json valid')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
