// Passive original startup-state trace for the exact five-unit Kraken fixture.
// sample(0) runs before UpdateSpot tick 1; sample(1..20) defaults to after
// the corresponding native tick. Pass phase="before" at completed-tick index
// 1..19 in later Update callbacks for paired before/after timing samples.
// No RNG draws, setter calls, event dispatch, hooks, or object construction.
function createMechanicsStartupStateObserver(runtime, management, loadedTeam,
    geometry, pin, emit) {
  const client = "2df7134a6a9c3a8dbbde88402fc8d16d1d6c3f4c2d5e262bea78c3d78b96dd02";
  if (!runtime || !management || management.isNull() || !loadedTeam ||
      loadedTeam.isNull() || !geometry || !geometry.live ||
      geometry.installedDllSha256 !== client ||
      !Array.isArray(geometry.live.actors) ||
      typeof pin !== "function" || typeof emit !== "function" ||
      typeof mechanicsRequestedEntityId !== "function" ||
      typeof invokeChecked !== "function" || typeof intArg !== "function")
    throw new Error("Original startup observer requires exact live fixture and bridge helpers");
  const request = globalThis.MECHANICS_REQUEST;
  const requestSha256 = globalThis.MECHANICS_REQUEST_SHA256;
  if (!request || !Array.isArray(request.characters) ||
      request.characters.length !== 5 ||
      request.characters.filter(actor => actor.nameCode === 5099).length !== 1 ||
      !request.encounter || !Number.isSafeInteger(request.encounter.randomSeed) ||
      request.encounter.randomSeed < 1 || request.encounter.randomSeed > 2147483647 ||
      typeof requestSha256 !== "string" || !/^[0-9a-f]{64}$/.test(requestSha256))
    throw new Error("Original startup observer request identity changed");
  const requestedEntityId=mechanicsRequestedEntityId(5099);
  const requestedSeed=request.encounter.randomSeed;
  const game = Process.getModuleByName("GameAssembly.dll");
  const at = (method, rva, label) => {
    if (!method.virtualAddress.equals(game.base.add(rva)))
      throw new Error("Installed startup method changed: " + label);
    return method;
  };
  const call = (method, self = null, args = []) => invokeChecked(method, self, args);
  const present = value => value != null && !value.isNull();
  const required = (value, label) => {
    if (!present(value)) throw new Error("Original startup " + label + " is null");
    return value;
  };
  const bits = new DataView(new ArrayBuffer(4));
  const f32 = value => {
    if (!Number.isFinite(value)) throw new Error("Original startup float is non-finite");
    bits.setFloat32(0, value, true);
    return {value, bits:"0x"+bits.getUint32(0,true).toString(16).padStart(8,"0")};
  };
  const floatResult = (method, self = null) =>
    f32(call(method, self).unbox().handle.readFloat());
  const intResult = (method, self = null) =>
    call(method, self).unbox().handle.readS32();
  const boolResult = (method, self = null) =>
    call(method, self).unbox().handle.readU8() !== 0;
  const statResult = (method, self) =>
    call(method, self).unbox().handle.readS64().toString();
  const obscuredFloatClass = Il2Cpp.domain.assembly("ACTk.Runtime").image
    .class("CodeStage.AntiCheat.ObscuredTypes.ObscuredFloat");
  const decryptFloat = at(obscuredFloatClass.method("op_Implicit")
    .overload("CodeStage.AntiCheat.ObscuredTypes.ObscuredFloat"),
    0x008A96C0,"ObscuredFloat.op_Implicit");
  const obscuredFloatResult = (method, self) => {
    const obscured = call(method,self);
    if (!present(obscured)) throw new Error("Original obscured float getter returned null");
    return f32(call(decryptFloat,null,[obscured.unbox().handle])
      .unbox().handle.readFloat());
  };
  const fieldOffset = (klass, name, offset) => {
    if (klass.field(name).offset !== offset)
      throw new Error("Installed startup field changed: " + klass.name + "." + name);
  };
  const unity = Il2Cpp.domain.assembly("UnityEngine.CoreModule").image;
  const time = unity.class("UnityEngine.Time");
  const unityRandom = unity.class("UnityEngine.Random");
  const cine = Il2Cpp.domain.assembly("Cinemachine").image
    .class("Cinemachine.CinemachineCore");
  const getTime = at(time.method("get_time",0),0x08275390,"Time.time");
  const getFrame = at(time.method("get_frameCount",0),0x08275240,"Time.frameCount");
  const getDelta = at(time.method("get_deltaTime",0),0x08275180,"Time.deltaTime");
  const getUnscaled = at(time.method("get_unscaledDeltaTime",0),
    0x082753C0,"Time.unscaledDeltaTime");
  const getUnityState = at(unityRandom.method("get_state",0),
    0x0826B9D0,"Random.state");
  const randomStateClass = unityRandom.nested("State");
  for (const [name,offset] of [["s0",0x10],["s1",0x14],
    ["s2",0x18],["s3",0x1C]]) fieldOffset(randomStateClass,name,offset);
  const cineOverride = cine.field("CurrentTimeOverride");
  if (!cineOverride.isStatic || cineOverride.offset !== 0x24)
    throw new Error("Installed Cinemachine override field changed");
  const staticGet = new NativeFunction(game.getExportByName(
    "il2cpp_field_static_get_value"),"void",["pointer","pointer"]);
  const cineBuffer = Memory.alloc(4);
  const cineTime = () => {
    staticGet(cineOverride.handle,cineBuffer);
    return f32(cineBuffer.readFloat());
  };
  const resolve = new NativeFunction(game.getExportByName(
    "il2cpp_resolve_icall"),"pointer",["pointer"]);
  const capturePointer = resolve(Memory.allocUtf8String(
    "UnityEngine.Time::get_captureDeltaTime"));
  const captureModule = capturePointer.isNull() ? null :
    Process.findModuleByAddress(capturePointer);
  if (!captureModule || captureModule.name.toLowerCase() !== "unityplayer.dll")
    throw new Error("Original Unity capture-time getter unavailable");
  const getCapture = new NativeFunction(capturePointer,"float",[]);

  const characterClass = runtime.class("NK.Spot.Model.Character.SpotCharacter");
  const weaponClass = runtime.class("NK.Spot.Model.Character.Weapon.SpotWeaponData");
  const skillClass = runtime.class("NK.Spot.Model.Character.Skill.SpotSkill");
  const aimInfoClass = runtime.class("NK.Spot.Model.Character.Aim.SpotCharacterAimInfo");
  const uiAimClass = runtime.class("NK.Spot.Presentation.UI.UIAim");
  const randomClass = runtime.class("NK.Spot.Common.SpotRandom");
  const recordClass = Il2Cpp.domain.assembly("NK.Runtime.StaticData").image.class(
    "NK.StaticData.StaticDataLayer.StaticInfo.CharacterSkillStaticInfo");
  for (const [klass,name,offset] of [
    [characterClass,"<CharacterStaticInfo>k__BackingField",0x70],
    [characterClass,"<DefaultWeaponData>k__BackingField",0xC8],
    [characterClass,"<CurrentWeaponData>k__BackingField",0xD0],
    [characterClass,"<AimInfo>k__BackingField",0xE0],
    [characterClass,"<UltimateSkill>k__BackingField",0x98],
    [characterClass,"<NormalSkillList>k__BackingField",0xA0],
    [characterClass,"<UsedAmmoCount>k__BackingField",0x100],
    [characterClass,"<SerialUsedAmmo>k__BackingField",0x104],
    [characterClass,"<ShotHitNum>k__BackingField",0x144],
    [characterClass,"<ShotPelletHitNum>k__BackingField",0x164],
    [skillClass,"<RecordData>k__BackingField",0x20],
    [skillClass,"<CurrentCooltime>k__BackingField",0x28],
    [aimInfoClass,"_aimControl",0x58],
    [uiAimClass,"_target",0x48],
    [recordClass,"<TableId>k__BackingField",0x10],
    [recordClass,"<Resource_name>k__BackingField",0x28],
    [randomClass,"_shared",0],
    [randomClass,"_currSeed",0x10],
    [randomClass,"<Random>k__BackingField",0x18],
    [randomClass,"<DrawCount>k__BackingField",0x20],
    [management.class,"_tickCount",0x64],
    [management.class,"_playtime",0x6C],
    [management.class,"_deltaTime",0x70],
    [management.class,"<SpotRandomSeed>k__BackingField",0x7C],
    [loadedTeam.class,"_isAutoModeAim",0x28],
    [loadedTeam.class,"_isAutoModeSkill",0x29]]) fieldOffset(klass,name,offset);
  const systemRandomClass = Il2Cpp.corlib.class("System.Random");
  fieldOffset(systemRandomClass,"_inext",0x10);
  fieldOffset(systemRandomClass,"_inextp",0x14);

  const staticInfo = Il2Cpp.domain.assembly("NK.Runtime.StaticData").image.class(
    "NK.StaticData.StaticDataLayer.StaticInfo.CharacterStaticInfo");
  const getNameCode = at(staticInfo.method("get_NameCode",0),0x04D4BD00,
    "CharacterStaticInfo.NameCode");
  const characterMethods = {
    stance:at(characterClass.method("get_StanceType",0),0x03B558B0,"Character.StanceType"),
    reloading:at(characterClass.method("get_IsReloading",0),0x029B0C90,"Character.IsReloading"),
    endDelay:at(characterClass.method("get_CurrentEndDelay",0),0x06385FB0,
      "Character.CurrentEndDelay")
  };
  const weaponMethods = {
    spotPreDelay:at(weaponClass.method("get_SpotPreDelay",0),0x063B7450,
      "Weapon.SpotPreDelay"),
    currentPreDelay:at(weaponClass.method("get_CurrentPreDelay",0),0x063B5E60,
      "Weapon.CurrentPreDelay"),
    currentAccumFireDelay:at(weaponClass.method("get_CurrentAccumFireDelay",0),
      0x063B5CE0,"Weapon.CurrentAccumFireDelay"),
    rateOfFire:at(weaponClass.method("get_RateOfFire",0),0x063B6D40,
      "Weapon.RateOfFire"),
    currentAmmo:at(weaponClass.method("get_CurrentAmmo",0),0x063B5D20,
      "Weapon.CurrentAmmo"),
    currentChargeTime:at(weaponClass.method("get_CurrentChargeTime",0),
      0x063B5DC0,"Weapon.CurrentChargeTime"),
    autoFire:at(weaponClass.method("get_IsAutoFireWeapon",0),0x063B64C0,
      "Weapon.IsAutoFireWeapon"),
    weaponType:at(weaponClass.method("get_WeaponType",0),0x063B7740,
      "Weapon.WeaponType")
  };
  const getCooltime = at(skillClass.method("get_CurrentCooltime",0),
    0x03B58350,"SpotSkill.CurrentCooltime");
  const nagaActors = geometry.live.actors.filter(actor=>actor.entityId===requestedEntityId);
  if (nagaActors.length!==1) throw new Error("Original requested Naga entity missing or duplicated");
  const naga = pin(required(nagaActors[0].entity,"Naga entity"));
  const nagaUiAim = pin(required(nagaActors[0].uiAim,"Naga original UIAim"));
  if (naga.class.type.name!==characterClass.type.name)
    throw new Error("Original Naga entity class changed");
  if (nagaUiAim.class.type.name!==uiAimClass.type.name)
    throw new Error("Original Naga UIAim class changed");
  const characterInfo = required(naga.field(
    "<CharacterStaticInfo>k__BackingField").value,"Naga CharacterStaticInfo");
  const nameCode = intResult(getNameCode,characterInfo);
  if (nameCode!==5099) throw new Error("Original Naga name code changed: "+nameCode);
  function aimReady() {
    const info = naga.field("<AimInfo>k__BackingField").value;
    const controller = present(info) ? info.field("_aimControl").value : null;
    const target = nagaUiAim.field("_target").value;
    return {aimInfoPresent:present(info),
      originalAimControlBound:present(controller) && present(geometry.live.aimControl) &&
        controller.handle.equals(geometry.live.aimControl.handle),
      originalUiAimTargetBound:present(target) && target.handle.equals(naga.handle)};
  }

  function skills() {
    const list = required(naga.field("<NormalSkillList>k__BackingField").value,
      "Naga normal skills");
    const count = intResult(list.method("get_Count",0),list);
    if (count<0 || count>12) throw new Error("Original Naga skill count outside bound");
    const found=[];
    for (let i=0;i<count+1;i++) {
      const skill = i===count ? naga.field("<UltimateSkill>k__BackingField").value :
        call(list.method("get_Item",1),list,[intArg(i)]);
      if (!present(skill)) {
        if (i===count) continue;
        throw new Error("Original Naga normal skill is null");
      }
      const record = required(skill.field("<RecordData>k__BackingField").value,
        "Naga skill RecordData");
      const text = record.field("<Resource_name>k__BackingField").value;
      found.push({slot:i===count?"ultimate":"normal:"+i,
        tableId:Number(record.field("<TableId>k__BackingField").value),
        resourceName:present(text)?new Il2Cpp.String(text.handle).content:null,
        currentCooltime:floatResult(getCooltime,skill)});
    }
    return found;
  }
  function weapon() {
    const current = pin(required(naga.field(
      "<CurrentWeaponData>k__BackingField").value,"Naga current weapon"));
    const original = naga.field("<DefaultWeaponData>k__BackingField").value;
    return {isDefaultWeapon:present(original)&&original.handle.equals(current.handle),
      weaponType:intResult(weaponMethods.weaponType,current),
      isAutoFireWeapon:boolResult(weaponMethods.autoFire,current),
      spotPreDelay:statResult(weaponMethods.spotPreDelay,current),
      currentPreDelay:obscuredFloatResult(weaponMethods.currentPreDelay,current),
      currentAccumFireDelay:obscuredFloatResult(
        weaponMethods.currentAccumFireDelay,current),
      rateOfFire:floatResult(weaponMethods.rateOfFire,current),
      currentAmmo:statResult(weaponMethods.currentAmmo,current),
      currentChargeTime:floatResult(weaponMethods.currentChargeTime,current)};
  }
  function unityState() {
    const value = required(call(getUnityState),"Unity Random.State");
    const ptr = value.unbox().handle;
    return [0,4,8,12].map(offset=>ptr.add(offset).readS32());
  }
  let lastAfter=0, lastBefore=-1;
  function sample(tick, phase = tick===0 ? "before" : "after") {
    if (!Number.isInteger(tick) ||
        (phase!=="before" && phase!=="after") ||
        (phase==="before" && (tick<0 || tick>19 ||
          tick!==lastAfter || tick!==lastBefore+1)) ||
        (phase==="after" && (tick<1 || tick>20 || tick!==lastAfter+1 ||
          lastBefore<0)))
      throw new Error("Original startup sample order must be before(0), " +
        "then ascending after(1..20), with optional paired before(1..19)");
    const shared = required(randomClass.field("_shared").value,"SpotRandom.Shared");
    const systemRandom = required(shared.field("<Random>k__BackingField").value,
      "SpotRandom.System.Random");
    const row = {status:"original_startup_state_sample",
      phase:phase==="before"?"before_next_native_tick":"after_native_tick",
      completedTicks:tick,
      clientSha256:client,requestSha256,
      managementTick:Number(management.field("_tickCount").value),
      managementPlaytime:f32(Number(management.field("_playtime").value)),
      managementDeltaTime:f32(Number(management.field("_deltaTime").value)),
      managementSeed:Number(management.field("<SpotRandomSeed>k__BackingField").value),
      teamAutoAim:Boolean(loadedTeam.field("_isAutoModeAim").value),
      teamAutoSkill:Boolean(loadedTeam.field("_isAutoModeSkill").value),
      naga:{entityId:requestedEntityId,nameCode,
        stance:intResult(characterMethods.stance,naga),
        isReloading:boolResult(characterMethods.reloading,naga),
        currentEndDelay:floatResult(characterMethods.endDelay,naga),
        usedAmmoCount:Number(naga.field("<UsedAmmoCount>k__BackingField").value),
        serialUsedAmmo:Number(naga.field("<SerialUsedAmmo>k__BackingField").value),
        shotHitNum:Number(naga.field("<ShotHitNum>k__BackingField").value),
        shotPelletHitNum:Number(naga.field("<ShotPelletHitNum>k__BackingField").value),
        aimReadiness:aimReady(),weapon:weapon(),skills:skills()},
      spotRandom:{seed:Number(shared.field("_currSeed").value),
        drawCount:shared.field("<DrawCount>k__BackingField").value.toString(),
        systemRandomInext:Number(systemRandom.field("_inext").value),
        systemRandomInextp:Number(systemRandom.field("_inextp").value)},
      unityRandomState:unityState(),
      unityClock:{time:floatResult(getTime),frameCount:intResult(getFrame),
        deltaTime:floatResult(getDelta),unscaledDeltaTime:floatResult(getUnscaled),
        captureDeltaTime:f32(getCapture()),
        cinemachineCurrentTimeOverride:cineTime()}};
    if (row.managementTick!==tick || row.managementSeed!==requestedSeed ||
        row.spotRandom.seed!==requestedSeed || !row.teamAutoAim || !row.teamAutoSkill)
      throw new Error("Original startup tick/seed/auto-input contract changed at "+tick);
    if (phase==="before") lastBefore=tick;
    else lastAfter=tick;
    emit(row);
    return row;
  }
  emit({status:"original_startup_state_observer_ready",nagaEntityId:requestedEntityId,
    nagaNameCode:5099,requestedSeed,requestSha256,firstSampleTick:0,lastSampleTick:20,
    installsHooks:false,drawsRandom:false,mutatesCombatState:false});
  return {sample};
}
