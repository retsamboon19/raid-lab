// Original current153 Lobby -> Battle transition. Call on Unity main, before
// SpotManagement.OnInit; retained roots live until the private process exits.
// Native UIPopupControll owns HideLoading and the loading-page flag.
function startOriginalPracticeOverlay(runtime,staticImage,pin,emit,done) {
  'use strict';
  const binding=globalThis.PRACTICE_LOADING_OVERLAY_BINDING;
  const state={status:'starting',readyShow:false,roots:[],rawBuffers:[],fault:null};
  let timer=null,scheduled=false,delivered=false;
  const call=(method,self=null,args=[])=>invokeChecked(method,self,args);
  const keep=value=>{if(value==null||value.isNull())throw Error('Original overlay reference is null');
    pin(value);state.roots.push(value);return value;};
  function fail(error){state.fault=state.fault||error;state.status='failed';if(timer!==null)clearInterval(timer);
    try{emit({status:'original_practice_overlay_failed',error:String(state.fault),nativeFrames:state.fault.nativeFrames||null});}catch(_){}
    if(!delivered){delivered=true;done(state.fault,state);}}
  function check(){if(state.fault)throw state.fault;return state.readyShow;}
  state.check=check;
  try {
    if(!binding||Process.pointerSize!==8||typeof pin!=='function'||typeof done!=='function'||
        typeof emit!=='function'||typeof onMain!=='function'||
        binding.clientSha256!=='d39896d3770888039c728a1908448c3db5efa7cdf874c90d56f46d8d566428d2')
      throw Error('Exact153 overlay source/main-thread binding required');
    const game=Process.getModuleByName('GameAssembly.dll');
    for(const fragment of binding.codeFragments){
      const actual=Array.from(new Uint8Array(game.base.add(fragment.rva).readByteArray(fragment.bytes.length/2)),
        x=>x.toString(16).padStart(2,'0')).join('');
      if(actual!==fragment.bytes)throw Error('Original overlay code differs at '+fragment.rva.toString(16));
    }
    const at=(method,spec)=>{
      if(Number(method.relativeVirtualAddress)!==spec.rva||method.isStatic!==spec.isStatic||
          method.returnType.name!==spec.returns||
          method.parameters.map(p=>p.type.name).join('|')!==spec.parameters.join('|'))
        throw Error('Original overlay method ABI differs: '+spec.name);
      return method;
    };
    const native=(owner,key)=>at(owner.method(binding.methods[key].name,binding.methods[key].parameters.length),binding.methods[key]);
    const layout=(owner,spec)=>{const f=owner.field(spec.name);
      if(f.offset!==spec.offset||f.type.name!==spec.type||f.isStatic)throw Error('Original overlay field differs: '+spec.name);
      return f;};
    const aliveMethod=Il2Cpp.domain.assembly('UnityEngine.CoreModule').image.class('UnityEngine.Object').method('op_Implicit',1);
    const live=(value,type,label)=>{keep(value);
      if(value.class.type.name!==type||call(aliveMethod,null,[value.handle]).unbox().handle.readU8()!==1)
        throw Error('Original overlay Unity reference differs: '+label);return value;};
    const text=value=>{
      if(value==null||value.isNull())throw Error('Original overlay string is null');
      // String fields are Il2Cpp.String wrappers, which have no Object.ref.
      // Pin the same managed handle through Object, retaining the original text.
      keep(new Il2Cpp.Object(value.handle));return new Il2Cpp.String(value.handle).content;
    };
    const manager=keep(call(native(staticImage.class('NK.StaticData.DataManager'),'manager')));
    const table=keep(call(native(manager,'table'),manager));
    const depart=Il2Cpp.string('Lobby'),arrive=Il2Cpp.string('Battle');
    keep(new Il2Cpp.Object(depart.handle));keep(new Il2Cpp.Object(arrive.handle));
    const zero=Memory.alloc(4);zero.writeS32(0);state.rawBuffers.push(zero);
    const find=native(table,'find');
    // The verified signature owns the actual class identity. EventId is not
    // declared in the same assembly as TransitionMethod/DataManager.
    const eventClass=find.parameters[2].type.class,arriveEventClass=find.parameters[3].type.class;
    if(eventClass.type.name!=='NK.StaticData.Categoricals.EventId'||
        !eventClass.handle.equals(arriveEventClass.handle)||
        !eventClass.isValueType||eventClass.valueTypeSize!==4)
      throw Error('Original EventId parameter class/layout differs');
    state.transitionRow=keep(call(find,table,[depart.handle,arrive.handle,zero,zero]));
    if(state.transitionRow.class.type.name!==binding.rowType||
        call(native(state.transitionRow,'rowId'),state.transitionRow).unbox().handle.readS32()!==19)
      throw Error('Original Lobby to Battle transition row differs');
    const methodClass=staticImage.class(binding.transitionMethodType);
    if(!methodClass.isValueType||methodClass.valueTypeSize!==24)throw Error('Original TransitionMethod layout differs');
    state.transitionMethod=keep(call(native(methodClass,'fromStatic'),null,[state.transitionRow.handle]));
    const value=state.transitionMethod.unbox();
    for(const spec of binding.transitionFields)layout(value,spec);
    const tip=keep(value.field('<LoadingTip>k__BackingField').value);
    if(text(value.field('<TransitionName>k__BackingField').value)!==binding.transitionName||
        value.field('<IsGauge>k__BackingField').value!==true||tip.class.type.name!==binding.tipType)
      throw Error('Original selected transition name/gauge/tip differs');
    for(const spec of binding.tipFields)layout(tip,spec);
    const rotation=tip.field('<RotationType>k__BackingField').value;
    if(tip.field('<Group>k__BackingField').value!==4||rotation.field('value__').value!==0)
      throw Error('Original selected loading tip group/rotation differs');
    state.service=live(call(native(runtime.class('NK.OverlayTransition'),'singleton')),'NK.OverlayTransition','resource singleton');
    for(const spec of binding.serviceFields)layout(state.service,spec);
    for(const spec of binding.requiredReferences)
      live(state.service.field(spec.name).value,spec.concreteType,spec.name);
    keep(state.service.field('_transitionViews').value);
    const canvas=state.service.field('_canvas').value;
    const serviceGo=keep(call(state.service.method('get_gameObject',0),state.service));
    const canvasGo=keep(call(canvas.method('get_gameObject',0),canvas));
    if(!serviceGo.handle.equals(canvasGo.handle))throw Error('Original overlay Canvas is not on service GameObject');
    state.tuple=keep(call(native(state.service,'show'),state.service,[value.handle,NULL]));
    state.task=state.tuple.unbox().field('Item1').value;
    if(state.task.type.name!=='Cysharp.Threading.Tasks.UniTask<System.Boolean>')throw Error('Original Show task type differs');
    state.awaiter=keep(call(state.task.method('GetAwaiter',0),state.task));
    state.startedAt=Date.now();state.status='showing';
    emit({status:'original_practice_overlay_show_started',transitionName:binding.transitionName,
      transitionTableId:19,loadingTipGroup:4,loadingTipRotation:0,providerNull:true,
      originalTableAndFromStaticInfoUsed:true,originalResourceSingletonUsed:true,
      serializedReferencesWritten:false,loadingFlagWritten:false,rngStateWritten:false,
      bootstrapSourceSha256:binding.bootstrapSourceSha256,cardSourceSha256:binding.cardSourceSha256});
    state.poll=()=>{
      if(state.status!=='showing')return check();
      try{
        if(Date.now()-state.startedAt>30000)throw Error('Original overlay Show exceeded bounded 30000ms');
        const a=state.awaiter.unbox();
        if(!call(a.method('get_IsCompleted',0),a).unbox().handle.readU8())return false;
        const success=call(a.method('GetResult',0),a).unbox().handle.readU8();
        if(success!==1)throw Error('Original overlay Show did not succeed');
        state.view=live(call(native(state.service,'active'),state.service),
          'NK.UI.Component.OverlayTransitionLazyController','original active selected view');
        for(const spec of binding.lazyFields)layout(state.view,spec);
        if(state.view.field('_isActive').value!==true)throw Error('Original selected overlay view is not active');
        keep(state.view.field('_view').value);
        const viewGo=keep(call(state.view.method('get_gameObject',0),state.view));
        if(text(call(viewGo.method('get_name',0),viewGo))!==binding.transitionName)
          throw Error('Original active overlay name differs');
        state.readyShow=true;state.status='ready';if(timer!==null)clearInterval(timer);
        emit({status:'original_practice_overlay_show_ready',transitionName:binding.transitionName,
          activeViewType:state.view.class.type.name,originalShowCompleted:true,
          originalHidePending:true,managerOnInitPending:true});
        if(!delivered){delivered=true;done(null,state);}return true;
      }catch(error){fail(error);return false;}
    };
    const quitting=()=>typeof probeQuitRequested!=='undefined'&&probeQuitRequested;
    timer=setInterval(()=>{if(quitting()){clearInterval(timer);return;}if(scheduled||state.status!=='showing')return;scheduled=true;
      try{
        // false means the driver's single main-work slot is busy. Retry from
        // the next interval; never deliver cleanup from this timer callback.
        if(!onMain(()=>{scheduled=false;if(quitting()){clearInterval(timer);return;}if(state.fault){fail(state.fault);return;}state.poll();}))scheduled=false;
      }catch(error){
        // Preserve a real scheduling fault, delivering it only once a main
        // callback is accepted. A permanently busy queue retains host bounds.
        scheduled=false;state.fault=state.fault||error;
      }},10);
  }catch(error){fail(error);}
  return state;
}
