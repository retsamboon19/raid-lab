import unittest
import copy
from unittest.mock import patch
from types import SimpleNamespace as E
import core
import burst_rotation
from validate_pairing_runtime import build


class BurstRotationTests(unittest.TestCase):
    def simulate(self,names,duration=90,required=False,favorite_phase=0):
        ids=[core.NAME_MAP[n.lower()] for n in names]
        roster={n:dict(id=n,build=build(),enabled=True,assumptions=[]) for n in ids}
        for row in roster.values():row['build']['favorite_stage']=favorite_phase
        s=core.validate_settings(dict(content_mode='practice',duration=duration,element='Any'))
        s['_rotation_required']=required
        return core.evaluate_candidate(tuple(ids),duration,True,roster,s)

    def test_arcana_isabel_needs_coverage_despite_cdr(self):
        team=['Liter','Arcana','Isabel','Modernia','Privaty']
        r=self.simulate(team)
        self.assertFalse(r['burst_rotation']['covered'])
        with self.assertRaisesRegex(ValueError,'Burst 2'):
            self.simulate(team,required=True)

    def test_arcana_isabel_with_second_b2(self):
        r=self.simulate(['Liter','Arcana','Crown','Isabel','Modernia'],required=True)
        self.assertTrue(r['burst_rotation']['covered'])
        b2=core.NAME_MAP['crown']
        self.assertTrue(any(e['unit']==b2 and e['event']=='stage:2 사용' for e in r['burst_log']))

    def test_blanc_real_personal_cdr_exception(self):
        r=self.simulate(['Liter','Blanc','Isabel','Modernia','Noir'],required=True)
        self.assertTrue(r['burst_rotation']['covered'])
        r=self.simulate(['Liter','Blanc','Isabel','Modernia','Privaty'])
        self.assertFalse(r['burst_rotation']['covered'])

    def test_two_40_second_b2_can_alternate(self):
        r=self.simulate(['Liter','Mast: Romantic Maid','Anchor: Innocent Maid','Scarlet','Modernia'],required=True)
        casts={e['unit'] for e in r['burst_log'] if e['event']=='stage:2 사용'}
        self.assertEqual(len(casts),2)

    def test_long_b1_delay_is_not_overlooked(self):
        cat={'b1':dict(burst='1',cooldown=40),'b2':dict(burst='2',cooldown=20)}
        events=[E(t=0,event='→ 1단계 진입',caster=''),E(t=0,event='stage:1 사용',caster='b1'),
                E(t=12,event='→ 1단계 진입',caster=''),E(t=40,event='stage:1 사용',caster='b1')]
        r=burst_rotation.report(list(cat),cat,events,60)
        self.assertFalse(r['covered'])
        self.assertEqual(r['support_stages'][0]['excess_delay'],20)

    def test_real_40_second_b1_needs_backup(self):
        r=self.simulate(['Moran','Crown','Isabel','Modernia','Privaty'])
        self.assertFalse(r['burst_rotation']['covered'])
        r=self.simulate(['Moran','Liter','Crown','Isabel','Modernia'],required=True)
        self.assertTrue(r['burst_rotation']['covered'])

    def test_favorite_item_can_supply_real_b1_cooldown_coverage(self):
        r=self.simulate(['Moran','Crown','Isabel','Modernia','Privaty'],required=True,favorite_phase=3)
        self.assertTrue(r['burst_rotation']['covered'])

    def test_isabel_shortening_applies_only_to_her_burst(self):
        r=self.simulate(['Liter','Crown','Isabel','Scarlet','Privaty'])
        windows=[w for w in r['burst_rotation']['full_bursts'] if w['complete']]
        for name,seconds in [('Isabel',5),('Scarlet',10)]:
            actual=[w['seconds'] for w in windows if w['unit']==core.NAME_MAP[name.lower()]]
            self.assertTrue(actual)
            self.assertTrue(all(abs(x-seconds)<.11 for x in actual),actual)

    def test_soda_extends_even_when_another_b3_bursts(self):
        r=self.simulate(['Tove','Leona','Scarlet','Soda: Twinkling Bunny','Privaty'])
        first=r['burst_rotation']['full_bursts'][0]
        self.assertEqual(first['unit'],core.NAME_MAP['scarlet'])
        self.assertAlmostEqual(first['seconds'],15,delta=.11)

    def test_soda_and_isabel_duration_effects_combine(self):
        r=self.simulate(['Liter','Crown','Isabel','Soda: Twinkling Bunny','Privaty'])
        first=r['burst_rotation']['full_bursts'][0]
        self.assertEqual(first['unit'],core.NAME_MAP['isabel'])
        self.assertAlmostEqual(first['seconds'],10,delta=.11)

    def test_soda_stack_thresholds_control_extension(self):
        soda=core.NAME_MAP['soda: twinkling bunny']
        original=core.char_effects
        for stacks,seconds in [(0,10),(10,12),(20,15)]:
            def effects(name,favorite_stage=None):
                rows=copy.deepcopy(original(name,favorite_stage))
                if name==soda:
                    for e in rows:
                        if e.get('stat')=='buff_stack_init':e['values']={str(i):stacks for i in range(1,11)}
                return rows
            with self.subTest(stacks=stacks),patch('calculator.buff_manager.char_effects',side_effect=effects):
                r=self.simulate(['Tove','Leona','Scarlet','Soda: Twinkling Bunny','Privaty'],duration=30)
                self.assertAlmostEqual(r['burst_rotation']['full_bursts'][0]['seconds'],seconds,delta=.11)

    def test_modernia_extension_only_when_she_bursts(self):
        r=self.simulate(['Liter','Crown','Modernia','Scarlet','Privaty'])
        windows=[w for w in r['burst_rotation']['full_bursts'] if w['complete']]
        for name,seconds in [('Modernia',15),('Scarlet',10)]:
            actual=[w['seconds'] for w in windows if w['unit']==core.NAME_MAP[name.lower()]]
            self.assertTrue(actual)
            self.assertTrue(all(abs(x-seconds)<.11 for x in actual),actual)


if __name__=='__main__':unittest.main()
