"""Consume actual producer receipt paths through the real stager resolver."""
import importlib.util
import json
from pathlib import Path
import unittest

HERE = Path(__file__).resolve().parent
spec = importlib.util.spec_from_file_location('cutscene_path_stage_test', HERE/'stage_practice153.py')
stage = importlib.util.module_from_spec(spec)
spec.loader.exec_module(stage)


class PathTests(unittest.TestCase):
    def test_actual_producer_receipt_all_source_paths(self):
        receipt = json.loads((HERE/'practice-cutscene-control-binding.json').read_text())
        for name, digest in receipt['sourceEvidence'].items():
            with self.subTest(name=name):
                self.assertEqual(stage.sha(stage.cutscene_evidence_path(name)), digest)

    def test_windows_and_forward_metadata_paths_same_exact_file(self):
        expected = (HERE.parent/'metadata/current153-cutscene-control2/mechanics-metadata.json').resolve()
        for name in ['metadata/current153-cutscene-control2/mechanics-metadata.json',
                     'metadata\\current153-cutscene-control2\\mechanics-metadata.json']:
            self.assertEqual(stage.cutscene_evidence_path(name), expected)

    def test_windows_nested_native_proof_path(self):
        self.assertEqual(stage.cutscene_evidence_path('startup-gate-metadata2\\report.json'),
                         (HERE/'startup-gate-metadata2/report.json').resolve())

    def test_absolute_and_traversal_rejected(self):
        for name in ['../outside.json', 'metadata\\..\\outside.json', str(HERE/'absolute.json')]:
            with self.subTest(name=name), self.assertRaises(ValueError):
                stage.cutscene_evidence_path(name)


if __name__ == '__main__':
    unittest.main()
