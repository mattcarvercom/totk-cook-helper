"""Read the running game's runtime material pouch from memory.

Port of livemem.py (Windows) to Linux. The game keeps each saved array behind
a descriptor: [u64 length, u64 pointer, u64 length, u64 pointer]. Material
names are fixed 0x50-byte entries: [u64 pointer to its own text][u32 capacity
0x40][64 bytes of text]. Counts are int32, -1 for an empty slot. Both copies
change together, so the first one is read.

find() scans the game's writable memory once for a descriptor pair that fits:
names that are known materials, and counts that are -1 exactly where a name is
empty. The save file supplies the array length and breaks a tie if more than
one int array fits. read() then takes a few milliseconds.

This module is read-only. It never writes to the game.
"""
import os
import struct

import live_save

NAME_STRIDE = 0x50
CHUNK = 64 << 20
MAX_ADDR = 1 << 47


class Gone(Exception):
    """The game exited or the arrays moved."""


class Pouch:
    def __init__(self, pid):
        self.pid = pid
        self.names_at = None
        self.nums_at = None
        self.n = 0

    def close(self):
        self.pid = None

    def alive(self):
        return bool(self.pid) and os.path.exists('/proc/%d' % self.pid)

    def read_mem(self, address, size):
        return live_save.read_mem(self.pid, address, size)

    def _read(self, address, size):
        try:
            return self.read_mem(address, size)
        except live_save.Unavailable:
            raise
        except OSError:
            return b''

    def regions(self):
        """Writable private or anonymous regions, as the game's heap."""
        try:
            with open('/proc/%d/maps' % self.pid, encoding='ascii') as f:
                for line in f:
                    parts = line.split()
                    if len(parts) < 2:
                        continue
                    perms = parts[1]
                    if 'r' not in perms or 'w' not in perms:
                        continue
                    try:
                        start, end = [int(x, 16) for x in parts[0].split('-')]
                    except ValueError:
                        continue
                    if end - start < 4096:
                        continue
                    path = parts[-1] if len(parts) > 5 else ''
                    if path and not path.startswith('['):
                        continue
                    yield start, end
        except OSError:
            raise Gone('the game process is gone')

    # --- discovery ------------------------------------------------------------

    def _names(self, ptr, n):
        raw = self._read(ptr, n * NAME_STRIDE)
        if len(raw) < n * NAME_STRIDE:
            return None
        out = []
        for i in range(n):
            o = i * NAME_STRIDE
            p, cap = struct.unpack_from('<QI', raw, o)
            if p != ptr + o + 12 or cap != 0x40:
                return None
            out.append(raw[o + 12:o + 76].split(b'\0')[0].decode('ascii', 'replace'))
        return out

    def find(self, n, materials, hint=None, stop=None):
        """Locate the names and counts arrays.

        n: array length from the save. materials: known material actor names.
        hint: {actor: count} from the save, used only to break a tie.
        stop: callable that aborts the scan.
        """
        key = struct.pack('<Q', n)
        descs = []
        for base, size in self.regions():
            off = 0
            while off < size:
                if stop and stop():
                    raise Gone('stopped')
                data = self._read(base + off, min(CHUNK, size - off) + 0x28)
                i = data.find(key)
                while i >= 0:
                    if i % 8 == 0 and data[i + 16:i + 24] == key and len(data) >= i + 0x20:
                        pa = struct.unpack_from('<Q', data, i + 8)[0]
                        pb = struct.unpack_from('<Q', data, i + 24)[0]
                        if 0x10000 < pa < MAX_ADDR and 0x10000 < pb < MAX_ADDR and pa != pb:
                            descs.append(pa)
                    i = data.find(key, i + 1)
                off += CHUNK
        names = None
        for pa in descs:
            got = self._names(pa, n)
            if got and any(got):
                used = [x for x in got if x]
                if sum(x in materials for x in used) >= 0.8 * len(used):
                    names, self.names_at = got, pa
                    break
        if names is None:
            raise Gone('no material list in memory')
        fits = []
        for pa in descs:
            raw = self._read(pa, n * 4)
            if len(raw) < n * 4:
                continue
            vals = struct.unpack('<%di' % n, raw)
            if all((v >= 0) == bool(nm) and v < 100000 for v, nm in zip(vals, names)):
                fits.append((pa, vals))
        if not fits:
            raise Gone('no count array in memory')
        if len(fits) > 1 and hint:
            def score(f):
                return sum(1 for v, nm in zip(f[1], names) if nm and hint.get(nm) == v)
            fits.sort(key=score, reverse=True)
        self.nums_at = fits[0][0]
        self.n = n
        return len(fits)

    # --- live read ------------------------------------------------------------

    def read(self):
        """{actor: count} from the game's memory."""
        if not self.alive():
            raise Gone('the game exited')
        names = self._names(self.names_at, self.n)
        raw = self._read(self.nums_at, self.n * 4)
        if names is None or len(raw) < self.n * 4:
            raise Gone('the arrays moved')
        vals = struct.unpack('<%di' % self.n, raw)
        inv = {}
        for nm, v in zip(names, vals):
            if nm and v > 0:
                inv[nm] = inv.get(nm, 0) + v
        return inv
