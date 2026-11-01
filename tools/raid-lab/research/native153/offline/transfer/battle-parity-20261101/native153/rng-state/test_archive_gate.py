"""Synthetic full-RNG archive acceptance controls; not native evidence."""
import copy
import json
from pathlib import Path
import unittest
from archive_gate import verify


class GateTests(unittest.TestCase):
    def setUp(self):
        self.expected = json.loads((Path(__file__).parent / "expected1/run1-onstart-shared-rng.json").read_text())
        self.sha = "a" * 64
        self.rows = [{"status": "original_practice_full_shared_rng_observed", "boundaryPhase": phase,
            "expectedFileSha256": self.sha, "referenceRunIndex": 1, "source": self.expected["phases"][phase]["source"],
            "actual": copy.deepcopy(self.expected["phases"][phase]["state"]), "passed": True, "mismatchFields": [],
            "mismatchArrayIndices": [], "comparedArrayElements": 56, "rngStateWritten": False,
            "rngMethodsInvoked": False, "sameOriginalOnStartBoundary": True} for phase in ("enter", "leave")]
        self.terminal = {"fullSharedRngState": {"seen": {"enter": True, "leave": True}, "fault": None,
            "observations": copy.deepcopy(self.rows), "expectedFileSha256": self.sha, "referenceRunIndex": 1,
            "comparedArrayElementsPerBoundary": 56, "rngStateWritten": False, "rngMethodsInvoked": False,
            "typedArrayAccessorPrimedOutsideNativeHooks": True, "helperInstallsHooks": False}}

    def result(self):
        return verify(self.rows, self.terminal, self.expected, self.sha)["status"]

    def test_positive_exact56_and_logger_envelope(self):
        self.rows[0].update(time=123, phase="original153_practice_probe", fullAccuracyVerified=False)
        self.assertEqual(self.result(), "passed")

    def test_missing_boundaries_or_snapshot(self):
        self.rows.pop(); self.assertEqual(self.result(), "failed")
        self.rows.clear(); self.terminal.clear(); self.assertEqual(self.result(), "failed")

    def test_reversed_rows_and_reversed_snapshot_rejected(self):
        self.rows.reverse()
        self.terminal["fullSharedRngState"]["observations"].reverse()
        self.assertEqual(self.result(), "failed")

    def test_claimed_pass_cannot_hide_changed_state(self):
        for name, value in (("seed", 1), ("drawCount", "0"), ("inext", 0), ("inextp", 21)):
            old = self.rows[0]["actual"][name]
            self.rows[0]["actual"][name] = value
            self.assertEqual(self.result(), "failed")
            self.rows[0]["actual"][name] = old
        self.rows[0]["actual"]["seedArray"][55] = -1
        self.assertEqual(self.result(), "failed")

    def test_wrong_binding_or_mutation(self):
        self.rows[0]["expectedFileSha256"] = "b" * 64
        self.assertEqual(self.result(), "failed")
        self.rows[0]["expectedFileSha256"] = self.sha
        self.terminal["fullSharedRngState"]["rngStateWritten"] = True
        self.assertEqual(self.result(), "failed")

    def test_omitted_array_value_read_fault_and_latched_fault(self):
        self.rows[0]["actual"]["seedArray"].pop()
        self.assertEqual(self.result(), "failed")
        self.rows.append({"status": "original_practice_full_shared_rng_read_failed", "error": "synthetic"})
        self.terminal["fullSharedRngState"]["fault"] = "synthetic"
        self.assertEqual(self.result(), "failed")


if __name__ == "__main__":
    unittest.main()
