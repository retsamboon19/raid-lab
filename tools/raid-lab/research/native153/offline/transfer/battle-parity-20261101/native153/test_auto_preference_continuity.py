"""No registry/native operations; reject changes to established private inputs."""
import copy
import unittest
from check_auto_preferences_continuity153 import compare_continuity
from test_auto_preference_witness import rows
from check_auto_preferences153 import NAMES


class ContinuityContracts(unittest.TestCase):
    def test_private_one_pair_is_accepted(self):self.assertEqual(compare_continuity(rows(True),rows(True)),[])
    def test_private_absence_not_reused(self):self.assertTrue(compare_continuity(rows(True),rows(False)))
    def test_either_normal_or_private_change_rejected(self):
        for scope in ('normal','private'):
            after=rows(True);after[scope]['values'][NAMES[0]]['value']=0
            self.assertEqual(compare_continuity(rows(True),after),[scope+'_preferences_differ_from_established_private_inputs'])


if __name__=='__main__':unittest.main()
