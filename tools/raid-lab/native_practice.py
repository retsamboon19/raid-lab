"""Transport one approved fixed original153 practice run; no combat fallback.

Disabled until the machine owner publishes private/native-practice-releases.json:
  {"schemaVersion":1,"releases":{ID:{"manifestSha256":SHA,"brokerSha256":SHA}}}
Paths are fixed below; requests never supply paths, executables or argv.
The pinned release manifest must contain schemaVersion1, approved:true,
releaseId/engine/fixtureId/inputSourceSha256/clientSha256/resultSchema bindings,
fixtureFile, rngExpectedFile, packetBasename (practiceN-original-result.pb),
and nativeValidation:{receiptFile,receiptSha256,
stagingFile,stagingSha256}. File paths are relative inside its release directory.
The fixture and full original shared-RNG expected file have fixed content hashes.
Both release admission and each fresh job require the archiver's full shared
OnStart enter/leave gate. Export-only historical14 is not an admitted release.
Per-entity and Unity RNG states were not captured and are not certified here.

Trusted broker argv (shell=False; current Python -I):
  native_practice_job.py --release-manifest PATH --manifest-sha256 SHA
    --job-id 24hex --fixture-id captured-fire90-run1
    --input-source-sha256 SHA --result-schema native-practice-v1
Broker owns the exclusive lease, private desktop/job, <=60s native host bound,
source/isolation witnesses, original output, independent decode and fresh archive.
stdout is UTF8 JSONL, <=256KiB/line and <=1MiB total: {type:'progress',phase},
then exactly one {type:'result',result:REPORT} or {type:'error',code,error}.
REPORT's schema is checked below; original damage values must be decimal strings.
The broker must wait for actual child closure before exiting. Cancellation here
waits for that bounded completion and preserves evidence; it never kills Unity.
No broker/release is bundled or enabled by this module.
"""
from __future__ import annotations

import hashlib
import json
import queue
import re
import secrets
import subprocess
import sys
import threading
from pathlib import Path

ROOT = Path(__file__).resolve().parent
OFFLINE_ROOT = Path('I:/Nikke offline')
SERVICE_ROOT = OFFLINE_ROOT / 'tools/raid-lab/private/native-player153-20261101/native-service'
RELEASES_ROOT = SERVICE_ROOT / 'releases'
JOBS_ROOT = SERVICE_ROOT / 'jobs'
REGISTRY = ROOT / 'private/native-practice-releases.json'
BROKER = OFFLINE_ROOT / 'tools/raid-lab/native_practice_job.py'
ENGINE = 'original153'
FIXTURE_ID = 'captured-fire90-run1'
FIXTURE_SHA256 = '9660b4f952fbc86228d7537b3d8d59838d98cc8138aed5812d696dac7169f8c7'
CLIENT_SHA256 = 'd39896d3770888039c728a1908448c3db5efa7cdf874c90d56f46d8d566428d2'
RNG_EXPECTED_SHA256 = '214742a251316375b8b2e3527d97df9150ee2039238fc3042ed358cb5183bb55'
RESULT_SCHEMA = 'native-practice-v1'
IDENTITIES = [(301701,5169),(141207,5134),(110109,5024),(319111,5004),(422205,5041)]
HEX = re.compile(r'[a-f0-9]{64}\Z')
RELEASE_ID = re.compile(r'[a-z0-9][a-z0-9_-]{0,79}\Z')
JOB_ID = re.compile(r'[a-f0-9]{24}\Z')
DECIMAL = re.compile(r'(?:0|[1-9][0-9]*)\Z')


class NativePracticeError(RuntimeError):
    def __init__(self, code, message, http_status=503):
        super().__init__(message)
        self.code, self.http_status = code, http_status


class NativePracticeCancelled(InterruptedError):
    def __init__(self, job_id, evidence=None):
        super().__init__('Native practice cancelled; any started run closed and its evidence was retained.')
        self.job_id, self.evidence = job_id, evidence


def _error(code, message, status=503):
    raise NativePracticeError(code, message, status)


def _hash(path):
    with path.open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()


def _json(path):
    if not path.is_file() or path.stat().st_size > 4_000_000:
        _error('native_release_unavailable', 'Native release evidence is missing or oversized.')
    try:
        value = json.loads(path.read_text(encoding='utf-8'), parse_constant=lambda _: (_ for _ in ()).throw(ValueError()))
    except (ValueError, UnicodeError):
        _error('native_evidence_invalid', 'Native evidence is not valid JSON.')
    if not isinstance(value, dict):
        _error('native_evidence_invalid', 'Native evidence must be an object.')
    return value


def _inside(base, relative):
    if not isinstance(relative, str) or not relative or ':' in relative or Path(relative).is_absolute():
        _error('native_evidence_invalid', 'Native release file path is invalid.')
    path = (base / relative).resolve()
    if not path.is_relative_to(base.resolve()):
        _error('native_evidence_invalid', 'Native evidence escapes its release directory.')
    return path


def _bound_file(base, relative, expected):
    path = _inside(base, relative)
    if not isinstance(expected, str) or not HEX.fullmatch(expected) or not path.is_file() or _hash(path) != expected:
        _error('native_source_mismatch', 'Native release/evidence file hash does not match.')
    return path


def _payload(payload):
    if not isinstance(payload, dict) or set(payload) != {'engine','fixtureId','inputSourceSha256','releaseId'}:
        _error('unsupported_native_input', 'Select the fixed native fixture and release; team/build/settings overrides are unsupported.', 400)
    if payload['engine'] != ENGINE or payload['fixtureId'] != FIXTURE_ID or payload['inputSourceSha256'] != FIXTURE_SHA256:
        _error('unsupported_native_input', 'This request is not the captured original153 Fire/Short90s fixture.', 400)
    if not isinstance(payload['releaseId'], str) or not RELEASE_ID.fullmatch(payload['releaseId']):
        _error('unsupported_native_input', 'Invalid native release identifier.', 400)
    return dict(payload)


def _shared_rng_gate(verification, staging, expected):
    """Check the existing archiver's shared-only full-state gate, not RNG math."""
    gate = verification.get('fullSharedRngStateVerification') or {}
    if (verification.get('requiredFullSharedRngStateVerified') is not True or
        gate.get('status') != 'passed' or gate.get('required') is not True or gate.get('errors') != [] or
        gate.get('expectedFileSha256') != RNG_EXPECTED_SHA256 or gate.get('referenceRunIndex') != 1 or
        gate.get('observedBoundaries') != 2 or gate.get('readFailures') != [] or
        gate.get('all56ElementsComparedAtEachOriginalBoundary') is not True or
        gate.get('rngStateWritten') is not False or gate.get('rngMethodsInvoked') is not False or
        staging.get('fullSharedRngStateRequired') is not True or
        (staging.get('sources', {}).get('rngExpectedInput') or {}).get('sha256') != RNG_EXPECTED_SHA256):
        _error('native_rng_gate_failed', 'The release/job lacks the required original full shared-RNG boundary gate.')
    observations = verification.get('fullSharedRngStateObservations')
    if (not isinstance(observations, list) or len(observations) != 2 or
        [row.get('boundaryPhase') for row in observations] != ['enter','leave']):
        _error('native_rng_gate_failed', 'Both original shared-RNG boundary observations are required.')
    phases = set()
    for row in observations:
        phase = row.get('boundaryPhase')
        if phase not in ('enter','leave') or phase in phases:
            _error('native_rng_gate_failed', 'Original shared-RNG boundaries are duplicated or missing.')
        phases.add(phase)
        wanted = expected.get('phases', {}).get(phase) or {}
        actual = row.get('actual') or {}
        if (row.get('status') != 'original_practice_full_shared_rng_observed' or row.get('passed') is not True or
            row.get('expectedFileSha256') != RNG_EXPECTED_SHA256 or row.get('referenceRunIndex') != 1 or
            row.get('comparedArrayElements') != 56 or row.get('mismatchFields') != [] or
            row.get('mismatchArrayIndices') != [] or row.get('rngStateWritten') is not False or
            row.get('rngMethodsInvoked') is not False or row.get('sameOriginalOnStartBoundary') is not True or
            row.get('source') != wanted.get('source') or actual != wanted.get('state') or
            actual.get('drawCount') != '1' or
            any(type(actual.get(key)) is not int for key in ('seed','inext','inextp')) or
            not isinstance(actual.get('seedArray'), list) or len(actual['seedArray']) != 56 or
            any(type(value) is not int or not -2147483648 <= value <= 2147483647 for value in actual['seedArray'])):
            _error('native_rng_gate_failed', 'Original shared-RNG source/full56/Int64 state does not match the captured boundary.')


def _release(request):
    registry = _json(REGISTRY)
    entry = (registry.get('releases') or {}).get(request['releaseId']) if registry.get('schemaVersion') == 1 else None
    if not isinstance(entry, dict):
        _error('native_release_unavailable', 'This native release is unavailable or has not been approved.')
    directory = RELEASES_ROOT / request['releaseId']
    if not directory.resolve().is_relative_to(RELEASES_ROOT.resolve()):
        _error('native_source_mismatch', 'Native release directory escapes the approved release root.')
    manifest_path = _bound_file(directory, 'manifest.json', entry.get('manifestSha256'))
    manifest = _json(manifest_path)
    bindings = {'schemaVersion':1,'approved':True,'releaseId':request['releaseId'],'engine':ENGINE,
        'fixtureId':FIXTURE_ID,'inputSourceSha256':FIXTURE_SHA256,'clientSha256':CLIENT_SHA256,'resultSchema':RESULT_SCHEMA}
    if any(type(manifest.get(k)) is not type(v) or manifest.get(k) != v for k,v in bindings.items()):
        _error('native_release_unavailable', 'Native release bindings/approval are invalid.')
    packet_basename = manifest.get('packetBasename')
    if not isinstance(packet_basename,str) or not re.fullmatch(r'practice[1-9][0-9]{0,3}-original-result\.pb',packet_basename):
        _error('native_release_unavailable', 'Native release output basename is not immutable/valid.')
    _bound_file(directory, manifest.get('fixtureFile'), FIXTURE_SHA256)
    expected_path = _bound_file(directory, manifest.get('rngExpectedFile'), RNG_EXPECTED_SHA256)
    validation = manifest.get('nativeValidation') or {}
    verification = _json(_bound_file(directory, validation.get('receiptFile'), validation.get('receiptSha256')))
    staging = _json(_bound_file(directory, validation.get('stagingFile'), validation.get('stagingSha256')))
    if verification.get('status') != 'passed' or any(verification.get(key) is not True for key in
        ('originalPacketExportVerified','requiredPreferenceStorageControlsPassed','completeBattle')):
        _error('native_release_unavailable', 'Native release validation has not passed.')
    expected = _json(expected_path)
    _shared_rng_gate(verification, staging, expected)
    if not BROKER.is_file() or not isinstance(entry.get('brokerSha256'), str) or _hash(BROKER) != entry['brokerSha256']:
        _error('native_broker_unavailable', 'The approved private native broker is unavailable or changed.')
    return manifest_path, entry['manifestSha256'], expected, packet_basename


def validate_request(payload):
    request = _payload(payload)
    _release(request)
    return request


def _int64_text(value):
    return isinstance(value, str) and len(value)<=19 and DECIMAL.fullmatch(value) and int(value) <= 9223372036854775807


def _result(report, request, job_id, manifest_sha, expected, packet_basename):
    bindings = {'schemaVersion':1,'schema':RESULT_SCHEMA,'engine':ENGINE,'releaseId':request['releaseId'],
        'releaseManifestSha256':manifest_sha,'fixtureId':FIXTURE_ID,'inputSourceSha256':FIXTURE_SHA256,
        'clientSha256':CLIENT_SHA256,'jobId':job_id,'rangeId':1,'waveId':6801001,'durationMs':90000,'nativeResult':1}
    if not isinstance(report, dict) or any(type(report.get(k)) is not type(v) or report.get(k) != v for k,v in bindings.items()):
        _error('native_output_invalid', 'Native broker returned a different result/input identity.')
    if set(report)-set(bindings)-{'score','characters','packet','evidence','fullAccuracyVerified','limits'}:
        _error('native_output_invalid', 'Unsupported native result fields; legacy modeled reports are not accepted.')
    if not _int64_text(report.get('score')) or report['score'] == '0':
        _error('native_output_invalid', 'Original native score must be a positive exact Int64 decimal string.')
    characters = report.get('characters')
    if not isinstance(characters, list) or len(characters) != 5:
        _error('native_output_invalid', 'Five ordered original character results are required.')
    for index, (row, identity) in enumerate(zip(characters, IDENTITIES), 1):
        if (not isinstance(row, dict) or type(row.get('slot')) is not int or row.get('slot') != index or
            (row.get('tableId'), row.get('nameCode')) != identity or
            type(row.get('entityId')) is not int or row['entityId'] <= 0 or
            not _int64_text(row.get('damage')) or not _int64_text(row.get('actualDamage'))):
            _error('native_output_invalid', 'Original ordered character identities/Int64 fields are invalid.')
    if len({row['entityId'] for row in characters}) != 5:
        _error('native_output_invalid', 'Original result entities are duplicated.')
    output = (JOBS_ROOT / job_id / 'output').resolve()
    packet = report.get('packet') or {}
    packet_path = _bound_file(output, packet.get('path'), packet.get('sha256')) if not Path(str(packet.get('path',''))).is_absolute() else Path(packet['path']).resolve()
    wanted_packet = output / packet_basename
    if (packet_path != wanted_packet or not packet_path.is_file() or packet.get('format') != 'protobuf_wire' or
        not isinstance(packet.get('sha256'),str) or not HEX.fullmatch(packet['sha256']) or
        type(packet.get('byteLength')) is not int or not 1 <= packet['byteLength'] <= 16777216 or
        packet_path.stat().st_size != packet['byteLength'] or _hash(packet_path) != packet['sha256']):
        _error('native_output_invalid', 'Fresh original native packet path/size/hash is invalid.')
    evidence = report.get('evidence') or {}
    artifacts = {}
    for key in ('verification','decoder','staging'):
        relative = evidence.get(key+'Path')
        path = Path(relative).resolve() if isinstance(relative,str) and Path(relative).is_absolute() else _inside(output,relative)
        if not path.is_relative_to(output) or not path.is_file() or _hash(path) != evidence.get(key+'Sha256'):
            _error('native_output_invalid', 'Fresh native verification/decoder evidence does not match.')
        artifacts[key] = _json(path)
    verification = artifacts['verification']
    if (verification.get('status') != 'passed' or type(verification.get('exitCode')) is not int or
        verification['exitCode'] != 0 or verification.get('timedOut') is not False or
        any(verification.get(key) is not True for key in
            ('originalPacketExportVerified','requiredPreferenceStorageControlsPassed','completeBattle'))):
        _error('native_output_invalid', 'The fresh original native run did not pass normal completion.')
    artifact = verification.get('originalPacketArtifact') or {}
    if (artifact.get('filename') != packet_basename or artifact.get('sha256') != packet['sha256'] or
        artifact.get('byteLength') != packet['byteLength'] or artifact.get('format') != 'protobuf_wire' or
        artifact.get('bytesRewritten') is not False):
        _error('native_output_invalid', 'Native verification refers to a different packet artifact.')
    decoder = artifacts['decoder']
    decoded_wire = decoder.get('originalWire') or {}
    decoded_path = decoded_wire.get('path')
    if (not isinstance(decoded_path,str) or Path(decoded_path).resolve() != packet_path or
        decoded_wire.get('sha256') != packet['sha256'] or decoded_wire.get('byteLength') != packet['byteLength'] or
        decoded_wire.get('bytesRewritten') is not False):
        _error('native_output_invalid', 'Independent decoding is not bound to this exact fresh original packet.')
    _shared_rng_gate(verification, artifacts['staging'], expected)
    terminal = (verification.get('terminalResults') or [{}])[-1]
    rounds = terminal.get('rounds') or []
    completion = terminal.get('verification') or {}
    if (terminal.get('completeBattle') is not True or terminal.get('resultCaptured') is not True or
        terminal.get('originalPacketExported') is not True or type(terminal.get('result')) is not int or
        terminal['result'] != 1 or terminal.get('inputSourceSha256') != FIXTURE_SHA256 or
        completion.get('passed') is not True or completion.get('completeNativePractice') is not True or
        completion.get('inputSourceSha256') != FIXTURE_SHA256 or completion.get('originalResult') != 1 or
        len(rounds) != 1 or rounds[0].get('squadTotal') != report['score'] or
        terminal.get('fullAccuracyVerified') is not False or
        not verification.get('frozenSourceInputsUnchanged') or
        any(value is not True for value in verification['frozenSourceInputsUnchanged'].values()) or
        artifacts['decoder'].get('status') != 'passed'):
        _error('native_output_invalid', 'Fresh original result/export/source verification is incomplete.')
    original_packet = terminal.get('originalAntiCheat') or {}
    decoded = decoder.get('typedReadback') or {}
    if (any(original_packet.get(k) != value or decoded.get(k) != value for k,value in
        [('waveId',6801001),('battleDuration',90000),('characterCount',5)]) or
        type(original_packet.get('monsterCount')) is not int or original_packet['monsterCount'] <= 0 or
        decoded.get('monsterCount') != original_packet['monsterCount'] or
        decoded.get('characterTids') != [identity[0] for identity in IDENTITIES]):
        _error('native_output_invalid', 'Decoded original packet differs from the original terminal input/statistics.')
    native_rows = {row['entityId']:row for row in rounds[0].get('characters',[])}
    for row in characters:
        actual = native_rows.get(row['entityId']) or {}
        if any(actual.get(k) != row.get(k) for k in ('tableId','nameCode')) or actual.get('outgoingDamage') != row['damage'] or actual.get('outgoingActualDamage') != row['actualDamage']:
            _error('native_output_invalid', 'Returned character values differ from original native statistics.')
    if report.get('fullAccuracyVerified') is not False:
        _error('native_output_invalid', 'This fixed native report does not certify full accuracy.')
    return report


def run_fixed_practice(payload, progress=lambda **_:None, cancel=lambda:False, *, job_id=None):
    request = _payload(payload)
    job_id = secrets.token_hex(12) if job_id is None else job_id
    if not isinstance(job_id,str) or not JOB_ID.fullmatch(job_id):
        _error('native_job_invalid','Native job ID must be server-generated24hex.',400)
    if cancel():
        raise NativePracticeCancelled(job_id)
    manifest, manifest_sha, expected, packet_basename = _release(request)
    if (JOBS_ROOT / job_id).exists():
        _error('native_job_exists','Native job evidence already exists; previous results cannot be reused.')
    command = [sys.executable,'-I',str(BROKER),'--release-manifest',str(manifest),
        '--manifest-sha256',manifest_sha,'--job-id',job_id,'--fixture-id',FIXTURE_ID,
        '--input-source-sha256',FIXTURE_SHA256,'--result-schema',RESULT_SCHEMA]
    try:
        process = subprocess.Popen(command,stdin=subprocess.DEVNULL,stdout=subprocess.PIPE,stderr=subprocess.PIPE,
            cwd=str(BROKER.parent),shell=False,creationflags=getattr(subprocess,'CREATE_NO_WINDOW',0))
    except OSError:
        _error('native_broker_unavailable','The approved private native broker could not start.')
    messages = queue.Queue()
    def pump(stream, name):
        size = 0
        try:
            while True:
                line = stream.readline(262145)
                if not line: break
                size += len(line)
                if len(line)>262144 or size>1048576:
                    messages.put(('fault','Native broker output exceeded its protocol bound.'))
                    while stream.read(8192): pass
                    break
                if name == 'stdout': messages.put(('line',line))
        except Exception:
            messages.put(('fault','Native broker output could not be read.'))
        finally:
            try: stream.close()
            finally: messages.put(('closed',name))
    threads = [threading.Thread(target=pump,args=(stream,name),daemon=True)
        for stream,name in [(process.stdout,'stdout'),(process.stderr,'stderr')]]
    for thread in threads: thread.start()
    closed, final, fault, cancelled = set(), None, None, False
    def notify(phase):
        nonlocal fault
        try: progress(phase=phase)
        except Exception: fault = 'Native job progress transport failed; evidence was retained after closure.'
    while len(closed)<2 or process.poll() is None:
        try: requested_cancel = cancel()
        except Exception:
            requested_cancel = False
            fault = 'Native job cancellation transport failed; evidence was retained after closure.'
        if requested_cancel and not cancelled:
            cancelled = True
            notify('Cancellation requested; waiting for the current battle to finish.')
        try: kind, value = messages.get(timeout=.1)
        except queue.Empty: continue
        if kind == 'closed': closed.add(value); continue
        if kind == 'fault': fault = value; continue
        try:
            row = json.loads(value.decode('utf-8'),parse_constant=lambda _: (_ for _ in ()).throw(ValueError()))
            if not isinstance(row,dict): raise ValueError()
            if row.get('type') == 'progress':
                phase = row.get('phase')
                if not isinstance(phase,str) or not 1<=len(phase)<=200: raise ValueError()
                notify(phase)
            elif row.get('type') in ('result','error') and final is None:
                final = row
            else: raise ValueError()
        except (ValueError,UnicodeError): fault = 'Native broker returned an invalid or repeated protocol message.'
    for thread in threads: thread.join()
    code = process.wait()
    if fault: _error('native_broker_protocol',fault)
    if final and final.get('type') == 'error':
        error_code = final.get('code')
        if not isinstance(error_code,str) or not re.fullmatch(r'[a-z_]{1,64}',error_code): error_code='native_broker_failed'
        _error(error_code,str(final.get('error') or 'Original native run failed.')[:500])
    if code != 0 or final is None:
        _error('native_broker_failed','Native broker exited without a verified original result.')
    result = _result(final.get('result'),request,job_id,manifest_sha,expected,packet_basename)
    if cancelled or cancel():
        raise NativePracticeCancelled(job_id,result['evidence'])
    return result
