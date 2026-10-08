// Exact original bare snapshot -> SpotCharacterData conversion. The returned
// object is pinned; only the caller decides whether to put it in a team.
function convertMechanicsBareSnapshot(runtimeImage, staticImage, selectedRow, member,
    pin, options) {
  const live=value=>value!=null && !value.isNull();
  const requireRef=(value,label)=>{
    if (!live(value)) throw new Error("Snapshot probe: missing "+label);
    return pin(value);
  };
  const call=(method,self=null,args=[])=>invokeChecked(method,self,args);
  const i32=(method,self=null)=>requireRef(call(method,self),method.name)
    .unbox().handle.readS32();
  const i64=(method,self=null)=>requireRef(call(method,self),method.name)
    .unbox().handle.readS64().toString();
  const bool=(method,self=null)=>requireRef(call(method,self),method.name)
    .unbox().handle.readU8()!==0;
  const countCollection=value=>value.class.type.name.endsWith("[]") ?
    i32(Il2Cpp.corlib.class("System.Array").method("get_Length",0),value) :
    i32(value.method("get_Count",0),value);
  const arg32=value=>{const p=Memory.alloc(4);p.writeS32(value);return p;};
  const requiredKeys=(object,keys,label)=>{
    if (!object || typeof object!=="object" || Array.isArray(object) ||
        Object.keys(object).sort().join("|")!==keys.slice().sort().join("|"))
      throw new Error("Snapshot probe: unsupported "+label);
    return object;
  };
  requiredKeys(options,["slot","costumeTableId"],"options");
  if (!Number.isSafeInteger(options.slot) || options.slot<1 || options.slot>5 ||
      options.costumeTableId!==0)
    throw new Error("Snapshot probe: only an explicit team slot/no-costume is supported");
  requiredKeys(member,["nameCode","level","grade","core","skillLevels",
    "barePolicy"],"bare member");
  const bare=requiredKeys(member.barePolicy,["equipment","attractiveLevel",
    "recycleResearch","harmonyCube","favoriteItem"],"bare policy");
  if (![5004,5011,5065,5099,5105].includes(member.nameCode) ||
      !Number.isSafeInteger(member.level) ||
      member.level<1 || member.level>1000 || member.grade!==0 || member.core!==0 ||
      !Array.isArray(bare.equipment) || bare.equipment.length!==0 ||
      bare.attractiveLevel!==0 || !Array.isArray(bare.recycleResearch) ||
      bare.recycleResearch.length!==0 || bare.harmonyCube!==null ||
      bare.favoriteItem!==null)
    throw new Error("Snapshot probe: member is not an explicitly staged bare build");
  requiredKeys(member.skillLevels,["1","2","3"],"skill levels");
  for (const level of Object.values(member.skillLevels))
    if (!Number.isSafeInteger(level) || level<1 || level>10)
      throw new Error("Snapshot probe: unsupported skill level");

  const row=requireRef(selectedRow,"selected CharacterStaticInfo");
  if (row.class.type.name!==
      staticImage.class("NK.StaticData.StaticDataLayer.StaticInfo.CharacterStaticInfo").type.name)
    throw new Error("Snapshot probe: selected row has wrong managed type");
  const gradeCore=requireRef(call(row.method("get_GradeCore",0),row),"GradeCore");
  const rowIdentity={nameCode:i32(row.method("get_NameCode",0),row),
    tableId:i32(row.method("get_TableId",0),row),
    grade:i32(gradeCore.method("get_Grade",0),gradeCore),
    core:i32(gradeCore.method("get_Core",0),gradeCore)};
  if (rowIdentity.nameCode!==member.nameCode || rowIdentity.tableId<=0 ||
      rowIdentity.grade!==member.grade || rowIdentity.core!==member.core)
    throw new Error("Snapshot probe: exact native row mismatch "+JSON.stringify(rowIdentity));

  const infoClass=runtimeImage.class("NK.Common.System.Stat.StatCalculateInfo");
  const builderClass=infoClass.nested("Builder");
  const absent=["_equipments","_statCalculateParameterHarmonyCube",
    "_statCalculateParameterFavoriteItem","_recycleDataProviders"];
  for (const name of absent)
    if (builderClass.field(name).type.class.isValueType)
      throw new Error("Snapshot probe: builder field is not nullable "+name);
  const builder=pin(builderClass.alloc());
  call(builder.method(".ctor").overload("NK.StaticData.Categoricals.CharacterTableId"),
    builder,[arg32(rowIdentity.tableId)]);
  call(builder.method("SetCharacterLevel").overload("System.Int32"),
    builder,[arg32(member.level)]);
  call(builder.method("SetAttractiveLevel").overload("System.Int32"),
    builder,[arg32(0)]);
  for (const name of absent)
    if (live(builder.field(name).value))
      throw new Error("Snapshot probe: bare investment field is populated "+name);
  const statInfo=requireRef(call(builder.method("Build",0),builder),"StatCalculateInfo");
  if (i32(statInfo.method("get_Grade",0),statInfo)!==0 ||
      i32(statInfo.method("get_Core",0),statInfo)!==0 ||
      i32(statInfo.method("get_CharacterLevel",0),statInfo)!==member.level ||
      i32(statInfo.method("get_AttractiveLevel",0),statInfo)!==0)
    throw new Error("Snapshot probe: original stat-builder input readback mismatch");
  const helperClass=runtimeImage.class("NK.Common.System.Stat.CharacterStatHelper");
  const calc=helperClass.method("Calc").overload(
    "NK.Common.System.Stat.StatCalculateInfo");
  const helper=pin(helperClass.alloc());
  call(helper.method(".ctor",0),helper);
  const providers=requireRef(helper.field("_calcs").value,"seven original providers");
  if (i32(providers.method("get_Count",0),providers)!==7)
    throw new Error("Snapshot probe: original stat providers differ");
  const statBox=requireRef(call(calc,helper,[statInfo.handle]),"CharacterStatData");
  const statValue=statBox.unbox();
  const calculated={HealthPoint:i64(statValue.method("get_Hp",0),statValue),
    Attack:i64(statValue.method("get_Attack",0),statValue),
    Defense:i64(statValue.method("get_Defense",0),statValue),
    EnergyResist:i64(statValue.method("get_EnergyResist",0),statValue),
    MetalResist:i64(statValue.method("get_MetalResist",0),statValue),
    BioResist:i64(statValue.method("get_BioResist",0),statValue)};

  const snapshotClass=runtimeImage.class("NK.Common.System.UserData.CharacterSnapshot");
  const ctor=snapshotClass.method(".ctor",16);
  const expectedTypes=[
    "NK.StaticData.StaticDataLayer.StaticInfo.CharacterStaticInfo",
    "NK.Common.System.UserData.NKCharacterInfo","System.Int32",
    "NK.StaticData.Categoricals.CostumeTableId","System.Int32","System.Int32",
    "System.Int32","NK.Common.System.Stat.CharacterStatData",
    "NK.Common.System.UserData.EquipsAndCube",
    "NK.Common.System.UserData.CharacterSnapshot.ItemStateEffects",
    "NK.Common.Util.Monad.Option<NK.Common.System.UserData.NKUser_CharacterData.CharacterSkillDisableStatus>",
    "NK.StaticData.StaticDataLayer.StaticInfo.SkillInfoStaticInfo",
    "NK.StaticData.StaticDataLayer.StaticInfo.SkillInfoStaticInfo",
    "NK.StaticData.StaticDataLayer.StaticInfo.SkillInfoStaticInfo",
    "System.Nullable<NK.StaticData.TableType>",
    "System.Nullable<NK.StaticData.TableType>"
  ];
  const actualTypes=ctor.parameters.map(parameter=>parameter.type.name);
  if (actualTypes.length!==16 || actualTypes.some((name,index)=>name!==expectedTypes[index]))
    throw new Error("Snapshot probe: 16-argument constructor metadata changed "+
      JSON.stringify(actualTypes));
  const characterInfoClass=runtimeImage.class("NK.Common.System.UserData.NKCharacterInfo");
  const emptyCharacterInfo=requireRef(call(characterInfoClass.method("CreateEmpty",0)),
    "NKCharacterInfo.CreateEmpty");
  if (!bool(emptyCharacterInfo.unbox().method("get_IsEmpty",0),
      emptyCharacterInfo.unbox()))
    throw new Error("Snapshot probe: original empty character identity is not empty");
  const equipsClass=runtimeImage.class("NK.Common.System.UserData.EquipsAndCube");
  const emptyEquips=requireRef(call(equipsClass.method("get_Empty",0)),
    "EquipsAndCube.Empty");
  // Original Empty contains an EquipCubeSnapshot.Empty sentinel, not null.
  // get_Empty 0x06B306D0 writes ISN/TID/level zero into that original record.
  const emptyCube=requireRef(call(emptyEquips.method("get_Cube",0),emptyEquips),
    "original empty cube sentinel");
  if (i64(emptyCube.method("get_Isn",0),emptyCube)!=="0" ||
      i32(emptyCube.method("get_Tid",0),emptyCube)!==0 ||
      i32(emptyCube.method("get_Level",0),emptyCube)!==0)
    throw new Error("Snapshot probe: original empty cube sentinel is nonempty");
  const effectsClass=snapshotClass.nested("ItemStateEffects");
  const emptyEffects=requireRef(call(effectsClass.method("get_Empty",0)),
    "ItemStateEffects.Empty");
  const emptyEffectList=requireRef(call(emptyEffects.method("get_TidList",0),emptyEffects),
    "empty effect list");
  if (countCollection(emptyEffectList)!==0)
    throw new Error("Snapshot probe: original empty item effects are not empty");

  const optionClass=ctor.parameters[10].type.class;
  const nullable1Class=ctor.parameters[14].type.class;
  const nullable2Class=ctor.parameters[15].type.class;
  if (!optionClass.isValueType || !nullable1Class.isValueType ||
      !nullable2Class.isValueType)
    throw new Error("Snapshot probe: Option/Nullable ABI types are not value types");
  // Nullable boxing unwraps to T (or null); allocating a boxed Nullable does
  // not provide its full argument payload. Use its validated native layout.
  const noneOption=pin(optionClass.alloc());
  const emptyNullable=(klass,expectedType)=>{
    if (klass.type.name!==expectedType || klass.valueTypeSize!==8 ||
        klass.field("hasValue").offset!==16 || klass.field("value").offset!==20 ||
        klass.field("hasValue").type.name!=="System.Boolean" ||
        klass.field("value").type.name!=="NK.StaticData.TableType")
      throw new Error("Snapshot probe: nullable TableType layout changed "+klass.type.name);
    const payload=Memory.alloc(8);
    payload.writeByteArray([0,0,0,0,0,0,0,0]);
    return new Il2Cpp.ValueType(payload,klass.type);
  };
  const noneNullable1=emptyNullable(nullable1Class,expectedTypes[14]);
  const noneNullable2=emptyNullable(nullable2Class,expectedTypes[15]);
  if (!bool(noneOption.unbox().method("get_IsNone",0),noneOption.unbox()) ||
      bool(noneNullable1.method("get_HasValue",0),noneNullable1) ||
      bool(noneNullable2.method("get_HasValue",0),noneNullable2))
    throw new Error("Snapshot probe: default Option/Nullable semantics changed");
  const skill1=requireRef(call(row.method("get_Skill1Info",0),row),"Skill1Info");
  const skill2=requireRef(call(row.method("get_Skill2Info",0),row),"Skill2Info");
  const ultimate=requireRef(call(row.method("get_UltSkill",0),row),"UltSkill");
  const skill3=requireRef(call(ultimate.method("get_Info",0),ultimate),"BurstSkillInfo");
  const snapshot=pin(snapshotClass.alloc());
  const args=[row.handle,emptyCharacterInfo.unbox().handle,
    arg32(member.level),arg32(options.costumeTableId),
    arg32(member.skillLevels["1"]),arg32(member.skillLevels["2"]),
    arg32(member.skillLevels["3"]),statValue.handle,
    emptyEquips.handle,emptyEffects.handle,noneOption.unbox().handle,
    // These are favorite-skill overrides, not mandatory base skill inputs.
    // Original ctor selects the row's skills when null; nonnull marks favorite.
    NULL,NULL,NULL,
    noneNullable1.handle,noneNullable2.handle];
  if (args.length!==16 || args.some((value,index)=>value==null ||
      (value.isNull() && ![11,12,13].includes(index))))
    throw new Error("Snapshot probe: a typed constructor argument is null");
  call(ctor,snapshot,args);
  const snapshotRow=requireRef(call(snapshot.method("get_CharacterStaticInfo",0),snapshot),
    "snapshot character row");
  const snapshotEquips=requireRef(call(snapshot.method("get_EquipsAndCube",0),snapshot),
    "snapshot empty equipment");
  const snapshotEffects=requireRef(call(snapshot.method("get_ItemStateEffectTidList",0),snapshot),
    "snapshot item effects");
  if (!snapshotRow.handle.equals(row.handle) ||
      !snapshotEquips.handle.equals(emptyEquips.handle) ||
      countCollection(snapshotEffects)!==0 ||
      i32(snapshot.method("get_Skill1Level",0),snapshot)!==member.skillLevels["1"] ||
      i32(snapshot.method("get_Skill2Level",0),snapshot)!==member.skillLevels["2"] ||
      i32(snapshot.method("get_SkillBurstLevel",0),snapshot)!==member.skillLevels["3"])
    throw new Error("Snapshot probe: original constructor readback mismatch");

  const extension=runtimeImage.class(
    "NK.Common.System.UserData.CharacterSnapshotExtension");
  const spot=requireRef(call(extension.method("CreateSpotCharacterData",1),null,
    [snapshot.handle]),"converted SpotCharacterData");
  const getInt=name=>i32(spot.method("get_"+name,0),spot);
  const getLong=name=>i64(spot.method("get_"+name,0),spot);
  const getBool=name=>bool(spot.method("get_"+name,0),spot);
  const status=spot.field("StatusData").value;
  const stats={};
  for (const name of ["HealthPoint","Attack","Defense","EnergyResist",
      "MetalResist","BioResist","CriticalRatio","CriticalDamage","HPRatio"])
    stats[name]=status.field(name).value.field("Value").value.toString();
  for (const [name,value] of Object.entries(calculated))
    if (stats[name]!==value)
      throw new Error("Snapshot probe: converted "+name+" differs from original Calc");
  if (stats.CriticalRatio!==i32(row.method("get_CriticalRatio",0),row).toString() ||
      stats.CriticalDamage!==i32(row.method("get_CriticalDamage",0),row).toString() ||
      stats.HPRatio!=="10000")
    throw new Error("Snapshot probe: converted table-critical/HP ratio mismatch");
  const readSkill=fieldName=>{
    const skill=requireRef(spot.field(fieldName).value,fieldName);
    return {groupId:i32(skill.method("get_GroupId",0),skill),
      level:i32(skill.method("get_Level",0),skill),
      tableType:i32(skill.method("get_TableType",0),skill),
      disabled:bool(skill.method("get_Disable",0),skill),
      favoriteItem:bool(skill.method("get_IsFavoriteItemSkill",0),skill)};
  };
  const countList=(fieldName)=>{
    const list=requireRef(spot.field(fieldName).value,fieldName);
    return {type:list.class.type.name,count:countCollection(list)};
  };
  const countEnumerable=(value,label)=>{
    if (!live(value)) return null;
    const iteratorBox=requireRef(call(value.method("GetEnumerator",0),value),
      label+" enumerator");
    const iterator=iteratorBox.class.isValueType?iteratorBox.unbox():iteratorBox;
    let count=0;
    while (bool(iterator.method("MoveNext",0),iterator)) {
      if (++count>100) throw new Error("Snapshot probe: excessive "+label+" records");
    }
    return {type:value.class.type.name,count};
  };
  const antiCheatEquip=spot.field("<NetAntiCheatItemDatasEquipsAndCube>k__BackingField").value;
  const antiCheatCube=spot.field("<NetAntiCheatItemDataCube>k__BackingField").value;
  const buff=spot.field("<BuffStaticInfos>k__BackingField").value;
  const convertedRow=requireRef(call(spot.method("get_CharacterStaticInfo",0),spot),
    "converted static row");
  if (!convertedRow.handle.equals(row.handle))
    throw new Error("Snapshot probe: converted static row changed");
  const output={status:"original_bare_snapshot_conversion_observed",
    source:"installed_original_CharacterSnapshot_conversion",
    requestMember:{nameCode:member.nameCode,level:member.level,grade:member.grade,
      core:member.core,skillLevels:member.skillLevels,barePolicy:bare,
      costumeTableId:options.costumeTableId},
    rowIdentity,constructorParameterTypes:actualTypes,
    nativeValues:{nameCode:i32(convertedRow.method("get_NameCode",0),convertedRow),
      positionType:getInt("PositionType"),buffStaticInfos:live(buff)?
        {type:buff.class.type.name,length:countCollection(buff)}:null,
      isSupportCharacter:getBool("IsSupportCharacter"),csn:getLong("CSN"),
      level:getInt("Level"),grade:getInt("Grade"),core:getInt("Core"),
      dps:getInt("DPS"),costumeTableId:getInt("CostumeTableId"),
      costumeIndex:getInt("CostumeIndex"),stats,
      skills:{skill1:readSkill("Skill1Data"),skill2:readSkill("Skill2Data"),
        burst:readSkill("SkillBurstData")},
      harmonyCubeTableId:getInt("HarmonyCubeTableIdID"),
      useBurstSkill:getInt("UseBurstSkill"),
      changeBurstStep:getInt("ChangeBurstStep"),
      battlePower:getInt("BattlePower"),
      overrideElements:countList("OverrideElements"),
      addedPassiveList:countList("<AddedPassiveList>k__BackingField"),
      antiCheatEquipment:countEnumerable(antiCheatEquip,"anti-cheat equipment"),
      antiCheatCube:live(antiCheatCube)?
        {type:antiCheatCube.class.type.name,present:true}:null},
    conversionBoundary:{singleCharacterOnly:true,teamPositionAndBuffsNotApplied:true,
      battleFixtureChanged:false},
    sourceRvas:{snapshotCtor:"0x06B2A3B0",convert:"0x06B27E70",
      convertStatus:"0x06B28770",teamSet:"0x06B28F10",
      statBuild:"0x06C445A0",statCalc:"0x06C47100"}};
  if (output.nativeValues.nameCode!==member.nameCode ||
      output.nativeValues.level!==member.level ||
      output.nativeValues.grade!==0 || output.nativeValues.core!==0 ||
      output.nativeValues.costumeTableId!==0)
    throw new Error("Snapshot probe: converted identity/investment mismatch");
  for (const [key,definition,level] of [
    ["skill1",skill1,member.skillLevels["1"]],
    ["skill2",skill2,member.skillLevels["2"]],
    ["burst",skill3,member.skillLevels["3"]]]) {
    const converted=output.nativeValues.skills[key];
    if (converted.favoriteItem || converted.disabled || converted.level!==level ||
        converted.groupId!==i32(definition.method("get_Group_id",0),definition))
      throw new Error("Snapshot probe: bare original skill conversion mismatch "+key);
  }
  return {spot,output};
}

// The historical one-character diagnostic remains read-only and does not
// install its converted SpotCharacterData into the battle transporter.
function probeMechanicsSnapshot(runtimeImage, staticImage, selectedRow, member,
    pin, emit, options) {
  const converted=convertMechanicsBareSnapshot(runtimeImage,staticImage,
    selectedRow,member,pin,options);
  emit(converted.output);
  return converted.output;
}
