"""Bounded Python shortlisting followed by verified original-engine battles.

Python estimates select candidates; only native results rank recommendations.
Native runs remain serial under the isolated player lease.
"""
from __future__ import annotations

import copy
import json
import math
import random
import time

import core
import native_battle
from search_guidance import SearchGuidance


def validate_request(payload):
    if not isinstance(payload, dict) or set(payload) - {'engine', 'roster', 'settings', 'search', 'account_id'}:
        raise ValueError('Search needs your roster, encounter settings and search options.')
    request = json.loads(native_battle._canonical(payload))
    if request.get('engine', native_battle.ENGINE) != native_battle.ENGINE:
        raise ValueError('Automatic search uses the original153 battle engine.')
    if len(native_battle._canonical(request)) > 2_000_000:
        raise ValueError('Search request is too large.')
    options = request.get('search', {})
    if not isinstance(options, dict) or set(options) - {'budget', 'teams'}:
        raise ValueError('Unknown search option.')
    budget, teams = options.get('budget', 3), options.get('teams', 1)
    if type(budget) is not int or budget not in (3, 6, 12):
        raise ValueError('Choose 3, 6 or 12 candidate allocations.')
    if type(teams) is not int or not 1 <= teams <= 5:
        raise ValueError('Choose between one and five non-overlapping teams.')
    rows = request.get('roster')
    if not isinstance(rows, list) or len(rows) > 400 or any(not isinstance(r, dict) for r in rows):
        raise ValueError('Search needs a roster of at most 400 units.')
    ids = [r.get('id') for r in rows]
    if any(not isinstance(n, str) or n not in core.CAT for n in ids) or len(set(ids)) != len(ids):
        raise ValueError('Roster entries must have unique known unit IDs.')
    enabled = [r for r in rows if r.get('enabled', True) is not False and r.get('owned', True) is not False]
    if len(enabled) < teams * 5:
        raise ValueError(f'Enable at least {teams * 5} units for {teams} non-overlapping teams.')
    for row in enabled:
        core.validate_build(row.get('build'))  # Validate without replacing saved input/provenance.
    battle = {k: copy.deepcopy(v) for k, v in request.items() if k not in ('search',)}
    battle['members'] = [r['id'] for r in enabled[:5]]
    validated = native_battle.validate_request(battle)
    request['settings'] = copy.deepcopy(validated['settings'])
    battle = validated
    encounter = native_battle._encounter(battle)
    if teams > 1 and encounter['contentMode'] not in ('solo', 'museum'):
        raise ValueError('Multiple non-overlapping squads are available for Solo Raid and Museum. Choose one squad for this mode.')
    request['search'] = {'budget': budget, 'teams': teams}
    return request


def proposals(request, encounter, cancelled=lambda: False, pool_size=None):
    roster = {r['id']: r for r in request['roster']
              if r.get('enabled', True) is not False and r.get('owned', True) is not False}
    catalog = core.resolve_catalog(roster)
    boss = next((b for b in core.encounters.BOSSES if b['id'] == encounter.get('bossId')), {})
    barrier = boss.get('barrier_element')
    if barrier and sum(barrier in catalog[n]['barrier_elements'] for n in roster) < request['search']['teams']:
        raise ValueError(f'Enable at least one {barrier} damage option per squad for this encounter.')
    # Investment is a proposal preference, not an approximation of native stats.
    weights = {n: (1 + sum(r['build']['skill_levels'].values()) / 30
               + min(r['build']['level'], 400) / 400)
               * (1.3 if catalog[n]['element'] == boss.get('weakness') else 1)
               for n, r in roster.items()}
    guidance = SearchGuidance(roster, catalog, {'content_mode': encounter['contentMode'],
        'boss_id': encounter.get('bossId'), 'encounter': {**boss, **encounter},
        'enemy_element': boss.get('enemy_element'), 'element': boss.get('weakness', 'Any')}, weights)
    count = request['search']['teams']
    budget = pool_size or request['search']['budget']
    rng = random.Random(42)
    plans = {}
    ids = sorted(roster)
    for attempt in range(600):
        if cancelled():
            break
        remaining = set(ids)
        plan = []
        for squad in range(count):
            team = []
            # Seed documented partner packages as well as unseeded proposals.
            if attempt % 3 == 0 and guidance.templates:
                template = guidance.templates[(attempt // 3 + squad) % len(guidance.templates)]
                if len(template) <= 5 and set(template) <= remaining:
                    team = list(template)
                    remaining.difference_update(team)
            for stage in ('1', '2', '3', '3', None):
                if len(team) >= 5:
                    break
                if stage in ('1', '2') and any(catalog[n]['burst'] == stage for n in team):
                    continue
                if stage == '3' and sum(catalog[n]['burst'] == '3' for n in team) >= 2:
                    continue
                pool = [n for n in ids if n in remaining and (stage is None or catalog[n]['burst'] == stage)]
                if not pool:
                    pool = [n for n in ids if n in remaining and catalog[n]['burst'] == 'A']
                if not pool:
                    continue
                chosen = max(pool, key=lambda n: guidance.priority(n, team)
                    + (.0 if attempt == 0 else .65) * -math.log(-math.log(max(1e-9, rng.random()))))
                team.append(chosen)
                remaining.remove(chosen)
            while len(team) < 5 and remaining:
                chosen = max(sorted(remaining), key=lambda n: guidance.priority(n, team))
                team.append(chosen)
                remaining.remove(chosen)
            stages = {catalog[n]['burst'] for n in team}
            if len(team) != 5 or not ({'1', '2', '3'} <= stages or 'A' in stages):
                break
            if barrier and not any(barrier in catalog[n]['barrier_elements'] for n in team):
                break
            ordered = core.ordered(team)
            orders = core.burst_orders(ordered, catalog, guidance)
            # Preserve different actual native slot orders for rotation comparisons.
            team = orders[(attempt // 3) % len(orders)] if attempt % 4 == 3 else orders[0]
            plan.append(tuple(team))
        if len(plan) == count:
            key = tuple(sorted(plan))
            plans[key] = sum(guidance.score(t) for t in plan)
        if len(plans) >= (budget if pool_size else max(30, budget * 8)):
            break
    if not plans and not cancelled():
        raise ValueError('No complete burst-stage allocation found. Enable more Burst I, II and III options.')
    ranked = sorted(plans, key=plans.get, reverse=True)
    # Reserve variety in membership before spending the remainder on slot orders.
    selected, memberships = [], set()
    for plan in ranked:
        key = tuple(sorted(tuple(sorted(t)) for t in plan))
        if key not in memberships:
            selected.append(plan)
            memberships.add(key)
        if len(selected) >= budget:
            break
    for plan in ranked:
        if len(selected) >= budget:
            break
        if plan not in selected:
            selected.append(plan)
    return selected


# Bound Python work and expensive real-time verification independently.
SEARCH_DEPTHS = {3: (40, 30, 1), 6: (80, 45, 2), 12: (120, 60, 3)}


def screening_inputs(request, encounter):
    """Separate model inputs; never rewrite the saved native request."""
    boss_id = encounter.get('bossId')
    modeled = boss_id in core.encounters.BY_ID
    duration = min(180, encounter['timeLimit'])
    settings = core.validate_settings({'boss_id': boss_id if modeled else 'training',
        'duration': max(30, duration), 'survival_policy': 'damage-only',
        'playstyle': 'auto', 'fixed_level': False})
    roster = {r['id']: copy.deepcopy(r) for r in request['roster']
              if r.get('enabled', True) is not False and r.get('owned', True) is not False}
    rule = encounter.get('unitLevel', {})
    for row in roster.values():
        if rule.get('mode') == 'cap':
            row['build']['level'] = min(row['build']['level'], rule['value'])
        elif rule.get('mode') == 'fixed':
            row['build']['level'] = rule['value']
    # Level policy already applied to the model-only copy above.
    settings['fixed_level'] = False
    settings['_catalog'] = core.resolve_catalog(roster)
    return roster, settings, modeled, duration


def shortlist(request, encounter, progress, cancel):
    from parallel_compute import CandidateExecutor
    started = time.perf_counter()
    pool_size, seconds, native_count = SEARCH_DEPTHS[request['search']['budget']]
    plans = proposals(request, encounter, cancel, pool_size=pool_size)
    if cancel():
        raise InterruptedError('Search stopped during Python shortlisting.')
    roster, settings, modeled, horizon = screening_inputs(request, encounter)
    cache, failures = {}, {}
    short = min(45, horizon)
    workers = CandidateExecutor(requested=4)
    stop_at = started + seconds
    def update():
        progress(phase='Python screening candidates', pythonSimulations=len(cache),
                 simulations=0, elapsed=round(time.perf_counter()-started, 1), progress=0)
    def fill(selected, duration):
        keys = [(team, duration, False) for plan in selected for team in plan]
        workers.fill(keys, roster, settings, cache, failures, update, cancel)
    def score(plan, duration):
        rows = [cache.get((team, duration, False)) for team in plan]
        if any(r is None or not math.isfinite(r['damage']) for r in rows):
            return None
        return sum(r['damage'] for r in rows)
    try:
        update()
        workers.deadline = started + seconds * .4
        fill(plans, short)
        ranked = sorted((p for p in plans if score(p, short) is not None),
                        key=lambda p: score(p, short), reverse=True)
        # Spend the remaining time on sustained damage, not just opening bursts.
        workers.deadline = stop_at
        fill(ranked[:max(4, native_count*4)], horizon)
    finally:
        workers.close()
    full = sorted((p for p in plans if score(p, horizon) is not None),
                  key=lambda p: score(p, horizon), reverse=True)
    ranked = full + [p for p in ranked if p not in full]
    selected = ranked[:native_count]
    # Medium/deep reserve a guidance candidate against Python model blind spots.
    if native_count > 1 and plans and plans[0] not in selected:
        selected = selected[:native_count-1] + [plans[0]]
    for plan in plans:
        if len(selected) >= native_count:
            break
        if plan not in selected:
            selected.append(plan)
    estimates = []
    for plan in selected:
        duration = horizon if score(plan, horizon) is not None else short
        estimates.append({'members': [list(t) for t in plan],
                          'estimatedDamage': score(plan, duration), 'duration': duration})
    evidence = {'method': '45-second screening, sustained-damage finalists, native verification',
        'elapsed': round(time.perf_counter()-started, 3), 'budgetSeconds': seconds,
        'proposedAllocations': len(plans), 'simulations': len(cache),
        'fullHorizonSimulations': sum(k[1] == horizon for k in cache),
        'failedSimulations': len(failures), 'failureReasons': sorted({str(e) for e in failures.values()}),
        'nativeAllocations': len(selected), 'encounterModel': settings['boss_id'],
        'matchedEncounterModel': modeled, 'horizon': horizon, 'estimates': estimates,
        'limitations': ['Python is approximate; estimates are not native damage or verified clears.',
            'Unmodeled encounters use a training-target shortlist; the engine uses the selected encounter.',
            'Medium/deep searches reserve a guidance candidate to reduce model selection bias.']}
    progress(phase='Python shortlist ready; verifying with the engine',
             pythonSimulations=len(cache), simulations=0, progress=0)
    return selected, evidence


def _damage(result):
    return result.get('gameTotalDamage') or result['score']


def _rank(result, mode):
    if mode in ('campaign', 'special'):
        outcome = result.get('nativeOutcome', {})
        # A terminal native result code alone can also accompany a squad wipe.
        hp = outcome.get('targetRemainHp')
        clear = int(hp) == 0 if hp is not None else result['nativeResult'] == 1
        return (clear, -result['durationMs'] if clear else 0, int(result['score']))
    return (int(_damage(result)),)


def run_search(payload, progress=lambda **_: None, cancel=lambda: False):
    request = validate_request(payload)
    start = time.monotonic()
    encounter = native_battle._encounter(request)
    plans, screening = shortlist(request, encounter, progress, cancel)
    cache, failures, tested = {}, [], 0
    total = len({team for plan in plans for team in plan})
    reason = 'completed'
    # One legitimate seed input across comparisons; no RNG state replacement.
    settings = copy.deepcopy(request['settings'])
    settings.setdefault('random_seed', random.SystemRandom().randrange(1, 2147483648))
    for plan in plans:
        for team in plan:
            if cancel():
                reason = 'cancelled'
                break
            if team in cache:
                continue
            battle = {k: copy.deepcopy(v) for k, v in request.items() if k != 'search'}
            battle.update(members=list(team), settings=copy.deepcopy(settings))
            def update(**event):
                progress(**{**event, 'simulations': len(cache), 'planned': total,
                    'progress': tested / max(total, 1), 'elapsed': round(time.monotonic() - start, 1)})
            update(phase=f'Testing candidate {tested + 1} of {total}')
            try:
                # Cancellation stops scheduling. Let the current battle finish
                # and validate normally so its completed result can be retained.
                result = native_battle.run_battle(battle, update)
                result['requestedInputs'] = battle
                cache[team] = result
                tested += 1
            except native_battle.NativeBattleError as error:
                failures.append({'members': list(team), 'code': error.code, 'error': str(error)})
                reason = 'error'
                break  # A source/isolation/runtime failure must not trigger more launches.
        if reason != 'completed':
            break
    if cancel():
        reason = 'cancelled'
    if not cache:
        if reason == 'cancelled':
            raise InterruptedError('Search stopped before any native battle completed.')
        if failures:
            raise native_battle.NativeBattleError(failures[0]['code'], failures[0]['error'])
        raise ValueError('No native team results were produced.')
    mode = encounter['contentMode']
    # Each planned allocation is non-overlapping. Partial allocations remain
    # eligible on cancellation, but never outrank a complete allocation by size.
    completed = [[cache[t] for t in plan if t in cache] for plan in plans]
    def plan_rank(rows):
        return (len(rows), *tuple(sum(values) for values in zip(*[_rank(r, mode) for r in rows])))
    selected = max(completed, key=plan_rank)
    selected.sort(key=lambda row: _rank(row, mode), reverse=True)
    teams = [{'members': row['requestedInputs']['members'], 'damage': _damage(row), 'native': row,
              'builds': {r['id']: r['build'] for r in request['roster'] if r['id'] in row['requestedInputs']['members']}}
             for row in selected]
    progress(phase='Native search finished', simulations=len(cache), planned=total, progress=1)
    return {'schema': 'native-search-v1', 'engine': native_battle.ENGINE, 'kind': 'search',
        'teams': teams, 'total': str(sum(int(t['damage']) for t in teams)),
        'simulations': len(cache), 'elapsed': round(time.monotonic() - start, 2),
        'settings': {**settings, 'content_mode': mode, 'boss_id': encounter.get('bossId') or encounter['id'].replace(':', '-'),
                     'encounter': encounter, 'duration': encounter['timeLimit'], **request['search']},
        'completion': {'reason': reason, 'requested_teams': request['search']['teams'], 'returned_teams': len(teams)},
        'screening': screening,
        'failures': failures, 'candidates': list(cache.values()), 'requestedInputs': request,
        'selection': {'objective': 'Clear first, then faster clears and damage' if mode in ('campaign', 'special') else 'Original native total damage',
                      'method': 'Python shortlist, then original full battles; recommendations ranked by native results only.'},
        'limits': ['A bounded search, not an exhaustive optimum. Untested teams and burst orders may be better.',
                   'Native engine accuracy is not established for every encounter and team.',
                   'Python estimates are approximate and only select finalists; final damage comes from the engine.']
                  + ([] if screening.get('matchedEncounterModel', True) else
                     ['This encounter has no matching Python model; screening used a training target.'])}
