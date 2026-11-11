"""Bind custom-build constructors to exact current153 metadata and PE bytes only."""
from pathlib import Path
import hashlib
import json
import sys

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[3]
METADATA = HERE.parent.parent / 'metadata'
sys.path.insert(0, str(ROOT / 'tools/raid-lab/private/native-python'))
import pefile

CLIENT = 'd39896d3770888039c728a1908448c3db5efa7cdf874c90d56f46d8d566428d2'
SOURCES = [METADATA / name / 'mechanics-metadata.json' for name in (
    'current153-run2', 'current153-custom-build1', 'current153-custom-build2')]
CLASSES = {
 'NK.Common.System.Stat.CharacterStatHelper',
 'NK.Common.System.Stat.StatCalculateInfo', 'NK.Common.System.Stat.StatCalculateInfo.Builder',
 'NK.Common.System.Stat.StatCalculateInfo.Builder.StatCalculateParameterEquipmentRecord',
 'NK.Common.System.Stat.StatCalculateInfo.Builder.StatCalculateParameterHarmonyCubeRecord',
 'NK.Common.System.Stat.RecycleDataProvider', 'NK.Common.System.Stat.CharacterStatData',
 'NK.Common.System.UserData.CharacterSnapshot',
 'NK.Common.System.UserData.CharacterSnapshot.ItemStateEffects',
 'NK.Common.System.UserData.CharacterSnapshot.ItemStateEffects.Builder',
 'NK.Common.System.UserData.CharacterSnapshot.ItemStateEffects.CubeAndLevel',
 'NK.Common.System.UserData.CharacterSnapshot.ItemStateEffects.FavoriteItemAndLevel',
 'NK.Common.System.UserData.CharacterSnapshotExtension', 'NK.Common.System.UserData.NKCharacterInfo',
 'NK.Common.System.UserData.EquipsAndCube', 'NK.Common.System.UserData.EquipsAndCube.Builder',
 'NK.Spot.Common.SpotCharacterData', 'NK.Spot.Common.SpotCharacterData_Status',
 'NK.StaticData.DataManager', 'NK.StaticData.DataTables.CharacterTable',
 'NK.StaticData.DataTables.ItemEquipTable', 'NK.StaticData.DataTables.ItemHarmonyCubeTable',
 'NK.StaticData.DataTables.FavoriteItemTable',
 'NK.StaticData.StaticDataLayer.StaticInfo.CharacterStaticInfo',
 'NK.StaticData.StaticDataLayer.StaticInfo.GradeCoreStaticInfo',
 'NK.StaticData.StaticDataLayer.StaticInfo.ItemEquipStaticInfo',
 'NK.StaticData.StaticDataLayer.StaticInfo.ItemHarmonyCubeStaticInfo',
 'NK.StaticData.StaticDataLayer.StaticInfo.FavoriteItemStaticInfo',
 'NK.StaticData.FavoriteItemSkillGroupData',
}

def sha(path):
    with path.open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()

def build():
    dll = ROOT / 'NIKKE/NIKKE/game/GameAssembly.dll'
    if sha(dll) != CLIENT:
        raise ValueError('Exact current153 GameAssembly required')
    pe = pefile.PE(str(dll), fast_load=True)
    classes = {}
    for source in SOURCES:
        payload = json.loads(source.read_text(encoding='utf-8'))
        if payload['clientSha256'] != CLIENT:
            raise ValueError('Foreign metadata source')
        for row in payload['classes']:
            if row['class'] in CLASSES or any(row['class'].startswith(root + '.') for root in CLASSES):
                classes[row['class']] = row
    if CLASSES - classes.keys():
        raise ValueError('Missing exact153 metadata: ' + str(CLASSES - classes.keys()))
    methods = {}
    favorite_source = METADATA / 'current153-custom-favorite-resolver1/method-owners.json'
    favorite = json.loads(favorite_source.read_text(encoding='utf-8'))
    if favorite['clientSha256'] != CLIENT or favorite['unresolvedRvas']:
        raise ValueError('Original favorite resolver owner metadata is incomplete')
    for row in favorite['matches']:
        name = row['class']
        classes.setdefault(name, {'assembly': row['assembly'], 'methods': [],
                                 'isValueType': False, 'instanceSize': None,
                                 'valueSize': None, 'fields': []})['methods'].append(row)
    for name, cls in classes.items():
        for method in cls['methods']:
            rva = method['nativeRva']
            if rva is None:
                continue
            types = [p['type'] for p in method['parameters']]
            key = name + '::' + method['name'] + '(' + ','.join(types) + ')'
            methods[key] = {'assembly': cls['assembly'], 'className': name,
                            **method, 'entryHex': pe.get_data(rva, 16).hex()}
    return {'schemaVersion': 1, 'clientSha256': CLIENT,
            'sourceMetadata': {str(p): sha(p) for p in SOURCES + [favorite_source]},
            'moduleSha256': sha(HERE / 'native_build153.js'),
            'methods': methods,
            'layouts': {name: {key: row[key] for key in (
                'isValueType', 'instanceSize', 'valueSize', 'fields')}
                        for name, row in classes.items()},
            'battleRunPerformed': False, 'constructorRunPerformed': False,
            'scope': 'Exact153 original native constructors and entry byte binding; no runtime validation claim'}

if __name__ == '__main__':
    output = HERE / 'native-build-binding153.json'
    with output.open('x', encoding='utf-8') as sink:
        json.dump(build(), sink, indent=2)
        sink.write('\n')
    print(json.dumps({'binding': str(output), 'sha256': sha(output)}))
