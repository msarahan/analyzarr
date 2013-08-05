# -*- coding: utf-8 -*-
"""
Copyright (c) 2012, Michael Sarahan
All rights reserved.

Redistribution and use in source and binary forms, with or without modification, are permitted provided that the following conditions are met:

    Redistributions of source code must retain the above copyright notice, this list of conditions and the following disclaimer.
    Redistributions in binary form must reproduce the above copyright notice, this list of conditions and the following disclaimer in the documentation and/or other materials provided with the distribution.

THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS "AS IS" AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE ARE DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT HOLDER OR CONTRIBUTORS BE LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES; LOSS OF USE, DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND ON ANY THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE OF THIS SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.
"""


from setuptools import setup

import distutils.dir_util

import os

from distutils.extension import Extension
from Cython.Distutils import build_ext

import numpy as np

import analyzarr.Release as Release
# clean the build directory so we aren't mixing Windows and Linux 
# installations carelessly.
if os.path.exists('build'):
    distutils.dir_util.remove_tree('build')

install_req = ['scipy', 'numpy', 'traits', 'chaco>=4.3', 'enaml==0.6.8',
               'cython', 'scikit_learn', 'tables>=3.0']

numpy_include_dir = np.get_include()

peak_finder_cython = Extension(
    'analyzarr.lib.cv.one_dim_findpeaks', 
    sources=['analyzarr/lib/cv/one_dim_findpeaks.pyx'],
    include_dirs=[numpy_include_dir],
    )
    
version = Release.version
setup(
    cmdclass = {'build_ext': build_ext},
    name = "analyzarr",
    package_dir = {'analyzarr': 'analyzarr'},
    version = version,
    packages = ['analyzarr', 'analyzarr.lib', 'analyzarr.lib.mda',
                'analyzarr.lib.io', 'analyzarr.lib.io.libs',
                'analyzarr.lib.cv', 'analyzarr.testing',
                'analyzarr.ui', 'analyzarr.controllers'],
    package_data = {
        'analyzarr' : [ '*.enaml', 'ui/*.enaml',],
        },
    install_requires = install_req,
    scripts = ['bin/analyzarr'],
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
        "Development Status :: 2 - Pre-Alpha",
        "Intended Audience :: Science/Research",
        "Natural Language :: English",
        "Operating System :: OS Independent",
        "Topic :: Scientific/Engineering",
        "Topic :: Scientific/Engineering :: Physics",
        ],
    #ext_modules = [peak_finder_cython,]
    )
