// Original campaign input preparation only. No combat/CP/penalty arithmetic,
// account lookup, progression submission, battle tick or result mutation.
function prepareNative153CampaignTeam(runtime,staticImage,pin,emit,modeInput,replay) {
  const binding=globalThis.NATIVE153_CAMPAIGN_BINDING;
  const encounter=modeInput?.encounter;
  if(!binding||binding.clientSha256!=='d39896d3770888039c728a1908448c3db5efa7cdf874c90d56f46d8d566428d2'||
      !encounter||encounter.contentMode!=='campaign'||encounter.source?.table!=='CampaignStage'||
      !Number.isSafeInteger(encounter.source.recordId)||!replay?.passed||replay.snapshots?.length!==5)
    throw Error('Original source-bound campaign stage and five native snapshots required');
  const game=Process.getModuleByName('GameAssembly.dll'),roots=[],rawBuffers=[];
  const retain=value=>{if(value==null||value.isNull())throw Error('Original campaign input object missing');pin(value);roots.push(value);return value;};
  const call=(method,self=null,args=[])=>invokeChecked(method,self,args);
  const i32=value=>{if(!Number.isSafeInteger(value)||value<-2147483648||value>2147483647)throw Error('Campaign Int32 input required');const p=Memory.alloc(4);p.writeS32(value);rawBuffers.push(p);return p;};
  const boolean=value=>{const p=Memory.alloc(1);p.writeU8(value?1:0);rawBuffers.push(p);return p;};
  const hex=data=>Array.from(new Uint8Array(data),value=>value.toString(16).padStart(2,'0')).join('');
  function klass(name) {
    const source=binding.methods.find(row=>row.className===name);
    if(!source)throw Error('Campaign original class binding missing '+name);
    const cls=(source.assembly==='NK.Runtime.dll'?runtime:staticImage).class(name),layout=binding.layouts[name];
    if(!layout||cls.isValueType!==layout.isValueType||layout.isValueType&&cls.valueTypeSize!==layout.valueSize)
      throw Error('Campaign original value layout differs '+name);
    return cls;
  }
  function method(name,member,types=[]) {
    const rows=binding.methods.filter(row=>row.className===name&&row.name===member&&
      row.parameters.map(p=>p.type).join('|')===types.join('|'));
    if(rows.length!==1)throw Error('One original campaign method required '+name+'.'+member);
    const source=rows[0],result=klass(name).method(member).overload(...types);
    if(!result.virtualAddress.equals(game.base.add(source.nativeRva))||result.returnType.name!==source.returns||
        result.isStatic!==Boolean(source.flags&16)||hex(result.virtualAddress.readByteArray(16))!==source.entryHex)
      throw Error('Campaign original method signature/bytes differ '+name+'.'+member);
    return result;
  }
  const integer=(object,name)=>retain(call(object.method('get_'+name,0),object)).unbox().handle.readS32();
  const staticName='NK.StaticData.StaticDataLayer.StaticInfo.CampaignStageStaticInfo';
  const manager=retain(call(method('NK.StaticData.DataManager','get_Instance')));
  const table=retain(call(method('NK.StaticData.DataManager','get_CampaignStageTable'),manager));
  const stage=retain(call(method('NK.StaticData.DataTables.CampaignStageTable','FindById',['System.Int32']),table,[i32(encounter.source.recordId)]));
  const get=name=>retain(call(method(staticName,'get_'+name),stage)).unbox().handle.readS32();
  const stageId=get('TableId'),waveId=get('SpotID'),fixedParty=get('FixedPlayCharacterID');
  const stageLevel=get('CharacterLevel'),groupID=get('StatIncreaseGroupID'),standardBattlePower=get('StandardBattlePower');
  if(stageId!==encounter.source.recordId||waveId!==encounter.waveId||fixedParty!==0||
      groupID!==encounter.context.StageStatIncreaseGroupId||standardBattlePower!==encounter.context.StandardBattlePower||
      stageLevel!==encounter.context.CharacterLv||get('MonsterStageLv')!==encounter.monsterStageLv||
      get('DynamicObjectStageLv')!==encounter.dynamicObjectLv)
    throw Error('Original campaign stage identity/levels/CP rule differs from selected source record');
  // EnterSpotUnit.Initialize (070783B0) obtains CP before its later stage-level
  // correction path in CreateSpotDataTransfer (07077687..070776D1). Preserve
  // original own levels for that CP selection, then use the battle snapshots
  // already constructed at the original campaign correction level.
  const selectedInput=globalThis.NATIVE_BATTLE_INPUT;
  if(!selectedInput||selectedInput.characters?.length!==5)throw Error('Original current-job native build input missing');
  if(selectedInput.characters.some(member=>member.level!==(stageLevel>0?stageLevel:member.ownLevel)))
    throw Error('Campaign battle snapshots do not retain the original own/fixed stage-level policy');
  let powerReplay=replay;
  const powerCharacters=selectedInput.characters.map(member=>{
    if(!Number.isSafeInteger(member.ownLevel)||member.ownLevel<1||member.ownLevel>1000)
      throw Error('Campaign requires the original own level before native stage correction');
    return {...member,level:member.ownLevel};
  });
  if(powerCharacters.some((member,index)=>member.level!==selectedInput.characters[index].level)) {
    powerReplay=buildNativeTeam153(runtime,staticImage,pin,row=>emit({...row,
      status:row.status+'_campaign_power_source'}),{...selectedInput,characters:powerCharacters});
    roots.push(...powerReplay.roots);rawBuffers.push(...powerReplay.rawBuffers);
  }
  const infoName='NK.Common.System.UserData.NKCharacterInfo';
  const dtoName='NK.Common.Model.DTO.CharacterDTO',squadName='NK.Common.Model.DTO.Squad';
  const empty=retain(call(method(infoName,'CreateEmpty')));
  const dtos=[];
  const powers=[];
  for(let index=0;index<5;index++) {
    const native=powerReplay.converted[index],member=powerCharacters[index];
    const info=retain(native.field('<CharacterStaticInfo>k__BackingField').value);
    const power=integer(native,'BattlePower');
    if(integer(info,'TableId')!==member.characterTableId||integer(native,'Level')!==member.ownLevel)
      throw Error('Original campaign power-source character identity/level differs');
    const dto=retain(klass(dtoName).alloc());
    // This aggregate-only DTO takes the constructor's original empty-identity
    // preview branch: CostumeTableIdToCostumeIndex(073A2740), rather than an
    // account lookup by the custom serial. Battle snapshots keep their real
    // per-job CSNs; this DTO is used only by original Squad.get_CombatPower.
    call(method(dtoName,'.ctor',['NK.StaticData.StaticDataLayer.StaticInfo.CharacterStaticInfo',infoName,
      'System.Int32','System.Int32','System.Boolean','System.Boolean','NK.StaticData.Categoricals.CostumeTableId']),dto.unbox(),
      [info.handle,empty.unbox().handle,i32(member.ownLevel),i32(power),boolean(false),boolean(false),i32(member.costumeTableId)]);
    const value=dto.unbox();
    if(value.field('BattlePower').value!==power||value.field('Level').value!==member.ownLevel)
      throw Error('Original aggregate CharacterDTO CP/level readback differs');
    dtos.push(dto);powers.push({slot:index+1,tableId:member.characterTableId,level:member.ownLevel,battlePower:power});
  }
  const set=Il2Cpp.corlib.class('System.Array').method('SetValue').overload('System.Object','System.Int32');
  const array=Il2Cpp.array(klass(dtoName),5);retain(array.object);
  dtos.forEach((dto,index)=>call(set,array.object,[dto.handle,i32(index)]));
  const squad=retain(klass(squadName).alloc());
  call(method(squadName,'.ctor',['System.Int32','NK.Common.Model.DTO.CharacterDTO[]']),squad.unbox(),[i32(0),array.handle]);
  const battlePower=retain(call(method(squadName,'get_CombatPower'),squad.unbox())).unbox().handle.readS32();
  const increaseName='NK.StaticData.StaticDataLayer.StaticInfo.StageStatIncreaseStaticInfo';
  const selected=call(method(increaseName,'GetStageStatIncreaseInfo',['System.Int32','System.Int32','System.Int32']),null,
    [i32(groupID),i32(battlePower),i32(standardBattlePower)]);
  let statIncreaseValue=0;
  if(selected!=null&&!selected.isNull()) {
    retain(selected);
    statIncreaseValue=retain(call(method(increaseName,'get_StatIncrease'),selected)).unbox().handle.readS32();
  }
  const snapshots=Il2Cpp.array(runtime.class('NK.Common.System.UserData.CharacterSnapshot'),5);retain(snapshots.object);
  replay.snapshots.forEach((snapshot,index)=>call(set,snapshots.object,[snapshot.handle,i32(index)]));
  const team=retain(call(method('NK.Common.System.UserData.CharacterSnapshotExtension','CreateSpotTeamData',[
    'System.Collections.Generic.IReadOnlyList<NK.Common.System.UserData.CharacterSnapshot>',
    'System.Collections.Generic.List<NK.StaticData.StaticDataLayer.StaticInfo.BuffStaticInfo[]>','System.Int32']),null,
    [snapshots.handle,ptr(0),i32(statIncreaseValue)]));
  const increases=retain(call(method('NK.Spot.Common.SpotTeamData','get_StatIncreaseValue'),team));
  if(integer(increases,'Count')!==1||retain(call(increases.method('get_Item',1),increases,[i32(0)])).unbox().handle.readS32()!==statIncreaseValue)
    throw Error('Original campaign team penalty readback differs');
  const readback={status:'original153_campaign_team_prepared',passed:true,requestSha256:globalThis.NATIVE_BATTLE_REQUEST_SHA256,
    stageId,waveId,stageLevel,groupID,standardBattlePower,battlePower,statIncreaseValue,powerCharacters:powers,
    originalSquadCombatPowerGetterInvoked:true,originalStageStatIncreaseSelectorInvoked:true,
    statIncreaseAppliedByOriginalCreateSpotTeamData:true,accountCostumeLookupPerformed:false,
    aggregateOnlyDtoIdentity:'Original NKCharacterInfo.CreateEmpty preview branch; combat snapshots unchanged',
    pythonCombatPowerFormulaUsed:false,javascriptCombatPowerFormulaUsed:false,battleStarted:false};
  emit(readback);
  return {team,expected:replay.expected,statIncreaseValue,spotContextData:null,roots,rawBuffers,readback};
}
