from __future__ import annotations

from agents.base import pm_resources, render_agent_context, safe_json
from core.debug import trace_block
from core.llm import call_role_llm


def build_pm_prompt(task: str, agent_context: dict | None = None, story_packet: dict | None = None) -> str:
    project_mode = (story_packet or {}).get("project_mode", "new_project")
    return f"""
You are the PM / BA role.

Current task:
- refine the current story into a clear, testable product specification for downstream roles

Highest priority order:
1. scope clarity
2. testable acceptance criteria
3. realistic V1 boundaries

Read and follow these resources:
{pm_resources(story_packet, project_mode)}

User task:
{task}

Story packet:
{safe_json(story_packet or {})}

Your agent context:
{render_agent_context(agent_context or {})}

Return plain text only.
Do not generate architecture or code.
""".strip()


def run_pm(task: str, agent_context: dict | None = None, story_packet: dict | None = None) -> str:
    prompt = build_pm_prompt(task=task, agent_context=agent_context, story_packet=story_packet)
    trace_block("PM PROMPT", prompt)
    response = call_role_llm("pm", prompt)
    trace_block("PM RESPONSE", response)
    return response
