"""Source-backed production regressions for Rapunzel: Sanctuary."""
from types import SimpleNamespace
import unittest

import core
from calculator.buff_manager import BuffManager, char_effects
from calculator.timeline import CharState, BurstController, _register_instant_handlers
from calculator import roster_mechanics as roster
from runner.kits_rapunzel_sanctuary import NAME, CONSUMED, BLESSING
from anomaly_target_context import select_enemy_effect_targets, direct_skill_enemy_targets
from raid_boss_combat import RaidBossRuntime

FRAY = ('홍련 : 신살', '마리안 : 퀸')
SQUAD = ['리타', NAME, *FRAY, '크라운']


def build(level=10):
    result = core.default_build()
    result['skill_levels'] = dict.fromkeys(('1', '2', '3'), level)
    return result


def fixture(level=10, names=None):
    names = names or SQUAD
    chars = [core.spec.build_char(n, build(level), no_layer=True) for n in names]
    state = {'hp': dict.fromkeys(names, 10000.0),
             'hp_pct': dict.fromkeys(names, 100.0),
             'base_stats': {n: {'hp': 10000.0, 'atk': 1000.0, 'def': 100.0}
                            for n in names},
             'rng_expected': True, 'burst_gauge_charging': True}
    state['burst_stages'] = {}
    manager = BuffManager(chars, state)
    fighters = {c['name']: CharState(c, 1000.0, '철갑') for c in chars}
    _register_instant_handlers(manager, fighters,
                              SimpleNamespace(cooldowns={}, next_ready={}, _cooldowns={}))
    manager.battle_start(0)
    return manager, fighters


def down(manager, names):
    for n in names:
        manager.state['hp'][n] = 0.0
        manager.sync_hp(n)


class RapunzelSanctuaryTests(unittest.TestCase):
    def test_identity_import_and_all_ten_level_arrays(self):
        row = core.CAT[NAME]
        self.assertEqual((row['name'], row['resource_id'], row['name_code']),
                         ('Rapunzel: Sanctuary', 473, 5187))
        self.assertEqual((row['weapon'], row['burst'], row['cooldown']), ('RL', '2', 20))
        self.assertTrue(row['supported'])
        imported = core.import_roster({'elements': {'Iron': [{'name_code': 5187,
            'skill1_level': 2, 'skill2_level': 4, 'skill_burst_level': 6}]}})
        unit = imported['roster'][0]
        self.assertEqual(unit['id'], NAME)
        self.assertEqual(unit['build']['skill_levels'], {'1': 2, '2': 4, '3': 6})
        effects = char_effects(NAME, 0)
        self.assertEqual({e['source'] for e in effects}, {'스킬1', '스킬2', '스킬3'})
        for e in effects:
            if 'values' in e:
                self.assertEqual(set(e['values']), set(map(str, range(1, 11))))

    def test_fullcharge_healing_exact_levels_skips_dead_allies(self):
        expected = [2.3, 2.48, 2.66, 2.83, 3.01, 3.19, 3.37, 3.54, 3.72, 3.9]
        for level, percent in enumerate(expected, 1):
            bm, _ = fixture(level)
            for n in SQUAD:
                bm.state['hp'][n] = 5000
                bm.sync_hp(n)
            down(bm, ['리타'])
            bm.notify('full_charge', 1, NAME)
            for n in SQUAD[1:]:
                self.assertAlmostEqual(bm.state['hp'][n], 5000 + 10000 * percent / 100)
            self.assertEqual(bm.state['hp']['리타'], 0)

    def test_fullburst_self_and_tagged_allies_no_other_targets(self):
        bm, _ = fixture()
        bm.notify('full_burst_start', 1, NAME)
        for n in [NAME, *FRAY]:
            buffs = bm.get_buffs(n, '__enemy__', 1)
            self.assertAlmostEqual(buffs['atk_dmg_pct'], 27.45)
            self.assertAlmostEqual(buffs['atk_flat'], 291.7)
        for n in ['리타', '크라운']:
            buffs = bm.get_buffs(n, '__enemy__', 1)
            self.assertEqual(buffs['atk_dmg_pct'], 0)
            self.assertEqual(buffs['atk_flat'], 0)
        # Recipients are captured when FullBurst starts, not later tag additions.
        for ab in bm._active:
            if ab.effect.get('into_the_fray'):
                ab.expires_at = 2
        bm.tick(2.1)
        self.assertAlmostEqual(bm.get_buffs(FRAY[0], '__enemy__', 2.1)['atk_flat'], 291.7)
        bm.tick(11.01)
        self.assertEqual(bm.get_buffs(NAME, '__enemy__', 11.01)['atk_dmg_pct'], 0)

    def test_charge_hold_shared_pool_release_and_blessing_cooldown(self):
        bm, _ = fixture()
        bm.state['full_charging'] = {NAME: True}
        bm.notify('full_charge_ready', 1, NAME)
        bm.notify('charge_hold:1', 2, NAME)
        self.assertTrue(bm.has_shield(NAME))
        # A shared barrier protects the team but the installed state belongs
        # to its caster (GAMEPLAY shared-shield rule); no per-ally shield flag.
        self.assertFalse(bm.has_shield('리타'))
        shield = next(a for a in bm._active if a.effect.get('stat') == 'shared_shield_from_max_hp_pct')
        self.assertEqual(set(shield.shield_per_target.values()), {739.0})
        kind, absorbed = roster.shield_hit(bm, '리타', 300, 2)
        self.assertEqual((kind, absorbed), ('shield', 300))
        self.assertEqual(set(shield.shield_per_target.values()), {439.0})
        self.assertAlmostEqual(bm._effective_def('리타'), 142.24)
        bm.state['full_charging'][NAME] = False
        bm.notify('charge_end', 2.1, NAME)
        self.assertFalse(any(bm.has_shield(n) for n in SQUAD))
        self.assertTrue(bm._has_self_state(NAME, BLESSING))
        bm.notify('charge_hold:1', 3, NAME)
        self.assertFalse(bm.has_shield(NAME))
        bm.tick(12.01)
        bm.notify('charge_hold:1', 13, NAME)
        self.assertTrue(bm.has_shield(NAME))

    def test_fullcharge_immunity_ends_on_release_and_new_charge(self):
        bm, fighters = fixture(names=[NAME])
        cs = fighters[NAME]
        # Actual charging holds the original full-charge state; the first1sec
        # is unmodified. Fullcharge-ready fires independently of a fired shot.
        cs._hold_release_t = 5
        enemy = {'def': 0, 'core_px': 0, 'is_element_match': False}
        cfg = {'rng_mode': 'expected'}
        cs._tick_charge(0, bm, enemy, cfg)
        self.assertFalse(bm.get_buffs(NAME, '__enemy__', 0)['charge_speed_buff_immune'])
        cs._tick_charge(1.01, bm, enemy, cfg)
        self.assertTrue(bm.get_buffs(NAME, '__enemy__', 1.01)['charge_speed_buff_immune'])
        self.assertTrue(bm.get_buffs(NAME, '__enemy__', 1.01)['charge_speed_debuff_immune'])
        cs._tick_charge(2.02, bm, enemy, cfg)
        self.assertTrue(bm.has_shield(NAME))
        cs._end_charge(2.1, bm)
        self.assertFalse(bm.has_shield(NAME))
        self.assertFalse(bm.get_buffs(NAME, '__enemy__', 2.1)['charge_speed_buff_immune'])
        # A new charge cannot retain the old immunity.
        cs._charge_phase = 'ready'
        cs._tick_charge(2.2, bm, enemy, cfg)
        self.assertFalse(bm.get_buffs(NAME, '__enemy__', 2.2)['charge_speed_buff_immune'])

    def test_burst_zero_or_two_dead_never_consumes_resurrection(self):
        for count in (0, 2):
            bm, _ = fixture()
            down(bm, [n for n in SQUAD if n != NAME][:count])
            bm.notify('burst_cast', 1, NAME)
            self.assertFalse(bm.state.get('revives'))
            self.assertFalse(bm._has_self_state(NAME, CONSUMED))
            self.assertEqual(bm.get_buffs(NAME, '__enemy__', 1)['burst_cooldown'], 0)
            self.assertAlmostEqual(bm.get_buffs(NAME, '__enemy__', 1)['atk_flat'], 348.4)

    def test_three_and_four_dead_revive_targets_and_exclusive_branch(self):
        for count in (3, 4):
            bm, _ = fixture()
            fallen = [n for n in SQUAD if n != NAME][:count]
            down(bm, fallen)
            bm.notify('burst_cast', 1, NAME)
            self.assertEqual([r['unit'] for r in bm.state['revives']], fallen)
            for n in fallen:
                self.assertAlmostEqual(bm.state['hp'][n], 9600)
                self.assertAlmostEqual(bm.get_buffs(n, '__enemy__', 1)['atk_flat'], 1013.7)
                self.assertAlmostEqual(bm._effective_def(n), 321.76)
            self.assertEqual(bm.get_buffs(NAME, '__enemy__', 1)['atk_flat'], 0)
            self.assertTrue(bm._has_self_state(NAME, CONSUMED))
            self.assertEqual(bm.get_buffs(NAME, '__enemy__', 1)['burst_cooldown'], -40)
            self.assertEqual(bm.get_buffs(NAME, '__enemy__', 1)['def_pct'], 0)
            bm.tick(1.099)
            self.assertEqual(bm.get_buffs(NAME, '__enemy__', 1.099)['def_pct'], 0)
            bm.tick(1.1)
            self.assertEqual(bm.get_buffs(NAME, '__enemy__', 1.1)['def_pct'], 10)
            bm.tick(12)
            down(bm, fallen)
            bm.notify('burst_cast', 13, NAME)
            self.assertEqual(len(bm.state['revives']), count)
            self.assertTrue(all(bm.state['hp'][n] == 0 for n in fallen))
            self.assertAlmostEqual(bm.get_buffs(NAME, '__enemy__', 13)['atk_flat'], 348.4)
            # Persistent state and DEF survive the caster dying and being revived.
            down(bm, [NAME])
            bm.state['hp'][NAME] = 5000
            bm.sync_hp(NAME)
            self.assertTrue(bm._has_self_state(NAME, CONSUMED))
            self.assertEqual(bm.get_buffs(NAME, '__enemy__', 13)['def_pct'], 10)

    def test_actual_firing_additional_hit_once_per_fullcharge(self):
        char = core.spec.build_char(NAME, build(), no_layer=True)
        result = core.simulate([char], {'duration': 8, 'rng_mode': 'expected'},
                              {'def': 0, 'core_px': 0, 'is_element_match': False},
                              seed=42, verbose=True)
        shots = [h for h in result.hits if h.skill_name == '기본 공격']
        bonus = [h for h in result.hits if h.skill_name == '셀레스티얼 헤이븐 추가 대미지']
        self.assertGreater(len(shots), 2)
        self.assertEqual([h.t for h in shots], [h.t for h in bonus])
        self.assertAlmostEqual(bonus[0].damage / shots[0].damage,
                               220.7 / (61.3 * 2.5), delta=.0001)

    def test_resurrection_penalty_changes_this_and_future_cast_cooldowns(self):
        bm, fighters = fixture(names=[NAME, *FRAY, '홍련', '크라운'])
        controller = BurstController(bm.squad, {}, fighters, {'def': 0})
        _register_instant_handlers(bm, fighters, controller)
        fallen = ['홍련', *FRAY]
        down(bm, fallen)
        controller._cast_burst(NAME, '2', 1, bm, bm.state)
        self.assertEqual(controller.burst_ready_at[NAME], 61)
        # Full Burst must not apply the40secondpenalty a second time.
        controller._phase = 'switching'
        controller._next_action_t = 1.2
        controller.tick(1.2, bm, bm.state)
        self.assertEqual(controller.burst_ready_at[NAME], 61)
        controller._cast_burst(NAME, '2', 61, bm, bm.state)
        self.assertEqual(controller.burst_ready_at[NAME], 121)
        self.assertEqual(len(bm.state['revives']), 3)

    def test_delayed_persistent_def_survives_death_before_due_time(self):
        bm, _ = fixture()
        down(bm, ['리타', *FRAY])
        bm.notify('burst_cast', 1, NAME)
        down(bm, [NAME])
        bm.tick(1.1)
        # Native OnResurrection reconnects this persistentDEF. Retaining its
        # dormant buff on the dead caster preserves that same postrevive state.
        bm.state['hp'][NAME] = 5000
        bm.sync_hp(NAME)
        self.assertEqual(bm.get_buffs(NAME, '__enemy__', 1.1)['def_pct'], 10)

    def test_actual_cover_death_and_reload_cancel_held_barrier(self):
        for reason in ('cover', 'death', 'reload'):
            bm, fighters = fixture(names=[NAME])
            cs = fighters[NAME]
            cs._hold_release_t = 5
            enemy = {'def': 0, 'core_px': 0, 'is_element_match': False}
            cfg = {'rng_mode': 'expected'}
            for at in (0, 1.01, 2.02):
                cs._tick_charge(at, bm, enemy, cfg)
            self.assertTrue(bm.has_shield(NAME), reason)
            if reason == 'reload':
                cs._start_reload(2.1, bm)
            else:
                if reason == 'cover':
                    bm.state['planned_cover'] = True
                else:
                    down(bm, [NAME])
                cs.tick(2.1, bm, enemy, cfg)
            self.assertFalse(bm.has_shield(NAME), reason)
            self.assertFalse(bm.state['full_charging'][NAME], reason)
            self.assertFalse(bm.get_buffs(NAME, '__enemy__', 2.1)['charge_speed_buff_immune'], reason)
            self.assertTrue(bm._has_self_state(NAME, BLESSING), reason)

    def test_standard_squad_manual_and_search_use_identical_production_kit(self):
        units = {n: {'id': n, 'build': build(), 'enabled': True, 'assumptions': []}
                 for n in SQUAD}
        settings = core.validate_settings({'duration': 35, 'content_mode': 'practice'})
        manual = core.simulate_manual(SQUAD, units, settings)['teams'][0]
        search = core.evaluate_candidate(SQUAD, 35, True, units, settings)
        self.assertGreater(manual['damage'], 0)
        self.assertEqual(manual['damage'], search['damage'])
        self.assertEqual(manual['builds'], search['builds'])

    def test_nearest_aim_hit_ignores_stale_historical_enemy_target(self):
        runtime = RaidBossRuntime([], 10, key='anomaly-indivilia')
        runtime.time = 1
        runtime.last_enemy_target_by_caster[NAME] = 'expired-summon'
        effect = next(e for e in char_effects(NAME, 0)
                      if e['name'] == '셀레스티얼 헤이븐 추가 대미지')
        self.assertEqual(effect['target'], 'enemies_nearest_aim:1')
        self.assertEqual(select_enemy_effect_targets(runtime, effect, NAME, 1), ['__boss__'])
        # The live damage route must forward the explicit selector too.
        hit = {'effect_target': effect['target'], 'effect_source': effect['source'],
               'effect_name': effect['name'], 'native_skill_id': effect['native_skill_id'],
               'native_target_condition': effect['native_target_condition']}
        self.assertEqual(direct_skill_enemy_targets(runtime, NAME, hit), ['__boss__'])
        runtime.adds = [{'id': 'live-summon', 'hp': 1000, 'max_hp': 1000,
                         'next_attack': 10, 'spawned': .5, 'defence': 0}]
        # Current aim can move to a living add before the next ordinary shot
        # updates historical hit bookkeeping.
        self.assertEqual(select_enemy_effect_targets(runtime, effect, NAME, 1), ['live-summon'])
        self.assertEqual(direct_skill_enemy_targets(runtime, NAME, hit), ['live-summon'])
        runtime.adds[0]['hp'] = 0
        self.assertEqual(direct_skill_enemy_targets(runtime, NAME, hit), ['__boss__'])
        # Run the actual timeline-to-encounter path too: losing selector
        # metadata there previously turned the first extra hit into zero.
        char = core.spec.build_char(NAME, build(), no_layer=True)
        traces = []
        for stale in (False, True):
            encounter = RaidBossRuntime([], 3, key='anomaly-indivilia')
            if stale:
                encounter.last_enemy_target_by_caster[NAME] = 'expired-summon'
            result = core.simulate([char], {'duration': 3, 'rng_mode': 'expected',
                                  'encounter_runtime': encounter},
                                  {'def': 0, 'core_px': 0}, seed=42, verbose=True)
            traces.append([(h.t, h.damage) for h in result.hits
                           if h.skill_name == '셀레스티얼 헤이븐 추가 대미지'])
        self.assertTrue(traces[0])
        self.assertTrue(all(damage > 0 for _, damage in traces[0]))
        self.assertEqual(traces[0], traces[1])


if __name__ == '__main__':
    unittest.main()
