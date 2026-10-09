// Input arbitration regression: use the real break policy with controlled
// original-adapter readbacks; this establishes no native collision outcome.
const fs=require('node:fs'),vm=require('node:vm'),path=require('node:path');
const assert=require('node:assert/strict');
let tick=0,qteActive=false,coverWanted=false,qteOwned=false;
const state={autoAim:true,forcedCover:false,inputType:0,focusedEntityId:1,focusedStance:0};
const commands=[];
const actions={snapshot:()=>({...state}),setAutoAim:v=>{state.autoAim=v;commands.push(['auto',v]);},
  focus:id=>{state.focusedEntityId=id;},release:()=>{state.inputType=0;commands.push(['release']);},
  press:()=>{state.inputType=2;commands.push(['press']);},aimWorld:()=>{}};
const events=[];
const releaseQte=()=>{if(qteOwned){state.autoAim=true;qteOwned=false;}};
const context=vm.createContext({MECHANICS_REQUEST:{encounter:{waveId:6302006}},
  mechanicsVerifiedCoverRules:()=>[],
  createMechanicsQtePolicy:()=>({summary:()=>({owned:qteOwned}),checkFault(){},
    suspend:releaseQte,resume(){},step(t,s){
      if(!s.qte.active){releaseQte();return;}
      if(!qteOwned){assert.equal(state.autoAim,true,'break must release before QTE acquisition');
        assert.equal(state.inputType,0);qteOwned=true;state.autoAim=false;}
    }}),
  createMechanicsCoverPolicy:()=>({inspect:()=>({wantsCover:coverWanted}),
    summary:()=>({covered:state.forcedCover}),step(){
      if(coverWanted&&!state.forcedCover){
        assert.equal(state.autoAim,true,'break must release before cover');
        assert.equal(state.inputType,0);
      }
      state.forcedCover=coverWanted;
    }})});
for(const file of ['mechanics_break_policy.js','mechanics_tactical_controller.js'])
  vm.runInContext(fs.readFileSync(path.join(__dirname,file),'utf8'),context);
const observer={checkFault(){},snapshot:t=>({supported:true,tick:t,
  qte:{supported:true,active:qteActive,targets:[]},
  squad:{supported:true,characters:[{id:1,health:{hp:'100'},weapon:{ammo:'100',type:{name:'SMG'}}}]}})};
const breakables={checkFault(){},summary:()=>({}),snapshot:t=>({supported:true,tick:t,
  latestEpisodes:[{ownerId:8192,startSequence:1}],monsters:[{
    supported:true,entityId:8192,tableId:'4510010123',playing:true,nativeIsAllBreak:false,
    colliders:[{colliderId:0,name:'break_col_03',type:{value:3,name:'Break'},hp:'100',maxHp:'100',
      unityLive:true,enabled:true,worldAimPoint:[0,1,2],aimPointBasis:'UnityEngine.Collider.bounds.center'}]}]})};
const controller=context.createMechanicsTacticalController('boss-tactical',
  {field:()=>({value:tick})},observer,actions,[],r=>events.push(r),null,breakables);
function sample(t){tick=t;controller.afterTick(t);}
sample(1);controller.beforeTick(2);sample(3);controller.beforeTick(4);
sample(6);controller.beforeTick(7);
assert.equal(controller.summary().breakPolicy.owned,true);
qteActive=true;sample(9);controller.beforeTick(10);
assert.equal(controller.summary().breakPolicy.owned,false);
assert.equal(qteOwned,true);
qteActive=false;sample(12);controller.beforeTick(13);
assert.equal(qteOwned,false);
assert.equal(controller.summary().breakPolicy.owned,false,'fresh reaction after QTE');
sample(15);controller.beforeTick(16);
assert.equal(controller.summary().breakPolicy.owned,true);
coverWanted=true;sample(18);controller.beforeTick(19);
assert.equal(controller.summary().breakPolicy.owned,false);
assert.equal(state.forcedCover,true);
assert.equal(controller.summary().breakPolicy.fault,null);
assert.deepEqual(Array.from(controller.summary().breakPolicy.unsupported),[]);
console.log('PASS: required-part input releases before QTE/cover and reacquires after reaction');
