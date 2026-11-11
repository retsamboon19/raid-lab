"""The installed visible roster must be complete, not just the newest pickup."""
import copy
import json
from pathlib import Path
import unittest
from types import SimpleNamespace

import core
from calculator.buff_manager import char_effects
from calculator.buff_manager import BuffManager
from raid_boss_combat import RaidBossRuntime


class CurrentRosterTests(unittest.TestCase):
    def test_all_four_additions_share_manual_and_search_execution(self):
        names = [core.NAME_MAP['liter']] + [core.CODE_MAP[str(code)] for code in (5184, 5187, 5185, 5186)]
        roster = {n: {'id': n, 'build': core.default_build(), 'enabled': True, 'assumptions': []}
                  for n in names}
        settings = core.validate_settings({'duration': 65, 'content_mode': 'practice'})
        manual = core.simulate_manual(names, roster, settings)['teams'][0]
        candidate = core.evaluate_candidate(names, 65, True, roster, settings)
        self.assertEqual(manual['damage'], candidate['damage'])
        self.assertEqual(manual['breakdown'], candidate['breakdown'])
        self.assertEqual(manual['builds'], candidate['builds'])
        self.assertTrue(all(manual['breakdown'][n] > 0 for n in names))
        self.assertTrue(any('Marian: Queen' in warning for warning in manual['warnings']))

    def test_pumpkin_stealth_in_actual_boss_target_and_damage_paths(self):
        witch = core.CODE_MAP['5184']
        names = [witch, core.NAME_MAP['liter']]
        for defense in ('none', 'cover', 'shield'):
            with self.subTest(defense=defense):
                chars = [core.spec.build_char(n, core.default_build(), no_layer=True) for n in names]
                bm = BuffManager(chars, {'hp': dict.fromkeys(names, 10000.),
                    'hp_pct': dict.fromkeys(names, 100.),
                    'base_stats': {n: {'hp': 10000., 'atk': 1000., 'def': 0.} for n in names}})
                bm.battle_start(0)
                runtime = RaidBossRuntime([], 30, key='anomaly-ultra', auto_cover=False)
                runtime.bind(bm, chars, {n: SimpleNamespace(base_atk=1000., weapon_type='RL',
                    fire_rate=1., charge_time_base=1., reloading_until=0) for n in names})
                runtime.time = 2
                bm.notify('full_burst_start', 1, witch)
                skill = dict(runtime.skills[1], FireType='Direct', TargetCount=1, ShotCount=1,
                    SkillValue01=10000, TargetCharacterRatio=100, TargetCoverRatio=0, TargetNothingRatio=0)
                self.assertEqual(runtime.attack_targets(skill, {}), [names[1]])
                aoe = dict(skill, FireType='DirectAll', TargetCount=5)
                self.assertEqual(runtime.attack_targets(aoe, {}), names)
                runtime.cover.update(dict.fromkeys(names, 10000. if defense == 'cover' else 0.))
                runtime.covered = {witch} if defense == 'cover' else set()
                if defense == 'shield':
                    bm._activate({'type': 'buff', 'source': 'test', 'name': 'Test shield',
                        'stat': 'shield_from_max_hp_pct', 'fixed_value': 100., 'target': 'self',
                        'duration': 10, 'max_stack': 1, 'trigger': {'timing': [], 'condition': []}}, witch, 1)
                runtime.hurt_functions = lambda *args, **kwargs: []
                node = {'_incoming_snapshot': {'attack': 100., 'stat_ratio': 10000,
                    'element_multiplier': 1, 'element_id': 100001}}
                runtime.receive_attack(aoe, node)
                self.assertEqual(bm._has_self_state(witch, '유령 분장'), defense != 'none')
                incoming = next(row for row in runtime.incoming if row['target'] == witch)
                self.assertEqual(incoming['blocked_by'], None if defense == 'none' else defense)

    def test_entire_installed_visible_roster_has_combat_support(self):
        manifest = json.loads(Path(__file__).with_name('current-roster.json').read_text(encoding='utf-8'))
        expected = set(manifest['visible_resource_ids'])
        actual = {c['resource_id'] for c in core.CATALOG}
        self.assertEqual(actual, expected)
        self.assertEqual(len(core.CATALOG), len(actual))
        self.assertTrue(all(c['supported'] for c in core.CATALOG))

    def test_added_characters_keep_distinct_imports_and_investment(self):
        for english, resource, code in (
            ('Belorta: Pumpkin Witch', 63, 5184),
            ('Marian: Queen', 19, 5185),
            ('Scarlet: Goddeath', 472, 5186),
            ('Rapunzel: Sanctuary', 473, 5187),
        ):
            with self.subTest(character=english):
                name = core.CODE_MAP[str(code)]
                unit = core.CAT[name]
                self.assertEqual((unit['name'], unit['resource_id']), (english, resource))
                self.assertEqual(core.NAME_MAP[english.casefold()], name)
                row = core.import_roster({'elements': {unit['element']: [{
                    'name_code': code, 'skill1_level': 3, 'skill2_level': 7,
                    'skill_burst_level': 9, 'limit_break': {'grade': 2, 'core': 0},
                }]}})['roster'][0]
                self.assertEqual(row['build']['skill_levels'], {'1': 3, '2': 7, '3': 9})
                row['enabled'] = False
                row['build']['equip_skills']['max_ammo_pct'] = [64.82]
                self.assertEqual(core.import_roster({'roster': [copy.deepcopy(row)]})['roster'], [row])
                effects = char_effects(name, 0)
                self.assertEqual({e['source'] for e in effects}, {'스킬1', '스킬2', '스킬3'})
                for effect in effects:
                    for key in ('values', 'damage_coeff', 'duration_values'):
                        if isinstance(effect.get(key), dict):
                            self.assertEqual(set(effect[key]), {str(i) for i in range(1, 11)})


if __name__ == '__main__':
    unittest.main()
