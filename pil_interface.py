# $Id: pil_interface.py,v 1.1 1996/05/09 23:38:27 fredrik Exp fl $
#
# The Python Imaging Library.
#
# File:
#	pil_interface.py -- a PIL interface for Grail
#
# Notes:
#	You may wish to remove the print statements in here.  They
#	are included only to show you that PIL is pretty fast compared
#	to everything else...
#
# History:
#	96-04-18 fl	Created
#

import Image, ImageTk
import Tkinter
import string, StringIO

import time

from formatter import AS_IS

class pil_interface:
    
    """Parser base class for images handled by PIL.
    
    Hack version: collect all data into a string buffer, and create
    an image from it when completed.

    """
    
    def __init__(self, viewer, reload=0):
	self.broken = 0
	self.viewer = viewer
	self.viewer.new_font((AS_IS, AS_IS, AS_IS, 1))
	self.label = Tkinter.Label(self.viewer.text, text = "<decoding>")
	self.viewer.add_subwindow(self.label)
	self.buf = []

	global t
	t = time.time()
	print "** GRAIL", time.time() - t

    def feed(self, data):
	try:
	    self.buf.append(data)
	    # FIXME: try to identify the file; as soon as this succeeds,
	    # start decoding data as it arrives
	except IOError, (errno, errmsg):
	    self.buf = []
	    self.broken = 1
	    raise IOError, (errno, errmsg)

    def close(self):
	if self.buf:
	    try:
		print "** PIL", time.time() - t
		self.buf = string.joinfields(self.buf, "")
		im = Image.open(StringIO.StringIO(self.buf))
		im.load() # benchmark decoding
		tkim = ImageTk.PhotoImage(im.mode, im.size)
		tkim.paste(im)
		self.label.image = tkim.image
		print "** TK", time.time() - t
		self.label.config(image = self.label.image)
		print "** OK", time.time() - t
	    except:
		self.broken = 1
	if self.broken:
	    self.label.image = Tkinter.PhotoImage(file = 'icons/sadsmiley.gif')
	    self.label.config(image = self.label.image)
	    self.viewer.text.insert(Tkinter.END, '\nBroken Image!')
