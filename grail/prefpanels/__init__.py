"""Package to be searched for preference GUI panel dialog modules"""

import os
from .. import grailutil

grail_root = grailutil.get_grailroot()

# User's panels dirs should come first, so they take precedence.
panels_dirs = [
               # These two for backwards compat with beta versions:
               os.path.expanduser("~/.grail/prefspanels"),
               os.path.join(grail_root, 'prefspanels'),
               
               os.path.expanduser("~/.grail/prefpanels"),
]

__path__[:0] = panels_dirs  # Insert at beginning
