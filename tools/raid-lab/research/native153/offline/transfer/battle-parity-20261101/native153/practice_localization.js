// Original current153 ArenaSimulation local-locale setup, before the practice
// probe and original overlay Show. Call on main; pin roots through process exit.
function startOriginalPracticeLocalization(runtime,pin,emit,done) {
  'use strict';
  const binding=globalThis.PRACTICE_LOCALIZATION_BINDING;
  const fixture=globalThis.PRACTICE_LOCALIZATION_FIXTURE;
  const state={status:'starting',ready:false,roots:[],fault:null};
  let timer=null,scheduled=false,delivered=false;
  const keep=value=>{if(value==null||value.isNull())throw Error('Original localization native reference is null');
    pin(value);state.roots.push(value);return value;};
  const call=(method,self=null,args=[])=>invokeChecked(method,self,args);
  function checkAsyncFault(){
    if(typeof firstAsyncFault!=='undefined'&&firstAsyncFault){
      if(!state.observedAsyncError){
        const original=firstAsyncFault;
        state.observedAsyncError=original instanceof Error?original:new Error(original.error||String(original));
        if(!(original instanceof Error))state.observedAsyncError.nativeFrames=original.nativeFrames||[];
        state.originalAsyncFault=original;
      }
      throw state.observedAsyncError;
    }
  }
  state.check=()=>{if(state.fault)throw state.fault;checkAsyncFault();return state.ready;};
  function fail(error){
    state.fault=state.fault||error;state.status='failed';if(timer!==null)clearInterval(timer);
    try{emit({status:'original_practice_localization_failed',error:String(state.fault),nativeFrames:state.fault.nativeFrames||[]});}catch(_){}
    if(!delivered){delivered=true;done(state.fault,state);}
  }
  try{
    if(typeof pin!=='function'||typeof emit!=='function'||typeof done!=='function'||
        typeof onMain!=='function'||Process.pointerSize!==8||
        globalThis.PRACTICE_LOCALIZATION_BINDING_SHA256!==
          '7621643f35dce4a77c4b8b1b99f2f64cbacee29bcecf4ec697f27a6b03efe2d8'||
        binding?.clientSha256!=='d39896d3770888039c728a1908448c3db5efa7cdf874c90d56f46d8d566428d2'||
        binding.metadataSha256!=='0a6f081085208b211999c416357fcce2fb5411e8d300f44123da667ba289bc5c')
      throw Error('Exact153 original localization source/main-thread binding required');
    if(globalThis.PRACTICE_LOCALIZATION_FIXTURE_SHA256!==binding.fixtureSha256||
        fixture?.status!=='original153_local_fixture_bytes_staged'||fixture.sourceProofSha256!==binding.assetSourceSha256||
        fixture.installedFilesWritten!==false||fixture.catalogsRewritten!==false||fixture.signatureBytesChanged!==false||
        !Array.isArray(fixture.copies)||fixture.copies.length!==5)
      throw Error('Exact original five-file private localization fixture required');
    for(const expected of binding.requiredFiles){
      const rows=fixture.copies.filter(row=>row.assetKey===expected.assetKey);
      if(rows.length!==1||rows[0].sha256!==expected.sha256||rows[0].bytes!==expected.bytes)
        throw Error('Original localization fixture file differs: '+expected.assetKey);
    }
    checkAsyncFault();
    const game=Process.getModuleByName('GameAssembly.dll');
    for(const frag of binding.codeFragments){
      const bytes=Array.from(new Uint8Array(game.base.add(frag.rva).readByteArray(frag.bytes.length/2)),
        x=>x.toString(16).padStart(2,'0')).join('');
      if(bytes!==frag.bytes)throw Error('Original localization method bytes differ: '+frag.rva.toString(16));
    }
    const at=(method,spec)=>{
      if(method.isStatic!==spec.isStatic||Number(method.relativeVirtualAddress)!==spec.rva||
          method.returnType.name!==spec.returns||
          method.parameters.map(p=>p.type.name).join('|')!==spec.parameters.join('|'))
        throw Error('Original localization method ABI differs: '+spec.name);
      return method;
    };
    const initializer=runtime.class(binding.methods.tables.class);
    const tables=at(initializer.method(binding.methods.tables.name,0),binding.methods.tables);
    const readiness=at(initializer.method(binding.methods.readiness.name,0),binding.methods.readiness);
    const localImage=Il2Cpp.domain.assembly(binding.methods.catalog.assembly).image;
    const catalog=at(localImage.class(binding.methods.catalog.class).method(binding.methods.catalog.name,0),binding.methods.catalog);
    const readCatalog=()=>{
      const value=call(catalog).unbox().handle.readU8();
      if(value!==0&&value!==1)throw Error('Original localization readiness getter returned malformed boolean');
      return value===1;
    };
    state.catalogUpdatedBefore=readCatalog();checkAsyncFault();
    state.task=keep(call(tables));checkAsyncFault();
    const taskValue=state.task.unbox();
    state.awaiter=keep(call(taskValue.method('GetAwaiter',0),taskValue));checkAsyncFault();
    state.status='registering';state.startedAt=Date.now();
    emit({status:'original_practice_localization_started',mode:binding.mode,
      catalogUpdatedBefore:state.catalogUpdatedBefore,fixtureSha256:binding.fixtureSha256,
      originalTablesInitializerRva:binding.methods.tables.rva,originalReadinessInitializerPending:true,
      languageSetterCalledByHost:false,newLanguagePreferenceInput:false});
    state.poll=()=>{
      if(state.status!=='registering')return state.check();
      try{
        checkAsyncFault();
        if(Date.now()-state.startedAt>30000)throw Error('Original local-locale registration exceeded bounded 30000ms');
        const awaiter=state.awaiter.unbox();
        const completed=call(awaiter.method('get_IsCompleted',0),awaiter).unbox().handle.readU8();
        checkAsyncFault();
        if(completed!==0&&completed!==1)throw Error('Original localization awaiter returned malformed boolean');
        if(completed===0)return false;
        call(awaiter.method('GetResult',0),awaiter);checkAsyncFault();
        state.originalRegistrationTaskCompleted=true;
        // This is the game's own ArenaSimulation readiness initializer. Its
        // source writes CatalogUpdated; the host never writes the field/setter.
        call(readiness);checkAsyncFault();
        state.catalogUpdated=readCatalog();checkAsyncFault();
        if(!state.catalogUpdated)throw Error('Original localization readiness initialization readback is false');
        emit({status:'original_practice_localization_ready',mode:binding.mode,
          originalRegistrationTaskCompleted:true,catalogUpdated:true,
          originalReadinessInitializerCalled:true,hostDirectReadinessFieldWrite:false,
          languageSetterCalledByHost:false,newLanguagePreferenceInput:false,
          selectedLocale:null,selectedLocaleVerified:false,fontClosureLocale:'en',
          originalLocaleSelectionPreserved:true,
          remoteSausCatalogInitialized:false,sqlTableOpenVerified:false,fontBundleLoadedVerified:false,
          beforeOriginalPracticeProbe:true});
        checkAsyncFault();state.ready=true;state.status='ready';
        if(timer!==null)clearInterval(timer);
        if(!delivered){delivered=true;done(null,state);}return true;
      }catch(error){fail(error);return false;}
    };
    const quitting=()=>typeof probeQuitRequested!=='undefined'&&probeQuitRequested;
    timer=setInterval(()=>{
      if(quitting()){clearInterval(timer);return;}
      if(scheduled||state.status!=='registering')return;scheduled=true;
      try{
        // Busy is backpressure, not a failed native operation. Keep callbacks
        // and any caller-owned Unity cleanup on the original main thread.
        if(!onMain(()=>{scheduled=false;if(quitting()){clearInterval(timer);return;}if(state.fault){fail(state.fault);return;}state.poll();}))scheduled=false;
      }catch(error){scheduled=false;state.fault=state.fault||error;}
    },10);
  }catch(error){fail(error);}
  return state;
}
