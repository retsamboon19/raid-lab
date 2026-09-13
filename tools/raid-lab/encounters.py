"""Versioned encounter facts and explicitly separated modeling assumptions.
No guessed phase timestamps, health values, or museum buff multipliers.
"""
import copy
import math
import re
import json
from pathlib import Path
from bisect import bisect_right

CHECKED = "2026-09-10"
MODEL_REVISION = "complete-roster-v1"
MUSEUM_SOURCE = "https://gamewith.jp/nikke/article/show/573385"
ADVANTAGE = {"Fire":"Wind", "Wind":"Iron", "Iron":"Electric", "Electric":"Water", "Water":"Fire"}

def profile(key, name, group, weakness, **extra):
    return dict(id=key, name=name, group=group, weakness=weakness,
        enemy_element=ADVANTAGE.get(weakness,"Neutral"), checked_at=CHECKED,
        status="Partial model", sources=[], facts={}, **extra)

BOSSES = [
    profile("sr40", "Luxurious Spider", "Past Solo Raid", "Fire", raid=40, latest_verified=True,
        period="20–27 Aug 2026", barrier_element="Fire", preferred=["rapid_fire", "AoE"]),
    profile("sr39", "Island Eater", "Past Solo Raid", "Iron", raid=39,
        barrier_element="Iron", preferred=[]),
]
BOSSES[0]["sources"] = ["https://enikk.app/soloraid/40", "https://note.com/shiro_gov/n/n47f9cfbb8e86"]
BOSSES[0]["facts"] = {
    "core":False, "egg_sac_hp_approx":58660000,
    "barrier":"Only Fire deals damage while summoned adds maintain the barrier.",
    "attacks":["Highest-ATK rifle targeting", "Random lasers", "Interceptible missiles",
        "Team laser", "Add summons and enraged attack increase", "Single-unit vision obstruction",
        "Cover-piercing laser with interruption check", "Egg spawns", "Team slam"],
    "unmodeled":["Add hit counters and clear times", "Egg destruction and damage transfer", "Barrier timing", "Interruption checks and survival"]}
BOSSES[1]["sources"] = ["https://enikk.app/soloraid/39"]
BOSSES[1]["facts"] = {"barrier":"Saturation attack includes an Iron-only code barrier.",
    "attacks":["Particle cannon", "Interceptible sludge missiles", "Homing lasers", "Team saturation attack", "Highest-ATK vulcan", "Radial barrage", "Stomp interruption"],
    "unmodeled":["Barrier timing", "Interruption checks and survival"]}
for hall, entries in [
    (1, [("mother-whale","Mother Whale","Electric","distributed damage"), ("blacksmith","Blacksmith","Water","core damage"), ("ultra","Ultra","Iron","pierce damage")]),
    (2, [("alteisen","Alteisen","Electric","damage over time"), ("modernia","Modernia","Wind","core damage"), ("storm-bringer","Storm Bringer","Fire","pierce damage")]),
    (3, [("harvester","Harvester","Water","distributed damage"), ("crystal-chamber","Crystal Chamber","Electric","shotgun damage"), ("indivilia","Indivilia","Iron","element advantage damage")]),
]:
    for key, name, weakness, buff in entries:
        p = profile("museum-"+key, name, "Museum · Hall "+str(hall), weakness,
            hall=hall, preferred=["rapid_fire"] if key=="crystal-chamber" else ["AoE"] if key in ("mother-whale","harvester") else [])
        p["sources"] = [MUSEUM_SOURCE]
        p["facts"] = {"buff_category":buff, "buff_multiplier":None,
            "unmodeled":["Museum buff magnitude and weekly rotation", "Core geometry and exposure", "Finite parts", "Phase timing and survival"]}
        BOSSES.append(p)
# Mandatory code barriers belong to the boss variant, not a user DPS filter.
# Harvester's removable add barrier and the barrier-free Museum variants must
# not be confused with mandatory element-locked interruption checks.
MUSEUM_REQUIRED_ELEMENTS={
    'mother-whale':'Electric','blacksmith':'Water','storm-bringer':'Fire',
    'crystal-chamber':'Electric','indivilia':'Iron',
}
for p in BOSSES:
    if p.get('hall'):
        key=p['id'].removeprefix('museum-')
        if key in MUSEUM_REQUIRED_ELEMENTS:
            p['barrier_element']=MUSEUM_REQUIRED_ELEMENTS[key]
            p['facts']['element_requirement']='mandatory'
        else:
            p['facts']['element_requirement']='removable add barrier' if key=='harvester' else 'no mandatory code barrier'
BOSSES.append(profile("training", "Training target", "Practice", "Any", preferred=[]))
for key,name,weakness in [("alteisen","Alteisen","Any"),("gravedigger","Grave Digger","Any"),("blacksmith","Blacksmith","Any"),("chatterbox","Chatterbox","Any"),("modernia","Modernia","Any")]:
    p=profile("special-"+key,name,"Special Interception",weakness,content="special",preferred=[])
    p['sources']=['https://nikke.gg/interception/']
    p['facts']={'unmodeled':['Variant-specific enemy stats and element','HP-triggered phases','Interruption deadlines and target health','Survival']}
    BOSSES.append(p)
for key,name,weakness in [("ultra","Ultra","Iron"),("mirror-container","Mirror Container","Electric"),("kraken","Kraken","Wind"),("harvester","Harvester","Water"),("indivilia","Indivilia","Fire")]:
    p=profile("anomaly-"+key,name,"Anomaly Interception",weakness,content="anomaly",barrier_element=weakness,preferred=[])
    p['sources']=[]
    p['facts']={'unmodeled':['QTE target health and exact deadlines','HP-triggered phases','Boss damage modifiers','Survival']}
    if key=='mirror-container':p['facts'].update(precision_qte=True,charge_check=True,one_hit_check=True,fail_consequence='Squad wipe',untargetable_transition=True)
    if key=='ultra':p['facts'].update(precision_qte=True,fail_consequence='Major damage or squad wipe',phase_trigger='Damage stage and core state')
    BOSSES.append(p)
BOSSES.append(profile('campaign','Non-boss stage','Campaign','Any',content='campaign',preferred=['AoE']))
BY_ID = {p["id"]:p for p in BOSSES}
from raid_boss_combat import PROFILES as RAID_PROFILES
for key in RAID_PROFILES:
    BY_ID[key]['automatic_mechanics']=True
    BY_ID[key]['status']='Automatic fight model'
    if key.startswith('special-'):
        p=BY_ID[key];data=RAID_PROFILES[key]
        p['enemy_element']={100001:'Fire',200001:'Water',300001:'Wind',400001:'Electric',500001:'Iron'}[data['monster']['ElementId'][0]]
        p['weakness']=next(k for k,v in ADVANTAGE.items() if v==p['enemy_element'])
        p['checked_at']='2026-09-14'
        p['facts']={'unmodeled':['Exact spatial movement, projectile travel and incidental part hits','Gameplay calibration'],
                    'qte':'Actual circle HP and deadlines; boss-specific retaliation',
                    'survival':'Finite HP, cover, shields, healing and revival; stops on a squad wipe'}
BY_ID['museum-mother-whale']['automatic_mechanics']=True
BY_ID['anomaly-kraken']['automatic_mechanics']=True
for key,p in BY_ID.items():
    p['critical_part_deadlines']=key in ('museum-mother-whale','anomaly-kraken') or any(
        skill['ControlParts'] and skill['CancelType'].startswith('BrokenParts')
        for skill in RAID_PROFILES.get(key,{}).get('skills',[]))
BY_ID['special-modernia']['critical_part_deadlines']=True
BY_ID['museum-crystal-chamber']['attack_choices']=[
    {'id':'auto','name':'Choose for this squad'},
    {'id':'projectile','name':'Crystal sphere · hit-count check'},
    {'id':'debuff','name':'ATK reduction · can be cleansed'}]
# Part objectives are distinct from elemental QTE access. Until the variant's
# target geometry, HP and animation timing are resolved, they cannot certify a
# break or justify applying a guessed shield/damage multiplier.
BY_ID['museum-mother-whale']['critical_parts'] = [{
    'id':'mother-whale-core', 'part':'Core',
    'objective':'Destroy the core before Ultrasonic Wave buffs the summoned Raptures.',
    'consequence':'An intact core allows the wave to give summoned enemies hit-count protection. Remaining summons increase pressure and maintain the Electric-only code barrier.',
    'alternative':'A summon-clearing strategy must account for hit-count protection and the barrier; failing to break the core is not automatically a failed fight.',
    'status':'unverified', 'hp':None, 'deadline_seconds':None,
    'missing':['Museum-mode core HP', 'First buff activation and core exposure timing', 'Damage actually directed at the core', 'Summon clear time and barrier duration'],
    'evidence':{'checked_at':'2026-09-12', 'source':'https://enikk.app/soloraid/1',
                'local_scripts':['bt_bba001_singleRaid_Museum','bt_bba001_singleRaid_Nolimited'],
                'scope':'Core-dependent branches confirmed in both local Museum trees; raid HP and timestamps are not imported into Museum.'},
}]
MODES=[{'id':'solo','name':'Solo Raid','teams':5}, {'id':'museum','name':'Solo Raid Museum','teams':5},
       {'id':'special','name':'Special Interception','teams':1}, {'id':'anomaly','name':'Anomaly Interception','teams':1},
       {'id':'campaign','name':'Campaign · non-boss stage','teams':1}, {'id':'practice','name':'Practice · one team','teams':1}]
GUIDANCE=json.loads((Path(__file__).parent/'boss-guidance.json').read_text(encoding='utf-8'))
STATIC_DATA=json.loads((Path(__file__).parent/'boss-static-data.json').read_text(encoding='utf-8'))
KRAKEN_STATIC=json.loads((Path(__file__).parent/'kraken-static-data.json').read_text(encoding='utf-8'))
for key,guide in GUIDANCE['profiles'].items():
    BY_ID[key]['guidance']=guide
    if guide.get('barrier_element'):BY_ID[key]['barrier_element']=guide['barrier_element']
from special_guidance import GUIDES as SPECIAL_GUIDES
for key,guide in SPECIAL_GUIDES.items():
    BY_ID['special-'+key]['guidance']=copy.deepcopy(guide)
    BY_ID['special-'+key]['sources']=[guide['source']]

CP_TABLE=json.loads((Path(__file__).parent/'cp-penalty.json').read_text(encoding='utf-8'))['rows']

def cp_penalty(deficit):
    if deficit<=0:return 0.0
    if deficit<CP_TABLE[1][0]:return CP_TABLE[1][1]
    return CP_TABLE[max(0,bisect_right([x[0] for x in CP_TABLE],deficit)-1)][1]

def unit_level(build,settings):
    if settings.get('content_mode')=='anomaly':return min(build['level'],400)
    return settings['level'] if settings['fixed_level'] else build['level']



def cover_plan(raw, duration):
    """Half-open intervals in elapsed seconds. Explicit windows replace total time."""
    mode = raw.get("cover_mode", "total")
    if mode not in ("total", "windows"): raise ValueError("Invalid cover mode.")
    windows=[]
    if mode == "windows":
        value=raw.get("cover_windows_text", "")
        if not isinstance(value,str) or len(value)>2000: raise ValueError("Invalid cover windows.")
        for part in value.split(","):
            if not part.strip(): continue
            match=re.fullmatch(r"\s*(\d+(?:\.\d+)?)\s*[-–]\s*(\d+(?:\.\d+)?)\s*",part)
            if not match: raise ValueError("Use elapsed seconds, for example 25-30, 90-95.")
            a,b=map(float,match.groups())
            if not 0<=a<b<=duration: raise ValueError("Cover windows must be inside the fight, with start before end.")
            windows.append([a,b])
        windows.sort()
        merged=[]
        for a,b in windows:
            if merged and a<=merged[-1][1]: merged[-1][1]=max(b,merged[-1][1])
            else: merged.append([a,b])
        windows=merged
    else:
        val=raw.get("cover_seconds",0)
        if isinstance(val,bool):raise ValueError("Invalid cover time.")
        try:seconds=float(val)
        except (TypeError,ValueError):raise ValueError("Invalid cover time.")
        if not math.isfinite(seconds) or not 0<=seconds<=duration: raise ValueError("Cover time must be between zero and the fight duration.")
        if seconds: windows=[[(duration-seconds)/2,(duration+seconds)/2]]
    seconds=sum(b-a for a,b in windows)
    return dict(cover_mode=mode, cover_seconds=seconds, cover_windows_text=raw.get("cover_windows_text","") if mode=="windows" else "",
        cover_windows=windows, uptime=round(100*(duration-seconds)/duration,2))


def apply_profile(raw, settings):
    key=raw.get("boss_id", "training")
    if not isinstance(key,str) or key not in BY_ID:raise ValueError("Choose a listed boss.")
    p=BY_ID[key]
    inferred='solo' if p.get('raid') else 'museum' if p.get('hall') else p.get('content','practice')
    content=raw.get('content_mode',inferred)
    if content not in {m['id'] for m in MODES}:raise ValueError('Choose a supported content mode.')
    if content!=inferred:raise ValueError('This boss does not belong to the selected content.')
    settings['content_mode']=content
    policy=raw.get('survival_policy','guide')
    if policy not in ('guide','damage-only'):raise ValueError('Invalid survival policy.')
    settings['survival_policy']=policy
    if 'content_mode' in raw:settings['teams']=5 if content in ('solo','museum') else 1
    objective=raw.get('campaign_objective','battle')
    if objective not in ('battle','defense','base-defense'):raise ValueError('Invalid stage objective.')
    settings['campaign_objective']=objective
    deficit=raw.get('cp_deficit',0) if content=='campaign' else 0
    if isinstance(deficit,bool):raise ValueError('Invalid CP deficit.')
    try:deficit=float(deficit)
    except (TypeError,ValueError):raise ValueError('Invalid CP deficit.')
    if not math.isfinite(deficit) or not 0<=deficit<=50:raise ValueError('CP deficit must be between 0 and 50 percent.')
    settings.update(cp_deficit=deficit,stat_penalty=cp_penalty(deficit))
    mode=raw.get("museum_mode","challenge")
    if mode not in ("challenge","no-limit"):raise ValueError("Invalid Museum mode.")
    settings.update(boss_id=key, museum_mode=mode, encounter=copy.deepcopy(p))
    # Server-owned constraint: Any, an off-element selection, damage-only policy
    # or caller-supplied encounter metadata cannot disable this requirement.
    settings['element_locked']=bool(p.get('barrier_element'))
    if settings['element_locked']:settings['element']=p['barrier_element']
    # Defence is an engine baseline, not a verified boss stat. Keep it internal.
    # Body-only comparison avoids inventing pixel geometry or permanent part uptime.
    if key!="training":
        settings.update(enemy_element=p["enemy_element"], **{"def":31784,"core_px":0,"has_parts":False,"optimal_range_weapons":[]})
        settings.update(fixed_level=not (p.get("hall") and mode=="no-limit"),level=400)
    if content=='special':settings.update(fixed_level=True,level=200)
    elif content in ('campaign','anomaly'):settings['fixed_level']=False
    settings.update(cover_plan(raw,settings["duration"]))
    immunity=raw.get('invulnerable_windows_text','')
    settings['invulnerable_windows_text']=immunity
    settings['invulnerable_windows']=cover_plan({'cover_mode':'windows','cover_windows_text':immunity},settings['duration'])['cover_windows']
    settings["encounter"]["model_revision"]=MODEL_REVISION
    simulation=raw.get('boss_simulation','automatic' if key=='anomaly-kraken' else 'reference')
    if simulation not in ('automatic','reference'):raise ValueError('Invalid boss simulation mode.')
    settings['boss_simulation']=simulation if key=='anomaly-kraken' else 'reference'
    if key=='museum-mother-whale':settings['boss_simulation']='automatic'
    if key in RAID_PROFILES:settings['boss_simulation']='automatic'
    choice=raw.get('boss_attack_choice','auto')
    if choice not in ('auto','projectile','debuff'):raise ValueError('Invalid boss attack choice.')
    settings['boss_attack_choice']=choice if key=='museum-crystal-chamber' else 'auto'
    part_policy=raw.get('boss_part_policy','safe')
    if part_policy not in ('safe','all','body'):raise ValueError('Invalid boss part strategy.')
    settings['boss_part_policy']=part_policy
    policy=raw.get('kraken_target_policy','delay')
    if policy not in ('delay','safe','body'):raise ValueError('Invalid Kraken targeting policy.')
    settings['kraken_target_policy']=policy
    settings['require_critical_parts']=bool(settings.get('require_critical_parts') and p.get('critical_part_deadlines') and settings['boss_simulation']=='automatic')
    if settings['require_critical_parts']:
        # A body-only comparison contradicts the requested part-break objective.
        if settings['boss_part_policy']=='body':settings['boss_part_policy']='safe'
        if settings['kraken_target_policy']=='body':settings['kraken_target_policy']='safe'
    settings["encounter"]["modeled"]=["Element advantage", "Roster investment", "Burst rotation", "Planned squad cover"]
    if key in STATIC_DATA['profiles']:
        data=STATIC_DATA['profiles'][key]['modes'][mode]
        settings['encounter']['stat_phases']=copy.deepcopy(data['level_changes'])
        settings['encounter']['static_source_sha256']=STATIC_DATA['source_sha256']
        settings['encounter']['modeled'].append('Table-derived base defence and damage-triggered level changes')
    if key=='anomaly-kraken':
        settings['encounter']['stat_phases']=copy.deepcopy(KRAKEN_STATIC['level_changes'])
        settings['encounter']['static_source_sha256']=KRAKEN_STATIC['source_sha256']
        settings['encounter']['modeled'].append('Offline Kraken base defence and stage progression')
    if key=='museum-mother-whale':
        from mother_whale_combat import DATA,STATS
        objective=settings['encounter']['critical_parts'][0]
        monster=DATA['mode_monsters'][mode]
        row=STATS[(monster['StatenhanceId'],DATA['modes'][mode]['MonsterStageLv'])]
        settings['encounter']['stat_phases']=[dict(after_damage=s['ConditionValueMin'],enemy_def=STATS[(monster['StatenhanceId'],s['MonsterStageLv'])]['LevelDefence']*monster['DefenceRatio']/10000) for s in DATA['stages'] if s['Group']==DATA['modes'][mode]['MonsterStageLvChangeGroup']]
        objective.update(status='modeled',hp=row['LevelHp']*.2,missing=[])
        settings['encounter']['modeled'].extend(['Core destruction and Ultrasonic Wave','Finite summons and hit-count protection','Electric barrier removal','Incoming attacks, healing and finite cover'])
    if key in RAID_PROFILES:
        data=RAID_PROFILES[key];variant=data['modes'].get(mode,data['modes']['challenge'])
        stats={(s['GroupId'],s['Lv']):s for s in data['stats']};monster=data['mode_monsters'].get(mode,data['monster'])
        settings['encounter']['stat_phases']=[dict(after_damage=s['ConditionValueMin'],enemy_def=stats[(monster['StatenhanceId'],s['MonsterStageLv'])]['LevelDefence']*monster['DefenceRatio']/10000) for s in data['stages'] if s['Group']==variant['MonsterStageLvChangeGroup']]
        settings['encounter']['modeled'].extend(['Boss attack branches and player choices','Finite parts and interruption targets','Incoming attacks and squad survival'])
    return settings


def config(settings, duration):
    # Quick passes retain the actual first 30 seconds of the selected schedule.
    out={"stat_multiplier":1-settings.get("stat_penalty",0)/100,"planned_cover_windows":[[a,min(b,duration)] for a,b in settings["cover_windows"] if a<duration]}
    script=copy.deepcopy(settings['encounter'].get('script',[]))
    script.extend(dict(id='stat-stage-'+str(i),kind='stat_stage',duration=duration,**phase)
                  for i,phase in enumerate(settings['encounter'].get('stat_phases',[])))
    script.extend({'id':'user-immunity-'+str(i),'kind':'invulnerable','start':a,'duration':b-a} for i,(a,b) in enumerate(settings.get('invulnerable_windows',[])))
    if script:
        from mechanics import EncounterRuntime
        out['encounter_runtime']=EncounterRuntime(script,duration=duration)
    if settings['boss_id']=='anomaly-kraken' and settings.get('boss_simulation')=='automatic':
        from kraken_combat import KrakenRuntime
        out['encounter_runtime']=KrakenRuntime(script,duration,target_policy=settings.get('kraken_target_policy','delay'))
    if settings['boss_id']=='museum-mother-whale':
        from mother_whale_combat import MotherWhaleRuntime
        out['encounter_runtime']=MotherWhaleRuntime(script,duration,mode=settings['museum_mode'])
    if settings['boss_id'] in RAID_PROFILES:
        from raid_boss_combat import RaidBossRuntime
        runtime=RaidBossRuntime
        if settings['boss_id'].startswith('special-'):
            from special_interception import SpecialInterceptionRuntime
            runtime=SpecialInterceptionRuntime
        out['encounter_runtime']=runtime(script,duration,key=settings['boss_id'],mode=settings['museum_mode'],choice_policy=settings.get('boss_attack_choice','auto'),part_policy=settings.get('boss_part_policy','safe'))
    if out.get('encounter_runtime'):
        out['encounter_runtime'].aim_controller_override=settings.get('_aim_controller')
    return out


def notes(settings):
    p=settings["encounter"]
    if p['id'].startswith('special-'):
        from special_interception import ASSUMPTIONS
        return list(ASSUMPTIONS)
    if p['id'] in RAID_PROFILES:
        from raid_boss_combat import ASSUMPTIONS
        return list(ASSUMPTIONS)
    if p['id']=='museum-mother-whale':
        from mother_whale_combat import ASSUMPTIONS
        return list(ASSUMPTIONS)
    result=["Body-target estimate with internal baseline defence; exact boss stats, exposed cores, finite parts, range changes, phase barriers and incoming attacks are not yet calibrated.",
        "Entered invulnerability windows stop firing and block damage, including ongoing effects. They do not automatically describe the complete boss script.",
        "Cover pauses all five units' firing and new burst activations. Reloads, cooldowns, existing buffs and effect damage continue; DPS uses the full fight duration."]
    if settings["cover_mode"]=="total" and settings["cover_seconds"]:
        result.append("Total cover time is placed as one break in the middle of the fight. Use exact windows to match your run; timing changes the result.")
    if p.get("barrier_element"):
        result.append(p["barrier_element"]+" is automatically required on every team. Search also requires a substantial matching damage contributor of any class or Burst stage. This composition safeguard does not prove sufficient circle damage before the deadline; uncalibrated QTEs remain unverified.")
    if p.get("hall"):
        result[0]="Museum base defence follows the local game tables and damage-triggered level changes. Enemy passive modifiers, exposed cores, finite parts, range changes, phase barriers and incoming attacks are not yet calibrated."
        result.append("Museum buffs and weekly modifiers are not applied: their exact values are unverified. This is a team comparison, not a Museum score prediction.")
    for objective in p.get('critical_parts',[]):
        result.append(objective['part']+' objective unverified: '+objective['objective']+' '+objective['consequence']+' Body-target DPS and burst timing do not establish this part break.')
    if p['id']=='anomaly-kraken':
        result[0]='Kraken base defence uses its offline monster table and damage-triggered levels. Enemy passive modifiers, cores, finite tentacles, attacks and survival remain unverified.'
        result.extend(KRAKEN_STATIC['unresolved'])
        if settings.get('boss_simulation')=='automatic':
            from kraken_combat import MODEL_ASSUMPTIONS
            result=list(MODEL_ASSUMPTIONS)+KRAKEN_STATIC['unresolved']
    return result


def assessment(settings,team,catalog):
    p=settings['encounter'];facts=p.get('facts',{});checks=[]
    if p['id']=='training':return {'status':'Practice only','checks':[],'clear_verified':False}
    checks.append({'name':'Boss availability / phase timeline','status':'assumed' if settings.get('invulnerable_windows') else 'unknown','detail':'Entered immunity windows are applied; unrecorded phases remain unverified.' if settings.get('invulnerable_windows') else 'Exact phase transitions are not calibrated.'})
    checks.append({'name':'QTE damage before deadline','status':'unknown','detail':'Target HP and deadlines are missing; team DPS is not evidence of a pass.'})
    for objective in p.get('critical_parts',[]):
        checks.append({'name':objective['part']+' before mechanic activation','status':'unknown',
            'detail':objective['objective']+' '+objective['consequence']+' '+objective['alternative']+' Missing: '+', '.join(objective['missing'])+'.'})
    if p.get('barrier_element'):
        present=any(p['barrier_element'] in catalog[n].get('barrier_elements',[catalog[n]['element']]) for n in team)
        checks.append({'name':'Elemental barrier access','status':'pass' if present else 'fail','detail':'Element presence only; damage sufficiency is still unchecked.'})
    if facts.get('precision_qte'):
        present=any(catalog[n]['weapon'] in ('AR','SMG','MG','SR') for n in team)
        checks.append({'name':'Precision aiming option','status':'pass' if present else 'risk','detail':'Red/grey circle execution is not guaranteed by weapon type.'})
    if facts.get('charge_check'):
        present=any(catalog[n]['weapon'] in ('SR','RL') for n in team)
        checks.append({'name':'Charged-shot option','status':'pass' if present else 'fail','detail':'One-hit damage threshold is still unknown.'})
    guide=p.get('guidance',{})
    if guide:
        tags={tag for n in team for tag in catalog[n]['tags']}
        missing=set(guide.get('required_tags',[]))-tags
        checks.append({'name':'Guide support coverage','status':'risk' if missing else 'present','detail':('Missing '+', '.join(sorted(missing))+'. ') if missing else 'Recommended support roles present; strength and timing remain unverified.'})
        exposed=[catalog[n]['name'] for n in team if catalog[n]['element']==guide.get('vulnerable_element')]
        if exposed:checks.append({'name':'Incoming element disadvantage','status':'risk','detail':', '.join(exposed)+' take increased elemental damage in this Anomaly variant. Strong builds or specific protection may still justify them.'})
    checks.append({'name':'Survival after failed checks','status':'unknown','detail':'Incoming attacks and deaths are not calibrated.'})
    return {'status':'Mechanics unverified','checks':checks,'clear_verified':False}


def follows_guide(team,settings,catalog):
    if settings.get('survival_policy')=='damage-only':return True
    guide=settings.get('encounter',{}).get('guidance',{})
    tags={tag for n in team for tag in catalog[n]['tags']}
    if not set(guide.get('required_tags',[]))<=tags:return False
    return all(any(catalog[n]['weapon'] in group for n in team) for group in guide.get('required_weapon_groups',[]))


def support_report(team,settings,catalog):
    g=settings['encounter'].get('guidance')
    if not g:return None
    tags=set(g.get('required_tags',[])+g.get('preferred_tags',[]))
    return {'source':g['source'],'source_name':g['source_name'],'summary':g['summary'],'cover_policy':g['cover_policy'],
            'policy':settings.get('survival_policy','guide'),
            'providers':[{'id':n,'roles':sorted(set(catalog[n]['tags'])&tags)} for n in team if set(catalog[n]['tags'])&tags],
            'warning':'Support presence is not proof of enough healing or shielding. Imported investment is used for comparisons, but incoming damage and optimal cover timing are not calibrated.'}
