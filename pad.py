"""XInput gamepad reader: a show/hide button combo, combo recording, and menu navigation keys.

XInput sees Xbox pads and anything Steam Input presents as one. The Guide button comes from the undocumented
XInputGetStateEx (ordinal 100); the port does not bind Guide, so a combo with it never reaches the game.
"""
import ctypes
import threading
import time

BUTTONS = {
    'dpad_up': 0x0001, 'dpad_down': 0x0002, 'dpad_left': 0x0004, 'dpad_right': 0x0008,
    'start': 0x0010, 'back': 0x0020, 'lstick': 0x0040, 'rstick': 0x0080, 'lb': 0x0100, 'rb': 0x0200,
    'guide': 0x0400, 'a': 0x1000, 'b': 0x2000, 'x': 0x4000, 'y': 0x8000,
    'lt': 0x10000, 'rt': 0x20000,  # triggers past half travel, as virtual bits
}
NAV = {'dpad_up': 'up', 'dpad_down': 'down', 'dpad_left': 'left', 'dpad_right': 'right', 'lb': 'prev_tab',
       'rb': 'next_tab', 'b': 'hide', 'y': 'filter', 'x': 'sort'}
REPEAT = {'up', 'down', 'left', 'right'}


class _Gamepad(ctypes.Structure):
    _fields_ = [('buttons', ctypes.c_ushort), ('lt', ctypes.c_ubyte), ('rt', ctypes.c_ubyte),
                ('lx', ctypes.c_short), ('ly', ctypes.c_short), ('rx', ctypes.c_short), ('ry', ctypes.c_short)]


class _State(ctypes.Structure):
    _fields_ = [('packet', ctypes.c_uint), ('pad', _Gamepad)]


def _load():
    for name in ('xinput1_4', 'xinput1_3', 'xinput9_1_0'):
        try:
            dll = ctypes.WinDLL(name)
        except OSError:
            continue
        try:
            fn = dll[100]  # XInputGetStateEx: same as XInputGetState plus the Guide bit
        except (AttributeError, OSError):
            fn = dll.XInputGetState
        fn.argtypes = [ctypes.c_uint, ctypes.POINTER(_State)]
        fn.restype = ctypes.c_uint
        return fn
    return None


def mask_of(names):
    m = 0
    for n in names:
        m |= BUTTONS.get(n, 0)
    return m


def names_of(mask):
    return [n for n, b in BUTTONS.items() if mask & b]


class PadThread(threading.Thread):
    """Polls every pad at about 60 Hz.

    on_combo()      the combo was held for hold_ms
    on_nav(action)  a navigation press, only while nav_enabled() returns True
    on_record(names) the buttons held together during a recording, once all are released
    """

    def __init__(self, combo, hold_ms, on_combo, on_nav, on_record, nav_enabled):
        super().__init__(daemon=True)
        self.get_state = _load()
        self.set_combo(combo, hold_ms)
        self.on_combo, self.on_nav, self.on_record, self.nav_enabled = on_combo, on_nav, on_record, nav_enabled
        self.recording = False
        self.connected = []
        self._stop = threading.Event()

    def set_combo(self, combo, hold_ms):
        self.combo = mask_of(combo)
        self.hold = max(0, hold_ms) / 1000.0

    def record(self, on=True):
        self.recording = on
        self._peak = 0

    def stop(self):
        self._stop.set()

    def _read(self, slot):
        st = _State()
        if self.get_state(slot, ctypes.byref(st)) != 0:
            return None
        m = st.pad.buttons
        if st.pad.lt > 128:
            m |= BUTTONS['lt']
        if st.pad.rt > 128:
            m |= BUTTONS['rt']
        return m

    def run(self):
        if not self.get_state:
            return
        held_since, fired, prev, next_scan = None, False, 0, 0.0
        repeat_at = {}
        while not self._stop.is_set():
            now = time.monotonic()
            if now >= next_scan:  # polling an empty slot is slow, so look for new pads only every 2 s
                self.connected = [s for s in range(4) if self._read(s) is not None]
                next_scan = now + 2.0
            mask = 0
            for s in self.connected:
                m = self._read(s)
                if m is not None:
                    mask |= m

            if self.recording:
                if mask:
                    self._peak |= mask
                elif self._peak:
                    names, self.recording = names_of(self._peak), False
                    self.on_record(names)
                prev = mask
                time.sleep(0.016)
                continue

            if self.combo and mask & self.combo == self.combo:
                held_since = held_since or now
                if not fired and now - held_since >= self.hold:
                    fired = True
                    self.on_combo()
            else:
                held_since, fired = None, False

            in_combo = self.combo and mask & self.combo and held_since
            if not in_combo and self.nav_enabled():
                for name, action in NAV.items():
                    b = BUTTONS[name]
                    if mask & b and not prev & b:
                        self.on_nav(action)
                        repeat_at[name] = now + 0.36
                    elif mask & b and action in REPEAT and now >= repeat_at.get(name, 1e18):
                        self.on_nav(action)
                        repeat_at[name] = now + 0.09
            prev = mask
            time.sleep(0.016)
