"""Opens the cook helper when totk.exe starts. The helper closes itself when the game exits.

Started at Windows login by the "TotK Cook Helper watcher" shortcut in the Startup folder. It checks the process
list every 3 seconds, which costs next to nothing. Delete that shortcut to turn auto-start off.
"""
import ctypes
import os
import subprocess
import sys
import time

import proc

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), 'padblock'))
import padblock  # noqa: E402

HERE = os.path.dirname(os.path.abspath(__file__))
GAME_EXE = 'totk.exe'
POLL_S = 3
LOG = os.path.join(HERE, 'autostart_watch.log')
ERROR_ALREADY_EXISTS = 183


def log(msg):
    try:
        with open(LOG, 'a', encoding='utf-8') as f:
            f.write('%s %s\n' % (time.strftime('%Y-%m-%dT%H:%M:%S'), msg))
    except OSError:
        pass


def start_helper():
    pyw = os.path.join(os.path.dirname(sys.executable), 'pythonw.exe')
    if not os.path.exists(pyw):
        pyw = sys.executable
    return subprocess.Popen([pyw, '-E', os.path.join(HERE, 'cook_helper.pyw'), '--with-game'], cwd=HERE)


def main():
    k32 = ctypes.windll.kernel32
    mutex = k32.CreateMutexW(None, False, 'Local\\TotKCookHelperWatcher')  # one watcher at a time
    if k32.GetLastError() == ERROR_ALREADY_EXISTS:
        return
    log('watcher started')
    was_running = proc.running(GAME_EXE)  # started while the game runs: the helper is already up
    checked = 0
    while True:
        running = proc.running(GAME_EXE)
        if running and not was_running:
            # A helper closed by hand stays closed until the next game start.
            h = start_helper()
            log('game started, helper opened (pid %d)' % h.pid)
        if not running and (was_running or time.time() - checked > 60):  # SDL3.dll is writable only while the game is closed
            checked = time.time()
            note = padblock.ensure()
            if note:
                log(note)
        was_running = running
        time.sleep(POLL_S)
    k32.CloseHandle(mutex)


if __name__ == '__main__':
    main()
