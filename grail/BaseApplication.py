"""Base class for the Grail Application object.

This provides the preferences initialization if needed as well as the
extension loading mechanisms.  The later are the primary motivation
for this, allowing the html2ps.py script to use extensions intelligently
using the same approaches (and implementation) as the Tk-based browser.
"""
__version__ = '$Revision: 2.17 $'
#  $Source: /cvsroot/grail/grail/src/BaseApplication.py,v $

import keyword
import os

from .grailbase import app
from .grailbase import mtloader
from .grailbase import utils

from .sgml import extloader

# make extension packages from these:
from . import filetypes
from . import html
from .printing import filetypes as printing_filetypes
from .printing import htmltags as printing_htmltags
from . import protocols
from .protocols import ProtocolAPI


class BaseApplication(app.Application):

    def __init__(self, prefs=None):
        app.Application.__init__(self, prefs)
        loader = extloader.TagExtensionLoader(html)
        self.add_loader("html.viewer", loader)
        loader = extloader.TagExtensionLoader(printing_htmltags)
        self.add_loader("html.postscript", loader)
        loader = mtloader.MIMEExtensionLoader(filetypes)
        self.add_loader("filetypes", loader)
        loader = mtloader.MIMEExtensionLoader(printing_filetypes)
        self.add_loader("printing.filetypes", loader)
        loader = ProtocolAPI.ProtocolLoader(protocols)
        self.add_loader("protocols", loader)

        # cache of available extensions
        self.__extensions = {}

    def find_type_extension(self, package, mimetype):
        handler = None
        try:
            loader = self.get_loader(package)
        except KeyError:
            pass
        else:
            try:
                content_type, opts = utils.conv_mimetype(mimetype)
            except:
                pass
            else:
                handler = loader.get(content_type)
        return handler

    def find_extension(self, subdir, module):
        try:
            return self.get_loader(subdir).get(module)
        except KeyError:
            return None
