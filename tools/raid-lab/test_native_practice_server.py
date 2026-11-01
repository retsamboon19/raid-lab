"""In-process request/worker contracts only; no HTTP server or native launch."""
import importlib.util
import io
import json
from pathlib import Path
import queue
import sys
import threading
import types
import unittest
from unittest.mock import Mock, patch

import native_practice


class NativeServerTests(unittest.TestCase):
    def setUp(self):
        self.core=types.ModuleType('core')
        for name in ('manual','search','import_roster','validate_settings'):
            setattr(self.core,name,Mock(side_effect=AssertionError('Python combat/roster path entered')))
        stubs={name:types.ModuleType(name) for name in ('browser_connection','report_history','feedback','accounts')}
        stubs['core']=self.core
        with patch.dict(sys.modules,stubs):
            spec=importlib.util.spec_from_file_location('_native_server_contract',Path(__file__).with_name('server.py'))
            self.server=importlib.util.module_from_spec(spec);spec.loader.exec_module(self.server)
        self.request={'engine':native_practice.ENGINE,'fixtureId':native_practice.FIXTURE_ID,
            'inputSourceSha256':native_practice.FIXTURE_SHA256,'releaseId':'approved-test'}

    def post(self,path,payload):
        body=json.dumps(payload).encode()
        handler=object.__new__(self.server.Handler)
        handler.path=path;handler.rfile=io.BytesIO(body)
        handler.headers={'Host':'127.0.0.1:8766','Content-Type':'application/json','Content-Length':str(len(body))}
        answers=[];handler.send_json=lambda data,status=200:answers.append((status,data))
        handler.do_POST();return answers[-1]

    def test_native_dispatch_uses_generated_job_without_calculator_validation(self):
        process=Mock();process.is_alive.return_value=True
        with patch.object(native_practice,'validate_request',side_effect=native_practice._payload),\
             patch.object(self.server.mp,'Process',return_value=process) as create,\
             patch.object(self.server.mp,'Queue',side_effect=queue.SimpleQueue),\
             patch.object(self.server.mp,'Event',side_effect=threading.Event):
            status,data=self.post('/api/native/practice',self.request)
        self.assertEqual(status,202);self.assertRegex(data['id'],r'^[a-f0-9]{24}$')
        args=create.call_args.kwargs['args']
        self.assertEqual(args[0],self.request);self.assertEqual(args[1],'native_practice');self.assertEqual(args[4],data['id'])
        self.assertFalse(create.call_args.kwargs['daemon']);process.start.assert_called_once()
        self.core.manual.assert_not_called();self.core.search.assert_not_called()
        self.core.import_roster.assert_not_called();self.core.validate_settings.assert_not_called()

    def test_recovery_status_returns_latest_native_only_without_launching(self):
        def get_status():
            handler=object.__new__(self.server.Handler)
            handler.path='/api/native/practice/status';handler.headers={'Host':'127.0.0.1:8766'}
            answers=[];handler.send_json=lambda data,status=200:answers.append((status,data))
            handler.do_GET();return answers[-1]
        with patch.object(self.server.mp,'Process') as create:
            self.assertEqual(get_status(),(200,{'job':None}))
            for token,kind in [('a'*24,'native_practice'),('b'*24,'native_practice'),('c'*24,'manual')]:
                self.server.JOBS[token]={'kind':kind,'state':{'status':'done','phase':'Finished'},
                    'queue':queue.SimpleQueue(),'process':Mock()}
            self.assertEqual(get_status(),(200,{'job':{'id':'b'*24,'status':'done','phase':'Finished'}}))
            create.assert_not_called()
        self.core.manual.assert_not_called();self.core.search.assert_not_called()

    def test_unsupported_override_is_rejected_before_worker(self):
        with patch.object(native_practice,'validate_request',side_effect=native_practice._payload),\
             patch.object(self.server.mp,'Process') as create:
            status,data=self.post('/api/native/practice',{**self.request,'members':['edited']})
        self.assertEqual(status,400);self.assertEqual(data['code'],'unsupported_native_input');create.assert_not_called()

    def test_unavailable_broker_release_is_explicit_503(self):
        error=native_practice.NativePracticeError('native_broker_unavailable','Broker is unavailable')
        with patch.object(native_practice,'validate_request',side_effect=error),patch.object(self.server.mp,'Process') as create:
            status,data=self.post('/api/native/practice',self.request)
        self.assertEqual(status,503);self.assertEqual(data['code'],error.code);create.assert_not_called()

    def test_native_worker_never_uses_legacy_history_or_combat(self):
        events=queue.SimpleQueue();cancel=threading.Event();result={'schema':'native-practice-v1','score':'9007199254740993'}
        def native(payload,progress,cancelled,*,job_id):
            self.assertEqual(payload,self.request);self.assertEqual(job_id,'a'*24)
            self.assertFalse(cancelled());progress(phase='Original battle');return result
        with patch.object(native_practice,'run_fixed_practice',side_effect=native),\
             patch.object(self.server,'history_store',side_effect=AssertionError('legacy history entered')):
            self.server.worker(self.request,'native_practice',events,cancel,'a'*24)
        self.assertEqual(events.get_nowait(),{'status':'running','phase':'Original battle'})
        self.assertEqual(events.get_nowait(),{'status':'done','result':result})
        self.core.manual.assert_not_called();self.core.search.assert_not_called()

    def test_native_failure_and_cancellation_keep_distinct_states(self):
        for error in [native_practice.NativePracticeError('runner_busy','busy'),
                      native_practice.NativePracticeCancelled('b'*24,{'verificationPath':'retained'})]:
            events=queue.SimpleQueue()
            with patch.object(native_practice,'run_fixed_practice',side_effect=error):
                self.server.worker(self.request,'native_practice',events,threading.Event(),'b'*24)
            row=events.get_nowait()
            self.assertEqual(row['status'],'cancelled' if isinstance(error,InterruptedError) else 'error')
            if isinstance(error,InterruptedError):self.assertEqual(row['nativeEvidence'],error.evidence)
            else:self.assertEqual(row['code'],'runner_busy')
        self.core.search.assert_not_called()

    def test_cancel_requests_waiting_without_terminating_native_worker(self):
        cancel=threading.Event();process=Mock()
        self.server.JOBS['c'*24]={'state':{'status':'running'},'kind':'native_practice','cancel':cancel,'process':process}
        status,data=self.post('/api/cancel/'+'c'*24,{})
        self.assertEqual(status,200);self.assertTrue(cancel.is_set());process.terminate.assert_not_called()
        self.assertEqual(self.server.JOBS['c'*24]['state']['phase'],'Cancellation requested; waiting for the current battle to finish.')

    def test_legacy_manual_worker_preserves_existing_history_path(self):
        self.core.manual.side_effect=None;self.core.manual.return_value={'teams':[]}
        history=Mock();history.save.return_value={'id':'saved'};events=queue.SimpleQueue()
        with patch.object(self.server,'history_store',return_value=history),patch.object(native_practice,'run_fixed_practice') as native:
            self.server.worker({},'manual',events,threading.Event())
        row=events.get_nowait();self.assertEqual(row['status'],'done');self.assertEqual(row['result']['history'],{'id':'saved'})
        history.save.assert_called_once();native.assert_not_called()


if __name__=='__main__':unittest.main()
