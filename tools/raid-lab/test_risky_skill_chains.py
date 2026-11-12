"""Focused cross-effect checks for the high-risk roster review."""
import unittest
from test_complete_roster import manager
from calculator.buff_manager import char_effects
from calculator import roster_mechanics as kits


def setup(name, *allies):
    bm, names, states = manager(name, *allies)
    hits=[]
    bm.register_damage_handler(lambda effect,caster,t:hits.append((effect['name'],effect.get('stat'),t)))
    bm.battle_start(0)
    return bm,names,states,hits


class RiskySkillChains(unittest.TestCase):
    def test_neon_recharge_and_full_gauge_choose_distinct_branches(self):
        for start in (10,100):
            bm,(n,),_,_=setup('Neon: Vision Eye')
            bm.state['gauges'][n]['화력 게이지']=start
            bm.notify('burst_cast',1,n)
            if start==10:
                self.assertTrue(bm._has_self_state(n,'화력 충전'))
                self.assertFalse(bm._has_self_state(n,'초화력'))
                bm.notify('on_attack',2,n)
                self.assertEqual(bm.state['gauges'][n]['화력 게이지'],13)
            else:
                self.assertTrue(bm._has_self_state(n,'초화력'))
                self.assertFalse(bm._has_self_state(n,'화력 충전'))
                self.assertEqual(bm.state['gauges'][n]['화력 게이지'],0)

    def test_mint_alternates_dance_and_vocal_without_leaving_both_active(self):
        bm,(n,),_,_=setup('Mint')
        for i in range(1,5):
            bm.notify('burst_cast',i*30,n)
            self.assertEqual(bm._has_self_state(n,'무대 파트 : 댄스'),i%2==1)
            self.assertEqual(bm._has_self_state(n,'무대 파트 : 보컬'),i%2==0)

    def test_laplace_ultimate_transforms_only_on_fifth_charge_and_consumes_warmup(self):
        bm,(n,),_,_=setup('Laplace: Ultimate Hero')
        for i in range(1,5):
            bm.notify('full_charge_fire',i,n)
            self.assertIsNone(bm.get_weapon_change(n))
        bm.notify('full_charge_fire',5,n)
        self.assertIsNotNone(bm.get_weapon_change(n))
        self.assertFalse(bm._has_self_state(n,'예열'))

    def test_arcana_six_attack_cycle_grants_pellets_then_attack_and_resets(self):
        bm,(n,),_,_=setup('Arcana: Fortune Mate')
        bm.notify('burst_cast',1,n)
        for i in range(1,7):
            bm.notify('on_attack',1+i*.1,n)
            self.assertEqual(bm.state['gauges'][n]['공격 횟수'],i)
            self.assertEqual(bm._has_self_state(n,'행복한 기억'),i>=4)
            self.assertEqual(bm._has_self_state(n,'소중한 추억'),i>=6)
        bm.notify('full_burst_end',12,n)
        self.assertFalse(bm._has_self_state(n,'행복한 기억'))
        self.assertFalse(bm._has_self_state(n,'소중한 추억'))

    def test_elegg_thirteen_ghost_branch_does_not_fall_into_six_after_consumption(self):
        for ghosts,count,remaining in ((12,6,6),(13,13,4),(1,6,1),(0,6,0)):
            bm,(n,),_,hits=setup('Elegg: Boom and Shock')
            bm.state.setdefault('gauges',{}).setdefault(n,{})['유령']=ghosts
            bm.notify('burst_cast',1,n)
            self.assertEqual([stat for _,stat,_ in hits if stat.startswith('sequential_damage')],[f'sequential_damage:{count}'])
            self.assertEqual(bm.state['gauges'][n]['유령'],remaining)

    def test_label_shield_invulnerability_prevents_depletion(self):
        bm,(n,),_,_=setup('Label')
        before=bm.shield_amount(n)
        self.assertGreater(before,0)
        bm.notify('burst_cast',1,n)
        before=bm.shield_amount(n)
        kits.shield_hit(bm,n,before*10,2)
        self.assertEqual(bm.shield_amount(n),before)

    def test_phantom_mark_prevents_repeated_dagger_gain_on_same_marked_target(self):
        bm,(n,),_,_=setup('Phantom')
        bm.notify('hit_count',1,n)
        self.assertTrue(bm._has_target_state('예고장',caster=n,t=1))
        first=bm.ref_count(n,'괴도의 단검')
        for i in range(2,6):bm.notify('hit_count',i,n)
        self.assertEqual(bm.ref_count(n,'괴도의 단검'),first)

    def test_maxwell_overcurrent_increases_once_per_burst(self):
        bm,(n,),_,_=setup('Maxwell: Ordinary Mechanic')
        for i in range(1,6):
            bm.notify('burst_cast',i*40,n)
            self.assertEqual(bm.state['gauges'][n]['과전류'],i)
            self.assertIsNotNone(bm.get_weapon_change(n))

    def test_velvet_spends_only_available_shared_ammunition(self):
        bm,(n,),_,_=setup('Velvet')
        self.assertEqual(bm.state['gauges'][n]['탄환 주머니'],6000)
        bm.notify('full_charge_fire',1,n)
        self.assertEqual(bm.state['gauges'][n]['탄환 주머니'],5900)
        bm.state['full_burst']=True
        bm.notify('full_burst_start',2,n)
        bm.state['gauges'][n]['탄환 주머니']=125
        bm.notify('full_charge_fire',3,n)
        self.assertEqual(bm.state['gauges'][n]['탄환 주머니'],0)
        self.assertTrue(bm._has_self_state(n,'사랑의 탄환 2'))
        bm.notify('burst_enter:2',4,n)
        self.assertEqual(bm.state['gauges'][n]['탄환 주머니'],6000)

    def test_crystal_wave_manual_reload_toggle_and_natural_reload_gate(self):
        bm,(n,),_,_=setup('Cinderella: Crystal Wave')
        bm.notify('event:full_reload',1,n)
        self.assertIsNone(bm.get_weapon_change(n))
        bm.notify('event:full_reload',4,n)
        self.assertIsNotNone(bm.get_weapon_change(n))
        self.assertTrue(bm._has_self_state(n,'디스트로이'))
        self.assertFalse(bm._has_self_state(n,'핀 포인트'))
        bm.notify('last_bullet_fire',5,n)
        bm.notify('event:full_reload',8,n)
        self.assertIsNotNone(bm.get_weapon_change(n))
        bm.notify('event:full_reload',11,n)
        self.assertIsNone(bm.get_weapon_change(n))
        self.assertTrue(bm._has_self_state(n,'핀 포인트'))
        self.assertFalse(bm._has_self_state(n,'디스트로이'))

    def test_milk_hold_penalty_once_and_burst_clears_and_blocks_it(self):
        bm,(n,),_,hits=setup('Milk: Blooming Bunny')
        bm.notify('charge_hold:0.5',1,n)
        self.assertTrue(bm._has_self_state(n,'부끄러움'))
        self.assertTrue(bm._has_self_state(n,'부끄러움 4'))
        count=len(hits)
        bm.notify('charge_hold:0.5',2,n)
        self.assertEqual(len(hits),count)
        bm.notify('event:full_reload',4,n)
        self.assertFalse(bm._has_self_state(n,'부끄러움 4'))
        self.assertTrue(bm._has_self_state(n,'부끄러움'))
        bm.notify('burst_cast',5,n)
        self.assertFalse(bm._has_self_state(n,'부끄러움'))
        self.assertFalse(bm._has_self_state(n,'부끄러움 6'))
        bm.notify('charge_hold:0.5',6,n)
        self.assertFalse(bm._has_self_state(n,'부끄러움'))

    def test_milk_original_forty_second_state_allows_reentry_after_expiry(self):
        bm,(n,),_,_=setup('Milk: Blooming Bunny')
        bm.notify('charge_hold:0.5',1,n)
        self.assertTrue(bm._has_self_state(n,'부끄러움 6'))
        bm.tick(40.99)
        self.assertTrue(bm._has_self_state(n,'부끄러움'))
        bm.tick(41)
        self.assertFalse(bm._has_self_state(n,'부끄러움'))
        self.assertFalse(bm._has_self_state(n,'부끄러움 4'))
        bm.notify('charge_hold:0.5',42,n)
        self.assertTrue(bm._has_self_state(n,'부끄러움'))

    def test_ark_first_burst_transforms_then_consumes_without_immediate_drain(self):
        bm,(n,),_,_=setup('Ark Ranger Black')
        bm.notify('burst_cast',1,n)
        self.assertTrue(bm._has_self_state(n,'변신'))
        self.assertEqual(bm.state['gauges'][n]['배터리'],50)
        bm.tick(1)
        self.assertEqual(bm.state['gauges'][n]['배터리'],50)

    def test_marciana_whistle_enemy_count_boundaries(self):
        from types import SimpleNamespace
        bm,(n,),_,hits=setup('Marciana: Marine Study')
        self.assertEqual(bm.ref_count(n,'휘슬'),5)
        bm.state['encounter_runtime']=SimpleNamespace(select_enemy_effect_targets=lambda *a:[],living_enemy_count=lambda:3)
        bm.tick(5)
        self.assertEqual(bm.ref_count(n,'휘슬'),6)
        self.assertFalse(any(x[0]=='펭군 긴급 출동' for x in hits))
        bm.state['encounter_runtime'].living_enemy_count=lambda:6
        bm.tick(6)
        self.assertEqual(bm.ref_count(n,'휘슬'),5)
        self.assertTrue(any(x[0]=='펭군 긴급 출동' for x in hits))

    def test_viper_stealth_breaks_on_received_hit(self):
        bm,(n,),_,_=setup('Viper')
        bm.notify('full_burst_start',1,n)
        self.assertTrue(bm._has_self_state(n,'애교'))
        bm.notify('received_hit',2,n)
        self.assertFalse(bm._has_self_state(n,'애교'))

    def test_exia_fifth_last_bullet_unlocks_bonus_burst(self):
        for stacks in (4,5):
            bm,(n,),_,hits=setup('Exia')
            for i in range(stacks):bm.notify('last_bullet',i+1,n)
            bm.notify('burst_cast',6,n)
            self.assertEqual(any(x[0]=='원사이드 프로토콜 [3]' for x in hits),stacks==5)

    def test_anis_auto_weapon_obeys_original_first_delay(self):
        bm,(n,),_,hits=setup('Anis: Star')
        bm.notify('burst_cast',1,n)
        bm.tick(1.19)
        self.assertFalse(any(x[0]=='슈팅 스타1' for x in hits))
        bm.tick(1.2)
        self.assertTrue(any(x[0]=='슈팅 스타1' for x in hits))

    def test_sugar_shotgun_ammo_buff_excludes_other_weapon(self):
        bm,(n,ally),_,_=setup('Sugar','Crow')
        bm.notify('full_burst_start',1,n)
        rows=bm._by_name('느와르 센서 3')
        self.assertEqual(len(rows),1)
        self.assertEqual(rows[0].target_chars,[n])
        for i in range(1,5):bm.notify('event:cover_hit',i,n)
        self.assertFalse(bm._has_self_state(n,'블랙 타이푼'))
        bm.notify('event:cover_hit',5,n)
        self.assertTrue(bm._has_self_state(n,'블랙 타이푼'))

    def test_diesel_hundred_hit_boundary_and_fullburst_heal_gate(self):
        bm,(n,),_,_=setup('Diesel')
        for i in range(1,100):bm.notify('hit_count',i*.01,n)
        self.assertIsNone(bm.ref_count(n,'딸기 사탕'))
        bm.notify('hit_count',1,n)
        self.assertEqual(bm.ref_count(n,'딸기 사탕'),1)
        bm.state['hp'][n]=5000;bm.sync_hp(n)
        bm.notify('received_hit',2,n)
        self.assertEqual(bm.state['hp'][n],5000)
        bm.state['full_burst']=True
        bm.notify('received_hit',3,n)
        self.assertGreater(bm.state['hp'][n],5000)

    def test_zwei_fifth_attack_heals_existing_cover_but_does_not_revive(self):
        from types import SimpleNamespace
        bm,(n,ally),_,_=setup('Zwei','Crow')
        runtime=SimpleNamespace(cover={n:500.,ally:0.},cover_max={n:1000.,ally:1000.})
        bm.state['encounter_runtime']=runtime
        for i in range(1,5):bm.notify('on_attack',i,n)
        self.assertEqual(runtime.cover[n],500)
        bm.notify('on_attack',5,n)
        self.assertGreater(runtime.cover[n],500)
        self.assertEqual(runtime.cover[ally],0)
        bm.notify('burst_cast',6,n)
        self.assertIsNotNone(bm.get_weapon_change(n))
        self.assertTrue(bm._has_self_state(n,'과충전 공식 2'))

    def test_privaty_stun_extra_hit_and_expiry(self):
        bm,(n,),_,hits=setup('Privaty')
        bm.notify('last_bullet',1,n)
        self.assertFalse(any(x[0]=='LD 어설트 3' for x in hits))
        bm.notify('burst_cast',2,n)
        bm.notify('last_bullet',3,n)
        self.assertEqual(sum(x[0]=='LD 어설트 3' for x in hits),1)
        bm.tick(5)
        bm.notify('last_bullet',6,n)
        self.assertEqual(sum(x[0]=='LD 어설트 3' for x in hits),1)


if __name__=='__main__':unittest.main()
