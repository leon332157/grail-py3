import tempfile
import os
from grailutil import getenv, which
from Tkinter import *
from formatter import AS_IS
from os import getenv

_FILTERCMD = 'djpeg'
_FILTERARG = '-gif'
_FILTERPATH = which(_FILTERCMD, getenv('PATH').split(':'))

if hasattr(os, 'popen') and _FILTERPATH:
    _FILTER = _FILTERPATH + ' ' + _FILTERARG
 
    class parse_image_jpeg:
    
        """Parser for image/jpeg files.
    
        Collect all the data on a temp file and then create an in-line
        image from it.
    
        """
    
        def __init__(self, viewer, reload=False):
            self.broken = None
            self.tf = self.tfname = None
            self.viewer = viewer
            self.viewer.new_font((AS_IS, AS_IS, AS_IS, True))
            self.tfname = tempfile.mktemp()
            self.tf = os.popen(_FILTER + '>' + self.tfname, 'wb')
            self.label = Label(self.viewer.text, text=self.tfname,
                               highlightthickness=0, borderwidth=0)
            self.viewer.add_subwindow(self.label)
    
        def feed(self, data):
            try:
                self.tf.write(data)
            except IOError:
                self.tf.close()
                self.tf = None
                self.broken = True
                raise
    
        def close(self):
            if self.tf:
                self.tf.close()
                self.tf = None
                self.label.image = PhotoImage(file=self.tfname)
                self.label.config(image=self.label.image)
            try:
                os.unlink(self.tf.name)
            except os.error:
                pass
            if self.broken:
                # TBD: horrid kludge... don't hate me! ;-)
                self.label.image = PhotoImage(file='icons/sadsmiley.gif')
                self.label.config(image=self.label.image)
                self.viewer.text.insert(END, '\nBroken Image!')