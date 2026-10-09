// Exercises the production scheduling functions with a deterministic bridge.
// Synthetic Unity timing only: a passing test is not a native startup result.
const assert=require('node:assert/strict');
const fs=require('node:fs');
const path=require('node:path');
const vm=require('node:vm');

const driver=fs.readFileSync(path.join(__dirname,'headless_driver.js'),'utf8');
const start=driver.indexOf('let pendingMain = false;');
const end=driver.indexOf('const startManagedProbe = () =>',start);
assert.ok(start>=0 && end>start,'production scheduling region must be present');
const production=driver.slice(start,end);

function harness() {
  let now=0,mode='missing',attached=0,scheduleCalls=0;
  const timers=[],scheduled=[],records=[],performModes=[],postCalls=[];
  const missing="couldn't find the synchronization context of the main thread, perhaps this is early instrumentation?";
  const post={virtualAddress:{equals:value=>value===0x07F17E50}};
  const uni={class:name=>name==='Cysharp.Threading.Tasks.UniTask' ?
    {method:(method,arity)=>{
      assert.equal(method,'Post');assert.equal(arity,2);return post;
    }} : {field:field=>{
      assert.equal(name,'Cysharp.Threading.Tasks.PlayerLoopTiming');
      assert.equal(field,'Update');return {value:8};
    }}};
  const game={base:{add:value=>value}};
  const context=vm.createContext({
    Date:{now:()=>now},
    setTimeout(callback,delay){timers.push({at:now+delay,callback});},
    record:row=>records.push(row),
    Process:{getCurrentThreadId:()=>77,getModuleByName:name=>{
      assert.equal(name,'GameAssembly.dll');return game;
    }},
    intArg:value=>value,
    Il2Cpp:{
      domain:{assembly:name=>{
        assert.equal(name,'UniTask');return {image:uni};
      }},
      corlib:{class:name=>{
        assert.equal(name,'System.Action');return name;
      }},
      delegate:(type,callback)=>({handle:{type,callback},ref:()=>({})}),
      mainThread:{schedule:callback=>{
        scheduleCalls++;
        if (mode==='missing') throw new Error(missing);
        if (mode==='unrelated') throw new Error('unrelated bridge failure');
        scheduled.push(callback);
        return Promise.resolve();
      }},
      perform:(callback,delivery)=>{
        performModes.push(delivery);
        assert.equal(delivery,'free');
        attached++;
        try {
          const returned=callback();
          assert.equal(returned,undefined,'perform callback must not await schedule');
          return Promise.resolve();
        } catch(error) {return Promise.reject(error);}
        finally {attached--;}
      }
    },
    invokeChecked:(method,self,args)=>{
      assert.equal(method,post);
      assert.equal(self,null);
      assert.equal(args.length,2);
      postCalls.push(args);
      scheduled.push(args[0].callback);
    },
  });
  vm.runInContext('let firstAsyncFault=null;\n'+production+
    '\nglobalThis.__unit={onMain,state:()=>({pendingMain,mainDelivery,'+
    'pendingMainBlock,mainWork:{...mainWork},firstAsyncFault})};',context,
    {filename:'headless_driver.js'});
  const unit=context.__unit;
  async function flush() {for(let i=0;i<4;i++) await Promise.resolve();}
  async function advanceTo(target) {
    assert.ok(target>=now);
    for (;;) {
      timers.sort((a,b)=>a.at-b.at);
      if (!timers.length || timers[0].at>target) break;
      const timer=timers.shift();now=timer.at;timer.callback();await flush();
    }
    now=target;await flush();
  }
  function deliver() {
    assert.ok(scheduled.length,'expected a main-thread callback');
    const callback=scheduled.shift();callback();
  }
  return {unit,records,performModes,postCalls,scheduled,timers,
    flush,advanceTo,deliver,setMode:value=>{mode=value;},
    attached:()=>attached,scheduleCalls:()=>scheduleCalls,now:()=>now};
}

async function testUnavailableThenReadyExactlyOnce() {
  const h=harness();let first=0,second=0;
  assert.equal(h.unit.onMain(()=>first++),true);
  assert.equal(h.unit.onMain(()=>second++),false,'one pending block owns the slot');
  await h.flush();
  assert.equal(h.records.filter(r=>r.phase==='main_context_pending').length,1);
  assert.equal(h.records.filter(r=>r.phase==='schedule_error').length,0);
  assert.equal(h.attached(),0,'worker must detach before main callback');
  await h.advanceTo(600);
  h.setMode('ready');await h.advanceTo(800);
  assert.equal(h.scheduled.length,1);
  assert.equal(first,0,'scheduled work has not run on the worker');
  h.deliver();
  assert.equal(first,1);assert.equal(second,0);
  assert.equal(h.unit.state().pendingMain,false);
  assert.equal(h.unit.state().mainDelivery,'original_unitask_update');
  assert.equal(h.records.filter(r=>r.phase==='main_work_delivery_ready').length,1);
  assert.ok(h.performModes.every(x=>x==='free'));
  await h.advanceTo(1200);
  assert.equal(first,1,'no timer can replay completed work');
}

async function testUnrelatedFailureDoesNotRetry() {
  const h=harness();let calls=0;
  h.setMode('unrelated');assert.equal(h.unit.onMain(()=>calls++),true);
  await h.flush();
  assert.equal(h.unit.state().pendingMain,false);
  assert.equal(h.records.filter(r=>r.phase==='main_context_pending').length,0);
  assert.equal(h.records.filter(r=>r.phase==='schedule_error').length,1);
  assert.equal(h.timers.length,0);
  await h.advanceTo(16000);
  assert.equal(h.scheduleCalls(),1);assert.equal(calls,0);
}

async function testBoundedContextWaitClearsSlot() {
  const h=harness();let calls=0;
  h.unit.onMain(()=>calls++);await h.flush();
  await h.advanceTo(16000);
  assert.equal(h.unit.state().pendingMain,false);
  assert.equal(h.timers.length,0);
  assert.equal(h.records.filter(r=>r.phase==='main_context_pending').length,1);
  assert.equal(h.records.filter(r=>r.phase==='schedule_error').length,1);
  assert.equal(calls,0);
  assert.ok(h.scheduleCalls()>1 && h.scheduleCalls()<100);
  h.setMode('ready');assert.equal(h.unit.onMain(()=>calls++),true);
  await h.flush();h.deliver();
  assert.equal(calls,1,'a later independent request can use the freed slot');
}

async function testLaterUniTaskQueueUnchanged() {
  const h=harness();h.setMode('ready');let first=0,later=0;
  h.unit.onMain(()=>first++);await h.flush();h.deliver();
  assert.equal(first,1);
  assert.equal(h.unit.onMain(()=>later++),true);
  await h.flush();
  assert.equal(h.postCalls.length,1,'later dispatch must use original UniTask.Post');
  assert.equal(h.scheduleCalls(),1,'bridge schedule is bootstrap-only');
  assert.equal(later,0);assert.equal(h.attached(),0);
  h.deliver();
  assert.equal(later,1);
  assert.equal(h.unit.state().pendingMain,false);
  assert.ok(h.performModes.every(x=>x==='free'));
}

(async()=>{
  await testUnavailableThenReadyExactlyOnce();
  await testUnrelatedFailureDoesNotRetry();
  await testBoundedContextWaitClearsSlot();
  await testLaterUniTaskQueueUnchanged();
  console.log('Headless startup context: 4 extracted-driver regression checks passed');
})().catch(error=>{console.error(error.stack||error);process.exitCode=1;});
