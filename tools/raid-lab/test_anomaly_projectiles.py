import math
import unittest

from anomaly_projectiles import (LAUNCH_SOCKETS, NATIVE_SPEED_SCALE,
                                 build_anomaly_mechanics)
from raid_boss_combat import RaidBossRuntime
from test_raid_boss_combat import bind, hit


class AnomalyProjectileTests(unittest.TestCase):
    def mechanics(self, key, *, auto_cover=False):
        runtime = RaidBossRuntime([], 180, key=key, auto_cover=auto_cover)
        mechanics = build_anomaly_mechanics(runtime)
        self.assertIsNotNone(mechanics)
        runtime.projectile_mechanics = mechanics
        return runtime, mechanics

    def skill(self, runtime, ident):
        return next(s for s in runtime.data["skills"] if s["Id"] == ident)

    def test_factory_is_scoped_to_exact_profiles(self):
        mirror = RaidBossRuntime([], 180, key="anomaly-mirror-container")
        indivilia = RaidBossRuntime([], 180, key="anomaly-indivilia")
        ultra = RaidBossRuntime([], 180, key="anomaly-ultra")
        self.assertIsNotNone(build_anomaly_mechanics(mirror))
        self.assertIsNotNone(build_anomaly_mechanics(indivilia))
        self.assertIsNone(build_anomaly_mechanics(ultra))

    def test_observed_endpoint_uses_recipient_and_character_stance(self):
        runtime, mechanics = self.mechanics("anomaly-mirror-container")
        runtime.projectile_target_positions = {"unit": {
            "character": {"aiming": (0.1, -0.5, 4.5),
                          "hiding": (-0.935, -2.2, 4.5)},
            "cover": (-1.028, -2.349, 4.7),
        }}
        self.assertEqual(mechanics._target_position("unit")[0], (0.1, -0.5, 4.5))
        self.assertEqual(mechanics._target_position("unit", "cover")[0], (-1.028, -2.349, 4.7))
        runtime.covered = {"unit"}
        self.assertEqual(mechanics._target_position("unit")[0], (-0.935, -2.2, 4.5))
        self.assertEqual(mechanics._target_position("unit", "cover")[0], (-1.028, -2.349, 4.7))
        skill = dict(self.skill(runtime, 520678), TargetCoverRatio=100,
                     TargetCharacterRatio=0)
        mechanics.perform_skill(skill, {"_locked_targets": ["unit"]})
        self.assertEqual(runtime.projectiles[0]["target_position"], (-1.028, -2.349, 4.7))

    def test_default_endpoints_use_measured_formation_and_cover(self):
        from types import SimpleNamespace
        runtime, mechanics = self.mechanics("anomaly-mirror-container")
        runtime.bm = SimpleNamespace(state={"hp": dict.fromkeys("abcde", 100)})
        self.assertEqual(mechanics._target_position("a")[0], (-5.0, -.5, 4.5))
        self.assertEqual(mechanics._target_position("b", "cover")[0], (-3.428, -2.349, 2.7))
        self.assertEqual(mechanics._target_position("e")[0], (5.8, -.5, 4.5))
        runtime.covered = {"c"}
        for actual, expected in zip(mechanics._target_position("c")[0], (-.935, -2.2, 4.5)):
            self.assertAlmostEqual(actual, expected)
        self.assertEqual(mechanics._target_position("c", "cover")[0], (-1.028, -2.349, 4.7))

    def test_phase_cinematic_advances_mirror_but_freezes_indivilia_projectiles(self):
        mirror, mechanics = self.mechanics("anomaly-mirror-container")
        mechanics.perform_skill(self.skill(mirror, 520678),
                                {"_locked_targets": ["locked"]})
        shot = mirror.projectiles[0]
        mirror.receive_attack = lambda skill, node: None
        mechanics.advance_cinematic_projectiles(shot["deadline"])
        self.assertEqual(shot["status"], "hit")

        indivilia, mechanics = self.mechanics("anomaly-indivilia")
        mechanics.perform_skill(self.skill(indivilia, 531474),
                                {"_locked_targets": ["locked"]})
        shot = indivilia.projectiles[0]
        mechanics.advance_cinematic_projectiles(shot["deadline"] + 1)
        self.assertEqual(shot["status"], "active")

    def test_mirror_cinematic_rebases_only_surviving_active_deadlines(self):
        runtime, mechanics = self.mechanics("anomaly-mirror-container")
        mechanics.perform_skill(self.skill(runtime, 520678),
                                {"_locked_targets": ["locked"]})
        shot = runtime.projectiles[0]
        original = shot["deadline"]
        mechanics.rebase_cinematic_functions(1.25)
        self.assertAlmostEqual(shot["deadline"], original - 1.25)

        indivilia, mechanics = self.mechanics("anomaly-indivilia")
        mechanics.perform_skill(self.skill(indivilia, 531474),
                                {"_locked_targets": ["locked"]})
        shot = indivilia.projectiles[0]
        original = shot["deadline"]
        mechanics.rebase_cinematic_functions(1.25)
        self.assertEqual(shot["deadline"], original)

    def test_installed_skill_records_and_launch_sources(self):
        cases = {
            "anomaly-mirror-container": {
                520661: (5, "ConcurrenceGroup", 1500, 10000, True, 100, 0, 0),
                520672: (1, "Concurrence", 1000, 0, False, 100, 0, 0),
                520673: (1, "Concurrence", 1000, 0, False, 100, 0, 0),
                520674: (1, "Concurrence", 1000, 0, False, 100, 0, 0),
                520675: (1, "Concurrence", 1000, 0, False, 100, 0, 0),
                520678: (1, "Concurrence", 1000, 15000, True, 0, 100, 380),
                520679: (1, "Concurrence", 1000, 15000, True, 0, 100, 380),
            },
            "anomaly-indivilia": {
                531474: (3, "Sequence", 1000, 300, True, 100, 0, 0),
            },
        }
        for key, expected in cases.items():
            runtime = RaidBossRuntime([], 180, key=key)
            for ident, values in expected.items():
                with self.subTest(key=key, skill=ident):
                    skill = self.skill(runtime, ident)
                    actual = (skill["ShotCount"], skill["ShotTiming"],
                              skill["ProjectileSpeed"], skill["ProjectileHpRatio"],
                              skill["IsDestroyableProjectile"],
                              skill["TargetCharacterRatio"], skill["TargetCoverRatio"],
                              skill["SpotExplosionRange"])
                    self.assertEqual(actual, values)
                    self.assertTrue(LAUNCH_SOCKETS[ident])

    def test_mirror_small_missile_hp_and_defence_all_stages(self):
        expected_hp = [8469, 8469, 8469, 14060, 25393,
                       28723, 31914, 40665, 40665]
        expected_def = [17211] * 9
        runtime, mechanics = self.mechanics("anomaly-mirror-container")
        skill = self.skill(runtime, 520661)
        for stage, hp, defence in zip(runtime.stages, expected_hp, expected_def):
            with self.subTest(stage=stage["Step"]):
                runtime.damage = stage["ConditionValueMin"]
                runtime.projectiles.clear()
                mechanics.perform_skill(skill, {"_locked_targets": ["locked"]})
                self.assertEqual(len(runtime.projectiles), 10)
                active = [p for p in runtime.projectiles
                          if p["status"] == "active"]
                pending = [p for p in runtime.projectiles
                           if p["status"] == "pending"]
                self.assertEqual(len(active), 2)
                self.assertTrue(all(p["hp"] == hp for p in active))
                self.assertTrue(all(p["defence"] == defence for p in active))
                self.assertTrue(all(p["hp"] is None and p["defence"] is None
                                    for p in pending))

    def test_mirror_arrow_hp_and_defence_all_stages(self):
        expected_hp = [127035, 127035, 127035, 210900, 380888,
                       430845, 478706, 609975, 609975]
        runtime, mechanics = self.mechanics("anomaly-mirror-container")
        skill = self.skill(runtime, 520678)
        for stage, hp in zip(runtime.stages, expected_hp):
            with self.subTest(stage=stage["Step"]):
                runtime.damage = stage["ConditionValueMin"]
                runtime.projectiles.clear()
                mechanics.perform_skill(skill, {"_locked_targets": ["locked"]})
                projectile = runtime.projectiles[0]
                self.assertEqual(projectile["hp"], hp)
                self.assertEqual(projectile["defence"], 17211)
                self.assertEqual(projectile["target_kind"], "cover")

    def test_mirror_phase_two_defence_layers_are_snapshotted_on_projectile(self):
        runtime, mechanics = self.mechanics("anomaly-mirror-container")
        runtime.anomaly.phase = 2
        runtime.anomaly.defence_layers = {
            "Weapon_07", "Weapon_08", "Weapon_09", "Weapon_10"}
        mechanics.perform_skill(self.skill(runtime, 520678),
                                {"_locked_targets": ["locked"]})
        self.assertAlmostEqual(runtime.projectiles[0]["defence"], 17211 * 4.6)
        runtime.anomaly.defence_layers.remove("Weapon_07")
        self.assertAlmostEqual(runtime.projectiles[0]["defence"], 17211 * 4.6)

    def test_legacy_sequence_defence_is_snapshotted_at_volley_start(self):
        runtime, mechanics = self.mechanics("anomaly-mirror-container")
        mechanics._owner_defence = lambda skill, stat: 111
        mechanics.perform_skill(self.skill(runtime, 520661),
                                {"_locked_targets": ["locked"]})
        pending = runtime.projectiles[2]
        self.assertIsNone(pending["defence"])
        self.assertEqual(pending["volley_defence"], 111)
        mechanics._owner_defence = lambda skill, stat: 999
        runtime.time = .1
        mechanics.advance(.1)
        self.assertEqual(pending["defence"], 111)
        self.assertEqual(pending["defence_snapshot_at"], 0)

    def test_indivilia_needle_hp_and_defence_all_stages(self):
        expected_hp = [141, 141, 141, 234, 479, 532, 748, 1033, 1033]
        expected_def = [21087, 21087, 21087, 86057, 86057, 86057,
                        102664, 123532, 123532]
        runtime, mechanics = self.mechanics("anomaly-indivilia")
        skill = self.skill(runtime, 531474)
        for stage, hp, defence in zip(runtime.stages, expected_hp, expected_def):
            with self.subTest(stage=stage["Step"]):
                runtime.damage = stage["ConditionValueMin"]
                runtime.projectiles.clear()
                mechanics.perform_skill(skill, {"_locked_targets": ["locked"]})
                self.assertEqual(len(runtime.projectiles), 18)
                self.assertTrue(all(p["hp"] == hp for p in runtime.projectiles))
                self.assertTrue(all(p["defence"] == defence for p in runtime.projectiles))
                self.assertEqual([p["shot_index"] for p in runtime.projectiles],
                                 [0] * 6 + [1] * 6 + [2] * 6)
                self.assertEqual([p["launcher_index"] for p in runtime.projectiles],
                                 list(range(6)) * 3)

    def test_native_fire_order_and_delay_are_applied_per_fire_group(self):
        mirror, mechanics = self.mechanics("anomaly-mirror-container")
        mechanics.perform_skill(self.skill(mirror, 520661),
                                {"_locked_targets": ["locked"]})
        self.assertEqual([p["status"] for p in mirror.projectiles],
                         ["active"] * 2 + ["pending"] * 8)
        self.assertEqual([round(p["launch_at"], 3) for p in mirror.projectiles],
                         [0, 0, .1, .1, .2, .2, .3, .3, .4, .4])
        mechanics.advance(.1)
        self.assertEqual([p["status"] for p in mirror.projectiles].count("active"), 4)

        indivilia, mechanics = self.mechanics("anomaly-indivilia")
        mechanics.perform_skill(self.skill(indivilia, 531474),
                                {"_locked_targets": ["locked"]})
        self.assertTrue(all(p["status"] == "active"
                            for p in indivilia.projectiles))
        self.assertEqual([p["launcher_index"] for p in indivilia.projectiles],
                         list(range(6)) * 3)

    def test_pending_projectile_snapshots_stats_at_actual_launch(self):
        runtime, mechanics = self.mechanics("anomaly-mirror-container")
        bind(runtime)
        mechanics.perform_skill(self.skill(runtime, 520661),
                                {"_locked_targets": ["locked"]})
        first = runtime.projectiles[0]
        self.assertEqual(first["incoming_snapshot"]["time"], 0)
        first_attack = first["incoming_snapshot"]["attack"]
        self.assertIsNone(runtime.projectiles[2]["hp"])
        runtime.damage = runtime.stages[-1]["ConditionValueMin"]
        runtime.time = .1
        mechanics.advance(.1)
        later = runtime.projectiles[2]
        self.assertEqual(later["snapshot_at"], .1)
        self.assertGreater(later["hp"], first["hp"])
        self.assertGreater(later["incoming_snapshot"]["attack"], first_attack)
        received = []
        runtime.receive_attack = lambda skill, node: received.append(node)
        mechanics.impact(first, at=first["deadline"])
        self.assertEqual(received[0]["_incoming_snapshot"],
                         first["incoming_snapshot"])

    def test_late_advance_reports_actual_snapshot_tick(self):
        runtime, mechanics = self.mechanics("anomaly-mirror-container")
        bind(runtime)
        mechanics.perform_skill(self.skill(runtime, 520661),
                                {"_locked_targets": ["locked"]})
        runtime.time = .35
        mechanics.advance(.35)
        crossed = runtime.projectiles[2:8]
        self.assertTrue(all(p["launch_at"] < .35 for p in crossed))
        self.assertTrue(all(p["snapshot_at"] == .35 for p in crossed))
        self.assertTrue(all(p["incoming_snapshot"]["time"] == .35
                            for p in crossed))

    def test_automatic_flight_uses_native_speed_and_endpoint_distance(self):
        runtime, mechanics = self.mechanics("anomaly-mirror-container")
        mechanics.perform_skill(self.skill(runtime, 520661),
                                {"_locked_targets": ["locked"]})
        for projectile in runtime.projectiles:
            self.assertIsNotNone(projectile["deadline"])
            self.assertEqual(projectile["impact_at"], projectile["deadline"])
            self.assertEqual(projectile["impact_timing_status"],
                             "estimated-native-distance-speed")
            self.assertAlmostEqual(projectile["native_speed"],
                                   1500 * NATIVE_SPEED_SCALE)
            self.assertAlmostEqual(projectile["flight_seconds"],
                                   projectile["endpoint_distance"] /
                                   projectile["native_speed"])
        received = []
        runtime.receive_attack = lambda skill, node: received.append((skill, node))
        deadline = min(p["deadline"] for p in runtime.projectiles)
        mechanics.advance(deadline - 1e-9)
        self.assertEqual(received, [])
        mechanics.advance(deadline)
        self.assertTrue(any(p["status"] == "hit" for p in runtime.projectiles))
        self.assertTrue(received)

    def test_no_deadline_is_explicit_diagnostic_mode_only(self):
        runtime, mechanics = self.mechanics("anomaly-mirror-container")
        runtime.projectile_diagnostic_no_deadline = True
        mechanics.perform_skill(self.skill(runtime, 520661),
                                {"_locked_targets": ["locked"]})
        self.assertTrue(all(p["deadline"] is None and
                            p["impact_timing_status"] == "diagnostic-unresolved"
                            for p in runtime.projectiles))
        mechanics.advance(10**6)
        self.assertTrue(all(p["status"] == "active" for p in runtime.projectiles))
        self.assertEqual(len(mechanics.report()["unresolved_projectile_impacts"]), 10)

    def test_measured_deadline_overrides_geometric_estimate(self):
        runtime, mechanics = self.mechanics("anomaly-indivilia")
        received = []
        runtime.receive_attack = lambda skill, node: received.append((skill, node))
        mechanics.perform_skill(self.skill(runtime, 531474),
                                {"_locked_targets": ["locked"]})
        first, second = runtime.projectiles[:2]
        self.assertTrue(mechanics.set_impact_at(first, 1.25, "native trace frame 75"))
        mechanics.advance(1.249)
        self.assertEqual(received, [])
        mechanics.advance(1.25)
        self.assertEqual(first["status"], "hit")
        self.assertEqual(second["status"], "active")
        self.assertEqual(len(received), 1)
        with self.assertRaises(ValueError):
            mechanics.set_impact_at(second, -1, "native trace")

    def test_destroyable_projectiles_absorb_player_fire_independently(self):
        runtime, mechanics = self.mechanics("anomaly-mirror-container")
        _, names = bind(runtime)
        mechanics.perform_skill(self.skill(runtime, 520661),
                                {"_locked_targets": [names[0]]})
        first, second = runtime.projectiles[:2]
        before_boss = runtime.damage
        self.assertEqual(hit(runtime, first["hp"], caster=names[1],
                             is_normal_atk=True), 0)
        self.assertEqual(first["status"], "destroyed")
        self.assertEqual(second["status"], "active")
        self.assertEqual(runtime.damage, before_boss)
        self.assertEqual(runtime.damage_to_projectiles, first["max_hp"])

    def test_non_destroyable_timeline_bullets_do_not_intercept_player_fire(self):
        runtime, mechanics = self.mechanics("anomaly-mirror-container")
        skill = self.skill(runtime, 520672)
        for _ in range(5):
            mechanics.perform_skill(skill, {"_locked_targets": ["locked"]})
        self.assertEqual(len(runtime.projectiles), 5)
        self.assertTrue(all(not p["destroyable"] and p["hp"] is None
                            for p in runtime.projectiles))
        self.assertIsNone(mechanics.resolve_target("unit", "전격", "AR", True))

    def test_native_prefab_multiplicity_and_per_prefab_damage_split(self):
        mirror, mirror_mechanics = self.mechanics("anomaly-mirror-container")
        mirror_mechanics.perform_skill(self.skill(mirror, 520661),
                                      {"_locked_targets": ["locked"]})
        self.assertEqual(len(mirror.projectiles), 10)
        self.assertEqual([p["launch_socket"] for p in mirror.projectiles],
                         ["socket_muzzle_fire_19", "socket_muzzle_fire_18"] * 5)
        self.assertTrue(all(p["skill"]["_damage_shots"] == 1
                            for p in mirror.projectiles))
        self.assertTrue(all(p["projectile_damage_ratio_divisor"] == 2
                            and p["projectile_damage_ratio"] == 600
                            for p in mirror.projectiles))
        self.assertTrue(all(p["projectile_hp_shot_divisor"] == 10
                            for p in mirror.projectiles))

        indivilia, indivilia_mechanics = self.mechanics("anomaly-indivilia")
        indivilia_mechanics.perform_skill(self.skill(indivilia, 531474),
                                         {"_locked_targets": ["locked"]})
        self.assertEqual(len(indivilia.projectiles), 18)
        self.assertEqual({p["launch_socket"] for p in indivilia.projectiles},
                         set(LAUNCH_SOCKETS[531474]))
        self.assertTrue(all(p["skill"]["_damage_shots"] == 1
                            for p in indivilia.projectiles))
        self.assertTrue(all(p["projectile_damage_ratio_divisor"] == 6
                            and p["projectile_damage_ratio"] == 500
                            for p in indivilia.projectiles))
        self.assertTrue(all(p["projectile_hp_shot_divisor"] == 18
                            for p in indivilia.projectiles))
        self.assertEqual(sum(p["skill"]["SkillValue01"]
                             for p in mirror.projectiles), 6000)
        self.assertEqual(sum(p["skill"]["SkillValue01"]
                             for p in indivilia.projectiles), 9000)

    def test_observed_target_transform_replaces_formation_proxy(self):
        runtime, mechanics = self.mechanics("anomaly-indivilia")
        runtime.projectile_target_positions = {"locked": (3, 4, 5)}
        mechanics.perform_skill(self.skill(runtime, 531474),
                                {"_locked_targets": ["locked"]})
        first = runtime.projectiles[0]
        self.assertEqual(first["target_position"], (3.0, 4.0, 5.0))
        self.assertEqual(first["target_position_source"],
                         "runtime observed target transform")
        self.assertAlmostEqual(first["endpoint_distance"],
                               math.dist(first["launch_position"], (3, 4, 5)))

    def test_destroyed_projectile_can_never_hit(self):
        runtime, mechanics = self.mechanics("anomaly-indivilia")
        received = []
        runtime.receive_attack = lambda *args, **kwargs: received.append(args)
        mechanics.perform_skill(self.skill(runtime, 531474),
                                {"_locked_targets": ["locked"]})
        projectile = runtime.projectiles[0]
        mechanics.resolve_hit(projectile, projectile["hp"], {"is_normal_atk": True})
        self.assertFalse(mechanics.impact(projectile))
        self.assertEqual(received, [])

    def test_phase_cutscene_preserves_pending_and_flying_shots(self):
        runtime, mechanics = self.mechanics("anomaly-mirror-container")
        received = []
        runtime.receive_attack = lambda skill, node: received.append(skill["Id"])
        mechanics.perform_skill(self.skill(runtime, 520661),
                                {"_locked_targets": ["locked"]})
        active = [p for p in runtime.projectiles if p["status"] == "active"]
        pending = [p for p in runtime.projectiles if p["status"] == "pending"]
        self.assertEqual((len(active), len(pending)), (2, 8))
        mechanics.on_cinematic_start(0)
        mechanics.on_phase_changed(2, 0)  # idempotent phase-commit fanout
        self.assertTrue(all(p["status"] == "pending" for p in pending))
        mechanics.advance(max(p["deadline"] for p in active + pending))
        self.assertTrue(all(p["status"] == "hit" for p in active + pending))
        self.assertEqual(received, [520661] * 10)

    def test_non_cancelable_projectile_volley_survives_part_break(self):
        runtime, mechanics = self.mechanics("anomaly-mirror-container")
        mechanics.perform_skill(self.skill(runtime, 520661),
                                {"_locked_targets": ["locked"]})
        pending = [p for p in runtime.projectiles if p["status"] == "pending"]
        self.assertEqual(mechanics.on_part_broken("Weapon_01", 0), 0)
        self.assertTrue(all(p["status"] == "pending" for p in pending))

    def test_broken_part_matching_normalizes_enum_spelling(self):
        runtime, mechanics = self.mechanics("anomaly-mirror-container")
        skill = self.skill(runtime, 520661)
        skill["CancelType"] = "BrokenParts"
        skill["ControlParts"] = ["Weapon02"]
        mechanics.perform_skill(skill, {"_locked_targets": ["locked"]})
        self.assertEqual(mechanics.on_part_broken("Weapon_02", 0), 8)

    def test_mirror_cover_arrow_hits_locked_cover_not_character(self):
        runtime, mechanics = self.mechanics("anomaly-mirror-container")
        bm, names = bind(runtime)
        target = names[0]
        before_hp = bm.state["hp"][target]
        before_cover = runtime.cover[target]
        mechanics.perform_skill(self.skill(runtime, 520678),
                                {"_locked_targets": [target]})
        projectile = runtime.projectiles[0]
        self.assertTrue(mechanics.impact(projectile, source="test observed impact"))
        self.assertEqual(bm.state["hp"][target], before_hp)
        self.assertLess(runtime.cover[target], before_cover)
        self.assertEqual(runtime.incoming[-1]["blocked_by"], "cover")
        self.assertEqual(runtime.incoming[-2]["target"], target)
        self.assertEqual(projectile["splash_resolution"],
                         "formation-transform proxy")
        self.assertEqual(projectile["splash_radius_world"], 3.8)
        self.assertEqual([row["target"] for row in runtime.incoming[-2:]], names)

    def test_cover_arrow_does_not_retarget_character_when_cover_destroyed(self):
        runtime, mechanics = self.mechanics("anomaly-mirror-container")
        bm, names = bind(runtime)
        target = names[0]
        runtime.cover[target] = 0
        before_hp = bm.state["hp"][target]
        mechanics.perform_skill(self.skill(runtime, 520678),
                                {"_locked_targets": [target]})
        projectile = runtime.projectiles[0]
        self.assertEqual(projectile["node"]["_target_recipient"], "cover")
        mechanics.impact(projectile, source="test observed impact")
        self.assertEqual(bm.state["hp"][target], before_hp)
        target_rows = [row for row in runtime.incoming if row["target"] == target]
        self.assertEqual(target_rows[-1]["blocked_by"], "destroyed cover")

    def test_mirror_arrow_accepts_observed_splash_collider_set(self):
        runtime, mechanics = self.mechanics("anomaly-mirror-container")
        bm, names = bind(runtime)
        before_hp = dict(bm.state["hp"])
        before_cover = dict(runtime.cover)
        mechanics.perform_skill(self.skill(runtime, 520679),
                                {"_locked_targets": [names[0]]})
        projectile = runtime.projectiles[0]
        mechanics.impact(projectile, source="native collider trace",
                         splash_targets=names)
        self.assertEqual(projectile["splash_resolution"], "observed")
        self.assertEqual(projectile["splash_targets"], names)
        for name in names:
            self.assertEqual(bm.state["hp"][name], before_hp[name])
            self.assertLess(runtime.cover[name], before_cover[name])
        self.assertEqual([row["target"] for row in runtime.incoming[-2:]], names)

    def test_indivilia_eighteen_needles_keep_fixed_high_attack_target_and_split_damage(self):
        runtime, mechanics = self.mechanics("anomaly-indivilia")
        bm, names = bind(runtime)
        target = names[1]
        skill = self.skill(runtime, 531474)
        mechanics.perform_skill(skill, {"_locked_targets": [target]})
        self.assertEqual([p["target"] for p in runtime.projectiles], [target] * 18)
        self.assertTrue(all(p["skill"]["ShotCount"] == 1 and
                            p["skill"]["_damage_shots"] == 1 and
                            p["skill"]["SkillValue01"] == 500
                            for p in runtime.projectiles))
        before = bm.state["hp"][target]
        for projectile in runtime.projectiles:
            mechanics.impact(projectile, source="test observed impact")
        self.assertLess(bm.state["hp"][target], before)
        self.assertTrue(all(row["target"] == target for row in runtime.incoming[-3:]))
        self.assertEqual([row["shot"] for row in runtime.incoming[-18:]], [531474] * 18)


if __name__ == "__main__":
    unittest.main()
