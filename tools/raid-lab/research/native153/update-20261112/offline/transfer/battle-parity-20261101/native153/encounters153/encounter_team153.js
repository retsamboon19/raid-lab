// Original team creation and original Museum passive-input preparation.
// This follows the actual entry caller's native typed calls. It does not write
// character/monster stats or replace native damage, HP, conditions or results.
function prepareNative153EncounterTeam(runtime, staticImage, pin, emit, modeInput, replay) {
  'use strict';
  validateNative153EncounterInput(modeInput);
  const encounter = native153EncounterSpec(modeInput);
  if (encounter.contentMode === 'campaign') {
    if (typeof prepareNative153CampaignTeam !== 'function')
      throw Error('Original campaign team/CP input constructor is required');
    const prepared = prepareNative153CampaignTeam(runtime, staticImage, pin, emit, modeInput, replay);
    if (!prepared || !prepared.team || !prepared.expected || !prepared.readback || prepared.readback.passed !== true)
      throw Error('Original campaign team/CP preparation did not return verified native inputs');
    const receipt = {...prepared.readback, status: 'original153_encounter_team_prepared', passed: true,
      encounterId: encounter.id, requestSha256: modeInput.requestSha256 || globalThis.NATIVE_BATTLE_REQUEST_SHA256};
    emit(receipt);
    return {...prepared, characters: replay.characters, transporterBindings: {}, receipt, passed: true};
  }
  if (!replay || replay.passed !== true || !Array.isArray(replay.snapshots) || replay.snapshots.length !== 5 ||
      !Array.isArray(replay.characters) || replay.characters.length !== 5)
    throw Error('Five current-job native selected build snapshots required');
  const api = native153EncounterApi(runtime, staticImage), roots = [], rawBuffers = [];
  const keep = value => { if (!value || value.isNull()) throw Error('Original encounter team input object absent'); pin(value); roots.push(value); return value; };
  const arg32 = value => { const data = Memory.alloc(4); data.writeS32(value); rawBuffers.push(data); return data; };
  const zero64 = Memory.alloc(8); zero64.writeS64(int64('0')); rawBuffers.push(zero64);
  const arrays = Il2Cpp.corlib.class('System.Array');
  const set = arrays.method('SetValue').overload('System.Object', 'System.Int32');
  const snapshots = Il2Cpp.array(runtime.class('NK.Common.System.UserData.CharacterSnapshot'), 5); keep(snapshots.object);
  replay.snapshots.forEach((snapshot, index) => api.call(set, snapshots.object, [snapshot.handle, arg32(index)]));
  const team = keep(api.call(api.method('NK.Common.System.UserData.CharacterSnapshotExtension', 'CreateSpotTeamData', [
    'System.Collections.Generic.IReadOnlyList<NK.Common.System.UserData.CharacterSnapshot>',
    'System.Collections.Generic.List<NK.StaticData.StaticDataLayer.StaticInfo.BuffStaticInfo[]>', 'System.Int32']),
  null, [snapshots.handle, ptr(0), arg32(0)]));
  const groups = keep(team.field('<CharacterDataList>k__BackingField').value);
  if (api.read32(groups, 'Count') !== 1) throw Error('Original single-team encounter group count differs');
  const members = keep(api.call(groups.method('get_Item', 1), groups, [arg32(0)]));
  if (api.read32(members, 'Count') !== 5) throw Error('Original encounter team member count differs');
  const nativeMembers = Array.from({length: 5}, (_, index) => keep(api.call(members.method('get_Item', 1), members, [arg32(index)])));
  const modePassiveIds = [];
  if (encounter.contentMode === 'museum') {
    const context = encounter.context;
    if (!context || !Number.isSafeInteger(context.stageBuffSkillId) || context.stageBuffSkillId <= 0 ||
        !Object.prototype.hasOwnProperty.call(context, 'selectedWeeklyBuffSkillId') ||
        !Number.isSafeInteger(context.selectedWeeklyBuffSkillId) || context.selectedWeeklyBuffSkillId < 0)
      throw Error('Original Museum base passive and explicit weekly selection required');
    modePassiveIds.push(context.stageBuffSkillId);
    if (context.selectedWeeklyBuffSkillId !== 0) {
      if (!Array.isArray(context.weeklyBuffOptions) || !context.weeklyBuffOptions.some(row => row.skillId === context.selectedWeeklyBuffSkillId))
        throw Error('Museum weekly passive does not belong to the selected original stage');
      modePassiveIds.push(context.selectedWeeklyBuffSkillId);
    }
    const manager = keep(api.call(api.method('NK.StaticData.DataManager', 'get_Instance', [])));
    const table = keep(api.call(api.method('NK.StaticData.DataManager', 'get_StateEffectTable', []), manager));
    const effects = modePassiveIds.map(id => {
      const effect = keep(api.call(api.method('NK.StaticData.DataTables.StateEffectTable', 'FindById', ['System.Int32']), table, [arg32(id)]));
      if (api.read32(effect, 'TableId') !== id) throw Error('Original Museum state-effect table identity differs');
      return effect;
    });
    for (const member of nativeMembers) {
      const passives = keep(member.field('<AddedPassiveList>k__BackingField').value), add = passives.method('Add', 1);
      if (add.parameters.length !== 1 || add.parameters[0].type.name !== 'NK.StaticData.StaticDataLayer.StaticInfo.StateEffectStaticInfo' ||
          add.returnType.name !== 'System.Void') throw Error('Original typed Museum passive-list Add ABI differs');
      const source = api.binding.raidPassiveAdd;
      const actual = Array.from(new Uint8Array(add.virtualAddress.readByteArray(16)), value => value.toString(16).padStart(2, '0')).join('');
      if (!source || !add.virtualAddress.equals(api.game.base.add(source.nativeRva)) || actual !== source.entryHex)
        throw Error('Original Museum caller typed-list Add native entry differs');
      // Original EnterSpotFromSoloRaidMuseumUnit appends the base effect, then
      // its optional weekly effect to this exact native list before combat.
      effects.forEach(effect => api.call(add, passives, [effect.handle]));
    }
  }
  const get64 = (value, name) => api.call(value.method('get_' + name, 0), value).unbox().handle.readS64().toString();
  const getBool = (value, name) => api.call(value.method('get_' + name, 0), value).unbox().handle.readU8() !== 0;
  const expectedCharacters = nativeMembers.map((member, index) => {
    const identity = replay.characters[index], stats = {}, values = {}, skills = {};
    const status = member.field('StatusData').value;
    for (const name of ['HealthPoint', 'Attack', 'Defense', 'EnergyResist', 'MetalResist', 'BioResist', 'CriticalRatio', 'CriticalDamage', 'HPRatio'])
      stats[name] = status.field(name).value.field('Value').value.toString();
    for (const name of ['Level', 'Grade', 'Core', 'BattlePower', 'CostumeTableId', 'HarmonyCubeTableIdID']) values[name] = api.read32(member, name);
    for (const name of ['Skill1Data', 'Skill2Data', 'SkillBurstData']) {
      const skill = keep(member.field(name).value);
      skills[name] = {GroupId: api.read32(skill, 'GroupId'), Level: api.read32(skill, 'Level'), TableType: api.read32(skill, 'TableType'),
        Disable: getBool(skill, 'Disable'), IsFavoriteItemSkill: getBool(skill, 'IsFavoriteItemSkill')};
    }
    const passives = keep(member.field('<AddedPassiveList>k__BackingField').value), count = api.read32(passives, 'Count');
    if (count < 0 || count > 256) throw Error('Native encounter passive count bound');
    const addedPassiveRecordIds = Array.from({length: count}, (_, itemIndex) =>
      api.read32(keep(api.call(passives.method('get_Item', 1), passives, [arg32(itemIndex)])), 'TableId'));
    const original = replay.expected.characters[index].nativeConversion.addedPassiveRecordIds;
    if (JSON.stringify(addedPassiveRecordIds) !== JSON.stringify(original.concat(modePassiveIds)))
      throw Error('Original encounter passive identity/order differs from original entry policy');
    if (get64(member, 'CSN') !== identity.sourceCsn || api.read32(member, 'PositionType') !== identity.slot)
      throw Error('Original encounter team conversion changed ordered native identities');
    return {slot: identity.slot, sourceCsn: identity.sourceCsn,
      nativeConversion: {stats, values, skills, addedPassiveRecordIds}};
  });
  const transporterBindings = {};
  let raidContext = null;
  if (encounter.contentMode === 'museum' || encounter.contentMode === 'solo') {
    const name = 'NK.Spot.Data.SpotSoloRaidContextData';
    raidContext = keep(runtime.class(name).alloc());
    // Fresh isolated simulations have no accumulated prior-team damage and do
    // not consume account entries. These three fields are original UI/result
    // context, separate from monster HP and all combat stat providers.
    api.call(api.method(name, '.ctor', ['System.Int64', 'System.Int32', 'System.Int32']), raidContext,
      [zero64, arg32(0), arg32(0)]);
    if (raidContext.field('TrialDamage').value.field('Value').value.toString() !== '0' ||
        Number(raidContext.field('RemainEnterCount').value) !== 0 || Number(raidContext.field('MaxEnterCount').value) !== 0)
      throw Error('Original isolated raid context constructor readback differs');
    transporterBindings['<SpotContextData>k__BackingField'] = {value: raidContext,
      receipt: {kind: 'original_private_native_owner', sourceNativeType: 'NK.Spot.Data.SpotContextData',
        receiptSha256: api.binding.raidInputSourceSha256, originalConstructorInvoked: true,
        accountProgressReused: false, trialDamage: '0', remainEnterCount: 0, maxEnterCount: 0}};
  }
  const receipt = {status: 'original153_encounter_team_prepared', passed: true,
    encounterId: encounter.id, requestSha256: modeInput.requestSha256 || globalThis.NATIVE_BATTLE_REQUEST_SHA256,
    originalTeamConstructorInvoked: true, originalTypedPassiveAdds: modePassiveIds,
    museumBasePassive: encounter.contentMode === 'museum' ? encounter.context.stageBuffSkillId : null,
    selectedWeeklyPassive: encounter.contentMode === 'museum' ? encounter.context.selectedWeeklyBuffSkillId : null,
    statIncreaseValue: 0, targetMonsterHPPolicy: 'original_native_full_hp_with_zero_override_and_ratio',
    targetMonsterHPOverride: '0', targetMonsterHPRatio: 0, raidLevelChangeGroup: encounter.raidLvChangeGroup,
    originalRaidContextConstructed: raidContext !== null, accountProgressReused: false,
    characterStatsWritten: false, monsterStatsWritten: false, battleStarted: false};
  emit(receipt);
  return {team, expected: {characters: expectedCharacters}, expectedTeamReadbacks: expectedCharacters,
    characters: replay.characters, transporterBindings, spotContextData: raidContext,
    roots, rawBuffers, receipt, passed: true};
}
