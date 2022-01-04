#!/usr/bin/env python3
import sys
import os
import sysconfig
#if sys.platform == 'win32':
#    from win32com.client import Dispatch
#    import winreg
from setuptools import setup

def get_reg(name,path):
    # Read variable from Windows Registry
    # From https://stackoverflow.com/a/35286642
    try:
        registry_key = winreg.OpenKey(winreg.HKEY_CURRENT_USER, path, 0,
                                       winreg.KEY_READ)
        value, regtype = winreg.QueryValueEx(registry_key, name)
        winreg.CloseKey(registry_key)
        return value
    except WindowsError:
        return None

def post_install():
    # Creates a Desktop shortcut to the installed software

    # Package name
    packageName = 'mypackage'

    # Scripts directory (location of launcher script)
    scriptsDir = sysconfig.get_path('scripts')

    # Target of shortcut
    target = os.path.join(scriptsDir, packageName + '.exe')

    # Name of link file
    linkName = packageName + '.lnk'

    # Read location of Windows desktop folder from registry
    regName = 'Desktop'
    regPath = r'Software\Microsoft\Windows\CurrentVersion\Explorer\User Shell Folders'
    desktopFolder = os.path.normpath(get_reg(regName,regPath))

    # Path to location of link file
    pathLink = os.path.join(desktopFolder, linkName)
    shell = Dispatch('WScript.Shell')
    shortcut = shell.CreateShortCut(pathLink)
    shortcut.Targetpath = target
    shortcut.WorkingDirectory = scriptsDir
    shortcut.WindowStyle = 7 # 7 - minimized, 3 - Maximized, 1 - Normal
    shortcut.save()

with open('README.rst', 'r', encoding='utf-8') as f:
    long_description = f.read();
with open('g3mclass/version.txt', 'r') as f:
    version = f.read().rstrip();

setup(
   name='g3mclass',
   version=version,
   description='Gaussian Mixture Model for marker classification',
   keywords='biomedical marker, semi-supervised classification, GMM',
   license='GNU General Public License v2',
   long_description=long_description,
   author='Serguei Sokol, Marina Guvakova',
   author_email='sokol@insa-toulouse.fr',
   url='https://github.com/sgsokol/g3mclass',
   packages=['g3mclass'],
   py_modules=['g3mclass', 'tools_g3m'],
   scripts=['postinst.py'],
   #options={'bdist_wininst': {'post_install': 'postinst.py'}},
   #package_dir={'g3mclass': '.'},
   package_data={
        'g3mclass': ['version.txt', 'licence_en.txt', 'g3mclass_lay.kvh', 'welcome.html', 'help/*', 'example/*'],
   },
   install_requires=['wxpython', 'numpy', 'pandas', 'matplotlib>=3.5.1', 'xlsxwriter'],
   entry_points={
        'gui_scripts': [
        'g3mclass = g3mclass.g3mclass:main',
        ],
   },
   classifiers=[
        'Environment :: Console',
        'Environment :: MacOS X :: Aqua',
        'Environment :: MacOS X :: Carbon',
        'Environment :: MacOS X :: Cocoa',
        'Environment :: Win32 (MS Windows)',
        'Environment :: X11 Applications :: GTK',
        'Intended Audience :: End Users/Desktop',
        'License :: OSI Approved :: GNU General Public License v2 (GPLv2)',
        'Operating System :: OS Independent',
        'Programming Language :: Python :: 3',
        'Topic :: Scientific/Engineering :: Bio-Informatics',
   ],
   project_urls={
        'Documentation': 'https://readthedocs.org/g3mclass',
        'Source': 'https://github.com/sgsokol/g3mclass',
        'Tracker': 'https://github.com/sgsokol/g3mclass/issues',
   },
)
#if sys.argv[1] == 'install' and sys.platform == 'win32':
#    post_install()
