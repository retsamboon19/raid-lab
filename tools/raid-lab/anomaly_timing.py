"""Source-backed timing helpers for Anomaly Interception behavior trees.

The client drives phase actions and movement to completion callbacks.  This
module exposes those rules and the extracted timing/point data without turning
missing client state (for example combat-zone membership) into guessed values.
"""
from __future__ import annotations

import json
import math
import re
from pathlib import Path


_DATA_PATH = Path(__file__).with_name("anomaly-timing-data.json")
DATA = json.loads(_DATA_PATH.read_text(encoding="utf-8"))
_CLONE_SUFFIX = re.compile(r"(?:\(Clone\))+$")
_EPSILON = 1e-9


def marker_kind(marker_type: str) -> str:
    """Return a marker's stable kind, removing any repeated Unity clone suffix."""
    return _CLONE_SUFFIX.sub("", marker_type).rsplit("/", 1)[-1]


def timeline_schedule(timeline: dict, casting_seconds: float) -> dict:
    """Return native-equivalent attack offsets and completion time.

    MonsterTimeLineControl treats CastingTime as the amount of time spent in
    the half-open [LoopStart, LoopEnd) region.  It rewinds the director and
    removes already-fired attack markers in that region on every iteration.
    Markers after LoopEnd are shifted by effective casting time minus the
    authored loop length. The caller supplies the constructed skill's casting
    time, including its casting-shot effect. InitSkill's zero-value fallback
    concerns TimelineLoopStartTime, a separate field, not CastingTime.
    """
    markers = timeline.get("markers", ())
    starts = [float(m["time"]) for m in markers if marker_kind(m["type"]) == "LoopStart"]
    ends = [float(m["time"]) for m in markers if marker_kind(m["type"]) == "LoopEnd"]
    attacks = [m for m in markers if marker_kind(m["type"]) == "Attack"]
    duration = float(timeline["duration"])
    if not starts or not ends or ends[0] <= starts[0]:
        events = [{**m, "time": float(m["time"])} for m in attacks]
        impact_times = [event["time"] for event in events]
        return {
            "impacts": impact_times,
            "impact_events": events,
            "end": max([duration, *impact_times]),
            "loop": None,
        }

    start, end = starts[0], ends[0]
    loop_length = end - start
    table_casting_seconds = max(0.0, float(casting_seconds))
    effective_casting_seconds = table_casting_seconds
    shift = effective_casting_seconds - loop_length
    impact_events = [
        {**marker, "time": float(marker["time"])}
        for marker in attacks if float(marker["time"]) < start
    ]

    # The native fired-marker predicate is exactly start <= time < end.
    for marker in (m for m in attacks if start <= float(m["time"]) < end):
        attack = float(marker["time"])
        relative = attack - start
        cycle = 0
        while relative + cycle * loop_length < effective_casting_seconds - _EPSILON:
            impact_events.append({
                **marker,
                "time": start + relative + cycle * loop_length,
                "loop_iteration": cycle,
            })
            cycle += 1

    impact_events.extend(
        {**marker, "time": float(marker["time"]) + shift}
        for marker in attacks if float(marker["time"]) >= end
    )
    impact_events.sort(key=lambda event: (event["time"], event.get("target", 0)))
    impacts = [event["time"] for event in impact_events]
    adjusted_end = duration + shift
    return {
        "impacts": impacts,
        "impact_events": impact_events,
        "end": max([adjusted_end, *impacts]),
        "loop": {
            "start": start,
            "end": end,
            "authored_seconds": loop_length,
            "table_casting_seconds": table_casting_seconds,
            "casting_seconds": effective_casting_seconds,
            "shift_seconds": shift,
        },
    }


def profile_timeline_schedule(profile_key: str, shot: int) -> dict:
    row = DATA["profiles"][profile_key]["timelines"][str(shot)]
    return timeline_schedule(row, row["casting_seconds"])


# Same original clip-marker windows as the native qte-parts-cover controller.
# Values are director times, not battle-clock deadlines. Mirror has no defensive
# cover window; its gray-QTE input isolation is a separate policy.
_NATIVE_COVER_WINDOWS = {
    'anomaly-ultra': {510634: (7/3, 58/15), 510635: (17/6, 88/15)},
    'anomaly-harvester': {510131: (149/30, 383/60)},
    'anomaly-indivilia': {531463: (4., 4.3), 531464: (3., 217/60),
                           531466: (16/3, 86/15), 531470: (2.2, 47/12)},
}


def native_cover_window(profile_key: str, skill_id: int, schedule: dict):
    window = _NATIVE_COVER_WINDOWS.get(profile_key, {}).get(skill_id)
    if window is None:
        return None
    loop = schedule['loop']
    # These source-bound windows begin at or after LoopEnd; never map a point
    # inside a repeating loop to one invented wall-clock interval.
    if loop and window[0] < loop['end'] - _EPSILON:
        raise ValueError('cover window requires repeated-loop mapping')
    shift = loop['shift_seconds'] if loop else 0.
    return tuple(at + shift for at in window)


def ordinary_fire_record(profile_key: str, skill_id: int) -> dict:
    """Return extracted legacy AttackV2/AttackV3 fire cardinality."""
    return DATA["profiles"][profile_key]["ordinary_fire"][str(skill_id)]


def ordinary_fire_schedule(profile_key: str, skill_id: int, *, start: float = 0.0,
                           destroyed_parts=(), coroutine_step: float | None = None,
                           casting_complete: bool = False) -> dict:
    """Schedule every physical fire from an ordinary AttackV2/AttackV3 skill.

    Sequence spaces every prefab/muzzle fire by DelayTime.  Concurrence and
    ConcurrenceGroup emit every filtered muzzle together, then repeat that
    group once per table ShotCount.  ``destroyed_parts`` removes weapon
    prefabs before cardinality and damage/HP divisors are computed, matching
    FireCastingV2's WeaponData.IsDestroy filter.
    """
    row = ordinary_fire_record(profile_key, skill_id)
    destroyed_numbers = {
        int(part) for part in destroyed_parts
        if isinstance(part, int) or (isinstance(part, str) and part.isdigit())
    }
    destroyed_names = {
        str(part).replace("_", "").lower() for part in destroyed_parts
        if not (isinstance(part, int) or (isinstance(part, str) and part.isdigit()))
    }
    active_prefabs = [
        dict(prefab, source_index=index) for index,prefab in enumerate(row["weapon_prefabs"])
        if int(prefab["parts_type"]) not in destroyed_numbers
        and prefab["parts_type_name"].lower() not in destroyed_names
    ]
    muzzle_count = sum(len(prefab["muzzles"]) for prefab in active_prefabs)
    count = int(row["shot_count"]) * muzzle_count
    delay = float(row["delay_seconds"])
    start = float(start)
    fire_start = start + (0.0 if casting_complete else float(row.get("effective_casting_seconds", 0.0)))
    events = []
    if row["shot_timing"] == "Sequence":
        for hit_index in range(count):
            prefab=active_prefabs[hit_index % len(active_prefabs)]
            events.append({"time":fire_start+hit_index*delay,"hit_index":hit_index,
                "fire_index":hit_index,"prefab_index":prefab['source_index'],
                "muzzle_index":(hit_index//len(active_prefabs))%len(prefab['muzzles']),
                "weapon_part":prefab['parts_type_name']})
    elif row["shot_timing"] in {"Concurrence", "ConcurrenceGroup"}:
        for shot_index in range(int(row["shot_count"])):
            for prefab in active_prefabs:
                for muzzle_index in range(len(prefab['muzzles'])):
                    events.append({"time":fire_start+shot_index*delay,
                        "hit_index":len(events),"shot_index":shot_index,
                        "fire_index":shot_index,"prefab_index":prefab['source_index'],
                        "muzzle_index":muzzle_index,"weapon_part":prefab['parts_type_name']})
    else:
        raise ValueError(f"unsupported ShotTiming {row['shot_timing']!r}")
    impacts = [event["time"] for event in events]
    if coroutine_step is not None and events:
        # FireCastingV2 yields Fire, which yields Sequence/ConcurrenceFire,
        # which yields WaitFire. Each new child begins on the next update.
        # Original TickCoroutine.ProcessIEnumeratorRecursive unwinds completed
        # children in the same update, but never starts a newly yielded child.
        step = float(coroutine_step)
        if not math.isfinite(step) or step <= 0:
            raise ValueError("coroutine_step must be finite and positive")
        delay_ticks = math.ceil(delay / step - _EPSILON)
        tick = 3
        previous_group = None
        for index, event in enumerate(events):
            group = event.get('shot_index', event['fire_index'])
            if index:
                if row['shot_timing'] == 'Sequence':
                    tick += 2 + delay_ticks
                elif row['shot_timing'] == 'Concurrence':
                    tick += (2 if group != previous_group else 1)
                    if group:tick += delay_ticks
                else:
                    tick += 2 + delay_ticks if group != previous_group else 1
            event['time'] = fire_start + tick * step
            event['coroutine_tick'] = tick
            previous_group = group
        impacts = [event['time'] for event in events]
    damage_divisor = muzzle_count
    damage_coefficient = (
        math.floor(float(row["skill_value01_raw"]) / muzzle_count + 0.5)
        if muzzle_count else 0
    )
    damage_shot_count = int(row["shot_count"]) if row["fire_type"] == "Instant" else 1
    projectile_hp_divisor = count if row["fire_type"] == "ProjectileCurve" else None
    # Fire waits the final MonsterFireEvent's DelayTime and then the cached
    # fire-end clip after its last physical launch. ``end`` remains the final
    # impact for existing consumers; ``action_end`` is behavior-tree occupancy.
    action_end = (
        max(impacts) + float(row.get("shot_tail_seconds", delay))
        + float(row.get("fire_end_animation_seconds", 0.0))
        if impacts else start
    )
    if coroutine_step is not None and impacts:
        # PlayAnimEnd yields the shot tail, then the original end-clip wait.
        # Even a zero-second WaitForTickSeconds starts on the next update.
        tail = math.ceil(float(row.get('shot_tail_seconds', delay))/step-_EPSILON)
        clip = math.ceil(float(row.get('fire_end_animation_seconds',0))/step-_EPSILON)
        group_tail = delay_ticks if row['shot_timing']=='ConcurrenceGroup' else 0
        action_end = max(impacts) + (3 + tail + clip + group_tail)*step
    return {
        "skill_id": int(skill_id),
        "impacts": impacts,
        "impact_events": events,
        "end": max(impacts, default=start),
        "action_end": action_end,
        "active_weapon_prefab_count": len(active_prefabs),
        "active_muzzle_count": muzzle_count,
        "damage_ratio_divisor": damage_divisor,
        "damage_coefficient_raw": damage_coefficient,
        "damage_shot_count": damage_shot_count,
        "projectile_hp_ratio_divisor": projectile_hp_divisor,
    }


def move_distance(position: dict, destination: dict, using_axis_y: bool) -> float:
    """Distance used by MoveToVer2.IsInPoint (XYZ or XZ)."""
    axes = ("x", "y", "z") if using_axis_y else ("x", "z")
    return math.sqrt(sum((float(destination[a]) - float(position[a])) ** 2 for a in axes))


def combat_zone_contains(position: dict, *, slope: float = 1.5,
                         max_z: float = 40.0, max_y: float = 0.5) -> bool:
    """Apply NKCombatZone.IsIn using its current native constructor defaults."""
    x = float(position["x"])
    y = float(position["y"])
    z = float(position["z"])
    return slope * x + z > 0 and z - slope * x > 0 and max_z > z and max_y > y


def move_reached(position: dict, destination: dict, tolerance: float, using_axis_y: bool) -> bool:
    """Whether MoveToVer2 returns Success on this update."""
    return move_distance(position, destination, using_axis_y) <= float(tolerance)


def move_speed_step(current_speed: float, monster_speed_raw: int, speed_rate: float,
                    acceleration_time_raw: int, dt: float) -> float:
    """Advance movement speed by the exact MonsterLogic.SetMove interpolation.

    Both raw monster speed and acceleration time use a 0.01 multiplier.  The
    client lerps current speed toward (speed * rate) by clamp(acceleration*dt).
    """
    target = float(monster_speed_raw) * 0.01 * float(speed_rate)
    alpha = min(1.0, max(0.0, float(acceleration_time_raw) * 0.01 * float(dt)))
    return current_speed + (target - current_speed) * alpha


def move_duration(distance: float, tolerance: float, monster_speed_raw: int,
                  speed_rate: float, acceleration_time_raw: int, *,
                  dt: float = 0.02, current_speed: float = 0.0) -> float:
    """Integrate a fixed-rate MoveToVer2 segment until its tolerance is reached.

    The caller must supply the rate chosen for the segment and carried current
    speed.  MoveToVer2 can switch between in/out combat-zone rates while moving;
    this helper intentionally does not guess that zone state.
    """
    remaining = max(0.0, float(distance) - float(tolerance))
    elapsed = 0.0
    while remaining > _EPSILON:
        current_speed = move_speed_step(
            current_speed, monster_speed_raw, speed_rate, acceleration_time_raw, dt
        )
        if current_speed <= 0:
            raise ValueError("movement speed cannot reach a positive value")
        remaining -= current_speed * dt
        elapsed += dt
        if elapsed > 3600:
            raise ValueError("movement did not converge")
    return elapsed


def phase_action_status(requested_phase: int, current_phase: int, *,
                        timeline_playing: bool) -> str:
    """Return isPhaseAction's OnUpdate status.

    OnStart dispatches the cutscene only when requested_phase > current_phase.
    OnUpdate returns Running while that timeline plays and Failure afterward.
    An already-reached phase also returns Failure immediately.
    """
    if requested_phase <= current_phase:
        return "failure"
    return "running" if timeline_playing else "failure"


def phase_duration(profile_key: str) -> float:
    """Asset duration for a fallback scheduler; callback state is authoritative."""
    return float(DATA["profiles"][profile_key]["phase"]["completion_seconds"])


def phase_stops_spot_tick(profile_key: str) -> bool:
    """Whether the phase timeline pauses all normal Spot tick contexts."""
    return bool(DATA["profiles"][profile_key]["phase"]["stop_spot_tick"])
