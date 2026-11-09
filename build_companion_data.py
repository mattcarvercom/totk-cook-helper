"""Build the TotK Companion's local data from the port's romfs.

Everything here comes from the user's own copy of the game: item and armor
metadata, icons, compendium pictures, and the surface/sky map tiles. The only
pre-computed input is data/collectibles.json (coordinates and completion
hashes), which is documented in data/NOTICE.md.

Run:

    python3 build_companion_data.py /path/to/TotK

The output goes to ui/companion_data/ and is gitignored.
"""
import argparse
import json
import os
import re
import shutil
import struct
import sys
import time

from PIL import Image, ImageChops, ImageOps

import build_data
import build_icons
import byml
import msbt
import sarc

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, 'ui', 'companion_data')
ICONS = os.path.join(OUT, 'icons')
MAP = os.path.join(OUT, 'map')
MAPICONS = os.path.join(OUT, 'mapicons')
DATA = os.path.join(HERE, 'data')

# Map tiles use ASTC 12x12 in addition to the formats the icon exporter knows.
for _fmt, _spec in {
    0x35: (10, 5, 16, 'astc'), 0x36: (10, 6, 16, 'astc'), 0x37: (10, 8, 16, 'astc'),
    0x38: (10, 10, 16, 'astc'), 0x39: (12, 10, 16, 'astc'), 0x3a: (12, 12, 16, 'astc'),
}.items():
    build_icons.FORMATS.setdefault(_fmt, _spec)

SLOTS = ('Head', 'Upper', 'Lower')
SLOT_ORDER = {'Head': 0, 'Upper': 1, 'Lower': 2}
SLOT_WORD = {'Head': 'Head', 'Upper': 'Body', 'Lower': 'Legs'}

CATEGORIES = {
    'shrines': {'label': 'Shrines', 'color': '#7fd0ff', 'icon': 'shrine', 'kind': 'shrine'},
    'lightroots': {'label': 'Lightroots', 'color': '#c79bff', 'icon': 'lightroot', 'kind': 'lightroot'},
    'hidden_koroks': {'label': 'Korok seeds', 'color': '#9ee06e', 'icon': 'korok', 'kind': 'korok'},
    'carry_koroks': {'label': 'Korok friends', 'color': '#c8e887', 'icon': 'korok', 'kind': 'korok'},
    'bubbuls': {'label': 'Bubbuls', 'color': '#f4a259', 'icon': 'bubbul', 'kind': 'bubbul'},
    'locations': {'label': 'Locations', 'color': '#e8dcc0', 'icon': 'location', 'kind': 'location'},
    'caves': {'label': 'Caves', 'color': '#d99a6c', 'icon': 'cave', 'kind': 'cave'},
    'wells': {'label': 'Wells', 'color': '#8fc6c8', 'icon': 'well', 'kind': 'well'},
    'chasms': {'label': 'Chasms', 'color': '#b47fd0', 'icon': 'chasm', 'kind': 'chasm'},
    'hinoxes': {'label': 'Hinoxes', 'color': '#e07a6a', 'icon': 'boss', 'kind': 'boss'},
    'taluses': {'label': 'Stone Taluses', 'color': '#c9a06a', 'icon': 'boss', 'kind': 'boss'},
    'moldugas': {'label': 'Moldugas', 'color': '#e0b26a', 'icon': 'boss', 'kind': 'boss'},
    'flux_constructs': {'label': 'Flux Constructs', 'color': '#9fb6d9', 'icon': 'boss', 'kind': 'boss'},
    'froxes': {'label': 'Froxes', 'color': '#9bd4a8', 'icon': 'boss', 'kind': 'boss'},
    'gleeoks': {'label': 'Gleeoks', 'color': '#e08a9c', 'icon': 'boss', 'kind': 'boss'},
    'old_maps': {'label': 'Old maps', 'color': '#d6c38a', 'icon': 'map', 'kind': 'treasure'},
    'sages_wills': {'label': "Sages' wills", 'color': '#a8d8ff', 'icon': 'will', 'kind': 'treasure'},
    'addison_signposts': {'label': 'Addison signs', 'color': '#e8c56a', 'icon': 'sign', 'kind': 'treasure'},
    'schema_stones': {'label': 'Schema stones', 'color': '#bfa8e0', 'icon': 'schema', 'kind': 'treasure'},
    'yiga_schematics': {'label': 'Yiga schematics', 'color': '#d98f8f', 'icon': 'yiga', 'kind': 'treasure'},
}

# Map marker textures from UI/LayoutArchive/Common.blarc, timg/__Combined.bntx.
# These are the game's own map icon shapes; each is tinted with its category color.
MAP_ICON_SOURCES = {
    'shrines': 'MapIconDungeon_L_Icon',
    'lightroots': 'Nt_MapChallengeIcon_00',
    'hidden_koroks': 'MapIconKorok_x2',
    'carry_koroks': 'MapIconKorok_x2',
    'bubbuls': 'MapIconCaveM_72x72',
    'locations': 'MapIconFrontierPoint_64x64',
    'caves': 'MapIconCaveM_72x72',
    'wells': 'MapIconCaveS_72x72',
    'chasms': 'MapIconCaveS_72x72',
    'hinoxes': 'MapIconSkull_72x72',
    'taluses': 'MapIconSkull_72x72',
    'moldugas': 'MapIconSkull_72x72',
    'flux_constructs': 'MapIconSkull_72x72',
    'froxes': 'MapIconSkull_72x72',
    'gleeoks': 'MapIconSkull_72x72',
    'old_maps': 'MapIconTreasureBox_72x72',
    'sages_wills': 'SageWillPouchIcon_00',
    'addison_signposts': 'MapIconBuildingNewsPaper_58x58',
    'schema_stones': 'MapIconRelief_00',
    'yiga_schematics': 'MapIconShopEvil_58x58',
}

LAYER_LABEL = {'surface': 'Surface', 'sky': 'Sky', 'depths': 'Depths'}
WORLD = {'x_min': -6000.0, 'x_max': 6000.0, 'z_min': -5000.0, 'z_max': 5000.0}
MAP_LOD = {0: 3000, 1: 840, 2: 300, 3: 135, 4: 27}
ICON_SIZE = 128
PB_ICON_SIZE = 112


def log(*a):
    print(*a, flush=True)


def basename(ref):
    if not ref:
        return None
    name = ref.replace('\\', '/').split('/')[-1]
    for suffix in ('.engine__actor__ActorParam.gyml', '.gyml', '.bgyml'):
        if name.endswith(suffix):
            name = name[:-len(suffix)]
            break
    return name


def prettify(name):
    if not name:
        return ''
    name = re.sub(r'^(Work/Actor/|Actor/)', '', name)
    name = re.sub(r'\.(engine__actor__ActorParam\.)?(gyml|bgyml)$', '', name)
    return name.replace('_', ' ')


def pick_tile_suffix(entries):
    """Pick the most complete all-terrain tile variant for one map cell."""
    for n in (4, 3, 2, 1):
        for suffix in ('T' * n + '_A', 'T' * n + '_B', 'T' * n):
            if suffix in entries:
                return suffix
    return None


def tint_icon(img, color):
    """Recolor a game map icon while keeping its black symbol readable.

    Two kinds of textures are used by the map UI:
    - a white rounded tile with a black symbol in the alpha-cut tile shape
    - a red/white shape on an opaque black background
    """
    rgba = img.convert('RGBA')
    alpha = rgba.getchannel('A')
    amin, amax = alpha.getextrema()
    c = color.lstrip('#')
    rgb = (int(c[0:2], 16), int(c[2:4], 16), int(c[4:6], 16))
    if amin < 250 and amax > 0:
        # Tile icon: keep the black symbol, color the white tile.
        gray = ImageOps.grayscale(rgba.convert('RGB'))
        color_layer = Image.new('RGB', img.size, rgb)
        shaded = ImageChops.multiply(color_layer, Image.merge('RGB', (gray, gray, gray)))
        out = Image.merge('RGBA', shaded.split() + (alpha,))
        return out
    # Silhouette icon: the shape is the bright part of an opaque black image.
    r, g, b = rgba.convert('RGB').split()
    mask = ImageChops.lighter(ImageChops.lighter(r, g), b)
    out = Image.new('RGBA', img.size, rgb + (0,))
    out.putalpha(mask)
    return out


class Builder:
    def __init__(self, game, lod=2, skip_map=False, skip_icons=False):
        self.game = os.path.abspath(os.path.expanduser(game))
        self.lod = lod
        self.skip_map = skip_map
        self.skip_icons = skip_icons
        self.rf = build_data.Romfs(self.game)
        self.usen = sarc.read(self.rf.read(self.rf.find('Mals/USen.Product.', '.sarc.zs')))
        self.pouch_text = self._msbt('ActorMsg/PouchContent.msbt')
        self.pb_text = self._msbt('ActorMsg/PictureBook.msbt')
        self.location_text = self._msbt('LocationMsg/Location.msbt')
        self.dungeon_text = self._msbt('LocationMsg/Dungeon.msbt')
        self.icons_have = {
            p[len('UI/Tex/Icon/'):-len('.bntx.zs')]: p
            for p in self.rf.files if p.startswith('UI/Tex/Icon/') and p.endswith('.bntx.zs')
        }
        self.pb_have = {
            p[len('UI/Tex/PictureBook/'):-len('.bntx.zs')]: p
            for p in self.rf.files if p.startswith('UI/Tex/PictureBook/') and p.endswith('.bntx.zs')
        }
        self.built_icons = {}
        self.icon_failures = []
        self.actors = {}
        self.weapon_stats = {}
        self.armor_raw = {}
        self.enhancement = {}
        self.catalog = {}
        self.counts = {}

    def _msbt(self, name):
        if name not in self.usen:
            return {}
        return msbt.read(self.usen[name])

    # --- text -----------------------------------------------------------------

    def name(self, actor):
        return (self.pouch_text.get(actor + '_Name') or self.pb_text.get(actor + '_Name')
                or prettify(actor))

    def caption(self, actor):
        return (self.pouch_text.get(actor + '_Caption') or self.pb_text.get(actor + '_Caption') or '')

    # --- icons ----------------------------------------------------------------

    def _save_icon(self, key, source, size=ICON_SIZE, quality=88):
        if key in self.built_icons:
            return self.built_icons[key]
        if source not in self.rf.files:
            self.built_icons[key] = None
            return None
        try:
            img = build_icons.decode_bntx(self.rf.read(source)).convert('RGBA')
        except Exception as e:
            self.icon_failures.append('%s: %s' % (source, e))
            self.built_icons[key] = None
            return None
        if img.width != size or img.height != size:
            img = img.resize((size, size), Image.LANCZOS)
        safe = re.sub(r'[^A-Za-z0-9_.-]+', '_', key)
        fname = safe + '.webp'
        os.makedirs(ICONS, exist_ok=True)
        img.save(os.path.join(ICONS, fname), 'WEBP', quality=quality, method=6)
        self.built_icons[key] = fname
        return fname

    def icon_for(self, actor, effect=None):
        names = []
        if actor.startswith('Item_Cook_') and effect:
            names.append('%s_%s' % (actor, effect))
        names.extend(build_icons.candidates(actor))
        for n in names:
            if n in self.icons_have:
                return self._save_icon(n, self.icons_have[n])
        return None

    def compendium_icon(self, actor):
        key = 'pb_' + actor
        src = self.pb_have.get(actor + '_Icon')
        if not src:
            return None
        return self._save_icon(key, src, size=PB_ICON_SIZE, quality=86)

    # --- rsdb -----------------------------------------------------------------

    def load_rsdb(self):
        self.pouch = {row['__RowId']: row for row in
                      byml.Byml(self.rf.read(self.rf.find('RSDB/PouchActorInfo.', '.byml.zs'))).root}
        self.actor_info = {row['ActorName']: row for row in
                           byml.Byml(self.rf.read(self.rf.find('RSDB/ActorInfo.', '.byml.zs'))).root
                           if row.get('ActorName')}
        self.enhancement = {basename(row['__RowId']): row for row in
                            byml.Byml(self.rf.read(self.rf.find('RSDB/EnhancementMaterialInfo.', '.byml.zs'))).root}

    # --- weapons and armor ----------------------------------------------------

    def _actor_pack(self, actor):
        path = 'Pack/Actor/%s.pack.zs' % actor
        if path not in self.rf.files:
            return None
        return sarc.read(self.rf.read(path))

    def collect_weapon_stats(self):
        for actor, row in self.pouch.items():
            cat = row.get('PouchCategory')
            if cat not in ('Weapon', 'Bow', 'Shield'):
                continue
            pack = self._actor_pack(actor)
            stats = {'max_life': 0, 'attack': 0, 'defense': 0}
            if pack:
                for k in pack:
                    if 'LifeParameters' in k and k.endswith('.bgyml'):
                        try:
                            stats['max_life'] = int(byml.Byml(pack[k]).root.get('MaxLife', 0))
                        except Exception:
                            pass
                        break
                try:
                    ap = build_data.pack_param(pack, 'Actor/%s.engine__actor__ActorParam.bgyml' % actor)
                    comps = ap.get('Components', {})
                    wr = build_data.pack_param(pack, comps.get('WeaponRef'))
                    stats['attack'] = int(wr.get('BaseAttack', 0) or 0)
                    stats['defense'] = int(wr.get('BaseDefense', wr.get('Defense', 0)) or 0)
                except Exception:
                    pass
            self.weapon_stats[actor] = stats

    def collect_armor(self):
        for actor, row in self.pouch.items():
            if row.get('PouchCategory') != 'Armor' or actor.endswith('_B'):
                continue
            pack = self._actor_pack(actor)
            if not pack:
                continue
            try:
                ap = build_data.pack_param(pack, 'Actor/%s.engine__actor__ActorParam.bgyml' % actor)
                comps = ap.get('Components', {})
                ar = build_data.pack_param(pack, comps.get('ArmorRef'))
            except Exception:
                continue
            slot = actor.rsplit('_', 1)[-1]
            if slot not in SLOTS:
                continue
            # Unused/debug armor actors have no localized name or caption.
            if self.name(actor).startswith('Armor ') and not self.caption(actor):
                continue
            up = self.enhancement.get(actor, {})
            items = []
            for item in up.get('Items', []):
                items.append({'actor': basename(item.get('Actor')), 'n': int(item.get('Number', 0))})
            self.armor_raw[actor] = {
                'actor': actor,
                'slot': slot,
                'rank': int(ar.get('Rank', 1) or 1),
                'defense': int(ar.get('BaseDefense', 0) or 0),
                'next': basename(ar.get('NextRankActor')),
                'series': ar.get('SeriesName', '') or '',
                'effects': ar.get('ArmorEffect', []) or [],
                'upgrade': items,
                'price': int(up.get('Price', 0) or 0),
                'upgradeable': bool(up),
            }

    def build_armor_catalog(self):
        prev = {}
        for actor, row in self.armor_raw.items():
            nxt = row['next']
            if nxt and nxt in self.armor_raw:
                prev[nxt] = actor

        def root(actor):
            seen = set()
            while actor in prev and actor not in seen:
                seen.add(actor)
                actor = prev[actor]
            return actor

        sets = {}
        for actor, row in sorted(self.armor_raw.items()):
            base = root(actor)
            set_key = base.rsplit('_', 1)[0]
            set_name = row['series'] or self.name(base)
            sets.setdefault(set_key, set_name)
            row['base'] = base
            row['set_key'] = set_key
            row['set_name'] = set_name
            row['name'] = self.name(actor)
            row['caption'] = self.caption(actor)
            row['icon'] = self.icon_for(actor)
            row['rank'] = row['rank']
            row['defense_next'] = self.armor_raw.get(row['next'], {}).get('defense')
        catalog = []
        for actor, row in sorted(self.armor_raw.items(), key=lambda kv: (kv[1]['set_key'], SLOT_ORDER.get(kv[1]['slot'], 9), kv[1]['rank'])):
            catalog.append(row)
        self.catalog['armor'] = catalog
        self.catalog['armor_sets'] = [{'key': k, 'name': v} for k, v in sorted(sets.items(), key=lambda kv: kv[1])]

    # --- compendium -----------------------------------------------------------

    def collect_compendium(self):
        actors = sorted(k[:-5] for k in self.pb_text if k.endswith('_Name'))
        out = []
        for actor in actors:
            prefix = actor.split('_', 1)[0]
            if prefix == 'Animal':
                group = 'Animals'
            elif prefix == 'Enemy':
                group = 'Monsters'
            elif prefix == 'Weapon' or prefix == 'Armor':
                group = 'Equipment'
            elif prefix == 'Item':
                group = 'Items'
            elif prefix == 'Object' or prefix == 'Obj':
                group = 'Objects'
            else:
                group = 'Other'
            out.append({
                'actor': actor,
                'name': self.pb_text.get(actor + '_Name') or prettify(actor),
                'caption': self.pb_text.get(actor + '_Caption') or '',
                'group': group,
                'icon': self.compendium_icon(actor),
            })
        self.catalog['compendium'] = out

    # --- actors ---------------------------------------------------------------

    def build_actors(self):
        wanted = set(self.pouch)
        cook = {}
        try:
            cook = json.load(open(os.path.join(HERE, 'cookdata.json'), encoding='utf-8'))
            wanted |= set(cook.get('materials', {}))
            wanted |= set(cook.get('dish_names', {}))
            wanted |= {r['result'] for r in cook.get('recipes', [])}
        except (OSError, ValueError):
            pass
        effects = list(cook.get('effects', {}))
        for actor in sorted(a for a in wanted if a.startswith('Item_Cook_')):
            for effect in effects:
                self.icon_for(actor, effect)
        for item in self.catalog.get('compendium', []):
            wanted.add(item['actor'])
        for actor in sorted(wanted):
            row = self.pouch.get(actor, {})
            cat = row.get('PouchCategory')
            ai = self.actor_info.get(actor, {})
            entry = {
                'actor': actor,
                'name': self.name(actor),
                'caption': self.caption(actor),
                'category': cat,
                'kind': ai.get('Category') or '',
                'icon': self.icon_for(actor),
                'buy': int(row.get('BuyingPrice', 0) or 0),
                'sell': int(row.get('SellingPrice', 0) or 0),
                'cure': row.get('CureEffectType') or 'None',
                'hearts': float(row.get('HitPointRecover', 0) or 0),
                'use': row.get('PouchUseType') or '',
                'stockable': bool(row.get('PouchStockable')),
            }
            if actor in self.weapon_stats:
                entry['weapon'] = self.weapon_stats[actor]
            if actor.startswith('Item_Cook_'):
                entry['effect_icons'] = {}
                for effect in effects:
                    fn = self.icon_for(actor, effect)
                    if fn:
                        entry['effect_icons'][effect] = fn
            self.actors[actor] = entry
        self.catalog['actors'] = self.actors

    # --- collectibles ---------------------------------------------------------

    def build_collectibles(self):
        src = json.load(open(os.path.join(DATA, 'collectibles.json'), encoding='utf-8'))
        items = []
        categories = []
        for key, rows in src.items():
            meta = CATEGORIES.get(key)
            if not meta:
                continue
            cat = {'key': key, 'label': meta['label'], 'color': meta['color'], 'icon': meta['icon'],
                   'kind': meta['kind'], 'total': len(rows)}
            categories.append(cat)
            for i, row in enumerate(rows):
                pos = row.get('position') or {}
                y = float(pos.get('y', 0) or 0)
                if key == 'lightroots':
                    layer = 'depths'
                elif key in ('wells', 'chasms'):
                    layer = 'surface'
                elif y < -100:
                    layer = 'depths'
                elif y > 900:
                    layer = 'sky'
                else:
                    layer = 'surface'
                name = row.get('display_name') or row.get('internal_name')
                if not name:
                    if key == 'hidden_koroks':
                        name = row.get('type') or 'Korok seed'
                    elif key == 'carry_koroks':
                        name = row.get('type') or 'Korok friend'
                    else:
                        name = '%s %d' % (meta['label'].rstrip('s'), i + 1)
                item = {
                    'id': '%s:%d' % (key, i),
                    'cat': key,
                    'name': name,
                    'x': float(pos.get('x', 0) or 0),
                    'y': y,
                    'z': float(pos.get('z', 0) or 0),
                    'layer': layer,
                    'kind': meta['kind'],
                }
                if 'completion_hash' in row:
                    item['hash'] = int(row['completion_hash']) & 0xffffffff
                elif 'guid_hash' in row:
                    item['guid'] = str(row['guid_hash'])
                if row.get('path'):
                    item['path'] = row['path']
                items.append(item)
        self.catalog['collectible_categories'] = categories
        self.catalog['collectibles'] = items

    # --- map ------------------------------------------------------------------

    def build_map(self):
        cell_px = MAP_LOD.get(self.lod, 300)
        os.makedirs(MAP, exist_ok=True)
        tile_re = re.compile(r'UI/Map/MainField/([GS])_(\d+)-(\d+)_(\d+)_(.+)\.bntx\.zs$')
        cells = {'G': {}, 'S': {}}
        for path in self.rf.files:
            m = tile_re.match(path)
            if not m:
                continue
            layer, x, y, z, suffix = m.groups()
            if int(z) != self.lod:
                continue
            cells[layer].setdefault((int(x), int(y)), {})[suffix] = path
        cols, rows = 12, 10
        images = {}
        for layer, bg in (('G', (10, 15, 25)), ('S', (5, 8, 14))):
            canvas = Image.new('RGB', (cols * cell_px, rows * cell_px), bg)
            filled = 0
            for (x, y), entries in sorted(cells[layer].items()):
                suffix = pick_tile_suffix(entries)
                if not suffix:
                    continue
                try:
                    img = build_icons.decode_bntx(self.rf.read(entries[suffix])).convert('RGB')
                except Exception as e:
                    self.icon_failures.append('%s: %s' % (entries[suffix], e))
                    continue
                if img.size != (cell_px, cell_px):
                    img = img.resize((cell_px, cell_px), Image.LANCZOS)
                canvas.paste(img, (x * cell_px, y * cell_px))
                filled += 1
            images[layer] = canvas
            log('map %s: %d/%d cells filled' % (LAYER_LABEL['sky' if layer == 'S' else 'surface'], filled, cols * rows))
        surface = images['G']
        sky = images['S']
        depth = ImageOps.colorize(ImageOps.grayscale(surface), black=(3, 6, 12), white=(32, 58, 68))
        surface.save(os.path.join(MAP, 'surface.webp'), 'WEBP', quality=88, method=6)
        sky.save(os.path.join(MAP, 'sky.webp'), 'WEBP', quality=88, method=6)
        depth.save(os.path.join(MAP, 'depths.webp'), 'WEBP', quality=86, method=6)
        meta = {
            'width': surface.width, 'height': surface.height,
            'cols': cols, 'rows': rows, 'cell': cell_px,
            'world': WORLD, 'lod': self.lod,
            'layers': {
                'surface': {'label': 'Surface', 'image': 'map/surface.webp'},
                'sky': {'label': 'Sky', 'image': 'map/sky.webp'},
                'depths': {'label': 'Depths', 'image': 'map/depths.webp'},
            },
        }
        self.catalog['map'] = meta
        json.dump(meta, open(os.path.join(MAP, 'map.json'), 'w', encoding='utf-8'), indent=1)

    # --- map markers ----------------------------------------------------------

    def extract_map_icons(self):
        """Export the game's own map-marker textures from the Common UI archive."""
        path = self.rf.find('UI/LayoutArchive/Common.', '.blarc.zs')
        if not path:
            log('map icons: Common UI archive not found')
            return
        try:
            archive = sarc.read(self.rf.read(path))
            bntx = archive['timg/__Combined.bntx']
        except Exception as e:
            log('map icons: cannot read texture archive:', e)
            return
        textures = {}
        for match in re.finditer(b'BRTI', bntx):
            off = match.start()
            ptr = struct.unpack_from('<Q', bntx, off + 0x60)[0]
            raw = bntx[ptr:ptr + 300]
            if len(raw) < 2:
                continue
            n = struct.unpack_from('<H', raw, 0)[0]
            if 0 < n < 250:
                name = raw[2:2 + n].split(b'\0')[0].decode('latin1', 'ignore')
            else:
                name = raw.split(b'\0')[0].decode('latin1', 'ignore')
            textures[name.split('^')[0]] = off
        os.makedirs(MAPICONS, exist_ok=True)
        out = {}
        for cat, source in MAP_ICON_SOURCES.items():
            off = textures.get(source)
            if off is None:
                log('map icons: missing texture', source)
                continue
            try:
                img = build_icons.decode_bntx(bntx, off)
            except Exception as e:
                log('map icons: cannot decode %s: %s' % (source, e))
                continue
            img = tint_icon(img, CATEGORIES[cat]['color'])
            fname = cat + '.webp'
            img.save(os.path.join(MAPICONS, fname), 'WEBP', quality=90, method=6)
            out[cat] = 'mapicons/' + fname
        self.catalog['map_icons'] = out
        log('map icons: %d exported' % len(out))

    # --- run ------------------------------------------------------------------

    def run(self):
        os.makedirs(OUT, exist_ok=True)
        os.makedirs(ICONS, exist_ok=True)
        self.load_rsdb()
        if not os.path.isfile(os.path.join(HERE, 'cookdata.json')):
            log('building cookdata.json ...')
            build_data.GAME = self.game
            build_data.main()
        self.collect_weapon_stats()
        self.collect_armor()
        self.build_armor_catalog()
        self.collect_compendium()
        self.build_actors()
        self.build_collectibles()
        if not self.skip_map:
            self.build_map()
        self.extract_map_icons()
        # Copy the cooking data so the UI has a single self-contained folder.
        try:
            shutil.copyfile(os.path.join(HERE, 'cookdata.json'), os.path.join(OUT, 'cookdata.json'))
        except OSError:
            pass
        self.catalog['meta'] = {
            'game': self.game,
            'built': int(time.time()),
            'lod': self.lod,
            'counts': {
                'actors': len(self.catalog.get('actors', {})),
                'armor': len(self.catalog.get('armor', [])),
                'compendium': len(self.catalog.get('compendium', [])),
                'collectibles': len(self.catalog.get('collectibles', [])),
                'icons': len([v for v in self.built_icons.values() if v]),
                'map_icons': len(self.catalog.get('map_icons', {})),
            },
        }
        json.dump(self.catalog, open(os.path.join(OUT, 'catalog.json'), 'w', encoding='utf-8'),
                  ensure_ascii=False, separators=(',', ':'))
        log('wrote %s' % os.path.join(OUT, 'catalog.json'))
        log('counts', json.dumps(self.catalog['meta']['counts']))
        if self.icon_failures:
            log('%d icon failures (first 10):' % len(self.icon_failures))
            for f in self.icon_failures[:10]:
                log(' ', f)
        return 0


def main(argv=None):
    ap = argparse.ArgumentParser(description='Build TotK Companion data from the game romfs')
    ap.add_argument('game', nargs='?', default=os.path.join(HERE, '..', 'game'))
    ap.add_argument('--lod', type=int, default=1, choices=sorted(MAP_LOD), help='map detail level (default 1)')
    ap.add_argument('--skip-map', action='store_true', help='skip map tile assembly')
    ap.add_argument('--skip-icons', action='store_true', help='accepted for symmetry; icons are built with the catalog')
    args = ap.parse_args(argv)
    game = os.path.abspath(os.path.expanduser(args.game))
    if not os.path.isdir(os.path.join(game, 'romfs')):
        print('romfs not found under %s' % game, file=sys.stderr)
        return 2
    return Builder(game, args.lod, args.skip_map, args.skip_icons).run()


if __name__ == '__main__':
    sys.exit(main())
