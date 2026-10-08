// Policy-contract fixtures only: no DLL, Unity, native boss, or accuracy claim.
const assert=require("node:assert/strict");
const fs=require("node:fs");
const path=require("node:path");
const vm=require("node:vm");
const source=fs.readFileSync(path.join(__dirname,"mechanics_qte_policy.js"),"utf8");
const createPolicy=vm.runInNewContext(source+"\ncreateMechanicsQtePolicy;");

function harness(initial={}) {
  const calls=[],decisions=[];
  const state={autoAim:true,forcedCover:false,focusedEntityId:1,
    focusedStance:0,inputType:1,...initial};
  const actions={
    snapshot(){return {...state};},
    setAutoAim(v){calls.push(["auto",v]);state.autoAim=v;},
    focus(id){calls.push(["focus",id]);state.focusedEntityId=id;},
    aimWorld(id,world,flag){calls.push(["aim",id,...world,flag]);},
    press(){calls.push(["press"]);state.inputType=2;state.focusedStance=2;},
    release(){calls.push(["release"]);state.inputType=1;state.focusedStance=0;}
  };
  return {calls,decisions,state,
    policy:createPolicy(actions,row=>decisions.push(row))};
}
const actor=(id,type="SMG",ammo=120)=>({id,health:{hp:"1000"},
  weapon:{type:{name:type},ammo}});
const target=(id,kind="Break",order=0,remainingNativeTime=10,extra={})=>({
  id,entityId:6000+id,colType:{name:kind},state:{name:"Enable"},
  order,remainingNativeTime,health:{hp:"100"},worldPosition:[id,2,3],...extra});
function observation(tick,overrides={}) {
  const {qte:qteOverrides,squad:squadOverrides,...rest}=overrides;
  return {tick,qte:{supported:true,active:true,groupId:771,currentIndex:0,
      currentOrder:0,targets:[target(11)],...qteOverrides},
    squad:{supported:true,characters:[actor(4100)],...squadOverrides},
    latestQuickTimeStart:null,latestPresetEnd:null,...rest};
}
function through(h,first,last,make=observation) {
  for(let tick=first;tick<=last;tick++) h.policy.step(tick,make(tick));
}
const tests=[
  ["native collider zero and group-key preset start from trial122 remain valid",()=>{
    const h=harness();
    through(h,100,106,tick=>observation(tick,{qte:{targets:[target(0)],groupId:212},
      latestPresetStart:{tick:100,index:212,isStart:true}}));
    assert.equal(h.decisions.find(d=>d.action==="aim_break").targetId,0);
    assert.deepEqual(Array.from(h.policy.summary().unsupported),[]);
    h.policy.step(107,observation(107,{qte:{targets:[target(2)],groupId:213,currentIndex:1},
      latestPresetStart:{tick:107,index:213,isStart:false}}));
    assert.equal(h.policy.summary().episode,1);
    assert.equal(h.policy.summary().groupId,213);
  }],
  ["three-tick sampled native input is accepted without pretending it is current",()=>{
    const h=harness();
    h.policy.step(100,observation(99));
    h.policy.step(101,observation(99));
    h.policy.step(102,observation(99));
    assert.equal(h.policy.summary().fault,null);
    h.policy.step(103,observation(99));
    assert.notEqual(h.policy.summary().fault,null);
  }],
  ["native reload switches to a ready actor without unsupported-state failure",()=>{
    const h=harness();through(h,100,106);
    h.policy.step(107,observation(107,{squad:{characters:[actor(4100,"SMG",0),actor(4101,"AR")]}}));
    assert.equal(h.policy.summary().actorId,4101);
    assert.deepEqual(Array.from(h.policy.summary().unsupported),[]);
  }],
  ["generic group chooses only live Break, never urgent Counter or Choice",()=>{
    const h=harness();
    through(h,100,106,tick=>observation(tick,{qte:{targets:[
      target(1,"Counter",0,0.1),target(2,"Choice",0,0.1),target(11,"Break",0,4)]}}));
    const aims=h.calls.filter(c=>c[0]==="aim");
    assert.ok(aims.length>0);
    assert.ok(aims.every(c=>c[2]===11));
    assert.equal(h.policy.summary().observedGroups[0],771);
  }],
  ["nonzero order follows native CurrentOrder and zero remains eligible",()=>{
    const h=harness();
    through(h,100,103,tick=>observation(tick,{qte:{currentOrder:2,
      targets:[target(1,"Break",1,0.1),target(2,"Break",2,5),
        target(3,"Break",0,6)]}}));
    assert.equal(h.decisions.find(d=>d.action==="aim_break").targetId,2);
    h.policy.step(104,observation(104,{qte:{currentOrder:3,
      targets:[target(1,"Break",1,0.1),target(3,"Break",3,1)]}}));
    assert.equal(h.decisions.filter(d=>d.action==="aim_break").at(-1).targetId,3);
    assert.ok(h.calls.every(c=>c[0]!=="aim"||c[2]!==1));
  }],
  ["expired native deadline releases held input and never fires expired target",()=>{
    const h=harness();through(h,100,106);
    assert.equal(h.state.inputType,2);
    h.policy.step(107,observation(107,{qte:{targets:[target(11,"Break",0,0)]}}));
    assert.equal(h.state.inputType,1);
    assert.equal(h.policy.summary().targetId,null);
  }],
  ["three reaction ticks and three target-settle ticks precede original press",()=>{
    const h=harness();through(h,100,102);
    assert.equal(h.calls.length,0);
    h.policy.step(103,observation(103));
    assert.equal(h.calls.filter(c=>c[0]==="press").length,0);
    through(h,104,106);
    assert.equal(h.calls.filter(c=>c[0]==="press").length,1);
  }],
  ["multiple presets and repeated same-group episode count native results once",()=>{
    const h=harness();through(h,100,106);
    h.policy.step(107,observation(107,{qte:{currentIndex:1,targets:[target(21)]},
      latestPresetEnd:{tick:107,presetInfoId:700,success:true,end:false}}));
    assert.equal(h.policy.summary().nativePresetSuccesses,1);
    assert.equal(h.policy.summary().completed,false);
    through(h,108,114,tick=>observation(tick,{qte:{currentIndex:1,targets:[target(21)]},
      latestPresetEnd:{tick:107,presetInfoId:700,success:true,end:false}}));
    assert.equal(h.policy.summary().nativePresetSuccesses,1);
    h.policy.step(115,observation(115,{qte:{currentIndex:1,targets:[]},
      latestPresetEnd:{tick:115,presetInfoId:701,success:true,end:true}}));
    assert.equal(h.policy.summary().nativeTerminalSuccesses,1);
    assert.equal(h.state.autoAim,true);
    h.policy.step(116,observation(116,{qte:{active:false,targets:[]}}));
    through(h,117,123,tick=>observation(tick,{qte:{targets:[target(31)]},
      latestPresetEnd:{tick:115,presetInfoId:701,success:true,end:true}}));
    assert.equal(h.policy.summary().episode,2);
    assert.equal(h.policy.summary().nativeTerminalSuccesses,1);
  }],
  ["native failed terminal result restores prior auto without success claim",()=>{
    const h=harness({autoAim:false});through(h,100,106);
    h.policy.step(107,observation(107,{qte:{targets:[]},
      latestPresetEnd:{tick:107,presetInfoId:700,success:false,end:true}}));
    assert.equal(h.state.autoAim,false);
    assert.equal(h.state.inputType,1);
    assert.equal(h.policy.summary().nativeTerminalFailures,1);
    assert.equal(h.policy.summary().nativeTerminalSuccesses,0);
  }],
  ["terminal native result is retained when context turns inactive that tick",()=>{
    const h=harness();through(h,100,106);
    h.policy.step(107,observation(107,{qte:{active:false,targets:[]},
      latestPresetEnd:{tick:107,presetInfoId:701,success:true,end:true}}));
    assert.equal(h.policy.summary().nativeTerminalSuccesses,1);
    assert.equal(h.state.autoAim,true);
  }],
  ["native end identity must match a seen original preset when IDs are exposed",()=>{
    const h=harness();
    through(h,100,106,tick=>observation(tick,{qte:{presetEntityId:700}}));
    h.policy.step(107,observation(107,{qte:{presetEntityId:700},
      latestPresetEnd:{tick:107,presetInfoId:999,success:true,end:true}}));
    assert.equal(h.policy.summary().nativeTerminalSuccesses,0);
    assert.ok(h.policy.summary().unsupported.includes(
      "native_preset_end_identity_mismatch"));
  }],
  ["new original preset-start event resets reaction even at the same index",()=>{
    const h=harness();through(h,100,106);
    h.policy.step(107,observation(107,{latestPresetStart:{tick:107,index:771,isStart:true}}));
    assert.equal(h.policy.summary().owned,false);
    assert.equal(h.state.inputType,1);
    h.policy.step(108,observation(108,{latestPresetStart:{tick:107,index:771,isStart:true}}));
    assert.equal(h.policy.summary().owned,false);
    h.policy.step(110,observation(110,{latestPresetStart:{tick:107,index:771,isStart:true}}));
    assert.equal(h.policy.summary().owned,true);
  }],
  ["preexisting press or external forced cover stays untouched",()=>{
    for (const initial of [{inputType:2},{forcedCover:true}]) {
      const h=harness(initial);through(h,100,106);
      assert.equal(h.calls.length,0);
      assert.equal(h.policy.summary().owned,false);
    }
  }],
  ["external focus ownership change releases and restores auto",()=>{
    const h=harness();through(h,100,106);
    h.state.focusedEntityId=4999;
    h.policy.step(107,observation(107));
    assert.equal(h.policy.summary().owned,false);
    assert.equal(h.state.inputType,1);
    assert.equal(h.state.autoAim,true);
  }],
  ["cover priority suspends without counting native outcome and resumes after cover",()=>{
    const h=harness();through(h,100,106);
    h.policy.suspend(106,"live_threat");
    assert.equal(h.state.inputType,1);
    assert.equal(h.state.autoAim,true);
    assert.equal(h.policy.summary().nativeTerminalSuccesses,0);
    h.state.forcedCover=true;
    const before=h.calls.length;
    through(h,107,110);
    assert.equal(h.calls.length,before);
    h.state.forcedCover=false;
    h.policy.step(111,observation(111));
    assert.equal(h.policy.summary().suspended,false);
    assert.equal(h.calls.filter(c=>c[0]==="press").length,1);
    through(h,112,117);
    assert.equal(h.calls.filter(c=>c[0]==="press").length,2);
  }],
  ["suspended QTE still records original terminal failure",()=>{
    const h=harness();through(h,100,106);
    h.policy.suspend(106,"cover");h.state.forcedCover=true;
    h.policy.step(107,observation(107,{qte:{active:false,targets:[]},
      latestPresetEnd:{tick:107,presetInfoId:701,success:false,end:true}}));
    assert.equal(h.policy.summary().nativeTerminalFailures,1);
    assert.equal(h.policy.summary().owned,false);
  }],
  ["deterministic ready SMG preference excludes empty and dead actors",()=>{
    const h=harness();through(h,100,103,tick=>observation(tick,{squad:{characters:[
      actor(1,"MG",300),actor(2,"SMG",0),actor(3,"AR",30),
      {...actor(4,"SMG",100),health:{hp:"0"}}]}}));
    assert.equal(h.decisions.find(d=>d.action==="take_manual_control").actorId,3);
  }],
  ["unknown type or missing live position fails closed",()=>{
    for (const hostile of [target(11,"Unknown"),
      target(11,"Break",0,10,{worldPosition:null})]) {
      const h=harness();through(h,100,106,tick=>observation(tick,{qte:{targets:[hostile]}}));
      assert.equal(h.calls.length,0);
      assert.ok(h.policy.summary().unsupported.includes(
        "unreadable_or_unknown_target_semantics"));
    }
  }],
  ["close releases owned input and blocks later actions",()=>{
    const h=harness();through(h,100,106);
    h.policy.close("test_end");
    const before=h.calls.length;
    h.policy.step(107,observation(107));
    assert.equal(h.calls.length,before);
    assert.equal(h.policy.summary().closed,true);
    assert.equal(h.state.autoAim,true);
  }]
];
let failed=0;
for(const [name,run] of tests) {
  try {run();process.stdout.write("ok - "+name+"\n");}
  catch(error){failed++;process.stderr.write("not ok - "+name+"\n"+
    (error.stack||String(error))+"\n");}
}
if(failed) process.exitCode=1;
