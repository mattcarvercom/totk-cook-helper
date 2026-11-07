"""Add or remove the Startup-folder shortcut that runs autostart_watch.pyw at sign-in.

    py -3 install_autostart.py           add the shortcut and start the watcher now
    py -3 install_autostart.py remove    delete the shortcut
"""
import os
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
NAME = 'TotK Cook Helper watcher.lnk'


def startup():
    out = subprocess.run(['powershell', '-NoProfile', '-Command', "[Environment]::GetFolderPath('Startup')"],
                         capture_output=True, text=True, check=True)
    return out.stdout.strip()


def pythonw():
    exe = os.path.join(os.path.dirname(sys.executable), 'pythonw.exe')
    return exe if os.path.exists(exe) else sys.executable


def add():
    link = os.path.join(startup(), NAME)
    script = os.path.join(HERE, 'autostart_watch.pyw')
    ps = ("$s = (New-Object -ComObject WScript.Shell).CreateShortcut('%s'); $s.TargetPath = '%s'; "
          "$s.Arguments = '-E \"%s\"'; $s.WorkingDirectory = '%s'; $s.Save()") % (link, pythonw(), script, HERE)
    subprocess.run(['powershell', '-NoProfile', '-Command', ps], check=True)
    subprocess.Popen([pythonw(), '-E', script], cwd=HERE)
    print('added %s and started the watcher' % link)


def remove():
    link = os.path.join(startup(), NAME)
    if os.path.exists(link):
        os.remove(link)
        print('removed %s; the watcher stops at the next sign-in or when you end pythonw.exe' % link)
    else:
        print('no shortcut to remove')


if __name__ == '__main__':
    remove() if sys.argv[1:] == ['remove'] else add()
