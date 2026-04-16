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
        self.assertEqual(target["system_type"], "fullstack_website")
        self.assertEqual(target["backend_language"], "none")

    def test_effective_target_backend_only_keeps_backend(self) -> None:
        target = derive_effective_target(BASE_TARGET, ["backend"])
        self.assertEqual(target["effective_mode"], "backend_only")
        self.assertEqual(target["backend_language"], "java")


if __name__ == "__main__":
    unittest.main()



class EffectiveLayoutTests(unittest.TestCase):
    def test_frontend_only_required_files_keep_frontend_subdir_layout(self) -> None:
        from core.orchestrator_helpers.delivery import find_missing_required_files_in_output
        target = derive_effective_target(BASE_TARGET, ["frontend"])
        missing = find_missing_required_files_in_output(target)
        self.assertIn("frontend/package.json", missing)
        self.assertNotIn("package.json", missing)

    def test_backend_only_disables_frontend_preflight_checks(self) -> None:
        target = derive_effective_target(BASE_TARGET, ["backend"])
        self.assertEqual(target["effective_mode"], "backend_only")
        self.assertEqual(target["frontend_stack"], "none")
