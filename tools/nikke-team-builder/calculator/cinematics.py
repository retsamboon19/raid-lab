"""Advance function clocks while an encounter cinematic freezes battle time.

The NIKKE client keeps SpotManagement ticks running during monster phase
cinematics even though CampaignProcess no longer increments its battle clock.
This helper advances time-based functions at frame cadence, then rebases their
absolute timestamps into the calculator's battle-time domain.  Callers therefore
keep one public battle clock without collapsing periodic effects into one jump.
"""
from __future__ import annotations

from dataclasses import dataclass
import math
from typing import Callable, Iterable


@dataclass(frozen=True)
class CinematicSpan:
    battle_time: float
    seconds: float
    phase: int | None = None
    stop_spot_tick: bool = False


class CinematicCursor:
    """Consume newly appended ``runtime.phase_cinematics`` records once."""

    def __init__(self) -> None:
        self._runtime_id: int | None = None
        self._index = 0

    def consume(self, runtime, battle_time: float) -> list[CinematicSpan]:
        runtime_id = id(runtime)
        if runtime_id != self._runtime_id:
            self._runtime_id = runtime_id
            self._index = 0
        records = getattr(runtime, "phase_cinematics", ())
        result: list[CinematicSpan] = []
        while self._index < len(records):
            record = records[self._index]
            record_time = float(record.get("time", battle_time))
            # Do not consume a predeclared future cinematic.
            if record_time > battle_time + 1e-9:
                break
            self._index += 1
            # A live boss timeline is recorded for reporting but consumes
            # ordinary battle ticks. It must not advance a second virtual clock.
            if record.get("battle_clock_paused") is False:
                continue
            seconds = float(record.get("seconds", 0.0))
            if math.isfinite(seconds) and seconds > 0.0:
                result.append(CinematicSpan(
                    record_time, seconds, record.get("phase"),
                    bool(record.get("stop_spot_tick", False)),
                ))
        return result


def cinematic_ticks(start: float, seconds: float, dt: float) -> Iterable[float]:
    """Yield frame ticks strictly after ``start``, including the exact end."""
    if not (math.isfinite(seconds) and seconds > 0.0):
        return
    if not (math.isfinite(dt) and dt > 0.0):
        raise ValueError("cinematic dt must be a positive finite number")
    end = start + seconds
    count = int(math.floor(seconds / dt + 1e-9))
    for index in range(1, count + 1):
        tick = start + index * dt
        if tick < end - 1e-9:
            yield tick
    yield end


def _shift(value: float, seconds: float) -> float:
    value = float(value)
    if not math.isfinite(value):
        return value
    return value - seconds


def _shift_burst_deadline(value: float, seconds: float) -> float:
    """Shift real burst deadlines while retaining negative sentinel values."""
    value = float(value)
    if not math.isfinite(value) or value < 0.0:
        return value
    return value - seconds


def _rebase_buff_manager(bm, seconds: float, battle_time: float) -> None:
    for buff in getattr(bm, "_active", ()):
        buff.activated_at = _shift(buff.activated_at, seconds)
        buff.expires_at = _shift(buff.expires_at, seconds)
        for window in getattr(buff, "enemy_target_windows", {}).values():
            window["activated_at"] = _shift(window["activated_at"], seconds)
            window["expires_at"] = _shift(window["expires_at"], seconds)

    bm._next_fire = {
        key: (_shift(next_t, seconds), interval)
        for key, (next_t, interval) in getattr(bm, "_next_fire", {}).items()
    }
    bm._dot_timers = {
        key: (caster, _shift(next_t, seconds), _shift(expires_at, seconds))
        for key, (caster, next_t, expires_at) in getattr(bm, "_dot_timers", {}).items()
    }
    bm._instant_timers = {
        key: (caster, _shift(next_t, seconds), _shift(expires_at, seconds))
        for key, (caster, next_t, expires_at) in getattr(bm, "_instant_timers", {}).items()
    }
    bm._ramp_pending = [
        (_shift(fire_t, seconds), effect, caster, stack)
        for fire_t, effect, caster, stack in getattr(bm, "_ramp_pending", ())
    ]
    bm._lazy_target_cache = {
        (caster, _shift(activated_at, seconds), target): resolved
        for (caster, activated_at, target), resolved
        in getattr(bm, "_lazy_target_cache", {}).items()
    }

    for info in getattr(bm, "state", {}).get("weapon_change", {}).values():
        if "expires_at" in info:
            info["expires_at"] = _shift(info["expires_at"], seconds)
    for by_id in getattr(bm, "state", {}).get("feathers", {}).values():
        for summon in by_id.values():
            summon["expiry"] = [_shift(value, seconds) for value in summon.get("expiry", ())]
            if summon.get("next_t") is not None:
                summon["next_t"] = _shift(summon["next_t"], seconds)

    bm._cur_t = battle_time
    invalidate = getattr(bm, "_invalidate_buffs_cache", None)
    if invalidate is not None:
        invalidate()


def _rebase_burst_controller(controller, seconds: float) -> None:
    for name in ("burst_ready_at", "gauge_full_at"):
        values = getattr(controller, name, None)
        if values is not None:
            for key, value in values.items():
                values[key] = _shift(value, seconds)
    for name in (
        "_stage_open_t", "_next_action_t", "_full_burst_end_t",
        "_last_fb_start_t", "_obs_next_fb", "_cd_next_fb",
    ):
        if hasattr(controller, name):
            setattr(controller, name, _shift_burst_deadline(getattr(controller, name), seconds))


def advance_cinematic_reloads(char_states, bm, function_time: float) -> tuple[set[str], set[str]]:
    """Complete reload ticks while monster cinematics pause battle time.

    Native ``UpdateReload`` continues during phase cinematics, but dead
    characters do not update.  Temporary weapon modes use the same bounded
    reload rule as the engine's cover path: only persistent, finite-ammo modes
    that explicitly own their reload may finish one here.
    """
    advanced: set[str] = set()
    finished: set[str] = set()
    hp = getattr(bm, "state", {}).get("hp", {})
    for name, cs in char_states.items():
        if hp.get(name, 0) <= 0 or cs.reloading_until <= 0:
            continue
        wc = bm.get_weapon_change(name)
        reload_runs = wc is None or (
            cs._reload_in_weapon_change
            and wc.get("max_ammo", -1) != -1
            and wc.get("duration") is None
            and wc.get("duration_bullets") is None
        )
        if reload_runs:
            advanced.add(name)
            if function_time >= cs.reloading_until:
                cs._finish_reload(function_time, bm)
                finished.add(name)
    return advanced, finished


def rebase_cinematic_reloads(
    char_states, seconds: float, advanced: set[str], finished: set[str]
) -> None:
    """Return reload deadlines advanced in virtual time to battle-clock time."""
    for name, cs in char_states.items():
        if name in advanced and cs.reloading_until > 0:
            cs.reloading_until = _shift(cs.reloading_until, seconds)
        if name not in finished:
            continue
        if cs._post_reload_end_t > 0:
            cs._post_reload_end_t = _shift(cs._post_reload_end_t, seconds)
        cs.next_fire_time = _shift(cs.next_fire_time, seconds)


def advance_cinematic_functions(
    bm,
    burst_controller,
    state: dict,
    battle_time: float,
    seconds: float,
    dt: float,
    after_tick: Callable[[float, float], None] | None = None,
    *,
    before_tick: Callable[[float, float], None] | None = None,
) -> None:
    """Advance timed functions through one battle-clock-paused cinematic.

    ``bm.tick`` runs once per simulation frame so periodic effects preserve every
    tick.  Burst expiry and cooldown clocks also advance, while the pause gate
    prevents a new burst activation.  ``after_tick(elapsed, delta)`` runs after
    each BuffManager tick and lets encounter-owned clocks advance against the
    same current buff/shield state before timestamps are rebased.
    ``before_tick(elapsed, delta)`` runs first so an encounter can expose the
    virtual frame time to damage callbacks emitted from ``bm.tick`` itself.
    """
    if not (math.isfinite(seconds) and seconds > 0.0):
        return
    old_pause = state.get("encounter_pause_burst")
    state["encounter_pause_burst"] = True
    try:
        previous_time = battle_time
        for function_time in cinematic_ticks(battle_time, seconds, dt):
            elapsed = function_time - battle_time
            delta = function_time - previous_time
            if before_tick is not None:
                before_tick(elapsed, delta)
            bm.tick(function_time)
            if burst_controller is not None:
                burst_controller.tick(function_time, bm, state)
            if after_tick is not None:
                after_tick(elapsed, delta)
            previous_time = function_time
    finally:
        if old_pause is None:
            state.pop("encounter_pause_burst", None)
        else:
            state["encounter_pause_burst"] = old_pause
    _rebase_buff_manager(bm, seconds, battle_time)
    if burst_controller is not None:
        _rebase_burst_controller(burst_controller, seconds)
