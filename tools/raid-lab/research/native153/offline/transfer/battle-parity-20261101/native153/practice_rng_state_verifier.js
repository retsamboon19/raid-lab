// Compare original shared RNG at the actual OnStart boundary. Never advance or write RNG state.
function compareOriginalPracticeSharedRngState(actual, expected) {
  const valid=state=>state&&Number.isInteger(state.seed)&&state.seed>=-2147483648&&state.seed<=2147483647&&
    typeof state.drawCount==='string'&&/^(0|[1-9][0-9]{0,18})$/.test(state.drawCount)&&
    Number.isInteger(state.inext)&&state.inext>=0&&state.inext<56&&
    Number.isInteger(state.inextp)&&state.inextp>=0&&state.inextp<56&&
    Array.isArray(state.seedArray)&&state.seedArray.length===56&&state.seedArray.every(
      value=>Number.isInteger(value)&&value>=-2147483648&&value<=2147483647);
  if(!valid(actual)||!valid(expected))throw Error('Complete typed shared RNG state required');
  const mismatchFields=['seed','drawCount','inext','inextp'].filter(name=>actual[name]!==expected[name]);
  const mismatchArrayIndices=[];
  for(let index=0;index<56;index++)if(actual.seedArray[index]!==expected.seedArray[index])mismatchArrayIndices.push(index);
  return {passed:mismatchFields.length===0&&mismatchArrayIndices.length===0,mismatchFields,mismatchArrayIndices,
    comparedArrayElements:56};
}

function createOriginalPracticeRngStateVerifier(runtime,expected,pin,emit,options) {
  'use strict';
  options=options||{};
  const client='d39896d3770888039c728a1908448c3db5efa7cdf874c90d56f46d8d566428d2';
  const metadata='58933dbe6080485c5270a127a2fe5e83070c035e7660d0a22227bf2acb41a741';
  if(!expected||expected.clientSha256!==client||expected.sourceMetadataSha256!==metadata||
     expected.captureSha256!=='634ab51506bd28c10f4c229a6b0c1baabe0aa757f1c3611ca5142dcff936d82d'||
     expected.boundary!=='NK.Spot.SpotManagement::OnStart'||expected.methodRva!==0x076064c0||
     expected.all56ElementsCaptured!==true||!Array.isArray(expected.rngPathCaptureErrors)||expected.rngPathCaptureErrors.length||
     expected.nativeRngStateWritesAllowed!==false||!/^[a-f0-9]{64}$/.test(options.expectedSha256||''))
    throw Error('Frozen complete original OnStart shared RNG expectation required');
  for(const phase of ['enter','leave']) {
    const entry=expected.phases?.[phase];
    if(!entry||entry.source?.phase!==phase||entry.source.boundary!=='NK.Spot.SpotManagement::OnStart@0x76064c0'||
       !Number.isInteger(entry.source.sequence)||!/^[a-f0-9]{64}$/.test(entry.source.sha256)||
       !Array.isArray(entry.source.rngPathCaptureErrors)||entry.source.rngPathCaptureErrors.length)
      throw Error('Exact clean source boundary anchor required');
    compareOriginalPracticeSharedRngState(entry.state,entry.state);
  }
  const game=Process.getModuleByName('GameAssembly.dll'),roots=[],rawBuffers=[],observations=[];
  const rngClass=runtime.class('NK.Spot.Common.SpotRandom'),randomClass=Il2Cpp.corlib.class('System.Random');
  if(rngClass.instanceSize!==40||randomClass.instanceSize!==32)throw Error('Exact current RNG instance sizes differ');
  function field(klass,name,type,offset,isStatic=false) {
    const result=klass.field(name);
    if(result.type.name!==type||result.offset!==offset||result.isStatic!==isStatic)
      throw Error('Exact current RNG field layout differs '+name);
    return result;
  }
  const sharedField=field(rngClass,'_shared','NK.Spot.Common.SpotRandom',0,true);
  field(rngClass,'_currSeed','System.Int32',16);
  field(rngClass,'<Random>k__BackingField','System.Random',24);
  field(rngClass,'<DrawCount>k__BackingField','System.Int64',32);
  field(randomClass,'_inext','System.Int32',16);
  field(randomClass,'_inextp','System.Int32',20);
  field(randomClass,'_seedArray','System.Int32[]',24);
  const staticGet=new NativeFunction(game.getExportByName('il2cpp_field_static_get_value'),'void',['pointer','pointer']);
  const rootBuffer=Memory.alloc(Process.pointerSize);rawBuffers.push(rootBuffer);
  // The bridge discovers Array.elements using original ToCharArray on first access.
  // Prime that accessor here, outside every OnStart/native observer callback.
  const prime=Il2Cpp.array(Il2Cpp.corlib.class('System.Int32'),1);
  pin(prime.object);roots.push(prime.object);
  if(prime.length!==1||prime.elementSize!==4||!prime.elements.handle)
    throw Error('Original typed Int32 array accessor unavailable');
  let fault=null;
  const seen={enter:false,leave:false};
  const safeEmit=row=>{try{if(typeof emit==='function')emit(row);}catch(_){}};
  function object(pointer,type) {
    if(pointer.isNull())throw Error('Original shared RNG reference is null: '+type);
    const value=new Il2Cpp.Object(pointer);
    if(value.class.type.name!==type)throw Error('Original shared RNG type differs: '+type);
    roots.push(value);return value;
  }
  function read() {
    staticGet(sharedField.handle,rootBuffer);
    const shared=object(rootBuffer.readPointer(),'NK.Spot.Common.SpotRandom');
    const random=object(shared.handle.add(24).readPointer(),'System.Random');
    const arrayPointer=random.handle.add(24).readPointer();
    object(arrayPointer,'System.Int32[]');
    const array=new Il2Cpp.Array(arrayPointer);
    if(array.length!==56||array.elementSize!==4)throw Error('Original shared RNG needs exactly56 Int32 elements');
    const elements=array.elements.handle,seedArray=[];
    for(let index=0;index<56;index++)seedArray.push(elements.add(index*4).readS32());
    return {seed:shared.handle.add(16).readS32(),drawCount:shared.handle.add(32).readS64().toString(),
      inext:random.handle.add(16).readS32(),inextp:random.handle.add(20).readS32(),seedArray};
  }
  function observe(phase) {
    try {
      if(!Object.prototype.hasOwnProperty.call(seen,phase)||seen[phase]||phase==='leave'&&!seen.enter)
        throw Error('Duplicate, unordered or unsupported original RNG boundary observation');
      seen[phase]=true;
      const actual=read(),comparison=compareOriginalPracticeSharedRngState(actual,expected.phases[phase].state);
      const row={status:'original_practice_full_shared_rng_observed',boundaryPhase:phase,
        expectedFileSha256:options.expectedSha256,referenceRunIndex:expected.referenceRunIndex,
        source:expected.phases[phase].source,actual,...comparison,
        rngStateWritten:false,rngMethodsInvoked:false,sameOriginalOnStartBoundary:true};
      observations.push(row);safeEmit(row);
      if(!comparison.passed)fault=fault||Error('Original shared RNG mismatch at OnStart '+phase);
      return row;
    } catch(error) {
      fault=fault||error;
      const row={status:'original_practice_full_shared_rng_read_failed',boundaryPhase:phase,error:String(error),
        expectedFileSha256:options.expectedSha256,rngStateWritten:false,rngMethodsInvoked:false};
      if(observations.length<4)observations.push(row);safeEmit(row);return row;
    }
  }
  function check(){if(fault)throw fault;}
  function assertComplete(){check();if(!seen.enter||!seen.leave)throw Error('Both original OnStart RNG boundaries must be observed');}
  return {observe,check,assertComplete,roots,rawBuffers,retainedListeners:[],
    snapshot:()=>({seen:{...seen},fault:fault?String(fault):null,observations:observations.slice(),
      expectedFileSha256:options.expectedSha256,referenceRunIndex:expected.referenceRunIndex,
      comparedArrayElementsPerBoundary:56,rngStateWritten:false,rngMethodsInvoked:false,
      typedArrayAccessorPrimedOutsideNativeHooks:true,helperInstallsHooks:false})};
}
