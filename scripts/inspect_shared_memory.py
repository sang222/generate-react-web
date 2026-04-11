from __future__ import annotations

from memory.sanctum import load_shared_memory


def main() -> int:
    shared = load_shared_memory()
    for name, content in (shared.get('documents', {}) or {}).items():
        print(f"===== {name} =====")
        print(content)
        print()
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
