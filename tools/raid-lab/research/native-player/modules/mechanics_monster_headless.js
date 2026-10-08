// Narrow private-player boundary for the original monster loader's color-only
// dependency. Install before SpotManagement.OnLoad. The installed DLL and exact
// instruction bytes are required; never use this on a different client build.
// This leaves the original wave, pre-spawn, entity, damage and result methods.

function installMechanicsMonsterHeadless(emit) {
  if (typeof emit !== "function") throw new Error("Monster headless boundary needs an evidence callback");
  const expectedClient = "2df7134a6a9c3a8dbbde88402fc8d16d1d6c3f4c2d5e262bea78c3d78b96dd02";
  const source = globalThis.MECHANICS_GEOMETRY_SOURCE;
  if (!source || source.installed_client_sha256 !== expectedClient)
    throw new Error("Monster headless boundary is not bound to the installed DLL receipt");
  const module = Process.findModuleByName("GameAssembly.dll");
  if (!module) throw new Error("GameAssembly.dll is not loaded in the private player");
  const at = rva => module.base.add(rva);
  const signatures = [
    [0x061D5D6E, "85c9"],         // state dispatcher: observe state 0 before patch
    [0x061D5E30, "c74310ffffffff"], // state 0 becomes running before the optional gradient
    [0x061D5E37, "488b0d12609b04"], // patch 1: SpotGraphicOptions lookup
    [0x061D5E67, "4885c0"],         // lookup returned (should be unreachable after skip)
    [0x061D5E96, "0f108780000000"], // original task await resumes unchanged
    [0x061D5D9A, "c74310ffffffff"], // original state 1: PreSpawnEvent
    [0x061D5D80, "c74310ffffffff"], // original state 2: load complete
    [0x061D5ECD, "e89ed564fa"],   // original local null-throw helper
    [0x061D4ABF, "488b7b18"],     // InitColor post-yield, clear of patched JE
    [0x061D4AD3, "0f8445010000"], // patch 2: null gradient used to throw
    [0x061D4B08, "c703feffffff"], // original UniTask completion path
    [0x061C69C0, "48895c2410"],   // OnDarkChangeOff: color only
    [0x061C6C40, "48894c2408"]    // OnDarkChangeOnTarget: color only
  ];
  for (const [rva, wanted] of signatures) {
    const bytes = at(rva).readByteArray(wanted.length / 2);
    if (bytes === null) throw new Error("Unreadable installed code at RVA 0x" + rva.toString(16));
    const actual = Array.from(new Uint8Array(bytes), x => x.toString(16).padStart(2, "0")).join("");
    if (actual !== wanted)
      throw new Error("Installed code signature mismatch at RVA 0x" + rva.toString(16));
  }

  // Only the private process image changes. Never write the installed DLL.
  // The first branch starts after the original state-0 write of -1 and jumps
  // directly to the original first await. The second retargets only the
  // null-gradient branch after the original post-yield controller check.
  const patches = [
    { rva: 0x061D5E37, original: "488b0d12609b04", patched: "e95a0000009090" },
    { rva: 0x061D4AD3, original: "0f8445010000", patched: "0f842f000000" }
  ];
  const hexAt = (address, size) => {
    const bytes = address.readByteArray(size);
    if (bytes === null) throw new Error("Unreadable private code at " + address);
    return Array.from(new Uint8Array(bytes), x => x.toString(16).padStart(2, "0")).join("");
  };
  const patchBytes = (rva, hex) => {
    const bytes = hex.match(/../g).map(part => parseInt(part, 16));
    Memory.patchCode(at(rva), bytes.length, writable => writable.writeByteArray(bytes));
    if (hexAt(at(rva), bytes.length) !== hex)
      throw new Error("Private code patch readback mismatch at RVA 0x" + rva.toString(16));
  };
  const applied = [];
  try {
    for (const patch of patches) {
      if (hexAt(at(patch.rva), patch.original.length / 2) !== patch.original)
        throw new Error("Private code changed before patch at RVA 0x" + patch.rva.toString(16));
      // Record before writing, so even a failed readback is rolled back.
      applied.push(patch);
      patchBytes(patch.rva, patch.patched);
    }
  } catch (error) {
    const rollbackErrors = [];
    for (const patch of applied.reverse()) {
      try { patchBytes(patch.rva, patch.original); }
      catch (rollbackError) { rollbackErrors.push(String(rollbackError)); }
    }
    throw new Error("Private monster patch failed: " + error +
      (rollbackErrors.length ? "; rollback failed: " + rollbackErrors.join(" | ") : ""));
  }

  let fault = null;
  const counts = { gradientLookupsSkipped: 0, tintCompletions: 0,
    darkOffSkipped: 0, darkTargetSkipped: 0,
    gradientLookupExecuted: 0, firstAwaitEntered: 0,
    state1Entered: 0, state2Entered: 0, loaderNullThrowEntered: 0 };
  const latch = (where, error) => {
    if (fault === null) fault = where + ": " + String(error);
    emit({ status: "monster_headless_boundary_fault", where, error: String(error) });
  };
  const controllerOf = coroutine => {
    if (coroutine.isNull()) throw new Error("Null original coroutine");
    const controller = coroutine.add(0x20).readPointer();
    if (controller.isNull()) throw new Error("Null original MonsterPrefabController");
    return controller;
  };
  const requireNoGradient = controller => {
    if (!controller.add(0x68).readPointer().isNull())
      throw new Error("Original monster gradient is unexpectedly present");
  };

  // Observe the original state dispatcher, well away from the patched bytes.
  // Frida may relocate more than one instruction for an inline hook, so never
  // attach to 0x61D5E30 immediately adjacent to the branch patch.
  Interceptor.attach(at(0x061D5D6E), {
    onEnter() {
      try {
        const coroutine = this.context.rbx;
        if (coroutine.isNull()) throw new Error("Null original OnLoading coroutine");
        const state = coroutine.add(0x10).readS32();
        if (state !== 0) return;
        const controller = controllerOf(coroutine);
        if (!this.context.rdi.equals(controller))
          throw new Error("Original OnLoading state/controller mismatch");
        requireNoGradient(controller);
        counts.gradientLookupsSkipped++;
      } catch (error) { latch("OnLoading state 0", error); }
    }
  });

  // These observations verify the patched branch reaches the original await
  // and preserve later PreSpawnEvent/completion visibility.
  // They never change original registers, state, events, or results.
  Interceptor.attach(at(0x061D5E67), {
    onEnter() {
      try {
        counts.gradientLookupExecuted++;
        const returnedNull = this.context.rax.isNull();
        emit({ status: "monster_headless_gradient_lookup_executed",
          returnedNull, intendedRedirects: counts.gradientLookupsSkipped });
        if (counts.gradientLookupsSkipped > 0)
          latch("OnLoading branch", "Original graphics lookup executed after private branch patch");
      } catch (error) { latch("gradient lookup observation", error); }
    }
  });
  Interceptor.attach(at(0x061D5E96), {
    onEnter() {
      try {
        counts.firstAwaitEntered++;
        emit({ status: "monster_headless_original_first_await_entered",
          state: this.context.rbx.add(0x10).readS32() });
      } catch (error) { latch("first await observation", error); }
    }
  });
  Interceptor.attach(at(0x061D5D9A), {
    onEnter() {
      try {
        counts.state1Entered++;
        emit({ status: "monster_headless_original_prespawn_state_entered",
          firstAwaitEntered: counts.firstAwaitEntered });
      } catch (error) { latch("prespawn state observation", error); }
    }
  });
  Interceptor.attach(at(0x061D5D80), {
    onEnter() {
      try {
        counts.state2Entered++;
        emit({ status: "monster_headless_original_load_completion_entered",
          state1Entered: counts.state1Entered });
      } catch (error) { latch("load completion observation", error); }
    }
  });
  Interceptor.attach(at(0x061D5ECD), {
    onEnter() {
      try {
        counts.loaderNullThrowEntered++;
        emit({ status: "monster_headless_original_loader_null_throw",
          firstAwaitEntered: counts.firstAwaitEntered,
          state1Entered: counts.state1Entered, state2Entered: counts.state2Entered,
          gradientLookupExecuted: counts.gradientLookupExecuted });
      } catch (error) { latch("loader null throw observation", error); }
    }
  });

  // InitColor already executed its original yield when it reaches this point.
  // The patched null-gradient JE reaches original completion at 0x61D4B08.
  Interceptor.attach(at(0x061D4ABF), {
    onEnter() {
      try {
        const coroutine = this.context.rbx;
        const controller = controllerOf(coroutine);
        if (!this.context.rsi.equals(controller) ||
            coroutine.readS32() !== -1 || coroutine.add(0x18).readPointer().isNull())
          throw new Error("Original InitColor state/controller/prefab mismatch");
        requireNoGradient(controller);
      } catch (error) { latch("InitColor tint", error); }
    }
  });
  Interceptor.attach(at(0x061D4B08), {
    onEnter() {
      try {
        const coroutine = this.context.rbx;
        const controller = controllerOf(coroutine);
        if (coroutine.readS32() !== -1 || this.context.rdi.isNull())
          throw new Error("Original InitColor completion state/prefab mismatch");
        requireNoGradient(controller);
        counts.tintCompletions++;
      } catch (error) { latch("InitColor completion", error); }
    }
  });

  // Both original dark-change handlers only write monster/material/background
  // colors. Retained NativeCallbacks replace these color-only methods; no
  // context.pc redirection is used and no spawn/HP/damage method is replaced.
  const retainedCallbacks = [];
  const skipColorEvent = (entry, key) => {
    const callback = new NativeCallback(function (controller) {
      try {
        if (controller.isNull()) throw new Error("Null original MonsterPrefabController");
        requireNoGradient(controller);
        counts[key]++;
      } catch (error) { latch(key, error); }
    }, "void", ["pointer", "pointer", "pointer"]);
    retainedCallbacks.push(callback);
    Interceptor.replace(at(entry), callback);
  };
  skipColorEvent(0x061C69C0, "darkOffSkipped");
  skipColorEvent(0x061C6C40, "darkTargetSkipped");

  emit({ status: "monster_headless_boundary_installed",
    installedClientSha256: expectedClient,
    privateProcessPatches: patches.map(p => ({ rva: "0x" + p.rva.toString(16),
      originalBytes: p.original, patchedBytes: p.patched,
      readbackVerified: hexAt(at(p.rva), p.patched.length / 2) === p.patched })),
    onLoadingFirstAwaitRva: "0x061D5E96", initColorCompletionRva: "0x061D4B08",
    preserved: ["original OnLoading await", "original PreSpawnEvent.SendAsync await",
      "original IsResourceLoad completion", "original CreateMonster", "original SpotMonster"] });
  // Retain interceptors until normal player exit, as with other private probes.
  return {
    check() { if (fault !== null) throw new Error(fault); },
    snapshot() { return { ...counts, fault }; },
    retainedCallbacks
  };
}
