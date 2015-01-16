#!/usr/bin/env python
import sys
from argparse import ArgumentParser

from Tkinter import *
from tkarg import ArgparseGui
#from ttk import *

'''Pass any script that uses the argparse ArgumentParser to control command line input.
The below will monkey patch the ArgumentParser.parse_args call that would normally 
process command line input such that it pulls the details of the command line options
out of the ArgumentParser instance and uses them to construct a simple Tk GUI.  
Arguments entered into the GUI are subsequently passed to the original ArgumentParser.parse_args
function and returned.  So, the other script knows nothing about the fact that a GUI was
even used.
'''

#back up the original parse_args function
old_parse_args = ArgumentParser.parse_args

def parse_args(self):
    root = Tk()
    gui = ArgparseGui(self, root, height=768, width=1024)
    root.wait_window(gui.frame)
    if gui.cancelled:
        sys.exit('GUI cancelled ...')
    args = gui.make_commandline_list()
    return old_parse_args(self, args)

#do the monkey patch
ArgumentParser.parse_args = parse_args

#execute the original script
execfile(sys.argv[1])

