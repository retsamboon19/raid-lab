"""Extract original snapshot constructor inputs; verification output is separate."""
from pathlib import Path
import argparse
import hashlib
import importlib.util
import json

HERE = Path(__file__).resolve().parent
BASE = HERE.parents[1]
SPEC = importlib.util.spec_from_file_location('reference_graph', BASE / 'results/compare_references.py')
graphs = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(graphs)


def sha(data):
    return hashlib.sha256(data).hexdigest()


def raw(node, size, label):
    if not isinstance(node, dict) or node.get('$valueSize') != size:
        raise ValueError(label + ' value size mismatch')
    data = bytes.fromhex(node['rawHex'])
    if len(data) != size:
        raise ValueError(label + ' raw payload mismatch')
    return node['rawHex']


def extract(capture, run_index=1):
    groups, incomplete = graphs.read_capture(capture)
    if incomplete or not 1 <= run_index <= len(groups):
        raise ValueError('Complete requested original capture group required')
    group = groups[run_index - 1]
    ctor = group[0]
    cg = graphs.Graph(ctor['value'])
    ordered = cg.items(ctor['value']['snapshots'])
    ordered_csns = [str(graphs.scalar(cg.f(cg.f(snapshot, '<CharacterInfo>k__BackingField'), '_serialNumber')))
                    for snapshot in ordered]
    if len(ordered_csns) != 5 or len(set(ordered_csns)) != 5:
        raise ValueError('Five unique original logical snapshot slots required')
    sources = [row for row in group if 'CreateSpotCharacterData' in row['boundary'] and row['phase'] == 'enter']
    converted = [row for row in group if 'CreateSpotCharacterData' in row['boundary'] and row['phase'] == 'leave']
    if len(sources) != 5 or len(converted) != 5 or any(row['errors'] for row in sources + converted):
        raise ValueError('Five complete original source/conversion pairs required')
    inputs, expected = [], []
    for source in sources:
        graph = graphs.Graph(source['value'])
        snapshot = source['value']['snapshots']
        short = graphs.normalized_snapshot(source)
        csn = short['csn']
        target = next(row for row in converted if row['callId'] == source['callId'])
        native = graphs.normalized_native_build(target)
        if native['csn'] != csn:
            raise ValueError('Original source/result CSN mismatch')
        character_record = graph.f(graph.f(snapshot, '<CharacterStaticInfo>k__BackingField'), '_record')
        skill_disable = graph.f(snapshot, '<SkillDisableStatus>k__BackingField')
        none_hex = raw(skill_disable, 16, 'Option<SkillDisableStatus>')
        if set(bytes.fromhex(none_hex)) - {0}:
            raise ValueError('Nonempty skill-disable Option not supported by this exact trial replayer')
        override = graph.f(snapshot, '_override')
        for key in ('UseBurstSkill', 'ChangeBurstStep'):
            if graphs.field(graph.f(override, '<' + key + '>k__BackingField'), 'hasValue') is not False:
                raise ValueError('Nonempty original burst override needs a separate native reconstruction path')
        skills = []
        for label in ('Skill1', 'Skill2', 'SkillBurst'):
            info = graph.f(snapshot, '<' + label + 'Info>k__BackingField')
            favorite = graph.f(snapshot, '<Is' + label + 'FavoriteItem>k__BackingField')
            if type(favorite) is not bool:
                raise ValueError('Exact favorite-skill flag required')
            table_type = graph.f(snapshot, '<' + label + 'TableType>k__BackingField') if label != 'SkillBurst' else None
            skills.append({'role': label, 'level': graph.f(snapshot, '<' + label + 'Level>k__BackingField'),
                           'favoriteOverride': favorite, 'skillInfoTableId': graph.f(info, '<TableId>k__BackingField'),
                           'tableType': graphs.scalar(table_type) if table_type is not None else None})
        entry = {'slot': ordered_csns.index(csn) + 1, 'sourceCsn': csn,
                 'characterTableId': graph.f(character_record, '<Id>k__BackingField'),
                 'sourceNameCode': graph.f(character_record, '<Name_code>k__BackingField'),
                 'characterInfoRawHex': raw(graph.f(snapshot, '<CharacterInfo>k__BackingField'), 16, 'NKCharacterInfo'),
                 'levelObscuredIntRawHex': raw(graph.f(snapshot, '<Level>k__BackingField'), 20, 'ObscuredInt Level'),
                 'characterStatDataRawHex': raw(graph.f(snapshot, '<Status>k__BackingField'), 240, 'CharacterStatData'),
                 'costumeTableId': graphs.scalar(graph.f(snapshot, '<CostumeTableId>k__BackingField')),
                 'skills': skills, 'equipmentAndCube': short['equipmentAndCube'],
                 'itemStateEffectTids': short['itemStateEffectTids'],
                 'noneSkillDisableStatusRawHex': none_hex,
                 'overrideElements': [graphs.scalar(value) for value in graph.items(graph.f(snapshot, 'OverrideElements'))],
                 'emptyBurstOverrides': True,
                 'sourceRow': {'sequence': source['sequence'], 'callId': source['callId'], 'sha256': source['completeLineSha256']}}
        inputs.append(entry)
        expected.append({'slot': entry['slot'], 'sourceCsn': csn,
                         'nativeConversion': {key: value for key, value in native.items() if key not in ('sequence', 'readErrors')},
                         'sourceRow': {'sequence': target['sequence'], 'callId': target['callId'], 'sha256': target['completeLineSha256']}})
    inputs.sort(key=lambda value: value['slot'])
    expected.sort(key=lambda value: value['slot'])
    start = next(row for row in group if 'OnStart' in row['boundary'] and row['phase'] == 'enter')
    sg = graphs.Graph(start['value'])
    return ({'schemaVersion': 1, 'scope': 'Original captured snapshot constructor inputs; no expected converted or battle values',
             'clientSha256': 'd39896d3770888039c728a1908448c3db5efa7cdf874c90d56f46d8d566428d2',
             'capturePath': str(capture.resolve()), 'captureSha256': sha(capture.read_bytes()), 'runIndex': run_index,
             'characters': inputs,
             'nativeEncounterReferenceOnly': {'waveId': sg.f(start['value']['transporter'], '_waveId'),
                                             'seed': sg.f(start['value']['transporter'], '<RandomSeed>k__BackingField')},
             'missingRawInventoryProvenance': ['collection inventory identity/level', 'favorite inventory identity/level', 'rolled OL option IDs/numeric values'],
             'completeReplayInputVerified': False},
            {'schemaVersion': 1, 'scope': 'Independent original native conversion verification only; never applied as constructor inputs',
             'captureSha256': sha(capture.read_bytes()), 'runIndex': run_index, 'characters': expected,
             'battleOutputsIncluded': False})


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--capture', type=Path, required=True)
    parser.add_argument('--run', type=int, default=1)
    parser.add_argument('--output-directory', type=Path, required=True)
    args = parser.parse_args()
    inputs, expected = extract(args.capture, args.run)
    args.output_directory.mkdir(parents=True, exist_ok=False)
    for name, value in [('native-replay-input.json', inputs), ('native-conversion-expected.json', expected)]:
        with (args.output_directory / name).open('x', encoding='utf-8') as stream:
            json.dump(value, stream, indent=2)
            stream.write('\n')
    print(json.dumps({'directory': str(args.output_directory), 'characters': len(inputs['characters']),
                      'captureSha256': inputs['captureSha256'], 'expectedKeptSeparate': True}))


if __name__ == '__main__':
    main()
