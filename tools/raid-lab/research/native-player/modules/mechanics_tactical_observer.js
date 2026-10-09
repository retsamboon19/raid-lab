// Read-only original tactical state. Extended identity is opt-in so retained
// Kraken evidence keeps its original observation contract.
// Call on Unity main thread. The caller forwards its existing SendEventDefault
// event and samples after each original UpdateSpot tick. No hooks or actions.
function createMechanicsTacticalObserver(runtime, management, team, pin, emit, extended=false) {
  if (!runtime || !management || management.isNull() || !team || team.isNull() ||
      typeof pin !== "function" || typeof emit !== "function" ||
      typeof invokeChecked !== "function" || typeof intArg !== "function")
    throw new Error("Original tactical observer needs live management/team and bridge helpers");
  const game = Process.getModuleByName("GameAssembly.dll");
  const at = (method,rva,label) => {
    if (!method.virtualAddress.equals(game.base.add(rva)))
      throw new Error("Installed tactical method changed: " + label);
    return method;
  };
  const call = (method,self=null,args=[]) => invokeChecked(method,self,args);
  const live = value => value != null && !value.isNull();
  const number = value => typeof value === "number" || typeof value === "boolean" ?
    Number(value) : Number(value.field("value__").value);
  const boundedInt = (value,limit,label) => {
    const n=Number(value);
    if (!Number.isSafeInteger(n) || n<0 || n>limit)
      throw new Error("Original tactical " + label + " outside bound: " + value);
    return n;
  };
  const field = (klass,name,offset) => {
    if (klass.field(name).offset !== offset)
      throw new Error("Installed tactical field changed: " + klass.name + "." + name);
  };
  const intResult=(method,self=null,args=[]) =>
    call(method,self,args).unbox().handle.readS32();
  const boolResult=(method,self=null,args=[]) =>
    call(method,self,args).unbox().handle.readU8()!==0;
  const i64Result=(method,self=null,args=[]) =>
    call(method,self,args).unbox().handle.readS64().toString();
  const finite=value=>{
    const n=Number(value);
    if (!Number.isFinite(n)) throw new Error("Original tactical non-finite float");
    return n;
  };
  const unsupported=(reason)=>({supported:false,reason});
  const enumMap=(klass,names)=>{
    const map=new Map();
    for (const name of names) {
      const id=number(klass.field(name).value);
      if (!Number.isSafeInteger(id) || map.has(id))
        throw new Error("Installed tactical enum changed: " + klass.name + "." + name);
      map.set(id,name);
    }
    return map;
  };
  const enumValue=(map,value)=>{
    const id=number(value);
    return {value:id,name:map.get(id)||null};
  };
  const unity=Il2Cpp.domain.assembly("UnityEngine.CoreModule").image;
  const unityObject=unity.class("UnityEngine.Object");
  const component=unity.class("UnityEngine.Component");
  const transform=unity.class("UnityEngine.Transform");
  const valid=at(unityObject.method("op_Implicit",1),0x08269CB0,
    "UnityEngine.Object.op_Implicit");
  const getTransform=at(component.method("get_transform",0),0x08263110,
    "Component.get_transform");
  const getPosition=at(transform.method("get_position",0),0x0827A100,
    "Transform.get_position");
  const unityValid=value=>live(value)&&boolResult(valid,null,[value.handle]);
  const position=object=>{
    if (!unityValid(object)) return unsupported("missing_live_unity_transform");
    const ptr=call(getPosition,object).unbox().handle;
    const xyz=[ptr.readFloat(),ptr.add(4).readFloat(),ptr.add(8).readFloat()];
    if (!xyz.every(Number.isFinite)) throw new Error("Original tactical position non-finite");
    return xyz;
  };
  const collider=Il2Cpp.domain.assembly("UnityEngine.PhysicsModule").image
    .class("UnityEngine.Collider");
  const colliderEnabled=at(collider.method("get_enabled",0),0x082D6B80,
    "Collider.get_enabled");
  const entity=runtime.class("NK.Spot.Model.Common.SpotEntity");
  const status=runtime.class("NK.Spot.Model.Common.SpotEntityStatus");
  const character=runtime.class("NK.Spot.Model.Character.SpotCharacter");
  const cover=runtime.class("NK.Spot.Model.Character.SpotCharacterCover");
  const monster=runtime.class("NK.Spot.Model.Monster.SpotMonster");
  const parts=runtime.class("NK.Spot.Model.Monster.SpotMonsterPartsData").nested("PartsData");
  const qteContextClass=runtime.class("NK.Spot.Context.QuickTimeEventContext");
  const monsterContextClass=runtime.class("NK.Spot.Context.Monster.MonsterContext");
  const presetClass=runtime.class("NK.Spot.Model.QuickTimeEvent.SpotQuickTimePreset");
  const qteColliderClass=runtime.class("NK.Spot.Model.QuickTimeEvent.SpotQuickTimeCollider");
  const entityInfo=runtime.class("NK.Spot.Logic.Character.SpotEntityInfo");
  const eventBase=runtime.class("NK.Spot.Common.SpotEvent");
  const eventIds=eventBase.nested("SpotEventType");
  const monsterData=runtime.class("NK.Spot.Monster.Model.MonsterData");
  const monsterCondition=runtime.class("NK.Spot.Model.Monster.SpotMonsterCondition");
  const monsterStatic=Il2Cpp.domain.assembly("NK.Runtime.StaticData").image
    .class("NK.StaticData.StaticDataLayer.StaticInfo.MonsterStaticInfo");
  if (extended) for (const [klass,name,offset] of [
    [monsterContextClass,"_monsters",0x10],
    [monster,"<Data>k__BackingField",0x88],
    [monster,"<Condition>k__BackingField",0x70],
    [monsterData,"<MonsterStaticInfo>k__BackingField",0x18],
    [monsterStatic,"<TableId>k__BackingField",0x10],
    [monsterCondition,"<CurrentConditionType>k__BackingField",0x10]
  ]) field(klass,name,offset);
  for (const [klass,name,offset] of [
    [management.class,"_contexts",0x20],[management.class,"_tickCount",0x64],
    [management.class,"_playtime",0x6C],
    [team.class,"_focusedCharacter",0x20],
    [team.class,"<CharacterList>k__BackingField",0x38],
    [character,"<Cover>k__BackingField",0xF8],
    [entity,"Id",0x10],[entity,"<CurrentStatus>k__BackingField",0x30],
    [entityInfo,"EntityID",0x10],[eventBase,"<SpotEventID>k__BackingField",0x14],
    [monsterContextClass,"_targetMonster",0x38],
    [monsterContextClass,"_allMonsterParts",0x28],
    [monster,"<PartsData>k__BackingField",0x90],
    [parts,"PartsType",0x18],[parts,"<HitPoint>k__BackingField",0x20],
    [parts,"<Owner>k__BackingField",0x30],
    [parts,"<IsDestroyed>k__BackingField",0x3C],
    [qteContextClass,"<IsQuickTime>k__BackingField",0x39],
    [qteContextClass,"_currentTime",0x30],
    [qteContextClass,"_currentIndex",0x24],
    [qteContextClass,"<CurrentPreset>k__BackingField",0x40],
    [presetClass,"_colliders",0x68],
    [presetClass,"<GroupId>k__BackingField",0x90],
    [presetClass,"<CurrentOrder>k__BackingField",0x94],
    [presetClass,"<IsPlaying>k__BackingField",0x98],
    [qteColliderClass,"<ColliderId>k__BackingField",0x70],
    [qteColliderClass,"<Collider>k__BackingField",0x78],
    [qteColliderClass,"<ColType>k__BackingField",0x8C],
    [qteColliderClass,"_currentState",0xA4],
    [qteColliderClass,"_remainTime",0xA8]
  ]) field(klass,name,offset);
  const getHp=at(status.method("get_HP",0),0x0638B4C0,"Status.HP");
  const getMaxHp=at(status.method("get_MaxHP",0),0x0638B880,"Status.MaxHP");
  const getPartHp=at(parts.method("get_CurrentHp",0),0x06380910,"PartsData.CurrentHp");
  const getPartMaxHp=at(parts.method("get_MaxHp",0),0x06380A30,"PartsData.MaxHp");
  const partActive=at(parts.method("get_IsActive",0),0x063809F0,"PartsData.IsActive");
  const qteOrder=at(qteColliderClass.method("get_Order",0),0x06375950,
    "SpotQuickTimeCollider.Order");
  const qteSuccess=at(presetClass.method("IsSuccess",0),0x06375ED0,"SpotQuickTimePreset.IsSuccess");
  const weapon=runtime.class("NK.Spot.Model.Character.Weapon.SpotWeaponData");
  const getWeaponType=at(weapon.method("get_WeaponType",0),0x063B7740,"Weapon.WeaponType");
  const getAmmo=at(weapon.method("get_CurrentAmmo",0),0x063B5D20,"Weapon.CurrentAmmo");
  const weaponTypes=enumMap(Il2Cpp.domain.assembly("NK.Runtime.StaticData").image
    .class("NK.StaticData.WeaponType"),["None","AR","RL","SR","MG","SG","AS","GL","PS","SMG"]);
  const colType=enumMap(Il2Cpp.domain.assembly("NK.Runtime.StaticData").image
    .class("NK.StaticData.ColType"),["None","Break","Counter","Choice"]);
  const colState=enumMap(qteColliderClass.nested("ColliderState"),
    ["Enable","StartDelay","WaitConnect","Disable"]);
  const contexts=management.field("_contexts").value;
  if (!live(contexts)) throw new Error("Original management contexts missing");
  const contextFor=klass=>pin(call(contexts.method("get_Item",1),contexts,
    [klass.type.object.handle]));
  let qte=null, qteContextProblem=null;
  try { qte=contextFor(qteContextClass); }
  catch(error) { qteContextProblem=String(error); }
  const monsterContext=contextFor(monsterContextClass);
  if (!live(monsterContext)) throw new Error("Original MonsterContext missing");
  const hpOf=value=>{
    if (!live(value)) return unsupported("entity_missing");
    const current=value.field("<CurrentStatus>k__BackingField").value;
    if (!live(current)) return unsupported("current_status_missing");
    return {hp:i64Result(getHp,current),maxHp:i64Result(getMaxHp,current)};
  };
  const listCount=value=>boundedInt(intResult(value.method("get_Count",0),value),32,
    "list count");
  const listItems=(value,limit)=>{
    if (!live(value)) return [];
    const count=listCount(value);
    if (count>limit) throw new Error("Original tactical list limit exceeded");
    const rows=[];
    for (let i=0;i<count;i++) rows.push(call(value.method("get_Item",1),value,[intArg(i)]));
    return rows;
  };
  const dictionaryValues=(value,limit)=>{
    if (!live(value)) return unsupported("dictionary_missing");
    const count=boundedInt(intResult(value.method("get_Count",0),value),limit,
      "dictionary count");
    const values=call(value.method("get_Values",0),value);
    if (!live(values)) return unsupported("dictionary_values_missing");
    const iterator=call(values.method("GetEnumerator",0),values);
    if (!live(iterator)) return unsupported("dictionary_iterator_missing");
    const result=[];
    for (let i=0;i<=count;i++) {
      const cursor=iterator.unbox();
      if (!boolResult(cursor.method("MoveNext",0),cursor)) break;
      if (i===count) throw new Error("Original tactical dictionary enumeration exceeds Count");
      result.push(call(cursor.method("get_Current",0),cursor));
    }
    if (result.length!==count) throw new Error("Original tactical dictionary count mismatch");
    return result;
  };
  const qteTargets=()=>{
    if (!live(qte)) return unsupported("QuickTimeEventContext_missing: "+
      (qteContextProblem||"not_registered"));
    const active=Boolean(qte.field("<IsQuickTime>k__BackingField").value);
    if (!active) return {supported:true,active:false,targets:[]};
    const preset=qte.field("<CurrentPreset>k__BackingField").value;
    if (!live(preset)) return unsupported("active_QTE_has_no_current_preset");
    const members=dictionaryValues(preset.field("_colliders").value,32);
    if (!Array.isArray(members)) return members;
    const targets=[];
    for (const value of members) {
      if (!live(value) || value.class.type.name!==qteColliderClass.type.name)
        throw new Error("Original QTE dictionary value type changed");
      const nativeCollider=value.field("<Collider>k__BackingField").value;
      if (!unityValid(nativeCollider)) continue;
      const enabled=boolResult(colliderEnabled,nativeCollider);
      if (!enabled) continue;
      const world=call(getTransform,nativeCollider);
      const originalHp=hpOf(value);
      const worldPosition=position(world);
      if (!Array.isArray(worldPosition) || originalHp.supported===false)
        return unsupported("active_QTE_target_missing_live_position_or_health");
      targets.push({id:Number(value.field("<ColliderId>k__BackingField").value),
        entityId:Number(value.field("Id").value),
        state:enumValue(colState,value.field("_currentState").value),
        colType:enumValue(colType,value.field("<ColType>k__BackingField").value),
        order:intResult(qteOrder,value),
        remainingNativeTime:finite(value.field("_remainTime").value),
        worldPosition,health:originalHp});
    }
    targets.sort((a,b)=>a.id-b.id);
    return {supported:true,active:true,
      ...(extended?{presetEntityId:Number(preset.field("Id").value)}:{}),
      groupId:Number(preset.field("<GroupId>k__BackingField").value),
      currentOrder:Number(preset.field("<CurrentOrder>k__BackingField").value),
      currentNativeTime:finite(qte.field("_currentTime").value),
      currentIndex:Number(qte.field("_currentIndex").value),
      nativePresetSuccess:boolResult(qteSuccess,preset),targets};
  };
  const monsterParts=()=>{
    const target=monsterContext.field("_targetMonster").value;
    if (!live(target)) return {supported:true,targetMonsterId:null,parts:[]};
    const members=listItems(monsterContext.field("_allMonsterParts").value,32);
    const out=[];
    for (const item of members) {
      if (!live(item) || item.class.type.name!==parts.type.name)
        throw new Error("Original monster part type changed");
      const owner=item.field("<Owner>k__BackingField").value;
      if (!live(owner) || !owner.handle.equals(target.handle)) continue;
      if (Boolean(item.field("<IsDestroyed>k__BackingField").value) ||
          !boolResult(partActive,item)) continue;
      const hitPoint=item.field("<HitPoint>k__BackingField").value;
      const worldPosition=position(hitPoint);
      if (!Array.isArray(worldPosition))
        return unsupported("active_monster_part_missing_live_hit_point");
      out.push({partsType:number(item.field("PartsType").value),
        worldPosition,
        hp:i64Result(getPartHp,item),maxHp:i64Result(getPartMaxHp,item)});
    }
    out.sort((a,b)=>a.partsType-b.partsType);
    return {supported:true,targetMonsterId:Number(target.field("Id").value),parts:out};
  };
  const monsterIdentities=()=>listItems(monsterContext.field("_monsters").value,32)
    .map(value=>{
      if (!live(value)||value.class.type.name!==monster.type.name)
        throw new Error("Original monster identity type changed");
      const data=value.field("<Data>k__BackingField").value;
      const condition=value.field("<Condition>k__BackingField").value;
      if (!live(data)||!live(condition)) throw new Error("Original monster data/condition missing");
      const info=data.field("<MonsterStaticInfo>k__BackingField").value;
      if (!live(info)) throw new Error("Original monster static identity missing");
      return {entityId:Number(value.field("Id").value),
        tableId:info.field("<TableId>k__BackingField").value.toString(),
        condition:enumValue(conditionMap,condition.field("<CurrentConditionType>k__BackingField").value)};
    });
  const squad=()=>{
    const focused=team.field("_focusedCharacter").value;
    const members=listItems(team.field("<CharacterList>k__BackingField").value,5);
    const characters=[];
    for (const item of members) {
      if (!live(item) || item.class.type.name!==character.type.name)
        throw new Error("Original team character type changed");
      const itemCover=item.field("<Cover>k__BackingField").value;
      const health=hpOf(item);
      const coverHealth=live(itemCover)?hpOf(itemCover):null;
      if (health.supported===false || coverHealth && coverHealth.supported===false)
        return unsupported("team_character_or_cover_health_missing");
      const currentWeapon=item.field("<CurrentWeaponData>k__BackingField").value;
      if (!live(currentWeapon)) return unsupported("team_character_weapon_missing");
      const weaponType=intResult(getWeaponType,currentWeapon);
      characters.push({id:Number(item.field("Id").value),health,
        weapon:{type:{value:weaponType,name:weaponTypes.get(weaponType)||null},
          ammo:i64Result(getAmmo,currentWeapon)},
        cover:live(itemCover) ? {id:Number(itemCover.field("Id").value),
          health:coverHealth} : null});
    }
    return {supported:true,focusId:live(focused)?Number(focused.field("Id").value):null,
      characters};
  };
  const specs=[
    ["NK.Spot.Event.QuickTime.QuickTimeStartEvent","QuickTimeStart",[["MonsterInfo",0x40],["QuickTimeId",0x48]]],
    ["NK.Spot.Event.QuickTime.QuickTimePresetStartEvent","QuickTimePresetStart",[["MonsterInfo",0x40],["Index",0x48],["IsStart",0x4C]]],
    ["NK.Spot.Event.QuickTime.QuickTimeColliderEnabledEvent","QuickTimeColliderEnabled",[["EntityInfo",0x40],["Enabled",0x48]]],
    ["NK.Spot.Event.QuickTime.QuickTimeColliderHitEvent","QuickTimeColliderHit",[["EntityInfo",0x40]]],
    ["NK.Spot.Event.QuickTime.QuickTimeEndEvent","QuickTimeEnd",[["Success",0x40]]],
    ["NK.Spot.Event.QuickTime.QuickTimePresetEndEvent","QuickTimePresetEnd",[["PresetInfo",0x40],["Success",0x48],["End",0x49]]],
    ["NK.Spot.Event.Monster.MonsterBreakableTimeStartEvent","MonsterBreakableTimeStart",[["MonsterInfo",0x40],["BreakableTime",0x48],["TargetCount",0x4C]]],
    ["NK.Spot.Event.Monster.MonsterBreakableProgressEvent","MonsterBreakableProgress",[["MonsterInfo",0x40],["RemainValue",0x48]]],
    ["NK.Spot.Event.Monster.MonsterBreakableTimeEndEvent","MonsterBreakableTimeEnd",[["MonsterInfo",0x40],["Reason",0x48]]],
    ["NK.Spot.Event.Monster.MonsterBreakColliderActiveStartEvent","MonsterBreakColliderActiveStart",[["EntityInfo",0x40],["CastingTime",0x5C],["EndAtRemainCount",0x60]]],
    ["NK.Spot.Event.Monster.MonsterAttackEvent","MonsterAttack",[["CasterInfo",0x40],["TargetInfo",0x48],["AttackNodeID",0x64],["AniNumber",0x5C]]],
    ["NK.Spot.Event.Monster.MonsterChoiceSkillEvent","MonsterSelectChoiceSkill",[["CasterInfo",0x40],["EndAtRemainCount",0x48],["DurationTime",0x4C]]],
    ["NK.Spot.Event.Monster.MonsterConditionEvent","MonsterCondition",[["MonsterInfo",0x40],["CurrentCondition",0x48]]]
  ];
  const expected=new Map();
  for (const [className,enumName,fields] of specs) {
    const klass=runtime.class(className);
    for (const [name,offset] of fields) field(klass,name,offset);
    expected.set(className,{id:number(eventIds.field(enumName).value),enumName,
      fieldNames:new Set(fields.map(([name])=>name))});
  }
  at(management.method("SendEventDefault",1),0x0614BAF0,"SendEventDefault");
  const conditionMap=enumMap(runtime.class("NK.Spot.Model.Monster.MonsterConditionType"),
    ["None","Idle","WaitMove","Move","Dead","JumpReady","Jump","JumpEnd",
      "Stun","FireCasting","Fire","FireEnd","Suicide","Teleport","DashReady",
      "Dash","DashEnd"]);
  const endReasonMap=enumMap(runtime.class(
    "NK.Spot.Event.Monster.MonsterBreakableTimeEndEvent").nested("EReason"),
    ["TimeOver","TargetCompleted","Cancelled"]);
  let fault=null,total=0,emitted=0,lastSnapshotTick=-1;
  const counts=new Map(),latest=new Map(),conditions=new Map(),maxEmitted=extended?1024:256;
  const latch=(stage,error)=>{
    if (fault===null) fault=stage+": "+(error&&error.stack?error.stack:String(error));
  };
  const eventEntity=value=>{
    if (!live(value)) return null;
    if (value.class.type.name!==entityInfo.type.name)
      throw new Error("Original tactical event entity type changed");
    return Number(value.field("EntityID").value);
  };
  function observeSendEvent(event) {
    if (fault!==null || !live(event)) return;
    const spec=expected.get(event.class.type.name);
    if (!spec) return;
    try {
      const id=number(event.field("<SpotEventID>k__BackingField").value);
      if (id!==spec.id) throw new Error("Original tactical event class/ID mismatch");
      const row={kind:spec.enumName,tick:Number(management.field("_tickCount").value),
        nativePlaytime:finite(management.field("_playtime").value),eventId:id};
      for (const name of ["MonsterInfo","CasterInfo","EntityInfo","TargetInfo","PresetInfo"])
        if (spec.fieldNames.has(name))
          row[name.charAt(0).toLowerCase()+name.slice(1)+"Id"]=
            eventEntity(event.field(name).value);
      if (spec.enumName==="QuickTimeStart")
        row.quickTimeId=Number(event.field("QuickTimeId").value);
      if (spec.enumName==="QuickTimePresetStart") {
        row.index=Number(event.field("Index").value);
        row.isStart=Boolean(event.field("IsStart").value);
      }
      if (spec.enumName==="QuickTimeColliderEnabled")
        row.enabled=Boolean(event.field("Enabled").value);
      if (spec.enumName==="QuickTimeEnd" || spec.enumName==="QuickTimePresetEnd")
        row.success=Boolean(event.field("Success").value);
      if (spec.enumName==="QuickTimePresetEnd") row.end=Boolean(event.field("End").value);
      if (spec.enumName==="MonsterBreakableTimeStart") {
        row.breakableNativeTime=finite(event.field("BreakableTime").value);
        row.targetCount=Number(event.field("TargetCount").value);
      }
      if (spec.enumName==="MonsterBreakableProgress")
        row.remainValue=Number(event.field("RemainValue").value);
      if (spec.enumName==="MonsterBreakableTimeEnd")
        row.reason=enumValue(endReasonMap,event.field("Reason").value);
      if (spec.enumName==="MonsterBreakColliderActiveStart") {
        row.castingNativeTime=finite(event.field("CastingTime").value);
        row.endAtRemainCount=Number(event.field("EndAtRemainCount").value);
        row.colliderNames=unsupported("original_string_array_not_decoded_in_event_callback");
      }
      if (spec.enumName==="MonsterAttack") {
        row.attackNodeId=Number(event.field("AttackNodeID").value);
        row.animationNumber=number(event.field("AniNumber").value);
      }
      if (spec.enumName==="MonsterSelectChoiceSkill") {
        row.durationNativeTime=finite(event.field("DurationTime").value);
        row.endAtRemainCount=Number(event.field("EndAtRemainCount").value);
        row.skillChoices=unsupported("original_choice_list_not_decoded_in_event_callback");
      }
      if (spec.enumName==="MonsterCondition") {
        row.condition=enumValue(conditionMap,event.field("CurrentCondition").value);
        if (extended) {
          if (!conditions.has(row.monsterInfoId)&&conditions.size>=128)
            throw new Error("Monster condition identity retention limit exceeded");
          conditions.set(row.monsterInfoId,row);
        }
      }
      total++;
      counts.set(spec.enumName,(counts.get(spec.enumName)||0)+1);
      latest.set(spec.enumName,row);
      if (emitted<maxEmitted) {
        emitted++;
        emit({status:"original_tactical_transition",ordinal:emitted,...row});
      }
    } catch(error) { latch("observeSendEvent",error); }
  }
  function snapshot(tick) {
    if (fault!==null) return {status:"original_tactical_snapshot",supported:false,fault};
    try {
      if (!Number.isSafeInteger(tick) || tick<0 || tick<=lastSnapshotTick ||
          Number(management.field("_tickCount").value)!==tick)
        throw new Error("Original tactical snapshot must follow one increasing native tick");
      lastSnapshotTick=tick;
      const subgroup=(name,fn)=>{
        try { return fn(); }
        catch(error) { return unsupported(name+": "+String(error)); }
      };
      return {status:"original_tactical_snapshot",supported:true,tick,
        nativePlaytime:finite(management.field("_playtime").value),
        qte:subgroup("qte",qteTargets),
        monster:subgroup("monster",monsterParts),
        squad:subgroup("squad",squad),
        latestBreakable:latest.get("MonsterBreakableTimeStart")||null,
        latestAttack:latest.get("MonsterAttack")||null,
        latestChoiceSkill:latest.get("MonsterSelectChoiceSkill")||null,
        latestPresetEnd:latest.get("QuickTimePresetEnd")||null,
        latestCondition:latest.get("MonsterCondition")||null,
        ...(extended?{
          latestQuickTimeStart:latest.get("QuickTimeStart")||null,
          latestPresetStart:latest.get("QuickTimePresetStart")||null,
          monsters:subgroup("monster_identities",monsterIdentities),
          monsterConditions:[...conditions.values()].sort((a,b)=>a.monsterInfoId-b.monsterInfoId)
        }: {})};
    } catch(error) {
      latch("snapshot",error);
      return {status:"original_tactical_snapshot",supported:false,fault};
    }
  }
  function summary() {
    return {status:"original_tactical_observer_summary",total,emitted,
      emittedLimit:maxEmitted,transitionsTruncated:total>maxEmitted,
      counts:Object.fromEntries([...counts].sort((a,b)=>a[0].localeCompare(b[0]))),
      latest:Object.fromEntries([...latest].sort((a,b)=>a[0].localeCompare(b[0]))),
      lastSnapshotTick,fault};
  }
  function checkFault() { if (fault!==null) throw new Error(fault); }
  emit({status:"original_tactical_observer_ready",qteContextPresent:live(qte),
    expectedInstalledDllSha256:"2df7134a6a9c3a8dbbde88402fc8d16d1d6c3f4c2d5e262bea78c3d78b96dd02",
    installsHooks:false,drawsRandom:false,mutatesCombatState:false});
  return {observeSendEvent,snapshot,summary,checkFault};
}
