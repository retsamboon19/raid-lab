"""Focused behavior checks for Guilty/Sin bunny kits.

Run with ``python -m runner.bunny_kits``.  These checks use the normal simulator
entry points and intentionally build characters with ``no_layer=True`` so app or
runner defaults cannot hide mode behavior.
"""

from __future__ import annotations

import json
from pathlib import Path

from calculator.timeline import simulate
from runner.spec import build_char


GUILTY = "길티 : 마이티 바니"
SIN = "신 : 스위프트 바니"
STANCE = "바니 모드 : 스탠스"
ENGAGE = "바니 모드 : 인게이지"
HOLD = {"control": {"sequence": [{"t": 0.0, "action": "hold", "until": 2.2}]}}
ROOT = Path(__file__).resolve().parents[1]


def _squad(names, overrides=None):
    overrides = overrides or {}
    return [build_char(name, overrides.get(name), no_layer=True) for name in names]


def _run(names, overrides=None, duration=10.0, enemy_def=31_784, **config):
    cfg = {"duration": duration, "rng_mode": "expected", **config}
    return simulate(
        _squad(names, overrides), cfg, {"def": enemy_def}, verbose=True, seed=1
    )


def _events(result, name, kind="activate"):
    return [e for e in result.log.buff_events if e.name == name and e.kind == kind]


def test_source_values() -> None:
    data = json.loads((ROOT / "data" / "parsed_skills.json").read_text(encoding="utf-8"))

    def effect(char, name):
        return next(e for e in data[char] if e["name"] == name)

    assert effect(GUILTY, "어떻게 하는 게 좋아…?")["values"] == {
        str(i): v for i, v in enumerate(
            [11.88, 12.79, 13.7, 14.62, 15.53, 16.45, 17.36, 18.27, 19.19, 20.1], 1
        )
    }
    stomp = effect(GUILTY, "마이티 스톰프")
    assert stomp["damage_coeff"]["10"] == 101.3
    assert (stomp["charge_time"], stomp["full_charge_mult"], stomp["duration_bullets"]) == (1.5, 250, 1)
    assert stomp["burst_energy"] == 5.6

    shift = effect(SIN, "바니 시프트")
    assert shift["values"]["1"] == 9.07 and shift["values"]["10"] == 15.35
    piercing = effect(SIN, "스위프트 피어싱")
    assert piercing["damage_coeff"]["10"] == 73.22
    assert (piercing["input_type"], piercing["fire_rate"], piercing["max_ammo"]) == (
        "DOWN_Charge", 5.0, 999
    )
    assert (piercing["charge_time"], piercing["full_charge_mult"], piercing["burst_energy"]) == (
        0.5, 300, 2.8
    )


def test_opening_mode_sync_and_scope() -> None:
    names = [GUILTY, SIN, "test_B3"]
    result = _run(names, {GUILTY: HOLD}, duration=3.0)
    for bunny in (GUILTY, SIN):
        stance = [e for e in _events(result, STANCE) if e.target == bunny]
        engage = [e for e in _events(result, ENGAGE) if e.target == bunny]
        assert len(stance) == 1 and stance[0].t == 0
        assert len(engage) == 1 and 2.0 < engage[0].t < 2.1
    assert not [e for e in _events(result, STANCE) + _events(result, ENGAGE)
                if e.target == "test_B3"]


def test_two_holds_cancel_to_stance() -> None:
    result = _run(
        [GUILTY, SIN], {GUILTY: HOLD, SIN: HOLD}, duration=3.0, control_mode="warn"
    )
    # Both independent 1-second holds fire on the same frame. The second toggle
    # returns the pair to Stance, which is why the app must pick one leader.
    for bunny in (GUILTY, SIN):
        assert len([e for e in _events(result, ENGAGE, "expire") if e.target == bunny]) == 1
        assert len([e for e in _events(result, STANCE) if e.target == bunny]) == 2


def test_mighty_stomp_blocks_hold_toggle() -> None:
    seq = {"control": {"sequence": [
        {"t": 0.0, "action": "hold", "until": 2.2},
        {"t": 3.0, "action": "hold", "until": 5.9},
    ]}}
    result = _run(
        ["리틀 머메이드", "크라운", GUILTY, SIN], {GUILTY: seq}, duration=7.0
    )
    # The second threshold occurs while the one-shot weapon is still being held.
    # It must not create a second mode transition.
    assert len(_events(result, ENGAGE)) == 2
    assert not [e for e in _events(result, ENGAGE, "expire") if e.t > 2.1]
    fixed = [e for e in _events(result, "마이티 스톰프 차지시간고정", "expire")]
    assert len(fixed) == 1 and 5.8 < fixed[0].t < 6.0


def test_defense_ignore_normal_and_changed_weapon() -> None:
    def normal_damage(char, defense, engage):
        names = ["리틀 머메이드", "크라운", char, "test_B3"]
        result = _run(names, {char: HOLD} if engage else {}, duration=10.0,
                      enemy_def=defense)
        return [h.damage for h in result.hits
                if h.caster == char and h.skill_name == "기본 공격"]

    assert normal_damage(GUILTY, 0, False) != normal_damage(GUILTY, 150_000, False)
    # Each list includes its basic SR and its changed-weapon shots.
    for char in (GUILTY, SIN):
        assert normal_damage(char, 0, True) == normal_damage(char, 150_000, True)


def test_swift_piercing_fixed_charge_and_exclusion() -> None:
    names = ["리틀 머메이드", "크라운", SIN, "test_B3"]
    assisted = {
        "control": {"tap_fire": {"rate": 4.0, "release": 0.03, "window": "always"}},
        "equip_skills": {"charge_speed_pct": 99.0},
    }
    result = _run(names, {SIN: assisted}, duration=10.0)
    cast_t = next(e.t for e in result.log.burst_log
                  if e.caster == SIN and e.event == "stage:3 사용")
    end_t = next(e.t for e in _events(result, "스위프트 피어싱 차지시간고정", "expire"))
    mode_hits = [h for h in result.hits
                 if h.caster == SIN and h.skill_name == "기본 공격" and cast_t < h.t < end_t]
    assert len(mode_hits) == 9
    gaps = [b.t - a.t for a, b in zip(mode_hits, mode_hits[1:])]
    assert all(0.52 < gap < 0.55 for gap in gaps)
    for buff_name in ("바니 시프트 2", "바니 시프트 3"):
        assert not [e for e in _events(result, buff_name) if cast_t <= e.t < end_t]


def main() -> None:
    tests = [
        test_source_values,
        test_opening_mode_sync_and_scope,
        test_two_holds_cancel_to_stance,
        test_mighty_stomp_blocks_hold_toggle,
        test_defense_ignore_normal_and_changed_weapon,
        test_swift_piercing_fixed_charge_and_exclusion,
    ]
    for test in tests:
        test()
        print(f"PASS {test.__name__}")
    print(f"PASS bunny kits ({len(tests)} checks)")


if __name__ == "__main__":
    main()
