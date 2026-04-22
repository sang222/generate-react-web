from __future__ import annotations

from pathlib import Path


class ProjectScanTool:
    def list_files(self, root: str | Path, *, max_files: int = 500) -> list[str]:
        base = Path(root)
        if not base.exists():
            return []
        files: list[str] = []
        for path in base.rglob("*"):
            if path.is_file():
                files.append(str(path.relative_to(base)).replace("\\", "/"))
                if len(files) >= max_files:
                    break
        return files
