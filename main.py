from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional

from core.skill_candidates import VALID_DECISIONS


def _load_task_from_file(path: str) -> str:
    return Path(path).read_text(encoding="utf-8").strip()


def _qa_line(question: str, answer: Any) -> None:
    value = answer if isinstance(answer, str) else json.dumps(answer, ensure_ascii=False)
    print(f"Q: {question}")
    print(f"A: {value}")


def _print_summary(result: Dict[str, Any]) -> None:
    _qa_line("Project ID?", result.get('project_id', ''))
    _qa_line("Epic ID?", result.get('epic_id', ''))
    _qa_line("Story ID?", result.get('story_id', ''))
    _qa_line("Story name?", result.get('story_name', ''))
    _qa_line("Project mode?", result.get('project_mode', ''))
    _qa_line("Final decision?", result.get('final_decision', ''))
    _qa_line("Release status?", result.get('release_status', ''))
    _qa_line("Severity?", result.get('severity', ''))
    if result.get('delivery_manifest'):
        _qa_line("Delivery manifest?", result.get('delivery_manifest', ''))
        _qa_line("Delivery source?", result.get('delivery_source', ''))
        _qa_line("Next story?", result.get('next_story', ''))
    _qa_line("Execution error?", result.get('execution_error', '') or 'None')


def _ask(prompt: str, default: Optional[str] = None, allow_empty: bool = False) -> str:
    while True:
        suffix = f" [{default}]" if default else ""
        value = input(f"Q: {prompt}{suffix}\nA: ").strip()
        if value:
            return value
        if default is not None:
            return default
        if allow_empty:
            return ""


def _ask_choice(prompt: str, choices: List[str], default: Optional[str] = None) -> str:
    lowered = {choice.lower(): choice for choice in choices}
    while True:
        value = _ask(f"{prompt} ({'/'.join(choices)})", default=default)
        picked = lowered.get(value.lower())
        if picked:
            return picked


def _ask_yes_no(prompt: str, default: bool = False) -> bool:
    default_text = "y" if default else "n"
    while True:
        value = _ask(f"{prompt} (y/n)", default=default_text).lower()
        if value in {"y", "yes"}:
            return True
        if value in {"n", "no"}:
            return False


def _ask_optional_list(prompt: str) -> Optional[List[str]]:
    values: List[str] = []
    while True:
        value = input(f"Q: {prompt} (leave empty to finish)\nA: ").strip()
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


def _run_skill_candidate_cli(*argv: str) -> int:
    from scripts.skill_candidates import main as skill_candidates_main
    import sys as _sys

    old_argv = list(_sys.argv)
    try:
        _sys.argv = [old_argv[0], *argv]
        return skill_candidates_main()
    finally:
        _sys.argv = old_argv


def _interactive_collect(args: argparse.Namespace) -> argparse.Namespace:
    action = _ask_choice('Choose action', ['run_workflow', 'workflow_status', 'skill_candidates', 'show_recovery_history', 'setup_info'], default='run_workflow')

    if action == 'workflow_status':
        args.workflow_status = True
        args.project_id = _ask('Project ID')
        return args

    if action == 'skill_candidates':
        subaction = _ask_choice('Skill candidate action', ['list', 'show', 'review'], default='list')
        if subaction == 'list':
            args.list_skill_candidates = True
            return args
        if subaction == 'show':
            args.show_skill_candidate = _ask('Candidate ID')
            return args
        args.review_skill_candidate = _ask('Candidate ID')
        args.skill_candidate_decision = _ask_choice('Decision', list(VALID_DECISIONS), default='reject')
        args.skill_candidate_note = _ask('Review note', allow_empty=True)
        return args

    if action == 'show_recovery_history':
        args.show_recovery_history = True
        return args

    if action == 'setup_info':
        args.entry_skill = 'dev-team-setup'
        return args

    args.entry_skill = _ask_choice('Entry skill', ['dev-team-workflow', 'dev-team-agent'], default=args.entry_skill or 'dev-team-workflow')
    task_input_mode = _ask_choice('Task input mode', ['direct_text', 'task_file'], default='direct_text')
    if task_input_mode == 'task_file':
        args.task_file = _ask('Task file path')
        args.task = None
    else:
        args.task = _ask('Task text')

    args.project_mode = _ask_choice('Project mode', ['new_project', 'existing_project'], default=args.project_mode or 'new_project')
    args.project_id = _ask('Project ID')
    args.epic_id = _ask('Epic ID')
    args.story_id = _ask('Story ID', default=args.story_id or 'story_1')
    args.story_name = _ask('Story name', allow_empty=True)

    need_resume = args.project_mode == 'existing_project' or _ask_yes_no('Resume from an existing baseline?', default=False)
    args.resume_from = _ask('Resume from path', allow_empty=True) if need_resume else None

    args.depends_on = _ask_optional_list('Dependency story ID') if _ask_yes_no('Add story dependencies?', default=False) else None
    args.execution_mode = _ask_choice('Execution mode', ['auto', 'frontend_only', 'backend_only', 'fullstack'], default=args.execution_mode or 'auto')
    args.json = _ask_yes_no('Print full JSON result?', default=args.json)
    args.save_result = _ask('Result output path', allow_empty=True) if _ask_yes_no('Save full result to a file?', default=False) else None
    return args


def main() -> int:
    parser = argparse.ArgumentParser(description='Run the AI Dev Team orchestrator')
    parser.add_argument('task', nargs='?', help='Task text')
    parser.add_argument('--task-file', help='Path to a file containing the task')
    parser.add_argument('--project-mode', default='new_project', choices=['new_project', 'existing_project'])
    parser.add_argument('--project-id', help='Stable project identifier for story delivery')
    parser.add_argument('--epic-id', help='Epic identifier, e.g. SHOP-EPIC-1')
    parser.add_argument('--story-id', default='story_1', help='Story identifier')
    parser.add_argument('--story-name', help='Human-readable story name')
    parser.add_argument('--resume-from', help='Path to a delivered story source directory to continue from')
    parser.add_argument('--depends-on', action='append', default=None, help='Story dependency. Repeat for multiple dependencies.')
    parser.add_argument('--entry-skill', default='dev-team-workflow', choices=['dev-team-workflow', 'dev-team-agent', 'dev-team-setup'])
    parser.add_argument('--execution-mode', default='auto', choices=['auto', 'frontend_only', 'backend_only', 'fullstack'], help='Lane activation policy for implementation')
    parser.add_argument('--json', action='store_true', help='Print full result as JSON')
    parser.add_argument('--workflow-status', action='store_true', help='Show workflow status for a project and exit')
    parser.add_argument('--list-skill-candidates', action='store_true', help='List skill candidates and exit')
    parser.add_argument('--show-skill-candidate', help='Show one skill candidate by id and exit')
    parser.add_argument('--review-skill-candidate', help='Review one skill candidate by id and exit')
    parser.add_argument('--skill-candidate-decision', choices=list(VALID_DECISIONS), help='Decision for --review-skill-candidate')
    parser.add_argument('--skill-candidate-note', default='', help='Optional note for skill candidate review')
    parser.add_argument('--save-result', help='Save full result JSON to a file')
    parser.add_argument('--interactive', action='store_true', help='Ask for options step by step')
    parser.add_argument('--list-agents', action='store_true', help='List available agent files and exit')
    parser.add_argument('--list-skills', action='store_true', help='List available skills and exit')
    parser.add_argument('--show-skill', help='Show one skill pack in detail and exit')
    parser.add_argument('--run-skill-evals', action='store_true', help='List skill eval corpus cases and exit')
    parser.add_argument('--show-skill-eval-case', help='Show one skill eval case by id and exit')
    parser.add_argument('--show-recovery-history', action='store_true', help='Show adaptive recovery history and exit')
    args = parser.parse_args()

    no_direct_inputs = not any([args.task, args.task_file, args.workflow_status, args.list_skill_candidates, args.show_skill_candidate, args.review_skill_candidate, args.save_result, args.list_agents, args.list_skills, args.show_skill, args.run_skill_evals, args.show_skill_eval_case, args.show_recovery_history]) and args.project_id is None and args.epic_id is None and args.story_name is None and args.resume_from is None and args.depends_on is None
    if args.interactive or no_direct_inputs:
        args = _interactive_collect(args)

    task = (args.task or '').strip()
    if args.task_file:
        task = _load_task_from_file(args.task_file)

    if args.workflow_status:
        if not args.project_id:
            print('Q: workflow status request')
            print('A: project_id is required')
            return 1
        return _run_workflow_status(args.project_id)

    if args.list_skill_candidates:
        return _run_skill_candidate_cli('--list')
    if args.show_skill_candidate:
        return _run_skill_candidate_cli('--show', args.show_skill_candidate)
    if args.review_skill_candidate:
        if not args.skill_candidate_decision:
            print('Q: skill candidate review')
            print('A: --skill-candidate-decision is required')
            return 2
        cli_args = ['--review', args.review_skill_candidate, '--decision', args.skill_candidate_decision]
        if args.skill_candidate_note:
            cli_args.extend(['--note', args.skill_candidate_note])
        return _run_skill_candidate_cli(*cli_args)

    if args.list_agents:
        from scripts.list_agents import main as _m
        return _m()
    if args.list_skills:
        from scripts.list_skills import main as _m
        return _m()
    if args.show_skill:
        from scripts.show_skill import main as _m
        import sys as _sys
        old_argv = list(_sys.argv)
        try:
            _sys.argv = [old_argv[0], '--skill', args.show_skill]
            return _m()
        finally:
            _sys.argv = old_argv

    if args.show_recovery_history:
        from scripts.show_recovery_history import main as _m
        import sys as _sys
        old_argv = list(_sys.argv)
        try:
            _sys.argv = [old_argv[0]]
            return _m()
        finally:
            _sys.argv = old_argv

    if args.run_skill_evals or args.show_skill_eval_case:
        from scripts.run_skill_eval import main as _m
        import sys as _sys
        old_argv = list(_sys.argv)
        try:
            argv = [old_argv[0], '--suite', 'brownfield']
            if args.show_skill_eval_case:
                argv.extend(['--show-case', args.show_skill_eval_case])
            _sys.argv = argv
            return _m()
        finally:
            _sys.argv = old_argv

    if args.entry_skill == 'dev-team-setup':
        _qa_line('Setup info?', 'Inspect _bmad/config.yaml and _bmad/module-help.csv')
        return 0

    if not task:
        print('Q: workflow run')
        print('A: No task provided')
        return 1

    try:
        from core.orchestrator import run_orchestrator
        result = run_orchestrator(task, project_mode=args.project_mode, project_id=args.project_id, epic_id=args.epic_id, story_id=args.story_id, story_name=args.story_name, resume_from=args.resume_from, depends_on=args.depends_on, execution_mode=args.execution_mode)
    except KeyboardInterrupt:
        print('Q: workflow run')
        print('A: Interrupted')
        return 130
    except Exception as exc:
        print('Q: workflow run')
        print(f'A: Runtime error: {exc}')
        return 1

    if args.json:
        print(json.dumps(result, ensure_ascii=False, indent=2))
    else:
        _print_summary(result)

    if args.save_result:
        Path(args.save_result).write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding='utf-8')
    return 0 if result.get('final_decision') in {'DONE', 'DELIVER_STORY'} else 2


if __name__ == '__main__':
    raise SystemExit(main())
