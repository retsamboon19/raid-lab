"""Extract semantic practice transport fields; never retain process pointers."""
from pathlib import Path
import argparse
import hashlib
import importlib.util
import json

HERE = Path(__file__).resolve().parent
BASE = HERE.parents[1]
SPEC = importlib.util.spec_from_file_location('snapshots', HERE / 'extract_snapshot_inputs.py')
snapshots = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(snapshots)
g = snapshots.graphs


def extract(capture, metadata_path, run=1):
    groups, incomplete = g.read_capture(capture)
    if incomplete:
        raise ValueError('Final complete capture required')
    group = groups[run - 1]
    source = next(row for row in group if 'OnStart' in row['boundary'] and row['phase'] == 'enter')
    source_graph = g.Graph(source['value'])
    transporter = source['value']['transporter']
    metadata_bytes = metadata_path.read_bytes()
    metadata = json.loads(metadata_bytes)
    cls = next(c for c in metadata['classes'] if c['class'] == 'NK.Spot.Data.NKSpotDataTransporter')
    if cls['valueSize'] != 376:
        raise ValueError('Exact current376-byte transporter required')
    value_types = {c['class']: c for c in metadata.get('embeddedValueTypes', [])}
    value_types.update({c['class']: c for c in metadata['classes'] if c['isValueType']})
    primitive = {'System.Int32': ('int32', 4), 'System.Boolean': ('bool', 1),
                 'System.Single': ('float32', 4), 'System.Int64': ('int64', 8)}
    fields, required_native_bindings = [], []
    raw = bytes.fromhex(transporter['rawHex'])
    for field in cls['fields']:
        if field['flags'] & 0x10:
            continue
        name, type_name = field['name'], field['type']
        value = source_graph.f(transporter, name)
        entry = dict(field)
        entry['sourceNativeFieldOffset'] = field['offset']
        setter_name = 'set_' + name[1:name.index('>')] if name.startswith('<') else 'set_WaveId' if name == '_waveId' else None
        setter = next((m for m in cls['methods'] if m['name'] == setter_name), None)
        entry['setter'] = setter
        compound_size = value.get('$valueSize') if isinstance(value, dict) else None
        if compound_size is None and type_name.startswith('System.Nullable<'):
            argument = type_name[len('System.Nullable<'):-1]
            layout = next((item for item in metadata.get('embeddedValueTypes', [])
                           if item['class'] == 'System.Nullable`1' and
                           any(f['name'] == 'value' and f['type'] == argument for f in item['fields'])), None)
            compound_size = layout['valueSize'] if layout else None
        if name == 'MyTeamData':
            entry.update(kind='reconstructedOriginalTeam', sourceValuePresent=value is not None)
        elif type_name in primitive:
            kind, size = primitive[type_name]
            if isinstance(value, dict) and '$excluded' in value:
                payload = raw[field['offset'] - 16:field['offset'] - 16 + size]
                if any(payload):
                    raise ValueError('Excluded nonzero field is unsupported: ' + name)
                value = False if kind == 'bool' else 0
                entry['zeroValueProvenFromCapturedRawPayload'] = True
            entry.update(kind=kind, value=g.scalar(value))
            if kind == 'float32':
                entry['bitsLE'] = value['bitsLE']
        elif type_name in value_types or compound_size is not None:
            size = compound_size if compound_size is not None else value_types[type_name]['valueSize']
            payload = raw[field['offset'] - 16:field['offset'] - 16 + size]
            if isinstance(value, dict) and any(k.endswith('::value__') for k in value.get('fields', {})):
                entry.update(kind='enum32', value=g.scalar(value), valueSize=size)
            elif not any(payload):
                entry.update(kind='zeroValueType', valueSize=size, rawHex='00' * size,
                             zeroValueProvenFromCapturedRawPayload=True)
            elif type_name == 'NK.Common.StatValue':
                entry.update(kind='originalValueType', valueSize=size, rawHex=payload.hex())
            else:
                # Contains live native strings/delegates: rebind a fresh original
                # private owner; never write these captured raw pointer bytes.
                entry.update(kind='nativeOwnerBinding', valueSize=size)
                entry['semanticTuple'] = {key.split('::')[-1]: val if isinstance(val, (str, bool)) or val is None else
                                         {'nativeType': val.get('$type'), 'requiredNonNull': True}
                                         for key, val in value.get('fields', {}).items()}
                required_native_bindings.append(name)
        elif value is None:
            entry.update(kind='nullReference')
        elif type_name == 'System.String' and isinstance(value, str):
            entry.update(kind='string', value=value)
        elif isinstance(value, dict) and '$excluded' in value and name.startswith('<Multiplay'):
            payload = raw[field['offset'] - 16:field['offset'] - 16 + 8]
            if any(payload):
                raise ValueError('Excluded nonnull multiplayer reference unsupported: ' + name)
            entry.update(kind='nullReference', zeroValueProvenFromCapturedRawPayload=True)
        else:
            entry.update(kind='nativeOwnerBinding', requiredNativeType=type_name)
            required_native_bindings.append(name)
        fields.append(entry)
    team_entry = next(row for row in group if 'CreateSpotTeamData@' in row['boundary'] and row['phase'] == 'enter')
    if team_entry['value']['buffInfos'] is not None or type(team_entry['value']['statIncrease']) is not int:
        raise ValueError('This exact trial fixture supports captured null buffs and original scalar stat increase only')
    return {'schemaVersion': 1, 'scope': 'Original semantic native transport reconstruction only',
            'clientSha256': metadata['clientSha256'], 'captureSha256': hashlib.sha256(capture.read_bytes()).hexdigest(),
            'metadataSha256': hashlib.sha256(metadata_bytes).hexdigest(), 'runIndex': run,
            'sourceOnStart': {'sequence': source['sequence'], 'sha256': source['completeLineSha256']},
            'transporterValueSize': 376, 'fields': fields,
            'requiredFreshOriginalNativeOwnerBindings': required_native_bindings,
            'teamConversion': {'buffInfos': None, 'statIncrease': team_entry['value']['statIncrease'],
                               'methodRva': 0x06dad210, 'sourceRowSha256': team_entry['completeLineSha256']},
            'wave': {'tableId': source_graph.f(transporter, '_waveId'),
                     'requiredNativeType': 'StaticData.StaticDataLayer.StaticInfo.WaveDataStaticInfo'},
            'completeReplayInputVerified': False}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--capture', type=Path, required=True)
    parser.add_argument('--metadata', type=Path, default=BASE / 'metadata/current153-run3/mechanics-metadata.json')
    parser.add_argument('--run', type=int, default=1)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    result = extract(args.capture, args.metadata, args.run)
    with args.output.open('x', encoding='utf-8') as stream:
        json.dump(result, stream, indent=2)
        stream.write('\n')
    print(json.dumps({'fieldCount': len(result['fields']),
                      'requiredNativeOwnerBindings': result['requiredFreshOriginalNativeOwnerBindings']}))


if __name__ == '__main__':
    main()
