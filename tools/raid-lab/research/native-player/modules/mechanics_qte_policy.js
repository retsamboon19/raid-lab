// Source-bound, reactive QTE input policy for installed NK.Spot. No predicted
// sequence, native writes, collider calls, or future RNG. Its inputs are the
// existing original tactical observer and original input adapter snapshots.
// Source: QuickTimeEventContext.OnQuickTimeColliderHit 0x064A56E0 fails a
// Counter hit or wrong nonzero order; SpotQuickTimePreset.IsSuccess 0x06375ED0
// checks disabled Break colliders (predicates 0x06379F30/0x06379F50).
// SpotQuickTimeCollider.UpdateLimitTime 0x06375460 spends native simulation
// delta. Element matching in DamageLogic.ExistWeakElement 0x063F2440 is a weak
// damage bonus, not proof of a mandatory element gate.
function createMechanicsQtePolicy(actions,emit) {
  if (!actions || typeof actions.snapshot!=="function" ||
      typeof actions.release!=="function" || typeof actions.setAutoAim!=="function" ||
      typeof actions.focus!=="function" || typeof actions.aimWorld!=="function" ||
      typeof actions.press!=="function" || typeof emit!=="function")
    throw new Error("Original QTE policy requires the original input adapter and emit");
  const version="reactive-qte-v1",reactionTicks=3,settleTicks=3;
  const weaponPriority={SMG:0,AR:1,MG:2};
  const unsupported=new Set(),groups=new Set();
  let lastTick=-1,episode=0,episodeStart=-1,startEventTick=-1;
  let groupId=null,presetIndex=null,presetSeenTick=-1,
    presetStartEventTick=-1,completed=false;
  const seenPresetIds=new Set();
  let owned=false,actorId=null,targetId=null,targetSeenTick=-1,priorAuto=null;
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
    if (owned && actions.snapshot().inputType===2) actions.release();
  };
  function releaseControl(tick,reason) {
    if (!owned) return;
    releasePress();
    // Only restore an auto setting still in the state installed by this policy.
    if (actions.snapshot().autoAim===false) actions.setAutoAim(priorAuto);
    note("release_manual_control",{tick,reason,actorId});
    owned=false;actorId=null;targetId=null;targetSeenTick=-1;priorAuto=null;
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
        releaseControl(tick,reason);
        suspended=true;suspendSawCover=Boolean(actions.snapshot().forcedCover);
        note("suspend_for_cover",{tick,reason});
      }
    } catch(error) { fault="suspend: "+String(error); }
  }
  function resume(tick) {
    if (closed || fault!==null || !suspended) return false;
    try {
      if (!validInt(tick)) throw new Error("QTE resume requires an original tick");
      if (actions.snapshot().forcedCover) return false;
      suspended=false;suspendSawCover=false;
      presetSeenTick=tick;targetId=null;targetSeenTick=-1;
      note("resume_after_cover",{tick});
      return true;
    } catch(error) { fault="resume: "+String(error);return false; }
  }
  function resetEpisode(tick,reason) {
    releaseControl(tick,reason);
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
      releaseControl(tick,"native_terminal_preset_result");
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
      Object.hasOwn(weaponPriority,actor.weapon.type?.name) &&
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
      out.push(target);
    }
    out.sort((a,b)=>a.remainingNativeTime-b.remainingNativeTime || a.id-b.id);
    return out;
  }
  function acquire(tick,actors) {
    const before=actions.snapshot();
    if (before.forcedCover) { unsupportedAt(tick,"existing_forced_cover");return false; }
    if (before.inputType===2) { unsupportedAt(tick,"preexisting_pressed_input");return false; }
    if (!actors.length) { unsupportedAt(tick,"no_ready_continuous_fire_actor");return false; }
    actorId=actors[0].id;priorAuto=before.autoAim;
    // Ownership begins before the first mutation, so a failed call can restore.
    owned=true;
    actions.setAutoAim(false);
    actions.focus(actorId);
    if (actions.snapshot().focusedStance===2) {
      actions.press();actions.release();
    }
    note("take_manual_control",{tick,actorId,weapon:actors[0].weapon.type,
      weaponPreference:"SMG_AR_MG_observed_short_chain_not_universal_DPS"});
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
      if (suspended && actions.snapshot().forcedCover) suspendSawCover=true;
      if (suspended && suspendSawCover && !actions.snapshot().forcedCover)
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
      // OnQuickTimePresetStart 0x064A5E20 uses event.Index as the preset
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
      const candidates=safeTargets(qte);
      if (candidates===null) {
        unsupportedAt(tick,"unreadable_or_unknown_target_semantics");return;
      }
      if (!candidates.length) {
        releasePress();targetId=null;targetSeenTick=-1;
        return;
      }
      if (tick-presetSeenTick<reactionTicks) return;
      const actors=readyActors(observation.squad);
      if (actors===null) { unsupportedAt(tick,"live_squad_unavailable");return; }
      // Reloading is normal native state. Release the trigger and wait/switch
      // through the original input path; it is not an unsupported mechanic.
      if (owned&&!actors.some(value=>value.id===actorId))
        releaseControl(tick,"controlled_actor_reloading_or_unavailable");
      if (!actors.length) { releasePress();return; }
      if (!owned && !acquire(tick,actors)) return;
      const current=actions.snapshot();
      if (current.forcedCover || current.focusedEntityId!==actorId ||
          current.autoAim!==false) {
        unsupportedAt(tick,"input_ownership_changed");return;
      }
      const actor=actors.find(value=>value.id===actorId);
      if (!actor) { unsupportedAt(tick,"controlled_actor_unavailable");return; }
      const target=candidates.find(value=>value.id===targetId)||candidates[0];
      if (target.id!==targetId) {
        releasePress();targetId=target.id;targetSeenTick=tick;selected++;
        note("aim_break",{tick,actorId,targetId,entityId:target.entityId,
          groupId,presetIndex,order:target.order,
          remainingNativeTime:target.remainingNativeTime,
          avoidedCounterAndChoiceIds:qte.targets.filter(value=>
            value.colType.name==="Counter"||value.colType.name==="Choice")
            .map(value=>value.id)});
      }
      // Reproject every native tick; the original adapter applies camera/rays.
      actions.aimWorld(actorId,target.worldPosition,false);
      if (tick-targetSeenTick>=settleTicks && actions.snapshot().inputType!==2)
        actions.press();
    } catch(error) {
      fault="step: "+(error&&error.stack?error.stack:String(error));
      try { releaseControl(tick,"policy_fault"); }
      catch(cleanupError) { fault+="; cleanup: "+String(cleanupError); }
    }
  }
  function close(reason="caller_closed") {
    if (closed) return;
    try { releaseControl(lastTick,reason); }
    finally { closed=true;suspended=false; }
  }
  function checkFault() { if (fault!==null) throw new Error(fault); }
  function summary() {
    return {version,reactionTicks,settleTicks,lastTick,episode,groupId,presetIndex,
      owned,suspended,suspendSawCover,actorId,targetId,completed,
      decisions,targetsSelected:selected,
      nativePresetSuccesses,nativePresetFailures,nativeTerminalSuccesses,
      nativeTerminalFailures,observedGroups:[...groups].sort((a,b)=>a-b),
      unsupported:[...unsupported],counterTargetingImplemented:false,
      choiceTargetingImplemented:false,weakElementBonusNotHardGate:true,
      nativeOutcomeRequired:true,nativeValidatedBosses:[],fault,closed};
  }
  return {step,suspend,resume,close,checkFault,summary};
}
