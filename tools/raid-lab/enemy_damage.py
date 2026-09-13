"""Ordinary incoming hit arithmetic recovered from the offline damage routine.

DEF is subtracted before both percentage multipliers. ShotCount divides the
attack's damage budget; scheduling those shots must not multiply that budget.
Geometry, attack modifiers and the minimum-hit clamp still need client checks.
"""

def incoming_hit(attack, defence, skill_value, stat_ratio, shot_count=1):
    return max(1., (attack - defence) * skill_value / 10000 * stat_ratio / 10000
               / max(1, shot_count))
