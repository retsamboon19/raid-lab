"""Cross-target cache correctness and live buff lookup regression cases."""
import math
import unittest

from calculator.buff_manager import ActiveBuff, BuffManager


class BuffLookupTests(unittest.TestCase):
    def setUp(self):
        self.bm = BuffManager([])

    def buff(self, stat, value, targets=('enemy-a',), expires=math.inf):
        return ActiveBuff({'stat': stat, 'fixed_value': value}, 'unit',
                          list(targets), 0.0, expires)

    def test_same_tick_different_enemy_does_not_reuse_debuff(self):
        self.bm._active = [self.buff('received_dmg_pct', 25.0)]
        affected = self.bm.get_buffs('unit', 'enemy-a', 1.0)
        unaffected = self.bm.get_buffs('unit', 'enemy-b', 1.0)
        self.assertEqual(affected['received_dmg'], 25.0)
        self.assertEqual(unaffected['received_dmg'], 0.0)
        self.assertIs(self.bm.get_buffs('unit', 'enemy-a', 1.0), affected)

    def test_lookup_order_live_values_and_invalidation(self):
        first = self.buff('atk_pct', 10.0)
        second = self.buff('atk_pct', 20.0)
        self.bm._active = [first, self.buff('def_pct', 30.0), second]
        self.assertEqual(self.bm._by_stat('atk_pct'), [first, second])
        self.assertEqual(self.bm._by_stat('missing'), [])
        first.stack = 2
        first.target_chars = ['enemy-b']
        self.assertEqual(self.bm._by_stat('atk_pct')[0].stack, 2)
        self.assertEqual(self.bm._by_stat('atk_pct')[0].target_chars, ['enemy-b'])
        self.bm._active.remove(first)
        self.bm._invalidate_buffs_cache()
        self.assertEqual(self.bm._by_stat('atk_pct'), [second])
        self.bm.reset()
        self.assertEqual(self.bm._by_stat('atk_pct'), [])

    def test_finite_buff_expiry_and_extension_keep_live_deadline(self):
        active = self.buff('received_dmg_pct', 25.0, expires=2.0)
        self.bm._active = [active]
        self.assertEqual(self.bm.get_buffs('unit', 'enemy-a', 1.0)['received_dmg'], 25.0)
        self.assertEqual(self.bm.get_buffs('unit', 'enemy-a', 2.0)['received_dmg'], 0.0)
        active.expires_at = 4.0
        self.assertEqual(self.bm.get_buffs('unit', 'enemy-a', 3.0)['received_dmg'], 25.0)
        self.assertEqual(self.bm.get_buffs('unit', 'enemy-a', 4.0)['received_dmg'], 0.0)

    def test_finite_stacking_buff_is_still_evaluated_live(self):
        active = self.buff('received_dmg_pct', 10.0, expires=5.0)
        active.effect['max_stack'] = 3
        self.bm._active = [active]
        self.assertEqual(self.bm.get_buffs('unit', 'enemy-a', 1.0)['received_dmg'], 10.0)
        active.stack = 3
        self.assertEqual(self.bm.get_buffs('unit', 'enemy-a', 2.0)['received_dmg'], 30.0)


if __name__ == '__main__':
    unittest.main()
