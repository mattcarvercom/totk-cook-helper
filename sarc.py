"""Minimal little-endian SARC reader."""
import struct


def read(data):
    assert data[:4] == b'SARC'
    hdr_len, bom = struct.unpack_from('<HH', data, 4)
    data_off = struct.unpack_from('<I', data, 0x0C)[0]
    o = hdr_len
    assert data[o:o + 4] == b'SFAT'
    sfat_len, count = struct.unpack_from('<HH', data, o + 4)
    nodes = []
    for i in range(count):
        e = o + sfat_len + 16 * i
        h, attr, s, end = struct.unpack_from('<IIII', data, e)
        nodes.append((attr, s, end))
    sfnt = o + sfat_len + 16 * count
    assert data[sfnt:sfnt + 4] == b'SFNT'
    names_at = sfnt + 8
    out = {}
    for attr, s, end in nodes:
        name_off = (attr & 0xFFFF) * 4
        ne = data.index(b'\0', names_at + name_off)
        name = data[names_at + name_off:ne].decode('utf-8')
        out[name] = data[data_off + s:data_off + end]
    return out
