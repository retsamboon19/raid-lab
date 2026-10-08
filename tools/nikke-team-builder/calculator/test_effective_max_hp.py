"""HP-size index retains active-buff order and follows active-list invalidation."""
import unittest
from types import SimpleNamespace

from calculator.buff_manager import BuffManager


def buff(stat, value, targets=('target',), caster='source'):
    return SimpleNamespace(effect={'stat': stat, 'value': value},
                           target_chars=list(targets), caster=caster)


class EffectiveMaxHpIndexTests(unittest.TestCase):
    def setUp(self):
        self.bm = object.__new__(BuffManager)
        self.bm.state = {'base_stats': {'target': {'hp': 100.0},
                                        'source': {'hp': 200.0}}}
        self.bm._cur_t = 0.0
        self.bm._active = [
            buff('atk_pct', 999.0),
            buff('max_hp_pct', 10.0),
            buff('hp_caster_based_pct', 5.0),
            buff('max_hp_only_pct', 20.0),
        ]
        self.bm._get_value = lambda effect, active, recipient: effect['value']
        self.bm._hp_size_active = None
        self.bm._stat_index = None
        self.bm._name_index_cache = {}
        self.bm._plan_cache = {}
        self.bm._buffs_cache = {}
        self.bm._stunned_cache = {}
        self.bm._cache_version = 0

    def test_hp_size_changes_after_buff_invalidation(self):
        # 100 * (1 + (10 + 20)/100) + 200 * 5/100
        self.assertEqual(self.bm.effective_max_hp('target'), 140.0)
        self.assertEqual(self.bm.effective_max_hp('target'), 140.0)
        self.bm._active.append(buff('hp_only_caster_based_pct', 2.0))
        self.bm._invalidate_buffs_cache()
        self.assertEqual(self.bm.effective_max_hp('target'), 144.0)
        self.bm._active.pop()
        self.bm._invalidate_buffs_cache()
        self.assertEqual(self.bm.effective_max_hp('target'), 140.0)

    def test_unrelated_buff_and_other_recipient_do_not_change_hp(self):
        self.bm._active.append(buff('max_hp_pct', 100.0, targets=('other',)))
        self.assertEqual(self.bm.effective_max_hp('target'), 140.0)
        self.assertEqual(self.bm.effective_max_hp('source'), 200.0)


if __name__ == '__main__':
    unittest.main()
