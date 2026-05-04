from __future__ import annotations

from typing import Any, Dict, Iterable

from core.topology_contract import normalize_topology_contract


def _apply_topology_contract(target: Dict[str, Any], topology_contract: Dict[str, Any]) -> Dict[str, Any]:
    topology = normalize_topology_contract(topology_contract, text="")
    target["effective_mode"] = "fullstack"
    target["layout"] = "monorepo"
    target["app_topology"] = topology.get("app_topology", "monorepo")
    target["frontend_roots"] = list(topology.get("frontend_roots") or ["web"])
    target["backend_root"] = topology.get("backend_root") or "api"
    target["backend_framework"] = topology.get("backend_framework") or "express"
    target["database_engine"] = topology.get("database_engine") or "mongodb"

    if target["backend_framework"] == "express":
        target["backend_language"] = "node"
        target["backend_build_tool"] = "npm"
        target["database_orm"] = "none"
    elif target["backend_framework"] == "spring_boot":
        target["backend_language"] = "java"
        target["backend_build_tool"] = "gradle"
        target.setdefault("database_orm", "jpa")
    elif target["backend_framework"] == "fastapi":
        target["backend_language"] = "python"
        target["backend_build_tool"] = "pip"
        target.setdefault("database_orm", "none")

    target["frontend_root"] = ""
    target["topology_contract"] = topology
    return target


def derive_effective_target(
    system_target: Dict[str, Any],
    active_lanes: Iterable[str] | None = None,
    topology_contract: Dict[str, Any] | None = None,
) -> Dict[str, Any]:
    target = dict(system_target or {})
    lanes = set(active_lanes or [])

    if not lanes:
        return target

    has_frontend = "frontend" in lanes
    has_backend = "backend" in lanes

    if has_frontend and has_backend:
        if topology_contract:
            return _apply_topology_contract(target, topology_contract)
        target["effective_mode"] = "fullstack"
        target.setdefault("frontend_root", "frontend")
        target.setdefault("backend_root", "backend")
        return target

    if has_frontend:
        target["effective_mode"] = "frontend_only"
        target["frontend_root"] = "."
        target["backend_language"] = "none"
        target["backend_framework"] = "none"
        target["backend_build_tool"] = "none"
        target["database_engine"] = "none"
        target["database_orm"] = "none"
        return target

    if has_backend:
        target["effective_mode"] = "backend_only"
        target["frontend_stack"] = "none"
        target.setdefault("backend_root", "backend")
        return target

    return target


def resolve_effective_target(
    system_target: Dict[str, Any],
    active_lanes: Iterable[str] | None = None,
    *,
    task: str | None = None,
    story_packet: Dict[str, Any] | None = None,
    topology_contract: Dict[str, Any] | None = None,
) -> Dict[str, Any]:
    packet = story_packet or {}
    topology = topology_contract or packet.get("topology_contract")
    return derive_effective_target(system_target, active_lanes, topology_contract=topology if isinstance(topology, dict) else None)
