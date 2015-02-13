import sys
from os import devnull
from Tkinter import *
import tkFileDialog
import tkFont
#importing ttk here overrides some widget definitions from Tkinter, which is fine
#except bizarre things like specifying background= in constructors doesn't work
#from ttk import *
import argparse
from textwrap import fill
import re
import shlex
import subprocess


class ArgparseActionAppendToDefault(argparse.Action):
    '''Normally defaults can be set on argparse options, but will be overridden if the 
    argument appears on the command line.  This will allow arguments passed on the
    command line to simply be appended to the default list.  This would mainly be 
    used for kwargs specified on the command line and a PlottingArgumentParser
    instantiated with some kwargs set as defaults. Because the values that would
    come from the commandline appear later, they should trump earlier ones in the
    prepare_plot_kwargs function.
    '''
    def __call__(self, parser, namespace, values, option_string=None):
        #print '%r %r %r' % (self.dest, self.default, values)
        if not hasattr(self, 'default'):
            raise ValueError('only makes sense to call AppendToDefaultArgparseAction \
                    when default value to argument is defined')
        if not isinstance(self.default, list):
            raise ValueError('only makes sense to call AppendToDefaultArgparseAction \
                    when defaults are in a list')
        if isinstance(values, str):
            values = values.split()

        setattr(namespace, self.dest, self.default + values)


def argparse_bounded_float(min_val=0.0, max_val=1.0):
    '''Closure-based function for use in type and bound checking, specified as a type= argument in argparse.add_argument().
    It defaults to checking for a proportion, but any bounds can be passed.
    On failure raises an ArgumentTypeError, defined by argparse.
    >>> f = argparse_bounded_float()
    >>> f(1.0)
    1.0
    >>> f = argparse_bounded_float()
    >>> f('1.1')
    Traceback (most recent call last):
    ...
    ArgumentTypeError: value 1.100000 must be between 0.00 and 1.00
    >>> f = argparse_bounded_float(max_val=2.0)
    >>> f('1.9')
    1.9
    '''
    def func(string):
        value = float(string)
        if value < min_val or value > max_val:
            mess = 'value %f must be between %.2f and %.2f' % (value, min_val, max_val)
            raise ArgumentTypeError(mess)
        return value
    
    return func


def proportion_type():
    '''Limited version of argparse_bounded_float for compatibility with legacy code.'''
    return argparse_bounded_float()


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


#class ArgparseOption(object):
class ArgparseOption(Frame):
    '''Base class for graphical representation of argparse command line arguments.
    Derived classes handle specific argument types, e.g. strings, choices, etc.
    '''
    def __init__(self, tk_parent, option, **kwargs):
        '''
        Configure the basics of this gui item.
        
        option - instance of a class derived from argparse Action

        The output_arg is an important thing to set up here.  It will be part of the
        string that is passed to ArgumentParser.parse_args after the gui is closed.
        #Use the last listed flag, which is likely to be the more descriptive long one.
        #There will be no option_strings for a positional arg
        '''
        Frame.__init__(self, tk_parent)

        self.option = option

        if option.option_strings:
            self.output_arg = option.option_strings[-1]
        else:
            self.output_arg = None
       
        self.return_string = []
        
        self.omit = 'HIDE' in option.help
        
        self.nargs = option.nargs

        self.dependent_options = []
        self.depends_on = 0

    def extract_label_from_help(self):
        '''Extract a reasonable label.
        '''
        help_string = re.sub('[(]default [)]', '', self.option.help).strip()
        if help_string:
            self.label_string = help_string
        else:
            self.label_string = re.sub('--', '', self.option.option_strings[-1])

    def position(self, row, col, padx=10, pady=2):
        '''Position the widget, and the return the correct row for the next widget
        to be placed at
        '''
        next_row = row + 1
        self.label.grid(row=row, column=col, padx=padx, pady=pady, sticky='W')
        self.widget.grid(row=row, column=col + 1, padx=padx, pady=pady, sticky='N')
        #an update box is used e.g. to show the path of a text file that has been chosen
        if hasattr(self, 'update_box'):
            self.update_box.grid(row=row + 1, column=col, padx=padx, sticky='W', columnspan=2)
            next_row += 1
        
        self.columnconfigure(0, minsize=450)
        self.columnconfigure(1, minsize=150)
        self.grid()
        return next_row 

    def grey_out(self):
        '''Disable both the label and widget assigned to a particular option, which 
        by default means to grey it out
        '''
        if not hasattr(self, 'widget'):
            sys.exit('ERROR: grey_out called before ArgparseOption configured\n')
        for child in [ self.nametowidget(ch) for ch in self.winfo_children() ]:
            child.config(state=DISABLED)

    def activate(self):
        '''Return the label and widget for an option back to the normal state from 
        the disabled state. If this option is dependent on multiple others, there 
        is a sort of reference counting that is does to ensure the proper number 
        of dependencies are met.
        '''
        self.depends_on -= 1
        if not self.depends_on:
            for child in [ self.nametowidget(ch) for ch in self.winfo_children() ]:
                child.config(state=NORMAL)

    def register_dependency(self, dep):
        '''Add dep to a list of other options that depend on this option, and grey
        it out.  Also increment the dependency reference count of the dependent 
        option.
        '''
        self.dependent_options.append(dep)
        dep.grey_out()
        dep.depends_on += 1

    def activate_dependencies(self):
        '''Tell all depenent options that this dependency has been met, decrementing 
        its dependency counter, and possibly fully activating it.
        '''
        for dep in self.dependent_options:
            dep.activate()
       

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
            tk_parent, 
            label_width=60):
        
        ArgparseOption.__init__(self, tk_parent, option)

        #using Variable rather than IntVar since it allows a default of None
        self.var = Variable()
        self.var.set(option.default)

        if not self.omit:
            self.extract_label_from_help()

            self.label = Label(self, text=fill(self.label_string, label_width))
            
            if isinstance(option, argparse._StoreTrueAction):
                self.widget = Checkbutton(self, variable=self.var, onvalue=1, offvalue=0)
            elif isinstance(option, argparse._StoreFalseAction):
                self.widget = Checkbutton(self, variable=self.var, onvalue=0, offvalue=1)
            else: 
                #I think that I found some case where it is possible for the action to be
                #neither store_true nor store_false
                self.widget = Checkbutton(self, variable=self.var, onvalue=1, offvalue=0)
         

    def make_string(self):
        if bool(self.var.get()):
            return [ self.output_arg ]
        else:
            return []


class ArgparseStringOption(ArgparseOption):
    def __init__(
            self, 
            option, 
            tk_parent, 
            label_width=60):

        ArgparseOption.__init__(self, tk_parent, option)
        self.var = StringVar()
        self.widget = Entry(self, textvariable=self.var, width=10)

        if not self.omit:
            self.extract_label_from_help()
            
            req_string = 'REQ: ' if option.required else ''
            self.label_string = req_string + self.label_string
            
            if isinstance(self.nargs, int):
                self.label_string += ' (%d values expected)' % self.nargs
            elif self.nargs in [ '*', '+' ]:
                self.label_string += ' (multiple values allowed)'

            self.label = Label(self, text=fill(self.label_string, label_width))
        
        if option.default:
            if isinstance(option.default, list):
                self.widget.insert(0, ' '.join([str(val) for val in option.default]))
            else:
                self.widget.insert(0, str(option.default))

    def make_string(self):
        if self.var.get():
            #output_arg is None for positional arg
            if self.output_arg is not None:
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
            tk_parent, 
            label_width=60):
        
        ArgparseOption.__init__(self, tk_parent, option)
        
        self.var = StringVar()
        self.var.set(option.default)

        #OptionMenu signature is this:
        #__init__(self, master, variable, value, *values, **kwargs)
        #where variable is "the resource textvariable", and value is the default value
        self.widget = OptionMenu(self, self.var, option.choices[0], *option.choices[1:])

        self.extract_label_from_help()
        req_string = 'REQ: ' if option.required else ''
        self.label_string = req_string + self.label_string

        self.label = Label(self, text=fill(self.label_string, label_width))

    def make_string(self):
        if self.var.get():
            self.return_string.append(self.output_arg)
            self.return_string.append(self.var.get())
        return self.return_string


class ArgparseFileOption(ArgparseOption):
    def __init__(
            self, 
            option, 
            tk_parent, 
            display_filenames=True,
            label_width=60):
        
        ArgparseOption.__init__(self, tk_parent, option)
        self.label_width = label_width

        self.label = Label(self, text=fill(option.help, self.label_width))
        if option.type and hasattr(option.type, "_mode"):
            #a mode would be here if the option is specified a file to argparse, rather than the path to a file
            if 'r' in option.type._mode:
                if self.nargs and (self.nargs in [ '*', '+' ] or self.nargs > 1):
                    self.widget = Button(self, text='OPEN', command=self.open_multiple_files_dialog)
                else:
                    self.widget = Button(self, text='OPEN', command=self.open_file_dialog)
            elif 'w' in option.type._mode:
                self.widget = Button(self, text='OPEN', command=self.output_file_dialog)
        else:
            #this is obviously a total hack, and depends on the "destination" variable name assigned in argparse
            if 'out' in option.dest.lower():
                self.widget = Button(self, text='SAVE AS', command=self.output_file_dialog)
            else:
                if self.nargs and (self.nargs in [ '*', '+' ] or self.nargs > 1):
                    self.widget = Button(self, text='OPEN', command=self.open_multiple_files_dialog)
                else:
                    self.widget = Button(self, text='OPEN', command=self.open_file_dialog)

        if self.nargs and (self.nargs in [ '*', '+' ] or self.nargs > 1):
            fstr = 'Files'
        else:
            fstr = 'File'

        self.update_box = Label(self, text=fill('  %s chosen: ' % fstr, self.label_width), anchor='w', foreground='red')

        self.var = None

    def open_file_dialog(self):
        self.var = tkFileDialog.askopenfilename()
        self.update_box.config(text=fill('  File chosen: %s ' % self.var, self.label_width+50), foreground='red')
        self.activate_dependencies()

    def open_multiple_files_dialog(self):
        self.var = tkFileDialog.askopenfilenames()
        self.update_box.config(text=fill('  Files chosen: %s ' % ' '.join(self.var), self.label_width+50), foreground='red')
        self.activate_dependencies()

    def output_file_dialog(self):
        self.var = tkFileDialog.asksaveasfilename()
        self.update_box.config(text=fill('  File chosen: %s ' % self.var, self.label_width+50), foreground='red')
        self.activate_dependencies()

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


class ArgparseOptionGroup(Frame):
    def __init__(self, 
            tk_parent, 
            group,
            widget_padx=10,
            widget_pady=4,
            label_width=60):
      
        #ArgparseGui
            #column frame
                #self (group_frame)
                #   group_title_frame
                #       title_label
                #       hide_button
                #   options_frame
                #       each option
                #           label
                #           widget
                #           (other, e.g. update box)

        column_offset = 0

        #self.tk_parent = tk_parent
        Frame.__init__(self, tk_parent)
        self.options = {}
        self.num_rows = 0

        if group.title != "optional arguments":
            self.display_title = group.title.upper()
        else:
            #This is for the optional group, the default group for arguments
            self.display_title = "Misc. options".upper()
        #Put the group label and hide widget in a single frame here
        self.group_title_frame = Frame(self)
        Label(self.group_title_frame, 
                width=int(label_width*0.7),
                text=fill(self.display_title, label_width*0.7), 
                font=tkFont.Font(size=14, weight='bold')).grid(row=self.num_rows, column=column_offset, columnspan=1)
        #hide button is created here for simplicity, but may be removed if specified in gui_config
        self.hide_button = Button(self.group_title_frame, text='HIDE', command=self.flip_hidden_state)
        self.hide_button.grid(row=self.num_rows, column=1, sticky=N)
        self.num_rows += 1
        self.group_title_frame.grid()
        self.group_title_frame.columnconfigure(0, minsize=450)
        self.group_title_frame.columnconfigure(1, minsize=150)

        positional_num = 0
        seen_options = []
        self.options_frame = Frame(self)
        #Loop over the individual arguments in this group
        for option in group._group_actions:
            if option not in seen_options:
                seen_options.append(option)
                
                #a flag, which appears as a checkbox
                if isinstance(option, (argparse._StoreTrueAction, argparse._StoreFalseAction, argparse._StoreConstAction)):
                    gui_option = ArgparseBoolOption(option, self.options_frame, label_width=label_width)
               
                #some variable(s) to store
                elif isinstance(option, (argparse._StoreAction, argparse._AppendAction)):
                    #with fixed choices, appears as a select box
                    if option.choices:
                        gui_option = ArgparseOptionMenuOption(option, self.options_frame, label_width=label_width)
                    
                    #hack to add a file chooser widget if 'file' appears in the option name, which would be considered a string otherwise
                    elif option.type in [str, None] and 'file' in option.dest.lower():
                        gui_option = ArgparseFileOption(option, self.options_frame, label_width=label_width)
                    
                    #if no type is specified to ArgumentParser.add_argument then the default is str
                    #this will appear as a text entry box
                    elif option.type in [None, str, float, int, type(proportion_type), type(argparse_bounded_float)]:
                        gui_option = ArgparseStringOption(option, self.options_frame, label_width=label_width)
                   
                    #if the actual argparse.FileType is specified in the type, in which case it is usually automatically opened during parse_args
                    elif option.type in [argparse.FileType,  file]:
                        gui_option = ArgparseFileOption(option, self.options_frame, label_width=label_width)
                   
                    else:
                        sys.exit("unknown Store action: %s (%s)\n" % (type(option), option.dest))
                
                #my derived action, same as append, but doesn't overwrite specified defaults (good for kwargs)
                elif isinstance(option, ArgparseActionAppendToDefault):
                    gui_option = ArgparseStringOption(option, self.options_frame, label_width=label_width)
                #ignore help
                elif isinstance(option, (argparse._HelpAction, argparse._VersionAction)):
                    continue
                else:
                    sys.exit("unknown action: %s\n" % option)
               
                self.num_rows = gui_option.position(self.num_rows, column_offset)

                if gui_option.option.option_strings:
                    self.options[gui_option.option.option_strings[-1]] = gui_option
                else:
                    self.options['positional%d' % positional_num] = gui_option
                    positional_num += 1
                
            self.options_frame.grid()

            self.hidden = False
            if hasattr(group, 'gui_config'):
                self.config(**group.gui_config)
            else:
                self.config()
    
    def position(self, row, col, padx=10, pady=2):
        self.grid(row=row, column=col, padx=padx, pady=pady, sticky='N')
        return self.num_rows

    def hide(self):
        self.hidden = True
        self.options_frame.grid_remove()

    def unhide(self):
        self.hidden = False
        self.options_frame.grid()

    def flip_hidden_state(self):
        if self.hidden:
            self.unhide()
            self.hide_button.config(text='HIDE')
        else:
            self.hide()
            self.hide_button.config(text='UNHIDE')

    def config(self, **kwargs):
        if not hasattr(self, 'gui_config'):
            self.gui_config = {
                    'allow_hide': False,
                    'start_hidden': False
                    }
        self.gui_config.update(kwargs)
        for key, val in kwargs.iteritems():
            self.gui_config[key] = val

        if self.gui_config['start_hidden']:
            self.hide()
        elif self.gui_config['allow_hide'] is False:
            self.hide_button.grid_remove()
            

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
            label_width=60,
            destroy_when_done=True,
            output_frame=False,
            graphics_window=False):

        self.tk = tk or Tk()
        self.tk.title(parser.description or parser.prog)

        auto_size = False
        if auto_size:
            width = self.tk.winfo_screenwidth() * 0.9
            height = self.tk.winfo_screenheight() * 0.85

        #this call is currently required, so has side effects besides making the scrollbars
        self.AddScrollbars(height, width)

        #start collecting the options
        self.option_list = {}

        group_row, option_row = 0, 0
        max_row, max_col = 0, 0
        
        #first group is positional, second is optional, then any user defined groups
        #optional group includes any flags not explictly placed in a group
        #this reorders them such that the optional group will appear last below
        group_list = [parser._action_groups[0]]
        if len(parser._action_groups) > 2:
            group_list.extend(parser._action_groups[2:])
        group_list.append(parser._action_groups[1])
       
        positional_num = 1
        #Loop over the argparse argument groups
        self.column_frame = Frame(self.frame)
        self.column_frames = [self.column_frame]
        for group in group_list:
            if len(group._group_actions) and not hasattr(group, 'GUI_IGNORE'):
                #This is inelegant, but first create the group, then look at its size.  
                #If it is too big to fit into the current column, just make the gui 
                #forget it and remake it to place into the next column. Making a 
                #function that just determines the size is a little dangerous since
                #its logic will need to be manually sync'ed with the group __init__
                gui_group = ArgparseOptionGroup(self.column_frame, group)
                group_row_size = gui_group.num_rows

                if option_row + group_row_size >= widgets_per_column:
                    gui_group.grid_forget()
                    group_row = 0
                    option_row = 0
                    self.column_frame = Frame(self.frame)
                    self.column_frames.append(self.column_frame)
                    gui_group = ArgparseOptionGroup(self.column_frame, group)
               
                #by default this places widget in next unused row
                gui_group.grid()
                option_row += group_row_size
                group_row += 1

                self.option_list.update(gui_group.options)

        for num, frame in enumerate(self.column_frames):
            frame.grid(row=0, column=num, sticky=N)

        #buttons appear below the other widgets
        self.button_frame = Frame(self.frame)
        self.button_frame.grid(row=widgets_per_column+1, column=0)
        self.buttons = {}
        if destroy_when_done:
            but = Button(self.button_frame, text='DONE', command=self.done)
            but.grid(row=0, column=0)
            self.buttons['DONE'] = but
        else:
            but = Button(self.button_frame, text='RUN', command=self.submit)
            #this button will be clicked if the enter key is pressed
            #having trouble getting it to look like focus is on it though
            but.bind('<Return>', self.submit)
            but.focus_set()
            but.config(state='active', highlightcolor='red', activebackground='red', highlightthickness=5)
            but.grid(row=0, column=0)
            self.buttons['RUN'] = but
        but = Button(self.button_frame, text='CANCEL/QUIT', command=self.cancel)
        but.grid(row=0, column=1)
        self.buttons['CANCEL'] = but

        self.cancelled = False

        self.bring_to_front()

    def AddScrollbars(self, height, width):
        '''adapted from http://stackoverflow.com/questions/3085696/adding-a-scrollbar-to-a-grid-of-widgets-in-tkinter
        
        This canvas object will be the entire toplevel window.  The scrollbars will be attached to it, a window
        will be made (which is what allows other widgets to be embedded in a canvas), a frame will be embedded 
        in the window to actually hold all other widgets.
        This call is currently required, i.e. it has side effects besides adding the scrollbars.
        '''
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
        self.frame.config(background="#ffffff")
        #the window is a slot in the canvas (the size of the canvas) to hold a single other widget, which will be the frame
        self.canvas.create_window((4, 4), window=self.frame, anchor="nw", tags="self.frame")
        
        #this will allow the scrollbars to adjust if the window is manually resized
        self.frame.bind("<Configure>", self.OnFrameConfigure)

    def output_result(self, text):
        if self.results:
            self.results.insert(END, text)

    def make_commandline_list(self):
        '''The most important part of the entire process.  Convert each of the options entered through 
        the GUI into its command line equivalent strings, and pass to the underlying ArgumentParser, 
        which need not know that the input came from the GUI at all.
        '''
        return_list = []
        for option in self.option_list.values():
            return_list.extend(option.make_string())
        return return_list

    def submit(self, event=None):
        self.frame.quit()

    def done(self):
        self.frame.destroy()

    def cancel(self):
        self.frame.quit()
        self.frame.destroy()
        self.cancelled = True

    def OnFrameConfigure(self, event):
        '''Reset the scroll region to encompass the inner frame'''
        self.canvas.configure(scrollregion=self.canvas.bbox("all"))

    def bring_to_front(self):
        '''Need to do this on OS X to bring window to front, otherwise root.lift() should work.'''
        if 'darwin' in sys.platform.lower():
            try:
                #this can give odd non-critical error messages from the OS, so send stderr to devnull
                retcode = subprocess.call(shlex.split('''/usr/bin/osascript -e 'tell app "Finder" to set frontmost of process "Python" to true' '''), stderr=open(devnull, 'wb'))
            except:
                #didn't manage to get window to front, but don't worry about it
                pass
        else:
            self.tk.lift()

    def register_dependencies(self, depend_dict):
        '''Use the passed dictionary to indicate dependencies of one option upon others.
        Dict keys are the options that are dependencies for each of the options listed in the 
        values.  Keys and values are passed as the argument flags, ie. 
        {'--some-dep':['--dependent1', '--dependent2']}
        '''
        for key, val in depend_dict.items():
            if not isinstance(val, str):
                for v in val:
                    self.option_list[key].register_dependency(self.option_list[v])
            else:
                self.option_list[key].register_dependency(self.option_list[val])

    def add_buttons(self, button_dict):
        '''Use the passed dictionary to create simple buttons, with keys being the name
        to appear on the button, and the value being the callback function
        '''
        self.buttons = []
        for name, func in button_dict.items():
            button = Button(self.button_frame, text=name, command=func)
            button.grid(row=0, column=2)
            self.buttons.append(button)


class ResultsWindow(object):
    '''Class to more easily create a new toplevel window that contains various kinds of results,
    either graphics drawn onto a canvas or a text box.  Things like the size of each pane and
    the border between them are set up on the class instance, and then individual panes are 
    requested by chosing a column, row, row_span and column_span, much like the grid geometry
    manager.
    '''
    def __init__(self, tk_root, width, height, border_width=5, pane_width=512, pane_height=384):
        self.border_width = border_width
        self.pane_width = pane_width
        self.pane_height = pane_height
        self.max_row, self.max_column = 0, 0

        self.internal_pane_width = pane_width - border_width * 2
        self.internal_pane_height = pane_height - border_width * 2

        self.tk = Toplevel(tk_root)
        self.tk.title('Results')
        self.main_canvas = Canvas(self.tk, borderwidth=0)
        self.main_canvas.pack()

        self.panes = {}

    def _place_pane(self, pane, row, column, row_span=1, column_span=1):
        '''Place a pane (canvas or text) that has already been created
        by add_canvas_pane or add_text_pane. Determine the new required
        size of the main canvas, and resize as necessary
        '''

        pane_x0 = column * self.pane_width + self.border_width
        pane_y0 = row * self.pane_height + self.border_width
        
        self.main_canvas.create_window((pane_x0, pane_y0), 
                window=pane, 
                height=pane.winfo_reqheight() + self.border_width, 
                width=pane.winfo_reqwidth() + self.border_width, 
                anchor='nw'
                )
      
        self.max_row = max(row + row_span, self.max_row)
        self.max_column = max(column + column_span, self.max_column)

        self.main_canvas.config(width=self.pane_width * self.max_column, height=self.pane_height * self.max_row)

    def add_canvas_pane(self, row=0, column=0, row_span=1, column_span=1, name=None):
        '''
        Outer dimensions are the pane size, which is internally taken care of by this class
        The inner is the actual tk widget to be used and the canvas window that it lives in.  
        The difference between them is the border_width
        /-----------\
        | /-------\ |
        | |       | |
        | |       | |
        | \-------/ |
        \-----------/
        '''
        pane = Canvas(self.tk, 
                width=self.internal_pane_width * column_span, 
                height=self.internal_pane_height * row_span,
                borderwidth=0
                )
        
        self._place_pane(pane, row, column, row_span, column_span)

        if name:
            self.panes[name] = pane
        else:
            self.panes['pane%d' % len(self.panes)] = pane
        return pane
    
    def add_text_pane(self, row, column, row_span=1, column_span=1, name=None):
        '''
        Outer dimensions are the pane size, which is internally taken care of by this class
        The inner is the actual tk widget to be used and the window that it lives in.  
        The difference between them is the border_width
        /-----------\
        | /-------\ |
        | |       | |
        | |       | |
        | \-------/ |
        \-----------/
        '''
        #irritatingly, the line size of the text wrapping has nothing to do with the actual Text
        #widget size.  Need to specify it by characters or text will vanish off the right side
        #of the window.  With the default font about 70 chars can fit in 512 pixels width, so
        #each char is about 7.3 pixels wide, so to be conservative (i.e. be sure not to be 
        #too wide) figure 7.5 pixels per character
        char_width = int(self.pane_width * column_span / 7.5)
        pane = Text(self.tk, width=char_width)

        self._place_pane(pane, row, column, row_span, column_span)
        
        if name:
            self.panes[name] = pane
        else:
            self.panes['pane%d' % len(self.panes)] = pane

        return pane
 
