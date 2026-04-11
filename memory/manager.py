from __future__ import annotations

import re
from typing import Any, Dict, List

from core.db import get_agent_memories_collection, get_agent_profiles_collection
from memory.curation import curate_and_prune_sessions
from memory.first_breath import run_first_breath, should_run_first_breath
from memory.sanctum import (
    append_curated_memory,
    append_session_log,
    append_shared_memory,
    ensure_sanctum,
    load_agent_sanctum,
    load_shared_memory,
)
from memory.schemas import AGENT_IDS, MEMORY_AGENT_IDS, get_agent_type, get_default_agent_profile


class AgentMemoryManager:
    def ensure_bootstrap(self) -> None:
        ensure_sanctum()
        collection = get_agent_profiles_collection()
        for agent_id in AGENT_IDS:
            profile = get_default_agent_profile(agent_id)
            if not profile:
                continue
            collection.update_one(
                {"agent_id": agent_id},
                {
                    "$setOnInsert": {
                        "agent_id": agent_id,
                        "agent_type": profile.get("agent_type", "memory"),
                        "persona": profile.get("persona", ""),
                        "creed": profile.get("creed", ""),
                        "bond": profile.get("bond", {}),
                        "capabilities": profile.get("capabilities", []),
                    },
                },
                upsert=True,
            )

    def ensure_first_breath(self, task: str, workflow_context: Dict[str, Any]) -> Dict[str, Any]:
        if should_run_first_breath("dev-team-agent"):
            return run_first_breath(task=task, workflow_context=workflow_context, agent_id="dev-team-agent")
        return {"agent_id": "dev-team-agent", "completed": False, "territories": []}

    def load_context(self, agent_id: str, task: str, workflow_context: Dict[str, Any]) -> Dict[str, Any]:
        agent_type = get_agent_type(agent_id)
        sanctum = load_agent_sanctum(agent_id)
        shared = load_shared_memory()
        memories: List[Dict[str, Any]] = []
        if agent_type == "memory":
            memories = self._load_relevant_memories(agent_id, task, workflow_context, sanctum, shared)
        return {
            "profile": self._load_profile(agent_id),
            "sanctum": sanctum,
            "shared_memory": shared,
            "memories": memories,
            "project_mode": workflow_context.get("project_mode", "new_project"),
            "agent_type": agent_type,
            "is_memory_agent": agent_type == "memory",
        }

    def remember_run(self, result: Dict[str, Any]) -> None:
        self._append_session_logs(result)
        self._remember_shared_lessons(result)
        self._remember_developer_lessons(result)
        self._remember_pm_lessons(result)
        self._remember_architect_lessons(result)
        curate_and_prune_sessions()

    def _load_profile(self, agent_id: str) -> Dict[str, Any]:
        profile = get_agent_profiles_collection().find_one({"agent_id": agent_id}, {"_id": 0})
        if profile:
            return profile
        default_profile = get_default_agent_profile(agent_id)
        return {"agent_id": agent_id, **default_profile}

    def _load_relevant_memories(
        self,
        agent_id: str,
        task: str,
        workflow_context: Dict[str, Any],
        sanctum: Dict[str, Any],
        shared: Dict[str, Any],
        limit: int = 8,
    ) -> List[Dict[str, Any]]:
        collection = get_agent_memories_collection()
        terms = self._extract_terms(
            " ".join(
                [
                    task,
                    workflow_context.get("execution_error", ""),
                    workflow_context.get("fix_suggestion", ""),
                    workflow_context.get("release_status", ""),
                    workflow_context.get("project_mode", "new_project"),
                ]
            )
        )
        docs = list(collection.find({"agent_id": agent_id}, {"_id": 0}).limit(100))
        merged: List[Dict[str, Any]] = []
        for item in sanctum.get("memory_items", []) or []:
            merged.append(
                {
                    "agent_id": agent_id,
                    "title": item[:80],
                    "content": item,
                    "tags": ["sanctum", workflow_context.get("project_mode", "new_project")],
                    "importance": 0.88,
                    "source": "sanctum_memory_md",
                }
            )
        for item in sanctum.get("bond_items", []) or []:
            merged.append(
                {
                    "agent_id": agent_id,
                    "title": item[:80],
                    "content": item,
                    "tags": ["bond", workflow_context.get("project_mode", "new_project")],
                    "importance": 0.74,
                    "source": "sanctum_bond_md",
                }
            )
        for item in shared.get("memory_items", []) or []:
            merged.append(
                {
                    "agent_id": agent_id,
                    "title": item[:80],
                    "content": item,
                    "tags": ["shared_module_memory", workflow_context.get("project_mode", "new_project")],
                    "importance": 0.69,
                    "source": "shared_memory_md",
                }
            )
        merged.extend(docs)
        if not merged:
            return []
        scored: List[Dict[str, Any]] = []
        for doc in merged:
            score = self._score_memory(doc, terms, workflow_context)
            if score <= 0:
                continue
            enriched = dict(doc)
            enriched["score"] = round(score, 4)
            scored.append(enriched)
        scored.sort(key=lambda item: (item.get("score", 0), item.get("importance", 0)), reverse=True)
        unique: List[Dict[str, Any]] = []
        seen = set()
        for item in scored:
            key = (item.get("title", "").strip().lower(), item.get("content", "").strip().lower())
            if key in seen:
                continue
            seen.add(key)
            unique.append(item)
        return unique[:limit]

    def _score_memory(self, doc: Dict[str, Any], terms: List[str], workflow_context: Dict[str, Any]) -> float:
        text = " ".join(
            [
                str(doc.get("title", "")),
                str(doc.get("content", "")),
                " ".join(doc.get("tags", []) or []),
            ]
        ).lower()
        score = float(doc.get("importance", 0.5))
        if workflow_context.get("project_mode") and workflow_context.get("project_mode") in text:
            score += 0.2
        if workflow_context.get("project_mode") == doc.get("project_mode"):
            score += 0.25
        if workflow_context.get("execution_error") and any(tag in text for tag in ["build", "import", "export", "json", "required_files"]):
            score += 0.1
        score += min(sum(1 for term in terms if term in text) * 0.18, 0.72)
        return score

    def _append_session_logs(self, result: Dict[str, Any]) -> None:
        task = result.get("task", "")
        decision = result.get("final_decision", "")
        execution_error = result.get("execution_error", "")
        project_mode = result.get("project_mode", "new_project")
        qa_detail = result.get("qa_detail") or {}
        summary = (
            f"Task: {task}\n\n"
            f"Project mode: {project_mode}\n\n"
            f"Final decision: {decision}\n\n"
            f"Execution error: {execution_error or 'None'}\n\n"
            f"QA detail: {qa_detail}\n"
        )
        for agent_id in MEMORY_AGENT_IDS:
            append_session_log(agent_id, summary)

    def _remember_shared_lessons(self, result: Dict[str, Any]) -> None:
        if result.get("final_decision") == "DONE":
            append_shared_memory(
                f"Recent successful run pattern: project_mode={result.get('project_mode', 'new_project')} with release_status={result.get('release_status', '')}."
            )
        if result.get("execution_error"):
            append_shared_memory(f"Recurring blocker to watch: {str(result.get('execution_error', ''))[:220]}")

    def _remember_pm_lessons(self, result: Dict[str, Any]) -> None:
        qa_detail = result.get("qa_detail") or {}
        if qa_detail.get("prd_gaps"):
            lesson = "When requirements are underspecified, add explicit acceptance criteria for core user actions, states, and success conditions."
            self._upsert_memory(
                agent_id="pm",
                title="Acceptance criteria should close common PRD gaps",
                content=lesson,
                tags=["prd", "acceptance_criteria", "scope"],
                source_run_id=result.get("run_id", ""),
                importance=0.8,
                project_mode=result.get("project_mode", "new_project"),
            )
            append_curated_memory("pm", lesson)

    def _remember_architect_lessons(self, result: Dict[str, Any]) -> None:
        execution_error = (result.get("execution_error") or "").lower()
        if any(term in execution_error for term in ["import", "export", "missing required files"]):
            lesson = "Architect plans should call out the minimum file tree, import/export contracts, and concrete component ownership when build safety is at risk."
            self._upsert_memory(
                agent_id="architect",
                title="Architect plans should emphasize build-safe file manifests",
                content=lesson,
                tags=["build_safety", "file_tree", "imports"],
                source_run_id=result.get("run_id", ""),
                importance=0.81,
                project_mode=result.get("project_mode", "new_project"),
            )
            append_curated_memory("architect", lesson)

    def _remember_developer_lessons(self, result: Dict[str, Any]) -> None:
        execution_error = (result.get("execution_error") or "").strip()
        project_mode = result.get("project_mode", "new_project")
        if not execution_error:
            lesson = "Prefer a small, valid project with strict import/export consistency before adding polish."
            self._upsert_memory(
                agent_id="developer",
                title="Prefer minimal buildable output",
                content=lesson,
                tags=["stability", "json"],
                source_run_id=result.get("run_id", ""),
                importance=0.82,
                project_mode=project_mode,
            )
            append_curated_memory("developer", lesson)
            return
        lower_error = execution_error.lower()
        if "invalid project json" in lower_error:
            lesson = "Return only one JSON object with a non-empty files array and no commentary. Keep the schema minimal."
            self._upsert_memory(
                agent_id="developer",
                title="Avoid invalid developer JSON output",
                content=lesson,
                tags=["json", "output_contract"],
                source_run_id=result.get("run_id", ""),
                importance=0.96,
                project_mode=project_mode,
            )
            append_curated_memory("developer", lesson)
        if "missing required files" in lower_error:
            lesson = "Always include the minimum required file set before richer features."
            self._upsert_memory(
                agent_id="developer",
                title="Always include the minimum required file set",
                content=lesson,
                tags=["required_files", "build"],
                source_run_id=result.get("run_id", ""),
                importance=0.94,
                project_mode=project_mode,
            )
            append_curated_memory("developer", lesson)
        if "uri malformed" in lower_error:
            lesson = "Keep HTML shells minimal and standards-compliant. Do not inject encoded or malformed content into entry HTML."
            self._upsert_memory(
                agent_id="developer",
                title="Keep entry HTML minimal to avoid URI malformed errors",
                content=lesson,
                tags=["html", "uri"],
                source_run_id=result.get("run_id", ""),
                importance=0.9,
                project_mode=project_mode,
            )
            append_curated_memory("developer", lesson)
        if "import" in lower_error or "export" in lower_error:
            lesson = "Match default imports to default exports, named imports to named exports, and ensure every imported local path exists."
            self._upsert_memory(
                agent_id="developer",
                title="Protect import export consistency",
                content=lesson,
                tags=["imports", "exports", "build"],
                source_run_id=result.get("run_id", ""),
                importance=0.91,
                project_mode=project_mode,
            )
            append_curated_memory("developer", lesson)

    def _upsert_memory(
        self,
        agent_id: str,
        title: str,
        content: str,
        tags: List[str],
        source_run_id: str,
        importance: float,
        project_mode: str,
    ) -> None:
        collection = get_agent_memories_collection()
        collection.update_one(
            {"agent_id": agent_id, "title": title, "project_mode": project_mode},
            {
                "$set": {
                    "content": content,
                    "tags": tags,
                    "source_run_id": source_run_id,
                    "importance": importance,
                    "project_mode": project_mode,
                }
            },
            upsert=True,
        )

    def _extract_terms(self, text: str) -> List[str]:
        terms = re.findall(r"[a-zA-Z0-9_:+.-]{3,}", (text or "").lower())
        stop = {"the", "and", "for", "with", "that", "this", "from", "into", "project", "task", "new_project", "existing_project"}
        unique: List[str] = []
        seen = set()
        for term in terms:
            if term in stop or term in seen:
                continue
            seen.add(term)
            unique.append(term)
        return unique[:24]
