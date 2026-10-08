// Original, source-bound Kraken geometry in the isolated Null-graphics player.
// The host supplies MECHANICS_GEOMETRY_SOURCE and its SHA-256; this module does
// not synthesize a camera pose, canvas size, ray, or character target.
// Required globals: Il2Cpp, invokeChecked, intArg, onMain.
// Call start before SpotManagement.OnInit, then finish after process state 2.
// Only the original mechanical presentation controls and their six serialized
// Canvas references are instantiated. The other normal-mode presentations that
// reach Locale_System are omitted.

function startMechanicsGeometryRuntime(management, pin, emit, done) {
  const source = globalThis.MECHANICS_GEOMETRY_SOURCE;
  const receipt = globalThis.MECHANICS_GEOMETRY_SOURCE_SHA256;
  const client = "2df7134a6a9c3a8dbbde88402fc8d16d1d6c3f4c2d5e262bea78c3d78b96dd02";
  const profile=globalThis.MECHANICS_ENCOUNTER_PROFILE||null;
  const mirror=profile&&profile.productId==="anomaly-mirror-container";
  const expectedReceipt = mirror?
    "d1c334def34ae73ed4344c4f79e1f00431f35df49e1fc7eefc562b0c1095f306":
    "fabe414859d5ed3d7486b3ab6b2bc979847c01fa56c793b0832f2c35e33bf2fc";
  const present = x => x != null && !x.isNull();
  const requireRef = (x, name) => { if (!present(x)) throw new Error(name + " is null"); return x; };
  const call = (method, instance = null, args = []) => invokeChecked(method, instance, args);
  if (!source || source.installed_client_sha256 !== client ||
      receipt !== expectedReceipt) {
    throw new Error("Original geometry fixture/client receipt mismatch");
  }
  const backgroundRole=mirror?source.profile.background_role:"kraken_background_hd";
  const backgroundKey=profile?profile.wave.backgroundKey:"sbg_oceanbbg004_001";
  if (!source.bundles||!source.bundles[backgroundRole]||
      source.bundles[backgroundRole].catalog_key!==backgroundKey||
      (mirror&&(source.profile.id!==profile.productId||
        source.profile.wave_id!==profile.encounter.waveId)))
    throw new Error("Registered installed-catalog geometry key mismatch");
  if (!present(management) || typeof pin !== "function" ||
      typeof emit !== "function" || typeof done !== "function") {
    throw new Error("Geometry runtime requires original management, retention and callbacks");
  }
  if (typeof onMain !== "function") throw new Error("Geometry runtime requires main-thread scheduler");
  const runtime = Il2Cpp.domain.assembly("NK.Runtime").image;
  const unity = Il2Cpp.domain.assembly("UnityEngine.CoreModule").image;
  const gameObject = pin(unity.class("UnityEngine.GameObject").alloc());
  call(gameObject.method(".ctor").overload("System.String"), gameObject,
    [Il2Cpp.string("RaidLab.OriginalMechanicsPresentation").handle]);
  management.field("PresentationRoot").value = gameObject;
  const state = { gameObject, management, sourceReceiptSha256: receipt,
    backgroundKey,
    clientSha256: client, status: "loading", startedAt: Date.now(),
    instances: {}, index: 0, task: null, awaiter: null };
  const canvasRefs = {
    overlay_canvas: "_canvasOverlayRef",
    instant_overlay_canvas: "_canvasInstantOverlayRef",
    camera1_canvas: "_canvasCamera1Ref",
    camera2_canvas: "_canvasCamera2Ref",
    popup_canvas: "_canvasPopupRef",
    always_canvas: "_canvasAlwaysRef"
  };
  const bundleRoles = ["ui_canvas_control", ...Object.keys(canvasRefs),
    "character_map", "spot_camera", "auto_camera", "ui_aim", "aim_ui_ref",
    "prefab_root", "monster_controller", "summon_controller", "qte_controller"];
  const componentTypes = {
    ui_canvas_control: "NK.Spot.Presentation.UI.UICanvasControl",
    character_map: "NK.Spot.Presentation.Map.SpotCharacterMap",
    spot_camera: "NK.Spot.Presentation.Camera.SpotCameraControl",
    auto_camera: "NK.Spot.Presentation.Camera.AutoModeCameraController",
    ui_aim: "NK.Spot.Presentation.UI.UIAimControll",
    monster_controller: "NK.Spot.Presentation.MonsterPrefabController",
    summon_controller: "NK.Spot.Presentation.SummonPrefabController",
    qte_controller: "NK.Spot.Presentation.QuickTimeEventPrefabController"
  };
  // Exact Intercept.asset Data[6] ParentObject and children. See
  // AIM-THEME-HIERARCHY.md and MECHANICAL-PRESENTATION-CONTRACT.md; installed
  // theme UnityFS SHA-256 5cbccfdece990facf8eff3f485539c500d21fa30853a66fac676a55bf7032474.
  const supplementalAssets = {
    prefab_root: { key: "PrefabControl", id: "9022068b08512344181fc634755eff39" },
    monster_controller: { key: "MonsterObjectController", id: "ae0ee471e5e1d23458b6b485b5522b0f" },
    summon_controller: { key: "SummonPrefabController", id: "342d3a4ea95847344911914d0d1b0de1" },
    qte_controller: { key: "QuickTimeEventPrefabController", id: "71e8cc9931c3ae7489afb1315a4e4c34" }
  };
  const addressables = Il2Cpp.domain.assembly("NKAddressable").image
    .class("NK.Common.NKAddressables");
  const falseArg = Memory.alloc(1); falseArg.writeU8(0);
  const transform = go => requireRef(call(go.method("get_transform", 0), go),
    "Transform of " + go.class.name);
  const sourceCanvasRefs = source.bundles.ui_canvas_control.components
    .find(item => item.type === "UICanvasControl").fields;
  function originalCanvasReference(role) {
    const fieldName = canvasRefs[role];
    const control = requireRef(state.canvasControl, "UICanvasControl before " + role);
    const reference = requireRef(control.field(fieldName).value, fieldName);
    const guidValue = requireRef(call(reference.method("get_AssetGUID", 0), reference),
      fieldName + ".AssetGUID");
    const guid = new Il2Cpp.String(guidValue.handle).content;
    if (guid !== sourceCanvasRefs[fieldName].m_AssetGUID)
      throw new Error("Original " + fieldName + " GUID differs from installed prefab");
    const runtimeKey = requireRef(call(reference.method("get_RuntimeKey", 0),
      reference), fieldName + ".RuntimeKey");
    const keyText = new Il2Cpp.String(call(runtimeKey.method("ToString", 0),
      runtimeKey).handle).content;
    if (keyText !== guid) throw new Error("Canvas runtime key differs from serialized GUID for " + role);
    return { reference, keyText };
  }
  function originalAimReference() {
    const control = requireRef(state.aimControl, "UIAimControll before AimUI reference");
    const reference = requireRef(control.field("_AimUIRef").value,
      "UIAimControll._AimUIRef");
    const expectedGuid = source.bundles.ui_aim.components
      .find(item => item.type === "UIAimControll")
      .fields._AimUIRef.m_AssetGUID;
    const guidValue = requireRef(call(reference.method("get_AssetGUID", 0), reference),
      "AimUI AssetGUID");
    const guid = new Il2Cpp.String(guidValue.handle).content;
    if (guid !== expectedGuid) throw new Error("Original AimUI GUID differs from installed prefab");
    const runtimeKey = requireRef(call(reference.method("get_RuntimeKey", 0),
      reference), "AimUI RuntimeKey");
    const keyText = new Il2Cpp.String(call(runtimeKey.method("ToString", 0),
      runtimeKey).handle).content;
    if (keyText !== guid) throw new Error("AimUI runtime key differs from serialized GUID");
    return { reference, keyText };
  }
  const originalReference = role => role === "aim_ui_ref" ?
    originalAimReference() : originalCanvasReference(role);
  function registerReference(role, instance) {
    const { reference, keyText } = originalReference(role);
    const guidDictionary = requireRef(management.field("_guidDic").value,
      "SpotManagement GUID dictionary");
    const key = Il2Cpp.string(keyText);
    if (call(guidDictionary.method("ContainsKey", 1), guidDictionary,
      [key.handle]).unbox().handle.readU8())
      throw new Error("Original canvas GUID was already registered: " + role);
    call(guidDictionary.method("set_Item", 2), guidDictionary,
      [key.handle, instance.handle]);
    const resolved = requireRef(call(management.method("GetReferenceGameObject", 1),
      management, [reference.handle]),
      "registered " + role);
    if (!resolved.handle.equals(instance.handle))
      throw new Error("Original reference lookup returned another canvas for " + role);
  }
  function verifyAimHierarchy() {
    const canvasType = Il2Cpp.domain.assembly("UnityEngine.UIModule").image
      .class("UnityEngine.Canvas").type.object;
    const rectType = unity.class("UnityEngine.RectTransform").type.object;
    const overlay = state.instances.overlay_canvas;
    const cameraOne = state.instances.camera1_canvas;
    const aimUi = state.instances.aim_ui_ref;
    const controlGo = state.instances.ui_aim;
    requireRef(call(overlay.method("GetComponent").overload("System.Type"),
      overlay, [rectType.handle]), "overlay Canvas RectTransform");
    requireRef(call(cameraOne.method("GetComponent").overload("System.Type"),
      cameraOne, [rectType.handle]), "camera-one Canvas RectTransform");
    requireRef(call(aimUi.method("GetComponent").overload("System.Type"),
      aimUi, [rectType.handle]), "referenced AimUI RectTransform");
    const overlayCanvas = requireRef(call(overlay.method("GetComponent")
      .overload("System.Type"), overlay, [canvasType.handle]),
      "original overlay Canvas component");
    const cameraOneCanvas = requireRef(call(cameraOne.method("GetComponent")
      .overload("System.Type"), cameraOne, [canvasType.handle]),
      "original camera-one Canvas component");
    if (overlayCanvas.handle.equals(cameraOneCanvas.handle))
      throw new Error("Original overlay and camera-one Canvases are not distinct");
    for (const [name, go, expectedCanvas] of [
      ["AimUI", aimUi, overlayCanvas],
      ["UIAimControll", controlGo, cameraOneCanvas]
    ]) {
      const parentCanvas = requireRef(call(go.method("GetComponentInParent")
        .overload("System.Type"), go, [canvasType.handle]),
        name + " parent Canvas");
      if (!parentCanvas.handle.equals(expectedCanvas.handle))
        throw new Error(name + " resolves the wrong original theme Canvas parent");
    }
    requireRef(state.aimControl.field("_characterAimUis").value,
      "UIAimControll character dictionary");
    requireRef(state.aimControl.field("_characterAimGameObjectss").value,
      "UIAimControll rect dictionary");
    emit({ status: "original_aim_on_init_prerequisites_ready",
      aimUiAssetGuid: "5adcb72651300194487f5d42daa0cf56",
      aimUiOverlayCanvasGuid: "c5bf41344e3c70148902a6763a81c5b7",
      aimControlCameraOneCanvasGuid: "67c58c027fde94a4a84a08b6b2b8f701",
      distinctOriginalCanvases: true, dictionariesAllocated: true });
  }
  function verifyMechanicalHierarchy() {
    const root = state.instances.prefab_root;
    const rootTransform = transform(root);
    for (const role of ["monster_controller", "summon_controller", "qte_controller"]) {
      const childTransform = transform(state.instances[role]);
      const parentTransform = requireRef(call(childTransform.method("get_parent", 0),
        childTransform), role + " parent Transform");
      if (!parentTransform.handle.equals(rootTransform.handle))
        throw new Error(role + " is not under original PrefabControl parent");
    }
    emit({ status: "original_mechanical_prefab_hierarchy_ready",
      parentKey: supplementalAssets.prefab_root.key,
      parentInternalId: supplementalAssets.prefab_root.id,
      childRoles: ["monster_controller", "summon_controller", "qte_controller"] });
  }
  function next() {
    if (typeof firstAsyncFault !== "undefined" && firstAsyncFault)
      throw new Error("Original async presentation fault: " + firstAsyncFault.error);
    if (state.index === bundleRoles.length) {
      verifyAimHierarchy();
      verifyMechanicalHierarchy();
      for (const role of ["ui_canvas_control", "character_map", "spot_camera",
        "auto_camera", "ui_aim", "monster_controller", "summon_controller",
        "qte_controller"]) {
        const go = state.instances[role];
        const concreteType = runtime.class(componentTypes[role]).type.object;
        const component = requireRef(call(go.method("GetComponent")
          .overload("System.Type"), go, [concreteType.handle]),
          "Original component " + componentTypes[role]);
        pin(component);
        // SpotRunner.PresentationInit's original registration callback uses
        // each component's virtual GetPresentationType, not its concrete type.
        const presentationType = requireRef(call(component.method(
          "GetPresentationType", 0), component),
          "presentation type for " + componentTypes[role]);
        call(management.method("RegisterPresentationContext", 2), management,
          [presentationType.handle, component.handle]);
      }
      const dictionary = requireRef(management.field("_presentations").value,
        "Original presentation dictionary");
      const count = call(dictionary.method("get_Count", 0), dictionary)
        .unbox().handle.readS32();
      if (count !== 8) throw new Error("Selective mechanical presentation count " + count + " != 8");
      state.status = "ready";
      state.presentationCount = count;
      emit({ status: "original_mechanical_prefabs_registered", presentationCount: count,
        roles: bundleRoles, managerOnInitPending: true, sceneLoadedByHelper: false,
        sourceReceiptSha256: receipt });
      done(null, state);
      return;
    }
    const role = bundleRoles[state.index];
    const referenceInfo = canvasRefs[role] || role === "aim_ui_ref" ?
      originalReference(role) : null;
    const key = referenceInfo ? referenceInfo.keyText :
      (supplementalAssets[role]?.key || source.bundles[role].catalog_key);
    let parent = gameObject;
    if (canvasRefs[role]) parent = state.instances.ui_canvas_control;
    if (role === "ui_aim") parent = state.instances.camera1_canvas;
    if (role === "aim_ui_ref")
      parent = state.instances.overlay_canvas;
    if (["monster_controller", "summon_controller", "qte_controller"].includes(role))
      parent = state.instances.prefab_root;
    const parentTransform = transform(parent);
    const task = pin(referenceInfo
      ? call(addressables.method("InstantiateAsync")
        .overload("UnityEngine.AddressableAssets.AssetReferenceGameObject",
          "UnityEngine.Transform", "System.Boolean"), null,
        [referenceInfo.reference.handle, parentTransform.handle, falseArg])
      : call(addressables.method("InstantiateAsync")
        .overload("System.String", "UnityEngine.Transform", "System.Boolean"),
        null, [Il2Cpp.string(key).handle, parentTransform.handle, falseArg]));
    state.task = task;
    state.awaiter = pin(call(task.unbox().method("GetAwaiter", 0), task.unbox()));
    emit({ status: "original_mechanical_prefab_load_started", role, key,
      catalogInternalId: supplementalAssets[role]?.id || null,
      ordinal: state.index + 1, total: bundleRoles.length });
  }
  next();
  let pending = false;
  const timer = setInterval(() => {
    if (pending || state.status !== "loading") return;
    pending = true;
    const accepted = onMain(() => {
      pending = false;
      if (state.status !== "loading") return;
      try {
        if (typeof firstAsyncFault !== "undefined" && firstAsyncFault)
          throw new Error("Original async presentation fault: " + firstAsyncFault.error);
        if (Date.now() - state.startedAt > 30000)
          throw new Error("Selective original prefab load pending beyond 30000 ms");
        const awaiter = state.awaiter;
        const doneNow = !!call(awaiter.unbox().method("get_IsCompleted", 0),
          awaiter.unbox()).unbox().handle.readU8();
        if (!doneNow) return;
        const role = bundleRoles[state.index];
        const result = requireRef(call(awaiter.unbox().method("GetResult", 0),
          awaiter.unbox()), "Original prefab " + role);
        state.instances[role] = pin(result);
        if (role === "ui_canvas_control") {
          const type = runtime.class(componentTypes.ui_canvas_control).type.object;
          state.canvasControl = pin(requireRef(call(result.method("GetComponent")
            .overload("System.Type"), result, [type.handle]),
            "Original UICanvasControl component"));
        }
        if (role === "ui_aim") {
          const type = runtime.class(componentTypes.ui_aim).type.object;
          state.aimControl = pin(requireRef(call(result.method("GetComponent")
            .overload("System.Type"), result, [type.handle]),
            "Original UIAimControll component"));
        }
        if (canvasRefs[role] || role === "aim_ui_ref") registerReference(role, result);
        emit({ status: "original_mechanical_prefab_loaded", role,
          key: canvasRefs[role] || role === "aim_ui_ref" ?
            originalReference(role).keyText :
            (supplementalAssets[role]?.key || source.bundles[role].catalog_key),
          catalogInternalId: supplementalAssets[role]?.id || null });
        state.index += 1;
        state.task = null;
        state.awaiter = null;
        next();
        if (state.status === "ready") clearInterval(timer);
      } catch (error) {
        state.status = "failed";
        clearInterval(timer);
        emit({ status: "original_mechanical_prefab_first_failure",
          role: bundleRoles[state.index], error: String(error),
          nativeFrames: error.nativeFrames || [] });
        done(error, state);
      }
    });
    if (accepted === false) pending = false;
  }, 100);
  return state;
}

function finishMechanicsGeometryRuntime(state, management, team, pin, emit) {
  const present = x => x != null && !x.isNull();
  const required = (x, name) => { if (!present(x)) throw new Error("Original " + name + " is null"); return pin(x); };
  const call = (method, instance = null, args = []) => invokeChecked(method, instance, args);
  const count = object => call(object.method("get_Count", 0), object)
    .unbox().handle.readS32();
  if (!state || state.status !== "ready" || state.management !== management ||
      !present(team)) throw new Error("Geometry post-load requires completed original presentation init and team");
  if (typeof firstAsyncFault !== "undefined" && firstAsyncFault)
    throw new Error("Original async presentation fault: " + firstAsyncFault.error);
  const pending = reason => {
    if (state.pendingReason !== reason) {
      state.pendingReason = reason;
      emit({ status: "original_mechanical_geometry_pending", reason });
    }
    return null;
  };
  const dictionary = required(management.field("_presentations").value,
    "presentation dictionary");
  const values = required(call(dictionary.method("get_Values", 0), dictionary),
    "presentation values");
  const iterator = required(call(values.method("GetEnumerator", 0), values),
    "presentation iterator");
  const byName = {};
  for (let i = 0; i <= state.presentationCount; ++i) {
    if (!call(iterator.unbox().method("MoveNext", 0),
      iterator.unbox()).unbox().handle.readU8()) break;
    if (i === state.presentationCount) throw new Error("Presentation enumeration exceeded Count");
    const item = required(call(iterator.unbox().method("get_Current", 0),
      iterator.unbox()),
      "presentation entry");
    const name = item.class.name;
    if (byName[name]) throw new Error("Duplicate original presentation " + name);
    byName[name] = item;
  }
  const map = required(byName.SpotCharacterMap, "SpotCharacterMap");
  const cameraControl = required(byName.SpotCameraControl, "SpotCameraControl");
  const canvasControl = required(byName.UICanvasControl, "UICanvasControl");
  const aimControl = required(byName.UIAimControll, "UIAimControll");
  required(byName.AutoModeCameraController, "AutoModeCameraController");
  required(byName.MonsterPrefabController, "MonsterPrefabController");
  required(byName.SummonPrefabController, "SummonPrefabController");
  required(byName.QuickTimeEventPrefabController, "QuickTimeEventPrefabController");
  for (const [name, value] of Object.entries(byName)) {
    if (!call(value.method("get_IsLoadComplete", 0), value)
      .unbox().handle.readU8()) return pending(name + ".IsLoadComplete=false");
  }
  if (!present(map.field("_spotMap").value))
    return pending("SpotCharacterMap._spotMap not loaded");
  const spotMap = required(map.field("_spotMap").value, "loaded SpotBaseMap");
  const actualMapName = new Il2Cpp.String(call(spotMap.method("GetName", 0),
    spotMap).handle).content;
  const expectedMapName = state.backgroundKey;
  if (actualMapName !== expectedMapName)
    throw new Error("Current original loaded map " + actualMapName +
      " differs from source encounter map " + expectedMapName);
  const cameraList = required(map.field("_cameraList").value,
    "SpotCharacterMap camera list");
  if (count(cameraList) !== 5) throw new Error("Original map camera list is not five");
  const camera = required(cameraControl.field("_spotCamera").value,
    "SpotCameraControl camera");
  required(cameraControl.field("_cinemachineBrain").value,
    "SpotCameraControl CinemachineBrain");
  required(cameraControl.field("_zoomLogic").value,
    "SpotCameraControl zoom logic");
  const overlayCanvas = required(call(canvasControl.method("GetOverlayCanvas", 0),
    canvasControl), "UICanvasControl overlay canvas");
  const canvasRect = required(aimControl.field("_parentRect").value,
    "UIAimControll parent RectTransform");
  required(aimControl.field("_parentCanvas").value,
    "UIAimControll parent Canvas");
  if (!present(aimControl.field("_characterAimUis").value))
    return pending("UIAimControll._characterAimUis not allocated");
  const aimUis = required(aimControl.field("_characterAimUis").value,
    "UIAimControll character dictionary");
  if (count(aimUis) < 5) return pending("UIAimControll has " + count(aimUis) + "/5 targets");
  if (count(aimUis) !== 5) throw new Error("Original UIAim count exceeds five");
  const aimValues = required(call(aimUis.method("get_Values", 0), aimUis),
    "UIAim values");
  const aimIterator = required(call(aimValues.method("GetEnumerator", 0),
    aimValues), "UIAim iterator");
  const actors = [];
  for (let i = 0; i < 6; ++i) {
    if (!call(aimIterator.unbox().method("MoveNext", 0), aimIterator.unbox())
      .unbox().handle.readU8()) break;
    if (i === 5) throw new Error("Original UIAim enumeration exceeds five");
    const uiAim = required(call(aimIterator.unbox().method("get_Current", 0),
      aimIterator.unbox()), "UIAim entry");
    const entity = required(uiAim.field("_target").value,
      "UIAim target at " + i);
    required(uiAim.field("_rectTransform").value,
      "UIAim rect at " + i);
    const entityId = Number(entity.field("Id").value);
    if (!Number.isInteger(entityId) || entityId <= 0)
      throw new Error("Original UIAim target ID invalid at " + i);
    actors.push({ entity, entityId, uiAim });
  }
  if (actors.length !== 5 || new Set(actors.map(x => x.entityId)).size !== 5)
    throw new Error("Original UIAim targets are not five distinct characters");
  const unity = Il2Cpp.domain.assembly("UnityEngine.CoreModule").image;
  const screenClass = unity.class("UnityEngine.Screen");
  const width = call(screenClass.method("get_width", 0)).unbox().handle.readS32();
  const height = call(screenClass.method("get_height", 0)).unbox().handle.readS32();
  const safeHandle = call(screenClass.method("get_safeArea", 0)).unbox().handle;
  const safeArea = [0, 4, 8, 12].map(offset =>
    safeHandle.add(offset).readFloat());
  if (width <= 0 || height <= 0) throw new Error("Original Unity screen dimensions invalid");
  const geometry = { installedDllSha256: state.clientSha256,
    sourceReceiptSha256: state.sourceReceiptSha256,
    screen: { width, height, safeArea },
    live: { camera, cameraControl, overlayCanvas, canvasRect, map,
      aimControl, actors } };
  emit({ status: "original_geometry_ready", mapName: actualMapName,
    sourceReceiptSha256: state.sourceReceiptSha256,
    presentationCount: count(dictionary), cameraCount: count(cameraList),
    aimedCharacterCount: actors.length, actorIds: actors.map(x => x.entityId),
    screen: geometry.screen, sceneLoadedByHelper: false,
    originalMapMethodRva: "0x06300230",
    originalCameraMethodRva: "0x06311820" });
  return geometry;
}
