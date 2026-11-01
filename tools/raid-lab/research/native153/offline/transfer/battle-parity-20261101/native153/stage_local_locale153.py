"""Stage only five source-verified original153 local locale/font fixture files.

No game/native initializer is invoked. Root must confirm current153 local-mode
initialization prerequisites before --copy; --check-only is read-only preparation.
"""
import argparse
import ctypes
from ctypes import wintypes
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import shutil

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
SANDBOX = ROOT / "tools/raid-lab/private/native-player153-20261101"
DEST = SANDBOX / "NIKKE/NIKKE/game/nikke_Data/StreamingAssets/lss"
SOURCE = ROOT / "NIKKE/Unity/com_proximabeta_NIKKE/com.shiftup.patch/saus/raw"
PROOF = HERE / "practice-locale-local-source153.json"
PROOF_SHA = "aa94f6f319d74f7226dd070772e928141075d728decba92219afa84c691ce3e3"
LEASE = ROOT / "tools/raid-lab/native_runner_lease.py"
LEASE_SHA = "a019f95b599fa1194dcd59b36d0bfb05530829e60d7c85e025437a991b3d37ca"
RECEIPT = SANDBOX / "local-locale153-fixture1.json"
DEAD_PID = 41980
TARGETS = {"Locale_System": "Locale_System.lsc", "Locale_System.lsc": "Locale_System.lsc.nds",
           "FontCollection": "Asset/FontCollection.lsc", "FontCollection.lsc": "Asset/FontCollection.lsc.nds",
           "lss_fontcollection_en": "Asset/lss_fontcollection_en.bundle"}


def sha(path):
    with Path(path).open("rb") as source:
        return hashlib.file_digest(source, "sha256").hexdigest()


def no_links(path):
    path = Path(path).absolute()
    current = Path(path.anchor)
    for part in path.parts[1:]:
        current /= part
        if current.is_symlink() or (hasattr(os.path, "isjunction") and os.path.isjunction(current)):
            raise ValueError("Locale fixture paths may not traverse links or junctions")
    return path.resolve()


def prepare():
    if sha(no_links(PROOF)) != PROOF_SHA:
        raise ValueError("Exact current153 original locale source proof required")
    proof = json.loads(PROOF.read_text(encoding="utf-8"))
    for item in [proof["deploymentEvidence"], proof["failedNative17"], proof["cardSource"], *proof["catalogs"].values()]:
        if sha(no_links(item["path"])) != item["sha256"]:
            raise ValueError("Original locale/version/catalog/native17 evidence changed")
    rows = proof["assets"]
    if len(rows) != 5 or {row["assetKey"] for row in rows} != set(TARGETS) or proof["failedNative17"]["actualPlayerPid"] != DEAD_PID:
        raise ValueError("Exact five-file current153/closed17 fixture scope required")
    plan = []
    for row in rows:
        source = no_links(row["sourcePath"])
        target = no_links(DEST / TARGETS[row["assetKey"]])
        if source.parent != no_links(SOURCE) or not target.is_relative_to(no_links(DEST)) or \
           str(target) != row["privateTarget"] or row["privateRelativePath"] != TARGETS[row["assetKey"]]:
            raise ValueError("Locale source/canonical private target escaped exact scope")
        if not source.is_file() or source.stat().st_size != row["bytes"] or sha(source) != row["sha256"]:
            raise ValueError("Original publisher locale/font bytes changed")
        exists = target.exists()
        if exists and (not target.is_file() or target.stat().st_nlink != 1 or target.stat().st_size != row["bytes"] or sha(target) != row["sha256"] or os.path.samefile(source, target)):
            raise FileExistsError("Conflicting locale target preserved: " + str(target))
        partial = no_links(target.with_name(target.name + ".locale153.partial"))
        if partial.exists():
            raise FileExistsError("Prior locale copy partial preserved: " + str(partial))
        plan.append({**row, "source": source, "target": target, "partial": partial, "existingIdenticalCopy": exists})
    return proof, plan


def confirm_closed():
    kernel = ctypes.WinDLL("kernel32", use_last_error=True)
    kernel.OpenProcess.argtypes = [wintypes.DWORD, wintypes.BOOL, wintypes.DWORD]
    kernel.OpenProcess.restype = wintypes.HANDLE
    kernel.GetExitCodeProcess.argtypes = [wintypes.HANDLE, ctypes.POINTER(wintypes.DWORD)]
    kernel.GetExitCodeProcess.restype = wintypes.BOOL
    kernel.CloseHandle.argtypes = [wintypes.HANDLE]
    handle = kernel.OpenProcess(0x1000, False, DEAD_PID)
    if not handle:
        error = ctypes.get_last_error()
        if error not in (87, 1168):
            raise ctypes.WinError(error)
        return {"pid": DEAD_PID, "processPresent": False}
    try:
        code = wintypes.DWORD()
        if not kernel.GetExitCodeProcess(handle, ctypes.byref(code)):
            raise ctypes.WinError(ctypes.get_last_error())
        if code.value == 259:
            raise RuntimeError("Known original native17 child is still active")
        return {"pid": DEAD_PID, "processPresent": True, "exitCode": code.value, "stillActive": False}
    finally:
        kernel.CloseHandle(handle)


def stage():
    if os.name != "nt":
        raise RuntimeError("Reviewed private Windows fixture only")
    if sha(no_links(LEASE)) != LEASE_SHA:
        raise ValueError("Reviewed shared runner lease changed")
    spec = importlib.util.spec_from_file_location("locale_fixture_lease153", LEASE)
    module = importlib.util.module_from_spec(spec); spec.loader.exec_module(module)
    with module.NativeRunnerLease(no_links(SANDBOX / "native-service/runner.lock")):
        if no_links(RECEIPT).exists():
            raise FileExistsError("Preserve existing locale fixture receipt")
        closed = confirm_closed()
        proof, plan = prepare()  # All conflicts checked before the first copy.
        copied = []
        for row in plan:
            source, target, partial = row["source"], row["target"], row["partial"]
            if not row["existingIdenticalCopy"]:
                target.parent.mkdir(parents=True, exist_ok=True)
                with source.open("rb") as incoming, partial.open("xb") as outgoing:
                    shutil.copyfileobj(incoming, outgoing, 1048576)
                if sha(source) != row["sha256"] or sha(partial) != row["sha256"] or partial.stat().st_size != row["bytes"]:
                    raise ValueError("Locale copy readback differs; partial preserved")
                os.rename(partial, target)  # Windows rename refuses an existing target.
            if sha(target) != row["sha256"] or target.stat().st_nlink != 1 or os.path.samefile(source, target):
                raise ValueError("Locale fixture must be an independent exact byte copy")
            copied.append({"assetKey": row["assetKey"], "source": str(source), "target": str(target),
                           "sha256": row["sha256"], "bytes": row["bytes"], "existingIdenticalCopy": row["existingIdenticalCopy"]})
        report = {"schemaVersion": 1, "status": "original153_local_fixture_bytes_staged", "sourceProofSha256": PROOF_SHA,
                  "sourceProofPath": str(PROOF), "helperSourceSha256": sha(Path(__file__)), "leaseSourceSha256": LEASE_SHA,
                  "exclusiveLeaseHeld": True, "knownChildClosed": closed, "copies": copied,
                  "installedFilesWritten": False, "catalogsRewritten": False, "signatureBytesChanged": False,
                  "nativeInitializerInvoked": False, "nativeLocalRegistrationVerified": False,
                  "nativeRunPerformed": False, "localeScope": "en font closure; original Locale_System table retains all source languages"}
        with RECEIPT.open("x", encoding="utf-8", newline="\n") as sink:
            json.dump(report, sink, indent=2); sink.write("\n")
        return report


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--check-only", action="store_true")
    group.add_argument("--copy", action="store_true")
    args = parser.parse_args()
    if args.check_only:
        proof, plan = prepare()
        print(json.dumps({"status": "validated_static_copy_plan", "files": len(plan), "bytes": sum(row["bytes"] for row in plan),
                          "existingMatchingTargets": sum(row["existingIdenticalCopy"] for row in plan), "copied": False, "nativeRunPerformed": False}))
    else:
        stage()
        print(json.dumps({"receipt": str(RECEIPT), "sha256": sha(RECEIPT), "files": 5, "nativeRunPerformed": False}))
