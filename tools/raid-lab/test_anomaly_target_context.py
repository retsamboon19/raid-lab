import sys
import random
import unittest
from pathlib import Path
from types import SimpleNamespace

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "nikke-team-builder"))

from calculator.buff_manager import BuffManager
import core
from anomaly_target_context import (
    all_monster_targetable,
    damage_args_for_target,
    direct_skill_enemy_targets,
    enemy_attack_for_target,
    native_instant_circle_capsule,
    native_skill_excluded_layers,
    native_skill_target_condition,
    native_skill_range_geometry,
    select_enemy_effect_targets,
)


class FakeBuffManager:
    def __init__(self, active=()):
        self._active = list(active)

    @staticmethod
    def _get_value(effect, active, recipient, stack_override=None):
        return effect["value"] * (active.stack if stack_override is None else stack_override)

    @staticmethod
    def _runtime_condition_ok(conditions, owner, caster, recipient, time):
        return "runtime_false" not in conditions


def active(stat, value, target="enemies_target:1", activated=5, expires=20,
           *, runtime_conditions=(), per_target_stack=None):
    return SimpleNamespace(
        effect={
            "stat": stat,
            "value": value,
            "target": target,
            "trigger": {"condition": list(runtime_conditions)},
        },
        caster="support",
        target_chars=["__enemy__"],
        activated_at=activated,
        expires_at=expires,
        stack=1,
        per_char_stacks=(
            {"__enemy__": per_target_stack, "attacker": 99}
            if per_target_stack is not None else {}
        ),
        has_runtime_conditions=bool(runtime_conditions),
    )


class TargetContextTests(unittest.TestCase):
    def setUp(self):
        self.args = {
            "buffs": {
                "atk_pct": 40,
                "enemy_def_down_pct": -30,
                "received_dmg": 50,
                "part_dmg_pct": 25,
            },
            "enemy_def": 1000,
        }

    def test_boss_parts_and_ordinary_break_objects_keep_boss_effects(self):
        runtime = SimpleNamespace(time=10, bm=FakeBuffManager())
        for kind in ("boss", "part", "ordinary_break"):
            with self.subTest(kind=kind):
                result = damage_args_for_target(self.args, "attacker", kind, runtime)
                self.assertEqual(result["buffs"]["enemy_def_down_pct"], -30)
                self.assertEqual(result["buffs"]["received_dmg"], 50)

    def test_projectiles_and_special_qte_have_independent_status(self):
        runtime = SimpleNamespace(time=10, bm=FakeBuffManager())
        for kind in ("projectile", "special_qte"):
            with self.subTest(kind=kind):
                result = damage_args_for_target(self.args, "attacker", kind, runtime)
                self.assertEqual(result["buffs"]["enemy_def_down_pct"], 0)
                self.assertEqual(result["buffs"]["received_dmg"], 0)
                self.assertEqual(result["buffs"]["atk_pct"], 40)
                self.assertEqual(result["buffs"]["part_dmg_pct"], 25)

    def test_add_keeps_only_all_enemy_effects_activated_during_its_lifetime(self):
        runtime = SimpleNamespace(
            time=10,
            bm=FakeBuffManager([
                active("def_pct", -20, target="enemies_target:1", activated=6),
                active("received_dmg_pct", 30, target="all_enemies", activated=6),
                active("def_pct", -10, target="all_enemies", activated=7),
                active("received_dmg_pct", 99, target="all_enemies", activated=3),
            ]),
        )
        result = damage_args_for_target(
            self.args, "attacker", "add", runtime, {"spawned": 5}
        )
        self.assertEqual(result["buffs"]["enemy_def_down_pct"], -10)
        self.assertEqual(result["buffs"]["received_dmg"], 30)

    def test_expired_and_currently_false_all_enemy_effects_do_not_apply(self):
        runtime = SimpleNamespace(
            time=10,
            bm=FakeBuffManager([
                active("def_pct", -10, target="all_enemies", expires=10),
                active("received_dmg_pct", 30, target="all_enemies",
                       runtime_conditions=("runtime_false",)),
            ]),
        )
        result = damage_args_for_target(
            self.args, "attacker", "add", runtime, {"spawned": 1}
        )
        self.assertEqual(result["buffs"]["enemy_def_down_pct"], 0)
        self.assertEqual(result["buffs"]["received_dmg"], 0)

    def test_all_enemy_stack_uses_enemy_recipient_key(self):
        runtime = SimpleNamespace(
            time=10,
            bm=FakeBuffManager([
                active("received_dmg_pct", 5, target="all_enemies",
                       activated=6, per_target_stack=3),
            ]),
        )
        result = damage_args_for_target(
            self.args, "attacker", "add", runtime, {"spawned": 5}
        )
        self.assertEqual(result["buffs"]["received_dmg"], 15)

    def test_unknown_target_kind_cannot_silently_inherit_boss_context(self):
        runtime = SimpleNamespace(time=10, bm=FakeBuffManager())
        with self.assertRaises(ValueError):
            damage_args_for_target(self.args, "attacker", "mystery", runtime)


class SnapshotSelectorTests(unittest.TestCase):
    def runtime(self):
        boss = {
            "Id": 1, "StatenhanceId": 10, "HpRatio": 10000,
            "AttackRatio": 10000, "DefenceRatio": 10000,
            "ElementId": [300001],
        }
        add_monster = {
            "Id": 2, "StatenhanceId": 20, "HpRatio": 10000,
            "AttackRatio": 10000, "DefenceRatio": 10000,
            "ElementId": [400001],
        }
        runtime = SimpleNamespace(
            time=1.0, damage=100, enemy_def=None, effects={}, functions={},
            data={"monster": boss, "monsters": [boss, add_monster]},
            adds=[{
                "id": "summon-0", "monster_id": 2, "hp": 200,
                "max_hp": 200, "spawned": 0.5, "defence": 500,
                "position": {"x": 0, "y": 0, "z": 20},
            }],
            rng=random.Random(42), coordinates={"x": 0, "y": 0, "z": 0},
            world=SimpleNamespace(coordinates={"x": 0, "y": 0, "z": 40}),
            squad_coordinates={"attacker": {"x": 10, "y": 0, "z": 0}},
            last_enemy_target_by_caster={"attacker": "summon-0"},
        )
        runtime.stat = lambda monster=None: (
            {"LevelHp": 1000, "LevelAttack": 100, "LevelDefence": 200}
            if (monster or boss)["Id"] == 1 else
            {"LevelHp": 200, "LevelAttack": 300, "LevelDefence": 500}
        )
        runtime.living_adds = lambda: [a for a in runtime.adds if a["hp"] > 0]
        runtime.anomaly_hook = lambda *args: None
        runtime.select_enemy_effect_targets = lambda effect, caster, now: (
            select_enemy_effect_targets(runtime, effect, caster, now))
        return runtime

    def test_rank_code_and_current_target_select_alive_entities(self):
        runtime = self.runtime()
        self.assertEqual(select_enemy_effect_targets(
            runtime, {"target": "enemies_top_atk:1"}, "attacker", 1),
            ["summon-0"])
        self.assertEqual(select_enemy_effect_targets(
            runtime, {"target": "enemies_lowest_def:1"}, "attacker", 1),
            ["__boss__"])
        self.assertEqual(select_enemy_effect_targets(
            runtime, {"target": "enemies_code:전격"}, "attacker", 1),
            ["summon-0"])
        self.assertEqual(select_enemy_effect_targets(
            runtime, {"target": "target"}, "attacker", 1),
            ["summon-0"])
        self.assertEqual(select_enemy_effect_targets(
            runtime, {"target": "enemies_nearest:1"}, "attacker", 1),
            ["summon-0"])

    def test_installed_direct_skill_none_target_preference_is_source_specific(self):
        runtime = self.runtime()
        runtime.data["monsters"][1]["Nonetarget"] = "None"
        runtime.data["monsters"][1]["Functionnonetarget"] = "NoAllMonster"
        runtime.adds[0]["attack"] = 900
        runtime.last_enemy_target_by_caster["헬름"] = "summon-0"
        self.assertEqual(native_skill_target_condition(
            {"source": "스킬3"}, "헬름"), "IncludeNoneTargetLast")
        self.assertEqual(native_skill_target_condition(
            {"source": "스킬3"}, "마나"), "None")
        self.assertEqual(select_enemy_effect_targets(
            runtime, {"target": "enemies_top_atk:1", "source": "스킬3"},
            "헬름", 1), ["__boss__"])
        # A function or hand-authored selector with no proven CharacterSkill
        # link keeps its existing roster; it does not borrow Helm's metadata.
        self.assertEqual(select_enemy_effect_targets(
            runtime, {"target": "enemies_top_atk:1"}, "헬름", 1),
            ["summon-0"])
        self.assertEqual(select_enemy_effect_targets(
            runtime, {"target": "target", "source": "스킬3"},
            "헬름", 1), ["summon-0"])
        self.assertEqual(select_enemy_effect_targets(
            runtime, {"target": "all_enemies", "source": "스킬3"},
            "헬름", 1), ["__boss__"])
        self.assertEqual(direct_skill_enemy_targets(runtime, "헬름", {
            "effect_target": "enemies_top_atk:1",
            "effect_source": "스킬3",
            "effect_name": "ranked Helm hit",
        }), ["__boss__"])

    def test_last_priority_changes_only_for_include_last_skill(self):
        runtime = self.runtime()
        runtime.data["monsters"][1]["Nonetarget"] = "Last"
        runtime.adds[0]["attack"] = 900
        self.assertEqual(select_enemy_effect_targets(
            runtime, {"target": "enemies_top_atk:1", "source": "스킬3"},
            "헬름", 1), ["summon-0"])
        self.assertEqual(select_enemy_effect_targets(
            runtime, {"target": "enemies_top_atk:1", "source": "스킬3"},
            "마나", 1), ["__boss__"])

    def test_exact_nested_skill_id_can_include_none_target(self):
        runtime = self.runtime()
        runtime.data["monsters"][1]["Nonetarget"] = "None"
        runtime.adds[0]["attack"] = 900
        nested = {"source": "스킬2", "native_skill_id": 1322201}
        self.assertEqual(native_skill_target_condition(
            nested, "마르차나 : 마린 스터디"), "IncludeNoneTargetNone")
        self.assertIsNone(native_skill_target_condition(
            {"source": "스킬2"}, "마르차나 : 마린 스터디"))
        self.assertEqual(select_enemy_effect_targets(
            runtime, {"target": "enemies_top_atk:1", **nested},
            "마르차나 : 마린 스터디", 1), ["summon-0"])
        self.assertEqual(select_enemy_effect_targets(
            runtime, {"target": "enemies_top_atk:1", "source": "스킬3"},
            "마나", 1), ["__boss__"])

    def test_in_range_uses_encounter_shooting_zone_membership(self):
        runtime = self.runtime()
        runtime.enemy_in_shooting_zone = (
            lambda _caster, entity_id: entity_id == "__boss__")
        self.assertEqual(select_enemy_effect_targets(
            runtime, {"target": "enemies_in_range"}, "attacker", 1),
            ["__boss__"])
        self.assertEqual(runtime.range_targeting_unresolved,
                         {"attacker:?:enemies_in_range": 1})

    def test_native_area_geometry_and_physical_range_provider(self):
        runtime = self.runtime()
        geometry = native_skill_range_geometry({"source": "스킬3"}, "드레이크")
        self.assertEqual(geometry["skill_type"], "InstantArea")
        self.assertEqual(geometry["range_diameter_cm"], 700)
        self.assertEqual(geometry["range_stat_id"], 191)
        self.assertEqual(geometry["base_cast_radius_m"], 3.5)
        self.assertNotIn("reach_cm", geometry)
        circle = native_skill_range_geometry({"source": "스킬3"}, "아니스")
        self.assertEqual(circle["skill_type"], "InstantCircle")
        self.assertEqual(circle["base_cast_radius_m"], 3.5)
        self.assertEqual(circle["circle_height_cm"], 0)
        self.assertEqual(circle["base_cast_height_m"], 0)
        self.assertNotIn("reach_cm", circle)
        seen = []
        def physical(_caster, entity_id, authored):
            seen.append((entity_id, authored))
            return entity_id == "summon-0"
        runtime.enemy_in_skill_range = physical
        selected = select_enemy_effect_targets(
            runtime, {"target": "enemies_in_range", "source": "스킬3"},
            "드레이크", 1)
        self.assertEqual(selected, ["summon-0"])
        self.assertEqual([entity_id for entity_id, _ in seen],
                         ["__boss__", "summon-0"])
        self.assertTrue(all(authored == geometry for _, authored in seen))
        self.assertFalse(hasattr(runtime, "range_targeting_unresolved"))

    def test_native_circle_capsule_uses_forward_and_adjusted_radius(self):
        # Installed Circle rows currently have zero height. The synthetic
        # nonzero height checks the separate native slot-3 endpoint term.
        geometry = {"skill_type": "InstantCircle", "base_cast_height_m": 2.4}
        capsule = native_instant_circle_capsule(
            geometry, {"x": 1, "y": -2, "z": 5}, adjusted_radius_m=4.25)
        self.assertEqual(capsule, {
            "endpoint_a": (1, -2, 9.25),
            "endpoint_b": (1, -2, 11.65),
            "radius_m": 4.25,
        })
        circle = native_skill_range_geometry({"source": "스킬3"}, "아니스")
        self.assertEqual(native_instant_circle_capsule(
            circle, (0, 0, 0), adjusted_radius_m=circle["base_cast_radius_m"]),
            {"endpoint_a": (0, 0, 3.5), "endpoint_b": (0, 0, 3.5),
             "radius_m": 3.5})
        with self.assertRaises(ValueError):
            native_instant_circle_capsule(
                {"skill_type": "InstantArea", "base_cast_height_m": 1},
                (0, 0, 0), adjusted_radius_m=1)

    def test_stigma_removes_only_projectile_layers(self):
        self.assertEqual(native_skill_excluded_layers(
            {"source": "스킬3"}, "도로시"), (8, 11))
        self.assertEqual(native_skill_excluded_layers(
            {"source": "스킬3"}, "아니스"), ())

    def test_nearest_in_range_filters_before_sort_and_reports_fallback(self):
        runtime = self.runtime()
        runtime.enemy_in_skill_range = (
            lambda _caster, entity_id, _geometry: entity_id == "__boss__")
        self.assertEqual(select_enemy_effect_targets(
            runtime, {"target": "enemies_nearest_in_range:1"}, "attacker", 1),
            ["__boss__"])
        del runtime.enemy_in_skill_range
        self.assertEqual(select_enemy_effect_targets(
            runtime, {"target": "enemies_nearest_in_range:1"}, "attacker", 1),
            ["summon-0"])
        self.assertEqual(runtime.range_targeting_unresolved,
                         {"attacker:?:enemies_nearest_in_range:1": 1})

    def test_activation_snapshot_does_not_migrate_and_refresh_is_per_entity(self):
        runtime = self.runtime()
        name = core.NAME_MAP["liter"]
        chars = [core.spec.build_char(name, core.default_build(), no_layer=True)]
        chars[0]["name"] = "attacker"
        bm = BuffManager(chars, {"encounter_runtime": runtime})
        runtime.bm = bm
        effect = {
            "type": "buff", "name": "selector regression",
            "stat": "received_dmg_pct", "fixed_value": 10,
            "target": "enemies_top_atk:1", "duration": 10,
            "max_stack": 1, "polarity": "harmful",
            "trigger": {"condition": []},
        }
        bm._activate(effect, "attacker", 1)
        active = bm._active[0]
        self.assertEqual(set(active.enemy_target_windows), {"summon-0"})

        # A stronger add spawned after activation does not inherit or steal it.
        runtime.adds.append({
            "id": "summon-1", "monster_id": 2, "hp": 200,
            "max_hp": 200, "spawned": 2, "attack": 900, "defence": 500,
        })
        runtime.time = 3
        old = damage_args_for_target(
            {"buffs": {"received_dmg": 10, "enemy_def_down_pct": 0}},
            "attacker", "add", runtime, runtime.adds[0])
        new = damage_args_for_target(
            {"buffs": {"received_dmg": 10, "enemy_def_down_pct": 0}},
            "attacker", "add", runtime, runtime.adds[1])
        self.assertEqual(old["buffs"]["received_dmg"], 10)
        self.assertEqual(new["buffs"]["received_dmg"], 0)

        # A real reapplication selects the new top-ATK entity.  It does not
        # extend the old entity's original expiry.
        bm._activate(effect, "attacker", 3)
        self.assertEqual(active.enemy_target_windows["summon-0"]["expires_at"], 11)
        self.assertEqual(active.enemy_target_windows["summon-1"]["expires_at"], 13)

    def test_all_enemy_snapshot_excludes_later_spawn_until_reapplication(self):
        runtime = self.runtime()
        first = select_enemy_effect_targets(
            runtime, {"target": "all_enemies"}, "attacker", 1)
        runtime.adds.append({
            "id": "summon-1", "monster_id": 2, "hp": 100,
            "max_hp": 100, "spawned": 2,
        })
        second = select_enemy_effect_targets(
            runtime, {"target": "all_enemies"}, "attacker", 3)
        self.assertEqual(first, ["__boss__", "summon-0"])
        self.assertEqual(second, ["__boss__", "summon-0", "summon-1"])

    def test_no_all_monster_excludes_only_all_monster_selection(self):
        runtime = self.runtime()
        no_all_monster = {
            "Id": 2210050635, "ElementId": [400001],
            "Functionnonetarget": "NoAllMonster",
            "Nonetarget": "Normal",
            "AttackRatio": 10000, "DefenceRatio": 10000,
        }
        runtime.data["monsters"].append(no_all_monster)
        runtime.adds[0]["monster_id"] = 2210050635
        runtime.adds[0]["attack"] = 900
        add = runtime.adds[0]
        self.assertFalse(all_monster_targetable(runtime, add))
        self.assertEqual(select_enemy_effect_targets(
            runtime, {"target": "all_enemies"}, "attacker", 1),
            ["__boss__"])
        # FunctionNoneTargetType is distinct from the skill/auto-target flag.
        self.assertEqual(select_enemy_effect_targets(
            runtime, {"target": "enemies_top_atk:1"}, "attacker", 1),
            ["summon-0"])
        self.assertEqual(select_enemy_effect_targets(
            runtime, {"target": "target"}, "attacker", 1),
            ["summon-0"])
        self.assertIsNone(direct_skill_enemy_targets(runtime, "attacker", {
            "effect_target": "all_enemies", "effect_name": "wide hit",
        }))
        self.assertEqual(direct_skill_enemy_targets(runtime, "attacker", {
            "effect_target": "same_target:wide hit", "effect_name": "follow-up",
        }), ["__boss__"])

    def test_no_all_monster_does_not_inherit_all_enemy_debuff(self):
        runtime = self.runtime()
        runtime.data["monsters"].append({
            "Id": 2210050636, "Functionnonetarget": "NoAllMonster",
        })
        runtime.adds[0]["monster_id"] = 2210050636
        runtime.time = 10
        runtime.bm = FakeBuffManager([active(
            "received_dmg_pct", 30, target="all_enemies", activated=6,
        )])
        result = damage_args_for_target(
            {"buffs": {"received_dmg": 30, "enemy_def_down_pct": 0}},
            "attacker", "add", runtime, runtime.adds[0],
        )
        self.assertEqual(result["buffs"]["received_dmg"], 0)

    def test_boss_immunity_does_not_discard_add_recipient(self):
        runtime = self.runtime()
        name = core.NAME_MAP["liter"]
        chars = [core.spec.build_char(name, core.default_build(), no_layer=True)]
        chars[0]["name"] = "attacker"
        bm = BuffManager(chars, {"encounter_runtime": runtime})
        runtime.bm = bm
        immunity = {
            "type": "buff", "name": "boss immunity", "stat": "debuff_immune",
            "fixed_value": 1, "target": "enemy", "duration": 10,
            "max_stack": 1, "polarity": "beneficial", "trigger": {"condition": []},
        }
        harmful = {
            "type": "buff", "name": "attack down", "stat": "atk_pct",
            "fixed_value": -20, "target": "all_enemies", "duration": 10,
            "max_stack": 1, "polarity": "harmful", "trigger": {"condition": []},
        }
        bm._activate(immunity, "attacker", 1)
        bm._activate(harmful, "attacker", 2)
        debuff = next(active for active in bm._active if active.effect is harmful)
        self.assertEqual(set(debuff.enemy_target_windows), {"summon-0"})
        runtime.time = 3
        self.assertEqual(enemy_attack_for_target(runtime, 100, "__boss__"), 100)
        self.assertEqual(enemy_attack_for_target(runtime, 100, "summon-0"), 80)

    def test_direct_ranked_damage_records_same_target_recipient(self):
        runtime = self.runtime()
        selected = direct_skill_enemy_targets(runtime, "attacker", {
            "effect_target": "enemies_top_atk:1", "effect_name": "ranked hit",
        })
        self.assertEqual(selected, ["summon-0"])
        runtime.last_enemy_target_by_caster["attacker"] = "__boss__"
        self.assertEqual(direct_skill_enemy_targets(runtime, "attacker", {
            "effect_target": "same_target:ranked hit", "effect_name": "follow-up",
        }), ["summon-0"])

    def test_split_damage_uses_authored_selector_before_division(self):
        runtime = self.runtime()
        runtime.adds[0]["attack"] = 900
        self.assertEqual(direct_skill_enemy_targets(runtime, "attacker", {
            "effect_target": "enemies_top_atk:1", "effect_name": "split ranked",
            "is_split": True,
        }), ["summon-0"])
        self.assertEqual(direct_skill_enemy_targets(runtime, "attacker", {
            "effect_target": "all_enemies", "effect_name": "split all",
            "is_split": True,
        }), ["__boss__", "summon-0"])

    def test_dot_ticks_reuse_application_snapshot(self):
        runtime = self.runtime()
        runtime.bm = FakeBuffManager([SimpleNamespace(
            caster="attacker",
            effect={"name": "fixed dot"},
            enemy_target_windows={
                "summon-0": {"activated_at": 1, "expires_at": 11, "stack": 1},
            },
        )])
        runtime.time = 5
        self.assertEqual(direct_skill_enemy_targets(runtime, "attacker", {
            "effect_target": "enemies_random:1", "effect_name": "fixed dot",
            "is_dot": True,
        }), ["summon-0"])
        runtime.time = 12
        self.assertEqual(direct_skill_enemy_targets(runtime, "attacker", {
            "effect_target": "enemies_random:1", "effect_name": "fixed dot",
            "is_dot": True,
        }), [])

    def test_existing_all_enemy_route_records_same_target_membership(self):
        runtime = self.runtime()
        self.assertIsNone(direct_skill_enemy_targets(runtime, "attacker", {
            "effect_target": "all_enemies", "effect_name": "wide hit",
        }))
        self.assertEqual(direct_skill_enemy_targets(runtime, "attacker", {
            "effect_target": "same_target:wide hit", "effect_name": "follow-up",
        }), ["__boss__", "summon-0"])

    def test_enemy_count_conditions_use_live_boss_plus_add_roster(self):
        runtime = self.runtime()
        # Native ExcludeSpawnAndCountCheck is distinct from NoAllMonster.
        runtime.adds[0]["Functionnonetarget"] = "NoAllMonster"
        name = core.NAME_MAP["liter"]
        chars = [core.spec.build_char(name, core.default_build(), no_layer=True)]
        chars[0]["name"] = "attacker"
        bm = BuffManager(chars, {"encounter_runtime": runtime})
        runtime.bm = bm
        self.assertTrue(bm._condition_ok(["enemy_count_above:2"], "attacker", 1))
        self.assertFalse(bm._condition_ok(["enemy_count_below:1"], "attacker", 1))
        self.assertTrue(bm._runtime_condition_ok(
            ["enemy_count_above:2"], "attacker", "attacker", "attacker", 1))
        runtime.adds[0]["hp"] = 0
        self.assertFalse(bm._runtime_condition_ok(
            ["enemy_count_above:2"], "attacker", "attacker", "attacker", 2))
        self.assertTrue(bm._condition_ok(["enemy_count_below:1"], "attacker", 2))


if __name__ == "__main__":
    unittest.main()
