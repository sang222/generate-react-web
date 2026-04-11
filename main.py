from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any, Dict

from core.orchestrator import run_orchestrator


def _load_task_from_file(path: str) -> str:
    return Path(path).read_text(encoding="utf-8").strip()


def _print_summary(result: Dict[str, Any]) -> None:
    print(f"Run ID: {result.get('run_id', '')}")
    print(f"Project mode: {result.get('project_mode', '')}")
    print(f"Decision: {result.get('final_decision', '')}")
    print(f"Release status: {result.get('release_status', '')}")
    print(f"Severity: {result.get('severity', '')}")
    print(f"Run state: {result.get('run_state_path', '')}")
    print("Execution error:")
    print(result.get("execution_error", "") or "")


def main() -> int:
    parser = argparse.ArgumentParser(description="Run the AI Dev Team orchestrator")
    parser.add_argument("task", nargs="?", help="Task text")
    parser.add_argument("--task-file", help="Path to a file containing the task")
    parser.add_argument("--project-mode", default="new_project", choices=["new_project", "existing_project"])
    parser.add_argument("--entry-skill", default="dev-team-workflow", choices=["dev-team-workflow", "dev-team-agent", "dev-team-setup"])
    parser.add_argument("--json", action="store_true", help="Print full result as JSON")
    parser.add_argument("--save-result", help="Save full result JSON to a file")
    args = parser.parse_args()

    task = (args.task or "").strip()
    if args.task_file:
        task = _load_task_from_file(args.task_file)

    if args.entry_skill == 'dev-team-setup':
        print('Setup skill is file/config based. Inspect _bmad/config.yaml and _bmad/module-help.csv.')
        return 0

    if not task:
        print("No task provided.", file=sys.stderr)
        return 1

    try:
        result = run_orchestrator(task, project_mode=args.project_mode)
    except Exception as exc:
        print(f"Runtime error: {exc}", file=sys.stderr)
        return 1

    if args.json:
        print(json.dumps(result, ensure_ascii=False, indent=2))
    else:
        _print_summary(result)

    if args.save_result:
        Path(args.save_result).write_text(
            json.dumps(result, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )

    return 0 if result.get("final_decision") == "DONE" else 2


if __name__ == "__main__":
    raise SystemExit(main())
