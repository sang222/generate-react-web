import json
import sys

from core.db import get_runs_collection


def main() -> None:
    if len(sys.argv) < 2:
        print("Usage: python scripts/show_run.py <run_id>")
        return

    run_id = sys.argv[1]
    collection = get_runs_collection()
    run = collection.find_one({"run_id": run_id}, {"_id": 0})

    if not run:
        print(f"Run not found: {run_id}")
        return

    print(json.dumps(run, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
