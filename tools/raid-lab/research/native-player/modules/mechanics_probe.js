// Called once on Unity's main thread after original tables load. This creates
// a synthetic Intercept fixture to diagnose the original lifecycle.
// The full fixture attempts original headless battle ticks and captures only
// original terminal results. It never loads a scene or submits account data.
// Required driver globals: Il2Cpp, invokeChecked(method, instance, argPointers),
// intArg(number), record(row). The driver calls runMechanicsLifecycleProbe.
function runMechanicsLifecycleProbe(record, done, originalManagerLifecycle=false) {
  const roots = [];
  let stage = "lookup";
  let finished = false;
  let originalSpawnEvents=0;
  let monsterBoundary=null;
  let spawnObserver=null;
  let fxCleanupParent=null;
  let audioBoundary=null;
  let damageTrace=null;
  let rangeTrace=null;
  let projectileObserver=null;
  let skillEventObserver=null;
  let skillGateObserver=null;
  let tacticalObserver=null;
  let threatObserver=null;
  let tacticalController=null;
  const controlMode=globalThis.MECHANICS_CONTROL_MODE || "original";
  const diagnostics=globalThis.MECHANICS_TRACE_MODE!=="results";
  const emit = row => record({ phase: "mechanics_lifecycle_probe",
    fixture: globalThis.MECHANICS_ENCOUNTER_PROFILE?"diagnostic_registered_intercept":
      originalManagerLifecycle ? "synthetic_five_unit_kraken_intercept" :
      "synthetic_empty_team_intercept_TDD", completeBattle: false,
    ...(globalThis.MECHANICS_ENCOUNTER_PROFILE?{
      encounterProfileId:globalThis.MECHANICS_ENCOUNTER_PROFILE.productId}:{}),
    ...row });
  const present = value => value != null && !value.isNull();
  const pin = value => {
    if (present(value)) roots.push(value.ref(true));
    return value;
  };
  const floatArg = value => {
    const buffer = Memory.alloc(4);
    buffer.writeFloat(value);
    return buffer;
  };
  const boolArg = value => {
    const buffer = Memory.alloc(1);
    buffer.writeU8(value ? 1 : 0);
    return buffer;
  };
  const number = value => typeof value === "number"
    ? value : Number(value.field("value__").value);
  const call = (method, instance = null, args = []) =>
    invokeChecked(method, instance, args);
  const checkedBool = (method, instance) =>
    !!call(method, instance).unbox().handle.readU8();
  const checkedInt = (method, instance) =>
    call(method, instance).unbox().handle.readS32();
  const count = object => checkedInt(object.method("get_Count", 0), object);
  const typeName = object => object.class.type.name;

  function finish(status, detail = {}) {
    if (finished) return;
    finished = true;
    emit({ status, stage, retainedRootCount: roots.length,
      rootsRetainedUntilProcessExit: true,
      traceMode:diagnostics ? "diagnostics" : "results",
      monsterHeadlessBoundary:monsterBoundary ? monsterBoundary.snapshot() : null,
      originalSpawnObserver:spawnObserver ? spawnObserver.snapshot() : null,
      fxCleanupParent:fxCleanupParent ? fxCleanupParent.snapshot() : null,
      audioBoundary:audioBoundary ? audioBoundary.snapshot() : null,
      damageTraceRecords:damageTrace ? damageTrace.getRecordCount() : null,
      rangeTraceRecords:rangeTrace ? rangeTrace.getRecordCount() : null,
      projectileOccurrence:projectileObserver ? projectileObserver.snapshot() : null,
      skillEventOccurrence:skillEventObserver ? skillEventObserver.snapshot() : null,
      skillTimelineGate:skillGateObserver ? skillGateObserver.snapshot() : null,
      tacticalObservation:tacticalObserver ? tacticalObserver.summary() : null,
      threatObservation:threatObserver ? threatObserver.summary() : null,
      tacticalControl:tacticalController ? tacticalController.summary() : null,
      ...detail });
    done();
  }
  function fail(error) {
    emit({ status: "first_failure", stage, error: String(error),
      nativeFrames: error.nativeFrames || [],
      stack: error && error.stack ? String(error.stack) : null });
    finish("stopped_on_first_failure");
  }
  function contextValues(dictionary, expected) {
    const values = dictionary.method("get_Values", 0).invoke();
    const iterator = values.method("GetEnumerator", 0).invoke();
    const objects = [];
    for (let index = 0; index <= expected; index++) {
      if (!iterator.method("MoveNext", 0).invoke()) break;
      if (index === expected) throw new Error("Context enumeration exceeds Count");
      const context = pin(iterator.method("get_Current", 0).invoke());
      if (!present(context)) throw new Error("Null context at index " + index);
      objects.push(context);
    }
    if (objects.length !== expected) {
      throw new Error("Context enumeration/count mismatch: " +
        objects.length + "/" + expected);
    }
    return objects;
  }

  try {
    const runtime = Il2Cpp.domain.assembly("NK.Runtime").image;
    if (!["original","observe","probe","kraken-qte","kraken-cover-probe","kraken-tactical","boss-observe","boss-tactical"].includes(controlMode))
      throw new Error("Unsupported native control mode: "+controlMode);
    emit({status:"native_control_mode_selected",controlMode,
      policyVersion:controlMode.startsWith("boss-")?"boss-tactical-v1":controlMode==="kraken-tactical" ? "kraken-tactical-v2" :
        controlMode==="kraken-cover-probe" ? "kraken-cover-probe-v1" :
        controlMode==="kraken-qte" ? "kraken-qte-v2" :
        controlMode==="probe" ? "native-input-proof-v1" : "original-auto-v1",
      observesNativeState:controlMode!=="original",issuesTacticalCommands:["probe","kraken-qte","kraken-cover-probe","kraken-tactical","boss-tactical"].includes(controlMode),
      productionSearchIntegrated:false});
    const staticImage = Il2Cpp.domain.assembly("NK.Runtime.StaticData").image;
    if (originalManagerLifecycle) {
      stage="original_battle_settings";
      initializeOriginalMechanicsSettings(runtime,pin,emit);
      stage="headless_audio_boundary";
      audioBoundary=installMechanicsAudioBoundary(emit);
      stage="monster_color_boundary";
      monsterBoundary=installMechanicsMonsterHeadless(row=>{
        emit(row);
        if (row.status==="monster_headless_boundary_fault" && !firstAsyncFault)
          firstAsyncFault={error:row.where+": "+row.error,nativeFrames:[]};
      });
      spawnObserver=installMechanicsSpawnObserver(emit);
    }
    const managementClass = runtime.class("NK.Spot.SpotManagement");
    if (originalManagerLifecycle) {
      const spawnEventType=runtime.class("NK.Spot.Event.Wave.SpawnMonsterEvent").handle;
      Interceptor.attach(managementClass.method("SendEventDefault",1).virtualAddress,{
        onEnter(args) {
          if (args[1].isNull()) return;
          if (damageTrace || tacticalObserver) {
            try {
              const event=new Il2Cpp.Object(args[1]);
              if (damageTrace) damageTrace.observeSendEvent(event);
              if (rangeTrace) rangeTrace.observeSendEvent(event);
              if (skillEventObserver) skillEventObserver.observeSendEvent(event);
              if (skillGateObserver) skillGateObserver.observeSendEvent(event);
              if (tacticalObserver) tacticalObserver.observeSendEvent(event);
              if (threatObserver) threatObserver.observeSendEvent(event);
            }
            catch(error) {
              if (!firstAsyncFault) firstAsyncFault={error:String(error),nativeFrames:[]};
              emit({status:"first_failure",stage:"native_damage_trace",error:String(error)});
            }
          }
          if (args[1].readPointer().equals(spawnEventType)) {
            if (originalSpawnEvents===0) {
              try { spawnObserver.arm(); }
              catch(error) {
                if (!firstAsyncFault) firstAsyncFault={error:String(error),nativeFrames:[]};
                emit({status:"first_failure",stage:"spawn_observer_arm",error:String(error)});
              }
            }
            originalSpawnEvents++;
            if (originalSpawnEvents<=5) emit({status:"original_spawn_event_dispatched",
              count:originalSpawnEvents});
          }
        }
      });
    }
    if (present(managementClass.field("_instance").value)) {
      throw new Error("SpotManagement singleton already exists; fresh process required");
    }
    const management = pin(managementClass.alloc());
    call(management.method(".ctor", 0), management);
    call(management.method("Init", 0), management);
    managementClass.field("_instance").value = management;
    const singleton = call(managementClass.method("get_Instance", 0));
    if (!present(singleton) || !singleton.handle.equals(management.handle)) {
      throw new Error("Original SpotManagement singleton did not retain root");
    }
    call(management.method("InitSpotEvent", 0), management);
    if (originalManagerLifecycle && diagnostics) {
      damageTrace=installMechanicsDamageTrace(runtime,management,emit);
      rangeTrace=installMechanicsRangeTrace(runtime,management,emit);
      projectileObserver=installMechanicsProjectileObserver(runtime,management,emit);
      skillEventObserver=installMechanicsSkillEventObserver(runtime,management,emit);
      skillGateObserver=installMechanicsSkillGateObserver(runtime,management,emit);
    }

    stage = "original_dispatcher";
    const dispatcherType = managementClass.field("_onSendEventAction").type.object;
    const dispatcherMethod = managementClass.method("SendEventDefault", 1).object;
    if (!present(dispatcherType) || !present(dispatcherMethod)) {
      throw new Error("Original PvE dispatcher reflection objects unavailable");
    }
    const createDelegate = Il2Cpp.corlib.class("System.Delegate")
      .method("CreateDelegate").overload("System.Type", "System.Object",
        "System.Reflection.MethodInfo");
    const dispatch = pin(call(createDelegate, null,
      [dispatcherType.handle, management.handle, dispatcherMethod.handle]));
    if (!present(dispatch)) throw new Error("Original dispatcher creation returned null");
    management.field("_onSendEventAction").value = dispatch;
    if (!present(management.field("_onSendEventAction").value)) {
      throw new Error("Original dispatcher was not retained");
    }

    stage = originalManagerLifecycle ? "synthetic_kraken_fixture" : "synthetic_empty_fixture";
    let teamData = null, teamCount = 0;
    const transporterClass = runtime.class("NK.Spot.Data.NKSpotDataTransporter");
    const size = transporterClass.valueTypeSize;
    if (size < 360 || size > 1024) {
      throw new Error("Unexpected NKSpotDataTransporter size " + size);
    }
    let transporterBox;
    if (originalManagerLifecycle) {
      transporterBox = prepareMechanicsFixture(runtime, staticImage, pin, emit);
      teamCount = 5;
    } else {
    const teamClass = runtime.class("NK.Spot.Common.SpotTeamData");
    teamData = pin(teamClass.alloc());
    call(teamData.method(".ctor", 0), teamData);
    const teamList = call(teamData.method("get_CharacterDataList", 0), teamData);
    teamCount = count(teamList);
    if (teamCount !== 0) throw new Error("Synthetic team must be empty");
    transporterBox = pin(transporterClass.alloc());
    const transporter = transporterBox.unbox();
    transporter.field("MyTeamData").value = teamData;
    if (!present(transporter.field("MyTeamData").value)) {
      throw new Error("Transporter did not retain empty team");
    }
    const managementType = runtime.class("NK.Spot.Common.CommonEnum")
      .nested("ManagementType").field("SinglePlay").value;
    call(transporter.method("set_ManagementType", 1), transporter,
      [intArg(number(managementType))]);
    call(transporter.method("set_ProcessType", 1), transporter, [intArg(7)]);
    call(transporter.method("set_TimeLimit", 1), transporter, [floatArg(180)]);
    call(transporter.method("set_RandomSeed", 1), transporter, [intArg(1)]);
    call(transporter.method("set_TDDProcess", 1), transporter, [boolArg(true)]);
    call(transporter.method("set_IsAuto", 1), transporter, [boolArg(true)]);
    }
    if (!originalManagerLifecycle) {
      const randomClass = runtime.class("NK.Spot.Common.SpotRandom");
      call(randomClass.method("Generate", 1), null, [intArg(1)]);
    }
    // The installed bridge's static value-type getter allocates only a pointer-
    // sized buffer. Copy the full unboxed struct through the native setter and
    // never read it back via Field.value.
    const assembly = Process.getModuleByName("GameAssembly.dll");
    const setStatic = new NativeFunction(assembly.getExportByName(
      "il2cpp_field_static_set_value"), "void", ["pointer", "pointer"]);
    setStatic(managementClass.field("DataTransporter").handle,
      transporterBox.unbox().handle);
    const requestedSeed=originalManagerLifecycle ? globalThis.MECHANICS_REQUEST.encounter.randomSeed : 1;
    emit({ status: "synthetic_fixture_ready", teamCount, seed: requestedSeed,
      requestSha256:originalManagerLifecycle ? globalThis.MECHANICS_REQUEST_SHA256 : null,
      timeLimit: 180, tddProcess: !originalManagerLifecycle, isAuto: true,
      transporterValueTypeSize: size, accountDataUsed: false });

    // Original SpotLoader installs/selects mode from DataTransporter before
    // creating process contexts. CreateContext also reads UseOverclock.
    stage = "original_intercept_context";
    const intercept = staticImage.class("NK.StaticData.SpotModType")
      .field("Intercept").value;
    if (number(intercept) !== 7) throw new Error("Installed Intercept enum is not 7");
    const processClass = runtime.class("NK.Spot.Context.Process.InterceptProcess");
    const process = pin(processClass.alloc());
    call(process.method(".ctor", 1), process, [intArg(7)]);
    call(management.method("SetProcess", 1), management, [process.handle]);
    if (!present(management.field("_process").value)) {
      throw new Error("SetProcess did not retain original InterceptProcess");
    }
    call(process.method("CreateContext", 0), process);
    const router = pin(management.field("_spotLogicRouter").value);
    if (!present(router)) throw new Error("SpotLogicRouter is missing");
    call(router.method("OnInit", 0), router);

    if (originalManagerLifecycle) {
      // Original presentation initialization precedes management.OnInit, which
      // registers event observers and builds the original combined tick lists.
      stage="original_geometry_initialization";
      startMechanicsGeometryRuntime(management,pin,emit,(geometryError,geometryState)=>{
      if (finished) return;
      if (geometryError) { fail(geometryError); return; }
      try {
      stage="original_fx_cleanup_parent";
      fxCleanupParent=installMechanicsFxCleanupParent(geometryState,pin,row=>{
        emit(row);
        if (row.status==="mechanics_fx_cleanup_parent_fault" && !firstAsyncFault)
          firstAsyncFault={error:row.error,nativeFrames:[]};
      });
      stage="original_management_on_init";
      call(management.method("OnInit",0),management);
      const random=runtime.class("NK.Spot.Common.SpotRandom").field("_shared").value;
      const seed=Number(management.field("<SpotRandomSeed>k__BackingField").value);
      if (!present(random) || seed!==requestedSeed || Number(random.field("_currSeed").value)!==requestedSeed)
        throw new Error("Original OnInit did not apply the requested seed to both mechanical RNG fields");
      emit({status:"original_rng_initialized",managerSeed:seed,
        sharedSeed:Number(random.field("_currSeed").value),
        drawCount:random.field("<DrawCount>k__BackingField").value.toString()});
      emit({status:"original_management_on_init_returned",
        processState:checkedInt(process.method("get_State",0),process),
        presentationCount:count(management.field("_presentations").value)});
      const started=Date.now();
      let loadedTeam=null;
      const poll=setInterval(()=>onMain(()=>{
        if (finished) { clearInterval(poll); return; }
        try {
          monsterBoundary.check();
          spawnObserver.check();
          fxCleanupParent.check();
          if (firstAsyncFault) {
            clearInterval(poll);
            const error=new Error(firstAsyncFault.error);
            error.nativeFrames=firstAsyncFault.nativeFrames;
            fail(error);
            return;
          }
          const state=checkedInt(process.method("get_State",0),process);
          if (Date.now()-started>15000) {
            clearInterval(poll);
            stage="original_load_pending";
            finish("original_load_did_not_complete",{processState:state,
              pendingReason:geometryState.pendingReason || null});
            return;
          }
          if (state===2) {
            stage="original_loaded_aim_binding";
            if (!loadedTeam) {
            loadedTeam=pin(call(process.method("get_MyTeam",0),process));
            const teamState={status:"original_loaded_team_state",processState:state};
            for (const name of ["<CharacterList>k__BackingField",
              "<CoverList>k__BackingField", "<PreSpawnCharacterList>k__BackingField"]) {
              const value=loadedTeam.field(name).value;
              teamState[name]=present(value) ? count(value) : null;
            }
            teamState.focusedCharacterPresent=present(loadedTeam.field("_focusedCharacter").value);
            teamState.autoAim=loadedTeam.field("_isAutoModeAim").value;
            teamState.autoBurst=loadedTeam.field("_isAutoModeSkill").value;
            emit(teamState);
            }
            const geometry=finishMechanicsGeometryRuntime(geometryState,
              management,loadedTeam,pin,emit);
            if (geometry===null) return;
            clearInterval(poll);
            const unity=Il2Cpp.domain.assembly("UnityEngine.CoreModule").image;
            const aimBinding=prepareMechanicsAimBinding(runtime,unity,management,
              loadedTeam,geometry,pin,emit);
            for (const actor of geometry.live.actors) {
              const info=actor.entity.field("<CharacterStaticInfo>k__BackingField").value;
              const nameCode=checkedInt(info.method("get_NameCode",0),info);
              if (actor.entityId!==mechanicsRequestedEntityId(nameCode))
                throw new Error("Original entity identity does not match requested slot: " + nameCode);
              emit({status:"original_aim_state",entityId:actor.entityId,
                nameCode,requestSha256:globalThis.MECHANICS_REQUEST_SHA256,
                native:aimBinding.getNativeAimState(actor.entityId)});
            }
            // Explicit unattended input, after DataContext's initial saved-
            // preferences event. Keep original event dispatch and aim logic.
            const autoEvent=runtime.class("NK.Spot.Event.Data.ChangeAutoModeEvent");
            const autoType=runtime.class("NK.Spot.Event.Data.SpotAutoType");
            for (const name of ["Aim","Skill"]) {
              call(autoEvent.method("Send",2),null,
                [intArg(number(autoType.field(name).value)),boolArg(true)]);
            }
            const autoAim=checkedBool(loadedTeam.method("get_IsAutoModeAim",0),loadedTeam);
            const autoBurst=checkedBool(loadedTeam.method("get_IsAutoModeSkill",0),loadedTeam);
            if (!autoAim || !autoBurst) throw new Error("Original auto input did not reach team");
            emit({status:"original_auto_input_applied",autoAim,autoBurst,
              event:"ChangeAutoModeEvent.Send",eventRva:"0x0644B7E0"});
            if (controlMode!=="original") {
              stage="native_tactical_binding";
              const generic=controlMode.startsWith("boss-");
              tacticalObserver=createMechanicsTacticalObserver(runtime,management,loadedTeam,pin,emit,generic);
              const watchNodes=generic?mechanicsVerifiedCoverRules()
                .filter(r=>r.waveId===globalThis.MECHANICS_REQUEST.encounter.waveId)
                .map(r=>r.attackNodeId):[];
              threatObserver=createMechanicsThreatObserver(runtime,management,emit,
                generic?{mode:"monster",watchAttackNodes:watchNodes}:undefined);
              const actions=!["observe","boss-observe"].includes(controlMode) ? createMechanicsTacticalActions(
                runtime,management,loadedTeam,geometry,aimBinding,pin,emit) : null;
              tacticalController=createMechanicsTacticalController(controlMode,management,
                tacticalObserver,actions,geometry.live.actors,emit,threatObserver);
            }
            stage="original_battle_ticks";
            const captureTerminal=installMechanicsResultCapture(runtime,
              loadedTeam,pin,emit);
            const monsterType=runtime.class("NK.Spot.Context.Monster.MonsterContext");
            const contexts=management.field("_contexts").value;
            const monsters=pin(call(contexts.method("get_Item",1),contexts,
              [monsterType.type.object.handle]));
            if (!present(monsters)) throw new Error("Original MonsterContext is absent");
            const waveType=runtime.class("NK.Spot.Context.Wave.WaveContext");
            const wave=pin(call(contexts.method("get_Item",1),contexts,
              [waveType.type.object.handle]));
            if (!present(wave)) throw new Error("Original WaveContext is absent");
            const currentWave=wave.field("_waveDataRecord").value;
            if (!present(currentWave)) throw new Error("Original current wave row is null");
            const targetIds=call(currentWave.method("get_TargetList",0),currentWave);
            const currentTargets=[];
            for (let i=0;i<count(targetIds);i++) {
              if (i>=32) throw new Error("Unexpected fixture target list size");
              currentTargets.push(call(targetIds.method("get_Item",1),targetIds,
                [intArg(i)]).unbox().handle.readS64().toString());
            }
            emit({status:"original_current_wave_targets",targetIds:currentTargets});
            const sampleEncounter=sample=>{
              spawnObserver.check();
              const detail={status:"original_encounter_sample",...sample,
                originalSpawnEvents,
                targetMonsterPresent:present(monsters.field("_targetMonster").value)};
              for (const name of ["_monsters","_allMonsters","_allMonsterParts","_aimPointsAll"]) {
                const list=monsters.field(name).value;
                detail[name]=present(list) ? count(list) : null;
              }
              detail.wave={};
              for (const name of ["WaveBundlesV2","WaveBundlesRepeat"]) {
                const list=wave.field(name).value;
                detail.wave[name]=present(list) ? count(list) : null;
              }
              for (const name of ["AllTargetCount","CurrentMonsterGroup","MonsterLiveCount"])
                detail.wave[name]=Number(wave.field("<"+name+">k__BackingField").value);
              const pendingWave=process.field("_waveDataList").value;
              detail.wave.pendingEntries=present(pendingWave) ? count(pendingWave) : null;
              detail.firstActorAim=aimBinding.getNativeAimState(geometry.live.actors[0].entityId);
              emit(detail);
            };
            const clockObserver=diagnostics ? createMechanicsClockObserver(runtime,geometryState,
              management,pin,emit) : null;
            const cameraObserver=diagnostics ? createMechanicsCameraObserver(runtime,management,
              aimBinding,pin,emit) : null;
            const startupObserver=diagnostics ? createMechanicsStartupStateObserver(runtime,
              management,loadedTeam,geometry,pin,emit) : null;
            startOriginalMechanicsTicks(runtime,management,process,emit,
              ()=>finish("original_tick_driver_stopped"),captureTerminal,
              {onSample:diagnostics ? sampleEncounter : undefined,batchSize:1,maxWallMs:35000,
                beforeTick:diagnostics || tacticalController ? tick=>{
                  if (tacticalController) tacticalController.beforeTick(tick);
                  if (!diagnostics) return;
                  if (tick<20) startupObserver.sample(tick,"before");
                  clockObserver.sample("before",tick+1);
                  cameraObserver.sample("before",tick+1);
                } : undefined,
                afterTick:diagnostics || tacticalController ? tick=>{
                  if (tacticalController) tacticalController.afterTick(tick);
                  if (!diagnostics) return;
                  if (tick<=20) startupObserver.sample(tick,"after");
                  clockObserver.sample("after",tick);
                  cameraObserver.sample("after",tick);
                  rangeTrace.checkFault();
                  projectileObserver.checkFault();
                  skillEventObserver.checkFault();
                  if (skillGateObserver) skillGateObserver.checkFault();
                } : undefined,
                schedule:createMechanicsFrameScheduler(pin,emit,
                  globalThis.MECHANICS_WALL_FRAME_RATE)});
          }
        } catch(error) { clearInterval(poll); fail(error); }
      }),100);
      } catch(error) { fail(error); }
      });
      return;
    }

    stage = "process_on_init";
    call(process.method("OnInit", 0), process);
    const stateAfterInit = checkedInt(process.method("get_State", 0), process);
    if (stateAfterInit !== 1) {
      throw new Error("Original process OnInit state " + stateAfterInit + " != 1");
    }
    const team = pin(call(process.method("get_MyTeam", 0), process));
    if (!present(team)) throw new Error("Original process has no MyTeam context");
    const camp = runtime.class("NK.Spot.Model.Character.SpotCharacter")
      .nested("CampType").field("Red").value;
    stage = "team_data_on_init";
    call(team.method("OnInit", 2), team,
      [teamData.handle, intArg(number(camp))]);
    // Character fixture evidence shows these original TeamContext fields are
    // initialized by character construction before the zero-argument OnInit.
    // Here there are no characters, so construct only the original typed lists.
    for (const fieldName of ["<CharacterList>k__BackingField",
      "<CoverList>k__BackingField"]) {
      const field = team.field(fieldName);
      if (!present(field.value)) {
        const list = pin(field.type.class.alloc());
        call(list.method(".ctor", 0), list);
        field.value = list;
      }
    }
    const functionContext = pin(call(runtime.class("NK.Spot.Context.FunctionContext")
      .method("get_Instance", 0)));
    if (!present(functionContext)) throw new Error("FunctionContext.Instance missing");
    stage = "function_context_on_init";
    call(functionContext.method("OnInit", 0), functionContext);

    stage = "remaining_contexts_on_init";
    const contexts = pin(management.field("_contexts").value);
    const presentations = pin(management.field("_presentations").value);
    if (!present(contexts) || !present(presentations)) {
      throw new Error("Original context/presentation dictionary missing");
    }
    const contextCount = count(contexts);
    const presentationCount = count(presentations);
    if (contextCount !== 16 || presentationCount !== 0) {
      throw new Error("Expected 16 contexts and zero presentations; got " +
        contextCount + "/" + presentationCount);
    }
    if (!checkedBool(management.method("IsResourceLoad", 0), management)) {
      throw new Error("Original empty-presentation resource gate is false");
    }
    const actualContexts = contextValues(contexts, contextCount);
    const contextClasses = actualContexts.map(typeName);
    emit({ status: "original_contexts_enumerated", contextClasses,
      contextCount, presentationCount, processState: stateAfterInit });
    for (const context of actualContexts) {
      const name = typeName(context);
      if (context.handle.equals(functionContext.handle)) {
        emit({ status: "context_on_init_already_called", context: name });
        continue;
      }
      stage = "context_on_init:" + name;
      call(context.method("OnInit", 0), context);
      emit({ status: "context_on_init_returned", context: name });
    }

    stage = "tick_coroutine_init";
    const externalTicks = pin(management.field("_ticks").value);
    if (!present(externalTicks)) throw new Error("Original external ITick list absent");
    // OnInit gives the coroutine runner a NEW combined list. _ticks remains
    // the separately registered list; adding contexts there would tick twice.
    const listClass = managementClass.field("_ticks").type.class;
    const ticks = pin(listClass.alloc());
    call(ticks.method(".ctor",0),ticks);
    const addTick = ticks.method("Add", 1);
    for (const context of actualContexts) {
      call(addTick, ticks, [context.handle]);
    }
    call(addTick, ticks, [process.handle]);
    if (count(ticks) !== contextCount + 1) {
      throw new Error("Original tick list count mismatch");
    }
    const tickRunner = runtime.class("NK.Spot.Util.TickCoroutineRunner");
    call(tickRunner.method("Init", 1), null, [ticks.handle]);

    stage = "valid_tick_lists";
    const valid = pin(management.field("_validDic").value);
    if (!present(valid) || count(valid) !== 0) {
      throw new Error("Original valid-tick dictionary absent or nonempty");
    }
    for (const [key, capacity] of [[0, contextCount], [1, presentationCount],
      [2, count(externalTicks)]]) {
      const list = pin(listClass.alloc());
      call(list.method(".ctor", 1), list, [intArg(capacity)]);
      call(valid.method("Add", 2), valid, [intArg(key), list.handle]);
    }
    if (count(valid) !== 3) throw new Error("Valid-tick dictionary count != 3");
    emit({ status: "original_tick_infrastructure_ready", tickCount: count(ticks),
      validKeys: [0, 1, 2], presentationCount });

    stage = "process_on_load";
    call(process.method("OnLoad", 0), process);
    const stateAfterLoad = checkedInt(process.method("get_State", 0), process);
    if (stateAfterLoad !== 2) {
      throw new Error("Original OnLoad state " + stateAfterLoad + " != 2");
    }
    emit({ status: "original_process_on_load_returned", processState: stateAfterLoad });

    stage = "first_update_spot";
    const before = Number(management.field("_tickCount").value);
    call(management.method("UpdateSpot", 1), management,
      [floatArg(1 / 30)]);
    const after = Number(management.field("_tickCount").value);
    const finalState = checkedInt(process.method("get_State", 0), process);
    emit({ status: "original_first_tick_returned", tickBefore: before,
      tickAfter: after, processState: finalState,
      resourceLoaded: checkedBool(management.method("IsResourceLoad", 0),
        management), battleStarted: false, resultCaptured: false });
    finish("lifecycle_tick_diagnostic_complete");
  } catch (error) {
    fail(error);
  }
}
