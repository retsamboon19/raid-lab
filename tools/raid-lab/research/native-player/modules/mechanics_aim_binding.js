// Live original aim binding for the private Unity mechanics host.
// GameAssembly SHA-256: 2df7134a6a9c3a8dbbde88402fc8d16d1d6c3f4c2d5e262bea78c3d78b96dd02.
// Run on Unity's main thread after original map/camera/UI aim initialization and
// character LoadAim completion, before the first battle tick. This helper does
// not create, replace, disable, or register presentation objects: their native
// UpdateTick and resource-load behavior must remain the game's own behavior.
// Required globals: Il2Cpp, Memory, invokeChecked, intArg, onMain.
// geometry={installedDllSha256,sourceReceiptSha256,screen:{width,height,
// safeArea:[x,y,w,h]},live:{camera,cameraControl,overlayCanvas,aimControl,
// actors:[{entity,entityId}]}}. All live refs come from the original loaded
// SpotCharacterMap/SpotCameraControl/UICanvasControl/UIAimControll lifecycle.
function prepareMechanicsAimBinding(runtime, unity, management, team, geometry, pin, emit) {
  const present = value => value != null && !value.isNull();
  const requireObject = (value, name) => {
    if (!present(value)) throw new Error("Original aim dependency missing: " + name);
    return pin(value);
  };
  const requireFinite = (value, name) => {
    if (typeof value !== "number" || !Number.isFinite(value))
      throw new Error("Original aim measurement missing: " + name);
    return value;
  };
  const call = (method, instance = null, args = []) =>
    invokeChecked(method, instance, args);
  const readBool = (method, instance) =>
    !!call(method, instance).unbox().handle.readU8();
  const readInt = (method, instance) =>
    call(method, instance).unbox().handle.readS32();
  const readVector3 = value => {
    const p = value.unbox().handle;
    return [p.readFloat(), p.add(4).readFloat(), p.add(8).readFloat()];
  };
  const vectorArg = values => {
    if (!Array.isArray(values) || values.length !== 3)
      throw new Error("Original MoveAim requires an explicit Vector3 screen position");
    const p = Memory.alloc(12);
    values.forEach((value, index) =>
      p.add(index * 4).writeFloat(requireFinite(value, "screenPosition[" + index + "]")));
    return p;
  };
  const same = (a, b) => present(a) && present(b) && a.handle.equals(b.handle);
  const intValue = value => typeof value === "number" ? value :
    Number(value.field("value__").value);

  if (!geometry || geometry.installedDllSha256 !==
      "2df7134a6a9c3a8dbbde88402fc8d16d1d6c3f4c2d5e262bea78c3d78b96dd02")
    throw new Error("Live aim geometry is not bound to installed GameAssembly");
  if (!/^[0-9a-f]{64}$/.test(geometry.sourceReceiptSha256 || ""))
    throw new Error("Live aim geometry requires exact source receipt SHA-256");
  if (typeof pin !== "function" || typeof emit !== "function" ||
      typeof onMain !== "function")
    throw new Error("Aim binding requires pin, emit, and onMain callbacks");
  requireObject(management, "SpotManagement");
  requireObject(team, "TeamContext");
  const live = geometry.live || {};
  const camera = requireObject(live.camera, "live.Camera");
  const cameraControl = requireObject(live.cameraControl,
    "live.SpotCameraControl post InitCamera");
  const overlayCanvas = requireObject(live.overlayCanvas,
    "live.UICanvasControl overlay Canvas");
  const aimControl = requireObject(live.aimControl,
    "live.UIAimControll post OnInit/LoadAim");
  const actors = live.actors;
  if (!Array.isArray(actors) || actors.length !== 5)
    throw new Error("Live aim binding requires five original loaded characters");

  // SpotCameraControl.UpdateTick RVA 0x06313A20 calls the original
  // CinemachineBrain.ManualUpdate and CameraZoomLogic.Update. A copied Camera
  // pose or an uninitialized control would lose focus/zoom and can null-deref.
  if (!same(cameraControl.field("_spotCamera").value, camera))
    throw new Error("SpotCameraControl does not own the live Camera");
  requireObject(cameraControl.field("_cinemachineBrain").value,
    "SpotCameraControl._cinemachineBrain");
  requireObject(cameraControl.field("_zoomLogic").value,
    "SpotCameraControl._zoomLogic");
  if (!same(aimControl.field("_teamContext").value, team))
    throw new Error("UIAimControll is not bound to the original TeamContext");
  requireObject(aimControl.field("_parentRect").value,
    "UIAimControll._parentRect");
  requireObject(aimControl.field("_aimUIParentCanvas").value,
    "UIAimControll._aimUIParentCanvas");
  requireObject(aimControl.field("_parentCanvas").value,
    "UIAimControll._parentCanvas");
  const aimRects = requireObject(aimControl.field("_characterAimGameObjectss").value,
    "UIAimControll._characterAimGameObjectss");
  const aimUis = requireObject(aimControl.field("_characterAimUis").value,
    "UIAimControll._characterAimUis");

  // Original presentation registry and load gate are observed, not changed.
  const cameraControlClass = runtime.class(
    "NK.Spot.Presentation.Camera.SpotCameraControl");
  const aimControlClass = runtime.class(
    "NK.Spot.Presentation.UI.UIAimControll");
  const presentations = requireObject(management.field("_presentations").value,
    "SpotManagement._presentations");
  for (const [klass, object] of [[cameraControlClass, cameraControl],
    [aimControlClass, aimControl]]) {
    const registered = call(presentations.method("get_Item", 1), presentations,
      [klass.type.object.handle]);
    if (!same(registered, object))
      throw new Error("Original presentation registration mismatch: " + klass.name);
  }
  const presentationBase = runtime.class(
    "NK.Spot.Presentation.Common.PresentationBase");
  if (!readBool(presentationBase.method("get_IsLoadComplete", 0), cameraControl) ||
      !readBool(presentationBase.method("get_IsLoadComplete", 0), aimControl))
    throw new Error("Original aim presentations have not completed OnLoadAsync");
  if (!readBool(management.method("IsResourceLoad", 0), management))
    throw new Error("Original SpotManagement resource gate remains pending");

  // The live UIAim dictionaries must contain the same five game entities.
  // UIAimControll.UpdateTick RVA 0x06233FC0 calls each UIAim.UpdateTick;
  // UIAim.UpdateTick RVA 0x062297D0 can call WeaponLogic.TryFireTarget. A
  // targetless synthetic UIAim would silently remove combat firing.
  const bound = new Map();
  for (const item of actors) {
    const entity = requireObject(item.entity, "actor.entity");
    const id = intValue(entity.field("Id").value);
    if (id !== requireFinite(item.entityId, "actor.entityId") || bound.has(id))
      throw new Error("Original actor/entity identity mismatch: " + id);
    const info = requireObject(entity.field("_entityInfo").value,
      "actor._entityInfo");
    const aimInfo = requireObject(call(entity.method("GetAimInfo", 0), entity),
      "actor.GetAimInfo");
    if (!same(aimInfo.field("_aimControl").value, aimControl))
      throw new Error("Original AimInfo control mismatch for " + id);
    const rect = requireObject(call(aimRects.method("get_Item", 1), aimRects,
      [intArg(id)]), "original GameAim RectTransform " + id);
    const uiAim = requireObject(call(aimUis.method("get_Item", 1), aimUis,
      [intArg(id)]), "original UIAim " + id);
    requireObject(uiAim.field("_rectTransform").value,
      "UIAim._rectTransform " + id);
    if (!same(uiAim.field("_target").value, entity))
      throw new Error("Original UIAim target mismatch for " + id);
    if (!same(uiAim.field("_control").value, aimControl))
      throw new Error("Original UIAim controller mismatch for " + id);
    bound.set(id, { entity, info, aimInfo, rect, uiAim });
  }

  const screen = geometry.screen || {};
  const screenClass = unity.class("UnityEngine.Screen");
  const width = readInt(screenClass.method("get_width", 0));
  const height = readInt(screenClass.method("get_height", 0));
  if (width !== requireFinite(screen.width, "screen.width") ||
      height !== requireFinite(screen.height, "screen.height"))
    throw new Error("Original live screen dimensions changed");
  const safeAreaPtr = call(screenClass.method("get_safeArea", 0)).unbox().handle;
  const safeArea = [0, 4, 8, 12].map(offset => safeAreaPtr.add(offset).readFloat());
  if (!Array.isArray(screen.safeArea) || screen.safeArea.length !== 4 ||
      screen.safeArea.some((value, index) =>
        Math.abs(requireFinite(value, "screen.safeArea[" + index + "]") -
          safeArea[index]) > 0.0001))
    throw new Error("Original live Screen.safeArea changed");
  const ratio = [aimControl.handle.add(0xa0).readFloat(),
    aimControl.handle.add(0xa4).readFloat()];
  const margins = [0xb0, 0xb4, 0xb8, 0xbc]
    .map(offset => aimControl.handle.add(offset).readFloat());
  if (ratio.some(value => !Number.isFinite(value) || value <= 0) ||
      margins.some(value => !Number.isFinite(value)))
    throw new Error("Original UIAimControll.SetCanvasData has invalid output");

  const moveType = intValue(runtime.class("NK.Spot.Common.SpotEvent")
    .nested("SpotEventType")
    .field("MoveAimToScreenPosition").value);
  const actions = requireObject(management.field("_spotEvents").value,
    "SpotManagement._spotEvents");
  const action = requireObject(call(actions.method("get_Item", 1), actions,
    [intArg(moveType)]), "original MoveAim event action");
  requireObject(action.field("SpotEvent").value,
    "original MoveAim observer registered by UIAimControll.OnInit");
  const moveEvent = runtime.class(
    "NK.Spot.Event.Character.Aim.MoveAimToScreenPosition");
  const aimLogic = runtime.class("NK.Spot.Logic.Character.AimLogic");
  const readUiAim = id => readVector3(call(aimControl.method("GetAimPosition", 1),
    aimControl, [intArg(id)]));
  const nativeAimState = id => {
    const actor = bound.get(id);
    if (!actor) throw new Error("Native aim actor not bound: " + id);
    return {
      uiAimPosition: readVector3(call(actor.aimInfo.method(
        "get_UIAimPosition", 0), actor.aimInfo)),
      logicAimPosition: readVector3(call(aimLogic.method("GetAimPosition", 1),
        null, [actor.aimInfo.handle])),
      logicAimDirection: readVector3(call(aimLogic.method("GetAimDirection", 1),
        null, [actor.aimInfo.handle]))
    };
  };
  const moveAimNow = (id, screenPosition) => {
    const actor = bound.get(id);
    if (!actor) throw new Error("MoveAim actor not bound: " + id);
    const before = readUiAim(id);
    // This sends the original pooled SpotEvent; the observer installed by the
    // original UIAimControll.OnInit executes OnMoveAimToScreenPosition
    // (0x062327B0), then OnChangedAim (0x06230560).
    call(moveEvent.method("Send", 2), null,
      [actor.info.handle, vectorArg(screenPosition)]);
    const after = readUiAim(id);
    const native = nativeAimState(id);
    emit({ phase: "mechanics_aim_binding", status: "original_move_aim_sent",
      entityId: id, screenPosition, before, after, native,
      originalSendRva: "0x06453570", originalHandlerRva: "0x062327B0",
      originalChangedAimRva: "0x06230560" });
    return native;
  };
  emit({ phase: "mechanics_aim_binding", status: "live_original_binding_verified",
    entityCount: bound.size, screen: { width, height, safeArea },
    originalSetCanvasDataOutput: { ratio, margins },
    cameraControlTickRva: "0x06313A20", uiAimControlTickRva: "0x06233FC0",
    uiAimTickRva: "0x062297D0", resourceGateRva: "0x061491A0",
    presentationObjectsCreated: 0, presentationRegistryMutated: false,
    originalResourceGatePassed: true });
  return { camera, cameraControl, overlayCanvas, aimControl, bound,
    getAimPosition: readUiAim, getNativeAimState: nativeAimState,
    moveAimNow, moveAim: (id, position) => onMain(() => moveAimNow(id, position)) };
}
