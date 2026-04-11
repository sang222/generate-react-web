from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from core.orchestrator import run_orchestrator


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run AI Dev Team")
    parser.add_argument("task", nargs="?", help="Task string to execute")
    parser.add_argument("--task-file", help="Path to a file containing the task")
    parser.add_argument("--json", action="store_true", help="Print JSON result")
    parser.add_argument("--save-result", help="Save final result JSON to a file")
    return parser.parse_args()


def resolve_task(args: argparse.Namespace) -> str:
    if args.task:
        return args.task.strip()
    if args.task_file:
        return Path(args.task_file).read_text(encoding="utf-8").strip()
    raise ValueError("Provide either a task string or --task-file")


def main() -> int:
    try:
        args = parse_args()
        task = resolve_task(args)
        if not task:
            raise ValueError("Task cannot be empty")

        result = run_orchestrator(task)

        if args.save_result:
            Path(args.save_result).write_text(
                json.dumps(result, ensure_ascii=False, indent=2),
                encoding="utf-8",
            )

        if args.json:
            print(json.dumps(result, ensure_ascii=False, indent=2))
        else:
            print(f"Run ID: {result.get('run_id', '')}")
            print(f"Decision: {result.get('final_decision', '')}")
            print(f"Release status: {result.get('release_status', '')}")
            print(f"Severity: {result.get('severity', '')}")
            if result.get("execution_error"):
                print("Execution error:")
                print(result["execution_error"])

        if result.get("final_decision") == "DONE":
            return 0
        return 2
    except Exception as exc:
        print(f"Runtime error: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
