"""Build and install the SDL3.dll wrapper that holds the controller still while the Cook Helper is in front.

    py -3 padblock.py build      compile SDL3.dll in this folder from padblock.c (needs clang, lld-link, Windows SDK)
    py -3 padblock.py install    put the wrapper in the game folder; the real DLL becomes SDL3_orig.dll
    py -3 padblock.py uninstall  put the real SDL3.dll back
    py -3 padblock.py status

The game must be closed to install or uninstall. ensure() is what the auto-start watcher calls while the game is
closed: it puts the wrapper back after a port update replaced SDL3.dll, as long as the wrapper still forwards every
function the new SDL3.dll has.
"""
import glob
import os
import shutil
import struct
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
GAME = os.path.normpath(os.path.join(HERE, '..', '..', 'game'))
WRAPPER = os.path.join(HERE, 'SDL3.dll')
MARK = 'CookHelperPadBlock'
OWN = {'SDL_GetGamepadButton', 'SDL_GetGamepadAxis', 'SDL_GetGamepadSensorData', MARK}


def exports(path):
    """Export names of a PE DLL, read straight from its export directory."""
    with open(path, 'rb') as f:
        b = f.read()
    pe = struct.unpack_from('<I', b, 0x3C)[0]
    nsec = struct.unpack_from('<H', b, pe + 6)[0]
    opt = pe + 24
    rva = struct.unpack_from('<I', b, opt + 112)[0]  # PE32+ data directory 0: exports
    if not rva:
        return set()
    sec_at = opt + struct.unpack_from('<H', b, pe + 20)[0]
    secs = [struct.unpack_from('<IIII', b, sec_at + i * 40 + 8) for i in range(nsec)]  # vsize, va, rawsize, rawptr

    def off(r):
        for vsize, va, rawsize, ptr in secs:
            if va <= r < va + max(vsize, rawsize):
                return r - va + ptr
        raise ValueError('rva %#x outside the sections' % r)

    d = off(rva)
    n, names_rva = struct.unpack_from('<I', b, d + 24)[0], struct.unpack_from('<I', b, d + 32)[0]
    out = set()
    for i in range(n):
        p = off(struct.unpack_from('<I', b, off(names_rva) + i * 4)[0])
        out.add(b[p:b.index(b'\0', p)].decode('ascii'))
    return out


def is_wrapper(path):
    return os.path.exists(path) and MARK in exports(path)


def tool(name):
    found = shutil.which(name)
    if found:
        return found
    hits = glob.glob(os.path.expandvars(r'%LOCALAPPDATA%\Programs\Swift\Toolchains\*\usr\bin\%s.exe' % name))
    if hits:
        return hits[-1]
    raise SystemExit('%s not found' % name)


def build(real=None):
    real = real or os.path.join(GAME, 'SDL3_orig.dll')
    if not os.path.exists(real):
        real = os.path.join(GAME, 'SDL3.dll')
    if is_wrapper(real):
        raise SystemExit('%s is the wrapper, not the real SDL3' % real)
    names = sorted(exports(real) - OWN)
    with open(os.path.join(HERE, 'padblock.def'), 'w', newline='\n') as f:
        f.write('LIBRARY SDL3\nEXPORTS\n')
        f.writelines('    %s=SDL3_orig.%s\n' % (n, n) for n in names)
    sdk = sorted(glob.glob(r'C:\Program Files (x86)\Windows Kits\10\Lib\*\um\x64'))[-1]
    obj = os.path.join(HERE, 'padblock.obj')
    subprocess.run([tool('clang'), '--target=x86_64-pc-windows-msvc', '-O2', '-c', '-fno-stack-protector',
                    '-Wall', os.path.join(HERE, 'padblock.c'), '-o', obj], check=True)
    subprocess.run([tool('lld-link'), '/dll', '/nodefaultlib', '/entry:DllMain', '/def:' + os.path.join(HERE, 'padblock.def'),
                    '/libpath:' + sdk, 'kernel32.lib', 'user32.lib', obj, '/out:' + WRAPPER], check=True)
    for junk in (obj, os.path.join(HERE, 'SDL3.lib'), os.path.join(HERE, 'SDL3.exp')):
        if os.path.exists(junk):
            os.remove(junk)
    print('built %s, forwarding %d functions' % (WRAPPER, len(names)))


def install():
    dll, orig = os.path.join(GAME, 'SDL3.dll'), os.path.join(GAME, 'SDL3_orig.dll')
    if not is_wrapper(dll):
        missing = exports(dll) - exports(WRAPPER)
        if missing:
            return 'the game has a newer SDL3.dll; run "padblock.py build" first (%d new functions)' % len(missing)
        shutil.copy2(dll, orig)  # a port update brought a new real SDL3.dll; it replaces the old copy
    if open(dll, 'rb').read() != open(WRAPPER, 'rb').read():
        try:
            shutil.copy2(WRAPPER, dll)
        except PermissionError:
            return 'SDL3.dll is in use; close the game and run this again (the watcher does it on its own)'
        return 'installed'
    return 'already installed'


def uninstall():
    dll, orig = os.path.join(GAME, 'SDL3.dll'), os.path.join(GAME, 'SDL3_orig.dll')
    if is_wrapper(dll) and os.path.exists(orig):
        shutil.copy2(orig, dll)
        os.remove(orig)
        return 'removed, the real SDL3.dll is back'
    return 'not installed'


def ensure():
    """Reinstall after a port update. Returns a note for the log, or None when nothing changed."""
    dll = os.path.join(GAME, 'SDL3.dll')
    if not os.path.exists(WRAPPER) or not os.path.exists(os.path.join(GAME, 'SDL3_orig.dll')) or is_wrapper(dll):
        return None  # never installed, or still in place
    try:
        return 'pad block: ' + install()
    except OSError as e:
        return 'pad block: could not reinstall (%s)' % e


def status():
    dll = os.path.join(GAME, 'SDL3.dll')
    return 'installed' if is_wrapper(dll) else 'not installed'


if __name__ == '__main__':
    cmd = sys.argv[1] if len(sys.argv) > 1 else 'status'
    if cmd == 'build':
        build()
    else:
        print({'install': install, 'uninstall': uninstall, 'status': status}[cmd]())
