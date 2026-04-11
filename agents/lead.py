from __future__ import annotations

import json
from typing import Any, Dict, List

from core.llm import call_gemma
from core.debug import trace_block

DEFAULT_MODEL = "gemma3:4b"


def _safe_json(data: Any) -> str:
    try:
        return json.dumps(data, ensure_ascii=False, indent=2)
    except Exception:
        return "{}"


def _compact_history(history: List[Dict[str, Any]], limit: int = 8) -> str:
    if not history:
        return "[]"

    sliced = history[-limit:]
    simplified = []

    for item in sliced:
        simplified.append(
            {
                "loop": item.get("loop", 0),
                "release_status": item.get("release_status", ""),
                "severity": item.get("severity", ""),
                "execution_error": item.get("execution_error", ""),
                "qa_detail": item.get("qa_detail", {}),
                "fix_suggestion": item.get("fix_suggestion", ""),
            }
        )

    return _safe_json(simplified)


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
    memory_context: str = "[]",
) -> str:
    return f"""
You are an Engineering Lead.

Your job:
- Explain the release decision
- Suggest the best next action
- Use similar past execution memory as supporting context when helpful

Task:
{task}

PRD:
{prd}

Design:
{design}

Code summary:
{_safe_json(code)}

QA detail:
{_safe_json(qa_detail)}

Execution error:
{execution_error}

Loop count:
{loop_count}/{max_loop}

Rule-based decision:
{_safe_json(rule_result)}

Similar past execution memory:
{memory_context}

Recent history:
{_compact_history(history)}

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
- Use memory only as supporting context, not as proof
- Be practical and production-minded
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
    memory_context: str = "[]",
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
        memory_context=memory_context,
    )
    trace_block("LEAD PROMPT", prompt)
    response = call_gemma(prompt, DEFAULT_MODEL)
    trace_block("LEAD RESPONSE", response)
    return response
