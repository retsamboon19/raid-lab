"""Regression tests for extracted Anomaly timing rules."""
import json
import unittest

from anomaly_timing import (
    DATA,
    combat_zone_contains,
    marker_kind,
    move_distance,
    move_duration,
    move_reached,
    move_speed_step,
    ordinary_fire_record,
    ordinary_fire_schedule,
    phase_action_status,
    phase_duration,
    phase_stops_spot_tick,
    profile_timeline_schedule,
)


class AnomalyTimingTests(unittest.TestCase):
    def test_ordinary_action_end_includes_native_shot_and_animation_tails(self):
        cases = {
            ("anomaly-mirror-container", 520661): 1.2666667103767396,
            ("anomaly-indivilia", 531474): 0.0,
            ("anomaly-ultra", 510632): 2.0,
            ("anomaly-ultra", 510633): 2.0,
            ("anomaly-harvester", 510130): 4.4666666984558105,
        }
        for (profile, skill_id), expected in cases.items():
            with self.subTest(profile=profile, skill_id=skill_id):
                schedule = ordinary_fire_schedule(profile, skill_id)
                self.assertAlmostEqual(schedule["action_end"], expected)
                self.assertEqual(schedule["end"], max(schedule["impacts"]))

    def test_ordinary_action_end_respects_absolute_start(self):
        schedule = ordinary_fire_schedule(
            "anomaly-harvester", 510130, start=12.5)
        self.assertAlmostEqual(schedule["action_end"],
                               12.5 + 4.4666666984558105)

    def test_indivilia_shot01_uses_constructed_skill_casting_time(self):
        row = ordinary_fire_record("anomaly-indivilia", 531456)
        self.assertEqual(row["table_casting_seconds"], 0)
        self.assertAlmostEqual(row["effective_casting_seconds"], 0.8)
        schedule = ordinary_fire_schedule("anomaly-indivilia", 531456, start=10)
        self.assertEqual(len(schedule["impacts"]), 15)
        self.assertTrue(all(abs(impact - 10.8) < 1e-6
                            for impact in schedule["impacts"]))
        self.assertAlmostEqual(schedule["action_end"], 11.8)

    def test_indivilia_jump_animation_uses_native_clip_durations(self):
        animation = DATA["profiles"]["anomaly-indivilia"]["jump_animation"]
        self.assertAlmostEqual(animation["start_seconds"], 0.7666667103767395)
        self.assertAlmostEqual(animation["end_seconds"], 1.2666668891906738)

    def test_public_evidence_has_no_machine_absolute_paths(self):
        serialized = json.dumps(DATA)
        self.assertNotRegex(serialized, r"[A-Za-z]:\\")

    def test_clone_suffixes_are_normalized_repeatedly(self):
        self.assertEqual(marker_kind("SpotMonster/Attack(Clone)(Clone)(Clone)"), "Attack")

    def test_ultra_shot04_uses_cloned_loop_markers(self):
        schedule = profile_timeline_schedule("anomaly-ultra", 4)
        self.assertAlmostEqual(schedule["loop"]["shift_seconds"], 3.5)
        self.assertAlmostEqual(schedule["impacts"][0], 6.966666666666667)
        self.assertAlmostEqual(schedule["end"], 8.866666666667)

    def test_mirror_loop_replays_attack_markers(self):
        schedule = profile_timeline_schedule("anomaly-mirror-container", 12)
        self.assertEqual(len(schedule["impacts"]), 10)
        self.assertAlmostEqual(schedule["impacts"][0], 2.716666666666667)
        self.assertAlmostEqual(schedule["impacts"][5], 5.05)
        self.assertAlmostEqual(schedule["end"], 11.166666666665666)

    def test_zero_casting_time_uses_loop_start_as_native_fallback(self):
        schedule = profile_timeline_schedule("anomaly-ultra", 2)
        self.assertAlmostEqual(schedule["loop"]["casting_seconds"], 1.5)
        self.assertAlmostEqual(schedule["impacts"][0], 4.116666666666664)
        self.assertAlmostEqual(schedule["end"], 7.6)

    def test_harvester_generic_marker_names_preserve_five_targets(self):
        shot4 = profile_timeline_schedule("anomaly-harvester", 4)
        self.assertEqual([event["target"] for event in shot4["impact_events"]], [1, 2, 3, 4, 5])
        self.assertAlmostEqual(shot4["impacts"][0], 1.2666666666666666)
        shot5 = profile_timeline_schedule("anomaly-harvester", 5)
        self.assertEqual([event["target"] for event in shot5["impact_events"]], [1, 2, 3, 4, 5])
        self.assertAlmostEqual(shot5["impacts"][0], 4.383333333333333)

    def test_ordinary_projectile_divisors_preserve_native_two_stage_split(self):
        row = ordinary_fire_record("anomaly-mirror-container", 520661)
        self.assertEqual(row["weapon_prefab_count"], 2)
        self.assertEqual(row["muzzle_count"], 2)
        self.assertEqual(row["shot_count"], 5)
        self.assertEqual(row["physical_hit_count"], 10)
        self.assertEqual(row["damage_ratio_divisor"], 2)
        self.assertEqual(row["damage_coefficient_raw"], 600)
        self.assertEqual(row["damage_shot_count"], 1)
        self.assertEqual(row["per_hit_damage_ratio_raw"], 600)
        self.assertEqual(row["projectile_hp_ratio_divisor"], 10)
        self.assertEqual(row["per_projectile_hp_ratio_raw"], 1000)

    def test_harvester_shot02_has_seven_active_source_muzzles(self):
        row = ordinary_fire_record("anomaly-harvester", 510129)
        self.assertEqual(row["shot_timing"], "Concurrence")
        self.assertEqual(row["weapon_prefab_count"], 1)
        self.assertEqual(row["muzzle_count"], 7)
        self.assertTrue(row["all_weapon_components_enabled"])
        self.assertTrue(row["all_weapon_gameobjects_active"])
        self.assertEqual(
            [muzzle["name"] for muzzle in row["weapon_prefabs"][0]["muzzles"]],
            [
                "socket_muzzle_fire_03 2", "socket_muzzle_fire_05",
                "socket_muzzle_fire_06", "socket_muzzle_fire_04 1",
                "socket_muzzle_fire_01 2", "socket_muzzle_fire_02 2",
                "socket_muzzle_fire_11",
            ],
        )
        self.assertEqual(ordinary_fire_schedule("anomaly-harvester", 510129)["impacts"], [0] * 7)
        schedule = ordinary_fire_schedule("anomaly-harvester", 510129)
        self.assertEqual(schedule["damage_ratio_divisor"], 7)
        self.assertEqual(schedule["damage_coefficient_raw"], 286)
        self.assertEqual(schedule["damage_shot_count"], 1)

    def test_sequence_delay_is_per_physical_prefab_muzzle_fire(self):
        mirror = ordinary_fire_schedule("anomaly-mirror-container", 520668)
        self.assertEqual(len(mirror["impacts"]), 12)
        self.assertAlmostEqual(mirror["impacts"][-1], 1.1)
        self.assertEqual(mirror["damage_ratio_divisor"], 2)
        self.assertEqual(mirror["damage_coefficient_raw"], 550)
        self.assertEqual(mirror["damage_shot_count"], 6)
        ultra = ordinary_fire_schedule("anomaly-ultra", 510631)
        self.assertEqual(len(ultra["impacts"]), 20)
        self.assertAlmostEqual(ultra["impacts"][1], .1)
        self.assertAlmostEqual(ultra["impacts"][-1], 1.9)

    def test_destroyed_part_names_filter_weapon_prefabs_before_division(self):
        row = ordinary_fire_record("anomaly-ultra", 510632)
        self.assertEqual(row["weapon_prefabs"][0]["parts_type"], 14)
        self.assertEqual(row["weapon_prefabs"][0]["parts_type_enum"], "Weapon_02")
        self.assertEqual(row["weapon_prefabs"][0]["parts_type_name"], "Weapon02")
        by_name = ordinary_fire_schedule(
            "anomaly-ultra", 510632, destroyed_parts={"Weapon02"}
        )
        by_number = ordinary_fire_schedule(
            "anomaly-ultra", 510632, destroyed_parts={14}
        )
        self.assertEqual(by_name["impacts"], [])
        self.assertEqual(by_number["impacts"], [])
        self.assertEqual(by_name["damage_ratio_divisor"], 0)

    def test_projectile_damage_coefficient_is_rounded_before_impact(self):
        row = ordinary_fire_record("anomaly-harvester", 510130)
        self.assertEqual(row["muzzle_count"], 8)
        self.assertEqual(row["skill_value01_raw"], 2500)
        self.assertEqual(row["damage_coefficient_raw"], 313)
        self.assertEqual(row["damage_shot_count"], 1)

    def test_move_geometry_and_speed_scaling(self):
        points = DATA["profiles"]["anomaly-mirror-container"]["points"]
        self.assertEqual(move_distance(points["254"], points["251"], True), 10)
        self.assertFalse(combat_zone_contains(points["254"]))
        self.assertFalse(combat_zone_contains(points["251"]))
        self.assertFalse(move_reached(points["254"], points["251"], 1, True))
        self.assertAlmostEqual(move_speed_step(0, 150, 5, 400, .02), .6)
        self.assertAlmostEqual(move_duration(10, 1, 150, 5, 400), 1.44)
        self.assertAlmostEqual(move_duration(10, 1, 150, 3, 400), 2.24)

    def test_indivilia_jump_destination_is_authored_wave_point(self):
        points = DATA["profiles"]["anomaly-indivilia"]["points"]
        self.assertEqual(points["153"], {"x": 0.0, "y": 5.6, "z": 60.0})

    def test_phase_action_waits_for_playback_and_always_finishes_failure(self):
        self.assertEqual(phase_action_status(2, 1, timeline_playing=True), "running")
        self.assertEqual(phase_action_status(2, 1, timeline_playing=False), "failure")
        self.assertEqual(phase_action_status(2, 2, timeline_playing=True), "failure")
        self.assertAlmostEqual(phase_duration("anomaly-indivilia"), 8.966666666666667)
        self.assertAlmostEqual(phase_duration("anomaly-harvester"), 1 / 60)

    def test_only_indivilia_phase_stops_the_spot_tick_graph(self):
        self.assertFalse(phase_stops_spot_tick("anomaly-ultra"))
        self.assertTrue(phase_stops_spot_tick("anomaly-indivilia"))
        self.assertFalse(phase_stops_spot_tick("anomaly-mirror-container"))
        self.assertFalse(phase_stops_spot_tick("anomaly-harvester"))


if __name__ == "__main__":
    unittest.main()
