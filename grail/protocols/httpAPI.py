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
import email.parser
from .. import grailutil
import select
from .. import Reader
import re
import socket
from .. import GRAILVERSION


replypat = br'HTTP/1\.[0-9.]+[ \t]+([0-9][0-9][0-9])(.*)'
replyprog = re.compile(replypat)


# Search for blank line following HTTP headers
endofheaders = re.compile(br'\n[ \t]*\r?\n')


# Stages
# there are now five stages
WAIT = 'wait'  # waiting for a socket
META = 'meta'
DATA = 'data'
DONE = 'done'
CLOS = 'closed'


def simplereply(url):
    """Return (code, reason, headers) for a HTTP 0.9 reply based on URL"""
    headers = {}
    app = grailutil.get_grailapp()
    c_type, c_encoding = app.guess_type(url)
    if c_encoding:
        headers['content-encoding'] = c_encoding
    # HTTP/0.9 sends HTML by default
    headers['content-type'] = c_type or "text/html"
    return 200, "OK", headers


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
            assert method == "POST"
        else:
            assert method in ("GET", "POST")
        if isinstance(resturl, tuple):
            host, self.selector = resturl    # For proxy interface
        else:
            host, self.selector = splithost(resturl)
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
        self.h = http.client.HTTPConnection(host)

        # Grail does not currently seem to handle HTTP 1.1's persistent
        # connections, nor chunked transfer encoding
        self.h._http_vsn = 10
        self.h._http_vsn_str = 'HTTP/1.0'

        self.h.putrequest(method, self.selector)
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
        self.readahead = bytearray()
        self.state = META
        self.line1seen = False
        self.reply = None
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
            self.reply = simplereply(self.selector)
            return "EOF in server response", True
        self.readahead.extend(new)
        if b'\n' not in new:
            return "receiving server response", False
        if not self.line1seen:
            self.line1seen = True
            line, rest = self.readahead.split(b'\n', 1)
            m = replyprog.match(line)
            if not m:
                # Not an HTTP/1.0 response.  Fall back to HTTP/0.9.
                self.reply = simplereply(self.selector)
                return "received non-HTTP/1.0 server response", True
            self.errcode, self.errmsg = m.group(1, 2)
            self.errcode = int(self.errcode)
            self.errmsg = self.errmsg.decode('latin-1').strip()
            self.readahead = rest
        m = endofheaders.search(self.readahead)
        if m and m.start() >= 0:
            headers = self.readahead[:m.end()].decode('latin-1')
            del self.readahead[:m.end()]
            parser = email.parser.Parser()
            headers = parser.parsestr(headers, headersonly=True)
            self.reply = self.errcode, self.errmsg, headers
            return "received server response", True
        return "receiving server response", False

    def getmeta(self):
        assert self.state == META
        if not self.reply:
            x, y = self.pollmeta(None)
            while not y:
                x, y = self.pollmeta(None)
        self.state = DATA
        return self.reply

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
