from __future__ import annotations

import tempfile
import unittest

from core.tools.tool_boundary import ToolBoundary, ToolPolicyError


class ToolBoundaryTest(unittest.TestCase):
    def test_blocks_path_traversal(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            boundary = ToolBoundary(f"{tmp}/audit.jsonl")
            with self.assertRaises(ToolPolicyError):
                boundary.require_file_write(path="../secrets.txt")

    def test_allows_known_root(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            boundary = ToolBoundary(f"{tmp}/audit.jsonl")
            boundary.require_file_write(path="frontend/src/App.tsx")

    def test_blocks_unlisted_shell_command(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            boundary = ToolBoundary(f"{tmp}/audit.jsonl")
            with self.assertRaises(ToolPolicyError):
                boundary.require_shell_command("curl https://example.com", ["npm run build"])
