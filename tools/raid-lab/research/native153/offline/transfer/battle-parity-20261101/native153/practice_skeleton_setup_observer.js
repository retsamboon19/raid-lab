// Minimal passive diagnostic of one original skeleton async routine.
// No managed calls/getters from hooks, no mid-function hooks, no replacement.
function installPracticeSkeletonSetupObserver(emit) {
  if(typeof emit!=='function')throw new Error('Skeleton diagnostic requires the existing evidence sink');
  const binding={clientSha256:'d39896d3770888039c728a1908448c3db5efa7cdf874c90d56f46d8d566428d2',
    metadataSha256:'6f60f7aed3573afe1e5d56c86564a10d6a5bfa0799287337ef22935168a4c740',
    moveNextRva:0x07865060,moveNextEndRva:0x07867156,nullHelperRva:0x00841220,
    moveNextPrefix:'48894c24085356574154415541564157',
    nullHelperPrefix:'4883ec28e8d7630100cccccccccccccc'};
  if(Process.pointerSize!==8)throw new Error('Skeleton diagnostic requires exact153 x64 ABI');
  const game=Process.getModuleByName('GameAssembly.dll');
  const image=Il2Cpp.domain.assembly('NK.Spine.Runtime').image;
  const stateClass=image.class('NK.Spine.CombatSkeletonCharacterController').nested('<SetupSkeletonSetAsync>d__187');
  const move=stateClass.method('MoveNext',0);
  const getOffset=new NativeFunction(game.getExportByName('il2cpp_field_get_offset'),'uint64',['pointer']);
  const fields={state:{name:'<>1__state',boxed:16,type:'System.Int32'},
    skeletonSet:{name:'skeletonSet',boxed:40,type:'NK.Spine.CombatSkeletonCharacterController.CombatSkeletonSet'},
    source:{name:'source',boxed:48,type:'NK.Spine.CombatSkeletonCharacterController.CombatSkeletonSetSource'},
    owner:{name:'<>4__this',boxed:56,type:'NK.Spine.CombatSkeletonCharacterController'}};
  const offsets={};
  if(!stateClass.isValueType||stateClass.valueTypeSize!==88||move.isStatic||
      move.returnType.name!=='System.Void'||!move.virtualAddress.equals(game.base.add(binding.moveNextRva)))
    throw new Error('Original skeleton state-machine method/layout changed');
  for(const [key,spec]of Object.entries(fields)){
    const field=stateClass.field(spec.name),actual=Number(getOffset(field.handle).toString());
    if(actual!==spec.boxed||field.type.name!==spec.type||field.isStatic)
      throw new Error('Original skeleton raw field ABI changed: '+key);
    offsets[key]=actual-16;
  }
  // Native body reads state directly at[rcx] and owner at[rcx+28h].
  // Offsets above are API metadata BOX offsets minus the verified16-byte header.
  const hex=(address,size)=>Array.from(new Uint8Array(address.readByteArray(size)),
    byte=>byte.toString(16).padStart(2,'0')).join('');
  const helper=game.base.add(binding.nullHelperRva);
  // Validate BOTH entries before either listener can change its own prologue.
  if(hex(move.virtualAddress,16)!==binding.moveNextPrefix||hex(helper,16)!==binding.nullHelperPrefix)
    throw new Error('Original skeleton/helper bytes changed or a prior hook already occupies an entry');
  const active=new Map(),listeners=[];
  const counts={entries:0,normalReturns:0,targetNullRaises:0,entryRecords:0,nullRecords:0,diagnosticErrors:0};
  let sequence=0;
  const provenance=address=>{
    const module=Process.findModuleByAddress(address);
    return {address:address.toString(),module:module?.name||null,modulePath:module?.path||null,
      moduleOffset:module?address.sub(module.base).toString():null,
      gameAssemblyRva:module?.name.toLowerCase()==='gameassembly.dll'?address.sub(game.base).toString():null};
  };
  const readState=entry=>{
    try{return {rawUnboxedState:entry.address.toString(),state:entry.address.add(offsets.state).readS32(),
      skeletonSet:entry.address.add(offsets.skeletonSet).readPointer().toString(),
      source:entry.address.add(offsets.source).readPointer().toString(),
      owner:entry.address.add(offsets.owner).readPointer().toString()};}
    catch(error){return {rawUnboxedState:entry.address.toString(),rawReadError:String(error)};}
  };
  const fault=(where,error)=>{counts.diagnosticErrors++;if(counts.diagnosticErrors<=2)
    try{emit({status:'practice_skeleton_observer_diagnostic_error',where,error:String(error)});}catch(ignored){};};
  listeners.push(Interceptor.attach(move.virtualAddress,{
    onEnter(args){try{
      const threadId=Process.getCurrentThreadId();
      const entry={sequence:++sequence,threadId,address:args[0]};this.entry=entry;counts.entries++;
      if(!active.has(threadId))active.set(threadId,[]);
      active.get(threadId).push(entry);
      if(counts.entryRecords<16){counts.entryRecords++;
        emit({status:'original_skeleton_setup_move_next_entered',sequence:entry.sequence,threadId,
          caller:provenance(this.returnAddress),...readState(entry),nativeThisAbi:'unboxed88_byte_state_machine',
          nativeGettersInvokedByObserver:false,combatStateWritten:false});}
    }catch(error){fault('move_next_entry',error);}},
    onLeave(){try{
      const entry=this.entry;if(!entry)return;counts.normalReturns++;
      const stack=active.get(entry.threadId)||[],index=stack.findIndex(x=>x.sequence===entry.sequence);
      if(index>=0)stack.splice(index,1);
      if(stack.length===0)active.delete(entry.threadId);
    }catch(error){fault('move_next_leave',error);}}
  }));
  listeners.push(Interceptor.attach(helper,{
    onEnter(){try{
      const caller=this.returnAddress;
      if(caller.compare(game.base.add(binding.moveNextRva))<0||
          caller.compare(game.base.add(binding.moveNextEndRva))>=0)return;
      counts.targetNullRaises++;if(counts.nullRecords>=4)return;counts.nullRecords++;
      const threadId=Process.getCurrentThreadId(),stack=active.get(threadId)||[],entry=stack[stack.length-1];
      const callAddress=caller.sub(5),opcode=callAddress.readU8();
      const exactDirectCall=opcode===0xe8&&caller.add(callAddress.add(1).readS32()).equals(helper);
      emit({status:'original_skeleton_setup_null_guard_observed',threadId,
        sequence:entry?.sequence||null,actualHelperReturn:provenance(caller),
        originalDirectCallValidated:exactDirectCall,
        originalNullCallRva:exactDirectCall?callAddress.sub(game.base).toString():null,
        liveState:entry?readState(entry):null,activeStateObserved:!!entry,
        nullExceptionSuppressed:false,nativeGettersInvokedByObserver:false,combatStateWritten:false});
    }catch(error){fault('null_raise_entry',error);}}
  }));
  emit({status:'practice_skeleton_setup_observer_installed',...binding,
    rawStateOffsets:offsets,stateValueTypeSize:88,metadataBoxHeaderBytes:16,
    recordLimits:{entries:16,nullRaises:4,diagnosticErrors:2},
    ordinaryEntryHooksOnly:true,originalCallsReplaced:false,listenersRetainedUntilExit:true});
  return {retainedListeners:listeners,snapshot(){return {...counts,
    pendingObservedFrames:[...active.values()].reduce((n,stack)=>n+stack.length,0),
    nativeGettersInvokedByObserver:false,combatStateWritten:false,listenersRetainedUntilExit:true};}};
}
