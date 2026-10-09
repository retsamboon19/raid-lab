// Passive object-identity stages for installed 2df7134a Mirror Break damage.
// No method replacements, arguments/results writes, or managed calls in hooks.
function installMechanicsBreakResultGapProbe(runtime,management,emit,options={}) {
  if (!runtime || !management || management.isNull() || typeof emit!=="function")
    throw new Error("Original result gap probe requires runtime/management/emit");
  const first=options.firstTick??1110,last=options.lastTick??1280,targetId=options.targetId??8192;
  const colliderIds=options.colliderIds??[819201,819202];
  if (![first,last,targetId].every(Number.isSafeInteger) || first<0 || last<first || targetId<1)
    throw new Error("Invalid original result stage window");
  if (!Array.isArray(colliderIds)||colliderIds.length<1||colliderIds.length>8||
      !colliderIds.every(x=>Number.isSafeInteger(x)&&x>0))
    throw new Error("Invalid original Break collider filter");
  const allowed=new Set(colliderIds);
  const game=Process.getModuleByName("GameAssembly.dll");
  const cls=runtime.class("NK.Spot.Logic.Character.DamageResultTargetInfo");
  const ctor=cls.method(".ctor",12);
  if (!ctor.virtualAddress.equals(game.base.add(0x063FF0D0)))
    throw new Error("Installed shot result constructor changed");
  const logic=runtime.class("NK.Spot.Logic.Common.DamageLogic");
  const before=logic.method("ProcessDamageTargetInfo",4);
  const process=logic.method("ProcessMonsterGetDamage",5);
  if (!before.virtualAddress.equals(game.base.add(0x063FA4C0)) ||
      !process.virtualAddress.equals(game.base.add(0x063FC880)))
    throw new Error("Installed result processing method changed");
  const shot=runtime.class("NK.Spot.Logic.Character.ShotLogic");
  const makeResults=shot.method("MakeShotResultTargetInfos",2);
  const send=management.class.method("SendEventDefault",1);
  const router=runtime.class("NK.Spot.Logic.Common.SpotLogicRouter")
    .method("RouteEvent",1);
  const monster=runtime.class("NK.Spot.Context.Monster.MonsterContext")
    .method("OnCommonHurt",1);
  const probablyDie=logic.method("TrySendProbablyDieEvent",6);
  const weakElement=logic.method("ExistWeakElement").overload(
    "System.Collections.Generic.List<System.Int32>",
    "System.Collections.Generic.List<System.Int32>");
  const hasFunction=runtime.class("NK.Spot.Context.FunctionContext")
    .method("HasFunction").overload(
      "NK.Spot.Model.Common.SpotEntity","NK.StaticData.FunctionType");
  for (const [method,rva] of [[makeResults,0x06407560],[send,0x0614BAF0],
    [router,0x06409220],[monster,0x06503490],
    [probablyDie,0x063FD2D0],[weakElement,0x063F2440],
    [hasFunction,0x06497F80]])
    if (!method.virtualAddress.equals(game.base.add(rva)))
      throw new Error("Installed event handoff method changed at "+rva.toString(16));
  const info=runtime.class("NK.Spot.Logic.Character.SpotEntityInfo");
  const hurt=runtime.class("NK.Spot.Event.Common.CommonHurtEvent");
  const data=runtime.class("NK.Spot.Logic.Character.DamageResultData");
  const event=runtime.class("NK.Spot.Common.SpotEvent");
  const entity=runtime.class("NK.Spot.Model.Common.SpotEntity");
  for (const [klass,name,offset] of [
    [management.class,"_tickCount",0x64],[info,"EntityID",0x10],
    [cls,"TargetInfo",0x18],[cls,"SubID",0x20],
    [cls,"Damage",0x28],[cls,"StatusInfo",0x30],
    [hurt,"ResultDataList",0x50],[data,"TargetInfos",0x18],
    [event,"<SpotEventID>k__BackingField",0x14],[entity,"Id",0x10]
  ]) if (klass.field(name).offset!==offset)
    throw new Error("Installed result stage field changed: "+klass.name+"."+name);
  let count=0,emitted=0,fault=null;
  let conditionCount=0,conditionEmitted=0,conditionSeq=0;
  const activeConditions=new Map();
  const targets=new Map();
  const tick=()=>management.handle.add(0x64).readS32();
  const inWindow=n=>n>=first&&n<=last;
  const id=p=>p.isNull()?null:p.add(0x10).readS32();
  const signed=p=>BigInt.asIntN(64,BigInt(p.toString())).toString();
  const row=(stage,p,n,detail={})=>{
    if (p.isNull()) return;
    const targetInfo=p.add(0x18).readPointer();
    if (id(targetInfo)!==targetId) return;
    const colliderId=p.add(0x38).readS32();
    if (!allowed.has(colliderId)) return;
    const pointer=p.toString();
    count++;
    const prior=targets.get(pointer)||[];prior.push(stage);
    if (!targets.has(pointer) && targets.size>=256)
      targets.delete(targets.keys().next().value);
    targets.set(pointer,prior);
    if (emitted<144) {
      emitted++;
      emit({status:"original_break_result_stage",stage,tick:n,
        objectPointer:pointer,targetId,subId:p.add(0x20).readS32(),
        damage:p.add(0x28).readS64().toString(),statusColliderId:colliderId,
        priorStages:prior.slice(0,8),...detail});
    }
  };
  const guard=(name,fn)=>{try {fn();} catch(error) {
    if(fault===null)fault=name+": "+String(error&&error.stack||error);
  }};
  // Raw IL2CPP List<T> reference-array layout; inspect only live list arguments
  // while the original method owns them, and only objects captured at ctor.
  const listItems=(list,visit)=>{
    if(list.isNull())return;
    const size=list.add(0x18).readS32();
    if(size<0||size>128)throw new Error("Unsupported event list size "+size);
    const array=list.add(0x10).readPointer();
    if(array.isNull())throw new Error("Null event list array");
    const capacity=Number(array.add(0x18).readU64());
    if(capacity<size||capacity>1048576)throw new Error("Invalid event list capacity");
    for(let i=0;i<size;i++)visit(array.add(0x20+i*Process.pointerSize).readPointer());
  };
  const scanResults=(stage,list,n)=>listItems(list,p=>{
    if(!p.isNull()&&targets.has(p.toString()))row(stage,p,n);
  });
  const scanEvent=(stage,eventPointer,n)=>{
    if(eventPointer.isNull()||eventPointer.add(0x14).readS32()!==1000)return;
    listItems(eventPointer.add(0x50).readPointer(),dataPointer=>{
      if(!dataPointer.isNull())
        scanResults(stage,dataPointer.add(0x18).readPointer(),n);
    });
  };
  const currentCondition=()=>{
    const stack=activeConditions.get(Process.getCurrentThreadId());
    return stack&&stack.length?stack[stack.length-1]:null;
  };
  const conditionRow=(stage,context,detail={})=>{
    conditionCount++;
    if(conditionEmitted<160){
      conditionEmitted++;
      emit({status:"original_break_send_condition",stage,
        callId:context.callId,tick:context.tick,targetId,
        targetPointer:context.targetPointer,subId:context.subId,...detail});
    }
  };
  const intList=list=>{
    if(list.isNull())return null;
    const size=list.add(0x18).readS32();
    if(size<0||size>16)throw new Error("Unsupported element list size "+size);
    const array=list.add(0x10).readPointer();
    if(array.isNull())throw new Error("Null element array");
    const capacity=Number(array.add(0x18).readU64());
    if(capacity<size||capacity>1048576)throw new Error("Invalid element array capacity");
    const values=[];
    for(let i=0;i<size;i++)values.push(array.add(0x20+i*4).readS32());
    return values;
  };
  const hooks=[];
  // Native constructor parameter 5 is the original StatValue, stored at +0x28.
  hooks.push(Interceptor.attach(ctor.virtualAddress,{
    onEnter(args) {guard("ctor.enter",()=>{
      this.object=null;const n=tick();if(!inWindow(n)||id(args[2])!==targetId)return;
      this.object=args[0];this.n=n;this.inputDamage=signed(args[4]);
    });},
    onLeave() {guard("ctor.leave",()=>{
      if(this.object)row("ctor",this.object,this.n,{inputDamage:this.inputDamage});
    });}
  }));
  hooks.push(Interceptor.attach(before.virtualAddress,{
    onEnter(args) {guard("ProcessDamageTargetInfo.enter",()=>{
      const n=tick();if(inWindow(n))row("processTargetEntry",args[2],n);
    });}
  }));
  hooks.push(Interceptor.attach(process.virtualAddress,{
    onEnter(args) {guard("ProcessMonsterGetDamage.enter",()=>{
      const n=tick();if(inWindow(n))row("processMonsterEntry",args[0],n,
        {casterPointer:args[1].toString(),monsterPointer:args[2].toString()});
    });}
  }));
  hooks.push(Interceptor.attach(makeResults.virtualAddress,{
    onEnter() {this.n=tick();this.sample=inWindow(this.n);},
    onLeave(retval) {guard("MakeShotResultTargetInfos.leave",()=>{
      if(this.sample)scanResults("makeResultsReturn",retval,this.n);
    });}
  }));
  for(const [method,stage] of [[send,"sendEventEntry"],
    [router,"routeEventEntry"],[monster,"monsterOnCommonHurtEntry"]])
    hooks.push(Interceptor.attach(method.virtualAddress,{
      onEnter(args) {guard(stage,()=>{
        const n=tick();if(inWindow(n))scanEvent(stage,args[1],n);
      });}
    }));
  // TrySendProbablyDieEvent has an IL2CPP hidden ValueTuple return buffer.
  // Correlate nested original predicates on the same thread and call, without
  // invoking any managed method or altering the result.
  hooks.push(Interceptor.attach(probablyDie.virtualAddress,{
    onEnter(args) {guard("TrySendProbablyDieEvent.enter",()=>{
      this.condition=null;
      const n=tick();
      if(!inWindow(n)||args[2].isNull()||args[2].add(0x10).readS32()!==targetId)return;
      const context={callId:++conditionSeq,tick:n,targetPointer:args[2].toString(),
        subId:args[3].toInt32(),buffer:args[0]};
      this.condition=context;
      const thread=Process.getCurrentThreadId();
      const stack=activeConditions.get(thread)||[];
      stack.push(context);activeConditions.set(thread,stack);
      conditionRow("trySendEntry",context,
        {casterPointer:args[1].toString()});
    });},
    onLeave() {guard("TrySendProbablyDieEvent.leave",()=>{
      const context=this.condition;if(!context)return;
      conditionRow("trySendReturn",context,{flags:[
        context.buffer.readU8(),context.buffer.add(1).readU8(),
        context.buffer.add(2).readU8()]});
      const thread=Process.getCurrentThreadId();
      const stack=activeConditions.get(thread);
      if(!stack||stack.pop()!==context)throw new Error("Original predicate call nesting changed");
      if(stack.length===0)activeConditions.delete(thread);
    });}
  }));
  hooks.push(Interceptor.attach(weakElement.virtualAddress,{
    onEnter(args) {guard("ExistWeakElement.enter",()=>{
      this.condition=currentCondition();
      if(this.condition)this.lists={casterElements:intList(args[0]),
        targetElements:intList(args[1])};
    });},
    onLeave(retval) {guard("ExistWeakElement.leave",()=>{
      if(this.condition)conditionRow("existWeakElement",this.condition,
        {...this.lists,result:(retval.toInt32()&0xff)!==0});
    });}
  }));
  hooks.push(Interceptor.attach(hasFunction.virtualAddress,{
    onEnter(args) {guard("HasFunction.enter",()=>{
      this.condition=null;
      const context=currentCondition();if(!context)return;
      const type=args[2].toInt32();
      if((type===37||type===110)&&!args[1].isNull()&&
          args[1].add(0x10).readS32()===targetId){
        this.condition=context;this.functionType=type;
      }
    });},
    onLeave(retval) {guard("HasFunction.leave",()=>{
      if(this.condition)conditionRow("hasFunction",this.condition,
        {functionType:this.functionType,result:(retval.toInt32()&0xff)!==0});
    });}
  }));
  return {snapshot:()=>({window:{firstTick:first,lastTick:last,targetId,colliderIds},
    count,emitted,logLimit:144,objects:targets.size,
    conditionCount,conditionEmitted,conditionLogLimit:160,
    activeConditionThreads:activeConditions.size,fault}),checkFault:()=>fault,
    detach:()=>{for(const hook of hooks)hook.detach();}};
}
