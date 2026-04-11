from __future__ import annotations

from agents.base import load_skill_resource, render_agent_context
from core.debug import trace_block
from core.llm import call_role_llm


def build_architect_prompt(task: str, prd: str, agent_context: dict | None = None) -> str:
    mode_rules = load_skill_resource('new_project_rules.md' if (agent_context or {}).get('project_mode') == 'new_project' else 'existing_project_rules.md')
    return f"""
You are a Senior Software Architect.

Mission:
- Convert the PRD into a clear, implementation-oriented React plan
- Use your own durable memory and operating principles when relevant
- Give a concrete design that a developer can implement directly with minimal guessing

Relevant skill guidance:
{mode_rules}

Task:
{task}

PRD:
{prd}

Your agent context:
{render_agent_context(agent_context or {})}

Output format:
1. Architecture Overview
2. Tech Stack
3. App Structure
4. Component Design
5. State Management
6. Data Flow
7. Validation Rules
8. Error Handling
9. Suggested File Tree
10. Implementation Notes

Rules:
- Use React + Vite
- Keep architecture simple, practical, and scoped to the PRD
- Do not expand scope beyond V1 unless clearly required
- Do not generate code

Return only plain text.
""".strip()


def run_architect(task: str, prd: str, agent_context: dict | None = None) -> str:
    prompt = build_architect_prompt(task=task, prd=prd, agent_context=agent_context)
    trace_block("ARCHITECT PROMPT", prompt)
    response = call_role_llm("architect", prompt)
    trace_block("ARCHITECT RESPONSE", response)
    return response
