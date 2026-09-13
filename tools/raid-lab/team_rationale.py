"""Explain causal skill relationships using resolved kits and observed recipients."""
from collections import defaultdict
from calculator.buff_manager import char_effects
from kit_rationale import build_kit_reports

def explain(team, roster, settings, catalog, result, units):
    names={catalog[n]['name']:n for n in team}
    effects={n:char_effects(n,roster[n]['build']['favorite_stage']) for n in team}
    events=result.log.buff_events
    cards=[]
    def card(title,why,condition,observed,source=None):
        cards.append(dict(title=title,why=why,condition=condition,observed=observed,source=source))
    def observed(n,stat):
        return sorted({e.target for e in events if e.kind=='activate' and e.caster==n and e.stat==stat and e.target in team and e.target!=n})
    def readable(ids):return ', '.join(catalog[n]['name'] for n in ids)
    kits=build_kit_reports(team,roster,catalog,effects,result,settings)
    # Discover trigger-enabler relationships from the active kits, without named-pair rules.
    for recipient in team:
        for event,description in [('event:heal_received','healing'),('event:shield_applied','shield application')]:
            enabled=[e for e in effects[recipient] if event in e.get('trigger',{}).get('timing',[])]
            if not enabled:continue
            providers=set()
            if event=='event:heal_received':
                providers={e['caster'] for e in getattr(result.log,'heal_events',[]) if e.get('triggers_heal_received',True) and e['target']==recipient and e['caster'] in team and e['caster']!=recipient}
            else:
                providers={e.caster for e in events if e.kind=='activate' and e.target==recipient and e.caster in team and e.caster!=recipient and e.stat=='shield_from_max_hp_pct'}
            for provider in sorted(providers):
                from kit_rationale import MEANING
                benefits=sorted({MEANING[e['stat']][0] for e in enabled if e.get('stat') in MEANING})
                if not benefits:continue
                card(catalog[provider]['name']+' enables '+catalog[recipient]['name']+' through '+description,
                     catalog[provider]['name']+' supplies '+description+' to '+catalog[recipient]['name']+', whose active kit uses that event to enable '+', '.join(benefits)+'. This is an enabling relationship, not simply two independent buffs on the same team.',
                     'The effect still depends on its own target and duration rules. '+('Receiving a shield can trigger an effect even if that effect does not require the shield to remain intact.' if event=='event:shield_applied' else 'Healing the wrong ally does not enable this interaction; incoming damage can change healing targets.'),
                     'The enabling event reached this unit in the simulation. See each unit’s skill explanation for beneficiary and condition details.')
    if 'Crown' in names and 'Naga' in names:
        crown,naga=names['Crown'],names['Naga']
        healing=any(e.get('triggers_heal_received',True) and e['caster']==naga and e['target']==crown for e in getattr(result.log,'heal_events',[]))
        shield=any(e.caster==crown and e.target==naga and e.stat=='shield_from_max_hp_pct' and e.kind=='activate' for e in events)
        card('Crown + Naga: healing enables offense; shielding enables core damage' if healing else 'Crown + Naga: shielding and conditional healing synergy',
             'Crown shields Naga, enabling Naga’s shield-triggered team core-damage buff. Naga’s normal attacks provide healing and cover repair without using Burst II. Direct healing received by Crown can enable her team attack-damage buff; recovery redistributed by HP sharing cannot. Crown can keep the Burst II slot for her team damage buff and protection.',
             ('The core-damage part has no value in this run because the target model has no exposed core. ' if not (settings.get('core_px') or settings.get('_observed_core_hits')) else 'Core damage helps only shots that actually hit an exposed core. ')+
             'Naga targets the two lowest-HP allies: Crown must receive healing, not merely share the team. Crown in the first slot wins equal-HP targeting ties. Incoming damage can change those targets.',
             f'Crown shield reached Naga: {"yes" if shield else "no"}. Naga healing reached Crown: {"yes" if healing else "not observed"}. Her burst-only ATK buffs are not credited when Naga stays off burst.',
             None)
    if 'Crown' in names and 'Nayuta' in names:
        card('Nayuta + Crown: shared recovery does not enable Crown’s damage buff',
             'Nayuta supplies passive ATK, core-damage support and shared HP recovery. Crown supplies her own support kit, but Nayuta’s shared recovery cannot activate Crown’s healing-received attack-damage buff. Their combined value must come from the other effects and the selected burst rotation.',
             'Only one Burst II normally activates per rotation. Nayuta needs her Burst for her weapon transformation and much of her personal damage; Crown needs hers for its shield and burst damage buff. Their placement determines which is used.',
             'Shared HP recovery is excluded from healing-received triggers in this simulation.',
             None)
    if 'Blanc' in names and 'Noir' in names:
        blanc=names['Blanc']
        cdr=any(e.caster==blanc and e.stat=='burst_cooldown_reduce' for e in result.log.instant_events)
        card('Blanc + Noir: make Blanc’s long cooldown usable in a sustained rotation',
             'Noir satisfies Blanc’s same-squad condition, enabling Blanc’s personal cooldown reduction after Full Burst. That lets the team reuse Blanc’s healing and enemy damage-taken debuff instead of waiting her full base cooldown. Noir also supplies ATK and ammunition support.',
             'Noir’s ATK support depends on her HP condition. Added ammunition can delay last-bullet skills; the pairing is not automatically ideal for every attacker.',
             'Blanc’s personal cooldown reduction '+('activated in this run.' if cdr else 'did not activate in this run; do not assume a functioning loop.'))
    # Group by actual source/stat/recipient, so top-ATK buffs are never promised to an unselected recipient.
    grouped=defaultdict(set)
    for e in events:
        if e.kind=='activate' and e.caster in team and e.target in team and e.caster!=e.target and isinstance(e.stat,str):
            grouped[e.caster,e.stat].add(e.target)
    meanings={
      'atk_pct':('Attack support','Raises the recipients’ ATK, strengthening damage that scales with their attack.'),
      'atk_caster_based_pct':('Attack support based on the support’s build','Adds ATK based on the caster’s ATK. Investing in the support can therefore improve the attackers’ output as well as their own.'),
      'atk_dmg_pct':('Attack-damage amplification','Amplifies the recipients’ damage through an attack-damage modifier, a different modifier from an ATK increase.'),
      'reload_speed_pct':('Less time reloading','Shortens reload interruptions so weapon damage and attack-count skills can resume sooner. The benefit depends on the recipient’s magazine, reload and firing cycle.'),
      'charge_speed_pct':('Charged-weapon support','Shortens charging for charged weapons, potentially fitting more charged shots into a burst window.'),
      'charge_speed_caster_based_pct':('Charged-weapon support','Provides charge speed using the caster’s charge-speed basis; charged recipients can fit shots into a shorter window.'),
      'charge_dmg_pct':('Stronger charged shots','Raises charged-shot damage for recipients who actually use charged attacks.'),
      'core_dmg_pct':('Exposed-core specialization','Increases damage on core hits; it does not increase ordinary body-hit damage.'),
      'max_ammo_flat':('Longer firing strings','Adds magazine capacity, reducing how frequently the recipients need to reload. More ammunition can also delay last-bullet triggers.'),
      'max_ammo_pct':('Magazine-size interaction','Changes magazine capacity, affecting reload frequency and the timing of last-bullet skills.'),
    }
    for (n,stat),targets in sorted(grouped.items()):
        if stat not in meanings:continue
        title,why=meanings[stat];usable=sorted(targets)
        condition='The recipients below are selected by the engine using this build and rotation; a different ATK ranking or burst order can change them.'
        if 'charge' in stat:
            usable=[x for x in usable if catalog[x]['weapon'] in ('SR','RL') or any(e.get('type')=='weapon_change' and e.get('weapon_type') in ('SR','RL') for e in effects[x])]
            condition='Only charged attacks benefit. Charge-speed caps and weapon changes can reduce the gain; no extra-shot breakpoint is assumed.'
        if stat=='core_dmg_pct' and not (settings.get('core_px') or settings.get('_observed_core_hits')):condition='Inactive damage benefit for this target: no exposed core is modeled. This cannot justify the selection on damage grounds.'
        if not usable:continue
        if stat in ('max_ammo_pct','max_ammo_flat'):
            last=[x for x in usable if 'Last bullet' in catalog[x]['tags']]
            if last:condition='Check the tradeoff for '+readable(last)+': magazine changes alter their last-bullet trigger timing. The full rotation, rather than ammo size alone, decides the result.'
        card(catalog[n]['name']+' → '+readable(usable)+': '+title,why,condition,'This interaction reached these recipients during the full-duration run.')
    leaders=sorted(team,key=lambda n:result.char_total.get(n,0),reverse=True)[:2]
    guide=settings.get('encounter',{}).get('guidance',{})
    for u in units:
        n=u['id'];reasons=[];tags=set(catalog[n]['tags'])
        if n in leaders:reasons.append('Carries a large share of this team’s simulated damage. The surrounding support slots are evaluated together with this attacker’s actual build, rather than ranking their personal DPS independently.')
        if 'CDR' in tags:reasons.append('Provides team cooldown reduction to reduce waiting between burst chains. Gauge generation is a separate constraint, so cooldown reduction alone does not guarantee faster Full Bursts.')
        if 'Healing' in tags:reasons.append('Supplies recovery for sustained fighting'+(': '+guide['healing_reason'] if guide.get('healing_reason') else '.')+' Healing can reduce the need to hide for every nonlethal attack, but cannot rescue a unit from a lethal hit.')
        if 'Cover repair' in tags:reasons.append('Repairs cover so planned defensive cover use has a renewable resource; it does not make attacks that bypass cover safe.')
        if 'Shield' in tags:reasons.append('Adds protection for attacks that shields can block. Shield-piercing mechanics still need another response, and this model does not establish how many hits the shield survives.')
        if not u['burst_times']:reasons.append('Uses the flex slot without spending a burst turn. Only passive or otherwise triggered support is available here; burst-only benefits are not a reason to select this slot.')
        associated=[c['title'] for c in cards if catalog[n]['name'] in c['title']]
        if associated:reasons.append('Team interactions: '+'; '.join(associated[:3])+'.')
        u['kit_explanation']=kits[n]
        u['reasons']=reasons+u['reasons']
    return {'overview':'This allocation concentrates modeled damage in '+readable(leaders)+', with the remaining slots supplying the burst chain and support described below. It is selected from the allocations actually simulated, not from unit tier labels.',
            'interactions':cards,'kit_reports':kits,'boss_fit':guide.get('summary','No boss-specific support rule has been verified for this target.'),
            'allocation_note':'In a five-team raid, using a support here removes them from the other four teams. A strong pair is kept only when the tested combined allocation wins; pair reputation alone does not prove the best allocation.' if settings.get('teams',1)>1 else 'Only this team is being optimized; five-team resource allocation is not part of this result.'}
