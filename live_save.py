"""Read the running TotK recomp's memory without writing anything.

The recomp maps guest memory at its real addresses. The player actor graph
exposes the current position and facing through the same traversal the port's
frame trace uses; that is the live source the companion polls. A separate
LiveSave helper can also read the game's in-memory progress buffer when the
save manager has published it.

Linux only allows a process to read another process's memory when it is the
parent (Yama ptrace_scope 1) or has ptrace privileges. The companion gets that
for free when it launches the game itself. No sudo and no ptrace_scope changes.

This module is read-only. It never calls process_vm_writev and never writes to
the game or its save files.
"""
import ctypes
import glob
import math
import os
import struct

SENTINEL = 0xa3db7114
POINTER_SIZE = 8
HEADER_SIZE = 0x28
SCAN_CHUNK = 64 << 20
MIN_REGION = 1 << 20


class NotRunning(Exception):
    """The game process is gone."""


class NotReady(Exception):
    """The game is running but has not published its save buffer yet."""


class Unavailable(Exception):
    """Live memory cannot be read, usually because the companion is not the parent."""


class _IOVec(ctypes.Structure):
    _fields_ = [('iov_base', ctypes.c_void_p), ('iov_len', ctypes.c_size_t)]


_libc = ctypes.CDLL('libc.so.6', use_errno=True)
_libc.process_vm_readv.argtypes = [ctypes.c_int, ctypes.POINTER(_IOVec), ctypes.c_ulong,
                                   ctypes.POINTER(_IOVec), ctypes.c_ulong, ctypes.c_ulong]
_libc.process_vm_readv.restype = ctypes.c_ssize_t


def read_mem(pid, address, size):
    """Read up to size bytes from another process. Read-only."""
    if size <= 0:
        return b''
    buf = ctypes.create_string_buffer(size)
    local = _IOVec(ctypes.cast(buf, ctypes.c_void_p), size)
    remote = _IOVec(ctypes.c_void_p(address), size)
    got = _libc.process_vm_readv(pid, ctypes.byref(local), 1,
                                 ctypes.byref(remote), 1, 0)
    if got < 0:
        err = ctypes.get_errno()
        if err in (1, 13):  # EPERM, EACCES
            raise Unavailable('ptrace permission denied')
        raise OSError(err, os.strerror(err))
    return buf.raw[:got]


def _u64(pid, address):
    raw = read_mem(pid, address, 8)
    return struct.unpack('<Q', raw)[0] if len(raw) == 8 else 0


def _u32(pid, address):
    raw = read_mem(pid, address, 4)
    return struct.unpack('<I', raw)[0] if len(raw) == 4 else 0


def player_state(pid, anchor=None, max_distance=None):
    """Return the live player position and facing from the game's actor graph.

    This is the same actor lookup the recomp's frame trace uses. It returns
    None while the game is loading or in a menu where the graph is not up.
    """
    version = _u32(pid, 0x5e28b4)
    if version >= 0x8f:
        base = 0x7003add238
    elif version == 0x6e:
        base = 0x7003f60a68
    else:
        base = 0x7004024538
    p1 = _u64(pid, base)
    if not p1:
        return None
    p2 = _u64(pid, p1 + 0x1e8)
    if not p2:
        return None
    p3 = _u64(pid, p2 + 0x58)
    if not p3:
        return None
    p4 = _u64(pid, p3 + 0x68)
    if not p4:
        return None
    count = _u32(pid, p4 + 0x20)
    if not 0 < count <= 256:
        return None
    table = _u64(pid, p4 + 0x28)
    if not table:
        return None
    best = None
    best_d = 1e30
    for i in range(count):
        p6 = _u64(pid, table + 8 + i * 0x70)
        if not p6:
            continue
        p7 = _u64(pid, p6 + 0x40)
        if not p7:
            continue
        raw = read_mem(pid, p7 + 0x2b4, 12)
        quat = read_mem(pid, p7 + 0x2c0, 16)
        if len(raw) != 12 or len(quat) != 16:
            continue
        x, y, z = struct.unpack('<3f', raw)
        qw, qx, qy, qz = struct.unpack('<4f', quat)
        if not (math.isfinite(x) and math.isfinite(y) and math.isfinite(z)):
            continue
        if abs(x) > 12000 or abs(z) > 12000 or y < -5000 or y > 20000:
            continue
        if abs(x) < 1 and abs(y) < 1 and abs(z) < 1:
            continue
        if abs(x) < 1 and abs(y + 3975) < 1 and abs(z) < 1:
            # Placeholder actor used while the world is not loaded yet.
            continue
        norm = qw * qw + qx * qx + qy * qy + qz * qz
        if not (0.5 < norm < 1.5):
            continue
        heading = math.atan2(-2.0 * (qw * qy + qx * qz),
                             1.0 - 2.0 * (qy * qy + qz * qz))
        if anchor is not None:
            if len(anchor) >= 3:
                d = math.sqrt((x - anchor[0]) ** 2 + (y - anchor[1]) ** 2 +
                              (z - anchor[2]) ** 2)
            else:
                d = math.hypot(x - anchor[0], z - anchor[1])
            if max_distance is not None and d > max_distance:
                continue
        else:
            d = 0
        if d < best_d:
            best_d = d
            best = {'x': x, 'y': y, 'z': z, 'heading': heading}
        if anchor is None:
            break
    return best


def newest_save(save_root):
    paths = glob.glob(os.path.join(save_root, '*', 'slot_*', 'progress.sav'))
    if not paths:
        return None
    return max(paths, key=os.path.getmtime)


def find_pid(game_dir):
    exe = os.path.realpath(os.path.join(game_dir, 'totk'))
    for entry in glob.glob('/proc/[0-9]*'):
        if not os.path.basename(entry).isdigit():
            continue
        try:
            target = os.path.realpath(entry + '/exe')
        except OSError:
            continue
        if target == exe or os.path.basename(target) == 'totk':
            return int(os.path.basename(entry))
    return None


class LiveSave:
    def __init__(self, game_dir, pid=None, save_root=None):
        self.game_dir = os.path.abspath(os.path.expanduser(game_dir))
        self.save_root = save_root or os.path.join(self.game_dir, 'profile', 'save')
        self.pid = pid
        self.save_path = None
        self.size = 0
        self.table_size = 0
        self.signature = b''
        self.buffer_start = None

    def alive(self):
        return bool(self.pid) and os.path.exists('/proc/%d' % self.pid)

    def _regions(self):
        out = []
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
                    if end - start < MIN_REGION:
                        continue
                    path = parts[-1] if len(parts) > 5 else ''
                    if path and not path.startswith('['):
                        continue
                    out.append((start, end))
        except OSError:
            raise NotRunning('the game process is gone')
        return out

    def _prepare(self):
        if not self.pid:
            self.pid = find_pid(self.game_dir)
        if not self.pid or not self.alive():
            raise NotRunning('the game is not running')
        path = newest_save(self.save_root)
        if not path:
            raise NotReady('no save file yet')
        with open(path, 'rb') as f:
            disk = f.read()
        table_end = disk.find(struct.pack('<I', SENTINEL))
        if table_end < HEADER_SIZE:
            raise NotReady('the save table is not ready')
        signature = disk[HEADER_SIZE:HEADER_SIZE + 32]
        size = len(disk)
        needle = struct.pack('<I', SENTINEL)
        for start, end in self._regions():
            offset = start
            while offset < end:
                amount = min(SCAN_CHUNK, end - offset)
                try:
                    chunk = read_mem(self.pid, offset, amount)
                except Unavailable:
                    raise
                except OSError:
                    break
                pos = 0
                while True:
                    hit = chunk.find(needle, pos)
                    if hit < 0:
                        break
                    candidate = offset + hit - table_end
                    if candidate >= start:
                        try:
                            if read_mem(self.pid, candidate + HEADER_SIZE, 32) == signature:
                                self.save_path = path
                                self.size = size
                                self.table_size = table_end
                                self.signature = signature
                                self.buffer_start = candidate
                                return
                        except OSError:
                            pass
                    pos = hit + 1
                offset += amount
        raise NotReady('the live save buffer is not published yet')

    def read(self):
        """Return the current progress save as bytes.

        Raises NotRunning, NotReady, or Unavailable. The caller retries or
        falls back to the save file.
        """
        if not self.alive():
            raise NotRunning('the game is not running')
        if self.buffer_start is None:
            self._prepare()
        try:
            data = read_mem(self.pid, self.buffer_start, self.size)
        except OSError:
            # The game unmaps the save buffer while a menu is open, during a
            # load, and while it saves. Drop the address and look for the new
            # buffer; _prepare raises NotReady until the game publishes one.
            self.buffer_start = None
            self._prepare()
            data = read_mem(self.pid, self.buffer_start, self.size)
        if (len(data) != self.size or
                data[self.table_size:self.table_size + 4] != struct.pack('<I', SENTINEL) or
                data[HEADER_SIZE:HEADER_SIZE + 32] != self.signature):
            self.buffer_start = None
            self._prepare()
            data = read_mem(self.pid, self.buffer_start, self.size)
        return data
