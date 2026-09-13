import unittest
from unittest.mock import patch
import core
from gpu_search import explore

class ComputeTests(unittest.TestCase):
    def test_worker_defaults_follow_available_hardware(self):
        from parallel_compute import worker_count
        for count,expected in [(1,1),(4,2),(12,6),(32,16)]:
            with patch('parallel_compute.available_cpus',return_value=count):
                self.assertEqual(worker_count(),expected)
        with patch('parallel_compute.available_cpus',return_value=32):
            self.assertEqual(worker_count('cpu',12),12)
            self.assertEqual(worker_count('gpu',1),1)

    def test_explicit_worker_limit_and_gpu_selection_are_preserved(self):
        with patch('core.worker_limit',return_value=32):
            s=core.validate_settings({'cpu_workers':12,'gpu_device':'chosen-device'})
            self.assertEqual(s['cpu_workers'],12)
            self.assertEqual(s['gpu_device'],'chosen-device')
            with self.assertRaises(ValueError):core.validate_settings({'cpu_workers':33})
            with self.assertRaises(ValueError):core.validate_settings({'cpu_workers':1.5})

    def test_modes_are_explicit_and_invalid_backend_rejected(self):
        for mode in ('cpu','gpu','single'):
            self.assertEqual(core.validate_settings({'compute_mode':mode})['compute_mode'],mode)
        with self.assertRaises(ValueError):core.validate_settings({'compute_mode':'fake-gpu'})

    def test_gpu_failure_does_not_silently_claim_cpu_work_as_gpu(self):
        with patch('gpu_search.device_info',return_value={'available':False,'reason':'test unavailable'}):
            with self.assertRaisesRegex(ValueError,'Choose CPU'):
                explore([],{}, {},{},None,None)

if __name__=='__main__':unittest.main()
