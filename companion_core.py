"""Read a TotK save and turn it into the companion's dynamic payload.

The save is a flat hash table: murmur3(key name) -> either a scalar value or an
offset to an array/string/vector. Everything here is read-only. The only writes
the companion may make are to its own settings file.
"""
import json
import math
import os
import struct

import cook_core

HERE = os.path.dirname(os.path.abspath(__file__))
DATA = os.path.join(HERE, 'ui', 'companion_data')

# Enum values are murmur3 hashes of their names in the save format.
ENUM_NAMES = [
    'Hidden', 'Appear', 'Open', 'Enter', 'Clear', 'NotClear', 'Ready', 'Carry', 'Complete',
    'Unopened', 'TakePhoto', 'Buy', 'Ground', 'Sky', 'UnderGround', 'None', 'New', 'Update',
    'Blue', 'Red', 'Yellow', 'White', 'Black', 'Purple', 'Green', 'LightBlue', 'Navy',
    'Orange', 'Pink', 'Crimson', 'LightYellow', 'Brown', 'Gray',
]
# Food/effect enum names used by the save. Kept complete enough to decode every
# cooked dish in a normal save.
EFFECT_NAMES = [
    'None', 'ResistHot', 'ResistBurn', 'ResistCold', 'ResistElectric', 'ResitLightning',
    'ResistFreeze', 'ResistAncient', 'SwimSpeedUp', 'DecreaseSwimStamina', 'SpinAttack',
    'ClimbWaterfall', 'ClimbSpeedUp', 'ClimbSpeedUpOnlyHorizontaly', 'AttackUp', 'AttackUpCold',
    'AttackUpHot', 'AttackUpThunderstorm', 'AttackUpDark', 'AttackUpBone', 'QuietnessUp',
    'SandMoveUp', 'SnowMoveUp', 'WakeWind', 'TwiceJump', 'EmergencyAvoid', 'DefenseUp',
    'AllSpeed', 'MiasmaGuard', 'MaskBokoblin', 'MaskMoriblin', 'MaskLizalfos', 'MaskLynel',
    'YigaDisguise', 'StalDisguise', 'LifeRecover', 'LifeMaxUp', 'StaminaRecover',
    'ExStaminaMaxUp', 'LifeRepair', 'DivingMobilityUp', 'NotSlippy', 'Moisturizing',
    'LightEmission', 'RupeeGuard', 'FallResist', 'SwordBeamUp', 'VisualizeLife',
    'NightMoveSpeedUp', 'NightGlow', 'DecreaseWallJumpStamina', 'DecreaseChargeAttackStamina',
    'EmitTerror', 'NoBurning', 'NoFallDamage', 'NoSlip', 'RupeeGuardRate', 'MaskAll',
    'DecreaseZonauEnergy', 'ZonauEnergyHealUp', 'MaskHorablin', 'MiasmaDefenseUp',
    'ChargePowerUpCold', 'ChargePowerUpHot', 'ChargePowerUpThunderstorm', 'LightFootprint',
    'SoulPowerUpLightning', 'SoulPowerUpWater', 'SoulPowerUpWind', 'SoulPowerUpFire',
    'SoulPowerUpSpirit', 'EnableUseSwordBeam',
    'DurabilityUp', 'CriticalHit', 'LongThrow', 'QuickShot', 'ShieldGuardUp', 'SurfMaster',
    'GuardUp', 'SpeedUp',
]
ENUM_BY_HASH = {cook_core.murmur3(n): n for n in ENUM_NAMES + EFFECT_NAMES}
ENUM_BY_HASH[0] = 'None'

CATEGORY_LABELS = {
    'weapons': 'Weapons', 'bows': 'Bows', 'shields': 'Shields', 'armor': 'Armor',
    'materials': 'Materials', 'food': 'Food', 'zonai': 'Zonai devices',
    'keyitems': 'Key items', 'arrows': 'Arrows',
}
CATEGORY_ORDER = ['weapons', 'bows', 'shields', 'armor', 'materials', 'food', 'zonai', 'keyitems', 'arrows']
SLOT_ORDER = {'Head': 0, 'Upper': 1, 'Lower': 2}
SAGES = [
    ('Wind', 'Tulin'), ('Fire', 'Yunobo'), ('Water', 'Sidon'),
    ('Electric', 'Riju'), ('Soul', 'Mineru'),
]


def u32(b, off):
    return struct.unpack_from('<I', b, off)[0]


def i32(b, off):
    return struct.unpack_from('<i', b, off)[0]


def f32(b, off):
    return struct.unpack_from('<f', b, off)[0]


class Save:
    def __init__(self, path, catalog=None, cookdata_path=None):
        with open(path, 'rb') as f:
            self.b = f.read()
        self.path = path
        self.table = {}
        self.guid_offset = 0
        for i in range(0x28, len(self.b) - 8, 8):
            h, v = struct.unpack_from('<II', self.b, i)
            if h == 0xa3db7114:
                self.guid_offset = v
                break
            self.table.setdefault(h, v)
        self.guids = set()
        if self.guid_offset:
            for o in range(self.guid_offset, len(self.b) - 8, 8):
                g = struct.unpack_from('<Q', self.b, o)[0]
                if g == 0:
                    break
                self.guids.add(g)
        self.catalog = catalog or {}
        self.collectibles = self.catalog.get('collectibles', [])
        self.compendium_catalog = self.catalog.get('compendium', [])
        self.actors = self.catalog.get('actors', {})
        self.cookdata_path = cookdata_path or os.path.join(DATA, 'cookdata.json')
        self.cook = cook_core.Cook(self.cookdata_path)
        self._footprint = None
        self._footprint_mtime = None

    # --- raw access -----------------------------------------------------------

    def raw(self, name):
        return self.table.get(cook_core.murmur3(name))

    def u32(self, name):
        v = self.raw(name)
        return None if v is None else v

    def u32_hash(self, key_hash):
        return self.table.get(key_hash)

    def i32(self, name):
        v = self.raw(name)
        return None if v is None else struct.unpack('<i', struct.pack('<I', v))[0]

    def f32(self, name):
        v = self.raw(name)
        return None if v is None else struct.unpack('<f', struct.pack('<I', v))[0]

    def vec3(self, name):
        o = self.raw(name)
        if not o:
            return None
        return (f32(self.b, o), f32(self.b, o + 4), f32(self.b, o + 8))

    def vec3s(self, name):
        o, n = self._array(name)
        if o is None:
            return []
        return [(f32(self.b, o + i * 12), f32(self.b, o + i * 12 + 4),
                 f32(self.b, o + i * 12 + 8)) for i in range(n)]

    def string(self, name):
        o = self.raw(name)
        if not o:
            return None
        return self.b[o:o + 0x40].split(b'\0')[0].decode('utf-8', 'replace')

    def _array(self, name):
        o = self.raw(name)
        if not o:
            return None, 0
        n = u32(self.b, o)
        return o + 4, n

    def strings(self, name):
        o, n = self._array(name)
        if o is None:
            return []
        out = []
        for i in range(n):
            start = o + i * 0x40
            out.append(self.b[start:start + 0x40].split(b'\0')[0].decode('utf-8', 'replace'))
        return out

    def ints(self, name):
        o, n = self._array(name)
        if o is None:
            return []
        return list(struct.unpack_from('<%di' % n, self.b, o))

    def u32s(self, name):
        o, n = self._array(name)
        if o is None:
            return []
        return list(struct.unpack_from('<%dI' % n, self.b, o))

    def floats(self, name):
        o, n = self._array(name)
        if o is None:
            return []
        return list(struct.unpack_from('<%df' % n, self.b, o))

    def enum_name(self, value):
        if value is None:
            return None
        return ENUM_BY_HASH.get(value & 0xffffffff)

    # --- status ---------------------------------------------------------------

    def equipment(self):
        out = {}
        for key, cat in (('weapons', 'Weapon'), ('bows', 'Bow'), ('shields', 'Shield')):
            names = self.strings('Pouch.%s.Content.Name' % cat)
            idx = self.ints('Pouch.%s.EquipIndex' % cat)
            i = idx[0] if idx else -1
            out[key] = {'actor': names[i] if 0 <= i < len(names) else None, 'index': i}
        names = self.strings('Pouch.Armor.Content.Name')
        for slot, label in (('Head', 'armor_head'), ('Upper', 'armor_upper'), ('Bottom', 'armor_lower')):
            idx = self.ints('Pouch.Armor.EquipIndexes.%s' % slot)
            i = idx[0] if idx else -1
            out[label] = {'actor': names[i] if 0 <= i < len(names) else None, 'index': i}
        return out

    def status(self):
        max_life = self.i32('PlayerStatus.MaxLife') or 0
        life = self.i32('PlayerStatus.Life')
        if life is None:
            life = max_life
        pos = self.vec3('PlayerStatus.SavePos')
        sages = []
        for key, name in SAGES:
            base = 'PlayerStatus.Companion.%s.' % key
            sages.append({
                'key': key.lower(), 'name': name,
                'is_get': bool(self.i32(base + 'IsGet')),
                'is_summon': bool(self.i32(base + 'IsSummon')),
                'is_follow': bool(self.i32(base + 'IsFollowMode')),
            })
        abilities = [a for a in self.strings('Pouch.SpecialPower.Content.Name') if a]
        abilities = [{'actor': a, 'name': self.actors.get(a, {}).get('name') or a} for a in abilities]
        # MapData.CurrentLayer is the pause-map's last viewed layer, not Link's
        # physical layer. Use SavePos height so the marker follows Link.
        raw_layer = self.enum_name(self.u32('MapData.CurrentLayer')) or 'Ground'
        layer = raw_layer
        if pos:
            y = pos[1]
            if y < -100:
                layer = 'UnderGround'
            elif y > 1000:
                layer = 'Sky'
            else:
                layer = 'Ground'
        playtime = self.u32('Playtime')
        if playtime is None:
            # The game stores Playtime under a fixed hash that does not match
            # its display name in every save version.
            playtime = self.u32_hash(0xe573f564)
        path = self.hero_path()
        return {
            'hearts': {'current': life / 4.0, 'max': max_life / 4.0},
            'stamina': {'max': (self.f32('PlayerStatus.MaxStamina') or 0) / 1000.0},
            'energy': {'max': (self.f32('PlayerStatus.MaxEnergy') or 0) / 1000.0},
            'rupees': self.i32('PlayerStatus.CurrentRupee') or 0,
            'position': {'x': pos[0], 'y': pos[1], 'z': pos[2]} if pos else None,
            'layer': layer,
            'map_layer': raw_layer,
            'playtime': playtime,
            'deaths': path['deaths_count'] if path else None,
            'path_distance': path['distance'] if path else None,
            'path_points': path['points'] if path else None,
            'sages': sages,
            'abilities': abilities,
            'equipped': self.equipment(),
        }

    def travel_medallions(self):
        indexes = self.ints('MapData.IconData.WarpMarkerData.Index')
        positions = self.vec3s('MapData.IconData.WarpMarkerData.Pos')
        out = []
        for i, index in enumerate(indexes):
            if index is None or index < 0 or i >= len(positions):
                continue
            x, y, z = positions[i]
            out.append({'index': int(index), 'x': x, 'y': y, 'z': z})
        return out

    # --- Hero's Path ----------------------------------------------------------

    def footprint_path(self):
        if not self.path:
            return None
        path = os.path.join(os.path.dirname(self.path), 'footprint.sav')
        return path if os.path.isfile(path) else None

    def hero_path(self, step=6.0):
        """Read footprint.sav and return drawable Hero's Path segments.

        Each footprint is a packed 32-bit word: 13-bit X magnitude, 12-bit Z
        magnitude, sign bits, a two-bit layer, and warp/death flags. Points are
        quantized to four world units. Segments break on layer changes, warps,
        and deaths so the line never cuts across the map.
        """
        path = self.footprint_path()
        if not path:
            return None
        try:
            mtime = os.path.getmtime(path)
        except OSError:
            return None
        if self._footprint is not None and self._footprint_mtime == mtime:
            return self._footprint
        with open(path, 'rb') as f:
            raw = f.read()
        if len(raw) < 364 + 4:
            return None
        count = struct.unpack_from('<I', raw, 76)[0]
        count = min(count, (len(raw) - 364) // 4)
        limit = step * step
        segments = []
        deaths = []
        distance = 0.0
        total = 0
        layer = None
        points = None
        last = None
        for i in range(count):
            value = struct.unpack_from('<I', raw, 364 + i * 4)[0]
            x = (value >> 6) & 0x1fff
            if value & (1 << 5):
                x = -x
            z = (value >> 20) & 0xfff
            if not value & (1 << 19):
                z = -z
            point_layer = (value >> 3) & 3
            if point_layer == 3:
                continue
            warp = bool(value & 4)
            death = bool(value & 2)
            if death:
                deaths.append({'layer': point_layer, 'x': x, 'z': z})
            same_layer = points is not None and point_layer == layer
            if same_layer:
                dx = x - last[0]
                dz = z - last[1]
                if dx * dx + dz * dz >= limit:
                    distance += math.sqrt(dx * dx + dz * dz)
                    points.extend((x, z))
                    last = (x, z)
                    total += 1
            if warp or death:
                # The flag marks the point where the next recorded position
                # jumps, so close this segment here and start fresh after it.
                points = None
                last = None
                layer = None
                continue
            if not same_layer:
                points = [x, z]
                segments.append({'layer': point_layer, 'points': points})
                last = (x, z)
                layer = point_layer
                total += 1
        out = {
            'segments': segments,
            'deaths': deaths,
            'points': total,
            'deaths_count': len(deaths),
            'distance': distance,
        }
        self._footprint = out
        self._footprint_mtime = mtime
        return out

    # --- inventory ------------------------------------------------------------

    def _effect(self, cat, i):
        types = self.ints('Pouch.%s.Content.Effect.Type' % cat)
        values = self.ints('Pouch.%s.Content.Effect.Value' % cat)
        if not types or i >= len(types):
            return None, None
        return self.enum_name(types[i] & 0xffffffff), (values[i] if i < len(values) else None)

    def inventory(self):
        cats = {}
        # weapons, bows, shields
        for key, cat in (('weapons', 'Weapon'), ('bows', 'Bow'), ('shields', 'Shield')):
            names = self.strings('Pouch.%s.Content.Name' % cat)
            life = self.ints('Pouch.%s.Content.Life' % cat)
            extra = self.ints('Pouch.%s.Content.ExtraLife' % cat)
            combined = self.strings('Pouch.%s.Content.Combined.Name' % cat)
            combined_life = self.ints('Pouch.%s.Content.Combined.Life' % cat)
            eq = self.ints('Pouch.%s.EquipIndex' % cat)
            equipped = eq[0] if eq else -1
            items = []
            for i, actor in enumerate(names):
                if not actor:
                    continue
                effect, value = self._effect(cat, i)
                items.append({
                    'actor': actor, 'index': i, 'count': 1, 'equipped': i == equipped,
                    'life': life[i] if i < len(life) else None,
                    'extra': extra[i] if i < len(extra) else 0,
                    'effect': effect, 'effect_value': value,
                    'fused': combined[i] if i < len(combined) and combined[i] else None,
                    'fused_life': combined_life[i] if i < len(combined_life) else 0,
                })
            cats[key] = items
        # armor
        names = self.strings('Pouch.Armor.Content.Name')
        colors = self.u32s('Pouch.Armor.Content.ColorVariation')
        eq = {}
        for slot, key in (('Head', 'head'), ('Upper', 'upper'), ('Bottom', 'lower')):
            idx = self.ints('Pouch.Armor.EquipIndexes.%s' % slot)
            eq[key] = idx[0] if idx else -1
        armor = []
        for i, actor in enumerate(names):
            if not actor:
                continue
            armor.append({
                'actor': actor, 'index': i, 'count': 1,
                'color': self.enum_name(colors[i]) if i < len(colors) else None,
                'equipped': i in eq.values(),
            })
        cats['armor'] = armor
        # materials
        names = self.strings('Pouch.Material.Content.Name')
        stock = self.ints('Pouch.Material.Content.StockNum')
        mats = {}
        for i, actor in enumerate(names):
            if not actor:
                continue
            n = stock[i] if i < len(stock) else 1
            if n > 0:
                mats[actor] = mats.get(actor, 0) + n
        cats['materials'] = [{'actor': a, 'count': n} for a, n in mats.items()]
        # food
        names = self.strings('Pouch.Food.Content.Name')
        stock = self.ints('Pouch.Food.Content.StockNum')
        life = self.ints('Pouch.Food.Content.LifeRecover')
        levels = self.ints('Pouch.Food.Content.Effect.Level')
        times = self.ints('Pouch.Food.Content.Effect.Time')
        mat_names = self.strings('Pouch.Food.Content.MaterialName')
        food = {}
        for i, actor in enumerate(names):
            if not actor:
                continue
            n = stock[i] if i < len(stock) else 1
            if n <= 0:
                continue
            effect, _value = self._effect('Food', i)
            level = levels[i] if i < len(levels) else 0
            secs = times[i] if i < len(times) else 0
            heart = (life[i] if i < len(life) else 0) / 4.0
            ingredients = [m for m in mat_names[i * 5:i * 5 + 5] if m] if mat_names else []
            key = (actor, effect, level, secs, heart, tuple(ingredients))
            if key not in food:
                food[key] = {
                    'actor': actor, 'count': 0, 'effect': effect, 'level': level,
                    'seconds': secs, 'hearts': heart, 'ingredients': ingredients,
                    'indexes': [],
                }
            food[key]['count'] += n
            food[key]['indexes'].append(i)
        cats['food'] = list(food.values())
        # Zonai devices
        names = self.strings('Pouch.SpecialParts.Content.Name')
        stock = self.ints('Pouch.SpecialParts.Content.StockNum')
        zonai = {}
        for i, actor in enumerate(names):
            if not actor:
                continue
            n = stock[i] if i < len(stock) else 1
            if n > 0:
                zonai[actor] = zonai.get(actor, 0) + n
        cats['zonai'] = [{'actor': a, 'count': n} for a, n in zonai.items()]
        # key items
        names = self.strings('Pouch.KeyItem.Content.Name')
        stock = self.ints('Pouch.KeyItem.Content.StockNum')
        keys = {}
        for i, actor in enumerate(names):
            if not actor:
                continue
            n = stock[i] if i < len(stock) else 1
            keys[actor] = keys.get(actor, 0) + (n if n > 0 else 1)
        cats['keyitems'] = [{'actor': a, 'count': n} for a, n in keys.items()]
        # arrows
        arrow_names = self.strings('Pouch.Arrow.Content.Name')
        arrow_stock = self.ints('Pouch.Arrow.Content.StockNum')
        arrows = sum(n for i, name in enumerate(arrow_names)
                     if name and i < len(arrow_stock) and arrow_stock[i] > 0
                     for n in (arrow_stock[i],))
        arrow_actor = next((n for n in arrow_names if n), 'NormalArrow')
        cats['arrows'] = [{'actor': arrow_actor, 'count': arrows}] if arrows else []
        return cats

    # --- completion and compendium -------------------------------------------

    def completion(self):
        states = []
        for item in self.collectibles:
            state = 0
            if 'hash' in item:
                v = self.table.get(item['hash'])
                if v is not None:
                    name = self.enum_name(v)
                    if item['cat'] == 'shrines':
                        if name == 'Clear':
                            state = 2
                        elif name in ('Appear', 'Enter', 'Open'):
                            state = 1
                    elif item['cat'] == 'lightroots':
                        # Only an activated lightroot is useful here. Other
                        # status values still mean it is not open yet.
                        state = 2 if name == 'Open' else 0
                    elif item['cat'] == 'carry_koroks':
                        state = 2 if name == 'Clear' else 0
                    else:
                        state = 2 if v else 0
            elif 'guid' in item:
                try:
                    state = 2 if int(item['guid']) in self.guids else 0
                except (TypeError, ValueError):
                    state = 0
            states.append(state)
        cats = []
        for cat in self.catalog.get('collectible_categories', []):
            idx = [i for i, item in enumerate(self.collectibles) if item['cat'] == cat['key']]
            complete = sum(1 for i in idx if states[i] >= 2)
            started = sum(1 for i in idx if states[i] == 1)
            cats.append({**cat, 'complete': complete, 'started': started,
                         'found': complete + started, 'missing': cat['total'] - complete - started})
        return {
            'states': states,
            'categories': cats,
            'totals': {
                'complete': sum(c['complete'] for c in cats),
                'started': sum(c['started'] for c in cats),
                'total': sum(c['total'] for c in cats),
            },
        }

    def compendium(self):
        out = []
        for entry in self.compendium_catalog:
            actor = entry['actor']
            value = self.u32('PictureBookData.%s.State' % actor)
            state = self.enum_name(value) if value else 'Unopened'
            if not state:
                state = 'Unopened'
            out.append({
                'state': state,
                'new': bool(self.i32('PictureBookData.%s.IsNew' % actor)),
            })
        return out

    # --- cooking --------------------------------------------------------------

    def cooking(self):
        inv = {item['actor']: item['count'] for item in self.inventory()['materials']}
        rows = self.cook.what_can_i_cook(inv)
        return inv, rows


def load_catalog(path=None):
    path = path or os.path.join(DATA, 'catalog.json')
    with open(path, encoding='utf-8') as f:
        return json.load(f)
