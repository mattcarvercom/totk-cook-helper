"""Export the game's own item icons for the helper window.

Reads UI/Tex/Icon/<actor>.bntx.zs from the port's romfs, decodes the texture and writes
ui/icons/<icon>.webp plus ui/icons/index.json (actor name -> icon file). The icons come
from your own copy of the game and stay on this machine.

Run again after a game update:  py -3 build_icons.py [game folder]
Needs: pip install texture2ddecoder pillow
"""
import json
import os
import re
import struct
import sys

import texture2ddecoder as t2d
from PIL import Image

from build_data import Romfs

HERE = os.path.dirname(os.path.abspath(__file__))
GAME = sys.argv[1] if len(sys.argv) > 1 else os.path.join(HERE, '..', 'game')
OUT = os.path.join(HERE, 'ui', 'icons')
SIZE = 128

# format id (high byte of the BRTI format) -> (block w, block h, bytes per block, decoder)
FORMATS = {
    0x0b: (1, 1, 4, None),
    0x1a: (4, 4, 8, t2d.decode_bc1),
    0x1c: (4, 4, 16, t2d.decode_bc3),
    0x1d: (4, 4, 8, t2d.decode_bc4),
    0x1e: (4, 4, 16, t2d.decode_bc5),
    0x20: (4, 4, 16, t2d.decode_bc7),
    0x2d: (4, 4, 16, 'astc'), 0x2e: (5, 4, 16, 'astc'), 0x2f: (5, 5, 16, 'astc'),
    0x30: (6, 5, 16, 'astc'), 0x31: (6, 6, 16, 'astc'), 0x32: (8, 5, 16, 'astc'),
    0x33: (8, 6, 16, 'astc'), 0x34: (8, 8, 16, 'astc'),
}


def deswizzle(data, w, h, bpp, block_height):
    """Undo the Tegra block-linear layout. w and h are in format blocks."""
    gobs_x = -(-w * bpp // 64)
    out = bytearray(w * h * bpp)
    rows = 8 * block_height
    for y in range(h):
        base_y = (y // rows) * 512 * block_height * gobs_x + (y % rows // 8) * 512
        sub_y = ((y % 8) // 2) * 64 + (y % 2) * 16
        o = y * w * bpp
        for x in range(w):
            xb = x * bpp
            a = base_y + (xb // 64) * 512 * block_height + ((xb % 64) // 32) * 256 + ((xb % 32) // 16) * 32 + sub_y + (xb % 16)
            out[o:o + bpp] = data[a:a + bpp]
            o += bpp
    return bytes(out)


def decode_bntx(raw):
    i = raw.find(b'BRTI')
    if i < 0:
        raise ValueError('no BRTI')
    fmt, = struct.unpack_from('<I', raw, i + 0x1C)
    width, height = struct.unpack_from('<II', raw, i + 0x24)
    layout, = struct.unpack_from('<I', raw, i + 0x34)
    ptrs, = struct.unpack_from('<Q', raw, i + 0x70)
    mip0, = struct.unpack_from('<Q', raw, ptrs)
    kind = fmt >> 8
    if kind not in FORMATS:
        raise ValueError('format %#x' % fmt)
    bw, bh, bpp, dec = FORMATS[kind]
    wb, hb = -(-width // bw), -(-height // bh)
    block_height = 1 << (layout & 7)
    # small textures use a shorter block height
    while block_height > 1 and hb <= (block_height // 2) * 8:
        block_height //= 2
    lin = deswizzle(raw[mip0:], wb, hb, bpp, block_height)
    if dec is None:
        return Image.frombytes('RGBA', (width, height), lin)
    if dec == 'astc':
        px = t2d.decode_astc(lin, wb * bw, hb * bh, bw, bh)
    else:
        px = dec(lin, wb * bw, hb * bh)
    img = Image.frombytes('RGBA', (wb * bw, hb * bh), px, 'raw', 'BGRA')
    return img.crop((0, 0, width, height))


SUFFIX = re.compile(r'_(TemporaryOwnedByNpc|OwnedByNpc|Static|NoReaction|GoronDisplay|Kakariko\d+|Bundle_A)$')
GET = re.compile(r'^(?:Animal|Item)_(Fish|Insect|Plant|Mushroom|Fruit|Meat)_(\w+)$')


def candidates(actor):
    """Icon names to try for an actor, most specific first."""
    names = [actor]
    base = actor
    while SUFFIX.search(base):
        base = SUFFIX.sub('', base)
        names.append(base)
    m = GET.match(base)
    if m:
        names.append('Item_%sGet_%s' % m.groups())
    if base.startswith('LightBall_'):
        names.append('LightBall_Large' if 'Large' in base else 'LightBall_Small')
    return names


def main():
    rf = Romfs(GAME)
    have = {p[len('UI/Tex/Icon/'):-len('.bntx.zs')] for p in rf.files if p.startswith('UI/Tex/Icon/')}
    data = json.load(open(os.path.join(HERE, 'cookdata.json'), encoding='utf-8'))
    wanted = set(data['materials']) | set(data['dish_names']) | {r['result'] for r in data['recipes']}
    wanted |= {data['system']['FailActorName'], data['system']['FairyActorName']}
    wanted |= {n for n in have if n.startswith('Item_Cook_')}

    os.makedirs(OUT, exist_ok=True)
    index, done, missing, failed = {}, {}, [], []
    for actor in sorted(wanted):
        icon = next((n for n in candidates(actor) if n in have), None)
        if not icon:
            missing.append(actor)
            continue
        if icon not in done:
            try:
                img = decode_bntx(rf.read('UI/Tex/Icon/%s.bntx.zs' % icon))
                img = img.resize((SIZE, SIZE), Image.LANCZOS)
                img.save(os.path.join(OUT, icon + '.webp'), 'WEBP', quality=88, method=6)
                done[icon] = True
            except Exception as e:  # keep going, report at the end
                failed.append('%s: %s' % (icon, e))
                done[icon] = False
        if done[icon]:
            index[actor] = icon + '.webp'
    json.dump(index, open(os.path.join(OUT, 'index.json'), 'w', encoding='utf-8'), indent=0, sort_keys=True)
    print('%d actors mapped to %d icons' % (len(index), sum(done.values())))
    if missing:
        print('no icon for %d: %s' % (len(missing), ', '.join(missing)))
    for f in failed:
        print('failed', f)


if __name__ == '__main__':
    main()
