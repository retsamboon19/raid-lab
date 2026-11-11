// Original-input trial for source-bound Harvester non-timeline attacks only.
// No assumed impact timer or protection formula: retain targeted Idle ownership
// until the NEXT original boss attack, QTE/cover preemption, native phase change,
// target/cover loss or original finish. Native damage decides whether it protects.
function createMechanicsHarvesterTargetCover(actions,emit,configuration={}) {
  const enabled=configuration.waveId===6302010&&configuration.monsterId===1520010113;
  let owned=false,actorId=null,priorAuto=null,lastSequence=-1,phase=null,closed=false,entries=0,releases=0;
  const note=(action,detail={})=>emit({status:'original_harvester_targeted_cover',action,...detail,protectionClaimed:false});
  function release(reason,nativeFinish=false) {
    if(!owned)return;
    const previous=actorId,errors=[];
    try {
      if(nativeFinish)actions.restoreAutoAimBeforeNativeCleanup(priorAuto);
      else {
        try {if(actions.controlFlag("inputType")===2)actions.release();}catch(e){errors.push(e);}
        try {actions.setActorStance(actorId,'Aim');}catch(e){errors.push(e);}
        try {if(actions.controlFlag("autoAim")!==priorAuto)actions.setAutoAim(priorAuto);}catch(e){errors.push(e);}
      }
    } finally {owned=false;actorId=null;priorAuto=null;phase=null;releases++;note('released',{actorId:previous,reason,cleanupErrors:errors.map(String)});}
    if(errors.length)throw errors[0];
  }
  function wantsOwnership(observation,threat,context={}) {
    if(!enabled||closed||context.preempted)return false;
    const boss=observation?.monsters?.find(m=>m.entityId===observation.monster?.targetMonsterId&&String(m.tableId)===String(configuration.monsterId));
    const caster=boss?threat?.casters?.find(c=>c.casterId===boss.entityId):null;
    const attack=caster?[...(caster.recentAttacks||[]),caster.latestAttack].filter(a=>a&&[57,64,71].includes(a.attackNodeId)).sort((a,b)=>b.sequence-a.sequence)[0]:null;
    return owned||Boolean(attack&&attack.sequence!==lastSequence&&[57,64].includes(attack.attackNodeId));
  }
  function step(tick,observation,threat,context={}) {
    if(!enabled||closed)return false;
    const boss=observation?.monsters?.find(m=>m.entityId===observation.monster?.targetMonsterId&&String(m.tableId)===String(configuration.monsterId));
    const caster=boss?threat?.casters?.find(c=>c.casterId===boss.entityId):null;
    const attack=caster?[...(caster.recentAttacks||[]),caster.latestAttack].filter(a=>a&&[57,64,71].includes(a.attackNodeId)).sort((a,b)=>b.sequence-a.sequence)[0]:null;
    if(context.preempted||!boss||context.nativePhase!==phase&&owned) {
      release(context.preempted?'native_priority_preemption':!boss?'native_boss_unavailable':'native_phase_changed');
      if(attack)lastSequence=attack.sequence;return false;
    }
    if(attack&&attack.sequence!==lastSequence) {
      release('next_original_primary_boss_attack');lastSequence=attack.sequence;
      if(![57,64].includes(attack.attackNodeId))return false;
      const actor=observation.squad?.characters?.find(a=>a.id===attack.targetId);
      if(!actor||!/^\d+$/.test(actor.health?.hp)||BigInt(actor.health.hp)<=0n||!/^\d+$/.test(actor.cover?.health?.hp)||BigInt(actor.cover.health.hp)<=0n) {
        note('unsupported',{reason:'native_target_or_positive_cover_unavailable',attack});return false;
      }
      const state=actions.snapshot();
      if(state.forcedCover||state.inputType===2)return false;
      priorAuto=state.autoAim;actorId=actor.id;owned=true;phase=context.nativePhase;
      actions.setAutoAim(false);actions.focus(actorId);actions.setActorStance(actorId,'Idle');entries++;
      note('acquired',{tick,actorId,attack,sourceSkillId:attack.attackNodeId===57?510128:510129,lifecycle:'until_next_original_primary_57_64_71_or_native_preemption',otherActorsRetainOriginalAi:true});
    }
    if(!owned)return false;
    const actor=observation.squad?.characters?.find(a=>a.id===actorId);
    if(!actor||BigInt(actor.health.hp)<=0n||!actor.cover||BigInt(actor.cover.health.hp)<=0n) {release('native_target_or_cover_lost');return false;}
    const state=actions.snapshot();
    if(state.forcedCover||state.autoAim!==false||state.focusedEntityId!==actorId) {release('original_ownership_changed');return false;}
    actions.setActorStance(actorId,'Idle');return true;
  }
  return {step,wantsOwnership,close(reason='closed'){try{release(reason);}finally{closed=true;}},beforeNativeCleanup(){try{release('original_finish',true);}finally{closed=true;}},summary:()=>({enabled,owned,actorId,entries,releases,lastSequence,closed,protectionVerified:false,empiricalInputTrial:true})};
}
