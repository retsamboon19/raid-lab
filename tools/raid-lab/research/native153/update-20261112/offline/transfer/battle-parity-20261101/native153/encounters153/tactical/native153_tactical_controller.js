// Current153 original input orchestration. All damage, collider health, QTE
// outcomes, projectiles, cooldowns and boss transitions belong to the engine.
// Construct on Unity main thread after original Playing/aim geometry readiness,
// before the owner's SendEventDefault dispatch listener is installed.
function createNative153TacticalController(runtime, management, team, geometry, aimBinding, pin, emit, configuration) {
  const options = configuration || {};
  const policy = options.control_policy || 'auto';
  if (!['auto', 'qte-parts-cover'].includes(policy) || !Number.isSafeInteger(options.waveId) || options.waveId <= 0)
    throw Error('Original native control policy and wave identity required');
  let closed = false, originalFinishReleased = false, nativeEventFilter=null;
  if (policy === 'auto') {
    emit({status:'native_control_mode_selected',controlMode:'auto',issuesTacticalCommands:false,
      observesNativeState:false,waveId:options.waveId,current153NativeValidated:false});
    return {beforeTick(){},afterTick(){},forwardEvent(){},check(){},
      close(){closed=true;},onNativeFinish(){closed=true;originalFinishReleased=true;},
      summary:()=>({policy,closed,originalFinishReleased,commands:0,originalAutomaticControlsPreserved:true})};
  }
  const binding = kraken153Binding();
  const dispatch = runtime.class('NK.Spot.SpotManagement').method('SendEventDefault',1);
  requireKraken153Method(dispatch,binding.methods.dispatch.rva);
  // Resolve every original declaration before attaching the mouse input hook.
  const observer = createMechanicsTacticalObserver(runtime,management,team,pin,emit,true,options.waveId===6302008,[6302006,6302009].includes(options.waveId));
  const threats = createMechanicsThreatObserver(runtime,management,emit,{mode:'monster',watchAttackNodes:[],maxEventLogs:512,dispatchOrdinalProvider:()=>nativeEventFilter?.dispatchCount()});
  const breakable = createMechanicsBreakableObserver(runtime,management,pin,emit);
  const actions = createMechanicsTacticalActions(runtime,management,team,geometry,aimBinding,pin,emit);
  const observationTiming=createNativeObservationTiming(options.waveId===6302006,emit,300);
  const originalInputModePolicy=[6302006,6302008,6302010].includes(options.waveId);
  const nativeChargedCarryPolicy=[6302006,6302010].includes(options.waveId);
  const optionalChargeHandoff=createMechanicsOptionalChargeHandoff(actions.focusedChargeState,emit,options.waveId===6302006);
  const firing=createMechanicsFiringPolicy(actions,{nativeInputTypes:originalInputModePolicy});
  const interceptionPolicy=mechanicsInterceptionPolicy(options.waveId,runtime);
  const partPriority=createKraken153PartPriority(runtime,options.waveId);
  const interceptionThreats=createMechanicsInterceptionThreatTargets(runtime,management,pin,emit,options.waveId);
  const ultraBarriers=createMechanicsUltraBarrierObserver(runtime,emit,options.waveId);
  let latestUltraBarriers={supported:false,allLivingActorsShielded:false},lastShieldSkip=false;
  const moderniaWing=createMechanicsModerniaWingPolicy(interceptionPolicy);
  const mirrorStrategy=readNativeMirrorTeamStrategy(runtime,aimBinding,emit,options.waveId);
  const mirror=createMechanicsMirrorPolicy(actions,emit,{waveId:options.waveId,monsterId:interceptionPolicy?.monsterId,strategy:mirrorStrategy});
  const harvesterCover=createMechanicsHarvesterTargetCover(actions,emit,{waveId:options.waveId,monsterId:interceptionPolicy?.monsterId});
  let latestInterceptionThreats={supported:true,targets:[],modernia:{supported:false}};
  if(options.waveId===6302009&&typeof kraken153FrontTimelineThreatActive!=='function')
    throw Error('Original Kraken front timeline policy missing');
  const coreObserver=createKraken153CoreObserver(runtime,management,pin,emit,options.waveId,options.waveId===6302006?{visibleCorePoint:actions.visibleCorePoint,observePartColliders:mirrorStrategy.mode!=='core_pressure'}:{});
  const qteActorEvidence=createMechanicsQteActorEvidence(runtime,management,pin,emit);
  const weaponInputEvidence=createMechanicsWeaponInputEvidence(runtime,aimBinding,emit,options.waveId===6302006);
  const krakenFriendly=createMechanicsKrakenFriendlyProjectiles(runtime,management,pin,options.waveId===6302009);
  const qte = createMechanicsQtePolicy(actions,emit,{actorEvidence:qteActorEvidence,offensiveSuppression:[6302006,6302009].includes(options.waveId),suppressionGrayOnly:options.waveId===6302009,preferReadyClassOrderInGray:options.waveId===6302009,readFriendlyProjectiles:options.waveId===6302009?((tick,observation)=>krakenFriendly.snapshot(tick,observation.squad)):undefined,pendingChainBridge:options.waveId===6302006});
  // Kraken: cover only the observed big-attack timeline. Routine missiles and
  // the historical Shot02 follow-up rule must not interrupt damage output.
  const authored = null;
  const slamCover=createKraken153TimelineCoverObserver(runtime,pin,emit,options.waveId);
  let slamRows=[],slamIntentActive=false,latestCore={supported:true,targets:[]};
  let latest=null,latestThreat=null,latestBreak=null,lastBefore=-1,lastAfter=-1;
  const ultraCorePartTypes=new Set();
  let samples=0,transitions=0,signature=null,fault=null,genericCovered=false,genericCoverCommands=0;
  let chargedCarryOwned=false,carryReadySignature=null;
  let lastDirectedAim=null;
  let aimOwned=false,actorId=null,targetKey=null,priorAuto=null,targetSince=-1,aimCommands=0;
  const shotWitness=createMechanicsMirrorShotWitness(runtime,management,aimBinding,emit,{
    enabled:options.passiveShotWitness===true,waveId:options.waveId,nativeNameCodes:mirrorStrategy.nativeNameCodes,
    readNativeAim:actions.nativeAimEvidence,
    readIntent:()=>({aimOwned,actorId,targetKey,targetSince,lastFullObservationTick:latest?.tick??null,
      lastDirectedAim:lastDirectedAim?{...lastDirectedAim,world:[...lastDirectedAim.world]}:null,
      boundBossOwnerId:(latest?.monsters||[]).some(m=>m.entityId===latest?.monster?.targetMonsterId&&String(m.tableId)===String(interceptionPolicy?.monsterId))?latest.monster.targetMonsterId:null}),
    inspectCore:(owner,start,target)=>coreObserver.inspectProjectileRay(owner,start,target,actions.inspectProjectileInitialRay)
  });
  const missing = new Set();
  const log = (action,detail={}) => emit({status:'native153_tactical_decision',action,...detail});
  const noteMissing = reason => {if(!missing.has(reason)){missing.add(reason);log('unsupported',{reason});}};
  const tick = () => {
    const value=Number(management.field('_tickCount').value);
    if(!Number.isSafeInteger(value)||value<0)throw Error('Original native tactical tick unavailable');
    return value;
  };
  const decimal = value => typeof value==='string' && /^-?\d+$/.test(value);
  const vector = value => Array.isArray(value)&&value.length===3&&value.every(Number.isFinite);
  const releaseAim = reason => {
    if(!aimOwned)return;
    const selectedActor=actorId,selectedTarget=targetKey;
    const failures=mechanicsRunIndependentCleanup([
      ['cancel_charged_carry_before_priority',()=>{if(chargedCarryOwned||originalInputModePolicy&&actions.snapshot().focusedNativeInputType===2)actions.setActorStance(actorId,'Idle');}],
      ['release_directed_pointer',()=>{if(actions.controlFlag("inputType")===2)actions.release();}],
      ['restore_directed_auto',()=>{if(actions.controlFlag("autoAim")===false)actions.setAutoAim(priorAuto);}],
      ['reset_directed_ownership',()=>{aimOwned=false;actorId=null;targetKey=null;priorAuto=null;targetSince=-1;chargedCarryOwned=false;optionalChargeHandoff.cancel(reason);firing.reset();}]
    ]);
    log('release_directed_aim',{tick:tick(),reason,actorId:selectedActor,targetKey:selectedTarget,
      cleanupErrors:failures.map(f=>({step:f.step,error:String(f.error)}))});
    if(failures.length)throw failures[0].error;
  };
  const readyActors = () => {
    if(latest?.squad?.supported!==true||!Array.isArray(latest.squad.characters))return [];
    const preference={SMG:0,AR:1,MG:2,AS:3,SG:4,SR:5,RL:6,GL:7,PS:8};
    return latest.squad.characters.filter(actor=>Number.isSafeInteger(actor.id)&&actor.id>0&&
      decimal(actor.health?.hp)&&BigInt(actor.health.hp)>0n&&decimal(actor.weapon?.ammo)&&BigInt(actor.weapon.ammo)>0n&&
      Object.prototype.hasOwnProperty.call(preference,actor.weapon.type?.name)).sort((a,b)=>(options.waveId===6302006&&a.weapon.nativeIsAutoFireWeapon===true?-1:preference[a.weapon.type.name])-(options.waveId===6302006&&b.weapon.nativeIsAutoFireWeapon===true?-1:preference[b.weapon.type.name])||a.id-b.id);
  };
  const directedTargets = () => {
    const monsters=latestBreak?.supported===true&&Array.isArray(latestBreak.monsters)?latestBreak.monsters:[];
    const playing=monsters.filter(owner=>owner.supported===true&&owner.playing===true&&!owner.nativeIsAllBreak);
    if(playing.length) {
      // Non-QTE interruption circles use their original native collider type,
      // active bit, health and bounds; Counter/Choice are excluded explicitly.
      return playing.flatMap(owner=>(owner.colliders||[]).filter(collider=>collider.liveBreakTarget===true&&
        collider.type?.name==='Break'&&decimal(collider.hp)&&BigInt(collider.hp)>0n&&vector(collider.worldAimPoint))
        .map(collider=>({key:'break:'+owner.entityId+':'+collider.colliderId,world:collider.worldAimPoint,
          kind:'Break',ownerId:owner.entityId,colliderId:collider.colliderId,hp:collider.hp,
          unsafePresent:owner.colliders.some(item=>item.unityLive&&item.enabled&&['Counter','Choice'].includes(item.type?.name))})));
    }
    const defensiveTargets=latestInterceptionThreats.supported===true?latestInterceptionThreats.targets:[];
    if(latest?.monster?.supported!==true||!Array.isArray(latest.monster.parts))return defensiveTargets;
    if(interceptionPolicy&&!latest.monsters.some(owner=>owner.entityId===latest.monster.targetMonsterId&&
      String(owner.tableId)===String(interceptionPolicy.monsterId))) {
      noteMissing('target_is_not_source_bound_interception_boss');return defensiveTargets;
    }
    if(latestCore.supported!==true) {
      noteMissing(latestCore.reason||'native_core_snapshot_unavailable');return defensiveTargets;
    }
    const liveParts=latest.monster.parts.filter(part=>decimal(part.hp)&&BigInt(part.hp)>0n&&vector(part.worldPosition))
      .sort((a,b)=>BigInt(a.hp)<BigInt(b.hp)?-1:BigInt(a.hp)>BigInt(b.hp)?1:a.partsType-b.partsType)
      .map(part=>({key:'part:'+latest.monster.targetMonsterId+':'+part.partsType,world:part.worldPosition,
        kind:'Part',ownerId:latest.monster.targetMonsterId,partsType:part.partsType,hp:part.hp,unsafePresent:false}));
    const cores=mechanicsLiveCoreTargets(latestCore.targets||[],liveParts)
      .filter(core=>vector(core.world));
    if(options.waveId===6302008)for(const core of cores)ultraCorePartTypes.add(core.partsType);
    const centerAnchors=mechanicsUltraCenterlineTargets(options.waveId,latestCore,latest.monster.aimAnchors,ultraCorePartTypes,latest.monster.targetMonsterId);
    return moderniaWing.filter([...defensiveTargets,...mechanicsInterceptionFilterTargets([...cores,...centerAnchors,...liveParts],interceptionPolicy,latestCore)],latestInterceptionThreats.modernia);
  };
  const aimStep = current => {
    // Refresh moving edge/offscreen core geometry at input selection. Stable
    // on-screen center aim keeps the original bounded observation cadence.
    if(options.waveId===6302006&&mechanicsMirrorCoreGeometryRefreshWanted(latestCore,world=>actions.projectWorld(world)))
      latestCore=coreObserver.snapshot(latest.monster?.targetMonsterId,true);
    const breakPreemptsMirror=mechanicsHasLiveDirectedBreak(latestBreak);
    if(breakPreemptsMirror)mirror.suspend('original_non_qte_break_priority');
    if(interceptionPolicy?.waveId===6302006&&!breakPreemptsMirror) {
      const owner=(latest.monsters||[]).find(m=>m.entityId===latest.monster?.targetMonsterId);
      const prepareTargets=owner&&String(owner.tableId)===String(interceptionPolicy.monsterId)?
        (latest.monster.parts||[]).filter(p=>interceptionPolicy.avoidParts.includes(p.partsType)&&decimal(p.hp)&&BigInt(p.hp)>0n&&vector(p.worldPosition))
          .map(p=>({key:'part:'+owner.entityId+':'+p.partsType,kind:'Part',ownerId:owner.entityId,partsType:p.partsType,hp:p.hp,world:p.worldPosition,hurtCount:p.hurtCount,nativePartActive:p.nativePartActive,nativeIsDestroyed:p.nativeIsDestroyed})):[];
      const slippers=prepareTargets.flatMap(p=>(latestCore.partTargets||[]).filter(c=>c.partsType===p.partsType&&c.ownerId===p.ownerId)
        .map(c=>({...p,...c,hp:p.hp,hurtCount:p.hurtCount,nativePartActive:p.nativePartActive,nativeIsDestroyed:p.nativeIsDestroyed})));
      const fallback=directedTargets().find(t=>['Core','Part'].includes(t.kind)&&t.ownerId===owner?.entityId&&actions.projectWorld(t.world).visible);
      const mirrorInput={tick:current,targets:slippers,prepareTargets,actors:readyActors(),monsterId:owner?Number(owner.tableId):null,
        ownerId:owner?.entityId,fallbackWorld:fallback?.world,phase:latestCore.phase,partStates:latest.monster?.partStates||[],timelineRows:slamRows};
      if(mirror.wantsOwnership(mirrorInput))releaseAim('mirror_original_exposure_priority');
      const decision=mirror.step(mirrorInput);
      if(decision.handled)return;
    }
    const targets=directedTargets().filter(target=>actions.projectWorld(target.world).visible);
    if(!targets.length){releaseAim('no_visible_live_break_or_part');return;}
    let actors=mechanicsEligibleDirectedActors(readyActors(),targets,options.waveId)
      .filter(actor=>!targets.some(target=>target.unsafePresent)||['SMG','AR','MG','AS','SR'].includes(actor.weapon.type.name));
    if(nativeChargedCarryPolicy)actors=actors.filter(actor=>[1,2,3].includes(actor.weapon.nativeInputType)||actor.weapon.nativeDownFireTiming===true);
    if(!actors.length){releaseAim('no_ready_safe_actor');noteMissing('no_ready_actor_for_directed_target');return;}
    if(aimOwned&&!actors.some(actor=>actor.id===actorId))releaseAim('actor_reloading_or_defeated');
    const coreFirstMissileIds=options.waveId===6302006&&latestThreat?.supported===true?
      (latestThreat.activeBossProjectiles||[]).filter(p=>(latestCore.phase===1?[520661]:latestCore.phase===2?[520678,520679]:[]).includes(p.source?.skillId)).map(p=>p.projectileId):null;
    const preferredMirrorTarget=options.waveId===6302006?partPriority.choose(targets,targetKey,{phase:latestCore.phase,coreFirstMissileIds}):null;
    const ordinaryCarryAim=nativeChargedCarryPolicy&&mechanicsDirectedCarryAimAllowed(options.waveId,targets,preferredMirrorTarget);
    let carryActors=ordinaryCarryAim?mechanicsReadyOriginalUpCarries(actors,targets):[];
    if(options.waveId===6302006) {
      const heldCarries=carryActors.filter(actor=>actor.weapon.nativeInputType===3);
      if(heldCarries.length)carryActors=heldCarries;
    }
    const readySignature=carryActors.map(actor=>[actor.id,actor.weapon.identity,actor.weapon.nativeInputType].join(':')).sort().join('|');
    if(!ordinaryCarryAim||!carryActors.length)optionalChargeHandoff.cancel('urgent_target_or_no_ready_carry');
    if(ordinaryCarryAim&&carryActors.length&&(!aimOwned||readySignature!==carryReadySignature||optionalChargeHandoff.pending())) {
      const scores=qteActorEvidence.read(carryActors.map(actor=>actor.id),current,'whole_outgoing');
      const replacementCarries=carryActors.filter(actor=>actor.weapon.nativeIsReplacement===true);
      let ranked=mechanicsRankActorsByObservedDamage(replacementCarries.length?replacementCarries:carryActors,scores,false);
      if(options.waveId===6302006) {
        const inputIndex=weaponInputEvidence.read(carryActors.map(actor=>actor.id),current);
        if(inputIndex.supported)ranked=inputIndex.actorIds.map(id=>carryActors.find(actor=>actor.id===id));
      }
      if(aimOwned&&ranked[0].id!==actorId) {
        if(!optionalChargeHandoff.defer(actorId,ranked[0].id,current))releaseAim('ready_original_up_carry_priority');
      } else optionalChargeHandoff.cancel('preferred_actor_unchanged');
      if(!aimOwned)actors=ranked;
      log('native_up_carry_candidates',{tick:current,heuristic:options.waveId===6302006?'original_current_weapon_input_index':'original_whole_outgoing_including_skills_and_passives',actors:ranked.map(actor=>({actorId:actor.id,nativeBurstStep:actor.nativeBurstStep,nativeInputType:actor.weapon.nativeInputType,nativeIsReplacement:actor.weapon.nativeIsReplacement,nativeDownFireTiming:actor.weapon.nativeDownFireTiming,weaponIdentity:actor.weapon.identity,nativeObservedDamage:scores[String(actor.id)]}))});
    }
    carryReadySignature=readySignature;
    if(chargedCarryOwned&&(!(actors.find(actor=>actor.id===actorId)?.weapon.nativeInputType===2||actors.find(actor=>actor.id===actorId)?.weapon.nativeInputType===3||actors.find(actor=>actor.id===actorId)?.weapon.nativeDownFireTiming===true)))releaseAim('original_up_carry_priority_or_mode_changed');
    // Re-rank live replacement weapons. Leave charge control to the original
    // unfocused character BT when a ready continuous-fire actor can aim here.
    // Retain ordinary ownership; do not switch between continuous actors.
    if(aimOwned&&!chargedCarryOwned&&['SR','RL'].includes(actors.find(actor=>actor.id===actorId)?.weapon.type.name)&&
        !(originalInputModePolicy&&(actors.find(actor=>actor.id===actorId)?.weapon.nativeInputType===3||actors.find(actor=>actor.id===actorId)?.weapon.nativeDownFireTiming===true))&&
        (options.waveId!==6302006||actors.find(actor=>actor.id===actorId)?.weapon.nativeIsAutoFireWeapon!==true)&&
        actors[0].id!==actorId&&(['SMG','AR','MG','AS'].includes(actors[0].weapon.type.name)||(options.waveId===6302006&&actors[0].weapon.nativeIsAutoFireWeapon===true)))
      releaseAim('native_charge_weapon_handoff');
    if(!aimOwned&&options.waveId!==6302010&&!(ordinaryCarryAim&&carryActors.length)) {
      const scores=qteActorEvidence.read(actors.map(actor=>actor.id),current,options.waveId===6302006?'whole_outgoing':'shot');
      actors=mechanicsRankActorsByObservedDamage(actors,scores,true,originalInputModePolicy);
      log('directed_native_actor_evidence',{tick:current,evidenceMode:options.waveId===6302006?'whole_outgoing_including_skills_and_passives':'shot',actors:actors.map(actor=>({actorId:actor.id,weapon:actor.weapon.type.name,ammo:actor.weapon.ammo,nativeIsAutoFireWeapon:actor.weapon.nativeIsAutoFireWeapon,nativeObservedDamage:scores[String(actor.id)]}))});
    }
    if(!aimOwned) {
      const state=actions.snapshot();
      if(state.forcedCover||state.inputType===2){noteMissing('existing_native_input_ownership');return;}
      priorAuto=state.autoAim;actorId=actors[0].id;aimOwned=true;chargedCarryOwned=nativeChargedCarryPolicy&&actors[0].nativeIsBurst3===true&&(actors[0].weapon.nativeInputType===2||actors[0].weapon.nativeInputType===3||actors[0].weapon.nativeDownFireTiming===true);
      actions.setAutoAim(false);actions.focus(actorId);
      log('take_directed_aim',{tick:current,actorId,chargedCarryOwned,nativeBurstStep:actors[0].nativeBurstStep,nativeInputType:actors[0].weapon.nativeInputType,nativeIsReplacement:actors[0].weapon.nativeIsReplacement,nativeDownFireTiming:actors[0].weapon.nativeDownFireTiming,weaponIdentity:actors[0].weapon.identity,casterElementIds:actors[0].casterElementIds,
        requiredElementId:targets.some(t=>t.kind==='Break')?mechanicsInterceptionRequiredElement(options.waveId):null});
    }
    const state=actions.directedOwnershipState();
    if(state.forcedCover||state.autoAim!==false||state.focusedEntityId!==actorId){releaseAim('native_ownership_changed');return;}
    const urgentFrontParts=typeof kraken153FrontTimelineThreatActive==='function'&&
      kraken153FrontTimelineThreatActive(slamRows)?[9,10]:[];
    const rankContext={phase:latestCore.phase,urgentFrontParts,
      coreFirstMissileIds,
      attackingMobIds:options.waveId===6302010?mechanicsInterceptionAttackingMobIds(latestThreat):null};
    const target=interceptionPolicy?.waveId===6302005?
      keepEqualPriority(targets,targetKey,t=>Math.min(partPriority.rank(t,rankContext),(moderniaWing.rank(t)??Infinity))):
      partPriority.choose(targets,targetKey,rankContext);
    if(target.key!==targetKey) {
      const preserveHeld=mechanicsPreserveDirectedTrigger(originalInputModePolicy,chargedCarryOwned,actors.find(actor=>actor.id===actorId),target);
      if(state.inputType===2&&!preserveHeld){if(originalInputModePolicy&&(chargedCarryOwned||state.focusedNativeInputType===2))actions.setActorStance(actorId,"Idle");actions.release();}
      targetKey=target.key;targetSince=current;
      if(options.waveId===6302006&&target.kind==='Part')
        log('mirror_core_fallback_projection',{tick:current,...mechanicsMirrorCoreProjectionWitness(latestCore,latest.monster?.parts||[],geometry.screen,world=>actions.projectWorld(world))});
      log('select_live_target',{tick:current,actorId,...target,nativePhase:latestCore.phase,
        activePartTypes:(latest.monster?.parts||[]).map(part=>part.partsType),
        urgentFrontParts,targetReason:target.kind==='Break'?'original_break_priority':
          urgentFrontParts.includes(target.partsType)?'original_front_charge_cancel':
          target.kind==='Core'?'original_exposed_core':target.kind==='AimAnchor'?'original_persistent_centerline_anchor_not_live_core':'live_part_fallback'});
    }
    actions.aimWorld(actorId,target.world,false,false);aimCommands++;
    if(options.passiveShotWitness===true)lastDirectedAim={tick:current,actorId,key:target.key,kind:target.kind,
      ownerId:target.ownerId,world:[...target.world],nativeGeometryTick:target.nativeGeometryTick??latest.tick};
    const actor=actors.find(value=>value.id===actorId);
    firing.step(actor.weapon.type.name,current-targetSince>=3);
  };
  const projectileCoverWanted = () => interceptionPolicy?
    mechanicsInterceptionProjectileCoverWanted(options.waveId,latest,latestThreat):
    mechanicsIncomingProjectileCoverWanted(options.waveId,latest,latestThreat);
  const check = () => {
    try {
      observer.checkFault();threats.checkFault();breakable.checkFault();qte.checkFault();actions.pointer.check();
      if(fault)throw fault;
    } catch(error) {
      fault=fault||error;
      if(!closed)try {close('native_observer_fault');}
      catch(cleanupError){emit({status:'native153_tactical_cleanup_fault',error:String(cleanupError),originalFault:String(fault)});}
      throw fault;
    }
  };
  function beforeTick(driverTick) {
    if(closed)return;
    try {
    check();const current=tick();
    if(current===lastBefore||latest===null)return;
    if(current<lastBefore)throw Error('Native tactical clock moved backwards');
    lastBefore=current;
      if(genericCovered&&!actions.controlFlag("forcedCover")) {
        genericCovered=false;log('projectile_cover_ownership_changed',{tick:current});
      }
      const sourceIntent=authored?authored.inspect(current,latest,latestThreat):{wantsCover:false};
      const nativeTimelineCoverWanted=kraken153TimelineSlamCoverWanted(slamRows)||mechanicsInterceptionTimelineCoverWanted(slamRows);
      if(options.waveId===6302008&&nativeTimelineCoverWanted)latestUltraBarriers=ultraBarriers.snapshot(latest.squad);
      const shieldSkip=options.waveId===6302008&&nativeTimelineCoverWanted&&latestUltraBarriers.supported===true&&latestUltraBarriers.allLivingActorsShielded===true;
      if(shieldSkip!==lastShieldSkip){lastShieldSkip=shieldSkip;log('native_owned_barrier_cover_gate',{tick:current,skipTimelineCover:shieldSkip,barriers:latestUltraBarriers,timelines:slamRows});}
      const slamIntent={wantsCover:nativeTimelineCoverWanted&&!shieldSkip,threats:slamRows};
      if(slamIntent.wantsCover!==slamIntentActive) {
        slamIntentActive=slamIntent.wantsCover;
        log('timeline_slam_cover_intent',{tick:current,wantsCover:slamIntentActive,timelines:slamRows,
          ruleId:options.waveId===6302009?'kraken-shot06-original-timeline-markers':'original_interception_timeline_markers'});
      }
      const wantsGeneric=projectileCoverWanted()||slamIntent.wantsCover;
      const wantsCover=sourceIntent.wantsCover||wantsGeneric;
      if(wantsCover)harvesterCover.step(current,latest,latestThreat,{preempted:true,nativePhase:latestCore.phase});
      if(wantsCover||authored?.summary().covered) {
        mirror.suspend('native_projectile_or_authored_cover');releaseAim('native_projectile_or_authored_cover');qte.suspend(current,'native_projectile_or_authored_cover');
      }
      if(genericCovered&&sourceIntent.wantsCover) {
        if(actions.controlFlag("forcedCover"))actions.setCover(false);
        genericCovered=false;genericCoverCommands++;
      }
      if(authored)authored.step(current,latest,latestThreat,{qteSuspended:qte.summary().owned});
      if(!authored?.summary().covered&&!sourceIntent.wantsCover) {
        if(wantsGeneric&&!genericCovered) {
          const state=actions.snapshot();
          if(!state.forcedCover&&state.inputType!==2&&state.autoAim===true) {
            actions.setCover(true);genericCovered=true;genericCoverCommands++;
            log('projectile_cover_entered',{tick:current,reason:slamIntent.wantsCover?(options.waveId===6302009?'kraken_shot06_original_timeline':'source_bound_interception_timeline'):'live_nonpiercing_projectile',slamThreats:slamIntent.threats});
          }
        } else if(genericCovered&&!wantsGeneric) {
          if(actions.controlFlag("forcedCover"))actions.setCover(false);
          genericCovered=false;genericCoverCommands++;log('projectile_cover_released',{tick:current});
        }
      }
      if(actions.controlFlag("forcedCover")) {mirror.suspend('native_forced_cover');releaseAim('native_forced_cover');qte.suspend(current);return;}
      const coverContext={preempted:latest.qte?.supported===true&&latest.qte.active,nativePhase:latestCore.phase};
      if(harvesterCover.wantsOwnership(latest,latestThreat,coverContext)) {
        releaseAim('source_bound_harvester_targeted_cover');qte.suspend(current,'source_bound_harvester_targeted_cover');
        if(harvesterCover.step(current,latest,latestThreat,coverContext))return;
      } else harvesterCover.step(current,latest,latestThreat,coverContext);
      qte.resume(current);
      if(latest.qte?.active===true&&(options.waveId===6302006||options.waveId===6302009&&latest.qte.nativePresetHasForbidden===true))
        latest.qte=observer.snapshotQteGeometry(current);
      if(latest.qte?.supported===true&&latest.qte.active) {
        mirror.suspend('original_qte_priority');releaseAim('original_qte_priority');qte.step(current,latest);
      } else {
        qte.step(current,latest);aimStep(current);
      }
      check();
    } catch(error) {
      fault=fault||error;
      try {close('controller_fault');}
      catch(cleanupError) {emit({status:'native153_tactical_cleanup_fault',error:String(cleanupError)});}
      throw fault;
    }
  }
  function afterTick(driverTick) {
    if(closed)return;
    try {
    check();const current=tick();
    if(current===lastAfter||latest&&current-latest.tick<3)return;
    if(current<lastAfter)throw Error('Native tactical observation clock moved backwards');
    lastAfter=current;
    observationTiming.begin(current);
    try {
    latest=observationTiming.measure('observer_snapshot',()=>observer.snapshot(current));slamRows=observationTiming.measure('slam_cover_snapshot',()=>slamCover.snapshot(current,latest));latestThreat=observationTiming.measure('threats_snapshot',()=>threats.snapshot(current));latestBreak=observationTiming.measure('breakable_snapshot',()=>breakable.snapshot(current));
    latestCore=observationTiming.measure('core_snapshot',()=>coreObserver.snapshot(latest.monster?.targetMonsterId));
    latestInterceptionThreats=observationTiming.measure('interception_threat_snapshot',()=>interceptionThreats.snapshot(latest));
    latest.friendlyProjectiles=latestInterceptionThreats.friendlyProjectiles||[];
    if(interceptionPolicy?.waveId===6302006&&latest.monsters.some(m=>m.entityId===latest.monster?.targetMonsterId&&String(m.tableId)===String(interceptionPolicy.monsterId)))
      observationTiming.measure('mirror_state_audit',()=>mirror.observeNativeState({tick:current,phase:latestCore.phase,partStates:latest.monster.partStates||[],ownerId:latest.monster.targetMonsterId,timelineRows:slamRows}));
    if(latestInterceptionThreats.supported!==true)throw Error('Original interception threat snapshot failed');samples++;
    if(latest.supported!==true||latestThreat.supported!==true||latestBreak.supported!==true)throw Error('Original tactical native snapshot failed');
    observationTiming.measure('observation_signature_and_emit',()=>{
    const next=JSON.stringify({qte:latest.qte,monster:latest.monster,
      break:latestBreak.monsters.map(owner=>[owner.entityId,owner.playing,owner.nativeIsAllBreak,
        owner.colliders?.map(collider=>[collider.colliderId,collider.type?.name,collider.liveBreakTarget])])});
    if(next!==signature) {
      signature=next;transitions++;
      if(transitions<=256)emit({...latest,status:'original_tactical_observation_change',driverTick,ordinal:transitions,focusedFire:actions.snapshot()});
    }
    });
    check();
    } finally {observationTiming.end();}
    } catch(error) {
      fault=fault||error;
      try {close('tactical_observation_fault');}catch(cleanupError){emit({status:'native153_tactical_cleanup_fault',error:String(cleanupError)});}
      throw fault;
    }
  }
  function forwardEvent(event,dispatchOrdinal) {
    if(closed)return;
    ultraBarriers.forwardEvent(event);observer.observeSendEvent(event);threats.observeSendEvent(event,dispatchOrdinal);breakable.observeSendEvent(event);
    return shotWitness.beforeEvent(event);
  }
  function close(reason) {
    if(closed)return;
    const failures=mechanicsRunIndependentCleanup([
      ['passive_shot_witness',()=>shotWitness.close()],
      ['native_event_prefilter',()=>nativeEventFilter?.close()],
      ['ultra_barrier_observer',()=>ultraBarriers.cleanup()],
      ['harvester_target_cover',()=>harvesterCover.close(reason||'caller_closed')],
      ['mirror',()=>mirror.close(reason||'caller_closed')],
      ['directed_aim',()=>releaseAim(reason||'caller_closed')],
      ['qte',()=>qte.close(reason||'caller_closed')],
      ['cover',()=>{if((genericCovered||authored?.summary().covered)&&actions.controlFlag("forcedCover"))actions.setCover(false);}],
      ['pointer',()=>actions.pointer.clear()]
    ]);
    closed=true;
    if(failures.length){emit({status:'native153_tactical_cleanup_fault',reason,
      failures:failures.map(f=>({step:f.step,error:String(f.error)}))});throw failures[0].error;}
  }
  function finishBeforeCleanup() {
    if(closed)return;
    const failures=mechanicsRunIndependentCleanup([
      ['passive_shot_witness_before_cleanup',()=>shotWitness.close()],
      ['native_event_prefilter_before_cleanup',()=>nativeEventFilter?.close()],
      ['ultra_barrier_observer_before_cleanup',()=>ultraBarriers.cleanup()],
      ['harvester_target_cover_before_cleanup',()=>harvesterCover.beforeNativeCleanup()],
      ['mirror_before_cleanup',()=>mirror.beforeNativeCleanup()],
      ['directed_auto_before_cleanup',()=>{if(aimOwned)actions.restoreAutoAimBeforeNativeCleanup(priorAuto);}],
      ['qte_before_cleanup',()=>qte.beforeNativeCleanup()],
      ['clear_ownership',()=>{aimOwned=false;actorId=null;targetKey=null;priorAuto=null;targetSince=-1;genericCovered=false;}],
      ['pointer',()=>actions.pointer.clear()]
    ]);
    closed=true;if(failures.length)throw failures[0].error;
  }
  function onNativeFinish() {
    // SpotFinish already owns and disposes native team/input state. Do not call
    // commands/getters against the original destroyed context after cleanup.
    nativeEventFilter?.close();shotWitness.close();actions.pointer.clear();closed=true;originalFinishReleased=true;
  }
  const summary = () => ({policy,waveId:options.waveId,samples,transitions,closed,originalFinishReleased,
    current153NativeValidated:false,objective:'maximum_native_damage',interceptionPolicy,fault:fault?String(fault):null,unsupported:[...missing],
    nativeEventPrefilter:nativeEventFilter?.summary()||{enabled:false},passiveShotWitness:shotWitness.summary(),observationTiming:observationTiming.summary(),qte:qte.summary(),krakenQteFriendly:krakenFriendly.summary(),slamCover:slamCover.summary(),authoredCover:authored?.summary()||null,genericCoverCommands,genericCovered,
    directedAim:{owned:aimOwned,actorId,targetKey,commands:aimCommands},
    mirror:mirror.summary(),harvesterTargetCover:harvesterCover.summary(),ultraBarrierCoverage:latestUltraBarriers,interceptionThreats:interceptionThreats.summary(),moderniaWing:moderniaWing.summary(),observer:observer.summary(),coreObserver:coreObserver.summary(),threats:threats.summary(),breakable:breakable.summary(),pointer:actions.pointer.snapshot()});
  emit({status:'native_control_mode_selected',controlMode:policy,waveId:options.waveId,
    observesNativeState:true,issuesTacticalCommands:true,current153NativeValidated:false,
    source:'Original live QTE/Break/parts/projectile observations and original player commands'});
  function useEventPrefilter(filter){
    if(nativeEventFilter)throw Error('Native event prefilter already attached');
    nativeEventFilter=filter;return nativeEventFilter.activate(management);
  }
  return {inspectCurrentCoreGeometry:()=>coreObserver.inspectProjectileRay(latest?.monster?.targetMonsterId,null,null,()=>({queryNotRequested:true})),useEventPrefilter,beforeTick,afterTick,forwardEvent,afterEvent:token=>shotWitness.afterEvent(token),close,finishBeforeCleanup,onNativeFinish,check,summary,dispatchMethod:dispatch,
    retainUntilExit:[actions.pointer.listener]};
}

// A Unity-enabled core collider may briefly outlive its original active part.
// Match the same native snapshot's alive/active PartsData before aiming at it.
function mechanicsLiveCoreTargets(coreTargets,liveParts) {
  const parts=new Map(liveParts.filter(part=>typeof part.hp==='string'&&/^\d+$/.test(part.hp)&&
    BigInt(part.hp)>0n).map(part=>[part.partsType,part]));
  return coreTargets.filter(core=>core.nativeIsCore===true&&parts.has(core.partsType))
    .map(core=>({...core,nativePartActive:true,nativePartHp:parts.get(core.partsType).hp}));
}

// Source-scoped Kraken non-QTE Break circles require Wind under the authored
// elemental shield. ElementTable300001 is Wind (not enum/character-name guess).
// Seven-circle QuickTime is a separate native policy and stays unchanged.
function mechanicsEligibleDirectedActors(actors,targets,waveId) {
  if(!targets.some(t=>t.kind==="Break"))return actors;
  const required=typeof mechanicsInterceptionRequiredElement==='function'?mechanicsInterceptionRequiredElement(waveId):(waveId===6302009?300001:null);
  if(required===null)return actors;
  return actors.filter(actor=>Array.isArray(actor.casterElementIds)&&actor.casterElementIds.includes(required));
}

// Elemental interruption circles own input before offensive slipper coordination.
function mechanicsHasLiveDirectedBreak(snapshot) {
  return snapshot?.supported===true&&(snapshot.monsters||[]).some(owner=>
    owner.supported===true&&owner.playing===true&&!owner.nativeIsAllBreak&&
    (owner.colliders||[]).some(c=>c.liveBreakTarget===true&&c.type?.name==='Break'&&
      typeof c.hp==='string'&&/^\d+$/.test(c.hp)&&BigInt(c.hp)>0n));
}

// Cleanup is an input transaction: one failing native command must not skip
// restoration of other owners or approved auto preferences.
function mechanicsRunIndependentCleanup(steps) {
  const failures=[];
  for(const [step,run] of steps)try {run();}catch(error){failures.push({step,error});}
  return failures;
}


// Passive same-tick evidence only: no aiming, input, native-state or policy writes.
function mechanicsMirrorCoreProjectionWitness(core,parts,screen,project) {
  try {
    const targets=Array.isArray(core?.targets)?core.targets:[];
    const bounds=Array.isArray(core?.partTargets)?core.partTargets:[];
    return {nativePhase:core?.phase,nativeHasActiveCore:core?.nativeHasActiveCore,
      screen:{width:screen?.width,height:screen?.height},coreTargetCount:targets.length,
      limitedToFirstEight:targets.length>8,
      coreTargets:targets.slice(0,8).map(target=>{
        const matched=parts.filter(p=>p.partsType===target.partsType).map(p=>({partsType:p.partsType,hp:p.hp,worldPosition:p.worldPosition}));
        const b=bounds.find(p=>p.colliderId===target.colliderId&&p.ownerId===target.ownerId)||
          (target.nativeCoreBoundsCenter&&target.nativeCoreBoundsExtents?{world:target.nativeCoreBoundsCenter,extents:target.nativeCoreBoundsExtents,nativeColliderLive:true,nativeColliderEnabled:true}:null);
        const validBounds=Array.isArray(b?.world)&&b.world.length===3&&b.world.every(Number.isFinite)&&Array.isArray(b?.extents)&&b.extents.length===3&&b.extents.every(v=>Number.isFinite(v)&&v>0);
        const corners=[];
        if(validBounds)for(const x of [-1,1])for(const y of [-1,1])for(const z of [-1,1])
          corners.push(project(b.world.map((v,i)=>v+[x,y,z][i]*b.extents[i])));
        return {colliderId:target.colliderId,ownerId:target.ownerId,partsType:target.partsType,
          nativeIsCore:target.nativeIsCore,projection:project(target.world),matchedNativeParts:matched,
          hpAndWorldEligibility:matched.some(p=>typeof p.hp==='string'&&/^\d+$/.test(p.hp)&&BigInt(p.hp)>0n&&Array.isArray(p.worldPosition)&&p.worldPosition.length===3&&p.worldPosition.every(Number.isFinite)),
          bounds:b?{world:b.world,extents:b.extents,nativeColliderLive:b.nativeColliderLive,nativeColliderEnabled:b.nativeColliderEnabled}:null,
          boundsCornerProjections:corners};
      }),aabbCornerVisibilityDoesNotProveColliderRayHit:true,changesAim:false};
  } catch(error) {return {witnessUnavailable:String(error),changesAim:false};}
}

// Mirror actor input follows the selected native-priority target, not dormant lower-priority candidates.
function mechanicsDirectedCarryAimAllowed(waveId,targets,selectedTarget) {
  if(waveId===6302006)return ['Core','Part','AimAnchor'].includes(selectedTarget?.kind);
  return !targets.some(target=>['Break','Projectile','Mob'].includes(target.kind));
}

// Refresh moving edge/offscreen geometry on demand; on-screen center aim retains the original bounded observation cadence.
function mechanicsMirrorCoreGeometryRefreshWanted(core,projectWorld) {
  return core?.supported===true&&(core.targets||[]).some(target=>
    target.nativeColliderRaycastConfirmed===true||projectWorld(target.world).visible!==true);
}

// Optional actor preference must not cancel a real native charge already underway.
// Only original ammo progression or original state/charge end releases the guard.
function createMechanicsOptionalChargeHandoff(read,emit,enabled) {
  let pending=null,deferrals=0,completions=0;
  const cancel=reason=>{if(pending)emit({status:'original_optional_charge_handoff_end',reason,...pending});pending=null;};
  return {pending:()=>pending!==null,cancel,summary:()=>({enabled,pending,deferrals,completions}),
    defer(actorId,nextActorId,tick) {
      if(!enabled)return false;
      const state=read();
      if(!state||state.actorId!==actorId){cancel('original_focus_changed_or_absent');return false;}
      if(typeof state.weaponIdentity!=='string'||
          !Number.isSafeInteger(state.usedAmmoCount)||!Number.isFinite(state.currentChargeTime))throw Error('Original pending charge state unavailable');
      const liveCharge=state.inputType===2&&[2,3].includes(state.nativeInputType)&&state.stance===2&&
        typeof state.currentAmmo==='string'&&/^\d+$/.test(state.currentAmmo)&&BigInt(state.currentAmmo)>0n&&state.currentChargeTime>0;
      if(pending&&(pending.actorId!==actorId||pending.weaponIdentity!==state.weaponIdentity||
          state.usedAmmoCount!==pending.usedAmmoCount||!liveCharge)) {
        completions++;cancel(state.usedAmmoCount!==pending.usedAmmoCount?'original_ammo_progress':'original_charge_or_actor_state_ended');return false;
      }
      if(!liveCharge)return false;
      if(!pending) {pending={actorId,nextActorId,weaponIdentity:state.weaponIdentity,usedAmmoCount:state.usedAmmoCount,startedTick:tick};deferrals++;
        emit({status:'original_optional_charge_handoff_deferred',tick,...pending,nativeCurrentChargeTime:state.currentChargeTime});}
      else pending.nextActorId=nextActorId;
      return true;
    }};
}

// Passive host observation cost only. No native timer, RNG or control writes.
function createNativeObservationTiming(enabled,emit,limit=300,now=()=>Date.now()) {
  let active=false,completed=0,started=null,tick=null,reported=false,clockErrors=0,emitErrors=0;
  const rows=new Map();
  const stamp=()=>{try{const n=now();return Number.isFinite(n)?n:null;}catch(_){clockErrors++;return null;}};
  const add=(label,start)=>{
    const finish=stamp();
    if(start===null||finish===null||finish<start){clockErrors++;return;}
    if(!rows.has(label))rows.set(label,[]);
    rows.get(label).push(finish-start);
  };
  const summary=()=>({enabled,completed,limit,reported,clockErrors,emitErrors,
    clock:'JavaScript Date.now wall milliseconds; quantized, not native simulation dt',
    components:Object.fromEntries([...rows].map(([name,values])=>{
      const sorted=[...values].sort((a,b)=>a-b),n=sorted.length;
      return [name,{count:n,sumMs:values.reduce((a,b)=>a+b,0),maxMs:sorted[n-1],
        medianMs:n%2?sorted[(n-1)/2]:(sorted[n/2-1]+sorted[n/2])/2,
        p95Ms:sorted[Math.floor((n-1)*.95)]}];
    })),changesNativeClock:false,changesControls:false});
  return {
    begin(nativeTick){active=enabled&&completed<limit;if(active){tick=nativeTick;started=stamp();}},
    measure(label,read){
      if(!active)return read();
      const start=stamp();try{return read();}finally{add(label,start);}
    },
    end(){
      if(!active)return;add('total_after_tick',started);active=false;completed++;
      if(completed===limit&&!reported){reported=true;try{emit({status:'passive_observation_timing',lastNativeTick:tick,...summary()});}catch(_){emitErrors++;}}
    },
    summary
  };
}

// Passive diagnostic only. Captures primitive IDs before the original event can
// be pooled; observes registered original projectiles at the SAME dispatch return.
function createMechanicsMirrorShotWitness(runtime,management,aimBinding,emit,configuration={}) {
  const enabled=configuration.enabled===true&&configuration.waveId===6302006;
  if(!enabled)return {beforeEvent:()=>null,afterEvent(){},close(){},summary:()=>({enabled:false})};
  const names=configuration.nativeNameCodes,ids=[...aimBinding.bound.keys()];
  if(!Array.isArray(names)||names.length!==ids.length)throw Error('Passive witness original kit identity alignment missing');
  const neon=ids.filter((id,i)=>names[i]===5170);
  if(neon.length!==1)return {beforeEvent:()=>null,afterEvent(){},close(){},summary:()=>({enabled:false,reason:'exactly_one_original_Neon5170_required'})};
  const actorId=neon[0],limit=160,threadId=Process.getCurrentThreadId();
  const live=x=>x!=null&&!x.isNull(),c=n=>runtime.class('NK.Spot.'+n);
  const field=(k,n,t,o)=>{const f=k.field(n);if(f.isStatic||f.offset!==o||f.type.name!==t)throw Error('Passive projectile witness field changed: '+n);};
  const spawn=c('Event.Projectile.ProjectileSpawnEvent'),info=c('Logic.Character.SpotEntityInfo');
  const pcType=c('ProjectileContext'),projectile=c('Model.Projectile.SpotProjectile'),dataType=c('Weapon.Projectile.SpotProjectileData');
  const entity=c('Model.Common.SpotEntity'),character=c('Model.Character.SpotCharacter');
  for(const [k,n,t,o]of [[spawn,'CasterInfo',info.type.name,64],[spawn,'ProjectileInfo',info.type.name,72],
    [info,'EntityID','System.Int32',16],[entity,'Id','System.Int32',16],
    [pcType,'_projectileList','System.Collections.Generic.List<NK.Spot.Model.Projectile.SpotProjectile>',16],
    [pcType,'_addList','System.Collections.Generic.List<NK.Spot.Model.Projectile.SpotProjectile>',56],
    [projectile,'<Data>k__BackingField',dataType.type.name,104],
    [dataType,'<StartPos>k__BackingField','UnityEngine.Vector3',16],
    [dataType,'<TargetPos>k__BackingField','UnityEngine.Vector3',28],
    [dataType,'<Owner>k__BackingField',entity.type.name,72],
    [dataType,'<IsSkillShot>k__BackingField','System.Boolean',688]])field(k,n,t,o);
  const contexts=management.field('_contexts').value;
  const pc=invokeChecked(contexts.method('get_Item',1),contexts,[pcType.type.object.handle]);
  if(!live(pc)||pc.class.type.name!==pcType.type.name)throw Error('Passive original ProjectileContext missing');
  const seen=new Set();let closed=false,attempts=0,observed=0,missing=0,errors=0,wrongThread=0;
  const note=row=>{try{emit({status:'passive_original_projectile_fire_witness',actorId,nativeNameCode:5170,
    lifecycle:'original_Spawn_SendEventDefault_onLeave',changesControls:false,changesNativeMechanics:false,...row});}catch(_){errors++;}};
  const list=x=>{
    if(!live(x))return [];
    const sf=x.class.field('_size'),af=x.class.field('_items');
    if(sf.offset!==24||sf.type.name!=='System.Int32'||af.offset!==16||sf.isStatic||af.isStatic)throw Error('Passive original projectile List layout changed');
    const count=Number(x.field('_size').value);
    if(!Number.isSafeInteger(count)||count<0||count>8192)throw Error('Passive original projectile List bound');
    if(!count)return [];
    const items=x.field('_items').value;if(!live(items))throw Error('Passive original projectile backing array missing');
    const array=new Il2Cpp.Array(items.handle);if(array.length<count)throw Error('Passive original projectile array short');
    return Array.from({length:count},(_,i)=>array.get(i));
  };
  const nativeId=x=>{
    if(!live(x)||x.class.type.name!==info.type.name)throw Error('Passive original event entity info type changed');
    const id=Number(x.field('EntityID').value);if(!Number.isSafeInteger(id)||id<=0)throw Error('Passive original entity ID invalid');return id;
  };
  const xyz=(data,offset)=>{const p=data.handle.add(offset),v=[p.readFloat(),p.add(4).readFloat(),p.add(8).readFloat()];
    if(!v.every(Number.isFinite))throw Error('Passive native projectile position invalid');return v;};
  return {
    beforeEvent(event) {
      if(closed||attempts>=limit)return null;
      try {
        if(!live(event)||event.class.type.name!==spawn.type.name)return null;
        if(Process.getCurrentThreadId()!==threadId){wrongThread++;return null;}
        const owner=nativeId(event.field('CasterInfo').value);if(owner!==actorId)return null;
        const id=nativeId(event.field('ProjectileInfo').value);if(seen.has(id))return null;
        seen.add(id);attempts++;
        const intent=configuration.readIntent(),nativeTick=Number(management.field('_tickCount').value);
        return {projectileEntityId:id,casterEntityId:owner,spawnNativeTick:nativeTick,
          spawnNativePlaytime:Number(management.field('_playtime').value),spawnThreadId:threadId,
          cachedIntentAtSpawn:intent,
          cachedIntentAgeNativeTicks:Number.isSafeInteger(intent?.lastDirectedAim?.tick)?nativeTick-intent.lastDirectedAim.tick:null,
          cachedGeometryAgeNativeTicks:Number.isSafeInteger(intent?.lastDirectedAim?.nativeGeometryTick)?nativeTick-intent.lastDirectedAim.nativeGeometryTick:null,
          nativeAimAtSpawn:configuration.readNativeAim(actorId)};
      }catch(error){errors++;note({supported:false,reason:'spawn_entry_capture_unavailable',error:String(error)});return null;}
    },
    afterEvent(token) {
      if(closed||!token)return;
      let dataClassProof=null;
      try {
        if(Process.getCurrentThreadId()!==threadId){wrongThread++;note({...token,supported:false,reason:'dispatch_return_thread_changed'});return;}
        const matches=[];
        for(const name of ['_projectileList','_addList'])for(const p of list(pc.field(name).value)) {
          if(live(p)&&p.class.type.name===projectile.type.name&&Number(p.field('Id').value)===token.projectileEntityId)
            matches.push({projectile:p,location:name});
        }
        if(!matches.length){missing++;note({...token,supported:false,reason:'entity_not_in_either_original_list_at_dispatch_return',foundLocations:[]});return;}
        const p=matches[0].projectile;
        if(matches.some(m=>!m.projectile.handle.equals(p.handle)))throw Error('Passive duplicate native projectile identity');
        const data=p.field('<Data>k__BackingField').value;
        if(!live(data)){errors++;note({...token,supported:false,reason:'native_projectile_Data_null',nativeDataClass:null});return;}
        dataClassProof=mechanicsOriginalProjectileDataClassChain(data.class,dataType);
        if(dataClassProof.supported!==true){errors++;note({...token,supported:false,reason:'native_projectile_Data_not_assignable_to_verified_base',nativeDataClassProof:dataClassProof});return;}
        // Resolve inherited descriptors on the actual native class too. Never
        // accept a derived shadow field with a different base-layout offset.
        for(const [name,type,offset]of [['<StartPos>k__BackingField','UnityEngine.Vector3',16],
          ['<TargetPos>k__BackingField','UnityEngine.Vector3',28],
          ['<Owner>k__BackingField',entity.type.name,72],['<IsSkillShot>k__BackingField','System.Boolean',688]])
          field(data.class,name,type,offset);
        const owner=data.field('<Owner>k__BackingField').value;
        if(!live(owner)||owner.class.type.name!==character.type.name||Number(owner.field('Id').value)!==actorId)
          throw Error('Passive projectile actual owner differs from native Neon caster');
        const startPos=xyz(data,16),targetPos=xyz(data,28);
        const core=configuration.inspectCore(token.cachedIntentAtSpawn?.boundBossOwnerId,startPos,targetPos);
        observed++;note({...token,supported:true,nativeDataClassProof:dataClassProof,foundLocations:matches.map(m=>m.location),
          observedNativeTick:Number(management.field('_tickCount').value),observedNativePlaytime:Number(management.field('_playtime').value),
          nativeStartPos:startPos,nativeTargetPos:targetPos,nativeIsSkillShot:data.field('<IsSkillShot>k__BackingField').value===true,currentCoreQuery:core,
          lineMeaning:'straight initial native StartPos to TargetPos aim line, not measured velocity or entire curved/projectile trajectory',
          nativeAimAtDispatchReturn:configuration.readNativeAim(actorId)});
      }catch(error){errors++;note({...token,supported:false,reason:'dispatch_return_observation_unavailable',nativeDataClassProof:dataClassProof,error:String(error)});}
    },
    close(){closed=true;},
    summary:()=>({enabled:true,actorId,nativeNameCode:5170,limit,attempts,observed,missing,errors,wrongThread,closed,
      changesControls:false,changesNativeClock:false,delayedObservationRelabeledAtFire:false})
  };
}

// Original native Class.parent traversal, bounded and HANDLE-based. Names are
// diagnostic labels; acceptance requires the verified base Class identity.
function mechanicsOriginalProjectileDataClassChain(actual,base) {
  const chain=[],seen=new Set();let current=actual;
  for(let depth=0;depth<16;depth++) {
    if(!current||!current.handle||current.handle.isNull())return {supported:false,reason:'verified_base_absent_from_native_parent_chain',chain};
    const handle=current.handle.toString();
    if(seen.has(handle))return {supported:false,reason:'native_parent_chain_cycle',chain};
    seen.add(handle);chain.push({name:current.type.name,handle});
    if(current.handle.equals(base.handle))return {supported:true,actualClass:chain[0].name,
      verifiedBaseClass:base.type.name,verifiedBaseHandle:base.handle.toString(),chain};
    current=current.parent;
  }
  return {supported:false,reason:'native_parent_chain_depth_exceeded',chain};
}

// Native observation prefilter only: original dispatch, arguments, return and
// all native subscribers remain untouched. Only consumed events enter JS.
function createNativeTacticalEventPrefilter(runtime,management,dispatch,classes,forward,after,reportFault) {
  if(!Array.isArray(classes)||!classes.length||classes.length>64||new Set(classes).size!==classes.length)
    throw Error('Source-bound native event class allowlist required');
  const allowed=classes.map(name=>runtime.class(name).handle);
  const pointerSize=Process.pointerSize;if(pointerSize!==8||Process.arch!=='x64')throw Error('Native event filter requires original Win64 x64');
  const manager=Memory.alloc(pointerSize);manager.writePointer(management?management.handle:NULL);
  const array=Memory.alloc(pointerSize*allowed.length);allowed.forEach((p,i)=>array.add(i*pointerSize).writePointer(p));
  const count=Memory.alloc(4);count.writeU32(allowed.length);
  const active=Memory.alloc(4);active.writeU32(0);
  const counters=Memory.alloc(16);for(let i=0;i<4;i++)counters.add(i*4).writeU32(0);
  const pending=new Map();let tokenId=0,closed=false;
  const enter=new NativeCallback((event,ordinal)=>{
    try {
      const token=forward(new Il2Cpp.Object(event),ordinal);
      if(!token)return 0;
      tokenId++;if(tokenId>=0xffffffff)throw Error('Native event token bound exceeded');
      pending.set(tokenId,token);return tokenId;
    }catch(error){reportFault(error);return 0;}
  },'uint',['pointer','uint']);
  const leave=new NativeCallback(id=>{
    const token=pending.get(id);pending.delete(id);
    if(token)try{after(token);}catch(error){reportFault(error);}
  },'void',['uint']);
  const native=new CModule(`
#include <gum/guminterceptor.h>
extern gpointer expected_manager;
extern gpointer allowed_classes[];
extern guint allowed_count;
extern volatile gint active_flag;
extern volatile gint counters[];
extern gpointer original_object_get_class (gpointer object);
extern guint js_enter (gpointer event, guint ordinal);
extern void js_leave (guint token);
typedef struct { guint token; } EventInvocation;
static guint next_counter (volatile gint * pointer) {
  guint old = 1;
  __asm__ volatile ("lock xaddl %0, %1" : "+r" (old), "+m" (*pointer) : : "memory");
  return old + 1;
}
void on_enter (GumInvocationContext * ic) {
  EventInvocation * data = GUM_IC_GET_INVOCATION_DATA (ic, EventInvocation);
  data->token = 0;
  if (!active_flag) return;
  gpointer self = gum_invocation_context_get_nth_argument (ic, 0);
  gpointer event = gum_invocation_context_get_nth_argument (ic, 1);
  if (self != expected_manager || event == NULL) return;
  guint ordinal = next_counter (&counters[0]);
  gpointer klass = original_object_get_class (event);
  for (guint i = 0; i != allowed_count; i++) {
    if (klass == allowed_classes[i]) {
      next_counter (&counters[1]);
      data->token = js_enter (event, ordinal);
      return;
    }
  }
  next_counter (&counters[2]);
}
void on_leave (GumInvocationContext * ic) {
  EventInvocation * data = GUM_IC_GET_INVOCATION_DATA (ic, EventInvocation);
  if (data->token != 0) {
    next_counter (&counters[3]);
    js_leave (data->token);
    data->token = 0;
  }
}
`,{expected_manager:manager,allowed_classes:array,allowed_count:count,active_flag:active,counters,
    original_object_get_class:Process.getModuleByName('GameAssembly.dll').getExportByName('il2cpp_object_get_class'),
    js_enter:enter,js_leave:leave});
  let listener=null;
  return {get listener(){return listener;},
    activate(owner){
      if(closed||listener||!owner||owner.isNull())throw Error('Native event filter activation requires fresh live owner');
      manager.writePointer(owner.handle);
      listener=Interceptor.attach(dispatch.virtualAddress,{onEnter:native.on_enter,onLeave:native.on_leave});
      active.writeU32(1);return listener;
    },
    close(){if(closed)return;closed=true;active.writeU32(0);},
    dispatchCount:()=>counters.readU32(),
    summary:()=>({enabled:true,closed,allowedClassCount:classes.length,
      totalDispatches:counters.readU32(),forwardedToJs:counters.add(4).readU32(),
      ignoredByJs:counters.add(8).readU32(),pairedLeaves:counters.add(12).readU32(),pendingTokens:pending.size,
      originalObjectClassGetter:true,nativeDispatchSuppressed:false,nativeArgumentsOrReturnChanged:false}),
    // Keep C code, imported callbacks and data alive until script/process exit.
    nativeRoots:[native,enter,leave,manager,array,count,active,counters]};
}

function mechanicsNativeTacticalEventClasses(){return ["NK.Spot.Event.Character.AddedBarrierEvent", "NK.Spot.Event.Character.CoverTakeDamageEvent", "NK.Spot.Event.Common.OnEntityGetDamageEvent", "NK.Spot.Event.Monster.MonsterAllBreakColliderEvent", "NK.Spot.Event.Monster.MonsterAttackEvent", "NK.Spot.Event.Monster.MonsterBreakColliderActiveStartEvent", "NK.Spot.Event.Monster.MonsterBreakColliderActiveStartedEvent", "NK.Spot.Event.Monster.MonsterBreakColliderHurtEvent", "NK.Spot.Event.Monster.MonsterConditionEvent", "NK.Spot.Event.Monster.MonsterInActiveBreakColliderEvent", "NK.Spot.Event.Monster.MonsterSkillInterruptionEvent", "NK.Spot.Event.Projectile.ProjectileCreateEvent", "NK.Spot.Event.Projectile.ProjectileDespawnEvent", "NK.Spot.Event.Projectile.ProjectileSpawnEvent", "NK.Spot.Event.QuickTime.QuickTimeColliderEnabledEvent", "NK.Spot.Event.QuickTime.QuickTimeColliderHitEvent", "NK.Spot.Event.QuickTime.QuickTimeEndEvent", "NK.Spot.Event.QuickTime.QuickTimePresetEndEvent", "NK.Spot.Event.QuickTime.QuickTimePresetStartEvent", "NK.Spot.Event.QuickTime.QuickTimeStartEvent", "NK.Spot.Event.Summon.RemovedCharacterBarrierEvent"];}

// Original runtime_invoke exception semantics; no direct gameplay getter call.
// Compile before original OnInit. Every value is freshly read, no state cache.
function createNativeCheckedScalarReader() {
  if(Process.arch!=='x64'||Process.pointerSize!==8)throw Error('Checked scalar reader requires original Win64 ABI');
  const game=Process.getModuleByName('GameAssembly.dll');
  const native=new CModule(`
#include <gum/guminterceptor.h>
extern gpointer original_runtime_invoke(gpointer method,gpointer receiver,gpointer args,gpointer *exception);
extern gpointer original_object_unbox(gpointer object);
int read_checked_scalar(gpointer method,gpointer receiver,int kind,gpointer output) {
  gpointer exception=NULL;
  gpointer boxed=original_runtime_invoke(method,receiver,NULL,&exception);
  ((gpointer*)output)[1]=exception;
  if(exception!=NULL)return 1;
  if(boxed==NULL)return 2;
  gpointer value=original_object_unbox(boxed);
  if(value==NULL)return 3;
  if(kind==0)*(gint64*)output=(gint64)*(gint32*)value;
  else if(kind==1)*(gint64*)output=(gint64)*(guint8*)value;
  else if(kind==2)*(gint64*)output=*(gint64*)value;
  else return 4;
  return 0;
}
int read_checked_long_pair(gpointer first,gpointer second,gpointer receiver,gpointer output) {
  gpointer temporary[2];
  ((guint64*)output)[3]=0;
  int status=read_checked_scalar(first,receiver,2,temporary);
  ((gpointer*)output)[2]=temporary[1];
  if(status!=0)return status;
  ((gint64*)output)[0]=*((gint64*)temporary);
  ((guint64*)output)[3]=1;
  status=read_checked_scalar(second,receiver,2,temporary);
  ((gpointer*)output)[2]=temporary[1];
  if(status!=0)return status;
  ((gint64*)output)[1]=*((gint64*)temporary);
  return 0;
}`,{original_runtime_invoke:game.getExportByName('il2cpp_runtime_invoke'),original_object_unbox:game.getExportByName('il2cpp_object_unbox')});
  const readNative=new NativeFunction(native.read_checked_scalar,'int',['pointer','pointer','int','pointer']);
  const readPairNative=new NativeFunction(native.read_checked_long_pair,'int',['pointer','pointer','pointer','pointer']);
  let depth=0,calls=0;const buffers=[];
  function throwOriginal(method,exception){
    const text=Memory.alloc(8192);
    new NativeFunction(game.getExportByName('il2cpp_format_exception'),'void',['pointer','pointer','int'])(exception,text,8192);
    const error=Error(method.name+': '+text.readUtf8String());
    const addresses=Memory.alloc(8),count=Memory.alloc(4),uuid=Memory.alloc(8),image=Memory.alloc(8);
    addresses.writePointer(NULL);count.writeS32(0);uuid.writePointer(NULL);image.writePointer(NULL);
    new NativeFunction(game.getExportByName('il2cpp_native_stack_trace'),'void',['pointer','pointer','pointer','pointer','pointer'])(exception,addresses,count,uuid,image);
    const size=count.readS32(),frames=addresses.readPointer();error.nativeFrames=[];
    if(!frames.isNull()&&size>0&&size<1000)for(let i=0;i<Math.min(size,64);i++)error.nativeFrames.push(frames.add(i*8).readPointer().sub(game.base).toString());
    throw error;
  }
  return {read(method,self,kind){
    const code={int:0,bool:1,long:2}[kind];
    if(code===undefined||!self||self.isNull()||method.isStatic||method.parameters.length!==0)throw Error('Checked scalar getter receiver/signature differs');
    if(depth>=16)throw Error('Checked scalar getter reentrant bound exceeded');
    const index=depth++;let output=buffers[index];if(!output)output=buffers[index]=Memory.alloc(32);
    try{
      const status=readNative(method.handle,self.handle,code,output);calls++;
      if(status===1)throwOriginal(method,output.add(8).readPointer());
      if(status!==0)throw Error('Original scalar getter null/unsupported result: '+method.name+' status'+status);
      return kind==='bool'?output.readS64().toString()!=='0':kind==='long'?output.readS64().toString():output.readS32();
    }finally{depth--;}
  },bindLongPair(first,second){
    for(const method of [first,second])if(!method||method.isStatic||method.parameters.length!==0)throw Error('Checked scalar pair requires original instance no-arg getters');
    const handles=[first.handle,second.handle],methods=[first,second];
    return self=>{
      if(!self||self.isNull())throw Error('Checked scalar pair receiver differs');
      if(depth>=16)throw Error('Checked scalar getter reentrant bound exceeded');
      const index=depth++;let output=buffers[index];if(!output)output=buffers[index]=Memory.alloc(32);
      let failedIndex=0;
      try{
        const status=readPairNative(handles[0],handles[1],self.handle,output);failedIndex=status===0?1:output.add(24).readU32();calls+=failedIndex+1;
        if(status===1)throwOriginal(methods[failedIndex],output.add(16).readPointer());
        if(status!==0)throw Error('Original scalar getter null/unsupported result: '+methods[failedIndex].name+' status'+status);
        return {hp:output.readS64().toString(),maxHp:output.add(8).readS64().toString()};
      }catch(error){error.originalScalarPairIndex=failedIndex;throw error;}
      finally{depth--;}
    };
  },summary:()=>({calls,buffers:buffers.length,originalRuntimeInvoke:true,originalObjectUnbox:true}),roots:{native,readNative,readPairNative}};
}

// Passive diagnostic timestamps only; install AFTER existing original-method guards.
function installNativeLoadingTiming(emit) {
  const specs=[{"name":"NK.Spot.Presentation.UI.UIPopupControll.<HideLoading>d__3.MoveNext","rva":95592176,"prefix":"48895c2410488974242048894c2408574883ec500f297424","source":"loading-page-hide-source.json"},{"name":"NK.OverlayTransition.HideTransitionAsync","rva":121284144,"prefix":"48895c2408574883ec70803d8a145a0400488bda488bf975","source":"loading-overlay-hide-entry-source.json"},{"name":"NK.UI.Component.OverlayTransitionLazyController.HideTransition","rva":108515008,"prefix":"48895c2408574883ec30803d537d1c0500488bda488bf975","source":"loading-selected-lazy-hide-entry-source.json"},{"name":"NK.UI.Component.OverlayTransitionLazyController.HideTransitionFinished","rva":108514912,"prefix":"40534883ec20803db87d1c0500488bd97513488d0d67fb91","source":"loading-selected-lazy-finished-source.json"},{"name":"NK.OverlayTransitionView.<HideTransition>d__29.MoveNext","rva":121319664,"prefix":"48895c2410488974242048894c240857415641574883ec60","source":"loading-selected-view-hide-source.json"}];
  const game=Process.getModuleByName('GameAssembly.dll');
  let closed=false;const listeners=[],rows=specs.map(spec=>({...spec,enters:0,leaves:0,firstEnter:null,lastEnter:null,lastLeave:null}));
  const summary=()=>({closed,rows:rows.map(row=>({...row})),nativeStateWritten:false});
  const close=()=>{if(!closed){closed=true;for(const listener of listeners)listener.detach();emit({status:'native_loading_timing_closed',...summary()});}return summary();};
  // Validate ALL prefixes before attaching any callback, with no argument/return access.
  for(const spec of specs){const actual=Array.from(new Uint8Array(game.base.add(spec.rva).readByteArray(24)),v=>v.toString(16).padStart(2,'0')).join('');
    if(actual!==spec.prefix)throw Error('Original loading timing source differs: '+spec.name);}
  try {
    for(const row of rows)listeners.push(Interceptor.attach(game.base.add(row.rva),{
      onEnter(){if(closed)return;row.enters++;row.lastEnter=Date.now();if(row.firstEnter===null)row.firstEnter=row.lastEnter;
        if(row.enters<=2)emit({status:'native_loading_timing_entry',name:row.name,count:row.enters,wallMs:row.lastEnter});},
      onLeave(){if(closed)return;row.leaves++;row.lastLeave=Date.now();}
    }));
  }catch(error){close();throw error;}
  return {summary,close};
}

// Read-only metadata retrieval for a FUTURE already-owned probe. No method invocation.
function inspectOriginalRenderMetadata(emit) {
 const game=Process.getModuleByName('GameAssembly.dll');
 const roots=[['UnityEngine.CoreModule','UnityEngine.Rendering.OnDemandRendering'],['Cinemachine','Cinemachine.CinemachineBrain'],[null,'Spine.Unity.SkeletonAnimation'],[null,'Spine.Unity.SkeletonRenderer']];
 for(const [assemblyName,name]of roots){
  let cls=null,assembly=null;
  const assemblies=assemblyName?[Il2Cpp.domain.assembly(assemblyName)]:Il2Cpp.domain.assemblies;
  for(const candidate of assemblies){try{cls=candidate.image.class(name);assembly=candidate.name;break;}catch(_){}}
  if(!cls){emit({status:'render_metadata_missing',name,requestedAssembly:assemblyName});continue;}
  emit({status:'render_metadata_original',name,assembly,parent:cls.parent?.type.name||null,
   fields:cls.fields.map(f=>({name:f.name,type:f.type.name,offset:f.offset,isStatic:f.isStatic})),
   methods:cls.methods.filter(m=>name.includes('OnDemandRendering')||/Update|Render|Cull|Visible|Camera|Enable|Disable/.test(m.name)).map(m=>({name:m.name,returns:m.returnType.name,parameters:m.parameters.map(p=>p.type.name),isStatic:m.isStatic,
    rva:m.virtualAddress.isNull()?null:m.virtualAddress.sub(game.base).toString(),prefix24:m.virtualAddress.isNull()?null:Array.from(new Uint8Array(m.virtualAddress.readByteArray(24)),x=>x.toString(16).padStart(2,'0')).join('')}))});
 }
}

// Passive C listeners: no JS per invocation, no return/argument mutation.
function createNativeClockCallerCollector() {
 if(Process.arch!=='x64'||Process.pointerSize!==8)throw Error('Clock collector requires original Win64 x64');
 const bindings=[{"id": 0, "name": "fixedUnscaledDeltaTime", "rva": 139652144, "prefix": "4883ec28488b0515ae42034885c07513488d0d89696500e8"}, {"id": 1, "name": "fixedUnscaledTime", "rva": 139652192, "prefix": "4883ec28488b05d5ad42034885c07513488d0df9686500e8"}, {"id": 2, "name": "realtimeSinceStartup", "rva": 139652384, "prefix": "4883ec28488b0565ad42034885c07513488d0d016a6500e8"}, {"id": 3, "name": "realtimeSinceStartupAsDouble", "rva": 139652336, "prefix": "4883ec28488b059dad42034885c07513488d0d616a6500e8"}, {"id": 4, "name": "unscaledDeltaTime", "rva": 139652624, "prefix": "4883ec28488b052dac42034885c07513488d0d79676500e8"}, {"id": 5, "name": "unscaledTime", "rva": 139652720, "prefix": "4883ec28488b05b5ab42034885c07513488d0d91666500e8"}, {"id": 6, "name": "unscaledTimeAsDouble", "rva": 139652672, "prefix": "4883ec28488b05edab42034885c07513488d0de9666500e8"}];
 const game=Process.getModuleByName('GameAssembly.dll');
 const timeClass=Il2Cpp.domain.assembly('UnityEngine.CoreModule').image.class('UnityEngine.Time');
 // Every source/bounds guard must complete before the first attach.
 const addresses=bindings.map(row=>{
  if(!Number.isSafeInteger(row.rva)||row.rva<0||row.rva+24>game.size)throw Error('Clock getter outside original game module');
  const address=game.base.add(row.rva),range=Process.findRangeByAddress(address);
  const method=timeClass.method('get_'+row.name,0),returnType=row.name.endsWith('AsDouble')?'System.Double':'System.Single';
  if(method.name!=='get_'+row.name||!method.isStatic||method.parameters.length!==0||method.returnType.name!==returnType||!method.virtualAddress.equals(address))throw Error('Original Unity Time getter metadata changed: '+row.name);
  if(!range||!range.protection.includes('x'))throw Error('Clock getter is not executable');
  const bytes=Array.from(new Uint8Array(address.readByteArray(24)),x=>x.toString(16).padStart(2,'0')).join('');
  if(bytes!==row.prefix)throw Error('Clock getter source prefix changed: '+row.name);
  return address;
 });
 if(new Set(addresses.map(x=>x.toString())).size!==7)throw Error('Clock getter address alias');
 const active=Memory.alloc(4);active.writeU32(0);
 const inflight=Memory.alloc(4),lock=Memory.alloc(4),contention=Memory.alloc(4),overflow=Memory.alloc(4),bins=Memory.alloc(7*256*16),total=Memory.alloc(7*4),used=Memory.alloc(7*4);
 // Explicit initialization: imported writable buffers may contain arbitrary bytes.
 for(const [buffer,size]of [[inflight,4],[lock,4],[contention,4],[overflow,4],[bins,7*256*16],[total,7*4],[used,7*4]])buffer.writeByteArray(new Uint8Array(size));
 const native=new CModule("#include <gum/guminterceptor.h>\n#include <stdint.h>\n#define METHODS 7\n#define CAP 256\nextern volatile gint active_flag;\nextern volatile gint in_flight;\nextern volatile gint lock_word;\nextern volatile gint contention;\nextern volatile guint overflow;\ntypedef struct { gpointer caller; guint count; guint reserved; } Bin;\nextern Bin bins[METHODS][CAP];\nextern guint total[METHODS];\nextern guint used[METHODS];\nstatic int exchange(volatile gint *pointer) { gint old=1; __asm__ volatile (\"xchgl %0, %1\" : \"+r\" (old), \"+m\" (*pointer) : : \"memory\"); return old==0; }\nstatic int take_lock(void){return exchange(&lock_word);}\nstatic void increment(volatile gint *pointer){guint old=1;__asm__ volatile (\"lock xaddl %0, %1\" : \"+r\" (old), \"+m\" (*pointer) : : \"memory\");if(old==0xffffffffU)overflow=1;}\nstatic void release_lock(void) { __asm__ volatile (\"\" : : : \"memory\");lock_word=0; }\nstatic void observe(GumInvocationContext *ic,guint id) {\n increment(&in_flight);\n if(!active_flag)goto done;\n if(!take_lock()){increment(&contention);goto done;}\n if(!active_flag){release_lock();goto done;}\n gpointer caller=gum_invocation_context_get_return_address(ic);\n if(total[id]==0xffffffffU){overflow=1;release_lock();goto done;}total[id]++;\n guint slot=used[id];\n for(guint i=0;i<used[id];i++)if(bins[id][i].caller==caller){slot=i;break;}\n if(slot==CAP){overflow=1;release_lock();goto done;}\n if(slot==used[id]){bins[id][slot].caller=caller;used[id]++;}\n if(bins[id][slot].count==0xffffffffU)overflow=1;else bins[id][slot].count++;\n release_lock();\n done: { volatile gint *pointer=&in_flight;__asm__ volatile (\"lock decl %0\" : \"+m\" (*pointer) : : \"memory\"); }\n}\n// Output: contention, overflow, then per method total/used + CAP*(ptr,count,pad).\nint copy_stats(gpointer output) {\n if(active_flag||in_flight||!take_lock())return 0;\n if(in_flight){release_lock();return 0;}\n guint *p=(guint*)output;*p++=(guint)contention;*p++=overflow;\n for(guint id=0;id<METHODS;id++){\n  *p++=total[id];*p++=used[id];\n  Bin *out=(Bin*)p;for(guint i=0;i<CAP;i++)out[i]=bins[id][i];p=(guint*)(out+CAP);\n }\n release_lock();return 1;\n}\nvoid enter_0(GumInvocationContext *ic){observe(ic,0);}\nvoid enter_1(GumInvocationContext *ic){observe(ic,1);}\nvoid enter_2(GumInvocationContext *ic){observe(ic,2);}\nvoid enter_3(GumInvocationContext *ic){observe(ic,3);}\nvoid enter_4(GumInvocationContext *ic){observe(ic,4);}\nvoid enter_5(GumInvocationContext *ic){observe(ic,5);}\nvoid enter_6(GumInvocationContext *ic){observe(ic,6);}\n",{active_flag:active,in_flight:inflight,lock_word:lock,contention,overflow,bins,total,used});
 const bytes=8+7*(8+256*16),output=Memory.alloc(bytes);
 const copy=new NativeFunction(native.copy_stats,'int',['pointer']);
 let listeners=[],closed=false,started=false;
 const roots=[native,active,output,copy,lock,contention,overflow,bins,total,used,inflight];
 return {
  start(){
   if(closed||started)throw Error('Clock collector start requires fresh inactive instance');
   try{for(let i=0;i<7;i++)listeners.push(Interceptor.attach(addresses[i],{onEnter:native['enter_'+i]}));}
   catch(error){for(const listener of listeners)listener.detach();listeners=[];Interceptor.flush();throw error;}
   started=true;active.writeU32(1);
  },
  deactivate(){active.writeU32(0);},
  close(){if(closed)return;active.writeU32(0);for(const listener of listeners)listener.detach();listeners=[];Interceptor.flush();closed=true;},
  summary(){
   if(active.readU32()!==0)throw Error('Deactivate clock collector before snapshot');
   if(copy(output)!==1)throw Error('Clock collector snapshot busy; closure unproved');
   const contention=output.readU32(),overflow=output.add(4).readU32(),methods=[];
   for(let id=0;id<7;id++){
    const row=output.add(8+id*(8+256*16)),total=row.readU32(),used=row.add(4).readU32(),callers=[];
    if(used>256)throw Error('Clock collector bin count corrupt');
    for(let i=0;i<used;i++){
     const bin=row.add(8+i*16),address=bin.readPointer();
     const module=Process.findModuleByAddress(address);
     callers.push({returnAddress:address.toString(),callerModule:module?{name:module.name,rva:address.sub(module.base).toString()}:null,gameRva:address.compare(game.base)>=0&&address.compare(game.base.add(game.size))<0?address.sub(game.base).toString():null,count:bin.add(8).readU32()});
    }
    methods.push({...bindings[id],total,callers});
   }
   return {status:'passive_original_clock_callers',complete:contention===0&&overflow===0,contention,overflow,started,closed,methods,originalReturnsUntouched:true};
  },
  // Retained even after detach; never dispose code while listeners may execute.
  nativeRoots:roots
 };
}

function createNativeClockCallerDiagnostic(emit) {
  const collector=createNativeClockCallerCollector();let started=false,closed=false,startScope=null,endScope=null,result=null;
  const scope=phase=>({wallMs:Date.now(),nativeTick:phase?.tick??null,playTime:phase?.playTime??null,processState:phase?.lifecycle?.state??null});
  return {start(phase){
    if(started||closed)return;
    if(phase?.lifecycle?.state!==6)throw Error('Native clock caller collection requires originalPlaying');
    collector.start();started=true;startScope=scope(phase);
    emit({status:'native_clock_caller_scope_started',...startScope,collectorOnly:true,collectorReturnsUntouched:true,separateCoherentOverrideConfigured:globalThis.NATIVE153_COHERENT_CAPTURE_INPUT?.enabled===true});
  },close(phase,reason){
    if(closed)return result;closed=true;endScope=scope(phase);
    collector.deactivate();collector.close();
    try{result=collector.summary();const {originalReturnsUntouched,...collected}=result;result={...collected,collectorOnly:true,collectorReturnsUntouched:originalReturnsUntouched,separateCoherentOverrideActive:globalThis.NATIVE153_COHERENT_CAPTURE?.summary().applied===true,complete:result.complete&&result.started,startScope,endScope,reason};}
    catch(error){result={status:'passive_original_clock_callers',complete:false,error:String(error),startScope,endScope,reason,originalReturnsUntouched:true};}
    emit(result);return result;
  },summary:()=>({started,closed,startScope,endScope,result}),nativeRoots:collector.nativeRoots};
}

// Read-only loading diagnostics; never advances or skips a native coroutine.
function createNativeLoadingReadinessWitness(manager,emit) {
  const game=Process.getModuleByName('GameAssembly.dll');
  for(const [name,offset,type]of [['_presentations',40,'System.Collections.Generic.Dictionary<System.Type,NK.Spot.Presentation.Common.PresentationBase>'],['_isPause',193,'System.Boolean'],['_isFinish',194,'System.Boolean']]){
    const f=manager.class.field(name);
    if(f.isStatic||f.offset!==offset||f.type.name!==type)throw Error('Original loading readiness field differs '+name);
  }
  const getResource=manager.class.method('IsResourceLoad',0);
  const bytes=method=>Array.from(new Uint8Array(method.virtualAddress.readByteArray(24)),x=>x.toString(16).padStart(2,'0')).join('');
  if(!getResource.virtualAddress.equals(game.base.add(123749968))||bytes(getResource)!=='40534883ec60488bd9803d4f87340400754f488d0d270e8b'||
      getResource.isStatic||getResource.parameters.length||getResource.returnType.name!=='System.Boolean')throw Error('Original readiness getter signature/source differs');
  const invoke=(m,self)=>invokeChecked(m,self,[]),integer=value=>value.unbox().handle.readS32();
  const live=v=>v&&!v.isNull();let next=0,samples=0,closed=false,resourceCalls=0,resourceReady=null;const methods=new Map();
  const listener=Interceptor.attach(getResource.virtualAddress,{
    onEnter(args){this.owned=!closed&&args[0].equals(manager.handle);},
    onLeave(retval){if(this.owned&&!closed){resourceCalls++;resourceReady=(retval.toUInt32()&255)!==0;}}
  });
  const close=()=>{if(!closed){closed=true;listener.detach();}};
  function presentations(){
    const dictionary=manager.field('_presentations').value;
    if(!live(dictionary))throw Error('Original presentation dictionary missing');
    const count=integer(invoke(dictionary.method('get_Count',0),dictionary));
    if(!Number.isInteger(count)||count<0||count>64)throw Error('Original presentation count outside diagnostic bound');
    const values=invoke(dictionary.method('get_Values',0),dictionary);
    const cursor=invoke(values.method('GetEnumerator',0),values).unbox();
    const rows=[];
    for(let i=0;i<=count;i++){
      if(invoke(cursor.method('MoveNext',0),cursor).unbox().handle.readU8()===0)break;
      if(i===count)throw Error('Original presentation enumerator count differs');
      const object=invoke(cursor.method('get_Current',0),cursor);
      if(!live(object)){rows.push({supported:false,reason:'null_presentation'});continue;}
      const klass=object.class,key=klass.handle.toString();let method=methods.get(key),binding=null;
      if(!method){
        method=klass.method('get_IsLoadComplete',0);
        if(method.isStatic||method.parameters.length||method.returnType.name!=='System.Boolean'||method.virtualAddress.isNull()||
            method.virtualAddress.compare(game.base)<0||method.virtualAddress.compare(game.base.add(game.size))>=0)throw Error('Original presentation readiness getter unavailable');
        methods.set(key,method);
        binding={declaringType:method.class?.type.name||null,rva:method.virtualAddress.sub(game.base).toString(),
          prefix24:Array.from(new Uint8Array(method.virtualAddress.readByteArray(24)),x=>x.toString(16).padStart(2,'0')).join('')};
      }
      const pureLeaf=method.virtualAddress.equals(game.base.add(9178416))&&bytes(method).startsWith('0fb64118c3');
      rows.push({type:klass.type.name,entity:object.handle.toString(),ready:pureLeaf?invoke(method,object).unbox().handle.readU8()!==0:null,
        additionalOriginalGetterCall:pureLeaf,unsupportedOverride:!pureLeaf,binding});
    }
    if(rows.length!==count)throw Error('Original presentation count mismatch');
    return rows;
  }
  return {observe(phase){
    if(closed)return;
    if(phase.lifecycle.state===6){close();return;}
    const now=Date.now();if(now<next||samples>=16)return;next=now+1000;samples++;
    try{
      emit({status:'native_loading_readiness_sample',sample:samples,wallMs:now,nativeTick:phase.tick,playTime:phase.playTime,processState:phase.lifecycle.state,
        paused:manager.field('_isPause').value,finished:manager.field('_isFinish').value,
        originalResourceReady:resourceReady,originalResourceCallsObserved:resourceCalls,presentations:presentations(),nativeStateWritten:false});
    }catch(error){emit({status:'native_loading_readiness_unavailable',sample:samples,error:String(error),nativeStateWritten:false});}
  },close,summary:()=>({closed,samples,limit:16,originalResourceCallsObserved:resourceCalls,additionalPresentationCallsOnlySourceProvedLeaf:true,nativeStateWritten:false})};
}

function installNativePauseOwnerWitness(manager,emit) {
  const game=Process.getModuleByName('GameAssembly.dll'),specs=[['Pause',123758576,'40534883ec20803db965340400488bd9751f488d0ddf1d9a'],['Resume',123760160,'40534883ec20803d8c5f340400488bd97513488d0dffa7a0']];
  for(const [name,offset,type]of [['_isPause',193,'System.Boolean'],['_pauseCount',196,'System.Int32'],['_tickCount',100,'System.UInt32'],['_playtime',108,'System.Single']]){
    const field=manager.class.field(name);if(field.isStatic||field.offset!==offset||field.type.name!==type)throw Error('Original pause observer field differs '+name);
  }
  const methods=specs.map(([name,rva,prefix])=>{
    const method=manager.class.method(name,0),bytes=Array.from(new Uint8Array(method.virtualAddress.readByteArray(24)),x=>x.toString(16).padStart(2,'0')).join('');
    if(!method.virtualAddress.equals(game.base.add(rva))||bytes!==prefix||method.isStatic||method.parameters.length||method.returnType.name!=='System.Void')throw Error('Original pause lifecycle method differs '+name);
    return method;
  });
  const describe=address=>{const module=Process.findModuleByAddress(address);return {address:address.toString(),module:module?.name||null,rva:module?address.sub(module.base).toString():null};};
  const state=()=>({paused:manager.handle.add(193).readU8()!==0,pauseCount:manager.handle.add(196).readS32(),nativeTick:manager.handle.add(100).readU32(),playTime:manager.handle.add(108).readFloat()});
  let closed=false,count=0;const listeners=[];
  try{for(const method of methods)listeners.push(Interceptor.attach(method.virtualAddress,{
    onEnter(args){this.row=null;if(closed||!args[0].equals(manager.handle)||count>=64)return;try{
      count++;
      this.row={status:'native_pause_owner_entry',method:method.name,ordinal:count,wallMs:Date.now(),caller:describe(this.returnAddress),...state(),nativeStateWritten:false};
      try{this.row.stack=Thread.backtrace(this.context,Backtracer.ACCURATE).slice(0,16).map(describe);}
      catch(error){this.row.stackUnavailable=String(error);}
      emit(this.row);
    }catch(error){emit({status:'native_pause_owner_observation_error',error:String(error)});}},
    onLeave(){if(this.row)try{emit({status:'native_pause_owner_return',method:method.name,ordinal:this.row.ordinal,wallMs:Date.now(),...state(),nativeStateWritten:false});}catch(error){emit({status:'native_pause_owner_observation_error',error:String(error)});}}
  }));}catch(error){for(const listener of listeners)listener.detach();throw error;}
  return {close(){if(!closed){closed=true;for(const listener of listeners)listener.detach();emit({status:'native_pause_owner_closed',count,closed,nativeStateWritten:false});}},summary:()=>({closed,count,limit:64,nativeStateWritten:false})};
}

// Diagnostic original pose reads before native combat tick; no animation updates.
function createNativePoseClockWitness(runtime,pin,emit,readCoreGeometry) {
  if(typeof pin!=='function')throw Error('Original pose diagnostic needs bounded managed roots');
  const game=Process.getModuleByName('GameAssembly.dll'),unity=Il2Cpp.domain.assembly('UnityEngine.CoreModule').image;
  const animator=Il2Cpp.domain.assembly('UnityEngine.AnimationModule').image.class('UnityEngine.Animator');
  const at=(klass,name,arity,rva,returns,parameters,prefix)=>{
    const m=klass.method(name,arity),actual=Array.from(new Uint8Array(m.virtualAddress.readByteArray(24)),x=>x.toString(16).padStart(2,'0')).join('');
    if(!m.virtualAddress.equals(game.base.add(rva))||m.returnType.name!==returns||JSON.stringify(m.parameters.map(p=>p.type.name))!==JSON.stringify(parameters)||actual!==prefix)throw Error('Original pose clock source differs '+name);return m;
  };
  const stateMethod=at(animator,'GetCurrentAnimatorStateInfo',1,139220000,'UnityEngine.AnimatorStateInfo',['System.Int32'],'48895c24084889742410574883ec5033c00f57c90f110989');
  const speedMethod=at(animator,'get_speed',0,139234288,'System.Single',[],'40534883ec20488b053bd04803488bd94885c07513488d0d');
  const modeMethod=at(animator,'get_updateMode',0,139234800,'UnityEngine.AnimatorUpdateMode',[],'40534883ec20488b0503cd4803488bd94885c07513488d0d');
  if(stateMethod.isStatic||speedMethod.isStatic||modeMethod.isStatic)throw Error('Original Animator getter staticness differs');
  const stateClass=stateMethod.returnType.class,align=Memory.alloc(4);
  const size=new NativeFunction(game.getExportByName('il2cpp_class_value_size'),'int',['pointer','pointer'])(stateClass.handle,align);
  if(size!==36||align.readU32()!==4)throw Error('Original AnimatorStateInfo size/alignment differs');
  for(const [name,offset,type]of [['m_FullPath',24,'System.Int32'],['m_NormalizedTime',28,'System.Single'],['m_Length',32,'System.Single'],['m_Speed',36,'System.Single'],['m_SpeedMultiplier',40,'System.Single']]){
    const f=stateClass.field(name);if(f.isStatic||f.offset!==offset||f.type.name!==type)throw Error('Original AnimatorStateInfo field differs '+name);
  }
  const valid=unity.class('UnityEngine.Object').method('op_Implicit',1);requireKraken153Method(valid,0x85236e0);
  const time=unity.class('UnityEngine.Time'),clock={};
  for(const [name,rva,prefix]of [
    ['deltaTime',139652048,'4883ec28488b054dae42034885c07513488d0d09696500e8'],
    ['unscaledDeltaTime',139652624,'4883ec28488b052dac42034885c07513488d0d79676500e8'],
    ['time',139652576,'4883ec28488b052dac42034885c07513488d0da9666500e8'],
    ['unscaledTime',139652720,'4883ec28488b05b5ab42034885c07513488d0d91666500e8'],
    ['frameCount',139652240,'4883ec28488b05edad42034885c07513488d0d696a6500e8']]){
    const type=name==='frameCount'?'System.Int32':'System.Single',m=at(time,'get_'+name,0,rva,type,[],prefix);
    if(!m.isStatic)throw Error('Original clock getter staticness differs');
    const call=new NativeFunction(m.virtualAddress,name==='frameCount'?'int':'float',['pointer']);clock[name]=()=>call(m.handle);
  }
  const resolve=new NativeFunction(game.getExportByName('il2cpp_resolve_icall'),'pointer',['pointer']);
  const address=resolve(Memory.allocUtf8String('UnityEngine.Time::get_captureDeltaTime')),module=address.isNull()?null:Process.findModuleByAddress(address);
  if(!module||module.name.toLowerCase()!=='unityplayer.dll')throw Error('Original capture read binding unavailable');
  const capture=new NativeFunction(address,'float',[]);
  const controllerClass=runtime.class('NK.Spot.Monster.Animation.AnimController');
  const update=at(controllerClass,'AddDisabledAnimatorToUpdateList',2,105409024,'System.Void',['UnityEngine.Animator','System.Single'],'488bc4488958184889782055488d68a14881ec9000000080');
  if(update.isStatic)throw Error('Original animation update staticness differs');
  const root=controllerClass.field('RootAnimator');if(root.isStatic||root.offset!==48||root.type.name!=='UnityEngine.Animator')throw Error('Original animator root field differs');
  let closed=false,samples=0,seenOverflow=false,clockReads=0,lastSampleTick=-1;const actors=new Map();
  const listener=Interceptor.attach(update.virtualAddress,{
    onEnter(args){this.animator=null;if(!closed&&!args[0].isNull()&&!args[1].isNull()){this.owner=args[0];this.animator=args[1];}},
    onLeave(){if(closed||!this.animator)return;try{
      const key=this.animator.toString();if(actors.has(key))return;if(actors.size>=8){seenOverflow=true;return;}
      const owner=pin(new Il2Cpp.Object(this.owner)),value=pin(new Il2Cpp.Object(this.animator)),root=owner.field('RootAnimator').value;
      actors.set(key,{object:value,controller:this.owner.toString(),isRoot:root&&!root.isNull()&&root.handle.equals(this.animator)});
    }catch(error){emit({status:'original_pose_discovery_error',error:String(error)});}}
  });
  return {sample(phase){
    const interval=globalThis.NATIVE153_RENDER_INTERVAL_INPUT?.interval||1;
    const selected=interval>1?phase.tick%120<interval:phase.tick%60===0;
    if(closed||phase.lifecycle.state!==6||!selected||phase.tick===lastSampleTick||samples>=32)return;lastSampleTick=phase.tick;samples++;
    try{
      const clocks=Object.fromEntries(Object.entries(clock).map(([k,read])=>[k,read()]));clockReads+=5;clocks.captureDeltaTime=capture();
      const poses=[];
      for(const [id,item]of actors){
        if(invokeChecked(valid,null,[item.object.handle]).unbox().handle.readU8()===0){poses.push({id,alive:false});continue;}
        const info=invokeChecked(stateMethod,item.object,[intArg(0)]).unbox();
        poses.push({id,controller:item.controller,isRoot:item.isRoot,alive:true,
          fullPathHash:Number(info.field('m_FullPath').value),normalizedTime:Number(info.field('m_NormalizedTime').value),
          stateLength:Number(info.field('m_Length').value),stateSpeed:Number(info.field('m_Speed').value),stateSpeedMultiplier:Number(info.field('m_SpeedMultiplier').value),
          animatorSpeed:invokeChecked(speedMethod,item.object).unbox().handle.readFloat(),animatorUpdateMode:invokeChecked(modeMethod,item.object).unbox().handle.readS32()});
      }
      let currentCoreGeometry=null;try{if(typeof readCoreGeometry==='function')currentCoreGeometry=readCoreGeometry();}catch(error){currentCoreGeometry={supported:false,error:String(error)};}
      emit({status:'original_pose_clock_sample',sample:samples,wallMs:Date.now(),nativeTick:phase.tick,playTime:phase.playTime,
        sampledBeforeNativeTick:true,clocks,renderPhase:{interval,phase:clocks.frameCount%interval},currentCoreGeometry,coherentCapture:globalThis.NATIVE153_COHERENT_CAPTURE?.summary(),poses,rootLimitOverflow:seenOverflow,nativeStateWritten:false});
    }catch(error){emit({status:'original_pose_clock_unavailable',sample:samples,error:String(error),nativeStateWritten:false});}
  },close(){if(!closed){closed=true;listener.detach();emit({status:'original_pose_clock_closed',samples,clockGetterReadsIntroduced:clockReads,actors:actors.size,rootLimitOverflow:seenOverflow,nativeStateWritten:false});}},summary:()=>({closed,samples,actors:actors.size,rootLimitOverflow:seenOverflow,nativeStateWritten:false})};
}

// Metadata only. Caller supplies eight ALREADY resolved guarded original methods.
// Never initializes Method.virtualAddress: bridge initial getter invokes a cctor.
function createNativeClockOwnerLookup(guards) {
 if(Process.arch!=='x64'||Process.pointerSize!==8)throw Error('Clock owner lookup requires original x64');
 const game=Process.getModuleByName('GameAssembly.dll'),expected=[{"name": "UnityEngine.Time.get_fixedUnscaledDeltaTime", "rva": 139652144}, {"name": "UnityEngine.Time.get_fixedUnscaledTime", "rva": 139652192}, {"name": "UnityEngine.Time.get_realtimeSinceStartup", "rva": 139652384}, {"name": "UnityEngine.Time.get_realtimeSinceStartupAsDouble", "rva": 139652336}, {"name": "UnityEngine.Time.get_unscaledDeltaTime", "rva": 139652624}, {"name": "UnityEngine.Time.get_unscaledTime", "rva": 139652720}, {"name": "UnityEngine.Time.get_unscaledTimeAsDouble", "rva": 139652672}, {"name": "NK.Spot.Monster.Animation.AnimController.AddDisabledAnimatorToUpdateList", "rva": 105409024}],targetRvas=[9441648, 9446304, 10731184, 44531824, 45715152, 105409024, 115796912, 115825632, 116993952, 118991632, 136217952, 136263520, 138428848, 141909360, 100574976, 100577904, 114431376, 114431088];
 if(!Array.isArray(guards)||guards.length!==8)throw Error('Eight source-known method guards required');
 // Frozen bridge's initial accessor is NOT lazy-decorated. Only initialized
 // Method.virtualAddress replaces it with this exact original lazy wrapper.
 const descriptor=Object.getOwnPropertyDescriptor(Il2Cpp.Method.prototype,'virtualAddress');
 const initializedSource='function(){const C=n.call(this);return Object.defineProperty(this,e,{value:C,configurable:t.configurable,enumerable:t.enumerable,writable:!1}),C}';
 if(!descriptor||typeof descriptor.get!=='function'||descriptor.get.toString().replace(/\s/g,'')!==initializedSource.replace(/\s/g,''))throw Error('Original bridge virtualAddress descriptor is not proven initialized');
 let offset=null,reads=0;
 const sentinel=guards[0].resolvedVirtualAddress;
 const surrogate={handle:{add(value){if(offset!==null)throw Error('Original virtualAddress getter performed multiple offset reads');offset=Number(value);return {readPointer(){reads++;return sentinel;}};}}};
 if(descriptor.get.call(surrogate)!==sentinel||reads!==1||!Number.isSafeInteger(offset)||offset<0||offset>120||offset%8)throw Error('Original bridge MethodInfo offset proof failed');
 for(let i=0;i<8;i++){
  const g=guards[i],address=game.base.add(expected[i].rva);
  if(!g||g.name!==expected[i].name||!g.handle||g.handle.isNull()||!g.resolvedVirtualAddress||!g.resolvedVirtualAddress.equals(address)||!g.handle.add(offset).readPointer().equals(address))throw Error('Original source/bridge method pointer guard mismatch');
 }
 const symbols={};
 for(const name of ['domain_get_assemblies','assembly_get_image','image_get_class_count','image_get_class','class_get_methods'])symbols['original_'+name]=game.getExportByName('il2cpp_'+name);
 const native=new CModule("#include <gum/guminterceptor.h>\nextern gpointer original_domain_get_assemblies(gpointer domain,gsize *count);\nextern gpointer original_assembly_get_image(gpointer assembly);\nextern gsize original_image_get_class_count(gpointer image);\nextern gpointer original_image_get_class(gpointer image,gsize index);\nextern gpointer original_class_get_methods(gpointer klass,gpointer *iterator);\n#define TARGETS 18\n#define ALIASES 64\n// uint header[8] then per target uint64 count + pointer[64].\nint collect(gpointer domain,gpointer *targets,guint count,guint offset,gpointer output){\n guint *head=(guint*)output;gpointer *rows=(gpointer*)(head+8);\n for(guint i=0;i<8;i++)head[i]=0;\n for(guint i=0;i<TARGETS*(ALIASES+1);i++)rows[i]=NULL;\n if(!domain||count!=TARGETS||offset>120||offset%8){head[0]=1;return 0;}\n gsize ac=0;gpointer *assemblies=original_domain_get_assemblies(domain,&ac);\n if(!assemblies){head[0]=2;return 0;}if(ac>256){head[0]=3;return 0;}head[1]=(guint)ac;\n for(gsize a=0;a<ac;a++){\n  gpointer image=original_assembly_get_image(assemblies[a]);if(!image){head[0]=4;return 0;}\n  gsize cc=original_image_get_class_count(image);if(cc>1000000||head[2]+cc>1000000){head[0]=5;return 0;}head[2]+=(guint)cc;\n  for(gsize ci=0;ci<cc;ci++){\n   gpointer klass=original_image_get_class(image,ci);if(!klass){head[0]=6;return 0;}\n   gpointer iterator=NULL;guint mc=0;\n   for(;;){\n    gpointer method=original_class_get_methods(klass,&iterator);if(!method)break;\n    if(++mc>65536||++head[3]>4000000){head[0]=7;return 0;}\n    gpointer address=*((gpointer*)((char*)method+offset));\n    for(guint t=0;t<count;t++)if(address==targets[t]){\n     gpointer *row=rows+t*(ALIASES+1);gsize used=(gsize)row[0];\n     if(used==ALIASES){head[0]=8;return 0;}row[used+1]=method;row[0]=(gpointer)(used+1);head[4]++;\n    }\n   }\n  }\n }\n head[5]=1;return 1;\n}\n",symbols),collect=new NativeFunction(native.collect,'int',['pointer','pointer','uint','uint','pointer']);
 const targets=Memory.alloc(18*8),output=Memory.alloc(32+18*65*8);
 targetRvas.forEach((rva,i)=>{if(rva<0||rva>=game.size)throw Error('Clock owner target outside original game');targets.add(i*8).writePointer(game.base.add(rva));});
 return {lookup(domain){
   const ok=collect(domain.handle,targets,18,offset,output),status=output.readU32();
   const rows=targetRvas.map((rva,i)=>{
    const row=output.add(32+i*65*8),count=row.readU64().toNumber();if(count>64)throw Error('Clock owner result bound');
    const methods=[];for(let j=0;j<count;j++)methods.push(row.add((j+1)*8).readPointer());
    return {rva,methodHandles:methods};
   });
   return {complete:ok===1&&status===0&&output.add(20).readU32()===1,status,assemblies:output.add(4).readU32(),classes:output.add(8).readU32(),methods:output.add(12).readU32(),matches:output.add(16).readU32(),methodPointerOffset:offset,unmatchedTargetRvas:rows.filter(row=>row.methodHandles.length===0).map(row=>row.rva),methodInvocations:0,rows};
  },nativeRoots:[native,collect,targets,output,...Object.values(symbols)]};
}

function createNativeClockOwnerDiagnostic(runtime,emit) {
  const time=Il2Cpp.domain.assembly('UnityEngine.CoreModule').image.class('UnityEngine.Time');
  const names=['fixedUnscaledDeltaTime','fixedUnscaledTime','realtimeSinceStartup','realtimeSinceStartupAsDouble','unscaledDeltaTime','unscaledTime','unscaledTimeAsDouble'];
  const guards=names.map(name=>{const m=time.method('get_'+name,0);return {name:'UnityEngine.Time.get_'+name,handle:m.handle,resolvedVirtualAddress:m.virtualAddress};});
  const anim=runtime.class('NK.Spot.Monster.Animation.AnimController').method('AddDisabledAnimatorToUpdateList',2);
  guards.push({name:'NK.Spot.Monster.Animation.AnimController.AddDisabledAnimatorToUpdateList',handle:anim.handle,resolvedVirtualAddress:anim.virtualAddress});
  const lookup=createNativeClockOwnerLookup(guards);let done=false,result=null;const handles=new Map();
  return {resolve(){
    if(done)return result;done=true;const started=Date.now();
    try{
      const raw=lookup.lookup(Il2Cpp.domain);for(const row of raw.rows)handles.set(row.rva,row.methodHandles.slice());
      result={...raw,rows:raw.rows.map(row=>({rva:row.rva,methods:row.methodHandles.map(handle=>{
        const m=new Il2Cpp.Method(handle);return {className:m.class.type.name,name:m.name,returns:m.returnType.name,parameters:m.parameters.map(p=>p.type.name)};
      })})),status:'original_clock_owner_metadata',lookupStatus:raw.status,elapsedMs:Date.now()-started};
    }catch(error){result={status:'original_clock_owner_metadata',complete:false,error:String(error),elapsedMs:Date.now()-started};}
    emit(result);return result;
  },methodsFor(rva){if(!done)throw Error('Original owner metadata scan must complete first');return (handles.get(rva)||[]).map(handle=>new Il2Cpp.Method(handle));},nativeRoots:lookup.nativeRoots};
}

// One-time read-only original Update receiver/delegate witness. No invocation.
function createNativeHooksDelegateWitness(updateMethod,emit) {
 const game=Process.getModuleByName('GameAssembly.dll'),sources=[{"rva": 138428848, "prefix": "40534883ec20488b59184885db741e33c9e84aac1200488b43180f28c84c8b4328488b4b404883c4205b48ffe04883"}, {"rva": 138428976, "prefix": "48895c24084889742410574883ec20803ddd0b550300488b"}, {"rva": 138429152, "prefix": "48895c24084889742410574883ec20803d2e0b550300488b"}];
 const initializedSource='function(){const C=n.call(this);return Object.defineProperty(this,e,{value:C,configurable:t.configurable,enumerable:t.enumerable,writable:!1}),C}';
 const descriptor=Object.getOwnPropertyDescriptor(Il2Cpp.Method.prototype,'virtualAddress');
 if(!descriptor||typeof descriptor.get!=='function'||descriptor.get.toString().replace(/\s/g,'')!==initializedSource.replace(/\s/g,''))throw Error('Original bridge virtualAddress must already be initialized');
 if(Process.arch!=='x64'||Process.pointerSize!==8||typeof emit!=='function')throw Error('Delegate witness requires original x64 and receipt sink');
 for(const source of sources){
  if(source.rva<0||source.rva+source.prefix.length/2>game.size)throw Error('Delegate witness source outside original game');
  const p=game.base.add(source.rva),range=Process.findRangeByAddress(p);
  const bytes=Array.from(new Uint8Array(p.readByteArray(source.prefix.length/2)),x=>x.toString(16).padStart(2,'0')).join('');
  if(!range||!range.protection.includes('x')||bytes!==source.prefix)throw Error('Original Hooks source prefix changed');
 }
 const klass=updateMethod.class;
 if(klass.type.name!=='MonoBehaviourCallbackHooks'||updateMethod.name!=='Update'||updateMethod.isStatic||updateMethod.parameters.length||updateMethod.returnType.name!=='System.Void'||!updateMethod.virtualAddress.equals(game.base.add(0x84041b0)))throw Error('Original Hooks.Update metadata changed');
 const delegate=Il2Cpp.corlib.class('System.Delegate'),multicast=Il2Cpp.corlib.class('System.MulticastDelegate');
 const field=(owner,name,offset,type)=>{
  const f=owner.field(name);
  if(f.isStatic||f.isThreadStatic||f.offset<16||f.offset%8!==0||f.type.name!==type)throw Error('Original delegate field layout changed: '+owner.type.name+'.'+name);
  return f;
 };
 const targetField=field(delegate,'m_target',32,'System.Object'),methodField=field(delegate,'method',40,'System.IntPtr');
 const methodPtrField=field(delegate,'method_ptr',16,'System.IntPtr'),invokeField=field(delegate,'invoke_impl',24,'System.IntPtr');
 const membersField=field(multicast,'delegates',104,'System.Delegate[]');
 const fields=klass.fields.filter(f=>!f.isStatic&&f.offset===24);
 if(fields.length!==1||fields[0].isThreadStatic||!delegate.isAssignableFrom(fields[0].type.class))throw Error('Original Hooks offset24 delegate field missing/ambiguous');
 const updateDelegateField=fields[0],invoke=updateDelegateField.type.class.method('Invoke',1);
 if(invoke.isStatic||invoke.returnType.name!=='System.Void'||invoke.parameters.length!==1||invoke.parameters[0].type.name!=='System.Single')throw Error('Original Hooks callback signature differs');
 let listener=null,active=false,started=false,closed=false,receipt=null;const receivers=new Set(),receipts=[];
 const read=(f,o)=>f.withHolder(o).value;
 const describe=method=>{const address=method.virtualAddress;return {handle:method.handle.toString(),className:method.class.type.name,name:method.name,isStatic:method.isStatic,returns:method.returnType.name,parameters:method.parameters.map(p=>p.type.name),address:address.toString(),rva:address.compare(game.base)>=0&&address.compare(game.base.add(game.size))<0?address.sub(game.base).toString():null};};
 function capture(receiver){
  const owner=new Il2Cpp.Object(receiver);
  if(!owner.class.handle.equals(klass.handle))throw Error('Original Hooks actual receiver class differs');
  const root=read(updateDelegateField,owner),nodes=[],invocations=[],path=new Set();
  const walk=(value,depth)=>{
   if(value.isNull())throw Error('Original multicast member is null');
   if(depth>8||nodes.length>=64)throw Error('Original delegate witness bound exceeded');
   const identity=value.handle.toString();if(path.has(identity))throw Error('Original delegate list contains cycle');path.add(identity);
   if(!delegate.isAssignableFrom(value.class))throw Error('Original callback is not delegate');
   const method=read(methodField,value),target=read(targetField,value);
   const node={identity,className:value.class.type.name,target:target.isNull()?null:{identity:target.handle.toString(),className:target.class.type.name},method:method.isNull()?null:describe(new Il2Cpp.Method(method)),methodPtr:read(methodPtrField,value).toString(),invokeImpl:read(invokeField,value).toString(),depth};
   nodes.push(node);
   if(!multicast.isAssignableFrom(value.class))throw Error('Original delegate is not multicast-compatible');
   const members=read(membersField,value);
   if(members.isNull()){invocations.push(node);path.delete(identity);return;}
   const length=members.length;if(!Number.isSafeInteger(length)||length<1||length>64)throw Error('Original delegate invocation array bound');
   for(let i=0;i<length;i++)walk(members.get(i),depth+1);path.delete(identity);
  };
  if(!root.isNull())walk(root,0);
  return {supported:true,scope:'first_original_Update_per_receiver_only',receiver:receiver.toString(),receiverClass:owner.class.type.name,delegateField:{name:updateDelegateField.name,offset:24,type:updateDelegateField.type.name},delegateLayouts:[targetField,methodField,methodPtrField,invokeField,membersField].map(f=>({name:f.name,offset:f.offset,type:f.type.name})),rootDelegate:root.handle.toString(),nodes,invocations,methodInvocations:0,delegateInvocations:0};
 }
 const detach=()=>{active=false;if(listener){listener.detach();listener=null;}};
 return {start(){
  if(closed||started)throw Error('Delegate witness needs fresh explicit start');started=true;active=true;
  listener=Interceptor.attach(updateMethod.virtualAddress,{onEnter(args){
   if(!active)return;const key=args[0].toString();if(receivers.has(key))return;receivers.add(key);
   try{receipt={status:'original_hooks_delegate_witness',threadId:Process.getCurrentThreadId(),...capture(args[0])};}
   catch(error){receipt={status:'original_hooks_delegate_witness',supported:false,error:String(error.stack||error),methodInvocations:0,delegateInvocations:0};}
   receipts.push(receipt);if(receivers.size>=8)detach();emit(receipt);
  }});
 },close(){detach();closed=true;},summary:()=>({started,closed,attempted:receipt!==null,receiversAttempted:receivers.size,receiverLimit:8,receipt,receipts}),nativeRoots:[updateMethod,klass,delegate,multicast,targetField,methodField,methodPtrField,invokeField,membersField,updateDelegateField]};
}

// Source-proved Win64 generic method context arrives in RDX at these two entries.
// Both original prologues dereference RDX+0x20 as the generic declaring class.
// Metadata observations only: no method invocation or retained native receiver.
function installNativeGenericClockOwnerWitness(emit) {
  const game=Process.getModuleByName('GameAssembly.dll'),specs=[
    {rva:0x2b98ed0,prefix:'48895c2418574883ec20488b4220488bda488bf9f6803201'},
    {rva:0x2a78070,prefix:'48895c2410564883ec20803d639fe90800488bf2488bd975'}];
  for(const s of specs){
    s.address=game.base.add(s.rva);
    const bytes=Array.from(new Uint8Array(s.address.readByteArray(24)),x=>x.toString(16).padStart(2,'0')).join('');
    if(bytes!==s.prefix)throw Error('Original generic clock owner source differs '+s.rva);
  }
  const handles=new Set(),listeners=[];let closed=false,overflow=false,observations=0,errors=0;
  try{for(const s of specs)listeners.push(Interceptor.attach(s.address,{onEnter(args){
    if(closed)return;
    const key=args[1].toString();if(handles.has(key))return;
    if(handles.size>=16){overflow=true;return;}handles.add(key);
    try{
      if(args[1].isNull())throw Error('Original generic owner MethodInfo is null');
      const method=new Il2Cpp.Method(args[1]);
      if(!method.virtualAddress.equals(s.address))throw Error('Original generic owner method pointer differs');
      observations++;
      emit({status:'original_generic_clock_owner',rva:s.rva,methodInfo:key,className:method.class.type.name,
        name:method.name,returns:method.returnType.name,isStatic:method.isStatic,parameters:method.parameters.map(p=>p.type.name),nativeStateWritten:false,methodInvoked:false});
    }catch(error){errors++;emit({status:'original_generic_clock_owner_unavailable',rva:s.rva,error:String(error),nativeStateWritten:false});}
  }}));}catch(error){for(const listener of listeners)listener.detach();throw error;}
  return {close(){if(closed)return;closed=true;for(const listener of listeners)listener.detach();emit({status:'original_generic_clock_owner_closed',observations,errors,overflow});},
    summary:()=>({closed,observations,errors,overflow})};
}

// Read-only metadata; compile before runtime measurement, lookup once after original metadata readiness.
function createNativeCutSceneSkipClassLookup(guard) {
 if(Process.arch!=='x64'||Process.pointerSize!==8)throw Error('Cutscene class lookup requires x64');
 const game=Process.getModuleByName('GameAssembly.dll'),known=game.base.add(139652144);
 // Current153 MethodInfo pointer offset0 independently guarded by an already resolved original method.
 if(!guard||guard.name!=='UnityEngine.Time.get_fixedUnscaledDeltaTime'||!guard.handle||guard.handle.isNull()||!guard.resolvedVirtualAddress||!guard.resolvedVirtualAddress.equals(known)||!guard.handle.readPointer().equals(known))throw Error('Original current153 MethodInfo guard failed');
 const symbols={};
 for(const n of ['domain_get_assemblies','assembly_get_image','image_get_class_count','image_get_class','class_get_name'])symbols['original_'+n]=game.getExportByName('il2cpp_'+n);
 const code=`#include <gum/guminterceptor.h>
extern gpointer original_domain_get_assemblies(gpointer domain,gsize *count);
extern gpointer original_assembly_get_image(gpointer assembly);
extern gsize original_image_get_class_count(gpointer image);
extern gpointer original_image_get_class(gpointer image,gsize index);
extern const char* original_class_get_name(gpointer klass);
int match(const char *s){const char *n="MonsterCutSceneSkip";if(!s)return 0;for(guint i=0;s[i]&&i<4096;i++){guint j=0;while(n[j]&&s[i+j]&&s[i+j]==n[j])j++;if(!n[j])return 1;}return 0;}
int collect(gpointer domain,gpointer output){guint *h=(guint*)output;gpointer *rows=(gpointer*)(h+8);for(guint i=0;i<8;i++)h[i]=0;for(guint i=0;i<16;i++)rows[i]=NULL;
 if(!domain){h[0]=1;return 0;}gsize ac=0;gpointer *a=original_domain_get_assemblies(domain,&ac);if(!a||ac>256){h[0]=2;return 0;}h[1]=ac;
 for(gsize ai=0;ai<ac;ai++){gpointer image=original_assembly_get_image(a[ai]);if(!image){h[0]=3;return 0;}gsize cc=original_image_get_class_count(image);if(cc>1000000||h[2]+cc>1000000){h[0]=4;return 0;}h[2]+=cc;
 for(gsize ci=0;ci<cc;ci++){gpointer k=original_image_get_class(image,ci);if(!k){h[0]=5;return 0;}if(match(original_class_get_name(k))){if(h[3]>=16){h[0]=6;return 0;}rows[h[3]++]=k;}}}h[4]=1;return 1;}`;
 const module=new CModule(code,symbols),collect=new NativeFunction(module.collect,'int',['pointer','pointer']);let closed=false,done=false;
 return {lookup(domain){if(closed||done)throw Error('Cutscene metadata lookup is closed or already used');done=true;
  const output=Memory.alloc(32+16*8),start=Date.now(),ok=collect(domain.handle||domain,output),status=output.readU32();
  if(!ok||status||output.add(16).readU32()!==1)throw Error('Original class lookup incomplete: '+status);
  const rows=[];for(let i=0;i<output.add(12).readU32();i++){
   const c=new Il2Cpp.Class(output.add(32+i*8).readPointer());
   rows.push({className:c.namespace?c.namespace+'.'+c.name:c.name,parent:c.parent?c.parent.type.name:null,fields:c.fields.map(f=>({name:f.name,type:f.type.name,offset:f.offset})),constructors:c.methods.filter(m=>m.name==='.ctor').map(m=>{const address=m.handle.readPointer();return {name:m.name,returns:m.returnType.name,parameters:m.parameters.map(p=>({name:p.name,type:p.type.name})),rva:address.isNull()?null:address.compare(game.base)>=0&&address.compare(game.base.add(game.size))<0?address.sub(game.base).toString():null};})});
  }
  return {status:'original_monster_cutscene_skip_class_metadata',complete:true,assemblies:output.add(4).readU32(),classes:output.add(8).readU32(),matches:rows.length,rows,elapsedMs:Date.now()-start,methodInvocations:0};
 },close(){if(closed)return;closed=true;module.dispose();}};
}
