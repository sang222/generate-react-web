from __future__ import annotations

import hashlib
import json
import re
import shutil
import subprocess
from pathlib import Path
from typing import Dict, Iterable, List, Optional, Tuple

OUTPUT_DIR = "output_project"
NPM_INSTALL_TIMEOUT = 240
NPM_BUILD_TIMEOUT = 240
BACKEND_BUILD_TIMEOUT = 300
BUILD_CACHE_DIR = Path(".build_cache")

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
            "Make sure required runtimes are installed and available in PATH."
        )
    except Exception as exc:
        return False, f"Unexpected execution error: {exc}"


def _shorten_error(text: str, max_len: int = 7000) -> str:
    text = (text or "").strip()
    if len(text) <= max_len:
        return text
    return text[:max_len].rstrip() + "\n\n...[truncated]"


def _has_cmd(cmd: str) -> bool:
    return shutil.which(cmd) is not None


def _frontend_root(project_dir: Path, system_target: Dict[str, str]) -> Path:
    if system_target.get("system_type") == "fullstack_website":
        return project_dir / "frontend"
    return project_dir


def _backend_root(project_dir: Path, system_target: Dict[str, str]) -> Path:
    return project_dir / "backend"


def _validate_frontend_files(project_dir: Path, system_target: Dict[str, str]) -> Tuple[bool, str]:
    root = _frontend_root(project_dir, system_target)
    required = [
        root / "package.json",
        root / "index.html",
        root / "src" / "main.jsx",
        root / "src" / "App.jsx",
    ]
    missing = [str(p.relative_to(project_dir)) for p in required if not p.exists()]
    if missing:
        return False, f"Missing required frontend files before execution: {', '.join(missing)}"
    return True, ""


def _detect_backend_build_command(backend_dir: Path, build_tool: str) -> Tuple[Optional[List[str]], Optional[str]]:
    wrapper = backend_dir / "gradlew"
    wrapper_bat = backend_dir / "gradlew.bat"
    if build_tool == "gradle":
        if wrapper.exists():
            return ["bash", "./gradlew", "build", "-x", "test"], None
        if wrapper_bat.exists():
            return ["cmd", "/c", "gradlew.bat", "build", "-x", "test"], None
        if _has_cmd("gradle"):
            return ["gradle", "build", "-x", "test"], None
        return None, "Gradle build requested but neither gradlew nor gradle is available."
    return None, f"Unsupported backend build tool: {build_tool}"


def _discover_spring_boot_application_file(backend_dir: Path) -> Optional[str]:
    java_root = backend_dir / "src" / "main" / "java"
    if not java_root.exists():
        return None
    for path in java_root.rglob("*.java"):
        try:
            txt = path.read_text(encoding="utf-8")
        except Exception:
            continue
        if "@SpringBootApplication" in txt:
            return str(path.relative_to(backend_dir))
    return None


def _validate_backend_files(project_dir: Path, system_target: Dict[str, str]) -> Tuple[bool, str]:
    if system_target.get("backend_language") != "java":
        return True, ""

    backend_dir = _backend_root(project_dir, system_target)
    build_file = backend_dir / ("build.gradle.kts" if (backend_dir / "build.gradle.kts").exists() else "build.gradle")
    resources_dir = backend_dir / "src" / "main" / "resources"
    app_props = resources_dir / "application.properties"
    app_yml = resources_dir / "application.yml"
    main_app = _discover_spring_boot_application_file(backend_dir)

    missing = []
    if not backend_dir.exists():
        missing.append("backend/")
    if not build_file.exists():
        missing.append(f"backend/{build_file.name}")
    if not resources_dir.exists():
        missing.append("backend/src/main/resources")
    if not app_props.exists() and not app_yml.exists():
        missing.append("backend/src/main/resources/application.properties|application.yml")
    if not main_app:
        missing.append("backend/src/main/java/**/@SpringBootApplication entrypoint")
    if missing:
        return False, f"Missing required backend files before execution: {', '.join(missing)}"

    cmd, err = _detect_backend_build_command(backend_dir, system_target.get("backend_build_tool", "gradle"))
    if err:
        return False, err
    return True, ""


def _validate_database_contract(project_dir: Path, system_target: Dict[str, str]) -> Tuple[bool, str]:
    if system_target.get("database_engine") != "postgres":
        return True, ""
    backend_dir = _backend_root(project_dir, system_target)
    resources_dir = backend_dir / "src" / "main" / "resources"
    for path in [resources_dir / "application.properties", resources_dir / "application.yml"]:
        if path.exists():
            try:
                txt = path.read_text(encoding="utf-8").lower()
            except Exception:
                txt = ""
            if "postgres" in txt or "postgresql" in txt:
                return True, ""
    return False, "Database contract check failed: backend config does not appear to reference PostgreSQL."


def _find_local_import_issues(root: Path) -> List[str]:
    issues: List[str] = []
    if not root.exists():
        return issues
    extensions = {".js", ".jsx", ".ts", ".tsx"}
    patterns = [
        re.compile(r"import\s+[^;]*?from\s+['\"](.+?)['\"]"),
        re.compile(r"import\s+['\"](.+?)['\"]"),
    ]
    candidates_ext = ["", ".js", ".jsx", ".ts", ".tsx"]
    for path in root.rglob("*"):
        if path.suffix not in extensions:
            continue
        try:
            text = path.read_text(encoding="utf-8")
        except Exception:
            continue
        for regex in patterns:
            for match in regex.finditer(text):
                ref = match.group(1)
                if not ref.startswith("."):
                    continue
                base = (path.parent / ref).resolve()
                options = []
                if base.is_file():
                    continue
                for ext in candidates_ext:
                    options.append(Path(str(base) + ext))
                for ext in candidates_ext[1:]:
                    options.append(base / f"index{ext}")
                if not any(opt.exists() for opt in options):
                    issues.append(f"Missing local import target from {path.relative_to(root)}: {ref}")
    return issues


def run_preflight_checks(output_dir: str = OUTPUT_DIR, system_target: Optional[Dict[str, str]] = None, active_lanes: Optional[Iterable[str]] = None) -> Tuple[bool, str]:
    project_dir = Path(output_dir).resolve()
    if not project_dir.exists():
        return False, f"Project directory does not exist: {project_dir}"

    base_target = system_target or {
        "system_type": "fullstack_website",
        "frontend_stack": "react-vite",
        "backend_language": "java",
        "backend_framework": "spring_boot",
        "backend_build_tool": "gradle",
        "database_engine": "postgres",
        "database_orm": "jpa",
    }
    target = derive_effective_target(base_target, active_lanes)

    validators = []
    if target.get("effective_mode") != "backend_only":
        validators.append(_validate_frontend_files(project_dir, target))
    if target.get("backend_language") not in {None, "none", ""}:
        validators.append(_validate_backend_files(project_dir, target))
    if target.get("database_engine") not in {None, "none", ""}:
        validators.append(_validate_database_contract(project_dir, target))
    for ok, message in validators:
        if not ok:
            return False, message

    if target.get("effective_mode") != "backend_only":
        frontend_dir = _frontend_root(project_dir, target)
        package_error = validate_package_json_dependencies(frontend_dir)
        if package_error:
            return False, package_error

        issues = _find_local_import_issues(frontend_dir / "src")
        if issues:
            return False, "[preflight import check failed]\n" + "\n".join(issues[:20])
    return True, ""


def _manifest_hash(frontend_dir: Path) -> str:
    h = hashlib.sha256()
    for name in ["package.json", "package-lock.json", "npm-shrinkwrap.json", "yarn.lock", "pnpm-lock.yaml"]:
        path = frontend_dir / name
        if path.exists():
            h.update(name.encode("utf-8"))
            h.update(path.read_bytes())
    return h.hexdigest()


def _restore_cached_node_modules(frontend_dir: Path) -> bool:
    manifest_hash = _manifest_hash(frontend_dir)
    if not manifest_hash:
        return False
    cache_dir = BUILD_CACHE_DIR / "npm" / manifest_hash / "node_modules"
    target = frontend_dir / "node_modules"
    if target.exists():
        return True
    if not cache_dir.exists():
        return False
    target.parent.mkdir(parents=True, exist_ok=True)
    shutil.copytree(cache_dir, target)
    return True


def _store_cached_node_modules(frontend_dir: Path) -> None:
    target = frontend_dir / "node_modules"
    if not target.exists():
        return
    manifest_hash = _manifest_hash(frontend_dir)
    if not manifest_hash:
        return
    cache_dir = BUILD_CACHE_DIR / "npm" / manifest_hash / "node_modules"
    if cache_dir.exists():
        return
    cache_dir.parent.mkdir(parents=True, exist_ok=True)
    shutil.copytree(target, cache_dir)


def _run_frontend_check(project_dir: Path, system_target: Dict[str, str]) -> Tuple[bool, str]:
    frontend_dir = _frontend_root(project_dir, system_target)
    if not _has_cmd("npm"):
        return False, "npm not found in PATH. Please install Node.js/npm first."

    package_error = validate_package_json_dependencies(frontend_dir)
    if package_error:
        return False, package_error

    restored = _restore_cached_node_modules(frontend_dir)
    if not restored:
        install_cmd = ["npm", "ci"] if (frontend_dir / "package-lock.json").exists() else ["npm", "install"]
        install_ok, install_output = _run_command(install_cmd, cwd=frontend_dir, timeout=NPM_INSTALL_TIMEOUT)
        if not install_ok:
            return False, _shorten_error(f"[frontend {' '.join(install_cmd)} failed]\n{install_output}")
        _store_cached_node_modules(frontend_dir)

    build_ok, build_output = _run_command(["npm", "run", "build"], cwd=frontend_dir, timeout=NPM_BUILD_TIMEOUT)
    if not build_ok:
        return False, _shorten_error(f"[frontend npm run build failed]\n{build_output}")
    return True, ""


def _run_backend_check(project_dir: Path, system_target: Dict[str, str]) -> Tuple[bool, str]:
    if system_target.get("backend_language") != "java":
        return True, ""
    backend_dir = _backend_root(project_dir, system_target)
    cmd, err = _detect_backend_build_command(backend_dir, system_target.get("backend_build_tool", "gradle"))
    if err or not cmd:
        return False, err or "No backend build command available."
    ok, output = _run_command(cmd, cwd=backend_dir, timeout=BACKEND_BUILD_TIMEOUT)
    if not ok:
        return False, _shorten_error(f"[backend build failed]\n{output}")
    return True, ""


def run_system_check(output_dir: str = OUTPUT_DIR, system_target: Optional[Dict[str, str]] = None, active_lanes: Optional[Iterable[str]] = None) -> Tuple[bool, str]:
    preflight_ok, preflight_msg = run_preflight_checks(output_dir=output_dir, system_target=system_target, active_lanes=active_lanes)
    if not preflight_ok:
        return False, preflight_msg

    project_dir = Path(output_dir).resolve()
    base_target = system_target or {
        "system_type": "fullstack_website",
        "frontend_stack": "react-vite",
        "backend_language": "java",
        "backend_framework": "spring_boot",
        "backend_build_tool": "gradle",
        "database_engine": "postgres",
        "database_orm": "jpa",
    }
    target = derive_effective_target(base_target, active_lanes)

    if target.get("effective_mode") != "backend_only":
        front_ok, front_msg = _run_frontend_check(project_dir, target)
        if not front_ok:
            return False, front_msg

    if target.get("backend_language") not in {None, "none", ""}:
        back_ok, back_msg = _run_backend_check(project_dir, target)
        if not back_ok:
            return False, back_msg

    return True, ""


def run_react_check(output_dir: str = OUTPUT_DIR) -> Tuple[bool, str]:
    return run_system_check(
        output_dir=output_dir,
        system_target={
            "system_type": "frontend_web_app",
            "frontend_stack": "react-vite",
            "backend_language": "none",
            "backend_framework": "none",
            "backend_build_tool": "none",
            "database_engine": "none",
            "database_orm": "none",
        },
    )
