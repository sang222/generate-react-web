from __future__ import annotations

from typing import Any, Dict, List

from memory.sanctum import append_curated_memory, append_session_log, load_agent_sanctum, set_first_breath_complete


def should_run_first_breath(agent_id: str = "dev-team-agent") -> bool:
    sanctum = load_agent_sanctum(agent_id)
    return not bool(sanctum.get("first_breath_complete"))


def run_first_breath(task: str, workflow_context: Dict[str, Any], agent_id: str = "dev-team-agent") -> Dict[str, Any]:
    territories: List[str] = []
    project_mode = workflow_context.get("project_mode", "new_project")
    if task:
        territories.append(f"Current primary request: {task.strip()[:280]}")
    territories.append(f"Preferred project mode right now: {project_mode}")
    if workflow_context.get("design"):
        territories.append("The owner values an implementation-aware architecture handoff.")
    if workflow_context.get("execution_error"):
        territories.append("The owner expects retryable debugging when builds fail.")
    if not territories:
        territories.append("The owner is still establishing the project territory.")
    notes = "## Learned territories\n" + "\n".join([f"- {item}" for item in territories])
    set_first_breath_complete(agent_id, notes)
    append_session_log(agent_id, f"First Breath completed.\n\n{notes}")
    for item in territories[:3]:
        append_curated_memory(agent_id, item)
    return {"agent_id": agent_id, "completed": True, "territories": territories}
