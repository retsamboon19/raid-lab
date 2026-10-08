"""Source-bound current Intercept encounter registry checks (no native run)."""

import importlib.util
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch


MODULE_PATH = Path(__file__).with_name("mechanics_encounters.py")
SPEC = importlib.util.spec_from_file_location("mechanics_encounters", MODULE_PATH)
encounters = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(encounters)


class EncounterRegistryTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.registry = encounters.load_registry()

    def test_only_current_intercept_group_one(self):
        profiles = self.registry["profiles"]
        self.assertEqual([p["productId"] for p in profiles],
                         [x[0] for x in encounters.SELECTOR])
        self.assertEqual([p["wave"]["stageId"] for p in profiles],
                         list(range(6302001, 6302011)))
        self.assertTrue(all(p["tableKey"]["Group"] == 1 and
                            p["wave"]["groupId"] == "wave_Intercept_001" and
                            p["targets"] for p in profiles))

    def test_kraken_exact_match_with_seed(self):
        profile = next(p for p in self.registry["profiles"]
                       if p["productId"] == "anomaly-kraken")
        request = dict(profile["encounter"], randomSeed=1)
        self.assertIs(encounters.match_profile(self.registry, "anomaly-kraken", request), profile)
        self.assertEqual((request["waveId"], request["monsterStageLv"],
                          request["raidLvChangeGroup"]), (6302009, 250, 209))

    def test_reject_unknown_profile_and_altered_transport(self):
        profile = self.registry["profiles"][0]
        request = dict(profile["encounter"], randomSeed=23)
        with self.assertRaisesRegex(ValueError, "Unsupported"):
            encounters.match_profile(self.registry, "solo-sr40", request)
        for changed in ({"waveId": 6302009}, {"monsterStageLv": 1},
                        {"isAuto": False}, {"extra": 0}):
            with self.subTest(changed=changed), self.assertRaises(ValueError):
                encounters.match_profile(self.registry, profile["productId"],
                                         dict(request, **changed))

    def test_reject_bad_seed_type_or_range(self):
        profile = self.registry["profiles"][0]
        for seed in (True, 0, -1, 2**31, 1.0):
            with self.subTest(seed=seed), self.assertRaisesRegex(ValueError, "randomSeed"):
                encounters.match_profile(self.registry, profile["productId"],
                                         dict(profile["encounter"], randomSeed=seed))

    def test_registry_tamper_fails_source_reconstruction(self):
        changed = json.loads(json.dumps(self.registry))
        changed["profiles"][0]["targets"][0]["monsterPrefab"] = "made_up"
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "registry.json"
            path.write_text(json.dumps(changed), encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "schema/content"):
                encounters.load_registry(path)

    def test_client_or_archive_mismatch_fails_closed(self):
        original = encounters._file_sha

        def changed_client(path):
            return "0" * 64 if path == encounters.CLIENT else original(path)

        with patch.object(encounters, "_file_sha", side_effect=changed_client):
            with self.assertRaisesRegex(ValueError, "bytes changed"):
                encounters.load_registry()


if __name__ == "__main__":
    unittest.main()
