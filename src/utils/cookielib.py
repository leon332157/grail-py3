"""Utilities to read & write Netscape cookie files.

This can be used to implement client-side cookie handling.
"""
__author__ = "Fred L. Drake, Jr. <fdrake@acm.org>"
__version__ = '$Revision: 2.1 $'

import time
import ht_time


class Error(Exception):
    def __init__(self, message, *args):
        self.message = message
        Exception.__init__(self, (message,) + args)

class FormatError(Error):
    def __init__(self, message, lineno):
        self.lineno = lineno
        Error.__init__(self, message, lineno)

class CapacityError(Error):
    pass


def load(fp, db=None):
    """Load a cookies database from a file."""
    if db is None:
        db = CookieDB()
    db.load(fp)
    return db


BANNER = """# Netscape HTTP Cookie File
# http://www.netscape.com/newsref/std/cookie_spec.html
# This is a generated file!  Do not edit.

"""

def is_special_domain(domain):
    """Determine if hosts in the given top-level domain are allowed to
    have fewer name parts."""
    return len(domain) == 3


class CookieDB:
    def __init__(self, filename=None, fp=None, caps=None):
        self.__cookies = {}
        self.__num_cookies = 0
        self.set_capacities(caps)
        self.set_filename(filename)
        if fp is not None:
            self.load(fp)
        elif filename:
            self.load()

    def get_capacities(self):
        return self.__caps.copy()

    def set_capacities(self, caps=None):
        if caps is None:
            caps = Capacities()
        self.__caps = caps

    def set_filename(self, filename):
        self.__filename = filename

    def load(self, fp=None):
        if fp is None:
            fp = open(self.get_filename())
        pos = fp.tell()
        try:
            line = fp.readline()
        finally:
            fp.seek(pos)
        if line[:5] == "<?XML":
            self.load_xml(fp)
        else:
            self.load_ns(fp)

    def load_ns(self, fp=None):
        lineno = 0
        while 1:
            line = fp.readline()
            if not line:
                break
            lineno = lineno + 1
            if line[0] == '#':
                continue
            line = line.strip()
            if not line:
                continue
            parts = line.split('\t')
            if len(parts) != 7:
                raise FormatError("wrong number of fields", lineno)
            domain, isdomain, path, secure, expires, name, value = parts
            expires = int(expires)
            # This doesn't perform the same test for true, but perform the
            # same test Mozilla makes.
            secure = secure != 'FALSE'
            cookie = Cookie(domain, path, secure, expires, name, value)
            self.set_cookie(cookie)

    def save(self, fp=None):
        if fp is None:
            fp = open(self.__filename, 'w')
        fp.write(BANNER)
        for cookie in self.all_cookies():
            if cookie.expires is not None:
                isdomain = cookie.isdomain and 'TRUE' or 'FALSE'
                secure = cookie.secure and 'TRUE' or 'FALSE'
                expires = format(cookie.expires)
                l = [cookie.domain, isdomain, cookie.path, secure,
                     expires, cookie.name, cookie.value]
                s = '\t'.join(l)
                fp.write(s + '\n')

    def set_cookie(self, cookie):
        if hasattr(cookie, 'discard') or cookie.max_age == 0:
            return self.discard(cookie)
        # need to enforce capacities here!
        caps = self.__caps
        if len(cookie.name) > caps.max_cookie_size:
            raise CapacityError("cookie name too long")
        # truncate cookie value if necessay:
        max_value_len = caps.max_cookie_size - len(cookie.name)
        cookie.value = cookie.value[:max_value_len]
        try:
            cookies = self.__cookies[cookie.domain]
        except KeyError:
            self.__cookies[cookie.domain] = [cookie]
            self.__num_cookies = self.__num_cookies + 1
        else:
            for i in range(len(cookies)):
                c = cookies[i]
                if c.name == cookie.name and c.path == cookie.path:
                    cookies[i] = cookie
                    break
            else:
                if len(cookies) >= caps.num_per_server:
                    self.__expire_cookies(cookies)
                if len(cookies) == caps.num_per_server:
                    # need to remove one more!
                    mcookies = cookies[:]
                    mcookies.sort(lambda l, r: cmp(l.expires, r.expires))
                    for c, i in mcookies:
                        if c.expires:
                            cookies.remove(c)
                            break
                    else:
                        # all are per-session; just toss the first one
                        del cookies[0]
                    self.__num_cookies = self.__num_cookies - 1
                cookies.append(cookie)
                self.__num_cookies = self.__num_cookies + 1

    def discard(self, cookie):
        try:
            cookies = self.__cookies[cookie.domain]
        except KeyError:
            return
        for i in range(cookies):
            c = cookies[i]
            if c.name == cookie.name and c.path == cookie.path:
                del cookies[i]
                self.__num_cookies = self.__num_cookies - 1
                break

    def lookup(self, domain, path='/', secure=0):
        domain = domain.lower()
        hostparts = domain.split('.')
        results = self.__match_path(domain, path)
        minparts = 3
        if is_special_domain(hostparts[-1]):
            minparts = 2
        while len(hostparts) > minparts:
            del hostparts[0]
            key = '.'.join([''] + hostparts)
            results[len(results):] = self.__match_path(key, path)
        if not secure:
            results = filter(lambda c: not c.secure, results)
        return results

    def __expire_cookies(self, cookies):
        """Remove expired cookies from a list if they've expired.  Current
        database size is adjusted, so only call this on lists which are
        part of the database.  The resulting list is limited to the number
        of cookies allowed for a single domain."""
        now = int(time.time())
        old_len = len(cookies)
        indexes = range(old_len)
        indexes.reverse()
        for i in indexes:
            cookie = cookies[i]
            if cookie.expires is not None \
               and cookie.expires < now:
                del cookies[i]
        # should trim list back if there are too many:
        num_per_server = self.__caps.num_per_server
        if len(cookies) > num_per_server:
            # sort on expiration
            ncookies = cookies[:]
            ncookies.sort(lambda l, r: cmp(l.expires, r.expires))
            for cookie in ncookies:
                if cookie.expires:
                    cookies.remove(cookies)
                    if len(cookies) == num_per_server:
                        break
        if len(cookies) > num_per_server:
            # still too many; just toss the first few in the list
            del cookies[:-num_per_server]
        self.__num_cookies = self.__num_cookies + len(cookies) - old_len

    def __make_room(self, howmany):
        remove = (self.__num_cookies - self.__caps.max_cookies) + howmany
        # Expire cookies until we've killed off enough,
        # if that'll do the trick.
        domains = self.all_domains()
        while remove > 0 and domains:
            cookies = self.__cookies[domains.pop(0)]
            num_cookies = len(cookies)
            self.__expire_cookies(cookies)
            remove = remove - (num_cookies - len(cookies))
        if remove > 0:
            # need to be more aggressive
            pass

    def __match_path(self, domain, path):
        results = []
        try:
            cookies = self.__cookies[domain]
        except KeyError:
            pass
        else:
            if cookies:
                self.__expire_cookies(cookies)
            if cookies:
                for cookie in cookies:
                    if len(path) >= len(cookie.path) \
                       and cookie.path == path[:len(cookie.path)]:
                        results.append(cookie)
            else:
                # nothing left in domain
                del self.__cookies[domain]
        if results:
            results.sort(lambda l,r: cmp(len(r.path), len(l.path)))
            results.reverse()
        return results

    def all_domains(self):
        return self.__cookies.keys()

    def all_cookies(self):
        results = []
        for d in self.all_domains():
            cookies = self.__cookies[d]
            self.__expire_cookies(cookies)
            if cookies:
                results[len(results):] = cookies
            else:
                # nothing left; remove the domain
                del self.__cookies[d]
        return results


class Capacities:
    """Representation of database capacity settings."""

    num_per_server = 20
    max_cookie_size = 4096
    max_cookies = 300

    def copy(self):
        import copy
        return copy.copy(self)


class Cookie:
    max_age = None

    def __init__(self, domain, path, secure, expires,
                 name, value, others=None):
        self.domain = domain and domain.lower()
        self.isdomain = domain and domain[0] == '.'
        self.path = path
        self.secure = secure
        self.expires = expires and int(expires) or None
        self.name = name
        self.value = value
        if others:
            for k, v in others.items():
                setattr(self, k, v)


import re
_name_rx = re.compile(r"\s*(?P<value>[A-Z][-A-Z0-9]*)", re.IGNORECASE)
_value_rx = re.compile(r"\s*=\s*(?P<value>[^;,\s]+)\s*")
# RFC 850 date format...
_date_rx = re.compile(
    r"""\s*=\s*(\"|'|)\s*
        (?P<value>[A-Z]+,\s*\d+-[A-Z]+-\d+\s+\d+:\d+:\d+(?:\s+GMT)?)
        \s*(?:\1\s*)""",
    re.IGNORECASE | re.VERBOSE)
del re


def parse_cookies(s):
    results = []
    s = s.strip()
    while s:
        c, s = parse_cookie(s)
        results.append(c)
        s = s.strip()
        if s:
            if s[0] == ",":
                s = s[1:].strip()
            else:
                raise ValueError, "illegal cookie separator"
    return results


def parse_cookie(s):
    """Return the first cookie in the string and any unparsed data."""
    domain = None
    path = None
    secure = 0
    expires = None
    name = None
    value = None
    max_age = None
    others = {}
    #
    name, pos = _get_name(s)
    value, pos = _get_value(s, pos)
    if value is None:
        raise ValueError, "no value for cookie"
    s = s[pos:].strip()
    pos = 0
    if s and s[0] == ';':
        # look for parameters
        pos = 1
    while s:
        k, pos = _get_name(s, pos)
        k = k.lower()
        if k == "expires":
            expires, pos = _get_value(s, pos, _date_rx)
            if expires is None:
                raise ValueError, "missing or unrecognized expiration date"
            expires = ht_time.parse(expires)
        else:
            v, pos = _get_value(s, pos)
        #
        if k == 'secure':
            secure = 1
        elif k == 'path':
            path = v
        elif k == 'domain':
            domain = v.lower()
        elif k == 'max-age':
            max_age = int(v)
        elif k == 'expires':
            # don't fall into 'others'
            pass
        else:
            others[k] = v
        #
        s = s[pos:].strip()
        if s and s[0] != ';':
            break
        if s:
            # discard ';'
            s = s[1:].strip()
    if domain and domain[0] == '.':
        minparts = 3
        hostparts = '.'.split(domain)
        del hostparts[0]
        if hostparts[-1] in SPECIAL_DOMAINS:
            minparts = 2
        if len(hostparts) < minparts:
            raise ValueError, "too few components in domain specification"
    # prefer max-age over expires
    if max_age:
        expires = int(time.time()) + max_age
    others["max_age"] = max_age
    return Cookie(domain, path, secure, expires, name, value, others), s


def _get_name(s, start=0):
    m = _name_rx.match(s, start)
    if not m:
        raise ValueError, "could not extract name"
    return m.group(1), m.end()


def _get_value(s, start=0, value_rx=_value_rx):
    value = None
    m = value_rx.match(s, start)
    if m:
        value = m.group('value')
        start = m.end()
    return value, start



def testcgi():
    """CGI program that can be used to test a browser's cookie support.
    Call this as the main program of a CGI script."""
    import cgi
    print "Set-Cookie: key=value"
    print "Set-Cookie: another=thing"
    cgi.test()
    print
    print "<p> This is the <code>cookielib</code> module's"
    print "<code>testcgi()</code> function."


# Testing stuff.  The following things really need testing:
#
# - Capacity handling:
#   - eviction policy needs to be tested (and documented); some issues need
#     to be resolved still.
# - Parsing of dates following expires parameter with various quoting.

if __name__ == "__main__":
    test()
