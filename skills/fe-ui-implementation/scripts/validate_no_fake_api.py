from __future__ import annotations

from pathlib import Path

SUSPICIOUS = ["fake", "mock revenue", "demo stats", "lorem ipsum", "placeholder testimonial"]

def validate_file(path: str) -> list[str]:
    text = Path(path).read_text(encoding="utf-8", errors="ignore").lower()
    return [f"Suspicious fake data marker: {marker}" for marker in SUSPICIOUS if marker in text]
