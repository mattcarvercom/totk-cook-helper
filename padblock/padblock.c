/* SDL3.dll wrapper for totk.exe: holds the controller still while the Cook Helper window is in front.

   The game draws its own window and uses SDL only for the controller, so SDL never sees the game lose focus and keeps
   passing the pad through. This DLL takes the place of SDL3.dll; the real one is renamed SDL3_orig.dll. Every SDL
   function is forwarded unchanged (padblock.def, written by padblock.py), except the three the game polls the pad with:
   while the foreground window is titled "TotK Cook Helper" they report no buttons, centred sticks and no gyro
   motion. The game then sees a release, as when a player lets go of the pad.

   No C runtime: the DLL only needs kernel32 and user32. */
#include <windows.h>

typedef struct SDL_Gamepad SDL_Gamepad;
typedef _Bool (*get_button_fn)(SDL_Gamepad *, int);
typedef short (*get_axis_fn)(SDL_Gamepad *, int);
typedef _Bool (*get_sensor_fn)(SDL_Gamepad *, int, float *, int);

static get_button_fn real_button;
static get_axis_fn real_axis;
static get_sensor_fn real_sensor;
static ULONGLONG checked_at;
static volatile LONG blocked;

static const WCHAR HELPER_TITLE[] = L"TotK Cook Helper";

static HINSTANCE self;
static volatile LONG loaded;

/* SDL3_orig.dll sits next to this DLL. Loaded on first use, outside the loader lock DllMain runs under. */
static void load_real(void) {
    if (loaded) return;
    WCHAR path[MAX_PATH + 20];
    DWORD n = GetModuleFileNameW(self, path, MAX_PATH);
    while (n && path[n - 1] != L'\\') n--;
    lstrcpyW(path + n, L"SDL3_orig.dll");
    HMODULE h = LoadLibraryW(path);
    if (h) {
        real_sensor = (get_sensor_fn)GetProcAddress(h, "SDL_GetGamepadSensorData");
        real_axis = (get_axis_fn)GetProcAddress(h, "SDL_GetGamepadAxis");
        real_button = (get_button_fn)GetProcAddress(h, "SDL_GetGamepadButton");
    }
    loaded = 1;
}

/* The game asks for each button and axis every frame, so the window check runs at most every 30 ms. */
static int helper_in_front(void) {
    ULONGLONG now = GetTickCount64();
    if (now - checked_at >= 30) {
        WCHAR title[40];
        HWND fg = GetForegroundWindow();
        int n = fg ? GetWindowTextW(fg, title, 40) : 0;
        blocked = n == (int)(sizeof(HELPER_TITLE) / sizeof(WCHAR)) - 1 && lstrcmpW(title, HELPER_TITLE) == 0;
        checked_at = now;
    }
    return blocked;
}

__declspec(dllexport) _Bool SDL_GetGamepadButton(SDL_Gamepad *pad, int button) {
    load_real();
    if (!real_button) return 0;
    _Bool down = real_button(pad, button);
    return helper_in_front() ? 0 : down;
}

__declspec(dllexport) short SDL_GetGamepadAxis(SDL_Gamepad *pad, int axis) {
    load_real();
    if (!real_axis) return 0;
    short v = real_axis(pad, axis);
    return helper_in_front() ? 0 : v;
}

/* Gyro types are SDL_SENSOR_GYRO (2), GYRO_L (4) and GYRO_R (6). Accelerometers still report gravity, which is what a
   pad at rest reads anyway. */
__declspec(dllexport) _Bool SDL_GetGamepadSensorData(SDL_Gamepad *pad, int type, float *data, int count) {
    load_real();
    if (!real_sensor) return 0;
    _Bool ok = real_sensor(pad, type, data, count);
    if (ok && data && (type == 2 || type == 4 || type == 6) && helper_in_front())
        for (int i = 0; i < count; i++) ((volatile float *)data)[i] = 0.0f;  /* volatile: no memset, no CRT */
    return ok;
}

/* Marks this file as the wrapper, so the installer can tell it from a real SDL3.dll a port update put back. */
__declspec(dllexport) int CookHelperPadBlock(void) { return 1; }

BOOL WINAPI DllMain(HINSTANCE inst, DWORD reason, LPVOID reserved) {
    (void)reserved;
    if (reason == DLL_PROCESS_ATTACH) {
        DisableThreadLibraryCalls(inst);
        self = inst;
    }
    return TRUE;
}
