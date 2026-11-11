"""Marian: Queen, installed153 + official KO/EN all-level source mapping."""

NAME = '마리안 : 퀸'
FRAY = '임전 : 의지를 벼린 창끝'
WISH = '임전 : 파고드는 소망'
WOUND = '약점 개방'
SPEAR = '다크 매터 창'
CORE = '파고드는 소망 · 코어 명중'


def build(api):
    api.kit(NAME)
    api.e(1, 'battle_start', 'self', 'into_the_fray', 1.0, -1,
          name=FRAY, into_the_fray=True, unremovable=True)
    api.damage(1, 'every:4s', 'enemies_random:1', 0,
               stat='sequential_damage:7', name=SPEAR,
               native_skill_id=1019101, sequential_interval=0.2,
               on_hit_enemy_effect=WOUND)
    # The same named state refreshes, never stacks. Spear recipients are supplied
    # by the damage handler, rather than a fresh random selection.
    api.e(1, 'hit_count:'+SPEAR+':1', 'same_target:'+SPEAR,
          'received_dmg_pct', 2, -1, name=WOUND, unremovable=True, undispellable=True,
          buff_group="marian_open_wounds")
    api.e(1, 'burst_cast', 'all_enemies', 'received_dmg_pct', 2, -1,
          name=WOUND, unremovable=True, undispellable=True,
          buff_group="marian_open_wounds")
    api.e(2, 'burst_cast', 'self', 'into_the_fray', 1.0, 10,
          name=WISH, into_the_fray=True)
    api.e(2, 'burst_cast', 'self', 'effect_interval', -2.0, 10,
          name='파고드는 소망 · 반복 주기', target_effect=SPEAR)
    api.damage(2, 'on_attack_count:2', 'enemies_with_buff:'+WOUND, 1,
               condition='self_state:'+WISH+'|target_state:'+WOUND,
               stat='core_damage', name=CORE, required_target_state=WOUND)
    api.e(2, 'full_burst_start', 'self', 'sequential_dmg_pct', 4, 10,
          condition='not_self_state:'+WISH, name='유사 세계 · 순차 공격')
    api.e(2, 'full_burst_start', 'self', 'core_dmg_pct', 6, 10,
          condition='self_state:'+WISH, name='유사 세계 · 코어 대미지')
    api.e(3, 'burst_cast', 'self', 'ammo_charge_pct', 0)
    api.e(3, 'burst_cast', 'self', 'mg_warmup_speed_pct', 1, 10)
    api.e(3, 'burst_cast', 'self', 'atk_pct', 3, 10)
    api.e(3, 'burst_cast', 'self', 'atk_dmg_pct', 5, 10)
    api.damage(3, value=7, name='머나먼 신세계', native_skill_id=1019301)
