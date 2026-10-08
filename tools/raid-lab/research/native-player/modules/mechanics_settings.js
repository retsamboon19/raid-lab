// Original preferences in the isolated scratch profile. The combat snapshot is
// distinct from NikkeSettings and from CatalogDatabase quality selection.
function initializeOriginalMechanicsSettings(runtime, pin, emit) {
  const settingClass=runtime.class("NK.Common.System.Settings.NikkeSettings");
  const spotClass=runtime.class("NK.Spot.Common.SpotSettings");
  const native=Process.getModuleByName("GameAssembly.dll");
  const getStatic=new NativeFunction(native.getExportByName("il2cpp_field_static_get_value"),
    "void",["pointer","pointer"]);
  const bytes=p=>Array.from(new Uint8Array(p)).map(v=>v.toString(16).padStart(2,"0")).join("");
  const call=method=>invokeChecked(method,null);
  const video=pin(call(settingClass.method("get_VideoSetting",0)));
  const videoValue=video.unbox();
  const enumInt=v=>typeof v==="number"?v:Number(v.field("value__").value);
  const types=Il2Cpp.domain.assembly("NK.Types").image;
  const textureHd=enumInt(types.class("NK.Types.System.UserData.TextureQuality").field("HD").value);
  const meshHd=enumInt(types.class("NK.Types.System.UserData.MeshQuality").field("HD").value);
  if (enumInt(videoValue.field("TextureQuality").value)!==textureHd ||
      enumInt(videoValue.field("MeshQuality").value)!==meshHd) {
    // The geometry fixture is the installed HD map. Use the original private
    // preference setter, preserving every unrelated byte in this value type.
    videoValue.field("TextureQuality").value=types.class(
      "NK.Types.System.UserData.TextureQuality").field("HD").value;
    videoValue.field("MeshQuality").value=types.class(
      "NK.Types.System.UserData.MeshQuality").field("HD").value;
    invokeChecked(settingClass.method("set_VideoSetting",1),null,[videoValue.handle]);
  }
  const captured=[];
  for (const [name,size] of [["GameSetting",96],["ControlSetting",24],["VideoSetting",36]]) {
    const field=spotClass.field(name);
    if (field.type.class.valueTypeSize!==size)
      throw new Error("Unexpected original setting size for "+name);
    const before=Memory.alloc(size);
    getStatic(field.handle,before);
    const original=pin(call(settingClass.method("get_"+name,0)));
    captured.push({name,size,field,before:bytes(before.readByteArray(size)),
      expected:bytes(original.unbox().handle.readByteArray(size))});
  }
  // Original producer, recovered at 0x06DC6A70. It copies all three snapshots
  // and installs the normal MultiplayerEnabled delegate without starting UI.
  const injector=runtime.class("NK.Common.Scene.Unit.SpotDependencyInjector")
    .method("InjectNikkeSettings",0);
  if (Number(injector.relativeVirtualAddress)!==0x06dc6a70)
    throw new Error("Original battle settings initializer does not match source");
  call(injector);
  const snapshots=[];
  for (const {name,size,field,before,expected} of captured) {
    const after=Memory.alloc(size);
    getStatic(field.handle,after);
    const actual=bytes(after.readByteArray(size));
    if (actual!==expected) throw new Error("Original setting snapshot mismatch for "+name);
    snapshots.push({name,size,before,after:actual});
  }
  emit({status:"original_battle_settings_copied",privateProfile:true,
    originalProducer:"SpotDependencyInjector.InjectNikkeSettings",producerRva:"0x06DC6A70",
    targetGeometryQuality:"HD",snapshots,gameAndControlSettingsPreserved:true});
}
