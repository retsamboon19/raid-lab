import unittest
from types import SimpleNamespace as N
from unittest.mock import patch
import core
from recommendation import evidence_report

class RecommendationTests(unittest.TestCase):
    def test_nayuta_shared_healing_is_not_a_crown_buff_enabler(self):
        ids=[core.NAME_MAP[n.lower()] for n in ['Liter','Crown','Nayuta','Alice','Modernia']]
        rows=[{'id':n,'enabled':True,'assumptions':[],'build':core.default_build()} for n in ids]
        result=core.manual({'roster':rows,'members':ids,'settings':{'content_mode':'practice','duration':30}})
        cards=result['teams'][0]['recommendation']['rationale']['interactions']
        self.assertFalse(any(c['title']=='Nayuta enables Crown through healing' for c in cards))

    def test_search_does_not_lose_to_supplied_burst_order_for_same_five_units(self):
        names=['Little Mermaid','Nayuta','Scarlet: Black Shadow','Liberalio','Helm'] # Keep non-B3 slots fixed; test burst priority, not frame-order ties.
        ids=[core.NAME_MAP[n.lower()] for n in names]
        rows=[{'id':n,'enabled':True,'assumptions':[],'build':core.default_build()} for n in ids]
        settings={'content_mode':'anomaly','boss_id':'anomaly-kraken','duration':60,'budget':3}
        reference=core.manual({'roster':rows,'members':ids,'settings':settings})
        found=core.search({'roster':rows,'settings':settings})
        self.assertGreaterEqual(found['total'],reference['total'])
        self.assertEqual(set(found['teams'][0]['members']),set(ids))
        self.assertEqual(len(found['selection']['rotation_checks']),6)
        self.assertEqual(found['total'],max(x['damage'] for x in found['selection']['rotation_checks']))

    def test_every_supported_kit_has_primary_skill_explanations(self):
        from kit_rationale import build_kit_reports
        from calculator.buff_manager import char_effects
        result=N(log=N(buff_events=[],burst_log=[]))
        count=0
        for n,c in core.CAT.items():
            if not c['supported']:continue
            for stage in (0,3):
                row={'build':core.default_build()};row['build']['favorite_stage']=stage
                effects={n:char_effects(n,stage)}
                report=build_kit_reports([n],{n:row},core.CAT,effects,result,{})[n]
                self.assertTrue(report['skills'],c['name'])
                self.assertTrue(all(k['explanation'] and k['skill'] for k in report['skills']))
            count+=1
        self.assertGreaterEqual(count,87)

    def test_team_without_crown_or_naga_has_five_specific_kit_reports(self):
        ids=[core.NAME_MAP[n.lower()] for n in ['Liter','Blanc','Noir','Alice','Modernia']]
        rows=[{'id':n,'enabled':True,'assumptions':[],'build':core.default_build()} for n in ids]
        result=core.manual({'roster':rows,'members':core.ordered(ids),'settings':{'content_mode':'practice','duration':60}})
        units=result['teams'][0]['recommendation']['units']
        self.assertEqual(len(units),5)
        self.assertTrue(all(u['kit_explanation']['skills'] for u in units))
        alice=next(u for u in units if core.CAT[u['id']]['name']=='Alice')
        self.assertTrue(any('charged' in s['explanation'] for s in alice['kit_explanation']['skills']))
        liter=next(u for u in units if core.CAT[u['id']]['name']=='Liter')
        self.assertTrue(any(s['mechanic']=='burst cooldown reduction' for s in liter['kit_explanation']['skills']))

    def test_crown_naga_explanation_checks_real_heal_targets(self):
        ids=[core.NAME_MAP[n.lower()] for n in ['Liter','Crown','Naga','Alice','Modernia']]
        rows=[{'id':n,'enabled':True,'assumptions':[],'build':core.default_build()} for n in ids]
        order=core.ordered(ids)
        self.assertEqual(core.CAT[order[0]]['name'],'Crown')
        r=core.manual({'roster':rows,'members':order,'settings':{'content_mode':'practice','duration':60}})
        rec=r['teams'][0]['recommendation']
        pair=next(c for c in rec['rationale']['interactions'] if c['title'].startswith('Crown + Naga:'))
        self.assertIn('Naga healing reached Crown: yes',pair['observed'])
        self.assertIn('Crown shield reached Naga: yes',pair['observed'])
        self.assertIn('no exposed core',pair['condition'])
        naga=next(u for u in rec['units'] if core.CAT[u['id']]['name']=='Naga')
        self.assertEqual(naga['burst_times'],[])
        self.assertTrue(any(x['effect']=='attack damage' for x in rec['synergies']))

    def test_locked_effects_do_not_leak_into_build_tags(self):
        n=core.demo_roster()[0]['id']
        row={'build':core.default_build()}
        with patch('core.char_effects',return_value=[]):
            self.assertEqual(core.resolve_catalog({n:row})[n]['tags'],[])
        self.assertNotIn('_catalog',core.public_settings({'_catalog':{},'duration':30}))

    def test_shield_condition_is_not_shield_creation(self):
        self.assertNotIn('Shield',core.tags_for('',[{'stat':'during_shield'}]))
        self.assertIn('Healing',core.tags_for('',[{'stat':'lifesteal_pct','target':'all_allies'}]))

    def test_report_uses_observed_recipients_and_detects_idle_healer(self):
        team=['a','b'];catalog={n:{'name':n,'burst':'3','weapon':'AR','element':'Fire','barrier_elements':['Fire'],'tags':['Healing'] if n=='a' else []} for n in team}
        rows={n:{'build':core.default_build(),'assumptions':[]} for n in team}
        log=N(burst_log=[N(caster='b',t=10,event='stage:3 사용')],gauge_log=[N(caster='b',amount=100)],
              buff_events=[N(kind='activate',caster='a',target='b',stat='core_dmg_pct',t=10),N(kind='activate',caster='a',target='b',stat=None,t=10)])
        result=N(log=log,char_total={'a':10,'b':90},squad_total=100)
        with patch('calculator.buff_manager.char_effects',return_value=[{'stat':'heal_hp_pct','target':'all_allies','trigger':{'timing':['burst_cast']}}]):
            report=evidence_report(result,team,rows,{},catalog)
        self.assertEqual(report['available_healers'],[])
        self.assertTrue(report['warnings'])
        self.assertEqual(report['units'][1]['gauge_share'],100)
        self.assertEqual(report['synergies'][0]['target'],'b')
        self.assertIn('cannot increase',report['synergies'][0]['qualification'])

if __name__=='__main__':unittest.main()
