// Host boundary tests only: native serializer is mocked, not reimplemented.
const assert=require('node:assert/strict'),fs=require('node:fs'),vm=require('node:vm');
let checks=0;
function check(value,label){assert.ok(value,label);checks++;}
function harness(options={}) {
  const calls=[],roots=[],receipts=[],nativeError=options.nativeError;
  const wire=Uint8Array.from([8,1,24,144,191,5,66,8,255,255,255,255,255,255,255,127]).buffer;
  let binding=null,methods={},nativeBodies={};
  const pointer=rva=>({rva,equals:other=>other?.rva===rva,
    readByteArray:length=>{
      const body=nativeBodies[rva];
      if (!body||body.byteLength!==length) throw Error('unbound native body read');
      return options.corruptBody?new Uint8Array(body.byteLength).buffer:body;
    }});
  const klass={type:{name:'NK.Network.Packet.Lobby.NetAntiCheatBattleData'},
    image:{assembly:{name:'NK.Network.Packet.Runtime.dll'}},
    method:name=>methods[name]};
  const packet={class:klass,handle:{kind:'original_packet'},isNull:()=>false,
    field:()=>{throw Error('manual packet reconstruction forbidden');}};
  const originalArray={class:{type:{name:options.arrayType??'System.Byte[]'}},
    handle:{kind:'original_wire_array'},isNull:()=>false};
  const context=vm.createContext({console,ArrayBuffer,Uint8Array,
    Process:{getModuleByName:name=>{assert.equal(name,'GameAssembly.dll');return {base:{add:pointer}};}},
    Il2Cpp:{domain:{assembly:name=>{assert.equal(name,'Google.Protobuf');return {image:{class:()=>({method:name=>methods[name]})}};}},
      Array:function(handle){
        assert.equal(handle,originalArray.handle);
        this.elementType={name:options.elementType??'System.Byte'};
        this.elementSize=options.elementSize??1;this.length=options.arrayLength??wire.byteLength;
        this.elements={handle:{readByteArray:length=>{
          assert.equal(length,this.length);return options.shortRead?wire.slice(1):wire;
        }}};
      }}});
  if (!options.noChecksum) context.Checksum={compute:(algorithm,bytes)=>{
    assert.equal(algorithm,'sha256');assert.equal(bytes,wire);return options.badDigest?'bad':'b'.repeat(64);
  }};
  vm.runInContext(fs.readFileSync(__dirname+'/practice_packet_export.js','utf8'),context);
  binding=vm.runInContext('NATIVE153_PRACTICE_PACKET_EXPORT',context);
  for (const spec of binding.methods) {
    const m={name:spec.name,relativeVirtualAddress:spec.rva,virtualAddress:pointer(spec.rva),
      returnType:{name:spec.returns},isStatic:spec.isStatic,
      parameters:spec.parameters.map(name=>({type:{name}}))};
    methods[spec.name]=m;
    for(const fragment of spec.fragments)
      nativeBodies[fragment.rva]=Uint8Array.from(Buffer.from(fragment.hex,'hex')).buffer;
  }
  if (options.badSignature) methods.ToByteArray.returnType.name='System.String';
  if (options.badRva) methods.ToByteArray.relativeVirtualAddress++;
  context.invokeChecked=(method,self,args=[])=>{
    calls.push(method.name);
    if (method.name==='CalculateSize') {
      assert.equal(self,packet);
      return {isNull:()=>false,unbox:()=>({handle:{readS32:()=>options.expectedLength??wire.byteLength}})};
    }
    assert.equal(method.name,'ToByteArray');assert.equal(self,null);assert.equal(args[0],packet.handle);
    if(nativeError)throw nativeError;
    return options.nullArray?null:originalArray;
  };
  return {calls,roots,receipts,packet,wire,binding,
    run:()=>context.exportOriginalPracticePacket(options.nullPacket?null:packet,
      value=>{roots.push(value);return value;},row=>receipts.push(row))};
}
let h=harness(),result=h.run();
check(result.bytes===h.wire,'returned ArrayBuffer is the unchanged original native byte readback');
check(result.source.format==='protobuf_wire'&&result.source.byteLength===h.wire.byteLength,
  'parent receives explicit original wire format and length');
check(result.source.sha256==='b'.repeat(64)&&result.source.checksumSource==='Frida.Checksum.compute',
  'optional existing Frida digest covers the exact exported buffer');
check(h.calls.join('|')==='CalculateSize|ToByteArray','only original size and wire serializer invoked');
check(h.roots.length===2&&h.roots[0]===h.packet,'original packet and output array retained');
check(result.source.javascriptNumericConversion===false&&!result.source.fullAccuracyVerified&&
  result.source.diagnosticJsonUsed===false,'wire export does not claim JSON fallback or parity');
check(h.receipts[0].byteLength===h.wire.byteLength&&h.receipts[0].sha256===result.source.sha256,
  'metadata-only export receipt binds original length/digest');
h=harness({noChecksum:true});result=h.run();
check(result.source.sha256===null&&result.source.checksumSource==='unavailable_in_runtime',
  'missing optional Frida checksum does not initialize game cryptography');
for (const options of [{nullPacket:true},{badSignature:true},{badRva:true},{corruptBody:true}]) {
  h=harness(options);assert.throws(h.run);checks++;
  check(h.calls.length===0,'type/signature/address/body mismatch rejects before native serialization');
}
for (const expectedLength of [0,-1,16777217]) {
  h=harness({expectedLength});assert.throws(h.run,/CalculateSize.*bound/);checks++;
  check(!h.calls.includes('ToByteArray'),'oversized/empty original size never allocates serialized array');
}
for (const options of [{nullArray:true},{arrayType:'System.Int32[]'},{elementType:'System.SByte'},
  {elementSize:8},{arrayLength:1},{arrayLength:16777217},{shortRead:true},{badDigest:true}]) {
  h=harness(options);assert.throws(h.run);checks++;
  check(h.receipts.length===0,'invalid native output never emits a successful export receipt');
}
const nativeError=Object.assign(Error('original wire writer failed'),{nativeFrames:['0x3af879f']});
h=harness({nativeError});assert.throws(h.run,error=>error===nativeError);checks++;
check(nativeError.nativeFrames[0]==='0x3af879f','original native serialization exception/frames preserved');
console.log(checks+' packet wire contracts pass (mock native boundary; real serialization unverified).');
