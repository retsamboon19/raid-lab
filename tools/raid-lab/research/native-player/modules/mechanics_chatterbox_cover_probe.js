// One private Chatterbox cover experiment. This observes the original
// TimelineSkill node 6 / Shot_09 (skill 510209) and its own PlayEnd. It does
// not establish that the attack is coverable or install a production policy.
function createMechanicsChatterboxCoverProbe(runtime, management, actions, emit) {
  if (!runtime || !management || management.isNull() || !actions ||
      typeof actions.snapshot!=="function" || typeof actions.setCover!=="function" ||
      typeof emit!=="function" || typeof invokeChecked!=="function" ||
      typeof intArg!=="function")
    throw new Error("Chatterbox cover diagnostic needs native runtime, management and actions");
  const game=Process.getModuleByName("GameAssembly.dll");
  const at=(method,rva,name)=>{
    if (Number(method.relativeVirtualAddress)!==rva ||
        !method.virtualAddress.equals(game.base.add(rva)))
      throw new Error("Installed Chatterbox method changed: "+name);
    return method;
  };
  const field=(klass,name,offset)=>{
    if (klass.field(name).offset!==offset)
      throw new Error("Installed Chatterbox field changed: "+klass.name+"."+name);
  };
  const enumNumber=value=>typeof value==="number"?value:Number(value.field("value__").value);
  const timeline=runtime.class("NK.Spot.BehaviorTree.Monster.Actions.TimelineSkill");
  const task=Il2Cpp.domain.assembly("BehaviorDesigner.Runtime").image
    .class("BehaviorDesigner.Runtime.Tasks.Task");
  const monsterData=runtime.class("NK.Spot.Monster.Model.MonsterData");
  const monsterClass=runtime.class("NK.Spot.Model.Monster.SpotMonster");
  const sharedMonsterClass=runtime.class("NK.Spot.BehaviorTree.Variables.SharedBattleMonster");
  const battleMonsterClass=runtime.class("NK.Spot.BehaviorTree.Models.BattleMonster");
  const skill=runtime.class("NK.Spot.Model.Monster.SpotMonsterSkill");
  const skillInfo=Il2Cpp.domain.assembly("NK.Runtime.StaticData").image
    .class("NK.StaticData.StaticDataLayer.StaticInfo.MonsterSkillStaticInfo");
  const eventClass=runtime.class("NK.Spot.Event.Monster.MonsterConditionEvent");
  const entityInfo=runtime.class("NK.Spot.Logic.Character.SpotEntityInfo");
  const condition=runtime.class("NK.Spot.Model.Monster.MonsterConditionType");
  field(task,"id",0x30);
  field(timeline,"_aniNumberTypes",0x58);
  field(timeline,"_passTime",0x84);
  field(runtime.class("NK.Spot.BehaviorTree.Monster.Behaviors.BattleAction"),
    "mMonster",0x50);
  field(battleMonsterClass,"<Monster>k__BackingField",0x10);
  field(monsterClass,"<Data>k__BackingField",0x88);
  field(monsterData,"SkillList",0x30);
  field(skill,"SkillStaticInfo",0x18);
  field(skill,"AniNumberType",0x30);
  field(skill,"TimelineLoopStartTime",0xe0);
  field(eventClass,"MonsterInfo",0x40);
  field(eventClass,"CurrentCondition",0x48);
  field(entityInfo,"EntityID",0x10);
  field(runtime.class("NK.Spot.SpotManagement"),"_tickCount",0x64);
  const onStart=at(timeline.method("OnStart",0),0x065485e0,"TimelineSkill.OnStart");
  const getSkill=at(monsterData.method("GetSkill",1),0x06341d70,"MonsterData.GetSkill(aniNumber)");
  // Installed OnStart has a direct E8 call at 0x06548925. Its return is
  // 0x0654892A; other GetSkill calls nested inside OnStart are not this node's
  // selected skill and must not count toward the observed return.
  const onStartGetSkillReturn=game.base.add(0x0654892a);
  const playEnd=at(timeline.method("PlayEnd",1),0x06548dc0,"TimelineSkill.PlayEnd");
  const getTableId=at(skillInfo.method("get_TableId",0),0x03e05810,
    "MonsterSkillStaticInfo.get_TableId");
  const values=Object.fromEntries(["FireCasting","Fire","Idle"].map(name=>
    [name,enumNumber(condition.field(name).value)]));
  if (new Set(Object.values(values)).size!==3)
    throw new Error("Installed MonsterConditionType values changed");

  let fault=null, firstStart=null, casting=null, fired=null,
      end=null, coverTick=null, releaseTick=null, covered=false, completed=false;
  let previousTick=-1, startsSeen=0, hookStartCount=0, hookEndCount=0;
  let releaseState=null, resumeReadback=null;
  const starts=[],ends=[],conditions=[];
  const active=new Map();
  const latch=(place,error)=>{
    if (fault===null) fault=place+": "+(error&&error.stack?error.stack:String(error));
  };
  const tickNow=()=>management.handle.add(0x64).readU32();
  const push=(queue,row,place)=>{
    if (queue.length>=16) {latch(place,"native observation buffer overflow");return;}
    queue.push(row);
  };
  // These hooks retain only native pointer/integer observations. Managed
  // getters, input actions and reporting run after the original tick returns.
  Interceptor.attach(onStart.virtualAddress,{
    onEnter(args) {
      this.thread=Process.getCurrentThreadId();
      this.frame=null;
      try {
        if (args[0].isNull() || args[0].add(0x30).readS32()!==6) return;
        hookStartCount++;
        const stack=active.get(this.thread)||[];
        this.frame={self:args[0],tick:tickNow(),skill:null,skillCalls:0};
        stack.push(this.frame);active.set(this.thread,stack);
      } catch(error) {latch("TimelineSkill.OnStart enter",error);}
    },
    onLeave() {
      if (!this.frame) return;
      try {
        const stack=active.get(this.thread);
        if (!stack || stack.pop()!==this.frame)
          throw new Error("Original TimelineSkill start nesting changed");
        if (!stack.length) active.delete(this.thread);
        this.frame.passTimeAtReturn=this.frame.self.add(0x84).readFloat();
        push(starts,this.frame,"TimelineSkill.OnStart");
      } catch(error) {latch("TimelineSkill.OnStart leave",error);}
    }
  });
  Interceptor.attach(getSkill.virtualAddress,{
    onEnter(args) {
      this.frame=null;
      try {
        const stack=active.get(Process.getCurrentThreadId());
        if (stack && stack.length &&
            this.returnAddress.equals(onStartGetSkillReturn) &&
            args[1].toInt32()===9)
          this.frame=stack[stack.length-1];
      } catch(error) {latch("MonsterData.GetSkill enter",error);}
    },
    onLeave(retval) {
      if (!this.frame) return;
      try {
        this.frame.skillCalls++;
        // Frida's callback retval wrapper is transient. Retain a copy of its
        // native address for the post-tick managed-object comparison.
        if (this.frame.skillCalls===1) this.frame.skill=ptr(retval);
      } catch(error) {latch("MonsterData.GetSkill leave",error);}
    }
  });
  Interceptor.attach(playEnd.virtualAddress,{
    onEnter(args) {
      try {
        if (args[0].isNull() || args[0].add(0x30).readS32()!==6) return;
        hookEndCount++;
        push(ends,{self:args[0],tick:tickNow()},"TimelineSkill.PlayEnd");
      } catch(error) {latch("TimelineSkill.PlayEnd enter",error);}
    }
  });

  // Forward the already intercepted SendEventDefault event here. No extra
  // SendEvent hook is installed and nothing is emitted from its callback.
  function observeSendEvent(event) {
    if (fault || !event || event.isNull() ||
        event.class.type.name!==eventClass.type.name) return;
    try {
      const handle=event.handle;
      const monster=handle.add(0x40).readPointer();
      if (monster.isNull()) throw new Error("Original condition lacks MonsterInfo");
      const entityId=monster.add(0x10).readS32();
      const value=handle.add(0x48).readS32();
      if (entityId===8192 && Object.values(values).includes(value))
        push(conditions,{tick:tickNow(),entityId,value},"MonsterConditionEvent");
    } catch(error) {latch("MonsterConditionEvent",error);}
  }
  const readStart=row=>{
    const action=new Il2Cpp.Object(row.self);
    if (action.class.type.name!==timeline.type.name ||
        Number(action.field("id").value)!==6)
      throw new Error("Original TimelineSkill node identity changed");
    const anis=action.field("_aniNumberTypes").value;
    if (!anis || anis.isNull()) throw new Error("Original node 6 animation list absent");
    const count=invokeChecked(anis.method("get_Count",0),anis)
      .unbox().handle.readS32();
    if (count!==1) throw new Error("Original node 6 animation list is not unique");
    const ani=invokeChecked(anis.method("get_Item",1),anis,[intArg(0)])
      .unbox().handle.readS32();
    if (ani!==9) throw new Error("Original node 6 animation is not Shot_09");
    // OnStart 0x065485E0 reads SharedBattleMonster.Value, which is a
    // BattleMonster wrapper; its Monster is +0x10. Then it reads
    // SpotMonster.Data (+0x88) and MonsterData.SkillList (+0x30). Trial 144
    // proved +0x10 on the *shared variable* is not the Monster pointer.
    // Trial 137
    // showed our nested hook did not observe one matching return; that is
    // not evidence the original skill was absent. Read the source path's
    // retained list after the tick instead of relying on an inner hook.
    const shared=action.field("mMonster").value;
    if (!shared || shared.isNull() ||
        shared.class.type.name!==sharedMonsterClass.type.name)
      throw new Error("Original node 6 shared monster variable absent");
    const wrapper=invokeChecked(shared.method("get_Value",0),shared);
    if (!wrapper || wrapper.isNull() ||
        wrapper.class.type.name!==battleMonsterClass.type.name)
      throw new Error("Original node 6 BattleMonster value absent");
    const monster=wrapper.field("<Monster>k__BackingField").value;
    if (!monster || monster.isNull() || monster.class.type.name!==monsterClass.type.name)
      throw new Error("Original node 6 monster absent");
    const data=monster.field("<Data>k__BackingField").value;
    if (!data || data.isNull() || data.class.type.name!==monsterData.type.name)
      throw new Error("Original monster data absent");
    const skillList=data.field("SkillList").value;
    if (!skillList || skillList.isNull())
      throw new Error("Original monster skill list absent");
    const skillCount=invokeChecked(skillList.method("get_Count",0),skillList)
      .unbox().handle.readS32();
    if (skillCount<1 || skillCount>128)
      throw new Error("Original monster skill list count outside bound");
    let selected=null;
    for (let index=0;index<skillCount;index++) {
      const candidate=invokeChecked(skillList.method("get_Item",1),skillList,[intArg(index)]);
      if (!candidate || candidate.isNull() || candidate.class.type.name!==skill.type.name)
        throw new Error("Original monster skill list item changed");
      if (enumNumber(candidate.field("AniNumberType").value)===ani) {
        if (selected) throw new Error("Original monster Shot_09 skill is ambiguous");
        selected=candidate;
      }
    }
    if (!selected) throw new Error("Original monster Shot_09 skill absent");
    if (row.skillCalls>1 || (row.skillCalls===1 &&
        (!row.skill || row.skill.isNull() || !row.skill.equals(selected.handle))))
      throw new Error("Original nested GetSkill observation disagrees with skill list");
    const info=selected.field("SkillStaticInfo").value;
    if (!info || info.isNull() || info.class.type.name!==skillInfo.type.name)
      throw new Error("Original selected skill static info changed");
    const tableId=invokeChecked(getTableId,info).unbox().handle.readS32();
    if (tableId!==510209) throw new Error("Original node 6 skill is "+tableId);
    const sourcePassTime=Number(selected.field("TimelineLoopStartTime").value);
    const observedPassTime=row.passTimeAtReturn;
    if (!Number.isFinite(sourcePassTime) || observedPassTime!==sourcePassTime)
      throw new Error("Original OnStart skill-derived pass time disagrees");
    return {self:row.self,tick:row.tick,nodeId:6,animationNumber:ani,
      skillId:tableId,nestedGetSkillCalls:row.skillCalls};
  };
  function afterTick(tick) {
    checkFault();
    try {
      if (!Number.isSafeInteger(tick) || tick<=previousTick || tick<0 ||
          tickNow()!==tick) throw new Error("Probe requires each completed original tick");
      previousTick=tick;
      for (const row of starts.splice(0)) {
        startsSeen++;
        if (firstStart) continue; // exactly one diagnostic episode
        firstStart=readStart(row);
        emit({status:"original_chatterbox_node6_skill_observed",tick:firstStart.tick,
          nodeId:6,animationNumber:9,skillId:510209,
          nestedGetSkillCalls:firstStart.nestedGetSkillCalls});
      }
      for (const row of conditions.splice(0)) {
        if (row.value===values.FireCasting && !casting && firstStart &&
            row.tick>=firstStart.tick) {
          casting={tick:row.tick,entityId:row.entityId};
          emit({status:"original_chatterbox_first_fire_casting",...casting});
        } else if (row.value===values.Fire && casting && !fired &&
                   row.tick>=casting.tick) {
          fired={tick:row.tick,entityId:row.entityId};
          emit({status:"original_chatterbox_first_fire",...fired});
        }
      }
      for (const row of ends.splice(0)) {
        if (firstStart && !end && row.self.equals(firstStart.self) &&
            row.tick>=firstStart.tick) {
          end={tick:row.tick,nodeId:6,skillId:510209};
          emit({status:"original_chatterbox_first_play_end",...end});
        }
      }
      if (completed && !resumeReadback && tick>releaseTick) {
        const state=actions.snapshot();
        if (!Array.isArray(releaseState?.squad)||!Array.isArray(state.squad))
          throw new Error("Original squad ammo readback missing after cover release");
        const baseline=new Map(releaseState.squad.map(r=>[r.entityId,r.usedAmmoCount]));
        const firedAfterRelease=state.squad.some(r=>baseline.has(r.entityId)&&
          r.usedAmmoCount>baseline.get(r.entityId));
        if (firedAfterRelease || tick-releaseTick>=60) {
          resumeReadback={tick,releaseTick,state,firedAfterRelease};
          emit({status:"original_chatterbox_diagnostic_resume_readback",...resumeReadback});
        }
      }
    } catch(error) {latch("afterTick",error);}
    checkFault();
  }
  function beforeTick(tick) {
    checkFault();
    if (!Number.isSafeInteger(tick) || tick<=previousTick || tick<0)
      throw new Error("Probe beforeTick must precede the next original tick");
    if (completed || !casting) return;
    if (end && !covered) {
      latch("beforeTick","Original PlayEnd preceded diagnostic cover action");
      checkFault();
    }
    if (!covered) {
      const state=actions.snapshot();
      if (state.forcedCover!==false || state.autoAim!==true || state.inputType===2)
        throw new Error("Chatterbox cover diagnostic requires untouched original-auto ownership");
      actions.setCover(true);covered=true;coverTick=tick;
      const after=actions.snapshot();
      if (after.forcedCover!==true || after.autoAim!==true)
        throw new Error("Original whole-squad cover did not engage without changing auto-aim");
      emit({status:"original_chatterbox_diagnostic_cover_on",tick,
        castTick:casting.tick,nodeId:6,skillId:510209,wholeSquad:true,
        nativeBefore:state,nativeAfter:after});
    } else if (end) {
      const before=actions.snapshot();
      if (before.forcedCover!==true || before.autoAim!==true)
        throw new Error("Diagnostic cover ownership changed before original PlayEnd");
      actions.setCover(false);covered=false;completed=true;releaseTick=tick;
      const after=actions.snapshot();
      if (after.forcedCover!==false || after.autoAim!==true)
        throw new Error("Original cover release did not restore auto-aim");
      releaseState=after;
      emit({status:"original_chatterbox_diagnostic_cover_off",tick,
        originalPlayEndTick:end.tick,wholeSquad:true,nativeBefore:before,nativeAfter:after});
    }
  }
  function summary() {
    return {status:"original_chatterbox_cover_diagnostic",scope:"first_node6_skill510209_only",
      firstStart:firstStart?{tick:firstStart.tick,nodeId:6,animationNumber:9,
        skillId:510209,nestedGetSkillCalls:firstStart.nestedGetSkillCalls}:null,
      casting,fired,end,coverTick,releaseTick,covered,completed,startsSeen,
      hookStartCount,hookEndCount,fault,coverFeasibility:"unvalidated"};
  }
  function checkFault() {if (fault) throw new Error(fault);}
  emit({status:"original_chatterbox_cover_probe_ready",waveId:6302004,
    monsterTableId:1520020113,expectedInstalledDllSha256:
      "2df7134a6a9c3a8dbbde88402fc8d16d1d6c3f4c2d5e262bea78c3d78b96dd02",
    observedNodeId:6,observedSkillId:510209,wholeSquad:true,
    coverFeasibility:"unvalidated",drawsRandom:false,
    changesOriginalInputOnly:true,noDirectCombatMutation:true});
  return {observeSendEvent,beforeTick,afterTick,summary,checkFault};
}
