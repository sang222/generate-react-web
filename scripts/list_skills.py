from __future__ import annotations

from pathlib import Path


def _read(path: Path) -> str:
    return path.read_text(encoding='utf-8').strip() if path.exists() else ''


def _purpose(skill_dir: Path) -> str:
    text = _read(skill_dir / 'SKILL.md')
    for line in text.splitlines():
        if line.strip().lower().startswith('## purpose'):
            continue
    lines = [line.strip() for line in text.splitlines() if line.strip()]
    if len(lines) >= 3:
        return lines[2] if not lines[2].startswith('##') else lines[1]
    return lines[0] if lines else ''


def _first_bullet(path: Path) -> str:
    text = _read(path)
    for line in text.splitlines():
        stripped = line.strip()
        if stripped.startswith('- '):
            return stripped[2:]
    return ''


def main() -> int:
    skills_dir = Path('skills')
    if not skills_dir.exists():
        print('skills directory not found')
        return 1

    skill_dirs = sorted(p for p in skills_dir.iterdir() if p.is_dir())
    for skill_dir in skill_dirs:
        purpose = _purpose(skill_dir)
        output_hint = _first_bullet(skill_dir / 'output_artifact.md')
        when_hint = _first_bullet(skill_dir / 'when_to_use.md')
        print(f"{skill_dir.name}")
        if purpose:
            print(f"  purpose: {purpose}")
        if output_hint:
            print(f"  output: {output_hint}")
        if when_hint:
            print(f"  use-when: {when_hint}")
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
