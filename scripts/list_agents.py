from __future__ import annotations

from pathlib import Path


def main() -> int:
    agents_dir = Path('agents')
    names = sorted(p.stem for p in agents_dir.glob('*.py') if p.stem not in {'__init__', 'base'})
    for name in names:
        print(name)
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
