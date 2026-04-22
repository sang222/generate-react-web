from __future__ import annotations

import unittest
from pathlib import Path

from agents.base import developer_resources, qa_resources


class V29FESkillPackTests(unittest.TestCase):
    def test_fe_skill_directories_exist(self) -> None:
        for skill in ["fe-design-direction", "fe-ui-implementation", "fe-visual-review"]:
            root = Path("skills") / skill
            self.assertTrue((root / "SKILL.md").exists())
            self.assertTrue((root / "contracts.md").exists())
            self.assertTrue((root / "anti_slop_rules.md").exists())
            self.assertTrue((root / "artifact_contract").exists())

    def test_fe_developer_resources_include_framework_policy(self) -> None:
        story_packet = {"active_lanes": ["frontend"], "execution_mode": "frontend_only", "project_level": 2}
        resources = developer_resources("new_project", "", story_packet, role="fe_developer")
        self.assertIn("CSS / UI Framework Policy", resources)
        self.assertIn("No Fake API Protocol", resources)
        self.assertIn("FE UI Implementation Contract", resources)

    def test_fe_reviewer_resources_include_visual_rubric(self) -> None:
        story_packet = {"active_lanes": ["frontend"], "execution_mode": "frontend_only", "project_level": 2}
        resources = qa_resources(story_packet, "new_project", role="fe_reviewer")
        self.assertIn("FE Visual Review Contract", resources)
        self.assertIn("Visual Review Rubric", resources)

    def test_backend_only_does_not_load_fe_pack_for_backend_developer(self) -> None:
        story_packet = {"active_lanes": ["backend"], "execution_mode": "backend_only", "project_level": 2}
        resources = developer_resources("new_project", "", story_packet, role="be_developer")
        self.assertNotIn("FE UI Implementation Contract", resources)


if __name__ == "__main__":
    unittest.main()
