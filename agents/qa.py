from __future__ import annotations

from agents.base import qa_resources, render_agent_context, safe_json
from core.debug import trace_block
from core.llm import call_role_llm


def build_qa_prompt(
    role: str,
    lane: str,
    task: str,
    prd: str,
    design: str,
    code: dict,
    extra_bugs: list,
    agent_context: dict | None = None,
    story_packet: dict | None = None,
) -> str:
    return f"""
You are the {lane.capitalize()} Reviewer / QA role.

Current task:
- review the current story output for your lane and categorize findings correctly

Highest priority order:
1. blocker and regression safety
2. acceptance coverage
3. contract correctness

Read and follow these resources:
{qa_resources(story_packet, (story_packet or {}).get('project_mode', 'new_project'), role)}

Task:
{task}

Story packet:
{safe_json(story_packet or {})}

PRD:
{prd}

Design:
{design}

Code:
{safe_json(code)}

Pre-detected issues:
{safe_json(extra_bugs)}

Your agent context:
{render_agent_context(agent_context or {})}

Return ONLY valid JSON.
No markdown. No prose. No extra keys.
""".strip()


def run_qa(
    task: str,
    prd: str,
    design: str,
    code: dict,
    extra_bugs: list,
    agent_context: dict | None = None,
    role: str = "qa",
    lane: str = "integration",
    story_packet: dict | None = None,
) -> str:
    prompt = build_qa_prompt(
        role=role,
        lane=lane,
        task=task,
        prd=prd,
        design=design,
        code=code,
        extra_bugs=extra_bugs,
        agent_context=agent_context,
        story_packet=story_packet,
    )
    trace_block(f"{role.upper()} PROMPT", prompt)
    response = call_role_llm(role, prompt)
    trace_block(f"{role.upper()} RESPONSE", response)
    return response
