"""Search must not discard a membership because its off-burster sorted first."""
import unittest
from unittest.mock import patch
import core

class PrioritySearchTests(unittest.TestCase):
    def test_burst_one_and_two_priorities_are_not_fixed_by_sorting(self):
        catalog={n:{'burst':stage} for n,stage in [('b1a','1'),('b2a','2'),('b1b','1'),('b2b','2'),('b3','3')]}
        orders=core.burst_orders(list(catalog),catalog)
        self.assertEqual(len(orders),4)
        self.assertIn(('b1b','b2b','b1a','b2a','b3'),orders)

    def test_shortlist_reserves_places_for_distinct_memberships(self):
        rows=[(100,('a','b'),None),(99,('b','a'),None),(98,('a','c'),None)]
        self.assertEqual([frozenset(r[1]) for r in core.membership_shortlist(rows,2)],
                         [frozenset(('a','b')),frozenset(('a','c'))])

    def test_replacement_and_offburst_are_searched_together(self):
        names=['Little Mermaid','Anis: Star','Nayuta','Scarlet: Black Shadow','Snow White: Heavy Arms','Mihara: Bonding Chain']
        ids=[core.NAME_MAP[n.lower()] for n in names]
        mermaid,anis,nayuta,scarlet,snow,mihara=ids
        rows=[{'id':n,'enabled':True,'assumptions':[],'build':core.default_build()} for n in ids]
        desired=[anis,nayuta,scarlet,snow,mihara]
        seen=[]
        def evaluate(team,duration,detail,roster,s):
            team=list(team);seen.append((team,duration))
            # Alphabetical Anis membership is worse than Mermaid. Only a joint
            # membership+priority change exposes its advantage.
            b3=[n for n in team if core.CAT[n]['burst']=='3']
            damage=300 if set(team)==set(desired) and b3==desired[2:] else (100 if anis in team else 200)
            return {'members':team,'damage':damage,'breakdown':{n:damage/5 for n in team},
                    'encounter_timeline':{'stop_reason':'Unverified survival stop','simulated_until':125} if damage==300 else None}
        def heuristic(team,*args):return 100000 if mermaid in team else 1
        def fill(executor,keys,roster,settings,cache,failures,completed,cancelled):
            for key in keys:
                if key not in cache:
                    cache[key]=evaluate(*key,roster,settings);completed()
        with patch('core.CandidateExecutor.fill',new=fill),patch('core.heuristic',side_effect=heuristic):
            result=core.search({'roster':rows,'settings':{'content_mode':'practice','duration':180,'budget':3,'compute_mode':'single'}})
        selected=result['teams'][0]['members']
        self.assertEqual(set(selected),set(desired))
        self.assertEqual([n for n in selected if core.CAT[n]['burst']=='3'],desired[2:])
        self.assertIn((selected,180),seen)
        audit=result['selection']['screening_checks']
        self.assertTrue(any(set(r['members'])==set(selected) and r['full_duration_promoted'] for r in audit))
        self.assertTrue(result['selection']['survival_model_stops'])
        self.assertTrue(any('Ranking is sensitive' in w for w in result['warnings']))

if __name__=='__main__':unittest.main()
