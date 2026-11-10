"""Read the inventory from a TotK save and work out what it can cook.

Recipe matching follows KingFooZQ/Totk-Cooking-Simulator (MIT): the game walks the recipe table in order and takes the
first recipe whose ingredient slots are each filled by a different kind of ingredient in the pot. Single-ingredient
recipes apply only when the pot holds one kind of ingredient.
"""
import glob
import itertools
import json
import os
import struct

HERE = os.path.dirname(os.path.abspath(__file__))
SAVE_ROOT = os.path.join(HERE, '..', 'game', 'profile', 'save')

EFFECT_NAMES = {
    'None': '', 'ResistHot': 'Heat Resistance', 'ResistBurn': 'Flame Guard', 'ResistCold': 'Cold Resistance',
    'ResistElectric': 'Shock Resistance', 'SwimSpeedUp': 'Swim Speed Up', 'ClimbSpeedUp': 'Climb Speed Up',
    'AttackUp': 'Attack Up', 'AttackUpCold': 'Cold Weather Attack', 'AttackUpHot': 'Hot Weather Attack',
    'AttackUpThunderstorm': 'Stormy Weather Attack', 'QuietnessUp': 'Stealth Up', 'SandMoveUp': 'Sand Speed Up',
    'SnowMoveUp': 'Snow Speed Up', 'DefenseUp': 'Defense Up', 'AllSpeed': 'Speed Up', 'MiasmaGuard': 'Gloom Resistance',
    'LifeMaxUp': 'Extra Hearts', 'StaminaRecover': 'Stamina Recovery', 'ExStaminaMaxUp': 'Extra Stamina',
    'LifeRepair': 'Gloom Recovery', 'DivingMobilityUp': 'Skydive Mobility', 'NotSlippy': 'Slip Resistance',
    'LightEmission': 'Glow', 'LifeRecover': '',
}
PREFIX = {
    'LifeMaxUp': 'Hearty', 'StaminaRecover': 'Energizing', 'ExStaminaMaxUp': 'Enduring', 'AllSpeed': 'Hasty',
    'AttackUp': 'Mighty', 'DefenseUp': 'Tough', 'QuietnessUp': 'Sneaky', 'ResistCold': 'Spicy', 'ResistHot': 'Chilly',
    'ResistElectric': 'Electro', 'ResistBurn': 'Fireproof', 'LifeRepair': 'Sunny', 'LightEmission': 'Bright',
    'NotSlippy': 'Sticky',
}
SKIP_RESULTS ={'Item_Cook_O_01', 'Item_Cook_O_02'}  # Dubious Food, Rock-Hard Food
MAX_POT = 5
COMBO_CAP = 4000
TAG_LABELS = {
    'CookMeat': 'Any meat', 'CookFish': 'Any fish', 'CookMushroom': 'Any mushroom',
    'CookFruit': 'Any fruit', 'CookPlant': 'Any plant', 'CookSpice': 'Any spice',
    'CookInsect': 'Any critter', 'CookEnemy': 'Any monster part',
    'CookGolem': 'Any construct part', 'CookOre': 'Any ore',
    'CookForeign': 'Any fuse material',
}
# Potency thresholds used by the game for effects that have levels.
LEVEL_THRESHOLDS = {
    'ResistHot': [1, 6], 'ResistCold': [1, 6], 'ResistElectric': [1, 4, 6],
    'AllSpeed': [1, 5, 7], 'AttackUp': [1, 5, 7], 'QuietnessUp': [1, 6, 9],
    'ResistBurn': [1, 7], 'LightEmission': [1, 5, 7], 'NotSlippy': [1, 5, 7],
    'SwimSpeedUp': [1, 6, 9], 'AttackUpCold': [1, 6, 9], 'AttackUpHot': [1, 6, 9],
    'AttackUpThunderstorm': [1, 6, 9], 'MiasmaGuard': [1, 2, 3],
}


def murmur3(key, seed=0):
    data = key.encode()
    h = seed
    c1, c2 = 0xcc9e2d51, 0x1b873593
    n = len(data) // 4
    for i in range(n):
        k = struct.unpack_from('<I', data, i * 4)[0]
        k = (k * c1) & 0xffffffff
        k = ((k << 15) | (k >> 17)) & 0xffffffff
        k = (k * c2) & 0xffffffff
        h ^= k
        h = ((h << 13) | (h >> 19)) & 0xffffffff
        h = (h * 5 + 0xe6546b64) & 0xffffffff
    tail = data[n * 4:]
    if tail:
        k = 0
        for i, b in enumerate(tail):
            k |= b << (8 * i)
        k = (k * c1) & 0xffffffff
        k = ((k << 15) | (k >> 17)) & 0xffffffff
        k = (k * c2) & 0xffffffff
        h ^= k
    h ^= len(data)
    h ^= h >> 16
    h = (h * 0x85ebca6b) & 0xffffffff
    h ^= h >> 13
    h = (h * 0xc2b2ae35) & 0xffffffff
    h ^= h >> 16
    return h


def newest_save(root=SAVE_ROOT):
    saves = glob.glob(os.path.join(root, '*', 'slot_*', 'progress.sav'))
    return max(saves, key=os.path.getmtime) if saves else None


def read_inventory(path, with_size=False):
    """Return {actor name: count} from the save's material pouch (and the pouch array length if asked)."""
    with open(path, 'rb') as f:
        b = f.read()
    table = {}
    for i in range(0x28, len(b) - 8, 8):
        h, v = struct.unpack_from('<II', b, i)
        if h == 0xa3db7114:  # MetaData.SaveTypeHash ends the table
            break
        table.setdefault(h, v)

    def arr(name):
        off = table[murmur3(name)]
        return off, struct.unpack_from('<I', b, off)[0]

    off, n = arr('Pouch.Material.Content.Name')
    names = [b[off + 4 + i * 0x40:off + 4 + (i + 1) * 0x40].split(b'\0')[0].decode('utf-8', 'replace')
             for i in range(n)]
    off2, n2 = arr('Pouch.Material.Content.StockNum')
    nums = struct.unpack_from('<%di' % n2, b, off2 + 4)
    inv = {}
    for nm, q in zip(names, nums):
        if nm and q > 0:
            inv[nm] = inv.get(nm, 0) + q
    return (inv, n) if with_size else inv


class Cook:
    def __init__(self, data_path=os.path.join(HERE, 'cookdata.json')):
        d = json.load(open(data_path, encoding='utf-8'))
        self.mat = d['materials']
        self.recipes = d['recipes']
        self.dish_names = d['dish_names']
        self.sys = d['system']
        self.effects = d['effects']
        self._result_cache = {}

    def name(self, actor):
        m = self.mat.get(actor)
        return m['en'] if m else actor

    def _fits(self, target, actor):
        t, n = target
        if t == 'Actor':
            return n == actor
        return n in self.mat.get(actor, {}).get('tags', ())

    def _match(self, parts, kinds):
        """Can each recipe slot take a different ingredient kind? (small bipartite matching)"""
        if len(parts) > len(kinds):
            return False
        used = [None] * len(kinds)

        def assign(pi, seen):
            for ki, k in enumerate(kinds):
                if ki in seen or not any(self._fits(t, k) for t in parts[pi]):
                    continue
                seen.add(ki)
                if used[ki] is None or assign(used[ki], seen):
                    used[ki] = pi
                    return True
            return False

        return all(assign(pi, set()) for pi in range(len(parts)))

    def result_for(self, kinds):
        """The recipe the game picks for a pot holding these ingredient kinds."""
        key = tuple(kinds)
        if key in self._result_cache:
            return self._result_cache[key]
        single = len(kinds) == 1
        result = None
        for r in self.recipes:
            if r['single'] != single:
                continue
            if self._match(r['parts'], kinds):
                result = r
                break
        self._result_cache[key] = result
        return result

    def stats(self, pot, recipe):
        """Hearts and effect of a pot (list of actor names, repeats allowed). An estimate: no critical cooks."""
        mats = [self.mat.get(a, {}) for a in pot]
        hp = sum(m.get('hp', 0) for m in mats)
        effs = {m.get('effect') for m in mats if m.get('effect') not in (None, 'None')}
        effect = effs.pop() if len(effs) == 1 else None
        rate = self.sys.get('LifeRecoverRate', 2.0)
        hp = hp * rate + (recipe or {}).get('bonus', {}).get('Heart', 0)
        potency = sum(m.get('level', 0) for m in mats if m.get('effect') == effect) if effect else 0
        thresholds = LEVEL_THRESHOLDS.get(effect)
        if thresholds:
            level = sum(1 for t in thresholds if potency >= t)
        else:
            level = min(potency, int(self.effects.get(effect, {}).get('MaxLv', potency) or potency))
        secs = 0
        if effect:
            base = self.effects.get(effect, {}).get('BaseTime', 0)
            # Each ingredient adds its own EffectiveTime (frames at 30 per second); each one carrying the effect adds
            # the effect's base time on top. Same formula as KingFooZQ's simulator.
            secs = sum(m.get('time', 0) / 30 for m in mats) + base * sum(1 for m in mats if m.get('effect') == effect)
            secs += (recipe or {}).get('bonus', {}).get('Time', 0)
            if base == 0:
                secs = 0  # hearts, stamina and gloom effects have no duration
        extra = 0.0
        if effect == 'LifeMaxUp':  # hearty food: full recovery plus temporary hearts, a quarter heart per level
            extra = min(level, self.effects.get(effect, {}).get('MaxLv', level)) / 4.0
        return {'hearts': max(hp, 0) / 4.0, 'effect': effect, 'level': level, 'seconds': int(secs),
                'extra_hearts': extra, 'mixed_effects': len(effs) > 0}

    def display_name(self, row):
        base = row['name']
        pre = PREFIX.get(row['effect'] or '')
        return '%s %s' % (pre, base) if pre else base

    def fill_pot(self, kinds, inv):
        """Fill the pot to five with copies of the chosen kinds, best healing first, within stock."""
        pot = list(kinds)
        left = {k: inv[k] - 1 for k in kinds}
        order = sorted(kinds, key=lambda k: -self.mat.get(k, {}).get('hp', 0))
        for k in order:
            while len(pot) < MAX_POT and left[k] > 0:
                pot.append(k)
                left[k] -= 1
        return pot

    def part_label(self, part):
        labels = []
        for kind, value in part:
            if kind == 'Tag':
                labels.append(TAG_LABELS.get(value, value))
            else:
                labels.append(self.name(value))
        return ' or '.join(labels)

    def _part_candidates(self, part, effect):
        # Neutral ingredients are valid filler in any effect recipe. The
        # effect comes from at least one part, not every part.
        wanted = {None} if effect is None else {effect, None}
        out = []
        for kind, value in part:
            if kind == 'Actor':
                m = self.mat.get(value)
                mat_effect = m.get('effect') if m else None
                if mat_effect in (None, 'None'):
                    mat_effect = None
                if m and mat_effect in wanted:
                    out.append(value)
            else:
                for actor, m in self.mat.items():
                    mat_effect = m.get('effect')
                    if mat_effect in (None, 'None'):
                        mat_effect = None
                    if value in (m.get('tags') or []) and mat_effect in wanted:
                        out.append(actor)
        seen = set()
        unique = []
        for actor in out:
            if actor in seen:
                continue
            seen.add(actor)
            unique.append(actor)
        unique.sort(key=lambda a: (-(self.mat[a].get('level') or 0),
                                   -(self.mat[a].get('hp') or 0),
                                   self.name(a).lower()))
        return unique

    def _can_cook(self, parts, effect, inv):
        options = []
        for part in parts:
            opts = [a for a in self._part_candidates(part, effect) if inv.get(a, 0) > 0]
            if not opts:
                return False
            options.append(opts)
        options.sort(key=len)
        used = {}

        def place(i):
            if i >= len(options):
                return True
            for actor in options[i]:
                if used.get(actor, 0) >= inv.get(actor, 0):
                    continue
                used[actor] = used.get(actor, 0) + 1
                if place(i + 1):
                    return True
                used[actor] -= 1
            return False

        return place(0)

    def all_recipes(self, inv):
        """Every dish and effect variant the recipe table can produce.

        Each row uses one representative ingredient per recipe slot. Rows are
        keyed by dish and effect, so an ingredient change that only alters the
        effect still appears as its own recipe.
        """
        effects = [None]
        for effect in self.effects:
            if effect not in ('None', 'LifeRecover') and effect not in effects:
                effects.append(effect)
        best = {}
        for recipe in self.recipes:
            result = recipe['result']
            if result in SKIP_RESULTS:
                continue
            base = self.dish_names.get(result, result)
            for effect in effects:
                candidates = []
                ok = True
                for part in recipe['parts']:
                    cands = self._part_candidates(part, effect)
                    if not cands:
                        ok = False
                        break
                    candidates.append(cands)
                if not ok:
                    continue
                pot = [cands[0] for cands in candidates]
                stats = self.stats(pot, recipe)
                if (stats['effect'] or None) != effect:
                    continue
                key = result + '|' + (effect or 'None')
                score = (-len(recipe['parts']), stats['level'], stats['hearts'])
                row = {
                    'dish': result,
                    'name': self.display_name({'name': base, 'effect': effect}),
                    'effect': effect,
                    'level': stats['level'],
                    'hearts': stats['hearts'],
                    'extra': stats['extra_hearts'],
                    'seconds': stats['seconds'],
                    'mixed': False,
                    'pot': pot,
                    'size': len(recipe['parts']),
                    'req': [self.part_label(part) for part in recipe['parts']],
                    'missing': [self.part_label(part) for part in recipe['parts']
                                if not any(inv.get(a, 0) > 0
                                           for a in self._part_candidates(part, effect))],
                    'cookable': self._can_cook(recipe['parts'], effect, inv),
                }
                if key not in best or score > best[key][0]:
                    best[key] = (score, row)
        rows = [entry[1] for entry in best.values()]
        rows.sort(key=lambda x: (x['name'].lower(), x['effect'] or ''))
        return rows

    def what_can_i_cook(self, inv):
        """One row per dish: the smallest set of ingredient kinds that makes it, best by effect then hearts."""
        owned = [a for a in inv if a in self.mat and (self.mat[a]['tags'] or any(
            ('Actor', a) in [tuple(t) for p in r['parts'] for t in p] for r in self.recipes))]
        best = {}
        for r in self.recipes:
            res = r['result']
            if res in SKIP_RESULTS:
                continue
            cands = [[a for a in owned if any(self._fits(tuple(t), a) for t in part)] for part in r['parts']]
            if any(not c for c in cands):
                continue
            tried = 0
            for combo in itertools.product(*cands):
                if len(set(combo)) != len(combo):
                    continue
                tried += 1
                if tried > COMBO_CAP:
                    break
                kinds = sorted(set(combo))
                win = self.result_for(kinds)
                if not win or win['result'] != res:
                    continue
                pot = self.fill_pot(kinds, inv)
                st = self.stats(pot, win)
                score = (st['effect'] is not None, st['level'], st['hearts'])
                if res not in best or score > best[res]['score']:
                    best[res] = {'dish': res, 'name': self.dish_names.get(res, res), 'kinds': kinds, 'pot': pot,
                                 'score': score, **st}
        rows = sorted(best.values(), key=lambda x: (-x['hearts'], x['name']))
        return rows


def describe_pot(cook, pot):
    counts = {}
    for a in pot:
        counts[a] = counts.get(a, 0) + 1
    return ', '.join('%s x%d' % (cook.name(a), n) if n > 1 else cook.name(a) for a, n in counts.items())


if __name__ == '__main__':
    import sys
    path = sys.argv[1] if len(sys.argv) > 1 else newest_save()
    inv = read_inventory(path)
    c = Cook()
    print('Save:', path)
    print('Materials:', ', '.join('%s x%d' % (c.name(a), n) for a, n in inv.items()))
    for row in c.what_can_i_cook(inv):
        eff = EFFECT_NAMES.get(row['effect'] or 'None', row['effect'])
        hearts = 'full +%g' % row['extra_hearts'] if row['extra_hearts'] else '%g' % row['hearts']
        print('%-36s %-10s %-18s %s' % (c.display_name(row), hearts, eff, describe_pot(c, row['pot'])))
