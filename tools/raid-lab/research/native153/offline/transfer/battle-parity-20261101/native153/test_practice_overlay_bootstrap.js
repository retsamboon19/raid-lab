'use strict';
const fs=require('fs'),vm=require('vm'),assert=require('assert');
const source=fs.readFileSync(__dirname+'/practice_overlay_bootstrap.js','utf8');
const original=JSON.parse(fs.readFileSync(__dirname+'/practice-loading-overlay-binding.json','utf8'));
function run(options={}) {
 const binding=structuredClone(original),events=[],calls=[],pins=[],callbacks=[],timers=[],classLookups=[],eventClassReads=[];let id=0,now=0;
 let scheduleAttempts=0,inMain=false,queued=null,cleared=false;
 const enterMain=fn=>{inMain=true;try{return fn();}finally{inMain=false;}};
 const ptr=value=>({value,id:++id,equals(other){return !!other&&other.id===this.id;},readU8(){return this.value;},readS32(){return this.value;},writeS32(x){this.value=x;},readByteArray(size){return new Uint8Array(size).buffer;}});
 const eventClass={handle:ptr(),type:{name:options.badEventName?'Wrong.EventId':'NK.StaticData.Categoricals.EventId'},
  isValueType:!options.eventReferenceType,valueTypeSize:options.badEventSize?8:4};
 const arriveEventClass=options.differentEventClass?{...eventClass,handle:ptr()}:eventClass;
 const obj=(type,values={})=>{const o={handle:ptr(),class:{type:{name:type}},isNull:()=>false,field(name){
   const spec=[...binding.serviceFields,...binding.transitionFields,...binding.tipFields,...binding.lazyFields].find(x=>x.name===name);
   return {offset:(spec?.offset||0)+(options.badField===name?4:0),type:{name:spec?.type},isStatic:false,get value(){return values[name];},set value(_){throw Error('NATIVE WRITE');}};},method(name,argc){return methodFor(type,name,argc);}};return o;};
 const boxed=value=>({handle:ptr(),isNull:()=>false,unbox:()=>({handle:ptr(value)})});
 function methodFor(type,name,argc){let key;
  if(type==='NK.StaticData.DataManager')key=name==='get_Instance'?'manager':'table';
  else if(type==='NK.StaticData.DataTables.TransitionTable')key='find';
  else if(type===binding.rowType)key='rowId';
  else if(type===binding.transitionMethodType)key='fromStatic';
  else if(type==='NK.OverlayTransition')key=name==='get_Instance'?'singleton':name==='ShowTransitionAsync'?'show':name==='GetActiveViewToHide'?'active':null;
  const s=binding.methods[key];return {name,key,type,relativeVirtualAddress:s?s.rva+(options.badMethod===key?1:0):0,
   isStatic:s?s.isStatic:false,returnType:{name:s?.returns},parameters:s?s.parameters.map((name,index)=>({type:{
    name:options.badEventSignature&&key==='find'&&index===3?'System.Int32':name,
    get class(){eventClassReads.push(index);return index===2?eventClass:arriveEventClass;}}})):Array.from({length:argc},()=>({}))};
 }
 const str=value=>{const o=obj('System.String');o.mockString=true;o.handle.value=value;return o;};
 const serviceGo=obj('UnityEngine.GameObject'),viewGo=obj('UnityEngine.GameObject');
 const canvas=obj('UnityEngine.Canvas');
 const lazy=obj('NK.UI.Component.OverlayTransitionLazyController',{_isActive:!options.inactive,_view:obj('AsyncLazy')});
 const serviceValues={_parent:obj('UnityEngine.RectTransform'),_prefab:obj('NK.UI.Component.OverlayTransitionLazyController'),
  _transitionFade:obj('NK.OverlayTransitionView'),_allCameraRenderSuppressorBoard:obj('UnityEngine.GameObject'),_canvas:canvas,_transitionViews:obj('Dictionary')};
 if(options.missingRef)serviceValues[options.missingRef]=null;
 if(options.wrongRef)serviceValues[options.wrongRef]=obj('WrongType');
 const service=obj('NK.OverlayTransition',serviceValues),manager=obj('NK.StaticData.DataManager'),table=obj('NK.StaticData.DataTables.TransitionTable'),row=obj(binding.rowType);
 const tip=obj(binding.tipType,{'<Group>k__BackingField':options.tipGroup??4,'<RotationType>k__BackingField':{field:()=>({value:options.rotation??0})}});
 const transition=obj(binding.transitionMethodType,{'<TransitionName>k__BackingField':str(options.name??binding.transitionName),
  '<IsGauge>k__BackingField':options.gauge??true,'<LoadingTip>k__BackingField':options.noTip?null:tip});
 transition.unbox=()=>transition;
 const task={type:{name:options.wrongTask?'Other': 'Cysharp.Threading.Tasks.UniTask<System.Boolean>'},method:(name,argc)=>methodFor('Task',name,argc)};
 const tuple=obj('Tuple');tuple.unbox=()=>({field:()=>({value:task})});
 const awaiter=obj('Awaiter');awaiter.unbox=()=>awaiter;
 const nullPointer={null:true};
 const context={globalThis:null,Error,Uint8Array,Array,Number,Process:{pointerSize:8,getModuleByName:()=>({base:{add(rva){return {readByteArray(size){const f=binding.codeFragments.find(f=>f.rva===rva);const b=Buffer.from(f.bytes,'hex');if(options.badBytes)b[0]^=1;return b.buffer.slice(b.byteOffset,b.byteOffset+b.byteLength);}};}}})},
  Memory:{alloc:()=>ptr()},NULL:nullPointer,PRACTICE_LOADING_OVERLAY_BINDING:binding,Date:{now:()=>now},
  probeQuitRequested:false,
  setInterval:fn=>{timers.push(fn);return timers.length;},clearInterval:()=>{cleared=true;},onMain:fn=>{
   scheduleAttempts++;
   if(scheduleAttempts<=(options.scheduleThrowCount||0))throw options.scheduleError;
   if(options.rejectSchedule||scheduleAttempts<=(options.busyCount||0))return false;
   if(options.deferMain){queued=fn;return true;}enterMain(fn);return true;},
  Il2Cpp:{domain:{assembly:()=>({image:{class:()=>({method:()=>methodFor('UnityEngine.Object','op_Implicit',1)})}})},string:str,String:function(h){this.content=h.value;},Object:function(h){this.handle=h;this.isNull=()=>false;}},
  invokeChecked(method,self,args){calls.push({method,self,args});if(options.nativeError&&method.key===options.errorAt)throw options.nativeError;
   switch(method.key){case'manager':return manager;case'table':return table;case'find':assert.equal(args[0].value,'Lobby');assert.equal(args[1].value,'Battle');assert.equal(args[2].value,0);assert.equal(args[3].value,0);return row;
    case'rowId':return boxed(options.rowId??19);case'fromStatic':assert.strictEqual(args[0],row.handle);return transition;case'singleton':return service;
    case'show':assert.strictEqual(args[0],transition.handle);assert.strictEqual(args[1],nullPointer);return tuple;case'active':return options.noView?null:lazy;}
   if(method.name==='op_Implicit')return boxed(options.unityNull?0:1);
   if(method.name==='get_gameObject')return self===service?serviceGo:self===canvas?(options.otherCanvas?viewGo:serviceGo):viewGo;
   if(method.name==='get_name')return str(options.viewName??binding.transitionName);
   if(method.name==='GetAwaiter')return awaiter;
   if(method.name==='get_IsCompleted')return boxed(options.pending?0:1);
   if(method.name==='GetResult')return boxed(options.showFalse?0:1);
   throw Error('Unexpected native invocation '+method.name);
  }};
 context.globalThis=context;
 const runtime={class:name=>({method:(n,a)=>methodFor(name,n,a)})};
 const staticImage={class:name=>{classLookups.push(name);
  if(name==='NK.StaticData.Categoricals.EventId'){
   if(options.eventWrongAssemblyDecoy)return {handle:ptr(),type:{name},isValueType:true,valueTypeSize:4};
   throw Error('NK.Runtime.StaticData does not declare EventId');
  }
  return {isValueType:true,valueTypeSize:options.badMethodSize?8:24,method:(n,a)=>methodFor(name,n,a)};}};
 vm.runInNewContext(source,context);
 const state=context.startOriginalPracticeOverlay(runtime,staticImage,x=>{if(x.mockString)throw Error('Il2Cpp.String lacks Object.ref');pins.push(x);return x;},x=>{if(options.throwEmit||options.throwFailureEmit&&x.status==='original_practice_overlay_failed')throw Error('sink');events.push(x);},(error,state)=>callbacks.push({error,state,inMain}));
 const poll=()=>{if(!cleared)timers[0]?.();};return {state,poll,calls,pins,callbacks,events,classLookups,eventClassReads,context,
  scheduleAttempts:()=>scheduleAttempts,cleared:()=>cleared,release:()=>{const fn=queued;queued=null;if(fn)enterMain(fn);},advance:x=>{now=x;}};
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
check(()=>{const r=run();assert.equal(r.state.status,'showing');assert.equal(r.callbacks.length,0);r.poll();assert.equal(r.state.readyShow,true);assert.equal(r.callbacks.length,1);assert.equal(r.callbacks[0].error,null);assert.equal(r.state.check(),true);r.poll();assert.equal(r.callbacks.length,1);
 assert.equal(r.calls.filter(c=>c.method.name==='GetResult').length,1);assert.ok(r.pins.includes(r.state.tuple));assert.ok(r.pins.includes(r.state.awaiter));
 assert.equal(r.calls.filter(c=>/^Hide|^set_|^OnInit/.test(c.method.name)).length,0);});
check(()=>{const r=run();r.poll();assert.equal(r.state.readyShow,true);
 assert.deepStrictEqual(r.eventClassReads,[2,3]);assert.ok(!r.classLookups.includes('NK.StaticData.Categoricals.EventId'));});
check(()=>{const r=run({eventWrongAssemblyDecoy:true});r.poll();assert.equal(r.state.readyShow,true);
 assert.deepStrictEqual(r.eventClassReads,[2,3]);assert.ok(!r.classLookups.includes('NK.StaticData.Categoricals.EventId'));});
for(const options of [{differentEventClass:true},{eventReferenceType:true},{badEventName:true},{badEventSignature:true}])
 check(()=>{const r=run(options);assert.equal(r.state.status,'failed');assert.equal(r.calls.filter(c=>c.method.key==='find').length,0);});
for(const options of [{rowId:18},{name:'Other'},{gauge:false},{noTip:true},{tipGroup:0},{rotation:1},{badEventSize:true},{badMethodSize:true},{badBytes:true},
 ...['manager','table','find','rowId','fromStatic','singleton','show'].map(badMethod=>({badMethod})),
 ...['_parent','_prefab','_transitionFade','_allCameraRenderSuppressorBoard','_canvas','_transitionViews'].map(missingRef=>({missingRef})),
 ...['_parent','_prefab','_transitionFade','_allCameraRenderSuppressorBoard','_canvas'].map(wrongRef=>({wrongRef})),
 ...['_parent','_canvas','<TransitionName>k__BackingField','<Group>k__BackingField'].map(badField=>({badField})),
 {otherCanvas:true},{unityNull:true},{wrongTask:true}])check(()=>{const r=run(options);assert.equal(r.state.status,'failed');assert.equal(r.callbacks.length,1);assert.throws(()=>r.state.check());});
for(const options of [{showFalse:true},{noView:true},{inactive:true},{viewName:'Other'},{badMethod:'active'},{badField:'_isActive'}])check(()=>{const r=run(options);r.poll();assert.equal(r.state.status,'failed');assert.equal(r.callbacks.length,1);assert.throws(()=>r.state.check());});
check(()=>{const r=run({pending:true});r.poll();assert.equal(r.state.status,'showing');assert.equal(r.callbacks.length,0);assert.equal(r.calls.filter(c=>c.method.name==='GetResult').length,0);r.advance(30001);r.poll();assert.equal(r.state.status,'failed');});
check(()=>{const nativeError=Object.assign(new Error('native'),{nativeFrames:[{rva:'0x73aaf60'}]});const r=run({nativeError,errorAt:'show'});assert.strictEqual(r.state.fault,nativeError);assert.strictEqual(r.callbacks[0].error,nativeError);assert.throws(()=>r.state.check(),e=>e===nativeError);});
check(()=>{const nativeError=Object.assign(new Error('native'),{nativeFrames:[1]});const r=run({nativeError,errorAt:'show',throwEmit:true});assert.strictEqual(r.callbacks[0].error,nativeError);});
check(()=>{const r=run({busyCount:5}),before=r.calls.length;
 for(let i=0;i<5;i++)r.poll();assert.equal(r.state.status,'showing');assert.equal(r.callbacks.length,0);assert.equal(r.calls.length,before);
 r.poll();assert.equal(r.state.readyShow,true);assert.equal(r.callbacks.length,1);assert.equal(r.callbacks[0].inMain,true);
 assert.equal(r.scheduleAttempts(),6);assert.equal(r.calls.filter(c=>c.method.name==='GetResult').length,1);});
check(()=>{const r=run({deferMain:true});r.poll();const before=r.calls.length;for(let i=0;i<10;i++)r.poll();
 assert.equal(r.scheduleAttempts(),1);assert.equal(r.calls.length,before);assert.equal(r.callbacks.length,0);
 r.release();assert.equal(r.state.readyShow,true);assert.equal(r.callbacks.length,1);assert.equal(r.callbacks[0].inMain,true);});
check(()=>{const r=run({rejectSchedule:true}),before=r.calls.length;for(let i=0;i<70;i++){r.advance(i*1000);r.poll();}
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
check(()=>{const nativeError=Object.assign(new Error('original resumed native failure'),{nativeFrames:[9]});const r=run({busyCount:2,nativeError,errorAt:'active'});r.poll();r.poll();assert.equal(r.callbacks.length,0);r.poll();assert.strictEqual(r.callbacks[0].error,nativeError);assert.equal(r.callbacks[0].inMain,true);});
console.log(checks+' actual original-overlay loader contracts PASS; synthetic managed graph only, no native launch');


