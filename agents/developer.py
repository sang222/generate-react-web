from __future__ import annotations

from agents.base import compact_history, developer_resources, render_agent_context, safe_json
from core.debug import trace_block
from core.llm import call_role_llm


SIMPLE_JSON_EXAMPLE = """{
  "files": [
    {"path": "package.json", "content": "..."},
    {"path": "index.html", "content": "..."},
    {"path": "src/main.jsx", "content": "..."},
    {"path": "src/App.jsx", "content": "..."},
    {"path": "src/index.css", "content": "..."}
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

    return f"""
You are a Senior React Developer.

Mission:
- Generate a runnable React (Vite) project iteration
- Fix issues from previous iterations
- Reuse your own durable lessons when helpful

Relevant skill guidance:
{developer_resources(project_mode, execution_error)}

{DEPENDENCY_POLICY}

Task:
{task}

Project mode:
{project_mode}

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

Required schema:
{SIMPLE_JSON_EXAMPLE}

Minimum required files:
- package.json
- index.html
- src/main.jsx
- src/App.jsx
- src/index.css

Implementation rules:
- Use React + Vite
- Use functional components
- Use createRoot in main.jsx
- Ensure imports are valid
- Ensure all referenced files exist
- Keep import paths relative, exact, and buildable
- package.json must contain valid dependencies and scripts
- index.html must be a valid minimal Vite HTML entry
- Generate complete usable file contents
- Do not output placeholders or pseudo-code
- Prefer JavaScript unless the task clearly requires TypeScript
- Keep dependency count low
- Prefer local component state unless shared state is clearly needed
- Prefer verifiable, build-safe changes over broad speculative design

{retry_hint}

Before finalizing internally, check:
- Is the JSON valid?
- Are all required files present?
- Do local imports point to real files?
- Is package.json consistent with the generated files?
- Is index.html minimal and valid?

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
) -> str:
    prompt = build_developer_prompt(
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
    )
    trace_block("DEVELOPER PROMPT", prompt)
    response = call_role_llm("developer", prompt)
    trace_block("DEVELOPER RESPONSE", response)
    return response
