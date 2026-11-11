"""Source-bound Marian: Queen production mechanics regressions."""
import random
import unittest
from types import SimpleNamespace
from unittest.mock import patch

import core
from calculator.buff_manager import BuffManager, char_effects
from calculator.timeline import CharState, _register_instant_handlers
from runner.kits_marian_queen import NAME, FRAY, WISH, WOUND, SPEAR, CORE
from anomaly_target_context import direct_skill_enemy_targets, select_enemy_effect_targets



def build(level=10):
    value = core.default_build()
    value['skill_levels'] = dict.fromkeys(('1', '2', '3'), level)
    return value


def fixture(level=10):
    char = core.spec.build_char(NAME, build(level), no_layer=True)
    state = {'hp': {NAME:10000.}, 'hp_pct': {NAME:100.},
             'base_stats': {NAME:{'hp':10000., 'atk':1000., 'def':100.}},
             'rng_expected': True, 'burst_gauge_charging':True}
    bm = BuffManager([char], state)
    fighter = CharState(char,1000.,'철갑')
    _register_instant_handlers(bm,{NAME:fighter},SimpleNamespace(cooldowns={},next_ready={},_cooldowns={}))
    bm.battle_start(0.)
    return bm,fighter


def isolated(duration=10, own=False, off=False):
    original = BuffManager.battle_start
    def start(bm,*args,**kwargs):
        original(bm,*args,**kwargs)
        if own: bm.notify('burst_cast',0,NAME)
        if own or off: bm.notify('full_burst_start',0,NAME)
    char=core.spec.build_char(NAME,build(),no_layer=True)
    with patch.object(BuffManager,'battle_start',start):
        return core.simulate([char],{'duration':duration,'rng_mode':'expected'},
            {'def':0,'core_px':0,'is_element_match':False},seed=42,verbose=True)


def named(result,name):
    return [hit for hit in result.hits if hit.caster==NAME and hit.skill_name==name]


class MarianQueenTests(unittest.TestCase):
    def test_identity_and_import_levels(self):
        row=core.CAT[NAME]
        self.assertEqual((row['name'],row['resource_id'],row['name_code']),('Marian: Queen',19,5185))
        self.assertEqual((row['weapon'],row['element'],row['burst'],row['cooldown']),('MG','Fire','3',40))
        imported=core.import_roster({'elements':{'Fire':[{'name_code':5185,
            'skill1_level':2,'skill2_level':7,'skill_burst_level':9,
            'limit_break':{'grade':1,'core':0}}]}})['roster'][0]
        self.assertEqual(imported['id'],NAME)
        self.assertEqual(imported['build']['skill_levels'],{'1':2,'2':7,'3':9})

    def test_every_level_maps_canonical_slots_without_interpolation(self):
        effects=char_effects(NAME,0)
        mapping=[(SPEAR,1,0),(WOUND,1,2),(CORE,2,1),
                 ('유사 세계 · 순차 공격',2,4),('유사 세계 · 코어 대미지',2,6),
                 ('머나먼 신세계 [1]',3,0),('머나먼 신세계 [2]',3,1),
                 ('머나먼 신세계 [3]',3,3),('머나먼 신세계 [4]',3,5),('머나먼 신세계',3,7)]
        for name,slot,index in mapping:
            effect=next(e for e in effects if e['name']==name)
            self.assertEqual(set(effect['values']),set(map(str,range(1,11))))
            raw=list(core.RAW[NAME]['스킬'].values())[slot-1]
            for level in range(1,11):
                self.assertEqual(effect['values'][str(level)],float(raw['values'][str(level)][index]),(name,level))
        # Exact uneven source increments are retained at intermediate levels.
        self.assertEqual(next(e for e in effects if e['name']==CORE)['values']['4'],10.22)
        self.assertEqual(next(e for e in effects if e['name']==SPEAR)['values']['10'],125.51)
        self.assertEqual(next(e for e in effects if e['name']==WOUND)['values']['10'],5.05)

    def test_own_and_offburst_are_distinct_and_expire(self):
        bm,fighter=fixture()
        self.assertTrue(bm._has_self_state(NAME,FRAY))
        bm.notify('full_burst_start',0,NAME)
        self.assertEqual(bm.get_buffs(NAME,'__enemy__',0)['sequential_dmg_pct'],85.17)
        self.assertEqual(bm.get_buffs(NAME,'__enemy__',0)['core_dmg_pct'],0)
        bm.tick(10.1)
        fighter.ammo=1
        bm.notify('burst_cast',11,NAME)
        self.assertEqual(fighter.ammo,fighter._full_ammo(bm,11))
        bm.notify('full_burst_start',11,NAME)
        buffs=bm.get_buffs(NAME,'__enemy__',11)
        self.assertEqual((buffs['atk_pct'],buffs['atk_dmg_pct'],buffs['mg_warmup_speed_pct'],buffs['core_dmg_pct']),
                         (78.4,78.14,100,24.64))
        self.assertEqual(buffs['sequential_dmg_pct'],0)
        bm.tick(21.1)
        self.assertFalse(bm._has_self_state(NAME,WISH))
        self.assertTrue(bm._has_self_state(NAME,FRAY))
        self.assertEqual(bm.get_buffs(NAME,'__enemy__',21.1)['received_dmg'],5.05)

    def test_wound_refreshes_instead_of_stacking_across_activation_paths(self):
        bm,_=fixture()
        bm.notify('burst_cast',0,NAME)
        bm.notify('hit_count:'+SPEAR,1,NAME)
        bm.notify('hit_count:'+SPEAR,2,NAME)
        self.assertEqual(bm.get_buffs(NAME,'__enemy__',2)['received_dmg'],5.05)
        self.assertEqual(len([a for a in bm._active if a.effect['name']==WOUND]),1)
        self.assertTrue(all(e.get('undispellable') for e in char_effects(NAME,0) if e['name']==WOUND))

    def test_periodic_seven_hits_and_first_hit_debuff_order(self):
        result=isolated(duration=9.3)
        hits=named(result,SPEAR)
        self.assertEqual(len(hits),14)
        self.assertAlmostEqual(hits[0].t,4,delta=.025)
        self.assertAlmostEqual(hits[7].t,8,delta=.025)
        for left,right in zip(hits[:6],hits[1:7]):self.assertAlmostEqual(right.t-left.t,.2,delta=.025)
        self.assertAlmostEqual(hits[1].damage/hits[0].damage,1.0505,delta=.0001)
        self.assertEqual(len(named(result,CORE)),0)
        off=isolated(duration=5.3,off=True)
        self.assertAlmostEqual(named(off,SPEAR)[0].damage/hits[0].damage,1.8517,delta=.0001)

    def test_ownburst_two_second_spears_core_every_two_shots_and_marker_end(self):
        result=isolated(duration=12,own=True)
        spears=named(result,SPEAR)
        self.assertAlmostEqual(spears[0].t,2,delta=.025)
        self.assertAlmostEqual(spears[7].t,4,delta=.025)
        self.assertEqual(spears[0].damage,spears[1].damage)
        shots=[h for h in result.hits if h.caster==NAME and h.skill_name=='기본 공격' and h.t<10]
        cores=named(result,CORE)
        self.assertEqual(len(cores),len(shots)//2)
        self.assertEqual([h.t for h in cores],[h.t for h in shots[1::2]])
        self.assertTrue(all(h.t<10 for h in cores))
        self.assertGreater(len(named(result,'머나먼 신세계')),0)

    def test_wounded_filter_is_per_enemy_and_excludes_expired_or_unwounded(self):
        active=SimpleNamespace(effect={'name':WOUND},enemy_target_windows={
            'wounded':{'activated_at':0,'expires_at':99},
            'expired':{'activated_at':0,'expires_at':1}})
        runtime=SimpleNamespace(time=2,bm=SimpleNamespace(_active=[active],_notify_ctx={}),rng=random.Random(1))
        entities=[{'id':x} for x in ('wounded','expired','fresh')]
        with patch('anomaly_target_context._enemy_entities',return_value=entities):
            targets=direct_skill_enemy_targets(runtime,NAME,{'effect_target':'all_enemies',
                'effect_name':CORE,'required_target_state':WOUND})
            self.assertEqual(targets,['wounded'])
            self.assertEqual(select_enemy_effect_targets(runtime,{'target':'enemies_with_buff:'+WOUND},NAME,2),['wounded'])

    def test_two_cycle_manual_and_search_match(self):
        names=[core.NAME_MAP[n.casefold()] for n in ['Liter','Crown','Marian: Queen','Scarlet: Goddeath','Naga']]
        roster={n:{'id':n,'build':build(),'enabled':True,'assumptions':[]} for n in names}
        settings=core.validate_settings({'duration':65,'content_mode':'practice'})
        manual=core.simulate_manual(names,roster,settings)['teams'][0]
        search=core.evaluate_candidate(names,65,True,roster,settings)
        self.assertEqual(manual['damage'],search['damage'])
        self.assertEqual(manual['builds'],search['builds'])
        self.assertGreater(manual['damage'],0)


if __name__=='__main__': unittest.main()
