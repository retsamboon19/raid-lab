// Original bare stat calculation. It never changes SpotCharacterData; the
// caller separately applies and reads back the computed nine status fields.
function calculateOriginalBareStats(runtimeImage, staticImage, characterStaticInfo,
    member, pin, emit, slot=null, requestSha256=null) {
  const call=(method,self=null,args=[])=>invokeChecked(method,self,args);
  const live=value=>value!=null && !value.isNull();
  const required=(value,label)=>{
    if (!live(value)) throw new Error("Bare stats: missing original "+label);
    return value;
  };
  const i32=(method,self=null)=>{
    const value=required(call(method,self),method.name);
    return value.unbox().handle.readS32();
  };
  const int64=(method,self)=>{
    const value=required(call(method,self),method.name);
    return value.unbox().handle.readS64().toString();
  };
  const arg=value=>{
    const buffer=Memory.alloc(4);
    buffer.writeS32(value);
    return buffer;
  };
  const selected=required(characterStaticInfo,"CharacterStaticInfo");
  const policy=member && member.barePolicy;
  const bare=policy && typeof policy==="object" && !Array.isArray(policy) &&
    Object.keys(policy).sort().join("|")===
      ["equipment","attractiveLevel","recycleResearch","harmonyCube","favoriteItem"]
        .sort().join("|") &&
    Array.isArray(policy.equipment) && policy.equipment.length===0 &&
    policy.attractiveLevel===0 &&
    Array.isArray(policy.recycleResearch) && policy.recycleResearch.length===0 &&
    policy.harmonyCube===null && policy.favoriteItem===null;
  if (!member || !Number.isSafeInteger(member.nameCode) ||
      !Number.isSafeInteger(member.level) || member.level<1 || member.level>1000 ||
      member.grade!==0 || member.core!==0 || !bare) {
    throw new Error("Bare stats: explicit member/policy is unsupported");
  }
  const rowClass=staticImage.class(
    "NK.StaticData.StaticDataLayer.StaticInfo.CharacterStaticInfo");
  if (selected.class.type.name!==rowClass.type.name) {
    throw new Error("Bare stats: unexpected selected character row "+selected.class.type.name);
  }
  const nameCode=i32(selected.method("get_NameCode",0),selected);
  const gradeCore=required(call(selected.method("get_GradeCore",0),selected),"GradeCore");
  const grade=i32(gradeCore.method("get_Grade",0),gradeCore);
  const core=i32(gradeCore.method("get_Core",0),gradeCore);
  const tableId=i32(selected.method("get_TableId",0),selected);
  if (nameCode!==member.nameCode || grade!==member.grade ||
      core!==member.core || tableId<=0) {
    throw new Error("Bare stats: selected row differs from explicit member; got "+
      JSON.stringify({nameCode,grade,core,tableId}));
  }
  const criticalRatio=i32(selected.method("get_CriticalRatio",0),selected);
  const criticalDamage=i32(selected.method("get_CriticalDamage",0),selected);
  if (!Number.isSafeInteger(criticalRatio) || criticalRatio<0 ||
      !Number.isSafeInteger(criticalDamage) || criticalDamage<0) {
    throw new Error("Bare stats: installed table critical values are invalid");
  }

  const infoClass=runtimeImage.class("NK.Common.System.Stat.StatCalculateInfo");
  const builderClass=infoClass.nested("Builder");
  const absent=[
    ["_equipments","System.Collections.Generic.IEnumerable"],
    ["_statCalculateParameterHarmonyCube","StatCalculateParameterHarmonyCubeRecord"],
    ["_statCalculateParameterFavoriteItem","StatCalculateParameterFavoriteItemRecord"],
    ["_recycleDataProviders","System.Collections.Generic.IEnumerable"]
  ];
  // These are reference fields in the installed metadata. A changed value
  // type/field contract must fail before running the original builder.
  for (const [fieldName,typePart] of absent) {
    const field=builderClass.field(fieldName);
    if (field.type.class.isValueType || !field.type.name.includes(typePart)) {
      throw new Error("Bare stats: nonnullable/changed builder field "+fieldName+
        ": "+field.type.name);
    }
  }
  const helper=runtimeImage.class("NK.Common.System.Stat.CharacterStatHelper");
  const calc=helper.method("Calc").overload(
    "NK.Common.System.Stat.StatCalculateInfo");
  const helperCtor=helper.method(".ctor",0);
  const assembly=Process.getModuleByName("GameAssembly.dll");
  const getMethodFlags=new NativeFunction(assembly.getExportByName(
    "il2cpp_method_get_flags"),"uint32",["pointer","pointer"]);
  const flags=method=>{
    const iflags=Memory.alloc(4);
    iflags.writeU32(0);
    return getMethodFlags(method.handle,iflags);
  };
  const calcFlags=flags(calc),ctorFlags=flags(helperCtor);
  if (calcFlags!==0x86 || ctorFlags!==0x1886 ||
      (calcFlags & 0x10)!==0 || (ctorFlags & 0x10)!==0) {
    throw new Error("Bare stats: original helper instance-method flags changed "+
      JSON.stringify({calcFlags,ctorFlags}));
  }
  // The original constructor installs all seven stat providers in _calcs.
  // Calc reads this receiver list; passing a null receiver faults at 0x06C4724F.
  const calculator=pin(helper.alloc());
  call(helperCtor,calculator);
  const providers=required(calculator.field("_calcs").value,
    "CharacterStatHelper._calcs");
  const providerCount=i32(providers.method("get_Count",0),providers);
  if (providerCount!==7)
    throw new Error("Bare stats: original helper did not install seven providers ("+
      providerCount+")");
  const level=member.level;
    const builder=pin(builderClass.alloc());
    // Allocated managed objects start with null reference investment fields.
    for (const [fieldName] of absent) {
      if (live(builder.field(fieldName).value))
        throw new Error("Bare stats: investment field nonnull before ctor "+fieldName);
    }
    call(builder.method(".ctor").overload("NK.StaticData.Categoricals.CharacterTableId"),
      builder,[arg(tableId)]);
    for (const [fieldName] of absent) {
      if (live(builder.field(fieldName).value))
        throw new Error("Bare stats: investment field nonnull after ctor "+fieldName);
    }
    call(builder.method("SetCharacterLevel").overload("System.Int32"),builder,[arg(level)]);
    call(builder.method("SetAttractiveLevel").overload("System.Int32"),builder,[arg(0)]);
    for (const [fieldName] of absent) {
      if (live(builder.field(fieldName).value))
        throw new Error("Bare stats: investment field nonnull before Build "+fieldName);
    }
    const info=pin(required(call(builder.method("Build",0),builder),"StatCalculateInfo"));
    const resolvedRow=required(call(info.method("get_CharacterStaticInfo",0),info),
      "built CharacterStaticInfo");
    const readback={tableId:i32(resolvedRow.method("get_TableId",0),resolvedRow),
      nameCode:i32(resolvedRow.method("get_NameCode",0),resolvedRow),
      grade:i32(info.method("get_Grade",0),info),
      core:i32(info.method("get_Core",0),info),
      level:i32(info.method("get_CharacterLevel",0),info),
      attractiveLevel:i32(info.method("get_AttractiveLevel",0),info)};
    if (readback.tableId!==tableId || readback.nameCode!==member.nameCode ||
        readback.grade!==member.grade || readback.core!==member.core ||
        readback.level!==level || readback.attractiveLevel!==member.barePolicy.attractiveLevel) {
      throw new Error("Bare stats: original builder readback mismatch "+
        JSON.stringify(readback));
    }
    const calculated=pin(required(call(calc,calculator,[info.handle]),
      "CharacterStatData"));
    const data=calculated.unbox();
    const stats={
      HealthPoint:int64(data.method("get_Hp",0),data),
      Attack:int64(data.method("get_Attack",0),data),
      Defense:int64(data.method("get_Defense",0),data),
      EnergyResist:int64(data.method("get_EnergyResist",0),data),
      MetalResist:int64(data.method("get_MetalResist",0),data),
      BioResist:int64(data.method("get_BioResist",0),data),
      CriticalRatio:criticalRatio,
      CriticalDamage:criticalDamage,
      // Original status converter 0x06B28770 writes this constant. It is
      // source-derived here, not an invoked CharacterSnapshot readback.
      HPRatio:10000
    };
    const row={status:"original_bare_character_stats_calculated",
      ...(slot===null?{}:{slot}),nameCode,
      ...(requestSha256===null?{}:{requestSha256}),
      source:"installed_original_stat_builder",
      selectedTableId:tableId,readback,stats,
      statProvenance:{sixCalculated:"CharacterStatHelper.Calc original int64 getters",
        critical:"selected CharacterStaticInfo original getters",
        HPRatio:"source constant in CreateSpotSpotCharacterData_Status; not invoked"},
      barePolicy:member.barePolicy,
      originalHelper:{calcFlags,constructorFlags:ctorFlags,providerCount},
      sourceRvas:{snapshotInternal:"0x06BC9B60",gradeCoreLookup:"0x04E18B70",
        builderCtor:"0x06C46840",
        setCharacterLevel:"0x06C45340",setAttractiveLevel:"0x06C45330",
        build:"0x06C445A0",helperConstructor:"0x06C47580",
        calc:"0x06C47100",
        hp:"0x06C1F7D0",attack:"0x069A2A00",defense:"0x06C1F750",
        energyResist:"0x06C1F790",metalResist:"0x06C1F810",
        bioResist:"0x06C1F710",criticalRatio:"0x04D45E40",
        criticalDamage:"0x04D45EF0",statusConverter:"0x06B28770"},
      fixtureStatsChanged:false};
    emit(row);
    return row;
}

// Retain the Crown 399/400 diagnostic from trial 90 for synthetic-mode
// regressions. Neither call applies its output to SpotCharacterData.
function probeMechanicsBareStats(runtimeImage, staticImage, characterStaticInfo, pin, emit) {
  const results=[];
  for (const level of [399,400]) {
    const member={nameCode:5065,level,grade:0,core:0,
      barePolicy:{equipment:[],attractiveLevel:0,recycleResearch:[],
        harmonyCube:null,favoriteItem:null}};
    const row=calculateOriginalBareStats(runtimeImage,staticImage,
      characterStaticInfo,member,pin,
      result=>emit({...result,status:"original_bare_character_stats_observed",
        character:"Crown",fixtureStatsChanged:false}));
    results.push(row);
  }
  return results;
}
