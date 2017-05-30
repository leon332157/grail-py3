"""Parser for Grail's pickled bookmarks.  Old-style bookmarks are
automatically converted to the current type."""

__version__ = '$Revision: 1.3 $'

from .. import BookmarkFormatError
import re
import pickle


class Parser:
    mode = "b"
    __data = bytearray()
    __root = None

    def __init__(self, filename):
        self._filename = filename

    def feed(self, data):
        self.__data.extend(data)

    def close(self):
        data = self.__data
        # remove leading comment line
        _, data = self.__split_line(data)
        orig_fname, data = self.__split_line(data)
        orig_mtime, data = self.__split_line(data)
        self.original_filename = orig_fname.decode().strip()
        self.original_mtime = float(orig_mtime)
        self.__root = pickle.loads(data)

    def get_root(self):
        return self.__root

    def __split_line(self, data):
        header, newline, data = data.partition(b'\n')
        if not newline:
            raise BookmarkFormatError(self._filename,
                                      "incomplete file header")
        header += newline
        return header, data
