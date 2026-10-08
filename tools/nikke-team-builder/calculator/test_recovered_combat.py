"""Compare recovered arithmetic with recorded original-DLL outputs."""
import json
from pathlib import Path
import struct
import unittest

from calculator.recovered_combat import (
    CLIENT_SHA256, RATE_NAMES, apply_target_reduction, calculate_damage,
    calculate_damage_rates, double_to_long, normal_base_damage,
)
from calculator.damage import calc_damage


class RecoveredDamageTests(unittest.TestCase):
    def test_original_complete_hit_packet_controls(self):
        data = json.loads((Path(__file__).parent / 'fixtures' /
                           'client-2df7134a-packets.json').read_text())['report']
        caster = next(e['direct_primitives'] for e in data['events']
                      if e['phase'] == 'original_caster_packet')
        for row in data['events']:
            if row['phase'] != 'original_packet_control':
                continue
            with self.subTest(case=row['case']):
                target = row['effective_target_fields']
                rates = row['damage_rates']
                base = normal_base_damage(
                    int(caster['Attack']), int(target['Defence']),
                    rates['DamageRatio'], rates['StatDamageRatio'],
                    rates['DefIgnoreRatio'], rates['DefenceRatioRate'])
                self.assertEqual(base, rates['Damage0'])
                rate_values = tuple(rates['CoreShotDamageRateChange' if name ==
                                    'coreShotDamageRate' else name[0].upper()+name[1:]]
                                    for name in RATE_NAMES)
                primitive = calculate_damage_rates(base, int(caster['ShotCount']),
                                                   caster['MuzzleCount'], rate_values)
                raw = apply_target_reduction(
                    primitive, int(target['DamageReductionRate']),
                    int(target['DamageReductionValue']),
                    debuff_decrease_rate=int(target['DamageReductionDebuffDecreaseRate']))
                self.assertEqual(struct.pack('<d', raw), struct.pack('<d', row['raw_damage']))
                self.assertEqual(double_to_long(raw), row['converted_stat_value'])

    def test_production_hit_uses_original_half_tie_conversion(self):
        result = calc_damage(24.5, {'crit_rate': 0.0},
                             {'damage_coeff': 100.0}, enemy_def=0.0)
        self.assertEqual(result['damage'], 25)

    def test_original_integer_conversion_oracle(self):
        data = json.loads((Path(__file__).parent / 'fixtures' /
                           'client-2df7134a-damage.json').read_text())
        for vector in data['double_to_long_oracle']['vectors']:
            with self.subTest(vector=vector['name']):
                self.assertEqual(double_to_long(vector['input']), vector['result'])

    def test_original_client_oracle(self):
        data = json.loads((Path(__file__).parent / 'fixtures' /
                           'client-2df7134a-damage.json').read_text())
        self.assertEqual(data['client_sha256'], CLIENT_SHA256)
        for vector in data['oracle']['vectors']:
            with self.subTest(vector=vector['name']):
                result = calculate_damage(**vector['arguments'])
                self.assertEqual(struct.pack('<d', result),
                                 struct.pack('<d', vector['result']))


if __name__ == '__main__':
    unittest.main()
