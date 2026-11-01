"""Strict exercised Kraken gate. Original outcomes only; no combat calculations."""
import hashlib
import json
from pathlib import Path
from verify_tactical_parts import _qte, _cover

CLIENT = 'd39896d3770888039c728a1908448c3db5efa7cdf874c90d56f46d8d566428d2'
AUTHORED_SHA = '2880621c6edb7145a390d0db68f57f272ae6f165e9f03e42d32bf36c7c0de844'


def verify(rows, source, *, client_sha256, source_sha256):
    errors = []
    expected_break = [21201, 21203, 21205, 21207, 21209, 21211, 21213]
    expected_counter = [21202, 21204, 21206, 21208, 21210, 21212, 21214]
    if client_sha256 != CLIENT or source_sha256 != AUTHORED_SHA or source.get('clientSha256') != CLIENT or \
       source.get('waveId') != 6302009 or str(source.get('monsterTableId')) != '1520040153' or \
       source.get('qte', {}).get('groupId') != 212 or source['qte'].get('breakIds') != expected_break or \
       source['qte'].get('counterIds') != expected_counter:
        errors.append('Exact current153 authored Kraken source/count identity required')
    stops = [r for r in rows if r.get('status') == 'original_tick_driver_stopped']
    stop = stops[0] if len(stops) == 1 else None
    modes = [r for r in rows if r.get('status') == 'native_control_mode_selected']
    if len(modes) != 1 or modes[0].get('controlMode') != 'boss-tactical' or \
       modes[0].get('policyVersion') != 'boss-tactical-v1' or modes[0].get('clientSha256') != CLIENT or \
       modes[0].get('authoredSourceSha256') != AUTHORED_SHA:
        errors.append('Current153 tactical mode/source binding missing')
    terminals = [r for r in rows if r.get('status') == 'original_terminal_result']
    if len(terminals) != 1 or terminals[0].get('originalResult') is not True or \
       terminals[0].get('resultCaptured') is not True or terminals[0].get('completeBattle') is not True:
        errors.append('One complete original native Kraken result required')
    if stop is None or stop.get('stage') != 'original_battle_ticks':
        errors.append('Original native tick-driver stop evidence missing')
    for name, status, total_key in [('tacticalObservation','original_tactical_transition','total'),
                                     ('threatObservation','original_threat_event','emitted')]:
        observed = (stop or {}).get(name) or {}
        count = len([r for r in rows if r.get('status') == status])
        if observed.get('fault') is not None or observed.get('transitionsTruncated') is not False or \
           observed.get('emitted') != count or observed.get(total_key) != count or \
           name == 'threatObservation' and observed.get('droppedLogs') != 0:
            errors.append('Original observer evidence is incomplete/truncated: ' + name)
    try:
        qte, cover = _qte(rows, stop), _cover(rows, stop, 6302009)
    except (KeyError, TypeError, ValueError, AttributeError, OverflowError) as error:
        return {'passed': False, 'errors': errors + ['Malformed tactical evidence: ' + str(error)]}
    # Generic NOT_EXERCISED is never sufficient for this explicitly requested case.
    if qte['status'] != 'PASS' or qte.get('observedEpisodes', 0) < 1 or \
       len(qte.get('selectedBreakIds', [])) != 7 or len(qte.get('originalHitIds', [])) != 7:
        errors.append('All seven original Break targets must be selected and hit')
    if len(qte.get('sampledUnsafeTargetIds', [])) != 7:
        errors.append('All seven Counter targets need bounded unchanged-health evidence')
    decisions = [r for r in rows if r.get('status') == 'original_reactive_qte_decision' and r.get('action') == 'aim_break']
    if not decisions or any(r.get('groupId') != 212 for r in decisions):
        errors.append('Requested current Kraken group212 was not exclusively exercised')
    if cover['status'] != 'PASS' or cover.get('observedThreats', 0) < 1 or \
       min(cover.get('entered', 0), cover.get('released', 0), cover.get('resumed', 0)) < 1:
        errors.append('Original dangerous attack, protected cover, release and resumed fire must be exercised')
    dangers = [r for r in rows if r.get('status') == 'native_cover_decision' and r.get('action') == 'danger_observed']
    attacks = [r for r in rows if r.get('status') == 'original_threat_event' and r.get('kind') == 'attack']
    if not dangers or any(r.get('monsterTableId') != '1520040153' or
                          (r.get('attack') or {}).get('attackNodeId') != 230 for r in dangers):
        errors.append('Cover trigger lacks the original current Kraken identity/node')
    for danger in dangers:
        attack = danger.get('attack') or {}
        if not any(all(row.get(k) == attack.get(k) for k in ('tick','casterId','attackNodeId','sequence')) for row in attacks):
            errors.append('Cover trigger does not correlate an original attack event')
    control = (stop or {}).get('tacticalControl') or {}
    if control.get('mode') != 'boss-tactical' or control.get('policyVersion') != 'boss-tactical-v1' or \
       control.get('clientSha256') != CLIENT or control.get('fault') is not None or \
       control.get('observationTransitionsTruncated') is not False:
        errors.append('Current153 controller summary missing, faulted or truncated')
    errors.extend('QTE: ' + error for error in qte['errors'])
    errors.extend('cover: ' + error for error in cover['errors'])
    return {'schemaVersion': 1, 'passed': not errors, 'errors': errors, 'clientSha256': client_sha256,
            'authoredSourceSha256': source_sha256, 'waveId': 6302009, 'qte': qte, 'cover': cover,
            'native153TacticalMechanicsVerified': not errors,
            'fullAccuracyVerified': False, 'normalClientDamageParityVerified': False,
            'scope': 'Only source-bound current Kraken group212 seven Break targets and authored node230 cover episode'}


def verify_files(events_path, source_path):
    source_path = Path(source_path)
    source = json.loads(source_path.read_text(encoding='utf8'))
    rows = [json.loads(line) for line in Path(events_path).read_text(encoding='utf8').splitlines() if line]
    return verify(rows, source, client_sha256=CLIENT,
                  source_sha256=hashlib.sha256(source_path.read_bytes()).hexdigest())
