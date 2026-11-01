// Current153 captured-auto aim verification; runtime validation pending.
const PRACTICE_AIM_CONTRACT = {"clientSha256":"d39896d3770888039c728a1908448c3db5efa7cdf874c90d56f46d8d566428d2","metadataSha256":"58933dbe6080485c5270a127a2fe5e83070c035e7660d0a22227bf2acb41a741","methods":[{"className":"NK.Spot.Presentation.UI.UIAimControll","name":"OnInit","count":0,"rva":92076624},{"className":"NK.Spot.Presentation.UI.UIAimControll","name":"UpdateTick","count":1,"rva":92088272},{"className":"NK.Spot.Presentation.UI.UIAimControll","name":"GetAimPosition","count":1,"rva":92066864},{"className":"NK.Spot.Presentation.Camera.SpotCameraControl","name":"UpdateTick","count":1,"rva":103042432},{"className":"NK.Spot.Presentation.UI.UIAim","name":"UpdateTick","count":1,"rva":92106336},{"className":"NK.Spot.SpotManagement","name":"IsResourceLoad","count":0,"rva":123749968},{"className":"NK.Spot.Logic.Character.AimLogic","name":"GetAimPosition","count":1,"rva":112921280},{"className":"NK.Spot.Logic.Character.AimLogic","name":"GetAimDirection","count":1,"rva":112920944}],"fields":[{"name":"_screenToCanvasRatio","offset":160,"type":"UnityEngine.Vector2"},{"name":"_safeAreaTop","offset":176,"type":"System.Single"},{"name":"_safeAreaBottom","offset":180,"type":"System.Single"},{"name":"_safeAreaLeft","offset":184,"type":"System.Single"},{"name":"_safeAreaRight","offset":188,"type":"System.Single"}]};
// Live original aim binding for the private Unity mechanics host.
// GameAssembly SHA-256: d39896d3770888039c728a1908448c3db5efa7cdf874c90d56f46d8d566428d2.
// Run on Unity's main thread after original map/camera/UI aim initialization and
// character LoadAim completion, before the first battle tick. This helper does
// not create, replace, disable, or register presentation objects: their native
// UpdateTick and resource-load behavior must remain the game's own behavior.
// Required globals: Il2Cpp, Memory, invokeChecked, intArg, onMain.
// geometry={installedDllSha256,sourceReceiptSha256,screen:{width,height,
// safeArea:[x,y,w,h]},live:{camera,cameraControl,overlayCanvas,aimControl,
// actors:[{entity,entityId}]}}. All live refs come from the original loaded
// SpotCharacterMap/SpotCameraControl/UICanvasControl/UIAimControll lifecycle.
function verifyPracticeAimBinding(runtime, unity, management, team, geometry, pin, emit) {
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
  const same = (a, b) => present(a) && present(b) && a.handle.equals(b.handle);
  const intValue = value => typeof value === "number" ? value :
    Number(value.field("value__").value);

  if (!geometry || geometry.installedDllSha256 !==
      "d39896d3770888039c728a1908448c3db5efa7cdf874c90d56f46d8d566428d2")
    throw new Error("Live aim geometry is not bound to installed GameAssembly");
  if (!/^[0-9a-f]{64}$/.test(geometry.sourceReceiptSha256 || ""))
    throw new Error("Live aim geometry requires exact source receipt SHA-256");
  if (typeof pin !== "function" || typeof emit !== "function" ||
      typeof onMain !== "function")
    throw new Error("Aim binding requires pin, emit, and onMain callbacks");
  requireObject(management, "SpotManagement");
  requireObject(team, "TeamContext");
  for (const row of PRACTICE_AIM_CONTRACT.methods) {
    const method=runtime.class(row.className).method(row.name,row.count);
    if (Number(method.relativeVirtualAddress)!==row.rva)
      throw new Error('Current153 original aim method changed: '+row.className+'.'+row.name);
  }
  for (const row of PRACTICE_AIM_CONTRACT.fields) {
    const field=runtime.class('NK.Spot.Presentation.UI.UIAimControll').field(row.name);
    if (field.offset!==row.offset || field.type.name!==row.type || field.isStatic)
      throw new Error('Current153 original aim field changed: '+row.name);
  }
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

  // SpotCameraControl.UpdateTick RVA 0x06244D80 calls the original
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
  // UIAimControll.UpdateTick RVA 0x057D27D0 calls each UIAim.UpdateTick;
  // UIAim.UpdateTick RVA 0x057D6E60 can call WeaponLogic.TryFireTarget. A
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
  emit({ phase: "mechanics_aim_binding", status: "live_original_binding_verified",
    entityCount: bound.size, screen: { width, height, safeArea },
    originalSetCanvasDataOutput: { ratio, margins },
    cameraControlTickRva: "0x06244D80", uiAimControlTickRva: "0x057D27D0",
    uiAimTickRva: "0x057D6E60", resourceGateRva: "0x07604650",
    presentationObjectsCreated: 0, presentationRegistryMutated: false,
    originalResourceGatePassed: true });
  return { camera, cameraControl, overlayCanvas, aimControl, bound,
    getAimPosition: readUiAim, getNativeAimState: nativeAimState };
}
