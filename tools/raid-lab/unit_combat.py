"""Common unit-kit behavior for finite-HP boss encounters."""
from calculator import roster_mechanics as kits


def enemy_attack(runtime, attack):
    bm = runtime.bm
    percent = kits.total(bm, '__enemy__', 'atk_pct', runtime.time)
    flat = 0.0
    for ab in kits.active(bm, '__enemy__', 'atk_caster_based_pct', runtime.time):
        flat += bm.state['base_stats'][ab.caster]['atk'] * (bm._get_value(ab.effect, ab, ab.caster) or 0) / 100
    return max(0, attack * (1 + percent / 100) + flat)


def elemental_reduction(runtime, name, element):
    code = {100001: '작열', 200001: '수냉', 300001: '풍압', 400001: '전격', 500001: '철갑'}.get(element)
    return max(0, 1 + kits.total(runtime.bm, name, 'received_dmg_from_code:' + str(code), runtime.time) / 100)


def targetable(runtime, names):
    available = [n for n in names if not runtime.protection(n, 'stealth')]
    return available or names


def hit_shield(runtime, name, amount):
    return kits.shield_hit(runtime.bm, name, amount, runtime.time)


def cover_defence(runtime, name):
    return runtime.cover_def[name] * max(0, 1 + kits.total(runtime.bm, name, 'cover_def_pct', runtime.time) / 100)


def broadcast(runtime, event):
    if runtime.bm:
        for name in runtime.squad:
            runtime.bm.notify(event, runtime.time, name)
            if event == 'event:enemy_death':
                runtime.bm.notify('enemy_death', runtime.time, name)


def hurt(runtime, name, amount):
    return kits.hurt_hp(runtime.bm, name, amount, runtime.time)


def check_defeat(runtime):
    if not any(value > 0 for value in runtime.bm.state['hp'].values()):
        runtime.stop_reason = 'Squad defeated'
        runtime.stopped = True


def report(runtime):
    hp = runtime.bm.state.get('hp', {}) if runtime.bm else {}
    fallen = [n for n, value in hp.items() if value <= 0]
    return {'deaths': list(runtime.bm.state.get('deaths', [])) if runtime.bm else [],
            'revives': list(runtime.bm.state.get('revives', [])) if runtime.bm else [],
            'surviving_units': [n for n, value in hp.items() if value > 0],
            'survival': 'failed' if fallen or runtime.stop_reason else 'survived modeled attacks'}
