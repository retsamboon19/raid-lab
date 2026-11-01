// Explicit private-host UI/output boundary, not original scene callbacks.
// The original battle produces results. This adapter retains their references;
// it never changes combat, sends account requests, retries or drives pause UI.
function createPracticeHostCallbacks(runtime,pin,emit) {
  const transporter=runtime.class('NK.Spot.Data.NKSpotDataTransporter');
  if (transporter.valueTypeSize!==376)
    throw new Error('Current153 host callback transporter layout changed');
  const allowed=new Set(['OnSpotPauseFirstButton','OnSpotPauseSecondButton',
    'OnBattleFinish','OnBattleRetry']);
  const cache=new Map(), received=[];
  let fault=null, originalFinishObserver=null;
  const live=value=>value!=null&&!value.isNull();
  function latch(message) {
    if (fault===null) {
      fault=message!==null&&typeof message==='object'?message:new Error(String(message));
      // A failing evidence sink must not throw through the native delegate.
      // The retained fault is checked by the outer runner after the callback.
      try { emit({status:'practice_host_callback_fault',error:String(fault),
        nativeFrames:fault.nativeFrames||[]}); }
      catch (_) { /* preserve the first failure without recursive logging */ }
    }
  }
  function receive(name,value) {
    try {
      if (name!=='OnBattleFinish') {
        latch('Unexpected '+name+' invocation during unattended original practice');
        return;
      }
      if (!live(value)) throw new Error('Original battle finish callback has no result');
      if (received.length) throw new Error('Duplicate original battle finish callback');
      const original=pin(value);
      received.push(original);
      emit({status:'practice_host_original_result_received',callback:name,
        originalType:original.class.type.name,originalResultRetained:true,
        combatStateMutated:false,accountRequestSent:false});
      if (typeof originalFinishObserver!=='function')
        throw new Error('Original finish observer was not registered before callback');
      // The original request builder runs synchronously in this callback,
      // before SpotFinish destroys contexts. Preserve that lifetime window.
      originalFinishObserver(original);
    } catch (error) { latch(error); }
  }
  function resolveNativeOwnerField(spec) {
    if (!spec || !allowed.has(spec.name))
      throw new Error('Unsupported private host callback field');
    if (cache.has(spec.name)) return cache.get(spec.name);
    const field=transporter.field(spec.name);
    if (field.type.name!==spec.type || field.offset!==spec.offset || field.isStatic)
      throw new Error('Private host callback native field contract changed: '+spec.name);
    const tuple=spec.name.startsWith('OnSpotPause');
    let value;
    if (tuple) {
      const label=spec.semanticTuple?.Item1;
      if (typeof label!=='string' || spec.valueSize!==16 ||
          spec.semanticTuple?.Item2?.nativeType!=='UnityEngine.Events.UnityAction')
        throw new Error('Captured pause tuple has unsupported shape');
      const klass=field.type.class;
      if (!klass.isValueType || klass.valueTypeSize!==16)
        throw new Error('Original pause tuple layout changed');
      const actionType=klass.field('Item2').type.class;
      const action=pin(Il2Cpp.delegate(actionType,()=>receive(spec.name,null)));
      const labelObject=Il2Cpp.string(label);
      pin(new Il2Cpp.Object(labelObject.handle));
      value=pin(klass.alloc());
      invokeChecked(klass.method('.ctor').overload('System.String','UnityEngine.Events.UnityAction'),
        value.unbox(),[labelObject.handle,action.handle]);
      const observed=value.unbox().field('Item1').value;
      if (new Il2Cpp.String(observed.handle).content!==label ||
          !value.unbox().field('Item2').value.handle.equals(action.handle))
        throw new Error('Original pause tuple constructor readback differs');
    } else {
      if (spec.type!=='System.Action<NK.Spot.Interface.ISpotBattleResult>')
        throw new Error('Captured result callback signature changed');
      value=pin(Il2Cpp.delegate(field.type.class,result=>receive(spec.name,result)));
    }
    const receipt={kind:'host_output_boundary',sourceNativeType:spec.type,
      fieldName:spec.name,behavior:spec.name==='OnBattleFinish'
        ? 'retain_result_and_capture_original_packet_before_cleanup':'reject_if_invoked_unattended',
      sourceNativeFieldOffset:spec.offset,originalUiCallbacksReplayed:false,
      mutatesCombatState:false,submitsAccountData:false,
      originalPacketCaptureBeforeCleanup:spec.name==='OnBattleFinish',
      capturedTupleLabelPreserved:tuple,
      callbackCallsiteAudit:'pending',fullAccuracyVerified:false};
    const row={value,receipt};
    cache.set(spec.name,row);
    emit({status:'practice_host_callback_bound',...receipt});
    return row;
  }
  return {resolveNativeOwnerField,check(){if(fault)throw fault;},
    setOriginalFinishObserver(observer) {
      if (typeof observer!=='function' || originalFinishObserver!==null || received.length)
        throw new Error('Original finish observer must be registered exactly once before finish');
      originalFinishObserver=observer;
    },
    snapshot(){return {boundFields:[...cache.keys()],receivedResultCount:received.length,
      fault:fault===null?null:String(fault),nativeFrames:fault?.nativeFrames||[],
      originalFinishObserverRegistered:originalFinishObserver!==null,
      originalUiCallbacksReplayed:false,combatStateMutated:false};},
    getOriginalResults(){return received.slice();}};
}
