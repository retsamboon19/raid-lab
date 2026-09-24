"""Behavioral regressions for the real Anomaly records and common dispatch."""
import unittest
from unittest.mock import patch
import core
from raid_boss_combat import RaidBossRuntime
from test_raid_boss_combat import bind


class AnomalyRuntimeTests(unittest.TestCase):
    def test_selected_split_divides_before_integer_rounding_and_keeps_minimum_damage(self):
        from calculator.damage import calc_damage, default_hit_type
        r=RaidBossRuntime([],180,key='anomaly-ultra')
        r.adds=[dict(id=name,hp=100,max_hp=100,spawned=0,defence=0,protected=False)
                for name in ('a','b')]
        kind=default_hit_type(is_normal_atk=False,is_split=True,coeff=2.51)
        args=dict(base_atk=100,buffs={'crit_rate':0},
                  weapon={'damage_coeff':100,'weapon_type':'AR','core_dmg_mult':200},
                  hit_type=kind,enemy_def=0,expected=True)
        with patch.object(r,'anomaly_hook',return_value=None):
            result=r.resolve_selected_skill(['a','b'],'unit','작열','AR',kind,calc_damage,args)
        # 2.51 / 2 rounds to 1. Dividing an already-rounded 3 would give 2.
        self.assertEqual([add['hp'] for add in r.adds],[99,99])
        self.assertEqual(result['collision_hits'],2)
        self.assertEqual(result['damage'],0)
        self.assertEqual(kind['coeff'],2.51)

    def test_precision_controller_uses_native_replacement_weapon_class(self):
        from types import SimpleNamespace
        from mechanics import EncounterRuntime
        caster='나유타'
        r=RaidBossRuntime([],180,key='anomaly-ultra');r.aim_seconds=0
        r.bm=SimpleNamespace(get_weapon_change=lambda name: {'weapon_type':'RL','charge_time':.5},
                             state={'hp':{caster:100}})
        r.squad={caster:{'element_code':'풍압'}}
        r.char_states={caster:SimpleNamespace(weapon_type='RL',charge_time_base=1,fire_rate=1,reloading_until=0)}
        r.add_event(dict(kind='qte',start=0,duration=10,controller='auto',precision_hazards=True,
            graph=[dict(id=1,kind='break',target_kind='special_qte',hp=10000,duration=10,first=True),
                   dict(id=2,kind='counter',target_kind='special_qte',hp=10000,duration=10,first=True)]))
        EncounterRuntime.advance(r,0)
        r.choose_qte_controller()
        self.assertEqual(r.active['controller'],caster)
        self.assertEqual(r.qte_weapon_type(caster,'RL'),'SR')
        self.assertIsNotNone(r.target(caster,'RL','풍압'))

    def test_unsupported_qte_geometry_remains_visible_in_report_counters(self):
        r=RaidBossRuntime([],180,key='anomaly-ultra')
        with patch('anomaly_qte_shots.qte_shot_contacts',return_value=None):
            self.assertIsNone(r.resolve_physical_qte('unit','전격','AR',{},None,{},{}))
        self.assertEqual(r.qte_physics['shots'],0)
        self.assertEqual(r.qte_physics['unresolved_shots'],1)
        self.assertEqual(r.qte_physics['unresolved_units'],['unit'])

    def test_physical_qte_contacts_damage_actual_targets_and_grey_fails(self):
        from mechanics import EncounterRuntime
        r=RaidBossRuntime([],180,key='anomaly-ultra');r.aim_seconds=0
        ident=r.add_event(dict(kind='qte',start=0,duration=10,controller='unit',on_fail='downtime',
            graph=[dict(id=1,kind='break',target_kind='special_qte',hp=10000,duration=10,first=True,
                        local_position=(0,0,0),box_size=(1.7,)*3,**{'def':100}),
                   dict(id=2,kind='counter',target_kind='special_qte',hp=10000,duration=10,first=True,
                        local_position=(2,0,0),box_size=(1.7,)*3,**{'def':200})]))
        EncounterRuntime.advance(r,0)
        seen=[]
        def calculate(**kw):
            seen.append(kw)
            return dict(damage=1000-kw['enemy_def'],is_crit=False,crit_frac=0)
        kind=dict(is_normal_atk=True)
        shot=dict(contacts=[1,2],calibration='observed ray')
        with patch('anomaly_qte_shots.qte_shot_contacts',return_value=shot):
            result=r.resolve('unit','전격','RL',kind,calculate,
                dict(enemy_def=999,hit_type=kind,buffs={'received_dmg':100,'qte_dmg_pct':20}))
        self.assertEqual(result['damage'],0)
        self.assertEqual(result['collision_hits'],2)
        self.assertEqual([x['enemy_def'] for x in seen],[100,200])
        self.assertTrue(all(x['buffs']['received_dmg']==0 for x in seen))
        self.assertEqual(r.states[ident]['graph'].targets[1]['remaining'],8920)
        self.assertEqual(r.states[ident]['graph'].status,'failed')
        EncounterRuntime.advance(r,.1)
        self.assertEqual(r.states[ident]['status'],'failed')
        self.assertEqual(r.damage,0)

    def test_physical_qte_miss_does_not_become_a_body_hit(self):
        from mechanics import EncounterRuntime
        r=RaidBossRuntime([],180,key='anomaly-ultra');r.aim_seconds=0
        record=r.data['qtes'][0]
        r.special_qte({'Int32_quickTimeId':record['Id']},0,{})
        EncounterRuntime.advance(r,0)
        EncounterRuntime.advance(r,1)
        kind=dict(is_normal_atk=True)
        with patch('anomaly_qte_shots.qte_shot_contacts',return_value=dict(contacts=[],calibration='observed ray')):
            result=r.resolve('unit','전격','AR',kind,lambda **kw:dict(damage=1000,is_crit=False,crit_frac=0),
                             dict(enemy_def=0,hit_type=kind))
        self.assertEqual(result['damage'],0)
        self.assertEqual(result['collision_hits'],0)
        self.assertEqual(r.damage,0)
        self.assertEqual(r.qte_physics['misses'],1)

    def test_observed_rocket_ray_can_hit_grey_despite_safe_controller_policy(self):
        from mechanics import EncounterRuntime
        r=RaidBossRuntime([],180,key='anomaly-ultra');r.aim_seconds=0
        caster=core.NAME_MAP['rapunzel']
        ident=r.add_event(dict(kind='qte',start=0,duration=10,controller='auto',on_fail='downtime',
            precision_hazards=True,full_burst_follow=False,
            graph=[dict(id=1,kind='break',target_kind='special_qte',hp=10000,duration=10,first=True,
                        local_position=(0,0,0),box_size=(1.7,)*3,weapons=['AR']),
                   dict(id=2,kind='counter',target_kind='special_qte',hp=10000,duration=10,first=True,
                        local_position=(3,0,0),box_size=(1.7,)*3)]))
        EncounterRuntime.advance(r,0)
        self.assertIsNone(r.target(caster,'RL','철갑'))
        kind=dict(is_normal_atk=True,qte_ray={'origin':(3,0,0),'direction':(0,0,1)})
        result=r.resolve(caster,'철갑','RL',kind,lambda **kw:dict(damage=1000,is_crit=False,crit_frac=0),
                         dict(enemy_def=0,hit_type=kind))
        self.assertEqual(r.states[ident]['graph'].status,'failed')
        self.assertGreaterEqual(result['collision_hits'],1)
        self.assertEqual(r.qte_physics['counter_contacts'],1)
        self.assertEqual(result['damage'],0)

    def test_nearest_target_works_with_bound_ultra_and_harvester_squads(self):
        for key in ('anomaly-ultra','anomaly-harvester'):
            with self.subTest(key=key):
                r=RaidBossRuntime([],180,key=key)
                _,names=bind(r)
                r.adds.extend([
                    dict(id='far',hp=100,max_hp=100,spawned=0,position=(0,0,100)),
                    dict(id='near',hp=100,max_hp=100,spawned=0,position=(-5,0,10)),
                ])
                self.assertEqual(r.select_enemy_effect_targets(
                    {'target':'enemies_nearest:1'},names[0],0),['near'])
                r.adds[1]['hp']=0
                self.assertEqual(r.select_enemy_effect_targets(
                    {'target':'enemies_nearest:1'},names[0],0),['__boss__'])

    def test_special_qte_boxes_use_native_sizes_positions_and_active_lifetimes(self):
        from mechanics import EncounterRuntime
        for family in ('ultra','harvester','indivilia','mirror-container'):
            with self.subTest(family=family):
                r=RaidBossRuntime([],180,key='anomaly-'+family)
                record=r.data['qtes'][0]
                r.special_qte({'Int32_quickTimeId':record['Id']},0,{})
                EncounterRuntime.advance(r,0)
                self.assertEqual(r.active_qte_geometry(),())
                EncounterRuntime.advance(r,1)
                boxes=r.active_qte_geometry()
                self.assertTrue(boxes)
                source={q['ColIndex']:q for q in r.data['qte_targets'] if q['GroupId']==record['GroupId'][0]}
                for box in boxes:
                    local=source[box.collider_index]['ColPosition']
                    self.assertEqual(box.center,(local[0],local[1],local[2]+16))
                    self.assertEqual(box.half_extents,(1.25,)*3 if family=='harvester' and box.collider_index<=31 else (.85,)*3)
                translated=r.active_qte_geometry(root_position=(0,0,0))
                for local_box,world_box in zip(translated,boxes):
                    for actual,expected in zip(local_box.center,(world_box.center[0],world_box.center[1],world_box.center[2]-16)):
                        self.assertAlmostEqual(actual,expected)
                EncounterRuntime.advance(r,50)
                self.assertEqual(r.active_qte_geometry(),())

    def test_phase_cinematics_use_asset_clock_and_only_run_once(self):
        durations={'ultra':3,'harvester':1/60,'indivilia':8.966666666666667,'mirror-container':5}
        for family,seconds in durations.items():
            with self.subTest(family=family):
                r=RaidBossRuntime([],180,key='anomaly-'+family)
                node=next(n for n in r.tree.nodes.values() if n['Type'].endswith('.isPhaseAction'))
                r.time=37
                r.effects['barrier']=(40,1)
                state={'started':37}
                self.assertEqual(r.world.action(node,37,state),'failure' if family=='indivilia' else 'running')
                self.assertEqual(r.time,37)
                if family!='indivilia':
                    self.assertEqual(r.world.phase,1)
                    self.assertFalse(r.phase_cinematics[0]['battle_clock_paused'])
                    r.time=37+seconds
                    self.assertEqual(r.world.action(node,r.time,state),'failure')
                self.assertEqual(r.world.phase,2)
                self.assertEqual(r.effects['barrier'],(40,1))
                self.assertAlmostEqual(r.phase_cinematics[0]['seconds'],seconds)
                self.assertEqual(r.world.action(node,38,{'started':38}),'failure')
                self.assertEqual(len(r.phase_cinematics),1)
                self.assertEqual(r.phase_cinematics[0]['stop_spot_tick'],family=='indivilia')

    def test_indivilia_phase_preserves_function_deadlines(self):
        r=RaidBossRuntime([],180,key='anomaly-indivilia')
        bind(r);r.time=30;r.effects['barrier']=(40,1);r.part_immune['Weapon_03']=35
        node=next(n for n in r.tree.nodes.values() if n['Type'].endswith('.isPhaseAction'))
        r.world.action(node,30,{'started':30})
        self.assertTrue(r.phase_cinematics[-1]['stop_spot_tick'])
        r.finish_cinematic_time(r.phase_cinematics[-1]['seconds'])
        self.assertEqual(r.effects['barrier'],(40,1))
        self.assertEqual(r.part_immune['Weapon_03'],35)
        self.assertEqual(r.world.phase,2)

    def test_stage_passive_element_multiplier_matches_native_function(self):
        # Native GetElementBonusDamage plus ProcessFunctionAddEvent/GetDamageInfo
        # verified these ratios independently in a hidden original-DLL process.
        for key in ('ultra','harvester','indivilia','mirror-container'):
            r=RaidBossRuntime([],180,key='anomaly-'+key)
            for stage in r.stages:
                r.damage=stage['ConditionValueMin']
                self.assertEqual(r.stage_element_multiplier(),4 if stage['Step']<=3 else 5 if stage['Step']<=6 else 6)

    def test_cover_has_no_owner_element_for_stage_advantage(self):
        # Original SpotCharacterCover.GetTargetElementIDList returns an empty
        # list even when its owner has an elemental code.
        r=RaidBossRuntime([],180,key='anomaly-ultra',auto_cover=False)
        bm,names=bind(r);name=names[0]
        skill=dict(r.skills[1],Id=-1,ShotCount=1,TargetCharacterRatio=100,TargetCoverRatio=0)
        hits={}
        for recipient in ('character','cover'):
            for element in ('수냉','철갑'):
                r.squad[name]['element_code']=element
                bm.state['hp'][name]=1e9;r.cover[name]=1e9
                r.receive_attack(skill,{'_locked_targets':[name],'_target_recipient':recipient})
                hits[recipient,element]=r.incoming[-1]
        self.assertEqual(hits['cover','수냉']['absorbed'],hits['cover','철갑']['absorbed'])
        self.assertAlmostEqual(hits['character','수냉']['damage'],hits['character','철갑']['damage']*4,delta=3)

    def test_incoming_reductions_add_and_damage_rounds_after_minimum(self):
        r=RaidBossRuntime([],180,key='anomaly-ultra',auto_cover=False)
        bm,names=bind(r);name=names[0]
        r.stat=lambda monster=None:dict(LevelAttack=1001,LevelStatdamageratio=10000)
        r.active_stat=lambda target,stat:-20 if stat=='received_dmg_pct' else 0
        bm._effective_def=lambda target:0
        monster=dict(r.data['monster'],AttackRatio=10000)
        skill=dict(r.skills[1],Id=-1,ShotCount=1,SkillValue01=10000)
        with patch('unit_combat.elemental_reduction_percent',return_value=-30):
            r.receive_attack(skill,{'_locked_targets':[name],'_target_recipient':'character'},monster=monster)
        # Native reductions combine to 50%; DoubleToLong(500.5) is 501.
        self.assertEqual(r.incoming[-1]['damage'],501)
        bm._effective_def=lambda target:1002
        with patch('unit_combat.elemental_reduction_percent',return_value=-30):
            r.receive_attack(skill,{'_locked_targets':[name],'_target_recipient':'character'},monster=monster)
        self.assertEqual(r.incoming[-1]['damage'],1)

    def test_airborne_attack_snapshot_survives_stage_change(self):
        r=RaidBossRuntime([],180,key='anomaly-ultra',auto_cover=False)
        bm,names=bind(r);name=names[0]
        skill=dict(r.skills[1],Id=-1,ShotCount=1)
        snapshot=r.capture_incoming_snapshot()
        node={'_locked_targets':[name],'_target_recipient':'character','_incoming_snapshot':snapshot}
        r.receive_attack(skill,node)
        original=r.incoming[-1]['damage']
        r.damage=r.stages[-1]['ConditionValueMin']
        r.receive_attack(skill,node)
        self.assertEqual(r.incoming[-1]['damage'],original)
        r.receive_attack(skill,dict(node,_incoming_snapshot=None))
        self.assertGreater(r.incoming[-1]['damage'],original)

    def test_ordinary_instant_dispatch_uses_physical_muzzle_hits(self):
        for family,shot,count,last in [('ultra',5,20,1.9),('harvester',1,15,1.4),('mirror-container',2,12,1.1)]:
            with self.subTest(family=family):
                r=RaidBossRuntime([],180,key='anomaly-'+family)
                fired=[];r.receive_attack=lambda skill,node:fired.append(skill)
                r.perform_skill(r.skills[shot],{})
                self.assertEqual(len(fired),1)
                self.assertEqual(len(r.pending_shots),count-1)
                self.assertAlmostEqual(r.pending_shots[-1]['at'],last)
                self.assertEqual(fired[0]['_damage_shots'],r.skills[shot]['ShotCount'])
        r=RaidBossRuntime([],180,key='anomaly-harvester')
        fired=[];r.receive_attack=lambda skill,node:fired.append(skill)
        r.perform_skill(r.skills[2],{})
        self.assertEqual(len(fired),7)
        self.assertTrue(all(s['_damage_shots']==1 for s in fired))
        self.assertTrue(all(s['SkillValue01']==int(r.skills[2]['SkillValue01']/7+.5) for s in fired))

    def test_phase_preserves_unfired_instant_volley(self):
        r=RaidBossRuntime([],180,key='anomaly-ultra')
        bind(r)
        r.perform_skill(r.skills[5],{})
        self.assertTrue(r.pending_shots)
        node=next(n for n in r.tree.nodes.values() if n['Type'].endswith('.isPhaseAction'))
        self.assertEqual(r.world.action(node,0,{'started':0}),'running')
        self.assertEqual(r.world.phase,1)
        self.assertTrue(r.pending_shots)

    def test_destroyed_ordinary_weapon_emits_no_hits(self):
        r=RaidBossRuntime([],180,key='anomaly-mirror-container')
        r.world.parts.damage('Weapon_01',1e20,0)
        fired=[];r.receive_attack=lambda skill,node:fired.append(skill)
        skill=next(s for s in r.skills.values() if s['ControlParts']==['Weapon01'])
        r.perform_skill(skill,{})
        self.assertEqual(fired,[])
        self.assertEqual(r.pending_shots,[])

    def test_fixed_slot_does_not_retarget_a_dead_or_missing_unit(self):
        r=RaidBossRuntime([],180,key='anomaly-indivilia')
        bm,names=bind(r)
        skill=r.skills[5]
        self.assertEqual(r.attack_targets(skill,{'ECharacterPosition_targetPosition':'Player1'}),[names[0]])
        bm.state['hp'][names[0]]=0
        self.assertEqual(r.attack_targets(skill,{'ECharacterPosition_targetPosition':'Player1'}),[])
        self.assertEqual(r.attack_targets(skill,{'ECharacterPosition_targetPosition':'Player5'}),[])
        self.assertEqual(r.attack_targets(skill,{'_locked_targets':[names[0]]}),[])

    def test_cover_hurt_conditions_match_original_runtime_truth_table(self):
        r=RaidBossRuntime([],180,key='anomaly-harvester')
        # Native IsCover(value=1) passes for SpotCharacter only.
        self.assertIn(1999636,[f['Id'] for f in r.hurt_functions(r.skills[1],'character')])
        self.assertNotIn(1999636,[f['Id'] for f in r.hurt_functions(r.skills[1],'cover')])
        # The sniper add's cover-only 10% effect must never damage character HP.
        skill=next(s for s in r.data['skills'] if s['Id']==210201)
        self.assertIn(1999641,[f['Id'] for f in r.hurt_functions(skill,'cover')])
        self.assertNotIn(1999641,[f['Id'] for f in r.hurt_functions(skill,'character')])

    def test_delayed_summon_clear_does_not_execute_at_cast_start(self):
        r=RaidBossRuntime([],180,key='anomaly-harvester')
        r.adds=[{'id':'test-add','hp':100,'skill':None}]
        r.apply_function(1999167)
        self.assertEqual(r.adds[0]['hp'],100)
        self.assertEqual(r.pending_functions[0]['at'],.3)
        r.tree.advance=lambda t:None
        r.anomaly=None
        r.advance(.29,{})
        self.assertEqual(r.adds[0]['hp'],100)
        r.advance(.3,{})
        self.assertEqual(r.adds[0]['hp'],0)

    def test_shared_summon_skill_keeps_each_monsters_hurt_functions(self):
        r=RaidBossRuntime([],180,key='anomaly-harvester')
        skill=next(s for s in r.data['skills'] if s['Id']==100101)
        monsters={m['Id']:m for m in r.data['monsters']}
        self.assertEqual(r.hurt_functions(skill,monster=monsters[1220050613]),[])
        self.assertEqual([f['Id'] for f in r.hurt_functions(skill,monster=monsters[3210040113])],[1999642])

    def test_barrier_activation_and_expiry_preserve_report_windows(self):
        r=RaidBossRuntime([],180,key='anomaly-ultra')
        r.time=2;r.apply_function(1999600)
        self.assertTrue(r.barrier)
        self.assertEqual(r.barrier_windows,[{'start':2,'end':None}])
        r.time=5;r.apply_function(1999601)
        r.time=5.02;r.update_barrier()
        self.assertFalse(r.barrier)
        self.assertEqual(r.barrier_windows[0]['end'],5.02)

    def test_harvester_memory_red_target_waits_for_recorded_delay(self):
        r=RaidBossRuntime([],180,key='anomaly-harvester')
        state={}
        r.special_qte({'Int32_quickTimeId':10156},0,state)
        targets=r.states[state['qte']]['event']['graph']
        red=next(x for x in targets if x['kind']=='break')
        self.assertEqual(red['delay'],7)
        counters=[x for x in targets if x['kind']=='counter']
        self.assertEqual([round(x['delay'],1) for x in counters],[1,1.8,2.6,3.4,4.2,5])

    def test_memory_preview_does_not_ban_spread_weapons_after_greys_expire(self):
        from mechanics import EncounterRuntime
        r=RaidBossRuntime([],180,key='anomaly-harvester')
        state={};r.special_qte({'Int32_quickTimeId':10156},0,state)
        EncounterRuntime.advance(r,0)
        EncounterRuntime.advance(r,7)
        r.update_qte_hazards()
        red=r.active['graph'].aim(7)
        self.assertIsNone(red['weapons'])
        self.assertTrue(r.active['event']['full_burst_follow'])
        r=RaidBossRuntime([],180,key='anomaly-ultra')
        state={};r.special_qte({'Int32_quickTimeId':10152},0,state)
        EncounterRuntime.advance(r,0)
        EncounterRuntime.advance(r,1)
        r.update_qte_hazards()
        red=r.active['graph'].aim(1)
        self.assertNotIn('RL',red['weapons'])
        self.assertFalse(r.active['event']['full_burst_follow'])

    def test_special_qte_defence_ignores_mirror_body_function_layers(self):
        from mechanics import EncounterRuntime
        r=RaidBossRuntime([],180,key='anomaly-mirror-container')
        bm,names=bind(r);r.world.phase=2
        for ident in (1999472,):r.apply_function(ident)
        q=r.data['qtes'][0];state={}
        r.special_qte({'Int32_quickTimeId':q['Id']},0,state)
        event=r.states[state['qte']]['event']
        base=r.stat()['LevelDefence']*r.data['monster']['DefenceRatio']/10000
        self.assertTrue(all(t['def']==base for t in event['graph']))
        EncounterRuntime.advance(r,0)
        target=r.active['graph'].targets[next(t['id'] for t in event['graph'] if t['kind']=='break')]
        target.update(status='active',activated=0)
        r.target=lambda *args:target
        seen=[]
        def calculate(**kwargs):
            seen.append(kwargs['enemy_def']);return dict(damage=1,is_crit=False,crit_frac=0)
        kind=dict(is_normal_atk=True)
        r.resolve(names[0],'전격','SR',kind,calculate,dict(hit_type=kind))
        self.assertEqual(seen,[base])

    def test_independent_qte_and_summon_do_not_inherit_boss_debuffs(self):
        from mechanics import EncounterRuntime
        r=RaidBossRuntime([],180,key='anomaly-harvester')
        bm,names=bind(r);seen=[]
        buffs=dict(enemy_def_down_pct=-40,received_dmg=25,atk_pct=30)
        bm.state['encounter_runtime']=r
        for stat,value in [('def_pct',-40),('received_dmg_pct',25)]:
            bm._activate(dict(type='buff',stat=stat,fixed_value=value,target='all_enemies',
                              name='before summons '+stat,duration=10,trigger={'condition':[]}),names[0],0)
        def calculate(**kwargs):
            seen.append(kwargs['buffs']);return dict(damage=1,is_crit=False,crit_frac=0)
        kind=dict(is_normal_atk=True)
        event=dict(kind='qte',start=0,duration=10,controller=names[0],targets=[dict(hp=100,target_kind='special_qte')])
        r.add_event(event);EncounterRuntime.advance(r,0);r.aim_seconds=0
        result=r.resolve(names[0],'전격','AR',kind,calculate,dict(hit_type=kind,buffs=buffs))
        self.assertEqual(seen[-1],dict(enemy_def_down_pct=0,received_dmg=0,atk_pct=30))
        self.assertEqual((result['collision_hits'],result['body_hits'],result['part_hits']),(1,0,0))
        r.active=None
        row=next(c for c in r.data['calls'] if c['Id']==1482)
        r.anomaly._spawn_add(row,0)
        r.resolve(names[0],'전격','AR',dict(effect_target='all_enemies'),calculate,dict(hit_type={},buffs=buffs))
        self.assertEqual(seen[-2],buffs)
        self.assertEqual(seen[-1],dict(enemy_def_down_pct=0,received_dmg=0,atk_pct=30))
        self.assertEqual(buffs['received_dmg'],25)

    def test_multi_preset_interruption_shares_one_native_deadline(self):
        r=RaidBossRuntime([],180,key='anomaly-ultra')
        node={'Int32_quickTimeId':10152};state={}
        r.special_qte(node,20,state)
        # 7 seconds plus two one-second first-signal animations.
        self.assertEqual(state['deadline'],29)
        self.assertEqual(r.states[state['qte']]['event']['duration'],9)
        r.states[state['qte']]['status']='passed'
        r.special_qte(node,25,state)
        r.special_qte(node,25.02,state)
        event=r.states[state['qte']]['event']
        self.assertAlmostEqual(event['start']+event['duration'],29)
        self.assertLess(event['duration'],4)

    def test_harvester_timeline_markers_fire_once_at_each_fixed_slot(self):
        r=RaidBossRuntime([],180,key='anomaly-harvester')
        bm,names=bind(r)
        node=next(n for n in r.tree.nodes.values() if n['Type'].endswith('.TimelineSkill') and n.get('List`1_aniNumberTypes')==['Shot_07','Shot_04'])
        fired=[]
        r.perform_skill=lambda skill,attack_node:fired.append((r.time,r.attack_targets(skill,attack_node)))
        state={'started':0,'shot_index':1}
        r.world.action(node,0,state)
        self.assertEqual(len(state['impacts']),5)
        self.assertAlmostEqual(state['impacts'][0],1.2666666666666666)
        for at in state['impacts']:
            r.time=at;r.world.action(node,at,state)
        self.assertEqual([targets for _,targets in fired],[[n] for n in names]+[[]]*(5-len(names)))

    def test_mirror_real_timeline_repeats_inner_attack_markers(self):
        r=RaidBossRuntime([],180,key='anomaly-mirror-container')
        node=next(n for n in r.tree.nodes.values() if n['Type'].endswith('.TimelineSkill') and n.get('List`1_aniNumberTypes')==['Shot_12'])
        state={'started':0}
        r.world.action(node,0,state)
        self.assertEqual(len(state['impacts']),10)
        self.assertAlmostEqual(state['end'],11.166666666666666)

    def test_mirror_opening_move_uses_source_distance_acceleration_and_zone(self):
        r=RaidBossRuntime([],180,key='anomaly-mirror-container')
        node=r.tree.nodes[10];state={'started':0}
        self.assertEqual(r.world.action(node,0,state),'running')
        result='running'
        for tick in range(1,114):
            result=r.world.action(node,tick*.02,state)
            if result=='success':break
        self.assertEqual(result,'success')
        self.assertAlmostEqual(tick*.02,2.24)
        self.assertGreater(r.world.coordinates['z'],65)
        self.assertLessEqual(r.world.coordinates['z'],66)
        carried=r.world.move_speed
        # Re-entering an already reached destination neither moves nor resets speed.
        self.assertEqual(r.world.action(node,3,{'started':3}),'success')
        self.assertEqual(r.world.move_speed,carried)

    def test_indivilia_move_already_at_source_point_is_immediate(self):
        r=RaidBossRuntime([],180,key='anomaly-indivilia')
        r.world.coordinates=dict(r.world.movement_data['points']['154'])
        self.assertEqual(r.world.action(r.tree.nodes[45],0,{'started':0}),'success')

    def test_poison_matches_native_immediate_and_rounded_duration_ticks(self):
        r=RaidBossRuntime([],180,key='anomaly-ultra',auto_cover=False)
        bm,names=bind(r);name=names[0]
        f=r.functions[1999619]
        bm.state['hp'][name]=1_000_000
        r.apply_hurt_dot(f,name,r.data['monster'])
        self.assertEqual(bm.state['hp'][name],980_000)
        r.time=1.49;r.advance_dots(r.time)
        self.assertEqual(len(r.incoming),1)
        for tick in range(150,1501):
            r.time=tick/100;r.advance_dots(r.time)
        self.assertEqual(len(r.incoming),15)
        self.assertEqual([e['time'] for e in r.incoming],[0]+[1.5+i for i in range(14)])
        # Original function output with each measured integer fed back as HP.
        self.assertEqual([e['damage'] for e in r.incoming],[20000,19600,19208,18824,18447,18078,17717,17363,17015,16675,16341,16015,15694,15380,15073])
        self.assertEqual(bm.state['hp'][name],738570)
        self.assertEqual(r.dot_ticks,[])

    def test_poison_refresh_hits_immediately_and_restarts_bucket_timer(self):
        r=RaidBossRuntime([],180,key='anomaly-ultra',auto_cover=False)
        bm,names=bind(r);name=names[0]
        f=r.functions[1999619]
        r.apply_hurt_dot(f,name,r.data['monster'])
        r.time=.5;r.apply_hurt_dot(f,name,r.data['monster'])
        self.assertEqual([e['time'] for e in r.incoming],[0,.5])
        self.assertEqual(len(r.dot_ticks),1)
        r.time=1.5;r.advance_dots(r.time)
        self.assertEqual(len(r.incoming),2)
        r.time=2;r.advance_dots(r.time)
        self.assertEqual(r.incoming[-1]['time'],2)

    def test_add_weighted_cover_target_hits_cover_of_an_exposed_unit(self):
        r=RaidBossRuntime([],180,key='anomaly-harvester',auto_cover=False)
        bm,names=bind(r);name=names[0]
        monster=next(m for m in r.data['monsters'] if m['Id']==3220070113)
        skill=next(s for s in r.data['skills'] if s['Id']==210201)
        r.rng.choices=lambda *args,**kwargs:['cover']
        before=bm.state['hp'][name];cover=r.cover[name]
        r.receive_attack(skill,{'_locked_targets':[name]},monster=monster)
        self.assertEqual(bm.state['hp'][name],before)
        self.assertLess(r.cover[name],cover)
        self.assertEqual(r.incoming[-1]['blocked_by'],'cover')

    def test_indivilia_edge_pierce_adds_body_hit_without_second_part_hit(self):
        r=RaidBossRuntime([],180,key='anomaly-indivilia')
        bm,names=bind(r);caster=names[0];part='Weapon_01'
        r.select_part=lambda _:part
        r.active_stat=lambda name,stat:1 if stat=='pierce_enabled' else 0
        before=r.world.parts.parts[part]['hp']
        args=[]
        def calculate(**kwargs):
            args.append(kwargs)
            return dict(damage=100,is_crit=False,crit_frac=0)
        result=r.resolve(caster,'전격','SR',{'is_normal_atk':True},calculate,{'hit_type':{'is_normal_atk':True}})
        self.assertEqual(result['damage'],200)
        self.assertEqual((result['collision_hits'],result['part_hits'],result['body_hits']),(2,1,1))
        self.assertEqual(r.damage,200)
        self.assertEqual(r.world.parts.parts[part]['hp'],before-100)
        self.assertEqual(r.damage_to_parts,100)
        self.assertTrue(args[0]['hit_type']['is_part'])
        self.assertFalse(args[1]['hit_type']['is_part'])

    def test_ultra_pierce_hits_core_and_each_living_chamber_separately(self):
        r=RaidBossRuntime([],180,key='anomaly-ultra')
        bm,names=bind(r);caster=names[0]
        r.select_part=lambda _:'Weapon_01'
        r.active_stat=lambda name,stat:1 if stat=='pierce_enabled' else 0
        before={name:part['hp'] for name,part in r.world.parts.parts.items()}
        kinds=[]
        def calculate(**kwargs):
            kinds.append(kwargs['hit_type'])
            return dict(damage=200 if kwargs['hit_type'].get('core_prob') else 100,is_crit=False,crit_frac=0)
        kind=dict(is_normal_atk=True,core_prob=1)
        result=r.resolve(caster,'철갑','SR',kind,calculate,dict(hit_type=kind))
        self.assertEqual(result['damage'],400)
        self.assertEqual((result['collision_hits'],result['part_hits'],result['core_hits'],result['body_hits']),(3,3,1,0))
        self.assertEqual(r.damage_to_parts,400)
        self.assertEqual(r.world.parts.parts['Weapon_01']['hp'],before['Weapon_01']-200)
        for part in ('Weapon_02','Weapon_03'):
            self.assertEqual(r.world.parts.parts[part]['hp'],before[part]-100)
        self.assertTrue(all(k['is_part'] for k in kinds))
        self.assertEqual([k['core_prob'] for k in kinds],[1,0,0])

    def test_ultra_controlled_pierce_can_select_hidden_finite_core(self):
        r=RaidBossRuntime([],180,key='anomaly-ultra')
        bm,names=bind(r);caster=r.aim_controller
        self.assertNotEqual(r.select_part(caster),'Weapon_01')
        r.active_stat=lambda name,stat:1 if stat=='pierce_enabled' else 0
        self.assertEqual(r.select_part(caster),'Weapon_01')
        before=r.world.parts.parts['Weapon_01']['hp']
        kind=dict(is_normal_atk=True)
        r.resolve(caster,'철갑','SR',kind,lambda **kw:dict(damage=100,is_crit=False,crit_frac=0),dict(hit_type=kind))
        self.assertEqual(r.world.parts.parts['Weapon_01']['hp'],before-100)

    def test_all_parts_skill_hits_body_and_live_colliders_including_occluded_core(self):
        r=RaidBossRuntime([],180,key='anomaly-ultra')
        bm,names=bind(r);kinds=[]
        r.world.parts.parts['Weapon_02']['hp']=1
        r.world.parts.self_destruct('Weapon_03',0)
        before=r.world.parts.parts['Weapon_01']['hp']
        def calculate(**kwargs):
            kinds.append(kwargs['hit_type'])
            return dict(damage=100,is_crit=False,crit_frac=0)
        kind=dict(hits_parts=True)
        result=r.resolve(names[0],'철갑','AR',kind,calculate,dict(hit_type=kind))
        self.assertEqual(result['damage'],300)
        self.assertEqual((result['collision_hits'],result['part_hits'],result['body_hits']),(3,2,1))
        self.assertEqual(r.world.parts.parts['Weapon_01']['hp'],before-100)
        self.assertEqual(r.damage_to_parts,101)
        self.assertEqual(len(r.part_break_events),1)
        self.assertEqual([k['is_part'] for k in kinds],[False,True,True])
        self.assertTrue(all(k['core_prob']==0 for k in kinds))

    def test_zero_damage_barrier_collisions_still_grant_target_gauge(self):
        r=RaidBossRuntime([],180,key='anomaly-ultra')
        bm,names=bind(r);r.barrier=True
        r.select_part=lambda caster:'Weapon_01'
        r.active_stat=lambda name,stat:1 if stat=='pierce_enabled' else 0
        kind=dict(is_normal_atk=True,core_prob=1)
        before=r.world.parts.parts['Weapon_01']['hp']
        result=r.resolve(names[0],'작열','SR',kind,lambda **kw:dict(damage=100,is_crit=False,crit_frac=0),dict(hit_type=kind))
        self.assertEqual(result['damage'],0)
        self.assertEqual(result['collision_hits'],3)
        self.assertEqual(r.world.parts.parts['Weapon_01']['hp'],before)
        kind=dict(hits_parts=True)
        result=r.resolve(names[0],'작열','SR',kind,lambda **kw:dict(damage=100,is_crit=False,crit_frac=0),dict(hit_type=kind))
        self.assertEqual(result['damage'],0)
        self.assertEqual((result['collision_hits'],result['part_hits']),(4,3))

    def test_all_enemy_and_split_skills_use_each_summons_defence(self):
        for split in (False,True):
            with self.subTest(split=split):
                r=RaidBossRuntime([],180,key='anomaly-harvester')
                bm,names=bind(r)
                row=next(c for c in r.data['calls'] if c['Id']==1482)
                r.anomaly._spawn_add(row,0)
                add=r.adds[0];add['hp']=add['max_hp']=1_000_000
                defence=add['defence'];seen=[]
                def calculate(**kwargs):
                    seen.append(kwargs['enemy_def'])
                    return dict(damage=max(0,100_000-kwargs['enemy_def'])*kwargs['hit_type']['coeff']/100,is_crit=False,crit_frac=0)
                kind=dict(effect_target='all_enemies',is_split=split,coeff=100)
                result=r.resolve(names[0],'전격','AR',kind,calculate,dict(hit_type=kind))
                self.assertEqual(result['collision_hits'],2)
                self.assertEqual(seen[-1],defence)
                expected=(100_000-defence)/(2 if split else 1)
                self.assertAlmostEqual(r.damage_to_adds,expected)
                self.assertAlmostEqual(add['hp'],1_000_000-expected)
                add['hp']=1
                r.resolve(names[0],'전격','AR',kind,calculate,dict(hit_type=kind))
                self.assertEqual(add['state'],'destroyed')
                self.assertEqual(add['clear_reason'],'squad')

    def test_ranked_skill_hits_selected_summon_and_same_target_does_not_retarget_death(self):
        r=RaidBossRuntime([],180,key='anomaly-harvester')
        bm,names=bind(r)
        row=next(c for c in r.data['calls'] if c['Id']==1482)
        r.anomaly._spawn_add(row,0);r.anomaly._spawn_add(row,0)
        first,second=r.adds
        first['hp']=10;second['hp']=1000
        kind=dict(effect_target='enemies_lowest_hp:1',effect_name='ranked strike')
        seen=[]
        def calculate(**kwargs):
            seen.append(kwargs['enemy_def']);return dict(damage=100,is_crit=False,crit_frac=0)
        result=r.resolve(names[0],'전격','AR',kind,calculate,dict(hit_type=kind))
        self.assertEqual(result['damage'],0)
        self.assertEqual(result['collision_hits'],1)
        self.assertEqual(first['hp'],0)
        self.assertEqual(second['hp'],1000)
        self.assertEqual(r.damage,0)
        self.assertEqual(seen,[first['defence']])
        kind=dict(effect_target='same_target:ranked strike',effect_name='followup')
        result=r.resolve(names[0],'전격','AR',kind,calculate,dict(hit_type=kind,enemy_def=0))
        self.assertEqual(result['collision_hits'],0)
        self.assertEqual(second['hp'],1000)
        self.assertEqual(r.damage,0)

    def test_qte_does_not_remove_all_enemy_or_all_parts_skill_recipients(self):
        from mechanics import EncounterRuntime
        for family,kind,expected in (
                ('harvester',dict(effect_target='all_enemies'),2),
                ('ultra',dict(hits_parts=True),4)):
            with self.subTest(family=family):
                r=RaidBossRuntime([],180,key='anomaly-'+family)
                bm,names=bind(r)
                if family=='harvester':
                    row=next(c for c in r.data['calls'] if c['Id']==1482)
                    r.anomaly._spawn_add(row,0)
                r.add_event(dict(kind='qte',start=0,duration=10,controller=names[0],
                                 targets=[dict(hp=100,target_kind='special_qte')]))
                EncounterRuntime.advance(r,0)
                result=r.resolve(names[0],'철갑','AR',kind,
                                 lambda **kw:dict(damage=10,is_crit=False,crit_frac=0),dict(hit_type=kind))
                self.assertEqual(result['collision_hits'],expected)
                self.assertEqual(r.active['dealt'],0)

    def test_indivilia_no_all_monster_summons_do_not_dilute_split_damage(self):
        for split in (False,True):
            with self.subTest(split=split):
                r=RaidBossRuntime([],180,key='anomaly-indivilia')
                bm,names=bind(r)
                row=next(c for c in r.data['calls'] if c['MonsterId']==2210050635)
                r.anomaly._spawn_add(row,0)
                add=r.adds[0];before=add['hp']
                kind=dict(effect_target='all_enemies',is_split=split)
                result=r.resolve(names[0],'작열','AR',kind,
                    lambda **kw:dict(damage=100,is_crit=False,crit_frac=0),dict(hit_type=kind))
                self.assertEqual(result['damage'],100)
                self.assertEqual(result['collision_hits'],1)
                self.assertEqual(add['hp'],before)
                self.assertEqual(r.damage_to_adds,0)
                # Exclusion belongs to the all-monster function selector;
                # an aimed weapon hit can still damage this same summon.
                kind=dict(is_normal_atk=True)
                result=r.resolve(r.aim_controller,'작열','AR',kind,
                    lambda **kw:dict(damage=100,is_crit=False,crit_frac=0),dict(hit_type=kind))
                self.assertEqual(result['damage'],0)
                self.assertEqual(add['hp'],before-100)

    def test_all_enemy_dot_uses_each_original_recipient_once(self):
        from types import SimpleNamespace
        r=RaidBossRuntime([],180,key='anomaly-harvester')
        bm,names=bind(r)
        row=next(c for c in r.data['calls'] if c['Id']==1482)
        r.anomaly._spawn_add(row,0)
        first=r.adds[0];first['hp']=1000
        bm._active.append(SimpleNamespace(caster=names[0],effect={'name':'fixed dot'},
            enemy_target_windows={entity:dict(activated_at=0,expires_at=10,stack=1)
                                  for entity in ('__boss__',first['id'])}))
        r.anomaly._spawn_add(row,1)
        second=r.adds[1];second['hp']=1000
        r.time=2
        kind=dict(effect_target='all_enemies',effect_name='fixed dot',is_dot=True)
        result=r.resolve(names[0],'전격','AR',kind,
                         lambda **kw:dict(damage=100,is_crit=False,crit_frac=0),dict(hit_type=kind))
        self.assertEqual(result['collision_hits'],2)
        self.assertEqual(result['damage'],100)
        self.assertEqual(first['hp'],900)
        self.assertEqual(second['hp'],1000)
        self.assertEqual(r.damage_to_adds,100)

    def test_live_phase_advances_poison_without_rebasing_any_deadline(self):
        from calculator.cinematics import CinematicCursor
        r=RaidBossRuntime([],180,key='anomaly-ultra')
        bm,names=bind(r);name=names[0]
        bm.state['hp'][name]=1_000_000
        r.apply_hurt_dot(r.functions[1999619],name,r.data['monster'])
        r.effects['barrier']=(1,1);r.update_barrier()
        node=next(n for n in r.tree.nodes.values() if n['Type'].endswith('.isPhaseAction'))
        state={'started':0}
        self.assertEqual(r.world.action(node,0,state),'running')
        self.assertEqual(r.world.phase,1)
        self.assertEqual(CinematicCursor().consume(r,0),[])
        for frame in range(1,181):
            r.time=frame/60
            bm.tick(r.time);r.advance_dots(r.time);r.update_barrier()
            r.world.action(node,r.time,state)
        self.assertEqual(r.time,3)
        self.assertEqual(r.world.phase,2)
        self.assertFalse(r.barrier)
        self.assertAlmostEqual(bm.state['hp'][name],1_000_000*.98**3)
        self.assertAlmostEqual(r.dot_ticks[0]['next'],3.5)
        self.assertAlmostEqual(r.dot_ticks[0]['end'],15)
        self.assertEqual([e['time'] for e in r.incoming],[0,1.5,2.5])
        self.assertEqual(r.world.action(node,3,state),'failure')

    def test_outgoing_periodic_callbacks_see_cinematic_function_clock(self):
        from calculator.cinematics import advance_cinematic_functions
        r=RaidBossRuntime([],180,key='anomaly-ultra')
        bm,names=bind(r)
        r.effects['barrier']=(.5,1);r.update_barrier()
        observed=[];tick=bm.tick
        def record(time):
            observed.append((time,r.time,r.barrier))
            tick(time)
        bm.tick=record
        advance_cinematic_functions(bm,None,bm.state,0,1,.25,r.advance_cinematic_time,before_tick=r.begin_cinematic_time)
        self.assertEqual(observed,[(.25,.25,True),(.5,.5,False),(.75,.75,False),(1,1,False)])
        self.assertEqual(r.time,0)
        self.assertIsNone(r._cinematic_frame)

    def test_indivilia_memory_sequence_does_not_skip_the_preview(self):
        r=RaidBossRuntime([],180,key='anomaly-indivilia')
        state={}
        r.special_qte({'Int32_quickTimeId':10126},0,state)
        targets=r.states[state['qte']]['event']['graph']
        red=next(x for x in targets if x['id']==11)
        self.assertEqual(red['delay'],4.5)
        self.assertTrue(red['first'])

    def test_boss_debuff_immunity_rejects_new_harmful_effect(self):
        r=RaidBossRuntime([],180,key='anomaly-indivilia')
        bm,names=bind(r)
        r.apply_function(1999390)
        self.assertTrue(bm._has_immune('__enemy__','debuff_immune'))
        eff=dict(type='buff',stat='def_pct',fixed_value=-50,name='test def down',target='enemy',
                 polarity='harmful',duration=10,trigger={'condition':[]})
        bm._activate(eff,names[0],0)
        self.assertFalse(any(a.effect is eff for a in bm._active))
        r.time=2;r.apply_function(1999405)
        bm.advance_time(2.02) if hasattr(bm,'advance_time') else None
        r.time=2.02
        self.assertFalse(any(a.effect.get('stat')=='debuff_immune' and a.expires_at>r.time for a in bm._active))


if __name__=='__main__':unittest.main()
