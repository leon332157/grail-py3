# $Id: pil_interface.py,v 1.1 1996/05/09 23:38:27 fredrik Exp fl $
#
# The Python Imaging Library.
#
# File:
#	pil_interface.py -- a PIL interface for Grail
#
# History:
#	96-04-18 fl	Created
#	98-06-04 fld	Made minimal changes to look better with current
#			Grail implementation; removed timimg display.
#

"""
This is an extremely rudimentary interface between Grail 0.3b1 and PIL
0.1.  Among other things, it doesn't work for inline images.

To handle other file formats, just copy the image_tiff.py file to,
say, image_jpeg, image_gif, image_bmp, image_ppm, image_sgi,
image_sun, image_pcx, image_xbm, etc... (and make sure to change the
class name within the file as well).

Hopefully, future versions of Grail will let me register multiple
formats with a single module, and use the same code for inline images
as well.

	/F
"""

from PIL import Image, ImageTk
import tkinter
import io
from . import grailutil
import os.path

from formatter import AS_IS

class pil_interface:
    
    """Parser base class for images handled by PIL.
    
    Hack version: collect all data into a string buffer, and create
    an image from it when completed.

    """
    
    def __init__(self, viewer, reload=False):
        self.broken = False
        self.viewer = viewer
        self.viewer.new_font((AS_IS, AS_IS, AS_IS, True))
        self.label = tkinter.Label(self.viewer.text, text="<decoding>",
                                   background=viewer.text.cget("background"),
                                   highlightthickness=0)
        self.viewer.add_subwindow(self.label)
        self.buf = io.BytesIO()

    def feed(self, data):
        try:
            self.buf.write(data)
            # FIXME: try to identify the file; as soon as this succeeds,
            # start decoding data as it arrives
        except IOError:
            self.buf = io.BytesIO()
            self.broken = True
            raise

    def close(self):
        if self.buf.tell():
            try:
                self.buf.seek(0)
                im = Image.open(self.buf)
                im.load() # benchmark decoding
                tkim = ImageTk.PhotoImage(im.mode, im.size)
                tkim.paste(im)
                self.label.image = tkim
                self.label.config(image = self.label.image)
            except:
                self.broken = True
        if self.broken:
            file = grailutil.which(os.path.join('icons', 'sadsmiley.gif'))
            self.label.image = tkinter.PhotoImage(file = file)
            self.label.config(image = self.label.image)
            self.viewer.text.insert(tkinter.END, '\nBroken Image!')
