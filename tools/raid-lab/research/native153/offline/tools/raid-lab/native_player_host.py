"""Bounded private-desktop host for a staged Unity player, never the production launcher.

Dry-run validates a separately prepared clone and its bootstrap/network receipts.
Execution additionally requires an integration-ready receipt bound to that plan.
This module does not prepare a clone, start a backend, or install native hooks.
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
import subprocess
import sys
import time


WORKSPACE = Path(__file__).resolve().parents[2]
PRIVATE = WORKSPACE / 'tools/raid-lab/private'
HARNESS = WORKSPACE / 'event-selector/first-anniversary/catalog-repair/isolated_desktop.py'
REQUIRED_FILES = {'nikke.exe', 'UnityPlayer.dll', 'GameAssembly.dll',
                  'nikkeBase.dll', 'OfflineNetwork.dll'}
DIAGNOSTIC_FILES = {'d3d11.dll', 'frida-gadget.dll', 'frida-gadget.config',
                    'NKAB/dist/scene-probe.js'}
MAX_SECONDS = 180


def digest(path: Path) -> str:
    h = hashlib.sha256()
    with path.open('rb') as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b''):
            h.update(chunk)
    return h.hexdigest()


def canonical_json(value) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(',', ':')).encode('utf-8')


def require_absolute(value: str, name: str) -> Path:
    path = Path(value)
    if not path.is_absolute():
        raise ValueError(f'{name} must be absolute')
    if '..' in path.parts:
        raise ValueError(f'{name} may not contain parent traversal')
    current = Path(path.anchor)
    for part in path.parts[1:]:
        current = current / part
        if current.is_symlink() or (hasattr(os.path, 'isjunction') and os.path.isjunction(current)):
            raise ValueError(f'{name} traverses a link or junction')
    return path.resolve(strict=False)


def inside(path: Path, root: Path, name: str) -> Path:
    if not path.is_relative_to(root):
        raise ValueError(f'{name} escapes sandbox root')
    return path


def no_links(path: Path, root: Path, name: str) -> None:
    if root.is_symlink() or (hasattr(os.path, 'isjunction') and os.path.isjunction(root)):
        raise ValueError(f'{name} traverses a link or junction')
    current = root
    for part in path.relative_to(root).parts:
        current = current / part
        if current.is_symlink() or (hasattr(os.path, 'isjunction') and os.path.isjunction(current)):
            raise ValueError(f'{name} traverses a link or junction')


def bounded_file(path: Path, root: Path, name: str) -> Path:
    inside(path, root, name)
    no_links(path, root, name)
    if not path.is_file():
        raise ValueError(f'{name} missing: {path}')
    if path.stat().st_nlink != 1:
        raise ValueError(f'{name} must be a separate copy, not a hardlink')
    return path


def _receipt(path: Path, root: Path, mode: str, artifacts: dict[str, str]) -> tuple[dict, str]:
    bounded_file(path, root, f'{mode} receipt')
    value = json.loads(path.read_text(encoding='utf-8'))
    if value.get('schema_version') != 1 or value.get('mode') != mode:
        raise ValueError(f'{mode} receipt schema/mode mismatch')
    if require_absolute(value.get('sandbox_root', ''), 'receipt sandbox_root') != root:
        raise ValueError(f'{mode} receipt bound to another sandbox')
    for key, expected in artifacts.items():
        if value.get('artifacts', {}).get(key) != expected:
            raise ValueError(f'{mode} receipt artifact mismatch: {key}')
    return value, digest(path)


def validate(config_path: Path, *, fresh_output: bool = True) -> dict:
    config_path = config_path.resolve(strict=True)
    config = json.loads(config_path.read_text(encoding='utf-8'))
    if config.get('schema_version') != 1:
        raise ValueError('Player config schema_version must be 1')
    root = require_absolute(config['sandbox_root'], 'sandbox_root')
    if not root.is_relative_to(PRIVATE) or root == PRIVATE:
        raise ValueError('sandbox_root must be a dedicated directory under tools/raid-lab/private')
    if root.is_symlink() or (hasattr(os.path, 'isjunction') and os.path.isjunction(root)):
        raise ValueError('sandbox_root is a link or junction')
    if not root.is_dir():
        raise ValueError('sandbox_root missing')
    bounded_file(config_path, root, 'config')
    game = require_absolute(config['game_executable'], 'game_executable')
    game_dir = require_absolute(config['working_directory'], 'working_directory')
    expected_dir = root / 'NIKKE/NIKKE/game'
    if game != expected_dir / 'nikke.exe' or game_dir != expected_dir:
        raise ValueError('Player must be the staged NIKKE/NIKKE/game/nikke.exe')
    scratch = require_absolute(config['scratch_root'], 'scratch_root')
    if scratch != root / 'profile':
        raise ValueError('scratch_root must be the staged profile')
    no_links(game_dir, root, 'working_directory')
    no_links(scratch, root, 'scratch_root')
    if not scratch.is_dir():
        raise ValueError('scratch_root missing')
    output = require_absolute(config['output_dir'], 'output_dir')
    inside(output, root, 'output_dir')
    no_links(output, root, 'output_dir')
    if output == root or output.is_relative_to(game_dir) or output.is_relative_to(scratch):
        raise ValueError('output_dir must be separate from player and profile')
    if fresh_output and output.exists() and any(output.iterdir()):
        raise ValueError('output_dir must be empty for a new player run')
    if (root / 'local-account.json').exists() or (root / 'isolated/bin/OfflineLauncher.exe').exists():
        raise ValueError('Production account or launcher is present in player sandbox')
    max_seconds = config['max_seconds']
    if not isinstance(max_seconds, int) or not 1 <= max_seconds <= MAX_SECONDS:
        raise ValueError(f'max_seconds must be 1..{MAX_SECONDS}')
    args = config.get('args', [])
    if not isinstance(args, list) or not all(isinstance(x, str) and '\x00' not in x for x in args):
        raise ValueError('args must be a list of command arguments')
    if any(x.lower() in ('-logfile', '--logfile') for x in args):
        raise ValueError('logFile path is controlled by the host')
    files = config['expected_files']
    if set(files) != REQUIRED_FILES:
        raise ValueError('expected_files must name the five required player/guard binaries')
    checked = {}
    for name, item in files.items():
        path = require_absolute(item['path'], name)
        if path != game_dir / name:
            raise ValueError(f'{name} must be in staged game directory')
        bounded_file(path, root, name)
        actual = digest(path)
        if actual != item['sha256']:
            raise ValueError(f'{name} hash mismatch')
        checked[name] = actual
    if game != require_absolute(files['nikke.exe']['path'], 'nikke.exe'):
        raise ValueError('game_executable differs from expected_files')
    diagnostics = config.get('diagnostic_files', {})
    if not isinstance(diagnostics, dict):
        raise ValueError('diagnostic_files must be a dictionary')
    if diagnostics and set(diagnostics) != DIAGNOSTIC_FILES:
        raise ValueError('diagnostic_files must bind all four probe artifacts')
    if (game_dir / 'frida-gadget.config').exists() and set(diagnostics) != DIAGNOSTIC_FILES:
        raise ValueError('staged gadget config requires diagnostic_files binding')
    checked_diagnostics = {}
    for name, item in diagnostics.items():
        path = require_absolute(item['path'], name)
        if path != game_dir / name:
            raise ValueError(f'{name} must be at its staged player path')
        bounded_file(path, root, name)
        actual = digest(path)
        if actual != item['sha256']:
            raise ValueError(f'{name} hash mismatch')
        checked_diagnostics[name] = actual
    bootstrap_path = require_absolute(config['bootstrap_receipt'], 'bootstrap_receipt')
    network_path = require_absolute(config['network_receipt'], 'network_receipt')
    bootstrap, bootstrap_hash = _receipt(bootstrap_path, root, 'unity_player_bootstrap',
                                         {'nikkeBase.dll': checked['nikkeBase.dll']})
    network, network_hash = _receipt(network_path, root, 'deny_all',
                                     {'OfflineNetwork.dll': checked['OfflineNetwork.dll']})
    if bootstrap.get('private_desktop_guard') is not True:
        raise ValueError('bootstrap has no private desktop self-check')
    if network.get('registry_mode') != 'sandbox' or network.get('known_folder_mode') != 'sandbox':
        raise ValueError('network/host guard lacks scratch registry and known folders')
    if network.get('self_test_passed') is not True:
        raise ValueError('deny-all guard has no passing self-test receipt')
    plan = dict(schema_version=1, config_path=str(config_path), config_sha256=digest(config_path),
                sandbox_root=str(root), game_executable=str(game), working_directory=str(game_dir),
                scratch_root=str(scratch), output_dir=str(output), max_seconds=max_seconds,
                args=args, expected_files=checked, diagnostic_files=checked_diagnostics,
                host_sha256=digest(Path(__file__).resolve()), harness_sha256=digest(HARNESS),
                bootstrap_receipt_sha256=bootstrap_hash,
                network_receipt_sha256=network_hash, network_mode='deny_all', backend_mode='none')
    plan['plan_sha256'] = hashlib.sha256(canonical_json(plan)).hexdigest()
    return plan


def desktop_name() -> str:
    if sys.platform != 'win32':
        raise RuntimeError('Private desktop requires Windows')
    user = ctypes.WinDLL('user32', use_last_error=True)
    kernel = ctypes.WinDLL('kernel32', use_last_error=True)
    user.GetThreadDesktop.argtypes = [wintypes.DWORD]
    user.GetThreadDesktop.restype = wintypes.HANDLE
    user.GetUserObjectInformationW.argtypes = [wintypes.HANDLE, ctypes.c_int, ctypes.c_void_p,
                                               wintypes.DWORD, ctypes.POINTER(wintypes.DWORD)]
    user.GetUserObjectInformationW.restype = wintypes.BOOL
    kernel.GetCurrentThreadId.restype = wintypes.DWORD
    buffer = ctypes.create_unicode_buffer(256)
    length = wintypes.DWORD()
    handle = user.GetThreadDesktop(kernel.GetCurrentThreadId())
    if not user.GetUserObjectInformationW(handle, 2, buffer, ctypes.sizeof(buffer), ctypes.byref(length)):
        raise ctypes.WinError(ctypes.get_last_error())
    return buffer.value


def worker(config_path: Path, expected_hash: str, expected_desktop: str, gate: Path) -> int:
    if desktop_name() != expected_desktop or not expected_desktop.startswith('NikkeCatalogProbe_'):
        raise RuntimeError('Player worker is not on the assigned private desktop')
    deadline = time.monotonic() + 10
    while not gate.is_file() and time.monotonic() < deadline:
        time.sleep(.05)
    if not gate.is_file():
        raise RuntimeError('Parent job-assignment gate did not open')
    plan = validate(config_path, fresh_output=False)
    if plan['plan_sha256'] != expected_hash:
        raise RuntimeError('Player inputs changed after parent validation')
    root = Path(plan['sandbox_root'])
    scratch = Path(plan['scratch_root'])
    output = Path(plan['output_dir'])
    env = os.environ.copy()
    env.update(NIKKE_OFFLINE_ROOT=str(root), USERPROFILE=str(scratch),
               APPDATA=str(scratch / 'AppData/Roaming'),
               LOCALAPPDATA=str(scratch / 'AppData/Local'),
               TEMP=str(scratch / 'Temp'), TMP=str(scratch / 'Temp'))
    for name in ('AppData/Roaming', 'AppData/Local', 'Temp'):
        (scratch / name).mkdir(parents=True, exist_ok=True)
    command = [plan['game_executable'], *plan['args'], '-logFile', str(output / 'player.log')]
    print(json.dumps({'phase': 'player_start', 'desktop': expected_desktop,
                      'plan_sha256': expected_hash}), flush=True)
    with subprocess.Popen(command, cwd=plan['working_directory'], env=env,
                          stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL,
                          stderr=subprocess.DEVNULL, close_fds=True) as child:
        print(json.dumps({'phase': 'player_pid', 'pid': child.pid}), flush=True)
        try:
            return child.wait(timeout=plan['max_seconds'])
        except subprocess.TimeoutExpired:
            child.terminate()
            try:
                child.wait(timeout=3)
            except subprocess.TimeoutExpired:
                child.kill()
                child.wait(timeout=3)
            print(json.dumps({'phase': 'player_timeout', 'pid': child.pid}), flush=True)
            return 124


class KillOnCloseJob:
    """Win32 job assigned before opening the worker gate; descendants inherit it."""

    def __init__(self):
        if sys.platform != 'win32':
            raise RuntimeError('Windows job objects are required')
        self.kernel = ctypes.WinDLL('kernel32', use_last_error=True)
        self.kernel.CreateJobObjectW.restype = wintypes.HANDLE
        self.kernel.CreateJobObjectW.argtypes = [ctypes.c_void_p, wintypes.LPCWSTR]
        self.kernel.SetInformationJobObject.argtypes = [wintypes.HANDLE, ctypes.c_int,
                                                         ctypes.c_void_p, wintypes.DWORD]
        self.kernel.AssignProcessToJobObject.argtypes = [wintypes.HANDLE, wintypes.HANDLE]
        self.kernel.CloseHandle.argtypes = [wintypes.HANDLE]
        self.handle = self.kernel.CreateJobObjectW(None, None)
        if not self.handle:
            raise ctypes.WinError(ctypes.get_last_error())
        # JOBOBJECT_EXTENDED_LIMIT_INFORMATION: 16-byte basic limits on x64
        # are not enough; use the complete documented ctypes layout below.
        class IO_COUNTERS(ctypes.Structure):
            _fields_ = [(x, ctypes.c_uint64) for x in ('ReadOperationCount', 'WriteOperationCount',
                         'OtherOperationCount', 'ReadTransferCount', 'WriteTransferCount',
                         'OtherTransferCount')]
        class BASIC(ctypes.Structure):
            _fields_ = [('PerProcessUserTimeLimit', ctypes.c_int64),
                        ('PerJobUserTimeLimit', ctypes.c_int64), ('LimitFlags', wintypes.DWORD),
                        ('MinimumWorkingSetSize', ctypes.c_size_t),
                        ('MaximumWorkingSetSize', ctypes.c_size_t),
                        ('ActiveProcessLimit', wintypes.DWORD), ('Affinity', ctypes.c_size_t),
                        ('PriorityClass', wintypes.DWORD), ('SchedulingClass', wintypes.DWORD)]
        class EXTENDED(ctypes.Structure):
            _fields_ = [('BasicLimitInformation', BASIC), ('IoInfo', IO_COUNTERS),
                        ('ProcessMemoryLimit', ctypes.c_size_t), ('JobMemoryLimit', ctypes.c_size_t),
                        ('PeakProcessMemoryUsed', ctypes.c_size_t),
                        ('PeakJobMemoryUsed', ctypes.c_size_t)]
        info = EXTENDED()
        info.BasicLimitInformation.LimitFlags = 0x2000  # JOB_OBJECT_LIMIT_KILL_ON_JOB_CLOSE
        if not self.kernel.SetInformationJobObject(self.handle, 9, ctypes.byref(info), ctypes.sizeof(info)):
            error = ctypes.WinError(ctypes.get_last_error())
            self.close()
            raise error

    def assign(self, process_handle) -> None:
        if not self.kernel.AssignProcessToJobObject(self.handle, process_handle):
            raise ctypes.WinError(ctypes.get_last_error())

    def close(self) -> None:
        if self.handle:
            self.kernel.CloseHandle(self.handle)
            self.handle = None


def execute(config_path: Path, ready_path: Path) -> dict:
    config_path = config_path.resolve(strict=True)
    ready_path = ready_path.resolve(strict=True)
    plan = validate(config_path)
    root = Path(plan['sandbox_root'])
    bounded_file(ready_path, root, 'integration-ready receipt')
    ready = json.loads(ready_path.read_text(encoding='utf-8'))
    if (ready.get('schema_version') != 1 or ready.get('status') != 'integration_ready'
            or ready.get('plan_sha256') != plan['plan_sha256']
            or ready.get('sandbox_root') != plan['sandbox_root']):
        raise ValueError('integration-ready receipt does not bind this exact player plan')
    output = Path(plan['output_dir'])
    output.mkdir(parents=True, exist_ok=True)
    gate = output / ('player-job-gate-' + plan['plan_sha256'][:16])
    if gate.exists():
        raise ValueError('Stale job-assignment gate exists')
    spec = importlib.util.spec_from_file_location('_private_desktop_player', HARNESS)
    harness = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(harness)
    started = time.monotonic()
    job = None
    desktop = None
    child = None
    try:
        with harness.IsolatedDesktop() as desktop:
            try:
                child = desktop.popen([sys.executable, '-u', str(Path(__file__).resolve()),
                                       '--worker', '--config', str(config_path),
                                       '--plan-sha256', plan['plan_sha256'],
                                       '--desktop-name', desktop.name, '--gate', str(gate)], cwd=output)
                job = KillOnCloseJob()
                job.assign(child._process)
                gate.write_text(plan['plan_sha256'], encoding='ascii')
                try:
                    stdout, stderr = child.communicate(timeout=plan['max_seconds'] + 15, text=True)
                    returncode = child.returncode
                    timed_out = returncode == 124
                except subprocess.TimeoutExpired as exc:
                    stdout, stderr = exc.stdout or '', exc.stderr or ''
                    returncode, timed_out = None, True
            finally:
                if job:
                    job.close()  # Kill worker and every descendant before closing desktop.
    finally:
        if gate.exists():
            gate.unlink()
    report = dict(schema_version=1, plan_sha256=plan['plan_sha256'],
                  ready_receipt_sha256=digest(ready_path), desktop=desktop.name if desktop else None,
                  worker_pid=child.pid if child else None, returncode=returncode,
                  timed_out=timed_out, elapsed_seconds=round(time.monotonic() - started, 3),
                  stdout=str(stdout)[-8192:], stderr=str(stderr)[-8192:])
    (output / 'native-player-run.json').write_text(json.dumps(report, indent=2), encoding='utf-8')
    return report


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--config', type=Path, required=True)
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument('--dry-run', action='store_true')
    group.add_argument('--run', action='store_true')
    group.add_argument('--worker', action='store_true', help=argparse.SUPPRESS)
    parser.add_argument('--integration-ready', type=Path)
    parser.add_argument('--plan-sha256', help=argparse.SUPPRESS)
    parser.add_argument('--desktop-name', help=argparse.SUPPRESS)
    parser.add_argument('--gate', type=Path, help=argparse.SUPPRESS)
    args = parser.parse_args()
    if args.worker:
        if not all((args.plan_sha256, args.desktop_name, args.gate)):
            parser.error('worker requires parent plan, desktop, and gate')
        return worker(args.config, args.plan_sha256, args.desktop_name, args.gate)
    if args.dry_run:
        print(json.dumps(validate(args.config), indent=2))
        return 0
    if not args.integration_ready:
        parser.error('--run requires --integration-ready')
    report = execute(args.config, args.integration_ready)
    print(json.dumps(report, indent=2))
    return 0 if report['returncode'] == 0 and not report['timed_out'] else 1


if __name__ == '__main__':
    raise SystemExit(main())
