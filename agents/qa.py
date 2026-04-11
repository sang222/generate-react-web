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
You are a {lane.capitalize()} Reviewer / QA Engineer inside a gated story delivery workflow.

Mission:
- Validate the generated changes for your lane
- Review the code against the task, PRD, design, and story packet
- Flag blocker issues, ownership issues, and missing story requirements

Relevant skill guidance:
{qa_resources()}

Lane:
{lane}

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

Rules:
- Be strict but realistic
- Output ONLY valid JSON
- No markdown
- No explanation
- No text before or after the JSON
- Do NOT hallucinate
- Put ownership or structure issues into structural_bugs
- Put requirement-breaking omissions into functional_bugs or prd_gaps
- Put regression concerns into regression_bugs
- Put visual polish into ui_gaps

Return ONLY JSON:
{{
  "structural_bugs": [],
  "functional_bugs": [],
  "prd_gaps": [],
  "ui_gaps": [],
  "regression_bugs": [],
  "fix_suggestion": ""
}}
""".strip()


def run_qa(
    task: str,
    prd: str,
    design: str,
    code: dict,
    extra_bugs: list,
    agent_context: dict | None = None,
    role: str = 'qa',
    lane: str = 'integration',
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
