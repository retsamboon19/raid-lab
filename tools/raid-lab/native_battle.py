"""Transport selected team/build inputs to the original153 native broker.

Each request is byte-bound, composed in a fresh job and archived with its own
original packet. No Python damage or captured-team substitution is available.
"""
from __future__ import annotations

import hashlib
import importlib.util
import json
import queue
import re
import secrets
import subprocess
import sys
import threading
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent
OFFLINE_ROOT = Path('I:/Nikke offline')
SERVICE_ROOT = OFFLINE_ROOT / 'tools/raid-lab/private/native-player153-20261101/native-service'
JOBS_ROOT = SERVICE_ROOT / 'jobs'
REGISTRY = ROOT / 'private/native-battle-release.json'
BROKER = OFFLINE_ROOT / 'tools/raid-lab/native_battle_job.py'
SCHEMA = 'native-battle-v1'
ENGINE = 'original153'
CLIENT = 'd39896d3770888039c728a1908448c3db5efa7cdf874c90d56f46d8d566428d2'
HEX = re.compile(r'[a-f0-9]{64}\Z')
JOB_ID = re.compile(r'[a-f0-9]{24}\Z')
ENCOUNTER_MODULE = OFFLINE_ROOT / 'transfer/battle-parity-20261101/native153/encounters153/select_encounter153.py'


class NativeBattleError(RuntimeError):
    def __init__(self, code, message, http_status=503):
        super().__init__(message)
        self.code, self.http_status = code, http_status


class NativeBattleCancelled(InterruptedError):
    def __init__(self, job_id, evidence=None):
        super().__init__('Native battle cancelled; any started run closed and its evidence was retained.')
        self.job_id, self.evidence = job_id, evidence


def _error(code, message, status=503):
    raise NativeBattleError(code, message, status)


def _hash(path):
    with Path(path).open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()


def _canonical(value):
    return json.dumps(value, sort_keys=True, separators=(',', ':'), ensure_ascii=True, allow_nan=False).encode('utf-8')


def _json(path):
    path = Path(path)
    if not path.is_file() or path.stat().st_size > 4_000_000:
        _error('native_evidence_invalid', 'Native JSON is missing or oversized.')
    try:
        value = json.loads(path.read_text(encoding='utf-8'), parse_constant=lambda _: (_ for _ in ()).throw(ValueError()))
    except (ValueError, UnicodeError):
        _error('native_evidence_invalid', 'Native evidence is invalid JSON.')
    if not isinstance(value, dict):
        _error('native_evidence_invalid', 'Native evidence must be an object.')
    return value


def _payload(payload):
    if not isinstance(payload, dict):
        _error('unsupported_native_input', 'Select five units and their builds.', 400)
    try: encoded = _canonical(payload)
    except (TypeError, ValueError): _error('unsupported_native_input', 'Native request must contain finite JSON values.', 400)
    if len(encoded) > 2_000_000:
        _error('unsupported_native_input', 'Native request exceeds its input bound.', 400)
    members, roster = payload.get('members'), payload.get('roster')
    if not isinstance(members, list) or len(members) != 5 or any(not isinstance(x, str) or not x or len(x) > 200 for x in members) or len(set(members)) != 5:
        _error('unsupported_native_input', 'Choose exactly five different units.', 400)
    if not isinstance(roster, list) or len(roster) > 1000 or any(not isinstance(x, dict) for x in roster):
        _error('unsupported_native_input', 'The selected native team needs its roster builds.', 400)
    for member in members:
        matches = [x for x in roster if x.get('id') == member]
        if len(matches) != 1 or not isinstance(matches[0].get('build'), dict):
            _error('unsupported_native_input', 'Each selected member needs one explicit build.', 400)
    if not isinstance(payload.get('settings'), dict):
        _error('unsupported_native_input', 'Native encounter settings are required.', 400)
    return _execution_request(json.loads(encoded))



FAST60_FLAGS = {
    'native_speed_multiplier': 1, 'native_event_prefilter': True,
    'native_frame_profile': True, 'native_frame_profile_warmup_seconds': 6.5,
    'native_coherent_capture': True, 'native_render_interval': 1,
    'native_full_validation': True, 'native_js_runtime': 'v8',
    'native_startup_skip': False, 'native_clean_profile': True, 'native_fx_quality': 0,
}
# Waves the engine-side selector also accepts for accelerated60-preview (select_encounter153.py).
FAST60_WAVES = (6302006, 6302009)  # Mirror Container, Kraken

def _execution_request(request):
    settings = request['settings']
    profile = settings.get('execution_profile')
    if profile is None:
        return request  # Existing standard and explicit diagnostic requests.
    if profile not in ('standard', 'accelerated60-preview'):
        _error('unsupported_execution_profile', 'Choose Standard or Accelerated preview.', 400)
    if profile == 'standard':
        if any(key.startswith('native_') and key != 'native_viewport' for key in settings):
            _error('unsupported_execution_profile', 'Standard execution cannot include accelerated diagnostic settings.', 400)
        return request
    base = {key: value for key, value in settings.items() if key != 'execution_profile'}
    for key, value in FAST60_FLAGS.items():
        if key in base and (type(base[key]) is not type(value) or base[key] != value):
            _error('unsupported_execution_profile', 'Accelerated preview settings conflict with its fixed60 profile.', 400)
    if any(key.startswith('native_') and key not in FAST60_FLAGS and key != 'native_viewport' for key in base):
        _error('unsupported_execution_profile', 'Accelerated preview cannot include additional diagnostic settings.', 400)
    encounter = _encounters().select_encounter(base)
    if encounter.get('waveId') not in FAST60_WAVES or encounter.get('contentMode') != 'anomaly' or encounter.get('controlPolicy') != 'qte-parts-cover':
        _error('unsupported_execution_profile', 'Accelerated preview currently supports Mirror Container and Kraken with improved targeting. Use Standard for other encounters or controls.', 400)
    settings.update(FAST60_FLAGS)
    return request

def execution_profile(request):
    fast = request.get('settings', {}).get('execution_profile') == 'accelerated60-preview'
    diagnostic = not fast and any(key.startswith('native_') and key != 'native_viewport' for key in request.get('settings', {}))
    return {'id': 'accelerated60-preview' if fast else 'native-diagnostic' if diagnostic else 'standard',
            'label': 'Accelerated preview' if fast else 'Native diagnostic' if diagnostic else 'Standard',
            'originalEngine': True, 'fixedCaptureHz': 60 if request.get('settings', {}).get('native_coherent_capture') is True else None,
            'coverage': 'Mirror Container and Kraken with improved targeting; selected saved builds preserved' if fast else 'Explicit custom native diagnostic settings' if diagnostic else 'Original real-time execution',
            'accuracyScope': 'Tested on one reference team; results for other teams are not yet established' if fast else 'Accuracy is not established for every team or mode',
            'thirtySecondTargetMet': False}


def _release():
    registry = _json(REGISTRY)
    if registry.get('schemaVersion') != 1 or registry.get('engine') != 'original153' or registry.get('resultSchema') != SCHEMA:
        _error('native_release_unavailable', 'Selected-team original153 execution has no local source receipt.')
    if not HEX.fullmatch(str(registry.get('brokerSha256', ''))) or not BROKER.is_file() or _hash(BROKER) != registry['brokerSha256']:
        _error('native_broker_unavailable', 'The selected-team native broker is unavailable or changed.')
    modules = registry.get('modules')
    if not isinstance(modules, dict) or not modules or len(modules) > 64:
        _error('native_release_unavailable', 'The selected-team native source inventory is missing.')
    prefix = 'transfer/battle-parity-20261101/native153/'
    required = {prefix + name for name in (
        'custom-team/compose_native_battle153.py', 'custom-team/build_inputs153.py',
        'encounters153/select_encounter153.py', 'encounters153/encounter-catalog153.json',
        'encounters153/encounter-source153.json', 'encounters153/encounter_mode153.js',
        'encounters153/encounter_team153.js', 'encounters153/native_campaign153.js',
        'encounters153/geometry_inputs153.py', 'encounters153/tactical/native153_tactical_controller.js')}
    if not required.issubset(modules):
        _error('native_release_unavailable', 'The original encounter source inventory is incomplete.')
    for relative, digest in modules.items():
        if not isinstance(relative, str) or ':' in relative or Path(relative).is_absolute() or '..' in Path(relative).parts:
            _error('native_source_mismatch', 'Invalid custom native source path.')
        path = (OFFLINE_ROOT / relative).resolve()
        if not path.is_relative_to(OFFLINE_ROOT.resolve()) or not path.is_file() or not isinstance(digest, str) or not HEX.fullmatch(digest) or _hash(path) != digest:
            _error('native_source_mismatch', 'Selected-team native source changed.')
    return registry, _hash(REGISTRY)


def validate_request(payload):
    request = _payload(payload)
    _release()
    _encounter(request)
    return request


def _encounters():
    spec = importlib.util.spec_from_file_location('_raid_lab_native_encounters', ENCOUNTER_MODULE)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def encounter_catalog():
    _release()
    return _encounters().catalog()


def _encounter(request):
    try:
        return _encounters().select_encounter(request['settings'])
    except (ValueError, KeyError, TypeError) as error:
        _error('unsupported_native_input', str(error), 400)


def _bound_output(output, path, digest):
    if not isinstance(path, str) or not isinstance(digest, str) or not HEX.fullmatch(digest):
        _error('native_output_invalid', 'Missing native artifact path/hash.')
    resolved = Path(path).resolve() if Path(path).is_absolute() else (output / path).resolve()
    if not resolved.is_relative_to(output) or not resolved.is_file() or _hash(resolved) != digest:
        _error('native_output_invalid', 'Native artifact escaped the fresh job or changed.')
    return resolved


def _decimal(value):
    return isinstance(value, str) and len(value) <= 19 and re.fullmatch(r'0|[1-9][0-9]*', value) is not None and int(value) <= 9223372036854775807


def _result(report, request, job_id, registry, registry_sha):
    request_sha = hashlib.sha256(_canonical(request)).hexdigest()
    encounter = _encounter(request)
    bindings = {'schemaVersion': 1, 'schema': SCHEMA, 'engine': 'original153', 'jobId': job_id,
                'requestSha256': request_sha, 'customSourceReceiptSha256': registry_sha,
                'releaseId': registry['baseReleaseId'], 'releaseManifestSha256': registry['baseManifestSha256'],
                'clientSha256': CLIENT, 'encounterId': encounter['id'], 'waveId': encounter['waveId'],
                'fullAccuracyVerified': False}
    if not isinstance(report, dict) or any(type(report.get(k)) is not type(v) or report.get(k) != v for k, v in bindings.items()) or not HEX.fullmatch(str(report.get('inputSourceSha256', ''))) or not _decimal(report.get('score')):
        _error('native_output_invalid', 'Native result does not match this selected request/job.')
    if type(report.get('durationMs')) is not int or not 0 < report['durationMs'] <= encounter['timeLimit'] * 1000 + 1000 or type(report.get('nativeResult')) is not int or report['nativeResult'] not in (1, 2):
        _error('native_output_invalid', 'Original native duration/result is invalid.')
    output = (JOBS_ROOT / job_id / 'output').resolve()
    evidence = report.get('evidence') or {}; artifacts = {}
    for name in ('verification', 'decoder', 'staging', 'request'):
        path = _bound_output(output, evidence.get(name + 'Path'), evidence.get(name + 'Sha256'))
        artifacts[name] = _json(path)
    if _canonical(artifacts['request']) != _canonical(request):
        _error('native_output_invalid', 'Native evidence carries a different selected team/build.')
    verification, staging, decoder = artifacts['verification'], artifacts['staging'], artifacts['decoder']
    for key, value in [('jobId', job_id), ('requestSha256', request_sha), ('inputSourceSha256', report['inputSourceSha256']), ('customSourceReceiptSha256', registry_sha)]:
        if verification.get(key) != value or key != 'jobId' and staging.get(key) != value:
            _error('native_output_invalid', 'Custom native verification has different input provenance.')
    if verification.get('status') != 'passed' or type(verification.get('exitCode')) is not int or verification['exitCode'] != 0 or verification.get('timedOut') is not False or any(verification.get(k) is not True for k in ('completeBattle', 'requiredPreferenceStorageControlsPassed', 'resourceInputIdentitiesUnchanged', 'originalPacketExportVerified', 'normalNativeQuitRequested')) or not verification.get('frozenSourceInputsUnchanged') or any(v is not True for v in verification['frozenSourceInputsUnchanged'].values()) or verification.get('nativeFailures') != [] or verification.get('errors') != []:
        _error('native_output_invalid', 'Fresh original native completion/source/isolation gates failed.')
    if verification.get('capturedRngEqualityApplicable') is not False or verification.get('capturedRngEqualityClaimed') is not False:
        _error('native_output_invalid', 'Custom inputs cannot claim historical fixed-team RNG equality.')
    controls = verification.get('customNativeControls') or {}
    if controls.get('encounter') != encounter or report.get('encounter') != encounter or (controls.get('teamReadback') or {}).get('passed') is not True or (controls.get('controlPolicyReadback') or {}).get('controlMode') != encounter.get('controlPolicy','auto'):
        _error('native_output_invalid', 'Original selected encounter and native mode inputs differ.')
    observations = controls.get('rngObservations') or []
    if controls.get('status') != 'passed' or controls.get('requestSha256') != request_sha or controls.get('referenceCompared') is not False or controls.get('rngStateWritten') is not False or controls.get('rngMethodsInvoked') is not False or len(observations) != 2 or [x.get('boundaryPhase') for x in observations] != ['enter', 'leave'] or any(x.get('requestSha256') != request_sha or x.get('rngStateWritten') is not False or x.get('referenceCompared') is not False for x in observations) or (controls.get('fixtureReadback') or {}).get('passed') is not True or (controls.get('buildReadback') or {}).get('passed') is not True:
        _error('native_output_invalid', 'Original custom build/fixture/RNG readbacks are incomplete.')
    packet = report.get('packet') or {}
    packet_path = _bound_output(output, packet.get('path'), packet.get('sha256'))
    artifact = verification.get('originalPacketArtifact') or {}; wire = decoder.get('originalWire') or {}
    if packet.get('format') != 'protobuf_wire' or type(packet.get('byteLength')) is not int or not 1 <= packet['byteLength'] <= 16_777_216 or packet_path.stat().st_size != packet['byteLength'] or artifact.get('filename') != packet_path.name or artifact.get('sha256') != packet['sha256'] or artifact.get('byteLength') != packet['byteLength'] or artifact.get('bytesRewritten') is not False or wire.get('sha256') != packet['sha256'] or wire.get('byteLength') != packet['byteLength'] or wire.get('bytesRewritten') is not False or Path(str(wire.get('path', ''))).resolve() != packet_path or decoder.get('status') != 'passed':
        _error('native_output_invalid', 'Original packet and independent decoder bindings differ.')
    identities = staging.get('identities')
    if not isinstance(identities, list) or len(identities) != 5 or verification.get('identities') != identities:
        _error('native_output_invalid', 'Selected original character identities are absent.')
    rows = report.get('characters')
    terminal = (verification.get('terminalResults') or [{}])[-1]; rounds = terminal.get('rounds') or []
    ui_score = terminal.get('originalUiScore')
    if ui_score is not None:
        if (encounter.get('contentMode') != 'anomaly' or not isinstance(ui_score, dict)
                or not _decimal(ui_score.get('damage'))
                or ui_score.get('source') != 'BerserkContext.get_CurrentTargetDamage'
                or ui_score.get('conversion') != 'original_ACTk_ObscuredLong_op_Implicit'
                or ui_score.get('uiDestination') != 'StageResultInfoData.TotalDamage'
                or ui_score.get('capturedBeforeCleanup') is not True
                or ui_score.get('scoreCalculated') is not False
                or report.get('gameTotalDamage') != ui_score['damage']
                or report.get('gameTotalDamageSource') != ui_score):
            _error('native_output_invalid', 'Game total damage differs from the original UI score evidence.')
    elif report.get('gameTotalDamage') is not None or report.get('gameTotalDamageSource') is not None:
        _error('native_output_invalid', 'Game total damage has no original UI score evidence.')
    if len(rounds) != 1 or rounds[0].get('squadTotal') != report['score'] or terminal.get('inputSourceSha256') != report['inputSourceSha256'] or terminal.get('originalPacketExported') is not True or terminal.get('statisticsAndPacketCapturedBeforeCleanup') is not True or (terminal.get('verification') or {}).get('passed') is not True:
        _error('native_output_invalid', 'Returned score is not the original selected-input score.')
    native_rows = rounds[0].get('characters') or []
    if report.get('nativeOutcome') != {key: terminal.get(key) for key in ('spotResult','timeout','targetRemainHp','targetMaxHp','survivingPlayerCount','deadListCount')} or report.get('tactical') != terminal.get('tactical'):
        _error('native_output_invalid', 'Original outcome or control observations differ from archived native evidence.')
    if not isinstance(rows, list) or len(rows) != 5 or len(native_rows) != 5:
        _error('native_output_invalid', 'Five native character results are required.')
    for slot, (row, identity) in enumerate(zip(rows, identities), 1):
        if not isinstance(row, dict) or row.get('slot') != slot or [row.get('tableId'), row.get('nameCode')] != identity or type(row.get('entityId')) is not int or row['entityId'] <= 0 or not _decimal(row.get('damage')) or not _decimal(row.get('actualDamage')):
            _error('native_output_invalid', 'Native ordered character result is invalid.')
        matches = [x for x in native_rows if x.get('entityId') == row['entityId']]
        if len(matches) != 1 or any(matches[0].get(k) != row.get(k) for k in ('tableId', 'nameCode')) or matches[0].get('outgoingDamage') != row['damage'] or matches[0].get('outgoingActualDamage') != row['actualDamage']:
            _error('native_output_invalid', 'Returned damage differs from original statistics.')
    if len({x['entityId'] for x in rows}) != 5:
        _error('native_output_invalid', 'Duplicate original character entities.')
    decoded = decoder.get('typedReadback') or {}; anti = terminal.get('originalAntiCheat') or {}
    decoded_tids = decoded.get('characterTids')
    # The original protobuf collection need not serialize in team slot order.
    # Slot order is checked against original team/actor readbacks above; the
    # independent decoder's own identity contract compares the five IDs as a set.
    if not isinstance(decoded_tids, list) or len(decoded_tids) != 5 or any(type(value) is not int for value in decoded_tids) or sorted(decoded_tids) != sorted(x[0] for x in identities) or any(decoded.get(k) != v or anti.get(k) != v for k, v in [('waveId', encounter['waveId']), ('battleDuration', report['durationMs']), ('characterCount', 5)]) or decoded.get('monsterCount') != anti.get('monsterCount'):
        _error('native_output_invalid', 'Decoded packet is not the selected native team/encounter.')
    return report


def run_battle(payload, progress=lambda **_:None, cancel=lambda:False, *, job_id=None):
    started = time.monotonic()
    request = _payload(payload)
    job_id = secrets.token_hex(12) if job_id is None else job_id
    if not isinstance(job_id,str) or not JOB_ID.fullmatch(job_id):
        _error('native_job_invalid','Native job ID must be server-generated 24hex.',400)
    if cancel():
        raise NativeBattleCancelled(job_id)
    registry, registry_sha = _release()
    if (JOBS_ROOT / job_id).exists():
        _error('native_job_exists','Native job evidence already exists; previous results cannot be reused.')
    requests = SERVICE_ROOT / 'requests'
    requests.mkdir(exist_ok=True)
    request_path = requests / (job_id + '.json')
    encoded = _canonical(request)
    try:
        with request_path.open('xb') as stream: stream.write(encoded)
    except FileExistsError:
        _error('native_job_exists','Native request evidence already exists.')
    request_sha = hashlib.sha256(encoded).hexdigest()
    command = [sys.executable,'-I',str(BROKER),'--source-receipt',str(REGISTRY),
        '--receipt-sha256',registry_sha,'--job-id',job_id,'--request-sha256',request_sha]
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
    result = _result(final.get('result'),request,job_id,registry,registry_sha)
    if cancelled or cancel():
        raise NativeBattleCancelled(job_id,result['evidence'])
    result['executionProfile'] = execution_profile(request)
    result['executionTiming'] = {'workerToVerifiedSeconds': round(time.monotonic() - started, 3), 'scope': 'Worker request processing through original packet and archive verification; API validation/queue excluded'}
    return result
