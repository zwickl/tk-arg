# tk-arg
#Automatically generate a tkinter gui from an argparse script

Use typical python install
python setup.py install
(add sudo at the start of the line if necessary)

Try the example script:
tkgui.py examples/pass_me_to_tkgui.py

Any python script using argparse can be passed to tkgui.py.  It will pull information about the arguments out of the instantiated ArgumentParser and open a basic tkinter gui. After the gui has been interacted with and closed it passes information on the state to the script, such that the wrapped script thinks that arguments were passed on the command line.
