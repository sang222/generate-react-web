from __future__ import annotations

import argparse
import sys

from agents.architect import run_architect


def main() -> int:
    parser = argparse.ArgumentParser(description='Design one story from task + PRD')
    parser.add_argument('task')
    parser.add_argument('--prd', required=True)
    args = parser.parse_args()
    print(run_architect(task=args.task, prd=args.prd, agent_context='', story_packet={}))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
