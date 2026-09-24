"""Variant-specific raid AI with finite parts, interruptions and incoming attacks.

Recovered records drive branch decisions. Physical geometry and animation travel
are approximations and remain explicit in every report.
"""
import unit_combat
import copy
import json
import math
import random
from pathlib import Path
from boss_behavior import BehaviorTree, RUNNING, SUCCESS, FAILURE, UnsupportedBossAction
from boss_world import PartWorld
from boss_parts import part_max_hp, part_break_damage
from mechanics import EncounterRuntime
from enemy_damage import incoming_hit
from mother_whale_combat import part_name
from kraken_combat import KrakenRuntime
from critical_parts import Deadlines
from anomaly_ultra_harvester import (build_anomaly_mechanics as build_ultra_harvester,
                                     HARVESTER_BOSS_POINT)
from anomaly_mirror_indivilia import build_anomaly_mechanics as build_mirror_indivilia
from anomaly_projectiles import (build_anomaly_mechanics as build_projectile_mechanics,
                                 FORMATION_AIM)
from anomaly_target_context import (damage_args_for_target, select_enemy_effect_targets,
                                    enemy_attack_for_target, direct_skill_enemy_targets,
                                    all_monster_targetable)
from anomaly_qte_geometry import QTEBox, prefab_box_side
from anomaly_timing import (DATA as TIMING_DATA, phase_duration, phase_stops_spot_tick, timeline_schedule,
                            combat_zone_contains, move_distance, move_reached, move_speed_step,
                            ordinary_fire_schedule)

DATA=json.loads((Path(__file__).parent/'raid-boss-combat-data.json').read_text(encoding='utf-8'))
PROFILES=DATA['profiles']
ELEMENTS={100001:'작열',200001:'수냉',300001:'풍압',400001:'전격',500001:'철갑'}
COUNTER={100001:'수냉',200001:'전격',300001:'작열',400001:'철갑',500001:'풍압'}
WEAK_UNITS={100001:'풍압',200001:'작열',300001:'철갑',400001:'수냉',500001:'전격'}
NAMES={'sr39':'Island Eater','sr40':'Luxurious Spider',**{k:k.split('-',1)[1].replace('-',' ').title() for k in PROFILES if k.startswith(('museum-','anomaly-','special-'))}}
PART_LABELS={
 'indivilia':{'Weapon_03':'Tail','Weapon_01':'Left pincer','Weapon_02':'Right pincer','Weapon_04':'Phase 2 head','Weapon_05':'Core'},
 'modernia':{'Weapon_03':'Core','Weapon_01':'Left wing','Weapon_02':'Right wing'},
 'ultra':{'Weapon_01':'Core','Weapon_02':'Left poison chamber','Weapon_03':'Right poison chamber'},
 'crystal-chamber':{'Weapon_01':'Left crystal','Weapon_02':'Right crystal'},
 'blacksmith':{'Arm_Left':'Left gun','Arm_Right':'Right gun','Weapon_01':'Core'},
 'sr40':{'Weapon_01':'Egg sac'},
 'harvester':{'Head':'Head shell','Leg_Front_Left':'Left leg','Leg_Front_Right':'Right leg'},
}
ASSUMPTIONS=[
    'Outside Full Burst, only the selected aim controller directs weapon fire at the chosen part. Full Burst or an active Focus Fire skill redirects allied fire. Other AI units are modeled firing at the body; incidental part hits are not credited. Opening samples compare up to five fixed part-aim choices; promising controllers receive full-fight verification. Separate QTE and projectile targeting reactions still apply.',
 'Each content variant uses its own recovered AI, skill values, finite parts, QTE records and damage-triggered stat stages.',
 'Weapon fire is directed at urgent parts, interruption targets and summons. Skill damage does not automatically break a part. Damage spent on adds and QTEs is excluded from the boss score.',
 'QTE aim assumes accurate target selection, with 0.15 seconds per target. Grey targets restrict the controller to precise weapons; spread collision and manual aiming errors are not reproduced.',
 'Finite non-main parts use LevelBrokenHp with the monster and part HP ratios, following the recovered client constructor. Main or linked body HP uses LevelHp. Interruption HP uses LevelBrokenHp. Geometry and complete fights still need gameplay validation.',
 'Part destruction causes separate body HP loss using the main part BrokenHp and the destroyed part DamageHpRatio. This bonus is reported separately from direct character damage and does not increase lifesteal.',
 'Animation loops use table casting time. Movement and phase animations use one second when no explicit duration is present; projectile flight and overlap geometry remain approximate.',
 'Incoming damage uses enemy ATK and skill percentage, effective DEF and the level damage ratio. Finite cover, shields, healing, taunt, stun and invulnerability affect the run. Units stop attacking when defeated; living revival skills can restore them. Scoring stops when the squad is defeated.',
 'Ordinary projectile interception and summon travel are approximate. Museum weekly buffs are not applied. Modeled survival is not a verified in-game clear.',
 'Crystal sphere uses a 300-hit check and a modeled ten-second flight window; exact Museum travel needs client validation. Poison ticks use one-second intervals. Boss debuff immunity, collision-based cover bypass and overlapping pierce targets are not fully reproduced.',
]

class RaidWorld(PartWorld):
    def __init__(self,runtime):
        self.runtime=runtime;self.rows={part_name(p['PartsType']):p for p in runtime.data['parts']}
        self.main_part=next((p for p in self.rows.values() if p.get('IsMainPart')),None)
        super().__init__({n:part_max_hp(runtime.stat(),runtime.data['monster'],p,self.main_part) for n,p in self.rows.items()})
        self.position=254;self.direction=254;self.phase=1;self.attacks={};self.core_enabled=True;self.speed=1.
        self.finished_phase_checks=set()
        # Installed Anomaly spawn origin and early native attacks use point153.
        # Point154 incorrectly entered the optional opening return-jump branch.
        if 'indivilia' in runtime.key:self.position=153
        self.movement_data=TIMING_DATA['profiles'].get(runtime.key)
        self.coordinates=copy.deepcopy(self.movement_data['points'].get(str(self.position))) if self.movement_data else None
        # Spawn geometry exists before the AI records its first visited-point
        # index. Preserve that index's sentinel for IsInPoint branches.
        if runtime.key=='anomaly-ultra':self.coordinates=copy.deepcopy(self.movement_data['points']['151'])
        if runtime.key=='anomaly-harvester':self.coordinates=dict(zip(('x','y','z'),HARVESTER_BOSS_POINT))
        self.move_speed=0.
        for n,hp in self.part_hp.items():self.parts.spawn(n,hp,0)

    def cancel(self,node,time):
        attack=self.attacks.pop(node['ID'],None)
        if attack:
            if attack.get('qte'):self.runtime.finish_event(attack['qte'])
            self.runtime.log('boss attack branch cancelled',node=node['ID'])

    def choose(self,node,time,state):
        state.setdefault('started',time)
        if time-state['started']<self.runtime.aim_seconds:return None
        if 'choice' not in state:
            choice=self.runtime.choice_policy
            if choice=='auto':
                # Hit count capability comes from current weapon cadence, not class.
                rapid=any(cs.weapon_type=='MG' for cs in getattr(self.runtime,'char_states',{}).values())
                choice='projectile' if rapid else 'debuff'
            state['choice']=0 if choice=='projectile' else 1
            self.runtime.choices.append(dict(time=round(time,3),route=choice,node=node['ID']))
            self.runtime.log('boss attack choice',route=choice)
        return state['choice']

    def action(self,node,time,state):
        r=self.runtime;kind=node['Type'].split('.')[-1]
        if r.stopped:return RUNNING
        if kind=='CheckHp':
            if not r.key.startswith('anomaly-'):
                value=node['Int32mValue'];p=self.parts.parts.get(node['PartsTypemPartsType'])
                if node.get('BooleanisUsingMianHp'):
                    fraction=max(0,1-r.damage/(r.stat()['LevelHp']*r.data['monster']['HpRatio']/10000))*100
                    result=fraction<=value
                elif value in (0,1):result=not self.parts.alive(node['PartsTypemPartsType'])
                else:result=(p['hp']/p['max_hp']*100 if p else 0)<=value
                return SUCCESS if result==node['BooleanmLower'] else FAILURE
            value=node['Int32mValue'];p=self.parts.parts.get(node['PartsTypemPartsType'])
            if node.get('BooleanisUsingMianHp'):
                fraction=max(0,1-r.damage/(r.stat()['LevelHp']*r.data['monster']['HpRatio']/10000))*100
            else:fraction=p['hp']/p['max_hp']*100 if p else 0
            # CheckHp::OnUpdate 0x65199a0 uses strict comparisons in both
            # directions. Equality fails for either mLower value.
            result=fraction<value if node['BooleanmLower'] else fraction>value
            return SUCCESS if result else FAILURE
        if kind=='CheckPhase':
            # Native CheckPhase::OnUpdate (0x651af70) is a continuation
            # guard: TaskStatus.Success=2 until the threshold is reached,
            # then Failure=1, latched in _isfinishPhase for this node's
            # lifetime. The enclosing endOnFailure repeater exits the phase.
            if node['ID'] in self.finished_phase_checks:return FAILURE
            typ=node['PhaseCheckType_type'];value=node['Single_phaseValue']
            if typ=='BerserkStep':finished=r.stage()['Step']>=value
            elif typ=='HpRatio':finished=100*(1-r.damage/(r.stat()['LevelHp']*r.data['monster']['HpRatio']/10000))<value
            else:raise UnsupportedBossAction(typ)
            if finished:self.finished_phase_checks.add(node['ID'])
            return FAILURE if finished else SUCCESS
        if kind=='CheckMonsterCount':
            if not r.key.startswith('anomaly-'):
                return SUCCESS if node['Int32min']<=1+len(r.living_adds())<=node['Int32max'] else FAILURE
            # OnStart caches the inclusive range test. Native count excludes
            # FunctionNoneTargetType.ExcludeSpawnAndCountCheck (2); none of the
            # four recovered anomaly add profiles carries that flag.
            if 'monster_count_passed' not in state:
                count=1+len(r.living_adds())
                state['monster_count_passed']=node['Int32min']<=count<=node['Int32max']
            return SUCCESS if state['monster_count_passed'] else FAILURE
        if kind=='CheckVariableNode':
            if not r.key.startswith('anomaly-'):return super().action(node,time,state)
            # Native OnStart resets tick; first OnUpdate yields Running.
            if not state.get('variable_checked_once'):
                state['variable_checked_once']=True
                return RUNNING
            return SUCCESS if self.variables.get(node['MonsterBtVariabletype'],0)==node['Int32value'] else FAILURE
        if kind.startswith('BrokenParts'):
            for p in node['List`1_partsList']:
                if self.parts.alive(p):
                    self.parts.self_destruct(p,time)
                    r.anomaly_hook('on_part_broken',p,time,False)
            return SUCCESS
        if kind.startswith('RepairParts'):
            if time-state['started']<node.get('Single_repairTime',0):return RUNNING
            if not state.get('repaired'):
                for p in node['List`1_partsList']:
                    if p not in self.part_hp:raise UnsupportedBossAction('Unknown part '+p)
                    # Anomaly core/part replacement follows the current damage stage.
                    if r.key.startswith('anomaly-'):
                        self.part_hp[p]=part_max_hp(r.stat(),r.data['monster'],self.rows[p],self.main_part)
                    self.parts.spawn(p,self.part_hp[p],time);r.part_immune.pop(p,None)
                    r.anomaly_hook('on_part_repaired',p,time)
                state['repaired']=True
            return SUCCESS
        if kind=='isPhaseAction':
            if r.key in TIMING_DATA['profiles']:
                requested=2
                if self.phase<requested:
                    if not phase_stops_spot_tick(r.key):
                        # Scene type 2 is a live timeline. Campaign and Spot
                        # clocks keep ticking; only this boss tree node waits
                        # for IsPlayingTimeLine to clear. Type 4 is death.
                        if 'phase_end' not in state:
                            seconds=phase_duration(r.key)
                            state['phase_end']=time+seconds
                            r.phase_cinematics.append(dict(time=time,seconds=seconds,phase=requested,
                                stop_spot_tick=False,battle_clock_paused=False))
                            r.anomaly_hook('on_cinematic_start',time)
                        if time+1e-9<state['phase_end']:return RUNNING
                        self.phase=requested
                        r.log('boss phase changed',phase=requested,paused_seconds=0)
                        r.anomaly_hook('on_phase_changed',requested,time)
                        return FAILURE
                    if r.bm:
                        if not state.get('cinematic_requested'):
                            state['cinematic_requested']=True
                            r.phase_cinematics.append(dict(time=time,seconds=phase_duration(r.key),phase=requested,stop_spot_tick=phase_stops_spot_tick(r.key)))
                            r.pending_phase=requested
                            r.anomaly_hook('on_cinematic_start',time)
                        return RUNNING
                    r.phase_cinematics.append(dict(time=time,seconds=phase_duration(r.key),phase=requested,stop_spot_tick=phase_stops_spot_tick(r.key)))
                    r.anomaly_hook('on_cinematic_start',time)
                    self.phase=requested
                    r.log('boss phase changed',phase=requested,paused_seconds=phase_duration(r.key))
                    r.anomaly_hook('on_phase_changed',requested,time)
                return FAILURE
            if not state.get('applied'):
                self.phase=2;state['applied']=True;r.log('boss phase changed',phase=2)
                r.anomaly_hook('on_phase_changed',2,time)
            return FAILURE if time-state['started']>=1 else RUNNING
        if kind=='ColliderControlNode':self.core_enabled=node['Boolean_on'];return SUCCESS
        if kind=='IsInPoint':
            if not r.key.startswith('anomaly-'):
                return SUCCESS if self.position==node['Int32_point'] else FAILURE
            point_type=node['DirectionType_pointType']
            if point_type=='SelectPoint':point=node['Int32_point']
            elif point_type=='DirectionPoint':point=self.direction
            elif point_type=='StartPoint':point=self.position
            else:raise UnsupportedBossAction('Unknown IsInPoint target '+str(point_type))
            destination=self.movement_data['points'].get(str(point)) if self.movement_data else None
            if self.coordinates is None or destination is None:
                raise UnsupportedBossAction('Missing IsInPoint geometry for '+r.key+' point '+str(point))
            reached=move_reached(self.coordinates,destination,node['Single_duration'],node['Boolean_usingAxisY'])
            return SUCCESS if reached else FAILURE
        if kind=='SetDirection':self.direction=node.get('Int32mPointIndex',self.direction);return SUCCESS
        if kind.startswith(('MoveTo','TeleportTo','JumpTo')):
            if self.movement_data:
                if kind=='JumpToVer2':
                    # JumpReady -> SetJump -> JumpEnd is sequential. The BT
                    # waits for IsJumping to clear, not merely mDuration.
                    # Native Indivilia confirms both animation waits; frame
                    # scheduling adds a small observed completion tolerance.
                    animation=self.movement_data.get('jump_animation')
                    if animation is None:
                        raise UnsupportedBossAction('Missing jump animation timing for '+r.key)
                    elapsed=time-state['started']
                    flight_end=(node.get('Single_startDelay',0)+animation['start_seconds']
                                +node['SinglemDuration'])
                    if elapsed+1e-9>=flight_end:
                        dest=node['Int32mPointIndex']
                        self.position=dest
                        self.coordinates=copy.deepcopy(self.movement_data['points'][str(dest)])
                    return SUCCESS if elapsed+1e-9>=flight_end+animation['end_seconds'] else RUNNING
                movement=next((m for m in self.movement_data['movement_nodes'] if m['node_id']==node['ID']),None)
                if movement and kind=='MoveToVer2':
                    destination=self.movement_data['points'][str(movement['point_index'])]
                    if self.coordinates is None:raise UnsupportedBossAction('Missing source position for '+r.key)
                    elapsed=max(0.,time-state.get('last_move_time',time));state['last_move_time']=time
                    while elapsed>1e-9 and not move_reached(self.coordinates,destination,movement['tolerance'],movement['using_axis_y']):
                        dt=min(.02,elapsed);elapsed-=dt
                        zone='in' if combat_zone_contains(self.coordinates) else 'out'
                        self.move_speed=move_speed_step(self.move_speed,self.movement_data['monster_speed_raw'],
                            movement[zone+'_combat_zone_speed_rate'],self.movement_data['acceleration_time_raw'],dt)
                        distance=move_distance(self.coordinates,destination,True)
                        fraction=min(1.,self.move_speed*dt/distance) if distance else 1.
                        for axis in ('x','y','z'):self.coordinates[axis]+=(destination[axis]-self.coordinates[axis])*fraction
                    if move_reached(self.coordinates,destination,movement['tolerance'],movement['using_axis_y']):
                        self.position=movement['point_index'];return SUCCESS
                    return RUNNING
            duration=node.get('Single_teleportTime',node.get('SinglemDuration',1.))
            if time-state['started']<duration:return RUNNING
            dest=node.get('Int32_pointIndex',node.get('Int32mPointIndex',self.direction))
            if node.get('PositionCheckTypePositionCheckType')=='PointRange':dest=r.rng.randint(node['Int32_pointRangeMin'],node['Int32_pointRangeMax'])
            self.position=dest
            if self.movement_data:self.coordinates=copy.deepcopy(self.movement_data['points'].get(str(dest)))
            return RUNNING if kind=='MoveTo' else SUCCESS
        if kind=='IsTargetAlive':
            if not r.key.startswith('anomaly-'):
                names=list(getattr(r,'squad',{}));index=int(node['ECharacterPosition_targetPosition'][-1])-1
                return SUCCESS if not r.bm or index<len(names) and r.bm.state['hp'][names[index]]>0 else FAILURE
            names=list(getattr(r,'squad',{}));index=int(node['ECharacterPosition_targetPosition'][-1])-1
            if index<0 or index>=len(names):return FAILURE
            if node.get('Boolean_isNotHide'):
                raise UnsupportedBossAction('IsTargetAlive._isNotHide needs Function 107 status')
            if not r.bm:return FAILURE
            return SUCCESS if r.bm.state['hp'][names[index]]>0 else FAILURE
        if kind=='IsExistObstacle':return FAILURE # No static map obstacles in this approximation.
        if kind=='SetSpeedRate':self.speed=max(.01,node['SinglemCustomSpeedRate']);return SUCCESS
        if kind in ('EmptySuccess','SetMoveType','StopMove','StopMoveSuccess','TurnAround','StartAttack','EndAttack','AttackRelease'):return SUCCESS
        if kind=='QuickTimeEvent':return r.special_qte(node,time,state)
        if kind not in ('Attack','AttackV2','AttackV3','TimelineSkill','BreakCol'):return super().action(node,time,state)
        shots=node.get('List`1_aniNumberTypes',[node.get('SkillAniNumberTypemSkillAniNumber')])
        index=state.get('shot_index',0);shot=int(shots[index].split('_')[-1]);skill=r.skills[shot]
        if 'impacts' not in state:
            cast=skill['CastingTime']/100;timeline=r.data['timelines'].get(str(shot)) if kind=='TimelineSkill' else None
            if kind=='TimelineSkill' and r.key in TIMING_DATA['profiles']:
                timeline=TIMING_DATA['profiles'][r.key]['timelines'].get(str(shot),timeline)
            if timeline:
                if r.key in TIMING_DATA['profiles']:
                    schedule=timeline_schedule(timeline,cast)
                    impacts=[time+at for at in schedule['impacts']];end=time+schedule['end']
                    state['impact_events']=schedule['impact_events']
                    interrupt=time+(schedule['loop']['start'] if schedule['loop'] else 0)
                else:
                    markers=timeline['markers'];starts=[m['time'] for m in markers if m['type'].endswith('/LoopStart')];ends=[m['time'] for m in markers if m['type'].endswith('/LoopEnd')]
                    shift=cast-(ends[0]-starts[0]) if starts and ends else 0.
                    impacts=[time+m['time']+(shift if ends and m['time']>=ends[0] else 0) for m in markers if m['type'].endswith('/Attack')]
                    impacts=impacts or [time+cast];end=max(time+timeline['duration']+shift,max(impacts))
                    interrupt=time+(starts[0] if starts else 0)
            else:impacts=[time+cast];end=time+(cast+skill['DelayTime']/100)/self.speed;interrupt=time
            state.update(impacts=impacts,end=end,fired=0,shot=shot,interrupt=interrupt,parts=[part_name(p) for p in skill['ControlParts']],node=node)
            state['targets']=r.attack_targets(skill,node)
            state['cover_until']=max(impacts,default=end)+max(0,skill['ShotCount']-1)*skill['DelayTime']/100+.1
            ordinary=r.ordinary_schedule(skill,min(impacts,default=time),node)
            if ordinary:
                state['cover_until']=ordinary['end']+.1
                state['end']=ordinary.get('action_end',max(state['end'],ordinary['end']))
            state['node']=dict(node,_locked_targets=state['targets'])
            self.attacks[node['ID']]=state
            r.update_cover(time)
            r.apply_skill_functions(skill,'UseFunctionIdSkill')
            for p in state['parts']:
                if self.parts.alive(p) and impacts:self.parts.parts[p]['attack_at']=min(impacts)
            if skill['CancelType'].startswith('BrokenParts') and impacts:
                r.part_deadlines.register(self.parts,state['parts'],min(impacts),shot)
            r.log('boss attack started',shot=shot,impact=round(min(impacts),3) if impacts else None,node=node['ID'])
        parts=state['parts'];cancel=skill['CancelType'].startswith('BrokenParts') and parts and any(not self.parts.alive(p) for p in parts)
        override=r.anomaly_hook('attack_cancelled',skill,state,time)
        if override is not None:cancel=override
        if cancel and (override is not None or not state['fired']):
            reason='part hit cancelled attack' if skill['CancelType']=='BrokenPartsHurtCount' else 'part destruction cancelled attack'
            r.log(reason,shot=shot,parts=parts,markers_fired=state['fired']);self.attacks.pop(node['ID'],None);return FAILURE if node.get('BooleanFailueCheck') else SUCCESS
        if skill['BreakObject'] and state['impacts'] and time>=state['interrupt'] and 'qte' not in state:
            state['qte']=r.ordinary_qte(skill,time,max(.02,min(state['impacts'])-time))
        if state.get('qte') and r.states[state['qte']]['status']=='passed':
            self.attacks.pop(node['ID'],None);r.log('interruption cancelled attack',shot=shot)
            return FAILURE if node.get('BooleanFailueCheck') else SUCCESS
        while state['fired']<len(state['impacts']) and time>=state['impacts'][state['fired']]-1e-9:
            index_fired=state['fired'];state['fired']+=1
            marker=state.get('impact_events',[{}]*len(state['impacts']))[index_fired]
            impact_node=state['node']
            target=marker.get('target',0)
            if target in (1,2,3,4,5):
                impact_node=dict(impact_node,ECharacterPosition_targetPosition='Player'+str(target))
                impact_node.pop('_locked_targets',None)
            dispatched=skill
            if r.key in TIMING_DATA['profiles'] and 'impact_events' in state and skill['FireType'] in ('Instant','InstantAllFrontRay'):
                # Native timeline dispatch passes shotCount=1 to FireInstant.
                # Repeating table ShotCount here duplicates hurt functions.
                dispatched=dict(skill,ShotCount=1,_damage_shots=1)
            r.perform_skill(dispatched,impact_node)
        if time>=state['end']-1e-9:
            self.attacks.pop(node['ID'],None)
            if index+1<len(shots):
                state.clear();state.update(started=time,shot_index=index+1);return RUNNING
            return SUCCESS
        return RUNNING

class RaidBossRuntime(EncounterRuntime):
    active_stat=KrakenRuntime.active_stat
    protection=KrakenRuntime.protection

    def __init__(self,script,duration,*,key,mode='challenge',seed=42,choice_policy='auto',part_policy='safe',auto_cover=True):
        super().__init__(script,duration)
        if choice_policy not in ('auto','projectile','debuff'):raise ValueError('Invalid boss attack choice')
        if part_policy not in ('safe','body','all'):raise ValueError('Invalid part targeting policy')
        self.key=key;self.data=dict(PROFILES[key]);self.mode=mode if mode in self.data['modes'] else 'challenge'
        self.data['monster']=self.data['mode_monsters'][self.mode]
        self.rng=random.Random(seed);self.choice_policy=choice_policy;self.part_policy=part_policy;self.auto_cover=auto_cover;self.aim_seconds=.15
        group=self.data['modes'][self.mode]['MonsterStageLvChangeGroup']
        self.stages=sorted([s for s in self.data['stages'] if s['Group']==group],key=lambda x:x['ConditionValueMin'])
        self.stat_rows={(s['GroupId'],s['Lv']):s for s in self.data['stats']}
        allskills={s['Id']:s for s in self.data['skills']}
        self.skills={int(allskills[s['SkillId']]['SkillAniNumber'][4:]):allskills[s['SkillId']] for s in self.data['monster']['SkillData'] if s['SkillId']}
        self.functions={f['Id']:f for f in self.data['functions']};self.effects={};self.part_immune={};self.part_hits={};self.debuff_effects={}
        self.world=RaidWorld(self);self.tree=BehaviorTree(self.data['trees'][self.mode],self.world,seed)
        self.bm=None;self.cover={};self.cover_max={};self.cover_def={};self.covered=set();self.incoming=[];self.pending_shots=[];self.adds=[];self.pending=[]
        self.choices=[];self.normal_by_unit={};self.aim_id=None;self.aim_ready=0.;self.part_cursor=0;self.stop_reason=None;self.damage_to_parts=0.;self.damage_to_adds=0.;self.barrier_damage_by_unit={};self.barrier_windows=[];self.barrier=False
        self.first_part_deadlines={};self.first_breaks={};self.unhandled=set();self.dot_ticks=[];self.cover_windows=[];self.projectiles=[];self.cover_threats=[];self.cover_open={}
        self.part_deadlines=Deadlines()
        self.part_break_damage=0.;self.part_break_events=[]
        self.anomaly=build_ultra_harvester(self) or build_mirror_indivilia(self)
        self.projectile_mechanics=build_projectile_mechanics(self)
        self.pending_functions=[]
        self.phase_cinematics=[]
        self.pending_phase=None
        self.last_enemy_target_by_caster={}

    def anomaly_hook(self,name,*args):
        if name=='on_part_broken':
            part=args[0]
            self.pending_shots=[s for s in self.pending_shots if not
                (str(s['skill'].get('CancelType','')).startswith('BrokenParts') and
                 part in [part_name(p) for p in s['skill'].get('ControlParts',[])])]
        projectile=getattr(getattr(self,'projectile_mechanics',None),name,None)
        if projectile and name in ('perform_skill','resolve_target','resolve_hit'):
            result=projectile(*args)
            if result:return result
        if projectile and name in ('advance','on_part_broken','on_part_repaired','on_phase_changed','on_cinematic_start','advance_cinematic_functions','advance_cinematic_projectiles','rebase_cinematic_functions'):projectile(*args)
        hook=getattr(getattr(self,'anomaly',None),name,None)
        return hook(*args) if hook else None

    def log(self,event,**details):self.events.append(dict(time=round(self.time,3),event=event,**details))
    def begin_cinematic_time(self,elapsed,delta):
        # Keep the virtual clock installed while BuffManager runs outgoing
        # periodic effects; those callbacks also resolve against this runtime.
        self._cinematic_frame=(self.time,len(self.incoming),len(self.events))
        self._cinematic_active_projectiles={p['id'] for p in self.projectiles if p.get('status')=='active'}
        self.time+=elapsed
        for item in list(self.pending_functions):
            if item['at']<=self.time:
                self.pending_functions.remove(item)
                self.apply_function(item['ident'],item.get('target'),item.get('part'),delayed=True)
        self.update_barrier()
        self.anomaly_hook('advance_cinematic_functions',self.time)

    def advance_cinematic_time(self,elapsed,delta):
        if getattr(self,'_cinematic_frame',None) is None:self.begin_cinematic_time(elapsed,delta)
        battle_time,incoming_start,event_start=self._cinematic_frame
        try:
            # Incoming periodic damage observes the shields and buffs after
            # BuffManager has expired/advanced them at this virtual frame.
            self.anomaly_hook('advance_cinematic_projectiles',self.time)
            self.advance_dots(self.time)
            self.update_barrier()
        finally:
            self.time=battle_time;self._cinematic_frame=None
            for row in self.incoming[incoming_start:]+self.events[event_start:]:
                row['cinematic_elapsed']=round(elapsed,3);row['time']=round(battle_time,3)
            for projectile in self.projectiles:
                if projectile['id'] in self._cinematic_active_projectiles and projectile.get('status')=='hit':
                    projectile['cinematic_elapsed']=round(projectile.get('hit_at',battle_time+elapsed)-battle_time,6)
                    for field in ('hit_at','impact_at','deadline'):
                        if projectile.get(field) is not None:projectile[field]=battle_time

    def finish_cinematic_time(self,seconds):
        if not phase_stops_spot_tick(self.key):
            self.effects={key:(end-seconds,value) for key,(end,value) in self.effects.items()}
            for item in self.dot_ticks:
                item['next']-=seconds;item['end']-=seconds
            for item in self.pending_functions:item['at']-=seconds
            self.part_immune={part:end-seconds for part,end in self.part_immune.items()}
            self.anomaly_hook('rebase_cinematic_functions',seconds)
            for window in self.barrier_windows:
                if window['end'] is not None and window['end']>self.time:window['end']=self.time
        if self.pending_phase is not None:
            self.world.phase=self.pending_phase
            self.anomaly_hook('on_phase_changed',self.pending_phase,self.time)
            self.log('boss phase changed',phase=self.pending_phase,paused_seconds=seconds)
            self.pending_phase=None
    def update_barrier(self):
        active=self.effects.get('barrier',(0,0))[0]>self.time
        if active==self.barrier:return
        self.barrier=active
        if active:self.barrier_windows.append(dict(start=self.time,end=None))
        elif self.barrier_windows:self.barrier_windows[-1]['end']=self.time
        self.log('element barrier enabled' if active else 'element barrier removed')
    def stage(self):
        return max((s for s in self.stages if self.damage>=s['ConditionValueMin']),key=lambda s:s['ConditionValueMin'])
    def stat(self,monster=None):return self.stat_rows[((monster or self.data['monster'])['StatenhanceId'],self.stage()['MonsterStageLv'])]
    def bind(self,bm,squad,char_states):
        self.bm=bm;self.squad={c['name']:c for c in squad};self.char_states=char_states
        bm.state['encounter_runtime']=self
        if self.key in TIMING_DATA['profiles']:
            # Distance selectors need a real slot origin even for bosses
            # without the separate curve-projectile mechanics component.
            observed=getattr(self,'squad_coordinates',{})
            self.squad_coordinates={name:observed.get(name,FORMATION_AIM[slot])
                                    for slot,name in enumerate(self.squad)}
        rows={r['Lv']:r for r in DATA['cover_stats']}
        for n,c in self.squad.items():
            row=rows[min(400,max(1,int(c.get('level',400))))]
            self.cover[n]=self.cover_max[n]=row['LevelHp']*(1+self.active_stat(n,'cover_hp_pct')/100);self.cover_def[n]=row['LevelDefence']
        self.aim_controller=self.aim_controller_override or max(char_states,key=lambda n:char_states[n].base_atk)
        def repair(eff,caster,t,value):
            for n in bm._resolve_target(eff.get('target','all_allies'),caster):
                if self.cover.get(n,0)>0:self.cover[n]=min(self.cover_max[n],self.cover[n]+self.cover_max[n]*value/100)
        bm.register_instant_handler('cover_heal_pct',repair)

    def add_event(self,event):
        event=dict(event,id='raid-'+str(len(self.states)))
        checked=EncounterRuntime([event]);self.states.update(checked.states);return event['id']
    def finish_event(self,ident):
        if ident in self.states and self.states[ident]['status'] in ('pending','active'):self.states[ident]['status']='complete'
    def ordinary_qte(self,skill,time,duration):
        precise=any('counter' in s for s in skill['BreakObject'])
        targets=[dict(hp=self.stat()['LevelBrokenHp']*skill['BreakObjectHpRaito']/10000,
            element=COUNTER[self.data['monster']['ElementId'][0]] if self.barrier else None,
            weapons=['AR','SMG','MG','SR'] if precise else None) for s in skill['BreakObject'] if 'counter' not in s]
        if not targets or any(t['hp']<=0 for t in targets):raise UnsupportedBossAction('Missing interruption HP '+str(skill['Id']))
        return self.add_event(dict(kind='qte',start=time,duration=duration,targets=targets,controller='auto',full_burst_follow=not precise,on_fail='downtime',failure_downtime=0))

    def special_qte(self,node,time,state):
        record=next(q for q in self.data['qtes'] if q['Id']==node['Int32_quickTimeId'])
        if 'groups' not in state:
            state['groups']=[self.rng.choice(record['GroupId'])] if record['RandomPreset'] else list(record['GroupId']);state['group']=0
            if self.key in TIMING_DATA['profiles']:
                # Native QuickTimeEventContext owns one timer across presets;
                # its budget adds the first-signal animation for each group.
                state['deadline']=time+(record['TimeLimit']+record['FirstColAnimTime']*len(record['GroupId']))/100
        if 'qte' not in state:
            if 'deadline' in state and time>=state['deadline']:return SUCCESS
            group=state['groups'][state['group']];rows=[q for q in self.data['qte_targets'] if q['GroupId']==group]
            linked={i for q in rows for i in q['Chain']};precise=any(q['ColType']=='Counter' for q in rows)
            targets=[dict(id=q['ColIndex'],kind='break' if q['ColType']=='Break' else 'counter',target_kind='special_qte',
                hp=self.stat()['LevelBrokenHp']*q['HpRatio']/10000,duration=q['TimeLimit']/100,
                **{'def':self.stat()['LevelDefence']*self.data['monster']['DefenceRatio']/10000*q['DefRatio']/10000},
                first=q['FirstCol'] or q['ColIndex'] not in linked,delay=(q['DelayTime']+(record['FirstColAnimTime'] if q['ColIndex'] not in linked else 0))/100,
                chain=q['Chain'],element=COUNTER[record['ElementId']] if self.barrier and record['ElementId'] in COUNTER else None,
                weapons=['AR','SMG','MG','SR'] if precise else None) for q in rows]
            if self.key in TIMING_DATA['profiles']:
                for target,row in zip(targets,rows):
                    target['local_position']=tuple(row['ColPosition'])
                    target['box_size']=(prefab_box_side(record['QtePrefab'],row['ColIndex']),)*3
            duration=state['deadline']-time if 'deadline' in state else record['TimeLimit']/100
            state['qte']=self.add_event(dict(kind='qte',start=time,duration=duration,graph=targets,controller='auto',full_burst_follow=not precise,precision_hazards=precise and self.key in TIMING_DATA['profiles'],on_fail='downtime',failure_downtime=0))
            self.log('special interruption',pattern=record['Id'],group=group)
        status=self.states[state['qte']]['status']
        if status=='passed':
            state['group']+=1
            if state['group']<len(state['groups']):state.pop('qte');return RUNNING
            return FAILURE # Client AI uses success for the failed-check attack branch.
        if status in ('failed','unknown'):return SUCCESS
        return RUNNING

    def active_qte_geometry(self,root_position=(0,0,16)):
        """Active world boxes from local ColPosition and the prefab root.

        All four recovered roots are authored at z=16. The shared native
        initialization preserves that offset; six live Indivilia SetCollider
        observations independently confirmed (0, 0, 16).
        """
        graph=self.active.get('graph') if self.active else None
        if graph is None:return ()
        graph.advance(self.time)
        if graph.status!='active':return ()
        return tuple(QTEBox(row['id'],tuple(a+b for a,b in zip(row['local_position'],root_position)),tuple(size/2 for size in row['box_size']))
                     for row in graph.targets.values()
                     if row['status']=='active' and 'box_size' in row)

    def apply_skill_functions(self,skill,field,target=None):
        mapping=next((s for m in self.data['monsters'] for s in m['SkillData'] if s['SkillId']==skill['Id']),None)
        for i in (mapping or {}).get(field,[]):self.apply_function(i,target)

    def apply_function(self,ident,target=None,part=None,*,delayed=False):
        if not ident:return
        f=self.functions[ident];kind=f['FunctionType'];value=f['FunctionValue'];duration=f['DurationValue']/100
        if f['TimingTriggerType'] not in ('None','OnStart'):return
        if f.get('DelayType')=='TimeSec' and f.get('DelayValue',0)>0 and not delayed:
            self.pending_functions.append(dict(at=self.time+f['DelayValue']/100,ident=ident,target=target,part=part))
            return
        if self.anomaly_hook('apply_function',ident,target,part):return
        if kind=='TargetPartsId':
            row=next((p for p in self.data['parts'] if p['Id']==value),None)
            # Shared model functions may reference the base model's part IDs.
            if row is None:row=next((p for p in self.data['parts'] if p['Id']%100==value%100),None)
            if row:part=part_name(row['PartsType'])
        elif kind=='ImmuneOtherElement':
            self.effects['barrier']=(self.time+duration,value)
            self.update_barrier()
        elif kind=='DebuffImmune' and f['FunctionTarget']=='Self':
            if self.bm:
                group=f.get('GroupId') or ident
                self.bm._active=[a for a in self.bm._active if a.effect.get('boss_function_group')!=group]
                eff=dict(type='buff',stat='debuff_immune',fixed_value=1,name='Boss immunity '+str(group),target='enemy',
                    polarity='beneficial',duration=duration or -1,trigger={'condition':[]},boss_function_group=group)
                self.bm._activate(eff,next(iter(self.squad)),self.time)
        elif kind in ('StatAtk','StatDef') and f['FunctionTarget']=='Self':
            self.effects[ident]=(self.time+(duration or self.duration),value)
        elif kind in ('StatAtk','Stun','HealVariation') and f['FunctionTarget'] in ('Target','AllCharacter'):
            if self.bm:
                names=list(self.squad) if f['FunctionTarget']=='AllCharacter' else ([target] if target else [])
                stat={'StatAtk':'atk_pct','Stun':'stun','HealVariation':'heal_received_pct'}[kind]
                for n in names:
                    eff=self.debuff_effects.setdefault((ident,n),dict(type='buff',stat=stat,fixed_value=value/100,name='Boss effect '+str(ident),target='self',polarity='harmful',duration=duration or -1,max_stack=max(1,f['FullCount']),trigger={'condition':[]}))
                    self.bm._activate(eff,n,self.time)
        elif kind=='InstantDeath' and f['FunctionTarget']=='AllMonster':
            for a in self.living_adds():a.update(hp=0,clear_reason='boss attack',cleared_at=self.time)
        elif kind.startswith('PartsHpChange') and part:
            old=self.world.part_hp[part];new=old*(1+value/10000) if f['FunctionValueType']=='Percent' else value
            if new>0:
                self.world.part_hp[part]=new
                if self.world.parts.alive(part):
                    p=self.world.parts.parts[part];p['hp']=new*p['hp']/p['max_hp'];p['max_hp']=new
        elif kind=='PartsImmuneDamage' and part:self.part_immune[part]=self.time+duration
        elif kind in ('Damage','CurrentHpRatioDamage'):pass # Applied to actual hit recipient below.
        elif kind not in ('None','Immortal','ImmuneStun','ImmuneForcedStop','ImmuneGravityBomb','DebuffImmune','StatHpHeal','DamageReduction','DamageShareLowestPriority','IncElementDmg','ImmuneInstantDeath'):
            self.unhandled.add(kind)
        for child in f['ConnectedFunction']:self.apply_function(child,target,part)

    def living_adds(self):return [a for a in self.adds if a['hp']>0]
    def ordinary_schedule(self,skill,start,node):
        if str(node.get('Type','')).endswith('TimelineSkill'):return None
        records=TIMING_DATA['profiles'].get(self.key,{}).get('ordinary_fire',{})
        if str(skill['Id']) not in records:return None
        destroyed=[row['PartsType'] for name,row in self.world.rows.items() if not self.world.parts.alive(name)]
        return ordinary_fire_schedule(self.key,skill['Id'],start=start,destroyed_parts=destroyed)

    def perform_skill(self,skill,node):
        if self.anomaly_hook('perform_skill',skill,node):pass
        elif skill['FireType']=='Calling':
            for row in self.data['calls']:
                if row['GroupId']==skill['SkillValue01']:self.pending.append(dict(at=self.time+row['SpawnTime'],record=row))
        elif self.key=='museum-crystal-chamber' and skill['SkillAniNumber'] in ('Shot06','Shot15'):
            self.projectiles.append(dict(id='sphere-'+str(len(self.projectiles)),hp=300,max_hp=300,spawned=self.time,deadline=self.time+10,skill=skill,node=node,status='active'))
            self.log('crystal sphere launched',hits_required=300,deadline=round(self.time+10,3))
        elif skill['SkillValueType01']=='Percent' and skill['SkillValue01']>0:
            ordinary=self.ordinary_schedule(skill,self.time,node)
            if ordinary and skill['FireType']=='Instant':
                for at in ordinary['impacts']:
                    dispatched=dict(skill,ShotCount=1,SkillValue01=ordinary['damage_coefficient_raw'],_damage_shots=ordinary['damage_shot_count'])
                    if at<=self.time+1e-9:self.receive_attack(dispatched,node)
                    else:self.pending_shots.append(dict(at=at,skill=dispatched,node=node))
            elif skill['ShotTiming']=='Sequence' and skill['ShotCount']>1:
                for i in range(skill['ShotCount']):self.pending_shots.append(dict(at=self.time+i*skill['DelayTime']/100,skill=dict(skill,ShotCount=1,_damage_shots=skill['ShotCount']),node=node))
            else:self.receive_attack(skill,node)
        self.log('boss skill activated',shot=skill['SkillAniNumber'])

    def advance(self,t,state=None):
        self.time=t;self.frame=state or {};self.covered=set()
        if self.stopped:return
        if t>=self.duration-1e-9:self.stopped=True;return
        self.update_cover(t)
        self.tree.advance(t)
        if self.tree.status!=RUNNING:
            # Terminal scripts are finite encounter scripts, not implicit immortality.
            self.log('boss script ended',status=self.tree.status)
            self.stop_reason='Boss script ended before the fight duration';self.stopped=True;return
        self.update_cover(t)
        for item in list(self.pending_functions):
            if t>=item['at']:
                self.pending_functions.remove(item)
                self.apply_function(item['ident'],item['target'],item['part'],delayed=True)
        self.anomaly_hook('advance',t)
        for projectile in self.projectiles:
            if projectile.get('kind')=='hostile':continue
            if projectile['status']=='active' and t>=projectile['deadline']:
                projectile['status']='failed';self.receive_attack(projectile['skill'],dict(projectile['node'],_bypass_cover=True))
                self.log('crystal sphere hit squad',remaining_hits=projectile['hp'])
        self.advance_dots(t)
        for item in list(self.pending):
            if getattr(self.anomaly,'handles_summons',False):continue
            if t<item['at']:continue
            self.pending.remove(item);m=next(m for m in self.data['monsters'] if m['Id']==item['record']['MonsterId'])
            skills=[s for s in self.data['skills'] if s['Id'] in [x['SkillId'] for x in m['SkillData']] and s['SkillValueType01']=='Percent' and s['SkillValue01']>0]
            hp=self.stat(m)['LevelHp']*m['HpRatio']/10000;protected=False
            passive=next((p for p in self.data['passives'] if p['Id']==m['PassiveSkillId']),{})
            for itemf in passive.get('Functions',[]):
                f=self.functions.get(itemf['Function'],{})
                if f.get('FunctionType')=='StatHpHeal' and f.get('FunctionValueType')=='Integer':hp=f['FunctionValue']
                if f.get('FunctionType')=='DamageReduction':protected=True
            self.adds.append(dict(id='summon-'+str(len(self.adds)),monster_id=m['Id'],hp=hp,max_hp=hp,spawned=t,protected=protected,skill=skills[0] if skills else None,next_attack=t+3))
            self.log('summon spawned',monster=m['Id'],hp=hp)
        for a in self.living_adds():
            if getattr(self.anomaly,'handles_summons',False):continue
            if a['skill'] and t>=a['next_attack']:
                m=next(m for m in self.data['monsters'] if m['Id']==a['monster_id'])
                self.receive_attack(a['skill'],{},monster=m,source=a['id']);a['next_attack']=t+max(1,(a['skill']['CastingTime']+a['skill']['DelayTime'])/100)
        for item in list(self.pending_shots):
            if t>=item['at']:self.pending_shots.remove(item);self.receive_attack(item['skill'],item['node'])
        self.update_barrier()
        for p,a in self.world.parts.parts.items():
            if a['attack_at'] is not None:self.first_part_deadlines.setdefault(p,a['attack_at'])
        for event in self.world.parts.events[self.part_cursor:]:
            self.events.append(dict(event))
            if event['event']=='part destroyed by squad':
                self.first_breaks.setdefault(event['part'],event['time'])
                if self.bm:
                    for n in self.squad:self.bm.notify('event:part_destroy',t,n)
        self.part_cursor=len(self.world.parts.events)
        super().advance(t,state)
        self.part_deadlines.advance(t)
        if self.aim_controller_override:self.aim_controller=self.aim_controller_override
        if self.normal_by_unit and not self.active and not self.aim_controller_override:self.aim_controller=max(self.normal_by_unit,key=self.normal_by_unit.get)
        if any(p['status']=='active' and p.get('destroyable',True) for p in self.projectiles) and self.bm:
            self.aim_controller=max(self.char_states,key=lambda n:self.char_states[n].fire_rate*(10 if self.char_states[n].weapon_type=='SG' else 1))
        if state is not None:state['encounter_cover']=self.covered

    def attack_targets(self,skill,node):
        if not self.bm:return []
        if '_locked_targets' in node:return [n for n in node['_locked_targets'] if n in self.squad and self.bm.state['hp'].get(n,0)>0]
        names=unit_combat.targetable(self,[n for n in self.squad if self.bm.state['hp'][n]>0])
        if not names:return []
        position=node.get('ECharacterPosition_targetPosition',node.get('ECharacterPosition_positionType','None'))
        if position.startswith('Player'):
            index=int(position.removeprefix('Player'))-1
            slots=list(self.squad)
            return [slots[index]] if 0<=index<len(slots) and slots[index] in names else []
        if 'All' in skill['FireType'] or skill.get('TargetCount')==5:return names
        taunters=[n for n in names if self.protection(n,'taunt')]
        if taunters:return [taunters[0]]
        if skill['PreferTarget']=='HighAttack':return [max(names,key=self.bm._effective_atk)]
        return [self.rng.choice(names)]

    def update_cover(self,t):
        if not self.bm or not self.auto_cover:return
        for a in self.world.attacks.values():
            if a['impacts'] and not a.get('cover_registered'):
                a['cover_registered']=True
                self.cover_threats.append(dict(start=min(a['impacts'])-.25,end=a['cover_until'],skill=self.skills[a['shot']],targets=a['targets'],parts=a['parts']))
        reasons={}
        for threat in self.cover_threats:
            if not threat['start']<=t<threat['end']:continue
            skill=threat['skill']
            if threat['parts'] and any(not self.world.parts.alive(p) for p in threat['parts']):continue
            poison='ultra' in self.key and skill['SkillAniNumber']=='Shot02'
            harmful=poison or any(f['FunctionType']=='Stun' or f['FunctionType'] in ('Damage','CurrentHpRatioDamage') and f['DurationValue']>0 for f in self.hurt_functions(skill))
            for n in threat['targets']:
                if self.cover.get(n,0)<=0 or self.protection(n,'invincible'):continue
                estimate=incoming_hit(self.stat()['LevelAttack']*self.data['monster']['AttackRatio']/10000,self.bm._effective_def(n),skill['SkillValue01'],self.stat()['LevelStatdamageratio'],skill['ShotCount'])
                if harmful or estimate>self.bm.state['hp'][n]*.5:
                    reasons[n]='Avoid poison / debuff' if harmful else 'Cover targeted high damage'
        self.covered.update(reasons)
        for n,reason in reasons.items():
            if n not in self.cover_open:
                window=dict(unit=n,start=t,end=None,reason=reason);self.cover_windows.append(window);self.cover_open[n]=window
        for n in list(self.cover_open):
            if n not in reasons:self.cover_open.pop(n)['end']=t

    def advance_dots(self,t):
        if not self.bm:return
        for item in list(self.dot_ticks):
            if not any(a.effect is item['marker'] and a.expires_at>min(t,item['next']) for a in self.bm._active):
                self.dot_ticks.remove(item);continue
            while item['next']<=t+1e-9 and item['next']<item['end']-1e-9:
                self.dot_damage(item,item['next']);item['next']+=1
            if t>=item['end']:self.dot_ticks.remove(item)

    def dot_damage(self,item,t):
        name=item['target'];hp=self.bm.state['hp']
        if hp.get(name,0)<=0 or self.protection(name,'invincible'):return
        monster=item.get('monster') or self.data['monster'];stat=self.stat(monster)
        boost=sum(v/10000 for ident,(end,v) in self.effects.items() if ident in self.functions and end>t and self.functions[ident]['FunctionType']=='StatAtk')
        attack=unit_combat.enemy_attack(self,stat['LevelAttack']*monster['AttackRatio']/10000*(1+boost))
        amount=self.hurt_function_damage(item['function'],name,attack,stat)
        unit_combat.hurt(self,name,amount)
        self.incoming.append(dict(time=round(t,3),source='Damage over time',shot=item['function']['Id'],target=name,damage=round(amount),blocked_by=None,hp=round(hp[name]),cover=round(self.cover[name])))
        unit_combat.check_defeat(self)

    def apply_hurt_dot(self,function,name,monster):
        duration=function['DurationValue']/100
        marker=self.debuff_effects.setdefault(('dot',function['Id'],name),dict(type='buff',stat='boss_dot',fixed_value=1,name='Boss damage over time '+str(function['Id']),target='self',polarity='harmful',duration=duration,trigger={'condition':[]}))
        self.bm._activate(marker,name,self.time)
        if not any(a.effect is marker and a.expires_at>self.time for a in self.bm._active):return
        self.dot_ticks=[d for d in self.dot_ticks if d['marker'] is not marker]
        # Native TimeSec functions dispatch on application. Subsequent dispatch
        # follows rounded remaining-second buckets; the first half-second
        # crossing is skipped. Refresh starts this schedule again.
        first=duration-(math.floor(duration+.5)-1.5)
        item=dict(marker=marker,function=function,target=name,next=self.time+first,end=self.time+duration,monster=monster)
        self.dot_ticks.append(item)
        self.dot_damage(item,self.time)

    def select_part(self,caster):
        if self.active or any(p['status']=='active' and p.get('destroyable',True) for p in self.projectiles) or self.part_policy=='body':return None
        controlled=self.follows_aim(caster,getattr(self,'aim_controller',caster))
        if not controlled and not (self.key=='anomaly-ultra' and self.world.phase>=2):return None
        pierce=bool(self.bm and self.active_stat(caster,'pierce_enabled')>0)
        preferred=self.anomaly_hook('preferred_part',caster,pierce)
        if preferred and self.world.parts.alive(preferred) and self.part_immune.get(preferred,0)<=self.time:return preferred
        if not controlled:return None
        alive=[n for n,p in self.world.rows.items() if not p['IsMainPart'] and p['IsPartsDamageAble'] and self.world.parts.alive(n) and self.part_immune.get(n,0)<=self.time and self.anomaly_hook('part_targetable',n,self.time) is not False]
        if self.key=='museum-modernia' and self.part_policy=='safe':
            # Preserve one wing to avoid forcing the repeat teleport route.
            wings=[n for n in ('Weapon_01','Weapon_02') if n in alive]
            if len(wings)==1:alive.remove(wings[0])
        urgent=[a for a in self.world.attacks.values() if a.get('parts') and a['impacts'] and (not a['fired'] or self.skills[a['shot']]['CancelType']=='BrokenPartsHurtCount')]
        for a in sorted(urgent,key=lambda a:min(a['impacts'])):
            for p in a['parts']:
                if p in alive:return p
        priority=['Weapon_03','Weapon_01','Weapon_02'] if 'indivilia' in self.key or self.key=='museum-modernia' else ['Head','Weapon_01','Weapon_02','Weapon_03']
        if self.key=='museum-blacksmith':priority=['Arm_Left','Arm_Right','Weapon_01']
        if self.key=='museum-alteisen':priority=['Weapon_06','Weapon_04','Weapon_03','Weapon_05','Weapon_02','Weapon_01']
        return next((p for p in priority+alive if p in alive),None)

    def core_probability(self,caster,fallback):
        if self.active or not self.world.core_enabled:return 0.
        part=self.select_part(caster)
        pierce=bool(self.bm and self.active_stat(caster,'pierce_enabled')>0)
        override=self.anomaly_hook('core_probability',caster,part,pierce)
        if override is not None:return override
        if 'ultra' in self.key:
            cs=getattr(self,'char_states',{}).get(caster);pierce=bool(cs and self.bm and self.active_stat(caster,'pierce_enabled')>0)
            return float(self.world.parts.alive('Weapon_01') and (self.world.phase==2 or pierce) and part in (None,'Weapon_01'))
        if self.key=='anomaly-harvester':return float(not self.world.parts.alive('Head'))
        if self.key=='sr40' or self.key=='museum-alteisen':return 0.
        if self.key=='museum-modernia':return float(part=='Weapon_03' and self.world.parts.alive('Weapon_03'))
        if 'indivilia' in self.key or 'mirror-container' in self.key:return float(part is None)
        if self.key=='museum-crystal-chamber':return 0.
        if part:
            return float(any('core_col' in n for n in self.world.rows[part]['PartsObject']))
        return fallback

    def update_qte_hazards(self):
        q=self.active
        if not q or not q.get('graph') or not q['event'].get('precision_hazards'):return
        graph=q['graph'];graph.advance(self.time)
        dangerous=any(t['kind']=='counter' and t['status']=='active' for t in graph.targets.values())
        for target in graph.targets.values():
            if target['kind']=='break':target['weapons']=['AR','SMG','MG','SR'] if dangerous else None
        q['event']['full_burst_follow']=not dangerous

    def choose_qte_controller(self):
        self.update_qte_hazards()
        return KrakenRuntime.choose_qte_controller(self)

    def qte_weapon_type(self,caster,fallback):
        if self.key not in TIMING_DATA['profiles'] or not self.bm:return fallback
        changed=self.bm.get_weapon_change(caster)
        if not changed:return fallback
        from anomaly_qte_shots import temporary_weapon_parameters
        native=temporary_weapon_parameters(caster,changed.get('weapon_type',fallback))
        return native['WeaponType'] if native else fallback

    def target(self,caster,weapon,element):
        self.update_qte_hazards()
        weapon=self.qte_weapon_type(caster,weapon)
        target=super().target(caster,weapon,element)
        if target is not None:
            key=(self.active['event']['id'],target.get('id',self.active['index']))
            if key!=self.aim_id:self.aim_id=key;self.aim_ready=self.time+self.aim_seconds
            if self.time<self.aim_ready:return None
        return target
    def hold_fire(self,caster,weapon,element):
        if self.waiting:return True
        if self.active:
            self.choose_qte_controller();target=self.target(caster,weapon,element)
            return self.active.get('controller')==caster and target is None
        part=self.select_part(caster)
        if self.key=='anomaly-mirror-container' and part:
            # Avoid consuming a slipper's first hit with a weak follower.
            names=[n for n,cs in getattr(self,'char_states',{}).items() if self.bm.state['hp'].get(n,0)>0 and (self.bm.get_weapon_change(n) or {}).get('weapon_type',cs.weapon_type) in ('SR','RL')]
            shooter=self.anomaly_hook('preferred_part_shooter',names,part,self.time)
            if shooter is None:shooter=max(names,key=lambda n:self.char_states[n].base_atk) if names else getattr(self,'aim_controller',caster)
            return caster!=shooter
        return False

    def damage_target_args(self,args,caster,target):
        if self.key not in TIMING_DATA['profiles']:return args
        return damage_args_for_target(args,caster,target.get('target_kind','ordinary_break'),self,target)

    def resolve_physical_qte(self,caster,element,weapon,hit_type,calculate,args,target):
        from anomaly_qte_shots import qte_shot_contacts
        shot=qte_shot_contacts(self,caster,weapon,hit_type,target,args)
        stats=getattr(self,'qte_physics',None)
        if stats is None:stats=self.qte_physics=dict(shots=0,contacts=0,misses=0,counter_contacts=0,calibrations=[],path_models=[],unresolved_shots=0,unresolved_units=[])
        if shot is None:
            stats['unresolved_shots']+=1
            if caster not in stats['unresolved_units']:stats['unresolved_units'].append(caster)
            return None
        q=self.active;graph=q['graph']
        stats['shots']+=1
        if shot['calibration'] not in stats['calibrations']:stats['calibrations'].append(shot['calibration'])
        if shot.get('path_model') and shot['path_model'] not in stats['path_models']:stats['path_models'].append(shot['path_model'])
        contacts=list(dict.fromkeys(shot['contacts']))
        stats['contacts']+=len(contacts);stats['misses']+=int(not contacts)
        self.last_enemy_target_by_caster[caster]='special_qte'
        results=[]
        for ident in contacts:
            row=graph.targets[ident]
            context=self.damage_target_args(args,caster,row)
            context=dict(context,enemy_def=row.get('def',context['enemy_def']),
                         hit_type=dict(hit_type,is_core=False,core_prob=0,is_part=False))
            result=calculate(**context);results.append(result)
            eligible=not row.get('element') or row['element'] in self.element_access.get(caster,[element])
            damage=result['damage'] if eligible and not self.stopped and not self.blocks('invulnerable') else 0
            damage*=max(0,1+(context.get('buffs',{}).get('qte_dmg_pct',0)+context.get('buffs',{}).get('intercept_dmg_pct',0))/100)
            # The weapon restriction chooses a safe controller. A physical
            # pellet/explosion contact still damages its actual collider.
            if eligible:q['attempted']=True
            q['dealt']+=damage
            if row['kind']=='counter' and damage>0:stats['counter_contacts']+=1
            graph.hit(ident,damage,self.time)
        q['targets']=copy.deepcopy(graph.events)
        if graph.status=='passed':
            q['status']='passed';self.active=None
            self.events.append(dict(time=round(self.time,3),event='QTE passed',id=q['event']['id']))
        result=dict(results[0]) if results else calculate(**args)
        result.update(damage=0,collision_hits=len(contacts),part_hits=0,core_hits=0,body_hits=0)
        return result

    def select_enemy_effect_targets(self,effect,caster,time):
        if self.key not in TIMING_DATA['profiles']:return None
        return select_enemy_effect_targets(self,effect,caster,time)

    def resolve_selected_skill(self,selected,caster,element,weapon,hit_type,calculate,args):
        if hit_type.get('is_split') and len(selected)>1:
            # Native CalculateDamage divides its floating damage term before
            # the final integer conversion. Scaling the skill coefficient
            # preserves per-recipient DEF, buffs and the minimum-damage rule.
            coefficient=hit_type.get('coeff')
            if coefficient is None:coefficient=args['weapon']['damage_coeff']
            hit_type=dict(hit_type,coeff=coefficient/len(selected))
        results=[]
        for entity_id in selected:
            if self.stopped:break
            self.last_enemy_target_by_caster[caster]=entity_id
            if entity_id=='__boss__':
                kind=dict(hit_type,_enemy_target_selected=True)
                results.append(self.resolve(caster,element,weapon,kind,calculate,dict(args,hit_type=kind)))
                continue
            add=next((a for a in self.living_adds() if a['id']==entity_id),None)
            if add is None:continue
            kind=dict(hit_type,is_part=False,is_core=False,core_prob=0)
            target_args=damage_args_for_target(args,caster,'add',self,add)
            result=calculate(**dict(target_args,enemy_def=add.get('defence',0),hit_type=kind))
            amount=result['damage']
            routed=self.anomaly_hook('resolve_hit',add,amount,kind)
            if routed and routed.get('handled'):
                if routed.get('destroyed'):unit_combat.broadcast(self,'event:enemy_death')
            else:
                dealt=min(add['hp'],1 if add.get('protected') and amount>0 else amount)
                add['hp']-=dealt;self.damage_to_adds+=dealt
                if add['hp']<=0:
                    add.update(cleared_at=self.time,clear_reason='squad skill')
                    unit_combat.broadcast(self,'event:enemy_death')
            result.update(damage=0,collision_hits=1,part_hits=0,body_hits=0,core_hits=0)
            results.append(result)
        if not results:
            result=calculate(**args)
            result.update(damage=0,collision_hits=0,part_hits=0,body_hits=0,core_hits=0)
            return result
        result=dict(results[0])
        for key in ('damage','collision_hits','part_hits','body_hits','core_hits'):
            result[key]=sum(row.get(key,0) for row in results)
        return result

    def resolve(self,caster,element,weapon,hit_type,calculate,args):
        normal=hit_type.get('is_normal_atk') or hit_type.get('is_weapon_mode_skill')
        source_profile=self.key in TIMING_DATA['profiles']
        if source_profile and not hit_type.get('_enemy_target_selected'):
            selected=direct_skill_enemy_targets(self,caster,hit_type)
            if selected is not None:return self.resolve_selected_skill(selected,caster,element,weapon,hit_type,calculate,args)
        if source_profile:args=damage_args_for_target(args,caster,'boss',self)
        if source_profile and normal and self.active:
            selected_qte=self.target(caster,weapon,element)
            observed_ray=hit_type.get('qte_ray') or getattr(self,'qte_ray_overrides',{}).get(caster)
            if selected_qte is None and observed_ray and self.active.get('graph'):
                graph=self.active['graph'];graph.advance(self.time)
                selected_qte=next((row for row in graph.targets.values() if row['status']=='active'),None)
            if selected_qte is not None and selected_qte.get('target_kind')=='special_qte':
                result=self.resolve_physical_qte(caster,element,weapon,hit_type,calculate,args,selected_qte)
                if result is not None:return result
        def collision_result(result,part=0,core=0,body=0,count=1):
            if source_profile:result.update(collision_hits=count,part_hits=part,core_hits=core,body_hits=body)
            return result
        if normal and not self.active and self.follows_aim(caster,getattr(self,'aim_controller',caster)):
            extra=self.anomaly_hook('resolve_target',caster,element,weapon,normal)
            if extra is not None:
                target_args=damage_args_for_target(args,caster,'projectile' if extra.get('kind')=='hostile' else 'add',self,extra)
                result=calculate(**dict(target_args,enemy_def=extra['defence'],hit_type=dict(hit_type,core_prob=0,is_core=False,is_part=False)))
                routed=self.anomaly_hook('resolve_hit',extra,result['damage'],hit_type)
                if routed and routed.get('handled'):
                    self.last_enemy_target_by_caster[caster]=extra['id']
                    collision_result(result,count=int(not self.stopped))
                    result['damage']=routed['boss_damage']
                    self.damage+=result['damage']
                    if routed.get('destroyed'):unit_combat.broadcast(self,'event:projectile_destroy' if extra.get('kind')=='hostile' else 'event:enemy_death')
                    return result
        projectile=next((p for p in self.projectiles if p['status']=='active' and p.get('kind')!='hostile'),None)
        if projectile and normal and not self.active and (self.follows_aim(caster, getattr(self,'aim_controller',caster))):
            result=calculate(**dict(args,enemy_def=0,hit_type=dict(hit_type,core_prob=0,is_core=False,is_part=False)))
            if result['damage']>0:projectile['hp']-=1
            if projectile['hp']<=0:
                projectile.update(status='passed',destroyed_at=self.time);self.log('crystal sphere destroyed')
                unit_combat.broadcast(self, 'event:projectile_destroy')
            collision_result(result,count=int(not self.stopped))
            self.last_enemy_target_by_caster[caster]=projectile['id']
            result['damage']=0;return result
        part=self.select_part(caster) if normal else None
        adds=self.living_adds();controlled=self.follows_aim(caster, getattr(self,'aim_controller',caster))
        add=adds[0] if adds and normal and controlled and not self.active and (self.barrier or not part) else None
        if part:args=dict(args,hit_type=dict(args.get('hit_type',hit_type),is_part=True))
        bonus=sum(v/10000 for i,(end,v) in self.effects.items() if i in self.functions and end>self.time and self.functions[i]['FunctionType']=='StatDef')
        multiplier=self.anomaly_hook('defence_multiplier',self.time)
        if multiplier is not None:bonus=multiplier-1
        args=dict(args,enemy_def=(self.enemy_def if self.enemy_def is not None else self.stat()['LevelDefence']*self.data['monster']['DefenceRatio']/10000)*(1+bonus))
        body_defence=args['enemy_def']
        part_defence=self.anomaly_hook('part_defence_multiplier',part) if part else None
        if part_defence is not None:args['enemy_def']*=part_defence
        all_parts=bool(source_profile and not normal and hit_type.get('hits_parts') and not hit_type.get('_enemy_target_selected'))
        if all_parts:args['hit_type']=dict(hit_type,is_part=False,is_core=False,core_prob=0)
        if add:
            args=damage_args_for_target(args,caster,'add',self,add) if self.key in TIMING_DATA['profiles'] else args
            args['enemy_def']=add.get('defence',0);args['hit_type']=dict(hit_type,core_prob=0,is_core=False,is_part=False)
        before=self.damage;was_active=self.active is not None
        part_stat=self.stat() if part else None
        baseline=self.enemy_def;self.enemy_def=args['enemy_def']
        selected_qte=self.target(caster,weapon,element) if normal and self.active else None
        if normal:
            self.last_enemy_target_by_caster[caster]=(add['id'] if add else
                'special_qte' if selected_qte is not None and selected_qte.get('target_kind')=='special_qte' else '__boss__')
        calculated_damage=[]
        def calculate_recorded(**kwargs):
            value=calculate(**kwargs);calculated_damage.append(value['damage']);return value
        try:result=super().resolve(caster,element,weapon,hit_type,calculate_recorded,args)
        finally:self.enemy_def=baseline
        if self.barrier and not add and COUNTER[self.data['monster']['ElementId'][0]] not in self.element_access.get(caster,[element]):
            self.damage=before;result['damage']=0
        amount=result['damage']
        if source_profile:
            # ProcessDamageTargetInfo grants burst charge for a collision even
            # when immunity reduces applied damage to zero. No collider/target
            # remains distinct from an accepted, blocked hit.
            accepted=bool(not self.stopped and (selected_qte is not None or add or not self.blocks('untargetable')))
            core_prob=hit_type.get('core_prob')
            if core_prob is None:core_prob=1 if hit_type.get('is_core') else 0
            core=min(1,max(0,core_prob)) if accepted and not add and selected_qte is None else 0
            collision_result(result,count=int(accepted),part=int(accepted and part is not None and selected_qte is None),core=core,
                             body=(1-core) if accepted and not part and not add and selected_qte is None else 0)
        collisions=()
        if part and not was_active:
            slots=list(getattr(self,'squad',{}));position=slots.index(caster)+1 if caster in slots else 0
            pierce=bool(self.bm and self.active_stat(caster,'pierce_enabled')>0)
            collisions=self.anomaly_hook('player_collision_targets',part,position,pierce) or ()
            if source_profile and accepted:
                for secondary in dict.fromkeys(collisions):
                    if secondary=='Body':result['collision_hits']+=1;result['body_hits']+=1
                    elif secondary!=part and self.world.parts.alive(secondary) and self.part_immune.get(secondary,0)<=self.time and self.anomaly_hook('part_targetable',secondary,self.time) is not False:
                        result['collision_hits']+=1;result['part_hits']+=1
        if add:
            dealt=min(add['hp'],1 if add['protected'] and amount>0 else amount);add['hp']-=dealt;self.damage_to_adds+=dealt
            if add['hp']<=0:add.update(cleared_at=self.time,clear_reason='squad');unit_combat.broadcast(self, 'event:enemy_death')
            self.damage=before;result['damage']=0
        elif part and amount>0 and not was_active:
            was_alive=self.world.parts.alive(part)
            part_damage=self.world.parts.damage(part,amount,self.time)
            self.anomaly_hook('on_part_hit',part,self.time,part_damage,hit_type)
            self.damage_to_parts+=part_damage;self.record_part_aim(part,caster,part_damage)
            # Native SetDamage floors part HP at zero but transfers the full
            # incoming hit to the body and character damage statistics.
            if was_alive and not self.world.parts.alive(part):
                bonus=part_break_damage(part_stat,self.data['monster'],self.world.rows[part],self.world.main_part)
                self.part_break_damage+=bonus;self.damage+=bonus
                self.part_break_events.append(dict(time=self.time,part=part,damage=bonus))
                self.anomaly_hook('on_part_broken',part,self.time,True)
            if 'Body' in collisions:
                body=calculate(**dict(args,enemy_def=body_defence,hit_type=dict(hit_type,is_part=False,is_core=False,core_prob=0)))
                result['damage']+=body['damage'];self.damage+=body['damage'];amount+=body['damage']
                self.log('piercing body collision',unit=caster,part=part,damage=body['damage'])
            for secondary in dict.fromkeys(collisions):
                if secondary in (part,'Body') or not self.world.parts.alive(secondary):continue
                if self.part_immune.get(secondary,0)>self.time or self.anomaly_hook('part_targetable',secondary,self.time) is False:continue
                multiplier=self.anomaly_hook('part_defence_multiplier',secondary)
                secondary_type=dict(hit_type,is_part=True,is_core=False,core_prob=0)
                hit=calculate(**dict(args,enemy_def=body_defence*(1 if multiplier is None else multiplier),hit_type=secondary_type))
                damage=hit['damage']
                if damage<=0:continue
                part_stat=self.stat()
                result['damage']+=damage;self.damage+=damage;amount+=damage
                consumed=self.world.parts.damage(secondary,damage,self.time)
                self.damage_to_parts+=consumed;self.record_part_aim(secondary,caster,consumed)
                self.anomaly_hook('on_part_hit',secondary,self.time,consumed,secondary_type)
                if not self.world.parts.alive(secondary):
                    bonus=part_break_damage(part_stat,self.data['monster'],self.world.rows[secondary],self.world.main_part)
                    self.part_break_damage+=bonus;self.damage+=bonus
                    self.part_break_events.append(dict(time=self.time,part=secondary,damage=bonus))
                    self.anomaly_hook('on_part_broken',secondary,self.time,True)
                self.log('piercing part collision',unit=caster,part=secondary,damage=damage)
        if all_parts and not self.stopped and not self.blocks('untargetable'):
            # InstantAllParts emits body once, then every living damageable
            # subpart whose collider is enabled. Occlusion does not hide Ultra's
            # core from this selector (piercing rays can hit the same collider).
            targets=[p for p,row in self.world.rows.items() if not row['IsMainPart'] and row['IsPartsDamageAble']
                     and self.world.parts.alive(p) and self.part_immune.get(p,0)<=self.time
                     and (self.anomaly_hook('part_targetable',p,self.time) is not False
                          or self.key=='anomaly-ultra' and p=='Weapon_01')]
            blocked=self.blocks('invulnerable') or self.barrier and COUNTER[self.data['monster']['ElementId'][0]] not in self.element_access.get(caster,[element])
            for target_part in targets:
                result['collision_hits']+=1;result['part_hits']+=1
                multiplier=self.anomaly_hook('part_defence_multiplier',target_part)
                part_type=dict(hit_type,is_part=True,is_core=False,core_prob=0)
                hit=calculate(**dict(args,enemy_def=body_defence*(1 if multiplier is None else multiplier),hit_type=part_type))
                damage=0 if blocked else hit['damage']
                if damage<=0:continue
                part_stat=self.stat()
                result['damage']+=damage;self.damage+=damage
                consumed=self.world.parts.damage(target_part,damage,self.time)
                self.damage_to_parts+=consumed
                self.anomaly_hook('on_part_hit',target_part,self.time,consumed,part_type)
                if not self.world.parts.alive(target_part):
                    bonus=part_break_damage(part_stat,self.data['monster'],self.world.rows[target_part],self.world.main_part)
                    self.part_break_damage+=bonus;self.damage+=bonus
                    self.part_break_events.append(dict(time=self.time,part=target_part,damage=bonus))
                    self.anomaly_hook('on_part_broken',target_part,self.time,True)
                self.log('all-parts skill collision',unit=caster,part=target_part,damage=damage)
        wide_skill=not normal and (hit_type.get('effect_target')=='all_enemies' or hit_type.get('is_split')) and not hit_type.get('_enemy_target_selected')
        skill_adds=([a for a in adds if all_monster_targetable(self,a)] if source_profile else adds) if wide_skill else []
        if skill_adds:
            # Distributed skills divide their damage across the actual living targets.
            split=hit_type.get('is_split')
            if split:self.damage-=result['damage'];result['damage']=round(result['damage']/(len(skill_adds)+1));self.damage+=result['damage']
            for a in skill_adds:
                # Each summon owns its DEF. Reusing a zero-DEF calculation here
                # made all-enemy skills ignore the same armour normal shots hit.
                target_args=damage_args_for_target(args,caster,'add',self,a) if self.key in TIMING_DATA['profiles'] else args
                raw=calculate(**dict(target_args,enemy_def=a.get('defence',0),hit_type=dict(hit_type,core_prob=0,is_core=False,is_part=False)))['damage']
                each=raw/(len(skill_adds)+1) if split else raw
                if source_profile:result['collision_hits']+=1
                routed=self.anomaly_hook('resolve_hit',a,each,hit_type)
                if routed and routed.get('handled'):
                    if routed.get('destroyed'):unit_combat.broadcast(self,'event:enemy_death')
                    continue
                dealt=min(a['hp'],1 if a['protected'] and not split and each>0 else each);a['hp']-=dealt;self.damage_to_adds+=dealt
                if a['hp']<=0:a.update(cleared_at=self.time,clear_reason='squad skill');unit_combat.broadcast(self, 'event:enemy_death')
        if normal and not was_active:self.normal_by_unit[caster]=self.normal_by_unit.get(caster,0)+amount
        if self.barrier:self.barrier_damage_by_unit[caster]=self.barrier_damage_by_unit.get(caster,0)+result['damage']
        return result

    def capture_incoming_snapshot(self,monster=None,source=None):
        m=monster or self.data['monster'];stat=self.stat(m)
        boost=sum(v/10000 for i,(end,v) in self.effects.items() if i in self.functions and end>self.time and self.functions[i]['FunctionType']=='StatAtk') if monster is None or self.key not in TIMING_DATA['profiles'] else 0
        base_attack=stat['LevelAttack']*m['AttackRatio']/10000*(1+boost)
        entity_id=source or ('__boss__' if m['Id']==self.data['monster']['Id'] else 'monster-'+str(m['Id']))
        attack=enemy_attack_for_target(self,base_attack,entity_id) if self.key in TIMING_DATA['profiles'] else unit_combat.enemy_attack(self,base_attack)
        return dict(attack=attack,stat_ratio=stat['LevelStatdamageratio'],
                    element_multiplier=self.stage_element_multiplier() if monster is None and self.key.startswith('anomaly-') else 1,
                    element_id=m['ElementId'][0],monster_id=m['Id'],time=self.time)

    def receive_attack(self,skill,node,monster=None,source=None):
        if not self.bm or self.stopped:return
        bm=self.bm;names=[n for n in self.squad if bm.state['hp'][n]>0];m=monster or self.data['monster'];stat=self.stat(m)
        if not names:return
        if skill.get('TargetNothingRatio')==100 and not skill.get('TargetCharacterRatio') and not skill.get('TargetCoverRatio'):return
        traits=self.anomaly_hook('attack_traits',skill) or {}
        hurt=lambda recipient=None:self.hurt_functions(skill,recipient,monster=m)
        snapshot=node.get('_incoming_snapshot') or self.capture_incoming_snapshot(monster,source)
        stat=dict(stat,LevelStatdamageratio=snapshot['stat_ratio'])
        targets=self.attack_targets(skill,node)*max(1,skill['ShotCount'])
        for n in targets:
            if bm.state['hp'].get(n,0)<=0:continue
            recipient=node.get('_target_recipient')
            if recipient is None:
                weights=[skill.get('TargetCharacterRatio',100),skill.get('TargetCoverRatio',0),skill.get('TargetNothingRatio',0)]
                eligible=[kind for kind,weight in zip(('character','cover','nothing'),weights) if weight>0]
                recipient=eligible[0] if len(eligible)==1 else self.rng.choices(('character','cover','nothing'),weights=weights)[0] if sum(weights)>0 else 'character'
            if recipient=='nothing':continue
            hp=bm.state['hp'];defence=bm._effective_def(n)
            attack=snapshot['attack']
            element_multiplier=1
            if self.squad[n].get('element_code')==WEAK_UNITS.get(snapshot['element_id']):
                element_multiplier=snapshot['element_multiplier']
            amount=incoming_hit(attack,defence,skill['SkillValue01'],stat['LevelStatdamageratio'],skill.get('_damage_shots',skill['ShotCount']),element_multiplier)
            # Native GetDamage adds ordinary and code-specific reduction rates,
            # clamps to one after reduction, then DoubleToLong rounds half up.
            amount*=max(0,1+(self.active_stat(n,'received_dmg_pct')+unit_combat.elemental_reduction_percent(self,n,snapshot['element_id']))/100)
            amount=math.floor(max(1,amount)+.5)
            blocked=None;absorbed=0;shields=[a for a in bm._active if a.shield_per_target.get(n,0)>0 and self.time<a.expires_at]
            if self.protection(n,'invincible'):blocked='invincible'
            elif shields and not traits.get('bypass_shield'):
                blocked,absorbed=unit_combat.hit_shield(self,n,amount)
            elif recipient=='cover' and self.cover.get(n,0)<=0:
                blocked='destroyed cover'
            elif not (node.get('_bypass_cover') or traits.get('bypass_cover')) and self.cover.get(n,0)>0 and (recipient=='cover' or n in self.covered or bm.state.get('planned_cover') or self.auto_cover and (amount>hp[n]*.95 or any(f['FunctionType'] in ('Stun','Damage') and f['DurationValue']>0 for f in hurt()))):
                absorbed=min(self.cover[n],math.floor(incoming_hit(attack,unit_combat.cover_defence(self,n),skill['SkillValue01'],stat['LevelStatdamageratio'],skill.get('_damage_shots',skill['ShotCount']))+.5))
                self.cover[n]-=absorbed;blocked='cover';self.covered.add(n)
                for f in hurt('cover'):
                    if f['DurationValue']>0:continue
                    extra=self.hurt_function_damage(f,n,attack,stat,cover=True)
                    taken=min(self.cover[n],extra);self.cover[n]-=taken;absorbed+=taken
            else:
                unit_combat.hurt(self,n,amount)
                for f in hurt('character'):
                    if f['DurationValue']==0:
                        extra=self.hurt_function_damage(f,n,attack,stat)
                        if extra>0:unit_combat.hurt(self,n,extra);amount+=extra
                    if f['FunctionType'] not in ('Damage','CurrentHpRatioDamage'):self.apply_function(f['Id'],n)
                    if f['FunctionType'] not in ('Damage','CurrentHpRatioDamage') or f['DurationValue']<=0:continue
                    self.apply_hurt_dot(f,n,m)
            self.incoming.append(dict(time=round(self.time,3),source=source or NAMES[self.key],shot=skill['Id'],target=n,damage=0 if blocked else round(amount),absorbed=round(absorbed),blocked_by=blocked,hp=round(hp[n]),cover=round(self.cover[n])))
            if hp[n]<=0:self.log('squad member died',unit=n)
            unit_combat.check_defeat(self)
    def stage_element_multiplier(self):
        passive=next((p for p in self.data['passives'] if p['Id']==self.stage()['TargetPassiveSkillId']),{})
        values=[self.functions[e['Function']]['FunctionValue'] for e in passive.get('Functions',[]) if e['Function'] in self.functions and self.functions[e['Function']]['FunctionType']=='IncElementDmg']
        return 1+sum(values)/10000

    def hurt_function_damage(self,function,name,attack,stat,cover=False):
        kind=function['FunctionType'];value=function['FunctionValue']
        if kind=='CurrentHpRatioDamage':return math.floor(max(0,(self.cover[name] if cover else self.bm.state['hp'][name])*value/10000)+.5)
        if kind=='Damage':
            defence=unit_combat.cover_defence(self,name) if cover else self.bm._effective_def(name)
            amount=incoming_hit(attack,defence,value,stat['LevelStatdamageratio'])
            return math.floor((amount if cover else amount*max(0,1+self.active_stat(name,'received_dmg_pct')/100))+.5)
        return 0

    def hurt_functions(self,skill,recipient=None,*,monster=None):
        monsters=[monster] if monster else self.data['monsters']
        row=next((s for m in monsters for s in m['SkillData'] if s['SkillId']==skill['Id']),{})
        functions=[self.functions[i] for i in row.get('HurtFunctionIdSkill',[]) if i]
        if recipient is not None:
            # Confirmed through the original IsValidStatusCondition routine:
            # value 1 requires a character entity; value 0 requires cover.
            functions=[f for f in functions if f.get('StatusTriggerType')!='IsCover' or bool(f['StatusTriggerValue'])==(recipient=='character')]
        return functions

    def report(self):
        report=super().report();family=self.key.split('-',1)[-1] if self.key.startswith(('museum-','anomaly-')) else self.key
        objectives=[]
        for n,p in self.world.parts.parts.items():
            row=self.world.rows[n]
            if row['IsMainPart'] or not row['IsPartsDamageAble']:continue
            deadline=self.first_part_deadlines.get(n);broken=self.first_breaks.get(n)
            objectives.append(dict(id=n,part=PART_LABELS.get(family,{}).get(n,n.replace('_',' ')),hp=p['max_hp'],remaining_hp=p['hp'],deadline=deadline,destroyed_at=broken,
                status='passed' if broken is not None and (deadline is None or broken<=deadline) else 'failed' if deadline is not None and self.time>=deadline else 'pending'))
        report.update(model='Automatic '+NAMES[self.key]+' · modeled fight',model_id='raid-boss-runtime-v1',
            part_labels=PART_LABELS.get(family,{}),
            full_fight_verified=False,calibration_status='approximate',source_sha256=DATA['source_sha256'],phase=self.world.phase,tree_status=self.tree.status,phase_cinematics=list(self.phase_cinematics),
            qte_required=bool(self.data['qtes'] or any(s['BreakObject'] for s in self.skills.values())),critical_parts=objectives,
            critical_deadlines=self.part_deadlines.report(self.time),critical_deadlines_supported=any(s['ControlParts'] and s['CancelType'].startswith('BrokenParts') for s in self.skills.values()),
            incoming=self.incoming,parts=copy.deepcopy(self.world.parts.parts),choices=self.choices,cover_windows=self.cover_windows,projectiles=[{k:v for k,v in p.items() if k not in ('skill','node')} for p in self.projectiles],summons=[{k:v for k,v in a.items() if k!='skill'} for a in self.adds],
            barrier_windows=self.barrier_windows,barrier_damage_by_unit=self.barrier_damage_by_unit,damage_to_parts=round(self.damage_to_parts),damage_to_adds=round(self.damage_to_adds),
            part_break_damage=round(self.part_break_damage),part_break_events=copy.deepcopy(self.part_break_events),boss_hp_damage=round(self.damage),
            stop_reason=self.stop_reason,survival='failed' if self.stop_reason else 'survived modeled attacks',
            policy=dict(target=self.part_policy,attack_choice=self.choice_policy,auto_cover=self.auto_cover),
            assumptions=list(ASSUMPTIONS)+(['Unmodeled recovered effect types: '+', '.join(sorted(self.unhandled))] if self.unhandled else []))
        report.update(unit_combat.report(self))
        detail=self.anomaly_hook('report')
        if detail:
            report['boss_mechanics']=detail
            report['part_labels']=detail.get('part_labels',report['part_labels'])
        report['damage_to_projectiles']=round(getattr(self,'damage_to_projectiles',0))
        report['assumptions']+=getattr(self.anomaly,'assumptions',[])
        if self.projectile_mechanics:
            report['projectile_mechanics']=self.projectile_mechanics.report()
            report['assumptions']+=self.projectile_mechanics.assumptions
        if self.key in TIMING_DATA['profiles']:
            report['model_id']='anomaly-source-runtime-v7'
            report['static_record_verification']=TIMING_DATA.get('static_record_verification')
            report['qte_physics']=getattr(self,'qte_physics',None)
            report['unresolved_range_selections']=getattr(self,'range_targeting_unresolved',{})
            report['assumptions']=[a for a in report['assumptions'] if not a.startswith(('Animation loops use table casting time.','Crystal sphere uses a 300-hit check','Ordinary projectile interception and summon travel are approximate.','QTE aim assumes'))]
            report['assumptions'] += [
                'Attack markers, loop repetition, marker-specific slots and movement points use the installed assets. Boss movement integrates native speed and acceleration at intervals no larger than 0.02 seconds; combat-zone constructor defaults are used.',
                ('Phase cinematics pause battle time and firing. This phase asset stops normal combat ticks, so buffs, damage-over-time, cooldowns, reloads and projectiles also freeze until completion.' if phase_stops_spot_tick(self.key) else
                 'The phase timeline consumes ordinary battle time; effects, cooldowns, projectiles and the squad continue on the normal clock while the boss waits for its animation to finish. No extra virtual time or timer rebase is applied. Continued phase firing is directly verified for Ultra and Mirror Container; Harvester\'s authored 1/60-second transition completed within one measured battle tick.'),
                'Boss poison applies an immediate tick and uses native rounded-duration timing for subsequent ticks and refreshes. Cover-specific hurt effects and boss debuff immunity are modeled.',
                'Special-QTE shots use authored world boxes, native center-pellet sampling and impact-centered splash. Installed base and unambiguous replacement weapon geometry are available. The default reticle projection and origin use a client calibration; dynamic camera/stance motion, ambiguous weapon modes and incidental QTE contacts by body-aimed followers still require verification. Projectile paths currently use straight rays. Controller selection retains the precise-weapon policy and 0.15-second reaction time.',
                'Full-fight equivalence to the game client remains unverified. Projectile and summon movement still depend on the geometry assumptions listed for this boss.'
            ]
            if report['unresolved_range_selections']:
                report['assumptions'].append('Some area-skill target selections lack the live aim ray and animated collider geometry required by the native sphere/capsule cast. They currently retain eligible targets; unresolved selections are counted in this report.')
        return report
