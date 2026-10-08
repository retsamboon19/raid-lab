// Passive original-event trace for the fixed five-unit Intercept fixture.
// Call observeSendEvent(event) from the existing SendEventDefault onEnter hook.
// It reads the event before original dispatch, never changes it or combat state.
function installMechanicsDamageTrace(runtime, management, emit) {
  if (typeof emit!=="function") throw new Error("Damage trace needs an evidence callback");
  if (Number(management.method("SendEventDefault",1).relativeVirtualAddress)!==0x0614baf0)
    throw new Error("Installed SendEventDefault does not match damage trace contract");
  const sourceId=mechanicsRequestedEntityId(5099);
  const maxRecords=5000;
  let records=0;
  const present=value=>value!=null && !value.isNull();
  const eventTypes=new Map([
    ["NK.Spot.Event.Common.OnEntityGetDamageEvent","OnEntityGetDamage"],
    ["NK.Spot.Event.Common.StatisticsGetDamageEvent","StatisticsTakeDamage"],
    ["NK.Spot.Event.Common.DamageLogEvent","DamageLog"]
  ]);
  const stat=(event,name)=>event.field(name).value.field("Value").value.toString();
  const entityId=(info,name)=>{
    if (!present(info)) throw new Error("Original "+name+" SpotEntityInfo is null");
    return Number(info.field("EntityID").value);
  };
  const bool=(object,name)=>Boolean(object.field(name).value);
  const emitRecord=row=>{
    if (records>=maxRecords) throw new Error("Original Naga damage trace exceeded "+maxRecords+" records");
    records++;
    emit({status:"original_naga_damage_event",ordinal:records,...row});
  };
  function observeSendEvent(event) {
    if (!present(event)) return;
    const type=event.class.type.name;
    const sourceEventName=eventTypes.get(type);
    if (!sourceEventName) return;
    const casterInfo=event.field("CasterInfo").value;
    // Environmental damage can have no caster; it cannot be Naga's hit.
    if (!present(casterInfo)) return;
    const casterId=entityId(casterInfo,"caster");
    if (casterId!==sourceId) return;
    const targetId=entityId(event.field("TargetInfo").value,"target");
    const row={sourceEventName,tick:Number(management.field("_tickCount").value),
      playTime:Number(management.field("_playtime").value),
      casterId,targetId,damage:stat(event,"Damage"),
      actualDamage:stat(event,"ActualDamage")};
    if (type==="NK.Spot.Event.Common.OnEntityGetDamageEvent") {
      row.targetSubId=Number(event.field("TargetSubID").value);
      row.damageType=Number(event.field("DamageType").value.field("value__").value);
      row.critical=bool(event,"IsCritical");
      row.immune=bool(event,"IsImmune");
      row.shared=bool(event,"IsShare");
    } else if (type==="NK.Spot.Event.Common.DamageLogEvent") {
      const status=event.field("_damageStatusInfo").value;
      row.critical=bool(status,"IsCritical");
      row.core=bool(status,"IsCore");
      row.colliderId=Number(status.field("ColliderId").value);
      row.penetration=bool(status,"IsPenetration");
      row.damageType=Number(event.field("DamageType").value.field("value__").value);
    }
    emitRecord(row);
  }
  return {observeSendEvent,getRecordCount:()=>records};
}
