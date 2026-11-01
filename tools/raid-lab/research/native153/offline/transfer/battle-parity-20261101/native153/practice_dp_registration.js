// Original signed DP catalog registration, with no asset preloading or battle.
function beginOriginalPracticeDpRegistration(pin,emit) {
  if(typeof pin!=='function'||typeof emit!=='function')throw Error('Original DP registration requires retained ownership/evidence');
  const game=Process.getModuleByName('GameAssembly.dll');
  const cls=Il2Cpp.domain.assembly('Unity.Addressables').image.class('UnityEngine.AddressableAssets.Addressables');
  const method=cls.method('LoadCatalogDatabaseAsync',1);
  const prefix='48895c2408574883ec50803d24fd7603';
  const hex=(p,n)=>Array.from(new Uint8Array(p.readByteArray(n)),b=>b.toString(16).padStart(2,'0')).join('');
  if(!method.isStatic||method.parameters[0].type.name!=='System.String'||
     method.returnType.name!=='UnityEngine.ResourceManagement.AsyncOperations.AsyncOperationHandle<UnityEngine.AddressableAssets.ResourceLocators.IResourceLocator>'||
     !method.virtualAddress.equals(game.base.add(0x081e4250))||hex(method.virtualAddress,16)!==prefix)
    throw Error('Original current153 signed DP registration binding differs');
  const retained=[];
  const keep=obj=>{if(obj==null||obj.handle.isNull())throw Error('Original DP registration returned null');pin(obj);retained.push(obj);return obj;};
  // String has no Object.ref. Root an Object over the SAME existing native handle.
  const project=Il2Cpp.string('dp');keep(new Il2Cpp.Object(project.handle));retained.push(project);
  const operation=keep(invokeChecked(method,null,[project.handle]));
  let ready=null;
  emit({status:'original_practice_dp_registration_started',projectName:'dp',originalMethodRva:0x081e4250,
    directControlVerificationSha256:'bc973e780bc49936f94e1a1890ae4e162cd837b9fe80ebfbda69ebe8e61aba19',
    assetPreloads:0,signatureVerificationUnchanged:true});
  function poll(){
    if(ready)return ready;
    const value=operation.unbox();
    const complete=keep(invokeChecked(value.method('get_IsDone',0),value)).unbox().handle.readU8()!==0;
    if(!complete)return {ready:false,projectName:'dp'};
    // Same original status conversion exercised by the passing direct controls.
    const status=String(value.method('get_Status',0).invoke());
    if(status!=='Succeeded'){
      const error=value.method('get_OperationException',0).invoke();
      emit({status:'original_practice_dp_registration_failed',originalStatus:status,error:String(error)});
      throw Error('Original DP catalog registration '+status+': '+String(error));
    }
    const locator=keep(invokeChecked(value.method('get_Result',0),value));
    if(locator.class.type.name!=='UnityEngine.AddressableAssets.ResourceLocators.CatalogDatabase')
      throw Error('Original DP registration returned an unexpected locator class');
    ready={ready:true,projectName:'dp',originalStatus:status,locator,originalMethodRva:0x081e4250};
    emit({status:'original_practice_dp_registration_ready',projectName:'dp',originalStatus:status,
      locator:locator.handle.toString(),locatorClass:locator.class.type.name,assetPreloads:0});
    return ready;
  }
  return {poll,retained,operation,projectName:'dp'};
}
