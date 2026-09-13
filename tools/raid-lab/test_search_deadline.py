import unittest
from unittest.mock import Mock,patch
from concurrent.futures import Future
from parallel_compute import CandidateExecutor

class DeadlineTests(unittest.TestCase):
    def test_deadline_terminates_inflight_work_and_preserves_completed_cache(self):
        executor=CandidateExecutor('single');executor.deadline=10
        executor.pool=Mock();executor.stop=Mock()
        unfinished=Future();executor.pool.submit.return_value=unfinished
        pool=executor.pool;cache={'verified':'kept'}
        with patch('parallel_compute.time.perf_counter',side_effect=[0,0,11,11]):
            executor.fill([('new',180,True),('queued',180,True)],{}, {},cache,{},Mock(),lambda:False)
        self.assertEqual(pool.submit.call_count,1)
        pool.terminate_workers.assert_called_once()
        self.assertEqual(cache,{'verified':'kept'})
        self.assertIsNone(executor.pool)

    def test_expired_budget_never_dispatches(self):
        executor=CandidateExecutor('single');executor.deadline=0
        with patch('parallel_compute.ProcessPoolExecutor') as pool:
            executor.fill([('new',180,True)],{}, {},{}, {},Mock(),lambda:False)
            pool.assert_not_called()

if __name__=='__main__':unittest.main()
