const assert=require('node:assert/strict');
const {squadCheckItems,burstTimingCheck}=require('./web/squad-checks.js');
const settings={duration:180};
const get=(team,key)=>squadCheckItems(team,settings).find(c=>c.key===key);
const stationary={duration:180,encounter_timeline:{simulated_until:180,checks:[]}};
assert.equal(get(stationary,'survival').state,'unknown');
assert.equal(get(stationary,'qte').state,'unknown');
assert.equal(get(stationary,'wait').state,'unknown');
const modeled={duration:180,encounter_timeline:{model:'experimental',simulated_until:180,survival:'survived modeled attacks',checks:[{status:'passed'}]}};
const whale={duration:180,encounter_timeline:{model:'Mother Whale',simulated_until:180,survival:'survived modeled attacks',qte_required:false,
 critical_parts:[{id:'mother-whale-core',status:'passed',hp:1000,remaining_hp:0,deadline:20,destroyed_at:18}],
 summons:[{hp:0,clear_reason:'squad damage'},{hp:0,clear_reason:'scripted withdrawal'}],barrier_windows:[{start:12,end:17}],damage_to_adds:90}};
assert.equal(get(whale,'parts').value,'Core break passed');
assert.equal(get(whale,'qte').value,'Not applicable');
assert.equal(get(whale,'summons').value,'1/2 cleared');
assert.match(get(whale,'summons').detail,/5.00s/);
assert.equal(get(whale,'survival').state,'pass');
whale.encounter_timeline.critical_parts[0].status='failed';
assert.equal(get(whale,'parts').state,'warn'); // Add clearing remains a valid alternative.
// Actual full-fight summon clearance is independent of the opening core deadline.
const preclearedWhale=structuredClone(whale);
preclearedWhale.encounter_timeline.critical_parts[0].destroyed_at=null;
preclearedWhale.encounter_timeline.critical_parts[0].remaining_hp=500;
preclearedWhale.encounter_timeline.summon_control={protection_casts:5,empty_protection_casts:5,
 precleared_casts:5,casts_with_survivors:0,protected_adds:0,core_disabled_protection:false,observed_until:180};
assert.equal(get(preclearedWhale,'parts').state,'warn');
assert.equal(get(preclearedWhale,'summon-control').state,'pass');
assert.equal(get(preclearedWhale,'summon-control').value,'5/5 waves pre-cleared');
assert.match(get(preclearedWhale,'summon-control').detail,/valid alternative to breaking the core/);
assert.match(get(preclearedWhale,'summon-control').detail,/actual target HP and death times/);
const protectedWhale=structuredClone(preclearedWhale);
Object.assign(protectedWhale.encounter_timeline.summon_control,{empty_protection_casts:4,
 precleared_casts:4,casts_with_survivors:1,protected_adds:3});
assert.equal(get(protectedWhale,'summon-control').state,'warn');
assert.equal(get(protectedWhale,'summon-control').value,'4/5 waves pre-cleared');
assert.match(get(protectedWhale,'summon-control').detail,/1 casts found surviving summons; 3 distinct summons received protection/);
// Breaking the core later cannot erase observed protection failures.
protectedWhale.encounter_timeline.summon_control.core_disabled_protection=true;
assert.equal(get(protectedWhale,'summon-control').state,'warn');
const noCastWhale=structuredClone(preclearedWhale);
Object.assign(noCastWhale.encounter_timeline.summon_control,{protection_casts:0,
 empty_protection_casts:0,precleared_casts:0});
assert.equal(get(noCastWhale,'summon-control').state,'unknown');
assert.equal(get(noCastWhale,'summon-control').value,'No buff cast observed');
// Empty waves without evidence of squad kills do not prove an AoE clear.
const emptyWhale=structuredClone(preclearedWhale);
emptyWhale.encounter_timeline.summon_control.precleared_casts=0;
assert.equal(get(emptyWhale,'summon-control').state,'unknown');
const disabledWhale=structuredClone(noCastWhale);
disabledWhale.encounter_timeline.summon_control.core_disabled_protection=true;
assert.equal(get(disabledWhale,'summon-control').state,'pass');
assert.equal(get(disabledWhale,'summon-control').value,'Protection disabled');
assert.match(get(disabledWhale,'summon-control').detail,/Core destruction disabled subsequent protection casts/);
assert.match(get(disabledWhale,'summon-control').detail,/^0 protection casts followed actual squad clearance/);
const partialClearWhale=structuredClone(preclearedWhale);
partialClearWhale.encounter_timeline.simulated_until=60;
assert.equal(get(partialClearWhale,'summon-control').state,'unknown');
disabledWhale.encounter_timeline.simulated_until=60;
assert.equal(get(disabledWhale,'summon-control').state,'unknown');
assert.equal(get(modeled,'survival').value,'Survived in model');
assert.equal(get(modeled,'qte').value,'Scripted checks passed');
const early=structuredClone(modeled);early.encounter_timeline.simulated_until=60;
assert.equal(get(early,'qte').state,'unknown');
assert.equal(get(early,'survival').state,'unknown');
const failed=structuredClone(modeled);failed.encounter_timeline.stop_reason='First squad death';failed.encounter_timeline.checks[0].status='failed';
assert.equal(get(failed,'survival').state,'fail');
assert.equal(get(failed,'qte').state,'fail');
const partial=structuredClone(modeled);partial.encounter_timeline.checks.push({status:'pending'});
assert.equal(get(partial,'qte').state,'unknown');
const cycling={bursts:5,burst_rotation:{covered:true,support_stages:['1','2'].map(stage=>({stage,status:'observed',casts:5})),stage_delays:[{delay:0}],uptime_pct:50,full_burst_seconds:90}};
assert.equal(get(cycling,'chain').state,'pass');
assert.equal(get(cycling,'wait').state,'unknown');
assert.equal(get(cycling,'uptime').state,'info');
cycling.burst_rotation.stage_delays.push({stage:'3',delay:8});
assert.equal(get(cycling,'wait').state,'unknown');
cycling.burst_rotation.covered=false;
assert.equal(get(cycling,'chain').state,'fail');
assert.equal(get({recommendation:{available_healers:['a']}},'healing').state,'info');
assert.equal(get({kit_dependencies:[{unit:'a',status:'not activated'}]},'partners').state,'warn');
assert.equal(get({kit_dependencies:[]},'partners').state,'info');
assert.equal(get({elemental_damage:{element:'Fire',providers:[]}},'element').state,'fail');
const timing={duration:90,burst_rotation:{
 full_bursts:[{start:2,end:12,complete:true},{start:18,end:23,complete:true},{start:29,end:44,complete:true},{start:52,end:90,complete:false}],
 stage_delays:[{stage:'1',cast_time:1},{stage:'1',cast_time:17},{stage:'1',cast_time:28},{stage:'1',cast_time:51}]
}};
assert.deepEqual(burstTimingCheck(timing,90),{passed:2,total:3,majority:true});
assert.equal(get(timing,'wait').value,'2/3 within 5s');
assert.equal(get(timing,'wait').state,'pass');
// Exactly five seconds passes; beyond it fails. The initial B1 is not counted.
timing.burst_rotation.stage_delays[2].cast_time=28.01;
assert.equal(get(timing,'wait').state,'warn');
// Even a large sum of individual waits must not decide this check.
timing.burst_rotation.stage_delays[2].cast_time=28;
timing.burst_rotation.stage_delays.forEach(s=>s.delay=50);
assert.equal(get(timing,'wait').state,'pass');
// Missing next activation counts as late once the full observation window elapsed.
timing.burst_rotation.stage_delays.pop();
assert.deepEqual(burstTimingCheck(timing,90),{passed:2,total:3,majority:true});
timing.encounter_timeline={simulated_until:46};
assert.deepEqual(burstTimingCheck(timing,90),{passed:2,total:2,majority:true});
// A tie is not a majority, and incomplete/missing timing cannot report a pass.
timing.burst_rotation.stage_delays[2].cast_time=28.01;
assert.equal(get(timing,'wait').state,'warn');
timing.encounter_timeline.simulated_until=16.99;
assert.equal(get(timing,'wait').state,'unknown');
// Public tests must work from a fresh ZIP without anyone's saved account data.
const report={settings,teams:Array.from({length:5},(_,i)=>({...structuredClone(stationary),damage:(i+1)*1000}))};
for(const team of report.teams){
 const checks=squadCheckItems(team,report.settings);
 assert.equal(checks.length,8+(report.settings.encounter?.critical_parts?.length?1:0));
 assert.equal(checks.find(c=>c.key==='qte').state,'unknown');
 assert.equal(checks.find(c=>c.key==='survival').state,'unknown');
 assert.ok(checks.every(c=>c.detail));
}
console.log('Squad checklist evidence tests passed, including a five-squad report.');

const partSettings={duration:180,encounter:{critical_parts:[{part:'Core',objective:'Break before buff.',consequence:'Adds become protected.',alternative:'Clear adds instead.',missing:['part HP','deadline']}]}};
const partCheck=squadCheckItems({...modeled,damage:999999999999},partSettings).find(c=>c.key==='parts');
assert.equal(partCheck.state,'unknown');
assert.equal(partCheck.value,'Break unverified');
assert.ok(partCheck.detail.includes('part HP'));
