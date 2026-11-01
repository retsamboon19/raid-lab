"""Input separation/layout contracts only; never runs or emulates combat."""
import importlib.util
import json
from pathlib import Path
import unittest

HERE = Path(__file__).resolve().parent
SPEC = importlib.util.spec_from_file_location('snapshot_inputs', HERE / 'extract_snapshot_inputs.py')
subject = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(subject)


class CapturedSnapshotInputContracts(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.input = json.loads((HERE / 'run1/native-replay-input.json').read_text())
        cls.expected = json.loads((HERE / 'run1/native-conversion-expected.json').read_text())

    def test_only_source_snapshot_payloads_are_constructor_inputs(self):
        self.assertEqual([c['slot'] for c in self.input['characters']], [1, 2, 3, 4, 5])
        for member in self.input['characters']:
            self.assertEqual(len(bytes.fromhex(member['characterStatDataRawHex'])), 240)
            self.assertEqual(len(bytes.fromhex(member['levelObscuredIntRawHex'])), 20)
            self.assertEqual(len(bytes.fromhex(member['characterInfoRawHex'])), 16)
            self.assertNotIn('stats', member)
            self.assertNotIn('level', member)
            self.assertNotIn('nativeConversion', member)
        self.assertNotIn('score', self.input)

    def test_captured_cube_subtype_and_empty_cube_sentinel_are_preserved(self):
        for member in self.input['characters']:
            self.assertEqual([e['subType'] for e in member['equipmentAndCube']], [1, 2, 3, 4, 18])
        cube = self.input['characters'][1]['equipmentAndCube'][-1]
        self.assertEqual((cube['Isn'], cube['Tid'], cube['Level']), ('0', 0, 0))

    def test_favorite_overrides_come_from_original_snapshot_static_ids(self):
        skills = self.input['characters'][2]['skills']
        self.assertTrue(all(skill['favoriteOverride'] for skill in skills))
        self.assertEqual([skill['skillInfoTableId'] for skill in skills], [2101151, 2101251, 1101351])
        self.assertTrue(all(not skill['favoriteOverride'] for skill in self.input['characters'][0]['skills']))

    def test_expected_native_values_are_separate_hash_bound_verification(self):
        self.assertEqual(self.expected['captureSha256'], self.input['captureSha256'])
        self.assertFalse(self.expected['battleOutputsIncluded'])
        self.assertEqual([c['sourceRow']['sequence'] for c in self.expected['characters']], [5, 7, 9, 11, 13])
        self.assertEqual([c['sourceRow']['sequence'] for c in self.input['characters']], [4, 6, 8, 10, 12])
        self.assertIn('stats', self.expected['characters'][0]['nativeConversion'])

    def test_raw_payload_malformed_sizes_fail_closed(self):
        for node, size in [({'$valueSize': 239, 'rawHex': '00' * 240}, 240),
                           ({'$valueSize': 240, 'rawHex': '00'}, 240)]:
            with self.assertRaises(ValueError):
                subject.raw(node, size, 'TEST_ONLY_BAD_LAYOUT')

    def test_replayer_does_not_install_or_start_combat_or_settings(self):
        source = (HERE / 'reconstruct_snapshots.js').read_text()
        for prohibited in ['set_RandomSeed', 'UpdateTick(', 'set_captureDeltaTime',
                           'DataTransporter").value', 'expectedNative.stats[', 'SetCharacterLevel']:
            self.assertNotIn(prohibited, source)
        self.assertIn('0x008c7ed0', source)  # Exact original native level decoder.


if __name__ == '__main__':
    unittest.main()
