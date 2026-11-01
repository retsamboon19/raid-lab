// Actual read-only intro observer with synthetic original memory; no native run.
const fs=require('fs'),vm=require('vm'),assert=require('assert');
const source=fs.readFileSync(__dirname+'/practice_probe.js','utf8');
const start=source.indexOf('        const introExpected=');
const end=source.indexOf('        // Retain a passive original OnStart',start);
assert(start>=0&&end>start);
const code=source.slice(start,end)+'\n globalThis.observeActualIntro=observeIntro;';
const binding=JSON.parse(fs.readFileSync(__dirname+'/practice-cutscene-control-binding.json','utf8'));
const receipt='eae1d9b0bbccf92750e8ba80617346d0ec9f9024ad06e7c602a7b81fa4686936';
let controls=0;
function fixture({duration=4.4,useIntro=true,loading=false,expected=binding,throwLogger=false}={}) {
  const rows=[],reads=[];
  const bytes=Buffer.alloc(4);bytes.writeFloatLE(duration);
  const pointer=(kind,offset=0)=>({add:n=>pointer(kind,offset+n),
    readFloat(){assert.equal(kind,'manager');assert.equal(offset,0xb0);reads.push('duration');return bytes.readFloatLE();},
    readByteArray(n){assert.equal(kind,'manager');assert.equal(offset,0xb0);assert.equal(n,4);reads.push('bits');return Uint8Array.from(bytes).buffer;},
    readU8(){reads.push(kind+':'+offset);if(kind==='wave'){assert.equal(offset,0x98);return useIntro?1:0;}
      assert.equal(offset,0xb5);return loading?1:0;}});
  const context={manager:{handle:pointer('manager')},waveContext:{handle:pointer('wave')},
    PRACTICE_CUTSCENE_CONTROL_SOURCE:expected,PRACTICE_CUTSCENE_CONTROL_SOURCE_SHA256:receipt,
    emit:row=>{if(throwLogger)throw Error('logger failed');rows.push(row);}};
  vm.createContext(context);vm.runInContext(code,context);
  return {observe:context.observeActualIntro,rows,reads};
}
function check(fn){fn();controls++;}
let f=fixture();f.observe('enter');f.observe('leave');
check(()=>assert.deepEqual(f.rows.map(x=>[x.boundaryPhase,x.passed,x.introDurationBitsLE]),
  [['enter',true,'cdcc8c40'],['leave',true,'cdcc8c40']]));
check(()=>assert(f.rows.every(x=>x.stateWritten===false&&x.nativeMethodsInvokedInsideObserver===false&&x.sourceReceiptSha256===receipt)));
check(()=>assert.equal(f.reads.length,8));
for(const altered of [{duration:0},{duration:4.5},{useIntro:false},{loading:true}]) {
  f=fixture(altered);
  check(()=>assert.throws(()=>f.observe('enter'),/Original intro state differs/));
  check(()=>assert.equal(f.rows[0].passed,false));
}
check(()=>assert.throws(()=>fixture({expected:null}),/expectation is absent/));
check(()=>assert.throws(()=>fixture({expected:{...binding,expectedIntroDurationFloat32BitsLE:'nothex'}}),/expectation is absent/));
check(()=>assert.throws(()=>fixture({expected:{...binding,expectedUseIntroCutScene:false}}),/expectation is absent/));
check(()=>assert.throws(()=>fixture({throwLogger:true}).observe('enter'),/logger failed/));
console.log(JSON.stringify({status:'passed',controls,scope:'Actual source intro observer, synthetic memory only; native callbacks retain outer fault containment'}));
