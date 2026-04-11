from __future__ import annotations

from core.db import get_runs_collection


def main() -> None:
    result = get_runs_collection().delete_many({})
    print(f"Deleted {result.deleted_count} runs.")


if __name__ == "__main__":
    main()
