import copy
import unittest
from unittest.mock import patch

import core
import gpu_search


class ClassNeutralSearchTests(unittest.TestCase):
    def test_class_label_cannot_change_shortlist_score_or_burst_order(self):
        rows=core.demo_roster()
        roster={r['id']:r for r in rows}
        settings=core.validate_settings({'element':'Electric'})
        catalog=copy.deepcopy(core.CAT)
        settings['_catalog']=catalog
        cinderella=core.NAME_MAP['cinderella']
        scarlet=core.NAME_MAP['scarlet']
        scores=[];orders=[]
        for role in ('Attacker','Defender','Supporter'):
            catalog[cinderella]['role']=role
            scores.append(core.heuristic([cinderella],roster,settings))
            with patch.object(core,'CAT',catalog):
                orders.append(core.ordered([scarlet,cinderella]))
        self.assertEqual(len(set(scores)),1)
        self.assertEqual(orders,[orders[0]]*3)

    def test_cdr_healing_and_damage_support_still_matter(self):
        rows=core.demo_roster();roster={r['id']:r for r in rows}
        team=[core.NAME_MAP[n.lower()] for n in ['Liter','Crown','Cinderella','Scarlet','Naga']]
        settings=core.validate_settings({'element':'Electric','cdr':True,'healing':True})
        catalog=copy.deepcopy(core.CAT);settings['_catalog']=catalog
        self.assertTrue(core.valid(team,settings))
        baseline=core.heuristic(team,roster,settings)
        for n in team:catalog[n]['tags']=[]
        self.assertFalse(core.valid(team,settings))
        self.assertLess(core.heuristic(team,roster,settings),baseline)

    def test_gpu_accepts_elemental_defender_and_supporter_at_any_stage(self):
        ids=['b1','b2','b3','other3','flex']
        catalog={n:{'burst':stage,'role':role,'element':element,
                    'barrier_elements':[element],'tags':[]} for n,stage,role,element in [
            ('b1','1','Supporter','Electric'),('b2','2','Defender','Electric'),
            ('b3','3','Defender','Electric'),('other3','3','Attacker','Fire'),
            ('flex','2','Supporter','Fire')]}
        settings={'teams':1,'cdr':False,'healing':False,'element':'Electric','encounter':{}}
        def dispatch(identifier,inputs,count,length,shader):
            flags=inputs[1]
            self.assertEqual([bool(f&256) for f in flags],[True,True,True,False,False])
            return {2:list(range(5)),3:[1.]}
        with patch('gpu_search.device_info',return_value={'available':True,'id':'test','name':'test','backend':'test'}),patch('gpu_search._dispatch',side_effect=dispatch):
            plans,_=gpu_search.explore(ids,dict.fromkeys(ids,1),catalog,settings,lambda t,s:True,list,count=1)
        self.assertEqual(len(plans),1)


if __name__=='__main__':unittest.main()
