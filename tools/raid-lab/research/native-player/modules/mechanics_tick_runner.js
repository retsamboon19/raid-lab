// Bounded driver of original battle ticks. This changes scheduling, not combat
// state, target choice, resources or outcomes. Terminal results are extracted
// by the caller from the original process; reaching a state alone is not proof
// of an accurate complete battle.
function startOriginalMechanicsTicks(runtime, management, process, emit, finish,
    captureTerminal, options = {}) {
  const batchSize = options.batchSize || 8; // Eight only for the legacy diagnostic scheduler.
  const maxTicks = options.maxTicks || 20000;
  const maxWallMs = options.maxWallMs || 25000;
  const started = Date.now();
  const tickMethod = management.method("UpdateSpot",1);
  const stateMethod = process.method("get_State",0);
  const dt = floatArg(1/30); // Original float32 0.033333335f.
  const state = () => invokeChecked(stateMethod,process).unbox().handle.readS32();
  const states = runtime.class("NK.Spot.Context.Process.ProcessBase").nested("PlayState");
  const enumBuffer=Memory.alloc(4);
  const getEnum=new NativeFunction(Process.getModuleByName("GameAssembly.dll")
    .getExportByName("il2cpp_field_static_get_value"),"void",["pointer","pointer"]);
  const enumInt = name => {
    getEnum(states.field(name).handle,enumBuffer);
    return enumBuffer.readS32();
  };
  const clear=enumInt("Clear"), failed=enumInt("Fail");
  const terminal = new Set([clear,failed]);
  const playing = enumInt("Playing");
  emit({status:"original_native_play_states",clear,failed,playing});
  if (!terminal.has(8) || !terminal.has(9) || playing!==6)
    throw new Error("Original terminal states changed: "+JSON.stringify({clear,failed,playing}));
  const physics=Il2Cpp.domain.assembly("UnityEngine.PhysicsModule").image
    .class("UnityEngine.Physics");
  const priorAutoSync=!!invokeChecked(physics.method("get_autoSyncTransforms",0),null)
    .unbox().handle.readU8();
  const syncValue=Memory.alloc(1); syncValue.writeU8(1);
  invokeChecked(physics.method("set_autoSyncTransforms",1),null,[syncValue]);
  let ticks = 0, advancedTicks = 0, lastState = null, stopped = false, sawPlaying = false;
  const stop = (status, detail = {}) => {
    if (stopped) return;
    stopped = true;
    try {
      if (options.schedule) timer.cancel();
      else clearInterval(timer);
      syncValue.writeU8(priorAutoSync ? 1 : 0);
      invokeChecked(physics.method("set_autoSyncTransforms",1),null,[syncValue]);
    } catch(error) {
      status="first_failure";
      detail={...detail,error:"Physics state restoration: "+String(error),
        completeBattle:false,resultCaptured:false};
    }
    emit({status, completedTickCalls:ticks, advancedTicks,
      wallMs:Date.now()-started, ...detail});
    finish();
  };
  const fail = error => stop("first_failure", {
    stage:"original_battle_ticks", error:String(error),
    nativeFrames:error.nativeFrames || [],
    stack:error.stack || null, completeBattle:false, resultCaptured:false
  });
  const runBatch = () => {
    if (stopped) return;
    try {
      if (firstAsyncFault) {
        const error = new Error(firstAsyncFault.error);
        error.nativeFrames=firstAsyncFault.nativeFrames;
        throw error;
      }
      for (let i=0;i<batchSize;i++) {
        const current=state();
        if (current===playing) sawPlaying=true;
        if (current!==lastState) {
          emit({status:"original_process_state",processState:current,
            completedTickCalls:ticks,tick:Number(management.field("_tickCount").value),
            playTime:Number(management.field("_playtime").value)});
          lastState=current;
        }
        if (terminal.has(current)) {
          if (!sawPlaying || advancedTicks===0) {
            throw new Error("Original process terminated before an observed playing tick");
          }
          const result=captureTerminal(current);
          // Clear/Fail can precede original EndAction dispatch at UpdateSpot's
          // tail. Keep original ticks running within the same bounded budget.
          if (result && result.pending===true) {
            if (ticks>=maxTicks || Date.now()-started>=maxWallMs) {
              stop("original_battle_limit_reached",{processState:current,
                reason:"terminal_result_pending",completeBattle:false,resultCaptured:false});
              return;
            }
          } else {
          // The caller must return an original captured result, never a default.
          if (!result || result.resultCaptured!==true) {
            throw new Error("Original terminal reached without a captured result");
          }
          const expectedResult=current===clear ? 1 : 2;
          if (result.originalResult!==true || result.result!==expectedResult ||
              result.spotResult!==expectedResult || result.retreat!==false ||
              !Array.isArray(result.rounds) ||
              result.rounds.length===0 ||
              result.rounds[result.rounds.length-1].isWin!==(expectedResult===1)) {
            throw new Error("Original terminal/result mismatch or non-battle abort");
          }
          // This runner's fixture is a boss Intercept encounter. The native
          // clock can finish even if no boss ever spawned; reject that result.
          if (!/^[1-9][0-9]*$/.test(result.targetMaxHp || "")) {
            stop("original_invalid_encounter_result",{...result,
              nativeProcessCompleted:true,completeBattle:false,
              error:"Original Intercept result has no populated boss HP",
              fullAccuracyVerified:false});
            return;
          }
          stop("original_terminal_result",{...result,processState:current,
            completeBattle:true,fullAccuracyVerified:false});
          return;
          }
        }
        if (ticks>=maxTicks || Date.now()-started>=maxWallMs) {
          stop("original_battle_limit_reached",{processState:current,
            completeBattle:false,resultCaptured:false});
          return;
        }
        const before=Number(management.field("_tickCount").value);
        if (options.beforeTick) options.beforeTick(ticks);
        invokeChecked(tickMethod,management,[dt]);
        ticks++;
        if (options.afterTick) options.afterTick(ticks);
        if (firstAsyncFault) {
          const error=new Error(firstAsyncFault.error);
          error.nativeFrames=firstAsyncFault.nativeFrames;
          throw error;
        }
        const after=Number(management.field("_tickCount").value);
        if (after!==before) advancedTicks++;
        if (options.onSample && (ticks===1 || ticks%300===0))
          options.onSample({tick:after,processState:state(),completedTickCalls:ticks});
        if (ticks===1) emit({status:"original_first_tick_returned",tickBefore:before,
          tickAfter:after,tickAdvanced:after!==before,processState:state(),
          resultCaptured:false});
      }
    } catch(error) { fail(error); }
  };
  const timer = options.schedule ? options.schedule(runBatch,fail) :
    setInterval(() => onMain(runBatch),10);
  emit({status:"original_tick_driver_started",batchSize,deltaFloat32:Math.fround(1/30),
    maxTicks,maxWallMs,originalCombatMethodsUnchanged:true,
    fullAccuracyVerified:false});
  return {stop};
}
