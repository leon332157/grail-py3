from .Cache import SharedItem, SharedAPI
import urlparse
import os
import time
from . import ht_time
from . import grailutil
import re
from numbers import Real

META, DATA, DONE = 'META', 'DATA', 'DONE' # Three stages

class CacheEmpty(Exception):
    def __str__(self): return 'Cache Empty'
class CacheReadFailed(Exception):
    def __str__(self): return 'Cache Item Expired or Missing: {}'.format(
        Exception.__str__(self))
class CacheFileError(Exception):
    def __str__(self):
        return 'Cache File Error: {}'.format(Exception.__str__(self))


from mimetypes import guess_extension


def parse_cache_control(s):
    elts = s.split(',')
    for s in elts:
        a, _, b = s.partition('=')
        yield (a, b)

class CacheManager:
    """Manages one or more caches in hierarchy.

    The only methods that should be used by the application is
    open() and add_cache(). Other methods are intended for use by the
    cache itself.  

    overview of CacheManager and Cache organization

    CM has list of caches (could have more than one cache)
    
    items = {}: contains an entry for all the URLs in all the
    caches. value is a cache entry object (cf DiskCacheEntry
    below), has a get method that returns an protocol API object

    active = {}: contains an entry for each URL that is open in a
    browser window. this is the shared object list. if there is a
    request for an active page, a second SharedAPI for the same object
    is returned. the list stores SharedItems, which contain a reference
    count; when that cound reaches zero, it removes itself from the
    list. 

    freshness: CM is partly responsible for checking the freshness of
    pages. (pages with explicit TTL know when they expire.) freshness
    tests are preference driven, can be never, per session, or per
    time-unit. on each open, check to see if we should send an
    If-Mod-Since to the original server (based on fresh_p method).

    """
    
    def __init__(self, app):
        """Initializes cache manager, creates disk cache.

        Basic disk cache characteristics loaded from    """
        
        self.app = app
        self.caches = []
        self.items = {}
        self.active = {}
        self.disk = None
        self.disk = DiskCache(self, self.app.prefs.GetInt('disk-cache',
                                                     'size') * 1024,
                         self.app.prefs.Get('disk-cache', 'directory'))
        self.set_freshness_test()
        self.app.prefs.AddGroupCallback('disk-cache', self.update_prefs)

        # check preferences
        bool = self.app.prefs.GetInt('disk-cache', 'checkpoint')
        if bool:
            self.app.register_on_exit(lambda save=self.save_cache_state:save())

    def save_cache_state(self):
        for cache in self.caches:
            cache._checkpoint_metadata()

    def update_prefs(self):
        self.set_freshness_test()
        size = self.caches[0].max_size = self.app.prefs.GetInt('disk-cache',
                                                               'size') \
                                                               * 1024
        new_dir = self.app.prefs.Get('disk-cache', 'directory')
        if new_dir != self.disk.pref_dir:
            self.disk._checkpoint_metadata()
            self.reset_disk_cache(size, new_dir)

    def reset_disk_cache(self, size=None, dir=None, flush_log=False):
        """Close the current disk cache and open a new one.

        Used primarily to change the cache directory or to clear
        everything out of the cache when it is erased. The flush_log
        argument is passed to DiskCache.close(), allowing this routine
        to be used in both of the cases described. On erase, we want
        to write a new, empty log; on change directory, we want to
        keep the old log intact.
        """
        if not size:
            size = self.disk.max_size
        if not dir:
            dir = self.disk.directory
        self.disk.close(flush_log)
        self.disk = DiskCache(self, size, dir)
        
    def set_freshness_test(self):
        # read preferences to determine when pages should be checked
        # for freshness -- once per session, every n secs, or never
        fresh_type = self.app.prefs.Get('disk-cache', 'freshness-test-type')
        fresh_rate = int(self.app.prefs.GetFloat('disk-cache', 
                                             'freshness-test-period') * 3600.0)

        if fresh_type == 'per session':
            self.fresh_p = lambda key, self=self: \
                           self.fresh_every_session(self.items[key])
            self.session_freshen = []
        elif fresh_type == 'periodic':
            self.fresh_p = lambda key, self=self, t=fresh_rate: \
                           self.fresh_periodic(self.items[key],t)  
        elif fresh_type == 'never':
            self.fresh_p = lambda x: True
        else: #         == 'always'
            self.fresh_p = lambda x: False

    def open(self, url, mode, params, reload=False, data=None):
        """Opens a URL and returns a protocol API for it.

        This is the method called by the Application to load a
        URL. First, it checks the shared object list (and returns a
        second reference to a URL that is currently active). Then it
        calls open routines specialized for GET or POST.
        """

        key = self.url2key(url, mode, params)
        if mode == 'GET':
            if key in self.active:
                # XXX This appeared to be a bad idea!
##              if reload:
##                  self.active[key].reset()
                return SharedAPI(self.active[key])
            return self.open_get(key, url, mode, params, reload, data)
        elif mode == 'POST':
            return self.open_post(key, url, mode, params, reload, data)

    def open_get(self, key, url, mode, params, reload, data):
        """open() method specialized for GET request.

        Performs several steps:
        1. Check for the URL in the cache.
        2. If it is in the cache,
              1. Create a SharedItem for it.
              2. Reload the cached copy if reload flag is on.
              3. Refresh the page if the freshness test fails.
           If it isn't in the cache,
              1. Create a SharedItem (which will create a CacheEntry 
              after the page has been loaded.)
        3. call activate(), which adds the URL to the shared object
        list and creates a SharedAPI for the item
        """

        try:
            api = self.cache_read(key)
        except CacheReadFailed as err:
            (cache,) = err.args
            cache.evict(key)
            api = None
        if api:
            # creating reference to cached item
            try:
                if reload:
                    item = SharedItem(url, mode, params, self, key, data,
                                     api, reload=reload)
                    self.touch(key)
                elif not self.fresh_p(key):
                    item = SharedItem(url, mode, params, self, key, data,
                                     api, refresh=self.items[key].lastmod)
                    self.touch(key,refresh=True)
                else:
                    item = SharedItem(url, mode, params, self, key, data,
                        api)
            except:
                api.close()
                raise
        else:
            # cause item to be loaded (and perhaps cached)
            item = SharedItem(url, mode, params, self, key, data)

        return self.activate(item)

    def open_post(self, key, url, mode, params, reload, data):
        """Open a URL with a POST request. Do not cache."""
        key = self.url2key(url, mode, params)
        return self.activate(SharedItem(url, mode, params, None, key,
                                       data))

    def activate(self,item):
        """Adds a SharedItem to the shared object list and returns SharedAPI.
        """
        self.active[item.key] = item
        return SharedAPI(self.active[item.key])

    def deactivate(self,key):
        """Removes a SharedItem from the shared object list."""
        self.active.pop(key, None)

    def add_cache(self, cache):
        """Called by cache to notify manager this it is ready."""
        self.caches.append(cache)

    def close_cache(self, cache):
        self.caches.remove(cache)

    def cache_read(self,key):
        """Checks cache for URL. Returns protocol API on hit.

        Looks for a cache entry object in the items dictionary. If the
        CE object is found, call its method get() to create a protocol
        API for the item.
        """
        if key in self.items:
            return self.items[key].get()
        else:
            return None

    def touch(self,key=None,url=None,refresh=False):
        """Calls touch() method of CacheEntry object."""
        if url:
            key = self.url2key(url,'GET',{})
        if key and key in self.items:
            self.items[key].touch(refresh)

    def expire(self,key):
        """Should not be used."""
        assert 'night' == 'day'
        assert key in self.items
        self.items[key].evict()

    def delete(self, keys, evict=True):
        if isinstance(keys, str):
            keys = [keys]

        if evict:
            for key in keys:
                try:
                    self.items[key].cache.evict(key)
                except KeyError:
                    pass
        else:
            for key in keys:
                self.items.pop(key, None)

    def add(self,item,reload=False):
        """If item is not in the cache and is allowed to be cached, add it. 
        """
        try:
            if item.key not in self.items and self.okay_to_cache_p(item):
                self.caches[0].add(item)
            elif reload:
                self.caches[0].update(item)
        except CacheFileError, err_tuple:
            (file, err) = err_tuple
            print("error adding item %s (file %s): %s" % (item.url,
                                                          file, err))

    # list of protocols that we can cache
    cache_protocols = ['http', 'ftp', 'hdl']

    def okay_to_cache_p(self,item):
        """Check if this item should be cached.

        This routine probably (definitely) needs more thought.
        Currently, we do not cache URLs with the following properties:
        1. The scheme is not on the list of cacheable schemes.
        2. The item is bigger than a quarter of the cache size.
        3. The 'Pragma: no-cache' header was sent
        4. The 'Expires: 0' header was sent
        5. The URL includes a query part '?'
        
        """

        if len(self.caches) < 1:
            return False

        (scheme, netloc, path, parm, query, frag) = \
                 urlparse.urlparse(item.url)

        if query or scheme not in self.cache_protocols:
            return False

        # don't cache really big things
        #####
        ##### limit is hardcoded, please fix
        #####
        if item.datalen > self.caches[0].max_size / 4:
            return False

        code, msg, params = item.meta

        # don't cache things that don't want to be cached
        pragma = params.get('pragma')
        if pragma == 'no-cache':
            return False

        expires = params.get('expires')
        if expires == 0:
            return False

        # respond to http/1.1 cache control directives
        if 'cache-control' in params:
            for k, v in parse_cache_control(params['cache-control']):
                if k in  ('no-cache', 'no-store'):
                    return False
                if k == 'max-age':
                    expires = int(v)

        return True

    def fresh_every_session(self,entry):
        """Refresh the page once per session"""
        if not entry.key in self.session_freshen:
            self.session_freshen.append(entry.key)
            return False
        return True

    def fresh_periodic(self,entry,max_age):
        """Refresh it max_age seconds have passed since it was loaded."""
        try:
            age = time.time() - entry.date.get_secs()
            if age > max_age:
                return False
            return True
        except AttributeError:
            # if you don't tell me the date, I don't tell you it's stale
            return True

    def url2key(self, url, mode, params):
        """Normalize a URL for use as a caching key.

        - change the hostname to all lowercase
        - remove the port if it is the scheme's default port
        - reformat the port using %d
        - get rid of the fragment identifier

        """
        parsed = urlparse.urlparse(url)
        try:
            port = parsed.port
        except ValueError:
            port = None
        if port is None or parsed.scheme == 'http' and port == 80:
            netloc = parsed.hostname
        else:
            netloc = parsed.hostname + ":%d" % port
        return urlparse.urlunparse((parsed.scheme, netloc, parsed.path,
            parsed.params, parsed.query, ""))


class DiskCacheEntry:
    """Data about item stored in a disk cache.

    __init__ only store the cache this entry is in. To place real data
    in a cache item, you must call fill() to create a new item. 

    The DiskCacheEntry object is shared by the DiskCache and the
    CacheManager. The method get() is called by the
    CacheManager and change the state of the DiskCache.

    The data members include:
    date -- the date of the most recent HTTP request to the server
    (either a regular load or an If-Modified-Since request)
    """

    def __init__(self, cache=None):
        self.cache = cache

    def fill(self,key,url,size,date,lastmod,expires,ctype,
             cencoding,ctencoding):
        self.key = key
        self.url = url
        self.size = size
        if date:
            self.date = HTTime(date)
        else:
            self.date = None
        if lastmod:
            self.lastmod = HTTime(lastmod)
        else:
            self.lastmod = None
        if expires:
            self.expires = HTTime(expires)
        else:
            self.expires = None
        self.type = ctype
        self.encoding = cencoding
        self.transfer_encoding = ctencoding

    string_date = re.compile('^[A-Za-z]')

    def __repr__(self):
        return self.unparse()

    def parse(self,parsed_rep):
        """Reads transaction log entry.
        """
        vars = parsed_rep.split('\t')
        self.key = vars[0]
        self.url = vars[1]
        self.file = vars[2]
        self.size = int(vars[3])
        self.type = vars[7]
        try:
            self.encoding = vars[8]
        except IndexError:
            # log version 1.2
            self.encoding = None
            self.transfer_encoding = None
        else:
            if self.encoding == 'None':
                self.encoding = None
            try:
                self.transfer_encoding = vars[9]
            except IndexError:
                self.transfer_encoding = None
            else:
                if self.transfer_encoding == 'None':
                    self.transfer_encoding = None
        self.date = None
        self.lastmod = None
        self.expires = None
        for tup in [(vars[4], 'date'), (vars[5], 'lastmod'),
                     (vars[6], 'expires')]:
            self.parse_assign(tup[0],tup[1])

    def parse_assign(self,rep,var):
        if rep == 'None':
            setattr(self,var,None)
            return
        match = self.string_date.match(rep)
        if match and match.start() == 0:
            setattr(self,var,HTTime(str=rep))
        else:
            setattr(self,var,HTTime(secs=float(rep)))

    def unparse(self):
        """Return entry for transaction log.
        """
        if not hasattr(self, 'file'):
            self.file = ''
        stuff = [self.key, self.url, self.file, self.size, self.date,
                 self.lastmod, self.expires, self.type, self.encoding,
                 self.transfer_encoding]
        s = '\t'.join(map(str, stuff))
        return s

    def get(self):
        """Create a disk_cache_access API object and return it.

        Calls cache.get() to update the LRU information.

        Also checks to see if a page with an explicit Expire date has
        expired; raises a CacheReadFailed if it has.
        """
        if self.expires:
            if self.expires and self.expires.get_secs() < time.time():
                # we need to refresh the page; can we just reload?
                raise CacheReadFailed, self.cache
        self.cache.get(self.key) 
        try:
            api = disk_cache_access(self.cache.get_file_path(self.file),
                                    self.type, self.date, self.size,
                                    self.encoding, self.transfer_encoding)
        except IOError:
            raise CacheReadFailed, self.cache
        return api

    def touch(self,refresh=False):
        """Change the date of most recent check with server."""
        self.date = HTTime(secs=time.time())
        if refresh:
            self.cache.log_entry(self)

    def delete(self):
        pass

def expire_key(item):
    """used with list.sort() to sort list of CacheEntries by expiry date."""
    return item.expires.get_secs()

class DiskCache:
    """Persistent object cache.

    need to discuss:

    use_order

    the log: writes every change to cache or use_order, writes
    flushed, do a checkpoint run on startup, format is tuple (entry
    type, object), where entry type is add, evict, update use_order,
    version. 

    expires

    evict

    Note: Nowhere do we verify that the disk has enough space for a
    full cache.

    """

    def __init__(self, manager, size, directory):
        self.max_size = size
        self.size = 0
        self.pref_dir = directory
        if hasattr(os.path, 'expanduser'):
                directory = os.path.expanduser(directory)
        if not os.path.isabs(directory):
                directory = os.path.join(grailutil.getgraildir(), directory)
        self.directory = directory
        self.manager = manager
        self.manager.add_cache(self)
        self.items = {}
        self.use_order = []
        self.log = None
        self.expires = []
        self.types = {}

        grailutil.establish_dir(self.directory)
        self._read_metadata()
        self._reinit_log()

    log_version = "1.3"
    log_ok_versions = ["1.2", "1.3"]

    def close(self,log):
        self.manager.delete(self.items.keys(), evict=False)
        if log:
            self.use_order = []
            self._checkpoint_metadata()
        del self.items
        del self.expires
        self.manager.close_cache(self)
        self.dead = True

    def _read_metadata(self):
        """Read the transaction log from the cache directory.

        Reads the pickled log entries and re-creates the cache's
        current contents and use_order from the log.

        A version number is included, but currently we only assert
        that the version number read is the same as the current
        version number.
        """
        logpath = os.path.join(self.directory, 'LOG')
        try:
            log = open(logpath)
        except IOError:
            # now what happens if there is an error here?
            log = open(logpath, 'w')
            log.close()
            return

        with log:
            for line in log:
                try:
                    kind = line[0:1]        
                    if kind == '2': # use update
                        key = line[2:-1]
                        self.use_order.remove(key)
                        self.use_order.append(key)
                    elif kind == '1':           # delete
                        key = line[2:-1]
                        if key in self.items:
                            self.size = self.size - self.items.pop(key).size
                            del self.manager.items[key]
                            self.use_order.remove(key)
                            assert key not in self.use_order
                    elif kind == '0': # add
                        newentry = DiskCacheEntry(self)
                        newentry.parse(line[2:-1])
                        if newentry.key not in self.items:
                            self.use_order.append(newentry.key)
                        newentry.cache = self
                        self.items[newentry.key] = newentry
                        self.manager.items[newentry.key] = newentry
                        self.size = self.size + newentry.size
                    elif kind == '3': # version (hopefully first)
                        ver = line[2:-1]
                        if ver not in self.log_ok_versions:
                       ### clear out anything we might have read
                       ### and bail. this is an old log file.
                            if len(self.use_order) > 0:
                                self.use_order = []
                                for key in self.items.keys():
                                    del self.manager.items[key]
                                self.items.clear()
                                self.size = 0
                                return
                        assert ver in self.log_ok_versions
                except IndexError:
                    # ignore this line
                    pass

    def _checkpoint_metadata(self):
        """Checkpoint the transaction log.

        Creates a new log that contains only the current state of the
        cache.
        """
        import traceback
        if self.log:
            self.log.close()
        try:
            newpath = os.path.join(self.directory, 'CHECKPOINT')

            with open(newpath, 'w') as newlog:
                newlog.write('3 ' + self.log_version + '\n')
                for key in self.use_order:
                    self.log_entry(self.items[key],alt_log=newlog,
                        flush=False)
                    # don't flush writes during the checkpoint, because if
                    # we crash it won't matter
            logpath = os.path.join(self.directory, 'LOG')
            os.unlink(logpath)
            os.rename(newpath, logpath)
        except:
            print("exception during checkpoint")
            traceback.print_exc()

    def _reinit_log(self):
        """Open the log for writing new transactions."""
        logpath = os.path.join(self.directory, 'LOG')
        self.log = open(logpath, 'a')

    def log_entry(self,entry,delete=False,alt_log=None,flush=True):
        """Write to the log adds and evictions."""
        if alt_log:
            dest = alt_log
        else:
            dest = self.log
        if delete:
            dest.write('1 ' + entry.key + '\n')
        else:
            dest.write('0 ' + entry.unparse() + '\n')
        if flush:
            dest.flush()

    def log_use_order(self,key):
        """Write to the log changes in use_order."""
        if key in self.items:
            self.log.write('2 ' + key + '\n')
            # should we flush() here? probably...
            self.log.flush()

    cache_file = re.compile(r'^spam[0-9]+')

    def erase_cache(self):

        if hasattr(self,'dead'):
            # they got me
            self.manager.disk.erase_cache()
            return

        for dir,_,files in os.walk(self.directory):
            for file in files:
                if self.cache_file.match(file):
                    path = os.path.join(dir,file)
                    os.unlink(path)

        self.manager.reset_disk_cache(flush_log=True)

    def erase_unlogged_files(self):

        if hasattr(self,'dead'):
            # they got me
            self.manager.disk.erase_unlogged_files()
            return

        known = { 'LOG' }
        known.update(entry.file for entry in self.items.values())

        for dir,_,files in os.walk(self.directory):
            for file in files:
                if file not in known and self.cache_file.match(file):
                    path = os.path.join(dir,file)
                    os.unlink(path)

    def get(self,key):
        """Update and log use_order."""
        assert key in self.items
        self.use_order.remove(key)
        self.use_order.append(key)
        self.log_use_order(key)

    def update(self,object):
        # this is simple, but probably not that efficient
        self.evict(object.key)
        self.add(object)

    def add(self,object):
        """Creates a DiskCacheEntry for object and adds it to cache.

        Examines the object and its headers for size, date, type,
        etc. The DiskCacheEntry is placed in the DiskCache and the
        CacheManager and the entry is logged.

        XXX Need to handle replacement better?
        """
        respcode, msg, headers = object.meta
        size = object.datalen

        self.make_space(size)

        newitem = DiskCacheEntry(self)
        (date, lastmod, expires, ctype, cencoding, ctencoding) \
               = self.read_headers(headers)
        newitem.fill(object.key, object.url, size, date, lastmod,
                     expires, ctype, cencoding, ctencoding)
        newitem.file = self.get_file_name(newitem)
        if expires:
            self.add_expireable(newitem)

        self.make_file(newitem,object)
        self.log_entry(newitem)

        self.items[object.key] = newitem
        self.manager.items[object.key] = newitem
        self.use_order.append(object.key)

        return newitem

    def read_headers(self,headers):
        if 'date' in headers:
            date = headers['date']
        else:
            date = time.time()

        lastmod = headers.get('last-modified', date)

        expires = headers.get('expires')

        # what is the proper default content type?
        ctype = headers.get('content-type', 'text/html')

        cencoding = headers.get('content-encoding')

        ctencoding = headers.get('content-transfer-encoding')

        return (date, lastmod, expires, ctype, cencoding, ctencoding)


    def add_expireable(self,entry):
        """Adds entry to list of pages with explicit expire date."""
        self.expires.append(entry)

    def get_file_name(self,entry):
        """Invent a filename for a new cache entry."""
        filename = 'spam' + str(time.time()) + self.get_suffix(entry.type)
        return filename

    def get_file_path(self,filename):
        path = os.path.join(self.directory, filename)
        return path

    def get_suffix(self,type):
        if type in self.types:
            return self.types[type]
        else:
            return guess_extension(type) or ''

    def make_file(self,entry,object):
        """Write the object's data to disk."""
        path = self.get_file_path(entry.file)
        try:
            with open(path, 'wb') as f:
                f.writelines(object.data)
        except IOError, err:
            raise CacheFileError, (path, err)

    def make_space(self,amount):
        """Ensures that there are amount bytes free in the disk cache.

        If the cache does not have amount bytes free, pages are
        evicted. First, we check the list of pages with explicit
        expire dates and evict any that have expired. If we need more
        space, evict the least recently used page. Continue LRU
        eviction until enough space is available.

        Raises CacheEmpty if there are no entries in the cache, but
        amount bytes are not available.
        """

        if self.size + amount > self.max_size:
            self.evict_expired_pages()

        try:
            while self.size + amount > self.max_size:
                self.evict_any_page()
        except CacheEmpty:
            print("Can't make more room in the cache")
            pass
            # this is not the right thing to do, probably
            # but I don't think this should ever happen
        self.size = self.size + amount

    def evict_any_page(self):
        """Evict the least recently used page."""
        # get ride of least-recently used thing
        if len(self.items) > 0:
            key = self.use_order[0]
            self.evict(key)
        else:
            raise CacheEmpty

    def evict_expired_pages(self):
        """Evict any pages on the expires list that have expired."""
        self.expires.sort(key=expire_key)
        size = len(self.expires)
        if size > 0 \
           and self.expires[0].expires.get_secs() < time.time():
            index = 0
            t = time.time()
            while index < size and self.expires[index].expires.get_secs() < t:
                index = index + 1
            for item in self.expires[0:index]:
                self.evict(item.key)
            del self.expires[0:index]

    def evict(self,key):
        """Remove an entry from the cache and delete the file from disk."""
        self.use_order.remove(key)
        evictee = self.items.pop(key)
        del self.manager.items[key]
        if key in self.expires:
            self.expires.remove(key)
        try:
            os.unlink(self.get_file_path(evictee.file))
        except EnvironmentError as err:
            # print("error deleting %s from cache: %s" % (key, err))
            pass
        self.log_entry(evictee,delete=True)
        evictee.delete()
        self.size = self.size - evictee.size

class disk_cache_access:
    """protocol access interface for disk cache"""

    def __init__(self, filename, content_type, date, len,
                 content_encoding, transfer_encoding):
        self.headers = { 'content-type' : content_type,
                         'date' : date,
                         'content-length' : str(len) }
        if content_encoding:
            self.headers['content-encoding'] = content_encoding
        if transfer_encoding:
            self.headers['content-transfer-encoding'] = transfer_encoding
        self.filename = filename
        try:
            self.fp = open(filename, 'rb')
        except IOError, err:
            print("io error opening %s: %s" % (filename, err))
            # propogate error through
            raise IOError, err
        self.state = DATA

    def pollmeta(self):
        return "Ready", True

    def getmeta(self):
        return 200, "OK", self.headers

    def polldata(self):
        return "Ready", True

    def getdata(self,maxbytes):
        # get some data from the disk
        data = self.fp.read(maxbytes)
        if not data:
            self.state = DONE
        return data

    def fileno(self):
        try:
            return self.fp.fileno()
        except AttributeError:
            return -1

    def close(self):
        fp = self.fp
        self.fp = None
        if fp:
            fp.close()

    def tk_img_access(self):
        """Return the cached filename and content-type.

        Used by AsyncImage to create Tk image objects directly from
        the file in the disk cache.
        """
        return self.filename, self.headers['content-type']

class HTTime:
    """Stores time as HTTP string or seconds since epoch or both.

    Lazy conversions from one format to the other.
    """
    # HTTP defines three date formats, but only one is supposed to be
    # produced by an HTTP application. (The other two you're supposed to
    # handle for backwards compatibility.) It would be nice to accept
    # the two old date formats as str input and convert them to the
    # preferred format.

    def __init__(self,any=None,str=None,secs=None):
        if any:
            if isinstance(any, type('')):
                str = any
            elif isinstance(any, Real):
                secs = any
        if str:
            self.str = str
        else:
            self.str = None
        if secs:
            self.secs = secs
        else:
            self.secs = None

    def get_secs(self):
        if not self.secs:
            try:
                self.secs = ht_time.parse(self.str)
            except:
                # if there is a parsing error, we bail
                self.secs = 0
        return self.secs

    def get_str(self):
        if not self.str:
            self.str = ht_time.unparse(self.secs)
        return self.str

    def __repr__(self):
        if self.secs:
            return str(self.secs)
        elif self.str:
            return self.str
        else:
            return str(None)
