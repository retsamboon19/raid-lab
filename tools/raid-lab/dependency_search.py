"""Discover weak healing-dependent buffs from combat events, without named pairs."""

def healing_dependencies(team,effects,events,duration):
    rows=[]
    for unit in team:
        for effect in effects[unit]:
            if 'event:heal_received' not in effect.get('trigger',{}).get('timing',[]):continue
            if effect.get('type')!='buff' or effect.get('target')=='self':continue
            name,stat=effect.get('name'),effect.get('stat')
            intervals={target:[] for target in team};active={}
            for event in events:
                if event.caster!=unit or event.name!=name or event.target not in intervals:continue
                if event.stat!=stat and not (event.kind=='expire' and event.stat is None):continue
                target=event.target
                if event.kind=='activate':
                    if target in active:
                        a,b=active.pop(target);intervals[target].append((a,min(b,event.t)))
                    active[target]=(event.t,event.expires_at)
                elif event.kind=='expire' and target in active:
                    a,b=active.pop(target);intervals[target].append((a,min(b,event.t)))
            for target,window in active.items():intervals[target].append(window)
            coverage={}
            for target,windows in intervals.items():
                merged=[]
                for a,b in sorted((max(0,a),min(duration,b)) for a,b in windows):
                    if b<=a:continue
                    if merged and a<=merged[-1][1]:merged[-1][1]=max(b,merged[-1][1])
                    else:merged.append([a,b])
                coverage[target]=sum(b-a for a,b in merged)/max(duration,.001)
            rows.append({'unit':unit,'effect':name,'stat':stat,'uptime_by_target':coverage,
                         'uptime':sum(coverage.values())/max(1,len(team))})
    return rows

def healing_repairs(baseline,ids,effects,catalog,weights,valid):
    """Reserve comparisons for direct healers missed by personal-damage ranking.

    This proposes experiments, not compatibility verdicts. Burst timing, healing
    recipients, HP sharing and resulting damage are resolved by the combat engine.
    """
    team=baseline['members'];proposals=[]
    consumers={r['unit'] for r in baseline.get('healing_dependencies',[]) if r['uptime']<.8}
    providers=[n for n in ids if n not in team and any(
        e.get('stat') in ('heal_hp_pct','lifesteal_pct') and e.get('target')!='self'
        for e in effects[n])]
    # Passive direct recovery gets an early comparison; burst-only healing is
    # still tested in active/off-burst orders, never assumed to work off burst.
    providers.sort(key=lambda n:(any(e.get('stat') in ('heal_hp_pct','lifesteal_pct') and e.get('target')!='self' and 'burst_cast' not in e.get('trigger',{}).get('timing',[]) for e in effects[n]),weights[n]),reverse=True)
    for consumer in consumers:
        for provider in providers[:4]:
            options=[]
            for outgoing in team:
                if outgoing==consumer:continue
                candidate=[provider if n==outgoing else n for n in team]
                if valid(candidate):
                    # Prefer replacing a recovery-sharing source: its presence
                    # can prevent even a direct healer enabling the consumer.
                    sharing=any(e.get('stat')=='heal_split' for e in effects[outgoing])
                    options.append((not sharing,weights[outgoing],candidate,outgoing))
            for _,__,candidate,outgoing in sorted(options,key=lambda x:x[:2])[:1]:
                slots=[i for i,n in enumerate(candidate) if catalog[n]['burst']==catalog[provider]['burst']]
                for first in (False,True):
                    order=candidate.copy();position=order.index(provider);slot=slots[0] if first else slots[-1]
                    order[position],order[slot]=order[slot],order[position]
                    if not any(p['members']==order for p in proposals):proposals.append({'members':order,'consumer':consumer,'outgoing':outgoing,'incoming':provider})
    return proposals
