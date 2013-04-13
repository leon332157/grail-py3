"""Provisional HTTP interface using the new protocol API.

XXX This was hacked together in an hour so I would have something to
test ProtocolAPI.py.  Especially the way it uses knowledge about the
internals of httplib.HTTP is disgusting (but then, so would editing
the source of httplib.py be :-).

XXX Main deficiencies:

- poll*() always returns ready
- should read the headers more carefully (no blocking)
- (could even *write* the headers more carefully)
- should poll the connection making part too

"""


import http.client
from urllib.parse import splithost
import mimetools
from .. import grailutil
import select
from .. import Reader
import re
import StringIO
import socket
from .. import GRAILVERSION


replypat = r'HTTP/1\.[0-9.]+[ \t]+([0-9][0-9][0-9])(.*)'
replyprog = re.compile(replypat)


# Search for blank line following HTTP headers
endofheaders = re.compile(r'\n[ \t]*\r?\n')


# Stages
# there are now five stages
WAIT = 'wait'  # waiting for a socket
META = 'meta'
DATA = 'data'
DONE = 'done'
CLOS = 'closed'

class MyHTTPConnection(http.client.HTTPConnection):

    def putrequest(self, request, selector):
        self.selector = selector
        http.client.HTTPConnection.putrequest(self, request, selector)

    def getreply(self, file):
        """Copies from older httplib.HTTP.getreply() API"""
        self.file = file
        line = self.file.readline()
        if self.debuglevel > 0: print('reply:', repr(line))
        m = replyprog.match(line)
        if m is None:
            # Not an HTTP/1.0 response.  Fall back to HTTP/0.9.
            # Push the data back into the file.
            self.file.seek(-len(line), 1)
            self.headers = {}
            app = grailutil.get_grailapp()
            c_type, c_encoding = app.guess_type(self._conn.selector)
            if c_encoding:
                self.headers['content-encoding'] = c_encoding
            # HTTP/0.9 sends HTML by default
            self.headers['content-type'] = c_type or "text/html"
            return 200, "OK", self.headers
        errcode, errmsg = m.group(1, 2)
        errcode = int(errcode)
        errmsg = errmsg.strip()
        self.headers = mimetools.Message(self.file, 0)
        return errcode, errmsg, self.headers

    def close(self):
        if self.file:
            self.file.close()
        self.file = None
        http.client.HTTPConnection.close(self)


class http_access:

    def __init__(self, resturl, method, params, data=None):
        self.app = grailutil.get_grailapp()
        self.args = (resturl, method, params, data)
        self.state = WAIT
        self.h = None
        self.reader_callback = None
        self.app.sq.request_socket(self, self.open)

    def register_reader(self, reader_callback, ignore):
        if self.state == WAIT:
            self.reader_callback = reader_callback
        else:
            # we've been waitin' fer ya
            reader_callback()

    def open(self):
        assert self.state == WAIT
        resturl, method, params, data = self.args
        if data:
            assert method=="POST"
        else:
            assert method in ("GET", "POST")
        if isinstance(resturl, tuple):
            host, selector = resturl    # For proxy interface
        else:
            host, selector = splithost(resturl)
        if not host:
            raise IOError("no host specified in URL")
        user_passwd, sep, host = host.partition('@')
        if sep:
            import base64
            user_passwd = user_passwd.encode("latin-1")
            auth = base64.encodebytes(user_passwd).strip().decode("ascii")
        else:
            host = user_passwd
            auth = None
        self.h = MyHTTPConnection(host)
        self.h.putrequest(method, selector)
        self.h.putheader('User-agent', GRAILVERSION)
        if auth:
            self.h.putheader('Authorization', 'Basic {}'.format(auth))
        if 'host' not in params:
            self.h.putheader('Host', host)
        if 'accept-encoding' not in params:
            encodings = Reader.get_content_encodings()
            if encodings:
                encodings.sort()
                self.h.putheader('Accept-Encoding', ", ".join(encodings))
        for key, value in params.items():
            if not key.startswith('.'):
                self.h.putheader(key, value)
        self.h.putheader('Accept', '*/*')
        self.h.endheaders()
        if data:
            self.h.send(data)
        self.readahead = ""
        self.state = META
        self.line1seen = False
        if self.reader_callback:
            self.reader_callback()

    def close(self):
        if self.h:
            self.h.close()
        if self.state != CLOS:
            self.app.sq.return_socket(self)
            self.state = CLOS
        self.h = None

    def pollmeta(self, timeout=0):
        assert self.state == META

        sock = self.h.sock
        try:
            if not select.select([sock], [], [], timeout)[0]:
                return "waiting for server response", False
        except select.error as msg:
            raise IOError(msg) from msg
        new = sock.recv(1024)
        if not new:
            return "EOF in server response", True
        self.readahead = self.readahead + new
        if '\n' not in new:
            return "receiving server response", False
        if not self.line1seen:
            self.line1seen = True
            line = self.readahead.split('\n', 1)[0]
            if not replyprog.match(line):
                return "received non-HTTP/1.0 server response", True
        m = endofheaders.search(self.readahead)
        if m and m.start() >= 0:
            return "received server response", True
        return "receiving server response", False

    def getmeta(self):
        assert self.state == META
        if not self.readahead:
            x, y = self.pollmeta(None)
            while not y:
                x, y = self.pollmeta(None)
        file = StringIO.StringIO(self.readahead)
        errcode, errmsg, headers = self.h.getreply(file)
        self.state = DATA
        self.readahead = file.read()
        return errcode, errmsg, headers

    def polldata(self):
        assert self.state == DATA
        if self.readahead:
            return "processing readahead data", True
        return ("waiting for data",
                bool(select.select([self], [], [], 0)[0]))

    def getdata(self, maxbytes):
        assert self.state == DATA
        if self.readahead:
            data = self.readahead[:maxbytes]
            self.readahead = self.readahead[maxbytes:]
            return data
        data = self.h.sock.recv(maxbytes)
        if not data:
            self.state = DONE
            # self.close()
        return data

    def fileno(self):
        return self.h.sock.fileno()


# To test this, use ProtocolAPI.test()
