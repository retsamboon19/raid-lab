"""Production runtime regressions for Belorta: Pumpkin Witch's complete kit."""
import unittest
from types import SimpleNamespace
from unittest.mock import patch

import core
import unit_combat
from calculator import roster_mechanics
from calculator.buff_manager import BuffManager, char_effects
from calculator.timeline import CharState, _register_instant_handlers

NAME = '벨로타 : 펌킨 위치'
GHOST = '유령 분장'
RIGHT = '홍련'
LEFT = '리타'


def build(level=10):
    result = core.default_build()
    result['skill_levels'] = dict.fromkeys(('1', '2', '3'), level)
    return result


def fixture(names=(LEFT, NAME, RIGHT), level=10):
    chars = [core.spec.build_char(n, build(level), no_layer=True) for n in names]
    state = {'hp':dict.fromkeys(names,10000.), 'hp_pct':dict.fromkeys(names,100.),
             'base_stats':{n:{'hp':10000.,'atk':1000. if n==NAME else 2000.,'def':0.} for n in names},
             'rng_expected':True}
    manager=BuffManager(chars,state)
    fighters={c['name']:CharState(c,1000.,'수냉') for c in chars}
    _register_instant_handlers(manager,fighters,SimpleNamespace(cooldowns={},next_ready={},_cooldowns={}))
    manager.battle_start(0)
    return manager


class BelortaWitchTests(unittest.TestCase):
    def test_identity_levels_weapon_and_import(self):
        row=core.CAT[NAME]
        self.assertEqual((row['name'],row['resource_id'],row['name_code']),('Belorta: Pumpkin Witch',63,5184))
        self.assertEqual((row['element'],row['weapon'],row['role'],row['burst'],row['cooldown']),('Water','RL','Supporter','2',40))
        self.assertTrue(row['supported'])
        meta=core.META[NAME]
        self.assertEqual((meta['damage_coeff'],meta['max_ammo'],meta['reload_time'],meta['charge_time'],meta['full_charge_mult']),(61.3,6,2.,1.,250.))
        for effect in char_effects(NAME,0):
            if 'values' in effect:
                self.assertEqual(set(effect['values']),{str(i) for i in range(1,11)})
        imported=core.import_roster({'elements':{'Water':[{'name_code':5184,'skill1_level':2,'skill2_level':6,'skill_burst_level':9}]}})['roster'][0]
        self.assertEqual(imported['id'],NAME)
        self.assertEqual(imported['build']['skill_levels'],{'1':2,'2':6,'3':9})

    def test_all_ten_levels_drive_runtime_values(self):
        by_group={e['native_function_group']:e for e in char_effects(NAME,0)}
        for level in range(1,11):
            with self.subTest(level=level):
                bm=fixture(level=level)
                bm.notify('full_burst_start',1,NAME)
                bm.notify('full_charge',1,NAME)
                bm.notify('full_charge_hit',1,NAME)
                bm.notify('burst_cast',1,NAME)
                value=lambda group:by_group[group]['values'][str(level)]
                buffs=bm.get_buffs(RIGHT,'__enemy__',1)
                self.assertAlmostEqual(buffs['atk_flat'],10*(value(2063103)+value(1063305)))
                self.assertAlmostEqual(buffs['dot_dmg_pct'],value(2063202)+value(1063306))
                self.assertAlmostEqual(buffs['received_dmg'],value(2063201))
                self.assertAlmostEqual(bm.effective_max_hp(NAME),10000*(1+value(2063102)/100))

    def test_full_burst_right_slot_hp_and_burst_groups_add(self):
        bm=fixture()
        bm.notify('full_burst_start',1,NAME)
        self.assertTrue(bm._has_self_state(NAME,GHOST))
        self.assertAlmostEqual(bm.effective_max_hp(NAME),11584.)
        self.assertAlmostEqual(bm.state['hp'][NAME],11584.)
        self.assertAlmostEqual(bm.get_buffs(RIGHT,'__enemy__',1)['atk_flat'],448.8)
        for n in (LEFT,NAME): self.assertEqual(bm.get_buffs(n,'__enemy__',1)['atk_flat'],0)
        bm.notify('burst_cast',2,NAME)
        bm.notify('full_charge',2,NAME)
        buffs=bm.get_buffs(RIGHT,'__enemy__',2)
        self.assertAlmostEqual(buffs['atk_flat'],924.)
        self.assertAlmostEqual(buffs['dot_dmg_pct'],47.2)
        bm.tick(7.01)
        self.assertAlmostEqual(bm.get_buffs(RIGHT,'__enemy__',7.01)['dot_dmg_pct'],27.23)
        bm.tick(11.01)
        self.assertFalse(bm._has_self_state(NAME,GHOST))
        self.assertEqual(bm.effective_max_hp(NAME),10000.)
        self.assertAlmostEqual(bm.get_buffs(RIGHT,'__enemy__',11.01)['atk_flat'],475.2)
        bm.tick(12.01)
        self.assertEqual(bm.get_buffs(RIGHT,'__enemy__',12.01)['atk_flat'],0)

    def test_right_edge_and_dead_neighbor_never_redirect(self):
        for names,dead in [((LEFT,RIGHT,NAME),None),((NAME,LEFT,RIGHT),LEFT)]:
            with self.subTest(names=names,dead=dead):
                bm=fixture(names)
                if dead:
                    bm.state['hp'][dead]=0;bm.sync_hp(dead)
                self.assertEqual(bm._resolve_target('allies_right',NAME),[])
                bm.notify('full_burst_start',1,NAME);bm.notify('burst_cast',1,NAME);bm.notify('full_charge',1,NAME)
                for n in names:
                    self.assertEqual(bm.get_buffs(n,'__enemy__',1)['atk_flat'],0)
                    self.assertEqual(bm.get_buffs(n,'__enemy__',1)['dot_dmg_pct'],0)

    def test_charge_shot_hit_and_state_gate_are_distinct(self):
        bm=fixture()
        bm.notify('full_charge_hit',.1,NAME)
        self.assertEqual(bm.get_buffs(RIGHT,'__enemy__',.1)['received_dmg'],0)
        self.assertEqual(bm.get_buffs(RIGHT,'__enemy__',.1)['dot_dmg_pct'],0)
        bm.notify('full_charge',.2,NAME)
        self.assertAlmostEqual(bm.get_buffs(RIGHT,'__enemy__',.2)['dot_dmg_pct'],19.97)
        self.assertEqual(bm.get_buffs(RIGHT,'__enemy__',.2)['received_dmg'],0)
        bm.notify('full_burst_start',1,NAME)
        bm.notify('on_attack',1.1,NAME)
        self.assertEqual(bm.get_buffs(RIGHT,'__enemy__',1.1)['received_dmg'],0)
        bm.notify('full_charge_hit',1.2,NAME)
        self.assertAlmostEqual(bm.get_buffs(RIGHT,'__enemy__',1.2)['received_dmg'],10.56)
        bm.tick(11.01)
        bm.notify('full_charge_hit',11.1,NAME)
        bm.tick(11.21)
        self.assertEqual(bm.get_buffs(RIGHT,'__enemy__',11.21)['received_dmg'],0)

    def test_direct_hit_clears_only_ghost_dot_and_shared_damage_preserve(self):
        bm=fixture()
        bm.notify('full_burst_start',1,NAME)
        runtime=SimpleNamespace(bm=bm,time=2)
        unit_combat.hurt(runtime,NAME,10,direct=False)
        self.assertTrue(bm._has_self_state(NAME,GHOST))
        share={'source':'test','name':'shared','type':'buff','stat':'damage_share',
               'target':'all_allies','duration':10,'max_stack':1,
               'trigger':{'timing':[],'condition':[]}}
        bm._activate(share,LEFT,2)
        roster_mechanics.hurt_hp(bm,LEFT,90,2)
        self.assertTrue(bm._has_self_state(NAME,GHOST))
        unit_combat.hurt(runtime,NAME,10)
        self.assertFalse(bm._has_self_state(NAME,GHOST))
        self.assertTrue(bm._has_self_state(NAME,'장난 준비'))
        bm.notify('full_charge_hit',2.1,NAME)
        self.assertEqual(bm.get_buffs(RIGHT,'__enemy__',2.1)['received_dmg'],0)

    def test_single_target_exclusion_including_all_hidden_and_expiry(self):
        bm=fixture()
        bm.notify('full_burst_start',1,NAME)
        runtime=SimpleNamespace(bm=bm,time=2)
        runtime.protection=lambda n,stat:any(roster_mechanics.active(bm,n,stat,runtime.time))
        self.assertEqual(unit_combat.targetable(runtime,[LEFT,NAME,RIGHT]),[LEFT,RIGHT])
        self.assertEqual(unit_combat.targetable(runtime,[NAME]),[])
        runtime.time=11
        self.assertEqual(unit_combat.targetable(runtime,[NAME]),[NAME])

    def test_actual_charged_firing_applies_enemy_debuff_after_first_hit(self):
        char=core.spec.build_char(NAME,build(),no_layer=True)
        original=BuffManager.battle_start
        def start(manager,*args,**kw):
            original(manager,*args,**kw)
            manager.notify('full_burst_start',0,NAME)
        with patch.object(BuffManager,'battle_start',start):
            result=core.simulate([char],{'duration':5,'rng_mode':'expected'},
                                 {'def':0,'core_px':0,'is_element_match':False},seed=42,verbose=True)
        shots=[h for h in result.hits if h.caster==NAME and h.skill_name=='기본 공격']
        self.assertGreaterEqual(len(shots),3)
        self.assertAlmostEqual(shots[1].damage/shots[0].damage,1.1056,delta=.0001)
        windows=[e for e in result.log.buff_events if e.caster==NAME and e.name=='유령의 장난' and e.kind=='activate']
        self.assertTrue(windows)
        self.assertEqual(windows[0].t,shots[0].t)

    def test_two_cycles_own_burst_and_off_burst_passive(self):
        names=['리틀 머메이드',NAME,'크라운','test_B3','스노우 화이트 : 헤비암즈']
        result=core.simulate([core.spec.build_char(n,build(),no_layer=True) for n in names],
                             {'duration':45,'rng_mode':'expected'},seed=42,verbose=True)
        casts=[e for e in result.log.burst_log if e.caster==NAME and '사용' in e.event]
        full=[e for e in result.log.burst_log if e.event=='full_burst 시작']
        ghosts=[e for e in result.log.buff_events if e.caster==NAME and e.name==GHOST and e.kind=='activate']
        own=[e for e in result.log.buff_events if e.caster==NAME and e.name=='해피 할로윈! 지속 대미지' and e.kind=='activate']
        self.assertGreater(len(full),len(casts))
        self.assertEqual(len(ghosts),len(full))
        self.assertEqual(len(own),len(casts))

    def test_actual_dot_damage_increases_only_for_right_ally_after_charge(self):
        viper='바이퍼'
        original=BuffManager.battle_start
        def start(manager,*args,**kw):
            original(manager,*args,**kw)
            manager.notify('burst_cast',0,viper)
        results=[]
        for names in ([NAME,viper],[viper,NAME]):
            chars=[]
            for n in names:
                investment=build()
                if n==viper: investment['favorite_stage']=2
                chars.append(core.spec.build_char(n,investment,no_layer=True))
            with patch.object(BuffManager,'battle_start',start):
                result=core.simulate(chars,{'duration':5,'rng_mode':'expected'},
                                     {'def':0,'core_px':0,'is_element_match':False},seed=42,verbose=True)
            results.append([h for h in result.hits if h.caster==viper and h.skill_name=='스네이크 바이트 [3]'])
        buffed,baseline=results
        self.assertEqual(len(buffed),len(baseline))
        self.assertEqual(buffed[0].damage,baseline[0].damage)
        for boosted,plain in zip(buffed[1:],baseline[1:]):
            self.assertAlmostEqual(boosted.damage/plain.damage,1.1997,delta=.00002)


if __name__=='__main__':
    unittest.main()
