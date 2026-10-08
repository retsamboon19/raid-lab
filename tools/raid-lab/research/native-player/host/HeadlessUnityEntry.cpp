// Private mechanics host: real Unity object/services, null graphics device.
// No production launcher, account, backend, or battle scene is started here.
#define WIN32_LEAN_AND_MEAN
#include <windows.h>
#include <string>
#include <stdlib.h>
#include <stdio.h>

// Observe first-chance exceptions without intercepting the runtime's throw or
// unwind functions. Enabled only after the private-desktop guard, for the thread
// explicitly armed by the mechanics diagnostic. Always continue native handling.
static volatile LONG observeExceptions = 0, exceptionRecords = 0, inException = 0;
static DWORD observedThread = 0;
static ULONG_PTR gameBegin = 0, gameEnd = 0;
static PVOID exceptionObserver = nullptr;
static bool privateHost = false;

static void appendException(const char* line) {
    HANDLE file = CreateFileW(L"headless-native-exceptions.log", FILE_APPEND_DATA,
        FILE_SHARE_READ | FILE_SHARE_WRITE, nullptr, OPEN_ALWAYS, FILE_ATTRIBUTE_NORMAL, nullptr);
    if (file != INVALID_HANDLE_VALUE) {
        DWORD written = 0;
        WriteFile(file, line, (DWORD)strlen(line), &written, nullptr);
        FlushFileBuffers(file);
        CloseHandle(file);
    }
}

static void recordExceptionFrames(CONTEXT context) {
    __try {
        for (unsigned index = 0; index < 32 && context.Rip; ++index) {
            if (context.Rip >= gameBegin && context.Rip < gameEnd) {
                char line[96] = {};
                sprintf_s(line, "native_frame index=%u game_rva=0x%llx\n", index,
                    (unsigned long long)(context.Rip - gameBegin));
                appendException(line);
            }
            DWORD64 imageBase = 0;
            PRUNTIME_FUNCTION entry = RtlLookupFunctionEntry(context.Rip, &imageBase, nullptr);
            if (entry) {
                PVOID handlerData = nullptr; DWORD64 frame = 0;
                RtlVirtualUnwind(UNW_FLAG_NHANDLER, imageBase, context.Rip, entry,
                    &context, &handlerData, &frame, nullptr);
            } else {
                DWORD64 next = 0; SIZE_T bytes = 0;
                if (!ReadProcessMemory(GetCurrentProcess(), (LPCVOID)context.Rsp,
                        &next, sizeof(next), &bytes) || bytes != sizeof(next)) break;
                context.Rip = next; context.Rsp += sizeof(next);
            }
        }
    } __except (EXCEPTION_EXECUTE_HANDLER) {
        appendException("native_unwind_unavailable\n");
    }
}

static LONG CALLBACK observeNativeException(EXCEPTION_POINTERS* info) {
    const DWORD code = info->ExceptionRecord->ExceptionCode;
    if (!observeExceptions || GetCurrentThreadId() != observedThread ||
            (code != 0xE06D7363 && code != 0xC0000005 && code != 0xC0000409) ||
            InterlockedCompareExchange(&inException, 1, 0)) return EXCEPTION_CONTINUE_SEARCH;
    const LONG ordinal = InterlockedIncrement(&exceptionRecords);
    if (ordinal <= 16) {
        char line[256] = {};
        sprintf_s(line, "exception ordinal=%ld code=0x%08lx thread=%lu parameters=%lu\n",
            ordinal, code, observedThread, info->ExceptionRecord->NumberParameters);
        appendException(line); // Persist the marker even if native unwind is unavailable.
        if (code == 0xC0000005 && info->ExceptionRecord->NumberParameters >= 2) {
            sprintf_s(line, "access_violation operation=%llu address=0x%llx\n",
                (unsigned long long)info->ExceptionRecord->ExceptionInformation[0],
                (unsigned long long)info->ExceptionRecord->ExceptionInformation[1]);
            appendException(line);
        }
        recordExceptionFrames(*info->ContextRecord);
    }
    InterlockedExchange(&inException, 0);
    return EXCEPTION_CONTINUE_SEARCH;
}

extern "C" __declspec(dllexport) BOOL SetMechanicsExceptionObservation(int enabled) {
    if (!privateHost || !exceptionObserver) return FALSE;
    if (enabled) {
        HMODULE game = GetModuleHandleW(L"GameAssembly.dll");
        if (!game) return FALSE;
        const auto dos = (IMAGE_DOS_HEADER*)game;
        const auto pe = (IMAGE_NT_HEADERS*)((BYTE*)game + dos->e_lfanew);
        gameBegin = (ULONG_PTR)game; gameEnd = gameBegin + pe->OptionalHeader.SizeOfImage;
        observedThread = GetCurrentThreadId();
        InterlockedExchange(&exceptionRecords, 0);
        // Frida installs its own native-call exception handler after bootstrap.
        // Move only our passive observer ahead of it so an AV is logged before
        // Frida converts it to a JS error. Continue native handling unchanged.
        RemoveVectoredExceptionHandler(exceptionObserver);
        exceptionObserver = AddVectoredExceptionHandler(1, observeNativeException);
        if (!exceptionObserver) return FALSE;
    }
    InterlockedExchange(&observeExceptions, enabled ? 1 : 0);
    return TRUE;
}

static void trace(const char* line) {
    HANDLE file = CreateFileW(L"headless-bootstrap.log", FILE_APPEND_DATA,
        FILE_SHARE_READ | FILE_SHARE_WRITE, nullptr, OPEN_ALWAYS, FILE_ATTRIBUTE_NORMAL, nullptr);
    if (file != INVALID_HANDLE_VALUE) {
        DWORD written = 0;
        WriteFile(file, line, (DWORD)strlen(line), &written, nullptr);
        CloseHandle(file);
    }
}

static DWORD WINAPI loadDiagnostic(LPVOID) {
    trace("gadget_load_enter\n");
    HMODULE gadget = LoadLibraryW(L"frida-gadget.dll");
    trace(gadget ? "gadget_load_returned\n" : "gadget_load_failed\n");
    return gadget ? 0 : 45;
}

extern "C" __declspec(dllexport) int DoInit(HINSTANCE instance, HINSTANCE previous,
                                            LPSTR command, int show) {
    wchar_t desktop[256] = {}; DWORD needed = 0;
    if (!GetUserObjectInformationW(GetThreadDesktop(GetCurrentThreadId()), UOI_NAME,
            desktop, sizeof(desktop), &needed) ||
            wcsncmp(desktop, L"NikkeCatalogProbe_", 18)) return 41;
    wchar_t root[1024] = {};
    if (!GetEnvironmentVariableW(L"NIKKE_OFFLINE_ROOT", root, 1024)) return 42;
    privateHost = true;
    exceptionObserver = AddVectoredExceptionHandler(1, observeNativeException);
    if (!exceptionObserver) return 46;
    HMODULE network = LoadLibraryW(L"OfflineNetwork.dll");
    auto initialize = network ? (BOOL(*)())GetProcAddress(network, "InitializeOfflineNetwork") : nullptr;
    if (!initialize || !initialize()) return 43;
    HMODULE unity = LoadLibraryW(L"UnityPlayer.dll");
    // Exact UnityPlayer export scans the third argument as UTF-16 words.
    auto main = unity ? (int(*)(HINSTANCE,HINSTANCE,LPCWSTR,int))GetProcAddress(unity, "UnityMain") : nullptr;
    if (!main) return 44;
    // Gadget script initialization can wait for IL2CPP. Its LoadLibrary must
    // not block the same thread that must enter UnityMain to initialize it.
    // Retain the loaded diagnostic DLL until the isolated process exits.
    HANDLE diagnostic = CreateThread(nullptr, 0, loadDiagnostic, nullptr, 0, nullptr);
    if (!diagnostic) return 45;
    CloseHandle(diagnostic);
    // Read this private process's actual Unicode arguments, preserving the
    // host-controlled quoted log path regardless of the executable stub ABI.
    const wchar_t* tail = GetCommandLineW();
    if (*tail == L'"') {
        ++tail;
        while (*tail && *tail != L'"') ++tail;
        if (*tail) ++tail;
    } else {
        while (*tail && *tail != L' ' && *tail != L'\t') ++tail;
    }
    std::wstring args(tail);
    args += L" -batchmode -nographics";
    trace("unity_main_command_utf16\n");
    trace("unity_main_enter\n");
    int result = main(instance, previous, &args[0], SW_HIDE);
    trace("unity_main_returned\n");
    exit(result);
}
