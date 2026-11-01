"""Captured field accounting/source contracts, without native execution."""
import json
from pathlib import Path
import unittest

HERE = Path(__file__).resolve().parent


class CapturedPracticeFixtureContracts(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.data = json.loads((HERE / 'run1/native-fixture-input.json').read_text())
        cls.fields = {field['name']: field for field in cls.data['fields']}

    def test_all_original_nonstatic_fields_are_explicitly_accounted(self):
        self.assertEqual(len(self.fields), 61)
        metadata = json.loads((HERE.parents[1] / 'metadata/current153-run3/mechanics-metadata.json').read_text())
        native = next(c for c in metadata['classes'] if c['class'] == 'NK.Spot.Data.NKSpotDataTransporter')
        self.assertEqual(set(self.fields), {f['name'] for f in native['fields'] if not f['flags'] & 0x10})
        self.assertEqual(self.data['transporterValueSize'], 376)

    def test_observed_transporter_zero_process_is_not_replaced_by_wave_process_nine(self):
        self.assertEqual(self.fields['<ProcessType>k__BackingField']['value'], 0)
        self.assertEqual(self.fields['TeamType']['value'], 24)
        self.assertEqual(self.fields['<TimeLimit>k__BackingField']['value'], 90)
        self.assertEqual(self.fields['_waveId']['value'], 6801001)

    def test_callbacks_are_fresh_required_bindings_and_labels_are_original(self):
        self.assertEqual(self.data['requiredFreshOriginalNativeOwnerBindings'], [
            'OnSpotPauseFirstButton', 'OnSpotPauseSecondButton', 'OnBattleFinish', 'OnBattleRetry'])
        self.assertEqual(self.fields['OnSpotPauseFirstButton']['semanticTuple']['Item1'], 'Leave Shooting Range')
        self.assertEqual(self.fields['OnSpotPauseSecondButton']['semanticTuple']['Item1'], 'Retry')
        for name in self.data['requiredFreshOriginalNativeOwnerBindings']:
            self.assertNotIn('rawHex', self.fields[name])

    def test_excluded_multiplayer_values_require_original_zero_payload_proof(self):
        for name, field in self.fields.items():
            if name.startswith('<Multiplay'):
                self.assertTrue(field['zeroValueProvenFromCapturedRawPayload'])
        self.assertEqual(self.fields['<MultiplayMatchType>k__BackingField']['kind'], 'zeroValueType')
        self.assertEqual(self.fields['OnSpotPauseThirdButton']['rawHex'], '00' * 24)

    def test_original_team_context_and_warmup_source_remain_exact(self):
        self.assertIsNone(self.data['teamConversion']['buffInfos'])
        self.assertEqual(self.data['teamConversion']['statIncrease'], 0)
        self.assertEqual(self.data['sourceOnStart']['sequence'], 18)

    def test_resolver_uses_original_async_group_then_exact_leaf_lookup(self):
        source = (HERE / 'practice_wave_resolver.js').read_text()
        for rva in ['0x0517cc50', '0x0517ffb0', '0x05180500', '0x05180c90']:
            self.assertIn(rva, source)
        self.assertNotIn('FindById_Warning', source)
        self.assertNotIn('field(\'_tables\').value =', source)
        self.assertIn('groupAndLeafObjectIdentical:true', source)

    def test_fixture_is_readback_only_and_host_boundaries_are_not_exact_ui_replay(self):
        source = (HERE / 'prepare_practice_fixture.js').read_text()
        self.assertIn('il2cpp_field_set_value_object', source)
        self.assertIn("game.getExportByName('il2cpp_field_set_value')", source)
        self.assertIn('if(type.isValueType)setFieldValue(box.handle,field.handle,argument)', source)
        self.assertIn("status:'captured_practice_fixture_field_mismatch'", source)
        self.assertIn('receipt.mutatesCombatState===false', source)
        self.assertIn('transporterExactReplay:!adapters', source)
        self.assertNotIn('field("DataTransporter").value =', source)
        self.assertNotIn('set_captureDeltaTime', source)
        self.assertIn('staticTransporterInstalled:false,battleStarted:false', source)


if __name__ == '__main__':
    unittest.main()
