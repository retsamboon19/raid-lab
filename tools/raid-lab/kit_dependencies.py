"""Build-resolved teammate requirements. Presence is never proof of activation."""
from collections import defaultdict
from calculator.buff_manager import WEAPON_CHANGE_STATE


def possible_target(target, caster, recipient, meta):
    """Conservative static eligibility; dynamic rankings are verified in combat."""
    if isinstance(target,list):return any(possible_target(t,caster,recipient,meta) for t in target)
    if not isinstance(target,str):return False
    if target=='self':return caster==recipient
    if target in meta:return target==recipient
    if target.startswith(('enemy','enemies','target','same_target')):return False
    if 'excl' in target and caster==recipient:return False
    m=meta.get(recipient,{})
    if target.startswith('allies_code_weapon:') or target.startswith('allies_code_weapon_leftmost:'):
        p=target.split(':');return m.get('element_code')==p[1] and m.get('weapon_type')==p[2]
    if target.startswith(('allies_code:','allies_code_excl_self:')):return m.get('element_code')==target.split(':')[1]
    if target.startswith(('allies_weapon:','allies_weapon_top_atk:','allies_weapon_excl_self:','allies_burst_casted_weapon:')):return m.get('weapon_type')==target.split(':')[1]
    if target.startswith('allies_class:'):return m.get('class')==target.split(':')[1]
    if 'burst3' in target and str(m.get('burst_stage'))!='3':return False
    if target.startswith('allies_top_base_charge_time:') and not m.get('charge_time'):return False
    return target.startswith(('all_allies','allies'))


class KitDependencies:
    def __init__(self,effects,meta,catalog):
        self.effects,self.meta,self.catalog=effects,meta,catalog
        self.requirements=[]
        stats=defaultdict(list);names=defaultdict(list)
        for n,kit in effects.items():
            for e in kit:
                if e.get('stat'):stats[e['stat']].append((n,e))
                if e.get('name') and e.get('type') in ('buff','weapon_change'):names[e['name']].append((n,e))
        seen=set()
        def add(n,e,kind,key,options,target=None):
            signature=(n,e.get('name'),e.get('stat'),kind,key)
            if signature in seen:return
            seen.add(signature)
            providers=sorted({p for p,pe in options if possible_target(pe.get('target','self'),p,n,meta)})
            self.requirements.append({'unit':n,'effect':e.get('name'),'stat':e.get('stat'),
                'kind':kind,'key':key,'providers':providers,'recipient':target or n,
                'timing':e.get('trigger',{}).get('timing',[]),
                'conditions':e.get('trigger',{}).get('condition',[])})
        for n,kit in effects.items():
            local_states={e.get('name') for e in kit if possible_target(e.get('target','self'),n,n,meta)}
            if any(e.get('type')=='weapon_change' for e in kit):local_states.add(WEAPON_CHANGE_STATE)
            for e in kit:
                target=e.get('target','self')
                for t in target if isinstance(target,list) else [target]:
                    if t in meta and t!=n:
                        add(n,e,'named_ally',t,[(t,{'target':n})],target=t)
                trigger=e.get('trigger',{})
                for timing in trigger.get('timing',[]):
                    if timing=='event:heal_received':
                        add(n,e,'healing','direct healing',stats['heal_hp_pct']+stats['lifesteal_pct'])
                    elif timing=='event:cover_heal_received':add(n,e,'cover','cover repair',stats['cover_heal_pct'])
                    elif timing=='event:shield_applied':add(n,e,'shield','individual shield',stats['shield_from_max_hp_pct'])
                    elif timing.startswith('event:stat_applied:'):
                        stat=timing.split(':',2)[2];add(n,e,'stat',stat,stats[stat])
                    elif timing.startswith('event:') and timing[6:] in names:
                        add(n,e,'state_event',timing[6:],names[timing[6:]])
                for condition in trigger.get('condition',[]):
                    if condition=='squad_ally_exists':
                        squad=meta.get(n,{}).get('squad')
                        add(n,e,'squad',squad,[(p,{'target':n}) for p in effects if p!=n and squad and meta.get(p,{}).get('squad')==squad])
                    elif condition=='during_shield':add(n,e,'shield','active shield',stats['shield_from_max_hp_pct']+stats['shared_shield_from_max_hp_pct'])
                    elif condition.startswith('self_state:') and condition.split(':',1)[1] not in local_states:
                        state=condition.split(':',1)[1];add(n,e,'external_state',state,names[state])
                    elif condition.startswith('self_stat_above:'):
                        stat=condition.split(':')[1];add(n,e,'stat_threshold',stat,stats[stat])

    def packages(self):
        return list(dict.fromkeys((r['unit'],p) for r in self.requirements for p in r['providers'] if p!=r['unit']))

    def inspect(self,team,result=None):
        rows=[]
        buff_events=getattr(getattr(result,'log',None),'buff_events',[]) or []
        instant_events=getattr(getattr(result,'log',None),'instant_events',[]) or []
        for r in self.requirements:
            if r['unit'] not in team:continue
            providers=[p for p in r['providers'] if p in team]
            activations=[e for e in [*buff_events,*instant_events]
                         if e.caster==r['unit'] and e.name==r['effect']
                         and (not r['stat'] or e.stat==r['stat'])
                         and getattr(e,'kind','activate')=='activate'
                         and (r['kind']!='named_ally' or getattr(e,'target',None)==r['recipient'])]
            status=('activation observed' if activations else 'not activated') if result is not None else 'provider present; activation unverified'
            if not providers:status='missing enabler'
            rows.append({**r,'present_providers':providers,'status':status,'activations':len(activations),
                         'qualification':'This describes an individual skill effect, not a ban on the whole unit. Timing, target selection and uptime still matter.'})
        return rows

    def repairs(self,team,available,weights,valid,checks=()):
        """Reserve missing enablers even when their personal damage ranks low."""
        active={(r['unit'],r['effect'],r['kind']) for r in checks if r['status']=='activation observed'}
        proposals=[];seen=set()
        for r in self.requirements:
            unit=r['unit']
            if unit not in team or (unit,r['effect'],r['kind']) in active:continue
            for provider in sorted((p for p in r['providers'] if p in available and p not in team),key=lambda p:weights[p],reverse=True)[:3]:
                options=[]
                for outgoing in team:
                    if outgoing==unit:continue
                    candidate=[provider if n==outgoing else n for n in team]
                    if valid(candidate):options.append((weights[outgoing],outgoing,candidate))
                for _,outgoing,candidate in sorted(options)[:1]:
                    key=frozenset(candidate)
                    if key in seen:continue
                    seen.add(key);proposals.append({'members':candidate,'consumer':unit,'incoming':provider,'outgoing':outgoing,'kind':r['kind']})
        return proposals
