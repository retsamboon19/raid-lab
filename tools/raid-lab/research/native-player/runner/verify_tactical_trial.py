"""Verify native input effects; a completed command sequence alone is insufficient."""
import argparse
import hashlib
import json
from pathlib import Path


def verify(rows):
    errors = []
    points = [r for r in rows if r.get('status') == 'original_tactical_input_checkpoint']
    states = {r['label']: r['state'] for r in points}
    required = ('before_ownership', 'manual_ownership', 'selected_other_actor', 'pressed',
                'held_input_before_release', 'released', 'released_after_wait',
                'forced_cover_on', 'covered_after_wait', 'forced_cover_off',
                'repressed', 'released_again', 'restored_focus', 'restored_auto')
    missing = [label for label in required if label not in states]
    if missing:
        return {'passed': False, 'errors': ['missing checkpoints: ' + ', '.join(missing)]}
    if len(states) != len(points):
        errors.append('duplicate checkpoint labels')
    def check(ok, label):
        if not ok:
            errors.append(label)
    initial = states['before_ownership']
    selected = states['selected_other_actor']
    pressed = states['pressed']
    held = states['held_input_before_release']
    released = states['released']
    waited = states['released_after_wait']
    cover = states['forced_cover_on']
    covered = states['covered_after_wait']
    resumed = states['repressed']
    ended = states['released_again']
    restored = states['restored_auto']
    check(not states['manual_ownership']['autoAim'], 'original auto ownership not released')
    check(selected['focusedEntityId'] != initial['focusedEntityId'], 'focus did not change')
    check(all(states[k]['focusedEntityId'] == selected['focusedEntityId'] for k in required[2:-2]),
          'controlled actor changed during sequence')
    check(pressed['inputType'] == 2 and pressed['focusedStance'] == 2, 'press did not enter fire stance')
    shots = held['focusedUsedAmmoCount'] - pressed['focusedUsedAmmoCount']
    hits = held['focusedShotHitNum'] - pressed['focusedShotHitNum']
    check(shots > 0, 'held input fired no shots')
    check(hits > 0, 'directed native shots hit nothing')
    check(released['inputType'] == 1 and released['focusedStance'] == 0,
          'release did not enter cover stance')
    check(waited['focusedUsedAmmoCount'] == released['focusedUsedAmmoCount'],
          'controlled actor fired after release')
    check(cover['forcedCover'] and covered['forcedCover'], 'forced cover did not persist')
    squad = cover.get('squad', [])
    check(len(squad) == 5 and len({r['entityId'] for r in squad}) == 5,
          'five squad cover readbacks absent')
    check(bool(squad) and all(r['stance'] == 0 for r in squad), 'squad did not enter cover')
    check(bool(squad) and squad == covered.get('squad'), 'squad fired or left cover during wait')
    check(not states['forced_cover_off']['forcedCover'], 'forced cover did not end')
    check(ended['focusedUsedAmmoCount'] > resumed['focusedUsedAmmoCount'], 'firing did not resume')
    check(restored['focusedEntityId'] == initial['focusedEntityId'] and
          restored['autoAim'] == initial['autoAim'] and not restored['forcedCover'],
          'original control state not restored')
    pointer = restored.get('virtualPointer', {})
    check(pointer.get('active') is False and pointer.get('substitutions', 0) > 0 and
          pointer.get('fault') is None, 'virtual input lease not exercised and released')
    terminals = [r for r in rows if r.get('status') == 'original_terminal_result']
    check(len(terminals) == 1 and terminals[0].get('originalResult') is True,
          'original full battle result absent')
    return {'passed': not errors, 'errors': errors, 'held_shots': shots, 'held_hits': hits,
            'scope': 'Native input/aim effects, squad cover, and restoration; no all-boss or parity claim'}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('trial_directory', type=Path)
    args = parser.parse_args()
    folder = args.trial_directory
    data = (folder / 'scene-events.jsonl').read_bytes()
    rows = [json.loads(line) for line in data.decode().splitlines()]
    report = verify(rows)
    scene = json.loads((folder / 'scene-verification.json').read_text())
    if not scene['complete_battle_executed'] or scene['errors']:
        report['errors'].append('native battle verification failed')
        report['passed'] = False
    report.update(log_sha256=hashlib.sha256(data).hexdigest(),
                  bundle_sha256=scene['artifacts']['scene-probe.js'],
                  full_accuracy_verified=False)
    output = folder / 'tactical-input-verification.json'
    if output.exists():
        raise ValueError('Refusing to replace historical tactical evidence')
    output.write_text(json.dumps(report, indent=2) + '\n')
    print(json.dumps(report))
    return 0 if report['passed'] else 1


if __name__ == '__main__':
    raise SystemExit(main())
