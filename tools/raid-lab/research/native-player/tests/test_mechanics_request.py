"""Safety boundaries for the diagnostic native input handoff."""

import copy
import json
import unittest
from pathlib import Path

from mechanics_request import (load_request, request_sha256, validate_request,
                               verify_request_events)


FIXTURE = Path(__file__).with_name("mechanics_request_fixture.json")
BARE_FIXTURE = Path(__file__).with_name("mechanics_request_bare.json")
SNAPSHOT_FIXTURE = Path(__file__).with_name("mechanics_request_snapshot.json")


class MechanicsRequestTests(unittest.TestCase):
    def setUp(self):
        self.request = json.loads(FIXTURE.read_text(encoding="utf-8"))
        self.bare_request = json.loads(BARE_FIXTURE.read_text(encoding="utf-8"))
        self.snapshot_request = json.loads(SNAPSHOT_FIXTURE.read_text(encoding="utf-8"))

    def test_fixture_is_hash_bound_and_ordered(self):
        request, digest = load_request(FIXTURE)
        self.assertEqual([c["nameCode"] for c in request["characters"]],
                         [5065, 5011, 5105, 5004, 5099])
        self.assertEqual(digest, request_sha256(json.loads(json.dumps(request, sort_keys=True))))
        altered = copy.deepcopy(request)
        altered["characters"][4]["stats"]["Attack"] += 1
        self.assertNotEqual(digest, request_sha256(altered))

    def test_missing_or_lossy_build_information_cannot_be_silently_filled(self):
        for edit in (
            lambda r: r["characters"][0]["stats"].pop("Attack"),
            lambda r: r["characters"][0].update(equipment={"head": "T9"}),
            lambda r: r["characters"][0]["stats"].update(CriticalRatio={"source": "calculator"}),
            lambda r: r["characters"][0]["skillLevels"].pop("2"),
        ):
            with self.subTest(edit=edit.__code__.co_consts):
                value = copy.deepcopy(self.request)
                edit(value)
                with self.assertRaises(ValueError):
                    validate_request(value)

    def test_unsupported_character_encounter_or_provenance_is_rejected(self):
        for edit in (
            lambda r: r["characters"][1].update(nameCode=5065),
            lambda r: r["encounter"].update(waveId=6302010),
            lambda r: r["encounter"].update(isAuto=False),
            lambda r: r.update(installedClientSha256="0" * 64),
            lambda r: r["encounter"].pop("randomSeed"),
        ):
            with self.subTest(edit=edit.__code__.co_consts):
                value = copy.deepcopy(self.request)
                edit(value)
                with self.assertRaises(ValueError):
                    validate_request(value)

    def test_supported_diagnostic_variation_preserves_requested_slot_and_seed(self):
        value = copy.deepcopy(self.request)
        value["characters"] = value["characters"][::-1]
        value["characters"][0]["skillLevels"]["3"] = 7
        value["encounter"]["randomSeed"] = 27
        self.assertIs(validate_request(value), value)
        self.assertNotEqual(request_sha256(value), request_sha256(self.request))

    def _native_events(self):
        digest = request_sha256(self.request)
        prepared = []
        results = []
        for slot, character in enumerate(self.request["characters"], 1):
            stats = {key: (1500 if key == "CriticalRatio" else 15000)
                     if isinstance(value, dict) else value
                     for key, value in character["stats"].items()}
            prepared.append({"status": "original_character_data_prepared",
                "slot": slot, "nameCode": character["nameCode"],
                "level": character["level"], "grade": character["grade"],
                "core": character["core"], "tableId": 100000 + slot,
                "resourceId": 200 + slot, "stats": stats,
                "skillSources": [
                    {"field": field, "group": 300 + slot, "tableType": 1,
                     "level": character["skillLevels"][key]}
                    for key, field in (("1", "Skill1Data"),
                                       ("2", "Skill2Data"),
                                       ("3", "SkillBurstData"))],
                "requestSha256": digest})
            results.append({"entityId": 4095 + slot, "nameCode": character["nameCode"],
                            "tableId": 100000 + slot})
        return prepared + [
            {"status": "synthetic_kraken_transporter_prepared",
             "roster": [c["nameCode"] for c in self.request["characters"]],
             **self.request["encounter"], "requestSha256": digest,
             "transporterValueTypeSize": 360},
            {"status": "original_rng_initialized", "managerSeed": 1,
             "sharedSeed": 1},
            {"status": "original_terminal_result", "completeBattle": True,
             "resultCaptured": True, "originalResult": True,
             "resultType": "NK.BattleResult",
             "rounds": [{"characters": results}]},
        ]

    def test_native_handoff_accepts_original_readbacks_without_claiming_table_crit_value(self):
        receipt = verify_request_events(self.request, self._native_events())
        self.assertTrue(receipt["passed"], receipt["errors"])
        self.assertEqual(receipt["resolvedTableCriticalStats"]["1"],
                         {"CriticalRatio": 1500, "CriticalDamage": 15000})

    def test_native_handoff_rejects_stale_hash_and_wrong_slot_or_value(self):
        for edit, expected_error in (
            (lambda rows: rows[0].update(requestSha256="0" * 64), "requestSha256"),
            (lambda rows: rows[-1]["rounds"][0]["characters"][0].update(nameCode=5011),
             "terminal slot 1.nameCode"),
            (lambda rows: rows[2]["stats"].update(Attack=0), "prepared slot 3.stats.Attack"),
        ):
            with self.subTest(error=expected_error):
                rows = self._native_events()
                edit(rows)
                receipt = verify_request_events(self.request, rows)
                self.assertFalse(receipt["passed"])
                self.assertTrue(any(expected_error in error for error in receipt["errors"]),
                                receipt["errors"])

    def _bare_events(self):
        rows = self._native_events()
        digest = request_sha256(self.bare_request)
        calculated, applied = [], []
        for row in rows:
            if "requestSha256" in row:
                row["requestSha256"] = digest
            if row["status"] != "original_character_data_prepared":
                continue
            slot = row["slot"]
            request_character = self.bare_request["characters"][slot - 1]
            row["stats"] = {key: str(value) if key not in
                ("CriticalRatio", "CriticalDamage", "HPRatio") else value
                for key, value in row["stats"].items()}
            row["barePolicy"] = copy.deepcopy(request_character["barePolicy"])
            row["statSource"] = "installed_original_bare_builder"
            provenance = {"sixCalculated": "CharacterStatHelper.Calc original int64 getters",
                "critical": "selected CharacterStaticInfo original getters",
                "HPRatio": "source constant in CreateSpotSpotCharacterData_Status; not invoked"}
            helper = {"providerCount": 7, "calcFlags": 0x86,
                      "constructorFlags": 0x1886}
            calculated.append({"status": "original_bare_character_stats_calculated",
                "slot": slot, "nameCode": row["nameCode"], "requestSha256": digest,
                "source": "installed_original_stat_builder",
                "selectedTableId": row["tableId"], "stats": copy.deepcopy(row["stats"]),
                "barePolicy": copy.deepcopy(row["barePolicy"]),
                "statProvenance": provenance, "originalHelper": helper,
                "readback": {"tableId": row["tableId"], "nameCode": row["nameCode"],
                             "grade": row["grade"], "core": row["core"],
                             "level": row["level"], "attractiveLevel": 0}})
            applied.append({"status": "original_bare_stats_applied", "slot": slot,
                "nameCode": row["nameCode"], "tableId": row["tableId"],
                "level": row["level"], "grade": row["grade"], "core": row["core"],
                "requestSha256": digest, "source": "installed_original_stat_builder",
                "barePolicy": copy.deepcopy(row["barePolicy"]),
                "statProvenance": provenance, "originalHelper": helper,
                "stats": copy.deepcopy(row["stats"])})
        return rows + calculated + applied

    def test_bare_mode_requires_explicit_empty_investments_and_no_supplied_stats(self):
        self.assertIs(validate_request(self.bare_request), self.bare_request)
        for edit in (
            lambda r: r["characters"][0].update(stats={"Attack": 999}),
            lambda r: r["characters"][0]["barePolicy"].update(equipment=[123]),
            lambda r: r["characters"][0]["barePolicy"].update(attractiveLevel=1),
            lambda r: r["characters"][0].update(core=1),
        ):
            with self.subTest(edit=edit.__code__.co_consts):
                request = copy.deepcopy(self.bare_request)
                edit(request)
                with self.assertRaises(ValueError):
                    validate_request(request)

    def test_bare_receipt_requires_all_five_calculated_and_applied_statuses(self):
        receipt = verify_request_events(self.bare_request, self._bare_events())
        self.assertTrue(receipt["passed"], receipt["errors"])
        self.assertEqual((receipt["bareCalculatedRows"], receipt["bareAppliedRows"]), (5, 5))
        for edit, expected_error in (
            (lambda rows: rows[-1]["stats"].update(Attack="999"),
             "calculated/applied/prepared stats differ"),
            (lambda rows: rows[-6].update(requestSha256="0" * 64),
             "requestSha256"),
            (lambda rows: rows[-1].update(slot=1), "invalid or duplicate slot"),
        ):
            with self.subTest(error=expected_error):
                rows = self._bare_events()
                edit(rows)
                rejected = verify_request_events(self.bare_request, rows)
                self.assertFalse(rejected["passed"])
                self.assertTrue(any(expected_error in error for error in rejected["errors"]),
                                rejected["errors"])

    def _snapshot_events(self):
        rows = self._bare_events()
        digest = request_sha256(self.snapshot_request)
        for row in rows:
            if "requestSha256" in row:
                row["requestSha256"] = digest
            if row.get("status") == "original_character_data_prepared":
                row["characterSource"] = "installed_original_CharacterSnapshot_conversion"
        snapshots = []
        for row in rows:
            if row.get("status") != "original_character_data_prepared":
                continue
            skills = {}
            for key, source in zip(("skill1", "skill2", "burst"), row["skillSources"]):
                skills[key] = {"groupId": source["group"], "tableType": source["tableType"],
                               "level": source["level"], "disabled": False,
                               "favoriteItem": False}
            snapshots.append({"status": "original_bare_snapshot_applied",
                "slot": row["slot"], "nameCode": row["nameCode"], "tableId": row["tableId"],
                "level": row["level"], "grade": row["grade"], "core": row["core"],
                "requestSha256": digest, "barePolicy": copy.deepcopy(row["barePolicy"]),
                "source": "installed_original_CharacterSnapshot_conversion",
                "positionType": row["slot"], "emptyBuffCount": 0,
                "stats": copy.deepcopy(row["stats"]),
                "skillSources": copy.deepcopy(row["skillSources"]),
                "nativeValues": {"nameCode": row["nameCode"], "level": row["level"],
                    "grade": row["grade"], "core": row["core"], "costumeTableId": 0,
                    "positionType": row["slot"],
                    "buffStaticInfos": {"type": "BuffStaticInfo[]", "length": 0},
                    "stats": {key: str(value) for key, value in row["stats"].items()},
                    "skills": skills, "battlePower": 1000,
                    "overrideElements": {"type": "List", "count": 0},
                    "addedPassiveList": {"type": "List", "count": 0}}})
        return rows + snapshots

    def test_snapshot_mode_requires_original_conversion_for_all_five_slots(self):
        self.assertIs(validate_request(self.snapshot_request), self.snapshot_request)
        rows = self._snapshot_events()
        receipt = verify_request_events(self.snapshot_request, rows)
        self.assertTrue(receipt["passed"], receipt["errors"])
        self.assertEqual(receipt["bareSnapshotRows"], 5)
        for edit, expected_error in (
            (lambda events: events.pop(), "expected 5 rows"),
            (lambda events: events[-1]["nativeValues"]["skills"]["burst"].update(
                favoriteItem=True), "native burst differs"),
            (lambda events: events[-1]["nativeValues"]["stats"].update(Attack="999"),
             "native status differs"),
            (lambda events: (events[-1].update(positionType=1),
                             events[-1]["nativeValues"].update(positionType=1)),
             "native identity/position/buffs invalid"),
            (lambda events: events[-1].update(slot=1), "invalid or duplicate slot"),
        ):
            with self.subTest(error=expected_error):
                changed = self._snapshot_events()
                edit(changed)
                rejected = verify_request_events(self.snapshot_request, changed)
                self.assertFalse(rejected["passed"])
                self.assertTrue(any(expected_error in error for error in rejected["errors"]),
                                rejected["errors"])


if __name__ == "__main__":
    unittest.main()
