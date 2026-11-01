// Current153 original ShootingRange geometry loading candidate.
// Seventeen source-bound mechanical controls; runtime coverage remains unverified.
// Original native InstantiateAsync/registration/OnLoad/camera/aim methods run.
// Required globals: Il2Cpp, invokeChecked, intArg, onMain, source receipt.
function resolveOriginalPracticePopupAsset(source,popupSource) {
  const layers=source.hierarchy.filter(row=>row.parent_asset.primary_key==='Canvas(Screen Space - Overlay) - Popup');
  if(layers.length!==1)throw Error('Original popup Canvas theme is missing/ambiguous');
  const layer=layers[0];
  const matches=layer.children.flatMap(child=>child.asset_rows
    .filter(row=>row.primary_key===popupSource.selectedAsset.primary_key&&row.asset_type==='UnityEngine.GameObject')
    .map(row=>({key:child.asset_guid,id:row.internal_id,parent:layer.parent_guid})));
  if(matches.length!==1||matches[0].key!==popupSource.catalogKey||
      matches[0].id!==popupSource.selectedAsset.internal_id||matches[0].parent!==popupSource.parentGuid)
    throw Error('Original loading-page popup theme selection differs');
  return matches[0];
}
function verifyOriginalPracticePopupRegistration(control,count) {
  if(count!==17||control?.class?.type?.name!=='NK.Spot.Presentation.UI.UIPopupControll')
    throw Error('Original loading-page popup registration/count differs');
  for(const [name,rva,returns,args] of [['OnInit',0x05b34f50,'System.Void',[]],['OnRelease',0x056963a0,'System.Void',[]],
    ['HideLoading',0x05b34ec0,'Cysharp.Threading.Tasks.UniTask',[]],
    ['OnPlayStateChange',0x05b35020,'System.Void',['NK.Spot.Common.SpotEvent']]]) {
    const method=control.method(name,args.length);
    if(Number(method.relativeVirtualAddress)!==rva||method.isStatic||
        method.returnType.name!==returns||method.parameters.map(p=>p.type.name).join('|')!==args.join('|'))
      throw new Error('Original loading-page popup native lifecycle differs: '+name);
  }
  return control;
}
function verifyOriginalPracticeCutsceneReferences(control,binding,liveComponent,call,pin,emit) {
  if(control?.class?.type?.name!==binding?.componentType ||
      binding.componentType!=='NK.Spot.Presentation.UI.CutSceneControl')
    throw new Error('Original CutSceneControl component type differs');
  for(const spec of binding.fieldLayouts) {
    const field=control.field(spec.name);
    if(field.offset!==spec.offset||field.type.name!==spec.type||field.isStatic)
      throw new Error('Original CutSceneControl field differs: '+spec.name);
  }
  for(const name of ['OnInit','OnLoading','OnRelease','UpdateTick'])
    if(Number(control.method(name,name==='UpdateTick'?1:0).relativeVirtualAddress)!==binding.originalMethodRvas[name])
      throw new Error('Original CutSceneControl method differs: '+name);
  const intro=liveComponent(control.field('_introCutScene').value,'UnityEngine.Playables.PlayableDirector','serialized intro director');
  const ui=liveComponent(control.field('_introCutSceneUI').value,'UnityEngine.Playables.PlayableDirector','serialized intro UI director');
  const uiObject=liveComponent(control.field('_introCutSceneUIObject').value,'UnityEngine.GameObject','serialized intro UI object');
  if(intro.handle.equals(ui.handle))throw new Error('Original intro and UI directors must be distinct');
  const getter=intro.method('get_duration',0);
  if(Number(getter.relativeVirtualAddress)!==binding.directorDurationGetter.rva)
    throw new Error('Original PlayableDirector duration getter differs');
  const duration=call(getter,intro).unbox().handle.readDouble();
  const buffer=new ArrayBuffer(4);new DataView(buffer).setFloat32(0,duration,true);
  const durationBits=Array.from(new Uint8Array(buffer),x=>x.toString(16).padStart(2,'0')).join('');
  if(!Number.isFinite(duration)||duration<=0||durationBits!==binding.expectedIntroDurationFloat32BitsLE)
    throw new Error('Original serialized intro duration differs from source/native observation');
  if(Number(control.field('_skipSpeed').value)!==binding.serializedSkipSpeed)
    throw new Error('Original serialized intro skip speed differs');
  const boards=control.field('_modeBoard').value;
  if(boards==null||boards.isNull()||boards.length!==binding.serializedModeBoardCount)
    throw new Error('Original serialized mode board array differs');
  for(let i=0;i<boards.length;i++)liveComponent(boards.get(i),'UnityEngine.GameObject','serialized intro mode board '+i);
  pin(control);
  emit({status:'original_cutscene_controller_prerequisites_verified',componentType:binding.componentType,
    introDirectorType:intro.class.type.name,uiDirectorType:ui.class.type.name,
    originalIntroDuration:duration,introDurationFloat32BitsLE:durationBits,
    modeBoardCount:boards.length,sourceReceiptSha256:globalThis.PRACTICE_CUTSCENE_CONTROL_SOURCE_SHA256,
    beforeManagerOnInit:true,serializedReferencesWritten:false,managerIntroDurationWrittenByHost:false,
    originalOnLoadingOwnsDurationAndPlayback:true});
  return {control,intro,ui,uiObject,originalDuration:duration,durationBits};
}
function startPracticeGeometryRuntime(management, pin, emit, done) {
  const source = globalThis.MECHANICS_GEOMETRY_SOURCE;
  const receipt = globalThis.MECHANICS_GEOMETRY_SOURCE_SHA256;
  const client = "d39896d3770888039c728a1908448c3db5efa7cdf874c90d56f46d8d566428d2";
  const present = x => x != null && !x.isNull();
  const requireRef = (x, name) => { if (!present(x)) throw new Error(name + " is null"); return x; };
  const call = (method, instance = null, args = []) => invokeChecked(method, instance, args);
  if (!source || source.installed_client_sha256!==client ||
      receipt!=="ff3d69914a3735a7bd9de5493e687af30b8ef4b9ad35845e7446c19533435449" || source.theme_mode!==9 || source.theme_key!==0 ||
      source.bundles.practice_background_hd.catalog_key!=="sbg_tower_001")
    throw new Error("Exact153 normal ShootingRange geometry source binding changed");
  const backgroundKey="sbg_tower_001";
  const extra=globalThis.PRACTICE_ADDITIONAL_GEOMETRY_SOURCE;
  if (!extra || extra.source.clientSha256!==client ||
      globalThis.PRACTICE_ADDITIONAL_GEOMETRY_SOURCE_SHA256!==
        '4ae06a243b0674752f5f68ba45a5f84d837efcea5ecffb9c32f8e9c4ba4747bd' ||
      globalThis.NATIVE153_BINDING?.practiceResourceReceiptSha256!==
        '29c9687da1ab0f66ac6bc56f96590ed3bbab1cb9f54cc5ac747be5f13b793170')
    throw new Error('Current practice controller prefab/source receipt absent');
  const fxSource=globalThis.PRACTICE_FX_CONTROLLER_SOURCE;
  const timelineSource=globalThis.PRACTICE_TIMELINE_CONTROLLER_SOURCE;
  if (fxSource?.clientSha256!==client || timelineSource?.clientSha256!==client ||
      globalThis.PRACTICE_FX_CONTROLLER_SOURCE_SHA256!==
        '76141c9385c5854d2e92e11458d94d6fe8cbcf50962a2c1a98f45ca6b2caf3e9' ||
      globalThis.PRACTICE_TIMELINE_CONTROLLER_SOURCE_SHA256!==
        '55be446ab887db2ced8c470c9dbc94946a5b77bf1eb5681969baf89161f80b73')
    throw new Error('Current original FX/timeline source receipts absent');
  const graphicSource=globalThis.PRACTICE_GRAPHIC_OPTIONS_SOURCE;
  if (graphicSource?.clientSha256!==client ||
      globalThis.PRACTICE_GRAPHIC_OPTIONS_SOURCE_SHA256!==
        '6642fcf5e8aebbde638ded07753884a84b17cdc063a3f5d4a1c1cecb4e9788ea')
    throw new Error('Current original graphics-options source receipt absent');
  const cutsceneSource=globalThis.PRACTICE_CUTSCENE_CONTROL_SOURCE;
  if(cutsceneSource?.clientSha256!==client||
      globalThis.PRACTICE_CUTSCENE_CONTROL_SOURCE_SHA256!==
        'eae1d9b0bbccf92750e8ba80617346d0ec9f9024ad06e7c602a7b81fa4686936')
    throw new Error('Current original mechanical intro source receipt absent');
  const popupSource=globalThis.PRACTICE_POPUP_CONTROL_SOURCE;
  if(popupSource?.clientSha256!==client||
      globalThis.PRACTICE_POPUP_CONTROL_SOURCE_SHA256!==
        'b7abd4f46e21ef1f244746bebfa11300798380de9312f50e82a695007a14d469')
    throw new Error('Current original loading-page popup source receipt absent');
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
    commonGeometryReceiptSha256:receipt,
    backgroundKey,
    clientSha256: client, status: "loading", startedAt: Date.now(),
    instances: {}, components: {}, index: 0, task: null, awaiter: null };
  const canvasRefs = {
    overlay_canvas: "_canvasOverlayRef",
    instant_overlay_canvas: "_canvasInstantOverlayRef",
    camera1_canvas: "_canvasCamera1Ref",
    camera2_canvas: "_canvasCamera2Ref",
    popup_canvas: "_canvasPopupRef",
    always_canvas: "_canvasAlwaysRef"
  };
  const bundleRoles = ["ingame_root", "ui_canvas_control", ...Object.keys(canvasRefs),
    "character_map", "spot_camera", "auto_camera", "ui_aim", "aim_ui_ref",
    "prefab_root", "monster_controller", "summon_controller", "qte_controller",
    "character_controller", "projectile_controller", "dynamic_controller", "skill_director",
    "fx_controller", "timeline_controller", "graphic_options", "cutscene_control", "popup_control"];
  const componentTypes = {
    ui_canvas_control: "NK.Spot.Presentation.UI.UICanvasControl",
    character_map: "NK.Spot.Presentation.Map.SpotCharacterMap",
    spot_camera: "NK.Spot.Presentation.Camera.SpotCameraControl",
    auto_camera: "NK.Spot.Presentation.Camera.AutoModeCameraController",
    ui_aim: "NK.Spot.Presentation.UI.UIAimControll",
    monster_controller: "NK.Spot.Presentation.MonsterPrefabController",
    summon_controller: "NK.Spot.Presentation.SummonPrefabController",
    qte_controller: "NK.Spot.Presentation.QuickTimeEventPrefabController",
    character_controller: "NK.Spot.Presentation.SpineCharacterPrefabController",
    projectile_controller: "NK.Spot.Presentation.ProjectilePrefabController",
    dynamic_controller: "NK.Spot.Presentation.DynamicObjectPrefabController",
    skill_director: "NK.Spot.Presentation.SkillDirecting.SkillDirector",
    fx_controller: "NK.Spot.Presentation.FXController",
    timeline_controller: "NK.Spot.Presentation.SpotTimelineController",
    graphic_options: "NK.Spot.Presentation.SpotGraphicOptions",
    cutscene_control: "NK.Spot.Presentation.UI.CutSceneControl",
    popup_control: "NK.Spot.Presentation.UI.UIPopupControll"
  };
  // Resolve each selected mechanical object from this exact practice theme.
  // Script identities/serialized fields of the four added controls are in
  // practice-mechanical-resources1.json serializedAssets, hash checked above.
  function themeParent(key) {
    const rows=source.hierarchy.filter(layer=>layer.parent_asset.primary_key===key);
    if (rows.length!==1 || rows[0].parent_asset.asset_type!=="UnityEngine.GameObject")
      throw new Error("Missing/ambiguous original practice parent "+key);
    return rows[0];
  }
  const ingameLayer=themeParent("IngameObject"), prefabLayer=themeParent("PrefabControl");
  function themeChild(layer,key) {
    const matches=layer.children.flatMap(child=>child.asset_rows
      .filter(row=>row.primary_key===key && row.asset_type==="UnityEngine.GameObject")
      .map(row=>({key:child.asset_guid,id:row.internal_id,parent:layer.parent_guid})));
    if (matches.length!==1) throw new Error("Missing/ambiguous original practice child "+key);
    return matches[0];
  }
  const supplementalAssets = {
    ingame_root:{key:ingameLayer.parent_guid,id:ingameLayer.parent_asset.internal_id},
    prefab_root:{key:prefabLayer.parent_guid,id:prefabLayer.parent_asset.internal_id},
    monster_controller:themeChild(prefabLayer,"MonsterObjectController"),
    summon_controller:themeChild(prefabLayer,"SummonPrefabController"),
    qte_controller:themeChild(prefabLayer,"QuickTimeEventPrefabController")
  };
  for (const role of ['character_controller','projectile_controller','dynamic_controller','skill_director']) {
    const row=extra.bundles[role];
    const selection=themeChild(role==='skill_director'?ingameLayer:prefabLayer,
      row.selected_asset.primary_key);
    if (selection.id!==row.selected_asset.internal_id || selection.key!==row.catalog_key)
      throw new Error('Current practice extra controller theme selection differs: '+role);
    supplementalAssets[role]=selection;
  }
  const fxRow=fxSource.bundles.fx_controller;
  const graphicSelection=themeChild(ingameLayer,graphicSource.selectedAsset.primary_key);
  if (graphicSelection.key!==graphicSource.catalogKey ||
      graphicSelection.id!==graphicSource.selectedAsset.internal_id ||
      graphicSelection.parent!==graphicSource.parentGuid)
    throw new Error('Original graphics-options theme selection differs');
  supplementalAssets.graphic_options=graphicSelection;
  const cutsceneSelection=themeChild(ingameLayer,cutsceneSource.selectedAsset.primary_key);
  if(cutsceneSelection.key!==cutsceneSource.catalogKey||
      cutsceneSelection.id!==cutsceneSource.selectedAsset.internal_id||
      cutsceneSelection.parent!==cutsceneSource.parentGuid)
    throw new Error('Original mechanical intro theme selection differs');
  supplementalAssets.cutscene_control=cutsceneSelection;
  supplementalAssets.popup_control=resolveOriginalPracticePopupAsset(source,popupSource);
  const timelineRows=timelineSource.catalogRows;
  if (timelineRows.length!==1) throw new Error('Ambiguous original timeline source');
  for (const [role,row,key] of [
    ['fx_controller',fxRow.selected_asset,fxRow.catalog_key],
    ['timeline_controller',timelineRows[0],timelineSource.catalogKey]
  ]) {
    const selection=themeChild(prefabLayer,row.primary_key);
    if (selection.id!==row.internal_id || selection.key!==key)
      throw new Error('Original FX/timeline theme differs: '+role);
    supplementalAssets[role]=selection;
  }
  for (const role of ["ui_canvas_control","character_map","spot_camera","auto_camera"]) {
    const row=source.bundles[role];
    const nativeChild=themeChild(ingameLayer,row.catalog_key);
    if (nativeChild.id!==row.selected_asset.internal_id)
      throw new Error("Practice theme child differs from serialized source "+role);
  }
  const aimLayer=source.hierarchy.find(layer=>layer.parent_guid===
    source.bundles.camera_one_canvas.selected_asset.internal_id);
  const aimChild=themeChild(aimLayer,source.bundles.ui_aim.catalog_key);
  if (aimChild.id!==source.bundles.ui_aim.selected_asset.internal_id)
    throw new Error("Practice aim control theme selection differs");
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
    const ingameTransform=transform(state.instances.ingame_root);
    for (const role of ["ui_canvas_control","character_map","spot_camera","auto_camera","skill_director","graphic_options"]) {
      const actual=call(transform(state.instances[role]).method("get_parent",0),
        transform(state.instances[role]));
      if (!present(actual) || !actual.handle.equals(ingameTransform.handle))
        throw new Error(role+" is not under original ShootingRange IngameObject parent");
    }
    const root = state.instances.prefab_root;
    const popupParent=call(transform(state.instances.popup_control).method('get_parent',0),
      transform(state.instances.popup_control));
    if(!present(popupParent)||!popupParent.handle.equals(transform(state.instances.popup_canvas).handle))
      throw new Error('Original loading-page popup is not under original popup Canvas');
    const rootTransform = transform(root);
    for (const role of ["monster_controller", "summon_controller", "qte_controller",
      "character_controller","projectile_controller","dynamic_controller",
      "fx_controller","timeline_controller"]) {
      const childTransform = transform(state.instances[role]);
      const parentTransform = requireRef(call(childTransform.method("get_parent", 0),
        childTransform), role + " parent Transform");
      if (!parentTransform.handle.equals(rootTransform.handle))
        throw new Error(role + " is not under original PrefabControl parent");
    }
    emit({ status: "original_mechanical_prefab_hierarchy_ready",
      parentKey: supplementalAssets.prefab_root.key,
      parentInternalId: supplementalAssets.prefab_root.id,
      childRoles: ["monster_controller", "summon_controller", "qte_controller",
        "character_controller","projectile_controller","dynamic_controller",
        "fx_controller","timeline_controller"] });
  }
  function next() {
    if (typeof firstAsyncFault !== "undefined" && firstAsyncFault)
      throw new Error("Original async presentation fault: " + firstAsyncFault.error);
    if (state.index === bundleRoles.length) {
      verifyAimHierarchy();
      verifyMechanicalHierarchy();
      for (const role of Object.keys(componentTypes)) {
        const go = state.instances[role];
        const concreteType = runtime.class(componentTypes[role]).type.object;
        const component = requireRef(call(go.method("GetComponent")
          .overload("System.Type"), go, [concreteType.handle]),
          "Original component " + componentTypes[role]);
        pin(component);
        state.components[role]=component;
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
      if (count !== 17) throw new Error("Original mechanical presentation count " + count + " != 17");
      state.popupControl=verifyOriginalPracticePopupRegistration(state.components.popup_control,count);
      emit({status:'original_loading_page_popup_registered',componentType:componentTypes.popup_control,
        originalThemeParent:true,beforeManagerOnInit:true,originalOnInitAndHideLoadingPreserved:true,
        loadingFlagWrittenByHost:false,hideCalledByHost:false});
      // Read the original typed singleton lookup after normal registration,
      // before manager OnInit can launch the skill/director loading chain.
      for (const [role,rva] of [['fx_controller',0x0544dc20],['timeline_controller',0x056a2e60]]) {
        const cls=runtime.class(componentTypes[role]);
        const getter=cls.method('get_Instance',0);
        if (Number(getter.relativeVirtualAddress)!==rva)
          throw new Error('Current original controller getter changed: '+role);
        const actual=requireRef(call(getter),'registered singleton '+role);
        const expected=requireRef(call(state.instances[role].method('GetComponent')
          .overload('System.Type'),state.instances[role],[cls.type.object.handle]),role);
        if (!actual.handle.equals(expected.handle))
          throw new Error('Original controller singleton differs: '+role);
        if (role==='timeline_controller') {
          const useDebug=!!actual.field('UseDebug').value;
          const usePlayToDisable=!!actual.field('UsePlayToDisable').value;
          if (useDebug || !usePlayToDisable)
            throw new Error('Original serialized timeline flags differ');
          emit({status:'original_timeline_controller_verified',useDebug,usePlayToDisable,
            originalSingletonMatchesRegisteredPrefab:true,beforeManagerOnInit:true,
            flagsWritten:false,directorFactoryCalledByHost:false});
        }
      }
      const graphicType=runtime.class(componentTypes.graphic_options).type.object;
      state.graphicOptions=pin(requireRef(call(state.instances.graphic_options.method('GetComponent')
        .overload('System.Type'),state.instances.graphic_options,[graphicType.handle]),
        'original SpotGraphicOptions'));
      const unityAlive=unity.class('UnityEngine.Object').method('op_Implicit',1);
      function originalLiveComponent(value,type,label) {
        requireRef(value,label);
        if (value.class.type.name!==type ||
            !call(unityAlive,null,[value.handle]).unbox().handle.readU8())
          throw new Error(label+' has wrong native type or is Unity-null');
        pin(value);
        return value;
      }
      state.cutscene=verifyOriginalPracticeCutsceneReferences(state.components.cutscene_control,
        cutsceneSource,originalLiveComponent,call,pin,emit);
      const graphicControl=originalLiveComponent(state.graphicOptions.field('_graphicOptionController').value,
        'NK.Graphics.NKGraphicOptionController','serialized graphic controller');
      state.envGradient=originalLiveComponent(state.graphicOptions.field('_envGradientController').value,
        'NK.Spot.DayNight.NKEnvGradientController','serialized environment controller');
      const getVolume=state.envGradient.method('GetVolume',0);
      if (Number(getVolume.relativeVirtualAddress)!==0x06e8ce40)
        throw new Error('Current original environment GetVolume changed');
      const volume=originalLiveComponent(call(getVolume,state.envGradient),
        'UnityEngine.Rendering.Volume','original environment Volume');
      const envGo=requireRef(call(state.envGradient.method('get_gameObject',0),state.envGradient),'environment GameObject');
      const volumeGo=requireRef(call(volume.method('get_gameObject',0),volume),'Volume GameObject');
      if (!envGo.handle.equals(volumeGo.handle))
        throw new Error('Original Volume is not on environment controller GameObject');
      const providerClass=Il2Cpp.domain.assembly('NK.Unity').image
        .class('NK.ScriptableData.Graphics.NKGlobalShaderPropertyData');
      const providerGetter=providerClass.method('get_Instance',0);
      if (!providerGetter.isStatic || Number(providerGetter.relativeVirtualAddress)!==0x0788f320)
        throw new Error('Current original graphics provider getter changed');
      const provider=originalLiveComponent(call(providerGetter),providerClass.type.name,
        'original GlobalShaderConfig asset');
      emit({status:'original_graphic_options_prerequisites_verified',
        graphicControllerType:graphicControl.class.type.name,
        environmentControllerType:state.envGradient.class.type.name,
        volumeType:volume.class.type.name,volumeOnOriginalEnvironmentGameObject:true,
        providerType:provider.class.type.name,originalProviderGetterRva:'0x0788F320',
        originalProviderResourceKey:'ScriptableData/Graphics/GlobalShaderConfig',
        serializedReferencesWritten:false,dayNightCreationLeftToOriginalOnInit:true,
        sourceReceiptSha256:globalThis.PRACTICE_GRAPHIC_OPTIONS_SOURCE_SHA256});
      state.status = "ready";
      state.presentationCount = count;
      emit({ status: "original_mechanical_prefabs_registered", presentationCount: count,
        roles: bundleRoles, managerOnInitPending: true, sceneLoadedByHelper: false, fullMechanicalCoverageVerified:false,
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
    // Theme ParentObject instances are direct children of PresentationRoot.
    // UICanvasControl discovers the originals through the GUID registry.
    if (["ui_canvas_control","character_map","spot_camera","auto_camera","skill_director","graphic_options","cutscene_control"].includes(role))
      parent = state.instances.ingame_root;
    if (role === "ui_aim") parent = state.instances.camera1_canvas;
    if (role === "popup_control") parent = state.instances.popup_canvas;
    if (role === "aim_ui_ref")
      parent = state.instances.overlay_canvas;
    if (["monster_controller", "summon_controller", "qte_controller",
      "character_controller","projectile_controller","dynamic_controller",
      "fx_controller","timeline_controller"].includes(role))
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

function finishPracticeGeometryRuntime(state, management, team, pin, emit) {
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
  required(byName.SpineCharacterPrefabController, "SpineCharacterPrefabController");
  required(byName.ProjectilePrefabController, "ProjectilePrefabController");
  required(byName.DynamicObjectPrefabController, "DynamicObjectPrefabController");
  required(byName.SkillDirector, "SkillDirector");
  required(byName.FXController, "FXController");
  required(byName.SpotTimelineController, "SpotTimelineController");
  required(byName.SpotGraphicOptions, "SpotGraphicOptions");
  required(byName.CutSceneControl, "CutSceneControl");
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
  const brain=required(cameraControl.field("_cinemachineBrain").value,
    "SpotCameraControl CinemachineBrain");
  const cameraField=cameraControl.field('_spotCamera');
  if(cameraField.offset!==0x30||cameraField.type.name!=='UnityEngine.Camera')
    throw new Error('Current original intro cleanup camera field differs');
  const brainType=Il2Cpp.domain.assembly('Cinemachine').image.class('Cinemachine.CinemachineBrain');
  const actualBrain=required(call(camera.method('GetComponent').overload('System.Type'),camera,
    [brainType.type.object.handle]),'original intro cleanup CinemachineBrain');
  const isUnityLive=Il2Cpp.domain.assembly('UnityEngine.CoreModule').image.class('UnityEngine.Object').method('op_Implicit',1);
  if(actualBrain.class.type.name!=='Cinemachine.CinemachineBrain'||!actualBrain.handle.equals(brain.handle)||
      !call(isUnityLive,null,[actualBrain.handle]).unbox().handle.readU8())
    throw new Error('Original intro cleanup camera/brain identity is not ready');
  if(!state.introCleanupVerified){
    state.introCleanupVerified=true;
    emit({status:'original_cutscene_cleanup_prerequisite_verified',
      originalRegisteredCameraPreserved:true,originalBrainPresent:true,brainBlendWrittenByHost:false,
      phase:'after_original_resource_loading',source:'cutscene-ui-slots1/report.json:0B0353B0/0AF1C6A0'});
  }
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
    originalMapMethodRva: "0x0611D8B0",
    originalCameraMethodRva: "0x062425D0" });
  return geometry;
}
