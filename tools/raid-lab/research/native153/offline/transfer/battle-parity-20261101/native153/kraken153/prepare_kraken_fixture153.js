'use strict';
// A strict, separate mode gate around the existing unchanged native snapshot /
// team/transporter constructor. It accepts actual Kraken capture, never edits a
// practice packet to look like Kraken and never injects expected combat outputs.
function prepareCapturedKrakenFixture153(runtime,staticImage,pin,emit,input,expected,bindings) {
  const provenance=input?.krakenCapture,fixture=input?.fixtureInput,source=input?.snapshotInput;
  const hash=value=>typeof value==='string'&&/^[a-f0-9]{64}$/.test(value);
  if(!provenance||provenance.kind!=='actual_offline_kraken_prebattle'||provenance.clientSha256!==KRAKEN153_CLIENT||
      !hash(provenance.receiptSha256)||!hash(provenance.fixtureInputSha256)||!hash(provenance.snapshotInputSha256)||
      !fixture||!source||fixture.clientSha256!==KRAKEN153_CLIENT||source.clientSha256!==KRAKEN153_CLIENT||fixture.transporterValueSize!==376||
      fixture.captureSha256!==provenance.captureSha256||source.captureSha256!==provenance.captureSha256||
      expected?.captureSha256!==provenance.captureSha256||fixture.runIndex!==source.runIndex||
      source.runIndex!==expected.runIndex||expected.battleOutputsIncluded!==false||fixture.wave?.tableId!==6302009||
      fixture.wave.requiredNativeType!=='StaticData.StaticDataLayer.StaticInfo.WaveDataStaticInfo')
    throw Error('Actual original Kraken capture provenance/fixture required; practice-derived input unsupported');
  const fields=new Map();
  if(!Array.isArray(fixture.fields)||fixture.fields.length!==61)throw Error('Complete current61-field Kraken capture required');
  for(const field of fixture.fields) {
    if(fields.has(field.name))throw Error('Duplicate captured Kraken field: '+field.name);
    fields.set(field.name,field);
  }
  const value=name=>{
    const spec=fields.get(name);
    if(!spec||!['int32','enum32','float32','bool'].includes(spec.kind))throw Error('Captured Kraken semantic field absent: '+name);
    return spec.value;
  };
  const capturedTransporter={managementType:value('<ManagementType>k__BackingField'),
    processType:value('<ProcessType>k__BackingField'),teamType:value('TeamType'),teamNumber:value('TeamNumber'),
    timeLimit:value('<TimeLimit>k__BackingField'),waveId:value('_waveId'),
    monsterStageLv:value('<MonsterStageLv>k__BackingField'),dynamicObjectLv:value('<DynamicObjectLv>k__BackingField'),
    raidLvChangeGroup:value('<RaidLvChangeGroup>k__BackingField'),randomSeed:value('<RandomSeed>k__BackingField'),
    isAuto:value('<IsAuto>k__BackingField'),isMockBattle:value('<IsMockBattle>k__BackingField'),
    tddProcess:value('<TDDProcess>k__BackingField')};
  if(!Array.isArray(source.characters)||source.characters.length!==5||!Array.isArray(expected.characters)||expected.characters.length!==5)
    throw Error('Five actual Kraken source snapshots and separate native expectations required');
  const characters=source.characters.map(row=>({slot:row.slot,tableId:row.characterTableId,nameCode:row.sourceNameCode}));
  if(!Array.isArray(provenance.orderedCharacters)||provenance.orderedCharacters.length!==5||characters.some((row,index)=>
      row.slot!==provenance.orderedCharacters[index]?.slot||row.tableId!==provenance.orderedCharacters[index]?.tableId||
      row.nameCode!==provenance.orderedCharacters[index]?.nameCode))
    throw Error('Actual Kraken ordered actor provenance differs');
  const modeInput={schemaVersion:1,sourceKind:provenance.kind,clientSha256:KRAKEN153_CLIENT,
    processMetadataSha256:KRAKEN153_PROCESS_METADATA,encounterSourceSha256:KRAKEN153_ENCOUNTER_SOURCE,
    captureSha256:provenance.captureSha256,fixtureInputSha256:provenance.fixtureInputSha256,
    snapshotInputSha256:provenance.snapshotInputSha256,captureProvenanceSha256:provenance.receiptSha256,
    processType:7,waveId:6302009,timeLimit:180,capturedTransporter,
    characters};
  validateCapturedKrakenMode153(modeInput);
  if(typeof prepareCapturedPracticeFixture!=='function')throw Error('Unchanged original captured-object constructor is required');
  // This reusable constructor has no fixed wave/time semantics. The strict
  // ShootingRange mode validator remains untouched and is not invoked here.
  const result=prepareCapturedPracticeFixture(runtime,staticImage,pin,emit,input,expected,bindings);
  if(!result||result.passed!==true)throw Error('Original Kraken snapshot/team/transporter readback did not pass');
  const call=(method,self)=>invokeChecked(method,self);
  const valueType=result.transporterBox.unbox();
  const raidGetter=valueType.method('get_RaidLvChangeGroup',0);
  if(raidGetter.isStatic||raidGetter.returnType.name!=='System.Int32'||raidGetter.parameters.length!==0||
      Number(raidGetter.relativeVirtualAddress)!==62799008)
    throw Error('Original captured raid-group getter ABI differs');
  const raid=call(raidGetter,valueType).unbox().handle.readS32();
  const prepared={...result,sourceKind:provenance.kind,captureSha256:provenance.captureSha256,
    fixtureInputSha256:provenance.fixtureInputSha256,modeInput,
    readback:{...result.readback,raidLvChangeGroup:raid},
    // Host UI/output delegates are a disclosed boundary, never exact scene replay.
    transporterExactReplay:false,actualOfflineKrakenCaptured:true};
  verifyCapturedKrakenTransporter153(modeInput,prepared);
  emit({status:'actual_captured_kraken_fixture_prepared',passed:true,
    captureSha256:modeInput.captureSha256,fixtureInputSha256:modeInput.fixtureInputSha256,
    modeInput,staticTransporterInstalled:false,battleStarted:false,
    sourceSnapshotsAndNativeConversionReusedWithoutOverrides:true,
    tableConfiguredCoverStageLv:8,tableConfiguredLimitCharacterLv:400,
    actualCoverOrLevelModeCaptured:false,fullAccuracyVerified:false});
  return prepared;
}
