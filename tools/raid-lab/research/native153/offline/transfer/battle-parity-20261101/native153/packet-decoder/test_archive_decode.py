"""Synthetic native-evidence contract controls; no native/combat execution."""
import copy
import unittest
from archive_decode import validate_native_contract


class NativeWireContract(unittest.TestCase):
    def setUp(self):
        self.mode = {"waveId": 6801001, "timeLimit": 90, "characters": [{"tableId": i} for i in range(1, 6)]}
        self.terminal = {"completeBattle": True, "originalPacketExported": True,
                         "statisticsAndPacketCapturedBeforeCleanup": True,
                         "originalPacketSource": {"format": "protobuf_wire", "byteLength": 17, "sha256": "a" * 64},
                         "originalAntiCheat": {"source": "original_BattleResult_AntiCheatBattleDataInit", "waveId": 6801001,
                                               "battleDuration": 90000, "characterCount": 5, "monsterCount": 36}}

    def check(self, terminal=None):
        return validate_native_contract(terminal or self.terminal, self.mode, 17, "a" * 64)

    def test_positive_monster_count_is_native_not_hardcoded_35(self):
        self.assertEqual(self.check()[0]["monsterCount"], 36)

    def test_optional_native_digest(self):
        self.terminal["originalPacketSource"]["sha256"] = None
        self.assertEqual(self.check()[2], [1, 2, 3, 4, 5])

    def test_bad_export_fields_rejected(self):
        for field, bad in (("format", "native_json"), ("byteLength", 18), ("byteLength", True), ("sha256", "b" * 64)):
            with self.subTest(field=field, bad=bad):
                terminal = copy.deepcopy(self.terminal)
                terminal["originalPacketSource"][field] = bad
                with self.assertRaises(ValueError): self.check(terminal)

    def test_bad_native_typed_fields_rejected(self):
        for field, bad in (("source", "synthetic"), ("waveId", 1), ("battleDuration", 1), ("characterCount", 4),
                           ("monsterCount", 0), ("monsterCount", True), ("monsterCount", 100001)):
            with self.subTest(field=field, bad=bad):
                terminal = copy.deepcopy(self.terminal)
                terminal["originalAntiCheat"][field] = bad
                with self.assertRaises(ValueError): self.check(terminal)

    def test_callback_lifetime_and_completed_export_required(self):
        for field in ("completeBattle", "originalPacketExported", "statisticsAndPacketCapturedBeforeCleanup"):
            terminal = copy.deepcopy(self.terminal); terminal[field] = False
            with self.subTest(field=field), self.assertRaises(ValueError): self.check(terminal)

    def test_duplicate_captured_identity_rejected(self):
        self.mode["characters"][1]["tableId"] = 1
        with self.assertRaises(ValueError): self.check()


if __name__ == "__main__":
    unittest.main()
