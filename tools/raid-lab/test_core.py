import copy
import unittest
import core

class RosterTests(unittest.TestCase):
    def test_export_roundtrip(self):
        demo=core.demo_roster()
        self.assertGreaterEqual(len(demo),25)
        self.assertEqual(core.import_roster({'roster':demo})['roster'],demo)
    def test_complete_real_catalog_and_repeatable_import(self):
        self.assertEqual(len(core.CATALOG),200)
        self.assertTrue(all(c['supported'] for c in core.CATALOG))
        self.assertFalse(any(c['id'].startswith('test_') for c in core.CATALOG))
        n=core.NAME_MAP['crow']
        a=core.import_roster({'roster':[{'id':n,'build':core.default_build()}]})
        self.assertEqual(core.import_roster(a)['roster'],a['roster'])
        old=copy.deepcopy(a)
        old['roster'][0]['assumptions']=['Skill kit not supported; excluded from simulations.','Keep gear assumption.']
        self.assertEqual(core.import_roster(old)['roster'][0]['assumptions'],['Keep gear assumption.'])
    def test_personal_cdr_is_not_team_cdr(self):
        c=next(c for c in core.CATALOG if c['name']=='Blanc')
        self.assertNotIn('CDR',c['tags'])
        self.assertIn('Personal CDR',c['tags'])
    def test_exia_partial_import_does_not_invent_maxed_gear(self):
        c=next(c for c in core.CATALOG if c['name']=='Liter')
        r=core.import_roster({'elements':{'Iron':[{'name_code':c['name_code'],'skill1_level':7,'skill2_level':4,'skill_burst_level':10,'limit_break':{'grade':2,'core':0},'equipments':{'0':[{'function_type':'StatAmmoLoad','function_value':64.82},{'function_type':'StatAmmoLoad','function_value':52.5}]}}]}})['roster'][0]
        self.assertEqual(r['build']['skill_levels'],{'1':7,'2':4,'3':10})
        self.assertEqual(r['build']['equip_skills']['max_ammo_pct'],[64.82,52.5])
        self.assertTrue(all(e['tier']==core.NO_ITEM for e in r['build']['equipment'].values()))
        self.assertTrue(r['assumptions'])
    def test_unowned_and_duplicates(self):
        r=core.demo_roster()[0]
        out=core.import_roster({'roster':[r,r,{**r,'owned':False}]})
        self.assertEqual(len(out['roster']),1)
        self.assertIn('Duplicate',out['warnings'][0])
    def test_blank_exia_template_is_not_owned(self):
        c=next(c for c in core.CATALOG if c['name']=='Liter')
        with self.assertRaisesRegex(ValueError,'No matching owned'):
            core.import_roster({'elements':{'Iron':[{'name_code':c['name_code'],'skill1_level':'','limit_break':None}]}})
    def test_invalid_numeric_values(self):
        for val in [float('nan'),-1,1001,True]:
            b=core.default_build();b['level']=val
            with self.assertRaises(ValueError):core.validate_build(b)
        with self.assertRaises(ValueError):core.validate_settings({'duration':float('inf')})
    def test_no_unsupported_fallback(self):
        rows=core.demo_roster()[:4]
        with self.assertRaisesRegex(ValueError,'Need 5'):core.search({'roster':rows,'settings':{'teams':1}})
    def test_gear_tier_not_lost_in_merge(self):
        b=core.validate_build(core.demo_roster()[0]['build'])
        self.assertTrue(all(e['tier']=='기업' for e in b['equipment'].values()))
    def test_empty_cube_has_no_stats_or_effects(self):
        from calculator.base_stat import calc_base_stats
        from calculator.buff_manager import BuffManager
        name=next(c['id'] for c in core.CATALOG if c['name']=='Liter')
        empty=core.spec.build_char(name,core.default_build(),no_layer=True)
        equipped=copy.deepcopy(empty);equipped['cube']={'name':'렐릭 베어 큐브','level':1}
        a,b=calc_base_stats(empty),calc_base_stats(equipped)
        self.assertEqual(b['atk']-a['atk'],390)
        self.assertEqual(b['hp']-a['hp'],11800)
        self.assertEqual(BuffManager._make_cube_effects(None,core.NO_ITEM,0),[])
    def test_favorite_item_uses_sr15_stats(self):
        b=core.default_build();b['favorite_stage']=2
        self.assertEqual(core.validate_build(b)['collection_stage'],'SR15')
    def test_fixed_level_shortlisting_is_level_normalised(self):
        a=core.demo_roster()[0];b=copy.deepcopy(a);b['build']['level']=1
        s=core.validate_settings({'fixed_level':True,'level':400})
        self.assertEqual(core.heuristic([a['id']],{a['id']:a},s),core.heuristic([b['id']],{b['id']:b},s))

class SimulationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.roster=core.demo_roster()
        names=['Liter','Crown','Scarlet','Alice','Naga']
        cls.ids=[next(c['id'] for c in core.CATALOG if c['name']==n) for n in names]
    def test_repeatable_damage_and_bursts(self):
        p={'roster':self.roster,'members':self.ids,'settings':{'duration':30,'teams':1}}
        a=core.manual(p);b=core.manual(p)
        self.assertEqual(a['total'],b['total'])
        self.assertGreater(a['total'],0)
        self.assertGreater(a['teams'][0]['bursts'],0)
        self.assertEqual(sum(a['teams'][0]['breakdown'].values()),a['total'])
    def test_lower_skills_affect_damage(self):
        base={'roster':self.roster,'members':self.ids,'settings':{'duration':30,'teams':1}}
        high=core.manual(base)['total']
        low=copy.deepcopy(base)
        for r in low['roster']:r['build']['skill_levels']={'1':1,'2':1,'3':1}
        self.assertLess(core.manual(low)['total'],high)
    def test_duplicate_manual_units_rejected(self):
        with self.assertRaises(ValueError):core.manual({'roster':self.roster,'members':[self.ids[0]]*5})
    def test_five_team_plan_and_cancel(self):
        p={'roster':self.roster,'settings':{'teams':5,'duration':30,'budget':3}}
        with self.assertRaises(InterruptedError):core.search(p,cancelled=lambda:True)
        r=core.search(p)
        self.assertEqual(len(r['teams']),5)
        members=[n for t in r['teams'] for n in t['members']]
        self.assertEqual(len(members),len(set(members)))
        self.assertEqual(r['total'],sum(t['damage'] for t in r['teams']))
        self.assertTrue(all(t['duration']==30 for t in r['teams']))
    def test_impossible_filter_does_not_silently_relax(self):
        rows=[r for r in self.roster if core.CAT[r['id']]['element']!='Electric']
        with self.assertRaisesRegex(ValueError,'No complete plan'):core.search({'roster':rows,'settings':{'teams':1,'element':'Electric','budget':3}})

if __name__=='__main__':unittest.main()
