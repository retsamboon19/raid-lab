// Prepared current153-only adapter; no native validation claim. Historical input remains preserved.
// Original-action adapter for the isolated mechanics host. This module is
// deliberately synchronous: create and call it on the Unity main thread.
// Installed GameAssembly SHA-256:
// d39896d3770888039c728a1908448c3db5efa7cdf874c90d56f46d8d566428d2
// Required globals: Il2Cpp, Process, Memory, invokeChecked, intArg,
// floatArg. It never writes TeamContext/SpotDriver flags or combat outcomes.
function createMechanicsTacticalActions(runtime, management, team,
    geometry, aimBinding, pin, emit) {
  const installed =
    "d39896d3770888039c728a1908448c3db5efa7cdf874c90d56f46d8d566428d2";
  const live = value => value != null && !value.isNull();
  const requireRef = (value, name) => {
    if (!live(value)) throw new Error("Original tactical dependency missing: " + name);
    return pin(value);
  };
  const call = (method, instance = null, args = []) =>
    invokeChecked(method, instance, args);
  const boolArg = value => {
    const ptr=Memory.alloc(1);
    ptr.writeU8(value ? 1 : 0);
    return ptr;
  };
  const readInt = (method, instance) =>
    call(method, instance).unbox().handle.readS32();
  const readBool = (method, instance) =>
    !!call(method, instance).unbox().handle.readU8();
  const numeric = value => typeof value === "number" ? value :
    Number(value.field("value__").value);
  const same = (a, b) => live(a) && live(b) && a.handle.equals(b.handle);
  const exact = (method, rva, label) => {
    requireKraken153Method(method,rva);
    return method;
  };
  const float3 = (value, label) => {
    const array = Array.isArray(value) ? value :
      value && [value.x, value.y, value.z];
    if (!Array.isArray(array) || array.length !== 3 ||
        array.some(x => typeof x !== "number" || !Number.isFinite(x)))
      throw new Error(label + " requires explicit finite x/y/z");
    return array;
  };
  const struct = values => {
    const p = Memory.alloc(values.length * 4);
    values.forEach((x, i) => p.add(i * 4).writeFloat(x));
    return p;
  };
  const emitAction = (action, detail) => {
    emit({ phase: "mechanics_tactical_actions", action, ...detail });
  };

  if (!runtime || !geometry || geometry.installedDllSha256 !== installed ||
      !aimBinding || !(aimBinding.bound instanceof Map) ||
      typeof pin !== "function" || typeof emit !== "function")
    throw new Error("Tactical adapter requires exact live original aim binding");
  requireRef(management, "SpotManagement");
  requireRef(team, "TeamContext");
  const driver = requireRef(management.field("_spotDriver").value,
    "SpotManagement._spotDriver");
  const game = Process.getModuleByName("GameAssembly.dll");
  const driverClass = runtime.class("NK.Spot.Context.SpotDriver");
  const teamClass = runtime.class("NK.Spot.Context.Player.TeamContext");
  const spotEvent = runtime.class("NK.Spot.Common.SpotEvent");
  const autoEvent = runtime.class("NK.Spot.Event.Data.ChangeAutoModeEvent");
  const autoType = runtime.class("NK.Spot.Event.Data.SpotAutoType");
  const tagEvent = runtime.class("NK.Spot.Event.Character.TagCharacterEvent");
  const coverEvent = runtime.class("NK.Spot.Event.Character.ChangeForcedCoverEvent");
  const unity = Il2Cpp.domain.assembly("UnityEngine.CoreModule").image;
  const weaponClass = runtime.class(
    "NK.Spot.Model.Character.Weapon.SpotWeaponData");
  const currentAmmo = exact(weaponClass.method("get_CurrentAmmo", 0),
    0x066E7EC0, "SpotWeaponData.CurrentAmmo");
  const originalInputTypeField=weaponClass.field('<InputType>k__BackingField');
  if(originalInputTypeField.offset!==232||originalInputTypeField.type.name!=='NK.StaticData.InputType')throw Error('Original weapon InputType field changed');
  const nativeDownTiming=mechanicsOriginalDownTimingGetter(runtime);
  const nativeFullCharge=exact(weaponClass.method("get_IsFullCharge",0),107907472,"fullCharge");
  const nativeAutoFireWeapon=exact(weaponClass.method("get_IsAutoFireWeapon",0),107907232,"autoFireWeapon");
  const camera = requireRef(geometry.live && geometry.live.camera,
    "original live Camera");
  if (!same(camera, aimBinding.camera))
    throw new Error("Tactical camera differs from original aim binding");
  const cameraMethod = exact(unity.class("UnityEngine.Camera")
    .method("WorldToScreenPoint", 1), 0x084D8E00,
    "Camera.WorldToScreenPoint(Vector3)");
  const autoSend = exact(autoEvent.method("Send", 2), 0x06E82000,
    "ChangeAutoModeEvent.Send");
  const tagCtor = exact(tagEvent.method(".ctor", 1), 0x06E90F90,
    "TagCharacterEvent.ctor");
  const tagSend = exact(tagEvent.method("Send", 0), 0x06E90EA0,
    "TagCharacterEvent.Send");
  const coverCtor = exact(coverEvent.method(".ctor", 1), 0x06E82390,
    "ChangeForcedCoverEvent.ctor");
  const baseSend = exact(spotEvent.method("Send", 0), 0x0717EF10,
    "SpotEvent.Send");
  const down = exact(driverClass.method("InputPointDown", 0), 0x070F4B20,
    "SpotDriver.InputPointDown");
  const up = exact(driverClass.method("InputPointUp", 0), 0x070F4C00,
    "SpotDriver.InputPointUp");
  const move = exact(driverClass.method("MoveAimPosition", 3), 0x070F4DA0,
    "SpotDriver.MoveAimPosition");
  const getAuto = exact(teamClass.method("get_IsAutoModeAim", 0),24522560,"autoRead");
  const getCover = exact(teamClass.method("get_IsForcedCover", 0),40589008,"coverRead");
  const getInputType = exact(driverClass.method("get_InputType", 0),9175712,"inputRead");
  const getFocused = teamClass.field("_focusedCharacter");
  const inputField = driverClass.field("_inputType");
  const moveLock = driverClass.field("LockMoveAim");
  const inputLock = driverClass.field("LocKIunput");
  requireKraken153Field(teamClass,"_isAutoModeAim");
  requireKraken153Field(teamClass,"_isForcedCover");
  requireKraken153Field(teamClass,"_focusedCharacter");
  requireKraken153Field(driverClass,"_inputType");
  requireKraken153Field(driverClass,"LockMoveAim");
  requireKraken153Field(driverClass,"LocKIunput");
  const aimEnum = numeric(autoType.field("Aim").value);
  requireKraken153Enum(autoType,"Aim",aimEnum);
  if (aimEnum !== 0) throw new Error("Installed SpotAutoType.Aim changed");
  if (aimBinding.bound.size !== 5)
    throw new Error("Tactical adapter requires five original loaded actors");
  const pointer=createMechanicsVirtualPointer(emit);

  const focused = () => getFocused.withHolder(team).value;
  const inputType = () => readInt(getInputType, driver);
  const isLocked = field => !!field.withHolder(driver).value;
  const autoAim = () => readBool(getAuto, team);
  const forcedCover = () => readBool(getCover, team);
  const actorById = id => {
    if (!Number.isSafeInteger(id)) throw new Error("Entity ID must be an integer");
    const actor = aimBinding.bound.get(id);
    if (!actor || !live(actor.entity))
      throw new Error("Entity ID is not one of five original actors: " + id);
    return actor;
  };
  const focusedId = () => {
    const entity = focused();
    return live(entity) ? numeric(entity.field("Id").value) : null;
  };
  const snapshot = () => {
    pointer.check();
    const id = focusedId();
    const actor = id === null ? null : aimBinding.bound.get(id);
    const weapon = actor ? actor.entity.field(
      "<CurrentWeaponData>k__BackingField").value : null;
    if (actor && !live(weapon))
      throw new Error("Original focused weapon is absent");
    return {
      autoAim: autoAim(), forcedCover: forcedCover(),
      focusedEntityId: id, inputType: inputType(),
      focusedStance: actor ?
        readInt(actor.entity.method("get_StanceType", 0), actor.entity) : null,
      focusedUsedAmmoCount: actor ? readInt(actor.entity.method(
        "get_UsedAmmoCount", 0), actor.entity) : null,
      focusedShotHitNum: actor ? readInt(actor.entity.method(
        "get_ShotHitNum", 0), actor.entity) : null,
      focusedCurrentAmmo: actor ? call(currentAmmo, weapon)
        .unbox().handle.readS64().toString() : null,
      focusedWeaponIdentity: actor ? weapon.handle.toString() : null,
      focusedNativeInputType: actor ? numeric(weapon.field("<InputType>k__BackingField").value) : null,
      focusedNativeDownFireTiming: actor ? readBool(nativeDownTiming,weapon) : null,
      focusedIsFullCharge: actor ? readBool(nativeFullCharge,weapon) : null,
      focusedIsAutoFireWeapon: actor ? readBool(nativeAutoFireWeapon,weapon) : null,
      nativeAim: actor ? aimBinding.getNativeAimState(id) : null,
      originalAimControlReady: live(aimBinding.aimControl),
      originalCameraReady: live(camera),
      virtualPointer:pointer.snapshot(),
      squad:[...aimBinding.bound].map(([entityId,value])=>({entityId,
        stance:readInt(value.entity.method("get_StanceType",0),value.entity),
        usedAmmoCount:readInt(value.entity.method("get_UsedAmmoCount",0),value.entity)}))
    };
  };
  // Fresh required state only; preserve the original snapshot's required
  // pointer/focused-weapon guards and relative native getter order. Full
  // snapshot remains unchanged for logging and callers requiring diagnostics.
  const firingState = () => {
    pointer.check();
    const id = focusedId();
    const actor = id === null ? null : aimBinding.bound.get(id);
    const weapon = actor ? actor.entity.field(
      "<CurrentWeaponData>k__BackingField").value : null;
    if (actor && !live(weapon))
      throw new Error("Original focused weapon is absent");
    return {
      focusedEntityId: id, inputType: inputType(),
      focusedWeaponIdentity: actor ? weapon.handle.toString() : null,
      focusedNativeInputType: actor ? numeric(weapon.field("<InputType>k__BackingField").value) : null,
      focusedIsFullCharge: actor ? readBool(nativeFullCharge,weapon) : null,
      focusedIsAutoFireWeapon: actor ? readBool(nativeAutoFireWeapon,weapon) : null
    };
  };
  const directedOwnershipState = () => {
    pointer.check();
    const id = focusedId();
    const actor = id === null ? null : aimBinding.bound.get(id);
    const weapon = actor ? actor.entity.field(
      "<CurrentWeaponData>k__BackingField").value : null;
    if (actor && !live(weapon))
      throw new Error("Original focused weapon is absent");
    return {autoAim:autoAim(),forcedCover:forcedCover(),focusedEntityId:id,
      inputType:inputType(),focusedNativeInputType:actor ? numeric(weapon.field("<InputType>k__BackingField").value) : null};
  };
  const assertReleased = action => {
    if (inputType() === 2)
      throw new Error(action + " requires released original point input");
  };
  const assertManual = action => {
    if (autoAim())
      throw new Error(action + " requires original aim-auto off ownership");
  };

  const setAutoAim = enabled => {
    if (typeof enabled !== "boolean")
      throw new Error("setAutoAim requires a Boolean");
    assertReleased("Changing aim-auto ownership");
    if (autoAim() === enabled) return snapshot();
    call(autoSend, null, [intArg(aimEnum), boolArg(enabled)]);
    if (enabled) pointer.clear();
    if (autoAim() !== enabled)
      throw new Error("Original ChangeAutoModeEvent did not update TeamContext");
    emitAction("set_auto_aim", { enabled, eventRva: "0x06E82000" });
    return snapshot();
  };
  // Only the synchronous original finish boundary may use this. Native finish
  // already locks point input; InputPointUp must not be synthesized there.
  // ChangeAutoModeEvent and TeamContext.OnChangedAutoMode have no input lock gate.
  const restoreAutoAimBeforeNativeCleanup = enabled => {
    if (typeof enabled !== "boolean") throw new Error("Native finish autoAim requires Boolean");
    pointer.clear();
    if (autoAim() !== enabled) call(autoSend,null,[intArg(aimEnum),boolArg(enabled)]);
    if (autoAim() !== enabled) throw new Error("Original finish autoAim restoration failed");
    emitAction("restore_auto_aim_before_native_cleanup",{enabled,eventRva:"0x06E82000",
      pointInputReleased:false,nativeFinishOwnsLockedInput:true});
  };
  const focus = entityId => {
    assertReleased("Focus change");
    assertManual("Focus change");
    if (forcedCover()) throw new Error("Cannot change focus while forced cover is on");
    const actor = actorById(entityId);
    if (focusedId() === entityId) return snapshot();
    const position = readInt(actor.entity.method("get_PositionType", 0),
      actor.entity);
    const event = pin(tagEvent.alloc());
    call(tagCtor, event, [intArg(position)]);
    // Use the event's own Send override, including its original UI/input gate.
    call(tagSend, event);
    if (focusedId() !== entityId)
      throw new Error("Original TagCharacterEvent did not select requested actor");
    emitAction("focus", { entityId, position, eventRva: "0x06E90EA0" });
    return snapshot();
  };
  // Eligibility uses the same original camera as the actual input. Moving
  // parts can be active/healthy while outside the player viewport.
  const projectWorld = world => {
    const xyz = float3(world, "projectWorld");
    const screenPtr = call(cameraMethod, camera, [struct(xyz)]).unbox().handle;
    const screen = [screenPtr.readFloat(), screenPtr.add(4).readFloat(),
      screenPtr.add(8).readFloat()];
    if (screen.some(x => !Number.isFinite(x)))
      throw new Error("Original Camera projection is invalid");
    const bounds = geometry.screen;
    if (!bounds || !Number.isFinite(bounds.width) || bounds.width <= 0 ||
        !Number.isFinite(bounds.height) || bounds.height <= 0)
      throw new Error("Original live screen dimensions are unavailable");
    return {world:xyz,screen,visible:screen[2]>0 && screen[0]>=0 &&
      screen[0]<=bounds.width && screen[1]>=0 && screen[1]<=bounds.height};
  };
  const aimWorld = (entityId, world, log=true, readback=true) => {
    assertManual("Directed aim");
    if (isLocked(moveLock)) throw new Error("Original SpotDriver aim is locked");
    if (forcedCover()) throw new Error("Cannot direct aim while forced cover is on");
    const actor = actorById(entityId);
    if (focusedId() !== entityId)
      throw new Error("Directed aim requires the original focused actor");
    const projection=projectWorld(world),xyz=projection.world,screen=projection.screen;
    if (!projection.visible)
      throw new Error("Target projects outside original live screen");
    const dt = Number(management.field("_deltaTime").value);
    if (!Number.isFinite(dt) || dt <= 0 || dt > 0.25)
      throw new Error("Original SpotManagement delta time is unavailable");
    pointer.set(screen);
    call(move, driver, [actor.entity.handle,
      struct(screen.slice(0, 2)), floatArg(dt)]);
    // Command-only callers discard the return; retain full readback for logs and explicit callers.
    const native = log || readback ? aimBinding.getNativeAimState(entityId) : null;
    if (log) emitAction("aim_world", { entityId, world: xyz, screen,
      native, driverRva: "0x070F4DA0" });
    return { screen, native };
  };
  const press = () => {
    assertManual("Point-down fire input");
    if (isLocked(inputLock)) throw new Error("Original SpotDriver input is locked");
    if (forcedCover()) throw new Error("Cannot press fire while forced cover is on");
    if (focusedId() === null) throw new Error("No original focused actor");
    if (inputType() === 2) throw new Error("Original point input is already down");
    call(down, driver);
    if (inputType() !== 2)
      throw new Error("Original SpotDriver rejected point-down input");
    emitAction("press", { driverRva: "0x070F4B20" });
    return snapshot();
  };
  const release = () => {
    if (isLocked(inputLock)) throw new Error("Original SpotDriver input is locked");
    if (inputType() !== 2)
      throw new Error("Original point input was not pressed");
    call(up, driver);
    if (inputType() !== 1)
      throw new Error("Original SpotDriver rejected point-up input");
    // TeamContext.OnGetInputEvent (0x064EFA40) converts InputPointUpEvent's
    // 74000 ID into CheckChangeStanceEvent(stance=0), independent of the
    // aim-auto-only BTContext.OnInputPointUp branch.
    emitAction("release", { driverRva: "0x070F4C00" });
    return snapshot();
  };
  const setCover = enabled => {
    if (typeof enabled !== "boolean")
      throw new Error("setCover requires a Boolean");
    assertReleased("Forced-cover change");
    if (forcedCover() === enabled) return snapshot();
    const event = pin(coverEvent.alloc());
    call(coverCtor, event, [boolArg(enabled)]);
    call(baseSend, event);
    if (forcedCover() !== enabled)
      throw new Error("Original ChangeForcedCoverEvent did not update TeamContext");
    emitAction("set_cover", { enabled, eventRva: "0x06E82390" });
    return snapshot();
  };

  let autoSkillBinding=null;
  const autoSkill=()=>{
    if(!autoSkillBinding) {
      const getter=teamClass.method('get_IsAutoModeSkill',0),prefix='0fb64129c3cccccccccccccccccccccc';
      const bytes=Array.from(new Uint8Array(getter.virtualAddress.readByteArray(16)),x=>x.toString(16).padStart(2,'0')).join('');
      if(!getter.virtualAddress.equals(game.base.add(40589040))||getter.isStatic||getter.parameters.length||getter.returnType.name!=='System.Boolean'||bytes!==prefix)
        throw Error('Original auto-skill getter changed');
      const skill=numeric(autoType.field('Skill').value);requireKraken153Enum(autoType,'Skill',skill);
      if(skill!==1)throw Error('Original skill auto enum changed');
      autoSkillBinding={getter,skill};
    }
    return readBool(autoSkillBinding.getter,team);
  };
  const setAutoSkill=enabled=>{
    if(typeof enabled!=='boolean')throw Error('Auto skill input requires Boolean');
    const before=autoSkill();
    if(before!==enabled)call(autoSend,null,[intArg(autoSkillBinding.skill),boolArg(enabled)]);
    const after=autoSkill();if(after!==enabled)throw Error('Original skill-auto event rejected');
    if(before!==after)emitAction('set_auto_skill',{enabled,eventRva:'0x06E82000'});
    return after;
  };

  // Original per-character stance event used by TeamContext.OnGetInputEvent.
  // Binding is lazy: only one-shot coordination needs per-actor suppression.
  let actorStanceBinding=null;
  const setActorStance=(entityId,stanceName)=>{
    if(!['Idle','Aim'].includes(stanceName))throw Error('Only original Idle/Aim input stances allowed');
    const actor=actorById(entityId);
    if(!actorStanceBinding) {
      const klass=runtime.class('NK.Spot.Event.Character.CheckChangeStanceEvent');
      const ctor=klass.method('.ctor',2),spec={rva:0x06E85910,prefix:'48895c240848896c24104889742418574883ec20803df230'};
      const bytes=Array.from(new Uint8Array(ctor.virtualAddress.readByteArray(spec.prefix.length/2)),x=>x.toString(16).padStart(2,'0')).join('');
      if(!ctor.virtualAddress.equals(game.base.add(spec.rva))||bytes!==spec.prefix||ctor.isStatic||
        ctor.returnType.name!=='System.Void'||ctor.parameters.length!==2||
        ctor.parameters[0].type.name!=='NK.Spot.Model.Common.SpotEntity'||
        ctor.parameters[1].type.name!=='NK.Spot.Common.CommonEnum.EStance')
        throw Error('Original CheckChangeStanceEvent signature/prefix changed');
      for(const [name,type,offset] of [['CasterInfo','NK.Spot.Logic.Character.SpotEntityInfo',64],['ToStance','NK.Spot.Common.CommonEnum.EStance',72]]) {
        const field=klass.field(name);
        if(field.isStatic||field.type.name!==type||field.offset!==offset)throw Error('Original CheckChangeStanceEvent field changed: '+name);
      }
      const enumeration=ctor.parameters[1].type.class;
      if(enumeration.type.name!=='NK.Spot.Common.CommonEnum.EStance')throw Error('Original nested stance enum identity changed');
      const idle=numeric(enumeration.field('Idle').value),aim=numeric(enumeration.field('Aim').value);
      // Original OnGetInputEvent selects native Idle(0) on PointUp(74000),
      // native Aim(2) otherwise (current153 callsite0x07148729-0x07148744).
      if(idle!==0||aim!==2)throw Error('Original input stance enum changed');
      actorStanceBinding={klass,ctor,values:{Idle:idle,Aim:aim}};
    }
    const {klass,ctor,values}=actorStanceBinding;
    const before=readInt(actor.entity.method('get_StanceType',0),actor.entity);
    if(before===values[stanceName])return {entityId,stance:before,changed:false};
    // Never pull an ordinary dead/stunned/skill-animation actor out of native
    // ownership. This operation only switches the two ordinary input stances.
    if(![values.Idle,values.Aim].includes(before))return {entityId,stance:before,changed:false,nativeOwned:true};
    const event=pin(klass.alloc());call(ctor,event,[actor.entity.handle,intArg(values[stanceName])]);call(baseSend,event);
    const after=readInt(actor.entity.method('get_StanceType',0),actor.entity);
    emitAction('set_actor_stance',{entityId,requested:stanceName,before,after,eventRva:'0x06E85910',nativeEventOnly:true});
    return {entityId,stance:after,changed:after!==before,accepted:after===values[stanceName]};
  };

  const initial = snapshot();
  if (initial.focusedEntityId === null ||
      !aimBinding.bound.has(initial.focusedEntityId))
    throw new Error("Original focused actor is not bound to live aim geometry");
  const geometryWitness=captureNative153GeometryWitness(camera,aimBinding.aimControl,{invokeChecked});
  emit({status:'original_native_geometry_witness',...geometryWitness,
    nativeTick:Number(management.field('_tickCount').value),
    sampledOnceAtTacticalInitialization:true});
  emitAction("ready", { initial, originalCommandsOnly: true,
    sourceClientSha256: installed });
  let currentChargeGetter=null;
  const focusedChargeState=()=>{
    const id=focusedId();if(id===null)return null;
    const actor=actorById(id),weapon=actor.entity.field('<CurrentWeaponData>k__BackingField').value;
    if(!live(weapon))throw Error('Original charge handoff weapon missing');
    if(!currentChargeGetter) {
      const m=runtime.class('NK.Spot.Model.Character.Weapon.SpotWeaponData').method('get_CurrentChargeTime',0);
      const prefix=Array.from(new Uint8Array(m.virtualAddress.readByteArray(24)),v=>v.toString(16).padStart(2,'0')).join('');
      if(m.isStatic||m.parameters.length||m.returnType.name!=='System.Single'||!m.virtualAddress.equals(game.base.add(107904864))||prefix!=='40534883ec5033d2488bd9e880fdffff0f57c933d20f2fc1')throw Error('Original current charge getter changed');
      currentChargeGetter=m;
    }
    return {actorId:id,weaponIdentity:weapon.handle.toString(),inputType:inputType(),
      nativeInputType:numeric(weapon.field('<InputType>k__BackingField').value),
      stance:readInt(actor.entity.method('get_StanceType',0),actor.entity),
      usedAmmoCount:readInt(actor.entity.method('get_UsedAmmoCount',0),actor.entity),
      currentAmmo:call(currentAmmo,weapon).unbox().handle.readS64().toString(),
      currentChargeTime:call(currentChargeGetter,weapon).unbox().handle.readFloat()};
  };
  let projectileInitialQuery=null;
  const inspectProjectileInitialRay=(collider,start,target)=>{
    if(!projectileInitialQuery)projectileInitialQuery=createMechanicsProjectileInitialRayQuery();
    return projectileInitialQuery(collider,start,target);
  };
  const nativeAimEvidence=entityId=>({focusedEntityId:focusedId(),autoAim:autoAim(),
    forcedCover:forcedCover(),nativePointerInputType:inputType(),
    nativeAim:aimBinding.getNativeAimState(entityId)});
  let visibleCoreProbe=null,visibleCoreProbeFailed=false;
  const visibleCorePoint=(collider,world,extents)=>{
    if(visibleCoreProbeFailed)return null;
    try {
      if(!visibleCoreProbe)visibleCoreProbe=createMechanicsVisibleCoreProbe(camera,geometry,projectWorld,emit);
      return visibleCoreProbe(collider,world,extents);
    } catch(error) {
      visibleCoreProbeFailed=true;
      emit({status:'original_visible_core_edge_disabled',error:String(error),changesNativeMechanics:false});
      return null;
    }
  };
  const controlFlag = mechanicsCreateControlFlagReader(pointer, {inputType, autoAim, forcedCover});
  return { snapshot, firingState, directedOwnershipState, controlFlag, focusedChargeState, nativeAimEvidence, inspectProjectileInitialRay, projectWorld, visibleCorePoint, restoreAutoAimBeforeNativeCleanup, setAutoAim, focus, aimWorld, press, release, setCover, setActorStance, autoSkill, setAutoSkill, pointer };
}

// Passive original Unity/aim geometry witness. No setter, hook or event dispatch.
// Caller must verify exact current153 DLL identity and run on Unity main thread.
// Camera declarations: current153-kraken-tactical1; Screen: current153-run3.
// Original exact153 native RVA/prefix guards; pure getter calls only.
function captureNative153GeometryWitness(camera,aimControl,api) {
  const unity=Il2Cpp.domain.assembly('UnityEngine.CoreModule').image;
  const game=Process.getModuleByName('GameAssembly.dll');
  const methods={};
  const binding={"UnityEngine.Camera.get_fieldOfView":{"rva":139302720,"prefixHex":"40534883ec20488b0573d44703488bd9"},"UnityEngine.Camera.get_aspect":{"rva":139301520,"prefixHex":"40534883ec20488b05ebd94703488bd9"},"UnityEngine.Camera.get_pixelRect":{"rva":139303888,"prefixHex":"48895c2408574883ec20488b05efd347"},"UnityEngine.Camera.get_projectionMatrix":{"rva":139304352,"prefixHex":"48895c2408574883ec20488b0557d247"},"UnityEngine.Screen.get_width":{"rva":139443088,"prefixHex":"4883ec28488b0585b845034885c07513"},"UnityEngine.Screen.get_height":{"rva":139442704,"prefixHex":"4883ec28488b050dba45034885c07513"},"UnityEngine.Screen.get_safeArea":{"rva":139442976,"prefixHex":"40534883ec20488b059bb945030f57c0"}};
  const call=(klass,name,returns,self)=>{
    const method=klass.method(name,0);
    if(method.parameters.length!==0||method.returnType.name!==returns||method.isStatic!==(self===null))
      throw Error('Original passive geometry getter signature differs: '+name);
    const rva=Number(method.virtualAddress.sub(game.base));
    if(!Number.isSafeInteger(rva)||rva<=0||rva>=game.size)
      throw Error('Original passive geometry getter outside exact client: '+name);
    const key=klass.type.name+'.'+name,spec=binding[key];
    const prefixHex=Array.from(new Uint8Array(method.virtualAddress.readByteArray(16)),x=>x.toString(16).padStart(2,'0')).join('');
    if(!spec||spec.rva!==rva||spec.prefixHex!==prefixHex)throw Error('Original geometry getter native body differs: '+key);
    methods[key]={rva,returns,parameters:[],static:method.isStatic,prefixHex};
    return api.invokeChecked(method,self,[]).unbox();
  };
  const floats=(value,count)=>{
    const out=Array.from({length:count},(_,i)=>value.add(i*4).readFloat());
    if(!out.every(Number.isFinite))throw Error('Original geometry witness non-finite value');
    return out;
  };
  const rect=value=>{
    if(!value.type.class.isValueType||value.type.class.valueTypeSize!==16)throw Error('Original Rect size differs');
    const out=['m_XMin','m_YMin','m_Width','m_Height'].map(name=>{
      if(value.type.class.field(name).type.name!=='System.Single')throw Error('Original Rect field differs');
      return Number(value.field(name).value);
    });
    if(!out.every(Number.isFinite))throw Error('Original Rect values invalid');return out;
  };
  const matrix=value=>{
    if(!value.type.class.isValueType||value.type.class.valueTypeSize!==64)throw Error('Original Matrix4x4 size differs');
    const out={};
    for(let row=0;row<4;row++)for(let col=0;col<4;col++){
      const name='m'+row+col;
      if(value.type.class.field(name).type.name!=='System.Single')throw Error('Original Matrix4x4 field differs');
      out[name]=Number(value.field(name).value);
    }
    if(!Object.values(out).every(Number.isFinite))throw Error('Original matrix values invalid');return out;
  };
  const screen=unity.class('UnityEngine.Screen'),cam=unity.class('UnityEngine.Camera');
  if(!camera||camera.isNull()||!aimControl||aimControl.isNull())throw Error('Original geometry witness requires live camera/aim');
  const width=call(screen,'get_width','System.Int32',null).handle.readS32();
  const height=call(screen,'get_height','System.Int32',null).handle.readS32();
  const safeArea=rect(call(screen,'get_safeArea','UnityEngine.Rect',null));
  if(width<=0||height<=0)throw Error('Original geometry witness screen invalid');
  const cameraState={};
  for(const name of ['aspect','fieldOfView'])cameraState[name]=call(cam,'get_'+name,'System.Single',camera).handle.readFloat();
  for(const name of ['pixelRect'])cameraState[name]=rect(call(cam,'get_'+name,'UnityEngine.Rect',camera));
  for(const name of ['projectionMatrix'])cameraState[name]=matrix(call(cam,'get_'+name,'UnityEngine.Matrix4x4',camera));
  if(!['aspect','fieldOfView'].every(name=>Number.isFinite(cameraState[name])))throw Error('Original camera scalar invalid');
  const field=(name,type)=>{
    // Exact153 current153-run3 metadata58933dbe / original practice aim contract.
    const offsets={_screenToCanvasRatio:160,_safeAreaTop:176,_safeAreaBottom:180,_safeAreaLeft:184,_safeAreaRight:188};
    const f=aimControl.class.field(name);
    if(f.offset!==offsets[name]||f.isStatic||f.type.name!==type)throw Error('Original aim witness field type differs: '+name);
    return aimControl.handle.add(f.offset);
  };
  const ratio=floats(field('_screenToCanvasRatio','UnityEngine.Vector2'),2);
  const margins=['_safeAreaTop','_safeAreaBottom','_safeAreaLeft','_safeAreaRight'].map(name=>field(name,'System.Single').readFloat());
  if(!margins.every(Number.isFinite)||ratio.some(x=>x<=0))throw Error('Original aim witness canvas transform invalid');
  return {schemaVersion:1,source:'original_Unity_getters_and_UIAimControll_SetCanvasData_fields',
    screen:{width,height,safeArea},camera:cameraState,
    aim:{screenToCanvasRatio:ratio,safeAreaMargins:margins},nativeGetterBindings:methods,
    cameraPoseComparableOnlyAtMatchedNativePhase:true,passive:true,nativeStateWritten:false};
}

// Aim selection only. Original camera rays and the actual enabled core collider
// decide whether a visible point hits. Bounds alone never establish a hit.
function mechanicsVisibleCoreScreenCandidates(center,corners,screen) {
  const width=screen?.width,height=screen?.height;
  if(!Number.isFinite(width)||!Number.isFinite(height)||width<=2||height<=2||
      !Array.isArray(center)||center.length!==3||!center.every(Number.isFinite)||center[2]<=0)return [];
  const clamp=(v,lo,hi)=>Math.max(lo,Math.min(hi,v));
  const points=[[clamp(center[0],1,width-1),clamp(center[1],1,height-1)]];
  const visibleDepth=corners.filter(p=>Array.isArray(p)&&p.length===3&&p.every(Number.isFinite)&&p[2]>0);
  if(visibleDepth.length) {
    const left=Math.max(1,Math.min(...visibleDepth.map(p=>p[0]))),right=Math.min(width-1,Math.max(...visibleDepth.map(p=>p[0])));
    const bottom=Math.max(1,Math.min(...visibleDepth.map(p=>p[1]))),top=Math.min(height-1,Math.max(...visibleDepth.map(p=>p[1])));
    if(left<=right&&bottom<=top) {
      // Prefer the middle of the visible bounds intersection for input stability.
      // Every candidate still requires an original core Collider.Raycast hit.
      points.unshift([(left+right)/2,(bottom+top)/2]);
      for(const x of [0.25,0.75])for(const y of [0.25,0.75])points.push([left+(right-left)*x,bottom+(top-bottom)*y]);
    }
  }
  return points.filter((p,i)=>!points.slice(0,i).some(q=>p[0]===q[0]&&p[1]===q[1]));
}

function createMechanicsVisibleCoreProbe(camera,geometry,projectWorld,emit) {
  const game=Process.getModuleByName('GameAssembly.dll');
  const unity=Il2Cpp.domain.assembly('UnityEngine.CoreModule').image;
  const physics=Il2Cpp.domain.assembly('UnityEngine.PhysicsModule').image;
  function method(type,name,rva,result,parameters,prefix) {
    const matches=type.methods.filter(m=>m.name===name&&m.returnType.name===result&&
      !m.isStatic&&JSON.stringify(m.parameters.map(p=>p.type.name))===JSON.stringify(parameters));
    if(matches.length!==1)throw Error('Original visible-core method signature changed: '+name);
    const m=matches[0];
    const bytes=Array.from(new Uint8Array(m.virtualAddress.readByteArray(24)),v=>v.toString(16).padStart(2,'0')).join('');
    if(!m.virtualAddress.equals(game.base.add(rva))||bytes!==prefix)throw Error('Original visible-core method bytes changed: '+name);
    return m;
  }
  const rayType=unity.class('UnityEngine.Ray'),hitType=physics.class('UnityEngine.RaycastHit');
  // Use the same original metadata export as the current153 source exporter.
  // The Frida bridge does not expose Class.valueSize.
  const classValueSize=new NativeFunction(game.getExportByName('il2cpp_class_value_size'),'int',['pointer','pointer']);
  const rayAlignment=Memory.alloc(4),hitAlignment=Memory.alloc(4);
  const raySize=classValueSize(rayType.handle,rayAlignment),hitSize=classValueSize(hitType.handle,hitAlignment);
  if(raySize!==24||hitSize!==44||rayAlignment.readU32()!==4||hitAlignment.readU32()!==4)
    throw Error('Original ray/hit value size/alignment changed: '+JSON.stringify({raySize,hitSize,rayAlignment:rayAlignment.readU32(),hitAlignment:hitAlignment.readU32()}));
  for(const [type,name,offset]of [[rayType,'m_Origin',16],[rayType,'m_Direction',28],[hitType,'m_Point',16]]) {
    const f=type.field(name);if(f.offset!==offset||f.isStatic||f.type.name!=='UnityEngine.Vector3')throw Error('Original ray/hit field changed: '+name);
  }
  const makeRay=method(unity.class('UnityEngine.Camera'),'ScreenPointToRay',139296304,'UnityEngine.Ray',
    ['UnityEngine.Vector3'],'48895c2410574883ec400f57c033c00f1101488bfa488941');
  // The private overload returns a boxed RaycastHit via il2cpp_runtime_invoke.
  // Only the one-byte native Boolean out argument is caller-allocated.
  const raycast=method(physics.class('UnityEngine.Collider'),'Raycast',140053152,'UnityEngine.RaycastHit',
    ['UnityEngine.Ray','System.Single','System.Boolean&'],'48895c24084889742410574883ec4033c00f297424300f57');
  let queries=0,hits=0,misses=0;
  return function probe(collider,world,extents) {
    const original=projectWorld(world);
    if(original.visible)return null;
    if(!Array.isArray(extents)||extents.length!==3||!extents.every(v=>Number.isFinite(v)&&v>0))return null;
    const corners=[];
    for(const x of [-1,1])for(const y of [-1,1])for(const z of [-1,1])
      corners.push(projectWorld(world.map((v,i)=>v+[x,y,z][i]*extents[i])).screen);
    const candidates=mechanicsVisibleCoreScreenCandidates(original.screen,corners,geometry.screen);
    queries++;
    for(const screen of candidates) {
      const point=Memory.alloc(12);point.writeFloat(screen[0]);point.add(4).writeFloat(screen[1]);point.add(8).writeFloat(0);
      const ray=invokeChecked(makeRay,camera,[point]).unbox().handle;
      const origin=[ray.readFloat(),ray.add(4).readFloat(),ray.add(8).readFloat()];
      const distance=2*(Math.hypot(...world.map((v,i)=>v-origin[i]))+Math.hypot(...extents));
      if(!Number.isFinite(distance)||distance<=0)continue;
      const maxDistance=Memory.alloc(4);maxDistance.writeFloat(distance);
      const hasHit=Memory.alloc(1);hasHit.writeU8(0);
      const boxed=invokeChecked(raycast,collider,[ray,maxDistance,hasHit]);
      if(hasHit.readU8()===0)continue;
      if(!boxed||boxed.isNull()||boxed.class.type.name!=='UnityEngine.RaycastHit')throw Error('Original collider returned invalid hit');
      const hit=boxed.unbox().handle;
      const hitWorld=[hit.readFloat(),hit.add(4).readFloat(),hit.add(8).readFloat()];
      if(!hitWorld.every(Number.isFinite)||!projectWorld(hitWorld).visible)continue;
      hits++;
      const evidence={world:hitWorld,originalCoreCenter:world,originalCenterProjection:original.screen,
        requestedScreenPoint:screen,nativeColliderRaycastConfirmed:true,source:'original_core_collider_raycast_visible_edge'};
      if(hits<=8||hits%120===0)emit({status:'original_visible_core_edge_confirmed',queries,hits,misses,...evidence,changesNativeMechanics:false});
      return evidence;
    }
    misses++;
    if(misses<=3)emit({status:'original_visible_core_edge_unavailable',queries,hits,misses,candidateCount:candidates.length,
      originalCoreCenter:world,originalCenterProjection:original.screen,changesNativeMechanics:false});
    return null;
  };
}

// Passive geometry query on caller-local buffers. This is an initial straight
// StartPos->TargetPos segment, NOT measured velocity or a predicted trajectory.
function mechanicsNativeInitialRayInputs(start,target) {
  const vector=v=>Array.isArray(v)&&v.length===3&&v.every(Number.isFinite);
  if(!vector(start)||!vector(target))return null;
  const delta=target.map((n,i)=>Math.fround(n-start[i]));
  const distance=Math.fround(Math.hypot(...delta));
  if(!delta.every(Number.isFinite)||!Number.isFinite(distance)||distance<=0)return null;
  return {start:[...start],target:[...target],delta,distance};
}

function createMechanicsProjectileInitialRayQuery() {
  const game=Process.getModuleByName('GameAssembly.dll');
  const unity=Il2Cpp.domain.assembly('UnityEngine.CoreModule').image;
  const physics=Il2Cpp.domain.assembly('UnityEngine.PhysicsModule').image;
  const rayType=unity.class('UnityEngine.Ray'),vectorType=unity.class('UnityEngine.Vector3');
  const hitType=physics.class('UnityEngine.RaycastHit');
  const classValueSize=new NativeFunction(game.getExportByName('il2cpp_class_value_size'),'int',['pointer','pointer']);
  for(const [type,size] of [[rayType,24],[vectorType,12],[hitType,44]]) {
    const alignment=Memory.alloc(4);
    if(!type.isValueType||classValueSize(type.handle,alignment)!==size||alignment.readU32()!==4)
      throw Error('Original initial-ray value size/alignment changed: '+type.type.name);
  }
  for(const [type,name,offset,expected] of [[rayType,'m_Origin',16,'UnityEngine.Vector3'],
    [rayType,'m_Direction',28,'UnityEngine.Vector3'],[hitType,'m_Point',16,'UnityEngine.Vector3'],
    [hitType,'m_Distance',44,'System.Single']]) {
    const field=type.field(name);
    if(field.isStatic||field.offset!==offset||field.type.name!==expected)throw Error('Original initial-ray layout changed: '+name);
  }
  const checked=(type,name,rva,result,parameters,prefix)=>{
    const matches=type.methods.filter(m=>m.name===name&&!m.isStatic&&m.returnType.name===result&&
      JSON.stringify(m.parameters.map(p=>p.type.name))===JSON.stringify(parameters));
    if(matches.length!==1)throw Error('Original initial-ray signature changed: '+name);
    const method=matches[0],bytes=Array.from(new Uint8Array(method.virtualAddress.readByteArray(24)),v=>v.toString(16).padStart(2,'0')).join('');
    if(!method.virtualAddress.equals(game.base.add(rva))||bytes!==prefix)throw Error('Original initial-ray method changed: '+name);
    return method;
  };
  const ctor=checked(rayType,'.ctor',139418288,'System.Void',['UnityEngine.Vector3','UnityEngine.Vector3'],
    '40534883ec40f20f1002488bd98b4208488d542420f20f11');
  const cast=checked(physics.class('UnityEngine.Collider'),'Raycast',140053152,'UnityEngine.RaycastHit',
    ['UnityEngine.Ray','System.Single','System.Boolean&'],'48895c24084889742410574883ec4033c00f297424300f57');
  // Win64 ABI is independently proved in RAY-CONSTRUCTOR-SOURCE.asm. The
  // constructor writes only our local Ray and performs ORIGINAL normalization.
  const construct=new NativeFunction(ctor.virtualAddress,'void',['pointer','pointer','pointer','pointer']);
  const writeVector=v=>{const p=Memory.alloc(12);v.forEach((n,i)=>p.add(i*4).writeFloat(n));return p;};
  const readVector=p=>[p.readFloat(),p.add(4).readFloat(),p.add(8).readFloat()];
  return function inspectProjectileInitialRay(collider,start,target) {
    const inputs=mechanicsNativeInitialRayInputs(start,target);
    if(!inputs)return {supported:false,reason:'native_initial_segment_nonfinite_or_zero'};
    if(!collider||collider.isNull())return {supported:false,reason:'native_core_collider_absent'};
    const ray=Memory.alloc(24),origin=writeVector(inputs.start),direction=writeVector(inputs.delta);
    construct(ray,origin,direction,ctor.handle);
    const nativeOrigin=readVector(ray),nativeDirection=readVector(ray.add(12));
    if(!nativeOrigin.every(Number.isFinite)||!nativeDirection.every(Number.isFinite)||nativeDirection.every(n=>n===0))
      return {supported:false,reason:'original_Ray_constructor_returned_no_finite_direction'};
    const maxDistance=Memory.alloc(4);maxDistance.writeFloat(inputs.distance);
    const hasHit=Memory.alloc(1);hasHit.writeU8(0);
    const boxed=invokeChecked(cast,collider,[ray,maxDistance,hasHit]);
    const base={supported:true,source:'original_Ray_ctor_and_Collider_Raycast',
      scope:'straight_initial_StartPos_to_TargetPos_segment_not_velocity_or_trajectory',
      nativeStartPos:inputs.start,nativeTargetPos:inputs.target,nativeRayOrigin:nativeOrigin,
      nativeNormalizedDirection:nativeDirection,queryMaxDistance:inputs.distance,
      nativeCoreIntersection:hasHit.readU8()!==0,changesNativeObjects:false,changesAim:false};
    if(!base.nativeCoreIntersection)return base;
    if(!boxed||boxed.isNull()||boxed.class.type.name!=='UnityEngine.RaycastHit')throw Error('Original initial-ray returned invalid hit');
    const hit=boxed.unbox().handle,point=readVector(hit),distance=hit.add(28).readFloat();
    if(!point.every(Number.isFinite)||!Number.isFinite(distance)||distance<0)throw Error('Original initial-ray hit values invalid');
    return {...base,nativeHitWorld:point,nativeHitDistance:distance};
  };
}

// Read only the requested original flag. No state cache or combat writes.
function mechanicsCreateControlFlagReader(pointer, readers) {
  return function controlFlag(name) {
    if (!['inputType','autoAim','forcedCover'].includes(name))
      throw Error('Unknown original control flag: '+name);
    pointer.check();
    return readers[name]();
  };
}
