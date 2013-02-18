"""Parser to pull links from an HTML document."""

__version__ = '$Revision: 1.5 $'


from .. import nodes
import urllib.parse

from ...sgml import SGMLHandler
from ...sgml import SGMLParser


class Parser(SGMLHandler.BaseSGMLHandler):
    __buffer = ''
    __baseurl = None

    from htmlentitydefs import entitydefs

    def __init__(self, filename=None):
        self._filename = filename
        self.sgml_parser = SGMLParser.SGMLParser(gatherer=self)
        self.__root = nodes.Folder()
        self.__root.expand()

    def feed(self, data):
        self.sgml_parser.feed(data)

    def close(self):
        self.sgml_parser.close()

    def save_bgn(self):
        self.__buffer = ''

    def save_end(self, reflow=True):
        s, self.__buffer = self.__buffer, ''
        if reflow:
            s = ' '.join(s.split())
        return s

    def handle_data(self, data):
        self.__buffer = self.__buffer + data

    def handle_starttag(self, tag, method, attrs):
        method(self, attrs)

    def get_root(self):
        return self.__root

    # these are probably not useful for subclasses:

    def set_baseurl(self, baseurl):
        self.__baseurl = baseurl

    def do_meta(self, attrs):
        # attempt to pull in a description:
        name = attrs.get("name", "").lower().strip()
        if name in ("description", "dc.description"):
            desc = attrs.get("content", "").strip()
            if desc:
                self.__root.set_description(desc)

    def start_a(self, attrs):
        uri = attrs.get("href", "").strip()
        if uri:
            self.__node = nodes.Bookmark()
            self.__root.append_child(self.__node)
            if self.__baseurl:
                uri = urllib.parse.urljoin(self.__baseurl, uri)
            self.__node.set_uri(uri)
            title = " ".join(attrs.get("title", "").split())
            if title:
                self.__node.set_title(title)
        else:
            self.__node = None
        self.save_bgn()

    def end_a(self):
        s = self.save_end()
        if self.__node:
            if not self.__node.title():
                self.__node.set_title(s)
            self.__node = None

    def start_title(self, attrs):
        self.save_bgn()

    def end_title(self):
        s = self.save_end().strip()
        if s and not self.__root.title():
            self.__root.set_title(s)

    def start_h1(self, attrs):
        self.start_title({})

    def end_h1(self):
        self.end_title()
