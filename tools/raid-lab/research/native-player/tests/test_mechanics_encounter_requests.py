"""Reject boss/profile mixtures, arbitrary waves and invalid capped builds."""
import copy
import json
from pathlib import Path
import unittest
from unittest.mock import patch

import mechanics_request as request

HERE = Path(__file__).resolve().parent


class EncounterRequestTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.registry = json.loads((HERE/'mechanics-encounters-current.json').read_text())
        cls.base = json.loads((HERE/'mechanics_request_snapshot.json').read_text())

    def setUp(self):
        self.patch = patch.object(request, 'current_encounter_registry', return_value=self.registry)
        self.patch.start()
        self.addCleanup(self.patch.stop)

    def value(self, identity='anomaly-mirror-container'):
        profile = next(p for p in self.registry['profiles'] if p['productId'] == identity)
        value = copy.deepcopy(self.base)
        value.update(schemaVersion=2, encounterProfileId=identity,
                     encounter={**profile['encounter'], 'randomSeed':1})
        for character in value['characters']:
            levels=profile['sourceTableRow']
            character['level'] = levels['CharacterLv'] if 'CharacterLv' in levels else min(character['level'],levels['LimitCharacterLv'])
        return value

    def test_exact_registered_inputs_and_legacy_survive(self):
        request.validate_request(self.base)
        for profile in self.registry['profiles']:
            request.validate_request(self.value(profile['productId']))

    def test_wave_and_profile_mismatch_rejected(self):
        value = self.value()
        value['encounter']['waveId'] = 6302009
        with self.assertRaises(ValueError): request.validate_request(value)
        value = self.value()
        value['encounterProfileId'] = 'anomaly-kraken'
        with self.assertRaises(ValueError): request.validate_request(value)

    def test_unknown_profile_and_omitted_identity_rejected(self):
        value = self.value()
        value['encounterProfileId'] = 'unknown'
        with self.assertRaises(ValueError): request.validate_request(value)
        del value['encounterProfileId']
        with self.assertRaises(ValueError): request.validate_request(value)

    def test_original_character_cap_is_not_silently_ignored(self):
        value = self.value('special-chatterbox')
        value['characters'][0]['level'] = 400
        with self.assertRaises(ValueError): request.validate_request(value)

    def test_profile_identity_changes_request_hash(self):
        self.assertNotEqual(request.request_sha256(self.value()),request.request_sha256(self.value('anomaly-kraken')))


if __name__ == '__main__': unittest.main()
