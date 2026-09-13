import copy
import unittest
from types import SimpleNamespace
import core
from calculator.timeline import _restore_hp
from boss_behavior import BehaviorTree, SUCCESS
from test_boss_behavior import World, node
from kraken_combat import KrakenRuntime, DATA, FRONT
from mechanics import EncounterRuntime


class KrakenTests(unittest.TestCase):
    def test_part_overkill_is_full_direct_damage_with_zero_native_bonus(self):
        runtime=KrakenRuntime([],180)
        part=runtime.select_part('unit');hp=runtime.world.parts.parts[part]['hp']
        direct=hp+1234567
        result=runtime.resolve('unit','Wind','AR',{'is_normal_atk':True},
            lambda **kw:dict(damage=direct),dict(enemy_def=0,hit_type={}))
        self.assertEqual(result['damage'],direct)
        self.assertEqual(runtime.damage,direct)
        self.assertEqual(runtime.damage_to_parts,hp)
        self.assertFalse(runtime.world.parts.alive(part))
        report=runtime.report()
        self.assertTrue(report['part_break_damage_supported'])
        self.assertEqual(report['part_break_damage'],0)
        self.assertEqual(report['part_break_events'],[])
        self.assertEqual(report['boss_hp_damage'],direct)

    def test_future_nonzero_kraken_bonus_is_explicitly_unsupported(self):
        from unittest.mock import patch
        parts=copy.deepcopy(DATA['parts']);parts[1]['DamageHpRatio']=1000
        with patch.dict(DATA,parts=parts):
            report=KrakenRuntime([],180).report()
        self.assertFalse(report['part_break_damage_supported'])
        self.assertTrue(any('monster HP scaling record is missing' in a for a in report['assumptions']))

    def test_collection_passives_affect_cover_and_incoming_hp_damage(self):
        from calculator.buff_manager import BuffManager
        name=core.NAME_MAP['liter']
        build=core.default_build();build['collection_stage']='SR15'
        char=core.spec.build_char(name,build,no_layer=True)
        bm=BuffManager([char],{'hp':{name:1000.},'hp_pct':{name:100.},'base_stats':{name:{'hp':1000.,'atk':100.,'def':0.}}})
        bm.battle_start(0.)
        runtime=KrakenRuntime([],180)
        runtime.bind(bm,[char],{name:SimpleNamespace(base_atk=100)})
        base=next(r['LevelHp'] for r in DATA['cover_stats'] if r['Lv']==char['level'])
        self.assertAlmostEqual(runtime.cover_max[name],base*1.3)
        self.assertEqual(runtime.active_stat(name,'received_dmg_pct'),-17)
        runtime.stat=lambda:{'LevelAttack':100.,'LevelStatdamageratio':10000.}
        runtime.receive_attack(1,{'SkillValue01':10000,'ShotCount':1})
        self.assertAlmostEqual(bm.state['hp'][name],917.)

    def test_disabled_branch_has_no_side_effect(self):
        world=World()
        tree=BehaviorTree(node(0,'Sequence',node(1,'Unknown',Disabled=True),node(2,'Pass')),world)
        self.assertEqual(tree.advance(0),SUCCESS)
        self.assertEqual(world.calls,[(2,0)])

    def test_transformed_weapon_damage_can_hit_interruptions(self):
        for weapon_skill,expected in [(True,'passed'),(False,'active')]:
            runtime=EncounterRuntime([dict(kind='qte',start=0,duration=3,targets=[dict(hp=10)])])
            runtime.advance(0)
            result=runtime.resolve('unit','Wind','AR',dict(is_weapon_mode_skill=weapon_skill),
                lambda **kw:dict(damage=100),dict(enemy_def=0,hit_type={}))
            self.assertEqual(runtime.report()['checks'][0]['status'],expected)
            if weapon_skill:self.assertEqual(result['damage'],0)

    def test_aiming_waits_before_firing_at_each_target(self):
        runtime=KrakenRuntime([],180,aim_seconds=.2)
        ident=runtime.add_event(dict(kind='qte',start=0,duration=3,targets=[dict(hp=1),dict(hp=1)]))
        EncounterRuntime.advance(runtime,0)
        self.assertTrue(runtime.hold_fire('unit','AR','Wind'))
        runtime.time=.19
        self.assertTrue(runtime.hold_fire('unit','AR','Wind'))
        runtime.time=.2
        self.assertFalse(runtime.hold_fire('unit','AR','Wind'))
        runtime.resolve('unit','Wind','AR',dict(is_normal_atk=True),lambda **kw:dict(damage=10),dict(enemy_def=0,hit_type={}))
        self.assertTrue(runtime.hold_fire('unit','AR','Wind'))
        self.assertEqual(runtime.states[ident]['index'],1)

    def test_finite_part_hp_changes_target(self):
        runtime=KrakenRuntime([],180,target_policy='safe')
        part=runtime.select_part('unit')
        self.assertIn(part,FRONT)
        self.assertEqual(runtime.core_probability('unit',0),1)
        dealt=runtime.world.parts.damage(part,1e20,0)
        self.assertEqual(dealt,111000000)
        self.assertIsNone(runtime.select_part('unit'))
        self.assertEqual(runtime.core_probability('unit',1),0)
        runtime.world.phase=2
        runtime.target_policy='body'
        self.assertEqual(runtime.core_probability('unit',0),1)

    def test_unverified_death_is_not_a_verified_clear_failure(self):
        entry=dict(encounter_timeline=dict(model='experimental',survival='failed',stop_reason='death'))
        core.attach_combat_assessment(entry)
        self.assertFalse(entry['mechanics']['clear_verified'])
        self.assertIn('not a verified',entry['warnings'][0])

    def test_passive_references_are_resolved(self):
        ids={row['Id'] for row in DATA['passives']}
        self.assertTrue({row['TargetPassiveSkillId'] for row in DATA['stages']}<=ids)
        function_ids={row['Id'] for row in DATA['functions']}
        self.assertTrue({item['Function'] for row in DATA['passives'] for item in row['Functions'] if item['Function']}<=function_ids)

    def test_qte_controller_uses_current_weapon_not_base_weapon(self):
        runtime=KrakenRuntime([],180)
        runtime.add_event(dict(kind='qte',start=0,duration=4,targets=[dict(hp=10,weapons=['AR','MG','SR'])]))
        EncounterRuntime.advance(runtime,0)
        runtime.squad={n:dict(element_code='Wind') for n in ('transformed','rapid','reloading')}
        runtime.char_states={n:SimpleNamespace(weapon_type='AR',fire_rate=12.,charge_time_base=1.,reloading_until=2 if n=='reloading' else -1) for n in runtime.squad}
        runtime.bm=SimpleNamespace(state={'hp':dict.fromkeys(runtime.squad,100)},get_weapon_change=lambda n:{'weapon_type':'RL'} if n=='transformed' else None)
        runtime.choose_qte_controller()
        self.assertEqual(runtime.active['controller'],'rapid')

    def test_elemental_damage_dealer_can_be_burst_one_or_two_support_class(self):
        catalog={n:dict(burst=stage,role='Supporter',barrier_elements=[element]) for n,stage,element in [('a','1','Water'),('b','2','Water'),('c','3','Fire'),('d','2','Iron'),('e','3','Wind')]}
        settings=dict(encounter=dict(barrier_element='Water'))
        for dealer in ('a','b'):
            entry=dict(members=list(catalog),damage=100,breakdown={n:40 if n==dealer else 15 for n in catalog})
            self.assertIn(dealer,core.elemental_damage_report(entry,settings,catalog)['providers'])
        entry=dict(members=list(catalog),damage=100,breakdown=dict(a=3,b=4,c=40,d=30,e=23))
        self.assertFalse(core.elemental_damage_report(entry,settings,catalog)['providers'])


class HealingTests(unittest.TestCase):
    def manager(self):
        buff=SimpleNamespace(effect={'stat':'heal_split'},target_chars=['a','b','c'],expires_at=5)
        return SimpleNamespace(_active=[buff],state={'hp':{'a':95.,'b':20.,'c':0.}},
            effective_max_hp=lambda n:100.,sync_hp=lambda n:None,notify=lambda *args:None)

    def test_heal_sharing_caps_each_living_recipient_once(self):
        bm=self.manager();log=SimpleNamespace(heal_events=[])
        _restore_hp(bm,'a',40,1,'healer',log)
        self.assertEqual(bm.state['hp'],{'a':100.,'b':40.,'c':0.})
        self.assertEqual(sum(e['requested'] for e in log.heal_events),40)
        self.assertEqual(sum(e['effective'] for e in log.heal_events),25)

    def test_expired_heal_sharing_does_not_redistribute(self):
        bm=self.manager()
        _restore_hp(bm,'a',40,5,'healer')
        self.assertEqual(bm.state['hp'],{'a':100.,'b':20.,'c':0.})

    def test_shared_recovery_restores_hp_without_recovery_triggers(self):
        from unittest.mock import Mock
        bm=self.manager();bm.notify=Mock();log=SimpleNamespace(heal_events=[])
        _restore_hp(bm,'a',40,1,'healer',log)
        bm.notify.assert_not_called()
        self.assertTrue(all(not e['triggers_heal_received'] for e in log.heal_events))
        self.assertEqual(bm.state['hp']['b'],40)

    def test_direct_recovery_still_triggers_even_at_full_hp(self):
        from unittest.mock import Mock
        bm=self.manager();bm._active=[];bm.state['hp']['a']=100;bm.notify=Mock()
        _restore_hp(bm,'a',40,1,'healer')
        bm.notify.assert_called_once_with('event:heal_received',1,'a')


if __name__=='__main__':unittest.main()
