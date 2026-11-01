'use strict';
// Synthetic callback-boundary contracts only. No DLL loading/native invocation.
const assert=require('node:assert');
const fs=require('node:fs');
const path=require('node:path');
const vm=require('node:vm');
const source=fs.readFileSync(path.join(__dirname,'practice_host_callbacks.js'),'utf8');
const metadata=JSON.parse(fs.readFileSync(path.join(__dirname,
  '../metadata/current153-run3/mechanics-metadata.json'),'utf8'));
const transporter=metadata.classes.find(row=>row.class==='NK.Spot.Data.NKSpotDataTransporter');
assert.equal(transporter.valueSize,376);
const makeResult=()=>({isNull:()=>false,class:{type:{name:'NK.BattleResult'}},
  handle:{toString:()=>'<synthetic-original-result>'}});
function fixture({throwOnStatus=null,sinkError=null}={}){
  const events=[],order=[],pins=[];
  const runtime={class(name){
    assert.equal(name,transporter.class);
    return {valueTypeSize:transporter.valueSize,field(name){
      const field=transporter.fields.find(row=>row.name===name);assert(field,name);
      return {offset:field.offset,isStatic:(field.flags&16)!==0,
        type:{name:field.type,class:{type:{name:field.type}}}};
    }};
  }};
  const context={Il2Cpp:{delegate:(klass,callback)=>({klass,callback})}};
  vm.createContext(context);vm.runInContext(source,context);
  const pin=value=>{
    pins.push(value);
    if(value.class?.type.name==='NK.BattleResult')order.push('pin_original_result');
    return value;
  };
  const emit=row=>{
    events.push(row);
    if(row.status==='practice_host_original_result_received')order.push('record_original_result');
    if(throwOnStatus?.has(row.status))throw sinkError;
  };
  const callbacks=context.createPracticeHostCallbacks(runtime,pin,emit);
  const bind=name=>{
    const field=transporter.fields.find(row=>row.name===name);assert(field,name);
    return callbacks.resolveNativeOwnerField({name,type:field.type,offset:field.offset});
  };
  return {callbacks,bind,events,order,pins};
}
let passed=0;
function test(name,body){body();passed++;console.log('PASS '+name);}

test('same pinned original result is observed synchronously before caller cleanup',()=>{
  const f=fixture(),original=makeResult();let cleanupStarted=false,observed=null;
  f.callbacks.setOriginalFinishObserver(value=>{
    assert.equal(cleanupStarted,false);
    assert.strictEqual(value,original);
    assert(f.pins.includes(original));
    f.order.push('capture_before_cleanup');observed=value;
  });
  const finish=f.bind('OnBattleFinish');
  assert.equal(finish.receipt.originalPacketCaptureBeforeCleanup,true);
  assert.doesNotThrow(()=>finish.value.callback(original));
  cleanupStarted=true;f.order.push('caller_cleanup');
  assert.strictEqual(observed,original);
  assert.deepEqual(f.order,['pin_original_result','record_original_result',
    'capture_before_cleanup','caller_cleanup']);
  f.callbacks.check();
  assert.strictEqual(f.callbacks.getOriginalResults()[0],original);
  const copy=f.callbacks.getOriginalResults();copy.length=0;
  assert.equal(f.callbacks.getOriginalResults().length,1);
});

test('observer native exception identity and frames survive callback check',()=>{
  const f=fixture(),nativeError=new Error('synthetic native builder exception');
  nativeError.nativeFrames=['0x0727A7E9','0x0727DCB3'];
  f.callbacks.setOriginalFinishObserver(()=>{throw nativeError;});
  const finish=f.bind('OnBattleFinish');
  assert.doesNotThrow(()=>finish.value.callback(makeResult()));
  assert.throws(()=>f.callbacks.check(),error=>error===nativeError);
  const fault=f.events.find(row=>row.status==='practice_host_callback_fault');
  assert(fault);assert.strictEqual(fault.nativeFrames,nativeError.nativeFrames);
  assert.equal(f.callbacks.snapshot().receivedResultCount,1);
});

test('failing fault diagnostic sink cannot replace native observer exception',()=>{
  const loggerError=new Error('synthetic logger failure');
  const f=fixture({throwOnStatus:new Set(['practice_host_callback_fault']),sinkError:loggerError});
  const nativeError=new Error('synthetic native observer failure');nativeError.nativeFrames=['original-frame'];
  f.callbacks.setOriginalFinishObserver(()=>{throw nativeError;});
  assert.doesNotThrow(()=>f.bind('OnBattleFinish').value.callback(makeResult()));
  assert.throws(()=>f.callbacks.check(),error=>error===nativeError);
});

test('failing result and fault sinks do not unwind through native delegate',()=>{
  const sinkError=new Error('synthetic disconnected evidence sink');
  const f=fixture({throwOnStatus:new Set(['practice_host_original_result_received',
    'practice_host_callback_fault']),sinkError});let observerCalls=0;
  f.callbacks.setOriginalFinishObserver(()=>observerCalls++);
  const original=makeResult();
  assert.doesNotThrow(()=>f.bind('OnBattleFinish').value.callback(original));
  assert.strictEqual(f.callbacks.getOriginalResults()[0],original);
  assert.equal(observerCalls,0);
  assert.throws(()=>f.callbacks.check(),error=>error===sinkError);
});

test('observer registration is single and cannot change after finish',()=>{
  const f=fixture();let calls=0;
  f.callbacks.setOriginalFinishObserver(()=>calls++);
  assert.throws(()=>f.callbacks.setOriginalFinishObserver(()=>{}),/exactly once/);
  f.bind('OnBattleFinish').value.callback(makeResult());
  assert.equal(calls,1);
  assert.throws(()=>f.callbacks.setOriginalFinishObserver(()=>{}),/exactly once/);
});

test('missing observer and duplicate finish are explicit latched failures',()=>{
  const missing=fixture();
  assert.doesNotThrow(()=>missing.bind('OnBattleFinish').value.callback(makeResult()));
  assert.throws(()=>missing.callbacks.check(),/not registered/);
  const duplicate=fixture();let calls=0;
  duplicate.callbacks.setOriginalFinishObserver(()=>calls++);
  const bound=duplicate.bind('OnBattleFinish'),original=makeResult();
  bound.value.callback(original);
  assert.doesNotThrow(()=>bound.value.callback(original));
  assert.equal(calls,1);assert.equal(duplicate.callbacks.getOriginalResults().length,1);
  assert.throws(()=>duplicate.callbacks.check(),/Duplicate original battle finish/);
});

test('retry is rejected without invoking result observer',()=>{
  const f=fixture();let calls=0;
  f.callbacks.setOriginalFinishObserver(()=>calls++);
  assert.doesNotThrow(()=>f.bind('OnBattleRetry').value.callback(makeResult()));
  assert.equal(calls,0);assert.equal(f.callbacks.getOriginalResults().length,0);
  assert.throws(()=>f.callbacks.check(),/Unexpected OnBattleRetry/);
});

console.log(passed+' synthetic host callback contracts passed; no native process launched.');
