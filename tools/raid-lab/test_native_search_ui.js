const assert = require('node:assert/strict'), fs = require('node:fs'), vm = require('node:vm');
const app = fs.readFileSync('web/app.js','utf8'), html = fs.readFileSync('web/index.html','utf8');
const nodes = new Map();
const $ = id => {if (!nodes.has(id)) nodes.set(id, {value:id==='budget'?'3':id==='nativeTeams'?'5':'',hidden:true});return nodes.get(id);};
let submitted, manualCalls=0, rendered;
const context = vm.createContext({$, Number, JSON, Promise, window:{}, BigInt,
  working:false, job:null, revision:1, jobRevision:0, roster:[{id:'a',build:{level:388}}],
  clone:x=>JSON.parse(JSON.stringify(x)), settings:()=>({encounter_id:'solo:1'}),
  notice:()=>{},busy:()=>{},switchTab:()=>{},beginActivity:()=>{},endActivity:()=>{},
  api:async (route,payload)=>{submitted={route,payload};return {id:'job'};},poll:()=>{},
  openManual:()=>manualCalls++, cancelSearch:()=>{}});
vm.runInContext(app.slice(app.indexOf("async function start(kind="),app.indexOf('async function poll(id)')),context);
vm.runInContext(app.split('\n').find(line=>line.startsWith("$('buildBtn').onclick=")),context);
(async()=>{
 await $('buildBtn').onclick();
 assert.equal(manualCalls,0);
 assert.equal(submitted.route,'search');
 assert.equal(submitted.payload.members,undefined);
 assert.deepEqual(JSON.parse(JSON.stringify(submitted.payload.search)),{budget:3,teams:5});
 assert.equal(submitted.payload.roster[0].build.level,388);
 assert.equal(submitted.payload.settings.encounter_id,'solo:1');
 assert(html.includes('Find teams &amp; simulate'));
 assert(!html.includes('Automatic team search is not connected'));
 assert(html.includes('/native-search.js'));
 vm.runInContext(fs.readFileSync('web/native-search.js','utf8'),context);
 const battle={score:'9007199254740993',nativeResult:2,durationMs:90000,characters:[{slot:1,damage:'9007199254740993'}],requestedInputs:{members:['a']}};
 const report={total:battle.score,teams:[{members:['a'],damage:battle.score,native:battle}],settings:{encounter:{name:'<boss>'}},simulations:1,elapsed:90,completion:{reason:'cancelled',requested_teams:5},selection:{objective:'Damage',method:'Tested'},candidates:[battle],failures:[],limits:[]};
 rendered=context.window.RaidNativeSearch.render(report,{a:{name:'<unit>',burst:'3'}});
 assert(rendered.includes('9,007,199,254,740,993'));
 assert(rendered.includes('&lt;unit&gt;'));
 assert(rendered.includes('data-manual="0"'));
 assert(rendered.includes('Keeping 1 of 5'));
 assert(!context.window.RaidNativeSearch.render(report,{},false).includes('data-manual'));
 battle.gameTotalDamage='5472459958';report.teams[0].damage=battle.gameTotalDamage;report.total=battle.gameTotalDamage;
 rendered=context.window.RaidNativeSearch.render(report,{});
 assert(rendered.includes('5,472,459,958 game total damage'));
 assert(rendered.includes('9,007,199,254,740,993 native aggregate'));
 console.log('Native search UI: automatic submit, options/builds, exact Int64, escaping, partial results, read-only history passed.');
})().catch(error=>{console.error(error);process.exitCode=1;});
