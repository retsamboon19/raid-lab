"""Per-request original153 broker; preserves the admitted fixed release unchanged.

The custom source receipt is separately pinned. Each selected squad/build is
composed into a new job's script before launch. Damage is read only from the
original terminal and independently decoded original protobuf. No Python combat.
"""
from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import re
import subprocess
import sys
from types import SimpleNamespace

ROOT = Path(__file__).resolve().parent
WORKSPACE = ROOT.parents[1]
SANDBOX = ROOT / 'private/native-player153-20261101'
SERVICE = SANDBOX / 'native-service'
REGISTRY = Path('I:/Raid Lab/tools/raid-lab/private/native-battle-release.json')
BASE_BROKER = ROOT / 'native_practice_job.py'
COMPOSER = 'transfer/battle-parity-20261101/native153/custom-team/compose_native_battle153.py'
REALTIME_HOST = 'tools/raid-lab/native_realtime_host.py'
REALTIME_SCHEDULER = 'transfer/battle-parity-20261101/native153/custom-team/native_real_time_scheduler153.js'
SCHEMA = 'native-battle-v1'
CLIENT = 'd39896d3770888039c728a1908448c3db5efa7cdf874c90d56f46d8d566428d2'
JOB = re.compile(r'[a-f0-9]{24}\Z')
HEX = re.compile(r'[a-f0-9]{64}\Z')


class BrokerError(RuntimeError):
    def __init__(self, code, message):
        super().__init__(message)
        self.code = code


def fail(code, message):
    raise BrokerError(code, message)


def sha(path):
    with Path(path).open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()


def canonical(value):
    return json.dumps(value, sort_keys=True, separators=(',', ':'), ensure_ascii=True, allow_nan=False).encode('utf-8')


def load(path, name):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


def read(path):
    if not Path(path).is_file() or Path(path).stat().st_size > 4_000_000:
        fail('native_evidence_invalid', 'Missing or oversized native JSON')
    value = json.loads(Path(path).read_text(encoding='utf-8'), parse_constant=lambda _: (_ for _ in ()).throw(ValueError()))
    if not isinstance(value, dict):
        fail('native_evidence_invalid', 'Native JSON must be an object')
    return value


# Per-file fused validation only: every file retains a fresh complete ancestor
# traversal, file/nlink/size controls and SHA. No cross-file/phase path cache.
def _verify_checked_file(b, path, digest=None):
    # Private helper: path was just returned by original b.no_links in this call.
    if not path.is_file() or path.stat().st_nlink != 1 or path.stat().st_size > 536870912:
        b.fail('native_source_mismatch', 'Required separate bounded file is missing')
    if digest is not None and (not isinstance(digest, str) or not b.HEX.fullmatch(digest) or b.sha(path) != digest):
        b.fail('native_source_mismatch', 'Native source/evidence hash differs')
    return path


def _fused_bound_inside(b, directory, relative, digest=None):
    if not isinstance(relative, str) or not relative or ':' in relative or Path(relative).is_absolute() or '..' in Path(relative).parts:
        b.fail('native_source_mismatch', 'Invalid release-relative path')
    # Resolve the base first; the final full original no_links traversal below
    # checks every base/leaf ancestor immediately before file validation.
    resolved_base = Path(directory).resolve()
    path = b.no_links(Path(directory) / relative)
    if not path.is_relative_to(resolved_base) or path == resolved_base:
        b.fail('native_source_mismatch', 'Path escapes its exact release/job directory')
    return _verify_checked_file(b, path, digest)


def _verify_frozen_runtime_fused(b, data):
    runtime = data.get('runtime') or {}
    for path, key in ((b.HOST, 'hostSha256'), (b.LEASE, 'leaseSha256'), (b.HARNESS, 'harnessSha256')):
        b.bound(path, runtime.get(key))
    required = runtime.get('requiredFiles')
    if not isinstance(required, dict) or not b.REQUIRED_RUNTIME.issubset(required) or len(required) > 256:
        b.fail('native_release_unavailable', 'Original table/metadata/client dependency inventory is missing')
    if any(required.get(name) != digest for name, digest in b.REQUIRED_BUILTINS.items()):
        b.fail('native_release_unavailable', 'All four original mechanical intro builtin copies must be pinned')
    for relative, digest in required.items():
        if relative not in ('current-tables.zip', 'current-tables-provenance.json') and not relative.startswith('NIKKE/NIKKE/game/nikke_Data/'):
            b.fail('native_source_mismatch', 'Runtime dependency is outside the original private client essentials')
        _fused_bound_inside(b, b.SANDBOX, relative, digest)


def _verify_frozen_inventory_fused(release):
    b = release.base
    b.bound(release.frozen.path, release.frozen.sha)
    for relative, digest in release.data['files'].items():
        _fused_bound_inside(b, release.directory, relative, digest)
    _verify_frozen_runtime_fused(b, release.data)


RENDERED_BOOTSTRAP = 'transfer/battle-parity-20261101/native153/kraken-circle-repair-20261104/rendered-bootstrap/nikkeBase.dll'


def restore_rendered_bootstrap(state):
    if state is None or state.get('restored'):return
    b=state['base']; b.no_private_player()
    b.bound(state['originalReceipt'],state['originalReceiptSha256'])
    b.bound(state['backup'],state['originalSha256'])
    actual=sha(b.bound(state['slot']))
    if actual not in (state['originalSha256'],state['candidateSha256']):
        fail('native_bootstrap_restore_failed','Private bootstrap changed outside this job; backup and lease evidence retained')
    if actual!=state['originalSha256']:
        temporary=state['slot'].with_name('native-bootstrap-restore-'+state['jobId']+'.tmp')
        b.copy_new(state['backup'],temporary);os.replace(temporary,state['slot'])
    b.bound(state['slot'],state['originalSha256'])
    b.bound(state['originalReceipt'],state['originalReceiptSha256'])
    b.fresh_json(state['root']/'bootstrap-restored.json',{'status':'passed','originalDllSha256':state['originalSha256'],
        'originalReceiptSha256':state['originalReceiptSha256'],'originalReceiptUnchanged':True,'privatePlayerAbsent':True})
    b.bound(state['marker'],state['markerSha256']);state['marker'].unlink()
    state['restored']=True


def stage_rendered_bootstrap(release,root,config):
    # Caller owns the exclusive runner lease; this helper never starts a player.
    b=release.base;b.no_private_player()
    candidate=b.inside(WORKSPACE,RENDERED_BOOTSTRAP)
    candidate_sha=release.receipt['modules'].get(RENDERED_BOOTSTRAP)
    if not HEX.fullmatch(candidate_sha or ''):
        fail('native_source_mismatch','Rendered bootstrap must be registered in custom source inventory')
    b.bound(candidate,candidate_sha)
    slot=b.no_links(Path(config['expected_files']['nikkeBase.dll']['path']))
    if slot!=SANDBOX/'NIKKE/NIKKE/game/nikkeBase.dll':
        fail('native_source_mismatch','Rendered bootstrap destination is not the private player')
    original_sha=config['expected_files']['nikkeBase.dll']['sha256'];b.bound(slot,original_sha)
    receipt=b.no_links(Path(config['bootstrap_receipt']));original=read(receipt)
    if original.get('sandbox_root')!=str(SANDBOX) or original.get('mode')!='unity_player_bootstrap' or original.get('private_desktop_guard') is not True or original.get('artifacts',{}).get('nikkeBase.dll')!=original_sha:
        fail('native_source_mismatch','Original private bootstrap receipt differs')
    backup=root/'original-nikkeBase.dll';b.copy_new(slot,backup)
    receipt_backup=root/'original-bootstrap-receipt.json';b.copy_new(receipt,receipt_backup)
    marker=SERVICE/'bootstrap-pending.json'
    state={'base':b,'root':root,'jobId':root.name,'slot':slot,'backup':backup,'originalSha256':original_sha,
        'originalReceipt':receipt,'originalReceiptSha256':sha(receipt),'candidateSha256':candidate_sha,
        'marker':marker,'restored':False}
    record={'jobId':root.name,'originalDllSha256':original_sha,'candidateDllSha256':candidate_sha,
        'originalReceiptSha256':state['originalReceiptSha256'],'backup':str(backup),'jobRoot':str(root)}
    b.fresh_json(marker,record);state['markerSha256']=sha(marker)
    try:
        staged=dict(original);staged['artifacts']={**original['artifacts'],'nikkeBase.dll':candidate_sha}
        staged['previousBootstrapSourceSha256']=staged.pop('source_sha256',None)
        staged.update(scope='Registered request-scoped rendered bootstrap; original receipt unchanged',native_tested=False,
                      sourceEvidence=str(candidate.parent/'BUILD-RECEIPT.json'))
        local_receipt=root/'rendered-bootstrap-receipt.json';b.fresh_json(local_receipt,staged)
        temporary=slot.with_name('native-bootstrap-stage-'+root.name+'.tmp')
        b.copy_new(candidate,temporary);os.replace(temporary,slot);b.bound(slot,candidate_sha)
        config['expected_files']['nikkeBase.dll']['sha256']=candidate_sha
        config['bootstrap_receipt']=str(local_receipt)
        b.fresh_json(root/'bootstrap-staged.json',{**record,'jobLocalReceipt':str(local_receipt),'originalReceiptUnchanged':True})
        return state
    except BaseException:
        restore_rendered_bootstrap(state)
        raise


"""Functions to embed in the custom broker; no changes to the frozen broker."""


def restore_gadget_runtime(state):
    if state is None or state.get('restored'):
        return
    b = state['base']
    b.no_private_player()
    b.bound(state['marker'], state['markerSha256'])
    b.bound(state['backup'], state['originalSha256'])
    actual = sha(b.bound(state['slot']))
    if actual not in (state['originalSha256'], state['candidateSha256']):
        fail('native_gadget_restore_failed', 'Private Gadget config changed outside this job; backup and pending marker retained')
    if actual != state['originalSha256']:
        temporary = state['slot'].with_name('native-gadget-restore-' + state['jobId'] + '.tmp')
        b.copy_new(state['backup'], temporary)
        os.replace(temporary, state['slot'])
    b.bound(state['slot'], state['originalSha256'])
    receipt = state['root'] / 'gadget-runtime-restored.json'
    if not receipt.exists():
        b.fresh_json(receipt, {'status': 'passed', 'originalConfigSha256': state['originalSha256'],
                              'privatePlayerAbsent': True, 'jobId': state['jobId']})
    b.bound(state['marker'], state['markerSha256'])
    state['marker'].unlink()
    state['restored'] = True


def stage_gadget_runtime(release, root, config, request):
    requested = request.get('settings', {}).get('native_js_runtime', 'default')
    if requested not in ('default', 'v8'):
        fail('unsupported_native_input', 'Native JavaScript runtime must be default or v8')
    if requested == 'default':
        return None
    b = release.base
    b.no_private_player()
    item = config.get('diagnostic_files', {}).get('frida-gadget.config')
    if not isinstance(item, dict) or not HEX.fullmatch(item.get('sha256', '')):
        fail('native_source_mismatch', 'Original Gadget config binding missing')
    slot = b.no_links(Path(item['path']))
    if slot != SANDBOX / 'NIKKE/NIKKE/game/frida-gadget.config':
        fail('native_source_mismatch', 'Gadget runtime destination is not the private player')
    original_sha = item['sha256']
    b.bound(slot, original_sha)
    original = read(slot)
    if original.get('interaction') != {'type': 'script', 'path': 'NKAB/dist/scene-probe.js'} or original.get('runtime', 'default') not in ('default', 'qjs'):
        fail('native_source_mismatch', 'Original private Gadget script/runtime config differs')
    backup = root / 'original-frida-gadget.config'
    b.copy_new(slot, backup)
    candidate = root / 'v8-frida-gadget.config'
    b.fresh_json(candidate, {**original, 'runtime': 'v8'})
    candidate_sha = sha(candidate)
    marker = SERVICE / 'gadget-runtime-pending.json'
    state = {'base': b, 'root': root, 'jobId': root.name, 'slot': slot, 'backup': backup,
             'originalSha256': original_sha, 'candidateSha256': candidate_sha,
             'marker': marker, 'restored': False}
    record = {'jobId': root.name, 'jobRoot': str(root), 'backup': str(backup),
              'slot': str(slot), 'originalConfigSha256': original_sha,
              'candidateConfigSha256': candidate_sha, 'requestedRuntime': 'v8'}
    b.fresh_json(marker, record)
    state['markerSha256'] = sha(marker)
    try:
        temporary = slot.with_name('native-gadget-stage-' + root.name + '.tmp')
        b.copy_new(candidate, temporary)
        os.replace(temporary, slot)
        b.bound(slot, candidate_sha)
        config['diagnostic_files']['frida-gadget.config']['sha256'] = candidate_sha
        b.fresh_json(root / 'gadget-runtime-staged.json', {**record,
                     'scope': 'Request-scoped private Gadget runtime; original script interaction preserved',
                     'frozenConfigUnchanged': True})
        return state
    except BaseException:
        restore_gadget_runtime(state)
        config['diagnostic_files']['frida-gadget.config']['sha256'] = original_sha
        raise


def restore_private_runtime_overrides(bootstrap, gadget):
    """Try both independent restorations even if one fails; retain failed markers."""
    errors = []
    for restore, state in ((restore_gadget_runtime, gadget), (restore_rendered_bootstrap, bootstrap)):
        try:
            restore(state)
        except BaseException as error:
            errors.append(error)
    if errors:
        raise errors[0]


def validate_payload(request):
    if not isinstance(request, dict) or len(canonical(request)) > 2_000_000:
        fail('unsupported_native_input', 'A bounded selected team/build request is required')
    members, roster = request.get('members'), request.get('roster')
    if not isinstance(members, list) or len(members) != 5 or any(not isinstance(x, str) or not x or len(x) > 200 for x in members) or len(set(members)) != 5:
        fail('unsupported_native_input', 'Select exactly five different units')
    if not isinstance(roster, list) or len(roster) > 1000 or any(not isinstance(row, dict) for row in roster):
        fail('unsupported_native_input', 'Selected native builds require a roster')
    for member in members:
        rows = [row for row in roster if row.get('id') == member]
        if len(rows) != 1 or not isinstance(rows[0].get('build'), dict):
            fail('unsupported_native_input', 'Each selected member needs one explicit build')
    if not isinstance(request.get('settings'), dict):
        fail('unsupported_native_input', 'Native encounter settings are required')
    # The composer resolves source IDs and rejects unsupported mechanics. This
    # function preserves every original request field, including exact builds.
    return request


def load_release(receipt_path, receipt_sha):
    if Path(receipt_path).resolve() != REGISTRY.resolve() or not HEX.fullmatch(receipt_sha or '') or sha(REGISTRY) != receipt_sha:
        fail('native_source_mismatch', 'Custom native source receipt is not the pinned local registry')
    receipt = read(REGISTRY)
    if receipt.get('schemaVersion') != 1 or receipt.get('engine') != 'original153' or receipt.get('resultSchema') != SCHEMA:
        fail('native_release_unavailable', 'Custom native source receipt is unavailable')
    if sha(BASE_BROKER) != receipt.get('baseBrokerSha256') or sha(Path(__file__)) != receipt.get('brokerSha256'):
        fail('native_source_mismatch', 'Native broker source changed')
    base = load(BASE_BROKER, '_custom_battle_fixed_broker')
    rid = receipt.get('baseReleaseId')
    if not isinstance(rid, str) or not base.RELEASE_ID.fullmatch(rid):
        fail('native_release_unavailable', 'Invalid admitted base release ID')
    release = base.load_release(SERVICE / 'releases' / rid / 'manifest.json', receipt.get('baseManifestSha256'))
    modules = receipt.get('modules')
    if not isinstance(modules, dict) or COMPOSER not in modules or not 1 <= len(modules) <= 64:
        fail('native_release_unavailable', 'Custom native source inventory is incomplete')
    prefix = 'transfer/battle-parity-20261101/native153/encounters153/'
    required = {prefix + name for name in ('select_encounter153.py', 'encounter-catalog153.json',
        'encounter-source153.json', 'encounter_mode153.js', 'encounter_team153.js',
        'native_campaign153.js', 'geometry_inputs153.py', 'tactical/native153_tactical_controller.js')}
    required.update({REALTIME_HOST, REALTIME_SCHEDULER})
    if not required.issubset(modules):
        fail('native_release_unavailable', 'Original encounter source inventory is incomplete')
    for relative, digest in modules.items():
        _fused_bound_inside(base, WORKSPACE, relative, digest)
    composer = load(base.inside(WORKSPACE, COMPOSER), '_custom_battle_composer')
    # Preserve the separately admitted frozen practice host unchanged.
    realtime_host = load(base.inside(WORKSPACE, REALTIME_HOST), '_custom_real_time_native_host')
    if realtime_host.MAX_SECONDS != 390:fail('native_source_mismatch', 'Bounded original real-time host limit differs')
    return SimpleNamespace(base=base, frozen=release, receipt=receipt, receipt_sha=receipt_sha,
                           composer=composer, data=release.data, directory=release.directory,
                           file=release.file, host=realtime_host, lease_module=release.lease_module,
                           resource=release.resource, preference=release.preference, decoder=release.decoder,
                           sha=release.sha, path=release.path)


def verify_inventory(release):
    release.base.bound(REGISTRY, release.receipt_sha)
    release.base.bound(BASE_BROKER, release.receipt['baseBrokerSha256'])
    release.base.bound(Path(__file__), release.receipt['brokerSha256'])
    for relative, digest in release.receipt['modules'].items():
        _fused_bound_inside(release.base, WORKSPACE, relative, digest)
    _verify_frozen_inventory_fused(release)


def verify_staging(prepared):
    p, b = prepared, prepared.release.base
    unchanged = {}
    for group in ('sources', 'resourceReceipts'):
        inventory = p.staging.get(group)
        if not isinstance(inventory, dict) or not inventory:
            fail('native_source_mismatch', 'Per-job source/resource inventory is missing')
        for key, item in inventory.items():
            path = b.no_links(Path(item['path']))
            if path.is_relative_to(p.release.directory):
                if p.release.data['files'].get(path.relative_to(p.release.directory).as_posix()) != item['sha256']:
                    fail('native_source_mismatch', 'Frozen source is outside its exact base inventory')
            elif not path.is_relative_to(p.root):
                relative = path.relative_to(WORKSPACE).as_posix() if path.is_relative_to(WORKSPACE) else None
                if p.release.receipt['modules'].get(relative) != item['sha256']:
                    fail('native_source_mismatch', 'Custom source is not inventoried or job-local')
            _verify_checked_file(b, path, item['sha256']); unchanged[group + ':' + key] = True
    if canonical(read(p.root / 'request.json')) != canonical(p.request):
        fail('native_source_mismatch', 'Selected request changed after composition')
    fixture = (p.staging['sources'].get('customFixtureInput') or {})
    if fixture.get('sha256') != p.input_sha or not Path(fixture.get('path', '')).resolve().is_relative_to(p.root):
        fail('native_source_mismatch', 'Custom native fixture is not this job\'s source-bound input')
    fixture_value = read(Path(fixture['path']))
    if fixture_value.get('sourceKind') != 'custom_team' or fixture_value.get('requestSha256') != p.request_sha:
        fail('native_source_mismatch', 'Native fixture does not name this selected request')
    unchanged['selectedRequestAndFixture'] = True
    return unchanged


def prepare_job(receipt_path, receipt_sha, job_id, request, progress=lambda _: None):
    if not isinstance(job_id, str) or not JOB.fullmatch(job_id):
        fail('native_job_invalid', 'Server-generated 24hex job ID required')
    validate_payload(request)
    release = load_release(receipt_path, receipt_sha)
    b = release.base
    lease = release.lease_module.NativeRunnerLease(SERVICE / 'runner.lock')
    root = None; slot = None; backup = None; temporary = None; slot_replaced = False; bootstrap = None; gadget_runtime = None
    try:
        lease.acquire()
    except Exception as error:
        if type(error).__name__ == 'RunnerBusy':
            raise BrokerError('runner_busy', str(error)) from error
        raise
    try:
        b.no_private_player(); verify_inventory(release)
        if (SERVICE/'bootstrap-pending.json').exists():
            fail('native_bootstrap_restore_failed','Prior bootstrap transaction requires verified restoration before any player')
        if (SERVICE/'gadget-runtime-pending.json').exists():
            fail('native_gadget_restore_failed','Prior Gadget runtime transaction requires verified restoration before any player')
        jobs = b.no_links(SERVICE / 'jobs'); jobs.mkdir(exist_ok=True)
        root = b.inside(jobs, job_id); root.mkdir(exist_ok=False)
        request_sha = hashlib.sha256(canonical(request)).hexdigest()
        b.fresh_json(root / 'request.json', request)
        b.fresh_json(root / 'request-binding.json', {'schemaVersion': 1, 'jobId': job_id, 'requestSha256': request_sha,
                                                    'customSourceReceiptSha256': receipt_sha, 'baseReleaseManifestSha256': release.sha})
        composition = release.composer.compose_custom_job(release.frozen, request, root)
        bundle = b.bound(Path(composition['bundlePath']))
        if not bundle.is_relative_to(root):
            fail('native_source_mismatch', 'Custom script must be a fresh per-job artifact')
        identities = composition['identities']
        if not isinstance(identities, list) or len(identities) != 5 or any(not isinstance(x, (list, tuple)) or len(x) != 2 or any(type(v) is not int or v <= 0 for v in x) for x in identities) or len({tuple(x) for x in identities}) != 5:
            fail('native_source_mismatch', 'Five source-resolved ordered character identities required')
        input_sha = composition['inputSourceSha256']
        if not isinstance(input_sha, str) or not HEX.fullmatch(input_sha):
            fail('native_source_mismatch', 'Custom fixture hash required')
        staging = composition['staging']
        staging.update({'requestSha256': request_sha, 'inputSourceSha256': input_sha,
                        'customSourceReceiptSha256': receipt_sha, 'identities': identities,
                        'fullSharedRngStateRequired': False, 'capturedRngEqualityApplicable': False})
        p = SimpleNamespace(release=release, lease=lease, root=root, game=SANDBOX / 'NIKKE/NIKKE/game', job_id=job_id,
                            request=request, request_sha=request_sha, input_sha=input_sha, identities=identities,
                            staging=staging, mode=composition['mode'], encounter=composition['encounter'], progress=progress,
                            bundle=bundle, bundle_sha=sha(bundle), host_result=None, executed=False, collected=False)
        verify_staging(p)
        pre_resources = b.resource_witness(release.frozen, staging); pre_preferences = b.preference_witness(release.frozen)
        p.pre_resources, p.pre_preferences = pre_resources, pre_preferences
        if any((p.game / b.SLOT).parent.glob('native-service-*.tmp')) or any(SERVICE.glob('shared-artifacts-*.tmp')):
            fail('native_unarchived_artifact', 'Unfinished prior shared-slot/archive transaction remains')
        ledger_path = SERVICE / 'shared-artifacts.json'
        p.ledger_before_sha = sha(b.bound(ledger_path)) if ledger_path.exists() else None
        ledger = b.read_json(ledger_path)['artifacts'] if ledger_path.exists() else release.data.get('initialSharedArtifacts', {})
        current = b.shared_files(p.game)
        for name, source in current.items():
            if name not in ledger:
                fail('native_unarchived_artifact', 'Unknown shared artifact: ' + name)
            b.archived_entry(ledger[name], source)
        b.fresh_json(root / 'shared-before.json', {'artifacts': ledger})
        b.fresh_json(root / 'resource-pre.json', pre_resources); b.fresh_json(root / 'preferences-pre.json', pre_preferences)
        cleaned = []
        for name, source in current.items():
            if name == b.SLOT: continue
            b.archived_entry(ledger[name], source); source.unlink(); cleaned.append(name)
        slot = b.no_links(p.game / b.SLOT)
        if slot.exists():
            backup = root / 'previous-scene-probe.js'; b.copy_new(slot, backup)
        temporary = slot.parent / ('native-service-' + job_id + '.tmp')
        b.copy_new(bundle, temporary); os.replace(temporary, slot); slot_replaced = True
        config = composition['config']
        expected_wall_seconds=p.encounter['timeLimit']+120
        if not 121<=expected_wall_seconds<=390 or config.get('sandbox_root') != str(SANDBOX) or config.get('max_seconds') != expected_wall_seconds or config.get('expected_files', {}).get('GameAssembly.dll', {}).get('sha256') != CLIENT:
            fail('native_source_mismatch', 'Custom native host escaped original client/root/bound')
        config['output_dir'] = str(root / 'output')
        if config['diagnostic_files'][b.SLOT]['sha256'] != p.bundle_sha:
            fail('native_source_mismatch', 'Host is not bound to this selected custom script')
        bootstrap=stage_rendered_bootstrap(release,root,config)
        p.bootstrap=bootstrap
        gadget_runtime=stage_gadget_runtime(release,root,config,request)
        p.gadget_runtime=gadget_runtime
        b.fresh_json(root / 'config.json', config)
        p.plan = release.host.validate(root / 'config.json')
        staging['planSha256'] = p.plan['plan_sha256']; staging['originalResultFilename'] = release.data['packetBasename']
        b.fresh_json(root / 'plan.json', p.plan); b.fresh_json(root / 'staging.json', staging)
        b.fresh_json(root / 'mode.json', p.mode)
        b.fresh_json(root / 'ready.json', {'schema_version': 1, 'status': 'integration_ready', 'sandbox_root': str(SANDBOX),
                     'plan_sha256': p.plan['plan_sha256'], 'release_manifest_sha256': release.sha,
                     'native_battle_authorized': True, 'bounded_original_encounter_only': True, 'stop_first_failure': True})
        b.fresh_json(root / 'prepared.json', {'jobId': job_id, 'requestSha256': request_sha, 'inputSourceSha256': input_sha,
                     'bundleSha256': p.bundle_sha, 'identities': identities, 'clearedPreviouslyArchivedSharedFiles': cleaned})
        progress('prepared'); return p
    except BaseException as error:
        rollback = {'scriptRestored': False}
        try:
            b.no_private_player()
            if temporary is not None and temporary.exists() and root is not None:
                b.copy_new(temporary, root / 'abandoned-scene-probe.tmp'); temporary.unlink()
            if slot_replaced:
                b.bound(slot, sha(bundle))
                if backup is not None:
                    restore = slot.parent / ('native-service-' + job_id + '.tmp')
                    b.copy_new(backup, restore); os.replace(restore, slot)
                else: slot.unlink()
                rollback['scriptRestored'] = True
        except Exception as problem: rollback['rollbackError'] = str(problem)
        if root is not None and root.exists():
            try: b.fresh_json(root / 'preparation-error.json', {'error': str(error), 'noNativeHostExecuted': True, **rollback})
            except Exception: pass
        try: restore_private_runtime_overrides(bootstrap,gadget_runtime)
        except BaseException as restore_error:
            if root is not None:
                try:b.fresh_json(root/'bootstrap-restore-error.json',{'error':str(restore_error),'pendingMarkerRetained':True})
                except Exception:pass
            raise
        finally:lease.close()
        raise


def result_from_evidence(prepared, verification, decoder_path=None, *, validate_only=False):
    p = prepared
    encounter = p.encounter
    terminal = (verification.get('terminalResults') or [{}])[-1]
    rounds = terminal.get('rounds') or []
    if len(rounds) != 1 or terminal.get('inputSourceSha256') != p.input_sha or terminal.get('originalPacketExported') is not True or terminal.get('statisticsAndPacketCapturedBeforeCleanup') is not True or terminal.get('completeBattle') is not True or type(rounds[0].get('duration')) not in (int, float) or not 0 < rounds[0]['duration'] <= encounter['timeLimit'] + 1 or type(terminal.get('result')) is not int or terminal['result'] not in (1, 2) or not p.release.base._decimal(rounds[0].get('squadTotal')):
        fail('native_output_invalid', 'Original selected-input terminal is incomplete or bound to other inputs')
    completion = terminal.get('verification') or {}
    if completion.get('passed') is not True or completion.get('inputSourceSha256') != p.input_sha:
        fail('native_output_invalid', 'Original custom input/result verification failed')
    ui_score = terminal.get('originalUiScore')
    if encounter.get('contentMode') == 'anomaly':
        if (not isinstance(ui_score, dict) or not p.release.base._decimal(ui_score.get('damage'))
                or ui_score.get('source') != 'BerserkContext.get_CurrentTargetDamage'
                or ui_score.get('conversion') != 'original_ACTk_ObscuredLong_op_Implicit'
                or ui_score.get('uiDestination') != 'StageResultInfoData.TotalDamage'
                or ui_score.get('capturedBeforeCleanup') is not True
                or ui_score.get('scoreCalculated') is not False):
            fail('native_output_invalid', 'Original Anomaly UI score is missing or invalid')
    elif ui_score is not None:
        fail('native_output_invalid', 'Unexpected Anomaly UI score for another encounter mode')
    anti = terminal.get('originalAntiCheat') or {}
    if anti.get('waveId') != encounter['waveId'] or type(anti.get('battleDuration')) is not int or not 0 < anti['battleDuration'] <= encounter['timeLimit'] * 1000 + 1000 or anti.get('characterCount') != 5 or type(anti.get('monsterCount')) is not int or anti['monsterCount'] <= 0:
        fail('native_output_invalid', 'Original native encounter DTO differs')
    rows = rounds[0].get('characters') or []
    if len(rows) != 5:
        fail('native_output_invalid', 'Five original native character statistics required')
    characters = []
    for slot, (tid, name) in enumerate(p.identities, 1):
        matches = [row for row in rows if (row.get('tableId'), row.get('nameCode')) == (tid, name)]
        if len(matches) != 1:
            fail('native_output_invalid', 'Native result does not match the selected ordered team')
        row = matches[0]
        if type(row.get('entityId')) is not int or row['entityId'] <= 0 or not p.release.base._decimal(row.get('outgoingDamage')) or not p.release.base._decimal(row.get('outgoingActualDamage')):
            fail('native_output_invalid', 'Native exact Int64/entity statistics are invalid')
        characters.append({'slot': slot, 'tableId': tid, 'nameCode': name, 'entityId': row['entityId'],
                           'damage': row['outgoingDamage'], 'actualDamage': row['outgoingActualDamage']})
    if len({row['entityId'] for row in characters}) != 5:
        fail('native_output_invalid', 'Native character entities are duplicated')
    if validate_only:
        return {'score': rounds[0]['squadTotal'], 'characters': characters,
                **({'gameTotalDamage': ui_score['damage'], 'gameTotalDamageSource': ui_score} if ui_score else {})}
    output = p.root / 'output'; packet = output / p.release.data['packetBasename']
    evidence = {}
    for name, path in [('verification', output / 'verification.json'), ('decoder', decoder_path), ('staging', output / 'staging.json'), ('request', output / 'request.json')]:
        evidence[name + 'Path'], evidence[name + 'Sha256'] = str(path), sha(path)
    return {'schemaVersion': 1, 'schema': SCHEMA, 'engine': 'original153', 'jobId': p.job_id,
            'releaseId': p.release.data['releaseId'], 'releaseManifestSha256': p.release.sha,
            'customSourceReceiptSha256': p.release.receipt_sha, 'requestSha256': p.request_sha,
            'inputSourceSha256': p.input_sha, 'clientSha256': CLIENT,
            'encounterId': encounter['id'], 'encounter': encounter, 'waveId': encounter['waveId'],
            'durationMs': anti['battleDuration'], 'nativeResult': terminal['result'], 'score': rounds[0]['squadTotal'], 'characters': characters,
            'nativeOutcome': {key: terminal.get(key) for key in ('spotResult','timeout','targetRemainHp','targetMaxHp','survivingPlayerCount','deadListCount')},
            'tactical': terminal.get('tactical'),
            **({'gameTotalDamage': ui_score['damage'], 'gameTotalDamageSource': ui_score} if ui_score else {}),
            'packet': {'format': 'protobuf_wire', 'path': str(packet), 'sha256': sha(packet), 'byteLength': packet.stat().st_size},
            'evidence': evidence, 'fullAccuracyVerified': False,
            'limits': ['Original153 mechanics; selected custom team/build', encounter['name'],
                       'Custom native execution has no actual-game comparison claim', 'Captured fixed-team RNG equality is inapplicable to custom inputs']}


def decode_selected_packet(p, packet, report_path, terminal):
    """Use the unchanged managed decoder with original elapsed milliseconds.

    The historical wrapper assumed every run lasted the full 90 seconds. Only
    this argument adapter is different; original packet bytes and decoder
    binaries remain exactly those admitted with the fixed native release.
    """
    source = terminal.get('originalPacketSource') or {}
    native = terminal.get('originalAntiCheat') or {}
    duration = native.get('battleDuration')
    if type(duration) is not int or not 0 < duration <= p.encounter['timeLimit'] * 1000 + 1000 or source.get('format') != 'protobuf_wire' or type(source.get('byteLength')) is not int or source['byteLength'] != packet.stat().st_size or native.get('source') != 'original_BattleResult_AntiCheatBattleDataInit' or native.get('waveId') != p.encounter['waveId'] or native.get('characterCount') != 5 or type(native.get('monsterCount')) is not int or not 0 < native['monsterCount'] <= 100000:
        fail('native_output_invalid', 'Original custom packet DTO/export identity is invalid')
    if not 0 < packet.stat().st_size <= 16777216 or report_path.exists():
        fail('native_output_invalid', 'Original custom packet/decode output bounds are invalid')
    before = sha(packet)
    if source.get('sha256') is not None and source['sha256'] != before:
        fail('native_output_invalid', 'Native exporter hash differs from unchanged packet')
    receipt_path = p.release.file('decoderBuildReceiptFile')
    receipt = p.release.decoder.validate_build_receipt(receipt_path)
    command = [receipt['dotnet']['path'], receipt['artifacts']['PacketDecoder.dll']['path'],
               '--input', str(packet), '--output', str(report_path), '--wave', str(p.encounter['waveId']),
               '--duration', str(duration), '--characters', '5', '--monsters', str(native['monsterCount']),
               '--tids', ','.join(str(x[0]) for x in p.identities), '--native-byte-length', str(source['byteLength'])]
    if source.get('sha256') is not None: command += ['--native-sha256', before]
    process = subprocess.run(command, capture_output=True, text=True, timeout=30,
                             creationflags=getattr(subprocess, 'CREATE_NO_WINDOW', 0))
    if process.returncode:
        fail('native_output_invalid', 'Independent original wire decode failed: ' + (process.stdout + process.stderr)[:2000])
    report = read(report_path)
    wire, decoder = report.get('originalWire') or {}, report.get('decoder') or {}
    if sha(packet) != before or report.get('status') != 'passed' or wire.get('sha256') != before or wire.get('byteLength') != packet.stat().st_size or wire.get('bytesRewritten') is not False or any(decoder.get(k) != receipt['artifacts'][name]['sha256'] for k, name in [('assemblySha256', 'PacketDecoder.dll'), ('generatedTypesAssemblySha256', 'EpinelPS.dll'), ('protobufAssemblySha256', 'Google.Protobuf.dll')]):
        fail('native_output_invalid', 'Independent selected-input decoder/source binding differs')
    p.release.decoder.validate_build_receipt(receipt_path)
    return report


def custom_native_controls(rows, request_sha, identities, encounter, prebattle_match=None):
    observations = [row for row in rows if row.get('status') == 'original_custom_shared_rng_observed']
    if len(observations) != 2 or [row.get('boundaryPhase') for row in observations] != ['enter', 'leave'] or any(row.get('status') == 'original_custom_shared_rng_read_failed' for row in rows):
        fail('native_rng_gate_failed', 'Two clean original custom RNG entry/return observations required')
    for row in observations:
        actual = row.get('actual') or {}
        if row.get('requestSha256') != request_sha or row.get('rngStateWritten') is not False or row.get('rngMethodsInvoked') is not False or row.get('referenceCompared') is not False or not isinstance(actual.get('seedArray'), list) or len(actual['seedArray']) != 56 or any(type(value) is not int or not -2147483648 <= value <= 2147483647 for value in actual['seedArray']) or type(actual.get('seed')) is not int or not -2147483648 <= actual['seed'] <= 2147483647 or any(type(actual.get(k)) is not int or not 0 <= actual[k] < 56 for k in ('inext', 'inextp')) or not isinstance(actual.get('drawCount'), str) or not re.fullmatch(r'0|[1-9][0-9]{0,18}', actual['drawCount']) or int(actual['drawCount']) > 9223372036854775807:
            fail('native_rng_gate_failed', 'Original custom RNG observation/provenance is invalid')
    fixtures = [row for row in rows if row.get('status') == 'custom_native_fixture_prepared']
    builds = [row for row in rows if row.get('status') == 'original_native_build_prepared']
    if len(fixtures) != 1 or fixtures[0].get('passed') is not True or fixtures[0].get('requestSha256', (fixtures[0].get('readback') or {}).get('requestSha256')) != request_sha:
        fail('native_input_readback_failed', 'Original current-job transporter/team readbacks must pass')
    wanted = [{'slot': slot, 'tableId': tid, 'nameCode': name} for slot, (tid, name) in enumerate(identities, 1)]
    checks, fields = fixtures[0].get('teamChecks'), fixtures[0].get('fieldChecks')
    if not isinstance(checks, list) or len(checks) != 5 or any(row.get('passed') is not True or any(row.get(k) != expected[k] for k in ('slot', 'tableId', 'nameCode')) for row, expected in zip(checks, wanted)) or not isinstance(fields, list) or len(fields) != 61 or any(row.get('passed') is not True for row in fields):
        fail('native_input_readback_failed', 'All selected team and 61 original transporter field readbacks must pass')
    if len(builds) != 1 or builds[0].get('passed') is not True or builds[0].get('requestSha256') != request_sha or builds[0].get('characters') != wanted:
        fail('native_input_readback_failed', 'Selected native build constructors/readbacks must pass')
    prebattle_gate = None
    if prebattle_match is not None:
        gates = [row for row in rows if row.get('status') == 'original_native_prebattle_match']
        expected_cp = [row['nativeValues']['BattlePower'] for row in prebattle_match['characters']]
        if len(gates) != 1:
            fail('native_input_readback_failed', 'Exactly one pre-battle native build/CP comparison required')
        prebattle_gate = gates[0]
        if (prebattle_gate.get('passed') is not True or prebattle_gate.get('requestSha256') != request_sha
                or prebattle_gate.get('actualCaptureSha256') != prebattle_match['actualCaptureSha256']
                or prebattle_gate.get('beforeOnInit') is not True or prebattle_gate.get('battleStarted') is not False
                or prebattle_gate.get('expectedValuesUsedAsConstructorInputs') is not False
                or prebattle_gate.get('pythonStatMathUsed') is not False or prebattle_gate.get('mismatches') != []
                or prebattle_gate.get('expectedCombatPowers') != expected_cp
                or prebattle_gate.get('nativeCombatPowers') != expected_cp
                or rows.index(prebattle_gate) >= rows.index(builds[0])
                or rows.index(prebattle_gate) >= rows.index(fixtures[0])):
            fail('native_input_readback_failed', 'Original native build/CP comparison did not pass before encounter initialization')
    def one(status):
        found = [row for row in rows if row.get('status') == status]
        if len(found) != 1:
            fail('native_input_readback_failed', 'One selected encounter readback required: ' + status)
        return found[0]
    wave = one('original153_encounter_wave_verified')
    context = one('original153_encounter_context_created')
    geometry = one('original153_encounter_geometry_selected')
    team = one('original153_encounter_team_prepared')
    policy = one('native_control_mode_selected')
    if any(row.get('encounterId') != encounter['id'] for row in (wave, context, geometry, team)) or wave.get('waveId') != encounter['waveId'] or wave.get('backgroundName') != encounter['backgroundName'] or context.get('processType') != encounter['processType'] or context.get('processClass') != encounter['processClass'] or context.get('originalFactoryInvoked') is not True or context.get('originalContextInvoked') is not True or geometry.get('backgroundKey') != encounter['backgroundName'] or geometry.get('originalThemeFormatterInvoked') is not True or geometry.get('backgroundSubstituted') is not False or team.get('passed') is not True or team.get('requestSha256') != request_sha or policy.get('waveId') != encounter['waveId'] or policy.get('controlMode') != encounter.get('controlPolicy', 'auto'):
        fail('native_input_readback_failed', 'Original selected encounter, team, scene or controls differ')
    return {'status': 'passed', 'requestSha256': request_sha, 'rngObservations': observations,
            'fixtureReadback': fixtures[0], 'buildReadback': builds[0], 'referenceCompared': False,
            'prebattleMatch': prebattle_gate,
            'encounter': encounter, 'waveReadback': wave, 'contextReadback': context,
            'geometryReadback': geometry, 'teamReadback': team, 'controlPolicyReadback': policy,
            'rngStateWritten': False, 'rngMethodsInvoked': False}


def collect_job(p, execution_error=None):
    b = p.release.base
    if not p.executed or p.collected:
        fail('native_job_invalid', 'One completed host attempt required')
    b.no_private_player()
    output = p.root / 'output'; output.mkdir(exist_ok=True)
    errors = [] if execution_error is None else [str(execution_error)]
    unexpected = [x.name for x in output.iterdir() if x.name not in ('player.log', 'native-player-run.json')]
    if unexpected: errors.append('Unexpected host artifacts: ' + ','.join(unexpected))
    copied = {}
    for name, source in b.shared_files(p.game).items():
        if name not in b.LOGS and name not in (b.SLOT, p.release.data['packetBasename']):
            errors.append('Unknown shared result retained: ' + name); continue
        target = output / ('scene-probe.js' if name == b.SLOT else name)
        b.copy_new(source, target); copied[name] = target
    for name in ('request.json', 'request-binding.json', 'config.json', 'plan.json', 'ready.json', 'staging.json', 'mode.json', 'resource-pre.json', 'preferences-pre.json', 'prepared.json'):
        b.copy_new(p.root / name, output / name)
    if getattr(p,'bootstrap',None) is not None:
        for name in ('original-nikkeBase.dll','original-bootstrap-receipt.json','rendered-bootstrap-receipt.json','bootstrap-staged.json'):
            b.copy_new(p.root/name,output/name)
    if getattr(p,'gadget_runtime',None) is not None:
        for name in ('original-frida-gadget.config','v8-frida-gadget.config','gadget-runtime-staged.json'):
            b.copy_new(p.root/name,output/name)
    b.copy_new(REGISTRY, output / 'custom-source-receipt.json'); b.copy_new(p.release.path, output / 'release-manifest.json')
    run = p.host_result or {'returncode': None, 'timed_out': False, 'stdout': '', 'elapsed_seconds': None, 'desktop': None}
    if not (output / 'native-player-run.json').exists(): b.fresh_json(output / 'native-player-run.json', run)
    actual_pid = None
    for line in run.get('stdout', '').splitlines():
        try:
            row = json.loads(line)
            if row.get('phase') == 'player_pid' and type(row.get('pid')) is int: actual_pid = row['pid']
        except ValueError: pass
    if actual_pid is None: errors.append('Actual native child PID not recorded')
    try:
        verify_inventory(p.release); unchanged = verify_staging(p)
        b.bound(p.bundle, p.bundle_sha)
        if p.release.host.validate(p.root / 'config.json', fresh_output=False)['plan_sha256'] != p.plan['plan_sha256']:
            fail('native_source_mismatch', 'Host plan changed during custom job')
    except Exception as error: unchanged = {'sourceInputs': False}; errors.append(str(error))
    # Host validation above must still see the registered candidate. The frozen
    # isolation proof below deliberately pins the original private bootstrap.
    try: restore_private_runtime_overrides(getattr(p,'bootstrap',None),getattr(p,'gadget_runtime',None))
    except Exception as error: errors.append('Private runtime restoration failed: '+str(error))
    if (p.root/'gadget-runtime-restored.json').exists():
        b.copy_new(p.root/'gadget-runtime-restored.json',output/'gadget-runtime-restored.json')
    post_preferences = {'status': 'failed'}; post_resources = None
    try: post_preferences = b.preference_witness(p.release.frozen, p.pre_preferences)
    except Exception as error: errors.append(str(error))
    try:
        post_resources = b.resource_witness(p.release.frozen, p.staging)
        if post_resources['groupStats'] != p.pre_resources['groupStats']:
            fail('native_resources_changed', 'Original resource identities changed')
    except Exception as error: errors.append(str(error))
    b.fresh_json(output / 'preferences-post.json', post_preferences); b.fresh_json(output / 'resource-post.json', post_resources or {'status': 'failed'})
    rows = []; scene = output / 'scene-events.jsonl'
    if scene.exists():
        if scene.stat().st_size > 16_000_000: errors.append('Native event evidence exceeds bounds')
        else:
            try: rows = [json.loads(line) for line in scene.read_text(encoding='utf-8').splitlines()]
            except ValueError as error: errors.append('Malformed native events: ' + str(error))
    terminals = [row for row in rows if row.get('status') == 'original_practice_terminal_result']
    terminal = terminals[-1] if terminals else {}
    failures = [row for row in rows if row.get('status') in ('first_failure', 'original_practice_packet_export_failed') or row.get('phase') == 'native_exception']
    # Different teams legitimately consume different RNG. Keep observations as
    # evidence; never compare them with the historical five-character state.
    observations = [row for row in rows if row.get('status', '').startswith('original_practice_full_shared_rng_') or row.get('status') == 'original_custom_shared_rng_observed']
    custom_controls = {'status': 'failed'}
    try: custom_controls = custom_native_controls(rows, p.request_sha, p.identities, p.encounter, p.request.get('prebattleMatch'))
    except Exception as error: errors.append(str(error))
    packet = output / p.release.data['packetBasename']; decoder_path = output / 'independent-packet-decode.json'; decoded = None
    if terminal.get('originalPacketExported') is True and packet.exists() and all(unchanged.values()):
        try: decoded = decode_selected_packet(p, packet, decoder_path, terminal)
        except Exception as error: errors.append('Independent original packet decode failed: ' + str(error))
    packet_ok = decoded is not None and decoded.get('status') == 'passed'
    complete = terminal.get('completeBattle') is True and (terminal.get('verification') or {}).get('passed') is True
    quit_requested = any(row.get('phase') == 'quit_requested' for row in rows)
    preferences_ok = post_preferences.get('status') == 'passed'
    resources_ok = post_resources is not None and post_resources['groupStats'] == p.pre_resources['groupStats']
    if not complete or not packet_ok or not quit_requested or run.get('returncode') != 0 or run.get('timed_out') is not False or not str(run.get('desktop', '')).startswith('NikkeCatalogProbe_') or failures or not preferences_ok or not resources_ok:
        errors.append('Original native completion/export/exit/isolation/source gate failed')
    artifact = {'filename': packet.name, 'format': 'protobuf_wire', 'sha256': sha(packet), 'byteLength': packet.stat().st_size, 'bytesRewritten': False} if packet.exists() else None
    verification = {'schemaVersion': 1, 'status': 'failed' if errors else 'passed', 'jobId': p.job_id,
                    'requestSha256': p.request_sha, 'inputSourceSha256': p.input_sha, 'identities': p.identities,
                    'customSourceReceiptSha256': p.release.receipt_sha, 'releaseManifestSha256': p.release.sha,
                    'planSha256': p.plan['plan_sha256'], 'exitCode': run.get('returncode'), 'timedOut': run.get('timed_out'),
                    'actualPlayerPid': actual_pid, 'privateDesktop': run.get('desktop'), 'deadChild': {'privateImageAbsent': True},
                    'errors': errors, 'terminalResults': terminals, 'completeBattle': complete,
                    'frozenSourceInputsUnchanged': unchanged, 'nativeFailures': failures,
                    'requiredPreferenceStorageControlsPassed': preferences_ok, 'resourceInputIdentitiesUnchanged': resources_ok,
                    'originalPacketExportVerified': packet_ok, 'originalPacketArtifact': artifact,
                    'fullSharedRngStateObservations': observations, 'capturedRngEqualityApplicable': False,
                    'customNativeControls': custom_controls,
                    'capturedRngEqualityClaimed': False, 'normalNativeQuitRequested': quit_requested,
                    'fullAccuracyVerified': False, 'artifacts': {x.name: sha(x) for x in output.iterdir() if x.is_file()}}
    if not errors:
        try: result_from_evidence(p, verification, validate_only=True)
        except Exception as error: errors.append(str(error)); verification['status'] = 'failed'
    verification_path = output / 'verification.json'; b.fresh_json(verification_path, verification)
    p.collected = True
    b._finish_shared(p, verification_path, copied)
    p.progress('archived')
    if verification['status'] != 'passed':
        fail('native_verification_failed', 'Custom native job failed; evidence retained at ' + str(verification_path))
    return result_from_evidence(p, verification, decoder_path)


def run_job(p):
    b = p.release.base
    if p.executed:
        fail('native_job_invalid', 'A native host attempt may not be repeated')
    try:
        b.no_private_player(); verify_inventory(p.release); verify_staging(p)
        if (p.game / p.release.data['packetBasename']).exists():
            fail('native_unarchived_artifact', 'Original output must be absent before launch')
        p.executed = True; p.progress('running_private_player'); error = None
        try: p.host_result = p.release.host.execute(p.root / 'config.json', p.root / 'ready.json', prepared_plan=p.plan)
        except Exception as problem: error = problem
        return collect_job(p, error)
    except BaseException as error:
        try: b.fresh_json(p.root / 'job-error.json', {'code': getattr(error, 'code', 'native_runner_failed'), 'error': str(error), 'hostAttempted': p.executed, 'immutableArchiveCompleted': p.collected})
        except Exception: pass
        raise
    finally:
        try:
            restore_private_runtime_overrides(getattr(p,'bootstrap',None),getattr(p,'gadget_runtime',None))
        except BaseException as restore_error:
            try:b.fresh_json(p.root/'bootstrap-restore-error.json',{'error':str(restore_error),'pendingMarkerRetained':True})
            except Exception:pass
            raise
        finally:p.lease.close()


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source-receipt', type=Path, required=True)
    parser.add_argument('--receipt-sha256', required=True)
    parser.add_argument('--job-id', required=True)
    parser.add_argument('--request-sha256', required=True)
    args = parser.parse_args(argv)
    def emit(value):
        try: print(json.dumps(value, separators=(',', ':'), ensure_ascii=True), flush=True)
        except (BrokenPipeError, OSError): pass
    try:
        if not JOB.fullmatch(args.job_id) or not HEX.fullmatch(args.request_sha256):
            fail('native_job_invalid', 'Invalid server-generated request binding')
        request_path = SERVICE / 'requests' / (args.job_id + '.json')
        if request_path.is_symlink() or sha(request_path) != args.request_sha256:
            fail('native_source_mismatch', 'Original selected request bytes changed')
        request = read(request_path)
        if hashlib.sha256(canonical(request)).hexdigest() != args.request_sha256:
            fail('native_source_mismatch', 'Selected request is not canonical')
        p = prepare_job(args.source_receipt, args.receipt_sha256, args.job_id, request, lambda phase: emit({'type': 'progress', 'phase': phase}))
        emit({'type': 'result', 'result': run_job(p)}); return 0
    except Exception as error:
        emit({'type': 'error', 'code': getattr(error, 'code', 'native_runner_failed'), 'error': str(error)[:2000]}); return 2


if __name__ == '__main__':
    raise SystemExit(main())
