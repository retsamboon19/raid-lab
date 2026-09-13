"""Variant-specific raid AI with finite parts, interruptions and incoming attacks.

Recovered records drive branch decisions. Physical geometry and animation travel
are approximations and remain explicit in every report.
"""
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
 'Incoming damage uses enemy ATK and skill percentage, effective DEF and the level damage ratio. Finite cover, shields, healing, taunt, stun and invulnerability affect the run. The first death stops scoring conservatively.',
 'Ordinary projectile interception and summon travel are approximate. Museum weekly buffs are not applied. Modeled survival is not a verified in-game clear.',
 'Crystal sphere uses a 300-hit check and a modeled ten-second flight window; exact Museum travel needs client validation. Poison ticks use one-second intervals. Boss debuff immunity, collision-based cover bypass and overlapping pierce targets are not fully reproduced.',
]

class RaidWorld(PartWorld):
    def __init__(self,runtime):
        self.runtime=runtime;self.rows={part_name(p['PartsType']):p for p in runtime.data['parts']}
        self.main_part=next((p for p in self.rows.values() if p.get('IsMainPart')),None)
        super().__init__({n:part_max_hp(runtime.stat(),runtime.data['monster'],p,self.main_part) for n,p in self.rows.items()})
        self.position=254;self.direction=254;self.phase=1;self.attacks={};self.core_enabled=True;self.speed=1.
        if 'indivilia' in runtime.key:self.position=154 if runtime.key.startswith('anomaly') else 153
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
            value=node['Int32mValue'];p=self.parts.parts.get(node['PartsTypemPartsType'])
            if node.get('BooleanisUsingMianHp'):
                fraction=max(0,1-r.damage/(r.stat()['LevelHp']*r.data['monster']['HpRatio']/10000))*100
                result=fraction<=value
            elif value in (0,1):result=not self.parts.alive(node['PartsTypemPartsType'])
            else:result=(p['hp']/p['max_hp']*100 if p else 0)<=value
            return SUCCESS if result==node['BooleanmLower'] else FAILURE
        if kind=='CheckPhase':
            typ=node['PhaseCheckType_type'];value=node['Single_phaseValue']
            if typ=='BerserkStep':result=r.stage()['Step']>=value
            elif typ=='HpRatio':result=100*(1-r.damage/r.stat()['LevelHp'])<=value
            else:raise UnsupportedBossAction(typ)
            return SUCCESS if result else FAILURE
        if kind=='CheckMonsterCount':return SUCCESS if node['Int32min']<=1+len(r.living_adds())<=node['Int32max'] else FAILURE
        if kind.startswith('BrokenParts'):
            for p in node['List`1_partsList']:
                if self.parts.alive(p):self.parts.self_destruct(p,time)
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
                state['repaired']=True
            return SUCCESS
        if kind=='isPhaseAction':
            if not state.get('applied'):
                self.phase=2;state['applied']=True;r.log('boss phase changed',phase=2)
            return FAILURE if time-state['started']>=1 else RUNNING
        if kind=='ColliderControlNode':self.core_enabled=node['Boolean_on'];return SUCCESS
        if kind=='IsInPoint':return SUCCESS if self.position==node['Int32_point'] else FAILURE
        if kind=='SetDirection':self.direction=node.get('Int32mPointIndex',self.direction);return SUCCESS
        if kind.startswith(('MoveTo','TeleportTo','JumpTo')):
            duration=node.get('Single_teleportTime',node.get('SinglemDuration',1.))
            if time-state['started']<duration:return RUNNING
            dest=node.get('Int32_pointIndex',node.get('Int32mPointIndex',self.direction))
            if node.get('PositionCheckTypePositionCheckType')=='PointRange':dest=r.rng.randint(node['Int32_pointRangeMin'],node['Int32_pointRangeMax'])
            self.position=dest;return RUNNING if kind=='MoveTo' else SUCCESS
        if kind=='IsTargetAlive':
            names=list(getattr(r,'squad',{}));index=int(node['ECharacterPosition_targetPosition'][-1])-1
            return SUCCESS if not r.bm or index<len(names) and r.bm.state['hp'][names[index]]>0 else FAILURE
        if kind=='IsExistObstacle':return FAILURE # No static map obstacles in this approximation.
        if kind=='SetSpeedRate':self.speed=max(.01,node['SinglemCustomSpeedRate']);return SUCCESS
        if kind in ('EmptySuccess','SetMoveType','StopMove','StopMoveSuccess','TurnAround','StartAttack','EndAttack','AttackRelease'):return SUCCESS
        if kind=='QuickTimeEvent':return r.special_qte(node,time,state)
        if kind not in ('Attack','AttackV2','AttackV3','TimelineSkill','BreakCol'):return super().action(node,time,state)
        shots=node.get('List`1_aniNumberTypes',[node.get('SkillAniNumberTypemSkillAniNumber')])
        index=state.get('shot_index',0);shot=int(shots[index].split('_')[-1]);skill=r.skills[shot]
        if 'impacts' not in state:
            cast=skill['CastingTime']/100;timeline=r.data['timelines'].get(str(shot)) if kind=='TimelineSkill' else None
            if timeline:
                markers=timeline['markers'];starts=[m['time'] for m in markers if m['type'].endswith('/LoopStart')];ends=[m['time'] for m in markers if m['type'].endswith('/LoopEnd')]
                shift=cast-(ends[0]-starts[0]) if starts and ends else 0.
                impacts=[time+m['time']+(shift if ends and m['time']>=ends[0] else 0) for m in markers if m['type'].endswith('/Attack')]
                impacts=impacts or [time+cast];end=max(time+timeline['duration']+shift,max(impacts))
                interrupt=time+(starts[0] if starts else 0)
            else:impacts=[time+cast];end=time+(cast+skill['DelayTime']/100)/self.speed;interrupt=time
            state.update(impacts=impacts,end=end,fired=0,shot=shot,interrupt=interrupt,parts=[part_name(p) for p in skill['ControlParts']],node=node)
            state['targets']=r.attack_targets(skill,node)
            state['cover_until']=max(impacts)+max(0,skill['ShotCount']-1)*skill['DelayTime']/100+.1
            state['node']=dict(node,_locked_targets=state['targets'])
            self.attacks[node['ID']]=state
            r.update_cover(time)
            r.apply_skill_functions(skill,'UseFunctionIdSkill')
            for p in state['parts']:
                if self.parts.alive(p):self.parts.parts[p]['attack_at']=min(impacts)
            if skill['CancelType'].startswith('BrokenParts'):
                r.part_deadlines.register(self.parts,state['parts'],min(impacts),shot)
            r.log('boss attack started',shot=shot,impact=round(min(impacts),3),node=node['ID'])
        parts=state['parts'];cancel=skill['CancelType'].startswith('BrokenParts') and parts and any(not self.parts.alive(p) for p in parts)
        if cancel and not state['fired']:
            r.log('part destruction cancelled attack',shot=shot,parts=parts);self.attacks.pop(node['ID'],None);return FAILURE if node.get('BooleanFailueCheck') else SUCCESS
        if skill['BreakObject'] and time>=state['interrupt'] and 'qte' not in state:
            state['qte']=r.ordinary_qte(skill,time,max(.02,min(state['impacts'])-time))
        if state.get('qte') and r.states[state['qte']]['status']=='passed':
            self.attacks.pop(node['ID'],None);r.log('interruption cancelled attack',shot=shot)
            return FAILURE if node.get('BooleanFailueCheck') else SUCCESS
        while state['fired']<len(state['impacts']) and time>=state['impacts'][state['fired']]-1e-9:
            state['fired']+=1;r.perform_skill(skill,state['node'])
        if time>=state['end']-1e-9:
            self.attacks.pop(node['ID'],None)
            if index+1<len(shots):
                state.clear();state.update(started=time,shot_index=index+1);return RUNNING
            return SUCCESS
        return RUNNING

class RaidBossRuntime(EncounterRuntime):
    active_stat=KrakenRuntime.active_stat
    protection=KrakenRuntime.protection
    choose_qte_controller=KrakenRuntime.choose_qte_controller

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

    def log(self,event,**details):self.events.append(dict(time=round(self.time,3),event=event,**details))
    def stage(self):
        return max((s for s in self.stages if self.damage>=s['ConditionValueMin']),key=lambda s:s['ConditionValueMin'])
    def stat(self,monster=None):return self.stat_rows[((monster or self.data['monster'])['StatenhanceId'],self.stage()['MonsterStageLv'])]
    def bind(self,bm,squad,char_states):
        self.bm=bm;self.squad={c['name']:c for c in squad};self.char_states=char_states
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
        if 'qte' not in state:
            group=state['groups'][state['group']];rows=[q for q in self.data['qte_targets'] if q['GroupId']==group]
            linked={i for q in rows for i in q['Chain']};precise=any(q['ColType']=='Counter' for q in rows)
            targets=[dict(id=q['ColIndex'],kind='break' if q['ColType']=='Break' else 'counter',
                hp=self.stat()['LevelBrokenHp']*q['HpRatio']/10000,duration=q['TimeLimit']/100,
                first=q['FirstCol'] or q['ColIndex'] not in linked,delay=(record['FirstColAnimTime'] if q['ColIndex'] not in linked else q['DelayTime'])/100,
                chain=q['Chain'],element=COUNTER[record['ElementId']] if self.barrier and record['ElementId'] in COUNTER else None,
                weapons=['AR','SMG','MG','SR'] if precise else None) for q in rows]
            state['qte']=self.add_event(dict(kind='qte',start=time,duration=record['TimeLimit']/100,graph=targets,controller='auto',full_burst_follow=not precise,on_fail='downtime',failure_downtime=0))
            self.log('special interruption',pattern=record['Id'],group=group)
        status=self.states[state['qte']]['status']
        if status=='passed':
            state['group']+=1
            if state['group']<len(state['groups']):state.pop('qte');return RUNNING
            return FAILURE # Client AI uses success for the failed-check attack branch.
        if status in ('failed','unknown'):return SUCCESS
        return RUNNING

    def apply_skill_functions(self,skill,field,target=None):
        mapping=next((s for m in self.data['monsters'] for s in m['SkillData'] if s['SkillId']==skill['Id']),None)
        for i in (mapping or {}).get(field,[]):self.apply_function(i,target)

    def apply_function(self,ident,target=None,part=None):
        if not ident:return
        f=self.functions[ident];kind=f['FunctionType'];value=f['FunctionValue'];duration=f['DurationValue']/100
        if f['TimingTriggerType'] not in ('None','OnStart'):return
        if kind=='TargetPartsId':
            row=next((p for p in self.data['parts'] if p['Id']==value),None)
            # Shared model functions may reference the base model's part IDs.
            if row is None:row=next((p for p in self.data['parts'] if p['Id']%100==value%100),None)
            if row:part=part_name(row['PartsType'])
        elif kind=='ImmuneOtherElement':
            self.effects['barrier']=(self.time+duration,value)
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
    def perform_skill(self,skill,node):
        if skill['FireType']=='Calling':
            for row in self.data['calls']:
                if row['GroupId']==skill['SkillValue01']:self.pending.append(dict(at=self.time+row['SpawnTime'],record=row))
        elif self.key=='museum-crystal-chamber' and skill['SkillAniNumber'] in ('Shot06','Shot15'):
            self.projectiles.append(dict(id='sphere-'+str(len(self.projectiles)),hp=300,max_hp=300,spawned=self.time,deadline=self.time+10,skill=skill,node=node,status='active'))
            self.log('crystal sphere launched',hits_required=300,deadline=round(self.time+10,3))
        elif skill['SkillValueType01']=='Percent' and skill['SkillValue01']>0:
            if skill['ShotTiming']=='Sequence' and skill['ShotCount']>1:
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
        for projectile in self.projectiles:
            if projectile['status']=='active' and t>=projectile['deadline']:
                projectile['status']='failed';self.receive_attack(projectile['skill'],dict(projectile['node'],_bypass_cover=True))
                self.log('crystal sphere hit squad',remaining_hits=projectile['hp'])
        self.advance_dots(t)
        for item in list(self.pending):
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
            if a['skill'] and t>=a['next_attack']:
                m=next(m for m in self.data['monsters'] if m['Id']==a['monster_id'])
                self.receive_attack(a['skill'],{},monster=m,source=a['id']);a['next_attack']=t+max(1,(a['skill']['CastingTime']+a['skill']['DelayTime'])/100)
        for item in list(self.pending_shots):
            if t>=item['at']:self.pending_shots.remove(item);self.receive_attack(item['skill'],item['node'])
        was=self.barrier;self.barrier=self.effects.get('barrier',(0,0))[0]>t
        if was!=self.barrier:
            if self.barrier:self.barrier_windows.append(dict(start=t,end=None))
            elif self.barrier_windows:self.barrier_windows[-1]['end']=t
            self.log('element barrier enabled' if self.barrier else 'element barrier removed')
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
        if any(p['status']=='active' for p in self.projectiles) and self.bm:
            self.aim_controller=max(self.char_states,key=lambda n:self.char_states[n].fire_rate*(10 if self.char_states[n].weapon_type=='SG' else 1))
        if state is not None:state['encounter_cover']=self.covered

    def attack_targets(self,skill,node):
        if not self.bm:return []
        if '_locked_targets' in node:return node['_locked_targets']
        names=[n for n in self.squad if self.bm.state['hp'][n]>0]
        if not names:return []
        position=node.get('ECharacterPosition_targetPosition',node.get('ECharacterPosition_positionType','None'))
        if position.startswith('Player'):return [list(self.squad)[int(position[-1])-1]]
        if 'All' in skill['FireType'] or skill.get('TargetCount')==5:return names
        taunters=[n for n in names if self.protection(n,'taunt')]
        if taunters:return [taunters[0]]
        if skill['PreferTarget']=='HighAttack':return [max(names,key=self.bm._effective_atk)]
        return [self.rng.choice(names)]

    def update_cover(self,t):
        if not self.bm or not self.auto_cover:return
        for a in self.world.attacks.values():
            if not a.get('cover_registered'):
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
            if t<item['next'] or t>item['end']:continue
            marker=item['marker'];name=item['target']
            if not any(a.effect is marker and a.expires_at>t for a in self.bm._active):item['end']=0;continue
            f=item['function'];hp=self.bm.state['hp'];stat=self.stat()
            amount=hp[name]*f['FunctionValue']/10000 if f['FunctionType']=='CurrentHpRatioDamage' else incoming_hit(stat['LevelAttack'],self.bm._effective_def(name),f['FunctionValue'],stat['LevelStatdamageratio'])
            item['next']+=1
            if self.protection(name,'invincible'):continue
            amount*=max(0,1+self.active_stat(name,'received_dmg_pct')/100)
            hp[name]=max(1 if self.protection(name,'undying') else 0,hp[name]-amount);self.bm.sync_hp(name)
            self.incoming.append(dict(time=round(t,3),source='Damage over time',shot=f['Id'],target=name,damage=round(amount),blocked_by=None,hp=round(hp[name]),cover=round(self.cover[name])))
            if hp[name]<=0:self.stop_reason='First squad death from damage over time: '+name;self.stopped=True;break

    def select_part(self,caster):
        if self.active or any(p['status']=='active' for p in self.projectiles) or self.part_policy=='body':return None
        if not (self.follows_aim(caster, getattr(self,'aim_controller',caster))):return None
        alive=[n for n,p in self.world.rows.items() if not p['IsMainPart'] and p['IsPartsDamageAble'] and self.world.parts.alive(n) and self.part_immune.get(n,0)<=self.time]
        if self.key=='museum-modernia' and self.part_policy=='safe':
            # Preserve one wing to avoid forcing the repeat teleport route.
            wings=[n for n in ('Weapon_01','Weapon_02') if n in alive]
            if len(wings)==1:alive.remove(wings[0])
        urgent=[a for a in self.world.attacks.values() if a.get('parts') and not a['fired']]
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

    def target(self,caster,weapon,element):
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
            names=[n for n,cs in getattr(self,'char_states',{}).items() if (self.bm.get_weapon_change(n) or {}).get('weapon_type',cs.weapon_type) in ('SR','RL')]
            shooter=max(names,key=lambda n:self.char_states[n].base_atk) if names else getattr(self,'aim_controller',caster)
            return caster!=shooter
        return False

    def resolve(self,caster,element,weapon,hit_type,calculate,args):
        normal=hit_type.get('is_normal_atk') or hit_type.get('is_weapon_mode_skill')
        projectile=next((p for p in self.projectiles if p['status']=='active'),None)
        if projectile and normal and not self.active and (self.follows_aim(caster, getattr(self,'aim_controller',caster))):
            result=calculate(**dict(args,enemy_def=0,hit_type=dict(hit_type,core_prob=0,is_core=False,is_part=False)))
            if result['damage']>0:projectile['hp']-=1
            if projectile['hp']<=0:projectile.update(status='passed',destroyed_at=self.time);self.log('crystal sphere destroyed')
            result['damage']=0;return result
        part=self.select_part(caster) if normal else None
        adds=self.living_adds();controlled=self.follows_aim(caster, getattr(self,'aim_controller',caster))
        add=adds[0] if adds and normal and controlled and not self.active and (self.barrier or not part) else None
        if part:args=dict(args,hit_type=dict(args.get('hit_type',hit_type),is_part=True))
        bonus=sum(v/10000 for i,(end,v) in self.effects.items() if i in self.functions and end>self.time and self.functions[i]['FunctionType']=='StatDef')
        if self.key=='anomaly-mirror-container' and self.world.phase==2:
            bonus=.9*sum(self.world.parts.alive('Weapon_'+str(i).zfill(2)) for i in range(7,11))
        args=dict(args,enemy_def=(self.enemy_def if self.enemy_def is not None else self.stat()['LevelDefence']*self.data['monster']['DefenceRatio']/10000)*(1+bonus))
        if add:args['enemy_def']=0;args['hit_type']=dict(hit_type,core_prob=0,is_core=False,is_part=False)
        before=self.damage;was_active=self.active is not None
        part_stat=self.stat() if part else None
        baseline=self.enemy_def;self.enemy_def=args['enemy_def']
        try:result=super().resolve(caster,element,weapon,hit_type,calculate,args)
        finally:self.enemy_def=baseline
        if self.barrier and not add and COUNTER[self.data['monster']['ElementId'][0]] not in self.element_access.get(caster,[element]):
            self.damage=before;result['damage']=0
        amount=result['damage']
        if add:
            dealt=min(add['hp'],1 if add['protected'] and amount>0 else amount);add['hp']-=dealt;self.damage_to_adds+=dealt
            if add['hp']<=0:add.update(cleared_at=self.time,clear_reason='squad')
            self.damage=before;result['damage']=0
        elif part and amount>0 and not was_active:
            was_alive=self.world.parts.alive(part)
            part_damage=self.world.parts.damage(part,amount,self.time)
            self.damage_to_parts+=part_damage;self.record_part_aim(part,caster,part_damage)
            # Native SetDamage floors part HP at zero but transfers the full
            # incoming hit to the body and character damage statistics.
            if was_alive and not self.world.parts.alive(part):
                bonus=part_break_damage(part_stat,self.data['monster'],self.world.rows[part],self.world.main_part)
                self.part_break_damage+=bonus;self.damage+=bonus
                self.part_break_events.append(dict(time=self.time,part=part,damage=bonus))
            if self.key=='anomaly-mirror-container':self.part_immune[part]=self.time+5
        if adds and not normal and (hit_type.get('effect_target')=='all_enemies' or hit_type.get('is_split')) and not was_active:
            # Distributed skills divide their damage across the actual living targets.
            raw=calculate(**dict(args,enemy_def=0,hit_type=dict(hit_type,core_prob=0,is_core=False,is_part=False)))['damage']
            split=hit_type.get('is_split');each=raw/(len(adds)+1) if split else raw
            if split:self.damage-=result['damage'];result['damage']=round(result['damage']/(len(adds)+1));self.damage+=result['damage']
            for a in adds:
                dealt=min(a['hp'],1 if a['protected'] and not split and each>0 else each);a['hp']-=dealt;self.damage_to_adds+=dealt
                if a['hp']<=0:a.update(cleared_at=self.time,clear_reason='squad skill')
        if normal and not was_active:self.normal_by_unit[caster]=self.normal_by_unit.get(caster,0)+amount
        if self.barrier:self.barrier_damage_by_unit[caster]=self.barrier_damage_by_unit.get(caster,0)+result['damage']
        return result

    def receive_attack(self,skill,node,monster=None,source=None):
        if not self.bm or self.stopped:return
        bm=self.bm;names=[n for n in self.squad if bm.state['hp'][n]>0];m=monster or self.data['monster'];stat=self.stat(m)
        if not names:return
        targets=self.attack_targets(skill,node)*max(1,skill['ShotCount'])
        for n in targets:
            hp=bm.state['hp'];defence=bm._effective_def(n)
            boost=sum(v/10000 for i,(end,v) in self.effects.items() if i in self.functions and end>self.time and self.functions[i]['FunctionType']=='StatAtk')
            attack=stat['LevelAttack']*m['AttackRatio']/10000*(1+boost)
            amount=incoming_hit(attack,defence,skill['SkillValue01'],stat['LevelStatdamageratio'],skill.get('_damage_shots',skill['ShotCount']))
            if self.key.startswith('anomaly-') and self.squad[n].get('element_code')==WEAK_UNITS.get(m['ElementId'][0]):amount*=3 if self.stage()['Step']<=3 else 4 if self.stage()['Step']<=6 else 5
            amount*=max(0,1+self.active_stat(n,'received_dmg_pct')/100)
            blocked=None;absorbed=0;shields=[a for a in bm._active if a.shield_per_target.get(n,0)>0 and self.time<a.expires_at]
            if self.protection(n,'invincible'):blocked='invincible'
            elif shields:
                a=shields[0];absorbed=min(amount,a.shield_per_target[n]);a.shield_per_target[n]-=absorbed
                if a.effect.get('stat')=='shared_shield_from_max_hp_pct':
                    for name in a.shield_per_target:a.shield_per_target[name]=a.shield_per_target[n]
                blocked='shield';bm._invalidate_buffs_cache()
            elif not node.get('_bypass_cover') and self.cover.get(n,0)>0 and (n in self.covered or bm.state.get('planned_cover') or self.auto_cover and (amount>hp[n]*.95 or any(f['FunctionType'] in ('Stun','Damage') and f['DurationValue']>0 for f in self.hurt_functions(skill)))):
                absorbed=min(self.cover[n],incoming_hit(attack,self.cover_def[n],skill['SkillValue01'],stat['LevelStatdamageratio'],skill.get('_damage_shots',skill['ShotCount'])));self.cover[n]-=absorbed;blocked='cover';self.covered.add(n)
            else:
                for f in self.hurt_functions(skill):
                    if f['FunctionType']=='CurrentHpRatioDamage' and f['DurationValue']==0:amount+=hp[n]*f['FunctionValue']/10000
                hp[n]=max(1 if self.protection(n,'undying') else 0,hp[n]-amount);bm.sync_hp(n);bm.notify('received_hit',self.time,n)
                self.apply_skill_functions(skill,'HurtFunctionIdSkill',n)
                for f in self.hurt_functions(skill):
                    if f['FunctionType'] not in ('Damage','CurrentHpRatioDamage') or f['DurationValue']<=0:continue
                    marker=self.debuff_effects.setdefault(('dot',f['Id'],n),dict(type='buff',stat='boss_dot',fixed_value=1,name='Boss damage over time '+str(f['Id']),target='self',polarity='harmful',duration=f['DurationValue']/100,trigger={'condition':[]}))
                    bm._activate(marker,n,self.time)
                    self.dot_ticks=[d for d in self.dot_ticks if d['marker'] is not marker]
                    self.dot_ticks.append(dict(marker=marker,function=f,target=n,next=self.time+1,end=self.time+f['DurationValue']/100))
            self.incoming.append(dict(time=round(self.time,3),source=source or NAMES[self.key],shot=skill['Id'],target=n,damage=0 if blocked else round(amount),absorbed=round(absorbed),blocked_by=blocked,hp=round(hp[n]),cover=round(self.cover[n])))
            if hp[n]<=0:self.stop_reason='First squad death: '+n;self.stopped=True;self.log('squad member died',unit=n);break
    def hurt_functions(self,skill):
        row=next((s for m in self.data['monsters'] for s in m['SkillData'] if s['SkillId']==skill['Id']),{})
        return [self.functions[i] for i in row.get('HurtFunctionIdSkill',[]) if i]

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
            full_fight_verified=False,calibration_status='approximate',source_sha256=DATA['source_sha256'],phase=self.world.phase,tree_status=self.tree.status,
            qte_required=bool(self.data['qtes'] or any(s['BreakObject'] for s in self.skills.values())),critical_parts=objectives,
            critical_deadlines=self.part_deadlines.report(self.time),critical_deadlines_supported=any(s['ControlParts'] and s['CancelType'].startswith('BrokenParts') for s in self.skills.values()),
            incoming=self.incoming,parts=copy.deepcopy(self.world.parts.parts),choices=self.choices,cover_windows=self.cover_windows,projectiles=[{k:v for k,v in p.items() if k not in ('skill','node')} for p in self.projectiles],summons=[{k:v for k,v in a.items() if k!='skill'} for a in self.adds],
            barrier_windows=self.barrier_windows,barrier_damage_by_unit=self.barrier_damage_by_unit,damage_to_parts=round(self.damage_to_parts),damage_to_adds=round(self.damage_to_adds),
            part_break_damage=round(self.part_break_damage),part_break_events=copy.deepcopy(self.part_break_events),boss_hp_damage=round(self.damage),
            stop_reason=self.stop_reason,survival='failed' if self.stop_reason else 'survived modeled attacks',
            policy=dict(target=self.part_policy,attack_choice=self.choice_policy,auto_cover=self.auto_cover),
            assumptions=list(ASSUMPTIONS)+(['Unmodeled recovered effect types: '+', '.join(sorted(self.unhandled))] if self.unhandled else []))
        return report
