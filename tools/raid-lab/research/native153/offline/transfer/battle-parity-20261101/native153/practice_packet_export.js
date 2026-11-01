'use strict';
// Original current153 protobuf wire serialization. No diagnostic reflection,
// packet field reconstruction, damage calculation or JavaScript Int64 coercion.
const NATIVE153_PRACTICE_PACKET_EXPORT=Object.freeze({
  "clientSha256": "d39896d3770888039c728a1908448c3db5efa7cdf874c90d56f46d8d566428d2",
  "metadataSha256": "7feaa22d1cd9bb83d506d688d44f1d5137d017083eeb87c1fab81c11969f61e5",
  "sourceBindingSha256": "c87289e75a10a72cf9c67d8bb216fc8e96de53956856c0c19869470fc3322e92",
  "auditSha256": "cb4ca706236346ccc6a093ba239b3ea70cad32081803546bb23161a931b75f70",
  "packetClass": "NK.Network.Packet.Lobby.NetAntiCheatBattleData",
  "packetAssembly": "NK.Network.Packet.Runtime",
  "maxByteLength": 16777216,
  "methods": [
    {
      "key": "serializer",
      "owner": "Google.Protobuf.MessageExtensions",
      "name": "ToByteArray",
      "rva": 61834784,
      "returns": "System.Byte[]",
      "parameters": [
        "Google.Protobuf.IMessage"
      ],
      "isStatic": true,
      "sourceReport": "practice-packet-serialization-source.json",
      "sourceReportSha256": "c563494b794eb956f128e95de4fc36436d6af62887da38c64882fa9110599efe",
      "fragments": [
        {
          "rva": 61834784,
          "hex": "40554883ec20803df491e20700488be97543488d0df79f3b07e8428ad4fc488d0dcb103d07e8368ad4fc488d0d1fde5707e82a8ad4fc488d0d53124d07e81e8ad4fc488d0d3f714007e8128ad4fcc605ac91e207014c8b0534124d07488bcd488b1522714007",
          "sha256": "d8e7105bbc4e7d18491859734063a35bfa5a55afa442b43b78b51c649ddf4d2c"
        },
        {
          "rva": 61834886,
          "hex": "488974243848897c2440e85b7490fd4885ed0f8438010000488b15cbdd5707b9020000004c8bc5e8beba50fc488b0d779f3b078bd0e80083d4fc488b0d49103d07488bf0e88168d4fc488bf84885c00f84fb0000004885f60f84f2000000803dd790e2070048895c24308b5e18751f488d0dc4fb4c07e87f89d4fc488d0de0e04e07e87389d4fcc605ae90e2070133d2488bcfe8e28dddfc488d4f3848c747380000000033d2e81f82d4fc4c8b0588fb4c07488bce488b15a6e04e07e8a97390fd488d4f1848894718488bd0e8f981d4fc33d2c7472400000000488d4f28895f2048c7472800000000e8dc81d4fc488d4f3048897f30488bd7e8cc81d4fcc6471001b901000000488b15dcdc57074c8bcf4c8bc5e811fd50fc488b47304885c074074883783800752d48837f280075268b47203b4724756f488b5c2430488bc6488b742438488b7c24404883c4205dc3",
          "sha256": "f2da5e0e84bac88c105eef3b022a43c7b8cb3b60a276952c5a8f6990cee0d510"
        },
        {
          "rva": 61835222,
          "hex": "e8458ad4fccc",
          "sha256": "71e53b067c1bac1da6343d0882eab20c160e0911f0cad1ae83fc171eb739b672"
        },
        {
          "rva": 61835228,
          "hex": "488d0d5d0a3d07e8b888d4fc488bc8e86067d4fc488bc8488bd8e815a550fc488d0d6e7c5507e89988d4fc488bd04533c0488bcbe88b015d00488d0d94475607e87f88d4fc488bd0488bcbe8b489d4fccc488d0d0c0a3d07e86788d4fc488bc8e80f67d4fc488bc8488bd8e8c4a450fc488d0dcd554e07e84888d4fc488bd04533c0488bcbe83a015d00488d0d9b435607e82e88d4fc488bd0488bcbe86389d4fccc",
          "sha256": "d7cbcad7cc86398db7431b697f041810cb18e7334c8b395f3fdf541d80961d36"
        }
      ]
    },
    {
      "key": "size",
      "owner": "NK.Network.Packet.Lobby.NetAntiCheatBattleData",
      "name": "CalculateSize",
      "rva": 71220944,
      "returns": "System.Int32",
      "parameters": [],
      "isStatic": false,
      "sourceReport": "practice13-original-binary-packet-source.json",
      "sourceReportSha256": "4784bb56588e2bf19d9e7e5191af66f2f075ecee5f28a9a46bb9ced2f74c0546",
      "fragments": [
        {
          "rva": 71220944,
          "hex": "48895c24084889742410574883ec20803d2be0530700488bd97537488d0d1ed8ad06e8895145fc488d0d2ac6cb06e87d5145fc488d0d86c8ba06e8715145fc488d0d921cbb06e8655145fcc605efdf53070133ff397b187424488b0de0d7ad068b7b1883b9e0000000007505e82fb03cfc33d28bcfe866af6fff8d7801837b1c007425488b0db6d7ad068b731c83b9e0000000007505e805b03cfc33d28bcee83caf6fffffc003f8837b20007425488b0d8bd7ad068b732083b9e0000000007505e8daaf3cfc33d28bcee811af6fffffc003f8837b24007425488b0d60d7ad068b732483b9e0000000007505e8afaf3cfc33d28bcee8e6ae6fffffc003f8837b28007425488b0d35d7ad068b732883b9e0000000007505e884af3cfc33d28bcee8bbae6fffffc003f8837b2c007425488b0d0ad7ad068b732c83b9e0000000007505e859af3cfc33d28bcee890ae6fffffc003f8837b30007425488b0ddfd6ad068b733083b9e0000000007505e82eaf3cfc33d28bcee865ae6fffffc003f8488b05d2c4cb06488b733883b8e000000000750f488bc8e805af3cfc488b05b6c4cb06488b80b80000004885f60f84480200004c8b0507c7ba06488bce488b5008e80b197dfe488b158cc4cb06488b4b408d34074c8b82b8000000498b50104885c90f84130200004c8b05ea1abb06e8dd187dfe8d0c30807b48008d41020f44c1807b49008d78020f44f8488b43504885c00f84e3010000837810007426488b0d1cd6ad06488bf083b9e0000000007505e86bae3cfc33d2488bcee851b16fffffc003f8488b43584885c00f84aa010000837810007426488b0de3d5ad06488bf083b9e0000000007505e832ae3cfc33d2488bcee818b16fffffc003f8488b43604885c00f8471010000837810007426488b0daad5ad06488bf083b9e0000000007505e8f9ad3cfc33d2488bcee8dfb06fffffc003f8837b68007426488b0d7ed5ad068b736883b9e0000000007505e8cdad3cfc33d28bcee804ad6fff83c00203f8488b43704885c00f840c010000837810007427488b0d45d5ad06488bf083b9e0000000007505e894ad3cfc33d2488bcee87ab06fff83c00203f8488b43784885c00f84d2000000837810007427488b0d0bd5ad06488bf083b9e0000000007505e85aad3cfc33d2488bcee840b06fff83c00203f8488b83800000004885c00f8495000000837810007427488b0dced4ad06488bf083b9e0000000007505e81dad3cfc33d2488bcee803b06fff83c00203f8488b8b880000004885c9745c33d2e8eba06fff85c0742b488b0d90d4ad06488bb38800000083b9e0000000007505e8dbac3cfc33d2488bcee801ab6fff83c00203f848837b1000740d488b4b1033d2e8ba3971ff03f8488b5c24308bc7488b7424384883c4205fc3e8514f45fccc",
          "sha256": "367f6ec6032f48f18ca1c98b6a14390a3a5c745c760602055ee866853413d9fa"
        }
      ]
    },
    {
      "key": "write",
      "owner": "NK.Network.Packet.Lobby.NetAntiCheatBattleData",
      "name": "WriteTo",
      "rva": 61755984,
      "returns": "System.Void",
      "parameters": [
        "Google.Protobuf.CodedOutputStream"
      ],
      "isStatic": false,
      "sourceReport": "practice13-original-binary-packet-source.json",
      "sourceReportSha256": "4784bb56588e2bf19d9e7e5191af66f2f075ecee5f28a9a46bb9ced2f74c0546",
      "fragments": [
        {
          "rva": 61755984,
          "hex": "4883ec28488bc24885d27412488bd14533c0488bc84883c428e952230000e8adbfd5fccc",
          "sha256": "6f672f4b3cbab6bbf8f824599d9c95b00e318e636664b9b1dcf98c8c60a8a251"
        }
      ]
    },
    {
      "key": "bufferWrite",
      "owner": "NK.Network.Packet.Lobby.NetAntiCheatBattleData",
      "name": "pb::Google.Protobuf.IBufferMessage.InternalWriteTo",
      "rva": 71226896,
      "returns": "System.Void",
      "parameters": [
        "Google.Protobuf.WriteContext&"
      ],
      "isStatic": false,
      "sourceReport": "practice13-original-write-context-source.json",
      "sourceReportSha256": "f8c2b114816c88cdb9ed05245d5b1631caacd8e5d298552078a1fb08ff73c55d",
      "fragments": [
        {
          "rva": 71226896,
          "hex": "48895c24084889742410574883ec20803deac8530700488bfa488bd9752b488d0df3aecb06e8463a45fc488d0d47bcba06e83a3a45fc488d0d5310bb06e82e3a45fcc605b7c8530701837b1800741b4533c0b208488bcfe8746971ff8b53184533c0488bcfe8d66471ff837b1c00741b4533c0b218488bcfe8536971ff8b531c4533c0488bcfe8b56471ff837b2000741b4533c0b220488bcfe8326971ff8b53204533c0488bcfe8946471ff837b2400741b4533c0b228488bcfe8116971ff8b53244533c0488bcfe8736471ff837b2800741b4533c0b230488bcfe8f06871ff8b53284533c0488bcfe8526471ff837b2c00741b4533c0b238488bcfe8cf6871ff8b532c4533c0488bcfe8316471ff837b3000741b4533c0b240488bcfe8ae6871ff8b53304533c0488bcfe8106471ff4c8b05e1adcb06488b73384183b8e000000000750f498bc8e813983cfc4c8b05c4adcb064885f60f843b0200004d8b80b8000000488bd74c8b0d0abbba06488bce4d8b4008e8c64f7dfe488b4b404885c90f8411020000488b058aadcb06488bd74c8b0df80ebb064c8b80b80000004d8b4010e8984f7dfe807b4800741c4533c0b258488bcfe8156871ff0fb653484533c0488bcfe8265d71ff807b4900741c4533c0b260488bcfe8f36771ff0fb653494533c0488bcfe8045d71ff488b43504885c00f849f01000083781000741c4533c0b26a488bcfe8c46771ff488b53504533c0488bcfe8356971ff488b43584885c00f847001000083781000741c4533c0b272488bcfe8956771ff488b53584533c0488bcfe8066971ff488b43604885c00f844101000083781000741c4533c0b27a488bcfe8666771ff488b53604533c0488bcfe8d76871ff837b6800741e4533c941b001b280488bcfe8416671ff8b53684533c0488bcfe8a36271ff488b43704885c00f84ee00000083781000741f4533c941b001b29a488bcfe8106671ff488b53704533c0488bcfe8816871ff488b43784885c00f84bc00000083781000741f4533c941b001b2a2488bcfe8de6571ff488b53784533c0488bcfe84f6871ff488b83800000004885c00f84870000008378100074224533c941b001b2aa488bcfe8a96571ff488b93800000004533c0488bcfe8176871ff488b8b880000004885c9745333d2e8048a6fff85c074224533c941b001b2b2488bcfe8706571ff488b93880000004533c0488bcfe85e5c71ff48837b1000740f488b4b104533c0488bd7e8f83771ff488b5c2430488b7424384883c4205fc3e8733845fccc",
          "sha256": "c0e77f5bbbb116a2a553f35c4b4e4659a515d2a019c0ac801d9cab1fff862ea5"
        }
      ]
    }
  ]
});

function exportOriginalPracticePacket(packet,pin,emit) {
  const binding=NATIVE153_PRACTICE_PACKET_EXPORT;
  if (typeof pin!=='function'||typeof emit!=='function'||typeof invokeChecked!=='function')
    throw Error('Original practice packet export needs native invocation, pin and receipt helpers');
  if (packet==null||packet.isNull()||packet.class.type.name!==binding.packetClass ||
      packet.class.image.assembly.name.replace(/\.dll$/i,'')!==binding.packetAssembly)
    throw Error('Original practice packet export requires the retained original typed DTO');
  const game=Process.getModuleByName('GameAssembly.dll');
  const sameSignature=(method,spec)=>Number(method.relativeVirtualAddress)===spec.rva &&
    method.virtualAddress.equals(game.base.add(spec.rva)) && method.returnType.name===spec.returns &&
    method.isStatic===spec.isStatic && method.parameters.length===spec.parameters.length &&
    method.parameters.every((parameter,index)=>parameter.type.name===spec.parameters[index]);
  const methods={};
  for (const spec of binding.methods) {
    const klass=spec.owner===binding.packetClass?packet.class:
      Il2Cpp.domain.assembly('Google.Protobuf').image.class(spec.owner);
    const method=klass.method(spec.name,spec.parameters.length);
    if (!sameSignature(method,spec))
      throw Error('Original protobuf wire signature/address changed: '+spec.name);
    for (const fragment of spec.fragments) {
      const actual=Array.from(new Uint8Array(game.base.add(fragment.rva)
        .readByteArray(fragment.hex.length/2)),byte=>byte.toString(16).padStart(2,'0')).join('');
      if (actual!==fragment.hex)
        throw Error('Original protobuf wire native body changed: '+spec.name);
    }
    methods[spec.key]=method;
  }
  const retainedPacket=pin(packet);
  const sizeBox=invokeChecked(methods.size,retainedPacket);
  if (sizeBox==null||sizeBox.isNull()) throw Error('Original protobuf CalculateSize returned null');
  const expectedLength=sizeBox.unbox().handle.readS32();
  if (!Number.isSafeInteger(expectedLength)||expectedLength<1||expectedLength>binding.maxByteLength)
    throw Error('Original protobuf CalculateSize is outside the byte export bound');
  // Original native ToByteArray owns all protobuf traversal/encoding and calls
  // generated size/write methods itself. No descriptor or field fallback.
  const originalArray=invokeChecked(methods.serializer,null,[retainedPacket.handle]);
  if (originalArray==null||originalArray.isNull()||originalArray.class.type.name!=='System.Byte[]')
    throw Error('Original protobuf ToByteArray returned no System.Byte[]');
  const retainedArray=pin(originalArray),array=new Il2Cpp.Array(retainedArray.handle);
  if (array.elementType.name!=='System.Byte'||array.elementSize!==1)
    throw Error('Original protobuf byte array element ABI differs');
  const byteLength=Number(array.length);
  if (!Number.isSafeInteger(byteLength)||byteLength<1||byteLength>binding.maxByteLength ||
      byteLength!==expectedLength)
    throw Error('Original protobuf byte array length differs from CalculateSize/bound');
  // The frozen bridge discovers the typed array elements accessor from a native
  // char[]; do not introduce guessed array/header offsets or element rewrites.
  const bytes=array.elements.handle.readByteArray(byteLength);
  if (!(bytes instanceof ArrayBuffer)||bytes.byteLength!==byteLength)
    throw Error('Original protobuf raw byte readback was incomplete');
  let sha256=null;
  if (typeof Checksum!=='undefined'&&typeof Checksum.compute==='function') {
    sha256=Checksum.compute('sha256',bytes);
    if (typeof sha256!=='string'||!/^[a-f0-9]{64}$/.test(sha256))
      throw Error('Frida original byte buffer SHA256 receipt is invalid');
  }
  const source={format:'protobuf_wire',kind:'original_MessageExtensions_ToByteArray',
    packetClass:binding.packetClass,boundClientSha256:binding.clientSha256,
    metadataSha256:binding.metadataSha256,sourceBindingSha256:binding.sourceBindingSha256,
    auditSha256:binding.auditSha256,originalSerializerRva:'0x03AF8620',
    fullNativeEntryBodiesMatched:true,originalCalculateSize:expectedLength,byteLength,
    sha256,checksumSource:sha256===null?'unavailable_in_runtime':'Frida.Checksum.compute',
    originalPacketAndByteArrayRetained:true,rawBytesUnchanged:true,
    javascriptNumericConversion:false,scoreCalculated:false,
    diagnosticJsonUsed:false,descriptorFabricated:false,fullAccuracyVerified:false};
  emit({status:'original_practice_packet_exported',byteLength,sha256,source});
  return {bytes,source};
}
