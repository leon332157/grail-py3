"""Miscellaneous utilities for Grail."""

__version__ = "$Revision: 2.31 $"

import os

# Utility functions for handling attribute values used to be defined here;
# now get them from sgml.utils since Grail expects them to be here.  One is
# in the printing package.

from .grailbase.utils import *
from .sgml.utils import *
from .printing.utils import conv_fontsize


def complete_url(url):
    import urllib.parse
    scheme, netloc = urllib.parse.urlparse(url)[:2]
    if not scheme:
        if not netloc:
            # XXX url2pathname/pathname2url???
            if os.path.exists(url):
                url = "file:" + urllib.parse.quote(url)
            else:
                url = "http://" + url
        else:
            url = "http:" + url
    return url


def nicebytes(n):
    """Convert a bytecount to a string like '<number> bytes' or '<number>K'.

    This is intended for inclusion in status messages that display
    things like '<number>% read of <bytecount>' or '<bytecount> read'.
    When the byte count is large, it will be expressed as a small
    floating point number followed by K, M or G, e.g. '3.14K'.

    The word 'bytes' (or singular 'byte') is part of the returned
    string if the byte count is small; when the count is expressed in
    K, M or G, 'bytes' is implied.

    """
    if n < 1000:
        if n == 1: return "1 byte"
        return "{} bytes".format(n)
    n = n * 0.001
    if n < 1000.0:
        suffix = "K"
    else:
        n = n * 0.001
        if n < 1000.0:
            suffix = "M"
        else:
            n = n * 0.001
            suffix = "G"
    if n < 10.0: r = 2
    elif n < 100.0: r = 1
    else: r = 0
    return "{:.{}f}".format(n, r) + suffix




def pref_or_getenv(name, group='proxies', type_name='string',
                   check_ok=None):
    """Help for integrating environment variables with preferences.

    First check preferences, under 'group', for the component 'name'.
    If 'name' is defined as a 'string' and it's NULL, try to read
    'name' from the environment.  If 'name's defined in the
    environment, migrate the value to preferences.  Return the value
    associated with the name, None if it's not defined in either place
    (env or prefs... and it's a 'string').  If check_ok is not None,
    it is expected to be a tuple of valid names. e.g. ('name1',
    'name2').

    """
    if check_ok and  name not in check_ok:
            return None

    app = get_grailapp()

    component = app.prefs.GetTyped(group, name, type_name)
    if type_name != 'string' or len(component):
        return component

    import os
    try:
        component = os.environ[name]
    except:
        return None

    app.prefs.Set(group, name, component)
    return component


def close_subprocess(proc):
    """Close a process opened by the "subprocess" module
    
    Ignores broken pipe error when flushing and closing the process's input
    pipe and the stream is buffered. This function is used since neither
    proc.communicate() nor proc.__exit__() seem to clean up the process after
    a broken pipe. See <https://bugs.python.org/issue21619>."""
    try:
        proc.stdin.close()
    except BrokenPipeError:
        pass
    return proc.wait()
