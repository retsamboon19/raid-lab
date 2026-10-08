"""Require original QTE success and observed Counter safety, not a damage score."""
import argparse
import hashlib
import json
from pathlib import Path


def verify(rows):
    errors = []
    snapshots = [r for r in rows if r.get('status') == 'original_tactical_observation_change']
    known = {}
    counter_health = {}
    for row in snapshots:
        qte = row.get('qte', {})
        for target in qte.get('targets', []):
            entity = target['entityId']
            kind = target['colType']['name']
            if entity in known and known[entity] != kind:
                errors.append('live target identity changed type')
            known[entity] = kind
            if kind == 'Counter':
                counter_health.setdefault(entity, set()).add(target['health']['hp'])
    events = [r for r in rows if r.get('status') == 'original_tactical_transition']
    hits = {r['entityInfoId'] for r in events if r['kind'] == 'QuickTimeColliderHit'}
    unsafe = sorted(entity for entity in hits if known.get(entity) != 'Break')
    if unsafe:
        errors.append('hit Counter or unidentified QTE entity')
    if not counter_health or any(len(values) != 1 for values in counter_health.values()):
        errors.append('Counter health absent or changed in observations')
    native = [r for r in events if r['kind'] == 'QuickTimePresetEnd']
    if len(native) != 1 or native[0].get('success') is not True or native[0].get('end') is not True:
        errors.append('original successful preset-end event absent')
    decisions = [r for r in rows if r.get('status') == 'native_kraken_qte_decision']
    results = [r for r in decisions if r['action'] == 'native_preset_result']
    if len(results) != 1 or results[0].get('nativePresetSuccess') is not True:
        errors.append('original preset IsSuccess readback absent')
    selected = [r for r in decisions if r['action'] == 'aim_break']
    if len(selected) != 7 or {r['entityId'] for r in selected} != hits:
        errors.append('seven selected native Break entities were not all hit')
    end = [r for r in rows if r.get('status') == 'original_tick_driver_stopped']
    policy = end[0].get('tacticalControl', {}).get('policy', {}) if len(end) == 1 else {}
    if policy.get('nativePresetSuccesses') != 1 or policy.get('nativePresetFailures') != 0:
        errors.append('controller native outcome counters do not match success')
    if policy.get('owned') is not False or policy.get('unsupported') != []:
        errors.append('controller failed to restore auto or encountered unsupported state')
    return {'passed': not errors, 'errors': errors, 'break_entities_hit': sorted(hits),
            'unsafe_entities_hit': unsafe, 'counter_entities_observed': sorted(counter_health),
            'native_success_tick': native[0]['tick'] if len(native) == 1 else None,
            'scope': 'Observed group212 and exact fixture only; no all-boss certification'}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('trial_directory', type=Path)
    args = parser.parse_args()
    folder = args.trial_directory
    data = (folder / 'scene-events.jsonl').read_bytes()
    report = verify([json.loads(line) for line in data.decode().splitlines()])
    scene = json.loads((folder / 'scene-verification.json').read_text())
    if not scene['complete_battle_executed'] or scene['errors']:
        report['errors'].append('native battle verification failed')
        report['passed'] = False
    report.update(log_sha256=hashlib.sha256(data).hexdigest(),
                  bundle_sha256=scene['artifacts']['scene-probe.js'],full_accuracy_verified=False)
    output = folder / 'kraken-qte-verification.json'
    if output.exists():
        raise ValueError('Refusing to replace historical QTE evidence')
    output.write_text(json.dumps(report, indent=2) + '\n')
    print(json.dumps(report))
    return 0 if report['passed'] else 1


if __name__ == '__main__':
    raise SystemExit(main())
