from __future__ import annotations

import json
import shutil
import tempfile
import unittest
from pathlib import Path

from core.existing_project import generate_change_impact_report, generate_existing_system_summary, generate_integration_strategy, generate_readiness_report, story_artifact_root
from core.orchestrator_helpers.context import write_run_state


class ExistingProjectStateTests(unittest.TestCase):
    def setUp(self) -> None:
        self.tempdir = Path(tempfile.mkdtemp(prefix="v26_1_test_"))
        self.cwd = Path.cwd()
        import os
        os.chdir(self.tempdir)
        (self.tempdir / "project_state").mkdir(exist_ok=True)

    def tearDown(self) -> None:
        import os
        os.chdir(self.cwd)
        shutil.rmtree(self.tempdir, ignore_errors=True)

    def test_brownfield_artifacts_are_story_scoped(self) -> None:
        baseline = self.tempdir / "baseline"
        (baseline / "frontend" / "src").mkdir(parents=True)
        (baseline / "frontend" / "src" / "main.jsx").write_text("export default 1", encoding="utf-8")
        ownership = {"shared_paths": ["frontend/src"]}
        packet = {"story_id": "S1", "story_name": "Story 1", "system_target": {"system_type": "fullstack_website"}}
        summary = generate_existing_system_summary("proj", "S1", str(baseline), "tree", packet["system_target"], ownership)
        impact = generate_change_impact_report("proj", "S1", packet, ownership)
        strategy = generate_integration_strategy("proj", "S1", packet, "design", json.loads(Path(impact).read_text()))
        readiness = generate_readiness_report("proj", "S1", packet, str(baseline), json.loads(Path(impact).read_text()), Path(strategy).read_text())
        root = story_artifact_root("proj", "S1")
        self.assertTrue(Path(summary).is_relative_to(root))
        self.assertTrue(Path(impact).is_relative_to(root))
        self.assertTrue(Path(strategy).is_relative_to(root))
        self.assertTrue(Path(readiness).is_relative_to(root))

    def test_nonexistent_baseline_fails_readiness(self) -> None:
        packet = {"story_id": "S2"}
        impact_report = {"affected_modules": ["frontend/src"], "protected_modules": ["frontend/src"]}
        readiness = generate_readiness_report("proj", "S2", packet, str(self.tempdir / "missing"), impact_report, "strategy")
        payload = json.loads(Path(readiness).read_text(encoding="utf-8"))
        self.assertFalse(payload["ready"])
        self.assertIn("baseline path does not exist", payload["missing_information"])

    def test_run_state_snapshots_are_story_scoped(self) -> None:
        state_dir = self.tempdir / "state"
        run_state = state_dir / "run_state.json"
        ctx = {"run_id": "r1", "project_id": "proj", "story_id": "S3", "story_name": "Story 3", "history": []}
        path = write_run_state(ctx, state_dir, run_state, "output_project", {"system_type": "fullstack_website"})
        self.assertTrue(Path(path).exists())
        self.assertTrue((self.tempdir / "project_state" / "proj" / "stories" / "S3" / "run_state_current.json").exists())


if __name__ == "__main__":
    unittest.main()
