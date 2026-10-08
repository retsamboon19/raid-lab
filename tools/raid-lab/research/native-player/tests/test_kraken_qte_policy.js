// Small policy-contract tests only. No Frida, DLL, Unity, or native fight.
const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("node:path");
const vm = require("node:vm");

const source = fs.readFileSync(path.join(__dirname,
  "mechanics_kraken_qte_policy.js"), "utf8");
const createPolicy = vm.runInNewContext(source +
  "\ncreateMechanicsKrakenQtePolicy;");

function harness() {
  const calls = [], decisions = [];
  const state = {autoAim:true,forcedCover:false,focusedEntityId:1,
    focusedStance:0,inputType:1};
  const actions = {
    snapshot() { return {...state}; },
    setAutoAim(value) { calls.push(["setAutoAim",value]); state.autoAim=value; },
    focus(id) { calls.push(["focus",id]); state.focusedEntityId=id; },
    aimWorld(id,world,flag) { calls.push(["aimWorld",id,world[0],flag]); },
    press() { calls.push(["press"]); state.inputType=2;state.focusedStance=2; },
    release() { calls.push(["release"]);state.inputType=1;state.focusedStance=0; }
  };
  const policy = createPolicy(actions, row=>decisions.push(row));
  return {calls,decisions,state,policy};
}

function target(id,kind,time,position=[id,2,3]) {
  return {id,entityId:6302009,colType:{name:kind},state:{name:"Enable"},
    health:{hp:100},worldPosition:position,order:0,remainingNativeTime:time};
}

function observation(tick,groupId=212,targets=[target(11,"Break",10)]) {
  return {tick,qte:{supported:true,active:true,groupId,currentOrder:0,
      nativePresetSuccess:false,targets},
    squad:{supported:true,characters:[{id:2,health:{hp:1000},
      weapon:{type:{name:"AR"},ammo:30}}]},latestPresetEnd:null};
}

function through(h,first,last,build=observation) {
  for (let tick=first;tick<=last;tick++) h.policy.step(tick,build(tick));
}

const tests = [
  ["short Kraken chain prefers ready SMG over earlier-slot MG", () => {
    const h=harness();
    through(h,100,103,tick=>{
      const row=observation(tick);
      row.squad.characters=[
        {id:1,health:{hp:1000},weapon:{type:{name:"MG"},ammo:300}},
        {id:2,health:{hp:1000},weapon:{type:{name:"SMG"},ammo:120}}];
      return row;
    });
    assert.equal(h.decisions.find(row=>row.action==="take_manual_control").actorId,2);
  }],
  ["Break target takes priority over urgent Counter", () => {
    const h=harness();
    const targets=[target(4,"Counter",0,[4,0,0]),
      target(11,"Break",10,[11,0,0])];
    through(h,100,103,tick=>observation(tick,212,targets));
    assert.equal(h.calls.find(call=>call[0]==="aimWorld")[2],11);
    assert.equal(h.decisions.find(row=>row.action==="aim_break").targetId,11);
    assert.deepEqual([...h.decisions.find(row=>row.action==="aim_break")
      .avoidedCounterIds],[4]);
  }],
  ["reaction and settle ticks elapse before press", () => {
    const h=harness();
    through(h,100,102);
    assert.equal(h.calls.length,0,"no action before reaction tick 3");
    h.policy.step(103,observation(103));
    assert.deepEqual(h.calls.filter(call=>call[0]==="press"),[]);
    through(h,104,105);
    assert.deepEqual(h.calls.filter(call=>call[0]==="press"),[]);
    h.policy.step(106,observation(106));
    assert.equal(h.calls.filter(call=>call[0]==="press").length,1);
    assert.equal(h.policy.summary().reactionTicks,3);
    assert.equal(h.policy.summary().settleTicks,3);
  }],
  ["disappearing Break target releases held fire", () => {
    const h=harness();
    through(h,100,106);
    assert.equal(h.state.inputType,2);
    h.policy.step(107,observation(107,212,[]));
    assert.equal(h.state.inputType,1);
    assert.equal(h.calls.at(-1)[0],"release");
    assert.equal(h.policy.summary().targetId,null);
  }],
  ["unsupported group issues no gameplay command", () => {
    const h=harness();
    through(h,100,110,tick=>observation(tick,999));
    assert.equal(h.calls.length,0);
    assert.equal(h.policy.summary().owned,false);
    assert.equal(h.decisions.filter(row=>row.action==="unsupported").length,1);
  }],
  ["native failed preset restores auto without claiming success", () => {
    const h=harness();
    through(h,100,106);
    const ended=observation(107);
    ended.latestPresetEnd={tick:107,success:false,end:true};
    h.policy.step(107,ended);
    assert.equal(h.state.inputType,1);
    assert.equal(h.state.autoAim,true);
    assert.equal(h.policy.summary().owned,false);
    assert.equal(h.policy.summary().nativePresetSuccesses,0);
    assert.equal(h.policy.summary().nativePresetFailures,1);
    assert.equal(h.decisions.find(row=>row.action==="native_preset_result")
      .nativePresetSuccess,false);
  }],
  ["switch to unsupported group releases and restores ownership", () => {
    const h=harness();
    through(h,100,106);
    h.policy.step(107,observation(107,999));
    assert.equal(h.state.inputType,1);
    assert.equal(h.state.autoAim,true);
    assert.equal(h.policy.summary().owned,false);
    assert.equal(h.policy.summary().nativePresetSuccesses,0);
    assert.equal(h.calls.at(-1)[0],"setAutoAim");
  }]
];

let failed=0;
for (const [name,run] of tests) {
  try { run();process.stdout.write("ok - "+name+"\n"); }
  catch (error) {failed++;process.stderr.write("not ok - "+name+"\n"+
    (error.stack||String(error))+"\n");}
}
if (failed) process.exitCode=1;
