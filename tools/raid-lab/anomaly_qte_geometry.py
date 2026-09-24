"""Physical QTE box geometry recovered from the installed version 152 assets.

The four prefab roots have identity rotation/scale. Native
QuickTimeColliderPrefabData.SetData replaces each numbered child's local
position with QTEColPresetTable.ColPosition. All four prefab roots have an
authored z=16 offset. A passive live Indivilia capture confirmed the spawned
root's world position is (0, 0, 16); callers may override it if moved.
This module only tests geometry and
does not invent aim, pellet spread, occlusion, or firing decisions.
"""

from dataclasses import dataclass
import math


# Numbered GameObjects with enabled, non-trigger layer-18 BoxColliders in the
# current installed AssetBundles. Their names bind to QTE ColIndex. The root
# is authored at (0, 0, 16). Native Init::set_position affects an effect
# PlayableDirector, not this root; the root world position was also captured
# as (0, 0, 16) during a live Indivilia QTE setup.
DEFAULT_ROOT_POSITION = (0.0, 0.0, 16.0)
# Passive installed-client capture before and after an Indivilia QTE Play.
# These are world displacements per one UI reticle-local coordinate; the UI
# plane's world anchor and the firing origin move during battle and must be
# supplied at the shot time. This calibration is not a universal camera model.
CALIBRATED_UI_BASIS_X = (0.0025861, 0.0, 0.0)
CALIBRATED_UI_BASIS_Y = (0.0, 0.0025760, -0.0002257)
# Median plane intercept at world x=y=0 across 176 spaced live samples;
# observed post-QTE intercepts ranged 3.53 to 4.36 with camera movement.
# A default simulation can use this calibrated pose, while a time-dependent
# camera model should pass its own ui_plane_point to aimed_rays.
CALIBRATED_UI_PLANE_POINT = (0.0, 0.0, 3.96264)
PREFAB_BOX_SIDES = {
    "QTEPrefab_Indivilia": (1.7,) * 39,
    "QTEPrefab_MirrorContainer": (1.7,) * 39,
    "QTEPrefab_Ultra": (1.7,) * 39,
    "QTEPrefab_NoBG_Z9": (2.5,) * 31 + (1.7,) * 9,
}


@dataclass(frozen=True)
class QTEBox:
    collider_index: int
    center: tuple[float, float, float]
    half_extents: tuple[float, float, float]

    @property
    def bounds(self):
        return tuple((c - h, c + h) for c, h in zip(self.center, self.half_extents))


def prefab_box_side(prefab: str, collider_index: int) -> float:
    """Look up the numbered prefab child's exact BoxCollider side length."""
    sides = PREFAB_BOX_SIDES[prefab]
    if not isinstance(collider_index, int) or isinstance(collider_index, bool):
        raise ValueError("QTE collider index must be an integer")
    if collider_index < 1 or collider_index > len(sides):
        raise ValueError(f"{prefab} has no collider {collider_index}")
    return sides[collider_index - 1]


def active_qte_boxes(prefab: str, preset_rows, active_indices, *, root_position=DEFAULT_ROOT_POSITION):
    """Build boxes for active QTE ColIndex values, using authored positions.

    ``root_position`` is the prefab root's world position. The default is the
    authored position, confirmed in a live Indivilia QTE setup. Pass zero to
    compute relative coordinates. Inactive or cleared colliders must be
    excluded by the caller through ``active_indices``.
    """
    root = tuple(float(value) for value in root_position)
    if len(root) != 3 or not all(math.isfinite(value) for value in root):
        raise ValueError("QTE root position must be a finite 3D point")
    by_index = {}
    for row in preset_rows:
        index = int(row["ColIndex"])
        if index in by_index:
            raise ValueError(f"duplicate QTE collider {index} in one preset")
        by_index[index] = row
    boxes = []
    for index in sorted(set(active_indices)):
        row = by_index[index]
        position = tuple(float(value) for value in row["ColPosition"])
        if len(position) != 3 or not all(math.isfinite(value) for value in position):
            raise ValueError(f"invalid QTE collider position {index}")
        side = prefab_box_side(prefab, index)
        boxes.append(QTEBox(index, tuple(a + b for a, b in zip(root, position)), (side / 2,) * 3))
    return tuple(boxes)


def ray_aabb_distance(origin, direction, box: QTEBox, *, max_distance=math.inf):
    """Return first ray/box distance in world units, or None on a miss."""
    origin = tuple(float(value) for value in origin)
    direction = tuple(float(value) for value in direction)
    if len(origin) != 3 or len(direction) != 3:
        raise ValueError("ray needs 3D origin and direction")
    magnitude = math.sqrt(sum(value * value for value in direction))
    if not math.isfinite(magnitude) or magnitude == 0 or not math.isfinite(max_distance) and max_distance != math.inf:
        raise ValueError("invalid ray direction or distance")
    low, high = 0.0, float(max_distance)
    for axis, (minimum, maximum) in enumerate(box.bounds):
        speed = direction[axis] / magnitude
        if abs(speed) < 1e-12:
            if origin[axis] < minimum or origin[axis] > maximum:
                return None
            continue
        near = (minimum - origin[axis]) / speed
        far = (maximum - origin[axis]) / speed
        low = max(low, min(near, far))
        high = min(high, max(near, far))
        if low > high:
            return None
    return low


def sphere_aabb_hit(center, radius: float, box: QTEBox) -> bool:
    """Whether a physical overlap sphere touches this box, including tangency."""
    center = tuple(float(value) for value in center)
    radius = float(radius)
    if len(center) != 3 or not all(math.isfinite(value) for value in center) or not math.isfinite(radius) or radius < 0:
        raise ValueError("invalid overlap sphere")
    squared = sum((point - min(max(point, minimum), maximum)) ** 2
                  for point, (minimum, maximum) in zip(center, box.bounds))
    return squared <= radius * radius


def ray_hits(boxes, origin, direction, *, max_distance=math.inf):
    """Return distinct collider indices with ray distances, nearest first.

    Call once per pellet. The result includes geometry behind the first hit so
    the caller can apply the native occlusion or penetration rule separately.
    """
    hits = {}
    for box in boxes:
        distance = ray_aabb_distance(origin, direction, box, max_distance=max_distance)
        if distance is not None:
            hits[box.collider_index] = min(distance, hits.get(box.collider_index, math.inf))
    return tuple(sorted(hits.items(), key=lambda hit: (hit[1], hit[0])))


def sphere_hits(boxes, center, radius):
    """Return each overlapped collider index once, for one explosion."""
    return tuple(sorted({box.collider_index for box in boxes if sphere_aabb_hit(center, radius, box)}))


def native_shot_offsets(shot_count: int, center_shot_count: int,
                        accuracy_circle: float, rng, *, stored_ray=False):
    """Sample native pellet XY offsets before camera/world projection.

    The first ``center_shot_count`` rays share the unjittered center ray.
    Each remaining ray independently samples x in [-1,1], then y in
    [-sqrt(1-x²), +sqrt(1-x²)]. ``accuracy_circle`` is a diameter, so the
    sampled pair is scaled by half. For a stored Ray, native code applies an
    additional 0.001 multiplier to its origin XY. The UI path uses unscaled
    offsets in reticle-local coordinates.
    """
    if (not isinstance(shot_count, int) or isinstance(shot_count, bool)
            or not isinstance(center_shot_count, int) or isinstance(center_shot_count, bool)
            or shot_count < 0 or center_shot_count < 0 or center_shot_count > shot_count):
        raise ValueError("invalid shot or center shot count")
    accuracy_circle = float(accuracy_circle)
    if not math.isfinite(accuracy_circle) or accuracy_circle < 0:
        raise ValueError("invalid accuracy circle diameter")
    radius = accuracy_circle * 0.5 * (0.001 if stored_ray else 1.0)
    offsets = [(0.0, 0.0)] * center_shot_count
    for _ in range(shot_count - center_shot_count):
        x = rng.uniform(-1.0, 1.0)
        vertical = math.sqrt(max(0.0, 1.0 - x * x))
        y = rng.uniform(-vertical, vertical)
        offsets.append((x * radius, y * radius))
    return tuple(offsets)


def aimed_rays(origin, target, offsets, ui_plane_point, *,
               basis_x=CALIBRATED_UI_BASIS_X,
               basis_y=CALIBRATED_UI_BASIS_Y):
    """Turn UI-aim-mode reticle-local shot offsets into physical world rays.

    ``target`` is the desired world aim point, such as a red QTE box center.
    The unjittered aim lies where origin→target intersects the current UI
    reticle plane; ``ui_plane_point`` supplies one current world point on that
    plane. The measured local XY basis maps each offset onto that plane, and
    native ``GetRay`` then normalizes the vector from origin to the jittered
    point. This is not the stored-Ray mode, which jitters its ray origin in XY
    with a separate 0.001 factor. A caller must supply the live or modeled plane anchor
    and origin; the captured basis alone does not determine them.
    """
    vectors = [tuple(float(value) for value in item)
               for item in (origin, target, ui_plane_point, basis_x, basis_y)]
    if any(len(item) != 3 or not all(math.isfinite(v) for v in item)
           for item in vectors):
        raise ValueError("aim geometry must contain finite 3D points")
    origin, target, plane_point, bx, by = vectors
    normal = (bx[1] * by[2] - bx[2] * by[1],
              bx[2] * by[0] - bx[0] * by[2],
              bx[0] * by[1] - bx[1] * by[0])
    toward = tuple(b - a for a, b in zip(origin, target))
    divisor = sum(a * b for a, b in zip(normal, toward))
    if abs(divisor) < 1e-15:
        raise ValueError("aim path is parallel to UI reticle plane")
    distance = sum(a * (b - c) for a, b, c in zip(normal, plane_point, origin)) / divisor
    if distance <= 0:
        raise ValueError("UI reticle plane is behind aim origin")
    center = tuple(a + distance * b for a, b in zip(origin, toward))
    rays = []
    for offset in offsets:
        if len(offset) != 2 or not all(math.isfinite(float(v)) for v in offset):
            raise ValueError("shot offset must be a finite XY pair")
        x, y = (float(value) for value in offset)
        point = tuple(center[j] + x * bx[j] + y * by[j] for j in range(3))
        vector = tuple(value - origin[j] for j, value in enumerate(point))
        magnitude = math.sqrt(sum(value * value for value in vector))
        if magnitude == 0:
            raise ValueError("aim point coincides with origin")
        rays.append((origin, tuple(value / magnitude for value in vector)))
    return tuple(rays)
