// Explicit diagnostic five-unit Kraken input for one ORIGINAL mechanics trial.
// Called after original DataManager tables load, on the Unity main thread.
// Returns a pinned boxed NKSpotDataTransporter. The caller installs its full
// unboxed payload with il2cpp_field_static_set_value before management OnInit;
// this file never uses the bridge's unsafe static value-type getter.
// This is not account data, a scene, a battle result, or parity evidence.
function mechanicsRequestedEntityId(nameCode) {
  const characters=globalThis.MECHANICS_REQUEST && globalThis.MECHANICS_REQUEST.characters;
  const index=Array.isArray(characters) ? characters.findIndex(row=>row.nameCode===nameCode) : -1;
  if (index<0) throw new Error("Diagnostic request has no character " + nameCode);
  // Verified against live original entities before the first battle tick.
  return 4096+index;
}

function prepareMechanicsFixture(runtimeImage, staticImage, pin, emit) {
  const request = globalThis.MECHANICS_REQUEST;
  const requestSha256 = globalThis.MECHANICS_REQUEST_SHA256;
  const required = (object, keys, label) => {
    if (!object || Array.isArray(object) || typeof object!=="object" ||
        Object.keys(object).sort().join("|")!==keys.slice().sort().join("|")) {
      throw new Error("Incomplete or unsupported diagnostic "+label);
    }
    return object;
  };
  const whole = (value, min, max, label) => {
    if (!Number.isSafeInteger(value) || value<min || value>max)
      throw new Error("Invalid diagnostic "+label);
    return value;
  };
  required(request,["schemaVersion","purpose","installedClientSha256",
    "characters","encounter",...(request.schemaVersion===2?["encounterProfileId"]:[])],"request");
  const snapshotMode=request.purpose==="diagnostic_bare_snapshot_build";
  const bareMode=request.purpose==="diagnostic_bare_character_build" || snapshotMode;
  if (![1,2].includes(request.schemaVersion) ||
      !(request.purpose==="diagnostic_synthetic_input" || bareMode) ||
      request.installedClientSha256!=="2df7134a6a9c3a8dbbde88402fc8d16d1d6c3f4c2d5e262bea78c3d78b96dd02" ||
      typeof requestSha256!=="string" || !/^[a-f0-9]{64}$/.test(requestSha256)) {
    throw new Error("Diagnostic mechanics request provenance is missing or unsupported");
  }
  const roster=request.characters;
  const encounter=required(request.encounter,["managementType","processType",
    "timeLimit","waveId","monsterStageLv","dynamicObjectLv",
    "raidLvChangeGroup","randomSeed","isAuto","tddProcess"],"encounter");
  const profile=request.schemaVersion===2?globalThis.MECHANICS_ENCOUNTER_PROFILE:null;
  if (request.schemaVersion===2&&(!profile||profile.productId!==request.encounterProfileId||
      !/^[a-f0-9]{64}$/.test(globalThis.MECHANICS_ENCOUNTER_REGISTRY_SHA256||"")))
    throw new Error("Diagnostic encounter lacks a verified registry binding");
  if (profile&&roster.some(row=>profile.sourceTableRow.CharacterLv!==undefined?
      row.level!==profile.sourceTableRow.CharacterLv:row.level>profile.sourceTableRow.LimitCharacterLv))
    throw new Error("Diagnostic character exceeds original encounter level cap");
  for (const [key,value] of Object.entries(profile?profile.encounter:{managementType:0,processType:7,
    timeLimit:180,waveId:6302009,monsterStageLv:250,dynamicObjectLv:250,
    raidLvChangeGroup:209,isAuto:true,tddProcess:false})) {
    if (encounter[key]!==value) throw new Error("Unsupported diagnostic encounter "+key);
  }
  whole(encounter.randomSeed,1,2147483647,"randomSeed");
  if (!Array.isArray(roster) || roster.length!==5) throw new Error("Diagnostic request needs five ordered characters");
  const codes=roster.map((member,index)=>{
    required(member,["nameCode","level","grade","core","skillLevels",
      bareMode?"barePolicy":"stats"],
      "character "+index);
    whole(member.nameCode,1,999999,"nameCode");
    whole(member.level,1,1000,"level");
    whole(member.grade,0,3,"grade");
    whole(member.core,0,7,"core");
    required(member.skillLevels,["1","2","3"],"skill levels");
    for (const key of ["1","2","3"])
      whole(member.skillLevels[key],1,10,"skill "+key);
    if (bareMode) {
      if (member.grade!==0 || member.core!==0)
        throw new Error("Bare diagnostic supports only grade/core 0/0");
      const policy=required(member.barePolicy,["equipment","attractiveLevel",
        "recycleResearch","harmonyCube","favoriteItem"],"bare policy");
      if (!Array.isArray(policy.equipment) || policy.equipment.length!==0 ||
          policy.attractiveLevel!==0 || !Array.isArray(policy.recycleResearch) ||
          policy.recycleResearch.length!==0 || policy.harmonyCube!==null ||
          policy.favoriteItem!==null) {
        throw new Error("Unsupported diagnostic bare investment policy");
      }
    } else {
      required(member.stats,["HealthPoint","Attack","Defense","EnergyResist",
        "MetalResist","BioResist","CriticalRatio","CriticalDamage","HPRatio"],"stats");
      for (const [key,value] of Object.entries(member.stats)) {
        if ((key==="CriticalRatio" || key==="CriticalDamage") &&
            value && !Array.isArray(value) && typeof value==="object" &&
            Object.keys(value).length===1 &&
            value.source==="installed_character_table") continue;
        whole(value,0,Number.MAX_SAFE_INTEGER,"stat "+key);
      }
      if (member.stats.HealthPoint===0 || member.stats.HPRatio===0)
        throw new Error("Diagnostic character needs positive HP and HP ratio");
    }
    return member.nameCode;
  });
  if (codes.slice().sort((a,b)=>a-b).join("|")!==
      [5004,5011,5065,5099,5105].join("|")) {
    throw new Error("Diagnostic request has unstaged character resources");
  }
  const present = value => value != null && !value.isNull();
  const enumNumber = value => typeof value === "number"
    ? value : Number(value.field("value__").value);
  const get = (object, name) => object.method("get_" + name).invoke();
  const checked = (method, instance = null, args = []) =>
    invokeChecked(method, instance, args);
  const boolArg = value => {
    const buffer = Memory.alloc(1);
    buffer.writeU8(value ? 1 : 0);
    return buffer;
  };
  const floatArgLocal = value => {
    const buffer = Memory.alloc(4);
    buffer.writeFloat(value);
    return buffer;
  };
  const note = row => emit({ fixture: profile?"diagnostic_registered_intercept":snapshotMode ?
      "diagnostic_bare_snapshot_five_unit_kraken_intercept" : bareMode ?
      "diagnostic_bare_five_unit_kraken_intercept" :
      "synthetic_five_unit_kraken_intercept",
    ...(profile?{encounterProfileId:profile.productId,
      encounterRegistrySha256:globalThis.MECHANICS_ENCOUNTER_REGISTRY_SHA256}:{}),
    accountDataUsed: false, completeBattle: false, ...row });

  const manager = checked(staticImage.class("NK.StaticData.DataManager")
    .method("get_Instance", 0));
  if (!present(manager)) throw new Error("Original DataManager is not ready");
  const table = get(manager, "CharacterTable");
  if (!present(table)) throw new Error("Original CharacterTable is null");
  const buffClass = staticImage.class(
    "NK.StaticData.StaticDataLayer.StaticInfo.BuffStaticInfo");
  const buffs = Il2Cpp.array(buffClass, []);
  pin(buffs.object);
  const dataClass = runtimeImage.class("NK.Spot.Common.SpotCharacterData");
  const skillClass = dataClass.nested("CharacterSkillData");
  const tableTypes = staticImage.class("NK.StaticData.TableType");
  const positions = runtimeImage.class("NK.Spot.Common.CommonEnum")
    .nested("ECharacterPosition");

  const memberObjects = roster.map((member, index) => {
    const nameCode=member.nameCode;
    const slot = index + 1;
    const info = pin(checked(table.method("GetFirstByNameCode", 1), table,
      [intArg(nameCode)]));
    if (!present(info)) throw new Error("CharacterTable missing NameCode " + nameCode);
    if (request.purpose==="diagnostic_bare_character_build" &&
        globalThis.MECHANICS_TRACE_MODE==="diagnostics" && nameCode===5065)
      probeMechanicsSnapshot(runtimeImage,staticImage,info,member,pin,
        row=>emit({...row,requestSha256}),{slot:1,costumeTableId:0});
    if (!bareMode && globalThis.MECHANICS_TRACE_MODE==="diagnostics" && nameCode===5065)
      probeMechanicsBareStats(runtimeImage,staticImage,info,pin,emit);
    if (snapshotMode) {
      const converted=convertMechanicsBareSnapshot(runtimeImage,staticImage,
        info,member,pin,{slot,costumeTableId:0});
      const data=converted.spot;
      // The original converter owns status, skills, equipment, passive list,
      // battle power and costume data. Team slot and explicit empty buffs are
      // the two fixture-level fields supplied after conversion.
      checked(data.method("set_PositionType",1),data,
        [intArg(enumNumber(positions.field("Player"+slot).value))]);
      checked(data.method("set_BuffStaticInfos",1),data,[buffs.handle]);
      const positionType=enumNumber(get(data,"PositionType"));
      const wantedPosition=enumNumber(positions.field("Player"+slot).value);
      const nativeBuffs=get(data,"BuffStaticInfos");
      if (positionType!==wantedPosition || !present(nativeBuffs) ||
          !nativeBuffs.handle.equals(buffs.handle) || nativeBuffs.length!==0)
        throw new Error("Original converted position/empty buffs readback mismatch "+nameCode);
      const calculated=calculateOriginalBareStats(runtimeImage,staticImage,
        info,member,pin,note,slot,requestSha256);
      const status=data.field("StatusData").value;
      const appliedStats={};
      for (const [key,wanted] of Object.entries(calculated.stats)) {
        const actual=status.field(key).value.field("Value").value.toString();
        if (actual!==wanted.toString())
          throw new Error("Original snapshot stat differs from original Calc "+nameCode+"/"+key);
        appliedStats[key]=["CriticalRatio","CriticalDamage","HPRatio"].includes(key) ?
          Number(actual) : actual;
      }
      const skillSources=[];
      for (const [field,key,summaryKey] of [["Skill1Data","1","skill1"],
          ["Skill2Data","2","skill2"],["SkillBurstData","3","burst"]]) {
        const skill=data.field(field).value;
        if (!present(skill)) throw new Error("Original snapshot missing skill "+nameCode+"/"+field);
        const native=converted.output.nativeValues.skills[summaryKey];
        const source={field,group:native.groupId,tableType:native.tableType,
          level:native.level};
        if (source.level!==member.skillLevels[key] || source.group<=0 ||
            source.tableType<=0 || native.disabled || native.favoriteItem)
          throw new Error("Original snapshot skill readback mismatch "+nameCode+"/"+field);
        skillSources.push(source);
      }
      const tableId=enumNumber(get(info,"TableId"));
      if (Number(get(data,"Level"))!==member.level ||
          Number(get(data,"Grade"))!==member.grade ||
          Number(get(data,"Core"))!==member.core)
        throw new Error("Original snapshot investment readback mismatch "+nameCode);
      note({status:"original_bare_stats_applied",slot,nameCode,tableId,
        level:member.level,grade:member.grade,core:member.core,
        barePolicy:member.barePolicy,source:calculated.source,
        applicationSource:"installed_original_CharacterSnapshot_conversion",
        statProvenance:calculated.statProvenance,
        originalHelper:calculated.originalHelper,stats:appliedStats,requestSha256});
      note({status:"original_bare_snapshot_applied",slot,nameCode,tableId,
        level:member.level,grade:member.grade,core:member.core,
        barePolicy:member.barePolicy,requestSha256,
        source:"installed_original_CharacterSnapshot_conversion",
        positionType,emptyBuffCount:0,stats:appliedStats,skillSources,
        nativeValues:{...converted.output.nativeValues,positionType,
          buffStaticInfos:{type:nativeBuffs.object.class.type.name,
            length:nativeBuffs.length}}});
      note({status:"original_character_data_prepared",slot,nameCode,tableId,
        resourceId:enumNumber(get(info,"ResourceId")),skillSources,
        level:member.level,grade:member.grade,core:member.core,
        stats:appliedStats,requestSha256,
        statSource:"installed_original_bare_builder",
        characterSource:"installed_original_CharacterSnapshot_conversion",
        barePolicy:member.barePolicy});
      return data;
    }
    const data = pin(dataClass.alloc());
    checked(data.method(".ctor", 0), data);
    checked(data.method("set_CharacterStaticInfo", 1), data, [info.handle]);
    checked(data.method("set_Level", 1), data, [intArg(member.level)]);
    checked(data.method("set_Grade", 1), data, [intArg(member.grade)]);
    checked(data.method("set_Core", 1), data, [intArg(member.core)]);
    checked(data.method("set_PositionType", 1), data,
      [intArg(enumNumber(positions.field("Player" + slot).value))]);
    checked(data.method("set_BuffStaticInfos", 1), data, [buffs.handle]);
    checked(data.method("set_UseBurstSkill", 1), data,
      [intArg(enumNumber(get(info, "UseBurstSkill")))]);
    checked(data.method("set_ChangeBurstStep", 1), data,
      [intArg(enumNumber(get(info, "ChangeBurstStep")))]);

    const ultimate = get(info, "UltSkill");
    const definitions = [
      ["Skill1Data", get(info, "Skill1Info"), get(info, "Skill1Table"),"1"],
      ["Skill2Data", get(info, "Skill2Info"), get(info, "Skill2Table"),"2"],
      ["SkillBurstData", present(ultimate) ? get(ultimate, "Info") : null,
        tableTypes.field("CharacterSkill").value,"3"]
    ];
    const skillSources = [];
    for (const [fieldName, skillInfo, tableType,levelKey] of definitions) {
      const group = present(skillInfo) ? get(skillInfo, "Group_id") : 0;
      const skill = pin(skillClass.alloc());
      checked(skill.method(".ctor", 5), skill,
        [intArg(group), intArg(member.skillLevels[levelKey]), intArg(enumNumber(tableType)),
          boolArg(false), boolArg(false)]);
      data.field(fieldName).value = skill;
      const stored = data.field(fieldName).value;
      if (!present(stored) || !stored.handle.equals(skill.handle)) {
        throw new Error("Original skill reference mismatch " + nameCode + "/" + fieldName);
      }
      if (Number(get(stored,"Level"))!==member.skillLevels[levelKey] ||
          Number(get(stored,"GroupId"))!==Number(group)) {
        throw new Error("Original skill value mismatch "+nameCode+"/"+fieldName);
      }
      skillSources.push({ field: fieldName, group,
        tableType: enumNumber(tableType), level: member.skillLevels[levelKey] });
    }

    // Bare mode has no supplied HP/ATK/DEF or hidden fallback. It accepts
    // only original builder outputs for the explicitly empty investment set.
    const calculated=bareMode ? calculateOriginalBareStats(runtimeImage,
      staticImage,info,member,pin,note,slot,requestSha256) : null;
    const stats={};
    if (bareMode) Object.assign(stats,calculated.stats);
    else for (const [name,value] of Object.entries(member.stats))
      stats[name]=typeof value==="object" ? get(info,name) : value;
    const status = data.field("StatusData").value;
    const appliedStats={};
    for (const [name, value] of Object.entries(stats)) {
      status.field(name).value.field("Value").value = bareMode ?
        int64(value.toString()) : value;
      const readback=status.field(name).value.field("Value").value.toString();
      if (readback!==value.toString()) {
        throw new Error("Original status readback mismatch "+nameCode+"/"+name);
      }
      appliedStats[name]=bareMode &&
        !["CriticalRatio","CriticalDamage","HPRatio"].includes(name) ?
        readback : Number(readback);
    }
    if (Number(get(data,"Level"))!==member.level ||
        Number(get(data,"Grade"))!==member.grade ||
        Number(get(data,"Core"))!==member.core) {
      throw new Error("Original character investment readback mismatch "+nameCode);
    }
    const tableId=enumNumber(get(info,"TableId"));
    if (bareMode) note({status:"original_bare_stats_applied",slot,nameCode,
      tableId,level:member.level,grade:member.grade,core:member.core,
      barePolicy:member.barePolicy,source:calculated.source,
      statProvenance:calculated.statProvenance,
      originalHelper:calculated.originalHelper,
      stats:appliedStats,requestSha256});
    note({ status: "original_character_data_prepared", slot, nameCode,
      tableId,
      resourceId: enumNumber(get(info, "ResourceId")),
      skillSources, level: member.level, grade:member.grade, core:member.core,
      stats:bareMode?appliedStats:stats,requestSha256,
      ...(bareMode ? {statSource:"installed_original_bare_builder",
        barePolicy:member.barePolicy} : {}) });
    return data;
  });

  // Managed Array.SetValue writes references through the original barrier.
  // The installed bridge's implicit Array.elements.write path failed to
  // establish the requested length in the prior isolated-player trial.
  const members = Il2Cpp.array(dataClass, roster.length);
  pin(members.object);
  const assembly = Process.getModuleByName("GameAssembly.dll");
  const arrayLength = new NativeFunction(assembly.getExportByName(
    "il2cpp_array_length"), "uint32", ["pointer"]);
  const arrayClass = Il2Cpp.corlib.class("System.Array");
  const managedLength = checked(arrayClass.method("get_Length", 0),
    members.object).unbox().handle.readS32();
  if (arrayLength(members.handle) !== roster.length ||
      managedLength !== roster.length) {
    throw new Error("Original typed team array length mismatch");
  }
  const setValue = arrayClass.method("SetValue").overload(
    "System.Object", "System.Int32");
  const getValue = arrayClass.method("GetValue").overload("System.Int32");
  memberObjects.forEach((member, index) => {
    checked(setValue, members.object, [member.handle, intArg(index)]);
    const stored = checked(getValue, members.object, [intArg(index)]);
    if (!present(stored) || !stored.handle.equals(member.handle)) {
      throw new Error("Original typed team array element mismatch at " + index);
    }
  });
  const teamClass = runtimeImage.class("NK.Spot.Common.SpotTeamData");
  const teamData = pin(teamClass.alloc());
  checked(teamData.method(".ctor", 0), teamData);
  checked(teamData.method("Add", 2), teamData,
    [members.handle, intArg(0)]);
  const teamList = get(teamData, "CharacterDataList");
  if (!present(teamList) || get(teamList, "Count") !== 1) {
    throw new Error("SpotTeamData did not retain the five-slot list");
  }

  const transporterClass = runtimeImage.class("NK.Spot.Data.NKSpotDataTransporter");
  const valueSize = transporterClass.valueTypeSize;
  if (valueSize < 360 || valueSize > 1024) {
    throw new Error("Unexpected NKSpotDataTransporter value size " + valueSize);
  }
  const transporterBox = pin(transporterClass.alloc());
  const transporter = transporterBox.unbox();
  const managementType = runtimeImage.class("NK.Spot.Common.CommonEnum")
    .nested("ManagementType").field("SinglePlay").value;
  const processType = staticImage.class("NK.StaticData.SpotModType")
    .field("Intercept").value;
  if (enumNumber(processType) !== encounter.processType ||
      enumNumber(managementType)!==encounter.managementType) {
    throw new Error("Installed Intercept SpotModType is not 7");
  }
  checked(transporter.method("set_ManagementType", 1), transporter,
    [intArg(encounter.managementType)]);
  checked(transporter.method("set_ProcessType", 1), transporter,
    [intArg(encounter.processType)]);
  checked(transporter.method("set_TimeLimit", 1), transporter,
    [floatArgLocal(encounter.timeLimit)]);
  transporter.field("MyTeamData").value = teamData;
  if (!present(transporter.field("MyTeamData").value)) {
    throw new Error("NKSpotDataTransporter did not retain synthetic team");
  }
  for (const [setter, value] of [
    ["set_WaveId", encounter.waveId],
    ["set_MonsterStageLv", encounter.monsterStageLv],
    ["set_DynamicObjectLv", encounter.dynamicObjectLv],
    ["set_RaidLvChangeGroup", encounter.raidLvChangeGroup],
    ["set_RandomSeed", encounter.randomSeed]
  ]) {
    checked(transporter.method(setter, 1), transporter, [intArg(value)]);
  }
  checked(transporter.method("set_IsAuto", 1), transporter,
    [boolArg(encounter.isAuto)]);
  checked(transporter.method("set_TDDProcess", 1), transporter,
    [boolArg(encounter.tddProcess)]);
  const readback={managementType:enumNumber(get(transporter,"ManagementType")),
    processType:enumNumber(get(transporter,"ProcessType")),
    timeLimit:Number(get(transporter,"TimeLimit")),
    waveId:Number(get(transporter,"WaveId")),
    monsterStageLv:Number(get(transporter,"MonsterStageLv")),
    dynamicObjectLv:Number(get(transporter,"DynamicObjectLv")),
    raidLvChangeGroup:Number(get(transporter,"RaidLvChangeGroup")),
    randomSeed:Number(get(transporter,"RandomSeed")),
    isAuto:Boolean(get(transporter,"IsAuto")),
    tddProcess:Boolean(get(transporter,"TDDProcess"))};
  if (Object.keys(readback).some(key=>readback[key]!==encounter[key]) ||
      !present(transporter.field("MyTeamData").value)) {
    throw new Error("Prepared transporter readback mismatch");
  }
  note({ status: profile?"original_encounter_transporter_prepared":"synthetic_kraken_transporter_prepared",
    roster: roster.map(row => row.nameCode), ...readback,requestSha256,
    transporterValueTypeSize: valueSize,
    staticFieldInstalled: false, battleStarted: false, resultCaptured: false });
  return transporterBox;
}
