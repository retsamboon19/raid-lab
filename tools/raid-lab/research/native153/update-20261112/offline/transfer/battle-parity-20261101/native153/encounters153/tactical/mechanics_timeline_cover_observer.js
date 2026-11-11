// Passive current153 original timeline identity/time reader. No hooks or native writes.
const KRAKEN153_TIMELINE_COVER_METHODS=[{"className":"NK.Spot.Presentation.SpotTimelineController","name":"get_Instance","rva":90844768,"returns":"NK.Spot.Presentation.SpotTimelineController","parameters":[],"static":true,"prefixHex":"40534883ec20803da48b2906007537488d0da2978505e805"},{"className":"NK.Spot.Presentation.Timeline.SpotPlayableDirectorV2","name":"get_Time","rva":98149104,"returns":"System.Double","parameters":[],"static":false,"prefixHex":"40534883ec30803d5056ba0500488bd97513488d0d4f2d1e"},{"className":"NK.Spot.Presentation.Timeline.SpotPlayableDirectorV2","name":"get_IsPlaying","rva":35608640,"returns":"System.Boolean","parameters":[],"static":false,"prefixHex":"0fb64144c3cccccccccccccccccccccc885144c3cccccccc"}];
function createKraken153TimelineCoverObserver(runtime,pin,emit,waveId) {
  const interceptionRules=[...(typeof mechanicsInterceptionTimelineRules==='function'?mechanicsInterceptionTimelineRules(waveId):[]),
    ...(typeof mechanicsIndiviliaTimelineRules==='function'?mechanicsIndiviliaTimelineRules(waveId):[]),
    ...(typeof mechanicsMirrorTimelineRules==='function'?mechanicsMirrorTimelineRules(waveId):[])];
  if(waveId!==6302009&&!interceptionRules.length)return {snapshot:()=>[],summary:()=>({enabled:false})};
  const game=Process.getModuleByName("GameAssembly.dll");
  const classes=new Map();
  for(const row of KRAKEN153_TIMELINE_COVER_METHODS){
    const klass=runtime.class(row.className),method=klass.method(row.name,0);
    if(!method.virtualAddress.equals(game.base.add(row.rva))||method.returnType.name!==row.returns||
       method.isStatic!==row.static||method.parameters.length!==0)
      throw Error("Original Kraken timeline cover signature changed: "+row.name);
    const bytes=new Uint8Array(method.virtualAddress.readByteArray(row.prefixHex.length/2));
    if(Array.from(bytes,b=>b.toString(16).padStart(2,"0")).join("")!==row.prefixHex)
      throw Error("Original Kraken timeline cover prefix changed: "+row.name);
    classes.set(row.className,klass);
  }
  const controllerClass=classes.get("NK.Spot.Presentation.SpotTimelineController");
  const directorClass=classes.get("NK.Spot.Presentation.Timeline.SpotPlayableDirectorV2");
  for(const [klass,name,type,offset] of [
    [controllerClass,"directors","System.Collections.Generic.List<NK.Spot.Presentation.Timeline.SpotPlayableDirectorV2>",48],
    [directorClass,"<Timeline>k__BackingField","UnityEngine.Timeline.TimelineAsset",40],
    [directorClass,"<Owner>k__BackingField","NK.Spot.Model.Common.SpotEntity",112],
    [directorClass,"<DirectorID>k__BackingField","System.Int32",32],
    [directorClass,"_isPlaying","System.Boolean",68]]) {
    const field=klass.field(name);
    if(field.type.name!==type||field.offset!==offset||field.isStatic)throw Error("Original timeline field changed: "+name);
  }
  const getName=Il2Cpp.domain.assembly("UnityEngine.CoreModule").image
    .class("UnityEngine.Object").method("get_name",0);
  requireKraken153Method(getName,139605248);
  const live=x=>x!=null&&!x.isNull();
  const call=(m,self=null,args=[])=>invokeChecked(m,self,args);
  const singleton=pin(call(controllerClass.method("get_Instance",0)));
  if(!live(singleton))throw Error("Original timeline singleton missing");
  let samples=0,matched=0,lastRows=[];
  const phases=new Map(),clipNames=new Map();
  let cachedListKey=null,cachedItemsKey=null,cachedVersion=null,cachedDirectors=[];
  let poolRefreshes=0,lastPoolCount=0,maxPoolCount=0;
  function pooledDirectors(tick) {
    const list=singleton.field("directors").value;
    if(!live(list))throw Error("Original timeline directors list missing");
    const sizeField=list.class.field("_size"),itemsField=list.class.field("_items"),versionField=list.class.field("_version");
    if(sizeField.offset!==24||sizeField.type.name!=="System.Int32"||
       itemsField.offset!==16||versionField.offset!==28||versionField.type.name!=="System.Int32")
      throw Error("Original timeline List layout changed");
    const count=Number(list.field("_size").value),version=Number(list.field("_version").value);
    const items=list.field("_items").value;
    const listKey=list.handle.toString(),itemsKey=live(items)?items.handle.toString():"null";
    if(!Number.isSafeInteger(count)||count<0||count>65536)
      throw Error("Original timeline pool _size outside bound: "+count+" version="+version);
    lastPoolCount=count;maxPoolCount=Math.max(maxPoolCount,count);
    if(listKey!==cachedListKey||itemsKey!==cachedItemsKey||version!==cachedVersion||count!==cachedDirectors.length) {
      const array=live(items)?new Il2Cpp.Array(items.handle):null;
      if(count>0&&(!array||array.length<count))throw Error("Original timeline pool count exceeds backing array: "+count);
      cachedDirectors=[];
      for(let i=0;i<count;i++)cachedDirectors.push(array.get(i));
      cachedListKey=listKey;cachedItemsKey=itemsKey;cachedVersion=version;poolRefreshes++;
      if(poolRefreshes<=16)emit({status:"original_kraken_timeline_pool_observed",tick,count,
        backingArrayLength:array?.length||0,version,poolRefreshes,countSource:"original_List_size",readsOnly:true});
    }
    return cachedDirectors;
  }
  function snapshot(tick,observation){
    const bosses=new Set((observation?.monsters||[]).filter(m=>(waveId===6302009?String(m.tableId)==="1520040153":interceptionRules.some(rule=>String(m.tableId)===String(rule.monsterId)))).map(m=>m.entityId));
    const rows=[];
    // Cache pooled references until the original List version/backing array changes.
    // A cheap guarded native Boolean read filters idle pooled directors; only
    // currently playing boss directors need owner/name/time managed reads.
    for(const director of pooledDirectors(tick)) {
      if(!live(director)||director.handle.add(68).readU8()===0)continue;
      const owner=director.field("<Owner>k__BackingField").value;
      if(!live(owner))continue;
      const ownerId=Number(owner.field("Id").value);
      if(!bosses.has(ownerId))continue;
      const timeline=director.field("<Timeline>k__BackingField").value;
      if(!live(timeline))continue;
      const clipKey=timeline.handle.toString();
      let name=clipNames.get(clipKey);
      if(name===undefined){
        const nameValue=call(getName,timeline);
        name=live(nameValue)?new Il2Cpp.String(nameValue.handle).content:null;
        if(clipNames.size<4096)clipNames.set(clipKey,name);
      }
      const frontAttack=["bbg004_skill_03_dmtr","bbg004_skill_04_dmtr"].includes(name);
      const interceptionRule=interceptionRules.find(rule=>rule.clip===name);
      if(waveId!==6302009?!interceptionRule:(name!=="bbg004_skill_01_dmtr"&&!frontAttack))continue;
      const time=call(directorClass.method("get_Time",0),director).unbox().handle.readDouble();
      if(!Number.isFinite(time)||time<0)throw Error("Original Kraken timeline time invalid");
      const row=interceptionRule?{tick,ownerId,directorId:Number(director.field("<DirectorID>k__BackingField").value),name,time,
        ...interceptionRule,role:interceptionRule.role||"source_bound_interception_cover",loopStart:interceptionRule.coverStart??interceptionRule.windowStart,loopEnd:interceptionRule.coverStart??interceptionRule.windowEnd}:
        {tick,ownerId,directorId:Number(director.field("<DirectorID>k__BackingField").value),name,time,
        skillId:frontAttack?null:532037,role:frontAttack?"front_tentacle":"big_aoe",
        loopStart:frontAttack?2.7333333333333334:3,
        loopEnd:frontAttack?5.4:5.666666666666667,attackMarker:frontAttack?6.183333333333334:6.05};
      rows.push(row);
      const phase=row.role==="mirror_slipper_exposure"?(time<row.windowStart?"native_slipper_windup":time<=row.windowEnd?"native_slipper_exposure":"after_native_slipper_exposure"):time<row.loopStart?"windup":time<row.loopEnd?"native_charge_loop":time<=row.attackMarker?"preimpact_marker_window":"after_attack_marker";
      if(phases.get(row.directorId)!==phase){
        phases.set(row.directorId,phase);
        emit({status:row.role==="mirror_slipper_exposure"?"original_mirror_slipper_timeline_observed":frontAttack?"original_kraken_front_attack_timeline_observed":"original_kraken_timeline_cover_observed",phase,...row,readsOnly:true});
      }
    }
    samples++;matched+=rows.length;lastRows=rows;return rows;
  }
  emit({status:waveId===6302009?"original_kraken_timeline_cover_ready":"original_interception_timeline_cover_ready",sourceMetadataSha256:"971958024ba71bbf158b3e03618f5deb7776a78084ea6b3c4acdbcaea7e7a2e2",
    clip:"bbg004_skill_01_dmtr",skillId:532037,originalLoopEnd:5.666666666666667,originalAttackMarker:6.05,
    readsOnly:true,signatureAndPrefixGuarded:true,nativeProtectionVerified:false,enabled:waveId===6302009,interceptionRules});
  return {snapshot,summary:()=>({samples,matched,lastRows,poolRefreshes,lastPoolCount,maxPoolCount,readsOnly:true})};
}
function kraken153TimelineSlamCoverWanted(rows) {
  // The window is bounded by two extracted original timeline markers. Actual
  // director time includes native loops/jumps; wall/video time is never used.
  return (rows||[]).some(row=>row.name==="bbg004_skill_01_dmtr"&&row.skillId===532037&&
    row.time>=5.666666666666667&&row.time<=6.05);
}

function kraken153FrontTimelineThreatActive(rows) {
  // Both authored front-tentacle clips share these original charge markers.
  // Side identity is deliberately not inferred from clip suffixes. The caller
  // prioritizes live front parts while either native charge is in progress.
  return (rows||[]).some(row=>["bbg004_skill_03_dmtr","bbg004_skill_04_dmtr"].includes(row.name)&&
    Number.isFinite(row.time)&&row.time>=2.7333333333333334);
}

// Only exact original clip identities and extracted native pre-impact markers
// may request non-Kraken cover. No wall-clock or guide timestamp replay.
function mechanicsInterceptionTimelineCoverWanted(rows) {
  return (rows||[]).some(row=>row.role==='source_bound_interception_cover'&&
    row.coverable===true&&row.coverPiercing===false&&Number.isFinite(row.time)&&
    Number.isFinite(row.coverStart)&&Number.isFinite(row.attackMarker)&&
    row.coverStart<=row.attackMarker&&row.time>=row.coverStart&&row.time<=row.attackMarker);
}
