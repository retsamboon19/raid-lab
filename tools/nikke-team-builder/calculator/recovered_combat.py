"""Recovered numerical combat rules for installed client 2df7134a.

CalculateDamage RVA 0x063F2140: float32 rate buckets, then ordered float64
products. This module is a combat primitive, not a complete battle backend.
Native oracle fixtures bind its arithmetic to the original client routine.
"""
from ctypes import c_float
from functools import lru_cache
import math

CLIENT_SHA256 = '2df7134a6a9c3a8dbbde88402fc8d16d1d6c3f4c2d5e262bea78c3d78b96dd02'
RATE_NAMES = (
    'chargeDamageRate', 'criticalDamageRate', 'coreDamageRate', 'categoryRate',
    'burstDamageRate', 'bonusRangeRate', 'elementRate', 'breakRate',
    'addDamageRate', 'singleBurstDamageRate', 'instantAllBurstDamageRate',
    'sequentialAttackDamageRate', 'projectileDamageRate', 'partsDamageRate',
    'coreShotDamageRate', 'penetrationDamageRate', 'defIgnoreDamageRate',
    'durationDamageRate', 'barrierDamageRate', 'projectileExplosionDamageRate',
    'stickyProjectileCollisionDamageRate', 'resistRate',
)


def f32(value):
    return c_float(value).value


def double_to_long(value):
    """CommonUtil.DoubleToLong, RVA 0x06156DA0; finite signed-64-bit range.

    Math.Round(double, 5, ToEven) scales before rounding, unlike Python's
    decimal-place round algorithm. The second conversion is half-away from
    zero and uses the sign of the original input.
    """
    if not math.isfinite(value) or abs(value) >= 2**63:
        raise ValueError('Damage conversion requires a finite Int64-range value')
    stable = round(value * 100000.0) / 100000.0 if abs(value) < 1e16 else value
    return math.trunc(stable + (0.5 if value > 0.0 else -0.5))


def _trunc_div(numerator, denominator):
    quotient = abs(numerator) // denominator
    return -quotient if numerator < 0 else quotient


def apply_target_reduction(damage, reduction_rate=0, reduction_value=0,
                           element_rate=0, element_value=0,
                           debuff_decrease_rate=0, share_increase=0,
                           is_share_instant=False):
    """GetDamage's post-primitive phase (0x063F6C02..0x063F6EC2).

    Rates and values are original signed StatValue integers; 10000 is 100%.
    Callers must supply native fields, not guessed mappings from skill text.
    """
    rate = reduction_rate + element_rate
    value = reduction_value + element_value
    if rate < 0:
        rate = _trunc_div((debuff_decrease_rate + 10000) * rate, 10000)
    if value < 0:
        value = _trunc_div((debuff_decrease_rate + 10000) * value, 10000)
    scale = f32(0.0001)
    rate_float = f32(f32(rate) * scale)
    share_float = f32(-f32(share_increase) * scale) if is_share_instant else 0.0
    clamped = max(1.0, damage)
    reduction = f32(rate_float + share_float) * clamped + float(value)
    return max(1.0, clamped - reduction)


def normal_base_damage(attack, defence, damage_ratio, stat_damage_ratio=1.0,
                       def_ignore_ratio=0.0, defence_ratio_rate=0.0):
    """Recovered ordinary GetDamage branch; ratios already resolved by caller.

    This excludes the separate fixed-value and attack-only defence-ignore
    branches. It must not silently handle those as ordinary weapon damage.
    """
    ignore = min(f32(def_ignore_ratio), 1.0)
    defence_ratio = min(max(f32(defence_ratio_rate), 0.0), 1.0)
    remaining = f32(1.0 - ignore)
    effective_defence = max(f32(f32(defence) * remaining), 0.0)
    gate = max(f32(1.0 - f32(remaining * defence_ratio)), 0.0)
    value = f32(f32(attack) - effective_defence)
    value = f32(value * gate)
    value = f32(value * f32(stat_damage_ratio))
    return f32(value * f32(damage_ratio))


def _bucket(values):
    # Keep even the first subtract/add: cancellation is observable for floats.
    total = f32(f32(values[0] - 1.0) + 1.0)
    for value in values[1:]:
        total = f32(total + f32(value - 1.0))
    return total


@lru_cache(maxsize=4096)
def _rate_buckets(rates):
    r = tuple(map(f32, rates))
    return _bucket(r[7:21]), _bucket(r[1:6]), r[6], r[0], r[21]


def calculate_damage(damage, shotCount=1, muzzleCount=1, **rates):
    """Original 25-argument primitive, with named multipliers (neutral=1).

    Positive shot/muzzle counts are the supported battle-input contract.
    The client clamps muzzleCount to at most one; it does not divide by two
    for a two-muzzle weapon here. There is no minimum damage or rounding here.
    """
    unknown = rates.keys() - set(RATE_NAMES)
    if unknown:
        raise TypeError('Unknown native damage rates: ' + ', '.join(sorted(unknown)))
    if shotCount <= 0 or muzzleCount <= 0:
        raise ValueError('Damage input requires positive shot and muzzle counts')
    return calculate_damage_rates(damage, shotCount, muzzleCount,
                                  tuple(rates.get(name, 1.0) for name in RATE_NAMES))


def calculate_damage_rates(damage, shot_count, muzzle_count, rates):
    """Positional hot path; same ordering as RATE_NAMES, no inferred rates."""
    if len(rates) != 22:
        raise ValueError('CalculateDamage requires exactly 22 rates')
    typed, bonus, element, charge, resist = _rate_buckets(rates)
    return (typed * bonus * ((damage / float(shot_count)) / min(muzzle_count, 1))
            * element * charge * resist)
