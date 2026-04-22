from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from core.tools.filesystem_tool import FilesystemTool


class ArtifactWriter:
    def __init__(self, fs: FilesystemTool | None = None) -> None:
        self.fs = fs or FilesystemTool()

    def write_json(self, path: str, data: dict[str, Any]) -> Path:
        return self.fs.write_text(path, json.dumps(data, ensure_ascii=False, indent=2), allowed_roots=["project_state", "deliveries", "skill_candidates", "skill_history"])

    def write_markdown(self, path: str, content: str) -> Path:
        return self.fs.write_text(path, content, allowed_roots=["project_state", "deliveries", "docs"])
