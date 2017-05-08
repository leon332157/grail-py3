"""Several useful routines that isolate some of the weirdness of Grail-based
applications.
"""
__version__ = '$Revision: 1.3 $'

import os
from os import getenv

# TBD: hack!  The top-level grail package calculates grail_root, which would
# be convenient to export to extensions, but you can't `import grail' or
# `import __main__'.  The package isn't designed for that.  You could
# `from grail import grail_root' but that's kind of gross.  This
# global holds the value of grail_root which can be had with
# grailutil.get_grailroot()
_grail_root = None
_grail_app = None


# XXX Unix specific stuff
# XXX (Actually it limps along just fine for Macintosh, too)

def getgraildir():
    return getenv("GRAILDIR") or os.path.join(gethome(), ".grail")


def get_grailroot():
    return _grail_root


def get_grailapp():
    return _grail_app


def gethome():
    try:
        home = getenv("HOME")
        if not home:
            import pwd
            user = getenv("USER") or getenv("LOGNAME")
            if not user:
                pwent = pwd.getpwuid(os.getuid())
            else:
                pwent = pwd.getpwnam(user)
            home = pwent.pw_dir
        return home
    except (KeyError, ImportError):
        return os.curdir


def which(filename, searchlist=None):
    if searchlist is None:
        from .. import __path__ as searchlist
    for dir in searchlist:
        found = os.path.join(dir, filename)
        if os.path.exists(found):
            return os.path.abspath(found)
    return None


def establish_dir(dir):
    """Ensure existence of DIR, creating it if necessary.

    Returns True if successful, False otherwise."""
    if os.path.isdir(dir):
        return True
    head, tail = os.path.split(dir)
    if not establish_dir(head):
        return False
    try:
        os.mkdir(dir, 0o777)
        return True
    except os.error:
        return False


def conv_mimetype(type):
    """Convert MIME media type specifications to tuples of
    ('type/subtype', {'option': 'value'}).
    """
    if not type:
        return None, {}
    (type, sep, opts) = type.partition(';')
    if sep:
        opts = _parse_mimetypeoptions(opts)
    else:
        opts = {}
    type = type.lower()
    fields = type.split('/')
    if len(fields) != 2:
        raise ValueError("Illegal media type specification.")
    return type, opts


def _parse_mimetypeoptions(options):
    opts = {}
    while options:
        name, sep, value = options.partition('=')
        if sep:
            name = name.strip().lower()
            value, _, options = value.partition(';')
            value = value.strip()
            if name:
                opts[name] = value
        else:
            options = None
    return opts
