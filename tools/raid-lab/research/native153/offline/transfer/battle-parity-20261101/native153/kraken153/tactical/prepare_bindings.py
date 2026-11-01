"""Build only current153 tactical metadata/prefix bindings; never launch a player."""
from pathlib import Path
import hashlib
import importlib.util
import json
import sys

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[4]
NATIVE = HERE.parents[1]
META = NATIVE.parent / 'metadata'
CLIENT = 'd39896d3770888039c728a1908448c3db5efa7cdf874c90d56f46d8d566428d2'
FILES = ['current153-run3', 'current153-kraken-tactical1', 'current153-kraken-unity-leaves1',
         'current153-statistics-event-hp1', 'current153-initial-monster-target1',
         'current153-result-monster-statistics1', 'current153-kraken-monster-static1']
# Named lookup only. No address-wide method search or decompilation.
METHODS = {
 'ammo': ('NK.Spot.Model.Character.Weapon.SpotWeaponData', 'get_CurrentAmmo', 0),
 'weapon': ('NK.Spot.Model.Character.Weapon.SpotWeaponData', 'get_WeaponType', 0),
 'camera': ('UnityEngine.Camera', 'WorldToScreenPoint', 1),
 'auto': ('NK.Spot.Event.Data.ChangeAutoModeEvent', 'Send', 2),
 'tagCtor': ('NK.Spot.Event.Character.TagCharacterEvent', '.ctor', 1),
 'tagSend': ('NK.Spot.Event.Character.TagCharacterEvent', 'Send', 0),
 'coverCtor': ('NK.Spot.Event.Character.ChangeForcedCoverEvent', '.ctor', 1),
 'eventSend': ('NK.Spot.Common.SpotEvent', 'Send', 0),
 'down': ('NK.Spot.Context.SpotDriver', 'InputPointDown', 0),
 'up': ('NK.Spot.Context.SpotDriver', 'InputPointUp', 0),
 'move': ('NK.Spot.Context.SpotDriver', 'MoveAimPosition', 3),
 'autoRead': ('NK.Spot.Context.Player.TeamContext', 'get_IsAutoModeAim', 0),
 'coverRead': ('NK.Spot.Context.Player.TeamContext', 'get_IsForcedCover', 0),
 'inputRead': ('NK.Spot.Context.SpotDriver', 'get_InputType', 0),
 'unityAlive': ('UnityEngine.Object', 'op_Implicit', 1),
 'transform': ('UnityEngine.Component', 'get_transform', 0),
 'position': ('UnityEngine.Transform', 'get_position', 0),
 'colliderEnabled': ('UnityEngine.Collider', 'get_enabled', 0),
 'hp': ('NK.Spot.Model.Common.SpotEntityStatus', 'get_HP', 0),
 'maxHp': ('NK.Spot.Model.Common.SpotEntityStatus', 'get_MaxHP', 0),
 'partHp': ('NK.Spot.Model.Monster.SpotMonsterPartsData.PartsData', 'get_CurrentHp', 0),
 'partMaxHp': ('NK.Spot.Model.Monster.SpotMonsterPartsData.PartsData', 'get_MaxHp', 0),
 'partActive': ('NK.Spot.Model.Monster.SpotMonsterPartsData.PartsData', 'get_IsActive', 0),
 'qteOrder': ('NK.Spot.Model.QuickTimeEvent.SpotQuickTimeCollider', 'get_Order', 0),
 'qteSuccess': ('NK.Spot.Model.QuickTimeEvent.SpotQuickTimePreset', 'IsSuccess', 0),
 'dispatch': ('NK.Spot.SpotManagement', 'SendEventDefault', 1),
 'fireProjectile': ('NK.Spot.Logic.Monster.MonsterAttackLogic', 'FireProjectile', 6),
 'projectileCreate': ('NK.Spot.ProjectileContext', 'OnProjectileCreate', 1),
 'mouse': ('UnityEngine.Input', 'get_mousePosition', 0),
 'keyUpdate': ('NK.Spot.Context.KeyInputContext', 'UpdateTick', 1),
}


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    sys.path.insert(0, str(ROOT / 'tools/raid-lab/private/native-python'))
    import pefile
    inputs, classes = {}, {}
    for name in FILES:
        path = META / name / 'mechanics-metadata.json'
        data = json.loads(path.read_text())
        if data['clientSha256'] != CLIENT or data.get('missingRoots'):
            raise ValueError('Exact complete current153 metadata required: ' + name)
        inputs[str(path.relative_to(ROOT))] = sha(path)
        classes.update({c['class']: c for c in data['classes']})
        for value in data.get('embeddedValueTypes', []):
            classes.setdefault(value['class'], {**value, 'assembly': None,
                                               'isValueType': True, 'methods': []})
    pe = pefile.PE(str(ROOT / 'NIKKE/NIKKE/game/GameAssembly.dll'), fast_load=True)
    methods = {}
    for key, (class_name, name, count) in METHODS.items():
        cls = classes[class_name]
        found = [m for m in cls['methods'] if m['name'] == name and len(m['parameters']) == count]
        if len(found) != 1 or not found[0]['nativeRva']:
            raise ValueError('One exact native method required: ' + key)
        method = found[0]
        methods[key] = {'assembly': cls['assembly'], 'className': class_name, 'name': name,
                        'returns': method['returns'], 'parameters': [p['type'] for p in method['parameters']],
                        'static': bool(method['flags'] & 16), 'rva': method['nativeRva'],
                        'prefixHex': pe.get_data(method['nativeRva'], 16).hex()}
    # Existing complete-method extractor, applied to exactly the mouse consumer.
    spec = importlib.util.spec_from_file_location('kraken153_selected_body', NATIVE / 'disassemble_chained153.py')
    module = importlib.util.module_from_spec(spec); spec.loader.exec_module(module)
    stem = HERE / 'key-input-update-source'
    if not stem.with_suffix('.json').exists():
        module.extract(META / 'current153-run3/mechanics-metadata.json',
                       'NK.Spot.Context.KeyInputContext', 'UpdateTick', str(stem))
    body = json.loads(stem.with_suffix('.json').read_text())
    if body['clientSha256'] != CLIENT or body['primaryRva'] != methods['keyUpdate']['rva']:
        raise ValueError('Existing selected method source binding differs')
    for fragment in body['fragments']:
        raw = pe.get_data(fragment['startRva'], fragment['endRva'] - fragment['startRva'])
        if hashlib.sha256(raw).hexdigest() != fragment['sha256']:
            raise ValueError('Existing selected method original bytes differ')
    candidates = [i for f in body['fragments'] for i in f['instructions']
                  if i['mnemonic'] == 'call' and i['operands'] == hex(methods['mouse']['rva'])]
    if len(candidates) != 1 or len(bytes.fromhex(candidates[0]['bytes'])) != 5:
        raise ValueError('One exact direct KeyInputContext mouse getter call required')
    selected = candidates[0]
    pointer = {'callerClass': 'NK.Spot.Context.KeyInputContext', 'callerMethod': 'UpdateTick',
               'callRva': selected['rva'], 'returnRva': selected['rva'] + 5,
               'callHex': selected['bytes'], 'getterBinding': 'mouse',
               'abi': 'Original getter returns Vector3 through args[0] hidden return buffer; RAX is same buffer. Observe normal return, modify only x/y under owned input.'}
    # Fields/enums are checked from fresh metadata, including all nonstatic fields
    # on the selected declared types. Runtime collection methods remain original.
    selected_classes = {name for name, _, _ in METHODS.values()} | {
        'NK.Spot.Context.Monster.MonsterContext', 'NK.Spot.Model.Monster.SpotMonster',
        'NK.Spot.Model.Monster.SpotMonsterCondition',
        'NK.Spot.Model.Common.SpotEntity', 'NK.Spot.Model.Character.SpotCharacter',
        'NK.Spot.Model.Character.SpotCharacterCover', 'NK.Spot.Logic.Character.SpotEntityInfo',
        'NK.Spot.Event.Data.SpotAutoType', 'NK.Spot.Model.Enum.SpotObjectType',
        'NK.StaticData.ColType', 'NK.StaticData.WeaponType',
        'NK.Spot.Model.QuickTimeEvent.SpotQuickTimeCollider.ColliderState',
        'NK.Spot.Model.Monster.MonsterConditionType',
        'NK.Spot.Monster.Model.MonsterData', 'NK.StaticData.StaticDataLayer.StaticInfo.MonsterStaticInfo'}
    selected_classes.update(c for c in classes if c.startswith(('NK.Spot.Event.QuickTime.', 'NK.Spot.Event.Projectile.')))
    selected_classes.update(['NK.Spot.Event.Monster.MonsterAttackEvent', 'NK.Spot.Event.Monster.MonsterConditionEvent',
                              'NK.Spot.Event.Common.OnEntityGetDamageEvent', 'NK.Spot.Event.Character.CoverTakeDamageEvent'])
    selected_classes.update(['NK.Spot.Common.SpotEvent.SpotEventType', 'NK.Common.StatValue'])
    class_specs = {name: {'assembly': classes[name]['assembly'], 'isValueType': classes[name]['isValueType'],
                        'valueSize': classes[name]['valueSize'], 'fields': classes[name]['fields']}
                   for name in sorted(selected_classes) if name in classes}
    inputs[str(stem.with_suffix('.json').relative_to(ROOT))] = sha(stem.with_suffix('.json'))
    result = {'schemaVersion': 1, 'clientSha256': CLIENT, 'metadataInputs': inputs,
              'methods': methods, 'classes': class_specs, 'virtualPointer': pointer,
              'nativeRunPerformed': False, 'current153TacticsValidated': False,
              'limitations': ['Prefixes are entry identity guards, not recovered method implementations.',
                             'Dynamic generic collection access uses the original bridge; validate fresh native readbacks before battle.',
                             'Current authored encounter-rule proof must be supplied separately.']}
    path = HERE / 'tactical-binding.json'
    with path.open('x', encoding='utf8') as sink:
        json.dump(result, sink, indent=2); sink.write('\n')
    print(json.dumps({'path': str(path), 'sha256': sha(path), 'methods': len(methods), 'classes': len(class_specs)}))


if __name__ == '__main__':
    main()
