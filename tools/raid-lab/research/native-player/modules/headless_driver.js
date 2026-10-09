import "frida-il2cpp-bridge";

// A mechanics bootstrap in the existing private, offline Unity host. This file
// never enters the normal battle scene. Original aim geometry is initialized
// only inside this private Null-graphics diagnostic; nothing is displayed.
const record = row => {
  const file = new File("scene-events.jsonl", "a");
  file.write(JSON.stringify({time: Date.now(), ...row}) + "\n");
  file.flush(); file.close();
};
record({phase:"gadget_loaded", pid:Process.id, scope:"headless_mechanics"});

let firstAsyncFault = null;
let probeQuitRequested = false;
function nativeExceptionDetail(exception) {
  const runtime=Process.getModuleByName("GameAssembly.dll");
  const buffer=Memory.alloc(8192);
  new NativeFunction(runtime.getExportByName("il2cpp_format_exception"),"void",
    ["pointer","pointer","int"])(exception,buffer,8192);
  const addresses=Memory.alloc(Process.pointerSize), count=Memory.alloc(4);
  const uuid=Memory.alloc(Process.pointerSize), image=Memory.alloc(Process.pointerSize);
  addresses.writePointer(NULL); count.writeS32(0); uuid.writePointer(NULL); image.writePointer(NULL);
  new NativeFunction(runtime.getExportByName("il2cpp_native_stack_trace"),"void",
    ["pointer","pointer","pointer","pointer","pointer"])(
      exception,addresses,count,uuid,image);
  const n=count.readS32(), frames=addresses.readPointer(), nativeFrames=[];
  if (!frames.isNull() && n>0 && n<1000) {
    for (let i=0;i<n;i++) {
      const address=frames.add(i*Process.pointerSize).readPointer();
      // This installed build returns relative native stack addresses. Accept
      // an absolute address only if it lies inside the actual module.
      const relative=address.compare(runtime.base)>=0 &&
        address.compare(runtime.base.add(runtime.size))<0 ? address.sub(runtime.base) : address;
      nativeFrames.push({reportedAddress:address.toString(),rva:relative.toString()});
    }
  }
  return {error:buffer.readUtf8String(),nativeFrames};
}

// Cache the native entry point, never a method's result or argument buffers.
// Each tick still calls the original runtime and checks its own exception slot.
let checkedNativeInvoke=null;
function invokeChecked(method, instance, values=[]) {
  if (checkedNativeInvoke===null) {
    checkedNativeInvoke=new NativeFunction(Process.getModuleByName("GameAssembly.dll")
      .getExportByName("il2cpp_runtime_invoke"), "pointer",
      ["pointer","pointer","pointer","pointer"]);
  }
  const args = Memory.alloc(Math.max(1,values.length)*Process.pointerSize);
  values.forEach((value,index)=>args.add(index*Process.pointerSize).writePointer(value));
  const error = Memory.alloc(Process.pointerSize); error.writePointer(NULL);
  let result;
  try {
    result=checkedNativeInvoke(method.handle,instance ? instance.handle : NULL,args,error);
  } catch(fault) {
    // NativeFunction can convert an OS fault before the passive Windows
    // observer sees it. Preserve its native context instead of only JS stack.
    const detail={phase:"native_invoke_fault",method:method.name,
      error:String(fault),properties:Object.getOwnPropertyNames(fault)};
    try {
      const game=Process.getModuleByName("GameAssembly.dll");
      const rva=p=>p.compare(game.base)>=0 && p.compare(game.base.add(game.size))<0
        ? p.sub(game.base).toString() : null;
      detail.type=fault.type || null;
      detail.address=fault.address ? fault.address.toString() : null;
      detail.gameRva=fault.address ? rva(fault.address) : null;
      if (fault.address) {
        const faultModule=Process.findModuleByAddress(fault.address);
        const faultRange=Process.findRangeByAddress(fault.address);
        detail.faultModule=faultModule ? faultModule.name : null;
        detail.faultRange=faultRange ? {base:faultRange.base.toString(),
          size:faultRange.size,protection:faultRange.protection} : null;
      }
      if (fault.memory) detail.memory={operation:fault.memory.operation,
        address:fault.memory.address.toString()};
      if (fault.context) {
        detail.pc=fault.context.pc.toString();
        detail.gamePcRva=rva(fault.context.pc);
        if (fault.memory && fault.memory.operation==="execute") {
          const returnAddress=fault.context.sp.readPointer();
          detail.stackReturnAddress=returnAddress.toString();
          detail.stackReturnGameRva=rva(returnAddress);
        }
        detail.registers={};
        for (const name of ["rax","rcx","rdx","r8","r9","rbx","rdi","rsi"])
          detail.registers[name]=fault.context[name].toString();
        detail.gameAssemblyRvas=Thread.backtrace(fault.context,Backtracer.FUZZY)
          .map(rva).filter(Boolean).slice(0,16);
        fault.nativeFrames=detail.gameAssemblyRvas;
      }
    } catch(observationError) { detail.observationError=String(observationError); }
    record(detail);
    throw fault;
  }
  if (!error.readPointer().isNull()) {
    const runtime = Process.getModuleByName("GameAssembly.dll");
    const buffer = Memory.alloc(8192);
    new NativeFunction(runtime.getExportByName("il2cpp_format_exception"), "void",
      ["pointer","pointer","int"])(error.readPointer(),buffer,8192);
    const fault = new Error(method.name+": "+buffer.readUtf8String());
    const addresses=Memory.alloc(Process.pointerSize), count=Memory.alloc(4);
    const uuid=Memory.alloc(Process.pointerSize), image=Memory.alloc(Process.pointerSize);
    addresses.writePointer(NULL); count.writeS32(0); uuid.writePointer(NULL); image.writePointer(NULL);
    new NativeFunction(runtime.getExportByName("il2cpp_native_stack_trace"),"void",
      ["pointer","pointer","pointer","pointer","pointer"])(
        error.readPointer(),addresses,count,uuid,image);
    const n=count.readS32(), frames=addresses.readPointer();
    fault.nativeFrames=[];
    if (!frames.isNull() && n>0 && n<1000) {
      for (let i=0;i<n;i++) fault.nativeFrames.push(frames.add(i*Process.pointerSize).readPointer().toString());
    }
    throw fault;
  }
  return result.isNull() ? null : new Il2Cpp.Object(result);
}
const intArg = value => { const p=Memory.alloc(4); p.writeS32(Number(value)); return p; };
const floatArg = value => { const p=Memory.alloc(4); p.writeFloat(Number(value)); return p; };

let pendingMain = false;
const mainWork={queuedAt:0,enteredAt:0,returnedAt:0,threadId:null};
let pendingMainBlock=null, mainPost=null, mainPostPhase=null;
let mainPostAction=null, mainPostRoot=null, mainThreadId=null;
let mainDelivery="bridge_bootstrap";
const runMainBlock = () => {
  const block=pendingMainBlock;
  // Clear before invoking user work: even if the Unity queue repeats a
  // callback, the same work cannot run twice.
  pendingMainBlock=null;
  if (!block) {
    record({phase:"main_work_unexpected_callback",delivery:mainDelivery});
    return;
  }
  mainWork.enteredAt=Date.now(); mainWork.threadId=Process.getCurrentThreadId();
  try {
    if (mainThreadId===null) mainThreadId=mainWork.threadId;
    else if (mainWork.threadId!==mainThreadId)
      throw new Error("Main work moved off the original Unity main thread");
    if (mainDelivery==="bridge_bootstrap") {
      const game=Process.getModuleByName("GameAssembly.dll");
      const uni=Il2Cpp.domain.assembly("UniTask").image;
      const post=uni.class("Cysharp.Threading.Tasks.UniTask").method("Post",2);
      if (!post.virtualAddress.equals(game.base.add(0x07F17E50)))
        throw new Error("Original UniTask.Post method changed");
      const phase=uni.class("Cysharp.Threading.Tasks.PlayerLoopTiming").field("Update").value;
      const phaseNumber=typeof phase==="number" ? phase : Number(phase.field("value__").value);
      if (!Number.isInteger(phaseNumber)) throw new Error("Original Update phase is invalid");
      mainPostPhase=intArg(phaseNumber);
      mainPostAction=Il2Cpp.delegate(Il2Cpp.corlib.class("System.Action"),runMainBlock);
      mainPostRoot=mainPostAction.ref(true);
      mainPost=post;
      mainDelivery="original_unitask_update";
      record({phase:"main_work_delivery_ready",delivery:mainDelivery,
        postRva:"0x07F17E50",phaseNumber,mainThreadId});
    }
    block();
  } catch (error) {
    if (!firstAsyncFault) firstAsyncFault={error:String(error),nativeFrames:error.nativeFrames || []};
    record({phase:"schedule_error",status:"first_failure",delivery:mainDelivery,error:String(error)});
  } finally { pendingMain=false; mainWork.returnedAt=Date.now(); }
};
const onMain = block => {
  if (pendingMain) return false;
  pendingMain = true;
  pendingMainBlock=block;
  mainWork.queuedAt=Date.now(); mainWork.enteredAt=0;
  const queueFailure=error => {
    // A callback that already entered owns completion. A rejected queue call
    // must not leave the single-work slot occupied until the wrapper timeout.
    if (pendingMainBlock===block) { pendingMainBlock=null; pendingMain=false; }
    record({phase:"schedule_error",status:"first_failure",delivery:mainDelivery,
      error:String(error)});
  };
  if (mainDelivery==="bridge_bootstrap") {
    // The bridge can see il2cpp_get_corlib before Unity installs the main
    // thread's SynchronizationContext. Its schedule getter throws before Post,
    // so only that exact early-readiness failure may be retried. Keep each
    // perform(...,"free") synchronous and preserve the original work block.
    const earlyContext="couldn't find the synchronization context of the main thread";
    const waitLimitMs=15000, retryMs=200;
    let waitingLogged=false;
    const retryFailure=error => {
      if (pendingMainBlock===block && mainDelivery==="bridge_bootstrap" &&
          String(error).includes(earlyContext) &&
          Date.now()-mainWork.queuedAt<waitLimitMs) {
        if (!waitingLogged) {
          waitingLogged=true;
          record({phase:"main_context_pending",delivery:mainDelivery,
            queuedAt:mainWork.queuedAt,retryMs,waitLimitMs});
        }
        setTimeout(trySchedule,retryMs);
        return;
      }
      queueFailure(error);
    };
    const trySchedule=() => {
      if (pendingMainBlock!==block || mainDelivery!=="bridge_bootstrap") return;
      // Do not return/await schedule's Promise from perform(...,"free"):
      // retaining its attached worker through async work breaks shutdown.
      void Il2Cpp.perform(() => {
        void Il2Cpp.mainThread.schedule(runMainBlock).catch(retryFailure);
      },"free").catch(retryFailure);
    };
    trySchedule();
  } else {
    void Il2Cpp.perform(() => {
      invokeChecked(mainPost,null,[mainPostAction.handle,mainPostPhase]);
    },"free").catch(queueFailure);
  }
  return true;
};

const startManagedProbe = () => Il2Cpp.perform(() => {
  const runtime = Il2Cpp.domain.assembly("NK.Runtime").image;
  // Trial142 main-thread samples identify original signed-file hashing as the
  // startup wait. Observe only its file paths/duration; never replace verification
  // or read/log public-key bytes, signatures, or file contents.
  const signatureMethod=Il2Cpp.domain.assembly("Shiftup.Libsodium.Runtime").image
    .class("Shiftup.Libsodium.Utility.SignUtility").method("VerifySignature",3);
  if (!signatureMethod.virtualAddress.equals(
      Process.getModuleByName("GameAssembly.dll").base.add(0x07776A60)))
    throw new Error("Installed signed-file verifier address changed");
  let signatureObservations=0;
  const boundedPath=pointer=>{
    if (pointer.isNull()) return null;
    const length=pointer.add(0x10).readS32();
    if (length<0 || length>4096) throw new Error("Signature path length outside bound");
    return pointer.add(0x14).readUtf16String(length);
  };
  Interceptor.attach(signatureMethod.virtualAddress,{
    onEnter(args) {
      this.signatureObservation=null;
      if (signatureObservations>=24) return;
      try {
        this.signatureObservation={ordinal:++signatureObservations,
          contentPath:boundedPath(args[0]),signaturePath:boundedPath(args[1]),
          startedAt:Date.now(),threadId:Process.getCurrentThreadId()};
        record({phase:"original_signature_verification_started",...this.signatureObservation});
      } catch(error) {record({phase:"signature_observation_error",error:String(error)});}
    },
    onLeave(retval) {
      if (!this.signatureObservation) return;
      record({phase:"original_signature_verification_finished",...this.signatureObservation,
        elapsedMs:Date.now()-this.signatureObservation.startedAt,verified:retval.toInt32()!==0});
    }
  });
  // Park only the application's lobby/login bootstrap. Combat classes and
  // Unity's player loop stay original; no backend or lobby initialization starts.
  const splash = runtime.class("NK.Splash.SplashSceneControl").method("Start",0);
  const originalBase = Process.getModuleByName("GameAssembly.dll").base;
  if (!splashGate || !splash.virtualAddress.equals(originalBase.add(0x06559260))) {
    throw new Error("Original splash gate does not match current metadata");
  }
  const unity = Il2Cpp.domain.assembly("UnityEngine.CoreModule").image;
  // Observe the original async exception path without replacing or suppressing it.
  const publish=Il2Cpp.domain.assembly("UniTask").image
    .class("Cysharp.Threading.Tasks.UniTaskScheduler")
    .method("PublishUnobservedTaskException",1);
  const observeException=source=>({onEnter(args) {
    if (firstAsyncFault || args[0].isNull()) return;
    try {
      const detail=nativeExceptionDetail(args[0]);
      if (probeQuitRequested) {
        record({phase:"native_shutdown_exception",source,...detail});
        return;
      }
      firstAsyncFault=detail;
      record({phase:"native_exception",source,...detail});
    } catch(error) {
      firstAsyncFault={error:String(error),nativeFrames:[]};
      record({phase:"native_exception",source:"exception_observer",...firstAsyncFault});
    }
  }});
  Interceptor.attach(publish.virtualAddress,observeException("UniTaskScheduler"));
  const debug=unity.class("UnityEngine.Debug");
  Interceptor.attach(debug.method("CallOverridenDebugHandler",2).virtualAddress,
    observeException("Unity.Debug.CallOverridenDebugHandler"));
  Interceptor.attach(debug.method("LogException").overload("System.Exception").virtualAddress,
    observeException("Unity.Debug.LogException"));
  const app = unity.class("UnityEngine.Application");
  const roots = [];
  let taskBox = null, patchTask = null, settingsCatalog = null, finishing = false;
  let catalogStarted=0, catalogSnapshot=false, catalogLastPollAt=0;
  let catalogGapLogged=false;
  let tablePollStage="not_polled", tablePolls=0, lastStalledQueue=0;
  let interval = null, deadline = null;
  const watchdog=setInterval(()=>{
    if (!pendingMain || lastStalledQueue===mainWork.queuedAt ||
        Date.now()-mainWork.queuedAt<5000) return;
    lastStalledQueue=mainWork.queuedAt;
    record({phase:"main_work_stalled",mainWork:{...mainWork},tablePollStage,tablePolls});
    try {
      const thread=Process.enumerateThreads().find(t=>t.id===mainWork.threadId);
      if (thread) {
        const game=Process.getModuleByName("GameAssembly.dll");
        const pc=thread.context.pc;
        const gamePcRva=pc.compare(game.base)>=0 &&
          pc.compare(game.base.add(game.size))<0 ? pc.sub(game.base).toString() : null;
        record({phase:"main_work_stalled_native_pc",pc:pc.toString(),
          sp:thread.context.sp.toString(),gamePcRva,delivery:mainDelivery});
        const frames=Thread.backtrace(thread.context,Backtracer.FUZZY)
          .filter(p=>p.compare(game.base)>=0 && p.compare(game.base.add(game.size))<0)
          .slice(0,12).map(p=>p.sub(game.base).toString());
        record({phase:"main_work_stalled_native_frames",gameAssemblyRvas:frames});
      }
    } catch(error) { record({phase:"main_work_stall_observer_error",error:String(error)}); }
  },1000);
  const finish = () => {
    if (finishing) return;
    finishing = true;
    probeQuitRequested = true;
    clearInterval(interval); clearInterval(watchdog); clearTimeout(deadline);
    record({phase:"quit_requested",scope:"headless_mechanics"});
    app.method("Quit").overload("System.Int32").invoke(0);
  };
  const fail = (phase,error) => {
    record({phase,status:"first_failure",error:String(error),stack:error.stack});
    finish();
  };
  record({phase:"il2cpp_ready",unity:Il2Cpp.unityVersion});
  deadline = setTimeout(() => {
    record({phase:"probe_deadline",completed:false,pendingMain,
      mainWork:{...mainWork},tablePollStage,tablePolls});
    onMain(finish);
  }, 50000); // Includes bounded original aim initialization plus battle ticks.
  setTimeout(() => onMain(() => {
    try {
      const device = unity.class("UnityEngine.SystemInfo").method("get_graphicsDeviceType").invoke();
      const batch = app.method("get_isBatchMode").invoke();
      record({phase:"headless_runtime",batchMode:batch,graphicsDevice:String(device)});
      if (!batch || String(device) !== "Null") throw new Error("Expected batch mode and Null graphics device");
      const stream = Il2Cpp.corlib.class("System.IO.File").method("OpenRead")
        .invoke(Il2Cpp.string(__TABLE_ARCHIVE__));
      roots.push(stream.ref(true));
      const image = Il2Cpp.domain.assembly("NK.DataTable").image;
      const source = image.class("NK.DataTable.Source.ZipDataSource").alloc();
      source.method(".ctor",2).invoke(stream,image.class("NK.DataTable.StaticDataFormat").field("Mpk").value);
      roots.push(source.ref(true));
      const manager = Il2Cpp.domain.assembly("NK.Runtime.StaticData").image.class("NK.StaticData.DataManager");
      taskBox = invokeChecked(manager.method("InitializeAndLoadAllAsync",1),null,[source.handle]);
      roots.push(taskBox.ref(true));
      record({phase:"original_tables_started",addressablesInitialized:false});
    } catch (error) { fail("headless_bootstrap_error",error); }
  }), 1500);
  interval = setInterval(() => {
    if ((!taskBox && !patchTask && !settingsCatalog) || finishing) return;
    onMain(() => {
      try {
        if (patchTask) {
          const awaiter=patchTask.unbox().method("GetAwaiter").invoke();
          if (!awaiter.method("get_IsCompleted").invoke()) return;
          invokeChecked(awaiter.method("GetResult"),awaiter);
          patchTask=null;
          const manager=Il2Cpp.domain.assembly("Shiftup.Patch.Runtime").image
            .class("Shiftup.Patch.Runtime.PatchManager");
          const session=invokeChecked(manager.method("get_Session",0),null);
          const root=session.field("<RootDirectory>k__BackingField").value.content;
          const normalized=root.replace(/\\/g,"/").toLowerCase();
          const scratch=__SCRATCH_PROFILE__.replace(/\\/g,"/").toLowerCase();
          if (!normalized.startsWith(scratch+"/")) throw new Error("Patch session escaped scratch profile");
          record({phase:"original_local_patch_session_ready",root,networkMode:"deny_all"});
          const addressables=Il2Cpp.domain.assembly("Unity.Addressables").image
            .class("UnityEngine.AddressableAssets.Addressables");
          const method=addressables.method("InitializeAsync").overload("System.Boolean","System.Boolean");
          const no=Memory.alloc(1); no.writeU8(0);
          settingsCatalog=invokeChecked(method,null,[no,no]);
          catalogStarted=Date.now(); catalogLastPollAt=catalogStarted;
          roots.push(settingsCatalog.ref(true));
          record({phase:"original_mechanics_catalog_started",dependency:"SpotSetting.Load"});
          return;
        }
        if (settingsCatalog) {
          const pollAt=Date.now();
          if (!catalogGapLogged && pollAt-catalogLastPollAt>3000) {
            catalogGapLogged=true;
            record({phase:"mechanics_catalog_poll_gap",
              elapsedSinceCatalogStartMs:pollAt-catalogStarted,
              pollGapMs:pollAt-catalogLastPollAt,
              mainQueueWaitMs:mainWork.enteredAt-mainWork.queuedAt,
              tablePollStage,tablePolls});
          }
          catalogLastPollAt=pollAt;
          const handle=settingsCatalog.unbox();
          if (!handle.method("get_IsDone").invoke()) {
            if (!catalogSnapshot && Date.now()-catalogStarted>3000) {
              catalogSnapshot=true;
              const internal=handle.field("m_InternalOp").value;
              const detail={phase:"mechanics_catalog_dependency",type:internal.class.type.name};
              for (const name of ["m_rtdOp","m_loadCatalogOp"]) {
                const field=internal.class.fields.find(field=>field.name===name);
                if (!field) continue;
                const child=internal.field(name).value;
                const valid=child.method("IsValid",0).invoke();
                detail[name]={valid};
                if (valid) {
                  detail[name].status=String(child.method("get_Status").invoke());
                  const dependency=child.field("m_InternalOp").value;
                  detail[name].type=dependency.class.type.name;
                }
              }
              detail.fields=internal.class.fields.filter(f=>!f.isStatic).map(f=>({name:f.name,type:f.type.name}));
              record(detail);
            }
            return;
          }
          const status=String(handle.method("get_Status").invoke());
          if (status!=="Succeeded") {
            const error=handle.method("get_OperationException").invoke();
            throw new Error("Original mechanics catalog initialization "+status+": "+
              (error && !error.isNull() ? error.method("ToString").invoke().content : "no detail"));
          }
          clearInterval(interval); settingsCatalog=null;
          record({phase:"original_mechanics_catalog_ready",battleSceneLoaded:false});
          runMechanicsLifecycleProbe(record,finish,true);
          return;
        }
        tablePolls++;
        tablePollStage="get_awaiter";
        const awaiter = taskBox.unbox().method("GetAwaiter").invoke();
        tablePollStage="is_completed";
        const tablesDone=awaiter.method("get_IsCompleted").invoke();
        tablePollStage=tablesDone ? "get_result" : "pending";
        if (!tablesDone) return;
        invokeChecked(awaiter.method("GetResult"),awaiter);
        tablePollStage="completed";
        taskBox=null;
        record({phase:"original_tables_loaded"});
        // Original startup initializes its local PatchSession before catalog
        // lookup. This loads the existing scratch cache, never ApplyPatchAsync.
        const directory=app.method("get_persistentDataPath").invoke();
        const normalized=directory.content.replace(/\\/g,"/").toLowerCase();
        const scratch=__SCRATCH_PROFILE__.replace(/\\/g,"/").toLowerCase();
        if (!normalized.startsWith(scratch+"/")) throw new Error("Persistent path escaped scratch profile");
        const settings=runtime.class("NK.Common.System.Settings.NikkeSettings");
        const platformSetting=invokeChecked(settings.method("get_PlatformDependentSetting",0),null);
        roots.push(platformSetting.ref(true));
        const memorySave=platformSetting.unbox().field("MemorySave").value;
        const inMemory=Memory.alloc(1); inMemory.writeU8(memorySave ? 0 : 1);
        const patch=Il2Cpp.domain.assembly("Shiftup.Patch.Runtime").image
          .class("Shiftup.Patch.Runtime.PatchManager");
        patchTask=invokeChecked(patch.method("InitializeAsync",2),null,[directory.handle,inMemory]);
        roots.push(patchTask.ref(true));
        record({phase:"original_local_patch_session_started",root:directory.content,
          useInMemoryDb:!memorySave,networkMode:"deny_all"});
      } catch (error) { fail("table_error",error); }
    });
  },100);
}, "free").catch(error => record({phase:"bridge_error",error:String(error),stack:error.stack}));

// The bundled bridge's early initialize() waits only on il2cpp_init. This
// player can initialize through another entry point. Observe actual corlib
// availability first, then let the bridge attach to the initialized domain.
let splashGate = null, waitingLogged = false;
function ensureSplashGate(module) {
    if (splashGate) return;
    splashGate = new NativeCallback(function (self, method) {
      record({phase:"normal_app_start_parked",method:"SplashSceneControl.Start"});
    },"void",["pointer","pointer"]);
    // Exact installed client; native-player host binds the DLL SHA before run.
    Interceptor.replace(module.base.add(0x06559260),splashGate);
    record({phase:"normal_app_start_gate_installed",rva:"0x06559260"});
}
const readinessStarted = Date.now();
const readyInterval = setInterval(() => {
  try {
  const module = Process.findModuleByName("GameAssembly.dll");
  if (module) {
    ensureSplashGate(module);
    const corlib = new NativeFunction(module.getExportByName("il2cpp_get_corlib"),"pointer",[])();
    if (!corlib.isNull()) {
      clearInterval(readyInterval);
      record({phase:"original_corlib_available"});
      startManagedProbe();
      return;
    }
  }
  if (!waitingLogged) {
    waitingLogged=true;
    record({phase:"await_original_corlib",gameAssemblyPresent:!!module});
  }
  if (Date.now()-readinessStarted>20000) {
    clearInterval(readyInterval);
    record({phase:"bridge_error",error:"Original corlib unavailable after 20 seconds"});
  }
  } catch (error) {
    clearInterval(readyInterval);
    record({phase:"bridge_error",error:String(error),stack:error.stack});
  }
},50);
record({phase:"headless_driver_ready",fridaVersion:Frida.version,
  readinessCheck:"actual_il2cpp_get_corlib"});
