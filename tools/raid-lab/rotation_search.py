"""Reserve rotation alternatives for simulation; select only by actual damage."""
import itertools
from candidate_ranking import score


def timing(team):
    rotation = team.get('burst_rotation', {})
    stages = rotation.get('stage_delays', [])
    duration = min(team.get('duration', 0), (team.get('encounter_timeline') or {}).get('simulated_until', team.get('duration', 0)))
    cycles = []
    for window in rotation.get('full_bursts', []):
        if not window.get('complete') or window['end'] + 5 > duration:
            continue
        cast = next((s for s in stages if s['stage'] == '1' and s['cast_time'] >= window['end']), None)
        cycles.append(None if cast is None else round(cast['cast_time'] - window['end'], 2))
    passed = sum(gap is not None and gap <= 5 for gap in cycles)
    return {'bursts': len(rotation.get('full_bursts', [])), 'within_5s': passed,
            'cycles': len(cycles), 'on_time_share': passed / len(cycles) if cycles else 0}


def capabilities(unit, catalog, effects):
    stats = {e.get('stat', '') for e in effects.get(unit, [])}
    return {
        'cooldown': any('burst_cooldown' in stat for stat in stats),
        'gauge': bool(stats & {'burst_charge_pct', 'burst_charge_speed_pct'}) or catalog[unit]['weapon'] in ('SR', 'RL', 'SG'),
        'duration': any('fullburst' in stat.replace('_', '') and ('duration' in stat or 'time' in stat) for stat in stats),
    }


def proposals(results, index, ids, catalog, effects, priority, valid):
    """Reserve choices per slot and mechanism, including swaps with any squad."""
    team = results[index]['members']
    owners = {unit: i for i, row in enumerate(results) for unit in row['members']}
    found = {}
    for outgoing in team:
        remainder = [n for n in team if n != outgoing]
        options = []
        for incoming in ids:
            if incoming in team:
                continue
            candidate = [incoming if n == outgoing else n for n in team]
            if not valid(candidate):
                continue
            changes = {index: candidate}
            donor = owners.get(incoming)
            if donor is not None:
                replacement = [outgoing if n == incoming else n for n in results[donor]['members']]
                if not valid(replacement):
                    continue
                changes[donor] = replacement
            options.append({'outgoing': outgoing, 'incoming': incoming, 'changes': changes,
                            'priority': priority(incoming, remainder),
                            'capabilities': capabilities(incoming, catalog, effects)})
        options.sort(key=lambda p: p['priority'], reverse=True)
        groups = [('same stage', [p for p in options if catalog[p['incoming']]['burst'] == catalog[outgoing]['burst']])]
        groups += [(kind, [p for p in options if p['capabilities'][kind]]) for kind in ('cooldown', 'gauge', 'duration')]
        # Separate unused choices from donors so a popular allocated support
        # cannot hide an available alternative such as a lower-investment B1.
        for kind, group in groups:
            for is_swap in (False, True):
                selected = [p for p in group if (len(p['changes']) > 1) == is_swap][:1]
                for proposal in selected:
                    key = (outgoing, proposal['incoming'])
                    found.setdefault(key, {**proposal, 'reason': kind})
    return list(found.values())


def improve(results, ids, catalog, effects, priority, valid, orders, prefetch, run, duration, exhausted):
    """Screen 60s for ramping cycles; promote damage and timing diversity."""
    audit = []
    sequence = sorted(range(len(results)), key=lambda i: timing(results[i])['on_time_share'])
    for index in sequence:
        if exhausted():
            break
        candidates = proposals(results, index, ids, catalog, effects, priority, valid)
        screen_duration = min(60, duration)
        expanded = []
        for proposal in candidates:
            affected = list(proposal['changes'])
            choices = [orders(proposal['changes'][i])[:2] for i in affected]
            for combination in itertools.product(*choices):
                expanded.append((proposal, dict(zip(affected, combination))))
        screen_teams = [t for _, changes in expanded for t in changes.values()]
        screen_teams += [results[i]['members'] for i in range(len(results))]
        prefetch(screen_teams, screen_duration, phase='Checking burst cycling, gauge and cooldown alternatives')
        screened = []
        for proposal, changes in expanded:
            try:
                baseline = {i: run(results[i]['members'], screen_duration) for i in changes}
                alternative = {i: run(t, screen_duration) for i, t in changes.items()}
            except (ValueError, KeyError, IndexError, TypeError):
                continue
            damage_gain = sum(score(t) for t in alternative.values()) - sum(score(t) for t in baseline.values())
            burst_gain = sum(timing(t)['bursts'] for t in alternative.values()) - sum(timing(t)['bursts'] for t in baseline.values())
            cadence_gain = sum(timing(t)['on_time_share'] for t in alternative.values()) - sum(timing(t)['on_time_share'] for t in baseline.values())
            screened.append((proposal, changes, damage_gain, burst_gain, cadence_gain))
        promoted = []
        seen = set()
        # A 60-second damage leader, an extra-burst leader and a cadence leader
        # each get a full fight. Faster cycling never acts as a damage multiplier.
        for metric in (2, 3, 4):
            for row in sorted(screened, key=lambda r: (r[metric], r[2]), reverse=True):
                key = tuple(sorted((i, frozenset(t)) for i, t in row[1].items()))
                if key not in seen:
                    promoted.append(row); seen.add(key); break
        full = []
        for proposal, changes, *_ in promoted:
            affected = list(changes)
            for combination in itertools.product(*(orders(changes[i])[:4] for i in affected)):
                full.append((proposal, dict(zip(affected, combination))))
        prefetch([t for _, changes in full for t in changes.values()], duration, True,
                 phase='Verifying full-fight damage from burst rotation changes')
        best_gain = 0
        best = None
        for proposal, changes in full:
            try:
                alternative = {i: run(t, duration, True) for i, t in changes.items()}
            except (ValueError, KeyError, IndexError, TypeError):
                continue
            before = sum(results[i]['damage'] for i in changes)
            after = sum(t['damage'] for t in alternative.values())
            record = {'squad': index + 1, 'outgoing': proposal['outgoing'], 'incoming': proposal['incoming'],
                      'reason': proposal['reason'], 'affected_squads': [i + 1 for i in changes],
                      'baseline_damage': before, 'damage': after, 'accepted': False,
                      'before': {i + 1: timing(results[i]) for i in changes},
                      'after': {i + 1: timing(t) for i, t in alternative.items()}}
            audit.append(record)
            gain = sum(score(t) for t in alternative.values()) - sum(score(results[i]) for i in changes)
            if gain > best_gain:
                best_gain = gain
                best = alternative, record
        if best:
            for i, alternative in best[0].items():
                results[i] = alternative
            best[1]['accepted'] = True
    return audit
