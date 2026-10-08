// Private native observations, bounded input proof, and explicitly selected
// Kraken policies. Original-auto stays separate. The fixed probe sequence is
// evidence for input routes, not the adaptive boss controller.
function createMechanicsTacticalController(mode, management, observer, actions, actors, emit, threats=null) {
  const generic=mode==="boss-tactical"||mode==="boss-observe";
  if (!["observe","probe","kraken-qte","kraken-cover-probe","kraken-tactical","boss-tactical","boss-observe"].includes(mode) || !observer || (!["observe","boss-observe"].includes(mode) && !actions))
    throw new Error("Invalid private tactical controller dependencies");
  let samples=0, transitions=0, lastNativeTick=-1, lastSignature=null;
  let latest=null, selectedId=null, originalFocus=null, originalAuto=null, commands=0;
  let completed=false;
  let trackedPart=null;
  const checkpoints=[];
  const policy=mode==="boss-tactical"?createMechanicsQtePolicy(actions,emit):
    ["kraken-qte","kraken-tactical"].includes(mode) ? createMechanicsKrakenQtePolicy(actions,emit) : null;
  const coverProbe=["kraken-cover-probe","kraken-tactical"].includes(mode) ? createMechanicsKrakenCoverProbe(actions,emit) : null;
  const coverPolicy=mode==="boss-tactical"?createMechanicsCoverPolicy(actions,emit,
    mechanicsVerifiedCoverRules(),globalThis.MECHANICS_REQUEST.encounter.waveId):null;
  let latestThreat=null;
  const compact = state => ({
    qte:state.qte && {supported:state.qte.supported,reason:state.qte.reason,
      active:state.qte.active,groupId:state.qte.groupId,currentOrder:state.qte.currentOrder,
      ...(generic?{currentIndex:state.qte.currentIndex,presetEntityId:state.qte.presetEntityId}:{}),
      nativePresetSuccess:state.qte.nativePresetSuccess,
      targets:(state.qte.targets||[]).map(t=>[t.id,t.state,t.colType,t.order])},
    monster:state.monster && {supported:state.monster.supported,reason:state.monster.reason,
      id:state.monster.targetMonsterId,parts:(state.monster.parts||[]).map(p=>p.partsType)},
    squad:state.squad && {supported:state.squad.supported,reason:state.squad.reason}
  });
  function checkpoint(label,tick) {
    const state=actions.snapshot();
    const row={label,tick,nativeTick:Number(management.field("_tickCount").value),state};
    checkpoints.push(row);
    emit({status:"original_tactical_input_checkpoint",...row});
    return state;
  }
  function command(label,tick,fn) {
    fn(); commands++;
    return checkpoint(label,tick);
  }
  function beforeTick(tick) {
    observer.checkFault();
    if (threats) threats.checkFault();
    if (generic) {
      if (!policy||!latest) return;
      const intent=coverPolicy.inspect(tick,latest,latestThreat);
      const hadQteOwnership=policy.summary().owned;
      if (intent.wantsCover) policy.suspend(tick,"source_scoped_dangerous_attack");
      coverPolicy.step(tick,latest,latestThreat,{qteSuspended:hadQteOwnership});
      if (!coverPolicy.summary().covered&&!intent.wantsCover) policy.resume(tick);
      policy.step(tick,latest);
      policy.checkFault();
      return;
    }
    if (coverProbe) {
      const before=coverProbe.summary();
      if (policy && policy.summary().owned && latestThreat &&
          latestThreat.latestAttack && latestThreat.latestAttack.attackNodeId===230 && !before.completed)
        throw new Error("Unvalidated simultaneous Kraken QTE and cover input ownership");
      coverProbe.step(tick,latest,latestThreat);
      if (coverProbe.summary().covered || !policy) return;
    }
    if (policy) { policy.step(tick,latest); return; }
    if (mode!=="probe") return;
    if ((tick>93 && tick<108) || (tick>=140 && tick<156)) {
      const target=latest && latest.monster && (latest.monster.parts||[])
        .find(p=>p.partsType===trackedPart);
      if (!target) throw new Error("Input proof lost the original tracked part");
      actions.aimWorld(selectedId,target.worldPosition,false);
    }
    if (tick===90) {
      const initial=checkpoint("before_ownership",tick);
      originalFocus=initial.focusedEntityId; originalAuto=initial.autoAim;
      if (initial.forcedCover) throw new Error("Input proof requires initial forced cover off");
      if (initial.inputType===2) command("release_initial_input",tick,()=>actions.release());
      command("manual_ownership",tick,()=>actions.setAutoAim(false));
      const other=actors.find(a=>a.entityId!==originalFocus);
      if (!other) throw new Error("Input proof requires another live original actor");
      selectedId=other.entityId;
      command("selected_other_actor",tick,()=>actions.focus(selectedId));
    } else if (tick===93) {
      const target=latest && latest.monster && latest.monster.supported &&
        latest.monster.parts.find(p=>Array.isArray(p.worldPosition));
      if (!target) throw new Error("Input proof has no live native monster part aim point");
      trackedPart=target.partsType;
      command("aimed_live_part",tick,()=>actions.aimWorld(selectedId,target.worldPosition));
      command("pressed",tick,()=>actions.press());
    } else if (tick===108) {
      checkpoint("held_input_before_release",tick);
      command("released",tick,()=>actions.release());
    } else if (tick===120) {
      checkpoint("released_after_wait",tick);
    } else if (tick===123) {
      command("forced_cover_on",tick,()=>actions.setCover(true));
    } else if (tick===138) {
      checkpoint("covered_after_wait",tick);
      command("forced_cover_off",tick,()=>actions.setCover(false));
    } else if (tick===141) {
      command("repressed",tick,()=>actions.press());
    } else if (tick===156) {
      command("released_again",tick,()=>actions.release());
    } else if (tick===159) {
      command("restored_focus",tick,()=>actions.focus(originalFocus));
      const restored=command("restored_auto",tick,()=>actions.setAutoAim(originalAuto));
      if (restored.forcedCover || restored.autoAim!==originalAuto || restored.inputType===2)
        throw new Error("Input proof did not restore original auto ownership");
      completed=true;
      emit({status:"original_tactical_input_sequence_completed",tick,commands,
        mechanicalEffectVerificationPending:true});
    }
  }
  function afterTick(tick) {
    observer.checkFault();
    const nativeTick=Number(management.field("_tickCount").value);
    if (nativeTick===lastNativeTick || (tick>1 && tick%3!==0)) return;
    lastNativeTick=nativeTick;
    latest=observer.snapshot(nativeTick); samples++;
    if (threats) {
      latestThreat=threats.snapshot(nativeTick);
      threats.checkFault();
    }
    observer.checkFault();
    const signature=JSON.stringify(compact(latest));
    if (signature!==lastSignature) {
      lastSignature=signature; transitions++;
      if (transitions<=96) emit({...latest,status:"original_tactical_observation_change",
        driverTick:tick,ordinal:transitions});
    }
  }
  function summary() {
    return {mode,policyVersion:generic?"boss-tactical-v1":mode==="kraken-tactical" ? "kraken-tactical-v2" :
        coverProbe ? "kraken-cover-probe-v1" : policy ? "kraken-qte-v2" :
        mode==="probe" ? "native-input-proof-v1" : "original-auto-v1",samples,transitions,commands,
      inputSequenceCompleted:completed,checkpoints,
      observationTransitionsTruncated:transitions>96,
      adaptiveBossPolicyImplemented:policy!==null,
      policy:policy ? policy.summary() : null,
      ...(generic?{coverPolicy:coverPolicy?coverPolicy.summary():null}:{}),
      coverProbe:coverProbe ? coverProbe.summary() : null};
  }
  return {beforeTick,afterTick,summary};
}
