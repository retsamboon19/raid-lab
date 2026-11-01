// Current153 private original-engine integration. Not production Raid Lab.
// Native controls own all battle state; fixture expectations are readback-only.
function createOriginalPracticeManagement(runtime,pin,emit) {
  const cls=runtime.class('NK.Spot.SpotManagement');
  const call=(method,self=null,args=[])=>invokeChecked(method,self,args);
  const live=value=>value!=null&&!value.isNull();
  const method=(name,count,rva)=>{
    const value=cls.method(name,count);
    if (Number(value.relativeVirtualAddress)!==rva)
      throw new Error('Current153 management method changed: '+name);
    return value;
  };
  if (live(cls.field('_instance').value))
    throw new Error('Practice requires a fresh original management singleton');
  const manager=pin(cls.alloc());
  call(method('.ctor',0,0x07608470),manager);
  call(method('Init',0,0x07604590),manager);
  cls.field('_instance').value=manager;
  if (!call(method('get_Instance',0,0x07608880)).handle.equals(manager.handle))
    throw new Error('Original practice management singleton readback differs');
  call(method('InitSpotEvent',0,0x07604260),manager);
  const originalDispatch=method('SendEventDefault',1,0x076071f0);
  const delegateType=cls.field('_onSendEventAction').type.object;
  const make=Il2Cpp.corlib.class('System.Delegate').method('CreateDelegate').overload(
    'System.Type','System.Object','System.Reflection.MethodInfo');
  const dispatcher=pin(call(make,null,[delegateType.handle,manager.handle,originalDispatch.object.handle]));
  manager.field('_onSendEventAction').value=dispatcher;
  if (!manager.field('_onSendEventAction').value.handle.equals(dispatcher.handle))
    throw new Error('Original practice dispatcher readback differs');
  emit({status:'original_practice_management_created',
    originalDispatcherBound:true,combatStarted:false,privateHostOnly:true});
  return manager;
}

function installCapturedPracticeTransporter(runtime,fixture,emit) {
  if (!fixture?.passed || !fixture.transporterBox || fixture.transporterBox.class.valueTypeSize!==376)
    throw new Error('Original complete fixture readback required before static install');
  const cls=runtime.class('NK.Spot.SpotManagement'),field=cls.field('DataTransporter');
  if (!field.isStatic || field.type.name!=='NK.Spot.Data.NKSpotDataTransporter' ||
      field.type.class.valueTypeSize!==376)
    throw new Error('Current153 static transporter ABI changed');
  const game=Process.getModuleByName('GameAssembly.dll');
  const setter=new NativeFunction(game.getExportByName('il2cpp_field_static_set_value'),
    'void',['pointer','pointer']);
  const getter=new NativeFunction(game.getExportByName('il2cpp_field_static_get_value'),
    'void',['pointer','pointer']);
  const original=fixture.transporterBox.unbox().handle;
  const readback=Memory.alloc(376);
  setter(field.handle,original);
  getter(field.handle,readback);
  const before=new Uint8Array(original.readByteArray(376));
  const after=new Uint8Array(readback.readByteArray(376));
  if (before.some((byte,index)=>byte!==after[index]))
    throw new Error('Full current153 static transporter copy readback differs');
  emit({status:'captured_practice_static_transporter_installed',valueTypeSize:376,
    allBytesReadBack:true,capturedSemanticFieldsChecked:fixture.fieldChecks.length,
    transporterExactReplay:fixture.transporterExactReplay,
    callbackBehaviorOriginal:fixture.callbackBehaviorOriginal,
    combatStateWritten:false,combatStarted:false});
  // Retain this sized native buffer until process exit; never use Field.value.
  fixture.rawBuffers.push(readback);
}

// Team/transporter construction is verified separately before this integration
// entry is enabled. Geometry and original loading/start lifecycle are next.
function prepareOriginalPracticeContext(runtime,staticImage,pin,emit,fixture,modeInput) {
  validateNative153PracticeInput(modeInput);
  if (!fixture.passed) throw new Error('Captured practice fixture did not pass');
  const manager=createOriginalPracticeManagement(runtime,pin,emit);
  installCapturedPracticeTransporter(runtime,fixture,emit);
  const process=createOriginal153PracticeProcess(runtime,staticImage,manager,pin,emit,
    modeInput,fixture.readback);
  const router=pin(manager.field('_spotLogicRouter').value);
  if (!router || router.isNull()) throw new Error('Original practice logic router absent');
  invokeChecked(router.method('OnInit',0),router);
  return {manager,process,router,fixture,modeInput};
}

function runOriginalPracticeProbe(record,done) {
  const retained=[],listeners=[];
  let finished=false,stage='captured_inputs',poll=null,ticks=null;
  let callbacks=null,monsterBoundary=null,audioBoundary=null,fxBoundary=null;
  let skillPoolObserver=null;
  let skeletonSourceObserver=null;
  let dpReady=false;
  let colorReadiness=null,colorReadinessSamples=0;
  let autoPreferences=null,autoContentsAtPlaying=null;
  let rngStateVerifier=null;
  let loadingOverlay=null;
  const active={retained,listeners,boundaries:[]};
  let originalActors=null,geometry=null,aimBinding=null,capture=null;
  let originalAutoControlsVerified=false;
  let originalRngStateVerified=false;
  const emit=row=>record({phase:'original153_practice_probe',fullAccuracyVerified:false,...row});
  const live=value=>value!=null&&!value.isNull();
  const pin=value=>{if(!live(value))throw new Error('Required practice reference absent');retained.push(value.ref(true));return value;};
  const call=(method,self=null,args=[])=>invokeChecked(method,self,args);
  const integer=(object,name)=>call(object.method(name,0),object).unbox().handle.readS32();
  function complete(row={}) {
    if(finished)return;
    finished=true;
    if(poll)clearInterval(poll);
    if(row.completeBattle===true) {
      try {
        const filename=globalThis.PRACTICE_RESULT_FILENAME;
        if(typeof filename!=='string'||!/^practice[1-9][0-9]*-original-result\.pb$/.test(filename))
          throw new Error('A fresh private output filename is required');
        const exported=exportOriginalPracticePacket(capture.getOriginalPacket(),pin,emit);
        if(exported.source?.format!=='protobuf_wire'||!(exported.bytes instanceof ArrayBuffer)||
            exported.bytes.byteLength<1||exported.bytes.byteLength>16777216)
          throw new Error('Original binary protobuf export contract differs');
        const output=new File(filename,'wb');
        try {output.write(exported.bytes);output.flush();} finally {output.close();}
        row={...row,originalPacketExported:true,originalPacketFile:filename,
          originalPacketSource:exported.source};
      } catch(error) {
        row={...row,status:'original_practice_packet_export_failed',originalPacketExported:false,
          exportError:String(error),nativeFrames:error?.nativeFrames||[]};
      }
    }
    emit({status:'original_practice_probe_stopped',stage,retainedRootCount:retained.length,
      originalDpCatalogRegistered:dpReady,
      monsterColorReadiness:colorReadiness,monsterColorReadinessSamples:colorReadinessSamples,
      autoPreferenceInput:autoPreferences?.evidence,autoContentsAtPlaying,
      callbackBoundary:callbacks?.snapshot(),monsterBoundary:monsterBoundary?.snapshot(),
      audioBoundary:audioBoundary?.snapshot(),fxBoundary:fxBoundary?.snapshot(),
      skillPoolObserver:skillPoolObserver?.snapshot(),
      fullSharedRngState:rngStateVerifier?.snapshot(),
      originalLoadingOverlay:loadingOverlay?{status:loadingOverlay.status,readyShow:loadingOverlay.readyShow}:null,
      skeletonSourceObserver:skeletonSourceObserver?.snapshot(),...row});
    done();
  }
  function fail(error) {
    const detail={status:'first_failure',stage,error:String(error),nativeFrames:error?.nativeFrames||[],
      stack:error?.stack||null,completeBattle:false};
    if(ticks)ticks.stop('first_failure',detail);else complete(detail);
  }
  function checkFault() {
    if(typeof firstAsyncFault!=='undefined'&&firstAsyncFault) {
      const error=new Error(firstAsyncFault.error);error.nativeFrames=firstAsyncFault.nativeFrames;throw error;
    }
    callbacks?.check();monsterBoundary?.check();fxBoundary?.check();skeletonSourceObserver?.check();rngStateVerifier?.check();loadingOverlay?.check();
  }
  try {
    const runtime=Il2Cpp.domain.assembly('NK.Runtime').image;
    const staticImage=Il2Cpp.domain.assembly('NK.Runtime.StaticData').image;
    const modeInput=globalThis.PRACTICE_MODE_INPUT;
    validateNative153PracticeInput(modeInput);
    initializeCapturedPracticeSettings(runtime,pin,emit);
    stage='original_dp_catalog_registration';
    const dpRegistration=beginOriginalPracticeDpRegistration(pin,emit);
    active.boundaries.push(dpRegistration);
    stage='captured_inputs';
    const replay=runCapturedSnapshotReconstruction(runtime,staticImage,pin,emit,
      globalThis.CAPTURED_REPLAY_INPUT,globalThis.CAPTURED_REPLAY_EXPECTED);
    callbacks=createPracticeHostCallbacks(runtime,pin,emit);
    const waveLoader=createCapturedPracticeWaveResolver(staticImage,pin,emit);
    waveLoader.begin(modeInput.waveId);
    poll=setInterval(()=>onMain(()=>{
      if(finished)return;
      try {
        checkFault();
        if(!dpRegistration.poll().ready){stage='original_dp_catalog_registration';return;}
        dpReady=true;stage='captured_inputs';
        if(!waveLoader.poll().ready)return;
        clearInterval(poll);poll=null;
        const fixture=prepareCapturedPracticeFixture(runtime,staticImage,pin,emit,
          globalThis.CAPTURED_FIXTURE_INPUT,globalThis.CAPTURED_REPLAY_EXPECTED,
          {replay,resolveWaveData:waveLoader.resolve,resolveNativeOwnerField:callbacks.resolveNativeOwnerField});
        if(!fixture.passed)throw new Error('Original captured practice fixture did not pass');
        stage='native_presentation_boundaries';
        audioBoundary=installMechanicsAudioBoundary(emit);
        monsterBoundary=installPracticeMonsterColorObserver(emit);
        active.boundaries.push(callbacks,audioBoundary,monsterBoundary);
        const ctx=prepareOriginalPracticeContext(runtime,staticImage,pin,emit,fixture,modeInput);
        const manager=ctx.manager,process=ctx.process;
        stage='original_auto_preference_inputs';
        autoPreferences=prepareOriginalPracticeAutoPreferences(runtime,pin,emit);
        active.boundaries.push(autoPreferences);
        stage='original_shared_rng_state_guard';
        rngStateVerifier=createOriginalPracticeRngStateVerifier(runtime,
          globalThis.PRACTICE_RNG_EXPECTED,pin,emit,
          {expectedSha256:globalThis.PRACTICE_RNG_EXPECTED_SHA256});
        active.boundaries.push(rngStateVerifier);
        // Resolve the original context before observing native callbacks. The
        // getter returns the existing WaveContext created by CampaignProcess.
        const waveContext=pin(call(native153PracticeMethod(
          runtime.class('NK.Spot.Context.Wave.WaveContext'),'get_Instance',0,0x019598b0)));
        const introDurationField=manager.field('<IntroCutSceneDuration>k__BackingField');
        const introFlagField=waveContext.field('<UseIntroCutScene>k__BackingField');
        const loadingPageField=manager.field('<IsShowLoadingPage>k__BackingField');
        if(waveContext.class.type.name!=='NK.Spot.Context.Wave.WaveContext'||
            introDurationField.offset!==0xb0||introDurationField.type.name!=='System.Single'||introDurationField.isStatic||
            introFlagField.offset!==0x98||introFlagField.type.name!=='System.Boolean'||introFlagField.isStatic||
            loadingPageField.offset!==0xb5||loadingPageField.type.name!=='System.Boolean'||loadingPageField.isStatic)
          throw new Error('Original startup intro field layout differs');
        const introExpected=globalThis.PRACTICE_CUTSCENE_CONTROL_SOURCE;
        if(!introExpected||! /^[a-f0-9]{8}$/.test(introExpected.expectedIntroDurationFloat32BitsLE||'')||
            introExpected.expectedUseIntroCutScene!==true)
          throw new Error('Source-derived original intro expectation is absent');
        const observeIntro=boundaryPhase=>{
          const row={status:'original_practice_intro_state_observed',boundaryPhase,
            sourceReceiptSha256:globalThis.PRACTICE_CUTSCENE_CONTROL_SOURCE_SHA256,
            introDuration:manager.handle.add(0xb0).readFloat(),
            introDurationBitsLE:Array.from(new Uint8Array(manager.handle.add(0xb0).readByteArray(4)),
              value=>value.toString(16).padStart(2,'0')).join(''),
            useIntroCutScene:waveContext.handle.add(0x98).readU8()!==0,
            isShowLoadingPage:manager.handle.add(0xb5).readU8()!==0,
            stateWritten:false,nativeMethodsInvokedInsideObserver:false};
          row.passed=row.introDurationBitsLE===introExpected.expectedIntroDurationFloat32BitsLE&&
            row.useIntroCutScene===introExpected.expectedUseIntroCutScene&&!row.isShowLoadingPage;
          emit(row);
          if(!row.passed)throw new Error('Original intro state differs from the source and actual loading boundary');
        };
        // Retain a passive original OnStart observation, never dispatch it.
        const onStart=native153PracticeMethod(manager.class,'OnStart',0,0x076064c0);
        listeners.push(Interceptor.attach(onStart.virtualAddress,{onEnter(args){
          try {
            this.originalPracticeManager=args[0].equals(manager.handle);
            if(this.originalPracticeManager){
              observeIntro('enter');
              rngStateVerifier.observe('enter');
              emit({status:'original_practice_on_start_observed',
              nativeTick:Number(manager.field('_tickCount').value),
              nativePlayTime:Number(manager.field('_playtime').value),
              nativeDeltaTime:Number(manager.field('_deltaTime').value),manualDispatch:false});
            }
          } catch(error) {
            if(!firstAsyncFault)firstAsyncFault={error:String(error),nativeFrames:error?.nativeFrames||[]};
          }
        },onLeave(){
          if(this.originalPracticeManager){
            try {observeIntro('leave');}
            catch(error){if(!firstAsyncFault)firstAsyncFault={error:String(error),nativeFrames:error?.nativeFrames||[]};}
            rngStateVerifier.observe('leave');
          }
        }}));
        stage='original_geometry_initialization';
        startPracticeGeometryRuntime(manager,pin,emit,(error,geometryState)=>{
          if(finished)return;
          if(error){fail(error);return;}
          stage='original_loading_overlay';
          try {
          const application=Il2Cpp.domain.assembly('UnityEngine.CoreModule').image.class('UnityEngine.Application');
          const overlayFrameRate=call(native153PracticeMethod(application,'get_targetFrameRate',0,0x084D4350))
            .unbox().handle.readS32();
          if(overlayFrameRate!==globalThis.PRACTICE_SETTINGS_INPUT.frameRate||overlayFrameRate!==60)
            throw new Error('Original loading Show target frame rate differs from captured FPS60 preference');
          emit({status:'original_practice_overlay_target_frame_rate_verified',
            targetFrameRate:overlayFrameRate,achievedFrameRateMeasured:false,stateWritten:false});
          loadingOverlay=startOriginalPracticeOverlay(runtime,staticImage,pin,emit,(overlayError,overlayState)=>{
          if(finished)return;
          if(overlayError){fail(overlayError);return;}
          try {
            if(!overlayState?.readyShow)
              throw new Error('Original loading overlay Show did not complete');
            checkFault();
            // Check original getter bytes before the pool observer attaches.
            // Both passive observers precede the original OnInit loading chain.
            fxBoundary=installPracticeFxCleanupObserver(geometryState,pin,emit);
            active.boundaries.push(fxBoundary);
            skillPoolObserver=installPracticeSkillPoolObserver(emit);
            active.boundaries.push(skillPoolObserver);
            skeletonSourceObserver=installPracticeSkeletonSourceObserver(emit);
            active.boundaries.push(skeletonSourceObserver);
            stage='original_on_init';
            // This original entry launches OnLoad itself. The original loading
            // coroutines, not this adapter, invoke OnPostLoad and OnStart.
            call(native153PracticeMethod(manager.class,'OnInit',0,0x07605610),manager);
            const loadingPageAtInit=manager.handle.add(0xb5).readU8()!==0;
            emit({status:'original_practice_loading_page_initialized',
              isShowLoadingPage:loadingPageAtInit,afterOriginalOnInit:true,
              loadingFlagWrittenByHost:false});
            if(!loadingPageAtInit)
              throw new Error('Original popup controller did not retain the active loading page after OnInit');
            const dayNight=pin(geometryState.graphicOptions.field('<DayNight>k__BackingField').value);
            const originalEnv=call(dayNight.method('get_GradientController',0),dayNight);
            if (!live(originalEnv)||!originalEnv.handle.equals(geometryState.envGradient.handle))
              throw new Error('Original DayNight did not retain the serialized environment controller');
            emit({status:'original_graphic_options_on_init_verified',
              dayNightType:dayNight.class.type.name,originalEnvironmentIdentityPreserved:true,
              dayNightOrEnvironmentWritten:false});
            const team=pin(call(process.method('get_MyTeam',0),process));
            const resourceGate=native153PracticeMethod(manager.class,'IsResourceLoad',0,0x07604650);
            stage='original_loading_and_updates';
            function observeColorReadiness() {
              if(!geometry||colorReadiness?.ready||colorReadiness?.supported===false||colorReadinessSamples>=12)return;
              colorReadinessSamples++;
              colorReadiness=inspectPracticeMonsterColorReadiness(runtime,geometryState,manager,emit);
            }
            function observeReady(phase) {
              checkFault();
              if(phase.lifecycle.state===6&&!originalAutoControlsVerified) {
                rngStateVerifier.assertComplete();
                originalRngStateVerified=true;
                autoContentsAtPlaying=autoPreferences.readNativeContentsOpen();
                const managerSeed=Number(manager.field('<SpotRandomSeed>k__BackingField').value);
                const random=pin(runtime.class('NK.Spot.Common.SpotRandom').field('_shared').value);
                emit({status:'original_practice_rng_readback',managerSeed,
                  sharedCurrentSeed:Number(random.field('_currSeed').value),
                  originalDrawCount:random.field('<DrawCount>k__BackingField').value.toString(),
                  requestedSeed:modeInput.randomSeed,randomStateWritten:false,
                  fullSharedRngStateVerified:originalRngStateVerified});
                if(managerSeed!==modeInput.randomSeed)
                  throw new Error('Original manager did not retain the captured random seed');
                const autoAim=!!call(team.method('get_IsAutoModeAim',0),team).unbox().handle.readU8();
                const autoBurst=!!call(team.method('get_IsAutoModeSkill',0),team).unbox().handle.readU8();
                emit({status:'original_practice_playing_controls',autoAim,autoBurst,
                  nativeTick:phase.tick,controlInputsWritten:false});
                if(!autoAim||!autoBurst)
                  throw new Error('Original playing auto controls differ from the captured full-auto reference');
                originalAutoControlsVerified=true;
              }
              if(geometry)return;
              if(!call(resourceGate,manager).unbox().handle.readU8())
                return {pending:true,reason:'Original SpotManagement.IsResourceLoad=false'};
              const result=finishPracticeGeometryRuntime(geometryState,manager,team,pin,emit);
              if(!result)return {pending:true,reason:geometryState.pendingReason};
              geometry=result;
              observeColorReadiness();
              aimBinding=verifyPracticeAimBinding(runtime,
                Il2Cpp.domain.assembly('UnityEngine.CoreModule').image,manager,team,geometry,pin,emit);
              const observed=geometry.live.actors.map(actor=>{
                const info=pin(actor.entity.field('<CharacterStaticInfo>k__BackingField').value);
                return {entityId:actor.entityId,tableId:integer(info,'get_TableId'),nameCode:integer(info,'get_NameCode')};
              });
              originalActors=modeInput.characters.map(expected=>{
                const matches=observed.filter(actor=>actor.tableId===expected.tableId&&actor.nameCode===expected.nameCode);
                if(matches.length!==1)throw new Error('Original loaded actor differs from captured input');
                return matches[0];
              });
              capture=installOriginal153PracticeResultCapture(runtime,team,pin,emit,modeInput,callbacks);
              emit({status:'original_practice_loaded_inputs_verified',originalActors,
                sourceInputSha256:modeInput.inputSourceSha256,
                screen:geometry.screen,baselineNativeScreenDimensionsCaptured:false,
                fullMechanicalCoverageVerified:false});
            }
            ticks=startOriginalPracticeTicks(runtime,manager,process,modeInput,emit,complete,
              state=>capture?capture.captureTerminal(state):{pending:true,resultCaptured:false},{
                maxWallMs:40000,maxUpdates:20000,
                schedule:createPracticeFrameScheduler(pin,emit,-1,
                  ()=>originalAutoControlsVerified&&originalRngStateVerified),
                checkFault,beforeUpdate:observeReady,
                actorIdentities:()=>originalActors,
                inputEvidence:()=>({transporterProcessType:fixture.readback.processType,
                  managementType:fixture.readback.managementType,teamNumber:fixture.readback.teamNumber,
                  waveId:fixture.readback.waveId,timeLimit:fixture.readback.timeLimit,
                  teamType:fixture.readback.teamType,randomSeed:fixture.readback.randomSeed,
                  inputReadbackPassed:fixture.passed&&geometry!==null&&originalAutoControlsVerified&&originalRngStateVerified,
                  inputSourceSha256:modeInput.inputSourceSha256}),
                onSample:sample=>{
                  if(sample.completedUpdateCalls%300===0){
                    emit({status:'original_practice_progress',...sample});
                    if(sample.lifecycle.state===6)observeColorReadiness();
                  }
                }
              });
          }catch(problem){fail(problem);}
          });
          active.boundaries.push(loadingOverlay);
          }catch(problem){fail(problem);}
        });
      }catch(error){fail(error);}
    }),100);
  }catch(error){fail(error);}
  return active;
}
