from __future__ import annotations

import argparse
from pathlib import Path


SECTIONS = [
    'SKILL.md',
    'contracts.md',
    'checklist.md',
    'output_artifact.md',
    'when_to_use.md',
    'escalation_rules.md',
    'examples_good_bad.md',
    'known_failures.json',
]


def main() -> int:
    parser = argparse.ArgumentParser(description='Show one skill pack in detail')
    parser.add_argument('--skill', required=True)
    args = parser.parse_args()

    skill_dir = Path('skills') / args.skill
    if not skill_dir.exists() or not skill_dir.is_dir():
        print(f'Skill not found: {skill_dir}')
        return 1

    print(f'Skill: {args.skill}\n')
    for section in SECTIONS:
        path = skill_dir / section
        if not path.exists():
            continue
        print(f'===== {section} =====')
        print(path.read_text(encoding='utf-8').strip())
        print()
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
