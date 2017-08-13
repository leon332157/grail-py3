#! /usr/bin/env python

"""HTML to PostScript translator.

This is a standalone script for command line conversion of HTML documents
to PostScript.  Use the '-h' option to see information about all too many
command-line options.

"""

import os
import sys

from .printing import main


if __name__ == '__main__':
    if sys.argv[1:] and sys.argv[1] == "--profile":
        del sys.argv[1]
        main.profile_main()
    else:
        main.main()
