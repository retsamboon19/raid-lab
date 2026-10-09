// Passive trial-129 discriminator for the installed 2df7134a client.
// Installs entry/return hooks only; it never changes a native argument/result.
function installMechanicsBreakDamageProbe(runtime,management,emit,options={}) {
  if (!runtime || !management || management.isNull() || typeof emit!=="function")
    throw new Error("Break damage probe needs original runtime and management");
  const first=options.firstTick??1110,last=options.lastTick??1280;
  const targetId=options.targetId??8192;
  if (!Number.isSafeInteger(first) || !Number.isSafeInteger(last) || first<0 || last<first ||
      !Number.isSafeInteger(targetId) || targetId<1)
    throw new Error("Invalid bounded break damage observation window");
  const game=Process.getModuleByName("GameAssembly.dll");
  const method=(klass,name,argc,rva)=>{
    const value=runtime.class(klass).method(name,argc);
    if (!value.virtualAddress.equals(game.base.add(rva)))
      throw new Error("Installed break damage method changed: "+klass+"."+name);
    return value.virtualAddress;
  };
  const damageClass="NK.Spot.Logic.Common.DamageLogic";
  const getDamage=method(damageClass,"GetDamage",2,0x063F3CE0);
  const processDamage=method(damageClass,"ProcessMonsterGetDamage",5,0x063FC880);
  const setDamage=method("NK.Spot.Logic.Monster.MonsterAttackLogic","SetDamage",10,0x063C2330);
  const hasFunctionMethod=runtime.class("NK.Spot.Context.FunctionContext").method("HasFunction")
    .overload("NK.Spot.Model.Common.SpotEntity","NK.StaticData.FunctionType");
  if (!hasFunctionMethod.virtualAddress.equals(game.base.add(0x06497F80)))
    throw new Error("Installed HasFunction(FunctionType) overload changed");
  const hasFunction=hasFunctionMethod.virtualAddress;
  const entity=runtime.class("NK.Spot.Model.Common.SpotEntity");
  const result=runtime.class("NK.Spot.Logic.Character.DamageResultTargetInfo");
  const target=runtime.class("NK.Spot.Model.Common.TargetDamageData");
  const caster=runtime.class("NK.Spot.Model.Common.CasterDamageData");
  const managementClass=management.class;
  for (const [klass,name,offset] of [
    [managementClass,"_tickCount",0x64],[entity,"Id",0x10],
    [result,"TargetInfo",0x18],[result,"SubID",0x20],
    [result,"Damage",0x28],[result,"IsCoreHit",0x90],
    [target,"Target",0x10],[target,"PartsType",0x18],
    [target,"Defence",0x20],
    [target,"IsBreak",0x51],[target,"IsCounter",0x52],
    [target,"IsChoiceCollider",0x53],[target,"ColliderId",0x58],
    [caster,"Caster",0x10],[caster,"Attack",0x20],
    [caster,"AttackType",0x58],[caster,"ElementIDList",0x208]
  ]) if (klass.field(name).offset!==offset)
    throw new Error("Installed break damage field changed: "+klass.name+"."+name);
  // TargetDamageData/CasterDamageData are unboxed structs. Their metadata
  // offsets above include the 16-byte IL2CPP object header.
  const counts={calculate:0,process:0,setDamage:0,immunityCheck:0};
  const limit=32,emittedByKind={calculate:0,process:0,setDamage:0,immunityCheck:0};
  let emitted=0,fault=null;
  const tick=()=>management.handle.add(0x64).readS32();
  const active=()=>{const n=tick();return n>=first&&n<=last?n:null;};
  const id=ptr=>ptr.isNull()?null:ptr.add(0x10).readS32();
  const record=(kind,row)=>{
    counts[kind]++;
    if (emittedByKind[kind]<limit) {emittedByKind[kind]++;emitted++;
      emit({status:"original_break_damage_diagnostic",kind,...row});}
  };
  const guard=(where,fn)=>{try {fn();} catch(error) {
    if (fault===null) fault=where+": "+String(error&&error.stack||error);
  }};
  const hooks=[];
  // x64 IL2CPP large ValueTuple return: args[0] is the hidden output buffer.
  hooks.push(Interceptor.attach(getDamage,{
    onEnter(args) {guard("GetDamage.enter",()=>{
      this.row=null;const n=active();if (n===null) return;
      const t=args[2];if (t.isNull() || id(t.readPointer())!==targetId) return;
      const c=args[1];this.out=args[0];
      this.row={tick:n,casterId:c.isNull()?null:id(c.readPointer()),targetId,
        casterAttack:c.isNull()?null:c.add(0x10).readS64().toString(),
        casterAttackType:c.isNull()?null:c.add(0x48).readS32(),
        elementListPresent:!c.isNull()&&!c.add(0x1f8).readPointer().isNull(),
        partsType:t.add(8).readS32(),isBreak:t.add(0x41).readU8()!==0,
        isCounter:t.add(0x42).readU8()!==0,isChoice:t.add(0x43).readU8()!==0,
        colliderId:t.add(0x48).readS32(),targetDefence:t.add(0x10).readS64().toString()};
    });},
    onLeave() {guard("GetDamage.leave",()=>{
      if (this.row) record("calculate",{...this.row,calculatedDamage:this.out.readDouble()});
    });}
  }));
  // DamageResultTargetInfo is a managed reference, hence full metadata offsets.
  hooks.push(Interceptor.attach(processDamage,{
    onEnter(args) {guard("ProcessMonsterGetDamage.enter",()=>{
      const n=active();if (n===null || id(args[2])!==targetId) return;
      const info=args[0];if (info.isNull()) return;
      record("process",{tick:n,casterId:id(args[1]),targetId,
        partsType:args[3].toInt32(),subId:info.add(0x20).readS32(),
        inputDamage:info.add(0x28).readS64().toString(),
        isCoreHit:info.add(0x90).readU8()!==0});
    });}
  }));
  // SetDamage has a hidden 16-byte return buffer in args[0]. Its arg3 is the
  // raw StatValue passed unchanged to MonsterBreakColliderHurtEvent::.ctor.
  hooks.push(Interceptor.attach(setDamage,{
    onEnter(args) {guard("MonsterAttackLogic.SetDamage.enter",()=>{
      const n=active();if (n===null || id(args[1])!==targetId) return;
      record("setDamage",{tick:n,casterId:id(args[4]),targetId,
        partsType:args[2].toInt32(),
        rawDamage:BigInt.asIntN(64,BigInt(args[3].toString())).toString()});
    });}
  }));
  // FunctionType 38 = ImmuneDamage_MainHP in exact installed enum literals.
  hooks.push(Interceptor.attach(hasFunction,{
    onEnter(args) {guard("HasFunction.enter",()=>{
      this.row=null;if (args[2].toInt32()!==38) return;
      const n=active();if (n===null || id(args[1])!==targetId) return;
      this.row={tick:n,targetId,functionType:"ImmuneDamage_MainHP"};
    });},
    onLeave(retval) {guard("HasFunction.leave",()=>{
      if (this.row) record("immunityCheck",{...this.row,active:(retval.toInt32()&0xff)!==0});
    });}
  }));
  return {snapshot:()=>({window:{firstTick:first,lastTick:last,targetId},
    counts:{...counts},emitted,emittedByKind:{...emittedByKind},perKindLogLimit:limit,fault}),checkFault:()=>fault,
    detach:()=>{for(const hook of hooks) hook.detach();}};
}
