from __future__ import annotations

from agents.base import compact_history, developer_resources, render_agent_context, safe_json
from core.context_views import build_developer_context_view, render_context_view
from core.debug import trace_block
from core.llm import call_role_llm


def build_dependency_retry_hint(execution_error: str) -> str:
    err = (execution_error or "").lower()
    if (
        "eresolve" in err
        or "peer react" in err
        or "react-virtualized" in err
        or "unable to resolve dependency tree" in err
    ):
        return """
Retry focus:
- remove incompatible dependencies
- keep dependencies minimal
- prefer a smaller, safer patch than the previous attempt
""".strip()
    return ""


def build_developer_prompt(
    role: str,
    lane: str,
    task: str,
    prd: str,
    design: str,
    bugs: list,
    fix_suggestion: str,
    execution_error: str,
    history: list,
    planned_changes: dict | None = None,
    agent_context: dict | None = None,
    project_mode: str = "new_project",
    ownership_map: dict | None = None,
    story_packet: dict | None = None,
    system_target: dict | None = None,
    compact_context: bool = False,
) -> str:
    retry_hint = build_dependency_retry_hint(execution_error)
    lane_guidance = {
        "frontend": "Stay inside frontend-owned paths unless a shared integration file is clearly required.",
        "backend": "Stay inside backend-owned paths unless a shared integration file is clearly required.",
    }.get(lane, "Stay inside your lane ownership boundaries.")

    if compact_context:
        context_like = {
            "story_goal": task,
            "task": task,
            "story_packet": story_packet or {},
            "effective_target": system_target or {},
            "prd": prd,
            "design": design,
            "execution_error": execution_error,
            "fix_suggestion": fix_suggestion,
        }
        compact_view = render_context_view(build_developer_context_view(context_like, lane))
        return f"""
You are the {lane.capitalize()} Developer role.

Current task:
- implement the current story safely inside the {lane} lane

Highest priority order:
1. valid output contract
2. scope safety
3. production UI quality
4. minimal dependencies
5. story completeness

Frontend-only root Vite file contract:
- If lane=frontend and effective_target.effective_mode=frontend_only and effective_target.frontend_root='.', return paths at app root.
- Required paths are exactly: package.json, index.html, src/main.jsx, src/App.jsx, src/index.css.
- Do NOT prefix these files with frontend/, app/, web/, client/, or project-name/.

Read and follow these focused resources:
{developer_resources(project_mode, execution_error, story_packet, role)}

Compact implementation context:
{compact_view}

Ownership map:
{safe_json(ownership_map or {})}

Planned changes:
{safe_json(planned_changes or {})}

Current blocker bugs:
{safe_json(bugs)}

Retry hint:
{retry_hint}

Recent history:
{compact_history(history, limit=2)}

Return ONLY valid JSON with files.
No markdown. No prose. No extra keys.
""".strip()

    return f"""
You are the {lane.capitalize()} Developer role.

Current task:
- implement the current story safely inside the {lane} lane

Highest priority order:
1. valid output contract
2. scope safety
3. baseline preservation
4. minimal dependencies
5. story completeness

Frontend-only root Vite file contract:
- If lane=frontend and system_target.effective_mode=frontend_only and system_target.frontend_root='.', return paths at app root.
- Required paths are exactly: package.json, index.html, src/main.jsx, src/App.jsx, src/index.css.
- Do NOT prefix these files with frontend/, app/, web/, client/, or project-name/.

Read and follow these resources:
{developer_resources(project_mode, execution_error, story_packet, role)}

User task:
{task}

Project mode:
{project_mode}

Lane:
{lane}

Lane guidance:
{lane_guidance}

Story packet:
{safe_json(story_packet or {})}

System target:
{safe_json(system_target or {})}

Ownership map:
{safe_json(ownership_map or {})}

PRD:
{prd}

Design:
{design}

Planned changes:
{safe_json(planned_changes or {})}

Current blocker bugs:
{safe_json(bugs)}

Fix suggestion:
{fix_suggestion}

Execution error:
{execution_error}

Retry hint:
{retry_hint}

Your agent context:
{render_agent_context(agent_context or {})}

Recent history:
{compact_history(history)}

Return ONLY valid JSON.
No markdown. No prose. No extra keys.
""".strip()


def run_developer(
    task: str,
    prd: str,
    design: str,
    bugs: list,
    fix_suggestion: str,
    execution_error: str,
    history: list,
    planned_changes: dict | None = None,
    agent_context: dict | None = None,
    project_mode: str = "new_project",
    role: str = "developer",
    lane: str = "frontend",
    ownership_map: dict | None = None,
    story_packet: dict | None = None,
    system_target: dict | None = None,
    compact_context: bool = False,
) -> str:
    prompt = build_developer_prompt(
        role=role,
        lane=lane,
        task=task,
        prd=prd,
        design=design,
        bugs=bugs,
        fix_suggestion=fix_suggestion,
        execution_error=execution_error,
        history=history,
        planned_changes=planned_changes,
        agent_context=agent_context,
        project_mode=project_mode,
        ownership_map=ownership_map,
        story_packet=story_packet,
        system_target=system_target,
        compact_context=compact_context,
    )
    trace_block(f"{role.upper()} PROMPT", prompt)
    response = call_role_llm(role, prompt)
    trace_block(f"{role.upper()} RESPONSE", response)
    return response
