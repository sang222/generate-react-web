from __future__ import annotations

import shutil
from pathlib import Path
from typing import Dict, List

OUTPUT_DIR = Path("output_project")


def reset_output_dir(output_dir: Path = OUTPUT_DIR) -> None:
    if output_dir.exists():
        shutil.rmtree(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)


def _safe_target_path(path: str, output_dir: Path = OUTPUT_DIR) -> Path:
    target = (output_dir / path).resolve()
    base = output_dir.resolve()
    if not str(target).startswith(str(base)):
        raise ValueError(f"Unsafe path detected: {path}")
    return target


def write_project(files: List[Dict[str, str]], output_dir: Path = OUTPUT_DIR) -> None:
    for file in files:
        target = _safe_target_path(file["path"], output_dir=output_dir)
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(file["content"], encoding="utf-8")


def list_project_files(output_dir: Path = OUTPUT_DIR) -> List[str]:
    if not output_dir.exists():
        return []
    return sorted(
        str(path.relative_to(output_dir))
        for path in output_dir.rglob("*")
        if path.is_file()
    )


def summarize_project_tree(output_dir: Path = OUTPUT_DIR) -> str:
    files = list_project_files(output_dir=output_dir)
    if not files:
        return ""
    return "\n".join(files)
