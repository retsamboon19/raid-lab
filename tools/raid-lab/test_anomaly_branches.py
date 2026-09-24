"""Source-wide branch checks for the four Anomaly Interception trees.

These tests deliberately inspect every recovered tree node.  They protect the
failure/cancellation arms that an ordinary deterministic fight simulation can
miss, rather than treating one completed happy-path run as behavior coverage.
"""
from __future__ import annotations

import sys
import unittest
import copy
from types import SimpleNamespace
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "tools" / "nikke-team-builder"))
sys.path.insert(0, str(Path(__file__).resolve().parent))

from boss_behavior import BehaviorTree, FAILURE, RUNNING, SUCCESS  # noqa: E402
from raid_boss_combat import RaidBossRuntime  # noqa: E402


BOSSES = (
    "anomaly-ultra",
    "anomaly-indivilia",
    "anomaly-mirror-container",
    "anomaly-harvester",
)
ATTACK_KINDS = {"Attack", "AttackV2", "AttackV3", "TimelineSkill", "BreakCol"}
COMPOSITE_KINDS = {
    "InitVariables", "Sequence", "Selector", "RandomSequence", "RandomSelector",
    "Parallel", "ParallelSelector", "ParallelComplete", "Inverter", "Repeater",
    "ReturnSuccess", "ReturnFailure", "StartAttack", "EndAttack",
    "ChoiceSkillSelector", "PatternSequence", "PatternSelector",
}
LEAF_KINDS = {
    "AttackRelease", "BrokenParts", "BrokenPartsV2", "CheckHp", "CheckMonsterCount",
    "CheckPhase", "CheckVariableNode", "ColliderControlNode", "EmptySuccess",
    "IsExistObstacle", "IsInPoint", "IsTargetAlive", "JumpToVer2", "MoveTo",
    "MoveToVer2", "QuickTimeEvent", "RepairPartsVer2", "RepairPartsVer3",
    "SetDirection", "SetMoveType", "SetSpeedRate", "SetVariableNode", "StopMove",
    "StopMoveSuccess", "TeleportTo", "TeleportToVer2", "TimeCount", "TurnAround",
    "isPhaseAction", *ATTACK_KINDS,
}


def nodes(runtime, suffix=None):
    values = runtime.tree.nodes.values()
    if suffix is None:
        return list(values)
    return [node for node in values if node["Type"].split(".")[-1] == suffix]


class NativeJumpTimingTests(unittest.TestCase):
    def test_indivilia_spawn_skips_optional_return_jump(self):
        runtime = RaidBossRuntime([], 180, key='anomaly-indivilia')
        self.assertEqual(runtime.world.coordinates, {'x': 0.0, 'y': 5.6, 'z': 60.0})
        opening = next(n for n in nodes(runtime, 'IsInPoint') if n['ID'] == 14)
        self.assertEqual(runtime.world.action(opening, 0, {'started': 0}), FAILURE)

    def test_indivilia_jump_waits_for_landing_animation(self):
        runtime = RaidBossRuntime([], 180, key='anomaly-indivilia')
        animation = runtime.world.movement_data['jump_animation']
        for node in nodes(runtime, 'JumpToVer2'):
            with self.subTest(node=node['ID']):
                state = {'started': 10.0}
                flight = node['Single_startDelay'] + animation['start_seconds'] + node['SinglemDuration']
                finish = 10.0 + flight + animation['end_seconds']
                self.assertEqual(runtime.world.action(node, 11.0, state), RUNNING)
                self.assertEqual(runtime.world.action(node, 10.0 + flight, state), RUNNING)
                self.assertEqual(runtime.world.position, 153)
                self.assertEqual(runtime.world.action(node, finish - .001, state), RUNNING)
                self.assertEqual(runtime.world.action(node, finish, state), SUCCESS)


def shot_numbers(node):
    shots = node.get("List`1_aniNumberTypes", [node.get("SkillAniNumberTypemSkillAniNumber")])
    return [int(shot.split("_")[-1]) for shot in shots if shot]


def source_subtree(key, node_id):
    runtime = RaidBossRuntime([], 180, key=key)
    runtime.tree = BehaviorTree(copy.deepcopy(runtime.tree.nodes[node_id]), runtime.world)
    return runtime


def advance(runtime, time):
    runtime.time = time
    return runtime.tree.advance(time)


def resolve_active_qte(runtime, status, time):
    active = [state for state in runtime.states.values()
              if state["event"]["kind"] == "qte" and state["status"] in ("pending", "active")]
    if not active:
        raise AssertionError("source subtree did not open a QTE")
    active[-1]["status"] = status
    return advance(runtime, time)


class SourceReferenceCoverageTests(unittest.TestCase):
    def test_every_enabled_source_node_and_reference_has_an_engine_definition(self):
        for key in BOSSES:
            runtime = RaidBossRuntime([], 180, key=key)
            qte_ids = {row["Id"] for row in runtime.data["qtes"]}
            qte_groups = {row["GroupId"] for row in runtime.data["qte_targets"]}
            part_names = set(runtime.world.rows)
            for node in runtime.tree.nodes.values():
                if node.get("Disabled"):
                    continue
                kind = node["Type"].split(".")[-1]
                with self.subTest(boss=key, node=node["ID"], kind=kind):
                    self.assertIn(kind, COMPOSITE_KINDS | LEAF_KINDS)
                    if kind in ATTACK_KINDS:
                        for shot in shot_numbers(node):
                            self.assertIn(shot, runtime.skills)
                    elif kind == "QuickTimeEvent":
                        ident = node["Int32_quickTimeId"]
                        self.assertIn(ident, qte_ids)
                        record = next(row for row in runtime.data["qtes"] if row["Id"] == ident)
                        self.assertTrue(record["GroupId"])
                        self.assertTrue(set(record["GroupId"]) <= qte_groups)
                    elif kind.startswith(("BrokenParts", "RepairParts")):
                        self.assertTrue(set(node["List`1_partsList"]) <= part_names)
                    elif kind == "CheckHp" and not node.get("BooleanisUsingMianHp"):
                        self.assertIn(node["PartsTypemPartsType"], part_names)

    def test_every_special_qte_has_native_inverted_pass_and_failure_arms(self):
        for key in BOSSES:
            template = RaidBossRuntime([], 180, key=key)
            for source_node in nodes(template, "QuickTimeEvent"):
                ident = source_node["Int32_quickTimeId"]
                with self.subTest(boss=key, qte=ident, outcome="player-pass"):
                    runtime = RaidBossRuntime([], 180, key=key)
                    node = runtime.tree.nodes[source_node["ID"]]
                    state = {"started": 0}
                    result = runtime.special_qte(node, 0, state)
                    generated = []
                    while result == RUNNING:
                        if "qte" not in state:
                            result = runtime.special_qte(node, 0, state)
                            continue
                        generated.append(state["groups"][state["group"]])
                        runtime.states[state["qte"]]["status"] = "passed"
                        result = runtime.special_qte(node, 0, state)
                    self.assertEqual(result, FAILURE)
                    record = next(row for row in runtime.data["qtes"] if row["Id"] == ident)
                    expected = 1 if record["RandomPreset"] else len(record["GroupId"])
                    self.assertEqual(len(generated), expected)

                with self.subTest(boss=key, qte=ident, outcome="player-failure"):
                    runtime = RaidBossRuntime([], 180, key=key)
                    node = runtime.tree.nodes[source_node["ID"]]
                    state = {"started": 0}
                    self.assertEqual(runtime.special_qte(node, 0, state), RUNNING)
                    runtime.states[state["qte"]]["status"] = "failed"
                    self.assertEqual(runtime.special_qte(node, 0, state), SUCCESS)

    def test_nested_ultra_presets_use_one_context_then_the_source_fallback_timer(self):
        runtime = source_subtree("anomaly-ultra", 199)
        self.assertEqual(advance(runtime, 0), RUNNING)
        self.assertEqual(resolve_active_qte(runtime, "passed", 0), RUNNING)
        # The first preset completes inside one QuickTimeEvent context.  The
        # next update creates its second preset instead of exiting the node.
        self.assertEqual(advance(runtime, 0), RUNNING)
        self.assertEqual(resolve_active_qte(runtime, "passed", 0), RUNNING)
        self.assertEqual(advance(runtime, 0.049), RUNNING)
        self.assertEqual(advance(runtime, 0.05), RUNNING)
        self.assertEqual(advance(runtime, 0.149), RUNNING)
        self.assertEqual(advance(runtime, 0.151), SUCCESS)
        self.assertEqual(runtime.world.position, 151)

        # An unknown/expired context is the client QTE-failure result.  The
        # selector succeeds immediately and never enters the teleport arm.
        runtime = source_subtree("anomaly-ultra", 199)
        self.assertEqual(advance(runtime, 0), RUNNING)
        self.assertEqual(resolve_active_qte(runtime, "unknown", 9), SUCCESS)
        self.assertEqual(runtime.world.position, 254)

    def test_indivilia_pass_reaches_nested_groggy_timeline_after_timer(self):
        runtime = source_subtree("anomaly-indivilia", 191)
        self.assertEqual(advance(runtime, 0), RUNNING)
        self.assertEqual(resolve_active_qte(runtime, "passed", 0), RUNNING)
        self.assertEqual(advance(runtime, 0), RUNNING)
        self.assertEqual(advance(runtime, 0.049), RUNNING)
        self.assertEqual(advance(runtime, 0.05), RUNNING)
        self.assertEqual(runtime.world.position, 1317)
        # The inverted TimelineSkill deliberately makes the selector fail
        # after the groggy Shot18 completes, allowing its parent route to end.
        self.assertEqual(advance(runtime, 10), FAILURE)
        self.assertTrue(any(event.get("shot") == 18 and
                            event["event"] == "boss attack started"
                            for event in runtime.events))

    def test_mirror_qte_wrapper_selects_groggy_or_failure_timeline(self):
        # Passed QTE: Inverter succeeds, then Shot24 is the groggy route.
        runtime = source_subtree("anomaly-mirror-container", 89)
        self.assertEqual(advance(runtime, 0), RUNNING)
        self.assertEqual(advance(runtime, 1), RUNNING)
        self.assertEqual(resolve_active_qte(runtime, "passed", 1), RUNNING)
        self.assertEqual(advance(runtime, 2), RUNNING)
        end = runtime.tree.memory[95]["end"]
        self.assertEqual(advance(runtime, end), SUCCESS)
        self.assertTrue(any(event.get("shot") == 24 and
                            event["event"] == "boss attack started"
                            for event in runtime.events))
        self.assertFalse(any(event.get("shot") in (10, "Shot10") for event in runtime.events))

        # Failed QTE: the first Sequence fails and Selector falls through to
        # the Shot10 failure route.
        runtime = source_subtree("anomaly-mirror-container", 89)
        advance(runtime, 0)
        advance(runtime, 1)
        self.assertEqual(resolve_active_qte(runtime, "failed", 1), RUNNING)
        self.assertEqual(advance(runtime, 2), RUNNING)
        end = runtime.tree.memory[98]["end"]
        self.assertEqual(advance(runtime, end), SUCCESS)
        self.assertTrue(any(event.get("shot") == 10 and
                            event["event"] == "boss attack started"
                            for event in runtime.events))
        self.assertFalse(any(event.get("shot") in (24, "Shot24") for event in runtime.events))

    def test_mirror_part_flags_require_destruction_and_disable_only_that_route(self):
        cases = (
            (179, 169, "A", "Weapon_07"),
            (193, 183, "B", "Weapon_08"),
            (207, 197, "C", "Weapon_09"),
            (221, 211, "D", "Weapon_10"),
        )
        template = RaidBossRuntime([], 180, key="anomaly-mirror-container")
        for selector_id, gate_id, variable, part in cases:
            with self.subTest(variable=variable, state="mere-hit-survives"):
                runtime = RaidBossRuntime([], 180, key="anomaly-mirror-container")
                current = runtime.world.parts.parts[part]
                current["hp"] -= 1
                runtime.tree = BehaviorTree(copy.deepcopy(template.tree.nodes[selector_id]), runtime.world)
                self.assertEqual(advance(runtime, 0), SUCCESS)
                self.assertNotIn(variable, runtime.world.variables)

                runtime.tree = BehaviorTree(copy.deepcopy(template.tree.nodes[gate_id]), runtime.world)
                self.assertEqual(advance(runtime, 0), RUNNING)
                self.assertEqual(advance(runtime, 0), SUCCESS)

            with self.subTest(variable=variable, state="destroyed"):
                runtime = RaidBossRuntime([], 180, key="anomaly-mirror-container")
                runtime.world.parts.self_destruct(part, 0)
                runtime.tree = BehaviorTree(copy.deepcopy(template.tree.nodes[selector_id]), runtime.world)
                self.assertEqual(advance(runtime, 0), SUCCESS)
                self.assertEqual(runtime.world.variables[variable], 1)

                runtime.tree = BehaviorTree(copy.deepcopy(template.tree.nodes[gate_id]), runtime.world)
                self.assertEqual(advance(runtime, 0), RUNNING)
                self.assertEqual(advance(runtime, 0), FAILURE)

    def test_mirror_j_counter_advances_three_opening_attacks_then_rest_route(self):
        template = RaidBossRuntime([], 180, key="anomaly-mirror-container")
        runtime = RaidBossRuntime([], 180, key="anomaly-mirror-container")
        runtime.world.variables["J"] = 1
        expected_openers = {1: 27, 2: 29, 3: 30}
        for value in (1, 2, 3, 4):
            with self.subTest(j=value):
                runtime.tree = BehaviorTree(copy.deepcopy(template.tree.nodes[144]), runtime.world)
                expected_status = SUCCESS if value in expected_openers else RUNNING
                # Each CheckVariableNode now consumes one native Running tick
                # before its equality result can select the attack branch.
                for _ in range(5):
                    status=advance(runtime, 0)
                    if status==SUCCESS or 154 in runtime.tree.memory:break
                self.assertEqual(status, expected_status)
                starts = [event["shot"] for event in runtime.events
                          if event["event"] == "boss attack started"]
                if value in expected_openers:
                    self.assertEqual(starts[-1], expected_openers[value])
                else:
                    self.assertEqual(runtime.tree.memory[154]["started"], 0)

                runtime.tree = BehaviorTree(copy.deepcopy(template.tree.nodes[229]), runtime.world)
                for _ in range(5):
                    status=advance(runtime, 0)
                    if status!=RUNNING:break
                self.assertEqual(status, SUCCESS)
                self.assertEqual(runtime.world.variables["J"], min(4, value + 1))

    def test_harvester_failed_qte_reaches_failure_attack_but_pass_skips_it(self):
        runtime = source_subtree("anomaly-harvester", 82)
        self.assertEqual(advance(runtime, 0), RUNNING)
        self.assertEqual(resolve_active_qte(runtime, "failed", 0), RUNNING)
        first_end = runtime.tree.memory[85]["end"]
        self.assertEqual(advance(runtime, first_end), RUNNING)
        self.assertEqual(advance(runtime, first_end), RUNNING)
        second_end = runtime.tree.memory[85]["end"]
        self.assertEqual(advance(runtime, second_end), FAILURE)
        fired = [event.get("shot") for event in runtime.events
                 if event["event"] == "boss skill activated"]
        self.assertEqual(fired[0], "Shot07")
        self.assertEqual(fired[1:], ["Shot04"] * 5)

        runtime = source_subtree("anomaly-harvester", 82)
        self.assertEqual(advance(runtime, 0), RUNNING)
        self.assertEqual(resolve_active_qte(runtime, "passed", 0), RUNNING)
        self.assertEqual(advance(runtime, 0), RUNNING)
        self.assertEqual(resolve_active_qte(runtime, "passed", 0), FAILURE)
        self.assertFalse(any(event["event"] == "boss skill activated" for event in runtime.events))

    def test_every_ordinary_break_object_executes_pass_cancel_and_fail_fire(self):
        checked = 0
        for key in BOSSES:
            template = RaidBossRuntime([], 180, key=key)
            source_nodes = [
                node for node in template.tree.nodes.values()
                if node["Type"].split(".")[-1] in ATTACK_KINDS
                and any(template.skills[shot]["BreakObject"] for shot in shot_numbers(node))
            ]
            for source_node in source_nodes:
                shot = shot_numbers(source_node)[0]
                checked += 1
                with self.subTest(boss=key, node=source_node["ID"], shot=shot, outcome="player-pass"):
                    runtime = RaidBossRuntime([], 180, key=key)
                    node = runtime.tree.nodes[source_node["ID"]]
                    state = {"started": 0}
                    self.assertEqual(runtime.world.action(node, 0, state), RUNNING)
                    runtime.time = state["interrupt"]
                    self.assertEqual(runtime.world.action(node, runtime.time, state), RUNNING)
                    runtime.states[state["qte"]]["status"] = "passed"
                    expected = FAILURE if node.get("BooleanFailueCheck") else SUCCESS
                    self.assertEqual(runtime.world.action(node, runtime.time, state), expected)
                    self.assertFalse(any(event.get("shot") == f"Shot{shot:02d}" and
                                         event["event"] == "boss skill activated"
                                         for event in runtime.events))

                with self.subTest(boss=key, node=source_node["ID"], shot=shot, outcome="player-failure"):
                    runtime = RaidBossRuntime([], 180, key=key)
                    node = runtime.tree.nodes[source_node["ID"]]
                    state = {"started": 0}
                    runtime.world.action(node, 0, state)
                    runtime.time = state["interrupt"]
                    runtime.world.action(node, runtime.time, state)
                    runtime.states[state["qte"]]["status"] = "failed"
                    runtime.time = state["end"]
                    self.assertEqual(runtime.world.action(node, runtime.time, state), SUCCESS)
                    self.assertTrue(any(event.get("shot") == f"Shot{shot:02d}" and
                                        event["event"] == "boss skill activated"
                                        for event in runtime.events))
        self.assertEqual(checked, 10)

    def test_every_part_hp_condition_reaches_alive_and_broken_branches(self):
        checked = 0
        for key in BOSSES:
            template = RaidBossRuntime([], 180, key=key)
            for source_node in nodes(template, "CheckHp"):
                if source_node.get("BooleanisUsingMianHp"):
                    continue
                checked += 1
                for broken in (False, True):
                    runtime = RaidBossRuntime([], 180, key=key)
                    node = runtime.tree.nodes[source_node["ID"]]
                    part = node["PartsTypemPartsType"]
                    if broken:
                        runtime.world.parts.self_destruct(part, 0)
                    with self.subTest(boss=key, node=source_node["ID"], broken=broken):
                        self.assertEqual(runtime.world.action(node, 0, {"started": 0}),
                                         FAILURE if broken else SUCCESS)
        self.assertEqual(checked, 22)

    def test_hp_condition_strict_comparisons_fail_at_equality(self):
        runtime=RaidBossRuntime([],180,key='anomaly-ultra')
        part='Weapon_02'
        row=runtime.world.parts.parts[part]
        row['hp']=row['max_hp']*.5
        node=dict(Type='CheckHp',ID=9001,Int32mValue=50,
                  PartsTypemPartsType=part,BooleanisUsingMianHp=False)
        for lower in (False,True):
            node['BooleanmLower']=lower
            self.assertEqual(runtime.world.action(node,0,{}),FAILURE)
        row['hp']=row['max_hp']*.49
        node['BooleanmLower']=True
        self.assertEqual(runtime.world.action(node,0,{}),SUCCESS)
        node['BooleanmLower']=False
        self.assertEqual(runtime.world.action(node,0,{}),FAILURE)
        row['hp']=row['max_hp']*.51
        self.assertEqual(runtime.world.action(node,0,{}),SUCCESS)

    def test_every_variable_condition_waits_one_tick_then_compares_equality(self):
        checked=0
        for key in BOSSES:
            runtime=RaidBossRuntime([],180,key=key)
            for node in nodes(runtime,'CheckVariableNode'):
                checked+=1
                state={}
                name=node['MonsterBtVariabletype']
                value=node['Int32value']
                runtime.world.variables[name]=value+1
                with self.subTest(boss=key,node=node['ID']):
                    self.assertEqual(runtime.world.action(node,0,state),RUNNING)
                    self.assertEqual(runtime.world.action(node,0,state),FAILURE)
                    runtime.world.variables[name]=value
                    self.assertEqual(runtime.world.action(node,0,state),SUCCESS)
                    self.assertEqual(runtime.world.action(node,0,{}),RUNNING)
        self.assertGreater(checked,0)

    def test_all_authored_point_conditions_use_inclusive_xyz_or_xz_radius(self):
        checked=0
        for key in BOSSES:
            runtime=RaidBossRuntime([],180,key=key)
            for node in nodes(runtime,'IsInPoint'):
                checked+=1
                self.assertEqual(node['DirectionType_pointType'],'SelectPoint')
                destination=runtime.world.movement_data['points'][str(node['Int32_point'])]
                radius=node['Single_duration']
                with self.subTest(boss=key,node=node['ID']):
                    # The visited-point marker deliberately differs; native
                    # tests transform distance, including the boundary.
                    runtime.world.position=254 if node['Int32_point']!=254 else 253
                    runtime.world.coordinates={**destination,'x':destination['x']+radius}
                    self.assertEqual(runtime.world.action(node,0,{}),SUCCESS)
                    runtime.world.coordinates['x']=destination['x']+radius+.01
                    self.assertEqual(runtime.world.action(node,0,{}),FAILURE)
                    runtime.world.coordinates={**destination,'y':destination['y']+100}
                    expected=FAILURE if node['Boolean_usingAxisY'] else SUCCESS
                    self.assertEqual(runtime.world.action(node,0,{}),expected)
        self.assertEqual(checked,3)

    def test_authored_monster_count_bounds_are_inclusive_and_cached(self):
        runtime=RaidBossRuntime([],180,key='anomaly-harvester')
        for node in nodes(runtime,'CheckMonsterCount'):
            with self.subTest(node=node['ID']):
                runtime.living_adds=lambda:[object()]*5
                state={}
                self.assertEqual(runtime.world.action(node,0,state),SUCCESS)
                runtime.living_adds=lambda:[]
                self.assertEqual(runtime.world.action(node,1,state),SUCCESS)
                self.assertEqual(runtime.world.action(node,1,{}),FAILURE)
                runtime.living_adds=lambda:[object()]*49
                self.assertEqual(runtime.world.action(node,1,{}),SUCCESS)
                runtime.living_adds=lambda:[object()]*50
                self.assertEqual(runtime.world.action(node,1,{}),FAILURE)

    def test_every_authored_target_alive_condition_uses_its_slot(self):
        runtime=RaidBossRuntime([],180,key='anomaly-indivilia')
        runtime.squad={f'unit{i}':{} for i in range(1,6)}
        hp={name:100 for name in runtime.squad}
        runtime.bm=SimpleNamespace(state={'hp':hp})
        checked=0
        for node in nodes(runtime,'IsTargetAlive'):
            checked+=1
            self.assertFalse(node['Boolean_isNotHide'])
            slot=int(node['ECharacterPosition_targetPosition'][-1])
            name=f'unit{slot}'
            with self.subTest(node=node['ID'],slot=slot):
                self.assertEqual(runtime.world.action(node,0,{}),SUCCESS)
                hp[name]=0
                self.assertEqual(runtime.world.action(node,0,{}),FAILURE)
                hp[name]=100
        self.assertEqual(checked,20)
        runtime.bm=None
        self.assertEqual(runtime.world.action(nodes(runtime,'IsTargetAlive')[0],0,{}),FAILURE)

    def test_every_stage_condition_reaches_both_source_branches(self):
        checked = 0
        for key in BOSSES:
            template = RaidBossRuntime([], 180, key=key)
            for source_node in nodes(template, "CheckPhase"):
                checked += 1
                outcomes = set()
                for high in (False, True):
                    runtime = RaidBossRuntime([], 180, key=key)
                    node = runtime.tree.nodes[source_node["ID"]]
                    if high:
                        if node["PhaseCheckType_type"] == "BerserkStep":
                            threshold = next(row["ConditionValueMin"] for row in runtime.stages
                                             if row["Step"] >= node["Single_phaseValue"])
                            runtime.damage = threshold
                        else:
                            maximum = runtime.stat()["LevelHp"] * runtime.data["monster"]["HpRatio"] / 10000
                            runtime.damage = maximum
                    outcomes.add(runtime.world.action(node, 0, {"started": 0}))
                    # Native 0x651af70 returns Failure on the threshold and
                    # Success while the phase should continue. Merely
                    # observing both outcomes cannot catch an inversion.
                    self.assertEqual(runtime.world.action(node, 0, {"started": 0}),
                                     FAILURE if high else SUCCESS)
                with self.subTest(boss=key, node=source_node["ID"]):
                    self.assertEqual(outcomes, {SUCCESS, FAILURE})
        self.assertEqual(checked, 12)

    def test_phase_hp_guard_has_strict_boundary_and_persistent_completion(self):
        runtime=RaidBossRuntime([],180,key='anomaly-indivilia')
        node=dict(Type='CheckPhase',ID=999,PhaseCheckType_type='HpRatio',Single_phaseValue=50)
        maximum=runtime.stat()['LevelHp']*runtime.data['monster']['HpRatio']/10000
        runtime.damage=maximum*.5
        self.assertEqual(runtime.world.action(node,0,{}),SUCCESS)
        runtime.damage+=1
        self.assertEqual(runtime.world.action(node,0,{}),FAILURE)
        runtime.damage=0
        self.assertEqual(runtime.world.action(node,1,{}),FAILURE)

    def test_indivilia_initial_phase_does_not_skip_its_attack_loop(self):
        from test_raid_boss_combat import bind
        runtime=RaidBossRuntime([],180,key='anomaly-indivilia')
        bind(runtime)
        for tick in range(601):runtime.advance(tick/60)
        self.assertEqual(runtime.world.phase,1)
        self.assertEqual(runtime.phase_cinematics,[])
        for part in ('Weapon_01','Weapon_02','Weapon_03'):
            self.assertTrue(runtime.world.parts.alive(part))

    def test_functions_reachable_from_source_attacks_have_no_fallback_effects(self):
        for key in BOSSES:
            runtime = RaidBossRuntime([], 180, key=key)
            referenced = {
                shot for node in runtime.tree.nodes.values()
                if node["Type"].split(".")[-1] in ATTACK_KINDS
                for shot in shot_numbers(node)
            }
            for shot in referenced:
                runtime.apply_skill_functions(runtime.skills[shot], "UseFunctionIdSkill", "unit")
                runtime.apply_skill_functions(runtime.skills[shot], "HurtFunctionIdSkill", "unit")
            # Delayed OnStart functions are source-reachable too.  Drain them
            # explicitly so this check cannot pass merely because dispatch was
            # deferred beyond the assertion.
            while runtime.pending_functions:
                item = runtime.pending_functions.pop(0)
                runtime.time = item["at"]
                runtime.apply_function(
                    item["ident"], item.get("target"), item.get("part"), delayed=True,
                )
            with self.subTest(boss=key):
                self.assertEqual(runtime.unhandled, set())


if __name__ == "__main__":
    unittest.main()
