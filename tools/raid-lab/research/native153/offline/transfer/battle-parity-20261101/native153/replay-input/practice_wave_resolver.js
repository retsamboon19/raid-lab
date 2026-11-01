// Original asynchronous group loader, polled on the private Unity main thread.
// No new clock, worker-thread await, guessed group, or synchronous warning fallback.
function createCapturedPracticeWaveResolver(staticImage, pin, emit) {
  'use strict';
  const game=Process.getModuleByName('GameAssembly.dll'),roots=[],rawBuffers=[],cache=new Map();let pending=null;
  const keep=obj=>{if(obj==null||obj.isNull())throw Error('Original wave loader reference missing');pin(obj);roots.push(obj);return obj;};
  const call=(method,self=null,args=[])=>invokeChecked(method,self,args);
  const at=(method,rva)=>{if(!method.virtualAddress.equals(game.base.add(rva)))throw Error('Original wave ABI mismatch '+method.name);return method;};
  const arg=id=>{if(!Number.isSafeInteger(id)||id<=0)throw Error('Exact positive wave ID required');const p=Memory.alloc(4);p.writeS32(id);rawBuffers.push(p);return p;};
  const i32=(method,self)=>keep(call(method,self)).unbox().handle.readS32();
  const stringLen=new NativeFunction(game.getExportByName('il2cpp_string_length'),'int',['pointer']);
  const stringChars=new NativeFunction(game.getExportByName('il2cpp_string_chars'),'pointer',['pointer']);
  const manager=keep(call(at(staticImage.class('NK.StaticData.DataManager').method('get_Instance',0),0x04ebd140)));
  const group=keep(call(at(manager.method('get_WaveDataTable',0),0x04ebe7c0),manager));
  const dictionary=keep(call(at(manager.method('get_WaveDataGroupDictTable',0),0x04ebe7b0),manager));
  const groupIdFor=at(dictionary.method('FindById').overload('System.Int32'),0x0517cc50);
  const findAsync=at(group.method('FindByIdAsync',1),0x0517ffb0);
  const getLeaf=at(group.method('GetByGroupId',1),0x05180500);
  function begin(id) {
    if(pending)throw Error('One original wave load at a time');
    if(cache.has(id))return {ready:true,cached:true};
    const nativeGroupId=keep(call(groupIdFor,dictionary,[arg(id)]));
    const groupId=stringChars(nativeGroupId.handle).readUtf16String(stringLen(nativeGroupId.handle));
    if(!groupId)throw Error('Original wave group dictionary returned empty group');
    const task=keep(call(findAsync,group,[arg(id)]));
    const awaiter=keep(call(task.unbox().method('GetAwaiter',0),task.unbox()));
    pending={id,nativeGroupId,groupId,task,awaiter};
    emit({status:'original_practice_wave_group_load_started',waveId:id,groupId,
      groupDictionaryFindRva:0x0517cc50,asyncGroupFindRva:0x0517ffb0});
    return {ready:false,groupId};
  }
  function poll() {
    if(!pending)return {ready:cache.size>0,pending:false};
    const awaiter=pending.awaiter.unbox();
    const done=keep(call(awaiter.method('get_IsCompleted',0),awaiter)).unbox().handle.readU8()!==0;
    if(!done)return {ready:false,pending:true,groupId:pending.groupId};
    const groupResult=keep(call(awaiter.method('GetResult',0),awaiter));
    const leaf=keep(call(getLeaf,group,[pending.nativeGroupId.handle]));
    const leafFind=at(leaf.method('FindById').overload('System.Int32'),0x05180c90);
    const wave=keep(call(leafFind,leaf,[arg(pending.id)]));
    if(!wave.handle.equals(groupResult.handle)||wave.class.type.name!=='StaticData.StaticDataLayer.StaticInfo.WaveDataStaticInfo'||
        i32(at(wave.method('get_TableId',0),0x04bc4340),wave)!==pending.id)
      throw Error('Original async group/leaf wave identity mismatch');
    const receipt={kind:'original_static_table_lookup',methodRva:0x05180c90,
      asyncGroupFindRva:0x0517ffb0,groupId:pending.groupId,waveId:pending.id,
      // This identifies the exact metadata binding, not a fabricated runtime
      // receipt hash. The host freezes all emitted runtime evidence separately.
      sourceMetadataSha256:'b227ccdc5a0cf49cce4262d36470d1c710a2ff8c8fc4b42d552c1f2d26b4080d',
      receiptSha256:'b227ccdc5a0cf49cce4262d36470d1c710a2ff8c8fc4b42d552c1f2d26b4080d'};
    cache.set(pending.id,{value:wave,receipt});
    emit({status:'original_practice_wave_group_load_ready',...receipt,groupAndLeafObjectIdentical:true});
    pending=null;return {ready:true,pending:false};
  }
  function resolve(id) {
    if(!cache.has(id))throw Error('Original asynchronous wave group has not completed; call begin/poll on main first');
    return cache.get(id);
  }
  return {begin,poll,resolve,roots,rawBuffers};
}
