"""Negative contracts for one native Chatterbox cover episode; no native run."""

from __future__ import annotations

import json
import unittest
from pathlib import Path
from unittest.mock import patch
import mechanics_request

from mechanics_request import request_sha256
from verify_chatterbox_cover_trial import verify


REQUEST = json.loads(Path(__file__).with_name("mechanics_request_chatterbox.json").read_text())
REGISTRY = json.loads(Path(__file__).with_name("mechanics-encounters-current.json").read_text())
# Mock contracts use the committed registry fixture; installed DLL/table hashes
# are verified separately by the native runner, never required by this suite.
with patch.object(mechanics_request, "current_encounter_registry", return_value=REGISTRY):
    DIGEST = request_sha256(REQUEST)
SCENE = {"complete_battle_executed": True, "errors": [], "clean_quit_observed": True}
REQUEST_CHECK = {"passed": True, "requestSha256": DIGEST}


def _state(covered: bool, shots: int) -> dict:
    return {"autoAim": True, "forcedCover": covered, "inputType": 1,
            "squad": [{"entityId": 4096 + index,
                       "usedAmmoCount": shots} for index in range(5)]}


def _squad() -> dict:
    return {"supported": True, "characters": [
        {"id": 4096 + index, "health": {"hp": "474573"},
         "cover": {"id": 268455936 + 65536 * index,
                   "health": {"hp": "520100"}}}
        for index in range(5)]}


def complete_rows() -> list[dict]:
    rows = [
        {"status": "original_chatterbox_cover_probe_ready", "waveId": 6302004,
         "monsterTableId": 1520020113,
         "expectedInstalledDllSha256": REQUEST["installedClientSha256"],
         "coverFeasibility": "unvalidated"},
        {"status": "original_chatterbox_node6_skill_observed", "tick": 4,
         "nodeId": 6, "animationNumber": 9, "skillId": 510209},
        {"status": "original_chatterbox_first_fire_casting", "tick": 4,
         "entityId": 8192},
        {"status": "original_chatterbox_diagnostic_cover_on", "tick": 5,
         "castTick": 4, "nodeId": 6, "skillId": 510209, "wholeSquad": True,
         "squadObservationTick": 4,
         "nativeBefore": _state(False, 10), "nativeAfter": _state(True, 10),
         "squadBefore": _squad()},
        {"status": "original_chatterbox_first_fire", "tick": 87,
         "entityId": 8192},
        {"status": "original_threat_event", "kind": "cover_damage",
         "tick": 87, "casterId": 8192, "coverId": 268587008,
         "damage": "604650"},
        {"status": "original_threat_event", "kind": "damage",
         "tick": 87, "casterId": 8192, "targetId": 268587008,
         "targetType": "Cover", "actualDamage": "520100"},
        {"status": "original_chatterbox_first_play_end", "tick": 196,
         "nodeId": 6, "skillId": 510209},
        {"status": "original_chatterbox_diagnostic_cover_off", "tick": 197,
         "originalPlayEndTick": 196, "wholeSquad": True,
         "squadObservationTick": 196,
         "nativeBefore": _state(True, 10), "nativeAfter": _state(False, 10),
         "squadAfter": _squad()},
        {"status": "original_chatterbox_diagnostic_resume_readback",
         "tick": 207, "releaseTick": 197, "state": _state(False, 11),
         "firedAfterRelease": True},
        {"status": "original_terminal_result", "resultCaptured": True,
         "originalResult": True, "completeBattle": True,
         "resultType": "NK.BattleResult", "processState": 8,
         "result": 1, "targetMaxHp": "160011052", "targetRemainHp": "149455948",
         "advancedTicks": 1040, "rounds": [{"isWin": True}]},
        {"status": "original_tick_driver_stopped",
         "chatterboxCoverDiagnostic": {
             "scope": "first_node6_skill510209_only", "completed": True,
             "covered": False, "coverTick": 5, "releaseTick": 197,
             "fault": None,
             "firstStart": {"tick": 4}, "casting": {"tick": 4},
             "fired": {"tick": 87}, "end": {"tick": 196}},
         "threatObservation": {"droppedLogs": 0,
                               "transitionsTruncated": False,
                               "watchedFromFirstTrackedEvent": True}},
    ]
    return rows


class ChatterboxCoverTrialTests(unittest.TestCase):
    def setUp(self):
        registry_patch = patch.object(mechanics_request, "current_encounter_registry", return_value=REGISTRY)
        registry_patch.start()
        self.addCleanup(registry_patch.stop)

    def check(self, rows: list[dict], request_check: dict = REQUEST_CHECK) -> dict:
        return verify(rows, SCENE, REQUEST, request_check)

    def test_measured_interception_passes_without_claiming_boss_win(self) -> None:
        report = self.check(complete_rows())
        self.assertTrue(report["passed"], report["errors"])
        self.assertEqual(report["coverFeasibility"], "first_cast_intercepted")
        self.assertFalse(report["bossVictoryVerified"])

    def test_unclean_exit_cannot_pass(self) -> None:
        report = verify(complete_rows(), {**SCENE, "clean_quit_observed": False}, REQUEST, REQUEST_CHECK)
        self.assertFalse(report["passed"])
        self.assertIn("original native battle did not complete cleanly", report["errors"])

    def test_character_hit_at_first_fire_fails_despite_cover_hit(self) -> None:
        rows = complete_rows()
        rows.insert(6, {"status": "original_threat_event", "kind": "damage",
                        "tick": 87, "casterId": 8192, "targetId": 4098,
                        "targetType": "Character", "actualDamage": "474573"})
        report = self.check(rows)
        self.assertFalse(report["passed"])
        self.assertIn("original first cast still dealt positive damage to target 4098",
                      report["errors"])

    def test_unrelated_cover_damage_cannot_prove_interception(self) -> None:
        rows = complete_rows()
        cover = next(row for row in rows if row.get("kind") == "cover_damage")
        cover["coverId"] = 268521472
        self.assertFalse(self.check(rows)["passed"])

    def test_changed_target_hp_and_stale_request_fail(self) -> None:
        rows = complete_rows()
        end = next(row for row in rows if row.get("status") ==
                   "original_chatterbox_diagnostic_cover_off")
        end["squadAfter"]["characters"][2]["health"]["hp"] = "1"
        report = self.check(rows, {"passed": True, "requestSha256": "stale"})
        self.assertFalse(report["passed"])
        self.assertTrue(any("target 4098 HP" in error for error in report["errors"]))
        self.assertTrue(any("request preparation" in error for error in report["errors"]))

    def test_early_release_or_no_resume_fails(self) -> None:
        rows = complete_rows()
        off = next(row for row in rows if row.get("status") ==
                   "original_chatterbox_diagnostic_cover_off")
        off["tick"] = 86
        resume = next(row for row in rows if row.get("status") ==
                      "original_chatterbox_diagnostic_resume_readback")
        resume["state"] = _state(False, 10)
        report = self.check(rows)
        self.assertFalse(report["passed"])
        self.assertTrue(any("order invalid" in error for error in report["errors"]))
        self.assertTrue(any("did not measurably resume" in error for error in report["errors"]))

    def test_missing_squad_or_terminal_cannot_pass(self) -> None:
        rows = complete_rows()
        on = next(row for row in rows if row.get("status") ==
                  "original_chatterbox_diagnostic_cover_on")
        del on["squadBefore"]
        terminal = next(row for row in rows if row.get("status") ==
                        "original_terminal_result")
        terminal["resultCaptured"] = False
        report = self.check(rows)
        self.assertFalse(report["passed"])
        self.assertTrue(any("before/after squad" in error for error in report["errors"]))
        self.assertTrue(any("terminal BattleResult" in error for error in report["errors"]))


if __name__ == "__main__":
    unittest.main()
