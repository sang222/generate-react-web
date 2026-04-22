from __future__ import annotations

import uuid
from typing import Any

from core.config import get_system_target, load_module_config
from core.runtime.checkpoints import Checkpointer
from core.runtime.graph import RuntimeGraph
from core.runtime.nodes.legacy_orchestrator_node import LegacyOrchestratorNode
from core.runtime.state import ExecutionState, RunIdentity, RuntimeState
from core.runtime.transitions import TransitionTable


def create_initial_runtime_state(
    *,
    task: str,
    project_mode: str = "new_project",
    project_id: str | None = None,
    epic_id: str | None = None,
    story_id: str | None = None,
    story_name: str | None = None,
    resume_from: str | None = None,
    depends_on: list[str] | None = None,
    execution_mode: str | None = None,
) -> RuntimeState:
    project = project_id or "demo_project"
    epic = epic_id or "EPIC-001"
    story = story_id or "STORY-001"
    config = load_module_config()
    state = RuntimeState(
        identity=RunIdentity(
            project_id=project,
            epic_id=epic,
            story_id=story,
            run_id=str(uuid.uuid4()),
        ),
        task=task,
        project_mode=project_mode,
        execution_mode=execution_mode or "auto",
        system_target=get_system_target(config),
        execution=ExecutionState(phase="legacy_orchestrator"),
        raw_context={
            "story_name": story_name or story,
            "resume_from": resume_from,
            "depends_on": depends_on or [],
        },
    )
    return state


def create_delivery_runtime(*, checkpoint_root: str = "project_state") -> RuntimeGraph:
    return RuntimeGraph(
        nodes={"legacy_orchestrator": LegacyOrchestratorNode()},
        transitions=TransitionTable(),
        checkpointer=Checkpointer(checkpoint_root),
    )


def run_delivery_runtime(**kwargs: Any) -> dict[str, Any]:
    state = create_initial_runtime_state(**kwargs)
    final_state = create_delivery_runtime().run(state)
    return final_state.raw_context or final_state.to_dict()
