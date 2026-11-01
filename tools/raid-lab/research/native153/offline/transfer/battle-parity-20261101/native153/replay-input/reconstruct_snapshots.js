// Private current153 disposable player only. This prepares/readbacks original
// snapshots; it neither starts a battle nor installs a transporter or scheduler.
function runCapturedSnapshotReconstruction(runtime, staticImage, pin, emit, input, expected) {
  'use strict';
  const client='d39896d3770888039c728a1908448c3db5efa7cdf874c90d56f46d8d566428d2';
  if(!runtime||!staticImage||typeof pin!=='function'||typeof emit!=='function'||
      typeof invokeChecked!=='function'||!input||input.clientSha256!==client||
      !expected||input.captureSha256!==expected.captureSha256||
      input.characters.length!==5||expected.characters.length!==5)
    throw Error('Exact captured current153 inputs and separate native verification required');
  const game=Process.getModuleByName('GameAssembly.dll'), roots=[], rawBuffers=[];
  const retain=obj=>{if(obj==null||obj.isNull())throw Error('Missing required native object');pin(obj);roots.push(obj);return obj;};
  const call=(method,self=null,args=[])=>invokeChecked(method,self,args);
  const at=(method,rva,label)=>{if(!method.virtualAddress.equals(game.base.add(rva)))throw Error('Current153 binding mismatch '+label);return method;};
  const a32=value=>{if(!Number.isSafeInteger(value)||value<-2147483648||value>2147483647)throw Error('Invalid captured Int32');const p=Memory.alloc(4);p.writeS32(value);rawBuffers.push(p);return p;};
  const a64=value=>{if(typeof value!=='string'||!/^\d+$/.test(value))throw Error('Invalid captured Int64 string');const p=Memory.alloc(8);p.writeS64(int64(value));rawBuffers.push(p);return p;};
  const i32=(method,self)=>retain(call(method,self)).unbox().handle.readS32();
  const i64=(method,self)=>retain(call(method,self)).unbox().handle.readS64().toString();
  const bool=(method,self)=>retain(call(method,self)).unbox().handle.readU8()!==0;
  const bytes=hex=>{if(typeof hex!=='string'||hex.length%2||!/^[0-9a-f]*$/.test(hex))throw Error('Invalid original typed raw hex');return hex.match(/../g)?.map(x=>parseInt(x,16))||[];};
  const hex=p=>Array.from(new Uint8Array(p),x=>x.toString(16).padStart(2,'0')).join('');
  function typedRaw(cls,sourceHex,size,label) {
    if(!cls.isValueType||cls.valueTypeSize!==size||sourceHex.length!==size*2)throw Error('Original value layout mismatch '+label);
    const box=retain(cls.alloc()),value=box.unbox();
    value.handle.writeByteArray(bytes(sourceHex));
    if(hex(value.handle.readByteArray(size))!==sourceHex)throw Error('Raw typed source copy differs '+label);
    return value;
  }
  const setArray=Il2Cpp.corlib.class('System.Array').method('SetValue').overload('System.Object','System.Int32');
  function intArray(values) {
    if(!Array.isArray(values)||values.length>256)throw Error('Captured effect list bound');
    const cls=Il2Cpp.corlib.class('System.Int32'),array=Il2Cpp.array(cls,values.length);retain(array.object);
    const boxValue=new NativeFunction(game.getExportByName('il2cpp_value_box'),'pointer',['pointer','pointer']);
    values.forEach((value,index)=>{const boxed=retain(new Il2Cpp.Object(boxValue(cls.handle,a32(value))));call(setArray,array.object,[boxed.handle,a32(index)]);});
    return array;
  }
  function listCount(value) {
    if(value==null||value.isNull())return null;
    return value.class.type.name.endsWith('[]')?i32(Il2Cpp.corlib.class('System.Array').method('get_Length',0),value):i32(value.method('get_Count',0),value);
  }
  function listItems(value) {
    const count=listCount(value);if(count===null)return null;if(count<0||count>256)throw Error('Original list readback bound');
    const isArray=value.class.type.name.endsWith('[]');
    const getter=isArray?Il2Cpp.corlib.class('System.Array').method('GetValue').overload('System.Int32'):value.method('get_Item',1);
    return Array.from({length:count},(_,index)=>retain(call(getter,value,[a32(index)])));
  }
  const dataManagerClass=staticImage.class('NK.StaticData.DataManager');
  const manager=retain(call(at(dataManagerClass.method('get_Instance',0),0x04ebd140,'DataManager.Instance')));
  const characterTable=retain(call(at(manager.method('get_CharacterTable',0),0x04eb8510,'DataManager.CharacterTable'),manager));
  const findCharacter=at(characterTable.method('FindById',1),0x04f3fde0,'CharacterTable.FindById');
  const skillTable=retain(call(at(manager.method('get_SkillInfoTable',0),0x04ebe340,'DataManager.SkillInfoTable'),manager));
  const findSkill=at(skillTable.method('FindById',1),0x0515f950,'SkillInfoTable.FindById');
  if(findCharacter.parameters[0].type.class.valueTypeSize!==4||findSkill.parameters[0].type.name!=='System.Int32')
    throw Error('Exact current table lookup argument ABI differs');
  function rowById(table,method,id) {
    const row=retain(call(method,table,[a32(id)]));
    if(i32(row.method('get_TableId',0),row)!==id)throw Error('Original static table identity mismatch '+id);
    return row;
  }
  const snapshotClass=runtime.class('NK.Common.System.UserData.CharacterSnapshot');
  const ctor=at(snapshotClass.method('.ctor',16),0x06dae9f0,'CharacterSnapshot.ctor16');
  const converter=at(runtime.class('NK.Common.System.UserData.CharacterSnapshotExtension').method('CreateSpotCharacterData',1),0x06dac570,'CreateSpotCharacterData');
  const statClass=runtime.class('NK.Common.System.Stat.CharacterStatData');
  const infoClass=runtime.class('NK.Common.System.UserData.NKCharacterInfo');
  const obscured=Il2Cpp.domain.assembly('ACTk.Runtime').image.class('CodeStage.AntiCheat.ObscuredTypes.ObscuredInt');
  const originalLevelDecode=at(obscured.method('op_Implicit').overload('CodeStage.AntiCheat.ObscuredTypes.ObscuredInt'),0x008c7ed0,'original ObscuredInt to Int32');
  const equipClass=runtime.class('NK.Common.System.UserData.EquipsAndCube'),builderClass=equipClass.nested('Builder');
  const builderCtor=at(builderClass.method('.ctor',0),0x06dc5230,'EquipsAndCube.Builder.ctor');
  const builderSet=at(builderClass.method('Set').overload('NK.StaticData.ItemSubType','NK.StaticData.Categoricals.ItemSerialNumber','NK.StaticData.Categoricals.ItemTableId','System.Int32'),0x06dc5160,'EquipsAndCube.Builder.Set');
  const builderBuild=at(builderClass.method('Build',0),0x06dc5080,'EquipsAndCube.Builder.Build');
  const effectsClass=snapshotClass.nested('ItemStateEffects');
  const effectsCtor=at(effectsClass.method('.ctor',1),0x008ec040,'ItemStateEffects.ctor');
  const parameterTypes=['NK.StaticData.StaticDataLayer.StaticInfo.CharacterStaticInfo','NK.Common.System.UserData.NKCharacterInfo','System.Int32',
    'NK.StaticData.Categoricals.CostumeTableId','System.Int32','System.Int32','System.Int32','NK.Common.System.Stat.CharacterStatData',
    'NK.Common.System.UserData.EquipsAndCube','NK.Common.System.UserData.CharacterSnapshot.ItemStateEffects',
    'NK.Common.Util.Monad.Option<NK.Common.System.UserData.NKUser_CharacterData.CharacterSkillDisableStatus>',
    'NK.StaticData.StaticDataLayer.StaticInfo.SkillInfoStaticInfo','NK.StaticData.StaticDataLayer.StaticInfo.SkillInfoStaticInfo',
    'NK.StaticData.StaticDataLayer.StaticInfo.SkillInfoStaticInfo','System.Nullable<NK.StaticData.TableType>','System.Nullable<NK.StaticData.TableType>'];
  if(ctor.parameters.map(p=>p.type.name).join('|')!==parameterTypes.join('|'))throw Error('Exact original constructor signature differs');
  function nullableTable(cls,value) {
    if(!cls.isValueType||cls.valueTypeSize!==8||cls.field('hasValue').offset!==16||cls.field('value').offset!==20)
      throw Error('Current nullable TableType ABI differs');
    const p=Memory.alloc(8);p.writeByteArray([0,0,0,0,0,0,0,0]);
    if(value!==null){p.writeU8(1);p.add(4).writeS32(value);}rawBuffers.push(p);return p;
  }
  const snapshots=[],converted=[],reports=[];
  for(const member of input.characters) {
    emit({status:'captured_snapshot_reconstruction_step',slot:member.slot,phase:'begin_original_source_binding'});
    const expectedMember=expected.characters.find(x=>x.slot===member.slot&&x.sourceCsn===member.sourceCsn);
    if(!expectedMember||!member.emptyBurstOverrides||member.overrideElements.length!==0||
        !/^0{32}$/.test(member.noneSkillDisableStatusRawHex))throw Error('Unsupported original override/Option state');
    const row=rowById(characterTable,findCharacter,member.characterTableId);
    if(i32(row.method('get_NameCode',0),row)!==member.sourceNameCode)throw Error('Original source name-code identity differs');
    const info=typedRaw(infoClass,member.characterInfoRawHex,16,'NKCharacterInfo');
    const encodedLevel=typedRaw(obscured,member.levelObscuredIntRawHex,20,'source Level ObscuredInt');
    // Only the original native conversion decodes this source payload. No
    // expected level or XOR/crypto interpretation is supplied by JavaScript.
    const levelBox=retain(call(originalLevelDecode,null,[encodedLevel.handle]));
    const level=levelBox.unbox().handle.readS32();
    const status=typedRaw(statClass,member.characterStatDataRawHex,240,'CharacterStatData');
    const builder=retain(builderClass.alloc());call(builderCtor,builder);
    if(member.equipmentAndCube.length!==5)throw Error('Exact original five equipment/cube entries required');
    for(const equipment of member.equipmentAndCube)
      call(builderSet,builder,[a32(equipment.subType),a64(equipment.Isn),a32(equipment.Tid),a32(equipment.Level)]);
    const equips=retain(call(builderBuild,builder));
    const effects=retain(effectsClass.alloc()),effectArray=intArray(member.itemStateEffectTids);
    call(effectsCtor,effects,[effectArray.handle]);
    const skillInfos=member.skills.map(skill=>skill.favoriteOverride?rowById(skillTable,findSkill,skill.skillInfoTableId):null);
    const none=typedRaw(ctor.parameters[10].type.class,member.noneSkillDisableStatusRawHex,16,'None skill-disable Option');
    const nullable1=nullableTable(ctor.parameters[14].type.class,member.skills[0].favoriteOverride?member.skills[0].tableType:null);
    const nullable2=nullableTable(ctor.parameters[15].type.class,member.skills[1].favoriteOverride?member.skills[1].tableType:null);
    const snapshot=retain(snapshotClass.alloc());
    emit({status:'captured_snapshot_reconstruction_step',slot:member.slot,phase:'original_constructor_begin'});
    call(ctor,snapshot,[row.handle,info.handle,a32(level),a32(member.costumeTableId),
      ...member.skills.map(skill=>a32(skill.level)),status.handle,equips.handle,effects.handle,none.handle,
      ...skillInfos.map(skill=>skill===null?ptr(0):skill.handle),nullable1,nullable2]);
    emit({status:'captured_snapshot_reconstruction_step',slot:member.slot,phase:'original_constructor_returned'});
    const copied=snapshot.field('<Status>k__BackingField').value;
    if(hex(copied.handle.readByteArray(240))!==member.characterStatDataRawHex)throw Error('Original constructor changed source stat payload');
    emit({status:'captured_snapshot_reconstruction_step',slot:member.slot,phase:'original_converter_begin'});
    const spot=retain(call(converter,null,[snapshot.handle]));
    emit({status:'captured_snapshot_reconstruction_step',slot:member.slot,phase:'original_converter_returned'});
    // Verification begins only after original conversion. None of these
    // expected values participates in constructor arguments or source stats.
    const stat=spot.field('StatusData').value,nativeStats={};
    for(const name of ['HealthPoint','Attack','Defense','EnergyResist','MetalResist','BioResist','CriticalRatio','CriticalDamage','HPRatio'])
      nativeStats[name]=stat.field(name).value.field('Value').value.toString();
    const nativeValues={};
    for(const name of ['Level','Grade','Core','BattlePower','CostumeTableId','HarmonyCubeTableIdID'])
      nativeValues[name]=i32(spot.method('get_'+name,0),spot);
    const nativeSkills={};
    for(const name of ['Skill1Data','Skill2Data','SkillBurstData']) {
      const skill=retain(spot.field(name).value);
      nativeSkills[name]={GroupId:i32(skill.method('get_GroupId',0),skill),Level:i32(skill.method('get_Level',0),skill),
        TableType:i32(skill.method('get_TableType',0),skill),Disable:bool(skill.method('get_Disable',0),skill),
        IsFavoriteItemSkill:bool(skill.method('get_IsFavoriteItemSkill',0),skill)};
    }
    const passive=spot.field('<AddedPassiveList>k__BackingField').value;
    const passiveIds=(listItems(passive)||[]).map(item=>i32(item.method('get_TableId',0),item));
    const csn=i64(spot.method('get_CSN',0),spot);
    const originalEffects=retain(call(snapshot.method('get_ItemStateEffectTidList',0),snapshot));
    const effectIds=(listItems(originalEffects)||[]).map(item=>item.unbox().handle.readS32());
    const dictionary=retain(equips.field('_dict').value);
    const equipmentReadback=member.equipmentAndCube.map(item=>{
      const native=retain(call(dictionary.method('get_Item',1),dictionary,[a32(item.subType)]));
      return {subType:item.subType,Isn:i64(native.method('get_Isn',0),native),Tid:i32(native.method('get_Tid',0),native),Level:i32(native.method('get_Level',0),native)};
    });
    const expectedNative=expectedMember.nativeConversion;
    const checks={csn:csn===member.sourceCsn,stats:JSON.stringify(nativeStats)===JSON.stringify(expectedNative.stats),
      values:JSON.stringify(nativeValues)===JSON.stringify(expectedNative.values),skills:JSON.stringify(nativeSkills)===JSON.stringify(expectedNative.skills),
      passiveRecordIds:JSON.stringify(passiveIds)===JSON.stringify(expectedNative.addedPassiveRecordIds),
      originalEffectTids:JSON.stringify(effectIds)===JSON.stringify(member.itemStateEffectTids),
      originalEquipment:JSON.stringify(equipmentReadback)===JSON.stringify(member.equipmentAndCube)};
    const result={status:'captured_snapshot_native_conversion_readback',slot:member.slot,csn,checks,
      passed:Object.values(checks).every(Boolean),nativeStats,nativeValues,nativeSkills,passiveIds,
      originalEffectTids:effectIds,originalEquipment:equipmentReadback,
      battleStarted:false,transporterInstalled:false,combatOutputsUsedAsInputs:false};
    emit(result);reports.push(result);snapshots.push(snapshot);converted.push(spot);
    if(!result.passed)throw Error('Original captured snapshot conversion differs at slot '+member.slot);
  }
  return {snapshots,converted,reports,roots,rawBuffers,passed:reports.length===5&&reports.every(x=>x.passed),
    scope:'Original constructor/converter readback only; no native battle or simulator parity',completeReplayInputVerified:false};
}
