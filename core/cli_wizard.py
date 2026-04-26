from __future__ import annotations

from dataclasses import dataclass
from typing import List, Optional

try:
    import questionary  # type: ignore
except Exception:  # pragma: no cover - fallback for minimal environments
    questionary = None


@dataclass
class WizardResult:
    action: str
    task: str = ""
    project_mode: str = "new_project"
    execution_mode: str = "frontend_only"
    project_id: str = ""
    epic_id: str = ""
    story_id: str = "story_1"
    story_name: str = ""
    resume_from: str = ""
    depends_on: Optional[List[str]] = None
    entry_skill: str = "dev-team-workflow"
    json_output: bool = False
    save_result: str = ""
    benchmark_model: str = "qwen3.5:cloud"
    benchmark_runs: int = 5
    workflow_status_project_id: str = ""
    skill_candidate_action: str = ""
    skill_candidate_id: str = ""
    skill_candidate_decision: str = "reject"
    skill_candidate_note: str = ""


FULLSTACK_FOUNDATION_TEMPLATE = """Build only the monorepo foundation for a cafe ordering system.

Scope for this story:
Create runnable app shells only. Do not implement product features.

Required structure:
- customer-web: minimal Vite React shell
- staff-web: minimal Vite React shell
- admin-web: minimal Vite React shell
- api: minimal Express API shell

Customer web:
- package.json
- index.html
- src/main.jsx
- src/App.jsx
- src/index.css

Staff web:
- package.json
- index.html
- src/main.jsx
- src/App.jsx
- src/index.css

Admin web:
- package.json
- index.html
- src/main.jsx
- src/App.jsx
- src/index.css

API:
- package.json
- src/server.js
- src/app.js
- src/config/db.js
- .env.example
- GET /health endpoint
- MongoDB connection config through MONGODB_URI

Out of scope for this story:
- authentication
- menu CRUD
- order flow
- payment
- dashboards
- account management
- reports

Acceptance criteria:
- each web app is a valid Vite React app
- api starts with npm start
- GET /health returns JSON
- no feature logic beyond app shells and health check
- keep output small and valid JSON"""

FRONTEND_TEMPLATE = """Build a clean, polished React/Vite web app.

Scope:
- Create a root Vite React app.
- Keep the app focused enough to produce valid runnable files.

Required files:
- package.json
- index.html
- src/main.jsx
- src/App.jsx
- src/index.css

Requirements:
- No frontend/, app/, client/, web/, or nested wrapper folders.
- No backend.
- Responsive layout.
- Polished CSS.
- No fake API calls.
- Return only valid project JSON with files array."""


def _slug_default(value: str, fallback: str) -> str:
    raw = (value or "").strip().lower()
    if not raw:
        return fallback
    out: List[str] = []
    prev_sep = False
    for char in raw:
        if char.isalnum():
            out.append(char)
            prev_sep = False
        elif char in {" ", "-", "_", "/"} and not prev_sep:
            out.append("_")
            prev_sep = True
    result = "".join(out).strip("_")[:48]
    return result or fallback


def _fallback_select(message: str, choices: List[tuple[str, str]], default: str | None = None) -> str:
    print(f"\n{message}")
    for index, (label, value) in enumerate(choices, start=1):
        marker = "*" if value == default else " "
        print(f" {marker} {index}. {label}")
    while True:
        raw = input("Choose number: ").strip()
        if not raw and default:
            return default
        if raw.isdigit() and 1 <= int(raw) <= len(choices):
            return choices[int(raw) - 1][1]


def _fallback_text(message: str, default: str = "", multiline: bool = False) -> str:
    suffix = f" [{default[:80]}{'...' if len(default) > 80 else ''}]" if default else ""
    if multiline:
        print(f"\n{message}{suffix}")
        print("Paste text. End with a single line containing only EOF. Leave empty for default.")
        lines: List[str] = []
        while True:
            line = input()
            if line.strip() == "EOF":
                break
            lines.append(line)
        value = "\n".join(lines).strip()
        return value or default
    value = input(f"{message}{suffix}: ").strip()
    return value or default


def _fallback_confirm(message: str, default: bool = True) -> bool:
    default_text = "Y/n" if default else "y/N"
    raw = input(f"{message} ({default_text}): ").strip().lower()
    if not raw:
        return default
    return raw in {"y", "yes"}


def _select(message: str, choices: List[tuple[str, str]], default: str | None = None) -> str:
    if questionary is None:
        return _fallback_select(message, choices, default=default)
    q_choices = [questionary.Choice(label, value=value) for label, value in choices]
    answer = questionary.select(message, choices=q_choices, default=default).ask()
    return answer or (default or choices[0][1])


def _text(message: str, default: str = "", multiline: bool = False) -> str:
    if questionary is None:
        return _fallback_text(message, default=default, multiline=multiline)
    answer = questionary.text(message, default=default, multiline=multiline).ask()
    return (answer or default or "").strip()


def _confirm(message: str, default: bool = True) -> bool:
    if questionary is None:
        return _fallback_confirm(message, default=default)
    answer = questionary.confirm(message, default=default).ask()
    return bool(answer)


def _ask_common_workflow_fields(
    *,
    action: str,
    project_mode: str,
    execution_mode: str,
    default_task: str,
    default_project_id: str,
    default_story_id: str,
) -> WizardResult:
    task = _text("Task / story request", default=default_task, multiline=True)
    project_id = _text("Project ID", default=default_project_id or _slug_default(task, "demo_project"))
    epic_id = _text("Epic ID", default=f"{project_id}_epic")
    story_id = _text("Story ID", default=default_story_id)
    story_name = _text("Story name (optional)", default="")

    resume_from = ""
    if project_mode == "existing_project":
        resume_from = _text("Resume from path / delivered source directory (optional)", default="")

    depends_on: Optional[List[str]] = None
    if _confirm("Add dependency story IDs?", default=False):
        values: List[str] = []
        while True:
            value = _text("Dependency story ID (empty to finish)", default="")
            if not value:
                break
            values.append(value)
        depends_on = values or None

    json_output = _confirm("Print full JSON result?", default=False)
    save_result = ""
    if _confirm("Save full result to a file?", default=False):
        save_result = _text("Result output path", default=f".runs/{project_id}_{story_id}_result.json")

    print("\nRun summary:")
    print(f"  action: {action}")
    print(f"  project_mode: {project_mode}")
    print(f"  execution_mode: {execution_mode}")
    print(f"  project_id: {project_id}")
    print(f"  epic_id: {epic_id}")
    print(f"  story_id: {story_id}")
    if resume_from:
        print(f"  resume_from: {resume_from}")

    if not _confirm("Run with these settings?", default=True):
        return WizardResult(action="exit")

    return WizardResult(
        action="run_workflow",
        task=task,
        project_mode=project_mode,
        execution_mode=execution_mode,
        project_id=project_id,
        epic_id=epic_id,
        story_id=story_id,
        story_name=story_name,
        resume_from=resume_from,
        depends_on=depends_on,
        json_output=json_output,
        save_result=save_result,
    )


def run_cli_wizard() -> Optional[WizardResult]:
    action = _select(
        "What do you want to run?",
        [
            ("New frontend project", "new_frontend"),
            ("Existing frontend project", "existing_frontend"),
            ("New fullstack foundation", "new_fullstack_foundation"),
            ("Existing fullstack project", "existing_fullstack"),
            ("Custom workflow", "custom_workflow"),
            ("Check cloud models", "check_models"),
            ("Benchmark model", "benchmark_model"),
            ("Clear failed runs/logs", "clear_logs"),
            ("Workflow status", "workflow_status"),
            ("Skill candidates", "skill_candidates"),
            ("Exit", "exit"),
        ],
        default="new_frontend",
    )

    if action == "exit":
        return None

    if action == "check_models":
        return WizardResult(action="check_models")

    if action == "benchmark_model":
        model = _select(
            "Choose model to benchmark",
            [
                ("qwen3.5:cloud", "qwen3.5:cloud"),
                ("glm-5.1:cloud", "glm-5.1:cloud"),
                ("qwen3-coder-next:cloud", "qwen3-coder-next:cloud"),
            ],
            default="qwen3.5:cloud",
        )
        runs_raw = _text("Runs", default="5")
        runs = int(runs_raw) if runs_raw.isdigit() and int(runs_raw) > 0 else 5
        return WizardResult(action="benchmark_model", benchmark_model=model, benchmark_runs=runs)

    if action == "clear_logs":
        return WizardResult(action="clear_logs")

    if action == "workflow_status":
        project_id = _text("Project ID", default="demo_cloud")
        return WizardResult(action="workflow_status", workflow_status_project_id=project_id)

    if action == "skill_candidates":
        subaction = _select(
            "Skill candidate action",
            [
                ("List candidates", "list"),
                ("Show candidate", "show"),
                ("Review candidate", "review"),
            ],
            default="list",
        )
        result = WizardResult(action="skill_candidates", skill_candidate_action=subaction)
        if subaction in {"show", "review"}:
            result.skill_candidate_id = _text("Candidate ID", default="")
        if subaction == "review":
            result.skill_candidate_decision = _select(
                "Decision",
                [
                    ("approve", "approve"),
                    ("reject", "reject"),
                    ("revise", "revise"),
                ],
                default="reject",
            )
            result.skill_candidate_note = _text("Review note", default="")
        return result

    if action == "new_frontend":
        return _ask_common_workflow_fields(
            action=action,
            project_mode="new_project",
            execution_mode="frontend_only",
            default_task=FRONTEND_TEMPLATE,
            default_project_id="frontend_site",
            default_story_id="frontend_phase_1",
        )

    if action == "existing_frontend":
        return _ask_common_workflow_fields(
            action=action,
            project_mode="existing_project",
            execution_mode="frontend_only",
            default_task="Update the existing frontend project. Keep the current structure unchanged and modify only the scoped UI requested in this story.",
            default_project_id="frontend_site",
            default_story_id="frontend_update_1",
        )

    if action == "new_fullstack_foundation":
        return _ask_common_workflow_fields(
            action=action,
            project_mode="new_project",
            execution_mode="fullstack",
            default_task=FULLSTACK_FOUNDATION_TEMPLATE,
            default_project_id="cafe_fullstack",
            default_story_id="fullstack_foundation_1",
        )

    if action == "existing_fullstack":
        return _ask_common_workflow_fields(
            action=action,
            project_mode="existing_project",
            execution_mode="fullstack",
            default_task="Update the existing fullstack project within the current story scope. Preserve existing architecture, routes, database config, and app structure.",
            default_project_id="cafe_fullstack",
            default_story_id="fullstack_update_1",
        )

    project_mode = _select(
        "Project mode",
        [("new_project", "new_project"), ("existing_project", "existing_project")],
        default="new_project",
    )
    execution_mode = _select(
        "Execution mode",
        [
            ("auto", "auto"),
            ("frontend_only", "frontend_only"),
            ("backend_only", "backend_only"),
            ("fullstack", "fullstack"),
        ],
        default="frontend_only",
    )
    return _ask_common_workflow_fields(
        action=action,
        project_mode=project_mode,
        execution_mode=execution_mode,
        default_task="Describe the story you want the AI delivery engine to implement.",
        default_project_id="custom_project",
        default_story_id="story_1",
    )
