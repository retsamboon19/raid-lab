// Contract tests for rejecting incomplete native runs. These mock scheduling,
// not game mechanics, and are not native combat/parity evidence.
const assert=require("node:assert/strict");
const fs=require("node:fs");
const vm=require("node:vm");

function run({states, capture, tickError, maxWallMs=100, elapsed=0}) {
  let current=0,tick=0,callback,closed=false,autoSync=false;
  const rows=[];
  const physics={method:name=>({name})};
  const box=value=>({unbox:()=>({handle:{readS32:()=>value,readU8:()=>value}})});
  const context=vm.createContext({
    Math,Number,Set,Error,
    Date:{now:()=>elapsed},
    setInterval:fn=>{callback=fn; return 1;},clearInterval:()=>{},
    onMain:fn=>fn(),floatArg:value=>Math.fround(value),firstAsyncFault:null,
    Memory:{alloc:()=>({writeU8(v){this.value=v;},readS32(){return this.value;}})},
    Process:{getModuleByName:()=>({getExportByName:name=>name})},
    NativeFunction:function(){return (field,buffer)=>{buffer.value=field.value;};},
    Il2Cpp:{domain:{assembly:()=>({image:{class:()=>physics}})}},
    invokeChecked(method,instance,args=[]) {
      if (method.name==="get_autoSyncTransforms") return box(autoSync);
      if (method.name==="set_autoSyncTransforms") {autoSync=!!args[0].value; return null;}
      if (method.name==="get_State") return box(states[Math.min(current,states.length-1)]);
      if (method.name==="UpdateSpot") {
        if (tickError) throw new Error(tickError);
        tick++;current++;return null;
      }
      throw new Error("Unexpected method "+method.name);
    }
  });
  vm.runInContext(fs.readFileSync(__dirname+"/mechanics_tick_runner.js","utf8"),context);
  const runtime={class:()=>({nested:()=>({field:name=>({handle:{value:{Clear:8,Fail:9,Playing:6}[name]},value:{field:()=>({value:
    {Clear:8,Fail:9,Playing:6}[name]})}})})})};
  const management={method:name=>({name}),field:name=>({value:name==="_tickCount"?tick:tick/30})};
  const process={method:name=>({name})};
  context.startOriginalMechanicsTicks(runtime,management,process,row=>rows.push(row),
    ()=>{closed=true;},capture,{maxWallMs});
  // First callback is enough for these deliberately short process histories.
  if (elapsed) elapsed+=maxWallMs;
  callback();
  assert.equal(closed,true);
  assert.equal(autoSync,false,"Original physics setting must be restored on every exit");
  return rows.at(-1);
}

assert.equal(run({states:[8],capture:()=>({resultCaptured:true})}).status,"first_failure");
assert.equal(run({states:[6,8],capture:()=>null}).completeBattle,false);
assert.equal(run({states:[6],tickError:"native targeting fault",capture:()=>null}).completeBattle,false);
const validResult={resultCaptured:true,originalResult:true,result:1,spotResult:1,retreat:false,
  targetMaxHp:"1000",rounds:[{isWin:true,squadTotal:"123"}]};
const valid=run({states:[6,8],capture:()=>validResult});
assert.equal(valid.status,"original_terminal_result");
assert.equal(valid.completeBattle,true);
assert.equal(valid.advancedTicks,1);
assert.equal(valid.fullAccuracyVerified,false);
const limited=run({states:[2],capture:()=>null,maxWallMs:1,elapsed:1});
assert.equal(limited.status,"original_battle_limit_reached");
assert.equal(limited.completeBattle,false);
assert.equal(run({states:[6,9],capture:()=>({...validResult,result:6,spotResult:0})})
  .completeBattle,false);
assert.equal(run({states:[6,9],capture:()=>validResult}).completeBattle,false);
assert.equal(run({states:[6,8],capture:()=>({...validResult,rounds:[{isWin:false}]})})
  .completeBattle,false);
assert.equal(run({states:[6,9],capture:()=>({...validResult,result:2,spotResult:2,
  retreat:true,rounds:[{isWin:false}]})}).completeBattle,false);
const empty=run({states:[6,8],capture:()=>({...validResult,targetMaxHp:"0"})});
assert.equal(empty.status,"original_invalid_encounter_result");
assert.equal(empty.completeBattle,false);
assert.equal(empty.nativeProcessCompleted,true);
console.log("10 native tick-driver completion/cleanup contract cases passed (mock scheduling only).");
