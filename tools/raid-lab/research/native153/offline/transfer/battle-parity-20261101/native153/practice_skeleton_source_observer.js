// Passive ordinary-entry/normal-return observation of original skeleton inputs.
function installPracticeSkeletonSourceObserver(emit) {
  if(typeof emit!=='function'||Process.pointerSize!==8)throw new Error('Skeleton source observer requires x64 evidence sink');
  const game=Process.getModuleByName('GameAssembly.dll'),listeners=[],active=new Map(),addresses=new Map();
  const runtime=Il2Cpp.domain.assembly('NK.Runtime').image;
  const spine=Il2Cpp.domain.assembly('NK.Spine.Runtime').image;
  const controller=runtime.class('NK.Spot.Presentation.SpineCharacterPrefabController');
  const addressClass=controller.nested('CombatSkeletonSetAddresses');
  const stateClass=controller.nested('<LoadSkeletonSetSourceAsync>d__13');
  const sourceClass=spine.class('NK.Spine.CombatSkeletonCharacterController').nested('CombatSkeletonSetSource');
  const getOffset=new NativeFunction(game.getExportByName('il2cpp_field_get_offset'),'uint64',['pointer']);
  const counters={addressCalls:0,loaderEntries:0,loaderReturns:0,sourceReturns:0,records:0,diagnosticErrors:0};
  const binding={addressRva:0x05570bf0,loaderRva:0x056ac580,constructorRva:0x0520fc40,
    sourceConstructorReturnRva:0x056ad2d3,stateValueSize:192,rawAddressOffset:32,rawStateOffset:0,
    limits:{addressObjects:32,records:96,diagnosticErrors:2,stringCodeUnits:1024}};
  const field=(klass,name,type,offset)=>{
    const f=klass.field(name);
    if(f.isStatic||f.type.name!==type||Number(getOffset(f.handle).toString())!==offset)
      throw new Error('Skeleton source field binding differs: '+name);
  };
  const names=['AimSkeleton','CoverSkeleton','AimIdlePhysics','AimShootingPhysics','CoverPhysics'];
  names.forEach((name,i)=>field(addressClass,'<'+name+'>k__BackingField','System.String',16+8*i));
  const sourceNames=['AimSkeletonDataAsset','CoverSkeletonDataAsset','AimIdlePhysicsSetting','AimShootingPhysicsSetting','CoverPhysicsSetting'];
  sourceNames.forEach((name,i)=>field(sourceClass,'<'+name+'>k__BackingField',i<2?'Spine.Unity.SkeletonDataAsset':'NK.Spine.SkeletonPhysics.SkeletonCharacterPhysicsSetting',16+8*i));
  field(stateClass,'<>1__state','System.Int32',16);
  field(stateClass,'addresses','NK.Spot.Presentation.SpineCharacterPrefabController.CombatSkeletonSetAddresses',48);
  if(!stateClass.isValueType||stateClass.valueTypeSize!==192||addressClass.isValueType||sourceClass.isValueType)
    throw new Error('Skeleton source class/value ABI differs');
  const addressMethod=controller.method('GetSkeletonSetAddresses',3),loaderMethod=stateClass.method('MoveNext',0),ctor=sourceClass.method('.ctor',5);
  const methods=[
    [addressMethod,binding.addressRva,'48895c240848896c2410488974241848'],
    [loaderMethod,binding.loaderRva,'48895c241048894c2408565741544156'],
    [ctor,binding.constructorRva,'48895c24084889742410574883ec2048']];
  const hex=(p,n)=>Array.from(new Uint8Array(p.readByteArray(n)),b=>b.toString(16).padStart(2,'0')).join('');
  if(!addressMethod.isStatic||loaderMethod.isStatic||ctor.isStatic||addressMethod.returnType.name!=='NK.Spot.Presentation.SpineCharacterPrefabController.CombatSkeletonSetAddresses'||loaderMethod.returnType.name!=='System.Void'||ctor.returnType.name!=='System.Void')
    throw new Error('Skeleton source method signature differs');
  const parameterTypes=['NK.StaticData.Categoricals.CharacterResourceId','NK.StaticData.Categoricals.CostumeIndex','System.Int32'];
  if(addressMethod.parameters.some((p,i)=>p.type.name!==parameterTypes[i]||p.type.class.valueTypeSize!==4)||addressMethod.returnType.class.isValueType||
    ctor.parameters.some((p,i)=>p.type.name!==(i<2?'Spine.Unity.SkeletonDataAsset':'NK.Spine.SkeletonPhysics.SkeletonCharacterPhysicsSetting')||p.type.class.isValueType))
    throw new Error('Skeleton source register/reference ABI differs');
  for(const [method,rva,prefix]of methods)if(!method.virtualAddress.equals(game.base.add(rva))||hex(method.virtualAddress,16)!==prefix)
    throw new Error('Skeleton source original entry differs or is already hooked: '+rva.toString(16));
  // Export thunks plus their original bodies establish String length/chars ABI.
  for(const [name,rva,prefix,body,bodyPrefix]of [
    ['il2cpp_string_length',0x007b73b0,'e96b1885ff',0x00008c20,'8b4110c3'],
    ['il2cpp_string_chars',0x007b7380,'e9cb090000',0x007b7d50,'488d4114c3']]){
    const p=game.getExportByName(name);
    if(!p.equals(game.base.add(rva))||hex(p,5)!==prefix||hex(game.base.add(body),bodyPrefix.length/2)!==bodyPrefix)
      throw new Error('Original IL2CPP string ABI differs: '+name);
  }
  const safeEmit=value=>{try{emit(value);}catch(error){counters.diagnosticErrors++;}};
  const fault=(where,error)=>{counters.diagnosticErrors++;if(counters.diagnosticErrors<=2)safeEmit({status:'skeleton_source_observer_error',where,error:String(error)});};
  const record=value=>{if(counters.records<96){counters.records++;safeEmit(value);}};
  const provenance=p=>{const m=Process.findModuleByAddress(p);return {address:p.toString(),module:m?.name||null,moduleOffset:m?p.sub(m.base).toString():null,gameAssemblyRva:m?.name.toLowerCase()==='gameassembly.dll'?p.sub(game.base).toString():null};};
  // Exact original string_length/string_chars exports prove +10h/+14h below.
  const text=p=>{if(p.isNull())return null;const n=p.add(16).readS32();if(n<0||n>1024)throw new Error('Skeleton address string outside bound');return p.add(20).readUtf16String(n);};
  const readAddresses=p=>{const values={addressObject:p.toString()};if(!p.isNull())names.forEach((name,i)=>values[name]=text(p.add(16+8*i).readPointer()));return values;};
  let serial=0;
  listeners.push(Interceptor.attach(addressMethod.virtualAddress,{
    onEnter(args){try{this.selected={resourceId:args[0].toInt32(),costumeIndex:args[1].toInt32(),transformationStep:args[2].toInt32(),caller:provenance(this.returnAddress)};counters.addressCalls++;}catch(error){fault('address_entry',error);}},
    onLeave(result){try{if(!this.selected)return;const row={...this.selected,...readAddresses(result)};if(addresses.size<32)addresses.set(result.toString(),row);record({status:'original_skeleton_addresses_returned',...row});}catch(error){fault('address_return',error);}}
  }));
  listeners.push(Interceptor.attach(loaderMethod.virtualAddress,{
    onEnter(args){try{const tid=Process.getCurrentThreadId(),p=args[0],a=p.add(32).readPointer();this.entry={sequence:++serial,threadId:tid,rawState:p,state:p.readS32(),addresses:{selectionCorrelationMatched:addresses.has(a.toString()),...(addresses.get(a.toString())||{}),...readAddresses(a)}};if(!active.has(tid))active.set(tid,[]);active.get(tid).push(this.entry);counters.loaderEntries++;}catch(error){fault('loader_entry',error);}},
    onLeave(){try{const e=this.entry;if(!e)return;counters.loaderReturns++;const stack=active.get(e.threadId)||[],i=stack.indexOf(e);if(i>=0)stack.splice(i,1);if(!stack.length)active.delete(e.threadId);record({status:'original_skeleton_source_loader_returned',sequence:e.sequence,rawUnboxedState:e.rawState.toString(),stateBefore:e.state,stateAfter:e.rawState.readS32(),...e.addresses});}catch(error){fault('loader_return',error);}}
  }));
  // This five-reference constructor is shared. Filter its actual original d13 caller.
  listeners.push(Interceptor.attach(ctor.virtualAddress,{
    onEnter(args){try{if(!this.returnAddress.equals(game.base.add(binding.sourceConstructorReturnRva)))return;const stack=active.get(Process.getCurrentThreadId())||[];this.entry=stack[stack.length-1]||null;this.output=args[0];this.inputAim=args[1].toString();this.inputCover=args[2].toString();}catch(error){fault('source_constructor_entry',error);}},
    onLeave(){try{if(!this.output)return;counters.sourceReturns++;const fields={};sourceNames.forEach((name,i)=>fields[name]=this.output.add(16+8*i).readPointer().toString());record({status:'original_skeleton_source_constructed',sequence:this.entry?.sequence||null,source:this.output.toString(),addresses:this.entry?.addresses||null,inputAim:this.inputAim,inputCover:this.inputCover,fields,normalConstructorReturn:true,callerRva:'0x056ad2d3',nativeGettersInvoked:false,combatStateWritten:false});}catch(error){fault('source_constructor_return',error);}}
  }));
  const snapshot=()=>({...counters,addressObjects:addresses.size,activeLoaderCalls:Array.from(active.values()).reduce((n,s)=>n+s.length,0),retainedListeners:listeners.length});
  safeEmit({status:'practice_skeleton_source_observer_installed',...binding,exceptionHelperHooked:false,managedGetterInvokedFromHooks:false});
  return {binding,listeners,active,addresses,snapshot,check(){if(counters.diagnosticErrors)throw new Error('Skeleton source observation failed: '+counters.diagnosticErrors);}};
}
