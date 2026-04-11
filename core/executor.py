from __future__ import annotations

import json
import shutil
import subprocess
from pathlib import Path
from typing import Optional, Tuple

OUTPUT_DIR = "output_project"
NPM_INSTALL_TIMEOUT = 180
NPM_BUILD_TIMEOUT = 180


DISALLOWED_PACKAGES = {
    "react-virtualized": "Outdated peer dependency; incompatible with React 18+.",
}


def validate_package_json_dependencies(project_dir: Path) -> Optional[str]:
    package_json_path = project_dir / "package.json"
    if not package_json_path.exists():
        return None

    try:
        data = json.loads(package_json_path.read_text(encoding="utf-8"))
    except Exception as exc:
        return f"[package preflight failed]\nCould not parse package.json: {exc}"

    dependencies = data.get("dependencies", {}) or {}
    dev_dependencies = data.get("devDependencies", {}) or {}
    all_packages = {**dependencies, **dev_dependencies}

    for pkg, reason in DISALLOWED_PACKAGES.items():
        if pkg in all_packages:
            version = all_packages.get(pkg, "")
            return (
                "[package preflight failed]\n"
                f"Disallowed dependency detected: {pkg}@{version}\n"
                f"Reason: {reason}"
            )

    return None


def _run_command(command: list[str], cwd: Path, timeout: int) -> Tuple[bool, str]:
    try:
        result = subprocess.run(
            command,
            cwd=str(cwd),
            capture_output=True,
            text=True,
            timeout=timeout,
            check=False,
        )
        stdout = (result.stdout or "").strip()
        stderr = (result.stderr or "").strip()
        if result.returncode == 0:
            return True, stdout
        parts = []
        if stdout:
            parts.append(f"STDOUT:\n{stdout}")
        if stderr:
            parts.append(f"STDERR:\n{stderr}")
        if not parts:
            parts.append(f"Command failed with exit code {result.returncode}")
        return False, "\n\n".join(parts)
    except subprocess.TimeoutExpired as exc:
        partial_stdout = (exc.stdout or "").strip() if exc.stdout else ""
        partial_stderr = (exc.stderr or "").strip() if exc.stderr else ""
        parts = [f"Command timed out after {timeout}s: {' '.join(command)}"]
        if partial_stdout:
            parts.append(f"STDOUT:\n{partial_stdout}")
        if partial_stderr:
            parts.append(f"STDERR:\n{partial_stderr}")
        return False, "\n\n".join(parts)
    except FileNotFoundError:
        return False, (
            f"Command not found: {command[0]}. "
            "Make sure Node.js and npm are installed and available in PATH."
        )
    except Exception as exc:
        return False, f"Unexpected execution error: {exc}"


def _shorten_error(text: str, max_len: int = 5000) -> str:
    text = (text or "").strip()
    if len(text) <= max_len:
        return text
    return text[:max_len].rstrip() + "\n\n...[truncated]"


def _validate_project_files(project_dir: Path) -> Tuple[bool, str]:
    required_files = [
        project_dir / "package.json",
        project_dir / "index.html",
        project_dir / "src" / "main.jsx",
        project_dir / "src" / "App.jsx",
        ]
    missing = [str(p.relative_to(project_dir)) for p in required_files if not p.exists()]
    if missing:
        return False, f"Missing required files before execution: {', '.join(missing)}"
    return True, ""


def _has_npm() -> bool:
    return shutil.which("npm") is not None


def run_react_check(output_dir: str = OUTPUT_DIR) -> Tuple[bool, str]:
    project_dir = Path(output_dir).resolve()
    if not project_dir.exists():
        return False, f"Project directory does not exist: {project_dir}"
    ok, validation_error = _validate_project_files(project_dir)
    if not ok:
        return False, validation_error
    if not _has_npm():
        return False, "npm not found in PATH. Please install Node.js/npm first."

    package_error = validate_package_json_dependencies(project_dir)
    if package_error:
        return False, package_error

    install_ok, install_output = _run_command(
        ["npm", "install"],
        cwd=project_dir,
        timeout=NPM_INSTALL_TIMEOUT,
    )
    if not install_ok:
        return False, _shorten_error(f"[npm install failed]\n{install_output}")

    build_ok, build_output = _run_command(
        ["npm", "run", "build"],
        cwd=project_dir,
        timeout=NPM_BUILD_TIMEOUT,
    )
    if not build_ok:
        return False, _shorten_error(f"[npm run build failed]\n{build_output}")

    return True, ""
