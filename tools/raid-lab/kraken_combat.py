"""Automatic Kraken encounter, driven by recovered AI and real player hits.

This is a source-derived approximation, not a verified replica of the client.
Uncertain physical conversions are named in MODEL_ASSUMPTIONS and the report.
No account names, recorded scores, or recorded encounter timestamps are inputs.
"""
import copy
import json
import math
import random
from pathlib import Path
from boss_behavior import BehaviorTree, RUNNING, SUCCESS, FAILURE
from boss_world import PartWorld
from mechanics import EncounterRuntime
from enemy_damage import incoming_hit
from critical_parts import Deadlines

DATA=json.loads((Path(__file__).parent/'kraken-combat-data.json').read_text(encoding='utf8'))
FRONT=('Leg_Front_Left','Leg_Front_Right')
BACK=('Leg_Back_Left','Leg_Back_Right')
PART_NAMES={'LegFrontLeft':FRONT[0],'LegFrontRight':FRONT[1],
            'LegBackLeft':BACK[0],'LegBackRight':BACK[1]}
MODEL_ASSUMPTIONS=[
    'Outside Full Burst, only the selected aim controller directs weapon fire at the chosen part. Full Burst or an active Focus Fire skill redirects allied fire. Other AI units are modeled firing at the body; incidental part hits are not credited. Opening samples compare up to five fixed part-aim choices; promising controllers receive full-fight verification. Separate QTE and projectile targeting reactions still apply.',
    'Recovered behavior tree executes automatically; custom leaf completion semantics remain approximate.',
    'Part HP uses LevelBrokenHp times part HpRatio / 10000; dynamic-object scaling needs client verification.',
    'Timeline loop span is replaced by table CastingTime / 100; movement speed and phase animation timing need verification.',
    'Ordinary and special interruption HP use LevelBrokenHp times target ratio / 10000; intro, geometry and spread collision remain approximate.',
    'Normal and transformed weapon fire targets finite parts and applies part-damage buffs; overlapping pierce/AoE geometry is not modeled.',
    'Incoming damage subtracts DEF before skill and level ratios and divides the attack budget among its shots, following the recovered damage routine; complete client validation is pending. Projectile travel and interception are unmodeled; multi-projectile attacks resolve their shots at the same estimated impact time.',
    'Finite cover uses the level table; shields gate an individual hit. Cover is reserved for hits exceeding 95% of current HP. The run conservatively ends at the first squad death.',
    'Core geometry assumes perfect hits on a targeted front tentacle or exposed phase-two body; spread and hidden-core pierce overlap are unverified.',
]

class KrakenWorld(PartWorld):
    def __init__(self,runtime):
        self.runtime=runtime
        hp={PART_NAMES.get(r['PartsType'],r['PartsType']):111000000*r['HpRatio']/10000 for r in DATA['parts']}
        super().__init__(hp)
        self.skills={int(s['SkillAniNumber'][4:]):s for s in DATA['skills']}
        self.phase=1;self.position=254;self.front_scale=1.;self.serial=0
        self.barrier=False;self.submerged=False;self.attacks={}
        for name in BACK+('Head',):self.parts.spawn(name,hp[name],0)
        self.parts.spawn(runtime.rng.choice(FRONT),hp[FRONT[0]],0)

    def cancel(self,node,time):
        attack=self.attacks.pop(node['ID'],None)
        if attack:
            self.runtime.log('boss attack branch cancelled',node=node['ID'],shot=attack['shot'])
            if attack.get('qte'):self.runtime.finish_event(attack['qte'])

    def action(self,node,time,state):
        kind=node['Type'].split('.')[-1];r=self.runtime
        if r.stopped:return RUNNING
        if kind=='RepairPartsVer2':
            for part in node['List`1_partsList']:
                if part in FRONT:self.part_hp[part]=111000000*self.front_scale
            return super().action(node,time,state)
        if kind=='isPhaseAction':
            if not state.get('applied'):
                self.phase=2;state['applied']=True;r.log('boss phase changed',phase=2)
            # Animation duration is explicit model input, not fitted to a recording.
            return SUCCESS if time-state['started']>=r.phase_animation else RUNNING
        if kind in ('MoveToVer2','TeleportToVer2'):
            dest=node['Int32_pointIndex']
            if dest in (301,302):self.submerged=True
            delay=node.get('Single_teleportTime',r.move_seconds)
            if time-state['started']<delay:return RUNNING
            self.position=dest
            if dest==254:self.submerged=False;r.log('boss body available')
            return SUCCESS
        if kind=='QuickTimeEvent':
            if not state.get('qte'):
                record=next(x for x in DATA['qtes'] if x['Id']==node['Int32_quickTimeId'])
                # Kept independent of core to avoid importing account/search code.
                linked={i for x in DATA['qte_targets'] if x['GroupId'] in record['GroupId'] for i in x['Chain']}
                targets=[]
                for x in DATA['qte_targets']:
                    if x['GroupId'] not in record['GroupId']:continue
                    first=x['FirstCol'] or (x['ColType']=='Counter' and x['ColIndex'] not in linked)
                    targets.append(dict(id=x['ColIndex'],kind='break' if x['ColType']=='Break' else 'counter',
                        hp=r.stat()['LevelBrokenHp']*x['HpRatio']/10000,
                        duration=x['TimeLimit']/100,delay=(record['FirstColAnimTime'] if first else x['DelayTime'])/100,
                        first=first,chain=x['Chain'],weapons=['AR','SMG','MG','SR']))
                state['qte']=r.add_event(dict(kind='qte',start=time,duration=record['TimeLimit']/100,
                    graph=targets,controller='auto',full_burst_follow=False,on_fail='downtime',failure_downtime=0))
                r.log('special QTE selected',pattern=record['Id'])
            status=r.states[state['qte']]['status']
            if status=='passed':return FAILURE  # AI selector then sets A=1, the safe return path.
            if status in ('failed','unknown'):
                r.log('special QTE wipe');r.stop_reason='Special interruption failed';r.stopped=True;return SUCCESS
            return RUNNING
        if kind not in ('AttackV3','TimelineSkill'):return super().action(node,time,state)
        shot=int((node.get('SkillAniNumberTypemSkillAniNumber') or node['List`1_aniNumberTypes'][0]).split('_')[-1])
        if shot in (11,12):
            self.barrier=shot==11;r.log('element barrier enabled' if self.barrier else 'element barrier disabled');return SUCCESS
        if shot in (17,18,25,26):
            scale={17:101.,18:1.,25:.1,26:1.}[shot];self.front_scale=scale
            for part in FRONT:
                self.part_hp[part]=111000000*scale
                if self.parts.alive(part):
                    p=self.parts.parts[part];fraction=p['hp']/p['max_hp'];p['max_hp']=self.part_hp[part];p['hp']=p['max_hp']*fraction
            return SUCCESS
        skill=self.skills[shot]
        part={8:FRONT[0],14:FRONT[1],1:BACK[0],10:BACK[1]}.get(shot)
        if part and not self.parts.alive(part) and not state.get('committed'):
            self.attacks.pop(node['ID'],None);return FAILURE
        if 'impact' not in state:
            cast=skill['CastingTime']/100
            timeline=DATA['timelines'].get(str(shot)) if kind=='TimelineSkill' else None
            if timeline:
                markers={m['type'].split('/')[-1]:m['time'] for m in timeline['markers']}
                shift=cast-(markers['LoopEnd']-markers['LoopStart'])
                state['impact']=time+markers['Attack']+shift
                state['end']=time+timeline['duration']+shift
                state['interrupt_at']=time+markers['LoopStart']
            else:state.update(impact=time+cast,end=time+cast,interrupt_at=time)
            state.update(shot=shot,part=part);self.attacks[node['ID']]=state
            if part in FRONT:r.part_deadlines.register(self.parts,[part],state['impact'],shot)
            if shot in (1,10):state['committed']=True
            r.log('boss attack started',shot=shot,part=part,impact=round(state['impact'],3))
        if part in FRONT and not self.parts.alive(part) and not state.get('fired'):
            self.attacks.pop(node['ID'],None);r.log('charged attack cancelled by part destruction',shot=shot,part=part);return FAILURE
        if shot==16 and time>=state['interrupt_at'] and not state.get('qte'):
            state['qte']=r.add_event(dict(kind='qte',start=time,duration=max(.01,state['impact']-time),
                targets=[dict(hp=r.stat()['LevelBrokenHp']*skill['BreakObjectHpRaito']/10000,element='풍압') for _ in skill['BreakObject']],
                controller='auto',full_burst_follow=True,on_fail='downtime',failure_downtime=0))
        if shot==16 and state.get('qte') and r.states[state['qte']]['status']=='passed':
            self.attacks.pop(node['ID'],None);r.log('charged attack cancelled by QTE',shot=shot);return FAILURE
        if time>=state['impact'] and not state.get('fired'):
            state['fired']=True;r.receive_attack(shot,skill)
        if time>=state['end']:
            self.attacks.pop(node['ID'],None);return SUCCESS
        return RUNNING

class KrakenRuntime(EncounterRuntime):
    def __init__(self,script,duration,*,seed=42,auto_cover=True,target_policy='safe',
                 aim_seconds=.15,move_seconds=1.,phase_animation=1.,cover_threshold=.95):
        super().__init__(script,duration)
        if target_policy not in ('safe','delay','body'):raise ValueError('Invalid Kraken target policy')
        self.rng=random.Random(seed);self.auto_cover=auto_cover;self.target_policy=target_policy
        if not 0<cover_threshold<=1:raise ValueError("Cover threshold must be in (0,1]")
        self.cover_threshold=cover_threshold
        self.aim_seconds=aim_seconds;self.move_seconds=move_seconds;self.phase_animation=phase_animation
        self.world=KrakenWorld(self);self.tree=BehaviorTree(DATA['tree'],self.world,seed)
        self.bm=None;self.cover={};self.cover_max={};self.cover_def={};self.covered=set();self.incoming=[]
        self.target_history=[];self.aim_id=None;self.aim_ready=0.;self.part_cursor=0
        self.damage_to_parts=0.;self.damage_to_checks=0.;self.stop_reason=None
        self.normal_by_unit={};self.interrupt_margin=1.;self.part_rate=0.;self.normal_damage=0.;self.firing_seconds=0.;self.last_time=0.
        self.part_deadlines=Deadlines()
        self.part_break_damage=0.;self.part_break_events=[]
        # The recovered Kraken part rows all specify zero destruction bonus.
        # That establishes zero without inventing the missing monster HP ratio.
        self.part_break_damage_supported=all(p.get('DamageHpRatio')==0 for p in DATA['parts'])

    def bind(self,bm,squad,char_states):
        self.bm=bm;self.squad={x['name']:x for x in squad};self.char_states=char_states
        rows={x['Lv']:x for x in DATA['cover_stats']}
        for name,char in self.squad.items():
            row=rows[min(400,max(1,int(char.get('level',400))))]
            # Collection passives are active before bind. Their cover bonus was
            # previously dropped even though character flat stats were imported.
            maximum=float(row['LevelHp'])*max(0.,1+self.active_stat(name,'cover_hp_pct')/100)
            self.cover[name]=maximum;self.cover_max[name]=maximum
            self.cover_def[name]=float(row['LevelDefence'])
        self.aim_controller=self.aim_controller_override or max(char_states,key=lambda n:char_states[n].base_atk)
        def repair(eff,caster,t,val):
            for name in bm._resolve_target(eff.get('target','all_allies'),caster):
                if name in self.cover and self.cover[name]>0:self.cover[name]=min(self.cover_max[name],self.cover[name]+self.cover_max[name]*val/100)
        bm.register_instant_handler('cover_heal_pct',repair)

    def log(self,event,**details):self.events.append(dict(time=round(self.time,3),event=event,**details))
    def add_event(self,event):
        event=dict(event,id='kraken-'+str(len(self.states)))
        checked=EncounterRuntime([event]);self.states.update(checked.states)
        return event['id']
    def finish_event(self,ident):
        if ident in self.states:self.states[ident]['status']='complete'
    def stat(self):
        stage=max((x for x in DATA['stages'] if self.damage>=x['ConditionValueMin']),key=lambda x:x['ConditionValueMin'])
        return next(x for x in DATA['stats'] if x['Lv']==stage['MonsterStageLv'])

    def advance(self,t,state=None):
        self.time=t;self.frame=state or {};self.covered=set()
        if not self.waiting:self.firing_seconds+=max(0,t-self.last_time)
        self.last_time=t
        if t>=self.duration-1e-9:self.stopped=True;return
        if self.stopped:return
        if self.auto_cover and self.bm:
            # React to a pending coverable slam; only protected units take cover.
            for attack in self.world.attacks.values():
                if attack['shot']==6 and not attack.get('fired') and -1/30<=attack['impact']-t<=.25:
                    # Preserve finite cover when the squad can safely take a hit.
                    # This uses each unit's present HP/DEF, not a healer-name rule.
                    stat=self.stat();skill=self.world.skills[6]
                    for n in self.cover:
                        expected=incoming_hit(stat['LevelAttack'],self.bm._effective_def(n),skill['SkillValue01'],stat['LevelStatdamageratio'],skill['ShotCount'])
                        expected*=max(0.,1+self.active_stat(n,'received_dmg_pct')/100)
                        health=self.bm.state['hp'][n]
                        if expected>health*self.cover_threshold and self.cover[n]>0 and not self.bm.has_shield(n):self.covered.add(n)
        if self.normal_by_unit and not self.active and not self.aim_controller_override:
            self.aim_controller=max(self.normal_by_unit,key=self.normal_by_unit.get)
        self.tree.advance(t)
        self.part_deadlines.advance(t)
        if self.stopped:return
        super().advance(t,state)
        if self.world.submerged and not self.active:self.waiting=True
        for event in self.world.parts.events[self.part_cursor:]:
            self.events.append(dict(event))
            if event['event']=='part destroyed by squad' and self.bm:
                for name in self.squad:self.bm.notify('event:part_destroy',t,name)
        self.part_cursor=len(self.world.parts.events)
        if state is not None:
            state['encounter_cover']=self.covered
            state['encounter_pause_burst']=self.world.submerged

    def target(self,caster,weapon,element):
        target=super().target(caster,weapon,element)
        if target is not None:
            key=(self.active['event']['id'],target.get('id',self.active['index']))
            if self.aim_id!=key:self.aim_id=key;self.aim_ready=self.time+self.aim_seconds
            if self.time<self.aim_ready:return None
        return target

    def select_part(self,caster):
        part=None
        controlled=(self.follows_aim(caster, getattr(self,'aim_controller',caster)))
        if not self.active and not self.world.submerged and self.target_policy!='body' and controlled:
            choices=[p for p in FRONT if self.world.parts.alive(p)]
            if self.world.phase==2 and self.target_policy=='delay':
                urgent=[]
                for attack in self.world.attacks.values():
                    p=attack.get('part')
                    if p in choices and not attack.get('fired'):
                        # Learn available weapon damage from this run, never from
                        # the reference roster. Include a one-second safety margin.
                        controller=getattr(self,'aim_controller',caster)
                        rate=max(1,self.normal_by_unit.get(controller,0)/max(1,self.firing_seconds))
                        # Budget using the controlled unit alone: Full Burst can end
                        # during the charge, so total squad DPS is unsafe here.
                        latency=0.
                        if self.bm:
                            cs=self.char_states[controller];wc=self.bm.get_weapon_change(controller)
                            weapon=(wc or {}).get('weapon_type',cs.weapon_type)
                            latency=max(0.,cs.reloading_until-self.time)
                            if weapon in ('SR','RL'):latency+=(wc or {}).get('charge_time',cs.charge_time_base) or 1.
                        needed=self.world.parts.parts[p]['hp']/rate+latency+self.interrupt_margin+self.aim_seconds
                        if attack['impact']-self.time<=needed:urgent.append(p)
                choices=urgent
            if not choices and self.world.phase==2:choices=[p for p in BACK if self.world.parts.alive(p)]
            part=choices[0] if choices else None
        return part

    def core_probability(self,caster,fallback):
        if self.active or self.world.submerged:return 0.
        part=self.select_part(caster)
        return float(part in FRONT if part else self.world.phase==2)

    def choose_qte_controller(self):
        q=self.active
        if not q or not self.bm:return
        target=q['graph'].aim(self.time) if q['graph'] else q['event']['targets'][q['index']]
        if target is None:return
        if q['graph'] and q.get('graph_target')!=target['id']:
            q['controller']=None;q['graph_target']=target['id']
        options=[]
        for name,cs in self.char_states.items():
            wc=self.bm.get_weapon_change(name)
            weapon=wc.get('weapon_type',cs.weapon_type) if wc else cs.weapon_type
            element=self.squad[name].get('element_code')
            if target.get('weapons') and weapon not in target['weapons']:continue
            if target.get('element') and target['element'] not in self.element_access.get(name,[element]):continue
            if self.bm.state['hp'][name]<=0:continue
            if weapon in ('SR','RL'):
                interval=(wc or {}).get('charge_time',cs.charge_time_base) or 1.
            else:interval=1/max(.01,(wc or {}).get('fire_rate',cs.fire_rate) or 1.)
            delay=max(0.,cs.reloading_until-self.time)+interval
            options.append((delay,name))
        if q['controller'] not in {n for _,n in options}:
            q['controller']=min(options)[1] if options else None

    def hold_fire(self,caster,weapon,element):
        if not self.active:return self.world.submerged
        self.choose_qte_controller()
        if self.bm:
            wc=self.bm.get_weapon_change(caster)
            if wc:weapon=wc.get('weapon_type',weapon)
        target=self.target(caster,weapon,element)
        # Aiming holds ammunition and charge release; it is not a zero-damage shot.
        if target is None:
            return self.world.submerged or self.active.get("controller")==caster or (self.frame.get("full_burst") and self.active["event"].get("full_burst_follow"))
        return False

    def resolve(self,caster,element,weapon,hit_type,calculate,args):
        # Only the QTE controller fires during the submerged precision section.
        if self.world.submerged:
            target=self.target(caster,weapon,element) if (hit_type.get('is_normal_atk') or hit_type.get('is_weapon_mode_skill')) else None
            if target is None:
                result=calculate(**args);result['damage']=0;return result
        weapon_hit=hit_type.get('is_normal_atk') or hit_type.get('is_weapon_mode_skill')
        part=self.select_part(caster) if weapon_hit else None
        if part:args=dict(args,hit_type=dict(args['hit_type'],is_part=True))
        before=self.damage
        result=super().resolve(caster,element,weapon,hit_type,calculate,args)
        if weapon_hit and not self.active:
            # Barrier immunity must not teach the policy damage it cannot deal.
            dealt=0 if self.world.barrier and '풍압' not in self.element_access.get(caster,[element]) else result['damage']
            self.normal_damage+=dealt
            self.normal_by_unit[caster]=self.normal_by_unit.get(caster,0)+dealt
        if self.world.barrier and '풍압' not in self.element_access.get(caster,[element]):
            self.damage=before;result['damage']=0
        if part and result['damage']>0:
            amount=self.world.parts.damage(part,result['damage'],self.time)
            self.damage_to_parts+=amount;self.record_part_aim(part,caster,amount)
        return result

    def protection(self,name,stat):
        for ab in self.bm._active:
            if ab.effect.get('stat')!=stat or self.time>=ab.expires_at:continue
            targets=ab.target_chars if ab.target_chars is not None else self.bm._resolve_lazy(ab)
            if name not in targets:continue
            if ab.has_runtime_conditions and not self.bm._runtime_condition_ok(ab.effect.get('trigger',{}).get('condition',[]),ab.caster,name,name,self.time):continue
            return True
        return False

    def active_stat(self,name,stat):
        value=0.
        for ab in self.bm._active:
            if ab.effect.get('stat')!=stat or self.time>=ab.expires_at:continue
            targets=ab.target_chars if ab.target_chars is not None else self.bm._resolve_lazy(ab)
            if name not in targets:continue
            if ab.has_runtime_conditions and not self.bm._runtime_condition_ok(ab.effect.get('trigger',{}).get('condition',[]),ab.caster,name,name,self.time):continue
            value+=self.bm._get_value(ab.effect,ab,name,stack_override=ab.per_char_stacks.get(name)) or 0.
        return value

    def receive_attack(self,shot,skill):
        if not self.bm:return
        if shot in (8,14):
            self.interrupt_margin=min(8.,self.interrupt_margin+2.)
            self.log('interruption safety margin increased after missed cancellation',seconds=self.interrupt_margin)
        bm=self.bm;hp=bm.state['hp'];stat=self.stat()
        bypass=shot in (1,10,8,14,16,7)
        targets=list(self.squad) if shot in (6,7,16) else [self.rng.choice(list(self.squad)) for _ in range(skill.get('ShotCount',1))]
        for name in targets:
            if hp[name]<=0:continue
            in_cover=(name in self.covered or bm.state.get('planned_cover')) and self.cover.get(name,0)>0
            defence=self.cover_def[name] if in_cover and not bypass else bm._effective_def(name)
            amount=incoming_hit(stat['LevelAttack'],defence,skill['SkillValue01'],stat['LevelStatdamageratio'],skill['ShotCount'])
            if self.squad[name].get('element_code')=='전격':
                stage=sum(self.damage>=x['ConditionValueMin'] for x in DATA['stages'])
                amount*=3 if stage<=3 else 4 if stage<=6 else 5
            blocked=None;absorbed=0.
            shields=[ab for ab in bm._active if ab.shield_per_target.get(name,0)>0]
            if self.protection(name,'invincible'):
                blocked='invincible'
            elif not bypass and shields:
                # Shield gating: depletion blocks this individual hit, not future hits.
                ab=shields[0];absorbed=min(amount,ab.shield_per_target[name]);ab.shield_per_target[name]-=absorbed
                if ab.effect.get('stat')=='shared_shield_from_max_hp_pct':
                    for target in ab.shield_per_target:ab.shield_per_target[target]=ab.shield_per_target[name]
                blocked='shield';bm._invalidate_buffs_cache()
            elif not bypass and in_cover:
                mapping=next(x for x in DATA['skill_functions'] if x['SkillId']==skill['Id'])
                for func in DATA['functions']:
                    if func['Id'] in mapping['HurtFunctionIdSkill'] and func['FunctionType']=='CurrentHpRatioDamage' and func['StatusTriggerType']=='IsCover' and func['StatusTriggerValue']==1:
                        amount+=self.cover[name]*func['FunctionValue']/10000
                absorbed=min(amount,self.cover[name]);self.cover[name]-=absorbed;blocked='cover'
            else:
                # Ally received-damage modifiers belong to the HP recipient.
                # Do not mix enemy vulnerability buffs into incoming attacks.
                amount*=max(0.,1+self.active_stat(name,'received_dmg_pct')/100)
                minimum=1. if self.protection(name,'undying') else 0.
                hp[name]=max(minimum,hp[name]-amount);bm.sync_hp(name)
                bm.notify('received_hit',self.time,name)
            self.incoming.append(dict(time=round(self.time,3),shot=shot,target=name,damage=0 if blocked else round(amount),
                blocked_by=blocked,absorbed=round(absorbed),hp=round(hp[name]),cover=round(self.cover.get(name,0))))
            if hp[name]<=0:
                self.log('squad member died',unit=name);self.stop_reason='First squad death; conservative survival stop';self.stopped=True
        self.log('boss attack landed',shot=shot)

    def report(self):
        report=super().report()
        report.update(model='Automatic Kraken · approximate physical model',full_fight_verified=False,calibration_status='incomplete',
            part_labels={FRONT[0]:'Left front tentacle',FRONT[1]:'Right front tentacle',BACK[0]:'Left rear tentacle',BACK[1]:'Right rear tentacle'},
            critical_deadlines=self.part_deadlines.report(self.time),critical_deadlines_supported=True,
            source_sha256=DATA['source_sha256'],phase=self.world.phase,tree_status=self.tree.status,
            incoming=self.incoming,parts=copy.deepcopy(self.world.parts.parts),stop_reason=self.stop_reason,
            part_break_damage=round(self.part_break_damage),part_break_events=copy.deepcopy(self.part_break_events),boss_hp_damage=round(self.damage),
            part_break_damage_supported=self.part_break_damage_supported,
            damage_to_parts=round(self.damage_to_parts),policy=dict(auto_cover=self.auto_cover,target=self.target_policy,aim_seconds=self.aim_seconds,cover_threshold=self.cover_threshold,interrupt_margin=self.interrupt_margin),
            survival='failed' if self.stop_reason else 'survived modeled attacks',assumptions=list(MODEL_ASSUMPTIONS)+[
                'All recovered Kraken part destruction damage ratios are zero; part breaks add no separate body HP loss.'
                if self.part_break_damage_supported else
                'Part destruction bonus is not modeled: the Kraken monster HP scaling record is missing.'])
        return report
