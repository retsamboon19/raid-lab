import unittest
from types import SimpleNamespace
import core
from mother_whale_combat import MotherWhaleRuntime, DATA, SKILLS, CORE

def hit(runtime,damage=10,element='전격',**kind):
    return runtime.resolve('unit',element,'AR',kind,
        lambda **kw:dict(damage=damage,is_crit=False,crit_frac=0),dict(enemy_def=0,hit_type=kind))['damage']

class MotherWhaleTests(unittest.TestCase):
    def test_part_break_preserves_full_direct_hit_in_character_and_body_damage(self):
        runtime=MotherWhaleRuntime([],30)
        before=runtime.world.parts.parts[CORE]['hp']
        direct=before+1234567
        self.assertEqual(hit(runtime,direct,is_normal_atk=True),direct)
        self.assertEqual(runtime.world.parts.parts[CORE]['hp'],0)
        self.assertEqual(runtime.damage_to_parts,before)
        self.assertEqual(runtime.damage,direct+38_405_524)
        self.assertEqual(runtime.report()['part_break_damage'],38_405_524)

    def test_part_bonus_once_per_lifetime_and_not_self_destruction(self):
        r=MotherWhaleRuntime([],30)
        r.select_target=lambda caster:('part',CORE)
        hit(r,80_000_000,is_normal_atk=True)
        hit(r,80_000_000,is_normal_atk=True)
        self.assertEqual(r.part_break_damage,38_405_524)
        r.world.parts.spawn(CORE,r.world.part_hp[CORE],1)
        hit(r,80_000_000,is_normal_atk=True)
        self.assertEqual(r.part_break_damage,2*38_405_524)
        r.world.parts.spawn(CORE,r.world.part_hp[CORE],2)
        r.world.parts.self_destruct(CORE,2)
        hit(r,80_000_000,is_normal_atk=True)
        self.assertEqual(r.part_break_damage,2*38_405_524)

    def test_summon_raw_statistics_include_overkill_but_hp_damage_is_capped(self):
        r=MotherWhaleRuntime([],30,target_policy='body')
        r.spawn_add(DATA['calls'][0]);hp=r.adds[0]['hp']
        hit(r,hp+1_000_000,effect_target='all_enemies')
        report=r.report()
        self.assertEqual(report['damage_to_adds'],round(hp))
        self.assertEqual(report['add_damage_by_unit']['unit'],round(hp+1_000_000))
        self.assertEqual(r.adds[0]['hp'],0)
        hit(r,1_000_000,effect_target='all_enemies')
        self.assertEqual(r.report()['add_damage_by_unit'],report['add_damage_by_unit'])

    def test_death_does_not_extend_full_burst_to_requested_duration(self):
        import burst_rotation
        events=[SimpleNamespace(t=10,event='full_burst 시작',caster='unit')]
        rotation=burst_rotation.report([],{},events,180,observed_until=14)
        self.assertEqual(rotation['full_burst_seconds'],4)
        self.assertEqual(rotation['full_bursts'][0]['end'],14)
        self.assertFalse(rotation['full_bursts'][0]['complete'])
        self.assertEqual(rotation['uptime_pct'],2.2)

    def test_both_recovered_trees_execute_full_duration(self):
        for mode in ('challenge','no-limit'):
            r=MotherWhaleRuntime([],180,mode=mode)
            for i in range(10801):r.advance(i/60)
            self.assertGreater(len(r.waves),3)
            self.assertGreater(len(r.adds),50)
            self.assertEqual(r.report()['critical_parts'][0]['status'],'failed')
            self.assertFalse(r.report()['qte_required'])
            self.assertTrue(any(a.get('clear_reason')=='scripted withdrawal' for a in r.adds))

    def test_core_break_changes_source_branches(self):
        r=MotherWhaleRuntime([],60)
        self.assertEqual(r.world.part_hp[CORE],76811055)
        hit(r,2e9,is_normal_atk=True)
        for i in range(3601):r.advance(i/60)
        self.assertEqual(r.core_broken_at,0)
        self.assertFalse(r.waves)
        self.assertFalse(any(a['protected'] for a in r.adds))
        self.assertEqual(r.report()['critical_parts'][0]['status'],'passed')
        self.assertFalse(r.report()['full_fight_verified'])

    def test_part_hp_uses_selected_mode_broken_hp_while_body_uses_main_hp(self):
        import math
        from mother_whale_combat import STATS,part_name
        for mode in ('challenge','no-limit'):
            with self.subTest(mode=mode):
                r=MotherWhaleRuntime([],60,mode=mode)
                monster=DATA['mode_monsters'][mode]
                stat=STATS[(monster['StatenhanceId'],DATA['modes'][mode]['MonsterStageLv'])]
                for part in DATA['parts']:
                    base=stat['LevelHp' if part['IsMainPart'] else 'LevelBrokenHp']
                    expected=math.floor(round(base*monster['HpRatio']/10000*part['HpRatio']/10000,5)+.5)
                    self.assertEqual(r.world.part_hp[part_name(part['PartsType'])],expected)
                # Swapping in whole-boss HP makes the core over fifteen times
                # too durable in Challenge; this bound protects the actual mechanic.
                if mode=='challenge':self.assertLess(r.world.part_hp[CORE],stat['LevelHp']*.02)

    def test_native_part_hp_ratio_and_linked_body_semantics(self):
        from boss_parts import part_max_hp
        stat=dict(LevelHp=10_000,LevelBrokenHp=1_003)
        monster=dict(HpRatio=15_000)
        main=dict(IsMainPart=True,HpRatio=12_000)
        self.assertEqual(part_max_hp(stat,monster,main),18_000)
        self.assertEqual(part_max_hp(stat,monster,dict(IsMainPart=False,HpRatio=2_000)),301)
        self.assertEqual(part_max_hp(stat,monster,dict(IsMainPart=False,HpRatio=0),main),18_000)
        self.assertEqual(part_max_hp(stat,monster,dict(IsMainPart=False,HpRatio=0)),15_000)

    def test_each_mode_executes_its_own_skill_slots_and_summons(self):
        results={}
        for mode in ('challenge','no-limit'):
            r=MotherWhaleRuntime([],30,mode=mode)
            for i in range(1801):r.advance(i/60)
            started=next(e for e in r.events if e['event']=='boss attack started' and e['shot']==8)
            source=DATA['mode_monsters'][mode]['SkillData'][7]['SkillId']
            self.assertEqual(started['skill_id'],source)
            group=SKILLS[source]['SkillValue01']
            expected={c['MonsterId'] for c in DATA['calls'] if c['GroupId']==group}
            self.assertTrue(expected)
            self.assertIn(r.adds[0]['monster_id'],expected)
            results[mode]=(source,group,r.adds[0]['monster_id'])
        self.assertEqual(results['challenge'][:2],(530908,110))
        self.assertEqual(results['no-limit'][:2],(530947,262))
        self.assertNotEqual(results['challenge'][2],results['no-limit'][2])

    def test_extracted_summon_graph_contains_each_modes_referenced_records(self):
        from mother_whale_combat import MONSTERS,STATS
        for monster in DATA['monsters']:
            for slot in monster['SkillData']:
                if not slot['SkillId']:continue
                skill=SKILLS[slot['SkillId']]
                if skill['FireType']!='Calling':continue
                calls=[c for c in DATA['calls'] if c['GroupId']==skill['SkillValue01']]
                self.assertTrue(calls,msg=f"Missing summon group for skill {skill['Id']}")
                for call in calls:
                    add=MONSTERS[call['MonsterId']]
                    self.assertIn(add['SpotAi'],DATA['add_trees'])
                    for stage in DATA['stages']:
                        self.assertIn((add['StatenhanceId'],stage['MonsterStageLv']),STATS)

    def test_source_sized_core_can_break_before_wave_without_boss_sized_damage(self):
        r=MotherWhaleRuntime([],30)
        hit(r,80_000_000,is_normal_atk=True)
        self.assertEqual(r.core_broken_at,0)
        self.assertEqual(r.damage_to_parts,76_811_055)
        for i in range(1801):r.advance(i/60)
        self.assertEqual(r.report()['critical_parts'][0]['status'],'passed')
        self.assertFalse(any(a['protected'] for a in r.adds))

    def test_normal_hits_remove_one_hp_after_wave(self):
        r=MotherWhaleRuntime([],60,target_policy='adds')
        r.spawn_add(DATA['calls'][0]);add=r.adds[0]
        r.perform_skill(2,SKILLS[530902])
        self.assertEqual(add['hp'],90)
        self.assertEqual(hit(r,1e9,is_normal_atk=True),0)
        self.assertEqual(add['hp'],89)
        for _ in range(89):hit(r,1e9,is_normal_atk=True)
        self.assertEqual(add['hp'],0)
        self.assertEqual(r.damage,0)
        self.assertEqual(r.damage_to_adds,90)
        self.assertFalse(r.barrier)

    def test_aoe_hits_every_add_and_split_damage_bypasses_protection(self):
        r=MotherWhaleRuntime([],60,target_policy='body')
        for row in DATA['calls'][:3]:r.spawn_add(row)
        r.perform_skill(2,SKILLS[530902])
        hit(r,3000,effect_target='all_enemies')
        self.assertEqual([a['hp'] for a in r.adds],[89]*3)
        hit(r,3000,effect_target='all_enemies',is_split=True)
        self.assertFalse(r.living_adds())
        self.assertEqual(r.damage_to_adds,270)

    def test_sufficient_aoe_preclears_summons_before_protection_cast(self):
        r=MotherWhaleRuntime([],60,target_policy='body')
        for row in DATA['calls'][:3]:r.spawn_add(row)
        self.assertTrue(r.barrier)
        hit(r,1e9,effect_target='all_enemies')
        self.assertFalse(r.living_adds())
        self.assertFalse(r.barrier)
        r.perform_skill(2,SKILLS[530902])
        evidence=r.report()['summon_control']
        self.assertEqual(evidence['protection_casts'],1)
        self.assertEqual(evidence['empty_protection_casts'],1)
        self.assertEqual(evidence['precleared_casts'],1)
        self.assertEqual(evidence['casts_with_survivors'],0)
        self.assertEqual(evidence['protected_adds'],0)
        self.assertFalse(evidence['core_disabled_protection'])

    def test_insufficient_aoe_leaves_actual_protected_survivors(self):
        r=MotherWhaleRuntime([],60,target_policy='body')
        for row in DATA['calls'][:3]:r.spawn_add(row)
        hit(r,10,effect_target='all_enemies')
        r.perform_skill(2,SKILLS[530902])
        r.time=1
        r.perform_skill(2,SKILLS[530902])
        evidence=r.report()['summon_control']
        self.assertEqual(evidence['protection_casts'],2)
        self.assertEqual(evidence['empty_protection_casts'],0)
        self.assertEqual(evidence['precleared_casts'],0)
        self.assertEqual(evidence['casts_with_survivors'],2)
        self.assertEqual(evidence['protected_adds'],3)  # Unique summons, not six applications.
        self.assertEqual(evidence['observed_until'],1)
        self.assertTrue(r.barrier)
        self.assertTrue(all(add['protected'] for add in r.adds))

    def test_core_disabled_protection_does_not_claim_aoe_preclear(self):
        r=MotherWhaleRuntime([],30)
        hit(r,80_000_000,is_normal_atk=True)
        for i in range(1801):r.advance(i/60)
        evidence=r.report()['summon_control']
        self.assertTrue(evidence['core_disabled_protection'])
        self.assertEqual(evidence['protection_casts'],0)
        self.assertEqual(evidence['empty_protection_casts'],0)
        self.assertEqual(evidence['precleared_casts'],0)
        self.assertEqual(evidence['protected_adds'],0)

    def test_cast_without_spawned_summons_is_empty_but_not_precleared(self):
        r=MotherWhaleRuntime([],30)
        r.perform_skill(2,SKILLS[530902])
        evidence=r.report()['summon_control']
        self.assertEqual(evidence['empty_protection_casts'],1)
        self.assertEqual(evidence['precleared_casts'],0)

    def test_barrier_blocks_body_without_blocking_adds(self):
        r=MotherWhaleRuntime([],60,target_policy='body')
        r.spawn_add(DATA['calls'][0])
        self.assertEqual(hit(r,123,element='작열'),0)
        self.assertEqual(hit(r,123,element='전격'),123)
        self.assertEqual(hit(r,1e15,element='작열',effect_target='all_enemies'),0)
        self.assertFalse(r.barrier)
        self.assertEqual(hit(r,123,element='작열'),123)

    def test_core_destroyed_during_cast_cancels_buff(self):
        r=MotherWhaleRuntime([],30)
        for i in range(721):r.advance(i/60)
        self.assertIsNotNone(r.first_wave_deadline)
        r.world.parts.damage(CORE,1e20,r.time);r.core_broken_at=r.time
        for i in range(721,1201):r.advance(i/60)
        self.assertFalse(any(a['protected'] for a in r.adds))

    def test_damage_and_death_use_live_hp_not_healer_tag(self):
        from calculator.buff_manager import BuffManager
        name=core.NAME_MAP['liter'];char=core.spec.build_char(name,core.default_build(),no_layer=True)
        state=dict(hp={name:1000.},hp_pct={name:100.},base_stats={name:dict(hp=1000.,atk=100.,**{'def':0.})})
        bm=BuffManager([char],state);bm.battle_start(0)
        r=MotherWhaleRuntime([],180,auto_cover=False);r.bind(bm,[char],{name:SimpleNamespace(base_atk=100)})
        r.stat=lambda monster=None:dict(LevelAttack=100.,LevelStatdamageratio=10000)
        bm._effective_def=lambda name:0.
        skill=dict(SKILLS[530904],SkillValue01=20000,ShotCount=1)
        r.receive_attack(skill,source='fixture');self.assertEqual(state['hp'][name],800)
        # Actual recovered HP is consumed; a healer's name grants no immunity.
        state['hp'][name]=1000
        for _ in range(5):r.receive_attack(skill,source='fixture')
        self.assertTrue(r.stopped);self.assertEqual(r.report()['survival'],'failed')

if __name__=='__main__':unittest.main()
