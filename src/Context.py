"""Context class."""

from urlparse import urljoin, urlparse
from Cursors import *
import History


class Context:

    """Context for browsing operations.
    
    RATIONALE: After much thinking we uncovered the need for a
    separate object to hold the browsing context.  This contains items
    like the history stack (for the back/forward commands), the loaded
    URL (for the reload command), the base URL (for interpreting
    relative links), and probably more.  These used to be stored in
    the browser object, but when introducing frames, each frame will
    need its own context.  Storing the context in the viewer won't
    work either: table cells will be implemented as viewer objects,
    but share their browsing context with the containing frame.

    Resorting to viewer subclasses, some of which would maintain their
    own context and some of which wouldn't, would require overriding
    the anchor operations (which need the context) of the context-less
    viewers.  Having a pointer to a context object in all viewers
    makes this much simpler.

    """

    def __init__(self, viewer, browser):
	self.viewer = viewer
	self.browser = browser
	self.history = History.History()
	self.history_dialog = None
	self.app = browser.app
	self.root = self.browser.root	# XXX Really a Toplevel instance
	self.readers = []
	self.page = None
	self.future = -1
	self.set_url("")

    def clear_reset(self):
	self.browser.clear_reset()
	self.set_url("")

    # Load URL, base URL and target

    def set_url(self, url, baseurl=None, target=None):
	"""Set loaded URL, base URL and target for the current page.

	The loaded URL is what this page was loaded from; the base URL
	is used to calculate relative links, and defaults to the
	loaded URL.  The target is the default viewer name
	where followed links will appear, and defaults to this viewer.

	"""
	if url:
	    self.app.global_history.remember_url(url)
	    if not self.page:
		self.page = History.PageInfo(url)
		self.history.append_page(self.page)
	    else:
		self.page.set_url(url)
		self.page.set_title("")	# Will be reset from fresh HTML
		self.history.refresh()
	else:
	    if self.future >= 0:
		self.page = self.history.page(self.future)
		self.future = -1
	    else:
		self.page = None
	self._url = self._baseurl = url
	if baseurl:
	    self._baseurl = urljoin(url, baseurl)
	self._target = target
	self.browser.set_url(self._url)

    def set_baseurl(self, baseurl=None, target=None):
	"""Set the base URL and target for the current page.

	The base URL is taken relative to the existing base URL.

	"""
	if baseurl:
	    self._baseurl = urljoin(self._baseurl, baseurl)
	if target:
	    self._target = target

    def get_baseurl(self, *relurls):
	"""Return the base URL for the current page, joined with relative URLs.

	Without arguments, return the base URL.
	
	With arguments, return the base URL joined with all of the
	arguments.  Empty arguments don't contribute.

	E.g. baseurl(x, y) == urljoin(urljoin(baseurl(), x), y).

	"""
	url = self._baseurl
	for relurl in relurls:
	    if relurl:
		url = urljoin(url, relurl)
	return url
    baseurl = get_baseurl		# XXX Backwards compatibility
    # XXX see: AppletHTMLParser, AppletLoader, Viewer, Bookmarks, isindex

    def get_target(self):
	"""Return the default target for this page (which may be None)."""
	return self._target

    # Anchor callback support

    def enter(self, url):
	"""Show the full URL of the current anchor as a message, if idle."""
	if self.readers:
	    return
	if url[:1] != '#':
	    url = urljoin(self._baseurl, url)
	self.message(url, CURSOR_LINK)

    def leave(self):
	"""Clear the message on leaving an anchor, if idle."""
	if self.readers:
	    return
	self.message("", CURSOR_NORMAL)

    def follow(self, url):
	"""Follow a link, given by a relative URL.

	If the relative URL is *just* a fragment id (#name), just
	scroll there; otherwise do a full load of a new page.

	"""
	if url[:1] == '#':
	    self.viewer.scroll_to(url[1:])
	    self.viewer.remove_temp_tag(histify=1)
	    return
	self.load(self.baseurl(url))

    # Misc

    def get_formdata(self):
	return self.page and self.page.formdata()

    # Message interfaces

    def message(self, string="", cursor=None):
	if not cursor:
	    if self.readers:
		cursor = CURSOR_WAIT
	    else:
		cursor = CURSOR_NORMAL
	self.browser.message(string, cursor)

    def message_clear(self):
	self.message("")

    def error_dialog(self, exception, msg):
	if self.app:
	    self.app.error_dialog(exception, msg, root=self.root)
	else:
	    print "ERROR:", msg

    def set_title(self, title):
	self.app.global_history.remember_url(self._url, title)
	self.browser.set_title(title)
	if self.page:
	    self.page.set_title(title)
	    self.history.refresh()

    # Handle (a)synchronous images

    def get_image(self, src):
	image = self.get_async_image(src)
	if image:
	    if not image.load_synchronously(self):
		image = None
	return image

    def get_async_image(self, src):
	if not src: return None
	url = self.baseurl(src)
	if not url: return None
	app = self.app
	image = app.get_cached_image(url)
	if image:
	    if app.load_images and not image.loaded:
		image.start_loading(self)
	    return image
	from AsyncImage import AsyncImage
	try:
	    image = AsyncImage(self, url)
	except IOError, msg:
	    image = None
	if image:
	    app.set_cached_image(url, image)
	    if app.load_images:
		image.start_loading(self)
	return image

    # Navigation/history commands

    def go_back(self, event=None):
	self.load_from_history(self.history.peek(-1))

    def go_forward(self, event=None):
	self.load_from_history(self.history.peek(+1))

    def reload_page(self):
	self.load_from_history(self.history.peek(0), reload=1)

    def load_from_history(self, (future, page), reload=0):
	self.future = future
	if not page:
	    self.root.bell()
	    return
	self.load(page.url(), reload=reload, scrollpos=page.scrollpos())

    def show_history_dialog(self):
	if not self.history_dialog:
	    self.history_dialog = History.HistoryDialog(self, self.history)
	    self.history.set_dialog(self.history_dialog)
	else:
	    self.history_dialog.show()

    def clone_history_from(self, other):
	self.history = other.history.clone()
	self.future, page = self.history.peek()
	if page:
	    self.load(page.url(), page.scrollpos())

    # Internals handle loading pages

    def save_page_state(self, reload=0):
	if not self.page: return
	# Save page scroll position
	self.page.set_scrollpos(self.viewer.scrollpos())
	# Save form contents even if reloading
	formdata = []
	if hasattr(self, 'forms'):
	    for fi in self.forms:
		formdata.append(fi.get())
	    # remove the attribute
	    del self.forms
	self.page.set_formdata(formdata)

    def read_page(self, url, method, params, show_source=0, reload=0,
		  scrollpos=None, data=None):
	from Reader import Reader
	Reader(self, url, method, params, show_source, reload, data, scrollpos)

    # Externals for loading pages

    def load(self, url, method='GET', params={},
	     show_source=0, reload=0, scrollpos=None):
	# Update state of current page, in case we re-visit it via the
	# history mechanism.
	self.save_page_state()
	# Start loading a new URL into the window
	self.stop()
	self.message("Loading %s" % url, CURSOR_WAIT)
	try:
	    self.read_page(url, method, params,
			   show_source=show_source, reload=reload,
			   scrollpos=scrollpos)
	except IOError, msg:
	    self.error_dialog(IOError, msg)
	    self.message_clear()
	    self.viewer.remove_temp_tag()

    def post(self, url, data="", params={}):
	# Post form data
	self.save_page_state()
	url = self.baseurl(url)
	method = 'POST'
	self.stop()
	self.message("Posting to %s" % url, CURSOR_WAIT)
	try:
	    self.read_page(url, method, params, reload=1, data=data)
	except IOError, msg:
	    self.error_dialog(IOError, msg)
	    self.message_clear()

    # Externals for managing list of active readers

    def addreader(self, reader):
	self.readers.append(reader)
	self.browser.allowstop()

    def rmreader(self, reader):
	if reader in self.readers:
	    self.readers.remove(reader)
	if not self.readers:
	    self.browser.clearstop()
	    self.message("Done.")
	    self.viewer.remove_temp_tag()

    def busy(self):
	return not not self.readers

    def busycheck(self):
	if self.readers:
	    self.error_dialog('Busy',
		"Please wait until the transfer is done (or stop it)")
	    return 1
	return 0

    def stop(self):
	for reader in self.readers[:]:
	    reader.kill()

    # Page interface

    def get_url(self):
	return self._url

    def get_title(self):
	return self.page and self.page.title() or self.get_url()