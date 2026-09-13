import unittest

from boss_parts import part_break_damage


class PartBreakDamageTests(unittest.TestCase):
    def test_whale_native_float_bonus_uses_broken_hp(self):
        stat={'LevelHp':5_866_372_929,'LevelBrokenHp':384_055_273}
        monster={'HpRatio':10000}
        main={'IsMainPart':True,'HpRatio':10000}
        core={'IsMainPart':False,'HpRatio':1000,'DamageHpRatio':1000}
        port={'IsMainPart':False,'HpRatio':40,'DamageHpRatio':800}
        self.assertEqual(part_break_damage(stat,monster,core,main),38_405_524)
        self.assertEqual(part_break_damage(stat,monster,port,main),30_724_420)

    def test_break_bonus_uses_main_part_scaling_not_destroyed_part_hp(self):
        stat={'LevelHp':99_000_000,'LevelBrokenHp':10_000}
        monster={'HpRatio':15000}
        main={'IsMainPart':True,'HpRatio':20000}
        part={'IsMainPart':False,'HpRatio':10,'DamageHpRatio':2500}
        self.assertEqual(part_break_damage(stat,monster,part,main),7500)
        part['HpRatio']=9000
        self.assertEqual(part_break_damage(stat,monster,part,main),7500)
        stat['LevelHp']=1
        self.assertEqual(part_break_damage(stat,monster,part,main),7500)

    def test_zero_bonus_and_default_main_ratio(self):
        stat={'LevelBrokenHp':101}
        monster={'HpRatio':10000}
        part={'IsMainPart':False,'HpRatio':100,'DamageHpRatio':0}
        self.assertEqual(part_break_damage(stat,monster,part),0)
        part['DamageHpRatio']=5000
        self.assertEqual(part_break_damage(stat,monster,part),51)

    def test_main_part_can_supply_its_own_scaling(self):
        stat={'LevelBrokenHp':100}
        monster={'HpRatio':10000}
        main={'IsMainPart':True,'HpRatio':15000,'DamageHpRatio':5000}
        self.assertEqual(part_break_damage(stat,monster,main),75)


if __name__=='__main__':
    unittest.main()
