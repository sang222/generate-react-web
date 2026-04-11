from __future__ import annotations

import shutil
from pathlib import Path
from typing import Iterable

OUTPUT_DIR = Path("output_project")


def reset_output_dir() -> None:
    if OUTPUT_DIR.exists():
        shutil.rmtree(OUTPUT_DIR)
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)


def ensure_output_dir() -> None:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)


def _safe_target_path(relative_path: str) -> Path:
    target = (OUTPUT_DIR / relative_path).resolve()
    output_root = OUTPUT_DIR.resolve()
    if output_root not in target.parents and target != output_root:
        raise ValueError(f"Unsafe path outside output directory: {relative_path}")
    return target


def write_project(files: Iterable[dict]) -> None:
    for item in files:
        path = item["path"]
        content = item["content"]
        target = _safe_target_path(path)
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(content, encoding="utf-8")


def list_project_files() -> list[str]:
    if not OUTPUT_DIR.exists():
        return []
    return sorted(
        str(path.relative_to(OUTPUT_DIR))
        for path in OUTPUT_DIR.rglob("*")
        if path.is_file()
    )


def summarize_project_tree() -> str:
    files = list_project_files()
    if not files:
        return "(empty)"
    return "\n".join(files)


def copy_tree(src: Path, dest: Path) -> None:
    src = src.resolve()
    dest = dest.resolve()
    if not src.exists():
        raise FileNotFoundError(f"Source directory does not exist: {src}")
    if dest.exists():
        shutil.rmtree(dest)
    shutil.copytree(src, dest)


def load_baseline_project(src: str | Path) -> None:
    source = Path(src)
    if not source.exists():
        raise FileNotFoundError(f"Baseline directory does not exist: {source}")
    if OUTPUT_DIR.exists():
        shutil.rmtree(OUTPUT_DIR)
    shutil.copytree(source, OUTPUT_DIR)


def summarize_project_tree_for(root: str | Path) -> str:
    base = Path(root)
    if not base.exists():
        return "(missing)"
    files = sorted(str(path.relative_to(base)) for path in base.rglob('*') if path.is_file())
    if not files:
        return "(empty)"
    return "\n".join(files)
