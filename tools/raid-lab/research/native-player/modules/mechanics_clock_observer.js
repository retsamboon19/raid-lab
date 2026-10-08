// Read-only clock/geometry samples for the exact installed Kraken mechanics fixture.
// GameAssembly SHA-256: 2df7134a6a9c3a8dbbde88402fc8d16d1d6c3f4c2d5e262bea78c3d78b96dd02.
// Required globals: Il2Cpp, invokeChecked, intArg.
// Call sample("before", n) immediately before original UpdateSpot tick n and
// sample("after", n) immediately after that same tick (n is one-based).
// No Animator.Update, Physics.Simulate, transform writes or synthetic results.
function createMechanicsClockObserver(runtime, geometryState, management, pin, emit) {
  const present = value => value != null && !value.isNull();
  const requireObject = (value, name, retain = false) => {
    if (!present(value)) throw new Error("Clock observer missing original " + name);
    if (retain) pin(value);
    return value;
  };
  const call = (method, instance = null, args = []) =>
    invokeChecked(method, instance, args);
  const integer = (value, name) => {
    if (!Number.isInteger(value)) throw new Error("Invalid original " + name + ": " + value);
    return value;
  };
  const finite = (value, name) => {
    if (!Number.isFinite(value)) throw new Error("Invalid original " + name + ": " + value);
    return value;
  };
  const readInt = (method, instance = null, args = []) =>
    integer(call(method, instance, args).unbox().handle.readS32(), method.name);
  const readFloat = (method, instance = null, args = []) =>
    finite(call(method, instance, args).unbox().handle.readFloat(), method.name);
  const count = list => readInt(list.method("get_Count", 0), list);
  const item = (list, index) =>
    requireObject(call(list.method("get_Item", 1), list, [intArg(index)]),
      "list item " + index);
  const nameOf = component => {
    const go = requireObject(call(component.method("get_gameObject", 0),
      component), "collider GameObject");
    const name = requireObject(call(go.method("get_name", 0), go),
      "collider GameObject name");
    return new Il2Cpp.String(name.handle).content;
  };
  const position = transform => {
    const boxed = requireObject(call(transform.method("get_position", 0), transform),
      "Transform.position");
    const pointer = boxed.unbox().handle;
    return [0, 4, 8].map((offset, index) =>
      finite(pointer.add(offset).readFloat(), "position[" + index + "]"));
  };

  if (!runtime || typeof runtime.class !== "function" ||
      !geometryState || !geometryState.instances ||
      !present(geometryState.instances.monster_controller) ||
      !present(management) || typeof pin !== "function" ||
      typeof emit !== "function" || typeof intArg !== "function" ||
      typeof invokeChecked !== "function") {
    throw new Error("Clock observer requires live original geometry, management and bridge helpers");
  }
  const unity = Il2Cpp.domain.assembly("UnityEngine.CoreModule").image;
  const animation = Il2Cpp.domain.assembly("UnityEngine.AnimationModule").image;
  const time = unity.class("UnityEngine.Time");
  const stateInfoClass = animation.class("UnityEngine.AnimatorStateInfo");
  const animBase = runtime.class("NK.Spot.Monster.Animation.AnimController");
  const monsterType = runtime.class("NK.Spot.Presentation.MonsterPrefabController").type.object;
  const go = geometryState.instances.monster_controller;
  const controller = requireObject(call(go.method("GetComponent")
    .overload("System.Type"), go, [monsterType.handle]),
    "MonsterPrefabController component");
  // This exact client's Time metadata exposes fixedUnscaledTime, not fixedTime.
  const fixedUnscaledTimeMethod = time.method("get_fixedUnscaledTime", 0);

  let boss = null;
  let firstBossTick = null;
  function bindBoss() {
    if (boss) return true;
    const monsters = controller.field("_monsterList").value;
    if (!present(monsters)) return false;
    let match = null;
    for (let index = 0, total = count(monsters); index < total; ++index) {
      const monster = item(monsters, index);
      const parts = call(monster.method("get_PartsData", 0), monster);
      if (!present(parts)) continue;
      const colliderDatas = requireObject(parts.field("_colliderDatas").value,
        "MonsterPartsPrefabData._colliderDatas");
      const found = {};
      for (let j = 0, n = count(colliderDatas); j < n; ++j) {
        const data = item(colliderDatas, j);
        const collider = requireObject(data.field("Collider").value,
          "MonsterColliderData.Collider");
        const name = nameOf(collider);
        if (name === "core_col_01" || name === "break_col_10") {
          if (found[name]) throw new Error("Duplicate original Kraken collider " + name);
          found[name] = collider;
        }
      }
      if (!found.core_col_01 && !found.break_col_10) continue;
      if (!found.core_col_01 || !found.break_col_10)
        throw new Error("Partial original Kraken collider binding");
      if (match) throw new Error("Ambiguous original Kraken monster binding");
      const animController = requireObject(call(monster.method(
        "get_AnimController", 0), monster), "MonsterAnimController", true);
      const animator = requireObject(animBase.field("RootAnimator")
        .withHolder(animController).value, "AnimController.RootAnimator", true);
      const coreTransform = requireObject(call(found.core_col_01.method(
        "get_transform", 0), found.core_col_01), "core_col_01 Transform", true);
      const breakTransform = requireObject(call(found.break_col_10.method(
        "get_transform", 0), found.break_col_10), "break_col_10 Transform", true);
      pin(monster);
      match = {monster, animator, coreTransform, breakTransform};
    }
    if (!match) return false;
    boss = match;
    emit({status:"mechanics_clock_boss_bound",
      colliders:["core_col_01", "break_col_10"],
      originalAnimator:true, originalMonsterList:true});
    return true;
  }

  function sample(phase, tick) {
    if (phase !== "before" && phase !== "after")
      throw new Error("Clock observer phase must be before or after");
    integer(tick, "clock tick");
    if (tick < 1) throw new Error("Clock observer tick is one-based");
    if (!bindBoss()) return {pending:true, reason:"original Kraken monster not loaded"};
    // Anchor only on a before sample so the first 16 ticks have complete pairs.
    if (firstBossTick === null) {
      if (phase !== "before") return null;
      firstBossTick = tick;
    }
    if (!((tick >= firstBossTick && tick < firstBossTick + 16) ||
          tick === 300 || tick === 600)) return null;

    const animator = boss.animator;
    const stateBox = requireObject(call(animator.method(
      "GetCurrentAnimatorStateInfo", 1), animator, [intArg(0)]),
      "Animator.GetCurrentAnimatorStateInfo(0)");
    const state = stateBox.unbox();
    const movement = boss.monster.field("_colliderMovementData").value;
    const movementPresent = present(movement);
    const clock = {
      frameCount: readInt(time.method("get_frameCount", 0)),
      time: readFloat(time.method("get_time", 0)),
      fixedUnscaledTime: readFloat(fixedUnscaledTimeMethod),
      deltaTime: readFloat(time.method("get_deltaTime", 0)),
      unscaledDeltaTime: readFloat(time.method("get_unscaledDeltaTime", 0))
    };
    const result = {
      status:"mechanics_clock_sample", phase, tick, firstBossTick,
      managementTick: integer(Number(management.field("_tickCount").value),
        "management._tickCount"),
      managementPlayTime: finite(Number(management.field("_playtime").value),
        "management._playtime"),
      unityTime:clock,
      coreCol01WorldPosition: position(boss.coreTransform),
      breakCol10WorldPosition: position(boss.breakTransform),
      animatorEnabled: !!call(animator.method("get_enabled", 0), animator)
        .unbox().handle.readU8(),
      animatorUpdateMode: readInt(animator.method("get_updateMode", 0), animator),
      animatorSpeed: readFloat(animator.method("get_speed", 0), animator),
      animatorStateFullPathHash: readInt(stateInfoClass.method(
        "get_fullPathHash", 0), state),
      animatorStateNormalizedTime: readFloat(stateInfoClass.method(
        "get_normalizedTime", 0), state),
      colliderMovementListPresent: movementPresent,
      colliderMovementCount: movementPresent ? count(movement) : null
    };
    emit(result);
    return result;
  }
  return {sample};
}
