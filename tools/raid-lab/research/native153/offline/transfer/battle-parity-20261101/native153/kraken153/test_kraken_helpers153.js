'use strict';
// Synthetic ABI/ownership controls only. No game, capture payload or combat math.
const assert=require('node:assert/strict'),fs=require('node:fs'),path=require('node:path'),vm=require('node:vm');
const binding=JSON.parse(fs.readFileSync(path.join(__dirname,'kraken-mode-binding153.json'),'utf8'));
const sources=['kraken_mode153.js','prepare_kraken_fixture153.js'].map(name=>fs.readFileSync(path.join(__dirname,name),'utf8')).join('\n');
const H='a'.repeat(64),F='b'.repeat(64),S='c'.repeat(64),P='d'.repeat(64);
const team=[[301701,5169],[141207,5134],[110109,5024],[319111,5004],[422205,5041]];
let checks=0;
function test(name,run){run();checks++;process.stdout.write('PASS '+name+'\n');}
function data(){
  const values={'<ManagementType>k__BackingField':0,'<ProcessType>k__BackingField':7,'TeamType':3,'TeamNumber':0,
    '<TimeLimit>k__BackingField':180,'_waveId':6302009,'<MonsterStageLv>k__BackingField':250,
    '<DynamicObjectLv>k__BackingField':250,'<RaidLvChangeGroup>k__BackingField':209,'<RandomSeed>k__BackingField':123,
    '<IsAuto>k__BackingField':true,'<IsMockBattle>k__BackingField':false,'<TDDProcess>k__BackingField':false};
  return {input:{krakenCapture:{kind:'actual_offline_kraken_prebattle',clientSha256:binding.clientSha256,
      captureSha256:H,receiptSha256:P,fixtureInputSha256:F,snapshotInputSha256:S,
      orderedCharacters:team.map(([tableId,nameCode],i)=>({slot:i+1,tableId,nameCode}))},
    fixtureInput:{clientSha256:binding.clientSha256,transporterValueSize:376,captureSha256:H,runIndex:1,
      wave:{tableId:6302009,requiredNativeType:'StaticData.StaticDataLayer.StaticInfo.WaveDataStaticInfo'},
      fields:Object.entries(values).map(([name,value])=>({name,kind:typeof value==='boolean'?'bool':'int32',value}))
        .concat(Array.from({length:48},(_,index)=>({name:'synthetic_unused_field_'+index,kind:'int32',value:0})))},
    snapshotInput:{clientSha256:binding.clientSha256,captureSha256:H,runIndex:1,characters:team.map(([tableId,nameCode],i)=>
      ({slot:i+1,characterTableId:tableId,sourceNameCode:nameCode}))}},
    expected:{captureSha256:H,runIndex:1,battleOutputsIncluded:false,characters:team.map(()=>({}))}};
}
function environment(){
  const code=new Map(binding.methods.flatMap(m=>m.fragments.map(f=>[f.rva,Buffer.from(f.bytes,'hex')])));
  class Pointer{constructor(n){this.n=n;}add(n){return new Pointer(this.n+n);}equals(p){return this.n===p.n;}
    readByteArray(size){const b=code.get(this.n);if(!b)throw Error('Unbound test code read');return Uint8Array.from(b.subarray(0,size)).buffer;}}
  const pointer=n=>new Pointer(n),calls=[],events=[];let preparedArgs=null,delegateCalls=0;
  const scalar=n=>({unbox:()=>({handle:{readS32:()=>n}})});
  const method=(name,rva=0,params=[])=>({name,isStatic:false,returnType:{name:'System.Void'},
    parameters:params.map(name=>({type:{name}})),relativeVirtualAddress:rva,virtualAddress:pointer(rva)});
  const methods={'.ctor':method('.ctor',0x712d170,['NK.StaticData.SpotModType']),CreateContext:method('CreateContext',0x712d080)};
  let clear=[1,0,2],fail=[];
  const list=which=>({isNull:()=>false,method:name=>({...method(name),list:which})});
  const process={handle:pointer(100),isNull:()=>false,ref:()=>process,method:name=>method(name),
    field:name=>({value:name==='ClearConditionList'?list('clear'):list('fail')})};
  let installed=null;
  const manager={field:name=>({value:installed})};
  const cls={type:{name:'NK.Spot.Context.Process.InterceptProcess'},parent:{type:{name:'NK.Spot.Context.Process.CampaignProcess'}},
    instanceSize:136,isValueType:false,method:name=>methods[name],alloc:()=>process};
  const set=method('SetProcess',0x7607310,['NK.Spot.Context.Process.ProcessBase']);
  const runtime={class:name=>name==='NK.Spot.Context.Process.InterceptProcess'?cls:{method:()=>set}};
  const staticImage={class:()=>({field:()=>({value:7})})};
  const sandbox={Uint8Array,Map,Set,Error,Number,Object,Array,JSON,console,KRAKEN153_MODE_BINDING:structuredClone(binding),
    Process:{getModuleByName:()=>({base:pointer(0)})},intArg:n=>n,
    invokeChecked(m,self,args=[]){
      if(m===methods['.ctor']){calls.push('original_ctor');return null;}
      if(m===set){calls.push('original_SetProcess');installed=process;return null;}
      if(m===methods.CreateContext){calls.push('original_Intercept_CreateContext');return null;}
      if(m.name==='get_ProcessType')return scalar(7);
      if(m.name==='get_RaidLvChangeGroup')return scalar(209);
      if(m.name==='get_Count')return scalar((m.list==='clear'?clear:fail).length);
      if(m.name==='get_Item')return scalar((m.list==='clear'?clear:fail)[args[0]]);
      throw Error('Unexpected native method '+m.name);
    },prepareCapturedPracticeFixture(...args){delegateCalls++;preparedArgs=args;
      const fields=new Map(args[4].fixtureInput.fields.map(f=>[f.name,f.value]));
      const readback={transporterValueTypeSize:376,managementType:0,processType:fields.get('<ProcessType>k__BackingField'),
        teamType:fields.get('TeamType'),teamNumber:0,waveId:6302009,timeLimit:180,monsterStageLv:250,
        dynamicObjectLv:250,randomSeed:123,isAuto:true,isMockBattle:false,tddProcess:false};
      return {passed:true,readback,transporterBox:{unbox:()=>({method:name=>
          ({...method(name,62799008),returnType:{name:'System.Int32'}})})},
        teamChecks:args[4].snapshotInput.characters.map(row=>({passed:true,slot:row.slot,
          tableId:row.characterTableId,nameCode:row.sourceNameCode})),
        snapshots:[],converted:[],staticTransporterInstalled:false,battleStarted:false,transporterExactReplay:false};
    }};
  vm.createContext(sandbox);vm.runInContext(sources,sandbox);
  const emit=row=>events.push(row),pin=x=>x;
  const prepare=()=>{const d=data();return sandbox.prepareCapturedKrakenFixture153(runtime,staticImage,pin,emit,d.input,d.expected,{});};
  return {sandbox,code,methods,cls,set,calls,events,runtime,staticImage,manager,pin,emit,prepare,
    delegateCalls:()=>delegateCalls,preparedArgs:()=>preparedArgs,setClear:x=>clear=x,setFail:x=>fail=x};
}
test('actual-shaped Kraken packet reaches unchanged constructor',()=>{
  const e=environment(),d=data(),before=JSON.stringify(d);
  const f=e.sandbox.prepareCapturedKrakenFixture153(e.runtime,e.staticImage,e.pin,e.emit,d.input,d.expected,{});
  assert.equal(f.passed,true);assert.equal(e.delegateCalls(),1);assert.equal(JSON.stringify(d),before);
  assert.equal(e.preparedArgs()[4],d.input);assert.equal(e.preparedArgs()[5],d.expected);
  assert.equal(f.modeInput.capturedTransporter.raidLvChangeGroup,209);
});
test('captured transporter process0 remains0, process class remains7',()=>{
  const e=environment(),d=data();d.input.fixtureInput.fields.find(f=>f.name==='<ProcessType>k__BackingField').value=0;
  const f=e.sandbox.prepareCapturedKrakenFixture153(e.runtime,e.staticImage,e.pin,e.emit,d.input,d.expected,{});
  assert.equal(f.modeInput.processType,7);assert.equal(f.readback.processType,0);
});
test('different actual preset is accepted from its own source-bound ordered provenance',()=>{
  const e=environment(),d=data();
  d.input.snapshotInput.characters.forEach((row,index)=>{row.characterTableId=700001+index;row.sourceNameCode=9001+index;});
  d.input.krakenCapture.orderedCharacters=d.input.snapshotInput.characters.map(row=>
    ({slot:row.slot,tableId:row.characterTableId,nameCode:row.sourceNameCode}));
  const f=e.sandbox.prepareCapturedKrakenFixture153(e.runtime,e.staticImage,e.pin,e.emit,d.input,d.expected,{});
  assert.equal(f.modeInput.characters[0].tableId,700001);assert.equal(f.passed,true);
});
for(const [name,mutate] of [
  ['practice-derived provenance',d=>d.input.krakenCapture.kind='derived_practice'],
  ['cross-capture expectations',d=>d.expected.captureSha256='e'.repeat(64)],
  ['battle outputs mixed into expectations',d=>d.expected.battleOutputsIncluded=true],
  ['snapshot old client',d=>d.input.snapshotInput.clientSha256='2'.repeat(64)],
  ['wrong wave',d=>d.input.fixtureInput.wave.tableId=6801001],
  ['old client',d=>d.input.fixtureInput.clientSha256='2'.repeat(64)],
  ['wrong transporter layout',d=>d.input.fixtureInput.transporterValueSize=360],
  ['duplicate field',d=>d.input.fixtureInput.fields.push(d.input.fixtureInput.fields[0])],
  ['missing captured field',d=>d.input.fixtureInput.fields.pop()],
  ['wrong ordered actor',d=>d.input.snapshotInput.characters.reverse()],
  ['duplicate logical slot',d=>d.input.snapshotInput.characters[1].slot=1],
  ['missing provenance hash',d=>d.input.krakenCapture.receiptSha256=''],
  ['missing ordered actor provenance',d=>delete d.input.krakenCapture.orderedCharacters],
  ['unsupported auto-off',d=>d.input.fixtureInput.fields.find(f=>f.name==='<IsAuto>k__BackingField').value=false],
  ['wrong duration',d=>d.input.fixtureInput.fields.find(f=>f.name==='<TimeLimit>k__BackingField').value=90],
  ['overflowed captured enum',d=>d.input.fixtureInput.fields.find(f=>f.name==='TeamType').value=2**40],
  ['cross-run expectations',d=>d.expected.runIndex=2]
])test('reject '+name+' before original construction',()=>{
  const e=environment(),d=data();mutate(d);
  assert.throws(()=>e.sandbox.prepareCapturedKrakenFixture153(e.runtime,e.staticImage,e.pin,e.emit,d.input,d.expected,{}));
  assert.equal(e.delegateCalls(),0);
});
test('native conversion failure cannot become passed',()=>{
  const e=environment(),d=data();e.sandbox.prepareCapturedPracticeFixture=()=>({passed:false});
  assert.throws(()=>e.sandbox.prepareCapturedKrakenFixture153(e.runtime,e.staticImage,e.pin,e.emit,d.input,d.expected,{}),/readback/);
});
test('original constructor, manager installation, Intercept override order',()=>{
  const e=environment(),f=e.prepare();
  const p=e.sandbox.createOriginal153KrakenProcess(e.runtime,e.staticImage,e.manager,e.pin,e.emit,f.modeInput,f);
  assert.ok(p);assert.deepEqual(e.calls,['original_ctor','original_SetProcess','original_Intercept_CreateContext']);
  assert.equal(e.events.at(-1).actualCoverOrLevelModeCaptured,false);
  assert.equal(e.events.at(-1).conditionsWritten,false);
});
for(const [name,change] of [
  ['changed constructor byte',e=>e.code.get(0x712d170)[0]^=1],
  ['changed context byte',e=>e.code.get(0x712d080)[100]^=1],
  ['wrong current RVA',e=>e.methods.CreateContext.relativeVirtualAddress++],
  ['static constructor',e=>e.methods['.ctor'].isStatic=true],
  ['wrong constructor parameter',e=>e.methods['.ctor'].parameters[0].type.name='System.Int32'],
  ['wrong parent',e=>e.cls.parent.type.name='System.Object'],
  ['wrong process size',e=>e.cls.instanceSize=128],
  ['missing source binding',e=>e.sandbox.KRAKEN153_MODE_BINDING=null],
  ['wrong table source',e=>e.sandbox.KRAKEN153_MODE_BINDING.encounterSourceSha256='0'.repeat(64)]
])test('reject '+name+' without entering native constructor',()=>{
  const e=environment(),f=e.prepare();change(e);
  assert.throws(()=>e.sandbox.createOriginal153KrakenProcess(e.runtime,e.staticImage,e.manager,e.pin,e.emit,f.modeInput,f));
  assert.deepEqual(e.calls,[]);
});
test('changed original conditions reject before CreateContext',()=>{
  const e=environment(),f=e.prepare();e.setClear([1]);
  assert.throws(()=>e.sandbox.createOriginal153KrakenProcess(e.runtime,e.staticImage,e.manager,e.pin,e.emit,f.modeInput,f),/conditions/);
  assert.ok(!e.calls.includes('original_Intercept_CreateContext'));
});
test('native failure identity and nativeFrames preserved',()=>{
  const e=environment(),f=e.prepare(),original={message:'native',nativeFrames:['0x123']};
  e.sandbox.invokeChecked=()=>{throw original;};
  assert.throws(()=>e.sandbox.createOriginal153KrakenProcess(e.runtime,e.staticImage,e.manager,e.pin,e.emit,f.modeInput,f),x=>x===original);
});
console.log(checks+' contract checks passed; no native invocation');
