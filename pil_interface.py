# $Id$
#
# The Python Imaging Library.
#
# File:
#	pil_interface.py -- a PIL interface for Grail
#
# History:
#	96-04-18 fl	Created
#

import Image, ImageTk
import Tkinter, StringIO

from formatter import AS_IS

class pil_interface:
    
    """Parser base class for images handled by PIL.
    
    This version collects all data into a string buffer, and create
    an image from it when completed.  Things to do:
	- decode data as it arrives
	- support transparency (background colour, at least)
	- use progressive display

    """

    def __init__(self, viewer, reload=0):
	self.broken = 0
	self.viewer = viewer
	self.viewer.new_font((AS_IS, AS_IS, AS_IS, 1))
	self.label = Tkinter.Label(self.viewer.text, text = "<pil>")
	self.viewer.add_subwindow(self.label)
	self.buf = ""

    def feed(self, data):
	try:
	    self.buf = self.buf + data
	    # FIXME: try to identify the file; as soon as this succeeds,
	    # started decoding data as it arrives
	except IOError, (errno, errmsg):
	    self.buf = None
	    self.broken = 1
	    raise IOError, (errno, errmsg)

    def close(self):
	if self.buf:
	    try:
		im = Image.open(StringIO.StringIO(self.buf))
		tkim = ImageTk.PhotoImage(im.mode, im.size)
		tkim.paste(im)
		self.label.image = tkim.image
		self.label.config(image = self.label.image)
	    except:
		self.broken = 1
	if self.broken:
	    self.label.image = Tkinter.PhotoImage(file = 'icons/sadsmiley.gif')
	    self.label.config(image = self.label.image)
	    self.viewer.text.insert(END, '\nBroken Image!')
