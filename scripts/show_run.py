from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import json
import sys

from core.memory import find_run_by_id


def main() -> None:
    if len(sys.argv) < 2:
        print('Usage: python scripts/show_run.py <run_id>')
        return
    run_id = sys.argv[1]
    run = find_run_by_id(run_id)
    if not run:
        print(f'Run not found: {run_id}')
        return
    print(json.dumps(run, ensure_ascii=False, indent=2))


if __name__ == '__main__':
    main()
