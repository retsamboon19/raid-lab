"""Regression tests for encounter collision metadata consumed by the engine."""
import copy
import unittest

import core
from calculator.timeline import _notify_count


class _CollisionRuntime:
    stopped = False
    waiting = False

    def __init__(self, collisions):
        self.collisions = collisions

    def bind(self, *_args):
        pass

    def advance(self, *_args):
        pass

    def resolve(self, _caster, _element, _weapon, _hit_type, calculate, args):
        result = calculate(**args)
        result.update(
            collision_hits=self.collisions,
            part_hits=max(0, self.collisions - 1),
            body_hits=min(1, self.collisions),
            core_hits=0,
        )
        return result

    def report(self):
        return {}


class _NotifyRecorder:
    def __init__(self):
        self.state = {"rng_acc": {}}
        self.events = []


class AnomalyTimelineMetadataTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        roster = core.demo_roster()
        cls.ids = [row["id"] for row in roster[:5]]
        cls.chars = {row["id"]: row["build"] for row in roster[:5]}

    def _gauge(self, collisions):
        squad = core.spec.build_squad(
            self.ids, chars=copy.deepcopy(self.chars), no_layer=set(self.ids)
        )
        cfg = core.spec.build_config(
            squad,
            {"duration": 1, "rng_mode": "expected", "burst_gauge_mode": "fixed"},
        )
        cfg["encounter_runtime"] = _CollisionRuntime(collisions)
        result = core.simulate(squad, cfg, verbose=True, seed=1)
        return sum(entry.amount for entry in result.log.gauge_log)

    def test_burst_gauge_counts_each_accepted_physical_collision(self):
        one = self._gauge(1)
        self.assertGreater(one, 0)
        self.assertAlmostEqual(self._gauge(2), one * 2)
        self.assertEqual(self._gauge(0), 0)

    def test_integer_and_fractional_collision_notifications_accumulate(self):
        recorder = _NotifyRecorder()
        fire = lambda: recorder.events.append("hit")
        _notify_count(recorder, "core_hit", "unit", 2.5, fire)
        self.assertEqual(len(recorder.events), 2)
        _notify_count(recorder, "core_hit", "unit", 0.5, fire)
        self.assertEqual(len(recorder.events), 3)


if __name__ == "__main__":
    unittest.main()
