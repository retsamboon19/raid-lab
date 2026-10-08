"""Formation modes must agree with regular B1 versus re-entry support roles."""
import unittest
import core
from calculator.buff_manager import BuffManager


class AnisFormationTests(unittest.TestCase):
    def manager(self, partner):
        names = [core.NAME_MAP[n.lower()] for n in
                 ['Anis: Star', partner, 'Crown', 'Privaty', 'Helm']]
        squad = core.spec.build_squad(names, chars={n: core.default_build() for n in names},
                                      no_layer=set(names))
        return BuffManager(squad), names

    def test_regular_b1_enables_reentry(self):
        for partner in ['Little Mermaid', 'Liter', 'Rouge']:
            bm, names = self.manager(partner)
            self.assertTrue(bm._condition_ok(['has_burst1_ally'], names[0], 0))
            self.assertFalse(bm._condition_ok(['no_burst1_ally'], names[0], 0))

    def test_reentry_and_multistage_allies_preserve_offensive_mode(self):
        for partner in ['Tia', 'Avistar', 'Alice: Wonderland Bunny',
                        'Rupee: Winter Shopper', 'Red Hood', 'Rapi: Red Hood']:
            with self.subTest(partner=partner):
                bm, names = self.manager(partner)
                # Effective first-stage overrides must not change formation identity.
                bm.state['burst_stages'] = {n: '1' for n in names[:2]}
                self.assertTrue(bm._condition_ok(['no_burst1_ally'], names[0], 0))
                self.assertFalse(bm._condition_ok(['has_burst1_ally'], names[0], 0))

    def test_losing_regular_b1_allows_solo_mode_at_next_check(self):
        bm, names = self.manager('Little Mermaid')
        self.assertTrue(bm._condition_ok(['has_burst1_ally'], names[0], 0))
        bm.state['hp'] = {names[1]: 0}
        self.assertTrue(bm._condition_ok(['no_burst1_ally'], names[0], 10))


if __name__ == '__main__':
    unittest.main()
