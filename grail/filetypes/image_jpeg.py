import tempfile
import os
from tkinter import *
from formatter import AS_IS
import subprocess
from ..grailutil import close_subprocess

_FILTERCMD = 'djpeg'
_FILTERARG = '-gif'

class parse_image_jpeg:

    """Parser for image/jpeg files.

    Collect all the data in a temp file and then create an in-line
    image from it.

    """

    def __init__(self, viewer, reload=False):
        self.broken = None
        self.tf = self.proc = None
        self.viewer = viewer
        self.viewer.new_font((AS_IS, AS_IS, AS_IS, True))
        self.tf = tempfile.NamedTemporaryFile("wb", delete=False)
        try:
            self.proc = subprocess.Popen((_FILTERCMD, _FILTERARG),
                stdin=subprocess.PIPE, stdout=self.tf, bufsize=-1)
            self.tf.close()
            self.label = Label(self.viewer.text, text=self.tf.name,
                               highlightthickness=0, borderwidth=0)
            self.viewer.add_subwindow(self.label)
        except:
            self.tf.close()
            if self.proc:
                close_subprocess(self.proc)
            raise

    def feed(self, data):
        try:
            self.proc.stdin.write(data)
        except IOError:
            close_subprocess(self.proc)
            self.proc = None
            self.broken = True
            raise

    def close(self):
        if self.proc:
            close_subprocess(self.proc)
            self.proc = None
            self.label.image = PhotoImage(file=self.tf.name)
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
