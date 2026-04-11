from __future__ import annotations

import json
from typing import Any, Dict, List

from core.llm import call_qwen

DEFAULT_MODEL = "qwen3:8b"


def _safe_json(data: Any) -> str:
    try:
        return json.dumps(data, ensure_ascii=False, indent=2)
    except Exception:
        return "{}"


def _compact_history(history: List[Dict[str, Any]], limit: int = 6) -> str:
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


def build_developer_prompt(
    task: str,
    prd: str,
    design: str,
    bugs: list,
    fix_suggestion: str,
    execution_error: str,
    history: list,
    memory_context: str = "[]",
) -> str:
    return f"""
You are a Senior React Developer.

Your ONLY job:
- Generate a complete runnable React (Vite) project
- Fix issues from previous iterations
- Reuse relevant lessons from similar past executions
- Follow the PRD and design as the primary source of truth

Task:
{task}

PRD:
{prd}

Design:
{design}

Known issues:
{_safe_json(bugs)}

Fix suggestion:
{fix_suggestion}

Execution error:
{execution_error}

Similar past execution memory:
{memory_context}

Recent history:
{_compact_history(history)}

STRICT RULES:
- Output ONLY valid JSON
- No markdown
- No explanation
- No extra fields
- Do NOT report bugs or analysis
- Do NOT wrap the JSON in code fences
- Do NOT add text before or after the JSON

Required schema:
{{
  "files": [
    {{
      "path": "string",
      "content": "string"
    }}
  ]
}}

Minimum required files:
- package.json
- index.html
- src/main.jsx
- src/App.jsx
- src/index.css

Modularity rules:
- Split into components if app has multiple features
- Put UI pieces in src/components
- Put logic in hooks/utils if needed
- Do NOT put everything in App.jsx for non-trivial apps
- Follow the design file tree if provided
- Avoid repeating mistakes seen in similar past executions

Implementation rules:
- Use functional components
- Use createRoot in main.jsx
- Ensure imports are valid
- Ensure all referenced files exist
- Every imported local file must exist in the output
- Every exported symbol must be imported with the correct default or named form
- Do not use named import for a default export
- Do not use default import for a named export
- If a file is imported, that file must be generated
- If a component or utility is referenced, it must be defined and exported correctly
- Keep import paths relative, exact, and buildable
- Re-check import/export consistency across all generated files before finishing
- package.json must contain a valid React + Vite setup and build scripts
- index.html must be a valid minimal Vite HTML entry
- Do not include malformed encoded URLs, unusual asset links, or unnecessary external references in index.html
- Every file content must be complete and usable
- Do not output placeholders like TODO, omitted, or pseudo-code
- Keep it simple but correct
- Do not add unnecessary features outside the requested scope unless needed for correctness

Styling and UI rules:
- Use Tailwind CSS for styling
- Use a clean modern layout with good spacing, rounded corners, subtle shadows, and responsive sections
- Prefer polished, minimal, production-friendly UI
- Generate src/index.css and configure it correctly for Tailwind
- Use utility classes consistently instead of large custom CSS unless truly needed

Animation rules:
- Use Motion for React for small meaningful animations such as fade-in, hover feedback, or list transitions
- Keep animations subtle and smooth
- Avoid heavy, flashy, or distracting animations
- Motion should improve UX, not dominate it

Framework setup rules:
- package.json must include valid dependencies for React, Vite, Tailwind CSS, and Motion for React
- The project setup must be compatible with React + Vite
- main.jsx must import the main CSS file
- Tailwind setup must be valid for the generated project
- Motion should only be used where it adds clear UI value

Preferred React/Vite baseline:
- main.jsx should render App with ReactDOM.createRoot(document.getElementById("root"))
- index.html should include only a root div and a module script to /src/main.jsx unless the task clearly requires more
- Use common Vite React conventions

Self-check before finalizing:
- All required files exist
- All imported local modules exist
- All imports match the corresponding exports
- No broken relative paths
- No missing components, hooks, or utilities
- Tailwind setup is valid
- Motion imports are valid
- The project should be able to run npm install and npm run build successfully

Return ONLY JSON.
""".strip()


def run_developer(
    task: str,
    prd: str,
    design: str,
    bugs: list,
    fix_suggestion: str,
    execution_error: str,
    history: list,
    memory_context: str = "[]",
) -> str:
    prompt = build_developer_prompt(
        task=task,
        prd=prd,
        design=design,
        bugs=bugs,
        fix_suggestion=fix_suggestion,
        execution_error=execution_error,
        history=history,
        memory_context=memory_context,
    )
    response = call_qwen(prompt, DEFAULT_MODEL)
    return response
