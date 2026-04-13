from __future__ import annotations

from pathlib import Path


def main() -> int:
    skills_dir = Path('skills')
    skills = sorted(p.name for p in skills_dir.iterdir() if p.is_dir())
    for skill in skills:
        print(skill)
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
