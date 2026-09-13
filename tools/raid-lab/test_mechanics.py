import copy
import unittest
from unittest.mock import patch
import core
import encounters
from mechanics import EncounterRuntime

class ModeTests(unittest.TestCase):
    def test_content_controls_team_count_and_level(self):
        for mode,boss,teams in [('solo','sr40',5),('museum','museum-ultra',5),('special','special-modernia',1),('anomaly','anomaly-ultra',1),('campaign','campaign',1),('practice','training',1)]:
            s=core.validate_settings(dict(content_mode=mode,boss_id=boss,teams=3))
            self.assertEqual(s['teams'],teams)
        s=core.validate_settings(dict(content_mode='special',boss_id='special-modernia',level=900))
        self.assertEqual(encounters.unit_level({'level':1},s),200)
        s=core.validate_settings(dict(content_mode='anomaly',boss_id='anomaly-ultra'))
        self.assertEqual(encounters.unit_level({'level':240},s),240)
        self.assertEqual(encounters.unit_level({'level':900},s),400)
        with self.assertRaises(ValueError):core.validate_settings(dict(content_mode='campaign',boss_id='sr40'))
    def test_cp_penalty_only_in_campaign(self):
        self.assertEqual(encounters.cp_penalty(0),0)
        self.assertGreater(encounters.cp_penalty(.01),0)
        self.assertGreater(encounters.cp_penalty(30),encounters.cp_penalty(10))
        s=core.validate_settings(dict(boss_id='special-modernia',cp_deficit=30))
        self.assertEqual(s['stat_penalty'],0)
        report=core.search(dict(roster=core.demo_roster(),settings=dict(content_mode='campaign',boss_id='campaign',cp_deficit=20,budget=3)))
        self.assertEqual(report['kind'],'campaign');self.assertEqual(len(report['teams']),1)
        self.assertNotIn('total',report);self.assertNotIn('dps',report['teams'][0])
        self.assertGreater(report['settings']['stat_penalty'],20)
    def test_element_presence_does_not_certify_qte(self):
        s=core.validate_settings(dict(boss_id='sr40'))
        report=encounters.assessment(s,[r['id'] for r in core.demo_roster()[:5]],core.CAT)
        self.assertFalse(report['clear_verified'])
        self.assertEqual(next(c for c in report['checks'] if c['name']=='QTE damage before deadline')['status'],'unknown')

class RuntimeTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.roster=core.demo_roster()
        cls.ids=[next(c['id'] for c in core.CATALOG if c['name']==n) for n in ['Liter','Crown','Modernia','Scarlet','Alice']]
        cls.chars={r['id']:r['build'] for r in cls.roster if r['id'] in cls.ids}
    def sim(self,script):
        squad=core.spec.build_squad(self.ids,chars=copy.deepcopy(self.chars),no_layer=set(self.ids))
        cfg=core.spec.build_config(squad,{'duration':30,'rng_mode':'expected','burst_gauge_mode':'accumulate'})
        runtime=EncounterRuntime(script);cfg['encounter_runtime']=runtime
        result=core.simulate(squad,cfg,verbose=True,seed=42)
        return result,runtime
    def test_invulnerability_blocks_every_damage_path_and_resumes(self):
        result,runtime=self.sim([dict(kind='invulnerable',start=10,duration=10)])
        self.assertFalse(any(h.damage for h in result.hits if 10.001<h.t<19.999))
        self.assertTrue(any(h.damage for h in result.hits if h.t>20.001))
        self.assertFalse(runtime.stopped)
    def test_immunity_input_is_connected_to_app(self):
        report=core.manual(dict(roster=self.roster,members=self.ids,settings=dict(duration=30,invulnerable_windows_text='0-30')))
        self.assertEqual(report['total'],0)
        self.assertIsNotNone(report['teams'][0]['encounter_timeline'])
    def test_actual_weapon_damage_can_pass_or_fail_qte(self):
        base=dict(kind='qte',start=3,duration=3,controller=self.ids[0],on_fail='wipe',targets=[{'hp':1}])
        good,passed=self.sim([base])
        self.assertEqual(passed.report()['checks'][0]['status'],'passed')
        bad=copy.deepcopy(base);bad['targets'][0]['hp']=1e20
        result,failed=self.sim([bad])
        self.assertEqual(failed.report()['checks'][0]['status'],'failed')
        self.assertTrue(failed.stopped)
        self.assertLessEqual(max(h.t for h in result.hits),6)
        self.assertLess(result.squad_total,good.squad_total)
    def test_wrong_element_and_unknown_hp_never_pass(self):
        e=dict(kind='qte',start=3,duration=2,controller=self.ids[0],on_fail='wipe',targets=[{'hp':1,'element':'작열'}])
        _,r=self.sim([e]);self.assertEqual(r.report()['checks'][0]['status'],'failed')
        e['targets'][0]['hp']=None
        _,r=self.sim([e]);self.assertEqual(r.report()['checks'][0]['status'],'unknown')
    def test_damage_threshold_drives_phase(self):
        _,runtime=self.sim([dict(kind='invulnerable',after_damage=1,duration=3)])
        start=runtime.events[0]['time'];self.assertGreater(start,0);self.assertLess(start,1)
    def test_automatic_qte_aim_passes_only_with_real_damage(self):
        event=dict(kind='qte',start=3,duration=3,on_fail='wipe',targets=[{'hp':1},{'hp':1}])
        _,runtime=self.sim([event])
        check=runtime.report()['checks'][0]
        self.assertEqual(check['status'],'passed')
        self.assertTrue(all(t['controller'] in self.ids for t in check['targets']))
        event['targets']=[{'hp':1e20}]
        _,runtime=self.sim([event]);self.assertEqual(runtime.report()['checks'][0]['status'],'failed')
    def test_automatic_aim_skips_ineligible_shooter(self):
        runtime=EncounterRuntime([dict(kind='qte',start=0,duration=3,targets=[{'hp':1,'element':'Water'}])])
        runtime.advance(0)
        self.assertIsNone(runtime.target('wrong','AR','Fire'))
        self.assertIsNotNone(runtime.target('right','AR','Water'))
        self.assertEqual(runtime.active['controller'],'right')
    def test_submerged_boss_does_not_prevent_shooting_qte(self):
        _,runtime=self.sim([dict(kind='untargetable',start=0,duration=10),
                             dict(kind='qte',start=1,duration=3,targets=[{'hp':1}],on_fail='wipe')])
        self.assertEqual(runtime.report()['checks'][0]['status'],'passed')
    def test_chained_qte_uses_weapon_damage_in_combat_engine(self):
        graph=[dict(id=1,kind='break',hp=1,duration=2,first=True,chain=[2]),
               dict(id=2,kind='break',hp=1,duration=2,delay=.1)]
        _,runtime=self.sim([dict(kind='qte',start=1,duration=6,graph=graph,on_fail='wipe')])
        self.assertEqual(runtime.report()['checks'][0]['status'],'passed')
        graph[1]['hp']=1e20
        _,runtime=self.sim([dict(kind='qte',start=1,duration=6,graph=graph,on_fail='wipe')])
        self.assertEqual(runtime.report()['checks'][0]['status'],'failed')
    def test_scripted_cover_pauses_firing_without_immunity(self):
        result,runtime=self.sim([dict(kind='cover',start=0,duration=10)])
        self.assertFalse(any(h.damage for h in result.hits if h.t<9.999))
        self.assertTrue(any(h.damage for h in result.hits if h.t>10.001))
        self.assertFalse(runtime.stopped)
    def test_museum_defence_changes_after_damage_not_elapsed_time(self):
        settings=core.validate_settings(dict(content_mode='museum',boss_id='museum-ultra',museum_mode='no-limit'))
        runtime=encounters.config(settings,180)['encounter_runtime']
        stages=settings['encounter']['stat_phases']
        runtime.advance(0);self.assertEqual(runtime.enemy_def,stages[0]['enemy_def'])
        runtime.advance(90);self.assertEqual(runtime.enemy_def,stages[0]['enemy_def'])
        runtime.damage=stages[1]['after_damage'];runtime.advance(91)
        self.assertEqual(runtime.enemy_def,stages[1]['enemy_def'])
        seen=[]
        def calculate(**args):seen.append(args['enemy_def']);return {'damage':1}
        runtime.resolve('unit','Water','AR',{'is_normal_atk':True},calculate,{'enemy_def':0})
        self.assertEqual(seen,[stages[1]['enemy_def']])
    def test_every_museum_profile_has_complete_stat_references(self):
        for profile in encounters.STATIC_DATA['profiles'].values():
            for mode in profile['modes'].values():
                stages=mode['level_changes']
                self.assertEqual(stages[0]['after_damage'],0)
                self.assertEqual([s['after_damage'] for s in stages],sorted(s['after_damage'] for s in stages))
                self.assertTrue(all(s['record_id'] and s['enemy_def']>=0 for s in stages))
    def test_kraken_uses_its_own_defence_instead_of_training_baseline(self):
        settings=core.validate_settings(dict(content_mode='anomaly',boss_id='anomaly-kraken'))
        runtime=encounters.config(settings,180)['encounter_runtime'];runtime.advance(0)
        self.assertEqual(runtime.enemy_def,4217)
        runtime.damage=1364000001;runtime.advance(1)
        self.assertEqual(runtime.enemy_def,4317)
    def test_bad_script_rejected(self):
        for e in [dict(kind='qte',start=1,duration=2,targets=[]),dict(kind='invulnerable',start=-1,duration=3),dict(kind='qte',start=1,duration=2,targets=[{'hp':-1}])]:
            with self.assertRaises(ValueError):EncounterRuntime([e])

if __name__=='__main__':unittest.main()
