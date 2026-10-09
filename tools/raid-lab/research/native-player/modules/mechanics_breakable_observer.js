// Installed client 2df7134a: passive, non-QTE SpotMonsterBreak observation.
// Call on the Unity main thread. No hooks, input, RNG draws or state writes.
// The small ledger is exported for synthetic lifecycle tests; native evidence
// still requires the private original-player run.
function createBreakableEpisodeLedger(limit=64) {
  if (!Number.isSafeInteger(limit) || limit<1 || limit>256) throw new Error("Invalid break ledger limit");
  const episodes=new Map(), counts=new Map();
  let sequence=0;
  function observe(row) {
    if (!row || !Number.isSafeInteger(row.ownerId) || row.ownerId<0 ||
        !Number.isSafeInteger(row.tick) || row.tick<0 || typeof row.kind!=="string")
      throw new Error("Invalid original break event row");
    sequence++;
    counts.set(row.kind,(counts.get(row.kind)||0)+1);
    const previous=episodes.get(row.ownerId);
    const episode=(row.kind==="MonsterBreakColliderActiveStart" || !previous) ?
      {ownerId:row.ownerId,startSequence:sequence,startTick:row.tick,
        started:false,terminal:null,lastEvent:null,eventCount:0} : {...previous};
    if (row.kind==="MonsterBreakColliderActiveStarted") episode.started=true;
    if (row.kind==="MonsterAllBreakCollider")
      episode.terminal={kind:row.kind,tick:row.tick,isBreak:row.isBreak,
        lastBrokenColliderId:row.lastBrokenColliderId};
    episode.lastEvent={...row,sequence};
    episode.eventCount++;
    // A bounded summary does not erase the native event counter or imply that
    // evicted episodes were completed.
    if (!episodes.has(row.ownerId) && episodes.size>=limit)
      episodes.delete(episodes.keys().next().value);
    episodes.set(row.ownerId,episode);
    return episode;
  }
  return {observe,summary:()=>({eventCount:sequence,
    counts:Object.fromEntries(counts),episodes:[...episodes.values()].map(e=>({...e}))})};
}

function createMechanicsBreakableObserver(runtime,management,pin,emit) {
  if (!runtime || !management || management.isNull() ||
      typeof pin!=="function" || typeof emit!=="function" ||
      typeof invokeChecked!=="function" || typeof intArg!=="function")
    throw new Error("Break observer needs live management and bridge helpers");
  const game=Process.getModuleByName("GameAssembly.dll");
  const at=(method,rva,label)=>{
    if (!method.virtualAddress.equals(game.base.add(rva)))
      throw new Error("Installed break method changed: "+label);
    return method;
  };
  const call=(method,self=null,args=[])=>invokeChecked(method,self,args);
  const live=value=>value!=null && !value.isNull();
  const checkField=(klass,name,offset)=>{
    if (klass.field(name).offset!==offset)
      throw new Error("Installed break field changed: "+klass.name+"."+name);
  };
  const enumInt=value=>typeof value==="number" ? value :
    Number(value.field("value__").value);
  const intResult=(method,self=null,args=[])=>
    call(method,self,args).unbox().handle.readS32();
  const boolResult=(method,self=null,args=[])=>
    call(method,self,args).unbox().handle.readU8()!==0;
  const statResult=(method,self)=>
    call(method,self).unbox().handle.readS64().toString();
  const bound=(value,max,label)=>{
    const n=Number(value);
    if (!Number.isSafeInteger(n) || n<0 || n>max)
      throw new Error("Original "+label+" outside bound: "+value);
    return n;
  };
  const unsupported=reason=>({supported:false,reason});
  const unity=Il2Cpp.domain.assembly("UnityEngine.CoreModule").image;
  const physics=Il2Cpp.domain.assembly("UnityEngine.PhysicsModule").image;
  const uObject=unity.class("UnityEngine.Object");
  const component=unity.class("UnityEngine.Component");
  const transform=unity.class("UnityEngine.Transform");
  const bounds=unity.class("UnityEngine.Bounds");
  const collider=physics.class("UnityEngine.Collider");
  const valid=at(uObject.method("op_Implicit",1),0x08269CB0,"Object.op_Implicit");
  const getName=at(uObject.method("get_name",0),0x08269AD0,"Object.get_name");
  const getTransform=at(component.method("get_transform",0),0x08263110,"Component.get_transform");
  const getPosition=at(transform.method("get_position",0),0x0827A100,"Transform.get_position");
  const getEnabled=at(collider.method("get_enabled",0),0x082D6B80,"Collider.get_enabled");
  const getBounds=at(collider.method("get_bounds",0),0x082D6AE0,"Collider.get_bounds");
  const getCenter=at(bounds.method("get_center",0),0x081F51B0,"Bounds.get_center");
  const unityValid=value=>live(value)&&boolResult(valid,null,[value.handle]);
  const vec3=value=>{
    const p=value.unbox().handle;
    const out=[p.readFloat(),p.add(4).readFloat(),p.add(8).readFloat()];
    if (!out.every(Number.isFinite)) throw new Error("Original break position is non-finite");
    return out;
  };
  const runtimeClass=name=>runtime.class("NK.Spot."+name);
  const monsterContext=runtimeClass("Context.Monster.MonsterContext");
  const monster=runtimeClass("Model.Monster.SpotMonster");
  const breakState=runtimeClass("Model.Monster.SpotMonsterBreak");
  const breakData=runtimeClass("Model.Monster.SpotMonsterBreakData");
  const colliderData=runtimeClass("Monster.Body.MonsterColliderData");
  const monsterData=runtimeClass("Monster.Model.MonsterData");
  const entityInfo=runtimeClass("Logic.Character.SpotEntityInfo");
  const eventBase=runtimeClass("Common.SpotEvent");
  const eventIds=eventBase.nested("SpotEventType");
  const monsterStatic=Il2Cpp.domain.assembly("NK.Runtime.StaticData").image
    .class("NK.StaticData.StaticDataLayer.StaticInfo.MonsterStaticInfo");
  for (const [klass,name,offset] of [
    [management.class,"_contexts",0x20],[management.class,"_tickCount",0x64],
    [management.class,"_playtime",0x6C],[monsterContext,"_monsters",0x10],
    [monster,"Id",0x10],[monster,"<BreakData>k__BackingField",0xB0],
    [monster,"<Data>k__BackingField",0x88],
    [monsterData,"<MonsterStaticInfo>k__BackingField",0x18],
    [monsterStatic,"<TableId>k__BackingField",0x10],
    [breakState,"_colliderDatas",0x10],[breakState,"<IsPlaying>k__BackingField",0x2D],
    [breakData,"<ColliderData>k__BackingField",0x10],
    [colliderData,"ColType",0x10],[colliderData,"Collider",0x18],
    [colliderData,"colliderId",0x20],[entityInfo,"EntityID",0x10],
    [eventBase,"<SpotEventID>k__BackingField",0x14]
  ]) checkField(klass,name,offset);
  const currentHp=at(breakData.method("get_CurrentHp",0),0x008C88E0,"BreakData.CurrentHp");
  const maxHp=at(breakData.method("get_MaxHp",0),0x008A4D20,"BreakData.MaxHp");
  const isAllBreak=at(breakState.method("IsAllBreak",0),0x0638DFB0,"Break.IsAllBreak");
  const isPlaying=at(breakState.method("get_IsPlaying",0),0x03B566B0,"Break.IsPlaying");
  const colliderTypes=colliderData.nested("ColliderType");
  const types=new Map();
  for (const name of ["None","Normal","Core","Break","Counter","Choice"]) {
    const n=enumInt(colliderTypes.field(name).value);
    if (types.has(n)) throw new Error("Original break collider enum duplicated");
    types.set(n,name);
  }
  if (enumInt(colliderTypes.field("Break").value)!==3)
    throw new Error("Installed break collider type changed");
  const contexts=management.field("_contexts").value;
  if (!live(contexts)) throw new Error("Original management contexts missing");
  const context=pin(call(contexts.method("get_Item",1),contexts,
    [monsterContext.type.object.handle]));
  if (!live(context)) throw new Error("Original MonsterContext missing");
  const list=(value,max,label)=>{
    if (!live(value)) throw new Error("Original "+label+" list missing");
    const count=bound(intResult(value.method("get_Count",0),value),max,label+" count");
    const out=[];
    for (let i=0;i<count;i++) out.push(call(value.method("get_Item",1),value,[intArg(i)]));
    return out;
  };
  const activeMonsters=()=>list(context.field("_monsters").value,32,"monster");
  const nativeTick=()=>bound(management.field("_tickCount").value,10000000,"tick");
  const nativePlaytime=()=>{
    const n=Number(management.field("_playtime").value);
    if (!Number.isFinite(n)) throw new Error("Original playtime non-finite");
    return n;
  };
  const eventSpecs=[
    ["NK.Spot.Event.Monster.MonsterBreakColliderActiveStartEvent","MonsterBreakColliderActiveStart","EntityInfo",[["EntityInfo",0x40],["BreakColliders",0x48],["CastingTime",0x5C],["EndAtRemainCount",0x60]]],
    ["NK.Spot.Event.Monster.MonsterBreakColliderActiveStartedEvent","MonsterBreakColliderActiveStarted","EntityInfo",[["EntityInfo",0x40],["ColliderDatas",0x48]]],
    ["NK.Spot.Event.Monster.MonsterBreakColliderHurtEvent","MonsterBreakColliderHurt","EntityInfo",[["EntityInfo",0x40],["ColliderId",0x48],["Damage",0x50]]],
    ["NK.Spot.Event.Monster.MonsterInActiveBreakColliderEvent","MonsterInActiveBreakCollider","EntityInfo",[["EntityInfo",0x40],["ColliderId",0x48]]],
    ["NK.Spot.Event.Monster.MonsterAllBreakColliderEvent","MonsterAllBreakCollider","EntityInfo",[["EntityInfo",0x40],["MonsterSkill",0x48],["IsBreak",0x50],["LastBrokenColliderId",0x54]]],
    ["NK.Spot.Event.Monster.MonsterSkillInterruptionEvent","MonsterSkillInterruptionEvent","EntityInfo",[["EntityInfo",0x40],["MonsterSkill",0x48],["IsInterrupt",0x50]]]
  ];
  const specs=new Map();
  for (const [className,kind,ownerField,fields] of eventSpecs) {
    const klass=runtime.class(className);
    for (const [name,offset] of fields) checkField(klass,name,offset);
    specs.set(className,{kind,id:enumInt(eventIds.field(kind).value),ownerField});
  }
  at(management.method("SendEventDefault",1),0x0614BAF0,"SendEventDefault");
  const ledger=createBreakableEpisodeLedger();
  const maxEventLogs=512;
  let fault=null,lastSnapshotTick=-1,emitted=0,totalSnapshots=0;
  const latch=(where,error)=>{
    if (fault===null) fault=where+": "+(error&&error.stack?error.stack:String(error));
  };
  function observeSendEvent(event) {
    if (fault!==null || !live(event)) return;
    const spec=specs.get(event.class.type.name);
    if (!spec) return;
    try {
      if (enumInt(event.field("<SpotEventID>k__BackingField").value)!==spec.id)
        throw new Error("Original break event class/ID mismatch");
      const info=event.field(spec.ownerField).value;
      if (!live(info) || info.class.type.name!==entityInfo.type.name)
        throw new Error("Original break event owner missing or changed");
      const row={kind:spec.kind,ownerId:bound(info.field("EntityID").value,1000000,"ownerId"),
        tick:nativeTick(),nativePlaytime:nativePlaytime()};
      if (spec.kind==="MonsterBreakColliderActiveStart") {
        row.castingNativeTime=Number(event.field("CastingTime").value);
        row.endAtRemainCount=Number(event.field("EndAtRemainCount").value);
        row.colliderNames=unsupported("event_string_array_not_decoded; use live BreakData snapshot");
      } else if (spec.kind==="MonsterBreakColliderHurt") {
        row.colliderId=Number(event.field("ColliderId").value);
        row.damage=event.field("Damage").value.toString();
      } else if (spec.kind==="MonsterInActiveBreakCollider")
        row.colliderId=Number(event.field("ColliderId").value);
      else if (spec.kind==="MonsterAllBreakCollider") {
        row.isBreak=Boolean(event.field("IsBreak").value);
        row.lastBrokenColliderId=Number(event.field("LastBrokenColliderId").value);
      } else if (spec.kind==="MonsterSkillInterruptionEvent")
        row.isInterrupt=Boolean(event.field("IsInterrupt").value);
      ledger.observe(row);
      if (emitted<maxEventLogs) emit({status:"original_break_transition",sequence:++emitted,...row});
    } catch(error) { latch("observeSendEvent",error); }
  }
  const monsterSnapshot=value=>{
    if (!live(value) || value.class.type.name!==monster.type.name)
      throw new Error("Original monster type changed");
    const entityId=bound(value.field("Id").value,1000000,"monster entityId");
    const data=value.field("<Data>k__BackingField").value;
    if (!live(data)) return {supported:false,entityId,reason:"monster_data_missing"};
    const info=data.field("<MonsterStaticInfo>k__BackingField").value;
    if (!live(info)) return {supported:false,entityId,reason:"monster_static_info_missing"};
    const tableId=info.field("<TableId>k__BackingField").value.toString();
    const state=value.field("<BreakData>k__BackingField").value;
    if (!live(state)) return {supported:false,entityId,tableId,reason:"break_data_missing"};
    const playing=boolResult(isPlaying,state);
    const items=list(state.field("_colliderDatas").value,32,"break collider");
    const colliders=[];
    for (const item of items) {
      if (!live(item) || item.class.type.name!==breakData.type.name)
        throw new Error("Original SpotMonsterBreakData type changed");
      const source=item.field("<ColliderData>k__BackingField").value;
      if (!live(source) || source.class.type.name!==colliderData.type.name)
        throw new Error("Original MonsterColliderData missing or changed");
      const typeId=enumInt(source.field("ColType").value);
      const unityCollider=source.field("Collider").value;
      const hp=statResult(currentHp,item),maximum=statResult(maxHp,item);
      const row={colliderId:bound(source.field("colliderId").value,1000000,"colliderId"),
        type:{value:typeId,name:types.get(typeId)||null},hp,maxHp:maximum,
        unityLive:unityValid(unityCollider),enabled:false,name:null,
        worldAimPoint:null,aimPointBasis:"UnityEngine.Collider.bounds.center",
        transformPosition:null};
      if (row.unityLive) {
        row.enabled=boolResult(getEnabled,unityCollider);
        const name=call(getName,unityCollider);
        row.name=live(name)?new Il2Cpp.String(name.handle).content:null;
        if (row.enabled && playing && row.type.name==="Break" && BigInt(hp)>0n) {
          row.worldAimPoint=vec3(call(getCenter,call(getBounds,unityCollider).unbox()));
          const tr=call(getTransform,unityCollider);
          if (unityValid(tr)) row.transformPosition=vec3(call(getPosition,tr));
        }
      }
      // Original IsAllBreak tests type plus HP. Geometry and collider-enabled
      // status are separate live observations, not synthetic health state.
      row.liveBreakTarget=playing && row.type.name==="Break" &&
        row.unityLive && row.enabled && BigInt(hp)>0n &&
        Array.isArray(row.worldAimPoint);
      colliders.push(row);
    }
    colliders.sort((a,b)=>a.colliderId-b.colliderId);
    return {supported:true,entityId,tableId,playing,
      nativeIsAllBreak:boolResult(isAllBreak,state),colliders};
  };
  function snapshot(tick) {
    if (fault!==null) return {status:"original_break_snapshot",supported:false,fault};
    try {
      if (!Number.isSafeInteger(tick) || tick<=lastSnapshotTick || tick!==nativeTick())
        throw new Error("Break snapshot needs one increasing original tick");
      lastSnapshotTick=tick;
      totalSnapshots++;
      const monsters=activeMonsters().map(monsterSnapshot);
      return {status:"original_break_snapshot",supported:true,tick,
        nativePlaytime:nativePlaytime(),monsters,
        // Skill 520676 is a table candidate only. Event data alone does not
        // establish which active break session belongs to that skill.
        latestEpisodes:ledger.summary().episodes};
    } catch(error) { latch("snapshot",error); return {status:"original_break_snapshot",supported:false,fault}; }
  }
  function summary() {
    const retained=ledger.summary();
    return {status:"original_break_observer_summary",totalEvents:retained.eventCount,
      counts:retained.counts,latestEpisodes:retained.episodes,
      emittedEvents:emitted,eventEmissionLimit:maxEventLogs,
      eventTransitionsTruncated:retained.eventCount>maxEventLogs,
      totalSnapshots,lastSnapshotTick,fault};
  }
  function checkFault() { if (fault!==null) throw new Error(fault); }
  emit({status:"original_break_observer_ready",installsHooks:false,readsOnly:true,
    source:"SpotMonster.BreakData/SpotMonsterBreak._colliderDatas",
    installedDllSha256:"2df7134a6a9c3a8dbbde88402fc8d16d1d6c3f4c2d5e262bea78c3d78b96dd02"});
  return {observeSendEvent,snapshot,summary,checkFault};
}
