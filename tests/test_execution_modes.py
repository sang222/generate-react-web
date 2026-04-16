from __future__ import annotations

import unittest

from core.effective_target import derive_effective_target
from core.lane_detection import detect_needed_lanes

BASE_TARGET = {
    "system_type": "fullstack_website",
    "frontend_stack": "react-vite",
    "backend_language": "java",
    "backend_framework": "spring_boot",
    "backend_build_tool": "gradle",
    "database_engine": "postgres",
    "database_orm": "jpa",
}


class ExecutionModeTests(unittest.TestCase):
    def test_detect_needed_lanes_frontend_only(self) -> None:
        packet = {"execution_mode": "frontend_only", "project_level": 2}
        self.assertEqual(detect_needed_lanes(packet, "small UI tweak"), ["frontend"])

    def test_effective_target_frontend_only_disables_backend(self) -> None:
        target = derive_effective_target(BASE_TARGET, ["frontend"])
        self.assertEqual(target["system_type"], "frontend_web_app")
        self.assertEqual(target["backend_language"], "none")

    def test_effective_target_backend_only_keeps_backend(self) -> None:
        target = derive_effective_target(BASE_TARGET, ["backend"])
        self.assertEqual(target["effective_mode"], "backend_only")
        self.assertEqual(target["backend_language"], "java")


if __name__ == "__main__":
    unittest.main()
