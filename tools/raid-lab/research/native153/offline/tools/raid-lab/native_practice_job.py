"""Approved fixed-fixture original153 broker. No default release or combat fallback.

Only this broker's fresh job directories and known, already archived shared probe
artifacts are mutable. Native source is copied byte-for-byte from an admitted
release. No native player is started by import, validation, or tests.
"""
from __future__ import annotations

import argparse
import ctypes
from ctypes import wintypes
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import re
import shutil
import sys
from types import SimpleNamespace

WORKSPACE = Path(__file__).resolve().parents[2]
SANDBOX = WORKSPACE / "tools/raid-lab/private/native-player153-20261101"
HOST = WORKSPACE / "tools/raid-lab/native_player_host.py"
LEASE = WORKSPACE / "tools/raid-lab/native_runner_lease.py"
HARNESS = WORKSPACE / "event-selector/first-anniversary/catalog-repair/isolated_desktop.py"
CLIENT = "d39896d3770888039c728a1908448c3db5efa7cdf874c90d56f46d8d566428d2"
FIXTURE = "captured-fire90-run1"
FIXTURE_SHA = "9660b4f952fbc86228d7537b3d8d59838d98cc8138aed5812d696dac7169f8c7"
CAPTURE_SHA = "634ab51506bd28c10f4c229a6b0c1baabe0aa757f1c3611ca5142dcff936d82d"
RNG_SHA = "214742a251316375b8b2e3527d97df9150ee2039238fc3042ed358cb5183bb55"
PREF_BASELINE_SHA = "1fcd38c07f9ad25b85405899231ced0d19d7d9ba5ffd5baed322525c82b5681c"
ISOLATION_SHA = "149ecd1c37f6b56d7503f0ce04eb110fbe566e67ab0f1798963a809b3ad670fd"
IDENTITIES = [(301701, 5169), (141207, 5134), (110109, 5024), (319111, 5004), (422205, 5041)]
SCHEMA = "native-practice-v1"
HEX = re.compile(r"[a-f0-9]{64}\Z")
JOB = re.compile(r"[a-f0-9]{24}\Z")
RELEASE_ID = re.compile(r"[a-z0-9][a-z0-9_-]{0,79}\Z")
PACKET = re.compile(r"practice[1-9][0-9]*-original-result\.pb\Z")
SLOT = "NKAB/dist/scene-probe.js"
LOGS = ("scene-events.jsonl", "headless-bootstrap.log", "offline-network.log")
REQUIRED_RUNTIME = {"current-tables.zip", "current-tables-provenance.json",
                    "NIKKE/NIKKE/game/nikke_Data/il2cpp_data/Metadata/global-metadata.dat"}
_BUILTIN_ROOT = "NIKKE/NIKKE/game/nikke_Data/StreamingAssets/aa/StandaloneWindows64/"
REQUIRED_BUILTINS = {_BUILTIN_ROOT + name: digest for name, digest in {
    "audiogroupincludebuild_assets_all.bundle": "fad072af85f2fca091a0647869e43d8f7104599c9a61767894ca767de2813820",
    "shaders_assets_softmask.bundle": "d8aa4d3b568ecfd1ab053ec84f699cead96d7acd9fed0351b7e64d20d626f957",
    "shaders_assets_softmasketc1.bundle": "6506bc2b54aa305559f9d8ea9dffdd9d6d4166b0a99d68b58adf2d69d5f33193",
    "shaders_assets_ui_additive.bundle": "f86c5f33f52e040d25383a7a6e111ce2e3360a4a3eb0c712681aad76841db168",
}.items()}


class BrokerError(RuntimeError):
    def __init__(self, code, message):
        super().__init__(message)
        self.code = code


def fail(code, message):
    raise BrokerError(code, message)


def sha(path):
    with Path(path).open("rb") as source:
        return hashlib.file_digest(source, "sha256").hexdigest()


def no_links(path):
    path = Path(path).absolute()
    current = Path(path.anchor)
    for part in path.parts[1:]:
        current /= part
        if current.is_symlink() or (hasattr(os.path, "isjunction") and os.path.isjunction(current)):
            fail("native_source_mismatch", "Runner paths may not traverse links or junctions")
    return path.resolve()


def inside(base, relative):
    if not isinstance(relative, str) or not relative or ":" in relative or Path(relative).is_absolute() or ".." in Path(relative).parts:
        fail("native_source_mismatch", "Invalid release-relative path")
    path = no_links(base / relative)
    if not path.is_relative_to(no_links(base)) or path == no_links(base):
        fail("native_source_mismatch", "Path escapes its exact release/job directory")
    return path


def bound(path, digest=None):
    path = no_links(path)
    if not path.is_file() or path.stat().st_nlink != 1 or path.stat().st_size > 536870912:
        fail("native_source_mismatch", "Required separate bounded file is missing")
    if digest is not None and (not isinstance(digest, str) or not HEX.fullmatch(digest) or sha(path) != digest):
        fail("native_source_mismatch", "Native source/evidence hash differs")
    return path


def read_json(path):
    path = bound(path)
    if path.stat().st_size > 4000000:
        fail("native_evidence_invalid", "Native control JSON exceeds bounds")
    try:
        value = json.loads(path.read_text(encoding="utf-8"), parse_constant=lambda _: (_ for _ in ()).throw(ValueError()))
    except (ValueError, UnicodeError) as error:
        raise BrokerError("native_evidence_invalid", "Invalid native control JSON") from error
    if not isinstance(value, dict):
        fail("native_evidence_invalid", "Native control JSON must be an object")
    return value


def fresh_json(path, value):
    if path.exists():
        fail("native_job_exists", "Refuse to overwrite existing job evidence")
    with path.open("x", encoding="utf-8") as target:
        json.dump(value, target, indent=2); target.write("\n")


def copy_new(source, target):
    bound(source)
    if target.exists():
        fail("native_job_exists", "Refuse to overwrite archived native evidence")
    with source.open("rb") as incoming, target.open("xb") as outgoing:
        shutil.copyfileobj(incoming, outgoing, 1048576)
    if sha(source) != sha(target):
        fail("native_archive_failed", "Native artifact copy readback differs")


def load_module(path, name):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


def verify_runtime(data):
    """Pin small runtime/client dependencies; huge stores use identity witnesses."""
    runtime = data.get("runtime") or {}
    for path, key in ((HOST, "hostSha256"), (LEASE, "leaseSha256"), (HARNESS, "harnessSha256")):
        bound(path, runtime.get(key))
    required = runtime.get("requiredFiles")
    if not isinstance(required, dict) or not REQUIRED_RUNTIME.issubset(required) or len(required) > 256:
        fail("native_release_unavailable", "Original table/metadata/client dependency inventory is missing")
    if any(required.get(name) != digest for name, digest in REQUIRED_BUILTINS.items()):
        fail("native_release_unavailable", "All four original mechanical intro builtin copies must be pinned")
    for relative, digest in required.items():
        if relative not in ("current-tables.zip", "current-tables-provenance.json") and not relative.startswith("NIKKE/NIKKE/game/nikke_Data/"):
            fail("native_source_mismatch", "Runtime dependency is outside the original private client essentials")
        bound(inside(SANDBOX, relative), digest)


def no_private_player():
    """Read process image paths only; never attach/read game memory."""
    if os.name != "nt":
        fail("native_runner_unavailable", "Original player requires Windows")
    kernel = ctypes.WinDLL("kernel32", use_last_error=True)
    class Entry(ctypes.Structure):
        _fields_ = [("dwSize", wintypes.DWORD), ("cntUsage", wintypes.DWORD), ("th32ProcessID", wintypes.DWORD),
                    ("th32DefaultHeapID", ctypes.c_size_t), ("th32ModuleID", wintypes.DWORD), ("cntThreads", wintypes.DWORD),
                    ("th32ParentProcessID", wintypes.DWORD), ("pcPriClassBase", wintypes.LONG),
                    ("dwFlags", wintypes.DWORD), ("szExeFile", wintypes.WCHAR * 260)]
    kernel.CreateToolhelp32Snapshot.argtypes = [wintypes.DWORD, wintypes.DWORD]
    kernel.CreateToolhelp32Snapshot.restype = wintypes.HANDLE
    kernel.Process32FirstW.argtypes = kernel.Process32NextW.argtypes = [wintypes.HANDLE, ctypes.POINTER(Entry)]
    kernel.OpenProcess.argtypes = [wintypes.DWORD, wintypes.BOOL, wintypes.DWORD]; kernel.OpenProcess.restype = wintypes.HANDLE
    kernel.QueryFullProcessImageNameW.argtypes = [wintypes.HANDLE, wintypes.DWORD, wintypes.LPWSTR, ctypes.POINTER(wintypes.DWORD)]
    kernel.CloseHandle.argtypes = [wintypes.HANDLE]
    snapshot = kernel.CreateToolhelp32Snapshot(2, 0)
    if snapshot == ctypes.c_void_p(-1).value:
        raise ctypes.WinError(ctypes.get_last_error())
    try:
        entry = Entry(); entry.dwSize = ctypes.sizeof(entry)
        present = kernel.Process32FirstW(snapshot, ctypes.byref(entry))
        while present:
            if entry.szExeFile.lower() == "nikke.exe":
                process = kernel.OpenProcess(0x1000, False, entry.th32ProcessID)
                if not process:
                    fail("runner_busy", "A NIKKE process image cannot be verified closed")
                try:
                    buffer = ctypes.create_unicode_buffer(32768); size = wintypes.DWORD(len(buffer))
                    if not kernel.QueryFullProcessImageNameW(process, 0, buffer, ctypes.byref(size)):
                        fail("runner_busy", "A NIKKE process image cannot be verified")
                    if Path(buffer.value).resolve() == SANDBOX / "NIKKE/NIKKE/game/nikke.exe":
                        fail("runner_busy", "The shared private player is already alive")
                finally:
                    kernel.CloseHandle(process)
            present = kernel.Process32NextW(snapshot, ctypes.byref(entry))
    finally:
        kernel.CloseHandle(snapshot)


def admit_verification(record, staging, expected, rng_gate):
    required = ("completeBattle", "originalPacketExportVerified", "requiredPreferenceStorageControlsPassed", "requiredFullSharedRngStateVerified")
    if record.get("status") != "passed" or record.get("exitCode") != 0 or record.get("timedOut") is not False or \
       any(record.get(key) is not True for key in required) or staging.get("fullSharedRngStateRequired") is not True or \
       any(record.get(key) != [] for key in ("firstFailures", "nativeExceptions", "originalPacketExportFailures")) or \
       not record.get("frozenSourceInputsUnchanged") or any(value is not True for value in record["frozenSourceInputsUnchanged"].values()):
        fail("native_release_unavailable", "Original native completion/isolation/source/full-RNG validation is incomplete")
    terminal = (record.get("terminalResults") or [{}])[-1]
    checked = rng_gate.verify(record.get("fullSharedRngStateObservations") or [], terminal, expected, RNG_SHA)
    claimed = record.get("fullSharedRngStateVerification") or {}
    if checked["status"] != "passed" or any(claimed.get(key) != value for key, value in checked.items()) or \
       (staging.get("sources", {}).get("rngExpectedInput") or {}).get("sha256") != RNG_SHA:
        fail("native_rng_gate_failed", "Source-bound full shared RNG entry/return gate failed")
    return terminal


def load_release(manifest_path, manifest_sha):
    if not manifest_path.is_file():
        fail("native_release_unavailable", "No approved original-engine release is published")
    path = bound(manifest_path, manifest_sha)
    manifest = read_json(path); directory = path.parent
    rid = manifest.get("releaseId")
    if not isinstance(rid, str) or not RELEASE_ID.fullmatch(rid) or directory != no_links(SANDBOX / "native-service/releases" / rid) or path.name != "manifest.json":
        fail("native_release_unavailable", "Release is not in its fixed approved service directory")
    bindings = {"schemaVersion": 1, "approved": True, "engine": "original153", "fixtureId": FIXTURE,
                "inputSourceSha256": FIXTURE_SHA, "clientSha256": CLIENT, "resultSchema": SCHEMA}
    if any(type(manifest.get(key)) is not type(value) or manifest.get(key) != value for key, value in bindings.items()) or \
       not PACKET.fullmatch(str(manifest.get("packetBasename", ""))) or \
       (manifest.get("operationsPrerequisites") or {}).get("diagnosticLaunchersUseSameLease") is not True:
        fail("native_release_unavailable", "No approved complete fixed-fixture native release is available")
    inventory = manifest.get("files")
    if not isinstance(inventory, dict) or not 1 <= len(inventory) <= 512:
        fail("native_release_unavailable", "Frozen release inventory is missing or oversized")
    for relative, digest in inventory.items():
        bound(inside(directory, relative), digest)
    def file(key):
        relative = manifest.get(key)
        if relative not in inventory:
            fail("native_release_unavailable", "Required release file is not inventoried: " + key)
        return bound(inside(directory, relative), inventory[relative])
    if sha(file("fixtureFile")) != FIXTURE_SHA or sha(file("rngExpectedFile")) != RNG_SHA or \
       sha(file("preferenceBaselineFile")) != PREF_BASELINE_SHA or sha(file("isolationProofFile")) != ISOLATION_SHA:
        fail("native_source_mismatch", "Fixed input/RNG/preference-isolation proof differs")
    verify_runtime(manifest)
    host = load_module(HOST, "_approved_practice_host")
    lease = load_module(LEASE, "_approved_practice_lease")
    gate = load_module(file("rngArchiveGateFile"), "_approved_practice_rng_gate")
    resource = load_module(file("resourceVerifierFile"), "_approved_practice_resources")
    # The frozen resource function uses only CORE plus explicit receipt paths.
    resource.CORE = SANDBOX / "profile/AppData/LocalLow/com_proximabeta/NIKKE/com.shiftup.patch/core"
    preference = load_module(file("preferenceReaderFile"), "_approved_practice_preferences")
    decoder = load_module(file("decoderModuleFile"), "_approved_practice_decoder")
    decoder.ROOT = WORKSPACE  # Exact reviewed .NET runtime remains machine-local.
    decoder.validate_build_receipt(file("decoderBuildReceiptFile"))
    native = manifest.get("nativeValidation") or {}
    def validation_file(key, digest_key):
        relative = native.get(key)
        if relative not in inventory or inventory[relative] != native.get(digest_key):
            fail("native_release_unavailable", "Native release validation is not inventoried")
        return bound(inside(directory, relative), native[digest_key])
    verification = read_json(validation_file("receiptFile", "receiptSha256"))
    old_staging = read_json(validation_file("stagingFile", "stagingSha256"))
    original_build_path = file("decoderOriginalBuildReceiptFile")
    if sha(original_build_path) != (old_staging.get("sources", {}).get("packetDecoderBuildReceipt") or {}).get("sha256"):
        fail("native_source_mismatch", "Original native-validated decoder build receipt is not preserved")
    original_build = read_json(original_build_path); relocated_build = read_json(file("decoderBuildReceiptFile"))
    for group in ("sourceInputs", "artifacts"):
        hashes = lambda value: {name: item["sha256"] for name, item in value.get(group, {}).items()}
        if hashes(original_build) != hashes(relocated_build):
            fail("native_source_mismatch", "Published decoder relocation changed source or compiled artifact bytes")
    if (original_build.get("dotnet") or {}).get("sha256") != (relocated_build.get("dotnet") or {}).get("sha256"):
        fail("native_source_mismatch", "Published decoder relocation changed the reviewed managed runtime")
    expected = read_json(file("rngExpectedFile"))
    admit_verification(verification, old_staging, expected, gate)
    if verification.get("captureSha256") != CAPTURE_SHA or old_staging.get("captureSha256") != CAPTURE_SHA or \
       (old_staging.get("sources", {}).get("fixtureInput") or {}).get("sha256") != FIXTURE_SHA:
        fail("native_source_mismatch", "Native validation is not the original captured fixed input")
    result_from_evidence(SimpleNamespace(), verification, None, validate_only=True)
    validation_packet = validation_file("packetFile", "packetSha256")
    validation_decoder = read_json(validation_file("decoderFile", "decoderSha256"))
    raw = validation_decoder.get("originalWire") or {}
    artifact = verification.get("originalPacketArtifact") or {}
    if validation_decoder.get("status") != "passed" or raw.get("sha256") != sha(validation_packet) or \
       raw.get("byteLength") != validation_packet.stat().st_size or artifact.get("sha256") != raw["sha256"] or \
       artifact.get("byteLength") != raw["byteLength"] or artifact.get("format") != "protobuf_wire":
        fail("native_release_unavailable", "Original approved packet and independent decode are not bound")
    if old_staging.get("originalResultFilename") != manifest["packetBasename"] or \
       verification.get("artifacts", {}).get("scene-probe.js") != sha(file("bundleFile")) or \
       verification.get("artifacts", {}).get("config.json") != sha(file("configTemplateFile")):
        fail("native_source_mismatch", "Composed frozen bundle/result basename differs from the validated release")
    return SimpleNamespace(path=path, sha=manifest_sha, data=manifest, directory=directory, file=file, host=host,
                           lease_module=lease, gate=gate, resource=resource, preference=preference, decoder=decoder, expected=expected)


def verify_inventory(release):
    bound(release.path, release.sha)
    for relative, digest in release.data["files"].items():
        bound(inside(release.directory, relative), digest)
    verify_runtime(release.data)


def verify_staging(release, staging):
    unchanged = {}
    for group in ("sources", "resourceReceipts"):
        values = staging.get(group)
        if not isinstance(values, dict) or not values:
            fail("native_release_unavailable", "Frozen staging inventory is incomplete")
        for key, item in values.items():
            path = no_links(Path(item["path"]))
            if not path.is_relative_to(release.directory):
                fail("native_source_mismatch", "Service staging sources must be immutable in-release copies")
            relative = path.relative_to(release.directory).as_posix()
            if release.data["files"].get(relative) != item["sha256"]:
                fail("native_source_mismatch", "Staging path is not bound by the release inventory")
            bound(path, item["sha256"]); unchanged[key] = True
    for key, file_key in (("fixtureInput", "fixtureFile"), ("rngExpectedInput", "rngExpectedFile"), ("packetDecoderBuildReceipt", "decoderBuildReceiptFile")):
        if Path(staging["sources"][key]["path"]).resolve() != release.file(file_key):
            fail("native_source_mismatch", "Fixed service staging/file binding differs: " + key)
    return unchanged


def resource_witness(release, staging):
    guards = release.resource.verify_resource_receipts({key: Path(item["path"]) for key, item in staging["resourceReceipts"].items()})
    groups = {}
    for group in ("core", "dp"):
        path = no_links(SANDBOX / "profile/AppData/LocalLow/com_proximabeta/NIKKE/com.shiftup.patch" / group / "chunk/store.cdb")
        stat = path.stat()
        groups[group] = {"bytes": stat.st_size, "mtimeNs": stat.st_mtime_ns, "fileId": stat.st_ino,
                         "device": stat.st_dev, "hardlinkCount": stat.st_nlink}
    return {"groupStats": groups, "resourceGuards": guards, "fullPayloadRehashed": False}


def preference_witness(release, before=None):
    baseline = read_json(release.file("preferenceBaselineFile"))
    isolation = read_json(release.file("isolationProofFile"))
    for path, digest in isolation["bindings"].items():
        bound(Path(path), digest)
    rows = release.preference.read_exact_values()
    if rows != baseline["rows"] or before is not None and rows != before["rows"]:
        fail("native_preferences_changed", "Only the four exact approved preference values may be observed unchanged")
    return {"status": "passed", "rows": rows, "writesPerformed": False, "registryEnumerationPerformed": False,
            "normalTwoPreferencesUnchanged": before is not None, "specificPrivateDword1PersistenceVerified": before is not None,
            "isolationProofSha256": ISOLATION_SHA, "continuityBaselinePostSha256": PREF_BASELINE_SHA}


def shared_files(game):
    result = {}
    for name in LOGS:
        if (game / name).exists(): result[name] = bound(game / name)
    for path in game.iterdir():
        if path.is_file() and (path.name.startswith("practice") or path.name.startswith("native153-")) and "original-result" in path.name:
            if not re.fullmatch(r"practice[1-9][0-9]*-original-result\.(?:pb|json)", path.name):
                fail("native_unarchived_artifact", "Unknown shared native output basename")
            result[path.name] = bound(path)
    if (game / SLOT).exists(): result[SLOT] = bound(game / SLOT)
    return result


def archived_entry(entry, source):
    archive = no_links(Path(entry.get("archivePath", "")))
    verification = no_links(Path(entry.get("verificationPath", "")))
    if not archive.is_relative_to(SANDBOX) or archive.is_relative_to(SANDBOX / "NIKKE") or archive.is_relative_to(SANDBOX / "profile") or \
       not verification.is_relative_to(SANDBOX) or verification.is_relative_to(SANDBOX / "NIKKE") or \
       verification.is_relative_to(SANDBOX / "profile") or archive == source:
        fail("native_unarchived_artifact", "Shared artifact archive is not private immutable evidence")
    bound(verification, entry.get("verificationSha256")); bound(archive, entry.get("sha256"))
    if sha(source) != entry["sha256"]:
        fail("native_unarchived_artifact", "Shared artifact has no byte-identical archived copy")


def prepare_job(release_manifest, job_id, manifest_sha256, progress=lambda _: None, runtime=None):
    """Acquire the lease and prepare exactly one fresh job; never execute Unity."""
    if not isinstance(job_id, str) or not JOB.fullmatch(job_id):
        fail("native_job_invalid", "Server-generated24hex job ID required")
    release = load_release(Path(release_manifest), manifest_sha256) if runtime is None else runtime
    service = no_links(SANDBOX / "native-service")
    lease = release.lease_module.NativeRunnerLease(service / "runner.lock")
    root = None; created_root = False; slot = None; backup = None; temporary = None; slot_replaced = False
    try:
        lease.acquire()
    except Exception as error:
        if type(error).__name__ == "RunnerBusy": raise BrokerError("runner_busy", str(error)) from error
        raise
    try:
        no_private_player(); verify_inventory(release)
        jobs = service / "jobs"; jobs.mkdir(exist_ok=True)
        root = inside(jobs, job_id); root.mkdir(exist_ok=False)
        created_root = True
        game = SANDBOX / "NIKKE/NIKKE/game"
        if any((game / SLOT).parent.glob("native-service-*.tmp")):
            fail("native_unarchived_artifact", "An unarchived prior script staging file remains")
        if any(service.glob("shared-artifacts-*.tmp")):
            fail("native_unarchived_artifact", "An unfinished prior shared-archive transaction remains")
        staging = read_json(release.file("stagingTemplateFile")); verify_staging(release, staging)
        pre_resources = resource_witness(release, staging); pre_preferences = preference_witness(release)
        ledger_path = service / "shared-artifacts.json"
        ledger_before_sha = sha(bound(ledger_path)) if ledger_path.exists() else None
        ledger = read_json(ledger_path)["artifacts"] if ledger_path.exists() else release.data.get("initialSharedArtifacts", {})
        current = shared_files(game)
        for name, source in current.items():
            if name not in ledger: fail("native_unarchived_artifact", "Unknown or unarchived shared artifact: " + name)
            archived_entry(ledger[name], source)
        fresh_json(root / "request.json", {"schemaVersion": 1, "jobId": job_id, "releaseManifestSha256": release.sha,
                   "fixtureId": FIXTURE, "inputSourceSha256": FIXTURE_SHA})
        fresh_json(root / "shared-before.json", {"artifacts": ledger})
        fresh_json(root / "resource-pre.json", pre_resources); fresh_json(root / "preferences-pre.json", pre_preferences)
        # Shared deletions are individual verified files, never recursive paths.
        cleaned = []
        for name, source in current.items():
            if name == SLOT: continue
            archived_entry(ledger[name], source); source.unlink(); cleaned.append(name)
        slot = no_links(game / SLOT)
        if slot.exists():
            backup = root / "previous-scene-probe.js"; copy_new(slot, backup)
        temporary = slot.parent / ("native-service-" + job_id + ".tmp")
        copy_new(release.file("bundleFile"), temporary)
        os.replace(temporary, slot)  # Exact scratch script slot only, after archived-byte proof.
        slot_replaced = True
        config = read_json(release.file("configTemplateFile"))
        if config.get("sandbox_root") != str(SANDBOX) or config.get("max_seconds") != 60 or \
           config.get("expected_files", {}).get("GameAssembly.dll", {}).get("sha256") != CLIENT:
            fail("native_source_mismatch", "Original private host template/root/client/bound differs")
        config["output_dir"] = str(root / "output")
        if config["diagnostic_files"][SLOT]["sha256"] != sha(slot):
            fail("native_source_mismatch", "Frozen native code differs from the host template")
        fresh_json(root / "config.json", config)
        plan = release.host.validate(root / "config.json")
        staging["planSha256"] = plan["plan_sha256"]
        staging["originalResultFilename"] = release.data["packetBasename"]
        fresh_json(root / "plan.json", plan); fresh_json(root / "staging.json", staging)
        ready = {"schema_version": 1, "status": "integration_ready", "sandbox_root": str(SANDBOX),
                 "plan_sha256": plan["plan_sha256"], "release_manifest_sha256": release.sha,
                 "native_battle_authorized": True, "bounded_original_practice_only": True, "stop_first_failure": True}
        fresh_json(root / "ready.json", ready)
        fresh_json(root / "prepared.json", {"jobId": job_id, "planSha256": plan["plan_sha256"], "clearedPreviouslyArchivedSharedFiles": cleaned})
        progress("prepared")
        return SimpleNamespace(release=release, lease=lease, root=root, game=game, job_id=job_id, staging=staging,
                               plan=plan, progress=progress, pre_resources=pre_resources, pre_preferences=pre_preferences,
                               ledger_before_sha=ledger_before_sha, host_result=None, executed=False, collected=False)
    except BaseException as error:
        # No player has been launched by preparation. Preserve the failed job and
        # reverse only its own exact script-slot transaction, retaining backups.
        rollback = {"scriptRestored": False}
        try:
            no_private_player()
            if temporary is not None and temporary.exists() and root is not None:
                copy_new(temporary, root / "abandoned-scene-probe.tmp"); temporary.unlink()
            if slot_replaced:
                bound(slot, sha(release.file("bundleFile")))
                if backup is not None:
                    restore = slot.parent / ("native-service-" + job_id + ".tmp")
                    copy_new(backup, restore); os.replace(restore, slot)
                else:
                    slot.unlink()
                rollback["scriptRestored"] = True
        except Exception as problem:
            rollback["rollbackError"] = str(problem)
        if created_root:
            try: fresh_json(root / "preparation-error.json", {"error": str(error), "noNativeHostExecuted": True, **rollback})
            except Exception: pass
        lease.close(); raise


def _decimal(value):
    return isinstance(value, str) and re.fullmatch(r"0|[1-9][0-9]*", value) is not None and int(value) <= 9223372036854775807


def result_from_evidence(prepared, verification, decoder_path, *, validate_only=False):
    """Read original scalars only. Never sum damage or derive a score."""
    p = prepared; terminal = verification["terminalResults"][-1]
    rounds = terminal.get("rounds") or []
    if len(rounds) != 1 or rounds[0].get("duration") != 90 or rounds[0].get("isWin") is not True or \
       terminal.get("result") != 1 or terminal.get("spotResult") != 1 or terminal.get("originalPacketExported") is not True or \
       terminal.get("inputSourceSha256") != FIXTURE_SHA or terminal.get("statisticsAndPacketCapturedBeforeCleanup") is not True or \
       not _decimal(rounds[0].get("squadTotal")) or rounds[0]["squadTotal"] == "0":
        fail("native_output_invalid", "Original fixed-fixture terminal/Int64 result is incomplete")
    anti = terminal.get("originalAntiCheat") or {}
    if anti.get("waveId") != 6801001 or anti.get("battleDuration") != 90000 or anti.get("characterCount") != 5 or \
       type(anti.get("monsterCount")) is not int or anti["monsterCount"] <= 0:
        fail("native_output_invalid", "Original native DTO encounter/count differs")
    rows = rounds[0].get("characters") or []
    if len(rows) != 5:
        fail("native_output_invalid", "Five original ordered character results required")
    characters = []
    for slot, (tid, name) in enumerate(IDENTITIES, 1):
        matches = [row for row in rows if (row.get("tableId"), row.get("nameCode")) == (tid, name)]
        if len(matches) != 1:
            fail("native_output_invalid", "Original ordered character identity differs")
        row = matches[0]
        if type(row.get("entityId")) is not int or row["entityId"] <= 0 or \
           not _decimal(row.get("outgoingDamage")) or not _decimal(row.get("outgoingActualDamage")):
            fail("native_output_invalid", "Original entity/Int64 statistics are invalid")
        characters.append({"slot": slot, "tableId": tid, "nameCode": name, "entityId": row["entityId"],
                           "damage": row["outgoingDamage"], "actualDamage": row["outgoingActualDamage"]})
    if len({row["entityId"] for row in characters}) != 5:
        fail("native_output_invalid", "Original character entities are duplicated")
    if validate_only:
        return {"score": rounds[0]["squadTotal"], "characters": characters}
    output = p.root / "output"; packet = output / p.release.data["packetBasename"]
    verification_path = output / "verification.json"
    return {"schemaVersion": 1, "schema": SCHEMA, "engine": "original153", "releaseId": p.release.data["releaseId"],
            "releaseManifestSha256": p.release.sha, "jobId": p.job_id, "fixtureId": FIXTURE,
            "inputSourceSha256": FIXTURE_SHA, "clientSha256": CLIENT, "rangeId": 1, "waveId": 6801001,
            "durationMs": 90000, "nativeResult": 1, "score": rounds[0]["squadTotal"], "characters": characters,
            "packet": {"format": "protobuf_wire", "path": str(packet), "sha256": sha(packet), "byteLength": packet.stat().st_size},
            "evidence": {"verificationPath": str(verification_path), "verificationSha256": sha(verification_path),
                         "decoderPath": str(decoder_path), "decoderSha256": sha(decoder_path),
                         "stagingPath": str(output / "staging.json"), "stagingSha256": sha(output / "staging.json")},
            "fullAccuracyVerified": False, "limits": ["Fixed captured fixture only", "Shared RNG boundary gate only; no actor/Unity RNG certification",
                "No exact reference parity claim", "All launchers sharing the sandbox must honor the same lease"]}


def _finish_shared(prepared, verification_path, copied):
    """Publish matching archives, then clear only individual known scratch files."""
    p = prepared; service = SANDBOX / "native-service"
    previous = service / "shared-artifacts.json"
    if (sha(bound(previous)) if previous.exists() else None) != p.ledger_before_sha:
        fail("native_unarchived_artifact", "Shared archive ledger changed while the lease was held")
    ledger = {name: {"sha256": sha(path), "archivePath": str(path), "verificationPath": str(verification_path),
                     "verificationSha256": sha(verification_path)} for name, path in copied.items()}
    value = {"schemaVersion": 1, "jobId": p.job_id, "artifacts": ledger}
    temporary = service / ("shared-artifacts-" + p.job_id + ".tmp")
    fresh_json(temporary, value)
    # The previous ledger was preserved in this job's shared-before.json.
    os.replace(temporary, service / "shared-artifacts.json")
    cleared = []
    for name, path in copied.items():
        if name == SLOT: continue
        source = no_links(p.game / name)
        if source.exists():
            archived_entry(ledger[name], source); source.unlink(); cleared.append(name)
    fresh_json(p.root / "shared-cleanup.json", {"archivedVerificationSha256": sha(verification_path),
               "clearedOnlyKnownArchivedFiles": cleared, "scriptSlotRetained": True})


def collect_job(prepared, execution_error=None):
    """Archive even native failures; success additionally requires every real gate."""
    p = prepared
    if not p.executed or p.collected:
        fail("native_job_invalid", "Collection requires one completed host attempt")
    no_private_player()  # execute() closed its job; never detach/clear while Unity lives.
    output = p.root / "output"; output.mkdir(exist_ok=True)
    errors = [] if execution_error is None else ["Host execution failed: " + str(execution_error)]
    unexpected = [path.name for path in output.iterdir() if path.name not in ("player.log", "native-player-run.json")]
    if unexpected: errors.append("Unexpected host output artifacts retained: " + ",".join(unexpected))
    copied = {}
    for name, source in shared_files(p.game).items():
        if name not in LOGS and name not in (SLOT, p.release.data["packetBasename"]):
            errors.append("Unknown shared result retained: " + name); continue
        target = output / ("scene-probe.js" if name == SLOT else name)
        copy_new(source, target); copied[name] = target
    for name in ("request.json", "config.json", "plan.json", "ready.json", "staging.json", "resource-pre.json", "preferences-pre.json"):
        copy_new(p.root / name, output / name)
    copy_new(p.release.path, output / "release-manifest.json")
    run = p.host_result or {"returncode": None, "timed_out": False, "stdout": "", "elapsed_seconds": None, "desktop": None}
    if not (output / "native-player-run.json").exists(): fresh_json(output / "native-player-run.json", run)
    actual_pid = None
    for line in run.get("stdout", "").splitlines():
        try:
            row = json.loads(line)
            if row.get("phase") == "player_pid" and type(row.get("pid")) is int: actual_pid = row["pid"]
        except ValueError: pass
    if actual_pid is None: errors.append("Actual native child PID not recorded")
    try:
        verify_inventory(p.release); unchanged = verify_staging(p.release, p.staging)
        post_plan = p.release.host.validate(p.root / "config.json", fresh_output=False)
        if post_plan["plan_sha256"] != p.plan["plan_sha256"]: fail("native_source_mismatch", "Host inputs changed during the job")
    except Exception as error:
        unchanged = {"releaseOrHostInputs": False}; errors.append(str(error))
    post_preferences = {"status": "failed"}; post_resources = None
    try:
        post_preferences = preference_witness(p.release, p.pre_preferences)
    except Exception as error: errors.append(str(error)); post_preferences["error"] = str(error)
    try:
        post_resources = resource_witness(p.release, p.staging)
        if post_resources["groupStats"] != p.pre_resources["groupStats"]:
            fail("native_resources_changed", "Core/DP identities changed during the original native job")
    except Exception as error: errors.append(str(error))
    fresh_json(output / "preferences-post.json", post_preferences)
    fresh_json(output / "resource-post.json", post_resources or {"status": "failed"})
    scene = output / "scene-events.jsonl"
    rows = []
    if scene.exists():
        if scene.stat().st_size > 16000000: errors.append("Native event output exceeds bounds")
        else:
            try: rows = [json.loads(line) for line in scene.read_text(encoding="utf-8").splitlines()]
            except ValueError as error: errors.append("Malformed native event evidence: " + str(error))
    terminals = [row for row in rows if row.get("status") == "original_practice_terminal_result"]
    terminal = terminals[-1] if terminals else {}
    first_failures = [row for row in rows if row.get("status") == "first_failure"]
    native_errors = [row for row in rows if row.get("phase") == "native_exception"]
    export_errors = [row for row in rows if row.get("status") == "original_practice_packet_export_failed"]
    observations = [row for row in rows if row.get("status") in ("original_practice_full_shared_rng_observed", "original_practice_full_shared_rng_read_failed")]
    gate = p.release.gate.verify(rows, terminal, p.release.expected, RNG_SHA)
    if gate["status"] != "passed": errors.append("Full shared RNG gate failed")
    packet = output / p.release.data["packetBasename"]; decoded = None
    decoder_path = output / "independent-packet-decode.json"
    if terminal.get("originalPacketExported") is True and packet.exists() and all(unchanged.values()):
        try:
            mode = read_json(Path(p.staging["sources"]["modeInput"]["path"]))
            decoded = p.release.decoder.decode_archived_packet(packet, decoder_path, terminal, mode,
                       p.release.file("decoderBuildReceiptFile"))
        except Exception as error: errors.append("Independent original packet decode failed: " + str(error))
    packet_ok = decoded is not None and decoded.get("status") == "passed"
    complete = terminal.get("completeBattle") is True and (terminal.get("verification") or {}).get("passed") is True
    quit_requested = any(row.get("phase") == "quit_requested" for row in rows)
    preferences_ok = post_preferences.get("status") == "passed"
    if not complete or not packet_ok or not quit_requested or run.get("returncode") != 0 or run.get("timed_out") is not False or \
       not str(run.get("desktop", "")).startswith("NikkeCatalogProbe_") or first_failures or native_errors or export_errors or not preferences_ok:
        errors.append("Original native completion/export/exit/isolation check failed")
    artifact = {"filename": packet.name, "format": "protobuf_wire", "sha256": sha(packet), "byteLength": packet.stat().st_size,
                "bytesRewritten": False} if packet.exists() else None
    verification = {"schemaVersion": 1, "status": "failed" if errors else "passed", "jobId": p.job_id,
        "releaseManifestSha256": p.release.sha, "planSha256": p.plan["plan_sha256"], "captureSha256": p.staging["captureSha256"],
        "exitCode": run.get("returncode"), "timedOut": run.get("timed_out"), "elapsedSeconds": run.get("elapsed_seconds"),
        "actualPlayerPid": actual_pid, "deadChild": {"privateImageAbsent": True}, "privateDesktop": run.get("desktop"),
        "frozenSourceInputsUnchanged": unchanged, "firstFailures": first_failures, "nativeExceptions": native_errors,
        "originalPacketExportFailures": export_errors, "errors": errors, "terminalResults": terminals, "completeBattle": complete,
        "requiredPreferenceStorageControlsPassed": preferences_ok, "autoPreferenceWitnesses": {
            "pre": {"sha256": sha(output / "preferences-pre.json"), "evidence": p.pre_preferences},
            "post": {"sha256": sha(output / "preferences-post.json"), "evidence": post_preferences}},
        "resourceInputIdentitiesUnchanged": post_resources is not None and post_resources["groupStats"] == p.pre_resources["groupStats"],
        "originalPacketExportVerified": packet_ok, "originalPacketArtifact": artifact, "originalPacketFilename": packet.name,
        "independentManagedPacketDecode": decoded, "requiredFullSharedRngStateVerified": gate["status"] == "passed",
        "fullSharedRngStateVerification": gate, "fullSharedRngStateObservations": observations,
        "normalNativeQuitRequested": quit_requested,
        "shutdownExceptionsRetained": [row for row in rows if row.get("phase") == "native_shutdown_exception"],
        "fullAccuracyVerified": False, "productionIntegrated": False,
        "artifacts": {path.name: sha(path) for path in output.iterdir() if path.is_file()}}
    # Validate the report projection before committing successful evidence.
    if not errors:
        try: result_from_evidence(p, {**verification, "status": "passed"}, decoder_path, validate_only=True)
        except Exception as error: errors.append(str(error)); verification["status"] = "failed"
    verification_path = output / "verification.json"
    fresh_json(verification_path, verification)
    p.collected = True
    _finish_shared(p, verification_path, copied)
    p.progress("archived")
    if verification["status"] != "passed":
        fail("native_verification_failed", "Native job failed; immutable evidence retained at " + str(verification_path))
    return result_from_evidence(p, verification, decoder_path)


def run_job(prepared):
    """Run once under the retained lease; always wait for the bounded host."""
    p = prepared
    if p.executed: fail("native_job_invalid", "Native host attempt may not be repeated")
    error = None
    try:
        no_private_player(); verify_inventory(p.release)
        if (p.game / p.release.data["packetBasename"]).exists():
            fail("native_unarchived_artifact", "Original native result must be absent before launch")
        p.executed = True; p.progress("running_private_player")
        try:
            p.host_result = p.release.host.execute(p.root / "config.json", p.root / "ready.json")
        except Exception as problem: error = problem
        return collect_job(p, error)
    except BaseException as problem:
        try: fresh_json(p.root / "job-error.json", {"code": getattr(problem, "code", "native_runner_failed"),
            "error": str(problem), "hostAttempted": p.executed, "immutableArchiveCompleted": p.collected})
        except Exception: pass
        raise
    finally:
        # Existing host execute closes its kill-on-close job before returning or
        # raising. Refuse any cleanup above while a private image remains alive.
        p.lease.close()


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--release-manifest", type=Path, required=True)
    parser.add_argument("--manifest-sha256", required=True)
    parser.add_argument("--job-id", required=True)
    parser.add_argument("--fixture-id", required=True)
    parser.add_argument("--input-source-sha256", required=True)
    parser.add_argument("--result-schema", required=True)
    args = parser.parse_args(argv)
    def emit(value):
        try:
            print(json.dumps(value, separators=(",", ":"), ensure_ascii=True), flush=True)
        except (BrokenPipeError, OSError):
            pass  # A disconnected reader must not abandon a started private run.
    try:
        if args.fixture_id != FIXTURE or args.input_source_sha256 != FIXTURE_SHA or args.result_schema != SCHEMA:
            fail("unsupported_native_input", "Only the approved captured original fixture is supported")
        prepared = prepare_job(args.release_manifest, args.job_id, args.manifest_sha256,
                               lambda phase: emit({"type": "progress", "phase": phase}))
        result = run_job(prepared)
        emit({"type": "result", "result": result}); return 0
    except Exception as error:
        emit({"type": "error", "code": getattr(error, "code", "native_runner_failed"), "error": str(error)[:2000]})
        return 2


if __name__ == "__main__":
    raise SystemExit(main())

