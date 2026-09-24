import json
import math
import sys
import unittest
from pathlib import Path
from types import SimpleNamespace

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "nikke-team-builder"))

from anomaly_mirror_indivilia import (
    IndiviliaMechanics,
    MirrorContainerMechanics,
    build_anomaly_mechanics,
)


DATA = json.loads((Path(__file__).parent / "raid-boss-combat-data.json").read_text(encoding="utf-8"))


def fake_runtime(key):
    profile = DATA["profiles"][key]
    return SimpleNamespace(
        key=key,
        time=0.0,
        functions={row["Id"]: row for row in profile["functions"]},
        world=SimpleNamespace(
            phase=1,
            part_hp={f"Weapon_{index:02d}": 1000 for index in range(1, 7)}
                    | {f"Weapon_{index:02d}": 4400 for index in range(7, 11)},
            parts=SimpleNamespace(parts={
                f"Weapon_{index:02d}": {"hp": 4400, "max_hp": 4400, "status": "alive"}
                for index in range(7, 11)
            }),
        ),
    )


def walk(node):
    yield node
    for child in node.get("Children", []):
        yield from walk(child)


class MirrorContainerMechanicsTests(unittest.TestCase):
    def setUp(self):
        self.runtime = fake_runtime("anomaly-mirror-container")
        self.mechanics = MirrorContainerMechanics(self.runtime)

    def test_source_has_six_phase_one_and_four_phase_two_slippers(self):
        parts = DATA["profiles"]["anomaly-mirror-container"]["parts"]
        rows = {_part["PartsType"]: _part for _part in parts}
        self.assertEqual([rows[f"Weapon{i:02d}"]["HpRatio"] for i in range(1, 7)], [1] * 6)
        self.assertEqual([rows[f"Weapon{i:02d}"]["HpRatio"] for i in range(7, 11)], [44] * 4)
        self.assertEqual([rows[f"Weapon{i:02d}"]["DefenceRatio"] for i in range(7, 11)], [0] * 4)
        self.assertTrue(all(rows[f"Weapon{i:02d}"]["PassiveSkillId"] == 7451004 for i in range(1, 11)))

    def test_native_close_open_and_first_hit_gate(self):
        self.assertTrue(self.mechanics.apply_function(1999680))
        self.assertFalse(self.mechanics.part_targetable("Weapon_01", 10))

        self.runtime.time = 10
        self.assertTrue(self.mechanics.apply_function(1999700))
        self.assertFalse(self.mechanics.part_targetable("Weapon_01", 10))
        self.assertTrue(self.mechanics.part_targetable("Weapon_01", 10.01))

        self.mechanics.on_part_hit("Weapon_01", 10.5, 1)
        self.assertFalse(self.mechanics.part_targetable("Weapon_01", 15.499))
        self.assertTrue(self.mechanics.part_targetable("Weapon_01", 15.5))
        self.assertEqual(self.mechanics.hit_count["Weapon_01"], 1)

    def test_hurt_count_cancels_phase_two_attack_without_part_break(self):
        skill = dict(CancelType="BrokenPartsHurtCount", ControlParts=["Weapon07"])
        state = dict(started=20, parts=["Weapon_07"])
        # Native InitSkill snapshots the lifetime HurtCount and requires
        # current + ControlGauge.  A hit from an earlier attack therefore
        # cannot cancel this one even though PartsData itself is cumulative.
        self.mechanics.on_part_hit("Weapon_07", 19, 1)
        self.assertFalse(self.mechanics.attack_cancelled(skill, state, 20))
        self.mechanics.on_part_hit("Weapon_07", 20.25, 1)
        self.assertTrue(self.mechanics.attack_cancelled(skill, state, 20.25))
        self.assertIsNone(self.mechanics.attack_cancelled(dict(CancelType="BrokenParts"), state, 20.25))

    def test_repair_starts_a_new_one_hit_lifetime(self):
        self.mechanics.on_part_hit("Weapon_07", 1, 100)
        self.mechanics.on_part_repaired("Weapon_07", 2)
        self.assertEqual(self.mechanics.hit_count["Weapon_07"], 0)
        self.assertEqual(self.mechanics.last_hit["Weapon_07"], float("-inf"))

    def test_four_independent_defence_layers_only_drop_on_user_break(self):
        self.mechanics.on_phase_changed(2, 5)
        expected = [1.9, 2.8, 3.7, 4.6]
        for ident, multiplier in zip((1999664, 1999665, 1999666, 1999667), expected):
            self.assertTrue(self.mechanics.apply_function(ident))
            self.assertAlmostEqual(self.mechanics.defence_multiplier(5), multiplier)

        self.mechanics.on_part_broken("Weapon_07", 6, by_squad=False)
        self.assertAlmostEqual(self.mechanics.defence_multiplier(6), 4.6)
        self.mechanics.on_part_broken("Weapon_07", 6, by_squad=True)
        self.assertAlmostEqual(self.mechanics.defence_multiplier(6), 3.7)

    def test_each_slipper_uses_its_native_part_defence_ratio(self):
        rows = {part["PartsType"]: part for part in DATA["profiles"]["anomaly-mirror-container"]["parts"]}
        self.runtime.world.rows = {
            "Weapon_01": rows["Weapon01"],
            "Weapon_07": rows["Weapon07"],
        }
        self.assertEqual(self.mechanics.part_defence_multiplier("Weapon_01"), 1)
        self.assertEqual(self.mechanics.part_defence_multiplier("Weapon_07"), 0)

    def test_hp_functions_add_then_remove_native_additive_max_hp_groups(self):
        current = self.runtime.world.parts.parts["Weapon_07"]
        current["hp"] = 2200
        self.assertTrue(self.mechanics.apply_function(1999602))
        self.assertEqual(self.runtime.world.part_hp["Weapon_07"], 6776)
        self.assertEqual(current["hp"] / current["max_hp"], .5)
        self.assertEqual(self.mechanics.hp_ui_functions, {1999603, 1999604})

        self.assertTrue(self.mechanics.apply_function(1999736))
        self.assertEqual(self.runtime.world.part_hp["Weapon_07"], 5324)
        self.runtime.time = .01
        self.mechanics.advance(.01)
        self.assertEqual(self.runtime.world.part_hp["Weapon_07"], 5324)

        self.assertTrue(self.mechanics.apply_function(1999744))
        self.runtime.time = .02
        self.mechanics.advance(.02)
        self.assertEqual(self.runtime.world.part_hp["Weapon_07"], 4400)
        self.assertEqual(current["hp"] / current["max_hp"], .5)

    def test_hp_groups_are_part_local_and_use_native_integer_rounding(self):
        self.runtime.world.part_hp["Weapon_07"] = 101
        self.runtime.world.parts.parts["Weapon_07"].update(hp=50, max_hp=101)
        self.mechanics.base_part_hp["Weapon_07"] = 101
        self.assertTrue(self.mechanics.apply_function(1999602))
        self.assertEqual(self.runtime.world.part_hp["Weapon_07"], 156)
        self.assertEqual(self.runtime.world.parts.parts["Weapon_07"]["hp"], 77)
        self.assertEqual(self.runtime.world.part_hp["Weapon_08"], 4400)
        self.assertEqual(self.mechanics.hp_groups["Weapon_08"], {})

    def test_collapsed_cinematic_expires_hp_groups_and_rebases_function_deadlines(self):
        self.runtime.time = 10
        self.mechanics.on_part_hit("Weapon_07", 10, 1)
        self.assertTrue(self.mechanics.apply_function(1999602))
        self.assertTrue(self.mechanics.apply_function(1999736))
        self.assertEqual(self.runtime.world.part_hp["Weapon_07"], 5324)
        hit_count = self.mechanics.hit_count["Weapon_07"]
        last_hit = self.mechanics.last_hit["Weapon_07"]

        # The 1 cs replacement expires during a cutscene whose wall time is
        # collapsed out of the battle clock.  Permanent groups survive and
        # all surviving absolute deadlines move back by that collapsed span.
        self.mechanics.advance_cinematic_functions(20)
        self.mechanics.rebase_cinematic_functions(10)
        self.assertEqual(self.runtime.world.part_hp["Weapon_07"], 5324)
        self.assertNotIn(1999602, self.mechanics.hp_groups["Weapon_07"])
        self.assertEqual(self.mechanics.immune_until["Weapon_07"], 5)
        self.assertEqual(self.mechanics.hit_count["Weapon_07"], hit_count)
        self.assertEqual(self.mechanics.last_hit["Weapon_07"], last_hit)

    def test_repaired_slipper_is_full_at_active_adjusted_maximum(self):
        self.assertTrue(self.mechanics.apply_function(1999602))
        current = self.runtime.world.parts.parts["Weapon_07"]
        current.update(hp=0, max_hp=self.runtime.world.part_hp["Weapon_07"], status="destroyed")
        # BossWorld repairs at the current damage-stage base, then dispatches
        # on_part_repaired; active function groups must be reapplied to that
        # fresh lifetime at full HP.
        self.runtime.world.part_hp["Weapon_07"] = 4400
        current.update(hp=4400, max_hp=4400, status="alive")
        self.mechanics.on_part_repaired("Weapon_07", 1)
        self.assertEqual(current["max_hp"], 6776)
        self.assertEqual(current["hp"], 6776)

    def test_projectile_and_slipper_attack_traits_match_native_rows(self):
        opening = self.mechanics.attack_traits({"SkillAniNumber": "Shot01"})
        self.assertTrue(opening["destroyable"])
        self.assertEqual(opening["projectile_hp_ratio"], 10000)
        phase_two_missile = self.mechanics.attack_traits({"SkillAniNumber": "Shot18"})
        self.assertEqual(phase_two_missile["target"], "cover")
        self.assertEqual(phase_two_missile["splash_radius"], 200)
        self.assertFalse(phase_two_missile["iframeable"])
        slipper = self.mechanics.attack_traits({"SkillAniNumber": "Shot12"})
        self.assertEqual(slipper["cancelled_by"], "first_part_hit")

    def test_strongest_current_charged_shot_is_locked_for_attack_lifetime(self):
        self.runtime.world.attacks = {
            12: {"parts": ["Weapon_07"], "started": 2, "end": 8},
        }
        scores = {"alice": 100, "bob": 200}
        self.mechanics._charged_shot_score = lambda name, time: scores[name]
        self.assertEqual(
            self.mechanics.preferred_part_shooter(["alice", "bob"], "Weapon_07", 3),
            "bob",
        )
        scores.update(alice=300, bob=50)
        self.assertEqual(
            self.mechanics.preferred_part_shooter(["alice", "bob"], "Weapon_07", 4),
            "bob",
        )
        self.runtime.world.attacks = {
            13: {"parts": ["Weapon_07"], "started": 9, "end": 15},
        }
        self.assertEqual(
            self.mechanics.preferred_part_shooter(["alice", "bob"], "Weapon_07", 10),
            "alice",
        )

    def test_charged_shot_score_uses_live_attack_and_charge_buffs(self):
        class Buffs:
            state = {"full_burst": False}
            def get_weapon_change(self, name): return None
            def get_buffs(self, name, target, time):
                return {"atk_pct": 100 if name == "buffed" else 0, "crit_rate": 0}

        weapon = {"weapon_type": "SR", "damage_coeff": 100, "full_charge_mult": 250, "core_dmg_mult": 200}
        make = lambda name, attack: SimpleNamespace(
            name=name, base_atk=attack, weapon_type="SR", weapon=dict(weapon), muzzles=1,
            element_match=lambda bm: False,
        )
        self.runtime.bm = Buffs()
        self.runtime.char_states = {"plain": make("plain", 1000), "buffed": make("buffed", 700)}
        self.runtime.enemy_def = 0
        self.runtime.active_stat = lambda name, stat: 0
        self.mechanics.phase = 2
        self.assertGreater(
            self.mechanics._charged_shot_score("buffed", 5),
            self.mechanics._charged_shot_score("plain", 5),
        )


class IndiviliaMechanicsTests(unittest.TestCase):
    def setUp(self):
        self.runtime = fake_runtime("anomaly-indivilia")
        self.mechanics = IndiviliaMechanics(self.runtime)

    def test_source_phase_gate_and_parts_are_exact(self):
        profile = DATA["profiles"]["anomaly-indivilia"]
        rows = {_part["PartsType"]: _part for _part in profile["parts"]}
        self.assertEqual(set(rows), {"Body", "Weapon01", "Weapon02", "Weapon03", "Weapon04"})
        self.assertEqual(rows["Weapon03"]["HpRatio"], 600)
        self.assertEqual(rows["Weapon03"]["DamageHpRatio"], 200)
        self.assertEqual(rows["Weapon04"]["HpRatio"], 3000)
        gates = [node for node in walk(profile["trees"]["challenge"]) if node["Type"].endswith("CheckPhase")]
        self.assertEqual([(node["PhaseCheckType_type"], node["Single_phaseValue"]) for node in gates], [("BerserkStep", 8)])

    def test_transition_swaps_pincers_and_tail_for_blade(self):
        self.assertTrue(self.mechanics.part_targetable("Weapon_01", 0))
        self.assertTrue(self.mechanics.part_targetable("Weapon_03", 0))
        self.assertFalse(self.mechanics.part_targetable("Weapon_04", 0))
        self.mechanics.on_phase_changed(2, 60)
        self.assertFalse(self.mechanics.part_targetable("Weapon_03", 60))
        self.assertTrue(self.mechanics.part_targetable("Weapon_04", 60))
        self.assertNotIn("Weapon_05", self.mechanics.LABELS)
        self.assertEqual(self.mechanics.LABELS["Weapon_04"], "Blade")

    def test_tail_and_transformation_lasers_have_distinct_penetration(self):
        tail = self.mechanics.attack_traits({"SkillAniNumber": "Shot10"})
        self.assertEqual(tail["source_part"], "Weapon_03")
        self.assertEqual(tail["target"], "highest_attack")
        self.assertTrue(tail["bypass_cover"])
        self.assertTrue(tail["shieldable"])
        transform = self.mechanics.attack_traits({"SkillAniNumber": "Shot30"})
        self.assertTrue(transform["bypass_cover"])
        self.assertTrue(transform["bypass_shield"])
        self.assertFalse(transform["tauntable"])

    def test_destroyable_phase_two_missiles_keep_native_hp_ratio(self):
        traits = self.mechanics.attack_traits({"SkillAniNumber": "Shot19"})
        self.assertTrue(traits["destroyable"])
        self.assertEqual(traits["projectile_hp_ratio"], 300)
        self.assertEqual(traits["target"], "highest_attack")

    def test_edge_pierce_can_overlap_a_pincer_and_body(self):
        collide = self.mechanics.player_collision_targets
        self.assertEqual(collide("Weapon_01", 1, True), ("Weapon_01", "Body"))
        self.assertEqual(collide("Weapon_02", 5, True), ("Weapon_02", "Body"))
        self.assertEqual(collide("Weapon_01", 5, True), ("Weapon_01",))
        self.assertEqual(collide("Weapon_02", 1, True), ("Weapon_02",))
        self.assertEqual(collide("Weapon_01", 3, True), ("Weapon_01",))
        self.assertEqual(collide("Weapon_03", 1, True), ("Weapon_03",))
        self.mechanics.phase = 2
        self.assertEqual(collide("Weapon_01", 1, True), ("Weapon_01",))

    def test_suicide_add_routes_use_installed_points_and_tree_move_rates(self):
        from raid_boss_combat import RaidBossRuntime

        runtime = RaidBossRuntime([], 180, key="anomaly-indivilia")
        mechanics = runtime.anomaly
        expected = {177: 8.92, 178: 8.92, 179: 9.0}
        for row in runtime.data["calls"]:
            monster = mechanics._monster(row["MonsterId"])
            with self.subTest(call=row["Id"]):
                return_end = dict(zip(("x", "y", "z"),
                                      mechanics._return_end_position(row)))
                self.assertAlmostEqual(mechanics._entry_seconds(monster, row, return_end),
                                       expected[row["GroupId"]])
                route = mechanics._route(row)
                self.assertEqual(route[0], row["ActionPoint"])
                self.assertEqual(route[1], row["DirPoint"])
                self.assertTrue(all(point in mechanics.ROUTE_POINTS for point in route))

    def test_calling_wave_spawns_exact_offsets_and_native_add_stats(self):
        from raid_boss_combat import RaidBossRuntime

        runtime = RaidBossRuntime([], 180, key="anomaly-indivilia")
        runtime.time = 10
        skill = next(skill for skill in runtime.data["skills"] if skill["Id"] == 531457)
        self.assertTrue(runtime.anomaly.perform_skill(skill, {}))
        self.assertEqual([item["at"] for item in runtime.pending], [10, 10.3, 10.6, 10.9, 11.2])
        runtime.anomaly.advance(10)
        add = runtime.adds[0]
        monster = runtime.anomaly._monster(2210050635)
        self.assertEqual(add["skill"]["Id"], 100141)
        self.assertEqual(add["skill"]["SkillValue01"], 25700)
        hurt = runtime.hurt_functions(add["skill"], "character", monster=monster)
        self.assertEqual([(function["Id"], function["FunctionType"], function["FunctionValue"])
                          for function in hurt],
                         [(1999634, "CurrentHpRatioDamage", 5000)])
        self.assertEqual(add["defence"], runtime.stat(monster)["LevelDefence"] * 1.5)
        self.assertEqual(add["hp"], round(runtime.stat(monster)["LevelHp"] * .7))
        self.assertEqual(add["route"][:2], (303, 2789))
        self.assertEqual(add["teleport_from"], (-65.0, 15.0, 98.0))
        self.assertEqual(add["teleport_to"], (-25.0, 45.0, 63.0))
        self.assertEqual(add["position"], {"x": -65.0, "y": 15.0, "z": 98.0})
        self.assertAlmostEqual(add["teleport_at"], 10 + 3 * .017)
        self.assertAlmostEqual(add["spawn_action_completion"], 10 + 3.917)
        self.assertAlmostEqual(add["post_teleport_move_seconds"], 8.92)
        self.assertAlmostEqual(add["ready_at"], 10 + 3.917 + 8.92)
        self.assertAlmostEqual(add["return_end_position"]["x"], -17.083, delta=.01)
        self.assertIn("SetTeleport", add["timing_source"])

    def test_teleport_then_set_return_precedes_ai_route(self):
        from raid_boss_combat import RaidBossRuntime

        runtime = RaidBossRuntime([], 180, key="anomaly-indivilia")
        row = next(row for row in runtime.data["calls"] if row["GroupId"] == 177)
        runtime.anomaly._spawn_add(row, 0)
        add = runtime.adds[0]
        runtime.anomaly.advance(add["teleport_at"] - 1e-6)
        self.assertEqual(add["position"], {"x": -65.0, "y": 15.0, "z": 98.0})
        runtime.anomaly.advance(add["teleport_at"])
        self.assertEqual(add["position"], {"x": -25.0, "y": 45.0, "z": 63.0})
        runtime.anomaly.advance(.682)
        self.assertEqual(add["state"], "spawn-action")
        self.assertAlmostEqual(add["position"]["x"], -24.696, delta=.05)
        self.assertAlmostEqual(add["position"]["y"], 44.776, delta=.05)
        runtime.anomaly.advance(add["spawn_action_completion"] - 1e-6)
        self.assertEqual(add["state"], "spawn-action")
        self.assertAlmostEqual(add["position"]["x"], -17.083, delta=.02)
        runtime.anomaly.advance(add["spawn_action_completion"] + .1)
        self.assertEqual(add["state"], "approaching")
        self.assertGreater(add["position"]["x"], -17.083)

    def test_set_return_path_matches_independent_survivor_trace(self):
        from raid_boss_combat import RaidBossRuntime

        runtime = RaidBossRuntime([], 180, key="anomaly-indivilia")
        mechanics = runtime.anomaly
        row = next(row for row in runtime.data["calls"]
                   if row["ActionPoint"] == 304)
        self.assertEqual(mechanics.RETURN_TARGET, (0.0, 26.5, 59.0))
        for elapsed, observed in (
            (.550, (24.845, 44.885, 62.974)),
            (1.043, (23.882, 44.175, 62.820)),
            (1.540, (22.723, 43.315, 62.644)),
            (2.035, (21.578, 42.472, 62.459)),
        ):
            with self.subTest(elapsed=elapsed):
                point = mechanics._return_position_at(row, elapsed)
                actual = tuple(point[axis] for axis in ("x", "y", "z"))
                self.assertLess(math.dist(actual, observed), .08)

    def test_inner_return_gate_uses_installed_combat_pyramid(self):
        from raid_boss_combat import RaidBossRuntime

        runtime = RaidBossRuntime([], 180, key="anomaly-indivilia")
        mechanics = runtime.anomaly
        self.assertEqual(mechanics.COMBAT_ZONE_ORIGIN, (0.0, -4.0, 0.0))
        self.assertEqual(mechanics.COMBAT_ZONE_HEIGHT, 70.0)
        self.assertEqual(mechanics.COMBAT_ZONE_FAR, 100.0)
        for action in (305, 306):
            with self.subTest(action=action):
                row = next(row for row in runtime.data["calls"]
                           if row["ActionPoint"] == action)
                monster = mechanics._monster(row["MonsterId"])
                gate = mechanics._return_seconds(row, monster)
                self.assertAlmostEqual(gate, 4.743)
                before = mechanics._return_position_at(row, gate - .017, monster)
                at_gate = mechanics._return_position_at(row, gate, monster)
                self.assertFalse(mechanics._in_combat_zone(before))
                self.assertTrue(mechanics._in_combat_zone(at_gate))
                self.assertAlmostEqual(at_gate["y"], 38.732, delta=.05)

    def test_iscover_one_hurt_functions_apply_to_character_not_cover(self):
        from raid_boss_combat import RaidBossRuntime

        runtime = RaidBossRuntime([], 180, key="anomaly-indivilia")
        by_shot = {skill["SkillAniNumber"]: skill for skill in runtime.data["skills"]}
        for shot, expected in {
            "Shot01": [(1999631, "CurrentHpRatioDamage", 200)],
            "Shot05": [(1999539, "Damage", 60000), (1999633, "CurrentHpRatioDamage", 2000)],
            "Shot06": [(1999540, "Damage", 30000), (1999633, "CurrentHpRatioDamage", 2000)],
            "Shot07": [(1999540, "Damage", 30000), (1999633, "CurrentHpRatioDamage", 2000)],
            "Shot13": [(1999539, "Damage", 60000), (1999643, "CurrentHpRatioDamage", 5000)],
            "Shot14": [(1999539, "Damage", 60000), (1999643, "CurrentHpRatioDamage", 5000)],
            "Shot28": [(1999631, "CurrentHpRatioDamage", 200)],
        }.items():
            with self.subTest(shot=shot):
                character = [
                    (row["Id"], row["FunctionType"], row["FunctionValue"])
                    for row in runtime.hurt_functions(by_shot[shot], "character")
                    if row["FunctionType"] in ("Damage", "CurrentHpRatioDamage")
                ]
                cover = [
                    row for row in runtime.hurt_functions(by_shot[shot], "cover")
                    if row["FunctionType"] in ("Damage", "CurrentHpRatioDamage")
                ]
                self.assertEqual(character, expected)
                self.assertEqual(cover, [])

    def test_suicide_add_attacks_once_then_removes_itself(self):
        from raid_boss_combat import RaidBossRuntime

        runtime = RaidBossRuntime([], 180, key="anomaly-indivilia")
        received = []
        runtime.receive_attack = lambda *args, **kwargs: received.append((args, kwargs))
        row = next(row for row in runtime.data["calls"] if row["GroupId"] == 177)
        runtime.anomaly._spawn_add(row, 0)
        add = runtime.adds[0]
        runtime.anomaly.advance(add["next_attack"] - 1e-6)
        self.assertEqual(received, [])
        runtime.anomaly.advance(add["next_attack"])
        self.assertEqual(len(received), 1)
        self.assertEqual(received[0][0][0]["Id"], 100141)
        self.assertEqual(received[0][1]["source"], add["id"])
        self.assertEqual(add["state"], "self-destructed")
        self.assertEqual(add["hp"], 0)
        runtime.anomaly.advance(add["next_attack"] + 10)
        self.assertEqual(len(received), 1)

    def test_squad_fire_can_destroy_suicide_add_before_impact(self):
        from raid_boss_combat import RaidBossRuntime

        runtime = RaidBossRuntime([], 180, key="anomaly-indivilia")
        row = next(row for row in runtime.data["calls"] if row["GroupId"] == 179)
        runtime.anomaly._spawn_add(row, 0)
        add = runtime.adds[0]
        self.assertIs(runtime.anomaly.resolve_target("unit", "fire", "AR", True), add)
        result = runtime.anomaly.resolve_hit(add, add["hp"], {"is_normal_atk": True})
        self.assertTrue(result["handled"])
        self.assertTrue(result["destroyed"])
        self.assertEqual(result["boss_damage"], 0)
        self.assertEqual(runtime.damage_to_adds, add["max_hp"])


class FactoryTests(unittest.TestCase):
    def test_factory_is_scoped_to_two_anomaly_profiles(self):
        self.assertIsInstance(build_anomaly_mechanics(fake_runtime("anomaly-mirror-container")), MirrorContainerMechanics)
        self.assertIsInstance(build_anomaly_mechanics(fake_runtime("anomaly-indivilia")), IndiviliaMechanics)
        runtime = SimpleNamespace(key="anomaly-ultra", world=SimpleNamespace(phase=1))
        self.assertIsNone(build_anomaly_mechanics(runtime))


class RaidBossRuntimeIntegrationTests(unittest.TestCase):
    def test_qte_element_list_only_gates_hits_while_element_barrier_is_active(self):
        """Native QTE ElementIDList grants weakness; immunity is a boss function."""
        from raid_boss_combat import RaidBossRuntime

        runtime = RaidBossRuntime([], 180, key="anomaly-mirror-container")
        shot09 = next(skill for skill in runtime.data["skills"] if skill["Id"] == 520669)

        ordinary = runtime.ordinary_qte(shot09, 0, 3)
        self.assertTrue(all(target["element"] is None for target in runtime.states[ordinary]["event"]["targets"]))
        state = {}
        runtime.special_qte({"Int32_quickTimeId": 10159}, 0, state)
        self.assertTrue(all(target["element"] is None for target in runtime.states[state["qte"]]["event"]["graph"]))

        runtime.barrier = True
        ordinary = runtime.ordinary_qte(shot09, 1, 3)
        self.assertEqual({target["element"] for target in runtime.states[ordinary]["event"]["targets"]}, {"전격"})
        state = {}
        runtime.special_qte({"Int32_quickTimeId": 10159}, 1, state)
        self.assertEqual({target["element"] for target in runtime.states[state["qte"]]["event"]["graph"]}, {"전격"})

    def test_special_qte_copies_base_defence_without_function_layers(self):
        """Native QuickTimeEventContext copies the raw +0x318 DEF StatValue."""
        from raid_boss_combat import RaidBossRuntime

        runtime = RaidBossRuntime([], 180, key="anomaly-mirror-container")
        runtime.world.phase = 2
        runtime.anomaly.on_phase_changed(2, 0)
        for function_id in range(1999664, 1999668):
            runtime.apply_function(function_id)

        state = {}
        runtime.special_qte({"Int32_quickTimeId": 10159}, 0, state)
        targets = runtime.states[state["qte"]]["event"]["graph"]
        base_defence = (
            runtime.stat()["LevelDefence"]
            * runtime.data["monster"]["DefenceRatio"]
            / 10000
        )
        self.assertEqual({target["def"] for target in targets}, {base_defence})
        self.assertAlmostEqual(runtime.anomaly.defence_multiplier(0), 4.6)
        self.assertLess(targets[0]["def"], base_defence * runtime.anomaly.defence_multiplier(0))

    def test_ordinary_break_qte_retains_body_defence_fallback(self):
        """Break colliders use get_BreakColDefence, including ordinary StatDef."""
        from raid_boss_combat import RaidBossRuntime

        runtime = RaidBossRuntime([], 180, key="anomaly-mirror-container")
        runtime.world.phase = 2
        runtime.anomaly.on_phase_changed(2, 0)
        for function_id in range(1999664, 1999668):
            runtime.apply_function(function_id)
        shot16 = next(skill for skill in runtime.data["skills"] if skill["Id"] == 520676)

        ident = runtime.ordinary_qte(shot16, 0, 3)
        targets = runtime.states[ident]["event"]["targets"]
        self.assertTrue(targets)
        self.assertTrue(all("def" not in target for target in targets))
        self.assertAlmostEqual(runtime.anomaly.defence_multiplier(0), 4.6)

    def test_repairs_recompute_native_part_hp_at_every_damage_stage(self):
        from boss_behavior import SUCCESS
        from boss_parts import part_max_hp
        from raid_boss_combat import RaidBossRuntime

        # Indivilia's LevelBrokenHp changes at steps 4, 5, 6, 7 and 8.  A
        # repaired part is reconstructed from the current step, rather than
        # retaining its battle-start maximum.
        probe_parts = {
            "anomaly-indivilia": "Weapon_03",
            "anomaly-mirror-container": "Weapon_07",
        }
        for key, part in probe_parts.items():
            template = RaidBossRuntime([], 180, key=key)
            for stage in template.stages[:8]:
                with self.subTest(boss=key, step=stage["Step"]):
                    runtime = RaidBossRuntime([], 180, key=key)
                    runtime.damage = stage["ConditionValueMin"]
                    if key == "anomaly-mirror-container":
                        runtime.world.phase = 2
                        runtime.anomaly.on_phase_changed(2, 0)
                        runtime.apply_function(1999602)
                    runtime.world.parts.self_destruct(part, 0)
                    node = {
                        "Type": "RepairPartsVer3",
                        "List`1_partsList": [part],
                        "Single_repairTime": 0,
                    }
                    self.assertEqual(runtime.world.action(node, 1, {"started": 1}), SUCCESS)
                    base = part_max_hp(
                        runtime.stat(), runtime.data["monster"],
                        runtime.world.rows[part], runtime.world.main_part,
                    )
                    expected = (base * 154 + 50) // 100 if key == "anomaly-mirror-container" else base
                    if key == "anomaly-mirror-container":
                        self.assertEqual(runtime.anomaly.base_part_hp[part], base)
                    self.assertEqual(runtime.world.part_hp[part], expected)
                    self.assertEqual(runtime.world.parts.parts[part]["hp"], expected)

    def test_real_runtime_applies_and_persists_four_phase_two_defence_layers(self):
        from boss_behavior import SUCCESS
        from raid_boss_combat import RaidBossRuntime

        runtime = RaidBossRuntime([], 180, key="anomaly-mirror-container")
        runtime.world.phase = 2
        runtime.anomaly.on_phase_changed(2, 0)
        for shot in range(20, 24):
            node = {"ID": 9000 + shot, "Type": "Attack", "SkillAniNumberTypemSkillAniNumber": f"Shot_{shot:02d}"}
            self.assertEqual(runtime.world.action(node, 0, {"started": 0}), SUCCESS)
        self.assertEqual(runtime.anomaly.defence_layers, set(runtime.anomaly.PHASE_TWO_PARTS))
        self.assertAlmostEqual(runtime.anomaly.defence_multiplier(0), 4.6)

        runtime.world.action({"Type": "BrokenParts", "List`1_partsList": ["Weapon_07"]}, 1, {"started": 1})
        self.assertAlmostEqual(runtime.anomaly.defence_multiplier(1), 4.6)
        runtime.anomaly.on_part_broken("Weapon_07", 2, True)
        self.assertAlmostEqual(runtime.anomaly.defence_multiplier(2), 3.7)

    def test_phase_two_qte_pass_preserves_removed_layer_and_failure_restores_it(self):
        from boss_behavior import SUCCESS
        from raid_boss_combat import RaidBossRuntime

        runtime = RaidBossRuntime([], 180, key="anomaly-mirror-container")
        runtime.world.phase = 2
        runtime.anomaly.on_phase_changed(2, 0)
        for shot in range(20, 24):
            node = {"ID": 9100 + shot, "Type": "Attack", "SkillAniNumberTypemSkillAniNumber": f"Shot_{shot:02d}"}
            self.assertEqual(runtime.world.action(node, 0, {"started": 0}), SUCCESS)
        runtime.anomaly.on_part_broken("Weapon_07", 1, True)
        self.assertAlmostEqual(runtime.anomaly.defence_multiplier(1), 3.7)

        # Passed Shot16 takes selector fallback node 268: barrier-off Shot26
        # only, so no Shot20..23 layer is reapplied.
        off = {"ID": 9268, "Type": "Attack", "SkillAniNumberTypemSkillAniNumber": "Shot_26"}
        self.assertEqual(runtime.world.action(off, 2, {"started": 2}), SUCCESS)
        self.assertAlmostEqual(runtime.anomaly.defence_multiplier(2), 3.7)

        # Failed Shot16 continues nodes 255..259 and explicitly reapplies all
        # four layer skills before resetting the cycle variables.
        for shot in range(20, 24):
            node = {"ID": 9200 + shot, "Type": "Attack", "SkillAniNumberTypemSkillAniNumber": f"Shot_{shot:02d}"}
            self.assertEqual(runtime.world.action(node, 3, {"started": 3}), SUCCESS)
        self.assertAlmostEqual(runtime.anomaly.defence_multiplier(3), 4.6)

    def test_real_runtime_first_hit_cancels_phase_two_slipper_before_break(self):
        from boss_behavior import RUNNING, SUCCESS
        from raid_boss_combat import RaidBossRuntime

        runtime = RaidBossRuntime([], 180, key="anomaly-mirror-container")
        runtime.world.phase = 2
        runtime.anomaly.on_phase_changed(2, 0)
        runtime.apply_function(1999700)
        runtime.time = 0.1
        part = "Weapon_07"
        runtime.select_part = lambda caster: part
        node = {"ID": 9912, "Type": "Attack", "SkillAniNumberTypemSkillAniNumber": "Shot_12"}
        state = {"started": 0.1}
        self.assertEqual(runtime.world.action(node, 0.1, state), RUNNING)
        before = runtime.world.parts.parts[part]["hp"]
        runtime.resolve(
            "unit", "전격", "SR", {"is_normal_atk": True},
            lambda **kwargs: {"damage": 1, "is_crit": False, "crit_frac": 0},
            {"enemy_def": 0, "hit_type": {"is_normal_atk": True}},
        )
        self.assertEqual(runtime.world.parts.parts[part]["hp"], before - 1)
        self.assertTrue(runtime.world.parts.alive(part))
        self.assertEqual(runtime.world.action(node, 0.2, state), SUCCESS)
        self.assertFalse(any(event.get("shot") == "Shot12" and event["event"] == "boss skill activated" for event in runtime.events))

    def test_real_timeline_hit_after_first_marker_cancels_remaining_slipper_markers(self):
        from boss_behavior import RUNNING, SUCCESS
        from raid_boss_combat import RaidBossRuntime

        runtime = RaidBossRuntime([], 180, key="anomaly-mirror-container")
        runtime.world.phase = 2
        runtime.anomaly.on_phase_changed(2, 0)
        runtime.time = 0
        runtime.apply_function(1999700)
        part = "Weapon_07"
        runtime.select_part = lambda caster: part
        node = {
            "ID": 9913,
            "Type": "TimelineSkill",
            "List`1_aniNumberTypes": ["Shot_12"],
            "BooleanFailueCheck": False,
        }
        state = {"started": 0.1}
        self.assertEqual(runtime.world.action(node, 0.1, state), RUNNING)
        first = state["impacts"][0]
        runtime.time = first
        self.assertEqual(runtime.world.action(node, first, state), RUNNING)
        self.assertEqual(state["fired"], 1)

        runtime.resolve(
            "unit", "전격", "SR", {"is_normal_atk": True},
            lambda **kwargs: {"damage": 1, "is_crit": False, "crit_frac": 0},
            {"enemy_def": 0, "hit_type": {"is_normal_atk": True}},
        )
        runtime.time = first + .01
        self.assertEqual(runtime.world.action(node, runtime.time, state), SUCCESS)
        runtime.time = max(state["impacts"]) + .01
        self.assertEqual(
            len([event for event in runtime.events if event.get("shot") == "Shot12" and event["event"] == "boss skill activated"]),
            1,
        )
        cancel = next(event for event in runtime.events if event["event"] == "part hit cancelled attack")
        self.assertEqual(cancel["markers_fired"], 1)

    def test_real_indivilia_runtime_changes_targetable_parts_at_transition(self):
        from raid_boss_combat import RaidBossRuntime

        runtime = RaidBossRuntime([], 180, key="anomaly-indivilia")
        self.assertTrue(runtime.anomaly.part_targetable("Weapon_03", 0))
        self.assertFalse(runtime.anomaly.part_targetable("Weapon_04", 0))
        runtime.world.action({"Type": "isPhaseAction"}, 10, {"started": 10})
        self.assertEqual(runtime.world.phase, 2)
        self.assertFalse(runtime.anomaly.part_targetable("Weapon_03", 10))
        self.assertTrue(runtime.anomaly.part_targetable("Weapon_04", 10))

    def test_bound_runtime_commits_indivilia_transition_on_cinematic_completion(self):
        from boss_behavior import RUNNING
        from raid_boss_combat import RaidBossRuntime

        runtime = RaidBossRuntime([], 180, key="anomaly-indivilia")
        runtime.bm = SimpleNamespace()
        state = {"started": 10}
        self.assertEqual(runtime.world.action({"Type": "isPhaseAction"}, 10, state), RUNNING)
        self.assertEqual(runtime.world.phase, 1)
        self.assertEqual(runtime.pending_phase, 2)
        seconds = runtime.phase_cinematics[-1]["seconds"]
        runtime.finish_cinematic_time(seconds)
        self.assertEqual(runtime.world.phase, 2)
        self.assertIsNone(runtime.pending_phase)
        self.assertFalse(runtime.anomaly.part_targetable("Weapon_03", 10))
        self.assertTrue(runtime.anomaly.part_targetable("Weapon_04", 10))


if __name__ == "__main__":
    unittest.main()
