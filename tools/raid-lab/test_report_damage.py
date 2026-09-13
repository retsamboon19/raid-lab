import copy
import unittest

import core


class DamageAccountingTests(unittest.TestCase):
    def test_boss_objective_and_character_totals_remain_separate(self):
        team=dict(members=['a','b'],damage=300,breakdown={'a':100,'b':200},
            encounter_timeline=dict(part_break_damage=50,boss_hp_damage=350,
                                    add_damage_by_unit={'a':80,'b':20}))
        core.attach_combat_assessment(team)
        self.assertEqual(team['damage'],300)
        self.assertEqual(team['breakdown'],{'a':100,'b':200})
        accounting=copy.deepcopy(team['damage_accounting'])
        self.assertEqual(accounting['boss_hp_loss'],350)
        self.assertEqual(accounting['all_targets_direct'],400)
        self.assertEqual(accounting['by_unit']['a']['all_targets_direct'],180)
        core.attach_combat_assessment(team)
        self.assertEqual(team['damage_accounting'],accounting)

    def test_missing_summon_statistics_are_unknown(self):
        team=dict(members=['a'],damage=100,breakdown={'a':100},
            encounter_timeline=dict(part_break_damage=50,boss_hp_damage=150))
        core.attach_combat_assessment(team)
        self.assertIsNone(team['damage_accounting']['summon_direct'])
        self.assertIsNone(team['damage_accounting']['all_targets_direct'])
        self.assertEqual(team['damage_accounting']['by_unit'],{})


if __name__=='__main__':unittest.main()
