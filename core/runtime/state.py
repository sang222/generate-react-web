from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any, Literal

RuntimePhase = Literal[
    "bootstrap",
    "legacy_orchestrator",
    "planning",
    "design",
    "brownfield_readiness",
    "implementation",
    "review",
    "candidate_learning",
    "delivery",
    "blocked",
    "done",
]


@dataclass
class RunIdentity:
    project_id: str
    epic_id: str
    story_id: str
    run_id: str


@dataclass
class ExecutionState:
    phase: RuntimePhase = "bootstrap"
    loop_count: int = 0
    max_loop: int = 3
    retry_reason: str = ""
    execution_error: str = ""
    block_reason: str = ""
    final_decision: str = ""


@dataclass
class ArtifactState:
    artifacts: dict[str, str] = field(default_factory=dict)
    code_files: list[dict[str, str]] = field(default_factory=list)


@dataclass
class ReviewState:
    qa_detail: dict[str, list[str]] = field(default_factory=dict)
    fix_suggestion: str = ""
    release_status: str = ""
    severity: str = ""


@dataclass
class RuntimeState:
    identity: RunIdentity
    task: str
    project_mode: str = "new_project"
    execution_mode: str = "auto"
    story_packet: dict[str, Any] = field(default_factory=dict)
    system_target: dict[str, Any] = field(default_factory=dict)
    effective_target: dict[str, Any] = field(default_factory=dict)
    active_lanes: list[str] = field(default_factory=list)
    gates: dict[str, Any] = field(default_factory=dict)
    artifacts: ArtifactState = field(default_factory=ArtifactState)
    review: ReviewState = field(default_factory=ReviewState)
    recovery: dict[str, Any] = field(default_factory=dict)
    token_usage: dict[str, Any] = field(default_factory=dict)
    execution: ExecutionState = field(default_factory=ExecutionState)
    raw_context: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_legacy_context(cls, context: dict[str, Any]) -> "RuntimeState":
        state = cls(
            identity=RunIdentity(
                project_id=str(context.get("project_id", "unknown_project")),
                epic_id=str(context.get("epic_id", "unknown_epic")),
                story_id=str(context.get("story_id", "unknown_story")),
                run_id=str(context.get("run_id", "unknown_run")),
            ),
            task=str(context.get("task", "")),
            project_mode=str(context.get("project_mode", "new_project")),
            execution_mode=str(context.get("execution_mode", "auto")),
            story_packet=context.get("story_packet", {}) or {},
            system_target=context.get("system_target", {}) or {},
            effective_target=context.get("effective_target", {}) or {},
            active_lanes=list(context.get("active_lanes", []) or []),
            gates=context.get("gate_state", {}) or {},
            raw_context=dict(context),
        )
        state.execution.loop_count = int(context.get("loop_count", 0) or 0)
        state.execution.retry_reason = str(context.get("retry_reason", "") or "")
        state.execution.execution_error = str(context.get("execution_error", "") or "")
        state.execution.block_reason = str(context.get("blocked_reason", context.get("block_reason", "")) or "")
        state.execution.final_decision = str(context.get("final_decision", "") or "")
        state.review.release_status = str(context.get("release_status", "") or "")
        state.review.severity = str(context.get("severity", "") or "")
        state.review.qa_detail = context.get("qa_detail", {}) or {}
        state.review.fix_suggestion = str(context.get("fix_suggestion", "") or "")
        state.artifacts.code_files = ((context.get("code", {}) or {}).get("files", []) or [])
        return state
