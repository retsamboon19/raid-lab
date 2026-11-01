"""Disposable broker-boundary fixtures; never launch an app or native process."""
import copy
import hashlib
import io
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

import native_practice as native


def digest(value):
    return hashlib.sha256(value).hexdigest()


class NativePracticeTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.releases = self.root/'releases'
        self.jobs = self.root/'jobs'
        self.release = self.releases/'reviewed-test-release'
        self.release.mkdir(parents=True)
        self.registry = self.root/'registry.json'
        self.broker = self.root/'native_practice_job.py'
        self.broker.write_text('# disposable trusted broker contract\n')
        self.fixture = b'immutable disposable fixture'
        state = {'seed':555063220,'drawCount':'1','inext':1,'inextp':22,'seedArray':list(range(56))}
        self.expected = {'phases':{phase:{'source':{'sequence':index,'sha256':'a'*64,
            'boundary':'NK.Spot.SpotManagement::OnStart@0x76064c0','phase':phase},'state':copy.deepcopy(state)}
            for index,phase in [(18,'enter'),(19,'leave')]}}
        self.expected_bytes = json.dumps(self.expected).encode()
        self.fixture_sha,self.rng_sha = digest(self.fixture),digest(self.expected_bytes)
        for key,value in {'REGISTRY':self.registry,'RELEASES_ROOT':self.releases,'JOBS_ROOT':self.jobs,
            'BROKER':self.broker,'FIXTURE_SHA256':self.fixture_sha,'RNG_EXPECTED_SHA256':self.rng_sha}.items():
            p=patch.object(native,key,value);p.start();self.addCleanup(p.stop)
        self.write(self.release/'fixture.json',self.fixture)
        self.write(self.release/'rng.json',self.expected_bytes)
        self.staging={'fullSharedRngStateRequired':True,'sources':{'rngExpectedInput':{'sha256':self.rng_sha}}}
        self.verification=self.verified()
        self.write_json(self.release/'verification.json',self.verification)
        self.write_json(self.release/'staging.json',self.staging)
        self.manifest={'schemaVersion':1,'approved':True,'releaseId':'reviewed-test-release',
            'engine':native.ENGINE,'fixtureId':native.FIXTURE_ID,'inputSourceSha256':self.fixture_sha,
            'clientSha256':native.CLIENT_SHA256,'resultSchema':native.RESULT_SCHEMA,
            'packetBasename':'practice15-original-result.pb',
            'fixtureFile':'fixture.json','rngExpectedFile':'rng.json','nativeValidation':{
                'receiptFile':'verification.json','receiptSha256':native._hash(self.release/'verification.json'),
                'stagingFile':'staging.json','stagingSha256':native._hash(self.release/'staging.json')}}
        self.publish()
        self.request={'engine':native.ENGINE,'fixtureId':native.FIXTURE_ID,
            'inputSourceSha256':self.fixture_sha,'releaseId':'reviewed-test-release'}
        self.job='1'*24

    def write(self,path,data):
        path.parent.mkdir(parents=True,exist_ok=True);path.write_bytes(data)

    def write_json(self,path,value):
        self.write(path,json.dumps(value).encode())

    def publish(self):
        self.write_json(self.release/'manifest.json',self.manifest)
        self.manifest_sha=native._hash(self.release/'manifest.json')
        self.write_json(self.registry,{'schemaVersion':1,'releases':{'reviewed-test-release':{
            'manifestSha256':self.manifest_sha,'brokerSha256':native._hash(self.broker)}}})

    def verified(self):
        return {'status':'passed','exitCode':0,'timedOut':False,'frozenSourceInputsUnchanged':{'probe':True},
            'originalPacketExportVerified':True,'requiredPreferenceStorageControlsPassed':True,'completeBattle':True,
            'requiredFullSharedRngStateVerified':True,'fullSharedRngStateVerification':{
                'status':'passed','required':True,'errors':[],'expectedFileSha256':self.rng_sha,
                'referenceRunIndex':1,'observedBoundaries':2,'readFailures':[],
                'all56ElementsComparedAtEachOriginalBoundary':True,'rngStateWritten':False,'rngMethodsInvoked':False},
            'fullSharedRngStateObservations':[{'status':'original_practice_full_shared_rng_observed',
                'boundaryPhase':phase,'passed':True,'expectedFileSha256':self.rng_sha,'referenceRunIndex':1,
                'source':copy.deepcopy(self.expected['phases'][phase]['source']),
                'actual':copy.deepcopy(self.expected['phases'][phase]['state']),
                'mismatchFields':[],'mismatchArrayIndices':[],'comparedArrayElements':56,
                'rngStateWritten':False,'rngMethodsInvoked':False,'sameOriginalOnStartBoundary':True}
                for phase in ('enter','leave')]}

    def broker_output(self):
        output=self.jobs/self.job/'output';output.mkdir(parents=True)
        packet=output/self.manifest['packetBasename'];packet.write_bytes(b'opaque original wire bytes')
        chars=[{'slot':i,'tableId':tid,'nameCode':code,'entityId':4095+i,
            'damage':'9007199254740993','actualDamage':'9007199254740992'}
            for i,(tid,code) in enumerate(native.IDENTITIES,1)]
        verification=copy.deepcopy(self.verification)
        verification['originalPacketArtifact']={'filename':packet.name,'sha256':native._hash(packet),
            'byteLength':packet.stat().st_size,'format':'protobuf_wire','bytesRewritten':False}
        verification['terminalResults']=[{'completeBattle':True,'resultCaptured':True,'result':1,
            'inputSourceSha256':self.fixture_sha,'verification':{'passed':True,'completeNativePractice':True,
                'inputSourceSha256':self.fixture_sha,'originalResult':1},
            'originalPacketExported':True,'originalAntiCheat':{'waveId':6801001,'battleDuration':90000,
                'characterCount':5,'monsterCount':35},
            'fullAccuracyVerified':False,'rounds':[{'squadTotal':'9223372036854775807','characters':[
                {'entityId':r['entityId'],'tableId':r['tableId'],'nameCode':r['nameCode'],
                 'outgoingDamage':r['damage'],'outgoingActualDamage':r['actualDamage']} for r in chars]}]}]
        evidence={}
        decoder={'status':'passed','originalWire':{'path':str(packet),'sha256':native._hash(packet),
            'byteLength':packet.stat().st_size,'bytesRewritten':False},'typedReadback':{
                'waveId':6801001,'battleDuration':90000,'characterCount':5,'monsterCount':35,
                'characterTids':[identity[0] for identity in native.IDENTITIES]}}
        for key,value in [('verification',verification),('staging',self.staging),('decoder',decoder)]:
            p=output/(key+'.json');self.write_json(p,value)
            evidence.update({key+'Path':str(p),key+'Sha256':native._hash(p)})
        return {'schemaVersion':1,'schema':native.RESULT_SCHEMA,'engine':native.ENGINE,
            'releaseId':self.request['releaseId'],'releaseManifestSha256':self.manifest_sha,'jobId':self.job,
            'fixtureId':native.FIXTURE_ID,'inputSourceSha256':self.fixture_sha,'clientSha256':native.CLIENT_SHA256,
            'rangeId':1,'waveId':6801001,'durationMs':90000,'nativeResult':1,'score':'9223372036854775807',
            'characters':chars,'packet':{'format':'protobuf_wire','path':str(packet),
                'sha256':native._hash(packet),'byteLength':packet.stat().st_size},
            'evidence':evidence,'fullAccuracyVerified':False}

    def fake_process(self,mutate=None,code=0,protocol=None):
        test=self
        class Process:
            waited=False
            def __init__(self,command,**kwargs):
                test.command,test.kwargs=command,kwargs
                report=test.broker_output()
                if mutate:mutate(report)
                rows=protocol if protocol is not None else [{'type':'progress','phase':'Original native battle'},
                    {'type':'result','result':report}]
                self.stdout=io.BytesIO(b''.join(json.dumps(row).encode()+b'\n' for row in rows))
                self.stderr=io.BytesIO()
                test.process=self
            def poll(self):return code
            def wait(self):self.waited=True;return code
        return Process

    def test_request_is_fixed_and_release_is_immutable(self):
        self.assertEqual(native.validate_request(self.request),self.request)
        for changes in [{'seed':1},{'members':[]},{'settings':{}},{'fixtureId':'other'},
                        {'engine':'python'},{'releaseId':'../../outside'},{'inputSourceSha256':'f'*64}]:
            with self.subTest(changes=changes),self.assertRaises(native.NativePracticeError):
                native.validate_request({**self.request,**changes})
        (self.release/'fixture.json').write_bytes(b'edited fixture')
        with self.assertRaisesRegex(native.NativePracticeError,'hash does not match'):
            native.validate_request(self.request)

    def test_default_or_unknown_release_is_explicitly_unavailable(self):
        self.registry.unlink()
        with self.assertRaises(native.NativePracticeError) as caught:native.validate_request(self.request)
        self.assertEqual(caught.exception.http_status,503)

    def test_historical_output_only_pass_is_rejected(self):
        self.write_json(self.release/'verification.json',{'status':'passed','originalPacketExportVerified':True,
            'requiredPreferenceStorageControlsPassed':True,'completeBattle':True})
        self.manifest['nativeValidation']['receiptSha256']=native._hash(self.release/'verification.json');self.publish()
        with self.assertRaises(native.NativePracticeError) as caught:native.validate_request(self.request)
        self.assertEqual(caught.exception.code,'native_rng_gate_failed')

    def test_shared_gate_checks_full_state_and_strict_int64_string(self):
        for change in [lambda r:r['actual'].__setitem__('drawCount','0'),
                       lambda r:r['actual'].__setitem__('drawCount',1),
                       lambda r:r['actual']['seedArray'].__setitem__(55,999),
                       lambda r:r['source'].__setitem__('sequence',99)]:
            v=copy.deepcopy(self.verification);change(v['fullSharedRngStateObservations'][0])
            with self.assertRaises(native.NativePracticeError):native._shared_rng_gate(v,self.staging,self.expected)
        reversed_order=copy.deepcopy(self.verification)
        reversed_order['fullSharedRngStateObservations'].reverse()
        with self.assertRaises(native.NativePracticeError):native._shared_rng_gate(reversed_order,self.staging,self.expected)

    def test_changed_broker_cannot_launch(self):
        self.broker.write_text('# changed')
        with patch.object(native.subprocess,'Popen') as launch,self.assertRaises(native.NativePracticeError):
            native.run_fixed_practice(self.request,job_id=self.job)
        launch.assert_not_called()

    def test_success_transports_exact_strings_and_trusted_argv(self):
        with patch.object(native.subprocess,'Popen',self.fake_process()):
            report=native.run_fixed_practice(self.request,job_id=self.job)
        self.assertEqual(report['score'],'9223372036854775807')
        self.assertEqual(report['characters'][0]['damage'],'9007199254740993')
        self.assertFalse(report['fullAccuracyVerified'])
        self.assertIn('--job-id',self.command);self.assertIn(self.job,self.command)
        self.assertEqual(self.command[:3],[native.sys.executable,'-I',str(self.broker)])
        self.assertFalse(self.kwargs['shell']);self.assertEqual(self.kwargs['stdin'],native.subprocess.DEVNULL)
        self.assertTrue(self.process.waited)

    def test_no_cached_result_reuse(self):
        (self.jobs/self.job).mkdir(parents=True)
        with patch.object(native.subprocess,'Popen') as launch,self.assertRaises(native.NativePracticeError):
            native.run_fixed_practice(self.request,job_id=self.job)
        launch.assert_not_called()

    def test_wrong_numeric_or_legacy_output_is_not_success(self):
        for index,mutate in enumerate([lambda r:r.__setitem__('score',9007199254740993),
            lambda r:r.__setitem__('nativeResult',2),lambda r:r.__setitem__('total',123),
            lambda r:r['characters'][0].__setitem__('tableId',1),
            lambda r:r['packet'].__setitem__('sha256','0'*64)]):
            self.job=f'{index+10:024x}'
            with self.subTest(index=index),patch.object(native.subprocess,'Popen',self.fake_process(mutate)),self.assertRaises(native.NativePracticeError):
                native.run_fixed_practice(self.request,job_id=self.job)
            self.assertTrue(self.process.waited)

    def test_cancellation_waits_for_broker_and_preserves_evidence(self):
        count=0
        def cancel():
            nonlocal count
            count+=1;return count>1
        with patch.object(native.subprocess,'Popen',self.fake_process()),self.assertRaises(native.NativePracticeCancelled) as caught:
            native.run_fixed_practice(self.request,cancel=cancel,job_id=self.job)
        self.assertTrue(self.process.waited)
        self.assertTrue(Path(caught.exception.evidence['verificationPath']).is_file())

    def test_cross_packet_decode_or_unverified_export_is_rejected(self):
        changes=[('decoder',lambda d:d['originalWire'].__setitem__('sha256','f'*64)),
            ('decoder',lambda d:d['originalWire'].__setitem__('byteLength',1)),
            ('decoder',lambda d:d['originalWire'].__setitem__('path',str(self.root/'prior-job.pb'))),
            ('verification',lambda v:v.__setitem__('requiredPreferenceStorageControlsPassed',False)),
            ('verification',lambda v:v['originalPacketArtifact'].__setitem__('sha256','f'*64)),
            ('verification',lambda v:v['terminalResults'][0].__setitem__('originalPacketExported',False))]
        for index,(key,change) in enumerate(changes):
            self.job=f'{index+30:024x}'
            def mutate(report):
                path=Path(report['evidence'][key+'Path']);data=json.loads(path.read_text());change(data)
                self.write_json(path,data);report['evidence'][key+'Sha256']=native._hash(path)
            with self.subTest(index=index),patch.object(native.subprocess,'Popen',self.fake_process(mutate)),self.assertRaises(native.NativePracticeError):
                native.run_fixed_practice(self.request,job_id=self.job)
            self.assertTrue(self.process.waited)

    def test_before_launch_cancellation_does_not_start_broker(self):
        with patch.object(native.subprocess,'Popen') as launch,self.assertRaises(native.NativePracticeCancelled):
            native.run_fixed_practice(self.request,cancel=lambda:True,job_id=self.job)
        launch.assert_not_called()

    def test_progress_failure_waits_for_closure(self):
        def progress(**kwargs):raise RuntimeError('queue unavailable')
        with patch.object(native.subprocess,'Popen',self.fake_process()),self.assertRaises(native.NativePracticeError) as caught:
            native.run_fixed_practice(self.request,progress=progress,job_id=self.job)
        self.assertEqual(caught.exception.code,'native_broker_protocol');self.assertTrue(self.process.waited)

    def test_busy_and_nonzero_exit_are_explicit(self):
        with patch.object(native.subprocess,'Popen',self.fake_process(protocol=[{'type':'error','code':'runner_busy','error':'Runner busy'}])),self.assertRaises(native.NativePracticeError) as caught:
            native.run_fixed_practice(self.request,job_id=self.job)
        self.assertEqual(caught.exception.code,'runner_busy')
        self.job='2'*24
        with patch.object(native.subprocess,'Popen',self.fake_process(code=3)),self.assertRaises(native.NativePracticeError) as caught:
            native.run_fixed_practice(self.request,job_id=self.job)
        self.assertEqual(caught.exception.code,'native_broker_failed')


if __name__=='__main__':unittest.main()
