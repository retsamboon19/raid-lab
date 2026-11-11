// Candidate only. One original manager tick per real Unity Update callback.
// No capture clock, Cinemachine override, animator patch, dt/RNG/state writes.
function createPracticeFrameScheduler(pin,emit,legacyWallFrameRate,canAccelerate) {
  if(globalThis.PRACTICE_SETTINGS_INPUT?.frameRate!==60 ||
      globalThis.PRACTICE_SETTINGS_INPUT?.frameRateBinding?.literal!=='FPS60')
    throw Error('Original captured FPS60 preference required');
  const core=Il2Cpp.domain.assembly('UnityEngine.CoreModule').image;
  const time=core.class('UnityEngine.Time'),app=core.class('UnityEngine.Application');
  const game=Process.getModuleByName('GameAssembly.dll');
  const call=(method,self=null,args=[])=>invokeChecked(method,self,args);
  const getRate=app.method('get_targetFrameRate',0),setRate=app.method('set_targetFrameRate',1);
  if(!getRate.virtualAddress.equals(game.base.add(0x084D4350)) ||
      !setRate.virtualAddress.equals(game.base.add(0x084D4990)))throw Error('Original frame-rate binding differs');
  // Prove the original environment remains intact; never repair its values.
  // Reuse the frozen scheduler's validated read-only Unity icall rather than
  // require a possibly stripped managed captureDeltaTime accessor.
  const resolve=new NativeFunction(game.getExportByName('il2cpp_resolve_icall'),'pointer',['pointer']);
  const capturePointer=resolve(Memory.allocUtf8String('UnityEngine.Time::get_captureDeltaTime'));
  const captureModule=capturePointer.isNull()?null:Process.findModuleByAddress(capturePointer);
  if(!captureModule||captureModule.name.toLowerCase()!=='unityplayer.dll')throw Error('Original capture-time reader unavailable');
  const capture=new NativeFunction(capturePointer,'float',[])();
  const scale=call(time.method('get_timeScale',0)).unbox().handle.readFloat();
  const cine=Il2Cpp.domain.assembly('Cinemachine').image.class('Cinemachine.CinemachineCore');
  const cineField=cine.field('CurrentTimeOverride');
  if(!cineField.isStatic||cineField.offset!==0x24)throw Error('Original Cinemachine override declaration differs');
  const cineTime=Number(cineField.value);
  const animatorBytes=Array.from(new Uint8Array(game.base.add(0x06486AF5).readByteArray(5)),x=>x.toString(16).padStart(2,'0')).join('');
  if(capture!==0||scale!==1||cineTime!==-1||animatorBytes!=='e816830a02')
    throw Error('Real-time candidate requires untouched original clock/animator environment');
  emit({status:'original_clock_environment_verified',captureDeltaTime:capture,timeScale:scale,
    cinemachineCurrentTimeOverride:cineTime,animatorCallsiteBytes:animatorBytes,
    clockStateWritten:false,animatorCodePatched:false});
  const priorRate=call(getRate).unbox().handle.readS32();
  call(setRate,null,[intArg(60)]);
  if(call(getRate).unbox().handle.readS32()!==60)throw Error('Original FPS60 readback differs');
  const getFrame=time.method('get_frameCount',0);
  const uni=Il2Cpp.domain.assembly('UniTask').image;
  const post=uni.class('Cysharp.Threading.Tasks.UniTask').method('Post',2);
  if(!post.virtualAddress.equals(game.base.add(0x081CF660)))throw Error('Original UniTask.Post differs');
  const phase=uni.class('Cysharp.Threading.Tasks.PlayerLoopTiming').field('Update').value;
  const phaseNumber=typeof phase==='number'?phase:Number(phase.field('value__').value);
  const phaseArg=intArg(phaseNumber);
  const speedExperiment=createNativeSpeedExperiment(pin,emit,globalThis.NATIVE153_SPEED_INPUT||{multiplier:1});
  const frameProfile=createNativeFrameProfile(pin,emit,globalThis.NATIVE153_FRAME_PROFILE_INPUT||{enabled:false});
  globalThis.NATIVE153_FRAME_PROFILE=frameProfile;
  const coherentCapture=createNativeCoherentCaptureExperiment(pin,emit,globalThis.NATIVE153_COHERENT_CAPTURE_INPUT||{enabled:false});
  globalThis.NATIVE153_COHERENT_CAPTURE=coherentCapture;
  const renderInterval=createNativeRenderIntervalExperiment(emit,globalThis.NATIVE153_RENDER_INTERVAL_INPUT||{interval:1});
  globalThis.NATIVE153_RENDER_INTERVAL=renderInterval;
  globalThis.NATIVE153_SPEED_CLOSE=()=>{const errors=[];
    for(const cleanup of [()=>globalThis.NATIVE153_CLOCK_DIAGNOSTIC?.close(null,'capture_restore'),()=>coherentCapture.close(),()=>renderInterval.close(),()=>frameProfile.close(),()=>speedExperiment.close('original_finish_before_cleanup')])try{cleanup();}catch(e){errors.push(e);}
    if(errors.length)throw errors[0];
  };
  let started=false;
  return function schedule(runTick,fail) {
    if(started)throw Error('Real-time scheduler cannot be reused');started=true;
    let active=true,frames=0,lastFrame=call(getFrame).unbox().handle.readS32();
    const cancel=()=>{
      if(!active)return;active=false;const errors=[];
      try{globalThis.NATIVE153_CLOCK_DIAGNOSTIC?.close(null,'scheduler_cancel');}catch(error){errors.push(error);}
      try{coherentCapture.close();}catch(error){errors.push(error);}
      try{renderInterval.close();}catch(error){errors.push(error);}
      try{frameProfile.close();}catch(error){errors.push(error);}
      try{speedExperiment.close();}catch(error){errors.push(error);}
      try{
        call(setRate,null,[intArg(priorRate)]);
        if(call(getRate).unbox().handle.readS32()!==priorRate)throw Error('Original FPS restoration differs');
      }catch(error){errors.push(error);}
      emit({status:'original_unity_real_time_scheduler_stopped',frames,lastFrame,
        restored:errors.length===0,speedExperiment:speedExperiment.summary(),cleanupErrors:errors.map(String)});
      if(errors.length)throw errors[0];
    };
    const action=pin(Il2Cpp.delegate(Il2Cpp.corlib.class('System.Action'),()=>{
      if(!active)return;
      try {
        frameProfile.measure('scheduler_action_total',()=>{
        globalThis.NATIVE153_UNITY_SCOPE_TIMING?.setInsideAction(true);globalThis.NATIVE153_PLAYERLOOP_TIMING?.setInsideAction(true);try{
        const frame=frameProfile.measure('scheduler_frame_getter',()=>call(getFrame).unbox().handle.readS32());
        if(frame<=lastFrame)throw Error('Original combat repeated within one Unity frame');
        lastFrame=frame;frames++;
        frameProfile.measure('scheduler_readiness',()=>{
          speedExperiment.applyIfReady(globalThis.NATIVE153_SPEED_READY);
          frameProfile.applyIfReady(globalThis.NATIVE153_SPEED_READY);
          coherentCapture.check();coherentCapture.applyIfReady(globalThis.NATIVE153_SPEED_READY);
          renderInterval.applyIfReady(globalThis.NATIVE153_SPEED_READY);
        });
        frameProfile.measure('scheduler_callback',runTick); // Original delta reader untouched.
        if(active)frameProfile.measure('scheduler_post',()=>call(post,null,[action.handle,phaseArg]));
        }finally{globalThis.NATIVE153_PLAYERLOOP_TIMING?.setInsideAction(false);globalThis.NATIVE153_UNITY_SCOPE_TIMING?.setInsideAction(false);}
        });
      }catch(error){
        try{cancel();}catch(cleanupError){try{emit({status:'native_speed_cleanup_error',error:String(cleanupError),originalError:String(error)});}catch(_){} }
        fail(error);
      }
    }));
    emit({status:'original_unity_real_time_scheduler_started',phase:'Update',phaseNumber,
      configuredFrameRate:60,accelerated:false,realTimeDeltaSource:'original_UnityEngine.Time.get_deltaTime@0x0852EBD0',
      captureDeltaTimeWritten:false,cinemachineClockWritten:false,animatorCodePatched:false,
      nativeRngWritten:false,nativeCombatStateWritten:false,exactLiveFrameSequence:false});
    try{call(post,null,[action.handle,phaseArg]);}catch(error){cancel();throw error;}
    return {cancel};
  };
}

// Isolated opt-in experiment. Original Unity setters only; no delta injection.
function createNativeSpeedExperiment(pin,emit,input={}) {
  const multiplier=input.multiplier===undefined?1:input.multiplier;
  if(![1,1.5,2,6].includes(multiplier))throw Error("Native speed multiplier must be 1, 1.5, 2 or 6");
  if(typeof pin!=="function"||typeof emit!=="function")throw Error("Native speed experiment requires pin/emit");
  let applied=false,closed=false,restored=false,fault=null,prior=null,manager=null,methods=null,baseline=null,restoreErrors=[];
  let appliedAt=null,closedAt=null,observedBeforeRestore=null;
  const rows={getScale:[139652480,"4883ec28488b05edac42034885c07513488d0d21696500e8","System.Single",true,[]],setScale:[139652832,"4883ec38488b0595ab42030f297424200f28f04885c07513","System.Void",true,["System.Single"]],getRate:[139281232,"4883ec28488b05a52748034885c07513488d0d11946900e8","System.Int32",true,[]],setRate:[139282832,"40534883ec20488b056b2148038bd94885c07513488d0dfd","System.Void",true,["System.Int32"]],manager:[123748320,"4883ec48488b110f29742430f30f1071740f297c2420488b","System.Single",false,[]],dummy:[91342480,"f30f1005a4a61c03c3cccccccccccccc48895c2410488974","System.Single",false,[]]};
  const call=(m,self=null,args=[])=>invokeChecked(m,self,args);
  const float=m=>call(m).unbox().handle.readFloat(),integer=m=>call(m).unbox().handle.readS32();
  const summary=()=>({enabled:multiplier!==1,multiplier,applied,closed,restored,fault,prior,baseline,restoreErrors,appliedAt,closedAt,observedBeforeRestore,originalDeltaTimeUnchanged:true,captureClockWritten:false,cinemachineWritten:false,animatorPatched:false});
  const transition=()=>{try{return manager?{nativeTick:Number(manager.field('_tickCount').value),nativePlaytime:Number(manager.field('_playtime').value),wallMs:Date.now()}:null;}catch(error){return {unavailable:String(error)};}};
  function guard(m,key){const [rva,prefix,returns,isStatic,parameters]=rows[key],game=Process.getModuleByName("GameAssembly.dll");
    const actual=Array.from(new Uint8Array(m.virtualAddress.readByteArray(24)),v=>v.toString(16).padStart(2,"0")).join("");
    if(!m.virtualAddress.equals(game.base.add(rva))||actual!==prefix||m.returnType.name!==returns||m.isStatic!==isStatic||JSON.stringify(m.parameters.map(p=>p.type.name))!==JSON.stringify(parameters))throw Error("Original speed method ABI differs: "+key);
    return m;
  }
  function managerState(){return {tickScale:Number(manager.field("TickScale").value),gameSpeed:Number(manager.field("<GameSpeed>k__BackingField").value),effectiveScale:call(methods.manager,manager).unbox().handle.readFloat(),dummyRva:methods.dummy.virtualAddress.toString()};}
  function checkManager(){const now=managerState();if(JSON.stringify(now)!==JSON.stringify(baseline))throw Error("Original manager speed state changed");}
  function close(reason="caller_closed") {
    if(restored)return summary();
    closed=true;restoreErrors=[];
    if(prior&&methods){
      closedAt=transition();
      try{observedBeforeRestore={scale:float(methods.getScale),rate:integer(methods.getRate)};}catch(error){observedBeforeRestore={unavailable:String(error)};}
      try{call(methods.setScale,null,[floatArg(prior.scale)]);if(float(methods.getScale)!==prior.scale)throw Error("Original Unity scale restore differs");}catch(e){restoreErrors.push(String(e));}
      try{call(methods.setRate,null,[intArg(prior.rate)]);if(integer(methods.getRate)!==prior.rate)throw Error("Original Unity FPS restore differs");}catch(e){restoreErrors.push(String(e));}
      try{checkManager();}catch(e){restoreErrors.push(String(e));}
    }
    restored=restoreErrors.length===0;
    emit({status:"native_speed_experiment_closed",reason,...summary()});
    if(restoreErrors.length)throw Error(restoreErrors.join("; "));
    return summary();
  }
  function applyIfReady(state) {
    if(multiplier===1||closed||applied)return summary();
    if(state?.playing!==true||state?.auto!==true||state?.rng!==true)return summary();
    try{
      manager=pin(state.management);if(!manager||manager.isNull())throw Error("Original speed manager missing");
      const core=Il2Cpp.domain.assembly("UnityEngine.CoreModule").image,time=core.class("UnityEngine.Time"),app=core.class("UnityEngine.Application");
      methods={getScale:guard(time.method("get_timeScale",0),"getScale"),setScale:guard(time.method("set_timeScale",1),"setScale"),getRate:guard(app.method("get_targetFrameRate",0),"getRate"),setRate:guard(app.method("set_targetFrameRate",1),"setRate"),manager:guard(manager.class.method("GetTimeScale",0),"manager"),dummy:guard(manager.class.method("GetDummyTimeScale",0),"dummy")};
      for(const [name,offset]of [["TickScale",116],["<GameSpeed>k__BackingField",120]]){const f=manager.class.field(name);if(f.offset!==offset||f.type.name!=="System.Single"||f.isStatic)throw Error("Original manager speed field ABI differs");}
      const initial={scale:float(methods.getScale),rate:integer(methods.getRate)};
      if(initial.scale!==1||initial.rate!==60)throw Error("Native speed experiment requires original scale1/FPS60");
      baseline=managerState();if(!Number.isFinite(baseline.effectiveScale)||baseline.effectiveScale<=0)throw Error("Original manager scale invalid");
      prior=initial;
      call(methods.setRate,null,[intArg(60*multiplier)]);call(methods.setScale,null,[floatArg(multiplier)]);
      if(integer(methods.getRate)!==60*multiplier||float(methods.getScale)!==multiplier)throw Error("Original Unity speed readback differs");
      checkManager();applied=true;appliedAt=transition();
      emit({status:"native_speed_experiment_applied",processState:6,startupAutoAndRngGatesPassed:true,...summary()});
      return summary();
    }catch(e){fault=String(e&&e.stack||e);try{close("apply_failure");}catch(cleanup){fault+="; "+String(cleanup);}throw Error(fault);}
  }
  return {applyIfReady,close,summary};
}

// Diagnostic only. Original full Unity frames, no combat clock writes.
function createNativeFrameProfile(pin, emit, input = {}) {
  const enabled = input.enabled === undefined ? false : input.enabled;
  if (typeof enabled !== 'boolean') throw Error('Frame profile enabled must be boolean');
  const fullBattleValidation=input.fullBattleValidation===undefined?false:input.fullBattleValidation;
  if(typeof fullBattleValidation!=='boolean')throw Error('Full battle validation must beboolean');
  const limit = 600, warmupSeconds=input.warmupSeconds===undefined?0:input.warmupSeconds;
  if(![0,6.5].includes(warmupSeconds))throw Error('Diagnostic warmup must be0or6.5native seconds');
  let windowStarted=warmupSeconds===0;
  let applied = false, closed = false, restored = false, frames = 0, prior = null;
  let getRate, setRate, fault = null, environment = null, startedAt = null;
  const values = {}, clocks = [], errors = [];
  const call = (m, args = []) => invokeChecked(m, null, args);
  const integer = m => call(m).unbox().handle.readS32();
  const real = m => call(m).unbox().handle.readFloat();
  function stats(a) {
    const ordered = a.slice().sort((a,b) => a-b);
    return {count:a.length,totalMs:a.reduce((a,b)=>a+b,0),
      medianMs:ordered[Math.floor(ordered.length/2)]??null,
      p95Ms:ordered[Math.min(ordered.length-1,Math.floor(ordered.length*.95))]??null,
      maxMs:ordered.length?ordered[ordered.length-1]:null};
  }
  const summary = () => ({enabled,applied,closed,restored,frames,limit,fullBattleValidation,warmupSeconds,windowStarted,prior,environment,fault,
    errors:errors.slice(),startedAt,measurements:Object.fromEntries(Object.entries(values).map(([k,v])=>[k,stats(v)])),
    clockSamples:clocks.slice(),clockWritten:false,combatStateWritten:false});
  function close() {
    if(restored)return summary();
    closed=true;errors.length=0;
    if(prior!==null&&setRate){
      try{call(setRate,[intArg(prior)]);if(integer(getRate)!==prior)throw Error('Profile FPS restoration differs');}
      catch(e){errors.push(String(e));}
    }
    restored=errors.length===0;
    if(enabled)emit({status:'native_frame_profile_closed',...summary()});
    if(errors.length)throw Error(errors.join('; '));
    return summary();
  }
  function applyIfReady(state) {
    if(!enabled||applied||closed)return;
    if(state?.playing!==true||state?.auto!==true||state?.rng!==true)return;
    try{
      const game=Process.getModuleByName('GameAssembly.dll');
      const core=Il2Cpp.domain.assembly('UnityEngine.CoreModule').image;
      const app=core.class('UnityEngine.Application'),time=core.class('UnityEngine.Time');
      getRate=app.method('get_targetFrameRate',0);setRate=app.method('set_targetFrameRate',1);
      for(const [m,rva,returns,params] of [[getRate,0x084D4350,'System.Int32',[]],[setRate,0x084D4990,'System.Void',['System.Int32']]]){
        if(!m.virtualAddress.equals(game.base.add(rva))||!m.isStatic||m.returnType.name!==returns||JSON.stringify(m.parameters.map(p=>p.type.name))!==JSON.stringify(params))throw Error('Profile original FPS ABI differs');
      }
      const getScale=time.method('get_timeScale',0);
      if(!getScale.virtualAddress.equals(game.base.add(0x0852ED80)))throw Error('Profile scale reader differs');
      const resolve=new NativeFunction(game.getExportByName('il2cpp_resolve_icall'),'pointer',['pointer']);
      const captureAddress=resolve(Memory.allocUtf8String('UnityEngine.Time::get_captureDeltaTime'));
      const owner=captureAddress.isNull()?null:Process.findModuleByAddress(captureAddress);
      if(!owner||owner.name.toLowerCase()!=='unityplayer.dll')throw Error('Profile original capture reader unavailable');
      const capture=new NativeFunction(captureAddress,'float',[])();
      const scale=real(getScale),rate=integer(getRate);
      if(scale!==1||capture!==0||rate!==60)throw Error('Profile requires original scale1/capture0/FPS60');
      const readOptional=(className,methodName,kind)=>{
        try{const m=core.class(className).method(methodName,0);const value=call(m);
          return kind==='integer'?value.unbox().handle.readS32():value.content;}
        catch(e){
          if(className==='UnityEngine.QualitySettings'&&methodName==='get_vSyncCount')try{
            const address=resolve(Memory.allocUtf8String('UnityEngine.QualitySettings::get_vSyncCount'));
            const module=address.isNull()?null:Process.findModuleByAddress(address);
            if(!module||module.name.toLowerCase()!=='unityplayer.dll')throw Error('Original vSync icall unavailable');
            return {value:new NativeFunction(address,'int',[])(),source:'original_UnityPlayer_icall'};
          }catch(icallError){return {unavailable:String(e),icallUnavailable:String(icallError)};}
          return {unavailable:String(e)};
        }
      };
      environment={scale,captureDeltaTime:capture,priorRate:rate,
        vSyncCount:readOptional('UnityEngine.QualitySettings','get_vSyncCount','integer'),
        graphicsDeviceName:readOptional('UnityEngine.SystemInfo','get_graphicsDeviceName','string'),
        graphicsDeviceType:readOptional('UnityEngine.SystemInfo','get_graphicsDeviceType','integer')};
      prior=rate;call(setRate,[intArg(-1)]);
      if(integer(getRate)!==-1)throw Error('Profile uncapped FPS readback differs');
      applied=true;startedAt=Date.now();
      emit({status:'native_frame_profile_applied',...summary()});
    }catch(e){fault=String(e&&e.stack||e);try{close();}catch(cleanup){fault+='; '+String(cleanup);}throw Error(fault);}
  }
  function measure(label, fn) {
    if(!enabled||!applied||!windowStarted||closed||frames>=limit)return fn();
    const start=Date.now();try{return fn();}finally{
      if(!Object.prototype.hasOwnProperty.call(values,label)){
        if(Object.keys(values).length>=16)throw Error('Profile label bound exceeded');
        values[label]=[];
      }
      if(values[label].length<limit)values[label].push(Date.now()-start);
    }
  }
  function finishFrame(sample) {
    if(!enabled||!applied||closed||frames>=limit)return;
    if(!windowStarted){
      if(!Number.isFinite(sample?.playTime))throw Error('Profile needs original native playTime');
      if(sample.playTime<warmupSeconds)return;
      windowStarted=true;startedAt=Date.now();
      emit({status:'native_frame_profile_window_started',warmupSeconds,nativeTick:sample.nativeTick,playTime:sample.playTime,wallMs:startedAt});
      return;
    }
    frames++;
    if(frames<=4||frames%100===0)clocks.push({frame:frames,wallMs:Date.now(),...sample});
  }
  return {applyIfReady,measure,finishFrame,measurementStarted:()=>enabled&&applied&&windowStarted&&frames>0,measurementComplete:()=>enabled&&applied&&frames>=limit,stopRequested:()=>enabled&&applied&&frames>=limit&&!fullBattleValidation,close,summary};
}

// Isolated native ABI component only. A source-bound host must configure sites.
// Does not install hooks or change any Unity clock itself.
function createNativeScopedDeltaFilter(configuration) {
  if(Process.arch!=='x64'||Process.pointerSize!==8)throw Error('Native clock filter requires Win64');
  const c=configuration,world=c.worldReturnAddresses,physical=c.physicalReturnAddresses;
  if(!Array.isArray(world)||!world.length||world.length>256||!Array.isArray(physical)||physical.length>512)throw Error('Source-bound world/physical callsites required');
  const keys=[...world,...physical].map(p=>p.toString());if(new Set(keys).size!==keys.length)throw Error('Clock caller classifications overlap');
  const w=Memory.alloc(world.length*8),p=Memory.alloc(Math.max(1,physical.length)*8);
  world.forEach((x,i)=>w.add(i*8).writePointer(x));if(!physical.length)p.writePointer(NULL);physical.forEach((x,i)=>p.add(i*8).writePointer(x));
  const active=Memory.alloc(4),afterFrame=Memory.alloc(4),step=Memory.alloc(4),counts=Memory.alloc(16),firstUnknown=Memory.alloc(8),frameInfo=Memory.alloc(8),lo=Memory.alloc(8),hi=Memory.alloc(8),wc=Memory.alloc(4),pc=Memory.alloc(4),overflow=Memory.alloc(4);
  overflow.writeU32(0);active.writeS32(0);afterFrame.writeS32(0);step.writeFloat(0);counts.writeByteArray(new Uint8Array(16));firstUnknown.writePointer(NULL);
  frameInfo.writePointer(c.frameMethodInfo);lo.writePointer(c.gameBegin);hi.writePointer(c.gameEnd);wc.writeU32(world.length);pc.writeU32(physical.length);
  const module=new CModule(`
#include <gum/guminterceptor.h>
extern float original_unscaled_icall(void);
extern gint original_frame_counter(gpointer method);
extern gpointer frame_method_info;
extern gpointer game_begin,game_end;
extern gpointer world_sites[],physical_sites[];
extern guint world_count,physical_count;
extern volatile gint active_flag,activation_frame;
extern float capture_step;
extern volatile guint counters[];
extern volatile guint counter_overflow;
extern gpointer volatile first_unknown;
static void increment(volatile guint *p){guint old=1;__asm__ volatile("lock xaddl %0, %1":"+r"(old),"+m"(*p)::"memory");if(old==0xffffffffU)counter_overflow=1;}
// An aligned Win64 pointer store is atomic. Simultaneous unknown callers may
// select either observed address; either one invalidates the source closure.
static void remember(gpointer caller){if(first_unknown==NULL)first_unknown=caller;}
float replacement(gpointer method_info){
  if(!active_flag||original_frame_counter(frame_method_info)<=activation_frame){increment(&counters[0]);return original_unscaled_icall();}
  GumInvocationContext *ic=gum_interceptor_get_current_invocation();
  gpointer caller=ic?gum_invocation_context_get_return_address(ic):NULL;
  for(guint i=0;i<world_count;i++)if(caller==world_sites[i]){increment(&counters[1]);return capture_step;}
  for(guint i=0;i<physical_count;i++)if(caller==physical_sites[i]){increment(&counters[2]);return original_unscaled_icall();}
  if(caller>=game_begin&&caller<game_end){increment(&counters[3]);remember(caller);}
  else increment(&counters[0]);
  return original_unscaled_icall();
}`,{original_unscaled_icall:c.originalUnscaledIcall,original_frame_counter:c.originalFrameCounter,frame_method_info:frameInfo,game_begin:lo,game_end:hi,
      world_sites:w,physical_sites:p,world_count:wc,physical_count:pc,active_flag:active,activation_frame:afterFrame,capture_step:step,counters:counts,first_unknown:firstUnknown,counter_overflow:overflow});
  return {replacement:module.replacement,arm(frame,value){
    if(!Number.isInteger(frame)||frame<0||value!==Math.fround(1/60))throw Error('Source clock activation frame/step differs');
    afterFrame.writeS32(frame);step.writeFloat(value);active.writeS32(1);
  },disarm(){active.writeS32(0);},summary:()=>({active:active.readS32()!==0,afterFrame:afterFrame.readS32(),captureStep:step.readFloat(),
    fallbackReads:counts.readU32(),worldReads:counts.add(4).readU32(),physicalReads:counts.add(8).readU32(),unsupportedGameReads:counts.add(12).readU32(),firstUnsupportedCaller:firstUnknown.readPointer().toString(),counterOverflow:overflow.readU32()!==0}),
    nativeRoots:[module,w,p,active,afterFrame,step,counts,firstUnknown,frameInfo,lo,hi,wc,pc,overflow]};
}

// Diagnostic only. Original capture clock plus source-bound world delta input.
// UI/audio/real-time clocks remain physical; unknown callers are reported.
function createNativeCoherentCaptureExperiment(pin,emit,input={}) {
  const enabled=input.enabled===undefined?false:input.enabled;
  if(typeof enabled!=='boolean')throw Error('Coherent capture enabled must be boolean');
  if(!enabled)return {applyIfReady(){},check(){},close(){},summary:()=>({enabled:false})};
  const game=Process.getModuleByName('GameAssembly.dll'),core=Il2Cpp.domain.assembly('UnityEngine.CoreModule').image,time=core.class('UnityEngine.Time'),app=core.class('UnityEngine.Application');
  const readHex=(address,n)=>Array.from(new Uint8Array(address.readByteArray(n)),x=>x.toString(16).padStart(2,'0')).join('');
  const unscaled=time.method('get_unscaledDeltaTime',0),frame=time.method('get_frameCount',0);
  if(!unscaled.isStatic||unscaled.parameters.length||unscaled.returnType.name!=='System.Single'||!unscaled.virtualAddress.equals(game.base.add(139652624))||readHex(unscaled.virtualAddress,24)!=='4883ec28488b052dac42034885c07513488d0d79676500e8')throw Error('Original coherent delta getter ABI/source differs');
  if(!frame.isStatic||frame.parameters.length||frame.returnType.name!=='System.Int32'||!frame.virtualAddress.equals(game.base.add(139652240))||readHex(frame.virtualAddress,24)!=='4883ec28488b05edad42034885c07513488d0d696a6500e8')throw Error('Original coherent frame getter ABI/source differs');
  const resolve=new NativeFunction(game.getExportByName('il2cpp_resolve_icall'),'pointer',['pointer']);
  const icall=name=>{const address=resolve(Memory.allocUtf8String('UnityEngine.Time::'+name)),module=address.isNull()?null:Process.findModuleByAddress(address);if(!module||module.name.toLowerCase()!=='unityplayer.dll')throw Error('Original coherent clock icall missing '+name);return address;};
  const getCapture=new NativeFunction(icall('get_captureDeltaTime'),'float',[]),setCapture=new NativeFunction(icall('set_captureDeltaTime'),'void',['float']);
  const sourceSites={world:[0x6486afa,0x717ac48],physical:[0x6f9303a,0x6f93066,0x84041c6,0x2b99000,0x2a78140]};
  for(const address of [...sourceSites.world,...sourceSites.physical]){
    const bytes=new Uint8Array(game.base.add(address-5).readByteArray(5));
    if(bytes[0]!==0xe8||game.base.add(address).add(game.base.add(address-4).readS32()).compare(unscaled.virtualAddress)!==0)throw Error('Original coherent clock source callsite differs '+address);
  }
  const filter=createNativeScopedDeltaFilter({worldReturnAddresses:sourceSites.world.map(x=>game.base.add(x)),physicalReturnAddresses:sourceSites.physical.map(x=>game.base.add(x)),
    originalUnscaledIcall:icall('get_unscaledDeltaTime'),originalFrameCounter:frame.virtualAddress,frameMethodInfo:frame.handle,gameBegin:game.base,gameEnd:game.base.add(game.size)});
  const getRate=app.method('get_targetFrameRate',0),setRate=app.method('set_targetFrameRate',1),getScale=time.method('get_timeScale',0);
  if(!getRate.virtualAddress.equals(game.base.add(0x84d4350))||!setRate.virtualAddress.equals(game.base.add(0x84d4990))||!getScale.virtualAddress.equals(game.base.add(0x852ed80)))throw Error('Original coherent capture settings ABI differs');
  const call=(m,args=[])=>invokeChecked(m,null,args),integer=m=>call(m).unbox().handle.readS32();
  const uni=Il2Cpp.domain.assembly('UniTask').image,post=uni.class('Cysharp.Threading.Tasks.UniTask').method('Post',2);
  if(!post.virtualAddress.equals(game.base.add(0x81cf660)))throw Error('Original coherent capture late scheduling differs');
  const phaseValue=uni.class('Cysharp.Threading.Tasks.PlayerLoopTiming').field('LastPostLateUpdate').value;
  const phase=typeof phaseValue==='number'?phaseValue:Number(phaseValue.field('value__').value);
  if(!Number.isSafeInteger(phase))throw Error('Original LastPostLateUpdate enum unavailable');
  let queued=false,applied=false,closed=false,installed=false,fault=null,closureFault=null,prior=null,appliedAt=null,closedAt=null;const step=Math.fround(1/60),errors=[];
  const summary=()=>({enabled,queued,applied,closed,installed,fault,closureFault,prior,appliedAt,closedAt,filter:filter.summary(),sourceSites,
    diagnosticOnly:true,universalClockClosureProved:false,manualDeltaInjected:false,animatorCodePatched:false,cinemachineClockWritten:false,timeScaleWritten:false});
  const checkClosure=()=>{const proof=filter.summary();if(proof.counterOverflow||proof.unsupportedGameReads!==0||proof.firstUnsupportedCaller!=='0x0'){
    closureFault=closureFault||('Accelerated execution is unsupported for this native clock caller; use Standard. Caller: '+proof.firstUnsupportedCaller);
    fault=fault||closureFault;return closureFault;
  }return null;};
  const close=()=>{
    if(closed)return summary();closed=true;filter.disarm();errors.length=0;let finalClosureError=null;
    if(installed)try{Interceptor.revert(unscaled.virtualAddress);Interceptor.flush();installed=false;
      if(readHex(unscaled.virtualAddress,24)!=='4883ec28488b052dac42034885c07513488d0d79676500e8')throw Error('Coherent clock getter original bytes not restored');
    }catch(e){errors.push(String(e));}
    try{if(applied)finalClosureError=checkClosure();}catch(error){fault=fault||String(error);finalClosureError=fault;}
    if(prior)try{setCapture(prior.capture);if(getCapture()!==prior.capture)throw Error('Original capture restoration differs');}catch(e){errors.push(String(e));}
    if(prior)try{call(setRate,[intArg(prior.rate)]);if(integer(getRate)!==prior.rate)throw Error('Original rate restoration differs');}catch(e){errors.push(String(e));}
    closedAt={wallMs:Date.now(),frameCount:integer(frame)};emit({status:'native_coherent_capture_closed',...summary(),restoreErrors:errors.slice(),restored:errors.length===0});
    if(errors.length)throw Error(errors.join('; '));if(finalClosureError)throw Error(finalClosureError);return summary();
  };
  const action=pin(Il2Cpp.delegate(Il2Cpp.corlib.class('System.Action'),()=>{
    if(closed)return;
    try{
      const scale=call(getScale).unbox().handle.readFloat();if(scale!==1||getCapture()!==0)throw Error('Coherent capture requires original scale1/capture0');
      prior={capture:getCapture(),rate:integer(getRate)};
      const activationFrame=integer(frame);
      Interceptor.replace(unscaled.virtualAddress,filter.replacement);Interceptor.flush();installed=true;
      setCapture(step);call(setRate,[intArg(-1)]);
      if(getCapture()!==step||integer(getRate)!==-1)throw Error('Coherent native capture readback differs');
      filter.arm(activationFrame,step);applied=true;appliedAt={wallMs:Date.now(),frameCount:activationFrame,worldDeltaAppliesAfterFrame:activationFrame};
      emit({status:'native_coherent_capture_applied',...summary()});
    }catch(error){fault=String(error&&error.stack||error);try{close();}catch(cleanup){fault+='; '+String(cleanup);}}
  }));
  return {applyIfReady(state){
    if(queued||closed)return;if(state?.playing!==true||state?.auto!==true||state?.rng!==true)return;
    queued=true;call(post,[action.handle,intArg(phase)]);emit({status:'native_coherent_capture_queued',phase:'LastPostLateUpdate',phaseValue:phase,wallMs:Date.now()});
  },check(){if(fault)throw Error(fault);if(applied&&!closed){const error=checkClosure();if(error)throw Error(error);}},close,summary,nativeRoots:filter.nativeRoots};
}

// Diagnostic render cadence only. Every original Unity/game update remains.
// Not evidence that rendering-dependent animation/collider callbacks are safe.
function createNativeRenderIntervalExperiment(emit,input={}) {
  const interval=input.interval===undefined?1:input.interval;
  if(!Number.isInteger(interval)||interval<1||interval>8)throw Error('Diagnostic render interval must be integer1..8');
  if(interval===1)return {applyIfReady(){},close(){},summary:()=>({enabled:false,interval:1})};
  const game=Process.getModuleByName('GameAssembly.dll');
  const cls=Il2Cpp.domain.assembly('UnityEngine.CoreModule').image.class('UnityEngine.Rendering.OnDemandRendering');
  const getter=cls.method('get_renderFrameInterval',0),field=cls.field('m_RenderFrameInterval');
  const hex=Array.from(new Uint8Array(getter.virtualAddress.readByteArray(24)),x=>x.toString(16).padStart(2,'0')).join('');
  if(!getter.isStatic||getter.parameters.length||getter.returnType.name!=='System.Int32'||
     !getter.virtualAddress.equals(game.base.add(0x8542a40))||hex!=='4883ec28803d05784103007513488d0dbc849c02e827e62f')throw Error('Original render interval getter source/ABI differs');
  if(!field.isStatic||field.offset!==0||field.type.name!=='System.Int32')throw Error('Original render interval field layout differs');
  const read=()=>invokeChecked(getter,null,[]).unbox().handle.readS32();
  let prior=null,applied=false,closed=false,fault=null;
  const summary=()=>({enabled:true,interval,prior,applied,closed,fault,diagnosticOnly:true,
    cameraChanged:false,viewportChanged:false,clockChanged:false,originalUpdateSchedulingUnchanged:true,renderDependencyAccuracyVerified:false});
  const close=()=>{
    if(closed)return summary();closed=true;
    let error=null;
    if(prior!==null)try{field.value=prior;if(read()!==prior||field.value!==prior)throw Error('Original render interval restoration differs');}catch(e){error=String(e);}
    emit({status:'native_render_interval_closed',...summary(),restored:error===null,restoreError:error});
    if(error)throw Error(error);return summary();
  };
  return {applyIfReady(state){
    if(applied||closed||state?.playing!==true||state?.auto!==true||state?.rng!==true)return;
    try{
      const original=read(); // Original getter initializes its class normally.
      if(!Number.isInteger(original)||original<1||original>8||field.value!==original)throw Error('Original render interval initial value unsupported');
      prior=original;field.value=interval;
      if(read()!==interval||field.value!==interval)throw Error('Diagnostic render interval readback differs');
      applied=true;emit({status:'native_render_interval_applied',...summary()});
    }catch(e){fault=String(e);try{close();}catch(cleanup){fault+='; '+String(cleanup);}throw Error(fault);}
  },close,summary};
}

// Isolated opt-in candidate. Original event input only; no pause/timeline field writes.
// Construct before any hooks patch guarded entries. Caller observes original Play return.
function createNativeStartupMonsterCutsceneSkip(runtime,management,pin,emit,options={}) {
 const summary={enabled:options.enabled===true,observed:0,dispatched:0,refused:0,closed:false,fault:null};
 if(!summary.enabled)return {observeOriginalPlay(){},step(){},close(){summary.closed=true;},summary(){return {...summary};}};
 const game=Process.getModuleByName('GameAssembly.dll'),type='NK.Spot.Presentation.Monster.MonsterTimeLineControl',monsterType='NK.Spot.Model.Monster.SpotMonster',dataType='NK.Spot.Monster.Timeline.MonsterTimeLineData';
 const controllerClass=runtime.class(type),eventClass=runtime.class('NK.Spot.Event.Monster.MonsterCutSceneSkipEvent'),spotEvent=runtime.class('NK.Spot.Common.SpotEvent');
 function exact(klass,name,rva,parameters,returns,prefix){const m=klass.method(name,parameters.length);
  if(m.isStatic||m.returnType.name!==returns||m.parameters.some((p,i)=>p.type.name!==parameters[i])||!m.virtualAddress.equals(game.base.add(rva)))throw Error('Original startup skip method ABI changed: '+name);
  const bytes=Array.from(new Uint8Array(m.virtualAddress.readByteArray(prefix.length/2)),b=>b.toString(16).padStart(2,'0')).join('');if(bytes!==prefix)throw Error('Original startup skip entry changed: '+name);return m;}
 const ctor=exact(eventClass,'.ctor',0x6d21540,[monsterType],'System.Void','48895c2408574883ec20488bfa488bd933d2e829de4500c7');
 const send=exact(spotEvent,'Send',0x717ef10,[],'System.Void','40534883ec20803d35b87c0400488bd97513488d0dc79fe8');
 function fieldAt(klass,offset,expectedType){const fs=klass.fields.filter(f=>!f.isStatic&&f.offset===offset&&f.type.name===expectedType);if(fs.length!==1)throw Error('Original startup skip field ABI changed at '+offset);return fs[0];}
 const monsterField=fieldAt(controllerClass,48,monsterType),dataField=fieldAt(controllerClass,80,dataType),dataClass=runtime.class(dataType);
 const typeFields=dataClass.fields.filter(f=>!f.isStatic&&f.offset===24&&f.type.class.isEnum);if(typeFields.length!==1)throw Error('Original timeline enum ABI changed');const typeField=typeFields[0];
 fieldAt(eventClass,64,'NK.Spot.Logic.Character.SpotEntityInfo');
 pin(management);let pending=null,used=false,busy=false;
 const same=(a,b)=>a&&b&&!a.isNull()&&!b.isNull()&&a.handle.equals(b.handle);
 function refusal(reason){summary.refused++;emit({status:'original_startup_monster_skip_refused',reason});}
 function numeric(v){return typeof v==='number'?v:Number(v.field('value__').value);}
 return {observeOriginalPlay(controller,frame){
  if(summary.closed||used||pending||busy)return;
  if(!Number.isSafeInteger(frame)||frame<0||!controller||controller.isNull()||controller.class.type.name!==type)throw Error('Original startup timeline observation invalid');
  const monster=controller.field(monsterField.name).value,data=controller.field(dataField.name).value;
  if(!monster||monster.isNull()||!data||data.isNull())return refusal('native_owner_or_data_missing');
  pending={controller:pin(controller),monster:pin(monster),data:pin(data),frame};summary.observed++;
 },step(state){
  if(summary.closed||used||!pending||busy)return;
  if(!state||!same(state.management,management))return refusal('management_identity');
  // Required caller proof: exclusively initial paused startup, before original combat resumes.
  if(state.startupWindow!==true){pending=null;used=true;return refusal('startup_window_closed');}
  if(state.paused!==true||(state.playing!==true&&state.startupLoadingComplete!==true)||!Number.isSafeInteger(state.frame)||state.frame<=pending.frame)return;
  const p=pending,current=p.controller.field(dataField.name).value,monster=p.controller.field(monsterField.name).value;
  if(!same(current,p.data)||!same(monster,p.monster)){pending=null;used=true;return refusal('native_session_replaced');}
  const kind=numeric(current.field(typeField.name).value);
  if(!Number.isInteger(kind)||kind===4){pending=null;used=true;return refusal(kind===4?'original_type4_skip_forbidden':'native_type_unavailable');}
  // Mark consumed BEFORE native dispatch: original synchronous End may reenter callbacks.
  used=true;pending=null;busy=true;
  try {const event=pin(eventClass.alloc());invokeChecked(ctor,event,[p.monster.handle]);invokeChecked(send,event,[]);summary.dispatched++;emit({status:'original_startup_monster_skip_dispatched',timelineType:kind,originalEventType:eventClass.type.name,observedFrame:p.frame,dispatchFrame:state.frame,originalHandlerRetainsType4Refusal:true});}
  catch(error){summary.fault=String(error);throw error;}finally{busy=false;}
 },close(){if(summary.closed)return;summary.closed=true;pending=null;},summary(){return {...summary};}};
}

function installNativeStartupMonsterSkip(runtime,manager,pin,emit) {
 const input=createNativeStartupMonsterCutsceneSkip(runtime,manager,pin,emit,{enabled:true});
 const game=Process.getModuleByName('GameAssembly.dll'),klass=runtime.class('NK.Spot.Presentation.Monster.MonsterTimeLineControl');
 const play=klass.method('Play',2),frame=Il2Cpp.domain.assembly('UnityEngine.CoreModule').image.class('UnityEngine.Time').method('get_frameCount',0);
 const hex=p=>Array.from(new Uint8Array(p.readByteArray(24)),b=>b.toString(16).padStart(2,'0')).join('');
 if(play.isStatic||play.returnType.name!=='System.Void'||play.parameters.some(p=>p.type.name!=='System.Boolean')||!play.virtualAddress.equals(game.base.add(0x5fea700))||hex(play.virtualAddress)!=='4053415641574883ec20803dc767950500450fb6f0440fb6')throw Error('Original startup Play source differs');
 if(!frame.isStatic||frame.parameters.length||frame.returnType.name!=='System.Int32'||!frame.virtualAddress.equals(game.base.add(139652240)))throw Error('Original startup frame binding differs');
 for(const [name,offset,type]of [['_isPause',193,'System.Boolean'],['_playtime',108,'System.Single']]){const f=manager.class.field(name);if(f.isStatic||f.offset!==offset||f.type.name!==type)throw Error('Original startup skip manager field differs');}
 const readFrame=()=>invokeChecked(frame,null,[]).unbox().handle.readS32();let windowOpen=true,closed=false,fault=null,firstPlayTime=null,detached=false;
 const listener=Interceptor.attach(play.virtualAddress,{onEnter(args){this.owner=windowOpen&&!closed?new Il2Cpp.Object(args[0]):null;},onLeave(){if(!this.owner)return;try{input.observeOriginalPlay(this.owner,readFrame());}catch(error){fault=String(error);}}});
 const detach=()=>{if(!detached){detached=true;listener.detach();}};
 return {step(phase){if(fault)throw Error(fault);if(closed||!windowOpen)return;const playing=phase.lifecycle.state===6,paused=manager.handle.add(193).readU8()!==0;
   if(playing&&firstPlayTime===null)firstPlayTime=phase.playTime;
   if(playing&&(!paused||phase.playTime>firstPlayTime)){windowOpen=false;input.close();detach();emit({status:'original_startup_monster_skip_window_closed',nativeTick:phase.tick,playTime:phase.playTime,summary:input.summary()});return;}
   input.step({management:manager,startupWindow:windowOpen,startupLoadingComplete:phase.lifecycle.state===3,playing,paused,frame:readFrame()});
 },close(){if(closed)return;closed=true;windowOpen=false;input.close();detach();emit({status:'original_startup_monster_skip_closed',summary:input.summary()});},summary:()=>input.summary()};
}

// Diagnostic native inclusive wall timings only. No game methods/arguments/returns changed.
function createNativeUnityScopeTiming(emit) {
 const specs=[
  {
    "className": "Cinemachine.CinemachineBrain",
    "assembly": "Cinemachine",
    "method": {
      "name": "LateUpdate",
      "returns": "System.Void",
      "parameters": [],
      "isStatic": false,
      "rva": "0x97fb80",
      "prefix24": "83792803740733d2e9e3010000c3cccc48895c240848896c"
    }
  },
  {
    "className": "Cinemachine.CinemachineBrain",
    "assembly": "Cinemachine",
    "method": {
      "name": "ManualUpdate",
      "returns": "System.Void",
      "parameters": [],
      "isStatic": false,
      "rva": "0x97fd70",
      "prefix24": "40534883ec50803d0452f80a00488bd90f29742440752b48"
    }
  },
  {
    "className": "Spine.Unity.SkeletonAnimation",
    "assembly": "spine-unity",
    "method": {
      "name": "Update",
      "returns": "System.Void",
      "parameters": [],
      "isStatic": false,
      "rva": "0x7ab1940",
      "prefix24": "40534883ec2083b91801000001488bd9752c80b91c010000"
    }
  },
  {
    "className": "Spine.Unity.SkeletonAnimation",
    "assembly": "spine-unity",
    "method": {
      "name": "Update",
      "returns": "System.Void",
      "parameters": [
        "System.Single"
      ],
      "isStatic": false,
      "rva": "0x7ab1990",
      "prefix24": "40534883ec2080b9b800000000488bd90f84330100004883"
    }
  },
  {
    "className": "Spine.Unity.SkeletonAnimation",
    "assembly": "spine-unity",
    "method": {
      "name": "LateUpdate",
      "returns": "System.Void",
      "parameters": [],
      "isStatic": false,
      "rva": "0x7ab1820",
      "prefix24": "40534883ec2080b9e800000000488bd9750b4533c00f57c9"
    }
  },
  {
    "className": "Spine.Unity.SkeletonRenderer",
    "assembly": "spine-unity",
    "method": {
      "name": "LateUpdate",
      "returns": "System.Void",
      "parameters": [],
      "isStatic": false,
      "rva": "0x7ad4750",
      "prefix24": "80b9b800000000741a83792c037514488b11488b82d80100"
    }
  },
  {
    "className": "Spine.Unity.SkeletonRenderer",
    "assembly": "spine-unity",
    "method": {
      "name": "LateUpdateMesh",
      "returns": "System.Void",
      "parameters": [],
      "isStatic": false,
      "rva": "0x7ad3d80",
      "prefix24": "4055535657488d6c24c14881ecc8000000803dfbbee70300"
    }
  }
],game=Process.getModuleByName('GameAssembly.dll');
 const methods=specs.map(s=>{const klass=Il2Cpp.domain.assembly(s.assembly).image.class(s.className),m=klass.method(s.method.name,s.method.parameters.length);
   const hex=Array.from(new Uint8Array(m.virtualAddress.readByteArray(24)),x=>x.toString(16).padStart(2,'0')).join('');
   if(klass.type.name!==s.className||m.isStatic!==s.method.isStatic||m.returnType.name!==s.method.returns||JSON.stringify(m.parameters.map(p=>p.type.name))!==JSON.stringify(s.method.parameters)||!m.virtualAddress.equals(game.base.add(Number(s.method.rva)))||hex!==s.method.prefix24)throw Error('Original Unity timing scope source differs '+s.className+'.'+s.method.name);
   return m;
 });
 const kernel=Process.getModuleByName('kernel32.dll'),qpc=kernel.getExportByName('QueryPerformanceCounter'),frequency=kernel.getExportByName('QueryPerformanceFrequency'),thread=kernel.getExportByName('GetCurrentThreadId');
 for(const address of [qpc,frequency,thread]){const owner=Process.findModuleByAddress(address);if(!owner||!['kernel32.dll','kernelbase.dll'].includes(owner.name.toLowerCase()))throw Error('Original OS timing export owner differs');}
 const alloc=n=>{const p=Memory.alloc(n);p.writeByteArray(new Uint8Array(n));return p;};
 const active=alloc(4),inflight=alloc(4),ownerThread=alloc(4),insideAction=alloc(4),counts=alloc(56),totals=alloc(112),maxima=alloc(112),failures=alloc(4),ignored=alloc(4),overflow=alloc(4),freq=alloc(8);
 if(new NativeFunction(frequency,'int',['pointer'])(freq)!==1||Number(freq.readS64().toString())<=0)throw Error('Original OS QPC frequency unavailable');
 const native=new CModule(`
#include <gum/guminterceptor.h>
extern int original_qpc(gint64 *value);
extern guint original_thread(void);
extern volatile gint active_flag,inflight_count,inside_action;
extern guint owner_thread,counts[],failure_count,ignored_count,overflow_count;
extern gint64 totals[],maxima[];
typedef struct {gint64 begin;guint index;guint armed;} TimingInvocation;
static void atomic_increment(guint *p){guint old=1;__asm__ volatile("lock xaddl %0, %1":"+r"(old),"+m"(*p)::"memory");}
static void enter(GumInvocationContext *ic,guint index){
 TimingInvocation *data=GUM_IC_GET_INVOCATION_DATA(ic,TimingInvocation);data->armed=0;
 if(!active_flag)return;
 if(original_thread()!=owner_thread){atomic_increment(&ignored_count);return;}
 if(!original_qpc(&data->begin)){failure_count++;return;}
 data->index=index*2+(inside_action?1:0);data->armed=1;inflight_count++;
}
void leave(GumInvocationContext *ic){
 TimingInvocation *data=GUM_IC_GET_INVOCATION_DATA(ic,TimingInvocation);if(!data->armed)return;data->armed=0;
 gint64 end=0;if(!original_qpc(&end)||end<data->begin){failure_count++;inflight_count--;return;}
 guint i=data->index;gint64 elapsed=end-data->begin;
 if(counts[i]==0xffffffffU||elapsed>0x7fffffffffffffffLL-totals[i])overflow_count++;
 else {counts[i]++;totals[i]+=elapsed;if(elapsed>maxima[i])maxima[i]=elapsed;}
 inflight_count--;
}
${specs.map((s,i)=>`void enter_${i}(GumInvocationContext *ic){enter(ic,${i});}`).join('\n')}
`,{original_qpc:qpc,original_thread:thread,active_flag:active,inflight_count:inflight,inside_action:insideAction,owner_thread:ownerThread,counts,totals,maxima,failure_count:failures,ignored_count:ignored,overflow_count:overflow});
 let started=false,closed=false,startedAt=null,closedAt=null;const listeners=[],frequencyValue=Number(freq.readS64().toString());
 const summary=()=>({started,closed,startedAt,closedAt,mainThreadOnly:true,ownerThread:ownerThread.readU32(),active:active.readS32()!==0,inflight:inflight.readS32(),failures:failures.readU32(),ignoredOtherThreadEntries:ignored.readU32(),overflow:overflow.readU32(),
   complete:started&&closed&&active.readS32()===0&&inflight.readS32()===0&&failures.readU32()===0&&ignored.readU32()===0&&overflow.readU32()===0,
   partitionAtNativeEntry:true,frequency:freq.readS64().toString(),scopes:specs.map((s,i)=>({className:s.className,method:s.method.name,parameters:s.method.parameters,rva:s.method.rva,partitions:[0,1].map(partition=>{const at=i*2+partition;return {insideSchedulerAction:partition===1,count:counts.add(at*4).readU32(),inclusiveQpcTicks:totals.add(at*8).readS64().toString(),inclusiveWallMs:Number(totals.add(at*8).readS64().toString())/frequencyValue*1000,maxWallMs:Number(maxima.add(at*8).readS64().toString())/frequencyValue*1000};})})),
   timingsInclusiveAndNestedNotAdditive:true,originalArgumentsAndReturnsUntouched:true,noJsPerNativeCall:true,gameClockWritten:false});
 try{methods.forEach((m,i)=>listeners.push(Interceptor.attach(m.virtualAddress,{onEnter:native['enter_'+i],onLeave:native.leave})));}catch(error){for(const listener of listeners)try{listener.detach();}catch(_){}throw error;}
 return {setInsideAction(value){if(typeof value!=='boolean')throw Error('Diagnostic action partition must be boolean');insideAction.writeS32(value?1:0);},start(sample){if(started||closed)return;ownerThread.writeU32(Process.getCurrentThreadId());startedAt={wallMs:Date.now(),nativeTick:sample.tick,playTime:sample.playTime,phase:'after_original_manager_tick'};started=true;active.writeS32(1);emit({status:'native_unity_scope_timing_started',...summary()});},
   close(){if(closed)return;active.writeS32(0);closed=true;closedAt={wallMs:Date.now()};let firstError=null;for(const listener of listeners)try{listener.detach();}catch(error){if(!firstError)firstError=error;}emit({status:'native_unity_scope_timing_closed',...summary()});if(firstError)throw firstError;},summary,
   nativeRoots:[native,active,inflight,insideAction,ownerThread,counts,totals,maxima,failures,ignored,overflow,freq]};
}

// Current153 metadata and original PE guarded; diagnostic handles/private buffers only.
function createNativeProfilerRecorderBinding() {
 const spec={"classes":[{"class":"Unity.Profiling.ProfilerCategory","valueSize":2,"valueAlignment":1,"fields":[{"name":"m_CategoryId","type":"System.UInt16","offset":16,"flags":33}]},{"class":"Unity.Profiling.ProfilerRecorderOptions","valueSize":4,"valueAlignment":4,"fields":[{"name":"value__","type":"System.Int32","offset":16,"flags":1542},{"name":"None","type":"Unity.Profiling.ProfilerRecorderOptions","offset":0,"flags":32854,"literalValue":0},{"name":"StartImmediately","type":"Unity.Profiling.ProfilerRecorderOptions","offset":0,"flags":32854,"literalValue":1},{"name":"KeepAliveDuringDomainReload","type":"Unity.Profiling.ProfilerRecorderOptions","offset":0,"flags":32854,"literalValue":2},{"name":"CollectOnlyOnCurrentThread","type":"Unity.Profiling.ProfilerRecorderOptions","offset":0,"flags":32854,"literalValue":4},{"name":"WrapAroundWhenCapacityReached","type":"Unity.Profiling.ProfilerRecorderOptions","offset":0,"flags":32854,"literalValue":8},{"name":"SumAllSamplesInFrame","type":"Unity.Profiling.ProfilerRecorderOptions","offset":0,"flags":32854,"literalValue":16},{"name":"GpuRecorder","type":"Unity.Profiling.ProfilerRecorderOptions","offset":0,"flags":32854,"literalValue":64},{"name":"Default","type":"Unity.Profiling.ProfilerRecorderOptions","offset":0,"flags":32854,"literalValue":24}]},{"class":"Unity.Profiling.ProfilerRecorder.ControlOptions","valueSize":4,"valueAlignment":4,"fields":[{"name":"value__","type":"System.Int32","offset":16,"flags":1542},{"name":"Start","type":"Unity.Profiling.ProfilerRecorder.ControlOptions","offset":0,"flags":32854,"literalValue":0},{"name":"Stop","type":"Unity.Profiling.ProfilerRecorder.ControlOptions","offset":0,"flags":32854,"literalValue":1},{"name":"Reset","type":"Unity.Profiling.ProfilerRecorder.ControlOptions","offset":0,"flags":32854,"literalValue":2},{"name":"Release","type":"Unity.Profiling.ProfilerRecorder.ControlOptions","offset":0,"flags":32854,"literalValue":4},{"name":"SetFilterToCurrentThread","type":"Unity.Profiling.ProfilerRecorder.ControlOptions","offset":0,"flags":32854,"literalValue":5},{"name":"SetToCollectFromAllThreads","type":"Unity.Profiling.ProfilerRecorder.ControlOptions","offset":0,"flags":32854,"literalValue":6}]},{"class":"Unity.Profiling.ProfilerRecorder","valueSize":8,"valueAlignment":8,"fields":[{"name":"handle","type":"System.UInt64","offset":16,"flags":3},{"name":"SharedRecorder","type":"Unity.Profiling.ProfilerRecorderOptions","offset":0,"flags":32851}]},{"class":"Unity.Profiling.LowLevel.ProfilerMarkerDataType","valueSize":1,"valueAlignment":1,"fields":[{"name":"value__","type":"System.Byte","offset":16,"flags":1542},{"name":"Int32","type":"Unity.Profiling.LowLevel.ProfilerMarkerDataType","offset":0,"flags":32854,"literalValue":2},{"name":"UInt32","type":"Unity.Profiling.LowLevel.ProfilerMarkerDataType","offset":0,"flags":32854,"literalValue":3},{"name":"Int64","type":"Unity.Profiling.LowLevel.ProfilerMarkerDataType","offset":0,"flags":32854,"literalValue":4},{"name":"UInt64","type":"Unity.Profiling.LowLevel.ProfilerMarkerDataType","offset":0,"flags":32854,"literalValue":5},{"name":"Float","type":"Unity.Profiling.LowLevel.ProfilerMarkerDataType","offset":0,"flags":32854,"literalValue":6},{"name":"Double","type":"Unity.Profiling.LowLevel.ProfilerMarkerDataType","offset":0,"flags":32854,"literalValue":7},{"name":"String16","type":"Unity.Profiling.LowLevel.ProfilerMarkerDataType","offset":0,"flags":32854,"literalValue":9},{"name":"Blob8","type":"Unity.Profiling.LowLevel.ProfilerMarkerDataType","offset":0,"flags":32854,"literalValue":11}]},{"class":"Unity.Profiling.LowLevel.Unsafe.ProfilerRecorderDescription","valueSize":24,"valueAlignment":1,"fields":[{"name":"category","type":"Unity.Profiling.ProfilerCategory","offset":16,"flags":33},{"name":"flags","type":"Unity.Profiling.LowLevel.MarkerFlags","offset":18,"flags":33},{"name":"dataType","type":"Unity.Profiling.LowLevel.ProfilerMarkerDataType","offset":20,"flags":33},{"name":"unitType","type":"Unity.Profiling.ProfilerMarkerDataUnit","offset":21,"flags":33},{"name":"reserved0","type":"System.Int32","offset":24,"flags":33},{"name":"nameUtf8Len","type":"System.Int32","offset":28,"flags":33},{"name":"nameUtf8","type":"System.Byte*","offset":32,"flags":33}]},{"class":"Unity.Profiling.LowLevel.Unsafe.ProfilerRecorderHandle","valueSize":8,"valueAlignment":1,"fields":[{"name":"handle","type":"System.UInt64","offset":16,"flags":35}]},{"class":"Unity.Profiling.ProfilerMarkerDataUnit","valueSize":1,"valueAlignment":1,"fields":[{"name":"value__","type":"System.Byte","offset":16,"flags":1542},{"name":"Undefined","type":"Unity.Profiling.ProfilerMarkerDataUnit","offset":0,"flags":32854,"literalValue":0},{"name":"TimeNanoseconds","type":"Unity.Profiling.ProfilerMarkerDataUnit","offset":0,"flags":32854,"literalValue":1},{"name":"Bytes","type":"Unity.Profiling.ProfilerMarkerDataUnit","offset":0,"flags":32854,"literalValue":2},{"name":"Count","type":"Unity.Profiling.ProfilerMarkerDataUnit","offset":0,"flags":32854,"literalValue":3},{"name":"Percent","type":"Unity.Profiling.ProfilerMarkerDataUnit","offset":0,"flags":32854,"literalValue":4},{"name":"FrequencyHz","type":"Unity.Profiling.ProfilerMarkerDataUnit","offset":0,"flags":32854,"literalValue":5}]}],"methods":{"categoryCtor":{"class":"Unity.Profiling.ProfilerCategory","name":".ctor","returns":"System.Void","parameters":["System.UInt16"],"static":false,"rva":11543696,"prefix":"668911c3cccccccccccccccccccccccc0f100233d20f1101"},"lookup":{"class":"Unity.Profiling.LowLevel.Unsafe.ProfilerRecorderHandle","name":"GetByName_Unsafe_Injected","returns":"System.Void","parameters":["Unity.Profiling.ProfilerCategory&","System.Char*","System.Int32","Unity.Profiling.LowLevel.Unsafe.ProfilerRecorderHandle&"],"static":true,"rva":139413248,"prefix":"48895c240848896c24104889742418574883ec20488b0525"},"description":{"class":"Unity.Profiling.LowLevel.Unsafe.ProfilerRecorderHandle","name":"GetDescriptionInternal_Injected","returns":"System.Void","parameters":["Unity.Profiling.LowLevel.Unsafe.ProfilerRecorderHandle&","Unity.Profiling.LowLevel.Unsafe.ProfilerRecorderDescription&"],"static":true,"rva":139413552,"prefix":"48895c2408574883ec20488b0507204603488bda488bf948"},"handleValid":{"class":"Unity.Profiling.LowLevel.Unsafe.ProfilerRecorderHandle","name":"get_Valid","returns":"System.Boolean","parameters":[],"static":false,"rva":139413952,"prefix":"48833900750333c0c3488339ff0f95c0c3cccccccccccccc"},"recorderCtor":{"class":"Unity.Profiling.ProfilerRecorder","name":".ctor","returns":"System.Void","parameters":["Unity.Profiling.LowLevel.Unsafe.ProfilerRecorderHandle","System.Int32","Unity.Profiling.ProfilerRecorderOptions"],"static":false,"rva":139415600,"prefix":"48895c24184889742420574883ec20488b05d2174603418b"},"start":{"class":"Unity.Profiling.ProfilerRecorder","name":"Start","returns":"System.Void","parameters":[],"static":false,"rva":139415104,"prefix":"4883ec28488339007435488b014889442430488b05c71946"},"stop":{"class":"Unity.Profiling.ProfilerRecorder","name":"Stop","returns":"System.Void","parameters":[],"static":false,"rva":139415264,"prefix":"4883ec28488339007438488b014889442430488b05271946"},"dispose":{"class":"Unity.Profiling.ProfilerRecorder","name":"Dispose","returns":"System.Void","parameters":[],"static":false,"rva":139414416,"prefix":"40534883ec2048833900488bd9743a488b01488944243048"},"last":{"class":"Unity.Profiling.ProfilerRecorder","name":"GetLastValue_Injected","returns":"System.Int64","parameters":["Unity.Profiling.ProfilerRecorder&"],"static":true,"rva":139414624,"prefix":"40534883ec20488b05c31b4603488bd94885c07513488d0d"},"valid":{"class":"Unity.Profiling.ProfilerRecorder","name":"get_Valid","returns":"System.Boolean","parameters":[],"static":false,"rva":139416032,"prefix":"4883ec2848833900750c33c085c00f95c04883c428c3488b"}}};

 if(Process.arch!=='x64'||Process.pointerSize!==8)throw Error('Profiler original x64 required');
 const game=Process.getModuleByName('GameAssembly.dll'),image=Il2Cpp.domain.assembly('UnityEngine.CoreModule').image,classes=new Map();
 const valueSize=new NativeFunction(game.getExportByName('il2cpp_class_value_size'),'int',['pointer','pointer']);
 for(const c of spec.classes){const k=c.class==='Unity.Profiling.ProfilerRecorder.ControlOptions'?image.class('Unity.Profiling.ProfilerRecorder').nested('ControlOptions'):image.class(c.class),a=Memory.alloc(4);if(!k.isValueType||valueSize(k.handle,a)!==c.valueSize||a.readU32()!==c.valueAlignment)throw Error('Profiler original value layout changed: '+c.class);
  for(const f of c.fields){const actual=k.field(f.name);if(actual.offset!==f.offset||actual.type.name!==f.type||actual.isStatic!==!!(f.flags&16))throw Error('Profiler original field changed: '+c.class+'.'+f.name);
   if(f.literalValue!==undefined&&(typeof actual.value==='number'?actual.value:Number(actual.value.field('value__').value))!==f.literalValue)throw Error('Profiler original enum changed: '+f.name);}
  classes.set(c.class,k);
 }
 const methods={};for(const [key,s]of Object.entries(spec.methods)){const ms=classes.get(s.class).methods.filter(m=>m.name===s.name&&m.returnType.name===s.returns&&m.isStatic===s.static&&m.parameters.length===s.parameters.length&&m.parameters.every((p,i)=>p.type.name===s.parameters[i]));if(ms.length!==1)throw Error('Profiler original method declaration changed: '+key);const m=ms[0];if(!m.virtualAddress.equals(game.base.add(s.rva)))throw Error('Profiler original method RVA changed: '+key);const bytes=Array.from(new Uint8Array(m.virtualAddress.readByteArray(24)),b=>b.toString(16).padStart(2,'0')).join('');if(bytes!==s.prefix)throw Error('Profiler original method prefix changed: '+key);methods[key]=m;}
 const bind=(key,ret,args)=>new NativeFunction(methods[key].virtualAddress,ret,args.concat('pointer'));
 const categoryCtor=bind('categoryCtor','void',['pointer','uint16']),find=bind('lookup','void',['pointer','pointer','int','pointer']),describe=bind('description','void',['pointer','pointer']),handleValid=bind('handleValid','bool',['pointer']),ctor=bind('recorderCtor','void',['pointer','uint64','int','int']),valid=bind('valid','bool',['pointer']);
 const starts=bind('start','void',['pointer']),stops=bind('stop','void',['pointer']),disposes=bind('dispose','void',['pointer']);
 const owned=new Map(),handles=new Map();let closed=false;
 const id=p=>p.toString(),requireOpen=()=>{if(closed)throw Error('Profiler binding closed');};
 const requireOwned=p=>{requireOpen();if(owned.get(id(p))!==p)throw Error('Profiler recorder buffer not owned');};
 function dispose(p){if(owned.get(id(p))!==p)return false;disposes(p,methods.dispose.handle);if(p.readU64().toString()!=='0')throw Error('Original profiler Dispose did not clear owned handle');owned.delete(id(p));return true;}
 return {lookup(name){requireOpen();if(typeof name!=='string'||!name.length||name.length>1024||name.includes('\0'))return {supported:false,reason:'invalid_name'};
   const category=Memory.alloc(2),handle=Memory.alloc(8);handle.writeU64(0);categoryCtor(category,65535,methods.categoryCtor.handle);if(category.readU16()!==65535)throw Error('Original profiler Any category differs');
   const text=Memory.allocUtf16String(name);find(category,text,name.length,handle,methods.lookup.handle);
   if(!handleValid(handle,methods.handleValid.handle))return {supported:false,reason:'original_marker_unavailable'};
   const d=Memory.alloc(24);describe(handle,d,methods.description.handle);const length=d.add(12).readS32(),textPointer=d.add(16).readPointer();if(length<1||length>4096||textPointer.isNull())return {supported:false,reason:'original_description_invalid'};
   const description={name:textPointer.readUtf8String(length),category:d.readU16(),flags:d.add(2).readU16(),dataType:d.add(4).readU8(),unitType:d.add(5).readU8()};
   if(description.name!==name)return {supported:false,reason:'original_marker_name_mismatch',description};
   if(![1,2,3].includes(description.unitType)||![4,5].includes(description.dataType))return {supported:false,reason:'original_marker_unit_or_type_unsupported',description};
   handles.set(id(handle),{buffer:handle,value:handle.readU64().toString()});return {supported:true,handleBuffer:handle,description};
 },create(handle,options=28){requireOpen();if(options!==28&&options!==25)throw Error('Profiler recorder options unsupported');const h=handles.get(id(handle));if(!h||h.buffer!==handle||h.value!==handle.readU64().toString()||!handleValid(handle,methods.handleValid.handle))throw Error('Profiler marker handle not owned or changed');const p=Memory.alloc(8);p.writeU64(0);owned.set(id(p),p);
   let normalCtorReturned=false,normalInvalid=false,outputHandle=null;
   try{ctor(p,handle.readU64(),1,options,methods.recorderCtor.handle);normalCtorReturned=true;if(!valid(p,methods.valid.handle)){normalInvalid=true;outputHandle=p.readU64().toString();throw Error('Original profiler recorder invalid after creation');}return p;}
   catch(error){let cleanupVerified=false;try{dispose(p);cleanupVerified=!owned.has(id(p))&&p.readU64().toString()==='0';}catch(cleanup){error.cleanupError=String(cleanup);}
    if(normalCtorReturned&&normalInvalid&&cleanupVerified){error.nativeRecorderUnavailable=true;error.details={inputHandle:h.value,outputHandle,options,normalCtorReturned:true,cleanupVerified:true};}throw error;}
 },start(p){requireOwned(p);starts(p,methods.start.handle);},stop(p){requireOwned(p);stops(p,methods.stop.handle);},dispose,
 close(){if(closed)return;const errors=[];for(const p of [...owned.values()])try{dispose(p);}catch(e){errors.push(String(e));}if(errors.length)throw Error('Original profiler cleanup failed: '+errors.join('; '));closed=true;handles.clear();},
 nativeLastGetter:{address:methods.last.virtualAddress,methodInfo:methods.last.handle,returnType:'int64',argumentTypes:['pointer','pointer']},
 summary(){return {closed,ownedRecorders:owned.size,lookedUpHandles:handles.size,defaultOptions:28,supportedOptions:[28,25],capacity:1};}
 };
}

// Bounded diagnostic. Original native recorder getter, one JS->C call/frame.
function createNativeProfilerRecorderExperiment(binding,emit) {
 const names=['PlayerLoop','Main Thread','GC.Collect','GarbageCollector','GC.IncrementalCollect','GC.Alloc','GC Allocated In Frame','GC Used Memory','GC Reserved Memory','Total Used Memory','Total Reserved Memory','System Used Memory','Gfx.WaitForPresentOnGfxThread','Gfx.PresentFrame','Gfx.WaitForGfxCommandsFromMainThread','Gfx.ProcessCommands','RenderLoop','Camera.Render','Physics.Simulate','Physics.Processing','Animation.Update','Animator.Update','Canvas.SendWillRenderCanvases','UI.Canvas.BuildBatch'];
 const alloc=n=>{const p=Memory.alloc(n);p.writeByteArray(new Uint8Array(n));return p;};
 const active=alloc(4),busy=alloc(4),rows=alloc(4),count=alloc(4),reentrant=alloc(4),pointers=alloc(24*8),values=alloc(24*600*8),method=alloc(8);
 const getter=binding.nativeLastGetter;if(!getter||getter.returnType!=='int64'||JSON.stringify(getter.argumentTypes)!=='["pointer","pointer"]')throw Error('Original profiler getter ABI unavailable');method.writePointer(getter.methodInfo);
 const native=new CModule(`
#include <glib.h>
extern gint64 original_last(gpointer recorder,gpointer method);
extern gpointer last_method,recorder_ptrs[];
extern volatile gint active_flag,busy_flag;
extern guint sample_count,marker_count,reentrant_count;
extern gint64 sample_values[];
int collect(void){
 if(!active_flag||sample_count>=600)return 0;
 if(busy_flag){reentrant_count++;return -1;}busy_flag=1;
 guint row=sample_count;
 for(guint i=0;i<marker_count;i++)sample_values[row*24+i]=original_last(recorder_ptrs[i],last_method);
 sample_count=row+1;busy_flag=0;return 1;
}
`,{original_last:getter.address,last_method:method,recorder_ptrs:pointers,active_flag:active,busy_flag:busy,sample_count:rows,marker_count:count,reentrant_count:reentrant,sample_values:values});
 const collect=new NativeFunction(native.collect,'int',[]);let started=false,closed=false,startAt=null,ownerThread=null,fault=null;
 const selected=[],availability=[],times=[],cleanupErrors=[];
 function close(){
  if(closed)return;active.writeS32(0);closed=true;
  for(const item of selected){try{binding.stop(item.recorder);}catch(error){cleanupErrors.push(String(error));}finally{try{binding.dispose(item.recorder);}catch(error){cleanupErrors.push(String(error));}}}
  try{binding.close();}catch(error){cleanupErrors.push(String(error));}
  emit({status:'native_profiler_recorders_closed',...summary()});
  if(cleanupErrors.length)throw Error(cleanupErrors.join('; '));
 }
 function summary(){const n=rows.readU32();return {started,closed,startAt,fault,ownerThread,frames:n,limit:600,markerLimit:24,availability,
  samples:times.slice(),markers:selected.map((item,i)=>({...item.description,requestedName:item.name,nativeOptions:item.options,collectOnlyOnCurrentThread:item.options===28,creationAttempts:item.attempts,values:Array.from({length:n},(_,row)=>values.add((row*24+i)*8).readS64().toString())})),
  discardInitialSamples:2,sampleMeaning:'original GetLastValue: most recently completed native profiler frame, observed before original manager tick',
  unitsAreNativeDescription:true,damageCalculated:false,gameClockWritten:false,gameInputsWritten:false,oneJsToCReadCallPerSample:true,
  supportedMarkerCount:selected.length,dataAvailable:selected.length>0&&n>2,complete:started&&closed&&selected.length>0&&n>2&&times.length===n&&!fault&&busy.readS32()===0&&reentrant.readU32()===0&&cleanupErrors.length===0,
  busy:busy.readS32(),reentrant:reentrant.readU32(),cleanupErrors:cleanupErrors.slice()};}
 return {start(sample){
   if(started||closed)return;started=true;ownerThread=Process.getCurrentThreadId();startAt={nativeTick:sample.tick,playTime:sample.playTime,wallMs:Date.now()};
   try{for(const name of names){const lookup=binding.lookup(name);if(!lookup.supported){availability.push({name,supported:false,reason:lookup.reason});continue;}
     if(![1,2,3,4,5].includes(lookup.description.unitType)||![4,5].includes(lookup.description.dataType)){availability.push({name,supported:false,reason:'native_unit_or_integer_data_type_unsupported',description:lookup.description});continue;}
     let recorder=null,options=null;const attempts=[];
     for(const candidate of [28,25])try{recorder=binding.create(lookup.handleBuffer,candidate);options=candidate;break;}
     catch(error){if(error.nativeRecorderUnavailable===true&&error.details?.normalCtorReturned===true&&error.details?.cleanupVerified===true){attempts.push({...error.details,options:candidate});continue;}throw error;}
     if(!recorder){availability.push({name,supported:false,reason:'original_recorder_unavailable_after_normal_creation',description:lookup.description,attempts});continue;}
     const item={name,description:lookup.description,recorder,options,attempts};selected.push(item);if(options===28)binding.start(recorder);pointers.add((selected.length-1)*8).writePointer(recorder);
     availability.push({name,supported:true,description:lookup.description,nativeOptions:options,attempts});
   }count.writeU32(selected.length);if(selected.length)active.writeS32(1);emit({status:'native_profiler_recorders_started',startAt,ownerThread,selected:selected.length,availability});
   }catch(error){fault=String(error);try{close();}catch(cleanup){fault+='; '+String(cleanup);}throw error;}
  },sample(sample){try{if(!started||closed||!selected.length||rows.readU32()>=600)return;if(Process.getCurrentThreadId()!==ownerThread)throw Error('Original profiler sampling thread changed');
    const result=collect();if(result===1)times.push({nativeTick:sample.tick,playTime:sample.playTime});else if(result<0)throw Error('Original profiler batch unexpectedly reentered');
  }catch(error){fault=String(error);throw error;}},close,summary,nativeRoots:[native,collect,active,busy,rows,count,reentrant,pointers,values,method,binding]};
}

// Original153 metadata discovery ONLY; does not call/replace any native loop callback.
function createNativePlayerLoopDiscovery(pin) {
 const fieldSpec=[{"name":"type","type":"System.Type","offset":16,"flags":6},{"name":"subSystemList","type":"UnityEngine.LowLevel.PlayerLoopSystem[]","offset":24,"flags":6},{"name":"updateDelegate","type":"UnityEngine.LowLevel.PlayerLoopSystem.UpdateFunction","offset":32,"flags":6},{"name":"updateFunction","type":"System.IntPtr","offset":40,"flags":6},{"name":"loopConditionFunction","type":"System.IntPtr","offset":48,"flags":6}];

 if(Process.arch!=='x64'||Process.pointerSize!==8||typeof pin!=='function')throw Error('PlayerLoop discovery requires original x64 and pin');
 const game=Process.getModuleByName('GameAssembly.dll'),unity=Process.getModuleByName('UnityPlayer.dll'),image=Il2Cpp.domain.assembly('UnityEngine.CoreModule').image;
 const klass=image.class('UnityEngine.LowLevel.PlayerLoopSystem'),loop=image.class('UnityEngine.LowLevel.PlayerLoop');
 const getSize=new NativeFunction(game.getExportByName('il2cpp_class_value_size'),'int',['pointer','pointer']),fromType=new NativeFunction(game.getExportByName('il2cpp_class_from_system_type'),'pointer',['pointer']);
 const alignment=Memory.alloc(4);if(!klass.isValueType||getSize(klass.handle,alignment)!==40||alignment.readU32()!==8)throw Error('Original PlayerLoopSystem size/alignment changed');
 for(const s of fieldSpec){const f=klass.field(s.name);if(f.isStatic||f.offset!==s.offset||f.type.name!==s.type)throw Error('Original PlayerLoopSystem field changed: '+s.name);}
 const intPtrClass=klass.field('updateFunction').type.class,a=Memory.alloc(4);if(!intPtrClass.isValueType||getSize(intPtrClass.handle,a)!==8||a.readU32()!==8)throw Error('Original IntPtr layout changed');
 const m=loop.methods.find(m=>m.name==='GetCurrentPlayerLoop'&&m.isStatic&&m.returnType.name==='UnityEngine.LowLevel.PlayerLoopSystem'&&m.parameters.length===0);
 if(!m||!m.virtualAddress.equals(game.base.add(139746416)))throw Error('Original GetCurrentPlayerLoop declaration/RVA changed');
 const hex=(p,n)=>Array.from(new Uint8Array(p.readByteArray(n)),b=>b.toString(16).padStart(2,'0')).join('');
 if(hex(m.virtualAddress,24)!=='40534883ec5033c0c7442460000000000f57c0488bd90f11')throw Error('Original GetCurrentPlayerLoop prefix changed');
 const pointer=v=>v&&typeof v.add==='function'&&typeof v.readPointer==='function'&&typeof v.isNull==='function';
 function asPointer(value){if(pointer(value))return value;
  if(value&&value.type&&value.type.name==='System.IntPtr'&&value.handle){const fs=intPtrClass.fields.filter(f=>!f.isStatic&&f.name==='m_value'&&f.offset===16&&f.type.name==='System.Void*');if(fs.length!==1)throw Error('Original IntPtr boxed-field representation unsupported');const p=value.field('m_value').value;if(pointer(p))return p;if(typeof Il2Cpp.Pointer==='function'&&Object.getPrototypeOf(p)===Il2Cpp.Pointer.prototype&&p.type&&p.type.name==='System.Void'&&pointer(p.handle))return p.handle;}
  throw Error('Original IntPtr runtime representation unsupported');}
 const live=v=>v!=null&&(typeof v.isNull!=='function'||!v.isNull());
 const inUnity=p=>p.compare(unity.base)>=0&&p.compare(unity.base.add(unity.size))<0;
 return {discover(){const nodes=[],groups=[],byTarget=new Map(),counts={containers:0,managedDelegates:0,nativeSlots:0,nullSlots:0,unsupported:0};let complete=true,error=null;
  const root=pin(invokeChecked(m,null,[]));if(!root||root.isNull())throw Error('Original PlayerLoop root missing');const unboxed=root.unbox();
  function walk(system,path,depth){if(depth>32||nodes.length>=256){complete=false;error='Original PlayerLoop discovery bound exceeded';return;}
   const row={path,typeName:null,classification:null};nodes.push(row);
   try{const type=system.field('type').value;if(live(type)){const c=fromType(type.handle);if(c.isNull())throw Error('Original loop System.Type did not resolve class');row.typeName=new Il2Cpp.Class(c).type.name;}else row.typeName='<root>';
    const children=system.field('subSystemList').value,delegate=system.field('updateDelegate').value,slotValue=system.field('updateFunction').value;try{row.hasManagedDelegate=live(delegate);const slot=row.hasManagedDelegate?null:asPointer(slotValue);row.slot=slot?slot.toString():null;
    if(row.hasManagedDelegate){row.classification='managed_delegate';counts.managedDelegates++;}
    else if(slot.isNull()){row.classification=live(children)&&children.length>0?'container':'null_slot';counts[row.classification==='container'?'containers':'nullSlots']++;}
    else{const range=Process.findRangeByAddress(slot);if(!inUnity(slot)||!range||!range.protection.includes('r')||range.protection.includes('x')||!slot.and(7).isNull())throw Error('native_slot_not_aligned_readable_UnityPlayer_data');
     const target=slot.readPointer(),targetRange=target.isNull()?null:Process.findRangeByAddress(target);if(target.isNull()||!inUnity(target)||!targetRange||!targetRange.protection.includes('x'))throw Error('native_slot_target_not_executable_UnityPlayer');
     row.classification='native_slot';row.target=target.toString();let g=byTarget.get(row.target);if(!g){g={target,aliases:[],prefix24:hex(target,24)};byTarget.set(row.target,g);groups.push(g);}g.aliases.push({path,typeName:row.typeName,slot});counts.nativeSlots++;}}catch(e){row.classification='unsupported';row.reason=String(e);counts.unsupported++;}
    if(live(children)){const n=children.length;if(!Number.isSafeInteger(n)||n<0||n>256){complete=false;error='Original PlayerLoop child array bound exceeded';return;}for(let i=0;i<n;i++){if(!complete)return;walk(children.get(i),path+'/'+i,depth+1);}}
   }catch(e){row.classification='unsupported';row.reason=String(e);counts.unsupported++;complete=false;error='Original PlayerLoop field/tree read failed: '+String(e);}
  }
  walk(unboxed,'root',0);return {complete,nodeCount:nodes.length,groups,nodes,counts,error,source:'original_GetCurrentPlayerLoop',callbacksInvoked:0,loopMutated:false};
 }};
}

// Passive original GC export entries; these are NOT PlayerLoop function slots.
function createNativePlayerLoopDiscoveryWithGc(pin){
 const discovery=createNativePlayerLoopDiscovery(pin),game=Process.getModuleByName('GameAssembly.dll'),specs=[{"name":"il2cpp_gc_collect","rva":8087888,"prefix24":"e98bfa0a00cccccccccccccccccccccce98bfa0a00cccccc"},{"name":"il2cpp_gc_collect_a_little","rva":8087904,"prefix24":"e98bfa0a00cccccccccccccccccccccce98bfa0a00cccccc"},{"name":"il2cpp_gc_start_incremental_collection","rva":8088128,"prefix24":"e95b0b0b00cccccccccccccccccccccc488bca498bd0e905"}];
 const groups=specs.map(s=>{const target=game.getExportByName(s.name),range=Process.findRangeByAddress(target);
  const hex=Array.from(new Uint8Array(target.readByteArray(24)),x=>x.toString(16).padStart(2,'0')).join('');
  if(!target.equals(game.base.add(s.rva))||!range||!range.protection.includes('x')||hex!==s.prefix24)throw Error('Original GC export source differs '+s.name);
  return {target,prefix24:s.prefix24,aliases:[{path:'OriginalGcExports/'+s.name,typeName:s.name,slot:null,sourceKind:'original_gc_export'}]};
 });
 return {discover(){const found=discovery.discover();return {...found,groups:found.groups.concat(groups),extraOriginalGcExportTargets:groups.length};}};
}

// Passive native callbacks only; no native callback is invoked/replaced/reordered.
function createNativePlayerLoopTiming(discovery,emit) {
 const limit=259,kernel=Process.getModuleByName('kernel32.dll'),qpc=kernel.getExportByName('QueryPerformanceCounter'),frequency=kernel.getExportByName('QueryPerformanceFrequency'),thread=kernel.getExportByName('GetCurrentThreadId');
 for(const p of [qpc,frequency,thread]){const owner=Process.findModuleByAddress(p);if(!owner||!['kernel32.dll','kernelbase.dll'].includes(owner.name.toLowerCase()))throw Error('Original OS timer export owner differs');}
 const alloc=n=>{const p=Memory.alloc(n);p.writeByteArray(new Uint8Array(n));return p;};
 const active=alloc(4),inflight=alloc(4),inside=alloc(4),ownerThread=alloc(4),counts=alloc(limit*2*4),totals=alloc(limit*2*8),maxima=alloc(limit*2*8),failures=alloc(4),ignored=alloc(4),overflow=alloc(4),freq=alloc(8);
 if(new NativeFunction(frequency,'int',['pointer'])(freq)!==1||Number(freq.readS64().toString())<=0)throw Error('Original QPC frequency unavailable');
 const native=new CModule(`
#include <gum/guminterceptor.h>
extern int original_qpc(gint64 *value);
extern guint original_thread(void);
extern volatile gint active_flag,inflight_count,inside_action;
extern guint owner_thread,counts[],failure_count,ignored_count,overflow_count;
extern gint64 totals[],maxima[];
typedef struct {gint64 begin;guint index;guint armed;} TimingInvocation;
static void increment(guint *p){guint old=1;__asm__ volatile("lock xaddl %0, %1":"+r"(old),"+m"(*p)::"memory");}
static void enter(GumInvocationContext *ic,guint index){
 TimingInvocation *d=GUM_IC_GET_INVOCATION_DATA(ic,TimingInvocation);d->armed=0;
 if(!active_flag)return;
 if(original_thread()!=owner_thread){increment(&ignored_count);return;}
 if(!original_qpc(&d->begin)){failure_count++;return;}
 d->index=index*2+(inside_action?1:0);d->armed=1;inflight_count++;
}
void leave(GumInvocationContext *ic){
 TimingInvocation *d=GUM_IC_GET_INVOCATION_DATA(ic,TimingInvocation);if(!d->armed)return;d->armed=0;
 gint64 end=0;if(!original_qpc(&end)||end<d->begin){failure_count++;inflight_count--;return;}
 guint i=d->index;gint64 elapsed=end-d->begin;
 if(counts[i]==0xffffffffU||elapsed>0x7fffffffffffffffLL-totals[i])overflow_count++;
 else {counts[i]++;totals[i]+=elapsed;if(elapsed>maxima[i])maxima[i]=elapsed;}
 inflight_count--;
}
${Array.from({length:limit},(_,i)=>`void enter_${i}(GumInvocationContext *ic){enter(ic,${i});}`).join('\n')}
`,{original_qpc:qpc,original_thread:thread,active_flag:active,inflight_count:inflight,inside_action:inside,owner_thread:ownerThread,counts,totals,maxima,failure_count:failures,ignored_count:ignored,overflow_count:overflow});
 let started=false,closed=false,deactivated=false,startAt=null,deactivatedAt=null,closedAt=null,fault=null,coverage=null,groups=[];const listeners=[];
 const hex=p=>Array.from(new Uint8Array(p.readByteArray(24)),v=>v.toString(16).padStart(2,'0')).join('');
 const rate=Number(freq.readS64().toString());
 const summary=()=>({started,closed,deactivated,startAt,deactivatedAt,closedAt,fault,coverage,ownerThread:ownerThread.readU32(),active:active.readS32()!==0,inflight:inflight.readS32(),failures:failures.readU32(),ignoredOtherThreadEntries:ignored.readU32(),overflow:overflow.readU32(),
   hookedGroups:listeners.length,returnOnlyGroups:groups.filter(g=>g.timingStatus==='original_return_only_stub').length,unavailableHookGroups:groups.filter(g=>g.timingStatus==='native_interception_unavailable').length,
   complete:started&&closed&&deactivated&&listeners.length>0&&coverage?.complete===true&&(coverage?.counts?.unsupported||0)===0&&!groups.some(g=>g.timingStatus==='native_interception_unavailable')&&!fault&&inflight.readS32()===0&&failures.readU32()===0&&ignored.readU32()===0&&overflow.readU32()===0,
   groups:groups.map((g,i)=>({target:g.target.toString(),prefix24:g.prefix24,timingStatus:g.timingStatus,attachError:g.attachError||null,measured:g.timingStatus==='hooked',aliases:g.aliases.map(a=>({...a,slot:a.slot===null?null:a.slot.toString()})),partitions:[0,1].map(partition=>{const at=i*2+partition;return {insideSchedulerAction:partition===1,count:counts.add(at*4).readU32(),inclusiveQpcTicks:totals.add(at*8).readS64().toString(),inclusiveWallMs:Number(totals.add(at*8).readS64().toString())/rate*1000,maxWallMs:Number(maxima.add(at*8).readS64().toString())/rate*1000};})})),
   mainThreadOnly:true,inclusiveAndNestedNotAdditive:true,partitionAtNativeEntry:true,firstEnclosingPhaseNotRetroactivelyTimed:true,originalArgumentsAndReturnsUntouched:true,playerLoopWritten:false,noJsPerNativeCallback:true});
 function deactivate(sample){if(deactivated)return;active.writeS32(0);deactivated=true;deactivatedAt={wallMs:Date.now(),nativeTick:sample?.tick??null,playTime:sample?.playTime??null};}
 function close(){
  if(closed)return;deactivate(null);closed=true;closedAt={wallMs:Date.now()};const errors=[];
  if(inflight.readS32()!==0)errors.push('Native PlayerLoop timer closed with in-flight callback');
  for(const listener of listeners)try{listener.detach();}catch(error){errors.push(String(error));}
  try{Interceptor.flush();for(const group of groups)if(hex(group.target)!==group.prefix24)errors.push('Original native callback prefix restoration differs '+group.target);}catch(error){errors.push(String(error));}
  if(errors.length)fault=(fault?fault+'; ':'')+errors.join('; ');
  emit({status:'native_playerloop_timing_closed',...summary()});if(errors.length)throw Error(errors.join('; '));
 }
 return {setInsideAction(value){if(typeof value!=='boolean')throw Error('Diagnostic action partition must be boolean');inside.writeS32(value?1:0);},start(sample){
   if(started||closed)return;
   try{const found=discovery.discover();if(found.complete!==true)throw Error('Original PlayerLoop discovery incomplete');groups=found.groups;coverage={...found,groups:undefined};
    if(!Array.isArray(groups)||groups.length>limit)throw Error('Native PlayerLoop timing target bound exceeded');
    // Validate every observed original slot/entry before the first hook.
    for(const group of groups){if(hex(group.target)!==group.prefix24)throw Error('Native PlayerLoop callback changed before attach');for(const alias of group.aliases){if(alias.slot===null){if(alias.sourceKind!=='original_gc_export')throw Error('Native timing entry missing original source kind');}else if(!ptr(alias.slot).readPointer().equals(group.target))throw Error('Native PlayerLoop slot changed before attach');}}
    groups.forEach((group,i)=>{
     // A source entry whose first instruction is RET/RET0 performs no body work.
     if(group.prefix24.startsWith('c3')||group.prefix24.startsWith('c20000')){group.timingStatus='original_return_only_stub';return;}
     const beforeAttempt=hex(group.target);
     try{listeners.push(Interceptor.attach(group.target,{onEnter:native['enter_'+i],onLeave:native.leave}));group.timingStatus='hooked';}
     catch(error){Interceptor.flush();if(hex(group.target)!==beforeAttempt)throw Error('Refused native hook changed callback entry: '+group.target+'; '+String(error));group.timingStatus='native_interception_unavailable';group.attachError=String(error);}
    });Interceptor.flush();
    ownerThread.writeU32(Process.getCurrentThreadId());started=true;startAt={wallMs:Date.now(),nativeTick:sample.tick,playTime:sample.playTime,phase:'after_original_manager_tick'};active.writeS32(1);
    emit({status:'native_playerloop_timing_started',...summary()});
   }catch(error){fault=String(error);try{close();}catch(cleanup){fault+='; '+String(cleanup);}throw error;}
  },deactivate,finalize(){if(!deactivated)throw Error('Native PlayerLoop timing requires deferred deactivation');if(inflight.readS32()!==0)throw Error('Native PlayerLoop timing callback still in flight');close();},close,summary,
   nativeRoots:[native,active,inflight,inside,ownerThread,counts,totals,maxima,failures,ignored,overflow,freq,discovery]};
}

// Native QPC observer: original LateUpdate phase and original runtime_invoke only.
function createNativeLateUpdateOwnerTiming(discovery,emit){
 const spec={
  "name": "il2cpp_runtime_invoke",
  "rva": 8089472,
  "prefix24": "e9cba20500cccccccccccccccccccccce9aba30500cccccc"
},game=Process.getModuleByName('GameAssembly.dll'),invoke=game.getExportByName(spec.name);
 const hex=p=>Array.from(new Uint8Array(p.readByteArray(24)),v=>v.toString(16).padStart(2,'0')).join('');
 if(!invoke.equals(game.base.add(spec.rva))||hex(invoke)!==spec.prefix24)throw Error('Original runtime_invoke source differs');
 const kernel=Process.getModuleByName('kernel32.dll'),qpc=kernel.getExportByName('QueryPerformanceCounter'),frequency=kernel.getExportByName('QueryPerformanceFrequency'),thread=kernel.getExportByName('GetCurrentThreadId');
 for(const p of [qpc,frequency,thread]){const m=Process.findModuleByAddress(p);if(!m||!['kernel32.dll','kernelbase.dll'].includes(m.name.toLowerCase()))throw Error('Original native QPC owner differs');}
 const alloc=n=>{const p=Memory.alloc(n);p.writeByteArray(new Uint8Array(n));return p;};
 const active=alloc(4),owner=alloc(4),inflight=alloc(4),lateDepth=alloc(4),invokeDepth=alloc(4),keys=alloc(256*8),counts=alloc(256*4),totals=alloc(256*8),maxima=alloc(256*8),rootCounts=alloc(256*4),rootTotals=alloc(256*8),phaseCount=alloc(4),phaseTotal=alloc(8),phaseMax=alloc(8),invocations=alloc(4),rootCount=alloc(4),rootTotal=alloc(8),failures=alloc(4),overflow=alloc(4),ignored=alloc(4),freq=alloc(8);
 if(new NativeFunction(frequency,'int',['pointer'])(freq)!==1||Number(freq.readS64().toString())<=0)throw Error('Original QPC frequency unavailable');
 const native=new CModule(`
#include <gum/guminterceptor.h>
extern int original_qpc(gint64 *value);
extern guint original_thread(void);
extern volatile gint active_flag,inflight_count,late_depth,invoke_depth;
extern guint owner_thread,counts[],root_counts[],phase_count,invocations,root_count,failure_count,overflow_count,ignored_count;
extern gpointer method_keys[];
extern gint64 totals[],maxima[],root_totals[],phase_total,phase_max,root_total;
typedef struct {gint64 begin;guint armed;guint bin;guint root;} Invocation;
static void increment(guint *p){guint old=1;__asm__ volatile("lock xaddl %0, %1":"+r"(old),"+m"(*p)::"memory");}
static int begin(GumInvocationContext *ic,Invocation *d){d->armed=0;if(!active_flag)return 0;if(original_thread()!=owner_thread){increment(&ignored_count);return 0;}if(!original_qpc(&d->begin)){failure_count++;return 0;}d->armed=1;inflight_count++;return 1;}
void phase_enter(GumInvocationContext *ic){Invocation *d=GUM_IC_GET_INVOCATION_DATA(ic,Invocation);if(begin(ic,d))late_depth++;}
void phase_leave(GumInvocationContext *ic){Invocation *d=GUM_IC_GET_INVOCATION_DATA(ic,Invocation);if(!d->armed)return;d->armed=0;late_depth--;inflight_count--;gint64 end=0;if(!original_qpc(&end)||end<d->begin){failure_count++;return;}gint64 t=end-d->begin;phase_count++;phase_total+=t;if(t>phase_max)phase_max=t;}
void invoke_enter(GumInvocationContext *ic){Invocation *d=GUM_IC_GET_INVOCATION_DATA(ic,Invocation);d->armed=0;if(!active_flag||late_depth<=0)return;if(!begin(ic,d))return;
 gpointer method=gum_invocation_context_get_nth_argument(ic,0);d->bin=256;d->root=invoke_depth==0;invoke_depth++;
 if(method==NULL){failure_count++;return;}
 guint first=((gsize)method>>4)&255;
 for(guint n=0;n<256;n++){guint at=(first+n)&255;if(method_keys[at]==NULL)method_keys[at]=method;if(method_keys[at]==method){d->bin=at;return;}}overflow_count++;
}
void invoke_leave(GumInvocationContext *ic){Invocation *d=GUM_IC_GET_INVOCATION_DATA(ic,Invocation);if(!d->armed)return;d->armed=0;invoke_depth--;inflight_count--;gint64 end=0;if(!original_qpc(&end)||end<d->begin){failure_count++;return;}gint64 t=end-d->begin;invocations++;if(d->root){root_count++;root_total+=t;}
 if(d->bin<256){guint i=d->bin;counts[i]++;totals[i]+=t;if(t>maxima[i])maxima[i]=t;if(d->root){root_counts[i]++;root_totals[i]+=t;}}
}
`,{original_qpc:qpc,original_thread:thread,active_flag:active,inflight_count:inflight,late_depth:lateDepth,invoke_depth:invokeDepth,owner_thread:owner,method_keys:keys,counts,totals,maxima,root_counts:rootCounts,root_totals:rootTotals,phase_count:phaseCount,phase_total:phaseTotal,phase_max:phaseMax,invocations,root_count:rootCount,root_total:rootTotal,failure_count:failures,overflow_count:overflow,ignored_count:ignored});
 let started=false,closed=false,deactivated=false,startAt=null,deactivatedAt=null,fault=null,phase=null,resolved=null;const listeners=[],rate=Number(freq.readS64().toString());
 const ms=p=>Number(p.readS64().toString())/rate*1000;
 function metadata(){if(resolved)return resolved;resolved=[];for(let i=0;i<256;i++){const handle=keys.add(i*8).readPointer();if(handle.isNull())continue;const row={methodInfo:handle.toString(),count:counts.add(i*4).readU32(),inclusiveWallMs:ms(totals.add(i*8)),maxWallMs:ms(maxima.add(i*8)),outermostCount:rootCounts.add(i*4).readU32(),outermostWallMs:ms(rootTotals.add(i*8))};try{const m=new Il2Cpp.Method(handle);row.className=m.class.type.name;row.methodName=m.name;row.parameters=m.parameters.map(p=>p.type.name);row.returnType=m.returnType.name;row.methodRva=m.virtualAddress.sub(game.base).toString();}catch(error){row.metadataError=String(error);}resolved.push(row);}return resolved;}
 const summary=()=>({started,closed,deactivated,startAt,deactivatedAt,fault,phase:phase?{target:phase.target.toString(),aliases:phase.aliases.map(a=>({...a,slot:a.slot.toString()}))}:null,
  phaseCount:phaseCount.readU32(),phaseInclusiveWallMs:ms(phaseTotal),phaseMaxWallMs:ms(phaseMax),runtimeInvokeCount:invocations.readU32(),outermostRuntimeInvokeCount:rootCount.readU32(),outermostRuntimeInvokeWallMs:ms(rootTotal),owners:closed?metadata():[],
  inflight:inflight.readS32(),lateDepth:lateDepth.readS32(),invokeDepth:invokeDepth.readS32(),failures:failures.readU32(),overflow:overflow.readU32(),ignoredOtherThreads:ignored.readU32(),
  ownerMetadataComplete:closed?metadata().every(row=>!row.metadataError):false,complete:started&&closed&&deactivated&&!fault&&lateDepth.readS32()===0&&invokeDepth.readS32()===0&&metadata().every(row=>!row.metadataError)&&phaseCount.readU32()>0&&invocations.readU32()>0&&inflight.readS32()===0&&failures.readU32()===0&&overflow.readU32()===0&&ignored.readU32()===0,
  ownerDataAvailable:invocations.readU32()>0,allLateUpdateOwnersCovered:false,coverageMeaning:'Only observed original runtime_invoke calls while actual LateUpdate phase active; bypassed direct thunks remain possible',timingsInclusiveMayNest:true,originalArgumentsAndReturnsUntouched:true,noInstanceAddressesRetained:true,noJsPerNativeCall:true,gameClockWritten:false});
 function deactivate(sample){if(deactivated)return;active.writeS32(0);deactivated=true;deactivatedAt={wallMs:Date.now(),nativeTick:sample?.tick??null,playTime:sample?.playTime??null};}
 function close(){if(closed)return;deactivate(null);closed=true;const errors=[];if(inflight.readS32()!==0)errors.push('LateUpdate native invocation still in flight');for(const listener of listeners)try{listener.detach();}catch(error){errors.push(String(error));}try{Interceptor.flush();if(hex(invoke)!==spec.prefix24)errors.push('Original runtime_invoke prefix not restored');if(phase&&hex(phase.target)!==phase.prefix24)errors.push('Original LateUpdate prefix not restored');}catch(error){errors.push(String(error));}if(errors.length)fault=(fault?fault+'; ':'')+errors.join('; ');emit({status:'native_lateupdate_owner_timing_closed',...summary()});if(errors.length)throw Error(errors.join('; '));}
 return {start(sample){if(started||closed)return;try{const found=discovery.discover();if(found.complete!==true)throw Error('Original PlayerLoop discovery incomplete');const matches=found.groups.filter(g=>g.aliases.some(a=>a.typeName==='UnityEngine.PlayerLoop.PreLateUpdate.ScriptRunBehaviourLateUpdate'));if(matches.length!==1)throw Error('Original LateUpdate phase target is ambiguous');phase=matches[0];if(hex(invoke)!==spec.prefix24||hex(phase.target)!==phase.prefix24)throw Error('Original invocation/phase entry changed');for(const a of phase.aliases)if(!ptr(a.slot).readPointer().equals(phase.target))throw Error('Original LateUpdate slot changed');listeners.push(Interceptor.attach(invoke,{onEnter:native.invoke_enter,onLeave:native.invoke_leave}));listeners.push(Interceptor.attach(phase.target,{onEnter:native.phase_enter,onLeave:native.phase_leave}));Interceptor.flush();owner.writeU32(Process.getCurrentThreadId());started=true;startAt={wallMs:Date.now(),nativeTick:sample.tick,playTime:sample.playTime};active.writeS32(1);emit({status:'native_lateupdate_owner_timing_started',...summary()});}catch(error){fault=String(error);try{close();}catch(cleanup){fault+='; '+String(cleanup);}throw error;}},deactivate,finalize(){if(!deactivated||inflight.readS32()!==0||lateDepth.readS32()!==0||invokeDepth.readS32()!==0)throw Error('LateUpdate timing requires completed deferred deactivation');close();},close,summary,nativeRoots:[native,active,owner,inflight,lateDepth,invokeDepth,keys,counts,totals,maxima,rootCounts,rootTotals,phaseCount,phaseTotal,phaseMax,invocations,rootCount,rootTotal,failures,overflow,ignored,freq,discovery]};
}

// Passive original FX quality witness; no settings/cache/list writes.
function createNativeFxQualityWitness(runtime,manager,pin,emit,input={quality:0}) {
 if(input.quality!==0||typeof pin!=='function'||typeof emit!=='function')throw Error('FX witness requires explicit original minimum quality0 and pin/emit');
 const game=Process.getModuleByName('GameAssembly.dll'),controllerClass=runtime.class('NK.Spot.Presentation.FXController'),fx=controllerClass.nested('FxCache'),setting=runtime.class('NK.Spot.SpotSetting');
 function guard(k,n,r,params,prefix){const ms=k.methods.filter(m=>m.name===n&&!m.isStatic&&m.returnType.name===(n==='Init'?'System.Void':'System.Collections.Generic.List<System.String>')&&m.parameters.length===params.length&&m.parameters.every((p,i)=>p.type.name===params[i]));if(ms.length!==1)throw Error('Original FX witness declaration changed: '+n);const m=ms[0];if(!m.virtualAddress.equals(game.base.add(r)))throw Error('Original FX witness RVA changed: '+n);const b=Array.from(new Uint8Array(m.virtualAddress.readByteArray(24)),v=>v.toString(16).padStart(2,'0')).join('');if(b!==prefix)throw Error('Original FX witness prefix changed: '+n);return m;}
 const init=guard(fx,'Init',0x544e2b0,[],'40534883ec20803da3c34e0600488bd9752b488d0d9f7cbe');
 const getNames=guard(setting,'GetFxOptionList',0x7609850,['NK.Types.System.UserData.BattleEffectQuality'],'85d27508488b8148040000c383fa01740333c0c3488b8140');
 const qualityField=fx.field('_battleEffectQuality'),settingField=manager.class.field('<Setting>k__BackingField');
 if(qualityField.isStatic||qualityField.offset!==32||qualityField.type.name!=='NK.Types.System.UserData.BattleEffectQuality'||settingField.isStatic||settingField.offset!==168||settingField.type.name!=='NK.Spot.SpotSetting')throw Error('Original FX witness field ABI changed');
 const instanceField=controllerClass.field('_instance'),cacheField=controllerClass.field('_fxCache');if(!instanceField.isStatic||instanceField.offset!==0||instanceField.type.name!=='NK.Spot.Presentation.FXController'||cacheField.isStatic||cacheField.offset!==64||cacheField.type.name!==fx.type.name)throw Error('Original FX singleton/cache field ABI changed');
 pin(manager);const caches=new Map();let closed=false,observed=false,fault=null,overflow=false,initEntries=0,initLeaves=0,authored=null;
 const number=v=>typeof v==='number'?v:Number(v.field('value__').value);
 const noteError=e=>{fault=String(e);emit({status:'original_fx_quality_witness_fault',error:fault});};
 const listener=Interceptor.attach(init.virtualAddress,{onEnter(args){if(closed)return;try{initEntries++;if(args[0].isNull())throw Error('Original FxCache this null');const key=args[0].toString();if(!caches.has(key)){if(caches.size>=4){overflow=true;throw Error('Original FxCache witness owner bound exceeded');}const object=new Il2Cpp.Object(args[0]);if(object.class.type.name!==fx.type.name)throw Error('Original FxCache actual class changed');caches.set(key,{object:pin(object),address:key,quality:null});}this.cache=caches.get(key);}catch(e){noteError(e);}},onLeave(){if(closed||!this.cache)return;try{initLeaves++;const q=number(this.cache.object.field(qualityField.name).value);this.cache.quality=q;emit({status:'original_fx_cache_quality_readback',quality:q,requestedQuality:0,passed:q===0,address:this.cache.address,nativeInitReturned:true,cacheWritten:false});}catch(e){noteError(e);}}});
 return {observe(phase){if(closed||observed)return;const playing=phase==='Playing'||phase===6||phase&&phase.state===6||phase&&phase.lifecycle&&phase.lifecycle.state===6;if(!playing)return;observed=true;
  try{const controller=instanceField.value;if(!controller||controller.isNull())throw Error('Original FXController instance missing at Playing');const cache=controller.field(cacheField.name).value;if(!cache||cache.isNull()||cache.class.type.name!==fx.type.name)throw Error('Original FXController cache missing at Playing');const key=cache.handle.toString();if(!caches.has(key)){if(caches.size>=4){overflow=true;throw Error('Original FxCache witness owner bound exceeded');}caches.set(key,{object:pin(cache),address:key,quality:null});}const row=caches.get(key);row.quality=number(cache.field(qualityField.name).value);emit({status:'original_fx_cache_quality_readback',quality:row.quality,requestedQuality:0,passed:row.quality===0,address:key,source:'original_FXController_static_instance_cache_at_Playing',nativeInitMayBeInlined:true,cacheWritten:false});
   const value=manager.field(settingField.name).value;if(!value||value.isNull()){authored={supported:false,reason:'original_setting_missing'};emit({status:'original_fx_quality_authored_names',...authored});return;}
   const listValue=invokeChecked(getNames,value,[intArg(0)]);if(!listValue||listValue.isNull()){authored={supported:false,reason:'original_minimum_list_null'};emit({status:'original_fx_quality_authored_names',...authored});return;}
   const list=pin(listValue);if(list.class.type.name!=='System.Collections.Generic.List<System.String>')throw Error('Original FX exclusion list type changed');
   const countMethod=list.method('get_Count',0),itemMethod=list.method('get_Item',1);if(countMethod.returnType.name!=='System.Int32'||itemMethod.returnType.name!=='System.String'||itemMethod.parameters[0].type.name!=='System.Int32')throw Error('Original FX list getter ABI changed');
   const count=invokeChecked(countMethod,list,[]).unbox().handle.readS32();if(!Number.isInteger(count)||count<0||count>4096)throw Error('Original FX exclusion list bound exceeded');const names=[];
   for(let i=0;i<count;i++){const str=invokeChecked(itemMethod,list,[intArg(i)]);if(!str||str.isNull())throw Error('Original FX exclusion name null');if(str.class.type.name!=='System.String')throw Error('Original FX exclusion value not System.String');const name=new Il2Cpp.String(str.handle).content;if(typeof name!=='string'||name.length>2048)throw Error('Original FX exclusion name bound exceeded');names.push(name);}
   authored={supported:true,quality:0,names,count};emit({status:'original_fx_quality_authored_names',...authored,source:'original_SpotSetting_GetFxOptionList',listsWritten:false});
  }catch(e){authored={supported:false,reason:'original_read_failed'};noteError(e);}
 },close(){if(closed)return;listener.detach();closed=true;},summary(){return {closed,observed,fault,overflow,initEntries,initLeaves,caches:[...caches.values()].map(c=>({address:c.address,quality:c.quality,passed:c.quality===0})),authored};}};
}

// Read the original settings application. All hooks are observation only.
function createNativePostprocessApplicationWitness(runtime, emit) {
  const game = Process.getModuleByName('GameAssembly.dll');
  const profileType = 'UnityEngine.Rendering.VolumeProfile';
  const componentType = 'UnityEngine.Rendering.VolumeComponent';
  const video = runtime.class('NK.Common.System.Settings.NikkeVideoSetting');
  const rendering = Il2Cpp.domain.assembly('Unity.RenderPipelines.Core.Runtime').image;
  const profile = rendering.class(profileType);
  const component = rendering.class(componentType);
  const active = component.field('active');
  const flags = video.field('PostProcessFlags');
  const apply = video.method('ApplyCurrentVideoSettingToVolumeProfile', 1);
  if (profile.type.name !== profileType || component.type.name !== componentType ||
      active.isStatic || active.offset !== 24 || active.type.name !== 'System.Boolean' ||
      !video.isValueType || video.valueTypeSize !== 36 || flags.isStatic ||
      flags.offset !== 20 || flags.type.name !== 'NK.Types.System.UserData.PostProcessType' ||
      apply.isStatic || apply.returnType.name !== 'System.Void' ||
      apply.parameters.length !== 1 || apply.parameters[0].type.name !== profileType ||
      !apply.virtualAddress.equals(game.base.add(0x6f038e0))) {
    throw Error('Original post-process metadata changed');
  }
  const tryGet = game.base.add(0xb11ad0);
  function guard(address, prefix) {
    const actual = Array.from(new Uint8Array(address.readByteArray(24)),
      byte => byte.toString(16).padStart(2, '0')).join('');
    if (actual !== prefix) throw Error('Original post-process entry changed: ' + address);
  }
  guard(apply.virtualAddress, '40555357488bec4883ec50803d0056a40400488bfa488bd9');
  guard(tryGet, '48895c240848896c24104889742418574883ec20803d9c40');
  const sites = new Map([
    [0x6f039de, [0xb0153e8, 2]], [0x6f03a3d, [0xb0174d0, 4]],
    [0x6f03a64, [0xb017878, 4]], [0x6f03a8b, [0xb015b38, 4]],
    [0x6f03ab2, [0xb015790, 4]], [0x6f03ad9, [0xb0169d8, 4]],
    [0x6f03afc, [0xb015ee0, 4]], [0x6f03b1f, [0xb017128, 4]],
  ].map(([rva, [slot, mask]]) => [game.base.add(rva).toString(), {rva, slot, mask}]));
  const frames = new Map();
  const counts = {baseline: 0, apply: 0, restore: 0};
  const passed = {baseline: 0, apply: 0, restore: 0};
  const listeners = [];
  let closed = false;
  let fault = null;
  let phase = null;
  let ordinal = 0;

  function reportFault(error) {
    fault = String(error);
    frames.clear();
    try{detachTryGet();}catch(detach){fault+='; detach: '+String(detach);}
    try{emit({status: 'original_postprocess_witness_fault', error: fault});}catch(_){}
  }

  function classIncludes(klass, name) {
    for (let depth = 0; klass && depth < 32; depth++, klass = klass.parent) {
      if (klass.type.name === name) return true;
    }
    return false;
  }

  function readActive(handle) {
    const value = handle.add(24).readU8();
    if (value !== 0 && value !== 1) throw Error('Original VolumeComponent.active is not Boolean');
    return value === 1;
  }

  const tryCallbacks = {
      onEnter(args) {
        if (closed || fault) return;
        const site = sites.get(this.returnAddress.toString());
        const frame = frames.get(this.threadId);
        if (!site || !frame) return;
        try {
          if (!frame.profile.equals(args[0]) || args[1].isNull() || args[2].isNull() ||
              !game.base.add(site.slot).readPointer().equals(args[2]) ||
              frame.rows.has(site.rva)) {
            throw Error('Original post-process lookup ownership or MethodInfo changed');
          }
          const method = new Il2Cpp.Method(args[2]);
          if (method.class.type.name !== profileType || method.name !== 'TryGet' ||
              method.isStatic || method.returnType.name !== 'System.Boolean' ||
              method.parameters.length !== 1) {
            throw Error('Original VolumeProfile.TryGet metadata changed');
          }
          const byrefName = method.parameters[0].type.name;
          const typeName = byrefName.endsWith('&') ? byrefName.slice(0, -1) : '';
          const requestedType = /^[\w.]+\.[\w.]+$/.test(typeName) ? typeName : null;
          const row = {rva: site.rva, mask: site.mask, requestedType, found: null};
          frame.rows.set(site.rva, row);
          this.lookup = {frame, row, out: args[1]};
        } catch (error) { reportFault(error); }
      },
      onLeave(retval) {
        if (closed || fault || !this.lookup) return;
        try {
          const {frame, row, out} = this.lookup;
          if (frames.get(this.threadId) !== frame) throw Error('Original lookup frame lost');
          const result = retval.toInt32() & 0xff;
          if (result !== 0 && result !== 1) throw Error('Original TryGet result is not Boolean');
          row.found = result === 1;
          if (!row.found) return;
          const handle = out.readPointer();
          if (handle.isNull()) throw Error('Original successful lookup returned null');
          const object = new Il2Cpp.Object(handle);
          if (!classIncludes(object.class, componentType)) throw Error('Original object is not a VolumeComponent');
          row.actualType = object.class.type.name;
          row.componentAddress = handle.toString();
          row.beforeActive = readActive(handle);
          row.handle = handle;
        } catch (error) { reportFault(error); }
      },
  };
  let tryListener=null;
  function attachTryGet(){if(tryListener)return;tryListener=Interceptor.attach(tryGet,tryCallbacks);Interceptor.flush();}
  function detachTryGet(){if(!tryListener)return;const listener=tryListener;tryListener=null;listener.detach();Interceptor.flush();}
  try {
    listeners.push(Interceptor.attach(apply.virtualAddress, {
      onEnter(args) {
        if (closed || fault || !phase) return;
        try {
          if (frames.has(this.threadId) || frames.size >= 4 || ordinal >= 128) {
            throw Error('Original post-process observation bound exceeded');
          }
          if (args[0].isNull()) throw Error('Original unboxed VideoSetting receiver missing');
          const frame = {id: ++ordinal, phase, profile: args[1], flags: args[0].add(4).readS32(),
            rows: new Map()};
          if (!frame.profile.isNull() &&
              new Il2Cpp.Object(frame.profile).class.type.name !== profileType) {
            throw Error('Original VolumeProfile receiver type changed');
          }
          frames.set(this.threadId, frame);
          this.frame = frame;
          attachTryGet();
        } catch (error) { reportFault(error); }
      },
      onLeave() {
        if (closed || fault || !this.frame) return;
        try {
          const frame = this.frame;
          if (frames.get(this.threadId) !== frame) throw Error('Original application frame lost');
          frames.delete(this.threadId);
          if(!frames.size)detachTryGet();
          const rows = [...frame.rows.values()].map(({handle, ...row}) => {
            const outcome = !row.requestedType ? 'requested_type_unresolved' :
              row.found === false ? 'component_absent' : 'lookup_return_unobserved';
            if (!handle) return {...row, outcome};
            const afterActive = readActive(handle);
            const expectedActive = (frame.flags & row.mask) !== 0;
            const matches = row.requestedType === row.actualType && afterActive === expectedActive;
            return {...row, afterActive, expectedActive,
              outcome: !row.requestedType ? outcome : matches ? 'verified' : 'readback_mismatch'};
          });
          const {name, expectedFlags} = frame.phase;
          const verifiedPresent=rows.filter(row=>row.outcome==='verified').length;
          const knownAbsent=rows.filter(row=>row.outcome==='component_absent').length;
          const completeLookups=rows.length===sites.size&&verifiedPresent+knownAbsent===sites.size;
          const verified=completeLookups&&verifiedPresent>0&&frame.flags===expectedFlags;
          counts[name]++;
          if (verified) passed[name]++;
          emit({status: 'original_postprocess_application_readback', phase: name, id: frame.id,
            profileAddress: frame.profile.toString(), observedFlags: frame.flags, expectedFlags,
            outcome: rows.length === 0 ? 'no_lookup_observed' : verified ? 'verified' : 'incomplete',
            verified, completeLookups, verifiedPresent, knownAbsent, rows});
        } catch (error) { reportFault(error); }
      },
    }));
  } catch (error) {
    for (const listener of listeners) listener.detach();
    throw error;
  }
  return {
    setPhase(name, expectedFlags) {
      if (!Object.prototype.hasOwnProperty.call(counts, name) || !Number.isInteger(expectedFlags) ||
          expectedFlags !== (name === 'apply' ? 0 : -1)) {
        throw Error('Invalid post-process witness phase or flags');
      }
      if (closed || fault || frames.size) return false;
      phase = {name, expectedFlags};
      return true;
    },
    close() {
      if (closed) return;
      closed = true;
      frames.clear();
      try{detachTryGet();}finally{for(const listener of listeners)listener.detach();}
      emit({status:"original_postprocess_witness_closed",...this.summary(),scopedTryGetDetached:tryListener===null});
    },
    summary() { return {closed, fault, counts: {...counts}, passed: {...passed}}; },
  };
}
