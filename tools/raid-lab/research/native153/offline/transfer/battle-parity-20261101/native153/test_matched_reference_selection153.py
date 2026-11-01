"""Original input selection controls only; no native player/receipt writes."""
import copy
import importlib.util
from pathlib import Path
import unittest
from unittest.mock import patch

HERE = Path(__file__).resolve().parent
spec = importlib.util.spec_from_file_location("reference_selector_under_test153", HERE / "matched_reference_selection153.py")
selector = importlib.util.module_from_spec(spec)
spec.loader.exec_module(selector)


class SelectionTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.selections = {run: selector.select_reference(run) for run in (1, 2, 3)}

    def data(self, run=1):
        paths, _ = self.selections[run]
        fixture = selector.read(paths["fixtureInput"])
        mode = selector.read(paths["modeInput"])
        expected = selector.read(paths["rngExpectedInput"])
        return [run, fixture, mode, expected, copy.deepcopy(expected["phases"]), selector.sha(paths["fixtureInput"])]

    def test_each_original_run_has_own_exact_paths_seed_raw_hashes_and_full_anchors(self):
        for run, (paths, proof) in self.selections.items():
            with self.subTest(run=run):
                self.assertEqual(proof["referenceRunIndex"], run)
                self.assertEqual(proof["actualCapturedSeed"], selector.SEEDS[run])
                self.assertEqual(paths["fixtureInput"].parent.name, "run" + str(run))
                self.assertEqual(tuple(selector.sha(paths[key]) for key in selector.KEYS), selector.HASHES[run])
                self.assertEqual(proof["fullSharedRngAnchors"]["enter"]["sequence"], {1: 18, 2: 37, 3: 56}[run])
                self.assertEqual(proof["fullSharedRngAnchors"]["leave"]["sequence"], {1: 19, 2: 38, 3: 57}[run])
                self.assertTrue(proof["ownRunRawObscuredPayloadBytesPreserved"])
                self.assertTrue(proof["rngExpectedIsReadbackOnly"])
                self.assertTrue(proof["inputBindingReady"])
                self.assertFalse(proof["nativeFreezeReady"])
                contract = proof["fixtureHashContract"]
                self.assertEqual(contract["artifactSha256"], selector.sha(paths["fixtureInput"]))
                self.assertEqual(contract["modeInputSourceSha256"], contract["artifactSha256"] if run == 1 else contract["originalProducerLfSha256"])
        self.assertEqual(len({proof["files"]["originalInput"]["sha256"] for _, proof in self.selections.values()}), 3)
        self.assertEqual(len({proof["files"]["fixtureInput"]["sha256"] for _, proof in self.selections.values()}), 3)

    def test_invalid_indices_rejected_before_any_source_load(self):
        with patch.object(selector, "load", side_effect=AssertionError("must not load")):
            for run in (0, 4, True, "1", None):
                with self.subTest(run=run), self.assertRaises(ValueError):
                    selector.select_reference(run)

    def test_existing_validator_failure_propagates_for_reference2(self):
        actual_load = selector.load
        def wrapped(path, name):
            module = actual_load(path, name)
            if name == "selected_reference_validator153":
                module.validate = lambda run: (_ for _ in ()).throw(ValueError("existing matched validator rejected"))
            return module
        with patch.object(selector, "load", wrapped), self.assertRaisesRegex(ValueError, "existing matched validator"):
            selector.select_reference(2)

    def test_cross_run_rng_file_rejected(self):
        data = self.data(2)
        data[3] = self.data(3)[3]
        with self.assertRaisesRegex(ValueError, "RNG state/anchors"):
            selector.validate_semantics(*data)

    def test_cross_run_fixture_rejected(self):
        data = self.data(1)
        data[1] = self.data(2)[1]
        with self.assertRaisesRegex(ValueError, "fixture run"):
            selector.validate_semantics(*data)

    def test_one_of_all56_rng_elements_changed_rejected(self):
        for phase, index in (("enter", 0), ("leave", 55)):
            data = self.data(1)
            data[3]["phases"][phase]["state"]["seedArray"][index] += 1
            with self.subTest(phase=phase, index=index), self.assertRaisesRegex(ValueError, "RNG state/anchors"):
                selector.validate_semantics(*data)

    def test_source_row_anchor_changed_rejected(self):
        data = self.data(3)
        data[3]["phases"]["leave"]["source"]["sha256"] = "0" * 64
        with self.assertRaisesRegex(ValueError, "RNG state/anchors"):
            selector.validate_semantics(*data)

    def test_mode_from_different_fixture_hash_rejected(self):
        data = self.data(2)
        data[2]["inputSourceSha256"] = selector.HASHES[1][2]
        with self.assertRaisesRegex(ValueError, "mode/fixture"):
            selector.validate_semantics(*data)

    def test_historical_counter0_and_rng_write_claim_rejected(self):
        for change in ("counter0", "write"):
            data = self.data()
            if change == "counter0":
                data[3]["phases"]["enter"]["state"]["drawCount"] = "0"
            else:
                data[3]["nativeRngStateWritesAllowed"] = True
            with self.subTest(change=change), self.assertRaises(ValueError):
                selector.validate_semantics(*data)

    def test_wrong_seed_boolean_run_and_truncated_array_rejected(self):
        for change in ("seed", "boolean", "array"):
            data = self.data()
            if change == "seed": data[2]["randomSeed"] = selector.SEEDS[2]
            elif change == "boolean": data[1]["runIndex"] = True
            else: data[3]["phases"]["enter"]["state"]["seedArray"].pop()
            with self.subTest(change=change), self.assertRaises(ValueError):
                selector.validate_semantics(*data)


if __name__ == "__main__":
    unittest.main()
