// Observe the new battle's own original state; no captured-team equality gate.
function createCustomNativeRngObserver153(runtime,pin,emit) {
  const rng=runtime.class('NK.Spot.Common.SpotRandom');
  const random=Il2Cpp.corlib.class('System.Random');
  function field(klass,name,type,offset,isStatic=false) {
    const f=klass.field(name);
    if(f.type.name!==type||f.offset!==offset||f.isStatic!==isStatic)
      throw Error('Original RNG field layout changed: '+name);
    return f;
  }
  if(rng.instanceSize!==40||random.instanceSize!==32)throw Error('Original RNG layout changed');
  const shared=field(rng,'_shared','NK.Spot.Common.SpotRandom',0,true);
  field(rng,'_currSeed','System.Int32',16);
  field(rng,'<Random>k__BackingField','System.Random',24);
  field(rng,'<DrawCount>k__BackingField','System.Int64',32);
  field(random,'_inext','System.Int32',16);
  field(random,'_inextp','System.Int32',20);
  field(random,'_seedArray','System.Int32[]',24);
  const game=Process.getModuleByName('GameAssembly.dll');
  const get=new NativeFunction(game.getExportByName('il2cpp_field_static_get_value'),'void',['pointer','pointer']);
  const buffer=Memory.alloc(Process.pointerSize),roots=[],observations=[];
  const prime=Il2Cpp.array(Il2Cpp.corlib.class('System.Int32'),1);pin(prime.object);
  if(prime.length!==1||prime.elementSize!==4||!prime.elements.handle)throw Error('Original typed array unavailable');
  roots.push(prime.object);
  const seen={enter:false,leave:false};let fault=null;
  function object(pointer,type) {
    if(pointer.isNull())throw Error('Missing original RNG object');
    const value=new Il2Cpp.Object(pointer);
    if(value.class.type.name!==type)throw Error('Original RNG object type changed');
    roots.push(value);return value;
  }
  function observe(phase) {
    try {
      if(!Object.prototype.hasOwnProperty.call(seen,phase)||seen[phase]||phase==='leave'&&!seen.enter)
        throw Error('Duplicate or unordered native RNG boundary');
      get(shared.handle,buffer);
      const source=object(buffer.readPointer(),'NK.Spot.Common.SpotRandom');
      const randomObject=object(source.handle.add(24).readPointer(),'System.Random');
      const arrayPointer=randomObject.handle.add(24).readPointer();object(arrayPointer,'System.Int32[]');
      const array=new Il2Cpp.Array(arrayPointer);
      if(array.length!==56||array.elementSize!==4)throw Error('Original RNG array layout changed');
      const actual={seed:source.handle.add(16).readS32(),drawCount:source.handle.add(32).readS64().toString(),
        inext:randomObject.handle.add(16).readS32(),inextp:randomObject.handle.add(20).readS32(),
        seedArray:Array.from({length:56},(_,i)=>array.elements.handle.add(4*i).readS32())};
      if(actual.inext<0||actual.inext>=56||actual.inextp<0||actual.inextp>=56||!/^\d+$/.test(actual.drawCount))
        throw Error('Invalid original RNG state');
      seen[phase]=true;
      const row={status:'original_custom_shared_rng_observed',boundaryPhase:phase,actual,
        requestSha256:globalThis.NATIVE_BATTLE_REQUEST_SHA256,
        rngStateWritten:false,rngMethodsInvoked:false,referenceCompared:false};
      observations.push(row);emit(row);return row;
    }catch(error){fault=fault||error;emit({status:'original_custom_shared_rng_read_failed',boundaryPhase:phase,error:String(error)});}
  }
  function check(){if(fault)throw fault;}
  function assertComplete(){check();if(!seen.enter||!seen.leave)throw Error('Original OnStart boundaries not observed');}
  return {observe,check,assertComplete,roots,rawBuffers:[buffer],
    snapshot:()=>({seen:{...seen},observations:observations.slice(),fault:fault?String(fault):null,
      rngStateWritten:false,rngMethodsInvoked:false,referenceCompared:false})};
}
