"""Original153 regressions behind the Ultra and Harvester ranking comparisons."""
import unittest

from test_complete_roster import manager, buff
from test_raid_boss_combat import hit
from raid_boss_combat import RaidBossRuntime


def encounter(*names, key="anomaly-ultra"):
    bm, ids, states = manager(*names)
    bm.battle_start(0)
    runtime = RaidBossRuntime([], 180, key=key)
    runtime.bind(bm, [cs.char for cs in states.values()], states)
    return runtime, bm, ids


class RankingParityTests(unittest.TestCase):
    def test_harvester_targeted_cover_uses_primary_attack_lifecycle(self):
        r,bm,(n,other)=encounter('Liter','Crown',key='anomaly-harvester')
        r.harvester_primary_attack=dict(at=1,node=64,targets=[n],phase=1,consumed=False)
        r.time=1;r._native_cover_observed_at=.95;r.update_cover(1)
        self.assertNotIn(n,r.covered)
        r.time=1.05;r._native_cover_observed_at=1.05;r.update_cover(1.05)
        self.assertEqual(r.covered,{n})
        # A parallel summon does not end the primary attack's input ownership.
        r.world.attacks[24]=dict(impacts=[],shot=9)
        r.covered=set();r.time=3;r.update_cover(3)
        self.assertEqual(r.covered,{n})
        # Missile primary node 71 releases targeted cover rather than extending it.
        r.harvester_primary_attack=dict(at=3,node=71,targets=[other],phase=1,consumed=False)
        r.harvester_cover_owner=None;r.covered=set();r._native_cover_observed_at=3
        r.update_cover(3)
        self.assertEqual(r.covered,set())

    def test_harvester_qte_preempts_without_reacquiring_same_attack(self):
        r,bm,(n,)=encounter('Liter',key='anomaly-harvester')
        r.harvester_primary_attack=dict(at=1,node=57,targets=[n],phase=1,consumed=False)
        r.time=1;r._native_cover_observed_at=1;r.update_cover(1)
        self.assertEqual(r.covered,{n})
        r.active={'event':{}};r.covered=set();r.update_cover(2)
        self.assertIsNone(r.harvester_cover_owner)
        r.active=None;r.update_cover(3)
        self.assertEqual(r.covered,set())

    def test_harvester_targeted_cover_requires_living_target_and_cover(self):
        r,bm,(n,)=encounter('Liter',key='anomaly-harvester')
        for field in ('cover','hp'):
            r.cover[n]=100;bm.state['hp'][n]=100
            (r.cover if field=='cover' else bm.state['hp'])[n]=0
            r.harvester_primary_attack=dict(at=1,node=64,targets=[n],phase=1,consumed=False)
            r.time=1;r._native_cover_observed_at=1;r.covered=set();r.update_cover(1)
            self.assertEqual(r.covered,set())

    def test_original_seeded_random_matches_managed_next(self):
        from original_random import OriginalRandom
        r=OriginalRandom(1)
        self.assertEqual([r.next_int() for _ in range(5)],
                         [534011718,237820880,1002897798,1657007234,1412011072])
        r=OriginalRandom(1)
        self.assertEqual([r.randrange(5) for _ in range(5)],[1,0,2,3,3])

    def test_poison_stacks_cap_and_expire_as_one_effect(self):
        r,bm,(n,)=encounter('Liter')
        f=r.functions[1999247];values=[]
        r.hurt_function_damage=lambda function,*args,**kw: values.append(function['FunctionValue']) or 0
        for i in range(7):
            r.time=i/10
            bm.tick(r.time)
            r.apply_hurt_dot(f,n,r.data['monster'])
        self.assertEqual(values,[3000,6000,9000,12000,15000,15000,15000])
        self.assertEqual(len(r.dot_ticks),1)
        r.time=20;bm.tick(20);r.advance_dots(20)
        self.assertEqual(r.dot_ticks,[])
        r.apply_hurt_dot(f,n,r.data['monster'])
        self.assertEqual(values[-1],3000)

    def test_exposed_ultra_circle_holds_followers_but_reload_completes(self):
        from types import SimpleNamespace
        r,bm,(liter,crown)=encounter('Liter','Crown')
        r.choose_qte_controller=lambda:None
        r.target=lambda *args:None
        r.active=dict(controller=liter,graph=SimpleNamespace(targets={1:dict(status='active')}))
        cs=r.char_states[crown]
        cs.ammo=0;cs.reloading_until=1;r.time=1
        cs.tick(1,bm,{},dict(encounter_runtime=r))
        self.assertGreater(cs.ammo,0)
        self.assertTrue(r.hold_fire(crown,'MG','철갑'))

    def test_qte_handoff_restarts_settle_and_weapon_delay(self):
        from types import SimpleNamespace
        r,bm,(liter,crown)=encounter('Liter','Crown')
        target=dict(id=1,weapons=None,element=None)
        r.choose_qte_controller=lambda:None
        r.update_qte_hazards=lambda:None
        r.active=dict(controller=liter,index=0,graph_target=1,
                      graph=SimpleNamespace(aim=lambda t:target),
                      event=dict(id='qte',controller='auto'))
        self.assertIsNone(r.target(liter,'SMG','철갑'))
        r.time=.3
        self.assertIs(r.target(liter,'SMG','철갑'),target)
        r.active['controller']=crown
        self.assertIsNone(r.target(crown,'MG','철갑'))
        self.assertAlmostEqual(r.aim_ready,.55)
        r.time=.6
        self.assertIs(r.target(crown,'MG','철갑'),target)

    def test_native_auto_fire_discards_fractional_interval(self):
        r,bm,(n,)=encounter('Liter')
        cs=r.char_states[n];times=[]
        cs._fire=lambda t,*args: times.append(t) or []
        cs._native_pre_aim_until=0;cs.next_fire_time=0;cs.fire_rate=26.6666666667
        for frame in range(61):cs._tick_auto(frame/60,bm,{}, {})
        self.assertEqual(len(times),21)
        self.assertAlmostEqual(times[1],0.05)
        self.assertAlmostEqual(times[-1],1.0)

    def test_native_machine_gun_interval_uses_new_warmup(self):
        r,bm,(n,)=encounter('Crown');cs=r.char_states[n]
        cs._native_pre_aim_until=0;cs.next_fire_time=0;cs._cool_warmup=lambda *args:None
        def fire(*args):cs.warmup_shots+=1;return []
        cs._fire=fire
        cs._tick_auto(0,bm,{}, {})
        self.assertAlmostEqual(cs.next_fire_time,1/cs._current_fire_rate(bm,0))

    def test_native_mg_does_not_cool_between_scheduled_aim_shots(self):
        r,bm,(n,)=encounter('Crown');cs=r.char_states[n];shots=[]
        def fire(t,*args):
            cs.warmup_shots=min(cs.warmup_bullets,cs.warmup_shots+1)
            shots.append(t)
            return []
        cs._fire=fire
        for frame in range(301):cs._tick_auto(frame/60,bm,{}, {})
        # Native trace: sustained Crown ammo falls ~60/s after warmup.
        # The old gap-based cooler stalled this at 30/s at 60 Hz.
        self.assertEqual(sum(4 < t <= 5 for t in shots),60)
        self.assertEqual(cs.warmup_shots,cs.warmup_bullets)

    def test_native_mg_idle_preserves_warmup_cover_cools(self):
        r,bm,(n,)=encounter('Crown');cs=r.char_states[n]
        cs.warmup_shots=cs.warmup_bullets
        r.hold_fire=lambda *args:True
        cs.tick(1,bm,{},dict(encounter_runtime=r))
        cs.tick(1.1,bm,{},dict(encounter_runtime=r))
        self.assertEqual(cs.warmup_shots,cs.warmup_bullets)
        bm.state['encounter_cover']={n}
        cs.tick(1.2,bm,{},dict(encounter_runtime=r))
        self.assertLess(cs.warmup_shots,cs.warmup_bullets)

    def test_native_pre_aim_delay_gates_auto_charge_and_reload(self):
        r,bm,(liter,hood)=encounter('Liter','Red Hood')
        cs=r.char_states[liter];shots=[]
        cs._fire=lambda t,*args:shots.append(t) or []
        cs._tick_auto(.1,bm,{}, {})
        self.assertEqual(shots,[])
        cs._tick_auto(.2,bm,{}, {})
        self.assertEqual(shots,[.2])
        charged=r.char_states[hood]
        charged._tick_charge(.1,bm,{}, {})
        self.assertEqual(charged._charge_phase,'ready')
        charged._tick_charge(.2,bm,{}, {})
        self.assertEqual(charged._charge_phase,'charging')
        cs._finish_reload(2,bm)
        self.assertAlmostEqual(cs._native_pre_aim_until,2.2)
        cs._tick_auto(2.1,bm,{}, {})
        self.assertEqual(shots,[.2])

    def test_native_cover_release_restarts_pre_aim_delay(self):
        r,bm,(n,)=encounter('Liter');cs=r.char_states[n]
        r.hold_fire=lambda *args:False
        bm.state['encounter_cover']={n}
        cs.tick(1,bm,{},dict(encounter_runtime=r))
        self.assertTrue(cs._native_hidden)
        bm.state['encounter_cover']=set()
        cs.tick(2,bm,{},dict(encounter_runtime=r))
        self.assertAlmostEqual(cs._native_pre_aim_until,2.2)
        self.assertFalse(cs._native_hidden)

    def test_no_target_holds_ammunition(self):
        r,bm,(n,)=encounter('Crown')
        r.blocks=lambda kind:kind=='untargetable'
        self.assertTrue(r.hold_fire(n,'MG','철갑'))
        r.blocks=lambda kind:False
        self.assertFalse(r.hold_fire(n,'MG','철갑'))

    def test_qte_owner_uses_actual_shots_and_rejects_release_fired_actor(self):
        from types import SimpleNamespace
        r,bm,(liter,crown,hood)=encounter('Liter','Crown','Red Hood')
        r.update_qte_hazards=lambda:None
        target=dict(id=1,weapons=None,element=None)
        r.active=dict(graph=SimpleNamespace(aim=lambda t:target),controller=None,event={})
        r.normal_by_unit={liter:10,crown:20,hood:100}
        r.choose_qte_controller()
        self.assertEqual(r.active['controller'],crown)
        r.char_states[crown].reloading_until=10
        r.choose_qte_controller()
        self.assertEqual(r.active['controller'],liter)
        r.char_states[liter].reloading_until=10
        self.assertIsNone(r.target(hood,'SR','철갑'))
        self.assertIsNone(r.active['controller'])

    def test_explosion_overlap_uses_capsule_distance_and_weapon_radius(self):
        from part_explosions import capsule_overlap,explosion_parts
        capsule=dict(a=[0,0,0],b=[0,2,0],radius=1)
        self.assertTrue(capsule_overlap([3,1,0],2,capsule))
        self.assertFalse(capsule_overlap([3.01,1,0],2,capsule))
        r,bm,(n,)=encounter('Rapi: Red Hood')
        explosion={'is_projectile_explosion':True}
        self.assertEqual(set(explosion_parts(r,n,'MG',explosion,None)),{'Weapon_02','Weapon_03'})
        self.assertEqual(explosion_parts(r,n,'MG',{},None),())
        self.assertEqual(explosion_parts(r,n,'MG',explosion,'Weapon_01'),())
        bm._activate(buff('explosion_range',value=100),n,0)
        self.assertEqual(set(explosion_parts(r,n,'MG',explosion,'Weapon_01')),{'Weapon_02','Weapon_03'})
        r.world.parts.self_destruct('Weapon_02',0)
        self.assertEqual(explosion_parts(r,n,'MG',explosion,None),('Weapon_03',))

    def test_stage_changes_cap_part_hp_without_healing_or_resurrecting(self):
        r, _, _ = encounter('Red Hood')
        core=r.world.parts.parts['Weapon_01']
        r.world.parts.damage('Weapon_01', 1e6, 0)
        r.world.parts.self_destruct('Weapon_02', 0)
        r.damage=118000001
        r.update_part_stage()
        self.assertEqual(core['max_hp'],136631662)
        self.assertEqual(core['hp'],136631662)
        self.assertEqual(r.world.parts.parts['Weapon_02']['hp'],0)
        self.assertFalse(r.world.parts.alive('Weapon_02'))
        r.world.parts.damage('Weapon_01',1e6,1)
        r.damage=742000001
        r.update_part_stage()
        self.assertEqual(core['max_hp'],600000000)
        self.assertEqual(core['hp'],135631662)

    def test_incoming_uses_identity_code_missing_from_build(self):
        r, bm, (water, iron) = encounter('Snow White: Heavy Arms', 'Red Hood')
        self.assertEqual(r.squad[water]['element_code'], '수냉')
        self.assertEqual(r.squad[iron]['element_code'], '철갑')
        for n in (water, iron):
            bm.state['hp'][n] = 1e9
            bm.state['base_stats'][n]['def'] = 0
        r.damage = 1e9  # original stage table enables elemental damage increase
        r.hurt_functions = lambda *a, **kw: []
        skill = dict(r.skills[5], ShotCount=1)
        for n in (water, iron):r.receive_attack(skill, {'_locked_targets':[n]})
        water_hit, iron_hit = r.incoming[-2:]
        self.assertAlmostEqual(water_hit['damage']/iron_hit['damage'],
                               r.stage_element_multiplier(), places=4)
        self.assertGreater(water_hit['damage'], iron_hit['damage'])

    def test_shield_is_separate_zero_defence_entity(self):
        r, bm, (n,) = encounter('Red Hood')
        bm.state['base_stats'][n]['hp'] = 1e9
        bm._activate(buff('shield_from_max_hp_pct', value=100), n, 0)
        bm._activate(buff('def_pct', value=1000), n, 0)
        bm._activate(buff('received_dmg_pct', value=-90), n, 0)
        skill = dict(r.skills[5], ShotCount=1, SkillValue01=1500, _damage_shots=5)
        r.receive_attack(skill, {'_locked_targets':[n]})
        # 48307 ATK * 3% * 25.0917. Original packet barrier minimum=36363;
        # owner DEF/reductions must not make the barrier last longer.
        self.assertEqual(r.incoming[-1]['absorbed'], 36363)
        self.assertEqual(r.incoming[-1]['blocked_by'], 'shield')

    def test_boolean_pierce_keeps_secondary_contacts_after_core_destruction(self):
        r, bm, (n,) = encounter('Red Hood')
        self.assertTrue(r.protection(n, 'pierce_enabled'))
        self.assertEqual(r.active_stat(n, 'pierce_enabled'), 0)
        r.world.parts.self_destruct('Weapon_01', 0)
        r.aim_controller = n
        self.assertIsNone(r.select_part(n))
        before = {p:r.world.parts.parts[p]['hp'] for p in ('Weapon_02','Weapon_03')}
        result = hit(r, damage=1000, caster=n, is_normal_atk=True)
        self.assertEqual(result, 3000)
        for p, hp in before.items():self.assertEqual(r.world.parts.parts[p]['hp'], hp-1000)

    def test_qte_leadin_keeps_physical_boss_part_contacts(self):
        from types import SimpleNamespace
        r,bm,(n,)=encounter('Red Hood')
        r.world.parts.self_destruct('Weapon_01',0)
        r.aim_controller=n
        r.active=dict(controller=n,index=0,graph=SimpleNamespace(aim=lambda t:None),
                      event=dict(id='qte',controller='auto'))
        before={p:r.world.parts.parts[p]['hp'] for p in ('Weapon_02','Weapon_03')}
        self.assertEqual(hit(r,damage=1000,caster=n,is_normal_atk=True),3000)
        for p,hp in before.items():self.assertEqual(r.world.parts.parts[p]['hp'],hp-1000)

    def test_cover_release_uses_previous_native_observation(self):
        r, bm, (n,) = encounter('Red Hood')
        r.cover_threats=[dict(start=23.966666619,end=25.499999952,
                             skill=r.skills[1],targets=[n],parts=[])]
        r._native_cover_observed_at=25.483333333
        r.time=25.5
        r.update_cover(r.time)
        self.assertIn(n,r.covered)
        r.covered=set()
        r._native_cover_observed_at=25.533333333
        r.time=25.55
        r.update_cover(r.time)
        self.assertNotIn(n,r.covered)


if __name__ == '__main__':unittest.main()
