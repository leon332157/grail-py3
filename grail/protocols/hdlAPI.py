"""CNRI handle protocol extension.

This module glues the backend CNRI handle client resolution module in
hdllib.py to the Grail URI protocol API.  Currently we are only
interested in URL type handles, so we can get away semantically with
returning an HTTP-style relocation error to the browser for the
resolved handle (if the handle resolves to a single URL), or to
generating a piece of HTML which lets the user choose one (if it
resolves to multiple URLs).

XXX Remaining problems:

           Issuing a 302 relocate isn't the proper thing to do in the
           long term, because it forces the user back into URL space.
           So, for example, the user will naturally keep the resolved
           URL on her bookmarks, instead of the original handle.
           However, for backward compatibility with relative links, we
           need to define relative-handle semantics.  We're working
           with the CNRI handle group to define this and we'll be
           experimenting with solutions in the future.  This should be
           good enough for now.

           Handle resolution is done synchronously, thereby defeating
           the intended asynchronous API.  This should be fixed by
           adding an asynchronous interface to hdllib.py.

"""

import urllib.parse
from .. import hdllib
from . import nullAPI
from .. import grailutil
from xml.sax import saxutils


# We are currently only concerned with URL type handles.
HANDLE_TYPES = [hdllib.HDL_TYPE_URL]


# HTML boilerplate for response on handle with multiple URLs
HTML_HEADER = """<HTML>

<HEAD>
<TITLE>{title}</TITLE>
</HEAD>

<BODY>

<H1>{title}</H1>

The handle you have selected resolves to multiple data items or to an
unknown data type.<P>

Please select one from the following list:

<UL>
"""

HTML_TRAILER = """
</UL>

</BODY>

</HTML>
"""



def parse_handle(hdl):
    """Parse off options from handle.

    E.g. 'auth.subauth/path;type=url' will return
    ('auth.subauth.path', {'type': 'url'}).

    This also interprets % quoting in the non-option part.

    """
    hdl, attrs = urllib.parse.splitattr(hdl)
    d = {}
    if attrs:
        for attr in attrs:
            key, sep, value = attr.partition('=')
            if not sep:
                value = None
            else:
                value = urllib.parse.unquote(value)
            d[key.lower()] = value
    return urllib.parse.unquote(hdl, 'latin-1').encode('latin-1'), d

class hdl_access(nullAPI.null_access):

    _types = HANDLE_TYPES

    #print("Fetching global hash table")
    _global_hashtable = hdllib.fetch_global_hash_table()

    _hashtable = _global_hashtable

    _local_hashtables = {}

    def get_local_hash_table(self, hdl):
        key = hdllib.get_authority(hdl)
        if key not in self._local_hashtables:
            #print("Fetching local hash table for", key)
            self._local_hashtables[key] = hdllib.fetch_local_hash_table(
                key, self._global_hashtable)
        return self._local_hashtables[key]

    def __init__(self, hdl, method, params):
        self._msgattrs = {"title": "Ambiguous handle resolution"}
        nullAPI.null_access.__init__(self, hdl, method, params)

        self._hdl, self._attrs = parse_handle(hdl)
        self.app = grailutil.get_grailapp()

        if 'type' in self._attrs:
            t = self._attrs['type'].lower()
            mname = "hdl_type_" + t
            tname = mname.upper()
            try:
                m = self.app.get_loader('protocols').find_module(mname)
                if not m:
                    fmt = "hdlAPI: Could not load {} data type handler"
                    self._msgattrs["title"] = fmt.format(mname)
                    raise ImportError(mname)
                types = m.handle_types
                formatter = m.data_formatter
            except (ImportError, AttributeError):
                if tname in hdllib.data_map:
                    self._types = [hdllib.data_map[tname]]
                else:
                    try:
                        n = int(t)
                    except ValueError:
                        self._types = [] # Request all types
                    else:
                        self._types = [n]
            else:
                self._types = types
                if formatter:
                    self._formatter = formatter

        if 'server' in self._attrs:
            self._hashtable = hdllib.HashTable(server=self._attrs['server'])

    def pollmeta(self):
        nullAPI.null_access.pollmeta(self)
        try:
            replyflags, self._items = self._hashtable.get_data(
                self._hdl, self._types)
        except hdllib.Error as inst:
            if inst.errno == hdllib.HP_HANDLE_NOT_FOUND:
                #print("Retry using a local handle server")
                self._hashtable = self.get_local_hash_table(self._hdl)
                replyflags, self._items = self._hashtable.get_data(
                    self._hdl, self._types)
                return 'Ready', True
            raise
        else:
            return 'Ready', True

    def getmeta(self):
        nullAPI.null_access.getmeta(self)
        self._data = b""
        self._pos = 0
        return self._formatter(self)

    def formatter(self, alterego=None):
        if len(self._items) == 1 and self._items[0][0] == hdllib.HDL_TYPE_URL:
            location = self._items[0][1].decode('latin-1')
            return 302, 'Moved', {'location': location}
        if len(self._items) == 0:
            self._data = b"Handle not resolved to anything\n"
            return 404, 'Handle not resolved to anything', {}
        data = HTML_HEADER.format_map(self._msgattrs)
        for type, uri in self._items:
            if type == hdllib.HDL_TYPE_URL:
                uri = uri.decode('latin-1')
                text = '<LI><A HREF={}>{}</A>\n'.format(
                    saxutils.quoteattr(uri), saxutils.escape(uri))
            else:
                if type in (hdllib.HDL_TYPE_SERVICE_POINTER,
                            hdllib.HDL_TYPE_SERVICE_HANDLE):
                    uri = hdllib.hexstr(uri)
                else:
                    uri = escape(repr(uri))
                if type in hdllib.data_map:
                    type = hdllib.data_map[type][9:]
                else:
                    type = str(type)
                text = '<LI>type={}, value={}\n'.format(type, uri)
            data = data + text
        data = data + HTML_TRAILER
        self._data = data.encode('latin-1', 'xmlcharrefreplace')
        return 200, 'OK', {'content-type': 'text/html'}

    _formatter = formatter

    # polldata() is inherited from nullAPI

    def getdata(self, maxbytes):
        end = self._pos + maxbytes
        data = self._data[self._pos:end]
        if not data:
            return nullAPI.null_access.getdata(self, maxbytes)
        self._pos = end
        return data


# Here are some test handles:
#
# hdl:CNRI/19970131120001
# hdl:nlm.hdl_test/96053804
# hdl:cnri.dlib/december95
# hdl:cnri.dlib/november95
# hdl:nonreg.guido/python-home-page
# hdl:nonreg.guido/python-ftp-dir
