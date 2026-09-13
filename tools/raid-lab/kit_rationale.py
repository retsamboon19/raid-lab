"""Build-resolved skill explanations for every supported unit, independent of pair names."""
from collections import defaultdict

MEANING = {
 'atk_pct':('ATK','changes attack power used by attack-scaling damage'),
 'atk_caster_based_pct':('caster-based ATK','adds attack based on this support’s own ATK; the support’s investment matters'),
 'atk_dmg_pct':('attack damage','amplifies damage through a separate modifier from ATK'),
 'received_dmg_pct':('damage taken','makes the enemy take more damage, helping teammates attacking that target'),
 'reload_speed_pct':('reload speed','reduces firing interruptions and lets attack-count effects resume sooner'),
 'charge_speed_pct':('charge speed','lets charged weapons complete charges sooner, subject to charge-speed limits'),
 'charge_speed_caster_based_pct':('caster-based charge speed','supports charged attacks using the caster’s charge-speed basis'),
 'charge_dmg_pct':('charged damage','strengthens charged shots; ordinary uncharged attacks do not gain this benefit'),
 'core_dmg_pct':('core damage','strengthens core hits, with no benefit to body hits'),
 'crit_rate':('critical chance','increases how often eligible hits receive critical damage'),
 'crit_dmg':('critical damage','increases the damage of critical hits rather than all hits'),
 'element_bonus_pct':('element damage','strengthens elemental-advantage damage; its value depends on the enemy’s code'),
 'part_dmg_pct':('part damage','specializes in damaging boss parts; a body-only estimate cannot value the part-breaking benefit'),
 'intercept_dmg_pct':('interruption damage','helps damage interruption targets; a QTE still needs its actual HP, timing and targeting modeled'),
 'pierce_enabled':('piercing attacks','can hit aligned targets or parts; the benefit depends on encounter geometry'),
 'pierce_dmg_pct':('pierce damage','strengthens eligible piercing damage rather than every attack'),
 'dot_dmg_pct':('damage over time','amplifies ongoing damage effects rather than unrelated direct shots'),
 'split_dmg_pct':('distributed damage','amplifies distributed-damage attacks; enemy count changes how that damage is shared'),
 'normal_atk_dmg_pct':('normal attacks','strengthens ordinary weapon attacks rather than every skill'),
 'max_ammo_pct':('magazine size','changes time between reloads and last-bullet triggers'),
 'max_ammo_flat':('magazine size','adds ammunition capacity, delaying reloads but potentially delaying last-bullet skills'),
 'ammo_charge_pct':('ammunition refill','restores ammunition without a normal reload, extending firing but delaying empty-magazine triggers'),
 'ammo_charge_flat':('ammunition refill','adds ammunition directly, changing the next reload or last-bullet timing'),
 'burst_cooldown_reduce':('burst cooldown reduction','reduces waiting for burst skills; it does not supply the gauge needed to start a chain'),
 'burst_charge_pct':('burst gauge','helps fill the gauge needed to start a burst chain; cooldown readiness is still required'),
 'burst_charge_speed_pct':('burst generation','improves gauge generation so the team can become ready to burst sooner'),
 'heal_hp_pct':('healing','restores HP to sustain a fight and can enable healing-triggered teammate skills'),
 'lifesteal_pct':('lifesteal','turns damage dealt into recovery, so healing depends on continued eligible damage'),
 'cover_heal_pct':('cover repair','restores cover for defensive use and can enable cover-recovery-triggered teammate skills'),
 'shield_from_max_hp_pct':('individual shield','adds protection and can enable shield-application-triggered skills on the recipient'),
 'shared_shield_from_max_hp_pct':('shared shield','adds shared protection; it must not be assumed to satisfy every individual-shield interaction'),
 'def_pct':('DEF','changes mitigation of attacks that use defense; it does not establish survival against lethal mechanics'),
 'def_caster_based_pct':('caster-based DEF','adds defense based on the support’s build'),
 'max_hp_pct':('maximum HP','increases the HP pool and may affect HP-scaling effects'),
 'taunt':('taunt','redirects attacks that respect taunt, protecting teammates while concentrating danger on the taunter'),
 'invincible':('invulnerability','protects its recipient during the active window, rather than protecting the whole team indefinitely'),
 'undying':('survival protection','can keep its recipient alive during the effect window; timing and targeting matter'),
 'accuracy_pct':('accuracy','changes weapon spread and therefore the ability to hit small targets or cores'),
 'attack_speed_pct':('attack speed','changes shot frequency and the timing of attack-count effects'),
 'infinite_ammo':('unlimited ammunition','allows continued firing during its window without ordinary magazine exhaustion'),
 'fullburst_duration':('Full Burst duration','changes the damage window and when the next rotation can begin'),
 'stun':('stun','can interrupt susceptible enemies; bosses must not be assumed susceptible'),
}

def trigger_text(effect, level):
    timing=effect.get('trigger',{}).get('timing',[])
    labels={'passive':'while its passive conditions hold','battle_start':'at battle start','burst_cast':'when this unit bursts',
            'full_burst_start':'when Full Burst starts','full_burst_end':'when Full Burst ends',
            'last_bullet':'when its last-bullet trigger occurs','event:heal_received':'when this unit receives healing',
            'event:shield_applied':'when a shield is applied to this unit','event:cover_heal_received':'when its cover is repaired',
            'full_charge_fire':'when a fully charged shot is fired','full_charge_hit':'when a fully charged shot hits'}
    out=[]
    for t in timing:
        if t in labels:out.append(labels[t])
        elif t.startswith('on_attack_count:'):
            count=t.split(':',1)[1].replace('{0}',str(effect.get('trigger_values',{}).get(str(level),'the required number of')))
            out.append('after '+count+' normal attacks')
        elif t.startswith('every:'):out.append('every '+t.split(':',1)[1])
        elif t.startswith('burst_cast_count:'):out.append('on burst-count step '+t.split(':',1)[1])
        elif t.startswith('full_burst_start_count:'):out.append('on Full Burst-count step '+t.split(':',1)[1])
        else:out.append('when its additional skill trigger is met')
    return ', '.join(dict.fromkeys(out)) or 'under its skill trigger'

def build_kit_reports(team, roster, catalog, effects, result, settings):
    output={}; buffs=getattr(result.log,'buff_events',[])
    for n in team:
        rows=[];unexplained=set()
        for e in effects[n]:
            stat=e.get('stat','');kind=e.get('type');source=e.get('source','');slot=source[-1:] if source[-1:] in ('1','2','3') else '1'
            lv=roster[n]['build']['skill_levels'][slot]
            if stat in MEANING:title,benefit=MEANING[stat]
            elif kind=='damage':
                title='skill damage';benefit='adds '+('damage over time' if 'dot' in stat else 'distributed damage' if 'split' in stat else 'direct skill damage')+' to its eligible targets'
            elif kind=='weapon_change':title='weapon transformation';benefit='changes the weapon attack pattern to '+e.get('weapon_type','a special weapon')+', so support must suit that attack pattern'
            else:
                if stat:unexplained.add(stat)
                continue
            target=e.get('target','self');target=target if isinstance(target,str) else 'multiple_skill_targets';recipients=sorted({b.target for b in buffs if b.caster==n and b.kind=='activate' and b.stat==stat and getattr(b,'name',None)==e.get('name') and b.target in team})
            target_text={'self':catalog[n]['name'],'all_allies':'the team','all_enemies':'all enemies','target':'the current target','multiple_skill_targets':'the skill’s multiple target groups'}.get(target)
            if target.startswith('allies_top_atk:'):target_text='the '+target.split(':')[-1]+' highest-ATK allies'
            if target.startswith('allies_lowest_hp:'):target_text='the '+target.split(':')[-1]+' lowest-HP allies'
            if target.startswith('allies_weapon:'):target_text=target.split(':')[-1]+' teammates'
            if target=='all_allies_burst_casted':target_text='allies who used a burst in the chain'
            if target=='all_allies_burst_not_casted':target_text='allies who did not use a burst in the chain'
            target_text=target_text or 'the skill’s selected targets'
            condition=[]
            for c in e.get('trigger',{}).get('condition',[]):
                if c.startswith('self_hp_above:'):condition.append('requires own HP above '+c.split(':')[-1]+'%; incoming damage can disable it')
                elif c.startswith('self_hp_below:'):condition.append('requires own HP below '+c.split(':')[-1]+'%; a full-HP model can miss it')
                elif c=='during_shield':condition.append('requires a shield to remain active')
                elif c=='squad_ally_exists':condition.append('requires another member of the same in-game squad')
                else:condition.append('an additional skill condition must be satisfied')
            if stat=='core_dmg_pct' and not settings.get('core_px'):condition.append('no exposed core in this target model, so no damage benefit here')
            if stat in ('max_ammo_pct','max_ammo_flat','ammo_charge_pct','ammo_charge_flat'):
                last=[catalog[x]['name'] for x in team if 'Last bullet' in catalog[x]['tags']]
                if last:condition.append('changes last-bullet timing for '+', '.join(last))
            if 'burst_cast' in e.get('trigger',{}).get('timing',[]) and not any(b.caster==n and b.event.startswith(('stage:','reenter:')) for b in result.log.burst_log):condition.append('this unit did not burst in this run, so do not credit this burst-only benefit')
            rows.append({'skill':('Burst skill' if slot=='3' else 'Skill '+slot)+' · level '+str(lv), 'mechanic':title,
                         'explanation':trigger_text(e,lv).capitalize()+', '+catalog[n]['name']+' '+benefit+' for '+target_text+'.',
                         'recipients':[catalog[x]['name'] for x in recipients],'conditions':condition})
        output[n]={'skills':rows,'specialist_effects':sorted(unexplained),
                   'coverage':'Primary skill explanations are available. Specialist effects not translated here remain listed in the technical audit; this is not a complete kit certification.' if unexplained else 'All resolved skill effects have explanations.'}
    return output
