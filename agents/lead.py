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
You are an Engineering Lead.

Mission:
- Explain the release decision
- Suggest the best next action
- Use your own durable memory as supporting context when helpful

Relevant skill guidance:
{lead_resources(story_packet)}

Task:
{task}

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

Rules:
- The rule-based result is the final decision
- Do NOT override it
- Output ONLY valid JSON
- No markdown
- No explanation outside the JSON
- No text before or after the JSON
- No extra keys
- Focus on blockers, quality, and next steps
- Prioritize execution_error, structural_bugs, functional_bugs, and prd_gaps over minor UI issues
- Do not invent new release criteria beyond the provided rule_result and evidence

Return ONLY JSON:
{{
  "reason": "Explain why the current rule-based decision was reached.",
  "improvement": "State the most important next improvement or fix.",
  "ship_recommendation": "Recommend ship or fix, strictly aligned with the rule-based decision."
}}
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
