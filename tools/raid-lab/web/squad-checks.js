'use strict';

function burstTimingCheck(team, duration) {
 const rotation=team.burst_rotation;
 const windows=rotation?.full_bursts, stages=rotation?.stage_delays;
 if(!Array.isArray(windows)||!Array.isArray(stages)||!stages.length)return null;
 const until=Number.isFinite(team.encounter_timeline?.simulated_until)?Math.min(duration,team.encounter_timeline.simulated_until):duration;
 if(!(until>0))return null;
 const starts=stages.filter(s=>s.stage==='1'&&Number.isFinite(s.cast_time)).map(s=>s.cast_time).sort((a,b)=>a-b);
 if(!starts.length)return null;
 // Exclude the opening burst and windows cut short by the end of the fight.
 const cycles=windows.filter(w=>w.complete===true&&Number.isFinite(w.end)&&w.end+5<=until).map(w=>{
  const next=starts.find(t=>t>=w.end);
  return {end:w.end,delay:next===undefined?null:Math.round((next-w.end)*100)/100};
 });
 if(!cycles.length)return null;
 const passed=cycles.filter(c=>c.delay!==null&&c.delay<=5).length;
 return {passed,total:cycles.length,majority:passed>cycles.length/2};
}

// Status describes recorded evidence, not a promise of an in-game clear.
function squadCheckItems(team, settings, names={}) {
 const items=[], add=(key,label,state,value,detail)=>items.push({key,label,state,value,detail});
 const fight=team.encounter_timeline, rotation=team.burst_rotation;
 const duration=Number(team.duration||settings.duration||0);
 const partObjectives=settings.encounter?.critical_parts||[];
 const fullRun=duration>0&&Number.isFinite(fight?.simulated_until)&&fight.simulated_until>=duration-.1;
 const completedRoute=fullRun||fight?.target_reached===true;
 const element=team.elemental_damage;
 if(element) add('element','Element',element.providers?.length?'pass':'fail',element.providers?.length?`${element.element} covered`:`${element.element} missing`,
  element.assessment==='modeled-barrier'?element.criterion:element.providers?.length?`${element.providers.map(n=>names[n]||n).join(', ')} passed the matching damage-contribution screen. This does not establish enough circle damage before a QTE deadline.`:'No matching unit passed the damage-contribution screen. An element label alone is insufficient.');
 else add('element','Element',settings.encounter?.barrier_element?'unknown':'info',settings.encounter?.barrier_element?'Unverified':'Not required',settings.encounter?.barrier_element?'This saved result has no elemental-damage assessment.':'This result has no mandatory elemental damage screen.');

 if(fight?.control_plan?.length) add('aim','Off-burst aim','info',names[fight.off_burst_controller]||fight.off_burst_controller,'Outside Full Burst, control the recommended Nikke and aim at the listed part. Only that unit follows aim, unless an active Focus Fire effect redirects allies. See the control plan for target windows and tested alternatives.');
 const core=fight?.critical_parts?.find(p=>p.id==='mother-whale-core');
 if(core) add('parts','Critical parts',core.status==='passed'?'pass':core.status==='failed'?'warn':'unknown',core.status==='passed'?'Core break passed':core.status==='failed'?'Opening break missed':'Not yet observed',
  `Core HP: ${Math.round(core.hp).toLocaleString()}. ${core.destroyed_at!=null?`Destroyed at ${core.destroyed_at.toFixed(2)}s.`:`${Math.round(core.remaining_hp).toLocaleString()} HP remains.`} ${core.deadline!=null?`First protection wave deadline: ${core.deadline.toFixed(2)}s.`:'No protection wave activated in the observed interval.'} Actual targeted hits determine the break. Summons can instead be cleared before protection or defeated afterward; it is not automatically a failed fight.`);
 else if(fight?.critical_deadlines_supported) {
  const checks=fight.critical_deadlines||[],passed=checks.filter(p=>p.status==='passed').length,failed=checks.some(p=>p.status==='failed');
  const disabled=fight.special_interception&&completedRoute&&!checks.length&&fight.critical_parts?.some(p=>p.id==='Weapon_03'&&p.destroyed_at!=null);
  add('parts','Critical parts',failed?'warn':completedRoute&&(passed===checks.length)&&Boolean(checks.length||disabled)?'pass':'unknown',disabled?'Core disabled':checks.length?`${passed}/${checks.length} deadlines`:'No deadline reached',disabled?'The core was destroyed before a second beam deadline was needed on this completed route.':checks.length?checks.map(p=>`${p.part}: ${p.status}; deadline ${p.deadline.toFixed(2)}s${p.destroyed_at!=null?`, destroyed ${p.destroyed_at.toFixed(2)}s`:''}.`).join(' '):'No part-dependent attack deadline was reached during this modeled route.');
 }
 else if(fight?.critical_parts?.length) {
  const parts=fight.critical_parts,passed=parts.filter(p=>p.status==='passed').length,missed=parts.filter(p=>p.status==='failed').length;
  add('parts','Critical parts',missed?'warn':passed===parts.length?'pass':'info',`${passed}/${parts.length} breaks`,parts.map(p=>`${p.part}: ${Math.round(p.hp).toLocaleString()} HP. ${p.destroyed_at!=null?`Destroyed at ${p.destroyed_at.toFixed(2)}s.`:`${Math.round(p.remaining_hp).toLocaleString()} HP remains.`} ${p.deadline!=null?`Attack deadline ${p.deadline.toFixed(2)}s.`:'No attack deadline observed.'}`).join(' '));
 }
 else if(partObjectives.length) add('parts','Critical parts','unknown','Break unverified',
  partObjectives.map(p=>`${p.part}: ${p.objective} ${p.consequence} ${p.alternative} Not established by this simulation: ${(p.missing||[]).join(', ')}. Total DPS and a passing burst-timing check do not prove a part break.`).join(' '));

 const checks=fight?.checks||[];
 if(fight?.qte_route_skipped) add('qte','QTE','info','Route avoided','No circle check appeared on this completed Modernia route. Keeping a wing intact avoids the repeated teleport checks. Core destruction, bombs and survival are assessed separately.');
 else if(fight?.special_interception&&completedRoute&&!checks.length) add('qte','QTE','info','Not encountered','No circle check occurred before this route ended. This is not a circle-damage pass; check the reward stage and survival result.');
 else if(fight?.special_interception&&fight.stop_reason&&!checks.length) add('qte','QTE','info','Not reached','The run stopped at a squad death before a circle check appeared. The QTE model is active, but this team has no circle-clearance evidence. Inspect Survival first.');
 else if(fight?.qte_required===false) add('qte','QTE','info','Not applicable','This boss variant uses summon clearing and an elemental barrier rather than a timed circle QTE. See Critical parts and Summons for those outcomes.');
 else if(checks.some(c=>c.status==='failed')) add('qte','QTE','fail','Failed in model','At least one scripted interruption check failed. Inspect the mechanic details for the failed target and timing.');
 else if(checks.length&&checks.every(c=>c.status==='passed')&&completedRoute) add('qte','QTE','pass','Scripted checks passed',`${checks.length} scripted checks passed before ${fight?.target_reached?'the maximum reward stage was reached':'the full simulated fight ended'}. This covers only the modeled targets and deadlines; unmodeled mechanics and aiming remain unverified.`);
 else add('qte','QTE','unknown',checks.length?'Incomplete':'Unverified',checks.length?'Some checks are pending, unknown, or the simulated fight ended early. There is not enough evidence for a full-fight QTE pass.':'No calibrated QTE checks were recorded. Correct element and high team DPS do not prove circle clearance.');

 if(fight?.model&&(fight.stop_reason||fight.survival==='failed')) add('survival','Survival','fail','Stopped in model',`${fight.stop_reason||'The survival model reported a failure.'} This result depends on the model\u2019s approximate incoming damage.`);
 else if(fight?.model&&fight.target_reached&&fight.survival==='survived modeled attacks') add('survival','Survival','pass','Stage 9 reached',`The squad remained alive until the maximum reward threshold at ${fight.simulated_until}s. Finite cover, shields, healing and incoming attacks were modeled. This is not a verified in-game clear.`);
 else if(fight?.model&&fullRun&&fight.survival==='survived modeled attacks') add('survival','Survival','pass','Survived in model',`The squad survived modeled attacks for ${duration}s. Incoming damage and boss behavior still need gameplay calibration.`);
 else add('survival','Survival','unknown','Unverified',fight?.model?'The attack simulation did not establish survival through the full requested duration.':'A stationary damage simulation does not test survival. A complete calibrated incoming-attack model is needed to establish this.');
 if(Array.isArray(fight?.summons)&&fight.summons.length) {
  const cleared=fight.summons.filter(a=>a.clear_reason?.startsWith('squad')).length;
  const alive=fight.summons.filter(a=>a.hp>0).length;
  const windows=fight.barrier_windows||[];
  const blocked=windows.reduce((sum,w)=>sum+(w.end??fight.simulated_until)-w.start,0);
  add('summons','Summons',alive?'warn':'info',`${cleared}/${fight.summons.length} cleared`,`${cleared} summons cleared by the squad; ${alive} remain at the end. Boss sweeps and scripted withdrawals are counted separately. ${Math.round(fight.damage_to_adds||0).toLocaleString()} effective summon HP damage is excluded from direct boss damage. The elemental barrier was active for ${blocked.toFixed(2)}s. Individual hits and actual clear times determine this result.`);
 }
 if(fight?.summon_control) {
  const control=fight.summon_control,casts=control.protection_casts,precleared=control.precleared_casts||0;
  const clean=casts>0&&control.casts_with_survivors===0&&precleared===casts;
  const state=control.casts_with_survivors>0?'warn':fullRun&&(clean||control.core_disabled_protection)?'pass':'unknown';
  const value=casts>0?`${precleared}/${casts} waves pre-cleared`:control.core_disabled_protection?'Protection disabled':'No buff cast observed';
  add('summon-control','Summon control',state,value,
   `${precleared} protection casts followed actual squad clearance of the preceding summons. ${control.casts_with_survivors} casts found surviving summons; ${control.protected_adds} distinct summons received protection. ${control.core_disabled_protection?'Core destruction disabled subsequent protection casts. ':''}Clearing summons before a cast is a valid alternative to breaking the core. An AoE tag alone earns no pass; actual target HP and death times determine the outcome. Opening and later waves are counted separately from the core deadline.`);
 }
 if(fight?.choices?.length) add('choices','Attack choices','info',`${fight.choices.length} selected`,fight.choices.map(c=>`${c.time.toFixed(2)}s: ${c.route==='projectile'?'crystal sphere / hit-count route':'ATK reduction / cleanse route'}`).join('; '));
 if(fight?.cover_windows?.length) {
  const blocks=(fight.incoming||[]).filter(h=>h.blocked_by==='cover').length;
  add('cover','Cover','info',`${blocks} hits blocked`,fight.cover_windows.slice(0,12).map(w=>`${names[w.unit]||w.unit}: ${w.start.toFixed(2)}–${(w.end??fight.simulated_until).toFixed(2)}s (${w.reason}).`).join(' ')+` Firing pauses during these windows. Cover HP is finite; ${blocks} hits were absorbed by cover.`);
 }
 if(fight?.projectiles?.length) {
  const passed=fight.projectiles.filter(p=>p.status==='passed').length,failed=fight.projectiles.some(p=>p.status==='failed');
  add('projectiles','Projectiles',failed?'warn':passed===fight.projectiles.length?'pass':'unknown',`${passed}/${fight.projectiles.length} stopped`,fight.projectiles.slice(0,12).map(p=>`${Math.round(p.max_hp).toLocaleString()} ${p.kind==='hp'?'HP':'hits'} required; ${Math.round(p.hp).toLocaleString()} remain. Deadline ${p.deadline.toFixed(2)}s. ${p.status==='passed'?`Destroyed at ${p.destroyed_at.toFixed(2)}s.`:p.status==='failed'?'Hit the squad.':'Still in flight.'}`).join(' ')+(fight.projectiles.length>12?' Showing the first 12 projectiles.':''));
 }

 const stages=rotation?.support_stages||[];
 const cycling=team.bursts>=2&&['1','2'].every(s=>stages.some(r=>r.stage===s&&r.status==='observed'&&r.casts>=2));
 if(rotation?.covered===false) add('chain','Burst chain','fail','Coverage gap','A long-cooldown support stage had uncovered delays. Check B1/B2 backups and actual cooldown reduction.');
 else if(cycling) add('chain','Burst chain','pass','Cycling',`${team.bursts} Full Bursts completed and both support stages repeated. This is observed rotation coverage, not proof of the globally optimal burst order.`);
 else add('chain','Burst chain','unknown','Unverified','There are too few recorded support cycles to establish sustained burst coverage.');

 const timing=burstTimingCheck(team,duration);
 if(timing) add('wait','Burst timing',timing.majority?'pass':'warn',`${timing.passed}/${timing.total} within 5s`,
  `${timing.passed} of ${timing.total} follow-up burst cycles started within 5 seconds after the previous Full Burst ended. Pass requires more than half. Uses actual B1 activation, including gauge refill and cooldown delays, and each recorded Full Burst end, so shortened or extended bursts are respected. The opening cycle and endings with less than 5 seconds left to observe are excluded. Planned cover or boss downtime can delay activation.`);
 else add('wait','Burst timing','unknown','Unverified','No follow-up cycle with a complete 5-second observation window was recorded. The opening burst is excluded.');
 add('uptime','Full Burst',Number.isFinite(rotation?.uptime_pct)?'info':'unknown',Number.isFinite(rotation?.uptime_pct)?`${rotation.uptime_pct}% uptime`:'Unverified',
  Number.isFinite(rotation?.uptime_pct)?`${rotation.full_burst_seconds}s of the ${rotation.observed_duration??duration}s observed fight was spent in Full Burst. Longer uptime is not always better: duration-changing units, fixed buff expiry, gauge generation and total damage must be considered together.`:'Full Burst window durations are unavailable in this result.');

 const healers=team.recommendation?.available_healers;
 if(!Array.isArray(healers)) add('healing','Healing','unknown','Unverified','No healing assessment is available in this result.');
 else if(healers.length) add('healing','Healing','info','Available',`${healers.map(n=>names[n]||n).join(', ')} can provide healing in this build and rotation. Availability does not establish sufficient recovery or survival.`);
 else add('healing','Healing',settings.healing||settings.encounter?.guidance?.required_tags?.includes('Healing')?'warn':'info','None available','No usable team healer was established. This is not an automatic failure when the encounter does not require healing.');

 const partners=team.kit_dependencies;
 if(!Array.isArray(partners)) add('partners','Partners','unknown','Unverified','Partner activation data is unavailable in this result.');
 else if(!partners.length) add('partners','Partners','info','None tracked','No external partner requirements were tracked for these skill kits. This does not certify that every possible interaction is modeled.');
 else {
  const inactive=partners.filter(p=>['missing enabler','not activated'].includes(p.status));
  const active=partners.filter(p=>p.status==='activation observed');
  add('partners','Partners',inactive.length?'warn':active.length===partners.length?'pass':'unknown',inactive.length?`${inactive.length} inactive`:active.length===partners.length?'Activated':'Unverified',
   `${active.length}/${partners.length} tracked dependent effects activated. ${inactive.length?inactive.map(p=>`${names[p.unit]||p.unit}: ${p.status}`).join('; ')+'. ':''}Checks apply to individual effects; activation alone does not establish sufficient buff uptime or optimal pairing.`);
 }
 return items;
}

if(typeof module!=='undefined')module.exports={squadCheckItems,burstTimingCheck};
