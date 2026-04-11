from __future__ import annotations

import json
import sys
from pathlib import Path


DISALLOWED_PACKAGES = {
    "react-virtualized": "Outdated peer dependency; incompatible with React 18+."
}


def validate_package_json_in_dir(project_dir: Path) -> list[str]:
    issues: list[str] = []
    package_json_path = project_dir / "package.json"
    if not package_json_path.exists():
        return issues
    try:
        data = json.loads(package_json_path.read_text(encoding="utf-8"))
    except Exception as exc:
        issues.append(f"Could not parse package.json: {exc}")
        return issues
    deps = data.get("dependencies", {}) or {}
    dev_deps = data.get("devDependencies", {}) or {}
    all_packages = {**deps, **dev_deps}
    for pkg, reason in DISALLOWED_PACKAGES.items():
        if pkg in all_packages:
            issues.append(
                f"Disallowed dependency detected in package.json: {pkg}. Reason: {reason}"
            )
    return issues


def main() -> int:
    if len(sys.argv) != 2:
        print('Usage: python validate_changes.py <changes.json>')
        return 2
    path = Path(sys.argv[1])
    if not path.exists():
        print('changes.json not found')
        return 1
    try:
        data = json.loads(path.read_text(encoding='utf-8'))
    except Exception as exc:
        print(f'invalid json: {exc}')
        return 1
    if not isinstance(data, dict):
        print('changes.json must be a JSON object')
        return 1
    required = ['project_mode', 'goal', 'planned_updates']
    missing = [k for k in required if k not in data]
    if missing:
        print('missing keys: ' + ', '.join(missing))
        return 1
    updates = data.get('planned_updates')
    if not isinstance(updates, list):
        print('planned_updates must be a list')
        return 1

    project_dir = path.parent
    issues = validate_package_json_in_dir(project_dir)
    if issues:
        print('validation issues: ' + ' | '.join(issues))
        return 1

    print('changes.json valid')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
