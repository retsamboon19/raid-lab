"""Port the retained read-only native aim checks using exact153 metadata.

Source transformation only: no combat calculations, game launch or installed edits.
"""
import hashlib
import json
from pathlib import Path

HERE = Path(__file__).resolve().parent
META = HERE.parent / 'metadata/current153-run3/mechanics-metadata.json'
SOURCE = HERE / 'runtime-review2/mechanics_aim_binding.js'
TARGET = HERE / 'practice_aim_binding.js'


def main():
    metadata = json.loads(META.read_text())
    client = metadata['clientSha256']
    assert client == 'd39896d3770888039c728a1908448c3db5efa7cdf874c90d56f46d8d566428d2'
    classes = {row['class']: row for row in metadata['classes']}
    contracts = []
    for name, methods in {
        'NK.Spot.Presentation.UI.UIAimControll': [('OnInit', 0), ('UpdateTick', 1), ('GetAimPosition', 1)],
        'NK.Spot.Presentation.Camera.SpotCameraControl': [('UpdateTick', 1)],
        'NK.Spot.Presentation.UI.UIAim': [('UpdateTick', 1)],
        'NK.Spot.SpotManagement': [('IsResourceLoad', 0)],
        'NK.Spot.Logic.Character.AimLogic': [('GetAimPosition', 1), ('GetAimDirection', 1)],
    }.items():
        for method_name, count in methods:
            found = [x for x in classes[name]['methods'] if x['name'] == method_name and len(x['parameters']) == count]
            if len(found) != 1 or not found[0]['nativeRva']:
                raise ValueError(f'Ambiguous native aim method {name}.{method_name}/{count}')
            contracts.append({'className': name, 'name': method_name, 'count': count,
                              'rva': found[0]['nativeRva']})
    aim_fields = {row['name']: row for row in classes['NK.Spot.Presentation.UI.UIAimControll']['fields']}
    fields = []
    for name, offset, typ in [('_screenToCanvasRatio', 160, 'UnityEngine.Vector2'),
                              ('_safeAreaTop', 176, 'System.Single'), ('_safeAreaBottom', 180, 'System.Single'),
                              ('_safeAreaLeft', 184, 'System.Single'), ('_safeAreaRight', 188, 'System.Single')]:
        row = aim_fields[name]
        assert (row['offset'], row['type']) == (offset, typ)
        fields.append({'name': name, 'offset': offset, 'type': typ})
    source = SOURCE.read_text()
    source = source.replace('2df7134a6a9c3a8dbbde88402fc8d16d1d6c3f4c2d5e262bea78c3d78b96dd02', client)
    source = source.replace('prepareMechanicsAimBinding', 'verifyPracticeAimBinding')
    # This captured-auto fixture needs observations only; omit manual aim commands.
    start = source.index('  const vectorArg = values => {')
    end = source.index('  const same =', start)
    source = source[:start] + source[end:]
    start = source.index('  const moveType =')
    end = source.index('  const aimLogic =', start)
    source = source[:start] + source[end:]
    start = source.index('  const moveAimNow =')
    end = source.index('  emit({ phase: "mechanics_aim_binding", status: "live_original_binding_verified",', start)
    source = source[:start] + source[end:]
    source = source.replace('getAimPosition: readUiAim, getNativeAimState: nativeAimState,\n    moveAimNow, moveAim: (id, position) => onMain(() => moveAimNow(id, position))',
                            'getAimPosition: readUiAim, getNativeAimState: nativeAimState')
    marker = '  const live = geometry.live || {};'
    guard = '''  for (const row of PRACTICE_AIM_CONTRACT.methods) {
    const method=runtime.class(row.className).method(row.name,row.count);
    if (Number(method.relativeVirtualAddress)!==row.rva)
      throw new Error('Current153 original aim method changed: '+row.className+'.'+row.name);
  }
  for (const row of PRACTICE_AIM_CONTRACT.fields) {
    const field=runtime.class('NK.Spot.Presentation.UI.UIAimControll').field(row.name);
    if (field.offset!==row.offset || field.type.name!==row.type || field.isStatic)
      throw new Error('Current153 original aim field changed: '+row.name);
  }
'''
    source = source.replace(marker, guard + marker)
    contract = {'clientSha256': client, 'metadataSha256': hashlib.sha256(META.read_bytes()).hexdigest(),
                'methods': contracts, 'fields': fields}
    source = '// Current153 captured-auto aim verification; runtime validation pending.\n' + \
             'const PRACTICE_AIM_CONTRACT = ' + json.dumps(contract, separators=(',', ':')) + ';\n' + \
             source.removeprefix('// UNVALIDATED153 MIGRATION CANDIDATE: no execution/parity claim.\n')
    with TARGET.open('x', encoding='utf-8') as sink:
        sink.write(source)
    with (HERE / 'practice-aim-source-binding.json').open('x', encoding='utf-8') as sink:
        json.dump({**contract, 'sourceSha256': hashlib.sha256(SOURCE.read_bytes()).hexdigest(),
                   'outputSha256': hashlib.sha256(TARGET.read_bytes()).hexdigest(),
                   'scope': 'Read-only original aim dependency checks; no manual aiming',
                   'nativeTested': False}, sink, indent=2)
    print(json.dumps({'target': str(TARGET), 'methods': len(contracts), 'fields': len(fields)}))


if __name__ == '__main__':
    main()
