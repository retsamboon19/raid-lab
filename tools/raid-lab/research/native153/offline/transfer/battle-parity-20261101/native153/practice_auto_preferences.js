// Explicit host control inputs, matching requested/observed full-auto behavior.
// These are NOT raw preferences captured from the three installed references.
// Caller must first prove private PlayerPrefs isolation, then call on main before
// normal manager context loading. Preserve original DataContext.InitAutoMode(null).
function prepareOriginalPracticeAutoPreferences(runtime, pin, emit) {
  const binding={
    clientSha256:'d39896d3770888039c728a1908448c3db5efa7cdf874c90d56f46d8d566428d2',
    preferencesMetadataSha256:'992150d0e3d19c8c44eaf968e86d6d8f49643382941270b31cc363980bab1f63',
    playerPrefsMetadataSha256:'d09bd5d676570c10a4d5da0193756aee5e0df60a2a0dfb0fd988aeddb945c8e5',
    keyAndEnumMetadataProofSha256:'6d66e14af5044947a8bddf607ec385e82cc721c3976ccc394f72408bae36c924',
    getIntRva:0x06d95560,setIntRva:0x06d95730,contentsOpenRva:0x075fc0f0,
    contentsOpenType:'NK.StaticData.ContentsOpen',contentsOpenName:'Spot_AutoControl',
    contentsOpenValue:32
  };
  if(Process.pointerSize!==8||typeof pin!=='function'||typeof emit!=='function'||
      typeof intArg!=='function'||typeof invokeChecked!=='function'||
      globalThis.MECHANICS_GEOMETRY_SOURCE?.installed_client_sha256!==binding.clientSha256)
    throw Error('Auto preference inputs require exact current153 source/main-thread helpers');
  const prefs=runtime.class('NK.Common.System.NKPlayerPrefs');
  const getInt=prefs.method('GetInt',2),setInt=prefs.method('SetInt',2);
  const contentsOpen=runtime.class('NK.Spot.Util.CommonUtil').method('IsOpenedContents',1);
  const game=Process.getModuleByName('GameAssembly.dll');
  const check=(method,rva,returns,parameters)=>{
    if(!method.isStatic||method.returnType.name!==returns||
        method.parameters.map(value=>value.type.name).join('|')!==parameters.join('|')||
        !method.virtualAddress.equals(game.base.add(rva)))
      throw Error('Current153 original auto preference method changed at '+rva.toString(16));
  };
  check(getInt,binding.getIntRva,'System.Int32',['System.String','System.Int32']);
  check(setInt,binding.setIntRva,'System.Void',['System.String','System.Int32']);
  check(contentsOpen,binding.contentsOpenRva,'System.Boolean',[binding.contentsOpenType]);
  const hex=(rva,size)=>Array.from(new Uint8Array(game.base.add(rva).readByteArray(size)),
    value=>value.toString(16).padStart(2,'0')).join('');
  for(const [rva,bytes]of [
    [binding.getIntRva,'4533c0e998f57801'],
    [binding.setIntRva,'4533c0e9d8f57801'],
    [binding.contentsOpenRva,'40534883ec30803d290d3504008bd975'],
    [0x08524b00,'48895c2408574883ec20488b05c74643'],
    [0x08524d10,'48895c2408574883ec20488b059f4443']
  ])if(hex(rva,bytes.length/2)!==bytes)
    throw Error('Original auto preference/contents code changed at '+rva.toString(16));
  const rows=[];
  for(const key of ['SpotAutoAimMode','SpotAutoSkillMode']){
    const text=Il2Cpp.string(key);
    pin(new Il2Cpp.Object(text.handle));
    invokeChecked(setInt,null,[text.handle,intArg(1)]);
    const readback=invokeChecked(getInt,null,[text.handle,intArg(0)]).unbox().handle.readS32();
    if(readback!==1)throw Error('Original private preference readback differs: '+key);
    rows.push({key,requestedValue:1,nativeReadback:readback,defaultValueUsedByOriginalInit:0});
  }
  function readNativeContentsOpen(){
    const raw=invokeChecked(contentsOpen,null,[intArg(binding.contentsOpenValue)])
      .unbox().handle.readU8();
    if(raw!==0&&raw!==1)throw Error('Original auto contents gate returned malformed boolean');
    const evidence={contentsOpenName:binding.contentsOpenName,
      contentsOpenValue:binding.contentsOpenValue,nativeContentsOpen:raw===1,
      contentsGateChanged:false,nullableForcedModeUsed:false};
    emit({status:'original_auto_contents_gate_readback',...evidence});
    return evidence;
  }
  const gate=readNativeContentsOpen();
  const evidence={...binding,preferences:rows,...gate,
    inputKind:'explicit_host_control_input_matching_requested_and_observed_full_auto',
    originalRawPreferenceValuesCaptured:false,profileIsolationVerifiedByThisModule:false,
    callerMustConfirmPrivatePreferencesIsolation:true,beforeNormalContextLoadingRequired:true,
    originalPreferenceSettersUsed:true,normalNullableAbsentInitializationPreserved:true,
    initEventConstructedByHost:false,autoSwitchEventSent:false,teamFieldsWritten:false,
    clockOrCounterFieldsWritten:false,explicitPlayerPrefsSaveCalled:false,
    autoModeActiveVerified:false};
  emit({status:'original_practice_auto_preference_inputs_prepared',...evidence});
  return {evidence,readNativeContentsOpen,contentsOpenMethod:contentsOpen};
}
