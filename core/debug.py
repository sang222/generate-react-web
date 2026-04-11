from __future__ import annotations

import os
from datetime import datetime


TRACE_AGENTS = os.getenv("TRACE_AGENTS", "1") == "1"
TRACE_MAX_CHARS = int(os.getenv("TRACE_MAX_CHARS", "12000"))


def _now() -> str:
    return datetime.now().strftime("%H:%M:%S")


def _truncate(text: str, max_chars: int = TRACE_MAX_CHARS) -> str:
    text = (text or "").strip()
    if len(text) <= max_chars:
        return text
    return text[:max_chars].rstrip() + "\n\n...[truncated]"


def trace_block(title: str, content: str) -> None:
    if not TRACE_AGENTS:
        return

    print(f"\n[{_now()}] {'=' * 20} {title} {'=' * 20}", flush=True)
    print(_truncate(content), flush=True)
    print(f"[{_now()}] {'=' * 20} END {title} {'=' * 20}\n", flush=True)
