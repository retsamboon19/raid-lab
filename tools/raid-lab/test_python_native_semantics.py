"""Regressions for native hit, target-state and finite-monster semantics."""
import unittest
from types import SimpleNamespace
from unittest.mock import patch

import core
from calculator.timeline import _bullet_core_fracs
from calculator.buff_manager import BuffManager
from raid_boss_combat import RaidBossRuntime
from test_complete_roster import manager


class NativeSemanticsTests(unittest.TestCase):
    def test_ultra_flight_uses_world_endpoints_and_native_speed_units(self):
        import math
        from anomaly_ultra_harvester import UltraMechanics, NATIVE_SPEED_SCALE
        bm, names, states = manager('Red Hood')
        r = RaidBossRuntime([], 180, key='anomaly-ultra')
        r.bind(bm, [s.char for s in states.values()], states)
        mechanics = UltraMechanics(r)
        skill = next(s for s in r.data['skills'] if s['Id']==510632)
        projectile = mechanics._launch_projectile(skill, {'_locked_targets':names}, destroyable=False)
        expected = math.dist(projectile['launcher_position'],projectile['target_position'])/(skill['ProjectileSpeed']*NATIVE_SPEED_SCALE)
        self.assertAlmostEqual(projectile['flight_seconds'],expected)
        self.assertGreater(expected,1)
        self.assertEqual(projectile['target'],names[0])

    def test_native_star_policy_does_not_hold_teammates_for_slippers(self):
        bm, names, states = manager('Anis: Star', 'Helm')
        r = RaidBossRuntime([], 180, key='anomaly-mirror-container')
        r.bind(bm, [s.char for s in states.values()], states)
        self.assertTrue(r.mirror_core_pressure)
        for name in names:
            self.assertIsNone(r.select_part(name))
            self.assertFalse(r.hold_fire(name, states[name].weapon_type, '전격'))

    def test_ultra_does_not_retarget_chambers_after_core_destruction(self):
        bm, names, states = manager('Red Hood')
        r = RaidBossRuntime([], 180, key='anomaly-ultra')
        r.bind(bm, [s.char for s in states.values()], states)
        r.world.parts.parts['Weapon_01']['hp'] = 0
        self.assertIsNone(r.select_part(names[0]))

    def test_stun_does_not_bank_shots_for_recovery(self):
        bm, names, states = manager('Privaty')
        cs = states[names[0]]
        cs.next_fire_time = 0
        with patch.object(bm, 'is_stunned', return_value=True):
            self.assertEqual(cs.tick(10, bm, {}, {}), [])
        self.assertEqual(cs.next_fire_time, 10)
        # At recovery only the current shot is due, not ten seconds of fire.
        with patch.object(cs, '_fire', return_value=[]) as fire:
            cs._tick_auto(10, bm, {}, {})
        self.assertEqual(fire.call_count, 1)

    def test_missed_muzzle_does_not_emit_a_hit(self):
        self.assertEqual(_bullet_core_fracs([1,0,1,0],2,[0,0,1,0]),[1])
        self.assertEqual(_bullet_core_fracs([1],1,[0]),[])
        self.assertEqual(_bullet_core_fracs([1],1,[1]),[1])

    def test_auto_fire_without_contact_consumes_ammo_but_has_no_hit_triggers(self):
        bm,names,states=manager('Privaty')
        name=names[0];cs=states[name];cs.ammo=1
        result=dict(damage=0,is_crit=False,crit_frac=1,collision_hits=0,
                    core_hits=0,part_hits=0,body_hits=0)
        with patch('calculator.timeline._encounter_damage',return_value=result), \
             patch.object(bm,'notify',wraps=bm.notify) as notify, \
             patch.object(bm,'mark_normal_attack_landed') as landed:
            cs._fire(1,bm,{'core_px':0},{'rng_mode':'expected'})
        events=[c.args[0] for c in notify.call_args_list]
        self.assertIn('on_attack',events)
        self.assertIn('last_bullet_fire',events)
        for event in ('hit_count','last_bullet','crit_hit','crit_pellet_hit','core_hit','pellet_hit_single'):
            self.assertNotIn(event,events)
        landed.assert_not_called()
        self.assertEqual(cs.ammo,0)

    def test_named_state_is_per_recipient_and_per_expiry(self):
        bm=object.__new__(BuffManager)
        r=SimpleNamespace(time=3,select_enemy_effect_targets=lambda *a:[],
                          last_enemy_target_by_caster={'shooter':'add-2'})
        bm.state={'encounter_runtime':r}
        active=SimpleNamespace(target_chars=['__enemy__'],enemy_target_windows={
            '__boss__':dict(activated_at=1,expires_at=5),
            'add-1':dict(activated_at=1,expires_at=2)})
        bm._by_name=lambda name:[active]
        self.assertFalse(bm._has_target_state('mark',caster='shooter',t=3))
        self.assertFalse(bm._has_target_state('mark',target='add-1',t=3))
        self.assertTrue(bm._has_target_state('mark',target='__boss__',t=3))
        self.assertFalse(bm._has_target_state('mark',target='__boss__',t=5))

    def test_lethal_hit_stops_next_attack_and_keeps_overkill_separate(self):
        r=RaidBossRuntime([],180,key='anomaly-harvester');r.time=12
        cap=r.boss_max_hp
        def lethal(*args):
            r.damage=cap+123
            return {'damage':234}
        with patch.object(r,'_resolve_active',side_effect=lethal):
            first=r.resolve('a','Fire','AR',{},lambda **a:{'damage':999},{})
            second=r.resolve('b','Fire','AR',{},lambda **a:{'damage':999},{})
        self.assertEqual(first['damage'],234)
        self.assertEqual(second['damage'],0)
        self.assertEqual(second['collision_hits'],0)
        r.advance(13)
        self.assertEqual(r.time,12)
        report=r.report()
        self.assertEqual(report['boss_hp_damage'],cap)
        self.assertEqual(report['boss_damage_total'],cap+123)
        self.assertEqual(report['boss_remaining_hp'],0)
        self.assertEqual(report['boss_defeated_at'],12)
        self.assertEqual(report['survival'],'boss defeated')


if __name__=='__main__':unittest.main()
