// Current153 external-input boundary only. Retain listener until private exit.
function createMechanicsVirtualPointer(emit) {
  const binding=kraken153Binding(), spec=binding.virtualPointer;
  const game=Process.getModuleByName('GameAssembly.dll');
  const input=Il2Cpp.domain.assembly('UnityEngine.InputLegacyModule').image
    .class('UnityEngine.Input').method('get_mousePosition',0);
  requireKraken153Method(input,binding.methods.mouse.rva);
  const call=game.base.add(spec.callRva),returnAddress=game.base.add(spec.returnRva);
  const bytes=Array.from(new Uint8Array(call.readByteArray(5)),b=>b.toString(16).padStart(2,'0')).join('');
  if(bytes!==spec.callHex || call.readU8()!==0xe8 || spec.returnRva!==spec.callRva+5 ||
      !call.add(5).add(call.add(1).readS32()).equals(input.virtualAddress))
    throw Error('Current153 exact KeyInputContext mouse call changed');
  const mainThread=Process.getCurrentThreadId();
  let point=null,substitutions=0,inactiveSamples=0,otherCallers=0,fault=null;
  const listener=Interceptor.attach(input.virtualAddress,{
    onEnter(args) {
      this.virtualOutput=null;
      if(!this.returnAddress.equals(returnAddress)||this.threadId!==mainThread){otherCallers++;return;}
      if(point===null){inactiveSamples++;return;}
      this.virtualOutput=args[0];this.virtualPoint=point;
    },
    onLeave(result) {
      if(this.virtualOutput===null)return;
      try {
        if(this.virtualOutput.isNull()||!result.equals(this.virtualOutput))
          throw Error('Original current153 Vector3 return buffer changed');
        this.virtualOutput.writeFloat(this.virtualPoint[0]);
        this.virtualOutput.add(4).writeFloat(this.virtualPoint[1]);
        substitutions++;
      }catch(error){if(fault===null)fault=String(error);}
    }
  });
  const set=screen=>{
    if(!Array.isArray(screen)||screen.length<2||!screen.slice(0,2).every(Number.isFinite))
      throw Error('Virtual pointer requires finite screen x/y');
    point=screen.slice(0,2);
  };
  const snapshot=()=>({active:point!==null,substitutions,inactiveSamples,otherCallers,fault,
    originalGetterRva:binding.methods.mouse.rva,exactCallerReturnRva:spec.returnRva});
  const check=()=>{if(fault!==null)throw Error(fault);};
  emit({status:'original_virtual_pointer_ready',...snapshot(),mainThread,
    hookRetainedUntilProcessExit:true,retainsOriginalInputPolling:true});
  return{set,clear:()=>{point=null;},check,snapshot,listener};
}
