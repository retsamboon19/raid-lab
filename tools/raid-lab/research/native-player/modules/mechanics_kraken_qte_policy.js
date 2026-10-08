// First bounded reactive policy: the observed original Kraken group212 only.
// No forecasts, damage writes, direct collider hits or guaranteed QTE outcomes.
function createMechanicsKrakenQtePolicy(actions,emit) {
  const version="kraken-qte-v2", reactionTicks=3,settleTicks=3;
  let owned=false,actorId=null,targetId=null,acquiredTick=-1,seenTick=-1;
  let priorAuto=null,decisions=0,targetsSelected=0,lastObservationTick=-1;
  let completedEpisode=false,nativePresetSuccesses=0,nativePresetFailures=0;
  const unsupported=new Set();
  const note=(action,detail={})=>{
    decisions++;
    emit({status:"native_kraken_qte_decision",policyVersion:version,action,...detail});
  };
  const release=()=>{ if (actions.snapshot().inputType===2) actions.release(); };
  function resume(tick,reason) {
    if (!owned) return;
    release(); actions.setAutoAim(priorAuto);
    note("resume_original_auto",{tick,reason});
    owned=false;actorId=null;targetId=null;seenTick=-1;
  }
  function reject(tick,reason) {
    if (!unsupported.has(reason)) { unsupported.add(reason);note("unsupported",{tick,reason}); }
    resume(tick,reason);
  }
  function step(tick,observation) {
    if (!observation) return;
    const qte=observation.qte;
    if (!qte || qte.supported!==true) { reject(tick,"live_qte_state_unavailable");return; }
    if (!qte.active) { resume(tick,"native_qte_ended");completedEpisode=false;return; }
    if (qte.groupId!==212) { reject(tick,"unvalidated_group_"+qte.groupId);return; }
    if (completedEpisode) return;
    const ended=observation.latestPresetEnd;
    if (owned && ended && ended.tick>=seenTick) {
      if (ended.success && qte.nativePresetSuccess) nativePresetSuccesses++;
      else nativePresetFailures++;
      completedEpisode=true;
      note("native_preset_result",{tick,nativeEvent:ended,
        nativePresetSuccess:qte.nativePresetSuccess});
      resume(tick,"native_preset_result");return;
    }
    const squad=observation.squad;
    if (!squad || squad.supported!==true) { reject(tick,"live_squad_unavailable");return; }
    if (seenTick<0) { seenTick=tick;note("observed_qte",{tick,groupId:qte.groupId}); }
    if (tick-seenTick<reactionTicks) return;
    if (!owned) {
      const candidates=squad.characters.filter(c=>Number(c.health.hp)>0 &&
        c.weapon && ["AR","MG","SMG"].includes(c.weapon.type.name) && Number(c.weapon.ammo)>0);
      // Native combined trial119 exposed slot-order selection: surviving MG
      // cleared only three circles before the deadline. The available SMG
      // passed the full chain in114/115. Prefer that input/weapon class for
      // this short group212 chain; do not assert this is a universal DPS rank.
      const priority={SMG:0,AR:1,MG:2};
      candidates.sort((a,b)=>priority[a.weapon.type.name]-priority[b.weapon.type.name] || a.id-b.id);
      if (!candidates.length) { reject(tick,"no_ready_continuous_fire_actor");return; }
      const initial=actions.snapshot();
      if (initial.forcedCover) { reject(tick,"existing_forced_cover");return; }
      // Select using current live availability, bounded weapon priority, and original
      // weapon type. Other weapon input cycles are not yet certified by this policy.
      actorId=candidates[0].id; priorAuto=initial.autoAim;
      release();actions.setAutoAim(false);actions.focus(actorId);
      // A unit already focused in original-auto can still be in fire stance
      // with pointer-up. A real press/release tap enters native released stance.
      if (actions.snapshot().focusedStance===2) { actions.press();actions.release(); }
      owned=true;
      note("take_manual_control",{tick,actorId,weapon:candidates[0].weapon.type});
    }
    const actor=squad.characters.find(c=>c.id===actorId);
    if (!actor || Number(actor.health.hp)<=0) { reject(tick,"controlled_actor_died");return; }
    const candidates=qte.targets.filter(t=>t.state.name==="Enable" &&
      t.colType.name==="Break" && Number(t.health.hp)>0 && Array.isArray(t.worldPosition) &&
      (t.order===0 || t.order===qte.currentOrder));
    candidates.sort((a,b)=>a.remainingNativeTime-b.remainingNativeTime || a.id-b.id);
    const target=candidates.find(t=>t.id===targetId) || candidates[0];
    if (!target) { release();targetId=null;return; }
    if (target.id!==targetId) {
      release();targetId=target.id;acquiredTick=tick;targetsSelected++;
      note("aim_break",{tick,actorId,targetId,entityId:target.entityId,order:target.order,
        remainingNativeTime:target.remainingNativeTime,
        avoidedCounterIds:qte.targets.filter(t=>t.colType.name==="Counter").map(t=>t.id)});
    }
    // Projection is refreshed every native frame as the original focus camera
    // settles. The input context still applies sensitivity, aim and real rays.
    actions.aimWorld(actorId,target.worldPosition,false);
    if (tick-acquiredTick>=settleTicks && actions.snapshot().inputType!==2)
      actions.press();
    lastObservationTick=observation.tick;
  }
  function summary() {
    return {version,reactionTicks,settleTicks,decisions,targetsSelected,owned,actorId,
      targetId,lastObservationTick,unsupported:[...unsupported],
      completedEpisode,nativePresetSuccesses,nativePresetFailures,
      nativeQteOutcomeRequired:true,supportedGroups:[212],coverPolicyImplemented:false};
  }
  return {step,summary};
}
