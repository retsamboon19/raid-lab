import unittest
import core
import encounters
from unittest.mock import patch

class EncounterTests(unittest.TestCase):
    def test_cover_validation_and_union(self):
        s=core.validate_settings(dict(duration=180,cover_seconds=10))
        self.assertEqual(s['cover_windows'],[[85,95]])
        self.assertEqual(s['uptime'],94.44)
        s=core.validate_settings(dict(duration=180,cover_mode='windows',cover_windows_text='90-95, 25-30, 28-32'))
        self.assertEqual(s['cover_seconds'],12)
        self.assertEqual(s['cover_windows'],[[25,32],[90,95]])
        self.assertEqual(encounters.config(s,30)['planned_cover_windows'],[[25,30]])
        for val in [-1,181,float('nan'),True,'bad']:
            with self.assertRaises(ValueError):core.validate_settings(dict(cover_seconds=val))
        for val in ['20-10','0-181','NaN-1','-1-10','0-0']:
            with self.assertRaises(ValueError):core.validate_settings(dict(cover_mode='windows',cover_windows_text=val))
    def test_museum_and_immutable_profiles(self):
        self.assertEqual(sum(bool(b.get('hall')) for b in encounters.BOSSES),9)
        p=core.validate_settings(dict(boss_id='museum-harvester',museum_mode='no-limit',level=999))
        self.assertFalse(p['fixed_level'])
        p=core.validate_settings(dict(boss_id='museum-harvester',museum_mode='challenge',level=999,fixed_level=False))
        self.assertTrue(p['fixed_level']);self.assertEqual(p['level'],400)
        p['encounter']['name']='Changed'
        self.assertEqual(encounters.BY_ID['museum-harvester']['name'],'Harvester')
        p=core.validate_settings(dict(boss_id='sr40',enemy_element='Water',has_parts=True,core_px=300))
        self.assertEqual(p['enemy_element'],'Wind');self.assertEqual(p['core_px'],0)
        self.assertFalse(p['has_parts'])
        with self.assertRaises(ValueError):core.validate_settings(dict(boss_id='made-up'))
    def test_manual_rejects_missing_barrier_element(self):
        rows=[r for r in core.demo_roster() if core.CAT[r['id']]['element']!='Fire'][:5]
        with self.assertRaisesRegex(ValueError,'Fire unit'):
            core.manual(dict(roster=rows,members=[r['id'] for r in rows],settings=dict(boss_id='sr40')))
    def test_cover_pauses_firing_with_timers_and_reload_running(self):
        rows=core.demo_roster()
        ids=[next(c['id'] for c in core.CATALOG if c['name']==n) for n in ['Liter','Crown','Modernia','Scarlet','Alice']]
        captured=[]
        original=core.simulate
        def capture(*a,**kw):
            result=original(*a,**kw);captured.append(result);return result
        payload=dict(roster=rows,members=ids,settings=dict(duration=60,cover_mode='windows',cover_windows_text='10-25',playstyle='assisted'))
        with patch.object(core,'simulate',capture):report=core.manual(payload)
        r=captured[0]
        in_cover=lambda t:10+1e-6<t<25-1e-6
        self.assertFalse(any(in_cover(h.t) and h.skill_name=='기본 공격' for h in r.hits))
        self.assertFalse(any(in_cover(e.t) and ('사용' in e.event or e.event=='full_burst 시작') for e in r.log.burst_log))
        self.assertTrue(any(in_cover(e.t) and e.event=='full_burst 종료' for e in r.log.burst_log))
        self.assertTrue(any(in_cover(e.t) and '완료' in e.event for e in r.log.reload_log))
        self.assertTrue(any(h.t>25 and h.skill_name=='기본 공격' for h in r.hits))
        self.assertEqual(report['teams'][0]['dps'],report['total']/60)
        self.assertEqual(report['settings']['uptime'],75)
    def test_full_cover_does_not_fire(self):
        rows=core.demo_roster();ids=[next(c['id'] for c in core.CATALOG if c['name']==n) for n in ['Liter','Crown','Modernia','Scarlet','Alice']]
        result=core.manual(dict(roster=rows,members=ids,settings=dict(duration=30,cover_seconds=30)))
        self.assertEqual(result['total'],0)
        self.assertEqual(result['teams'][0]['bursts'],0)

if __name__=='__main__':unittest.main()
