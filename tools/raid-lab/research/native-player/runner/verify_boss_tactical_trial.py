"""Strict receipt for one completed original-engine boss-tactical diagnostic.

This validates observed native effects of the current bounded policies. A PASS
does not establish all-boss tactical coverage, user-roster fidelity, parity, or
mechanics accuracy. A mechanic absent from the trial is NOT_EXERCISED.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import math
from pathlib import Path


def _one(rows: list[dict], status: str, errors: list[str]) -> dict | None:
    found = [row for row in rows if row.get("status") == status]
    if len(found) != 1:
        errors.append(f"{status}: expected exactly one row, got {len(found)}")
        return None
    return found[0]


def _int(value: object, minimum: int = 0) -> bool:
    return type(value) is int and value >= minimum


def _number(value: object) -> int | None:
    try:
        if isinstance(value, bool) or value is None:
            return None
        result = int(value)
        return result if str(value) == str(result) else None
    except (TypeError, ValueError):
        return None


def _summary(stop: dict | None, *names: str) -> dict:
    control = (stop or {}).get("tacticalControl") or {}
    for name in names:
        value = control.get(name)
        if isinstance(value, dict):
            return value
    return {}


def _qte(rows: list[dict], stop: dict | None) -> dict:
    errors = []
    events = [r for r in rows if r.get("status") == "original_tactical_transition"]
    qevents = [r for r in events if str(r.get("kind", "")).startswith("QuickTime")]
    decisions = [r for r in rows if r.get("status") == "original_reactive_qte_decision"]
    if not qevents and not decisions:
        return {"status": "NOT_EXERCISED", "errors": [], "observedEpisodes": 0}
    if any(r.get("policyVersion") != "reactive-qte-v1" for r in decisions):
        errors.append("QTE decision version differs from bound reactive policy")
    starts = [r for r in qevents if r.get("kind") == "QuickTimeStart"]
    preset_starts = [r for r in qevents if r.get("kind") == "QuickTimePresetStart"]
    ends = [r for r in qevents if r.get("kind") == "QuickTimePresetEnd"]
    hits = [r for r in qevents if r.get("kind") == "QuickTimeColliderHit"]
    selected = [r for r in decisions if r.get("action") == "aim_break"]
    results = [r for r in decisions if r.get("action") == "native_preset_result"]
    if not starts or not preset_starts or not ends:
        errors.append("original QTE start/preset-start/preset-end chain incomplete")
    if len([r for r in decisions if r.get("action") == "observed_qte"]) != len(starts):
        errors.append("policy QTE episode count differs from original starts")
    if len(results) != len(ends):
        errors.append("policy native preset result count differs from original events")
    for event in ends:
        identity = (event.get("tick"), event.get("presetInfoId"),
                    event.get("success"), event.get("end"))
        matches = [d for d in results if (isinstance(d.get("nativeEvent"), dict) and
                   (d["nativeEvent"].get("tick"), d["nativeEvent"].get("presetInfoId"),
                    d["nativeEvent"].get("success"), d["nativeEvent"].get("end")) == identity)]
        if len(matches) != 1 or event.get("success") is not True:
            errors.append(f"native preset outcome not successful or not correlated: {identity}")
    for index, start in enumerate(starts):
        end_tick = starts[index + 1].get("tick", 2**63) if index + 1 < len(starts) else 2**63
        matching_starts = [p for p in preset_starts if (
            p.get("monsterInfoId") == start.get("monsterInfoId") and
            _int(p.get("tick")) and start.get("tick", -1) <= p["tick"] < end_tick)]
        matching_ends = [p for p in ends if (p.get("end") is True and
            _int(p.get("tick")) and start.get("tick", -1) <= p["tick"] < end_tick)]
        if not matching_starts or not matching_ends:
            errors.append("original QTE episode lacks matching preset start/terminal end")
    snapshots = sorted((r for r in rows if
        r.get("status") == "original_tactical_observation_change" and _int(r.get("tick"))),
        key=lambda row: row["tick"])
    known = {}
    sampled_health = {}
    for snapshot in snapshots:
        for target in (snapshot.get("qte") or {}).get("targets", []):
            if not isinstance(target, dict):
                errors.append("malformed original QTE target snapshot"); continue
            entity, kind = target.get("entityId"), (target.get("colType") or {}).get("name")
            if not _int(entity, 1) or kind not in ("Break", "Counter", "Choice"):
                errors.append("unidentified original QTE target"); continue
            if entity in known and known[entity] != kind:
                errors.append("QTE target identity changed collider type")
            known[entity] = kind
            if kind in ("Counter", "Choice"):
                sampled_health.setdefault(entity, set()).add((target.get("health") or {}).get("hp"))
    for choice in selected:
        tick = choice.get("tick")
        previous = next((s for s in reversed(snapshots) if _int(tick) and s["tick"] <= tick), None)
        qte = (previous or {}).get("qte") or {}
        targets = [t for t in qte.get("targets", []) if
                   t.get("id") == choice.get("targetId") and
                   t.get("entityId") == choice.get("entityId")]
        target = targets[0] if len(targets) == 1 else {}
        if (previous is None or tick - previous["tick"] > 3 or
            qte.get("active") is not True or qte.get("supported") is not True or
            qte.get("groupId") != choice.get("groupId") or
            qte.get("currentIndex") != choice.get("presetIndex") or
            (target.get("colType") or {}).get("name") != "Break" or
            (target.get("state") or {}).get("name") != "Enable" or
            target.get("order") not in (0, qte.get("currentOrder"))):
            errors.append(f"selected Break was not enabled/order-allowed in native snapshot: {choice.get('entityId')}")
    hit_ids = {r.get("entityInfoId") for r in hits}
    selected_ids = {r.get("entityId") for r in selected}
    if not selected_ids or selected_ids != hit_ids:
        errors.append("selected Break set differs from original hit set")
    if any(known.get(entity) != "Break" for entity in hit_ids):
        errors.append("Counter/Choice/unknown QTE collider received original hit")
    if any(len(values) != 1 or None in values for values in sampled_health.values()):
        errors.append("sampled Counter/Choice health changed or became unreadable")
    threat_damage = [r for r in rows if (r.get("status") == "original_threat_event" and
                     r.get("kind") == "damage" and r.get("targetId") in sampled_health and
                     (_number(r.get("actualDamage")) or 0) > 0)]
    if threat_damage:
        errors.append("original positive damage reached sampled Counter/Choice target")
    summary = _summary(stop, "reactiveQte", "qtePolicy", "policy")
    if (summary.get("version") != "reactive-qte-v1" or summary.get("fault") is not None or
        summary.get("unsupported") != [] or summary.get("owned") is not False or
        summary.get("nativeTerminalSuccesses") != len(starts) or
        summary.get("nativeTerminalFailures") != 0):
        errors.append("reactive QTE policy summary absent, faulted, unsupported, or retains ownership")
    if any(d.get("action") in ("unsupported", "force_end", "synthetic_end") for d in decisions):
        errors.append("QTE unsupported state or policy-owned terminal event")
    return {"status": "FAIL" if errors else "PASS", "errors": errors,
        "observedEpisodes": len(starts), "originalPresetEnds": len(ends),
        "selectedBreakIds": sorted(selected_ids), "originalHitIds": sorted(hit_ids),
        "sampledUnsafeTargetIds": sorted(sampled_health),
        "safetyScope": "Original hit events and bounded target-health/damage observations only"}


def _squad_members(value: dict, shape: str) -> dict:
    if shape == "observation":
        items = (value or {}).get("characters")
        key = "id"
    else:
        items = (value or {}).get("squad")
        key = "entityId"
    if not isinstance(items, list) or len(items) != 5:
        return {}
    ids = [item.get(key) for item in items if isinstance(item, dict)]
    return {item[key]: item for item in items} if len(ids) == 5 and len(set(ids)) == 5 else {}


def _cover(rows: list[dict], stop: dict | None, wave_id: int | None) -> dict:
    errors = []
    decisions = [r for r in rows if r.get("status") == "native_cover_decision"]
    if not decisions:
        return {"status": "NOT_EXERCISED", "errors": [], "observedThreats": 0}
    if wave_id != 6302009:
        errors.append("cover evidence is only source-scoped to current Kraken wave 6302009")
    observed = [r for r in decisions if r.get("action") == "danger_observed"]
    entered = [r for r in decisions if r.get("action") == "entered"]
    released = [r for r in decisions if r.get("action") == "released"]
    resumed = [r for r in decisions if r.get("action") == "resume_readback"]
    if (not observed or not entered or len(entered) != len(released) or
        len(released) != len(resumed) or
        {r.get("key") for r in observed} !=
        {t.get("key") for row in entered for t in (row.get("threats") or [])}):
        errors.append("original threat and entered/released/resume sequences incomplete")
    if any(d.get("action") == "unsupported" for d in decisions):
        errors.append("cover encountered unsupported state")
    threat_events = [r for r in rows if r.get("status") == "original_threat_event"]
    for index, start in enumerate(entered):
        if index >= len(released) or index >= len(resumed):
            break
        end, resume = released[index], resumed[index]
        threats = start.get("threats") or []
        resolved = end.get("resolved") or []
        if (not threats or not resolved or
            {x.get("key") for x in threats} != {x.get("key") for x in resolved} or
            end.get("coverTick") != start.get("tick") or
            resume.get("releaseTick") != end.get("tick")):
            errors.append("cover threat identity/readback pairing failed"); continue
        for item in resolved:
            attack = item.get("attack") or {}
            condition = item.get("condition") or {}
            caster = attack.get("casterId")
            if (item.get("ruleId") != "kraken-intercept-shot02-followup" or
                attack.get("attackNodeId") != 230 or
                not _int(attack.get("tick")) or start.get("tick", -1) - attack["tick"] < 3 or
                item.get("sawSkill") is not True or item.get("sawCasting") is not True or
                (condition.get("condition") or {}).get("name") != "Idle" or
                not _int(condition.get("tick")) or
                not attack["tick"] <= condition["tick"] <= end.get("tick", -1)):
                errors.append("cover reaction, original cast, or per-caster Idle gate failed")
            ids = item.get("projectileIds")
            if not isinstance(ids, list) or not ids or len(set(ids)) != len(ids):
                errors.append("original projectile identity set absent or duplicated"); continue
            spawn = {r.get("projectileId"): r for r in threat_events if (
                     r.get("kind") == "spawn" and r.get("casterId") == caster and
                     attack.get("tick", -1) <= r.get("tick", -1) <= end.get("tick", -1))}
            despawn = {r.get("projectileId"): r for r in threat_events if (
                       r.get("kind") == "despawn" and r.get("tick", -1) <= end.get("tick", -1))}
            if not set(ids) <= (spawn.keys() & despawn.keys()):
                errors.append("per-caster original projectiles not all spawned/despawned before release")
        before, after = _squad_members(start.get("squadBefore"), "observation"), \
            _squad_members(end.get("squadAfter"), "observation")
        covered, release_state = _squad_members(start.get("nativeAfter"), "state"), \
            _squad_members(end.get("nativeBefore"), "state")
        if not before or before.keys() != after.keys() or not covered or covered.keys() != release_state.keys():
            errors.append("five native squad identity readbacks absent")
        else:
            if any(before[unit].get("health", {}).get("hp") != after[unit].get("health", {}).get("hp")
                   for unit in before):
                errors.append("squad HP fell during protected interval")
            if any(covered[unit].get("usedAmmoCount") != release_state[unit].get("usedAmmoCount") or
                   release_state[unit].get("stance") != 0 for unit in covered):
                errors.append("squad fired or left cover during protected interval")
            cover_ids = {before[unit].get("cover", {}).get("id") for unit in before}
            interval = [r for r in threat_events if start.get("tick", -1) <= r.get("tick", -1) <= end.get("tick", -1)]
            damaged_covers = {r.get("coverId") for r in interval if (
                r.get("kind") == "cover_damage" and (_number(r.get("damage")) or 0) > 0)}
            if damaged_covers != cover_ids:
                errors.append("positive original cover damage not observed for all five covers")
            if any(r.get("kind") == "damage" and r.get("targetType") == "Character" and
                   (_number(r.get("actualDamage")) or 0) > 0 for r in interval):
                errors.append("original positive damage reached character during cover")
        if (start.get("nativeAfter", {}).get("forcedCover") is not True or
            end.get("nativeBefore", {}).get("forcedCover") is not True or
            end.get("nativeAfter", {}).get("forcedCover") is not False or
            resume.get("firingResumed") is not True or
            resume.get("state", {}).get("autoAim") is not True or
            resume.get("state", {}).get("forcedCover") is not False):
            errors.append("native cover, release, or automatic resume readback failed")
        baseline = _squad_members(end.get("nativeBefore"), "state")
        resumed_squad = _squad_members(resume.get("state"), "state")
        if baseline and resumed_squad and baseline.keys() == resumed_squad.keys():
            if not any(resumed_squad[u].get("usedAmmoCount", 0) > baseline[u].get("usedAmmoCount", 0)
                       for u in baseline):
                errors.append("native ammo readbacks show no resumed fire")
        else:
            errors.append("resume squad ammo readback absent")
    summary = _summary(stop, "coverPolicy", "cover")
    if (summary.get("version") != "native-cover-v1" or summary.get("covered") is not False or
        summary.get("pending") != [] or summary.get("unsupported") != [] or
        summary.get("droppedLogs") != 0 or summary.get("completed") != len(observed) or
        summary.get("resumeChecks") != len(resumed)):
        errors.append("cover policy summary absent, unsupported, truncated, or retains a threat")
    return {"status": "FAIL" if errors else "PASS", "errors": errors,
        "observedThreats": len(observed), "entered": len(entered),
        "released": len(released), "resumed": len(resumed),
        "safetyScope": "Only exact Kraken node 230, bounded original threat logs and five-unit readbacks"}


def _break(rows: list[dict], stop: dict | None, wave_id: int | None) -> dict:
    """Mirror native break input, damage and interruption are separate claims."""
    errors: list[str] = []
    decisions = [r for r in rows if r.get("status") == "original_mirror_break_decision"]
    states = [r for r in rows if r.get("status") == "original_break_observation_change"]
    events = [r for r in rows if r.get("status") == "original_break_transition"]
    selected = [r for r in decisions if r.get("action") == "aim_live_break"]
    bound_indices = [i for i, r in enumerate(rows) if r.get("status") ==
                     "original_break_action_observation"]
    if bound_indices and (len(bound_indices) != len(selected) or any(
            i + 1 >= len(rows) or
            rows[i + 1].get("status") != "original_mirror_break_decision" or
            rows[i + 1].get("action") != "aim_live_break" for i in bound_indices)):
        errors.append("decision-bound original break observations are missing or unpaired")
    mirror_states = []
    for state_index, state in enumerate(rows):
        if state.get("status") not in ("original_break_observation_change",
                                        "original_break_action_observation"):
            continue
        if not _int(state.get("tick")):
            errors.append("break snapshot has no original tick")
            continue
        for monster in state.get("monsters") or []:
            if monster.get("tableId") == "4510010123":
                mirror_states.append((state_index, state["tick"], monster))
    if wave_id != 6302006 and not decisions and not mirror_states:
        return {"status": "NOT_EXERCISED", "errors": [],
                "targeting": "NOT_EXERCISED", "interruption": "NOT_EXERCISED",
                "sourceSkillAssociationVerified": False}
    if not decisions and not events and not mirror_states:
        return {"status": "NOT_EXERCISED", "errors": errors,
                "targeting": "NOT_EXERCISED", "interruption": "NOT_EXERCISED",
                "sourceSkillAssociationVerified": False}
    if wave_id != 6302006:
        errors.append("Mirror break evidence belongs only to wave 6302006")
    policy = _summary(stop, "breakPolicy")
    if (policy.get("version") != "mirror-live-break-candidate-v2" or
        policy.get("waveId") != 6302006 or
        policy.get("monsterTableId") != "4510010123" or
        policy.get("candidateSourceSkillIds") != [520669, 520676] or
        policy.get("expectedSourceSkillId") is not None or
        policy.get("sourceSkillLinkVerified") is not False or
        policy.get("nativeCancellationVerified") is not False or
        policy.get("aimpointHitVerified") is not False or
        policy.get("owned") is not False or policy.get("fault") is not None or
        policy.get("unsupported") != [] or
        policy.get("decisionsTruncated") is not False or
        policy.get("targetsSelected") != len(selected)):
        errors.append("Mirror break policy summary absent, faulted, truncated or retains input")
    if any(r.get("policyVersion") != "mirror-live-break-candidate-v2" for r in decisions):
        errors.append("Mirror break decision version differs from source-bound policy")
    if any(r.get("action") == "unsupported" for r in decisions):
        errors.append("Mirror break policy reached an unsupported state")
    observer = (stop or {}).get("breakableObservation") or {}
    control = (stop or {}).get("tacticalControl") or {}
    if (observer.get("eventTransitionsTruncated") is not False or
        observer.get("fault") is not None or
        observer.get("totalEvents") != observer.get("emittedEvents") or
        observer.get("emittedEvents") != len(events) or
        control.get("breakObservationTransitionsTruncated") is not False or
        control.get("breakTransitions") != len(states) or
        not _int(control.get("breakSamples"), 1)):
        errors.append("original break observation incomplete, faulted or truncated")
    starts = [(i, r) for i, r in enumerate(rows) if r.get("status") ==
              "original_break_transition" and r.get("kind") ==
              "MonsterBreakColliderActiveStart"]
    started = [(i, r) for i, r in enumerate(rows) if r.get("status") ==
               "original_break_transition" and r.get("kind") ==
               "MonsterBreakColliderActiveStarted"]
    hurts = [(i, r) for i, r in enumerate(rows) if r.get("status") ==
             "original_break_transition" and r.get("kind") ==
             "MonsterBreakColliderHurt"]
    all_break = [(i, r) for i, r in enumerate(rows) if r.get("status") ==
                 "original_break_transition" and r.get("kind") ==
                 "MonsterAllBreakCollider"]
    interruptions = [(i, r) for i, r in enumerate(rows) if r.get("status") ==
                     "original_break_transition" and r.get("kind") ==
                     "MonsterSkillInterruptionEvent"]
    def episode_at(owner: int, row_index: int):
        """Use the original event stream order, including same-tick rearming."""
        prior = [(i, r) for i, r in starts if r.get("ownerId") == owner and
                 i < row_index]
        if not prior:
            return None
        start_index, start = prior[-1]
        end_index = next((i for i, r in starts if r.get("ownerId") == owner and
                          i > start_index), len(rows))
        return start_index, end_index, start
    if not selected:
        errors.append("no Mirror break target selected under original input")
    if not starts or not started:
        errors.append("original Mirror break activation/start chain not observed")
    # A change log omits unchanged frames by design. Only a recent state before
    # each selection can establish eligibility. The original Hurt event and a
    # later lower native HP are both required; a policy aim alone proves neither.
    hit_matches = []
    used_hurts: set[int] = set()
    for choice in selected:
        tick, owner, collider = (choice.get("tick"), choice.get("ownerId"),
                                 choice.get("colliderId"))
        if (not _int(tick) or not _int(owner, 1) or not _int(collider) or
            choice.get("targetKey") != f"{owner}:{collider}" or
            choice.get("sourceSkillLinkVerified") is not False):
            errors.append("selected Mirror target lacks exact original identity")
            continue
        row_index = next(i for i, row in enumerate(rows) if row is choice)
        episode = episode_at(owner, row_index)
        if episode is None:
            errors.append(f"selected Mirror collider {collider} lacks original activation")
            continue
        start_index, end_index, start = episode
        bound = rows[row_index - 1] if row_index else {}
        if bound.get("status") == "original_break_action_observation":
            # This is the unchanged original observer snapshot passed into
            # policy.step, emitted immediately before its aim decision.
            bound_episode = next((e for e in bound.get("latestEpisodes") or []
                                  if e.get("ownerId") == owner), {})
            if (bound.get("decisionTick") != tick or
                bound.get("actorId") != choice.get("actorId") or
                bound.get("ownerId") != owner or
                bound.get("colliderId") != collider or
                bound.get("supported") is not True or
                bound_episode.get("startSequence") != start.get("sequence") or
                bound_episode.get("startTick") != start.get("tick") or
                bound_episode.get("started") is not True or
                not _int(bound_episode.get("startSequence"), 1)):
                errors.append(f"selected Mirror collider {collider} bound observation differs from original episode or decision")
                continue
            previous = next(((i, t, m) for i, t, m in reversed(mirror_states)
                             if i == row_index - 1 and m.get("entityId") == owner), None)
        else:
            previous = next(((i, t, m) for i, t, m in reversed(mirror_states)
                             if start_index < i < row_index and t <= tick and
                             rows[i].get("status") == "original_break_observation_change" and
                             m.get("entityId") == owner), None)
        if (previous is None or previous[0] <= start_index or
                previous[1] > tick or tick - previous[1] > 3):
            errors.append(f"selected Mirror collider {collider} lacks recent native state")
            continue
        current_monster = previous[2]
        current = [c for c in current_monster.get("colliders") or []
                   if c.get("colliderId") == collider]
        target = current[0] if len(current) == 1 else {}
        if bound.get("status") == "original_break_action_observation" and (
                target.get("name") != choice.get("name") or
                target.get("hp") != choice.get("hp") or
                target.get("maxHp") != choice.get("maxHp") or
                target.get("aimPointBasis") != choice.get("aimPointBasis")):
            errors.append(f"selected Mirror collider {collider} does not match bound native collider")
            continue
        hp = _number(target.get("hp"))
        if (current_monster.get("playing") is not True or
            current_monster.get("nativeIsAllBreak") is not False or
            target.get("type", {}).get("name") != "Break" or
            target.get("name") not in {"break_col_01", "break_col_02",
                                       "break_col_03", "break_col_04",
                                       "break_col_05", "break_col_06"} or
            target.get("enabled") is not True or
            target.get("unityLive") is not True or
            target.get("liveBreakTarget") is not True or
            target.get("aimPointBasis") != "UnityEngine.Collider.bounds.center" or
            hp is None or hp <= 0 or
            not isinstance(target.get("worldAimPoint"), list) or
            len(target["worldAimPoint"]) != 3 or
            any(type(x) not in (int, float) or not math.isfinite(x)
                for x in target["worldAimPoint"])):
            errors.append(f"selected Mirror collider {collider} was not eligible in live native state")
            continue
        if not any(start_index < i < row_index and e.get("ownerId") == owner
                   for i, e in started):
            errors.append(f"selected Mirror collider {collider} lacks original activation")
            continue
        lease = next((r for r in reversed(rows[start_index:row_index]) if
                      r.get("status") == "original_mirror_break_decision" and
                      r.get("action") in ("take_manual_control",
                                          "release_manual_control")), None)
        if (lease is None or lease.get("action") != "take_manual_control" or
                lease.get("actorId") != choice.get("actorId")):
            errors.append(f"selected Mirror collider {collider} lacks policy input lease")
            continue
        press_index = next((i for i in range(row_index + 1, end_index)
                            if rows[i].get("phase") == "mechanics_tactical_actions" and
                            rows[i].get("action") == "press"), None)
        hurt = next(((i, e) for i, e in hurts if i not in used_hurts and
                     press_index is not None and press_index < i < end_index and
                     e.get("ownerId") == owner and e.get("colliderId") == collider and
                     _int(e.get("tick")) and e["tick"] >= tick and
                     (_number(e.get("damage")) or 0) > 0), None)
        if (press_index is None or hurt is None or
                any(r.get("status") == "original_mirror_break_decision" and
                    r.get("action") in ("release_manual_control", "suspended",
                                        "take_manual_control")
                    for r in rows[row_index + 1:press_index])):
            errors.append(f"selected Mirror collider {collider} lacks subsequent original press/Hurt")
            continue
        hurt_index, hurt_event = hurt
        if any((r.get("status") == "original_mirror_break_decision" and
                r.get("action") in ("release_manual_control", "suspended",
                                    "take_manual_control")) or
               (r.get("phase") == "mechanics_tactical_actions" and
                r.get("action") in ("release", "set_auto_aim"))
               for r in rows[press_index + 1:hurt_index]):
            errors.append(f"selected Mirror collider {collider} lost input lease before native Hurt")
            continue
        used_hurts.add(hurt_index)
        later = [(_number(c.get("hp")), t) for i, t, m in mirror_states
                 if hurt_index < i < end_index and
                 m.get("entityId") == owner
                 for c in m.get("colliders") or [] if c.get("colliderId") == collider]
        if not any(value is not None and value < hp for value, _ in later):
            errors.append(f"selected Mirror collider {collider} lacks original HP decrement")
            continue
        hit_matches.append({"ownerId": owner, "colliderId": collider,
                            "episodeStartTick": start.get("tick"),
                            "episodeStartSequence": start.get("sequence"),
                            "episodeStartRowIndex": start_index,
                            "episodeEndRowIndex": end_index,
                            "hurtRowIndex": hurt_index,
                            "selectionTick": tick, "hurtTick": hurt_event["tick"],
                            "beforeHp": str(hp),
                            "afterHp": str(min(v for v, _ in later if v is not None))})
    # Counter/Choice health and original hurt events remain separate safety
    # checks. These sampled bounds cannot certify every unsampled native frame.
    types: dict[tuple[int, int, int], str] = {}
    unsafe_hp: dict[tuple[int, int, int], set[str]] = {}
    for state_index, _, monster in mirror_states:
        owner = monster.get("entityId")
        episode = episode_at(owner, state_index)
        if episode is None:
            if monster.get("playing") is True or monster.get("colliders"):
                errors.append("original Mirror active collider state predates activation")
            continue
        for item in monster.get("colliders") or []:
            key = (episode[0], owner, item.get("colliderId"))
            kind = (item.get("type") or {}).get("name")
            if key in types and types[key] != kind:
                errors.append("original break collider identity changed type")
            types[key] = kind
            if kind in ("Counter", "Choice"):
                unsafe_hp.setdefault(key, set()).add(item.get("hp"))
    if any(len(hps) != 1 or None in hps for hps in unsafe_hp.values()):
        errors.append("sampled Counter/Choice break-collider HP changed")
    mirror_owner_ids = {m.get("entityId") for _, _, m in mirror_states}
    if any((episode_at(h.get("ownerId"), i) is None or
            types.get((episode_at(h.get("ownerId"), i)[0],
                       h.get("ownerId"), h.get("colliderId"))) != "Break")
           for i, h in hurts if h.get("ownerId") in mirror_owner_ids):
        errors.append("original Hurt reached Counter/Choice or unknown break collider")
    targeting = "PASS" if selected and len(hit_matches) == len(selected) and not errors else "FAIL"
    # Original AllBreak and SkillInterruption report native outcomes, but the
    # Event payloads do not identify which of rows 520669/520676 was active.
    outcome = "OBSERVED_UNASSOCIATED" if any(
        any(a.get("ownerId") == h["ownerId"] and a.get("isBreak") is True and
            h["hurtRowIndex"] < ai < h["episodeEndRowIndex"] for ai, a in all_break) and
        any(e.get("ownerId") == h["ownerId"] and e.get("isInterrupt") is True and
            h["hurtRowIndex"] < ei < h["episodeEndRowIndex"]
            for ei, e in interruptions) for h in hit_matches) else "UNVERIFIED"
    if selected and outcome != "OBSERVED_UNASSOCIATED":
        errors.append("original AllBreak plus SkillInterruption outcome not both observed")
    return {"status": "FAIL" if errors else "PASS", "errors": errors,
        "targeting": targeting, "interruption": outcome,
        "selected": len(selected), "matchedOriginalHits": hit_matches,
        "originalAllBreakEvents": len(all_break),
        "originalSkillInterruptionEvents": len(interruptions),
        "sampledUnsafeColliderIds": sorted({key[2] for key in unsafe_hp}),
        "sourceSkillAssociationVerified": False,
        "safetyScope": "Sampled original Mirror collider HP and original Hurt events; no 520669/520676 attribution"}


def verify(rows: list[dict], scene: dict | None = None) -> dict:
    """Return a report; scene evidence is required for an overall PASS."""
    errors: list[str] = []
    if not isinstance(rows, list) or any(not isinstance(r, dict) for r in rows):
        return {"passed": False, "errors": ["events must be JSON objects"],
                "qte": {"status": "NOT_EXERCISED"}, "cover": {"status": "NOT_EXERCISED"},
                "break": {"status": "NOT_EXERCISED"}}
    mode = _one(rows, "native_control_mode_selected", errors)
    stop = _one(rows, "original_tick_driver_stopped", errors)
    terminal = _one(rows, "original_terminal_result", errors)
    if (not isinstance(scene, dict) or scene.get("complete_battle_executed") is not True or
        scene.get("errors") != []):
        errors.append("scene-verification complete/error-free evidence required")
    if (not mode or mode.get("controlMode") != "boss-tactical" or
        mode.get("policyVersion") != "boss-tactical-v1" or
        mode.get("observesNativeState") is not True or
        mode.get("issuesTacticalCommands") is not True):
        errors.append("boss-tactical original control mode binding absent")
    if not stop or stop.get("stage") != "original_battle_ticks":
        errors.append("original native tick driver completion absent")
    if (not terminal or terminal.get("originalResult") is not True or
        terminal.get("resultCaptured") is not True or
        terminal.get("completeBattle") is not True or
        not _int(terminal.get("advancedTicks"), 1) or
        not _int(_number(terminal.get("targetMaxHp")), 1) or
        not isinstance(terminal.get("rounds"), list) or not terminal["rounds"]):
        errors.append("completed nonzero original native result absent")
    transitions = [r for r in rows if r.get("status") == "original_tactical_transition"]
    threats = [r for r in rows if r.get("status") == "original_threat_event"]
    observation = (stop or {}).get("tacticalObservation") or {}
    threat = (stop or {}).get("threatObservation") or {}
    if (observation.get("transitionsTruncated") is not False or
        observation.get("fault") is not None or
        observation.get("total") != observation.get("emitted") or
        observation.get("emitted") != len(transitions)):
        errors.append("original QTE/event observer incomplete or truncated")
    if (threat.get("transitionsTruncated") is not False or
        threat.get("fault") is not None or threat.get("droppedLogs") != 0 or
        threat.get("emitted") != len(threats)):
        errors.append("original threat observer incomplete or truncated")
    control = (stop or {}).get("tacticalControl") or {}
    if (control.get("mode") != "boss-tactical" or
        control.get("policyVersion") != "boss-tactical-v1" or
        control.get("observationTransitionsTruncated") is not False or
        control.get("fault") is not None):
        errors.append("boss-tactical driver summary absent or faulted")
    qte_summary = _summary(stop, "policy")
    cover_summary = _summary(stop, "coverPolicy")
    if (qte_summary.get("version") != "reactive-qte-v1" or
        qte_summary.get("fault") is not None or qte_summary.get("unsupported") != [] or
        qte_summary.get("owned") is not False):
        errors.append("reactive QTE policy not cleanly released, including unexercised policy")
    if (cover_summary.get("version") != "native-cover-v1" or
        cover_summary.get("unsupported") != [] or cover_summary.get("droppedLogs") != 0 or
        cover_summary.get("covered") is not False or cover_summary.get("pending") != []):
        errors.append("cover policy unsupported, truncated, or unresolved at terminal")
    transporter = [r for r in rows if r.get("status") in
                   ("synthetic_kraken_transporter_prepared", "original_transporter_prepared",
                    "original_encounter_transporter_prepared")]
    wave_id = transporter[0].get("waveId") if len(transporter) == 1 else None
    if len(transporter) != 1 or not _int(wave_id, 1):
        errors.append("exactly one source-bound original transporter/wave identity required")
    if len(transporter) == 1 and transporter[0].get("status") == \
            "original_encounter_transporter_prepared":
        bound = transporter[0]
        request_sha = bound.get("requestSha256")
        if (not isinstance(request_sha, str) or len(request_sha) != 64 or
            any(c not in "0123456789abcdef" for c in request_sha.lower()) or
            not isinstance(bound.get("encounterProfileId"), str) or
            not bound["encounterProfileId"] or
            not isinstance(bound.get("roster"), list) or
            len(bound["roster"]) != 5 or
            bound.get("staticFieldInstalled") is not False or
            bound.get("battleStarted") is not False or
            bound.get("resultCaptured") is not False):
            errors.append("schema-2 encounter transporter lacks exact request/profile/roster readback")
        aim_rows = [r for r in rows if r.get("status") == "original_aim_state"]
        if (len(aim_rows) != 5 or
            not isinstance(bound.get("roster"), list) or
            any(not _int(code, 1) for code in bound["roster"]) or
            any(not _int(r.get("nameCode"), 1) or
                not _int(r.get("entityId"), 1) for r in aim_rows) or
            any(r.get("requestSha256") != request_sha for r in aim_rows) or
            sorted(r.get("nameCode") for r in aim_rows) !=
                sorted(bound.get("roster") or []) or
            len({r.get("entityId") for r in aim_rows}) != 5):
            errors.append("schema-2 original live actor/request identities differ from transporter")
        if wave_id == 6302006:
            if bound.get("encounterProfileId") != "anomaly-mirror-container":
                errors.append("Mirror transporter profile identity differs from current source")
            targets = [r for r in rows if r.get("status") == "original_current_wave_targets"]
            if (len(targets) != 1 or not isinstance(targets[0].get("targetIds"), list) or
                "4510010123" not in targets[0]["targetIds"]):
                errors.append("original Mirror wave target 4510010123 not read back")
    try:
        qte = _qte(rows, stop)
    except (KeyError, TypeError, ValueError, AttributeError, OverflowError) as exc:
        qte = {"status": "FAIL", "errors": [f"malformed QTE evidence: {exc}"]}
    try:
        cover = _cover(rows, stop, wave_id)
    except (KeyError, TypeError, ValueError, AttributeError, OverflowError) as exc:
        cover = {"status": "FAIL", "errors": [f"malformed cover evidence: {exc}"]}
    try:
        break_result = _break(rows, stop, wave_id)
    except (KeyError, TypeError, ValueError, AttributeError, OverflowError, StopIteration) as exc:
        break_result = {"status": "FAIL", "errors": [f"malformed break evidence: {exc}"],
                        "targeting": "FAIL", "interruption": "UNVERIFIED",
                        "sourceSkillAssociationVerified": False}
    errors.extend("QTE: " + error for error in qte["errors"])
    errors.extend("cover: " + error for error in cover["errors"])
    errors.extend("break: " + error for error in break_result["errors"])
    if wave_id == 6302006 and break_result["status"] == "NOT_EXERCISED":
        errors.append("Mirror break mechanic not exercised; native targeting/cancellation unverified")
    return {"schemaVersion": 1, "passed": not errors, "errors": errors,
        "nativeResult": {"advancedTicks": (terminal or {}).get("advancedTicks"),
            "targetMaxHp": (terminal or {}).get("targetMaxHp"),
            "originalResult": (terminal or {}).get("originalResult")},
        "qte": qte, "cover": cover, "break": break_result, "waveId": wave_id,
        "fullAccuracyVerified": False, "allBossTacticalCoverageVerified": False,
        "scope": "One source-bound native diagnostic; unexercised mechanics remain unverified"}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("trial_directory", type=Path)
    args = parser.parse_args()
    folder = args.trial_directory
    data = (folder / "scene-events.jsonl").read_bytes()
    scene_data = (folder / "scene-verification.json").read_bytes()
    rows = [json.loads(line) for line in data.decode("utf-8").splitlines()]
    scene = json.loads(scene_data)
    report = verify(rows, scene)
    report["evidence"] = {"sceneEventsSha256": hashlib.sha256(data).hexdigest(),
        "sceneVerificationSha256": hashlib.sha256(scene_data).hexdigest(),
        "stagedBundleSha256": (scene.get("artifacts") or {}).get("scene-probe.js")}
    output = folder / "boss-tactical-verification.json"
    with output.open("x", encoding="utf-8") as target:
        json.dump(report, target, indent=2, ensure_ascii=False)
        target.write("\n")
    print(json.dumps(report, ensure_ascii=False))
    return 0 if report["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
