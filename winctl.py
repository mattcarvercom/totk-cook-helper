"""Win32 window, monitor and hotkey helpers for the cook helper (ctypes only)."""
import ctypes
import os
import threading
from ctypes import wintypes as W

u32 = ctypes.WinDLL('user32', use_last_error=True)
k32 = ctypes.WinDLL('kernel32', use_last_error=True)
dwm = ctypes.WinDLL('dwmapi')

HWND = W.HWND
u32.SetWindowPos.argtypes = [HWND, HWND, ctypes.c_int, ctypes.c_int, ctypes.c_int, ctypes.c_int, W.UINT]
u32.ShowWindow.argtypes = [HWND, ctypes.c_int]
u32.IsIconic.argtypes = [HWND]
u32.IsWindowVisible.argtypes = [HWND]
u32.GetWindowRect.argtypes = [HWND, ctypes.POINTER(W.RECT)]
u32.GetWindowTextW.argtypes = [HWND, W.LPWSTR, ctypes.c_int]
u32.GetWindowThreadProcessId.argtypes = [HWND, ctypes.POINTER(W.DWORD)]
u32.GetWindowThreadProcessId.restype = W.DWORD
u32.SetForegroundWindow.argtypes = [HWND]
u32.BringWindowToTop.argtypes = [HWND]
u32.GetForegroundWindow.restype = HWND
u32.SendMessageW.argtypes = [HWND, W.UINT, W.WPARAM, W.LPARAM]
u32.MonitorFromWindow.argtypes = [HWND, W.DWORD]
u32.MonitorFromWindow.restype = W.HMONITOR
u32.RegisterHotKey.argtypes = [HWND, ctypes.c_int, W.UINT, W.UINT]
u32.UnregisterHotKey.argtypes = [HWND, ctypes.c_int]
u32.PostThreadMessageW.argtypes = [W.DWORD, W.UINT, W.WPARAM, W.LPARAM]
u32.GetMessageW.argtypes = [ctypes.POINTER(W.MSG), HWND, W.UINT, W.UINT]
u32.PeekMessageW.argtypes = [ctypes.POINTER(W.MSG), HWND, W.UINT, W.UINT, W.UINT]
u32.AttachThreadInput.argtypes = [W.DWORD, W.DWORD, W.BOOL]
u32.GetWindow.argtypes = [HWND, W.UINT]
u32.GetWindow.restype = HWND
dwm.DwmSetWindowAttribute.argtypes = [HWND, W.DWORD, ctypes.c_void_p, W.DWORD]

HWND_TOPMOST, HWND_NOTOPMOST, HWND_TOP = HWND(-1), HWND(-2), HWND(0)
SWP_NOSIZE, SWP_NOMOVE, SWP_NOZORDER, SWP_NOACTIVATE = 0x1, 0x2, 0x4, 0x10
SW_HIDE, SW_MINIMIZE, SW_SHOWNOACTIVATE, SW_SHOWMINNOACTIVE, SW_RESTORE = 0, 6, 4, 7, 9
WM_NCLBUTTONDOWN, WM_HOTKEY, WM_APP = 0xA1, 0x312, 0x8000
GW_HWNDPREV = 3
HTCAPTION, HTLEFT, HTRIGHT, HTTOP, HTBOTTOM = 2, 10, 11, 12, 15
HT = {'move': HTCAPTION, 'left': HTLEFT, 'right': HTRIGHT, 'top': HTTOP, 'bottom': HTBOTTOM,
      'topleft': 13, 'topright': 14, 'bottomleft': 16, 'bottomright': 17}

WNDENUMPROC = ctypes.WINFUNCTYPE(W.BOOL, HWND, W.LPARAM)
MONITORENUMPROC = ctypes.WINFUNCTYPE(W.BOOL, W.HMONITOR, W.HDC, ctypes.POINTER(W.RECT), W.LPARAM)


class MONITORINFOEX(ctypes.Structure):
    _fields_ = [('cbSize', W.DWORD), ('rcMonitor', W.RECT), ('rcWork', W.RECT), ('dwFlags', W.DWORD),
                ('szDevice', W.WCHAR * 32)]


class WINDOWPLACEMENT(ctypes.Structure):
    _fields_ = [('length', W.UINT), ('flags', W.UINT), ('showCmd', W.UINT), ('ptMin', W.POINT), ('ptMax', W.POINT),
                ('rcNormal', W.RECT)]


def find_windows(title, own=True):
    """Top-level windows with this exact title, in this process (own=True) or in any other process."""
    me, out = os.getpid(), []

    def cb(h, _):
        buf = ctypes.create_unicode_buffer(256)
        u32.GetWindowTextW(h, buf, 256)
        if buf.value == title:
            pid = W.DWORD()
            u32.GetWindowThreadProcessId(h, ctypes.byref(pid))
            if (pid.value == me) == own:
                out.append(h)
        return True

    u32.EnumWindows(WNDENUMPROC(cb), 0)
    return out


def monitors():
    """Monitors left to right: {x, y, w, h} of the work area, the full bounds, and whether it is the primary."""
    out = []

    def cb(hmon, hdc, rc, _):
        mi = MONITORINFOEX()
        mi.cbSize = ctypes.sizeof(mi)
        u32.GetMonitorInfoW(hmon, ctypes.byref(mi))
        m, w = mi.rcMonitor, mi.rcWork
        out.append({'x': w.left, 'y': w.top, 'w': w.right - w.left, 'h': w.bottom - w.top,
                    'full': [m.left, m.top, m.right - m.left, m.bottom - m.top], 'primary': bool(mi.dwFlags & 1),
                    'device': mi.szDevice, 'handle': hmon or 0})
        return True

    u32.EnumDisplayMonitors(None, None, MONITORENUMPROC(cb), 0)
    out.sort(key=lambda m: (m['full'][0], m['full'][1]))
    return out


def monitor_of(hwnd):
    h = u32.MonitorFromWindow(hwnd, 2) or 0  # MONITOR_DEFAULTTONEAREST
    for i, m in enumerate(monitors()):
        if m['handle'] == h:
            return i
    return 0


def get_rect(hwnd):
    """Window bounds (x, y, w, h) in screen pixels, the restored bounds when it is minimized."""
    if u32.IsIconic(hwnd):
        wp = WINDOWPLACEMENT()
        wp.length = ctypes.sizeof(wp)
        u32.GetWindowPlacement(hwnd, ctypes.byref(wp))
        r = wp.rcNormal
    else:
        r = W.RECT()
        u32.GetWindowRect(hwnd, ctypes.byref(r))
    return [r.left, r.top, r.right - r.left, r.bottom - r.top]


def set_rect(hwnd, x, y, w, h):
    u32.SetWindowPos(hwnd, None, int(x), int(y), int(w), int(h), SWP_NOZORDER | SWP_NOACTIVATE)


def fit_rect(rect, mons=None):
    """Keep a saved rect on a monitor that still exists; otherwise centre it on the primary."""
    mons = mons or monitors()
    x, y, w, h = rect
    for m in mons:
        if m['x'] - 40 <= x + w // 2 <= m['x'] + m['w'] + 40 and m['y'] - 40 <= y + 20 <= m['y'] + m['h']:
            return [x, y, min(w, m['w']), min(h, m['h'])]
    p = next((m for m in mons if m['primary']), mons[0])
    w, h = min(w, p['w']), min(h, p['h'])
    return [p['x'] + (p['w'] - w) // 2, p['y'] + (p['h'] - h) // 2, w, h]


def rect_on_monitor(rect, mon):
    """Same size, moved to the right edge of a monitor's work area with a small margin."""
    w, h = min(rect[2], mon['w']), min(rect[3], mon['h'])
    return [mon['x'] + mon['w'] - w - 24, mon['y'] + max(24, (mon['h'] - h) // 4), w, h]


def set_topmost(hwnd, on):
    u32.SetWindowPos(hwnd, HWND_TOPMOST if on else HWND_NOTOPMOST, 0, 0, 0, 0,
                     SWP_NOMOVE | SWP_NOSIZE | SWP_NOACTIVATE)


def is_shown(hwnd):
    return bool(u32.IsWindowVisible(hwnd)) and not u32.IsIconic(hwnd)


def is_foreground(hwnd):
    return u32.GetForegroundWindow() == hwnd


def hide(hwnd, mode):
    if mode == 'hide':
        u32.ShowWindow(hwnd, SW_HIDE)
    elif is_foreground(hwnd):
        u32.ShowWindow(hwnd, SW_MINIMIZE)  # hands focus back to the window underneath, normally the game
    else:
        u32.ShowWindow(hwnd, SW_SHOWMINNOACTIVE)


def covered(hwnd):
    """True when the foreground window sits above this one and overlaps it, as the game does after a click into it."""
    fg = u32.GetForegroundWindow()
    if not fg or fg == hwnd:
        return False
    a, b = W.RECT(), W.RECT()
    u32.GetWindowRect(hwnd, ctypes.byref(a))
    u32.GetWindowRect(fg, ctypes.byref(b))
    if a.right <= b.left or b.right <= a.left or a.bottom <= b.top or b.bottom <= a.top:
        return False
    x = hwnd
    while True:
        x = u32.GetWindow(x, GW_HWNDPREV)
        if not x:
            return False
        if x == fg:
            return True


def show(hwnd, focus, topmost):
    u32.ShowWindow(hwnd, SW_SHOWNOACTIVATE)  # also restores a minimized window, without taking focus
    flags = SWP_NOMOVE | SWP_NOSIZE | SWP_NOACTIVATE
    # HWND_TOP is ignored when a background process asks (a controller press gives no foreground rights), but
    # passing through the topmost band always lands the window above the game.
    u32.SetWindowPos(hwnd, HWND_TOPMOST, 0, 0, 0, 0, flags)
    if not topmost:
        u32.SetWindowPos(hwnd, HWND_NOTOPMOST, 0, 0, 0, 0, flags)
    if focus:
        force_foreground(hwnd)


def force_foreground(hwnd):
    """SetForegroundWindow from a background process, by sharing input state with the current foreground thread."""
    if u32.IsIconic(hwnd):
        u32.ShowWindow(hwnd, SW_RESTORE)
    fg = u32.GetForegroundWindow()
    ftid = u32.GetWindowThreadProcessId(fg, None) if fg else 0
    me = k32.GetCurrentThreadId()
    attached = bool(ftid and ftid != me and u32.AttachThreadInput(me, ftid, True))
    try:
        u32.BringWindowToTop(hwnd)
        u32.SetForegroundWindow(hwnd)
    finally:
        if attached:
            u32.AttachThreadInput(me, ftid, False)


def native_drag(hwnd, edge):
    """Start a native move or resize loop. Must run on the window's own thread."""
    u32.ReleaseCapture()
    u32.SendMessageW(hwnd, WM_NCLBUTTONDOWN, HT.get(edge, HTCAPTION), 0)


def style(hwnd, border_rgb=(0x6b, 0x5f, 0x3e)):
    """Windows 11 frame touches: dark mode, rounded corners, a dim gold 1px border."""
    one = ctypes.c_int(1)
    dwm.DwmSetWindowAttribute(hwnd, 20, ctypes.byref(one), 4)  # DWMWA_USE_IMMERSIVE_DARK_MODE
    rnd = ctypes.c_int(2)
    dwm.DwmSetWindowAttribute(hwnd, 33, ctypes.byref(rnd), 4)  # DWMWA_WINDOW_CORNER_PREFERENCE: round
    r, g, b = border_rgb
    col = ctypes.c_uint(r | (g << 8) | (b << 16))
    dwm.DwmSetWindowAttribute(hwnd, 34, ctypes.byref(col), 4)  # DWMWA_BORDER_COLOR


# --- global keyboard hotkey -------------------------------------------------------------------------------------

MODS = {'alt': 0x1, 'ctrl': 0x2, 'shift': 0x4, 'win': 0x8}
NAMED_KEYS = {'space': 0x20, 'pageup': 0x21, 'pagedown': 0x22, 'end': 0x23, 'home': 0x24, 'insert': 0x2D,
              'delete': 0x2E, 'pause': 0x13, 'scrolllock': 0x91, 'tab': 0x09, 'backquote': 0xC0, 'minus': 0xBD,
              'equal': 0xBB, 'bracketleft': 0xDB, 'bracketright': 0xDD, 'backslash': 0xDC, 'semicolon': 0xBA,
              'quote': 0xDE, 'comma': 0xBC, 'period': 0xBE, 'slash': 0xBF}


def parse_hotkey(spec):
    """'ctrl+shift+c' -> (modifiers, virtual key). None for an empty or unknown spec."""
    if not spec:
        return None
    mods, vk = 0, None
    for part in spec.lower().split('+'):
        part = part.strip()
        if part in MODS:
            mods |= MODS[part]
        elif len(part) == 1 and part.isalnum():
            vk = ord(part.upper())
        elif part[:1] == 'f' and part[1:].isdigit() and 1 <= int(part[1:]) <= 24:
            vk = 0x70 + int(part[1:]) - 1
        elif part.startswith('num') and part[3:].isdigit():
            vk = 0x60 + int(part[3:])
        elif part in NAMED_KEYS:
            vk = NAMED_KEYS[part]
        else:
            return None
    return (mods, vk) if vk else None


class HotkeyThread(threading.Thread):
    """Owns one RegisterHotKey registration and calls on_press each time it fires."""

    def __init__(self, spec, on_press):
        super().__init__(daemon=True)
        self.spec, self.on_press = spec, on_press
        self.tid, self.error = None, None
        self.ready = threading.Event()

    def set(self, spec):
        self.spec = spec
        if self.tid:
            u32.PostThreadMessageW(self.tid, WM_APP, 0, 0)

    def _register(self):
        u32.UnregisterHotKey(None, 1)
        self.error = None
        hk = parse_hotkey(self.spec)
        if self.spec and not hk:
            self.error = 'unknown key'
        elif hk and not u32.RegisterHotKey(None, 1, hk[0] | 0x4000, hk[1]):  # MOD_NOREPEAT
            self.error = 'taken by another program'

    def run(self):
        msg = W.MSG()
        u32.PeekMessageW(ctypes.byref(msg), None, 0, 0, 0)  # creates this thread's message queue
        self.tid = k32.GetCurrentThreadId()
        self._register()
        self.ready.set()
        while u32.GetMessageW(ctypes.byref(msg), None, 0, 0) > 0:
            if msg.message == WM_HOTKEY:
                try:
                    self.on_press()
                except Exception:
                    pass
            elif msg.message == WM_APP:
                self._register()
