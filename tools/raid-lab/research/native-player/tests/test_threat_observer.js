// Native-shaped observer contract tests. No DLL, hooks, game, or Frida process.
const assert=require("node:assert/strict");
const fs=require("node:fs");
const path=require("node:path");
const vm=require("node:vm");

const source=fs.readFileSync(path.join(__dirname,
  "mechanics_threat_observer.js"),"utf8");

const R={
  "NK.Spot.SpotManagement.SendEventDefault":0x0614BAF0,
  "NK.Spot.Logic.Monster.MonsterAttackLogic.FireProjectile":0x063BDC00,
  "NK.Spot.ProjectileContext.OnProjectileCreate":0x06142DB0
};
const O={
  "NK.Spot.SpotManagement":{_tickCount:0x64,_playtime:0x6c},
  "NK.Spot.Common.SpotEvent":{"<SpotEventID>k__BackingField":0x14},
  "NK.Spot.Logic.Character.SpotEntityInfo":{EntityID:0x10,ObjectType:0x14},
  "NK.Spot.Event.Monster.MonsterAttackEvent":{
    CasterInfo:0x40,TargetInfo:0x48,AttackNodeID:0x64,AniNumber:0x5c},
  "NK.Spot.Event.Projectile.ProjectileCreateEvent":{Data:0x40,IsCharacter:0x48},
  "NK.Spot.Event.Projectile.ProjectileData":{
    OwnerId:0x10,TargetId:0x58,SkillId:0x5c,IsDestroyable:0x60},
  "NK.Spot.Event.Projectile.ProjectileSpawnEvent":{
    CasterInfo:0x40,ProjectileInfo:0x48},
  "NK.Spot.Event.Projectile.ProjectileDespawnEvent":{
    ProjectileInfo:0x40,DespawnTypeEnum:0x54},
  "NK.Spot.Event.Common.OnEntityGetDamageEvent":{
    CasterInfo:0x40,TargetInfo:0x48,TargetSubID:0x50,Damage:0x58,
    ActualDamage:0x60,DamageType:0x68,IsCritical:0x78,
    IsImmune:0x79,IsShare:0x7a},
  "NK.Spot.Event.Character.CoverTakeDamageEvent":{
    CasterInfo:0x40,CoverInfo:0x48,Damage:0x60},
  "NK.Common.StatValue":{Value:0x10}
};
const EVENT_IDS={MonsterAttack:1,ProjectileCreate:2,ProjectileSpawn:3,
  ProjectileDespawn:4,OnEntityGetDamage:5,CoverTakeDamage:6};
const TYPES={Character:1,Cover:2,Monster:3,Projectile:4};
const ptr=value=>({value,equals(other){return this.value===other.value;}});

function harness(configuration) {
  const classes=new Map(), emitted=[];
  const fakeClass=name=>{
    if (!classes.has(name)) classes.set(name,{
      type:{name},name,
      field(fieldName) {
        if (name==="NK.Spot.Common.SpotEvent.SpotEventType")
          return {value:EVENT_IDS[fieldName]};
        if (name==="NK.Spot.Model.Enum.SpotObjectType")
          return {value:TYPES[fieldName]};
        const offset=O[name]?.[fieldName];
        if (offset===undefined) throw new Error("Unexpected field "+name+"."+fieldName);
        return {offset};
      },
      method(methodName) {
        const rva=R[name+"."+methodName];
        if (rva===undefined) throw new Error("Unexpected method "+name+"."+methodName);
        return {virtualAddress:ptr(rva)};
      },
      nested(nestedName){return fakeClass(name+"."+nestedName);}
    });
    return classes.get(name);
  };
  const runtime={class:fakeClass};
  const clock={tick:0,time:0};
  const management={class:fakeClass("NK.Spot.SpotManagement"),
    isNull(){return false;},
    method(name){return this.class.method(name);},
    field(name){return {value:name==="_tickCount"?clock.tick:clock.time};}
  };
  const Process={getModuleByName(name){
    assert.equal(name,"GameAssembly.dll");return {base:{add:ptr}};
  }};
  const create=vm.runInNewContext(source+"\ncreateMechanicsThreatObserver;",
    {Process});
  const observer=create(runtime,management,row=>emitted.push(row),configuration);
  const object=(name,fields)=>({class:fakeClass(name),isNull(){return false;},
    field(fieldName){
      if (!(fieldName in fields)) throw new Error("Missing fixture field "+fieldName);
      return {value:fields[fieldName]};
    }});
  const info=(id,type=TYPES.Monster)=>object(
    "NK.Spot.Logic.Character.SpotEntityInfo",{EntityID:id,ObjectType:type});
  const stat=value=>object("NK.Common.StatValue",{Value:String(value)});
  const event=(className,kind,fields)=>object(className,
    {"<SpotEventID>k__BackingField":EVENT_IDS[kind],...fields});
  const attack=(casterId,node=230,type=TYPES.Monster)=>event(
    "NK.Spot.Event.Monster.MonsterAttackEvent","MonsterAttack",
    {CasterInfo:info(casterId,type),TargetInfo:info(1,TYPES.Character),
      AttackNodeID:node,AniNumber:0});
  const projectileCreate=(ownerId,skillId=532033)=>event(
    "NK.Spot.Event.Projectile.ProjectileCreateEvent","ProjectileCreate",
    {Data:object("NK.Spot.Event.Projectile.ProjectileData",
      {OwnerId:ownerId,TargetId:1,SkillId:skillId,IsDestroyable:true}),
      IsCharacter:false});
  const spawn=(casterId,projectileId,type=TYPES.Monster)=>event(
    "NK.Spot.Event.Projectile.ProjectileSpawnEvent","ProjectileSpawn",
    {CasterInfo:info(casterId,type),ProjectileInfo:info(projectileId,TYPES.Projectile)});
  const despawn=projectileId=>event(
    "NK.Spot.Event.Projectile.ProjectileDespawnEvent","ProjectileDespawn",
    {ProjectileInfo:info(projectileId,TYPES.Projectile),DespawnTypeEnum:0});
  const damage=casterId=>event(
    "NK.Spot.Event.Common.OnEntityGetDamageEvent","OnEntityGetDamage",
    {CasterInfo:info(casterId),TargetInfo:info(1,TYPES.Character),
      TargetSubID:0,Damage:stat(100),ActualDamage:stat(90),DamageType:0,
      IsCritical:false,IsImmune:false,IsShare:false});
  const send=(tick,...events)=>{
    clock.tick=tick;clock.time=tick/30;
    for (const item of events) observer.observeSendEvent(item);
    return observer.snapshot(tick);
  };
  return {observer,emitted,send,attack,projectileCreate,spawn,despawn,
    damage,info,event,object};
}

const tests=[
  ["no-config Kraken receipt keeps ID and watch-node behavior",()=>{
    const h=harness();
    const first=h.send(1,h.attack(9000,229),h.attack(8192,228));
    assert.equal(first.latestAttack.casterId,8192);
    assert.equal(h.emitted.filter(row=>row.status==="original_threat_event").length,0);
    h.send(2,h.attack(8192,229));
    const summary=h.observer.summary();
    assert.deepEqual([...summary.watchesFromAttackNodes],[229,230]);
    assert.equal(summary.counts.attack,2);
    assert.equal(summary.unwatchedLogs,1);
  }],
  ["two native Monster casters retain independent attack/projectile/damage state",()=>{
    const h=harness({mode:"monster"});
    const first=h.send(1,h.attack(10,301),h.attack(20,302),
      h.projectileCreate(10,111),h.spawn(10,101),
      h.projectileCreate(20,222),h.spawn(20,202),h.damage(20));
    assert.deepEqual([...first.casters.map(c=>c.casterId)],[10,20]);
    assert.equal(first.casters[0].recentAttacks[0].attackNodeId,301);
    assert.equal(first.casters[1].recentAttacks[0].attackNodeId,302);
    assert.equal(first.casters[0].activeProjectiles[0].source.skillId,111);
    assert.equal(first.casters[1].activeProjectiles[0].source.skillId,222);
    assert.equal(first.casters[1].latestDamage.casterId,20);
    const next=h.send(2,h.despawn(101));
    assert.deepEqual([...next.casters[0].activeProjectileIds],[]);
    assert.deepEqual([...next.casters[1].activeProjectileIds],[202]);
    assert.equal(next.casters[0].latestDespawn.casterId,10);
  }],
  ["intervening dispatch forbids create-spawn skill inference",()=>{
    const h=harness({mode:"verified_ids",verifiedBossIds:[10]});
    const unrelated=h.object("Unrelated.OriginalEvent",{});
    const snap=h.send(1,h.projectileCreate(10,111),unrelated,h.spawn(10,101));
    assert.equal(snap.casters[0].activeProjectiles[0].source,null);
    assert.equal(snap.casters[0].latestSpawn.sourceBinding,"unknown");
    assert.equal(h.observer.summary().unlinkedCreates,1);
    assert.equal(h.observer.summary().unknownSpawns,1);
  }],
  ["unclassified create before Monster identity never gains invented source",()=>{
    const h=harness({mode:"monster"});
    const snap=h.send(1,h.projectileCreate(10,111),h.spawn(10,101));
    assert.equal(snap.casters[0].activeProjectiles[0].source,null);
    assert.equal(h.observer.summary().unclassifiedCreates,1);
    assert.equal(h.observer.summary().unknownSpawns,1);
  }],
  ["repeated attacks retain only configured bounded history",()=>{
    const h=harness({mode:"monster",maxRecentAttacks:2});
    const snap=h.send(1,h.attack(10,1),h.attack(10,2),h.attack(10,3));
    assert.deepEqual([...snap.casters[0].recentAttacks.map(r=>r.attackNodeId)],[2,3]);
    assert.equal(snap.attackHistoryTruncated,true);
    assert.equal(h.observer.summary().historyDropped,1);
  }],
  ["generic event emission reports explicit truncation after bound",()=>{
    const h=harness({mode:"monster"});
    const rows=Array.from({length:202},(_,i)=>h.attack(10,1000+i));
    const snap=h.send(1,...rows);
    const summary=h.observer.summary();
    assert.equal(summary.emitted,200);
    assert.equal(summary.droppedLogs,2);
    assert.equal(summary.transitionsTruncated,true);
    assert.equal(snap.eventsTruncated,true);
  }],
  ["too many distinct casters fails closed as unsupported",()=>{
    const h=harness({mode:"monster"});
    const rows=Array.from({length:33},(_,i)=>h.attack(100+i));
    const snap=h.send(1,...rows);
    assert.equal(snap.supported,false);
    assert.match(snap.fault,/caster count exceeds bound/);
    assert.throws(()=>h.observer.checkFault(),/caster count exceeds bound/);
  }]
];

let failures=0;
for (const [name,run] of tests) {
  try {run();process.stdout.write("ok - "+name+"\n");}
  catch(error) {failures++;process.stderr.write("not ok - "+name+"\n"+
    (error.stack||String(error))+"\n");}
}
if(failures) process.exitCode=1;
