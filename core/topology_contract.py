from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Any, Dict, List, Tuple

from core.utils.json_utils import extract_json_object

VALID_BACKEND_FRAMEWORKS = {"express", "spring_boot", "fastapi", "none"}
VALID_DATABASE_ENGINES = {"mongodb", "postgres", "sqlite", "none"}
ROOT_RE = re.compile(r"^[a-z][a-z0-9]*(?:-[a-z0-9]+)*$")


@dataclass
class TopologyValidationResult:
    ok: bool
    warnings: List[str] = field(default_factory=list)
    errors: List[str] = field(default_factory=list)


def _normalize_root(value: str) -> str:
    clean = str(value or "").strip().replace("\\", "/").strip("/")
    clean = re.sub(r"\s+", "-", clean.lower())
    clean = re.sub(r"[^a-z0-9_\-/]", "-", clean)
    clean = clean.replace("_", "-")
    clean = re.sub(r"-+", "-", clean).strip("-")
    return clean


def _is_valid_root(root: str) -> bool:
    return bool(root) and "/" not in root and root not in {".", "src", "public", "node_modules"} and bool(ROOT_RE.match(root))


def _dedupe(values: List[str]) -> List[str]:
    seen: set[str] = set()
    out: List[str] = []
    for value in values:
        clean = _normalize_root(value)
        if clean and clean not in seen:
            seen.add(clean)
            out.append(clean)
    return out


def _detect_backend_framework(text: str, default: str = "express") -> str:
    low = text.lower()
    if any(term in low for term in ["spring boot", "spring_boot", "gradle", "java"]):
        return "spring_boot"
    if any(term in low for term in ["fastapi", "python api"]):
        return "fastapi"
    if any(term in low for term in ["express", "node.js", "nodejs", "node api", "package.json"]):
        return "express"
    return default


def _detect_database(text: str, default: str = "mongodb") -> str:
    low = text.lower()
    if any(term in low for term in ["mongodb", "mongo", "mongoose", "mongodb_uri"]):
        return "mongodb"
    if any(term in low for term in ["postgres", "postgresql", "jdbc:postgresql"]):
        return "postgres"
    if "sqlite" in low:
        return "sqlite"
    if "no database" in low or "database: none" in low:
        return "none"
    return default


def _line_roots_from_required_structure(text: str) -> Tuple[List[str], str]:
    """Extract explicit roots from user/architect text without domain keyword guesses.

    This intentionally looks for structural declarations like:
      - customer-web: minimal Vite React shell
      - api: minimal Express API shell

    It does not infer app roots from domain terms like cafe/wedding/travel.
    """
    frontend_roots: List[str] = []
    backend_root = ""

    ignored = {
        "package", "index", "main", "app", "src", "config", "server", "health",
        "mongodb", "mongoose", "authentication", "payment", "reports", "dashboard",
        "acceptance", "scope", "context", "goal", "api",  # api handled separately
    }

    for raw_line in text.splitlines():
        line = raw_line.strip()
        match = re.match(r"^[\-*•]\s*`?([A-Za-z][A-Za-z0-9_-]{1,40})`?\s*(?::|\-|$)", line)
        if not match:
            continue
        root = _normalize_root(match.group(1))
        if not root or root in ignored:
            continue
        low = line.lower()
        if root in {"api", "backend", "server"} or " api" in low or "express" in low or "backend" in low:
            if root in {"api", "backend", "server"}:
                backend_root = root
            continue
        if "web" in root or "frontend" in low or "react" in low or "vite" in low or "app shell" in low:
            frontend_roots.append(root)

    # Handle the common explicit backend root line separately because "api" is ignored above.
    for raw_line in text.splitlines():
        line = raw_line.strip()
        match = re.match(r"^[\-*•]\s*`?(api|backend|server)`?\s*(?::|\-|$)", line, flags=re.IGNORECASE)
        if match:
            backend_root = _normalize_root(match.group(1))
            break

    return _dedupe(frontend_roots), backend_root


def normalize_topology_contract(contract: Dict[str, Any] | None, text: str = "") -> Dict[str, Any]:
    data = dict(contract or {})
    frontend_apps = data.get("frontend_apps") or data.get("frontends") or []
    frontend_roots: List[str] = []

    if isinstance(frontend_apps, list):
        for item in frontend_apps:
            if isinstance(item, dict):
                root = item.get("root") or item.get("path") or item.get("directory")
            else:
                root = item
            if root:
                frontend_roots.append(str(root))

    if not frontend_roots:
        raw_roots = data.get("frontend_roots") or data.get("frontendRoots") or []
        if isinstance(raw_roots, str):
            frontend_roots = [part.strip() for part in raw_roots.split(",")]
        elif isinstance(raw_roots, list):
            frontend_roots = [str(item) for item in raw_roots]

    backend = data.get("backend") if isinstance(data.get("backend"), dict) else {}
    backend_root = str(backend.get("root") or data.get("backend_root") or data.get("backendRoot") or "").strip()
    backend_framework = str(backend.get("framework") or data.get("backend_framework") or data.get("backendFramework") or "").strip()
    database = str(backend.get("database") or data.get("database_engine") or data.get("databaseEngine") or "").strip()

    explicit_frontends, explicit_backend = _line_roots_from_required_structure(text or "")
    if not frontend_roots and explicit_frontends:
        frontend_roots = explicit_frontends
    if not backend_root and explicit_backend:
        backend_root = explicit_backend

    if not frontend_roots:
        frontend_roots = ["web"]
    if not backend_root:
        backend_root = "api"

    backend_framework = _normalize_root(backend_framework) if backend_framework else _detect_backend_framework(text or "")
    if backend_framework not in VALID_BACKEND_FRAMEWORKS:
        backend_framework = _detect_backend_framework(text or "")

    database = _normalize_root(database) if database else _detect_database(text or "")
    if database not in VALID_DATABASE_ENGINES:
        database = _detect_database(text or "")

    normalized_frontends = _dedupe(frontend_roots)
    normalized_backend = _normalize_root(backend_root) or "api"

    return {
        "app_topology": "monorepo" if normalized_backend else "single_frontend",
        "frontend_apps": [
            {"name": root.replace("-", " ").title(), "root": root, "purpose": "Frontend application"}
            for root in normalized_frontends
        ],
        "frontend_roots": normalized_frontends,
        "backend": {
            "root": normalized_backend,
            "framework": backend_framework,
            "database": database,
        },
        "backend_root": normalized_backend,
        "backend_framework": backend_framework,
        "database_engine": database,
    }


def validate_topology_contract(contract: Dict[str, Any]) -> TopologyValidationResult:
    warnings: List[str] = []
    errors: List[str] = []
    roots = contract.get("frontend_roots", []) or []
    backend_root = contract.get("backend_root") or (contract.get("backend") or {}).get("root")
    backend_framework = contract.get("backend_framework") or (contract.get("backend") or {}).get("framework")
    database = contract.get("database_engine") or (contract.get("backend") or {}).get("database")

    if not roots:
        errors.append("No frontend roots defined.")
    for root in roots:
        if not _is_valid_root(str(root)):
            errors.append(f"Invalid frontend root: {root}")
    if len(set(roots)) != len(roots):
        errors.append("Duplicate frontend roots detected.")
    if not _is_valid_root(str(backend_root or "")):
        errors.append(f"Invalid backend root: {backend_root}")
    if backend_root in roots:
        errors.append("Backend root overlaps with a frontend root.")
    if backend_framework not in VALID_BACKEND_FRAMEWORKS:
        warnings.append(f"Unknown backend framework {backend_framework}; runtime may fall back to Express conventions.")
    if database not in VALID_DATABASE_ENGINES:
        warnings.append(f"Unknown database engine {database}; runtime may use env-only config.")
    if len(roots) > 4:
        warnings.append("More than four frontend apps may be too large for one implementation story.")

    return TopologyValidationResult(ok=not errors, warnings=warnings, errors=errors)


def extract_topology_contract(design_text: str, fallback_text: str = "") -> Dict[str, Any]:
    obj = extract_json_object(design_text or "")
    contract = {}
    if isinstance(obj, dict):
        if isinstance(obj.get("topology_contract"), dict):
            contract = obj["topology_contract"]
        elif any(key in obj for key in ["frontend_apps", "frontend_roots", "backend"]):
            contract = obj
    return normalize_topology_contract(contract, text="\n".join([fallback_text or "", design_text or ""]))


def fallback_topology_for_execution_mode(execution_mode: str, task: str = "", story_packet: Dict[str, Any] | None = None) -> Dict[str, Any]:
    text_parts = [task or ""]
    packet = story_packet or {}
    for key in ["goal", "business_goal"]:
        if packet.get(key):
            text_parts.append(str(packet[key]))
    text = "\n".join(text_parts)
    if execution_mode == "fullstack":
        return normalize_topology_contract({}, text=text)
    if execution_mode == "frontend_only":
        return {
            "app_topology": "single_frontend",
            "frontend_apps": [{"name": "Web", "root": ".", "purpose": "Frontend app"}],
            "frontend_roots": ["."],
            "backend": {"root": "", "framework": "none", "database": "none"},
            "backend_root": "",
            "backend_framework": "none",
            "database_engine": "none",
        }
    return normalize_topology_contract({}, text=text)
