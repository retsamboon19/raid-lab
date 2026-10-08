// Headless external-input boundary. Original KeyInputContext/SpotDriver and
// all aiming/fire code still run. Only that context's physical mouse sample
// receives a virtual screen coordinate while a tactical input lease is active.
function createMechanicsVirtualPointer(emit) {
  const game=Process.getModuleByName("GameAssembly.dll");
  const input=Il2Cpp.domain.assembly("UnityEngine.InputLegacyModule").image
    .class("UnityEngine.Input").method("get_mousePosition",0);
  const call=game.base.add(0x0649EEEB),returnAddress=game.base.add(0x0649EEF0);
  if (!input.virtualAddress.equals(game.base.add(0x082BF850)) ||
      [0xe8,0x60,0x09,0xe2,0x01].some((b,i)=>call.add(i).readU8()!==b))
    throw new Error("Original KeyInput mouse sampling callsite changed");
  const mainThread=Process.getCurrentThreadId();
  let point=null,substitutions=0,inactiveSamples=0,otherCallers=0,fault=null;
  const listener=Interceptor.attach(input.virtualAddress,{
    onEnter(args) {
      this.virtualOutput=null;
      if (!this.returnAddress.equals(returnAddress) || this.threadId!==mainThread) {
        otherCallers++; return;
      }
      if (point===null) { inactiveSamples++; return; }
      this.virtualOutput=args[0]; this.virtualPoint=point;
    },
    onLeave(result) {
      if (this.virtualOutput===null) return;
      try {
        if (this.virtualOutput.isNull() || !result.equals(this.virtualOutput))
          throw new Error("Original mouse getter Vector3 output contract changed");
        // Preserve original z. No managed calls, input flags or battle writes.
        this.virtualOutput.writeFloat(this.virtualPoint[0]);
        this.virtualOutput.add(4).writeFloat(this.virtualPoint[1]);
        substitutions++;
      } catch(error) { if (fault===null) fault=String(error); }
    }
  });
  function set(screen) {
    if (!Array.isArray(screen) || screen.length<2 || !screen.slice(0,2).every(Number.isFinite))
      throw new Error("Virtual pointer requires finite original screen coordinates");
    point=screen.slice(0,2);
  }
  function check() { if (fault!==null) throw new Error(fault); }
  function snapshot() {
    return {active:point!==null,substitutions,inactiveSamples,otherCallers,fault,
      originalGetterRva:"0x082BF850",exactCallerReturnRva:"0x0649EEF0"};
  }
  // Retain the hook until fresh private process exit; clear merely ends input.
  emit({status:"original_virtual_pointer_ready",...snapshot(),mainThread,
    hookRetainedUntilProcessExit:true,retainsOriginalInputPolling:true});
  return {set,clear:()=>{point=null;},check,snapshot,listener};
}
