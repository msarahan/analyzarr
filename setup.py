# -*- coding: utf-8 -*-
"""
Copyright (c) 2012, Michael Sarahan
All rights reserved.

Redistribution and use in source and binary forms, with or without modification, are permitted provided that the following conditions are met:

    Redistributions of source code must retain the above copyright notice, this list of conditions and the following disclaimer.
    Redistributions in binary form must reproduce the above copyright notice, this list of conditions and the following disclaimer in the documentation and/or other materials provided with the distribution.

THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS "AS IS" AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE ARE DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT HOLDER OR CONTRIBUTORS BE LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES; LOSS OF USE, DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND ON ANY THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE OF THIS SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.
"""


from distutils.core import setup

import distutils.dir_util

import os
import sys
import shutil

import analyzarr.Release as Release
# clean the build directory so we aren't mixing Windows and Linux 
# installations carelessly.
if os.path.exists('build'):
    distutils.dir_util.remove_tree('build')

install_req = ['scipy', 'ipython', 'matplotlib', 'numpy', 
               'traits', 'traitsui', 'scikit_learn', ]

def are_we_building4linux():
    for arg in sys.argv:
        if 'wininst' in arg:
            return True
scripts = ['bin/analyzarr',]

if are_we_building4linux() or os.name in ['nt','dos']:
    # In the Windows command prompt we can't execute Python scripts 
    # without a .py extension. A solution is to create batch files
    # that runs the different scripts.
    # (code adapted from scitools)
    scripts.extend(('bin/win_post_installation.py',
                   'bin/install_analyzarr_here.py',
                   'bin/uninstall_analyzarr_here.py'))
    batch_files = []
    for script in scripts:
        batch_file = os.path.splitext(script)[0] + '.bat'
        f = open(batch_file, "w")
        f.write('set path=%~dp0;%~dp0\..\;%PATH%\n')
        if script == 'bin/analyzarr':
            f.write('start pythonw "%%~dp0\%s" --ipython_args qtconsole %%*\n' % os.path.split(script)[1])
        else:
            f.write('python "%%~dp0\%s" %%*\n' % os.path.split(script)[1])
        f.close()
        batch_files.append(batch_file)
    scripts.extend(batch_files)
    
version = Release.version
setup(
    name = "analyzarr",
    package_dir = {'analyzarr': 'analyzarr'},
    version = version,
    packages = ['analyzarr', 'analyzarr.io_plugins', 
                'analyzarr.drawing', 'analyzarr.learn', 'analyzarr.signals',  'analyzarr.tests',
                'analyzarr.tests.io', ],
    requires = install_req,
    scripts = scripts,
    package_data = 
    {
        'analyzarr': 
            [   'bin/*.py',
                'ipython_profile/*',
                'data/*.m', 
                'data/*.csv',
                'data/*.tar.gz',
				'data/analyzarr_logo.ico',
		'tests/io/dm3_1D_data/*.dm3',
		'tests/io/dm3_2D_data/*.dm3',
		'tests/io/dm3_3D_data/*.dm3',
            ],
    },
    author = Release.authors['M_S'][0],
    author_email = Release.authors['M_S'][1],
    maintainer = 'Michael Sarahan',
    maintainer_email = 'msarahan@gmail.com',
    description = Release.description,
    long_description = open('README.txt').read(),
    license = Release.license,
    platforms = Release.platforms,
    url = Release.url,
    #~ test_suite = 'nose.collector',
    keywords = Release.keywords,
    classifiers = [
        "Programming Language :: Python :: 2.7",
        "Development Status :: 4 - Beta",
        "Environment :: Console",
        "Intended Audience :: Science/Research",
        "License :: OSI Approved :: GNU General Public License v3 (GPLv3)",
        "Natural Language :: English",
        "Operating System :: OS Independent",
        "Topic :: Scientific/Engineering",
        "Topic :: Scientific/Engineering :: Physics",
        ],
    )
