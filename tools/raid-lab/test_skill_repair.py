import unittest
from types import SimpleNamespace
from test_complete_roster import manager, buff
from calculator.buff_manager import char_effects
from calculator import roster_mechanics as kits
import unit_combat


class OriginalSkillRepairTests(unittest.TestCase):
    def test_moran_and_laplace_cannot_cover_during_burst_mode(self):
        for name in ('Moran', 'Laplace'):
            with self.subTest(name=name):
                bm,(n,),states=manager(name)
                mode=next(e for e in char_effects(n,0) if e['type']=='weapon_change')
                restriction=next(e for e in char_effects(n,0) if e.get('stat')=='cover_disabled')
                bm._activate(restriction,n,0)  # passive registration at battle start
                bm._activate(mode,n,0)
                runtime=SimpleNamespace(bm=bm,time=1,covered={n},char_states=states)
                self.assertFalse(kits.can_cover(bm,n,1))
                self.assertFalse(unit_combat.hiding(runtime,n))
                states[n]._enter_cover(1,bm,3,'test')
                self.assertLess(states[n]._cover_until,0)
                bm.end_weapon_change(n,2)
                self.assertTrue(kits.can_cover(bm,n,2))
                self.assertTrue(unit_combat.hiding(runtime,n))

    def test_rosanna_removes_five_removable_buffs_preserving_other_effects(self):
        bm,(n,),_=manager('Rosanna')
        for i in range(7):
            e=buff('atk_pct',target='all_enemies',value=10)
            e['name']='enemy buff '+str(i)
            bm._activate(e,n,0)
        for polarity in ('harmful','beneficial_irremovable','neutral'):
            e=buff('def_pct',target='all_enemies',value=10)
            e.update(name=polarity,polarity=polarity)
            bm._activate(e,n,0)
        cleanse=next(e for e in char_effects(n,0) if e.get('stat')=='enemy_buff_cleanse')
        self.assertEqual(cleanse['fixed_value'],5)  # original Function228011004
        bm._activate(cleanse,n,1)
        remaining=[ab.effect['name'] for ab in bm._active]
        self.assertEqual(sum(x.startswith('enemy buff ') for x in remaining),2)
        for name in ('harmful','beneficial_irremovable','neutral'):self.assertIn(name,remaining)

    def test_nayuta_original_transformed_shot_is_sniper(self):
        bm,(n,),_=manager('Nayuta')
        mode=next(e for e in char_effects(n,0) if e['type']=='weapon_change')
        self.assertEqual(mode['weapon_type'],'SR')  # original CharacterShot1022302
        self.assertEqual(mode['charge_time'],1.8)
        self.assertEqual(mode['full_charge_mult'],250)


if __name__=='__main__':unittest.main()
