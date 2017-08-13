import os
import sys

__author__ = "CRNI"
__copyright__ = "CRNI 1996-1998"
__license__ = "Custom"
__maintainer__ = "None"
__version__ = "0.6f0"
__description__ = """An extensible web browser written in pure Python."""

script_dir = os.path.dirname(__file__)
grail_root = script_dir
for path in 'applets', 'ancillary', 'utils', 'pythonlib':
    __path__.append(os.path.join(grail_root, path))
