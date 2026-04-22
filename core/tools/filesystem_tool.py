from __future__ import annotations

from pathlib import Path

from core.tools.tool_boundary import ToolBoundary


class FilesystemTool:
    def __init__(self, root_dir: str | Path = ".", boundary: ToolBoundary | None = None) -> None:
        self.root_dir = Path(root_dir)
        self.boundary = boundary or ToolBoundary(Path("project_state") / "tool_audit.jsonl")

    def _resolve(self, path: str) -> Path:
        target = (self.root_dir / path).resolve()
        root = self.root_dir.resolve()
        if not str(target).startswith(str(root)):
            raise ValueError(f"Path escapes root: {path}")
        return target

    def write_text(self, path: str, content: str, *, allowed_roots: list[str] | None = None) -> Path:
        self.boundary.require_file_write(path=path, allowed_roots=allowed_roots)
        target = self._resolve(path)
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(content, encoding="utf-8")
        return target

    def read_text(self, path: str) -> str:
        return self._resolve(path).read_text(encoding="utf-8")
