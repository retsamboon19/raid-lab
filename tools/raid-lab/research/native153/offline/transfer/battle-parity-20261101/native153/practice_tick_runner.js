'use strict';
// One original native UpdateTick per caller-supplied real Unity Update callback.
// Owns no clock formula, loader transition, OnStart, physics change or result.
function startOriginalPracticeTicks(runtime,management,process,input,emit,finish,captureTerminal,options={}) {
  validateNative153PracticeInput(input);
  if (typeof options.schedule!=='function') throw Error('Practice requires the reviewed real Unity Update scheduler');
  const maxUpdates=options.maxUpdates===undefined?20000:options.maxUpdates;
  const maxWallMs=options.maxWallMs===undefined?60000:options.maxWallMs;
  if (!Number.isSafeInteger(maxUpdates)||maxUpdates<1||maxUpdates>1000000||
      !Number.isSafeInteger(maxWallMs)||maxWallMs<1||maxWallMs>300000)
    throw Error('Practice update/wall guard is invalid');
  const originalUpdate=native153PracticeMethod(runtime.class('NK.Spot.SpotManagement'),
    'UpdateTick',1,0x07607f40);
  const call=(method,self=null,args=[])=>invokeChecked(method,self,args);
  let readDelta=options.readDeltaTime,deltaSource=options.deltaReadbackSource;
  if (readDelta!==undefined) {
    if (typeof readDelta!=='function'||typeof deltaSource!=='string'||deltaSource.length===0)
      throw Error('An explicit delta reader needs its source label');
  } else {
    const time=Il2Cpp.domain.assembly('UnityEngine.CoreModule').image.class('UnityEngine.Time');
    const getter=native153PracticeMethod(time,'get_deltaTime',0,0x0852ebd0);
    readDelta=()=>call(getter).unbox().handle.readFloat();
    deltaSource='original_UnityEngine.Time.get_deltaTime@0x0852EBD0';
  }
  // The old Intercept runner forced this true. Actual references did not
  // capture it, so retain the engine's current value and report that limitation.
  const physics=Il2Cpp.domain.assembly('UnityEngine.PhysicsModule').image.class('UnityEngine.Physics');
  const physicsAutoSyncTransforms=call(physics.method('get_autoSyncTransforms',0))
    .unbox().handle.readU8()!==0;
  const dt=Memory.alloc(4),started=Date.now();
  let updateCalls=0,advancedTicks=0,sawPlaying=false,lastState=null,lastLifecycle=null;
  let stopped=false,scheduleHandle=null,cancelPending=false,finalRow=null,lastPendingReason=null;
  const terminal=new Set([8,9,10]);
  const progress=()=>({completedUpdateCalls:updateCalls,advancedTicks,
    observedPlaying:sawPlaying,lastLifecycle,wallMs:Date.now()-started});
  const stop=(status,detail={})=>{
    if (stopped) return finalRow;
    stopped=true;
    let cleanupError=null;
    if (scheduleHandle) {
      try {scheduleHandle.cancel();} catch(error) {cleanupError=String(error);}
    } else cancelPending=true;
    finalRow={status,...progress(),physicsAutoSyncTransforms,physicsSettingUnchanged:true,
      inputSourceSha256:input.inputSourceSha256,completeBattle:false,resultCaptured:false,
      processStateResultBinding:'unverified',fullAccuracyVerified:false,...detail};
    if (cleanupError) finalRow={...finalRow,status:'first_failure',completeBattle:false,
      error:'Parent frame scheduler cleanup failed: '+cleanupError};
    emit(finalRow);finish(finalRow);return finalRow;
  };
  const fail=error=>stop('first_failure',{stage:'original_practice_update_tick',
    error:String(error),stack:error?.stack||null,nativeFrames:error?.nativeFrames||[]});
  const faultCheck=()=>{
    if (options.checkFault) {
      const fault=options.checkFault();
      if (fault) throw fault instanceof Error?fault:Error(String(fault));
    }
  };
  const managerClock=()=>({tick:Number(management.field('_tickCount').value),
    playTime:Number(management.field('_playtime').value)});
  const verifyTerminal=state=>{
    if (typeof captureTerminal!=='function') throw Error('Original practice result capture is not installed');
    const result=captureTerminal(state);
    if (result?.pending===true) return false;
    if (!result || result.resultCaptured!==true) throw Error('Original practice terminal has no captured result');
    const supplied=typeof options.inputEvidence==='function'?options.inputEvidence():options.inputEvidence||{};
    const actors=typeof options.actorIdentities==='function'?options.actorIdentities():options.actorIdentities;
    const evidence={...supplied,originalActors:actors||supplied.originalActors,
      processClass:lastLifecycle.processClass,processType:lastLifecycle.processType,
      processState:state,observedPlaying:sawPlaying,advancedTicks};
    const verification=verifyOriginal153PracticeTerminal(input,result,evidence);
    if (!verification.passed) {
      stop('original_invalid_practice_result',{...result,verification,
        nativeProcessCompleted:true,completeBattle:false});
      return true;
    }
    stop('original_practice_terminal_result',{...result,verification,
      processState:state,completeBattle:true,scoreCalculated:false});
    return true;
  };
  const runUpdate=()=>{
    if (stopped) return;
    try {
      faultCheck();
      lastLifecycle=readOriginal153PracticeLifecycle(runtime,process);
      if (lastLifecycle.processClass!==NATIVE153_PRACTICE.processClass||lastLifecycle.processType!==9)
        throw Error('Original practice process changed during Update lifecycle');
      if (lastLifecycle.state===6) sawPlaying=true;
      if (lastLifecycle.state!==lastState) {
        emit({status:'original_practice_process_state',...progress(),...managerClock(),
          processState:lastLifecycle.state,stateName:lastLifecycle.stateName});
        lastState=lastLifecycle.state;
      }
      if (terminal.has(lastLifecycle.state)&&verifyTerminal(lastLifecycle.state)) return;
      if (updateCalls>=maxUpdates||Date.now()-started>=maxWallMs) {
        stop('original_practice_limit_reached',{processState:lastLifecycle.state,
          reason:terminal.has(lastLifecycle.state)?'original_result_pending':'update_or_wall_guard'});return;
      }
      // Parent may prepare original geometry/aim or stop a load-only trial.
      // Pending readiness does not suppress the original preload UpdateTick.
      const before=managerClock(),phase={...progress(),...before,lifecycle:lastLifecycle};
      const gate=options.beforeUpdate?options.beforeUpdate(phase):null;
      if (stopped) return;
      if (gate?.pending===true&&gate.reason!==lastPendingReason) {
        lastPendingReason=gate.reason;
        emit({status:'original_practice_preload_pending',reason:gate.reason||'parent_readiness',
          updateStillRuns:true,...progress()});
      }
      faultCheck();
      const delta=readDelta();
      if (!Number.isFinite(delta)||delta<=0||delta>1||Math.fround(delta)!==delta)
        throw Error('Practice UpdateTick delta is not a positive original float32 readback');
      dt.writeFloat(delta);
      call(originalUpdate,management,[dt]);
      updateCalls++;
      const after=managerClock();
      if (after.tick>before.tick) advancedTicks++;
      // Native preloading can advance clock before OnStart. Never reset either
      // clock or claim that the first callback is original tick0.
      lastLifecycle=readOriginal153PracticeLifecycle(runtime,process);
      if (lastLifecycle.state===6) sawPlaying=true;
      const sample={...progress(),...after,lifecycle:lastLifecycle,deltaFloat32:delta,
        deltaSource,managerTickBefore:before.tick};
      if (options.afterUpdate) options.afterUpdate(sample);
      if (stopped) return;
      faultCheck();
      if (updateCalls===1) emit({status:'original_practice_first_update_returned',...sample,
        resultCaptured:false});
      if (options.onSample) options.onSample(sample);
    } catch(error) {fail(error);}
  };
  const controller={stop,snapshot:progress};
  try {
    scheduleHandle=options.schedule(runUpdate,fail);
    if (!scheduleHandle||typeof scheduleHandle.cancel!=='function')
      throw Error('Parent real-frame scheduler did not return a cancellable handle');
    if (cancelPending) scheduleHandle.cancel();
    if (!stopped) emit({status:'original_practice_tick_driver_started',originalEntryRva:'0x07607F40',
      downstreamUpdateSpotRva:'0x07607B30',batchSize:1,maxUpdates,maxWallMs,deltaSource,
      physicsAutoSyncTransforms,physicsSettingUnchanged:true,
      onStartDispatch:'original_Campaign_PostLoadResource',manualStateOrClockWrites:false,
      fullAccuracyVerified:false});
  } catch(error) {fail(error);}
  return controller;
}
