from __future__ import annotations

from agents.base import compact_history, developer_resources, render_agent_context, safe_json
from core.debug import trace_block
from core.llm import call_role_llm


SIMPLE_JSON_EXAMPLE = """{
  "files": [
    {"path": "frontend/package.json", "content": "..."},
    {"path": "frontend/index.html", "content": "..."},
    {"path": "frontend/src/main.jsx", "content": "..."},
    {"path": "frontend/src/App.jsx", "content": "..."},
    {"path": "backend/build.gradle", "content": "..."},
    {"path": "backend/src/main/java/com/example/app/Application.java", "content": "..."},
    {"path": "backend/src/main/resources/application.properties", "content": "..."}
  ]
}"""


DEPENDENCY_POLICY = """
Dependency policy:
- Use the minimum necessary dependencies only.
- Do not add optional UI/performance libraries unless explicitly required by the task.
- Do not use deprecated or React-incompatible libraries.
- Do not use react-virtualized.
- If virtualization is explicitly required, prefer react-window.
- For simple apps like todo apps, do not add any virtualization library.
- Keep the project compatible with React 18+.
"""


def build_dependency_retry_hint(execution_error: str) -> str:
    err = (execution_error or "").lower()
    if (
        "eresolve" in err
        or "peer react" in err
        or "react-virtualized" in err
        or "unable to resolve dependency tree" in err
    ):
        return """
Dependency retry fix:
- The previous attempt failed because package.json included an incompatible dependency for React 18.
- Remove react-virtualized completely.
- Do not use any virtualization library unless explicitly required.
- Keep dependencies minimal and React 18 compatible.
- Regenerate a minimal stable project with only essential libraries.
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
) -> str:
    retry_hint_parts: list[str] = []
    if execution_error or bugs:
        retry_hint_parts.append("""
Retry priority:
- First fix the concrete execution_error and blocker bugs.
- Keep the solution smaller and safer than the previous attempt unless the task clearly demands more complexity.
- Prefer fewer files with cleaner imports over many files with risky coupling.
""".strip())
    dependency_hint = build_dependency_retry_hint(execution_error)
    if dependency_hint:
        retry_hint_parts.append(dependency_hint)
    retry_hint = "\n\n".join(part for part in retry_hint_parts if part)

    lane_guidance = {
        'frontend': "You own frontend paths such as frontend/, frontend/src/, frontend/public/, and shared frontend-facing contracts when needed for integration.",
        'backend': "You own backend paths such as backend/, backend/src/main/java/, backend/src/main/resources/, and shared/contracts/. Avoid frontend-only files unless required for integration.",
    }.get(lane, "Stay within your assigned ownership lane.")

    return f"""
You are a Senior {lane.capitalize()} Developer working inside a gated fullstack story delivery workflow.

Mission:
- Implement the current story safely inside your ownership lane
- Return only the files your lane needs to create or change
- Respect the existing baseline and do not regenerate unrelated files
- The default system target is fullstack: React + Vite frontend, Java + Spring Boot backend, Gradle build, PostgreSQL + JPA

Relevant skill guidance:
{developer_resources(project_mode, execution_error)}

{DEPENDENCY_POLICY}

Task:
{task}

Project mode:
{project_mode}

Current lane:
{lane}

Lane guidance:
{lane_guidance}

Story packet:
{safe_json(story_packet or {})}

Ownership map:
{safe_json(ownership_map or {})}

PRD:
{prd}

Design:
{design}

Planned changes:
{safe_json(planned_changes or {})}

Current bugs to fix:
{bugs}

Fix suggestion:
{fix_suggestion}

Execution error:
{execution_error}

Your agent context:
{render_agent_context(agent_context or {})}

Recent history:
{compact_history(history)}

STRICT RULES:
- Output ONLY valid JSON
- No markdown
- No explanation
- No extra fields
- Do NOT wrap the JSON in code fences
- The first character must be {{
- The last character must be }}
- Use double quotes for all JSON keys and string values
- Escape newlines correctly inside file content strings
- Do not use trailing commas
- Only return files that belong to your lane or are required shared integration files
- Do not overwrite unrelated files from another lane
- If the project mode is existing_project, preserve the existing app and patch it incrementally

Required schema:
{SIMPLE_JSON_EXAMPLE}

Implementation rules:
- Use the configured stacks exactly; do not invent a different stack.
- Frontend stack: {(story_packet or {}).get("system_target", {}).get("frontend_stack", "react-vite")}
- Backend stack: {(story_packet or {}).get("system_target", {}).get("backend_language", "java")} + {(story_packet or {}).get("system_target", {}).get("backend_framework", "spring_boot")} using {(story_packet or {}).get("system_target", {}).get("backend_build_tool", "gradle")}
- Database stack: {(story_packet or {}).get("system_target", {}).get("database_engine", "postgres")} + {(story_packet or {}).get("system_target", {}).get("database_orm", "jpa")}
- When touching frontend code, use a dedicated frontend/ app with React + Vite conventions.
- When touching backend code, use a dedicated backend/ service with Java + Spring Boot conventions and the configured build tool.
- For Java backend, generate Gradle build files, Spring Boot entrypoint, controller/service/repository/entity structure, and application.properties configured for PostgreSQL + JPA.
- Keep dependencies low and compatible.
- Preserve buildability.
- Keep imports exact and safe.
- Prefer minimal, verifiable changes over broad rewrites.
- Treat the delivered baseline as stable unless the current story explicitly changes it.

{retry_hint}

Return ONLY JSON.
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
    role: str = 'developer',
    lane: str = 'frontend',
    ownership_map: dict | None = None,
    story_packet: dict | None = None,
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
    )
    trace_block(f"{role.upper()} PROMPT", prompt)
    response = call_role_llm(role, prompt)
    trace_block(f"{role.upper()} RESPONSE", response)
    return response