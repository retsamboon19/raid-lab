"""Source-driven mechanics for Anomaly Mirror Container and Indivilia.

The recovered behavior tree remains responsible for sequencing attacks and
repairing/breaking parts.  These helpers own mechanics which are expressed by
native passive/function records rather than ordinary tree control flow.
"""

from __future__ import annotations

import math

from calculator.buff_manager import _get_skill_lv
from calculator.damage import calc_damage_avg, default_hit_type
from anomaly_timing import move_distance, move_reached, move_speed_step


def _part_name(row):
    value = row.get("PartsType", "")
    if value.startswith("Weapon"):
        return "Weapon_" + value.removeprefix("Weapon").zfill(2)
    return value


def _shot(skill):
    if isinstance(skill, dict):
        value = skill.get("SkillAniNumber", "")
        return int(value.removeprefix("Shot")) if value.startswith("Shot") else None
    if isinstance(skill, int) and skill <= 30:
        return skill
    return None


class _AnomalyMechanics:
    def __init__(self, runtime):
        self.runtime = runtime
        self.phase = getattr(runtime.world, "phase", 1)

    def on_part_repaired(self, part, time):
        pass

    def on_part_broken(self, part, time, by_squad):
        pass

    def on_part_hit(self, part, time, damage, hit_context=None):
        pass

    def part_targetable(self, part, time):
        return True

    def attack_cancelled(self, skill, state, time):
        return None

    def defence_multiplier(self, time):
        return None

    def part_defence_multiplier(self, part):
        return None

    def preferred_part_shooter(self, names, part, time):
        return None

    def on_phase_changed(self, phase, time):
        self.phase = phase

    def apply_function(self, ident, target=None, part=None):
        return False

    def attack_traits(self, skill):
        return {}

    def advance(self, time):
        pass

    def advance_cinematic_functions(self, virtual_time):
        pass

    def rebase_cinematic_functions(self, seconds):
        pass

    def report(self):
        return {}

    @property
    def assumptions(self):
        return []


class MirrorContainerMechanics(_AnomalyMechanics):
    """Glass Slipper hit gates and the four phase-two DEF layers.

    Native evidence:
    * StateEffect 7451004 attaches one OnPartsHurtCount function per part.
      Functions 1999644..1999663 grant PartsImmuneDamage for 500 cs after
      the first accepted hit.
    * Skills 520662..520667 cancel on BrokenParts; skills 520672..520675
      cancel on BrokenPartsHurtCount.
    * Skills 520680..520683 add four separate +9000/10000 DEF functions.
      OnUserPartsDestroy functions 1999668..1999671 remove the respective
      layer for parts 45101108..45101111.
    """

    PART_IDS = {45101101 + index: f"Weapon_{index:02d}" for index in range(1, 11)}
    PHASE_ONE_PARTS = tuple(f"Weapon_{index:02d}" for index in range(1, 7))
    PHASE_TWO_PARTS = tuple(f"Weapon_{index:02d}" for index in range(7, 11))
    LABELS = {
        **{f"Weapon_{index:02d}": f"Glass Slipper I {index}" for index in range(1, 7)},
        **{f"Weapon_{index:02d}": f"Glass Slipper II {index - 6}" for index in range(7, 11)},
    }
    DEFENCE_FUNCTION_PART = {
        1999664: "Weapon_07",
        1999665: "Weapon_08",
        1999666: "Weapon_09",
        1999667: "Weapon_10",
    }
    HIT_GATE_ROOTS = set(range(1999644, 1999663, 2))
    PERMANENT_CLOSE_ROOTS = set(range(1999680, 1999700, 2))
    OPEN_ROOTS = set(range(1999700, 1999720, 2))
    HP_UI_ROOTS = {1999602, 1999605, 1999608, 1999611, 1999736, 1999738, 1999740, 1999742, 1999744, 1999746, 1999748, 1999750}

    def __init__(self, runtime):
        super().__init__(runtime)
        self.immune_until = {}
        self.hit_count = dict.fromkeys(self.LABELS, 0)
        self.last_hit = dict.fromkeys(self.LABELS, float("-inf"))
        self.defence_layers = set()
        self.hp_ui_functions = set()
        self.base_part_hp = {
            part: runtime.world.part_hp.get(part, 0) for part in self.PHASE_TWO_PARTS
        }
        self.hp_groups = {part: {} for part in self.PHASE_TWO_PARTS}
        self.slipper_shooter_locks = {}

    def on_part_repaired(self, part, time):
        if part in self.hit_count:
            self.hit_count[part] = 0
            self.last_hit[part] = float("-inf")
        if part in self.hp_groups:
            # RaidWorld has just rebuilt the part at the current anomaly
            # damage stage.  Capture that unmodified maximum before restoring
            # any still-active native HP function groups for this lifetime.
            self.base_part_hp[part] = self.runtime.world.part_hp[part]
            self._refresh_part_hp(part, time)

    def on_part_broken(self, part, time, by_squad):
        if by_squad and part in self.PHASE_TWO_PARTS:
            self.defence_layers.discard(part)

    def on_part_hit(self, part, time, damage, hit_context=None):
        if part not in self.hit_count or damage <= 0:
            return
        self.hit_count[part] += 1
        self.last_hit[part] = time
        # Passive 7451004 triggers at one accepted hit and closes the slipper.
        self.immune_until[part] = max(self.immune_until.get(part, 0), time + 5.0)

    def part_targetable(self, part, time):
        return time >= self.immune_until.get(part, 0)

    def attack_cancelled(self, skill, state, time):
        if skill.get("CancelType") != "BrokenPartsHurtCount":
            return None
        started = state.get("started", state.get("interrupt", float("-inf")))
        parts = state.get("parts") or [_part_name({"PartsType": p}) for p in skill.get("ControlParts", [])]
        return any(self.last_hit.get(part, float("-inf")) >= started for part in parts)

    def defence_multiplier(self, time):
        if self.phase != 2:
            return 1.0
        return 1.0 + 0.9 * len(self.defence_layers)

    def part_defence_multiplier(self, part):
        """Apply the part record's own DEF ratio before phase-two layers.

        ``SpotMonsterPartsData.PartsData`` stores a separate defence stat for
        every part.  Mirror's first-phase slippers use 10000; the second-phase
        slippers deliberately use zero.
        """
        row = self.runtime.world.rows.get(part)
        return row["DefenceRatio"] / 10000 if row else None

    def _active_slipper_attack(self, part, time):
        attacks = getattr(self.runtime.world, "attacks", {})
        active = [
            (ident, state) for ident, state in attacks.items()
            if part in state.get("parts", ())
            and state.get("started", float("inf")) <= time < state.get("end", float("inf"))
        ]
        if not active:
            return None
        ident, state = max(active, key=lambda item: item[1].get("started", float("-inf")))
        return ident, state.get("started"), part

    def _charged_shot_score(self, name, time):
        """Expected current full-charge damage for the one-hit slipper gate."""
        runtime = self.runtime
        bm = runtime.bm
        cs = runtime.char_states[name]
        weapon = dict(cs.weapon)
        wc = bm.get_weapon_change(name)
        skill_damage = False
        if wc:
            dc = wc.get("damage_coeff", weapon.get("damage_coeff", 0))
            if isinstance(dc, dict):
                level = _get_skill_lv(cs.char, wc)
                dc = dc.get(level, dc.get("10", 0))
            weapon.update(
                weapon_type=wc.get("weapon_type", weapon.get("weapon_type", cs.weapon_type)),
                damage_coeff=float(dc),
                full_charge_mult=wc.get("full_charge_mult", weapon.get("full_charge_mult", 100)),
                core_dmg_mult=wc.get("core_dmg_mult", weapon.get("core_dmg_mult", 200)),
            )
            skill_damage = bool(wc.get("skill_damage"))
        weapon_type = weapon.get("weapon_type", cs.weapon_type)
        buffs = bm.get_buffs(name, "__enemy__", time)
        buffs["is_element_match"] = cs.element_match(bm)
        hit_type = default_hit_type(
            is_normal_atk=not skill_damage,
            is_weapon_mode_skill=skill_damage,
            is_full_charge=True,
            is_full_burst=bool(bm.state.get("full_burst")),
            is_part=True,
            is_pierce_damage=bool(runtime.active_stat(name, "pierce_enabled")),
            is_armor_break_damage=bool(runtime.active_stat(name, "armor_break_enabled")),
            is_projectile_explosion=weapon_type == "RL",
        )
        # Phase-II slippers have native DefenceRatio 0, so their accepted hit
        # is scored against zero local DEF even while the body has DEF layers.
        enemy_def = 0 if self.phase == 2 else (
            runtime.enemy_def if runtime.enemy_def is not None
            else runtime.stat()["LevelDefence"] * runtime.data["monster"]["DefenceRatio"] / 10000
        )
        muzzles = int(wc.get("muzzles", getattr(cs, "muzzles", 1))) if wc else int(getattr(cs, "muzzles", 1))
        return calc_damage_avg(cs.base_atk, buffs, weapon, hit_type, enemy_def) * max(1, muzzles)

    def preferred_part_shooter(self, names, part, time):
        """Choose and lock the strongest current charged shot for one opening.

        The lock key is the behavior-tree attack lifetime, so changes in buffs
        between timeline markers cannot hand the first-hit privilege to a
        follower after aiming has begun.
        """
        if part not in self.LABELS or not names:
            return None
        token = self._active_slipper_attack(part, time)
        active_tokens = {
            value for p in self.LABELS
            if (value := self._active_slipper_attack(p, time)) is not None
        }
        for stale in set(self.slipper_shooter_locks) - active_tokens:
            self.slipper_shooter_locks.pop(stale, None)
        if token and self.slipper_shooter_locks.get(token) in names:
            return self.slipper_shooter_locks[token]
        shooter = max(names, key=lambda name: self._charged_shot_score(name, time))
        if token:
            self.slipper_shooter_locks[token] = shooter
        return shooter

    def on_phase_changed(self, phase, time):
        super().on_phase_changed(phase, time)
        if phase != 2:
            self.defence_layers.clear()

    def _apply(self, ident, part=None):
        function = self.runtime.functions.get(ident)
        if function is None:
            return False
        kind = function["FunctionType"]
        handled = False
        if kind == "TargetPartsId" and function["FunctionValue"] in self.PART_IDS:
            part = self.PART_IDS[function["FunctionValue"]]
            handled = True
        elif kind == "PartsImmuneDamage" and part in self.hit_count:
            self.immune_until[part] = self.runtime.time + function["DurationValue"] / 100
            handled = True
        elif ident in self.DEFENCE_FUNCTION_PART and kind == "StatDef":
            self.defence_layers.add(self.DEFENCE_FUNCTION_PART[ident])
            handled = True
        elif kind == "FunctionOverlapChange" and ident == 1999673:
            # The corresponding OnUserPartsDestroy hook removes the layer.
            handled = True
        elif kind == "PartsHpChangeUIOn" and part in self.hit_count:
            self.hp_ui_functions.add(ident)
            group = function["GroupId"]
            expires = None if function["DurationValue"] >= 99999 else self.runtime.time + function["DurationValue"] / 100
            self.hp_groups[part][group] = (function["FunctionValue"], expires)
            self._refresh_part_hp(part, self.runtime.time)
            handled = True
        for child in function.get("ConnectedFunction", []):
            handled = self._apply(child, part) or handled
        return handled

    def apply_function(self, ident, target=None, part=None):
        function = self.runtime.functions.get(ident)
        if function is None:
            return False
        if ident in self.HIT_GATE_ROOTS:
            # These passive roots are dispatched by on_part_hit, not at start.
            return True
        relevant = (
            ident in self.PERMANENT_CLOSE_ROOTS
            or ident in self.OPEN_ROOTS
            or ident in self.HP_UI_ROOTS
            or ident in self.DEFENCE_FUNCTION_PART
            or ident == 1999673
            or function["FunctionType"] in ("PartsImmuneDamage", "PartsHpChangeUIOn") and part in self.hit_count
        )
        return self._apply(ident, part) if relevant else False

    def _refresh_part_hp(self, part, time):
        groups = self.hp_groups[part]
        for group, (_, expires) in list(groups.items()):
            if expires is not None and time >= expires:
                groups.pop(group)
        base = self.base_part_hp[part]
        # Parts HP is a StatValue (int64).  The client converts the adjusted
        # double with CommonUtil.DoubleToLong: five decimal places, positive
        # half-up.  Keep the same integer boundary when active groups make a
        # non-integral maximum.
        adjusted = base * (1 + sum(value for value, _ in groups.values()) / 10000)
        maximum = math.floor(round(adjusted, 5) + .5)
        old = self.runtime.world.part_hp.get(part, base)
        self.runtime.world.part_hp[part] = maximum
        current = self.runtime.world.parts.parts.get(part)
        if current and current["status"] == "alive":
            ratio = current["hp"] / current["max_hp"] if current["max_hp"] else 1
            current["max_hp"] = maximum
            current["hp"] = math.floor(round(maximum * ratio, 5) + .5)

    def advance(self, time):
        for part in self.PHASE_TWO_PARTS:
            self._refresh_part_hp(part, time)

    def advance_cinematic_functions(self, virtual_time):
        """Expire function-owned HP groups across collapsed cutscene time."""
        for part in self.PHASE_TWO_PARTS:
            self._refresh_part_hp(part, virtual_time)

    def rebase_cinematic_functions(self, seconds):
        """Move surviving absolute function deadlines onto the battle clock."""
        for part in list(self.immune_until):
            self.immune_until[part] -= seconds
        for groups in self.hp_groups.values():
            for group, (value, expires) in list(groups.items()):
                if expires is not None:
                    groups[group] = (value, expires - seconds)

    def attack_traits(self, skill):
        shot = _shot(skill)
        if shot == 1:
            return dict(projectile=True, destroyable=True, projectile_hp_ratio=10000, target="random_character")
        if shot in range(3, 9):
            return dict(target="highest_attack", tauntable=True, coverable=True, shieldable=True, cancelled_by="part_destroy")
        if shot in (9, 10, 16):
            return dict(target="all", penetration=True, qte_wipe=shot in (9, 16))
        if shot in range(12, 16):
            return dict(projectile=True, destroyable=False, target="random_character", cancelled_by="first_part_hit")
        if shot == 17:
            return dict(target="highest_attack", tauntable=True, coverable=True, shieldable=True)
        if shot in (18, 19):
            return dict(projectile=True, destroyable=True, projectile_hp_ratio=15000, target="cover", splash_radius=200, iframeable=False)
        return {}

    def report(self):
        return dict(
            kind="mirror-container",
            part_labels=dict(self.LABELS),
            slipper_immune_until=dict(self.immune_until),
            slipper_hit_count=dict(self.hit_count),
            defence_layers=sorted(self.defence_layers),
            defence_multiplier=self.defence_multiplier(self.runtime.time),
            hp_ui_functions=sorted(self.hp_ui_functions),
            slipper_shooter_locks={str(token): shooter for token, shooter in self.slipper_shooter_locks.items()},
            part_hp_multiplier={
                part: self.runtime.world.part_hp[part] / base if base else 1
                for part, base in self.base_part_hp.items()
            },
        )


class IndiviliaMechanics(_AnomalyMechanics):
    """Phase-valid parts, collision geometry, and suicide-add lifecycle."""

    handles_summons = True

    SUICIDE_MONSTERS = {2210050635, 2210050636}
    PINCER_EDGE_SLOT = {"Weapon_01": 1, "Weapon_02": 5}
    # Installed point_grd_indivilia_01/point_fly_indivilia_01 coordinates.
    # Calling teleports each add to ActionPoint; its custom tree then moves to
    # DirPoint at rate 5 and traverses the fixed MoveToVer2 route at rate 3.
    ROUTE_POINTS = {
        1010: (-65.0, 15.0, 98.0),
        303: (-25.0, 45.0, 63.0), 304: (25.0, 45.0, 63.0),
        305: (-10.0, 50.0, 63.0), 306: (10.0, 50.0, 63.0),
        2781: (-12.0, 25.5, 51.0), 2789: (12.0, 25.5, 51.0),
        2801: (-12.0, 29.5, 59.0), 2809: (12.0, 29.5, 59.0),
        2561: (-10.0, 11.5, 36.0), 2569: (10.0, 11.5, 36.0),
        9938: (0.0, 1.44, 27.0), 9939: (0.0, 0.0, 25.0),
        2541: (-10.0, 7.5, 30.0), 2542: (-7.5, 7.5, 30.0),
        2548: (7.5, 7.5, 30.0), 2549: (10.0, 7.5, 30.0),
        2734: (-1.5, 6.0, 21.0), 2735: (0.0, 6.0, 21.0),
        2736: (1.5, 6.0, 21.0),
    }
    SUICIDE_ROUTES = {
        (2210050635, 2781): (304, 2781, 2561, 9938, 2549, 2735),
        (2210050635, 2789): (303, 2789, 2569, 9938, 2541, 2735),
        (2210050636, 2801): (306, 2801, 2541, 9939, 2548, 2736),
        (2210050636, 2809): (305, 2809, 2549, 9939, 2542, 2734),
    }
    # SetReturn steers a flying Teleport add toward WaveContext's closest
    # return position before SpawnActionEndEvent. The installed
    # wave_combat_zone NKSquarePyramid defines its return boundary.
    # Nearest installed point_fly_indivilia_01 AirReturnPoint to the summon
    # ActionPoints. Its direction agrees with the live SetReturn trajectory.
    RETURN_TARGET = (0.0, 26.5, 59.0)
    RETURN_DISTANCE = 9.914
    OUTER_RETURN_END = (17.083, 39.178, 61.691)
    RETURN_START_SECONDS = 25 * .017
    OUTER_RETURN_SECONDS = 3.917
    COMBAT_ZONE_ORIGIN = (0.0, -4.0, 0.0)
    COMBAT_ZONE_GRADIENT = 2.0
    COMBAT_ZONE_NEAR = 10.0
    COMBAT_ZONE_FAR = 100.0
    COMBAT_ZONE_HEIGHT = 70.0
    COMBAT_ZONE_BOTTOM = 2.0
    LABELS = {
        "Weapon_01": "Left pincer",
        "Weapon_02": "Right pincer",
        "Weapon_03": "Tail",
        "Weapon_04": "Blade",
    }
    PHASE_PARTS = {
        1: frozenset(("Weapon_01", "Weapon_02", "Weapon_03")),
        2: frozenset(("Weapon_04",)),
    }

    def part_targetable(self, part, time):
        return part in self.PHASE_PARTS.get(self.phase, frozenset())

    def attack_traits(self, skill):
        shot = _shot(skill)
        if shot == 10:
            return dict(
                source_part="Weapon_03",
                target="highest_attack",
                penetration=True,
                bypass_cover=True,
                shieldable=True,
                taunt_lock="cast_start",
            )
        if shot == 30:
            return dict(target="all_fixed_slots", penetration=True, bypass_cover=True, bypass_shield=True, tauntable=False)
        if shot in (12, 16):
            return dict(target="all", penetration=True, bypass_cover=True, qte_wipe=True)
        if shot in (5, 6, 7, 13, 14):
            return dict(target="fixed_warned_slot", tauntable=False, coverable=True, shieldable=True)
        if shot in (11, 15):
            return dict(target="all", coverable=True, shieldable=True)
        if shot == 19:
            return dict(projectile=True, destroyable=True, projectile_hp_ratio=300, target="highest_attack", iframeable=True)
        return {}

    def player_collision_targets(self, part, squad_position, pierce_enabled):
        """Return the ordered native collision chain for an edge pincer ray.

        Weapon_01 and Weapon_02 sit in front of the body collider only on the
        corresponding P1/P5 oblique sightline.  ``Body`` is an additional
        collision for a piercing shot; it must not receive part HP damage.
        """
        if (self.phase == 1 and pierce_enabled
                and self.PINCER_EDGE_SLOT.get(part) == squad_position):
            return (part, "Body")
        return (part,)

    # Compatibility name used by the first audit integration draft.
    def overlap_targets(self, part, squad_position, pierce_enabled):
        return self.player_collision_targets(part, squad_position, pierce_enabled)

    def perform_skill(self, skill, node):
        if skill.get("FireType") != "Calling":
            return False
        group = skill["SkillValue01"]
        rows = [row for row in self.runtime.data["calls"] if row["GroupId"] == group]
        for row in rows:
            self.runtime.pending.append({
                "kind": "indivilia_summon",
                "at": self.runtime.time + row["SpawnTime"],
                "record": row,
            })
        self.runtime.log("Indivilia suicide wave called", group=group, count=len(rows))
        return True

    def _monster(self, ident):
        return next(m for m in self.runtime.data["monsters"] if m["Id"] == ident)

    def _suicide_skill(self, monster):
        ids = {entry["SkillId"] for entry in monster["SkillData"] if entry["SkillId"]}
        return next(skill for skill in self.runtime.data["skills"]
                    if skill["Id"] in ids and skill["FireType"] == "Suicide")

    def _route(self, row):
        return self.SUICIDE_ROUTES[(row["MonsterId"], row["DirPoint"])]

    def _entry_seconds(self, monster, row, start_position=None):
        """Estimate post-SpawnAction AI movement at a 20 ms tick.

        The custom add tree uses ordinary ``MoveTo`` at rate 5 until its
        one-unit ``IsInPoint`` condition succeeds, followed by four
        ``MoveToVer2`` legs at rate 3 and the same one-unit tolerance.  Both
        actions ultimately drive ``MonsterLogic.SetMove``; its current speed
        carries across legs and approaches the requested rate using the
        monster's acceleration coefficient. The CallingList's Teleport action
        places the add at ActionPoint first. SetReturn then moves it into the
        return box while SpawnAction is still active. This AI route follows
        SpawnActionEndEvent.
        """
        route = self._route(row)
        position = (dict(start_position) if start_position is not None else
                    dict(zip(("x", "y", "z"), self.ROUTE_POINTS[route[0]])))
        current_speed = 0.0
        elapsed = 0.0
        tick = 0.02
        for index, point in enumerate(route[1:]):
            destination = dict(zip(("x", "y", "z"), self.ROUTE_POINTS[point]))
            rate = 5.0 if index == 0 else 3.0
            while not move_reached(position, destination, 1.0, True):
                current_speed = move_speed_step(
                    current_speed, monster["SpotMoveSpeed"], rate,
                    monster["SpotAccelerationTime"], tick,
                )
                distance = move_distance(position, destination, True)
                fraction = min(1.0, current_speed * tick / distance) if distance else 1.0
                for axis in ("x", "y", "z"):
                    position[axis] += (destination[axis] - position[axis]) * fraction
                elapsed += tick
                if elapsed > 60:
                    raise ValueError("Indivilia summon movement did not converge")
        return elapsed

    def _position_at(self, monster, row, elapsed, start_position=None):
        """Reproduce the native 20 ms movement steps up to ``elapsed``."""
        route = self._route(row)
        position = (dict(start_position) if start_position is not None else
                    dict(zip(("x", "y", "z"), self.ROUTE_POINTS[route[0]])))
        current_speed = 0.0
        remaining_time = max(0.0, elapsed)
        tick = 0.02
        for index, point in enumerate(route[1:]):
            destination = dict(zip(("x", "y", "z"), self.ROUTE_POINTS[point]))
            rate = 5.0 if index == 0 else 3.0
            while not move_reached(position, destination, 1.0, True):
                if remaining_time <= 1e-9:
                    return position
                dt = min(tick, remaining_time)
                current_speed = move_speed_step(
                    current_speed, monster["SpotMoveSpeed"], rate,
                    monster["SpotAccelerationTime"], dt,
                )
                distance = move_distance(position, destination, True)
                fraction = min(1.0, current_speed * dt / distance) if distance else 1.0
                for axis in ("x", "y", "z"):
                    position[axis] += (destination[axis] - position[axis]) * fraction
                remaining_time -= dt
        return position

    @classmethod
    def _in_combat_zone(cls, position):
        """NKSquarePyramid.IsIn for the installed wave_combat_zone prefab."""
        x = position["x"] - cls.COMBAT_ZONE_ORIGIN[0]
        y = position["y"] - cls.COMBAT_ZONE_ORIGIN[1]
        z = position["z"] - cls.COMBAT_ZONE_ORIGIN[2]
        return (cls.COMBAT_ZONE_NEAR <= z <= cls.COMBAT_ZONE_FAR and
                abs(x) <= z / cls.COMBAT_ZONE_GRADIENT and
                -cls.COMBAT_ZONE_BOTTOM <= y <=
                cls.COMBAT_ZONE_HEIGHT * z / cls.COMBAT_ZONE_FAR)

    def _return_seconds(self, row, monster):
        if row["ActionPoint"] in (303, 304):
            # The outer-pyramid crossing is also fixed by three live
            # SpawnActionEndEvents to 3.917 s, within one Spot tick of the
            # source-derived plane crossing.
            return self.OUTER_RETURN_SECONDS
        tick = .017
        origin = self.ROUTE_POINTS[row["ActionPoint"]]
        length = math.dist(origin, self.RETURN_TARGET)
        direction = tuple((target - value) / length
                          for target, value in zip(self.RETURN_TARGET, origin))
        speed = .6
        distance = 0.0
        for step in range(1, 600):
            speed = move_speed_step(speed, monster["SpotMoveSpeed"], 1,
                                    monster["SpotAccelerationTime"], tick)
            distance += speed * tick
            elapsed = self.RETURN_START_SECONDS + step * tick
            position = {axis: value + distance * delta
                        for axis, value, delta in zip(("x", "y", "z"),
                                                      origin, direction)}
            if self._in_combat_zone(position):
                return elapsed
        raise ValueError("Indivilia SetReturn did not enter wave_combat_zone")

    def _return_end_position(self, row, monster=None):
        origin = self.ROUTE_POINTS[row["ActionPoint"]]
        if row["ActionPoint"] in (303, 304):
            side = -1.0 if origin[0] < 0 else 1.0
            return (side * self.OUTER_RETURN_END[0],
                    self.OUTER_RETURN_END[1], self.OUTER_RETURN_END[2])
        monster = monster or self._monster(row["MonsterId"])
        point = self._return_position_at(row, self._return_seconds(row, monster), monster)
        return tuple(point[axis] for axis in ("x", "y", "z"))

    def _return_position_at(self, row, elapsed, monster=None):
        """Integrate the observed SetReturn speed ramp before the AI route."""
        origin = self.ROUTE_POINTS[row["ActionPoint"]]
        if elapsed <= self.RETURN_START_SECONDS:
            return dict(zip(("x", "y", "z"), origin))
        outer = row["ActionPoint"] in (303, 304)
        remaining = (min(elapsed, self.OUTER_RETURN_SECONDS)
                     if outer else elapsed) - self.RETURN_START_SECONDS
        monster = monster or self._monster(row["MonsterId"])
        speed = .6  # residual fly-brake speed at the first observed return tick
        distance = 0.0
        while remaining > 1e-9:
            dt = min(.017, remaining)
            speed = move_speed_step(speed, monster["SpotMoveSpeed"], 1,
                                    monster["SpotAccelerationTime"], dt)
            distance += speed * dt
            remaining -= dt
        if outer:
            end = self._return_end_position(row)
            fraction = min(1.0, distance / self.RETURN_DISTANCE)
            return {axis: start + (finish - start) * fraction
                    for axis, start, finish in zip(("x", "y", "z"), origin, end)}
        direction = tuple(target - value for target, value in zip(self.RETURN_TARGET, origin))
        length = math.dist(origin, self.RETURN_TARGET)
        return {axis: value + distance * delta / length
                for axis, value, delta in zip(("x", "y", "z"), origin, direction)}

    def _spawn_add(self, row, time):
        r = self.runtime
        monster = self._monster(row["MonsterId"])
        skill = self._suicide_skill(monster)
        hp = math.floor(round(r.stat(monster)["LevelHp"] * monster["HpRatio"] / 10000, 5) + .5)
        route = self._route(row)
        spawn_action = self._return_seconds(row, monster)
        return_end = self._return_end_position(row, monster)
        return_position = dict(zip(("x", "y", "z"), return_end))
        route_seconds = self._entry_seconds(monster, row, return_position)
        entry = spawn_action + route_seconds
        add = {
            "id": "summon-" + str(len(r.adds)), "monster_id": monster["Id"],
            "hp": hp, "max_hp": hp, "spawned": time, "protected": False,
            "defence": r.stat(monster)["LevelDefence"] * monster["DefenceRatio"] / 10000,
            "skill": skill, "state": "spawn-action", "ready_at": time + entry,
            "next_attack": time + entry, "route": route,
            "route_positions": [self.ROUTE_POINTS[point] for point in route],
            "position": dict(zip(("x", "y", "z"), self.ROUTE_POINTS[row["StartPoint"]])),
            "teleport_from": self.ROUTE_POINTS[row["StartPoint"]],
            "teleport_to": self.ROUTE_POINTS[row["ActionPoint"]],
            "teleport_at": time + 3 * .017,
            "return_motion_at": time + self.RETURN_START_SECONDS,
            "return_end_position": return_position,
            "spawn_action_completion": time + spawn_action,
            "spawn_action_seconds": spawn_action,
            "post_teleport_move_seconds": route_seconds,
            "entry_seconds": entry, "spawn_type": row["SpawnType"],
            "start_point": row["StartPoint"], "action_point": row["ActionPoint"],
            "dir_point": row["DirPoint"], "suicide": True,
            "timing_source": "measured SetTeleport/SetBrake/SetReturn gate; then installed AI MoveTo route",
            "timing_status": (
                "Outer-point survivor SpawnActionEndEvent at 3.917 s and its SetReturn "
                "path match isolated-client positions; inner-point return gate "
                "is derived from installed combat pyramid geometry and native "
                "speed interpolation (about +/- 0.04 s onset uncertainty, "
                "not yet live-confirmed). Later AI route uses native acceleration and "
                "one-unit arrival tolerance at 20 ms"
            ),
        }
        r.adds.append(add)
        r.log("summon spawned", monster=monster["Id"], hp=hp, summon=add["id"],
              ready_at=round(add["ready_at"], 3), timing=add["timing_status"])

    def advance(self, time):
        r = self.runtime
        for item in list(r.pending):
            if item.get("kind") != "indivilia_summon" or time < item["at"]:
                continue
            r.pending.remove(item)
            self._spawn_add(item["record"], time)
        for add in r.adds:
            if add["hp"] <= 0 or add.get("state") in ("destroyed", "self-destructed"):
                continue
            if add.get("state") in ("spawn-action", "approaching"):
                if time < add["teleport_at"]:
                    continue
                if time < add["spawn_action_completion"]:
                    add["position"] = self._return_position_at(
                        {"ActionPoint": add["action_point"],
                         "MonsterId": add["monster_id"]}, time - add["spawned"])
                    continue
                add["state"] = "approaching"
                monster = self._monster(add["monster_id"])
                row = {
                    "MonsterId": add["monster_id"],
                    "DirPoint": add["dir_point"],
                }
                add["position"] = self._position_at(
                    monster, row, time - add["spawn_action_completion"],
                    add["return_end_position"])
            if time < add["next_attack"]:
                continue
            monster = self._monster(add["monster_id"])
            r.receive_attack(add["skill"], {}, monster=monster, source=add["id"])
            add.update(hp=0, state="self-destructed", attacks=1,
                       last_attack=time, clear_reason="suicide attack", cleared_at=time)
            r.log("summon self-destructed", summon=add["id"], monster=add["monster_id"])

    def resolve_target(self, caster, element, weapon, normal):
        if not normal:
            return None
        living = [add for add in self.runtime.adds if add["hp"] > 0]
        return min(living, key=lambda add: (add["next_attack"], add["id"])) if living else None

    def resolve_hit(self, target, damage, hit_type):
        if target not in self.runtime.adds or target["hp"] <= 0:
            return None
        dealt = min(target["hp"], max(0, damage))
        target["hp"] -= dealt
        self.runtime.damage_to_adds += dealt
        destroyed = target["hp"] <= 0
        if destroyed:
            target.update(state="destroyed", cleared_at=self.runtime.time, clear_reason="squad")
            self.runtime.log("summon cleared", summon=target["id"], monster=target["monster_id"])
        return {"handled": True, "consumed": dealt, "destroyed": destroyed, "boss_damage": 0}

    @property
    def assumptions(self):
        return [
            "Indivilia Teleport places adds after three 17 ms ticks. SetReturn "
            "then moves surviving outer-point adds through the flying return box "
            "until SpawnActionEndEvent at 3.917 seconds. The observed outer return "
            "path is modeled with native speed acceleration; the inner-point "
            "gate is derived from the installed wave_combat_zone pyramid with "
            "about 0.04-second onset uncertainty, pending direct live timing. "
            "The separate AI MoveTo route starts only "
            "after that event and uses installed points and one-unit tolerance.",
        ]

    def report(self):
        return dict(
            kind="indivilia",
            phase=self.phase,
            active_parts=sorted(self.PHASE_PARTS.get(self.phase, ())),
            part_labels=dict(self.LABELS),
            suicide_adds=[{
                "id": add["id"], "monster_id": add["monster_id"],
                "state": add.get("state"), "hp": add["hp"],
                "next_attack": add.get("next_attack"),
            } for add in getattr(self.runtime, "adds", ())
              if add.get("monster_id") in self.SUICIDE_MONSTERS],
        )


def build_anomaly_mechanics(runtime):
    if runtime.key == "anomaly-mirror-container":
        return MirrorContainerMechanics(runtime)
    if runtime.key == "anomaly-indivilia":
        return IndiviliaMechanics(runtime)
    return None
