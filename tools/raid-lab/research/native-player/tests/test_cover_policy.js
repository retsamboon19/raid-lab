// Pure policy-contract tests. These fixtures are not original native results.
const assert=require("node:assert/strict");
const fs=require("node:fs");
const path=require("node:path");
const vm=require("node:vm");
const source=fs.readFileSync(path.join(__dirname,"mechanics_cover_policy.js"),"utf8");
const api=vm.runInNewContext(source+
  "\n({createMechanicsCoverPolicy,mechanicsVerifiedCoverRules});");
const rule=()=>api.mechanicsVerifiedCoverRules();
function harness(waveId=6302009,initial={}) {
  const logs=[],calls=[];
  const state={inputType:1,forcedCover:false,autoAim:true,
    squad:[{entityId:4096,usedAmmoCount:10}],...initial};
  const actions={snapshot(){return {...state,squad:state.squad.map(x=>({...x}))};},
    setCover(value){calls.push(["cover",value]);state.forcedCover=value;}};
  const policy=api.createMechanicsCoverPolicy(actions,row=>logs.push(row),rule(),waveId);
  return {policy,state,calls,logs};
}
const attack=(tick,sequence,casterId=8192,node=230)=>({
  tick,sequence,casterId,attackNodeId:node,targetId:4096});
const monster=(entityId=8192,tableId="1520040153",condition="Idle")=>({
  entityId,tableId,condition:{name:condition}});
const caster=(casterId,attacks=[],latestCreate=null,activeProjectiles=[],
    totalAttackCount)=>({casterId,recentAttacks:attacks,latestCreate,
      activeProjectiles,...(totalAttackCount===undefined?{}:{totalAttackCount})});
function frame(tick,{monsters=[monster()],casters=[caster(8192)],
    conditions=[],pendingUnlinkedCreate=null,attackHistoryTruncated=false}={}) {
  return {observation:{supported:true,tick,monsters,
      monsterConditions:conditions,squad:[{entityId:4096,hp:"1000"}]},
    threat:{supported:true,tick,casters,pendingUnlinkedCreate,
      attackHistoryTruncated}};
}
function step(h,tick,parts) {
  const {observation,threat}=frame(tick,parts);
  h.policy.step(tick,observation,threat);
}
function observedCast(h,attackRow=attack(100,10)) {
  for(let t=100;t<=103;t++) step(h,t,{casters:[caster(attackRow.casterId,[attackRow])]});
}
const created=(tick,sequence,casterId=8192,skillId=532033)=>({
  tick,sequence,casterId,skillId});
const projectile=(projectileId,spawnTick,createSequence)=>({
  projectileId,spawnTick,source:{skillId:532033,createSequence}});
function finish(h,{start=104,casterId=8192,attackRow=attack(100,10),
    create=created(104,11),projectileRow=projectile(901,104,11)}={}) {
  const attacks=[attackRow],monsters=name=>[monster(casterId,"1520040153",name)];
  step(h,start,{casters:[caster(casterId,attacks,create,[projectileRow])],
    monsters:monsters("FireCasting"),conditions:[{monsterInfoId:casterId,
      tick:start,condition:{name:"FireCasting"}}]});
  step(h,start+1,{casters:[caster(casterId,attacks,create,[])],
    monsters:monsters("FireCasting"),conditions:[{monsterInfoId:casterId,
      tick:start,condition:{name:"FireCasting"}}]});
  step(h,start+2,{casters:[caster(casterId,attacks,create,[])],
    monsters:monsters("Idle"),conditions:[{monsterInfoId:casterId,
      tick:start+2,condition:{name:"Idle"}}]});
}
const tests=[
  ["only exact Kraken wave/table/node creates a cover command",()=>{
    const wrongWave=harness(9999);
    step(wrongWave,100,{casters:[caster(8192,[attack(100,10)])]});
    assert.equal(wrongWave.calls.length,0);
    const wrongTable=harness();
    for(let t=100;t<=105;t++) step(wrongTable,t,{monsters:[monster(8192,"9")],
      casters:[caster(8192,[attack(100,10)])]});
    assert.equal(wrongTable.calls.length,0);
    const wrongNode=harness();
    for(let t=100;t<=105;t++) step(wrongNode,t,{casters:[caster(8192,[attack(100,10,8192,229)])]});
    assert.equal(wrongNode.calls.length,0);
    const h=harness();observedCast(h);
    assert.deepEqual(h.calls,[["cover",true]]);
    assert.equal(h.logs.filter(x=>x.action==="entered").length,1);
  }],
  ["rejected rule cannot fabricate another boss, node, or projectile skill",()=>{
    for(const change of [{monsterTableId:"9"},{attackNodeId:229},
      {projectileSkillId:1},{waveId:9999},{reactionTicks:1}]) {
      const bad={...rule()[0],...change};
      assert.throws(()=>api.createMechanicsCoverPolicy({snapshot(){},setCover(){}},
        ()=>{},[bad],6302009),/source-bound Kraken/);
    }
  }],
  ["inspect then step same tick and repeated step do not duplicate entry",()=>{
    const h=harness(),a=attack(100,10);
    for(let t=100;t<=103;t++) {
      const {observation,threat}=frame(t,{casters:[caster(8192,[a])]});
      h.policy.inspect(t,observation,threat);
      h.policy.step(t,observation,threat);
      h.policy.step(t,observation,threat);
    }
    assert.equal(h.logs.filter(x=>x.action==="danger_observed").length,1);
    assert.deepEqual(h.calls,[["cover",true]]);
  }],
  ["stale same-tick create and projectile cannot resolve new attack",()=>{
    const h=harness();observedCast(h);
    const a=attack(100,10),oldCreate=created(100,9),
      oldProjectile=projectile(800,100,9);
    step(h,104,{casters:[caster(8192,[a],oldCreate,[oldProjectile])],
      monsters:[monster(8192,"1520040153","FireCasting")]});
    step(h,105,{casters:[caster(8192,[a],oldCreate,[])],
      monsters:[monster(8192,"1520040153","Idle")],
      conditions:[{monsterInfoId:8192,tick:105,condition:{name:"Idle"}}]});
    assert.equal(h.policy.summary().covered,true);
    assert.equal(h.logs.filter(x=>x.action==="released").length,0);
  }],
  ["missile despawn and intervening Idle cannot release during follow-up cast",()=>{
    const h=harness();observedCast(h);
    const a=attack(100,10),create=created(104,11),p=projectile(901,104,11);
    step(h,104,{casters:[caster(8192,[a],create,[p])],
      monsters:[monster(8192,"1520040153","FireCasting")]});
    step(h,105,{casters:[caster(8192,[a],create,[])],
      monsters:[monster(8192,"1520040153","FireCasting")],
      conditions:[{monsterInfoId:8192,tick:102,condition:{name:"Idle"}}]});
    assert.equal(h.policy.summary().covered,true);
    step(h,106,{casters:[caster(8192,[a],create,[])],
      monsters:[monster(8192,"1520040153","Fire")],
      conditions:[{monsterInfoId:8192,tick:106,condition:{name:"Fire"}}]});
    assert.equal(h.policy.summary().covered,true);
    step(h,107,{casters:[caster(8192,[a],create,[])],
      monsters:[monster(8192,"1520040153","Idle")],
      conditions:[{monsterInfoId:8192,tick:107,condition:{name:"Idle"}}]});
    assert.equal(h.policy.summary().covered,false);
    assert.deepEqual(h.calls,[["cover",true],["cover",false]]);
  }],
  ["sampled casting lag cannot move past the original Idle transition",()=>{
    const h=harness();observedCast(h);
    const a=attack(100,10),create=created(104,11),p=projectile(901,104,11);
    step(h,104,{casters:[caster(8192,[a],create,[p])],
      monsters:[monster(8192,"1520040153","FireCasting")],
      conditions:[{monsterInfoId:8192,tick:104,condition:{name:"FireCasting"}}]});
    step(h,105,{casters:[caster(8192,[a],create,[])],
      monsters:[monster(8192,"1520040153","FireCasting")],
      conditions:[{monsterInfoId:8192,tick:104,condition:{name:"FireCasting"}}]});
    step(h,106,{casters:[caster(8192,[a],create,[])],
      monsters:[monster(8192,"1520040153","Fire")],
      conditions:[{monsterInfoId:8192,tick:106,condition:{name:"Fire"}}]});
    // The live sampled condition can lag the event stream. Its stale Fire
    // sample must not make an Idle event at 107 appear earlier than casting.
    step(h,109,{casters:[caster(8192,[a],create,[])],
      monsters:[monster(8192,"1520040153","Fire")],
      conditions:[{monsterInfoId:8192,tick:107,condition:{name:"Idle"}}]});
    assert.equal(h.policy.summary().covered,true);
    step(h,112,{casters:[caster(8192,[a],create,[])],
      monsters:[monster(8192,"1520040153","Idle")],
      conditions:[{monsterInfoId:8192,tick:107,condition:{name:"Idle"}}]});
    assert.equal(h.policy.summary().covered,false);
    assert.equal(h.logs.find(x=>x.action==="released").tick,112);
  }],
  ["an Idle before a later projectile clears cannot release cover",()=>{
    const h=harness();observedCast(h);
    const a=attack(100,10),create=created(104,11);
    step(h,104,{casters:[caster(8192,[a],create,[projectile(901,104,11)])],
      monsters:[monster(8192,"1520040153","FireCasting")],
      conditions:[{monsterInfoId:8192,tick:104,condition:{name:"FireCasting"}}]});
    step(h,105,{casters:[caster(8192,[a],create,[])],
      monsters:[monster(8192,"1520040153","FireCasting")],
      conditions:[{monsterInfoId:8192,tick:104,condition:{name:"FireCasting"}}]});
    step(h,106,{casters:[caster(8192,[a],create,[projectile(902,106,12)])],
      monsters:[monster()],
      conditions:[{monsterInfoId:8192,tick:106,condition:{name:"Idle"}}]});
    step(h,107,{casters:[caster(8192,[a],create,[])],
      monsters:[monster()],
      conditions:[{monsterInfoId:8192,tick:106,condition:{name:"Idle"}}]});
    assert.equal(h.policy.summary().covered,true);
    step(h,108,{casters:[caster(8192,[a],create,[])],
      monsters:[monster()],
      conditions:[{monsterInfoId:8192,tick:108,condition:{name:"Idle"}}]});
    assert.equal(h.policy.summary().covered,false);
  }],
  ["cumulative ring truncation is not a missed-input report",()=>{
    const h=harness();
    for(let ordinal=1;ordinal<=20;ordinal++) {
      const a={...attack(ordinal,ordinal*100,8192,229),attackOrdinal:ordinal};
      step(h,ordinal,{casters:[caster(8192,[a],null,[],ordinal)],
        attackHistoryTruncated:ordinal>16});
    }
    assert.equal(h.policy.summary().historyCursorAvailable,true);
    assert.equal(h.policy.summary().historyGapCount,0);
    assert.ok(!h.policy.summary().unsupported.includes(
      "original_attack_history_cursor_gap"));
    assert.equal(h.calls.length,0);
  }],
  ["per-caster ordinal jump detects a genuinely lost recent attack",()=>{
    const h=harness();
    step(h,1,{casters:[caster(8192,[{...attack(1,100,8192,229),
      attackOrdinal:1}],null,[],1)]});
    step(h,2,{casters:[caster(8192,[{...attack(2,200,8192,229),
      attackOrdinal:3}],null,[],3)],attackHistoryTruncated:true});
    assert.ok(h.policy.summary().unsupported.includes(
      "original_attack_history_cursor_gap"));
    assert.equal(h.policy.summary().historyGapCount,1);
  }],
  ["two casters require both post-projectile Idle resolutions",()=>{
    const h=harness(),a=attack(100,10,8192),b=attack(101,20,8200);
    for(let t=100;t<=103;t++) step(h,t,{monsters:[monster(),monster(8200)],
      casters:[caster(8192,[a]),caster(8200,t>=101?[b]:[])]});
    assert.equal(h.policy.summary().pending.length,2);
    const createA=created(104,11),createB=created(104,21,8200);
    const projectileA=projectile(901,104,11),projectileB=projectile(902,104,21);
    step(h,104,{monsters:[monster(8192,"1520040153","FireCasting"),
      monster(8200,"1520040153","FireCasting")],
      casters:[caster(8192,[a],createA,[projectileA]),
        caster(8200,[b],createB,[projectileB])]});
    step(h,105,{monsters:[monster(8192,"1520040153","FireCasting"),
      monster(8200,"1520040153","FireCasting")],
      casters:[caster(8192,[a],createA,[]),caster(8200,[b],createB,[projectileB])],
      conditions:[{monsterInfoId:8192,tick:104,condition:{name:"FireCasting"}},
        {monsterInfoId:8200,tick:104,condition:{name:"FireCasting"}}]});
    step(h,106,{monsters:[monster(),monster(8200,"1520040153","FireCasting")],
      conditions:[{monsterInfoId:8192,tick:106,condition:{name:"Idle"}},
        {monsterInfoId:8200,tick:104,condition:{name:"FireCasting"}}],
      casters:[caster(8192,[a],createA,[]),caster(8200,[b],createB,[])]});
    assert.equal(h.policy.summary().covered,true);
    step(h,107,{monsters:[monster(),monster(8200)],
      conditions:[{monsterInfoId:8192,tick:106,condition:{name:"Idle"}},
        {monsterInfoId:8200,tick:107,condition:{name:"Idle"}}],
      casters:[caster(8192,[a],createA,[]),caster(8200,[b],createB,[])]});
    assert.equal(h.policy.summary().covered,false);
    assert.equal(h.policy.summary().completed,2);
  }],
  ["second same-node cycle cannot reuse first cycle create or Idle",()=>{
    const h=harness();observedCast(h);finish(h);
    assert.equal(h.policy.summary().completed,1);
    const firstCreate=created(104,11),a2=attack(200,30);
    for(let t=200;t<=203;t++) step(h,t,{casters:[caster(8192,[a2],firstCreate)],
      conditions:[{monsterInfoId:8192,tick:106,condition:{name:"Idle"}}]});
    assert.equal(h.policy.summary().covered,true);
    step(h,204,{casters:[caster(8192,[a2],firstCreate,[])],
      monsters:[monster(8192,"1520040153","Idle")],
      conditions:[{monsterInfoId:8192,tick:204,condition:{name:"Idle"}}]});
    assert.equal(h.policy.summary().completed,1);
    assert.equal(h.logs.filter(x=>x.action==="released").length,1);
    finish(h,{start:205,attackRow:a2,create:created(205,31),
      projectileRow:projectile(902,205,31)});
    assert.equal(h.policy.summary().completed,2);
    assert.equal(h.logs.filter(x=>x.action==="released").length,2);
  }],
  ["existing input ownership is preserved; external loss is explicit",()=>{
    for(const state of [{inputType:2},{forcedCover:true},{autoAim:false}]) {
      const h=harness(6302009,state);observedCast(h);
      assert.equal(h.calls.length,0);
      assert.ok(h.policy.summary().unsupported.includes(
        "cover_requires_released_original_auto_ownership"));
    }
    const h=harness();observedCast(h);
    h.state.forcedCover=false;
    step(h,104,{casters:[caster(8192,[attack(100,10)])]});
    assert.ok(h.policy.summary().unsupported.includes(
      "cover_ownership_lost_before_native_resolution"));
    assert.equal(h.policy.summary().completed,0);
  }],
  ["stale snapshots cannot trigger or release cover",()=>{
    const h=harness(),a=attack(100,10);
    for(let t=100;t<=104;t++) {
      const input=frame(t,{casters:[caster(8192,[a])]});
      input.threat.tick=t-1;
      h.policy.step(t,input.observation,input.threat);
    }
    assert.equal(h.calls.length,0);
    assert.ok(h.policy.summary().unsupported.includes(
      "stale_or_missing_original_tick_snapshot"));
  }],
  ["native firing resume readback is retained after release",()=>{
    const h=harness();observedCast(h);finish(h);
    h.state.squad[0].usedAmmoCount=11;
    step(h,121,{casters:[caster(8192)]});
    assert.equal(h.logs.find(x=>x.action==="resume_readback").firingResumed,true);
    assert.equal(h.policy.summary().resumeChecks,1);
  }]
];
let failed=0;
for(const [name,run] of tests) {
  try {run();process.stdout.write("ok - "+name+"\n");}
  catch(error){failed++;process.stderr.write("not ok - "+name+"\n"+
    (error.stack||String(error))+"\n");}
}
if(failed) process.exitCode=1;
