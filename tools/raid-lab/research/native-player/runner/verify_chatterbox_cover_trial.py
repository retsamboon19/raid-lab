"""Fail-closed receipt for one original Chatterbox Shot09 cover experiment.

A passing result establishes interception of this first cast in this exact
diagnostic request only. It does not establish a boss victory or a reusable
safe-cover rule.
"""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

from mechanics_request import request_sha256, verify_request_events


STATUSES = {
    "ready": "original_chatterbox_cover_probe_ready",
    "start": "original_chatterbox_node6_skill_observed",
    "cast": "original_chatterbox_first_fire_casting",
    "cover_on": "original_chatterbox_diagnostic_cover_on",
    "fire": "original_chatterbox_first_fire",
    "end": "original_chatterbox_first_play_end",
    "cover_off": "original_chatterbox_diagnostic_cover_off",
    "resume": "original_chatterbox_diagnostic_resume_readback",
    "terminal": "original_terminal_result",
    "stop": "original_tick_driver_stopped",
}


def _one(rows: list[dict], status: str, errors: list[str]) -> dict | None:
    matches = [row for row in rows if row.get("status") == status]
    if len(matches) != 1:
        errors.append(f"{status}: expected exactly one row, got {len(matches)}")
        return None
    return matches[0]


def _tick(value: object) -> bool:
    return type(value) is int and value >= 0


def _positive_decimal(value: object) -> int | None:
    if not isinstance(value, str) or not value.isdecimal():
        return None
    amount = int(value)
    return amount if amount > 0 else None


def _squad(value: object) -> dict[int, dict]:
    if not isinstance(value, dict) or value.get("supported") is not True:
        return {}
    members = value.get("characters")
    if not isinstance(members, list) or len(members) != 5:
        return {}
    found = {}
    for member in members:
        if not isinstance(member, dict) or type(member.get("id")) is not int:
            return {}
        found[member["id"]] = member
    return found if len(found) == 5 else {}


def _ammo(value: object) -> dict[int, int]:
    if not isinstance(value, dict):
        return {}
    members = value.get("squad")
    if not isinstance(members, list) or len(members) != 5:
        return {}
    found = {}
    for member in members:
        if (not isinstance(member, dict) or
            type(member.get("entityId")) is not int or
            type(member.get("usedAmmoCount")) is not int):
            return {}
        found[member["entityId"]] = member["usedAmmoCount"]
    return found if len(found) == 5 else {}


def verify(rows: list[dict], scene: dict, request: dict,
           request_check: dict) -> dict:
    errors: list[str] = []
    if not isinstance(rows, list) or any(not isinstance(row, dict) for row in rows):
        return {"passed": False, "errors": ["event log is not a list of objects"]}
    if not isinstance(scene, dict) or not isinstance(request, dict) or not isinstance(request_check, dict):
        return {"passed": False, "errors": ["scene/request verification input absent"]}

    digest = request_sha256(request)
    encounter = request.get("encounter") or {}
    if (request.get("schemaVersion") != 2 or
        request.get("encounterProfileId") != "special-chatterbox" or
        encounter.get("waveId") != 6302004 or
        encounter.get("isAuto") is not True):
        errors.append("request is not exact original-auto Special Chatterbox encounter")
    if (request_check.get("passed") is not True or
        request_check.get("requestSha256") != digest):
        errors.append("native request preparation/result readbacks failed or differ from request")
    if any(row.get("requestSha256") != digest for row in rows if "requestSha256" in row):
        errors.append("event log contains a different request hash")
    if (scene.get("complete_battle_executed") is not True or scene.get("errors") != [] or
            scene.get("clean_quit_observed") is not True):
        errors.append("original native battle did not complete cleanly")

    records = {key: _one(rows, status, errors) for key, status in STATUSES.items()}
    if any(row is None for row in records.values()):
        return {"passed": False, "errors": errors, "requestSha256": digest,
                "coverFeasibility": "unverified"}
    ready = records["ready"]
    start, cast, cover_on, fire, end, cover_off, resume = (
        records[name] for name in
        ("start", "cast", "cover_on", "fire", "end", "cover_off", "resume"))
    terminal, stop = records["terminal"], records["stop"]
    if (ready.get("waveId") != 6302004 or
        ready.get("monsterTableId") != 1520020113 or
        ready.get("expectedInstalledDllSha256") != request.get("installedClientSha256") or
        ready.get("coverFeasibility") != "unvalidated"):
        errors.append("installed Chatterbox probe/source identity not bound")

    ticks = [row.get("tick") for row in
             (start, cast, cover_on, fire, end, cover_off, resume)]
    if (not all(_tick(tick) for tick in ticks) or
        not ticks[0] <= ticks[1] < ticks[2] < ticks[3] <= ticks[4] < ticks[5] < ticks[6]):
        errors.append("original node/cast/cover/Fire/PlayEnd/release/resume order invalid")
    if (start.get("nodeId") != 6 or start.get("animationNumber") != 9 or
        start.get("skillId") != 510209 or
        any(row.get("entityId") != 8192 for row in (cast, fire)) or
        end.get("nodeId") != 6 or end.get("skillId") != 510209 or
        cover_on.get("nodeId") != 6 or cover_on.get("skillId") != 510209 or
        cover_on.get("castTick") != cast.get("tick") or
        cover_off.get("originalPlayEndTick") != end.get("tick") or
        resume.get("releaseTick") != cover_off.get("tick")):
        errors.append("original first node 6 / skill 510209 instance chain not bound")
    if cover_on.get("wholeSquad") is not True or cover_off.get("wholeSquad") is not True:
        errors.append("diagnostic did not use original whole-squad cover input")
    if (cover_on.get("squadObservationTick") != cover_on.get("tick", -1) - 1 or
        cover_off.get("squadObservationTick") != cover_off.get("tick", -1) - 1):
        errors.append("squad observations were not bound to pre-decision original ticks")

    on_before, on_after = cover_on.get("nativeBefore") or {}, cover_on.get("nativeAfter") or {}
    off_before, off_after = cover_off.get("nativeBefore") or {}, cover_off.get("nativeAfter") or {}
    resumed = resume.get("state") or {}
    if (on_before.get("forcedCover") is not False or
        on_after.get("forcedCover") is not True or
        off_before.get("forcedCover") is not True or
        off_after.get("forcedCover") is not False or
        resumed.get("forcedCover") is not False or
        any(state.get("autoAim") is not True for state in
            (on_before, on_after, off_before, off_after, resumed))):
        errors.append("original cover readbacks or auto-aim ownership changed unexpectedly")

    before, after = _squad(cover_on.get("squadBefore")), _squad(cover_off.get("squadAfter"))
    target = 4098
    if not before or before.keys() != after.keys() or target not in before:
        errors.append("five original before/after squad health identities absent")
        target_cover_id = None
    else:
        old_hp = _positive_decimal((before[target].get("health") or {}).get("hp"))
        new_hp = _positive_decimal((after[target].get("health") or {}).get("hp"))
        target_cover_id = (before[target].get("cover") or {}).get("id")
        if (old_hp is None or old_hp != new_hp or
            type(target_cover_id) is not int or
            target_cover_id != (after[target].get("cover") or {}).get("id")):
            errors.append("target 4098 HP changed/died or original cover identity changed")

    if all(_tick(tick) for tick in ticks):
        attack_events = [row for row in rows if row.get("status") == "original_threat_event" and
                         _tick(row.get("tick")) and
                         cover_on["tick"] <= row["tick"] <= end["tick"] and
                         row.get("casterId") == 8192]
        fire_cover = [row for row in attack_events if row.get("kind") == "cover_damage" and
                      row.get("tick") == fire["tick"] and
                      row.get("coverId") == target_cover_id and
                      _positive_decimal(row.get("damage")) is not None]
        if target_cover_id is None or not fire_cover:
            errors.append("positive original hit on target 4098 cover at first Fire absent")
        if any(row.get("kind") == "damage" and row.get("targetType") == "Character" and
               row.get("targetId") == target and
               _positive_decimal(row.get("actualDamage")) is not None
               for row in attack_events):
            errors.append("original first cast still dealt positive damage to target 4098")
    else:
        fire_cover = []

    ammo_release, ammo_resumed = _ammo(off_after), _ammo(resumed)
    if (resume.get("firedAfterRelease") is not True or
        not ammo_release or ammo_release.keys() != ammo_resumed.keys() or
        not any(ammo_resumed[identity] > ammo_release[identity]
                for identity in ammo_release)):
        errors.append("original automatic firing did not measurably resume after release")

    episode = stop.get("chatterboxCoverDiagnostic") or {}
    if (episode.get("scope") != "first_node6_skill510209_only" or
        episode.get("completed") is not True or episode.get("covered") is not False or
        episode.get("coverTick") != cover_on.get("tick") or
        episode.get("releaseTick") != cover_off.get("tick") or
        episode.get("fault") is not None or
        (episode.get("firstStart") or {}).get("tick") != start.get("tick") or
        (episode.get("casting") or {}).get("tick") != cast.get("tick") or
        (episode.get("fired") or {}).get("tick") != fire.get("tick") or
        (episode.get("end") or {}).get("tick") != end.get("tick")):
        errors.append("one-episode original action summary missing, faulted, or inconsistent")
    threat = stop.get("threatObservation") or {}
    if (threat.get("droppedLogs") != 0 or
        threat.get("transitionsTruncated") is not False or
        threat.get("watchedFromFirstTrackedEvent") is not True):
        errors.append("original threat damage log is incomplete or truncated")
    if (terminal.get("resultCaptured") is not True or
        terminal.get("originalResult") is not True or
        terminal.get("completeBattle") is not True or
        terminal.get("resultType") != "NK.BattleResult" or
        terminal.get("processState") not in (8, 9) or
        not _positive_decimal(terminal.get("targetMaxHp")) or
        not _tick(terminal.get("advancedTicks")) or
        not isinstance(terminal.get("rounds"), list) or
        not terminal["rounds"]):
        errors.append("complete original terminal BattleResult absent")

    return {"passed": not errors, "errors": errors, "requestSha256": digest,
            "coverFeasibility": "first_cast_intercepted" if not errors else "unverified",
            "scope": "diagnostic first Chatterbox node 6 / skill 510209 only",
            "bossVictoryVerified": False,
            "coverTick": cover_on.get("tick"), "fireTick": fire.get("tick"),
            "releaseTick": cover_off.get("tick"),
            "targetCoverId": target_cover_id,
            "positiveTargetCoverHitsAtFire": len(fire_cover)}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("trial_directory", type=Path)
    args = parser.parse_args()
    folder = args.trial_directory
    data = (folder / "scene-events.jsonl").read_bytes()
    rows = [json.loads(line) for line in data.decode("utf-8").splitlines()]
    scene = json.loads((folder / "scene-verification.json").read_text())
    request = json.loads((folder / "mechanics-request.json").read_text())
    request_check = verify_request_events(request, rows)
    result = verify(rows, scene, request, request_check)
    result["logSha256"] = hashlib.sha256(data).hexdigest()
    result["sceneProbeSha256"] = scene.get("artifacts", {}).get("scene-probe.js")
    output = folder / "chatterbox-cover-verification.json"
    if output.exists():
        raise ValueError("Refusing to replace historical Chatterbox cover evidence")
    output.write_text(json.dumps(result, indent=2) + "\n")
    print(json.dumps(result))
    return 0 if result["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
