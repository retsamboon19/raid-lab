"""Behavioral checks for roster-wide support, including incoming combat."""
import copy
import unittest
from types import SimpleNamespace

import core
from calculator.buff_manager import BuffManager, char_effects
from calculator import roster_mechanics as kits
from calculator.timeline import CharState, _register_instant_handlers, _restore_hp


def manager(*names, level=10, favorite=0):
    ids = [core.NAME_MAP[n.casefold()] for n in names]
    build = core.default_build()
    build.update(skill_levels=dict.fromkeys(('1', '2', '3'), level), favorite_stage=favorite)
    chars = [core.spec.build_char(n, build, no_layer=True) for n in ids]
    bases = {n: {'hp': 10000.0 * (i + 1), 'atk': 1000.0 * (i + 1), 'def': 100.0}
             for i, n in enumerate(ids)}
    state = {'hp': {n: b['hp'] for n, b in bases.items()}, 'hp_pct': dict.fromkeys(ids, 100.0),
             'base_stats': bases, 'rng_expected': True, 'burst_gauge_charging': True}
    bm = BuffManager(chars, state)
    cs = {c['name']: CharState(c, bases[c['name']]['atk'], '철갑') for c in chars}
    ctrl = SimpleNamespace(cooldowns={}, next_ready={}, _cooldowns={})
    _register_instant_handlers(bm, cs, ctrl)
    return bm, ids, cs


def buff(stat, target='self', value=10.0, **kw):
    return dict(type='buff', source='스킬1', name=stat, stat=stat, fixed_value=value,
                target=target, polarity='beneficial', max_stack=1, duration=10,
                trigger={'timing': ['battle_start'], 'condition': []}, **kw)


class CompleteRosterTests(unittest.TestCase):
    def test_every_real_character_has_all_three_base_skills(self):
        self.assertEqual(len(core.CATALOG), 202)
        for c in core.CATALOG:
            with self.subTest(character=c['name']):
                self.assertTrue(c['supported'])
                self.assertEqual({e['source'] for e in char_effects(c['id'], 0)}, {'스킬1', '스킬2', '스킬3'})

    def test_compiler_is_repeatable_and_uses_all_ten_source_levels(self):
        from runner import complete_roster as rules
        rules.KITS.clear(); rules.build()
        for name, effects in rules.KITS.items():
            self.assertEqual(effects, core.SKILLS[name], name)
            for e in effects:
                for key in ('values', 'duration_values'):
                    if key in e:
                        self.assertEqual(set(e[key]), {str(i) for i in range(1, 11)}, (name, e['name']))

    def test_shared_shield_protects_ally_and_depletes_one_pool(self):
        bm, (poli, ally), _ = manager('Poli', 'Crow')
        bm._activate(buff('shared_shield_from_max_hp_pct', value=10), poli, 0)
        self.assertEqual(kits.shield_hit(bm, ally, 400, 0), ('shield', 400))
        self.assertEqual(bm.shield_amount(poli), 600)
        self.assertEqual(bm.shield_amount(ally), 600)
        self.assertEqual(kits.shield_hit(bm, poli, 800, 0), ('shield', 600))
        self.assertFalse(bm.has_shield(ally))
        self.assertEqual(kits.shield_hit(bm, ally, 100, 0), (None, 0))

    def test_enemy_attack_debuff_does_not_reduce_player_attack(self):
        import unit_combat
        bm, (crow,), _ = manager('Crow')
        bm._activate(buff('atk_pct', target='all_enemies', value=-20), crow, 0)
        r = SimpleNamespace(bm=bm, time=0)
        self.assertEqual(unit_combat.enemy_attack(r, 1000), 800)
        self.assertEqual(bm.get_buffs(crow, '__enemy__', 0)['atk_pct'], 0)

    def test_refreshing_max_hp_does_not_repeatedly_heal(self):
        bm, (noise, ally), _ = manager('Noise', 'Crow')
        effect = buff('max_hp_pct', target='all_allies', value=20)
        bm._activate(effect, noise, 0)
        self.assertEqual(bm.state['hp'][ally], 24000)
        kits.hurt_hp(bm, ally, 1000, 1)
        bm._activate(effect, noise, 2)
        self.assertEqual(bm.state['hp'][ally], 23000)

    def test_received_hit_count_and_maiden_retaliation(self):
        bm, (maiden,), _ = manager('Maiden')
        before = bm.get_buffs(maiden, '__enemy__', 0)['atk_pct']
        for i in range(20): bm.notify('received_hit', i / 100, maiden)
        self.assertGreater(bm.get_buffs(maiden, '__enemy__', .2)['atk_pct'], before)

    def test_rapunzel_revives_only_fallen_units(self):
        bm, (rapunzel, ally), _ = manager('Rapunzel', 'Crow')
        bm.state['hp'][ally] = 0; bm.sync_hp(ally)
        eff = next(e for e in char_effects(rapunzel, 0) if e.get('stat') == 'revive_hp_pct')
        bm._activate(eff, rapunzel, 1)
        self.assertGreater(bm.state['hp'][ally], 0)
        self.assertEqual(len(bm.state['revives']), 1)
        bm._activate(eff, rapunzel, 2)
        self.assertEqual(len(bm.state['revives']), 1)

    def test_kilo_missing_shield_branch_precedes_recoating(self):
        bm, (kilo,), _ = manager('Kilo')
        bm.notify('burst_cast', 0, kilo)
        self.assertAlmostEqual(bm.effective_max_hp(kilo), 14800)
        self.assertAlmostEqual(bm.shield_amount(kilo), 14800 * .2112 * 1.1775)
        self.assertFalse(list(kits.active(bm, kilo, 'next_shield_hp_pct')))

    def test_damage_share_conserves_damage_without_recursing(self):
        bm, (jackal, ally), _ = manager('Jackal', 'Crow')
        bm._activate(buff('damage_share', target='all_allies'), jackal, 0)
        kits.hurt_hp(bm, jackal, 1000, 1)
        self.assertEqual(bm.state['hp'][jackal], 9500)
        self.assertEqual(bm.state['hp'][ally], 19500)

    def test_biscuit_protects_defender_at_health_threshold(self):
        bm, (biscuit, ally), _ = manager('Biscuit', 'Ludmilla')
        kits.hurt_hp(bm, ally, 11000, 0)
        self.assertTrue(list(kits.active(bm, ally, 'invincible', 0)))
        before = bm.state['hp'][ally]
        kits.hurt_hp(bm, ally, 100000, 1)
        self.assertEqual(bm.state['hp'][ally], before)

    def test_tactical_squad_target_and_conditional_state(self):
        bm, (emma, eunhwa, other), _ = manager('Emma: Tactical Upgrade', 'Eunhwa: Tactical Upgrade', 'Crow')
        bm.battle_start(0)
        self.assertEqual(set(bm._resolve_target('allies_squad', emma)), {emma, eunhwa})
        bm2, (alone,), _ = manager('Emma: Tactical Upgrade')
        bm2.battle_start(0)
        self.assertFalse(bm2._has_self_state(alone, '노출 발동 불가'))

    def test_crust_has_hold_threshold(self):
        bm, (crust,), _ = manager('Crust')
        self.assertIn((1.0, '1'), bm.charge_hold_thresholds(crust))

    def test_eh_weapon_ammo_scales_with_crafted_magazines(self):
        bm, (eh,), cs = manager('E.H.')
        bm.state.setdefault('gauges', {})[eh] = {'사제 탄창': 4}
        wc = next(e for e in char_effects(eh, 0) if e['type'] == 'weapon_change')
        bm._activate(wc, eh, 0)
        self.assertEqual(cs[eh]._full_ammo(bm, 0), 4)

    def test_nayuta_all_ammo_displays_999_but_keeps_buffed_true_magazine(self):
        bm, (nayuta,), states = manager('Nayuta')
        state = states[nayuta]
        bm._activate(buff('max_ammo_pct', value=-50.66), nayuta, 0)
        self.assertEqual(state.native_ammo_state(bm, 0)['true_max_ammo'], 59)
        weapon_change = next(e for e in char_effects(nayuta, 0)
                             if e['type'] == 'weapon_change' and e['max_ammo'] == -1)
        all_ammo = next(e for e in char_effects(nayuta, 0)
                        if e.get('stat') == 'infinite_ammo')
        bm._activate(weapon_change, nayuta, 0)
        bm._activate(all_ammo, nayuta, 0)
        self.assertEqual(state.native_ammo_state(bm, 0), {
            'current_ammo': 999, 'max_ammo': 999, 'true_max_ammo': 493})
        # TrueMaxAmmo tracks live buffs even while AllAmmo masks the display.
        self.assertEqual(state.native_ammo_state(bm, 11)['true_max_ammo'], 999)

    def test_delta_ifak_stores_healing_to_atk_cap_and_discharges_on_expiry(self):
        bm, (delta, ally), _ = manager('Delta: Ninja Thief', 'Crow')
        effects = char_effects(delta, 0)
        store = next(e for e in effects if e.get('stat') == 'heal_overcharge_store_atk_pct')
        boost = next(e for e in effects if e.get('stat') == 'accumulate_max_scale_pct')
        bm._activate(store, delta, 0)
        bm._activate(boost, delta, 0)
        bm.state['hp'][ally] = 15000
        bm.sync_hp(ally)
        _restore_hp(bm, delta, 1000, 1, delta)
        _restore_hp(bm, delta, 1000, 2, delta)
        cap = 1000 * 1.6528 * 1.2013
        self.assertAlmostEqual(bm.state['stored_healing_atk'][delta]['인법 IFAK'], cap)
        # The charge belongs to IFAK, not the excess-HP pool consumed on hit.
        self.assertNotIn(delta, bm.state.get('stored_healing', {}))
        kits.hurt_hp(bm, delta, 1000, 3)
        self.assertAlmostEqual(bm.state['stored_healing_atk'][delta]['인법 IFAK'], cap)
        bm.tick(4)
        self.assertAlmostEqual(bm.state['hp'][ally], 15000 + cap)
        self.assertEqual(bm.state['hp'][delta], bm.effective_max_hp(delta))
        self.assertNotIn(delta, bm.state['stored_healing_atk'])

    def test_delta_ifak_every_four_seconds_discharge_precedes_next_window(self):
        bm, (delta, ally), _ = manager('Delta: Ninja Thief', 'Crown')
        bm.battle_start(0)
        bm.state['hp'][ally] = 15000
        bm.sync_hp(ally)
        bm.tick(4)
        self.assertTrue(list(kits.active(bm, delta, 'heal_overcharge_store_atk_pct', 4)))
        _restore_hp(bm, delta, 500, 5, delta)
        bm.tick(8)
        self.assertEqual(bm.state['hp'][ally], 15500)
        self.assertNotIn(delta, bm.state.get('stored_healing_atk', {}))
        self.assertTrue(list(kits.active(bm, delta, 'heal_overcharge_store_atk_pct', 8)))
        _restore_hp(bm, delta, 200, 9, delta)
        bm.tick(12)
        self.assertEqual(bm.state['hp'][ally], 15700)

    def test_winter_guillotine_levels_up_at_each_experience_boundary(self):
        bm, (unit,), _ = manager('Guillotine: Winter Slayer')
        bm.battle_start(0)
        for i in range(60): bm.notify('hit_count', .01*i, unit, core_frac=0)
        self.assertEqual(bm.state['gauges'][unit]['경험치'], 10)
        self.assertEqual(bm.state['gauges'][unit]['용사 레벨'], 2)
        for i in range(60): bm.notify('hit_count', 1+.01*i, unit, core_frac=1)
        self.assertEqual(bm.state['gauges'][unit]['경험치'], 10)
        for i in range(30): bm.notify('core_hit', 2+.01*i, unit)
        self.assertEqual(bm.state['gauges'][unit]['용사 레벨'], 3)

    def test_damage_reduction_is_a_buff_and_survives_cleansing(self):
        bm, (noah, ally), _ = manager('Noah', 'Crow')
        effect = next(e for e in char_effects(noah, 0) if e.get('stat') == 'received_dmg_pct')
        self.assertEqual(effect['polarity'], 'beneficial')
        bm._activate(effect, noah, 0)
        before = kits.total(bm, ally, 'received_dmg_pct', 0)
        self.assertLess(before, 0)
        bm._dispatch_instant(dict(source='스킬1', type='instant', stat='debuff_cleanse', target='all_allies'), noah, 0)
        self.assertEqual(kits.total(bm, ally, 'received_dmg_pct', 0), before)

    def test_dorothy_accumulates_team_damage_and_detonates_once(self):
        bm, (dorothy, ally), _ = manager('Dorothy', 'Crow')
        effect = next(e for e in char_effects(dorothy, 0) if e.get('stat') == 'damage_accumulate')
        detonations = []
        bm.register_damage_handler(lambda e,c,t: detonations.append(e['fixed_value']))
        bm._activate(effect, dorothy, 0)
        kits.record_damage(bm, ally, 1200, 1, {'is_normal_atk': True})
        kits.record_damage(bm, dorothy, 800, 2, {'is_normal_atk': True})
        kits.tick(bm, 10); kits.tick(bm, 11)
        self.assertEqual(detonations, [2000])

    def test_ally_stack_reduction_reaches_the_actual_recipients(self):
        bm, (diesel, ally), _ = manager('Diesel: Winter Sweets', 'Crow')
        bm.notify('event:part_destroy', 0, diesel)
        stack = next(a for a in bm._active if a.effect.get('name') == '음소거')
        self.assertEqual(stack.stack, 1)
        eff = dict(source='스킬3',type='instant',stat='buff_stack_remove',
                   target='all_allies',target_effect='음소거',fixed_value=1)
        bm._dispatch_instant(eff, diesel, 1)
        self.assertFalse(bm._has_self_state(ally, '음소거'))

    def test_consuming_stacks_updates_the_reference_count(self):
        bm, (soda,), _ = manager('Soda: Twinkling Bunny')
        effect = next(e for e in char_effects(soda, 0) if e.get('name') == '골든 칩')
        for i in range(20): bm._activate(effect, soda, i/100)
        consume = next(e for e in char_effects(soda, 0) if e.get('stat') == 'buff_stack_remove')
        bm._dispatch_instant(consume, soda, 1)
        self.assertEqual(bm.ref_count(soda, '골든 칩'), 3)
        bm._dispatch_instant(consume, soda, 2)
        self.assertFalse(bm._has_self_state(soda, '골든 칩'))


if __name__ == '__main__':
    unittest.main()
