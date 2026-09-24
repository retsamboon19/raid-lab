"""Coin Rush catalogue identities must survive each supported import format."""
import copy
import unittest
from unittest.mock import patch

import core
from calculator.buff_manager import BuffManager


class CharacterUpdateTests(unittest.TestCase):
    def test_new_identity_and_investment_roundtrip(self):
        for english, resource, code in (
            ('Guilty: Mighty Bunny', 404, 5182),
            ('Sin: Swift Bunny', 405, 5183),
        ):
            with self.subTest(character=english):
                unit = core.CAT[core.CODE_MAP[str(code)]]
                self.assertEqual(unit['name'], english)
                self.assertEqual(unit['resource_id'], resource)
                self.assertEqual((unit['element'], unit['weapon'], unit['burst'], unit['cooldown']),
                                 ('Water', 'SR', '3', 40))
                self.assertTrue(unit['supported'])
                imported = core.import_roster({'elements': {'Water': [{
                    'name_code': code, 'skill1_level': 3, 'skill2_level': 7,
                    'skill_burst_level': 9, 'limit_break': {'grade': 2, 'core': 0},
                }]}})
                row = imported['roster'][0]
                self.assertEqual(row['id'], unit['id'])
                self.assertEqual(row['build']['skill_levels'], {'1': 3, '2': 7, '3': 9})
                row['enabled'] = False
                row['build']['equip_skills']['max_ammo_pct'] = [64.82]
                saved = copy.deepcopy(row)
                self.assertEqual(core.import_roster({'roster': [row]})['roster'], [saved])
                self.assertEqual(core.NAME_MAP[english.casefold()], unit['id'])

    def test_original_versions_remain_distinct(self):
        for original, alternate in [('Guilty', 'Guilty: Mighty Bunny'), ('Sin', 'Sin: Swift Bunny')]:
            self.assertNotEqual(core.NAME_MAP[original.casefold()], core.NAME_MAP[alternate.casefold()])
        codes = [c['name_code'] for c in core.CATALOG]
        self.assertEqual(len(codes), len(set(codes)))

    def test_bunny_mode_settings_and_single_operator(self):
        self.assertEqual(core.validate_settings({})['bunny_mode'], 'stance')
        with self.assertRaisesRegex(ValueError, 'bunny_mode'):
            core.validate_settings({'bunny_mode': 'guess'})
        for english in (
            ['Guilty: Mighty Bunny', 'Sin: Swift Bunny', 'Liter', 'Crown', 'Naga'],
            ['Sin: Swift Bunny', 'Guilty: Mighty Bunny', 'Liter', 'Crown', 'Naga'],
            ['Guilty: Mighty Bunny', 'Scarlet', 'Liter', 'Crown', 'Naga'],
            ['Sin: Swift Bunny', 'Scarlet', 'Liter', 'Crown', 'Naga'],
        ):
            names = [core.NAME_MAP[n.casefold()] for n in english]
            for playstyle in ('auto', 'assisted'):
                settings = core.validate_settings({'playstyle': playstyle, 'bunny_mode': 'engage'})
                squad = core.spec.build_squad(names, chars={n: core.default_build() for n in names}, no_layer=set(names))
                core.apply_squad_controls(squad, settings)
                operators = [c['name'] for c in squad if c['control'].get('sequence')]
                self.assertEqual(operators, [min((n for n in names if core.CAT[n]['resource_id'] in (404,405)), key=lambda n: core.CAT[n]['resource_id'])])
                # Check real frame execution, including the priority over assisted taps.
                managers = []
                original_start = BuffManager.battle_start
                def capture_start(manager, *args, **kwargs):
                    managers.append(manager)
                    return original_start(manager, *args, **kwargs)
                with patch.object(BuffManager, 'battle_start', capture_start):
                    result = core.simulate(squad, {'duration': 4, 'rng_mode': 'expected'}, seed=42)
                self.assertGreater(result.squad_total, 0)
                modes = {name: [a.effect['name'] for a in managers[0]._active
                                if name in (a.target_chars or []) and
                                a.effect.get('name') in ('바니 모드 : 스탠스', '바니 모드 : 인게이지')]
                         for name in names}
                for name in names:
                    expected = ['바니 모드 : 인게이지'] if core.CAT[name]['resource_id'] in (404, 405) else []
                    self.assertEqual(modes[name], expected)

    def test_manual_and_search_apply_identical_bunny_inputs(self):
        names = [core.NAME_MAP[n.casefold()] for n in
                 ['Liter', 'Crown', 'Guilty: Mighty Bunny', 'Sin: Swift Bunny', 'Naga']]
        roster = {n: {'id': n, 'build': core.default_build(), 'enabled': True, 'assumptions': []}
                  for n in names}
        for mode in ('stance', 'engage'):
            settings = core.validate_settings({'duration': 30, 'bunny_mode': mode})
            manual = core.simulate_manual(names, roster, settings)['teams'][0]
            search = core.evaluate_candidate(names, 30, True, roster, settings)
            self.assertAlmostEqual(manual['damage'], search['damage'])
            self.assertEqual(manual['builds'], search['builds'])


if __name__ == '__main__':
    unittest.main()
