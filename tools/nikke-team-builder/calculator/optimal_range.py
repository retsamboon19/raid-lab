"""Distance-aware optimal range for Ade : Agent Bunny.

The native SR band (45–100 m) comes from roledata bonusrange_min/max. The
near-boundary reduction is an approximation: the client formula for her
``optimal_range_min`` buffs has not been recovered.
"""

from __future__ import annotations

import math
from collections.abc import Mapping

ADE = "에이드 : 에이전트 바니"


def _position(value):
    if isinstance(value, Mapping):
        return tuple(float(value[axis]) for axis in ("x", "y", "z"))
    if isinstance(value, (tuple, list)) and len(value) == 3:
        return tuple(float(x) for x in value)
    return None


def _distance(enemy: dict, runtime, caster: str):
    explicit = enemy.get("distance_m")
    if explicit is not None:
        distance = float(explicit)
        return distance if math.isfinite(distance) and distance >= 0 else None
    if runtime is None:
        return None
    world = getattr(runtime, "world", None)
    target = _position(getattr(world, "coordinates", None))
    origin = _position((getattr(runtime, "squad_coordinates", None) or {}).get(caster))
    if target is None or origin is None:
        return None
    distance = math.dist(origin, target)
    return distance if math.isfinite(distance) else None


def is_optimal_range(caster: str, weapon_type: str, enemy: dict, bm, t: float) -> bool:
    """Use explicit weapon override, then Ade's known range if distance exists."""
    weapons = enemy.get("optimal_range_weapons") or []
    if weapons:
        return weapon_type in weapons
    if caster != ADE or weapon_type != "SR":
        return False
    distance = _distance(enemy, bm.state.get("encounter_runtime"), caster)
    if distance is None:
        return False

    reduction = 0.0
    for ab in bm._active:
        if ab.effect.get("stat") != "optimal_range_min" or t >= ab.expires_at:
            continue
        targets = ab.target_chars if ab.target_chars is not None else bm._resolve_lazy(ab)
        if caster not in targets:
            continue
        stack = ab.per_char_stacks.get(caster) if ab.per_char_stacks else None
        value = bm._get_value(ab.effect, ab, caster, stack_override=stack)
        if value is not None:
            reduction += value
    near = 45.0 * max(0.0, 1.0 - reduction / 100.0)
    return near <= distance <= 100.0
