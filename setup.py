#! /usr/bin/env python

##############################################################################
##  tk-arg - Automatically generate a tkinter gui from an argparse script
##
##  Copyright 2015 Derrick J. Zwickl
##  All rights reserved.
##
##  See "LICENSE.txt" for terms and conditions of usage.
##
##############################################################################

import sys
import os

#HACK OF DENDROPY setup.py BELOW

###############################################################################
# setuptools/distutils/etc. import and configuration

try:
    import ez_setup
    try:
        ez_setup_path = " ('" + os.path.abspath(ez_setup.__file__) + "')"
    except OSError:
        ez_setup_path = ""
    sys.stderr.write("using ez_setup%s\n" %  ez_setup_path)
    ez_setup.use_setuptools()
    import setuptools
    try:
        setuptools_path = " ('" +  os.path.abspath(setuptools.__file__) + "')"
    except OSError:
        setuptools_path = ""
    sys.stderr.write("using setuptools%s\n" % setuptools_path)
    from setuptools import setup, find_packages
except ImportError, e:
    sys.stderr.write("using distutils\n")
    from distutils.core import setup
    sys.stderr.write("using canned package list\n")
    PACKAGES = ['tkarg']
    EXTRA_KWARGS = {}
else:
    sys.stderr.write("searching for packages\n")
    PACKAGES = find_packages()
    EXTRA_KWARGS = dict(include_package_data=True)

PACKAGE_DIRS = [p.replace(".", os.path.sep) for p in PACKAGES]
PACKAGE_INFO = [("% 40s : %s" % p) for p in zip(PACKAGES, PACKAGE_DIRS)]
sys.stderr.write("packages identified:\n%s\n" % ("\n".join(PACKAGE_INFO)))
ENTRY_POINTS = {}

###############################################################################
# Script paths

SCRIPT_SUBPATHS = [
    ['scripts', 'tkgui.py']
]
SCRIPTS = [os.path.join(*i) for i in SCRIPT_SUBPATHS]
sys.stderr.write("\nscripts identified: %s\n" % "\n\t".join(SCRIPTS))

###############################################################################
# setuptools/distuils command extensions

try:
    from setuptools import Command
except ImportError:
    sys.stderr.write("setuptools.Command could not be imported: setuptools extensions not available\n")
else:
    sys.stderr.write("setuptools command extensions are available\n")
    command_hook = "distutils.commands"
    ENTRY_POINTS[command_hook] = []

###############################################################################
# Main setup

__version__ = 1.0
EXTRA_KWARGS["zip_safe"] = True

### compose long description ###
long_description = open('README.txt').read()

setup(name='tk-arg',
      version=__version__,
      author='Derrick Zwickl',
      author_email='zwickl@email.arizona.edu',
      url='https://github.com/zwickl/tk-arg',
      description='Automatically generate a tkinter gui from an argparse script',
      license='GPL3',
      packages=PACKAGES,
      package_dir=dict(zip(PACKAGES, PACKAGE_DIRS)),
      scripts = SCRIPTS,
      long_description=long_description,
      entry_points = ENTRY_POINTS,
      classifiers = [
            "Environment :: Console",
            "Intended Audience :: Developers",
            "Intended Audience :: Science/Research",
            "License :: OSI Approved :: GPL3",
            "Natural Language :: English",
            "Operating System :: OS Independent",
            "Programming Language :: Python",
            "Topic :: Scientific/Engineering :: Bio-Informatics",
            ],
      keywords='phylogenetics phylogeny phylogenies phylogenomics evolution evolutionary biology systematics phyloinformatics bioinformatics',
      **EXTRA_KWARGS
      )
