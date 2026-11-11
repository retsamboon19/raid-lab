// Original Mirror phase-two slipper exposure. The four authored attacks share
// one timeline; target identity comes from original live part/collider state,
// never from a guessed clip-side mapping. No wall-clock or guide timestamps.
function mechanicsMirrorTimelineRules(waveId) {
  if(waveId!==6302006)return [];
  return [{monsterId:4510010123,clip:'xba001_skill_04',role:'mirror_slipper_exposure',
    allowedPartNames:['Weapon_07','Weapon_08','Weapon_09','Weapon_10'],
    prepareStart:0,windowStart:2.3333333333333335,windowEnd:4.666666666666667,
    sourceAnimationNumbers:[12,13,14,15],sourceNodeIds:[177,191,205,219],
    ruleId:'mirror-phase2-native-shared-slipper-timeline',
    sharedClipRequiresLivePartIdentity:true,source:'mirror-exposure-source153.json'}];
}
function mechanicsMirrorExposureTargetAllowed(target,rows,nativePhase,phase2PartTypes,baselineHurtCount=0) {
  if(nativePhase!==2||!target||!Array.isArray(phase2PartTypes)||!phase2PartTypes.includes(target.partsType))return false;
  // These fields must come from the original enabled Collider and its live
  // world bounds, joined to the same native active positive-HP PartsData.
  if(target.nativeColliderEnabled!==true||!Number.isSafeInteger(target.colliderId)||
    target.nativePartActive!==true||target.nativeIsDestroyed!==false||
    !Number.isSafeInteger(baselineHurtCount)||baselineHurtCount<0||target.hurtCount!==baselineHurtCount||
    typeof target.hp!=='string'||!/^\d+$/.test(target.hp)||BigInt(target.hp)<=0n||
    !Array.isArray(target.world)||target.world.length!==3||!target.world.every(Number.isFinite))return false;
  return (rows||[]).some(row=>row.role==='mirror_slipper_exposure'&&row.ownerId===target.ownerId&&
    (row.name||row.clip)==='xba001_skill_04'&&Number.isFinite(row.time)&&
    row.time>=2.3333333333333335&&row.time<=4.666666666666667);
}

// During original timeline windup, suppress/charge while aiming the native
// core. Raw active part identity is sufficient to prepare; firing still needs
// the enabled collider bounds and open source marker window above.
function mechanicsMirrorPreparePartAllowed(rows,target,nativePhase,phase2PartTypes,baselineHurtCount=0) {
  if(nativePhase!==2||!target||!phase2PartTypes.includes(target.partsType)||
    target.nativePartActive!==true||target.nativeIsDestroyed!==false||
    !Number.isSafeInteger(baselineHurtCount)||baselineHurtCount<0||target.hurtCount!==baselineHurtCount||
    typeof target.hp!=='string'||!/^\d+$/.test(target.hp)||BigInt(target.hp)<=0n)return false;
  return (rows||[]).some(row=>row.role==='mirror_slipper_exposure'&&row.ownerId===target.ownerId&&
    (row.name||row.clip)==='xba001_skill_04'&&Number.isFinite(row.time)&&row.time>=0&&row.time<=4.666666666666667);
}

function mechanicsMirrorExposurePartAllowed(rows,target,nativePhase,phase2PartTypes,baselineHurtCount=0) {
  return mechanicsMirrorExposureTargetAllowed(target,rows,nativePhase,phase2PartTypes,baselineHurtCount);
}

// Pure observation/audit. Must run after EVERY original tactical snapshot,
// including QTE, cover, no live parts, and no eligible timeline window. This
// never sends input, restores a part, changes HP, resets HurtCount or buffs.
function createMechanicsMirrorStateAudit(emit,phase2PartTypes) {
  const states=new Map(),lastOwnerTick=new Map();let snapshots=0,repairs=0,firstHits=0,destroyedTransitions=0,firstHitKills=0;
  const positive=value=>typeof value==='string'&&/^\d+$/.test(value)&&BigInt(value)>0n;
  const log=(action,detail)=>emit({status:'native_mirror_one_shot',action,...detail,readsOnly:true});
  function observeNativeState(input) {
    const {tick,phase,partStates=[],ownerId}=input||{};
    if(!Number.isSafeInteger(tick)||!Number.isSafeInteger(ownerId))return;
    const signature=JSON.stringify([phase,partStates.map(p=>[p.partsType,p.hp,p.hurtCount,p.nativePartActive,p.nativeIsDestroyed])]);
    const prior=lastOwnerTick.get(ownerId);if(prior?.tick===tick&&prior.signature===signature)return;
    lastOwnerTick.set(ownerId,{tick,signature});snapshots++;
    for(const part of partStates.filter(p=>phase2PartTypes.includes(p.partsType))) {
      if(!Number.isSafeInteger(part.hurtCount)||part.hurtCount<0)continue;
      const key=ownerId+':'+part.partsType,previous=states.get(key);
      const explicitRepair=previous&&(previous.current.nativeIsDestroyed===true&&part.nativeIsDestroyed===false||
        part.hurtCount<previous.current.hurtCount);
      const fresh=!previous;
      const state=previous||{epoch:0,baselineHurtCount:0,attempted:false,firstHitRecorded:false,
        // A mid-exposure installation cannot call an already-hurt part fresh.
        baselineProved:part.hurtCount===0};
      if(explicitRepair) {
        state.epoch++;state.baselineHurtCount=part.hurtCount;state.attempted=false;
        state.firstHitRecorded=false;state.baselineProved=true;repairs++;
        log('native_slipper_repair_observed',{tick,nativePhase:phase,ownerId,partsType:part.partsType,
          epoch:state.epoch,baselineHurtCount:part.hurtCount,previousDestroyed:previous.current.nativeIsDestroyed,
          currentDestroyed:part.nativeIsDestroyed,originalHurtCounterReset:part.hurtCount<previous.current.hurtCount});
      }
      const hurtIncreased=previous&&part.hurtCount>previous.current.hurtCount;
      const destroyedNow=previous&&positive(previous.current.hp)&&part.hp==='0'&&part.nativeIsDestroyed===true;
      if(destroyedNow) {
        destroyedTransitions++;if(hurtIncreased)firstHitKills++;
        log('native_slipper_destroyed_transition',{tick,nativePhase:phase,ownerId,partsType:part.partsType,
          epoch:state.epoch,previousHp:previous.current.hp,hp:part.hp,hurtCount:part.hurtCount,
          newHurtSameObservation:!!hurtIncreased,damageAttributionProved:!!hurtIncreased,
          shieldRemovalProved:false});
      }
      if(phase===2&&part.hurtCount>state.baselineHurtCount&&!state.firstHitRecorded) {
        state.firstHitRecorded=true;firstHits++;
        log('native_first_hit_outcome',{tick,nativePhase:phase,ownerId,partsType:part.partsType,
          epoch:state.epoch,baselineHurtCount:state.baselineHurtCount,hurtCount:part.hurtCount,hp:part.hp,
          nativeIsDestroyed:part.nativeIsDestroyed,destroyed:part.hp==='0'&&part.nativeIsDestroyed===true,
          attemptedThisExposure:state.attempted,shieldRemovalProved:false});
      }
      const signature=JSON.stringify([part.hp,part.hurtCount,part.nativePartActive,part.nativeIsDestroyed]);
      if(fresh||previous.signature!==signature)log('native_slipper_state',{tick,nativePhase:phase,ownerId,
        ...part,epoch:state.epoch,baselineHurtCount:state.baselineHurtCount});
      state.current={...part};state.signature=signature;state.tick=tick;states.set(key,state);
    }
  }
  const exposure=(ownerId,partsType)=>{
    const state=states.get(ownerId+':'+partsType);if(!state)return null;
    return {epoch:state.epoch,baselineHurtCount:state.baselineHurtCount,baselineProved:state.baselineProved,
      attempted:state.attempted,firstHitConsumed:state.current.hurtCount>state.baselineHurtCount,
      current:{...state.current}};
  };
  const markAttempted=(ownerId,partsType)=>{const state=states.get(ownerId+':'+partsType);if(state)state.attempted=true;};
  return {observeNativeState,exposure,markAttempted,summary:()=>({snapshots,repairs,firstHits,destroyedTransitions,
    firstHitKills,shieldRemovalProved:false,nativeBehaviorValidated:false,readsOnly:true})};
}
