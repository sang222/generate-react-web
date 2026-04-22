from __future__ import annotations

from agents.base import architect_resources, render_agent_context, safe_json
from core.debug import trace_block
from core.llm import call_role_llm


def build_architect_prompt(task: str, prd: str, agent_context: dict | None = None, story_packet: dict | None = None) -> str:
    level = int((story_packet or {}).get("project_level", 2) or 2)
    execution_mode = str((story_packet or {}).get("execution_mode", "auto") or "auto")
    lightweight = (story_packet or {}).get("project_mode", "new_project") == "new_project" and execution_mode == "frontend_only" and level <= 2
    output_limit = "Keep the output under 700 words. Do not mention backend/database unless explicitly required." if lightweight else "Return plain text only."
    project_mode = (story_packet or {}).get("project_mode", (agent_context or {}).get("project_mode", "new_project"))
    return f"""
You are the Architect role.

Current task:
- produce the architecture / integration plan for the current story only

Highest priority order:
1. baseline safety
2. configured stack alignment
3. clear integration boundaries

Read and follow these resources:
{architect_resources(story_packet, project_mode)}

Task:
{task}

Story packet:
{safe_json(story_packet or {})}

PRD:
{prd}

Your agent context:
{render_agent_context(agent_context or {})}

{output_limit}
Do not generate code.
""".strip()


def run_architect(task: str, prd: str, agent_context: dict | None = None, story_packet: dict | None = None) -> str:
    prompt = build_architect_prompt(task=task, prd=prd, agent_context=agent_context, story_packet=story_packet)
    trace_block("ARCHITECT PROMPT", prompt)
    response = call_role_llm("architect", prompt)
    trace_block("ARCHITECT RESPONSE", response)
    return response
