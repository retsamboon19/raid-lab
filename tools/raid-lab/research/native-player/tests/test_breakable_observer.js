// Synthetic bookkeeping tests only; these do not validate native Mirror play.
const assert=require('node:assert/strict');
const fs=require('node:fs');
const path=require('node:path');
const vm=require('node:vm');
const source=fs.readFileSync(path.join(__dirname,'mechanics_breakable_observer.js'),'utf8');
const context=vm.createContext({});
vm.runInContext(source,context,{filename:'mechanics_breakable_observer.js'});
const make=context.createBreakableEpisodeLedger;

{
  const log=make(2);
  log.observe({kind:'MonsterBreakColliderActiveStart',ownerId:8192,tick:40});
  log.observe({kind:'MonsterBreakColliderActiveStarted',ownerId:8192,tick:40});
  log.observe({kind:'MonsterBreakColliderHurt',ownerId:8192,tick:41,colliderId:0,damage:'10'});
  let e=log.summary().episodes[0];
  assert.equal(e.started,true);
  assert.equal(e.terminal,null);
  assert.equal(e.lastEvent.colliderId,0);
  assert.equal(e.eventCount,3);
  log.observe({kind:'MonsterAllBreakCollider',ownerId:8192,tick:42,isBreak:true,
    lastBrokenColliderId:0});
  e=log.summary().episodes[0];
  assert.equal(e.terminal.isBreak,true);
  assert.equal(e.terminal.lastBrokenColliderId,0);
  log.observe({kind:'MonsterBreakColliderActiveStart',ownerId:8192,tick:90});
  e=log.summary().episodes[0];
  assert.equal(e.startTick,90);
  assert.equal(e.started,false);
  assert.equal(e.terminal,null);
  assert.equal(e.eventCount,1);
  assert.equal(log.summary().eventCount,5);
}

{
  const log=make(2);
  log.observe({kind:'MonsterBreakColliderActiveStart',ownerId:10,tick:1});
  log.observe({kind:'MonsterBreakColliderActiveStart',ownerId:20,tick:2});
  log.observe({kind:'MonsterBreakColliderHurt',ownerId:10,tick:3,colliderId:4,damage:'1'});
  log.observe({kind:'MonsterBreakColliderActiveStart',ownerId:30,tick:4});
  assert.deepEqual(Array.from(log.summary().episodes.map(x=>x.ownerId)),[20,30]);
  assert.equal(log.summary().eventCount,4);
  assert.equal(log.summary().counts.MonsterBreakColliderActiveStart,3);
  assert.equal(log.summary().episodes[0].eventCount,1);
}

for (const row of [null,{kind:'x',ownerId:-1,tick:0},
  {kind:'x',ownerId:1,tick:-1},{kind:42,ownerId:1,tick:0}])
  assert.throws(()=>make().observe(row),/Invalid original break event row/);

assert.throws(()=>make(257),/Invalid break ledger limit/);
console.log('Break episode bookkeeping: 3 focused synthetic checks passed');
