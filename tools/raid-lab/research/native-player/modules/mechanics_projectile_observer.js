// Passive, exact-client character-projectile occurrence check.
// GameAssembly SHA-256: 2df7134a6a9c3a8dbbde88402fc8d16d1d6c3f4c2d5e262bea78c3d78b96dd02.
// Install after IL2CPP initialization and before original battle ticks. Never
// changes return values, events, projectile objects, physics, or dispatch.
function installMechanicsProjectileObserver(runtime, management, emit) {
  if (!runtime || typeof runtime.class !== "function" || !management ||
      typeof emit !== "function")
    throw new Error("Projectile observer needs original runtime, management, and sink");

  const context = runtime.class("NK.Spot.ProjectileContext");
  const weapon = runtime.class("NK.Spot.Model.Character.Weapon.SpotWeaponData");
  const projectile = runtime.class("NK.Spot.Model.Projectile.SpotProjectile");
  const event = runtime.class("NK.Spot.Event.Projectile.ProjectileCreateEvent");
  const eventData = runtime.class("NK.Spot.Event.Projectile.ProjectileData");
  const entity = runtime.class("NK.Spot.Model.Common.SpotEntity");
  const onCreate = context.method("OnProjectileCreate", 1);
  const getBullet = weapon.method("GetBulletModel", 2);
  const setCollider = projectile.method("SetCollider", 2);
  const exact = (actual, expected, name) => {
    if (Number(actual) !== expected)
      throw new Error("Installed " + name + " mismatch: " + Number(actual).toString(16));
  };
  exact(onCreate.relativeVirtualAddress, 0x06142db0, "OnProjectileCreate RVA");
  exact(getBullet.relativeVirtualAddress, 0x063b3a10, "GetBulletModel RVA");
  exact(setCollider.relativeVirtualAddress, 0x06374100, "SetCollider RVA");
  exact(event.field("Data").offset, 64, "ProjectileCreateEvent.Data offset");
  exact(event.field("IsCharacter").offset, 72, "ProjectileCreateEvent.IsCharacter offset");
  exact(eventData.field("OwnerId").offset, 16, "ProjectileData.OwnerId offset");
  exact(entity.field("Id").offset, 16, "SpotEntity.Id offset");
  exact(projectile.field("_collider").offset, 152, "SpotProjectile._collider offset");
  exact(projectile.field("<ResourcePrefab>k__BackingField").offset, 168,
    "SpotProjectile.ResourcePrefab offset");

  const MAX_SAMPLES = 30;
  const counters = { create:0, characterCreate:0, otherCreate:0,
    getBullet:0, getBulletNull:0, setCollider:0, setColliderNull:0,
    sampled:0, omittedSamples:0 };
  let firstFailure = null;
  const active = new Map();
  const characterByOwnerId = new Map();
  const live = pointer => pointer !== null && pointer !== undefined && !pointer.isNull();
  const fail = (site, error) => {
    if (firstFailure === null) firstFailure = {site, error:String(error)};
  };
  const stack = () => {
    const id = Process.getCurrentThreadId();
    let result = active.get(id);
    if (!result) { result = []; active.set(id, result); }
    return result;
  };
  const current = () => {
    const entries = stack();
    return entries.length ? entries[entries.length - 1] : null;
  };
  const clock = () => ({
    tick:Number(management.field("_tickCount").value),
    playTime:Number(management.field("_playtime").value)
  });
  const publish = record => {
    // Monster projectiles are counted, but the bounded evidence budget is for
    // the character-origin path whose omitted controller is under test.
    if (record.character !== true) return;
    if (counters.sampled >= MAX_SAMPLES) { counters.omittedSamples++; return; }
    counters.sampled++;
    try { emit({status:"original_projectile_occurrence", ...record}); }
    catch (error) { fail("emit", error); }
  };

  Interceptor.attach(onCreate.virtualAddress, {
    onEnter(args) {
      counters.create++;
      const frame = {ordinal:counters.create, character:null, ownerId:null,
        bulletModelCalled:false, bulletModelNull:null,
        setColliderCalled:false, sourcePrefabNull:null,
        modelColliderNull:null, modelResourcePrefabNull:null};
      stack().push(frame);
      try {
        if (!live(args[1])) throw new Error("null ProjectileCreateEvent");
        frame.character = args[1].add(72).readU8() !== 0;
        if (frame.character) counters.characterCreate++;
        else counters.otherCreate++;
        const data = args[1].add(64).readPointer();
        frame.ownerId = live(data) ? data.add(16).readS32() : null;
        if (frame.character) {
          const key = frame.ownerId === null ? "null" : String(frame.ownerId);
          characterByOwnerId.set(key, (characterByOwnerId.get(key) || 0) + 1);
        }
        frame.start = clock();
      } catch (error) { fail("OnProjectileCreate.onEnter", error); }
    },
    onLeave(_) {
      const frames = stack();
      const frame = frames.pop();
      if (!frame) { fail("OnProjectileCreate.onLeave", "unpaired entry"); return; }
      try { publish(frame); }
      catch (error) { fail("OnProjectileCreate.onLeave", error); }
    }
  });

  Interceptor.attach(getBullet.virtualAddress, {
    onEnter(args) {
      counters.getBullet++;
      this.frame = current();
      try {
        this.sourceEntityId = live(args[1]) ? args[1].add(16).readS32() : null;
        if (this.frame) {
          this.frame.bulletModelCalled = true;
          this.frame.bulletSourceEntityId = this.sourceEntityId;
        }
      } catch (error) { fail("GetBulletModel.onEnter", error); }
    },
    onLeave(retval) {
      try {
        const missing = !live(retval);
        if (missing) counters.getBulletNull++;
        if (this.frame) this.frame.bulletModelNull = missing;
      } catch (error) { fail("GetBulletModel.onLeave", error); }
    }
  });

  Interceptor.attach(setCollider.virtualAddress, {
    onEnter(args) {
      counters.setCollider++;
      this.frame = current();
      this.model = args[0];
      try {
        const missing = !live(args[2]);
        if (this.frame) {
          this.frame.setColliderCalled = true;
          this.frame.sourcePrefabNull = missing;
        }
      } catch (error) { fail("SetCollider.onEnter", error); }
    },
    onLeave(_) {
      try {
        if (!live(this.model)) throw new Error("null SpotProjectile receiver");
        const colliderMissing = !live(this.model.add(152).readPointer());
        const resourceMissing = !live(this.model.add(168).readPointer());
        if (colliderMissing) counters.setColliderNull++;
        if (this.frame) {
          this.frame.modelColliderNull = colliderMissing;
          this.frame.modelResourcePrefabNull = resourceMissing;
        }
      } catch (error) { fail("SetCollider.onLeave", error); }
    }
  });

  return {
    snapshot:() => ({status:"original_projectile_occurrence_summary",
      counts:{...counters}, characterByOwnerId:Object.fromEntries(characterByOwnerId),
      activeCreateFrames:[...active.values()].reduce(
        (sum, frames) => sum + frames.length, 0), firstFailure}),
    checkFault:() => { if (firstFailure) throw new Error(
      "Projectile observer " + firstFailure.site + ": " + firstFailure.error); }
  };
}
