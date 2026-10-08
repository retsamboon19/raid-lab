// Results-only private player: NKAudioSource's sound-loading/playback entry
// points have no combat-state writes. Keep QTE directors/colliders/lifecycle.
// Source: 0759B9B0 Awake starts LoadAsync; 0759C310 OnEnable forwards Play;
// 0759C5A0 Play queues playback; 0759C380 PlayInternal calls the sound service.
function installMechanicsAudioBoundary(emit) {
  const client = "2df7134a6a9c3a8dbbde88402fc8d16d1d6c3f4c2d5e262bea78c3d78b96dd02";
  if (globalThis.MECHANICS_GEOMETRY_SOURCE.installed_client_sha256 !== client)
    throw new Error("Audio boundary requires the exact installed client receipt");
  const base = Process.getModuleByName("GameAssembly.dll").base;
  const audio = Il2Cpp.domain.assembly("NK.Sound.Common").image.class("NK.NKAudioSource");
  const specs = [["Awake", 0x0759B9B0, "40564881eca0000000803dc1"],
    ["OnEnable", 0x0759C310, "40534883ec2080792800488b"],
    ["Play", 0x0759C5A0, "40534883ec20803dd97c0004"],
    ["PlayInternal", 0x0759C380, "48895c241848897c24204156"]];
  for (const [name, rva, expected] of specs) {
    const method = audio.method(name, 0);
    const actual = Array.from(new Uint8Array(base.add(rva).readByteArray(12)),
      x => x.toString(16).padStart(2, "0")).join("");
    if (!method.virtualAddress.equals(base.add(rva)) || actual !== expected)
      throw new Error("Original audio entry mismatch: " + name);
  }
  const counts = {}, callbacks = [];
  for (const [name, rva] of specs) {
    counts[name] = 0;
    const callback = new NativeCallback(() => { counts[name]++; }, "void",
      ["pointer", "pointer"]);
    callbacks.push(callback);
    Interceptor.replace(base.add(rva), callback);
  }
  emit({ status: "mechanics_audio_boundary_installed", installedClientSha256: client,
    methods: specs.map(([name, rva]) => ({ name, rva: "0x" + rva.toString(16) })),
    scope: "sound loading and playback only; original QTE timing/colliders retained" });
  return { snapshot() { return { ...counts }; }, retainedCallbacks: callbacks };
}
