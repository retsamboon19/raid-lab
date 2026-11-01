// Synthetic boundary/memory controls only. No native player or RNG invocation.
const fs=require('fs'),vm=require('vm'),assert=require('assert'),path=require('path');
const here=__dirname,source=fs.readFileSync(path.join(here,'practice_rng_state_verifier.js'),'utf8');
const expected=JSON.parse(fs.readFileSync(path.join(here,'rng-state/expected1/run1-onstart-shared-rng.json'),'utf8'));
let assertions=0;
function check(fn){fn();assertions++;}
function fixture({emitThrows=false,readFails=false,fieldOffset=16}={}) {
  const memory=new Map(),types=new Map([[1000,'NK.Spot.Common.SpotRandom'],[2000,'System.Random'],[3000,'System.Int32[]'],[5000,'System.Int32[]']]);
  class Pointer {
    constructor(address){this.address=address;}
    isNull(){return !this.address;}
    add(offset){return new Pointer(this.address+offset);}
    readPointer(){return new Pointer(memory.get(this.address)||0);}
    readS32(){if(readFails&&this.address===4004)throw Error('Synthetic memory read error');return memory.get(this.address);}
    readS64(){return {toString:()=>String(memory.get(this.address))};}
  }
  const state=structuredClone(expected.phases.enter.state);
  function assign(value) {
    memory.set(1016,value.seed);memory.set(1024,2000);memory.set(1032,value.drawCount);
    memory.set(2016,value.inext);memory.set(2020,value.inextp);memory.set(2024,3000);
    value.seedArray.forEach((v,i)=>memory.set(4000+4*i,v));
  }
  assign(state);let primed=false,arrayReads=0,emitCalls=0;
  const schemas={
    'NK.Spot.Common.SpotRandom':{instanceSize:40,fields:{_shared:[0,'NK.Spot.Common.SpotRandom',true],_currSeed:[fieldOffset,'System.Int32'],
      '<Random>k__BackingField':[24,'System.Random'],'<DrawCount>k__BackingField':[32,'System.Int64']}},
    'System.Random':{instanceSize:32,fields:{_inext:[16,'System.Int32'],_inextp:[20,'System.Int32'],_seedArray:[24,'System.Int32[]']}}
  };
  function klass(name) {const schema=schemas[name];return {instanceSize:schema?.instanceSize,
    field(key){const [offset,type,isStatic=false]=schema.fields[key];return {offset,type:{name:type},isStatic,handle:'field:'+key};}};}
  class ObjectWrapper {constructor(pointer){this.handle=pointer;this.class={type:{name:types.get(pointer.address)}};}}
  class ArrayWrapper {
    constructor(pointer){this.handle=pointer;this.object=new ObjectWrapper(pointer);this.length=pointer.address===5000?1:56;this.elementSize=4;}
    get elements(){if(this.handle.address===5000)primed=true;else {assert(primed);arrayReads++;}return {handle:new Pointer(this.handle.address===5000?6000:4000)};}
  }
  const api={Process:{pointerSize:8,getModuleByName:()=>({getExportByName:name=>name})},
    Memory:{alloc:()=>new Pointer(7000)},
    NativeFunction:function(name,result,args){assert.equal(name,'il2cpp_field_static_get_value');assert.deepEqual(args,['pointer','pointer']);
      return (field,buffer)=>{assert.equal(field,'field:_shared');memory.set(buffer.address,1000);};},
    Il2Cpp:{corlib:{class:klass},Object:ObjectWrapper,Array:ArrayWrapper,array:()=>new ArrayWrapper(new Pointer(5000))}};
  const context=vm.createContext(api);vm.runInContext(source,context);
  const verifier=context.createOriginalPracticeRngStateVerifier({class:klass},expected,()=>{},()=>{emitCalls++;if(emitThrows)throw Error('Synthetic diagnostic sink failure');},{expectedSha256:'a'.repeat(64)});
  return {verifier,state,assign,memory,context,get arrayReads(){return arrayReads;},get emitCalls(){return emitCalls;}};
}
let f=fixture();check(()=>assert.equal(f.arrayReads,0));
check(()=>assert.equal(f.verifier.observe('enter').passed,true));
check(()=>assert.equal(f.verifier.observe('leave').passed,true));
check(()=>assert.doesNotThrow(()=>f.verifier.assertComplete()));
check(()=>assert.equal(f.arrayReads,2));
check(()=>assert.equal(f.verifier.snapshot().observations[0].actual.seedArray.length,56));
for(const [field,value]of [['seed',1],['drawCount','0'],['inext',0],['inextp',21]]){
  f=fixture();f.assign({...f.state,[field]:value});
  check(()=>assert.equal(f.verifier.observe('enter').passed,false));
  check(()=>assert.throws(()=>f.verifier.check(),/mismatch/));
}
for(const index of [0,1,55]){
  f=fixture();f.memory.set(4000+4*index,-123);
  check(()=>assert.deepEqual(Array.from(f.verifier.observe('enter').mismatchArrayIndices),[index]));
  check(()=>assert.throws(()=>f.verifier.check(),/mismatch/));
}
f=fixture({readFails:true});
check(()=>assert.equal(f.verifier.observe('enter').status,'original_practice_full_shared_rng_read_failed'));
check(()=>assert.throws(()=>f.verifier.check(),/Synthetic memory read error/));
f=fixture({emitThrows:true});
check(()=>assert.doesNotThrow(()=>f.verifier.observe('enter')));
check(()=>assert.doesNotThrow(()=>f.verifier.observe('leave')));
check(()=>assert.doesNotThrow(()=>f.verifier.assertComplete()));
f=fixture({emitThrows:true});f.assign({...f.state,drawCount:'0'});
check(()=>assert.doesNotThrow(()=>f.verifier.observe('enter')));
check(()=>assert.throws(()=>f.verifier.check(),/mismatch/));
f=fixture();check(()=>assert.throws(()=>f.verifier.assertComplete(),/Both original/));
check(()=>assert.equal(f.verifier.observe('leave').status,'original_practice_full_shared_rng_read_failed'));
check(()=>assert.throws(()=>fixture({fieldOffset:20}),/field layout/));
for(const run of [1,2,3]){
  const real=JSON.parse(fs.readFileSync(path.join(here,`rng-state/expected1/run${run}-onstart-shared-rng.json`),'utf8'));
  const compare=f.context.compareOriginalPracticeSharedRngState;
  check(()=>assert.equal(compare(real.phases.enter.state,real.phases.leave.state).passed,true));
  check(()=>assert.throws(()=>compare({...real.phases.enter.state,seedArray:real.phases.enter.state.seedArray.slice(1)},real.phases.enter.state),/Complete typed/));
}
console.log(JSON.stringify({status:'passed',assertions,scope:'Synthetic raw-memory/metadata and exact captured expected-state controls only; no native execution'}));
