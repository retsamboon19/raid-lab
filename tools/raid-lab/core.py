"""Local roster adapter and bounded search; see README for the empty-cube patch."""
from __future__ import annotations
import copy
import json
import math
import random
import itertools
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent
ENGINE = ROOT.parent / 'nikke-team-builder'
sys.path.insert(0, str(ENGINE))
import encounters
from runner import spec
from calculator.timeline import simulate
from calculator.base_stat import NO_ITEM
from calculator.buff_manager import char_effects
from recommendation import evidence_report
from dependency_search import healing_dependencies,healing_repairs
from kit_dependencies import KitDependencies
import pairing_search
import burst_rotation
import rotation_search
from candidate_ranking import score as candidate_score
from parallel_compute import CandidateExecutor, worker_limit

def read(path):
    return json.loads(path.read_text(encoding='utf-8'))

META = read(ENGINE / 'data/parsed_nikke.json')
SKILLS = read(ENGINE / 'data/parsed_skills.json')
RAW = read(ENGINE / 'scraper/nikke_scraped.json')
DIRECTORY = read(ROOT / 'directory.json')
BY_ID = {int(x['resource_id']): x for x in DIRECTORY}
ELEMENTS = {'작열':'Fire','수냉':'Water','철갑':'Iron','전격':'Electric','풍압':'Wind'}
ELEMENT_KO = {v:k for k,v in ELEMENTS.items()}
WEAK_TO = {'Fire':'Wind','Wind':'Iron','Iron':'Electric','Electric':'Water','Water':'Fire'}
PARTS = ['머리','몸통','팔','다리']
OPTIONS = {'StatAtk':'atk_pct','IncElementDmg':'element_bonus','StatAmmoLoad':'max_ammo_pct','StatCritical':'crit_rate','StatCriticalDamage':'crit_dmg','StatChargeTime':'charge_speed_pct','StatChargeDamage':'charge_dmg_pct','StatAccuracyCircle':'accuracy_pct','StatDef':'def_pct','IncHurtDef':'def_pct'}

def tags_for(name, effects=None):
    effects = SKILLS.get(name, []) if effects is None else effects
    stats = {e.get('stat','') for e in effects}
    tags = []
    if any(e.get('stat')=='burst_cooldown_reduce' and e.get('target')!='self' for e in effects): tags.append('CDR')
    elif 'burst_cooldown_reduce' in stats: tags.append('Personal CDR')
    if any((e.get('stat','').startswith('heal_') or e.get('stat')=='lifesteal_pct') and e.get('stat') != 'heal_received_pct' and e.get('target') != 'self' for e in effects): tags.append('Healing')
    if stats & {'shield_from_max_hp_pct','shared_shield_from_max_hp_pct'}: tags.append('Shield')
    if 'cover_heal_pct' in stats: tags.append('Cover repair')
    if any(e.get('type') == 'damage' and e.get('target') in ('all_enemies','enemies_in_range') for e in effects): tags.append('AoE')
    if any('pierce' in x for x in stats): tags.append('Pierce')
    if any('last_bullet' in json.dumps(e.get('trigger',{})) for e in effects): tags.append('Last bullet')
    if any(e.get('stat') in ('atk_pct','atk_caster_based_pct','atk_dmg_pct','attack_dmg_pct','received_dmg_pct','damage_taken_pct') and e.get('target') != 'self' for e in effects): tags.append('Damage support')
    return tags

CATALOG = []
for name, m in META.items():
    if name.startswith(('_', 'test_')): continue
    d = BY_ID.get(RAW.get(name,{}).get('id'), {})
    CATALOG.append({'id':name,'name':d.get('name_localkey',{}).get('name',name),
        'name_code':d.get('name_code'),'resource_id':RAW.get(name,{}).get('id'),
        'element':ELEMENTS.get(m.get('element_code'),'Unknown'),'burst':str(m['burst_stage']),
        'cooldown':m['burst_cooldown'],'weapon':m['weapon_type'],
        'role': {'화력형':'Attacker','지원형':'Supporter','방어형':'Defender'}.get(m['class'],m['class']),
        'tags':tags_for(name),'supported':bool(SKILLS.get(name)) and not m.get('preview',False)})
CATALOG.sort(key=lambda c:c['name'].lower())
CAT = {x['id']:x for x in CATALOG}
for c in CATALOG:
    c['barrier_elements']=[c['element']]
    for e in SKILLS.get(c['id'],[]):
        if e.get('stat')=='element_code_override' and 'battle_start' in e.get('trigger',{}).get('timing',[]) and not e.get('trigger',{}).get('condition'):
            enemy_element=ELEMENTS.get(e.get('target_code'))
            c['barrier_elements'].extend(k for k,v in WEAK_TO.items() if v==enemy_element)

NAME_MAP = {x['name'].casefold(): x['id'] for x in CATALOG}
CODE_MAP = {str(x['name_code']):x['id'] for x in CATALOG if x['name_code'] is not None}


def resolve_catalog(roster):
    catalog=copy.deepcopy(CAT)
    for n,row in roster.items():
        effects=char_effects(n,row['build']['favorite_stage'])
        catalog[n]['tags']=tags_for(n,effects)
    return catalog

def public_settings(s):
    return {k:v for k,v in s.items() if not k.startswith('_')}

def default_build():
    # Explicit modest assumptions, never the upstream maxed account by accident.
    return {'level':400,'breakthrough':0,'core_enhancement':0,'affinity':1,
        'skill_levels':{'1':1,'2':1,'3':1},
        'equipment':{p:{'tier':NO_ITEM,'level':0,'skills':[]} for p in PARTS},
        'equip_skills':{k:0 for k in spec.DEFAULT_CHAR['equip_skills']},
        'cube':{'name':NO_ITEM,'level':0},
        'console':{'common_level':0,'class_level':0,'company_level':0},
        'collection_stage':NO_ITEM,'favorite_stage':0,'control':{}}

def number(v, lo, hi, label, integer=False):
    if isinstance(v,bool): raise ValueError(f'{label} must be a number.')
    try: n=float(v)
    except (ValueError,TypeError): raise ValueError(f'{label} must be a number.')
    if not math.isfinite(n) or not lo <= n <= hi or (integer and n != int(n)):
        raise ValueError(f'{label} must be between {lo} and {hi}' + (' (whole number).' if integer else '.'))
    return int(n) if integer else n

def validate_build(raw):
    if not isinstance(raw,dict): raise ValueError('Build must be an object.')
    unknown=set(raw)-set(default_build())
    if unknown: raise ValueError('Unknown build fields: '+', '.join(sorted(unknown)))
    b=spec.deep_merge(default_build(),raw)
    for k,lo,hi in [('level',1,1000),('breakthrough',0,3),('core_enhancement',0,7),('affinity',1,40),('favorite_stage',0,3)]:
        b[k]=number(b[k],lo,hi,k,True)
    if set(b['skill_levels']) != {'1','2','3'}: raise ValueError('Skills need keys 1, 2, 3.')
    b['skill_levels']={k:number(v,1,10,'Skill level',True) for k,v in b['skill_levels'].items()}
    if set(b['equip_skills'])-set(spec.DEFAULT_CHAR['equip_skills']): raise ValueError('Unknown Overload option.')
    for k,v in b['equip_skills'].items():
        if isinstance(v,list):
            if len(v)>12: raise ValueError('Too many Overload lines.')
            b['equip_skills'][k]=[number(x,0,1000,k) for x in v]
        else: b['equip_skills'][k]=number(v,0,1000,k)
    cubes=read(ENGINE/'data/base_stat_tables/cube.json')
    if b['cube'].get('name')==NO_ITEM:
        b['cube']['level']=0
    else:
        if b['cube'].get('name') not in cubes or b['cube']['name'].startswith('_') or b['cube']['name']=='공통': raise ValueError('Unknown cube.')
        b['cube']['level']=number(b['cube'].get('level'),1,15,'Cube level',True)
    collections=read(ENGINE/'data/base_stat_tables/collection.json')['_stat_table']
    if b['collection_stage'] != NO_ITEM and b['collection_stage'] not in collections: raise ValueError('Unknown collection stage.')
    if b['favorite_stage']>0:b['collection_stage']='SR15'
    if set(b['equipment']) != set(PARTS): raise ValueError('Four equipment slots are required.')
    for p,e in b['equipment'].items():
        if not isinstance(e,dict): raise ValueError('Invalid equipment slot.')
        e['level']=number(e.get('level',0),0,5,'Equipment level',True)
        if e.get('skills'): raise ValueError('Use equip_skills for Overload lines, not equipment.skills.')
        tier=e.get('tier',NO_ITEM)
        if tier not in (NO_ITEM,'기업','T1','T2','T3','T4','T5','T6','T7','T8','T9'): raise ValueError('Equipment tier must be 없음, 기업 (Overload), or T1–T9.')
    if set(b['console']) != {'common_level','class_level','company_level'}: raise ValueError('Invalid research levels.')
    for k,v in b['console'].items(): b['console'][k]=number(v,0,1000,k,True)
    if b['control']: raise ValueError('Choose the playstyle in encounter settings; imported control scripts are not accepted.')
    return b

def import_roster(data):
    if isinstance(data,dict) and data.get('format')=='nikke-offline-blablalink-v1':
        return import_account_export(data)
    warnings=[]
    if isinstance(data,dict) and 'elements' in data:
        rows=[r for group in data['elements'].values() for r in group]
        kind='Exia BlaBlaLink export'
    elif isinstance(data,dict) and isinstance(data.get('roster'),list): rows=data['roster']; kind='Raid Lab export'
    elif isinstance(data,list): rows=data; kind='Roster list'
    else: raise ValueError('Use a Raid Lab roster JSON or an Exia character-data JSON containing elements. A profile URL alone does not include the roster.')
    if len(rows)>400: raise ValueError('Roster is limited to 400 entries.')
    result=[]; seen=set()
    for i,r in enumerate(rows):
        if not isinstance(r,dict): raise ValueError(f'Entry {i+1} is not an object.')
        if r.get('owned') is False or (isinstance(r.get('limit_break'),dict) and r['limit_break'].get('grade',0)<0): continue
        if kind=='Exia BlaBlaLink export':
            lb=r.get('limit_break')
            has_break=isinstance(lb,dict) and isinstance(lb.get('grade'),(int,float)) and lb['grade']>=0
            has_skills=any(isinstance(r.get(k),(int,float)) and r[k]>0 for k in ('skill1_level','skill2_level','skill_burst_level'))
            has_equipment=any(isinstance(v,list) and v for v in (r.get('equipments') or {}).values())
            if not (has_break or has_skills or has_equipment or r.get('item_rare')):continue
        key=r.get('id') if r.get('id') in CAT else CODE_MAP.get(str(r.get('name_code'))) or NAME_MAP.get(str(r.get('name',r.get('name_en',''))).casefold())
        if not key: warnings.append(f"Unmatched unit: {r.get('name',r.get('name_en',r.get('name_code',i+1)))}"); continue
        if key in seen: warnings.append(f'Duplicate skipped: {CAT[key]["name"]}'); continue
        seen.add(key)
        notes=list(r.get('assumptions',[])) if isinstance(r.get('assumptions'),list) else []
        if 'build' in r:
            b=validate_build(r['build'])
            if set(r['build']) != set(default_build()): notes.append('Missing build fields use the modest defaults shown in the editor.')
        else:
            b=default_build()
            lb=r.get('limit_break',r.get('limitBreak',{}))
            if isinstance(lb,dict): b.update(breakthrough=max(0,lb.get('grade',0)),core_enhancement=lb.get('core',0))
            for target,keys in [('1',['skill1_level','skill1_lv']),('2',['skill2_level','skill2_lv']),('3',['skill_burst_level','ulti_skill_lv'])]:
                b['skill_levels'][target]=next((r[k] for k in keys if r.get(k) not in (None,'')),1)
            b['level']=r.get('lv') or r.get('level') or 400
            b['affinity']=r.get('attractive_lv') or 1
            for effects in (r.get('equipments') or {}).values():
                for effect in effects:
                    stat=OPTIONS.get(effect.get('function_type'))
                    if stat:
                        val=number(effect.get('function_value'),0,1000,stat)
                        if stat in ('max_ammo_pct','charge_speed_pct'):
                            if not isinstance(b['equip_skills'][stat],list): b['equip_skills'][stat]=[]
                            b['equip_skills'][stat].append(val)
                        else: b['equip_skills'][stat]+=val
            rare=r.get('item_rare'); phase=r.get('item_level')
            if rare in ('R','SR') and phase not in (None,''): b['collection_stage']=f'{rare}{int(phase)}'
            if rare=='SSR': notes.append('Favorite-item phase needs manual entry; collection set to SR15.'); b['collection_stage']='SR15'
            notes.append('Imported ownership, skills, limit breaks and available Overload lines. Missing gear tiers/levels, cube, research, bond and favorite phase use visible defaults; review before comparing damage. Current displayed ATK is not reused at a fixed raid level.')
            b=validate_build(b)
        if CAT[key]['supported']:
            notes=[n for n in notes if n != 'Skill kit not supported; excluded from simulations.']
        else: notes.append('Skill kit not supported; excluded from simulations.')
        result.append({'id':key,'build':b,'enabled':r.get('enabled',True) is not False,'assumptions':list(dict.fromkeys(str(n) for n in notes))})
    if not result: raise ValueError('No matching owned units found. Import the character-data export, not accounts or a blank character template.')
    return {'roster':result,'warnings':warnings,'source':kind}

def import_account_export(data):
    """Convert the existing complete BlaBlaLink export, without credentials/network."""
    sys.path.insert(0,str(ENGINE/'scraper'))
    import profile_fetch as pf
    if data.get('complete') is not True or data.get('missing_codes') or data.get('errors'):
        raise ValueError('This account export is incomplete. Export a complete roster before importing.')
    effective={str(c['name_code']):c for c in data['roster']['characters']}
    details=[r for batch in data['details'] for r in batch.get('character_details',[])]
    effects=[r for batch in data['details'] for r in batch.get('state_effects',[])]
    if len({str(d['name_code']) for d in details})!=len(effective):raise ValueError('Character detail count does not match the owned roster.')
    opt,unknown,off_table=pf._build_option_map(effects,pf._load_equip_skill_table())
    warnings=[]
    if unknown:raise ValueError('Unmapped Overload effect types: '+', '.join(unknown)+'. Import stopped to avoid dropping stats.')
    referenced={str(d[f'{p}_equip_option{i}_id']) for d in details for p in ('head','torso','arm','leg') for i in (1,2,3) if d.get(f'{p}_equip_option{i}_id')}
    if referenced-set(opt):raise ValueError('Some equipped Overload options have no effect definition. Import stopped to avoid dropping stats.')
    for ftype,key,val,oid in off_table:warnings.append(f'Overload value {key}={val}% is outside the engine reference table; imported the actual value.')
    console=pf._console(data.get('outpost',{}).get('outpost_info',{}).get('recycle_room_researches',[]),warnings)
    fav_map={int(k):tuple(v) for k,v in read(ROOT/'favorite-map.json').items()}
    cube_names=pf._load_cube_name_map(); rows=[]
    missing_equipment=0;missing_collection=0;no_cube=0;unsynced=0
    for detail in details:
        code=str(detail['name_code']);name=CODE_MAP.get(code)
        if name is None:warnings.append(f'Character code {code} has no catalogue mapping; omitted.');continue
        if code not in effective:raise ValueError('A character detail is not in the owned roster.')
        eff=effective[code];meta=META[name];notes=[]
        local_warnings=[]
        growth=pf._to_profile(detail,eff,opt,fav_map,name,meta['weapon_type'],local_warnings,has_favorite=True)
        b=default_build()
        b.update({k:v for k,v in growth.items() if not k.startswith('_')})
        b['level']=eff['lv']
        if b['level']<=1:unsynced+=1
        for p,gear in b['equipment'].items():
            gear={k:v for k,v in gear.items() if not k.startswith('_')}
            if 'tier' not in gear:gear['tier']='기업'
            gear.setdefault('level',0);gear['skills']=[];b['equipment'][p]=gear
            missing_equipment+=gear['tier']==NO_ITEM
        missing_collection+=b['collection_stage']==NO_ITEM
        cube_id=detail.get('harmony_cube_tid',0)
        if cube_id:
            cube_name=cube_names.get(cube_id)
            if not cube_name:raise ValueError(f'Unmapped equipped cube for {CAT[name]["name"]}; import stopped.')
            b['cube']={'name':cube_name,'level':detail['harmony_cube_lv']}
        else:no_cube+=1
        if console:
            b['console']={'common_level':console['common_level'],'class_level':console['class_level'].get(meta['class'],0),'company_level':console['company_level'].get(meta['manufacturer'],0)}
            if meta['class'] not in console['class_level'] or meta['manufacturer'] not in console['company_level']:notes.append('A matching research category was absent; its level is set to zero.')
        else:notes.append('Research data missing; research bonuses set to zero.')
        notes.extend(local_warnings);warnings.extend(local_warnings)
        if not CAT[name]['supported']:notes.append('Skill kit not supported; excluded from simulations.')
        rows.append({'id':name,'build':validate_build(b),'enabled':True,'assumptions':notes})
    warnings=list(dict.fromkeys(warnings))
    if unsynced:warnings.append(f'{unsynced} owned units are level 1/outside the synchro squad. They remain owned; fixed-level mode recalculates their level, not their investment.')
    return {'roster':rows,'warnings':warnings,'source':'BlaBlaLink account · '+str(data.get('captured_at','unknown date'))[:10],
        'summary':{'owned':len(rows),'supported':sum(CAT[r['id']]['supported'] for r in rows),'empty_gear_slots':missing_equipment,'no_collection':missing_collection,'no_equipped_cube':no_cube,'unsynced':unsynced,'research_imported':bool(console),'captured_at':data.get('captured_at')}}

def demo_roster():
    wanted=['Liter','Dolla','Volume','Dorothy','D: Killer Wife','Rouge','Crown','Naga','Blanc','Noir','Grave','Helm: Aquamarine','Marciana','Centi','Novel','Scarlet','Scarlet: Black Shadow','Alice','Red Hood','Cinderella','Modernia','Privaty','Helm','Maxwell','Snow White','Anis: Sparkling Summer','Ludmilla: Winter Owner','Ein','Sakura: Bloom in Summer','Rosanna: Chic Ocean','Tove','Sugar','Drake','Laplace']
    norm=lambda s:''.join(s.casefold().split())
    selected=[c for c in CATALOG if c['supported'] and norm(c['name']) in {norm(x) for x in wanted}]
    out=[]
    for c in selected:
        b={k:copy.deepcopy(v) for k,v in spec.DEFAULT_CHAR.items() if k in default_build()}; b['control']={}; b['favorite_stage']=0
        for e in b['equipment'].values():e['tier']='기업'
        out.append({'id':c['id'],'build':b,'enabled':True,'assumptions':['Demonstration build: level 400, 10/10/10 skills, enhanced gear and cube 15. This is not your account.']})
    return out

def validate_settings(s):
    if not isinstance(s,dict): raise ValueError('Settings must be an object.')
    out={'teams':number(s.get('teams',1),1,5,'Teams',True), 'duration':number(s.get('duration',180),30,180,'Duration'),
         'def':number(s.get('def',31784),0,1000000,'Enemy defence'), 'core_px':number(s.get('core_px',0),0,500,'Core size'),
         'level':number(s.get('level',400),1,1000,'Fixed level',True), 'budget':number(s.get('budget',6),3,16,'Search budget',True)}
    for k,choices,default in [('element',['Any']+list(ELEMENT_KO),'Any'),('enemy_element',['Neutral']+list(ELEMENT_KO),'Neutral'),('playstyle',['auto','assisted'],'auto')]:
        out[k]=s.get(k,default)
        if out[k] not in choices: raise ValueError(f'Invalid {k}.')
    for k in ['cdr','healing','has_parts','fixed_level','require_critical_parts']: out[k]=s.get(k, k=='fixed_level') is True
    out['optimal_range_weapons']=s.get('optimal_range_weapons',[])
    if not isinstance(out['optimal_range_weapons'],list) or set(out['optimal_range_weapons'])-{'AR','SMG','MG','SG','SR','RL'}: raise ValueError('Invalid weapon range selection.')
    out['compute_mode']=s.get('compute_mode','cpu')
    if out['compute_mode'] not in ('cpu','gpu','auto','single'):raise ValueError('Invalid compute mode.')
    out['cpu_workers']=number(s.get('cpu_workers',0),0,worker_limit(),'CPU workers',True)
    out['gpu_device']=s.get('gpu_device','auto')
    if not isinstance(out['gpu_device'],str) or len(out['gpu_device'])>128:raise ValueError('Invalid GPU selection.')
    return encounters.apply_profile(s,out)

def kit_search_attack(char,effects,meta):
    """A kit-aware proposal prior, never an estimated DPS or acceptance score.

    Static ATK alone misses units that turn HP into ATK. Use their directly
    parsed self conversion, without assuming optional stacks or an external
    enabler. Unconditional burst coefficients add a bounded proposal bonus;
    random/split damage still counts only once across the entire enemy group.
    Full combat remains responsible for uptime, targets, gauge and survival.
    """
    levels=char.get('skill_levels',{})
    def value(effect):
        if effect.get('fixed_value') is not None:return float(effect['fixed_value'])
        source=str(effect.get('source',''))
        stage=next((k for k in ('1','2','3') if source.endswith(k)),None)
        level=levels.get(stage,1)
        values=effect.get('values') or {}
        return float(values.get(str(level),values.get(level,0)))
    conversion=0.;burst_coefficients=[]
    for effect in effects:
        trigger=effect.get('trigger') or {}
        if trigger.get('condition') or effect.get('scaling'):continue
        target=effect.get('target')
        targets=target if isinstance(target,list) else [target]
        if effect.get('stat')=='atk_from_hp_pct' and 'self' in targets:
            # A peak conversion keeps HP-scaling kits in the candidate pool;
            # it does not assert that the conversion lasts the entire fight.
            conversion=max(conversion,max(0.,value(effect)))
        if effect.get('type')!='damage' or 'burst_cast' not in trigger.get('timing',[]):continue
        stat=effect.get('stat','');hits=1
        if stat.startswith('sequential_damage:'):
            count=stat.split(':',1)[1]
            if not count.isdigit():continue  # Dynamic counters need simulation.
            hits=int(count)
        elif stat=='auto_damage':
            duration,interval=effect.get('duration',0),effect.get('tick_interval',0)
            if not isinstance(duration,(int,float)) or not isinstance(interval,(int,float)) or interval<=0 or duration<=0:continue
            hits=duration/interval
        elif stat not in ('damage','burst_damage','bonus_damage'):continue
        if target=='all_projectiles':continue
        burst_coefficients.append(max(0.,value(effect))*hits/100)
    attack=spec.static_atk(char)
    if conversion:attack+=spec.calc_base_stats(char)['hp']*conversion/100
    # Two nominal ATK multiples per second are only a normalization scale.
    # Cap this weak prior: unsupported triggers cannot manufacture a DPS score.
    cooldown=max(20.,float(meta.get('burst_cooldown') or 40))
    burst_bonus=min(1.,math.sqrt(1+sum(burst_coefficients)/cooldown/2)-1)
    return attack*(1+burst_bonus)


def heuristic(team,roster,s):
    catalog=s.get('_catalog',CAT)
    score=0
    for n in team:
        c=catalog[n]; b=copy.deepcopy(roster[n]['build'])
        b['level']=encounters.unit_level(b,s)
        # Only a shortlist score, never displayed as simulated DPS.
        char=spec.build_char(n,b,no_layer=True)
        stat=kit_search_attack(char,char_effects(n,b.get('favorite_stage',0)),META[n])
        # Class labels do not predict personal damage or team damage support.
        # Keep build/kit priors here; simulated squad damage selects finalists.
        score+=stat*(1+sum(b['skill_levels'].values())/30)*(1.25 if c['element']==s['element'] else 1)
    p=s.get('encounter',{})
    guide=p.get('guidance',{}) if s.get('survival_policy','guide')=='guide' else {}
    for n in team:
        c=catalog[n]
        if c['element']==p.get('weakness'):score*=1.08
        support_tags=set(guide.get('required_tags',[])+guide.get('preferred_tags',[]))&set(c['tags'])
        if support_tags:
            investment=sum(roster[n]['build']['skill_levels'].values())/30
            score*=1+min(.5,.12*len(support_tags))*(.5+.5*investment)
        if c['element']==guide.get('vulnerable_element'):score*=.9
        if 'rapid_fire' in p.get('preferred',[]) and c['weapon'] in ('MG','SMG'):score*=1.04
        if 'AoE' in p.get('preferred',[]) and 'AoE' in c['tags']:score*=1.04
    if s.get('content_mode')=='campaign':
        for n in team:
            tags=set(catalog[n]['tags'])
            score*=1+.65*('AoE' in tags)+.25*('CDR' in tags)+.15*('Healing' in tags)
    tags={t for n in team for t in catalog[n]['tags']}
    score*=1+.25*('CDR' in tags)+.08*('Damage support' in tags)
    # Documented structural pair synergies; simulation decides their value.
    names={catalog[n]['name'] for n in team}
    if {'Blanc','Noir'}<=names: score*=1.25
    if {'Crown','Naga'}<=names: score*=1.18
    return score

def valid(team,s):
    catalog=s.get('_catalog',CAT)
    if len(team)!=5 or len(set(team))!=5: return False
    barrier=s.get('encounter',{}).get('barrier_element')
    if barrier and not any(barrier in catalog[n]['barrier_elements'] for n in team):return False
    if not encounters.follows_guide(team,s,catalog):return False
    stages=[catalog[n]['burst'] for n in team]
    # V1 generator uses ordinary B1/B2/B3 chains. All-stage and re-entry units
    # are available in manual simulation; no unsafe wildcard shortcut here.
    if not all(str(x) in stages for x in [1,2,3]): return False
    if s['element']!='Any' and not any(s['element'] in catalog[n]['barrier_elements'] for n in team): return False
    if s['cdr'] and not any('CDR' in catalog[n]['tags'] for n in team): return False
    if s['healing'] and not any('Healing' in catalog[n]['tags'] for n in team): return False
    return True

def ordered(team):
    return sorted(team,key=lambda n:(-1 if CAT[n]['name']=='Crown' else {'1':0,'2':1,'A':2,'3':3}.get(CAT[n]['burst'],4),CAT[n]['name']))

def active_team_cdr(result):
    if not result.log:return 0
    return sum(e.stat=='burst_cooldown_reduce' and any(k.get('stat')=='burst_cooldown_reduce' and k.get('target')!='self' and k.get('name')==e.name for k in SKILLS.get(e.caster,[])) for e in result.log.instant_events)

def burst_orders(team,catalog,guidance=None):
    """Compare same-stage priorities without inventing a post-simulation order."""
    orders=[tuple(team)]
    for stage in ('1','2','3','A'):
        slots=[i for i,n in enumerate(team) if catalog[n]['burst']==stage]
        if len(slots)<2:continue
        expanded=[]
        for base in orders:
            for permutation in itertools.permutations([base[i] for i in slots]):
                candidate=list(base)
                for position,n in zip(slots,permutation):candidate[position]=n
                expanded.append(tuple(candidate))
        orders=expanded
    orders=list(dict.fromkeys(orders))
    return guidance.orders(orders) if guidance else orders

def membership_shortlist(screened,limit):
    """A membership gets one shortlist place, regardless of rotation count."""
    selected=[];seen=set()
    for row in sorted(screened,reverse=True):
        membership=frozenset(row[1])
        if membership not in seen:
            seen.add(membership);selected.append(row)
        if len(selected)>=limit:break
    return selected

def attach_combat_assessment(entry):
    fight=entry.get("encounter_timeline")
    if fight and 'part_break_damage' in fight:
        add_by=fight.get('add_damage_by_unit',{})
        by_unit={n:dict(boss_direct=entry['breakdown'].get(n,0),summon_direct=add_by.get(n,0),
            all_targets_direct=entry['breakdown'].get(n,0)+add_by.get(n,0)) for n in entry['members']}
        # Keep the comparison objective as direct boss damage. Destruction HP
        # loss and client character statistics are distinct native quantities;
        # Museum leaderboard context selection has not been established.
        entry['damage_accounting']=dict(boss_direct=entry['damage'],part_break_bonus=fight['part_break_damage'],
            boss_hp_loss=fight.get('boss_hp_damage',entry['damage']+fight['part_break_damage']),
            summon_direct=sum(add_by.values()) if 'add_damage_by_unit' in fight else None,
            all_targets_direct=entry['damage']+sum(add_by.values()) if 'add_damage_by_unit' in fight else None,
            by_unit=by_unit if 'add_damage_by_unit' in fight else {})
    if fight and fight.get('model'):
        entry['mechanics']={'status':fight['model'],'clear_verified':False,'checks':[
            {'name':'Automatic boss script','status':'modeled','detail':'Recovered AI branches use actual part destruction, interruption outcomes and attack completion.'},
            {'name':'Squad survival','status':fight['survival'],'detail':fight.get('stop_reason') or 'Survived the modeled attacks; incoming damage conversion remains approximate.'},
            {'name':'Physical calibration','status':'unverified','detail':'See combat assumptions. A completed simulation is not proof of client-equivalent behavior.'}]}
        if fight.get('model_id','').startswith('mother-whale'):
            part=fight['critical_parts'][0]
            destroyed=part['destroyed_at'];deadline=part['deadline']
            detail=(f"Core destroyed at {destroyed:.2f}s." if destroyed is not None else f"Core has {part['remaining_hp']:,.0f} HP remaining.")
            detail+=(f" First Ultrasonic Wave deadline: {deadline:.2f}s." if deadline is not None else ' No Ultrasonic Wave activated in the observed interval.')
            detail+=' Missing the opening break is not a wipe: clearing summons before protection, or defeating protected survivors, are alternative routes.'
            cleared=sum(a.get('clear_reason')=='squad damage' for a in fight['summons'])
            entry['mechanics']['checks'][:0]=[
                {'name':'Core before Ultrasonic Wave','status':part['status'],'detail':detail},
                {'name':'Summon clearing','status':'modeled','detail':f"{cleared}/{len(fight['summons'])} summons cleared by squad damage. {fight['damage_to_adds']:,.0f} effective summon HP damage is excluded from direct boss damage."},
                {'name':'Element barrier','status':'modeled','detail':'The Electric barrier blocks off-element boss hits while active. Clearing summons removes it; core destruction separately disables subsequent protection waves.'},
                {'name':'Circle QTE','status':'not applicable','detail':'This Museum variant uses summon clearing and an elemental barrier, not a timed circle QTE.'}]
            entry['mechanics']['summary']='Core timing, summon clearing, barrier damage and survival were simulated. Select the squad checks for the outcomes.'
        if fight.get('model_id')=='raid-boss-runtime-v1':
            checks=fight.get('checks',[])
            entry['mechanics']['checks'][:0]=[
                {'name':'Interruption targets','status':'modeled','detail':f"{sum(c['status']=='passed' for c in checks)} of {len(checks)} observed checks passed using actual weapon hits and deadlines."},
                {'name':'Part objectives','status':'modeled','detail':'Part damage, destruction and repair change the boss attack branches. The squad checks show each recorded objective.'}]
            if fight.get('choices'):entry['mechanics']['checks'].insert(0,{'name':'Boss attack choices','status':'modeled','detail':'; '.join(f"{c['time']:.2f}s: {c['route']}" for c in fight['choices'])})
            entry['mechanics']['summary']='Part objectives, QTEs, attack choices and survival affect this simulation. Select a squad check to inspect its outcome.'
        if fight.get('special_interception'):
            entry['combat_elapsed']=max(.001,fight['simulated_until'])
            entry['dps']=entry['damage']/entry['combat_elapsed']
            if entry.get('burst_rotation'):
                entry['burst_rotation']['uptime_pct']=round(100*entry['burst_rotation']['full_burst_seconds']/entry['combat_elapsed'],1)
                entry['burst_rotation']['observed_duration']=entry['combat_elapsed']
            entry['mechanics']['summary']=f"Reward stage {fight['reward_stage']}/9 in the model. Circle damage, missiles, cover and incoming attacks were tested; movement and manual aim remain approximate."
            for check in entry['mechanics']['checks']:
                if check['name']=='Automatic boss script':check['detail']='Boss-specific EX phase policies use recovered skill records and actual interruption outcomes. Spatial movement is approximated.'
    if fight and fight.get("stop_reason"):
        entry.setdefault("warnings",[]).append("Experimental boss model stopped: "+fight["stop_reason"]+". This is not a verified in-game failure.")


def elemental_damage_report(entry,settings,catalog):
    element=settings.get('encounter',{}).get('barrier_element')
    if not element:element=settings.get('element') if settings.get('element') not in (None,'Any') else None
    if not element:return None
    total=max(1,entry['damage'])
    ranked=sorted(entry['members'],key=lambda n:entry['breakdown'].get(n,0),reverse=True)
    fight=entry.get('encounter_timeline') or {}
    if fight.get('model_id')=='raid-boss-runtime-v1':
        providers=[n for n in ranked if element in catalog[n]['barrier_elements']]
        return dict(element=element,providers=providers,status='modeled barrier access' if providers else 'missing element',assessment='modeled-barrier',
            criterion='Matching element access is required. Actual shots must clear the interruption targets before their deadlines; total team damage share is not substituted for the check.',
            contributions=[dict(id=n,damage=entry['breakdown'].get(n,0),share=round(entry['breakdown'].get(n,0)/total,4),barrier_damage=round(fight.get('barrier_damage_by_unit',{}).get(n,0))) for n in providers])
    if fight.get('model_id','').startswith('mother-whale') and fight.get('qte_required') is False:
        providers=[n for n in ranked if element in catalog[n]['barrier_elements']]
        return dict(element=element,providers=providers,status='modeled barrier access' if providers else 'missing element',
            assessment='modeled-barrier',criterion='Electric access is required. The fight model applies the barrier to actual hits and removes it when summons clear. This variant has no timed circle QTE, so a 15% total-damage screen is not used as a substitute for the modeled mechanic.',
            contributions=[dict(id=n,damage=entry['breakdown'].get(n,0),share=round(entry['breakdown'].get(n,0)/total,4),barrier_damage=round(fight.get('barrier_damage_by_unit',{}).get(n,0))) for n in providers])
    providers=[n for n in ranked[:3] if element in catalog[n]['barrier_elements'] and entry['breakdown'].get(n,0)/total>=.15]
    return dict(element=element,providers=providers,status='damage dealer present' if providers else 'no substantial elemental damage dealer',
        criterion='At least one matching-element unit among the top three damage contributors, contributing at least 15% of simulated team damage. Burst stage and character class do not restrict eligibility. This composition safeguard is not proof of QTE success.',
        contributions=[dict(id=n,damage=entry['breakdown'].get(n,0),share=round(entry['breakdown'].get(n,0)/total,4)) for n in ranked if element in catalog[n]['barrier_elements']])


def damage_model_note(settings):
    if settings['boss_id'] in encounters.RAID_PROFILES:return 'Boss attacks, parts, interruptions and survival affect the damage score. Physical timing, aiming and incoming damage conversion remain approximate.'
    if settings['boss_id']=='museum-mother-whale':return 'Mother Whale core, summons, barrier and attacks are simulated; boss score excludes add damage. Physical timing and damage conversion remain approximate.'
    return ("Automatic Kraken uses an approximate physical model; damage and survival need validation across recorded fights." if settings.get("boss_simulation")=="automatic" and settings["boss_id"]=="anomaly-kraken" else "Stationary target; full boss attacks, geometry and survival are not simulated.")


def evaluate_candidate(team,duration,detail,roster,s):
    if s.get('require_critical_parts') and detail and not s.get('_aim_controller'):
        from critical_parts import assessment
        alternatives=[];errors=[]
        for controller in team:
            try:alternatives.append(evaluate_candidate(team,duration,detail,roster,dict(s,_aim_controller=controller)))
            except ValueError as error:errors.append(str(error))
        if not alternatives:raise ValueError('; '.join(sorted(set(errors))))
        result=max(alternatives,key=lambda r:(assessment(r)['passed'],candidate_score(r)))
        result['control_comparison']=[dict(unit=r['encounter_timeline']['off_burst_controller'],damage=r['damage'],parts_passed=assessment(r)['passed']) for r in alternatives]
        result['critical_part_requirement']=assessment(result)
        return result
    catalog=s.get('_catalog',CAT)
    overrides={n:copy.deepcopy(roster[n]['build']) for n in team}
    for b in overrides.values():b['level']=encounters.unit_level(b,s)
    squad=spec.build_squad(team,chars=overrides,no_layer=set(team))
    if s['playstyle']=='assisted':
        tactical=spec.tactic_overrides('버충',team)
        for c in squad: c['control']=spec.deep_merge(c.get('control',{}),tactical.get(c['name'],{}).get('control',{}))
    cfg=spec.build_config(squad,{'duration':duration,'rng_mode':'expected','burst_gauge_mode':'accumulate','burst_switch_delay':.5 if s['playstyle']=='auto' else .1})
    cfg.update(encounters.config(s,duration))
    # Alternating support routes are simulated, with the tested slot order
    # choosing which partner takes the first cycle. Explicit build patterns win.
    for rule in s.get('_support_cycles',[]):
        if set(rule['requires']+rule['cycle'])<=set(team):
            cycle=sorted(rule['cycle'],key=team.index)
            patterns={n:list(range(i+1,int(duration*2)+2,len(cycle))) for i,n in enumerate(cycle)}
            cfg['burst_pattern']={**patterns,**cfg.get('burst_pattern',{})}
    if cfg.get('encounter_runtime'):cfg['encounter_runtime'].element_access={n:[ELEMENT_KO[x] for x in catalog[n]['barrier_elements']] for n in team}
    enemy={'def':s['def'],'code':ELEMENT_KO.get(s['enemy_element']),'core_px':s['core_px'],'has_parts':s['has_parts'],'optimal_range_weapons':s['optimal_range_weapons']}
    result=simulate(squad,cfg,enemy,verbose=detail or s['cdr'] or s.get('_rotation_required',False),seed=42)
    encounter_report=getattr(result,'encounter_report',None)
    activated=active_team_cdr(result)
    if s['cdr'] and not activated:raise ValueError('A candidate had a team CDR skill but it never activated; candidate excluded.')
    entry={'members':list(team),'damage':result.squad_total,'dps':result.squad_total/duration,'duration':duration,'breakdown':result.char_total,'team_cdr_activations':activated,'mechanics':encounters.assessment(s,team,catalog),'encounter_timeline':encounter_report,'support_plan':encounters.support_report(team,s,catalog)}
    if result.log:
        entry['burst_rotation']=burst_rotation.report(team,catalog,result.log.burst_log,duration,cfg['burst_switch_delay'],observed_until=(encounter_report or {}).get('simulated_until'))
        if s.get('_rotation_required') and not entry['burst_rotation']['covered']:
            raise ValueError(' '.join(burst_rotation.warnings(entry['burst_rotation'])))
    if cfg.get('burst_pattern'):entry['support_burst_patterns']=cfg['burst_pattern']
    if detail:
        entry['healing_dependencies']=healing_dependencies(team,{n:char_effects(n,roster[n]['build']['favorite_stage']) for n in team},result.log.buff_events,duration)
        entry['kit_dependencies']=KitDependencies({n:char_effects(n,roster[n]['build']['favorite_stage']) for n in roster},META,catalog).inspect(team,result)
        entry['burst_log']=[{'time':round(e.t,2),'event':e.event,'unit':e.caster} for e in result.log.burst_log]
        entry['bursts']=sum(e.event=='full_burst 시작' for e in result.log.burst_log)
        entry['deviations']=spec.format_deviations(squad)
        entry['builds']=squad
        bins=[0]*math.ceil(duration/5)
        for h in result.hits: bins[min(int(h.t/5),len(bins)-1)]+=h.damage
        entry['timeline']=bins
        entry['recommendation']=evidence_report(result,team,roster,s,catalog)
        entry['warnings']=entry['recommendation']['warnings'].copy()
        entry['warnings'].extend(burst_rotation.warnings(entry['burst_rotation']))
        needs_healing=s['healing'] or (s.get('survival_policy','guide')=='guide' and 'Healing' in s['encounter'].get('guidance',{}).get('required_tags',[]))
        if needs_healing and not entry['recommendation']['available_healers']:raise ValueError('Required team healing cannot activate in this burst order; candidate excluded.')
        if entry['bursts']<2 and duration>=60:entry['warnings'].append('Fewer than two Full Bursts: this rotation may stall.')
        if not any('CDR' in catalog[n]['tags'] for n in team):entry['warnings'].append('No CDR skill detected.')
    entry['elemental_damage']=elemental_damage_report(entry,s,catalog)
    if s['element']!='Any' and s['element']!=s['encounter'].get('barrier_element'):
        requested=elemental_damage_report(entry,dict(encounter={'barrier_element':s['element']}),catalog)
        if not requested['providers']:raise ValueError('Candidate lacks a substantial '+s['element']+' damage dealer for the requested DPS element.')
    if entry['elemental_damage'] and not entry['elemental_damage']['providers']:
        raise ValueError('Candidate needs a substantial '+entry['elemental_damage']['element']+' damage dealer for element-locked QTEs; a matching support alone is insufficient.')
    attach_combat_assessment(entry)
    if encounter_report and not encounter_report.get('model') and any(c['status']=='failed' for c in encounter_report['checks']):raise ValueError('Candidate failed a scripted QTE damage check.')
    return entry

def search(payload,progress=lambda **kw:None,cancelled=lambda:False):
    settings=validate_settings(payload.get('settings',{}))
    executor=CandidateExecutor(settings['compute_mode'],settings['cpu_workers'])
    executor.partial_result=None
    try:
        try:result=_search(payload,progress,cancelled,executor)
        except (InterruptedError,TimeoutError):
            result=executor.partial_result
            if result is None:raise InterruptedError('Stopped before any team finished a full-fight simulation. No new recommendation is available yet.')
        except ValueError:
            if time.perf_counter()<executor.deadline or executor.partial_result is None:raise
            result=executor.partial_result
        reason='cancelled' if cancelled() else 'time_limit' if time.perf_counter()>=executor.deadline else 'completed'
        result['elapsed']=round(time.perf_counter()-getattr(executor,'search_started',time.perf_counter()),2)
        result['completion']={'reason':reason,'requested_teams':result['settings']['teams'],'returned_teams':len(result['teams'])}
        if reason!='completed':result['warnings'].append('Search stopped. Recommendations use completed full-fight simulations only; untested alternatives may be better.')
        progress(phase='Results ready',progress=1.,elapsed=result['elapsed'])
        return result
    finally:executor.close()

def _search(payload,progress,cancelled,executor):
    start=time.perf_counter(); s=validate_settings(payload.get('settings',{}))
    search_seconds=120 if s['budget']<=3 else 240 if s['budget']<=6 else 360
    executor.search_started=start
    executor.deadline=start+search_seconds
    exhausted=lambda:time.perf_counter()>=executor.deadline
    emit=progress
    def progress(**data):
        elapsed=time.perf_counter()-start
        emit(**dict({'elapsed':round(elapsed,1),'time_limit':search_seconds,'progress':min(.99,elapsed/search_seconds)},**data))
    def guard():
        if cancelled():raise InterruptedError('Search cancelled.')
        if exhausted():raise TimeoutError('Search time limit reached.')
    progress(phase='Preparing roster',simulations=0)
    guard()
    compute={'gpu_used':False}
    imported=import_roster({'roster':payload.get('roster',[])})
    roster={r['id']:r for r in imported['roster'] if r['enabled'] and CAT[r['id']]['supported']}
    catalog=resolve_catalog(roster); s['_catalog']=catalog
    if len(roster)<s['teams']*5: raise ValueError(f'Need {s["teams"]*5} enabled units with supported skill kits; found {len(roster)}.')
    required_element=s['encounter'].get('barrier_element')
    if required_element:
        available=sum(required_element in catalog[n]['barrier_elements'] for n in roster)
        if available<s['teams']:
            raise ValueError(f"{s['encounter']['name']} requires {required_element} coverage on every team. Need at least {s['teams']} distinct enabled, supported units with {required_element} access; found {available}. Matching damage strength is checked during simulation.")
    rng=random.Random(42); ids=list(roster); plans={}; attempts=0
    # Static strength computed once; avoid rebuilding stats in each proposal.
    weights={n:heuristic([n],roster,s) for n in ids}
    from search_guidance import SearchGuidance
    guidance=SearchGuidance(roster,catalog,s,weights)
    s['_support_cycles']=guidance.cycle_rules()
    effects={n:char_effects(n,roster[n]['build']['favorite_stage']) for n in ids}
    guidance.kits=KitDependencies(effects,META,catalog)
    s['_rotation_required']=True
    # Preserve the original investment-only proposal stream as a control seed.
    control_rng=random.Random(42); control_plans={}
    for _ in range(2500):
        if _%25==0:guard()
        if len(control_plans)>=s['budget']*5:break
        available=set(ids); allocation=[]
        for ti in range(s['teams']):
            team=[]
            for stage in ['1','2','3','3',None]:
                pool=[n for n in ids if n in available and (stage is None or catalog[n]['burst']==stage)]
                if stage is None:pool=[n for n in pool if valid(team+[n],s)]
                if not pool:break
                chosen=max(pool,key=lambda n:math.log(max(weights[n],1))+guide_priority(n,team,s)+.9*(-math.log(-math.log(max(1e-9,control_rng.random())))))
                team.append(chosen);available.remove(chosen)
            if not valid(team,s):break
            allocation.append(ordered(team))
        if len(allocation)==s['teams']:
            key=tuple(sorted(tuple(t) for t in allocation))
            control_plans[key]=sum(sum(weights[n] for n in t)*(1.25 if any('CDR' in catalog[n]['tags'] for n in t) else 1) for t in allocation)
    while attempts<2500 and len(plans)<s['budget']*5:
        if attempts%25==0:guard()
        attempts+=1; available=set(ids); teams=[]
        for ti in range(s['teams']):
            team=[]
            for stage in ['1','2','3','3',None]:
                pool=[n for n in ids if n in available and (stage is None or catalog[n]['burst']==stage)]
                if stage is None:pool=[n for n in pool if valid(team+[n],s)]
                if not pool: break
                # Gumbel sampling balances strong units with alternative allocations.
                chosen=max(pool,key=lambda n:guidance.priority(n,team)+guide_priority(n,team,s)+(.5 if attempts%3 else .9)*(-math.log(-math.log(max(1e-9,rng.random())))))
                team.append(chosen); available.remove(chosen)
            if not valid(team,s): break
            teams.append(list(burst_orders(ordered(team),catalog,guidance)[0]))
        if len(teams)==s['teams']:
            canonical=tuple(sorted(tuple(t) for t in teams))
            plans[canonical]=sum(guidance.score(t)*(1.25 if any('CDR' in catalog[n]['tags'] for n in t) else 1) for t in teams)
    if not plans: raise ValueError('No complete plan meets the boss guide and selected filters. Enable more healing, shielding, elemental or burst-stage options, Special burst chains can be tested manually.')
    candidates=sorted(plans,key=plans.get,reverse=True)[:s['budget']]
    if control_plans:
        control=max(control_plans,key=control_plans.get)
        candidates=list(dict.fromkeys([control]+candidates))[:s['budget']]
    progress(phase='Building partner combinations',simulations=0)
    package_plans,package_audit=pairing_search.allocations(ids,catalog,guidance,lambda t:valid(t,s),
        lambda t:list(burst_orders(ordered(t),catalog,guidance)[0]),s['teams'],max(3,s['budget']))
    candidates=list(dict.fromkeys(candidates+package_plans))
    plans.update({p:sum(guidance.score(t) for t in p) for p in package_plans})
    cpu_candidates=set(candidates)
    if s['compute_mode']=='gpu':
        from gpu_search import explore
        progress(phase='Exploring candidate teams on GPU',simulations=0)
        gpu_plans,compute=explore(ids,weights,catalog,s,valid,ordered)
        gpu_plans={tuple(tuple(burst_orders(t,catalog,guidance)[0]) for t in p):sum(guidance.score(t) for t in p) for p in gpu_plans}
        if cancelled():raise InterruptedError('Search cancelled.')
        extra=sorted(gpu_plans,key=gpu_plans.get,reverse=True)[:s['budget']]
        candidates=list(dict.fromkeys(candidates+extra));plans.update(gpu_plans)
    if s['content_mode']=='campaign':
        result=campaign_result(candidates,roster,s,start,progress,cancelled,guidance);result['compute']=compute;return result
    cache={}; failures={}; sims=0; errors=[];joint_allocation_checks=[]
    def checkpoint():
        from critical_parts import select_tested,selection_report
        rows=[r for k,r in cache.items() if k[1]==s['duration'] and k[2]]
        if not rows:return
        seeds=[[cache[(tuple(t),s['duration'],True)] for t in p] for p in candidates
               if all((tuple(t),s['duration'],True) in cache for t in p)]
        if executor.partial_result:seeds.append(executor.partial_result['teams'])
        selected=select_tested(rows,s['teams'],s.get('require_critical_parts'),seeds)
        executor.partial_result={'teams':selected,'total':sum(r['damage'] for r in selected),'elapsed':round(time.perf_counter()-start,2),
            'simulations':sims,'settings':public_settings(s),'plans_considered':len(plans),
            'compute':{'mode':s['compute_mode'],'workers':executor.workers,'backend':'CPU processes',**compute},
            'selection':{'critical_parts':selection_report(selected,s['teams']) if s.get('require_critical_parts') else None,
                         'joint_allocation_checks':list(joint_allocation_checks),
                         'objective':'Reward progress, then interruption reliability, remaining HP and clear time.' if s['content_mode']=='special' else 'Simulated damage', 'method':'Best completed simulations retained during the search.','optimality':'Best tested allocation so far.'},
            'warnings':list(imported['warnings']),
            'assumptions':sorted({str(note) for r in selected for n in r['members'] for note in roster[n]['assumptions']}),
            'limitations':encounters.notes(s)+[damage_model_note(s),'Only completed full-fight simulations are eligible. Stopping early can leave fewer squads than requested.']}
    def prefetch(teams,duration,detail=False,phase='Testing teams in parallel'):
        def completed():
            nonlocal sims
            sims+=1
            progress(phase=phase,simulations=sims,workers=executor.workers,elapsed=round(time.perf_counter()-start,1))
        try:executor.fill([(tuple(t),duration,detail) for t in teams],roster,s,cache,failures,completed,cancelled)
        finally:
            if detail:checkpoint()
        guard()
    def run(team,duration,detail=False):
        nonlocal sims
        if cancelled(): raise InterruptedError('Search cancelled.')
        key=(tuple(team),duration,detail)
        if key in cache:return cache[key]
        if key in failures:raise failures[key]
        if exhausted():raise ValueError('Search complete; candidate not verified.')
        prefetch([team],duration,detail)
        if key in cache:return cache[key]
        if key in failures:raise failures[key]
        raise ValueError('Search complete; candidate not verified.')
    # Secure a complete, full-fight allocation before spending time on exploration.
    prefetch(candidates[0],s['duration'],True,phase='Verifying an initial complete plan')
    prefetch([t for p in candidates for t in p],min(30,s['duration']))
    ranked=[]
    for i,p in enumerate(candidates):
        try:
            samples=[run(t,min(30,s['duration'])) for t in p]
            score=sum(candidate_score(r) for r in samples)
            if s.get('require_critical_parts'):
                from critical_parts import screen_score
                metrics=[screen_score(r) for r in samples]
                score=(sum(m[0] for m in metrics),min(m[1] for m in metrics),sum(m[2] for m in metrics),score)
            ranked.append((score,p))
        except (ValueError,KeyError,IndexError,TypeError) as e: errors.append(str(e))
        progress(phase=f'Quick pass {i+1}/{len(candidates)}',simulations=sims)
    if not ranked:ranked=[(0,candidates[0])]
    # Full-duration verification matters: 30-second ranking can favour early nukes.
    finalists_to_test=list(dict.fromkeys([candidates[0]]+[p for _,p in sorted(ranked,reverse=True)[:2]]+[p for _,p in sorted(ranked,reverse=True) if p in cpu_candidates][:2]))
    prefetch([t for p in finalists_to_test for t in p],s['duration'],True)
    finalists=[]
    for p in finalists_to_test:
        try:results=[run(t,s['duration'],True) for t in p]
        except (ValueError,KeyError,IndexError,TypeError) as e:
            errors.append(str(e));continue
        finalists.append((sum(t['damage'] for t in results),results))
    if not finalists:raise ValueError('No finalist passed the full simulation: '+ '; '.join(errors[-3:]))
    comparisons=[{'damage':v,'members':[t['members'] for t in rows]} for v,rows in finalists]
    total,results=max(finalists,key=lambda x:sum(candidate_score(r) for r in x[1]))
    critical_search=[]
    if s.get('require_critical_parts'):
        if executor.partial_result and len(executor.partial_result['teams'])==s['teams']:results=executor.partial_result['teams']
        from critical_parts import refine
        def part_proposals(index,current,iteration):
            used_elsewhere={n for i,r in enumerate(current) if i!=index for n in r['members']}
            base=current[index]['members'];available=[n for n in ids if n not in used_elsewhere]
            proposed=[base]
            for outgoing in base:
                remainder=[n for n in base if n!=outgoing]
                options=sorted((n for n in available if n not in base and valid(remainder+[n],s)),key=lambda n:guidance.priority(n,remainder),reverse=True)
                for incoming in guidance.alternatives(options,remainder,iteration)[:3]:proposed.append(ordered(remainder+[incoming]))
            proposed.extend(p['members'] for p in pairing_search.replacements(base,available,guidance,catalog,lambda t:valid(t,s),limit=4))
            return proposed
        critical_search=refine(results,part_proposals,lambda t:burst_orders(t,catalog,guidance),prefetch,run,s['duration'],
                               start+search_seconds*.65,cancelled)
    # Every search reserves real rotation counterfactuals, regardless of the
    # optional CDR filter. Accept only full-fight damage gains across all donors.
    rotation_improvements=rotation_search.improve(results,ids,catalog,effects,guidance.priority,
        lambda t:valid(t,s),lambda t:burst_orders(t,catalog,guidance),prefetch,run,s['duration'],exhausted)
    # A weak healing-dependent buff deserves targeted counterfactual checks,
    # even when the replacement healer has little personal-damage weight.
    dependency_checks=[]
    def verify_dependencies(index):
        baseline=results[index]
        if exhausted():return
        used_elsewhere={n for i,row in enumerate(results) if i!=index for n in row['members']}
        proposals=healing_repairs(baseline,[n for n in ids if n not in used_elsewhere],effects,catalog,weights,lambda t:valid(t,s))
        proposals+=guidance.kits.repairs(baseline['members'],[n for n in ids if n not in used_elsewhere],weights,
            lambda t:valid(t,s),baseline.get('kit_dependencies',[]))
        expanded=[]
        for proposal in proposals:
            for order in burst_orders(proposal['members'],catalog,guidance)[:2]:
                expanded.append({**proposal,'members':list(order)})
        proposals=expanded
        prefetch([p['members'] for p in proposals],s['duration'],True,phase='Verifying support reliability and burst choices')
        best=baseline
        for proposal in proposals:
            key=(tuple(proposal['members']),s['duration'],True)
            if key not in cache:continue
            alternative=cache[key]
            dependency_checks.append({**proposal,'baseline_damage':baseline['damage'],'damage':alternative['damage'],'healing_dependencies':alternative.get('healing_dependencies',[])})
            if candidate_score(alternative)>candidate_score(best):best=alternative
        results[index]=best
    for index in range(len(results)):verify_dependencies(index)
    # Test one joint round before independent partner sweeps can use the
    # remaining budget. Keep completed evidence in cancellation checkpoints.
    if s['teams']>1 and not exhausted():
        joint_allocation_checks.extend(pairing_search.refine_allocations(results,ids,catalog,guidance,
            lambda t:valid(t,s),lambda t:burst_orders(t,catalog,guidance),prefetch,run,s['duration'],exhausted,
            required=s.get('require_critical_parts',False),rounds=1))
        checkpoint()
    package_checks=[]
    # Test the damage dealer and its partner together. Neither unit needs to
    # win an isolated replacement before their combination is evaluated.
    for index in range(len(results)):
        if exhausted():break
        baseline=results[index]
        used_elsewhere={n for i,t in enumerate(results) if i!=index for n in t['members']}
        options=pairing_search.replacements(baseline['members'],[n for n in ids if n not in used_elsewhere],
            guidance,catalog,lambda t:valid(t,s),limit=max(4,s['budget']))
        orders={}
        for option in options:
            for order in burst_orders(option['members'],catalog,guidance)[:2]:orders[order]=option
        prefetch(orders,min(30,s['duration']),phase='Screening damage dealers with their partners')
        screened=[]
        for order,option in orders.items():
            try:screened.append((candidate_score(run(order,min(30,s['duration']))),order,option))
            except (ValueError,KeyError,IndexError,TypeError):continue
        finalists=membership_shortlist(sorted(screened,reverse=True),3)
        full={order:option for _,team,option in finalists for order in burst_orders(team,catalog,guidance)}
        prefetch(full,s['duration'],True,phase='Verifying complete partner combinations')
        best=baseline
        for order,option in full.items():
            key=(tuple(order),s['duration'],True)
            if key not in cache:continue
            alternative=cache[key]
            package_checks.append({'squad':index+1,'package':option['package'],'members':list(order),
                'baseline_damage':baseline['damage'],'damage':alternative['damage']})
            if candidate_score(alternative)>candidate_score(best):best=alternative
        results[index]=best
    # Try a small number of cross-team exchanges; never optimise teams in isolation.
    if s['teams']>1:
        for a,b in [(0,1),(s['teams']-2,s['teams']-1)]:
            first,second=results[a]['members'],results[b]['members']
            for stage in ['1','2']:
                na=next((n for n in first if catalog[n]['burst']==stage),None); nb=next((n for n in second if catalog[n]['burst']==stage),None)
                if not na or not nb:continue
                ta=ordered([nb if n==na else n for n in first]); tb=ordered([na if n==nb else n for n in second])
                if not valid(ta,s) or not valid(tb,s):continue
                try:ra,rb=run(ta,s['duration'],True),run(tb,s['duration'],True)
                except (ValueError,KeyError,IndexError,TypeError):continue
                if ra['damage']+rb['damage']>results[a]['damage']+results[b]['damage']:
                    results[a],results[b]=ra,rb; first,second=ta,tb
    neighborhood_checks=[];screening_checks=[]
    stable_rounds=0
    if s['teams']==1:
        # Membership and burst priority must be optimized together. Otherwise an
        # alphabetical off-burster can veto the right replacement before testing.
        for iteration in range(64):
            if exhausted():break
            verify_dependencies(0)
            baseline=results[0]; neighbors={}
            baseline_orders=burst_orders(baseline['members'],catalog,guidance)
            prefetch(baseline_orders,s['duration'],True,phase='Checking current burst priorities')
            for candidate in baseline_orders:
                try:alternative=run(candidate,s['duration'],True)
                except (ValueError,KeyError,IndexError,TypeError):continue
                if candidate_score(alternative)>candidate_score(baseline):baseline=alternative
            results[0]=baseline
            # Rank memberships before simulation; retain alternatives per outgoing
            # slot and rotate exploratory choices so the strongest score cannot
            # monopolize every slot. Burst order stays part of verification.
            for outgoing in baseline['members']:
                options=[n for n in ids if n not in baseline['members'] and valid([n if x==outgoing else x for x in baseline['members']],s)]
                remainder=[x for x in baseline['members'] if x!=outgoing]
                options.sort(key=lambda n:guidance.priority(n,remainder)+guide_priority(n,remainder,s),reverse=True)
                chosen=guidance.alternatives(options,remainder,iteration)
                for incoming in chosen:
                    candidate=[incoming if n==outgoing else n for n in baseline['members']]
                    if valid(candidate,s):
                        orders=burst_orders(candidate,catalog,guidance)
                        # Two different priorities per membership for screening;
                        # Guide-ranked priorities of promoted teams get full fights.
                        for order in orders[:1]+orders[1+iteration%max(1,len(orders)-1):][:1]:neighbors[order]=(outgoing,incoming)
            screened=[]
            progress(phase=f'Refining promising teams · round {iteration+1}',simulations=sims)
            prefetch(neighbors,min(30,s['duration']),phase=f'Testing promising replacements · {executor.workers} workers')
            for candidate,change in neighbors.items():
                audit={'pass':iteration+1,'members':list(candidate),'outgoing':change[0],'incoming':change[1],'duration':min(30,s['duration'])}
                try:
                    sample=run(candidate,min(30,s['duration']))
                    screened.append((candidate_score(sample),candidate,change));audit.update(status='screened',damage=sample['damage'])
                except (ValueError,KeyError,IndexError,TypeError) as e:audit.update(status='excluded',reason=str(e))
                screening_checks.append(audit)
            promoted=membership_shortlist(screened,3)
            full_orders={order:change for _,team,change in promoted for order in burst_orders(team,catalog,guidance)}
            promoted_sets={frozenset(t) for t in full_orders}
            for audit in screening_checks:
                if audit['pass']==iteration+1:audit['full_duration_promoted']=frozenset(audit['members']) in promoted_sets
            prefetch(full_orders,s['duration'],True,phase='Verifying full fight damage and off-burst choices')
            best=baseline
            for candidate,(outgoing,incoming) in full_orders.items():
                try:alternative=run(candidate,s['duration'],True)
                except (ValueError,KeyError,IndexError,TypeError) as e:
                    neighborhood_checks.append({'pass':iteration+1,'members':list(candidate),'outgoing':outgoing,'incoming':incoming,'status':'excluded','reason':str(e)});continue
                neighborhood_checks.append({'pass':iteration+1,'members':list(candidate),'outgoing':outgoing,'incoming':incoming,'status':'tested','damage':alternative['damage'],'baseline_damage':baseline['damage'],'stop_reason':(alternative.get('encounter_timeline') or {}).get('stop_reason')})
                if candidate_score(alternative)>candidate_score(best):best=alternative
            results[0]=best
            stable_rounds=stable_rounds+1 if candidate_score(best)<=candidate_score(baseline) else 0
            # Two unchanged rounds cover both recommended and exploratory picks.
            # Avoid repeatedly simulating the same neighborhood until the timer.
            if stable_rounds>=2:break

    # Reserve joint partnership verification before the final local sweeps;
    # those sweeps must not consume the budget needed to evaluate donor teams.
    if s['teams']>1 and not exhausted():
        joint_allocation_checks.extend(pairing_search.refine_allocations(results,ids,catalog,guidance,
            lambda t:valid(t,s),lambda t:burst_orders(t,catalog,guidance),prefetch,run,s['duration'],exhausted,
            required=s.get('require_critical_parts',False),rounds=3))
        checkpoint()
    # Test real owned replacements, keeping all other squads fixed and disjoint.
    replacement_checks=[]
    for index in range(len(results)):
        if exhausted():break
        progress(phase=f'Verifying owned alternatives {index+1}/{len(results)}',simulations=sims)
        used={n for row in results for n in row['members']}
        baseline=results[index]
        proposed=[]
        for outgoing in baseline['members']:
            remainder=[n for n in baseline['members'] if n!=outgoing]
            options=sorted((n for n in ids if n not in used and catalog[n]['burst']==catalog[outgoing]['burst']),key=lambda n:guidance.priority(n,remainder),reverse=True)
            for incoming in options[:4]:
                candidate=[incoming if n==outgoing else n for n in baseline['members']]
                if valid(candidate,s):proposed.append((guidance.priority(incoming,remainder),outgoing,incoming,list(burst_orders(candidate,catalog,guidance)[0])))
        prefetch([t for _,_,_,t in sorted(proposed,reverse=True)[:4]],s['duration'],True)
        best=baseline
        for _,outgoing,incoming,candidate in sorted(proposed,reverse=True)[:4]:
            try:alternative=run(candidate,s['duration'],True)
            except (ValueError,KeyError,IndexError,TypeError) as e:
                replacement_checks.append({'squad':index+1,'outgoing':outgoing,'incoming':incoming,'status':'excluded','reason':str(e)})
                continue
            delta=alternative['damage']-baseline['damage']
            replacement_checks.append({'squad':index+1,'outgoing':outgoing,'incoming':incoming,'status':'tested','baseline_damage':baseline['damage'],'alternative_damage':alternative['damage'],'delta_pct':round(100*delta/max(1,baseline['damage']),2),'baseline_members':baseline['members']})
            if candidate_score(alternative)>candidate_score(best):best=alternative
        results[index]=best
    rotation_checks=[]
    for index,baseline in enumerate(results):
        if exhausted():break
        orders=burst_orders(baseline['members'],catalog,guidance)
        prefetch(orders,s['duration'],True,phase='Comparing burst priorities')
        best=baseline
        for order in orders:
            candidate=list(order)
            try:alternative=run(candidate,s['duration'],True)
            except (ValueError,KeyError,IndexError,TypeError):continue
            rotation_checks.append({'squad':index+1,'members':candidate,'damage':alternative['damage']})
            if candidate_score(alternative)>candidate_score(best):best=alternative
        results[index]=best
    from critical_parts import select_tested,selection_report
    results=select_tested([r for k,r in cache.items() if k[1]==s['duration'] and k[2]],s['teams'],s.get('require_critical_parts'),[results])
    critical_selection=selection_report(results,s['teams']) if s.get('require_critical_parts') else None
    if critical_selection:critical_selection['screening']=critical_search
    for result in results:result['search_guidance']=guidance.report(result['members'])
    for check in replacement_checks:
        check['selected']=check['incoming'] in results[check['squad']-1]['members']
    survival_model_stops=[{'members':list(key[0]),'damage':entry['damage'],
                          'simulated_until':entry['encounter_timeline'].get('simulated_until'),
                          'reason':entry['encounter_timeline']['stop_reason']}
                         for key,entry in cache.items() if key[1]==s['duration'] and key[2]
                         and (entry.get('encounter_timeline') or {}).get('stop_reason')]
    ranking_warnings=[]
    if survival_model_stops:
        ranking_warnings.append('Ranking is sensitive to unverified survival predictions: '
                      f'{len(survival_model_stops)} full-duration candidates stopped early in the experimental boss model. '
                      'A lower score from a modeled death does not establish that the team is worse in game.')
    return {'compute':{'mode':s['compute_mode'],'workers':executor.workers,'backend':'GPU exploration + CPU verification' if compute['gpu_used'] else 'CPU processes',**compute},'selection':{'critical_parts':critical_selection,'joint_allocation_checks':joint_allocation_checks,'rotation_improvements':rotation_improvements,'pairing_packages':package_audit,'package_checks':package_checks,'dependency_checks':dependency_checks,'survival_model_stops':survival_model_stops,'screening_checks':screening_checks,'rotation_checks':rotation_checks,'neighborhood_checks':neighborhood_checks,'replacement_checks':replacement_checks,'objective':'Reward progress, then interruption reliability, remaining HP and clear time.' if s['content_mode']=='special' else 'Simulated damage', 'method':('Investment- and guide-ranked replacement shortlists with rotating exploration; promising memberships receive full-fight burst-priority verification.' if s['teams']==1 else 'Build-aware shortlist, 30-second screening, full-duration finalists and cross-team support swaps.')+' Rotation alternatives receive 60-second screening and full-fight damage verification, including affected donor squads, regardless of the CDR filter. Final unused-unit comparisons follow; this is a bounded search of simulated teams, not exhaustive optimization.'+(' Critical-part candidates are screened by damage dealt before their deadlines, then verified through full fights within the same time limit.' if s.get('require_critical_parts') else ''),'full_duration_finalists':comparisons,'optimality':'Best tested allocation; not an exhaustive optimum.'},'teams':results,'total':sum(t['damage'] for t in results),'elapsed':round(time.perf_counter()-start,2),'simulations':sims,'plans_considered':len(plans),'settings':public_settings(s),'warnings':imported['warnings']+ranking_warnings+(['Some candidates were excluded: '+ '; '.join(sorted(set(errors))[:3])] if errors else []),'assumptions':sorted({str(note) for n in {n for t in results for n in t['members']} for r in [roster[n]] for note in r['assumptions']}),'limitations':encounters.notes(s)+[damage_model_note(s),'Expected critical/core hits; fixed seed. Skill support is upstream implementation coverage, not a guarantee of in-game accuracy.',('The selected search depth is a hard computation limit, including critical-part searches. Deadline-focused samples prioritize full-fight tests. A fallback means no fully passing allocation was found within the tests completed, not that every possible team was exhausted.' if s.get('require_critical_parts') else 'Bounded search, not a proof of the best roster allocation. Short screening can miss slow-ramping teams.'),('Automatic boss models require matching-element access and evaluate actual interruption and barrier hits; a total-damage percentage is not used in place of those mechanics.' if s['boss_id']=='museum-mother-whale' or s['boss_id'] in encounters.RAID_PROFILES else 'Element-locked QTE bosses require a matching damage dealer among the top three contributors with at least 15% of simulated damage, regardless of Burst stage or class. This is a composition safeguard, not a QTE pass guarantee.')]}

def manual(payload):
    s=validate_settings(payload.get('settings',{})); rows=import_roster({'roster':payload.get('roster',[])})['roster']
    ids=payload.get('members',[])
    if len(ids)!=5 or len(set(ids))!=5:raise ValueError('Select five different units, in burst-priority order.')
    by={r['id']:r for r in rows}
    if any(n not in by or not CAT[n]['supported'] for n in ids):raise ValueError('All five units must be owned and have supported skill kits.')
    barrier=s['encounter'].get('barrier_element')
    if barrier and not any(barrier in CAT[n]['barrier_elements'] for n in ids):raise ValueError(f'This boss needs a {barrier} unit for its code barrier.')
    s['_catalog']=resolve_catalog({n:by[n] for n in ids})
    if s['content_mode']=='campaign':return campaign_result([(ids,)],by,s,time.perf_counter())
    # Reuse the same simulation policy through a one-plan search runner below.
    return simulate_manual(ids,by,s)

def simulate_manual(ids,by,s):
    if s.get('require_critical_parts') and not s.get('_aim_controller'):
        from critical_parts import assessment
        start=time.perf_counter()
        alternatives=[simulate_manual(ids,by,dict(s,_aim_controller=n)) for n in ids]
        chosen=max(alternatives,key=lambda r:(assessment(r['teams'][0])['passed'],candidate_score(r['teams'][0])))
        team=chosen['teams'][0]
        team['control_comparison']=[dict(unit=r['teams'][0]['encounter_timeline']['off_burst_controller'],damage=r['total'],parts_passed=assessment(r['teams'][0])['passed']) for r in alternatives]
        team['critical_part_requirement']=assessment(team)
        chosen['elapsed']=round(time.perf_counter()-start,2);chosen['simulations']=5
        return chosen
    catalog=s.get('_catalog',CAT)
    catalog=resolve_catalog({n:by[n] for n in ids}); s['_catalog']=catalog
    start=time.perf_counter(); chars={n:copy.deepcopy(by[n]['build']) for n in ids}
    for b in chars.values():b['level']=encounters.unit_level(b,s)
    squad=spec.build_squad(ids,chars=chars,no_layer=set(ids))
    if s['playstyle']=='assisted':
        tactics=spec.tactic_overrides('버충',ids)
        for c in squad:c['control']=spec.deep_merge(c.get('control',{}),tactics.get(c['name'],{}).get('control',{}))
    cfg=spec.build_config(squad,{'duration':s['duration'],'rng_mode':'expected','burst_gauge_mode':'accumulate','burst_switch_delay':.5 if s['playstyle']=='auto' else .1})
    cfg.update(encounters.config(s,s['duration']))
    if cfg.get('encounter_runtime'):cfg['encounter_runtime'].element_access={n:[ELEMENT_KO[x] for x in catalog[n]['barrier_elements']] for n in ids}
    r=simulate(squad,cfg,{'def':s['def'],'code':ELEMENT_KO.get(s['enemy_element']),'core_px':s['core_px'],'has_parts':s['has_parts'],'optimal_range_weapons':s['optimal_range_weapons']},verbose=True,seed=42)
    t={'members':ids,'damage':r.squad_total,'dps':r.squad_total/s['duration'],'duration':s['duration'],'breakdown':r.char_total,'burst_log':[{'time':round(e.t,2),'event':e.event,'unit':e.caster} for e in r.log.burst_log],'bursts':sum(e.event=='full_burst 시작' for e in r.log.burst_log),'deviations':spec.format_deviations(squad),'builds':squad,'warnings':[],'timeline':[],'team_cdr_activations':active_team_cdr(r),'mechanics':encounters.assessment(s,ids,catalog),'encounter_timeline':getattr(r,'encounter_report',None),'support_plan':encounters.support_report(ids,s,catalog)}
    t['kit_dependencies']=KitDependencies({n:char_effects(n,by[n]['build']['favorite_stage']) for n in by},META,catalog).inspect(ids,r)
    t['burst_rotation']=burst_rotation.report(ids,catalog,r.log.burst_log,s['duration'],cfg['burst_switch_delay'],observed_until=(getattr(r,'encounter_report',None) or {}).get('simulated_until'))
    t['warnings'].extend(burst_rotation.warnings(t['burst_rotation']))
    t['recommendation']=evidence_report(r,ids,by,s,catalog)
    t['warnings'].extend(t['recommendation']['warnings'])
    t['elemental_damage']=elemental_damage_report(t,s,catalog)
    if t['elemental_damage'] and not t['elemental_damage']['providers']:
        t['warnings'].append('No substantial '+t['elemental_damage']['element']+' damage dealer. This manual lineup would be excluded from recommendations for this element-locked QTE boss.')
    attach_combat_assessment(t)
    if t['encounter_timeline'] and not t['encounter_timeline'].get('model') and any(c['status']=='failed' for c in t['encounter_timeline']['checks']):
        t['mechanics']['status']='Scripted QTE failed'
        t['warnings'].append('A QTE failed; damage after a scripted wipe is not counted.')
    t['timeline']=[0]*math.ceil(s['duration']/5)
    for hit in r.hits:t['timeline'][min(int(hit.t/5),len(t['timeline'])-1)]+=hit.damage
    return {'teams':[t],'total':r.squad_total,'elapsed':round(time.perf_counter()-start,2),'simulations':1,'settings':public_settings(s),'warnings':[],'assumptions':sorted({str(x) for row in by.values() for x in row['assumptions']}),'limitations':encounters.notes(s)+[damage_model_note(s),'Manual slot order is preserved.']}


def campaign_result(plans,roster,s,start,progress=lambda **kw:None,cancelled=lambda:False,guidance=None):
    catalog=s.get('_catalog',CAT)
    # Campaign is a composition assessment, not a stationary boss DPS ranking.
    from calculator.base_stat import calc_base_stats
    best=None
    for plan in plans:
        if cancelled():raise InterruptedError('Search cancelled.')
        team=list(plan[0]);tags={t for n in team for t in catalog[n]['tags']}
        deficit=s['cp_deficit']/100
        strength=guidance.score(team) if guidance else sum(heuristic([n],roster,s) for n in team)
        utility=1+(.8+deficit)*('AoE' in tags)+.5*('CDR' in tags)+.2*('Healing' in tags)+.15*('Shield' in tags)
        if s['campaign_objective']!='battle':utility+=.35*('AoE' in tags)+.2*('Healing' in tags)
        score=strength*utility
        if best is None or score>best[0]:best=(score,team,tags)
    _,team,tags=best
    chars={n:copy.deepcopy(roster[n]['build']) for n in team}
    squad=spec.build_squad(team,chars=chars,no_layer=set(team))
    multiplier=1-s['stat_penalty']/100
    stats={c['name']:{k:round(v*multiplier) for k,v in calc_base_stats(c).items()} for c in squad}
    reasons=['Area damage available' if 'AoE' in tags else 'No area-damage skill detected; wave clear may struggle',
             'Team cooldown reduction available' if 'CDR' in tags else 'No team cooldown reduction detected',
             'Team healing available' if 'Healing' in tags else 'No team healing detected']
    progress(phase='Checking stage composition',simulations=0)
    return {'kind':'campaign','teams':[{'members':team,'reasons':reasons,'effective_stats':stats,'builds':squad}],
            'settings':public_settings(s),'simulations':0,'elapsed':round(time.perf_counter()-start,2),'plans_considered':len(plans),
            'warnings':[], 'assumptions':['Entered CP deficit is an assumed value for this team; compare its actual in-game CP against the stage before using the estimate.'],
            'limitations':['Composition recommendation only. Wave spawns, enemy HP, targeting and stage objectives are not simulated, so no DPS or clear claim is shown.',
                            'Effective ATK, HP and DEF use the published CP penalty table. This is a stat penalty, not a direct final-damage multiplier.']}


def guide_priority(n,team,s):
    catalog=s.get('_catalog',CAT)
    g=s.get('encounter',{}).get('guidance',{}) if s.get('survival_policy','guide')=='guide' else {}
    tags={tag for x in team for tag in catalog[x]['tags']}
    missing=set(g.get('required_tags',[]))-tags
    bonus=1.4*bool(missing&set(catalog[n]['tags']))
    barrier=s.get('encounter',{}).get('barrier_element')
    if barrier and not any(barrier in catalog[x]['barrier_elements'] for x in team) and barrier in catalog[n]['barrier_elements']:bonus+=1.0
    if s.get('cdr') and 'CDR' not in tags and 'CDR' in catalog[n]['tags']:bonus+=1.0
    return bonus
