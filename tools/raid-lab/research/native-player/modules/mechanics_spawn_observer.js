// First-spawn, read-only native call-site observer for the private mechanics
// player. Installation attaches NOTHING. The parent's existing
// SendEventDefault SpawnMonsterEvent observer calls arm() before dispatch;
// only then are these original CreateMonster-local call sites observed.

function installMechanicsSpawnObserver(emit, options = {}) {
  if (typeof emit !== "function") throw new Error("Spawn observer needs an evidence callback");
  const client = "2df7134a6a9c3a8dbbde88402fc8d16d1d6c3f4c2d5e262bea78c3d78b96dd02";
  const source = globalThis.MECHANICS_GEOMETRY_SOURCE;
  if (!source || source.installed_client_sha256 !== client)
    throw new Error("Spawn observer is not bound to the installed client receipt");
  const game = Process.getModuleByName("GameAssembly.dll");
  const at = rva => game.base.add(rva);
  let armed = false, fault = null, lastStage = null, records = 0;
  const hits = Object.create(null), retainedListeners = [];
  const maxRecords = 18;
  const emitOnce = (stage, detail = {}) => {
    hits[stage] = (hits[stage] || 0) + 1;
    if (hits[stage] !== 1 || records >= maxRecords) return;
    records++;
    lastStage = stage;
    try { emit({ status: "original_spawn_callsite", stage, ordinal: records, ...detail }); }
    catch (error) { if (fault === null) fault = "Spawn observer evidence write: " + String(error); }
  };
  const signatures = [
    [0x061CE7E0, "48895c2410564881", "OnSpawnMonster entry"],
    [0x061C47F0, "48894c2408555641", "CreateMonster entry"],
    [0x061C49C3, "4d85ed", "FindById preconditions"],
    [0x061C49E4, "488bf8", "FindById after"],
    [0x061C4F12, "498bcc", "Pool.Spawn before"],
    [0x061C4F2F, "488bd8", "Pool.Spawn after"],
    [0x061C5031, "4489742430", "SpotMonster.Create before"],
    [0x061C5049, "488bf8", "SpotMonster.Create after"],
    [0x061C50A4, "4c8b05958ab204", "LinkHitPoints after"]
  ];
  const verifyCode = () => {
    for (const [rva, expected, label] of signatures) {
      const raw = at(rva).readByteArray(expected.length / 2);
      if (raw === null) throw new Error("Unreadable original " + label);
      const actual = Array.from(new Uint8Array(raw), byte =>
        byte.toString(16).padStart(2, "0")).join("");
      if (actual !== expected) throw new Error("Installed call-site signature changed: " + label);
    }
  };
  const observe = (rva, stage, detail) => retainedListeners.push(Interceptor.attach(at(rva), {
    onEnter() {
      if (!armed || hits[stage]) return;
      try { emitOnce(stage, detail ? detail(this.context) : {}); }
      catch (error) { if (fault === null) fault = stage + ": " + String(error); }
    }
  }));

  function arm() {
    if (armed) return false;
    if (fault !== null) throw new Error(fault);
    try {
      verifyCode();
      // The isolated native bootstrap's passive VEH records C++ exception RVAs
      // without intercepting unwind functions. It is armed on this event's
      // current thread before the original event listeners run.
      const bootstrap = Process.getModuleByName("nikkeBase.dll");
      const enableObservation = new NativeFunction(
        bootstrap.getExportByName("SetMechanicsExceptionObservation"),
        "int", ["int"]);
      if (enableObservation(1) === 0)
        throw new Error("Private native exception observation rejected first spawn");
      // No global exception/throw-helper hook and no onLeave callback. All
      // addresses below belong to OnSpawnMonster or its CreateMonster body.
      if (options.callsiteMarkers === true) {
      observe(0x061CE7E0, "OnSpawnMonster.enter");
      observe(0x061C47F0, "CreateMonster.enter");
      observe(0x061C49C3, "MonsterTable.FindById.preconditions");
      observe(0x061C49E4, "MonsterTable.FindById.after",
        context => ({ rowPresent: !context.rax.isNull() }));
      observe(0x061C4F12, "NKGameObjectPool.Spawn.before");
      observe(0x061C4F2F, "NKGameObjectPool.Spawn.after",
        context => ({ gameObjectPresent: !context.rax.isNull() }));
      observe(0x061C5031, "SpotMonster.Create.before");
      observe(0x061C5049, "SpotMonster.Create.after",
        context => ({ monsterPresent: !context.rax.isNull() }));
      observe(0x061C50A4, "MonsterPrefabData.LinkHitPoints.after");
      }
      armed = true;
      emitOnce("observer.armed", { installedClientSha256: client,
        localMethod: "MonsterPrefabController.CreateMonster", maxRecords,
        callsiteMarkers:options.callsiteMarkers === true,
        nativeExceptionVehicle: "nikkeBase.dll!SetMechanicsExceptionObservation" });
      return true;
    } catch (error) {
      fault = "Spawn observer arm: " + String(error);
      throw error;
    }
  }

  return {
    arm,
    check() { if (fault !== null) throw new Error(fault); },
    snapshot() { return { armed, lastStage, hits, records, fault }; },
    retainedListeners
  };
}
