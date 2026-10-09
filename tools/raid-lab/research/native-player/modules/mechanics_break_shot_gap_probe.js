// Passive outer-shot discriminator for installed GameAssembly 2df7134a.
// It observes original DamageLogic.GetDamage's final StatValue and status;
// it does not replace arguments, results, targeting, or combat state.
function installMechanicsBreakShotGapProbe(runtime,management,emit,options={}) {
  if (!runtime || !management || management.isNull() || typeof emit!=="function")
    throw new Error("Original shot damage probe requires runtime/management/emit");
  const first=options.firstTick??1110,last=options.lastTick??1280,targetId=options.targetId??8192;
  if (![first,last,targetId].every(Number.isSafeInteger) || first<0 || last<first || targetId<1)
    throw new Error("Invalid original shot observation bounds");
  const game=Process.getModuleByName("GameAssembly.dll");
  const outer=runtime.class("NK.Spot.Logic.Common.DamageLogic").method("GetDamage",5);
  const inner=runtime.class("NK.Spot.Logic.Common.DamageLogic").method("GetDamage",2);
  if (!outer.virtualAddress.equals(game.base.add(0x063F31F0)))
    throw new Error("Installed outer shot damage method changed");
  if (!inner.virtualAddress.equals(game.base.add(0x063F3CE0)))
    throw new Error("Installed inner shot damage method changed");
  const entity=runtime.class("NK.Spot.Model.Common.SpotEntity");
  const status=runtime.class("NK.Spot.Logic.Common.DamageStatusInfo");
  const target=runtime.class("NK.Spot.Model.Common.TargetDamageData");
  for (const [klass,name,offset] of [
    [management.class,"_tickCount",0x64],[entity,"Id",0x10],
    [status,"IsImmuneDamage",0x11],[status,"IsCore",0x12],
    [status,"IsBreak",0x13],[status,"IsIgnoreDamage",0x14],
    [status,"ColliderId",0x18],[status,"IsValidRange",0x1c],
    [status,"IsResist",0x1d],[status,"IsCounter",0x21],
    [status,"IsChoiceCollider",0x28],
    [target,"Target",0x10],[target,"PartsType",0x18],
    [target,"IsBreak",0x51],[target,"IsCounter",0x52],
    [target,"IsChoiceCollider",0x53],[target,"ColliderId",0x58]
  ]) if (klass.field(name).offset!==offset)
    throw new Error("Installed shot status field changed: "+klass.name+"."+name);
  const id=p=>p.isNull()?null:p.add(0x10).readS32();
  let count=0,emitted=0,fault=null;
  const active=new Map();
  const top=thread=>{const stack=active.get(thread);return stack&&stack[stack.length-1];};
  const hook=Interceptor.attach(outer.virtualAddress,{
    onEnter(args) {try {
      this.row=null;
      const tick=management.handle.add(0x64).readS32();
      if (tick<first || tick>last || id(args[2])!==targetId) return;
      this.out=args[0];
      this.row={tick,casterId:id(args[1]),targetId,
        colliderPointer:args[3].toString(),innerCalls:[]};
      const stack=active.get(this.threadId)||[];
      stack.push(this.row);active.set(this.threadId,stack);
    } catch(error) {if(fault===null)fault="outer.enter: "+String(error&&error.stack||error);}},
    onLeave() {try {
      if (!this.row) return;
      const stack=active.get(this.threadId);
      if (!stack || stack.pop()!==this.row) throw new Error("Nested shot call stack changed");
      if (!stack.length) active.delete(this.threadId);
      count++;
      if (emitted>=96) return;
      const p=this.out,s=p.add(8);
      emitted++;
      emit({status:"original_break_outer_shot_damage",...this.row,
        damage:p.readS64().toString(),colliderId:s.add(8).readS32(),
        immune:s.add(1).readU8()!==0,core:s.add(2).readU8()!==0,
        break:s.add(3).readU8()!==0,ignore:s.add(4).readU8()!==0,
        validRange:s.add(12).readU8()!==0,resist:s.add(13).readU8()!==0,
        counter:s.add(17).readU8()!==0,choice:s.add(24).readU8()!==0});
    } catch(error) {if(fault===null)fault="outer.leave: "+String(error&&error.stack||error);}}
  });
  const innerHook=Interceptor.attach(inner.virtualAddress,{
    onEnter(args) {try {
      this.row=null;
      const frame=top(this.threadId);
      if (!frame) return;
      const t=args[2];
      if (t.isNull() || id(t.readPointer())!==targetId) return;
      this.out=args[0];
      this.row={partsType:t.add(8).readS32(),
        colliderId:t.add(0x48).readS32(),
        break:t.add(0x41).readU8()!==0,
        counter:t.add(0x42).readU8()!==0,
        choice:t.add(0x43).readU8()!==0};
      frame.innerCalls.push(this.row);
    } catch(error) {if(fault===null)fault="inner.enter: "+String(error&&error.stack||error);}},
    onLeave() {try {
      if (this.row) this.row.calculatedDamage=this.out.readDouble();
    } catch(error) {if(fault===null)fault="inner.leave: "+String(error&&error.stack||error);}}
  });
  return {snapshot:()=>({window:{firstTick:first,lastTick:last,targetId},
    count,emitted,logLimit:96,fault}),checkFault:()=>fault,
    detach:()=>{innerHook.detach();hook.detach();}};
}
