// Passive skill-timeline occurrence trace for the exact installed client.
// Forward the already wrapped event from the existing SendEventDefault hook.
// No hook, event dispatch, skill activation, or marker callback is added here.
function installMechanicsSkillEventObserver(runtime, management, emit) {
  if (!runtime || !management || management.isNull() || typeof emit !== "function")
    throw new Error("Original skill event observer requires management and emit");
  const game = Process.getModuleByName("GameAssembly.dll");
  const send = management.method("SendEventDefault", 1);
  if (!send.virtualAddress.equals(game.base.add(0x0614BAF0)))
    throw new Error("Installed SendEventDefault RVA changed");

  const events = runtime.class("NK.Spot.Common.SpotEvent").nested("SpotEventType");
  const character = runtime.class("NK.Spot.Event.Character.ProcessCharacterSkillEvent");
  const monster = runtime.class("NK.Spot.Event.Monster.ProcessMonsterSkillEvent");
  const skillClass = runtime.class("NK.Spot.Model.Character.Skill.SpotSkill");
  const recordClass = Il2Cpp.domain.assembly("NK.Runtime.StaticData").image.class(
    "NK.StaticData.StaticDataLayer.StaticInfo.CharacterSkillStaticInfo");
  const layouts = [
    [character,"CasterInfo",0x40],[character,"Skill",0x48],
    [character,"DirectorList",0x50],
    [monster,"CasterInfo",0x40],[monster,"DirectorList",0x48],
    [skillClass,"<RecordData>k__BackingField",0x20],
    [skillClass,"_resourceData",0xa0],
    [recordClass,"<TableId>k__BackingField",0x10],
    [recordClass,"<Resource_name>k__BackingField",0x28]
  ];
  for (const [klass,name,offset] of layouts)
    if (klass.field(name).offset !== offset)
      throw new Error("Installed skill event field layout changed: " + klass.name + "." + name);
  const ctorRvas = [[character,0x064578B0],[monster,0x06425320]];
  for (const [klass,rva] of ctorRvas)
    if (!klass.method(".ctor").virtualAddress.equals(game.base.add(rva)))
      throw new Error("Installed skill event constructor RVA changed: " + klass.name);
  const numeric = value => typeof value === "number" ? value :
    Number(value.field("value__").value);
  const expected = new Map([
    ["NK.Spot.Event.Character.ProcessCharacterSkillEvent",
      {kind:"character",id:0x2ee6,enumName:"ProcessCharacterSkill"}],
    ["NK.Spot.Event.Monster.ProcessMonsterSkillEvent",
      {kind:"monster",id:0x4e3c,enumName:"ProcessMonsterSkill"}]
  ]);
  for (const definition of expected.values())
    if (numeric(events.field(definition.enumName).value) !== definition.id)
      throw new Error("Installed SpotEventType changed: " + definition.enumName);

  const live = value => value != null && !value.isNull();
  const directorCountOf = list => {
    if (!live(list)) return null;
    // The event declares IReadOnlyList<T>; the concrete object may be List<T>
    // or an array. Read its original count without assuming one layout.
    const name = list.class.type.name;
    const method = name.endsWith("[]") ?
      Il2Cpp.corlib.class("System.Array").method("get_Length", 0) :
      list.method("get_Count", 0);
    const count = invokeChecked(method, list).unbox().handle.readS32();
    if (!Number.isSafeInteger(count) || count < 0 || count > 512)
      throw new Error("Original skill DirectorList count outside bound: " + count);
    return count;
  };
  const counts = new Map();
  const maxSamples = 30, maxGroups = 128;
  let total = 0, samples = 0, fault = null;
  const fail = (where,error) => {
    if (fault === null) fault = where + ": " +
      (error && error.stack ? error.stack : String(error));
  };
  const readSkill = skill => {
    if (!live(skill)) throw new Error("ProcessCharacterSkill event has no original Skill");
    if (skill.class.type.name !== "NK.Spot.Model.Character.Skill.SpotSkill")
      throw new Error("ProcessCharacterSkill event Skill type changed");
    const record = skill.field("<RecordData>k__BackingField").value;
    if (!live(record) || record.class.type.name !==
        "NK.StaticData.StaticDataLayer.StaticInfo.CharacterSkillStaticInfo")
      throw new Error("Original SpotSkill RecordData is missing or changed");
    const skillId = Number(record.field("<TableId>k__BackingField").value);
    const name = record.field("<Resource_name>k__BackingField").value;
    const resourceName = live(name) ? name.content : null;
    if (!Number.isSafeInteger(skillId) || skillId <= 0 || !resourceName)
      throw new Error("Original skill ID/resource name is incomplete");
    const resource = skill.field("_resourceData").value;
    return {skillId,resourceName,resourceDataLoaded:live(resource),
      resourceDataType:live(resource) ? resource.class.type.name : null};
  };
  function observeSendEvent(event) {
    if (!live(event) || fault !== null) return;
    const definition = expected.get(event.class.type.name);
    if (!definition) return;
    try {
      const actual = numeric(event.field("<SpotEventID>k__BackingField").value);
      if (actual !== definition.id)
        throw new Error("Original skill event class/ID mismatch: " + actual);
      const caster = event.field("CasterInfo").value;
      if (!live(caster)) throw new Error("Original skill event caster is missing");
      const casterId = Number(caster.field("EntityID").value);
      const tick = Number(management.field("_tickCount").value);
      const playTime = Number(management.field("_playtime").value);
      if (!Number.isSafeInteger(casterId) || casterId < 0 ||
          !Number.isSafeInteger(tick) || tick < 0 || !Number.isFinite(playTime))
        throw new Error("Original skill event caster/tick/time is invalid");
      // MonsterProcessSkill carries only a caster and DirectorList in its
      // original serialized schema; it has no Skill field. Never infer an ID.
      const skill = definition.kind === "character" ?
        readSkill(event.field("Skill").value) :
        {skillId:null,resourceName:null,resourceDataLoaded:null,
          resourceDataType:null};
      const directorList = event.field("DirectorList").value;
      const directorListPresent = live(directorList);
      const directorCount = directorCountOf(directorList);
      const row = {eventKind:definition.kind,eventId:actual,casterId,tick,
        playTime,skillId:skill.skillId,resourceName:skill.resourceName,
        resourceDataLoaded:skill.resourceDataLoaded,
        resourceDataType:skill.resourceDataType,directorListPresent,directorCount,
        skillIdentitySource:definition.kind === "character" ?
          "SpotSkill.RecordData.TableId/Resource_name" :
          "unavailable: ProcessMonsterSkillEvent has no Skill field"};
      const key = definition.kind + ":" + casterId + ":" +
        (skill.skillId === null ? "unknown" : skill.skillId);
      let group = counts.get(key);
      if (!group) {
        if (counts.size >= maxGroups) throw new Error("Skill event group limit exceeded");
        group = {eventKind:definition.kind,casterId,skillId:skill.skillId,
          resourceName:skill.resourceName,count:0,firstTick:tick,lastTick:tick,
          eventsWithDirectors:0,directorCountTotal:0,maxDirectorCount:0};
        counts.set(key,group);
      } else if (group.resourceName !== skill.resourceName) {
        throw new Error("Original skill ID changed its resource name");
      }
      if (!Number.isSafeInteger(total + 1) || !Number.isSafeInteger(group.count + 1))
        throw new Error("Skill event counter overflow");
      total++; group.count++; group.lastTick = tick;
      if (directorCount !== null) {
        group.directorCountTotal += directorCount;
        group.maxDirectorCount = Math.max(group.maxDirectorCount,directorCount);
        if (directorCount > 0) group.eventsWithDirectors++;
      }
      if (samples < maxSamples) {
        samples++;
        emit({status:"original_skill_process_event",ordinal:samples,...row});
      }
    } catch (error) { fail("observeSendEvent",error); }
  }
  function snapshot() {
    return {status:"original_skill_event_summary",total,sampled:samples,
      sampleLimit:maxSamples,groups:[...counts.values()].sort((a,b) =>
        a.eventKind.localeCompare(b.eventKind) || a.casterId-b.casterId ||
        (a.skillId||0)-(b.skillId||0)),
      // CharacterSkillStaticInfo.TableId varies by skill level (the current
      // fixture uses level 10). The exact installed resource name is stable.
      scarlet1225301Observed:[...counts.values()].some(row =>
        row.eventKind === "character" && row.resourceName === "c225_skill1_3"),
      scarlet1225301MatchSource:"exact CharacterSkillStaticInfo.Resource_name == c225_skill1_3",
      fault};
  }
  function checkFault() {
    if (fault !== null) throw new Error(fault);
  }
  emit({status:"original_skill_event_observer_ready",characterEventId:0x2ee6,
    monsterEventId:0x4e3c,firstSampleLimit:maxSamples,
    installedDllSha256:"2df7134a6a9c3a8dbbde88402fc8d16d1d6c3f4c2d5e262bea78c3d78b96dd02",
    installsHooks:false,mutatesCombatState:false});
  return {observeSendEvent,snapshot,checkFault};
}
