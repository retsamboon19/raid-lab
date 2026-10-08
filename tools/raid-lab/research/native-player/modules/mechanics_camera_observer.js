// Read-only, bounded camera/aim clock snapshot for the private mechanics host.
// Installed GameAssembly SHA-256: 2df7134a6a9c3a8dbbde88402fc8d16d1d6c3f4c2d5e262bea78c3d78b96dd02.
// Call sample("before"|"after", tick) on the Unity main thread around the
// original UpdateSpot call. This installs no hooks and changes no game state.
function createMechanicsCameraObserver(runtime, management, aimBinding, pin, emit) {
  if (typeof pin !== "function" || typeof emit !== "function" ||
      !management || management.isNull() || !aimBinding ||
      typeof aimBinding.getNativeAimState !== "function" ||
      !(aimBinding.bound instanceof Map))
    throw new Error("Original camera observer requires live aim binding and callbacks");
  const game = Process.getModuleByName("GameAssembly.dll");
  const unity = Il2Cpp.domain.assembly("UnityEngine.CoreModule").image;
  const cine = Il2Cpp.domain.assembly("Cinemachine").image;
  const time = unity.class("UnityEngine.Time");
  const component = unity.class("UnityEngine.Component");
  const transformClass = unity.class("UnityEngine.Transform");
  const objectClass = unity.class("UnityEngine.Object");
  const arrayClass = Il2Cpp.corlib.class("System.Array");
  const brainClass = cine.class("Cinemachine.CinemachineBrain");
  const coreClass = cine.class("Cinemachine.CinemachineCore");
  const perlinClass = cine.class("Cinemachine.CinemachineBasicMultiChannelPerlin");
  const camera = aimBinding.camera;
  const control = aimBinding.cameraControl;
  if (!camera || camera.isNull() || !control || control.isNull() ||
      !control.field("_spotCamera").value.handle.equals(camera.handle))
    throw new Error("Original camera observer requires the bound SpotCameraControl Camera");
  const brain = pin(control.field("_cinemachineBrain").value);
  if (!brain || brain.isNull())
    throw new Error("Original camera observer requires CinemachineBrain");
  const entityId=mechanicsRequestedEntityId(5099);
  const actor = aimBinding.bound.get(entityId);
  if (!actor || !actor.uiAim || actor.uiAim.isNull())
    throw new Error("Original camera observer requires bound Naga UIAim " + entityId);
  const uiAim = pin(actor.uiAim);
  // Exact installed metadata offsets: UIAim._targetPosition=0x50 (Vector2),
  // UIAim._currentPosition=0x58 (Vector2). Require fields before raw reads.
  uiAim.field("_targetPosition");
  uiAim.field("_currentPosition");
  const call = (method, self = null, args = []) => invokeChecked(method, self, args);
  const boxed = (method, self = null, args = []) => call(method, self, args).unbox().handle;
  const finite = (value, label) => {
    if (!Number.isFinite(value)) throw new Error("Invalid original " + label + ": " + value);
    return value;
  };
  const readVec = (ptr, count, label) => Array.from({length: count}, (_, i) =>
    finite(ptr.add(i * 4).readFloat(), label + "[" + i + "]"));
  const intValue = value => {
    const n = typeof value === "number" || typeof value === "boolean" ?
      Number(value) : Number(value.field("value__").value);
    return finite(n, "Cinemachine enum");
  };
  const readStaticFloat = field => {
    const ptr = Memory.alloc(4);
    const getter = new NativeFunction(game.getExportByName("il2cpp_field_static_get_value"),
      "void", ["pointer", "pointer"]);
    getter(coreClass.field(field).handle, ptr);
    return finite(ptr.readFloat(), "CinemachineCore." + field);
  };
  const effective = brainClass.method("GetEffectiveDeltaTime", 1);
  if (!effective.virtualAddress.equals(game.base.add(0x009611A0)))
    throw new Error("Installed CinemachineBrain.GetEffectiveDeltaTime RVA changed");
  // Do not invoke GetEffectiveDeltaTime: its installed body can initialize
  // static method/icall caches. Its false-branch selection is reported below
  // as a source-derived expectation, distinctly from a native call result.
  const cameraTransform = pin(call(component.method("get_transform", 0), camera));
  if (!cameraTransform || cameraTransform.isNull())
    throw new Error("Original camera observer requires live Camera Transform");
  const frameCount = time.method("get_frameCount", 0);
  const deltaTime = time.method("get_deltaTime", 0);
  const unscaledDeltaTime = time.method("get_unscaledDeltaTime", 0);
  const elapsedTime = time.method("get_time", 0);
  const position = transformClass.method("get_position", 0);
  const rotation = transformClass.method("get_rotation", 0);
  const fov = camera.method("get_fieldOfView", 0);
  const activeVirtualCamera = brainClass.method("get_ActiveVirtualCamera", 0);
  if (!activeVirtualCamera.virtualAddress.equals(game.base.add(0x00964430)))
    throw new Error("Installed Brain active virtual-camera getter RVA changed");
  // The original Perlin body at RVA 0x0097A360 reads these exact fields.
  const perlinFields = {m_AmplitudeGain:0x34, m_FrequencyGain:0x38,
    mInitialized:0x3c, mNoiseTime:0x40, mNoiseOffsets:0x44};
  for (const [name, offset] of Object.entries(perlinFields)) {
    if (perlinClass.field(name).offset !== offset)
      throw new Error("Installed Perlin field offset changed: " + name);
  }
  const intArg = value => {
    const ptr = Memory.alloc(4);
    ptr.writeS32(value);
    return ptr;
  };
  const getName = object => {
    const value = call(objectClass.method("get_name", 0), object);
    return value && !value.isNull() ? new Il2Cpp.String(value.handle).content : null;
  };
  const knownVcams = new Map();
  const readActiveVcam = phase => {
    const active = call(activeVirtualCamera, brain);
    if (!active || active.isNull()) {
      if (phase === "after")
        throw new Error("Original Brain has no active virtual camera after UpdateSpot");
      return {identity:null, perlin:[]};
    }
    const key = active.handle.toString();
    let cached = knownVcams.get(key);
    if (!cached) {
      const vcam = pin(active);
      const owner = pin(call(vcam.method("get_VirtualCameraGameObject", 0), vcam));
      if (!owner || owner.isNull())
        throw new Error("Active virtual camera has no original GameObject");
      // Search only the active, bound Brain camera's own pipeline hierarchy.
      const components = call(owner.method("GetComponentsInChildren").overload(
        "System.Type", "System.Boolean"), owner,
        [perlinClass.type.object.handle, intArg(1)]);
      if (!components || components.isNull())
        throw new Error("Active camera Perlin component query returned null");
      const length = boxed(arrayClass.method("get_Length", 0), components).readS32();
      if (length < 0 || length > 16)
        throw new Error("Active camera Perlin component count outside bound");
      const getValue = arrayClass.method("GetValue").overload("System.Int32");
      const perlin = [];
      for (let i = 0; i < length; i++) {
        const value = pin(call(getValue, components, [intArg(i)]));
        if (!value || value.isNull() ||
            value.class.type.name !== "Cinemachine.CinemachineBasicMultiChannelPerlin")
          throw new Error("Active camera Perlin component type mismatch");
        perlin.push(value);
      }
      cached = {vcam,owner,perlin};
      knownVcams.set(key,cached);
    }
    const identity = {type:cached.vcam.class.type.name,
      name:getName(cached.owner),
      instanceId:boxed(objectClass.method("GetInstanceID",0),cached.owner).readS32()};
    const perlin = cached.perlin.map((value,index) => ({index,
      name:getName(value),
      instanceId:boxed(objectClass.method("GetInstanceID",0),value).readS32(),
      amplitudeGain:finite(value.handle.add(0x34).readFloat(),"Perlin amplitude"),
      frequencyGain:finite(value.handle.add(0x38).readFloat(),"Perlin frequency"),
      initialized:!!value.handle.add(0x3c).readU8(),
      noiseTime:finite(value.handle.add(0x40).readFloat(),"Perlin noise time"),
      noiseOffsets:readVec(value.handle.add(0x44),3,"Perlin noise offsets")}));
    return {identity,perlin};
  };
  const selected = tick => tick === 1 || (tick >= 1408 && tick <= 1422);
  const sample = (phase, tick) => {
    if (phase !== "before" && phase !== "after")
      throw new Error("Camera observer phase must be before or after");
    if (!Number.isInteger(tick) || tick < 1)
      throw new Error("Camera observer tick must be positive integer");
    if (!selected(tick)) return;
    try {
      const nativeAim = aimBinding.getNativeAimState(entityId);
      const updateMethod = intValue(brain.field("m_UpdateMethod").value);
      const blendMethod = intValue(brain.field("m_BlendUpdateMethod").value);
      const ignoreScale = intValue(brain.field("m_IgnoreTimeScale").value);
      const frame = boxed(frameCount).readS32();
      const reportedDelta = boxed(deltaTime).readFloat();
      const reportedUnscaledDelta = boxed(unscaledDeltaTime).readFloat();
      const reportedTime = boxed(elapsedTime).readFloat();
      const uniformOverride = readStaticFloat("UniformDeltaTimeOverride");
      const currentOverride = readStaticFloat("CurrentTimeOverride");
      const expectedEffectiveDelta = uniformOverride >= 0 ? uniformOverride :
        ignoreScale ? reportedUnscaledDelta : reportedDelta;
      const active = readActiveVcam(phase);
      emit({phase, tick, status:"original_camera_aim_clock_sample",
        entityId, frameCount:frame,
        unityTime:{deltaTime:finite(reportedDelta,"Time.deltaTime"),
          unscaledDeltaTime:finite(reportedUnscaledDelta,"Time.unscaledDeltaTime"),
          time:finite(reportedTime,"Time.time")},
        camera:{worldPosition:readVec(boxed(position,cameraTransform),3,"Camera.position"),
          worldRotation:readVec(boxed(rotation,cameraTransform),4,"Camera.rotation"),
          fieldOfView:finite(boxed(fov,camera).readFloat(),"Camera.fieldOfView")},
        brain:{ignoreTimeScale:ignoreScale, updateMethod, blendMethod,
          lastFrameUpdated:finite(Number(brain.field("m_LastFrameUpdated").value),
            "CinemachineBrain.m_LastFrameUpdated"),
          uniformDeltaTimeOverride:uniformOverride,
          currentTimeOverride:currentOverride,
          expectedEffectiveDeltaTime:finite(expectedEffectiveDelta,
            "CinemachineBrain source-derived effective delta")},
        activeVirtualCamera:active.identity,
        activeCameraPerlin:active.perlin,
        naga:{uiWorldPosition:nativeAim.uiAimPosition,
          logicOrigin:nativeAim.logicAimPosition,
          logicDirection:nativeAim.logicAimDirection,
          targetPosition:readVec(uiAim.handle.add(0x50),2,"UIAim._targetPosition"),
          currentPosition:readVec(uiAim.handle.add(0x58),2,"UIAim._currentPosition")},
        optional:{brainFrameDeltaOverride:"unsupported: no active BrainFrame is bound",
          nativeEffectiveDeltaTime:"unsupported: getter may initialize static caches; source branch inferred only"},
        originalMethods:{effectiveDeltaTimeRva:"0x009611A0",
          cameraControlTickRva:"0x06313A20", uiAimTickRva:"0x062297D0"}});
    } catch (error) {
      emit({phase, tick, status:"original_camera_aim_clock_failure",
        entityId, error:String(error),
        nativeFrames:error.nativeFrames || []});
      throw error;
    }
  };
  emit({status:"original_camera_aim_observer_ready",entityId,
    sampledTicks:"1,1408..1422",phases:["before","after"],
    installsHooks:false, mutatesGameState:false});
  return {sample};
}
