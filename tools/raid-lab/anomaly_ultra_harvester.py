"""Profile-specific Anomaly Ultra and Harvester mechanics.

The records consumed here are already selected for the exact Anomaly variants
in ``raid-boss-combat-data.json``.  Static-table values and behavior-tree waits
are kept exact.  Harvester summon coordinates are from the installed
``point_grd_harvester_01`` and ``point_fly_harvester_01`` TextAssets.  Add
SpawnAction placement and readiness use current native control flow and
isolated-client tick traces; Drop falls vertically from the ActionPoint plus
the native 20-unit spawn height.

Integration contract
--------------------
``build_anomaly_mechanics(runtime)`` returns ``None`` for unrelated profiles.
For Ultra or Harvester it returns an object with these optional hooks:

* ``perform_skill(skill, node)``: return true when the hook scheduled/handled
  the skill and the common runtime must not execute it again.
* ``advance(t)``: advance scheduled hostile projectiles and, for Harvester,
  the complete profile-specific summon loop.  The common summon loop must be
  skipped when ``handles_summons`` is true.
* ``core_probability(caster, part, pierce)``: return a profile override.
* ``preferred_part(caster, pierce)``: expose Ultra's hidden core to a
  player-controlled pierce attacker.
* ``resolve_target(caster, element, weapon, normal)``: return an active
  projectile/add dictionary, or ``None`` to keep ordinary boss targeting.
* ``resolve_hit(target, damage, hit_type)``: consume damage on a target returned
  by ``resolve_target`` and return a result dictionary.
"""

import math

from anomaly_timing import ordinary_fire_schedule
from anomaly_projectiles import (FORMATION_AIM, HIDE_TRANSLATION,
                                 NATIVE_SPEED_SCALE)


ULTRA_ID = 1520460146
HARVESTER_ID = 1520010113
HARVESTER_PROJECTILE_SKILL = 510130
HARVESTER_OBJECT_SKILL = 510133
ULTRA_PROJECTILE_SKILLS = frozenset((510632, 510633, 510636, 510637))

# Native legacy Fire and TimeLineProjectileCurve both emit ShotCount times the
# selected prefab muzzle count, by different code paths.  All listed prefab
# GameObjects and their complete parent hierarchies are active in the installed
# intercept assets.
PROJECTILE_PHYSICAL_COUNTS = {
    510632: 10,  # Ultra WeaponObject03: one prefab, ten muzzles
    510633: 10,  # Ultra WeaponObject04: one prefab, ten muzzles
    510636: 1,   # Ultra WeaponObject06: one prefab, one muzzle
    510637: 1,   # Ultra WeaponObject05: one prefab, one muzzle
    510130: 8,   # Harvester WeaponObject03: two prefabs, four muzzles each
}
PROJECTILE_PREFAB_MUZZLE_COUNTS = {
    510632: (10,),
    510633: (10,),
    510636: (1,),
    510637: (1,),
    510130: (4, 4),
}
TIMELINE_PROJECTILE_SKILLS = frozenset((510636, 510637))

# Installed 152.8.11 PointData coordinates used by CallingList rows 1482-1496.
# Coordinate units are Unity world units. CallingList StartPoint remains the
# origin for Teleport, but Drop uses ActionPoint x/z and starts 20 units above it.
HARVESTER_GROUND_POINTS = {
    1002: (-19.94, -1.5, 18.5), 1632: (-3.75, -1.0, 24.6),
    1003: (-23.02, -1.0, 24.36), 1637: (2.5, -1.0, 24.6),
    1102: (18.56, -1.5, 18.3), 1644: (-1.5, -.5, 26.51),
    1104: (24.22, -.5, 27.51), 1647: (3.0, -.5, 26.51),
    1006: (-31.18, 1.0, 38.78), 1662: (-10.65, 1.0, 39.78),
    1005: (-29.44, 0.0, 36.24), 1657: (5.64, 0.0, 32.97),
    1205: (9.88, -1.5, 18.3), 1208: (12.77, -1.0, 25.58),
    1305: (-12.89, -1.5, 19.1900024), 1310: (-17.94, -.5, 25.8),
    1217: (18.42, 1.0, 34.79), 1214: (17.9999981, 0.0, 33.27),
}
HARVESTER_AIR_POINTS = {
    2201: (23.0, -1.0, 13.0), 2115: (31.0, 10.6, 33.0),
    2015: (-31.0, 10.6, 33.0), 2632: (-4.5, 4.9, 21.0),
    2746: (2.5, 11.2, 30.0), 2744: (-2.5, 11.2, 30.0),
    2635: (0.0, 4.9, 21.0), 2638: (4.5, 4.9, 21.0),
    2631: (-6.0, 4.9, 21.0), 2639: (6.0, 4.9, 21.0),
}

# Harvester spawns at ground point 151 (0, 0, 50).  These are the bind-pose
# locations of its two WeaponObject03 launchers after resolving the prefab
# transform hierarchy.  Animation and the selected squad member move the real
# endpoints, so they are evidence, not an exact impact deadline.
HARVESTER_BOSS_POINT = (0.0, 0.0, 50.0)
HARVESTER_LAUNCHERS = (
    (0.6044624234, 20.6720292523, -2.6293631433),
    (0.9435712541, 20.6244482308, -2.7634828348),
    (0.8884016529, 20.7461610881, -1.4182617119),
    (0.2751920329, 20.7186600814, -1.4989658770),
    (2.9491628908, 17.7991056362, -2.9191954830),
    (3.0836728913, 17.4718415137, -2.6515252847),
    (3.7890723942, 18.4285147242, -2.1358751564),
    (3.5763216011, 18.7786214640, -2.5512353319),
)


def _rounded_hp(value):
    return math.floor(round(value, 5) + 0.5)


class _BaseMechanics:
    handles_summons = False

    def __init__(self, runtime):
        self.runtime = runtime
        runtime.damage_to_projectiles = getattr(runtime, 'damage_to_projectiles', 0.0)

    @property
    def assumptions(self):
        return []

    def core_probability(self, caster, part, pierce):
        return None

    def _owns_projectile_skill(self, skill):
        ident = skill.get('Id')
        if self.runtime.key == 'anomaly-ultra':
            return ident in ULTRA_PROJECTILE_SKILLS
        if self.runtime.key == 'anomaly-harvester':
            return ident == HARVESTER_PROJECTILE_SKILL
        return False

    def _cancel_pending_projectiles(self, predicate, reason, time):
        cancelled = 0
        for projectile in self.runtime.projectiles:
            if (projectile.get('kind') != 'hostile' or
                    projectile.get('status') != 'pending' or
                    not self._owns_projectile_skill(
                        projectile.get('source_skill', {})) or
                    not predicate(projectile.get('source_skill', {}))):
                continue
            projectile.update(status='cancelled', clear_reason=reason,
                              cleared_at=time)
            cancelled += 1
        if cancelled:
            self.runtime.log('pending hostile projectile launches cancelled',
                             reason=reason, count=cancelled)
        return cancelled

    def on_part_broken(self, part, time, damaged=True):
        # MonsterContext.OnDestroyParts stops only a matching active skill for
        # which TryGetCancelableSkill succeeds. Already-created ordinary
        # projectiles stay in ProjectileContext._projectileList.
        normalized = ''.join(c for c in str(part).lower() if c.isalnum())
        return self._cancel_pending_projectiles(
            lambda skill: (str(skill.get('CancelType', '')).startswith(
                               'BrokenParts') and
                           normalized in {
                               ''.join(c for c in str(value).lower()
                                       if c.isalnum())
                               for value in skill.get('ControlParts', ())}),
            'launcher part destroyed', time)

    def on_cinematic_start(self, time):
        # Current native MonsterContext stops Fire only for sceneType 4
        # (Dead). Phase 2/3 does not cancel scheduled launches.
        return 0

    def on_phase_changed(self, phase, time):
        return self.on_cinematic_start(time)

    def resolve_target(self, caster, element, weapon, normal):
        if not normal:
            return None
        active = [p for p in self.runtime.projectiles
                  if p.get('status') == 'active' and p.get('destroyable')]
        return min(active, key=lambda p: (p['deadline'], p['id'])) if active else None

    def resolve_hit(self, target, damage, hit_type):
        if target not in self.runtime.projectiles or target.get('status') != 'active':
            return None
        dealt = min(target['hp'], max(0, damage))
        target['hp'] -= dealt
        self.runtime.damage_to_projectiles += dealt
        if target['hp'] <= 0:
            target['status'] = 'destroyed'
            target['destroyed_at'] = self.runtime.time
            self.runtime.log('hostile projectile destroyed', projectile=target['id'])
        return {'handled': True, 'consumed': dealt,
                'destroyed': target['status'] == 'destroyed', 'boss_damage': 0}

    def _flight_seconds(self, skill, monster=None, projectile_index=0):
        """Fallback distance/speed proxy for a curve with no resolved endpoints."""
        speed = skill.get('ProjectileSpeed', 0)
        if speed <= 0:
            return 0.0
        monster = monster or self.runtime.data['monster']
        distance = monster.get('DetectorCenter', 350)
        return distance / speed

    def _flight_source(self):
        return 'DetectorCenter / ProjectileSpeed proxy'

    def _projectile_geometry(self, projectile_index=0):
        return {}

    def _owner_defence(self, skill, stat):
        r = self.runtime
        bonus = sum(value / 10000 for ident, (end, value)
                    in getattr(r, 'effects', {}).items()
                    if ident in r.functions and end > r.time
                    and r.functions[ident]['FunctionType'] == 'StatDef')
        return (stat['LevelDefence'] * (1 + bonus) *
                skill['ProjectileDefRatio'] / 10000)

    def _activate_projectile(self, projectile):
        """Snapshot projectile durability and outgoing damage at actual launch."""
        r = self.runtime
        skill = projectile['source_skill']
        stat = r.stat()
        hp = (_rounded_hp(stat['LevelProjectileHp'] *
                          skill['ProjectileHpRatio'] / 10000 /
                          projectile['projectile_hp_shot_divisor'])
              if projectile['destroyable'] else None)
        defence = projectile.get('volley_defence')
        if defence is None:
            defence = self._owner_defence(skill, stat)
        projectile.update(status='active', hp=hp, max_hp=hp,
                          defence=defence,
                          defence_snapshot=True,
                          defence_snapshot_at=projectile.get(
                              'volley_defence_at', r.time),
                          # A coarse simulation tick can activate several
                          # scheduled fires at once. This is the actual state
                          # capture time; launch_at keeps the ideal schedule.
                          snapshot_at=r.time)
        capture = getattr(r, 'capture_incoming_snapshot', None)
        if capture is not None and r.bm is not None:
            projectile['incoming_snapshot'] = capture()
            projectile['snapshot_at'] = projectile['incoming_snapshot']['time']
        return projectile

    def _launch_projectile(self, skill, node, *, destroyable,
                           projectile_index=0, physical_count=1,
                           muzzle_count=1, prefab_index=0,
                           geometry_index=0, fire_index=0,
                           hp_divisor=None, damage_divisor=None,
                           volley_defence=None, volley_defence_at=None):
        is_timeline = skill['Id'] in TIMELINE_PROJECTILE_SKILLS
        if hp_divisor is None:
            hp_divisor = (max(1, skill['ShotCount']) if is_timeline
                          else physical_count)
        flight = self._flight_seconds(skill, projectile_index=geometry_index)
        launch_at = (self.runtime.time if is_timeline else
                     self.runtime.time + fire_index * skill['DelayTime'] / 100)
        # Timeline divides SkillValue01 by the current prefab's muzzle count;
        # legacy Fire divides by the total selected muzzle count and its
        # FireProjectile path copies that damage without reading ShotCount.
        if damage_divisor is None:
            damage_divisor = (max(1, skill['ShotCount']) * muzzle_count
                              if is_timeline else
                              sum(PROJECTILE_PREFAB_MUZZLE_COUNTS[skill['Id']]))
        projectile_damage_ratio = _rounded_hp(
            skill['SkillValue01'] / damage_divisor)
        projectile_skill = dict(
            skill, ShotCount=1, SkillValue01=projectile_damage_ratio,
            _damage_shots=1)
        projectile = {
            'id': 'projectile-' + str(len(self.runtime.projectiles)),
            'kind': 'hostile', 'skill_id': skill['Id'],
            'hp': None, 'max_hp': None, 'defence': None,
            'defence_snapshot': False,
            'volley_defence': volley_defence,
            'volley_defence_at': volley_defence_at,
            'scheduled_at': self.runtime.time,
            'spawned': launch_at, 'launch_at': launch_at,
            'deadline': launch_at + flight,
            'destroyable': destroyable,
            'status': 'active' if launch_at <= self.runtime.time else 'pending',
            'source_skill': skill,
            'skill': projectile_skill, 'node': dict(node),
            'physical_index': projectile_index,
            'fire_index': fire_index,
            'physical_count': physical_count,
            'projectile_hp_shot_divisor': hp_divisor,
            'projectile_damage_ratio_divisor': damage_divisor,
            'projectile_damage_ratio': projectile_damage_ratio,
            'prefab_index': prefab_index,
            'prefab_muzzle_count': muzzle_count,
            'flight_seconds': flight,
            'timing_source': self._flight_source(),
        }
        projectile.update(self._projectile_geometry(geometry_index))
        self.runtime.projectiles.append(projectile)
        if projectile['status'] == 'active':
            self._activate_projectile(projectile)
        self.runtime.log('hostile projectile launched' if projectile['status'] == 'active'
                         else 'hostile projectile scheduled',
                         projectile=projectile['id'],
                         shot=skill['SkillAniNumber'], hp=projectile['hp'],
                         launch_at=round(launch_at, 3),
                         deadline=round(projectile['deadline'], 3),
                         timing='approximate')
        return projectile

    def _launch_physical_projectiles(self, skill, node, *, destroyable):
        muzzle_counts = PROJECTILE_PREFAB_MUZZLE_COUNTS[skill['Id']]
        is_timeline = skill['Id'] in TIMELINE_PROJECTILE_SKILLS
        schedule = None
        if not is_timeline:
            destroyed = {name for name in self.runtime.world.parts.parts
                         if not self.runtime.world.parts.alive(name)}
            schedule = ordinary_fire_schedule(
                self.runtime.key, skill['Id'], start=self.runtime.time,
                destroyed_parts=destroyed)
            count = len(schedule['impact_events'])
            if not count:
                self.runtime.log('projectile weapon prefab unavailable',
                                 shot=skill['SkillAniNumber'],
                                 destroyed_parts=sorted(destroyed))
                return []
        else:
            count = max(1, skill['ShotCount']) * sum(muzzle_counts)
        # The ordinary Fire coroutine stores owner DEF/MakeDefenceRatio once
        # in FireData before delayed shots. Timeline markers launch directly.
        volley_defence = (self._owner_defence(skill, self.runtime.stat())
                          if not is_timeline else None)
        volley_defence_at = self.runtime.time if not is_timeline else None
        launched = []
        index = 0
        shots = max(1, skill['ShotCount'])
        if not is_timeline and skill['ShotTiming'] == 'Sequence':
            # Sequence alternates prefab entries, then advances the selected
            # prefab's muzzle index from the quotient of fireIndex/prefabCount.
            prefab_count = len(muzzle_counts)
            for fire_index in range(count):
                prefab_index = fire_index % prefab_count
                muzzle_index = ((fire_index // prefab_count) %
                                muzzle_counts[prefab_index])
                geometry_index = sum(muzzle_counts[:prefab_index]) + muzzle_index
                launched.append(self._launch_projectile(
                    skill, node, destroyable=destroyable,
                    projectile_index=index, physical_count=count,
                    muzzle_count=muzzle_counts[prefab_index],
                    prefab_index=prefab_index, geometry_index=geometry_index,
                    fire_index=fire_index,
                    hp_divisor=schedule['projectile_hp_ratio_divisor'],
                    damage_divisor=schedule['damage_ratio_divisor'],
                    volley_defence=volley_defence,
                    volley_defence_at=volley_defence_at))
                index += 1
        else:
            for shot_index in range(shots):
                for prefab_index, muzzle_count in enumerate(muzzle_counts):
                    for muzzle_index in range(muzzle_count):
                        geometry_index = sum(muzzle_counts[:prefab_index]) + muzzle_index
                        launched.append(self._launch_projectile(
                            skill, node, destroyable=destroyable,
                            projectile_index=index, physical_count=count,
                            muzzle_count=muzzle_count, prefab_index=prefab_index,
                            geometry_index=geometry_index,
                            fire_index=shot_index,
                            hp_divisor=(schedule['projectile_hp_ratio_divisor']
                                        if schedule else None),
                            damage_divisor=(schedule['damage_ratio_divisor']
                                            if schedule else None),
                            volley_defence=volley_defence,
                            volley_defence_at=volley_defence_at))
                        index += 1
        return launched

    def _advance_projectiles(self, t):
        for projectile in self.runtime.projectiles:
            if projectile.get('kind') != 'hostile':
                continue
            if projectile.get('status') == 'pending' and t >= projectile['launch_at']:
                self._activate_projectile(projectile)
                self.runtime.log('hostile projectile launched',
                                 projectile=projectile['id'],
                                 shot=projectile['skill']['SkillAniNumber'])
            if projectile.get('status') != 'active':
                continue
            if t < projectile['deadline']:
                continue
            projectile['status'] = 'hit'
            projectile['hit_at'] = t
            node = dict(projectile['node'])
            if projectile.get('incoming_snapshot') is not None:
                node['_incoming_snapshot'] = projectile['incoming_snapshot']
            self.runtime.receive_attack(projectile['skill'], node)
            self.runtime.log('hostile projectile hit squad',
                             projectile=projectile['id'],
                             shot=projectile['skill']['SkillAniNumber'])

    def advance(self, t):
        self._advance_projectiles(t)

    def advance_cinematic_projectiles(self, t):
        """Advance launched shots while these phase timelines keep Spot ticks.

        Ultra and Harvester serialize ``isStopTick=0`` on their phase options.
        This intentionally does not advance Harvester summon AI: the phase
        event stops monster behavior, while an already-created projectile is
        independently updated by ProjectileContext.
        """
        self._advance_projectiles(t)

    def rebase_cinematic_functions(self, seconds):
        """Map surviving projectile deadlines from wall time to battle time."""
        for projectile in self.runtime.projectiles:
            if (projectile.get('kind') != 'hostile' or
                    projectile.get('status') != 'active'):
                continue
            for field in ('spawned', 'launch_at', 'deadline'):
                if projectile.get(field) is not None:
                    projectile[field] -= seconds


class UltraMechanics(_BaseMechanics):
    """Ultra core exposure plus non-interceptable projectile travel."""

    @property
    def assumptions(self):
        return [
            'Ultra projectile flight uses DetectorCenter / ProjectileSpeed because '
            'the extracted skill record has speed but no resolved target path.',
            'Ultra core-to-both-chambers pierce overlap is backed by the installed '
            'bind-pose capsule geometry and the exact Anomaly Ultra guide. Animated '
            'per-character ray traces remain unavailable.',
        ]

    def core_probability(self, caster, part, pierce):
        r = self.runtime
        if not r.world.parts.alive('Weapon_01'):
            return 0.0
        exposed = r.world.phase >= 2
        # Core bonus belongs only to the core collider.  Pierce through the
        # hidden core is represented as distinct core/chamber collisions; it
        # must not turn a poison-chamber hit into one core-boosted hit.
        return float(part == 'Weapon_01' and (exposed or pierce))

    def player_collision_targets(self, part, position, pierce):
        """Additional installed part colliders crossed by a core-aimed shot.

        Both current public fight guides describe one piercing core shot as
        hitting the core and both poison chambers.  The core remains the
        primary (core-bonus) collision; these are separate regular part hits.
        The common dispatcher consumes these names if it supports multi-part
        collision routing.
        """
        if not pierce or part not in (None, 'Weapon_01'):
            return ()
        return tuple(name for name in ('Weapon_02', 'Weapon_03')
                     if self.runtime.world.parts.alive(name))

    def preferred_part(self, caster, pierce):
        """Aim controlled pierce fire at Ultra's living phase-one core."""
        if (self.runtime.world.parts.alive('Weapon_01')
                and (pierce or self.runtime.world.phase >= 2)):
            return 'Weapon_01'
        return None

    def part_targetable(self, part, time):
        if part == 'Weapon_01':
            return self.runtime.world.phase >= 2
        return None

    def perform_skill(self, skill, node):
        # Ultra Shot06/07 use legacy AttackV2/V3 with ten selected muzzles;
        # timeline Shot03/04 each use one prefab with one muzzle.
        if skill.get('Id') in ULTRA_PROJECTILE_SKILLS:
            self._launch_physical_projectiles(skill, node, destroyable=False)
            return True
        return False


class HarvesterMechanics(_BaseMechanics):
    """Harvester projectiles, core exposure, and native add attack loops."""

    handles_summons = True
    _GROUND_STUN_ADDS = {3220060113}
    _FLYING_STUN_ADDS = {1210010113}
    _SNIPER_ADDS = {3220070113}
    _SUICIDE_ADDS = {1220050613, 3210040113}

    @property
    def assumptions(self):
        return [
            'Harvester add spawn offsets, windups, cooldown choices, skills, HP and '
            'self-destruction come from CallingList, Monster and add behavior trees.',
            'Harvester Drop summons start 20 units above ActionPoint and wait for '
            'the native IsGround gate; Teleport summons remain at StartPoint until '
            'SetTeleport and flying brake complete. The 43/22 Spot-tick readiness '
            'gates are calibrated against isolated-client SpawnActionEndEvent traces. '
            'The landing collider and per-frame brake data remain unresolved.',
            'Harvester missile flight uses the installed spawn point, WeaponObject03 '
            'bind-pose launchers and ProjectileSpeed toward formation center. The '
            'animated launch socket, curved route and per-slot endpoint remain unknown.',
        ]

    def core_probability(self, caster, part, pierce):
        return float(not self.runtime.world.parts.alive('Head'))

    def perform_skill(self, skill, node):
        r = self.runtime
        if skill.get('FireType') == 'Calling':
            group = skill['SkillValue01']
            for row in r.data['calls']:
                if row['GroupId'] == group:
                    r.pending.append({'kind': 'harvester_summon',
                                      'at': r.time + row['SpawnTime'],
                                      'record': row})
            r.log('Harvester summon wave called', group=group,
                  count=sum(c['GroupId'] == group for c in r.data['calls']))
            return True
        if skill['Id'] == HARVESTER_PROJECTILE_SKILL:
            if '_locked_targets' not in node and r.bm:
                node = dict(node, _locked_targets=r.attack_targets(skill, node))
            self._launch_physical_projectiles(skill, node, destroyable=True)
            return True
        if skill['Id'] == HARVESTER_OBJECT_SKILL:
            # ObjectCreate targets Nothing (100%).  This is the visual/object lead-in
            # to the failed-QTE beam, not a direct character hit.
            r.log('Harvester failed-QTE object created', shot=skill['SkillAniNumber'])
            return True
        return False

    def _monster(self, ident):
        return next(m for m in self.runtime.data['monsters'] if m['Id'] == ident)

    def _skill(self, monster):
        ids = {s['SkillId'] for s in monster['SkillData'] if s['SkillId']}
        return next(s for s in self.runtime.data['skills']
                    if s['Id'] in ids and s['SkillValueType01'] == 'Percent'
                    and s['SkillValue01'] > 0)

    def _points(self, row):
        points = HARVESTER_AIR_POINTS if row['StartPoint'] in HARVESTER_AIR_POINTS else HARVESTER_GROUND_POINTS
        return points[row['StartPoint']], points[row['ActionPoint']], points[row['DirPoint']]

    def _entry_seconds(self, monster, row, dt=1 / 60):
        """Native SpawnAction completion at the installed 17 ms Spot tick.

        Drop waits for CharacterController grounding as its integrated height
        first crosses ActionPoint ground level. Teleport places the add after
        three ticks and waits for SpotSetting.FlyBrakeDuration (0.3 s) plus
        the coroutine's observed completion tick.
        """
        tick = .017
        if row['SpawnType'] == 'Teleport':
            return (3 + math.ceil(.3 / tick) + 1) * tick
        landing_tick = 1
        while self._drop_height(landing_tick * tick) > 0:
            landing_tick += 1
        return landing_tick * tick

    @staticmethod
    def _drop_height(elapsed, tick=.017):
        """Integrate native GetMoveDelta gravity at the installed Spot tick.

        TargetDir.y (-.825) and the .014-unit lead into SpawnAction were
        measured from two live Drops. The gravity term is exact native code:
        ``(InAirTime * 5)^2 * SpotSetting.MonsterGravity`` with gravity 6.
        """
        height = 20.0 - .014
        air_time = 0.0
        remaining = max(0.0, elapsed)
        while remaining > 1e-9:
            dt = min(tick, remaining)
            air_time += dt
            height += (-.825 - (air_time * 5) ** 2 * 6) * dt
            remaining -= dt
        return height

    def _flight_seconds(self, skill, monster=None, projectile_index=0):
        # Provisional center-slot duration before the physical launch resolves
        # the locked recipient and its current stance.
        speed = skill.get('ProjectileSpeed', 0) * NATIVE_SPEED_SCALE
        if speed <= 0:
            return 0.0
        local = HARVESTER_LAUNCHERS[projectile_index]
        launch = tuple(HARVESTER_BOSS_POINT[i] + local[i] for i in range(3))
        return math.dist(launch, (0.0, 0.0, 0.0)) / speed

    def _flight_source(self):
        return 'native endpoint distance / scaled ProjectileSpeed'

    def _projectile_geometry(self, projectile_index=0):
        local = HARVESTER_LAUNCHERS[projectile_index]
        launch = tuple(HARVESTER_BOSS_POINT[i] + local[i] for i in range(3))
        return {
            'path': 'ProjectileCurve',
            'boss_position': HARVESTER_BOSS_POINT,
            'launcher_bind_position': local,
            'launcher_position': launch,
            'launcher_positions': [tuple(HARVESTER_BOSS_POINT[i] + item[i]
                                         for i in range(3))
                                   for item in HARVESTER_LAUNCHERS],
            'target_position': (0.0, 0.0, 0.0),
            'geometry_status': 'bind-pose center-target estimate',
        }

    def _projectile_target_position(self, target):
        observed = getattr(self.runtime, 'projectile_target_positions', None) or {}
        if target in observed:
            value = observed[target]
            if isinstance(value, dict) and 'character' in value:
                value = value['character']
            if isinstance(value, dict) and 'aiming' in value:
                hiding = (target in getattr(self.runtime, 'covered', ()) or
                          bool(getattr(getattr(self.runtime, 'bm', None),
                                       'state', {}).get('planned_cover')))
                value = value.get('hiding' if hiding else 'aiming')
            if isinstance(value, dict) and all(axis in value for axis in ('x', 'y', 'z')):
                value = tuple(value[axis] for axis in ('x', 'y', 'z'))
            if value is not None and not isinstance(value, dict):
                return tuple(map(float, value)), 'runtime observed target transform'
        bm = getattr(self.runtime, 'bm', None)
        names = list(bm.state.get('hp', {})) if bm else []
        if target in names and names.index(target) < len(FORMATION_AIM):
            slot = names.index(target)
            hiding = (target in getattr(self.runtime, 'covered', ()) or
                      bool(bm.state.get('planned_cover')))
            if hiding:
                return tuple(a + b for a, b in zip(FORMATION_AIM[slot],
                                                   HIDE_TRANSLATION)), \
                       'measured shared hiding stance endpoint'
            return FORMATION_AIM[slot], 'measured shared aiming stance endpoint'
        return (0.0, 0.0, 0.0), 'unknown slot geometry proxy'

    def _activate_projectile(self, projectile):
        # FireData locks the target identity when the attack starts. Native
        # CreateTargetData reads its head transform at each physical launch.
        node = projectile['node']
        targets = list(node.get('_locked_targets', ()))
        target = targets[0] if targets else None
        target_position, target_source = self._projectile_target_position(target)
        coordinates = getattr(self.runtime.world, 'coordinates', None)
        boss_position = (tuple(coordinates[axis] for axis in ('x', 'y', 'z'))
                         if coordinates else HARVESTER_BOSS_POINT)
        local = projectile['launcher_bind_position']
        launcher = tuple(boss_position[i] + local[i] for i in range(3))
        distance = math.dist(launcher, target_position)
        speed = projectile['source_skill']['ProjectileSpeed'] * NATIVE_SPEED_SCALE
        flight = distance / speed if speed > 0 else 0.0
        projectile.update(target=target, target_position=target_position,
                          target_position_source=target_source,
                          boss_position=boss_position,
                          launcher_position=launcher,
                          endpoint_distance=distance,
                          native_speed=speed, flight_seconds=flight,
                          deadline=projectile['launch_at'] + flight,
                          geometry_status=('prefab bind-pose launcher + ' + target_source))
        return super()._activate_projectile(projectile)

    def _prefire(self, monster_id):
        if monster_id in self._FLYING_STUN_ADDS:
            return self.runtime.rng.choice((0.5, 1.0, 1.5))
        if monster_id in self._GROUND_STUN_ADDS or monster_id in self._SNIPER_ADDS:
            return 3.0
        return 0.0

    def _cooldown(self, monster_id):
        if monster_id in self._FLYING_STUN_ADDS:
            return self.runtime.rng.choice((0.0, 5.0))
        if monster_id in self._GROUND_STUN_ADDS:
            return self.runtime.rng.choice((1.0, 3.0))
        if monster_id in self._SNIPER_ADDS:
            # The alternate behavior-tree branch is a one-second JumpTo.
            return self.runtime.rng.choice((1.0, 3.0))
        return math.inf

    def _spawn_add(self, row, t):
        r = self.runtime
        monster = self._monster(row['MonsterId'])
        skill = self._skill(monster)
        hp = _rounded_hp(r.stat(monster)['LevelHp'] * monster['HpRatio'] / 10000)
        start, action, direction = self._points(row)
        route_distance = math.dist(start, action)
        entry = self._entry_seconds(monster, row)
        windup = self._prefire(monster['Id']) + skill['CastingTime'] / 100
        teleported = row['SpawnType'] == 'Teleport'
        initial = start if teleported else (action[0], action[1] + self._drop_height(0), action[2])
        add = {
            'id': 'summon-' + str(len(r.adds)), 'monster_id': monster['Id'],
            'hp': hp, 'max_hp': hp, 'spawned': t, 'protected': False,
            'defence': r.stat(monster)['LevelDefence'] * monster['DefenceRatio'] / 10000,
            'skill': skill, 'state': 'spawn-action',
            'ready_at': t + entry, 'next_attack': t + entry + windup,
            'entry_seconds': entry,
            'entry_distance': route_distance,
            'entry_speed': 0.0,
            'move_speed': 0.0,
            'base_move_speed': monster['SpotMoveSpeed'] / 100,
            'out_combat_speed_rate': 3.0,
            'in_combat_speed_rate': 1.0,
            'acceleration_rate': monster.get('SpotAccelerationTime', 0) / 100,
            'position': initial,
            'last_move_time': t,
            'entry_timing_source': ('SetTeleport plus SetBrake, measured SpawnActionEndEvent'
                                    if teleported else
                                    'SetSpawnDrop IsGround gate, measured SpawnActionEndEvent'),
            'entry_timing_status': ('runtime-calibrated Spot ticks; per-frame SetBrake data '
                                    'pending' if teleported else
                                    'runtime-calibrated Spot ticks and fall trajectory; '
                                    'landing collider remains source-dependent'),
            'spawn_type': row['SpawnType'], 'start_point': row['StartPoint'],
            'teleport_at': t + 3 * .017 if teleported else None,
            'spawn_action_end_at': t + entry,
            'spawn_action_tick_seconds': 0.017,
            'spawn_action_ticks': round(entry / .017),
            'action_point': row['ActionPoint'], 'dir_point': row['DirPoint'],
            'start_position': start, 'action_position': action,
            'direction_position': direction,
            'suicide': monster['Id'] in self._SUICIDE_ADDS,
        }
        r.adds.append(add)
        r.log('summon spawned', monster=monster['Id'], hp=hp,
              summon=add['id'], ready_at=round(add['ready_at'], 3),
              timing='runtime-calibrated SpawnAction gate and installed AI windup')

    def _advance_add_movement(self, add, monster, t):
        if add['state'] != 'spawn-action':
            return
        elapsed = max(0.0, t - add['spawned'])
        if elapsed >= add['entry_seconds']:
            add.update(position=add['action_position'], state='windup',
                       arrived_at=add['ready_at'])
        elif add['spawn_type'] == 'Teleport':
            if t >= add['teleport_at']:
                add['position'] = add['action_position']
        elif add['spawn_type'] == 'Drop':
            x, y, z = add['action_position']
            add['position'] = (x, y + self._drop_height(elapsed), z)
        add['last_move_time'] = t

    def _advance_adds(self, t):
        r = self.runtime
        for add in r.adds:
            if add['hp'] <= 0 or add.get('state') in ('destroyed', 'self-destructed'):
                continue
            monster = self._monster(add['monster_id'])
            self._advance_add_movement(add, monster, t)
            # SpawnAction/first-move must finish before the attack branch runs.
            # An estimated clock cannot authorize a hit while movement remains
            # in progress (for example after a coarse or irregular tick).
            if add['state'] == 'spawn-action' or t < add['next_attack']:
                continue
            r.receive_attack(add['skill'], {}, monster=monster, source=add['id'])
            add['attacks'] = add.get('attacks', 0) + 1
            add['last_attack'] = t
            if add['suicide']:
                add.update(hp=0, state='self-destructed',
                           clear_reason='suicide attack', cleared_at=t)
                r.log('summon self-destructed', summon=add['id'],
                      monster=add['monster_id'])
                continue
            cooldown = self._cooldown(add['monster_id'])
            prefire = self._prefire(add['monster_id'])
            add['state'] = 'cooldown'
            add['next_attack'] = (t + cooldown + prefire +
                                  add['skill']['CastingTime'] / 100)

    def advance(self, t):
        r = self.runtime
        for item in list(r.pending):
            if item.get('kind') != 'harvester_summon' or t < item['at']:
                continue
            r.pending.remove(item)
            self._spawn_add(item['record'], t)
        self._advance_adds(t)
        super().advance(t)

    def resolve_target(self, caster, element, weapon, normal):
        target = super().resolve_target(caster, element, weapon, normal)
        if target is not None or not normal:
            return target
        living = [a for a in self.runtime.adds if a['hp'] > 0]
        return min(living, key=lambda a: (a['next_attack'], a['id'])) if living else None

    def resolve_hit(self, target, damage, hit_type):
        result = super().resolve_hit(target, damage, hit_type)
        if result is not None:
            return result
        if target not in self.runtime.adds or target['hp'] <= 0:
            return None
        dealt = min(target['hp'], max(0, damage))
        target['hp'] -= dealt
        self.runtime.damage_to_adds += dealt
        if target['hp'] <= 0:
            target.update(state='destroyed', cleared_at=self.runtime.time,
                          clear_reason='squad')
            self.runtime.log('summon cleared', summon=target['id'],
                             monster=target['monster_id'])
        return {'handled': True, 'consumed': dealt,
                'destroyed': target['hp'] <= 0, 'boss_damage': 0}


def build_anomaly_mechanics(runtime):
    if runtime.key == 'anomaly-ultra':
        return UltraMechanics(runtime)
    if runtime.key == 'anomaly-harvester':
        return HarvesterMechanics(runtime)
    return None
