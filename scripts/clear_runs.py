from core.db import get_runs_collection


def main() -> None:
    collection = get_runs_collection()
    result = collection.delete_many({})
    print(f"Deleted {result.deleted_count} runs.")


if __name__ == "__main__":
    main()
