#define WIN32_LEAN_AND_MEAN
#include <winsock2.h>
#include <ws2tcpip.h>
#include <windows.h>
#include <stdio.h>
#include <shlobj.h>
#include <wincrypt.h>
#include <string>
#include "MinHook.h"

static decltype(&getaddrinfo) realA;
static decltype(&GetAddrInfoW) realW;
static decltype(&connect) realConnect;
static decltype(&WSAConnect) realWSAConnect;
static decltype(&OpenFileMappingW) realOpenMapW;
static decltype(&OpenFileMappingA) realOpenMapA;
static HANDLE WINAPI openMapW(DWORD access,BOOL inherit,LPCWSTR name) {
    if(name && !wcscmp(name,L"Sail.SharedMemory.29080"))name=L"Sail.SharedMemory.NIKKEOfflineProject";
    return realOpenMapW(access,inherit,name);
}
static HANDLE WINAPI openMapA(DWORD access,BOOL inherit,LPCSTR name) {
    if(name && !strcmp(name,"Sail.SharedMemory.29080"))name="Sail.SharedMemory.NIKKEOfflineProject";
    return realOpenMapA(access,inherit,name);
}
static wchar_t logPath[MAX_PATH];
static SRWLOCK logLock = SRWLOCK_INIT;
static void logName(const wchar_t* action,const wchar_t* name);
static std::wstring projectRoot;
static std::string offlineVariants;
static decltype(&RegQueryValueExW) realQueryValue;
static LSTATUS WINAPI queryValue(HKEY key,LPCWSTR name,LPDWORD reserved,LPDWORD type,LPBYTE data,LPDWORD size) {
    if (name && !wcscmp(name,L"variantsJson_h2327514681") && !offlineVariants.empty()) {
        if (!size) return ERROR_INVALID_PARAMETER;
        DWORD required=(DWORD)offlineVariants.size()+1;
        DWORD available=*size; *size=required;
        if(type)*type=REG_BINARY;
        if(!data)return ERROR_SUCCESS;
        if(available<required)return ERROR_MORE_DATA;
        memcpy(data,offlineVariants.c_str(),required);return ERROR_SUCCESS;
    }
    return realQueryValue(key,name,reserved,type,data,size);
}
static PCCERT_CONTEXT projectCert=nullptr;
static decltype(&SHGetKnownFolderPath) realKnownFolder;
static decltype(&SHGetFolderPathW) realFolderW;
static decltype(&CertOpenStore) realCertStore;
static const wchar_t* folderSuffix(REFKNOWNFOLDERID id) {
    if(IsEqualGUID(id,FOLDERID_LocalAppDataLow))return L"\\profile\\AppData\\LocalLow";
    if(IsEqualGUID(id,FOLDERID_LocalAppData))return L"\\profile\\AppData\\Local";
    if(IsEqualGUID(id,FOLDERID_RoamingAppData))return L"\\profile\\AppData\\Roaming";
    if(IsEqualGUID(id,FOLDERID_Profile))return L"\\profile";
    return nullptr;
}
static HRESULT WINAPI knownFolder(REFKNOWNFOLDERID id,DWORD flags,HANDLE token,PWSTR* out) {
    auto suffix=folderSuffix(id);if(!suffix)return realKnownFolder(id,flags,token,out);
    std::wstring path=projectRoot+suffix;
    *out=(PWSTR)CoTaskMemAlloc((path.size()+1)*sizeof(wchar_t));if(!*out)return E_OUTOFMEMORY;
    wcscpy_s(*out,path.size()+1,path.c_str());return S_OK;
}
static HRESULT WINAPI folderW(HWND window,int id,HANDLE token,DWORD flags,LPWSTR out) {
    const wchar_t* suffix=nullptr;
    switch(id & 0xff){case CSIDL_LOCAL_APPDATA:suffix=L"\\profile\\AppData\\Local";break;case CSIDL_APPDATA:suffix=L"\\profile\\AppData\\Roaming";break;case CSIDL_PROFILE:suffix=L"\\profile";break;}
    if(!suffix)return realFolderW(window,id,token,flags,out);
    return wcscpy_s(out,MAX_PATH,(projectRoot+suffix).c_str())==0 ? S_OK : E_FAIL;
}
static HCERTSTORE WINAPI certStore(LPCSTR provider,DWORD encoding,HCRYPTPROV_LEGACY crypto,DWORD flags,const void* parameter) {
    HCERTSTORE original=realCertStore(provider,encoding,crypto,flags,parameter);
    bool root=false;
    if(parameter && (provider==CERT_STORE_PROV_SYSTEM_W || provider==CERT_STORE_PROV_SYSTEM_REGISTRY_W))root=!_wcsicmp((LPCWSTR)parameter,L"ROOT");
    if(parameter && (provider==CERT_STORE_PROV_SYSTEM_A || provider==CERT_STORE_PROV_SYSTEM_REGISTRY_A))root=!_stricmp((LPCSTR)parameter,"ROOT");
    if(!root || !original || !projectCert)return original;
    HCERTSTORE memory=realCertStore(CERT_STORE_PROV_MEMORY,0,0,0,nullptr);if(!memory)return original;
    PCCERT_CONTEXT item=nullptr;
    while((item=CertEnumCertificatesInStore(original,item)))CertAddCertificateContextToStore(memory,item,CERT_STORE_ADD_ALWAYS,nullptr);
    CertAddCertificateContextToStore(memory,projectCert,CERT_STORE_ADD_ALWAYS,nullptr);
    CertCloseStore(original,0);logName(L"TRUST",L"project certificate added to in-memory root store");return memory;
}
static void logName(const wchar_t* action, const wchar_t* name) {
    AcquireSRWLockExclusive(&logLock);
    FILE* f = nullptr;
    _wfopen_s(&f, logPath, L"a, ccs=UTF-8");
    if (f) { fwprintf(f,L"%ls %ls\n",action,name ? name : L"(null)"); fclose(f); }
    ReleaseSRWLockExclusive(&logLock);
}
static bool ends(const wchar_t* name,const wchar_t* suffix) {
    size_t n=wcslen(name),s=wcslen(suffix);
    return n>=s && _wcsicmp(name+n-s,suffix)==0;
}
static bool local(const wchar_t* name) {
    return !name || !_wcsicmp(name,L"localhost") || !wcscmp(name,L"127.0.0.1") || !wcscmp(name,L"::1");
}
static bool gameDomain(const wchar_t* name) {
    return name && (ends(name,L".nikke-kr.com") || ends(name,L".intlgame.com") || !_wcsicmp(name,L"na-community.playerinfinite.com") || !_wcsicmp(name,L"www.jupiterlauncher.com"));
}
static int WSAAPI lookupW(PCWSTR name,PCWSTR service,const ADDRINFOW* hints,PADDRINFOW* result) {
    if(result)*result=nullptr; return WSAHOST_NOT_FOUND; // research: deny every DNS request
    if(!gameDomain(name)) { logName(L"BLOCK DNS",name); if(result)*result=nullptr; return WSAHOST_NOT_FOUND; }
    logName(L"LOCAL DNS",name);
    return realW(L"127.0.0.1",service,hints,result);
}
static int WSAAPI lookupA(PCSTR name,PCSTR service,const ADDRINFOA* hints,PADDRINFOA* result) {
    wchar_t wide[1024]={};
    if(name && !MultiByteToWideChar(CP_UTF8,0,name,-1,wide,1024)) return WSAHOST_NOT_FOUND;
    if(result)*result=nullptr; return WSAHOST_NOT_FOUND; // research: deny every DNS request
    if(!gameDomain(wide)) { logName(L"BLOCK DNS",wide); if(result)*result=nullptr; return WSAHOST_NOT_FOUND; }
    logName(L"LOCAL DNS",wide);
    return realA("127.0.0.1",service,hints,result);
}
static bool loopback(const sockaddr* address,int length) {
    if(!address) return false;
    if(address->sa_family==AF_INET && length>=sizeof(sockaddr_in)) return (ntohl(((const sockaddr_in*)address)->sin_addr.s_addr)>>24)==127;
    if(address->sa_family==AF_INET6 && length>=sizeof(sockaddr_in6)) return IN6_IS_ADDR_LOOPBACK(&((const sockaddr_in6*)address)->sin6_addr);
    return false;
}
static int WSAAPI connectLocal(SOCKET s,const sockaddr* address,int length) {
    if(true) // research: also deny production loopback
     { logName(L"BLOCK CONNECT",L"non-loopback"); WSASetLastError(WSAEACCES); return SOCKET_ERROR; }
    return realConnect(s,address,length);
}
static int WSAAPI wsaConnectLocal(SOCKET s,const sockaddr* a,int len,LPWSABUF caller,LPWSABUF callee,LPQOS sq,LPQOS gq) {
    if(true) // research: also deny production loopback
     { logName(L"BLOCK WSACONNECT",L"non-loopback"); WSASetLastError(WSAEACCES); return SOCKET_ERROR; }
    return realWSAConnect(s,a,len,caller,callee,sq,gq);
}

static SOCKET WSAAPI denySocket(int,int,int) { WSASetLastError(WSAEACCES);return INVALID_SOCKET; }
static SOCKET WSAAPI denyWSASocketA(int,int,int,LPWSAPROTOCOL_INFOA,GROUP,DWORD) { WSASetLastError(WSAEACCES);return INVALID_SOCKET; }
static SOCKET WSAAPI denyWSASocketW(int,int,int,LPWSAPROTOCOL_INFOW,GROUP,DWORD) { WSASetLastError(WSAEACCES);return INVALID_SOCKET; }
static int WSAAPI denySendTo(SOCKET,const char*,int,int,const sockaddr*,int) { WSASetLastError(WSAEACCES);return SOCKET_ERROR; }
static int WSAAPI denyWSASendTo(SOCKET,LPWSABUF,DWORD,LPDWORD,DWORD,const sockaddr*,int,LPWSAOVERLAPPED,LPWSAOVERLAPPED_COMPLETION_ROUTINE) { WSASetLastError(WSAEACCES);return SOCKET_ERROR; }

extern "C" __declspec(dllexport) BOOL InitializeOfflineNetwork() {
    wchar_t root[MAX_PATH]={};if(!GetEnvironmentVariableW(L"NIKKE_OFFLINE_ROOT",root,MAX_PATH))return FALSE;
    projectRoot=root;
    wchar_t desktop[256]={};DWORD needed=0;
    if(!GetUserObjectInformationW(GetThreadDesktop(GetCurrentThreadId()),UOI_NAME,desktop,sizeof(desktop),&needed)
        || wcsncmp(desktop,L"NikkeCatalogProbe_",18)) return FALSE;
    size_t rootSlash=projectRoot.find_last_of(L"\\/");
    std::wstring registry=L"Software\\RaidLabNativeSandbox\\"+projectRoot.substr(rootSlash+1);
    HKEY scratch=nullptr;
    if(RegCreateKeyExW(HKEY_CURRENT_USER,registry.c_str(),0,nullptr,0,KEY_ALL_ACCESS,nullptr,&scratch,nullptr)!=ERROR_SUCCESS)return FALSE;
    if(RegOverridePredefKey(HKEY_CURRENT_USER,scratch)!=ERROR_SUCCESS)return FALSE;

    // Supply the offline world's startup preferences only inside this process.
    // The user's normal game registry is never rewritten by this override.
    FILE* variants=nullptr;
    _wfopen_s(&variants,(projectRoot+L"\\profile\\offline-variants.json").c_str(),L"rb");
    if(variants) {
        char buffer[4096]; size_t n;
        while((n=fread(buffer,1,sizeof(buffer),variants)))offlineVariants.append(buffer,n);
        fclose(variants);
    }
    // MinHook resolves modules already loaded; the game's early native entry point
    // does not load advapi32, unlike the Python host used by the original test.
    if(!LoadLibraryW(L"advapi32.dll") || !LoadLibraryW(L"shell32.dll") || !LoadLibraryW(L"crypt32.dll"))return FALSE;
    std::wstring certificatePath=projectRoot+L"\\EpinelPS-runtime\\myCA.pem";
    FILE* pem=nullptr;_wfopen_s(&pem,certificatePath.c_str(),L"rb");if(!pem)return FALSE;
    char pemData[16384]={};DWORD pemSize=(DWORD)fread(pemData,1,sizeof(pemData),pem);fclose(pem);
    BYTE certificate[16384];DWORD certificateSize=sizeof(certificate);
    if(!CryptStringToBinaryA(pemData,pemSize,CRYPT_STRING_BASE64HEADER,certificate,&certificateSize,nullptr,nullptr))return FALSE;
    projectCert=CertCreateCertificateContext(X509_ASN_ENCODING,certificate,certificateSize);if(!projectCert)return FALSE;
    HMODULE self=nullptr;
    GetModuleHandleExW(GET_MODULE_HANDLE_EX_FLAG_FROM_ADDRESS|GET_MODULE_HANDLE_EX_FLAG_UNCHANGED_REFCOUNT,(LPCWSTR)&InitializeOfflineNetwork,&self);
    GetModuleFileNameW(self,logPath,MAX_PATH);
    wchar_t* slash=wcsrchr(logPath,L'\\'); if(!slash)return FALSE;
    wcscpy_s(slash+1,MAX_PATH-(slash+1-logPath),L"offline-network.log");
    if(MH_Initialize()!=MH_OK)return FALSE;
    if(MH_CreateHookApi(L"advapi32.dll","RegQueryValueExW",(LPVOID)queryValue,(LPVOID*)&realQueryValue)!=MH_OK)return FALSE;
    if(MH_CreateHookApi(L"ws2_32.dll","getaddrinfo",(LPVOID)lookupA,(LPVOID*)&realA)!=MH_OK ||
       MH_CreateHookApi(L"ws2_32.dll","GetAddrInfoW",(LPVOID)lookupW,(LPVOID*)&realW)!=MH_OK ||
       MH_CreateHookApi(L"ws2_32.dll","connect",(LPVOID)connectLocal,(LPVOID*)&realConnect)!=MH_OK ||
       MH_CreateHookApi(L"ws2_32.dll","WSAConnect",(LPVOID)wsaConnectLocal,(LPVOID*)&realWSAConnect)!=MH_OK ||
       MH_CreateHookApi(L"kernel32.dll","OpenFileMappingW",(LPVOID)openMapW,(LPVOID*)&realOpenMapW)!=MH_OK ||
       MH_CreateHookApi(L"kernel32.dll","OpenFileMappingA",(LPVOID)openMapA,(LPVOID*)&realOpenMapA)!=MH_OK ||
       MH_CreateHookApi(L"shell32.dll","SHGetKnownFolderPath",(LPVOID)knownFolder,(LPVOID*)&realKnownFolder)!=MH_OK ||
       MH_CreateHookApi(L"shell32.dll","SHGetFolderPathW",(LPVOID)folderW,(LPVOID*)&realFolderW)!=MH_OK ||
       MH_CreateHookApi(L"crypt32.dll","CertOpenStore",(LPVOID)certStore,(LPVOID*)&realCertStore)!=MH_OK) return FALSE;
    if(MH_CreateHookApi(L"ws2_32.dll","sendto",(LPVOID)denySendTo,nullptr)!=MH_OK ||
       MH_CreateHookApi(L"ws2_32.dll","WSASendTo",(LPVOID)denyWSASendTo,nullptr)!=MH_OK ||
       MH_CreateHookApi(L"ws2_32.dll","socket",(LPVOID)denySocket,nullptr)!=MH_OK ||
       MH_CreateHookApi(L"ws2_32.dll","WSASocketA",(LPVOID)denyWSASocketA,nullptr)!=MH_OK ||
       MH_CreateHookApi(L"ws2_32.dll","WSASocketW",(LPVOID)denyWSASocketW,nullptr)!=MH_OK)return FALSE;
    if(MH_EnableHook(MH_ALL_HOOKS)!=MH_OK)return FALSE;
    logName(L"READY",L"process-local routing"); return TRUE;
}
