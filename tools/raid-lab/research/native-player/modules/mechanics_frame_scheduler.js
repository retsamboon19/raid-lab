// One original combat tick in each real Unity Update phase. Unity retains its
// Animator, physics, Cinemachine and LateUpdate lifecycle; there are no manual
// pose/physics steps. FRAME-SCHEDULING-PLAN.md records the exact source binding.
function createMechanicsFrameScheduler(pin, emit, wallFrameRate = -1) {
  if (!Number.isInteger(wallFrameRate) || (wallFrameRate !== -1 &&
      (wallFrameRate < 160 || wallFrameRate > 1000)))
    throw new Error("Unsupported bounded wall frame rate");
  const core = Il2Cpp.domain.assembly("UnityEngine.CoreModule").image;
  const time = core.class("UnityEngine.Time");
  const app = core.class("UnityEngine.Application");
  const call = (method, self = null, args = []) => invokeChecked(method, self, args);
  const int = (klass, name) => call(klass.method(name, 0)).unbox().handle.readS32();
  const float = name => call(time.method(name, 0)).unbox().handle.readFloat();
  const game = Process.getModuleByName("GameAssembly.dll");
  const cine = Il2Cpp.domain.assembly("Cinemachine").image.class("Cinemachine.CinemachineCore");
  const cineTime = cine.method("get_CurrentTime", 0);
  const cineOverride = cine.field("CurrentTimeOverride");
  if (!cineTime.virtualAddress.equals(game.base.add(0x0099CEF0)) ||
      !cineOverride.isStatic || cineOverride.offset !== 0x24)
    throw new Error("Original Cinemachine clock contract changed");
  const staticGet = new NativeFunction(game.getExportByName("il2cpp_field_static_get_value"),
    "void", ["pointer", "pointer"]);
  const staticSet = new NativeFunction(game.getExportByName("il2cpp_field_static_set_value"),
    "void", ["pointer", "pointer"]);
  const cineValue = Memory.alloc(4);
  staticGet(cineOverride.handle, cineValue);
  const priorCineTime = cineValue.readFloat();
  if (priorCineTime !== -1) throw new Error("Unexpected preexisting Cinemachine time override");
  const setCineTime = value => {
    cineValue.writeFloat(value);
    staticSet(cineOverride.handle, cineValue);
    staticGet(cineOverride.handle, cineValue);
    if (cineValue.readFloat() !== value) throw new Error("Cinemachine clock readback failed");
  };
  const resolve = new NativeFunction(game.getExportByName("il2cpp_resolve_icall"),
    "pointer", ["pointer"]);
  const icall = name => {
    const pointer = resolve(Memory.allocUtf8String("UnityEngine.Time::" + name));
    const module = pointer.isNull() ? null : Process.findModuleByAddress(pointer);
    if (!module || module.name.toLowerCase() !== "unityplayer.dll")
      throw new Error("Original Unity capture-time binding unavailable: " + name);
    return pointer;
  };
  const getCapture = new NativeFunction(icall("get_captureDeltaTime"), "float", []);
  const setCapture = new NativeFunction(icall("set_captureDeltaTime"), "void", ["float"]);
  const prior = { captureDeltaTime: getCapture(), targetFrameRate: int(app, "get_targetFrameRate"),
    fixedDeltaTime: float("get_fixedDeltaTime"),
    timeScale: float("get_timeScale"), cinemachineCurrentTimeOverride: priorCineTime };
  if (prior.timeScale !== 1) throw new Error("Original battle Unity timeScale is not 1");
  const dt = Math.fround(1/30);
  // Trial71: actual normalized pose advancement follows speed*captureDelta,
  // even in Animator mode2, while Time.unscaledDeltaTime remains wall time.
  // Preserve the original speed adjustment but use that actual evaluation dt.
  const animatorClock = game.base.add(0x0635A4B8);
  const originalClockBytes = "e803aff101", capturedClockBytes = "e8c3acf101";
  const clockBytes = () => Array.from(new Uint8Array(animatorClock.readByteArray(5)),
    x => x.toString(16).padStart(2, "0")).join("");
  const writeClock = hex => {
    Memory.patchCode(animatorClock, 5, writable => writable.writeByteArray(
      hex.match(/../g).map(x => parseInt(x, 16))));
    if (clockBytes() !== hex) throw new Error("Animator clock callsite readback failed");
  };
  if (globalThis.MECHANICS_GEOMETRY_SOURCE.installed_client_sha256 !==
      "2df7134a6a9c3a8dbbde88402fc8d16d1d6c3f4c2d5e262bea78c3d78b96dd02" ||
      clockBytes() !== originalClockBytes)
    throw new Error("Original Animator clock callsite changed");
  let clockPatched = false;
  const restore = () => {
    if (clockPatched) { writeClock(originalClockBytes); clockPatched = false; }
    setCineTime(priorCineTime);
    setCapture(prior.captureDeltaTime);
    call(app.method("set_targetFrameRate", 1), null, [intArg(prior.targetFrameRate)]);
    if (getCapture() !== prior.captureDeltaTime) throw new Error("Capture time restoration failed");
  };
  try {
    setCapture(dt);
    // Original Perlin initializes phase from CurrentTime * frequency. Trials
    // 80/81 had identical RNG offsets but different phase from loading time.
    // Keep original sway, seeds, gains and update methods; control only its
    // documented clock input with an explicit simulation origin of zero.
    setCineTime(0);
    call(app.method("set_targetFrameRate", 1), null, [intArg(wallFrameRate)]);
    if (getCapture() !== dt) throw new Error("Original Unity capture-time readback failed");
    clockPatched = true;
    writeClock(capturedClockBytes);
    emit({status:"original_animator_capture_clock_adapted", callsiteRva:"0x0635A4B8",
      originalBytes:originalClockBytes, patchedBytes:capturedClockBytes,
      originalGetterRva:"0x082753C0", capturedGetterRva:"0x08275180",
      originalAnimatorLifecyclePreserved:true, captureDeltaTime:dt});
  } catch (error) { restore(); throw error; }
  try {
  const uni = Il2Cpp.domain.assembly("UniTask").image;
  const post = uni.class("Cysharp.Threading.Tasks.UniTask").method("Post", 2);
  if (!post.virtualAddress.equals(game.base.add(0x07F17E50))) {
    restore(); throw new Error("Original UniTask.Post method changed");
  }
  const phase = uni.class("Cysharp.Threading.Tasks.PlayerLoopTiming").field("Update").value;
  const phaseNumber = typeof phase === "number" ? phase : Number(phase.field("value__").value);
  const phaseArg = intArg(phaseNumber);
  let started = false;
  return function schedule(runTick, fail) {
    if (started) throw new Error("Frame scheduler cannot be reused without a reset");
    started = true;
    let active = true, frames = 0, lastFrame = int(time, "get_frameCount");
    const cancel = () => {
      if (!active) return;
      active = false;
      restore();
      emit({ status: "original_unity_frame_scheduler_stopped", frames,
        lastFrame, restored: true });
    };
    const action = pin(Il2Cpp.delegate(Il2Cpp.corlib.class("System.Action"), () => {
      if (!active) return;
      try {
        const frame = int(time, "get_frameCount");
        if (frame <= lastFrame) throw new Error("Combat callback repeated within one Unity frame");
        const delta = float("get_deltaTime");
        if (Math.abs(delta-dt) > 0.000001)
          throw new Error("Unity frame delta differs from requested battle delta: " + delta);
        lastFrame = frame; frames++;
        setCineTime(Math.fround(frames * dt));
        runTick();
        if (active) call(post, null, [action.handle, phaseArg]);
      } catch (error) { fail(error); }
    }));
    emit({ status: "original_unity_frame_scheduler_started", phase: "Update",
      phaseNumber, captureDeltaTime: dt, batchSize: 1, prior,
      wallFrameRate,
      cameraClockOriginSeconds:0, cameraClockGetterRva:"0x0099CEF0",
      cameraSwayAndRandomStreamsPreserved:true,
      originalPlayerLoopPreserved: true, fullAccuracyVerified: false });
    try { call(post, null, [action.handle, phaseArg]); }
    catch (error) { cancel(); throw error; }
    return { cancel };
  };
  } catch (error) { restore(); throw error; }
}
