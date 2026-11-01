// Native mode handoff and receipt contracts only; no native game is launched.
const assert=require('node:assert/strict'),fs=require('node:fs'),vm=require('node:vm');
const context=vm.createContext({console});
vm.runInContext(fs.readFileSync(__dirname+'/practice_mode.js','utf8'),context);
const binding=vm.runInContext('NATIVE153_PRACTICE',context);
const clone=value=>JSON.parse(JSON.stringify(value));
const input={schemaVersion:1,clientSha256:binding.clientSha256,
  processMetadataSha256:binding.processMetadataSha256,rangeEntrySha256:binding.rangeEntrySha256,
  waveEntrySha256:binding.waveEntrySha256,inputSourceSha256:'a'.repeat(64),rangeId:1,waveId:6801001,
  processType:9,transporterProcessType:0,managementType:0,teamNumber:0,
  timeLimit:90,teamType:24,specActive:false,randomSeed:555063220,
  characters:Array.from({length:5},(_,index)=>({tableId:100+index,nameCode:5000+index}))};
const actors=input.characters.map((row,index)=>({...row,entityId:4096+index}));
const result={resultCaptured:true,originalResult:true,resultType:'NK.BattleResult',result:1,spotResult:1,
  processState:8,retreat:false,targetRemainHp:'0',targetMaxHp:'0',
  originalAntiCheat:{source:'original_BattleResult_AntiCheatBattleDataInit',waveId:6801001,
    battleDuration:90000,characterCount:5,monsterCount:7},
  rounds:[{duration:90,isWin:true,squadTotal:'1013203602',characters:clone(actors)}]};
const evidence={processClass:binding.processClass,processType:9,waveId:6801001,timeLimit:90,
  transporterProcessType:0,managementType:0,teamNumber:0,
  teamType:24,randomSeed:input.randomSeed,inputReadbackPassed:true,inputSourceSha256:input.inputSourceSha256,
  observedPlaying:true,advancedTicks:2700,processState:8,originalActors:clone(actors)};
let checks=0;
function check(value,label){assert.ok(value,label);checks++;}
check(context.validateNative153PracticeInput(input)===input,'exact bound input accepted');
for(const mutate of [x=>x.processType=7,x=>x.timeLimit=180,x=>x.rangeId=2,x=>x.specActive=true,
    x=>x.clientSha256='b'.repeat(64),x=>x.processMetadataSha256='b'.repeat(64),x=>x.characters.pop()]) {
  const changed=clone(input);mutate(changed);assert.throws(()=>context.validateNative153PracticeInput(changed));checks++;
}
const transporter={transporterValueTypeSize:376,processType:0,managementType:0,teamNumber:0,
  waveId:6801001,timeLimit:90,teamType:24,randomSeed:input.randomSeed};
check(context.verifyNative153PracticeTransporter(input,transporter),'current376-byte transporter binding');
assert.throws(()=>context.verifyNative153PracticeTransporter(input,{...transporter,transporterValueTypeSize:360}));checks++;
assert.throws(()=>context.verifyNative153PracticeTransporter(input,{...transporter,processType:9}));checks++;
const complete=context.verifyOriginal153PracticeTerminal(input,result,evidence);
check(complete.passed&&complete.bossHpRequired===false,'populated practice completes with zero boss HP');
check(complete.processStateResultBinding==='unverified'&&!complete.fullAccuracyVerified,'state/result and parity claims remain unverified');
const differentState=clone(result);differentState.processState=9;
check(context.verifyOriginal153PracticeTerminal(input,differentState,{...evidence,processState:9}).passed,
  'no Intercept Clear-to-Win or Fail-to-Lose assumption');
const finalState=clone(result);finalState.processState=10;
check(context.verifyOriginal153PracticeTerminal(input,finalState,{...evidence,processState:10}).passed,
  'original Finish after SpotFinish is accepted without fabricating a Clear state');
for(const [mutateResult,mutateEvidence] of [
  [r=>r.resultCaptured=false,()=>{}],[r=>r.originalResult=false,()=>{}],
  [r=>r.retreat=true,()=>{}],[r=>r.result=4,()=>{}],
  [r=>r.originalAntiCheat.battleDuration=89999,()=>{}],
  [r=>r.originalAntiCheat.monsterCount=0,()=>{}],
  [r=>r.rounds[0].squadTotal='0',()=>{}],
  [r=>r.rounds[0].characters[0].tableId=999,()=>{}],
  [r=>r.rounds[0].characters[0]=null,()=>{}],
  [()=>{},e=>e.observedPlaying=false],[()=>{},e=>e.advancedTicks=0],
  [()=>{},e=>e.processState=6],[()=>{},e=>e.inputReadbackPassed=false],
  [()=>{},e=>e.inputSourceSha256='b'.repeat(64)],[()=>{},e=>e.randomSeed++],
  [()=>{},e=>e.originalActors.reverse()]]) {
  const r=clone(result),e=clone(evidence);mutateResult(r);mutateEvidence(e);
  check(!context.verifyOriginal153PracticeTerminal(input,r,e).passed,'incomplete/abort/wrong-input native receipt rejected');
}
const reference={inputSourceSha256:input.inputSourceSha256,rangeId:1,waveId:6801001,
  battleDuration:90000,battleResult:1,score:'1013203602'};
check(context.compareOriginal153PracticeReference(input,result,complete,reference).passed,'raw original result/reference equality');
check(!context.compareOriginal153PracticeReference(input,result,complete,{...reference,score:'1013203603'}).passed,
  'comparison never normalizes or adjusts original score');
check(!context.compareOriginal153PracticeReference(input,result,{passed:false},reference).passed,
  'reference match cannot substitute for original native completion');

// Constructor/context adapter delegates to original methods. It does not set
// play state, time, conditions, results or combat counters.
const calls=[],box=value=>({unbox:()=>({handle:{readS32:()=>value}})});
const handle={equals:other=>other===handle};
const list=values=>({values,isNull:()=>false,method:name=>({name})});
const clear=list([1,0,2]),fail=list([]);
const process={handle,isNull:()=>false,class:{type:{name:binding.processClass}},method:name=>({name}),
  field:name=>({value:name==='ClearConditionList'?clear:fail})};
const method=(name,rva)=>({name,relativeVirtualAddress:rva});
const parent={type:{name:binding.parentClass},method:()=>method('CreateContext',binding.createContext)};
const klass={type:{name:binding.processClass},parent,alloc:()=>process,
  method:()=>method('.ctor',binding.ctor)};
const management={handle:{},field:()=>({value:process})};
const condition={field:name=>({value:{AllMonsterDead:1,TimeOut:0,AllCharacterDead:2}[name]})};
const runtime={class:name=>name===binding.processClass?klass:name===binding.parentClass?parent:
  name==='NK.Spot.Logic.Process.ProcessConditionType'?condition:
  {type:{name},method:()=>method('SetProcess',binding.setProcess)}};
context.intArg=value=>value;
context.invokeChecked=(m,self,args=[])=>{
  calls.push(m.name);
  if(['.ctor','SetProcess','CreateContext'].includes(m.name))return null;
  if(m.name==='get_ProcessType')return box(9);
  if(m.name==='get_Count')return box(self.values.length);
  if(m.name==='get_Item')return box(self.values[args[0]]);
  throw Error('Unexpected native mutation/method '+m.name);
};
const emitted=[];
const created=context.createOriginal153PracticeProcess(runtime,{class:()=>({field:()=>({value:9})})},
  management,value=>value,row=>emitted.push(row),input,transporter);
check(created===process&&calls.includes('.ctor')&&calls.includes('SetProcess')&&calls.includes('CreateContext'),
  'original practice constructor, SetProcess and Campaign.CreateContext delegated');
check(clear.values.join('|')==='1|0|2'&&fail.values.length===0&&emitted[0].conditionsUnchanged,
  'original constructor condition lists only read back');
check(!calls.some(name=>['SetState','Clear','Fail','SpotFinish','UpdateSpot'].includes(name)),
  'mode setup never manufactures lifecycle or terminal transitions');
console.log(checks+' practice mode contracts pass (mock/readback logic only; no native invocation/parity).');
