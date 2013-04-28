from Tkinter import TclError

def _castrate(tk):
    """Remove all Tcl commands that can affect the file system.

    This way, if someone breaks through the bastion around Tk, all
    they can do is screw up Grail.  (Though if they are really clever,
    they may be able to catch some of the user's keyboard input, or do
    other subversive things.)

    """
    if not hasattr(tk, 'eval'): return # For Rivet
    def rm(name, tk=tk):
        try:
            tk.call('rename', name, '')
        except TclError:
            pass
    # Make sure the menu support commands are autoloaded, since we need them
    tk.eval("auto_load tkMenuInvoke")
    rm('exec')
    rm('cd')
    rm('open') # This is what breaks the menu support commands
    rm('send')
