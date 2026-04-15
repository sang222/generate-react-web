from __future__ import annotations

import argparse
from pathlib import Path


def _print_file(path: Path, title: str) -> None:
    print(f"== {title} ==")
    if not path.exists():
        print("(empty)")
        print()
        return
    print(path.read_text(encoding="utf-8").strip() or "(empty)")
    print()


def main() -> int:
    parser = argparse.ArgumentParser(description="Show adaptive recovery history files.")
    parser.add_argument("--root", default=".", help="Project root")
    args = parser.parse_args()

    root = Path(args.root)
    hist = root / "skill_history"
    _print_file(hist / "candidate_runs.jsonl", "Candidate runs")
    _print_file(hist / "candidate_reviews.jsonl", "Candidate reviews")
    _print_file(hist / "auto_applied.jsonl", "Auto applied")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
