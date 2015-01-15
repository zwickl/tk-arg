import sys
from os import devnull
from Tkinter import *
import tkFileDialog
import tkFont
from ttk import *
import argparse
from textwrap import fill
import re
import shlex
import subprocess
from plotutils import ArgparseActionAppendToDefault
from pygot.utils import proportion_type, argparse_bounded_float

'''
***For reference, here is the help on the attributes of the argparse.Action baseclass***

class Action(_AttributeHolder)
 |  Information about how to convert command line strings to Python objects.
 |  
 |  Action objects are used by an ArgumentParser to represent the information
 |  needed to parse a single argument from one or more strings from the
 |  command line. The keyword arguments to the Action constructor are also
 |  all attributes of Action instances.
 |  
 |  Keyword Arguments:
 |  
 |      - option_strings -- A list of command-line option strings which
 |          should be associated with this action.
 |  
 |      - dest -- The name of the attribute to hold the created object(s)
 |  
 |      - nargs -- The number of command-line arguments that should be
 |          consumed. By default, one argument will be consumed and a single
 |          value will be produced.  Other values include:
 |              - N (an integer) consumes N arguments (and produces a list)
 |              - '?' consumes zero or one arguments
 |              - '*' consumes zero or more arguments (and produces a list)
 |              - '+' consumes one or more arguments (and produces a list)
 |          Note that the difference between the default and nargs=1 is that
 |          with the default, a single value will be produced, while with
 |          nargs=1, a list containing a single value will be produced.
 |  
 |      - const -- The value to be produced if the option is specified and the
 |          option uses an action that takes no values.
 |  
 |      - default -- The value to be produced if the option is not specified.
 |  
 |      - type -- A callable that accepts a single string argument, and
 |          returns the converted value.  The standard Python types str, int,
 |          float, and complex are useful examples of such callables.  If None,
 |          str is used.
 |  
 |      - choices -- A container of values that should be allowed. If not None,
 |          after a command-line argument has been converted to the appropriate
 |          type, an exception will be raised if it is not a member of this
 |          collection.
 |  
 |      - required -- True if the action must always be specified at the
 |          command line. This is only meaningful for optional command-line
 |          arguments.
 |  
 |      - help -- The help string describing the argument.
 |  
 |      - metavar -- The name to be used for the option's argument with the
 |          help string. If None, the 'dest' value will be used as the name.
'''


class ArgparseOption(object):
    '''Base class for graphical representation of argparse command line arguments.
    Derived classes handle specific argument types, e.g. strings, choices, etc.
    '''
    def __init__(self, option, **kwargs):
        '''
        Configure the basics of this gui item.
        
        option - instance of a class derived from argparse Action

        The output_arg is an important thing to set up here.  It will be part of the
        string that is passed to ArgumentParser.parse_args after the gui is closed.
        #Use the last listed flag, which is likely to be the more descriptive long one.
        #There will be no option_strings for a positional arg
        '''
        self.option = option

        if option.option_strings:
            self.output_arg = option.option_strings[-1]
        else:
            self.output_arg = None
       
        self.return_string = []
        
        self.hide = 'HIDE' in option.help
        
        self.nargs = option.nargs

    def extract_label_from_help(self):
        help_string = re.sub('[(]default [)]', '', self.option.help).strip()
        if help_string:
            self.label_string = help_string
        else:
            self.label_string = re.sub('--', '', self.option.option_strings[-1])

    def position(self, row, col, padx=10, pady=2):
        next_row = row + 1
        self.label.grid(row=row, column=col, padx=padx, pady=pady, sticky='W')
        self.widget.grid(row=row, column=col + 1, padx=padx, pady=pady, sticky='W')
        if hasattr(self, 'update_box'):
            self.update_box.grid(row=row + 1, column=col, padx=padx, sticky='W', columnspan=2)
            next_row += 1
        return next_row 


class ArgparseBoolOption(ArgparseOption):
    '''A boolean True/False argument.  Will be represented in the gui with a Checkbutton.
    
    This gets a little confusing, because in ArgumentParser.add_argument it is possible 
    to set the argument action as either store_true or store_false, which sets the 
    corresponding variable accordingly if the flag appears.  Presumably the default is 
    set to the opposite setting.  I never do store_false, because I find it confusing, 
    and its possible to always use store_true anyway.  e.g., For a flag that suppresses 
    output I'd make an argument --suppress-output that sets parser namespace variable
    suppress_output to True, rather than the same flag setting a variable called 'output'
    to false if it appears.  
    
    In the gui I'm capturing this by having the checkbutton checked meaning the same thing
    as the flag appearing, i.e., True or False depending on the initial setup.  You could
    also try to map it by having a store_false action represented by a checkbutton that 
    defaults to checked, but that gets confusing and generally won't work with argument
    names or help strings.
    '''

    def __init__(
            self, 
            option, 
            frame, 
            label_width=100):
        
        ArgparseOption.__init__(self, option)
       
        #using Variable rather than IntVar since it allows a default of None
        self.var = Variable()
        self.var.set(option.default)

        if not self.hide:
            self.extract_label_from_help()

            self.label = Label(frame, text=fill(self.label_string, label_width))
            
            if isinstance(option, argparse._StoreTrueAction):
                self.widget = Checkbutton(frame, variable=self.var, onvalue=1, offvalue=0)
            elif isinstance(option, argparse._StoreFalseAction):
                self.widget = Checkbutton(frame, variable=self.var, onvalue=0, offvalue=1)
            else: 
                #I think that I found some case where it is possible for the action to be
                #neither store_true nor store_false
                self.widget = Checkbutton(frame, variable=self.var, onvalue=1, offvalue=0)
            
    def make_string(self):
        if bool(self.var.get()):
            return [ self.output_arg ]
        else:
            return []


class ArgparseStringOption(ArgparseOption):
    def __init__(
            self, 
            option, 
            frame, 
            label_width=100):

        ArgparseOption.__init__(self, option)
        self.var = StringVar()
        self.widget = Entry(frame, textvariable=self.var, width=10)

        if not self.hide:
            self.extract_label_from_help()
            
            req_string = 'REQ: ' if option.required else ''
            self.label_string = req_string + self.label_string
            
            if isinstance(self.nargs, int):
                self.label_string += ' (%d values expected)' % self.nargs
            elif self.nargs in [ '*', '+' ]:
                self.label_string += ' (multiple values allowed)' % self.nargs

            self.label = Label(frame, text=fill(self.label_string, label_width))
        
        if option.default:
            if isinstance(option.default, list):
                self.widget.insert(0, ' '.join([str(val) for val in option.default]))
            else:
                self.widget.insert(0, str(option.default))

    def make_string(self):
        if self.var.get():
            #print self.output_arg, self.var.get(), type(self.var.get()), self.nargs
            self.return_string.append(self.output_arg)
            
            if self.nargs and (self.nargs in [ '*', '+' ] or self.nargs > 1):
                #shlex.split here properly leaves quoted strings unsplit
                splt = shlex.split(self.var.get())
                #this is an annoying special case, where a leading "-" in an argument has to 
                #have double quotes explicitly embedded in the string
                for num, s in enumerate(splt):
                    if s[0] == '-':
                        splt[num] = '"' + s + '"'

                self.return_string.extend(splt)
            else:
                self.return_string.append(self.var.get())
        return self.return_string


class ArgparseOptionMenuOption(ArgparseOption):
    def __init__(
            self, 
            option, 
            frame, 
            label_width=100):
        
        ArgparseOption.__init__(self, option)
        
        self.var = StringVar()
        self.var.set(option.default)

        #OptionMenu signature is this:
        #__init__(self, master, variable, value, *values, **kwargs)
        #where variable is "the resource textvariable", and value is the 
        #default value
        self.widget = OptionMenu(frame, self.var, option.choices[0], *option.choices)

        self.extract_label_from_help()
        req_string = 'REQ: ' if option.required else ''
        self.label_string = req_string + self.label_string

        self.label = Label(frame, text=fill(self.label_string, label_width))

    def make_string(self):
        if self.var.get():
            self.return_string.append(self.output_arg)
            self.return_string.append(self.var.get())
        return self.return_string


class ArgparseFileOption(ArgparseOption):
    def __init__(
            self, 
            option, 
            frame, 
            display_filenames=True,
            label_width=100):
        
        ArgparseOption.__init__(self, option)
        self.label_width = label_width

        self.label = Label(frame, text=fill(option.help, self.label_width))
        if option.type and hasattr(option.type, "_mode"):
            #a mode would be here if the option is specified a file to argparse, rather than the path to a file
            if 'r' in option.type._mode:
                if self.nargs and (self.nargs in [ '*', '+' ] or self.nargs > 1):
                    self.widget = Button(frame, text='OPEN', command=self.open_multiple_files_dialog)
                else:
                    self.widget = Button(frame, text='OPEN', command=self.open_file_dialog)
            elif 'w' in option.type._mode:
                self.widget = Button(frame, text='OPEN', command=self.output_file_dialog)
        else:
            #this is obviously a total hack, and depends on the "destination" variable name assigned in argparse
            if 'out' in option.dest.lower():
                self.widget = Button(frame, text='SAVE AS', command=self.output_file_dialog)
            else:
                if self.nargs and (self.nargs in [ '*', '+' ] or self.nargs > 1):
                    self.widget = Button(frame, text='OPEN', command=self.open_multiple_files_dialog)
                else:
                    self.widget = Button(frame, text='OPEN', command=self.open_file_dialog)

        self.update_box = Label(frame, text=fill('  Files chosen: ', self.label_width), anchor='w', foreground='red')

        self.var = None

    def open_file_dialog(self):
        self.var = tkFileDialog.askopenfilename()
        self.update_box.config(text=fill('  File chosen: %s ' % self.var, self.label_width+50), foreground='red')

    def open_multiple_files_dialog(self):
        self.var = tkFileDialog.askopenfilenames()
        self.update_box.config(text=fill('  Files chosen: %s ' % ' '.join(self.var), self.label_width+50), foreground='red')

    def output_file_dialog(self):
        self.var = tkFileDialog.asksaveasfilename()
        self.update_box.config(text=fill('  File chosen: %s ' % self.var, self.label_width+50), foreground='red')

    def make_string(self):
        if self.var:
            if self.output_arg:
                self.return_string.append(self.output_arg)
            #self.var is actually a tuple here in the case of multiple filenames,
            #but may be just a string otherwise
            if isinstance(self.var, tuple):
                self.var = list(self.var)
            if isinstance(self.var, list):
                self.return_string.extend(self.var)
            else:
                self.return_string.append(self.var)
        return self.return_string


class ArgparseGui(object):
    def __init__(
            self, 
            parser, 
            tk=None, 
            height=720, 
            width=1152,
            widgets_per_column=18,
            widget_padx=10,
            widget_pady=4,
            label_width=65,
            destroy_when_done=True,
            output_frame=False,
            graphics_window=False):

        self.tk = tk or Tk()

        ###############
        #adapted from http://stackoverflow.com/questions/3085696/adding-a-scrollbar-to-a-grid-of-widgets-in-tkinter
        
        #This canvas object will be the entire toplevel window.  The scrollbars will be attached to it, a window
        #will be made (which is what allows other widgets to be embedded in a canvas), a frame will be embedded 
        #in the window to actually hold all other widgets.
        self.canvas = Canvas(self.tk, height=height, width=width, borderwidth=0, background="#ffffff")
        
        self.vsb = Scrollbar(self.tk, orient="vertical", command=self.canvas.yview)
        self.canvas.configure(yscrollcommand=self.vsb.set)
        self.vsb.pack(side="right", fill="y")

        self.hsb = Scrollbar(self.tk, orient="horizontal", command=self.canvas.xview)
        self.canvas.configure(xscrollcommand=self.hsb.set)
        self.hsb.pack(side="bottom", fill="x")
        
        #after this call the toplevel window with scrollbars and of the correct size will exist
        self.canvas.pack(side="left", fill="both", expand=True)
        
        self.frame = Frame(self.canvas)
        #the window is a slot in the canvas (the size of the canvas) to hold a single other widget, which will be the frame
        self.canvas.create_window((4, 4), window=self.frame, anchor="nw", tags="self.frame")
        
        #this will allow the scrollbars to adjust if the window is manually resized
        self.frame.bind("<Configure>", self.OnFrameConfigure)
        ################

        self.option_list = []
        #bizarrely, options appear once for each potential flag (i.e. short and long), so need to keep track
        seen_options = []

        column_offset = 0
        row = 0
        
        #I don't know why I did this, but probably had a reason.  Rather strange.
        group_list = [parser._action_groups[0]]
        if len(parser._action_groups) > 2:
            group_list.extend(parser._action_groups[2:])
        group_list.append(parser._action_groups[1])
        
        #Loop over the argparse argument groups
        for group in group_list:
            if len(group._group_actions):
                group_title_displayed = False
                #Loop over the individual arguments in this group
                for option in group._group_actions:
                    if option not in seen_options:
                        seen_options.append(option)
                        
                        if not group_title_displayed:
                            #Start in a new column if necessary
                            if row + len(group._group_actions) > widgets_per_column and row > widgets_per_column - 3:
                                row = 0
                                column_offset += 2
                            if group.title != "optional arguments":
                                display_title = group.title.upper()
                            else:
                                display_title = "Misc. options".upper()
                            #Place a centered label for the group name
                            Label(self.frame, text=fill(display_title, label_width), font=tkFont.Font(size=14, weight='bold')).grid(row=row, column=column_offset, columnspan=2)
                            group_title_displayed = True
                            row += 1
                       
                        #a flag, which appears as a checkbox
                        if isinstance(option, (argparse._StoreTrueAction, argparse._StoreFalseAction)):
                            gui_option = ArgparseBoolOption(option, self.frame, label_width=label_width)
                        
                        #some variable(s) to store
                        elif isinstance(option, (argparse._StoreAction, argparse._AppendAction)):
                            #with fixed choices, appears as a select box
                            if option.choices:
                                gui_option = ArgparseOptionMenuOption(option, self.frame, label_width=label_width)
                            
                            #hack to add a file chooser widget if 'file' appears in the option name, which would be considered a string otherwise
                            elif (isinstance(option.type, type(str)) or option.type is None) and 'file' in option.dest.lower():
                                gui_option = ArgparseFileOption(option, self.frame, label_width=label_width)
                            
                            #if no type is specified to ArgumentParser.add_argument then the default is str
                            #this will appear as a text entry box
                            elif option.type is None or isinstance(option.type, (type(str), type(proportion_type), type(argparse_bounded_float))):
                                gui_option = ArgparseStringOption(option, self.frame, label_width=label_width)
                           
                            #if the actual argparse.FileType is specified in the type, in which case it is usually automatically opened during parse_args
                            elif isinstance(option.type, argparse.FileType):
                                gui_option = ArgparseFileOption(option, self.frame, label_width=label_width)
                            
                            else:
                                sys.exit("unknown Store action: %s\n" % type(option))
                        
                        #my derived action, same as append, but doesn't overwrite specified defaults (good for kwargs)
                        elif isinstance(option, ArgparseActionAppendToDefault):
                            gui_option = ArgparseStringOption(option, self.frame, label_width=label_width)
                        #ignore help
                        elif isinstance(option, argparse._HelpAction):
                            continue
                        else:
                            sys.exit("unknown action: %s\n" % option)
                        
                        row = gui_option.position(row, column_offset)
                        
                        if row >= widgets_per_column:
                            row = 0
                            column_offset += 2

                        self.option_list.append(gui_option)

        #buttons appear below the other widgets
        self.button_frame = Frame(self.frame)
        self.button_frame.grid(row=widgets_per_column+1, column=0)
        
        if destroy_when_done:
            Button(self.button_frame, text='DONE', command=self.done).grid(row=0, column=0)
        else:
            Button(self.button_frame, text='RUN', command=self.submit).grid(row=0, column=0)
        Button(self.button_frame, text='CANCEL/QUIT', command=self.cancel).grid(row=0, column=1)

        #a window to spit out text
        if output_frame:
            self.results = Text(self.frame, width=label_width)
            self.results.grid(row=0, column = column_offset + 2, rowspan=widgets_per_column, padx=widget_padx, sticky='W')
        else:
            self.results = None

        #a window to spit out graphics
        if graphics_window:
            #self.sort_button = Button(self.frame, text='SORT')
            #self.sort_button.grid(row=widgets_per_column+2, column=0, padx=widget_padx)
            self.graphics_canvas = Canvas(self.frame, width=width, height=50)
            self.graphics_canvas.grid(row=widgets_per_column+2, column=0, padx=widget_padx, pady=widget_pady, columnspan=4, rowspan=2, sticky='W')

        self.cancelled = False

        self.bring_to_front()

    def output_result(self, text):
        if self.results:
            self.results.insert(END, text)

    def make_commandline_list(self):
        return_list = []
        for option in self.option_list:
            return_list.extend(option.make_string())
        return return_list

    def submit(self):
        self.frame.quit()

    def done(self):
        self.frame.destroy()

    def cancel(self):
        self.frame.quit()
        self.frame.destroy()
        #self.frame.quit()
        self.cancelled = True

    def OnFrameConfigure(self, event):
        '''Reset the scroll region to encompass the inner frame'''
        self.canvas.configure(scrollregion=self.canvas.bbox("all"))

    def bring_to_front(self):
        #Need to do this on OS X to bring window to front, otherwise root.lift() should work
        if 'darwin' in sys.platform.lower():
            try:
                #this can give odd non-critical error messages from the OS, so send stderr to devnull
                retcode = subprocess.call(shlex.split('''/usr/bin/osascript -e 'tell app "Finder" to set frontmost of process "Python" to true' '''), stderr=open(devnull, 'wb'))
            except:
                #didn't manage to get window to front, but don't worry about it
                pass
        else:
            self.tk.lift()


