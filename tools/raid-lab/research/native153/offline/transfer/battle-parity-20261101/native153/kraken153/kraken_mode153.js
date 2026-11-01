'use strict';
// Original current153 mode entry. Host supplies the frozen binding and actual
// Kraken capture contract; this module never manufactures transporter values.
const KRAKEN153_CLIENT='d39896d3770888039c728a1908448c3db5efa7cdf874c90d56f46d8d566428d2';
const KRAKEN153_PROCESS_METADATA='38011bccaf2f41fcf9e95b42b2974c45949432c7313d4e4e5b25dd709650bc77';
const KRAKEN153_ENCOUNTER_SOURCE='c33edc642e1840ec116ccbc5f8405a406ce2efa99107789b2109aa9d5421fded';

function validateCapturedKrakenMode153(input) {
  const hash=value=>typeof value==='string'&&/^[a-f0-9]{64}$/.test(value);
  const i32=value=>Number.isInteger(value)&&value>=-2147483648&&value<=2147483647;
  if(!input||input.schemaVersion!==1||input.sourceKind!=='actual_offline_kraken_prebattle'||
      input.clientSha256!==KRAKEN153_CLIENT||input.processMetadataSha256!==KRAKEN153_PROCESS_METADATA||
      input.encounterSourceSha256!==KRAKEN153_ENCOUNTER_SOURCE||
      !hash(input.captureSha256)||!hash(input.fixtureInputSha256)||!hash(input.snapshotInputSha256)||
      !hash(input.captureProvenanceSha256)||input.processType!==7||input.waveId!==6302009||input.timeLimit!==180)
    throw Error('An actual source-bound current153 Kraken capture is required');
  if(!Array.isArray(input.characters)||input.characters.length!==5||input.characters.some(row=>
      !row||!i32(row.tableId)||row.tableId<1||!i32(row.nameCode)||row.nameCode<1||
      !Number.isInteger(row.slot)||row.slot<0||row.slot>10)||new Set(input.characters.map(row=>row.slot)).size!==5)
    throw Error('Kraken capture must preserve five valid original actor identities and logical slots');
  const t=input.capturedTransporter;
  if(!t||t.managementType!==0||t.waveId!==input.waveId||t.timeLimit!==input.timeLimit||
      !i32(t.processType)||!i32(t.teamType)||!i32(t.teamNumber)||
      !i32(t.monsterStageLv)||t.monsterStageLv<1||
      !i32(t.dynamicObjectLv)||t.dynamicObjectLv<1||
      !i32(t.raidLvChangeGroup)||t.raidLvChangeGroup<0||
      !i32(t.randomSeed)||t.randomSeed<1||
      t.isAuto!==true||t.isMockBattle!==false||t.tddProcess!==false)
    throw Error('Actual Kraken transporter semantics are missing or unsupported');
  return input;
}

function verifyCapturedKrakenTransporter153(input,fixture) {
  validateCapturedKrakenMode153(input);
  if(!fixture||fixture.passed!==true||fixture.sourceKind!==input.sourceKind||
      fixture.captureSha256!==input.captureSha256||fixture.fixtureInputSha256!==input.fixtureInputSha256||
      fixture.readback?.transporterValueTypeSize!==376||fixture.staticTransporterInstalled!==false||
      fixture.battleStarted!==false||fixture.transporterExactReplay!==false)
    throw Error('Separately verified Kraken fixture readback is required');
  for(const [key,value] of Object.entries(input.capturedTransporter))
    if(fixture.readback[key]!==value)throw Error('Kraken transporter readback differs: '+key);
  if(!Array.isArray(fixture.teamChecks)||fixture.teamChecks.length!==5||fixture.teamChecks.some((row,index)=>
      !row.passed||row.slot!==input.characters[index].slot||row.tableId!==input.characters[index].tableId||
      row.nameCode!==input.characters[index].nameCode))throw Error('Kraken native team conversion differs');
  return true;
}

function guardOriginalKrakenEntry153(runtime) {
  const binding=globalThis.KRAKEN153_MODE_BINDING;
  if(!binding||binding.clientSha256!==KRAKEN153_CLIENT||binding.processMetadataSha256!==KRAKEN153_PROCESS_METADATA||
      binding.encounterSourceSha256!==KRAKEN153_ENCOUNTER_SOURCE||binding.nativeRunPerformed!==false)
    throw Error('Frozen Kraken native-entry source binding required');
  const cls=runtime.class('NK.Spot.Context.Process.InterceptProcess');
  if(cls.type.name!=='NK.Spot.Context.Process.InterceptProcess'||cls.parent?.type?.name!=='NK.Spot.Context.Process.CampaignProcess'||
      cls.instanceSize!==136||cls.isValueType)throw Error('Original InterceptProcess class layout differs');
  const base=Process.getModuleByName('GameAssembly.dll').base;
  const methods={};
  for(const [name,rva,args] of [['.ctor',0x0712d170,['NK.StaticData.SpotModType']],['CreateContext',0x0712d080,[]]]) {
    const method=cls.method(name,args.length),spec=binding.methods.find(row=>row.name===name);
    if(!spec||spec.rva!==rva||method.isStatic||method.returnType.name!=='System.Void'||
        method.parameters.map(p=>p.type.name).join('|')!==args.join('|')||
        Number(method.relativeVirtualAddress)!==rva||!method.virtualAddress.equals(base.add(rva))||
        !Array.isArray(spec.fragments)||spec.fragments.length!==1||spec.fragments[0].rva!==rva)
      throw Error('Original InterceptProcess method ABI differs: '+name);
    for(const fragment of spec.fragments) {
      if(typeof fragment.bytes!=='string'||! /^(?:[a-f0-9]{2})+$/.test(fragment.bytes)||
          fragment.bytes.length/2!==fragment.byteLength||fragment.byteLength<1||fragment.byteLength>16384)
        throw Error('Invalid Kraken entry-byte guard');
      const bytes=base.add(fragment.rva).readByteArray(fragment.byteLength);
      const hex=Array.from(new Uint8Array(bytes),v=>v.toString(16).padStart(2,'0')).join('');
      if(hex!==fragment.bytes)throw Error('Original InterceptProcess full entry bytes differ: '+name);
    }
    methods[name]=method;
  }
  return {cls,methods};
}

function createOriginal153KrakenProcess(runtime,staticImage,management,pin,emit,input,fixture) {
  verifyCapturedKrakenTransporter153(input,fixture);
  const {cls,methods}=guardOriginalKrakenEntry153(runtime);
  const call=(method,self=null,args=[])=>invokeChecked(method,self,args);
  const i32=(method,self)=>call(method,self).unbox().handle.readS32();
  const enumValue=staticImage.class('NK.StaticData.SpotModType').field('Intercept').value;
  if((typeof enumValue==='number'?enumValue:Number(enumValue.field('value__').value))!==7)
    throw Error('Original Intercept enum differs');
  const process=pin(cls.alloc());
  call(methods['.ctor'],process,[intArg(7)]);
  const set=runtime.class('NK.Spot.SpotManagement').method('SetProcess',1);
  if(set.isStatic||set.returnType.name!=='System.Void'||Number(set.relativeVirtualAddress)!==0x07607310||
      !set.virtualAddress.equals(Process.getModuleByName('GameAssembly.dll').base.add(0x07607310))||
      set.parameters.map(p=>p.type.name).join('|')!=='NK.Spot.Context.Process.ProcessBase')
    throw Error('Original manager SetProcess signature differs');
  call(set,management,[process.handle]);
  const retained=management.field('_process').value;
  if(!retained||retained.isNull()||!retained.handle.equals(process.handle)||i32(process.method('get_ProcessType',0),process)!==7)
    throw Error('Original manager did not retain the Intercept process');
  const list=name=>{
    const value=process.field(name).value;
    if(!value||value.isNull())throw Error('Original Intercept condition list missing');
    const count=i32(value.method('get_Count',0),value);
    if(count<0||count>16)throw Error('Original Intercept condition list bound');
    return Array.from({length:count},(_,index)=>call(value.method('get_Item',1),value,[intArg(index)]).unbox().handle.readS32());
  };
  const clearConditions=list('ClearConditionList'),failConditions=list('FailConditionList');
  if(clearConditions.join('|')!=='1|0|2'||failConditions.length!==0)
    throw Error('Original Intercept constructor conditions changed');
  // The original override owns Campaign.CreateContext and the Intercept-specific
  // setup. Do not call the parent instead or reimplement its config side effects.
  call(methods.CreateContext,process);
  emit({status:'original153_kraken_context_created',processType:7,processClass:cls.type.name,
    originalInterceptConstructorInvoked:true,originalInterceptCreateContextInvoked:true,
    clearConditions,failConditions,conditionsWritten:false,captureSha256:input.captureSha256,
    tableConfiguredCoverStageLv:8,tableConfiguredLimitCharacterLv:400,
    actualCoverOrLevelModeCaptured:false,fullAccuracyVerified:false});
  return process;
}
