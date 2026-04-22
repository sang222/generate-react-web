from __future__ import annotations
import argparse
from core.model_preflight import run_model_preflight
def main() -> int:
    parser = argparse.ArgumentParser(description='Preflight all configured Ollama Cloud role models.')
    parser.add_argument('--role', action='append', help='Role to check. Repeat for multiple roles. Defaults to all roles.')
    args = parser.parse_args()
    failures = 0
    for item in run_model_preflight(args.role):
        status = 'PASS' if item.ok else 'FAIL'
        print(f"[{status}] role={item.role} model={item.model} duration_ms={item.duration_ms}{' error=' + item.error if item.error else ''}")
        failures += 0 if item.ok else 1
    if failures:
        print(f'[FAIL] {failures} model(s) failed. Fix .env model names before running workflow.')
        return 2
    print('[PASS] all configured role models are reachable')
    return 0
if __name__ == '__main__':
    raise SystemExit(main())
