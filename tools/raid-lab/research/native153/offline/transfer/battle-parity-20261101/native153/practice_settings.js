// Restore captured preferences through original current153 native setters.
// This is private-profile input preparation, not combat implementation.
function initializeCapturedPracticeSettings(runtime, pin, emit) {
  const source=globalThis.PRACTICE_SETTINGS_INPUT;
  const game=Process.getModuleByName('GameAssembly.dll');
  if (!source || source.schemaVersion!==1 || source.clientSha256!==
      'd39896d3770888039c728a1908448c3db5efa7cdf874c90d56f46d8d566428d2')
    throw Error('Exact captured153 settings required');
  const settingsClass=runtime.class('NK.Common.System.Settings.NikkeSettings');
  const spotClass=runtime.class('NK.Spot.Common.SpotSettings');
  const readStatic=new NativeFunction(game.getExportByName('il2cpp_field_static_get_value'),
    'void',['pointer','pointer']);
  const hex=(p,n)=>Array.from(new Uint8Array(p.readByteArray(n)),
    x=>x.toString(16).padStart(2,'0')).join('');
  const primitives=new Set(['System.Boolean','System.Byte','System.SByte','System.Int16',
    'System.UInt16','System.Int32','System.UInt32','System.Int64','System.UInt64',
    'System.Char','System.Single','System.Double']);
  const rows=[];
  for (const name of ['GameSetting','ControlSetting','VideoSetting']) {
    const input=source.settings[name], layout=source.layouts[input.$type];
    const klass=runtime.class(input.$type), size=input.$valueSize;
    if (!klass.isValueType || klass.valueTypeSize!==size || layout.valueSize!==size ||
        input.rawHex.length!==size*2 || !/^[0-9a-f]+$/.test(input.rawHex))
      throw Error('Preference value layout mismatch '+name);
    for (const field of klass.fields.filter(f=>!f.isStatic)) {
      const expected=layout.fields.find(f=>f.name===field.name && !(f.flags&0x10));
      if (!expected || expected.offset!==field.offset || expected.type!==field.type.name)
        throw Error('Preference field layout mismatch '+name+'.'+field.name);
      // Cross-process raw bytes are safe only for primitives and inline enums.
      if (!primitives.has(field.type.name) && !field.type.class.isEnum)
        throw Error('Reference/nested preference field cannot be copied '+field.type.name);
    }
    const getter=settingsClass.method('get_'+name,0), setter=settingsClass.method('set_'+name,1);
    if (!getter.virtualAddress.equals(game.base.add(source.nativeMethods['get_'+name])) ||
        !setter.virtualAddress.equals(game.base.add(source.nativeMethods['set_'+name])))
      throw Error('Preference original method mismatch '+name);
    pin(invokeChecked(getter,null)); // Original lazy preference initialization.
    const box=pin(klass.alloc());
    box.unbox().handle.writeByteArray(input.rawHex.match(/../g).map(x=>parseInt(x,16)));
    invokeChecked(setter,null,[box.unbox().handle]);
    const readback=pin(invokeChecked(getter,null));
    if (hex(readback.unbox().handle,size)!==input.rawHex)
      throw Error('Original preference setter readback differs '+name);
    rows.push({name,size,originalGetterRva:source.nativeMethods['get_'+name],
      originalSetterRva:source.nativeMethods['set_'+name],rawHex:input.rawHex});
  }
  const injector=runtime.class('NK.Common.Scene.Unit.SpotDependencyInjector')
    .method('InjectNikkeSettings',0);
  if (!injector.virtualAddress.equals(game.base.add(0x0707B120)))
    throw Error('Original settings injector changed');
  invokeChecked(injector,null);
  for (const row of rows) {
    const field=spotClass.field(row.name), value=Memory.alloc(row.size);
    if (field.type.class.valueTypeSize!==row.size) throw Error('Spot setting size changed');
    readStatic(field.handle,value);
    if (hex(value,row.size)!==row.rawHex) throw Error('Original injected settings differ '+row.name);
  }
  const fps=Il2Cpp.domain.assembly('NK.Types').image.class(source.frameRateBinding.enum)
    .field(source.frameRateBinding.literal);
  const fpsValue=Memory.alloc(4); readStatic(fps.handle,fpsValue);
  if (fpsValue.readS32()!==source.frameRateBinding.value || source.frameRate!==60)
    throw Error('Original configured FPS mapping changed');
  emit({status:'original_captured_practice_settings_restored', settings:rows,
    configuredFrameRate:source.frameRate, sourceCaptureSha256:source.sourceCaptureSha256,
    nativeProducerRva:'0x0707B120', privateProfileOnly:true});
  return {frameRate:source.frameRate, settings:rows};
}
