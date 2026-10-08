// Passive original threat telemetry. Forward the already wrapped event
// from the existing SendEventDefault hook; this module installs no native hooks.
// All managed metadata resolution occurs at construction, never in dispatch.
function createMechanicsThreatObserver(runtime, management, emit, configuration) {
  if (!runtime || !management || management.isNull() || typeof emit !== "function")
    throw new Error("Original threat observer requires live management and emit");
  const game=Process.getModuleByName("GameAssembly.dll");
  const at=(method,rva,label)=>{
    if (!method.virtualAddress.equals(game.base.add(rva)))
      throw new Error("Installed threat method changed: "+label);
  };
  const layout=(klass,name,offset)=>{
    if (klass.field(name).offset!==offset)
      throw new Error("Installed threat field changed: "+klass.name+"."+name);
  };
  const live=value=>value!=null&&!value.isNull();
  const numeric=value=>typeof value==="number"||typeof value==="boolean" ?
    Number(value):Number(value.field("value__").value);
  const bounded=(value,label)=>{
    const n=Number(value);
    if (!Number.isSafeInteger(n)||n<0||n>0xffffffff)
      throw new Error("Original threat "+label+" invalid: "+value);
    return n;
  };
  const signed=(value,label)=>{
    const n=Number(value);
    if (!Number.isSafeInteger(n)||n<-0x80000000||n>0x7fffffff)
      throw new Error("Original threat "+label+" invalid: "+value);
    return n;
  };
  const positive=(value,label)=>{
    const n=bounded(value,label);
    if (n===0) throw new Error("Original threat "+label+" is zero");
    return n;
  };
  const options=configuration===undefined?{mode:"kraken"}:configuration;
  if (!options || !["kraken","monster","verified_ids"].includes(options.mode))
    throw new Error("Threat observer requires kraken, monster, or verified_ids mode");
  const idsConfigured=options.verifiedBossIds===undefined?[]:
    options.verifiedBossIds;
  if (!Array.isArray(idsConfigured)||idsConfigured.length>32)
    throw new Error("Threat verifiedBossIds must be an array of at most 32 IDs");
  const verifiedIds=new Set(idsConfigured.map(id=>positive(id,"verified boss ID")));
  if (verifiedIds.size!==idsConfigured.length ||
      (options.mode==="verified_ids" && verifiedIds.size===0) ||
      (options.mode==="kraken" && verifiedIds.size>0))
    throw new Error("Threat verifiedBossIds are duplicated or invalid for mode");
  const historyLimit=options.maxRecentAttacks===undefined?16:
    positive(options.maxRecentAttacks,"maxRecentAttacks");
  if (historyLimit>64) throw new Error("Threat maxRecentAttacks exceeds 64");
  const watchNodes=options.watchAttackNodes===undefined?
    (options.mode==="kraken"?[229,230]:[]):options.watchAttackNodes;
  if (!Array.isArray(watchNodes)||watchNodes.length>64||
      watchNodes.some(n=>!Number.isSafeInteger(n)||n<0))
    throw new Error("Invalid threat log watch nodes");
  const original=runtime.class("NK.Spot.Common.SpotEvent");
  const ids=original.nested("SpotEventType");
  const info=runtime.class("NK.Spot.Logic.Character.SpotEntityInfo");
  const data=runtime.class("NK.Spot.Event.Projectile.ProjectileData");
  const attack=runtime.class("NK.Spot.Event.Monster.MonsterAttackEvent");
  const create=runtime.class("NK.Spot.Event.Projectile.ProjectileCreateEvent");
  const spawn=runtime.class("NK.Spot.Event.Projectile.ProjectileSpawnEvent");
  const despawn=runtime.class("NK.Spot.Event.Projectile.ProjectileDespawnEvent");
  const damage=runtime.class("NK.Spot.Event.Common.OnEntityGetDamageEvent");
  const coverDamage=runtime.class("NK.Spot.Event.Character.CoverTakeDamageEvent");
  const objectTypes=runtime.class("NK.Spot.Model.Enum.SpotObjectType");
  at(management.method("SendEventDefault",1),0x0614BAF0,"SendEventDefault");
  // The original FireProjectile -> ProjectileCreate dispatch is synchronous.
  // ProjectileContext.OnProjectileCreate constructs an entity and sends Spawn
  // before returning. Only the immediately nested, matching Spawn is linked.
  at(runtime.class("NK.Spot.Logic.Monster.MonsterAttackLogic")
    .method("FireProjectile",6),0x063BDC00,"FireProjectile");
  at(runtime.class("NK.Spot.ProjectileContext").method("OnProjectileCreate",1),
    0x06142DB0,"ProjectileContext.OnProjectileCreate");
  for (const [klass,name,offset] of [
    [management.class,"_tickCount",0x64],[management.class,"_playtime",0x6c],
    [original,"<SpotEventID>k__BackingField",0x14],
    [info,"EntityID",0x10],[info,"ObjectType",0x14],
    [attack,"CasterInfo",0x40],[attack,"TargetInfo",0x48],
    [attack,"AttackNodeID",0x64],[attack,"AniNumber",0x5c],
    [create,"Data",0x40],[create,"IsCharacter",0x48],
    [data,"OwnerId",0x10],[data,"TargetId",0x58],
    [data,"SkillId",0x5c],[data,"IsDestroyable",0x60],
    [spawn,"CasterInfo",0x40],[spawn,"ProjectileInfo",0x48],
    [despawn,"ProjectileInfo",0x40],[despawn,"DespawnTypeEnum",0x54],
    [damage,"CasterInfo",0x40],[damage,"TargetInfo",0x48],
    [damage,"TargetSubID",0x50],[damage,"Damage",0x58],
    [damage,"ActualDamage",0x60],[damage,"DamageType",0x68],
    [damage,"IsCritical",0x78],[damage,"IsImmune",0x79],
    [damage,"IsShare",0x7a],
    [coverDamage,"CasterInfo",0x40],[coverDamage,"CoverInfo",0x48],[coverDamage,"Damage",0x60],
    [runtime.class("NK.Common.StatValue"),"Value",0x10]
  ]) layout(klass,name,offset);
  const expected=new Map();
  for (const [klass,enumName,kind] of [
    [attack,"MonsterAttack","attack"],[create,"ProjectileCreate","create"],
    [spawn,"ProjectileSpawn","spawn"],[despawn,"ProjectileDespawn","despawn"],
    [damage,"OnEntityGetDamage","damage"],[coverDamage,"CoverTakeDamage","cover_damage"]
  ]) expected.set(klass.type.name,{kind,id:numeric(ids.field(enumName).value)});
  const characterType=numeric(objectTypes.field("Character").value);
  const coverType=numeric(objectTypes.field("Cover").value);
  const monsterType=numeric(objectTypes.field("Monster").value);
  if (new Set([characterType,coverType,monsterType]).size!==3)
    throw new Error("Original Character/Cover/Monster object types collide");
  const infoId=(object,label)=>live(object)?
    positive(object.field("EntityID").value,label):null;
  const stat=(object,name)=>object.field(name).value.field("Value").value.toString();
  const stamp=()=>{
    const tick=bounded(management.field("_tickCount").value,"tick");
    const nativePlaytime=Number(management.field("_playtime").value);
    if (!Number.isFinite(nativePlaytime)||nativePlaytime<0)
      throw new Error("Original threat playtime invalid");
    return {tick,nativePlaytime};
  };
  const maxLogs=200,maxActive=64,maxCasters=32;
  let fault=null,sequence=0,logs=0,droppedLogs=0,lastSnapshotTick=-1,pending=null;
  let linked=0,unlinkedCreates=0,unknownSpawns=0,unmatchedDespawns=0;
  let unclassifiedCreates=0,historyDropped=0;
  let watchingDanger=false,unwatchedLogs=0;
  const counts={attack:0,create:0,spawn:0,despawn:0,damage:0,cover_damage:0};
  const active=new Map(),latest={attack:null,create:null,spawn:null,despawn:null,damage:null};
  const casters=new Map(),observedMonsterIds=new Set();
  const casterIdFromInfo=(entityInfo,label)=>{
    const id=infoId(entityInfo,label);
    if (id===null) return null;
    if (options.mode==="kraken") return id===8192?id:null;
    if (numeric(entityInfo.field("ObjectType").value)!==monsterType) return null;
    if (verifiedIds.size>0 && !verifiedIds.has(id)) return null;
    observedMonsterIds.add(id);
    return id;
  };
  const acceptCreateOwner=id=>options.mode==="kraken"?id===8192:
    verifiedIds.has(id)||observedMonsterIds.has(id);
  const casterState=id=>{
    let state=casters.get(id);
    if (!state) {
      if (casters.size>=maxCasters)
        throw new Error("Original threat caster count exceeds bound");
      state={casterId:id,totalAttackCount:0,recentAttacks:[],activeProjectileIds:new Set(),
        latestAttack:null,latestCreate:null,latestSpawn:null,
        latestDespawn:null,latestDamage:null,latestCoverDamage:null};
      casters.set(id,state);
    }
    return state;
  };
  const watch=row=>{
    if (watchNodes.length===0) watchingDanger=true;
    else if (row.kind==="attack"&&watchNodes.includes(row.attackNodeId)) watchingDanger=true;
  };
  const fail=(where,error)=>{
    if (fault===null) fault=where+": "+(error&&error.stack?error.stack:String(error));
  };
  const log=row=>{
    if (!watchingDanger) { unwatchedLogs++;return; }
    if (logs<maxLogs) {
      logs++;
      emit({status:"original_threat_event",ordinal:logs,...row});
    } else droppedLogs++;
  };
  const dropPending=reason=>{
    if (pending===null) return;
    unlinkedCreates++;
    log({kind:"unlinked_create",reason,create:pending.row});
    pending=null;
  };
  const activeIds=()=>[...active.keys()].sort((a,b)=>a-b);
  const casterRows=()=>[...casters.values()].sort((a,b)=>a.casterId-b.casterId)
    .map(state=>({casterId:state.casterId,totalAttackCount:state.totalAttackCount,
      recentAttacks:[...state.recentAttacks],
      activeProjectileIds:[...state.activeProjectileIds].sort((a,b)=>a-b),
      activeProjectiles:[...state.activeProjectileIds].sort((a,b)=>a-b)
        .map(id=>({projectileId:id,source:active.get(id).source,
          spawnTick:active.get(id).tick})),
      latestAttack:state.latestAttack,latestCreate:state.latestCreate,
      latestSpawn:state.latestSpawn,latestDespawn:state.latestDespawn,
      latestDamage:state.latestDamage,latestCoverDamage:state.latestCoverDamage}));
  function observeSendEvent(event) {
    if (fault!==null||!live(event)) return;
    try {
      // Include unrelated event dispatches in the adjacency check. The original
      // Create handler may only be linked to its immediate nested Spawn.
      sequence++;
      const spec=expected.get(event.class.type.name);
      if (pending!==null && (!spec||spec.kind!=="spawn"))
        dropPending("intervening_dispatch_before_spawn");
      if (!spec) return;
      const eventId=numeric(event.field("<SpotEventID>k__BackingField").value);
      if (eventId!==spec.id) throw new Error("Original "+spec.kind+" event ID mismatch");
      const base={kind:spec.kind,sequence,eventId,...stamp()};
      if (spec.kind==="attack") {
        const casterId=casterIdFromInfo(event.field("CasterInfo").value,
          "attack caster");
        if (casterId===null) return;
        const row={...base,casterId,
          targetId:infoId(event.field("TargetInfo").value,"attack target"),
          attackNodeId:bounded(event.field("AttackNodeID").value,"attack node"),
          animationNumber:numeric(event.field("AniNumber").value)};
        const state=casterState(casterId);
        row.attackOrdinal=++state.totalAttackCount;
        state.latestAttack=row;
        state.recentAttacks.push(row);
        if (state.recentAttacks.length>historyLimit) {
          state.recentAttacks.shift();historyDropped++;
        }
        watch(row);
        counts.attack++;latest.attack=row;log(row);return;
      }
      if (spec.kind==="create") {
        const projectileData=event.field("Data").value;
        if (!live(projectileData)) throw new Error("Original ProjectileCreate has no Data");
        if (projectileData.class.type.name!==data.type.name)
          throw new Error("Original ProjectileCreate Data class changed");
        const ownerId=positive(projectileData.field("OwnerId").value,"create owner");
        if (!acceptCreateOwner(ownerId)) {unclassifiedCreates++;return;}
        const row={...base,ownerId,casterId:ownerId,
          targetId:signed(projectileData.field("TargetId").value,"create target"),
          skillId:bounded(projectileData.field("SkillId").value,"create skill"),
          isDestroyable:Boolean(projectileData.field("IsDestroyable").value),
          isCharacter:Boolean(event.field("IsCharacter").value)};
        casterState(ownerId).latestCreate=row;
        watch(row);
        counts.create++;latest.create=row;log(row);
        pending={sequence,row};return;
      }
      if (spec.kind==="spawn") {
        const casterId=casterIdFromInfo(event.field("CasterInfo").value,
          "spawn caster");
        if (casterId===null) {
          if (pending!==null) dropPending("spawn_caster_mismatch");
          return;
        }
        const projectileId=infoId(event.field("ProjectileInfo").value,"spawn projectile");
        if (projectileId===null) throw new Error("Boss ProjectileSpawn has no ProjectileInfo");
        if (active.has(projectileId)) throw new Error("Duplicate active boss projectile ID");
        if (active.size>=maxActive) throw new Error("Active boss projectiles exceed bound");
        let source=null;
        if (pending!==null && pending.sequence===sequence-1 &&
            pending.row.ownerId===casterId && pending.row.tick===base.tick) {
          source={skillId:pending.row.skillId,targetId:pending.row.targetId,
            createSequence:pending.sequence};
          linked++;
          pending=null;
        } else if (pending!==null) dropPending("spawn_not_adjacent_or_tick_mismatch");
        if (source===null) unknownSpawns++;
        const row={...base,casterId,projectileId,source,
          sourceBinding:source===null?"unknown":"immediate_original_create_spawn"};
        active.set(projectileId,row);
        const state=casterState(casterId);
        state.latestSpawn=row;
        state.activeProjectileIds.add(projectileId);
        watch(row);
        counts.spawn++;latest.spawn=row;log(row);return;
      }
      if (spec.kind==="despawn") {
        const projectileId=infoId(event.field("ProjectileInfo").value,"despawn projectile");
        if (projectileId===null) return;
        const prior=active.get(projectileId);
        if (!prior) { unmatchedDespawns++; return; }
        active.delete(projectileId);
        const row={...base,casterId:prior.casterId,projectileId,source:prior.source,
          despawnType:bounded(event.field("DespawnTypeEnum").value,"despawn type")};
        const state=casterState(prior.casterId);
        state.latestDespawn=row;
        state.activeProjectileIds.delete(projectileId);
        watch(row);
        counts.despawn++;latest.despawn=row;log(row);return;
      }
      const casterId=casterIdFromInfo(event.field("CasterInfo").value,
        "damage caster");
      if (casterId===null) return;
      if (spec.kind==="cover_damage") {
        const row={...base,casterId,coverId:infoId(event.field("CoverInfo").value,"cover damage"),
          damage:stat(event,"Damage")};
        casterState(casterId).latestCoverDamage=row;
        watch(row);
        counts.cover_damage++;latest.coverDamage=row;log(row);return;
      }
      const target=event.field("TargetInfo").value;
      if (!live(target)) throw new Error("Boss damage event has no target info");
      const targetType=numeric(target.field("ObjectType").value);
      if (targetType!==characterType && targetType!==coverType) return;
      const row={...base,casterId,targetId:infoId(target,"damage target"),
        targetType:targetType===coverType?"Cover":"Character",
        targetSubId:signed(event.field("TargetSubID").value,"target sub-ID"),
        damage:stat(event,"Damage"),actualDamage:stat(event,"ActualDamage"),
        damageType:numeric(event.field("DamageType").value),
        critical:Boolean(event.field("IsCritical").value),
        immune:Boolean(event.field("IsImmune").value),
        shared:Boolean(event.field("IsShare").value)};
      casterState(casterId).latestDamage=row;
      watch(row);
      counts.damage++;latest.damage=row;log(row);
    } catch(error) { fail("observeSendEvent",error); }
  }
  function snapshot(tick) {
    if (fault!==null) return {supported:false,fault};
    try {
      if (!Number.isSafeInteger(tick)||tick<0||tick<=lastSnapshotTick||
          tick!==Number(management.field("_tickCount").value))
        throw new Error("Threat snapshot requires one increasing original tick");
      lastSnapshotTick=tick;
      return {supported:true,tick,allBossActiveProjectileIds:activeIds(),
        activeBossProjectiles:activeIds().map(id=>({projectileId:id,
          source:active.get(id).source,spawnTick:active.get(id).tick})),
        casters:casterRows(),eventsTruncated:droppedLogs>0,
        attackHistoryTruncated:historyDropped>0,
        pendingUnlinkedCreate:pending!==null?pending.row:null,
        lastEventSequence:sequence,latestAttack:latest.attack,
        latestCreate:latest.create,latestSpawn:latest.spawn,
        latestDespawn:latest.despawn,latestBossDamage:latest.damage};
    } catch(error) {
      fail("snapshot",error);
      return {supported:false,fault};
    }
  }
  function summary() {
    return {status:"original_threat_summary",counts,totalDispatches:sequence,
      emitted:logs,emissionLimit:maxLogs,droppedLogs,
      watchesFromAttackNodes:watchNodes,
      watchMode:options.mode,verifiedBossIds:[...verifiedIds],
      watchedFromFirstTrackedEvent:watchNodes.length===0,unwatchedLogs,
      transitionsTruncated:droppedLogs>0,
      historyLimit,historyDropped,attackHistoryTruncated:historyDropped>0,
      casterLimit:maxCasters,unclassifiedCreates,casters:casterRows(),
      linked,unlinkedCreates,unknownSpawns,unmatchedDespawns,
      allBossActiveProjectileIds:activeIds(),pendingUnlinkedCreate:pending?.row||null,
      latest,lastSnapshotTick,fault};
  }
  function checkFault() { if (fault!==null) throw new Error(fault); }
  emit({status:"original_threat_observer_ready",installsHooks:false,
    readsOnly:true,sourceBinding:"immediate_original_create_spawn_only"});
  return {observeSendEvent,snapshot,checkFault,summary};
}
