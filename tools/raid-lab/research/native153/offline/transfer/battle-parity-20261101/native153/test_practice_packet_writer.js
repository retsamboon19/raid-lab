'use strict';
// Execute the actual probe complete() branch with synthetic closure/File values.
// No native process, native packet construction or real filesystem output.
const assert=require('node:assert');
const fs=require('node:fs');
const path=require('node:path');
const vm=require('node:vm');
const source=fs.readFileSync(path.join(__dirname,'practice_probe.js'),'utf8');
const startMarker='  function complete(row={}) {',endMarker='\n  function fail(error) {';
assert.equal(source.split(startMarker).length,2,'one actual complete function');
assert.equal(source.split(endMarker).length,2,'one following fail function');
const start=source.indexOf(startMarker),end=source.indexOf(endMarker,start);
assert(end>start);
const actualComplete=source.slice(start,end);
function fixture({filename='practice14-original-result.pb',exported,exportError,writeError}={}){
  const buffer=Uint8Array.from([0x0a,0x0d,0x00,0xff,0x80,0x01,0x0a,0x00]).buffer;
  const originalSource={format:'protobuf_wire',byteLength:buffer.byteLength,
    rawBytesUnchanged:true,javascriptNumericConversion:false};
  const output=exported===undefined?{bytes:buffer,source:originalSource}:exported;
  const events=[],files=[];let exportCalls=0,doneCalls=0;
  const packet={originalPinnedPacket:true};
  const context={ArrayBuffer,Uint8Array,PRACTICE_RESULT_FILENAME:filename,
    finished:false,poll:null,capture:{getOriginalPacket:()=>packet},pin:value=>value,
    emit:row=>events.push(row),done:()=>doneCalls++,stage:'synthetic_writer_branch',retained:[],
    dpReady:true,colorReadiness:null,colorReadinessSamples:0,autoPreferences:null,loadingOverlay:null,
    autoContentsAtPlaying:null,callbacks:null,monsterBoundary:null,audioBoundary:null,
    fxBoundary:null,skillPoolObserver:null,skeletonSourceObserver:null,rngStateVerifier:null,
    exportOriginalPracticePacket(value){
      assert.strictEqual(value,packet);exportCalls++;
      if(exportError)throw exportError;
      return output;
    },
    File:function(name,mode){
      const file={name,mode,writes:[],flushes:0,closes:0};files.push(file);
      this.write=value=>{file.writes.push(value);if(writeError)throw writeError;
        file.originalBytes=Array.from(new Uint8Array(value));};
      this.flush=()=>file.flushes++;
      this.close=()=>file.closes++;
    }
  };
  vm.createContext(context);vm.runInContext(actualComplete,context);
  return {run:row=>context.complete(row),events,files,buffer,originalSource,
    counters:()=>({exportCalls,doneCalls})};
}
let passed=0;
function test(name,run){run();passed++;console.log('PASS '+name);}

test('binary mode receives exact original ArrayBuffer including LF CR NUL',()=>{
  const f=fixture();f.run({completeBattle:true});
  assert.equal(f.files.length,1);
  assert.equal(f.files[0].name,'practice14-original-result.pb');
  assert.equal(f.files[0].mode,'wb');
  assert.strictEqual(f.files[0].writes[0],f.buffer);
  assert.deepEqual(f.files[0].originalBytes,[0x0a,0x0d,0x00,0xff,0x80,0x01,0x0a,0x00]);
  assert.equal(f.files[0].flushes,1);assert.equal(f.files[0].closes,1);
  assert.equal(f.events[0].originalPacketExported,true);
  assert.strictEqual(f.events[0].originalPacketSource,f.originalSource);
  assert.equal(f.events[0].originalPacketFile,'practice14-original-result.pb');
  assert.equal(f.counters().doneCalls,1);
});

test('old JSON filename is rejected before export or output creation',()=>{
  const f=fixture({filename:'practice14-original-result.json'});f.run({completeBattle:true});
  assert.equal(f.files.length,0);assert.equal(f.counters().exportCalls,0);
  assert.equal(f.events[0].status,'original_practice_packet_export_failed');
  assert.equal(f.events[0].originalPacketExported,false);
});

test('old JSON exporter schema and non-ArrayBuffer bytes fail explicitly',()=>{
  for(const exported of [{jsonText:'{}',source:{format:'diagnostic_json'}},
    {bytes:Uint8Array.from([10,13,0]),source:{format:'protobuf_wire'}}]){
    const f=fixture({exported});f.run({completeBattle:true});
    assert.equal(f.files.length,0);
    assert.equal(f.events[0].originalPacketExported,false);
    assert.match(f.events[0].exportError,/binary protobuf export contract differs/);
  }
});

test('native export failure preserves original nativeFrames and is not successful export',()=>{
  const error=new Error('synthetic original serializer failure');error.nativeFrames=['original-native-frame'];
  const f=fixture({exportError:error});f.run({completeBattle:true});
  assert.equal(f.files.length,0);
  assert.equal(f.events[0].originalPacketExported,false);
  assert.strictEqual(f.events[0].nativeFrames,error.nativeFrames);
  assert.match(f.events[0].exportError,/original serializer failure/);
});

test('write failure closes file and cannot advertise successful export',()=>{
  const error=new Error('synthetic binary write failure');error.nativeFrames=['original-io-frame'];
  const f=fixture({writeError:error});f.run({completeBattle:true});
  assert.equal(f.files[0].closes,1);assert.equal(f.files[0].flushes,0);
  assert.equal(f.events[0].originalPacketExported,false);
  assert.strictEqual(f.events[0].nativeFrames,error.nativeFrames);
});

test('incomplete battle skips exporter and repeated completion cannot rewrite file',()=>{
  const incomplete=fixture();incomplete.run({completeBattle:false});
  assert.equal(incomplete.counters().exportCalls,0);assert.equal(incomplete.files.length,0);
  const completed=fixture();completed.run({completeBattle:true});completed.run({completeBattle:true});
  assert.equal(completed.files.length,1);assert.equal(completed.counters().exportCalls,1);
  assert.equal(completed.counters().doneCalls,1);
});

console.log(passed+' actual writer-branch contracts passed; no native execution or real output writes.');
