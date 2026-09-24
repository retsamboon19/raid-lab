"""Regressions for battle-clock-paused phase cinematic function time."""
import math
from types import SimpleNamespace
import unittest

import core  # Adds the shared calculator package to sys.path.
from calculator.cinematics import (
    CinematicCursor,
    advance_cinematic_functions,
    advance_cinematic_reloads,
    rebase_cinematic_reloads,
)


class _BuffManager:
    def __init__(self):
        self.ticks = []
        self._active = [SimpleNamespace(
            activated_at=0.0, expires_at=10.0,
            enemy_target_windows={
                "__boss__": {"activated_at": 1.0, "expires_at": 9.0, "stack": 1},
            },
        )]
        self._next_fire = {1: (4.0, 1.0)}
        self._dot_timers = {2: ("unit", 4.0, 10.0)}
        self._instant_timers = {3: ("unit", 4.0, 10.0)}
        self._ramp_pending = [(4.0, {}, "unit", 1)]
        self._lazy_target_cache = {("unit", 0.0, "self"): ["unit"]}
        self._cur_t = 0.0
        self.invalidations = 0
        self.state = {
            "weapon_change": {"unit": {"expires_at": 10.0}},
            "feathers": {"unit": {"f": {"expiry": [10.0], "next_t": 4.0}}},
        }

    def tick(self, t):
        self.ticks.append(t)

    def _invalidate_buffs_cache(self):
        self.invalidations += 1


class _BurstController:
    def __init__(self):
        self.ticks = []
        self.burst_ready_at = {"unit": 10.0}
        self.gauge_full_at = {"unit": 5.0}
        self._stage_open_t = -1.0
        self._next_action_t = math.inf
        self._full_burst_end_t = 10.0
        self._last_fb_start_t = -1.0
        self._obs_next_fb = -1.0
        self._cd_next_fb = -1.0

    def tick(self, t, _bm, state):
        self.ticks.append((t, state.get("encounter_pause_burst")))
        return []


class AnomalyCinematicClockTests(unittest.TestCase):
    def test_cursor_consumes_each_runtime_cinematic_once(self):
        runtime = SimpleNamespace(phase_cinematics=[
            {"time": 2.0, "seconds": 3.0, "phase": 2},
            {"time": 20.0, "seconds": 4.0, "phase": 3},
        ])
        cursor = CinematicCursor()
        first = cursor.consume(runtime, 2.0)
        self.assertEqual([(x.battle_time, x.seconds, x.phase) for x in first], [(2.0, 3.0, 2)])
        self.assertEqual(cursor.consume(runtime, 2.0), [])
        self.assertEqual(cursor.consume(runtime, 20.0)[0].seconds, 4.0)

    def test_cursor_preserves_stop_spot_tick_gate(self):
        runtime = SimpleNamespace(phase_cinematics=[
            {"time": 2.0, "seconds": 3.0, "phase": 2, "stop_spot_tick": True},
        ])
        span = CinematicCursor().consume(runtime, 2.0)[0]
        self.assertTrue(span.stop_spot_tick)

    def test_cursor_does_not_replay_live_phase_as_virtual_time(self):
        runtime = SimpleNamespace(phase_cinematics=[
            {"time": 2, "seconds": 3, "phase": 2,
             "stop_spot_tick": False, "battle_clock_paused": False},
            {"time": 6, "seconds": 8, "phase": 2, "stop_spot_tick": True},
        ])
        cursor = CinematicCursor()
        self.assertEqual(cursor.consume(runtime, 2), [])
        self.assertEqual(cursor.consume(runtime, 6)[0].seconds, 8)

    def test_function_ticks_run_at_frame_steps_then_rebase_to_battle_time(self):
        bm = _BuffManager()
        burst = _BurstController()
        state = {}
        collected = []
        advance_cinematic_functions(
            bm, burst, state, battle_time=2.0, seconds=3.0, dt=1.0,
            after_tick=lambda elapsed, delta: collected.append((elapsed, delta)),
        )
        self.assertEqual(bm.ticks, [3.0, 4.0, 5.0])
        self.assertEqual(collected, [(1.0, 1.0), (2.0, 1.0), (3.0, 1.0)])
        self.assertTrue(all(paused for _, paused in burst.ticks))
        self.assertNotIn("encounter_pause_burst", state)
        self.assertEqual(bm._active[0].activated_at, -3.0)
        self.assertEqual(bm._active[0].expires_at, 7.0)
        self.assertEqual(
            bm._active[0].enemy_target_windows["__boss__"],
            {"activated_at": -2.0, "expires_at": 6.0, "stack": 1},
        )
        self.assertEqual(bm._dot_timers[2], ("unit", 1.0, 7.0))
        self.assertEqual(bm._lazy_target_cache, {("unit", -3.0, "self"): ["unit"]})
        self.assertEqual(bm.state["weapon_change"]["unit"]["expires_at"], 7.0)
        self.assertEqual(bm.state["feathers"]["unit"]["f"]["expiry"], [7.0])
        self.assertEqual(burst.burst_ready_at["unit"], 7.0)
        self.assertEqual(burst._full_burst_end_t, 7.0)
        self.assertEqual(burst._stage_open_t, -1.0)
        self.assertEqual(bm._cur_t, 2.0)

    def test_non_integral_duration_keeps_exact_end_tick(self):
        bm = _BuffManager()
        steps = []
        advance_cinematic_functions(
            bm, None, {}, 10.0, 2.5, 1.0,
            after_tick=lambda elapsed, delta: steps.append((elapsed, delta)),
        )
        self.assertEqual(bm.ticks, [11.0, 12.0, 12.5])
        self.assertEqual(steps, [(1.0, 1.0), (2.0, 1.0), (2.5, 0.5)])

    def test_before_tick_exposes_virtual_time_to_tick_callbacks(self):
        order = []

        class ObservedBuffManager(_BuffManager):
            def tick(self, t):
                order.append(("tick", t))
                super().tick(t)

        bm = ObservedBuffManager()
        advance_cinematic_functions(
            bm, None, {}, 5.0, 1.0, 1.0,
            after_tick=lambda elapsed, delta: order.append(("after", elapsed)),
            before_tick=lambda elapsed, delta: order.append(("before", elapsed)),
        )
        self.assertEqual(order, [("before", 1.0), ("tick", 6.0), ("after", 1.0)])

    def test_reload_finishes_during_cinematic_and_dead_unit_does_not_advance(self):
        class Character:
            def __init__(self, name, deadline):
                self.name = name
                self.reloading_until = deadline
                self._reload_in_weapon_change = False
                self._post_reload_end_t = -1.0
                self.next_fire_time = 0.0
                self.finished = []

            def _finish_reload(self, t, _bm):
                self.finished.append(t)
                self.reloading_until = -1.0
                self._post_reload_end_t = t + 0.3
                self.next_fire_time = t

        alive = Character("alive", 3.0)
        dead = Character("dead", 3.0)
        bm = SimpleNamespace(
            state={"hp": {"alive": 1, "dead": 0}},
            get_weapon_change=lambda _name: None,
        )
        chars = {"alive": alive, "dead": dead}
        advanced, finished = set(), set()
        for function_time in (3.0, 4.0, 5.0):
            tick_advanced, tick_finished = advance_cinematic_reloads(
                chars, bm, function_time
            )
            advanced.update(tick_advanced)
            finished.update(tick_finished)
        rebase_cinematic_reloads(chars, 3.0, advanced, finished)

        self.assertEqual(alive.finished, [3.0])
        self.assertEqual(dead.finished, [])
        self.assertAlmostEqual(alive._post_reload_end_t, 0.3)
        self.assertEqual(alive.next_fire_time, 0.0)
        self.assertEqual(dead.reloading_until, 3.0)

    def test_persistent_weapon_mode_reload_runs_but_timed_mode_is_frozen(self):
        class Character:
            _reload_in_weapon_change = True
            _post_reload_end_t = -1.0
            next_fire_time = 0.0

            def __init__(self):
                self.reloading_until = 2.0
                self.finished = 0

            def _finish_reload(self, _t, _bm):
                self.finished += 1
                self.reloading_until = -1.0

        persistent, timed = Character(), Character()
        modes = {
            "persistent": {"max_ammo": 6},
            "timed": {"max_ammo": 6, "duration": 5},
        }
        bm = SimpleNamespace(
            state={"hp": {"persistent": 1, "timed": 1}},
            get_weapon_change=lambda name: modes[name],
        )
        _, finished = advance_cinematic_reloads(
            {"persistent": persistent, "timed": timed}, bm, 2.0
        )
        self.assertEqual(persistent.finished, 1)
        self.assertEqual(timed.finished, 0)
        self.assertEqual(finished, {"persistent"})


if __name__ == "__main__":
    unittest.main()
