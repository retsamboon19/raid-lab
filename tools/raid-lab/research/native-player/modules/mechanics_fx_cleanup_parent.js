// Private-process adaptation of the cleanup parent only. The original FX
// dictionary lookup, live-handle loop, callbacks and reactive removal execute.
// See FX-CLEANUP-TRIAL66.md; this is not a replacement FX implementation.
function installMechanicsFxCleanupParent(state, pin, emit) {
  const client = "2df7134a6a9c3a8dbbde88402fc8d16d1d6c3f4c2d5e262bea78c3d78b96dd02";
  const receipt = "fabe414859d5ed3d7486b3ab6b2bc979847c01fa56c793b0832f2c35e33bf2fc";
  if (!state || state.status !== "ready" || state.clientSha256 !== client ||
      state.commonGeometryReceiptSha256 !== receipt ||
      state.sourceReceiptSha256 !== globalThis.MECHANICS_GEOMETRY_SOURCE_SHA256 ||
      Process.pointerSize !== 8)
    throw new Error("FX parent requires the verified original geometry hierarchy");
  const root = state.instances.prefab_root;
  if (!root || root.isNull()) throw new Error("Original PrefabControl is absent");
  const parent = pin(invokeChecked(root.method("get_transform", 0), root));
  if (!parent || parent.isNull() || parent.class.type.name !== "UnityEngine.Transform")
    throw new Error("Original PrefabControl Transform is absent or has wrong type");
  const self = invokeChecked(parent.method("get_transform", 0), parent);
  if (!self || !self.handle.equals(parent.handle))
    throw new Error("Original Component.get_transform did not preserve parent identity");
  const game = Process.getModuleByName("GameAssembly.dll");
  const hexAt = (rva, size) => Array.from(new Uint8Array(
    game.base.add(rva).readByteArray(size)), x => x.toString(16).padStart(2, "0")).join("");
  const rva = 0x06159260;
  const original = "488b15d145ba04488bc8e8115290fa";
  if (hexAt(0x06159150, 10) !== "488954241048894c2408" ||
      hexAt(rva, 15) !== original)
    throw new Error("Original RemoveFunctionFx bytes changed or old wrapper is still installed");
  const pointer = Memory.alloc(8);
  pointer.writePointer(parent.handle);
  const replacement = [0x48, 0xb8, ...new Uint8Array(pointer.readByteArray(8)),
    0x90, 0x90, 0x90, 0x90, 0x90];
  const patched = replacement.map(x => x.toString(16).padStart(2, "0")).join("");
  const write = bytes => Memory.patchCode(game.base.add(rva), 15,
    writable => writable.writeByteArray(bytes));
  try {
    write(replacement);
    if (hexAt(rva, 15) !== patched) throw new Error("FX parent patch readback mismatch");
  } catch (error) {
    write(original.match(/../g).map(x => parseInt(x, 16)));
    if (hexAt(rva, 15) !== original) throw new Error("FX parent patch rollback failed: " + error);
    throw error;
  }
  let fault = null;
  const counts = { calls: 0, liveCollections: 0, originalRemovalsVerified: 0,
    activeDespawnCalls: 0, despawnCalls: 0, completionCallbacks: 0 };
  const listeners = [];
  const latch = error => {
    if (fault !== null) return;
    fault = String(error);
    emit({ status: "mechanics_fx_cleanup_parent_fault", error: fault });
  };
  const lookup = (dictionary, key) => {
    const slot = Memory.alloc(Process.pointerSize); slot.writePointer(NULL);
    const found = invokeChecked(dictionary.method("TryGetValue", 2), dictionary,
      [key, slot]).unbox().handle.readU8() !== 0;
    return { found, collection: slot.readPointer() };
  };
  // Ordinary method-entry observers only; no mid-function hooks or register edits.
  listeners.push(Interceptor.attach(game.base.add(0x06159150), {
    onEnter(args) {
      counts.calls++;
      try {
        this.dictionary = new Il2Cpp.Object(args[1]);
        this.key = args[0].add(0x20).readPointer();
        const entry = lookup(this.dictionary, this.key);
        this.hadKey = entry.found;
        if (entry.found) {
          if (entry.collection.isNull()) throw new Error("Null original FX collection");
          const collection = new Il2Cpp.Object(entry.collection);
          const count = invokeChecked(collection.method("get_Count", 0), collection)
            .unbox().handle.readS32();
          this.liveCount = count;
          if (count > 0) counts.liveCollections++;
        }
      } catch (error) { latch(error); }
    },
    onLeave() {
      try {
        if (!this.hadKey) return;
        if (lookup(this.dictionary, this.key).found)
          throw new Error("Original FX cleanup returned with its key still present");
        counts.originalRemovalsVerified++;
        if (this.liveCount > 0) emit({ status: "original_live_fx_cleanup_returned",
          liveHandleCount: this.liveCount, nativeKeyRemoved: true, ...counts });
      } catch (error) { latch(error); }
    }
  }));
  for (const [methodRva, counter] of [[0x062F13F0, "activeDespawnCalls"],
    [0x0568CEB0, "despawnCalls"], [0x06170E70, "completionCallbacks"]]) {
    listeners.push(Interceptor.attach(game.base.add(methodRva), {
      onEnter() { counts[counter]++; }
    }));
  }
  emit({ status: "mechanics_fx_cleanup_parent_installed", installedClientSha256: client,
    sourceReceiptSha256: state.sourceReceiptSha256, commonGeometryReceiptSha256:receipt,
    patchRva: "0x06159260", originalBytes: original,
    patchedBytes: patched, parentAssetKey: "PrefabControl",
    parentAssetGuid: "9022068b08512344181fc634755eff39",
    parentPointer: parent.handle.toString(), parentType: parent.class.type.name,
    originalCleanupLoopPreserved: true, visualPoolPlacementEquivalent: false });
  return { check() { if (fault !== null) throw new Error(fault); },
    snapshot() { return { ...counts, fault }; }, retainedListeners: listeners };
}
