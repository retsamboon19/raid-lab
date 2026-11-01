'use strict';
const fs=require('fs'),vm=require('vm'),assert=require('assert');
const source=fs.readFileSync(__dirname+'/practice_localization.js','utf8');
const binding=JSON.parse(fs.readFileSync(__dirname+'/practice-localization-binding.json','utf8'));
const fixture=JSON.parse(fs.readFileSync(__dirname+'/../../../tools/raid-lab/private/native-player153-20261101/local-locale153-fixture1.json','utf8'));
function run(options={}){
 const b=structuredClone(binding),f=structuredClone(fixture),events=[],calls=[],pins=[],callbacks=[],timers=[],assemblies=[];
 let now=0,catalogReads=0,scheduleAttempts=0,inMain=false,queued=null,cleared=false;
 const enterMain=fn=>{inMain=true;try{return fn();}finally{inMain=false;}};
 if(options.fixtureMutate)options.fixtureMutate(f);
 function method(name){let key=Object.keys(b.methods).find(k=>b.methods[k].name===name);
  const spec=b.methods[key];return {key,name,isStatic:options.badStatic===key?!spec.isStatic:spec?.isStatic,
   relativeVirtualAddress:spec?spec.rva+(options.badRva===key?1:0):0,
   returnType:{name:options.badReturn===key?'Other':spec?.returns},
   parameters:options.badArgs===key?[{type:{name:'System.Int32'}}]:[]};}
 const handle=value=>({readU8:()=>value});
 const box=value=>({handle:handle(value),isNull:()=>false,unbox:()=>({handle:handle(value)})});
 const task=box();task.unbox=()=>({method:(n,a)=>({name:n}),handle:{}});
 const awaiter=box();awaiter.unbox=()=>({method:(n,a)=>({name:n}),handle:{}});
 const asyncRecord={error:'Original native async failure',nativeFrames:[{rva:'0x82f5c5a'}]};
 const context={globalThis:null,Error,Array,Uint8Array,Number,Date:{now:()=>now},
  PRACTICE_LOCALIZATION_BINDING:b,PRACTICE_LOCALIZATION_BINDING_SHA256:options.badBindingSha?'wrong':'7621643f35dce4a77c4b8b1b99f2f64cbacee29bcecf4ec697f27a6b03efe2d8',
  PRACTICE_LOCALIZATION_FIXTURE:f,PRACTICE_LOCALIZATION_FIXTURE_SHA256:options.badFixtureSha?'wrong':b.fixtureSha256,
  firstAsyncFault:options.initialFaultValue|| (options.initialFault?asyncRecord:null),probeQuitRequested:false,
  Process:{pointerSize:8,getModuleByName:()=>({base:{add(rva){return {readByteArray(size){const row=b.codeFragments.find(r=>r.rva===rva);const raw=Buffer.from(row.bytes,'hex');if(options.badBytes)raw[0]^=1;return raw.buffer.slice(raw.byteOffset,raw.byteOffset+raw.byteLength);}};}}})},
  Il2Cpp:{domain:{assembly(name){assemblies.push(name);assert.equal(name,'NK.LocalizedStrings','exact fresh metadata assembly');
   return {image:{class(name){assert.equal(name,b.methods.catalog.class);return {method:(name,count)=>method(name)};}}};}}},
  setInterval:fn=>{timers.push(fn);return timers.length;},clearInterval:()=>{cleared=true;},onMain:fn=>{
   scheduleAttempts++;if(scheduleAttempts<=(options.scheduleThrowCount||0))throw options.scheduleError;
   if(options.scheduleReject||scheduleAttempts<=(options.busyCount||0))return false;
   if(options.deferMain){queued=fn;return true;}enterMain(fn);return true;},
  invokeChecked(m,self,args){calls.push(m.name);const phase=m.key==='catalog'?(++catalogReads===1?'catalogBefore':'catalogAfter'):m.key||m.name;
   if(options.throwAt===phase)throw options.nativeError;
   if(options.faultAt===phase)context.firstAsyncFault=asyncRecord;
   if(m.key==='catalog')return box(catalogReads===1?0:(options.readinessFalse?0:options.badBool?2:1));
   if(m.key==='tables')return options.nullTask?null:task;
   if(m.key==='readiness')return null;
   if(m.name==='GetAwaiter')return awaiter;
   if(m.name==='get_IsCompleted')return box(options.pending?0:options.malformedCompleted?2:1);
   if(m.name==='GetResult')return null;
   throw Error('Unexpected represented method '+m.name);
  }};
 context.globalThis=context;
 const runtime={class(name){assert.equal(name,b.methods.tables.class,'no NKLocalizationSystem in NK.Runtime decoy');return {method:(name,count)=>method(name)};}};
 vm.runInNewContext(source,context);
 const state=context.startOriginalPracticeLocalization(runtime,x=>{pins.push(x);return x;},row=>{events.push(row);if(options.throwEmit||options.throwFailureEmit&&row.status==='original_practice_localization_failed')throw Error('sink');if(options.faultAt==='readyEmit'&&row.status==='original_practice_localization_ready')context.firstAsyncFault=asyncRecord;},(error,state)=>callbacks.push({error,state,inMain}));
 return {state,poll:()=>{if(!cleared)timers[0]?.();},events,calls,pins,callbacks,assemblies,context,asyncRecord,
  scheduleAttempts:()=>scheduleAttempts,cleared:()=>cleared,release:()=>{const fn=queued;queued=null;if(fn)enterMain(fn);},advance:value=>{now=value;}};
}
function existingBoundedHostTimeout(){
 const {spawnSync}=require('child_process'),path=require('path');
 // Execute the existing worker's actual bounded-wait AST with a synthetic
 // child only. No Popen, Unity, filesystem mutation or native process launch.
 const script=`import ast,json,pathlib,subprocess,sys
root=ast.parse(pathlib.Path(sys.argv[1]).read_text())
worker=next(n for n in root.body if isinstance(n,ast.FunctionDef) and n.name=='worker')
owned=next(n for n in worker.body if isinstance(n,ast.With))
wait=next(n for n in owned.body if isinstance(n,ast.Try))
class Child:
 pid=123
 def __init__(self):self.waits=[];self.terminated=0
 def wait(self,timeout):
  self.waits.append(timeout)
  if len(self.waits)==1:raise subprocess.TimeoutExpired('TEST-ONLY-FAKE-PLAYER',timeout)
  return 0
 def terminate(self):self.terminated+=1
 def kill(self):raise AssertionError('unexpected synthetic kill')
child=Child()
f=ast.FunctionDef(name='bounded_wait',args=ast.arguments(posonlyargs=[],args=[],kwonlyargs=[],kw_defaults=[],defaults=[]),body=[wait],decorator_list=[])
code=ast.fix_missing_locations(ast.Module(body=[f],type_ignores=[]))
scope={'child':child,'plan':{'max_seconds':60},'subprocess':subprocess,'json':json}
exec(compile(code,'existing-native-player-host-bounded-wait','exec'),scope)
assert scope['bounded_wait']()==124
assert child.waits==[60,3] and child.terminated==1
print('existing bounded host timeout branch PASS; synthetic child only')`;
 const result=spawnSync('python',['-c',script,path.resolve(__dirname,'../../../tools/raid-lab/native_player_host.py')],{encoding:'utf8'});
 assert.equal(result.status,0,result.stderr);assert.match(result.stdout,/existing bounded host timeout branch PASS/);
}
let checks=0;const check=fn=>{fn();checks++;};
check(()=>{const r=run();assert.equal(r.state.status,'registering');assert.equal(r.callbacks.length,0);r.poll();assert.equal(r.state.ready,true);assert.equal(r.state.check(),true);assert.equal(r.callbacks.length,1);assert.equal(r.callbacks[0].error,null);
 assert.deepStrictEqual(r.calls,['get_CatalogUpdated','InitializeLocaleTablesAsync','GetAwaiter','get_IsCompleted','GetResult','InitializeNKLocalizationSystem','get_CatalogUpdated']);
 assert.ok(r.pins.includes(r.state.task));assert.ok(r.pins.includes(r.state.awaiter));r.poll();assert.equal(r.callbacks.length,1);assert.equal(r.calls.filter(n=>n==='GetResult').length,1);
 assert.equal(r.events.at(-1).hostDirectReadinessFieldWrite,false);assert.equal(r.events.at(-1).originalReadinessInitializerCalled,true);
 assert.equal(r.events.at(-1).languageSetterCalledByHost,false);assert.deepStrictEqual(r.assemblies,['NK.LocalizedStrings']);});
for(const options of [{badBindingSha:true},{badFixtureSha:true},{badBytes:true},{nullTask:true},
 ...['tables','readiness','catalog'].flatMap(key=>[{badStatic:key},{badRva:key},{badReturn:key},{badArgs:key}]),
 ...[f=>{f.status='unrun';},f=>{f.sourceProofSha256='wrong';},f=>{f.installedFilesWritten=true;},f=>{f.catalogsRewritten=true;},f=>{f.signatureBytesChanged=true;},f=>{f.copies.pop();},f=>{f.copies[0].sha256='wrong';},f=>{f.copies[0].bytes++;},f=>{f.copies[4]=f.copies[0];}].map(fixtureMutate=>({fixtureMutate}))])
 check(()=>{const r=run(options);assert.equal(r.state.status,'failed');assert.equal(r.callbacks.length,1);assert.throws(()=>r.state.check());});
check(()=>{const r=run({pending:true});r.poll();assert.equal(r.state.status,'registering');assert.ok(!r.calls.includes('GetResult'));assert.ok(!r.calls.includes('InitializeNKLocalizationSystem'));r.advance(30001);r.poll();assert.equal(r.state.status,'failed');});
for(const options of [{readinessFalse:true},{badBool:true},{malformedCompleted:true}])check(()=>{const r=run(options);r.poll();assert.equal(r.state.status,'failed');assert.equal(r.callbacks.length,1);assert.equal(r.state.ready,false);});
check(()=>{const r=run({initialFault:true});assert.equal(r.state.status,'failed');assert.equal(r.calls.length,0);assert.strictEqual(r.context.firstAsyncFault,r.asyncRecord);assert.strictEqual(r.callbacks[0].error.nativeFrames,r.asyncRecord.nativeFrames);});
check(()=>{const original=Object.assign(new Error('previous native failure'),{nativeFrames:[7]});const r=run({initialFaultValue:original});
 assert.strictEqual(r.state.fault,original);assert.strictEqual(r.callbacks[0].error,original);assert.strictEqual(r.context.firstAsyncFault,original);});
for(const faultAt of ['tables','GetAwaiter','get_IsCompleted','GetResult','readiness','catalogAfter','readyEmit'])check(()=>{const r=run({faultAt});r.poll();assert.equal(r.state.status,'failed');assert.equal(r.state.ready,false);assert.equal(r.callbacks.length,1);assert.ok(r.callbacks[0].error);assert.strictEqual(r.context.firstAsyncFault,r.asyncRecord);assert.strictEqual(r.callbacks[0].error.nativeFrames,r.asyncRecord.nativeFrames);});
check(()=>{const r=run();r.poll();r.context.firstAsyncFault=r.asyncRecord;assert.throws(()=>r.state.check(),e=>e.nativeFrames===r.asyncRecord.nativeFrames);assert.equal(r.callbacks.length,1);});
for(const throwAt of ['tables','GetResult','readiness','catalogAfter'])check(()=>{const nativeError=Object.assign(new Error('native'),{nativeFrames:[1]});const r=run({throwAt,nativeError});r.poll();assert.strictEqual(r.state.fault,nativeError);assert.strictEqual(r.callbacks[0].error,nativeError);});
check(()=>{const nativeError=Object.assign(new Error('native'),{nativeFrames:[1]});const r=run({throwAt:'tables',nativeError,throwEmit:true});assert.strictEqual(r.callbacks[0].error,nativeError);});
check(()=>{const r=run();r.poll();const row=r.events.at(-1);assert.equal(row.selectedLocale,null);assert.equal(row.selectedLocaleVerified,false);
 assert.equal(row.fontClosureLocale,'en');assert.equal(row.originalLocaleSelectionPreserved,true);});
check(()=>{const r=run({busyCount:5}),before=r.calls.length;
 for(let i=0;i<5;i++)r.poll();assert.equal(r.state.status,'registering');assert.equal(r.callbacks.length,0);assert.equal(r.calls.length,before);
 r.poll();assert.equal(r.state.ready,true);assert.equal(r.callbacks.length,1);assert.equal(r.callbacks[0].inMain,true);
 assert.equal(r.scheduleAttempts(),6);assert.equal(r.calls.filter(c=>c==='GetResult').length,1);});
check(()=>{const r=run({deferMain:true});r.poll();const before=r.calls.length;for(let i=0;i<10;i++)r.poll();
 assert.equal(r.scheduleAttempts(),1);assert.equal(r.calls.length,before);assert.equal(r.callbacks.length,0);
 r.release();assert.equal(r.state.ready,true);assert.equal(r.callbacks.length,1);assert.equal(r.callbacks[0].inMain,true);});
check(()=>{const r=run({scheduleReject:true}),before=r.calls.length;for(let i=0;i<70;i++){r.advance(i*1000);r.poll();}
 assert.equal(r.callbacks.length,0);assert.equal(r.calls.length,before);assert.equal(r.state.fault,null);
 existingBoundedHostTimeout();r.context.probeQuitRequested=true;r.poll();assert.equal(r.cleared(),true);assert.equal(r.callbacks.length,0);});
check(()=>{const r=run({busyCount:2});r.poll();r.poll();r.advance(30001);r.poll();
 assert.equal(r.state.status,'failed');assert.equal(r.callbacks.length,1);assert.equal(r.callbacks[0].inMain,true);assert.match(String(r.callbacks[0].error),/bounded 30000ms/);});
check(()=>{const scheduleError=Object.assign(new Error('original scheduling failure'),{nativeFrames:[{rva:'0x7f17e50'}]});
 const r=run({scheduleThrowCount:2,scheduleError,throwFailureEmit:true});r.poll();r.poll();assert.equal(r.callbacks.length,0);
 assert.strictEqual(r.state.fault,scheduleError);assert.throws(()=>r.state.check(),e=>e===scheduleError);
 r.poll();assert.equal(r.callbacks.length,1);assert.strictEqual(r.callbacks[0].error,scheduleError);assert.equal(r.callbacks[0].inMain,true);});
check(()=>{const scheduleError=Object.assign(new Error('original scheduling failure'),{nativeFrames:[1]});
 const r=run({scheduleThrowCount:1,scheduleError});r.poll();const before=r.calls.length;r.context.probeQuitRequested=true;r.poll();
 assert.equal(r.cleared(),true);assert.equal(r.scheduleAttempts(),1);assert.equal(r.callbacks.length,0);assert.equal(r.calls.length,before);assert.strictEqual(r.state.fault,scheduleError);});
check(()=>{const r=run({deferMain:true});r.poll();const before=r.calls.length;r.context.probeQuitRequested=true;r.release();
 assert.equal(r.cleared(),true);assert.equal(r.callbacks.length,0);assert.equal(r.calls.length,before);assert.equal(r.scheduleAttempts(),1);});
check(()=>{const r=run({busyCount:2});r.poll();r.context.firstAsyncFault=r.asyncRecord;r.poll();assert.equal(r.callbacks.length,0);r.poll();assert.equal(r.callbacks.length,1);assert.equal(r.callbacks[0].inMain,true);assert.strictEqual(r.callbacks[0].error.nativeFrames,r.asyncRecord.nativeFrames);assert.strictEqual(r.context.firstAsyncFault,r.asyncRecord);});
console.log(checks+' actual original-localization module contracts PASS; synthetic graph only, no native execution');
