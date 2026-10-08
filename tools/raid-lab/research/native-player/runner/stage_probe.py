"""Stage only the diagnostic module, without the installed gameplay hooks."""
import hashlib
import json
from pathlib import Path
import shutil
import sys
from mechanics_request import load_request, encounter_profile

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
SANDBOX = ROOT / 'tools/raid-lab/private/native-player-20261008a'
GAME = SANDBOX / 'NIKKE/NIKKE/game'
sys.path.insert(0,str(ROOT/'event-selector/chainsaw-man/catalog-repair/hook-testing'))
from build_bundle import parse, DELIMITER


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


scenario = sys.argv[2] if len(sys.argv)>2 else 'skill'
wall_frame_rate = int(sys.argv[3]) if len(sys.argv)>3 else -1
if wall_frame_rate != -1 and (scenario != 'mechanics' or not 160 <= wall_frame_rate <= 1000):
    raise ValueError('Invalid bounded mechanics wall frame rate')
if scenario not in ('skill', 'battle', 'battle-normal', 'battle-scene', 'mechanics'):
    raise ValueError('Unknown scenario')
request = request_hash = None
profile = None
geometry_source = HERE / 'mechanics-geometry-source-v2.json'
trace_mode = sys.argv[5] if len(sys.argv) > 5 else 'diagnostics'
if trace_mode not in ('diagnostics', 'results'):
    raise ValueError('Unsupported mechanics trace mode')
control_mode = sys.argv[6] if len(sys.argv) > 6 else 'original'
if control_mode not in ('original', 'observe', 'probe', 'kraken-qte', 'kraken-cover-probe', 'kraken-tactical', 'boss-observe', 'boss-tactical'):
    raise ValueError('Unsupported mechanics control mode')
if scenario == 'mechanics':
    request_path = Path(sys.argv[4]) if len(sys.argv) > 4 else HERE/'mechanics_request_fixture.json'
    request, request_hash = load_request(request_path)
    profile = encounter_profile(request)
    if profile is not None and profile['productId'] != 'anomaly-kraken':
        if profile['productId'] != 'anomaly-mirror-container':
            raise ValueError('Registered encounter still needs source-bound mechanical asset staging')
        geometry_source = HERE / 'mirror-geometry-source.json'
        if sha(geometry_source) != 'd1c334def34ae73ed4344c4f79e1f00431f35df49e1fc7eefc562b0c1095f306':
            raise ValueError('Mirror mechanical geometry source changed')
        geometry = json.loads(geometry_source.read_text(encoding='utf-8'))
        receipt = json.loads((SANDBOX/'mirror-asset-staging-receipt.json').read_text(encoding='utf-8'))
        if receipt['source_sha256'] != sha(geometry_source) or \
                geometry['profile']['wave_id'] != request['encounter']['waveId'] or \
                geometry['wave_current_row']['BackgroundName'] != profile['wave']['backgroundKey'] or \
                geometry['wave_current_row']['TargetList'] != profile['wave']['targetMonsterIds']:
            raise ValueError('Mirror source/staging/profile binding mismatch')
for name in ('nikkeBase.dll', 'OfflineNetwork.dll'):
    build = HERE / 'build'
    if scenario == 'mechanics' and name == 'nikkeBase.dll':
        build /= 'headless'
    shutil.copy2(build / name, GAME / name)
events_path = GAME / 'scene-events.jsonl'
if events_path.exists():
    previous = json.loads((SANDBOX/'sandbox-player.json').read_text())
    archive = Path(previous['output_dir']).resolve()
    if not archive.is_relative_to(SANDBOX) or not (archive/'native-player-run.json').is_file():
        raise RuntimeError('Previous player run must be closed and archived before restaging')
    if not (archive/'scene-events.jsonl').is_file() or sha(archive/'scene-events.jsonl') != sha(events_path):
        raise RuntimeError('Archive the previous scene events before restaging')
    events_path.unlink()  # Exact bytes remain in the verified immutable trial archive.
for diagnostic_name in ('headless-bootstrap.log', 'headless-native-exceptions.log'):
    bootstrap_log = GAME / diagnostic_name
    if not bootstrap_log.exists():
        continue
    previous = json.loads((SANDBOX/'sandbox-player.json').read_text())
    archive = Path(previous['output_dir']).resolve()
    if not archive.is_relative_to(SANDBOX) or not (archive/'native-player-run.json').is_file():
        raise RuntimeError('Previous headless bootstrap must be archived before restaging')
    saved = archive / bootstrap_log.name
    if not saved.exists():
        shutil.copy2(bootstrap_log, saved)
    if sha(saved) != sha(bootstrap_log):
        raise RuntimeError('Headless bootstrap archive mismatch')
    bootstrap_log.unlink()
headers, modules = parse((ROOT/'NIKKE/NIKKE/game/NKAB/dist/hi_shiftup_dont_mind_me.js').read_bytes())
table_archive = SANDBOX / 'current-tables.zip'
assert sha(table_archive) == sha(ROOT / 'tools/raid-lab/private/native-current-tables-2df7134a.zip')
driver = 'headless_driver.js' if scenario == 'mechanics' else 'scene_probe.js'
scene_source = (HERE / driver).read_text().replace('__TABLE_ARCHIVE__', json.dumps(str(table_archive)))
scene_source = scene_source.replace('__SCRATCH_PROFILE__', json.dumps(str(SANDBOX/'profile')))
entry = {'skill':'runSkillResourceProbe(record, finish)',
         'battle':'runBattleProbe(record, finish, true)',
         'battle-normal':"runBattleProbe(record, finish, true, 'normal')",
         'battle-scene':"runBattleProbe(record, finish, true, 'scene')",
         'mechanics':'runMechanicsLifecycleProbe(record, finish)'}[scenario]
scene_source = scene_source.replace('__RUN_SCENARIO__', entry)
scene_source = scene_source.replace('__LOAD_DP__', 'true' if scenario in ('battle-normal','battle-scene') else 'false')
sources = (['mechanics_bare_stats_probe.js', 'mechanics_snapshot_probe.js', 'mechanics_fixture.js', 'mechanics_settings.js', 'mechanics_monster_headless.js',
            'mechanics_spawn_observer.js', 'mechanics_fx_cleanup_parent.js', 'mechanics_audio_boundary.js', 'mechanics_geometry_runtime.js',
            'mechanics_aim_binding.js', 'mechanics_result_capture.js', 'mechanics_damage_trace.js',
            'mechanics_range_trace.js', 'mechanics_camera_observer.js',
            'mechanics_projectile_observer.js',
            'mechanics_skill_event_observer.js', 'mechanics_skill_gate_observer.js',
            'mechanics_startup_state_observer.js',
            'mechanics_tactical_observer.js', 'mechanics_threat_observer.js', 'mechanics_virtual_pointer.js',
            'mechanics_tactical_actions.js', 'mechanics_kraken_qte_policy.js',
            'mechanics_kraken_cover_probe.js', 'mechanics_qte_policy.js',
            'mechanics_cover_policy.js', 'mechanics_tactical_controller.js',
            'mechanics_tick_runner.js', 'mechanics_frame_scheduler.js', 'mechanics_clock_observer.js', 'mechanics_probe.js'] if scenario == 'mechanics' else
           ['skill_probe.js'] if scenario == 'skill' else ['battle_observer.js', 'battle_probe.js'])
if scenario == 'mechanics':
    scene_source += ('\nglobalThis.MECHANICS_GEOMETRY_SOURCE=' + geometry_source.read_text() +
                     ';\nglobalThis.MECHANICS_GEOMETRY_SOURCE_SHA256=' +
                      json.dumps(sha(geometry_source)) + ';\n')
    scene_source += '\nglobalThis.MECHANICS_WALL_FRAME_RATE=' + str(wall_frame_rate) + ';\n'
    scene_source += '\nglobalThis.MECHANICS_REQUEST=' + json.dumps(request, sort_keys=True) + ';\n'
    scene_source += '\nglobalThis.MECHANICS_REQUEST_SHA256=' + json.dumps(request_hash) + ';\n'
    if request['schemaVersion'] == 2:
        from mechanics_encounters import REGISTRY
        scene_source += '\nglobalThis.MECHANICS_ENCOUNTER_PROFILE=' + json.dumps(profile, sort_keys=True) + ';\n'
        scene_source += '\nglobalThis.MECHANICS_ENCOUNTER_REGISTRY_SHA256=' + json.dumps(sha(REGISTRY)) + ';\n'
    scene_source += '\nglobalThis.MECHANICS_TRACE_MODE=' + json.dumps(trace_mode) + ';\n'
    scene_source += '\nglobalThis.MECHANICS_CONTROL_MODE=' + json.dumps(control_mode) + ';\n'
modules[1] = (scene_source + '\n' + '\n'.join((HERE / name).read_text() for name in sources)).encode()
headers[2] = f'{len(modules[1])} /src/nmm_030.js'
out = GAME/'NKAB/dist/scene-probe.js'
out.parent.mkdir(parents=True, exist_ok=True)
out.write_bytes('\n'.join(headers).encode()+DELIMITER+DELIMITER.join(modules))
(GAME/'frida-gadget.config').write_text(json.dumps({'interaction':{'type':'script','path':'NKAB/dist/scene-probe.js'}}))
config = dict(schema_version=1,sandbox_root=str(SANDBOX),game_executable=str(GAME/'nikke.exe'),
              working_directory=str(GAME),scratch_root=str(SANDBOX/'profile'),
              output_dir=str(SANDBOX/('probe-output-'+(sys.argv[1] if len(sys.argv)>1 else '3'))),max_seconds=60,
              args=['-batchmode', '-nographics'] if scenario == 'mechanics' else [],
              expected_files={name:dict(path=str(GAME/name),sha256=sha(GAME/name)) for name in
                  ('nikke.exe','UnityPlayer.dll','GameAssembly.dll','nikkeBase.dll','OfflineNetwork.dll')},
              bootstrap_receipt=str(SANDBOX/'bootstrap-receipt.json'),network_receipt=str(SANDBOX/'network-receipt.json'))
config['diagnostic_files']={name:dict(path=str(GAME/name),sha256=sha(GAME/name)) for name in
                           ('NKAB/dist/scene-probe.js','frida-gadget.config','d3d11.dll','frida-gadget.dll')}
(SANDBOX/'sandbox-player.json').write_text(json.dumps(config,indent=2))
bootstrap=dict(schema_version=1,mode='unity_player_bootstrap',sandbox_root=str(SANDBOX),private_desktop_guard=True,
               artifacts={'nikkeBase.dll':sha(GAME/'nikkeBase.dll')},
               source_sha256=sha(HERE/('HeadlessUnityEntry.cpp' if scenario == 'mechanics' else 'UnityEntry.cpp')))
network=dict(schema_version=1,mode='deny_all',sandbox_root=str(SANDBOX),registry_mode='sandbox',known_folder_mode='sandbox',
             self_test_passed=True,artifacts={'OfflineNetwork.dll':sha(GAME/'OfflineNetwork.dll')},
             source_sha256=sha(HERE/'OfflineNetwork.cpp'),
             self_test='guard-test-NikkeCatalogProbe_8a97095c87244370a10fd401fe74c0bd.json')
test=json.loads((SANDBOX/network['self_test']).read_text())
assert test['returncode']==0
assert test['artifact_sha256']==sha(GAME/'OfflineNetwork.dll')
(SANDBOX/'bootstrap-receipt.json').write_text(json.dumps(bootstrap,indent=2))
(SANDBOX/'network-receipt.json').write_text(json.dumps(network,indent=2))
print(json.dumps({'config':str(SANDBOX/'sandbox-player.json'),'gadget_sha256':sha(out)}))
