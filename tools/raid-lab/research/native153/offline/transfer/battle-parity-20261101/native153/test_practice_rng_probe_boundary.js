// Execute actual probe observer/check/Playing branches with synthetic closures only.
const fs=require('fs'),path=require('path'),vm=require('vm'),assert=require('assert');
const source=fs.readFileSync(path.join(__dirname,'practice_probe.js'),'utf8');
const take=(start,end)=>{const a=source.indexOf(start),b=source.indexOf(end,a);assert(a>=0&&b>a);return source.slice(a,b);};
const hook=take('        listeners.push(Interceptor.attach(onStart.virtualAddress,','\n        stage=\'original_geometry_initialization\';');
const object=hook.slice(hook.indexOf(',')+1,hook.lastIndexOf('));'));
const faultFunction=take('  function checkFault() {','\n  try {\n    const runtime=');
const readyFunction=take('            function observeReady(phase) {','\n            ticks=startOriginalPracticeTicks');
let assertions=0;
function check(fn){fn();assertions++;}
function fixture({latchedFault=false,emitThrows=false,introThrowPhase=null,overlayFault=false}={}) {
  const calls=[],events=[],seen={enter:false,leave:false};let preferenceCalls=0,fieldReads=0;
  const managerHandle={equals:other=>other===managerHandle};
  const rng={observe(phase){seen[phase]=true;calls.push(phase);return {passed:!latchedFault};},
    check(){if(latchedFault)throw Error('Synthetic full RNG mismatch');},
    assertComplete(){calls.push('assertComplete');this.check();if(!seen.enter||!seen.leave)throw Error('Both original RNG boundaries required');}};
  const random={field:name=>({value:name==='<DrawCount>k__BackingField'?'1':555063220})};
  const context={rngStateVerifier:rng,observeIntro:phase=>{calls.push('intro_'+phase);if(phase===introThrowPhase)throw Error('Synthetic intro mismatch');},callbacks:null,monsterBoundary:null,fxBoundary:null,skeletonSourceObserver:null,
    loadingOverlay:{check(){if(overlayFault)throw Error('Synthetic original overlay failure');}},
    firstAsyncFault:null,originalAutoControlsVerified:false,originalRngStateVerified:false,
    manager:{handle:managerHandle,field:name=>{fieldReads++;return {value:name==='<SpotRandomSeed>k__BackingField'?555063220:0};}},
    emit:row=>{if(emitThrows)throw Error('Synthetic diagnostic sink');events.push(row);},
    autoPreferences:{readNativeContentsOpen(){preferenceCalls++;return {nativeContentsOpen:true};}},
    autoContentsAtPlaying:null,runtime:{class:()=>({field:()=>({value:random})})},pin:value=>value,
    modeInput:{randomSeed:555063220},team:{method:name=>name},
    call:()=>({unbox:()=>({handle:{readU8:()=>1}})}),geometry:{},
  };
  vm.createContext(context);vm.runInContext('observer='+object+';\n'+faultFunction+'\n'+readyFunction,context);
  return {context,calls,events,seen,get fieldReads(){return fieldReads;},get preferenceCalls(){return preferenceCalls;},
    enter(matches=true){const invocation={};context.observer.onEnter.call(invocation,[{equals:()=>matches}]);return invocation;},
    leave(invocation){context.observer.onLeave.call(invocation);},
    ready(){context.observeReady({lifecycle:{state:6},tick:123});}};
}
let f=fixture(),inv=f.enter();f.leave(inv);f.ready();
check(()=>assert.deepEqual(f.calls,['intro_enter','enter','intro_leave','leave','assertComplete']));
check(()=>assert.equal(f.context.originalRngStateVerified,true));
check(()=>assert.equal(f.context.originalAutoControlsVerified,true));
check(()=>assert.equal(f.preferenceCalls,1));
check(()=>assert.equal(f.events.find(row=>row.status==='original_practice_rng_readback').fullSharedRngStateVerified,true));
f=fixture();inv=f.enter(false);f.leave(inv);
check(()=>assert.equal(f.calls.length,0));
check(()=>assert.equal(f.fieldReads,0));
check(()=>assert.throws(()=>f.ready(),/Both original RNG boundaries/));
check(()=>assert.equal(f.preferenceCalls,0));
check(()=>assert.equal(f.context.originalRngStateVerified,false));
f=fixture();f.enter();
check(()=>assert.throws(()=>f.ready(),/Both original RNG boundaries/));
check(()=>assert.equal(f.preferenceCalls,0));
f=fixture({latchedFault:true});
check(()=>assert.doesNotThrow(()=>{const invocation=f.enter();f.leave(invocation);}));
check(()=>assert.throws(()=>f.context.checkFault(),/Synthetic full RNG mismatch/));
check(()=>assert.throws(()=>f.ready(),/Synthetic full RNG mismatch/));
check(()=>assert.equal(f.preferenceCalls,0));
f=fixture({emitThrows:true});
check(()=>assert.doesNotThrow(()=>{const invocation=f.enter();f.leave(invocation);}));
check(()=>assert.match(f.context.firstAsyncFault.error,/Synthetic diagnostic sink/));
check(()=>assert.throws(()=>f.context.checkFault(),/Synthetic diagnostic sink/));
for(const introThrowPhase of ['enter','leave']) {
  f=fixture({introThrowPhase});
  check(()=>assert.doesNotThrow(()=>{const invocation=f.enter();f.leave(invocation);}));
  check(()=>assert.match(f.context.firstAsyncFault.error,/Synthetic intro mismatch/));
  check(()=>assert.throws(()=>f.context.checkFault(),/Synthetic intro mismatch/));
}
f=fixture({overlayFault:true});inv=f.enter();f.leave(inv);
check(()=>assert.throws(()=>f.ready(),/Synthetic original overlay failure/));
check(()=>assert.equal(f.preferenceCalls,0));
check(()=>assert.equal(f.context.originalAutoControlsVerified,false));
check(()=>assert.equal(f.context.originalRngStateVerified,false));
console.log(JSON.stringify({status:'passed',assertions,scope:'Actual probe OnStart/check/firstPlaying branches with synthetic closures only; no native execution'}));
