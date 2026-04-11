from __future__ import annotations

import json
from typing import Any

from core.llm import call_qwen
from core.debug import trace_block

DEFAULT_MODEL = "qwen3:8b"


def _safe_json(data: Any) -> str:
    try:
        return json.dumps(data, ensure_ascii=False, indent=2)
    except Exception:
        return "{}"


def build_qa_prompt(
    task: str,
    prd: str,
    design: str,
    code: dict,
    extra_bugs: list,
    memory_context: str = "[]",
) -> str:
    return f"""
You are a QA Engineer.

Your job:
- Validate the generated React project
- Review the code against the task, PRD, and design
- Use similar past execution memory as supporting context when relevant

Task:
{task}

PRD:
{prd}

Design:
{design}

Code:
{_safe_json(code)}

Pre-detected issues:
{_safe_json(extra_bugs)}

Similar past execution memory:
{memory_context}

Evaluate in 4 areas:

1. STRUCTURAL
- Missing files
- Invalid imports
- Broken setup
- Invalid package structure
- Missing referenced files

2. FUNCTIONAL
- Logic correctness
- State handling
- Event handling
- Persistence or derived behavior if required

3. PRD COVERAGE
- Missing features
- Wrong implementation
- Missing flows
- Scope mismatch

4. UI COVERAGE
- Missing UI elements
- Missing empty/loading/error states when required
- Missing access to required user actions

Rules:
- Be strict but realistic
- Output ONLY valid JSON
- No markdown
- No explanation
- No text before or after the JSON
- No extra keys
- Do NOT hallucinate
- Do NOT decide DONE/RETRY
- Use memory only as a hint, not as proof
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
    memory_context: str = "[]",
) -> str:
    prompt = build_qa_prompt(
        task=task,
        prd=prd,
        design=design,
        code=code,
        extra_bugs=extra_bugs,
        memory_context=memory_context,
    )
    trace_block("QA PROMPT", prompt)
    response = call_qwen(prompt, DEFAULT_MODEL)
    trace_block("QA RESPONSE", response)
    return response
