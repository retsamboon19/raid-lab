// Original result lifetime contracts only. No Unity process/native methods run.
const assert=require('node:assert/strict'),fs=require('node:fs'),vm=require('node:vm');
let checks=0;
function check(value,label){assert.ok(value,label);checks++;}
function harness(options={}) {
  const listeners=[],emitted=[],calls=[],order=[],objects=new Map();
  let observer=null,registrations=0,afterCleanup=false;
  const pointer=id=>({id,isNull:()=>false,equals:other=>other?.id===id});
  const method=(name,rva=0)=>({name,relativeVirtualAddress:rva,virtualAddress:pointer(rva)});
  const box=value=>({unbox:()=>({handle:{readS32:()=>Number(value),readU8:()=>Number(value),
    readS64:()=>({toString:()=>String(value)})}})});
  let serial=1;
  const object=(name,fields={},extra={})=>{
    const value={handle:pointer(serial++),class:{type:{name}},isNull:()=>false,
      field:key=>({value:fields[key]}),method:key=>method(key),...extra};
    objects.set(value.handle.id,value);return value;
  };
  const list=rows=>object('List',{}, {rows});
  const actors=Array.from({length:5},(_,index)=>({entityId:4096+index,tableId:100+index,nameCode:5000+index}));
  const members=actors.map((actor,index)=>{
    const info=object('CharacterStaticInfo',{},actor);
    const source=object('CharacterSnapshot',{}, {staticInfo:info});
    return {actor,statistics:object('CharacterStatisticsData',{
      InfoData:object('CharacterInfoData',{Id:actor.entityId,UserCharacterData:source})},
      {damage:'900719925474099'+index,actualDamage:'900719925474098'+index})};
  });
  const dictionary=object('Dictionary',{}, {members});
  const round=object('SpotStatisticsData',{RedTeamData:dictionary,PlayTime:90,IsWin:true});
  const rounds=list([round]);
  const hp=value=>({field:()=>({value:{toString:()=>value}})});
  const result=object('NK.BattleResult',{TargetMonsterRemainHP:hp('0'),TargetMonsterMaxHP:hp('0'),
    Timeout:true,Retreat:false,Result:1});
  const other=object('NK.BattleResult');
  const packet=object('NK.Network.Packet.Lobby.NetAntiCheatBattleData',{},
    {WaveId:6801001,BattleDuration:90000,Characters:list(actors),Monsters:list(Array(7).fill({}))});
  const team=object('SpotTeamData',{'<CharacterList>k__BackingField':list(actors.map(()=>object('SpotCharacter'))),
    _deadCharacterList:list([]),'<CampType>k__BackingField':0});
  const klass=name=>({type:{name},method:key=>method(key,{
    SpotFinish:0x07607390,IsAlive:0x066e1f00,get_SpotStatisticsData:0x0727e7b0,
    get_SpotResult:0x0727e770,AntiCheatBattleDataInit:options.badRva?1:0x0727a4c0}[key]),
    nested:()=>({field:()=>({value:0})})});
  const context=vm.createContext({console,Interceptor:{attach:(address,listener)=>{
    listeners.push(listener);return {address};}},Il2Cpp:{Object:function(handle){
      return objects.get(handle.id);}}});
  context.intArg=value=>value;
  context.invokeChecked=(m,self,args=[])=>{
    if (afterCleanup) throw Error('UNSAFE_NATIVE_READ_AFTER_CLEANUP '+m.name);
    calls.push(m.name);
    if (options.failStatistics&&m.name==='get_AllRedTeamTotalDamage') throw options.failStatistics;
    if (m.name==='AntiCheatBattleDataInit') {
      order.push('original_packet_builder');
      if(options.packetError)throw options.packetError;
      return packet;
    }
    if (m.name==='get_SpotStatisticsData') return rounds;
    if (m.name==='get_SpotResult') return box(1);
    if (m.name==='IsAlive') return box(1);
    if (m.name==='get_Count') return box(self.rows?.length??self.members?.length);
    if (m.name==='get_Item') return self.rows[args[0]];
    if (m.name==='GetEnumerator') {
      const iterator=object('Enumerator',{}, {cursor:-1,members:self.members});
      return {unbox:()=>iterator};
    }
    if (m.name==='MoveNext') return box(++self.cursor<self.members.length);
    if (m.name==='get_Current') {
      const row=self.members[self.cursor];
      const pair=object('KeyValuePair',{}, {key:row.actor.entityId,value:row.statistics});
      return {unbox:()=>pair};
    }
    if (m.name==='get_Key') return box(self.key);
    if (m.name==='get_Value') return self.value;
    if (m.name==='get_CharacterStaticInfo') return self.staticInfo;
    if (m.name==='get_TableId') return box(self.tableId);
    if (m.name==='get_NameCode') return box(self.nameCode);
    if (m.name==='get_TakeTotalDamage') return box(self.damage);
    if (m.name==='get_TakeTotalActualDamage') return box(self.actualDamage);
    if (m.name==='get_AllRedTeamTotalDamage') return box('9223372036854775806');
    if (['get_WaveId','get_BattleDuration','get_Characters','get_Monsters'].includes(m.name)) {
      const value=self[m.name.slice(4)];return typeof value==='number'?box(value):value;
    }
    throw Error('Unexpected native operation '+m.name);
  };
  vm.runInContext(fs.readFileSync(__dirname+'/practice_result_capture.js','utf8'),context);
  vm.runInContext(fs.readFileSync(__dirname+'/practice_mode.js','utf8'),context);
  const binding=vm.runInContext('NATIVE153_PRACTICE',context);
  const input={schemaVersion:1,clientSha256:binding.clientSha256,
    processMetadataSha256:binding.processMetadataSha256,rangeEntrySha256:binding.rangeEntrySha256,
    waveEntrySha256:binding.waveEntrySha256,inputSourceSha256:'a'.repeat(64),rangeId:1,waveId:6801001,
    processType:9,transporterProcessType:0,managementType:0,teamNumber:0,
    timeLimit:90,teamType:24,specActive:false,randomSeed:555063220,characters:actors};
  const emit=row=>{
    if (options.throwFailureEmit&&row.status==='original_practice_finish_capture_failed')
      throw Error('diagnostic sink failed');
    emitted.push(row);order.push(row.status);
  };
  const start=()=>context.installOriginal153PracticeResultCapture({class:klass},team,x=>x,emit,input,
    {setOriginalFinishObserver:fn=>{registrations++;observer=fn;}});
  return {start,result,other,packet,emitted,calls,order,
    enter:()=>listeners.forEach(listener=>listener.onEnter([{},result.handle])),
    callback:value=>observer(value??result),
    leave:()=>{listeners.forEach(listener=>listener.onLeave());afterCleanup=true;},
    get registrations(){return registrations;}};
}

let h=harness(),capture=h.start();
check(h.registrations===1,'exactly one typed finish observer registered');
h.enter();check(capture.captureTerminal(8).pending===true,'entry alone cannot produce completed packet');
h.callback();
check(h.order.indexOf('original_practice_statistics_captured_before_cleanup')<
  h.order.indexOf('original_packet_builder'),'all original statistics read before packet and cleanup');
check(capture.getOriginalPacket()===h.packet,'same fully built original packet retained');
const partial=h.emitted.find(row=>row.status==='original_practice_statistics_captured_before_cleanup');
check(partial.completeOriginalPacket===false,'statistics receipt remains distinct from complete protobuf packet');
check(Object.isFrozen(partial.statistics)&&Object.isFrozen(partial.statistics.rounds)&&
  Object.isFrozen(partial.statistics.rounds[0].characters[0]),'cached JS original statistics are deeply immutable');
const callsAtFinish=h.calls.length;h.leave();
const final=capture.captureTerminal(8),again=capture.captureTerminal(10);
check(h.calls.length===callsAtFinish,'terminal reads perform zero native getters/builders after cleanup');
check(final.resultCaptured&&final.statisticsAndPacketCapturedBeforeCleanup&&again.processState===10,
  'terminal reads cached original result at current observed state');
check(final.rounds[0].squadTotal==='9223372036854775806'&&
  final.rounds[0].characters[0].outgoingDamage==='9007199254740990',
  'native signed Int64 damage getter strings are exact without Number conversion');
check(final.originalAntiCheat.battleDuration===90000&&final.originalAntiCheat.monsterCount===7,
  'cached original packet readback remains populated');

h=harness();capture=h.start();h.enter();
assert.throws(()=>h.callback(h.other),/differs from the active original/);checks++;
check(!h.calls.includes('AntiCheatBattleDataInit'),'foreign callback result never invokes packet builder');
h.leave();assert.throws(()=>capture.captureTerminal(8),/differs from the active original/);checks++;
h=harness();capture=h.start();h.enter();h.callback();
assert.throws(()=>h.callback(),/Duplicate original practice finish/);checks++;
h=harness();capture=h.start();h.enter();h.leave();
assert.throws(()=>capture.captureTerminal(8),/statistics were not captured/);checks++;
check(!h.calls.includes('AntiCheatBattleDataInit'),'missing callback fails rather than rebuilding released packet');
h=harness();capture=h.start();h.enter();h.leave();
assert.throws(()=>h.callback(),/differs from the active original/);checks++;

const nativeError=Object.assign(Error('original monster projection failed'),{nativeFrames:['0x727dcb3']});
h=harness({packetError:nativeError,throwFailureEmit:true});capture=h.start();h.enter();
assert.throws(()=>h.callback(),error=>error===nativeError);checks++;
h.leave();assert.throws(()=>capture.captureTerminal(8),error=>error===nativeError);checks++;
check(nativeError.nativeFrames[0]==='0x727dcb3'&&capture.getOriginalPacket()===null,
  'native failure identity/frames retained despite throwing diagnostic sink; no fabricated packet');
check(h.emitted.some(row=>row.status==='original_practice_statistics_captured_before_cleanup'),
  'original statistics partial evidence survives later packet failure');
const statisticsError=Error('original statistics getter failed');
h=harness({failStatistics:statisticsError});capture=h.start();h.enter();
assert.throws(()=>h.callback(),error=>error===statisticsError);checks++;
check(!h.calls.includes('AntiCheatBattleDataInit'),'failed original statistics prevents a misleading packet success');
h=harness({badRva:true});assert.throws(h.start,/binding changed/);checks++;
console.log(checks+' result lifetime contracts pass (mock boundary only; no native execution/parity).');
