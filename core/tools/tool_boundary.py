from __future__ import annotations

import json
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any


class ToolPolicyError(RuntimeError):
    pass


@dataclass(frozen=True)
class ToolDecision:
    status: str
    reason: str = ""
    path: str = ""


class ToolBoundary:
    """Central policy boundary for file/shell tools.

    This starts as an explicit guard/audit layer. As nodes migrate from the legacy
    orchestrator, file writes and shell execution should pass through this class.
    """

    def __init__(self, audit_path: str | Path = "tool_audit.jsonl") -> None:
        self.audit_path = Path(audit_path)

    def audit(self, event: dict[str, Any]) -> None:
        payload = {"timestamp_ms": int(time.time() * 1000), **event}
        self.audit_path.parent.mkdir(parents=True, exist_ok=True)
        with self.audit_path.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(payload, ensure_ascii=False) + "\n")

    def validate_file_write(self, *, path: str, allowed_roots: list[str] | None = None) -> ToolDecision:
        normalized = path.replace("\\", "/").lstrip("/")
        if ".." in Path(normalized).parts:
            return ToolDecision("BLOCK", "PATH_TRAVERSAL", normalized)
        roots = allowed_roots or ["frontend", "backend", "database", "docs", "project_state", "deliveries"]
        if not any(normalized == root or normalized.startswith(root.rstrip("/") + "/") for root in roots):
            return ToolDecision("BLOCK", "PATH_OUTSIDE_ALLOWED_ROOTS", normalized)
        return ToolDecision("ALLOW", "", normalized)

    def require_file_write(self, *, path: str, allowed_roots: list[str] | None = None) -> None:
        decision = self.validate_file_write(path=path, allowed_roots=allowed_roots)
        self.audit({"event": "file_write_policy_check", "path": path, "decision": decision.status, "reason": decision.reason})
        if decision.status != "ALLOW":
            raise ToolPolicyError(decision.reason)

    def validate_shell_command(self, command: str, allowed_commands: list[str]) -> ToolDecision:
        stripped = command.strip()
        destructive_markers = ["rm -rf", "mkfs", ":(){", "shutdown", "reboot", "sudo "]
        if any(marker in stripped for marker in destructive_markers):
            return ToolDecision("BLOCK", "DESTRUCTIVE_COMMAND")
        if not any(stripped == allowed or stripped.startswith(allowed + " ") for allowed in allowed_commands):
            return ToolDecision("BLOCK", "COMMAND_NOT_ALLOWLISTED")
        return ToolDecision("ALLOW")

    def require_shell_command(self, command: str, allowed_commands: list[str]) -> None:
        decision = self.validate_shell_command(command, allowed_commands)
        self.audit({"event": "shell_policy_check", "command": command, "decision": decision.status, "reason": decision.reason})
        if decision.status != "ALLOW":
            raise ToolPolicyError(decision.reason)
