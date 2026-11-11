"""Production combat and import regressions for Scarlet: Goddeath."""
import copy
import unittest
from unittest.mock import patch

import core
from calculator.buff_manager import BuffManager, char_effects
from calculator.timeline import CharState, _register_instant_handlers
from types import SimpleNamespace


NAME = '홍련 : 신살'
MARKER = '임전 : 신검합일'
MODE = '화무십일일홍 · 만개'


def build(level=10):
    result = core.default_build()
    result['skill_levels'] = dict.fromkeys(('1', '2', '3'), level)
    return result


def fixture(level=10):
    char = core.spec.build_char(NAME, build(level), no_layer=True)
    state = {'hp': {NAME:10000.0}, 'hp_pct': {NAME:100.0},
             'base_stats': {NAME:{'hp':10000.0,'atk':1000.0,'def':100.0}},
             'rng_expected':True, 'burst_gauge_charging':True}
    manager = BuffManager([char], state)
    fighter = CharState(char,1000.0,'철갑')
    _register_instant_handlers(manager,{NAME:fighter},
                               SimpleNamespace(cooldowns={},next_ready={},_cooldowns={}))
    manager.battle_start(0)
    return manager,fighter


def isolated(duration=2, own_burst=False, level=10):
    char = core.spec.build_char(NAME,build(level),no_layer=True)
    original = BuffManager.battle_start
    def start(manager,*args,**kwargs):
        original(manager,*args,**kwargs)
        if own_burst:
            manager.notify('burst_cast',0,NAME)
    with patch.object(BuffManager,'battle_start',start):
        return core.simulate([char], {'duration':duration,'rng_mode':'expected'},
                             {'def':0,'core_px':0,'is_element_match':False},
                             seed=42,verbose=True)


class GoddeathTests(unittest.TestCase):
    def test_identity_and_import_preserve_investment(self):
        row = core.CAT[NAME]
        self.assertEqual((row['name'],row['resource_id'],row['name_code']),
                         ('Scarlet: Goddeath',472,5186))
        self.assertEqual((row['element'],row['weapon'],row['role'],row['burst'],row['cooldown']),
                         ('Fire','AR','Attacker','3',40))
        self.assertTrue(row['supported'])
        self.assertEqual(len({NAME,core.NAME_MAP['scarlet'],core.NAME_MAP['scarlet: black shadow']}),3)
        imported = core.import_roster({'elements':{'Fire':[{'name_code':5186,
            'skill1_level':3,'skill2_level':7,'skill_burst_level':9,
            'limit_break':{'grade':2,'core':0}}]}})
        unit=imported['roster'][0]
        self.assertEqual(unit['id'],NAME)
        self.assertEqual(unit['build']['skill_levels'],{'1':3,'2':7,'3':9})
        unit['enabled']=False
        unit['build']['equip_skills']['max_ammo_pct']=[64.82]
        self.assertEqual(core.import_roster({'roster':[copy.deepcopy(unit)]})['roster'],[unit])

    def test_all_source_levels_and_native_weapon_overrides(self):
        effects=char_effects(NAME,0)
        self.assertEqual({e['source'] for e in effects},{'스킬1','스킬2','스킬3'})
        for effect in effects:
            for key in ('values','damage_coeff'):
                if isinstance(effect.get(key),dict):
                    self.assertEqual(set(effect[key]),{str(i) for i in range(1,11)})
        iai=next(e for e in effects if e['name']=='거합')
        self.assertEqual((iai['values']['1'],iai['values']['10']),(54.5,109))
        mode=next(e for e in effects if e['type']=='weapon_change')
        self.assertEqual((mode['damage_coeff']['1'],mode['damage_coeff']['10']),(107.57,115))
        self.assertEqual((mode['fire_rate'],mode['max_ammo'],mode['duration']),(1.5,999,10))
        self.assertEqual((mode['native_shot_id'],mode['box_width'],mode['box_height']),(1047202,2000,50))
        meta=core.META[NAME]
        self.assertEqual((meta['damage_coeff'],meta['fire_rate'],meta['max_ammo'],meta['reload_time']),
                         (107.57,1.5,9,1.17))

    def test_normal_only_critical_scope_and_own_burst_expiry(self):
        manager,_=fixture()
        before=manager.get_buffs(NAME,'__enemy__',0)
        self.assertAlmostEqual(before['crit_rate'],.5)
        self.assertAlmostEqual(before['crit_rate_skill'],.15)
        self.assertTrue(before['pierce_enabled'])
        manager.notify('burst_cast',1,NAME)
        during=manager.get_buffs(NAME,'__enemy__',1)
        self.assertAlmostEqual(during['crit_rate'],1.0)
        self.assertAlmostEqual(during['crit_rate_skill'],.15)
        self.assertEqual(during['atk_pct'],120)
        self.assertEqual(during['atk_dmg_pct'],116)
        self.assertEqual(manager.weapon_change_name(NAME),MODE)
        manager.tick(11.01)
        after=manager.get_buffs(NAME,'__enemy__',11.01)
        self.assertAlmostEqual(after['crit_rate'],.5)
        self.assertEqual(after['atk_pct'],0)
        self.assertFalse(manager.is_weapon_changed(NAME))

    def test_refund_on_two_normal_crits_blocked_during_own_burst(self):
        manager,fighter=fixture()
        fighter.ammo=3
        manager.notify('crit_hit',.1,NAME)
        self.assertEqual(fighter.ammo,3)
        manager.notify('crit_hit',.2,NAME)
        self.assertEqual(fighter.ammo,4)
        manager.notify('burst_cast',1,NAME)
        for index in range(4): manager.notify('crit_hit',2+index,NAME)
        self.assertEqual(fighter.ammo,4)
        manager.tick(11.1)
        manager.notify('crit_hit',11.2,NAME)
        manager.notify('crit_hit',11.3,NAME)
        self.assertEqual(fighter.ammo,5)
        # A full normal magazine cannot be overfilled by this skill.
        fighter.ammo=9
        manager.notify('crit_hit',12,NAME);manager.notify('crit_hit',12.1,NAME)
        self.assertEqual(fighter.ammo,9)

    def test_off_burst_only_grants_full_burst_critical_damage(self):
        manager,_=fixture()
        manager.notify('full_burst_start',1,NAME)
        stats=manager.get_buffs(NAME,'__enemy__',1)
        self.assertEqual(stats['crit_dmg'],60)
        self.assertEqual(stats['crit_dmg_skill'],60)
        self.assertAlmostEqual(stats['crit_rate'],.5)
        self.assertEqual(stats['atk_pct'],0)
        self.assertFalse(manager.is_weapon_changed(NAME))
        self.assertFalse(manager._has_self_state(NAME,MARKER))

    def test_actual_firing_one_iai_per_shot_and_only_iai_doubles(self):
        ordinary,changed=isolated(),isolated(own_burst=True)
        def hits(result,skill):
            return [h for h in result.hits if h.caster==NAME and h.skill_name==skill]
        for result in (ordinary,changed):
            shots,iai=hits(result,'기본 공격'),hits(result,'거합')
            self.assertEqual([h.t for h in shots],[h.t for h in iai])
            self.assertGreater(len(shots),2)
        base_iai=hits(ordinary,'거합')[0].damage
        burst_iai=hits(changed,'거합')[0].damage
        self.assertAlmostEqual(burst_iai,base_iai*2*2.2*2.16,delta=12)
        base_shot=hits(ordinary,'기본 공격')[0].damage
        burst_shot=hits(changed,'기본 공격')[0].damage
        self.assertAlmostEqual(burst_shot,base_shot*(115/107.57)*(1.5/1.25)*2.2*2.16,delta=12)

    def test_actual_temporary_magazine_and_normal_firing_resume(self):
        result=isolated(duration=12,own_burst=True)
        ammo=[e for e in result.log.ammo_log if e.caster==NAME]
        self.assertTrue(any(e.ammo==998 for e in ammo))
        self.assertTrue(all(9<e.ammo<=999 for e in ammo if e.t<10))
        self.assertTrue(any(e.t>=10 and e.ammo<=9 for e in ammo))
        normal=[h for h in result.hits if h.caster==NAME and h.skill_name=='기본 공격']
        self.assertGreater(len([h for h in normal if 0<=h.t<10]),10)
        self.assertTrue(any(h.t>=10 for h in normal))

    def test_two_cycle_trace_and_manual_search_agree(self):
        names=[core.NAME_MAP[n.casefold()] for n in
               ['Liter','Crown','Scarlet: Goddeath','Scarlet','Naga']]
        roster={n:{'id':n,'build':build(),'enabled':True,'assumptions':[]} for n in names}
        settings=core.validate_settings({'duration':60,'content_mode':'practice'})
        manual=core.simulate_manual(names,roster,settings)['teams'][0]
        search=core.evaluate_candidate(names,60,True,roster,settings)
        self.assertGreater(manual['damage'],0)
        self.assertEqual(manual['damage'],search['damage'])
        self.assertEqual(manual['builds'],search['builds'])
        self.assertTrue(any('Scarlet: Goddeath' in note for note in manual['warnings']))
        self.assertTrue(any('Scarlet: Goddeath' in note for note in search['warnings']))
        squad=[core.spec.build_char(n,build(),no_layer=True)
               for n in ['리틀 머메이드','크라운',NAME,'test_B3']]
        result=core.simulate(squad,{'duration':45,'rng_mode':'expected'},seed=42,verbose=True)
        own_casts=[e for e in result.log.burst_log if e.caster==NAME and '사용' in e.event]
        nuke=[h for h in result.hits if h.caster==NAME and h.skill_name=='화무십일일홍 · 신살']
        self.assertEqual(len(nuke),len(own_casts))
        full_bursts=[e for e in result.log.burst_log if e.event=='full_burst 시작']
        crit_windows=[e for e in result.log.buff_events if e.caster==NAME
                      and e.name=='화무십일일홍 · 개화' and e.kind=='activate']
        self.assertEqual(len(full_bursts),len(crit_windows))
        self.assertGreater(len(full_bursts),len(own_casts))


if __name__=='__main__':
    unittest.main()
