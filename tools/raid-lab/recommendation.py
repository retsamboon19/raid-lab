"""Selection rationale derived from recorded events, never generated combat claims."""
from collections import defaultdict
from team_rationale import explain

LABELS = {'atk_caster_based_pct':'caster-based ATK', 'atk_dmg_pct':'attack damage', 'charge_speed_caster_based_pct':'charge speed', 'atk_pct':'ATK', 'attack_dmg_pct':'attack damage', 'core_dmg_pct':'core damage',
          'charge_dmg_pct':'charge damage', 'charge_speed_pct':'charge speed',
          'reload_speed_pct':'reload speed', 'max_ammo_pct':'ammo capacity',
          'crit_rate':'critical rate', 'crit_dmg':'critical damage',
          'lifesteal_pct':'lifesteal', 'shield_from_max_hp_pct':'shield',
          'shared_shield_from_max_hp_pct':'shared shield', 'element_bonus':'element damage'}

def evidence_report(result, team, roster, settings, catalog):
    log=result.log
    settings=dict(settings,_observed_core_hits=any(h.damage>0 and "core" in h.hit_tag for h in getattr(result,"hits",[])))
    automatic=bool(getattr(result,"encounter_report",None) and result.encounter_report.get("model"))
    bursts={n:[round(e.t,2) for e in log.burst_log if e.caster==n and e.event.startswith(('stage:','reenter:'))] for n in team}
    gauge={n:sum(e.amount for e in log.gauge_log if e.caster==n) for n in team}
    gauge_total=sum(gauge.values())
    links=defaultdict(lambda: {'count':0,'first':None})
    for e in log.buff_events:
        if e.kind!='activate' or e.caster not in team or e.target not in team or e.target==e.caster or e.stat not in LABELS:continue
        row=links[(e.caster,e.target,e.stat)]
        row['count']+=1
        if row['first'] is None:row['first']=round(e.t,2)
    warnings=[]; synergy=[]; inactive_healers=[]
    for (source,target,stat),value in sorted(links.items()):
        caveat='Activation is observed; its incremental damage contribution is not isolated.'
        if stat=='core_dmg_pct' and not (settings.get('core_px') or settings.get('_observed_core_hits')):
            caveat='No core is exposed in this target model, so this core-damage buff cannot increase modeled damage.'
        if stat in ('charge_dmg_pct','charge_speed_pct') and catalog[target]['weapon'] not in ('SR','RL'):
            caveat='Recipient has no ordinary charged weapon; benefit requires a separately supported weapon-change effect.'
        if stat in ('lifesteal_pct','shield_from_max_hp_pct','shared_shield_from_max_hp_pct'):
            caveat=('Shield consumption and incoming attacks are modeled with unverified physical conversions; see the combat report.' if automatic else 'Support activation only. Incoming damage and shield consumption are not modeled.')
        synergy.append({'source':source,'target':target,'effect':LABELS[stat],**value,'qualification':caveat})
    units=[]
    for n in team:
        c=catalog[n];b=roster[n]['build'];reasons=[]
        reasons.append(f"Burst {c['burst']}: {len(bursts[n])} recorded casts" + ('; occupies a non-bursting flex slot in this rotation.' if not bursts[n] else '.'))
        if c['element']==settings.get('encounter',{}).get('weakness'):reasons.append('Matches the selected weakness element.')
        barrier=settings.get('encounter',{}).get('barrier_element')
        if barrier and barrier in c['barrier_elements']:reasons.append(f'Provides {barrier} barrier access; this alone does not prove QTE success.')
        roles=set(c['tags']) & {'Healing','Shield','Cover repair','CDR'}
        if roles:reasons.append('Available in this build: '+', '.join(sorted(roles))+'. Availability does not establish sufficient healing or protection.')
        units.append({'id':n,'reasons':reasons,'tags':c['tags'],
                      'damage_share':round(100*result.char_total.get(n,0)/max(1,result.squad_total),2),
                      'gauge_share':round(100*gauge[n]/max(1,gauge_total),2),'burst_times':bursts[n],
                      'skills':b['skill_levels'],'favorite_stage':b['favorite_stage'],
                      'assumptions':roster[n].get('assumptions',[])})
        # Burst-only support cannot justify a mandatory support slot when never cast.
        from calculator.buff_manager import char_effects
        effects=char_effects(n,b['favorite_stage'])
        support=[e for e in effects if (e.get('stat','').startswith('heal_') or e.get('stat')=='lifesteal_pct') and e.get('stat')!='heal_received_pct' and e.get('target')!='self']
        if support and not bursts[n] and all('burst_cast' in e.get('trigger',{}).get('timing',[]) for e in support):
            inactive_healers.append(n)
            warnings.append(f"{c['name']}'s team healing requires their burst, but they never burst in this rotation.")
    fb=[round(e.t,2) for e in log.burst_log if e.event=='full_burst 시작']
    rationale=explain(team,roster,settings,catalog,result,units)
    return {'rationale':rationale, 'available_healers':[n for n in team if 'Healing' in catalog[n]['tags'] and n not in inactive_healers], 'units':units,'synergies':synergy,'warnings':warnings,
            'rotation':{'full_burst_times':fb,'largest_gap':round(max((b-a for a,b in zip(fb,fb[1:])),default=0),2)},
            'evidence':'Damage, gauge and buff activations are observations inside this simulation, not measured gameplay.',
            'unverified':['Incoming attacks, deaths and finite cover/shield health are not calibrated.',
                          ('Guide support roles do not prove survival. Shield depletion is modeled, but the incoming-damage conversion is unverified.' if automatic else 'Guide support roles do not prove survival. Shield-dependent buffs may be optimistic because shields are not consumed.'),
                          'Unscripted boss phases and QTE thresholds remain unknown.']}
