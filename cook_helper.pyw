"""TotK Cook Helper: a window that lists what your current inventory can cook.

It reads the newest save slot of the PC port and refreshes whenever the game saves. The UI is ui/index.html in a
pywebview window. Show or hide it with the controller combo, the keyboard hotkey or alt-tab; all of that is set in
the gear panel and stored in settings.json.

Start it with "TotK Cook Helper.bat" or:  pyw -3 -E cook_helper.pyw
"""
import ctypes
import json
import os
import sys
import threading
import time

import webview

import cook_core as cc
import livemem
import pad
import proc
import winctl as wc

WITH_GAME = '--with-game' in sys.argv  # started by the watcher with the game: don't take the focus at start
SYNCHRONIZE, WAIT_TIMEOUT = 0x00100000, 0x102
k32 = ctypes.WinDLL('kernel32', use_last_error=True)
k32.OpenProcess.argtypes = [ctypes.c_ulong, ctypes.c_int, ctypes.c_ulong]
k32.OpenProcess.restype = ctypes.c_void_p
k32.WaitForSingleObject.argtypes = [ctypes.c_void_p, ctypes.c_ulong]
k32.WaitForSingleObject.restype = ctypes.c_ulong
k32.CloseHandle.argtypes = [ctypes.c_void_p]
TITLE = 'TotK Cook Helper'
HERE = os.path.dirname(os.path.abspath(__file__))
SETTINGS = os.path.join(HERE, 'settings.json')
POLL_S = 2.0
LIVE_S = 0.5  # memory read interval once the pouch is found
LIVE_RETRY_S = 30  # wait between scans that found nothing (title screen, save not loaded yet)

DEFAULTS = {
    'rect': None,                     # [x, y, w, h] in screen pixels
    'on_top': True,
    'take_focus': True,               # showing the helper gives it the focus, so the pad drives the helper and not the game
    'hide_mode': 'minimize',          # minimize keeps it in alt-tab and the taskbar; hide removes it from both
    'combo': ['lstick', 'rstick'],    # both sticks clicked together
    'hold_ms': 300,
    'hotkey': 'ctrl+shift+c',
    'dish_sort': 'hearts',            # hearts, time, name or effect
    'dish_effect': '',                # show only dishes with this effect; 'none' for no effect, '' for all
    'pad_nav': True,                  # the pad moves the selection while the helper has focus
    'start_hidden': False,
    'tab': 'dishes',
}

KIND_NAMES = {'CookMeat': 'Meat', 'CookFish': 'Fish', 'CookMushroom': 'Mushroom', 'CookFruit': 'Fruit',
              'CookSpice': 'Spice', 'CookPlant': 'Plant', 'CookInsect': 'Critter', 'CookEnemy': 'Monster part',
              'CookGolem': 'Construct part', 'CookOre': 'Mineral', 'CookOther': 'Other'}
GLYPH_ORDER = [('CookMeat', 'meat'), ('CookFish', 'fish'), ('CookMushroom', 'mushroom'), ('CookFruit', 'fruit'),
               ('CookSpice', 'spice'), ('CookPlant', 'plant'), ('CookInsect', 'insect'), ('CookEnemy', 'enemy'),
               ('CookGolem', 'golem'), ('CookOre', 'ore'), ('CookOther', 'pouch')]


def load_settings():
    s = dict(DEFAULTS)
    try:
        old = json.load(open(SETTINGS, encoding='utf-8'))
    except (OSError, ValueError):
        old = {}
    s.update({k: v for k, v in old.items() if k in DEFAULTS})
    g = old.get('geometry')  # the Tk window stored "640x520+3677+250"
    if not s['rect'] and isinstance(g, str):
        try:
            size, x, y = g.split('+')[0], int(g.split('+')[1]), int(g.split('+')[2])
            w, h = (int(v) for v in size.split('x'))
            s['rect'] = [x, y, max(w, 760), max(h, 560)]
        except (ValueError, IndexError):
            pass
    return s


def save_settings(s):
    try:
        with open(SETTINGS, 'w', encoding='utf-8') as f:
            json.dump(s, f, indent=1)
    except OSError:
        pass


def load_icons():
    """Actor name -> icon file in ui/icons, written by build_icons.py from the game's own textures."""
    try:
        with open(os.path.join(HERE, 'ui', 'icons', 'index.json'), encoding='utf-8') as f:
            return json.load(f)
    except (OSError, ValueError):
        return {}


ICONS = load_icons()


def dish_icon(dish, effect):
    """Elixirs share one actor and the game picks the bottle by effect."""
    return ICONS.get('%s_%s' % (dish, effect)) or ICONS.get(dish)


def glyph(m):
    tags = m.get('all_tags', [])
    for tag, g in GLYPH_ORDER:
        if tag in tags:
            return g
    return 'pouch'


class Api:
    """Methods the page calls as window.pywebview.api.<name>(). Private attributes stay hidden from the page."""

    def __init__(self, app):
        self._app = app

    def state(self, version):
        a = self._app
        return a.payload if a.payload and a.payload['version'] != version else None

    def set_setting(self, key, value):
        self._app.set_setting(key, value)

    def hide(self):
        self._app.hide()

    def close(self):
        self._app.close()

    def drag(self, edge):
        self._app.native_drag(edge)

    def move_to_monitor(self, index):
        self._app.move_to_monitor(int(index))

    def record_combo(self, on):
        self._app.record_combo(bool(on))


class App:
    def __init__(self):
        self.cook = cc.Cook()
        self.s = load_settings()
        self.hwnd = None
        self.window = None
        self.version = 0
        self.payload = None
        self.save_path = self.save_mtime = None
        self.rows, self.inv = [], {}
        self.save_inv, self.save_n = {}, None
        self.live = 'off'  # off | scanning | on | failed
        self.inv_lock = threading.Lock()
        self.error = None
        self.recording = False
        self.record_note = None
        self.closing = False
        self.lock = threading.Lock()
        self.pad = pad.PadThread(self.s['combo'], self.s['hold_ms'], self.toggle, self.nav, self.recorded,
                                 lambda: self.s['pad_nav'] and self.hwnd and wc.is_foreground(self.hwnd))
        self.hotkey = wc.HotkeyThread(self.s['hotkey'], self.toggle)

    # --- window -------------------------------------------------------------------------------------------------

    def run(self):
        self.window = webview.create_window(
            TITLE, url=os.path.join(HERE, 'ui', 'index.html'), js_api=Api(self), width=880, height=600,
            frameless=True, easy_drag=False, hidden=True, background_color='#0a0d0c', min_size=(400, 340),
            text_select=False)
        self.window.events.closing += self.on_closing
        webview.start(self.boot, gui='edgechromium', private_mode=True)

    def boot(self):
        self.window.events.loaded.wait(15)
        for _ in range(50):
            found = wc.find_windows(TITLE)
            if found:
                self.hwnd = found[0]
                break
            time.sleep(0.1)
        if not self.hwnd:
            return
        wc.style(self.hwnd)
        rect = self.s['rect'] or wc.rect_on_monitor([0, 0, 880, 600], wc.monitors()[-1])
        wc.set_rect(self.hwnd, *wc.fit_rect(rect))
        if not self.s['start_hidden']:
            wc.show(self.hwnd, focus=not WITH_GAME and self.s['take_focus'], topmost=self.s['on_top'])
        elif self.s['hide_mode'] == 'minimize':
            wc.show(self.hwnd, focus=False, topmost=False)
            wc.hide(self.hwnd, 'minimize')
        wc.set_topmost(self.hwnd, self.s['on_top'])
        self.pad.start()
        self.hotkey.start()
        self.hotkey.ready.wait(2)
        threading.Thread(target=self.live_loop, daemon=True).start()
        threading.Thread(target=self.game_watch, daemon=True).start()
        self.loop()

    def toggle(self):
        if not self.hwnd:
            return
        if wc.is_shown(self.hwnd) and not wc.covered(self.hwnd):
            self.hide()
        else:
            wc.show(self.hwnd, focus=self.s['take_focus'], topmost=self.s['on_top'])
            self.push()

    def hide(self):
        if self.hwnd:
            wc.hide(self.hwnd, self.s['hide_mode'])

    def native_drag(self, edge):
        from System import Action  # pythonnet, already loaded by pywebview
        form = self.window.native
        form.BeginInvoke(Action(lambda: wc.native_drag(self.hwnd, edge)))

    def move_to_monitor(self, i):
        mons = wc.monitors()
        if self.hwnd and 0 <= i < len(mons):
            wc.set_rect(self.hwnd, *wc.rect_on_monitor(wc.get_rect(self.hwnd), mons[i]))
            self.remember_rect()
            self.push()

    def remember_rect(self):
        if self.hwnd:
            self.s['rect'] = wc.get_rect(self.hwnd)
            save_settings(self.s)

    def on_closing(self):
        self.closing = True
        if self.hwnd:
            self.s['rect'] = wc.get_rect(self.hwnd)
        save_settings(self.s)
        self.pad.stop()

    def close(self):
        if not self.closing:
            self.window.destroy()

    # --- settings and pad ---------------------------------------------------------------------------------------

    def set_setting(self, key, value):
        if key not in DEFAULTS or key == 'rect':
            return
        self.s[key] = value
        if key == 'on_top' and self.hwnd:
            wc.set_topmost(self.hwnd, bool(value))
        if key in ('combo', 'hold_ms'):
            self.pad.set_combo(self.s['combo'], int(self.s['hold_ms']))
        if key == 'hotkey':
            self.hotkey.set(value)
            time.sleep(0.15)  # let the hotkey thread report whether the registration worked
        save_settings(self.s)
        self.push()

    def record_combo(self, on):
        self.recording, self.record_note = on, None
        self.pad.record(on)
        self.push()

    def recorded(self, names):
        self.recording = False
        if len(names) == 1 and names[0] != 'guide':
            self.record_note = 'One button alone also does something in the game. Hold two or more together.'
        else:
            self.s['combo'] = names
            self.pad.set_combo(names, int(self.s['hold_ms']))
            save_settings(self.s)
        self.push()

    def nav(self, action):
        if action == 'hide':
            self.hide()
        elif self.window:
            self.window.evaluate_js('window.padNav && window.padNav(%s)' % json.dumps(action))

    # --- save polling ---------------------------------------------------------------------------------------------

    def loop(self):
        while not self.closing:
            self.poll()
            time.sleep(POLL_S)

    # --- close with the game ----------------------------------------------------------------------------------------

    def game_watch(self):
        """Close the helper the moment totk.exe ends, however either was started. Opening the helper without the game
        is fine: it closes only after it has seen the game run."""
        seen = False
        while not self.closing:
            pid = proc.pid_of('totk.exe')
            h = k32.OpenProcess(SYNCHRONIZE, False, pid) if pid else None
            if not h:
                if seen:
                    self.quit_with_game()
                    return
                time.sleep(2)
                continue
            seen = True
            while not self.closing and k32.WaitForSingleObject(h, 500) == WAIT_TIMEOUT:
                pass
            k32.CloseHandle(h)  # the loop looks again, in case the game restarted itself under a new process

    def quit_with_game(self):
        killer = threading.Timer(5, os._exit, (0,))  # if the window or a thread hangs, end the process anyway
        killer.daemon = True
        killer.start()
        self.close()

    def poll(self):
        try:
            path = cc.newest_save()
            mtime = os.path.getmtime(path) if path else None
            if path and (path != self.save_path or mtime != self.save_mtime):
                inv, n = cc.read_inventory(path, with_size=True)  # raises while the game is mid-write; retried next poll
                self.save_inv, self.save_n = inv, n
                self.save_path, self.save_mtime = path, mtime
                self.error = None
                if self.live == 'on':
                    self.push()  # the status line shows the new save time; memory stays the source
                else:
                    self.set_inv(inv)
            elif not path and self.error != 'nosave':
                self.error = 'nosave'
                self.push()
        except Exception as e:  # keep polling; the page shows that the save is being written
            if self.error != e.__class__.__name__:
                self.error = e.__class__.__name__
                self.push()

    def set_inv(self, inv):
        with self.inv_lock:
            self.inv = inv
            self.rows = self.cook.what_can_i_cook(inv)
        self.push()

    # --- live pouch from the game's memory ------------------------------------------------------------------------

    def live_loop(self):
        """Find the pouch in totk.exe once per launch, then read it twice a second. The save is the fallback."""
        pouch, failed_at = None, 0
        while not self.closing:
            try:
                if pouch is None:
                    pid = proc.pid_of('totk.exe')
                    if pid and self.save_n and time.time() - failed_at > LIVE_RETRY_S:
                        self.set_live('scanning')
                        try:
                            pouch = livemem.Pouch(pid)
                            pouch.find(self.save_n, set(self.cook.mat), hint=self.save_inv, stop=lambda: self.closing)
                        except (OSError, livemem.Gone):
                            if pouch:
                                pouch.close()
                            pouch, failed_at = None, time.time()
                            self.set_live('failed')
                            continue
                        self.set_live('on')
                    elif not pid:
                        self.set_live('off')
                if pouch is not None:
                    inv = pouch.read()
                    if inv != self.inv:
                        self.set_inv(inv)
            except livemem.Gone:  # the game exited or loaded something that moved the arrays: scan again
                pouch.close()
                pouch = None
                self.set_live('off')
                if self.save_inv:
                    self.set_inv(self.save_inv)
            time.sleep(LIVE_S)

    def set_live(self, state):
        if self.live != state:
            self.live = state
            self.push()

    def push(self):
        with self.lock:
            self.version += 1
            self.payload = self.build()

    def build(self):
        c = self.cook
        rate = c.sys.get('LifeRecoverRate', 2.0)
        dishes = []
        for r in self.rows:
            counts = {}
            for a in r['pot']:
                counts[a] = counts.get(a, 0) + 1
            pot = [{'actor': a, 'name': c.name(a), 'n': n, 'glyph': glyph(c.mat.get(a, {})), 'icon': ICONS.get(a),
                    'effect': c.mat.get(a, {}).get('effect', 'None')} for a, n in counts.items()]
            name = c.display_name(r)
            g = 'elixir' if 'Elixir' in r['name'] else max(pot, key=lambda p: (p['n'], p['glyph'] != 'pouch'))['glyph']
            dishes.append({'id': r['dish'], 'name': name, 'hearts': r['hearts'], 'extra': r['extra_hearts'],
                           'effect': r['effect'] or '', 'effect_name': cc.EFFECT_NAMES.get(r['effect'] or 'None', ''),
                           'seconds': r['seconds'], 'mixed': bool(r['mixed_effects'] and not r['effect']),
                           'glyph': g, 'icon': dish_icon(r['dish'], r['effect']), 'pot': pot, 'size': len(r['pot'])})
        mats = []
        for a, n in sorted(self.inv.items(), key=lambda x: c.name(x[0])):
            m = c.mat.get(a, {})
            kinds = [KIND_NAMES[t] for t in m.get('all_tags', []) if t in KIND_NAMES]
            used = [{'id': d['id'], 'name': d['name']} for d in dishes if any(p['actor'] == a for p in d['pot'])]
            mats.append({'id': a, 'name': c.name(a), 'count': n, 'effect': m.get('effect', 'None'),
                         'effect_name': cc.EFFECT_NAMES.get(m.get('effect', 'None'), ''),
                         'hearts': m.get('hp', 0) * rate / 4.0, 'kinds': kinds, 'glyph': glyph(m), 'icon': ICONS.get(a),
                         'known': bool(m), 'used_in': used})
        mons = wc.monitors()
        here = wc.monitor_of(self.hwnd) if self.hwnd else 0
        return {
            'version': self.version, 'dishes': dishes, 'materials': mats,
            'save': {'slot': os.path.basename(os.path.dirname(self.save_path)) if self.save_path else None,
                     'mtime': self.save_mtime, 'error': self.error, 'live': self.live},
            'settings': {k: v for k, v in self.s.items() if k != 'rect'},
            'pad': {'connected': len(self.pad.connected), 'recording': self.recording, 'note': self.record_note,
                    'available': self.pad.get_state is not None},
            'hotkey_error': self.hotkey.error,
            'monitors': [{'x': m['full'][0], 'y': m['full'][1], 'w': m['full'][2], 'h': m['full'][3],
                          'primary': m['primary']} for m in mons],
            'monitor': here, 'with_game': WITH_GAME,
        }


def already_running():
    """One helper at a time. A second start brings the first one forward and exits."""
    k32 = ctypes.windll.kernel32
    App._mutex = k32.CreateMutexW(None, False, 'Local\\TotKCookHelperWindow')
    if k32.GetLastError() != 183:  # ERROR_ALREADY_EXISTS
        return False
    for h in wc.find_windows(TITLE, own=False):
        wc.show(h, focus=True, topmost=False)
    return True


if __name__ == '__main__':
    if not already_running():
        App().run()
