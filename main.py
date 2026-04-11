from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional

from core.orchestrator import run_orchestrator


def _load_task_from_file(path: str) -> str:
    return Path(path).read_text(encoding="utf-8").strip()


def _print_summary(result: Dict[str, Any]) -> None:
    print(f"Run ID: {result.get('run_id', '')}")
    print(f"Project ID: {result.get('project_id', '')}")
    print(f"Epic ID: {result.get('epic_id', '')}")
    print(f"Story ID: {result.get('story_id', '')}")
    print(f"Story name: {result.get('story_name', '')}")
    print(f"Project mode: {result.get('project_mode', '')}")
    print(f"Decision: {result.get('final_decision', '')}")
    print(f"Release status: {result.get('release_status', '')}")
    print(f"Severity: {result.get('severity', '')}")
    print(f"Run state: {result.get('run_state_path', '')}")
    if result.get('delivery_manifest'):
        print(f"Delivery manifest: {result.get('delivery_manifest', '')}")
        print(f"Delivery source: {result.get('delivery_source', '')}")
        print(f"Next story: {result.get('next_story', '')}")
    print("Execution error:")
    print(result.get("execution_error", "") or "")


def _ask(prompt: str, default: Optional[str] = None, allow_empty: bool = False) -> str:
    while True:
        suffix = f" [{default}]" if default else ""
        value = input(f"{prompt}{suffix}: ").strip()
        if value:
            return value
        if default is not None:
            return default
        if allow_empty:
            return ""
        print("Value is required.")


def _ask_choice(prompt: str, choices: List[str], default: Optional[str] = None) -> str:
    lowered = {choice.lower(): choice for choice in choices}
    while True:
        value = _ask(f"{prompt} ({'/'.join(choices)})", default=default)
        picked = lowered.get(value.lower())
        if picked:
            return picked
        print(f"Invalid choice. Allowed values: {', '.join(choices)}")


def _ask_yes_no(prompt: str, default: bool = False) -> bool:
    default_text = "y" if default else "n"
    while True:
        value = _ask(f"{prompt} (y/n)", default=default_text).lower()
        if value in {"y", "yes"}:
            return True
        if value in {"n", "no"}:
            return False
        print("Please answer y or n.")


def _ask_optional_list(prompt: str) -> Optional[List[str]]:
    values: List[str] = []
    while True:
        value = input(f"{prompt} (leave empty to finish): ").strip()
        if not value:
            break
        values.append(value)
    return values or None


def _run_workflow_status(project_id: str) -> int:
    from scripts.workflow_status import main as workflow_status_main
    import sys as _sys

    old_argv = list(_sys.argv)
    try:
        _sys.argv = [old_argv[0], '--project-id', project_id]
        return workflow_status_main()
    finally:
        _sys.argv = old_argv


def _interactive_collect(args: argparse.Namespace) -> argparse.Namespace:
    print("AI Dev Team Interactive Mode")
    print("Enter values step by step. Press Enter to accept a default.\n")

    action = _ask_choice(
        "Choose action",
        ["run_workflow", "workflow_status", "setup_info"],
        default="run_workflow",
    )

    if action == "workflow_status":
        args.workflow_status = True
        args.project_id = _ask("Project ID")
        return args

    if action == "setup_info":
        args.entry_skill = "dev-team-setup"
        return args

    args.entry_skill = _ask_choice(
        "Entry skill",
        ["dev-team-workflow", "dev-team-agent"],
        default=args.entry_skill or "dev-team-workflow",
    )

    task_input_mode = _ask_choice(
        "Task input mode",
        ["direct_text", "task_file"],
        default="direct_text",
    )
    if task_input_mode == "task_file":
        args.task_file = _ask("Task file path")
        args.task = None
    else:
        args.task = _ask("Task text")

    args.project_mode = _ask_choice(
        "Project mode",
        ["new_project", "existing_project"],
        default=args.project_mode or "new_project",
    )
    args.project_id = _ask("Project ID")
    args.epic_id = _ask("Epic ID")
    args.story_id = _ask("Story ID", default=args.story_id or "story_1")
    args.story_name = _ask("Story name", allow_empty=True)

    need_resume = args.project_mode == "existing_project" or _ask_yes_no(
        "Resume from an existing baseline?",
        default=False,
    )
    if need_resume:
        args.resume_from = _ask("Resume from path", allow_empty=True)
    else:
        args.resume_from = None

    if _ask_yes_no("Add story dependencies?", default=False):
        args.depends_on = _ask_optional_list("Dependency story ID")
    else:
        args.depends_on = None

    args.json = _ask_yes_no("Print full JSON result?", default=args.json)
    if _ask_yes_no("Save full result to a file?", default=False):
        args.save_result = _ask("Result output path")
    else:
        args.save_result = None

    return args


def main() -> int:
    parser = argparse.ArgumentParser(description="Run the AI Dev Team orchestrator")
    parser.add_argument("task", nargs="?", help="Task text")
    parser.add_argument("--task-file", help="Path to a file containing the task")
    parser.add_argument("--project-mode", default="new_project", choices=["new_project", "existing_project"])
    parser.add_argument("--project-id", help="Stable project identifier for story delivery")
    parser.add_argument("--epic-id", help="Epic identifier, e.g. SHOP-EPIC-1")
    parser.add_argument("--story-id", default="story_1", help="Story identifier, e.g. story_1 or SHOP-101")
    parser.add_argument("--story-name", help="Human-readable story name")
    parser.add_argument("--resume-from", help="Path to a delivered story source directory to continue from")
    parser.add_argument("--depends-on", action='append', default=None, help="Story dependency. Repeat for multiple dependencies.")
    parser.add_argument("--entry-skill", default="dev-team-workflow", choices=["dev-team-workflow", "dev-team-agent", "dev-team-setup"])
    parser.add_argument("--json", action="store_true", help="Print full result as JSON")
    parser.add_argument("--workflow-status", action="store_true", help="Show workflow status for a project and exit")
    parser.add_argument("--save-result", help="Save full result JSON to a file")
    parser.add_argument("--interactive", action="store_true", help="Ask for options step by step")
    args = parser.parse_args()

    no_direct_inputs = not any([
        args.task,
        args.task_file,
        args.workflow_status,
        args.save_result,
    ]) and args.project_id is None and args.epic_id is None and args.story_name is None and args.resume_from is None and args.depends_on is None

    if args.interactive or no_direct_inputs:
        args = _interactive_collect(args)

    task = (args.task or "").strip()
    if args.task_file:
        task = _load_task_from_file(args.task_file)

    if args.workflow_status:
        if not args.project_id:
            print('--workflow-status requires --project-id', file=sys.stderr)
            return 1
        return _run_workflow_status(args.project_id)

    if args.entry_skill == 'dev-team-setup':
        print('Setup skill is file/config based. Inspect _bmad/config.yaml and _bmad/module-help.csv.')
        return 0

    if not task:
        print("No task provided.", file=sys.stderr)
        return 1

    try:
        result = run_orchestrator(
            task,
            project_mode=args.project_mode,
            project_id=args.project_id,
            epic_id=args.epic_id,
            story_id=args.story_id,
            story_name=args.story_name,
            resume_from=args.resume_from,
            depends_on=args.depends_on,
        )
    except KeyboardInterrupt:
        print("\nInterrupted.", file=sys.stderr)
        return 130
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

    return 0 if result.get("final_decision") in {"DONE", "DELIVER_STORY"} else 2


if __name__ == "__main__":
    raise SystemExit(main())
