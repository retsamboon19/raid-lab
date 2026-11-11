"""Rapunzel: Sanctuary, exact installed153 skill/Function coefficients.

Values are canonical roledata indexes at all ten levels; special target lists
and cast-entry predicates preserve the original mutually exclusive resurrection.
"""
NAME = '라푼젤 : 생츄어리'
CONSUMED = '나노 입자 소모'
BLESSING = '갓데스 블레싱'


def build(api):
    api.kit(NAME)
    e = api.e
    target = 'self_and_allies_state:into_the_fray'
    api.heal(1, 'full_charge', value=0, name='디바인 라이트 회복')
    e(1, 'full_burst_start', target, 'atk_dmg_pct', 1, 10,
      name='디바인 라이트 공격 대미지')
    for stat in ('charge_speed_buff_immune', 'charge_speed_debuff_immune'):
        e(1, 'full_charge_ready', 'self', stat, duration=-1,
          condition='during_full_charge', remove_on_event='charge_end')

    # Same event: construct the barrier before blessing gates future holds.
    gate = 'not_self_state:' + BLESSING
    e(2, 'charge_hold:1', 'self', 'shared_shield_from_max_hp_pct', 1, -1,
      gate, name='셀레스티얼 헤이븐 보호막', remove_on_event='charge_end')
    e(2, 'charge_hold:1', 'all_allies', 'def_caster_based_pct', 2, 10,
      gate, name=BLESSING)
    e(2, 'full_burst_start', target, 'atk_caster_based_pct', 4, 10,
      name='셀레스티얼 헤이븐 공격력')
    api.damage(2, 'full_charge', 'enemies_nearest_aim:1', 6, stat='bonus_damage',
               name='셀레스티얼 헤이븐 추가 대미지', native_skill_id=1473401,
               native_target_condition='IncludeNoneTargetLast')

    rescue = 'event_start_dead_at_least:3|event_start_not_self_state:' + CONSUMED
    # Connected StatAtk/StatDef affect the *revived* characters only. The
    # event-start selection survives the preceding Resurrection HP mutation.
    e(3, 'burst_cast', 'event_start_down_allies', 'revive_hp_pct', 0,
      condition=rescue, name='나노 입자 투여', max_trigger=1)
    e(3, 'burst_cast', 'event_start_down_allies', 'atk_caster_based_pct', 1, 10,
      rescue, name='나노 입자 투여 공격력', max_trigger=1)
    e(3, 'burst_cast', 'event_start_down_allies', 'def_caster_based_pct', 3, 10,
      rescue, name='나노 입자 투여 방어력', max_trigger=1)
    # ChangeCoolTimeUlti integer4000 is +40 seconds, represented by a negative
    # cooldown reduction in the production scheduler. It applies on this cast.
    e(1, 'burst_cast', 'self', 'burst_cooldown', 3, -1, rescue,
      negative=True, name='나노 입자 소모 재사용 시간', max_trigger=1,
      undispellable=True, persists_on_revive=True, reconcile_on_cast=True)
    # Native247310106 DelayValue10/100 is a real 0.1second delay.
    e(1, 'burst_cast', 'self', 'def_pct', 4, -1, rescue,
      name='나노 입자 소모 방어력', max_trigger=1, activation_delay=0.1,
      undispellable=True, persists_on_revive=True)
    e(1, 'burst_cast', 'self', None, duration=-1, condition=rescue,
      name=CONSUMED, max_trigger=1, undispellable=True, persists_on_revive=True)
    for gate, name in (
        ('event_start_dead_below:3|event_start_not_self_state:' + CONSUMED,
         '가든 오브 아르카디아 일반 공격력'),
        ('event_start_self_state:' + CONSUMED,
         '가든 오브 아르카디아 소모 후 공격력'),
    ):
        e(3, 'burst_cast', 'all_allies', 'atk_caster_based_pct', 5, 10,
          gate, name=name)
