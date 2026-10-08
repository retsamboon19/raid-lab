"""Check actual native protection, casting completion, release, and resumed fire."""
import argparse
import hashlib
import json
from pathlib import Path


def verify(rows):
    errors = []
    def one(status):
        matches = [row for row in rows if row.get('status') == status]
        if len(matches) != 1:
            errors.append(status + ': expected exactly one record')
            return None
        return matches[0]
    entered = one('native_cover_probe_entered')
    released = one('native_cover_probe_released')
    resumed = one('native_cover_probe_resume_readback')
    if not entered or not released or not resumed:
        return {'passed': False, 'errors': errors}
    def check(condition, message):
        if not condition:
            errors.append(message)
    check(entered['attack']['attackNodeId'] == 230 and
          entered['tick'] - entered['attack']['tick'] >= 3, 'original telegraph/reaction absent')
    check(entered['nativeAfter']['forcedCover'] is True and
          released['nativeBefore']['forcedCover'] is True and
          released['nativeAfter']['forcedCover'] is False, 'cover state transition/readback failed')
    check(released.get('observedCasting') is True and
          released['condition']['condition']['name'] == 'Idle' and
          released['tick'] >= released['condition']['tick'], 'released before original casting finished')
    check(released['observedProjectileIds'] and
          released['threat']['allBossActiveProjectileIds'] == [] and
          released['threat']['pendingUnlinkedCreate'] is None, 'released before projectile resolution')
    before = {unit['id']: unit for unit in entered['squadBefore']['characters']}
    after = {unit['id']: unit for unit in released['squadAfter']['characters']}
    check(len(before) == 5 and before.keys() == after.keys(), 'five native character identities absent')
    check(all(unit['health']['hp'] == after[identity]['health']['hp']
              for identity, unit in before.items()), 'character HP decreased during protected sequence')
    events = [row for row in rows if row.get('status') == 'original_threat_event' and
              entered['tick'] <= row.get('tick', -1) <= released['tick']]
    cover_ids = {row['coverId'] for row in events if row['kind'] == 'cover_damage' and
                 int(row['damage']) > 0}
    check(cover_ids == {unit['cover']['id'] for unit in before.values()},
          'original positive cover damage was not observed for all five covers')
    check(not any(row['kind'] == 'damage' and row['targetType'] == 'Character' and
                  int(row['actualDamage']) > 0 for row in events),
          'original boss damage reached a character during protected sequence')
    spent_before = {u['entityId']: u['usedAmmoCount'] for u in entered['nativeAfter']['squad']}
    spent_after = {u['entityId']: u['usedAmmoCount'] for u in released['nativeBefore']['squad']}
    check(spent_before == spent_after, 'squad fired during forced cover')
    check(resumed.get('firingResumed') is True and resumed['state']['forcedCover'] is False and
          resumed['state']['autoAim'] is True, 'native automatic firing did not resume')
    return {'passed': not errors, 'errors': errors, 'cover_tick': entered['tick'],
            'release_tick': released['tick'], 'protected_character_ids': sorted(before),
            'original_cover_damage_ids': sorted(cover_ids),
            'scope': 'Exact node230 missile/follow-up-cast sequence; not all attacks or bosses'}


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
    output = folder / 'kraken-cover-verification.json'
    if output.exists():
        raise ValueError('Refusing to replace historical cover evidence')
    output.write_text(json.dumps(report, indent=2) + '\n')
    print(json.dumps(report))
    return 0 if report['passed'] else 1


if __name__ == '__main__':
    raise SystemExit(main())
