"""XBEL writer."""

__version__ = '$Revision: 1.12 $'

from .. import XBEL_1_0_PUBLIC_ID, XBEL_1_0_SYSTEM_ID
from xml.sax import saxutils
from .. import iso8601
from .. import walker
import sys


class Writer(walker.TreeWalker):
    _depth = 0
    __header = '''\
<?xml version="1.0" encoding="ISO-8859-1"?>
<!DOCTYPE {}
  PUBLIC "{}"
         "{}">
'''

    PUBLIC_ID = XBEL_1_0_PUBLIC_ID
    SYSTEM_ID = XBEL_1_0_SYSTEM_ID

    def __init__(self, root=None):
        walker.TreeWalker.__init__(self, root)
        self.__close_folders = []

    def write_tree(self, fp):
        root = self.get_root()
        root_type = root.get_nodetype().lower()
        if root_type == "folder":
            root_type = "xbel"
        fp.write(self.__header.format(
            root_type, self.PUBLIC_ID, self.SYSTEM_ID))
        self.__fp = fp
        self.write = fp.write
        self.walk()

    def get_filetype(self):
        return "xbel"

    def start_Folder(self, node):
        info = node.info()
        title = node.title()
        desc = node.description()
        tab = "  " * self._depth
        attrs = ''
        added = node.add_date()
        if added:
            attrs = '\n      added="{}"'.format(iso8601.ctime(added))
        if node.id():
            if not attrs:
                attrs = "\n     "
            attrs = '{} id="{}"'.format(attrs, node.id())
        #
        if not self._depth:
            self.write('<xbel{}>\n'.format(attrs))
            if title:
                self.write("{}  <title>{}</title>\n".format(
                           tab, saxutils.escape(title)))
            if info:
                self.__write_info(info)
            if desc:
                self.__write_description(desc, tab)
            self._depth = 1
            self.__close_folders.append(0)
            return
        #
        if node.expanded_p():
            attrs = attrs + ' folded="no"'
        else:
            attrs = attrs + ' folded="yes"'
        if title or info or desc or node.children():
            self.write(tab + '<folder{}>\n'.format(attrs))
            if title:
                self.write("{}  <title>{}</title>\n".format(
                           tab, saxutils.escape(title)))
            if info:
                self.__write_info(info)
            if desc:
                self.__write_description(desc, tab)
            self._depth = self._depth + 1
            self.__close_folders.append(1)
            # children are handled through the walker
        else:
            self.write(tab + '<folder{}/>\n'.format(attrs))
            self.__close_folders.append(0)

    def end_Folder(self, node):
        depth = self._depth = self._depth - 1
        if self.__close_folders.pop():
            self.write("  " * depth + "</folder>\n")
        else:
            self.write("</xbel>\n")

    def start_Separator(self, node):
        tab = "  " * self._depth
        self.write(tab + "<separator/>\n")

    def start_Alias(self, node):
        idref = node.idref()
        if idref is None:
            sys.stderr.write("Alias node has no referent; dropping.\n")
        else:
            self.write('{}<alias ref="{}"/>\n'.format(
                       "  " * self._depth, idref))

    def start_Bookmark(self, node):
        date_attr = _fmt_date_attr
        added = date_attr(node.add_date(), "added")
        modified = date_attr(node.last_modified(), "modified")
        visited = date_attr(node.last_visited(), "visited")
        desc = (node.description() or '').strip()
        idref = node.id() or ''
        if idref:
            idref = 'id="{}"'.format(idref)
        title = saxutils.escape(node.title() or '')
        uri = saxutils.quoteattr(node.uri() or '')
        attrs = filter(None, (idref, added, modified, visited))
        #
        tab = "  " * self._depth
        sep = "\n{}          ".format(tab)
        attrs = sep.join(attrs)
        if attrs:
            attrs = " " + attrs
        else:
            sep = " "
        self.write('{}<bookmark{}{}href={}>\n'.format(tab, attrs, sep, uri))
        if title:
            self.write("{}  <title>{}</title>\n".format(tab, title))
        if node.info():
            self.__write_info(node.info())
        if desc:
            self.__write_description(desc, tab)
        self.write(tab + "  </bookmark>\n")

    # support methods

    def __write_description(self, desc, tab):
        w = 60 - len(tab)
        desc = saxutils.escape(desc)
        if len(desc) > w:
            desc = _wrap_lines(desc, 70 - len(tab), indentation=len(tab) + 4)
            desc = "{}\n{}    ".format(desc, tab)
        self.write("{}  <desc>{}</desc>\n".format(tab, desc))

    def __write_info(self, info):
        tab = "  " * (self._depth + 1)
        L = [tab, "<info>\n"]
        append = L.append
        for element in info:
            append(tab)
            append("  ")
            self.__dump_xml(element, L, tab + "    ")
            append("\n")
        append(tab)
        append("  </info>\n")
        self.write("".join(L))

    def __dump_xml(self, element, L, tab):
        append = L.append
        append("<")
        append(element.tag)
        space = " "
        for attr, value in element.items():
            append('{}{}={}'.format(space, attr, saxutils.quoteattr(value)))
            space = "\n{}{}".format(tab, " "*len(tag))
        if not element.text and not len(element):
            append("/>")
            return
        has_text = (tab is None) or (attrs.get("xml:space") == "preserve")
        if not has_text:
            has_text = element.text or any(citem.tail for citem in element)
        if has_text:
            # some plain text in the data; assume significant:
            append(">")
            if element.text:
                append(saxutils.escape(element.text))
            for citem in element:
                self.__dump_xml(citem, L, None)
                if citem.tail:
                    append(saxutils.escape(citem.tail))
        else:
            append(">\n")
            for citem in element:
                append(tab)
                self.__dump_xml(citem, L, tab + "  ")
                append("\n")
            append(tab)
        append("</{}>".format(element.tag))


def _fmt_date_attr(date, attrname):
    if date:
        return '{}="{}"'.format(attrname, iso8601.ctime(date))
    return ''


def _wrap_lines(s, width, indentation=0):
    words = s.split()
    lines = []
    buffer = ''
    for w in words:
        if buffer:
            nbuffer = "{} {}".format(buffer, w)
            if len(nbuffer) > width:
                lines.append(buffer)
                buffer = w
            else:
                buffer = nbuffer
        else:
            buffer = w
    if buffer:
        lines.append(buffer)
    if len(lines) > 1:
        lines.insert(0, '')
    return ("\n" + " "*indentation).join(lines)
