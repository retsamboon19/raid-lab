// Passive original153 core collider reader. No hooks, RNG or native writes.
function createKraken153CoreObserver(runtime,management,pin,emit,waveId,configuration={}) {
  if(waveId!==6302009&&!(typeof mechanicsInterceptionPolicy==='function'&&mechanicsInterceptionPolicy(waveId)))return {snapshot:()=>({supported:true,targets:[]}),summary:()=>({enabled:false})};
  const game=Process.getModuleByName('GameAssembly.dll');
  const klass=n=>runtime.class('NK.Spot.'+n);
  const unity=Il2Cpp.domain.assembly('UnityEngine.CoreModule').image;
  const physics=Il2Cpp.domain.assembly('UnityEngine.PhysicsModule').image;
  const monster=klass('Model.Monster.SpotMonster'),prefab=klass('Monster.MonsterPrefabData');
  const parts=klass('Monster.Body.MonsterPartsPrefabData'),data=klass('Monster.Body.MonsterColliderData');
  const partsModel=klass('Model.Monster.SpotMonsterPartsData');
  const contextType=klass('Context.Monster.MonsterContext');
  const field=(c,n,t,o)=>{const f=c.field(n);if(f.offset!==o||f.type.name!==t||f.isStatic)throw Error('Original core field changed: '+n);};
  for(const [c,n,t,o] of [
    [monster,'<PrefabData>k__BackingField','NK.Spot.Monster.MonsterPrefabData',120],
    [monster,'<PartsData>k__BackingField','NK.Spot.Model.Monster.SpotMonsterPartsData',144],
    [partsModel,'MainPartType','NK.StaticData.PartsType',24],
    [prefab,'<CurrentPhase>k__BackingField','System.Int32',104],
    [prefab,'<PartsData>k__BackingField','NK.Spot.Monster.Body.MonsterPartsPrefabData',216],
    [parts,'_coreColliderDatas','System.Collections.Generic.List<NK.Spot.Monster.Body.MonsterColliderData>',96],
    [data,'PartsType','NK.StaticData.PartsType',20],[data,'Collider','UnityEngine.Collider',24],
    [data,'colliderId','System.Int32',32],
    [unity.class('UnityEngine.Bounds'),'m_Center','UnityEngine.Vector3',16],
    [unity.class('UnityEngine.Bounds'),'m_Extents','UnityEngine.Vector3',28]])field(c,n,t,o);
  const method=(c,n,rva,returns)=>{const m=c.method(n,0);if(!m.virtualAddress.equals(game.base.add(rva))||m.returnType.name!==returns||m.isStatic||m.parameters.length)throw Error('Original core getter changed: '+n);return m;};
  if(waveId===6302006)field(parts,'_colliderDatas','System.Collections.Generic.List<NK.Spot.Monster.Body.MonsterColliderData>',32);
  const hasCore=method(monster,'HasActiveCore',106657280,'System.Boolean');
  const isCore=method(data,'get_IsCore',105438032,'System.Boolean');
  const disabled=method(data,'get_IsColliderPermanentlyDisabled',63128784,'System.Boolean');
  const enabled=method(physics.class('UnityEngine.Collider'),'get_enabled',0x08590D20,'System.Boolean');
  const bounds=method(physics.class('UnityEngine.Collider'),'get_bounds',0x08590C80,'UnityEngine.Bounds');
  const valid=unity.class('UnityEngine.Object').method('op_Implicit',1);
  requireKraken153Method(valid,0x085236E0);
  const call=(m,self,args=[])=>invokeChecked(m,self,args);
  const live=x=>x!=null&&!x.isNull();
  const bool=(m,self,args=[])=>call(m,self,args).unbox().handle.readU8()!==0;
  const contexts=management.field('_contexts').value;
  const context=pin(call(contexts.method('get_Item',1),contexts,[contextType.type.object.handle]));
  if(!live(context))throw Error('Original core MonsterContext missing');
  const list=value=>{
    if(!live(value))return [];
    field(value.class,'_size','System.Int32',24);
    const itemsField=value.class.field('_items');
    if(itemsField.offset!==16||itemsField.isStatic)throw Error('Original core List backing field changed');
    const n=Number(value.field('_size').value),items=value.field('_items').value;
    if(!Number.isSafeInteger(n)||n<0||n>256)throw Error('Original core list outside bound');
    if(n===0)return [];
    if(!live(items))throw Error('Original core List backing array missing');
    const array=new Il2Cpp.Array(items.handle);
    if(array.length<n)throw Error('Original core List exceeds backing array');
    const out=[];for(let i=0;i<n;i++)out.push(array.get(i));return out;
  };
  const enumInt=x=>typeof x==='number'?x:Number(x.field('value__').value);
  let samples=0,coreSamples=0,lastSignature=null,last=null,invalidMirrorBounds=0,geometryRefreshes=0;
  const invalidMirrorColliderIds=new Set();
  function snapshot(targetMonsterId,refreshGeometry=false) {
    const geometryOnly=waveId===6302006&&refreshGeometry===true;
    const nativeGeometryTick=Number(management.field('_tickCount').value);
    const owner=list(context.field('_monsters').value).find(x=>live(x)&&Number(x.field('Id').value)===targetMonsterId);
    if(!owner)return {supported:true,targets:[],phase:null,nativeHasActiveCore:false};
    const model=owner.field('<PrefabData>k__BackingField').value;
    if(!live(model))return {supported:false,targets:[],reason:'native_prefab_unavailable'};
    const phase=Number(model.field('<CurrentPhase>k__BackingField').value);
    if(!Number.isSafeInteger(phase)||phase<0||phase>256)throw Error('Original native CurrentPhase outside bound');
    const body=model.field('<PartsData>k__BackingField').value;
    const nativeParts=owner.field('<PartsData>k__BackingField').value;
    if(!live(nativeParts))return {supported:false,targets:[],phase,reason:'native_parts_model_unavailable'};
    const nativeMainPartType=enumInt(nativeParts.field('MainPartType').value);
    const nativeHasActiveCore=bool(hasCore,owner),targets=[],partTargets=[];
    if(live(body)&&nativeHasActiveCore)for(const row of list(body.field('_coreColliderDatas').value)) {
      if(!live(row))continue;
      if(row.class.type.name!==data.type.name)throw Error('Original core collider data type changed');
      if(!bool(isCore,row)||bool(disabled,row))continue;
      const collider=row.field('Collider').value;
      if(!live(collider)||!bool(valid,null,[collider.handle])||!bool(enabled,collider))continue;
      const p=call(bounds,collider).unbox().handle;
      const world=[p.readFloat(),p.add(4).readFloat(),p.add(8).readFloat()];
      const extents=[p.add(12).readFloat(),p.add(16).readFloat(),p.add(20).readFloat()];
      if(!world.every(Number.isFinite)||!extents.every(Number.isFinite))throw Error('Original core bounds non-finite');
      // Unity gives empty bounds for inactive GameObjects. Never target those.
      if(!extents.every(x=>x>0))continue;
      const colliderId=Number(row.field('colliderId').value),partsType=enumInt(row.field('PartsType').value);
      const edge=waveId===6302006&&typeof configuration.visibleCorePoint==='function'?
        configuration.visibleCorePoint(collider,world,extents):null;
      targets.push({key:'core:'+targetMonsterId+':'+colliderId,kind:'Core',ownerId:targetMonsterId,
        colliderId,partsType,world:edge?edge.world:world,nativeIsCore:true,nativeHasActiveCore:true,nativeMainPart:partsType===nativeMainPartType,
        ...(edge?{nativeColliderRaycastConfirmed:true,aimPointSource:edge.source}:{}),
        ...(waveId===6302006?{nativeCoreBoundsCenter:world,nativeCoreBoundsExtents:extents}:{}),
        nativePhase:phase,nativeGeometryTick,unsafePresent:false});
    }
    if(geometryOnly) {
      geometryRefreshes++;
      return {supported:true,phase,nativeMainPartType,nativeHasActiveCore,targets,
        partTargets:last?.partTargets||[],nativeGeometryTick,coreGeometryOnly:true};
    }
    // Mirror needs actual enabled hit collider bounds; generic visual HitPoint
    // transforms are insufficient during authored slipper movement/exposure.
    if(waveId===6302006&&configuration.observePartColliders!==false&&live(body))for(const row of list(body.field('_colliderDatas').value)) {
      if(!live(row))continue;
      if(row.class.type.name!==data.type.name)throw Error('Original Mirror collider data type changed');
      if(bool(disabled,row))continue;
      const collider=row.field('Collider').value;
      if(!live(collider)||!bool(valid,null,[collider.handle])||!bool(enabled,collider))continue;
      const p=call(bounds,collider).unbox().handle;
      const world=[p.readFloat(),p.add(4).readFloat(),p.add(8).readFloat()];
      const extents=[p.add(12).readFloat(),p.add(16).readFloat(),p.add(20).readFloat()];
      if(!world.every(Number.isFinite)||!extents.every(Number.isFinite)) {
        invalidMirrorBounds++;const badId=Number(row.field('colliderId').value);
        if(!invalidMirrorColliderIds.has(badId)&&invalidMirrorColliderIds.size<32){invalidMirrorColliderIds.add(badId);emit({status:'original_mirror_collider_skipped',colliderId:badId,reason:'native_bounds_nonfinite',readsOnly:true});}
        continue;
      }
      if(!extents.every(x=>x>0))continue;
      const colliderId=Number(row.field('colliderId').value),partsType=enumInt(row.field('PartsType').value);
      partTargets.push({key:'part:'+targetMonsterId+':'+partsType,kind:'Part',ownerId:targetMonsterId,
        colliderId,partsType,world,extents,nativeColliderLive:true,nativeColliderEnabled:true,nativePartCollider:true,unsafePresent:false});
    }
    samples++;if(targets.length)coreSamples++;
    last={supported:true,phase,nativeMainPartType,nativeHasActiveCore,targets,partTargets};
    const signature=JSON.stringify([phase,nativeHasActiveCore,targets.map(t=>[t.colliderId,t.partsType])]);
    if(signature!==lastSignature){lastSignature=signature;emit({status:'original_kraken_core_state',tick:Number(management.field('_tickCount').value),nativePlaytime:Number(management.field('_playtime').value),...last,readsOnly:true});}
    return last;
  }
  // Passive query of CURRENT original core geometry only; never updates the
  // control snapshot, geometry counters, aim or any native object.
  function inspectProjectileRay(targetMonsterId,start,target,query) {
    if(waveId!==6302006||!Number.isSafeInteger(targetMonsterId))return {supported:false,reason:'no_source_bound_Mirror_core_owner'};
    const owner=list(context.field('_monsters').value).find(x=>live(x)&&Number(x.field('Id').value)===targetMonsterId);
    if(!owner)return {supported:false,reason:'native_boss_owner_absent'};
    const model=owner.field('<PrefabData>k__BackingField').value;
    if(!live(model))return {supported:false,reason:'native_prefab_absent'};
    const body=model.field('<PartsData>k__BackingField').value;
    const active=bool(hasCore,owner),out=[];
    if(live(body)&&active)for(const row of list(body.field('_coreColliderDatas').value)) {
      if(!live(row)||row.class.type.name!==data.type.name)throw Error('Passive current core data type changed');
      if(!bool(isCore,row)||bool(disabled,row))continue;
      const collider=row.field('Collider').value;
      if(!live(collider)||!bool(valid,null,[collider.handle])||!bool(enabled,collider))continue;
      const p=call(bounds,collider).unbox().handle;
      const center=[p.readFloat(),p.add(4).readFloat(),p.add(8).readFloat()];
      const extents=[p.add(12).readFloat(),p.add(16).readFloat(),p.add(20).readFloat()];
      if(!center.every(Number.isFinite)||!extents.every(v=>Number.isFinite(v)&&v>0))continue;
      out.push({colliderId:Number(row.field('colliderId').value),partsType:enumInt(row.field('PartsType').value),
        originalBounds:{center,extents},rayQuery:query(collider,start,target)});
    }
    return {supported:true,ownerId:targetMonsterId,nativeHasActiveCore:active,
      phase:Number(model.field('<CurrentPhase>k__BackingField').value),
      nativeGeometryTick:Number(management.field('_tickCount').value),cores:out,
      intersectionDoesNotProveActualDamageOrUnoccludedTrajectory:true};
  }
  return {snapshot,inspectProjectileRay,summary:()=>({observePartColliders:waveId===6302006&&configuration.observePartColliders!==false,samples,coreSamples,geometryRefreshes,last,invalidMirrorBounds,invalidMirrorColliderIds:[...invalidMirrorColliderIds],readsOnly:true})};
}
