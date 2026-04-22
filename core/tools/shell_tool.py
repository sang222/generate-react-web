from __future__ import annotations

import os
import subprocess
from pathlib import Path

from core.tools.tool_boundary import ToolBoundary


class ShellTool:
    DEFAULT_ALLOWED = [
        "npm install",
        "npm ci",
        "npm run build",
        "./gradlew build -x test",
        "python3 -m unittest",
        "python3 -m compileall",
    ]

    def __init__(self, boundary: ToolBoundary | None = None, allowed_commands: list[str] | None = None) -> None:
        self.boundary = boundary or ToolBoundary(Path("project_state") / "tool_audit.jsonl")
        self.allowed_commands = allowed_commands or list(self.DEFAULT_ALLOWED)

    def execute(self, command: str, *, cwd: str | Path = ".", timeout: int = 120) -> subprocess.CompletedProcess[str]:
        self.boundary.require_shell_command(command, self.allowed_commands)
        return subprocess.run(
            command,
            cwd=str(cwd),
            shell=True,
            text=True,
            capture_output=True,
            timeout=timeout,
            env={k: v for k, v in os.environ.items() if k not in {"OLLAMA_API_KEY"}},
        )
