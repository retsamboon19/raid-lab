import random
import unittest

from anomaly_qte_geometry import QTEBox
from anomaly_qte_shots import (
    CALIBRATED_AIM_ORIGIN,
    base_weapon_parameters,
    qte_shot_contacts,
    temporary_weapon_parameters,
)


class Runtime:
    def __init__(self):
        self.rng = random.Random(1)
        self.boxes = (
            QTEBox(1, (0, 0, 14.7), (0.85,) * 3),
            QTEBox(2, (2, 0, 14.7), (0.85,) * 3),
        )
        self.qte_ray_overrides = {}

    def active_qte_geometry(self):
        return self.boxes


class QTEShotTests(unittest.TestCase):
    def test_installed_base_weapon_rows_and_world_splash_scale(self):
        self.assertIsNone(base_weapon_parameters("unknown unit"))
        ar = base_weapon_parameters("크라운")
        self.assertEqual((ar["WeaponType"], ar["ShotCount"], ar["CenterShotCount"]),
                         ("MG", 1, 0))
        shotgun = base_weapon_parameters("드레이크")
        self.assertEqual((shotgun["WeaponType"], shotgun["ShotCount"]), ("SG", 10))
        rocket = base_weapon_parameters("에밀리아")
        self.assertEqual((rocket["WeaponType"], rocket["FireType"],
                          rocket["SpotExplosionRange"], rocket["explosion_radius"]),
                         ("RL", "HomingProjectile", 750, 7.5))

    def test_default_calibrated_ray_hits_red_box(self):
        shot = qte_shot_contacts(Runtime(), "크라운", "MG",
                                 {"is_normal_atk": True, "accuracy_circle": 0,
                                  "pellet_index": 0, "pellet_count": 1},
                                 {"id": 1}, {})
        self.assertEqual(shot["contacts"], [1])
        self.assertEqual(shot["origin"], CALIBRATED_AIM_ORIGIN)
        self.assertEqual(shot["calibration"], "calibrated_ui_pose")
        self.assertEqual(shot["path_model"], "instant_ray")
        self.assertLess(shot["impact_point"][2], 14.7)

    def test_rocket_splash_dedupes_and_includes_adjacent_gray(self):
        shot = qte_shot_contacts(Runtime(), "에밀리아", "RL",
                                 {"is_normal_atk": True, "accuracy_circle": 0},
                                 {"id": 1}, {})
        self.assertEqual(shot["contacts"], [1, 2])
        self.assertEqual(shot["path_model"], "projectile_ray_approximation")

    def test_observed_ray_overrides_target_aim_and_can_miss(self):
        runtime = Runtime()
        runtime.qte_ray_overrides["크라운"] = {
            "origin": (2, 0, 0), "direction": (0, 0, 2)}
        shot = qte_shot_contacts(runtime, "크라운", "MG",
                                 {"is_normal_atk": True}, {"id": 1}, {})
        self.assertEqual(shot["contacts"], [2])
        self.assertEqual(shot["calibration"], "observed_ray")
        miss = qte_shot_contacts(runtime, "크라운", "MG",
                                 {"is_normal_atk": True,
                                  "qte_ray": {"origin": (0, 0, 0), "direction": (1, 0, 0)}},
                                 {"id": 1}, {})
        self.assertEqual(miss["contacts"], [])
        self.assertIsNone(miss["impact_point"])

    def test_spread_can_physically_touch_gray_counter(self):
        class EdgeRng:
            def __init__(self):
                self.values = iter((1.0, 0.0))

            def uniform(self, low, high):
                return next(self.values)

        runtime = Runtime()
        runtime.rng = EdgeRng()
        shot = qte_shot_contacts(runtime, "드레이크", "SG",
                                 {"is_normal_atk": True, "accuracy_circle": 500,
                                  "pellet_index": 0, "pellet_count": 10},
                                 {"id": 1}, {})
        self.assertEqual(shot["contacts"], [2])

    def test_extra_pellet_does_not_repeat_center_pellet(self):
        class EdgeRng:
            def __init__(self):
                self.values = iter((1.0, 0.0))

            def uniform(self, low, high):
                return next(self.values)

        runtime = Runtime()
        runtime.rng = EdgeRng()
        parameters = {"WeaponType": "SG", "FireType": "Instant",
                      "ShotCount": 2, "CenterShotCount": 1,
                      "MuzzleCount": 1, "SpotExplosionRange": 0}
        hit = {"is_normal_atk": True, "accuracy_circle": 500,
               "pellet_index": 2, "pellet_count": 3,
               "native_weapon_geometry": parameters}
        shot = qte_shot_contacts(runtime, "드레이크", "SG", hit,
                                 {"id": 1}, {})
        self.assertEqual(shot["contacts"], [2])

    def test_temporary_weapon_needs_explicit_native_parameters(self):
        runtime = Runtime()
        hit = {"is_weapon_mode_skill": True, "weapon_changed": True,
               "accuracy_circle": 0}
        self.assertIsNone(qte_shot_contacts(runtime, "크라운", "MG", hit,
                                            {"id": 1}, {}))
        explicit = dict(base_weapon_parameters("크라운"))
        shot = qte_shot_contacts(runtime, "크라운", "MG",
                                 dict(hit, native_weapon_geometry=explicit),
                                 {"id": 1}, {})
        self.assertEqual(shot["contacts"], [1])
        self.assertIsNone(qte_shot_contacts(runtime, "unknown unit", "AR",
                                            {"is_normal_atk": True,
                                             "accuracy_circle": 0},
                                            {"id": 1}, {}))

    def test_native_replacement_class_controls_geometry_independently_of_damage_class(self):
        # Nayuta's parsed damage mode is RL; the installed replacement is an
        # instant SR with no explosion, unlike her homing RL base weapon.
        mode = temporary_weapon_parameters("나유타", "RL")
        self.assertEqual((mode["shot_id"], mode["WeaponType"], mode["FireType"]),
                         (1022302, "SR", "Instant"))
        shot = qte_shot_contacts(Runtime(), "나유타", "RL",
                                 {"is_weapon_mode_skill": True, "weapon_changed": True,
                                  "accuracy_circle": 0}, {"id": 1}, {})
        self.assertEqual(shot["contacts"], [1])
        self.assertEqual(shot["path_model"], "instant_ray")
        self.assertEqual(shot["calibration"], "installed_temporary_weapon_calibrated_ui_pose")

    def test_native_replacement_with_splash_reaches_neighbor(self):
        shot = qte_shot_contacts(Runtime(), "은화 : 택티컬 업", "RL",
                                 {"is_normal_atk": True, "weapon_changed": True,
                                  "accuracy_circle": 0}, {"id": 1}, {})
        self.assertEqual(shot["contacts"], [1, 2])
        self.assertIsNone(temporary_weapon_parameters("은화 : 택티컬 업", "RL", 1))

    def test_multitarget_replacement_is_not_mislabeled_as_one_projectile_ray(self):
        shot = qte_shot_contacts(Runtime(), "모더니아", "MG",
                                 {"is_normal_atk": True, "weapon_changed": True,
                                  "accuracy_circle": 0}, {"id": 1}, {})
        self.assertIsNone(shot)


if __name__ == "__main__":
    unittest.main()
