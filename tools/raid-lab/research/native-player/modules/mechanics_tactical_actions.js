// Original-action adapter for the isolated mechanics host. This module is
// deliberately synchronous: create and call it on the Unity main thread.
// Installed GameAssembly SHA-256:
// 2df7134a6a9c3a8dbbde88402fc8d16d1d6c3f4c2d5e262bea78c3d78b96dd02
// Required globals: Il2Cpp, Process, Memory, invokeChecked, intArg,
// floatArg. It never writes TeamContext/SpotDriver flags or combat outcomes.
function createMechanicsTacticalActions(runtime, management, team,
    geometry, aimBinding, pin, emit) {
  const installed =
    "2df7134a6a9c3a8dbbde88402fc8d16d1d6c3f4c2d5e262bea78c3d78b96dd02";
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
    if (!method.virtualAddress.equals(game.base.add(rva)))
      throw new Error("Installed tactical method changed: " + label);
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
    0x063B5D20, "SpotWeaponData.CurrentAmmo");
  const camera = requireRef(geometry.live && geometry.live.camera,
    "original live Camera");
  if (!same(camera, aimBinding.camera))
    throw new Error("Tactical camera differs from original aim binding");
  const cameraMethod = exact(unity.class("UnityEngine.Camera")
    .method("WorldToScreenPoint", 1), 0x0821F520,
    "Camera.WorldToScreenPoint(Vector3)");
  const autoSend = exact(autoEvent.method("Send", 2), 0x0644B7E0,
    "ChangeAutoModeEvent.Send");
  const tagCtor = exact(tagEvent.method(".ctor", 1), 0x0645A1A0,
    "TagCharacterEvent.ctor");
  const tagSend = exact(tagEvent.method("Send", 0), 0x0645A0B0,
    "TagCharacterEvent.Send");
  const coverCtor = exact(coverEvent.method(".ctor", 1), 0x0644BB70,
    "ChangeForcedCoverEvent.ctor");
  const baseSend = exact(spotEvent.method("Send", 0), 0x06510EE0,
    "SpotEvent.Send");
  const down = exact(driverClass.method("InputPointDown", 0), 0x064A6A60,
    "SpotDriver.InputPointDown");
  const up = exact(driverClass.method("InputPointUp", 0), 0x064A6B40,
    "SpotDriver.InputPointUp");
  const move = exact(driverClass.method("MoveAimPosition", 3), 0x064A6CE0,
    "SpotDriver.MoveAimPosition");
  const getAuto = teamClass.method("get_IsAutoModeAim", 0);
  const getCover = teamClass.method("get_IsForcedCover", 0);
  const getInputType = driverClass.method("get_InputType", 0);
  const getFocused = teamClass.field("_focusedCharacter");
  const inputField = driverClass.field("_inputType");
  const moveLock = driverClass.field("LockMoveAim");
  const inputLock = driverClass.field("LocKIunput");
  for (const [field, offset] of [[teamClass.field("_isAutoModeAim"), 0x28],
      [teamClass.field("_isForcedCover"), 0x2a], [getFocused, 0x20],
      [inputField, 0x10], [moveLock, 0x14], [inputLock, 0x15]])
    if (field.offset !== offset)
      throw new Error("Installed tactical field layout changed: " + field.name);
  const aimEnum = numeric(autoType.field("Aim").value);
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
      nativeAim: actor ? aimBinding.getNativeAimState(id) : null,
      originalAimControlReady: live(aimBinding.aimControl),
      originalCameraReady: live(camera),
      virtualPointer:pointer.snapshot(),
      squad:[...aimBinding.bound].map(([entityId,value])=>({entityId,
        stance:readInt(value.entity.method("get_StanceType",0),value.entity),
        usedAmmoCount:readInt(value.entity.method("get_UsedAmmoCount",0),value.entity)}))
    };
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
    emitAction("set_auto_aim", { enabled, eventRva: "0x0644B7E0" });
    return snapshot();
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
    emitAction("focus", { entityId, position, eventRva: "0x0645A0B0" });
    return snapshot();
  };
  const aimWorld = (entityId, world, log=true) => {
    assertManual("Directed aim");
    if (isLocked(moveLock)) throw new Error("Original SpotDriver aim is locked");
    if (forcedCover()) throw new Error("Cannot direct aim while forced cover is on");
    const actor = actorById(entityId);
    if (focusedId() !== entityId)
      throw new Error("Directed aim requires the original focused actor");
    const xyz = float3(world, "aimWorld");
    const screenPtr = call(cameraMethod, camera, [struct(xyz)]).unbox().handle;
    const screen = [screenPtr.readFloat(), screenPtr.add(4).readFloat(),
      screenPtr.add(8).readFloat()];
    if (screen.some(x => !Number.isFinite(x)) || screen[2] <= 0)
      throw new Error("Original Camera projection is invalid or behind camera");
    const bounds = geometry.screen;
    if (!bounds || !Number.isFinite(bounds.width) ||
        !Number.isFinite(bounds.height) || screen[0] < 0 ||
        screen[0] > bounds.width || screen[1] < 0 ||
        screen[1] > bounds.height)
      throw new Error("Target projects outside original live screen");
    const dt = Number(management.field("_deltaTime").value);
    if (!Number.isFinite(dt) || dt <= 0 || dt > 0.25)
      throw new Error("Original SpotManagement delta time is unavailable");
    pointer.set(screen);
    call(move, driver, [actor.entity.handle,
      struct(screen.slice(0, 2)), floatArg(dt)]);
    const native = aimBinding.getNativeAimState(entityId);
    if (log) emitAction("aim_world", { entityId, world: xyz, screen,
      native, driverRva: "0x064A6CE0" });
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
    emitAction("press", { driverRva: "0x064A6A60",
      teamInputHandlerRva: "0x064EFA40" });
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
    emitAction("release", { driverRva: "0x064A6B40",
      teamInputHandlerRva: "0x064EFA40" });
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
    emitAction("set_cover", { enabled, eventRva: "0x0644BB70",
      handlerRva: "0x0645E970" });
    return snapshot();
  };

  const initial = snapshot();
  if (initial.focusedEntityId === null ||
      !aimBinding.bound.has(initial.focusedEntityId))
    throw new Error("Original focused actor is not bound to live aim geometry");
  emitAction("ready", { initial, originalCommandsOnly: true,
    sourceClientSha256: installed });
  return { snapshot, setAutoAim, focus, aimWorld, press, release, setCover };
}
