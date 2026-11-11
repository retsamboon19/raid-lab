// Original153 build evaluation. This module has no captured snapshot/stat input,
// damage arithmetic, account lookup, saved inventory mutation, or battle start.
// IDs are data-only selections from the exact153 tables; native builders resolve
// their original stat providers, item effects and favorite skill replacements.
function buildNativeTeam153(runtime, staticImage, pin, emit, input, binding) {
  'use strict';
  binding = binding || globalThis.NATIVE_BUILD_BINDING153;
  const CLIENT = 'd39896d3770888039c728a1908448c3db5efa7cdf874c90d56f46d8d566428d2';
  if (!runtime || !staticImage || typeof pin !== 'function' || typeof emit !== 'function' ||
      typeof invokeChecked !== 'function' || !binding || binding.clientSha256 !== CLIENT ||
      !input || input.schemaVersion !== 1 || input.clientSha256 !== CLIENT ||
      !Array.isArray(input.characters) || input.characters.length !== 5)
    throw Error('Exact original153 custom build input and source binding required');
  const game = Process.getModuleByName('GameAssembly.dll'), roots = [], rawBuffers = [], cache = new Map();
  const retain = value => {
    if (value == null || value.isNull()) throw Error('Missing original native build object');
    pin(value); roots.push(value); return value;
  };
  const call = (method, self = null, args = []) => invokeChecked(method, self, args);
  const hex = bytes => Array.from(new Uint8Array(bytes), value => value.toString(16).padStart(2, '0')).join('');
  const i32arg = value => {
    if (!Number.isSafeInteger(value) || value < -2147483648 || value > 2147483647)
      throw Error('Custom build Int32 range');
    const data = Memory.alloc(4); data.writeS32(value); rawBuffers.push(data); return data;
  };
  const i64arg = value => {
    if (typeof value !== 'string' || !/^[1-9][0-9]{0,18}$/.test(value) || BigInt(value) > 9223372036854775807n)
      throw Error('Custom build serial must be a positive Int64 decimal string');
    const data = Memory.alloc(8); data.writeS64(int64(value)); rawBuffers.push(data); return data;
  };
  function klass(name) {
    if (cache.has(name)) return cache.get(name);
    const entry = Object.values(binding.methods).find(row => row.className === name);
    if (!entry) throw Error('Missing exact153 native class binding ' + name);
    const image = entry.assembly === 'NK.Runtime.dll' ? runtime : staticImage;
    let found = null;
    const parts = name.split('.');
    for (let end = parts.length; end > 0 && !found; end--) {
      try {
        let candidate = image.class(parts.slice(0, end).join('.'));
        for (const nested of parts.slice(end)) candidate = candidate.nested(nested);
        found = candidate;
      } catch (_) { /* Try the enclosing source type for a nested class. */ }
    }
    if (!found) throw Error('Original153 class missing ' + name);
    const layout = binding.layouts[name];
    if (layout && (found.isValueType !== layout.isValueType ||
        (layout.valueSize !== null && found.valueTypeSize !== layout.valueSize)))
      throw Error('Original153 value layout differs ' + name);
    cache.set(name, found); return found;
  }
  function bound(name, methodName, types = null) {
    const candidates = Object.values(binding.methods).filter(row => row.className === name && row.name === methodName &&
      (types === null || row.parameters.map(parameter => parameter.type).join('|') === types.join('|')));
    if (candidates.length !== 1) throw Error('One source-bound153 method required ' + name + '.' + methodName);
    const source = candidates[0], cls = klass(name);
    const method = cls.method(methodName).overload(...source.parameters.map(parameter => parameter.type));
    if (!method.virtualAddress.equals(game.base.add(source.nativeRva)) ||
        hex(method.virtualAddress.readByteArray(16)) !== source.entryHex || method.returnType.name !== source.returns)
      throw Error('Original153 native method binding differs ' + name + '.' + methodName);
    return method;
  }
  const get32 = (value, name) => retain(call(value.method('get_' + name, 0), value)).unbox().handle.readS32();
  const get64 = (value, name) => retain(call(value.method('get_' + name, 0), value)).unbox().handle.readS64().toString();
  const getBool = (value, name) => retain(call(value.method('get_' + name, 0), value)).unbox().handle.readU8() !== 0;
  const getRef = (value, name) => retain(call(value.method('get_' + name, 0), value));
  const obj = (name, types, args) => {
    const value = retain(klass(name).alloc());
    call(bound(name, '.ctor', types), klass(name).isValueType ? value.unbox() : value, args);
    return value;
  };
  const setArray = Il2Cpp.corlib.class('System.Array').method('SetValue').overload('System.Object', 'System.Int32');
  function array(cls, items) {
    const value = Il2Cpp.array(cls, items.length); retain(value.object);
    items.forEach((item, index) => call(setArray, value.object, [item.handle, i32arg(index)]));
    return value;
  }
  function items(value) {
    const isArray = value.class.type.name.endsWith('[]');
    const count = isArray ? retain(call(Il2Cpp.corlib.class('System.Array').method('get_Length', 0), value)).unbox().handle.readS32() : get32(value, 'Count');
    if (count < 0 || count > 256) throw Error('Original native build collection bound');
    const getter = isArray ? Il2Cpp.corlib.class('System.Array').method('GetValue').overload('System.Int32') : value.method('get_Item', 1);
    return Array.from({length: count}, (_, index) => retain(call(getter, value, [i32arg(index)])));
  }
  function intArray(values) {
    const cls = Il2Cpp.corlib.class('System.Int32');
    const box = new NativeFunction(game.getExportByName('il2cpp_value_box'), 'pointer', ['pointer', 'pointer']);
    return array(cls, values.map(value => retain(new Il2Cpp.Object(box(cls.handle, i32arg(value))))));
  }
  const U = 'NK.Common.System.UserData.', S = 'NK.Common.System.Stat.';
  const builderName = S + 'StatCalculateInfo.Builder';
  const equipRecord = builderName + '.StatCalculateParameterEquipmentRecord';
  const cubeRecord = builderName + '.StatCalculateParameterHarmonyCubeRecord';
  const effectsName = U + 'CharacterSnapshot.ItemStateEffects', effectBuilder = effectsName + '.Builder';
  const manager = retain(call(bound('NK.StaticData.DataManager', 'get_Instance')));
  const tables = {};
  function row(table, id) {
    if (!tables[table]) tables[table] = retain(call(bound('NK.StaticData.DataManager', 'get_' + table + 'Table'), manager));
    return retain(call(bound('NK.StaticData.DataTables.' + table + 'Table', 'FindById'), tables[table], [i32arg(id)]));
  }
  function range(value, lo, hi, label) {
    if (!Number.isSafeInteger(value) || value < lo || value > hi) throw Error('Invalid native build ' + label);
  }
  const helper = obj(S + 'CharacterStatHelper', [], []);
  if (get32(retain(helper.field('_calcs').value), 'Count') !== 7)
    throw Error('Original native stat provider set differs');
  const snapshots = [], converted = [], reports = [], characters = [], expectedCharacters = [];
  const serials = new Set();
  for (let index = 0; index < input.characters.length; index++) {
    const member = input.characters[index];
    range(member.slot, 1, 5, 'slot');
    if (member.slot !== index + 1) throw Error('Native custom team slots must be ordered1..5');
    range(member.level, 1, 1000, 'level'); range(member.affinity, 0, 40, 'affinity');
    range(member.grade, 0, 3, 'grade'); range(member.core, 0, 7, 'core');
    range(member.costumeTableId, 0, 2147483647, 'costume');
    if (!Array.isArray(member.skillLevels) || member.skillLevels.length !== 3) throw Error('Three native skill levels required');
    member.skillLevels.forEach(level => range(level, 1, 10, 'skill level'));
    if (!Array.isArray(member.equipment) || member.equipment.length > 4 || !Array.isArray(member.research) ||
        member.research.length > 3 || !Array.isArray(member.overload) || member.overload.length > 12)
      throw Error('Native investment collection bounds');
    if (serials.has(member.serialNumber)) throw Error('Duplicate per-job native character serial');
    serials.add(member.serialNumber);
    const selected = row('Character', member.characterTableId), gradeCore = getRef(selected, 'GradeCore');
    if (get32(selected, 'TableId') !== member.characterTableId || get32(selected, 'NameCode') !== member.nameCode ||
        get32(gradeCore, 'Grade') !== member.grade || get32(gradeCore, 'Core') !== member.core)
      throw Error('Original character identity/grade/core differs from requested build');
    const builder = obj(builderName, ['NK.StaticData.Categoricals.CharacterTableId'], [i32arg(member.characterTableId)]);
    call(bound(builderName, 'SetCharacterLevel', ['System.Int32']), builder, [i32arg(member.level)]);
    call(bound(builderName, 'SetAttractiveLevel', ['System.Int32']), builder, [i32arg(member.affinity)]);
    const equipmentSlots = new Set(), equipmentReadback = [];
    const equipment = member.equipment.map(item => {
      range(item.subType, 1, 4, 'equipment slot'); range(item.level, 0, 5, 'equipment level');
      range(item.corporationType, 0, 7, 'equipment corporation');
      if (equipmentSlots.has(item.subType)) throw Error('Duplicate native equipment slot');
      equipmentSlots.add(item.subType);
      const source = row('ItemEquip', item.tableId);
      if (get32(source, 'TableId') !== item.tableId || get32(source, 'ItemSubType') !== item.subType ||
          get32(source, 'Class') !== get32(selected, 'Class')) throw Error('Native equipment source/class mismatch');
      const value = obj(equipRecord, ['NK.StaticData.Categoricals.ItemTableId', 'System.Int32', 'NK.StaticData.CorporationType'],
        [i32arg(item.tableId), i32arg(item.level), i32arg(item.corporationType)]);
      if (get32(value, 'ItemTableId') !== item.tableId || get32(value, 'Level') !== item.level ||
          get32(value, 'CorporationType') !== item.corporationType) throw Error('Original equipment record readback mismatch');
      return value;
    });
    const equipmentArray = array(klass(equipRecord), equipment);
    call(bound(builderName, 'SetEquipment', ['System.Collections.Generic.IEnumerable<' + equipRecord + '>']), builder, [equipmentArray.handle]);
    if (member.cube !== null) {
      const cube = member.cube; range(cube.level, 1, 15, 'cube level');
      const cubeSource = row('ItemHarmonyCube', cube.tableId);
      if (get32(cubeSource, 'TableId') !== cube.tableId || get32(cubeSource, 'ItemSubType') !== cube.subType)
        throw Error('Native cube table identity mismatch');
      const record = obj(cubeRecord, ['NK.StaticData.Categoricals.ItemTableId', 'System.Int32'], [i32arg(cube.tableId), i32arg(cube.level)]);
      call(bound(builderName, 'SetHarmonyCube', [cubeRecord]), builder, [record.handle]);
    }
    const researchType = S + 'RecycleDataProvider';
    const research = member.research.map(item => {
      range(item.subType, 0, 2147483647, 'research subtype'); range(item.level, 0, 1000, 'research level');
      return obj(researchType, ['NK.StaticData.RecycleSubType', 'System.Int32'], [i32arg(item.subType), i32arg(item.level)]);
    });
    const researchArray = array(klass(researchType), research);
    call(bound(builderName, 'SetRecycleResearch', ['System.Collections.Generic.IEnumerable<' + researchType + '>']), builder, [researchArray.handle]);
    let favorite = null;
    if (member.favorite !== null) {
      const item = member.favorite; range(item.level, 0, 2147483647, 'favorite/collection level');
      favorite = row('FavoriteItem', item.tableId);
      if (get32(favorite, 'TableId') !== item.tableId || item.level > get32(favorite, 'Max_level') ||
          (get32(favorite, 'Name_code') !== 0 && get32(favorite, 'Name_code') !== member.nameCode))
        throw Error('Native collection/favorite source identity or level differs');
      call(bound(builderName, 'SetFavoriteItem', ['NK.StaticData.Categoricals.FavoriteItemTableId', 'System.Int32']),
        builder, [i32arg(item.tableId), i32arg(item.level)]);
    }
    const calculation = retain(call(bound(builderName, 'Build'), builder));
    const statInputs = {tableId: get32(getRef(calculation, 'CharacterStaticInfo'), 'TableId'),
      grade: get32(calculation, 'Grade'), core: get32(calculation, 'Core'),
      level: get32(calculation, 'CharacterLevel'), affinity: get32(calculation, 'AttractiveLevel')};
    if (statInputs.tableId !== member.characterTableId || statInputs.grade !== member.grade || statInputs.core !== member.core ||
        statInputs.level !== member.level || statInputs.affinity !== member.affinity)
      throw Error('Original stat-builder input readback differs');
    const calculated = retain(call(bound(S + 'CharacterStatHelper', 'Calc', [S + 'StatCalculateInfo']), helper, [calculation.handle]));
    const nativeCalculatedStats = {};
    for (const field of ['Attack', 'Defense', 'Hp', 'EnergyResist', 'MetalResist', 'BioResist'])
      nativeCalculatedStats[field] = get64(calculated.unbox(), field);
    const equipsBuilderName = U + 'EquipsAndCube.Builder', equipsBuilder = obj(equipsBuilderName, [], []);
    for (const item of member.equipment.concat(member.cube === null ? [] : [member.cube])) {
      call(bound(equipsBuilderName, 'Set', ['NK.StaticData.ItemSubType', 'NK.StaticData.Categoricals.ItemSerialNumber',
        'NK.StaticData.Categoricals.ItemTableId', 'System.Int32']), equipsBuilder,
      [i32arg(item.subType), i64arg(item.serialNumber), i32arg(item.tableId), i32arg(item.level)]);
    }
    const equips = retain(call(bound(equipsBuilderName, 'Build'), equipsBuilder));
    const dict = retain(equips.field('_dict').value);
    for (const item of member.equipment.concat(member.cube === null ? [] : [member.cube])) {
      const record = retain(call(dict.method('get_Item', 1), dict, [i32arg(item.subType)]));
      const readback = {subType: item.subType, serialNumber: get64(record, 'Isn'), tableId: get32(record, 'Tid'), level: get32(record, 'Level')};
      if (readback.serialNumber !== item.serialNumber || readback.tableId !== item.tableId || readback.level !== item.level)
        throw Error('Original equipment snapshot readback differs');
      equipmentReadback.push(readback);
    }
    const effectBuild = retain(call(bound(effectBuilder, 'Create')));
    if (member.cube !== null) {
      const recordName = effectsName + '.CubeAndLevel';
      const record = obj(recordName, ['NK.StaticData.Categoricals.ItemTableId', 'System.Int32'],
        [i32arg(member.cube.tableId), i32arg(member.cube.level)]);
      call(bound(effectBuilder, 'AddHarmonyCube', [recordName]), effectBuild, [record.handle]);
    }
    if (favorite !== null) {
      const recordName = effectsName + '.FavoriteItemAndLevel';
      const record = obj(recordName, ['NK.StaticData.Categoricals.FavoriteItemTableId', 'System.Int32'],
        [i32arg(member.favorite.tableId), i32arg(member.favorite.level)]);
      call(bound(effectBuilder, 'AddFavoriteItemTable', [recordName]), effectBuild, [record.handle]);
    }
    const generatedEffects = retain(call(bound(effectBuilder, 'Build'), effectBuild));
    const generatedEffectIds = items(getRef(generatedEffects, 'TidList')).map(value => value.unbox().handle.readS32());
    const overloadIds = member.overload.map(item => { range(item.stateEffectTid, 1, 2147483647, 'Overload source effect'); return item.stateEffectTid; });
    // Original awakening producer yields Option1Id/2Id/3Id directly, filtering
    // zero. Preserve multiplicity: repeated valid source rolls stack normally.
    const allEffects = intArray(overloadIds.concat(generatedEffectIds));
    const effects = retain(call(bound(effectsName, 'FromTidList'), null, [allEffects.handle]));
    const identityBox = retain(call(bound(U + 'NKCharacterInfo', 'CreateCharacter'), null, [i64arg(member.serialNumber)]));
    const create = bound(U + 'CharacterSnapshot', 'CreateDummyCharacter');
    const noneClass = create.parameters[5].type.class;
    if (!noneClass.isValueType || noneClass.valueTypeSize !== 16) throw Error('Original skill-disable Option ABI differs');
    const none = retain(noneClass.alloc());
    if (!/^0{32}$/.test(hex(none.unbox().handle.readByteArray(16)))) throw Error('Original empty Option payload differs');
    const favoriteGroups = [1, 2, 3].map(slot => favorite === null ? null : call(bound('NK.UI.Popup.CharacterSkill.SkillUtility',
      'TryGetSlotSkillGroupData'), null, [favorite.handle, i32arg(member.favorite.level), i32arg(slot)]));
    favoriteGroups.forEach(value => { if (value !== null && !value.isNull()) retain(value); });
    const snapshot = retain(call(create, null, [selected.handle, identityBox.unbox().handle, calculated.unbox().handle,
      equips.handle, effects.handle, none.unbox().handle, i32arg(member.level), i32arg(member.costumeTableId),
      ...member.skillLevels.map(i32arg), ...favoriteGroups.map(value => value === null || value.isNull() ? ptr(0) : value.handle)]));
    const spot = retain(call(bound(U + 'CharacterSnapshotExtension', 'CreateSpotCharacterData'), null, [snapshot.handle]));
    const status = spot.field('StatusData').value, nativeStats = {}, nativeValues = {}, nativeSkills = {};
    for (const name of ['HealthPoint', 'Attack', 'Defense', 'EnergyResist', 'MetalResist', 'BioResist', 'CriticalRatio', 'CriticalDamage', 'HPRatio'])
      nativeStats[name] = status.field(name).value.field('Value').value.toString();
    for (const [name, calculatedName] of [['HealthPoint', 'Hp'], ['Attack', 'Attack'], ['Defense', 'Defense'],
      ['EnergyResist', 'EnergyResist'], ['MetalResist', 'MetalResist'], ['BioResist', 'BioResist']])
      if (nativeStats[name] !== nativeCalculatedStats[calculatedName])
        throw Error('Original native converter changed calculated build stat ' + name);
    for (const name of ['Level', 'Grade', 'Core', 'BattlePower', 'CostumeTableId', 'HarmonyCubeTableIdID']) nativeValues[name] = get32(spot, name);
    for (const name of ['Skill1Data', 'Skill2Data', 'SkillBurstData']) {
      const skill = retain(spot.field(name).value);
      nativeSkills[name] = {GroupId: get32(skill, 'GroupId'), Level: get32(skill, 'Level'), TableType: get32(skill, 'TableType'),
        Disable: getBool(skill, 'Disable'), IsFavoriteItemSkill: getBool(skill, 'IsFavoriteItemSkill')};
    }
    const addedPassiveRecordIds = items(retain(spot.field('<AddedPassiveList>k__BackingField').value)).map(value => get32(value, 'TableId'));
    const csn = get64(spot, 'CSN');
    const originalEffectIds = items(getRef(snapshot, 'ItemStateEffectTidList')).map(value => value.unbox().handle.readS32());
    if (JSON.stringify(originalEffectIds) !== JSON.stringify(overloadIds.concat(generatedEffectIds)))
      throw Error('Original native snapshot changed selected item effect identity/multiplicity');
    if (csn !== member.serialNumber || nativeValues.Level !== member.level || nativeValues.Grade !== member.grade ||
        nativeValues.Core !== member.core || nativeValues.CostumeTableId !== member.costumeTableId ||
        nativeValues.HarmonyCubeTableIdID !== (member.cube === null ? 0 : member.cube.tableId) ||
        nativeSkills.Skill1Data.Level !== member.skillLevels[0] || nativeSkills.Skill2Data.Level !== member.skillLevels[1] ||
        nativeSkills.SkillBurstData.Level !== member.skillLevels[2]) throw Error('Original custom snapshot conversion input readback differs');
    const report = {status: 'original_native_character_build_prepared', passed: true, slot: member.slot,
      csn, characterTableId: member.characterTableId, nameCode: member.nameCode, statInputs, nativeCalculatedStats,
      nativeStats, nativeValues, nativeSkills, addedPassiveRecordIds, equipmentReadback,
      itemStateEffectTids: overloadIds.concat(generatedEffectIds), capturedStatPayloadUsed: false,
      pythonStatMathUsed: false, battleStarted: false};
    emit(report); reports.push(report); snapshots.push(snapshot); converted.push(spot);
    characters.push({slot: member.slot, sourceCsn: csn, characterTableId: member.characterTableId, sourceNameCode: member.nameCode});
    expectedCharacters.push({slot: member.slot, sourceCsn: csn,
      nativeConversion: {stats: nativeStats, values: nativeValues, skills: nativeSkills, addedPassiveRecordIds}});
  }
  // Actual native outputs are assertion-only data. All original calculations,
  // snapshots and converters above finish before this gate reads expectations.
  // A mismatch throws before the caller can prepare a fixture or call OnInit.
  if (input.prebattleMatch !== undefined) {
    const expected = input.prebattleMatch;
    if (!expected || expected.schemaVersion !== 1 || expected.source !== 'original153-actual-prebattle-native-readback' ||
        !/^[0-9a-f]{64}$/.test(expected.actualCaptureSha256 || '') || !Array.isArray(expected.characters) || expected.characters.length !== 5)
      throw Error('Original actual prebattle match source differs');
    const allowed = new Set(['slot', 'characterTableId', 'nameCode', 'nativeValues', 'nativeStats', 'nativeCalculatedStats',
      'nativeSkills', 'addedPassiveRecordIds', 'itemStateEffectTids']);
    const mismatches = [];
    let fieldsCompared = 0;
    function compare(wanted, observed, field, slot) {
      if (wanted !== null && typeof wanted === 'object' && !Array.isArray(wanted)) {
        if (observed === null || typeof observed !== 'object' || Array.isArray(observed)) {
          mismatches.push({slot, field, expected: wanted, actual: observed}); return;
        }
        for (const [key, value] of Object.entries(wanted)) compare(value, observed[key], field + '.' + key, slot);
        return;
      }
      fieldsCompared++;
      if (Array.isArray(wanted) ? JSON.stringify(wanted) !== JSON.stringify(observed) : wanted !== observed)
        mismatches.push({slot, field, expected: wanted, actual: observed});
    }
    expected.characters.forEach((wanted, index) => {
      if (!wanted || Object.keys(wanted).some(key => !allowed.has(key)) || wanted.slot !== index + 1 ||
          wanted.characterTableId !== reports[index].characterTableId || wanted.nameCode !== reports[index].nameCode ||
          !wanted.nativeValues || !Number.isInteger(wanted.nativeValues.BattlePower))
        throw Error('Five ordered actual native identities and per-character combat powers required');
      for (const [key, value] of Object.entries(wanted)) compare(value, reports[index][key], key, index + 1);
    });
    const gate = {status: 'original_native_prebattle_match', passed: mismatches.length === 0,
      actualCaptureSha256: expected.actualCaptureSha256, requestSha256: globalThis.NATIVE_BATTLE_REQUEST_SHA256 || input.inputSourceSha256,
      fieldsCompared, mismatches, expectedCombatPowers: expected.characters.map(value => value.nativeValues.BattlePower),
      nativeCombatPowers: reports.map(value => value.nativeValues.BattlePower), beforeOnInit: true, battleStarted: false,
      expectedValuesUsedAsConstructorInputs: false, pythonStatMathUsed: false};
    emit(gate);
    if (!gate.passed) throw Error('Original native prebattle build/CP match failed before OnInit: ' + JSON.stringify(mismatches));
  }
  emit({status: 'original_native_build_prepared', passed: true,
    requestSha256: globalThis.NATIVE_BATTLE_REQUEST_SHA256 || input.inputSourceSha256,
    characters: characters.map(value => ({slot: value.slot, tableId: value.characterTableId, nameCode: value.sourceNameCode})), reports});
  return {snapshots, converted, reports, roots, rawBuffers, passed: true, characters,
    expected: {characters: expectedCharacters}, source: 'Exact153 original StatCalculateInfo/CharacterStatHelper/CharacterSnapshot'};
}
