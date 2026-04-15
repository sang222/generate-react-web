from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from core.memory import clear_runs


def main() -> None:
    deleted_count = clear_runs()
    print(f'Deleted {deleted_count} runs.')


if __name__ == '__main__':
    main()
