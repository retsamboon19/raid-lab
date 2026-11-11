"""Compose selected builds into the original153 host; never execute a battle."""
from pathlib import Path
import copy
import hashlib
import importlib.util
import json
import re
import struct

HERE=Path(__file__).resolve().parent
ENCOUNTERS=HERE.parent/'encounters153'
ROOT=HERE.parents[3]
CLIENT='d39896d3770888039c728a1908448c3db5efa7cdf874c90d56f46d8d566428d2'
DELIMITER=b'\n\xe2\x9c\x84\n'

def digest(data): return hashlib.sha256(data).hexdigest()
def encoded(value): return json.dumps(value,sort_keys=True,separators=(',',':'),ensure_ascii=True).encode()
def write_json(path,value):
    with path.open('xb') as f:f.write(encoded(value)+b'\n')
    return digest(path.read_bytes())
def load_module(path,name):
    spec=importlib.util.spec_from_file_location(name,path)
    module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module);return module
def replace_once(source,old,new,label):
    if source.count(old)!=1:raise ValueError('Frozen source boundary changed: '+label)
    return source.replace(old,new,1)
def parse_bundle(data):
    if not data.startswith(b'\xf0\x9f\x93\xa6\n'):raise ValueError('Expected original Frida package')
    head,separator,rest=data.partition(DELIMITER)
    if not separator:raise ValueError('Missing package frame')
    headers=head.decode().splitlines()
    entries=[x for x in headers[1:] if re.fullmatch(r'\d+ /.+',x)]
    modules=[]
    for i,entry in enumerate(entries):
        size=int(entry.split(' ',1)[0]);modules.append(rest[:size]);rest=rest[size:]
        if len(modules[-1])!=size:raise ValueError('Truncated package')
        if i+1<len(entries):
            if not rest.startswith(DELIMITER):raise ValueError('Broken package frame')
            rest=rest[len(DELIMITER):]
    if rest:raise ValueError('Unexpected package suffix')
    return headers,modules

def custom_probe(source):
    source=replace_once(source,
        "    const replay=runCapturedSnapshotReconstruction(runtime,staticImage,pin,emit,\n      globalThis.CAPTURED_REPLAY_INPUT,globalThis.CAPTURED_REPLAY_EXPECTED);",
        "    const replay=buildNativeTeam153(runtime,staticImage,pin,emit,globalThis.NATIVE_BATTLE_INPUT);",
        'original build construction')
    source=replace_once(source,
        '          globalThis.CAPTURED_FIXTURE_INPUT,globalThis.CAPTURED_REPLAY_EXPECTED,',
        "          {fixtureInput:globalThis.CUSTOM_NATIVE_FIXTURE,snapshotInput:{sourceKind:'custom_team',characters:replay.characters}},replay.expected,",
        'original team conversion')
    source=replace_once(source,
        "        rngStateVerifier=createOriginalPracticeRngStateVerifier(runtime,\n          globalThis.PRACTICE_RNG_EXPECTED,pin,emit,\n          {expectedSha256:globalThis.PRACTICE_RNG_EXPECTED_SHA256});",
        '        rngStateVerifier=createCustomNativeRngObserver153(runtime,pin,emit);',
        'new battle RNG observation')
    source=source.replace('originalRngStateVerified','originalRngStateObserved')
    source=source.replace('fullSharedRngStateVerified:','fullSharedRngStateObserved:')
    source=source.replace("phase:'original153_practice_probe'","phase:'original153_custom_team_probe',requestSha256:globalThis.NATIVE_BATTLE_REQUEST_SHA256")
    for before,after in [('validateNative153PracticeInput','validateNative153EncounterInput'),
                         ('createOriginal153PracticeProcess','createOriginal153EncounterProcess'),
                         ('installOriginal153PracticeResultCapture','installOriginal153EncounterResultCapture')]:
        source=source.replace(before,after)
    source=replace_once(source,'    initializeCapturedPracticeSettings(runtime,pin,emit);',
        """    initializeCapturedPracticeSettings(runtime,pin,emit);
    const viewportGate=(()=>{
      const target=globalThis.NATIVE153_REQUESTED_VIEWPORT;
      if(!target)return ()=>true;
      const core=Il2Cpp.domain.assembly('UnityEngine.CoreModule').image;
      const screen=core.class('UnityEngine.Screen'),game=Process.getModuleByName('GameAssembly.dll');
      const bind=(name,rva,prefix,returns,parameters)=>{
        const method=screen.method(name).overload(...parameters),address=game.base.add(rva);
        const bytes=Array.from(new Uint8Array(address.readByteArray(prefix.length/2)),v=>v.toString(16).padStart(2,'0')).join('');
        if(!method.isStatic||method.returnType.name!==returns||!method.virtualAddress.equals(address)||bytes!==prefix)
          throw Error('Original viewport method binding differs: '+name);
        return method;
      };
      const width=bind('get_width',139443088,'4883ec28488b0585b845034885c07513488d0d51666700e8','System.Int32',[]);
      const height=bind('get_height',139442704,'4883ec28488b050dba45034885c07513488d0df1676700e8','System.Int32',[]);
      const mode=bind('get_fullScreenMode',139442608,'4883ec28488b05c5ba45034885c07513488d0d896a6700e8','UnityEngine.FullScreenMode',[]);
      const set=bind('SetResolution',139441936,'48895c24084889742410574883ec20488b0572bd4503418b','System.Void',['System.Int32','System.Int32','UnityEngine.FullScreenMode']);
      const enumClass=core.class('UnityEngine.FullScreenMode'),field=enumClass.field('Windowed');
      if(!enumClass.isEnum||enumClass.valueTypeSize!==4||field.type.name!=='UnityEngine.FullScreenMode'||field.offset!==0||!field.isStatic||!field.isLiteral)
        throw Error('Original Windowed enum binding differs');
      const raw=field.value,windowed=typeof raw==='number'?raw:Number(raw.field('value__').value);
      if(!Number.isSafeInteger(windowed))throw Error('Original Windowed enum literal invalid');
      const read=()=>({width:invokeChecked(width,null,[]).unbox().handle.readS32(),
        height:invokeChecked(height,null,[]).unbox().handle.readS32(),
        fullScreenMode:invokeChecked(mode,null,[]).unbox().handle.readS32()});
      const before=read(),started=Date.now();let verified=false;
      invokeChecked(set,null,[intArg(target.width),intArg(target.height),intArg(windowed)]);
      emit({status:'original_request_viewport_requested',before,target,windowed,originalSetResolutionRva:139441936,cameraOrProjectionWrites:false});
      return ()=>{
        const actual=read();
        if(actual.width===target.width&&actual.height===target.height&&actual.fullScreenMode===windowed){
          if(!verified)emit({status:'original_request_viewport_verified',target,actual,beforeFixture:true,cameraOrProjectionWrites:false});
          verified=true;return true;
        }
        if(Date.now()-started>10000)throw Error('Original requested viewport did not settle within10s: '+JSON.stringify({target,actual}));
        return false;
      };
    })();""",'original request viewport initialization')
    source=replace_once(source,"        checkFault();\n        if(!dpRegistration.poll().ready)",
        "        checkFault();\n        if(!viewportGate()){stage='original_request_viewport_pending';return;}\n        if(!dpRegistration.poll().ready)",
        'original viewport readiness before fixture')
    source=replace_once(source,"  let rngStateVerifier=null;","  let rngStateVerifier=null,tactical=null,compiledEventPrefilter=null;",'tactical lifetime')
    source=replace_once(source,"    finished=true;","    finished=true;\n    tactical?.onNativeFinish();\n    row={...row,tactical:tactical?.summary()||null};",'native finish input cleanup')
    source=source.replace('callbacks?.check();monsterBoundary?.check();','tactical?.check();callbacks?.check();monsterBoundary?.check();')
    source=replace_once(source,"        if(!fixture.passed)throw new Error('Original captured practice fixture did not pass');",
        "        if(!fixture.passed)throw new Error('Original selected encounter fixture did not pass');\n        verifyNative153EncounterWave(staticImage,pin,emit,modeInput,fixture.waveStaticInfo);",'original selected wave')
    source=replace_once(source,
        '          row.passed=row.introDurationBitsLE===introExpected.expectedIntroDurationFloat32BitsLE&&\n            row.useIntroCutScene===introExpected.expectedUseIntroCutScene&&!row.isShowLoadingPage;',
        '          row.passed=Number.isFinite(row.introDuration)&&row.introDuration>=0&&!row.isShowLoadingPage;\n          row.referenceCompared=false;',
        'custom original intro observation')
    source=replace_once(source,
        '        const ctx=prepareOriginalPracticeContext(runtime,staticImage,pin,emit,fixture,modeInput);',
        "        if(globalThis.NATIVE153_EVENT_PREFILTER_INPUT===true){\n          const eventDispatch=runtime.class('NK.Spot.SpotManagement').method('SendEventDefault',1);\n          requireKraken153Method(eventDispatch,kraken153Binding().methods.dispatch.rva);\n          compiledEventPrefilter=createNativeTacticalEventPrefilter(runtime,null,eventDispatch,mechanicsNativeTacticalEventClasses(),\n            (event,ordinal)=>tactical?.forwardEvent(event,ordinal),token=>tactical?.afterEvent(token),\n            error=>{if(!firstAsyncFault)firstAsyncFault={error:String(error),nativeFrames:error?.nativeFrames||[]};});\n        }\n        if(globalThis.NATIVE153_FRAME_PROFILE_INPUT?.enabled===true)globalThis.NATIVE153_CHECKED_SCALAR_READER=createNativeCheckedScalarReader();\n        if(globalThis.NATIVE153_FRAME_PROFILE_INPUT?.enabled===true&&globalThis.NATIVE153_CLEAN_PROFILE_INPUT!==true)globalThis.NATIVE153_CLOCK_DIAGNOSTIC=createNativeClockCallerDiagnostic(emit);\n        const originalUiScoreReader=modeInput.encounter.contentMode==='anomaly'?installOriginal153AnomalyUiScore(runtime,pin):null;\n        const ctx=prepareOriginalPracticeContext(runtime,staticImage,pin,emit,fixture,modeInput);",
        'passive original UI score observer before native OnInit')
    source=replace_once(source,'              capture=installOriginal153EncounterResultCapture(runtime,team,pin,emit,modeInput,callbacks);',
        "              capture=installOriginal153EncounterResultCapture(runtime,team,pin,emit,modeInput,{...callbacks,originalUiScoreReader,\n                setOriginalFinishObserver:observer=>callbacks.setOriginalFinishObserver(value=>{\n                  let originalError=null;\n                  try{return observer(value);}catch(error){originalError=error;throw error;}\n                  finally{\n                    const cleanupErrors=[];\n                    for(const cleanup of [()=>globalThis.NATIVE153_PROFILER_RECORDERS?.close(),()=>globalThis.NATIVE153_UNITY_SCOPE_TIMING?.close(),()=>globalThis.NATIVE153_LATEUPDATE_OWNERS?.close(),()=>globalThis.NATIVE153_PLAYERLOOP_TIMING?.close(),()=>tactical?.finishBeforeCleanup(),()=>tactical?.onNativeFinish(),()=>globalThis.NATIVE153_SPEED_CLOSE?.(),()=>globalThis.NATIVE153_FX_SETTINGS_RESTORE?.(),()=>globalThis.NATIVE153_POSTPROCESS_WITNESS?.close(),()=>globalThis.NATIVE153_FX_QUALITY_WITNESS?.close(),()=>globalThis.NATIVE153_POSE_CLOCK?.close(),()=>globalThis.NATIVE153_HOOKS_DELEGATE?.close(),()=>globalThis.NATIVE153_GENERIC_CLOCK_OWNER?.close(),()=>globalThis.NATIVE153_PAUSE_OWNER?.close()])\n                      try{cleanup();}catch(error){cleanupErrors.push(error);}\n                    if(cleanupErrors.length&&!originalError)throw cleanupErrors[0];\n                  }\n                })});",'native finish tactical ownership')
    source=replace_once(source,'                maxWallMs:40000,maxUpdates:20000,',
        '                maxWallMs:modeInput.encounter.timeLimit*1000+120000,maxUpdates:200000,','bounded longer encounters')
    source=replace_once(source,'                checkFault,beforeUpdate:observeReady,',
        """                checkFault,beforeUpdate:phase=>{
                  if(globalThis.NATIVE153_FRAME_PROFILE?.measurementComplete()){
                    globalThis.NATIVE153_LATEUPDATE_OWNERS?.finalize();
                    globalThis.NATIVE153_PLAYERLOOP_TIMING?.finalize();
                    let cleanupError=null;for(const cleanup of [()=>globalThis.NATIVE153_UNITY_SCOPE_TIMING?.close(),()=>globalThis.NATIVE153_PROFILER_RECORDERS?.close()])try{cleanup();}catch(error){if(!cleanupError)cleanupError=error;}if(cleanupError)throw cleanupError;
                  }
                  globalThis.NATIVE153_PROFILER_RECORDERS?.sample(phase);
                  if(phase.lifecycle.state===6)globalThis.NATIVE153_FX_QUALITY_WITNESS?.observe('Playing');
                  globalThis.NATIVE153_STARTUP_SKIP?.step(phase);
                  globalThis.NATIVE153_LOADING_READINESS?.observe(phase);
                  if(globalThis.NATIVE153_FRAME_PROFILE?.stopRequested()){
                    globalThis.NATIVE153_CLOCK_DIAGNOSTIC?.close(phase,'profile_complete');
                    for(const cleanup of [()=>globalThis.NATIVE153_POSE_CLOCK?.close(),()=>globalThis.NATIVE153_PAUSE_OWNER?.close(),()=>globalThis.NATIVE153_CLOCK_OWNER_META?.resolve(),()=>{globalThis.NATIVE153_HOOKS_DELEGATE?.close();emit({status:'original_hooks_delegate_closed',summary:globalThis.NATIVE153_HOOKS_DELEGATE?.summary()});},()=>globalThis.NATIVE153_GENERIC_CLOCK_OWNER?.close()])try{cleanup();}catch(error){emit({status:'native_performance_diagnostic_cleanup_fault',error:String(error)});}
                    tactical?.close('native_frame_profile_complete');
                    emit({status:'native_frame_profile_diagnostic_complete',profile:globalThis.NATIVE153_FRAME_PROFILE.summary(),diagnosticOnly:true});
                    throw Error('Diagnostic native frame profile completed600Playingframes');
                  }
                  return globalThis.NATIVE153_FRAME_PROFILE?globalThis.NATIVE153_FRAME_PROFILE.measure('before_update',()=>{
                  if(globalThis.NATIVE153_FRAME_PROFILE_INPUT?.enabled===true&&phase.lifecycle.state!==6){
                    const row={processState:phase.lifecycle.state,isShowLoadingPage:manager.handle.add(0xb5).readU8()!==0,
                      introDuration:manager.handle.add(0xb0).readFloat(),nativeTick:phase.tick,playTime:phase.playTime};
                    const key=JSON.stringify([row.processState,row.isShowLoadingPage,row.introDuration]);
                    if(globalThis.NATIVE153_LOADING_STATE_KEY!==key){globalThis.NATIVE153_LOADING_STATE_KEY=key;
                      emit({status:'native_loading_state_transition',...row,stateWritten:false});}
                  }
                  globalThis.NATIVE153_POSE_CLOCK?.sample(phase);
                  const ready=observeReady(phase);
                  if(globalThis.NATIVE153_SPEED_INPUT?.multiplier!==1||globalThis.NATIVE153_FRAME_PROFILE_INPUT?.enabled===true)
                    globalThis.NATIVE153_SPEED_READY={playing:phase.lifecycle.state===6,
                      auto:originalAutoControlsVerified,rng:originalRngStateObserved,management:manager};
                  if(phase.lifecycle.state===6)originalUiScoreReader?.assertInitialized();
                  const requestedViewport=globalThis.NATIVE153_REQUESTED_VIEWPORT;
                  if(geometry&&requestedViewport&&
                      (geometry.screen.width!==requestedViewport.width||geometry.screen.height!==requestedViewport.height))
                    throw Error('Original request viewport mismatch before tactical control: '+JSON.stringify({requested:requestedViewport,actual:geometry.screen}));
                  if(geometry&&originalAutoControlsVerified&&phase.lifecycle.state===6){
                    if(!tactical){
                      tactical=createNative153TacticalController(runtime,manager,team,geometry,aimBinding,pin,emit,
                        {waveId:modeInput.encounter.waveId,control_policy:modeInput.encounter.controlPolicy||'auto',passiveShotWitness:modeInput.encounter.waveId===6302006});
                      if(tactical.dispatchMethod&&globalThis.NATIVE153_EVENT_PREFILTER_INPUT===true)
                        listeners.push(tactical.useEventPrefilter(compiledEventPrefilter));
                      else if(tactical.dispatchMethod)listeners.push(Interceptor.attach(tactical.dispatchMethod.virtualAddress,{
                        onEnter(args){this.passiveShotToken=null;if(args[0].equals(manager.handle)&&!args[1].isNull()){
                          try{this.passiveShotToken=tactical.forwardEvent(new Il2Cpp.Object(args[1]));}
                          catch(error){if(!firstAsyncFault)firstAsyncFault={error:String(error),nativeFrames:error?.nativeFrames||[]};}
                        }},
                        onLeave(){if(this.passiveShotToken)tactical?.afterEvent?.(this.passiveShotToken);}
                      }));
                    }
                    tactical.beforeTick(phase.tick);
                    if(originalRngStateObserved){globalThis.NATIVE153_CLOCK_DIAGNOSTIC?.start(phase);if(globalThis.NATIVE153_HOOKS_DELEGATE&&!globalThis.NATIVE153_HOOKS_DELEGATE.summary().started)globalThis.NATIVE153_HOOKS_DELEGATE.start();}
                  }
                  return ready;
                  }):(()=>{throw Error("Native frame profile scheduler object missing");})();
                },afterUpdate:sample=>{
                  const profile=globalThis.NATIVE153_FRAME_PROFILE;
                  const run=()=>tactical?.afterTick(sample.tick);
                  if(profile)profile.measure('after_update',run);else run();
                  profile?.finishFrame({deltaTime:sample.deltaFloat32,nativeTick:sample.tick,playTime:sample.playTime,lifecycle:sample.lifecycle.state});
                  if(profile?.measurementStarted()){globalThis.NATIVE153_UNITY_SCOPE_TIMING?.start(sample);globalThis.NATIVE153_PROFILER_RECORDERS?.start(sample);globalThis.NATIVE153_PLAYERLOOP_TIMING?.start(sample);globalThis.NATIVE153_LATEUPDATE_OWNERS?.start(sample);}
                  if(profile?.measurementComplete()){globalThis.NATIVE153_LATEUPDATE_OWNERS?.deactivate(sample);globalThis.NATIVE153_PLAYERLOOP_TIMING?.deactivate(sample);}
                },""",'native player control policy')
    source=replace_once(source,"            stage='original_on_init';",
        "            if(globalThis.NATIVE153_LATEUPDATE_OWNERS_INPUT===true)globalThis.NATIVE153_LATEUPDATE_OWNERS=createNativeLateUpdateOwnerTiming(createNativePlayerLoopDiscovery(pin),emit);if(globalThis.NATIVE153_PLAYERLOOP_TIMING_INPUT===true)globalThis.NATIVE153_PLAYERLOOP_TIMING=createNativePlayerLoopTiming(createNativePlayerLoopDiscoveryWithGc(pin),emit);if(globalThis.NATIVE153_PROFILER_RECORDERS_INPUT===true)globalThis.NATIVE153_PROFILER_RECORDERS=createNativeProfilerRecorderExperiment(createNativeProfilerRecorderBinding(),emit);if(globalThis.NATIVE153_UNITY_SCOPE_PROFILE_INPUT===true)globalThis.NATIVE153_UNITY_SCOPE_TIMING=createNativeUnityScopeTiming(emit);if(globalThis.NATIVE153_GRAPHICS_OVERRIDE_INPUT)globalThis.NATIVE153_FX_QUALITY_WITNESS=createNativeFxQualityWitness(runtime,manager,pin,emit,{quality:0});if(globalThis.NATIVE153_STARTUP_SKIP_INPUT===true)globalThis.NATIVE153_STARTUP_SKIP=installNativeStartupMonsterSkip(runtime,manager,pin,emit);if(globalThis.NATIVE153_FRAME_PROFILE_INPUT?.enabled===true&&globalThis.NATIVE153_CLEAN_PROFILE_INPUT!==true){try{inspectOriginalRenderMetadata(emit);}catch(error){emit({status:'render_metadata_diagnostic_error',error:String(error)});}globalThis.NATIVE153_LOADING_TIMING=installNativeLoadingTiming(emit);globalThis.NATIVE153_LOADING_READINESS=createNativeLoadingReadinessWitness(manager,emit);globalThis.NATIVE153_PAUSE_OWNER=installNativePauseOwnerWitness(manager,emit);try{globalThis.NATIVE153_POSE_CLOCK=createNativePoseClockWitness(runtime,pin,emit,()=>tactical?.inspectCurrentCoreGeometry?.());}catch(error){emit({status:'original_pose_clock_binding_unavailable',error:String(error)});}try{globalThis.NATIVE153_CLOCK_OWNER_META=createNativeClockOwnerDiagnostic(runtime,emit);globalThis.NATIVE153_CLOCK_OWNER_META.resolve();try{const m=Il2Cpp.domain.assembly('UnityEngine.CoreModule').image.class('UnityEngine.Time').method('get_fixedUnscaledDeltaTime',0);const finder=createNativeCutSceneSkipClassLookup({name:'UnityEngine.Time.get_fixedUnscaledDeltaTime',handle:m.handle,resolvedVirtualAddress:m.virtualAddress});emit(finder.lookup(Il2Cpp.domain));finder.close();}catch(error){emit({status:'original_monster_cutscene_skip_class_unavailable',error:String(error)});}const hookMethods=globalThis.NATIVE153_CLOCK_OWNER_META.methodsFor(0x84041b0);if(hookMethods.length!==1)throw Error('ExpectedoneoriginalHooks.Update');try{globalThis.NATIVE153_HOOKS_DELEGATE=createNativeHooksDelegateWitness(hookMethods[0],emit);}catch(error){emit({status:'original_hooks_delegate_binding_unavailable',error:String(error)});}globalThis.NATIVE153_GENERIC_CLOCK_OWNER=installNativeGenericClockOwnerWitness(emit);}catch(error){emit({status:'original_clock_owner_binding_unavailable',error:String(error)});}}\n            stage='original_on_init';",'passive loading timing after source guards')
    source=replace_once(source,'    tactical?.onNativeFinish();',
        "    for(const cleanup of [()=>globalThis.NATIVE153_PROFILER_RECORDERS?.close(),()=>globalThis.NATIVE153_UNITY_SCOPE_TIMING?.close(),()=>globalThis.NATIVE153_STARTUP_SKIP?.close(),()=>globalThis.NATIVE153_LOADING_TIMING?.close(),()=>globalThis.NATIVE153_LOADING_READINESS?.close(),()=>globalThis.NATIVE153_CLOCK_DIAGNOSTIC?.close(null,'complete'),()=>globalThis.NATIVE153_POSE_CLOCK?.close(),()=>globalThis.NATIVE153_PAUSE_OWNER?.close(),()=>globalThis.NATIVE153_HOOKS_DELEGATE?.close(),()=>globalThis.NATIVE153_GENERIC_CLOCK_OWNER?.close()])try{cleanup();}catch(error){emit({status:'native_performance_diagnostic_cleanup_fault',error:String(error)});}\n    tactical?.onNativeFinish();",'diagnostic loading observer cleanup')
    source=replace_once(source,'                  if(phase.lifecycle.state===6)originalUiScoreReader?.assertInitialized();',
        '                  if(phase.lifecycle.state===6){globalThis.NATIVE153_LOADING_TIMING?.close();globalThis.NATIVE153_PAUSE_OWNER?.close();originalUiScoreReader?.assertInitialized();}', 'loading timing firstPlaying detach')
    source=replace_once(source,"  const emit=row=>record({phase:'original153_custom_team_probe',requestSha256:globalThis.NATIVE_BATTLE_REQUEST_SHA256,fullAccuracyVerified:false,...row});",
        "  const emit=row=>record({phase:'original153_custom_team_probe',requestSha256:globalThis.NATIVE_BATTLE_REQUEST_SHA256,fullAccuracyVerified:false,...row});\n  emit({status:'native_js_runtime_observed',runtime:Script.runtime,fridaVersion:Frida.version,requested:globalThis.NATIVE153_JS_RUNTIME_EXPECTED});if(globalThis.NATIVE153_JS_RUNTIME_EXPECTED==='v8'&&Script.runtime!=='V8')throw Error('RequestedV8Gadgetruntime notactive');",'actualJSruntime receipt')
    complete_start=source.index("    finished=true;",source.index("  function complete(row={})"))
    complete_end=source.index("    if(poll)clearInterval(poll);",complete_start)
    if 'tactical?.onNativeFinish();' not in source[complete_start:complete_end]:
        raise RuntimeError('Original custom completion cleanup contract changed')
    source=source[:complete_start]+r"""    finished=true;
    const probeCleanupErrors=[];
    for(const [step,cleanup] of [
      ['tactical_inputs',()=>{if(row.completeBattle===true)tactical?.onNativeFinish();else tactical?.close('native_probe_stopped_before_native_finish');}],
      ['original_clocks_and_rate',()=>globalThis.NATIVE153_SPEED_CLOSE?.()],
      ['original_graphics_settings',()=>globalThis.NATIVE153_FX_SETTINGS_RESTORE?.()],
      ['original_postprocess_witness',()=>globalThis.NATIVE153_POSTPROCESS_WITNESS?.close()],
      ['graphics_quality_witness',()=>globalThis.NATIVE153_FX_QUALITY_WITNESS?.close()],
      ['lateupdate_owner_timing',()=>globalThis.NATIVE153_LATEUPDATE_OWNERS?.close()],
      ['playerloop_native_timing',()=>globalThis.NATIVE153_PLAYERLOOP_TIMING?.close()],
      ['profiler_recorders',()=>globalThis.NATIVE153_PROFILER_RECORDERS?.close()],
      ['native_unity_scope',()=>globalThis.NATIVE153_UNITY_SCOPE_TIMING?.close()],
      ['startup_skip',()=>globalThis.NATIVE153_STARTUP_SKIP?.close()],
      ['loading_timing',()=>globalThis.NATIVE153_LOADING_TIMING?.close()],
      ['loading_readiness',()=>globalThis.NATIVE153_LOADING_READINESS?.close()],
      ['clock_diagnostic',()=>globalThis.NATIVE153_CLOCK_DIAGNOSTIC?.close(null,'complete')],
      ['pose_clock',()=>globalThis.NATIVE153_POSE_CLOCK?.close()],
      ['pause_owner',()=>globalThis.NATIVE153_PAUSE_OWNER?.close()],
      ['hooks_delegate',()=>globalThis.NATIVE153_HOOKS_DELEGATE?.close()],
      ['generic_clock_owner',()=>globalThis.NATIVE153_GENERIC_CLOCK_OWNER?.close()]
    ])try{cleanup();}catch(error){probeCleanupErrors.push({step,error:String(error)});}
    if(probeCleanupErrors.length)row={...row,status:'first_failure',statusBeforeCleanup:row.status,
      error:row.error===undefined?'Original probe cleanup failed: '+probeCleanupErrors.map(e=>e.step+': '+e.error).join('; '):row.error,probeCleanupErrors};
    row={...row,tactical:tactical?.summary()||null};
"""+source[complete_end:]
    # Route the existing intentional profile stop through this same error cleanup.
    source=replace_once(source,"                    tactical?.close('native_frame_profile_complete');\n",'',
        'shared external-failure cleanup owns diagnostic profile stop')
    return source


def custom_fixture(source):
    source=replace_once(source,
        "  if(!fixture||!source||fixture.captureSha256!==source.captureSha256||fixture.transporterValueSize!==376)",
        "  if(!fixture||!source||fixture.sourceKind!=='custom_team'||source.sourceKind!=='custom_team'||fixture.transporterValueSize!==376)",
        'custom source provenance')
    source=replace_once(source,
        '  const replay=bindings.replay||runCapturedSnapshotReconstruction(runtime,staticImage,pin,emit,source,expected);',
        '  const replay=bindings.replay;\n  if(!replay||!expected)throw Error("Original current-job build readbacks required");',
        'no captured fallback')
    source=replace_once(source,
        '  const team=retain(call(createTeam,null,[array.handle,ptr(0),a32(fixture.teamConversion.statIncrease)]));',
        '  const encounterTeam=prepareNative153EncounterTeam(runtime,staticImage,pin,emit,globalThis.PRACTICE_MODE_INPUT,replay);\n  const team=retain(encounterTeam.team);\n  const teamExpected=encounterTeam.expected;',
        'original mode team construction')
    source=replace_once(source,'    const ref=expected.characters[index].nativeConversion;',
        '    const ref=teamExpected.characters[index].nativeConversion;','original mode team readbacks')
    source=replace_once(source,
        "    const binding=typeof bindings.resolveNativeOwnerField==='function'?bindings.resolveNativeOwnerField(spec):null;",
        "    const binding=encounterTeam.transporterBindings?.[spec.name]||\n      (typeof bindings.resolveNativeOwnerField==='function'?bindings.resolveNativeOwnerField(spec):null);",
        'original mode context binding')
    source=source.replace('captureSourceSha256:fixture.captureSha256','requestSha256:fixture.requestSha256')
    source=source.replace("status:'captured_practice_fixture_prepared'","status:'custom_native_fixture_prepared'")
    source=source.replace("status:'custom_native_fixture_prepared',passed:","status:'custom_native_fixture_prepared',requestSha256:fixture.requestSha256,passed:")
    source=replace_once(source,"    randomSeed:getInt('RandomSeed'),isAuto:getBool('IsAuto'),",
        "    raidLvChangeGroup:getInt('RaidLvChangeGroup'),themeType:getInt('ThemeType'),stageTableType:getInt('StageTableType'),\n    randomSeed:getInt('RandomSeed'),isAuto:getBool('IsAuto'),",'encounter context field readbacks')
    return source


def encounter_ticks(source):
    source=replace_once(source,'      call(originalUpdate,management,[dt]);',
        "      if(globalThis.NATIVE153_FRAME_PROFILE)globalThis.NATIVE153_FRAME_PROFILE.measure('original_update_tick',()=>call(originalUpdate,management,[dt]));else call(originalUpdate,management,[dt]);",'passive original update timing')
    source=source.replace('validateNative153PracticeInput','validateNative153EncounterInput')
    source=source.replace('readOriginal153PracticeLifecycle','readOriginal153EncounterLifecycle')
    source=source.replace('verifyOriginal153PracticeTerminal','verifyOriginal153EncounterCompletion')
    source=replace_once(source,'maxWallMs>300000','maxWallMs>390000','bounded original real-time encounter wall limit')
    return replace_once(source,
        'lastLifecycle.processClass!==NATIVE153_PRACTICE.processClass||lastLifecycle.processType!==9',
        'lastLifecycle.processClass!==input.encounter.processClass||lastLifecycle.processType!==input.encounter.processType',
        'original selected process lifecycle')


def encounter_geometry(source):
    before='''  if (!source || source.installed_client_sha256!==client ||
      receipt!=="ff3d69914a3735a7bd9de5493e687af30b8ef4b9ad35845e7446c19533435449" || source.theme_mode!==9 || source.theme_key!==0 ||
      source.bundles.practice_background_hd.catalog_key!=="sbg_tower_001")
    throw new Error("Exact153 normal ShootingRange geometry source binding changed");
  const backgroundKey="sbg_tower_001";'''
    after='''  const selected=globalThis.NATIVE153_GEOMETRY_SELECTION;
  const formatBinding=globalThis.NATIVE153_GEOMETRY_BINDING;
  if(!source||source.installed_client_sha256!==client||!selected||!formatBinding||
      formatBinding.clientSha256!==client||!receipt||source.encounterId!==selected.encounterId||
      source.theme_mode!==selected.processType||source.theme_key!==selected.uiTheme||
      source.backgroundKey!==selected.backgroundKey||source.loadedMapName!==selected.loadedMapName||selected.commonMechanicalPrefabsVerified!==true)
    throw Error('Original selected encounter presentation binding differs');
  const formatter=Il2Cpp.domain.assembly('NK.Runtime').image.class(formatBinding.className).method('GetPresentationPath',2);
  const formatAddress=Process.getModuleByName('GameAssembly.dll').base.add(formatBinding.method.nativeRva);
  const formatHex=Array.from(new Uint8Array(formatAddress.readByteArray(16)),value=>value.toString(16).padStart(2,'0')).join('');
  if(!formatter.isStatic||!formatter.virtualAddress.equals(formatAddress)||formatHex!==formatBinding.entryHex)
    throw Error('Original presentation path formatter differs');
  const originalMode=Memory.alloc(4);originalMode.writeS32(selected.processType);
  const simulation=Memory.alloc(1);simulation.writeU8(0);
  const originalPath=call(formatter,null,[originalMode,simulation]);
  if(!originalPath||originalPath.isNull()||new Il2Cpp.String(originalPath.handle).content!==selected.themeAssetKey)
    throw Error('Original mode chose another presentation theme');
  const backgroundKey=selected.backgroundKey;
  emit({status:'original153_encounter_geometry_selected',...selected,sourceReceiptSha256:receipt,
    originalThemeFormatterInvoked:true,backgroundSubstituted:false});'''
    source=replace_once(source,before,after,'source-selected original geometry')
    return replace_once(source,'const expectedMapName = state.backgroundKey;',
        'const expectedMapName = globalThis.NATIVE153_GEOMETRY_SELECTION.loadedMapName;',
        'original serialized loaded phase-map identity')

def custom_mode(source):
    source=replace_once(source,'packet.battleDuration!==90000 || packet.characterCount!==5 ||',
        '(!Number.isInteger(packet.battleDuration)||packet.battleDuration<=0||packet.battleDuration>90000) || packet.characterCount!==5 ||',
        'original early terminal duration')
    source=source.replace("!/^[1-9][0-9]*$/.test(r.rounds[0]?.squadTotal||'')", "!/^(0|[1-9][0-9]*)$/.test(r.rounds[0]?.squadTotal||'')")
    return source

def requested_native_viewport(request):
    value=request.get('settings',{}).get('native_viewport')
    # The normal simulator uses the verified original rendered viewport too;
    # restoring the graphics lifecycle must not require a comparison-only flag.
    if value is None:return {'width':905,'height':509}
    if not isinstance(value,dict) or set(value)!={'width','height'}:
        raise ValueError('native_viewport requires only width and height')
    if any(type(value[key]) is not int or not 64<=value[key]<=16384 for key in ('width','height')):
        raise ValueError('native_viewport dimensions must be integers in64..16384')
    return dict(value)


"""Derive one explicit native graphics input; never edit the captured fixture."""
from copy import deepcopy
import hashlib
import json

VIDEO = "NK.Common.System.Settings.NikkeVideoSetting"
QUALITY = "NK.Types.System.UserData.BattleEffectQuality"
FIELD = VIDEO + "::BattleEffectQuality"
VALUE = QUALITY + "::value__"
QUALITY_CLIENT = "d39896d3770888039c728a1908448c3db5efa7cdf874c90d56f46d8d566428d2"


def _digest(value):
    data = json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
    return hashlib.sha256(data.encode("utf-8")).hexdigest()


def derive_quality_input(source, quality=0):
    """Return (owned derived input, provenance); only authored minimum is allowed."""
    if type(quality) is not int or quality != 0:
        raise ValueError("Only explicit native minimum battle-effect quality 0 is supported")
    if source.get("schemaVersion") != 1 or source.get("clientSha256") != QUALITY_CLIENT:
        raise ValueError("Exact original153 captured settings schema/client required")
    try:
        video = source["settings"]["VideoSetting"]
        layout = source["layouts"][VIDEO]
        effect = video["fields"][FIELD]
        fields = [field for field in layout["fields"]
                  if field["name"] == "BattleEffectQuality"]
        valid_layout = (
            video["$type"] == VIDEO and video["$valueSize"] == 36
            and layout["valueSize"] == 36 and len(fields) == 1
            and fields[0]["offset"] == 28 and fields[0]["type"] == QUALITY
            and fields[0]["flags"] == 6
            and effect["$type"] == QUALITY and effect["$valueSize"] == 4
        )
        raw = video["rawHex"]
        if not valid_layout or not isinstance(raw, str) or len(raw) != 72:
            raise ValueError("Original VideoSetting/quality layout differs")
        if any(character not in "0123456789abcdef" for character in raw):
            raise ValueError("Original VideoSetting bytes must be exact lowercase hex")
        before = bytes.fromhex(raw)
        if (before[12:16] != b"\x02\x00\x00\x00"
                or effect["rawHex"] != "02000000"
                or type(effect["fields"][VALUE]) is not int
                or effect["fields"][VALUE] != 2):
            raise ValueError("Expected mutually consistent captured quality 2")
    except (KeyError, TypeError) as error:
        raise ValueError("Captured VideoSetting shape is incomplete") from error

    derived = deepcopy(source)
    result = derived["settings"]["VideoSetting"]
    after = before[:12] + b"\x00\x00\x00\x00" + before[16:]
    result["rawHex"] = after.hex()
    result["fields"][FIELD]["rawHex"] = "00000000"
    result["fields"][FIELD]["fields"][VALUE] = 0

    # Independently reconstruct the capture. No second setting may have changed.
    reconstructed = deepcopy(derived)
    reconstructed_video = reconstructed["settings"]["VideoSetting"]
    reconstructed_video["rawHex"] = video["rawHex"]
    reconstructed_effect = reconstructed_video["fields"][FIELD]
    reconstructed_effect["rawHex"] = effect["rawHex"]
    reconstructed_effect["fields"][VALUE] = effect["fields"][VALUE]
    if reconstructed != source:
        raise ValueError("Graphics derivation changed unrelated captured input")
    if before[:12] != after[:12] or before[16:] != after[16:]:
        raise ValueError("Graphics derivation changed non-quality bytes")
    receipt = {
        "schemaVersion": 1,
        "kind": "derived_native_graphics_input",
        "capturedInputCanonicalSha256": _digest(source),
        "derivedInputCanonicalSha256": _digest(derived),
        "sourceCaptureSha256": source.get("sourceCaptureSha256"),
        "capturedQuality": 2,
        "requestedQuality": 0,
        "nativeSettingType": VIDEO,
        "nativeEnumType": QUALITY,
        "unboxedByteOffset": 12,
        "byteWidth": 4,
        "capturedVideoRawHex": before.hex(),
        "derivedVideoRawHex": after.hex(),
        "changedPaths": [
            "/settings/VideoSetting/rawHex",
            "/settings/VideoSetting/fields/" + FIELD + "/rawHex",
            "/settings/VideoSetting/fields/" + FIELD + "/fields/" + VALUE,
        ],
        "capturedFixtureMutated": False,
        "allOtherInputsUnchanged": True,
        "runtimeApplied": False,
        "provenance": "Quality 0 selects original SpotSetting.GetFxOptionList minimum exclusions; this is an explicit derived input, not a captured quality-0 setting.",
    }
    return derived, receipt


"""Prepare an owned original153 video input with post-processing flags cleared."""
from copy import deepcopy
import hashlib
import json

PP_VIDEO = "NK.Common.System.Settings.NikkeVideoSetting"
PP_POSTPROCESS = "NK.Types.System.UserData.PostProcessType"
PP_QUALITY = "NK.Types.System.UserData.BattleEffectQuality"
PP_FIELD = PP_VIDEO + "::PostProcessFlags"
PP_VALUE = PP_POSTPROCESS + "::value__"
PP_CLIENT = "d39896d3770888039c728a1908448c3db5efa7cdf874c90d56f46d8d566428d2"


def PP__digest(value):
    canonical = json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def derive_postprocess_input(source):
    """Return (derived input, provenance) from a validated minimum-FX input."""
    if (not isinstance(source, dict) or type(source.get("schemaVersion")) is not int
            or source["schemaVersion"] != 1 or source.get("clientSha256") != PP_CLIENT):
        raise ValueError("Exact original153 settings schema and client required")
    try:
        video = source["settings"]["VideoSetting"]
        layout = source["layouts"][PP_VIDEO]
        flags = video["fields"][PP_FIELD]
        quality = video["fields"][PP_VIDEO + "::BattleEffectQuality"]
        postprocess_fields = [field for field in layout["fields"]
                              if field["name"] == "PostProcessFlags"]
        quality_fields = [field for field in layout["fields"]
                          if field["name"] == "BattleEffectQuality"]
        if (video["$type"] != PP_VIDEO or video["$valueSize"] != 36
                or layout["valueSize"] != 36
                or postprocess_fields != [
                    {"name": "PostProcessFlags", "type": PP_POSTPROCESS, "offset": 20, "flags": 6}]
                or quality_fields != [
                    {"name": "BattleEffectQuality", "type": PP_QUALITY, "offset": 28, "flags": 6}]
                or flags["$type"] != PP_POSTPROCESS or flags["$valueSize"] != 4
                or quality["$type"] != PP_QUALITY or quality["$valueSize"] != 4):
            raise ValueError("Original video field layout differs")
        raw = video["rawHex"]
        if (not isinstance(raw, str) or len(raw) != 72
                or any(character not in "0123456789abcdef" for character in raw)):
            raise ValueError("Expected exact lowercase hex for all 36 video bytes")
        before = bytes.fromhex(raw)
        if (before[4:8] != b"\xff" * 4 or flags["rawHex"] != "ffffffff"
                or type(flags["fields"][PP_VALUE]) is not int or flags["fields"][PP_VALUE] != -1):
            raise ValueError("Expected consistent captured post-process flags -1")
        quality_value = quality["fields"][PP_QUALITY + "::value__"]
        if (before[12:16] != bytes(4) or quality["rawHex"] != "00000000"
                or type(quality_value) is not int or quality_value != 0):
            raise ValueError("Expected consistent minimum battle-effect quality 0")
    except (KeyError, TypeError) as error:
        raise ValueError("Original VideoSetting shape is incomplete") from error

    derived = deepcopy(source)
    result = derived["settings"]["VideoSetting"]
    result["rawHex"] = (before[:4] + bytes(4) + before[8:]).hex()
    result["fields"][PP_FIELD]["rawHex"] = "00000000"
    result["fields"][PP_FIELD]["fields"][PP_VALUE] = 0

    reconstructed = deepcopy(derived)
    restored = reconstructed["settings"]["VideoSetting"]
    restored_raw = bytes.fromhex(restored["rawHex"])
    restored["rawHex"] = (restored_raw[:4] + before[4:8] + restored_raw[8:]).hex()
    restored["fields"][PP_FIELD]["rawHex"] = flags["rawHex"]
    restored["fields"][PP_FIELD]["fields"][PP_VALUE] = flags["fields"][PP_VALUE]
    if reconstructed != source:
        raise ValueError("Post-process derivation changed unrelated input")

    field_path = "/settings/VideoSetting/fields/" + PP_FIELD
    return derived, {
        "schemaVersion": 1,
        "kind": "derived_native_postprocess_input",
        "inputCanonicalSha256": PP__digest(source),
        "derivedInputCanonicalSha256": PP__digest(derived),
        "sourceCaptureSha256": source.get("sourceCaptureSha256"),
        "nativeSettingType": PP_VIDEO,
        "nativeEnumType": PP_POSTPROCESS,
        "unboxedByteOffset": 4,
        "boxedByteOffset": 20,
        "byteWidth": 4,
        "inputPostProcessFlags": -1,
        "derivedPostProcessFlags": 0,
        "preservedBattleEffectQuality": 0,
        "inputVideoRawHex": raw,
        "derivedVideoRawHex": result["rawHex"],
        "changedPaths": ["/settings/VideoSetting/rawHex", field_path + "/rawHex",
                         field_path + "/fields/" + PP_VALUE],
        "runtimeApplied": False,
        "restorationBaseline": "Use original captured 36 bytes, before either derivation.",
        "provenance": "Explicit derived setting. Original VolumeProfile code reads masks 2 and 4.",
    }


def custom_graphics_settings(source):
    source=replace_once(source,'  const rows=[];',"""  const postProcessWitness=globalThis.NATIVE153_POSTPROCESS_OVERRIDE_INPUT?createNativePostprocessApplicationWitness(runtime,emit):null;
  const postProcessPhase=(name,value)=>{if(!postProcessWitness)return;try{if(postProcessWitness.setPhase(name,value)!==true)throw Error('Original postprocess witness not armed');}catch(error){try{emit({status:'original_postprocess_witness_phase_fault',name,error:String(error)});}catch(_){}}};
  if(postProcessWitness){globalThis.NATIVE153_POSTPROCESS_WITNESS=postProcessWitness;postProcessPhase('baseline',-1);}
  const rows=[];""",'passive postprocess setting application witness')
    marker="    invokeChecked(setter,null,[box.unbox().handle]);"
    addition="""    if(name==='VideoSetting'&&globalThis.NATIVE153_GRAPHICS_BASELINE_INPUT){
      const baseline=globalThis.NATIVE153_GRAPHICS_BASELINE_INPUT;
      if(baseline.$type!==input.$type||baseline.$valueSize!==size)throw Error('Graphics baseline layout differs');
      const original=pin(klass.alloc());
      original.unbox().handle.writeByteArray(baseline.rawHex.match(/../g).map(x=>parseInt(x,16)));
      let restored=false;
      globalThis.NATIVE153_FX_SETTINGS_RESTORE=()=>{
        if(restored)return;
        postProcessPhase('restore',-1);
        invokeChecked(setter,null,[original.unbox().handle]);
        const checked=pin(invokeChecked(getter,null));
        if(hex(checked.unbox().handle,size)!==baseline.rawHex)throw Error('Graphics baseline setter restoration differs');
        const inject=runtime.class('NK.Common.Scene.Unit.SpotDependencyInjector').method('InjectNikkeSettings',0);
        if(!inject.virtualAddress.equals(game.base.add(0x0707B120)))throw Error('Original settings injector changed');
        invokeChecked(inject,null);
        const field=spotClass.field(name),bytes=Memory.alloc(size);
        readStatic(field.handle,bytes);
        if(hex(bytes,size)!==baseline.rawHex)throw Error('Graphics baseline injected restoration differs');
        restored=true;
        emit({status:'native_graphics_override_restored',rawHex:baseline.rawHex,privateProfileOnly:true});
      };
    }
"""
    source=replace_once(source,marker,addition+"    if(name==='VideoSetting')postProcessPhase('apply',0);\n"+marker,'graphics baseline restoration registration')
    return replace_once(source,"configuredFrameRate:source.frameRate, sourceCaptureSha256:source.sourceCaptureSha256,",
      "configuredFrameRate:source.frameRate, customGraphicsOverride:globalThis.NATIVE153_GRAPHICS_OVERRIDE_INPUT||null, sourceCaptureSha256:source.sourceCaptureSha256,",'graphics provenance')


def compose_custom_job(release,request,root):
    root=Path(root)
    viewport=requested_native_viewport(request)
    request_sha=digest(encoded(request))
    mapper=load_module(HERE/'build_inputs153.py','native_build_inputs153')
    build=mapper.prepare_custom_request(request)
    build['requestSha256']=request_sha
    encounter=build['encounter']
    duration=encounter['timeLimit']
    if type(duration) is not int or not 1<=duration<=270:raise ValueError('Original supported encounter duration exceeds bounded270s catalogue')
    wall_seconds=duration+120
    if wall_seconds>390:raise ValueError('Original encounter real-time wall guard exceeds390s')
    if build.get('clientSha256')!=CLIENT or len(build.get('characters',[]))!=5:
        raise ValueError('Five original153 build inputs required')
    identities=[{'slot':x['slot'],'tableId':x['characterTableId'],'nameCode':x['nameCode']} for x in build['characters']]
    if [x['slot'] for x in identities]!=[1,2,3,4,5] or len({x['nameCode'] for x in identities})!=5:
        raise ValueError('Five ordered distinct characters required')
    build_path=root/'native-build-input.json';build_sha=write_json(build_path,build)
    fixture=json.loads(release.file('fixtureFile').read_text())
    # Retain the source-backed encounter layout and original callback adapters,
    # not the reference squad or its stats. Team data is constructed afresh.
    fixture.pop('captureSha256',None);fixture.pop('sourceOnStart',None);fixture.pop('runIndex',None)
    fixture.update(sourceKind='custom_team',requestSha256=request_sha,
        scope='Original selected encounter; current selected team built natively',nativeBuildInputSha256=build_sha)
    fields={field['name']:field for field in fixture['fields']}
    for name,value in encounter['transporter'].items():
        if name not in fields:raise ValueError('Unknown original transporter input '+name)
        field=fields[name]
        if field['kind'] not in ('int32','enum32','float32','bool','string'):
            raise ValueError('Selected native value requires its original typed constructor: '+name)
        field['value']=value
        if field['kind']=='float32':field['bitsLE']=struct.pack('<f',value).hex()
    fixture['wave']['tableId']=encounter['waveId']
    fields['<StageNameLocaleLazy>k__BackingField']['value']=encounter['name']
    if encounter['contentMode'] in ('museum','solo'):
        fields['<SpotContextData>k__BackingField']['kind']='nativeOwnerBinding'
    # Native zero overrides select the source monster's complete initial HP.
    # Never carry captured remaining HP into a new team/encounter.
    if fields['<TargetMonsterHPRatio>k__BackingField']['value']!=0:
        raise ValueError('Fresh encounter requires original full-HP sentinel')
    hp_fields=[field for field in fixture['fields'] if 'TargetMonsterHP>' in field['name']]
    if len(hp_fields)!=1 or hp_fields[0].get('rawHex')!='0000000000000000':
        raise ValueError('Original target-HP zero input layout changed')
    seed=build.get('randomSeed',1)
    if type(seed) is not int or not 1<=seed<=2147483647:raise ValueError('Invalid native seed')
    seed_field=next(x for x in fixture['fields'] if x['name']=='<RandomSeed>k__BackingField')
    seed_field['value']=seed
    fixture_path=root/'custom-fixture.json';fixture_sha=write_json(fixture_path,fixture)
    mode={'schemaVersion':1,'clientSha256':CLIENT,'encounter':encounter,
        'inputSourceSha256':fixture_sha,'requestSha256':request_sha,'randomSeed':seed,'characters':identities,
        'waveId':encounter['waveId'],'timeLimit':encounter['timeLimit'],'processType':encounter['processType']}
    write_json(root/'custom-mode.json',mode)
    headers,modules=parse_bundle(release.file('bundleFile').read_bytes())
    source=modules[1].decode()
    updates={
        'probeSource':custom_probe,
        'fixtureSource':custom_fixture,
        'settingsSource':custom_graphics_settings,
        'tickSource':encounter_ticks,
        'geometrySource':encounter_geometry,
        'schedulerSource':lambda original:(HERE/'native_real_time_scheduler153.js').read_text(),
    }
    source_hashes={}
    for name,transform in updates.items():
        old=(release.directory/('frozen/frozen-'+name+'.js')).read_text()
        new=transform(old)
        source=replace_once(source,old,new,name)
        output=root/('custom-'+name+'.js');output.write_text(new,encoding='utf-8')
        source_hashes[name]={'path':str(output),'sha256':digest(output.read_bytes())}
    # Frida rewrites the driver's import while bundling; bind this one exact
    # native-host watchdog boundary instead of expecting the raw module verbatim.
    source=replace_once(source,
        '      if (!batch || String(device) !== "Null") throw new Error("Expected batch mode and Null graphics device");',
        '''      if(globalThis.NATIVE153_REQUESTED_VIEWPORT) {
        if(batch||String(device)!=="Direct3D11") throw Error("Requested original rendered viewport requires non-batch Direct3D11");
      } else if (!batch || String(device) !== "Null") throw new Error("Expected batch mode and Null graphics device");''',
        'request-scoped original graphics device guard')
    source=replace_once(source,'  }, 50000); // Includes bounded original aim initialization plus battle ticks.',
        f'  }}, {wall_seconds*1000}); // Bounded original real-time loading and selected encounter ticks.',
        'selected encounter overall watchdog')
    for name in ['CAPTURED_REPLAY_INPUT','CAPTURED_REPLAY_EXPECTED','CAPTURED_FIXTURE_INPUT',
                 'PRACTICE_MODE_INPUT','PRACTICE_RNG_EXPECTED','PRACTICE_RNG_EXPECTED_SHA256','PRACTICE_REFERENCE_SELECTION',
                 'MECHANICS_GEOMETRY_SOURCE','MECHANICS_GEOMETRY_SOURCE_SHA256']:
        source,count=re.subn(r'^globalThis\.'+name+r'=.*;\n','',source,flags=re.MULTILINE)
        if name!='PRACTICE_REFERENCE_SELECTION' and count!=1:raise ValueError('Frozen input assignment changed: '+name)
    binding=json.loads((HERE/'native-build-binding153.json').read_text())
    geometry_module=load_module(ENCOUNTERS/'geometry_inputs153.py','native_encounter_geometry_inputs153')
    geometry,geometry_selection=geometry_module.prepare_geometry(release,encounter)
    geometry_path=root/'encounter-geometry-input.json';geometry_sha=write_json(geometry_path,geometry)
    tactical_binding_path=ENCOUNTERS/'tactical/tactical-binding-final.json'
    authored_path=HERE.parent/'kraken153-qte-cover-source.json'
    values={'NATIVE_BATTLE_REQUEST_SHA256':request_sha,'NATIVE_BATTLE_INPUT':build,
        'CUSTOM_NATIVE_FIXTURE':fixture,'PRACTICE_MODE_INPUT':mode,
        'NATIVE_BUILD_BINDING153':binding,
        'NATIVE153_ENCOUNTER_BINDING':json.loads((ENCOUNTERS/'encounter-binding153.json').read_text()),
        'NATIVE153_CAMPAIGN_BINDING':json.loads((ENCOUNTERS/'campaign-binding153.json').read_text()),
        'NATIVE153_GEOMETRY_BINDING':json.loads((ENCOUNTERS/'geometry-binding153.json').read_text()),
        'NATIVE153_GEOMETRY_SELECTION':geometry_selection,
        'MECHANICS_GEOMETRY_SOURCE':geometry,'MECHANICS_GEOMETRY_SOURCE_SHA256':geometry_sha,
        'NATIVE153_TACTICAL_BINDING':json.loads(tactical_binding_path.read_text()),
        'NATIVE153_TACTICAL_BINDING_SHA256':digest(tactical_binding_path.read_bytes()),
        'KRAKEN153_AUTHORED_RULE':json.loads(authored_path.read_text()),
        'KRAKEN153_AUTHORED_RULE_SHA256':digest(authored_path.read_bytes())}
    if request.get('settings',{}).get('native_fx_quality') is not None:
        baseline=json.loads((release.directory/'frozen/frozen-settingsInput.json').read_text())
        derived,graphics_receipt=derive_quality_input(baseline,request['settings']['native_fx_quality'])
        if request['settings'].get('native_postprocess_flags') is not None:
            derived,postprocess_receipt=derive_postprocess_input(derived)
            graphics_receipt.update(postProcess=postprocess_receipt,
                finalDerivedInputCanonicalSha256=postprocess_receipt['derivedInputCanonicalSha256'],
                finalDerivedVideoRawHex=postprocess_receipt['derivedVideoRawHex'])
            values['NATIVE153_POSTPROCESS_OVERRIDE_INPUT']=postprocess_receipt
        write_json(root/'derived-graphics-settings.json',derived)
        write_json(root/'derived-graphics-receipt.json',graphics_receipt)
        values['PRACTICE_SETTINGS_INPUT']=derived
        values['NATIVE153_GRAPHICS_BASELINE_INPUT']=baseline['settings']['VideoSetting']
        values['NATIVE153_GRAPHICS_OVERRIDE_INPUT']=graphics_receipt
    values['NATIVE153_REQUESTED_VIEWPORT']=viewport
    values['NATIVE153_RENDER_INTERVAL_INPUT']={'interval':request.get('settings',{}).get('native_render_interval',1)}
    values['NATIVE153_LATEUPDATE_OWNERS_INPUT']=request.get('settings',{}).get('native_lateupdate_owners',False)
    values['NATIVE153_PLAYERLOOP_TIMING_INPUT']=request.get('settings',{}).get('native_playerloop_timing',False)
    values['NATIVE153_PROFILER_RECORDERS_INPUT']=request.get('settings',{}).get('native_profiler_recorders',False)
    values['NATIVE153_UNITY_SCOPE_PROFILE_INPUT']=request.get('settings',{}).get('native_unity_scope_profile',False)
    values['NATIVE153_CLEAN_PROFILE_INPUT']=request.get('settings',{}).get('native_clean_profile',False)
    values['NATIVE153_STARTUP_SKIP_INPUT']=request.get('settings',{}).get('native_startup_skip',False)
    values['NATIVE153_COHERENT_CAPTURE_INPUT']={'enabled':request.get('settings',{}).get('native_coherent_capture',False)}
    values['NATIVE153_JS_RUNTIME_EXPECTED']=request.get('settings',{}).get('native_js_runtime','default')
    values['NATIVE153_FRAME_PROFILE_INPUT']={'enabled':request.get('settings',{}).get('native_frame_profile',False),'warmupSeconds':request.get('settings',{}).get('native_frame_profile_warmup_seconds',0),'fullBattleValidation':request.get('settings',{}).get('native_full_validation',False)}
    values['NATIVE153_SPEED_INPUT']={'multiplier':request.get('settings',{}).get('native_speed_multiplier',1)}
    values['NATIVE153_EVENT_PREFILTER_INPUT']=request.get('settings',{}).get('native_event_prefilter',False)
    for name,value in values.items():source+='\nglobalThis.'+name+'='+encoded(value).decode()+';\n'
    for name in ['native_build153.js','native_rng_observer153.js']:
        path=HERE/name;source+='\n'+path.read_text()+'\n'
        source_hashes[name]={'path':str(path),'sha256':digest(path.read_bytes())}
    for relative in ['encounter_mode153.js','original_ui_score153.js','native_campaign153.js','encounter_team153.js',
        'tactical/native153_tactical_binding.js','tactical/mechanics_virtual_pointer.js',
        'tactical/mechanics_tactical_actions.js','tactical/mechanics_tactical_observer.js',
        'tactical/mechanics_threat_observer.js','tactical/mechanics_breakable_observer.js',
        'tactical/mechanics_firing_policy.js','tactical/mechanics_interception_policy.js','tactical/mechanics_indivilia_cover.js','tactical/mechanics_mirror_exposure.js','tactical/mechanics_mirror_policy.js','tactical/mechanics_harvester_target_cover.js','tactical/mechanics_interception_threat_targets.js','tactical/kraken_part_priority.js','tactical/kraken_core_observer.js',
        'tactical/mechanics_qte_actor_evidence.js','tactical/mechanics_qte_policy.js','tactical/mechanics_cover_policy.js',
        'tactical/mechanics_timeline_cover_observer.js','tactical/native153_tactical_controller.js']:
        path=ENCOUNTERS/relative;source+='\n'+path.read_text()+'\n'
        source_hashes[relative]={'path':str(path),'sha256':digest(path.read_bytes())}
    # Original minimum startup plus original dependency-aware demand loading.
    # Avoid materializing hundreds of unrelated tables in every private player.
    source=replace_once(source,
        'manager.method("InitializeAndLoadAllAsync",1)',
        'manager.method("InitializeMinimumAsync",1)', 'minimum table startup')
    modules[1]=source.encode();headers[2]=str(len(modules[1]))+' /src/nmm_030.js'
    bundle='\n'.join(headers).encode()+DELIMITER+DELIMITER.join(modules)
    bundle_path=root/'custom-scene-probe.js';bundle_path.write_bytes(bundle)
    config=json.loads(release.file('configTemplateFile').read_text())
    if viewport is not None:
        # A matched camera viewport needs the original graphics device. The
        # no-graphics launch retained stale Screen dimensions despite these
        # startup arguments. Rendering remains on the isolated desktop.
        args=[arg for arg in config.get('args',[]) if arg.lower() not in ('-batchmode','-nographics')]
        if any(arg.lower() in ('-screen-fullscreen','-screen-width','-screen-height') for arg in args):
            raise ValueError('Frozen config already defines viewport startup options')
        config['args']=args+['-screen-fullscreen','0','-screen-width',str(viewport['width']),
                             '-screen-height',str(viewport['height'])]
    config['output_dir']=str(root/'output')
    config['max_seconds']=wall_seconds
    config['diagnostic_files']['NKAB/dist/scene-probe.js']['sha256']=digest(bundle)
    staging=copy.deepcopy(json.loads(release.file('stagingTemplateFile').read_text()))
    for key in ['captureSha256','matchedReferenceSelection','lastActualNativeArchive','sourcePredecessorArchive']:
        staging.pop(key,None)
    staging.update(schemaVersion=1,requestSha256=request_sha,inputSourceSha256=fixture_sha,
        characters=identities,encounter=encounter,scope='Custom selected native encounter/team/build; no reference comparison',
        sourceSha256=digest(source.encode()),fullSharedRngStateRequired=False,
        clockMode=('diagnostic_original_capture60_source_scoped_delta' if request.get('settings',{}).get('native_coherent_capture') else 'original_real_time_no_clock_or_animator_patches'),wallBudgetSeconds=wall_seconds,
        customSharedRngObservationRequired=True,referenceCompared=False,nativeRunPerformed=False,
        fullAccuracyVerified=False,productionIntegrated=True,originalResultFilename=release.data['packetBasename'])
    staging['sources'].update(source_hashes)
    staging['sources']['customNativeBuildInput']={'path':str(build_path),'sha256':build_sha}
    staging['sources']['customFixtureInput']={'path':str(fixture_path),'sha256':fixture_sha}
    staging['sources']['encounterGeometryInput']={'path':str(geometry_path),'sha256':geometry_sha}
    return {'bundlePath':bundle_path,'staging':staging,'config':config,'characters':identities,
        'identities':[(x['tableId'],x['nameCode']) for x in identities],
        'inputSourceSha256':fixture_sha,'requestSha256':request_sha,'mode':mode,'encounter':encounter}
