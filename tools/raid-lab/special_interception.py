"""EX encounter policies using recovered EX skills, HP, parts and timelines.

Spatial AI is reduced to explicit encounter phases. Movement, missile flight
and manual reaction are approximations, disclosed with every result.
"""
import copy
from boss_behavior import RUNNING
from raid_boss_combat import RaidBossRuntime, PART_LABELS, DATA
from mechanics import EncounterRuntime

SPECIAL_KEYS=tuple(k for k in DATA['profiles'] if k.startswith('special-'))
PART_LABELS.update(chatterbox={'Weapon_01':'Left launcher','Weapon_02':'Right launcher','Weapon_03':'Head core'},
    gravedigger={'Head':'Head shell','Arm_Left':'Left drill','Arm_Right':'Right drill','Weapon_09':'Inner drill'},
    alteisen={'Weapon_01':'Left turret 1','Weapon_02':'Left turret 2','Weapon_03':'Right turret 1','Weapon_04':'Right turret 2','Weapon_05':'Left launcher','Weapon_06':'Right launcher'})

ASSUMPTIONS=[
    'EX monster IDs are resolved through InterceptSpecial and its wave records. Units are fixed at level 200; imported equipment, skills and other investment are retained.',
    'Circle HP and casting times, enemy stats, projectile HP and finite part HP come from the recovered EX records. Actual weapon hits must clear every circle; QTE and projectile damage do not inflate boss damage.',
    'The spatial behavior trees are reduced to boss-specific phase policies. Movement and recovery use an approximate one-second interval. Missile flight uses a three-second reaction window; exact trajectories, splash overlap and animation-driven projectile counts need gameplay calibration.',
    'Target changes include 0.15 seconds of reaction time. Aim is accurate after that delay. The model does not assume invulnerability from manual dodging.',
    'Finite cover, shields, healing, taunt, stun, Chatterbox debuff stacks and deaths are simulated. Grave Digger phase-three drill attacks bypass cover. The first death stops scoring; recovery after a death is not simulated.',
    'Modernia preserves her final wing; Chatterbox preserves his head and final launcher under the safe targeting policy. Incidental splash or piercing damage to protected parts is not modeled.',
    'Train turret enrage timing is not fully reproduced. Chatterbox overlap-change is approximated as one extra corrosion stack. Those interactions and cover-stat conversion still need client verification.',
    'Stage 9 means the recovered maximum reward threshold was reached. It is not a promise of a live-game clear. Physical timing and incoming damage remain approximate.',
]

class SpecialScript:
    """Outcome-driven attack policy; uses the existing attack/cover scheduler."""
    status=RUNNING
    def __init__(self,r):
        self.r=r;self.running=[];self.queue=[];self.next_at=0.;self.serial=0
        self.cycle=0;self.phase=1;self.pressure=1;self.laser_count=0
        self.opened=False;self.last_qte=None;self.phase_transition=False

    def batch(self,shots,*,target=None,parts=(),bypass=False,pure_qte=False,delay=0,recovery=1):
        for shot in shots:
            self.serial+=1
            node=dict(ID=100000+self.serial,Type='TimelineSkill' if str(shot) in self.r.data['timelines'] else 'AttackV3',
                SkillAniNumberTypemSkillAniNumber='Shot_'+str(shot),BooleanFailueCheck=False,
                _bypass_cover=bypass,_pure_qte=pure_qte,_source_parts=list(parts),_ready_at=self.r.time+delay,_recovery=recovery)
            if target:node['ECharacterPosition_targetPosition']=target
            self.running.append((node,{'started':self.r.time}))

    def advance(self,t):
        r=self.r
        # Deadline resolution occurs before attack impact on the same tick.
        for node,state in list(self.running):
            if t<node['_ready_at']:continue
            parts=node['_source_parts']
            if parts and any(not r.world.parts.alive(p) for p in parts):
                r.world.cancel(node,t);self.running.remove((node,state));continue
            result=r.world.action(node,t,state)
            if r.key=='special-modernia' and self.laser_count>=2 and parts==['Weapon_03'] and state.get('impacts') and not state.get('deadline_registered'):
                state['deadline_registered']=True
                r.part_deadlines.register(r.world.parts,parts,min(state['impacts']),5)
                r.first_part_deadlines.setdefault('Weapon_03',min(state['impacts']))
            if state.get('qte'):self.last_qte=state['qte']
            if result!=RUNNING:
                self.running.remove((node,state));self.next_at=max(self.next_at,t+node['_recovery'])
        if self.running or t<self.next_at or r.stopped:return RUNNING
        if self.queue:
            shots,kwargs=self.queue.pop(0);self.batch(shots,**kwargs);return RUNNING
        getattr(self,r.key.removeprefix('special-'))()
        return RUNNING

    def alteisen(self):
        r=self.r;phase=2 if r.stage()['Step']>=7 else 1
        if phase!=self.phase:
            self.phase=phase;r.world.phase=phase;r.log('boss phase changed',phase=phase)
        if not self.opened:
            self.opened=True;self.batch([7]*4);return # 2 missiles per skill, 8 total.
        if phase==2:
            self.batch([9]);self.queue=[([7]*4,{})];return
        alive=r.world.parts.alive
        side=next((s for s in ((6,3,4),(5,1,2)) if any(alive(f'Weapon_{i:02}') for i in s)),None)
        if side is None:
            self.batch([8]);self.queue=[]
            # The recovered phase-one loop repairs weapons after the laser check.
            for i in range(1,7):r.world.parts.spawn(f'Weapon_{i:02}',r.world.part_hp[f'Weapon_{i:02}'],r.time)
            return
        launcher,a,b=side
        if alive(f'Weapon_{launcher:02}'):self.batch([launcher],parts=[f'Weapon_{launcher:02}'])
        for turret in (a,b):
            if alive(f'Weapon_{turret:02}'):self.queue.append(([turret],{'parts':[f'Weapon_{turret:02}']}))
        if not self.running and self.queue:
            shots,kwargs=self.queue.pop(0);self.batch(shots,**kwargs)

    def gravedigger(self):
        r=self.r;phase=3 if r.stage()['Step']>=7 else 2 if r.stage()['Step']>=4 else 1
        if phase!=self.phase:
            self.phase=phase;r.world.phase=phase;self.pressure=1;self.last_qte=None
            r.log('boss phase changed',phase=phase)
        if self.last_qte:
            status=r.states[self.last_qte]['status'];self.last_qte=None
            self.pressure=max(0,self.pressure-1) if status=='passed' else self.pressure+1
            limit=2 if phase==3 else 3
            if self.pressure>=limit:
                self.batch([5 if phase==3 else 4],bypass=phase==3)
                r.log('drill retaliation',phase=phase,cover_bypass=phase==3)
                self.pressure=1;return
        if self.cycle%2==0:self.batch([3,3])
        # Two circles at stage 1–3; three tighter circles from stage 4 onward.
        shot=(6,7,8)[self.cycle%3] if phase==1 else (9,10)[self.cycle%2]
        self.queue.append(([shot],{'pure_qte':True}));self.cycle+=1
        if not self.running:
            shots,kwargs=self.queue.pop(0);self.batch(shots,**kwargs)

    def blacksmith(self):
        r=self.r
        if self.cycle and self.cycle%3==0:
            if r.stage()['Step']>=7:
                # Capture the highest-HP unit, then give the remaining units a check.
                if r.bm:
                    target=max(r.squad,key=lambda n:r.bm.state['hp'][n]);r.apply_function(1999035,target)
                self.batch([6])
            else:self.batch([2])
        else:
            self.batch([3,9,3]);self.queue=[([1],{}),([7],{})]
        self.cycle+=1

    def chatterbox(self):
        r=self.r
        if not self.opened:
            self.opened=True;self.batch([9],target='Player3');return
        if self.cycle%2==0:
            head=r.world.parts.alive('Weapon_03');self.batch([10 if head else 5])
            for part,shot in [('Weapon_01',2),('Weapon_02',6)]:
                if r.world.parts.alive(part):self.queue.append(([shot]*3,{'parts':[part]}))
        else:self.batch([4])
        self.cycle+=1

    def modernia(self):
        r=self.r;alive=r.world.parts.alive
        if not alive('Weapon_01') and not alive('Weapon_02'):
            r.world.phase=2;r.log('teleport phase entered; wings and core restored')
            for part in ('Weapon_01','Weapon_02','Weapon_03'):
                r.world.parts.spawn(part,r.world.part_hp[part],r.time)
            r.add_event(dict(kind='untargetable',start=r.time,duration=1))
            self.batch([9]);self.queue=[([10],{})];return
        if not self.opened:
            # Recovered opening: one-second positioning, one-second pause,
            # machine gun, then a three-second pause before the core beam.
            self.opened=True;self.batch([4]*3,delay=2,recovery=3);return
        if alive('Weapon_03'):
            self.laser_count+=1;self.batch([5],parts=['Weapon_03'])
        for part,shot in [('Weapon_01',7),('Weapon_02',8)]:
            if alive(part):self.queue.append(([shot]*3,{'parts':[part]}))
        self.queue.append(([4]*3,{'recovery':3}))
        if not self.running:
            shots,kwargs=self.queue.pop(0);self.batch(shots,**kwargs)

class SpecialInterceptionRuntime(RaidBossRuntime):
    def __init__(self,*args,**kwargs):
        super().__init__(*args,**kwargs)
        if self.key not in SPECIAL_KEYS:raise ValueError('Expected an EX encounter')
        self.tree=SpecialScript(self);self.damage_to_projectiles=0.;self.target_ready=0.;self.last_target=None
        self.debuff_stacks={};self.target_reached=False;self.reward_stage=1
        self.max_reward_damage=max(s['ConditionValueMin'] for s in self.stages)

    def bind(self,bm,squad,char_states):
        super().bind(bm,squad,char_states)
        level=self.data['modes'][self.mode]['CoverStageLv']
        row=next(r for r in DATA['cover_stats'] if r['Lv']==level)
        for n in self.squad:
            self.cover[n]=self.cover_max[n]=row['LevelHp']*(1+self.active_stat(n,'cover_hp_pct')/100)
            self.cover_def[n]=row['LevelDefence']

    def advance(self,t,state=None):
        if self.stopped:return
        # Update the QTE deadline before its linked attack can fire.
        EncounterRuntime.advance(self,t,state)
        if self.stopped:return
        super().advance(t,state)
        self.reward_stage=self.stage()['Step']
        if self.damage>=self.max_reward_damage and not self.stop_reason:
            self.target_reached=True;self.stopped=True;self.log('maximum reward stage reached',stage=9)

    def select_part(self,caster):
        if self.active or self.part_policy=='body' or any(p['status']=='active' for p in self.projectiles):return None
        if not self.follows_aim(caster,getattr(self,'aim_controller',caster)):return None
        alive=self.world.parts.alive
        if self.key=='special-modernia':
            if alive('Weapon_03'):return 'Weapon_03'
            wings=[p for p in ('Weapon_01','Weapon_02') if alive(p)]
            return wings[0] if wings and (len(wings)==2 or self.part_policy=='all') else None
        if self.key=='special-chatterbox':
            launchers=[p for p in ('Weapon_01','Weapon_02') if alive(p)]
            if launchers and (len(launchers)==2 or self.part_policy=='all'):return launchers[0]
            return 'Weapon_03' if self.part_policy=='all' and alive('Weapon_03') else None
        if self.key=='special-alteisen':
            return next((f'Weapon_{p:02}' for p in (6,3,4,5,1,2) if alive(f'Weapon_{p:02}')),None)
        if self.key=='special-blacksmith':return None # Core/body, not the high-HP guns.
        return super().select_part(caster)

    def core_probability(self,caster,fallback):
        if self.active or any(p['status']=='active' for p in self.projectiles):return 0.
        if self.key=='special-modernia':return float(self.select_part(caster)=='Weapon_03')
        if self.key=='special-blacksmith':return 1.
        return 0.

    def ordinary_qte(self,skill,time,duration):
        ident=super().ordinary_qte(skill,time,duration)
        e=self.states[ident]['event'];e['shot']=skill['Id'];e['phase']=self.world.phase
        return ident

    def reaction_target(self,ident):
        if ident!=self.last_target:self.last_target=ident;self.target_ready=self.time+self.aim_seconds
        return self.time>=self.target_ready

    def target(self,caster,weapon,element):
        target=EncounterRuntime.target(self,caster,weapon,element)
        if target is not None and not self.reaction_target((self.active['event']['id'],self.active['index'])):return None
        return target

    def perform_skill(self,skill,node):
        if node.get('_pure_qte'):return # Movement pressure, not a direct bullet hit.
        if skill['IsDestroyableProjectile']:
            count=max(1,skill['ShotCount']);stats=self.stat()
            for i in range(count):
                hp=stats['LevelProjectileHp']*skill['ProjectileHpRatio']/10000
                self.projectiles.append(dict(id='missile-'+str(len(self.projectiles)),kind='hp',hp=hp,max_hp=hp,
                    defence=stats['LevelDefence']*skill['ProjectileDefRatio']/10000,spawned=self.time,
                    deadline=self.time+3,skill=dict(skill,ShotCount=1,_damage_shots=count),node=node,status='active'))
            self.log('interceptible projectiles launched',shot=skill['Id'],count=count)
            return
        super().perform_skill(skill,node)

    def resolve(self,caster,element,weapon,hit_type,calculate,args):
        normal=hit_type.get('is_normal_atk') or hit_type.get('is_weapon_mode_skill')
        active=[p for p in self.projectiles if p['status']=='active']
        controlled=self.follows_aim(caster,getattr(self,'aim_controller',caster))
        if self.stopped or self.blocks('invulnerable'):
            result=calculate(**args);result['damage']=0;return result
        if self.active and normal:
            target=self.target(caster,weapon,element)
            if target is None and self.follows_aim(caster,self.active.get('controller')):
                result=calculate(**args);result['damage']=0;return result
        if active and not self.active and normal and controlled:
            p=active[0]
            result=calculate(**dict(args,enemy_def=p['defence'],hit_type=dict(hit_type,core_prob=0,is_core=False,is_part=False)))
            if self.reaction_target(p['id']):self.damage_projectile(p,result['damage'])
            result['damage']=0;return result
        # AoE can clear visible missiles. Distributed skills split their budget.
        aoe=active and not self.active and not normal and (hit_type.get('effect_target')=='all_enemies' or hit_type.get('is_split'))
        if aoe:
            for p in active:
                raw=calculate(**dict(args,enemy_def=p['defence'],hit_type=dict(hit_type,core_prob=0,is_core=False,is_part=False)))['damage']
                self.damage_projectile(p,raw/(len(active)+1) if hit_type.get('is_split') else raw)
        # Prevent the base class's hit-count sphere handler from taking HP missiles.
        projectiles=self.projectiles;self.projectiles=[]
        try:
            before=self.damage;result=super().resolve(caster,element,weapon,hit_type,calculate,args)
        finally:self.projectiles=projectiles
        if aoe and hit_type.get('is_split'):
            self.damage=before+round(result['damage']/(len(active)+1));result['damage']=round(result['damage']/(len(active)+1))
        return result

    def damage_projectile(self,p,amount):
        dealt=min(p['hp'],max(0,amount));p['hp']-=dealt;self.damage_to_projectiles+=dealt
        if p['hp']<=0:p.update(status='passed',destroyed_at=self.time);self.log('projectile destroyed',id=p['id'])

    def apply_function(self,ident,target=None,part=None):
        if self.key=='special-chatterbox' and ident in (1999101,1999102,1999133) and target and self.bm:
            if ident==1999101:
                f=self.functions[ident]
                # Use the buff manager's active count so cleansing removes stacks.
                eff=self.debuff_effects.setdefault((ident,target),dict(type='buff',stat='def_pct',fixed_value=f['FunctionValue']/100,
                    name='Chatterbox corrosion',target='self',polarity='harmful',duration=-1,max_stack=f['FullCount'],trigger={'condition':[]}))
                self.bm._activate(eff,target,self.time)
                count=sum(a.stack for a in self.bm._active if a.effect is eff and a.expires_at>self.time)
                self.debuff_stacks[target]=count
                if count>=f['FullCount']:
                    self.bm.state['hp'][target]=0;self.bm.sync_hp(target);self.stopped=True
                    self.stop_reason='Chatterbox corrosion reached seven stacks: '+target
                    self.log('squad member died',unit=target,reason='corrosion')
            elif ident==1999133:
                # Punches carry a second stack operation in addition to StatDef.
                self.apply_function(1999101,target)
            return
        super().apply_function(ident,target,part)

    def receive_attack(self,skill,node,**kwargs):
        # HP projectiles obey normal cover; only the sphere model bypasses it.
        if skill.get('IsDestroyableProjectile'):node=dict(node,_bypass_cover=False)
        super().receive_attack(skill,node,**kwargs)

    def update_cover(self,t):
        # Aim at airborne missiles and circles; do not duck at their launch time.
        hidden={k:a for k,a in self.world.attacks.items() if self.skills[a['shot']]['IsDestroyableProjectile'] or a['node'].get('_pure_qte')}
        for k in hidden:self.world.attacks.pop(k)
        try:super().update_cover(t)
        finally:self.world.attacks.update(hidden)

    def report(self):
        report=super().report();family=self.key.removeprefix('special-')
        report.update(model='Special Interception · '+family.replace('-',' ').title()+' · modeled fight',
            special_interception=True,part_labels=PART_LABELS.get(family,{}),assumptions=list(ASSUMPTIONS)+(['Unmodeled recovered effect types: '+', '.join(sorted(self.unhandled))] if self.unhandled else []),
            target_reached=self.target_reached,reward_stage=self.reward_stage,max_reward_damage=self.max_reward_damage,
            minimum_hp_pct=min(self.bm.state.get('hp_pct',{}).values(),default=0) if self.bm else 0,
            next_reward_damage=next((s['ConditionValueMin'] for s in self.stages if s['ConditionValueMin']>self.damage),None),
            damage_to_projectiles=round(self.damage_to_projectiles),debuff_stacks=copy.deepcopy(self.debuff_stacks),
            critical_deadlines_supported=self.key=='special-modernia',
            qte_route_skipped=self.key=='special-modernia' and not report['checks'] and (self.target_reached or self.time>=self.duration-.1))
        for p in report['critical_parts']:
            p['part']=PART_LABELS.get(family,{}).get(p['id'],p['part'])
            if self.part_policy=='safe' and ((family=='chatterbox' and p['id']=='Weapon_03') or
                (family in ('chatterbox','modernia') and p['id'] in ('Weapon_01','Weapon_02') and p['remaining_hp']>0)):
                p['preserved']=True
        for c in report['checks']:
            item=self.states[c['id']];e=item['event'];c.update(start=item['start'],deadline=(item['start']+e['duration']) if item['start'] is not None else None,
                shot=e.get('shot'),phase=e.get('phase'),target_count=len(e.get('targets',[])))
        return report
