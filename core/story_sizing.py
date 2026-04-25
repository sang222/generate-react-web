from __future__ import annotations

import re
from dataclasses import dataclass, asdict
from typing import Any, Dict, List


FULLSTACK_TERMS = {
    "fullstack", "backend", "api", "server", "database", "mongodb", "postgres",
    "mysql", "auth", "login", "admin", "staff", "customer", "dashboard",
    "order", "payment", "crud", "management", "account", "role", "permission",
}

FRONTEND_COMPLEX_TERMS = {
    "rsvp", "localstorage", "countdown", "gallery", "faq", "accordion", "timeline",
    "validation", "form", "animation", "responsive", "component", "components",
    "routing", "routes", "dashboard", "calendar", "upload", "search", "filter",
}

SECTION_PATTERNS = [
    r"\bhero\b", r"\bour story\b", r"\bevent details?\b", r"\bcountdown\b",
    r"\bgallery\b", r"\brsvp\b", r"\bguest information\b", r"\bfaq\b",
    r"\bfooter\b", r"\badmin\b", r"\bstaff\b", r"\bcustomer\b", r"\bmenu\b",
    r"\bcart\b", r"\bcheckout\b", r"\border\b", r"\blogin\b",
]

SCOPE_LIMITER_PATTERNS = [
    r"\bfoundation\b",
    r"\bfoundation only\b",
    r"\bphase\s*1\b",
    r"\bthis phase\b",
    r"\bthis story\b",
    r"\bshell only\b",
    r"\bapp shell\b",
    r"\bapi shell\b",
    r"\bminimal\b",
    r"\bplaceholder\b",
    r"\bout of scope\b",
    r"\bdo not implement\b",
    r"\bno auth\b",
    r"\bno order\b",
    r"\bno payment\b",
    r"\bno menu crud\b",
    r"\bno fake api\b",
    r"\blater stor(?:y|ies)\b",
    r"\bfuture stor(?:y|ies)\b",
    r"\bkeep output small\b",
    r"\bkeep this phase focused\b",
]

EXPLICIT_BIG_BANG_PATTERNS = [
    r"\bcomplete fullstack app\b",
    r"\bcomplete product\b",
    r"\bbuild the complete product\b",
    r"\bfull production system\b",
    r"\bimplement all features\b",
    r"\ball features\b",
    r"\bend-to-end.*one story\b",
    r"\beverything.*one story\b",
    r"\bfull app.*auth.*payment\b",
    r"\bcustomer.*staff.*admin.*backend.*auth.*payment\b",
]


@dataclass
class StorySizingResult:
    ok: bool
    status: str
    should_block: bool
    reason_code: str
    severity: str
    estimated_apps: int
    estimated_files: int
    estimated_sections: int
    matched_terms: List[str]
    scope_limiters: List[str]
    explicit_big_bang_terms: List[str]
    summary: str
    suggested_split: List[Dict[str, Any]]

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


def _lower_text(*parts: Any) -> str:
    return "\n".join(str(part or "") for part in parts).lower()


def _matches_patterns(text: str, patterns: List[str]) -> List[str]:
    return [pattern for pattern in patterns if re.search(pattern, text)]


def _count_apps(text: str) -> int:
    explicit_roots = ["customer-web", "staff-web", "admin-web", "api/"]
    count = sum(1 for term in explicit_roots if term in text)

    if "customer" in text and "staff" in text and "admin" in text:
        count = max(count, 3)
    if "3 website" in text or "three website" in text or "3 react" in text:
        count = max(count, 3)
    if "backend" in text or "api" in text or "server" in text:
        count += 1
    if "frontend" in text and count == 0:
        count = 1
    if "website" in text and count == 0:
        count = 1

    return max(1, min(count, 5))


def _count_sections(text: str) -> int:
    return sum(1 for pattern in SECTION_PATTERNS if re.search(pattern, text))


def _matched_terms(text: str) -> List[str]:
    terms = sorted((FULLSTACK_TERMS | FRONTEND_COMPLEX_TERMS))
    return [term for term in terms if term in text]


def _estimate_files(text: str, apps: int, sections: int, terms: List[str]) -> int:
    estimate = 5
    estimate += max(0, sections - 1) * 2
    estimate += max(0, apps - 1) * 5
    if any(term in terms for term in ["backend", "api", "server", "database", "mongodb"]):
        estimate += 8
    if any(term in terms for term in ["auth", "login", "role", "permission"]):
        estimate += 5
    if any(term in terms for term in ["crud", "order", "payment", "dashboard", "management"]):
        estimate += 6
    if any(term in terms for term in ["gallery", "rsvp", "countdown", "faq", "validation"]):
        estimate += 4
    return estimate


def _frontend_split() -> List[Dict[str, Any]]:
    return [
        {
            "story_id_suffix": "foundation",
            "title": "Build visual foundation",
            "scope": ["root Vite app", "hero", "event details", "basic story/content section", "footer", "responsive CSS"],
        },
        {
            "story_id_suffix": "interactive_features",
            "title": "Add interactive features",
            "scope": ["forms", "client validation", "localStorage persistence", "countdown", "accordion if needed"],
        },
        {
            "story_id_suffix": "content_polish",
            "title": "Add rich content and polish",
            "scope": ["gallery", "FAQ", "extra sections", "animations", "final responsive polish"],
        },
    ]


def _fullstack_split() -> List[Dict[str, Any]]:
    return [
        {
            "story_id_suffix": "foundation",
            "title": "Create monorepo foundation",
            "scope": ["web app shells", "api shell", "environment config", "health endpoint"],
        },
        {
            "story_id_suffix": "backend_core",
            "title": "Build backend core APIs",
            "scope": ["models", "validation", "core endpoints", "seed data", "error handling"],
        },
        {
            "story_id_suffix": "customer_web",
            "title": "Build customer web flow",
            "scope": ["customer screens", "API client integration", "main user flow"],
        },
        {
            "story_id_suffix": "staff_web",
            "title": "Build staff operations web",
            "scope": ["staff screens", "queue/status workflow", "role-scoped operations"],
        },
        {
            "story_id_suffix": "admin_web",
            "title": "Build admin management web",
            "scope": ["admin screens", "management features", "settings/reports if scoped"],
        },
        {
            "story_id_suffix": "integration_polish",
            "title": "Integration validation and polish",
            "scope": ["end-to-end validation", "responsive polish", "bug fixes", "release validation"],
        },
    ]


def _make_result(
    *,
    status: str,
    should_block: bool,
    reason_code: str,
    severity: str,
    apps: int,
    estimated_files: int,
    sections: int,
    terms: List[str],
    scope_limiters: List[str],
    explicit_big_bang_terms: List[str],
    summary: str,
    suggested_split: List[Dict[str, Any]],
) -> StorySizingResult:
    return StorySizingResult(
        ok=not should_block,
        status=status,
        should_block=should_block,
        reason_code=reason_code,
        severity=severity,
        estimated_apps=apps,
        estimated_files=estimated_files,
        estimated_sections=sections,
        matched_terms=terms,
        scope_limiters=scope_limiters,
        explicit_big_bang_terms=explicit_big_bang_terms,
        summary=summary,
        suggested_split=suggested_split,
    )


def evaluate_story_size(
    *,
    task: str,
    project_mode: str,
    execution_mode: str,
    story_packet: Dict[str, Any] | None = None,
    max_files: int = 24,
    max_sections: int = 7,
) -> StorySizingResult:
    packet = story_packet or {}
    text = _lower_text(task, packet)
    apps = _count_apps(text)
    sections = _count_sections(text)
    terms = _matched_terms(text)
    estimated_files = _estimate_files(text, apps, sections, terms)
    scope_limiters = _matches_patterns(text, SCOPE_LIMITER_PATTERNS)
    explicit_big_bang_terms = _matches_patterns(text, EXPLICIT_BIG_BANG_PATTERNS)

    is_frontend_only = execution_mode == "frontend_only" or packet.get("execution_mode") == "frontend_only"
    is_backend_only = execution_mode == "backend_only" or packet.get("execution_mode") == "backend_only"
    is_fullstack_mode = execution_mode == "fullstack" or packet.get("execution_mode") == "fullstack"

    has_fullstack_terms = bool(
        {"backend", "api", "server", "database", "mongodb"}.intersection(terms)
        and {"customer", "staff", "admin", "auth", "order", "payment", "crud"}.intersection(terms)
    )
    is_fullstack_like = bool(is_fullstack_mode or (not is_frontend_only and not is_backend_only and (apps >= 3 or has_fullstack_terms)))

    too_many_files = estimated_files > max_files
    too_many_sections = is_frontend_only and sections > max_sections
    high_complexity = bool(is_fullstack_like or too_many_files or too_many_sections)
    has_scope_limiter = bool(scope_limiters)
    explicit_big_bang = bool(explicit_big_bang_terms)

    if not high_complexity:
        return _make_result(
            status="PASS",
            should_block=False,
            reason_code="STORY_SIZE_OK",
            severity="NONE",
            apps=apps,
            estimated_files=estimated_files,
            sections=sections,
            terms=terms,
            scope_limiters=scope_limiters,
            explicit_big_bang_terms=explicit_big_bang_terms,
            summary="Story size is within the single-story implementation budget.",
            suggested_split=[],
        )

    split = _fullstack_split() if is_fullstack_like else _frontend_split()

    # Advisory-first rule:
    # - Large scoped/foundation/phase stories should continue with WARN.
    # - Hard block only explicit big-bang requests without a scope limiter.
    if explicit_big_bang and not has_scope_limiter:
        return _make_result(
            status="FAIL",
            should_block=True,
            reason_code="STORY_TOO_LARGE_BIG_BANG",
            severity="BLOCKER",
            apps=apps,
            estimated_files=estimated_files,
            sections=sections,
            terms=terms,
            scope_limiters=scope_limiters,
            explicit_big_bang_terms=explicit_big_bang_terms,
            summary="Story appears to request a big-bang implementation that is too large for one safe LLM response.",
            suggested_split=split,
        )

    reason = "FULLSTACK_STORY_LARGE_WARN" if is_fullstack_like else "FRONTEND_STORY_LARGE_WARN"
    summary = (
        "Story is large, but it is allowed to continue as a scoped implementation. "
        "Runtime should enforce lane budgets, deterministic validation, and invalid-output retry handling."
    )

    return _make_result(
        status="WARN",
        should_block=False,
        reason_code=reason,
        severity="WARNING",
        apps=apps,
        estimated_files=estimated_files,
        sections=sections,
        terms=terms,
        scope_limiters=scope_limiters,
        explicit_big_bang_terms=explicit_big_bang_terms,
        summary=summary,
        suggested_split=split,
    )


def format_story_split(result: StorySizingResult) -> str:
    lines = [result.summary]
    lines.append(
        f"Estimated apps={result.estimated_apps}, sections={result.estimated_sections}, files={result.estimated_files}."
    )
    if result.matched_terms:
        lines.append("Matched complexity terms: " + ", ".join(result.matched_terms[:20]))
    if result.scope_limiters:
        lines.append("Scope limiters: " + ", ".join(result.scope_limiters[:12]))
    if result.explicit_big_bang_terms:
        lines.append("Explicit big-bang terms: " + ", ".join(result.explicit_big_bang_terms[:12]))
    if result.suggested_split:
        lines.append("Suggested split:")
        for idx, item in enumerate(result.suggested_split, start=1):
            scope = "; ".join(item.get("scope", []))
            lines.append(f"{idx}. {item.get('title', 'Story')} ({item.get('story_id_suffix', 'story')}): {scope}")
    return "\n".join(lines)
