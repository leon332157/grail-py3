"""Writer for Netscape HTML bookmarks."""

__version__ = '$Revision: 1.4 $'


from xml.sax import saxutils
from .. import walker
import sys
from io import TextIOWrapper


class Writer(walker.TreeWalker):
    __depth = 1
    __need_header = True
    __alias_id = ''
    __id_next = 0

    # public interface

    def get_filetype(self):
        return "html"

    def write_tree(self, fp):
        self.__id_map = {}
        root = self.get_root()
        fp = TextIOWrapper(fp, "ascii", "xmlcharrefreplace")
        try:
            self.__fp = fp
            self.walk()
            print('</DL><p>', file=self.__fp)
        finally:
            fp.detach()

    # node-type handlers

    def start_Separator(self, node):
        print('{}<HR>'.format(self.__tab()), file=self.__fp)

    def start_Bookmark(self, node):
        alias = self.__compute_alias_info(node)
        modified = node.last_modified() or ''
        if modified:
            modified = ' LAST_MODIFIED="{}"'.format(modified)
        add_date = node.add_date() or ''
        if add_date:
            add_date = ' ADD_DATE="{}"'.format(add_date)
        last_visit = node.last_visited()
        if last_visit:
            last_visit = ' LAST_VISIT="{}"'.format(last_visit)
        print('{}<DT><A HREF="{}"{}{}{}{}>{}</A>'.format(
              self.__tab(), node.uri(), alias, add_date,
              last_visit, modified, saxutils.escape(node.title())),
              file=self.__fp)
        self.__write_description(node.description())

    def start_Alias(self, node):
        refnode = node.get_refnode()
        if refnode is None or refnode.get_nodetype() == "Folder":
            return
        idref = node.idref()
        if idref not in self.__id_map:
            self.__id_map[idref] = self.__id_next
            self.__id_next = self.__id_next + 1
        self.__alias_id = ' ALIASOF="{}"'.format(self.__id_map[idref])
        self.start_Bookmark(node.get_refnode())

    def start_Folder(self, node):
        if self.__need_header:
            self.__need_header = False
            self.__write_header(node)
            self.__write_description(node.description())
            print("<DL><p>", file=self.__fp)
            return
        tab = self.__tab()
        if node.expanded_p():
            folded = ''
        else:
            folded = ' FOLDED'
        add_date = node.add_date() or ''
        if add_date:
            add_date = ' ADD_DATE="{}"'.format(add_date)
        print('{}<DT><H3{}{}>{}</H3>'.format(
              tab, folded, add_date, node.title()), file=self.__fp)
        self.__write_description(node.description())
        print(tab + '<DL><p>', file=self.__fp)
        self.__depth = self.__depth + 1

    def end_Folder(self, node):
        self.__depth = self.__depth - 1
        print(self.__tab() + '</DL><p>', file=self.__fp)

    # support methods

    def __compute_alias_info(self, node):
        alias = self.__alias_id
        if not alias:
            id = node.id()
            if id:
                if id not in self.__id_map:
                    self.__id_map[id] = self.__id_next
                    self.__id_next = self.__id_next + 1
                alias = ' ALIASID="{}"'.format(self.__id_map[id])
        self.__alias_id = ''
        return alias

    def __tab(self):
        return "    " * self.__depth

    def __write_description(self, desc):
        if not desc:
            return
        # write the description, sans leading and trailing whitespace
        print('<DD>{}'.format(saxutils.escape(desc).strip()), file=self.__fp)

    __header = """\
<!DOCTYPE NETSCAPE-Bookmark-file-1>
<!-- This is an automatically generated file.
    It will be read and overwritten.
    Do Not Edit! -->
<TITLE>{title}</TITLE>
<H1>{title}</H1>"""

    def __write_header(self, root):
        print(self.__header.format(title=root.title()), file=self.__fp)
