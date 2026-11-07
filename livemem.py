"""Read the material pouch live from the running game's memory.

The game keeps each saved array behind a 0x40-byte descriptor: the array length, a pointer to the array, the
length again and a pointer to a second copy. The material names are fixed 64-byte strings, each stored as
[pointer to its own text][capacity 0x40][64 bytes of text] (0x50 per entry); the counts are int32, -1 for an
empty slot. Both copies change together, so the first one is read.

find() scans the game's writable memory once (about 10 to 20 s) for a descriptor pair that fits: names that
are known materials, and counts that are -1 exactly where a name is empty. The save file supplies the array
length and breaks a tie if more than one int array fits. read() then takes a few milliseconds.
"""
import ctypes
import ctypes.wintypes as wt
import struct

k32 = ctypes.WinDLL('kernel32', use_last_error=True)


class MBI(ctypes.Structure):
    _fields_ = [('BaseAddress', ctypes.c_void_p), ('AllocationBase', ctypes.c_void_p), ('AllocationProtect', wt.DWORD),
                ('PartitionId', wt.WORD), ('RegionSize', ctypes.c_size_t), ('State', wt.DWORD), ('Protect', wt.DWORD),
                ('Type', wt.DWORD)]


k32.OpenProcess.argtypes = [wt.DWORD, wt.BOOL, wt.DWORD]
k32.OpenProcess.restype = wt.HANDLE
k32.CloseHandle.argtypes = [wt.HANDLE]
k32.VirtualQueryEx.argtypes = [wt.HANDLE, ctypes.c_void_p, ctypes.POINTER(MBI), ctypes.c_size_t]
k32.VirtualQueryEx.restype = ctypes.c_size_t
k32.ReadProcessMemory.argtypes = [wt.HANDLE, ctypes.c_void_p, ctypes.c_void_p, ctypes.c_size_t,
                                  ctypes.POINTER(ctypes.c_size_t)]
k32.GetExitCodeProcess.argtypes = [wt.HANDLE, ctypes.POINTER(wt.DWORD)]

MEM_COMMIT, MEM_PRIVATE, PAGE_READWRITE = 0x1000, 0x20000, 0x04
NAME_STRIDE = 0x50
CHUNK = 64 << 20


class Gone(Exception):
    """The game exited or the arrays moved."""


class Pouch:
    def __init__(self, pid):
        self.pid = pid
        self.h = k32.OpenProcess(0x0410, False, pid)  # query information + read
        if not self.h:
            raise OSError('cannot open the game process (error %d)' % ctypes.get_last_error())
        self.names_at = self.nums_at = None
        self.n = 0

    def close(self):
        if self.h:
            k32.CloseHandle(self.h)
            self.h = None

    def alive(self):
        code = wt.DWORD()
        return bool(self.h) and k32.GetExitCodeProcess(self.h, ctypes.byref(code)) and code.value == 259

    def read_mem(self, addr, size):
        buf = ctypes.create_string_buffer(size)
        got = ctypes.c_size_t()
        k32.ReadProcessMemory(self.h, ctypes.c_void_p(addr), buf, size, ctypes.byref(got))
        return buf.raw[:got.value]

    def regions(self):
        addr, m = 0, MBI()
        while k32.VirtualQueryEx(self.h, ctypes.c_void_p(addr), ctypes.byref(m), ctypes.sizeof(m)):
            base = m.BaseAddress or 0
            if m.State == MEM_COMMIT and m.Type == MEM_PRIVATE and m.Protect == PAGE_READWRITE:
                yield base, m.RegionSize
            addr = base + m.RegionSize
            if addr >= 1 << 47:
                break

    # --- discovery ---
    def _names(self, ptr, n):
        raw = self.read_mem(ptr, n * NAME_STRIDE)
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
        """Locate the arrays. n: array length from the save. materials: known material actor names.
        hint: {actor: count} from the save, used only to break a tie. stop: callable that aborts the scan."""
        key = struct.pack('<Q', n)
        descs = []
        for base, size in self.regions():
            off = 0
            while off < size:
                if stop and stop():
                    raise Gone('stopped')
                data = self.read_mem(base + off, min(CHUNK, size - off) + 0x28)
                i = data.find(key)
                while i >= 0:
                    if i % 8 == 0 and data[i + 16:i + 24] == key and len(data) >= i + 0x20:
                        pa, pb = struct.unpack_from('<Q', data, i + 8)[0], struct.unpack_from('<Q', data, i + 24)[0]
                        if 0x10000 < pa < 1 << 47 and 0x10000 < pb < 1 << 47 and pa != pb:
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
            raw = self.read_mem(pa, n * 4)
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

    # --- live read ---
    def read(self):
        """{actor: count} from the game's memory."""
        if not self.alive():
            raise Gone('the game exited')
        names = self._names(self.names_at, self.n)
        raw = self.read_mem(self.nums_at, self.n * 4)
        if names is None or len(raw) < self.n * 4:
            raise Gone('the arrays moved')
        vals = struct.unpack('<%di' % self.n, raw)
        inv = {}
        for nm, v in zip(names, vals):
            if nm and v > 0:
                inv[nm] = inv.get(nm, 0) + v
        return inv
