#!/usr/bin/env python3
from pathlib import Path
import sys

ROOT_DIR = Path(__file__).resolve().parents[1]
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from core.model_preflight import run_model_preflight


def main() -> int:
    results = run_model_preflight()

    ok = True
    for result in results:
        status = "PASS" if result.ok else "FAIL"
        print(
            f"[{status}] role={result.role} "
            f"model={result.model} "
            f"duration_ms={result.duration_ms}"
            + (f" error={result.error}" if result.error else "")
        )
        ok = ok and result.ok

    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())