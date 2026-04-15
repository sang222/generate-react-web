from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from core.memory import get_recent_runs


def main() -> None:
    runs = get_recent_runs(limit=20)
    if not runs:
        print('No runs found.')
        return
    for idx, run in enumerate(runs, start=1):
        print('=' * 100)
        print(f'#{idx}')
        print('run_id         :', run.get('run_id', ''))
        print('created_at     :', run.get('created_at', ''))
        print('task           :', run.get('task', ''))
        print('final_decision :', run.get('final_decision', ''))
        print('release_status :', run.get('release_status', ''))
        print('severity       :', run.get('severity', ''))
        print('loop_count     :', run.get('loop_count', 0))
        print('execution_error:', run.get('execution_error', ''))
        print('summary        :', run.get('summary', ''))


if __name__ == '__main__':
    main()
