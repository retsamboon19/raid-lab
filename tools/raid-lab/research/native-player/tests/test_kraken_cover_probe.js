// Cover-policy contract tests only. No Unity, Frida, DLL, or native run.
const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("node:path");
const vm = require("node:vm");

const source = fs.readFileSync(path.join(__dirname,
  "mechanics_kraken_cover_probe.js"), "utf8");
const createProbe = vm.runInNewContext(source +
  "\ncreateMechanicsKrakenCoverProbe;");

function harness() {
  const calls=[],events=[];
  const state={forcedCover:false,inputType:1};
  const actions={
    snapshot() {return {...state};},
    setCover(value) {calls.push(["setCover",value]);state.forcedCover=value;}
  };
  return {calls,events,state,probe:createProbe(actions,event=>events.push(event))};
}

function observation(tick,condition="FireCasting") {
  return {latestCondition:{tick,condition:{name:condition}},
    squad:{supported:true,characters:[]}};
}

function threat(tick,{node=230,projectiles=[],created=false,pending=null}={}) {
  return {supported:true,latestAttack:{tick:100,attackNodeId:node},
    latestCreate:created?{tick,skillId:532033}:null,
    activeBossProjectiles:projectiles,
    allBossActiveProjectileIds:projectiles.map(p=>p.projectileId),
    pendingUnlinkedCreate:pending};
}

const liveMissile={projectileId:41,spawnTick:103};
const tests=[
  ["unrelated attack never arms cover",()=>{
    const h=harness();
    for(let tick=100;tick<=105;tick++)
      h.probe.step(tick,observation(tick),threat(tick,{node:231}));
    assert.equal(h.probe.summary().armed,false);
    assert.equal(h.calls.length,0);
  }],
  ["live node 230 waits three native ticks before cover",()=>{
    const h=harness();
    for(let tick=100;tick<=102;tick++)
      h.probe.step(tick,observation(tick),threat(tick));
    assert.equal(h.calls.length,0);
    h.probe.step(103,observation(103),threat(103));
    assert.deepEqual(h.calls,[["setCover",true]]);
    assert.equal(h.probe.summary().coverTick,103);
  }],
  ["preexisting projectile alone cannot authorize release",()=>{
    const h=harness();
    const old={projectileId:40,spawnTick:99};
    h.probe.step(100,observation(100),threat(100));
    h.probe.step(103,observation(103,"Idle"),threat(99,
      {projectiles:[old],created:true}));
    h.probe.step(104,observation(104,"Idle"),threat(104));
    assert.equal(h.probe.summary().sawProjectile,false);
    assert.equal(h.probe.summary().completed,false);
    assert.deepEqual(h.calls,[["setCover",true]]);
  }],
  ["last missile gone during FireCasting holds cover until Idle",()=>{
    const h=harness();
    h.probe.step(100,observation(100),threat(100));
    h.probe.step(103,observation(103),threat(103,
      {projectiles:[liveMissile],created:true}));
    assert.equal(h.probe.summary().sawProjectile,true);
    h.probe.step(104,observation(104,"FireCasting"),threat(104));
    assert.equal(h.state.forcedCover,true,
      "despawn while FireCasting must not end cover");
    assert.equal(h.probe.summary().releaseTick,null);
    h.probe.step(105,observation(105,"Idle"),threat(105));
    assert.deepEqual(h.calls,[["setCover",true],["setCover",false]]);
    assert.equal(h.probe.summary().releaseTick,105);
    assert.equal(h.probe.summary().completed,true);
  }],
  ["an active boss projectile blocks release even in Idle",()=>{
    const h=harness();
    h.probe.step(100,observation(100),threat(100));
    h.probe.step(103,observation(103,"Idle"),threat(103,
      {projectiles:[liveMissile],created:true}));
    h.probe.step(104,observation(104,"Idle"),threat(104,
      {projectiles:[liveMissile],created:true}));
    assert.equal(h.probe.summary().sawProjectile,true);
    assert.equal(h.probe.summary().completed,false);
    assert.deepEqual(h.calls,[["setCover",true]]);
  }]
];

let failed=0;
for(const [name,run] of tests) {
  try {run();process.stdout.write("ok - "+name+"\n");}
  catch(error) {failed++;process.stderr.write("not ok - "+name+"\n"+
    (error.stack||String(error))+"\n");}
}
if(failed) process.exitCode=1;
