import copy
import unittest
from types import SimpleNamespace
import core
from raid_boss_combat import RaidBossRuntime, PROFILES, DATA
from boss_behavior import RUNNING, SUCCESS, FAILURE
from boss_parts import part_break_damage
from calculator.buff_manager import BuffManager

def hit(r,damage=1e9,element='전격',caster='unit',**kind):
    return r.resolve(caster,element,'AR',kind,lambda **kw:dict(damage=damage,is_crit=False,crit_frac=0),dict(enemy_def=0,hit_type=kind))['damage']

def bind(r):
    names=[core.NAME_MAP[n] for n in ('liter','scarlet')]
    chars=[core.spec.build_char(n,core.default_build(),no_layer=True) for n in names]
    bm=BuffManager(chars,{'hp':dict.fromkeys(names,1e9),'hp_pct':dict.fromkeys(names,100.),'base_stats':{n:{'hp':1e9,'atk':100*(i+1),'def':0} for i,n in enumerate(names)}})
    bm.battle_start(0)
    r.bind(bm,chars,{n:SimpleNamespace(base_atk=100*(i+1),weapon_type='AR',fire_rate=12,charge_time_base=1,reloading_until=0) for i,n in enumerate(names)})
    return bm,names

class RaidBossTests(unittest.TestCase):
    def test_part_overkill_is_not_lost_from_body_or_character_damage(self):
        runtime=RaidBossRuntime([],180,key='museum-modernia')
        part=runtime.select_part('unit')
        before=runtime.world.parts.parts[part]['hp']
        direct=before+1234567
        bonus=part_break_damage(runtime.stat(),runtime.data['monster'],runtime.world.rows[part],runtime.world.main_part)
        self.assertEqual(hit(runtime,direct,is_normal_atk=True),direct)
        self.assertEqual(runtime.world.parts.parts[part]['hp'],0)
        self.assertEqual(runtime.damage_to_parts,before)
        self.assertEqual(runtime.damage,direct+bonus)
        self.assertEqual(runtime.part_break_damage,bonus)
        report=runtime.report()
        self.assertEqual(report['boss_hp_damage'],direct+bonus)
        self.assertEqual(report['part_break_damage'],bonus)
        self.assertEqual(report['part_break_events'],[dict(time=0.,part=part,damage=bonus)])

    def test_part_bonus_occurs_once_per_player_destroyed_lifetime(self):
        runtime=RaidBossRuntime([],180,key='museum-modernia')
        part=runtime.select_part('unit')
        runtime.select_part=lambda caster:part
        damage=runtime.world.parts.parts[part]['hp']*2
        hit(runtime,damage,is_normal_atk=True)
        first=runtime.part_break_damage
        self.assertGreater(first,0)
        hit(runtime,damage,is_normal_atk=True)
        self.assertEqual(runtime.part_break_damage,first)
        self.assertEqual(len(runtime.part_break_events),1)
        node={'Type':'RepairPartsVer2','List`1_partsList':[part]}
        runtime.time=2
        self.assertEqual(runtime.world.action(node,2,{'started':2}),SUCCESS)
        hit(runtime,damage,is_normal_atk=True)
        self.assertEqual(runtime.part_break_damage,first*2)
        self.assertEqual(len(runtime.part_break_events),2)

    def test_self_destroyed_part_does_not_award_break_bonus(self):
        runtime=RaidBossRuntime([],180,key='museum-modernia')
        part=runtime.select_part('unit')
        runtime.world.action({'Type':'BrokenParts','List`1_partsList':[part]},0,{'started':0})
        runtime.select_part=lambda caster:part
        hit(runtime,1e9,is_normal_atk=True)
        self.assertEqual(runtime.part_break_damage,0)
        self.assertEqual(runtime.part_break_events,[])

    def test_break_uses_stat_before_hit_crosses_damage_stage(self):
        runtime=RaidBossRuntime([],180,key='museum-modernia')
        initial=runtime.stat();part=runtime.select_part('unit')
        expected=part_break_damage(initial,runtime.data['monster'],runtime.world.rows[part],runtime.world.main_part)
        runtime.stat=lambda monster=None:dict(initial,LevelBrokenHp=initial['LevelBrokenHp']*(2 if runtime.damage else 1))
        hit(runtime,1e9,is_normal_atk=True)
        self.assertEqual(runtime.part_break_damage,expected)

    def test_finite_part_hp_uses_broken_hp_in_every_content_mode(self):
        from decimal import Decimal, ROUND_HALF_UP
        for key,profile in PROFILES.items():
            for mode in profile['modes']:
                with self.subTest(key=key,mode=mode):
                    runtime=RaidBossRuntime([],180,key=key,mode=mode)
                    for ident,part in runtime.world.rows.items():
                        if part.get('IsMainPart') or not part['HpRatio']:continue
                        # Independent arithmetic: the native part constructor has
                        # no raid-versus-Anomaly branch for finite part HP.
                        raw=Decimal(runtime.stat()['LevelBrokenHp'])*Decimal(runtime.data['monster']['HpRatio'])*Decimal(part['HpRatio'])/Decimal(100000000)
                        expected=int(raw.quantize(Decimal('0.00001')).quantize(Decimal(1),rounding=ROUND_HALF_UP))
                        self.assertEqual(runtime.world.part_hp[ident],expected)

    def test_incoming_budget_is_split_and_defence_precedes_ratios(self):
        from enemy_damage import incoming_hit
        # Recovered routine subtracts DEF, then applies both /10000 ratios,
        # and CalculateDamage divides by ShotCount.
        self.assertEqual(incoming_hit(1000,200,20000,30000,4),1200)
        self.assertEqual(incoming_hit(1000,200,20000,30000),4800)
        self.assertEqual(incoming_hit(1000,2000,20000,30000),1)

    def test_sequence_does_not_repeat_entire_damage_budget(self):
        r=RaidBossRuntime([],180,key='anomaly-ultra',auto_cover=False)
        bm,names=bind(r)
        skill=dict(r.skills[1],Id=-1,ShotTiming='Sequence',ShotCount=4,SkillValue01=20000,FireType='Direct',SkillValueType01='Percent')
        r.stat=lambda monster=None:dict(LevelAttack=1000,LevelStatdamageratio=10000)
        r.data['monster']=dict(r.data['monster'],AttackRatio=10000)
        before=bm.state['hp'][names[0]]
        r.perform_skill(skill,{'_locked_targets':[names[0]]})
        for shot in r.pending_shots:r.receive_attack(shot['skill'],shot['node'])
        self.assertEqual(before-bm.state['hp'][names[0]],2000)

    def test_all_profiles_execute_success_and_failure_routes(self):
        for key,p in PROFILES.items():
            for mode in p['modes']:
                for outcome in ('passed','failed'):
                    with self.subTest(key=key,mode=mode,outcome=outcome):
                        r=RaidBossRuntime([],180,key=key,mode=mode)
                        for i in range(3601):
                            r.advance(i/20,{})
                            for q in r.states.values():
                                if q['status']=='active':q['status']=outcome
                            if r.stopped:break
                        self.assertGreater(len(r.events),5)
                        self.assertTrue(r.time>=180 or r.stop_reason)
                        self.assertFalse(r.report()['full_fight_verified'])

    def test_mode_records_and_latest_raid_are_not_borrowed_variants(self):
        self.assertEqual(PROFILES['sr40']['monster']['Id'],1520210138)
        for key,p in PROFILES.items():
            if not key.startswith('museum-'):continue
            a=RaidBossRuntime([],180,key=key,mode='challenge');b=RaidBossRuntime([],180,key=key,mode='no-limit')
            self.assertNotEqual(a.data['monster']['StatenhanceId'],b.data['monster']['StatenhanceId'])
            self.assertNotEqual(a.stat()['Id'],b.stat()['Id'])

    def test_part_break_cancels_charged_crystal_attack(self):
        r=RaidBossRuntime([],180,key='museum-crystal-chamber')
        node=dict(ID=999,Type='AttackV3',SkillAniNumberTypemSkillAniNumber='Shot_03',BooleanFailueCheck=True)
        state={'started':0}
        self.assertEqual(r.world.action(node,0,state),RUNNING)
        part=state['parts'][0]
        r.world.parts.damage(part,1e20,.5)
        self.assertEqual(r.world.action(node,.5,state),FAILURE)
        self.assertFalse(any(e['event']=='boss skill activated' for e in r.events))

    def test_skill_damage_does_not_destroy_tail(self):
        r=RaidBossRuntime([],180,key='anomaly-indivilia')
        hp=r.world.parts.parts['Weapon_03']['hp']
        hit(r,is_normal_atk=False)
        self.assertEqual(r.world.parts.parts['Weapon_03']['hp'],hp)
        hit(r,is_normal_atk=True)
        self.assertFalse(r.world.parts.alive('Weapon_03'))

    def test_modernia_safe_strategy_preserves_one_wing(self):
        r=RaidBossRuntime([],180,key='museum-modernia')
        r.world.parts.damage('Weapon_03',1e20,0);r.world.parts.damage('Weapon_01',1e20,0)
        self.assertIsNone(r.select_part('unit'))
        r.part_policy='all';self.assertEqual(r.select_part('unit'),'Weapon_02')

    def test_sphere_requires_hits_and_is_not_boss_damage(self):
        r=RaidBossRuntime([],180,key='museum-crystal-chamber')
        r.perform_skill(r.skills[6],{})
        self.assertEqual(hit(r,is_normal_atk=True),0)
        self.assertEqual(r.projectiles[0]['hp'],299)
        for _ in range(299):hit(r,is_normal_atk=True)
        self.assertEqual(r.projectiles[0]['status'],'passed');self.assertEqual(r.damage,0)

    def test_explicit_choice_changes_branch(self):
        node=dict(ID=999,SingledurationTime=5)
        for policy,expected in [('projectile',0),('debuff',1)]:
            r=RaidBossRuntime([],180,key='museum-crystal-chamber',choice_policy=policy);state={}
            self.assertIsNone(r.world.choose(node,0,state))
            self.assertEqual(r.world.choose(node,.2,state),expected)
            self.assertEqual(r.choices[0]['route'],policy)

    def test_poison_cover_starts_before_impact_and_blocks_dot(self):
        r=RaidBossRuntime([],180,key='anomaly-ultra');bm,names=bind(r)
        skill=r.skills[2]
        r.cover_threats.append(dict(start=1.75,end=2.5,skill=skill,targets=names,parts=[]))
        r.time=1.8;r.update_cover(1.8)
        self.assertEqual(r.covered,set(names));self.assertEqual(len(r.cover_windows),2)
        before=dict(r.cover);r.receive_attack(skill,{'_locked_targets':names})
        self.assertTrue(all(x['blocked_by']=='cover' for x in r.incoming))
        self.assertFalse(r.dot_ticks)
        self.assertTrue(any(r.cover[n]<before[n] for n in names))

    def test_poison_without_cover_applies_dot_and_cleanse_removes_it(self):
        r=RaidBossRuntime([],180,key='anomaly-ultra',auto_cover=False);bm,names=bind(r)
        r.cover=dict.fromkeys(names,0);r.receive_attack(r.skills[2],{'_locked_targets':names})
        self.assertTrue(r.dot_ticks)
        before=bm.state['hp'][names[0]];r.time=1;r.advance_dots(1)
        self.assertLess(bm.state['hp'][names[0]],before)
        # The engine's cleanse removes harmful buffs, including the DoT marker.
        bm._active=[a for a in bm._active if a.effect.get('polarity')!='harmful'];before=bm.state['hp'][names[0]]
        r.time=2;r.advance_dots(2);self.assertEqual(bm.state['hp'][names[0]],before)

    def test_highest_current_attack_selects_only_that_unit_for_cover(self):
        r=RaidBossRuntime([],180,key='anomaly-ultra');bm,names=bind(r)
        skill=dict(r.skills[5],PreferTarget='HighAttack',SkillValue01=1e10)
        selected=r.attack_targets(skill,{})
        self.assertEqual(selected,[names[1]])
        r.cover_threats.append(dict(start=0,end=2,skill=skill,targets=selected,parts=[]));r.update_cover(1)
        self.assertEqual(r.covered,{names[1]})

    def test_crystal_attack_debuff_is_real_and_cleansable(self):
        r=RaidBossRuntime([],180,key='museum-crystal-chamber');bm,names=bind(r)
        before=bm._effective_atk(names[0]);r.apply_skill_functions(r.skills[7],'UseFunctionIdSkill')
        self.assertAlmostEqual(bm._effective_atk(names[0]),before*.7)
        self.assertTrue(any(a.effect.get('polarity')=='harmful' for a in bm._active))

    def test_manual_and_search_settings_install_automatic_runtime(self):
        for key in PROFILES:
            s=core.validate_settings(dict(boss_id=key,content_mode='museum' if key.startswith('museum-') else 'anomaly' if key.startswith('anomaly-') else 'solo'))
            self.assertIsInstance(core.encounters.config(s,30)['encounter_runtime'],RaidBossRuntime)
            self.assertEqual(s['boss_simulation'],'automatic')

if __name__=='__main__':unittest.main()
