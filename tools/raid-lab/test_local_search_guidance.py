import unittest
from unittest.mock import patch
import core
from search_guidance import SearchGuidance, load_data


class LocalGuidanceTests(unittest.TestCase):
    def make(self, names, weights=None, **settings):
        ids=[core.NAME_MAP[n.lower()] for n in names]
        roster={n:{'build':core.default_build()} for n in ids}
        g=SearchGuidance(roster,core.CAT,settings,dict(zip(ids,weights or [100]*len(ids))))
        return g,ids

    def test_all_real_catalog_units_mapped_and_collisions_distinct(self):
        data=load_data()
        self.assertEqual(data['coverage']['unmapped_catalog'],['test_B1','test_B2','test_B3'])
        self.assertNotEqual(data['units']['rei']['unit_id'],data['units']['rei-ayanami']['unit_id'])
        self.assertNotEqual(data['units']['sakura']['unit_id'],data['units']['sakura-suzuhara']['unit_id'])

    def test_owned_fourth_recommendation_is_reserved_and_build_ranked(self):
        g,ids=self.make(['Crown','Naga','Rapunzel','Helm','Alice: Wonderland Bunny','Mana','Liter'],[100,5,10,20,800,100,100000])
        crown,naga,rapunzel,helm,alice,mana,liter=ids
        g.roster[helm]['build']['favorite_stage']=3
        g=SearchGuidance(g.roster,core.CAT,{},g.weights)
        choices=g.alternatives(ids[1:],[crown])
        self.assertIn(alice,choices)
        self.assertLess(choices.index(alice),choices.index(naga))
        self.assertGreaterEqual(len([n for n in choices if g.bonus(n,[crown])>0]),4)
        self.assertIn(liter,choices)  # Strong non-recommended unit remains eligible.

    def test_favorite_and_context_conditions(self):
        g,ids=self.make(['Crown','Helm'])
        self.assertIsNone(g.resolve('helm-treasure'))
        self.assertFalse(g.context({'mode':'PVP'}))
        self.assertFalse(g.context({'mode':'Campaign'}))
        self.assertFalse(g.context({'element':'Wind'}))
        self.assertFalse(g.context({'assisted':True}))
        self.assertFalse(g.context({'mode':'Anomaly - Kraken'}))
        g.settings['boss_id']='anomaly-kraken'
        self.assertTrue(g.context({'mode':'Anomaly - Kraken'}))

    def test_crown_precedes_naga_without_dropping_alternatives(self):
        g,ids=self.make(['Naga','Crown','Liter','Alice','Modernia'])
        orders=core.burst_orders(ids,core.CAT,g)
        self.assertEqual(orders[0][0],ids[1])
        self.assertEqual(len(orders),len(core.burst_orders(ids,core.CAT)))

    def test_museum_examples_match_only_the_selected_boss(self):
        g,_=self.make(['Cinderella','Anis: Star','Arcana','Isabel'],
                     content_mode='museum',element='Electric',
                     encounter={'name':'Mother Whale'})
        self.assertTrue(g.context({'mode':'Museum - Mother Whale','element':'Electric'}))
        self.assertFalse(g.context({'mode':'Museum - Ultra'}))
        # The stored package also requires Flora's Favorite Item. Missing her
        # must not turn an incomplete team into a claimed complete template.
        self.assertFalse(any(core.NAME_MAP['cinderella'] in t for t in g.templates))
        g.settings['encounter']['name']='Blacksmith'
        self.assertTrue(g.context({'mode':'Museum - Black Smith'}))
        g.settings['content_mode']='solo'
        self.assertFalse(g.context({'mode':'Museum - Black Smith'}))

    def test_cinderella_support_pairs_remain_available(self):
        g,ids=self.make(['Cinderella','Rouge','Anis: Sparkling Summer'],element='Electric')
        for support in ids[1:]:
            self.assertGreater(g.bonus(support,[ids[0]]),0)

    def test_anis_star_prefers_solo_burst_one_without_excluding_reentry(self):
        g,ids=self.make(['Anis: Star','Liter','Alice: Wonderland Bunny','Rupee: Winter Shopper',
                         'Avistar','Tia','Red Hood','Rapi: Red Hood'])
        anis,liter,*exceptions=ids
        self.assertEqual(g.anis_star_mode([anis]),'solo')
        self.assertEqual(g.anis_star_mode([anis,liter]),'reentry')
        self.assertLess(g.priority(liter,[anis]),g.priority(liter,[]))
        self.assertLess(g.priority(anis,[liter]),g.priority(anis,[]))
        self.assertLess(g.score([anis,liter]),2*g.score([anis]))
        for unit in exceptions:
            with self.subTest(unit=unit):
                self.assertEqual(g.anis_star_mode([anis,unit]),'solo')
                self.assertEqual(g.priority(unit,[anis]),g.priority(unit,[]))
        self.assertTrue(any(liter in g.alternatives([liter,*exceptions],[anis],iteration)
                            for iteration in range(3)))
        self.assertTrue(any('healing and Max HP' in note for note in g.report([anis,liter])['notes']))

    def test_anis_star_reentry_metadata_matches_skill_model(self):
        data=load_data()
        model={n for n,effects in core.SKILLS.items()
               if n!=data['units']['anis-star']['unit_id']
               and any(e.get('stat')=='burst_stage_override:reenter1' for e in effects)}
        recorded={data['units'][slug]['unit_id'] for slug in data['reentry_burst1']}
        self.assertEqual(recorded,model)

    def test_crown_anis_star_healing_pair_requires_reentry(self):
        g,(crown,anis,liter)=self.make(['Crown','Anis: Star','Liter'])
        self.assertNotIn(tuple(sorted((crown,anis))),g.pair_values([crown,anis]))
        self.assertIn(tuple(sorted((crown,anis))),g.pair_values([crown,anis,liter]))
        self.assertFalse(any('re-entry' in p['reason'] for p in g.report([crown,anis])['pairs']))

    def test_runtime_needs_no_network_or_captures(self):
        load_data.cache_clear()
        with patch('socket.socket',side_effect=AssertionError('Network forbidden')):
            g,ids=self.make(['Crown','Naga'])
            self.assertGreater(g.bonus(ids[1],[ids[0]]),0)
        data=load_data()
        self.assertFalse(any('review' in u or 'notes' in u for u in data['units'].values()))
        self.assertFalse(any('notes' in t for t in data['teams']))


if __name__=='__main__': unittest.main()
