"""TotK Cook Helper, Linux save mode.

Reads the newest TotK PC recomp save and lists what its material pouch can cook.
This port deliberately does not read the game's memory or block controller input:
it refreshes whenever the save file changes. The UI is the same ui/index.html.

Run from the repository root:

    python3 cook_helper_linux.py --game /path/to/TotK
"""
import argparse
import fcntl
import json
import os
import sys
import tempfile
import threading
import time

import cook_core as cc

HERE = os.path.dirname(os.path.abspath(__file__))
SETTINGS = os.path.join(HERE, 'settings.json')
TITLE = 'TotK Cook Helper'
POLL_S = 15.0
MIN_POLL_S = 0.5
SPINNER_MIN_S = 0.35

DEFAULTS = {
    'on_top': True,
    'hide_mode': 'minimize',
    'start_hidden': False,
    'dish_sort': 'hearts',
    'dish_effect': '',
    'tab': 'dishes',
    'combo': ['lstick', 'rstick'],
    'hold_ms': 300,
    'hotkey': 'ctrl+shift+c',
    'pad_nav': False,
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
    return s


def save_settings(s):
    try:
        with open(SETTINGS, 'w', encoding='utf-8') as f:
            json.dump(s, f, indent=1)
    except OSError:
        pass


def load_icons():
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


def monitor_list():
    """The Gdk monitor rectangles, or one sensible fallback."""
    try:
        import gi
        gi.require_version('Gdk', '3.0')
        from gi.repository import Gdk
        display = Gdk.Display.get_default()
        if display:
            primary = display.get_primary_monitor()
            out = []
            for i in range(display.get_n_monitors()):
                mon = display.get_monitor(i)
                geo = mon.get_geometry()
                out.append({'x': geo.x, 'y': geo.y, 'w': geo.width, 'h': geo.height, 'primary': mon == primary})
            if out:
                return out
    except Exception:
        pass
    return [{'x': 0, 'y': 0, 'w': 1920, 'h': 1080, 'primary': True}]


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

    def refresh(self):
        self._app.poll_once()
        self._app.push()

    # The shared UI still has these calls; they are harmless in save mode.
    def drag(self, edge):
        pass

    def move_to_monitor(self, index):
        pass

    def record_combo(self, on):
        pass


class App:
    def __init__(self, game, poll_s=POLL_S):
        self.game = os.path.abspath(game)
        self.save_root = os.path.join(self.game, 'profile', 'save')
        self.cook = cc.Cook()
        self.s = load_settings()
        self.window = None
        self.version = 0
        self.data_version = 0
        self.payload = None
        self.save_path = self.save_mtime = None
        self.rows, self.inv = [], {}
        self.error = None
        self.checking = False
        self.poll_s = max(MIN_POLL_S, float(poll_s))
        self.next_scan = time.time() + self.poll_s
        self._inv_key = None
        self.closing = False
        self.lock = threading.Lock()
        self.lock_handle = None

    # --- window -------------------------------------------------------------------------------------------------

    def run(self):
        import webview
        self.window = webview.create_window(
            TITLE, url=os.path.join(HERE, 'ui', 'index.html'), js_api=Api(self), width=880, height=600,
            min_size=(400, 340), background_color='#0a0d0c', text_select=False, on_top=self.s['on_top'])
        self.window.events.closing += self.on_closing
        webview.start(self.boot, gui='gtk', private_mode=True)

    def boot(self):
        self.window.events.loaded.wait(15)
        self.next_scan = time.time() + self.poll_s
        self.poll_once()
        if self.payload is None:
            self.push()
        if self.s['start_hidden']:
            try:
                self.window.minimize()
            except Exception:
                pass
        threading.Thread(target=self.loop, daemon=True).start()

    def hide(self):
        # Without a global hotkey, minimize so the window stays reachable from the taskbar.
        # Do not fall back to hide(); a hidden window would have no way back.
        if self.window:
            try:
                self.window.minimize()
            except Exception:
                pass

    def close(self):
        if self.window:
            self.window.destroy()

    def on_closing(self):
        self.closing = True
        save_settings(self.s)

    # --- settings ------------------------------------------------------------------------------------------------

    def set_setting(self, key, value):
        if key not in DEFAULTS:
            return
        self.s[key] = value
        if key == 'on_top' and self.window:
            try:
                self.window.on_top = bool(value)
            except Exception:
                pass
        save_settings(self.s)
        self.push()

    # --- save polling ---------------------------------------------------------------------------------------------

    def loop(self):
        while not self.closing:
            self.next_scan = time.time() + self.poll_s
            self.poll_once()
            while not self.closing and time.time() < self.next_scan:
                time.sleep(min(0.2, max(0.0, self.next_scan - time.time())))

    def poll_once(self):
        try:
            path = cc.newest_save(self.save_root)
            mtime = os.path.getmtime(path) if path else None
            if path and (path != self.save_path or mtime != self.save_mtime):
                self.checking = True
                self.push_status()
                started = time.monotonic()
                inv, _n = cc.read_inventory(path, with_size=True)  # raises while the game is mid-write
                self.save_path, self.save_mtime = path, mtime
                self.error = None
                key = tuple(sorted(inv.items()))
                if key != self._inv_key:
                    self._inv_key = key
                    self.rows = self.cook.what_can_i_cook(inv)
                    self.data_version += 1
                self.inv = inv
                # Keep the spinner visible long enough to be readable.
                remain = SPINNER_MIN_S - (time.monotonic() - started)
                if remain > 0:
                    time.sleep(remain)
                self.checking = False
                self.push()
            elif not path and self.error != 'nosave':
                self.error = 'nosave'
                self.checking = False
                self.push()
            else:
                self.push_status()
        except Exception as e:  # keep polling; the page shows that the save is being written
            self.checking = False
            if self.error != e.__class__.__name__:
                self.error = e.__class__.__name__
            self.push_status()

    def save_status(self):
        return {'slot': os.path.basename(os.path.dirname(self.save_path)) if self.save_path else None,
                'mtime': self.save_mtime, 'error': self.error, 'live': 'off',
                'checking': self.checking, 'next_scan': self.next_scan, 'poll_s': self.poll_s}

    def push_status(self):
        with self.lock:
            self.version += 1
            if self.payload is None:
                self.payload = self.build()
            else:
                self.payload['version'] = self.version
                self.payload['save'] = self.save_status()

    def push(self):
        with self.lock:
            self.version += 1
            self.payload = self.build()

    # --- page payload ---------------------------------------------------------------------------------------------

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
        mons = monitor_list()
        return {
            'version': self.version, 'data_version': self.data_version, 'dishes': dishes, 'materials': mats,
            'save': self.save_status(),
            'settings': {k: v for k, v in self.s.items() if k != 'rect'},
            'pad': {'connected': 0, 'recording': False, 'note': None, 'available': False},
            'hotkey_error': None,
            'monitors': mons,
            'monitor': 0, 'with_game': False, 'platform': 'linux',
        }


def already_running():
    """One helper at a time; keep the lock file descriptor open for the process lifetime."""
    path = os.path.join(tempfile.gettempdir(), 'totk-cook-helper.lock')
    handle = open(path, 'w')
    try:
        fcntl.flock(handle, fcntl.LOCK_EX | fcntl.LOCK_NB)
    except OSError:
        handle.close()
        return True
    App.lock_handle = handle
    return False


def find_game(argument):
    if argument:
        return os.path.abspath(os.path.expanduser(argument))
    return os.path.abspath(os.path.join(HERE, '..', 'game'))


def main(argv=None):
    ap = argparse.ArgumentParser(description='TotK Cook Helper, Linux save mode')
    ap.add_argument('--game', help='folder holding profile/save; default: ../game')
    ap.add_argument('--poll', type=float, default=POLL_S, help='seconds between save scans (default: 15)')
    ap.add_argument('--check', action='store_true', help='read the newest save, print counts, and exit')
    args = ap.parse_args(argv)

    game = find_game(args.game)
    if not os.path.isfile(os.path.join(HERE, 'cookdata.json')):
        print('Missing cookdata.json. Run: python3 build_data.py "%s"' % game, file=sys.stderr)
        return 1
    if not os.path.isdir(os.path.join(game, 'profile', 'save')):
        print('Warning: no profile/save folder under %s' % game, file=sys.stderr)

    if args.check:
        app = App(game, args.poll)
        app.next_scan = time.time() + app.poll_s
        app.poll_once()
        p = app.build()
        print(json.dumps({'game': game, 'save': app.save_path, 'slot': p['save']['slot'],
                          'materials': len(p['materials']), 'dishes': len(p['dishes'])}, ensure_ascii=False))
        return 0

    if already_running():
        print('TotK Cook Helper is already running.', file=sys.stderr)
        return 1
    App(game, args.poll).run()
    return 0


if __name__ == '__main__':
    sys.exit(main())
