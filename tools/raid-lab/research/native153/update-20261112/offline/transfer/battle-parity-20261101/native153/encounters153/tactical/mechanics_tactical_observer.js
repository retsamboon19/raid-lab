// Metadata only: every read still uses the original bridge withHolder/value.
function createOriginalSnapshotMetadataCache() {
  const classes=new Map();
  const bindings=klass=>{
    const key=klass.handle.toString();
    let entry=classes.get(key);
    if(!entry){entry={fields:new Map(),methods:new Map()};classes.set(key,entry);}
    return entry;
  };
  return {
    field(holder,name){
      const klass=holder instanceof Il2Cpp.ValueType?holder.type.class:holder.class,table=bindings(klass).fields;
      let metadata=table.get(name);
      if(!metadata){metadata=klass.field(name);table.set(name,metadata);}
      return metadata.withHolder(holder).value;
    },
    method(holder,name,arity,valueType=false){
      const klass=valueType?holder.type.class:holder.class,table=bindings(klass).methods;
      const key=name+'#'+arity;
      let metadata=table.get(key);
      if(!metadata){metadata=klass.method(name,arity);table.set(key,metadata);}
      return metadata.withHolder(holder);
    }
  };
}

// Prepared current153-only adapter; no native validation claim. Historical input remains preserved.
// Read-only original tactical state. Extended identity is opt-in so retained
// Kraken evidence keeps its original observation contract.
// Call on Unity main thread. The caller forwards its existing SendEventDefault
// event and samples after each original UpdateSpot tick. No hooks or actions.
function createMechanicsTacticalObserver(runtime, management, team, pin, emit, extended=false, readVisualAimAnchors=false, pendingQteGeometry=false) {
  if (!runtime || !management || management.isNull() || !team || team.isNull() ||
      typeof pin !== "function" || typeof emit !== "function" ||
      typeof invokeChecked !== "function" || typeof intArg !== "function")
    throw new Error("Original tactical observer needs live management/team and bridge helpers");
  const game = Process.getModuleByName("GameAssembly.dll");
  // Opt-in diagnostic scalar adapter. SAME original checked runtime invoker;
  // first8 calls/method compare native unboxing to existing JS boxed path.
  const scalarDirect=globalThis.NATIVE153_FRAME_PROFILE_INPUT?.enabled===true;
  const guardedScalarMethods=new Set(),scalarCalls=new Map();
  let statValueClassHandle=null;
  const classValueSize=scalarDirect?new NativeFunction(game.getExportByName('il2cpp_class_value_size'),'int',['pointer','pointer']):null;
  const statValueAlignment=scalarDirect?Memory.alloc(4):null;
  const isOriginalStatValue=method=>{
    if(method.returnType.name!=='NK.Common.StatValue')return false;
    const klass=method.returnType.class;
    if(statValueClassHandle){if(!klass.handle.equals(statValueClassHandle))throw Error('Original StatValue class identity changed');return true;}
    const field=klass.field('Value');
    if(classValueSize(klass.handle,statValueAlignment)!==8||statValueAlignment.readU32()!==8||
        field.isStatic||field.offset!==16||field.type.name!=='System.Int64')throw Error('Original StatValue scalar layout changed');
    statValueClassHandle=klass.handle;return true;
  };
  const checkedScalar=scalarDirect?globalThis.NATIVE153_CHECKED_SCALAR_READER:null;
  if(scalarDirect&&!checkedScalar)throw Error('Original checked scalar reader not compiled before context');
  const at = (method,rva,label) => {
    requireKraken153Method(method,rva);
    guardedScalarMethods.add(method.handle.toString());
    return method;
  };
  const call = (method,self=null,args=[]) => invokeChecked(method,self,args);
  const snapshotMetadata=scalarDirect?createOriginalSnapshotMetadataCache():{
    field:(holder,name)=>holder.field(name).value,
    method:(holder,name,arity)=>holder.method(name,arity)
  };
  const live = value => value != null && !value.isNull();
  const number = value => typeof value === "number" || typeof value === "boolean" ?
    Number(value) : Number(snapshotMetadata.field(value,"value__"));
  const boundedInt = (value,limit,label) => {
    const n=Number(value);
    if (!Number.isSafeInteger(n) || n<0 || n>limit)
      throw new Error("Original tactical " + label + " outside bound: " + value);
    return n;
  };
  const field = (klass,name,offset) => {
    requireKraken153Field(klass,name);
  };
  const scalarRead=(method,self,args,kind,readBox)=>{
    if(!scalarDirect||!guardedScalarMethods.has(method.handle.toString())||method.isStatic||
        method.parameters.length!==0||args.length!==0)return readBox(call(method,self,args));
    const key=method.handle.toString();let entry=scalarCalls.get(key);
    if(!entry){
      const expected={int:'System.Int32',bool:'System.Boolean',long:'System.Int64'}[kind];
      // Native WeaponType is an original4-byte enum, not a System.Int32 getter.
      // Keep its existing boxed path rather than infer a categorical ABI.
      if(method.returnType.name!==expected&&!(kind==='long'&&isOriginalStatValue(method)))return readBox(call(method,self,args));
      entry={kind,returnType:method.returnType.name,name:method.name,verified:0,calls:0};
      scalarCalls.set(key,entry);
    }
    if(entry.kind!==kind||!self||self.isNull())throw Error('Original scalar getter receiver/kind changed');
    const result=checkedScalar.read(method,self,kind);
    if(entry.verified<8){
      const original=readBox(call(method,self,args));
      if(result!==original)throw Error('Original checked scalar getter comparison differs '+method.name);
      entry.verified++;
    }
    entry.calls++;
    return result;
  };
  const intResult=(method,self=null,args=[]) =>scalarRead(method,self,args,'int',v=>v.unbox().handle.readS32());
  const boolResult=(method,self=null,args=[]) =>scalarRead(method,self,args,'bool',v=>v.unbox().handle.readU8()!==0);
  const i64Result=(method,self=null,args=[]) =>scalarRead(method,self,args,'long',v=>v.unbox().handle.readS64().toString());
  const scalarPairs=new WeakMap();
  const i64Pair=(first,second,self)=>{
    if(!scalarDirect)return {hp:i64Result(first,self),maxHp:i64Result(second,self)};
    let pair=scalarPairs.get(first);
    if(!pair||pair.second!==second){
      const a=scalarCalls.get(first.handle.toString()),b=scalarCalls.get(second.handle.toString());
      // Preserve every existing ordered comparison invocation during warmup.
      if(!a||!b||a.verified<8||b.verified<8||a.kind!=='long'||b.kind!=='long')return {hp:i64Result(first,self),maxHp:i64Result(second,self)};
      pair={second,a,b,read:checkedScalar.bindLongPair(first,second)};scalarPairs.set(first,pair);
    }
    try{const values=pair.read(self);pair.a.calls++;pair.b.calls++;return values;}
    catch(error){if(error.originalScalarPairIndex===1)pair.a.calls++;throw error;}
  };
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
      requireKraken153Enum(klass,name,id);
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
  const valid=at(unityObject.method("op_Implicit",1),0x085236E0,
    "UnityEngine.Object.op_Implicit");
  const getTransform=at(component.method("get_transform",0),0x0851CB40,
    "Component.get_transform");
  const getPosition=at(transform.method("get_position",0),0x08533B90,
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
  // Opt-in only: caller must enable for Mirror, never shared baseline paths.
  let pendingBounds=null;
  if(pendingQteGeometry) {
    const boundsClass=unity.class("UnityEngine.Bounds");
    const classValueSize=new NativeFunction(game.getExportByName('il2cpp_class_value_size'),'int',['pointer','pointer']);
    const alignment=Memory.alloc(4);
    if(classValueSize(boundsClass.handle,alignment)!==24||alignment.readU32()!==4)
      throw Error("Original QTE Bounds size/alignment changed");
    for(const [name,offset]of [["m_Center",16],["m_Extents",28]]) {
      const f=boundsClass.field(name);
      if(f.offset!==offset||f.type.name!=="UnityEngine.Vector3"||f.isStatic)throw Error("Original QTE Bounds field changed");
    }
    pendingBounds=collider.method("get_bounds",0);
    const bytes=Array.from(new Uint8Array(pendingBounds.virtualAddress.readByteArray(24)),x=>x.toString(16).padStart(2,"0")).join("");
    if(!pendingBounds.virtualAddress.equals(game.base.add(0x08590C80))||pendingBounds.isStatic||pendingBounds.parameters.length||
       pendingBounds.returnType.name!=="UnityEngine.Bounds"||bytes!=="48895c2408574883ec2033c00f57c00f110148894110488b")throw Error("Original QTE collider bounds ABI changed");
  }
  const colliderEnabled=at(collider.method("get_enabled",0),0x08590D20,
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
    [management.class,"_playtime",0x6c],
    [team.class,"_focusedCharacter",0x20],
    [team.class,"<CharacterList>k__BackingField",0x38],
    [character,"<Cover>k__BackingField",0xf8],
    [entity,"Id",0x10],[entity,"<CurrentStatus>k__BackingField",0x30],
    [entityInfo,"EntityID",0x10],[eventBase,"<SpotEventID>k__BackingField",0x14],
    [monsterContextClass,"_targetMonster",0x38],
    [monsterContextClass,"_allMonsterParts",0x28],
    [monster,"<PartsData>k__BackingField",0x90],
    [parts,"PartsType",0x18],[parts,"<HitPoint>k__BackingField",0x20],
    [parts,"<Owner>k__BackingField",0x30],
    [parts,"<IsDestroyed>k__BackingField",0x3c],
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
    [qteColliderClass,"<ColType>k__BackingField",0x8c],
    [qteColliderClass,"_currentState",0xa4],
    [qteColliderClass,"_remainTime",0xa8]
  ]) field(klass,name,offset);
  const getHp=at(status.method("get_HP",0),0x066E0D50,"Status.HP");
  const getMaxHp=at(status.method("get_MaxHP",0),0x066E1110,"Status.MaxHP");
  const getPartHp=at(parts.method("get_CurrentHp",0),0x065ABE20,"PartsData.CurrentHp");
  const getPartMaxHp=at(parts.method("get_MaxHp",0),0x065ABF40,"PartsData.MaxHp");
  const partActive=at(parts.method("get_IsActive",0),0x065ABF00,"PartsData.IsActive");
  // Exact current153 read-only first-hit witness. PartsData metadata declares
  // HurtCount:Int32 field412; native getter is a direct load from that field.
  let getPartHurtCount=null;
  if(extended) {
    getPartHurtCount=parts.method('get_HurtCount',0);
    const prefix='8b819c010000c3cccccccccccccccccc';
    const bytes=Array.from(new Uint8Array(getPartHurtCount.virtualAddress.readByteArray(16)),x=>x.toString(16).padStart(2,'0')).join('');
    const hurt=parts.field('<HurtCount>k__BackingField'),partStatus=parts.field('Status');
    if(!getPartHurtCount.virtualAddress.equals(game.base.add(106610320))||getPartHurtCount.isStatic||
      getPartHurtCount.parameters.length||getPartHurtCount.returnType.name!=='System.Int32'||bytes!==prefix||
      hurt.isStatic||hurt.offset!==412||hurt.type.name!=='System.Int32'||partStatus.isStatic||partStatus.offset!==376||partStatus.type.name!=='NK.Spot.Model.Common.SpotEntityStatus')throw Error('Original PartsData.HurtCount ABI changed');
  }

  const qteOrder=at(qteColliderClass.method("get_Order",0),0x065BCF90,
    "SpotQuickTimeCollider.Order");
  const qteSuccess=at(presetClass.method("IsSuccess",0),0x065BD520,"SpotQuickTimePreset.IsSuccess");
  const weapon=runtime.class("NK.Spot.Model.Character.Weapon.SpotWeaponData");
  const getWeaponType=at(weapon.method("get_WeaponType",0),0x066E9A40,"Weapon.WeaponType");
  const getAmmo=at(weapon.method("get_CurrentAmmo",0),0x066E7EC0,"Weapon.CurrentAmmo");
  field(weapon,"<InputType>k__BackingField",232);
  field(weapon,"<CharacterAttackType>k__BackingField",1140);
  field(character,"_initUseBurstStep",280);
  const thirdBurstStep=number(Il2Cpp.domain.assembly("NK.Runtime.StaticData").image.class("NK.StaticData.BurstStep").field("Step3").value);
  if(!Number.isSafeInteger(thirdBurstStep))throw Error('Original Step3 enum unavailable');
  const getDownTiming=mechanicsOriginalDownTimingGetter(runtime);
  const getAutomatic=at(weapon.method("get_IsAutoFireWeapon",0),107907232,"Weapon.IsAutoFireWeapon");
  const casterElements=createMechanicsCasterElementReader(character,game,call);
  const weaponTypes=enumMap(Il2Cpp.domain.assembly("NK.Runtime.StaticData").image
    .class("NK.StaticData.WeaponType"),["None","AR","RL","SR","MG","SG","AS","GL","PS","SMG"]);
  const colType=enumMap(Il2Cpp.domain.assembly("NK.Runtime.StaticData").image
    .class("NK.StaticData.ColType"),["None","Break","Counter","Choice"]);
  const colState=enumMap(qteColliderClass.nested("ColliderState"),
    ["Enable","StartDelay","WaitConnect","Disable"]);
  const contexts=snapshotMetadata.field(management,"_contexts");
  if (!live(contexts)) throw new Error("Original management contexts missing");
  const contextFor=klass=>pin(call(snapshotMetadata.method(contexts,"get_Item",1),contexts,
    [klass.type.object.handle]));
  let qte=null, qteContextProblem=null;
  try { qte=contextFor(qteContextClass); }
  catch(error) { qteContextProblem=String(error); }
  const monsterContext=contextFor(monsterContextClass);
  if (!live(monsterContext)) throw new Error("Original MonsterContext missing");
  const hpOf=value=>{
    if (!live(value)) return unsupported("entity_missing");
    const current=snapshotMetadata.field(value,"<CurrentStatus>k__BackingField");
    if (!live(current)) return unsupported("current_status_missing");
    return i64Pair(getHp,getMaxHp,current);
  };
  const listCount=value=>boundedInt(intResult(snapshotMetadata.method(value,"get_Count",0),value),256,
    "list count");
  const listItems=(value,limit)=>{
    if (!live(value)) return [];
    const count=listCount(value);
    if (count>limit) throw new Error("Original tactical list limit exceeded");
    const rows=[];
    for (let i=0;i<count;i++) rows.push(call(snapshotMetadata.method(value,"get_Item",1),value,[intArg(i)]));
    return rows;
  };
  const dictionaryValues=(value,limit)=>{
    if (!live(value)) return unsupported("dictionary_missing");
    const count=boundedInt(intResult(snapshotMetadata.method(value,"get_Count",0),value),limit,
      "dictionary count");
    const values=call(snapshotMetadata.method(value,"get_Values",0),value);
    if (!live(values)) return unsupported("dictionary_values_missing");
    const iterator=call(snapshotMetadata.method(values,"GetEnumerator",0),values);
    if (!live(iterator)) return unsupported("dictionary_iterator_missing");
    const result=[];
    for (let i=0;i<=count;i++) {
      const cursor=iterator.unbox();
      if (!boolResult(snapshotMetadata.method(cursor,"MoveNext",0,true),cursor)) break;
      if (i===count) throw new Error("Original tactical dictionary enumeration exceeds Count");
      result.push(call(snapshotMetadata.method(cursor,"get_Current",0,true),cursor));
    }
    if (result.length!==count) throw new Error("Original tactical dictionary count mismatch");
    return result;
  };
  const qteTargets=()=>{
    if (!live(qte)) return unsupported("QuickTimeEventContext_missing: "+
      (qteContextProblem||"not_registered"));
    const active=Boolean(snapshotMetadata.field(qte,"<IsQuickTime>k__BackingField"));
    if (!active) return {supported:true,active:false,targets:[]};
    const preset=snapshotMetadata.field(qte,"<CurrentPreset>k__BackingField");
    if (!live(preset)) return unsupported("active_QTE_has_no_current_preset");
    const members=dictionaryValues(snapshotMetadata.field(preset,"_colliders"),32);
    if (!Array.isArray(members)) return members;
    const targets=[],pendingTargets=[],forbiddenGeometry=[];let nativePresetHasForbidden=false;
    for (const value of members) {
      if (!live(value) || value.class.type.name!==qteColliderClass.type.name)
        throw new Error("Original QTE dictionary value type changed");
      const presetColType=pendingQteGeometry?enumValue(colType,snapshotMetadata.field(value,"<ColType>k__BackingField")):null;
      if(presetColType&&["Counter","Choice"].includes(presetColType.name))nativePresetHasForbidden=true;
      const nativeCollider=snapshotMetadata.field(value,"<Collider>k__BackingField");
      if (!unityValid(nativeCollider)) continue;
      const enabled=boolResult(colliderEnabled,nativeCollider);
      if(pendingQteGeometry) {
        const state=enumValue(colState,snapshotMetadata.field(value,"_currentState"));
        const colTypeValue=presetColType;
        const pending=["StartDelay","WaitConnect"].includes(state.name);
        const forbidden=["Counter","Choice"].includes(colTypeValue.name);
        if((colTypeValue.name==="Break"&&pending)||(forbidden&&enabled)) {
          const row={id:Number(snapshotMetadata.field(value,"<ColliderId>k__BackingField")),entityId:Number(snapshotMetadata.field(value,"Id")),
            state,colType:colTypeValue,order:intResult(qteOrder,value),nativeColliderEnabled:enabled,
            remainingNativeTime:finite(snapshotMetadata.field(value,"_remainTime")),
            worldPosition:position(call(getTransform,nativeCollider)),health:hpOf(value)};
          if(colTypeValue.name==="Break")pendingTargets.push(row);
          else {
            try {
              const b=call(pendingBounds,nativeCollider).unbox().handle;
              const center=[b.readFloat(),b.add(4).readFloat(),b.add(8).readFloat()];
              const extents=[b.add(12).readFloat(),b.add(16).readFloat(),b.add(20).readFloat()];
              row.geometry=center.every(Number.isFinite)&&extents.every(v=>Number.isFinite(v)&&v>0)?
                {supported:true,center,extents,source:"original_Unity_Collider_bounds"}:
                {supported:false,reason:"original_forbidden_collider_bounds_empty_or_invalid"};
            }catch(error){row.geometry={supported:false,reason:"original_forbidden_collider_bounds_unavailable",error:String(error)};}
            forbiddenGeometry.push(row);
          }
        }
      }
      if (!enabled) continue;
      const world=call(getTransform,nativeCollider);
      const originalHp=hpOf(value);
      const worldPosition=position(world);
      if (!Array.isArray(worldPosition) || originalHp.supported===false)
        return unsupported("active_QTE_target_missing_live_position_or_health");
      targets.push({id:Number(snapshotMetadata.field(value,"<ColliderId>k__BackingField")),
        entityId:Number(snapshotMetadata.field(value,"Id")),
        state:enumValue(colState,snapshotMetadata.field(value,"_currentState")),
        colType:enumValue(colType,snapshotMetadata.field(value,"<ColType>k__BackingField")),
        order:intResult(qteOrder,value),
        remainingNativeTime:finite(snapshotMetadata.field(value,"_remainTime")),
        worldPosition,health:originalHp});
    }
    targets.sort((a,b)=>a.id-b.id);
    return {...(pendingQteGeometry?{pendingTargets,forbiddenGeometry,pendingGeometrySupported:true,nativePresetHasForbidden}:{}),supported:true,active:true,
      ...(extended?{presetEntityId:Number(snapshotMetadata.field(preset,"Id"))}:{}),
      groupId:Number(snapshotMetadata.field(preset,"<GroupId>k__BackingField")),
      currentOrder:Number(snapshotMetadata.field(preset,"<CurrentOrder>k__BackingField")),
      currentNativeTime:finite(snapshotMetadata.field(qte,"_currentTime")),
      currentIndex:Number(snapshotMetadata.field(qte,"_currentIndex")),
      nativePresetSuccess:boolResult(qteSuccess,preset),targets};
  };
  const monsterParts=()=>{
    const target=snapshotMetadata.field(monsterContext,"_targetMonster");
    if (!live(target)) return {supported:true,targetMonsterId:null,parts:[]};
    const members=listItems(snapshotMetadata.field(monsterContext,"_allMonsterParts"),256);
    const out=[],partStates=[],aimAnchors=[];
    for (const item of members) {
      if (!live(item) || item.class.type.name!==parts.type.name)
        throw new Error("Original monster part type changed");
      const owner=snapshotMetadata.field(item,"<Owner>k__BackingField");
      if (!live(owner) || !owner.handle.equals(target.handle)) continue;
      const nativeIsDestroyed=Boolean(snapshotMetadata.field(item,"<IsDestroyed>k__BackingField"));
      const nativePartActive=boolResult(partActive,item);
      const hurtCount=extended?intResult(getPartHurtCount,item):null;
      if(extended&&(!Number.isSafeInteger(hurtCount)||hurtCount<0))throw Error('Original part HurtCount invalid');
      if(!extended&&(nativeIsDestroyed||!nativePartActive))continue;
      const nativeStatus=snapshotMetadata.field(item,'Status');
      const partHealth=live(nativeStatus)?i64Pair(getPartHp,getPartMaxHp,item):{hp:'0',maxHp:'0'},partHp=partHealth.hp,partMaxHp=partHealth.maxHp;
      if(extended)partStates.push({partsType:number(snapshotMetadata.field(item,"PartsType")),nativeIsDestroyed,nativePartActive,
        hp:partHp,maxHp:partMaxHp,hurtCount});
      if(readVisualAimAnchors) {
        const anchor=position(snapshotMetadata.field(item,"<HitPoint>k__BackingField"));
        if(Array.isArray(anchor)&&anchor.every(Number.isFinite))aimAnchors.push({partsType:number(snapshotMetadata.field(item,"PartsType")),world:anchor,nativeIsDestroyed,nativePartActive,source:'original_persistent_HitPoint_transform',claimsActiveCollider:false});
      }
      if(nativeIsDestroyed||!nativePartActive)continue;
      const hitPoint=snapshotMetadata.field(item,"<HitPoint>k__BackingField");
      const worldPosition=position(hitPoint);
      if (!Array.isArray(worldPosition))
        return unsupported("active_monster_part_missing_live_hit_point");
      out.push({partsType:number(snapshotMetadata.field(item,"PartsType")),
        worldPosition,
        hp:partHp,maxHp:partMaxHp,...(extended?{hurtCount,nativePartActive,nativeIsDestroyed}:{})});
    }
    out.sort((a,b)=>a.partsType-b.partsType);
    return {supported:true,targetMonsterId:Number(snapshotMetadata.field(target,"Id")),parts:out,...(extended?{partStates}:{}),...(readVisualAimAnchors?{aimAnchors}:{})};
  };
  const monsterIdentities=()=>listItems(snapshotMetadata.field(monsterContext,"_monsters"),256)
    .map(value=>{
      if (!live(value)||value.class.type.name!==monster.type.name)
        throw new Error("Original monster identity type changed");
      const data=snapshotMetadata.field(value,"<Data>k__BackingField");
      const condition=snapshotMetadata.field(value,"<Condition>k__BackingField");
      if (!live(data)||!live(condition)) throw new Error("Original monster data/condition missing");
      const info=snapshotMetadata.field(data,"<MonsterStaticInfo>k__BackingField");
      if (!live(info)) throw new Error("Original monster static identity missing");
      return {entityId:Number(snapshotMetadata.field(value,"Id")),
        tableId:snapshotMetadata.field(info,"<TableId>k__BackingField").toString(),
        condition:enumValue(conditionMap,snapshotMetadata.field(condition,"<CurrentConditionType>k__BackingField"))};
    });
  const squad=()=>{
    const focused=snapshotMetadata.field(team,"_focusedCharacter");
    const members=listItems(snapshotMetadata.field(team,"<CharacterList>k__BackingField"),5);
    const characters=[];
    for (const item of members) {
      if (!live(item) || item.class.type.name!==character.type.name)
        throw new Error("Original team character type changed");
      const itemCover=snapshotMetadata.field(item,"<Cover>k__BackingField");
      const health=hpOf(item);
      const coverHealth=live(itemCover)?hpOf(itemCover):null;
      if (health.supported===false || coverHealth && coverHealth.supported===false)
        return unsupported("team_character_or_cover_health_missing");
      const currentWeapon=snapshotMetadata.field(item,"<CurrentWeaponData>k__BackingField");
      if (!live(currentWeapon)) return unsupported("team_character_weapon_missing");
      const weaponType=intResult(getWeaponType,currentWeapon);
      const defaultWeapon=snapshotMetadata.field(item,"<DefaultWeaponData>k__BackingField");
      characters.push({id:Number(snapshotMetadata.field(item,"Id")),health,casterElementIds:casterElements(item),
        nativeBurstStep:number(snapshotMetadata.field(item,"_initUseBurstStep")),nativeIsBurst3:number(snapshotMetadata.field(item,"_initUseBurstStep"))===thirdBurstStep,
        weapon:{identity:currentWeapon.handle.toString(),nativeIsReplacement:live(defaultWeapon)&&!currentWeapon.handle.equals(defaultWeapon.handle),nativeInputType:number(snapshotMetadata.field(currentWeapon,"<InputType>k__BackingField")),nativeAttackType:number(snapshotMetadata.field(currentWeapon,"<CharacterAttackType>k__BackingField")),type:{value:weaponType,name:weaponTypes.get(weaponType)||null},
          ammo:i64Result(getAmmo,currentWeapon),nativeDownFireTiming:boolResult(getDownTiming,currentWeapon),nativeIsAutoFireWeapon:boolResult(getAutomatic,currentWeapon)},
        cover:live(itemCover) ? {id:Number(snapshotMetadata.field(itemCover,"Id")),
          health:coverHealth} : null});
    }
    return {supported:true,focusId:live(focused)?Number(snapshotMetadata.field(focused,"Id")):null,
      characters};
  };
  const specs=[
    ["NK.Spot.Event.QuickTime.QuickTimeStartEvent","QuickTimeStart",[["MonsterInfo",0x40],["QuickTimeId",0x48]]],
    ["NK.Spot.Event.QuickTime.QuickTimePresetStartEvent","QuickTimePresetStart",[["MonsterInfo",0x40],["Index",0x48],["IsStart",0x4C]]],
    ["NK.Spot.Event.QuickTime.QuickTimeColliderEnabledEvent","QuickTimeColliderEnabled",[["EntityInfo",0x40],["Enabled",0x48]]],
    ["NK.Spot.Event.QuickTime.QuickTimeColliderHitEvent","QuickTimeColliderHit",[["EntityInfo",0x40]]],
    ["NK.Spot.Event.QuickTime.QuickTimeEndEvent","QuickTimeEnd",[["Success",0x40]]],
    ["NK.Spot.Event.QuickTime.QuickTimePresetEndEvent","QuickTimePresetEnd",[["PresetInfo",0x40],["Success",0x48],["End",0x49]]],
    ["NK.Spot.Event.Monster.MonsterAttackEvent","MonsterAttack",[["CasterInfo",0x40],["TargetInfo",0x48],["AttackNodeID",0x64],["AniNumber",0x5C]]],
    ["NK.Spot.Event.Monster.MonsterConditionEvent","MonsterCondition",[["MonsterInfo",0x40],["CurrentCondition",0x48]]]
  ];
  const expected=new Map();
  for (const [className,enumName,fields] of specs) {
    const klass=runtime.class(className);
    for (const [name,offset] of fields) field(klass,name,offset);
    expected.set(className,{id:number(eventIds.field(enumName).value),enumName,
      fieldNames:new Set(fields.map(([name])=>name))});
  }
  at(management.method("SendEventDefault",1),0x076071F0,"SendEventDefault");
  const conditionMap=enumMap(runtime.class("NK.Spot.Model.Monster.MonsterConditionType"),
    ["None","Idle","WaitMove","Move","Dead","JumpReady","Jump","JumpEnd",
      "Stun","FireCasting","Fire","FireEnd","Suicide","Teleport","DashReady",
      "Dash","DashEnd"]);
  const endReasonMap=new Map(); // No Mirror-only break event roots in Kraken.
  let fault=null,total=0,emitted=0,lastSnapshotTick=-1;
  const counts=new Map(),latest=new Map(),conditions=new Map(),maxEmitted=extended?1024:256;
  const latch=(stage,error)=>{
    if (fault===null) fault=stage+": "+(error&&error.stack?error.stack:String(error));
  };
  const eventEntity=value=>{
    if (!live(value)) return null;
    if (value.class.type.name!==entityInfo.type.name)
      throw new Error("Original tactical event entity type changed");
    return Number(snapshotMetadata.field(value,"EntityID"));
  };
  function observeSendEvent(event) {
    if (fault!==null || !live(event)) return;
    const spec=expected.get(event.class.type.name);
    if (!spec) return;
    try {
      const id=number(snapshotMetadata.field(event,"<SpotEventID>k__BackingField"));
      if (id!==spec.id) throw new Error("Original tactical event class/ID mismatch");
      const row={kind:spec.enumName,tick:Number(snapshotMetadata.field(management,"_tickCount")),
        nativePlaytime:finite(snapshotMetadata.field(management,"_playtime")),eventId:id};
      for (const name of ["MonsterInfo","CasterInfo","EntityInfo","TargetInfo","PresetInfo"])
        if (spec.fieldNames.has(name))
          row[name.charAt(0).toLowerCase()+name.slice(1)+"Id"]=
            eventEntity(snapshotMetadata.field(event,name));
      if (spec.enumName==="QuickTimeStart")
        row.quickTimeId=Number(snapshotMetadata.field(event,"QuickTimeId"));
      if (spec.enumName==="QuickTimePresetStart") {
        row.index=Number(snapshotMetadata.field(event,"Index"));
        row.isStart=Boolean(snapshotMetadata.field(event,"IsStart"));
      }
      if (spec.enumName==="QuickTimeColliderEnabled")
        row.enabled=Boolean(snapshotMetadata.field(event,"Enabled"));
      if (spec.enumName==="QuickTimeEnd" || spec.enumName==="QuickTimePresetEnd")
        row.success=Boolean(snapshotMetadata.field(event,"Success"));
      if (spec.enumName==="QuickTimePresetEnd") row.end=Boolean(snapshotMetadata.field(event,"End"));
      if (spec.enumName==="MonsterBreakableTimeStart") {
        row.breakableNativeTime=finite(snapshotMetadata.field(event,"BreakableTime"));
        row.targetCount=Number(snapshotMetadata.field(event,"TargetCount"));
      }
      if (spec.enumName==="MonsterBreakableProgress")
        row.remainValue=Number(snapshotMetadata.field(event,"RemainValue"));
      if (spec.enumName==="MonsterBreakableTimeEnd")
        row.reason=enumValue(endReasonMap,snapshotMetadata.field(event,"Reason"));
      if (spec.enumName==="MonsterBreakColliderActiveStart") {
        row.castingNativeTime=finite(snapshotMetadata.field(event,"CastingTime"));
        row.endAtRemainCount=Number(snapshotMetadata.field(event,"EndAtRemainCount"));
        row.colliderNames=unsupported("original_string_array_not_decoded_in_event_callback");
      }
      if (spec.enumName==="MonsterAttack") {
        row.attackNodeId=Number(snapshotMetadata.field(event,"AttackNodeID"));
        row.animationNumber=number(snapshotMetadata.field(event,"AniNumber"));
      }
      if (spec.enumName==="MonsterSelectChoiceSkill") {
        row.durationNativeTime=finite(snapshotMetadata.field(event,"DurationTime"));
        row.endAtRemainCount=Number(snapshotMetadata.field(event,"EndAtRemainCount"));
        row.skillChoices=unsupported("original_choice_list_not_decoded_in_event_callback");
      }
      if (spec.enumName==="MonsterCondition") {
        row.condition=enumValue(conditionMap,snapshotMetadata.field(event,"CurrentCondition"));
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
          Number(snapshotMetadata.field(management,"_tickCount"))!==tick)
        throw new Error("Original tactical snapshot must follow one increasing native tick");
      lastSnapshotTick=tick;
      const subgroup=(name,fn)=>{
        try { return scalarDirect?globalThis.NATIVE153_FRAME_PROFILE.measure('observer_'+name,fn):fn(); }
        catch(error) { return unsupported(name+": "+String(error)); }
      };
      return {status:"original_tactical_snapshot",supported:true,tick,
        nativePlaytime:finite(snapshotMetadata.field(management,"_playtime")),
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
      lastSnapshotTick,fault,scalarGetterDiagnostic:{enabled:scalarDirect,bindings:scalarCalls.size,statValueLayoutVerified:statValueClassHandle!==null,
        calls:[...scalarCalls].map(([method,x])=>({method,name:x.name,returnType:x.returnType,kind:x.kind,verified:x.verified,calls:x.calls}))}};
  }
  function checkFault() { if (fault!==null) throw new Error(fault); }
  emit({status:"original_tactical_observer_ready",qteContextPresent:live(qte),
    expectedInstalledDllSha256:"d39896d3770888039c728a1908448c3db5efa7cdf874c90d56f46d8d566428d2",
    installsHooks:false,drawsRandom:false,mutatesCombatState:false});
  return {observeSendEvent,snapshot,summary,checkFault,
    snapshotQteGeometry:tick=>({...qteTargets(),nativeGeometryTick:tick})};
}

// Original current153 virtual getter returns inherited dynamic CasterElementId,
// including original UpdateCasterElement changes; never infer from names/kits.
function createMechanicsCasterElementReader(character,game,call) {
  const getter=character.method("GetCasterElementIDList",0);
  const prefix="488b4160c3cccccccccccccccccccccc48895c2408574883";
  if(getter.isStatic||getter.parameters.length!==0||
     getter.returnType.name!=="System.Collections.Generic.List<System.Int32>"||
     !getter.virtualAddress.equals(game.base.add(9322480)))
    throw Error("Original caster element getter signature changed");
  const bytes=new Uint8Array(getter.virtualAddress.readByteArray(prefix.length/2));
  if(Array.from(bytes,b=>b.toString(16).padStart(2,"0")).join("")!==prefix)
    throw Error("Original caster element getter source changed");
  return actor=>{
    const list=call(getter,actor);
    if(!list||list.isNull())throw Error("Original dynamic caster element list missing");
    const size=list.class.field("_size"),items=list.class.field("_items");
    if(size.offset!==24||size.type.name!=="System.Int32"||items.offset!==16)
      throw Error("Original caster element List layout changed");
    const count=Number(list.field("_size").value),source=list.field("_items").value;
    if(!Number.isSafeInteger(count)||count<0||count>16)throw Error("Original caster element count invalid");
    if(count===0)return [];
    if(!source||source.isNull())throw Error("Original caster element array missing");
    const array=new Il2Cpp.Array(source.handle);
    if(array.length<count)throw Error("Original caster element count exceeds array");
    const ids=[];
    for(let i=0;i<count;i++){
      const id=Number(array.get(i));
      if(!Number.isSafeInteger(id)||id<=0)throw Error("Original caster element ID invalid");
      ids.push(id);
    }
    return ids;
  };
}
