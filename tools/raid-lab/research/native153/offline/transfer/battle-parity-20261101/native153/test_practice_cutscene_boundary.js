'use strict';
const fs=require('fs'),vm=require('vm'),assert=require('assert');
const source=fs.readFileSync(__dirname+'/practice_geometry.js','utf8');
const original=JSON.parse(fs.readFileSync(__dirname+'/practice-cutscene-control-binding.json','utf8'));
function run(options={}){
  const binding=JSON.parse(JSON.stringify(original)),events=[],calls=[],pinned=[];
  let id=1;
  function object(type){const handle={id:id++,equals(other){return this.id===other.id;}};
    return {handle,class:{type:{name:type}},isNull(){return false;},method(name,count){
      calls.push(['lookup',name,count]);return {name,relativeVirtualAddress:binding.directorDurationGetter.rva};}};}
  const intro=object('UnityEngine.Playables.PlayableDirector'),ui=object('UnityEngine.Playables.PlayableDirector');
  const uiObject=object('UnityEngine.GameObject'),board=object('UnityEngine.GameObject');
  const values={_introCutScene:intro,_introCutSceneUI:options.sameDirector?intro:ui,
    _introCutSceneUIObject:uiObject,_skipSpeed:binding.serializedSkipSpeed,
    _modeBoard:{length:1,isNull:()=>false,get:()=>board}};
  Object.assign(values,options.values||{});
  const specs=new Map(binding.fieldLayouts.map(f=>[f.name,f]));
  const control=object(options.wrongType?'Other.Control':binding.componentType);
  control.field=name=>{
    const spec=specs.get(name);return {offset:spec.offset+(options.badLayout?4:0),type:{name:spec.type},
      isStatic:!!options.staticField,get value(){return values[name];},set value(_){throw Error('UNAUTHORIZED NATIVE WRITE');}};
  };
  control.method=(name,count)=>{calls.push(['lookup',name,count]);return {name,
    relativeVirtualAddress:binding.originalMethodRvas[name]+(options.badMethod?1:0)};};
  if(options.badGetter)intro.method=()=>({name:'get_duration',relativeVirtualAddress:1});
  const context={globalThis:null,ArrayBuffer,DataView,Uint8Array,Number,Array,Error};context.globalThis=context;
  context.PRACTICE_CUTSCENE_CONTROL_SOURCE_SHA256='test-only';vm.runInNewContext(source,context);
  const live=(value,type,label)=>{
    if(!value||value.isNull()||value.class.type.name!==type||options.unityNull===label)throw Error('Unity-null/type: '+label);
    pinned.push(value);return value;};
  const call=(method,self)=>{calls.push(['invoke',method.name,self]);if(options.nativeError)throw options.nativeError;
    return {unbox:()=>({handle:{readDouble:()=>options.duration===undefined?4.4:options.duration}})};};
  const result=context.verifyOriginalPracticeCutsceneReferences(control,binding,live,call,x=>{pinned.push(x);return x;},x=>events.push(x));
  return {result,events,calls,pinned};
}
let checks=0;const check=fn=>{fn();checks++;};
check(()=>{const r=run();assert.equal(r.result.originalDuration,4.4);assert.equal(r.result.durationBits,'cdcc8c40');
  assert.equal(r.events[0].managerIntroDurationWrittenByHost,false);
  assert.equal(r.calls.filter(x=>x[0]==='invoke').length,1);assert.equal(r.calls.find(x=>x[0]==='invoke')[1],'get_duration');});
for(const option of ['wrongType','badLayout','staticField','badMethod','badGetter','sameDirector'])check(()=>assert.throws(()=>run({[option]:true})));
check(()=>assert.throws(()=>run({values:{_introCutScene:null}}),/Unity-null/));
check(()=>assert.throws(()=>run({unityNull:'serialized intro UI director'}),/Unity-null/));
check(()=>assert.throws(()=>run({values:{_skipSpeed:3}}),/skip speed/));
check(()=>assert.throws(()=>run({values:{_modeBoard:null}}),/mode board/));
check(()=>assert.throws(()=>run({values:{_modeBoard:{length:2,isNull:()=>false}}}),/mode board/));
check(()=>assert.throws(()=>run({values:{_modeBoard:{length:1,isNull:()=>false,get:()=>null}}}),/Unity-null/));
for(const duration of [0,1,NaN,Infinity])check(()=>assert.throws(()=>run({duration}),/duration differs/));
check(()=>{const nativeError=Object.assign(new Error('native-duration-failure'),{nativeFrames:[{rva:'0x855e980'}]});
  try{run({nativeError});assert.fail('Expected native failure');}catch(error){assert.strictEqual(error,nativeError);assert.equal(error.nativeFrames[0].rva,'0x855e980');}});
console.log(checks+' actual-geometry original-intro boundary contracts PASS; no native launch');
