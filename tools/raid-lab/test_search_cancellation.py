import time
import unittest
from unittest.mock import patch,Mock
from concurrent.futures import Future
import core
from parallel_compute import CandidateExecutor


class SearchCancellationTests(unittest.TestCase):
    def search_stopped(self,teams=1,limit=False):
        stopped=False
        def fill(executor,keys,roster,settings,cache,failures,completed,cancelled):
            nonlocal stopped
            for key in list(dict.fromkeys(keys))[:min(2,teams)]:
                team,duration,detail=key
                cache[key]={'members':list(team),'duration':duration,'damage':100+len(cache),'encounter_timeline':None,'warnings':[]}
                completed()
            # An enormous incomplete screening score must never enter the result.
            cache[(('fake',),10,False)]={'members':['fake'],'damage':10**20}
            if limit:executor.deadline=time.perf_counter()-1
            else:stopped=True;raise InterruptedError('Search cancelled.')
        with patch.object(CandidateExecutor,'fill',fill):
            return core.search({'roster':core.demo_roster(),'settings':dict(boss_id='training',teams=teams,duration=180,budget=3,compute_mode='single')},cancelled=lambda:stopped)

    def test_cancel_returns_completed_recommendation(self):
        result=self.search_stopped()
        self.assertEqual(result['completion']['reason'],'cancelled')
        self.assertEqual(len(result['teams']),1)
        self.assertEqual(len(result['teams'][0]['members']),5)
        self.assertNotIn('fake',result['teams'][0]['members'])

    def test_cancel_returns_disjoint_partial_allocation(self):
        result=self.search_stopped(3)
        self.assertEqual(result['completion'],dict(reason='cancelled',requested_teams=3,returned_teams=2))
        self.assertEqual(len({n for r in result['teams'] for n in r['members']}),10)

    def test_time_limit_returns_results_without_more_work(self):
        result=self.search_stopped(limit=True)
        self.assertEqual(result['completion']['reason'],'time_limit')
        self.assertEqual(len(result['teams']),1)

    def test_cancel_before_first_result_does_not_invent_a_team(self):
        with self.assertRaisesRegex(InterruptedError,'No new recommendation'):
            core.search({'roster':core.demo_roster(),'settings':dict(boss_id='training')},cancelled=lambda:True)

    def test_cancel_harvests_finished_futures_and_terminates_others(self):
        e=CandidateExecutor('cpu',2);e.pool=Mock();e.stop=Mock();pool=e.pool
        finished=Future();finished.set_result({'damage':10})
        pending=Future();e.pool.submit.side_effect=[finished,pending]
        key=(('a',),180,True);cache={}
        with self.assertRaises(InterruptedError):
            e.fill([key,(('b',),180,True)],{},{},cache,{},Mock(),Mock(side_effect=[False,True]))
        self.assertEqual(cache[key]['damage'],10);pool.terminate_workers.assert_called_once()

    def test_cancel_retains_one_completed_aim_controller(self):
        e=CandidateExecutor('cpu',2);e.pool=Mock();e.stop=Mock();pool=e.pool
        key=(tuple('abcde'),180,True)
        finished=Future();finished.set_result(dict(members=list('abcde'),duration=180,damage=10,
            encounter_timeline=dict(simulated_until=180,critical_parts=[dict(status='passed')],off_burst_controller='a')))
        pending=Future();e.pool.submit.side_effect=[finished,pending];cache={}
        with self.assertRaises(InterruptedError):
            e.fill([key],{},dict(require_critical_parts=True),cache,{},Mock(),Mock(side_effect=[False,True]))
        self.assertEqual(cache[key]['control_comparison'][0]['unit'],'a')
        self.assertFalse(cache[key]['control_search_complete'])
        self.assertTrue(cache[key]['critical_part_requirement']['passed'])
        pool.terminate_workers.assert_called_once()


if __name__=='__main__':unittest.main()
