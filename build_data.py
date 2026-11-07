"""Build cookdata.json from the port's romfs: recipes, ingredient tags, cure values and English names.

Run again after a game update changes the romfs:  py -3 build_data.py [game folder]
"""
import json
import os
import sys

from backports import zstd

import byml
import msbt
import sarc

HERE = os.path.dirname(os.path.abspath(__file__))
GAME = sys.argv[1] if len(sys.argv) > 1 else os.path.join(HERE, '..', 'game')


class Romfs:
    def __init__(self, game):
        idx = json.load(open(os.path.join(game, 'romfs', 'index.json'), encoding='utf-8'))
        self.files = {f['path']: f for f in idx['files']}
        self.bin = open(os.path.join(game, 'romfs', 'romfs.bin'), 'rb')
        dics = sarc.read(zstd.decompress(self.raw('Pack/ZsDic.pack.zs')))
        self.dicts = {k: zstd.ZstdDict(v) for k, v in dics.items()}

    def find(self, prefix, suffix):
        hits = [p for p in self.files if p.startswith(prefix) and p.endswith(suffix)]
        return sorted(hits)[-1] if hits else None

    def raw(self, path):
        f = self.files[path]
        self.bin.seek(f['offset'])
        return self.bin.read(f['size'])

    def read(self, path):
        data = self.raw(path)
        if not path.endswith('.zs'):
            return data
        try:
            return zstd.decompress(data)
        except zstd.ZstdError:
            pass
        for name in ('pack.zsdic', 'zs.zsdic', 'bcett.byml.zsdic'):
            try:
                return zstd.decompress(data, zstd_dict=self.dicts[name])
            except zstd.ZstdError:
                continue
        raise ValueError('cannot decompress ' + path)


def load_tags(rf):
    path = rf.find('RSDB/Tag.Product.', '.rstbl.byml.zs')
    t = byml.Byml(rf.read(path)).root
    tags = t['TagList']
    bits = t['BitTable']
    pl = t['PathList']
    ntag = len(tags)
    out = {}
    for i in range(len(pl) // 3):
        name = pl[3 * i + 1]
        mine = []
        for j, tag in enumerate(tags):
            b = i * ntag + j
            if bits[b >> 3] >> (b & 7) & 1:
                mine.append(tag)
        if mine:
            out[name] = mine
    return out


def pack_param(pack, ref):
    """Read a '?Path.bgyml' ref from a pack, merging its $parent chain."""
    if not ref:
        return {}
    path = ref.lstrip('?')
    if path not in pack:
        return {}
    node = byml.Byml(pack[path]).root
    parent = node.get('$parent')
    base = {}
    if parent:
        pp = parent.replace('Work/', '', 1).replace('.gyml', '.bgyml')
        base = pack_param(pack, pp)
    merged = dict(base)
    for k, v in node.items():
        if k == 'Components' and isinstance(v, dict):
            comp = dict(base.get('Components', {}))
            comp.update(v)
            merged[k] = comp
        elif k != '$parent':
            merged[k] = v
    return merged


def actor_params(rf, name):
    path = 'Pack/Actor/%s.pack.zs' % name
    if path not in rf.files:
        return None
    pack = sarc.read(rf.read(path))
    actor = pack_param(pack, 'Actor/%s.engine__actor__ActorParam.bgyml' % name)
    gpt = pack_param(pack, actor.get('Components', {}).get('GameParameterTableRef'))
    comps = gpt.get('Components', {})
    cure = pack_param(pack, comps.get('CureParam'))
    price = pack_param(pack, comps.get('PriceParam'))
    return {
        'hp': cure.get('HitPointRecover', 0),
        'effect': cure.get('EffectType', 'None'),
        'level': cure.get('EffectLevel', 0),
        'time': cure.get('EffectiveTime', 0),
        'sell': price.get('SellingPrice', 0),
    }


def main():
    rf = Romfs(GAME)
    table = byml.Byml(rf.read('Cooking/CookingTable.game__cooking__Table.bgyml')).root

    def recipes(lst, single):
        out = []
        for r in lst:
            parts = [[(t['Type'], t['Name']) for t in m['TargetList']] for m in r['MaterialList']]
            out.append({'result': r['ResultActorName'], 'parts': parts, 'single': single,
                        'bonus': r.get('Bonus', {})})
        return out

    all_recipes = recipes(table['RecipeList'], False) + recipes(table['SingleRecipeList'], True)
    recipe_tags = {n for r in all_recipes for p in r['parts'] for t, n in p if t == 'Tag'}
    recipe_actors = {n for r in all_recipes for p in r['parts'] for t, n in p if t == 'Actor'}

    tags = load_tags(rf)
    texts = msbt.read(sarc.read(rf.read(rf.find('Mals/USen.Product.', '.sarc.zs')))['ActorMsg/PouchContent.msbt'])

    materials = {}
    for name, tl in tags.items():
        cook = [t for t in tl if t.startswith('Cook') and t not in ('Cook', 'CookResult')]
        if not cook and name not in recipe_actors:
            continue
        p = actor_params(rf, name)
        if p is None:
            continue
        p['tags'] = [t for t in cook if t in recipe_tags]
        p['all_tags'] = cook
        p['en'] = texts.get(name + '_Name', name)
        materials[name] = p

    dishes = sorted({r['result'] for r in all_recipes} | {table['SystemData'].get('FailActorName', '')} - {''})
    data = {
        'materials': materials,
        'recipes': all_recipes,
        'dish_names': {d: texts.get(d + '_Name', d) for d in dishes},
        'system': {k: v for k, v in table['SystemData'].items() if k != 'EffectList'},
        'effects': {e['Name']: e for e in table['SystemData'].get('EffectList', [])},
    }
    out = os.path.join(HERE, 'cookdata.json')
    json.dump(data, open(out, 'w', encoding='utf-8'), ensure_ascii=False, indent=1, default=str)
    print('materials %d, recipes %d, dishes %d -> %s' % (len(materials), len(all_recipes), len(dishes), out))


if __name__ == '__main__':
    main()
