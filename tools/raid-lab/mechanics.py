"""Encounter timeline runtime. No real-boss timing/HP is invented here.
A calibrated profile supplies a script. Unknown checks stay unknown.
All values are elapsed seconds and target HP, not average squad DPS.
"""
import copy
import math
from qte_graph import QTEGraph

class EncounterRuntime:
    def __init__(self,script,duration=None):
        self.element_access={}
        self.duration=duration
        self.script=copy.deepcopy(script);self.time=0;self.events=[];self.stopped=False
        self.damage=0;self.waiting=False;self.active=None;self.states={};self.frame={};self.enemy_def=None
        self.control_plan=[];self.aim_controller_override=None
        for i,event in enumerate(self.script):
            event.setdefault('id',str(i))
            if event.get('kind') not in ('invulnerable','untargetable','barrier','qte','cover','stat_stage'):raise ValueError('Unknown encounter event.')
            if event['kind']=='stat_stage':
                value=event.get('enemy_def')
                if isinstance(value,bool) or not isinstance(value,(int,float)) or not math.isfinite(value) or value<0:raise ValueError('Invalid stage defence.')
            if ('start' in event)==('after_damage' in event):raise ValueError('Event needs exactly one start trigger.')
            trigger=event.get('start',event.get('after_damage'))
            if isinstance(trigger,bool) or not isinstance(trigger,(int,float)) or not math.isfinite(trigger) or trigger<0:raise ValueError('Invalid event trigger.')
            duration=event.get('duration')
            if isinstance(duration,bool) or not isinstance(duration,(int,float)) or not math.isfinite(duration) or duration<=0:raise ValueError('Event duration must be positive.')
            if event['id'] in self.states:raise ValueError('Duplicate encounter event ID.')
            if event['kind']=='qte':
                event.setdefault('controller','auto')
                event.setdefault('full_burst_follow',event['controller']=='auto')
                targets=event.get('targets',event.get('graph',[]))
                if not targets:raise ValueError('QTE requires target records, even if HP is unknown.')
                if event.get('graph'):QTEGraph(event['graph'],0,event['duration'])
                for target in targets:
                    if target.get('hp') is not None and (isinstance(target['hp'],bool) or not isinstance(target['hp'],(int,float)) or not math.isfinite(target['hp']) or target['hp']<=0):raise ValueError('Invalid QTE HP.')
                if event.get('on_fail','unknown') not in ('wipe','downtime','unknown'):raise ValueError('Unsupported QTE failure outcome.')
            self.states[event['id']]={'event':event,'start':None,'status':'pending','index':0,'dealt':0,'attempted':False,'targets':[],'controller':None,'graph':None}

    def advance(self,t,state=None):
        self.time=t;self.frame=state or {};self.waiting=False;self.active=None
        if self.duration is not None and t>=self.duration-1e-9:
            self.stopped=True;return
        for item in self.states.values():
            e=item['event']
            if item['status']=='pending' and (t>=e.get('start',math.inf) or self.damage>=e.get('after_damage',math.inf)):
                item.update(start=t,status='active');self.events.append({'time':round(t,3),'event':e['kind']+' started','id':e['id']})
                if e.get('graph'):item['graph']=QTEGraph(e['graph'],t,t+e['duration'])
            if item['status']!='active':continue
            if item['graph']:
                item['graph'].advance(t)
                if item['graph'].status=='failed':
                    item['status']='failed';item['targets']=copy.deepcopy(item['graph'].events)
                    self.events.append({'time':round(t,3),'event':'QTE failed','id':e['id']})
                    if e.get('on_fail','unknown') in ('wipe','unknown'):self.stopped=True
                    else:item['downtime_end']=t+e.get('failure_downtime',0)
                    continue
            if e.get('until_qte') and self.states.get(e['until_qte'],{}).get('status')=='passed':
                item['status']='complete';continue
            if t>=item['start']+e['duration']-1e-9:
                if e['kind']=='qte':
                    unknown=any(x.get('hp') is None for x in e['targets'])
                    item['status']='unknown' if unknown else 'failed'
                    self.events.append({'time':round(t,3),'event':'QTE '+item['status'],'id':e['id']})
                    consequence=e.get('on_fail','unknown')
                    if unknown or consequence in ('wipe','unknown'):self.stopped=True
                    elif consequence=='downtime':item['downtime_end']=t+e.get('failure_downtime',0)
                else:item['status']='complete'
                continue
            if e['kind'] in ('invulnerable','cover'):self.waiting=True
            if e['kind']=='qte':
                if self.active is not None:raise ValueError('Overlapping QTEs require a combined target sequence.')
                self.active=item
        if self.blocks('untargetable') and self.active is None:self.waiting=True
        if any(t<x.get('downtime_end',0) for x in self.states.values()):self.waiting=True
        stages=[x for x in self.states.values() if x['status']=='active' and x['event']['kind']=='stat_stage']
        self.enemy_def=max(stages,key=lambda x:x['event'].get('after_damage',0))['event']['enemy_def'] if stages else None

    def blocks(self,kind):
        return any(x['status']=='active' and x['event']['kind']==kind for x in self.states.values())

    def follows_aim(self,caster,controller=None,full_burst_follow=True):
        """Only the player aims off burst, unless an active kit grants Focus Fire."""
        controller=controller or getattr(self,'aim_controller',None)
        if caster==controller or (full_burst_follow and self.frame.get('full_burst')):return True
        bm=getattr(self,'bm',None)
        if bm and controller is not None:
            for ab in bm._active:
                if ab.effect.get('stat')!='focus_fire' or self.time>=ab.expires_at:continue
                if bm.state.get('hp',{}).get(ab.caster,1)<=0:continue
                targets=ab.target_chars if ab.target_chars is not None else bm._resolve_lazy(ab)
                if caster not in targets:continue
                # Focusing means a live aim point, not Full Burst or controlling
                # the support herself. Other conditions retain their real lifetime.
                conditions=[c for c in ab.effect.get('trigger',{}).get('condition',[]) if c!='focusing']
                if conditions and not bm._runtime_condition_ok(conditions,ab.caster,caster,caster,self.time):continue
                return True
        return False

    def record_part_aim(self,part,caster,amount):
        if amount<=0 or self.frame.get('full_burst'):return
        controller=getattr(self,'aim_controller',caster)
        focused=caster!=controller and self.follows_aim(caster)
        key=(controller,part)
        if self.control_plan and (self.control_plan[-1]['unit'],self.control_plan[-1]['part'])==key and self.time-self.control_plan[-1]['end']<=2:
            row=self.control_plan[-1]
        else:
            row=dict(unit=controller,part=part,start=round(self.time,3),end=round(self.time,3),damage=0,focus_fire=False)
            self.control_plan.append(row)
        row['end']=round(self.time,3);row['damage']+=round(amount);row['focus_fire']|=focused

    def target(self,caster,weapon,element):
        q=self.active
        if not q:return None
        e=q['event']
        if q['graph']:
            target=q['graph'].aim(self.time)
            if target is None:return None
            if q.get('graph_target')!=target['id']:
                q['controller']=None;q['graph_target']=target['id']
        else:target=e['targets'][q['index']]
        controller=e.get('controller')
        if controller=='auto':
            # Select the first eligible shooter ready to fire, then keep aim on
            # this circle. No average-DPS shortcut or automatic QTE success.
            eligible=(not target.get('element') or target['element'] in self.element_access.get(caster,[element])) and (not target.get('weapons') or weapon in target['weapons'])
            if q['controller'] is None and eligible:q['controller']=caster
            controller=q['controller']
        # One specified aim controller; FB may explicitly redirect the whole team.
        if not self.follows_aim(caster,controller,e.get('full_burst_follow',False)):return None
        return target

    def resolve(self,caster,element,weapon,hit_type,calculate,args):
        if self.enemy_def is not None:args=dict(args,enemy_def=self.enemy_def)
        normal=hit_type.get('is_normal_atk',False) or hit_type.get('is_weapon_mode_skill',False)
        target=self.target(caster,weapon,element) if normal else None
        if target is not None:
            args=dict(args);args['enemy_def']=target.get('def',args['enemy_def']);args['hit_type']=dict(hit_type,is_core=False,core_prob=0)
        result=calculate(**args)
        if self.stopped or self.blocks('invulnerable'):
            result['damage']=0;return result
        if target is not None:
            q=self.active;e=q['event']
            eligible=(not target.get('element') or target['element'] in self.element_access.get(caster,[element])) and (not target.get('weapons') or weapon in target['weapons'])
            damage=result['damage'] if eligible else 0
            if target.get('hit_count'):damage=1 if eligible and damage>0 else 0
            if target.get('first_hit_only') and q['attempted']:damage=0
            if eligible:q['attempted']=True
            q['dealt']+=damage
            if q['graph']:
                dealt=q['graph'].hit(target['id'],damage,self.time)
                q['targets']=copy.deepcopy(q['graph'].events)
                if q['graph'].status=='passed':
                    q['status']='passed';self.active=None
                    self.events.append({'time':round(self.time,3),'event':'QTE passed','id':e['id']})
                result['damage']=round(dealt*target.get('body_transfer',0))
                self.damage+=result['damage']
                return result
            if target.get('hp') is not None and q['dealt']>=target['hp']:
                q['targets'].append({'damage':q['dealt'],'time':round(self.time,3),'controller':q['controller'] or e['controller']})
                q['index']+=1;q['dealt']=0;q['attempted']=False;q['controller']=None
                if q['index']==len(e['targets']):
                    q['status']='passed';self.active=None
                    self.events.append({'time':round(self.time,3),'event':'QTE passed','id':e['id']})
            # Interruption-target damage is separate from body damage unless verified transfer is supplied.
            result['damage']=round(damage*target.get('body_transfer',0))
        else:
            if self.blocks('untargetable') and not hit_type.get('is_dot'):result['damage']=0
            for item in self.states.values():
                e=item['event']
                if item['status']=='active' and e['kind']=='barrier' and e['element'] not in self.element_access.get(caster,[element]):result['damage']=0
        self.damage+=result['damage']
        return result

    def report(self):
        return {'events':self.events,'stopped':self.stopped,'simulated_until':round(self.time,3),'control_plan':copy.deepcopy(self.control_plan),'off_burst_controller':self.aim_controller_override or getattr(self,'aim_controller',None),
                'checks':[{'id':x['event']['id'],'status':x['status'],'targets':x['targets'],'remaining_target_damage':x['dealt']} for x in self.states.values() if x['event']['kind']=='qte'],
                'assumptions':['Automatic QTE aim selects the first eligible shooter ready to fire and follows with the squad during Full Burst. Explicit script controllers override this. Actual shots must meet each target threshold before its deadline.', 'Scripted cover stops firing and new bursts; cover HP, incoming damage and survival are not modeled. Exact aiming errors, interruption-specific buffs and collision geometry are not modeled.']}
