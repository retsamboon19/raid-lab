// Read-only original153 enemy projectile/mob collider reader. No native writes.
// Exact new ABI roots: metadata/current153-interception-projectile-targets1/2.
function createMechanicsInterceptionThreatTargets(runtime,management,pin,emit,waveId) {
  const descriptor=mechanicsInterceptionPolicy(waveId);
  if(!descriptor||waveId===6302009)return {snapshot:()=>({supported:true,targets:[],modernia:null}),summary:()=>({enabled:false})};
  const game=Process.getModuleByName('GameAssembly.dll'),live=x=>x!=null&&!x.isNull();
  const c=n=>runtime.class('NK.Spot.'+n),call=(m,self,args=[])=>invokeChecked(m,self,args);
  const field=(k,n,t,o)=>{const f=k.field(n);if(f.offset!==o||f.type.name!==t||f.isStatic)throw Error('Original interception target field changed: '+n);};
  const method=(k,n,rva,t)=>{const m=k.method(n,0);if(m.isStatic||m.parameters.length||m.returnType.name!==t||!m.virtualAddress.equals(game.base.add(rva)))throw Error('Original interception target method changed: '+n);return m;};
  const projectile=c('Model.Projectile.SpotProjectile'),projectileData=c('Weapon.Projectile.SpotProjectileData');
  const entity=c('Model.Common.SpotEntity'),status=c('Model.Common.SpotEntityStatus');
  const summon=c('Model.Summon.SpotSummon');
  field(summon,'<Owner>k__BackingField','NK.Spot.Model.Common.SpotEntity',104);
  const monster=c('Model.Monster.SpotMonster'),prefab=c('Monster.MonsterPrefabData'),body=c('Monster.Body.MonsterPartsPrefabData'),colliderData=c('Monster.Body.MonsterColliderData');
  const part=c('Model.Monster.SpotMonsterPartsData').nested('PartsData');
  const monsterContextType=c('Context.Monster.MonsterContext'),projectileContextType=c('ProjectileContext');
  for(const [k,n,t,o] of [
    [projectile,'<Data>k__BackingField','NK.Spot.Weapon.Projectile.SpotProjectileData',104],
    [projectile,'_collider','UnityEngine.BoxCollider',152],
    [projectile,'_isDespawn','System.Boolean',184],[projectile,'<IsDestroy>k__BackingField','System.Boolean',192],
    [projectileData,'<IsDestroyable>k__BackingField','System.Boolean',668],
    [projectileData,'<Owner>k__BackingField','NK.Spot.Model.Common.SpotEntity',72],
    [entity,'Id','System.Int32',16],[entity,'<CurrentStatus>k__BackingField','NK.Spot.Model.Common.SpotEntityStatus',48],
    [projectileContextType,'_projectileList','System.Collections.Generic.List<NK.Spot.Model.Projectile.SpotProjectile>',16],
    [monsterContextType,'_monsters','System.Collections.Generic.List<NK.Spot.Model.Monster.SpotMonster>',16],
    [monsterContextType,'_allMonsterParts','System.Collections.Generic.List<NK.Spot.Model.Monster.SpotMonsterPartsData.PartsData>',40],
    [monster,'<PrefabData>k__BackingField','NK.Spot.Monster.MonsterPrefabData',120],
    [prefab,'<PartsData>k__BackingField','NK.Spot.Monster.Body.MonsterPartsPrefabData',216],
    [body,'_colliderDatas','System.Collections.Generic.List<NK.Spot.Monster.Body.MonsterColliderData>',32],
    [colliderData,'Collider','UnityEngine.Collider',24],
    [part,'PartsType','NK.StaticData.PartsType',24],[part,'<Owner>k__BackingField','NK.Spot.Model.Monster.SpotMonster',48],
    [part,'<IsDestroyed>k__BackingField','System.Boolean',60]])field(k,n,t,o);
  const physics=Il2Cpp.domain.assembly('UnityEngine.PhysicsModule').image;
  const unity=Il2Cpp.domain.assembly('UnityEngine.CoreModule').image;
  const enabled=method(physics.class('UnityEngine.Collider'),'get_enabled',0x08590D20,'System.Boolean');
  const bounds=method(physics.class('UnityEngine.Collider'),'get_bounds',0x08590C80,'UnityEngine.Bounds');
  const disabled=method(colliderData,'get_IsColliderPermanentlyDisabled',63128784,'System.Boolean');
  const getHp=method(status,'get_HP',0x066E0D50,'NK.Common.StatValue');
  const valid=unity.class('UnityEngine.Object').method('op_Implicit',1);
  if(!valid.isStatic||!valid.virtualAddress.equals(game.base.add(0x085236E0)))throw Error('Original Unity lifetime guard changed');
  const bool=(m,self,args=[])=>call(m,self,args).unbox().handle.readU8()!==0;
  const list=x=>{if(!live(x))return [];const sf=x.class.field('_size'),af=x.class.field('_items');if(sf.offset!==24||sf.type.name!=='System.Int32'||af.offset!==16)throw Error('Original target list layout changed');const n=Number(x.field('_size').value);if(!Number.isSafeInteger(n)||n<0||n>8192)throw Error('Original target list bound exceeded');if(!n)return [];const items=x.field('_items').value;if(!live(items))throw Error('Original target list missing backing');const a=new Il2Cpp.Array(items.handle);if(a.length<n)throw Error('Original target array short');return Array.from({length:n},(_,i)=>a.get(i));};
  const contexts=management.field('_contexts').value;
  const context=k=>pin(call(contexts.method('get_Item',1),contexts,[k.type.object.handle]));
  const pc=context(projectileContextType),mc=context(monsterContextType);
  if(!live(pc)||!live(mc))throw Error('Original enemy target contexts missing');
  const hp=x=>{const s=x.field('<CurrentStatus>k__BackingField').value;return live(s)?call(getHp,s).unbox().handle.readS64().toString():null;};
  const positive=x=>typeof x==='string'&&/^\d+$/.test(x)&&BigInt(x)>0n;
  function colliderBounds(x){
    if(!live(x)||!bool(valid,null,[x.handle])||!bool(enabled,x))return null;
    const p=call(bounds,x).unbox().handle;
    const world=[p.readFloat(),p.add(4).readFloat(),p.add(8).readFloat()];
    const extents=[p.add(12).readFloat(),p.add(16).readFloat(),p.add(20).readFloat()];
    if(!world.every(Number.isFinite)||!extents.every(Number.isFinite))throw Error('Original target bounds nonfinite');
    return extents.every(v=>v>0)?{world,extents}:null;
  }
  const enumInt=x=>typeof x==='number'?x:Number(x.field('value__').value);
  let samples=0,projectileSamples=0,mobSamples=0,last=null;
  function snapshot(observation){
    if(!observation||!Array.isArray(observation.monsters))throw Error('Original enemy identities required');
    const identities=new Map(observation.monsters.map(m=>[m.entityId,m]));
    const bosses=new Set(observation.monsters.filter(m=>String(m.tableId)===String(descriptor.monsterId)).map(m=>m.entityId));
    const targets=[],friendlyProjectiles=[];let modernia=null;
    const squadIds=new Set((observation.squad?.characters||[]).map(a=>a.id));
    for(const x of list(pc.field('_projectileList').value)){
      if(!live(x)||x.class.type.name!==projectile.type.name)continue;
      if(x.field('_isDespawn').value||x.field('<IsDestroy>k__BackingField').value)continue;
      const d=x.field('<Data>k__BackingField').value;
      if(!live(d))continue;
      const owner=d.field('<Owner>k__BackingField').value;
      let friendlyOwner=owner;
      if(live(owner)&&owner.class.type.name.includes('.Summon.')){const sourceOwner=owner.field('<Owner>k__BackingField').value;if(live(sourceOwner))friendlyOwner=sourceOwner;}
      if(live(friendlyOwner)&&squadIds.has(Number(friendlyOwner.field('Id').value))){friendlyProjectiles.push({entityId:Number(x.field('Id').value),ownerId:Number(friendlyOwner.field('Id').value),nativeDespawn:false,nativeDestroyed:false});continue;}
      if(d.field('<IsDestroyable>k__BackingField').value!==true)continue;
      if(!live(owner)||owner.class.type.name!==monster.type.name||!identities.has(Number(owner.field('Id').value)))continue;
      const health=hp(x),b=colliderBounds(x.field('_collider').value);
      if(!positive(health)||!b)continue;
      const id=Number(x.field('Id').value);
      targets.push({key:'projectile:'+id,kind:'Projectile',ownerId:Number(owner.field('Id').value),entityId:id,hp:health,...b,nativeDestructible:true,nativeColliderLive:true,unsafePresent:false});
    }
    for(const x of list(mc.field('_monsters').value)){
      if(!live(x)||x.class.type.name!==monster.type.name)continue;
      const id=Number(x.field('Id').value),identity=identities.get(id);
      if(!identity)continue;
      if(bosses.has(id)){
        if(waveId===6302005){
          const destroyedParts=list(mc.field('_allMonsterParts').value).filter(p=>live(p)&&p.field('<Owner>k__BackingField').value.handle.equals(x.handle)&&p.field('<IsDestroyed>k__BackingField').value===true).map(p=>enumInt(p.field('PartsType').value));
          modernia={supported:true,ownerId:id,monsterTableId:descriptor.monsterId,destroyedParts};
        }
        continue;
      }
      const health=hp(x);if(!positive(health))continue;
      const model=x.field('<PrefabData>k__BackingField').value;if(!live(model))continue;
      const b=model.field('<PartsData>k__BackingField').value;if(!live(b))continue;
      const candidates=list(b.field('_colliderDatas').value).filter(d=>live(d)&&!bool(disabled,d)).map(d=>colliderBounds(d.field('Collider').value)).filter(Boolean);
      if(!candidates.length)continue;
      const target=candidates.reduce((a,b)=>a.extents.reduce((v,n)=>v*n,1)>=b.extents.reduce((v,n)=>v*n,1)?a:b);
      targets.push({key:'mob:'+id,kind:'Mob',ownerId:id,entityId:id,monsterTableId:identity.tableId,hp:health,...target,nativeColliderLive:true,unsafePresent:false});
    }
    samples++;projectileSamples+=targets.filter(t=>t.kind==='Projectile').length;mobSamples+=targets.filter(t=>t.kind==='Mob').length;
    last={supported:true,targets,friendlyProjectiles,modernia};return last;
  }
  emit({status:'original_interception_threat_targets_ready',waveId,readsOnly:true,nativeBehaviorValidated:false});
  return {snapshot,summary:()=>({samples,projectileSamples,mobSamples,last,readsOnly:true})};
}

// Original live projectile identities only; no projectile removal or prediction.
function createMechanicsKrakenFriendlyProjectiles(runtime,management,pin,enabled) {
 if(!enabled)return {snapshot:()=>null,summary:()=>({enabled:false})};
 const c=n=>runtime.class('NK.Spot.'+n),live=x=>x!=null&&!x.isNull();
 const pcType=c('ProjectileContext'),projectile=c('Model.Projectile.SpotProjectile');
 const dataType=c('Weapon.Projectile.SpotProjectileData'),entity=c('Model.Common.SpotEntity'),summon=c('Model.Summon.SpotSummon');
 const field=(k,n,o,t)=>{const f=k.field(n);if(f.isStatic||f.offset!==o||f.type.name!==t)throw Error('Original friendly projectile field differs: '+n);return f;};
 field(management.class,'_contexts',32,'System.Collections.Generic.Dictionary<System.Type,NK.Spot.Interface.IContextBase>');
 for(const [k,n,o,t]of [[pcType,'_projectileList',16,'System.Collections.Generic.List<NK.Spot.Model.Projectile.SpotProjectile>'],[pcType,'_addList',56,'System.Collections.Generic.List<NK.Spot.Model.Projectile.SpotProjectile>'],
  [projectile,'Id',16,'System.Int32'],[projectile,'<Data>k__BackingField',104,dataType.type.name],
  [projectile,'_isDespawn',184,'System.Boolean'],[projectile,'<IsDestroy>k__BackingField',192,'System.Boolean'],
  [dataType,'<Owner>k__BackingField',72,entity.type.name],[entity,'Id',16,'System.Int32'],[summon,'<Owner>k__BackingField',104,entity.type.name]])field(k,n,o,t);
 const contexts=management.field('_contexts').value;if(!live(contexts))throw Error('Original friendly projectile contexts missing');
 const pc=pin(invokeChecked(contexts.method('get_Item',1),contexts,[pcType.type.object.handle]));
 if(!live(pc)||pc.class.type.name!==pcType.type.name)throw Error('Original friendly ProjectileContext missing');
 let samples=0,last=null;
 function list(value){
  if(!live(value))throw Error('Original friendly projectile list missing');
  const size=field(value.class,'_size',24,'System.Int32'),items=field(value.class,'_items',16,'NK.Spot.Model.Projectile.SpotProjectile[]');
  const count=Number(value.field(size.name).value);if(!Number.isSafeInteger(count)||count<0||count>8192)throw Error('Original friendly projectile list bound');
  if(!count)return[];
  const backing=value.field(items.name).value;if(!live(backing))throw Error('Original friendly projectile backing missing');
  const array=new Il2Cpp.Array(backing.handle);if(array.length<count)throw Error('Original friendly projectile array short');
  return Array.from({length:count},(_,i)=>array.get(i));
 }
 function snapshot(tick,squad){
  samples++;if(!Number.isSafeInteger(tick)||!Array.isArray(squad?.characters))throw Error('Original friendly projectile snapshot needs current squad');
  const ids=new Set(squad.characters.map(a=>a.id)),found=new Map();let unknown=null;
  for(const name of ['_projectileList','_addList'])for(const p of list(pc.field(name).value)){
   if(!live(p))continue;
   if(p.class.type.name!==projectile.type.name)throw Error('Original friendly projectile class differs');
   if(p.field('_isDespawn').value===true||p.field('<IsDestroy>k__BackingField').value===true)continue;
   const id=Number(p.field('Id').value);if(!Number.isSafeInteger(id)||id<=0)throw Error('Original friendly projectile id invalid');
   const prior=found.get(id);if(prior){if(!prior.handle.equals(p.handle))throw Error('Original friendly projectile identity collision');prior.locations.push(name);continue;}
   const data=p.field('<Data>k__BackingField').value;
   if(!live(data)){unknown='native_projectile_data_pending';continue;}
   if(mechanicsOriginalProjectileDataClassChain(data.class,dataType).supported!==true)throw Error('Original friendly projectile data ancestry differs');
   field(data.class,'<Owner>k__BackingField',72,entity.type.name);
   let owner=data.field('<Owner>k__BackingField').value;
   if(!live(owner)){unknown='native_projectile_owner_pending';continue;}
   if(mechanicsOriginalProjectileDataClassChain(owner.class,summon).supported===true){
    field(owner.class,'<Owner>k__BackingField',104,entity.type.name);owner=owner.field('<Owner>k__BackingField').value;
    if(!live(owner)){unknown='native_summon_owner_pending';continue;}
   }
   field(owner.class,'Id',16,'System.Int32');const ownerId=Number(owner.field('Id').value);
   if(!Number.isSafeInteger(ownerId)||ownerId<=0)throw Error('Original friendly owner id invalid');
   if(ids.has(ownerId))found.set(id,{handle:p.handle,entityId:id,ownerId,locations:[name],nativeDespawn:false,nativeDestroyed:false});
  }
  last={supported:unknown===null,tick,reason:unknown,projectiles:unknown===null?[...found.values()].map(({handle,...row})=>row):null,listsRead:['_projectileList','_addList']};
  return last;
 }
 return {snapshot,summary:()=>({enabled:true,samples,last,readsOnly:true})};
}
