#!/usr/bin/env python3
from setuptools import setup

with open('README.rst', 'r', encoding='utf-8') as f:
    long_description = f.read();
with open('version.txt', 'r') as f:
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
   package_dir={'g3mclass': '.'},
   package_data={
        'g3mclass': ['version.txt', 'licence_en.txt', 'g3mclass_lay.kvh', 'welcome.html', 'docs/*', 'example/*'],
   },
   install_requires=['wxpython', 'numpy', 'pandas', 'matplotlib'],
   entry_points={
        'console_scripts': [
        'g3mclass = g3mclass:main',
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
