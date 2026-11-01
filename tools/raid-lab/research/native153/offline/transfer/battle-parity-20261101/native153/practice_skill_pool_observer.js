// Passive exact153 observation only. No native getter invocation, argument,
// return-value, pool, exception, clock or combat-state replacement.
function installPracticeSkillPoolObserver(emit) {
  if (typeof emit!=='function') throw new Error('Skill-pool observer requires an evidence sink');
  const binding={
    clientSha256:'d39896d3770888039c728a1908448c3db5efa7cdf874c90d56f46d8d566428d2',
    poolMetadataSha256:'bac4c5d59ee60417ef35d4eb7193fd231f8b378e44c22edde688118d2cb9fbb8',
    fxMetadataSha256:'a071361fb452c7118416291263684558295c01cc1b42a9a24bd150a05325310b',
    preloadRva:0x068103b0,fxGetterRva:0x0544dc20,
    preloadPrefix:'48895c241848896c2420564883ec4080',
    fxGetterPrefix:'40534883ec20803d21ca4e0600753748'
  };
  const game=Process.getModuleByName('GameAssembly.dll');
  const runtime=Il2Cpp.domain.assembly('NK.Runtime').image;
  const preload=runtime.class('NK.Spot.Logic.Skill.SpotSkillLogic').method('PreloadSkillDirectorPool',2);
  const getter=runtime.class('NK.Spot.Presentation.FXController').method('get_Instance',0);
  const hex=(address,size)=>Array.from(new Uint8Array(address.readByteArray(size)),
    value=>value.toString(16).padStart(2,'0')).join('');
  if (!preload.isStatic||preload.returnType.name!=='System.Void'||
      preload.parameters.map(value=>value.type.name).join('|')!==
        'UnityEngine.GameObject|NK.Spot.Model.Character.Skill.SpotSkill'||
      !getter.isStatic||getter.returnType.name!=='NK.Spot.Presentation.FXController'||
      !preload.virtualAddress.equals(game.base.add(binding.preloadRva))||
      !getter.virtualAddress.equals(game.base.add(binding.fxGetterRva))||
      hex(preload.virtualAddress,16)!==binding.preloadPrefix||
      hex(getter.virtualAddress,16)!==binding.fxGetterPrefix)
    throw new Error('Exact current153 skill pool/getter signatures or original bytes changed');
  const limit=32,traceLimit=6,traceFrames=16,active=new Map(),listeners=[];
  const counts={preloadEntries:0,preloadNormalReturns:0,getterCallsInsidePreload:0,
    getterReturnsInsidePreload:0,nullTimelineArguments:0,nullSkillArguments:0,
    nullFxGetterReturns:0,preloadRecords:0,getterRecords:0,returnRecords:0,
    traceRecords:0,diagnosticErrors:0};
  let nextCallId=0;
  const describe=address=>{
    const module=Process.findModuleByAddress(address);
    return {address:address.toString(),module:module?.name||null,
      modulePath:module?.path||null,moduleOffset:module?address.sub(module.base).toString():null,
      gameAssemblyRva:module?.name.toLowerCase()==='gameassembly.dll'
        ?address.sub(module.base).toString():null};
  };
  const reportError=(where,error)=>{
    counts.diagnosticErrors++;
    if(counts.diagnosticErrors<=4)emit({status:'practice_skill_pool_observer_diagnostic_error',
      where,error:String(error),combatStateWritten:false});
  };
  listeners.push(Interceptor.attach(preload.virtualAddress,{
    onEnter(args) {
      try {
        const threadId=Process.getCurrentThreadId(),callId=++nextCallId;
        counts.preloadEntries++;
        if(args[0].isNull())counts.nullTimelineArguments++;
        if(args[1].isNull())counts.nullSkillArguments++;
        const entry={callId,threadId,timelinePrefab:args[0].toString(),skill:args[1].toString(),
          timelinePrefabNull:args[0].isNull(),skillNull:args[1].isNull(),
          methodInfoArgument:args[2].toString(),caller:describe(this.returnAddress)};
        this.entry=entry;
        if(!active.has(threadId))active.set(threadId,[]);
        active.get(threadId).push(entry);
        if(counts.preloadRecords>=limit)return;
        counts.preloadRecords++;
        if(counts.traceRecords<traceLimit) {
          counts.traceRecords++;
          try {
            entry.backtraceKind='Frida.ACCURATE_from_live_entry_context';
            entry.backtrace=Thread.backtrace(this.context,Backtracer.ACCURATE)
              .slice(0,traceFrames).map(describe);
          }catch(error){entry.backtraceError=String(error);}
        }
        emit({status:'original_practice_skill_pool_entry',...entry,
          originalEntryRva:'0x068103B0',nativeGettersInvokedByObserver:false,
          argumentsChanged:false,combatStateWritten:false});
      }catch(error){reportError('preload_entry',error);}
    },
    onLeave() {
      try {
        const entry=this.entry;
        if(!entry)return;
        counts.preloadNormalReturns++;
        const stack=active.get(entry.threadId)||[];
        const index=stack.findIndex(value=>value.callId===entry.callId);
        if(index>=0)stack.splice(index,1);
        if(stack.length===0)active.delete(entry.threadId);
        if(counts.returnRecords<limit) {
          counts.returnRecords++;
          emit({status:'original_practice_skill_pool_returned',callId:entry.callId,
            threadId:entry.threadId,originalMethodReturned:true,resultOrStateChanged:false});
        }
      }catch(error){reportError('preload_leave',error);}
    }
  }));
  listeners.push(Interceptor.attach(getter.virtualAddress,{
    onEnter() {
      try {
        const stack=active.get(Process.getCurrentThreadId());
        if(!stack||stack.length===0)return;
        this.poolEntry=stack[stack.length-1];
        this.caller=describe(this.returnAddress);
        counts.getterCallsInsidePreload++;
      }catch(error){reportError('getter_entry',error);}
    },
    onLeave(retval) {
      try {
        if(!this.poolEntry)return;
        counts.getterReturnsInsidePreload++;
        if(retval.isNull())counts.nullFxGetterReturns++;
        if(counts.getterRecords>=limit)return;
        counts.getterRecords++;
        emit({status:'original_practice_fx_getter_return_inside_pool',
          callId:this.poolEntry.callId,threadId:this.poolEntry.threadId,
          originalGetterRva:'0x0544DC20',returnPointer:retval.toString(),
          returnIsNull:retval.isNull(),caller:this.caller,
          observedNormalNativeReturn:true,nativeGettersInvokedByObserver:false,
          returnValueChanged:false,combatStateWritten:false});
      }catch(error){reportError('getter_leave',error);}
    }
  }));
  emit({status:'practice_skill_pool_observer_installed',...binding,
    recordLimitPerKind:limit,accurateBacktraceLimit:traceLimit,backtraceFrames:traceFrames,
    listenersRetainedUntilExit:true,originalCallsReplaced:false});
  return {retainedListeners:listeners,snapshot(){return {...counts,
    pendingObservedCalls:[...active.values()].reduce((total,stack)=>total+stack.length,0),
    listenersRetainedUntilExit:true,nativeGettersInvokedByObserver:false,combatStateWritten:false};}};
}
