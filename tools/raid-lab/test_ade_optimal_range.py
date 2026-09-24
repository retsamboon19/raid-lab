"""Ade's approximate near-range extension and explicit legacy overrides."""

import unittest
import sys
from pathlib import Path
from types import SimpleNamespace

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "nikke-team-builder"))

from calculator.buff_manager import ActiveBuff, BuffManager
from calculator.optimal_range import ADE, is_optimal_range
import core
from raid_boss_combat import RaidBossRuntime


class AdeOptimalRangeTests(unittest.TestCase):
    def setUp(self):
        self.enemy = {"optimal_range_weapons": [], "distance_m": 30.0}
        self.bm = BuffManager([{"name": ADE, "skill_level": 10,
                                "equipment": {}, "cube": {"name": "", "level": 0},
                                "collection_stage": "없음"}],
                              {"enemy": self.enemy})

    def add_range_buff(self, value, stacks=1, expires=10.0):
        effect = {"stat": "optimal_range_min", "fixed_value": value,
                  "max_stack": 10 if stacks > 1 else 1}
        self.bm._active.append(ActiveBuff(effect, ADE, [ADE], 0.0, expires, stack=stacks))

    def test_near_boundary_tracks_stacks_and_expiry(self):
        self.assertFalse(is_optimal_range(ADE, "SR", self.enemy, self.bm, 1.0))
        self.add_range_buff(4.44, 10, expires=5.0)
        self.assertTrue(is_optimal_range(ADE, "SR", self.enemy, self.bm, 4.0))
        self.assertFalse(is_optimal_range(ADE, "SR", self.enemy, self.bm, 5.0))
        self.bm._active[0].stack = 2
        self.assertFalse(is_optimal_range(ADE, "SR", self.enemy, self.bm, 4.0))
        self.add_range_buff(55.56)
        self.assertTrue(is_optimal_range(ADE, "SR", self.enemy, self.bm, 4.0))

    def test_override_and_unknown_distance_keep_legacy_behavior(self):
        self.enemy["optimal_range_weapons"] = ["SG"]
        self.add_range_buff(55.56)
        self.assertFalse(is_optimal_range(ADE, "SR", self.enemy, self.bm, 1.0))
        self.enemy["optimal_range_weapons"] = ["SR"]
        self.assertTrue(is_optimal_range(ADE, "SR", self.enemy, self.bm, 1.0))
        del self.enemy["distance_m"]
        self.enemy["optimal_range_weapons"] = []
        self.assertFalse(is_optimal_range(ADE, "SR", self.enemy, self.bm, 1.0))

    def test_runtime_coordinates_and_condition_use_same_result(self):
        del self.enemy["distance_m"]
        runtime = SimpleNamespace(
            world=SimpleNamespace(coordinates={"x": 0, "y": 0, "z": 50}),
            squad_coordinates={ADE: (0, 0, 0)},
        )
        self.bm.state["encounter_runtime"] = runtime
        self.assertTrue(is_optimal_range(ADE, "SR", self.enemy, self.bm, 1.0))
        self.assertTrue(self.bm._condition_ok(["optimal_range"], ADE, 1.0))
        runtime.world.coordinates["z"] = 120
        self.assertFalse(self.bm._condition_ok(["optimal_range"], ADE, 1.0))

    def test_real_anomaly_runtime_supplies_live_coordinates(self):
        runtime = RaidBossRuntime([], 180, key="anomaly-ultra")
        character = core.spec.build_char(ADE, core.default_build(), no_layer=True)
        bm = BuffManager([character], {"enemy": {"optimal_range_weapons": []}})
        runtime.bind(bm, [character], {ADE: SimpleNamespace(base_atk=1)})
        self.assertIn(ADE, runtime.squad_coordinates)
        self.assertIsNotNone(runtime.world.coordinates)
        runtime.world.coordinates = dict(runtime.squad_coordinates[ADE]
                                         if isinstance(runtime.squad_coordinates[ADE], dict)
                                         else zip(("x", "y", "z"), runtime.squad_coordinates[ADE]))
        runtime.world.coordinates["z"] += 50
        self.assertTrue(is_optimal_range(ADE, "SR", bm.state["enemy"], bm, 1.0))


if __name__ == "__main__":
    unittest.main()
