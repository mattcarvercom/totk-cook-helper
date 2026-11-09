"""TotK Companion, Linux save mode.

A read-only window over the newest Tears of the Kingdom save: status, inventory,
armor upgrades, the map, completion tracking, the compendium, and cooking. It
never writes to the save and does not read game memory. The view refreshes when
the game writes a save.

Run from the repository root:

    python3 companion.py --game /path/to/TotK
"""
import argparse
import fcntl
import glob
import json
import os
import sys
import tempfile
import threading
import time

import cook_core as cc
import companion_core as core

HERE = os.path.dirname(os.path.abspath(__file__))
SETTINGS = os.path.join(HERE, 'companion_settings.json')
DATA = os.path.join(HERE, 'ui', 'companion_data')
TITLE = 'TotK Companion'
POLL_S = 15.0
MIN_POLL_S = 0.5
SPINNER_MIN_S = 0.35

DEFAULTS = {
    'on_top': True,
    'start_hidden': False,
    'tab': 'status',
    'save_path': '',
    'ui_state': {},
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


def monitor_list():
    try:
        import gi
        gi.require_version('Gdk', '3.0')
        from gi.repository import Gdk
        display = Gdk.Display.get_default()
        if display:
            out = []
            primary = display.get_primary_monitor()
            for i in range(display.get_n_monitors()):
                mon = display.get_monitor(i)
                geo = mon.get_geometry()
                out.append({'x': geo.x, 'y': geo.y, 'w': geo.width, 'h': geo.height, 'primary': mon == primary})
            if out:
                return out
    except Exception:
        pass
    return [{'x': 0, 'y': 0, 'w': 1920, 'h': 1080, 'primary': True}]


def glyph(material):
    tags = material.get('all_tags', []) if material else []
    for tag, g in GLYPH_ORDER:
        if tag in tags:
            return g
    return 'pouch'


def actor_entry(catalog, actor):
    return catalog.get('actors', {}).get(actor, {})


def base_item(catalog, actor):
    a = actor_entry(catalog, actor)
    return {'actor': actor, 'name': a.get('name') or actor, 'caption': a.get('caption') or '',
            'icon': a.get('icon'), 'sell': a.get('sell', 0), 'category': a.get('category'),
            'kind': a.get('kind') or ''}


def enrich_inventory(inv, catalog, cook):
    armor_by_actor = {a['actor']: a for a in catalog.get('armor', [])}
    out = {}
    for key in core.CATEGORY_ORDER:
        items = []
        for raw in inv.get(key, []):
            it = base_item(catalog, raw['actor'])
            it.update(raw)
            a = actor_entry(catalog, raw['actor'])
            if key in ('weapons', 'bows', 'shields'):
                it['weapon'] = a.get('weapon') or {}
                if raw.get('fused'):
                    fused = actor_entry(catalog, raw['fused'])
                    it['fused_name'] = fused.get('name') or raw['fused']
                    it['fused_icon'] = fused.get('icon')
                else:
                    it.pop('fused', None)
                    it.pop('fused_life', None)
            elif key == 'armor':
                ar = armor_by_actor.get(raw['actor'])
                if ar:
                    for k in ('slot', 'rank', 'defense', 'defense_next', 'next', 'set_key', 'set_name',
                              'upgrade', 'price', 'upgradeable', 'effects', 'effect_info',
                              'set_bonus', 'base'):
                        it[k] = ar.get(k)
                else:
                    it['rank'] = 1
                    it['defense'] = 0
            elif key == 'materials':
                m = cook.mat.get(raw['actor'], {})
                it['effect'] = m.get('effect') or 'None'
                it['effect_name'] = cc.EFFECT_NAMES.get(it['effect'], '')
                it['hearts'] = (m.get('hp', 0) * cook.sys.get('LifeRecoverRate', 2.0)) / 4.0
                it['kinds'] = [KIND_NAMES[t] for t in m.get('all_tags', []) if t in KIND_NAMES]
                it['glyph'] = glyph(m)
            elif key == 'food':
                effs = a.get('effect_icons') or {}
                it['icon'] = effs.get(raw.get('effect') or '') or it.get('icon')
                it['effect_name'] = cc.EFFECT_NAMES.get(raw.get('effect') or 'None', '')
            items.append(it)
        items.sort(key=lambda x: ((x.get('rank') or 0), (x.get('name') or '').lower()))
        out[key] = {'key': key, 'label': core.CATEGORY_LABELS.get(key, key), 'items': items}
    return [out[k] for k in core.CATEGORY_ORDER]


def build_cooking(inv, cook, catalog):
    materials = {x['actor']: x['count'] for x in inv.get('materials', [])}
    rows = cook.what_can_i_cook(materials)
    mats = []
    for x in inv.get('materials', []):
        actor, n = x['actor'], x['count']
        m = cook.mat.get(actor, {})
        mats.append({
            'id': actor, 'name': cook.name(actor), 'count': n,
            'effect': m.get('effect') or 'None',
            'effect_name': cc.EFFECT_NAMES.get(m.get('effect') or 'None', ''),
            'hearts': (m.get('hp', 0) * cook.sys.get('LifeRecoverRate', 2.0)) / 4.0,
            'kinds': [KIND_NAMES[t] for t in m.get('all_tags', []) if t in KIND_NAMES],
            'glyph': glyph(m), 'icon': actor_entry(catalog, actor).get('icon'),
            'known': bool(m),
        })
    mats.sort(key=lambda x: x['name'].lower())
    dishes = []
    for r in rows:
        counts = {}
        for a in r['pot']:
            counts[a] = counts.get(a, 0) + 1
        pot = []
        for a, n in counts.items():
            m = cook.mat.get(a, {})
            pot.append({'actor': a, 'name': cook.name(a), 'n': n, 'glyph': glyph(m),
                        'icon': actor_entry(catalog, a).get('icon'),
                        'effect': m.get('effect') or 'None'})
        eff = r['effect'] or ''
        a = actor_entry(catalog, r['dish'])
        icon = (a.get('effect_icons') or {}).get(eff) or a.get('icon')
        g = 'elixir' if 'Elixir' in r['name'] else max(pot, key=lambda p: (p['n'], p['glyph'] != 'pouch'))['glyph']
        dishes.append({
            'id': r['dish'], 'name': cook.display_name(r), 'hearts': r['hearts'],
            'extra': r['extra_hearts'], 'effect': eff,
            'effect_name': cc.EFFECT_NAMES.get(eff or 'None', ''),
            'seconds': r['seconds'], 'mixed': bool(r['mixed_effects'] and not r['effect']),
            'glyph': g, 'icon': icon, 'pot': pot, 'size': len(r['pot']),
        })
    dishes.sort(key=lambda x: (-(100 + x['extra'] if x['extra'] else x['hearts']), x['name'].lower()))
    return {'dishes': dishes, 'materials': mats}


class Api:
    def __init__(self, app):
        self._app = app

    def bootstrap(self):
        return self._app.bootstrap

    def state(self, version):
        a = self._app
        return a.payload if a.payload and a.payload['version'] != version else None

    def set_setting(self, key, value):
        self._app.set_setting(key, value)

    def refresh(self):
        self._app.poll_once(force=True)
        self._app.push()

    def saves(self):
        return self._app.list_saves()

    def select_save(self, path):
        return self._app.select_save(path)

    def hide(self):
        self._app.hide()

    def close(self):
        self._app.close()


class App:
    def __init__(self, game, poll_s=POLL_S):
        self.game = os.path.abspath(game)
        self.save_root = os.path.join(self.game, 'profile', 'save')
        self.catalog = core.load_catalog(os.path.join(DATA, 'catalog.json'))
        self.cook = cc.Cook(os.path.join(DATA, 'cookdata.json'))
        self.s = load_settings()
        self.selected_save = self.s.get('save_path') or None
        self.window = None
        self.version = 0
        self.data_version = 0
        self.payload = None
        self.bootstrap = None
        self.save = None
        self.save_path = self.save_mtime = None
        self.error = None
        self.checking = False
        self.poll_s = max(MIN_POLL_S, float(poll_s))
        self.next_scan = time.time() + self.poll_s
        self.closing = False
        self.lock = threading.Lock()
        self.lock_handle = None

    # --- window ---------------------------------------------------------------

    def run(self):
        import webview
        self.window = webview.create_window(
            TITLE, url=os.path.join(HERE, 'ui', 'companion.html'), js_api=Api(self),
            width=1220, height=780, min_size=(860, 560), background_color='#0a0d0c',
            text_select=False, on_top=self.s['on_top'])
        self.window.events.closing += self.on_closing
        webview.start(self.boot, gui='gtk', private_mode=True)

    def boot(self):
        self.window.events.loaded.wait(15)
        self.bootstrap = {
            'catalog': self.catalog,
            'settings': {k: v for k, v in self.s.items()},
            'saves': self.list_saves(),
            'selected_save': self.selected_save,
            'platform': 'linux',
        }
        self.next_scan = time.time() + self.poll_s
        self.poll_once(force=True)
        if self.payload is None:
            self.push()
        if self.s['start_hidden']:
            try:
                self.window.minimize()
            except Exception:
                pass
        threading.Thread(target=self.loop, daemon=True).start()

    def hide(self):
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

    # --- settings -------------------------------------------------------------

    def set_setting(self, key, value):
        if key not in DEFAULTS:
            return
        if key == 'ui_state':
            self.s[key] = value if isinstance(value, dict) else {}
            save_settings(self.s)
            return
        self.s[key] = value
        if key == 'on_top' and self.window:
            try:
                self.window.on_top = bool(value)
            except Exception:
                pass
        save_settings(self.s)
        self.push()

    # --- save selection -------------------------------------------------------

    def list_saves(self):
        out = []
        for path in glob.glob(os.path.join(self.save_root, '*', 'slot_*', 'progress.sav')):
            try:
                mtime = os.path.getmtime(path)
            except OSError:
                continue
            out.append({
                'path': path,
                'slot': os.path.basename(os.path.dirname(path)),
                'profile': os.path.basename(os.path.dirname(os.path.dirname(path))),
                'mtime': mtime,
            })
        out.sort(key=lambda x: x['mtime'], reverse=True)
        return out

    def select_save(self, path):
        if not path:
            self.selected_save = None
            self.s['save_path'] = ''
            save_settings(self.s)
            self.save_path = self.save_mtime = None
            self.poll_once(force=True)
            self.push()
            return True
        path = os.path.abspath(path)
        root = os.path.abspath(self.save_root) + os.sep
        if not path.startswith(root) or not os.path.isfile(path):
            return False
        self.selected_save = path
        self.s['save_path'] = path
        save_settings(self.s)
        self.save_path = self.save_mtime = None
        self.poll_once(force=True)
        self.push()
        return True

    # --- save polling ---------------------------------------------------------

    def loop(self):
        while not self.closing:
            self.next_scan = time.time() + self.poll_s
            self.poll_once()
            while not self.closing and time.time() < self.next_scan:
                time.sleep(min(0.2, max(0.0, self.next_scan - time.time())))

    def poll_once(self, force=False):
        try:
            path = self.selected_save if self.selected_save and os.path.isfile(self.selected_save) else cc.newest_save(self.save_root)
            mtime = os.path.getmtime(path) if path else None
            if path and (force or path != self.save_path or mtime != self.save_mtime):
                self.checking = True
                self.push_status()
                started = time.monotonic()
                save = core.Save(path, self.catalog, os.path.join(DATA, 'cookdata.json'))
                # Read the whole dynamic payload once; this is what catches a
                # half-written save before we commit the new mtime.
                payload = self.build(save)
                self.save_path, self.save_mtime = path, mtime
                self.save = save
                self.error = None
                self.data_version += 1
                payload['data_version'] = self.data_version
                self.payload = payload
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
        except Exception as e:
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
                self.payload = self.empty_payload()
            self.payload['version'] = self.version
            self.payload['save'] = self.save_status()

    def push(self):
        with self.lock:
            self.version += 1
            if self.payload is not None:
                self.payload['version'] = self.version
                self.payload['save'] = self.save_status()

    # --- payload --------------------------------------------------------------

    def empty_payload(self):
        return {
            'version': self.version, 'data_version': self.data_version, 'save': self.save_status(),
            'status': None, 'inventory': [], 'completion': None, 'compendium': [],
            'cooking': {'dishes': [], 'materials': []}, 'travel_medallions': [],
            'settings': {k: v for k, v in self.s.items()}, 'platform': 'linux',
        }

    def build(self, save):
        inv = save.inventory()
        status = save.status()
        status['inventory_counts'] = {k: sum(1 for _ in inv.get(k, [])) for k in core.CATEGORY_ORDER}
        status['inventory_counts']['arrows'] = inv.get('arrows', [{}])[0].get('count', 0) if inv.get('arrows') else 0
        payload = {
            'version': self.version, 'data_version': self.data_version, 'save': self.save_status(),
            'status': status,
            'inventory': enrich_inventory(inv, self.catalog, self.cook),
            'completion': save.completion(),
            'compendium': save.compendium(),
            'cooking': build_cooking(inv, self.cook, self.catalog),
            'travel_medallions': save.travel_medallions(),
            'settings': {k: v for k, v in self.s.items()},
            'platform': 'linux',
        }
        return payload


def already_running():
    path = os.path.join(tempfile.gettempdir(), 'totk-companion.lock')
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
    for candidate in (os.path.join(HERE, '..', 'game'), os.path.expanduser('~/Games/TotK')):
        if os.path.isdir(os.path.join(candidate, 'profile', 'save')):
            return os.path.abspath(candidate)
    return os.path.abspath(os.path.join(HERE, '..', 'game'))


def main(argv=None):
    ap = argparse.ArgumentParser(description='TotK Companion, Linux save mode')
    ap.add_argument('--game', help='folder holding romfs and profile/save; default: ../game or ~/Games/TotK')
    ap.add_argument('--poll', type=float, default=POLL_S, help='seconds between save scans (default: 15)')
    ap.add_argument('--check', action='store_true', help='read the newest save, print a summary, and exit')
    args = ap.parse_args(argv)

    game = find_game(args.game)
    catalog_path = os.path.join(DATA, 'catalog.json')
    if not os.path.isfile(catalog_path):
        print('Missing %s.\nRun: python3 build_companion_data.py "%s"' % (catalog_path, game), file=sys.stderr)
        return 1
    if not os.path.isdir(os.path.join(game, 'profile', 'save')):
        print('Warning: no profile/save folder under %s' % game, file=sys.stderr)

    if args.check:
        app = App(game, args.poll)
        app.next_scan = time.time() + app.poll_s
        app.poll_once(force=True)
        p = app.build(app.save) if app.save else None
        if not p:
            print(json.dumps({'game': game, 'save': app.save_path, 'error': app.error}, ensure_ascii=False))
            return 1
        states = p['completion']['states'] if p['completion'] else []
        comp = {x: sum(1 for v in p['compendium'] if v['state'] == x) for x in ('Unopened', 'TakePhoto', 'Buy')}
        print(json.dumps({
            'game': game, 'save': app.save_path, 'slot': p['save']['slot'],
            'hearts': p['status']['hearts'], 'rupees': p['status']['rupees'],
            'position': p['status']['position'],
            'inventory': {k: len(v['items']) for k, v in
                          ((x['key'], x) for x in p['inventory'])},
            'completion': p['completion']['totals'],
            'compendium': comp,
            'dishes': len(p['cooking']['dishes']),
        }, ensure_ascii=False, indent=1))
        return 0

    if already_running():
        print('TotK Companion is already running.', file=sys.stderr)
        return 1
    App(game, args.poll).run()
    return 0


if __name__ == '__main__':
    sys.exit(main())
