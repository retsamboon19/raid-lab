// Original153 encounter adapter. Source tables select the encounter; the original
// SpotLoader factory chooses the process and original context owns its rules.
// No monster stats, process conditions, clock, result or score are manufactured.
const NATIVE153_ENCOUNTER_CLIENT = 'd39896d3770888039c728a1908448c3db5efa7cdf874c90d56f46d8d566428d2';

function native153EncounterSpec(input) {
  return input && (input.encounter || input);
}

function native153EncounterApi(runtime, staticImage) {
  'use strict';
  const binding = globalThis.NATIVE153_ENCOUNTER_BINDING;
  if (!binding || binding.schemaVersion !== 1 || binding.clientSha256 !== NATIVE153_ENCOUNTER_CLIENT)
    throw Error('Exact original153 encounter binding required');
  const game = Process.getModuleByName('GameAssembly.dll');
  const hex = bytes => Array.from(new Uint8Array(bytes), value => value.toString(16).padStart(2, '0')).join('');
  const call = (method, self, args) => invokeChecked(method, self || null, args || []);
  const method = (className, name, parameterTypes) => {
    const choices = Object.values(binding.methods).filter(row => row.className === className && row.name === name &&
      (!parameterTypes || row.parameters.map(value => value.type).join('|') === parameterTypes.join('|')));
    if (choices.length !== 1) throw Error('One exact encounter method required: ' + className + '.' + name);
    const source = choices[0], image = source.assembly === 'NK.Runtime.dll' ? runtime : staticImage;
    const klass = image.class(className), result = klass.method(name).overload(...source.parameters.map(value => value.type));
    if (!result.virtualAddress.equals(game.base.add(source.nativeRva)) || result.returnType.name !== source.returns ||
        result.isStatic !== !!(source.flags & 16) || hex(result.virtualAddress.readByteArray(16)) !== source.entryHex)
      throw Error('Original153 encounter method binding differs: ' + className + '.' + name);
    if (source.bodyHex && hex(result.virtualAddress.readByteArray(source.bodyHex.length / 2)) !== source.bodyHex)
      throw Error('Original153 process factory full body differs');
    return result;
  };
  const read32 = (self, name) => call(self.method('get_' + name, 0), self).unbox().handle.readS32();
  return {binding, game, method, call, read32};
}

function validateNative153EncounterInput(input) {
  'use strict';
  const spec = native153EncounterSpec(input), binding = globalThis.NATIVE153_ENCOUNTER_BINDING;
  const hash = value => typeof value === 'string' && /^[a-f0-9]{64}$/.test(value);
  const positive = value => Number.isSafeInteger(value) && value > 0 && value <= 2147483647;
  if (!input || input.schemaVersion !== 1 || input.clientSha256 !== NATIVE153_ENCOUNTER_CLIENT ||
      !binding || binding.clientSha256 !== NATIVE153_ENCOUNTER_CLIENT || !spec ||
      typeof spec.id !== 'string' || !spec.id || !positive(spec.waveId) ||
      !Number.isFinite(spec.timeLimit) || spec.timeLimit <= 0 || spec.timeLimit > 3600 ||
      !Number.isSafeInteger(spec.processType) || !binding.dispatch[spec.processType] ||
      spec.processClass !== binding.dispatch[spec.processType].processClass ||
      !spec.transporter || !hash(input.inputSourceSha256) || !positive(input.randomSeed) ||
      !Array.isArray(input.characters) || input.characters.length !== 5 || input.characters.some(row =>
        !row || !positive(row.tableId) || !positive(row.nameCode)))
    throw Error('Complete source-bound original153 encounter/team input required');
  if (input.waveId !== undefined && input.waveId !== spec.waveId ||
      input.timeLimit !== undefined && input.timeLimit !== spec.timeLimit ||
      input.processType !== undefined && input.processType !== spec.processType)
    throw Error('Encounter summary differs from the authoritative source selection');
  if (spec.transporter._waveId !== spec.waveId || spec.transporter['<TimeLimit>k__BackingField'] !== spec.timeLimit)
    throw Error('Native transporter encounter identity/duration differs from selected source');
  return input;
}

function verifyNative153EncounterTransporter(input, readback) {
  'use strict';
  validateNative153EncounterInput(input);
  const spec = native153EncounterSpec(input), fields = spec.transporter;
  if (!readback || readback.transporterValueTypeSize !== 376)
    throw Error('Complete original153 transporter native readback required');
  const names = {
    '<ManagementType>k__BackingField': 'managementType', '<ProcessType>k__BackingField': 'processType',
    '<TimeLimit>k__BackingField': 'timeLimit', TeamType: 'teamType', TeamNumber: 'teamNumber',
    _waveId: 'waveId', '<MonsterStageLv>k__BackingField': 'monsterStageLv',
    '<DynamicObjectLv>k__BackingField': 'dynamicObjectLv', '<RaidLvChangeGroup>k__BackingField': 'raidLvChangeGroup',
    '<ThemeType>k__BackingField': 'themeType', '<StageTableType>k__BackingField': 'stageTableType',
    '<IsAuto>k__BackingField': 'isAuto', '<IsMockBattle>k__BackingField': 'isMockBattle',
    '<TDDProcess>k__BackingField': 'tddProcess'
  };
  for (const required of ['<ManagementType>k__BackingField', '<ProcessType>k__BackingField', '<TimeLimit>k__BackingField',
    'TeamType', 'TeamNumber', '_waveId', '<MonsterStageLv>k__BackingField', '<DynamicObjectLv>k__BackingField'])
    if (!Object.prototype.hasOwnProperty.call(fields, required)) throw Error('Encounter source omits native field ' + required);
  for (const [field, name] of Object.entries(names))
    if (Object.prototype.hasOwnProperty.call(fields, field) && readback[name] !== fields[field])
      throw Error('Original encounter transporter readback differs: ' + field);
  if (readback.randomSeed !== input.randomSeed || readback.managementType !== 0)
    throw Error('Original standalone encounter seed/management type differs');
  return true;
}

function verifyNative153EncounterWave(staticImage, pin, emit, input, wave) {
  'use strict';
  validateNative153EncounterInput(input);
  if (!wave || wave.isNull() || wave.class.type.name !== 'StaticData.StaticDataLayer.StaticInfo.WaveDataStaticInfo')
    throw Error('The original asynchronously resolved encounter wave is required');
  pin(wave);
  const spec = native153EncounterSpec(input), call = (name) => invokeChecked(wave.method('get_' + name, 0), wave);
  const integer = name => call(name).unbox().handle.readS32();
  const stringLen = new NativeFunction(Process.getModuleByName('GameAssembly.dll').getExportByName('il2cpp_string_length'), 'int', ['pointer']);
  const stringChars = new NativeFunction(Process.getModuleByName('GameAssembly.dll').getExportByName('il2cpp_string_chars'), 'pointer', ['pointer']);
  const background = call('BackgroundName');
  if (!background || background.isNull()) throw Error('Original encounter background key is null');
  const actual = {waveId: integer('TableId'), stageId: integer('StageID'), waveSpotMod: integer('SpotMod'),
    waveBattleTime: integer('BattleTime'), themeType: integer('ThemeType'),
    backgroundName: stringChars(background.handle).readUtf16String(stringLen(background.handle))};
  if (actual.waveId !== spec.waveId || !actual.backgroundName)
    throw Error('Original selected wave identity/background is missing');
  for (const field of ['waveSpotMod', 'waveBattleTime', 'themeType', 'backgroundName'])
    if (spec[field] !== undefined && actual[field] !== spec[field]) throw Error('Original source wave field differs: ' + field);
  emit({status: 'original153_encounter_wave_verified', encounterId: spec.id, ...actual,
    sourceLookupOriginal: true, monsterStatsWritten: false, battleStarted: false});
  return actual;
}

function createOriginal153EncounterProcess(runtime, staticImage, management, pin, emit, input, transporterReadback) {
  'use strict';
  verifyNative153EncounterTransporter(input, transporterReadback);
  const spec = native153EncounterSpec(input), api = native153EncounterApi(runtime, staticImage);
  const loaderClass = runtime.class('NK.Spot.Context.SpotLoader'), loader = loaderClass.alloc(); pin(loader);
  api.call(api.method(loaderClass.type.name, '.ctor', []), loader);
  const type = Memory.alloc(4); type.writeS32(spec.processType);
  const process = api.call(api.method(loaderClass.type.name, 'GetProcess', ['NK.StaticData.SpotModType&']), loader, [type]);
  if (!process || process.isNull() || type.readS32() !== spec.processType || process.class.type.name !== spec.processClass ||
      api.read32(process, 'ProcessType') !== spec.processType)
    throw Error('Original process factory returned a different encounter process/type');
  pin(process);
  api.call(api.method('NK.Spot.SpotManagement', 'SetProcess', ['NK.Spot.Context.Process.ProcessBase']), management, [process.handle]);
  const retained = management.field('_process').value;
  if (!retained || retained.isNull() || !retained.handle.equals(process.handle))
    throw Error('Original manager did not retain the original encounter process');
  const dispatch = api.binding.dispatch[spec.processType];
  const conditions = name => {
    const list = process.field(name).value;
    if (!list || list.isNull()) throw Error('Original encounter condition list is absent');
    const count = api.read32(list, 'Count');
    if (count < 0 || count > 16) throw Error('Original encounter condition count bound');
    return Array.from({length: count}, (_, index) => {
      const argument = Memory.alloc(4); argument.writeS32(index);
      return api.call(list.method('get_Item', 1), list, [argument]).unbox().handle.readS32();
    });
  };
  const clearConditions = conditions('ClearConditionList'), failConditions = conditions('FailConditionList');
  // The returned original process determines the override. No lists are copied
  // from another mode and no completion state is forced by the host.
  api.call(api.method(dispatch.contextOwner, 'CreateContext', []), process);
  emit({status: 'original153_encounter_context_created', encounterId: spec.id, waveId: spec.waveId,
    processClass: process.class.type.name, processType: spec.processType, contextOwner: dispatch.contextOwner,
    originalFactoryInvoked: true, originalContextInvoked: true, conditionsWritten: false,
    clearConditions, failConditions, inputSourceSha256: input.inputSourceSha256, fullAccuracyVerified: false});
  return process;
}

function readOriginal153EncounterLifecycle(runtime, process) {
  'use strict';
  const cls = runtime.class('NK.Spot.Context.Process.ProcessBase');
  const value = name => invokeChecked(cls.method('get_' + name, 0), process).unbox().handle;
  const state = value('State').readS32(), states = {2: 'LoadingStart', 3: 'LoadingComplete', 6: 'Playing', 8: 'Clear', 9: 'Fail', 10: 'Finish'};
  return {processClass: process.class.type.name, processType: value('ProcessType').readS32(),
    state, stateName: states[state] || 'other_native_state', playTime: value('PlayTime').readFloat(),
    battleTime: value('BattleTime').readFloat(), battleTickCount: Number(process.field('_battleTickCount').value)};
}

function installOriginal153EncounterResultCapture(runtime, team, pin, emit, input, callbacks) {
  'use strict';
  validateNative153EncounterInput(input);
  if (!callbacks || typeof callbacks.setOriginalFinishObserver !== 'function' ||
      typeof installOriginal153PracticeBattleResultCapture !== 'function')
    throw Error('Original synchronous result/statistics capture boundary required');
  const api = native153EncounterApi(runtime, null), resultClass = runtime.class('NK.BattleResult');
  const finish = api.method('NK.Spot.SpotManagement', 'SpotFinish', ['NK.Spot.Interface.ISpotBattleResult']);
  const packetInit = api.method('NK.BattleResult', 'AntiCheatBattleDataInit', []);
  // This retained reader obtains the original NK.BattleResult, statistics,
  // survival and get_AllRedTeamTotalDamage. It has no Practice Score getter.
  const capture = installOriginal153PracticeBattleResultCapture(runtime, team, pin, emit);
  let original = null, packet = null, packetReadback = null, returned = false, captured = false, fault = null, originalUiScore = null;
  const listener = Interceptor.attach(finish.virtualAddress, {
    onEnter(args) {
      try {
        if (original || args[1].isNull()) throw Error('Missing or duplicate original encounter finish');
        original = new Il2Cpp.Object(args[1]);
        if (!original.class.handle.equals(resultClass.handle)) throw Error('Encounter finish has a different result type');
        pin(original);
      } catch (error) { fault = error; }
    },
    onLeave() { returned = true; }
  });
  callbacks.setOriginalFinishObserver(value => {
    try {
      if (fault) throw fault;
      if (!original || returned || captured || !value || value.isNull() || !value.handle.equals(original.handle))
        throw Error('Encounter capture must occur inside the same original finish before cleanup');
      if (native153EncounterSpec(input).contentMode === 'anomaly') {
        if (!callbacks.originalUiScoreReader) throw Error('Original Anomaly UI score observer missing');
        originalUiScore = callbacks.originalUiScoreReader.readBeforeCleanup();
      }
      capture.captureBeforeCleanup(value);
      packet = api.call(packetInit, original);
      if (!packet || packet.isNull() || packet.class.type.name !== 'NK.Network.Packet.Lobby.NetAntiCheatBattleData')
        throw Error('Original encounter anti-cheat packet is missing');
      pin(packet);
      const count = name => api.read32(api.call(packet.method('get_' + name, 0), packet), 'Count');
      packetReadback = {source: 'original_BattleResult_AntiCheatBattleDataInit', waveId: api.read32(packet, 'WaveId'),
        battleDuration: api.read32(packet, 'BattleDuration'), characterCount: count('Characters'), monsterCount: count('Monsters')};
      captured = true;
      emit({status: 'original153_encounter_packet_captured_before_cleanup', encounterId: native153EncounterSpec(input).id,
        originalAntiCheat: packetReadback, originalPacketRetained: true});
    } catch (error) { fault = error; throw error; }
  });
  return {
    captureTerminal(state) {
      if (fault) throw fault;
      const result = capture(state);
      if (result.pending === true || !returned || !original) return {pending: true, resultCaptured: false};
      if (!captured || !packetReadback || !packet) throw Error('Original encounter packet was not captured before cleanup');
      return {...result, originalAntiCheat: packetReadback, inputSourceSha256: input.inputSourceSha256,
        ...(originalUiScore ? {originalUiScore} : {}),
        encounterId: native153EncounterSpec(input).id, statisticsAndPacketCapturedBeforeCleanup: true,
        damageGetter: 'original_SpotStatisticsData.get_AllRedTeamTotalDamage',
        submittedModeScoreVerified: false, scoreCalculated: false, terminalCause: 'unverified', fullAccuracyVerified: false};
    },
    getOriginalPacket() { return packet; }, retainUntilExit: listener
  };
}

function verifyOriginal153EncounterCompletion(input, result, evidence) {
  'use strict';
  const errors = [], spec = native153EncounterSpec(input), e = evidence || {}, r = result || {}, packet = r.originalAntiCheat || {};
  try { validateNative153EncounterInput(input); } catch (error) { errors.push(String(error)); }
  if (!spec) return {passed: false, errors, completeNativeEncounter: false};
  if (e.processClass !== spec.processClass || e.processType !== spec.processType ||
      e.waveId !== spec.waveId || e.timeLimit !== spec.timeLimit || e.randomSeed !== input.randomSeed ||
      e.inputReadbackPassed !== true || e.inputSourceSha256 !== input.inputSourceSha256)
    errors.push('Original encounter process/input readbacks differ from selected source');
  if (e.observedPlaying !== true || !Number.isInteger(e.advancedTicks) || e.advancedTicks <= 0 ||
      ![8, 9, 10].includes(e.processState) || r.processState !== e.processState)
    errors.push('Original encounter did not complete its playing/terminal lifecycle');
  if (r.resultCaptured !== true || r.originalResult !== true || r.resultType !== 'NK.BattleResult' ||
      ![1, 2].includes(r.result) || !Number.isInteger(r.spotResult) || r.retreat !== false)
    errors.push('Original non-abort encounter BattleResult is missing');
  if (packet.source !== 'original_BattleResult_AntiCheatBattleDataInit' || packet.waveId !== spec.waveId ||
      !Number.isInteger(packet.battleDuration) || packet.battleDuration <= 0 ||
      packet.battleDuration > Math.ceil(spec.timeLimit * 1000) + 1000 || packet.characterCount !== 5 ||
      !Number.isInteger(packet.monsterCount) || packet.monsterCount <= 0)
    errors.push('Original encounter packet has invalid identity, duration, players or monsters');
  const rounds = r.rounds;
  if (!Array.isArray(rounds) || rounds.length !== 1 || !Number.isFinite(rounds[0]?.duration) || rounds[0].duration <= 0 ||
      rounds[0].duration > spec.timeLimit + 1 || !/^(0|[1-9][0-9]*)$/.test(rounds[0]?.squadTotal || ''))
    errors.push('Original single-team encounter damage statistics are missing or invalid');
  const actors = e.originalActors, members = rounds?.[0]?.characters;
  const valid = rows => Array.isArray(rows) && rows.length === 5 && rows.every(row => row &&
    Number.isSafeInteger(row.entityId) && row.entityId > 0 && Number.isSafeInteger(row.tableId) && row.tableId > 0 &&
    Number.isSafeInteger(row.nameCode) && row.nameCode > 0) && new Set(rows.map(row => row.entityId)).size === 5;
  if (!valid(actors) || !valid(members)) errors.push('Original selected actor/statistics identities are incomplete');
  else actors.forEach((actor, index) => {
    const expected = input.characters[index], member = members.find(value => value.entityId === actor.entityId);
    if (!expected || !member || actor.tableId !== expected.tableId || actor.nameCode !== expected.nameCode ||
        member.tableId !== actor.tableId || member.nameCode !== actor.nameCode)
      errors.push('Original selected actor/statistics identity differs at slot ' + (index + 1));
  });
  return {passed: errors.length === 0, errors, completeNativeEncounter: errors.length === 0,
    encounterId: spec.id, waveId: spec.waveId, inputSourceSha256: input.inputSourceSha256,
    processState: e.processState, originalResult: r.result, originalSpotResult: r.spotResult,
    damageGetter: 'original_SpotStatisticsData.get_AllRedTeamTotalDamage', scoreCalculated: false,
    submittedModeScoreVerified: false, terminalCause: 'unverified', fullAccuracyVerified: false};
}
