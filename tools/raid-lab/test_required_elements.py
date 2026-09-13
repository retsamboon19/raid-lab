"""Boss mechanics are mandatory even when the caller asks for Any element."""
import copy
import unittest
from unittest.mock import patch
import core
import encounters
import gpu_search


class RequiredElementTests(unittest.TestCase):
    required={
        'sr40':'Fire','sr39':'Iron',
        'museum-mother-whale':'Electric','museum-blacksmith':'Water',
        'museum-storm-bringer':'Fire','museum-crystal-chamber':'Electric','museum-indivilia':'Iron',
        'anomaly-ultra':'Iron','anomaly-mirror-container':'Electric','anomaly-kraken':'Wind',
        'anomaly-harvester':'Water','anomaly-indivilia':'Fire',
    }

    def test_all_mandatory_boss_profiles_override_absent_any_and_wrong_element(self):
        for boss,element in self.required.items():
            for mode in ('challenge','no-limit'):
                for supplied in (None,'Any',next(e for e in core.ELEMENT_KO if e!=element)):
                    with self.subTest(boss=boss,mode=mode,element=supplied):
                        raw=dict(boss_id=boss,museum_mode=mode,survival_policy='damage-only',encounter={'barrier_element':None})
                        if supplied is not None:raw['element']=supplied
                        s=core.validate_settings(raw)
                        self.assertTrue(s['element_locked'])
                        self.assertEqual(s['element'],element)
                        self.assertEqual(s['encounter']['barrier_element'],element)

    def test_no_blanket_weakness_barrier_inference(self):
        for boss in ('museum-ultra','museum-modernia','museum-alteisen','museum-harvester','training'):
            s=core.validate_settings(dict(boss_id=boss,element='Any'))
            self.assertFalse(s['element_locked'])
            self.assertEqual(s['element'],'Any')

    def test_cpu_and_manual_cannot_bypass_museum_element(self):
        names=['Liter','Crown','Modernia','Alice','Maxwell']
        ids=[core.NAME_MAP[n.lower()] for n in names]
        for mode in ('challenge','no-limit'):
            s=core.validate_settings(dict(boss_id='museum-mother-whale',element='Any',museum_mode=mode,survival_policy='damage-only'))
            self.assertFalse(core.valid(ids,s))
            with self.assertRaisesRegex(ValueError,'Electric unit'):
                core.manual(dict(roster=core.demo_roster(),members=ids,settings=s))

    def test_every_team_needs_distinct_element_access_before_search(self):
        rows=[dict(id=c['id'],build=core.default_build(),enabled=True,assumptions=[])
              for c in core.CATALOG if c['supported'] and 'Fire' not in c['barrier_elements']]
        with self.assertRaisesRegex(ValueError,'5 distinct.*Fire access; found 0'):
            core.search(dict(roster=rows,settings=dict(content_mode='solo',boss_id='sr40',element='Any',budget=3)))

    def test_matching_support_label_alone_is_not_a_damage_dealer(self):
        ids=['fire','b1','b2','b3','flex']
        catalog={n:dict(barrier_elements=['Fire' if n=='fire' else 'Water']) for n in ids}
        entry=dict(members=ids,damage=1000,breakdown=dict(fire=1,b1=1,b2=1,b3=600,flex=397))
        s=core.validate_settings(dict(boss_id='sr40',element='Any'))
        self.assertEqual(core.elemental_damage_report(entry,s,catalog)['providers'],[])
        entry['breakdown'].update(fire=400,b3=201)
        self.assertEqual(core.elemental_damage_report(entry,s,catalog)['providers'],['fire'])

    def test_gpu_gets_locked_element_and_accepts_supporter(self):
        ids=['fire','b2','b3','other3','flex']
        catalog={n:dict(burst=stage,role='Supporter',element=e,barrier_elements=[e],tags=[])
                 for n,stage,e in [('fire','1','Fire'),('b2','2','Water'),('b3','3','Water'),('other3','3','Water'),('flex','2','Water')]}
        s=core.validate_settings(dict(boss_id='anomaly-indivilia',element='Any',survival_policy='damage-only'))
        def dispatch(identifier,inputs,count,length,shader):
            self.assertEqual(s['element'],'Fire')
            self.assertEqual([bool(f&128) for f in inputs[1]],[True,False,False,False,False])
            self.assertEqual([bool(f&256) for f in inputs[1]],[True,False,False,False,False])
            return {2:list(range(5)),3:[1.]}
        with patch('gpu_search.device_info',return_value=dict(available=True,id='test',name='test',backend='test')),patch('gpu_search._dispatch',side_effect=dispatch):
            plans,_=gpu_search.explore(ids,dict.fromkeys(ids,1),catalog,s,lambda t,s:True,list,count=1)
        self.assertEqual(len(plans),1)


if __name__=='__main__':unittest.main()
