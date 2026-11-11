"""Reviewed installed153 Belorta: Pumpkin Witch rules (resource63/name5184)."""


def build(api):
    api.kit('벨로타 : 펌킨 위치')
    api.e(1, 'full_burst_start', 'self', 'stealth', duration=10,
          name='유령 분장', remove_on_direct_hit=True,
          native_function_group=2063101)
    api.e(1, 'full_burst_start', 'self', 'max_hp_pct', 1, 10,
          name='장난 준비', native_function_group=2063102)
    api.e(1, 'full_burst_start', 'allies_right', 'atk_caster_based_pct', 3, 10,
          name='플레이풀 리틀 위치 공격력', native_function_group=2063103)
    api.e(2, 'full_charge_hit', 'target', 'received_dmg_pct', 0, 10,
          condition='self_state:유령 분장', name='유령의 장난',
          native_function_group=2063201)
    api.e(2, 'full_charge', 'allies_right', 'dot_dmg_pct', 2, 5,
          name='트릭 오어 트릿! 지속 대미지', native_function_group=2063202)
    api.e(3, 'burst_cast', 'allies_right', 'atk_caster_based_pct', 0, 10,
          name='해피 할로윈! 공격력', native_function_group=1063305)
    api.e(3, 'burst_cast', 'allies_right', 'dot_dmg_pct', 2, 10,
          name='해피 할로윈! 지속 대미지', native_function_group=1063306)
