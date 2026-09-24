import unittest
import json
from pathlib import Path

from anomaly_qte_geometry import (
    active_qte_boxes,
    prefab_box_side,
    ray_aabb_distance,
    ray_hits,
    sphere_aabb_hit,
    sphere_hits,
    native_shot_offsets,
    aimed_rays,
    CALIBRATED_UI_BASIS_X,
    CALIBRATED_UI_BASIS_Y,
)


class QTEGeometryTests(unittest.TestCase):
    def test_ui_local_jitter_projects_through_reticle_plane(self):
        rays = aimed_rays((0, 0, 0), (0, 0, 10), ((0, 0), (10, 0), (0, 10)),
                          (0, 0, 4), basis_x=(0.01, 0, 0), basis_y=(0, 0.01, 0))
        self.assertEqual(rays[0], ((0.0, 0.0, 0.0), (0.0, 0.0, 1.0)))
        self.assertAlmostEqual(rays[1][1][0] / rays[1][1][2] * 10, 0.25)
        self.assertAlmostEqual(rays[2][1][1] / rays[2][1][2] * 10, 0.25)
        self.assertAlmostEqual(CALIBRATED_UI_BASIS_X[0], 0.0025861)
        self.assertAlmostEqual(CALIBRATED_UI_BASIS_Y[2], -0.0002257)

    def test_ui_plane_position_controls_spread_but_not_center_aim(self):
        near = aimed_rays((1, 0, -1), (0, 0, 15), ((0, 0), (10, 0)), (0, 0, 3))
        far = aimed_rays((1, 0, -1), (0, 0, 15), ((0, 0), (10, 0)), (0, 0, 5))
        self.assertEqual(near[0], far[0])
        self.assertNotEqual(near[1], far[1])
        with self.assertRaises(ValueError):
            aimed_rays((0, 0, 0), (0, 0, 10), ((0, 0),), (0, 0, -1))

    def test_native_pellet_sampling_centers_and_disc_chords(self):
        class FixedRng:
            def __init__(self):
                self.values = [0.6, 0.4, -1.0, 0.0]
                self.ranges = []

            def uniform(self, low, high):
                self.ranges.append((low, high))
                return self.values.pop(0)

        rng = FixedRng()
        offsets = native_shot_offsets(4, 2, 100.0, rng)
        self.assertEqual(offsets[:2], ((0, 0), (0, 0)))
        self.assertAlmostEqual(offsets[2][0], 30.0)
        self.assertAlmostEqual(offsets[2][1], 20.0)
        self.assertEqual(offsets[3], (-50.0, 0.0))
        self.assertAlmostEqual(rng.ranges[1][0], -0.8)
        self.assertAlmostEqual(rng.ranges[1][1], 0.8)
        stored = native_shot_offsets(1, 0, 100.0, FixedRng(), stored_ray=True)[0]
        self.assertAlmostEqual(stored[0], 0.03)
        self.assertAlmostEqual(stored[1], 0.02)

    def test_all_four_recovered_presets_have_matching_numbered_boxes(self):
        data = json.loads((Path(__file__).with_name("raid-boss-combat-data.json")).read_text(encoding="utf-8"))
        for key in ("anomaly-indivilia", "anomaly-mirror-container", "anomaly-ultra", "anomaly-harvester"):
            profile = data["profiles"][key]
            for qte in profile["qtes"]:
                for group in qte["GroupId"]:
                    rows = [row for row in profile["qte_targets"] if row["GroupId"] == group]
                    indices = [row["ColIndex"] for row in rows]
                    self.assertTrue(indices, (key, group))
                    boxes = active_qte_boxes(qte["QtePrefab"], rows, indices)
                    self.assertEqual(len(boxes), len(rows), (key, group))

    def test_installed_prefab_sizes_bind_to_numbered_collider(self):
        for name in ("QTEPrefab_Indivilia", "QTEPrefab_MirrorContainer", "QTEPrefab_Ultra"):
            self.assertEqual(prefab_box_side(name, 1), 1.7)
            self.assertEqual(prefab_box_side(name, 39), 1.7)
            with self.assertRaises(ValueError):
                prefab_box_side(name, 40)
        self.assertEqual(prefab_box_side("QTEPrefab_NoBG_Z9", 31), 2.5)
        self.assertEqual(prefab_box_side("QTEPrefab_NoBG_Z9", 32), 1.7)
        self.assertEqual(prefab_box_side("QTEPrefab_NoBG_Z9", 40), 1.7)

    def test_authored_positions_replace_prefab_grid_positions(self):
        rows = [
            {"ColIndex": 1, "ColPosition": [0.0, 8.0, 1.0]},
            {"ColIndex": 2, "ColPosition": [-1.4, 6.6, 1.0]},
            {"ColIndex": 3, "ColPosition": [-2.8, 5.2, 1.0]},
        ]
        boxes = active_qte_boxes("QTEPrefab_Indivilia", rows, [2, 1], root_position=(0, 0, 10))
        self.assertEqual([box.collider_index for box in boxes], [1, 2])
        self.assertEqual(boxes[0].center, (0.0, 8.0, 11.0))
        self.assertEqual(boxes[1].center, (-1.4, 6.6, 11.0))
        self.assertAlmostEqual(boxes[0].half_extents[0], 0.85)
        self.assertAlmostEqual(boxes[0].bounds[0][0], -0.85)

    def test_default_world_root_matches_live_qte_root_capture(self):
        rows = [{"ColIndex": 1, "ColPosition": [0.0, 1.0, -1.3]}]
        box = active_qte_boxes("QTEPrefab_Indivilia", rows, [1])[0]
        self.assertEqual(box.center, (0.0, 1.0, 14.7))

    def test_ray_hit_distances_and_occluded_candidates(self):
        rows = [
            {"ColIndex": 1, "ColPosition": [0, 0, 0]},
            {"ColIndex": 2, "ColPosition": [0, 0, 2]},
            {"ColIndex": 3, "ColPosition": [5, 0, 0]},
        ]
        boxes = active_qte_boxes("QTEPrefab_Ultra", rows, [1, 2, 3], root_position=(0, 0, 0))
        hits = ray_hits(boxes, (0, 0, -5), (0, 0, 2))
        self.assertEqual([index for index, _ in hits], [1, 2])
        self.assertAlmostEqual(hits[0][1], 4.15)
        self.assertAlmostEqual(hits[1][1], 6.15)
        self.assertIsNone(ray_aabb_distance((0, 0, -5), (0, 0, 1), boxes[2]))
        self.assertEqual(ray_aabb_distance((0, 0, 0), (1, 0, 0), boxes[0]), 0)
        self.assertEqual(ray_hits(boxes, (0, 0, -5), (0, 0, 1), max_distance=4), ())

    def test_sphere_overlap_can_reach_adjacent_counter_box(self):
        rows = [
            {"ColIndex": 1, "ColPosition": [0, 0, 0]},
            {"ColIndex": 2, "ColPosition": [2, 0, 0]},
            {"ColIndex": 3, "ColPosition": [5, 0, 0]},
        ]
        boxes = active_qte_boxes("QTEPrefab_MirrorContainer", rows, [1, 2, 3], root_position=(0, 0, 0))
        self.assertEqual(sphere_hits(boxes, (0, 0, 0), 1.15), (1, 2))
        self.assertFalse(sphere_aabb_hit((0, 0, 0), 1.14, boxes[1]))
        self.assertTrue(sphere_aabb_hit((0, 0, 0), 1.15, boxes[1]))
        self.assertEqual(sphere_hits(boxes + (boxes[1],), (0, 0, 0), 1.15), (1, 2))


if __name__ == "__main__":
    unittest.main()
