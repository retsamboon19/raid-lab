// Mock original-hook contract only; no GameAssembly, player or asset access.
const assert=require("node:assert/strict");
const fs=require("node:fs");
const path=require("node:path");
const vm=require("node:vm");

const source=fs.readFileSync(path.join(__dirname,
  "mechanics_chatterbox_cover_probe.js"),"utf8");

function harness({tableId=510209,startNode=6}={}) {
  const callbacks=new Map(),events=[],calls=[];
  const state={forcedCover:false,autoAim:true,inputType:1};
  const memory=new Map();
  class Pointer {
    constructor(address) {this.address=address;}
    add(offset) {return new Pointer(this.address+offset);}
    equals(other) {return this.address===other.address;}
    isNull() {return this.address===0;}
    readS32() {return memory.get(this.address)||0;}
    readU32() {return this.readS32();}
    readFloat() {return memory.get(this.address)||0;}
    readPointer() {return new Pointer(this.readS32());}
    toInt32() {return this.address;}
  }
  const ptr=value=>new Pointer(value instanceof Pointer?value.address:value);
  const method=(name,rva)=>({name,relativeVirtualAddress:rva,
    virtualAddress:ptr(0x10000000+rva)});
  const makeClass=(name,fields={},methods={})=>({name,type:{name},
    field(key) {
      if (!(key in fields)) throw new Error("Missing mock field "+name+"."+key);
      const value=fields[key];
      return typeof value==="number"?{offset:value}:{value};
    },
    method(key) {
      if (!(key in methods)) throw new Error("Missing mock method "+name+"."+key);
      return methods[key];
    }
  });
  const timeline=makeClass("NK.Spot.BehaviorTree.Monster.Actions.TimelineSkill",
    {_aniNumberTypes:0x58,_passTime:0x84},{OnStart:method("OnStart",0x065485e0),
      PlayEnd:method("PlayEnd",0x06548dc0)});
  const task=makeClass("BehaviorDesigner.Runtime.Tasks.Task",{id:0x30});
  const battleAction=makeClass("NK.Spot.BehaviorTree.Monster.Behaviors.BattleAction",
    {mMonster:0x50});
  const sharedMonsterClass=makeClass(
    "NK.Spot.BehaviorTree.Variables.SharedBattleMonster");
  const battleMonsterClass=makeClass(
    "NK.Spot.BehaviorTree.Models.BattleMonster",
    {"<Monster>k__BackingField":0x10});
  const monsterClass=makeClass("NK.Spot.Model.Monster.SpotMonster",
    {"<Data>k__BackingField":0x88});
  const monsterData=makeClass("NK.Spot.Monster.Model.MonsterData",{SkillList:0x30},
    {GetSkill:method("GetSkill",0x06341d70)});
  const skillClass=makeClass("NK.Spot.Model.Monster.SpotMonsterSkill",
    {SkillStaticInfo:0x18,AniNumberType:0x30,TimelineLoopStartTime:0xe0});
  const skillInfoClass=makeClass(
    "NK.StaticData.StaticDataLayer.StaticInfo.MonsterSkillStaticInfo",{},
    {get_TableId:method("get_TableId",0x03e05810)});
  const boxed=value=>({field(name) {
    if (name!=="value__") throw new Error(name);
    return {value};
  }});
  const conditionClass=makeClass("NK.Spot.Model.Monster.MonsterConditionType",
    {FireCasting:boxed(9),Fire:boxed(10),Idle:boxed(1)});
  const eventClass=makeClass("NK.Spot.Event.Monster.MonsterConditionEvent",
    {MonsterInfo:0x40,CurrentCondition:0x48});
  const classes=new Map([
    [timeline.name,timeline],[monsterData.name,monsterData],
    [monsterClass.name,monsterClass],[battleAction.name,battleAction],
    [sharedMonsterClass.name,sharedMonsterClass],
    [battleMonsterClass.name,battleMonsterClass],
    [skillClass.name,skillClass],[skillInfoClass.name,skillInfoClass],
    [conditionClass.name,conditionClass],[eventClass.name,eventClass],
    ["NK.Spot.Logic.Character.SpotEntityInfo",
      makeClass("NK.Spot.Logic.Character.SpotEntityInfo",{EntityID:0x10})],
    ["NK.Spot.SpotManagement",makeClass("NK.Spot.SpotManagement",{_tickCount:0x64})]
  ]);
  const action=ptr(0x1000),selected=ptr(0x2000),info=ptr(0x3000),
    monster=ptr(0x4000),eventPtr=ptr(0x5000),managementPtr=ptr(0x6000),
    battleMonster=ptr(0x8000),shared=ptr(0x9000),data=ptr(0xa000);
  memory.set(action.add(0x30).address,startNode);
  memory.set(action.add(0x50).address,shared.address);
  memory.set(monster.add(0x10).address,8192);
  memory.set(eventPtr.add(0x40).address,monster.address);
  const aniList={kind:"ani",isNull(){return false;},method(key){return {name:key};}};
  const skillList={kind:"skills",isNull(){return false;},method(key){return {name:key};}};
  const infoObj={isNull(){return false;},class:skillInfoClass};
  const selectedObj={handle:selected,isNull(){return false;},class:skillClass,
    field(name) {
      if (name==="AniNumberType") return {value:{field(){return {value:9};}}};
      if (name==="SkillStaticInfo") return {value:infoObj};
      if (name==="TimelineLoopStartTime") return {value:0};
      throw new Error(name);
    }};
  const dataObj={isNull(){return false;},class:monsterData,
    field(name){if(name==="SkillList")return {value:skillList};throw new Error(name);}};
  const monsterObj={isNull(){return false;},class:monsterClass,field(name) {
    if (name==="<Data>k__BackingField") return {value:dataObj};
    throw new Error(name);
  }};
  const wrapperObj={isNull(){return false;},class:battleMonsterClass,field(name) {
    if (name==="<Monster>k__BackingField") return {value:monsterObj};
    throw new Error(name);
  }};
  const sharedObj={isNull(){return false;},class:sharedMonsterClass,method(name) {
    if (name==="get_Value") return {name};
    throw new Error(name);
  }};
  const managed=new Map([
    [action.address,{class:timeline,field(name) {
      if (name==="id") return {value:startNode};
      if (name==="_aniNumberTypes") return {value:aniList};
      if (name==="_passTime") return {value:0};
      if (name==="mMonster") return {value:sharedObj};
      throw new Error(name);
    }}],
    [selected.address,selectedObj],
    [battleMonster.address,monsterObj]
  ]);
  class ManagedObject {
    constructor(pointer) {
      const object=managed.get(pointer.address);
      if (!object) throw new Error("Unmapped managed pointer");
      return object;
    }
  }
  const sandbox={
    Process:{getModuleByName(){return {base:ptr(0x10000000)};},
      getCurrentThreadId(){return 1;}},
    Il2Cpp:{domain:{assembly(name){return {image:{class(className){
      if (name==="BehaviorDesigner.Runtime") return task;
      if (name==="NK.Runtime.StaticData" && className===skillInfoClass.name)
        return skillInfoClass;
      throw new Error("Unexpected mock assembly/class "+name+"/"+className);
    }}};}},
      Object:ManagedObject},
    Interceptor:{attach(address,handlers){callbacks.set(address.address-0x10000000,handlers);}},
    ptr,
    invokeChecked(method,self) {
      if (method.name==="get_Value" && self===sharedObj) return wrapperObj;
      if (method.name==="get_Item" && self===skillList) return selectedObj;
      const result=method.name==="get_Count"?1:method.name==="get_Item"?9:
        method.name==="get_TableId"?tableId:null;
      if (result===null) throw new Error("Unexpected managed method");
      return {unbox(){return {handle:{readS32(){return result;}}};}};
    },
    intArg(value){return value;}
  };
  const create=vm.runInNewContext(source+"\ncreateMechanicsChatterboxCoverProbe;",sandbox);
  const management={handle:managementPtr,isNull(){return false;}};
  const actions={snapshot(){return {...state};},setCover(value) {
    calls.push(value);state.forcedCover=value;
  }};
  const probe=create({class:name=>classes.get(name)},management,actions,
    event=>events.push(event));
  const setTick=value=>memory.set(managementPtr.add(0x64).address,value);
  const start=(observeSkill=true,returnRva=0x0654892a)=>{
    const startHook=callbacks.get(0x065485e0),getSkill=callbacks.get(0x06341d70);
    const startContext={};
    startHook.onEnter.call(startContext,[action]);
    if (observeSkill) {
      const skillContext={returnAddress:ptr(0x10000000+returnRva)};
      getSkill.onEnter.call(skillContext,[ptr(0x7000),ptr(9)]);
      getSkill.onLeave.call(skillContext,selected);
    }
    startHook.onLeave.call(startContext);
  };
  const condition=value=>{
    memory.set(eventPtr.add(0x48).address,value);
    probe.observeSendEvent({handle:eventPtr,isNull(){return false;},class:eventClass});
  };
  const end=(self=action)=>callbacks.get(0x06548dc0).onEnter([self]);
  return {probe,calls,events,state,setTick,start,condition,end};
}

const tests=[
  ["original node, skill, first cast and matching PlayEnd bound one cover episode",()=>{
    const h=harness();
    h.setTick(4);h.start();h.condition(9);h.probe.afterTick(4);
    h.setTick(5);h.probe.beforeTick(5);
    assert.deepEqual(h.calls,[true]);
    h.setTick(87);h.condition(10);h.probe.afterTick(87);
    h.setTick(88);h.probe.beforeTick(88);
    assert.deepEqual(h.calls,[true]);
    h.setTick(196);h.end();h.probe.afterTick(196);
    h.setTick(197);h.probe.beforeTick(197);
    assert.deepEqual(h.calls,[true,false]);
    assert.equal(h.probe.summary().completed,true);
    assert.equal(h.probe.summary().fired.tick,87);
    assert.equal(h.state.autoAim,true);
    assert.equal(h.probe.summary().coverFeasibility,"unvalidated");
  }],
  ["condition alone and unrelated node cannot acquire input",()=>{
    const h=harness({startNode:7});
    h.setTick(4);h.start();h.condition(9);h.probe.afterTick(4);
    h.setTick(5);h.probe.beforeTick(5);
    assert.deepEqual(h.calls,[]);
  }],
  ["wrong original skill fails closed before cover",()=>{
    const h=harness({tableId:510208});
    h.setTick(4);h.start();h.condition(9);
    assert.throws(()=>h.probe.afterTick(4),/skill is 510208/);
    assert.deepEqual(h.calls,[]);
  }],
  ["original retained skill path works when nested hook sees no return",()=>{
    const h=harness();
    h.setTick(4);h.start(false);h.condition(9);h.probe.afterTick(4);
    h.setTick(5);h.probe.beforeTick(5);
    assert.deepEqual(h.calls,[true]);
    assert.equal(h.probe.summary().firstStart.skillId,510209);
  }],
  ["nested GetSkill from another caller is excluded",()=>{
    const h=harness();
    h.setTick(4);h.start(true,0x06548930);h.condition(9);h.probe.afterTick(4);
    h.setTick(5);h.probe.beforeTick(5);
    assert.deepEqual(h.calls,[true]);
    assert.equal(h.probe.summary().firstStart.nestedGetSkillCalls,0);
  }],
  ["another node 6 instance cannot release the acquired cover",()=>{
    const h=harness();
    h.setTick(4);h.start();h.condition(9);h.probe.afterTick(4);
    h.setTick(5);h.probe.beforeTick(5);
    // A different node 6 pointer reaches PlayEnd first.
    const other={address:0x9000,add(offset){return {readS32(){return offset===0x30?6:0;}};},
      isNull(){return false;},equals(value){return value.address===0x9000;}};
    h.setTick(100);h.end(other);h.probe.afterTick(100);
    h.setTick(101);h.probe.beforeTick(101);
    assert.deepEqual(h.calls,[true]);
    assert.equal(h.probe.summary().end,null);
  }]
];
let failures=0;
for (const [name,run] of tests) {
  try {run();process.stdout.write("ok - "+name+"\n");}
  catch(error) {failures++;process.stderr.write("not ok - "+name+"\n"+
    (error.stack||String(error))+"\n");}
}
if (failures) process.exitCode=1;
