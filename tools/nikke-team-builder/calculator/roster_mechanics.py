"""Shared combat primitives needed by the complete roster.

This module operates on BuffManager state, never on runner profiles. Encounter
adapters supply finite cover and enemy attacks; target-dummy runs have no attacks.
"""
from __future__ import annotations

RUNTIME_CONDITIONS = ('caster_alive', 'during_decoy', 'during_charge_hold:',
                      'target_stack_above:', 'self_cover_broken', 'no_broken_ally_cover')


def alive(bm, name):
    return bm.state.get('hp', {}).get(name, 1) > 0


def recipients(bm, ab):
    return ab.target_chars if ab.target_chars is not None else bm._resolve_lazy(ab)


def active(bm, name, stat, t=None):
    t = bm._cur_t if t is None else t
    for ab in list(bm._by_stat(stat)):
        targets = ab.shield_per_target if stat == 'shared_shield_from_max_hp_pct' else recipients(bm, ab)
        if t >= ab.expires_at or name not in targets:
            continue
        if ab.has_runtime_conditions and not bm._runtime_condition_ok(
                ab.effect['trigger'].get('condition', []), ab.caster, name, name, t):
            continue
        yield ab


def total(bm, name, stat, t=None):
    return sum(bm._get_value(ab.effect, ab, name,
               stack_override=ab.per_char_stacks.get(name)) or 0.0 for ab in active(bm, name, stat, t))


def resolve_target(bm, target, caster, meta):
    if not isinstance(target, str):
        return None
    names = [n for n in bm.squad_names if alive(bm, n)]
    suffix = target.rsplit(':', 1)[-1]
    count = int(suffix) if suffix.isdigit() else 1
    if target == 'allies_king':
        return [n for n in names if n == '크라운']  # Native IsCheckCharacter = 330.
    if target == 'allies_idol':
        return [n for n in names if n == '아니스 : 스타']  # Native IsCheckCharacter = 17.
    if target == 'allies_squad':
        squad = meta.get(caster, {}).get('squad')
        return [n for n in names if n == caster or (squad and meta[n].get('squad') == squad)]
    if target == 'event_healer':
        n = bm._notify_ctx.get('healer')
        return [n] if n in names else []
    if target == 'event_subject':
        n = bm._notify_ctx.get('subject')
        return [n] if n in names else []
    if target.startswith('self_and_top_atk:'):
        return [caster] + bm._top_by('atk', count, exclude=caster)
    if target.startswith('self_and_lowest_hp:'):
        return [caster] + sorted((n for n in names if n != caster), key=lambda n: bm.state.get('hp', {}).get(n, 0))[:count]
    if target.startswith('self_and_weapon_top_atk:'):
        weapon = target.split(':')[1]
        pool = [n for n in names if n != caster and meta[n]['weapon_type'] == weapon]
        return [caster] + sorted(pool, key=bm._effective_atk, reverse=True)[:count]
    if target.startswith('allies_lowest_hp_ratio:'):
        return sorted(names, key=lambda n: bm.state.get('hp_pct', {}).get(n, 100))[:count]
    if target.startswith('allies_top_hp:'):
        return sorted(names, key=bm.effective_max_hp, reverse=True)[:count]
    if target.startswith('allies_down_'):
        pool = [n for n in bm.squad_names if not alive(bm, n)]
        if target.startswith('allies_down_class_random:'):
            cls = target.split(':')[1]
            pool = [n for n in pool if meta[n]['class'] == cls]
            return bm._roster_rng.sample(pool, min(count, len(pool)))
        return sorted(pool, key=bm._effective_atk, reverse=True)[:count]
    if target.startswith('allies_broken_cover_random:'):
        runtime = bm.state.get('encounter_runtime')
        pool = [n for n in names if runtime and runtime.cover.get(n, 0) <= 0]
        return bm._roster_rng.sample(pool, min(count, len(pool)))
    if target.startswith('allies_debuff_random:'):
        pool = [n for n in names if any(ab.effect.get('polarity') == 'harmful'
                and n in recipients(bm, ab) for ab in bm._active)]
        return bm._roster_rng.sample(pool, min(count, len(pool)))
    if target.startswith('allies_without_buff:'):
        state = target.split(':', 1)[1]
        return [n for n in names if not bm._has_self_state(n, state)]
    if target.startswith('allies_with_any_buff:'):
        states = target.split(':', 1)[1].split(',')
        return [n for n in names if any(bm._has_self_state(n, s) for s in states)]
    if target.startswith('allies_class:') and target.count(':') == 2:
        return [n for n in names if meta[n]['class'] == target.split(':')[1]][:count]
    return None


def condition(bm, cond, caster, t):
    if cond == 'caster_alive':
        return alive(bm, caster)
    if cond == 'healed_by_other':
        return bm._notify_ctx.get('healer') not in (None, caster)
    if cond == 'target_is_boss':
        return bm.state.get('target_is_boss', True)
    if cond.startswith('target_stack_above:'):
        _, name, n = cond.split(':')
        return any(ab.stack >= int(n) and '__enemy__' in recipients(bm, ab) for ab in bm._by_name(name))
    if cond == 'during_decoy':
        return any(ab.shield_per_target.get(caster, 0) > 0 for ab in active(bm, caster, 'decoy', t))
    if cond.startswith('during_charge_hold:'):
        cs = bm.state.get('char_states', {}).get(caster)
        threshold = float(cond.split(':')[1])
        return bool(cs and bm.state.get('charging', {}).get(caster)
                    and cs._charge_full_t >= 0 and t - cs._charge_full_t >= threshold - 1e-8)
    if cond in ('self_cover_broken', 'no_broken_ally_cover'):
        runtime = bm.state.get('encounter_runtime')
        if not runtime or not hasattr(runtime, 'cover'):
            return False
        if cond == 'self_cover_broken':
            return runtime.cover.get(caster, 0) <= 0
        return all(runtime.cover.get(n, 0) > 0 for n in bm.squad_names if alive(bm, n))
    return None


def timing_key(timing):
    if timing.startswith('burst_enter_count:'):
        return 'burst_enter:' + timing.split(':')[1]
    if timing.startswith('charge_hold_count:'):
        return 'charge_hold:' + timing.split(':')[1]
    for prefix, event in [('non_full_charge_fire_count:', 'non_full_charge_fire'),
                          ('crit_pellet_hit_count:', 'crit_pellet_hit'),
                          ('pellet_hit_single:', 'pellet_hit_single')]:
        if timing.startswith(prefix):
            return event
    return None


def timing_match(timing, event, count, ctx):
    key = timing_key(timing)
    if key is None:
        return None
    if key != event:
        return False
    n = int(timing.rsplit(':', 1)[1])
    if timing.startswith('burst_enter_count:'):
        return count >= n
    if timing.startswith('pellet_hit_single:'):
        return ctx.get('pellets', 0) >= n
    return count % n == 0


def remove(bm, ab, t):
    if ab not in bm._active:
        return
    bm._active.remove(ab)
    bm._dot_timers.pop(id(ab.effect), None)
    bm._instant_timers.pop(id(ab.effect), None)
    bm._invalidate_buffs_cache()
    name = ab.effect.get('name')
    if name:
        targets = recipients(bm, ab)
        if bm._buff_event_handler:
            for n in targets:
                bm._buff_event_handler('expire', name, ab.caster, n, t, t)
        for n in dict.fromkeys([ab.caster] + [n for n in targets if n in bm.squad_names]):
            bm.notify('event:state_end:' + name, t, n)


def instant(bm, eff, caster, t, value):
    stat = eff.get('stat')
    if stat == 'buff_stack_remove':
        targets = set(bm._resolve_target(eff.get('target', 'self'), caster))
        for ab in list(bm._active):
            if eff.get('target_effect') and ab.effect.get('name') != eff['target_effect']:
                continue
            if ab.effect.get('polarity') != 'beneficial':
                continue
            group = recipients(bm, ab)
            affected = [n for n in group if n in targets and not bm._has_immune(n, 'stack_change_immune')]
            if not affected:
                continue
            for n in affected:
                ab.per_char_stacks[n] = max(0, ab.per_char_stacks.get(n, ab.stack) - int(value or 1))
            if all(ab.per_char_stacks.get(n, ab.stack) == 0 for n in group):
                remove(bm, ab, t)
            else:
                remaining = {ab.per_char_stacks.get(n, ab.stack) for n in group}
                if len(remaining) == 1:
                    ab.stack = remaining.pop()
                    ab.per_char_stacks.clear()
                ab.target_chars = [n for n in group if ab.per_char_stacks.get(n, ab.stack) > 0]
                bm._invalidate_buffs_cache()
                if bm._buff_event_handler:
                    for n in affected:
                        bm._buff_event_handler('activate', ab.effect['name'], ab.caster, n, t,
                                               ab.expires_at, bm._get_value(ab.effect, ab, n,
                                               stack_override=ab.per_char_stacks.get(n)), ab.effect.get('stat'))
        return True
    if stat == 'buff_stack_add' and not eff.get('target_effect'):
        targets = set(bm._resolve_target(eff.get('target', 'self'), caster))
        changes = []
        for ab in list(bm._active):
            cap = ab.effect.get('max_stack', 1)
            if cap == 1 or ab.effect.get('polarity') != 'beneficial':
                continue
            group = recipients(bm, ab)
            affected = targets.intersection(group)
            affected = {n for n in affected if not bm._has_immune(n, 'stack_change_immune')}
            if not affected:
                continue
            if affected != set(group):
                for n in group:
                    ab.per_char_stacks.setdefault(n, ab.stack)
                for n in affected:
                    old = ab.per_char_stacks[n]
                    ab.per_char_stacks[n] = old + int(value or 1) if cap < 0 else min(cap, old + int(value or 1))
            else:
                ab.stack = ab.stack + int(value or 1) if cap < 0 else min(cap, ab.stack + int(value or 1))
                for n in ab.per_char_stacks:
                    ab.per_char_stacks[n] = min(cap, ab.per_char_stacks[n] + int(value or 1)) if cap > 0 else ab.per_char_stacks[n] + int(value or 1)
            duration = ab.effect.get('duration', -1)
            if duration and duration > 0:
                ab.expires_at = t + duration
            changes.append(ab)
        bm._invalidate_buffs_cache()
        for ab in changes:
            for n in recipients(bm, ab):
                bm.notify(f'stack_reach:{ab.effect["name"]}:{ab.per_char_stacks.get(n, ab.stack)}', t, n)
                bm.notify('event:' + ab.effect['name'], t, n)
        return True
    if stat == 'buff_duration_extend':
        targets = set(bm._resolve_target(eff.get('target', 'self'), caster))
        for ab in bm._by_name(eff['target_effect']):
            if targets.intersection(recipients(bm, ab)):
                ab.expires_at += value or 0
        bm._invalidate_buffs_cache()
        return True
    if stat in ('shield_restore_pct', 'decoy_heal_pct'):
        targets = bm._resolve_target(eff.get('target', 'self'), caster)
        for n in targets:
            stats = ('decoy',) if stat == 'decoy_heal_pct' else ('shield_from_max_hp_pct', 'shared_shield_from_max_hp_pct')
            for kind in stats:
                for ab in active(bm, n, kind, t):
                    current = ab.shield_per_target.get(n, 0)
                    if current <= 0:
                        continue
                    cap = getattr(ab, 'shield_capacity', {}).get(n, current)
                    new = min(cap, current + bm.effective_max_hp(caster) * (value or 0) / 100)
                    for recipient in ab.shield_per_target if kind == 'shared_shield_from_max_hp_pct' else [n]:
                        ab.shield_per_target[recipient] = new
        bm._invalidate_buffs_cache()
        return True
    return False


def before_activate(bm, eff, caster, t):
    # Multiple source clauses that refresh the same named shield share one pool.
    if eff.get('stat') in ('shield_from_max_hp_pct', 'shared_shield_from_max_hp_pct', 'debuff_block_charge'):
        for ab in list(bm._by_name(eff.get('name', ''))):
            if ab.caster == caster and ab.effect is not eff and ab.effect.get('stat') == eff.get('stat'):
                bm._active.remove(ab)
                bm._invalidate_buffs_cache()


def after_activate(bm, eff, caster, t):
    stat = eff.get('stat')
    if stat not in ('shield_from_max_hp_pct', 'shared_shield_from_max_hp_pct', 'decoy',
                    'atk_copy', 'hp_copy', 'damage_accumulate'):
        return
    ab = next((a for a in bm._active if a.effect is eff and a.caster == caster), None)
    if ab is None:
        return
    value = bm._get_value(eff, ab, caster) or 0
    if stat in ('shield_from_max_hp_pct', 'shared_shield_from_max_hp_pct', 'decoy'):
        multiplier = 1 + total(bm, caster, 'next_shield_hp_pct', t) / 100
        amount = bm.effective_max_hp(caster) * value / 100 * multiplier
        targets = bm.squad_names if stat == 'shared_shield_from_max_hp_pct' else recipients(bm, ab)
        ab.shield_per_target = {n: amount for n in targets}
        ab.shield_capacity = dict(ab.shield_per_target)
        for boost in list(active(bm, caster, 'next_shield_hp_pct', t)):
            remove(bm, boost, t)
    elif stat in ('atk_copy', 'hp_copy'):
        # Snapshot the donor before adding this effect; this avoids self-copy recursion.
        pool = [n for n in bm.squad_names if n != caster and alive(bm, n)]
        donor_value = max((bm._effective_atk(n) if stat == 'atk_copy' else bm.effective_max_hp(n) for n in pool), default=0)
        ab.copied_base = donor_value
        if stat == 'hp_copy':
            bm.state['hp'][caster] += donor_value * value / 100
            bm.sync_hp(caster)
    elif stat == 'damage_accumulate':
        ab.accumulated = 0.0
        boost = sum((bm._get_value(a.effect, a, caster) or 0) for a in active(bm, caster, 'accumulate_max_scale_pct', t)
                    if a.effect.get('target_effect') == eff.get('name'))
        ab.accumulate_cap = bm._effective_atk(caster) * value / 100 * (1 + boost / 100)
    bm._invalidate_buffs_cache()


def augment_buffs(bm, caster, target, t, buffs):
    for ab in active(bm, caster, 'atk_copy', t):
        buffs['atk_flat'] += getattr(ab, 'copied_base', 0) * (bm._get_value(ab.effect, ab, caster) or 0) / 100
    fixed = list(active(bm, caster, 'reload_speed_fixed', t))
    if fixed:
        value = bm._get_value(fixed[-1].effect, fixed[-1], caster) or 0
        buffs['reload_speed_pct'] = value
        buffs.get('_quant_parts', {})['reload_speed_pct'] = [value]
    for ab in active(bm, target, 'received_dmg_buff_mag_pct', t):
        for base in active(bm, target, 'received_dmg_pct', t):
            if base.effect.get('name') == ab.effect.get('target_effect'):
                buffs['received_dmg'] += (bm._get_value(base.effect, base, target) or 0) * (bm._get_value(ab.effect, ab, target) or 0) / 100


def hp_edges(bm, name, previous, current):
    if bm.state.get('_roster_hp_edge') or previous is None or current >= previous:
        return
    bm.state['_roster_hp_edge'] = True
    try:
        for key in list(bm._notify_index.get(name, {})):
            if key.startswith('hp_below:'):
                threshold = float(key.split(':')[1])
                if previous > threshold >= current:
                    bm.notify(key, bm._cur_t, name)
        from .buff_manager import _NIKKE
        if _NIKKE[name].get('class') == '방어형' and previous > 50 >= current:
            for n in bm.squad_names:
                bm.notify('event:defender_hp_below:50', bm._cur_t, n, subject=name)
    finally:
        bm.state['_roster_hp_edge'] = False


def consume_debuff_charge(bm, name, t):
    for ab in active(bm, name, 'debuff_block_charge', t):
        charges = getattr(ab, 'charges', None)
        if charges is None:
            ab.charges = charges = {n: 1 for n in recipients(bm, ab)}
        if charges.get(name, 0) > 0:
            charges[name] -= 1
            return True
    return False


def shield_hit(bm, name, amount, t):
    for stat in ('decoy', 'shield_from_max_hp_pct', 'shared_shield_from_max_hp_pct'):
        for ab in active(bm, name, stat, t):
            hp = ab.shield_per_target.get(name, 0)
            if hp <= 0:
                continue
            if any(active(bm, ab.caster, 'shield_invincible', t)):
                return 'shield', 0.0
            absorbed = min(hp, amount)
            new = hp - absorbed
            for n in ab.shield_per_target if stat == 'shared_shield_from_max_hp_pct' else [name]:
                ab.shield_per_target[n] = new
            bm._invalidate_buffs_cache()
            if new <= 0:
                bm.notify('event:shield_consumed', t, name)
                if not any(v > 0 for v in ab.shield_per_target.values()):
                    remove(bm, ab, t)
            return ('decoy' if stat == 'decoy' else 'shield'), absorbed
    return None, 0.0


def hurt_hp(bm, name, amount, t, *, share=True):
    """Apply HP damage once; shared damage cannot recursively redistribute."""
    if not alive(bm, name) or any(active(bm, name, 'invincible', t)):
        return 0.0
    if share:
        for stat in ('damage_share_weighted', 'damage_share'):
            group = next(active(bm, name, stat, t), None)
            if group:
                members = [n for n in recipients(bm, group) if alive(bm, n)]
                weights = {n: (4.0 if n == group.caster else 1.5) if stat == 'damage_share_weighted' else 1.0 for n in members}
                runtime = bm.state.get('encounter_runtime')
                cover = runtime and any(active(bm, group.caster, 'cover_damage_share', t)) and runtime.cover.get(group.caster, 0) > 0
                # Native DamageShare values: user +300%, allies +50%, cover +13000%.
                denom = sum(weights.values()) + (131.0 if cover else 0)
                if cover:
                    runtime.cover[group.caster] = max(0, runtime.cover[group.caster] - amount * 131 / denom)
                return sum(hurt_hp(bm, n, amount * weight / denom, t, share=False) for n, weight in weights.items())
    hp = bm.state['hp']
    before = hp[name]
    if amount >= before:
        bm.notify('event:lethal_hit', t, name)
    floor = 1.0 if any(active(bm, name, 'undying', t)) else 0.0
    hp[name] = max(floor, before - amount)
    bm.sync_hp(name)
    bm.notify('received_hit', t, name)
    # Stored excess healing is consumed only after an attack leaves the recipient alive.
    if hp[name] > 0:
        reserve = bm.state.setdefault('stored_healing', {}).get(name, 0)
        restored = min(reserve, max(0, bm.effective_max_hp(name) - hp[name]))
        hp[name] += restored
        bm.state['stored_healing'][name] = reserve - restored
        bm.sync_hp(name)
    elif before > 0:
        bm.state.setdefault('deaths', []).append({'t': t, 'unit': name})
        bm.notify('event:self_down', t, name)
        for n in bm.squad_names:
            if n != name:
                bm.notify('event:ally_down', t, n, subject=name)
    return before - hp[name]


def register_handlers(bm, char_states, sim_log):
    bm.state['char_states'] = char_states

    def revive(eff, caster, t, value):
        for n in bm._resolve_target(eff.get('target', 'self'), caster):
            if not alive(bm, n):
                bm.state['hp'][n] = bm.effective_max_hp(n) * max(0, min(100, value)) / 100
                bm.sync_hp(n)
                bm.state.setdefault('revives', []).append({'t': t, 'unit': n, 'caster': caster})

    def cover(eff, caster, t, value):
        runtime = bm.state.get('encounter_runtime')
        if not runtime or not hasattr(runtime, 'cover'):
            return
        for n in bm._resolve_target(eff.get('target', 'self'), caster):
            if n not in runtime.cover:
                continue
            before = runtime.cover[n]
            if eff['stat'] == 'cover_revive_pct':
                if before <= 0:
                    runtime.cover[n] = runtime.cover_max[n] * value / 100
            elif before > 0:
                basis = bm.effective_max_hp(caster) if eff['stat'] == 'cover_heal_hp_pct' else runtime.cover_max[n]
                runtime.cover[n] = min(runtime.cover_max[n], before + basis * value / 100)
            if runtime.cover[n] > before:
                bm.notify('event:cover_heal_received', t, n, healer=caster)
                bm.notify('event:cover_heal', t, n, healer=caster)

    bm.register_instant_handler('revive_hp_pct', revive)
    for stat in ('cover_heal_hp_pct', 'cover_heal_pct', 'cover_revive_pct'):
        bm.register_instant_handler(stat, cover)


def record_damage(bm, caster, amount, t, hit_type):
    if amount <= 0 or hit_type.get('fixed_copy'):
        return
    if hit_type.get('is_normal_atk'):
        previous = bm.state.setdefault('last_normal_hit', {}).get(caster)
        value = amount + (previous[1] if previous and previous[0] == t else 0)
        bm.state['last_normal_hit'][caster] = (t, value)
    for ab in list(bm._by_stat('damage_accumulate')):
        if t >= ab.expires_at:
            continue
        if ab.effect.get('accumulate_source') == 'self' and ab.caster != caster:
            continue
        ratio = ab.effect.get('accumulate_ratio', 100) + total(bm, ab.caster, 'accumulate_ratio_pct', t)
        ab.accumulated = min(getattr(ab, 'accumulate_cap', 0), getattr(ab, 'accumulated', 0) + amount * ratio / 100)
        if ab.effect.get('detonate_at_cap') and ab.accumulated >= ab.accumulate_cap:
            detonate(bm, ab, t)


def detonate(bm, ab, t):
    amount = getattr(ab, 'accumulated', 0)
    caster, name = ab.caster, ab.effect.get('name', 'Accumulated damage')
    remove(bm, ab, t)
    if amount > 0 and bm._damage_handler:
        bm._damage_handler({'source': ab.effect['source'], 'type': 'damage',
            'stat': 'fixed_split_damage', 'name': name, 'target': 'all_enemies',
            'trigger': {'timing': [], 'condition': []}, 'fixed_value': amount}, caster, t)


def tick(bm, t):
    for ab in list(bm._by_stat('damage_accumulate')):
        if t >= ab.expires_at:
            detonate(bm, ab, t)
    # Cover maximum-HP bonuses heal by the increase, and shrink without killing
    # the remaining cover when the bonus expires.
    runtime = bm.state.get('encounter_runtime')
    if runtime and hasattr(runtime, 'cover_max'):
        bases = bm.state.setdefault('base_cover_max', dict(runtime.cover_max))
        for n, base in bases.items():
            addition = bm.effective_max_hp(n) * total(bm, n, 'cover_max_hp_from_hp_pct', t) / 100
            maximum = base + addition
            change = maximum - runtime.cover_max[n]
            if runtime.cover.get(n, 0) > 0:
                runtime.cover[n] = min(maximum, runtime.cover[n] + max(0, change))
            runtime.cover_max[n] = maximum
    # Excess healing cannot outlive the storage buff that supplied its capacity.
    for n in list(bm.state.get('stored_healing', {})):
        if not any(active(bm, n, 'heal_overcharge_store', t)):
            bm.state['stored_healing'].pop(n, None)
