from __future__ import annotations

from agents.base import qa_resources, render_agent_context, safe_json
from core.debug import trace_block
from core.llm import call_role_llm


def build_qa_prompt(
    task: str,
    prd: str,
    design: str,
    code: dict,
    extra_bugs: list,
    agent_context: dict | None = None,
) -> str:
    return f"""
You are a QA Engineer.

Mission:
- Validate the generated React project
- Review the code against the task, PRD, and design
- Use your own durable memory as supporting context when relevant

Relevant skill guidance:
{qa_resources()}

Task:
{task}

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
- Do NOT decide DONE or RETRY
- Base findings on the provided code, PRD, and design
- Do not assume hidden files or behavior not present in the code
- If unsure, avoid inventing issues
- Do not repeat the same issue across multiple categories unless truly necessary
- Put minor presentation or UX polish issues into ui_gaps
- Put requirement-breaking omissions into structural_bugs, functional_bugs, or prd_gaps as appropriate
- fix_suggestion must be concise, actionable, and focused on the next developer iteration

Return ONLY JSON:
{{
  "structural_bugs": [],
  "functional_bugs": [],
  "prd_gaps": [],
  "ui_gaps": [],
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
) -> str:
    prompt = build_qa_prompt(
        task=task,
        prd=prd,
        design=design,
        code=code,
        extra_bugs=extra_bugs,
        agent_context=agent_context,
    )
    trace_block("QA PROMPT", prompt)
    response = call_role_llm("qa", prompt)
    trace_block("QA RESPONSE", response)
    return response
