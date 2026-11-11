"""Replay original native formula observations, not simulator-generated values."""
import unittest
from types import SimpleNamespace
import core
from raid_boss_combat import RaidBossRuntime
from enemy_damage import incoming_hit


class NativeFunctionDamageTests(unittest.TestCase):
    def test_indivilia_original_function_1999539_observations(self):
        # Original packet c7223c62ef7cb867064d1f31; sourceId1999539,
        # damageRatio6, statDamageRatio1. Enemy weapon ratio is about25x.
        samples=[(71370,64163,43.23,24548),(71370,72405,43.23,1),
                 (71370,25381,17,229025),(111339,27776,43.23,284632)]
        runtime=object.__new__(RaidBossRuntime)
        for attack,defence,reduction,expected in samples:
            runtime.bm=SimpleNamespace(_effective_def=lambda _:defence)
            runtime.active_stat=lambda *_:-reduction
            with self.subTest(attack=attack,defence=defence):
                actual=runtime.hurt_function_damage({'FunctionType':'Damage','FunctionValue':60000},
                    'recipient',attack,{'LevelStatdamageratio':255250})
                self.assertEqual(actual,expected)

    def test_current_hp_function_keeps_its_hp_basis(self):
        runtime=object.__new__(RaidBossRuntime)
        runtime.bm=SimpleNamespace(state={'hp':{'recipient':2000000}})
        runtime.cover={'recipient':1000000}
        function={'FunctionType':'CurrentHpRatioDamage','FunctionValue':2000}
        self.assertEqual(runtime.hurt_function_damage(function,'recipient',71370,{},False),400000)
        self.assertEqual(runtime.hurt_function_damage(function,'recipient',71370,{},True),200000)

    def test_weapon_hit_still_uses_original_level_ratio(self):
        self.assertEqual(round(incoming_hit(48307,34296,500,250917,5)*(1-.17)),2918)


if __name__=='__main__':unittest.main()
