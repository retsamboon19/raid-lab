// Passive, single-tick trace of the installed DamageLogic range decision.
// This observes original code and the existing SendEventDefault event stream.
function installMechanicsRangeTrace(runtime, management, emit) {
  const expected={damage:0x063f3ce0,min:0x06385e90,max:0x06385e10};
  const damage=runtime.class("NK.Spot.Logic.Common.DamageLogic").method("GetDamage",2);
  const character=runtime.class("NK.Spot.Model.Character.SpotCharacter");
  const min=character.method("get_BonusRangeMin",0);
  const max=character.method("get_BonusRangeMax",0);
  for (const [method,rva,label] of [[damage,expected.damage,"GetDamage(CasterDamageData, TargetDamageData)"],
    [min,expected.min,"get_BonusRangeMin"],[max,expected.max,"get_BonusRangeMax"]]) {
    if (Number(method.relativeVirtualAddress)!==rva)
      throw new Error("Installed range trace method changed: "+label);
  }
  const watchTick=1421, watchCaster=mechanicsRequestedEntityId(5099), watchTarget=8192, maxRecords=64;
  const active=new Map();
  let records=0, fault=null;
  const live=pointer=>pointer!=null && !pointer.isNull();
  const tick=()=>Number(management.field("_tickCount").value);
  const record=row=>{
    if (records>=maxRecords) throw new Error("Original range trace exceeded "+maxRecords+" records");
    records++;
    emit({status:"original_naga_range_probe",ordinal:records,...row});
  };
  const fail=(where,error)=>{
    if (fault===null) fault=where+": "+(error && error.stack ? error.stack : String(error));
  };
  const top=threadId=>{
    const stack=active.get(threadId);
    return stack && stack.length?stack[stack.length-1]:null;
  };
  // Native GetDamage has a hidden return-buffer pointer in RCX, followed by
  // pointers to the unboxed CasterDamageData and TargetDamageData structs.
  Interceptor.attach(damage.virtualAddress,{
    onEnter(args) {
      try {
        const casterData=args[1], targetData=args[2];
        if (!live(casterData) || !live(targetData)) return;
        const caster=casterData.readPointer(), target=targetData.readPointer();
        if (!live(caster) || !live(target)) return;
        if (tick()!==watchTick || caster.add(16).readS32()!==watchCaster ||
            target.add(16).readS32()!==watchTarget) return;
        const frame={tick:watchTick,casterId:watchCaster,targetId:watchTarget,
          hitDepth:casterData.add(492).readFloat(),
          priorBonusRangeRatio:casterData.add(488).readS32(),
          targetIsCore:!!targetData.add(64).readU8(),
          targetColliderId:targetData.add(72).readS32(),
          min:null,max:null,casterData};
        const stack=active.get(this.threadId)||[];
        stack.push(frame);
        active.set(this.threadId,stack);
        this.frame=frame;
      } catch(error) {fail("DamageLogic.GetDamage.onEnter",error);}
    },
    onLeave() {
      if (!this.frame) return;
      try {
        const stack=active.get(this.threadId);
        if (!stack || stack.pop()!==this.frame) throw new Error("Range trace stack mismatch");
        if (!stack.length) active.delete(this.threadId);
        record({source:"DamageLogic.GetDamage",tick:this.frame.tick,
          casterId:this.frame.casterId,targetId:this.frame.targetId,
          hitDepth:this.frame.hitDepth,
          bonusRangeMin:this.frame.min,bonusRangeMax:this.frame.max,
          priorBonusRangeRatio:this.frame.priorBonusRangeRatio,
          computedBonusRangeRatio:this.frame.casterData.add(488).readS32(),
          targetIsCore:this.frame.targetIsCore,
          targetColliderId:this.frame.targetColliderId});
      } catch(error) {fail("DamageLogic.GetDamage.onLeave",error);}
    }
  });
  const observeBound=(method,name)=>Interceptor.attach(method.virtualAddress,{
    onLeave(retval) {
      try {
        const frame=top(this.threadId);
        // Frida's NativePointer has no toInt64() method. Its hex string is
        // parsed as a signed 64-bit return value from the StatValue getter.
        if (frame) frame[name]=int64(retval.toString()).toString();
      } catch(error) {fail("SpotCharacter.get_BonusRange"+name+".onLeave",error);}
    }
  });
  observeBound(min,"min");
  observeBound(max,"max");
  function observeSendEvent(event) {
    if (!event || event.isNull() || tick()!==watchTick ||
        event.class.type.name!=="NK.Spot.Event.Common.DamageLogEvent") return;
    const caster=event.field("CasterInfo").value;
    const target=event.field("TargetInfo").value;
    if (!caster || caster.isNull() || !target || target.isNull()) return;
    if (Number(caster.field("EntityID").value)!==watchCaster ||
        Number(target.field("EntityID").value)!==watchTarget) return;
    const status=event.field("_damageStatusInfo").value;
    record({source:"DamageLogEvent",tick:watchTick,casterId:watchCaster,
      targetId:watchTarget,depth:Number(event.field("Depth").value),
      isValidRange:Boolean(status.field("IsValidRange").value),
      isCore:Boolean(status.field("IsCore").value),
      isCritical:Boolean(status.field("IsCritical").value),
      colliderId:Number(status.field("ColliderId").value),
      damage:event.field("Damage").value.field("Value").value.toString(),
      actualDamage:event.field("ActualDamage").value.field("Value").value.toString()});
  }
  return {observeSendEvent,checkFault:()=>{if(fault!==null) throw new Error(fault);},
    getRecordCount:()=>records};
}
