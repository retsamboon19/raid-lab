import math
import unittest

from anomaly_ultra_harvester import (
    HARVESTER_AIR_POINTS,
    HARVESTER_GROUND_POINTS,
    PROJECTILE_PHYSICAL_COUNTS,
    build_anomaly_mechanics,
)
from anomaly_projectiles import FORMATION_AIM, HIDE_TRANSLATION
from boss_behavior import RUNNING
from qte_graph import QTEGraph
from raid_boss_combat import RaidBossRuntime
from test_raid_boss_combat import bind, hit


class AnomalyUltraHarvesterTests(unittest.TestCase):
    def test_factory_and_core_exposure(self):
        ultra = RaidBossRuntime([], 180, key='anomaly-ultra')
        ultra.anomaly = build_anomaly_mechanics(ultra)
        self.assertEqual(ultra.anomaly.core_probability('unit', 'Weapon_01', False), 0)
        self.assertEqual(ultra.anomaly.core_probability('unit', 'Weapon_01', True), 1)
        self.assertEqual(ultra.anomaly.core_probability('unit', 'Weapon_02', True), 0)
        self.assertEqual(ultra.anomaly.player_collision_targets(
            'Weapon_01', 3, True), ('Weapon_02', 'Weapon_03'))
        self.assertEqual(ultra.anomaly.player_collision_targets(
            'Weapon_02', 3, True), ())
        self.assertEqual(ultra.anomaly.preferred_part('unit', True), 'Weapon_01')
        self.assertIsNone(ultra.anomaly.preferred_part('unit', False))
        self.assertFalse(ultra.anomaly.part_targetable('Weapon_01', 0))
        ultra.world.phase = 2
        self.assertEqual(ultra.anomaly.core_probability('unit', None, False), 0)
        self.assertEqual(ultra.anomaly.core_probability('unit', 'Weapon_01', False), 1)
        self.assertEqual(ultra.anomaly.preferred_part('unit', False), 'Weapon_01')
        self.assertTrue(ultra.anomaly.part_targetable('Weapon_01', 0))
        harvester = RaidBossRuntime([], 180, key='anomaly-harvester')
        harvester.anomaly = build_anomaly_mechanics(harvester)
        self.assertEqual(harvester.anomaly.core_probability('unit', None, False), 0)
        harvester.world.parts.damage('Head', 10**20, 0)
        self.assertEqual(harvester.anomaly.core_probability('unit', None, False), 1)

    def test_nonstop_phase_advances_projectiles_without_advancing_add_ai(self):
        r = RaidBossRuntime([], 180, key='anomaly-harvester')
        m = r.anomaly
        skill = next(s for s in r.data['skills'] if s['Id'] == 510130)
        m.perform_skill(skill, {'_locked_targets': []})
        shot = r.projectiles[0]
        row = next(c for c in r.data['calls'] if c['Id'] == 1482)
        m._spawn_add(row, 0)
        add = r.adds[0]
        original_position = add['position']
        r.receive_attack = lambda skill, node, **kwargs: None
        m.advance_cinematic_projectiles(shot['deadline'])
        self.assertEqual(shot['status'], 'hit')
        self.assertEqual(add['position'], original_position)

    def test_nonstop_phase_rebases_surviving_projectile_deadline(self):
        r = RaidBossRuntime([], 180, key='anomaly-ultra')
        m = r.anomaly
        skill = next(s for s in r.data['skills'] if s['Id'] == 510632)
        m.perform_skill(skill, {'_locked_targets': []})
        shot = r.projectiles[0]
        original = shot['deadline']
        m.rebase_cinematic_functions(1.5)
        self.assertAlmostEqual(shot['deadline'], original - 1.5)

    def test_harvester_wave_uses_exact_call_offsets_and_add_ids(self):
        r = RaidBossRuntime([], 180, key='anomaly-harvester')
        r.anomaly = build_anomaly_mechanics(r)
        r.time = 10
        skill = next(s for s in r.data['skills'] if s['Id'] == 510136)
        self.assertTrue(r.anomaly.perform_skill(skill, {}))
        self.assertEqual([round(p['at'], 1) for p in r.pending], [10, 11.5, 13])
        for t in (10, 11.5, 13):
            r.time = t
            r.anomaly.advance(t)
        self.assertEqual([a['monster_id'] for a in r.adds], [1220050613] * 3)
        self.assertTrue(all(a['suicide'] for a in r.adds))
        self.assertTrue(all(a['next_attack'] > a['spawned'] for a in r.adds))

    def test_harvester_all_call_rows_use_installed_points_and_spawn_gates(self):
        r = RaidBossRuntime([], 180, key='anomaly-harvester')
        m = build_anomaly_mechanics(r)
        for row in r.data['calls']:
            with self.subTest(call=row['Id']):
                monster = m._monster(row['MonsterId'])
                points = HARVESTER_AIR_POINTS if row['StartPoint'] in HARVESTER_AIR_POINTS else HARVESTER_GROUND_POINTS
                self.assertIn(row['StartPoint'], points)
                self.assertIn(row['ActionPoint'], points)
                self.assertIn(row['DirPoint'], points)
                ticks = 22 if row['SpawnType'] == 'Teleport' else 43
                self.assertAlmostEqual(m._entry_seconds(monster, row), ticks * .017)

    def test_spawned_add_exposes_geometry_and_native_defence(self):
        r = RaidBossRuntime([], 180, key='anomaly-harvester')
        m = build_anomaly_mechanics(r)
        row = next(c for c in r.data['calls'] if c['Id'] == 1482)
        m._spawn_add(row, 4)
        add = r.adds[0]
        monster = m._monster(row['MonsterId'])
        self.assertEqual(add['start_position'], HARVESTER_GROUND_POINTS[1002])
        self.assertEqual(add['action_position'], HARVESTER_GROUND_POINTS[1632])
        self.assertEqual(add['direction_position'], HARVESTER_GROUND_POINTS[1205])
        self.assertAlmostEqual(add['ready_at'], 4 + 43 * .017)
        self.assertEqual(add['entry_speed'], 0)
        self.assertEqual(add['position'], (-3.75, 18.986, 24.6))
        self.assertEqual(add['base_move_speed'], 1.5)
        self.assertEqual(add['out_combat_speed_rate'], 3)
        self.assertEqual(add['in_combat_speed_rate'], 1)
        self.assertEqual(add['acceleration_rate'], 4)
        self.assertIn('fall trajectory', add['entry_timing_status'])
        self.assertEqual(add['defence'], r.stat(monster)['LevelDefence'] * 1.5)

    def test_teleport_rows_begin_at_origin_and_wait_for_spawn_action(self):
        r = RaidBossRuntime([], 180, key='anomaly-harvester')
        m = build_anomaly_mechanics(r)
        for ident in (1488, 1489, 1490):
            row = next(c for c in r.data['calls'] if c['Id'] == ident)
            m._spawn_add(row, 4)
            add = r.adds[-1]
            self.assertEqual(add['position'], add['start_position'])
            self.assertGreater(add['ready_at'], 4)
            self.assertEqual(add['state'], 'spawn-action')
            self.assertAlmostEqual(add['teleport_at'], 4 + 3 * .017)
            self.assertEqual(add['entry_distance'],
                             math.dist(add['start_position'],
                                       add['action_position']))
            self.assertIn('SetTeleport', add['entry_timing_source'])
            self.assertIn('runtime-calibrated', add['entry_timing_status'])
            m._advance_adds(add['teleport_at'])
            self.assertEqual(add['position'], add['action_position'])
            self.assertEqual(add['state'], 'spawn-action')

    def test_approaching_add_cannot_attack_before_arrival(self):
        r = RaidBossRuntime([], 180, key='anomaly-harvester')
        m = build_anomaly_mechanics(r)
        row = next(c for c in r.data['calls'] if c['Id'] == 1482)
        m._spawn_add(row, 0)
        add = r.adds[0]
        add['next_attack'] = 0  # Deliberately stale estimate.
        received = []
        r.receive_attack = lambda *args, **kwargs: received.append(args)
        m._advance_adds(0.1)
        self.assertEqual(add['state'], 'spawn-action')
        self.assertEqual(received, [])

    def test_add_attack_waits_match_each_installed_behavior_tree(self):
        r = RaidBossRuntime([], 180, key='anomaly-harvester')
        m = build_anomaly_mechanics(r)
        self.assertEqual(m._prefire(3220060113), 3)
        self.assertEqual(m._prefire(3220070113), 3)
        self.assertIn(m._prefire(1210010113), (.5, 1, 1.5))
        self.assertEqual(m._prefire(1220050613), 0)
        self.assertIn(m._cooldown(3220060113), (1, 3))
        self.assertIn(m._cooldown(3220070113), (1, 3))
        self.assertIn(m._cooldown(1210010113), (0, 5))
        self.assertEqual(m._cooldown(1220050613), float('inf'))

    def test_harvester_drop_falls_at_fixed_action_xz_until_spawn_action_ends(self):
        r = RaidBossRuntime([], 180, key='anomaly-harvester')
        m = build_anomaly_mechanics(r)
        row = next(c for c in r.data['calls'] if c['Id'] == 1482)
        m._spawn_add(row, 0)
        add = r.adds[0]
        m._advance_adds(1 / 60)
        self.assertEqual(add['state'], 'spawn-action')
        self.assertAlmostEqual(add['position'][0], add['action_position'][0])
        self.assertAlmostEqual(add['position'][2], add['action_position'][2])
        self.assertLess(add['position'][1], add['action_position'][1] + 20)
        m._advance_adds(.68)
        self.assertAlmostEqual(add['position'][1], 2.114, delta=.05)
        self.assertEqual(add['state'], 'spawn-action')
        m._advance_adds(add['ready_at'])
        self.assertEqual(add['position'], add['action_position'])
        self.assertIn(add['state'], ('windup', 'cooldown', 'self-destructed'))

    def test_harvester_projectile_hp_scales_from_stage_record(self):
        r = RaidBossRuntime([], 180, key='anomaly-harvester')
        r.anomaly = build_anomaly_mechanics(r)
        skill = next(s for s in r.data['skills'] if s['Id'] == 510130)
        self.assertTrue(r.anomaly.perform_skill(skill, {'_locked_targets': []}))
        projectile = r.projectiles[0]
        self.assertEqual(projectile['hp'], 15879)
        self.assertTrue(projectile['destroyable'])
        result = r.anomaly.resolve_hit(projectile, 15879, {'is_normal_atk': True})
        self.assertTrue(result['destroyed'])
        self.assertEqual(result['boss_damage'], 0)

    def test_harvester_projectile_hp_all_damage_stages_and_deadline(self):
        expected = [15879, 15879, 15879, 47611, 59838,
                    92699, 116218, 195225, 195225]
        r = RaidBossRuntime([], 180, key='anomaly-harvester')
        skill = next(s for s in r.data['skills'] if s['Id'] == 510130)
        for stage, hp in zip(r.stages, expected):
            with self.subTest(stage=stage['Step']):
                r.damage = stage['ConditionValueMin']
                r.projectiles.clear()
                r.anomaly.perform_skill(skill, {'_locked_targets': []})
                projectile = r.projectiles[0]
                self.assertEqual(projectile['hp'], hp)
                self.assertGreater(projectile['flight_seconds'], 6)
                self.assertLess(projectile['flight_seconds'], 7)
                self.assertEqual(projectile['deadline'], projectile['flight_seconds'])
                self.assertEqual(len(projectile['launcher_positions']), 8)

    def test_harvester_missile_endpoint_uses_locked_character_at_launch(self):
        r = RaidBossRuntime([], 180, key='anomaly-harvester')
        _, names = bind(r)
        skill = next(s for s in r.data['skills'] if s['Id'] == 510130)
        target = names[1]
        r.projectile_target_positions = {
            target: {'character': {'aiming': (4.0, 2.0, 1.0),
                                   'hiding': (4.0, 1.0, -2.0)}}
        }
        r.anomaly.perform_skill(skill, {'_locked_targets': [target]})
        first, pending = r.projectiles[:2]
        self.assertEqual(first['target'], target)
        self.assertEqual(first['target_position'], (4.0, 2.0, 1.0))
        self.assertAlmostEqual(first['endpoint_distance'],
                               math.dist(first['launcher_position'], (4.0, 2.0, 1.0)))
        r.covered = {target}
        r.time = pending['launch_at']
        r.anomaly.advance(r.time)
        self.assertEqual(pending['target_position'], (4.0, 1.0, -2.0))
        self.assertAlmostEqual(pending['flight_seconds'],
                               math.dist(pending['launcher_position'], (4.0, 1.0, -2.0))
                               / pending['native_speed'])
        self.assertAlmostEqual(pending['deadline'],
                               pending['launch_at'] + pending['flight_seconds'])

    def test_harvester_missile_formation_endpoint_tracks_stance(self):
        r = RaidBossRuntime([], 180, key='anomaly-harvester')
        _, names = bind(r)
        target = names[1]
        skill = next(s for s in r.data['skills'] if s['Id'] == 510130)
        r.anomaly.perform_skill(skill, {'_locked_targets': [target]})
        first, pending = r.projectiles[:2]
        self.assertEqual(first['target_position'], FORMATION_AIM[1])
        r.covered = {target}
        r.time = pending['launch_at']
        r.anomaly.advance(r.time)
        self.assertEqual(pending['target_position'],
                         tuple(a + b for a, b in zip(FORMATION_AIM[1],
                                                    HIDE_TRANSLATION)))

    def test_harvester_multiple_missile_launches_remain_independent(self):
        r = RaidBossRuntime([], 180, key='anomaly-harvester')
        skill = next(s for s in r.data['skills'] if s['Id'] == 510130)
        for count in (2, 6):
            r.projectiles.clear()
            for _ in range(count):
                r.anomaly.perform_skill(skill, {'_locked_targets': []})
            self.assertEqual(len(r.projectiles), count * 8)
            self.assertEqual(len({p['id'] for p in r.projectiles}), count * 8)
            first = r.projectiles[0]
            r.anomaly.resolve_hit(first, first['hp'], {'is_normal_atk': True})
            self.assertEqual(first['status'], 'destroyed')
            self.assertTrue(all(p['status'] in ('active', 'pending')
                                for p in r.projectiles[1:]))
            first_deadline = min(p['deadline'] for p in r.projectiles[1:])
            last_deadline = max(p['deadline'] for p in r.projectiles[1:])
            r.anomaly.advance(first_deadline - 1e-6)
            self.assertTrue(all(p['status'] == 'active' for p in r.projectiles[1:]))
            r.anomaly.advance(last_deadline)
            self.assertTrue(all(p['status'] == 'hit' for p in r.projectiles[1:]))

    def test_native_curve_prefab_and_muzzle_multiplicity(self):
        ultra = RaidBossRuntime([], 180, key='anomaly-ultra')
        ultra.anomaly = build_anomaly_mechanics(ultra)
        for ident, count in ((510632, 10), (510633, 10),
                             (510636, 1), (510637, 1)):
            with self.subTest(skill=ident):
                ultra.projectiles.clear()
                skill = next(s for s in ultra.data['skills'] if s['Id'] == ident)
                self.assertTrue(ultra.anomaly.perform_skill(skill, {}))
                self.assertEqual(len(ultra.projectiles), count)
                self.assertTrue(all(p['physical_count'] == count
                                    for p in ultra.projectiles))
                self.assertTrue(all(p['skill']['_damage_shots'] == 1
                                    for p in ultra.projectiles))
                self.assertEqual(sum(p['skill']['SkillValue01']
                                     for p in ultra.projectiles),
                                 skill['SkillValue01'])

        harvester = RaidBossRuntime([], 180, key='anomaly-harvester')
        skill = next(s for s in harvester.data['skills'] if s['Id'] == 510130)
        self.assertTrue(harvester.anomaly.perform_skill(skill, {}))
        self.assertEqual(len(harvester.projectiles), 8)
        self.assertEqual(PROJECTILE_PHYSICAL_COUNTS[510130], 8)
        self.assertEqual([p['physical_index'] for p in harvester.projectiles],
                         list(range(8)))
        self.assertTrue(all(p['skill']['_damage_shots'] == 1
                                    for p in harvester.projectiles))

    def test_legacy_sequence_launch_delay_matches_physical_fire_index(self):
        ultra = RaidBossRuntime([], 180, key='anomaly-ultra')
        skill = next(s for s in ultra.data['skills'] if s['Id'] == 510632)
        ultra.anomaly.perform_skill(skill, {})
        self.assertEqual([round(p['launch_at'], 2) for p in ultra.projectiles],
                         [round(i * .2, 2) for i in range(10)])
        self.assertEqual([p['status'] for p in ultra.projectiles],
                         ['active'] + ['pending'] * 9)

        harvester = RaidBossRuntime([], 180, key='anomaly-harvester')
        skill = next(s for s in harvester.data['skills'] if s['Id'] == 510130)
        harvester.anomaly.perform_skill(skill, {})
        self.assertEqual([p['launcher_position'] for p in harvester.projectiles],
                         [harvester.projectiles[i]['launcher_positions'][j]
                          for i, j in enumerate((0, 4, 1, 5, 2, 6, 3, 7))])
        self.assertEqual([round(p['launch_at'], 2) for p in harvester.projectiles],
                         [i * .5 for i in range(8)])
        self.assertEqual([p['status'] for p in harvester.projectiles],
                         ['active'] + ['pending'] * 7)
        self.assertEqual([p['prefab_index'] for p in harvester.projectiles],
                         [0, 1] * 4)
        self.assertTrue(all(p['projectile_damage_ratio_divisor'] == 8
                            and p['projectile_damage_ratio'] == 313
                            for p in harvester.projectiles))
        self.assertEqual(sum(p['skill']['SkillValue01']
                             for p in harvester.projectiles), 2504)
        self.assertEqual(len({p['launcher_position']
                              for p in harvester.projectiles}), 8)

    def test_legacy_defence_uses_volley_start_but_attack_uses_launch_tick(self):
        r = RaidBossRuntime([], 180, key='anomaly-harvester')
        bind(r)
        skill = next(s for s in r.data['skills'] if s['Id'] == 510130)
        r.anomaly._owner_defence = lambda row, stat: 111
        r.anomaly.perform_skill(skill, {'_locked_targets': []})
        pending = r.projectiles[1]
        self.assertEqual(pending['volley_defence'], 111)
        r.anomaly._owner_defence = lambda row, stat: 999
        r.time = .75
        r.anomaly.advance(.75)
        self.assertEqual(pending['defence'], 111)
        self.assertEqual(pending['defence_snapshot_at'], 0)
        self.assertEqual(pending['snapshot_at'], .75)
        self.assertEqual(pending['incoming_snapshot']['time'], .75)

    def test_launched_ultra_projectile_survives_launcher_part_break(self):
        ultra = RaidBossRuntime([], 180, key='anomaly-ultra')
        skill = next(s for s in ultra.data['skills'] if s['Id'] == 510632)
        received = []
        ultra.receive_attack = lambda row, node: received.append(row['Id'])
        ultra.anomaly.perform_skill(skill, {})
        active = ultra.projectiles[0]
        ultra.world.parts.damage('Weapon_02', 10 ** 20, 0)
        ultra.anomaly.advance(active['deadline'])
        self.assertEqual(active['status'], 'hit')
        self.assertEqual(received, [510632])

    def test_ultra_part_break_keeps_non_cancelable_pending_volley(self):
        ultra = RaidBossRuntime([], 180, key='anomaly-ultra')
        skill = next(s for s in ultra.data['skills'] if s['Id'] == 510632)
        ultra.anomaly.perform_skill(skill, {})
        pending = [p for p in ultra.projectiles if p['status'] == 'pending']
        self.assertEqual(ultra.anomaly.on_part_broken('Weapon_02', 0), 0)
        self.assertTrue(all(p['status'] == 'pending' for p in pending))

    def test_ultra_phase_cutscene_preserves_unlaunched_projectiles(self):
        ultra = RaidBossRuntime([], 180, key='anomaly-ultra')
        received = []
        ultra.receive_attack = lambda row, node: received.append(row['Id'])
        skill = next(s for s in ultra.data['skills'] if s['Id'] == 510632)
        ultra.anomaly.perform_skill(skill, {})
        active = [p for p in ultra.projectiles if p['status'] == 'active']
        pending = [p for p in ultra.projectiles if p['status'] == 'pending']
        self.assertEqual((len(active), len(pending)), (1, 9))
        ultra.anomaly.on_cinematic_start(0)
        ultra.anomaly.on_phase_changed(2, 0)  # idempotent phase-commit fanout
        self.assertTrue(all(p['status'] == 'pending' for p in pending))
        ultra.anomaly.advance(max(p['deadline'] for p in active + pending))
        self.assertTrue(all(p['status'] == 'hit' for p in active + pending))
        self.assertEqual(received, [510632] * 10)

    def test_destroyed_ultra_chamber_filters_its_legacy_projectile_prefab(self):
        ultra = RaidBossRuntime([], 180, key='anomaly-ultra')
        skill = next(s for s in ultra.data['skills'] if s['Id'] == 510632)
        ultra.world.parts.damage('Weapon_02', 10 ** 20, 0)
        self.assertTrue(ultra.anomaly.perform_skill(skill, {}))
        self.assertEqual(ultra.projectiles, [])

    def test_live_resolve_routes_normal_fire_through_add_defence(self):
        r = RaidBossRuntime([], 180, key='anomaly-harvester')
        _, names = bind(r)
        row = next(c for c in r.data['calls'] if c['Id'] == 1485)
        r.anomaly._spawn_add(row, 0)
        add = r.adds[0]
        before = add['hp']
        self.assertEqual(hit(r, damage=1000, caster=names[1], is_normal_atk=True), 0)
        self.assertEqual(add['hp'], before - 1000)
        self.assertEqual(r.damage_to_adds, 1000)

    def test_suicide_add_attacks_once_and_removes_itself(self):
        r = RaidBossRuntime([], 180, key='anomaly-harvester')
        received = []
        r.receive_attack = lambda *args, **kwargs: received.append((args, kwargs))
        r.anomaly = build_anomaly_mechanics(r)
        row = next(c for c in r.data['calls'] if c['GroupId'] == 181)
        r.anomaly._spawn_add(row, 0)
        add = r.adds[0]
        r.time = add['next_attack']
        r.anomaly.advance(r.time)
        self.assertEqual(add['state'], 'self-destructed')
        self.assertEqual(add['hp'], 0)
        self.assertEqual(add['attacks'], 1)
        self.assertEqual(len(received), 1)

    def test_real_qte_graph_greys_are_hazards_not_required_targets(self):
        r = RaidBossRuntime([], 180, key='anomaly-ultra')
        q = r.data['qtes'][0]
        rows = [x for x in r.data['qte_targets'] if x['GroupId'] == q['GroupId'][0]]
        linked = {i for x in rows for i in x['Chain']}
        targets = [dict(id=x['ColIndex'], kind=x['ColType'].lower(),
                        hp=r.stat()['LevelBrokenHp'] * x['HpRatio'] / 10000,
                        duration=x['TimeLimit'] / 100,
                        first=x['FirstCol'] or x['ColIndex'] not in linked,
                        delay=x['DelayTime'] / 100, chain=x['Chain']) for x in rows]
        graph = QTEGraph(targets, 0, q['TimeLimit'] / 100)
        self.assertEqual(graph.aim(0)['kind'], 'break')
        grey = next(x for x in targets if x['kind'] == 'counter')
        graph.hit(grey['id'], 1, 0)
        self.assertEqual(graph.status, 'failed')

    def test_all_ultra_special_qte_groups_keep_one_red_and_four_greys(self):
        r = RaidBossRuntime([], 180, key='anomaly-ultra')
        for stage in r.stages:
            r.damage = stage['ConditionValueMin']
            for qte in r.data['qtes']:
                state = {}
                self.assertEqual(r.special_qte({'Int32_quickTimeId': qte['Id']}, 0, state), RUNNING)
                first = r.states[state['qte']]['event']['graph']
                self.assertEqual([x['kind'] for x in first].count('break'), 1)
                self.assertEqual([x['kind'] for x in first].count('counter'), 4)
                red = next(x for x in first if x['kind'] == 'break')
                self.assertEqual(red['hp'], r.stat()['LevelBrokenHp'] * 8 / 10000)
                r.states[state['qte']]['status'] = 'passed'
                self.assertEqual(r.special_qte({'Int32_quickTimeId': qte['Id']}, 0, state), RUNNING)
                self.assertEqual(r.special_qte({'Int32_quickTimeId': qte['Id']}, 0, state), RUNNING)
                second = r.states[state['qte']]['event']['graph']
                self.assertEqual([x['kind'] for x in second].count('break'), 1)
                self.assertEqual([x['kind'] for x in second].count('counter'), 4)

    def test_all_harvester_memory_qtes_preserve_preview_and_red_chain(self):
        r = RaidBossRuntime([], 180, key='anomaly-harvester')
        for qte in r.data['qtes']:
            state = {}
            r.special_qte({'Int32_quickTimeId': qte['Id']}, 0, state)
            preview = r.states[state['qte']]['event']['graph']
            self.assertEqual([round(x['delay'], 1) for x in preview if x['kind'] == 'counter'],
                             [1, 1.8, 2.6, 3.4, 4.2, 5])
            self.assertEqual(next(x for x in preview if x['kind'] == 'break')['delay'], 7)
            graph = QTEGraph(preview, 0, qte['TimeLimit'] / 100)
            self.assertIsNone(graph.aim(1))
            grey = next(x for x in preview if x['kind'] == 'counter')
            graph.hit(grey['id'], 1, 1)
            self.assertEqual(graph.status, 'failed')
            r.states[state['qte']]['status'] = 'passed'
            r.special_qte({'Int32_quickTimeId': qte['Id']}, 0, state)
            r.special_qte({'Int32_quickTimeId': qte['Id']}, 0, state)
            chain = r.states[state['qte']]['event']['graph']
            self.assertEqual(len(chain), 5)
            self.assertTrue(all(x['kind'] == 'break' and x['hp'] == 72600 for x in chain))
            self.assertEqual([x['chain'] for x in chain], [[2], [3], [4], [5], []])

    def test_ordinary_element_qtes_scale_from_every_stage_record(self):
        cases = [('anomaly-ultra', 3, 3, 8), ('anomaly-ultra', 4, 3, 8),
                 ('anomaly-harvester', 14, 2, 35)]
        for key, shot, count, ratio in cases:
            r = RaidBossRuntime([], 180, key=key)
            for stage in r.stages:
                r.damage = stage['ConditionValueMin']
                ident = r.ordinary_qte(r.skills[shot], 0, 1)
                targets = r.states[ident]['event']['targets']
                self.assertEqual(len(targets), count)
                self.assertTrue(all(x['hp'] == r.stat()['LevelBrokenHp'] * ratio / 10000
                                    for x in targets))

    def test_approximate_intervals_are_explicit(self):
        r = RaidBossRuntime([], 180, key='anomaly-harvester')
        mechanics = build_anomaly_mechanics(r)
        self.assertTrue(any('landing collider' in x for x in mechanics.assumptions))
        self.assertTrue(any('curved route' in x for x in mechanics.assumptions))


if __name__ == '__main__':
    unittest.main()
