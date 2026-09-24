"""Damage-argument target context for source-driven Anomaly encounters.

The calculator has one historical enemy sentinel (``__enemy__``).  Its damage
argument therefore combines attacker buffs with effects attached to the boss.
Anomaly encounters introduce independent damageable entities.  Their native
status does not inherit effects attached to the boss, so callers must replace
the two target-owned damage modifiers before calculating their damage.

Parts and ordinary BreakObject colliders belong to the monster and retain its
effects.  Destroyable projectiles and special-QTE colliders own separate status.
Adds retain only an ``all_enemies`` effect that activated while that add was
alive and could receive an AllMonster function. Ranked skill selectors use the
live enemy roster; physical area selectors accept a collider-query provider.
"""

from __future__ import annotations

import math
import json
from functools import lru_cache
from pathlib import Path
from typing import Any, Mapping


TARGET_DAMAGE_KEYS = ("enemy_def_down_pct", "received_dmg")
_INHERITS_BOSS_STATUS = frozenset(("boss", "part", "ordinary_break"))
_INDEPENDENT_STATUS = frozenset(("projectile", "special_qte"))
_TARGET_STAT_TO_KEY = {
    "def_pct": "enemy_def_down_pct",
    "received_dmg_pct": "received_dmg",
}

_ELEMENT_NAMES = {
    100001: "작열",
    200001: "수냉",
    300001: "풍압",
    400001: "전격",
    500001: "철갑",
}

_TARGET_PREFERENCE_DATA = Path(__file__).with_name("anomaly-target-preferences.json")
_NONE_TARGET_VALUES = frozenset(("Normal", "Last", "None"))
_PREFERENCE_VALUES = frozenset(("None", "IncludeNoneTargetLast", "IncludeNoneTargetNone"))


@lru_cache(maxsize=1)
def _native_target_preferences() -> Mapping[str, Any]:
    data = json.loads(_TARGET_PREFERENCE_DATA.read_text(encoding="utf-8"))
    if data.get("schema") != 1 or data.get("client_version") != "152.8.11":
        raise ValueError("unsupported installed target-preference metadata")
    return data


def _native_skill_row(effect: Mapping[str, Any], caster: str) -> Mapping[str, Any] | None:
    """Identify a direct CharacterSkill or exact nested skill invocation.

    Parsed effects retain their source slot but not their native function ID.
    A direct CharacterSkill root has one unambiguous condition for the slot.
    A StateEffect root can invoke several different CharacterSkills; it is
    used only when the caller supplies the exact ``native_skill_id``.
    """
    source = effect.get("source") or effect.get("effect_source")
    if not source:
        return None
    data = _native_target_preferences()
    direct = data["direct_skills"].get(caster, {}).get(source)
    supplied_id = effect.get("native_skill_id")
    if supplied_id is not None:
        if direct and direct["skill_id"] == supplied_id:
            return direct
        nested = data["nested_character_skills"].get(caster, {}).get(source, ())
        matched = [row for row in nested if row["skill_id"] == supplied_id]
        return matched[0] if len(matched) == 1 else None
    return direct


def native_skill_target_condition(effect: Mapping[str, Any], caster: str) -> str | None:
    """Return an authored CharacterSkill condition only for a proven skill."""
    row = _native_skill_row(effect, caster)
    return row["condition"] if row else None


def native_skill_range_geometry(effect: Mapping[str, Any], caster: str) -> dict[str, Any] | None:
    """Return authored base cast geometry for an identified area skill.

    The native targeting processor scales SkillValueData[2] by 0.5/100 for
    both InstantCircle and InstantArea. InstantCircle adds raw value slot 3
    divided by 100 as its forward capsule height. Dynamic
    StatInstantSkillRange buffs and physical collider intersection remain the
    caller's responsibility.
    """
    row = _native_skill_row(effect, caster)
    if not row or "base_cast_radius_m" not in row:
        return None
    return {key: row[key] for key in (
        "skill_id", "skill_type", "range_diameter_cm", "range_stat_id", "base_cast_radius_m",
        "circle_height_cm", "base_cast_height_m")
        if key in row}


def native_instant_circle_capsule(
    geometry: Mapping[str, Any], caster_position: Mapping[str, float] | tuple[float, float, float],
    *, adjusted_radius_m: float,
) -> dict[str, Any]:
    """Build the native OverlapCapsule shape from an explicit caster position.

    ``adjusted_radius_m`` must incorporate active StatInstantSkillRange 191;
    passing ``base_cast_radius_m`` models only a cast without that modifier.
    The forward axis is UnityEngine.Vector3.forward = (0, 0, 1), not a stage
    aspect or screen-space vector.
    """
    if geometry.get("skill_type") != "InstantCircle":
        raise ValueError("InstantCircle geometry required")
    if isinstance(caster_position, Mapping):
        x, y, z = (float(caster_position[axis]) for axis in ("x", "y", "z"))
    else:
        x, y, z = map(float, caster_position)
    radius = float(adjusted_radius_m)
    height = float(geometry["base_cast_height_m"])
    if not all(math.isfinite(value) for value in (x, y, z, radius, height)) \
            or radius < 0 or height < 0:
        raise ValueError("finite nonnegative capsule dimensions required")
    return {"endpoint_a": (x, y, z + radius),
            "endpoint_b": (x, y, z + radius + height),
            "radius_m": radius}


def native_skill_excluded_layers(effect: Mapping[str, Any], caster: str) -> tuple[int, ...]:
    """Return source-specific NKLayer exclusions for a proven skill.

    The Stigma Area path filters PlayerProjectile=8 and
    MonsterProjectile=11 from PlayerInteractiveLayers.
    """
    row = _native_skill_row(effect, caster)
    return tuple(row.get("excluded_nk_layers", ())) if row else ()


def _none_target_partition(entities: list[dict[str, Any]], condition: str | None) -> list[dict[str, Any]]:
    """Apply the native stable NoneTarget partition after preference ranking.

    Native GetTargetList ranks candidates first, then SortByNoneTarget (RVA
    0x6411190) partitions Monster.NoneTargetType. Unmapped parsed function
    selectors retain their old candidate roster rather than borrowing a
    CharacterSkill condition that may belong to another nested effect.
    """
    if condition not in _PREFERENCE_VALUES:
        return entities
    primary, deferred = [], []
    for entity in entities:
        flag = entity.get("none_target", "Normal")
        if flag not in _NONE_TARGET_VALUES:
            flag = "Normal"
        if flag == "None" and condition != "IncludeNoneTargetNone":
            continue
        if flag == "Last" and condition != "IncludeNoneTargetLast":
            deferred.append(entity)
        else:
            primary.append(entity)
    return primary + deferred


def _enemy_selector(target: Any) -> bool:
    if not isinstance(target, str):
        return False
    return target in {"enemy", "all_enemies", "target", "target_body", "same_target"} \
        or target.startswith(("enemies_", "same_target:"))


def _monster_row(runtime: Any, monster_id: Any) -> Mapping[str, Any] | None:
    return next((row for row in runtime.data.get("monsters", ())
                 if row.get("Id") == monster_id), None)


def all_monster_targetable(runtime: Any,
                           target: Mapping[str, Any] | None) -> bool:
    """Whether an enemy may receive an AllMonster function/damage route.

    The native AllMonster function predicate checks the monster's
    ``FunctionNoneTargetType``.  It is separate from ``NoneTargetType``, which
    controls automatic/skill targeting.  A direct hit on a NoAllMonster add is
    therefore still possible.
    """
    if not target or target.get("id") == "__boss__":
        return True
    monster_id = target.get("monster_id")
    monster = (_monster_row(runtime, monster_id)
               if monster_id is not None and getattr(runtime, "data", None)
               else None)
    return (target.get("Functionnonetarget") or
            (monster or {}).get("Functionnonetarget")) != "NoAllMonster"


def _element_name(monster: Mapping[str, Any]) -> str | None:
    ids = monster.get("ElementId", ())
    ident = ids[0] if isinstance(ids, list) and ids else ids
    try:
        return _ELEMENT_NAMES.get(int(ident))
    except (TypeError, ValueError):
        return None


def _enemy_entities(runtime: Any, caster: str | None = None) -> list[dict[str, Any]]:
    """Return alive native target candidates in stable spawn order."""
    monster = runtime.data["monster"]
    stat = runtime.stat(monster)
    max_hp = stat["LevelHp"] * monster["HpRatio"] / 10000
    base_def = stat["LevelDefence"] * monster["DefenceRatio"] / 10000
    bonus = 0.0
    for ident, (end, value) in getattr(runtime, "effects", {}).items():
        function = getattr(runtime, "functions", {}).get(ident, {})
        if end > runtime.time and function.get("FunctionType") == "StatDef":
            bonus += value / 10000
    multiplier = runtime.anomaly_hook("defence_multiplier", runtime.time)
    defence = base_def * (multiplier if multiplier is not None else 1 + bonus)
    rows = [{
        "id": "__boss__",
        "hp": max(0.0, max_hp - runtime.damage),
        "max_hp": max_hp,
        "attack": stat["LevelAttack"] * monster["AttackRatio"] / 10000,
        "defence": defence,
        "element": _element_name(monster),
        "position": getattr(getattr(runtime, "world", None), "coordinates", None),
        "spawned": float("-inf"),
        "none_target": monster.get("Nonetarget", "Normal"),
    }]
    for add in runtime.living_adds():
        owner = _monster_row(runtime, add.get("monster_id")) or {}
        owner_stat = runtime.stat(owner) if owner else {}
        rows.append({
            "id": str(add["id"]),
            "monster_id": add.get("monster_id"),
            "hp": float(add.get("hp", 0)),
            "max_hp": float(add.get("max_hp", add.get("hp", 0))),
            "attack": float(add.get("attack", owner_stat.get("LevelAttack", 0)
                                      * owner.get("AttackRatio", 10000) / 10000)),
            "defence": float(add.get("defence", owner_stat.get("LevelDefence", 0)
                                       * owner.get("DefenceRatio", 10000) / 10000)),
            "element": add.get("element", _element_name(owner)),
            "position": add.get("coordinates", add.get("position",
                (add.get("route_positions") or [None])[0])),
            "spawned": float(add.get("spawned", 0)),
            "none_target": add.get("Nonetarget", owner.get("Nonetarget", "Normal")),
        })
    if caster is not None and getattr(runtime, "bm", None) is not None:
        for entity in rows:
            modifiers = _snapshotted_modifiers(runtime, caster, entity["id"])
            entity["defence"] *= max(
                0.0, 1 + modifiers["enemy_def_down_pct"] / 100)
            entity["attack"] = enemy_attack_for_target(
                runtime, entity["attack"], entity["id"])
    return rows


def _count_suffix(selector: str, default: int = 1) -> int:
    try:
        return max(0, int(selector.rsplit(":", 1)[1]))
    except (IndexError, TypeError, ValueError):
        return default


def _named_effect_targets(runtime: Any, effect_name: str, now: float) -> list[str]:
    bm = getattr(runtime, "bm", None)
    # The charged shot retains recipients locked at its firing boundary even
    # when its on_attack notification clears the lock before the full-charge
    # damage effect is dispatched. BuffManager restores this context as soon
    # as that notification ends, so later shots cannot reuse the recipients.
    shot_targets = getattr(bm, "_notify_ctx", {}).get("shot_enemy_targets")
    if shot_targets is not None and effect_name in shot_targets:
        return list(shot_targets[effect_name])
    found: list[str] = []
    for active in getattr(bm, "_active", ()):
        if active.effect.get("name") != effect_name:
            continue
        for entity_id, window in getattr(active, "enemy_target_windows", {}).items():
            if float(window["activated_at"]) <= now < float(window["expires_at"]):
                found.append(entity_id)
    return list(dict.fromkeys(found))


def _distance(runtime: Any, caster: str, entity: Mapping[str, Any]) -> float:
    exact = getattr(runtime, "enemy_distance_to_caster", None)
    if exact is not None:
        return float(exact(caster, entity["id"]))
    position = entity.get("position")
    origin = getattr(runtime, "squad_coordinates", {}).get(caster)
    geometry = getattr(runtime, "projectile_mechanics", None)
    target_position = getattr(geometry, "_target_position", None)
    if origin is None and target_position is not None:
        origin = target_position(caster)[0]
    if isinstance(origin, (tuple, list)):
        origin = dict(zip(("x", "y", "z"), origin))
    if isinstance(position, (tuple, list)):
        position = dict(zip(("x", "y", "z"), position))
    if isinstance(position, Mapping) and isinstance(origin, Mapping):
        return math.sqrt(sum((float(position.get(axis, 0))
                              - float(origin.get(axis, 0))) ** 2
                             for axis in ("x", "y", "z")))
    raise ValueError(f"Missing geometry for enemy selector target {entity['id']}")


def _ranged_candidates(runtime: Any, effect: Mapping[str, Any], caster: str,
                       selector: str, entities: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Combine stage eligibility with a supplied native-shape collider test.

    Stage shooting-zone membership is only GetCandidateList eligibility. An
    area skill's InstantCircle/InstantArea cast has a separate collider test.
    Preserve the existing inclusive fallback when that physical provider is
    absent, and expose each unresolved selection in runtime diagnostics.
    """
    stage = getattr(runtime, "enemy_in_shooting_zone", None)
    physical = getattr(runtime, "enemy_in_skill_range", None)
    geometry = native_skill_range_geometry(effect, caster)
    if physical is None:
        diagnostics = getattr(runtime, "range_targeting_unresolved", None)
        if diagnostics is None:
            diagnostics = runtime.range_targeting_unresolved = {}
        key = f"{caster}:{effect.get('source') or effect.get('effect_source') or '?'}:{selector}"
        diagnostics[key] = diagnostics.get(key, 0) + 1
    return [entity for entity in entities
            if (stage is None or stage(caster, entity["id"]))
            and (physical is None or physical(caster, entity["id"], geometry))]


def select_enemy_effect_targets(runtime: Any, effect: Mapping[str, Any],
                                caster: str, now: float) -> list[str] | None:
    """Snapshot native enemy recipients for one effect activation.

    Native ``TargetingLogic.GetTargetList`` selects from the currently alive
    candidates at cast time.  This function mirrors its parsed selectors; the
    returned entity ids are stored on ``ActiveBuff`` and never retargeted just
    because a summon appears or an old recipient dies.
    """
    selector = effect.get("target", "")
    if not _enemy_selector(selector):
        return None
    entities = _enemy_entities(runtime, caster)
    if not entities:
        return []
    by_id = {entity["id"]: entity for entity in entities}
    all_ids = list(by_id)
    target_condition = native_skill_target_condition(effect, caster)

    if selector == "all_enemies":
        return [entity["id"] for entity in entities
                if all_monster_targetable(runtime, entity)]
    if selector == "enemy":
        return ["__boss__"] if "__boss__" in by_id else []
    if selector == "enemies_in_range":
        candidates = _ranged_candidates(runtime, effect, caster, selector,
                                        entities)
        return [entity["id"] for entity in _none_target_partition(candidates, target_condition)]
    if selector in ("target", "target_body", "same_target") or selector.startswith("enemies_target:"):
        current = getattr(runtime, "last_enemy_target_by_caster", {}).get(caster, "__boss__")
        return [current] if current in by_id else []
    if selector.startswith("same_target:"):
        return [entity_id for entity_id in _named_effect_targets(
            runtime, selector.split(":", 1)[1], now) if entity_id in by_id]
    if selector.startswith("enemies_with_buff:"):
        return [entity_id for entity_id in _named_effect_targets(
            runtime, selector.split(":", 1)[1], now) if entity_id in by_id]
    if selector.startswith("enemies_code:"):
        code = selector.split(":", 1)[1]
        candidates = [entity for entity in entities if entity["element"] == code]
        return [entity["id"] for entity in _none_target_partition(candidates, target_condition)]
    if selector.startswith("enemies_lowest_hp_code:"):
        _, code, count = selector.rsplit(":", 2)
        candidates = [entity for entity in entities if entity["element"] == code]
        candidates.sort(key=lambda entity: (entity["hp"], all_ids.index(entity["id"])))
        candidates = _none_target_partition(candidates, target_condition)
        return [entity["id"] for entity in candidates[:int(count)]]
    if selector.startswith("enemies_random"):
        count = _count_suffix(selector, len(entities))
        if target_condition in _PREFERENCE_VALUES:
            # Native preference ordering (including Random) precedes the
            # NoneTarget partition; sample the full roster before truncation.
            ordered = runtime.rng.sample(entities, len(entities))
            ordered = _none_target_partition(ordered, target_condition)
            return [entity["id"] for entity in ordered[:count]]
        return [entity["id"] for entity in runtime.rng.sample(
            entities, min(count, len(entities)))]

    count = _count_suffix(selector)
    if selector.startswith("enemies_nearest"):
        candidates = (_ranged_candidates(runtime, effect, caster, selector, entities)
                      if selector.startswith("enemies_nearest_in_range") else entities)
        ordered = sorted(candidates, key=lambda entity: (
            _distance(runtime, caster, entity), all_ids.index(entity["id"])))
    elif selector.startswith("enemies_top_atk:"):
        ordered = sorted(entities, key=lambda entity: (
            -entity["attack"], all_ids.index(entity["id"])))
    elif selector.startswith("enemies_top_def:"):
        ordered = sorted(entities, key=lambda entity: (
            -entity["defence"], all_ids.index(entity["id"])))
    elif selector.startswith("enemies_lowest_def:"):
        ordered = sorted(entities, key=lambda entity: (
            entity["defence"], all_ids.index(entity["id"])))
    elif selector.startswith("enemies_top_hp:"):
        ordered = sorted(entities, key=lambda entity: (
            -entity["hp"], all_ids.index(entity["id"])))
    elif selector.startswith("enemies_lowest_hp:"):
        ordered = sorted(entities, key=lambda entity: (
            entity["hp"], all_ids.index(entity["id"])))
    else:
        raise ValueError(f"Unsupported native enemy selector: {selector}")
    ordered = _none_target_partition(ordered, target_condition)
    return [entity["id"] for entity in ordered[:count]]


def direct_skill_enemy_targets(runtime: Any, caster: str,
                               hit_type: Mapping[str, Any]) -> list[str] | None:
    """Resolve non-normal skill recipients that the common body path omits.

    ``None`` means the established body/all-parts/all-enemy/split route owns the
    hit.  A list means the caller must route one physical result to each entity
    id.  Periodic damage reuses the ActiveBuff application snapshot instead of
    selecting a new ranked/random target on every tick.
    """
    if hit_type.get("is_normal_atk") or hit_type.get("is_weapon_mode_skill"):
        return None
    selector = hit_type.get("effect_target")
    if not _enemy_selector(selector):
        return None
    effect_name = hit_type.get("effect_name") or hit_type.get("skill_name")
    now = float(getattr(runtime, "time", 0.0))

    def remember(selected: list[str]) -> None:
        if not effect_name:
            return
        remembered = getattr(runtime, "last_skill_targets_by_effect", None)
        if remembered is None:
            remembered = runtime.last_skill_targets_by_effect = {}
        remembered[(caster, effect_name)] = list(selected)

    if hit_type.get("is_dot") and effect_name:
        bm = getattr(runtime, "bm", None)
        for active in getattr(bm, "_active", ()):
            if active.caster != caster or active.effect.get("name") != effect_name:
                continue
            selected = [
                entity_id for entity_id, window
                in getattr(active, "enemy_target_windows", {}).items()
                if float(window["activated_at"]) <= now < float(window["expires_at"])
            ]
            remember(selected)
            return selected
        return []

    # These authored shapes already have dedicated damage routes.  Record the
    # owning enemy entities so a paired same_target effect can reuse them.
    if hit_type.get("hits_parts"):
        remember(["__boss__"])
        return None
    if selector == "all_enemies" and not hit_type.get("is_split"):
        selected = [entity["id"] for entity in _enemy_entities(runtime, caster)
                    if all_monster_targetable(runtime, entity)]
        remember(selected)
        return None

    if isinstance(selector, str) and selector.startswith("same_target:"):
        referenced = selector.split(":", 1)[1]
        remembered = getattr(runtime, "last_skill_targets_by_effect", {}).get(
            (caster, referenced))
        if remembered is not None:
            alive = {entity["id"] for entity in _enemy_entities(runtime, caster)}
            return [entity_id for entity_id in remembered if entity_id in alive]

    selected = select_enemy_effect_targets(
        runtime, {"target": selector,
                  "source": hit_type.get("effect_source"),
                  "native_skill_id": hit_type.get("native_skill_id")},
        caster, now)
    remember(list(selected or ()))
    return selected


def _target_spawned_at(target: Mapping[str, Any] | None) -> float:
    if not target:
        return float("inf")
    return float(target.get("spawned", target.get("spawned_at", float("inf"))))


def _all_enemy_add_modifiers(runtime: Any, caster: str,
                             target: Mapping[str, Any] | None) -> dict[str, float]:
    """Return target-side modifiers known to include this particular add.

    ActiveBuff records retain both their activation time and original parsed
    target selector.  This is enough to prove membership for exact
    ``all_enemies`` effects.  It is not enough to reconstruct range, random or
    ranked selectors, so those effects intentionally do not migrate from the
    boss sentinel.
    """
    result = {key: 0.0 for key in TARGET_DAMAGE_KEYS}
    if not all_monster_targetable(runtime, target):
        return result
    bm = getattr(runtime, "bm", None)
    if bm is None:
        return result
    now = float(getattr(runtime, "time", 0.0))
    spawned = _target_spawned_at(target)
    for active in getattr(bm, "_active", ()):
        effect = getattr(active, "effect", {})
        key = _TARGET_STAT_TO_KEY.get(effect.get("stat"))
        if key is None or effect.get("target") != "all_enemies":
            continue
        if float(getattr(active, "activated_at", float("-inf"))) + 1e-9 < spawned:
            continue
        if now >= float(getattr(active, "expires_at", float("inf"))):
            continue
        targets = getattr(active, "target_chars", None)
        if targets is not None and "__enemy__" not in targets:
            continue
        if getattr(active, "has_runtime_conditions", False):
            conditions = effect.get("trigger", {}).get("condition", ())
            checker = getattr(bm, "_runtime_condition_ok", None)
            if checker is None or not checker(
                    conditions, active.caster, caster, "__enemy__", now):
                continue
        value_getter = getattr(bm, "_get_value", None)
        if value_getter is None:
            continue
        per_char = getattr(active, "per_char_stacks", None) or {}
        value = value_getter(
            # This value belongs to the enemy recipient, not the attacking
            # character.  Enemy-target stacks use the sentinel recipient key.
            effect, active, "__enemy__", stack_override=per_char.get("__enemy__")
        )
        if value is not None:
            result[key] += float(value)
    return result


def _snapshotted_modifiers(runtime: Any, caster: str,
                           entity_id: str) -> dict[str, float]:
    result = {key: 0.0 for key in TARGET_DAMAGE_KEYS}
    bm = getattr(runtime, "bm", None)
    if bm is None:
        return result
    now = float(getattr(runtime, "time", 0.0))
    stamp = (now, getattr(bm, "_cache_version", 0))
    if getattr(runtime, "_enemy_modifier_cache_stamp", None) != stamp:
        runtime._enemy_modifier_cache_stamp = stamp
        runtime._enemy_modifier_cache = {}
    cache = runtime._enemy_modifier_cache
    cache_key = (caster, entity_id)
    if cache_key in cache:
        return dict(cache[cache_key])
    for active in getattr(bm, "_active", ()):
        effect = getattr(active, "effect", {})
        key = _TARGET_STAT_TO_KEY.get(effect.get("stat"))
        if key is None:
            continue
        window = getattr(active, "enemy_target_windows", {}).get(entity_id)
        if window is None or not (
                float(window["activated_at"]) <= now < float(window["expires_at"])):
            continue
        if getattr(active, "has_runtime_conditions", False):
            conditions = effect.get("trigger", {}).get("condition", ())
            checker = getattr(bm, "_runtime_condition_ok", None)
            if checker is None or not checker(
                    conditions, active.caster, caster, "__enemy__", now):
                continue
        value_getter = getattr(bm, "_get_value", None)
        if value_getter is None:
            continue
        value = value_getter(effect, active, "__enemy__",
                             stack_override=window.get("stack"))
        if value is not None:
            result[key] += float(value)
    cache[cache_key] = dict(result)
    return result


def enemy_attack_for_target(runtime: Any, base_attack: float,
                            entity_id: str) -> float:
    """Apply only ATK modifiers snapshotted onto the attacking enemy.

    This is the incoming-damage counterpart to ``damage_args_for_target``.
    A boss-only ATK debuff must not lower a summon with the same monster row,
    while an all-enemy application made after the summon spawned must affect it.
    """
    bm = getattr(runtime, "bm", None)
    if bm is None:
        return max(0.0, float(base_attack))
    now = float(getattr(runtime, "time", 0.0))
    stamp = (now, getattr(bm, "_cache_version", 0))
    if getattr(runtime, "_enemy_attack_cache_stamp", None) != stamp:
        runtime._enemy_attack_cache_stamp = stamp
        runtime._enemy_attack_cache = {}
    cache = runtime._enemy_attack_cache
    cache_key = (str(entity_id), float(base_attack))
    if cache_key in cache:
        return cache[cache_key]
    percent = 0.0
    flat = 0.0
    for active in getattr(bm, "_active", ()):
        window = getattr(active, "enemy_target_windows", {}).get(str(entity_id))
        if window is None or not (
                float(window["activated_at"]) <= now < float(window["expires_at"])):
            continue
        effect = active.effect
        stat = effect.get("stat")
        if stat not in ("atk_pct", "atk_caster_based_pct"):
            continue
        if getattr(active, "has_runtime_conditions", False):
            conditions = effect.get("trigger", {}).get("condition", ())
            if not bm._runtime_condition_ok(
                    conditions, active.caster, active.caster, "__enemy__", now):
                continue
        value = bm._get_value(effect, active, active.caster,
                              stack_override=window.get("stack")) or 0
        if stat == "atk_pct":
            percent += float(value)
        else:
            caster_atk = bm.state.get("base_stats", {}).get(
                active.caster, {}).get("atk", 0)
            flat += float(caster_atk) * float(value) / 100
    result = max(0.0, float(base_attack) * (1 + percent / 100) + flat)
    cache[cache_key] = result
    return result


def damage_args_for_target(args: Mapping[str, Any], caster: str,
                           target_kind: str, runtime: Any,
                           target: Mapping[str, Any] | None = None) -> dict[str, Any]:
    """Copy calculator arguments and apply the target's own debuff context.

    ``target_kind`` is one of ``boss``, ``part``, ``ordinary_break``, ``add``,
    ``projectile`` or ``special_qte``.  Unknown kinds raise instead of silently
    inheriting boss effects.
    """
    if target_kind not in _INDEPENDENT_STATUS and target_kind != "add":
        if target_kind not in _INHERITS_BOSS_STATUS:
            raise ValueError(f"Unknown Anomaly damage target kind: {target_kind}")

    out = dict(args)
    buffs = dict(args.get("buffs", {}))
    if target_kind in _INDEPENDENT_STATUS:
        modifiers = {key: 0.0 for key in TARGET_DAMAGE_KEYS}
    elif callable(getattr(runtime, "select_enemy_effect_targets", None)):
        entity_id = (str(target["id"]) if target_kind == "add" and target
                     else "__boss__")
        modifiers = _snapshotted_modifiers(runtime, caster, entity_id)
    elif target_kind in _INHERITS_BOSS_STATUS:
        return dict(args)
    else:
        modifiers = _all_enemy_add_modifiers(runtime, caster, target)
    for key in TARGET_DAMAGE_KEYS:
        buffs[key] = modifiers[key]
    out["buffs"] = buffs
    return out
