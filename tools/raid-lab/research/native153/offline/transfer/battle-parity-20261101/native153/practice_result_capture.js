// Current153 practice result observation; native execution/parity unverified.
// Passive, typed capture of the ORIGINAL BattleResult. No result constructor,
// process-state write, finish substitution, or inferred zero statistics.
function installOriginal153PracticeBattleResultCapture(runtime, team, pin, emit) {
  const klass=runtime.class("NK.Spot.SpotManagement");
  const finish=klass.method("SpotFinish",1);
  if (Number(finish.relativeVirtualAddress)!==0x07607390) {
    throw new Error("Installed SpotFinish does not match result contract");
  }
  // Fresh current153-run3 metadata. These are original NK.BattleResult getters,
  // rather than historical result-wrapper offsets or calculated replacements.
  const resultClass=runtime.class("NK.BattleResult");
  const originalGetter=(name,rva)=>{
    const method=resultClass.method(name,0);
    if (Number(method.relativeVirtualAddress)!==rva)
      throw new Error("Installed original result getter changed: "+name);
    return method;
  };
  const statisticsGetter=originalGetter("get_SpotStatisticsData",0x0727e7b0);
  const spotResultGetter=originalGetter("get_SpotResult",0x0727e770);
  let result=null, terminalSnapshot=null, returned=false, fault=null;
  let preCleanupSnapshot=null,snapshotAttempted=false;
  const live=value=>value!=null && !value.isNull();
  const call=(method,self=null,args=[])=>invokeChecked(method,self,args);
  const int=(method,self)=>call(method,self).unbox().handle.readS32();
  const long=(method,self)=>call(method,self).unbox().handle.readS64().toString();
  const enumNumber=value=>typeof value==="number"?value:Number(value.field("value__").value);
  const hpValue=(value,name)=>{
    const hp=value.field(name).value.field("Value").value.toString();
    if (!/^-?\d+$/.test(hp)) throw new Error("Invalid original "+name+" value "+hp);
    return hp;
  };
  const isAlive=runtime.class("NK.Spot.Model.Common.SpotEntity").method("IsAlive",0);
  if (Number(isAlive.relativeVirtualAddress)!==0x066E1F00) {
    throw new Error("Installed SpotEntity.IsAlive does not match result contract");
  }
  const listCount=(name)=>{
    const list=team.field(name).value;
    if (!live(list)) throw new Error("Original team "+name+" list is null at SpotFinish");
    const count=int(list.method("get_Count",0),list);
    if (count<0 || count>5) throw new Error("Invalid original team "+name+" count "+count);
    return count;
  };
  const teamCounts=()=>{
    const roster=team.field("<CharacterList>k__BackingField").value;
    if (!live(roster)) throw new Error("Original CharacterList is null at SpotFinish");
    const rawRosterCount=listCount("<CharacterList>k__BackingField");
    let survivingPlayerCount=0;
    for (let index=0;index<rawRosterCount;index++) {
      const character=call(roster.method("get_Item",1),roster,[intArg(index)]);
      if (!live(character)) throw new Error("Null original roster character at "+index);
      if (call(isAlive,character).unbox().handle.readU8()) survivingPlayerCount++;
    }
    return {rawRosterCount,deadListCount:listCount("_deadCharacterList"),
      survivingPlayerCount};
  };
  const camp=enumNumber(team.field("<CampType>k__BackingField").value);
  const red=enumNumber(runtime.class("NK.Spot.Model.Character.SpotCharacter")
    .nested("CampType").field("Red").value);
  // This adapter reads the ordinary player/Red practice team. The Blue
  // total has a different original wrapper; reject it rather than reinterpret.
  if (camp!==red) throw new Error("Result capture currently supports original Red player team only");
  Interceptor.attach(finish.virtualAddress,{
    onEnter(args) {
      try {
        if (result) throw new Error("Duplicate original terminal result");
        if (args[1].isNull()) throw new Error("Original SpotFinish has no result");
        const value=new Il2Cpp.Object(args[1]);
        if (value.class.type.name!=="NK.BattleResult") {
          throw new Error("Unsupported original result type "+value.class.type.name);
        }
        result=pin(value);
        // CharacterList is a roster, not a live-only collection. Use the
        // original SpotEntity.IsAlive for each character before cleanup.
        terminalSnapshot={...teamCounts(),
          targetRemainHp:hpValue(value,"TargetMonsterRemainHP"),
          targetMaxHp:hpValue(value,"TargetMonsterMaxHP"),
          timeout:Boolean(value.field("Timeout").value)};
        emit({status:"original_battle_result_observed",resultType:value.class.type.name,
          resultCaptured:false});
      } catch(error) {fault=error;}
    },
    onLeave() {returned=true;}
  });
  function readOriginalStatistics() {
    if (!terminalSnapshot) throw new Error("Original SpotFinish terminal snapshot is missing");
    const rounds=pin(call(statisticsGetter,result));
    if (!live(rounds)) throw new Error("Original result statistics list is null");
    const roundCount=int(rounds.method("get_Count",0),rounds);
    if (roundCount<1 || roundCount>32) throw new Error("Invalid original statistics round count "+roundCount);
    const data=[];
    for (let index=0;index<roundCount;index++) {
      const round=call(rounds.method("get_Item",1),rounds,[intArg(index)]);
      if (!live(round)) throw new Error("Null original statistics round");
      const members=round.field("RedTeamData").value;
      if (!live(members)) throw new Error("Original player statistics dictionary is null");
      const memberCount=int(members.method("get_Count",0),members);
      if (memberCount<1 || memberCount>5) throw new Error("Unexpected original player statistics count");
      const iteratorBox=pin(call(members.method("GetEnumerator",0),members));
      const iterator=iteratorBox.unbox();
      const characters=[];
      while (call(iterator.method("MoveNext",0),iterator).unbox().handle.readU8()) {
        if (characters.length>=memberCount) throw new Error("Statistics enumeration exceeds Count");
        const pair=pin(call(iterator.method("get_Current",0),iterator)).unbox();
        const entityId=int(pair.method("get_Key",0),pair);
        const character=call(pair.method("get_Value",0),pair);
        if (!live(character)) throw new Error("Null original character statistics");
        const info=character.field("InfoData").value;
        if (!live(info)) throw new Error("Original character statistics have no identity");
        const source=info.field("UserCharacterData").value;
        if (!live(source)) throw new Error("Original character statistics lack source build");
        const staticInfo=call(source.method("get_CharacterStaticInfo",0),source);
        if (!live(staticInfo)) throw new Error("Original character static info is null");
        characters.push({entityId,statisticsId:Number(info.field("Id").value),
          tableId:int(staticInfo.method("get_TableId",0),staticInfo),
          nameCode:int(staticInfo.method("get_NameCode",0),staticInfo),
          outgoingDamage:long(character.method("get_TakeTotalDamage",0),character),
          outgoingActualDamage:long(character.method("get_TakeTotalActualDamage",0),character)});
      }
      if (characters.length!==memberCount) throw new Error("Incomplete original character statistics");
      const duration=Number(round.field("PlayTime").value);
      if (!Number.isFinite(duration) || duration<=0) throw new Error("Original battle duration is not positive");
      data.push({index,duration,isWin:Boolean(round.field("IsWin").value),
        squadTotal:long(round.method("get_AllRedTeamTotalDamage",0),round),characters});
    }
    // Keep original target HP and Timeout raw. Neither identifies a practice
    // ending condition; this observer makes no boss-kill/result-state inference.
    const terminalCause="unverified";
    return {resultCaptured:true,originalResult:true,playerCamp:camp,
      resultType:"NK.BattleResult",result:enumNumber(result.field("Result").value),
      spotResult:int(spotResultGetter,result),
      timeout:terminalSnapshot.timeout,retreat:Boolean(result.field("Retreat").value),
      targetRemainHp:terminalSnapshot.targetRemainHp,targetMaxHp:terminalSnapshot.targetMaxHp,
      rawRosterCount:terminalSnapshot.rawRosterCount,
      survivingPlayerCount:terminalSnapshot.survivingPlayerCount,
      deadListCount:terminalSnapshot.deadListCount,terminalCause,
      rounds:data,fullAccuracyVerified:false};
  }
  function captureTerminal(processState) {
    if (fault) throw fault;
    if (!result || !returned) return {pending:true,resultCaptured:false};
    if (!preCleanupSnapshot)
      throw new Error('Original practice statistics were not captured in the finish callback before cleanup');
    // All native getter/field reads occurred in the original callback window.
    return {...preCleanupSnapshot,processState};
  }
  captureTerminal.captureBeforeCleanup=observedResult=>{
    try {
      if (fault) throw fault;
      if (!result || returned || !live(observedResult) ||
          observedResult.class.type.name!=='NK.BattleResult' ||
          !observedResult.handle.equals(result.handle))
        throw new Error('Original statistics capture requires the same active SpotFinish callback result');
      if (snapshotAttempted) throw new Error('Duplicate original pre-cleanup statistics capture');
      snapshotAttempted=true;
      const freeze=value=>{
        if (value!==null&&typeof value==='object') {
          for (const child of Object.values(value)) freeze(child);
          Object.freeze(value);
        }
        return value;
      };
      preCleanupSnapshot=freeze(readOriginalStatistics());
      emit({status:'original_practice_statistics_captured_before_cleanup',
        statistics:preCleanupSnapshot,completeOriginalPacket:false,
        originalStatisticsGettersRead:true,fullAccuracyVerified:false});
      return preCleanupSnapshot;
    } catch(error) {fault=error;throw error;}
  };
  return captureTerminal;
}
