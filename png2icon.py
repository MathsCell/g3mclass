#!/usr/bin/env python3
import sys
try:
    import Cocoa
except ModuleNotFoundError:
    import subprocess
    res=subprocess.run([sys.executable, "-m", "pip", "install", "--user", 'pyobjc'], capture_output=True)
    #print(res)
    import Cocoa

def main():
    Cocoa.NSWorkspace.sharedWorkspace().setIcon_forFile_options_(Cocoa.NSImage.alloc().initWithContentsOfFile_(sys.argv[-2]), sys.argv[-1], 0) or sys.exit("Unable to set file icon")
if __name__ == "__main__":
    main()
