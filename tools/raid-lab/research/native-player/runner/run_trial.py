"""Stage, bind, run and archive one fresh bounded private-player trial."""
import argparse
import hashlib
import json
from pathlib import Path
import subprocess
import sys

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent))
import native_player_host as host
from finalize_trial import finalize
from mechanics_request import load_request, verify_request_events


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('trial', type=int)
    parser.add_argument('scenario', choices=['skill', 'battle', 'battle-normal', 'battle-scene', 'mechanics'])
    parser.add_argument('--wall-frame-rate', type=int, default=-1,
                        help='Mechanics-only wall-cadence diagnostic; simulation delta stays fixed')
    parser.add_argument('--request', type=Path,
                        help='Explicit diagnostic mechanics request; defaults to retained baseline fixture')
    parser.add_argument('--trace-mode', choices=('diagnostics', 'results'), default='diagnostics',
                        help='Results mode omits passive per-hit, pose and camera diagnostics')
    parser.add_argument('--control-mode', choices=('original', 'observe', 'probe', 'kraken-qte', 'kraken-cover-probe', 'kraken-tactical', 'boss-observe', 'boss-tactical'), default='original',
                        help='Private native autoplay: unchanged original, passive observation, or bounded input proof')
    parser.add_argument('--replay-trial', type=int,
                        help='Replay an archived exact mechanics bundle with its archived request')
    args = parser.parse_args()
    if args.wall_frame_rate != -1 and not 160 <= args.wall_frame_rate <= 1000:
        parser.error('Wall frame rate must be -1 or 160..1000 within the private host bound')
    if args.scenario != 'mechanics' and args.wall_frame_rate != -1:
        parser.error('Wall frame-rate control is mechanics-only')
    if args.request is not None and args.scenario != 'mechanics':
        parser.error('Explicit request is mechanics-only')
    if args.scenario != 'mechanics' and args.trace_mode != 'diagnostics':
        parser.error('Results trace mode is mechanics-only')
    if args.scenario != 'mechanics' and args.control_mode != 'original':
        parser.error('Tactical control is mechanics-only')
    sandbox = HERE.parent / 'private/native-player-20261008a'
    replay = None
    if args.replay_trial is not None:
        if args.scenario != 'mechanics' or args.request is not None or \
                args.wall_frame_rate != -1 or args.trace_mode != 'diagnostics' or args.control_mode != 'original':
            parser.error('Archived replay uses its own mechanics request and timing/trace settings')
        source = sandbox / f'probe-output-{args.replay_trial}'
        source_plan = json.loads((sandbox/f'plan-{args.replay_trial}.json').read_text())
        source_receipt = json.loads((source/'mechanics-request-receipt.json').read_text())
        bundle = (source/'scene-probe.js').read_bytes()
        bundle_hash = hashlib.sha256(bundle).hexdigest()
        if bundle_hash != source_plan['diagnostic_files']['NKAB/dist/scene-probe.js']:
            raise RuntimeError('Archived replay bundle no longer matches its frozen plan')
        args.request = source/'mechanics-request.json'
        replay = {'source_trial': args.replay_trial,
                  'source_plan_sha256': source_plan['plan_sha256'],
                  'source_bundle_sha256': bundle_hash,
                  'source_request_sha256': source_receipt['request_sha256'],
                  'scope': 'Exact code/input replay; scratch profile is not rolled back'}
    request_path = (args.request or HERE/'mechanics_request_fixture.json').resolve()
    request = digest = None
    if args.scenario == 'mechanics':
        request, digest = load_request(request_path)
    if replay and digest != replay['source_request_sha256']:
        raise RuntimeError('Archived replay request hash mismatch')
    output = sandbox / f'probe-output-{args.trial}'
    if output.exists():
        raise RuntimeError('Trial output must be fresh')
    stage_args = [sys.executable, str(HERE/'stage_probe.py'), str(args.trial), args.scenario,
                  str(args.wall_frame_rate)]
    if request is not None:
        stage_args.extend([str(request_path), args.trace_mode, args.control_mode])
    subprocess.run(stage_args, check=True)
    config = sandbox/'sandbox-player.json'
    if replay:
        staged = json.loads(config.read_text())
        for name, expected in source_plan['expected_files'].items():
            if staged['expected_files'][name]['sha256'] != expected:
                raise RuntimeError('Archived replay original/native host binary changed: '+name)
        for name, expected in source_plan['diagnostic_files'].items():
            if name != 'NKAB/dist/scene-probe.js' and \
                    staged['diagnostic_files'][name]['sha256'] != expected:
                raise RuntimeError('Archived replay diagnostic dependency changed: '+name)
        target = Path(staged['diagnostic_files']['NKAB/dist/scene-probe.js']['path']).resolve()
        if target != (sandbox/'NIKKE/NIKKE/game/NKAB/dist/scene-probe.js').resolve():
            raise RuntimeError('Archived replay target escaped exact scratch bundle')
        target.write_bytes(bundle)
        staged['diagnostic_files']['NKAB/dist/scene-probe.js']['sha256'] = bundle_hash
        config.write_text(json.dumps(staged, indent=2))
        print(json.dumps({'frozen_replay': replay, 'staged_bundle_sha256': bundle_hash}), flush=True)
    plan = host.validate(config)
    (sandbox/f'plan-{args.trial}.json').write_text(json.dumps(plan, indent=2))
    ready = sandbox/f'integration-ready-{args.trial}.json'
    ready.write_text(json.dumps(dict(schema_version=1, status='integration_ready',
        sandbox_root=str(sandbox), plan_sha256=plan['plan_sha256']), indent=2))
    result = subprocess.run([sys.executable, str(HERE.parent/'native_player_host.py'),
        '--config', str(config), '--run', '--integration-ready', str(ready)])
    if (output/'native-player-run.json').is_file():
        report = finalize(args.trial)
        if replay:
            (output/'frozen-replay.json').write_text(json.dumps(replay, indent=2)+'\n')
        if request is not None:
            (output/'mechanics-request.json').write_text(json.dumps(request, indent=2)+'\n', encoding='utf-8')
            events = [json.loads(line) for line in (output/'scene-events.jsonl').read_text().splitlines()]
            binding = verify_request_events(request, events)
            controls = [event for event in events if event.get('status') == 'native_control_mode_selected']
            control_binding = {'mode': controls[0]['controlMode'] if len(controls) == 1 else None,
                               'settings': controls[0] if len(controls) == 1 else None,
                               'bundle_sha256': plan['diagnostic_files']['NKAB/dist/scene-probe.js'],
                               'scope': 'Private controller identity; command correctness requires native readbacks'}
            if not replay and (len(controls) != 1 or control_binding['mode'] != args.control_mode):
                raise RuntimeError('Native controller mode does not match staged request')
            (output/'mechanics-request-receipt.json').write_text(json.dumps({
                'request_sha256': digest, 'source': str(request_path),
                'plan_sha256': plan['plan_sha256'], 'purpose': request['purpose'],
                'native_input_readbacks': binding,
                'control_binding': control_binding,
                'full_accuracy_verified': False}, indent=2)+'\n', encoding='utf-8')
            print(json.dumps({'native_input_readbacks': binding}))
            if not binding['passed']:
                return result.returncode or 1
            validators = {'boss-tactical': ['verify_boss_tactical_trial.py'],
                          'probe': ['verify_tactical_trial.py'],
                          'kraken-qte': ['verify_kraken_qte_trial.py'],
                          'kraken-cover-probe': ['verify_kraken_cover_trial.py'],
                          'kraken-tactical': ['verify_kraken_qte_trial.py',
                                             'verify_kraken_cover_trial.py']}.get(control_binding['mode'], [])
            if control_binding['mode'] == 'boss-tactical' and request.get('encounter', {}).get('waveId') == 6302004:
                validators.append('verify_chatterbox_cover_trial.py')
            for validator in validators:
                verified = subprocess.run([sys.executable, str(HERE / validator), str(output)])
                if verified.returncode:
                    return verified.returncode
        if report['errors'] or not report['clean_quit_observed']:
            return result.returncode or 1
    return result.returncode


if __name__ == '__main__':
    sys.exit(main())
