from __future__ import annotations

import argparse
import json

from core.db import get_agent_memories_collection, get_agent_profiles_collection


def main() -> int:
    parser = argparse.ArgumentParser(description="Inspect agent profile and memories")
    parser.add_argument("agent_id", help="Agent ID, e.g. developer")
    parser.add_argument("--project-mode", default="new_project", choices=["new_project", "existing_project"])
    parser.add_argument("--limit", type=int, default=10)
    args = parser.parse_args()

    profile = get_agent_profiles_collection().find_one({"agent_id": args.agent_id}, {"_id": 0}) or {}
    memories = list(
        get_agent_memories_collection()
        .find({"agent_id": args.agent_id, "project_mode": args.project_mode}, {"_id": 0})
        .sort([("importance", -1), ("updated_at", -1)])
        .limit(args.limit)
    )

    print(json.dumps({"profile": profile, "memories": memories}, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
