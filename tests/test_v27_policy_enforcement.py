import json
import shutil
import tempfile
import unittest
from pathlib import Path

from core.integration_service import _load_locked_artifacts
from core.runtime_override_manager import resolve_final_apply_scope


class TestV27Policy(unittest.TestCase):
    def test_scope_cap_prefers_stricter(self):
        self.assertEqual(resolve_final_apply_scope('core_candidate_only', 'runtime_override'), 'core_candidate_only')
        self.assertEqual(resolve_final_apply_scope('project_only', 'runtime_override'), 'project_only')

    def test_locked_artifact_source_namespace_maps_relative_files(self):
        tmp = Path(tempfile.mkdtemp())
        try:
            src = tmp / 'deliveries' / 'p' / 's' / 'source'
            (src / 'frontend' / 'src').mkdir(parents=True)
            (src / 'frontend' / 'src' / 'App.jsx').write_text('x', encoding='utf-8')
            lock_file = tmp / 'artifact_locks.json'
            lock_file.write_text(json.dumps({'locked_artifacts':[{'path': str(src)}]}), encoding='utf-8')
            locks = _load_locked_artifacts(str(lock_file))
            self.assertIn('frontend/src/App.jsx', locks)
        finally:
            shutil.rmtree(tmp)

if __name__ == '__main__':
    unittest.main()
