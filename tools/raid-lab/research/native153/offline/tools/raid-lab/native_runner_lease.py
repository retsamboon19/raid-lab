"""Exclusive Windows lease for the shared private original-engine sandbox.

This is runner coordination only. It neither launches Unity nor computes combat.
Retain the lease through child exit, archival and post-run witnesses.
"""

from __future__ import annotations

import ctypes
from ctypes import wintypes
import os
from pathlib import Path


class RunnerBusy(RuntimeError):
    pass


class NativeRunnerLease:
    """Hold a share-mode-zero handle; process exit also releases the lease."""

    def __init__(self, path: Path):
        self.path = Path(path)
        self._handle = None
        self._kernel = None

    def acquire(self):
        if self._handle is not None:
            raise RuntimeError("Runner lease is already held by this instance")
        if os.name != "nt":
            raise RuntimeError("Original native runner requires Windows")
        if not self.path.is_absolute() or ".." in self.path.parts:
            raise ValueError("Runner lease path must be absolute without traversal")
        current = Path(self.path.anchor)
        for part in self.path.parts[1:]:
            current /= part
            if current.is_symlink() or (hasattr(os.path, "isjunction") and os.path.isjunction(current)):
                raise ValueError("Runner lease path traverses a link or junction")
        if not self.path.parent.is_dir():
            raise ValueError("Runner service directory must already exist")
        kernel = ctypes.WinDLL("kernel32", use_last_error=True)
        kernel.CreateFileW.argtypes = [wintypes.LPCWSTR, wintypes.DWORD, wintypes.DWORD,
                                      wintypes.LPVOID, wintypes.DWORD, wintypes.DWORD,
                                      wintypes.HANDLE]
        kernel.CreateFileW.restype = wintypes.HANDLE
        kernel.CloseHandle.argtypes = [wintypes.HANDLE]
        kernel.CloseHandle.restype = wintypes.BOOL
        # OPEN_ALWAYS leaves an existing coordination file intact. No truncate,
        # delete-on-close, shared handle or inheritable handle is requested.
        handle = kernel.CreateFileW(str(self.path), 0x80000000 | 0x40000000,
                                    0, None, 4, 0x80, None)
        if handle == ctypes.c_void_p(-1).value:
            code = ctypes.get_last_error()
            if code in (32, 33):
                raise RunnerBusy("The original native battle runner is busy")
            raise ctypes.WinError(code)
        self._kernel, self._handle = kernel, handle
        return self

    def close(self):
        if self._handle is None:
            return
        if not self._kernel.CloseHandle(self._handle):
            raise ctypes.WinError(ctypes.get_last_error())
        self._handle = None

    def __enter__(self):
        return self.acquire()

    def __exit__(self, exc_type, exc, traceback):
        self.close()

