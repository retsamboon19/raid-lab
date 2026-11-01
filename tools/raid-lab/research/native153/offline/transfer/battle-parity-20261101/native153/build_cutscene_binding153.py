"""Create compact immutable source binding for the original mechanical intro control."""
from pathlib import Path
import hashlib
import json
import struct

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    prefab_path = HERE/'practice-cutscene-control-source.json'
    prefab = json.loads(prefab_path.read_text())
    records = [(b, o) for b in prefab['bundles'] for o in b['objects']
               if o.get('class') == 'NK.Spot.Presentation.UI.CutSceneControl']
    if len(records) != 1:
        raise ValueError('One original CutSceneControl required')
    bundle, control = records[0]
    objects = {o['path_id']: o for o in bundle['objects']}
    references = {}
    for name, expected_type in [('_introCutScene', 'PlayableDirector'),
                                ('_introCutSceneUI', 'PlayableDirector'), ('_introCutSceneUIObject', 'GameObject')]:
        pointer = control['fields'][name]
        if pointer['m_FileID'] != 0 or pointer['m_PathID'] == 0 or objects[pointer['m_PathID']]['type'] != expected_type:
            raise ValueError('Original local serialized reference differs: '+name)
        references[name] = {'local': True, 'pathId': str(pointer['m_PathID']), 'type': expected_type}
    intro = objects[int(references['_introCutScene']['pathId'])]
    asset_ref = intro['fields']['m_PlayableAsset']
    if asset_ref['m_FileID'] != 0:
        raise ValueError('Original intro TimelineAsset must be local')
    asset = objects[asset_ref['m_PathID']]
    if asset.get('class') != 'UnityEngine.Timeline.TimelineAsset' or asset['fields']['m_DurationMode'] != 0:
        raise ValueError('Original clip-based TimelineAsset required')
    clips = []
    for reference in asset['fields']['m_Tracks']:
        if reference['m_FileID'] != 0:
            raise ValueError('Original local intro track required')
        for clip in objects[reference['m_PathID']]['fields'].get('m_Clips', []):
            clips.append({'start': clip['m_Start'], 'duration': clip['m_Duration'], 'name': clip['m_DisplayName']})
    duration = max(c['start']+c['duration'] for c in clips)
    expected_bits = struct.pack('<f', duration).hex()
    capture = HERE.parent/'capture/preload-phase-live3-22044/preload-phase-events.jsonl'
    if sha(capture) != '3483737b1e42eb9c5cc4c7a3711f1e20581a6ada4b093a18ac9440cab75e6ec4':
        raise ValueError('Finalized original loading/intro observation changed')
    rows = [json.loads(line).get('message', {}).get('payload', {}) for line in capture.read_text().splitlines()]
    observed = [r for r in rows if r.get('boundary') == 'OnStart' and r.get('phase') == 'enter']
    if len(observed) != 1 or observed[0]['managerState']['introDuration']['bitsLE'] != expected_bits or not observed[0]['waveContext']['useIntroCutScene']:
        raise ValueError('Original timeline-derived duration and native observation disagree')
    metadata_path = HERE.parent/'metadata/current153-cutscene-control2/mechanics-metadata.json'
    metadata = json.loads(metadata_path.read_text())
    if metadata['missingRoots']:
        raise ValueError('Exact original CutSceneControl metadata required')
    cls = next(c for c in metadata['classes'] if c['class'] == 'NK.Spot.Presentation.UI.CutSceneControl')
    sources = ['preload-cutscene-init-source.json', 'preload-cutscene-loading-source.json',
               'preload-cutscene-intro-source.json', 'preload-cutscene-release-source.json',
               'preload-cutscene-update-source.json', 'preload-cutscene-late-source.json',
               'preload-process-postload-source.json']
    binding = {
        'schemaVersion': 1, 'clientSha256': prefab['clientSha256'],
        'catalogKey': prefab['catalogKey'], 'selectedAsset': prefab['selectedAsset'],
        'parentGuid': prefab['parentGuid'], 'themeLayer': prefab['themeLayer'], 'themeKey': 0,
        'componentType': cls['class'], 'fieldLayouts': cls['fields'],
        'originalMethodRvas': {m['name']: m['nativeRva'] for m in cls['methods']},
        'serializedReferences': references, 'serializedSkipSpeed': control['fields']['_skipSpeed'],
        'serializedModeBoardCount': len(control['fields']['_modeBoard']),
        'introTimeline': {'name': asset['fields']['m_Name'], 'clipBased': True, 'clips': clips},
        'directorDurationGetter': {'rva': 0x0855E980, 'type': 'UnityEngine.Playables.PlayableDirector', 'returns': 'System.Double'},
        'expectedIntroDurationFloat32BitsLE': expected_bits, 'expectedUseIntroCutScene': True,
        'managerIntroField': {'name': '<IntroCutSceneDuration>k__BackingField', 'offset': 0xB0, 'type': 'System.Single'},
        'waveGetter': {'rva': 0x019598B0, 'name': 'get_Instance', 'returns': 'NK.Spot.Context.Wave.WaveContext',
                       'slotRva': 0x0B0B6088, 'slotKind': 'MethodInfo'},
        'waveIntroField': {'name': '<UseIntroCutScene>k__BackingField', 'offset': 0x98, 'type': 'System.Boolean'},
        'sourceEvidence': {str(prefab_path.relative_to(HERE)): sha(prefab_path),
                           str(metadata_path.relative_to(HERE.parent)): sha(metadata_path),
                           'startup-gate-metadata2/report.json': sha(HERE/'startup-gate-metadata2/report.json'),
                           **{name: sha(HERE/name) for name in sources}},
        'originalObservation': {'captureSha256': sha(capture), 'sequence': observed[0]['sequence'],
                                'status': 'read_only_expected_value_not_replay_input'},
        'scope': 'Original serialized intro control restores native duration writer and coroutine path; expected values are verification only',
        'combatOutputsUsedAsInputs': False, 'nativeLoaded': False,
    }
    output = HERE/'practice-cutscene-control-binding.json'
    with output.open('x', encoding='utf-8') as target:
        json.dump(binding, target, indent=2)
        target.write('\n')
    print(json.dumps({'path': str(output), 'sha256': sha(output), 'expectedIntroBits': expected_bits}))


if __name__ == '__main__':
    main()
