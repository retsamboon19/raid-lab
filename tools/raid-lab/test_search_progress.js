const assert=require('node:assert/strict'),fs=require('node:fs'),vm=require('node:vm');
const source=fs.readFileSync('web/app.js','utf8');
const elements=new Map();
const $=id=>{if(!elements.has(id))elements.set(id,{style:{},attributes:{},setAttribute(k,v){this.attributes[k]=v}});return elements.get(id)};
const context=vm.createContext({$,Number,Math,String});
vm.runInContext(source.slice(source.indexOf('let working=false'),source.indexOf('async function start(kind=')),context);
vm.runInContext('setActivityProgress(.4);setActivityProgress(.2)',context);
assert.equal($('activityFill').style.width,'40%');
assert.equal($('activityBar').attributes['aria-valuenow'],'40');
vm.runInContext('setActivityProgress(1)',context);
assert.equal($('activityFill').style.width,'100%');
assert.equal($('activityFill').textContent,undefined); // No percentage number displayed.
const css=fs.readFileSync('web/style.css','utf8');
assert(!css.includes('search-sweep'));
assert(!css.includes('animation:search'));
console.log('Determinate search progress: monotonic, completes, no visible percentage or sweep.');
