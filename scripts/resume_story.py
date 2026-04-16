from __future__ import annotations

import argparse
import json
import sys

from core.orchestrator import run_orchestrator


def main() -> int:
    parser = argparse.ArgumentParser(description='Resume a story from an existing baseline')
    parser.add_argument('task')
    parser.add_argument('--project-id', required=True)
    parser.add_argument('--epic-id', required=True)
    parser.add_argument('--story-id', required=True)
    parser.add_argument('--story-name', required=True)
    parser.add_argument('--execution-mode', default='auto', choices=['auto', 'frontend_only', 'backend_only', 'fullstack'])
    parser.add_argument('--resume-from', required=True)
    parser.add_argument('--depends-on', action='append', default=None)
    args = parser.parse_args()
    result = run_orchestrator(
        args.task,
        project_mode='existing_project',
        project_id=args.project_id,
        epic_id=args.epic_id,
        story_id=args.story_id,
        story_name=args.story_name,
        resume_from=args.resume_from,
        depends_on=args.depends_on,
        execution_mode=args.execution_mode,
    )
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if result.get('final_decision') in {'DONE', 'DELIVER_STORY'} else 2


if __name__ == '__main__':
    raise SystemExit(main())
