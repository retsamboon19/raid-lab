"""Prepare/run one exact-sandbox deny-all self-test, never Unity or combat.

Default prints the intended scope. --run is required to load the staged guard
inside the existing bounded private desktop; use after coordinating with parent.
"""
import argparse
import ctypes as C
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import socket
import sys
import winreg

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
SANDBOX = ROOT / "tools/raid-lab/private/native-player153-20261101"
DLL = SANDBOX / "NIKKE/NIKKE/game/OfflineNetwork.dll"
REPAIR = ROOT / "event-selector/chainsaw-man/catalog-repair"


def sha(path):
    with path.open("rb") as source:
        return hashlib.file_digest(source, "sha256").hexdigest()


def load(path, name):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def worker():
    guard = load(REPAIR / "full-native/probe.py", "deny_all153_private_guard")
    guard.require_private_desktop()
    receipt = json.loads((SANDBOX / "helper-build-receipt.json").read_text())
    if receipt["artifacts"]["OfflineNetwork.dll"] != sha(DLL):
        raise ValueError("Fresh153 guard differs from reviewed build")
    os.environ["NIKKE_OFFLINE_ROOT"] = str(SANDBOX)
    existing = socket.socket()
    original = winreg.OpenKey(winreg.HKEY_CURRENT_USER, "Software", 0, winreg.KEY_READ)
    dll = C.WinDLL(str(DLL))
    initialize = dll.InitializeOfflineNetwork
    initialize.restype, initialize.argtypes = C.c_int, []
    if initialize() != 1:
        raise ValueError("Deny-all guard initialization failed")
    cases = []
    try:
        existing.connect(("127.0.0.1", 80))
        raise AssertionError("Loopback unexpectedly allowed")
    except OSError as error:
        if error.winerror != 10013:
            raise
        cases.append("existing_socket_loopback_denied")
    try:
        socket.socket()
        raise AssertionError("New socket unexpectedly allowed")
    except OSError as error:
        if error.winerror != 10013:
            raise
        cases.append("new_socket_denied")
    with winreg.CreateKey(winreg.HKEY_CURRENT_USER, "Probe") as key:
        winreg.SetValueEx(key, "value", 0, winreg.REG_SZ, "scratch-only")
    path = "RaidLabNativeSandbox\\" + SANDBOX.name + "\\Probe"
    with winreg.OpenKey(original, path) as key:
        if winreg.QueryValueEx(key, "value")[0] != "scratch-only":
            raise ValueError("Scratch HKCU readback mismatch")
    cases.append("HKCU_redirect_verified")
    folder = C.create_unicode_buffer(260)
    shell = C.WinDLL("shell32")
    if shell.SHGetFolderPathW(None, 28, None, 0, folder) != 0 or \
            Path(folder.value) != SANDBOX / "profile/AppData/Local":
        raise ValueError("Scratch known-folder readback mismatch")
    cases.append("known_folder_redirect_verified")
    print(json.dumps({"phase": "guard_result", "passed": cases}), flush=True)
    os._exit(0)


def main():
    isolated = load(REPAIR / "isolated_desktop.py", "deny_all153_isolated")
    artifact = sha(DLL)
    with isolated.IsolatedDesktop() as desktop:
        command = [sys.executable, "-u", str(Path(__file__).resolve()), "--worker"]
        run = desktop.run(command, cwd=SANDBOX, timeout=15, text=True)
        target = SANDBOX / ("guard-test-" + desktop.name + ".json")
        result = {"returncode": run.returncode, "stdout": run.stdout, "stderr": run.stderr,
                  "artifact_sha256": artifact, "private_desktop": desktop.name,
                  "sandbox_root": str(SANDBOX), "source_sha256": sha(Path(__file__)),
                  "game_launched": False, "combat_invoked": False}
        if sha(DLL) != artifact:
            raise ValueError("Guard changed during selftest")
        with target.open("x", encoding="utf-8") as sink:
            json.dump(result, sink, indent=2)
            sink.write("\n")
        print(json.dumps({"returncode": run.returncode, "report": str(target)}))
        return run.returncode


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--worker", action="store_true")
    parser.add_argument("--run", action="store_true")
    args = parser.parse_args()
    if args.worker:
        try:
            worker()
        except BaseException as error:
            print(json.dumps({"phase": "worker_error", "error": repr(error)}), flush=True)
            os._exit(2)
    elif args.run:
        sys.exit(main())
    else:
        print(json.dumps({"sandbox": str(SANDBOX), "scope": "Private guard self-test only; requires --run",
                          "gameLaunched": False, "guardLoaded": False}))
