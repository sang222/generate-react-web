from __future__ import annotations

from agents.base import architect_resources, render_agent_context, safe_json
from core.debug import trace_block
from core.llm import call_role_llm


def build_architect_prompt(task: str, prd: str, agent_context: dict | None = None, story_packet: dict | None = None) -> str:
    packet = story_packet or {}
    level = int(packet.get("project_level", 2) or 2)
    execution_mode = str(packet.get("execution_mode", "auto") or "auto")
    project_mode = packet.get("project_mode", (agent_context or {}).get("project_mode", "new_project"))
    lightweight = project_mode == "new_project" and execution_mode == "frontend_only" and level <= 2

    if lightweight:
        output_contract = """
Return concise plain text under 700 words.
Do not mention backend/database unless explicitly required.
Do not generate code.
""".strip()
    elif execution_mode == "fullstack":
        output_contract = """
Return ONLY valid JSON. No markdown. No prose.
Required JSON shape:
{
  "architecture_summary": "short summary",
  "topology_contract": {
    "app_topology": "monorepo",
    "frontend_apps": [
      {"name": "Readable app name", "root": "kebab-case-root", "purpose": "why this frontend exists"}
    ],
    "backend": {
      "root": "api",
      "framework": "express | spring_boot | fastapi | none",
      "database": "mongodb | postgres | sqlite | none"
    }
  },
  "lane_boundaries": {
    "frontend_allowed_roots": ["frontend-root-1", "frontend-root-2"],
    "backend_allowed_root": "api"
  },
  "implementation_notes": ["short notes only"]
}

Topology rules:
- Choose app roots from the requested product roles and explicit required structure.
- Do NOT use hardcoded cafe/travel/wedding defaults.
- Do NOT use legacy frontend/ + backend/ unless the user explicitly asks for those roots.
- Use kebab-case root names.
- Frontend roots must not overlap with backend root.
- If the task asks for Express/MongoDB, set backend.framework="express" and backend.database="mongodb".
- If the task does not clearly require multiple frontends, use one frontend root: "web".
Do not generate code.
""".strip()
    else:
        output_contract = "Return plain text only. Do not generate code."

    return f"""
You are the Architect role.

Current task:
- produce the architecture / integration plan for the current story only

Highest priority order:
1. baseline safety
2. configured stack alignment
3. clear lane boundaries
4. explicit topology contract for fullstack work

Read and follow these resources:
{architect_resources(story_packet, project_mode)}

Task:
{task}

Story packet:
{safe_json(packet)}

PRD:
{prd}

Your agent context:
{render_agent_context(agent_context or {})}

{output_contract}
""".strip()


def run_architect(task: str, prd: str, agent_context: dict | None = None, story_packet: dict | None = None) -> str:
    prompt = build_architect_prompt(task=task, prd=prd, agent_context=agent_context, story_packet=story_packet)
    trace_block("ARCHITECT PROMPT", prompt)
    response = call_role_llm("architect", prompt)
    trace_block("ARCHITECT RESPONSE", response)
    return response
