from __future__ import annotations

import argparse
import sys

from agents.pm import run_pm


def main() -> int:
    parser = argparse.ArgumentParser(description='Create PRD text from a task')
    parser.add_argument('task')
    args = parser.parse_args()
    print(run_pm(task=args.task, agent_context=''))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
