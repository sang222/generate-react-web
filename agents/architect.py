from __future__ import annotations

from core.llm import call_gemma

DEFAULT_MODEL = "gemma3:4b"


def build_architect_prompt(task: str, prd: str, memory_context: str = "[]") -> str:
    return f"""
You are a Senior Software Architect.

Your job:
- Convert the PRD into a clear, implementation-oriented React plan
- Reuse useful lessons from similar past executions when relevant
- Avoid repeating past mistakes
- Give a concrete design that a developer can implement directly with minimal guessing

Task:
{task}

PRD:
{prd}

Similar past execution memory:
{memory_context}

Output format:

1. Architecture Overview
2. Tech Stack
3. App Structure
4. Component Design
5. State Management
6. Data Flow
7. Validation Rules
8. Error Handling
9. Suggested File Tree
10. Implementation Notes

Rules:
- Use React + Vite
- Keep architecture simple, practical, and scoped to the PRD
- Do not expand scope beyond V1 unless clearly required
- File tree must be concrete and usable
- Encourage modular structure for medium or complex tasks
- Clearly describe component responsibilities
- Clearly describe where state should live and how data should flow
- Prefer local state unless broader shared state is truly needed
- Mention important UI states such as empty, loading, error, and validation when relevant
- Mention any build-safety concerns such as file placement, import paths, and dependency practicality
- Avoid unnecessary abstraction or overengineering
- Do NOT generate code

Return only plain text.
""".strip()


def run_architect(task: str, prd: str, memory_context: str) -> str:
    prompt = build_architect_prompt(
        task=task,
        prd=prd,
        memory_context=memory_context,
    )
    response = call_gemma(prompt, model=DEFAULT_MODEL)
    return response
