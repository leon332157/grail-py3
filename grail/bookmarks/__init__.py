import os
import sys
from io import TextIOBase, TextIOWrapper


class Error(Exception):
    def __init__(self, filename):
        self.filename = filename
    def __repr__(self):
        C = type(self)
        return "<{}.{} for file {}>".format(
               C.__module__, C.__name__, self.filename)


class BookmarkFormatError(Error):
    def __init__(self, filename, problem, what="file"):
        Error.__init__(self, filename)
        self.problem = problem
        self.what = what

    def __repr__(self):
        C = type(self)
        return "<{}.{} for {} {}>".format(
               C.__module__, C.__name__, self.what, self.filename)

    def __str__(self):
        return "{} for {} {}".format(self.problem, self.what, self.filename)


class PoppedRootError(Error):
    pass


class BookmarkReader:
    def __init__(self, parser):
        self.__parser = parser

    def read_file(self, fp):
        wrapper = None
        try:
            if "t" in self.__parser.mode:
                if not isinstance(fp, TextIOBase):
                    wrapper = TextIOWrapper(fp)
                    fp = wrapper
            else:
                if isinstance(fp, TextIOWrapper):
                    keep_open = fp
                    fp = fp.buffer
            self.__parser.feed(fp.read())
            self.__parser.close()
        finally:
            if wrapper:
                wrapper.detach()
        return self.__parser.get_root()


class BookmarkWriter:
    # base class -- subclasses are required to set _filetype attribute
    def get_filetype(self):
        return self._filetype



pubid_fmt = "+//IDN python.org//DTD XML Bookmark Exchange Language {}//EN"
sysid_fmt = "http://www.python.org/topics/xml/dtds/xbel-{}.dtd"

XBEL_1_0_PUBLIC_ID = pubid_fmt.format("1.0")
XBEL_1_0_SYSTEM_ID = sysid_fmt.format("1.0")
XBEL_1_0_ROOT_ELEMENTS = ("xbel", "folder", "bookmark", "alias", "separator")

# not yet released
XBEL_1_1_PUBLIC_ID = pubid_fmt.format("1.1")
XBEL_1_1_SYSTEM_ID = sysid_fmt.format("1.1")
XBEL_1_1_ROOT_ELEMENTS = XBEL_1_0_ROOT_ELEMENTS + ("link",)

del pubid_fmt
del sysid_fmt


def check_xml_format(buffer):
    from . import xmlinfo
    try:
        info = xmlinfo.get_xml_info(buffer)
    except xmlinfo.Error:
        return None
    if info.doc_elem in XBEL_1_0_ROOT_ELEMENTS:
        public_id = info.public_id
        system_id = info.system_id
        if public_id == XBEL_1_0_PUBLIC_ID:
            if system_id == XBEL_1_0_SYSTEM_ID or not system_id:
                return "xbel"
        elif public_id:
            pass
        elif system_id == XBEL_1_0_SYSTEM_ID:
            return "xbel"


# The canonical table of supported bookmark formats:
__formats = {
    # format-name     first-line-magic
    #                  short-name   extension
    "html":          (br'<!DOCTYPE\s+(GRAIL|NETSCAPE)-Bookmark-file-1',
                      "html",      ".html",	"html"),
    "pickle":        (br'#.*GRAIL-Bookmark-file-[5]',
                      "pickle",    ".pkl5",	"xbel"),
    "xbel":          (br'<(\?xml|!DOCTYPE)\s+xbel',
                      "xbel",      ".xml",	"xbel"),
    }

__format_inited = False

def __init_format_table():
    global __format_inited
    global __format_table
    import re
    __format_table = table = []
    for result, (rx, sname, ext, outfmt) in __formats.items():
        if rx:
            rx = re.compile(rx)
            table.append((rx, result))
    __format_inited = True

def get_format(fp):
    if not __format_inited:
        __init_format_table()
    format = None
    pos = fp.tell()
    try:
        line1 = fp.read(1024)
        for re, fmt in __format_table:
            if re.match(line1):
                format = fmt
                break
        else:
            format = check_xml_format(line1)
    finally:
        fp.seek(pos)
    return format


def get_short_name(format):
    return __formats[format][1]

def get_default_extension(format):
    return __formats[format][2]


def get_parser_class(format):
    from . import formats
    name = "{}_parser".format(get_short_name(format))
    return __import__(name, vars(formats), level=1).Parser

def get_writer_class(format):
    from . import formats
    name = "{}_writer".format(get_short_name(format))
    return __import__(name, vars(formats), level=1).Writer

def get_output_format(format):
    return __formats[format][3]
