"""Synthetic gate controls only, never original/native evidence."""
import copy

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
