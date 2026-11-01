// Passive current153 observation for a later reviewed unmodified-color candidate.
// No branch edits, callback replacement, native getters, or combat-state writes.
function installPracticeMonsterColorObserver(emit) {
  const client='d39896d3770888039c728a1908448c3db5efa7cdf874c90d56f46d8d566428d2';
  const sourceReceiptSha256='07e954c5a819259cf7d3d1f07576aa87a6b0e80949ba50debd22f3f01d9e5a2f';
  if (typeof emit!=='function' || Process.pointerSize!==8 ||
      globalThis.MECHANICS_GEOMETRY_SOURCE?.installed_client_sha256!==client)
    throw new Error('Monster color observer requires exact current153 source binding');
  const game=Process.getModuleByName('GameAssembly.dll');
  const runtime=Il2Cpp.domain.assembly('NK.Runtime').image;
  const controller=runtime.class('NK.Spot.Presentation.MonsterPrefabController');
  const loading=controller.nested('<OnLoading>d__32');
  const tint=controller.nested('<InitColor>d__37');
  if (controller.field('_monterGradient').offset!==0x68 ||
      controller.field('_monterGradient').type.name!=='NK.Spot.DayNight.NKEnvGlobalGradient_Monster' ||
      loading.isValueType || loading.field('<>4__this').offset!==0x20 ||
      !tint.isValueType || tint.valueTypeSize!==48 || tint.field('<>4__this').offset!==0x30)
    throw new Error('Current153 monster coroutine/gradient metadata changed');
  const methods=[
    {name:'loading',method:loading.method('MoveNext',0),rva:0x0557af20,
      returns:'System.Boolean',parameters:[],prefix:'48895c2418574883ec30803da9003c06'},
    {name:'initColor',method:tint.method('MoveNext',0),rva:0x05575940,
      returns:'System.Void',parameters:[],prefix:'48894c24085356574883ec40488bd980'},
    {name:'darkOff',method:controller.method('OnDarkChangeOff',1),rva:0x05454070,
      returns:'System.Void',parameters:['NK.Spot.Common.SpotEvent'],prefix:'48895c2410488974241848894c240857'},
    {name:'darkTarget',method:controller.method('OnDarkChangeOnTarget',1),rva:0x05454300,
      returns:'System.Void',parameters:['NK.Spot.Common.SpotEvent'],prefix:'48894c2408535657415641574881ec90'}
  ];
  const hex=(rva,size)=>Array.from(new Uint8Array(game.base.add(rva).readByteArray(size)),
    value=>value.toString(16).padStart(2,'0')).join('');
  // Includes original GetPresentation<SpotGraphicOptions>, env lookup and store.
  const lookupBytes='488b0da2dea80583b9e0000000007505e814bf23fb33c9e81dd808024885c07475488b1591aaab05488bc8e8a95553fb4885c07461488b48384885c97458488b15947eab05e87feae4fb4885ff7447488d4f6848894768488bd0e8aa582cfb';
  for (const row of methods) {
    const method=row.method;
    if (method.isStatic || method.returnType.name!==row.returns ||
        method.parameters.map(value=>value.type.name).join('|')!==row.parameters.join('|') ||
        !method.virtualAddress.equals(game.base.add(row.rva)) ||
        hex(row.rva,row.prefix.length/2)!==row.prefix)
      throw new Error('Original current153 monster method identity/prefix changed: '+row.name);
  }
  if (hex(0x0557b047,lookupBytes.length/2)!==lookupBytes ||
      hex(0x05575a03,6)!=='0f8445010000')
    throw new Error('Original monster lookup/tint branches changed or old color adapter is installed');
  const counts=Object.fromEntries(methods.map(row=>[row.name,{entries:0,normalReturns:0,
    entryRecords:0,returnRecords:0}]));
  const retainedListeners=[],recordLimitPerKindPerMethod=4;
  let fault=null,diagnosticErrors=0;
  const latch=error=>{
    diagnosticErrors++;
    if (fault!==null) return;
    fault=String(error);
    try { emit({status:'practice_monster_color_observer_fault',error:fault}); }
    catch (_) { /* Never throw through an original native call. */ }
  };
  for (const row of methods) {
    const counter=counts[row.name];
    retainedListeners.push(Interceptor.attach(row.method.virtualAddress,{
      onEnter() {
        try {
          this.originalColorObserved=true;
          this.callId=++counter.entries;
          if (counter.entryRecords>=recordLimitPerKindPerMethod) return;
          counter.entryRecords++;
          emit({status:'original_practice_monster_color_entry',method:row.name,
            rva:'0x'+row.rva.toString(16),callId:this.callId,
            nativeGettersInvokedByObserver:false,argumentsChanged:false});
        } catch (error) { latch(error); }
      },
      onLeave() {
        try {
          if (!this.originalColorObserved) return;
          counter.normalReturns++;
          if (counter.returnRecords>=recordLimitPerKindPerMethod) return;
          counter.returnRecords++;
          emit({status:'original_practice_monster_color_returned',method:row.name,
            callId:this.callId,observedNormalNativeReturn:true,colorEffectsVerified:false,
            nativeResultChanged:false,combatStateWritten:false});
        } catch (error) { latch(error); }
      }
    }));
  }
  emit({status:'practice_monster_color_observer_installed',clientSha256:client,
    sourceReceiptSha256,
    originalLookupBytes:lookupBytes,lookupStartRva:'0x0557B047',
    originalTintNullBranch:'0f8445010000',tintNullBranchRva:'0x05575A03',
    originalColorMethodsPreserved:true,branchPatchesInstalled:false,callbacksReplaced:false,
    recordLimitPerKindPerMethod,listenersRetainedUntilExit:true,colorEffectsVerified:false});
  return {retainedListeners,
    check() { if (fault!==null) throw new Error(fault); },
    snapshot() { return {methods:Object.fromEntries(Object.entries(counts).map(([name,value])=>
      [name,{...value,entriesWithoutObservedNormalReturn:value.entries-value.normalReturns}])),
      fault,diagnosticErrors,colorEffectsVerified:false,combatStateWritten:false,
      nativeGettersInvokedByObserver:false,branchPatchesInstalled:false,callbacksReplaced:false,
      listenersRetainedUntilExit:true}; }
  };
}
