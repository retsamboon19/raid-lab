"""Compact negative contracts for the immutable native boss-tactical receipt."""

import copy
import importlib.util
import unittest
from pathlib import Path


SPEC = importlib.util.spec_from_file_location(
    "verify_boss_tactical_trial", Path(__file__).with_name("verify_boss_tactical_trial.py"))
subject = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(subject)
SCENE = {"complete_battle_executed": True, "errors": []}


def base():
    rows = [
        {"status": "native_control_mode_selected", "controlMode": "boss-tactical",
         "policyVersion": "boss-tactical-v1",
         "observesNativeState": True, "issuesTacticalCommands": True},
        {"status": "synthetic_kraken_transporter_prepared", "waveId": 6302009},
        {"status": "original_terminal_result", "originalResult": True,
         "resultCaptured": True, "completeBattle": True, "advancedTicks": 100,
         "targetMaxHp": "1000", "rounds": [{}]},
        {"status": "original_tick_driver_stopped", "stage": "original_battle_ticks",
         "tacticalObservation": {"transitionsTruncated": False, "fault": None,
             "total": 0, "emitted": 0},
         "threatObservation": {"transitionsTruncated": False, "fault": None,
             "droppedLogs": 0, "emitted": 0},
         "tacticalControl": {"mode": "boss-tactical",
             "policyVersion": "boss-tactical-v1",
             "observationTransitionsTruncated": False, "fault": None,
             "policy": {"version": "reactive-qte-v1", "fault": None,
                 "unsupported": [], "owned": False, "nativeTerminalSuccesses": 0,
                 "nativeTerminalFailures": 0},
             "coverPolicy": {"version": "native-cover-v1", "covered": False,
                 "pending": [], "unsupported": [], "droppedLogs": 0,
                 "completed": 0, "resumeChecks": 0}}},
    ]
    return rows


def finalize(rows):
    stop = next(r for r in rows if r["status"] == "original_tick_driver_stopped")
    count = sum(r.get("status") == "original_tactical_transition" for r in rows)
    stop["tacticalObservation"].update(total=count, emitted=count)
    stop["threatObservation"]["emitted"] = sum(
        r.get("status") == "original_threat_event" for r in rows)
    return rows


def with_qte():
    rows = base()
    rows += [
        {"status": "original_tactical_transition", "kind": "QuickTimeStart",
         "tick": 1, "monsterInfoId": 50, "quickTimeId": 90},
        {"status": "original_tactical_transition", "kind": "QuickTimePresetStart",
         "tick": 1, "monsterInfoId": 50, "index": 212},
        {"status": "original_tactical_observation_change", "tick": 2,
         "qte": {"supported": True, "active": True, "groupId": 212,
             "currentIndex": 0, "currentOrder": 1, "targets": [
                 {"id": 1, "entityId": 101, "colType": {"name": "Break"},
                  "state": {"name": "Enable"}, "order": 1, "health": {"hp": "20"}},
                 {"id": 2, "entityId": 102, "colType": {"name": "Counter"},
                  "state": {"name": "Enable"}, "order": 1, "health": {"hp": "20"}}]}},
        {"status": "original_reactive_qte_decision", "action": "observed_qte",
         "tick": 2, "groupId": 212, "policyVersion": "reactive-qte-v1"},
        {"status": "original_reactive_qte_decision", "action": "aim_break",
         "tick": 3, "groupId": 212, "presetIndex": 0, "targetId": 1,
         "entityId": 101, "policyVersion": "reactive-qte-v1"},
        {"status": "original_tactical_transition", "kind": "QuickTimeColliderHit",
         "tick": 4, "entityInfoId": 101},
        {"status": "original_tactical_transition", "kind": "QuickTimePresetEnd",
         "tick": 5, "presetInfoId": 500, "success": True, "end": True},
        {"status": "original_reactive_qte_decision", "action": "native_preset_result",
         "tick": 5, "nativeEvent": {"tick": 5, "presetInfoId": 500,
                                       "success": True, "end": True},
         "policyVersion": "reactive-qte-v1"},
    ]
    stop = next(r for r in rows if r["status"] == "original_tick_driver_stopped")
    stop["tacticalControl"]["policy"] = {"version": "reactive-qte-v1", "fault": None,
        "unsupported": [], "owned": False, "nativeTerminalSuccesses": 1,
        "nativeTerminalFailures": 0}
    return finalize(rows)


def with_cover():
    rows = base()
    chars = [{"id": i, "health": {"hp": "100"}, "cover": {"id": i + 100}}
             for i in range(1, 6)]
    squad = [{"entityId": i, "usedAmmoCount": 10, "stance": 0}
             for i in range(1, 6)]
    attack = {"tick": 10, "casterId": 50, "attackNodeId": 230}
    rows += [
        {"status": "original_threat_event", "kind": "spawn", "tick": 14,
         "casterId": 50, "projectileId": 700},
        {"status": "original_threat_event", "kind": "despawn", "tick": 17,
         "projectileId": 700},
        *[{"status": "original_threat_event", "kind": "cover_damage", "tick": 16,
           "coverId": i + 100, "damage": "10"} for i in range(1, 6)],
        {"status": "native_cover_decision", "action": "danger_observed", "tick": 10,
         "key": "a"},
        {"status": "native_cover_decision", "action": "entered", "tick": 13,
         "threats": [{"key": "a", "attack": attack}],
         "squadBefore": {"characters": chars},
         "nativeAfter": {"forcedCover": True, "squad": copy.deepcopy(squad)}},
        {"status": "native_cover_decision", "action": "released", "tick": 18,
         "coverTick": 13, "resolved": [{"key": "a", "ruleId": "kraken-intercept-shot02-followup",
             "attack": attack, "sawSkill": True, "sawCasting": True,
             "condition": {"tick": 18, "condition": {"name": "Idle"}},
             "projectileIds": [700]}],
         "squadAfter": {"characters": copy.deepcopy(chars)},
         "nativeBefore": {"forcedCover": True, "squad": copy.deepcopy(squad)},
         "nativeAfter": {"forcedCover": False}},
        {"status": "native_cover_decision", "action": "resume_readback", "tick": 33,
         "releaseTick": 18, "firingResumed": True,
         "state": {"autoAim": True, "forcedCover": False,
                   "squad": [dict(unit, usedAmmoCount=11 if unit["entityId"] == 1 else 10)
                             for unit in squad]}},
    ]
    stop = next(r for r in rows if r["status"] == "original_tick_driver_stopped")
    stop["tacticalControl"]["coverPolicy"] = {"version": "native-cover-v1",
        "covered": False, "pending": [], "unsupported": [], "droppedLogs": 0,
        "completed": 1, "resumeChecks": 1}
    return finalize(rows)


def with_mirror_break(collider_id=3, collider_name="break_col_03"):
    rows = base()
    transporter = next(r for r in rows if r["status"] ==
                       "synthetic_kraken_transporter_prepared")
    transporter.update(status="original_encounter_transporter_prepared",
                       waveId=6302006,
                       encounterProfileId="anomaly-mirror-container",
                       requestSha256="a" * 64, roster=[101, 102, 103, 104, 105],
                       staticFieldInstalled=False, battleStarted=False,
                       resultCaptured=False)
    rows.append({"status": "original_current_wave_targets",
                 "targetIds": ["4510010123"]})
    rows.extend({"status": "original_aim_state", "requestSha256": "a" * 64,
                 "nameCode": 101 + i, "entityId": 4100 + i}
                for i in range(5))
    target = {"colliderId": collider_id, "name": collider_name,
              "type": {"value": 3, "name": "Break"},
              "hp": "100", "maxHp": "100", "unityLive": True,
              "enabled": True, "liveBreakTarget": True,
              "aimPointBasis": "UnityEngine.Collider.bounds.center",
              "worldAimPoint": [1.0, 2.0, 3.0]}
    def snapshot(tick, hp):
        item = copy.deepcopy(target)
        item["hp"] = hp
        return {"status": "original_break_observation_change", "tick": tick,
                "monsters": [{"supported": True, "entityId": 8192,
                              "tableId": "4510010123", "playing": True,
                              "nativeIsAllBreak": False, "colliders": [item]}]}
    def event(kind, tick, **extra):
        return {"status": "original_break_transition", "kind": kind,
                "ownerId": 8192, "tick": tick, **extra}
    def decision(action, tick, **extra):
        return {"status": "original_mirror_break_decision", "action": action,
                "tick": tick, "policyVersion": "mirror-live-break-candidate-v2",
                **extra}
    rows += [
        event("MonsterBreakColliderActiveStart", 9),
        event("MonsterBreakColliderActiveStarted", 9),
        snapshot(10, "100"),
        decision("observed_live_break_episode", 10, ownerId=8192),
        decision("take_manual_control", 11, actorId=4100),
        decision("aim_live_break", 11, actorId=4100, ownerId=8192,
                 colliderId=collider_id, targetKey=f"8192:{collider_id}",
                 sourceSkillLinkVerified=False),
        {"phase": "mechanics_tactical_actions", "action": "press"},
        event("MonsterBreakColliderHurt", 15, colliderId=collider_id, damage="30"),
        snapshot(15, "70"),
        event("MonsterAllBreakCollider", 16, isBreak=True,
              lastBrokenColliderId=collider_id),
        event("MonsterSkillInterruptionEvent", 17, isInterrupt=True),
        decision("release_manual_control", 18, actorId=4100),
    ]
    stop = next(r for r in rows if r["status"] == "original_tick_driver_stopped")
    stop["breakableObservation"] = {"eventTransitionsTruncated": False,
        "fault": None, "totalEvents": 5, "emittedEvents": 5}
    stop["tacticalControl"].update(
        breakSamples=2, breakTransitions=2,
        breakObservationTransitionsTruncated=False,
        breakPolicy={"version": "mirror-live-break-candidate-v2",
            "waveId": 6302006, "monsterTableId": "4510010123",
            "candidateSourceSkillIds": [520669, 520676],
            "expectedSourceSkillId": None,
            "sourceSkillLinkVerified": False, "nativeCancellationVerified": False,
            "aimpointHitVerified": False, "owned": False, "fault": None,
            "unsupported": [], "decisionsTruncated": False,
            "targetsSelected": 1})
    return finalize(rows)


def with_bound_mirror_reselection():
    """Sparse transition log, but the decision carries its exact sampled state."""
    rows = with_mirror_break(819201, "break_col_01")
    start = next(r for r in rows if r.get("kind") ==
                 "MonsterBreakColliderActiveStart")
    start["sequence"] = 1
    for row in rows:
        if row.get("status") == "original_mirror_break_decision" and row["tick"] >= 11:
            row["tick"] += 1144
        elif row.get("status") == "original_break_transition" and row["tick"] >= 15:
            row["tick"] += 1144
        elif row.get("status") == "original_break_observation_change" and row["tick"] == 15:
            row["tick"] += 1144
    choice = next(r for r in rows if r.get("action") == "aim_live_break")
    choice.update(name="break_col_01", hp="100", maxHp="100",
                  aimPointBasis="UnityEngine.Collider.bounds.center")
    choice_index = next(i for i, row in enumerate(rows) if row.get("action") ==
                        "aim_live_break")
    bound = copy.deepcopy(next(r for r in rows if r.get("status") ==
                               "original_break_observation_change" and r["tick"] == 10))
    bound.update(status="original_break_action_observation", supported=True,
                 tick=1155,
                 decisionTick=1155, actorId=4100, ownerId=8192,
                 colliderId=819201, latestEpisodes=[{"ownerId": 8192,
                     "startSequence": 1, "startTick": 9, "started": True}])
    rows.insert(choice_index, bound)
    return rows


class BossTacticalReceiptTests(unittest.TestCase):
    def test_unexercised_is_explicit_not_pass_for_mechanic(self):
        report = subject.verify(base(), SCENE)
        self.assertTrue(report["passed"], report["errors"])
        self.assertEqual(report["qte"]["status"], "NOT_EXERCISED")
        self.assertEqual(report["cover"]["status"], "NOT_EXERCISED")

    def test_original_qte_positive_control_and_counter_rejection(self):
        rows = with_qte()
        self.assertEqual(subject.verify(rows, SCENE)["qte"]["status"], "PASS")
        bad = copy.deepcopy(rows)
        next(r for r in bad if r.get("kind") == "QuickTimeColliderHit")["entityInfoId"] = 102
        self.assertEqual(subject.verify(bad, SCENE)["qte"]["status"], "FAIL")

    def test_qte_failed_native_preset_and_wrong_order_rejected(self):
        bad = with_qte()
        next(r for r in bad if r.get("kind") == "QuickTimePresetEnd")["success"] = False
        self.assertFalse(subject.verify(bad, SCENE)["passed"])
        bad = with_qte()
        next(r for r in bad if r.get("status") == "original_tactical_observation_change")\
            ["qte"]["targets"][0]["order"] = 2
        self.assertEqual(subject.verify(bad, SCENE)["qte"]["status"], "FAIL")

    def test_original_cover_positive_control_and_missed_release(self):
        rows = with_cover()
        self.assertEqual(subject.verify(rows, SCENE)["cover"]["status"], "PASS")
        bad = copy.deepcopy(rows)
        next(r for r in bad if r.get("action") == "released")["nativeAfter"]["forcedCover"] = True
        self.assertEqual(subject.verify(bad, SCENE)["cover"]["status"], "FAIL")

    def test_cover_rejects_early_idle_projectile_or_hp_loss(self):
        bad = with_cover()
        next(r for r in bad if r.get("action") == "released")["resolved"][0]\
            ["condition"]["condition"]["name"] = "FireCasting"
        self.assertEqual(subject.verify(bad, SCENE)["cover"]["status"], "FAIL")
        bad = with_cover()
        next(r for r in bad if r.get("kind") == "despawn")["tick"] = 19
        self.assertEqual(subject.verify(bad, SCENE)["cover"]["status"], "FAIL")
        bad = with_cover()
        next(r for r in bad if r.get("action") == "released")["squadAfter"]\
            ["characters"][0]["health"]["hp"] = "90"
        self.assertEqual(subject.verify(bad, SCENE)["cover"]["status"], "FAIL")

    def test_truncated_observer_missing_terminal_and_scene_fail_closed(self):
        rows = with_qte()
        stop = next(r for r in rows if r["status"] == "original_tick_driver_stopped")
        stop["tacticalObservation"]["transitionsTruncated"] = True
        self.assertFalse(subject.verify(rows, SCENE)["passed"])
        rows = [r for r in base() if r["status"] != "original_terminal_result"]
        self.assertFalse(subject.verify(rows, SCENE)["passed"])
        self.assertFalse(subject.verify(base())["passed"])
        bad = with_qte()
        next(r for r in bad if r.get("kind") == "QuickTimeStart")["tick"] = None
        self.assertEqual(subject.verify(bad, SCENE)["qte"]["status"], "FAIL")

    def test_mirror_break_reports_targeting_and_unassociated_native_outcome(self):
        report = subject.verify(with_mirror_break(), SCENE)
        self.assertTrue(report["passed"], report["errors"])
        self.assertEqual(report["break"]["targeting"], "PASS")
        self.assertEqual(report["break"]["interruption"], "OBSERVED_UNASSOCIATED")
        self.assertFalse(report["break"]["sourceSkillAssociationVerified"])
        self.assertEqual(report["break"]["matchedOriginalHits"][0]["afterHp"], "70")

    def test_mirror_initial_phase_source_pair_is_eligible_without_skill_claim(self):
        for collider_id, name in ((819201, "break_col_01"),
                                  (819202, "break_col_02")):
            rows = with_mirror_break(collider_id, name)
            report = subject.verify(rows, SCENE)
            self.assertTrue(report["passed"], (name, report["break"]["errors"]))
            self.assertEqual(report["break"]["matchedOriginalHits"][0]
                             ["colliderId"], collider_id)
            self.assertFalse(report["break"]["sourceSkillAssociationVerified"])

    def test_mirror_bound_native_state_validates_sparse_later_selection(self):
        rows = with_bound_mirror_reselection()
        report = subject.verify(rows, SCENE)
        self.assertTrue(report["passed"], report["break"]["errors"])
        for field, bad in (("decisionTick", 1156), ("actorId", 4099),
                           ("colliderId", 819202), ("tick", 1150)):
            altered = copy.deepcopy(rows)
            bound = next(r for r in altered if r.get("status") ==
                         "original_break_action_observation")
            bound[field] = bad
            self.assertEqual(subject.verify(altered, SCENE)["break"]["status"],
                             "FAIL", field)
        altered = copy.deepcopy(rows)
        bound = next(r for r in altered if r.get("status") ==
                     "original_break_action_observation")
        bound["latestEpisodes"][0]["startSequence"] = 2
        self.assertEqual(subject.verify(altered, SCENE)["break"]["status"], "FAIL")
        altered = copy.deepcopy(rows)
        next(r for r in altered if r.get("kind") ==
             "MonsterBreakColliderHurt")["damage"] = "0"
        self.assertEqual(subject.verify(altered, SCENE)["break"]["targeting"], "FAIL")
        altered = copy.deepcopy(rows)
        later = next(r for r in altered if r.get("status") ==
                     "original_break_observation_change" and r["tick"] == 1159)
        later["monsters"][0]["colliders"][0]["hp"] = "100"
        self.assertEqual(subject.verify(altered, SCENE)["break"]["targeting"], "FAIL")

    def test_mirror_pre_activation_empty_state_is_not_a_false_fault(self):
        rows = with_mirror_break()
        first_start = next(i for i, row in enumerate(rows) if row.get("kind") ==
                           "MonsterBreakColliderActiveStart")
        rows.insert(first_start, {"status": "original_break_observation_change",
                                  "tick": 6,
                                  "monsters": [{"entityId": 8192,
                                                "tableId": "4510010123",
                                                "playing": False,
                                                "nativeIsAllBreak": True,
                                                "colliders": []}]})
        stop = next(r for r in rows if r["status"] == "original_tick_driver_stopped")
        stop["tacticalControl"]["breakTransitions"] = 3
        self.assertTrue(subject.verify(rows, SCENE)["passed"])

    def test_mirror_no_break_episode_is_not_exercised_and_not_a_pass(self):
        rows = with_mirror_break()
        rows[:] = [r for r in rows if r.get("status") not in {
            "original_mirror_break_decision", "original_break_observation_change",
            "original_break_transition"}]
        stop = next(r for r in rows if r["status"] == "original_tick_driver_stopped")
        stop["breakableObservation"].update(totalEvents=0, emittedEvents=0)
        stop["tacticalControl"].update(breakTransitions=0)
        report = subject.verify(rows, SCENE)
        self.assertEqual(report["break"]["status"], "NOT_EXERCISED")
        self.assertFalse(report["passed"])

    def test_mirror_intent_without_native_hurt_press_or_hp_drop_fails(self):
        for change in ("hurt", "press", "hp"):
            rows = with_mirror_break()
            if change == "hurt":
                rows[:] = [r for r in rows if r.get("kind") !=
                           "MonsterBreakColliderHurt"]
                stop = next(r for r in rows if r["status"] == "original_tick_driver_stopped")
                stop["breakableObservation"].update(totalEvents=4, emittedEvents=4)
            elif change == "press":
                rows[:] = [r for r in rows if not (r.get("phase") ==
                    "mechanics_tactical_actions" and r.get("action") == "press")]
            else:
                next(r for r in rows if r.get("status") ==
                     "original_break_observation_change" and r["tick"] == 15)\
                    ["monsters"][0]["colliders"][0]["hp"] = "100"
            report = subject.verify(rows, SCENE)
            self.assertEqual(report["break"]["targeting"], "FAIL", change)
            self.assertFalse(report["passed"], change)

    def test_mirror_wrong_owner_counter_and_stale_state_fail_closed(self):
        for change in ("owner", "counter", "stale"):
            rows = with_mirror_break()
            if change == "owner":
                next(r for r in rows if r.get("kind") ==
                     "MonsterBreakColliderHurt")["ownerId"] = 8193
            elif change == "counter":
                for row in rows:
                    if row.get("status") == "original_break_observation_change":
                        row["monsters"][0]["colliders"][0]["type"]["name"] = "Counter"
            else:
                next(r for r in rows if r.get("status") ==
                     "original_mirror_break_decision" and
                     r.get("action") == "aim_live_break")["tick"] = 14
            report = subject.verify(rows, SCENE)
            self.assertEqual(report["break"]["status"], "FAIL", change)

    def test_mirror_unsafe_counter_health_and_missing_input_lease_fail(self):
        rows = with_mirror_break()
        for row in rows:
            if row.get("status") == "original_break_observation_change":
                unsafe = copy.deepcopy(row["monsters"][0]["colliders"][0])
                unsafe.update(colliderId=4, name="counter_col",
                              type={"value": 4, "name": "Counter"},
                              hp="10" if row["tick"] == 10 else "9",
                              liveBreakTarget=False)
                row["monsters"][0]["colliders"].append(unsafe)
        report = subject.verify(rows, SCENE)
        self.assertEqual(report["break"]["status"], "FAIL")
        self.assertTrue(any("Counter/Choice" in e for e in report["break"]["errors"]))
        rows = with_mirror_break()
        rows[:] = [r for r in rows if not (r.get("status") ==
            "original_mirror_break_decision" and r.get("action") ==
            "take_manual_control")]
        self.assertEqual(subject.verify(rows, SCENE)["break"]["targeting"], "FAIL")

    def test_mirror_rearmed_episode_allows_new_type_and_counter_hp_reset(self):
        rows = with_mirror_break()
        old = next(r for r in rows if r.get("status") ==
                   "original_break_observation_change" and r["tick"] == 15)
        first_counter = copy.deepcopy(old["monsters"][0]["colliders"][0])
        first_counter.update(colliderId=4, name="counter_col",
                             type={"value": 4, "name": "Counter"},
                             hp="10", liveBreakTarget=False)
        old["monsters"][0]["colliders"].append(first_counter)
        rearmed = copy.deepcopy(old)
        rearmed["tick"] = 25
        rearmed["monsters"][0]["colliders"][0].update(
            type={"value": 4, "name": "Counter"}, hp="100",
            liveBreakTarget=False)
        rearmed["monsters"][0]["colliders"][1]["hp"] = "20"
        rows.extend([
            {"status": "original_break_transition", "kind":
             "MonsterBreakColliderActiveStart", "ownerId": 8192,
             "tick": 25, "sequence": 6},
            {"status": "original_break_transition", "kind":
             "MonsterBreakColliderActiveStarted", "ownerId": 8192,
             "tick": 25, "sequence": 7},
            rearmed,
        ])
        stop = next(r for r in rows if r["status"] == "original_tick_driver_stopped")
        stop["breakableObservation"].update(totalEvents=7, emittedEvents=7)
        stop["tacticalControl"]["breakTransitions"] = 3
        report = subject.verify(rows, SCENE)
        self.assertTrue(report["passed"], report["break"]["errors"])
        self.assertEqual(report["break"]["targeting"], "PASS")
        self.assertEqual(report["break"]["matchedOriginalHits"][0]["episodeStartTick"], 9)

    def test_mirror_counter_hurt_within_episode_is_unsafe(self):
        rows = with_mirror_break()
        for row in rows:
            if row.get("status") == "original_break_observation_change":
                unsafe = copy.deepcopy(row["monsters"][0]["colliders"][0])
                unsafe.update(colliderId=4, name="counter_col",
                              type={"value": 4, "name": "Counter"},
                              hp="10", liveBreakTarget=False)
                row["monsters"][0]["colliders"].append(unsafe)
        rows.append({"status": "original_break_transition", "kind":
                     "MonsterBreakColliderHurt", "ownerId": 8192,
                     "colliderId": 4, "damage": "1", "tick": 16})
        stop = next(r for r in rows if r["status"] == "original_tick_driver_stopped")
        stop["breakableObservation"].update(totalEvents=6, emittedEvents=6)
        report = subject.verify(rows, SCENE)
        self.assertEqual(report["break"]["status"], "FAIL")
        self.assertTrue(any("Counter/Choice or unknown" in e
                            for e in report["break"]["errors"]))

    def test_mirror_release_or_reacquisition_before_hurt_breaks_pairing(self):
        for action in ("release_manual_control", "take_manual_control", "suspended"):
            rows = with_mirror_break()
            hurt_index = next(i for i, row in enumerate(rows) if row.get("kind") ==
                              "MonsterBreakColliderHurt")
            rows.insert(hurt_index, {"status": "original_mirror_break_decision",
                                     "action": action, "tick": 14,
                                     "actorId": 4100,
                                     "policyVersion": "mirror-live-break-candidate-v2"})
            report = subject.verify(rows, SCENE)
            self.assertEqual(report["break"]["targeting"], "FAIL", action)
            self.assertTrue(any("lost input lease" in e
                                for e in report["break"]["errors"]), action)
        rows = with_mirror_break()
        hurt_index = next(i for i, row in enumerate(rows) if row.get("kind") ==
                          "MonsterBreakColliderHurt")
        rows.insert(hurt_index, {"phase": "mechanics_tactical_actions",
                                 "action": "release"})
        self.assertEqual(subject.verify(rows, SCENE)["break"]["targeting"], "FAIL")

    def test_mirror_same_tick_rearm_cannot_supply_prior_episode_hit(self):
        rows = with_mirror_break()
        hurt_index = next(i for i, row in enumerate(rows) if row.get("kind") ==
                          "MonsterBreakColliderHurt")
        rows[hurt_index:hurt_index] = [
            {"status": "original_break_transition", "kind":
             "MonsterBreakColliderActiveStart", "ownerId": 8192,
             "tick": 15, "sequence": 4},
            {"status": "original_break_transition", "kind":
             "MonsterBreakColliderActiveStarted", "ownerId": 8192,
             "tick": 15, "sequence": 5},
        ]
        stop = next(r for r in rows if r["status"] == "original_tick_driver_stopped")
        stop["breakableObservation"].update(totalEvents=7, emittedEvents=7)
        report = subject.verify(rows, SCENE)
        self.assertEqual(report["break"]["targeting"], "FAIL")
        self.assertEqual(report["break"]["interruption"], "UNVERIFIED")

    def test_mirror_missing_outcome_keeps_hit_proof_separate(self):
        for missing in ("MonsterAllBreakCollider", "MonsterSkillInterruptionEvent"):
            rows = with_mirror_break()
            rows[:] = [r for r in rows if r.get("kind") != missing]
            stop = next(r for r in rows if r["status"] == "original_tick_driver_stopped")
            stop["breakableObservation"].update(totalEvents=4, emittedEvents=4)
            report = subject.verify(rows, SCENE)
            self.assertEqual(report["break"]["targeting"], "PASS")
            self.assertEqual(report["break"]["interruption"], "UNVERIFIED")
            self.assertFalse(report["passed"])

    def test_mirror_rejects_truncation_ownership_and_wrong_source_identity(self):
        for change in ("truncation", "ownership", "profile", "request", "target",
                       "live_actor"):
            rows = with_mirror_break()
            stop = next(r for r in rows if r["status"] == "original_tick_driver_stopped")
            transporter = next(r for r in rows if r["status"] ==
                               "original_encounter_transporter_prepared")
            if change == "truncation":
                stop["breakableObservation"]["eventTransitionsTruncated"] = True
            elif change == "ownership":
                stop["tacticalControl"]["breakPolicy"]["owned"] = True
            elif change == "profile":
                transporter["encounterProfileId"] = "other"
            elif change == "request":
                transporter["requestSha256"] = "bad"
            elif change == "live_actor":
                next(r for r in rows if r["status"] == "original_aim_state")\
                    ["requestSha256"] = "b" * 64
            else:
                next(r for r in rows if r["status"] ==
                     "original_current_wave_targets")["targetIds"] = ["other"]
            self.assertFalse(subject.verify(rows, SCENE)["passed"], change)

    def test_non_mirror_break_events_do_not_claim_mirror_mechanic(self):
        rows = base()
        rows.append({"status": "original_break_transition",
                     "kind": "MonsterBreakColliderActiveStart",
                     "ownerId": 8192, "tick": 5})
        report = subject.verify(rows, SCENE)
        self.assertEqual(report["break"]["status"], "NOT_EXERCISED")
        self.assertTrue(report["passed"], report["errors"])


if __name__ == "__main__":
    unittest.main()
