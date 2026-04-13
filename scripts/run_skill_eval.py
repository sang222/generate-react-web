from __future__ import annotations

import argparse
import json
from pathlib import Path


def list_cases(suite_root: Path) -> int:
    cases = sorted((suite_root / 'cases').glob('*.json'))
    if not cases:
        print('No eval cases found.')
        return 1
    for case in cases:
        data = json.loads(case.read_text(encoding='utf-8'))
        print(f"{data.get('case_id','')} | role={data.get('role','')} | file={case}")
    return 0


def show_case(suite_root: Path, case_id: str) -> int:
    for case in (suite_root / 'cases').glob('*.json'):
        data = json.loads(case.read_text(encoding='utf-8'))
        if data.get('case_id') == case_id:
            print(json.dumps(data, ensure_ascii=False, indent=2))
            return 0
    print(f'Case not found: {case_id}')
    return 1


def main() -> int:
    parser = argparse.ArgumentParser(description='Inspect skill eval corpus')
    parser.add_argument('--suite', default='brownfield')
    parser.add_argument('--show-case')
    args = parser.parse_args()

    suite_root = Path('evals') / args.suite
    if not suite_root.exists():
        print(f'Suite not found: {suite_root}')
        return 1

    if args.show_case:
        return show_case(suite_root, args.show_case)
    return list_cases(suite_root)


if __name__ == '__main__':
    raise SystemExit(main())
