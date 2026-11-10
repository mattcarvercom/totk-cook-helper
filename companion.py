"""TotK Companion, Linux save mode.

A read-only window over the newest Tears of the Kingdom save: status, inventory,
armor upgrades, the map, completion tracking, the compendium, and cooking. It
never writes to the save or the game. When the companion launches the game it
also reads the game's in-memory copy of the save, so position, facing, hearts,
inventory, and completion update while playing. If the game was started some
other way the companion falls back to save-file polling.

Run from the repository root:

    python3 companion.py --game /path/to/TotK
    python3 companion.py --game /path/to/TotK --launch-game
"""
import argparse
import fcntl
import glob
import json
import os
import re
import signal
import struct
import subprocess
import sys
import tempfile
import threading
import time

import cook_core as cc
import companion_core as core
import live_save

HERE = os.path.dirname(os.path.abspath(__file__))
SETTINGS = os.path.join(HERE, 'companion_settings.json')
DATA = os.path.join(HERE, 'ui', 'companion_data')
TITLE = 'TotK Companion'
LIVE_MARKER = os.path.join(os.environ.get('XDG_RUNTIME_DIR') or tempfile.gettempdir(),
                           'totk-companion.live')
POLL_S = 15.0
LIVE_POLL_S = 0.25
LIVE_SAVE_POLL_S = 2.0
MIN_POLL_S = 0.5
SPINNER_MIN_S = 0.35

DEFAULTS = {
    'on_top': True,
    'start_hidden': False,
    'tab': 'status',
    'save_path': '',
    'poll_s': POLL_S,
    'ui_state': {},
}

POUCH_BASE = {'weapons': 10, 'bows': 5, 'shields': 4}
POUCH_MAX = {'weapons': 20, 'bows': 14, 'shields': 20}
POUCH_COSTS = {
    'weapons': [1, 2, 3, 5, 8, 12, 17, 25, 35, 45],
    'bows': [1, 2, 3, 5, 8, 12, 17, 25, 35],
    'shields': [1, 2, 3, 4, 5, 10, 10, 10, 10, 10, 15, 15, 15, 15, 15, 20],
}
POUCH_OTHER = {'armor': 150, 'materials': 255, 'food': 60, 'zonai': 30, 'keyitems': 100}

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


def pretty_actor(actor):
    name = actor or ''
    for prefix in ('AbsObj_', 'AsbObj_', 'FldObj_', 'Obj_', 'Item_', 'SpObj_'):
        if name.startswith(prefix):
            name = name[len(prefix):]
    name = os.path.splitext(name)[0]
    return re.sub(r'(?<=[a-z0-9])(?=[A-Z])', ' ', name).replace('_', ' ')


# Fused rocks have no pouch icon in the game data. Use the Rock Salt item
# texture, which is the closest game asset to a plain boulder.
FUSE_NAME_ICONS = {
    'Rock': 'Item_Ore_H.webp',
    'Large Rock': 'Item_Ore_H.webp',
}


def fused_name(catalog, actor):
    entry = actor_entry(catalog, actor)
    if entry.get('name'):
        return entry['name']
    names = catalog.get('fuse_names') or {}
    for key in (actor, actor.replace('AbsObj_', 'AsbObj_', 1),
                actor.replace('AsbObj_', 'AbsObj_', 1)):
        if key in names:
            return names[key]
    return pretty_actor(actor)


def enrich_inventory(inv, catalog, cook, pouch_sizes=None):
    pouch_sizes = pouch_sizes or {}
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
                    it['fused_name'] = fused_name(catalog, raw['fused'])
                    it['fused_icon'] = fused.get('icon') or FUSE_NAME_ICONS.get(it['fused_name'])
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
        entry = {'key': key, 'label': core.CATEGORY_LABELS.get(key, key), 'items': items,
                 'used': len(items)}
        if key in POUCH_COSTS:
            entry['cap'] = int(pouch_sizes.get(key) or POUCH_MAX[key])
            entry['max'] = POUCH_MAX[key]
            bought = max(0, entry['cap'] - POUCH_BASE[key])
            costs = POUCH_COSTS[key]
            entry['next_cost'] = costs[bought] if bought < len(costs) else None
        elif key in POUCH_OTHER:
            entry['cap'] = POUCH_OTHER[key]
            entry['max'] = POUCH_OTHER[key]
            entry['next_cost'] = None
        out[key] = entry
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
            'level': r['level'], 'seconds': r['seconds'],
            'mixed': bool(r['mixed_effects'] and not r['effect']),
            'glyph': g, 'icon': icon, 'pot': pot, 'size': len(r['pot']),
        })
    dishes.sort(key=lambda x: (-(100 + x['extra'] if x['extra'] else x['hearts']), x['name'].lower()))
    return {'dishes': dishes, 'materials': mats}


def build_all_recipes(inv, cook, catalog):
    materials = {x['actor']: x['count'] for x in inv.get('materials', [])}
    out = []
    for row in cook.all_recipes(materials):
        pot = []
        for actor in row['pot']:
            m = cook.mat.get(actor, {})
            pot.append({'actor': actor, 'name': cook.name(actor), 'n': 1,
                        'glyph': glyph(m),
                        'icon': actor_entry(catalog, actor).get('icon'),
                        'effect': m.get('effect') or 'None'})
        out.append({
            'id': row['dish'] + '|' + (row['effect'] or 'None'),
            'name': row['name'], 'hearts': row['hearts'], 'extra': row['extra'],
            'effect': row['effect'] or '', 'effect_name': cc.EFFECT_NAMES.get(row['effect'] or 'None', ''),
            'seconds': row['seconds'], 'mixed': False, 'level': row['level'],
            'glyph': 'elixir' if 'Elixir' in row['name'] else (pot[0]['glyph'] if pot else 'pouch'),
            'icon': actor_entry(catalog, row['dish']).get('icon'), 'pot': pot, 'size': row['size'],
            'req': row['req'], 'missing': row['missing'], 'cookable': row['cookable'],
            'all': True,
        })
    return out


class Api:
    def __init__(self, app):
        self._app = app

    def bootstrap(self):
        return self._app.bootstrap

    def state(self, version):
        a = self._app
        return a.payload if a.payload and a.payload['version'] != version else None

    def hero_path(self):
        return self._app.hero_path()

    def all_recipes(self):
        return self._app.all_recipes()

    def set_setting(self, key, value):
        self._app.set_setting(key, value)

    def refresh(self):
        self._app.poll_once(force=True)
        self._app.push()

    def launch_game(self):
        return self._app.launch_game_now()

    def rebuild(self):
        return self._app.start_rebuild()

    def ack_rebuild(self):
        self._app.ack_rebuild()
        return True

    def saves(self):
        return self._app.list_saves()

    def select_save(self, path):
        return self._app.select_save(path)

    def hide(self):
        self._app.hide()

    def close(self):
        self._app.close()


class App:
    def __init__(self, game, poll_s=POLL_S, launch_game=False):
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
        self.caption_for = None
        self.caption_url = None
        self.caption_v = None
        self.error = None
        self.checking = False
        self._all_recipes = None
        self._all_recipes_for = None
        self.launch_game = bool(launch_game)
        self.game_proc = None
        self.live_pid = None
        self.live_state = None
        self.live_at = 0.0
        self.live_error = None
        self.live_active = False
        self.live_thread = None
        self.live_data_thread = None
        self.live_save = None
        self.live_save_error = None
        self.live_data_ok = False
        self.live_data_version = 0
        self._live_fingerprint = None
        self._cook_cache_key = None
        self._cook_cache = None
        self._cook_lock = threading.Lock()
        self._launch_requested = False
        try:
            signal.signal(signal.SIGUSR2, self._request_launch)
        except (ValueError, OSError):
            pass
        self.poll_s = max(MIN_POLL_S, float(self.s.get('poll_s') or poll_s))
        self.s['poll_s'] = self.poll_s
        self.rebuild_state = {'running': False, 'done': False, 'error': None,
                              'message': '', 'started': 0}
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
        if self.launch_game:
            self.start_game()
        self.poll_once(force=True)
        if self.payload is None:
            self.push()
        if self.s['start_hidden']:
            try:
                self.window.minimize()
            except Exception:
                pass
        threading.Thread(target=self.loop, daemon=True).start()
        if self.launch_game:
            self.start_live()

    # --- live memory ----------------------------------------------------------

    def start_game(self):
        """Start TotK as this process's child so live memory is readable."""
        if self.game_proc and self.game_proc.poll() is None:
            return True
        exe = os.path.join(self.game, 'totk')
        if not os.path.isfile(exe):
            self.live_error = 'totk was not found in the game folder'
            return False
        if live_save.find_pid(self.game):
            self.live_error = 'TotK is already running outside the companion'
            return False
        try:
            self.game_proc = subprocess.Popen(
                [exe], cwd=self.game, stdin=subprocess.DEVNULL,
                stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
                start_new_session=True)
            self.live_pid = self.game_proc.pid
            self.live_state = None
            self.live_active = False
            self.live_error = None
            return True
        except OSError as e:
            self.live_error = str(e)[:200]
            return False

    def _request_launch(self, signum=None, frame=None):
        self._launch_requested = True

    def launch_game_now(self):
        ok = self.start_game()
        if ok:
            self.launch_game = True
            self.start_live()
        self.push()
        return ok

    def start_live(self):
        if not (self.live_thread and self.live_thread.is_alive()):
            self.live_thread = threading.Thread(target=self.live_loop, daemon=True)
            self.live_thread.start()
        if not (self.live_data_thread and self.live_data_thread.is_alive()):
            self.live_data_thread = threading.Thread(target=self.live_data_loop, daemon=True)
            self.live_data_thread.start()

    def live_loop(self):
        while not self.closing:
            if self.live_pid is None:
                self.live_pid = live_save.find_pid(self.game)
            if not self.live_pid:
                self.live_active = False
                time.sleep(LIVE_POLL_S)
                continue
            try:
                anchor = None
                if self.live_state:
                    anchor = (self.live_state['x'], self.live_state['y'],
                              self.live_state['z'])
                else:
                    saved = (self.payload or {}).get('status') or {}
                    saved_pos = saved.get('position')
                    if saved_pos:
                        anchor = (saved_pos['x'], saved_pos['y'], saved_pos['z'])
                state = live_save.player_state(self.live_pid, anchor=anchor,
                                               max_distance=700)
            except live_save.Unavailable as e:
                self.live_active = False
                self.live_state = None
                self.live_error = 'start TotK from the companion for live memory'
                print('live: unavailable: %s' % e, file=sys.stderr, flush=True)
                return
            except (live_save.NotRunning, OSError) as e:
                self.live_active = False
                self.live_state = None
                self.live_pid = None
                self.live_error = 'the game exited'
                print('live: stopped: %s' % e, file=sys.stderr, flush=True)
                return
            if state:
                if not self.live_active:
                    layer = ('UnderGround' if state['y'] < -100
                             else 'Sky' if state['y'] > 1000 else 'Ground')
                    print('live: player at (%.0f, %.0f, %.0f), %s' %
                          (state['x'], state['y'], state['z'], layer),
                          file=sys.stderr, flush=True)
                self.live_state = state
                self.live_at = time.time()
                self.live_active = True
                self.live_error = None
                self.push_live(state)
            else:
                # The actor graph is unavailable (title screen, loading, or a
                # save loaded far away). Drop the stale anchor so the next read
                # starts from the save position again.
                self.live_state = None
                self.live_active = False
            time.sleep(LIVE_POLL_S)

    def live_data_loop(self):
        """Refresh hearts, inventory, completion and medallions from live memory."""
        delay = LIVE_SAVE_POLL_S
        while not self.closing:
            if self.live_pid:
                try:
                    self.refresh_live_save()
                except live_save.Unavailable:
                    self.live_save = None
                    self.live_data_ok = False
                    self.live_save_error = 'the live save buffer is not readable'
                    delay = 10.0
                except live_save.NotRunning:
                    self.live_save = None
                    self.live_data_ok = False
                    self.live_save_error = 'the game exited'
                    delay = 10.0
                except (live_save.NotReady, OSError) as e:
                    self.live_data_ok = False
                    self.live_save_error = str(e)[:120]
                    delay = 10.0
                else:
                    self.live_data_ok = True
                    self.live_save_error = None
                    delay = LIVE_SAVE_POLL_S
            else:
                delay = LIVE_SAVE_POLL_S
            time.sleep(delay)

    def live_fingerprint(self, payload):
        status = payload.get('status') or {}
        core_status = {k: status.get(k) for k in
                       ('hearts', 'stamina', 'energy', 'rupees', 'sages',
                        'abilities', 'equipped')}
        return json.dumps([core_status, payload.get('inventory'),
                           payload.get('completion'), payload.get('compendium'),
                           payload.get('cooking'), payload.get('travel_medallions')],
                          sort_keys=True, separators=(',', ':'))

    def refresh_live_save(self):
        if not self.live_pid:
            return
        if not self.live_save or self.live_save.pid != self.live_pid:
            self.live_save = live_save.LiveSave(
                self.game, pid=self.live_pid, save_root=self.save_root)
        data = self.live_save.read()
        # Use the selected save's footprint for Hero's Path; live progress
        # data comes from the game's in-memory buffer.
        path = self.save_path or self.live_save.save_path
        save = core.Save(path, self.catalog,
                         os.path.join(DATA, 'cookdata.json'), data=data)
        payload = self.build(save)
        state = self.live_state
        if state and payload.get('status'):
            y = state['y']
            payload['status']['position'] = {'x': state['x'], 'y': state['y'],
                                             'z': state['z']}
            payload['status']['heading'] = state['heading']
            payload['status']['layer'] = ('UnderGround' if y < -100
                                          else 'Sky' if y > 1000 else 'Ground')
        fingerprint = self.live_fingerprint(payload)
        if fingerprint == self._live_fingerprint:
            return
        self._live_fingerprint = fingerprint
        self.live_data_version += 1
        with self.lock:
            self.version += 1
            payload['version'] = self.version
            payload['data_version'] = self.data_version
            payload['live_data_version'] = self.live_data_version
            payload['save'] = self.save_status()
            self.payload = payload

    def push_live(self, state):
        with self.lock:
            if self.payload is None:
                return
            status = self.payload.get('status')
            if not status:
                return
            pos = {'x': state['x'], 'y': state['y'], 'z': state['z']}
            y = state['y']
            layer = 'UnderGround' if y < -100 else 'Sky' if y > 1000 else 'Ground'
            status['position'] = pos
            status['heading'] = state['heading']
            status['layer'] = layer
            self.payload['live'] = {'position': pos, 'heading': state['heading'],
                                    'layer': layer}
            self.payload['version'] += 1
            self.payload['save'] = self.save_status()

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
        clear_live_marker()
        save_settings(self.s)

    # --- settings -------------------------------------------------------------

    def set_setting(self, key, value):
        if key not in DEFAULTS:
            return
        if key == 'ui_state':
            self.s[key] = value if isinstance(value, dict) else {}
            save_settings(self.s)
            return
        if key == 'poll_s':
            try:
                value = max(MIN_POLL_S, min(300.0, float(value)))
            except (TypeError, ValueError):
                return
            self.poll_s = value
            self.next_scan = time.time() + value
        self.s[key] = value
        if key == 'on_top' and self.window:
            try:
                self.window.on_top = bool(value)
            except Exception:
                pass
        save_settings(self.s)
        self.push()

    # --- lazy data ------------------------------------------------------------

    def hero_path(self):
        return self.save.hero_path() if self.save else None

    def all_recipes(self):
        if not self.save:
            return []
        key = (self.save_path, self.data_version)
        if self._all_recipes is not None and self._all_recipes_for == key:
            return self._all_recipes
        inv = self.save.inventory()
        self._all_recipes = build_all_recipes(inv, self.cook, self.catalog)
        self._all_recipes_for = key
        return self._all_recipes

    def ack_rebuild(self):
        if not self.rebuild_state['running']:
            self.rebuild_state = {'running': False, 'done': False, 'error': None,
                                  'message': '', 'started': 0}
            self.push()

    def start_rebuild(self):
        if self.rebuild_state['running']:
            return False
        self.rebuild_state = {'running': True, 'done': False, 'error': None,
                              'message': 'Rebuilding data. This can take several minutes.',
                              'started': int(time.time())}
        self.push()
        threading.Thread(target=self._rebuild_job, daemon=True).start()
        return True

    def _rebuild_job(self):
        log_path = os.path.join(self.game, 'logs', 'companion-rebuild.log')
        try:
            os.makedirs(os.path.dirname(log_path), exist_ok=True)
            lod = str((self.catalog.get('meta') or {}).get('lod') or 1)
            cmd = [sys.executable, os.path.join(HERE, 'build_companion_data.py'),
                   self.game, '--lod', lod]
            proc = subprocess.run(cmd, cwd=HERE, capture_output=True, text=True)
            with open(log_path, 'w', encoding='utf-8') as f:
                f.write(proc.stdout or '')
                if proc.stderr:
                    f.write('\n' + proc.stderr)
            if proc.returncode != 0:
                tail = (proc.stderr or proc.stdout or '').strip().splitlines()[-3:]
                self.rebuild_state = {'running': False, 'done': False, 'error': 'Build failed.',
                                      'message': ' '.join(tail)[-400:], 'started': self.rebuild_state['started']}
                self.push()
                return
            self.catalog = core.load_catalog(os.path.join(DATA, 'catalog.json'))
            self.cook = cc.Cook(os.path.join(DATA, 'cookdata.json'))
            with self._cook_lock:
                self._cook_cache = None
                self._cook_cache_key = None
            self._live_fingerprint = None
            self._all_recipes = None
            self._all_recipes_for = None
            self.bootstrap['catalog'] = self.catalog
            if self.save:
                payload = self.build(self.save)
                self.data_version += 1
                payload['data_version'] = self.data_version
                self.payload = payload
            self.rebuild_state = {'running': False, 'done': True, 'error': None,
                                  'message': 'Data rebuilt.', 'started': self.rebuild_state['started']}
            self.push()
        except Exception as e:
            self.rebuild_state = {'running': False, 'done': False, 'error': e.__class__.__name__,
                                  'message': str(e)[:400], 'started': self.rebuild_state['started']}
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
            self.caption_for = None
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
        self.caption_for = None
        self.poll_once(force=True)
        self.push()
        return True

    # --- save polling ---------------------------------------------------------

    def loop(self):
        while not self.closing:
            if self._launch_requested:
                self._launch_requested = False
                self.launch_game_now()
            self.next_scan = time.time() + self.poll_s
            self.poll_once()
            while not self.closing and time.time() < self.next_scan:
                if self._launch_requested:
                    break
                time.sleep(min(0.2, max(0.0, self.next_scan - time.time())))

    def poll_once(self, force=False):
        try:
            path = self.selected_save if self.selected_save and os.path.isfile(self.selected_save) else cc.newest_save(self.save_root)
            mtime = os.path.getmtime(path) if path else None
            if path and (force or path != self.save_path or mtime != self.save_mtime):
                self.checking = True
                self.push_status()
                if self.live_active and self.live_data_ok:
                    # Live memory is authoritative. Keep the disk path and
                    # caption current for fallback, but do not overwrite the
                    # live payload with a save that may be many minutes old.
                    self.save_path, self.save_mtime = path, mtime
                    self.save = core.Save(path, self.catalog,
                                          os.path.join(DATA, 'cookdata.json'))
                    self.error = None
                    self.checking = False
                    self.push_status()
                    return
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
        caption = None
        caption_v = None
        if self.save_path:
            cap_path = os.path.join(os.path.dirname(self.save_path), 'caption.sav')
            try:
                cap_mtime = os.path.getmtime(cap_path)
            except OSError:
                cap_mtime = None
            key = (cap_path, cap_mtime)
            if key != self.caption_for:
                caption, caption_v = read_caption(self.save_path)
                self.caption_for = key
                self.caption_url = caption
                self.caption_v = caption_v
            else:
                caption, caption_v = self.caption_url, self.caption_v
        return {'slot': os.path.basename(os.path.dirname(self.save_path)) if self.save_path else None,
                'path': self.save_path, 'dir': os.path.dirname(self.save_path) if self.save_path else None,
                'caption': caption, 'caption_v': caption_v,
                'mtime': self.live_at if self.live_active else self.save_mtime,
                'error': self.error,
                'live': 'on' if self.live_active else 'off',
                'live_error': self.live_error,
                'checking': self.checking, 'next_scan': self.next_scan, 'poll_s': self.poll_s,
                'rebuild': dict(self.rebuild_state)}

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
            'version': self.version, 'data_version': self.data_version,
            'live_data_version': self.live_data_version, 'save': self.save_status(),
            'status': None, 'inventory': [], 'completion': None, 'compendium': [],
            'cooking': {'dishes': [], 'materials': []}, 'travel_medallions': [],
            'settings': {k: v for k, v in self.s.items()}, 'platform': 'linux',
        }

    def build(self, save):
        inv = save.inventory()
        status = save.status()
        status['inventory_counts'] = {k: sum(1 for _ in inv.get(k, [])) for k in core.CATEGORY_ORDER}
        status['inventory_counts']['arrows'] = inv.get('arrows', [{}])[0].get('count', 0) if inv.get('arrows') else 0
        # Cooking is expensive and only depends on ingredient counts. Keep the
        # last result until the pouch materials actually change.
        mat_key = tuple(sorted((x['actor'], x['count'])
                               for x in inv.get('materials', [])))
        with self._cook_lock:
            if self._cook_cache is None or mat_key != self._cook_cache_key:
                self._cook_cache = build_cooking(inv, self.cook, self.catalog)
                self._cook_cache_key = mat_key
            cooking = self._cook_cache
        payload = {
            'version': self.version, 'data_version': self.data_version,
            'live_data_version': self.live_data_version, 'save': self.save_status(),
            'status': status,
            'inventory': enrich_inventory(inv, self.catalog, self.cook, save.pouch_sizes()),
            'completion': save.completion(),
            'compendium': save.compendium(),
            'cooking': cooking,
            'travel_medallions': save.travel_medallions(),
            'settings': {k: v for k, v in self.s.items()},
            'platform': 'linux',
        }
        return payload


def read_caption(save_path):
    """Extract the save-menu screenshot from the sibling caption.sav."""
    cap_path = os.path.join(os.path.dirname(save_path), 'caption.sav')
    if not os.path.isfile(cap_path):
        return None, None
    try:
        data = open(cap_path, 'rb').read()
        jpg_offset = None
        for i in range(0x28, min(0x1c0, len(data) - 8) + 1, 8):
            h, value = struct.unpack_from('<II', data, i)
            if h == 0x63696a32:
                jpg_offset = value
                break
        if not jpg_offset:
            return None, None
        size = struct.unpack_from('<I', data, jpg_offset)[0]
        if size <= 0 or jpg_offset + 4 + size > len(data):
            return None, None
        jpg = data[jpg_offset + 4:jpg_offset + 4 + size]
        if not jpg.startswith(b'\xff\xd8'):
            return None, None
        stamp = int(os.path.getmtime(cap_path))
        fname = 'save-caption-%d.jpg' % stamp
        out = os.path.join(DATA, fname)
        tmp = out + '.tmp'
        with open(tmp, 'wb') as f:
            f.write(jpg)
        os.replace(tmp, out)
        return fname, stamp
    except (OSError, struct.error):
        return None, None


def write_live_marker():
    try:
        with open(LIVE_MARKER, 'w', encoding='ascii') as f:
            f.write(str(os.getpid()))
    except OSError:
        pass


def clear_live_marker():
    try:
        with open(LIVE_MARKER, encoding='ascii') as f:
            if f.read().strip() != str(os.getpid()):
                return
        os.remove(LIVE_MARKER)
    except OSError:
        pass


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
    ap.add_argument('--launch-game', action='store_true',
                    help='start TotK as a child process so live memory can be read')
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
            'position': p['status']['position'], 'playtime': p['status'].get('playtime'),
            'deaths': p['status'].get('deaths'), 'path_distance': p['status'].get('path_distance'),
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
    app = App(game, args.poll, launch_game=args.launch_game)
    write_live_marker()
    try:
        app.run()
    finally:
        clear_live_marker()
    return 0


if __name__ == '__main__':
    sys.exit(main())
