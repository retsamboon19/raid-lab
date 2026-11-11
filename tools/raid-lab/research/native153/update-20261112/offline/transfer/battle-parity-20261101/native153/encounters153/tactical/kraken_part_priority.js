// Input selection only. Caller supplies original live, alive, projected-visible
// parts; this helper never changes native HP, colliders or attack mechanics.
function createKraken153PartPriority(runtime, waveId) {
  if (waveId !== 6302009) {
    const descriptor=typeof mechanicsInterceptionPolicy==='function'?mechanicsInterceptionPolicy(waveId,runtime):null;
    const rank=(target,context={})=>descriptor?mechanicsInterceptionPartRank(target,context,descriptor):0;
    return {rank,choose:(targets,key,context={})=>keepEqualPriority(targets,key,t=>rank(t,context))};
  }
  const type=Il2Cpp.domain.assembly('NK.Runtime.StaticData').image.class('NK.StaticData.PartsType');
  const read=name=>{
    const value=type.field(name).value;
    return typeof value==='number'||typeof value==='boolean'?Number(value):Number(value.field('value__').value);
  };
  const left=read('Leg_Front_Left'), right=read('Leg_Front_Right');
  const rearLeft=read('Leg_Back_Left'), rearRight=read('Leg_Back_Right');
  if (![left,right,rearLeft,rearRight].every(Number.isSafeInteger)||
      new Set([left,right,rearLeft,rearRight]).size!==4)
    throw Error('Original Kraken part enum unavailable');
  // Exposed original core colliders drive damage aim. A front charge cue may
  // preempt them to cancel the authored attack. Rear parts never displace a
  // visible core just because their HP is low. Authored Kraken phase lists are
  // 1 and 2. Phase 1 keeps front-core aim (the center is armored); only native
  // CurrentPhase 2 promotes the central core. Unknown phases stay conservative.
  const rank=(target,context={})=>target.kind==='Break'?-3:
    (context.urgentFrontParts||[]).includes(target.partsType)?(target.kind==='Core'?-2:-1):
    target.kind==='Core'&&target.nativeIsCore===true?
      ([left,right].includes(target.partsType)?(context.phase===2?1:0):
        (context.phase===2&&target.nativeMainPart===true?0:4)):
    [left,right].includes(target.partsType)?2:
    [rearLeft,rearRight].includes(target.partsType)?3:4;
  return {rank,choose:(targets,key,context={})=>keepEqualPriority(targets,key,t=>rank(t,context))};
}

function keepEqualPriority(targets,key,rank=()=>0) {
  if(!targets.length)return null;
  const best=targets.reduce((a,b)=>rank(a)<=rank(b)?a:b);
  const retained=targets.find(target=>target.key===key);
  return retained&&rank(retained)===rank(best)?retained:best;
}
