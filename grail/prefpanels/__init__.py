"""Package to be searched for preference GUI panel dialog modules"""

import os
from .. import grailutil

grail_root = grailutil.get_grailroot()

# User's panels dir should come first, so it takes precedence.
panels_dirs = [
               os.path.expanduser("~/.grail/prefpanels"),
]

__path__[:0] = panels_dirs  # Insert at beginning
