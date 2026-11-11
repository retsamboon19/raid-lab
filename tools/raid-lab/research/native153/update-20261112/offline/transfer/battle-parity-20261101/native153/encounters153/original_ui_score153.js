// Passive Anomaly Interception UI score capture. Original getters/conversion only.
// Install before original context OnInit; read synchronously before finish cleanup.
function installOriginal153AnomalyUiScore(runtime, pin) {
  'use strict';
  const game = Process.getModuleByName('GameAssembly.dll');
  const cls = runtime.class('NK.Spot.Context.Monster.BerserkContext');
  const actk = Il2Cpp.domain.assembly('ACTk.Runtime').image;
  const hex = bytes => Array.from(new Uint8Array(bytes), x => x.toString(16).padStart(2, '0')).join('');
  const checked = (method, rva, prefix) => {
    if (!method.virtualAddress.equals(game.base.add(rva)) ||
        hex(method.virtualAddress.readByteArray(prefix.length / 2)) !== prefix)
      throw Error('Original Anomaly UI score method differs: ' + method.name);
    return method;
  };
  const init = checked(cls.method('OnInit', 0), 118717312,
    '48895c24084889742410574883ec20803dab2a810400488b');
  const getter = checked(cls.method('get_CurrentTargetDamage', 0), 26496832,
    '0f104218488bc10f104a280f1101f20f1042380f114910f2');
  const longClass = actk.class('CodeStage.AntiCheat.ObscuredTypes.ObscuredLong');
  if (!longClass.isValueType || longClass.valueTypeSize !== 40)
    throw Error('Original ObscuredLong value layout differs');
  const convert = checked(longClass.method('op_Implicit').overload('CodeStage.AntiCheat.ObscuredTypes.ObscuredLong'), 9208816,
    '4883ec2833d2e815feffff4883c428c340534883ec204c8b');
  if (init.isStatic || getter.isStatic || !convert.isStatic ||
      init.returnType.name !== 'System.Void' ||
      getter.returnType.name !== 'CodeStage.AntiCheat.ObscuredTypes.ObscuredLong' ||
      convert.returnType.name !== 'System.Int64' || convert.parameters.length !== 1 ||
      convert.parameters[0].type.name !== 'CodeStage.AntiCheat.ObscuredTypes.ObscuredLong')
    throw Error('Original Anomaly UI score signatures differ');
  let context = null, fault = null;
  const listener = Interceptor.attach(init.virtualAddress, {
    onEnter(args) {
      try {
        const value = new Il2Cpp.Object(args[0]);
        if (value.class.type.name !== 'NK.Spot.Context.Monster.InterceptBerserkContext')
          throw Error('Unexpected original Anomaly berserk context');
        if (context && !context.handle.equals(value.handle))
          throw Error('Multiple Anomaly score contexts');
        context = value;
        pin(context);
      } catch (error) { fault = error; }
    }
  });
  return {
    assertInitialized() {
      if (fault) throw fault;
      if (!context) throw Error('Original Anomaly score context initialization not observed');
    },
    readBeforeCleanup() {
      if (fault) throw fault;
      if (!context) throw Error('Original Anomaly score context initialization not observed');
      const originalValue = invokeChecked(getter, context);
      const decoded = invokeChecked(convert, null, [originalValue.unbox().handle]);
      const damage = decoded.unbox().handle.readS64().toString();
      if (!/^(0|[1-9][0-9]*)$/.test(damage)) throw Error('Invalid original Anomaly UI score');
      return {damage, source: 'BerserkContext.get_CurrentTargetDamage',
        conversion: 'original_ACTk_ObscuredLong_op_Implicit',
        uiDestination: 'StageResultInfoData.TotalDamage',
        capturedBeforeCleanup: true, scoreCalculated: false};
    },
    retainUntilExit: listener
  };
}
