#!/usr/bin/env python
import sys
import os
import argparse

parser = argparse.ArgumentParser(description='Example parser for tk-arg GUI demonstration')

parser.add_argument(dest='positional_arg', type=str, 
        help='Positional argument appear as others, indicated as required')

parser.add_argument('-f', '--flag-arg', action='store_const', const=2, default=False, 
        help='Basic flags without arguments appear as checkboxes')

parser.add_argument('-s', '--string-arg', default='default string', type=str, 
        help='String arguments appear as text boxes, already filled with the default value')

parser.add_argument('-c', '--choice-arg', choices=['meow', 'woof', 'moo'], default='moo', 
        help='Arguments with discrete possible values appear as dropdown menus')

file_group = parser.add_argument_group('Argument groups appear as headings over the contained arguments')

file_group.add_argument('-i', '--file-arg', type=file, 
        help='Arguments of type=file or argparse.FileType generate a file chooser button')

file_group.add_argument('-m', '--multifile-arg', type=file, nargs="*", 
        help='Arguments of type=file or argparse.FileType with nargs > 1 generate a multi-file chooser button')

#version action is ignored
parser.add_argument('-v', '--version', action='version', version='1.0')

#this will draw the input to parse from the ArgparseGui, rather than from the command line
options = parser.parse_args()

vdict = vars(options)
wid = max(len(v) for v in vdict.keys())
sys.stdout.write('%*s\t%s\n' % (wid, 'var', 'value'))
for opt, val in vdict.items():
    sys.stdout.write('%*s\t%r\n' % (wid, opt, val))

