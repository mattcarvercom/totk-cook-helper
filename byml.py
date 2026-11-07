"""Minimal little-endian BYML (v2 to v7) reader."""
import struct


class Byml:
    def __init__(self, data):
        self.d = data
        assert data[:2] == b'YB', 'only little-endian BYML'
        self.ver = struct.unpack_from('<H', data, 2)[0]
        kt, st, root = struct.unpack_from('<III', data, 4)
        self.keys = self._strtab(kt) if kt else []
        self.strs = self._strtab(st) if st else []
        self.root = self._node(root) if root else None

    def u32(self, o):
        return struct.unpack_from('<I', self.d, o)[0]

    def _strtab(self, o):
        assert self.d[o] == 0xC2
        n = int.from_bytes(self.d[o + 1:o + 4], 'little')
        out = []
        for i in range(n):
            s = o + self.u32(o + 4 + 4 * i)
            e = self.d.index(b'\0', s)
            out.append(self.d[s:e].decode('utf-8'))
        return out

    def _value(self, t, raw, at):
        d = self.d
        if t == 0xA0:
            return self.strs[raw]
        if t == 0xA1:  # binary
            n = self.u32(raw)
            return d[raw + 4:raw + 4 + n]
        if t == 0xD0:
            return bool(raw)
        if t == 0xD1:
            return struct.unpack('<i', struct.pack('<I', raw))[0]
        if t == 0xD2:
            return struct.unpack('<f', struct.pack('<I', raw))[0]
        if t == 0xD3:
            return raw
        if t == 0xD4:
            return struct.unpack_from('<q', d, raw)[0]
        if t == 0xD5:
            return struct.unpack_from('<Q', d, raw)[0]
        if t == 0xD6:
            return struct.unpack_from('<d', d, raw)[0]
        if t == 0xFF:
            return None
        if t in (0xC0, 0xC1, 0x20, 0x21):
            return self._node(raw)
        raise ValueError('type %02x at %x' % (t, at))

    def _node(self, o):
        d = self.d
        t = d[o]
        n = int.from_bytes(d[o + 1:o + 4], 'little')
        if t == 0xC0:
            types = d[o + 4:o + 4 + n]
            vo = o + 4 + ((n + 3) & ~3)
            return [self._value(types[i], self.u32(vo + 4 * i), o) for i in range(n)]
        if t == 0xC1:
            out = {}
            for i in range(n):
                e = o + 4 + 8 * i
                ki = int.from_bytes(d[e:e + 3], 'little')
                vt = d[e + 3]
                out[self.keys[ki]] = self._value(vt, self.u32(e + 4), e)
            return out
        if t in (0x20, 0x21):  # hash maps: u32 or u64 keys
            ks = 4 if t == 0x20 else 8
            es = ks + 4
            out = {}
            types_at = o + 4 + es * n
            for i in range(n):
                e = o + 4 + es * i
                k = int.from_bytes(d[e:e + ks], 'little')
                v = self.u32(e + ks)
                out[k] = self._value(d[types_at + i], v, e)
            return out
        if t == 0xA0:
            return self.strs[n]
        raise ValueError('node %02x at %x' % (t, o))


def load(path):
    return Byml(open(path, 'rb').read()).root
