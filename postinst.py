import sys
import os
uprof=os.getenv("USERPROFILE")
td=os.path.join(uprof, "tmp")
os.makedirs(td, exist_ok=True)
sys.stderr=open(os.path.join(td, "err.txt"), "w")
sys.stdout=open(os.path.join(td, "out.txt"), "w")
try:
    from win32com.client import Dispatch
except ModuleNotFoundError:
    import subprocess
    subprocess.check_call([sys.executable, "-m", "pip", "install", "--user", 'pywin32'])
    from win32com.client import Dispatch


pexe=sys.executable.replace("python.exe", "pythonw.exe")
print("entering postinst, argv=", sys.argv,
"\npf=", sys.platform,
"\npexe=", pexe,
"\nuprof=", uprof,
)

desktop=os.path.join(uprof, "Desktop")
print("\ndesk=", desktop)
pdir=os.path.dirname(pexe)
if "conda" in pexe:
    target=os.path.join(pdir, "Scripts", "conda.exe")
    targs="run g3mclass.exe"
else:
    import g3mclass
    target=pexe
    targs=os.path.join(os.path.dirname(g3mclass.__file__), "g3mclass.py")
print("target=", target)
print("targs=", targs)

shell=Dispatch('WScript.Shell')
shortcut=shell.CreateShortCut(os.path.join(desktop, "G3Mclass.lnk"))
print("sho=", shortcut)
print("dir=", dir(shortcut))

shortcut.TargetPath=target
shortcut.Arguments=targs
shortcut.WorkingDirectory=uprof
shortcut.WindowStyle=1 # 7 - minimized, 3 - Maximized, 1 - Normal
shortcut.save()

print("end")
