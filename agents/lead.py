from __future__ import annotations

from agents.base import compact_history, lead_resources, render_agent_context, safe_json
from core.debug import trace_block
from core.llm import call_role_llm


def build_lead_prompt(
    task: str,
    prd: str,
    design: str,
    code: dict,
    qa_detail: dict,
    execution_error: str,
    loop_count: int,
    max_loop: int,
    rule_result: dict,
    history: list,
    agent_context: dict | None = None,
    story_packet: dict | None = None,
) -> str:
    return f"""
You are the Lead role.

Current task:
- explain the final decision for the current story and name the highest priority next action

Highest priority order:
1. obey rule-based decision
2. release safety
3. clarity of next action

Read and follow these resources:
{lead_resources(story_packet, (story_packet or {}).get('project_mode', 'new_project'))}

Task:
{task}

Story packet:
{safe_json(story_packet or {})}

PRD:
{prd}

Design:
{design}

Code summary:
{safe_json(code)}

QA detail:
{safe_json(qa_detail)}

Execution error:
{execution_error}

Loop count:
{loop_count}/{max_loop}

Rule-based decision:
{safe_json(rule_result)}

Your agent context:
{render_agent_context(agent_context or {})}

Recent history:
{compact_history(history)}

Return ONLY valid JSON.
No markdown. Do not override the rule-based decision.
""".strip()


def run_lead(
    task: str,
    prd: str,
    design: str,
    code: dict,
    qa_detail: dict,
    execution_error: str,
    loop_count: int,
    max_loop: int,
    rule_result: dict,
    history: list,
    agent_context: dict | None = None,
    story_packet: dict | None = None,
) -> str:
    prompt = build_lead_prompt(
        task=task,
        prd=prd,
        design=design,
        code=code,
        qa_detail=qa_detail,
        execution_error=execution_error,
        loop_count=loop_count,
        max_loop=max_loop,
        rule_result=rule_result,
        history=history,
        agent_context=agent_context,
        story_packet=story_packet,
    )
    trace_block("LEAD PROMPT", prompt)
    response = call_role_llm("lead", prompt)
    trace_block("LEAD RESPONSE", response)
    return response
