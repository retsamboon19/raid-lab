"""Ordinary incoming hit arithmetic recovered from the offline damage routine.

DEF is subtracted before the percentage and elemental multipliers. The original
CalculateDamage divides by its runtime ShotCount; projectile construction passes
one here even when the skill table declares a multi-shot volley. Callers supply
the effective divisor from the appropriate legacy or timeline dispatch path.
GetDamage then clamps this pre-reduction result to one. Reduction, final rounding
and collision handling are owned by the caller.
"""

def incoming_hit(attack, defence, skill_value, stat_ratio, shot_count=1, element_multiplier=1):
    return max(1., (attack - defence) * skill_value / 10000 * stat_ratio / 10000
               / max(1, shot_count) * element_multiplier)
