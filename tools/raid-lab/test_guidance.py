import unittest
import core
import encounters

class GuidanceTests(unittest.TestCase):
    def setUp(self):
        self.rows=core.demo_roster()
        self.nonhealers=[c['id'] for c in core.CATALOG if c['supported'] and 'Healing' not in c['tags']][:5]
    def test_stormbringer_requires_healing_in_guide_mode(self):
        s=core.validate_settings({'boss_id':'museum-storm-bringer'})
        self.assertEqual(s['encounter']['barrier_element'],'Fire')
        self.assertFalse(encounters.follows_guide(self.nonhealers,s,core.CAT))
        healer=next(c['id'] for c in core.CATALOG if c['supported'] and 'Healing' in c['tags'])
        self.assertTrue(encounters.follows_guide(self.nonhealers[:4]+[healer],s,core.CAT))
        s['survival_policy']='damage-only'
        self.assertTrue(encounters.follows_guide(self.nonhealers,s,core.CAT))
    def test_shield_and_healing_are_not_interchangeable(self):
        s=core.validate_settings({'boss_id':'anomaly-ultra'})
        no_shield=[c['id'] for c in core.CATALOG if c['supported'] and 'Shield' not in c['tags']][:5]
        self.assertFalse(encounters.follows_guide(no_shield,s,core.CAT))
        self.assertEqual(s['encounter']['guidance']['required_tags'],['Shield'])
    def test_guidance_keeps_variants_and_sources_separate(self):
        self.assertIsNone(encounters.BY_ID['anomaly-ultra']['guidance']['source'])
        self.assertIn('note.com',encounters.BY_ID['museum-storm-bringer']['guidance']['source'])
        self.assertNotIn('guidance',encounters.BY_ID['special-modernia'])
    def test_support_presence_never_proves_survival(self):
        s=core.validate_settings({'boss_id':'museum-storm-bringer'})
        r=encounters.assessment(s,self.nonhealers,core.CAT)
        self.assertFalse(r['clear_verified'])
        self.assertEqual(next(c for c in r['checks'] if c['name']=='Guide support coverage')['status'],'risk')
    def test_same_unit_more_invested_has_higher_shortlist_weight(self):
        row=next(r for r in self.rows if 'Healing' in core.CAT[r['id']]['tags'])
        import copy
        low=copy.deepcopy(row);low['build']['skill_levels']={'1':1,'2':1,'3':1}
        s=core.validate_settings({'boss_id':'museum-storm-bringer'})
        self.assertGreater(core.heuristic([row['id']],{row['id']:row},s),core.heuristic([low['id']],{low['id']:low},s))

if __name__=='__main__':unittest.main()
