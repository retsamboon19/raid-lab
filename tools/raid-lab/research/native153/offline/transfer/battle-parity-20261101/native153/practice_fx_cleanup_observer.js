// Passive current153 original cleanup observation. No parent substitution.
// Geometry owns prior native FXController registration/identity verification.
function installPracticeFxCleanupObserver(state, pin, emit) {
  const client='d39896d3770888039c728a1908448c3db5efa7cdf874c90d56f46d8d566428d2';
  const sourceReceiptSha256='46c328521ac8b3f29869e0950eb7f32cfb662f4818bb41017d7326c2b2bdfa16';
  if (typeof emit!=='function' || typeof pin!=='function' || Process.pointerSize!==8 ||
      state?.status!=='ready' || state.clientSha256!==client ||
      state.sourceReceiptSha256!==globalThis.MECHANICS_GEOMETRY_SOURCE_SHA256 ||
      !state.instances?.fx_controller || state.instances.fx_controller.isNull())
    throw new Error('FX cleanup observer requires verified original FX geometry');
  const game=Process.getModuleByName('GameAssembly.dll');
  const runtime=Il2Cpp.domain.assembly('NK.Runtime').image;
  const remove=runtime.class('NK.Spot.Util.FunctionUtil').method('RemoveFunctionFx',2);
  const getter=runtime.class('NK.Spot.Presentation.FXController').method('get_Instance',0);
  const parameterTypes=[
    'NK.Spot.Model.Character.Function.SpotFunction',
    'UniRx.ReactiveDictionary<NK.StaticData.StaticDataLayer.StaticInfo.FunctionStaticInfo,UniRx.ReactiveCollection<System.ValueTuple<NK.Spot.Model.Character.Function.SpotFunctionEffectData,NK.Spot.Presentation.Effect.FxHandle>>>'
  ];
  const hex=(rva,size)=>Array.from(new Uint8Array(game.base.add(rva).readByteArray(size)),
    value=>value.toString(16).padStart(2,'0')).join('');
  const parentLookupBytes='e8c1abeeff4885c00f8474020000488b1501569103488bc8e8492939f94885c00f845c02000033d2488bc8e856eedf00';
  if (!remove.isStatic || remove.returnType.name!=='System.Void' ||
      remove.parameters.map(value=>value.type.name).join('|')!==parameterTypes.join('|') ||
      !remove.virtualAddress.equals(game.base.add(0x0771dbb0)) ||
      !getter.isStatic || getter.returnType.name!=='NK.Spot.Presentation.FXController' ||
      getter.parameters.length!==0 || !getter.virtualAddress.equals(game.base.add(0x0544dc20)) ||
      hex(0x0771dbb0,10)!=='488954241048894c2408' ||
      hex(0x0771dcba,parentLookupBytes.length/2)!==parentLookupBytes ||
      hex(0x0544dc20,16)!=='40534883ec20803d21ca4e0600753748' ||
      hex(0x0544dcbb,15)!=='488b150e56be05488bc8e8562966fb')
    throw new Error('Current153 cleanup/getter identity or unmodified parent lookup differs');
  const counts={entries:0,normalReturns:0,entryRecords:0,returnRecords:0,
    diagnosticErrors:0};
  const recordLimitPerKind=8,retainedListeners=[];
  let fault=null;
  const latch=error=>{
    counts.diagnosticErrors++;
    if (fault!==null) return;
    fault=String(error);
    try { emit({status:'practice_fx_cleanup_observer_fault',error:fault}); }
    catch (_) { /* Never throw through a native callback. */ }
  };
  retainedListeners.push(Interceptor.attach(remove.virtualAddress,{
    onEnter() {
      try {
        this.observedCleanup=true;
        this.callId=++counts.entries;
        if (counts.entryRecords>=recordLimitPerKind) return;
        counts.entryRecords++;
        emit({status:'original_practice_fx_cleanup_entry',callId:this.callId,
          originalMethodRva:'0x0771DBB0',nativeGettersInvokedByObserver:false,
          argumentsChanged:false,combatStateWritten:false});
      } catch (error) { latch(error); }
    },
    onLeave() {
      try {
        if (!this.observedCleanup) return;
        counts.normalReturns++;
        if (counts.returnRecords>=recordLimitPerKind) return;
        counts.returnRecords++;
        emit({status:'original_practice_fx_cleanup_returned',callId:this.callId,
          observedNormalNativeReturn:true,cleanupEffectsVerified:false,
          resultOrStateChanged:false});
      } catch (error) { latch(error); }
    }
  }));
  emit({status:'practice_fx_cleanup_observer_installed',clientSha256:client,
    sourceReceiptSha256,originalMethodRva:'0x0771DBB0',
    parentLookupStartRva:'0x0771DCBA',originalParentLookupBytes:parentLookupBytes,
    originalParentLookupPreserved:true,parentPatchInstalled:false,
    recordLimitPerKind,listenersRetainedUntilExit:true,nativeGettersInvokedByObserver:false,
    originalCallsReplaced:false,cleanupEffectsVerified:false});
  return {retainedListeners,
    check() { if (fault!==null) throw new Error(fault); },
    snapshot() { return {...counts,fault,
      entriesWithoutObservedNormalReturn:counts.entries-counts.normalReturns,
      originalParentLookupPreserved:true,parentPatchInstalled:false,
      nativeGettersInvokedByObserver:false,cleanupEffectsVerified:false,
      listenersRetainedUntilExit:true}; }
  };
}
