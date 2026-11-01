"""Matched-input admission controls only; never calls the mutating stager."""
import copy
import importlib.util
import inspect
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

HERE = Path(__file__).resolve().parent
spec = importlib.util.spec_from_file_location("matched_reference_stager_under_test", HERE / "stage_practice153.py")
stage = importlib.util.module_from_spec(spec); spec.loader.exec_module(stage)
spec2 = importlib.util.spec_from_file_location("extended_continuity_under_test", HERE / "check_auto_preferences_continuity153.py")
continuity = importlib.util.module_from_spec(spec2); spec2.loader.exec_module(continuity)


class MatchedStageTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.selections = {run: stage.prepare_reference_selection(17, run) for run in (1, 2, 3)}

    def prior(self, run):
        return {"sources": {key: copy.deepcopy(self.selections[run]["proof"]["files"][key]) for key in stage.REFERENCE_INPUT_KEYS}}

    def test_default1_historical_paths_and_new_reference_bounds(self):
        self.assertEqual(inspect.signature(stage.main).parameters["reference_run"].default, 1)
        with patch.object(stage, "sha", side_effect=AssertionError("no historical selector load")):
            for index in (1, 15, 16): self.assertIsNone(stage.prepare_reference_selection(index, 1))
            for index, run in ((16, 2), (15, 3), (23, 1), (17, True)):
                with self.subTest(index=index, run=run), self.assertRaises(ValueError):
                    stage.prepare_reference_selection(index, run)
        self.assertEqual(stage.prepare_reference_selection(22, 3)["referenceRunIndex"], 3)

    def test_exact_selector_inputs_and_both_hash_conventions(self):
        for run, selected in self.selections.items():
            stage.verify_selected_reference_paths(selected["paths"], selected["proof"], run)
            self.assertEqual(selected["sha256"], stage.hashlib.sha256(selected["bytes"]).hexdigest())
            self.assertEqual(json.loads(selected["bytes"]), selected["proof"])
            self.assertNotIn(b"\r\n", selected["bytes"])
        c1 = self.selections[1]["proof"]["fixtureHashContract"]
        c2 = self.selections[2]["proof"]["fixtureHashContract"]
        self.assertEqual(c1["modeInputSourceSha256"], c1["artifactSha256"])
        self.assertEqual(c2["modeInputSourceSha256"], c2["originalProducerLfSha256"])
        self.assertNotEqual(c2["modeInputSourceSha256"], c2["artifactSha256"])

    def test_cross_run_mode_path_is_not_admitted(self):
        selected = self.selections[2]; paths = dict(selected["paths"])
        paths["modeInput"] = self.selections[3]["paths"]["modeInput"]
        with self.assertRaisesRegex(ValueError, "path/artifact"):
            stage.verify_selected_reference_paths(paths, selected["proof"], 2)

    def test_bad_producer_hash_and_wrong_artifact_hash_are_not_admitted(self):
        for field in ("originalProducerLfSha256", "artifactSha256", "modeInputSourceSha256"):
            selected = self.selections[2]; proof = copy.deepcopy(selected["proof"])
            proof["fixtureHashContract"][field] = "0" * 64
            with self.subTest(field=field), self.assertRaisesRegex(ValueError, "hash contract"):
                stage.verify_selected_reference_paths(selected["paths"], proof, 2)

    def test_historical1_to2_switch_has_only_exact_input_key_exceptions(self):
        selected = self.selections[2]
        allowed, proof = stage.admit_reference_input_changes(self.prior(1), selected["paths"], selected)
        self.assertEqual(allowed, set(stage.REFERENCE_INPUT_KEYS) | {"referenceSelectionProof"})
        self.assertNotIn("geometryInput", allowed)
        self.assertNotIn("settingsInput", allowed)
        self.assertEqual((proof["fromReferenceRun"], proof["toReferenceRun"]), (1, 2))

    def test_same_reference_provides_no_change_bypass(self):
        selected = self.selections[1]
        allowed, _ = stage.admit_reference_input_changes(self.prior(1), selected["paths"], selected)
        self.assertEqual(allowed, set())

    def test_one_crosswired_historical_key_rejects_whole_switch(self):
        prior = self.prior(1)
        prior["sources"]["expectedReadbacks"] = self.prior(3)["sources"]["expectedReadbacks"]
        selected = self.selections[2]
        with self.assertRaisesRegex(ValueError, "Historical reference input key"):
            stage.admit_reference_input_changes(prior, selected["paths"], selected)

    def test_unknown_historical_fixture_and_missing_rng_rejected(self):
        selected = self.selections[2]
        for change in ("unknown", "missing"):
            prior = self.prior(1)
            if change == "unknown": prior["sources"]["fixtureInput"]["sha256"] = "0" * 64
            else: del prior["sources"]["rngExpectedInput"]
            with self.subTest(change=change), self.assertRaises(ValueError):
                stage.admit_reference_input_changes(prior, selected["paths"], selected)

    def test_recorded_selection_without_bound_proof_file_is_rejected(self):
        prior = self.prior(2)
        prior["matchedReferenceSelection"] = {"referenceRunIndex": 2, "proof": self.selections[2]["proof"]}
        selected = self.selections[3]
        with self.assertRaises(ValueError):
            stage.admit_reference_input_changes(prior, selected["paths"], selected)

    def test_saved2_proof_allows3_or1_but_rejects_a_changed_record(self):
        temporary = tempfile.TemporaryDirectory(prefix="raidlab-reference-proof-test-")
        root = Path(temporary.name).resolve()
        try:
            path = root / "previous-selection.json"
            path.write_bytes(self.selections[2]["bytes"])
            prior = self.prior(2)
            prior["sources"]["referenceSelectionProof"] = {"path": str(path), "sha256": stage.sha(path)}
            prior["matchedReferenceSelection"] = {"referenceRunIndex": 2, "proofPath": str(path),
                "proofSha256": stage.sha(path), "proof": self.selections[2]["proof"]}
            for run in (3, 1):
                selected = self.selections[run]
                allowed, proof = stage.admit_reference_input_changes(prior, selected["paths"], selected)
                self.assertIn("modeInput", allowed)
                self.assertEqual((proof["fromReferenceRun"], proof["toReferenceRun"]), (2, run))
            prior["matchedReferenceSelection"]["proof"] = copy.deepcopy(prior["matchedReferenceSelection"]["proof"])
            prior["matchedReferenceSelection"]["proof"]["actualCapturedSeed"] = 0
            with self.assertRaisesRegex(ValueError, "Previous selected reference proof"):
                stage.admit_reference_input_changes(prior, selected["paths"], selected)
        finally:
            assert root.parent == Path(tempfile.gettempdir()).resolve() and root.name.startswith("raidlab-reference-proof-test-") and not root.is_symlink()
            temporary.cleanup()

    def test_json_and_unknown_python_review_bypass_rejected(self):
        for name in ("modeInput", "geometryInput", "expectedReadbacks"):
            self.assertFalse(stage.source_review_allowed(name, Path("input.json"), 17))
        self.assertFalse(stage.source_review_allowed("unknownPython", Path("helper.py"), 20))
        self.assertFalse(stage.source_review_allowed("autoPreferencesContinuityWitnessSource", Path("helper.py"), 15))
        self.assertTrue(stage.source_review_allowed("autoPreferencesContinuityWitnessSource", Path("helper.py"), 16))

    def test_continuity_bounds_accept22_before_any_registry_or_plan_access(self):
        with patch.object(Path, "read_text", side_effect=RuntimeError("stopped before file/registry read")):
            for index in (16, 17, 20, 21, 22):
                with self.subTest(index=index), self.assertRaisesRegex(RuntimeError, "stopped before"):
                    continuity.main(index, "pre", "a" * 64)
            for index in (11, 23):
                with self.subTest(index=index), self.assertRaises(ValueError):
                    continuity.main(index, "pre", "a" * 64)


if __name__ == "__main__": unittest.main()
