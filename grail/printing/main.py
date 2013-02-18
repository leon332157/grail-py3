"""HTML to PostScript translator.

This module uses the AbstractWriter class interface defined by in the
standard formatter module to generate PostScript corresponding to a
stream of HTML text.  The HTMLParser class scans the HTML stream,
generating high-level calls to an AbstractWriter object.

Note that this module can be run as a standalone script for command
line conversion of HTML files to PostScript.  Use the '-h' option to
see information about all-too-many command-line options.

"""

import os
import sys
import posixpath
import traceback
import urllib.request
import urllib.parse
import pkgutil
import subprocess
from io import TextIOWrapper

# local modules:
from . import epstools
from . import fonts                            # nested package
from . import utils
from . import PSParser
from . import PSWriter

from . import paper as printing_paper  # 'paper' used as a local

from ..grailbase.uricontext import URIContext


MULTI_DO_PAGE_BREAK = True                 # changing this breaks stuff




#  The main program.  Really needs to be broken up a bit!


def run(app):
    global logfile
    import getopt
    from . import settings
    settings = settings.get_settings(app.prefs)
    # do this after loading the settings so the user can just call
    # get_settings() w/out an arg to get a usable object.
    load_rcscript()
    context = None
    help = False
    error = 0
    logfile = None
    title = ''
    url = ''
    tabstop = None
    multi = False
    verbose = 0
    printer = None
    copies = 1
    levels = None
    outfile = None
    #
    try:
        options, args = getopt.getopt(sys.argv[1:],
                                      'mvhdcaUl:u:t:sp:o:f:C:P:T:i',
                                      ['color',
                                       'copies=',
                                       'debug',
                                       'fontsize=',
                                       'footnote-anchors',
                                       'help',
                                       'images',
                                       'logfile=',
                                       'multi',
                                       'orientation=',
                                       'output=',
                                       'papersize=',
                                       'paragraph-indent=',
                                       'paragraph-skip=',
                                       'printer=',
                                       'strict-parsing',
                                       'tab-width=',
                                       'tags=',
                                       'title=',
                                       'underline-anchors',
                                       'url=',
                                       'verbose',
                                       ])
    except getopt.error as err:
        error = 1
        help = True
        options = ()
        sys.stderr.write("option failure: {}\n".format(err))
    for opt, arg in options:
        if opt in ('-h', '--help'):
            help = True
        elif opt in ('-a', '--footnote-anchors'):
            settings.footnoteflag = not settings.footnoteflag
        elif opt in ('-i', '--images'):
            settings.imageflag = not settings.imageflag
        elif opt in ('-d', '--debug'):
            utils.set_debugging(True)
        elif opt in ('-l', '--logfile'):
            logfile = arg
        elif opt in ('-o', '--orientation'):
            settings.orientation = arg
        elif opt in ('-f', '--fontsize'):
            settings.set_fontsize(arg)
        elif opt in ('-t', '--title'):
            title = arg
        elif opt in ('-u', '--url'):
            url = arg
        elif opt in ('-U', '--underline-anchors'):
            settings.underflag = not settings.underflag
        elif opt in ('-c', '--color'):
            settings.greyscale = not settings.greyscale
        elif opt in ('-p', '--papersize'):
            settings.papersize = arg
        elif opt in ('-s', '--strict-parsing'):
            settings.strict_parsing = not settings.strict_parsing
        elif opt in ('-C', '--copies'):
            copies = int(arg)
        elif opt in ('-P', '--printer'):
            printer = arg
        elif opt in ('-T', '--tab-width'):
            tabstop = float(arg)
        elif opt in ('-m', '--multi'):
            multi = True
        elif opt in ('-v', '--verbose'):
            verbose = verbose + 1
        elif opt == '--output':
            outfile = arg
        elif opt == '--tags':
            if not load_tag_handler(app, arg):
                error = 2
                help = True
        elif opt == '--paragraph-indent':
            # negative indents should indicate hanging indents, but we don't
            # do those yet, so force to normal interpretation
            settings.paragraph_indent = max(float(arg), 0.0)
        elif opt == '--paragraph-skip':
            settings.paragraph_skip = max(float(arg), 0.0)
    if help:
        usage(settings)
        sys.exit(error)
    # crack open log file if given
    stderr = sys.stderr
    if logfile:
        try: sys.stderr = open(logfile, 'a')
        except IOError: sys.stderr = stderr
    utils.debug("Using Python version " + sys.version)
    # crack open the input file, or stdin
    outfp = None
    if printer:
        if copies < 1:
            copies = 1
        outfile = "|lpr -#{} -P{}".format(copies, printer)
    if args:
        infile = args[0]
        if args[1:]:
            multi = True
        infp, infile, outfn = open_source(infile)
        if not outfile:
            outfile = (os.path.splitext(outfn)[0] or 'index') + '.ps'
    else:
        infile = None
        infp = sys.stdin
        outfile = '-'
    #
    # open the output file
    #
    outfp = None
    proc = None
    try:
        if outfile[0] == '|':
            cmd = outfile[1:].strip()
            outfile = '|' + cmd
            proc = subprocess.Popen(cmd, shell=True, stdin=subprocess.PIPE,
                bufsize=-1)
            outfp = proc.stdin
        elif outfile == '-':
            outfp = sys.stdout.buffer
        else:
            outfp = open(outfile, 'wb')
        outfp = TextIOWrapper(outfp, 'latin-1', 'replace')
        if outfile != '-':
            print('Outputting PostScript to', outfile)

        if infile:
            context = URIContext(infile)
            if not url:
                url = infile
        else:
            # BOGOSITY: reading from stdin
            context = URIContext("file:/index.html")
        context.app = app
        paper = printing_paper.PaperInfo(settings.papersize,
                                         margins=settings.margins,
                                         rotation=settings.orientation)
        if tabstop and tabstop > 0:
            paper.TabStop = tabstop
        if utils.get_debugging('paper'):
            paper.dump()
        # create the writer & parser
        fontsize, leading = settings.get_fontsize()
        w = PSWriter.PSWriter(outfp, title or None, url or '',
                              #varifamily='Palatino',
                              paper=paper, settings=settings)
        ctype = "text/html"
        mod = app.find_type_extension("printing.filetypes", ctype)
        if not mod.parse:
            sys.exit("cannot load printing support for " + ctype)
        p = mod.parse(w, settings, context)
        if multi:
            if args[1:]:
                xform = explicit_multi_transform(args[1:])
            else:
                xform = multi_transform(context, levels)
            p.add_anchor_transform(xform)
            p.feed(infp.read())
            docs = [(context.get_url(), 1, w.ps.get_title(), 1)]
            #
            # This relies on xform.get_subdocs() returning the list used
            # internally to accumulate subdocs.  Make a copy to go only one
            # level deep.
            #
            for url in xform.get_subdocs():
                xform.set_basedoc(url)
                while p.sgml_parser.get_depth():
                    p.sgml_parser.lex_endtag(p.sgml_parser.get_stack()[0])
                try:
                    infp, url, fn = open_source(url)
                except IOError as err:
                    if verbose and outfile != '-':
                        print("Error opening subdocument", url)
                        print("   ", err)
                else:
                    new_ctype = get_ctype(app, url, infp)
                    if new_ctype != ctype:
                        if verbose:
                            print("skipping", url)
                            print("  wrong content type:", new_ctype)
                        continue
                    if verbose and outfile != '-':
                        print("Subdocument", url)
                    w.ps.close_line()
                    # must be true for now, not sure why
                    if MULTI_DO_PAGE_BREAK:
                        pageend = w.ps.push_page_end()
                        context.set_url(url)
                        w.ps.set_pageno(w.ps.get_pageno() + 1)
                        w.ps.set_url(url)
                        w.ps.push_page_start(pageend)
                    else:
                        context.set_url(url)
                        w.ps.set_url(url)
                    pageno = w.ps.get_pageno()
                    p.feed(infp.read())
                    infp.close()
                    title = w.ps.get_title()
                    p._set_docinfo(url, pageno, title)
                    spec = (url, pageno, title, xform.get_level(url))
                    docs.append(spec)
        else:
            p.feed(infp.read())
        p.close()
        w.close()
    finally:
        if outfp:
            outfp.close()
        if proc:
            proc.wait()



#  Lots of helper functions....


def load_tag_handler(app, arg):
    loader = app.get_loader("html.postscript")
    narg = os.path.join(os.getcwd(), arg)
    if os.path.isdir(narg):
        loader.add_directory(narg)
    elif os.path.isfile(narg):
        basename, ext = os.path.splitext(narg)
        if ext != ".py":
            sys.stdout = sys.stderr
            print("Extra tags must be defined in a"
                   " Python source file with '.py' extension.")
            print()
            return False
        dirname, modname = os.path.split(basename)
        mloader = pkgutil.get_importer(dirname).find_module(modname)
        if not mloader:
            raise ImportError("Cannot load {!r}".format(narg))
        mod = mloader.load_module(modname)
        loader.load_tag_handlers(mod)
    else:
        sys.stdout = sys.stderr
        print("Could not locate tag handler", arg)
        print()
        print("Argument to --tags must be a directory to be added to the html")
        print("package or a file containing tag handler functions.  The tag")
        print("handlers defined in the directory or file will take precedence")
        print("over any defined in other extensions.")
        print()
        return False
    return True


def get_ctype(app, url, infp):
    """Attempt to determine the MIME content-type as best as possible."""
    try:
        return infp.info()["content-type"]
    except (AttributeError, KeyError):
        return app.guess_type(url)[0]


def load_rcscript():
    try:
        from .. import grailutil
    except ImportError:
        return
    graildir = grailutil.getgraildir()
    userdir = os.path.join(graildir, "user")
    if os.path.isdir(userdir):
        sys.path.insert(0, userdir)
        try:
            import html2psrc
        except ImportError:
            pass
        except:
            traceback.print_exc()
            sys.stderr.write("[Traceback generated in html2psrc module.]\n")


def open_source(infile):
    try:
        infp = open(infile, 'r')
    except IOError:
        # derive file object via URL; still needs to be HTML.
        infp = urllib.request.urlopen(infile)
        infile = getattr(infp, "url", infile)
        infp = TextIOWrapper(infp, 'latin-1')
        # use posixpath since URLs are expected to be POSIX-like; don't risk
        # that we're running on NT and os.path.basename() doesn't "do the
        # right thing."
        fn = posixpath.basename(urllib.parse.urlparse(infile).path)
    else:
        fn = posixpath.basename(infile)
    return infp, infile, fn


class multi_transform:
    def __init__(self, context, levels=None):
        self.__app = context.app
        baseurl = context.get_baseurl()
        scheme, netloc, path, params, query, frag = urllib.parse.urlparse(
            baseurl)
        self.__scheme = scheme
        self.__netloc = netloc.lower()
        self.__path = os.path.dirname(path)
        self.__subdocs = []
        self.__max_levels = levels
        self.__level = 0
        self.__docs = {baseurl: 0}

    def __call__(self, url, attrs):
        scheme, netloc, path, params, query, frag = urllib.parse.urlparse(
            url)
        if params or query:             # safety restraint
            return url
        netloc = netloc.lower()
        if scheme != self.__scheme or netloc != self.__netloc:
            return url
        # check the paths:
        stored_url = urllib.parse.urlunparse(
            (scheme, netloc, path, '', '', ''))
        if stored_url in self.__docs:
            return url
        if not path.startswith(self.__path):
            return url
        if (not self.__max_levels) \
           or (self.__max_levels and self.__level < self.__max_levels):
            self.__docs[stored_url] = self.__level + 1
            self.insert(stored_url)
        return url

    def get_subdocs(self):
        return self.__subdocs

    __base_index = None
    def set_basedoc(self, url):
        level = self.__docs.get(url, 1)
        self.__level = level
        self.__current_base = url
        try:
            self.__base_index = self.__subdocs.index(url)
        except ValueError:
            self.__base_index = None

    def insert(self, url):
        if self.__base_index is not None:
            i = self.__base_index + 1
            scheme, netloc, path, x, y, z = urllib.parse.urlparse(url)
            basepath = os.path.dirname(path)
            while i < len(self.__subdocs):
                scheme, netloc, path, x, y, z = urllib.parse.urlparse(
                    self.__subdocs[i])
                path = os.path.dirname(path)
                i = i + 1
                if path != basepath:
                    break
            self.__subdocs.insert(i, url)
            return
        self.__subdocs.append(url)

    def get_level(self, url):
        return self.__docs[url]


class explicit_multi_transform:
    def __init__(self, subdocs):
        self.__subdocs = list(subdocs)

    def __call__(self, url, attrs):
        return url

    def get_subdocs(self):
        return list(self.__subdocs)

    def set_basedoc(self, url):
        pass

    def get_level(self, url):
        return 1


def usage(settings):
    progname = os.path.basename(sys.argv[0])
    print('Usage:', progname, '[options] [file-or-url]')
    print('    -u: URL for footer')
    print('    -t: title for header')
    print('    -a: toggle anchor footnotes (default is {})'.format(
          _onoff(settings.footnoteflag)))
    print('    -U: toggle anchor underlining (default is {})'.format(
          _onoff(settings.underflag)))
    print('    -o: orientation; portrait, landscape, or seascape')
    print('    -p: paper size; letter, legal, a4, etc.', end=' ')
    print('(default is {})'.format(settings.papersize))
    print('    -f: font size, in points (default is {}/{})'.format(
          *settings.get_fontsize()))
    print('    -d: turn on debugging')
    print('    -l: logfile for debugging, otherwise stderr')
    line = '    -s: toggle "advanced" SGML recognition (default is {})'
    print(line.format(_onoff(settings.strict_parsing)))
    print('    -T: size of tab stop in points (default is {})'.format(
          printing_paper.PaperInfo.TabStop))
    print('    -P: specify output printer')
    print('    -m: descend tree starting from specified document,')
    print('        printing all HTML documents found')
    print('    -h: this help message')
    print('[file]: file to convert, otherwise from stdin')


def _onoff(bool):
    return "ON" if bool else "OFF"


#  main() & relations....


from .. import BaseApplication


class Application(BaseApplication.BaseApplication):
    def __init__(self, prefs=None):
        BaseApplication.BaseApplication.__init__(self, prefs)
        from .. import GlobalHistory
        self.global_history = GlobalHistory.GlobalHistory(
            self, readonly=True)

    def exception_dialog(self, message='', *args):
        traceback.print_exc()
        if message:
            sys.stderr.write(message + "\n")


def main():
    app = Application()
    try:
        run(app)
    except KeyboardInterrupt:
        if utils.get_debugging():
            app.exception_dialog()
        sys.exit(1)


def profile_main(n=18):
    import profile, pstats
    print("Running under profiler....")
    profiler = profile.Profile()
    try:
        profiler.runctx('main()', globals(), locals())
    finally:
        sys.stdout = logfile
        profiler.dump_stats('@html2ps.prof')
        p = pstats.Stats('@html2ps.prof')
        p.strip_dirs().sort_stats('time').print_stats(n)
        p.print_callers(n)
        p.sort_stats('cum').print_stats(n)
