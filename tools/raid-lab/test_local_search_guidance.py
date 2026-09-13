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

    def test_runtime_needs_no_network_or_captures(self):
        load_data.cache_clear()
        with patch('socket.socket',side_effect=AssertionError('Network forbidden')):
            g,ids=self.make(['Crown','Naga'])
            self.assertGreater(g.bonus(ids[1],[ids[0]]),0)
        data=load_data()
        self.assertFalse(any('review' in u or 'notes' in u for u in data['units'].values()))
        self.assertFalse(any('notes' in t for t in data['teams']))


if __name__=='__main__': unittest.main()
