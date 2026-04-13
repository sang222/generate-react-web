from __future__ import annotations

import argparse
import sys

from core.skill_candidates import (
    VALID_DECISIONS,
    list_skill_candidates,
    render_skill_candidate,
    review_skill_candidate,
)


def cmd_list() -> int:
    candidates = list_skill_candidates()
    if not candidates:
        print("No skill candidates found.")
        return 0

    for item in candidates:
        print(
            f"{item.get('candidate_id', '')}  "
            f"{item.get('target', '')}  "
            f"{item.get('status', '')}  "
            f"{item.get('summary', '')}"
        )
    return 0


def cmd_show(candidate_id: str) -> int:
    try:
        print(render_skill_candidate(candidate_id), end="")
        return 0
    except FileNotFoundError as exc:
        print(str(exc), file=sys.stderr)
        return 1


def cmd_review(candidate_id: str, decision: str, note: str, reviewer: str) -> int:
    try:
        record = review_skill_candidate(
            candidate_id,
            decision=decision,  # type: ignore[arg-type]
            note=note,
            reviewed_by=reviewer,
        )
        print(f"Reviewed {candidate_id}: {record.get('decision', '')}")
        if record.get("applied"):
            print(f"Patch applied via {record.get('apply_mode', '')}")
        return 0
    except FileNotFoundError as exc:
        print(str(exc), file=sys.stderr)
        return 1
    except ValueError as exc:
        print(str(exc), file=sys.stderr)
        return 2


def main() -> int:
    parser = argparse.ArgumentParser(description="Skill candidate CLI")
    parser.add_argument("--list", action="store_true", help="List all skill candidates")
    parser.add_argument("--show", help="Show one skill candidate by id")
    parser.add_argument("--review", help="Review one skill candidate by id")
    parser.add_argument("--decision", choices=list(VALID_DECISIONS), help="Review decision")
    parser.add_argument("--note", default="", help="Optional review note")
    parser.add_argument("--reviewed-by", default="human", help="Reviewer name")
    args = parser.parse_args()

    if args.list:
        return cmd_list()
    if args.show:
        return cmd_show(args.show)
    if args.review:
        if not args.decision:
            print("--review requires --decision", file=sys.stderr)
            return 2
        return cmd_review(args.review, args.decision, args.note, args.reviewed_by)

    parser.print_help()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
