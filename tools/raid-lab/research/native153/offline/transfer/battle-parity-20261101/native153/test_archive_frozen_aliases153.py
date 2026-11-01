"""Frozen source-copy preflight controls; no native/archiver main execution."""
import copy
import importlib.util
import json
from pathlib import Path
import shutil
import tempfile
import unittest

HERE = Path(__file__).resolve().parent
spec = importlib.util.spec_from_file_location("alias_archive_under_test153", HERE / "archive_practice153.py")
archive = importlib.util.module_from_spec(spec); spec.loader.exec_module(archive)


class FrozenAliasTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory(prefix="raidlab-frozen-alias-test-")
        self.root = Path(self.temporary.name).resolve()
        self.output = self.root / "output"; self.output.mkdir()
        self.source = self.root / "source.json"; self.source.write_bytes(b'{"source":"synthetic"}\n')
        self.item = {"path": str(self.source), "sha256": archive.sha(self.source)}

    def tearDown(self):
        root = self.root.resolve()
        assert root.parent == Path(tempfile.gettempdir()).resolve() and root.name.startswith("raidlab-frozen-alias-test-") and not root.is_symlink()
        self.temporary.cleanup()

    def staging(self):
        return {"sources": {"overlayCardSourceProof": copy.deepcopy(self.item)},
                "resourceReceipts": {"overlayCardSourceProof": copy.deepcopy(self.item)}}

    def test_actual16_duplicate_shape_has_one_existing_named_action(self):
        staging16 = json.loads((archive.SANDBOX / "practice-staging16.json").read_text())
        key = "overlayCardSourceProof"
        self.assertEqual(staging16["sources"][key], staging16["resourceReceipts"][key])
        selected = {group: {key: staging16[group][key]} for group in ("sources", "resourceReceipts")}
        actions = archive.frozen_archive_plan(selected, self.output)
        self.assertEqual(len(actions), 1)
        name, source, digest, target = actions[0]
        self.assertEqual((name, target.name), (key, "frozen-overlayCardSourceProof.json"))
        self.assertEqual(source.resolve(), Path(staging16["sources"][key]["path"]).resolve())
        self.assertEqual(digest, staging16["sources"][key]["sha256"])

    def test_same_invocation_copies_exact_alias_once_with_original_bytes(self):
        actions = archive.frozen_archive_plan(self.staging(), self.output)
        self.assertEqual(list(self.output.iterdir()), [])  # Planning is read-only.
        for _, source, expected, target in actions:
            self.assertEqual(archive.sha(source), expected)
            shutil.copyfile(source, target)
            self.assertEqual(source.read_bytes(), target.read_bytes())
        self.assertEqual(len(list(self.output.iterdir())), 1)

    def test_next_invocation_rejects_existing_target_even_if_bytes_match(self):
        actions = archive.frozen_archive_plan(self.staging(), self.output)
        shutil.copyfile(actions[0][1], actions[0][3])
        with self.assertRaises(FileExistsError): archive.frozen_archive_plan(self.staging(), self.output)
        self.assertEqual(actions[0][3].read_bytes(), self.source.read_bytes())

    def test_same_key_different_expected_hash_rejected_before_copy(self):
        staging = self.staging(); staging["resourceReceipts"]["overlayCardSourceProof"]["sha256"] = "0" * 64
        with self.assertRaisesRegex(ValueError, "key/path/hash alias"):
            archive.frozen_archive_plan(staging, self.output)
        self.assertEqual(list(self.output.iterdir()), [])

    def test_same_key_different_path_rejected_even_when_contents_match(self):
        duplicate = self.root / "other.json"; duplicate.write_bytes(self.source.read_bytes())
        staging = self.staging(); staging["resourceReceipts"]["overlayCardSourceProof"]["path"] = str(duplicate)
        with self.assertRaisesRegex(ValueError, "key/path/hash alias"):
            archive.frozen_archive_plan(staging, self.output)

    def test_same_key_different_suffix_rejected_instead_of_overwriting_status(self):
        duplicate = self.root / "other.py"; duplicate.write_bytes(self.source.read_bytes())
        staging = self.staging(); staging["resourceReceipts"]["overlayCardSourceProof"]["path"] = str(duplicate)
        with self.assertRaisesRegex(ValueError, "key/path/hash alias"):
            archive.frozen_archive_plan(staging, self.output)

    def test_case_only_destination_collision_is_not_an_alias(self):
        staging = self.staging(); staging["resourceReceipts"] = {"OverlayCardSourceProof": copy.deepcopy(self.item)}
        with self.assertRaisesRegex(ValueError, "destination collision"):
            archive.frozen_archive_plan(staging, self.output)

    def test_reserved_existing_archive_name_rejected(self):
        source = self.root / "source.py"; source.write_bytes(b"# synthetic\n")
        staging = {"sources": {"stager": {"path": str(source), "sha256": archive.sha(source)}}, "resourceReceipts": {}}
        with self.assertRaisesRegex(ValueError, "destination collision"):
            archive.frozen_archive_plan(staging, self.output, ["frozen-stager.py"])

    def test_preexisting_second_unique_target_rejected_before_any_copy(self):
        staging = self.staging(); staging["sources"]["second"] = copy.deepcopy(self.item)
        target = self.output / "frozen-second.json"; target.write_bytes(b"existing evidence")
        with self.assertRaises(FileExistsError): archive.frozen_archive_plan(staging, self.output)
        self.assertEqual([p.name for p in self.output.iterdir()], [target.name])
        self.assertEqual(target.read_bytes(), b"existing evidence")

    def test_changed_source_remains_a_false_unchanged_gate(self):
        staging = self.staging(); self.source.write_bytes(b"changed after manifest")
        actions = archive.frozen_archive_plan(staging, self.output)
        unchanged = {name: archive.sha(source) == wanted for name, source, wanted, _ in actions}
        self.assertEqual(unchanged, {"overlayCardSourceProof": False})
        self.assertEqual(list(self.output.iterdir()), [])

    def test_path_shaped_keys_rejected(self):
        for key in ("../outside", "x/../config", "x\\child", "name:stream", ""):
            with self.subTest(key=key), self.assertRaises(ValueError):
                archive.frozen_archive_plan({"sources": {key: self.item}, "resourceReceipts": {}}, self.output)


if __name__ == "__main__": unittest.main()
