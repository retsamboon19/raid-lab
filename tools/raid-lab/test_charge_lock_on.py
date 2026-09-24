"""Charged shots retain lock-on recipients after their attack clears the lock."""

import unittest
from unittest.mock import patch

import core
from calculator.buff_manager import BuffManager


class ChargeLockOnTest(unittest.TestCase):
    def test_snow_white_heavy_arms_auto_fire_hits_locked_target(self):
        names = [
            "아니스 : 스타",
            "나유타",
            "스노우 화이트 : 헤비암즈",
            "라피 : 레드 후드",
            "프리바티",
        ]
        payload = {
            "roster": [{"id": name, "build": core.default_build()} for name in names],
            "members": names,
            "settings": {
                "content_mode": "anomaly",
                "boss_id": "anomaly-indivilia",
                "duration": 30,
                "playstyle": "auto",
            },
        }
        results = []
        original = core.simulate
        original_notify = BuffManager.notify
        shot_events = []

        def capture(*args, **kwargs):
            result = original(*args, **kwargs)
            results.append(result)
            return result

        def record_notify(manager, event, t, caster, **ctx):
            if (caster == "스노우 화이트 : 헤비암즈"
                    and event in ("on_attack", "full_charge_fire")):
                shot_events.append((event, t))
            return original_notify(manager, event, t, caster, **ctx)

        with patch.object(core, "simulate", side_effect=capture), \
             patch.object(BuffManager, "notify", record_notify):
            core.manual(payload)

        auto_fire = [
            hit for hit in results[0].hits
            if hit.caster == "스노우 화이트 : 헤비암즈"
            and hit.skill_name == "오토 파이어 2"
        ]
        self.assertTrue(auto_fire)
        self.assertTrue(all(hit.damage > 0 for hit in auto_fire[:5]))
        first_shot = shot_events[0][1]
        self.assertEqual(
            [event for event, t in shot_events if t == first_shot][:2],
            ["on_attack", "full_charge_fire"],
        )


if __name__ == "__main__":
    unittest.main()
