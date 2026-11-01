"""Synthetic temporary-file contracts for the actual private builtin verifier."""
import hashlib
import importlib.util
from pathlib import Path
import tempfile
import unittest

HERE = Path(__file__).resolve().parent
spec = importlib.util.spec_from_file_location('stage_practice_builtin_test', HERE/'stage_practice153.py')
stage = importlib.util.module_from_spec(spec)
spec.loader.exec_module(stage)


class BuiltinTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix='raidlab-cutscene-test-only-')
        self.root = Path(self.temp.name)
        self.source, self.target = self.root/'installed', self.root/'private'
        self.source.mkdir()
        self.target.mkdir()
        self.data = b'test-only\x00\r\noriginal-builtin'
        (self.source/'sample.bundle').write_bytes(self.data)
        (self.target/'sample.bundle').write_bytes(self.data)
        self.prefab = {'verifiedBundles': {'sample.bundle': {'source': 'installed_builtin',
            'path': str(self.source/'sample.bundle'), 'bytes': len(self.data),
            'sha256': hashlib.sha256(self.data).hexdigest()}}}

    def tearDown(self):
        self.temp.cleanup()

    def test_actual_private_copy_bound(self):
        rows = stage.verify_cutscene_builtin_copies(self.prefab, self.source, self.target)
        self.assertEqual(rows[0]['target'], str((self.target/'sample.bundle').resolve()))
        self.assertEqual(rows[0]['sha256'], hashlib.sha256(self.data).hexdigest())

    def test_tampered_private_copy_rejected(self):
        (self.target/'sample.bundle').write_bytes(b'x'*len(self.data))
        with self.assertRaisesRegex(ValueError, 'bytes differ'):
            stage.verify_cutscene_builtin_copies(self.prefab, self.source, self.target)

    def test_changed_installed_source_rejected(self):
        (self.source/'sample.bundle').write_bytes(b'x'*len(self.data))
        with self.assertRaisesRegex(ValueError, 'bytes differ'):
            stage.verify_cutscene_builtin_copies(self.prefab, self.source, self.target)

    def test_path_escape_rejected(self):
        self.prefab['verifiedBundles']['sample.bundle']['path'] = str(self.root/'outside.bundle')
        with self.assertRaisesRegex(ValueError, 'escaped'):
            stage.verify_cutscene_builtin_copies(self.prefab, self.source, self.target)

    def test_same_install_target_rejected(self):
        with self.assertRaisesRegex(ValueError, 'private clone'):
            stage.verify_cutscene_builtin_copies(self.prefab, self.source, self.source)

    def test_absent_private_copy_rejected(self):
        (self.target/'sample.bundle').unlink()
        with self.assertRaises(FileNotFoundError):
            stage.verify_cutscene_builtin_copies(self.prefab, self.source, self.target)

    def test_empty_builtin_receipt_rejected(self):
        with self.assertRaisesRegex(ValueError, 'must be explicit'):
            stage.verify_cutscene_builtin_copies({'verifiedBundles': {}}, self.source, self.target)


if __name__ == '__main__':
    unittest.main()
