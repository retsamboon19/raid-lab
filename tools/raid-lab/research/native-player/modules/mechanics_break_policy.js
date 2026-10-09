// Candidate Mirror interrupt input, not a native-validated cancellation rule.
// Installed client 2df7134a: SpotMonster.TrySetBreakCollider 0x06372090
// populates live SpotMonsterBreakData; IsAllBreak 0x0638DFB0 checks original
// Break/Counter/Choice HP. Current Mirror wave 6302006/table 4510010123
// MonsterSkill rows 520669 (Shot09) and 520676 (Shot16) list BreakCol with
// break_col_01/02 and break_col_03..06 respectively. Retained BT node 84 is
// Shot_09, node 253 Shot_16. Trial128 observed 01/02 live after node 83
// AttackV3 Shot_25; that event does NOT by itself identify the skill. Never
// attribute an episode to a skill or claim native attack cancellation here.
function createMechanicsBreakPolicy(actions,emit,source) {
  if (!actions || typeof actions.snapshot!=="function" ||
      typeof actions.setAutoAim!=="function" || typeof actions.focus!=="function" ||
      typeof actions.aimWorld!=="function" || typeof actions.press!=="function" ||
      typeof actions.release!=="function" || typeof emit!=="function" ||
      !source || source.waveId!==6302006)
    throw new Error("Mirror break policy requires original actions and exact wave 6302006");
  const version="mirror-live-break-candidate-v2";
  const tableId="4510010123",names=new Set([
    "break_col_01","break_col_02","break_col_03","break_col_04",
    "break_col_05","break_col_06"]);
  const weaponPriority={SMG:0,AR:1,MG:2};
  const reactionTicks=3,settleTicks=3,maxLogs=160;
  const unsupported=new Set();
  let lastTick=-1,seenTick=-1,episodeKey=null,owned=false,suspended=false;
  let actorId=null,targetKey=null,targetSeenTick=-1,priorAuto=null;
  let fault=null,closed=false,decisions=0,emitted=0,selected=0,episodes=0;
  const validInt=(n,min=0)=>Number.isSafeInteger(n)&&n>=min;
  const finite=n=>typeof n==="number"&&Number.isFinite(n);
  const decimal=value=>typeof value==="string"&&/^-?\d+$/.test(value);
  const note=(action,detail={})=>{
    decisions++;
    if (emitted<maxLogs) {
      emitted++;
      emit({status:"original_mirror_break_decision",policyVersion:version,
        action,...detail});
    }
  };
  const limit=(tick,reason)=>{
    if (!unsupported.has(reason)) {
      unsupported.add(reason);note("unsupported",{tick,reason});
    }
  };
  const releasePress=()=>{
    if (owned&&actions.snapshot().inputType===2) actions.release();
  };
  function releaseControl(tick,reason) {
    if (!owned) return;
    releasePress();
    if (actions.snapshot().autoAim===false) actions.setAutoAim(priorAuto);
    note("release_manual_control",{tick,reason,actorId,targetKey});
    owned=false;actorId=null;targetKey=null;targetSeenTick=-1;priorAuto=null;
  }
  function readyActors(squad) {
    if (!squad || squad.supported!==true || !Array.isArray(squad.characters) ||
        squad.characters.length>5) return null;
    const actors=[];
    for (const actor of squad.characters) {
      if (!validInt(actor?.id,1)||!decimal(actor.health?.hp)||
          !decimal(actor.weapon?.ammo)) return null;
      if (BigInt(actor.health.hp)<=0n || BigInt(actor.weapon.ammo)<=0n) continue;
      if (!Object.hasOwn(weaponPriority,actor.weapon.type?.name)) continue;
      actors.push(actor);
    }
    actors.sort((a,b)=>weaponPriority[a.weapon.type.name]-
      weaponPriority[b.weapon.type.name]||a.id-b.id);
    return actors;
  }
  // Pure decision over retained original state. A bounds center is a live
  // candidate aiming point, not proof that a bullet will hit that collider.
  function inspect(tick,breakSnapshot,tacticalSnapshot) {
    if (!validInt(tick) || !breakSnapshot || breakSnapshot.supported!==true ||
        !validInt(breakSnapshot.tick) || breakSnapshot.tick>tick ||
        tick-breakSnapshot.tick>3)
      return {supported:false,reason:"recent_original_break_snapshot_unavailable"};
    if (!tacticalSnapshot || tacticalSnapshot.supported!==true ||
        !validInt(tacticalSnapshot.tick) || tacticalSnapshot.tick>tick ||
        tick-tacticalSnapshot.tick>3)
      return {supported:false,reason:"recent_original_tactical_snapshot_unavailable"};
    if (!Array.isArray(breakSnapshot.monsters) || breakSnapshot.monsters.length>32)
      return {supported:false,reason:"original_monster_collection_unreadable"};
    const matches=breakSnapshot.monsters.filter(m=>m?.tableId===tableId);
    if (matches.length>1) return {supported:false,reason:"multiple_mirror_monsters_ambiguous"};
    if (!matches.length) return {supported:true,wantsBreak:false,reason:"mirror_not_spawned"};
    const owner=matches[0];
    if (owner.supported!==true || !validInt(owner.entityId,1) ||
        typeof owner.playing!=="boolean" ||
        typeof owner.nativeIsAllBreak!=="boolean" ||
        !Array.isArray(owner.colliders) || owner.colliders.length>32)
      return {supported:false,reason:"original_mirror_break_state_unreadable"};
    if (!owner.playing || owner.nativeIsAllBreak)
      return {supported:true,wantsBreak:false,reason:"native_break_state_inactive",
        ownerId:owner.entityId};
    const ids=new Set(),targets=[];
    for (const item of owner.colliders) {
      if (!validInt(item?.colliderId) || ids.has(item.colliderId) ||
          !decimal(item.hp) || !decimal(item.maxHp) ||
          typeof item.enabled!=="boolean" ||
          typeof item.unityLive!=="boolean" ||
          !["Normal","Core","Break","Counter","Choice","None"]
            .includes(item.type?.name))
        return {supported:false,reason:"original_break_collider_fields_unreadable"};
      ids.add(item.colliderId);
      // Counter and Choice are never target candidates. Other collider types
      // are also excluded, regardless of position or remaining HP.
      if (item.type.name!=="Break" || BigInt(item.hp)<=0n ||
          !item.unityLive || !item.enabled) continue;
      if (!names.has(item.name))
        return {supported:false,reason:"live_break_name_outside_mirror_source_row"};
      if (item.aimPointBasis!=="UnityEngine.Collider.bounds.center" ||
          !Array.isArray(item.worldAimPoint) ||
          item.worldAimPoint.length!==3 ||
          !item.worldAimPoint.every(finite))
        return {supported:false,reason:"live_break_collider_bounds_unavailable"};
      targets.push({ownerId:owner.entityId,colliderId:item.colliderId,
        name:item.name,hp:item.hp,maxHp:item.maxHp,
        worldAimPoint:item.worldAimPoint});
    }
    targets.sort((a,b)=>a.colliderId-b.colliderId);
    const actors=readyActors(tacticalSnapshot.squad);
    if (actors===null) return {supported:false,reason:"original_squad_readiness_unavailable"};
    if (breakSnapshot.latestEpisodes!==undefined &&
        (!Array.isArray(breakSnapshot.latestEpisodes) ||
         breakSnapshot.latestEpisodes.length>64))
      return {supported:false,reason:"original_break_episode_ledger_unreadable"};
    const retained=(breakSnapshot.latestEpisodes||[])
      .find(e=>e.ownerId===owner.entityId);
    const episode=retained && validInt(retained.startSequence,1) ?
      owner.entityId+":"+retained.startSequence :
      owner.entityId+":observed_without_start_event";
    return {supported:true,wantsBreak:targets.length>0,ownerId:owner.entityId,
      episodeKey:episode,targets,actors,
      sourceSkillLinkVerified:false,nativeCancellationVerified:false};
  }
  function acquire(tick,actor) {
    const before=actions.snapshot();
    if (before.forcedCover || before.inputType===2 || before.autoAim!==true) {
      limit(tick,"original_input_lease_unavailable");return false;
    }
    priorAuto=before.autoAim;actorId=actor.id;owned=true;
    actions.setAutoAim(false);actions.focus(actorId);
    if (actions.snapshot().focusedStance===2) {
      actions.press();actions.release();
    }
    note("take_manual_control",{tick,actorId,
      weapon:actor.weapon.type.name,
      preference:"SMG_AR_MG_from_short_QTE_chain_not_break_DPS_proof"});
    return true;
  }
  function step(tick,breakSnapshot,tacticalSnapshot) {
    if (closed || fault!==null) return;
    try {
      if (!validInt(tick) || tick<=lastTick)
        throw new Error("Break policy needs one increasing native tick");
      lastTick=tick;
      const intent=inspect(tick,breakSnapshot,tacticalSnapshot);
      if (!intent.supported) {
        limit(tick,intent.reason);releaseControl(tick,intent.reason);return;
      }
      if (!intent.wantsBreak) {
        releaseControl(tick,intent.reason||"no_live_break_target");
        episodeKey=null;seenTick=-1;return;
      }
      if (episodeKey!==intent.episodeKey) {
        releaseControl(tick,"new_original_break_episode");
        episodeKey=intent.episodeKey;seenTick=tick;episodes++;
        note("observed_live_break_episode",{tick,episodeKey,
          ownerId:intent.ownerId,colliderIds:intent.targets.map(t=>t.colliderId),
          sourceSkillLinkVerified:false});
      }
      if (suspended) return;
      if (tick-seenTick<reactionTicks) return;
      if (owned && !intent.actors.some(a=>a.id===actorId))
        releaseControl(tick,"controlled_actor_reloading_or_unavailable");
      if (!intent.actors.length) {releasePress();return;}
      if (!owned && !acquire(tick,intent.actors[0])) return;
      const control=actions.snapshot();
      if (control.forcedCover || control.autoAim!==false ||
          control.focusedEntityId!==actorId) {
        limit(tick,"original_input_ownership_changed");
        releaseControl(tick,"original_input_ownership_changed");return;
      }
      const target=intent.targets.find(t=>
        t.ownerId+":"+t.colliderId===targetKey)||intent.targets[0];
      const key=target.ownerId+":"+target.colliderId;
      if (key!==targetKey) {
        releasePress();targetKey=key;targetSeenTick=tick;selected++;
        note("aim_live_break",{tick,actorId,targetKey,name:target.name,
          ownerId:target.ownerId,colliderId:target.colliderId,
          hp:target.hp,maxHp:target.maxHp,
          aimPointBasis:"UnityEngine.Collider.bounds.center",
          sourceSkillLinkVerified:false});
      }
      actions.aimWorld(actorId,target.worldAimPoint,false);
      if (tick-targetSeenTick>=settleTicks && actions.snapshot().inputType!==2)
        actions.press();
    } catch(error) {
      fault="step: "+(error&&error.stack?error.stack:String(error));
      try { releaseControl(tick,"policy_fault"); }
      catch(cleanupError) { fault+="; cleanup: "+String(cleanupError); }
    }
  }
  function suspend(tick,reason="higher_priority_mechanic") {
    if (closed || fault!==null || suspended) return;
    try {
      if (!validInt(tick)) throw new Error("Break suspend needs original tick");
      releaseControl(tick,reason);suspended=true;
      note("suspended",{tick,reason});
    } catch(error) {fault="suspend: "+String(error);}
  }
  function resume(tick) {
    if (closed || fault!==null || !suspended) return false;
    try {
      if (!validInt(tick)) throw new Error("Break resume needs original tick");
      if (actions.snapshot().forcedCover) return false;
      suspended=false;seenTick=tick;targetKey=null;targetSeenTick=-1;
      note("resumed",{tick});return true;
    } catch(error) {fault="resume: "+String(error);return false;}
  }
  function close(reason="caller_closed") {
    if (closed) return;
    try {releaseControl(lastTick,reason);}
    finally {closed=true;suspended=false;}
  }
  function checkFault() {if (fault!==null) throw new Error(fault);}
  function summary() {
    return {version,waveId:source.waveId,monsterTableId:tableId,
      candidateSourceSkillIds:[520669,520676],
      expectedSourceSkillId:null,sourceSkillLinkVerified:false,
      nativeCancellationVerified:false,aimpointHitVerified:false,
      reactionTicks,settleTicks,lastTick,episodeKey,episodes,
      owned,suspended,actorId,targetKey,targetsSelected:selected,
      decisions,emitted,decisionEmissionLimit:maxLogs,
      decisionsTruncated:decisions>maxLogs,
      unsupported:[...unsupported],fault,closed};
  }
  return {inspect,step,suspend,resume,close,checkFault,summary};
}
