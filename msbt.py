"""Minimal little-endian MSBT reader: label -> plain text."""
import struct


def _text(raw):
    out = []
    i = 0
    n = len(raw)
    while i + 1 < n:
        c = struct.unpack_from('<H', raw, i)[0]
        i += 2
        if c == 0:
            break
        if c == 0x0E:  # tag: group, type, param size, params
            _, _, size = struct.unpack_from('<HHH', raw, i)
            i += 6 + size
            continue
        if c == 0x0F:  # closing tag: group, type
            i += 4
            continue
        out.append(chr(c))
    return ''.join(out)


def read(data):
    assert data[:8] == b'MsgStdBn'
    nsec = struct.unpack_from('<H', data, 0x0E)[0]
    o = 0x20
    labels, texts = {}, []
    for _ in range(nsec):
        magic = data[o:o + 4]
        size = struct.unpack_from('<I', data, o + 4)[0]
        body = o + 0x10
        if magic == b'LBL1':
            groups = struct.unpack_from('<I', data, body)[0]
            for g in range(groups):
                count, off = struct.unpack_from('<II', data, body + 4 + 8 * g)
                p = body + off
                for _ in range(count):
                    ln = data[p]
                    name = data[p + 1:p + 1 + ln].decode('utf-8')
                    idx = struct.unpack_from('<I', data, p + 1 + ln)[0]
                    labels[name] = idx
                    p += 1 + ln + 4
        elif magic == b'TXT2':
            count = struct.unpack_from('<I', data, body)[0]
            offs = [struct.unpack_from('<I', data, body + 4 + 4 * k)[0] for k in range(count)]
            offs.append(size)
            for k in range(count):
                texts.append(_text(data[body + offs[k]:body + offs[k + 1]]))
        o = body + ((size + 15) & ~15)
    return {name: texts[idx] for name, idx in labels.items() if idx < len(texts)}
