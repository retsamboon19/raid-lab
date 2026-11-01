// Disposable current153 player only. Constructs original input objects, never
// installs the static transporter, starts a fight, or edits loaded combat stats.
function isAcceptedCapturedPracticeNativeOwnerReceipt(spec, receipt) {
  if(!spec||!receipt||receipt.sourceNativeType!==spec.type)return false;
  // Preserve the independent original-owner path and its source receipt gate.
  if(receipt.kind==='original_private_native_owner')
    return /^[0-9a-f]{64}$/.test(receipt.receiptSha256||'');
  if(receipt.kind!=='host_output_boundary')return false;
  const pause=spec.name==='OnSpotPauseFirstButton'||spec.name==='OnSpotPauseSecondButton';
  const finish=spec.name==='OnBattleFinish';
  if(!pause&&!finish&&spec.name!=='OnBattleRetry')return false;
  // Building an original output packet is permitted; submitting account data
  // and mutating combat are not. The retired combined claim concealed that
  // distinction and must not validate as the current host boundary schema.
  return !Object.prototype.hasOwnProperty.call(receipt,'serializesOrSubmitsAccountData')&&
    receipt.fieldName===spec.name&&receipt.sourceNativeFieldOffset===spec.offset&&
    receipt.originalUiCallbacksReplayed===false&&receipt.mutatesCombatState===false&&
    receipt.submitsAccountData===false&&receipt.originalPacketCaptureBeforeCleanup===finish&&
    receipt.capturedTupleLabelPreserved===pause&&
    receipt.behavior===(finish?'retain_result_and_capture_original_packet_before_cleanup':
      'reject_if_invoked_unattended');
}

function prepareCapturedPracticeFixture(runtime, staticImage, pin, emit, input, expected, bindings) {
  'use strict';
  bindings=bindings||{};
  const fixture=input.fixtureInput,source=input.snapshotInput;
  if(!fixture||!source||fixture.captureSha256!==source.captureSha256||fixture.transporterValueSize!==376)
    throw Error('Hash-bound original fixture/snapshot packet required');
  const game=Process.getModuleByName('GameAssembly.dll'),roots=[],rawBuffers=[];
  const retain=obj=>{if(obj==null||obj.isNull())throw Error('Required original native reference absent');pin(obj);roots.push(obj);return obj;};
  const call=(method,self=null,args=[])=>invokeChecked(method,self,args);
  const at=(method,rva)=>{if(!method.virtualAddress.equals(game.base.add(rva)))throw Error('Source-bound fixture method differs '+method.name);return method;};
  const a32=n=>{if(!Number.isSafeInteger(n))throw Error('Captured Int32 required');const p=Memory.alloc(4);p.writeS32(n);rawBuffers.push(p);return p;};
  const i32=(method,self)=>retain(call(method,self)).unbox().handle.readS32();
  const i64=(method,self)=>retain(call(method,self)).unbox().handle.readS64().toString();
  const boolean=(method,self)=>retain(call(method,self)).unbox().handle.readU8()!==0;
  const hex=data=>Array.from(new Uint8Array(data),x=>x.toString(16).padStart(2,'0')).join('');
  const raw=string=>{if(!/^(?:[0-9a-f]{2})*$/.test(string))throw Error('Invalid source raw value');return (string.match(/../g)||[]).map(x=>parseInt(x,16));};
  const strLen=new NativeFunction(game.getExportByName('il2cpp_string_length'),'int',['pointer']);
  const strChars=new NativeFunction(game.getExportByName('il2cpp_string_chars'),'pointer',['pointer']);
  const stringValue=pointer=>pointer.isNull()?null:strChars(pointer).readUtf16String(strLen(pointer));
  const assignable=new NativeFunction(game.getExportByName('il2cpp_class_is_assignable_from'),'bool',['pointer','pointer']);
  const setFieldObject=new NativeFunction(game.getExportByName('il2cpp_field_set_value_object'),'void',['pointer','pointer','pointer']);
  const setFieldValue=new NativeFunction(game.getExportByName('il2cpp_field_set_value'),'void',['pointer','pointer','pointer']);
  const replay=bindings.replay||runCapturedSnapshotReconstruction(runtime,staticImage,pin,emit,source,expected);
  if(!replay.passed||replay.snapshots.length!==5||replay.converted.length!==5)throw Error('Five successful original snapshot roundtrips required');
  if(fixture.teamConversion.buffInfos!==null)throw Error('Unsupported captured nonnull team buff graph');
  const snapshotClass=runtime.class('NK.Common.System.UserData.CharacterSnapshot');
  const array=Il2Cpp.array(snapshotClass,5);retain(array.object);
  const arraySet=Il2Cpp.corlib.class('System.Array').method('SetValue').overload('System.Object','System.Int32');
  replay.snapshots.forEach((snapshot,index)=>call(arraySet,array.object,[snapshot.handle,a32(index)]));
  const extension=runtime.class('NK.Common.System.UserData.CharacterSnapshotExtension');
  const createTeam=at(extension.method('CreateSpotTeamData').overload(
    'System.Collections.Generic.IReadOnlyList<NK.Common.System.UserData.CharacterSnapshot>',
    'System.Collections.Generic.List<NK.StaticData.StaticDataLayer.StaticInfo.BuffStaticInfo[]>','System.Int32'),fixture.teamConversion.methodRva);
  const team=retain(call(createTeam,null,[array.handle,ptr(0),a32(fixture.teamConversion.statIncrease)]));
  const groups=retain(team.field('<CharacterDataList>k__BackingField').value);
  if(i32(groups.method('get_Count',0),groups)!==1)throw Error('Original flat team did not retain one logical team');
  const members=retain(call(groups.method('get_Item',1),groups,[a32(0)]));
  if(i32(members.method('get_Count',0),members)!==5)throw Error('Original team logical count differs');
  const teamChecks=[];
  for(let index=0;index<5;index++) {
    const member=retain(call(members.method('get_Item',1),members,[a32(index)]));
    const ref=expected.characters[index].nativeConversion;
    const stats=member.field('StatusData').value,actualStats={};
    for(const name of Object.keys(ref.stats))actualStats[name]=stats.field(name).value.field('Value').value.toString();
    const row=retain(member.field('<CharacterStaticInfo>k__BackingField').value);
    const values={},skills={};
    for(const name of Object.keys(ref.values))values[name]=i32(member.method('get_'+name,0),member);
    for(const name of ['Skill1Data','Skill2Data','SkillBurstData']){
      const skill=retain(member.field(name).value);
      skills[name]={GroupId:i32(skill.method('get_GroupId',0),skill),Level:i32(skill.method('get_Level',0),skill),
        TableType:i32(skill.method('get_TableType',0),skill),Disable:boolean(skill.method('get_Disable',0),skill),
        IsFavoriteItemSkill:boolean(skill.method('get_IsFavoriteItemSkill',0),skill)};
    }
    const passive=retain(member.field('<AddedPassiveList>k__BackingField').value),passiveCount=i32(passive.method('get_Count',0),passive);
    if(passiveCount<0||passiveCount>256)throw Error('Original team passive count bound');
    const passiveIds=Array.from({length:passiveCount},(_,i)=>{
      const item=retain(call(passive.method('get_Item',1),passive,[a32(i)]));return i32(item.method('get_TableId',0),item);
    });
    const actual={slot:i32(member.method('get_PositionType',0),member),csn:i64(member.method('get_CSN',0),member),
      tableId:i32(row.method('get_TableId',0),row),nameCode:i32(row.method('get_NameCode',0),row),stats:actualStats,values,skills,passiveIds};
    const passed=actual.slot===source.characters[index].slot&&actual.csn===source.characters[index].sourceCsn&&
      actual.tableId===source.characters[index].characterTableId&&actual.nameCode===source.characters[index].sourceNameCode&&
      JSON.stringify(actualStats)===JSON.stringify(ref.stats)&&JSON.stringify(values)===JSON.stringify(ref.values)&&
      JSON.stringify(skills)===JSON.stringify(ref.skills)&&JSON.stringify(passiveIds)===JSON.stringify(ref.addedPassiveRecordIds);
    teamChecks.push({passed,...actual});
  }
  if(teamChecks.some(check=>!check.passed))throw Error('Original team conversion changed captured ordered unit/stat values');
  const cls=runtime.class('NK.Spot.Data.NKSpotDataTransporter');
  if(!cls.isValueType||cls.valueTypeSize!==376)throw Error('Current native transporter value size differs');
  const box=retain(cls.alloc()),value=box.unbox(),ownerBindings=new Map(),unsupported=[];
  for(const spec of fixture.fields.filter(f=>f.kind==='nativeOwnerBinding')) {
    const binding=typeof bindings.resolveNativeOwnerField==='function'?bindings.resolveNativeOwnerField(spec):null;
    const receipt=binding&&binding.receipt;
    const allowed=isAcceptedCapturedPracticeNativeOwnerReceipt(spec,receipt);
    if(!binding||!binding.value||!allowed) {
      unsupported.push({field:spec.name,type:spec.type,reason:'Fresh typed original owner or explicit audited host-output boundary receipt required'});
    } else ownerBindings.set(spec.name,binding);
  }
  if(typeof bindings.resolveWaveData!=='function')unsupported.push({field:'originalWaveDataStaticInfo',reason:'Original source-bound WaveDataTable resolver required'});
  if(unsupported.length) {
    const result={transporterBox:null,readback:null,team,snapshots:replay.snapshots,converted:replay.converted,
      passed:false,unsupported,roots,rawBuffers,teamChecks,transporterExactReplay:false};
    emit({status:'captured_practice_fixture_unsupported',unsupported,teamChecksPassed:true});return result;
  }
  const waveBinding=bindings.resolveWaveData(fixture.wave.tableId);
  if(!waveBinding||!waveBinding.value||!waveBinding.receipt||
      waveBinding.receipt.kind!=='original_static_table_lookup'||waveBinding.receipt.methodRva!==0x05180c90||
      !/^[0-9a-f]{64}$/.test(waveBinding.receipt.receiptSha256||''))throw Error('Original WaveDataTable.FindById receipt absent');
  const wave=retain(waveBinding.value);
  if(wave.class.type.name!==fixture.wave.requiredNativeType||i32(wave.method('get_TableId',0),wave)!==fixture.wave.tableId)
    throw Error('Original wave static-info identity differs');
  const fieldChecks=[],nativeValues=new Map();
  for(const spec of fixture.fields) {
    const field=box.field(spec.name),type=field.type.class;
    if(field.offset!==spec.sourceNativeFieldOffset||field.type.name!==spec.type)throw Error('Exact transporter field layout differs '+spec.name);
    let assignment,argument,reference=null,byteValue=null,verifiedZeroInitialization=false;
    if(spec.kind==='reconstructedOriginalTeam'){assignment=team;argument=team.handle;reference=team.handle;}
    else if(spec.kind==='nullReference'){assignment=null;argument=ptr(0);reference=ptr(0);}
    else if(spec.kind==='string'){
      const text=Il2Cpp.string(spec.value);assignment=new Il2Cpp.Object(text.handle);retain(assignment);argument=assignment.handle;reference=argument;
    } else if(spec.kind==='nativeOwnerBinding'){
      const binding=ownerBindings.get(spec.name);assignment=retain(binding.value);
      if(!assignable(type.handle,assignment.class.handle))throw Error('Host binding native type differs '+spec.name);
      if(type.isValueType){const unboxed=assignment.unbox();argument=unboxed.handle;byteValue=hex(unboxed.handle.readByteArray(type.valueTypeSize));}
      else{argument=assignment.handle;reference=argument;}
      if(spec.semanticTuple){
        const tuple=assignment.unbox();
        for(const [name,semantic] of Object.entries(spec.semanticTuple)) {
          const child=tuple.field(name).value;
          if(typeof semantic==='string'&&stringValue(child.handle)!==semantic)throw Error('Original pause label differs '+spec.name);
          if(semantic&&semantic.requiredNonNull&&child.isNull())throw Error('Original required pause delegate absent '+spec.name);
        }
      }
    } else if(['enum32','zeroValueType','originalValueType'].includes(spec.kind)){
      if(!type.isValueType||type.valueTypeSize!==spec.valueSize)throw Error('Captured field value layout differs '+spec.name);
      if(spec.kind==='zeroValueType'){
        argument=Memory.alloc(spec.valueSize);argument.writeByteArray(raw(spec.rawHex));rawBuffers.push(argument);
        byteValue=spec.rawHex;verifiedZeroInitialization=!spec.setter;
        if(verifiedZeroInitialization&&hex(box.handle.add(spec.sourceNativeFieldOffset).readByteArray(spec.valueSize))!==spec.rawHex)
          throw Error('Fresh native value is not the captured source zero state '+spec.name);
      }else{
        assignment=retain(type.alloc());const own=assignment.unbox();
        if(spec.kind==='enum32')own.handle.writeS32(spec.value);else own.handle.writeByteArray(raw(spec.rawHex));
        argument=own.handle;byteValue=hex(own.handle.readByteArray(spec.valueSize));
      }
    } else {
      assignment=spec.value;
      if(spec.kind==='float32'){argument=Memory.alloc(4);argument.writeByteArray(raw(spec.bitsLE));byteValue=spec.bitsLE;}
      else if(spec.kind==='bool'){argument=Memory.alloc(1);argument.writeU8(spec.value?1:0);byteValue=spec.value?'01':'00';}
      else if(spec.kind==='int32'){argument=a32(spec.value);byteValue=hex(argument.readByteArray(4));}
      else if(spec.kind==='int64'){argument=Memory.alloc(8);argument.writeS64(int64(spec.value));byteValue=hex(argument.readByteArray(8));}
      else throw Error('Unsupported source field kind '+spec.kind);
      rawBuffers.push(argument);
    }
    const fieldSize=type.isValueType?type.valueTypeSize:Process.pointerSize;
    if(!Number.isInteger(fieldSize)||fieldSize<1||fieldSize>376)throw Error('Native fixture field-size bound '+spec.name);
    const address=box.handle.add(spec.sourceNativeFieldOffset);
    const beforeBytes=hex(address.readByteArray(fieldSize));
    // Exact153 object setter writes an object pointer only; it NEVER unboxes
    // enums/structs. Public values require generic field_set_value with the
    // original typed payload. Public references use the object write barrier.
    if(spec.setter){const setter=at(value.method(spec.setter.name,1),spec.setter.nativeRva);call(setter,value,[argument]);}
    else if(!verifiedZeroInitialization) {
      if(type.isValueType)setFieldValue(box.handle,field.handle,argument);
      else setFieldObject(box.handle,field.handle,assignment===null?ptr(0):assignment.handle);
    }
    const actualBytes=hex(address.readByteArray(fieldSize));
    let passed;
    if(reference!==null)passed=address.readPointer().equals(reference);
    else passed=actualBytes===byteValue;
    fieldChecks.push({field:spec.name,kind:spec.kind,passed,setterRva:spec.setter&&spec.setter.nativeRva,verifiedZeroInitialization,
      receipt:ownerBindings.has(spec.name)?ownerBindings.get(spec.name).receipt:null});
    nativeValues.set(spec.name,{spec,address,reference});
    if(!passed){
      emit({status:'captured_practice_fixture_field_mismatch',field:spec.name,declaredType:spec.type,
        nativeFieldType:field.type.name,nativeIsValueType:!!type.isValueType,nativeFieldSize:fieldSize,
        boxedFieldOffset:field.offset,fieldInfo:field.handle.toString(),fieldAddress:address.toString(),
        boxedOwner:box.handle.toString(),argument:argument.toString(),beforeBytes,
        expectedBytes:byteValue,expectedReference:reference===null?null:reference.toString(),actualBytes,
        assignmentPath:spec.setter?'original_property_setter':verifiedZeroInitialization?'verified_source_zero':
          type.isValueType?'generic_typed_payload_setter':'object_reference_setter'});
      throw Error('Original semantic field readback differs '+spec.name);
    }
  }
  const getInt=name=>i32(value.method('get_'+name,0),value);
  const getBool=name=>retain(call(value.method('get_'+name,0),value)).unbox().handle.readU8()!==0;
  const time=retain(call(value.method('get_TimeLimit',0),value)).unbox().handle.readFloat();
  const readback={managementType:getInt('ManagementType'),processType:getInt('ProcessType'),timeLimit:time,
    teamType:box.field('TeamType').value.field('value__').value,teamNumber:box.field('TeamNumber').value,
    waveId:getInt('WaveId'),monsterStageLv:getInt('MonsterStageLv'),dynamicObjectLv:getInt('DynamicObjectLv'),
    randomSeed:getInt('RandomSeed'),isAuto:getBool('IsAuto'),isMockBattle:getBool('IsMockBattle'),tddProcess:getBool('TDDProcess'),
    transporterValueTypeSize:376,myTeamDataPresent:true,captureSourceSha256:fixture.captureSha256,
    orderedTeam:teamChecks.map(({slot,csn,tableId,nameCode})=>({slot,csn,tableId,nameCode}))};
  const adapters=Array.from(ownerBindings.values()).some(binding=>binding.receipt.kind==='host_output_boundary');
  const result={transporterBox:box,readback,team,snapshots:replay.snapshots,converted:replay.converted,
    passed:fieldChecks.every(check=>check.passed)&&teamChecks.every(check=>check.passed),roots,rawBuffers,
    fieldChecks,teamChecks,waveStaticInfo:wave,transporterExactReplay:!adapters,
    callbackBehaviorOriginal:!adapters,staticTransporterInstalled:false,battleStarted:false};
  emit({status:'captured_practice_fixture_prepared',passed:result.passed,readback,fieldChecks,teamChecks,
    transporterExactReplay:result.transporterExactReplay,staticTransporterInstalled:false,battleStarted:false});
  return result;
}
