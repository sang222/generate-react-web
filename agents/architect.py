from __future__ import annotations

from agents.base import common_workflow_helpers, load_skill_resource, render_agent_context, safe_json
from core.debug import trace_block
from core.llm import call_role_llm


def build_architect_prompt(task: str, prd: str, agent_context: dict | None = None, story_packet: dict | None = None) -> str:
    mode_rules = load_skill_resource('new_project_rules.md' if (agent_context or {}).get('project_mode') == 'new_project' else 'existing_project_rules.md')
    system_target = (story_packet or {}).get('system_target', {})
    return f"""
You are a Senior Software Architect.

Mission:
- Convert the PRD into a clear, implementation-oriented system plan
- Use your own durable memory and operating principles when relevant
- Give a concrete design that a developer can implement directly with minimal guessing

Relevant skill guidance:
{common_workflow_helpers(story_packet)}

{mode_rules}

Task:
{task}

PRD:
{prd}

Story packet:
{safe_json(story_packet or {})}

System target:
{safe_json(system_target)}

Your agent context:
{render_agent_context(agent_context or {})}

Output format:
1. Architecture Overview
2. Tech Stack
3. Frontend Structure
4. Backend Structure
5. Data and API Flow
6. Validation Rules
7. Error Handling
8. Suggested File Tree
9. Implementation Notes

Rules:
- Use the configured stacks exactly; do not invent a different backend or database stack
- Frontend stack: {system_target.get('frontend_stack', 'react-vite')}
- Backend stack: {system_target.get('backend_language', 'java')} + {system_target.get('backend_framework', 'spring_boot')} ({system_target.get('backend_build_tool', 'gradle')})
- Database stack: {system_target.get('database_engine', 'postgres')} + {system_target.get('database_orm', 'jpa')}
- Keep architecture simple, practical, and scoped to the PRD
- For fullstack targets, separate frontend/ and backend/ explicitly
- For Java backend, prefer controller/service/repository/entity/config package split
- Include Gradle and application.properties expectations when backend is Spring Boot
- Do not expand scope beyond V1 unless clearly required
- Do not generate code

Return only plain text.
""".strip()


def run_architect(task: str, prd: str, agent_context: dict | None = None, story_packet: dict | None = None) -> str:
    prompt = build_architect_prompt(task=task, prd=prd, agent_context=agent_context, story_packet=story_packet)
    trace_block("ARCHITECT PROMPT", prompt)
    response = call_role_llm("architect", prompt)
    trace_block("ARCHITECT RESPONSE", response)
    return response
