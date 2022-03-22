#!/usr/bin/env python3
import sys
import os
import sysconfig
#if sys.platform == 'win32':
#    from win32com.client import Dispatch
#    import winreg
from setuptools import setup

long_description = "G3Mclass is a software for Gaussian Mixture Model for Marker Classification";
with open('g3mclass/version.txt', 'r') as f:
    version = f.read().rstrip();

setup(
   name='g3mclass',
   version=version,
   description='Gaussian Mixture Model for marker classification',
   keywords='biomedical marker, semi-constrained classification, GMM',
   license='GNU General Public License v2',
   long_description=long_description,
   author='Serguei Sokol, Marina Guvakova',
   author_email='sokol@insa-toulouse.fr',
   url='https://github.com/MathsCell/g3mclass',
   packages=['g3mclass'],
   py_modules=['g3mclass', 'tools_g3m'],
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
        'Source': 'https://github.com/MathsCell/g3mclass',
        'Tracker': 'https://github.com/MathsCell/g3mclass/issues',
   },
)
