// Read-only current153 original shot statistics. Actor-selection evidence only.
function createMechanicsQteActorEvidence(runtime, management, pin, emit) {
  "use strict";
  if (!runtime || !management || typeof pin !== "function" || typeof emit !== "function" ||
      typeof invokeChecked !== "function" || typeof intArg !== "function")
    throw Error("Original QTE actor evidence requires bridge and management");
  const game=Process.getModuleByName("GameAssembly.dll");
  const root="NK.Spot.Context.StatisticsContext";
  const live=x=>x!=null&&!x.isNull();
  const field=(cls,name,offset,type)=>{
    const f=cls.field(name);
    if(f.offset!==offset || f.type.name!==type) throw Error("QTE evidence field ABI differs: "+name);
  };
  const checked=(method,rva,prefix,returns)=>{
    const actual=Array.from(new Uint8Array(method.virtualAddress.readByteArray(prefix.length/2)),x=>x.toString(16).padStart(2,"0")).join("");
    if(!method.virtualAddress.equals(game.base.add(rva)) || actual!==prefix || method.isStatic ||
       method.parameters.length!==0 || method.returnType.name!==returns)
      throw Error("QTE evidence method ABI differs: "+method.name);
    return method;
  };
  field(management.class,"_contexts",32,"System.Collections.Generic.Dictionary<System.Type,NK.Spot.Interface.IContextBase>");
  const cls=runtime.class(root), roundCls=cls.nested("SpotStatisticsData");
  field(roundCls,"RedTeamData",48,"System.Collections.Generic.Dictionary<System.Int32,"+root+".CharacterStatisticsData>");
  field(cls.nested("CharacterStatisticsData"),"ShotData",96,root+".ShotData");
  field(cls.nested("ShotData"),"DamageData",168,root+".DamageData");
  const current=checked(cls.method("get_Current",0),118481888,"40534883ec20803ddcbf840400488bd97543488d0defa0e1",root+".SpotStatisticsData");
  const damage=checked(cls.nested("DamageData").method("get_TotalActualTakeDamage",0),118517200,"4883ec284c8b41184d85c07423488b51284885d2741a488b","System.Int64");
  const wholeDamage=checked(cls.nested("EntityStatisticsData").method("get_TakeTotalActualDamage",0),118526784,"4883ec28488b51104885d27423488b52184885d2741a488b","System.Int64");
  const contexts=management.field("_contexts").value;
  if(!live(contexts))throw Error("Original QTE statistics registry missing");
  const context=pin(invokeChecked(contexts.method("get_Item",1),contexts,[cls.type.object.handle]));
  if(!live(context))throw Error("Original QTE statistics context missing");
  return {read(actors,tick,mode="shot"){
    if(!["shot","whole_outgoing"].includes(mode))throw Error("Invalid actor evidence mode");
    if(!Array.isArray(actors)||!Number.isSafeInteger(tick)||tick<0)throw Error("Invalid QTE evidence request");
    const round=invokeChecked(current,context);
    if(!live(round))throw Error("Original QTE statistics round missing");
    const red=round.field("RedTeamData").value;
    if(!live(red))throw Error("Original QTE red statistics missing");
    const result=Object.create(null),seen=new Set();
    for(const actor of actors){
      const id=typeof actor==="number"?actor:actor.entityId;
      if(!Number.isSafeInteger(id)||id<0||id>2147483647||seen.has(id))throw Error("Invalid QTE evidence actor ID");
      seen.add(id);
      // Dictionary get_Item is read-only and fails if this actor was never registered.
      const stats=invokeChecked(red.method("get_Item",1),red,[intArg(id)]);
      if(!live(stats))throw Error("Original QTE actor statistics missing");
      let value;
      if(mode==="whole_outgoing") {
        value=invokeChecked(wholeDamage,stats).unbox().handle.readS64().toString();
      } else {
        const shot=stats.field("ShotData").value;
        if(!live(shot))throw Error("Original QTE shot statistics missing");
        const data=shot.field("DamageData").value;
        if(!live(data))throw Error("Original QTE shot damage missing");
        value=invokeChecked(damage,data).unbox().handle.readS64().toString();
      }
      if(!/^(0|[1-9][0-9]*)$/.test(value))throw Error("Invalid original QTE damage evidence");
      result[String(id)]=value;
    }
    emit(mode==="whole_outgoing"?
      {status:"original_directed_actor_evidence",tick,mode,source:"StatisticsContext.Current.RedTeamData.TakeTotalActualDamage",actualWholeOutgoingDamageByActor:result,
        interpretation:"Original whole outgoing totals include skills/passives; ordinary aim selection heuristic only, not weapon DPS, predicted damage or calculated score"}:
      {status:"original_qte_actor_evidence",tick,mode,source:"StatisticsContext.Current.RedTeamData.ShotData.DamageData.TotalActualTakeDamage",actualShotDamageByActor:result,
        interpretation:"Observed totals over common elapsed battle time; actor-selection evidence, not predicted QTE damage or calculated score"});
    return result;
  }};
}

function createMechanicsWeaponInputEvidence(runtime,aimBinding,emit,enabled) {
 if(!enabled)return {read:()=>({supported:false,reason:"outside_mirror"})};
 const rows={"normal": {"rva": 107908608, "prefix": "40534883ec500f104120488bd933d20f1049300f29442420", "returns": "NK.Common.StatValue", "class": "NK.Spot.Model.Character.Weapon.SpotWeaponData"}, "full": {"rva": 107906144, "prefix": "48895c240848896c24104889742418574883ec50803d55c2", "returns": "NK.Common.StatValue", "class": "NK.Spot.Model.Character.Weapon.SpotWeaponData"}, "time": {"rva": 107904240, "prefix": "48895c2418574883ec20803dcec9250500488bf9751f488d", "returns": "System.Single", "class": "NK.Spot.Model.Character.Weapon.SpotWeaponData"}, "attack": {"rva": 107872224, "prefix": "4889742418574881ec80000000803d5446260500488bf975", "returns": "NK.Common.StatValue", "class": "NK.Spot.Model.Common.SpotEntityStatus"}};

 const names={normal:'get_NormalDamage',full:'get_FullChargeDamage',time:'get_ChargeTime',attack:'get_Attack'},methods={};
 const game=Process.getModuleByName('GameAssembly.dll');
 for(const [key,row]of Object.entries(rows)) {
  const m=runtime.class(row.class).method(names[key],0),prefix=Array.from(new Uint8Array(m.virtualAddress.readByteArray(24)),x=>x.toString(16).padStart(2,'0')).join('');
  if(!m.virtualAddress.equals(game.base.add(row.rva))||prefix!==row.prefix||m.isStatic||m.parameters.length||m.returnType.name!==row.returns)throw Error('Original weapon-index getter ABI changed: '+names[key]);
  methods[key]=m;
 }
 const live=x=>x!=null&&!x.isNull();
 function read(actorIds,tick) {
  try {
   const values=[];
   for(const actorId of actorIds) {
    try {
    const actor=aimBinding.bound.get(actorId)?.entity;if(!live(actor))throw Error('Native weapon-index actor missing');
    const weapon=actor.field('<CurrentWeaponData>k__BackingField').value,status=actor.field('<CurrentStatus>k__BackingField').value;
    if(!live(weapon)||!live(status))throw Error('Native weapon-index references missing');
    const scalar=(method,owner)=>invokeChecked(method,owner).unbox().handle.readS64().toString();
    const nativeAttack=scalar(methods.attack,status),nativeNormalDamage=scalar(methods.normal,weapon),nativeFullChargeDamage=scalar(methods.full,weapon);
    const chargeTimeSeconds=invokeChecked(methods.time,weapon).unbox().handle.readFloat();
    if(![nativeAttack,nativeNormalDamage,nativeFullChargeDamage].every(v=>/^\d+$/.test(v))||!Number.isFinite(chargeTimeSeconds)||chargeTimeSeconds<=0)throw Error('Native weapon-index stat invalid '+JSON.stringify({actorId,nativeAttack,nativeNormalDamage,nativeFullChargeDamage,chargeTimeSeconds}));
    const numerator=BigInt(nativeAttack)*BigInt(nativeNormalDamage)*BigInt(nativeFullChargeDamage);
    let denominator=1n,multiplier=1n;
    if(chargeTimeSeconds>0) {
     const view=new DataView(new ArrayBuffer(4));view.setFloat32(0,chargeTimeSeconds,true);const bits=view.getUint32(0,true),exp=(bits>>>23)&255,mantissa=BigInt((bits&0x7fffff)+(exp?0x800000:0)),power=(exp?exp-127:-126)-23;
     denominator=mantissa;if(power>=0)denominator<<=BigInt(power);else multiplier<<=BigInt(-power);
    }
    values.push({actorId,weaponIdentity:weapon.handle.toString(),nativeAttack,nativeNormalDamage,nativeFullChargeDamage,chargeTimeSeconds,indexNumerator:(numerator*multiplier).toString(),indexDenominator:denominator.toString()});
    } catch(error) { emit({status:'original_native_weapon_input_actor_unavailable',tick,actorId,error:String(error)}); }
   }
   if(!values.length)throw Error('No current native weapon input index available');
   values.sort((a,b)=>BigInt(a.indexNumerator)*BigInt(b.indexDenominator)>BigInt(b.indexNumerator)*BigInt(a.indexDenominator)?-1:BigInt(a.indexNumerator)*BigInt(b.indexDenominator)<BigInt(b.indexNumerator)*BigInt(a.indexDenominator)?1:a.actorId-b.actorId);
   emit({status:'original_native_weapon_input_index',tick,values,meaning:'Selection heuristic from original current weapon coefficients, attack and charge timing; includes no passive/Burst damage counter. Not predicted damage, DPS or result score.',damageCalculated:false});
   return {supported:true,values,actorIds:values.map(v=>v.actorId)};
  }catch(error){emit({status:'original_native_weapon_input_index_unsupported',tick,error:String(error)});return {supported:false,error:String(error)};}
 }
 return {read};
}
