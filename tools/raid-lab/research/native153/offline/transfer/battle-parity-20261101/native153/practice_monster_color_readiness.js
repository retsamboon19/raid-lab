// Call on the Unity main thread after original resource/actor readiness, or at
// later Playing samples. Evidence only: pending must not block the battle.
// No hooks, forcing loads, state writes, tint calls or animation commands.
function inspectPracticeMonsterColorReadiness(runtime, geometryState, manager, emit) {
  const sourceBindings={
    clientSha256:'d39896d3770888039c728a1908448c3db5efa7cdf874c90d56f46d8d566428d2',
    run3MetadataSha256:'58933dbe6080485c5270a127a2fe5e83070c035e7660d0a22227bf2acb41a741',
    environmentMetadataSha256:'2766179bc36342bf8938e558924c4ed3bc74c67005b4a4aea7b2965ac62892ef',
    monsterGradientMetadataSha256:'4c93205ba6d93f8ea682d80d68b27c2a3ceb0df24e40021cf69202ac68001ca4',
    prefabMetadataSha256:'038d2418a093d6778b9f43dde0bba752f8c385e53c9e58b29d35819b4762bbba',
    animationMetadataSha256:'6239ec3fa7659324d29404bc382ce2715a6ab4cb3a002cc684c830204af6ca12',
    graphicPrefabReceiptSha256:'6642fcf5e8aebbde638ded07753884a84b17cdc063a3f5d4a1c1cecb4e9788ea',
    nativeColorTintMethodRva:'0x06369AB0',nativeEnvironmentInitRva:'0x06E8CE80'
  };
  const result={status:'pending',ready:false,supported:true,sourceBindings,
    scope:'original_environment_and_loaded_prefab_reference_prerequisites',
    environment:{ready:false},loadedMonsters:{ready:false,rows:[]},blockingReasons:[],
    monsterGradientAssignmentRequired:false,completeAnimationInitializationVerified:false,
    tintEffectsVerified:false,combatStateWritten:false,nativeLoadsForced:false,
    sourceCorrection:{prefabOffsetD8:'PartsData, not animation',
      actualAnimationReferenceOffset:'0x28',nativeTintPartsReferenceOffset:'0xD8'}};
  const pending=reason=>{if(!result.blockingReasons.includes(reason))result.blockingReasons.push(reason);};
  const live=value=>value!=null&&!value.isNull();
  const call=(method,self=null,args=[])=>invokeChecked(method,self,args);
  const integer=value=>value.unbox().handle.readS32();
  const boundedCount=(value,label,limit)=>{
    const count=integer(call(value.method('get_Count',0),value));
    if(!Number.isInteger(count)||count<0||count>limit)throw Error(label+' count outside bound');
    return count;
  };
  const checkField=(cls,name,offset,type)=>{
    const field=cls.field(name);
    if(field.isStatic||field.offset!==offset||field.type.name!==type)
      throw Error('Current153 field binding differs: '+cls.type.name+'.'+name);
  };
  const hierarchy=cls=>{
    const names=[];
    for(let current=cls;current!=null;current=current.parent){
      if(names.length>=32)throw Error('Native class hierarchy exceeds bound');
      names.push(current.type.name);
    }
    return names;
  };
  try {
    if(Process.pointerSize!==8||geometryState?.clientSha256!==sourceBindings.clientSha256||
        globalThis.PRACTICE_GRAPHIC_OPTIONS_SOURCE_SHA256!==sourceBindings.graphicPrefabReceiptSha256)
      throw Error('Exact current153 original graphic source binding absent');
    if(typeof invokeChecked!=='function'||typeof intArg!=='function')
      throw Error('Original invocation helpers absent');
    if(geometryState.status!=='ready'){pending('geometry_not_ready');return finish();}
    if(!live(manager)||!live(geometryState.management)||
        !manager.handle.equals(geometryState.management.handle))
      throw Error('Original management identity differs from geometry');
    if(manager.class.type.name!=='NK.Spot.SpotManagement')
      throw Error('Original management native type differs');
    result.management={pointer:manager.handle.toString(),type:manager.class.type.name,
      matchesOriginalGeometryManagement:true};
    const unity=Il2Cpp.domain.assembly('UnityEngine.CoreModule').image;
    const unityAlive=unity.class('UnityEngine.Object').method('op_Implicit',1);
    if(!unityAlive.isStatic||unityAlive.returnType.name!=='System.Boolean'||
        unityAlive.parameters[0]?.type.name!=='UnityEngine.Object')
      throw Error('Original Unity object liveness signature differs');
    const describe=(value,expected)=>{
      if(!live(value))return {managedNonNull:false,expectedType:expected,type:null,pointer:null,
        typeMatches:false,unityObject:false,unityAlive:null,usable:false};
      const types=hierarchy(value.class),unityObject=types.includes('UnityEngine.Object');
      const alive=unityObject?call(unityAlive,null,[value.handle]).unbox().handle.readU8()!==0:null;
      const typeMatches=types.includes(expected);
      return {managedNonNull:true,expectedType:expected,type:value.class.type.name,
        pointer:value.handle.toString(),typeMatches,unityObject,unityAlive:alive,
        usable:typeMatches&&(!unityObject||alive)};
    };
    const controllerClass=runtime.class('NK.Spot.Presentation.MonsterPrefabController');
    const envClass=runtime.class('NK.Spot.DayNight.NKEnvGradientController');
    const prefabClass=runtime.class('NK.Spot.Monster.MonsterPrefabData');
    const graphicClass=runtime.class('NK.Spot.Presentation.SpotGraphicOptions');
    checkField(controllerClass,'_monsterList',0x38,'System.Collections.Generic.List<NK.Spot.Monster.MonsterPrefabData>');
    checkField(envClass,'_gradients',0x30,'NK.Spot.DayNight.NKEnvGlobalGradient[]');
    checkField(envClass,'_isInit',0x3c,'System.Boolean');
    checkField(graphicClass,'_envGradientController',0x38,'NK.Spot.DayNight.NKEnvGradientController');
    checkField(prefabClass,'<Id>k__BackingField',0x24,'System.Int32');
    checkField(prefabClass,'<AnimController>k__BackingField',0x28,'NK.Spot.Monster.Animation.MonsterAnimController');
    checkField(prefabClass,'<PartsData>k__BackingField',0xd8,'NK.Spot.Monster.Body.MonsterPartsPrefabData');
    if(Number(envClass.method('Init',1).relativeVirtualAddress)!==0x06e8ce80||
        Number(prefabClass.method('SetColorTint',1).relativeVirtualAddress)!==0x06369ab0)
      throw Error('Original environment/tint method identity differs');
    const env=geometryState.envGradient,graphic=geometryState.graphicOptions;
    const envEvidence=describe(env,envClass.type.name);
    const graphicEvidence=describe(graphic,graphicClass.type.name);
    result.environment={...envEvidence,graphicOptions:graphicEvidence,ready:false,gradientCount:null,gradients:[]};
    if(!envEvidence.usable||!graphicEvidence.usable){pending('original_environment_or_graphic_options_unavailable');}
    else {
      const serialized=graphic.field('_envGradientController').value;
      result.environment.serializedReferenceMatches=live(serialized)&&serialized.handle.equals(env.handle);
      const initByte=env.handle.add(0x3c).readU8();
      if(initByte!==0&&initByte!==1)throw Error('Native environment init flag is malformed');
      result.environment.originalInitFlag=initByte===1;
      const arrayRef=env.field('_gradients').value;
      if(!live(arrayRef))pending('original_environment_gradient_array_pending');
      else {
        const array=new Il2Cpp.Object(arrayRef.handle);
        if(array.class.type.name!=='NK.Spot.DayNight.NKEnvGlobalGradient[]')
          throw Error('Original environment gradient array type differs');
        const count=integer(call(array.method('get_Length',0),array));
        if(!Number.isInteger(count)||count<0||count>128)throw Error('Gradient array outside128 bound');
        result.environment.gradientCount=count;
        const get=array.method('GetValue').overload('System.Int32');
        for(let index=0;index<count;index++){
          const value=call(get,array,[intArg(index)]);
          result.environment.gradients.push({index,...describe(value,'NK.Spot.DayNight.NKEnvGlobalGradient')});
        }
        const monsters=result.environment.gradients.filter(value=>
          value.type==='NK.Spot.DayNight.NKEnvGlobalGradient_Monster'&&value.usable);
        result.environment.monsterGradientCount=monsters.length;
        result.environment.originalMonsterGradient=monsters.length===1?monsters[0]:null;
        result.environment.ready=result.environment.serializedReferenceMatches&&initByte===1&&count>0&&
          result.environment.gradients.every(value=>value.usable)&&monsters.length===1;
      }
      if(!result.environment.ready)pending('original_environment_init_or_gradient_graph_pending');
    }
    const go=geometryState.instances?.monster_controller;
    if(!live(go)){pending('original_monster_controller_gameobject_pending');return finish();}
    const controller=call(go.method('GetComponent').overload('System.Type'),go,
      [controllerClass.type.object.handle]);
    result.loadedMonsters.controller=describe(controller,controllerClass.type.name);
    result.loadedMonsters.originalGameObjectPointer=go.handle.toString();
    if(!result.loadedMonsters.controller.usable){pending('original_monster_controller_pending');return finish();}
    const list=controller.field('_monsterList').value;
    if(!live(list)){pending('original_monster_list_pending');return finish();}
    if(list.class.type.name!=='System.Collections.Generic.List<NK.Spot.Monster.MonsterPrefabData>')
      throw Error('Original monster list type differs');
    const count=boundedCount(list,'Loaded original monster',256);
    result.loadedMonsters.count=count;
    if(count===0)pending('original_monster_list_empty');
    const item=list.method('get_Item',1);
    for(let index=0;index<count;index++){
      const prefab=call(item,list,[intArg(index)]),row={index,...describe(prefab,prefabClass.type.name)};
      result.loadedMonsters.rows.push(row);
      if(!row.usable){pending('original_monster_prefab_reference_pending');continue;}
      row.prefabId=prefab.handle.add(0x24).readS32();
      row.animation=describe(prefab.field('<AnimController>k__BackingField').value,
        'NK.Spot.Monster.Animation.MonsterAnimController');
      row.partsForNativeTint=describe(prefab.field('<PartsData>k__BackingField').value,
        'NK.Spot.Monster.Body.MonsterPartsPrefabData');
      row.referencePrerequisitesReady=row.animation.usable&&row.partsForNativeTint.usable;
      if(!row.referencePrerequisitesReady)pending('original_monster_animation_or_tint_parts_pending');
    }
    result.loadedMonsters.ready=count>0&&result.loadedMonsters.rows.every(row=>row.referencePrerequisitesReady===true);
  } catch(error) {
    result.supported=false;result.error=String(error);pending('readiness_diagnostic_or_source_binding_error');
  }
  return finish();
  function finish(){
    result.ready=result.supported&&result.environment.ready&&result.loadedMonsters.ready;
    result.status=result.ready?'ready':'pending';
    if(typeof emit==='function')try{emit({status:'original_monster_color_readiness',readiness:result});}
      catch(error){result.evidenceSinkError=String(error);}
    return result;
  }
}
