'use strict';
// Review-only current153 practice adapter. Not installed into the host yet.
// No native result/state/damage writes, constructor emulation or score math.
const NATIVE153_PRACTICE = Object.freeze({
  clientSha256:'d39896d3770888039c728a1908448c3db5efa7cdf874c90d56f46d8d566428d2',
  processMetadataSha256:'55a5d5538e2d61620ad0603ffdd538ea74a77eed834d4c6e40b1ee1fab6fe61b',
  rangeEntrySha256:'8bc6b24b343b8518592598b92838543067f8c7b080434b655ec5b32f81663a1b',
  waveEntrySha256:'f3e2f59946ecf4d7a0bbefef5a3809f47ec4dd89386029702d7d24857a8dd2d0',
  processClass:'NK.Spot.Context.Process.ShootingRangeProcess',
  parentClass:'NK.Spot.Context.Process.CampaignProcess',
  ctor:0x0712fbd0,createContext:0x07122f90,setProcess:0x07607310,
  spotFinish:0x07607390,antiCheatBattleDataInit:0x0727a4c0,
  playStates:Object.freeze({Playing:6,Clear:8,Fail:9,Finish:10,LoadingStart:2,LoadingComplete:3})
});

function validateNative153PracticeInput(input) {
  const binding=NATIVE153_PRACTICE;
  if (!input || input.schemaVersion!==1 || input.clientSha256!==binding.clientSha256 ||
      input.processMetadataSha256!==binding.processMetadataSha256 ||
      input.rangeEntrySha256!==binding.rangeEntrySha256 || input.waveEntrySha256!==binding.waveEntrySha256 ||
      !/^[a-f0-9]{64}$/.test(input.inputSourceSha256||'') ||
      input.rangeId!==1 || input.waveId!==6801001 || input.processType!==9 ||
      input.transporterProcessType!==0 || input.managementType!==0 || input.teamNumber!==0 ||
      input.timeLimit!==90 || input.teamType!==24 || input.specActive!==false ||
      !Number.isInteger(input.randomSeed) || input.randomSeed<1 || input.randomSeed>2147483647 ||
      !Array.isArray(input.characters) || input.characters.length!==5 || input.characters.some(row=>
        !row || !Number.isSafeInteger(row.tableId) || row.tableId<=0 ||
        !Number.isSafeInteger(row.nameCode) || row.nameCode<=0))
    throw Error('Practice mode requires the exact captured current153 normal Fire/Short input binding');
  return input;
}

function native153PracticeMethod(klass,name,args,rva) {
  const method=klass.method(name,args);
  if (Number(method.relativeVirtualAddress)!==rva)
    throw Error('Practice original method binding changed: '+klass.type.name+'::'+name);
  return method;
}

function verifyNative153PracticeTransporter(input,readback) {
  validateNative153PracticeInput(input);
  if (!readback || readback.transporterValueTypeSize!==376 ||
      (readback.valueTypeSize!==undefined && readback.valueTypeSize!==376) ||
      readback.processType!==0 || readback.managementType!==0 || readback.teamNumber!==0 ||
      readback.waveId!==6801001 || readback.timeLimit!==90 || readback.teamType!==24 ||
      readback.randomSeed!==input.randomSeed)
    throw Error('Original sized current153 practice transporter readback does not match mode input');
  return true;
}

function createOriginal153PracticeProcess(runtime,staticImage,management,pin,emit,input,transporterReadback) {
  validateNative153PracticeInput(input);
  verifyNative153PracticeTransporter(input,transporterReadback);
  const call=(method,self=null,args=[])=>invokeChecked(method,self,args);
  const i32=(method,self)=>call(method,self).unbox().handle.readS32();
  const live=value=>value!=null&&!value.isNull();
  const enumValue=(klass,name)=>{
    const value=klass.field(name).value;
    return typeof value==='number'?value:Number(value.field('value__').value);
  };
  if (enumValue(staticImage.class('NK.StaticData.SpotModType'),'ShootingRange')!==9)
    throw Error('Current original ShootingRange process enum changed');
  const klass=runtime.class(NATIVE153_PRACTICE.processClass);
  if (!klass.parent || klass.parent.type.name!==NATIVE153_PRACTICE.parentClass)
    throw Error('Original ShootingRangeProcess no longer derives from CampaignProcess');
  const parent=runtime.class(NATIVE153_PRACTICE.parentClass);
  const process=pin(klass.alloc());
  call(native153PracticeMethod(klass,'.ctor',1,NATIVE153_PRACTICE.ctor),process,[intArg(9)]);
  call(native153PracticeMethod(runtime.class('NK.Spot.SpotManagement'),'SetProcess',1,
    NATIVE153_PRACTICE.setProcess),management,[process.handle]);
  const retained=management.field('_process').value;
  if (!live(retained) || !retained.handle.equals(process.handle))
    throw Error('Original manager did not retain original ShootingRangeProcess');
  if (i32(process.method('get_ProcessType',0),process)!==9)
    throw Error('Original practice process type readback differs');
  // Observe the original constructor's actual lists. Do not copy Intercept
  // conditions or change these lists to make an encounter finish.
  const readList=name=>{
    const list=process.field(name).value;
    if (!live(list)) throw Error('Original practice condition list is null: '+name);
    const count=i32(list.method('get_Count',0),list),values=[];
    if (count<0||count>16) throw Error('Unexpected original condition list size');
    for(let index=0;index<count;index++)
      values.push(call(list.method('get_Item',1),list,[intArg(index)]).unbox().handle.readS32());
    return values;
  };
  const clearConditions=readList('ClearConditionList'),failConditions=readList('FailConditionList');
  const conditions=runtime.class('NK.Spot.Logic.Process.ProcessConditionType');
  const wanted=['AllMonsterDead','TimeOut','AllCharacterDead'].map(name=>enumValue(conditions,name));
  if (wanted.join('|')!=='1|0|2' || clearConditions.join('|')!==wanted.join('|') || failConditions.length!==0)
    throw Error('Original ShootingRangeProcess constructor conditions changed');
  call(native153PracticeMethod(parent,'CreateContext',0,NATIVE153_PRACTICE.createContext),process);
  emit({status:'original_practice_context_created',processClass:klass.type.name,
    parentClass:parent.type.name,processType:9,clearConditions,failConditions,
    originalConstructorInvoked:true,originalCampaignCreateContextInvoked:true,
    conditionsUnchanged:true,inputSourceSha256:input.inputSourceSha256,
    fullAccuracyVerified:false});
  return process;
}

function readOriginal153PracticeLifecycle(runtime,process) {
  const base=runtime.class('NK.Spot.Context.Process.ProcessBase');
  const call=(name,rva)=>invokeChecked(native153PracticeMethod(base,name,0,rva),process).unbox().handle;
  const state=call('get_State',0x009069d0).readS32();
  return {processClass:process.class.type.name,processType:call('get_ProcessType',0x017690a0).readS32(),
    state,stateName:Object.keys(NATIVE153_PRACTICE.playStates)
      .find(name=>NATIVE153_PRACTICE.playStates[name]===state)||'other_native_state',
    playTime:call('get_PlayTime',0x0099f6e0).readFloat(),
    battleTime:call('get_BattleTime',0x009069c0).readFloat(),
    battleTickCount:Number(process.field('_battleTickCount').value)};
}

function installOriginal153PracticeResultCapture(runtime,team,pin,emit,input,callbacks) {
  validateNative153PracticeInput(input);
  if (!callbacks || typeof callbacks.setOriginalFinishObserver!=='function')
    throw Error('Practice result capture requires the typed synchronous original finish callback boundary');
  if (typeof installOriginal153PracticeBattleResultCapture!=='function')
    throw Error('The reviewed current153 original result reader is required');
  const finish=native153PracticeMethod(runtime.class('NK.Spot.SpotManagement'),'SpotFinish',1,
    NATIVE153_PRACTICE.spotFinish);
  const originalPacket=native153PracticeMethod(runtime.class('NK.BattleResult'),'AntiCheatBattleDataInit',0,
    NATIVE153_PRACTICE.antiCheatBattleDataInit);
  const capture=installOriginal153PracticeBattleResultCapture(runtime,team,pin,emit);
  let originalResult=null,returned=false,fault=null,packetReadback=null,originalPacketData=null;
  let callbackAttempted=false,callbackCaptured=false;
  const listener=Interceptor.attach(finish.virtualAddress,{
    onEnter(args) {
      try {
        if (originalResult) throw Error('Duplicate original practice SpotFinish');
        if (args[1].isNull()) throw Error('Original practice SpotFinish result is null');
        const result=new Il2Cpp.Object(args[1]);
        if (result.class.type.name!=='NK.BattleResult') throw Error('Practice result is not original NK.BattleResult');
        originalResult=pin(result);
      } catch(error) {fault=error;}
    },
    onLeave() {returned=true;}
  });
  const call=(method,self=null,args=[])=>invokeChecked(method,self,args);
  const integer=(object,name)=>call(object.method('get_'+name,0),object).unbox().handle.readS32();
  const listCount=(object,name)=>{
    const list=call(object.method('get_'+name,0),object);
    if (list==null||list.isNull()) throw Error('Original practice packet list is null: '+name);
    return integer(list,'Count');
  };
  callbacks.setOriginalFinishObserver(value=>{
    try {
      if (fault) throw fault;
      if (callbackAttempted) throw Error('Duplicate original practice finish callback capture');
      callbackAttempted=true;
      if (!originalResult || returned || value==null || value.isNull() ||
          value.class.type.name!=='NK.BattleResult' ||
          !value.handle.equals(originalResult.handle))
        throw Error('Practice finish callback differs from the active original SpotFinish result');
      if (typeof capture.captureBeforeCleanup!=='function')
        throw Error('Practice result reader lacks the original pre-cleanup statistics boundary');
      capture.captureBeforeCleanup(value);
      // The original shooting-range request builder does this synchronously
      // inside OnBattleFinish, before SpotFinish calls manager.OnDestroy.
      // Monster projection depends on live key.Data/Movement references.
      const packet=pin(call(originalPacket,originalResult));
      if (packet==null||packet.isNull()||packet.class.type.name!=='NK.Network.Packet.Lobby.NetAntiCheatBattleData')
        throw Error('Original practice result did not produce typed anti-cheat data');
      originalPacketData=packet;
      packetReadback=Object.freeze({source:'original_BattleResult_AntiCheatBattleDataInit',
        waveId:integer(packet,'WaveId'),battleDuration:integer(packet,'BattleDuration'),
        characterCount:listCount(packet,'Characters'),monsterCount:listCount(packet,'Monsters')});
      callbackCaptured=true;
      emit({status:'original_practice_packet_captured_before_cleanup',
        originalAntiCheat:packetReadback,originalPacketRetained:true,
        callbackResultMatchesSpotFinish:true,fullAccuracyVerified:false});
    } catch(error) {
      fault=error;
      try {
        emit({status:'original_practice_finish_capture_failed',
          stage:'original_typed_finish_callback_before_cleanup',error:String(error),
          nativeFrames:error?.nativeFrames||[],completeOriginalPacket:false,
          resultCaptured:false,fullAccuracyVerified:false});
      } catch(receiptError) {
        // A diagnostic sink failure must not replace the native exception.
        // The host's typed callback latch receives the original error below.
      }
      // The typed host boundary latches this; native cleanup proceeds normally.
      // captureTerminal also preserves the original failure instead of retrying.
      throw error;
    }
  });
  return {
    captureTerminal(processState) {
      if (fault) throw fault;
      const result=capture(processState);
      if (result.pending===true || !returned || !originalResult) return {pending:true,resultCaptured:false};
      if (!callbackCaptured || !packetReadback || !originalPacketData)
        throw Error('Original practice packet was not captured in the finish callback before cleanup');
      // Boss kill/HP semantics do not define practice completion. Preserve raw
      // target fields, but omit the old Intercept reader's inferred bossKilled.
      const {bossKilled,terminalCause,...original}=result;
      return {...original,originalAntiCheat:packetReadback,
        processStateResultBinding:'unverified',terminalCause:'unverified',
        inputSourceSha256:input.inputSourceSha256,practiceMode:true,
        statisticsAndPacketCapturedBeforeCleanup:true,fullAccuracyVerified:false};
    },
    // Same-process pinned original DTO for an independently reviewed original
    // protobuf serializer. Its reference must never become a replay input.
    getOriginalPacket() { return originalPacketData; },
    retainUntilExit:listener
  };
}

function verifyOriginal153PracticeTerminal(input,result,evidence) {
  const errors=[];
  try { validateNative153PracticeInput(input); } catch(error) {errors.push(String(error));}
  const e=evidence||{},r=result||{},packet=r.originalAntiCheat||{};
  if (e.processClass!==NATIVE153_PRACTICE.processClass || e.processType!==9 ||
      e.transporterProcessType!==0 || e.managementType!==0 || e.teamNumber!==0 ||
      e.waveId!==6801001 || e.timeLimit!==90 || e.teamType!==24 || e.randomSeed!==input?.randomSeed)
    errors.push('Original practice process/transporter/seed readbacks differ from captured input');
  if (e.inputReadbackPassed!==true || e.inputSourceSha256!==input?.inputSourceSha256)
    errors.push('Original input reconstruction readback has not passed for this source');
  if (e.observedPlaying!==true || !Number.isInteger(e.advancedTicks) || e.advancedTicks<=0 ||
      ![8,9,10].includes(e.processState) || r.processState!==e.processState)
    errors.push('No observed playing clock followed by original Clear/Fail/Finish state');
  if (r.resultCaptured!==true || r.originalResult!==true || r.resultType!=='NK.BattleResult' ||
      ![1,2].includes(r.result) || !Number.isInteger(r.spotResult) || r.retreat!==false)
    errors.push('No original non-abort practice BattleResult');
  if (packet.source!=='original_BattleResult_AntiCheatBattleDataInit' || packet.waveId!==6801001 ||
      packet.battleDuration!==90000 || packet.characterCount!==5 ||
      !Number.isInteger(packet.monsterCount) || packet.monsterCount<=0)
    errors.push('Original result packet lacks populated five-player 90-second practice statistics');
  if (!Array.isArray(r.rounds) || r.rounds.length!==1 ||
      !Number.isFinite(r.rounds[0]?.duration) || r.rounds[0].duration<=0 ||
      !/^[1-9][0-9]*$/.test(r.rounds[0]?.squadTotal||''))
    errors.push('Original practice statistics round or native positive damage getter is missing');
  const actors=e.originalActors,members=r.rounds?.[0]?.characters;
  const validRows=rows=>Array.isArray(rows)&&rows.length===5&&rows.every(row=>row&&
    Number.isSafeInteger(row.entityId)&&row.entityId>0&&Number.isSafeInteger(row.tableId)&&row.tableId>0&&
    Number.isSafeInteger(row.nameCode)&&row.nameCode>0);
  if (!validRows(actors) || !validRows(members) ||
      new Set(actors?.map(row=>row.entityId)).size!==5 ||
      new Set(members?.map(row=>row.entityId)).size!==5)
    errors.push('Original ordered actors/statistics identities are incomplete');
  else {
    for(let index=0;index<5;index++) {
      const actor=actors[index],expected=input?.characters?.[index];
      const member=members.find(row=>row.entityId===actor.entityId);
      if (!expected||!member||actor.tableId!==expected.tableId||actor.nameCode!==expected.nameCode||
          member.tableId!==actor.tableId||member.nameCode!==actor.nameCode)
        errors.push('Original actor/statistics identity differs at ordered slot '+(index+1));
    }
  }
  return {passed:errors.length===0,errors,completeNativePractice:errors.length===0,
    inputSourceSha256:input?.inputSourceSha256,processState:e.processState,
    originalResult:r.result,originalSpotResult:r.spotResult,
    processStateResultBinding:'unverified',terminalCause:'unverified',
    bossHpRequired:false,scoreCalculated:false,fullAccuracyVerified:false};
}

function compareOriginal153PracticeReference(input,result,completion,reference) {
  const errors=[];
  if (completion?.passed!==true) errors.push('Native practice completion is not verified');
  if (!reference || reference.inputSourceSha256!==input?.inputSourceSha256 ||
      reference.rangeId!==1 || reference.waveId!==6801001 || reference.battleDuration!==90000 ||
      reference.battleResult!==1 || !/^[1-9][0-9]*$/.test(reference.score||''))
    errors.push('Reference is not the hash-bound original normal Fire90s request');
  if (result?.result!==reference?.battleResult ||
      result?.originalAntiCheat?.battleDuration!==reference?.battleDuration ||
      result?.rounds?.[0]?.squadTotal!==reference?.score)
    errors.push('Original native result/raw damage getter differs from original reference request');
  return {passed:errors.length===0,errors,comparison:'original_native_getters_vs_original_client_request',
    scoreCalculated:false,processStateResultBinding:'unverified',fullAccuracyVerified:false};
}
