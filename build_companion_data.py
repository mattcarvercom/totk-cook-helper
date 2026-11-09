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
import collections
import json
import os
import re
import shutil
import struct
import sys
import time

from PIL import Image, ImageChops, ImageDraw, ImageFilter, ImageOps

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

# Character-directory portraits for the five sages on the status page.
SAGE_ICON_SOURCES = {
    'wind': 'Npc_HighMountain001_Sage_Icon',
    'fire': 'Npc_Goron020_Sage_Icon',
    'water': 'Npc_ZoraB001_Sage_Icon',
    'electric': 'Npc_oasis003_Sage_Icon',
    'soul': 'Npc_RaumiGolem_Sage_Icon',
}

# The raw SeriesName values are internal labels. These are the set names used
# by the armor screen and the item names.
SET_DISPLAY_NAMES = {
    'Hylia': 'Hylian',
    'HyliaArmor': "Soldier's",
    'Korok': 'Of the Wild',
    'NightGlow': 'Radiant',
    'Zonanium': 'Zonaite',
    'NotSlippy': 'Froggy',
    'Diving': 'Glide',
    'ChemicalFire': 'Ember',
    'ChemicalIce': 'Frostbite',
    'ChemicalElectric': 'Charged',
    'UnderGround': 'Depths',
    'Climb': 'Climbing',
    'Power': 'Barbarian',
    'Sheikah': 'Stealth',
    'Goron': 'Flamebreaker',
    'Rito': 'Snowquill',
    'Gerudo': 'Desert Voe',
    'GerudoLady': 'Gerudo',
    'RoyalGuard': 'Royal Guard',
    'Kishin': 'Fierce Deity',
    'PhantomGanon': 'Evil Spirit',
    'Tingle': "Tingle's",
    'OcarinaOfTime': 'Of Time',
    'TwilightPrincess': 'Of Twilight',
    'SkywardSword': 'Of the Sky',
    'WindWaker': 'Of Wind',
    'AncientHeroSoul': 'Ancient Hero',
    'NewHero': "Champion's",
    'SheikMask': "Sheik's",
    'ThunderHelm': 'Lightning',
    'Fashonable': 'Cece',
    'Naked': 'Well-Worn',
    'None': 'Island Lobster',
    'MagicArmor': 'Mystic',
    'Zelda1': 'Hero',
    'LightEmission': "Miner's",
}

# Armor effect types without a row in StaticMsg/Buff.msbt. The names follow
# the effect wording used by the armor screen and the armor captions.
EFFECT_NAME_OVERRIDES = {
    'AttackUpBone': 'Attack Up (Bone)',
    'ClimbWaterfall': 'Waterfall Climbing',
    'ClimbSpeedUpOnlyHorizontaly': 'Climb Speed Up (Horizontal)',
    'EmitTerror': 'Terror',
    'EnableUseSwordBeam': 'Master Sword Beam Up',
    'MaskAll': 'Monster Disguise',
    'MaskBokoblin': 'Bokoblin Disguise',
    'MaskHorablin': 'Horriblin Disguise',
    'MaskLizalfos': 'Lizalfos Disguise',
    'MaskLynel': 'Lynel Disguise',
    'MaskMoriblin': 'Moblin Disguise',
    'Moisturizing': 'Moisturizing',
    'NightGlow': 'Glow',
    'SoulPowerUpFire': 'Sage of Fire Power Up',
    'SoulPowerUpLightning': 'Sage of Lightning Power Up',
    'SoulPowerUpSpirit': 'Sage of Spirit Power Up',
    'SoulPowerUpWater': 'Sage of Water Power Up',
    'SoulPowerUpWind': 'Sage of Wind Power Up',
    'SpinAttack': 'Spin Attack',
    'WakeWind': 'Wind Wake',
    'YigaDisguise': 'Yiga Disguise',
}

CATEGORIES = {
    'shrines': {'label': 'Shrines', 'color': '#7fd0ff', 'icon': 'shrine', 'kind': 'shrine'},
    'lightroots': {'label': 'Lightroots', 'color': '#c79bff', 'icon': 'lightroot', 'kind': 'lightroot'},
    'towers': {'label': 'Skyview Towers', 'color': '#e8c56a', 'icon': 'tower', 'kind': 'tower'},
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
    'shrines': 'Nt_MapDungeonNew_02',
    'lightroots': None,
    'towers': 'MapIconTower_00',
    'hidden_koroks': 'MapIconKorok_x2',
    'carry_koroks': 'MapIconKorok_x2',
    'bubbuls': 'MapIconCaveM_72x72',
    'locations': 'MapIconFrontierPoint_64x64',
    'caves': 'MapIconCaveM_72x72',
    'wells': 'MapIconCaveS_72x72',
    'chasms': 'MapIconCaveL_72x72',
    'hinoxes': 'MapIconSkull_72x72',
    'taluses': 'MapIconSkull_72x72',
    'moldugas': 'MapIconSkull_72x72',
    'flux_constructs': 'MapIconSkull_72x72',
    'froxes': 'MapIconSkull_72x72',
    'gleeoks': 'MapIconSkull_72x72',
    'old_maps': 'MapIconTreasureBox_72x72',
    'sages_wills': None,
    'addison_signposts': 'MapIconBuildingNewsPaper_58x58',
    'schema_stones': 'MapIconRelief_00',
    'yiga_schematics': 'MapIconShopEvil_58x58',
}
MAP_ICON_FRAMES = {'shrines': 'Nt_MapDungeonNewF_01'}
MAP_ICON_ITEM_SOURCES = {
    'bubbuls': 'CaveMasterMedal',
    'sages_wills': 'Obj_SageWill',
    'old_maps': 'Obj_TreasureMap_00',
    'schema_stones': 'Obj_AutoBuilderDraft_00',
    'yiga_schematics': 'Obj_AutoBuilderDraftAssassin_00',
}
MAP_ICON_COLORS = {
    'shrines': '#4fb8f0', 'hidden_koroks': '#e6c15a', 'carry_koroks': '#f0d77a',
    'lightroots': '#b98cff', 'sages_wills': '#f1e28a',
}

# Material sources keep a bounded number of points per material so the
# catalog stays small enough to load in the webview at startup.
MAX_SOURCE_POINTS = 400
# Enemy packs also contain sub-actors for weak points, bullets, and mounts.
# They are not independent spawns, so they would mislead a farming list.
SOURCE_SUB_ACTORS = (
    '_KeyCrystal', '_Wander', '_WeakPoint', '_Lower_', '_Upper_', '_Arm_',
    '_Attention', '_Bullet', '_Tornado', '_SpreadBullet', '_Thorns',
    '_Uncleared', '_Underground', '_Tear', '_Hair', '_SecretStone', '_Head',
    '_Ragdoll', '_Practice',
)
DRAGON_NOTES = {
    'Item_Enemy_38': 'Shoot Dinraal as it flies over Eldin and Death Mountain.',
    'Item_Enemy_39': 'Shoot Dinraal as it flies over Eldin and Death Mountain.',
    'Item_Enemy_47': 'Shoot Dinraal as it flies over Eldin and Death Mountain.',
    'Item_Enemy_211': 'Shoot Dinraal as it flies over Eldin and Death Mountain.',
    'Item_Enemy_228': 'Shoot Dinraal as it flies over Eldin and Death Mountain.',
    'Item_Enemy_49': 'Shoot Naydra as it flies around Mount Lanayru.',
    'Item_Enemy_50': 'Shoot Naydra as it flies around Mount Lanayru.',
    'Item_Enemy_51': 'Shoot Naydra as it flies around Mount Lanayru.',
    'Item_Enemy_212': 'Shoot Naydra as it flies around Mount Lanayru.',
    'Item_Enemy_229': 'Shoot Naydra as it flies around Mount Lanayru.',
    'Item_Enemy_53': 'Shoot Farosh as it flies over Faron and Lake Hylia.',
    'Item_Enemy_54': 'Shoot Farosh as it flies over Faron and Lake Hylia.',
    'Item_Enemy_55': 'Shoot Farosh as it flies over Faron and Lake Hylia.',
    'Item_Enemy_213': 'Shoot Farosh as it flies over Faron and Lake Hylia.',
    'Item_Enemy_230': 'Shoot Farosh as it flies over Faron and Lake Hylia.',
    'Item_Enemy_158': 'Shoot the Light Dragon as it circles the sky.',
    'Item_Enemy_159': 'Shoot the Light Dragon as it circles the sky.',
    'Item_Enemy_160': 'Shoot the Light Dragon as it circles the sky.',
    'Item_Enemy_214': 'Shoot the Light Dragon as it circles the sky.',
    'Item_Ore_J': 'Falls from the sky at night; it has no fixed spawn point.',
    'Item_Enemy_169': 'Dropped by Soldier Construct IV, a rare late-game construct.',
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
    """Pick the most complete all-terrain tile variant for one map cell.

    Sky cells can carry a second suffix pair (T_A_A, T_A_B, ...). The shorter
    T_A/T_B variants are foreground-only cutouts with an opaque brown backing;
    the doubled variants include the sky and cloud background. Prefer the
    doubled suffix, then the single suffix, then the plain variant.
    """
    for n in (4, 3, 2, 1):
        base = 'T' * n
        for suffix in (base + '_A_A', base + '_A_B', base + '_B_A', base + '_B_B',
                       base + '_A', base + '_B', base):
            if suffix in entries:
                return suffix
    return None


def point_in_ring(x, z, ring):
    inside = False
    n = len(ring)
    for i in range(n):
        x1, z1 = ring[i][0], ring[i][1]
        x2, z2 = ring[(i + 1) % n][0], ring[(i + 1) % n][1]
        if (z1 > z) != (z2 > z):
            if x < (x2 - x1) * (z - z1) / (z2 - z1) + x1:
                inside = not inside
    return inside


def region_bbox(region):
    xs = [p[0] for poly in region['polys'] for p in poly['outer']]
    zs = [p[1] for poly in region['polys'] for p in poly['outer']]
    return (min(xs), min(zs), max(xs), max(zs))


def region_contains(region, x, z):
    box = region.get('_bbox')
    if box and (x < box[0] or x > box[2] or z < box[1] or z > box[3]):
        return False
    for poly in region['polys']:
        if not point_in_ring(x, z, poly['outer']):
            continue
        if any(point_in_ring(x, z, hole) for hole in poly['holes']):
            continue
        return True
    return False


def region_for(regions, x, z):
    for region in regions:
        if region_contains(region, x, z):
            return region
    return None


def region_for_smallest(regions, x, z):
    hits = [region for region in regions if region_contains(region, x, z)]
    if not hits:
        return None
    return min(hits, key=lambda region: (region['_bbox'][2] - region['_bbox'][0]) *
                                          (region['_bbox'][3] - region['_bbox'][1]))


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


def composite_icon(base, frame, size=96):
    base = base.convert('RGBA').resize((size, size), Image.LANCZOS)
    if frame is None:
        return base
    frame = frame.convert('RGBA').resize((size, size), Image.LANCZOS)
    out = Image.new('RGBA', (size, size), (0, 0, 0, 0))
    out.alpha_composite(base)
    out.alpha_composite(frame)
    return out


def make_lightroot_icon(color, size=96):
    """Draw the Depths lightroot teardrop with the game's diamond gem."""
    mask = Image.new('L', (size, size), 0)
    d = ImageDraw.Draw(mask)
    d.ellipse((18, 8, 78, 64), fill=255)
    d.polygon([(18, 38), (78, 38), (48, 94)], fill=255)
    # Soft dark outline.
    outline = mask.filter(ImageFilter.MaxFilter(7))
    out = Image.new('RGBA', (size, size), (0, 0, 0, 0))
    dark = Image.new('RGBA', (size, size), (8, 8, 16, 190))
    out.paste(dark, (0, 0), outline)
    c = color.lstrip('#')
    rgb = (int(c[0:2], 16), int(c[2:4], 16), int(c[4:6], 16))
    grad = Image.new('RGBA', (size, size), (0, 0, 0, 0))
    for y in range(size):
        t = y / max(1, size - 1)
        col = (
            int(rgb[0] * (0.62 + 0.38 * (1 - t))),
            int(rgb[1] * (0.62 + 0.38 * (1 - t))),
            int(rgb[2] * (0.62 + 0.38 * (1 - t))),
            255,
        )
        ImageDraw.Draw(grad).line([(0, y), (size, y)], fill=col)
    out.paste(grad, (0, 0), mask)
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
        self.buff_text = self._msbt('StaticMsg/Buff.msbt')
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

    def _save_icon(self, key, source, size=ICON_SIZE, quality=88, fit=False,
                   centering=(0.5, 0.5), center_on_alpha=False):
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
            if fit:
                if center_on_alpha:
                    box = img.getchannel('A').getbbox()
                    if box:
                        centering = (((box[0] + box[2]) / 2) / img.width,
                                     ((box[1] + box[3]) / 2) / img.height)
                img = ImageOps.fit(img, (size, size), method=Image.LANCZOS,
                                   centering=centering)
            else:
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

    def extract_sage_icons(self):
        out = {}
        for key, name in SAGE_ICON_SOURCES.items():
            src = 'UI/Tex/CharaDirectory/%s.bntx.zs' % name
            icon = self._save_icon('sage_' + key, src, size=192, quality=90,
                                   fit=True, center_on_alpha=True)
            if icon:
                out[key] = icon
        self.catalog['sage_icons'] = out
        log('sage icons: %d exported' % len(out))

    # --- rsdb -----------------------------------------------------------------

    def load_rsdb(self):
        self.pouch = {row['__RowId']: row for row in
                      byml.Byml(self.rf.read(self.rf.find('RSDB/PouchActorInfo.', '.byml.zs'))).root}
        self.actor_info = {row['ActorName']: row for row in
                           byml.Byml(self.rf.read(self.rf.find('RSDB/ActorInfo.', '.byml.zs'))).root
                           if row.get('ActorName')}
        self.enhancement = {basename(row['__RowId']): row for row in
                            byml.Byml(self.rf.read(self.rf.find('RSDB/EnhancementMaterialInfo.', '.byml.zs'))).root}
        self.series_effects = {}
        series_path = ('GameParameter/SeriesArmorEffectParamList/'
                       'Default.game__equipment__SeriesArmorEffectParamList.bgyml')
        if series_path in self.rf.files:
            try:
                root = byml.Byml(self.rf.read(series_path)).root
                self.series_effects = {
                    row.get('SeriesName'): row.get('ArmorEffect', [])
                    for row in root.get('SeriesArmorEffectList', [])
                    if row.get('SeriesName')
                }
            except Exception:
                self.series_effects = {}

    # --- weapons and armor ----------------------------------------------------

    def effect_info(self, effects, set_bonus=False):
        """Turn raw ArmorEffect rows into display names and levels."""
        out = []
        for effect in effects or []:
            kind = effect.get('ArmorEffectType')
            if not kind:
                continue
            key = ('SetBonus_' + kind) if set_bonus else kind
            name = (self.buff_text.get(key) or self.buff_text.get(kind)
                    or EFFECT_NAME_OVERRIDES.get(kind)
                    or re.sub(r'(?<=[a-z])(?=[A-Z])', ' ', kind))
            level = int(effect.get('ArmorEffectLevel') or 0)
            out.append({'type': kind, 'name': name, 'level': level, 'set': bool(set_bonus)})
        return out

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
            set_name = (SET_DISPLAY_NAMES.get(row['series']) or row['series']
                        or self.name(base))
            row['base'] = base
            row['set_key'] = set_key
            row['set_name'] = set_name
            row['name'] = self.name(actor)
            row['caption'] = self.caption(actor)
            row['icon'] = self.icon_for(actor)
            row['rank'] = row['rank']
            row['defense_next'] = self.armor_raw.get(row['next'], {}).get('defense')
            row['effect_info'] = self.effect_info(row['effects'])
            row['set_bonus'] = self.effect_info(
                self.series_effects.get(row['series'], []), set_bonus=True)
            if set_key not in sets:
                sets[set_key] = {
                    'key': set_key, 'name': set_name, 'series': row['series'],
                    'bonus': row['set_bonus'],
                }
        # A one-piece "set" reads better under the piece name than under an
        # internal series label such as Ancient or NewHero.
        pieces_per_set = collections.defaultdict(set)
        for row in self.armor_raw.values():
            pieces_per_set[row['set_key']].add(row['base'])
        for row in self.armor_raw.values():
            if len(pieces_per_set[row['set_key']]) == 1:
                row['set_name'] = self.name(row['base'])
                if row['set_key'] in sets:
                    sets[row['set_key']]['name'] = row['set_name']
        catalog = []
        for actor, row in sorted(self.armor_raw.items(), key=lambda kv: (kv[1]['set_key'], SLOT_ORDER.get(kv[1]['slot'], 9), kv[1]['rank'])):
            catalog.append(row)
        self.catalog['armor'] = catalog
        self.catalog['armor_sets'] = sorted(sets.values(), key=lambda x: x['name'])

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
                if row.get('internal_name'):
                    item['internal'] = row['internal_name']
                if 'completion_hash' in row:
                    item['hash'] = int(row['completion_hash']) & 0xffffffff
                elif 'guid_hash' in row:
                    item['guid'] = str(row['guid_hash'])
                if row.get('path'):
                    item['path'] = row['path']
                items.append(item)
        self.catalog['collectible_categories'] = categories
        self.catalog['collectibles'] = items

    # --- map reveal regions ---------------------------------------------------

    def build_reveal_regions(self):
        """Store the game's surface tower and Depths reveal regions.

        Surface and Sky reveal by Skyview Tower region. The Depths map is a set
        of Field Map Area polygons, each assigned to the nearest Lightroot.
        Activating a Lightroot reveals its polygon group, so the reveal follows
        the map regions instead of a fixed radius. The UI draws the polygons
        directly, which keeps the catalog small and avoids per-region textures.
        """
        path = os.path.join(DATA, 'map_regions.json')
        if not os.path.isfile(path):
            log('reveal regions: data/map_regions.json missing')
            return
        data = json.load(open(path, encoding='utf-8'))
        towers = data.get('towers') or []
        depths = data.get('depths') or []
        for region in towers + depths:
            region['_bbox'] = region_bbox(region)

        lightroots = [it for it in self.catalog['collectibles']
                      if it['cat'] == 'lightroots' and it.get('internal')]

        def centroid(region):
            xs = [p[0] for poly in region['polys'] for p in poly['outer']]
            zs = [p[1] for poly in region['polys'] for p in poly['outer']]
            return sum(xs) / len(xs), sum(zs) / len(zs)

        owned = collections.defaultdict(list)
        for root in lightroots:
            region = region_for_smallest(depths, root['x'], root['z'])
            if region:
                owned[root['internal']].append(region)
        for root in lightroots:
            if owned.get(root['internal']):
                continue
            cx, cz = root['x'], root['z']
            region = min(depths, key=lambda r: (centroid(r)[0] - cx) ** 2 +
                                               (centroid(r)[1] - cz) ** 2)
            owned[root['internal']].append(region)
        covered = {id(region) for regions in owned.values() for region in regions}
        for region in depths:
            if id(region) in covered:
                continue
            cx, cz = centroid(region)
            root = min(lightroots, key=lambda it: (it['x'] - cx) ** 2 + (it['z'] - cz) ** 2)
            owned[root['internal']].append(region)

        region_owners = collections.defaultdict(list)
        for name, regions in owned.items():
            for region in regions:
                region_owners[region['area']].append(name)
        for region in depths:
            region['owners'] = region_owners.get(region['area'], [])

        self.catalog['map_regions'] = {'towers': towers, 'depths': depths}
        self.catalog.pop('reveal', None)
        for item in self.catalog['collectibles']:
            item.pop('regions', None)
            if item['cat'] == 'lightroots' and item.get('internal'):
                item['region'] = item['internal']
            elif item['layer'] == 'depths':
                item.pop('region', None)
                region = region_for_smallest(depths, item['x'], item['z'])
                if region:
                    item['regions'] = list(region.get('owners') or [])
            else:
                item.pop('region', None)
                if item['cat'] == 'towers' and item.get('internal'):
                    try:
                        item['tower'] = int(item['internal'][-2:])
                    except ValueError:
                        pass
                else:
                    region = region_for(towers, item['x'], item['z'])
                    if region:
                        item['tower'] = region['tower']
        for region in towers + depths:
            region.pop('_bbox', None)
        log('reveal regions: %d tower regions, %d Depths regions, %d Lightroot owners'
            % (len(towers), len(depths), len(owned)))

    # --- material sources -----------------------------------------------------

    def build_material_sources(self):
        """Index where every armor-upgrade material can be bought, dropped, or found.

        Shops come from the actor packs' ShopParam GoodsLists, drops from the
        enemy packs' DropTable resources and horn mapping tables, and world
        spawns from the Banc map placement files. The output is keyed by the
        item actor used in the armor upgrade rows.
        """
        actors = self.catalog.get('actors', {})
        wanted = collections.OrderedDict()
        for armor in self.catalog.get('armor', []):
            for up in armor.get('upgrade', []):
                actor = up.get('actor')
                if not actor:
                    continue
                row = wanted.setdefault(actor, {'used_in': set(), 'total': 0})
                row['used_in'].add(armor.get('base') or armor.get('actor'))
                row['total'] += int(up.get('n') or 0)
        if not wanted:
            self.catalog['material_sources'] = {}
            return

        def humanize(name):
            name = re.sub(r'^(?:Npc_|NPC_|Enemy_)', '', name)
            name = name.replace('_', ' ')
            name = re.sub(r'(?<=[a-z])(?=[A-Z])', ' ', name)
            return re.sub(r'\d+$', '', name).strip() or name

        def layer_for(path):
            if path.startswith('Banc/MinusField/'):
                return 'depths'
            if path.startswith('Banc/MainField/Sky/'):
                return 'sky'
            return 'surface'

        # Placements: cell actors, sky islands, cave interiors, and the Depths.
        place = collections.defaultdict(list)
        placement_re = re.compile(
            r'Banc/(?:MainField|MinusField)/[A-J]-\d+_(?:Static|Dynamic)\.bcett\.byml\.zs$')
        placement_files = [
            p for p in self.rf.files
            if placement_re.match(p) or
            ((p.startswith('Banc/MainField/Sky/') or p.startswith('Banc/MainField/Cave/'))
             and p.endswith('.bcett.byml.zs'))
        ]
        for path in placement_files:
            layer = layer_for(path)
            try:
                root = byml.Byml(self.rf.read(path)).root
            except Exception:
                continue
            for actor in root.get('Actors', []):
                name = actor.get('Gyaml')
                pos = actor.get('Translate')
                if not name or not pos or len(pos) < 3:
                    continue
                place[name].append((round(float(pos[0]), 1), round(float(pos[1]), 1),
                                    round(float(pos[2]), 1), layer))

        # Gear the rank-specific horn proxy: an enemy pack can carry several
        # mapping tables inherited from its templates, so pick the table whose
        # name shares the longest suffix with the enemy actor.
        def horn_items(pack, enemy):
            stem = enemy[len('Enemy_'):] if enemy.startswith('Enemy_') else enemy
            best = None
            best_len = -1
            for key in pack:
                if 'HornTypeAndAttachmentMappingTable' not in key:
                    continue
                name = key.split('/')[-1].split('.')[0]
                score = 0
                for i in range(1, min(len(stem), len(name)) + 1):
                    if stem[-i:] == name[-i:]:
                        score = i
                    else:
                        break
                if score > best_len:
                    best_len = score
                    best = pack[key]
            if best is None:
                return []
            try:
                root = byml.Byml(best).root
            except Exception:
                return []
            out = []
            for entry in root.get('HornTypeAndAttachmentMapping', []):
                item = entry.get('AttachmentName', '').split('/')[-1].split('.')[0]
                if item.startswith('Item_'):
                    out.append(item)
            return out

        # Shops: the 103 actor packs that expose a ShopParam.
        shops = {}
        sold = collections.defaultdict(list)
        for path in self.rf.files:
            if not (path.startswith('Pack/Actor/') and path.endswith('.pack.zs')):
                continue
            try:
                pack = sarc.read(self.rf.read(path))
            except Exception:
                continue
            if not any(k.startswith('Component/ShopParam/') for k in pack):
                continue
            actor = path.split('/')[-1][:-8]
            try:
                params = build_data.pack_param(
                    pack, 'Actor/%s.engine__actor__ActorParam.bgyml' % actor)
                shop = build_data.pack_param(pack, params.get('Components', {}).get('ShopRef'))
            except Exception:
                continue
            goods = []
            for entry in shop.get('GoodsList', []):
                item = entry.get('Actor', '').split('/')[-1]
                item = item.replace('.engine__actor__ActorParam.gyml', '')
                if item not in wanted:
                    continue
                base = int(actors.get(item, {}).get('buy') or 0)
                offset = int(entry.get('PriceOffset') or 0)
                goods.append((item, max(0, base + offset), int(entry.get('StockNum') or 0),
                              entry.get('Currency') or 'Rupee'))
            if goods:
                shops[actor] = goods

        locations = [x for x in self.catalog.get('collectibles', [])
                     if x.get('cat') == 'locations']
        stables = [x for x in locations if x.get('name', '').endswith('Stable')]

        def enemy_label(enemy):
            named = actors.get(enemy, {}).get('name')
            if named and not named.startswith('Enemy '):
                return named
            rank = ''
            if 'Middle' in enemy:
                rank = 'Blue '
            elif 'Senior' in enemy:
                rank = 'Black '
            elif 'Dark' in enemy:
                rank = 'Silver '
            families = (
                ('Bokoblin', 'Bokoblin'), ('Lizalfos', 'Lizalfos'),
                ('Moriblin', 'Moblin'), ('Horablin', 'Horriblin'),
                ('Giant', 'Hinox'), ('Golem', 'Talus'),
                ('CaveMaster', 'Frox'), ('Drake', 'Gleeok'),
                ('Sandworm', 'Molduga'),
            )
            for key, label in families:
                if key in enemy:
                    return rank + label
            return humanize(enemy)

        def nearest_place(x, z, layer):
            best = None
            best_d = None
            for loc in locations:
                if loc.get('layer') != layer:
                    continue
                dx = float(loc.get('x', 0)) - x
                dz = float(loc.get('z', 0)) - z
                d = dx * dx + dz * dz
                if best_d is None or d < best_d:
                    best_d = d
                    best = loc
            return best if best_d is not None and best_d <= 300 * 300 else None

        def shop_label(actor, x, z, layer):
            if actor.startswith('Npc_TripMaster') or actor == 'Npc_RoadShop_01':
                return 'Beedle'
            if 'DemonStatue' in actor or 'AmosStatue' in actor:
                return 'Demon Statue'
            if x is not None:
                near = nearest_place(x, z, layer)
                if near:
                    return near['name']
            if actor.startswith('Npc_RoadShop') or actor.startswith('Npc_Road_'):
                return 'Traveling merchant'
            return humanize(actor)

        for actor, goods in shops.items():
            positions = place.get(actor, [])
            if not positions and actor == 'Npc_RoadShop_01':
                positions = [(x['x'], x['y'], x['z'], x['layer']) for x in stables]
            for item, price, stock, currency in goods:
                seen = set()
                for x, y, z, layer in positions[:40]:
                    label = shop_label(actor, x, z, layer)
                    near = nearest_place(x, z, layer)
                    place_name = near['name'] if label == 'Beedle' and near else ''
                    key = (label, round(x), round(z))
                    if key in seen:
                        continue
                    seen.add(key)
                    sold[item].append({
                        'shop': label, 'place': place_name, 'actor': actor, 'price': price,
                        'stock': stock, 'currency': currency,
                        'x': x, 'y': y, 'z': z, 'layer': layer,
                    })
                if not positions:
                    sold[item].append({
                        'shop': shop_label(actor, None, None, None), 'place': '', 'actor': actor,
                        'price': price, 'stock': stock, 'currency': currency,
                        'x': None, 'y': None, 'z': None, 'layer': None,
                    })

        # Enemy drops: direct DropTable items plus the horn mapping tables.
        drops = collections.defaultdict(dict)
        for path in self.rf.files:
            if not (path.startswith('Pack/Actor/Enemy_') and path.endswith('.pack.zs')):
                continue
            enemy = path.split('/')[-1][:-8]
            if any(marker in enemy for marker in SOURCE_SUB_ACTORS):
                continue
            try:
                pack = sarc.read(self.rf.read(path))
                params = build_data.pack_param(
                    pack, 'Actor/%s.engine__actor__ActorParam.bgyml' % enemy)
                drop = build_data.pack_param(pack, params.get('Components', {}).get('DropRef'))
            except Exception:
                continue
            found = {}
            horn_proxy = False
            for table_ref in drop.get('DropTableResourceList', []):
                table_path = table_ref.replace('Work/', '', 1).replace('.gyml', '.bgyml')
                if table_path not in pack:
                    continue
                try:
                    table = byml.Byml(pack[table_path]).root
                except Exception:
                    continue
                for list_ref in table.get('DropTableElementResourceList', []):
                    list_path = list_ref.replace('Work/', '', 1).replace('.gyml', '.bgyml')
                    if list_path not in pack:
                        continue
                    try:
                        elements = byml.Byml(pack[list_path]).root
                    except Exception:
                        continue
                    for entry in elements.get('DropTableElement', []):
                        if entry.get('ProxyType') == 'HornMaterial':
                            horn_proxy = True
                        item = entry.get('DropActorName', '').split('/')[-1]
                        item = item.replace('.engine__actor__ActorParam.gyml', '')
                        if item in wanted:
                            found[item] = max(found.get(item, 0.0),
                                              float(entry.get('DropProbability') or 0))
            mapped_horns = horn_items(pack, enemy)
            for item in mapped_horns:
                if item in wanted:
                    found[item] = max(found.get(item, 0.0), 100.0)
            # The plain Bokoblin template has no mapping table; its rank-0
            # horn is the only one not declared in a table.
            if (horn_proxy and not mapped_horns and 'Bokoblin' in enemy
                    and 'Boss' not in enemy and 'Item_Enemy_77' in wanted):
                found.setdefault('Item_Enemy_77', 100.0)
            for item, chance in found.items():
                prev = drops[item].get(enemy)
                if prev is None or chance > prev:
                    drops[item][enemy] = chance

        # Direct world spawns, with live plants/fish/critters standing in for
        # the harvested item actor.
        aliases = {}
        for item in wanted:
            if item.startswith('Item_PlantGet_'):
                aliases[item] = 'Item_Plant_' + item[len('Item_PlantGet_'):]
            elif item.startswith('Item_FishGet_'):
                aliases[item] = 'Animal_Fish_' + item[len('Item_FishGet_'):]
            elif item.startswith('Item_InsectGet_'):
                aliases[item] = 'Animal_Insect_' + item[len('Item_InsectGet_'):]

        def point_list(points):
            rows = [[x, y, z, layer] for x, y, z, layer in points[:MAX_SOURCE_POINTS]]
            return rows, len(points)

        sources = {}
        for item, info in wanted.items():
            entry = {
                'name': actors.get(item, {}).get('name') or humanize(item),
                'icon': actors.get(item, {}).get('icon'),
                'used_in': sorted(info['used_in']),
                'need': info['total'],
                'sold': sold.get(item, []),
                'dropped': [],
                'found': [],
                'notes': [],
            }
            merged_drops = {}
            for enemy, chance in sorted(drops.get(item, {}).items()):
                points, total = point_list(place.get(enemy, []))
                label = enemy_label(enemy)
                row = merged_drops.get(label)
                if row is None:
                    merged_drops[label] = {
                        'enemy': label, 'actor': enemy, 'chance': chance,
                        'points': points, 'total': total,
                    }
                else:
                    row['chance'] = max(row['chance'], chance)
                    row['total'] += total
                    row['points'].extend(points)
            for row in merged_drops.values():
                if not row['total']:
                    continue
                row['points'] = row['points'][:MAX_SOURCE_POINTS]
                entry['dropped'].append(row)
            entry['dropped'].sort(key=lambda d: -d['total'])
            points = list(place.get(item, []))
            alias = aliases.get(item)
            if alias:
                points.extend(place.get(alias, []))
            if points:
                rows, total = point_list(points)
                entry['found'].append({'name': 'World spawn', 'points': rows, 'total': total})
            if item in DRAGON_NOTES:
                entry['notes'].append(DRAGON_NOTES[item])
            elif item.startswith('Item_Ore_'):
                entry['notes'].append('Also mined from ore deposits throughout Hyrule.')
            sources[item] = entry

        self.catalog['material_sources'] = sources
        coverage = sum(1 for e in sources.values()
                       if e['sold'] or e['dropped'] or e['found'] or e['notes'])
        log('material sources: %d/%d materials, %d shops, %d drop entries'
            % (coverage, len(sources), len(shops), sum(len(v) for v in drops.values())))

    # --- map ------------------------------------------------------------------

    def build_map(self):
        cell_px = MAP_LOD.get(self.lod, 300)
        os.makedirs(MAP, exist_ok=True)
        # G/S cells carry F/T terrain/fog suffixes; the Depths U cells are a
        # single texture per grid cell and use the same 12x10 layout.
        tile_re = re.compile(r'UI/Map/MainField/([GSU])_(\d+)-(\d+)_(\d+)(?:_([A-Za-z0-9_]+))?\.bntx\.zs$')
        cells = {'G': {}, 'S': {}, 'U': {}}
        for path in self.rf.files:
            m = tile_re.match(path)
            if not m:
                continue
            layer, x, y, z, suffix = m.groups()
            if int(z) != self.lod:
                continue
            cells[layer].setdefault((int(x), int(y)), {})[suffix or ''] = path
        cols, rows = 12, 10
        images = {}
        for layer, bg, label in (('G', (10, 15, 25), 'Surface'), ('S', (5, 8, 14), 'Sky'), ('U', (4, 6, 10), 'Depths')):
            canvas = Image.new('RGB', (cols * cell_px, rows * cell_px), bg)
            filled = 0
            for (x, y), entries in sorted(cells[layer].items()):
                suffix = pick_tile_suffix(entries) if layer != 'U' else ('' if '' in entries else None)
                if suffix is None:
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
            log('map %s: %d/%d cells filled' % (label, filled, cols * rows))
        surface = images['G']
        sky = images['S']
        depth = images['U'] if cells['U'] else ImageOps.colorize(ImageOps.grayscale(surface), black=(3, 6, 12), white=(32, 58, 68))
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
        states = {}

        def decode(source):
            off = textures.get(source)
            if off is None:
                log('map icons: missing texture', source)
                return None
            try:
                return build_icons.decode_bntx(bntx, off)
            except Exception as e:
                log('map icons: cannot decode %s: %s' % (source, e))
                return None

        def save_icon(name, img):
            if img is None:
                return None
            fname = name + '.webp'
            img.save(os.path.join(MAPICONS, fname), 'WEBP', quality=90, method=6)
            return 'mapicons/' + fname

        # Shrines use the blue diamond seen on the map, with the three game
        # states: orange, orange plus blue frame, and fully blue.
        shrine_fill = decode('Nt_MapDungeonNew_02')
        shrine_frame = decode('Nt_MapDungeonNewF_01')
        if shrine_fill is not None:
            def shrine_icon(fill, frame):
                return composite_icon(tint_icon(shrine_fill, fill),
                                      tint_icon(shrine_frame, frame) if shrine_frame is not None else None)
            states['shrines'] = {
                '0': save_icon('shrines_missing', shrine_icon('#e39a55', '#e39a55')),
                '1': save_icon('shrines_started', shrine_icon('#e39a55', '#58c8f5')),
                '2': save_icon('shrines_done', shrine_icon('#58c8f5', '#b8ecff')),
            }
            out['shrines'] = states['shrines']['2']

        # The lightroot is a teardrop with a diamond gem; the pause-map ring
        # texture is only the gem, so build the root silhouette around it.
        gem = decode('Nt_MapDungeonNewF_01')
        def lightroot(color):
            img = make_lightroot_icon(color)
            if gem is not None:
                g = tint_icon(gem, '#e2f5ff').resize((34, 34), Image.LANCZOS)
                img.alpha_composite(g, (31, 14))
            return img
        states['lightroots'] = {
            '0': save_icon('lightroots_missing', lightroot('#6d5a8c')),
            '2': save_icon('lightroots_done', lightroot('#b98cff')),
        }
        out['lightroots'] = states['lightroots']['2']

        for cat, source in MAP_ICON_SOURCES.items():
            if cat in ('shrines', 'lightroots'):
                continue
            color = MAP_ICON_COLORS.get(cat, CATEGORIES[cat]['color'])
            img = None
            if cat in MAP_ICON_ITEM_SOURCES:
                name = MAP_ICON_ITEM_SOURCES[cat]
                path = 'UI/Tex/Icon/%s.bntx.zs' % name
                if path in self.rf.files:
                    try:
                        img = build_icons.decode_bntx(self.rf.read(path))
                    except Exception as e:
                        log('map icons: cannot decode %s: %s' % (name, e))
                if img is None:
                    img = decode(source)
            else:
                img = decode(source)
                if img is not None:
                    img = tint_icon(img, color)
                    frame_src = MAP_ICON_FRAMES.get(cat)
                    if frame_src:
                        frame = decode(frame_src)
                        if frame is not None:
                            img = composite_icon(img, tint_icon(frame, '#d6f4ff'))
            if img is None:
                continue
            out[cat] = save_icon(cat, img)
        self.catalog['map_icons'] = out
        self.catalog['map_icon_states'] = states
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
        self.extract_sage_icons()
        self.build_collectibles()
        self.build_material_sources()
        if not self.skip_map:
            self.build_map()
            self.build_reveal_regions()
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
                'material_sources': len(self.catalog.get('material_sources', {})),
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
