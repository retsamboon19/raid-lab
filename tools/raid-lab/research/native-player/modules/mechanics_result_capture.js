// Passive, typed capture of the ORIGINAL BattleResult. No result constructor,
// process-state write, finish substitution, or inferred zero statistics.
function installMechanicsResultCapture(runtime, team, pin, emit) {
  const klass=runtime.class("NK.Spot.SpotManagement");
  const finish=klass.method("SpotFinish",1);
  if (Number(finish.relativeVirtualAddress)!==0x0614bc60) {
    throw new Error("Installed SpotFinish does not match result contract");
  }
  let result=null, terminalSnapshot=null, returned=false, fault=null;
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
  if (Number(isAlive.relativeVirtualAddress)!==0x0638c660) {
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
  // This private fixture is the ordinary player/Red Intercept team. The Blue
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
      } catch(error) {fault=String(error);}
    },
    onLeave() {returned=true;}
  });
  return function captureTerminal(processState) {
    if (fault) throw new Error(fault);
    if (!result || !returned) return {pending:true,resultCaptured:false};
    if (!terminalSnapshot) throw new Error("Original SpotFinish terminal snapshot is missing");
    const rounds=pin(call(result.method("get_SpotStatisticsData",0),result));
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
    const bossKilled=BigInt(terminalSnapshot.targetRemainHp)===0n;
    // BattleResult.Timeout is not the originating condition: trial 70 ended
    // at its 180-second limit with Timeout=false. A source-event hook is
    // required before assigning a terminal cause.
    const terminalCause="unknown";
    return {resultCaptured:true,originalResult:true,processState,playerCamp:camp,
      resultType:"NK.BattleResult",result:enumNumber(result.field("Result").value),
      spotResult:int(result.method("get_SpotResult",0),result),
      timeout:terminalSnapshot.timeout,retreat:Boolean(result.field("Retreat").value),
      targetRemainHp:terminalSnapshot.targetRemainHp,targetMaxHp:terminalSnapshot.targetMaxHp,
      rawRosterCount:terminalSnapshot.rawRosterCount,
      survivingPlayerCount:terminalSnapshot.survivingPlayerCount,
      deadListCount:terminalSnapshot.deadListCount,bossKilled,terminalCause,
      rounds:data,fullAccuracyVerified:false};
  };
}
