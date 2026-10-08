"""Contract tests for native tactical receipt validation; no DLL is loaded."""

import copy
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from verify_tactical_trial import verify


LABELS = (
    'before_ownership', 'manual_ownership', 'selected_other_actor', 'pressed',
    'held_input_before_release', 'released', 'released_after_wait',
    'forced_cover_on', 'covered_after_wait', 'forced_cover_off',
    'repressed', 'released_again', 'restored_focus', 'restored_auto',
)


def native_shaped_rows():
    """Small coherent analogue of trial 112's observed command checkpoints."""
    states = {label: {
        'autoAim': False, 'forcedCover': False, 'focusedEntityId': 2,
        'inputType': 1, 'focusedStance': 0,
        'focusedUsedAmmoCount': 39, 'focusedShotHitNum': 39,
    } for label in LABELS}
    states['before_ownership'].update(autoAim=True, focusedEntityId=1)
    states['manual_ownership']['focusedEntityId'] = 1
    states['pressed'].update(inputType=2, focusedStance=2)
    states['held_input_before_release'].update(
        inputType=2, focusedStance=2,
        focusedUsedAmmoCount=49, focusedShotHitNum=49)
    for label in ('released', 'released_after_wait', 'forced_cover_on',
                  'covered_after_wait', 'forced_cover_off', 'repressed'):
        states[label].update(focusedUsedAmmoCount=49, focusedShotHitNum=49)
    squad = [{'entityId': entity_id, 'stance': 0, 'usedAmmoCount': 39}
             for entity_id in range(1, 6)]
    squad[1]['usedAmmoCount'] = 49
    for label in ('forced_cover_on', 'covered_after_wait'):
        states[label].update(forcedCover=True, squad=copy.deepcopy(squad))
    states['repressed'].update(inputType=2, focusedStance=2)
    states['released_again'].update(
        focusedUsedAmmoCount=50, focusedShotHitNum=50)
    states['restored_focus']['focusedEntityId'] = 1
    states['restored_auto'].update(
        autoAim=True, focusedEntityId=1,
        virtualPointer={'active': False, 'substitutions': 15, 'fault': None})
    return [{'status': 'original_tactical_input_checkpoint',
             'label': label, 'state': states[label]} for label in LABELS] + [
        {'status': 'original_terminal_result', 'originalResult': True}]


class TacticalReceiptContractTests(unittest.TestCase):
    def setUp(self):
        self.rows = native_shaped_rows()

    def state(self, label):
        return next(row['state'] for row in self.rows
                    if row.get('label') == label)

    def assert_rejected_for(self, message):
        report = verify(self.rows)
        self.assertFalse(report['passed'])
        self.assertIn(message, report['errors'])

    def test_coherent_native_shaped_sequence_passes(self):
        report = verify(self.rows)
        self.assertTrue(report['passed'], report['errors'])
        self.assertEqual((report['held_shots'], report['held_hits']), (10, 10))

    def test_spent_ammo_without_hits_rejects_lost_aim(self):
        # Trial 111 failure shape: shots spent while the original ray drifted.
        self.state('held_input_before_release')['focusedShotHitNum'] = 39
        self.assert_rejected_for('directed native shots hit nothing')

    def test_ammo_spent_after_release_is_rejected(self):
        self.state('released_after_wait')['focusedUsedAmmoCount'] = 50
        self.assert_rejected_for('controlled actor fired after release')

    def test_one_squad_member_firing_under_cover_is_rejected(self):
        self.state('covered_after_wait')['squad'][4]['usedAmmoCount'] += 1
        self.assert_rejected_for('squad fired or left cover during wait')

    def test_focus_drift_mid_sequence_is_rejected(self):
        self.state('held_input_before_release')['focusedEntityId'] = 3
        self.assert_rejected_for('controlled actor changed during sequence')

    def test_pointer_lease_left_active_is_rejected(self):
        self.state('restored_auto')['virtualPointer']['active'] = True
        self.assert_rejected_for('virtual input lease not exercised and released')

    def test_missing_original_terminal_is_rejected(self):
        self.rows.pop()
        self.assert_rejected_for('original full battle result absent')


if __name__ == '__main__':
    unittest.main()
