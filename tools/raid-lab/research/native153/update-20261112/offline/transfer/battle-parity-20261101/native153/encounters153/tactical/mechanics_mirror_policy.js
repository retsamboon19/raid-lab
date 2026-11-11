// Mirror first-hit coordination uses original player input events only. Caller
// supplies exposed original positive-HP slipper targets from the same native
// observation, plus native living actor/weapon observations. No charge timer.
function createMechanicsMirrorPolicy(actions,emit,configuration={}) {
  const enabled=configuration.waveId===6302006&&configuration.monsterId===4510010123;
  const strategy=configuration.strategy||{mode:'coordinated_slippers',reason:'no_native_kit_strategy_supplied'};
  const coordinationEnabled=enabled&&strategy.mode!=='core_pressure';
  const phase2Names=['Weapon_07','Weapon_08','Weapon_09','Weapon_10'];
  const phase2PartTypes=enabled?phase2Names.map(name=>{
    const type=Il2Cpp.domain.assembly('NK.Runtime.StaticData').image.class('NK.StaticData.PartsType');
    const value=type.field(name).value,n=typeof value==='number'?value:Number(value.field('value__').value);
    if(!Number.isSafeInteger(n))throw Error('Original Mirror phase2 part enum missing: '+name);return n;
  }):[];
  if(new Set(phase2PartTypes).size!==phase2PartTypes.length)throw Error('Original Mirror phase2 part enum aliases');
  let nativePhase=null,targetOwnerId=null,targetPartsType=null,shotConfirmed=false;
  const stateAudit=enabled?createMechanicsMirrorStateAudit(emit,phase2PartTypes):null;
  function observeNativeState(input) {
    if(!enabled)return;
    const old=new Map(phase2PartTypes.map(type=>[type,stateAudit.exposure(input.ownerId,type)?.epoch]));
    stateAudit.observeNativeState(input);
    for(const type of phase2PartTypes) {
      const current=stateAudit.exposure(input.ownerId,type);
      if(current&&current.epoch!==old.get(type))attempted.delete('part:'+input.ownerId+':'+type);
    }
  }
  let owned=false,actorId=null,key=null,priorAuto=null,priorSkill=null,priorStances=new Map();
  let fallbackWorld=null,baseline=null,phase='idle',releases=0,confirmed=0,suppressionViolations=0;
  let ownershipTick=null,releasedTick=null,watchdogAborts=0;
  const attempted=new Set(),exposed=new Set();
  const log=(action,detail={})=>emit({status:'native_mirror_one_shot',action,actorId,targetKey:key,...detail});
  const nativeCount=v=>Number.isSafeInteger(v)&&v>=0;
  const positive=v=>typeof v==='string'&&/^\d+$/.test(v)&&BigInt(v)>0n;
  const visible=t=>Array.isArray(t.world)&&t.world.length===3&&t.world.every(Number.isFinite)&&actions.projectWorld(t.world).visible;
  const record=(state)=>({shot:state.focusedShotHitNum,used:state.focusedUsedAmmoCount,
    squad:new Map((state.squad||[]).map(x=>[x.entityId,x.usedAmmoCount]))});
  // A prior in-flight projectile may increment ShotHitNum while charging;
  // only original ammo consumption AFTER our PointUp proves this new shot.
  const hasFired=state=>baseline&&nativeCount(state.focusedUsedAmmoCount)&&state.focusedUsedAmmoCount>baseline.used;
  function restore(reason,beforeNativeCleanup=false) {
    if(!owned)return;
    const selected=actorId,target=key;
    const failures=[];
    try {
      if(!beforeNativeCleanup&&actions.controlFlag("inputType")===2) {
        const state=actions.snapshot();
        if(fallbackWorld&&!state.forcedCover&&state.focusedEntityId===actorId&&actions.projectWorld(fallbackWorld).visible)
          actions.aimWorld(actorId,fallbackWorld,false,false);
        actions.release();
      }
    } catch(error){failures.push(String(error));}
    for(const [id,stance] of priorStances)if(['Idle','Aim'].includes(stance)) {
      try {actions.setActorStance(id,stance);}catch(error){failures.push(String(error));}
    }
    try {
      if(beforeNativeCleanup)actions.restoreAutoAimBeforeNativeCleanup(priorAuto);
      else actions.setAutoAim(priorAuto);
    } catch(error){failures.push(String(error));}
    finally {
      try {actions.setAutoSkill(priorSkill);}catch(error){failures.push(String(error));}
      finally {
        owned=false;actorId=null;key=null;baseline=null;phase='idle';priorStances=new Map();ownershipTick=null;releasedTick=null;
      }
    }
    log('restored',{reason,selectedActorId:selected,selectedTargetKey:target,beforeNativeCleanup,cleanupErrors:failures});
    if(failures.length)throw Error('Mirror original input cleanup failed: '+failures.join('; '));
  }
  function wantsOwnership(input) {
    if(!coordinationEnabled)return false;
    if(!enabled||input?.phase!==2||input?.monsterId!==4510010123)return owned;
    if(owned)return true;
    const eligible=(target,prepare)=>{
      const state=stateAudit.exposure(input.ownerId,target.partsType);
      if(!state?.baselineProved||state.firstHitConsumed||attempted.has(target.key))return false;
      return prepare?mechanicsMirrorPreparePartAllowed(input.timelineRows,target,input.phase,phase2PartTypes,state.baselineHurtCount):
        mechanicsMirrorExposurePartAllowed(input.timelineRows,target,input.phase,phase2PartTypes,state.baselineHurtCount);
    };
    return (input.targets||[]).some(t=>eligible(t,false))||(input.prepareTargets||[]).some(t=>eligible(t,true));
  }
  function step(input) {
    if(!coordinationEnabled){nativePhase=input?.phase??nativePhase;return {handled:false,strategy:strategy.mode};}
    const {tick,targets=[],actors=[]}=input||{};
    if(!Number.isSafeInteger(tick))throw Error('Mirror requires original tick');
    // The caller's exact boss gate is repeated here before ownership changes.
    if(owned&&((Number.isSafeInteger(releasedTick)&&tick-releasedTick>60)||
        (Number.isSafeInteger(ownershipTick)&&tick-ownershipTick>600))) {
      watchdogAborts++;attempted.add(key);
      log('original_input_watchdog_abort',{tick,ownershipTick,releasedTick,chargeTimingChanged:false});
      restore('native_input_no_progress_watchdog');return {handled:true,watchdogAborted:true};
    }
    if(input.monsterId!==4510010123){restore('different_native_boss');return {handled:false};}
    if(nativePhase!==input.phase){nativePhase=input.phase;log('native_phase_gate',{tick,nativePhase,phase2PartTypes,damageObjective:'skip_unnecessary_phase1_slippers'});}
    // Source MonsterParts45101102-07 are first-phase objects;45101108-11
    // are the four second-phase shield slippers. P1 destruction is optional
    // and costs boss damage, so one-shot coordination owns only native P2.
    if(input.phase!==2){restore('native_phase_not_two');return {handled:false};}
    observeNativeState({...input,partStates:Array.isArray(input.partStates)?input.partStates:targets});
    const ownedExposure=owned?stateAudit.exposure(targetOwnerId,targetPartsType):null;
    if(ownedExposure&&(ownedExposure.firstHitConsumed||ownedExposure.current.nativeIsDestroyed===true)) {
      if(!shotConfirmed&&['released','await_hit'].includes(phase)&&hasFired(actions.snapshot())){confirmed++;shotConfirmed=true;log('native_shot_confirmed',{tick,awaitingNativePartHit:false});}
      log('native_exposure_completed',{tick,nativePhase,partsType:targetPartsType,epoch:ownedExposure.epoch,
        baselineHurtCount:ownedExposure.baselineHurtCount,hurtCount:ownedExposure.current.hurtCount,
        hp:ownedExposure.current.hp,nativeIsDestroyed:ownedExposure.current.nativeIsDestroyed,
        selectedShotConfirmed:shotConfirmed,shieldRemovalProved:false});
      restore(ownedExposure.firstHitConsumed?'original_first_hit_observed':'original_part_destroyed');
      return {handled:true,firstHitConsumed:ownedExposure.firstHitConsumed};
    }
    const matching=targets.filter(t=>t.ownerId===input.ownerId&&t.kind==='Part'&&phase2PartTypes.includes(t.partsType));
    const preparation=(input.prepareTargets||targets).filter(t=>t.ownerId===input.ownerId&&t.kind==='Part'&&phase2PartTypes.includes(t.partsType));
    const valid=matching.filter(t=>{
      const exposure=stateAudit.exposure(input.ownerId,t.partsType);
      return exposure?.baselineProved===true&&!exposure.firstHitConsumed&&
        (!exposure.attempted||owned&&t.key===key)&&
        mechanicsMirrorExposurePartAllowed(input.timelineRows,t,input.phase,phase2PartTypes,exposure.baselineHurtCount)&&visible(t);
    });
    const prepared=preparation.filter(t=>{
      const exposure=stateAudit.exposure(input.ownerId,t.partsType);
      return exposure?.baselineProved===true&&!exposure.firstHitConsumed&&(!exposure.attempted||owned&&t.key===key)&&
        mechanicsMirrorPreparePartAllowed(input.timelineRows,t,input.phase,phase2PartTypes,exposure.baselineHurtCount);
    });
    // A released native projectile may still be in flight. Retain suppression
    // until native first-hit/part-state evidence, not merely an ammo counter.
    if(owned&&['released','await_hit'].includes(phase)) {
      const state=actions.snapshot();
      for(const actor of actors)if(actor.id!==actorId)actions.setActorStance(actor.id,'Idle');
      if(!shotConfirmed&&hasFired(state)) {
        confirmed++;shotConfirmed=true;phase='await_hit';log('native_shot_confirmed',{tick,
          usedAmmoCount:state.focusedUsedAmmoCount,shotHitNum:state.focusedShotHitNum,awaitingNativePartHit:true});
      }
      return {handled:true,phase};
    }
    const active=new Set(prepared.map(t=>t.key));
    for(const old of exposed)if(!active.has(old))exposed.delete(old);
    for(const now of active)exposed.add(now);
    const desired=prepared.find(t=>owned&&t.key===key)||prepared.find(t=>!attempted.has(t.key));
    if(!desired){restore('no_unattempted_exposed_slipper');return {handled:false,waitingForExposure:valid.length>0};}
    if(owned&&key!==desired.key)restore('native_slipper_changed');
    const candidates=actors.filter(a=>positive(a.health?.hp)&&positive(a.weapon?.ammo)&&a.weapon.type?.name==='SR')
      .sort((a,b)=>(a.weapon.type.name==='SR'?0:1)-(b.weapon.type.name==='SR'?0:1)||a.id-b.id);
    if(!owned) {
      const initial=actions.snapshot();
      if(initial.forcedCover||initial.inputType===2)return {handled:false,reason:'external_native_input'};
      if(!candidates.length){log('no_native_charged_actor',{tick});return {handled:true,unsupported:'no_living_native_SR'};}
      priorAuto=initial.autoAim;priorSkill=actions.autoSkill();
      priorStances=new Map((initial.squad||[]).map(x=>[x.entityId,x.stance===0?'Idle':x.stance===2?'Aim':null]));
      if(!Array.isArray(input.fallbackWorld)||input.fallbackWorld.length!==3||!input.fallbackWorld.every(Number.isFinite)||!actions.projectWorld(input.fallbackWorld).visible)
        return {handled:false,unsupported:'native_safe_body_aim_required_for_abort'};
      fallbackWorld=input.fallbackWorld.slice();actorId=candidates[0].id;key=desired.key;targetOwnerId=input.ownerId;targetPartsType=desired.partsType;shotConfirmed=false;owned=true;phase='suppress';ownershipTick=tick;releasedTick=null;
      actions.setAutoAim(false);actions.setAutoSkill(false);
      // Suppress BEFORE changing the original player aim to an exposed slipper.
      for(const actor of actors)if(actor.id!==actorId)actions.setActorStance(actor.id,'Idle');
      actions.focus(actorId);
      const focused=actions.snapshot();
      if(focused.focusedIsAutoFireWeapon!==false){restore('replacement_weapon_is_native_autofire');return {handled:true,unsupported:'native_nonautomatic_charged_weapon_required'};}
      baseline=record(focused);log('ownership_started',{tick,priorAuto,priorSkill,nativeChargeGetter:true});
      return {handled:true,phase};
    }
    if(!candidates.some(a=>a.id===actorId)){restore('charged_actor_unavailable');return {handled:true};}
    let state=actions.snapshot();
    if(state.forcedCover||state.focusedEntityId!==actorId||state.autoAim!==false){restore('external_native_ownership');return {handled:false};}
    for(const actor of actors)if(actor.id!==actorId)actions.setActorStance(actor.id,'Idle');
    state=actions.snapshot();
    const others=state.squad.filter(a=>a.entityId!==actorId&&actors.some(b=>b.id===a.entityId&&positive(b.health?.hp)));
    const violations=others.filter(a=>nativeCount(a.usedAmmoCount)&&nativeCount(baseline.squad.get(a.entityId))&&a.usedAmmoCount>baseline.squad.get(a.entityId));
    if(violations.length){
      suppressionViolations+=violations.length;log('suppression_shot_observed',{tick,actors:violations});
      attempted.add(key);restore('nonfocused_native_shot_during_suppression');
      return {handled:true,suppressionFailed:true};
    }
    // Continue only once all surviving nonfocused actors actually read Idle.
    // Dead/stun/skill-animation actors remain native-owned and cannot be forced.
    if(others.some(a=>a.stance!==0)){log('waiting_for_native_idle',{tick,stances:others});return {handled:true,phase:'suppress'};}
    const fireTarget=valid.find(t=>t.key===key);
    actions.aimWorld(actorId,fireTarget?fireTarget.world:fallbackWorld,false,false);
    if(hasFired(state)) {
      log('uncommanded_native_ammo_consumption',{tick,usedAmmoCount:state.focusedUsedAmmoCount,
        baselineUsedAmmoCount:baseline.used,shotHitNum:state.focusedShotHitNum,explicitReleaseObserved:false});
      restore('native_weapon_fired_before_requested_release');return {handled:false,unsupported:'native_charge_release_semantics'};
    }
    if(phase==='released')return {handled:true,phase};
    if(state.inputType!==2){actions.press();phase='charging';log('native_charge_started',{tick});return {handled:true,phase};}
    if(state.focusedIsFullCharge===true&&fireTarget) {
      actions.release();releases++;phase='released';releasedTick=tick;attempted.add(key);stateAudit.markAttempted(targetOwnerId,targetPartsType);
      log('native_full_charge_released',{tick,releaseOrdinal:releases});
      // Keep suppression until a subsequent original native shot observation.
      return {handled:true,phase};
    }
    return {handled:true,phase:state.focusedIsFullCharge?'holding_native_full_charge_for_exposure':'charging'};
  }
  return {step,wantsOwnership,observeNativeState,suspend:reason=>restore(reason||'caller_suspended'),close:reason=>restore(reason||'caller_closed'),
    beforeNativeCleanup:()=>restore('native_cleanup',true),
    summary:()=>({enabled,coordinationEnabled,strategy,owned,actorId,targetKey:key,phase,releases,confirmed,suppressionViolations,watchdogAborts,ownershipTick,releasedTick,
      attempted:[...attempted],nativePhase,phase2PartTypes,nativeStateAudit:stateAudit?.summary()||null,nativeBehaviorValidated:false,chargeTiming:'original_IsFullCharge_only'})};
}

// Guide-backed input strategy, selected from original native kit identity rather
// than a captured squad/build. This never disables the kit's native effects.
function mechanicsMirrorStrategyForNameCodes(nameCodes) {
  if(!Array.isArray(nameCodes)||!nameCodes.length||nameCodes.some(n=>!Number.isSafeInteger(n)||n<=0))throw Error('Original native kit identities required');
  const corePressure=nameCodes.includes(5169);
  return {mode:corePressure?'core_pressure':'coordinated_slippers',nativeNameCodes:[...nameCodes],
    reason:corePressure?'original_Anis_Star_kit_guide_bruteforce_strategy':'compatible_kit_keeps_original_charged_slipper_coordination',
    source:'original_CharacterStaticInfo.get_NameCode',guide:'https://www.prydwen.gg/nikke/guides/ai-mirror-container',
    claimsStarSpoiledObservedShots:false,changesNativeEffects:false};
}
function readNativeMirrorTeamStrategy(runtime,aimBinding,emit,waveId) {
  if(waveId!==6302006)return {mode:'outside_mirror',readsNativeIdentity:false};
  const native=runtime.class('NK.Spot.Model.Character.SpotCharacter'),field=native.field('<CharacterStaticInfo>k__BackingField');
  if(field.offset!==112||field.isStatic||field.type.name!=='NK.StaticData.StaticDataLayer.StaticInfo.CharacterStaticInfo')throw Error('Original native kit identity field changed');
  const infoType=Il2Cpp.domain.assembly('NK.Runtime.StaticData').image.class('NK.StaticData.StaticDataLayer.StaticInfo.CharacterStaticInfo');
  const getName=infoType.method('get_NameCode',0),prefix=Array.from(new Uint8Array(getName.virtualAddress.readByteArray(24)),v=>v.toString(16).padStart(2,'0')).join('');
  if(getName.isStatic||getName.parameters.length||getName.returnType.name!=='NK.StaticData.Categoricals.NameCode'||
      !getName.virtualAddress.equals(Process.getModuleByName('GameAssembly.dll').base.add(82217344))||prefix!=='4883ec28488b49104885c9740b33d24883c428e9685ae4ff')throw Error('Original native NameCode getter changed');
  if(!(aimBinding.bound instanceof Map)||aimBinding.bound.size!==5)throw Error('Original five-member kit binding required');
  const nameCodes=[...aimBinding.bound.values()].map(actor=>{
    const entity=actor.entity;if(!entity||entity.isNull()||entity.class.type.name!==native.type.name)throw Error('Original native kit actor type missing');
    const info=entity.field('<CharacterStaticInfo>k__BackingField').value;
    if(!info||info.isNull()||info.class.type.name!==infoType.type.name)throw Error('Original native character static info missing');
    return invokeChecked(getName,info).unbox().handle.readS32();
  });
  const strategy=mechanicsMirrorStrategyForNameCodes(nameCodes);emit({status:'original_mirror_team_strategy',waveId,...strategy});return strategy;
}
