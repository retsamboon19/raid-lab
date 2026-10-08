// Reactive whole-squad cover through original player commands. Rules are scoped
// to a source-bound wave AND a live original monster table identity. A node ID
// alone is not a boss identity. Unknown attacks retain original automatic play.
function createMechanicsCoverPolicy(actions,emit,rules,waveId) {
  if (!actions||typeof actions.snapshot!=="function"||
      typeof actions.setCover!=="function"||typeof emit!=="function"||
      !Array.isArray(rules)||!Number.isSafeInteger(waveId))
    throw new Error("Cover policy requires original actions and explicit rules");
  // Only this installed-client/source-tested rule is approved. A similarly
  // numbered node in another wave or monster is not a cover signal.
  const approved=mechanicsVerifiedCoverRules()[0];
  for (const r of rules) {
    if (!r||r.id!==approved.id||r.waveId!==approved.waveId||
        r.monsterTableId!==approved.monsterTableId||
        r.attackNodeId!==approved.attackNodeId||
        r.projectileSkillId!==approved.projectileSkillId||
        r.reactionTicks!==approved.reactionTicks||
        r.releaseCondition!==approved.releaseCondition||
        r.requireCasting!==approved.requireCasting||
        r.source?.clientSha256!==approved.source.clientSha256||
        !Array.isArray(r.source.nativeTrials)||
        !approved.source.nativeTrials.every(v=>r.source.nativeTrials.includes(v)))
      throw new Error("Cover rule lacks the exact source-bound Kraken contract");
  }
  const selected=rules.filter(r=>r.waveId===waveId);
  const ruleIds=new Set();
  for (const r of selected) {
    if (!r.id||ruleIds.has(r.id)||!/^\d+$/.test(r.monsterTableId)||
        !Number.isSafeInteger(r.attackNodeId)||!Number.isSafeInteger(r.reactionTicks)||
        r.reactionTicks<1||r.reactionTicks>30||!Number.isSafeInteger(r.projectileSkillId)||
        r.releaseCondition!=="Idle"||r.requireCasting!==true||!r.source)
      throw new Error("Unbound/unsupported native cover rule");
    ruleIds.add(r.id);
  }
  const pending=new Map(),seen=new Map(),seenOrdinals=new Map(),unsupported=new Set();
  let covered=false,entered=null,completed=0,commands=0,lastTick=-1;
  let lastInspectTick=-1,resumeChecks=0,conflicts=0,logs=0,droppedLogs=0;
  let historyCursorAvailable=false,historyGapCount=0;
  const resumes=[];
  const log=row=>{
    if (logs++<128) emit({status:"native_cover_decision",...row});
    else droppedLogs++;
  };
  const limitation=(tick,reason)=>{
    if (!unsupported.has(reason)) {unsupported.add(reason);log({tick,action:"unsupported",reason});}
  };
  function inspect(tick,observation,threat) {
    if (!Number.isSafeInteger(tick)||tick<0||tick<lastInspectTick)
      throw new Error("Cover inspection requires increasing original ticks");
    lastInspectTick=tick;
    if (selected.length===0) return {wantsCover:false,covered};
    if (!observation||!threat||!Number.isSafeInteger(observation.tick)||
        observation.tick>tick||tick-observation.tick>3||threat.tick!==observation.tick) {
      limitation(tick,"stale_or_missing_original_tick_snapshot");
      return {wantsCover:covered,covered};
    }
    if (observation.supported!==true||threat.supported!==true||
        !Array.isArray(observation.monsters)||!Array.isArray(threat.casters)) {
      limitation(tick,"original_monster_or_threat_identity_unavailable");
      return {wantsCover:covered,covered};
    }
    const monsters=new Map();
    for (const monster of observation.monsters) {
      if (!Number.isSafeInteger(monster.entityId)||monsters.has(monster.entityId))
        throw new Error("Original monster identity duplicated or invalid");
      monsters.set(monster.entityId,monster);
    }
    for (const caster of threat.casters) {
      // The observer's global historyTruncated flag means its bounded ring has
      // ever discarded an attack, including attacks consumed many ticks ago.
      // Only a per-caster ordinal gap can establish a missed attack here.
      const hasCursor=Number.isSafeInteger(caster.totalAttackCount)&&
        caster.totalAttackCount>=0&&caster.recentAttacks.every(a=>
          Number.isSafeInteger(a.attackOrdinal)&&a.attackOrdinal>=1);
      if (hasCursor) {
        historyCursorAvailable=true;
        const previous=seenOrdinals.get(caster.casterId)||0;
        const firstUnseen=caster.recentAttacks.find(a=>a.attackOrdinal>previous);
        if ((firstUnseen&&firstUnseen.attackOrdinal>previous+1)||
            (!firstUnseen&&caster.totalAttackCount>previous)) {
          historyGapCount++;
          limitation(tick,"original_attack_history_cursor_gap");
        }
      }
      const last=seen.get(caster.casterId)||0;
      for (const attack of caster.recentAttacks) {
        if (attack.sequence<=last) continue;
        const monster=monsters.get(caster.casterId);
        if (!monster) {limitation(tick,"attack_caster_missing_live_table_identity");continue;}
        for (const rule of selected) {
          if (rule.monsterTableId!==monster.tableId||rule.attackNodeId!==attack.attackNodeId) continue;
          const key=rule.id+":"+caster.casterId+":"+attack.sequence;
          if (pending.size>=32) throw new Error("Cover policy active threat bound exceeded");
          pending.set(key,{key,rule,attack,seenProjectileIds:new Set(),
            sawSkill:false,sawCasting:false,sawPostProjectileCasting:false,
            postProjectileCastingTick:-1,projectilesClearedTick:-1});
          log({tick,action:"danger_observed",key,ruleId:rule.id,monsterTableId:monster.tableId,attack});
        }
        seen.set(caster.casterId,Math.max(seen.get(caster.casterId)||0,attack.sequence));
        if (hasCursor) seenOrdinals.set(caster.casterId,
          Math.max(seenOrdinals.get(caster.casterId)||0,attack.attackOrdinal));
      }
    }
    for (const item of pending.values()) {
      const caster=threat.casters.find(c=>c.casterId===item.attack.casterId);
      const monster=monsters.get(item.attack.casterId);
      const condition=(observation.monsterConditions||[]).find(c=>c.monsterInfoId===item.attack.casterId);
      if (!caster) {
        item.resolved=false;
        limitation(tick,"tracked_cover_caster_disappeared");continue;
      }
      const casting=monster&&["FireCasting","Fire"].includes(monster.condition?.name);
      if (casting) item.sawCasting=true;
      if (caster.latestCreate&&caster.latestCreate.tick>=item.attack.tick&&
          caster.latestCreate.sequence>item.attack.sequence&&
          caster.latestCreate.skillId===item.rule.projectileSkillId) item.sawSkill=true;
      for (const projectile of caster.activeProjectiles)
        if (projectile.spawnTick>item.attack.tick ||
            (projectile.spawnTick===item.attack.tick &&
             projectile.source?.createSequence>item.attack.sequence))
          item.seenProjectileIds.add(projectile.projectileId);
      if (caster.activeProjectiles.length>0) item.projectilesClearedTick=-1;
      else if (item.seenProjectileIds.size>0&&item.projectilesClearedTick<0)
        item.projectilesClearedTick=tick;
      if (casting&&condition&&["FireCasting","Fire"].includes(
          condition.condition?.name)&&condition.tick>item.attack.tick&&
          item.sawSkill&&item.seenProjectileIds.size>0&&
          caster.activeProjectiles.length===0) {
        item.sawPostProjectileCasting=true;
        // Use the native transition's tick. A sampled live state can lag its
        // corresponding Idle event by up to the observer's three-tick cadence.
        item.postProjectileCastingTick=Math.max(
          item.postProjectileCastingTick,condition.tick);
      }
      // Idle is a live original condition, never a guessed attack duration.
      // Unknown skill associations are retained until every caster projectile
      // resolves; an unrelated monster cannot release this caster's cover.
      item.resolved=item.sawSkill&&item.seenProjectileIds.size>0&&
        item.sawCasting&&item.sawPostProjectileCasting&&
        caster.activeProjectiles.length===0&&
        (!threat.pendingUnlinkedCreate||threat.pendingUnlinkedCreate.ownerId!==item.attack.casterId)&&
        condition&&condition.tick>item.postProjectileCastingTick&&
        condition.tick>item.projectilesClearedTick&&
        condition.condition.name===item.rule.releaseCondition&&
        monster&&monster.condition.name===item.rule.releaseCondition;
      item.condition=condition||null;
    }
    if (!covered) for (const [key,item] of pending)
      if (item.resolved) {
        pending.delete(key);
        log({tick,action:"resolved_before_cover",key,ruleId:item.rule.id});
      }
    return {covered,wantsCover:[...pending.values()].some(p=>!p.resolved&&
      tick-p.attack.tick>=p.rule.reactionTicks)};
  }
  function step(tick,observation,threat,{qteSuspended=false}={}) {
    if (!Number.isSafeInteger(tick)||tick<lastTick) throw new Error("Cover policy tick moved backwards");
    if (tick===lastTick) return;
    lastTick=tick;
    const intent=inspect(tick,observation,threat);
    if (covered&&!actions.snapshot().forcedCover) {
      limitation(tick,"cover_ownership_lost_before_native_resolution");
      covered=false;entered=null;
    }
    if (!covered&&!intent.wantsCover) {
      while (resumes.length&&tick>=resumes[0].tick+15) {
        const resume=resumes.shift(),state=actions.snapshot();
        const old=new Map(resume.ammo.map(u=>[u.entityId,u.usedAmmoCount]));
        const firingResumed=Array.isArray(state.squad)&&state.squad.some(u=>
          old.has(u.entityId)&&u.usedAmmoCount>old.get(u.entityId));
        log({tick,action:"resume_readback",releaseTick:resume.tick,state,firingResumed});
        if (!Array.isArray(state.squad))
          limitation(tick,"native_resume_squad_readback_unavailable");
        resumeChecks++;
      }
    }
    if (intent.wantsCover&&!covered) {
      const before=actions.snapshot();
      if (before.inputType===2||before.forcedCover||before.autoAim!==true) {
        limitation(tick,"cover_requires_released_original_auto_ownership");return;
      }
      if (qteSuspended) {conflicts++;log({tick,action:"qte_cover_conflict",priority:"source_scoped_cover"});}
      actions.setCover(true);commands++;
      const after=actions.snapshot();
      if (!after.forcedCover) throw new Error("Original cover command failed readback");
      covered=true;entered={tick,squad:observation.squad,ammo:after.squad};
      log({tick,action:"entered",threats:[...pending.values()].map(p=>({key:p.key,attack:p.attack,ruleId:p.rule.id})),
        squadBefore:observation.squad,nativeAfter:after});
    }
    if (covered&&pending.size>0&&[...pending.values()].every(p=>p.resolved)) {
      const before=actions.snapshot();
      actions.setCover(false);commands++;
      const after=actions.snapshot();
      if (after.forcedCover) throw new Error("Original cover release failed readback");
      const resolved=[...pending.values()].map(p=>({key:p.key,ruleId:p.rule.id,attack:p.attack,
        condition:p.condition,sawSkill:p.sawSkill,sawCasting:p.sawCasting,projectileIds:[...p.seenProjectileIds]}));
      covered=false;completed+=resolved.length;
      if (resumes.length>=32) throw new Error("Cover resume readback bound exceeded");
      resumes.push({tick,ammo:Array.isArray(before.squad)?before.squad:[]});
      log({tick,action:"released",coverTick:entered.tick,resolved,
        squadAfter:observation.squad,nativeBefore:before,nativeAfter:after});
      pending.clear();entered=null;
    }
  }
  const summary=()=>({version:"native-cover-v1",waveId,ruleIds:[...ruleIds],covered,completed,
    pending:[...pending.keys()],pendingResumeChecks:resumes.length,resumeChecks,
    historyCursorAvailable,historyGapCount,
    commands,conflicts,unsupported:[...unsupported],droppedLogs,
    scope:"Only explicitly source-scoped rules; other attacks use original auto"});
  return {inspect,step,summary};
}

function mechanicsVerifiedCoverRules() {
  return [{id:"kraken-intercept-shot02-followup",waveId:6302009,monsterTableId:"1520040153",
    attackNodeId:230,projectileSkillId:532033,reactionTicks:3,releaseCondition:"Idle",requireCasting:true,
    source:{clientSha256:"2df7134a6a9c3a8dbbde88402fc8d16d1d6c3f4c2d5e262bea78c3d78b96dd02",
      nativeTrials:[120,121],scope:"Exact native missile and follow-up-cast sequence"}}];
}
