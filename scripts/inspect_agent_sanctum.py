from __future__ import annotations

import argparse
import json

from memory.sanctum import ensure_sanctum, load_agent_sanctum
from memory.schemas import AGENT_IDS


def main() -> int:
    parser = argparse.ArgumentParser(description="Inspect BMad sanctum markdown for an agent")
    parser.add_argument("agent_id", choices=AGENT_IDS)
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()

    ensure_sanctum()
    data = load_agent_sanctum(args.agent_id)
    if args.json:
        print(json.dumps(data, ensure_ascii=False, indent=2))
    else:
        print(f"Agent: {args.agent_id}")
        print(f"Sanctum dir: {data.get('sanctum_dir', '')}")
        print("Memory items:")
        for item in data.get("memory_items", []):
            print(f"- {item}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
