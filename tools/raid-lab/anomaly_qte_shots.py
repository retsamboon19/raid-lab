"""Calibrated physical contacts for normal Anomaly QTE shots.

The current installed base-weapon rows supply pellet and explosion geometry.
The UI reticle basis and default plane/origin were measured in an Indivilia
client capture; they are a calibrated pose, not an exact animated camera.
Callers may override the ray, origin, and plane with observed values. One call
represents one pellet; damage, counter-failure, and HP remain runtime-owned.
"""

from functools import lru_cache
import json
import math
from pathlib import Path
from typing import Any, Mapping

from anomaly_qte_geometry import (
    CALIBRATED_UI_PLANE_POINT,
    aimed_rays,
    native_shot_offsets,
    ray_hits,
    sphere_hits,
)


BASE_WEAPON_DATA = Path(__file__).with_name("anomaly-weapon-geometry.json")
# Median of 368 initial Indivilia native GetRays origins around the active
# player aim. Other actors and moving poses differed; this is only a fallback.
CALIBRATED_AIM_ORIGIN = (0.07, -0.710, -0.292)


@lru_cache(maxsize=1)
def _weapon_data() -> dict[str, Any]:
    data = json.loads(BASE_WEAPON_DATA.read_text(encoding="utf-8"))
    if data.get("schema") != 1 or data.get("explosion_range_scale") != 0.01:
        raise ValueError("unsupported current base-weapon geometry schema")
    return data


def base_weapon_parameters(unit_name: str) -> dict[str, Any] | None:
    """Get installed version-152 base-weapon geometry by exact unit name.

    Returns a copy with ``explosion_radius`` in world units. A temporary
    weapon mode must supply its own CharacterShot row; this lookup cannot
    describe it.
    """
    row = _weapon_data()["units"].get(unit_name)
    if row is None:
        return None
    result = dict(row)
    result["explosion_radius"] = float(row["SpotExplosionRange"]) * 0.01
    return result


def temporary_weapon_parameters(unit_name: str, weapon: str,
                                shot_id: int | None = None) -> dict[str, Any] | None:
    """Resolve an unambiguous installed replacement weapon for this character.

    Multiple native modes with different geometry cannot be selected by weapon
    class alone. An observed CharacterShot ID resolves those cases.
    """
    del weapon  # Parsed damage categories need not equal the native shot class.
    rows = [row for row in _weapon_data().get("temporary_weapons", {}).get(unit_name, ())
            if shot_id is None or row["shot_id"] == shot_id]
    if not rows:
        return None
    # Some modes change damage only. Their shared geometry is sufficient, but
    # never choose between modes with different physical shot parameters.
    geometry = lambda row: {k: v for k, v in row.items()
                            if k not in ("shot_id", "skill_groups", "resource_names")}
    if any(geometry(row) != geometry(rows[0]) for row in rows[1:]):
        return None
    result = dict(rows[0])
    if len(rows) > 1:
        result["equivalent_shot_ids"] = [row["shot_id"] for row in rows]
        result.pop("shot_id")
    result["explosion_radius"] = float(result["SpotExplosionRange"]) * 0.01
    return result


def _point(value) -> tuple[float, float, float]:
    point = tuple(float(item) for item in value)
    if len(point) != 3 or not all(math.isfinite(item) for item in point):
        raise ValueError("QTE shot requires finite 3D point")
    return point


def _unit(value) -> tuple[float, float, float]:
    direction = _point(value)
    length = math.sqrt(sum(item * item for item in direction))
    if length == 0:
        raise ValueError("QTE ray direction cannot be zero")
    return tuple(item / length for item in direction)


def qte_shot_contacts(runtime, caster: str, weapon: str,
                      hit_type: Mapping[str, Any], target: Mapping[str, Any],
                      args: Mapping[str, Any]) -> dict[str, Any] | None:
    """Resolve one normal pellet against current active QTE colliders.

    ``None`` means missing or unsupported physical inputs; the runtime may
    use its established target route. A returned dictionary (including empty
    contacts) is a resolved physical shot. Direct first contact is followed
    by distinct RL explosion overlaps centered on that ray impact point.

    ``hit_type['qte_ray']`` or ``runtime.qte_ray_overrides[caster]`` may supply
    an observed ``{'origin': XYZ, 'direction': XYZ}`` ray. Otherwise native
    ``accuracy_circle`` and ``pellet_index`` drive the installed base weapon's
    shot pattern. ``qte_origin`` and ``qte_ui_plane_point`` override the
    calibrated UI pose. Temporary weapons use an unambiguous installed row;
    ``native_shot_id`` disambiguates multiple modes, and
    ``native_weapon_geometry`` supplies an explicit observed row.
    """
    del args  # Geometry does not depend on damage buffs.
    if not (hit_type.get("is_normal_atk") or hit_type.get("is_weapon_mode_skill")):
        return None
    boxes = tuple(runtime.active_qte_geometry())
    if not boxes or target is None:
        return None
    by_id = {box.collider_index: box for box in boxes}
    aim_box = by_id.get(target.get("id"))
    if aim_box is None:
        return None

    explicit_weapon = hit_type.get("native_weapon_geometry")
    if explicit_weapon is not None:
        parameters = dict(explicit_weapon)
        calibration = "explicit_weapon_geometry"
    elif hit_type.get("is_weapon_mode_skill") or hit_type.get("weapon_changed"):
        parameters = temporary_weapon_parameters(caster, weapon, hit_type.get("native_shot_id"))
        calibration = "installed_temporary_weapon_calibrated_ui_pose"
    else:
        parameters = base_weapon_parameters(caster)
        calibration = "installed_base_weapon"
    if parameters is None:
        return None
    # MultiTarget has its own native target enumeration; one aimed ray would
    # silently discard its extra recipients and cannot represent that mode.
    if parameters.get("FireType") == "MultiTarget":
        return None
    if calibration == "installed_base_weapon" and parameters.get("WeaponType") != weapon:
        return None

    override = hit_type.get("qte_ray")
    if override is None:
        override = getattr(runtime, "qte_ray_overrides", {}).get(caster)
    if override is not None:
        origin = _point(override["origin"])
        direction = _unit(override["direction"])
        calibration = "observed_ray"
    else:
        if "accuracy_circle" not in hit_type:
            return None
        shot_count = int(parameters["ShotCount"])
        muzzle_count = int(parameters.get("MuzzleCount", 1))
        center_count = int(parameters.get("CenterShotCount", 0))
        pellet_index = int(hit_type.get("pellet_index", 0))
        pellet_count = int(hit_type.get("pellet_count", shot_count * muzzle_count))
        if (shot_count < 1 or muzzle_count < 1 or center_count < 0
                or center_count > shot_count or pellet_count < 1
                or pellet_index < 0 or pellet_index >= pellet_count):
            return None
        # The timeline index is already within one effective volley. Do not
        # repeat native center pellets when a pellet-count buff extends it.
        center = pellet_index < min(center_count, pellet_count)
        offset = native_shot_offsets(1, int(center),
                                     hit_type["accuracy_circle"], runtime.rng)[0]
        origin = _point(hit_type.get("qte_origin", CALIBRATED_AIM_ORIGIN))
        plane = _point(hit_type.get("qte_ui_plane_point", CALIBRATED_UI_PLANE_POINT))
        _, direction = aimed_rays(origin, aim_box.center, (offset,), plane)[0]
        if calibration == "installed_base_weapon":
            calibration = "calibrated_ui_pose"

    hits = ray_hits(boxes, origin, direction)
    path_model = ("instant_ray" if parameters.get("FireType") == "Instant"
                  else "projectile_ray_approximation")
    if not hits:
        return dict(contacts=[], origin=origin, direction=direction,
                    impact_point=None, calibration=calibration,
                    path_model=path_model)
    first_id, distance = hits[0]
    impact = tuple(origin[axis] + direction[axis] * distance for axis in range(3))
    contacts = [first_id]
    radius = float(parameters.get("explosion_radius",
                                  float(parameters.get("SpotExplosionRange", 0)) * 0.01))
    if radius > 0 and parameters.get("WeaponType") == "RL":
        contacts.extend(index for index in sphere_hits(boxes, impact, radius)
                        if index != first_id)
    return dict(contacts=contacts, origin=origin, direction=direction,
                impact_point=impact, calibration=calibration,
                path_model=path_model)
