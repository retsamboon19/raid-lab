"""Archive a completed scene probe and separate exit success from mechanic success."""
import argparse
import hashlib
import json
import re
from pathlib import Path
import shutil

ROOT = Path(__file__).resolve().parents[3]
SANDBOX = ROOT / 'tools/raid-lab/private/native-player-20261008a'
GAME = SANDBOX / 'NIKKE/NIKKE/game'


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def finalize(trial):
    output = SANDBOX / f'probe-output-{trial}'
    run = json.loads((output / 'native-player-run.json').read_text())
    first_archive = not (output/'scene-verification.json').exists()
    files = {
        'scene-events.jsonl': GAME / 'scene-events.jsonl',
        'scene-probe.js': GAME / 'NKAB/dist/scene-probe.js',
        'actual-player.log': SANDBOX / 'profile/AppData/LocalLow/com.proximabeta/NIKKE/Player.log',
        'resource-chunks.json': SANDBOX / 'resource-chunks.json',
        'bootstrap-resources.json': SANDBOX / 'bootstrap-resources.json',
        'dp-character-resource-chunks.json': SANDBOX / 'dp-character-resource-chunks.json',
        'localization-resources.json': SANDBOX / 'localization-resources.json',
        'local-localization-fixture.json': SANDBOX / 'local-localization-fixture.json',
        'headless-bootstrap.log': GAME / 'headless-bootstrap.log',
        'headless-native-exceptions.log': GAME / 'headless-native-exceptions.log',
        'player.log': output / 'player.log',
    }
    # The scratch profile survives trials; its last Player.log may predate a
    # failed bootstrap. Preserve the distinction instead of attributing old
    # locale/resource errors to a new mechanics diagnostic.
    run_record_path = output / 'native-player-run.json'
    run_start = run_record_path.stat().st_mtime - run['elapsed_seconds']
    profile_log = files['actual-player.log'] if first_archive else output / 'actual-player.log'
    profile_log_fresh = profile_log.is_file() and profile_log.stat().st_mtime >= run_start - 2
    if first_archive and not profile_log_fresh:
        files.pop('actual-player.log')
    for name, source in files.items():
        target = output / name
        if target.exists():
            continue  # An earlier immutable archive is authoritative.
        if not first_archive:
            continue  # Re-evaluation must never import a later run's resources.
        if source.is_file():
            shutil.copy2(source, target)
    events = [json.loads(line) for line in (output/'scene-events.jsonl').read_text().splitlines()]
    phases = {event['phase'] for event in events}
    loads = [event for event in events if event.get('status') == 'native_skill_resource_result']
    errors = [event for event in events if event.get('status') in ('method_error','probe_error','first_failure',
              'original_simulation_error_callback','finish_callback_capture_error','error_callback_capture_error',
              'original_load_did_not_complete','original_battle_limit_reached',
              'original_geometry_load_did_not_complete','original_invalid_encounter_result')
              or event['phase'] in ('scene_error','table_error','poll_error','probe_deadline','bridge_error','native_exception')]
    if run['returncode'] != 0 or run.get('timed_out'):
        errors.append({'phase': 'native_process_error', 'returncode': run['returncode'],
                       'timed_out': bool(run.get('timed_out')),
                       'detail': 'Private player ended abnormally; no completed battle is accepted'})
    skill_passed = bool(loads) and all(row.get('skills') and all(
        skill.get('created') and skill.get('resourcePresent') is True for skill in row['skills']) for row in loads)
    current_log = output / 'player.log'
    player_log=(current_log.read_text(errors='replace') if current_log.is_file() else
                (output/'actual-player.log').read_text(errors='replace') if (
        profile_log_fresh and (output/'actual-player.log').is_file()) else '')
    asset_errors=[line for line in player_log.splitlines() if
        ('decompression failed' in line or re.match(r'^(?:Rethrow as )?[\w.]+Exception\s*:',line) or
         'No Location found for Key=' in line)]
    errors.extend({'phase':'native_asset_error','detail':line} for line in dict.fromkeys(asset_errors))
    mechanics = [event for event in events if event['phase'].startswith('mechanics_')]
    terminal = [event for event in mechanics if event.get('status') == 'original_terminal_result']
    complete = (len(terminal) == 1 and not errors and run['returncode'] == 0 and
                'quit_requested' in phases and terminal[0].get('completeBattle') is True and
                terminal[0].get('originalResult') is True and
                terminal[0].get('resultCaptured') is True and
                terminal[0].get('advancedTicks', 0) > 0 and
                str(terminal[0].get('targetMaxHp', '')).isdigit() and
                int(terminal[0]['targetMaxHp']) > 0 and
                bool(terminal[0].get('rounds')))
    report = dict(schema_version=2,trial=trial,scene_object_created='real_scene_object_created' in phases,
                  current_tables_loaded='original_tables_loaded' in phases,
                  dp_catalog_loaded=any(row['phase']=='dp_catalog_result' and row.get('status')=='Succeeded' for row in events),
                  original_skill_resources_loaded=skill_passed,errors=errors,
                  battle_observations=[event for event in events if event['phase']=='battle_probe'],
                  mechanics_observations=mechanics,
                  clean_quit_observed=run['returncode']==0 and 'quit_requested' in phases,
                  complete_battle_executed=complete,full_accuracy_verified=False,
                  profile_player_log_fresh=profile_log_fresh,
                  artifacts={name:sha(output/name) for name in files if (output/name).is_file()})
    (output/'scene-verification.json').write_text(json.dumps(report,indent=2))
    summary={key:value for key,value in report.items() if key not in ('battle_observations','mechanics_observations','artifacts','errors')}
    summary['error_count']=len(errors)
    summary['errors']=[{'status':row.get('status',row['phase']),
        'detail':str(row.get('error',row.get('detail','')))[:500]} for row in errors[:3]]
    # One original load can fail concurrently for several resources. Preserve
    # the compact summary while exposing every distinct requested bundle up to
    # this bound, instead of encouraging a retry for just the first exception.
    failed_bundles=sorted({key for row in errors for key in re.findall(
        r"key='([^']+\.bundle)'", str(row.get('error',row.get('detail',''))))})
    if failed_bundles:
        summary['failed_bundle_keys']=failed_bundles[:32]
        summary['failed_bundle_keys_truncated']=len(failed_bundles)>32
    print(json.dumps(summary,indent=2))
    return report


if __name__ == '__main__':
    parser=argparse.ArgumentParser();parser.add_argument('trial',type=int)
    finalize(parser.parse_args().trial)
