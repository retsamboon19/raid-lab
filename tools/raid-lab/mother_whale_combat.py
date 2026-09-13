"""Mother Whale's Museum AI, finite core and summons, driven by actual hits.

Physical approximations are explicit; no observed score or roster names are used.
"""
import copy
import json
import random
import re
from pathlib import Path
from boss_behavior import BehaviorTree, RUNNING, SUCCESS, FAILURE
from boss_world import PartWorld
from boss_parts import part_max_hp, part_break_damage
from mechanics import EncounterRuntime
from enemy_damage import incoming_hit
from kraken_combat import KrakenRuntime

DATA=json.loads((Path(__file__).parent/'mother-whale-combat-data.json').read_text(encoding='utf-8'))
SKILLS={s['Id']:s for s in DATA['skills']}
MONSTERS={m['Id']:m for m in DATA['monsters']}
STATS={(s['GroupId'],s['Lv']):s for s in DATA['stats']}
CORE='Weapon_09'
ASSUMPTIONS=[
    'Outside Full Burst, only the selected aim controller directs weapon fire at the chosen part. Full Burst or an active Focus Fire skill redirects allied fire. Other AI units are modeled firing at the body; incidental part hits are not credited. Autonomous random-target projectiles currently share this aim approximation; their actual target selection and exact part-break times are not calibrated. Opening samples compare up to five fixed part-aim choices; promising controllers receive full-fight verification. Separate QTE and projectile targeting reactions still apply.',
    'Museum AI and animation attack markers drive the boss clock. Animation loops use CastingTime / 100; movement completion is approximated as one second.',
    'Finite part HP uses the starting monster LevelBrokenHp times the monster and part HP ratios, as confirmed in the client constructor. Main-body HP uses LevelHp. The aim controller focuses the core, then summons, then launch ports; the whole squad follows during Full Burst. Perfect aim is assumed; overlapping pierce and splash geometry are not reproduced.',
    'Ultrasonic Wave sets existing summons to 90 HP with one damage per hit. All-enemy skills hit each summon; distributed damage bypasses the reduction according to the recovered damage-share priority effect.',
    'Boss damage excludes damage spent on summons. The full direct hit transfers to the body when a part breaks, even when it exceeds remaining part HP. Part destruction also removes body HP and changes damage-based phases; that bonus is reported separately from direct damage. Character Battle Records additionally include summon hits, including overkill.',
    'Summon entry and attack cadence approximate movement using their AI waits and skill casting/delay values. Projectiles are treated as arriving at the attack marker; manual projectile interception is not modeled.',
    'Incoming damage uses ATK minus effective DEF, multiplied by the skill and level ratios, divided among the attack shots. Finite cover, shields, healing, taunt and invulnerability are applied. The run ends conservatively at the first squad death; client damage conversion remains approximate.',
    'Museum weekly damage buffs are not applied. These are modeled outcomes, not verified in-game clear predictions.',
]

def part_name(name):
    return re.sub(r'(?<=[a-z])(?=[A-Z0-9])','_',name)

class MotherWhaleWorld(PartWorld):
    def __init__(self,runtime):
        self.runtime=runtime
        self.rows={part_name(p['PartsType']):p for p in DATA['parts']}
        main=next(p for p in self.rows.values() if p['IsMainPart'])
        hp={name:part_max_hp(runtime.stat(),runtime.monster,p,main) for name,p in self.rows.items()}
        super().__init__(hp)
        self.position=254;self.attacks={};self.serial=0
        for name in hp:self.parts.spawn(name,hp[name],0)

    def cancel(self,node,time):
        if self.attacks.pop(node['ID'],None):self.runtime.log('boss attack cancelled',node=node['ID'])

    def action(self,node,time,state):
        kind=node['Type'].split('.')[-1];r=self.runtime
        if r.stopped:return RUNNING
        if kind=='CheckHp':
            if node.get('BooleanisUsingMianHp'):raise ValueError('Unexpected main HP condition')
            p=self.parts.parts[node['PartsTypemPartsType']]
            # These source branches use <1 for dead and >0 for living parts.
            value=p['hp'];threshold=node['Int32mValue']
            if threshold not in (0,1):raise ValueError('Unsupported part HP threshold')
            ok=value<threshold if node['BooleanmLower'] else value>threshold
            return SUCCESS if ok else FAILURE
        if kind=='IsInPoint':
            if self.position==node['Int32_point']:return SUCCESS
            return FAILURE if time-state['started']>=node['Single_duration'] else RUNNING
        if kind=='MoveToVer3':
            if time-state['started']<r.move_seconds:return RUNNING
            self.position=node['Int32_pointIndex'];return SUCCESS
        if kind=='CheckMonsterCount':
            count=1+len(r.living_adds())
            return SUCCESS if node['Int32min']<=count<=node['Int32max'] else FAILURE
        if kind in ('BrokenPartsV3','RepairPartsVer3'):
            translated=dict(node,Type='BrokenPartsV2' if kind=='BrokenPartsV3' else 'RepairPartsVer2')
            return super().action(translated,time,state)
        if kind not in ('Attack','AttackV3','TimelineSkill'):return super().action(node,time,state)
        shot=int((node.get('SkillAniNumberTypemSkillAniNumber') or node['List`1_aniNumberTypes'][0]).split('_')[-1])
        skill=SKILLS[r.monster['SkillData'][shot-1]['SkillId']]
        if 'impacts' not in state:
            cast=skill['CastingTime']/100
            timeline=DATA['timelines'].get(str(shot)) if kind=='TimelineSkill' else None
            if timeline:
                markers=timeline['markers'];a=next(m['time'] for m in markers if m['type'].endswith('/LoopStart'))
                b=next(m['time'] for m in markers if m['type'].endswith('/LoopEnd'))
                shift=cast-(b-a)
                impacts=[time+m['time']+shift for m in markers if '/Attack' in m['type']]
                end=time+timeline['duration']+shift
            else:impacts=[time+cast];end=time+cast+skill['DelayTime']/100
            state.update(impacts=impacts,end=end,fired=0,shot=shot)
            self.attacks[node['ID']]=state
            r.log('boss attack started',shot=shot,skill_id=skill['Id'],impact=round(impacts[0],3),node=node['ID'])
            if shot==2 and r.first_wave_deadline is None:r.first_wave_deadline=impacts[0]
        while state['fired']<len(state['impacts']) and time>=state['impacts'][state['fired']]-1e-9:
            state['fired']+=1;r.perform_skill(shot,skill)
        if time>=state['end']-1e-9:
            self.attacks.pop(node['ID'],None);return SUCCESS
        return RUNNING

class EliteWorld(PartWorld):
    """Elite summons execute their own attack and withdrawal branches."""
    def __init__(self,runtime,add,position):
        super().__init__({});self.runtime=runtime;self.add=add;self.position=position

    def action(self,node,time,state):
        kind=node['Type'].split('.')[-1];r=self.runtime
        if kind in ('SpawnAction','IsNormalCondition','IsInCombatZone'):return SUCCESS
        if kind=='IsInPoint':return SUCCESS if self.position==node['Int32_point'] else FAILURE
        if kind=='TeleportTo':
            if time-state['started']<node['Single_teleportTime']:return RUNNING
            self.position=node['Int32_pointIndex'];return SUCCESS
        if kind=='SelfDestruct':
            self.add.update(hp=0,cleared_at=time,clear_reason='scripted withdrawal');r.log('elite withdrew',target=self.add['id']);return SUCCESS
        if kind=='Stun':return FAILURE
        if kind=='Attack':
            skill=SKILLS[self.add['skill']]
            if time-state['started']<skill['CastingTime']/100:return RUNNING
            if not state.get('fired'):
                r.queue_attack(skill,source=self.add['id'],monster=MONSTERS[self.add['monster_id']],buffed=self.add['buffed']);state['fired']=True
            return SUCCESS if time-state['started']>=(skill['CastingTime']+skill['DelayTime'])/100 else RUNNING
        return super().action(node,time,state)

class MotherWhaleRuntime(EncounterRuntime):
    # Shared ally buff semantics; boss targeting and attack formulas are separate.
    active_stat=KrakenRuntime.active_stat
    protection=KrakenRuntime.protection

    def __init__(self,script,duration,*,mode='challenge',seed=42,target_policy='core',move_seconds=1.,auto_cover=True):
        super().__init__(script,duration)
        if mode not in DATA['modes']:raise ValueError('Invalid Museum mode')
        if target_policy not in ('core','adds','body'):raise ValueError('Invalid Mother Whale target policy')
        self.monster=DATA['mode_monsters'][mode];self.mode=mode;self.target_policy=target_policy;self.move_seconds=move_seconds;self.auto_cover=auto_cover
        self.stages=sorted((s for s in DATA['stages'] if s['Group']==DATA['modes'][mode]['MonsterStageLvChangeGroup']),key=lambda s:s['ConditionValueMin'])
        self.rng=random.Random(seed);self.world=MotherWhaleWorld(self)
        self.tree=BehaviorTree(DATA['trees'][mode],self.world,seed)
        self.bm=None;self.adds=[];self.add_trees={};self.pending=[];self.pending_shots=[];self.incoming=[];self.cover={};self.cover_max={};self.cover_def={};self.covered=set();self.def_debuffs={}
        self.first_wave_deadline=None;self.core_broken_at=None;self.core_hp_at_deadline=None;self.waves=[];self.barrier_windows=[];self.barrier=False;self.barrier_used=False
        self.part_break_damage=0.;self.part_break_events=[];self.damage_to_parts=0.;self.damage_to_adds=0.;self.add_damage_by_unit={};self.barrier_damage_by_unit={};self.part_cursor=0;self.stop_reason=None;self.attack_boost_until=0.;self.attack_boost=0.

    def stat(self,monster=None):
        m=monster or self.monster
        stage=max((s for s in self.stages if self.damage>=s['ConditionValueMin']),key=lambda s:s['ConditionValueMin'])
        return STATS[(m['StatenhanceId'],stage['MonsterStageLv'])]

    def bind(self,bm,squad,char_states):
        self.bm=bm;self.squad={c['name']:c for c in squad};self.char_states=char_states
        rows={r['Lv']:r for r in DATA['cover_stats']}
        for name,char in self.squad.items():
            row=rows[min(400,max(1,int(char.get('level',400))))]
            maximum=row['LevelHp']*max(0,1+self.active_stat(name,'cover_hp_pct')/100)
            self.cover[name]=self.cover_max[name]=maximum;self.cover_def[name]=row['LevelDefence']
        self.aim_controller=self.aim_controller_override or max(char_states,key=lambda n:char_states[n].base_atk)
        def repair(eff,caster,t,value):
            for name in bm._resolve_target(eff.get('target','all_allies'),caster):
                if self.cover.get(name,0)>0:self.cover[name]=min(self.cover_max[name],self.cover[name]+self.cover_max[name]*value/100)
        bm.register_instant_handler('cover_heal_pct',repair)

    def log(self,event,**details):self.events.append(dict(time=round(self.time,3),event=event,**details))
    def living_adds(self):return [a for a in self.adds if a['hp']>0]

    def refresh_barrier(self):
        alive=bool(self.living_adds())
        if alive and not self.barrier_used:
            self.barrier=self.barrier_used=True;self.barrier_windows.append(dict(start=self.time,end=None))
            self.log('Electric barrier enabled')
        elif self.barrier and not alive and not self.pending:
            self.barrier=False;self.barrier_windows[-1]['end']=self.time;self.log('Electric barrier removed by clearing summons')

    def perform_skill(self,shot,skill):
        if self.stopped:return
        self.log('boss skill activated',shot=shot,skill_id=skill['Id'])
        if skill['FireType']=='Calling':
            for row in DATA['calls']:
                if row['GroupId']==skill['SkillValue01']:self.pending.append(dict(record=row,at=self.time+row['SpawnTime']))
        elif shot==2:
            enabled=self.world.parts.alive(CORE)
            self.waves.append(dict(time=round(self.time,3),core_alive=enabled,adds=len(self.living_adds())))
            if enabled:
                for add in self.living_adds():add.update(hp=90.,protected=True,buffed=True)
                self.log('Ultrasonic Wave protected summons',count=len(self.living_adds()))
            else:self.log('Ultrasonic Wave cancelled by core destruction')
        elif shot==11:
            count=1+len(self.living_adds());self.attack_boost=.2*sum(count>=n for n in (3,5,10,15,20));self.attack_boost_until=self.time+10
        elif shot==17:
            if self.barrier:self.barrier=False;self.barrier_windows[-1]['end']=self.time
        elif skill['SkillValueType01']=='Percent' and skill['SkillValue01']>0:
            self.queue_attack(skill,source='Mother Whale')
            if shot in (1,3):
                for add in self.living_adds():add['hp']=0;add['cleared_at']=self.time;add['clear_reason']='boss sweep'
                self.pending=[];self.refresh_barrier()

    def spawn_add(self,row):
        monster=MONSTERS[row['MonsterId']];stat=self.stat(monster)
        skill=next(SKILLS[s['SkillId']] for s in monster['SkillData'] if s['SkillId'])
        # Ordinary minions have 0.5–1.5s AI attack waits; fixed ground summons use 1.5s.
        wait=1.5 if monster['SpotAi']=='bt_motherwhale_calling_02' else 1.
        hp=stat['LevelHp']*monster['HpRatio']/10000
        add=dict(id=f"summon-{len(self.adds)+1}",monster_id=monster['Id'],spawned=self.time,hp=hp,max_hp=hp,
                 protected=False,buffed=False,skill=skill['Id'],next_attack=self.time+wait+skill['CastingTime']/100,
                 interval=max(.1,wait+skill['CastingTime']/100+skill['DelayTime']/100),cleared_at=None)
        self.adds.append(add)
        if monster['SpotAi'] in ('bt_motherwhale_calling_movefire','bt_motherwhale_calling_cannonade'):
            self.add_trees[add['id']]=BehaviorTree(DATA['add_trees'][monster['SpotAi']],EliteWorld(self,add,row['ActionPoint']))
        self.log('summon spawned',target=add['id'],monster_id=monster['Id'],hp=round(hp));self.refresh_barrier()

    def advance(self,t,state=None):
        if self.stopped:return
        super().advance(t,state)
        if self.stopped:return
        self.covered=set()
        for item in list(self.pending):
            if t>=item['at']-1e-9:self.pending.remove(item);self.spawn_add(item['record'])
        self.tree.advance(t)
        if self.first_wave_deadline is not None and t>=self.first_wave_deadline and self.core_hp_at_deadline is None:
            self.core_hp_at_deadline=self.world.parts.parts[CORE]['hp']
        for add in self.living_adds():
            if self.stopped:break
            if add['id'] in self.add_trees:self.add_trees[add['id']].advance(t)
            elif t>=add['next_attack']:
                self.queue_attack(SKILLS[add['skill']],source=add['id'],monster=MONSTERS[add['monster_id']],buffed=add['buffed'])
                add['next_attack']+=add['interval']
        for shot in list(self.pending_shots):
            if self.stopped:break
            if t>=shot['at']-1e-9:
                self.pending_shots.remove(shot)
                self.receive_attack(shot['skill'],**shot['context'])
        self.refresh_barrier()
        for event in self.world.parts.events[self.part_cursor:]:
            if event['event']=='part destroyed by squad':
                self.events.append(dict(event))
                if self.bm:
                    for n in self.squad:self.bm.notify('event:part_destroy',t,n)
        self.part_cursor=len(self.world.parts.events)
        if self.enemy_def is not None:self.enemy_def*=1+self.monster_stack_bonus('StatDef')
        if state is not None:state['encounter_cover']=self.covered

    def monster_stack_bonus(self,kind):
        count=1+len(self.living_adds())
        return sum(f['FunctionValue']/10000 for f in DATA['functions'] if f['FunctionType']==kind and f['TimingTriggerType']=='OnSpawnMonster' and count>=f['StatusTriggerValue'])

    def select_target(self,caster):
        controlled=self.follows_aim(caster, getattr(self,'aim_controller',caster))
        if not controlled or self.target_policy=='body':return ('body',None)
        adds=self.living_adds()
        electric='전격' in self.element_access.get(caster,[(getattr(self,'squad',{}).get(caster) or {}).get('element_code')])
        if self.target_policy=='core' and self.world.parts.alive(CORE) and (not adds or (not self.waves and (not self.barrier or electric))):return ('part',CORE)
        if adds:return ('add',adds[0])
        if self.world.parts.alive(CORE):return ('part',CORE)
        for part in ('Weapon_01','Weapon_04','Weapon_02','Weapon_05','Weapon_03','Weapon_06'):
            if self.world.parts.alive(part):return ('part',part)
        return ('body',None)

    def core_probability(self,caster,fallback):
        kind,target=self.select_target(caster)
        return float(kind=='part' and target==CORE)

    def hold_fire(self,caster,weapon,element):return self.waiting

    def hurt_add(self,add,amount,caster,split=False):
        if add['hp']<=0:return 0.
        raw=1. if add['protected'] and not split and amount>0 else amount
        dealt=min(add['hp'],raw)
        add['hp']-=dealt;self.damage_to_adds+=dealt
        # Native character statistics and drain events use raw incoming damage,
        # including overkill; effective summon HP loss is tracked separately.
        self.add_damage_by_unit[caster]=self.add_damage_by_unit.get(caster,0)+raw
        if add['hp']<=0:
            add['cleared_at']=self.time;add['clear_reason']='squad damage';self.log('summon cleared',target=add['id'])
            self.refresh_barrier()
        return raw

    def resolve(self,caster,element,weapon,hit_type,calculate,args):
        barrier_at_start=self.barrier
        weapon_hit=hit_type.get('is_normal_atk') or hit_type.get('is_weapon_mode_skill')
        kind,target=self.select_target(caster) if weapon_hit else ('body',None)
        aoe=hit_type.get('effect_target')=='all_enemies' or hit_type.get('is_aoe_burst') or hit_type.get('is_split')
        if aoe:kind,target='body',None
        args=dict(args,hit_type=dict(args['hit_type']))
        if self.enemy_def is not None:args['enemy_def']=self.enemy_def
        if kind=='add':
            monster=MONSTERS[target['monster_id']];args['enemy_def']=self.stat(monster)['LevelDefence']*monster['DefenceRatio']/10000
            args['hit_type'].update(is_core=False,core_prob=0,is_part=False)
        elif kind=='part':args['hit_type']['is_part']=True
        result=calculate(**args)
        if self.stopped or self.blocks('invulnerable'):
            result['damage']=0;return result
        amount=result['damage'];extra=0.
        if aoe:
            targets=list(self.living_adds())
            if hit_type.get('is_split'):amount/=1+len(targets)
            for add in targets:
                monster=MONSTERS[add['monster_id']]
                add_args=dict(args,enemy_def=self.stat(monster)['LevelDefence']*monster['DefenceRatio']/10000,
                              hit_type=dict(args['hit_type'],is_core=False,core_prob=0,is_part=False))
                add_amount=calculate(**add_args)['damage']/(1+len(targets) if hit_type.get('is_split') else 1)
                extra+=self.hurt_add(add,add_amount,caster,split=hit_type.get('is_split',False))
            if targets and self.bm:
                # The engine already counts the body hit. Each additional enemy
                # hit supplies the same unit/skill-specific gauge coefficient.
                from calculator.timeline import BURST_GAUGE_EXCEPTIONS
                energy=BURST_GAUGE_EXCEPTIONS.get(caster,{}).get(hit_type.get('effect_name'),{}).get('burst_energy')
                gain=self.char_states[caster]._burst_gain(args['buffs'],len(targets),burst_energy=energy)
                self.bm.add_burst_gauge(gain,self.time,caster,'summon hits')
        if kind=='add':
            extra+=self.hurt_add(target,amount,caster);amount=0.
        elif barrier_at_start and '전격' not in self.element_access.get(caster,[element]):amount=0.
        elif kind=='part' and amount>0:
            alive=self.world.parts.alive(target)
            part_damage=self.world.parts.damage(target,amount,self.time)
            self.damage_to_parts+=part_damage;self.record_part_aim(target,caster,part_damage)
            if alive and not self.world.parts.alive(target):
                main=next(p for p in self.world.rows.values() if p['IsMainPart'])
                bonus=part_break_damage(self.stat(),self.monster,self.world.rows[target],main)
                self.part_break_damage+=bonus;self.damage+=bonus
                self.part_break_events.append(dict(time=self.time,part=target,damage=bonus))
            if target==CORE and alive and not self.world.parts.alive(CORE):
                self.core_broken_at=self.time;self.log('core destroyed',before_first_wave=not self.waves)
        if barrier_at_start and amount>0:self.barrier_damage_by_unit[caster]=self.barrier_damage_by_unit.get(caster,0)+amount
        self.damage+=amount;result['damage']=round(amount)
        # Add damage is not boss score, but it still restores lifesteal HP.
        # The engine applies lifesteal to the returned boss damage separately.
        if extra and self.bm:
            from calculator.timeline import _restore_hp
            lifesteal=self.bm.get_buffs(caster,'__enemy__',self.time).get('lifesteal_pct',0.)
            if lifesteal>0:_restore_hp(self.bm,caster,extra*lifesteal/100,self.time,caster,None)
        return result

    def queue_attack(self,skill,**context):
        if skill.get('ShotTiming')=='Sequence' and skill['ShotCount']>1:
            single=dict(skill,ShotCount=1,_damage_shots=skill['ShotCount'])
            for i in range(skill['ShotCount']):
                self.pending_shots.append(dict(at=self.time+i*skill['DelayTime']/100,skill=single,context=context))
        else:self.receive_attack(skill,**context)

    def receive_attack(self,skill,*,source,monster=None,buffed=False):
        if not self.bm or self.stopped:return
        bm=self.bm;hp=bm.state['hp'];stat=self.stat(monster);m=monster or self.monster
        names=[n for n in self.squad if hp[n]>0]
        taunters=[n for n in names if self.protection(n,'taunt')]
        count=max(1,skill['ShotCount']);all_targets=skill.get('TargetCount')==5
        targets=names if all_targets else [self.rng.choice(taunters or names) for _ in range(count)]
        for name in targets:
            roll=self.rng.random()*100
            direct_cover=roll<skill.get('TargetCoverRatio',0)
            if roll>=skill.get('TargetCoverRatio',0)+skill.get('TargetCharacterRatio',100):
                self.log('enemy shot missed squad',source=source,shot=skill['Id']);continue
            debuffs=[end for end in self.def_debuffs.get(name,[]) if end>self.time]
            self.def_debuffs[name]=debuffs
            base_def=bm.state.get('base_stats',{}).get(name,{}).get('def',0.)
            defence=max(0.,bm._effective_def(name)-base_def*.05*len(debuffs))
            boost=(1.2 if buffed else 0.) if monster else self.monster_stack_bonus('StatAtk')+(self.attack_boost if self.time<self.attack_boost_until else 0.)
            attack=stat['LevelAttack']*m['AttackRatio']/10000*(1+boost)
            amount=incoming_hit(attack,defence,skill['SkillValue01'],stat['LevelStatdamageratio'],skill.get('_damage_shots',skill['ShotCount']))
            amount*=max(0,1+self.active_stat(name,'received_dmg_pct')/100)
            # Water enemies have advantage against Fire units.
            if self.squad[name].get('element_code')=='작열' and m['ElementId']==[200001]:amount*=1.1
            blocked=None;absorbed=0.
            shields=[ab for ab in bm._active if ab.shield_per_target.get(name,0)>0 and self.time<ab.expires_at]
            if self.protection(name,'invincible'):blocked='invincible'
            elif shields:
                ab=shields[0];absorbed=min(amount,ab.shield_per_target[name]);ab.shield_per_target[name]-=absorbed
                if ab.effect.get('stat')=='shared_shield_from_max_hp_pct':
                    for n in ab.shield_per_target:ab.shield_per_target[n]=ab.shield_per_target[name]
                blocked='shield';bm._invalidate_buffs_cache()
            elif self.cover.get(name,0)>0 and (direct_cover or bm.state.get('planned_cover') or (self.auto_cover and amount>hp[name]*.95)):
                amount=incoming_hit(attack,self.cover_def[name],skill['SkillValue01'],stat['LevelStatdamageratio'],skill.get('_damage_shots',skill['ShotCount']))
                absorbed=min(amount,self.cover[name]);self.cover[name]-=absorbed;blocked='cover';self.covered.add(name)
            elif direct_cover:blocked='destroyed cover'
            else:
                hp[name]=max(1. if self.protection(name,'undying') else 0.,hp[name]-amount)
                bm.sync_hp(name);bm.notify('received_hit',self.time,name)
                if skill['Id'] in (530904,530905,530912,530913,530914,530915):
                    self.def_debuffs[name]=(debuffs+[self.time+90])[-10:]
            self.incoming.append(dict(time=round(self.time,3),source=source,shot=skill['Id'],target=name,
                damage=0 if blocked else round(amount),blocked_by=blocked,absorbed=round(absorbed),hp=round(hp[name]),cover=round(self.cover.get(name,0))))
            if hp[name]<=0:
                self.stop_reason='First squad death: '+name;self.stopped=True;self.log('squad member died',unit=name);break

    def report(self):
        report=super().report()
        deadline=self.first_wave_deadline
        status='passed' if self.core_broken_at is not None and (deadline is None or self.core_broken_at<=deadline) else 'failed' if deadline is not None and self.time>=deadline else 'pending'
        protection_waves=[wave for wave in self.waves if wave['core_alive']]
        precleared=0;previous_cast=float('-inf')
        for wave in protection_waves:
            # Empty casts are observed facts. Credit pre-clearing only when
            # actual summons were killed by the squad since the previous cast;
            # core cancellation or a cast before any spawn proves no AoE clear.
            if wave['adds']==0 and any(add.get('clear_reason')=='squad damage'
                    and add.get('cleared_at') is not None
                    and previous_cast<add['cleared_at']<=wave['time']+1e-3 for add in self.adds):
                precleared+=1
            previous_cast=wave['time']
        summon_control=dict(protection_casts=len(protection_waves),
            empty_protection_casts=sum(wave['adds']==0 for wave in protection_waves),
            precleared_casts=precleared,
            casts_with_survivors=sum(wave['adds']>0 for wave in protection_waves),
            protected_adds=sum(bool(add['protected']) for add in self.adds),
            core_disabled_protection=self.core_broken_at is not None,observed_until=self.time)
        report.update(model='Automatic Mother Whale · modeled fight',model_id='mother-whale-museum-v1',
            part_labels={CORE:'Core'},
            full_fight_verified=False,calibration_status='approximate',source_sha256=DATA['source_sha256'],qte_required=False,
            tree_status=self.tree.status,incoming=self.incoming,parts=copy.deepcopy(self.world.parts.parts),
            critical_parts=[dict(id='mother-whale-core',part='Core',status=status,hp=self.world.part_hp[CORE],
                remaining_hp=self.world.parts.parts[CORE]['hp'],remaining_hp_at_deadline=self.core_hp_at_deadline,deadline=deadline,destroyed_at=self.core_broken_at)],
            waves=copy.deepcopy(self.waves),summons=copy.deepcopy(self.adds),barrier_windows=copy.deepcopy(self.barrier_windows),
            summon_control=summon_control,
            damage_to_parts=round(self.damage_to_parts),damage_to_adds=round(self.damage_to_adds),
            add_damage_by_unit={n:round(v) for n,v in self.add_damage_by_unit.items()},
            part_break_damage=round(self.part_break_damage),part_break_events=copy.deepcopy(self.part_break_events),boss_hp_damage=round(self.damage),
            barrier_damage_by_unit=dict(self.barrier_damage_by_unit),
            stop_reason=self.stop_reason,survival='failed' if self.stop_reason else 'survived modeled attacks',
            policy=dict(target=self.target_policy,auto_cover=self.auto_cover),assumptions=list(ASSUMPTIONS))
        return report
