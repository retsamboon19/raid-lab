"""Run bounded Windows children on a private desktop that is never activated.

Python's subprocess.STARTUPINFO does not pass lpDesktop through to CreateProcess.
This module calls CreateProcessW directly and inherits only three stdio handles.
It never switches desktops or attaches to an existing process.
"""
from __future__ import annotations

import ctypes as C
from ctypes import wintypes as W
import json
import msvcrt
import os
import subprocess
import sys
import threading
import time
import uuid

GENERIC_ALL=0x10000000
GENERIC_READ=0x80000000
CREATE_NO_WINDOW=0x08000000
EXTENDED_STARTUPINFO_PRESENT=0x00080000
STARTF_USESHOWWINDOW=1
STARTF_USESTDHANDLES=0x100
PROC_THREAD_ATTRIBUTE_HANDLE_LIST=0x00020002
WAIT_OBJECT_0=0
WAIT_TIMEOUT=0x102
INFINITE=0xffffffff
STILL_ACTIVE=259
INVALID_HANDLE_VALUE=C.c_void_p(-1).value


class SECURITY_ATTRIBUTES(C.Structure):
    _fields_=[('nLength',W.DWORD),('lpSecurityDescriptor',W.LPVOID),('bInheritHandle',W.BOOL)]


class STARTUPINFOW(C.Structure):
    _fields_=[('cb',W.DWORD),('lpReserved',W.LPWSTR),('lpDesktop',W.LPWSTR),
              ('lpTitle',W.LPWSTR),('dwX',W.DWORD),('dwY',W.DWORD),('dwXSize',W.DWORD),
              ('dwYSize',W.DWORD),('dwXCountChars',W.DWORD),('dwYCountChars',W.DWORD),
              ('dwFillAttribute',W.DWORD),('dwFlags',W.DWORD),('wShowWindow',W.WORD),
              ('cbReserved2',W.WORD),('lpReserved2',C.POINTER(W.BYTE)),
              ('hStdInput',W.HANDLE),('hStdOutput',W.HANDLE),('hStdError',W.HANDLE)]


class STARTUPINFOEXW(C.Structure):
    _fields_=[('StartupInfo',STARTUPINFOW),('lpAttributeList',W.LPVOID)]


class PROCESS_INFORMATION(C.Structure):
    _fields_=[('hProcess',W.HANDLE),('hThread',W.HANDLE),
              ('dwProcessId',W.DWORD),('dwThreadId',W.DWORD)]


def _api():
    k=C.WinDLL('kernel32',use_last_error=True)
    u=C.WinDLL('user32',use_last_error=True)
    signatures={
        'CreatePipe':([C.POINTER(W.HANDLE),C.POINTER(W.HANDLE),C.POINTER(SECURITY_ATTRIBUTES),W.DWORD],W.BOOL),
        'SetHandleInformation':([W.HANDLE,W.DWORD,W.DWORD],W.BOOL),
        'CreateFileW':([W.LPCWSTR,W.DWORD,W.DWORD,C.POINTER(SECURITY_ATTRIBUTES),W.DWORD,W.DWORD,W.HANDLE],W.HANDLE),
        'InitializeProcThreadAttributeList':([W.LPVOID,W.DWORD,W.DWORD,C.POINTER(C.c_size_t)],W.BOOL),
        'UpdateProcThreadAttribute':([W.LPVOID,W.DWORD,C.c_size_t,W.LPVOID,C.c_size_t,W.LPVOID,C.POINTER(C.c_size_t)],W.BOOL),
        'DeleteProcThreadAttributeList':([W.LPVOID],None),
        'CreateProcessW':([W.LPCWSTR,W.LPWSTR,W.LPVOID,W.LPVOID,W.BOOL,W.DWORD,W.LPVOID,W.LPCWSTR,C.POINTER(STARTUPINFOW),C.POINTER(PROCESS_INFORMATION)],W.BOOL),
        'WaitForSingleObject':([W.HANDLE,W.DWORD],W.DWORD),
        'GetExitCodeProcess':([W.HANDLE,C.POINTER(W.DWORD)],W.BOOL),
        'TerminateProcess':([W.HANDLE,W.UINT],W.BOOL),
        'CancelIoEx':([W.HANDLE,W.LPVOID],W.BOOL),
        'CloseHandle':([W.HANDLE],W.BOOL),
    }
    for name,(args,restype) in signatures.items():
        fn=getattr(k,name);fn.argtypes=args;fn.restype=restype
    u.CreateDesktopW.argtypes=[W.LPCWSTR,W.LPCWSTR,W.LPVOID,W.DWORD,W.DWORD,W.LPVOID]
    u.CreateDesktopW.restype=W.HANDLE
    u.CloseDesktop.argtypes=[W.HANDLE]
    u.CloseDesktop.restype=W.BOOL
    return k,u


def _checked(value):
    if not value:
        raise C.WinError(C.get_last_error())
    return value


class DesktopProcess:
    """Popen-like owner of one process started on the private desktop."""
    def __init__(self,k,info,stdout,stderr):
        self._k=k
        self._process=info.hProcess
        self._thread=info.hThread
        self.pid=info.dwProcessId
        self.stdout=stdout
        self.stderr=stderr
        self.returncode=None
        self._closed=False
        self._readers=[]
        self._chunks=[bytearray(),bytearray()]
        self._reader_errors=[]

    def _signal_state(self):
        outcome=self._k.WaitForSingleObject(self._process,0)
        if outcome==WAIT_OBJECT_0:return True
        if outcome==WAIT_TIMEOUT:return False
        raise C.WinError(C.get_last_error())

    def poll(self):
        if self.returncode is None and self._signal_state():
            code=W.DWORD()
            _checked(self._k.GetExitCodeProcess(self._process,C.byref(code)))
            self.returncode=C.c_int32(code.value).value
        return self.returncode

    def wait(self,timeout=None):
        if self.poll() is not None:return self.returncode
        ms=INFINITE if timeout is None else max(0,min(INFINITE-1,int(timeout*1000)))
        outcome=self._k.WaitForSingleObject(self._process,ms)
        if outcome==WAIT_TIMEOUT:
            raise subprocess.TimeoutExpired(str(self.pid),timeout)
        if outcome!=WAIT_OBJECT_0:
            raise C.WinError(C.get_last_error())
        return self.poll()

    def terminate(self):
        if not self._signal_state():
            _checked(self._k.TerminateProcess(self._process,1))

    def _partial(self,text,encoding,errors):
        values=(bytes(self._chunks[0]),bytes(self._chunks[1]))
        return tuple(value.decode(encoding,errors) for value in values) if text else values

    def _start_readers(self):
        if self._readers:return
        def read(index,stream):
            try:
                while chunk:=stream.read(4096):
                    self._chunks[index].extend(chunk)
            except (OSError,ValueError) as error:
                self._reader_errors.append((index,str(error)))
        self._readers=[threading.Thread(target=read,args=(0,self.stdout),daemon=True),
                       threading.Thread(target=read,args=(1,self.stderr),daemon=True)]
        for thread in self._readers:thread.start()

    def communicate(self,timeout=None,*,text=False,encoding='utf-8',errors='replace'):
        deadline=None if timeout is None else time.monotonic()+timeout
        self._start_readers()
        try:
            self.wait(timeout)
        except subprocess.TimeoutExpired:
            output,stderr=self._partial(text,encoding,errors)
            raise subprocess.TimeoutExpired(str(self.pid),timeout,output=output,stderr=stderr)
        # A descendant may keep the pipe write handles open after this child exits.
        # Never wait indefinitely for EOF from either reader.
        remaining=1.0 if deadline is None else max(0,min(1.0,deadline-time.monotonic()))
        for thread in self._readers:
            started=time.monotonic()
            thread.join(remaining)
            remaining=max(0,remaining-(time.monotonic()-started))
        output,stderr=self._partial(text,encoding,errors)
        if any(thread.is_alive() for thread in self._readers):
            raise subprocess.TimeoutExpired(str(self.pid),timeout,output=output,stderr=stderr)
        if self._reader_errors:
            raise OSError('Pipe reader failed: '+str(self._reader_errors))
        return output,stderr

    def close(self):
        if self._closed:return
        try:
            if not self._signal_state():
                self.terminate()
                try:self.wait(2)
                except subprocess.TimeoutExpired:pass
            for stream in (self.stdout,self.stderr):
                try:self._k.CancelIoEx(msvcrt.get_osfhandle(stream.fileno()),None)
                except (OSError,ValueError):pass
            for thread in self._readers:thread.join(0.25)
            for index,stream in enumerate((self.stdout,self.stderr)):
                if index>=len(self._readers) or not self._readers[index].is_alive():
                    stream.close()
        finally:
            self._k.CloseHandle(self._thread)
            self._k.CloseHandle(self._process)
            self._closed=True


class IsolatedDesktop:
    def __init__(self):
        self.name='NikkeCatalogProbe_'+uuid.uuid4().hex
        self.handle=None
        self._children=[]

    def __enter__(self):
        if sys.platform!='win32':raise RuntimeError('Private desktops require Windows')
        self.k,self.u=_api()
        self.handle=_checked(self.u.CreateDesktopW(self.name,None,None,0,GENERIC_ALL,None))
        return self

    def popen(self,args,*,cwd=None):
        if not self.handle:raise RuntimeError('Enter the desktop context first')
        if not isinstance(args,(list,tuple)) or not args:raise TypeError('args must be a nonempty sequence')
        args=[os.fspath(arg) for arg in args]
        command=C.create_unicode_buffer(subprocess.list2cmdline(args))
        security=SECURITY_ATTRIBUTES(C.sizeof(SECURITY_ATTRIBUTES),None,True)
        out_read,out_write=W.HANDLE(),W.HANDLE()
        err_read,err_write=W.HANDLE(),W.HANDLE()
        nul=W.HANDLE()
        attr_buffer=None
        attr_ready=False
        info=PROCESS_INFORMATION()
        try:
            _checked(self.k.CreatePipe(C.byref(out_read),C.byref(out_write),C.byref(security),0))
            _checked(self.k.CreatePipe(C.byref(err_read),C.byref(err_write),C.byref(security),0))
            _checked(self.k.SetHandleInformation(out_read,1,0))
            _checked(self.k.SetHandleInformation(err_read,1,0))
            nul=self.k.CreateFileW('NUL',GENERIC_READ,3,C.byref(security),3,0x80,None)
            if nul==INVALID_HANDLE_VALUE:raise C.WinError(C.get_last_error())
            handles=(W.HANDLE*3)(nul,out_write,err_write)
            size=C.c_size_t()
            self.k.InitializeProcThreadAttributeList(None,1,0,C.byref(size))
            attr_buffer=C.create_string_buffer(size.value)
            _checked(self.k.InitializeProcThreadAttributeList(attr_buffer,1,0,C.byref(size)))
            attr_ready=True
            _checked(self.k.UpdateProcThreadAttribute(attr_buffer,0,PROC_THREAD_ATTRIBUTE_HANDLE_LIST,
                                                       C.cast(handles,W.LPVOID),C.sizeof(handles),None,None))
            startup=STARTUPINFOEXW()
            startup.StartupInfo.cb=C.sizeof(startup)
            startup.StartupInfo.lpDesktop=self.name
            startup.StartupInfo.dwFlags=STARTF_USESHOWWINDOW|STARTF_USESTDHANDLES
            startup.StartupInfo.wShowWindow=0
            startup.StartupInfo.hStdInput=nul
            startup.StartupInfo.hStdOutput=out_write
            startup.StartupInfo.hStdError=err_write
            startup.lpAttributeList=C.cast(attr_buffer,W.LPVOID)
            _checked(self.k.CreateProcessW(args[0],command,None,None,True,
                                           CREATE_NO_WINDOW|EXTENDED_STARTUPINFO_PRESENT,
                                           None,os.fspath(cwd) if cwd else None,
                                           C.cast(C.byref(startup),C.POINTER(STARTUPINFOW)),C.byref(info)))
            out_fd=msvcrt.open_osfhandle(out_read.value,os.O_RDONLY|os.O_BINARY)
            out_read=W.HANDLE()
            err_fd=msvcrt.open_osfhandle(err_read.value,os.O_RDONLY|os.O_BINARY)
            err_read=W.HANDLE()
            child=DesktopProcess(self.k,info,os.fdopen(out_fd,'rb',buffering=0),
                                 os.fdopen(err_fd,'rb',buffering=0))
            info=PROCESS_INFORMATION()
            self._children.append(child)
            return child
        finally:
            if attr_ready:self.k.DeleteProcThreadAttributeList(attr_buffer)
            for handle in (out_write,err_write,nul,out_read,err_read):
                value=handle.value if isinstance(handle,C.c_void_p) else handle
                if value not in (None,0,INVALID_HANDLE_VALUE):
                    self.k.CloseHandle(handle)
            if info.hThread:self.k.CloseHandle(info.hThread)
            if info.hProcess:
                self.k.TerminateProcess(info.hProcess,1)
                self.k.CloseHandle(info.hProcess)

    def run(self,args,*,cwd=None,timeout=None,text=False,encoding='utf-8',errors='replace',check=False):
        child=self.popen(args,cwd=cwd)
        try:
            try:
                stdout,stderr=child.communicate(timeout,text=text,encoding=encoding,errors=errors)
            except subprocess.TimeoutExpired:
                child.terminate()
                try:child.wait(3)
                except subprocess.TimeoutExpired:pass
                raise
            result=subprocess.CompletedProcess(args,child.returncode,stdout,stderr)
            if check:result.check_returncode()
            return result
        finally:
            child.close()

    def __exit__(self,*_):
        try:
            for child in self._children:child.close()
        finally:
            if self.handle:
                _checked(self.u.CloseDesktop(self.handle))
                self.handle=None


if __name__=='__main__':
    # Plain Python child only: no GameAssembly or other game DLL is loaded.
    code='''import ctypes,json
from ctypes import wintypes
u=ctypes.WinDLL('user32',use_last_error=True)
k=ctypes.WinDLL('kernel32',use_last_error=True)
u.GetThreadDesktop.argtypes=[wintypes.DWORD];u.GetThreadDesktop.restype=wintypes.HANDLE
u.GetUserObjectInformationW.argtypes=[wintypes.HANDLE,ctypes.c_int,ctypes.c_void_p,wintypes.DWORD,ctypes.POINTER(wintypes.DWORD)]
b=ctypes.create_unicode_buffer(256);n=wintypes.DWORD()
assert u.GetUserObjectInformationW(u.GetThreadDesktop(k.GetCurrentThreadId()),2,b,ctypes.sizeof(b),ctypes.byref(n))
print(json.dumps({'desktop':b.value}))
'''
    with IsolatedDesktop() as desktop:
        result=desktop.run([sys.executable,'-c',code],text=True,check=True,timeout=10)
        observed=json.loads(result.stdout)['desktop']
        assert observed==desktop.name,(observed,desktop.name)
        print('PASS: child assigned private desktop; no desktop activated; no game DLL loaded.')
