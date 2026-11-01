// Kraken-only integration of unchanged reactive QTE/cover algorithms.
// Call afterTick after each original management.UpdateTick; beforeTick before it.
function createKraken153TacticalController(management,observer,actions,threats,emit) {
  if(!observer||!actions||!threats||typeof emit!=='function')throw Error('Original tactical dependencies required');
  const client=kraken153Binding().clientSha256;
  const qte=createMechanicsQtePolicy(actions,emit);
  const cover=createMechanicsCoverPolicy(actions,emit,mechanicsVerifiedCoverRules(),6302009);
  let latest=null,latestThreat=null,lastNativeTick=-1,lastSignature=null,samples=0,transitions=0,fault=null,closed=false;
  const maxTransitions=256;
  const compact=state=>({
    qte:state.qte&&{supported:state.qte.supported,reason:state.qte.reason,active:state.qte.active,
      groupId:state.qte.groupId,currentOrder:state.qte.currentOrder,currentIndex:state.qte.currentIndex,
      presetEntityId:state.qte.presetEntityId,nativePresetSuccess:state.qte.nativePresetSuccess,
      targets:(state.qte.targets||[]).map(t=>[t.id,t.state,t.colType,t.order])},
    monster:state.monster&&{supported:state.monster.supported,reason:state.monster.reason,
      id:state.monster.targetMonsterId,parts:(state.monster.parts||[]).map(p=>p.partsType)},
    squad:state.squad&&{supported:state.squad.supported,reason:state.squad.reason}
  });
  const check=()=>{observer.checkFault();threats.checkFault();qte.checkFault();actions.pointer.check();if(fault)throw fault;};
  const beforeTick=tick=>{
    if(closed)return;
    check();
    if(!latest)return;
    try{
      const intent=cover.inspect(tick,latest,latestThreat);
      const owned=qte.summary().owned;
      if(intent.wantsCover)qte.suspend(tick,'source_scoped_dangerous_attack');
      cover.step(tick,latest,latestThreat,{qteSuspended:owned});
      if(!cover.summary().covered&&!intent.wantsCover)qte.resume(tick);
      qte.step(tick,latest);check();
    }catch(error){fault=fault||error;throw fault;}
  };
  const afterTick=tick=>{
    if(closed)return;
    check();
    const nativeTick=Number(management.field('_tickCount').value);
    if(nativeTick===lastNativeTick||(tick>1&&tick%3!==0))return;
    lastNativeTick=nativeTick;
    latest=observer.snapshot(nativeTick);latestThreat=threats.snapshot(nativeTick);samples++;
    // Keep the historical decision-bound snapshots, including target health,
    // so the strict verifier can correlate selected Breaks and unsafe targets.
    const signature=JSON.stringify(compact(latest));
    if(signature!==lastSignature){
      lastSignature=signature;transitions++;
      if(transitions<=maxTransitions)emit({...latest,status:'original_tactical_observation_change',driverTick:tick,ordinal:transitions});
    }
    check();
  };
  const summary=()=>({mode:'boss-tactical',policyVersion:'boss-tactical-v1',clientSha256:client,
    authoredSourceSha256:globalThis.KRAKEN153_AUTHORED_RULE_SHA256,samples,transitions,
    observationTransitionsTruncated:transitions>maxTransitions,fault:fault?String(fault):null,
    policy:qte.summary(),coverPolicy:cover.summary(),closed});
  const close=reason=>{
    if(closed)return;
    try{qte.close(reason||'caller_closed');if(cover.summary().covered&&actions.snapshot().forcedCover)actions.setCover(false);}
    finally{actions.pointer.clear();closed=true;}
  };
  emit({status:'native_control_mode_selected',controlMode:'boss-tactical',policyVersion:'boss-tactical-v1',
    clientSha256:client,authoredSourceSha256:globalThis.KRAKEN153_AUTHORED_RULE_SHA256,
    observesNativeState:true,issuesTacticalCommands:true,current153NativeValidated:false});
  return{beforeTick,afterTick,check,close,summary};
}
