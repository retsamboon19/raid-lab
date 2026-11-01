'use strict';
// Actual host receipt producer -> actual fixture predicate. Synthetic managed
// tuple/delegate construction only; no DLL/native process or combat emulation.
const assert=require('node:assert');
const fs=require('node:fs');
const path=require('node:path');
const vm=require('node:vm');
const hostSource=fs.readFileSync(path.join(__dirname,'practice_host_callbacks.js'),'utf8');
const fixtureSource=fs.readFileSync(path.join(__dirname,'replay-input/prepare_practice_fixture.js'),'utf8');
const captured=JSON.parse(fs.readFileSync(path.join(__dirname,
  'replay-input/run1/native-fixture-input.json'),'utf8'));
const metadata=JSON.parse(fs.readFileSync(path.join(__dirname,
  '../metadata/current153-run3/mechanics-metadata.json'),'utf8'));
const native=metadata.classes.find(row=>row.class==='NK.Spot.Data.NKSpotDataTransporter');
const specs=captured.fields.filter(row=>row.kind==='nativeOwnerBinding');
assert.deepEqual(specs.map(row=>row.name),['OnSpotPauseFirstButton',
  'OnSpotPauseSecondButton','OnBattleFinish','OnBattleRetry']);
assert(fixtureSource.includes('const allowed=isAcceptedCapturedPracticeNativeOwnerReceipt(spec,receipt);'));
let serial=0;
const pointer=extra=>({id:++serial,...extra,equals(other){return this.id===other.id;}});
const managed=handle=>({handle,isNull:()=>false});
const actionClass={type:{name:'UnityEngine.Events.UnityAction'}};
const tupleClass={isValueType:true,valueTypeSize:16,
  field(name){assert.equal(name,'Item2');return {type:{class:actionClass}};},
  alloc(){
    const values={},unboxed={values,field:name=>({value:values[name]})};
    return {...managed(pointer()),unbox:()=>unboxed};
  },
  method(name){assert.equal(name,'.ctor');return {overload(first,second){
    assert.equal(first,'System.String');assert.equal(second,'UnityEngine.Events.UnityAction');
    return {construct(self,args){self.values.Item1=managed(args[0]);self.values.Item2=managed(args[1]);}};
  }};}
};
const runtime={class(name){
  assert.equal(name,native.class);
  return {valueTypeSize:native.valueSize,field(name){
    const field=native.fields.find(row=>row.name===name);assert(field);
    return {offset:field.offset,isStatic:(field.flags&16)!==0,
      type:{name:field.type,class:field.type.startsWith('System.ValueTuple<')
        ?tupleClass:{type:{name:field.type}}}};
  }};
}};
const sandbox={Il2Cpp:{delegate:(klass,callback)=>({...managed(pointer()),klass,callback}),
  string:text=>managed(pointer({text})),Object:function(handle){return managed(handle);},
  String:function(handle){this.content=handle.text;}},
  invokeChecked:(method,self,args)=>method.construct(self,args)};
vm.createContext(sandbox);vm.runInContext(hostSource+'\n'+fixtureSource,sandbox);
const producer=sandbox.createPracticeHostCallbacks(runtime,value=>value,()=>{});
const accept=sandbox.isAcceptedCapturedPracticeNativeOwnerReceipt;
let assertions=0;
const check=(actual,expected,label)=>{assert.equal(actual,expected,label);assertions++;};
for(const spec of specs){
  const binding=producer.resolveNativeOwnerField(spec),receipt=binding.receipt;
  assert(binding.value);
  check(accept(spec,receipt),true,'actual current host accepted '+spec.name);
  check(receipt.submitsAccountData,false,'host submission claim '+spec.name);
  for(const [name,value]of [
    ['submitsAccountData',true],['mutatesCombatState',true],
    ['originalUiCallbacksReplayed',true],['sourceNativeType','wrong.Native.Type'],
    ['behavior','wrong_behavior'],['originalPacketCaptureBeforeCleanup',undefined],
    ['originalPacketCaptureBeforeCleanup',spec.name!=='OnBattleFinish'],
    ['fieldName','wrong_callback'],['sourceNativeFieldOffset',spec.offset+8],
    ['capturedTupleLabelPreserved',!spec.name.startsWith('OnSpotPause')]
  ])check(accept(spec,{...receipt,[name]:value}),false,name+' rejected '+spec.name);
  const old={...receipt,serializesOrSubmitsAccountData:false};
  delete old.submitsAccountData;delete old.originalPacketCaptureBeforeCleanup;
  if(spec.name==='OnBattleFinish')old.behavior='record_original_result_without_writes';
  check(accept(spec,old),false,'old combined serialization/submission schema rejected '+spec.name);
  check(accept(spec,{...receipt,serializesOrSubmitsAccountData:false}),false,
    'retired false serialization claim rejected even with new fields '+spec.name);
  const original={kind:'original_private_native_owner',sourceNativeType:spec.type,
    receiptSha256:'a'.repeat(64)};
  check(accept(spec,original),true,'independent original private owner preserved '+spec.name);
  check(accept(spec,{...original,receiptSha256:'a'.repeat(63)}),false,
    'original owner still needs full source hash '+spec.name);
  check(accept(spec,{...original,sourceNativeType:'wrong.Native.Type'}),false,
    'original owner still needs exact type '+spec.name);
}
for(const [first,second]of [[specs[0],specs[1]],[specs[2],specs[3]]])
  check(accept(second,producer.resolveNativeOwnerField(first).receipt),false,
    'same-typed callback receipts cannot be interchanged');
check(accept({...specs[2],name:'UnknownCallback'},producer.resolveNativeOwnerField(specs[2]).receipt),false,
  'host boundary is limited to four original callback categories');
check(accept(specs[0],null),false,'missing receipt rejected');
console.log(assertions+' producer/fixture boundary assertions passed across all four callbacks; no native execution.');
