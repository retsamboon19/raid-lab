"""Derive a research-only deny-all guard from the reviewed offline adapter."""
import hashlib
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
source = (ROOT / 'isolated/OfflineNetwork.cpp').read_text()


def replace(old, new):
    global source
    if source.count(old) != 1:
        raise RuntimeError('Reviewed source changed: ' + old[:80])
    source = source.replace(old, new)


replace('    projectRoot=root;', '''    projectRoot=root;
    wchar_t desktop[256]={};DWORD needed=0;
    if(!GetUserObjectInformationW(GetThreadDesktop(GetCurrentThreadId()),UOI_NAME,desktop,sizeof(desktop),&needed)
        || wcsncmp(desktop,L"NikkeCatalogProbe_",18)) return FALSE;
    size_t rootSlash=projectRoot.find_last_of(L"\\\\/");
    std::wstring registry=L"Software\\\\RaidLabNativeSandbox\\\\"+projectRoot.substr(rootSlash+1);
    HKEY scratch=nullptr;
    if(RegCreateKeyExW(HKEY_CURRENT_USER,registry.c_str(),0,nullptr,0,KEY_ALL_ACCESS,nullptr,&scratch,nullptr)!=ERROR_SUCCESS)return FALSE;
    if(RegOverridePredefKey(HKEY_CURRENT_USER,scratch)!=ERROR_SUCCESS)return FALSE;
''')
replace('    if(local(name)) return realW(name,service,hints,result);',
        '    if(result)*result=nullptr; return WSAHOST_NOT_FOUND; // research: deny every DNS request')
replace('    if(local(name ? wide : nullptr)) return realA(name,service,hints,result);',
        '    if(result)*result=nullptr; return WSAHOST_NOT_FOUND; // research: deny every DNS request')
replace('    if(!loopback(address,length))', '    if(true) // research: also deny production loopback\n    ')
replace('    if(!loopback(a,len))', '    if(true) // research: also deny production loopback\n    ')
extra = '''
static SOCKET WSAAPI denySocket(int,int,int) { WSASetLastError(WSAEACCES);return INVALID_SOCKET; }
static SOCKET WSAAPI denyWSASocketA(int,int,int,LPWSAPROTOCOL_INFOA,GROUP,DWORD) { WSASetLastError(WSAEACCES);return INVALID_SOCKET; }
static SOCKET WSAAPI denyWSASocketW(int,int,int,LPWSAPROTOCOL_INFOW,GROUP,DWORD) { WSASetLastError(WSAEACCES);return INVALID_SOCKET; }
static int WSAAPI denySendTo(SOCKET,const char*,int,int,const sockaddr*,int) { WSASetLastError(WSAEACCES);return SOCKET_ERROR; }
static int WSAAPI denyWSASendTo(SOCKET,LPWSABUF,DWORD,LPDWORD,DWORD,const sockaddr*,int,LPWSAOVERLAPPED,LPWSAOVERLAPPED_COMPLETION_ROUTINE) { WSASetLastError(WSAEACCES);return SOCKET_ERROR; }
'''
replace('extern "C" __declspec(dllexport) BOOL InitializeOfflineNetwork()', extra+'\nextern "C" __declspec(dllexport) BOOL InitializeOfflineNetwork()')
replace('    if(MH_EnableHook(MH_ALL_HOOKS)!=MH_OK)return FALSE;', '''    if(MH_CreateHookApi(L"ws2_32.dll","sendto",(LPVOID)denySendTo,nullptr)!=MH_OK ||
       MH_CreateHookApi(L"ws2_32.dll","WSASendTo",(LPVOID)denyWSASendTo,nullptr)!=MH_OK ||
       MH_CreateHookApi(L"ws2_32.dll","socket",(LPVOID)denySocket,nullptr)!=MH_OK ||
       MH_CreateHookApi(L"ws2_32.dll","WSASocketA",(LPVOID)denyWSASocketA,nullptr)!=MH_OK ||
       MH_CreateHookApi(L"ws2_32.dll","WSASocketW",(LPVOID)denyWSASocketW,nullptr)!=MH_OK)return FALSE;
    if(MH_EnableHook(MH_ALL_HOOKS)!=MH_OK)return FALSE;''')
(HERE / 'OfflineNetwork.cpp').write_text(source)
print('Generated research-only guard; source SHA256 '+hashlib.sha256(source.encode()).hexdigest())
