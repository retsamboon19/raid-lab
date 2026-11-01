// Contract-only mocks: scheduling, cancellation and original lifecycle routing.
// Does not launch Unity or claim native battle validation.
const assert=require('node:assert/strict'),fs=require('node:fs'),vm=require('node:vm');
let checks=0;
function check(value,label){assert.ok(value,label);checks++;}
function harness(overrides={}) {
  let tick=243,playTime=4.1529951095581055,state=2,frame=null,cancelled=0,updates=0;
  let now=0,physicsReads=0,captureCalls=0,methods=[];
  const emitted=[],finished=[],deltas=[],context=vm.createContext({console,
    Date:{now:()=>now},Memory:{alloc:()=>({writeFloat:value=>deltas.push(value)})},
    Il2Cpp:{domain:{assembly:name=>({image:{class:()=>({method:method=>({name:method,
      owner:name,relativeVirtualAddress:0x0852ebd0})})}})}}});
  vm.runInContext(fs.readFileSync(__dirname+'/practice_mode.js','utf8'),context);
  const binding=vm.runInContext('NATIVE153_PRACTICE',context);
  const input={schemaVersion:1,clientSha256:binding.clientSha256,
    processMetadataSha256:binding.processMetadataSha256,rangeEntrySha256:binding.rangeEntrySha256,
    waveEntrySha256:binding.waveEntrySha256,inputSourceSha256:'a'.repeat(64),rangeId:1,waveId:6801001,
    processType:9,transporterProcessType:0,managementType:0,teamNumber:0,
    timeLimit:90,teamType:24,specActive:false,randomSeed:555063220,
    characters:Array.from({length:5},(_,index)=>({tableId:100+index,nameCode:5000+index}))};
  const actors=input.characters.map((row,index)=>({...row,entityId:4096+index}));
  const evidence={processClass:binding.processClass,processType:9,waveId:6801001,timeLimit:90,
    transporterProcessType:0,managementType:0,teamNumber:0,teamType:24,randomSeed:555063220,
    inputReadbackPassed:true,inputSourceSha256:input.inputSourceSha256};
  const nativeResult=()=>({resultCaptured:true,originalResult:true,resultType:'NK.BattleResult',
    result:1,spotResult:1,processState:state,retreat:false,
    originalAntiCheat:{source:'original_BattleResult_AntiCheatBattleDataInit',waveId:6801001,
      battleDuration:90000,characterCount:5,monsterCount:7},
    rounds:[{duration:90,squadTotal:'1013203602',characters:actors}]});
  const runtime={class:()=>({type:{name:'NK.Spot.SpotManagement'},method:name=>({name,
    relativeVirtualAddress:overrides.updateRva??0x07607f40})})};
  const management={field:name=>({value:name==='_tickCount'?tick:playTime})};
  context.readOriginal153PracticeLifecycle=()=>({processClass:binding.processClass,processType:9,
    state,stateName:String(state),playTime,battleTime:playTime-4.1529951095581055});
  context.invokeChecked=(method,self,args=[])=>{
    methods.push(method.name);
    if (method.name==='get_autoSyncTransforms') {
      physicsReads++;return {unbox:()=>({handle:{readU8:()=>0}})};
    }
    if (method.name==='get_deltaTime')
      return {unbox:()=>({handle:{readFloat:()=>Math.fround(.017)}})};
    if (method.name!=='UpdateTick') throw Error('Unexpected native entry '+method.name);
    updates++;tick++;playTime+=Math.fround(.017);
    if (overrides.nativeUpdate) overrides.nativeUpdate({setState:value=>state=value,updates});
  };
  vm.runInContext(fs.readFileSync(__dirname+'/practice_tick_runner.js','utf8'),context);
  const options={schedule:callback=>{frame=callback;return {cancel:()=>cancelled++};},
    inputEvidence:()=>evidence,actorIdentities:()=>actors,...overrides.options};
  const capture=()=>{captureCalls++;return overrides.capture?
    overrides.capture(captureCalls,nativeResult):nativeResult();};
  const start=()=>context.startOriginalPracticeTicks(runtime,management,{},input,
    row=>emitted.push(row),row=>finished.push(row),capture,options);
  return {start,fire:()=>frame(),setState:value=>state=value,setNow:value=>now=value,
    emitted,finished,deltas,evidence,actors,
    get snapshot(){return {tick,playTime,state,cancelled,updates,physicsReads,captureCalls,methods};}};
}

let h=harness({options:{beforeUpdate:()=>({pending:true,reason:'original_resources_loading'})}});
let control=h.start();h.fire();
check(h.snapshot.updates===1&&h.snapshot.tick===244,'pending parent readiness still invokes original preload UpdateTick');
check(h.emitted.find(row=>row.status==='original_practice_first_update_returned').managerTickBefore===243,
  'original nonzero pre-OnStart tick is preserved');
check(h.deltas[0]===Math.fround(.017),'original float32 Time.deltaTime readback forwarded without cadence math');
check(h.snapshot.physicsReads===1&&!h.snapshot.methods.includes('set_autoSyncTransforms'),
  'physics setting only read and unchanged');
const stopped=control.stop('original_loading_verified',{geometryValidated:true});h.fire();
check(stopped.completeBattle===false&&stopped.resultCaptured===false&&stopped.geometryValidated,
  'load-only stop never claims a battle result');
check(h.snapshot.updates===1&&h.snapshot.cancelled===1&&h.finished.length===1,
  'stop cancels scheduler once and stale frame callbacks do nothing');
control.stop('again');check(h.finished.length===1,'stop is idempotent');

h=harness({nativeUpdate:({setState,updates})=>setState(updates===1?6:9),
  capture:(count,result)=>count===1?{pending:true}:result()});
control=h.start();h.fire();h.fire();h.fire();h.fire();
check(h.snapshot.updates===3&&h.snapshot.captureCalls===2,'pending original result allows native return lifecycle to continue');
check(h.finished[0].status==='original_practice_terminal_result'&&h.finished[0].verification.passed,
  'observed Playing plus original result passes separate practice verification');
check(h.finished[0].processState===9&&h.finished[0].result===1,
  'no invented Fail-to-Lose or boss-HP completion assumption');
check(h.finished[0].fullAccuracyVerified===false&&h.finished[0].physicsSettingUnchanged,
  'complete native receipt alone does not certify exact parity');
check(!h.snapshot.methods.some(name=>['OnStart','GameStart','OnLoad','SetState','SpotFinish','UpdateSpot'].includes(name)),
  'only original management UpdateTick dispatch is used');

h=harness({nativeUpdate:({setState,updates})=>setState(updates===1?6:8)});
h.evidence.inputReadbackPassed=false;h.start();h.fire();h.fire();h.fire();
check(h.finished[0].status==='original_invalid_practice_result'&&!h.finished[0].completeBattle,
  'unpassed source input reconstruction rejects otherwise populated original result');
h=harness({options:{maxUpdates:1}});h.start();h.fire();h.fire();
check(h.finished[0].status==='original_practice_limit_reached'&&!h.finished[0].resultCaptured,
  'bounded update limit records incomplete loading without manufacturing a result');
h=harness();h.start();h.setNow(60000);h.fire();
check(h.snapshot.updates===0&&h.finished[0].status==='original_practice_limit_reached',
  'wall bound stops before another native update');
h=harness({options:{readDeltaTime:()=>1/60,deltaReadbackSource:'test_unrounded_number'}});h.start();h.fire();
check(h.snapshot.updates===0&&h.finished[0].status==='first_failure',
  'unrounded arbitrary double delta is rejected rather than converted into a synthetic clock');
h=harness({options:{checkFault:()=>Error('original loader failed')}});h.start();h.fire();
check(h.snapshot.updates===0&&h.finished[0].status==='first_failure'&&h.snapshot.cancelled===1,
  'observed original loader fault cancels bounded trial');
h=harness({updateRva:0x1234});assert.throws(h.start,/binding changed/);checks++;
console.log(checks+' practice tick contracts pass (mock lifecycle only; no native invocation/parity).');
