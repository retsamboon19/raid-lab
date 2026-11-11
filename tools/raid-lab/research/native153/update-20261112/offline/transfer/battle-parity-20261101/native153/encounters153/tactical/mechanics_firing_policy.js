// Input orchestration only. Original current153 IsAutoFireWeapon getter
// 0x066E88A0 (107907232), IsFullCharge 0x066E8990 (107907472).
// Never infer automatic firing from the displayed SR/RL weapon class: an
// original replacement weapon can retain that class and fire while held.
function createMechanicsFiringPolicy(actions,configuration={}) {
  let previous = null;
  return {
    reset() { previous = null; },
    step(weaponType, ready) {
      const state = actions.firingState();
      if (typeof state.focusedIsAutoFireWeapon !== 'boolean' ||
          typeof state.focusedIsFullCharge !== 'boolean' ||
          typeof state.focusedWeaponIdentity !== 'string' || !state.focusedWeaponIdentity)
        throw Error('Original focused firing mode/weapon identity unavailable');
      const current = {actor:state.focusedEntityId, weapon:state.focusedWeaponIdentity,
        automatic:state.focusedIsAutoFireWeapon, type:weaponType,input:state.focusedNativeInputType};
      const changed = previous !== null && (previous.actor !== current.actor ||
        previous.weapon !== current.weapon || previous.automatic !== current.automatic ||
        previous.type !== current.type || previous.input !== current.input);
      previous = current;
      // ChangeWeapon can replace native firing state while SpotDriver still
      // reports a held pointer. Re-establish an original up/down edge. Keep the
      // up for one engine update, then press on the following policy step.
      if (changed && state.inputType === 2) {
        if(configuration.nativeInputTypes===true&&state.focusedNativeInputType===2)actions.setActorStance(state.focusedEntityId,'Idle');
        actions.release(); return 'weapon_transition_release';
      }
      const releaseFired=configuration.nativeInputTypes===true?state.focusedNativeInputType===2:!current.automatic&&['SR','RL'].includes(weaponType);
      if (releaseFired &&
          state.inputType === 2 && state.focusedIsFullCharge && (configuration.nativeInputTypes!==true||ready)) {
        actions.release(); return 'full_charge_release';
      }
      if (ready && state.inputType !== 2) {
        actions.press(); return 'press';
      }
      return 'hold';
    }
  };
}

function mechanicsOriginalDownTimingGetter(runtime) {
  const method=runtime.class('NK.Spot.Model.Character.Weapon.SpotWeaponData').method('get_IsDownTypeFireTiming',0);
  const prefix='4883ec5883b9e800000002750732c04883c458c30f108198';
  const actual=Array.from(new Uint8Array(method.virtualAddress.readByteArray(24)),x=>x.toString(16).padStart(2,'0')).join('');
  if(!method.virtualAddress.equals(Process.getModuleByName('GameAssembly.dll').base.add(107907280))||actual!==prefix||method.isStatic||method.parameters.length||method.returnType.name!=='System.Boolean')throw Error('Original IsDownTypeFireTiming signature/prefix changed');
  return method;
}

function mechanicsPreserveDirectedTrigger(nativeInputMode,carryOwned,actor,target) {
  return nativeInputMode===true&&target?.unsafePresent!==true&&
    (carryOwned===true||[1,2,3].includes(actor?.weapon?.nativeInputType));
}
