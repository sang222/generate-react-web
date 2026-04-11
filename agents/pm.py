from __future__ import annotations

from agents.base import load_skill_resource, render_agent_context
from core.debug import trace_block
from core.llm import call_role_llm


def build_pm_prompt(task: str, agent_context: dict | None = None, story_packet: dict | None = None) -> str:
    skill_overview = load_skill_resource('skill_overview.md')
    return f"""
You are a Senior Product Manager.

Mission:
- Convert the user task into a clear, structured PRD
- Make it actionable for architect, developer, and QA
- Use your own durable memory and operating principles when relevant

Skill context:
{skill_overview}

User task:
{task}

Story packet:
{story_packet or {}}

Your agent context:
{render_agent_context(agent_context or {})}

Output format:
1. Product Goal
2. Target Users
3. Core Features
4. User Flow
5. Functional Requirements
6. Non-Functional Requirements
7. UI / UX Notes
8. Technical Notes
9. Acceptance Criteria
10. Final Scope for V1

Rules:
- Be concrete and implementation-oriented
- Do not ask questions
- Assume reasonable defaults if details are missing
- Keep scope realistic for the configured fullstack target, including frontend, backend, and database responsibilities when present
- Do not generate code
- Do not produce architecture or file structure
- Acceptance criteria must be specific and testable

Return only plain text.
""".strip()


def run_pm(task: str, agent_context: dict | None = None, story_packet: dict | None = None) -> str:
    prompt = build_pm_prompt(task=task, agent_context=agent_context, story_packet=story_packet)
    trace_block("PM PROMPT", prompt)
    response = call_role_llm("pm", prompt)
    trace_block("PM RESPONSE", response)
    return response
