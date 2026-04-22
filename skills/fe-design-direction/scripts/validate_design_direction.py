from __future__ import annotations

from pathlib import Path

REQUIRED = ["Visual thesis", "Layout hierarchy", "Typography", "Color", "Accessibility", "Anti-slop"]

def validate(path: str) -> list[str]:
    text = Path(path).read_text(encoding="utf-8")
    return [f"Missing section: {item}" for item in REQUIRED if item.lower() not in text.lower()]
