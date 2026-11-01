'use strict';
const fs=require('fs'),vm=require('vm'),assert=require('assert');
const ctx={Error,Number};vm.runInNewContext(fs.readFileSync(__dirname+'/practice_geometry.js','utf8'),ctx);
const original=JSON.parse(fs.readFileSync(__dirname+'/practice-geometry-source.json','utf8'));
const popup=JSON.parse(fs.readFileSync(__dirname+'/practice-popup-control-source.json','utf8'));
let checks=0;const check=fn=>{fn();checks++;};
check(()=>{const r=ctx.resolveOriginalPracticePopupAsset(original,popup);assert.equal(r.key,popup.catalogKey);assert.equal(r.parent,popup.parentGuid);});
for(const mutate of [s=>{s.hierarchy=[];},s=>{s.hierarchy.push(structuredClone(s.hierarchy[4]));},
 s=>{s.hierarchy[4].children=[];},s=>{s.hierarchy[4].children.push(structuredClone(s.hierarchy[4].children[1]));},
 s=>{s.hierarchy[4].parent_guid='wrong';},s=>{s.hierarchy[4].children[1].asset_guid='wrong';},
 s=>{s.hierarchy[4].children[1].asset_rows[0].internal_id='wrong';},s=>{s.hierarchy[4].children[1].asset_rows[0].asset_type='Sprite';}])check(()=>{
 const source=structuredClone(original);mutate(source);assert.throws(()=>ctx.resolveOriginalPracticePopupAsset(source,popup));});
const specs={OnInit:[0x05b34f50,'System.Void',[]],OnRelease:[0x056963a0,'System.Void',[]],HideLoading:[0x05b34ec0,'Cysharp.Threading.Tasks.UniTask',[]],OnPlayStateChange:[0x05b35020,'System.Void',['NK.Spot.Common.SpotEvent']]};
function control(options={}) {return {class:{type:{name:options.wrongType?'Other':'NK.Spot.Presentation.UI.UIPopupControll'}},method(name,argc){const [rva,returns,args]=specs[name];assert.equal(argc,args.length);
 return {relativeVirtualAddress:rva+(options.badMethod===name?1:0),isStatic:options.staticMethod===name,returnType:{name:options.badReturn===name?'Other':returns},parameters:args.map(name=>({type:{name:options.badArg?'Other':name}}))};}};}
check(()=>{const value=control();assert.strictEqual(ctx.verifyOriginalPracticePopupRegistration(value,17),value);});
for(const options of [{wrongType:true},{badArg:true},...Object.keys(specs).flatMap(name=>[{badMethod:name},{badReturn:name},{staticMethod:name}])])check(()=>assert.throws(()=>ctx.verifyOriginalPracticePopupRegistration(control(options),17)));
check(()=>assert.throws(()=>ctx.verifyOriginalPracticePopupRegistration(control(),16)));
console.log(checks+' actual-geometry popup theme/lifecycle contracts PASS; no native launch');
