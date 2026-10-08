// Isolated cover experiment, triggered by original node230; no fixed-time
// dodge schedule. Release requires projectile resolution and native Idle after
// the follow-up casting sequence; missile disappearance alone is insufficient.
function createMechanicsKrakenCoverProbe(actions,emit) {
  let armed=false,covered=false,completed=false,sawProjectile=false;
  let attack=null,coverTick=null,releaseTick=null;
  let observedCasting=false;
  let releaseAmmo=null,resumeChecked=false;
  const seen=new Set();
  function step(tick,observation,threat) {
    if (!observation || !threat) return;
    if (!threat.supported) throw new Error("Native threat observation unavailable");
    if (completed) {
      if (!resumeChecked && tick>=releaseTick+15) {
        resumeChecked=true;
        const state=actions.snapshot();
        emit({status:"native_cover_probe_resume_readback",tick,releaseTick,state,
          firingResumed:state.squad.some(unit=>unit.usedAmmoCount>
            releaseAmmo.find(prior=>prior.entityId===unit.entityId).usedAmmoCount)});
      }
      return;
    }
    if (!armed && threat.latestAttack && threat.latestAttack.attackNodeId===230) {
      attack=threat.latestAttack;
      armed=true;
    }
    if (!armed) return;
    const condition=observation.latestCondition;
    if (condition && condition.tick>=attack.tick &&
        ["FireCasting","Fire"].includes(condition.condition.name)) observedCasting=true;
    if (!covered) {
      // Three original ticks reaction to a live event, not future simulation.
      if (tick-attack.tick<3) return;
      const before=actions.snapshot();
      if (before.forcedCover || before.inputType===2)
        throw new Error("Cover probe initial input ownership is not original-auto");
      actions.setCover(true);covered=true;coverTick=tick;
      emit({status:"native_cover_probe_entered",tick,attack,
        squadBefore:observation.squad,nativeAfter:actions.snapshot()});
    }
    for (const projectile of threat.activeBossProjectiles) {
      // All observed boss missiles are retained, including unknown skill
      // associations. This conservative probe never guesses a resolved threat.
      if (projectile.spawnTick>=attack.tick && threat.latestCreate &&
          threat.latestCreate.tick>=attack.tick && threat.latestCreate.skillId===532033)
        sawProjectile=true;
      seen.add(projectile.projectileId);
    }
    if (sawProjectile && threat.allBossActiveProjectileIds.length===0 &&
        threat.pendingUnlinkedCreate===null && condition && condition.tick>=attack.tick &&
        condition.condition.name==="Idle") {
      const before=actions.snapshot();
      releaseAmmo=before.squad;
      actions.setCover(false);covered=false;completed=true;releaseTick=tick;
      emit({status:"native_cover_probe_released",tick,coverTick,
        observedProjectileIds:[...seen],squadAfter:observation.squad,
        nativeBefore:before,nativeAfter:actions.snapshot(),threat,condition,observedCasting});
    }
  }
  function summary() {
    return {armed,covered,completed,sawProjectile,attack,coverTick,releaseTick,
      observedProjectileIds:[...seen],observedCasting,resumeChecked,
      scope:"isolated_node230_whole_squad_cover"};
  }
  return {step,summary};
}
