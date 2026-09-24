"""Source-driven projectile lifecycle for Anomaly Mirror Container and Indivilia.

The installed 152.8.11 tables identify launch grouping, interception HP/DEF,
target rules and damage.  Native code scales ``ProjectileSpeed`` by exactly
the float stored at GameAssembly RVA 0x8627d20, constructs the curve from the
live launcher and target transforms, and advances it using endpoint distance.
This module therefore gives every normal-run projectile a deterministic flight
window using that native formula.  Boss movement points are exact; muzzle
positions are prefab bind poses. Target positions use the measured shared
five-slot formation and stance endpoints unless the caller supplies a live
transform. Stance transitions still require animated geometry.

Integration contract
--------------------
``build_anomaly_mechanics(runtime)`` returns a mechanics object for the exact
Anomaly Mirror Container and Indivilia profiles.  A composite dispatcher should
delegate ``perform_skill``, ``advance``, ``resolve_target`` and ``resolve_hit``
to this object.  ``perform_skill`` returns true for owned curve-projectile
skills so the common runtime must not apply their damage immediately.

Primary evidence
----------------
* ``private/offline-tables/MonsterSkillTable.mpk.json``: skill rows.
* ``raid-boss-combat-data.json``: selected Anomaly monster, stage and stat rows.
* ``private/offline-assets/raid-xba001_psid_intercept-components.json`` and
  ``raid-ebg003_anmi_intercept-components.json``: weapon/muzzle bindings.
* ``private/anomaly-audit/shared-source/current-native-source/``:
  ``MonsterAttackLogic-TimeLineProjectileCurve-current.asm``,
  ``ProjectileCurveMovement-SetProjectilePoint-current.asm``, and
  ``SpotProjectileBezierCurveRunner-Play-current.asm``.  The last two read the
  live GameObject transforms and endpoint-distance curve advancement.
  ``ProjectileContext-OnMonsterPartsDestroy.asm`` and
  ``ProjectileContext-OnMonsterCutSceneStart.asm`` show that those events only
  process the separate sticky-arrival list, so already launched curve shots
  remain in flight. ``MonsterContext-OnDestroyParts-current.asm`` and
  ``MonsterContext-OnMonsterCutSceneStart-current-full.asm`` show the separate
  launch-coroutine rule: a matching cancelable part skill, or the death
  cutscene (scene type 4), stops launches that have not happened yet.
"""

from __future__ import annotations

import math


MIRROR_KEY = "anomaly-mirror-container"
INDIVILIA_KEY = "anomaly-indivilia"

MIRROR_PROJECTILES = frozenset((520661, 520672, 520673, 520674, 520675,
                                520678, 520679))
INDIVILIA_PROJECTILES = frozenset((531474,))
PROJECTILE_SKILLS = MIRROR_PROJECTILES | INDIVILIA_PROJECTILES
TIMELINE_PROJECTILES = frozenset((520672, 520673, 520674, 520675))

# Muzzle names are evidence about launch sources, not static flight endpoints:
# animation changes their world positions.  Mirror's WeaponObject18 has two
# simultaneous launchers; Indivilia's WeaponObject10 has six prefab entries.
LAUNCH_SOCKETS = {
    520661: ("socket_muzzle_fire_19", "socket_muzzle_fire_18"),
    520672: ("socket_muzzle_fire_07",),
    520673: ("socket_muzzle_fire_09",),
    520674: ("socket_muzzle_fire_08",),
    520675: ("socket_muzzle_fire_10",),
    520678: ("socket_muzzle_fire_11",),
    520679: ("socket_muzzle_fire_12",),
    531474: tuple(f"socket_muzzle_fire_{n:02d}" for n in (13, 16, 11, 14, 12, 15)),
}

# Absolute model-space bind positions, after the model's xba001_var rotation.
# These are added to the exact live BossWorld movement-point coordinate.  The
# remaining error is muzzle animation at the attack frame, exposed in every
# projectile's geometry metadata instead of being presented as native truth.
LAUNCHER_BIND_POSITIONS = {
    "socket_muzzle_fire_19": (1.598728706, 25.540464429, -8.846742374),
    "socket_muzzle_fire_18": (-1.584766, 25.508302, -8.849292),
    "socket_muzzle_fire_07": (-15.350312, 32.888769, -2.575740),
    "socket_muzzle_fire_09": (-14.874889, 4.287601, -2.869151),
    "socket_muzzle_fire_08": (15.354771, 32.893228, -2.629336),
    "socket_muzzle_fire_10": (14.864166, 4.298470, -2.800642),
    "socket_muzzle_fire_11": (-17.663716656, 17.845350608, -1.868519835),
    "socket_muzzle_fire_12": (17.664000127, 17.845347711, -1.868521086),
    "socket_muzzle_fire_13": (-5.397379, 34.463506, 9.480689),
    "socket_muzzle_fire_16": (10.794637, 33.271023, 9.072955),
    "socket_muzzle_fire_11@indivilia": (-10.794639, 33.271021, 9.072954),
    "socket_muzzle_fire_14": (8.198415, 33.830674, 9.365302),
    "socket_muzzle_fire_12@indivilia": (-8.198416, 33.830670, 9.365304),
    "socket_muzzle_fire_15": (5.397376, 34.463511, 9.480688),
}

NATIVE_SPEED_SCALE = 0.009999999776482582
NATIVE_DISTANCE_SCALE = 0.01
# Hidden-client GetHeadPosition/GetCoverPosition observations independently
# matched across Ultra, Harvester and Mirror; Indivilia sampled slots 1–3.
# GetHeadPosition returns collider.transform.position, not bounds.center.
FORMATION_AIM = ((-5.0, -.5, 4.5), (-2.3, -.5, 2.5), (.1, -.5, 4.5),
                 (3.1, -.5, 2.5), (5.8, -.5, 4.5))
FORMATION_COVER = ((-6.128, -2.349, 4.7), (-3.428, -2.349, 2.7),
                   (-1.028, -2.349, 4.7), (1.972, -2.349, 2.7),
                   (4.672, -2.349, 4.7))
# Four slots directly reached this endpoint in the traces. Slot 2 uses the
# same local stance translation; its trace only sampled the moving pose.
HIDE_TRANSLATION = (-1.035, -1.7, 0.0)
DEFAULT_BOSS_POSITIONS = {
    MIRROR_KEY: (0.0, 0.0, 75.0),
    INDIVILIA_KEY: (0.0, 3.59, 40.0),
}


def _rounded_hp(value):
    """Match CommonUtil.DoubleToLong: round to 5 places, positive half-up."""
    return math.floor(round(value, 5) + 0.5)


class AnomalyProjectileMechanics:
    """Lifecycle and interception for the two exact Anomaly profiles."""

    handles_summons = False

    def __init__(self, runtime):
        self.runtime = runtime
        runtime.damage_to_projectiles = getattr(runtime, "damage_to_projectiles", 0.0)

    @property
    def assumptions(self):
        return [
            "Projectile flight uses native endpoint-distance/speed progression with "
            "exact boss points and prefab bind-pose muzzles; attack-frame animation "
            "remains approximate. Character and cover positions use the measured "
            "shared formation; stance endpoints do not reproduce the transition "
            "animation, and slot 2's hiding endpoint uses the shared translation.",
        ]

    def _owns(self, skill):
        ident = skill.get("Id")
        if self.runtime.key == MIRROR_KEY:
            return ident in MIRROR_PROJECTILES
        if self.runtime.key == INDIVILIA_KEY:
            return ident in INDIVILIA_PROJECTILES
        return False

    def _cancel_pending(self, predicate, reason, time):
        """Cancel only shots that native ``StopFire`` has not launched yet."""
        cancelled = 0
        for projectile in self.runtime.projectiles:
            if (projectile.get("kind") != "hostile" or
                    projectile.get("status") != "pending" or
                    not self._owns(projectile.get("source_skill", {})) or
                    not predicate(projectile.get("source_skill", {}))):
                continue
            projectile.update(status="cancelled", clear_reason=reason,
                              cleared_at=time)
            cancelled += 1
        if cancelled:
            self.runtime.log("pending hostile projectile launches cancelled",
                             reason=reason, count=cancelled)
        return cancelled

    def on_part_broken(self, part, time, damaged=True):
        # TryGetCancelableSkill is selective: it stops the Fire coroutine only
        # when the active row names the destroyed part and uses BrokenParts
        # cancellation. None of the current Mirror/Indivilia projectile rows
        # qualify, but keeping the native predicate covers future rows.
        normalized = "".join(c for c in str(part).lower() if c.isalnum())
        return self._cancel_pending(
            lambda skill: (str(skill.get("CancelType", "")).startswith(
                               "BrokenParts") and
                           normalized in {
                               "".join(c for c in str(value).lower()
                                       if c.isalnum())
                               for value in skill.get("ControlParts", ())}),
            "launcher part destroyed", time)

    def on_cinematic_start(self, time):
        # Current native MonsterContext stops Fire only for sceneType 4
        # (Dead). Phase 2/3 does not cancel scheduled launches.
        return 0

    def on_phase_changed(self, phase, time):
        return self.on_cinematic_start(time)

    def _locked_target(self, node):
        targets = list(node.get("_locked_targets", ()))
        if not targets and self.runtime.bm:
            targets = self.runtime.attack_targets(node["_projectile_skill"], node)
        return targets[0] if targets else None

    def _boss_position(self):
        coordinates = getattr(getattr(self.runtime, "world", None),
                              "coordinates", None)
        if coordinates:
            return tuple(float(coordinates[axis]) for axis in ("x", "y", "z")), \
                   "BossWorld live movement point"
        return DEFAULT_BOSS_POSITIONS[self.runtime.key], "profile initial point"

    def _target_position(self, target, recipient="character"):
        observed = getattr(self.runtime, "projectile_target_positions", None) or {}
        if target in observed:
            value = observed[target]
            # Native CreateTargetData selects GetHeadPosition or
            # GetCoverPosition according to the recipient. Character collider
            # transforms also move when the unit changes stance.
            if isinstance(value, dict) and recipient in value:
                value = value[recipient]
            if isinstance(value, dict) and "aiming" in value:
                hiding = (target in getattr(self.runtime, "covered", ()) or
                          bool(getattr(getattr(self.runtime, "bm", None),
                                       "state", {}).get("planned_cover")))
                value = value.get("hiding" if hiding else "aiming")
            if isinstance(value, dict):
                value = (tuple(value[axis] for axis in ("x", "y", "z"))
                         if all(axis in value for axis in ("x", "y", "z")) else None)
            if value is not None:
                return tuple(map(float, value)), "runtime observed target transform"
        names = []
        if self.runtime.bm:
            names = list(self.runtime.bm.state.get("hp", {}))
        if target in names and names.index(target) < len(FORMATION_AIM):
            slot = names.index(target)
            if recipient == "cover":
                return FORMATION_COVER[slot], "measured shared cover transform"
            hiding = (target in getattr(self.runtime, "covered", ()) or
                      bool(self.runtime.bm.state.get("planned_cover")))
            if hiding:
                return tuple(a + b for a, b in zip(FORMATION_AIM[slot], HIDE_TRANSLATION)), \
                       "measured formation with shared hiding stance endpoint"
            return FORMATION_AIM[slot], "measured shared aiming stance endpoint"
        return (0.0, 0.0, 0.0), "unknown slot geometry proxy"

    def _launcher_bind(self, socket):
        key = socket
        if self.runtime.key == INDIVILIA_KEY and socket in (
                "socket_muzzle_fire_11", "socket_muzzle_fire_12"):
            key += "@indivilia"
        return LAUNCHER_BIND_POSITIONS[key]

    def _owner_defence(self, skill, stat):
        runtime = self.runtime
        bonus = sum(value / 10000 for ident, (end, value)
                    in getattr(runtime, "effects", {}).items()
                    if ident in runtime.functions and end > runtime.time
                    and runtime.functions[ident]["FunctionType"] == "StatDef")
        hook = getattr(getattr(runtime, "anomaly", None),
                       "defence_multiplier", None)
        multiplier = hook(runtime.time) if hook else None
        if multiplier is not None:
            bonus = multiplier - 1
        return (stat["LevelDefence"] * (1 + bonus) *
                skill["ProjectileDefRatio"] / 10000)

    def _activate(self, projectile):
        """Create native launch-time projectile stats and attacker snapshot."""
        runtime = self.runtime
        skill = projectile["source_skill"]
        stat = runtime.stat()
        hp = (_rounded_hp(stat["LevelProjectileHp"] *
                          skill["ProjectileHpRatio"] / 10000 /
                          projectile["projectile_hp_shot_divisor"])
              if projectile["destroyable"] else None)
        defence = projectile.get("volley_defence")
        if defence is None:
            defence = self._owner_defence(skill, stat)
        projectile.update(status="active", hp=hp, max_hp=hp,
                          defence=defence,
                          defence_snapshot=True,
                          defence_snapshot_at=projectile.get(
                              "volley_defence_at", runtime.time),
                          # ``advance`` can cross more than one scheduled fire
                          # time in a single simulation tick. Native snapshots
                          # at launch; report the model's actual capture time.
                          snapshot_at=runtime.time)
        capture = getattr(runtime, "capture_incoming_snapshot", None)
        if capture is not None and runtime.bm is not None:
            projectile["incoming_snapshot"] = capture()
            projectile["snapshot_at"] = projectile["incoming_snapshot"]["time"]
        return projectile

    def _spawn_one(self, skill, node, launcher_index, shot_index,
                   physical_index, fire_index, volley_defence=None,
                   volley_defence_at=None):
        runtime = self.runtime
        destroyable = bool(skill["IsDestroyableProjectile"])
        physical_count = (len(LAUNCH_SOCKETS[skill["Id"]]) *
                          max(1, skill["ShotCount"]))
        # Ordinary AttackV2/V3 builds one FireData for the complete weapon
        # list and divides ProjectileHpRatio by ShotCount * total muzzle count.
        # TimeLineProjectileCurve instead divides HP only by ShotCount.  The
        # owned timeline rows each have one launcher, so both paths remain
        # explicit here rather than relying on that coincidence.
        hp_divisor = (max(1, skill["ShotCount"])
                      if skill["Id"] in TIMELINE_PROJECTILES
                      else physical_count)
        # The ordinary path divides SkillValue01 by total muzzle count.  Its
        # FireProjectile path copies that damage directly and does not read
        # FireData.ShotCount, so each ShotCount volley repeats the table budget.
        damage_divisor = (max(1, skill["ShotCount"])
                          if skill["Id"] in TIMELINE_PROJECTILES
                          else len(LAUNCH_SOCKETS[skill["Id"]]))
        projectile_damage_ratio = _rounded_hp(
            skill["SkillValue01"] / damage_divisor)
        projectile_skill = dict(skill, ShotCount=1,
                                SkillValue01=projectile_damage_ratio,
                                _damage_shots=1)
        projectile_node = dict(node)
        target = self._locked_target(dict(projectile_node,
                                          _projectile_skill=skill))
        if target is not None:
            projectile_node["_locked_targets"] = [target]
        target_kind = ("cover" if skill.get("TargetCoverRatio") == 100
                       else "character")
        # Preserve the table's intended recipient.  In particular, a missile
        # aimed at a destroyed cover does not silently turn into character hit.
        projectile_node["_target_recipient"] = target_kind
        socket = LAUNCH_SOCKETS[skill["Id"]][launcher_index]
        boss_position, boss_position_source = self._boss_position()
        bind_position = self._launcher_bind(socket)
        launch_position = tuple(a + b for a, b in zip(boss_position,
                                                      bind_position))
        target_position, target_position_source = self._target_position(target, target_kind)
        endpoint_distance = math.dist(launch_position, target_position)
        native_speed = skill["ProjectileSpeed"] * NATIVE_SPEED_SCALE
        flight_seconds = endpoint_distance / native_speed
        legacy = skill["Id"] not in TIMELINE_PROJECTILES
        launch_at = (runtime.time + fire_index * skill["DelayTime"] / 100
                     if legacy else runtime.time)
        diagnostic = bool(getattr(runtime, "projectile_diagnostic_no_deadline",
                                  False))
        impact_at = None if diagnostic else launch_at + flight_seconds
        total = physical_count
        projectile = {
            "id": "projectile-" + str(len(runtime.projectiles)),
            "kind": "hostile",
            "profile": runtime.key,
            "skill_id": skill["Id"],
            "shot": skill["SkillAniNumber"],
            "shot_index": shot_index,
            "launcher_index": launcher_index,
            "physical_index": physical_index,
            "fire_index": fire_index,
            "physical_count": total,
            "shot_count": skill["ShotCount"],
            "shot_timing": skill["ShotTiming"],
            "hp": None,
            "max_hp": None,
            "defence": None,
            "defence_snapshot": False,
            "volley_defence": volley_defence,
            "volley_defence_at": volley_defence_at,
            "scheduled_at": runtime.time,
            "spawned": launch_at,
            "launch_at": launch_at,
            "deadline": impact_at,
            "impact_at": impact_at,
            "flight_seconds": flight_seconds,
            "impact_timing_status": ("diagnostic-unresolved" if diagnostic else
                                     "estimated-native-distance-speed"),
            "impact_timing_source": ("explicit diagnostic no-deadline mode" if diagnostic
                                     else "native endpoint distance / scaled table speed"),
            "projectile_speed": skill["ProjectileSpeed"],
            "native_speed": native_speed,
            "projectile_hp_ratio": skill["ProjectileHpRatio"],
            "projectile_hp_shot_divisor": hp_divisor,
            "projectile_damage_ratio_divisor": damage_divisor,
            "projectile_damage_ratio": projectile_damage_ratio,
            "projectile_def_ratio": skill["ProjectileDefRatio"],
            "projectile_radius_object": skill["ProjectileRadiusObject"],
            "projectile_radius": skill["ProjectileRadius"],
            "spot_explosion_range": skill["SpotExplosionRange"],
            "splash_resolution": ("not-applicable" if not skill["SpotExplosionRange"]
                                  else "unresolved-live-collider-overlap"),
            "destroyable": destroyable,
            "target": target,
            "target_kind": target_kind,
            "weapon_object": skill["WeaponObjectEnum"],
            "launch_socket": socket,
            "launch_sockets": LAUNCH_SOCKETS[skill["Id"]],
            "boss_position": boss_position,
            "boss_position_source": boss_position_source,
            "launcher_bind_position": bind_position,
            "launch_position": launch_position,
            "target_position": target_position,
            "target_position_source": target_position_source,
            "endpoint_distance": endpoint_distance,
            "path": "ProjectileCurve",
            "geometry_status": ("exact boss point + prefab bind-pose launcher + "
                                + target_position_source),
            "status": "active" if launch_at <= runtime.time else "pending",
            "source_skill": skill,
            "skill": projectile_skill,
            "node": projectile_node,
        }
        runtime.projectiles.append(projectile)
        if projectile["status"] == "active":
            self._activate(projectile)
        runtime.log("hostile projectile launched" if projectile["status"] == "active"
                    else "hostile projectile scheduled",
                    projectile=projectile["id"], shot=projectile["shot"],
                    hp=projectile["hp"],
                    launch_at=round(launch_at, 3),
                    timing=projectile["impact_timing_status"])
        return projectile

    def perform_skill(self, skill, node):
        if not self._owns(skill):
            return False
        # Both native paths produce ShotCount * total muzzle count.  Legacy
        # Fire does so via Sequence/Concurrence/ConcurrenceGroup; timeline
        # curve attacks enumerate their prefab muzzles directly.
        launchers = len(LAUNCH_SOCKETS[skill["Id"]])
        shots = max(1, skill["ShotCount"])
        legacy = skill["Id"] not in TIMELINE_PROJECTILES
        # Legacy Fire builds one FireData before its delayed firing coroutine;
        # owner DEF and MakeDefenceRatio are stored there once for the volley.
        # Timeline curve attacks read them at their immediate marker launch.
        volley_defence = (self._owner_defence(skill, self.runtime.stat())
                           if legacy else None)
        volley_defence_at = self.runtime.time if legacy else None
        physical_index = 0
        if skill.get("ShotTiming") == "Sequence" and legacy:
            # Legacy Sequence selects prefab = fireIndex % weapon count.  All
            # owned prefabs expose one muzzle, so each complete launcher pass
            # advances the table shot index.
            for fire_index in range(launchers * shots):
                launcher_index = fire_index % launchers
                shot_index = fire_index // launchers
                self._spawn_one(skill, node, launcher_index, shot_index,
                                physical_index, fire_index, volley_defence,
                                volley_defence_at)
                physical_index += 1
        else:
            # Concurrence and ConcurrenceGroup schedule each ShotCount group;
            # every selected prefab/muzzle in the group shares its fireIndex.
            for shot_index in range(shots):
                for launcher_index in range(launchers):
                    self._spawn_one(skill, node, launcher_index, shot_index,
                                    physical_index, shot_index, volley_defence,
                                    volley_defence_at)
                    physical_index += 1
        return True

    def _find(self, projectile):
        if isinstance(projectile, dict):
            return projectile if projectile in self.runtime.projectiles else None
        return next((p for p in self.runtime.projectiles
                     if p.get("id") == projectile), None)

    def set_impact_at(self, projectile, at, source, splash_targets=None):
        """Override the geometric estimate with a measured/native timestamp."""
        item = self._find(projectile)
        if item is None or item.get("status") != "active":
            return False
        if not source:
            raise ValueError("An observed/native impact source is required")
        if at < item["spawned"]:
            raise ValueError("Projectile impact cannot precede its launch")
        item["impact_at"] = at
        item["deadline"] = at
        item["impact_timing_status"] = "observed"
        item["impact_timing_source"] = source
        if splash_targets is not None:
            item["observed_splash_targets"] = list(splash_targets)
        return True

    def _formation_splash_targets(self, item):
        """Approximate native live-collider overlap with squad transforms.

        SpotExplosionRange is stored in centimetre-like table units.  Mirror's
        380 becomes 3.8 world units, which reaches the adjacent two-unit-spaced
        formation slots and reproduces the documented three-cover blast for an
        interior target.  Runtime-observed transforms take precedence.
        """
        if not item["spot_explosion_range"] or not self.runtime.bm:
            return [item.get("target")] if item.get("target") is not None else []
        center, _ = self._target_position(item.get("target"))
        radius = item["spot_explosion_range"] * NATIVE_DISTANCE_SCALE
        result = []
        for candidate in self.runtime.bm.state.get("hp", {}):
            position, _ = self._target_position(candidate)
            if math.dist(center, position) <= radius + 1e-9:
                result.append(candidate)
        return result

    def impact(self, projectile, at=None, source="observed impact event",
               splash_targets=None, timing_status="observed"):
        """Resolve one externally observed impact through normal damage rules.

        Mirror Shot18/19 have ``SpotExplosionRange=380``.  Native
        ``ProjectileLogic.CheckExplosion`` iterates live collider hits, so an
        exact multi-unit impact requires the observed overlapping unit names in
        ``splash_targets``.  With no list, only the locked primary cover is hit
        and the projectile retains an explicit unresolved splash marker.
        """
        item = self._find(projectile)
        if item is None or item.get("status") != "active":
            return False
        when = self.runtime.time if at is None else at
        if when < item["spawned"]:
            raise ValueError("Projectile impact cannot precede its launch")
        item.update(status="hit", hit_at=when, impact_at=when, deadline=when,
                    impact_timing_status=timing_status,
                    impact_timing_source=source)
        if splash_targets is None and item["spot_explosion_range"]:
            splash_targets = self._formation_splash_targets(item)
            item["splash_resolution"] = "formation-transform proxy"
            item["splash_radius_world"] = round(
                item["spot_explosion_range"] * NATIVE_DISTANCE_SCALE, 9)
        targets = list(dict.fromkeys(splash_targets or (item.get("target"),)))
        targets = [target for target in targets if target is not None]
        if (item["spot_explosion_range"] and splash_targets is not None
                and item["splash_resolution"] != "formation-transform proxy"):
            item["splash_resolution"] = "observed"
            item["splash_targets"] = targets
        for target in targets:
            node = dict(item["node"], _locked_targets=[target])
            if item.get("incoming_snapshot") is not None:
                node["_incoming_snapshot"] = item["incoming_snapshot"]
            self.runtime.receive_attack(item["skill"],
                                        node)
        self.runtime.log("hostile projectile hit squad", projectile=item["id"],
                         shot=item["shot"], target=item.get("target"),
                         target_kind=item["target_kind"], timing=timing_status)
        return True

    def advance(self, time):
        for projectile in list(self.runtime.projectiles):
            if (projectile.get("kind") == "hostile"
                    and projectile.get("status") == "pending"
                    and time >= projectile["launch_at"]):
                self._activate(projectile)
                self.runtime.log("hostile projectile launched",
                                 projectile=projectile["id"],
                                 shot=projectile["shot"],
                                 timing=projectile["impact_timing_status"])
            if (projectile.get("kind") == "hostile"
                    and projectile.get("status") == "active"
                    and projectile.get("impact_at") is not None
                    and time >= projectile["impact_at"]):
                self.impact(projectile, projectile["impact_at"],
                            projectile.get("impact_timing_source", "observed impact event"),
                            projectile.get("observed_splash_targets"),
                            projectile.get("impact_timing_status", "observed"))

    def advance_cinematic_projectiles(self, time):
        """Advance launched shots only for phase timelines that keep Spot ticks.

        The installed Mirror phase option has ``isStopTick=0``.  Indivilia's
        phase option has ``isStopTick=1`` and excludes only its timeline
        controller from the pause, so its ordinary ProjectileContext freezes.
        """
        if self.runtime.key == MIRROR_KEY:
            self.advance(time)

    def rebase_cinematic_functions(self, seconds):
        """Map surviving Mirror projectile deadlines back to battle time."""
        if self.runtime.key != MIRROR_KEY:
            return
        for projectile in self.runtime.projectiles:
            if (projectile.get("kind") != "hostile" or
                    projectile.get("status") != "active"):
                continue
            for field in ("spawned", "launch_at", "deadline", "impact_at"):
                if projectile.get(field) is not None:
                    projectile[field] -= seconds

    def resolve_target(self, caster, element, weapon, normal):
        if not normal:
            return None
        active = [p for p in self.runtime.projectiles
                  if p.get("kind") == "hostile"
                  and p.get("status") == "active"
                  and p.get("destroyable")]
        return min(active, key=lambda p: (p["spawned"], p["id"])) if active else None

    def resolve_hit(self, target, damage, hit_type):
        if (target not in self.runtime.projectiles
                or target.get("kind") != "hostile"
                or target.get("status") != "active"
                or not target.get("destroyable")):
            return None
        dealt = min(target["hp"], max(0, damage))
        target["hp"] -= dealt
        self.runtime.damage_to_projectiles += dealt
        if target["hp"] <= 0:
            target.update(status="destroyed", destroyed_at=self.runtime.time)
            self.runtime.log("hostile projectile destroyed", projectile=target["id"])
        return {"handled": True, "consumed": dealt,
                "destroyed": target["status"] == "destroyed", "boss_damage": 0}

    def attack_traits(self, skill):
        ident = skill.get("Id")
        if ident == 520661:
            return dict(projectile=True, destroyable=True,
                        projectile_hp_ratio=10000,
                        target="random_character", iframeable=True)
        if ident in (520672, 520673, 520674, 520675):
            return dict(projectile=True, destroyable=False,
                        target="random_character", iframeable=True,
                        cancelled_by="first_part_hit")
        if ident in (520678, 520679):
            return dict(projectile=True, destroyable=True,
                        projectile_hp_ratio=15000, target="cover",
                        splash_radius=380, iframeable=False)
        if ident == 531474:
            return dict(projectile=True, destroyable=True,
                        projectile_hp_ratio=300, target="highest_attack",
                        iframeable=True, fixed_target=True)
        return {}

    def report(self):
        unresolved = [p["id"] for p in self.runtime.projectiles
                      if p.get("kind") == "hostile"
                      and p.get("status") == "active"
                      and p.get("impact_at") is None]
        return {"projectile_timing": "native distance/speed estimate or observed override",
                "unresolved_projectile_impacts": unresolved}


def build_anomaly_mechanics(runtime):
    if runtime.key in (MIRROR_KEY, INDIVILIA_KEY):
        return AnomalyProjectileMechanics(runtime)
    return None
