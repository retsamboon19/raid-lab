const assert = require('node:assert/strict');
const history = require('./web/history.js');
const tick = () => new Promise(resolve => setImmediate(resolve));
const run = (id='a') => ({id,created_at:'2026-09-13T00:00:00Z',kind:'search',mode:'museum',boss_id:'whale',boss_name:'Whale',museum_mode:'challenge',duration:180,total:5e9,requested_teams:5,completion_reason:'completed',teams:Array.from({length:5},(_,i) => ({index:i+1,damage:1e9,members:Array.from({length:5},(_,j) => ({id:`unit${i}${j}`,name:`Saved <unit ${i}${j}>`,element:'Electric',burst:'3',weapon:'RL'}))}))});
const modes = [{id:'museum',name:'Museum',bosses:[{id:'whale',name:'Whale',count:12}]},{id:'anomaly',name:'Anomaly',bosses:[{id:'kraken',name:'Kraken',count:1}]}];
const page = (runs=[],total=runs.length,has_more=false) => ({modes,runs,total,has_more});
const card = history.runCard(run(),true);
assert.equal((card.match(/class="history-lineup"/g)||[]).length,5);
assert.equal((card.match(/data-history-open=/g)||[]).length,1);
assert(card.includes('5B'));
assert(card.includes('Saved &lt;unit 00&gt;'));
assert(!card.includes('<unit'));
const partial = run(); partial.teams = partial.teams.slice(0,3); partial.completion_reason = 'cancelled';
assert.equal(history.squadCount(partial),'3/5 squads');
assert(history.runCard(partial,false).includes('Cancelled · best completed results'));

// Minimal DOM surface: exercise asynchronous view state without a browser or live server.
const elements = new Map(), listeners = {}, pending = [];
const element = id => {if(!elements.has(id)) elements.set(id,{innerHTML:'',value:'',hidden:false,disabled:false,focus(){this.focused=true;},scrollIntoView(){},insertAdjacentHTML(_,html){this.innerHTML += html;}}); return elements.get(id);};
const root = {hidden:false,querySelector(selector){return element(selector.slice(1));},querySelectorAll(){return [];},addEventListener(type,fn){listeners[type]=fn;}};
let exported, checkSettings;
const ui = history.create({root,api:path => new Promise((resolve,reject) => pending.push({path,resolve,reject})),getCatalog:() => ({unit00:{name:'TODAY NAME',weapon:'MG'}}),download:(filename,value) => {exported=value;},getModelRevision:()=>"current-model",checks:(team,settings) => {checkSettings=settings;return [];}});
const click = (dataset={},attributes=[]) => listeners.click({target:{closest:() => ({dataset,hasAttribute:k => attributes.includes(k)})}});
async function main() {
 ui.show(); assert.equal(pending[0].path,'history');
 pending.shift().resolve(page()); await tick();
 assert.equal(element('historyBoss').disabled,true);
 element('historyMode').value='museum'; element('historyMode').onchange();
 const oldRequest = pending.shift();
 element('historyMode').value='anomaly'; element('historyMode').onchange();
 pending.shift().resolve(page()); await tick();
 oldRequest.resolve({modes:[],runs:[],total:0,has_more:false}); await tick();
 assert.equal(ui.state.mode,'anomaly'); assert.equal(ui.state.modes.length,2);
 element('historyMode').value='museum'; element('historyMode').onchange(); pending.shift().resolve(page()); await tick();
 element('historyBoss').value='whale'; element('historyBoss').onchange();
 assert.equal(pending[0].path,'history?mode=museum&boss=whale&offset=0&limit=10');
 pending.shift().resolve(page([run('a'),run('b')],3,true)); await tick();
 element('historyMore').onclick(); assert(pending[0].path.includes('offset=2'));
 pending.shift().resolve(page([run('c')],4,false)); await tick();
 assert(pending[0].path.includes('offset=0')); // New run shifted page: restart safely.
 pending.shift().resolve(page([run('new'),run('a'),run('b'),run('c')],4)); await tick();
 assert.equal(ui.state.runs.length,4);
 click({historyOpen:'a'}); const slowDetail = pending.shift();
 click({},['data-history-back']);
 slowDetail.resolve({}); await tick();
 assert.equal(ui.state.detail,null); assert.equal(element('historyDetail').hidden,true);
 const summary = run('a'), saved = {settings:{duration:180,encounter:{name:'Saved boss'}},simulations:'<img src=x>',elapsed:'<img src=x>',teams:summary.teams.map(t => ({members:t.members.map(m => m.id),bursts:'<img src=x>',damage:t.damage,builds:{exact:123}}))};
 const before = JSON.stringify(saved);
 click({historyOpen:'a'}); pending.shift().resolve({id:'a',created_at:summary.created_at,summary,report:saved}); await tick();
 const html = element('historyDetail').innerHTML;
 assert(html.includes('Saved with an earlier model.'));
 assert(html.includes('historySquadTab4')); assert(!html.includes('id="squadTab'));
 assert(html.includes('Saved &lt;unit 00&gt;')); assert(!html.includes('TODAY NAME'));
 assert(html.includes('&lt;img src=x&gt;')); assert(!html.includes('<img src=x>'));
 assert(!html.includes('Adjust & simulate')); assert.equal(checkSettings,saved.settings);
 assert.equal(JSON.stringify(saved),before);
 click({},['data-history-export']); assert.equal(exported,saved);
 ui.invalidate(); click({},['data-history-back']); pending.shift().resolve(page([run('a')],1)); await tick();
 assert.equal(element('historyMode').focused,true); // Restores a safe focus target after refresh.
 console.log('History UI checks passed: grouped squads, escaped snapshots, filter races, pagination, navigation, and exact read-only export.');
}
main().catch(error => {console.error(error);process.exitCode=1;});
