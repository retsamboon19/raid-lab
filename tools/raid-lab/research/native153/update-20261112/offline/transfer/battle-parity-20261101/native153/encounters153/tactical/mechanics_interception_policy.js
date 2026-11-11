// Original153 input policy only. Source receipt: interception-policy-source153.json.
// No combat/stat/RNG writes. All targets still require original live/HP/projection gates.
const MECHANICS_INTERCEPTION_PROFILES = Object.freeze({
  6302001:{boss:'Alteisen',monsterId:3520010133,priorityNames:['Weapon_05','Weapon_06','Weapon_01','Weapon_02','Weapon_03','Weapon_04'],avoidNames:['Weapon_07','Weapon_08'],limitations:['Only original destructible projectiles can be intercepted; green indestructible missiles remain native mechanics']},
  6302002:{boss:'Gravedigger',monsterId:3520020143,priorityNames:[],avoidNames:[],limitations:['Failed-interruption piercing drill is never a defensive cover trigger']},
  6302003:{boss:'Blacksmith',monsterId:1520030113,priorityNames:['Arm_Left','Arm_Right'],avoidNames:[],limitations:['Native bomb interception enabled; rifle cast impact is not source-bound for cover']},
  6302004:{boss:'Chatterbox',monsterId:1520020113,priorityNames:['Weapon_01','Weapon_02'],avoidNames:['Weapon_03'],avoidCore:true,limitations:['Cover-piercing shockwave is never a cover trigger']},
  6302005:{boss:'Modernia',monsterId:3520040153,priorityNames:['Weapon_03'],avoidNames:[],wingNames:['Weapon_01','Weapon_02'],coreName:'Weapon_03',limitations:['Original auto teammates can cause collateral wing destruction','Native core laser cover uses extracted loop-end and attack markers']},
  6302006:{boss:'Mirror Container',monsterId:4510010123,requiredElement:400001,priorityNames:[],avoidNames:['Weapon_01','Weapon_02','Weapon_03','Weapon_04','Weapon_05','Weapon_06','Weapon_07','Weapon_08','Weapon_09','Weapon_10'],limitations:['Native Anis: Star kit selects core pressure without slipper suppression; other kits retain original charged coordination','Native gray-QTE teammate Idle/autoburst isolation is input-only; airborne projectiles are never removed']},
  6302007:{boss:'Indivilia',monsterId:2520130133,requiredElement:100001,priorityNames:['Weapon_03'],avoidNames:['Weapon_01','Weapon_02'],limitations:['Tail is prioritized whenever live; no guessed charge timer','Tail/transform piercing attacks never trigger cover; authored nonpiercing major attacks are handled separately']},
  6302008:{boss:'Ultra',monsterId:1520460146,requiredElement:500001,priorityNames:[],avoidNames:[],limitations:['Phase-one centerline uses original persistent HitPoint after core destruction, never claims an active core collider','Owned live barriers on every living actor can skip authored shockwave/poison cover; unknown retains cover']},
  6302009:{boss:'Kraken',monsterId:1520040153,requiredElement:300001,priorityNames:[],avoidNames:[],limitations:[]},
  6302010:{boss:'Harvester',monsterId:1520010113,requiredElement:200001,priorityNames:['Head'],avoidNames:[],limitations:['Original Shot05 timeline laser plus targeted Shot01/02 primary-branch cover; parallel summon nodes cannot end protection; piercing attacks excluded']}
});
function mechanicsInterceptionPolicy(waveId,runtime) {
  const source=MECHANICS_INTERCEPTION_PROFILES[waveId];if(!source)return null;
  const descriptor={...source,waveId,objective:'maximum_damage',nativeBehaviorValidated:false};
  if(runtime) {
    const type=Il2Cpp.domain.assembly('NK.Runtime.StaticData').image.class('NK.StaticData.PartsType');
    const read=name=>{const v=type.field(name).value;const n=typeof v==='number'?v:Number(v.field('value__').value);if(!Number.isSafeInteger(n))throw Error('Original interception PartsType unavailable: '+name);return n;};
    descriptor.priorityParts=source.priorityNames.map(read);descriptor.avoidParts=source.avoidNames.map(read);
    if(source.wingNames){descriptor.wingParts=source.wingNames.map(read);descriptor.corePart=read(source.coreName);}
  }
  return descriptor;
}
function mechanicsInterceptionRequiredElement(waveId) {return MECHANICS_INTERCEPTION_PROFILES[waveId]?.requiredElement||null;}
function mechanicsInterceptionFilterTargets(targets,descriptor,core) {
  if(!descriptor||descriptor.waveId===6302009)return targets;
  if(!Array.isArray(descriptor.avoidParts))throw Error('Original interception enum binding required');
  return targets.filter(t=>t.kind==='Break'||(!descriptor.avoidParts.includes(t.partsType)&&!(descriptor.avoidCore&&t.kind==='Core')));
}
function mechanicsInterceptionPartRank(target,context,descriptor) {
  if(target.kind==='Break')return -100;
  if(target.kind==='Projectile') {
    if(descriptor?.waveId===6302006&&[1,2].includes(context.phase)&&Array.isArray(context.coreFirstMissileIds)&&
        context.coreFirstMissileIds.includes(target.entityId))return 1;
    return -90;
  }
  if(target.kind==='Mob') {
    // Only Harvester's not-yet-attacking mobs yield to its head/exposed core.
    // Unknown observation preserves the prior defensive priority.
    const observed=context.attackingMobIds;
    if(descriptor?.waveId===6302010&&Array.isArray(observed)&&
        Number.isSafeInteger(target.entityId)&&target.entityId>0&&
        !observed.includes(target.entityId))return 1;
    return -80;
  }
  const index=(descriptor?.priorityParts||[]).indexOf(target.partsType);
  if(index>=0)return -20+index;
  if(target.kind==='Core'&&target.nativeIsCore===true)return 0;
  if(descriptor?.waveId===6302008&&context.phase===1&&target.kind==='AimAnchor'&&target.source==='original_persistent_HitPoint_transform'&&target.claimsActiveCollider===false)return 1;
  return target.nativeMainPart===true?1:2;
}
function mechanicsInterceptionProjectileCoverWanted(waveId,observation,threat) {
  // Native threat schema does not expose a verified cover-piercing classification
  // or time-to-impact. Covering every projectile costs damage and can be useless.
  // Source-bound per-boss timeline rules handle only identified large attacks.
  return false;
}

// Bounds come from original timeline markers, never battle/video elapsed time.
function mechanicsInterceptionTimelineRules(waveId) {
  const rows={
    6302004:[{ruleId:'chatterbox-native-shot09-dash',monsterId:1520020113,clip:'bbg002_shot_09_dashattack',skillId:510209,coverStart:1.9333333333333333,attackMarker:2.283333333333333}],
    6302005:[{ruleId:'modernia-native-shot05-laser',monsterId:3520040153,clip:'mbg004_shot_05_laser',skillId:530405,coverStart:1.2,attackMarker:3.6166666666666667}],
    6302008:[{ruleId:'ultra-native-shot01-shockwave',monsterId:1520460146,clip:'bbg006_skill_01',skillId:510634,coverStart:2.3333333333333335,attackMarker:3.8666666666666667},
      {ruleId:'ultra-native-shot02-poison',monsterId:1520460146,clip:'bbg006_skill_02',skillId:510635,coverStart:2.8333333333333335,attackMarker:5.8666666666666645}],
    6302010:[{ruleId:'harvester-native-shot05-laser',monsterId:1520010113,clip:'bbg001_shot_05_laser',skillId:510131,coverStart:4.966666666666667,attackMarker:6.383333333333333}]
  };
  return (rows[waveId]||[]).map(row=>({...row,coverable:true,coverPiercing:false,source:'interception-cover-source153.json; nonkraken-timeline-source-20261104.json',nativeProtectionVerified:false}));
}

// One native destroyed wing is sufficient: retain the other wing for the rest
// of this battle. Absence from an active-parts list is never destruction proof.
function createMechanicsModerniaWingPolicy(descriptor) {
  let chosenWing=null,wingDestroyed=false,bossId=null;
  return {filter(targets,state) {
    if(descriptor?.waveId!==6302005)return targets;
    if(!state||state.supported!==true||!Array.isArray(state.destroyedParts)||
       state.monsterTableId!==descriptor.monsterId)return targets.filter(t=>!descriptor.wingParts.includes(t.partsType));
    if(bossId===null)bossId=state.ownerId;
    if(state.ownerId!==bossId)throw Error('Original Modernia entity identity changed');
    if(state.destroyedParts.some(p=>descriptor.wingParts.includes(p)))wingDestroyed=true;
    if(wingDestroyed)return targets.filter(t=>!descriptor.wingParts.includes(t.partsType));
    // Core first. The actual native destroyed bit authorizes one wing afterward.
    if(!state.destroyedParts.includes(descriptor.corePart))return targets.filter(t=>!descriptor.wingParts.includes(t.partsType));
    const wings=targets.filter(t=>descriptor.wingParts.includes(t.partsType));
    if(chosenWing===null&&wings.length)chosenWing=wings.reduce((a,b)=>BigInt(a.hp||'0')<=BigInt(b.hp||'0')?a:b).partsType;
    return targets.filter(t=>!descriptor.wingParts.includes(t.partsType)||t.partsType===chosenWing);
  },rank(target) {return !wingDestroyed&&target.partsType===chosenWing?-10:null;},
  summary:()=>({chosenWing,wingDestroyed,bossId,destructionProof:'original_parts_IsDestroyed_boolean'})};
}

// A current original visual transform is an input anchor, never a claim that
// the destroyed core collider is active. Original ray/hit logic decides contact.
function mechanicsUltraCenterlineTargets(waveId,core,anchors,seenCorePartTypes,ownerId) {
  if(waveId!==6302008||core?.supported!==true||core.phase!==1||core.nativeHasActiveCore!==false||
    !(seenCorePartTypes instanceof Set)||!Number.isSafeInteger(ownerId)||ownerId<=0)return [];
  return (Array.isArray(anchors)?anchors:[]).filter(a=>seenCorePartTypes.has(a.partsType)&&
    a.source==='original_persistent_HitPoint_transform'&&a.claimsActiveCollider===false&&
    Array.isArray(a.world)&&a.world.length===3&&a.world.every(Number.isFinite))
    .map(a=>({...a,key:'visual-anchor:'+ownerId+':'+a.partsType,kind:'AimAnchor',ownerId,unsafePresent:false}));
}

// STAGED input-policy evidence only. Original events, owner and IsAlive; no HP arithmetic.
function createMechanicsUltraBarrierObserver(runtime, emit, waveId) {
  if (waveId !== 6302008) return {
    forwardEvent() {}, cleanup() {}, check() { return null; },
    snapshot() { return {supported:false,allLivingActorsShielded:false,reason:'outside_ultra',owners:[]}; }
  };
  const names = {
    added:'NK.Spot.Event.Character.AddedBarrierEvent',
    removed:'NK.Spot.Event.Summon.RemovedCharacterBarrierEvent',
    summon:'NK.Spot.Model.Summon.SpotSummon',
    barrier:'NK.Spot.Model.Summon.SpotCharacterBarrier',
    entity:'NK.Spot.Model.Common.SpotEntity',
    info:'NK.Spot.Logic.Character.SpotEntityInfo'
  };
  const classes=Object.fromEntries(Object.entries(names).map(([k,v])=>[k,runtime.class(v)]));
  const field=(klass,name,offset,type)=>{
    const f=klass.field(name);
    if(f.offset!==offset||f.type.name!==type||f.isStatic)
      throw Error('Original Ultra barrier field mismatch: '+klass.type.name+'.'+name);
  };
  field(classes.added,'Barrier',72,names.summon);
  field(classes.removed,'BarrierInfo',64,names.info);
  field(classes.summon,'<Owner>k__BackingField',104,names.entity);
  field(classes.entity,'Id',16,'System.Int32');
  field(classes.info,'EntityID',16,'System.Int32');
  const aliveMethod=classes.entity.method('IsAlive',0);
  const expected='40534883ec20803d3227260500488bd97573488d0d67249d';
  function checkedAlive(method) {
  const actual=Array.from(new Uint8Array(method.virtualAddress.readByteArray(expected.length/2)))
    .map(b=>b.toString(16).padStart(2,'0')).join('');
  if(!method.virtualAddress.equals(Process.getModuleByName('GameAssembly.dll').base.add(107880192))||
      method.returnType.name!=='System.Boolean'||method.isStatic||method.parameters.length!==0||actual!==expected)
    throw Error('Original Ultra barrier IsAlive ABI mismatch');
  return method;
  }
  checkedAlive(aliveMethod);
  const live=o=>o!=null&&!o.isNull();
  const id=(n,label)=>{n=Number(n);if(!Number.isSafeInteger(n)||n<=0)throw Error('Invalid native barrier '+label);return n;};
  const active=new Map();let fault=null,added=0,removed=0,closed=false;
  const fail=e=>{if(fault===null){fault=String(e&&e.stack||e);active.clear();emit({status:'original_ultra_barrier_fault',fault});}};
  function forwardEvent(event) {
    if(closed||fault!==null||!live(event))return;
    try {
      const type=event.class.type.name;
      if(type===names.added){
        const barrier=event.field('Barrier').value;
        if(!live(barrier))throw Error('Original AddedBarrier has null barrier');
        if(barrier.class.type.name!==names.barrier)return;
        const isAlive=checkedAlive(barrier.method('IsAlive',0));
        const owner=barrier.field('<Owner>k__BackingField').value;
        if(!live(owner))throw Error('Original AddedBarrier has null owner');
        const barrierId=id(barrier.field('Id').value,'identity');
        const ownerId=id(owner.field('Id').value,'owner');
        if(!active.has(barrierId)&&active.size>=64)throw Error('Original barrier map bound exceeded');
        active.set(barrierId,{barrier,ownerId,isAlive});added++;
      }else if(type===names.removed){
        const info=event.field('BarrierInfo').value;
        if(!live(info))throw Error('Original RemovedCharacterBarrier has null identity');
        active.delete(id(info.field('EntityID').value,'removed identity'));removed++;
      }
    }catch(e){fail(e);}
  }
  function snapshot(squad) {
    const unsupported=reason=>({supported:false,allLivingActorsShielded:false,reason,owners:[],added,removed});
    if(closed)return unsupported('observer_closed');
    if(fault!==null)return unsupported('native_barrier_observer_fault');
    if(squad?.supported!==true||!Array.isArray(squad.characters))return unsupported('native_squad_unavailable');
    try {
      const seen=new Set(),living=[];
      for(const actor of squad.characters){
        const actorId=id(actor.id,'squad identity');
        if(seen.has(actorId)||typeof actor.health?.hp!=='string'||!/^\d+$/.test(actor.health.hp))
          return unsupported('native_squad_identity_or_hp_unavailable');
        seen.add(actorId);if(BigInt(actor.health.hp)>0n)living.push(actorId);
      }
      const byOwner=new Map(living.map(n=>[n,[]]));
      for(const [barrierId,row] of active){
        const isAlive=row.isAlive.invoke();
        if(isAlive!==true&&isAlive!==false)throw Error('Native barrier IsAlive returned nonboolean');
        if(!isAlive){active.delete(barrierId);continue;}
        if(byOwner.has(row.ownerId))byOwner.get(row.ownerId).push(barrierId);
      }
      const owners=[...byOwner].map(([ownerId,barrierIds])=>({ownerId,barrierIds:barrierIds.sort((a,b)=>a-b)}));
      return {supported:true,allLivingActorsShielded:living.length>0&&owners.every(o=>o.barrierIds.length>0),
        livingActorIds:living,owners,added,removed,source:'original_AddedBarrier_Owner_IsAlive_RemovedCharacterBarrier',hpCalculated:false};
    }catch(e){fail(e);return unsupported('native_barrier_observer_fault');}
  }
  return {forwardEvent,snapshot,check:()=>fault,cleanup(){closed=true;active.clear();}};
}

// Native attack history is retained per caster even when event logging truncates.
// Null means unavailable; it must never demote a threat.
function mechanicsInterceptionAttackingMobIds(threat) {
  if(threat?.supported!==true||!Array.isArray(threat.casters))return null;
  const ids=[];
  for(const caster of threat.casters) {
    if(!Number.isSafeInteger(caster.casterId)||caster.casterId<=0)return null;
    if(caster.latestAttack==null)continue;
    const attack=caster.latestAttack;
    if(attack.kind!=='attack'||attack.casterId!==caster.casterId||
        !Number.isSafeInteger(attack.tick)||attack.tick<0)return null;
    ids.push(caster.casterId);
  }
  return [...new Set(ids)].sort((a,b)=>a-b);
}
