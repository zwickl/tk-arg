#!/usr/bin/env python
import sys
import os.path
import importlib 

from Tkinter import *
from tkinterutils import ArgparseGui
#from ttk import *
from argparse import ArgumentParser

'''Pass any script that uses the argparse ArgumentParser to control command line input.
The below will monkey patch the ArgumentParser.parse_args call that would normally 
process command line input such that it pulls the details of the command line options
out of the ArgumentParser instance and uses them to construct a simple Tk GUI.  
Arguments entered into the GUI are subsequently passed to the original ArgumentParser.parse_args
function and returned.  So, the other script knows nothing about the fact that a GUI was
even used.
'''

#TODO
#Pass name of script and set as title of tk window
#Print program description

#back up the original parse_args function
old_parse_args = ArgumentParser.parse_args

def parse_args(self):
    root = Tk()
    gui = ArgparseGui(self, root, height=768, width=1024)
    root.wait_window(gui.frame)
    if gui.cancelled:
        sys.exit('GUI cancelled ...')
    args = gui.make_commandline_list()
    #print args
    return old_parse_args(self, args)

#do the monkey patch
ArgumentParser.parse_args = parse_args

#By default files can't be imported by path, so need to do this.  There are other
#ways that this could be done besides adding the path to sys.path, but they are 
#a little odd. I suppose that this could import from the wrong location if a python
#file of the same name existed at some location earlier in the path.

execfile(sys.argv[1])

#pth, pyfile = os.path.split(sys.argv[1])
#modname = os.path.splitext(pyfile)[0]
#sys.path.append(pth)
#importlib.import_module(modname)

