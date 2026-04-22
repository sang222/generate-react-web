from __future__ import annotations

import argparse
import json
from pathlib import Path


def main() -> int:
    parser = argparse.ArgumentParser(description="Show token usage for a story")
    parser.add_argument("--project-id", required=True)
    parser.add_argument("--story-id", required=True)
    args = parser.parse_args()

    path = Path("project_state") / args.project_id / "stories" / args.story_id / "token_usage.jsonl"
    print("Q: Token usage file?")
    print(f"A: {path}")
    if not path.exists():
        print("Q: Token usage records?")
        print("A: none")
        return 0

    total = 0
    by_role: dict[str, int] = {}
    count = 0
    for line in path.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        try:
            item = json.loads(line)
        except Exception:
            continue
        count += 1
        tokens = int(item.get("estimated_total_tokens", 0) or 0)
        total += tokens
        role = str(item.get("role", "unknown"))
        by_role[role] = by_role.get(role, 0) + tokens

    print("Q: LLM calls?")
    print(f"A: {count}")
    print("Q: Estimated total tokens?")
    print(f"A: {total}")
    print("Q: Estimated tokens by role?")
    print("A:")
    for role, tokens in sorted(by_role.items(), key=lambda pair: pair[1], reverse=True):
        print(f"- {role}: {tokens}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
