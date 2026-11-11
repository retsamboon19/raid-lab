// Prepared current153-only adapter; no native validation claim. Historical input remains preserved.
// Source-bound, reactive QTE input policy for installed NK.Spot. No predicted
// sequence, native writes, collider calls, or future RNG. Its inputs are the
// existing original tactical observer and original input adapter snapshots.
// Current153 selected source: OnQuickTimeColliderHit 070F3780 compares
// native ColType Counter(2) and nonzero native order before emitting failure.
// This policy reads the original preset IsSuccess getter 065BD520; it never
// computes or assigns success. Charge weapons release only after the original
// weapon reports IsFullCharge. No claim about element-based eligibility.
function createMechanicsQtePolicy(actions,emit,configuration={}) {
  if (!actions || typeof actions.snapshot!=="function" ||
      typeof actions.release!=="function" || typeof actions.setAutoAim!=="function" ||
      typeof actions.focus!=="function" || typeof actions.aimWorld!=="function" ||
      typeof actions.projectWorld!=="function" || typeof actions.press!=="function" || typeof emit!=="function")
    throw new Error("Original QTE policy requires the original input adapter and emit");
  const firing=createMechanicsFiringPolicy(actions,{nativeInputTypes:true});
  const version="reactive-qte-v2",reactionTicks=3,settleTicks=3;
  const weaponPriority={SMG:0,AR:1,MG:2,AS:3,SR:4,SG:5,RL:6,GL:7};
  const actorEvidence=configuration.actorEvidence||null;
  const suppression=createMechanicsQteSuppression(actions,emit,configuration.offensiveSuppression===true,{readFriendlyProjectiles:configuration.readFriendlyProjectiles,retainDeadOwnerProjectiles:configuration.suppressionGrayOnly===true});
  let evidenceReads=0,lastActorScores=[];
  const unsupported=new Set(),groups=new Set();
  let lastTick=-1,episode=0,episodeStart=-1,startEventTick=-1;
  let groupId=null,presetIndex=null,presetSeenTick=-1,
    presetStartEventTick=-1,completed=false;
  const seenPresetIds=new Set();
  let owned=false,actorId=null,targetId=null,targetSeenTick=-1,priorAuto=null,activeWeaponIdentity=null;
  let decisions=0,selected=0,nativePresetSuccesses=0,nativePresetFailures=0;
  let nativeTerminalSuccesses=0,nativeTerminalFailures=0,lastEndKey=null;
  let fault=null,closed=false,suspended=false,suspendSawCover=false;
  const note=(action,detail={})=>{
    decisions++;
    emit({status:"original_reactive_qte_decision",policyVersion:version,
      episode,action,...detail});
  };
  const validInt=(value,min=0)=>Number.isSafeInteger(value)&&value>=min;
  const finite=value=>typeof value==="number"&&Number.isFinite(value);
  const releasePress=()=>{
    if (owned && actions.controlFlag("inputType")===2) actions.release();
  };
  function releaseControl(tick,reason) {
    if (!owned) return;
    const previousActor=actorId,errors=[];
    try{releasePress();}catch(e){errors.push(e);}
    try{firing.reset();}catch(e){errors.push(e);}
    try{if(!suppression.active()&&actions.controlFlag("autoAim")===false)actions.setAutoAim(priorAuto);}catch(e){errors.push(e);}
    finally{owned=false;actorId=null;targetId=null;targetSeenTick=-1;priorAuto=null;activeWeaponIdentity=null;note("release_manual_control",{tick,reason,actorId:previousActor,cleanupErrors:errors.map(String)});}
    if(errors.length)throw errors[0];
  }
  function markUnsupported(tick,reason) {
    if (!unsupported.has(reason)) {
      unsupported.add(reason);note("unsupported",{tick,reason});
    }
  }
  function unsupportedAt(tick,reason) {
    markUnsupported(tick,reason);
    releaseControl(tick,reason);
    if (presetSeenTick>=0) presetSeenTick=tick;
  }
  function suspend(tick,reason="higher_priority_cover") {
    if (closed || fault!==null) return;
    try {
      if (!validInt(tick)) throw new Error("QTE suspend requires an original tick");
      if (!suspended) {
        releaseControl(tick,reason);suppression.restore(reason);
        suspended=true;suspendSawCover=Boolean(actions.controlFlag("forcedCover"));
        note("suspend_for_cover",{tick,reason});
      }
    } catch(error) { fault="suspend: "+String(error); }
  }
  function resume(tick) {
    if (closed || fault!==null || !suspended) return false;
    try {
      if (!validInt(tick)) throw new Error("QTE resume requires an original tick");
      if (actions.controlFlag("forcedCover")) return false;
      suspended=false;suspendSawCover=false;
      presetSeenTick=tick;targetId=null;targetSeenTick=-1;
      note("resume_after_cover",{tick});
      return true;
    } catch(error) { fault="resume: "+String(error);return false; }
  }
  function resetEpisode(tick,reason) {
    releaseControl(tick,reason);suppression.restore(reason);
    groupId=null;presetIndex=null;presetSeenTick=-1;
    episodeStart=-1;startEventTick=-1;presetStartEventTick=-1;
    completed=false;lastEndKey=null;seenPresetIds.clear();
  }
  function recordEnd(tick,end,nativePresetSuccess=null) {
    if (!end) return;
    if (!validInt(end.tick) || typeof end.success!=="boolean" ||
        typeof end.end!=="boolean") {
      markUnsupported(tick,"native_preset_end_fields_incomplete");return;
    }
    if (end.tick<episodeStart) return;
    if (seenPresetIds.size && !seenPresetIds.has(end.presetInfoId)) {
      markUnsupported(tick,"native_preset_end_identity_mismatch");return;
    }
    const key=[end.tick,end.presetInfoId??"unknown",end.success,end.end].join(":");
    if (key===lastEndKey) return;
    lastEndKey=key;
    if (end.success) nativePresetSuccesses++;
    else nativePresetFailures++;
    note("native_preset_result",{tick,nativeEvent:end,nativePresetSuccess});
    if (end.end) {
      if (end.success) nativeTerminalSuccesses++;
      else nativeTerminalFailures++;
      completed=true;
      releaseControl(tick,"native_terminal_preset_result");suppression.restore("native_terminal_preset_result");
    }
  }
  function startPreset(tick,qte,reason) {
    releaseControl(tick,reason);
    groupId=qte.groupId;presetIndex=qte.currentIndex;
    presetSeenTick=tick;targetId=null;targetSeenTick=-1;
    if (validInt(qte.presetEntityId,1)) seenPresetIds.add(qte.presetEntityId);
    note("observed_preset",{tick,groupId,presetIndex,reason});
  }
  function readyActors(squad) {
    if (!squad || squad.supported!==true || !Array.isArray(squad.characters))
      return null;
    return squad.characters.filter(actor=>validInt(actor.id,1) && actor.health &&
      Number.isFinite(Number(actor.health.hp)) && Number(actor.health.hp)>0 &&
      actor.weapon &&
      // Generic circles never steal/restart original AI charge weapons.
      // Mirror's explicit charged first-hit coordinator is a separate policy.
      (["SMG","AR","MG","AS"].includes(actor.weapon.type?.name)||actor.weapon.nativeInputType===3||actor.weapon.nativeDownFireTiming===true) &&
      Number.isFinite(Number(actor.weapon.ammo)) &&
      Number(actor.weapon.ammo)>0).sort((a,b)=>
      weaponPriority[a.weapon.type.name]-weaponPriority[b.weapon.type.name] ||
      a.id-b.id);
  }
  function safeTargets(qte) {
    if (!Array.isArray(qte.targets) || qte.targets.length>64) return null;
    const out=[],ids=new Set();
    for (const target of qte.targets) {
      const kind=target?.colType?.name,state=target?.state?.name;
      if (!validInt(target?.id) || !validInt(target?.entityId,1) || !validInt(target?.order) ||
          !finite(target?.remainingNativeTime) ||
          !["Break","Counter","Choice"].includes(kind) ||
          !["Enable","StartDelay","WaitConnect","Disable"].includes(state))
        return null;
      if (ids.has(target.id)) return null;
      ids.add(target.id);
      const hp=Number(target.health?.hp);
      if (!Number.isFinite(hp)) return null;
      // Native OnQuickTimeColliderHit fails Counter, regardless of deadline.
      // Choice semantics are not established; never fire at either type.
      if (kind!=="Break" || state!=="Enable" ||
          hp<=0 || target.remainingNativeTime<=0 ||
          (target.order!==0 && target.order!==qte.currentOrder)) continue;
      if (!Array.isArray(target.worldPosition) ||
          target.worldPosition.length!==3 ||
          !target.worldPosition.every(finite)) return null;
      if (actions.projectWorld(target.worldPosition).visible) out.push(target);
    }
    out.sort((a,b)=>a.remainingNativeTime-b.remainingNativeTime || a.id-b.id);
    return out;
  }
  function acquire(tick,actors,suppressPreset,legacyGrayOrder) {
    const before=actions.snapshot();
    if (before.forcedCover) { unsupportedAt(tick,"existing_forced_cover");return false; }
    if (before.inputType===2) { unsupportedAt(tick,"preexisting_pressed_input");return false; }
    if (!actors.length) { unsupportedAt(tick,"no_ready_continuous_fire_actor");return false; }
    actorId=actors[0].id;priorAuto=before.autoAim;
    // Ownership begins before the first mutation, so a failed call can restore.
    owned=true;
    actions.setAutoAim(false);
    actions.focus(actorId);
    if(suppressPreset)actions.setActorStance(actorId,"Idle");
    else if (actions.snapshot().focusedStance===2) {actions.press();actions.release();}
    note("take_manual_control",{tick,actorId,weapon:actors[0].weapon.type,
      weaponPreference:legacyGrayOrder?"retained_ready_class_order_kraken_gray":actorEvidence?"original_observed_actual_shot_damage_ready_safe_actors":"legacy_class_fallback_without_evidence"});
    return true;
  }
  function step(tick,observation) {
    if (closed || fault!==null) return;
    try {
      if (!validInt(tick) || tick<=lastTick || !observation ||
          !validInt(observation.tick)||observation.tick>tick||tick-observation.tick>3)
        throw new Error("QTE policy needs an increasing tick and a recent original snapshot");
      lastTick=tick;
      const qte=observation.qte;
      if (suspended && actions.controlFlag("forcedCover")) suspendSawCover=true;
      if (suspended && suspendSawCover && !actions.controlFlag("forcedCover"))
        resume(tick);
      if (fault!==null) return;
      if (!qte || qte.supported!==true) {
        unsupportedAt(tick,"live_qte_state_unavailable");
        resetEpisode(tick,"live_qte_state_unavailable");return;
      }
      if (!qte.active) {
        // Native context can turn inactive in the same tick that it emits the
        // terminal preset result. Consume that original event before reset.
        if (episodeStart>=0) recordEnd(tick,observation.latestPresetEnd);
        resetEpisode(tick,"native_qte_inactive");return;
      }
      if (!validInt(qte.groupId,1) || !validInt(qte.currentIndex) ||
          !validInt(qte.currentOrder)) {
        unsupportedAt(tick,"invalid_live_group_or_order");
        resetEpisode(tick,"invalid_live_group_or_order");return;
      }
      const start=observation.latestQuickTimeStart;
      const presetStart=observation.latestPresetStart;
      const newStart=start && validInt(start.tick) &&
        start.tick<=tick && start.tick>startEventTick &&
        (episodeStart<0 || start.tick>episodeStart);
      if (episodeStart<0 || newStart) {
        if (episodeStart>=0) resetEpisode(tick,"new_original_qte_identity");
        episode++;episodeStart=tick;startEventTick=newStart?start.tick:-1;
        groups.add(qte.groupId);
        note("observed_qte",{tick,groupId:qte.groupId,
          quickTimeId:newStart?start.quickTimeId:null});
        startPreset(tick,qte,"new_preset");
        if (presetStart && presetStart.index===qte.groupId &&
            validInt(presetStart.tick) && presetStart.tick<=tick)
          presetStartEventTick=presetStart.tick;
      } else if (presetIndex!==qte.currentIndex||groupId!==qte.groupId) {
        groups.add(qte.groupId);
        startPreset(tick,qte,"original_preset_index_changed");
      } else if (presetStart && presetStart.index===qte.groupId &&
                 validInt(presetStart.tick) && presetStart.tick<=tick &&
                 presetStart.tick>presetStartEventTick &&
                 presetStart.tick>presetSeenTick) {
        startPreset(tick,qte,"original_preset_start_event");
      }
      // OnQuickTimePresetStart 0x070F3ED0 uses event.Index as the preset
      // dictionary/group key; context._currentIndex is a separate ordinal.
      if (presetStart && presetStart.index===qte.groupId &&
          validInt(presetStart.tick) && presetStart.tick<=tick &&
          presetStart.tick>presetStartEventTick)
        presetStartEventTick=presetStart.tick;
      recordEnd(tick,observation.latestPresetEnd,qte.nativePresetSuccess??null);
      if (completed) return;
      if (suspended) return;
      if (qte.targets?.some(target=>target?.colType?.name==="Choice"))
        markUnsupported(tick,"choice_target_semantics_unverified");
      const graySensitive=qte.nativePresetHasForbidden===true||qte.targets?.some(target=>["Counter","Choice"].includes(target?.colType?.name));
      const suppressPreset=configuration.offensiveSuppression===true&&(configuration.suppressionGrayOnly!==true||graySensitive);
      // Retain the proven ready-class order for Kraken gray circles.
      const legacyGrayOrder=configuration.preferReadyClassOrderInGray===true&&suppressPreset;
      let suppressionReady=true;
      if(suppressPreset) {
        let warm=readyActors(observation.squad)||[];
        warm=mechanicsPreferReadyDownOne(warm.filter(actor=>actor.weapon.nativeAttackType===0));
        const selected=owned&&warm.some(actor=>actor.id===actorId)?actorId:warm[0]?.id??null;
        suppressionReady=suppression.prepare(tick,selected,observation,owned?priorAuto:undefined);
      } else suppression.restore('no_gray_sensitive_native_preset');
      const candidates=safeTargets(qte);
      if (candidates===null) {
        unsupportedAt(tick,"unreadable_or_unknown_target_semantics");return;
      }
      if (!candidates.length) {
        // Preserve an already-running native DOWN_Charge only at a separated
        // ORIGINAL pending Break point. Input3 can autonomously fire between
        // samples: safety is native forbidden-collider geometry separation,
        // not the absence of a firing.step call or a guessed charge deadline.
        const current=actions.snapshot();
        const actor=readyActors(observation.squad)?.find(a=>a.id===actorId);
        const pending=configuration.pendingChainBridge===true&&owned&&targetId!==null&&
          suppressionReady&&actor?.weapon.nativeInputType===3&&actor.weapon.nativeAttackType===0&&
          current.inputType===2&&current.focusedEntityId===actorId&&current.autoAim===false&&
          !current.forcedCover&&current.focusedWeaponIdentity===activeWeaponIdentity&&
          current.focusedIsFullCharge===false?
          qte.nativeGeometryTick===tick?mechanicsQtePendingChainPoint(qte,actions.projectWorld,targetId):null:null;
        if(pending) {
          actions.aimWorld(actorId,pending.worldPosition,false,false);
          if(suppressPreset)suppression.prepare(tick,actorId,observation,priorAuto);
          note('preserve_native_charge_at_pending_break',{tick,actorId,targetId:pending.id,
            state:pending.state.name,worldPosition:pending.worldPosition,
            nativeGeometryTick:qte.nativeGeometryTick,forbiddenGeometry:qte.forbiddenGeometry,
            focusedWeaponIdentity:current.focusedWeaponIdentity,focusedIsFullCharge:current.focusedIsFullCharge,
            safety:'original_pending_point_outside_all_enabled_counter_choice_projected_bounds',
            autonomousInput3MayFire:true});
          return;
        }
        releaseControl(tick,"no_visible_eligible_qte_target");targetId=null;targetSeenTick=-1;
        return;
      }
      if (tick-presetSeenTick<reactionTicks) return;
      let actors=readyActors(observation.squad);
      if(actors&&(suppressPreset||qte.targets.some(target=>["Counter","Choice"].includes(target.colType?.name))))
        actors=actors.filter(actor=>actor.weapon.nativeAttackType===undefined?["SMG","AR","MG","AS","SR"].includes(actor.weapon.type.name):actor.weapon.nativeAttackType===0&&["SMG","AR","MG","AS","SR","RL"].includes(actor.weapon.type.name));
      if (actors===null) { unsupportedAt(tick,"live_squad_unavailable");return; }
      actors=mechanicsPreferReadyDownOne(actors);
      // All actors share the same observed battle interval. Rank ready safe
      // continuous weapons by ORIGINAL accumulated actual SHOT damage, read
      // only on ownership acquisition/handoff. No estimated damage formula,
      // class-name DPS assumption or expected values enter combat/stat state.
      const currentActor=owned?actors.find(value=>value.id===actorId):null;
      const needsEvidence=!owned||!currentActor||
        ['SR','RL'].includes(currentActor.weapon.type.name)&&currentActor.weapon.nativeInputType!==3&&currentActor.weapon.nativeDownFireTiming!==true&&actors.some(a=>['SMG','AR','MG','AS'].includes(a.weapon.type.name));
      if(actorEvidence&&!legacyGrayOrder&&needsEvidence&&actors.length) {
        const scores=actorEvidence.read(actors.map(a=>a.id),tick);evidenceReads++;
        actors=mechanicsRankQteActorsByObservedShotDamage(actors,scores);
        lastActorScores=actors.map(a=>({actorId:a.id,weapon:a.weapon.type.name,ammo:a.weapon.ammo,
          nativeActualShotDamage:String(typeof scores.get==='function'?scores.get(a.id):scores[a.id])}));
        note('native_ready_actor_evidence',{tick,reason:owned?'native_reload_or_charge_handoff':'native_qte_acquisition',
          actors:lastActorScores,commonObservationInterval:true,combatDamageCalculated:false});
      }
      // Reloading is normal native state. Release the trigger and wait/switch
      // through the original input path; it is not an unsupported mechanic.
      if (owned&&!actors.some(value=>value.id===actorId))
        releaseControl(tick,"controlled_actor_reloading_or_unavailable");
      // The original current weapon can change during Burst. Return charge
      // weapons to their own native BT when a ready continuous actor can aim.
      if(owned&&['SR','RL'].includes(actors.find(value=>value.id===actorId)?.weapon.type.name)&&
          actors.find(value=>value.id===actorId)?.weapon.nativeInputType!==3&&actors.find(value=>value.id===actorId)?.weapon.nativeDownFireTiming!==true&&
          actors[0].id!==actorId&&['SMG','AR','MG','AS'].includes(actors[0].weapon.type.name))
        releaseControl(tick,'native_charge_weapon_handoff');
      if (!actors.length) { releasePress();return; }
      if (!owned && !acquire(tick,actors,suppressPreset,legacyGrayOrder)) return;
      const current=actions.snapshot();
      if (current.forcedCover || current.focusedEntityId!==actorId ||
          current.autoAim!==false) {
        unsupportedAt(tick,"input_ownership_changed");return;
      }
      const actor=actors.find(value=>value.id===actorId);
      if (!actor) { unsupportedAt(tick,"controlled_actor_unavailable");return; }
      activeWeaponIdentity=current.focusedWeaponIdentity;
      const target=candidates.find(value=>value.id===targetId)||candidates[0];
      if (target.id!==targetId) {
        // A safe native Break-to-Break pointer jump needs no trigger edge.
        // Preserve original continuous-fire spool; initial acquisition, native
        // weapon replacement and charge release still use the firing policy.
        const keepHeld=targetId!==null && current.inputType===2 &&
          (["SMG","AR","MG","AS"].includes(actor.weapon.type.name)||actor.weapon.nativeInputType===3||actor.weapon.nativeDownFireTiming===true);
        if (!keepHeld) releasePress();
        targetId=target.id;targetSeenTick=keepHeld?tick-settleTicks:tick;selected++;
        note("aim_break",{tick,actorId,targetId,entityId:target.entityId,
          groupId,presetIndex,order:target.order,
          remainingNativeTime:target.remainingNativeTime,
          avoidedCounterAndChoiceIds:qte.targets.filter(value=>
            value.colType.name==="Counter"||value.colType.name==="Choice")
            .map(value=>value.id)});
      }
      // Reproject every native tick; the original adapter applies camera/rays.
      actions.aimWorld(actorId,target.worldPosition,false,false);
      const readyToFire=suppressionReady&&(!suppressPreset||suppression.prepare(tick,actorId,observation,priorAuto));
      if(suppressPreset&&!readyToFire){releasePress();firing.reset();}
      else firing.step(actor.weapon.type.name,readyToFire&&tick-targetSeenTick>=settleTicks);
      if(suppressPreset)suppression.prepare(tick,actorId,observation,priorAuto);
    } catch(error) {
      fault="step: "+(error&&error.stack?error.stack:String(error));
      try { releaseControl(tick,"policy_fault");suppression.restore("policy_fault"); }
      catch(cleanupError) { fault+="; cleanup: "+String(cleanupError); }
    }
  }
  function close(reason="caller_closed") {
    if (closed) return;
    try { releaseControl(lastTick,reason); }
    finally {try{suppression.restore(reason);}finally{closed=true;suspended=false;}}
  }
  function beforeNativeCleanup() {
    if (closed) return;
    try {
      if (owned) actions.restoreAutoAimBeforeNativeCleanup(priorAuto);
      owned=false;actorId=null;targetId=null;priorAuto=null;
    } finally {try{suppression.restore("original_finish",true);}finally{closed=true;suspended=false;}}
  }
  function checkFault() { if (fault!==null) throw new Error(fault); }
  function summary() {
    return {version,reactionTicks,settleTicks,lastTick,episode,groupId,presetIndex,evidenceReads,lastActorScores,offensiveSuppression:suppression.summary(),
      owned,suspended,suspendSawCover,actorId,targetId,completed,
      decisions,targetsSelected:selected,
      nativePresetSuccesses,nativePresetFailures,nativeTerminalSuccesses,
      nativeTerminalFailures,observedGroups:[...groups].sort((a,b)=>a-b),
      unsupported:[...unsupported],counterTargetingImplemented:false,
      choiceTargetingImplemented:false,elementGateClaimed:false,
      nativeOutcomeRequired:true,nativeValidatedBosses:[],fault,closed};
  }
  return {step,suspend,resume,close,beforeNativeCleanup,checkFault,summary};
}

// This is input selection from original observed statistics, never a predicted
// hit, native damage replacement, stat setter or result-score calculation.
function mechanicsRankActorsByObservedDamage(actors,scores,preferContinuous=true,acceptNativeDownCharge=true) {
  const score=actor=>{const value=typeof scores?.get==='function'?scores.get(actor.id):scores?.[actor.id];
    if(typeof value!=='string'||!/^\d+$/.test(value))throw Error('Original QTE shot damage statistic missing');
    return BigInt(value);};
  const continuous=actor=>!preferContinuous?0:(['SMG','AR','MG','AS'].includes(actor.weapon.type.name)||(acceptNativeDownCharge&&(actor.weapon.nativeInputType===3||actor.weapon.nativeDownFireTiming===true||actor.weapon.nativeIsAutoFireWeapon===true)))?0:1;
  return [...actors].sort((a,b)=>continuous(a)-continuous(b)||
    (score(a)>score(b)?-1:score(a)<score(b)?1:0)||
    (BigInt(a.weapon.ammo)>BigInt(b.weapon.ammo)?-1:BigInt(a.weapon.ammo)<BigInt(b.weapon.ammo)?1:0)||a.id-b.id);
}

function mechanicsRankQteActorsByObservedShotDamage(actors,scores){return mechanicsRankActorsByObservedDamage(actors,scores,true);}

function mechanicsReadyOriginalUpCarries(actors,targets) {
  if(!Array.isArray(actors)||!Array.isArray(targets)||targets.some(t=>['Break','Projectile','Mob'].includes(t.kind)))return [];
  return actors.filter(a=>a.nativeIsBurst3===true&&(a.weapon?.nativeInputType===2||a.weapon?.nativeInputType===3||a.weapon?.nativeDownFireTiming===true)&&
    typeof a.weapon.ammo==='string'&&/^\d+$/.test(a.weapon.ammo)&&BigInt(a.weapon.ammo)>0n);
}

// Original input isolation for the human-observed Mirror gray-circle sequence.
// Never removes projectiles or disables damage; waits for observed airborne
// teammate projectiles and original Idle confirmation before the first shot.
function createMechanicsQteSuppression(actions,emit,enabled,options={}) {
  if(enabled&&["autoSkill","setAutoSkill","setActorStance","restoreAutoAimBeforeNativeCleanup"].some(name=>typeof actions[name]!=="function"))throw Error("Original QTE suppression input adapter incomplete");
  let active=false,priorAuto=null,priorSkill=null,selected=null,entries=0,lastTick=-1,lastAmmo=new Map(),waits=0;
  const stances=new Map();
  const note=(action,data={})=>emit({status:'original_qte_offensive_suppression',action,...data});
  function restore(reason,nativeFinish=false) {
    if(!active)return;
    const errors=[];
    if(!nativeFinish)try{if(actions.controlFlag("inputType")===2){if(selected!==null)actions.setActorStance(selected,'Idle');actions.release();}}catch(e){errors.push(e);}
    for(const [id,stance] of stances)try{actions.setActorStance(id,stance);}catch(e){errors.push(e);}
    try{if(nativeFinish)actions.restoreAutoAimBeforeNativeCleanup(priorAuto);else if(actions.controlFlag("autoAim")!==priorAuto)actions.setAutoAim(priorAuto);}catch(e){errors.push(e);}
    try{actions.setAutoSkill(priorSkill);}catch(e){errors.push(e);}
    finally{active=false;selected=null;priorAuto=null;priorSkill=null;stances.clear();lastAmmo.clear();lastTick=-1;note('restored',{reason,cleanupErrors:errors.map(String)});}
    if(errors.length)throw errors[0];
  }
  function prepare(tick,actorId,observation,originalAutoAim) {
    if(!enabled)return true;
    const living=new Set((observation.squad?.characters||[]).filter(a=>/^\d+$/.test(a.health?.hp)&&BigInt(a.health.hp)>0n).map(a=>a.id));
    if(!active){
      const before=actions.snapshot();
      for(const row of before.squad||[])if(living.has(row.entityId)&&[0,2].includes(row.stance))stances.set(row.entityId,row.stance===0?'Idle':'Aim');
      priorAuto=typeof originalAutoAim==='boolean'?originalAutoAim:before.autoAim;priorSkill=actions.autoSkill();active=true;entries++;
      if(priorSkill)actions.setAutoSkill(false);
      if(before.autoAim!==false){if(before.inputType===2){actions.setActorStance(before.focusedEntityId,'Idle');actions.release();}actions.setAutoAim(false);}
      note('began',{tick,actorId,originalAutoAim:priorAuto,originalAutoSkill:priorSkill});
    }

    const before=actions.snapshot();let ready=actorId!==null;
    if(!Array.isArray(before.squad))throw Error("Original QTE suppression squad unavailable");
    if(before.forcedCover)return false;
    if(before.autoAim!==false){if(before.inputType===2){actions.setActorStance(before.focusedEntityId,'Idle');actions.release();}actions.setAutoAim(false);}
    if(actorId!==null&&before.focusedEntityId!==actorId){if(before.inputType===2){actions.setActorStance(before.focusedEntityId,"Idle");actions.release();}actions.focus(actorId);}
    for(const row of before.squad||[]) {
      if(!living.has(row.entityId)||row.entityId===actorId)continue;
      if(!stances.has(row.entityId)&&[0,2].includes(row.stance))stances.set(row.entityId,row.stance===0?'Idle':'Aim');
      if(tick!==lastTick&&lastAmmo.has(row.entityId)&&lastAmmo.get(row.entityId)!==row.usedAmmoCount){ready=false;note('native_teammate_ammo_changed',{tick,actorId:row.entityId,usedAmmoCount:row.usedAmmoCount});}
      const nativeIdle=actions.setActorStance(row.entityId,'Idle');
      if(nativeIdle?.stance!==0){ready=false;note('native_teammate_idle_unconfirmed',{tick,actorId:row.entityId,priorStance:row.stance,nativeStance:nativeIdle?.stance});}
    }

    const proof=typeof options.readFriendlyProjectiles==='function'?options.readFriendlyProjectiles(tick,observation):null;
    const projectiles=typeof options.readFriendlyProjectiles==='function'?(proof?.supported===true?proof.projectiles:null):observation.friendlyProjectiles;
    const owners=options.retainDeadOwnerProjectiles===true?new Set((observation.squad?.characters||[]).map(a=>a.id)):living;
    const pending=Array.isArray(projectiles)?projectiles.filter(p=>p.ownerId!==actorId&&owners.has(p.ownerId)):null;
    if(pending===null||pending.length)ready=false;
    if(tick!==lastTick){lastAmmo=new Map((before.squad||[]).map(row=>[row.entityId,row.usedAmmoCount]));lastTick=tick;}
    if(selected!==actorId){selected=actorId;note('selected',{tick,actorId});}
    if(!ready)waits++;
    return ready;
  }
  return {prepare,restore,active:()=>active,summary:()=>({enabled,active,selected,entries,waits,originalProjectilesNeverRemoved:true,readsProjectilesAfterOriginalStanceInput:typeof options.readFriendlyProjectiles==='function',retainsDeadOwnerProjectiles:options.retainDeadOwnerProjectiles===true})};
}

function mechanicsPreferReadyDownOne(actors) {
  const direct=actors.filter(a=>['SMG','AR','MG','AS'].includes(a.weapon.type.name)&&a.weapon.nativeInputType!==3);
  return direct.length?direct:actors;
}

// Conservative input-safety test; projected AABB separation is not a claimed
// native hit. Every currently enabled forbidden collider must have complete
// original positive bounds entirely in front of the original camera.
function mechanicsQtePendingChainPoint(qte,projectWorld,previousTargetId) {
  const vector=v=>Array.isArray(v)&&v.length===3&&v.every(Number.isFinite);
  if(qte.pendingGeometrySupported!==true||!Array.isArray(qte.pendingTargets)||
      !Array.isArray(qte.forbiddenGeometry))return null;
  const rectangles=[];
  const unsafeIds=new Set(qte.forbiddenGeometry.map(t=>t.id));
  if(!Array.isArray(qte.targets)||qte.targets.some(t=>['Counter','Choice'].includes(t.colType?.name)&&!unsafeIds.has(t.id)))return null;
  for(const unsafe of qte.forbiddenGeometry) {
    const b=unsafe.geometry;
    if(b?.supported!==true||!['Counter','Choice'].includes(unsafe.colType?.name)||!vector(b?.center)||
        !vector(b?.extents)||!b.extents.every(n=>n>0))return null;
    const corners=[];
    for(const x of [-1,1])for(const y of [-1,1])for(const z of [-1,1]) {
      const p=projectWorld(b.center.map((n,i)=>n+b.extents[i]*[x,y,z][i]));
      if(!vector(p?.screen)||p.screen[2]<=0)return null;
      corners.push(p.screen);
    }
    rectangles.push([Math.min(...corners.map(p=>p[0])),Math.max(...corners.map(p=>p[0])),
      Math.min(...corners.map(p=>p[1])),Math.max(...corners.map(p=>p[1]))]);
  }
  for(const target of qte.pendingTargets) {
    if(target.id===previousTargetId||target.colType?.name!=='Break'||!['StartDelay','WaitConnect'].includes(target.state?.name)||
        !Number.isSafeInteger(target.id)||!Number.isSafeInteger(target.entityId)||
        !Number.isSafeInteger(target.order)||(target.order!==0&&target.order!==qte.currentOrder)||
        !(Number(target.health?.hp)>0)||!vector(target.worldPosition))continue;
    const p=projectWorld(target.worldPosition);
    if(!p?.visible||!vector(p.screen))continue;
    if(rectangles.some(r=>p.screen[0]>=r[0]&&p.screen[0]<=r[1]&&p.screen[1]>=r[2]&&p.screen[1]<=r[3]))continue;
    return target;
  }
  return null;
}
