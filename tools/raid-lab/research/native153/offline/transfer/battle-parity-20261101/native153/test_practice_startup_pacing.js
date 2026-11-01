'use strict';
const assert=require('node:assert/strict');
const fs=require('node:fs');
const vm=require('node:vm');
const source=fs.readFileSync(__dirname+'/practice_frame_scheduler.js','utf8');
function host(options={}) {
  const state={rate:-1,capture:0,cine:-1,frame:0,ready:false,ticks:0,events:[],queue:[],
    errors:[],writes:[],clock:'e816830a02',wrongRead:false};
  const addresses={get_targetFrameRate:0x084D4350,set_targetFrameRate:0x084D4990,
    get_CurrentTime:0x009BB3E0,Post:0x081CF660};
  const ptr=value=>({value,isNull:()=>false,equals:other=>value===other.value,
    readByteArray:()=>Buffer.from(state.clock,'hex')});
  const scalar=value=>({unbox:()=>({handle:{readS32:()=>value,readFloat:()=>value}})});
  const klass=name=>({method:(method,count)=>({name:method,count,
      virtualAddress:ptr(addresses[method]+(options.badBinding&&method==='set_targetFrameRate'?1:0))}),
    field:field=>field==='CurrentTimeOverride'?{isStatic:true,offset:0x24,handle:'cine'}:{value:0}});
  const game={base:{add:ptr},getExportByName:name=>({name})};
  const context={PRACTICE_SETTINGS_INPUT:{frameRate:60,frameRateBinding:{literal:'FPS60'},
    clientSha256:'d39896d3770888039c728a1908448c3db5efa7cdf874c90d56f46d8d566428d2'},
    Il2Cpp:{domain:{assembly:()=>({image:{class:klass}})},corlib:{class:klass},
      delegate:(_type,callback)=>({handle:callback})},
    Process:{getModuleByName:()=>game,findModuleByAddress:()=>({name:'UnityPlayer.dll'})},
    Memory:{alloc:()=>{let value;return {readFloat:()=>value,writeFloat:x=>{value=Math.fround(x);}};},
      allocUtf8String:name=>({name}),patchCode:(_address,_size,fn)=>fn({writeByteArray:bytes=>{state.clock=Buffer.from(bytes).toString('hex');}})},
    NativeFunction:function(pointer) {
      switch(pointer.name) {
        case 'il2cpp_field_static_get_value':return (_field,out)=>out.writeFloat(state.cine);
        case 'il2cpp_field_static_set_value':return (_field,input)=>{state.cine=input.readFloat();};
        case 'il2cpp_resolve_icall':return name=>({...name,isNull:()=>false});
        case 'UnityEngine.Time::get_captureDeltaTime':return ()=>state.capture;
        case 'UnityEngine.Time::set_captureDeltaTime':return value=>{state.capture=value;};
        default:throw Error('Unexpected native API '+pointer.name);
      }
    },intArg:value=>value,
    invokeChecked:(method,_self,args=[])=>{
      switch(method.name) {
        case 'get_targetFrameRate':return scalar(state.wrongRead?0:state.rate);
        case 'set_targetFrameRate':
          state.rate=args[0];state.writes.push(args[0]);
          state.wrongRead=!!(options.failInitial&&args[0]===60 ||
            options.failAcceleration&&state.ready&&args[0]===-1&&!state.failedOnce);
          if(state.wrongRead&&state.ready)state.failedOnce=true;
          return null;
        case 'get_fixedDeltaTime':return scalar(0.02);
        case 'get_timeScale':return scalar(1);
        case 'get_deltaTime':return scalar(Math.fround(1/60));
        case 'get_frameCount':return scalar(state.frame);
        case 'Post':state.queue.push(args[0]);return null;
        default:throw Error('Unexpected represented method '+method.name);
      }
    }};
  vm.createContext(context);vm.runInContext(source,context);
  state.make=()=>context.createPracticeFrameScheduler(x=>x,event=>state.events.push(event),-1,()=>state.ready);
  state.next=()=>{assert.ok(state.queue.length);state.frame++;state.queue.shift()();};
  state.start=()=>{state.schedule=state.make();state.control=state.schedule(()=>state.ticks++,error=>{
    state.errors.push(String(error));state.control.cancel();});};
  state.assertRestored=()=>{assert.equal(state.rate,-1);assert.equal(state.capture,0);
    assert.equal(state.cine,-1);assert.equal(state.clock,'e816830a02');};
  return state;
}
let passed=0;
function test(name,fn){fn();passed++;console.log('PASS '+name);}
test('actual scheduler uses captured startup pacing until verified original combat',()=>{
  const h=host();h.start();assert.equal(h.rate,60);
  h.next();h.next();assert.equal(h.ticks,2);assert.equal(h.rate,60);
  const capture=h.capture,cine=h.cine;h.ready=true;h.next();
  assert.equal(h.rate,-1);assert.equal(h.capture,capture);assert.ok(h.cine>cine);
  h.next();assert.deepEqual(h.writes,[60,-1]);assert.equal(h.ticks,4);
  assert.equal(h.events.filter(e=>e.status==='original_practice_combat_wall_pacing').length,1);
  h.control.cancel();h.assertRestored();h.next();assert.equal(h.ticks,4);
});
test('cancel during loading restores original clocks and rate without a combat tick',()=>{
  const h=host();h.start();h.control.cancel();h.assertRestored();h.next();assert.equal(h.ticks,0);
});
test('startup rate readback failure restores all prior inputs before scheduling',()=>{
  const h=host({failInitial:true});assert.throws(()=>h.make(),/readback differs/);
  h.assertRestored();assert.equal(h.queue.length,0);
});
test('nonboolean readiness fails without advancing or accelerating combat',()=>{
  const h=host();h.start();h.ready=1;h.next();assert.equal(h.ticks,0);
  assert.match(h.errors[0],/explicit boolean/);h.assertRestored();
});
test('acceleration readback failure cancels before another native combat update',()=>{
  const h=host({failAcceleration:true});h.start();h.next();h.ready=true;h.next();
  assert.equal(h.ticks,1);assert.match(h.errors[0],/readback differs/);h.assertRestored();
});
test('wrong exact-client Application setter binding prevents all mutations',()=>{
  const h=host({badBinding:true});assert.throws(()=>h.make(),/Application binding changed/);
  h.assertRestored();assert.deepEqual(h.writes,[]);
});
console.log(JSON.stringify({passed,scope:'Actual scheduler source with isolated native-API doubles; no native execution'}));
