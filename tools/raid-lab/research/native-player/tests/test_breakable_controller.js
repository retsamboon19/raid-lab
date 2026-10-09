// Controller wiring tests with synthetic read-only snapshots; no native claim.
const assert=require('node:assert/strict');
const fs=require('node:fs');
const path=require('node:path');
const vm=require('node:vm');
const source=fs.readFileSync(path.join(__dirname,'mechanics_tactical_controller.js'),'utf8');
const context=vm.createContext({});
vm.runInContext(source,context,{filename:'mechanics_tactical_controller.js'});
const create=context.createMechanicsTacticalController;

let nativeTick=0;
const management={field:name=>{
  assert.equal(name,'_tickCount');
  return {value:nativeTick};
}};
const observer={checkFault(){},snapshot:tick=>({supported:true,tick,
  qte:{supported:false},monster:{supported:false},squad:{supported:false}})};
const events=[];
let hp='10',worldX=0,breakSnapshots=0;
const breakables={
  checkFault(){},
  snapshot(tick){breakSnapshots++;return {supported:true,tick,monsters:[{
    supported:true,entityId:8192,tableId:'4510010123',playing:true,
    nativeIsAllBreak:false,colliders:[{colliderId:0,name:'break_col_03',
      type:{value:3,name:'Break'},hp,maxHp:'10',unityLive:true,enabled:true,
      liveBreakTarget:true,worldAimPoint:[worldX,1,2]}]}]};},
  summary:()=>({totalEvents:2,eventTransitionsTruncated:false,fault:null})
};
assert.throws(()=>create('boss-observe',management,observer,null,[],()=>{}),
  /needs original break observer/);
const controller=create('boss-observe',management,observer,null,[],
  row=>events.push(row),null,breakables);
nativeTick=1;controller.afterTick(1);
worldX=4;nativeTick=3;controller.afterTick(3);
hp='8';nativeTick=6;controller.afterTick(6);
assert.equal(breakSnapshots,3);
assert.equal(events.filter(e=>e.status==='original_break_observation_change').length,2,
  'position-only movement must not produce transition spam');
assert.equal(controller.summary().breakSamples,3);
assert.equal(controller.summary().breakTransitions,2);
assert.equal(controller.summary().breakObservation.totalEvents,2);
assert.equal(controller.summary().breakObservationTransitionsTruncated,false);

const legacy=create('observe',management,observer,null,[],()=>{});
assert.equal(legacy.summary().breakObservation,undefined);
console.log('Break controller integration: 2 focused synthetic checks passed');
