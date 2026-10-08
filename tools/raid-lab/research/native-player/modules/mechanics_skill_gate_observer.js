// One-event, read-only diagnostic for the installed Scarlet skill timeline.
// Forward the already wrapped event from the existing SendEventDefault hook.
// No hook, director creation, event dispatch, or presentation registration.
function installMechanicsSkillGateObserver(runtime, management, emit) {
  if (!runtime || !management || management.isNull() || typeof emit !== "function")
    throw new Error("Original skill gate observer requires management and emit");
  const game = Process.getModuleByName("GameAssembly.dll");
  const at = (method, rva, label) => {
    if (!method.virtualAddress.equals(game.base.add(rva)))
      throw new Error("Installed skill gate method changed: " + label);
    return method;
  };
  const call = (method, instance = null, args = []) =>
    invokeChecked(method, instance, args);
  const present = value => value != null && !value.isNull();
  const intValue = value => typeof value === "number" ? value :
    Number(value.field("value__").value);
  const objectClass = Il2Cpp.domain.assembly("UnityEngine.CoreModule").image
    .class("UnityEngine.Object");
  const unityValidMethod = at(objectClass.method("op_Implicit", 1),
    0x08269CB0, "UnityEngine.Object.op_Implicit");
  const unityValid = value => present(value) &&
    call(unityValidMethod, null, [value.handle]).unbox().handle.readU8() !== 0;
  const gameObjectClass = Il2Cpp.domain.assembly("UnityEngine.CoreModule").image
    .class("UnityEngine.GameObject");
  const getComponent = at(gameObjectClass.method("GetComponent")
    .overload("System.Type"), 0x08264C50, "GameObject.GetComponent(Type)");
  const getName = at(objectClass.method("get_name", 0),
    0x08269AD0, "UnityEngine.Object.get_name");
  const directorType = Il2Cpp.domain.assembly("UnityEngine.DirectorModule")
    .image.class("UnityEngine.Playables.PlayableDirector").type.object;

  const eventClass = runtime.class("NK.Spot.Event.Character.ProcessCharacterSkillEvent");
  const skillClass = runtime.class("NK.Spot.Model.Character.Skill.SpotSkill");
  const resourceClass = runtime.class(
    "NK.Spot.ScriptableData.Skill.NKCharacterSkillResourceData_InstantNumber");
  const cameraClass = runtime.class("NK.Spot.Presentation.Camera.SpotCameraControl");
  const fxClass = runtime.class("NK.Spot.Presentation.FXController");
  const fxCacheClass = fxClass.nested("FxCache");
  const recordClass = Il2Cpp.domain.assembly("NK.Runtime.StaticData").image.class(
    "NK.StaticData.StaticDataLayer.StaticInfo.CharacterSkillStaticInfo");
  const layouts = [
    [eventClass,"Skill",0x48],[eventClass,"DirectorList",0x50],
    [skillClass,"<RecordData>k__BackingField",0x20],
    [skillClass,"_resourceData",0xA0],
    [recordClass,"<TableId>k__BackingField",0x10],
    [recordClass,"<Resource_name>k__BackingField",0x28],
    [resourceClass,"WorldTimeline",0x38],
    [resourceClass,"CasterTimeline",0x50],
    [resourceClass,"TargetTimeline",0x78],
    [fxClass,"_instance",0],[fxClass,"_fxCache",0x38],
    [fxCacheClass,"_excludeFxOptionSet",0x18],
    [fxCacheClass,"_battleEffectQuality",0x20],
    [management.class,"_presentations",0x28]
  ];
  for (const [klass, name, offset] of layouts)
    if (klass.field(name).offset !== offset)
      throw new Error("Installed skill gate field changed: " + klass.name + "." + name);
  at(eventClass.method(".ctor", 5), 0x064578B0,
    "ProcessCharacterSkillEvent.ctor");
  at(runtime.class("NK.Spot.Logic.Skill.SpotSkillLogic")
    .method("ProcessWorldTimeLine", 6), 0x063AD0F0,
    "SpotSkillLogic.ProcessWorldTimeLine");
  const fxIsValid = at(fxClass.method("IsValidFx", 1), 0x061B0360,
    "FXController.IsValidFx");
  at(fxClass.method("get_Instance", 0), 0x061B2640,
    "FXController.get_Instance");
  at(management.method("SendEventDefault", 1), 0x0614BAF0,
    "SpotManagement.SendEventDefault");

  function registeredPresentations() {
    const dictionary = management.field("_presentations").value;
    if (!present(dictionary)) throw new Error("Original presentation dictionary is null");
    const count = call(dictionary.method("get_Count", 0), dictionary)
      .unbox().handle.readS32();
    if (count < 0 || count > 64)
      throw new Error("Original presentation count outside diagnostic bound: " + count);
    const values = call(dictionary.method("get_Values", 0), dictionary);
    const iterator = call(values.method("GetEnumerator", 0), values);
    const found = {camera:null,fx:null};
    for (let i = 0; i <= count; i++) {
      const cursor = iterator.unbox();
      if (!call(cursor.method("MoveNext", 0), cursor)
        .unbox().handle.readU8()) break;
      if (i === count) throw new Error("Original presentation enumeration exceeds Count");
      const item = call(cursor.method("get_Current", 0), cursor);
      if (!present(item)) throw new Error("Original presentation dictionary has null value");
      const name = item.class.type.name;
      if (name === cameraClass.type.name) found.camera = item;
      if (name === fxClass.type.name) found.fx = item;
    }
    return {count,found};
  }
  function timelineState(resource, field) {
    const go = resource.field(field).value;
    const state = {field,managedReferencePresent:present(go),unityValid:false,
      gameObjectName:null,playableDirectorPresent:false,
      playableDirectorUnityValid:false};
    if (!unityValid(go)) return state;
    state.unityValid = true;
    const name = call(getName, go);
    state.gameObjectName = present(name) ? new Il2Cpp.String(name.handle).content : null;
    const component = call(getComponent, go, [directorType.handle]);
    state.playableDirectorPresent = present(component);
    state.playableDirectorUnityValid = unityValid(component);
    return state;
  }
  function fxState(fx, registered, worldName) {
    const state = {registered,unityValid:unityValid(fx),
      cachePresent:false,excludeSetPresent:false,battleEffectQuality:null,
      isValidFx:null,isValidFxSkipped:null};
    if (!state.unityValid) {
      state.isValidFxSkipped = "no live original FXController";
      return state;
    }
    const cache = fx.field("_fxCache").value;
    state.cachePresent = present(cache);
    if (!state.cachePresent) {
      state.isValidFxSkipped = "original FxCache is null";
      return state;
    }
    const excluded = cache.field("_excludeFxOptionSet").value;
    state.excludeSetPresent = present(excluded);
    state.battleEffectQuality = intValue(cache.field("_battleEffectQuality").value);
    if (!worldName) {
      state.isValidFxSkipped = "WorldTimeline name unavailable";
      return state;
    }
    if (state.battleEffectQuality !== 2 && !state.excludeSetPresent) {
      state.isValidFxSkipped = "original exclusion set is null";
      return state;
    }
    const name = Il2Cpp.string(worldName);
    state.isValidFx = call(fxIsValid, fx, [name.handle])
      .unbox().handle.readU8() !== 0;
    return state;
  }

  let observed = false, report = null, fault = null;
  function observeSendEvent(event) {
    if (observed || fault !== null || !present(event) ||
        event.class.type.name !== eventClass.type.name) return;
    try {
      const skill = event.field("Skill").value;
      if (!present(skill) || skill.class.type.name !== skillClass.type.name)
        throw new Error("Original ProcessCharacterSkillEvent.Skill changed");
      const record = skill.field("<RecordData>k__BackingField").value;
      if (!present(record) || record.class.type.name !== recordClass.type.name)
        throw new Error("Original SpotSkill.RecordData changed");
      const text = record.field("<Resource_name>k__BackingField").value;
      const resourceName = present(text) ? new Il2Cpp.String(text.handle).content : null;
      if (resourceName !== "c225_skill1_3") return;
      observed = true; // Exactly one attempt; failure is reported, never retried.
      const resource = skill.field("_resourceData").value;
      if (!present(resource) || resource.class.type.name !== resourceClass.type.name)
        throw new Error("Original Scarlet InstantNumber resource missing or changed");
      const {count,found} = registeredPresentations();
      const fxStatic = fxClass.field("_instance").value;
      const fx = unityValid(fxStatic) ? fxStatic : found.fx;
      const world = timelineState(resource,"WorldTimeline");
      const caster = timelineState(resource,"CasterTimeline");
      const target = timelineState(resource,"TargetTimeline");
      report = {status:"original_skill_timeline_gate",resourceName,
        tableId:Number(record.field("<TableId>k__BackingField").value),
        tick:Number(management.field("_tickCount").value),
        presentationCount:count,
        spotCameraControl:{registered:present(found.camera),
          unityValid:unityValid(found.camera)},
        fxController:fxState(fx,present(found.fx),world.gameObjectName),
        fxStaticInstanceUnityValid:unityValid(fxStatic),
        worldTimeline:world,casterTimeline:caster,targetTimeline:target,
        existingDirectorListPresent:present(event.field("DirectorList").value),
        source:"installed GameAssembly RVAs 0x063A4A30, 0x063AD0F0, 0x0639E1E0"};
      emit(report);
    } catch (error) {
      fault = error && error.stack ? error.stack : String(error);
      emit({status:"original_skill_timeline_gate_fault",fault});
    }
  }
  function snapshot() {
    return {status:"original_skill_timeline_gate_summary",observed,report,fault};
  }
  function checkFault() { if (fault !== null) throw new Error(fault); }
  emit({status:"original_skill_timeline_gate_ready",resourceName:"c225_skill1_3",
    oneEventOnly:true,installsHooks:false,mutatesCombatState:false});
  return {observeSendEvent,snapshot,checkFault};
}
