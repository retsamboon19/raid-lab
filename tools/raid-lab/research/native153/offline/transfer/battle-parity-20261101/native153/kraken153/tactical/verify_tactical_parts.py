"""Unchanged bounded QTE/cover validators copied from historical source, not native153 proof."""
# Original source SHA256 ec6ec001c17674acc0300e66af874f4eb8f9daca41b672af761c463d8e0dede7

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
