// Synthetic policy-contract fixtures; native Mirror input remains unverified.
const assert=require('node:assert/strict');
const fs=require('node:fs');
const path=require('node:path');
const vm=require('node:vm');
const source=fs.readFileSync(path.join(__dirname,'mechanics_break_policy.js'),'utf8');
const create=vm.runInNewContext(source+'\ncreateMechanicsBreakPolicy;');
const actor=(id,type='SMG',ammo='30')=>({id,health:{hp:'100'},
  weapon:{type:{name:type},ammo}});
const col=(colliderId,name='break_col_03',extra={})=>({colliderId,name,
  type:{name:'Break'},hp:'100',maxHp:'100',unityLive:true,enabled:true,
  aimPointBasis:'UnityEngine.Collider.bounds.center',worldAimPoint:[1,2,3],...extra});
const breakState=(tick,extra={})=>({supported:true,tick,monsters:[{
  supported:true,entityId:8192,tableId:'4510010123',playing:true,
  nativeIsAllBreak:false,colliders:[col(3)],...extra}],latestEpisodes:[{
    ownerId:8192,startSequence:7,startTick:tick}]});
const tactical=tick=>({supported:true,tick,squad:{supported:true,
  characters:[actor(4100)]}});
function harness(initial={}) {
  const calls=[],decisions=[];
  const state={autoAim:true,forcedCover:false,focusedEntityId:4100,
    focusedStance:0,inputType:1,...initial};
  const actions={snapshot:()=>({...state}),
    setAutoAim(v){calls.push(['auto',v]);state.autoAim=v;},
    focus(v){calls.push(['focus',v]);state.focusedEntityId=v;},
    aimWorld(id,point,flag){calls.push(['aim',id,...point,flag]);},
    press(){calls.push(['press']);state.inputType=2;state.focusedStance=2;},
    release(){calls.push(['release']);state.inputType=1;state.focusedStance=0;}};
  return {calls,decisions,state,policy:create(actions,row=>decisions.push(row),
    {waveId:6302006})};
}
function through(h,a,b,makeBreak=breakState,makeTactical=tactical) {
  for(let tick=a;tick<=b;tick++) h.policy.step(tick,
    makeBreak(tick),makeTactical(tick));
}
const tests=[
  ['exact Mirror wave required; no skill/cancellation success assertion',()=>{
    assert.throws(()=>create({},()=>{},{waveId:6302009}),/exact wave/);
    const h=harness();through(h,100,106);
    assert.deepEqual(Array.from(h.policy.summary().candidateSourceSkillIds),
      [520669,520676]);
    assert.equal(h.policy.summary().expectedSourceSkillId,null);
    assert.equal(h.policy.summary().sourceSkillLinkVerified,false);
    assert.equal(h.policy.summary().nativeCancellationVerified,false);
    assert.equal(h.calls.filter(c=>c[0]==='press').length,1);
  }],
  ['only original live enabled positive-HP Break is aimed',()=>{
    const h=harness();through(h,100,106,tick=>breakState(tick,{colliders:[
      col(1,'counter',{type:{name:'Counter'},worldAimPoint:[9,9,9]}),
      col(2,'choice',{type:{name:'Choice'},worldAimPoint:[8,8,8]}),
      col(3,'break_col_03'),col(4,'break_col_04',{hp:'0'}),
      col(5,'break_col_05',{enabled:false})]}));
    assert.ok(h.calls.filter(c=>c[0]==='aim').every(c=>c[2]===1));
    assert.equal(h.policy.summary().targetKey,'8192:3');
  }],
  ['trial128 first-phase 01/02 colliders are source-bound candidates',()=>{
    const h=harness();through(h,1113,1120,tick=>breakState(tick,{colliders:[
      col(819201,'break_col_01',{hp:'350000',maxHp:'350000'}),
      col(819202,'break_col_02',{hp:'350000',maxHp:'350000'})]}));
    assert.equal(h.policy.summary().targetKey,'8192:819201');
    assert.equal(h.policy.summary().targetsSelected,1);
    assert.equal(h.policy.summary().sourceSkillLinkVerified,false);
    assert.equal(h.calls.filter(c=>c[0]==='press').length,1);
  }],
  ['wrong boss or inactive break never takes input',()=>{
    for(const override of [{tableId:'4510010999'},{playing:false},
      {nativeIsAllBreak:true}]) {
      const h=harness();through(h,100,106,tick=>breakState(tick,override));
      assert.equal(h.calls.length,0);
    }
  }],
  ['ambiguous owner, duplicate collider, bad geometry fail closed',()=>{
    const cases=[
      tick=>{const b=breakState(tick);b.monsters.push({...b.monsters[0],entityId:8193});return b;},
      tick=>breakState(tick,{colliders:[col(3),col(3)]}),
      tick=>breakState(tick,{colliders:[col(3,'break_col_03',{worldAimPoint:null})]}),
      tick=>breakState(tick,{colliders:[col(3,'other_break')]})
    ];
    for(const make of cases) {
      const h=harness();through(h,100,106,make);
      assert.equal(h.calls.length,0);
      assert.ok(h.policy.summary().unsupported.length>0);
    }
  }],
  ['stable owner/collider ID survives reorder and moving bounds',()=>{
    const h=harness();through(h,100,106,tick=>breakState(tick,{colliders:[
      col(4,'break_col_04'),col(3,'break_col_03',{worldAimPoint:[tick,2,3]})]}));
    assert.equal(h.policy.summary().targetKey,'8192:3');
    assert.equal(h.policy.summary().targetsSelected,1);
    assert.ok(h.calls.filter(c=>c[0]==='aim').some(c=>c[2]===106));
  }],
  ['stale native snapshot releases held trigger and original auto',()=>{
    const h=harness();through(h,100,106);
    h.policy.step(107,breakState(103),tactical(103));
    assert.equal(h.policy.summary().owned,false);
    assert.equal(h.state.inputType,1);
    assert.equal(h.state.autoAim,true);
  }],
  ['cover/QTE suspension releases input and resumes with fresh reaction',()=>{
    const h=harness();through(h,100,106);
    h.policy.suspend(106,'qte_priority');
    assert.equal(h.state.inputType,1);
    assert.equal(h.state.autoAim,true);
    h.state.forcedCover=true;
    assert.equal(h.policy.resume(107),false);
    through(h,107,110);
    h.state.forcedCover=false;
    assert.equal(h.policy.resume(110),true);
    const presses=h.calls.filter(c=>c[0]==='press').length;
    through(h,111,112);
    assert.equal(h.calls.filter(c=>c[0]==='press').length,presses);
    through(h,113,116);
    assert.equal(h.calls.filter(c=>c[0]==='press').length,presses+1);
  }],
  ['preexisting input ownership and actor readiness are respected',()=>{
    for(const state of [{inputType:2},{forcedCover:true},{autoAim:false}]) {
      const h=harness(state);through(h,100,106);
      assert.equal(h.calls.length,0);
    }
    const h=harness();through(h,100,106,breakState,tick=>({supported:true,tick,
      squad:{supported:true,characters:[actor(1,'SMG','0'),
        actor(2,'MG','40'),actor(3,'AR','20')]}}));
    assert.equal(h.policy.summary().actorId,3);
  }],
  ['close releases control and blocks later commands',()=>{
    const h=harness();through(h,100,106);
    h.policy.close('test');
    const n=h.calls.length;h.policy.step(107,breakState(107),tactical(107));
    assert.equal(h.calls.length,n);
    assert.equal(h.policy.summary().closed,true);
    assert.equal(h.state.autoAim,true);
  }]
];
let failed=0;
for(const [label,test] of tests) {
  try {test();console.log('ok - '+label);}
  catch(error) {failed++;console.error('not ok - '+label+'\n'+error.stack);}
}
if(failed) process.exitCode=1;
