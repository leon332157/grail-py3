"""General Grail preferences panel."""

__version__ = "$Revision: 1.1 $"
# $Source: /cvsroot/grail/grail/src/prefpanels/PrintingPanel.py,v $

# Base class for the panel:
import PrefsPanels

#import sys, os

#from Tkinter import *
#import tktools
#import grailutil
#import tktools
#import string

class PrintingPanel(PrefsPanels.Framework):
    """Printing preferences."""

    # Class var for help button - relative to grail-home-page.
    HELP_URL = "help/prefs/printing.html"

    def CreateLayout(self, name, frame):

	# Printer configs are simple enough to use the convenience functions
	self.PrefsEntry(frame, 'Print command:',
			      'printing', 'command')
	self.PrefsCheckButton(frame, "Images:", "Print images ",
			      'printing', 'images')
	self.PrefsCheckButton(frame, "Images:", "Reduce images to greyscale",
			      'printing', 'greyscale')
	self.PrefsCheckButton(frame, "Anchors:", "Footnotes for anchors",
			      'printing', 'footnote-anchors')
	self.PrefsCheckButton(frame, "Anchors:", "Underline anchors",
			      'printing', 'underline-anchors')
