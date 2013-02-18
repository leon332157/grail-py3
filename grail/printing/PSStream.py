__version__ = '$Revision: 1.6 $'

from . import fonts                            # a package
from . import utils                            # || module
import os
import re
from . import settings
import sys
import time
import urllib.parse
from numbers import Real
from io import StringIO
from collections import Iterable


RECT_DEBUG = False

SYSTEM_DATA_DIR = os.path.join(os.path.dirname(__file__), "data")


# Load the PostScript prologue:
def get_systemheader():
    options = settings.get_settings()
    fn = utils.which(
        "header.ps", list(options.user_data_dirs) + [SYSTEM_DATA_DIR])
    if fn:
        with open(fn) as file:
            return file.read()
    return "%\%  System header {} not found!\n%".format(fn)


USERHEADER_INFO = """\
%
% This is custom header material was loaded from:
%      {}
%"""

# Allow the user to provide supplemental prologue material:
def get_userheader():
    options = settings.get_settings()
    templates = []
    for fn in settings.get_settings().user_headers:
        filename = utils.which(fn, options.user_data_dirs)
        if filename:
            templates.append(USERHEADER_INFO.format(fn))
            with open(filename) as file:
                templates.append(file.read())
    return '\n'.join(templates)


# Regular expressions.
QUOTE_re = r'(\(|\)|\\)'

def cook(string):
    return re.sub(QUOTE_re, r'\\\1', string)


# Keep images that come above the ascenders for the current line
# from clobbering the descenders of the line above by allowing the
# font height * PROTECT_DESCENDERS_MULTIPLIER.  This should be a
# reasonable percentage of the font height.
#
PROTECT_DESCENDERS_MULTIPLIER = 0.20


ALIGN_LEFT = 'left'
ALIGN_CENTER = 'center'
ALIGN_RIGHT = 'right'

# horizontal rule spacing, in points
HR_TOP_MARGIN = 4.0
HR_BOT_MARGIN = 2.0

# paragraph rendering
PARAGRAPH_SEPARATION = 1.0              # * base-font-size

# distance after a label tag in points
LABEL_TAB = 6.0


class PSStream:
    _margin = 0.0
    _rmargin = 0.0
    _leading = 0.0                      # "external" leading == between lines
    _align = ALIGN_LEFT
    _inliteral_p = False
    _render = 'S'                       # S == normal string, U == underline

    # current line state; we really need some good comments about these....
    _space_width = 0.0
    _baseline = None
    _descender = 0.0
    _xpos = 0.0
    _ypos = 0.0
    _vtab = _leading                    # extra vertical tab before the line
    _lineshift = 0.0                    # adjustment at start of line

    def __init__(self, psfont, ofp, title='', url='', paper=None):
        self._paper = paper
        self._font = psfont
        self._ofp = ofp
        self.set_title(title)
        # strip any fragment identifiers from the url, and pre-cook:
        self.set_url(url)
        # current line state
        self._linestr = []
        self._yshift = [(0.0, 0.0)]     # vertical baseline shift w/in line
        self._linefp = StringIO()
        self._base_font_size = self.get_fontsize()
        self._line_start_font = self._font.get_font()

    __pageno = 1
    def get_pageno(self):
        return self.__pageno

    def set_pageno(self, pageno):
        utils.debug("========== new page number: {}\n".format(pageno))
        self.__pageno = pageno

    __titles = None
    def set_title(self, title):
        # replace all whitespace sequences with a single space
        title = ' '.join(title.split())
        if self.__titles is None:
            self.__titles = [title]
        else:
            self.__titles.append(title)

    def get_title(self):
        return self.__titles[0]

    def prune_titles(self):
        del self.__titles[:-1]

    def set_url(self, url):
        parsed = urllib.parse.urlparse(url)[:3] + ('', '', '')
        self._url_cooked = cook(urllib.parse.urlunparse(parsed))

    def start(self):
        # print document preamble
        print("%!PS-Adobe-1.0", file=self._ofp)
        if self.get_title():
            print("%%Title:", self.get_title(), file=self._ofp)
        # output font prolog
        print("%%DocumentPaperSizes:", self._paper.PaperName, file=self._ofp)
        self._ofp.write("%%DocumentFonts: Symbol ZapfDingbats")
        docfonts = self._font.docfonts
        for dfv in docfonts.values(): self._ofp.write(" " + dfv)
        self._ofp.write("\n")
        # spew out the contents of the header PostScript file
        print(get_systemheader(), file=self._ofp)
        # define the fonts
        print("/scalfac", self._font.points_per_pixel, "D", file=self._ofp)
        for key, value in docfonts.items():
            print("/{} /{} dup reencodeISO D findfont D".format(key, value),
                file=self._ofp)
        # finish out the prolog with paper information:
        for name, value in vars(self._paper).items():
            if isinstance(value, str):
                print("/Gr{} ({}) D".format(name, value), file=self._ofp)
            else:
                print("/Gr{} {} D".format(name, value), file=self._ofp)
        # Add time information to allow the printing functions to include
        # 'date printed' to the footers if desired.  We need a way to get
        # the last-modified time of the document from the context headers,
        # but these are not available to us at this point.
        print("%%\n%% time values for use by page decorating functions:",
            file=self._ofp)
        names = ("Year", "Month", "Day", "Hour", "Minute", "Second",
                 "Weekday", "Julian", "DST")
        t = time.time()
        local = time.localtime(t)
        utc = time.gmtime(t)
        for name, local, utc in zip(names, local, utc):
            print("/Gr{} {} D /GrUTC{} {} D".format(name, local, name, utc),
                file=self._ofp)
        # add per-user customization:
        user_template = get_userheader()
        if user_template:
            print(user_template, file=self._ofp)
        print("%%EndProlog", file=self._ofp)
        self.print_page_preamble()
        self.push_font_change(None)     # ??? why ???

    def get_fontsize(self):
        return self._font.font_size()

    def get_pageheight(self):
        return self._paper.ImageHeight

    def get_pagewidth(self):
        return self._paper.ImageWidth - self._margin - self._rmargin

    def set_leading(self, value):
        # `value' is the "internal" leading: for '10 on 12', pass in 12;
        # the stored value is the "external" leading.  This is only computed
        # here.  The external leading is restricted to non-negative values
        # to ensure at least some level of sanity.
        self._leading = max(0.0, value - self._base_font_size)

    def push_eps(self, img, align=None):
        """Insert encapsulated postscript in stream."""
        if self._linestr:
            self.close_string()
        if align not in ('absmiddle', 'baseline', 'middle', 'texttop', 'top'):
            align = 'bottom'

        # constrain image size to fit on page:
        width, height = img.get_size()
        xscaling, yscaling = settings.get_settings().get_scaling()
        if xscaling:
            img.restrict(height=height * xscaling)
        if yscaling:
            img.restrict(width=width * yscaling)
        pagewidth = self.get_pagewidth()
        img.restrict(width=pagewidth, height=self.get_pageheight())

        extra = PROTECT_DESCENDERS_MULTIPLIER * self.get_fontsize()
        above_portion, below_portion, vshift = 0.5, 0.5, 0.0
        if align == 'absmiddle':
            vshift = self.get_fontsize() / 2.0
        elif align in ('bottom', 'baseline'):
            above_portion, below_portion = 1.0, 0.0
        elif align != 'middle':
            # ALIGN in 'top', 'texttop'
            above_portion, below_portion, extra = 0.0, 1.0, 0.0
            vshift = self.get_fontsize()

        width, height = img.get_size()
        above = above_portion * height
        below = (below_portion * height) - vshift

        # Check space available:
        if width > (pagewidth - self._xpos):
            self.close_line()
        # Update page availability info:
        imgshift = above + self._yshift[-1][0] + vshift + extra
        if self._baseline is None:
            self._baseline = imgshift
        else:
            self._baseline = max(self._baseline, imgshift)
        self._descender = max(self._descender, below - self._yshift[-1][0])
        self._xpos = self._xpos + width
        ll_x, ll_y, ur_x, ur_y = img.bbox
        #
        xscale, yscale = img.get_scale()
        # Translate & scale for image origin (maybe should add
        # some cropping?  just assuming image is reasonable):
        print('gsave\n currentpoint {} sub translate {} {} scale'.format(
              below, xscale, yscale), file=self._linefp)
        if ll_x or ll_y:
            #  Have to translate again to make image happy:
            print(' {} {} translate'.format(-ll_x, -ll_y), file=self._linefp)
        if img.data[-1] == '\n':
            img.data = img.data[:-1]
        print(img.data, file=self._linefp)
        #  Restore context, move to right of image:
        print('grestore {} 0 R'.format(width), file=self._linefp)

    def push_font_string(self, s, font):
        if not font:
            self.push_string_flowing(s)
            return
        if self._linestr:
            self.close_string()
        if font not in self._font.fontobjs:
            self._font.fontobjs[font] = fonts.font_from_name(font)
        fontobj = self._font.fontobjs[font]
        size = self.get_fontsize()
        width = fontobj.text_width(size, s)
        if self._xpos + width > self.get_pagewidth():
            self.close_line()
        if self._baseline is None:
            self._baseline = size
        else:
            self._baseline = max(self._baseline, size)
        fmt = 'gsave\n /{} findfont {} scalefont setfont '
        self._linefp.write(fmt.format(font, size))
        fmt = '({}) show\ngrestore {} 0 R\n'
        self._linefp.write(fmt.format(cook(s), width))
        self._xpos = self._xpos + width

    def push_alignment(self, align):
        if align == 'right':
            self._align = ALIGN_RIGHT
        elif align == 'center':
            self._align = ALIGN_CENTER
        else:
            self._align = ALIGN_LEFT

    def push_yshift(self, yshift):
        """Adjust the current baseline relative to the real baseline.

        The `yshift' parameter is a float value specifying the adjustment
        relative to the current virtual baseline.  Use pop_yshift() to
        undo the effects of the adjustment.
        """
        if self._linestr:
            self.close_string()
        yshift = 1.0 * yshift
        self._linefp.write('0 {} R\n'.format(yshift))
        absshift = self._yshift[-1][0] + yshift
        self._yshift.append((absshift, yshift))
        newheight = absshift + self.get_fontsize()
        if self._baseline is None:
            self._baseline = max(0.0, newheight)
        else:
            self._baseline = max(self._baseline, newheight)
        if absshift < 0.0:
            if self._descender is None:
                self._descender = -absshift
            else:
                self._descender = max(self._descender, -absshift)

    def pop_yshift(self):
        if self._linestr:
            self.close_string()
        self._linefp.write('0 {} R\n'.format(-self._yshift.pop()[1]))

    def push_end(self):
        self.close_line()
        self.print_page_postamble()
        print("%%Trailer", file=self._ofp)
        print("%%Pages:", self.get_pageno(), file=self._ofp)
        print("%%EOF", file=self._ofp)

    def push_font_change(self, font):
        if self._linestr:
            self.close_string()
        if self._baseline is None and self._xpos != 0.0:
            self._baseline = self.get_fontsize() \
                             + max(0.0, self._yshift[-1][0])
        psfontname, size = self._font.set_font(font)
        self._linefp.write('{} {} SF\n'.format(psfontname, size))
        self._space_width = self._font.text_width(' ')
        newfontsize = size + max(0.0, self._yshift[-1][0])
        if self._baseline is None:
            self._baseline = newfontsize
        else:
            self._baseline = max(self._baseline, newfontsize)

    def push_space(self, spaces=1):
        # spaces at the beginning of a line are thrown away, unless we
        # are in literal text.
        if self._inliteral_p or self._xpos > 0.0:
            self._linestr.append(' ' * spaces)
            self._xpos = self._xpos + self._space_width * spaces

    def push_horiz_rule(self, abswidth=None, percentwidth=None,
                        height=None, align=None):
        if isinstance(height, Real):
            height = 0.5 * max(height, 1)       # each unit is 0.5pts
        else:
            height = 1                          # 2 "units"
        old_align = self._align
        if align is not None:
            self.push_alignment(align)
        self._baseline = HR_TOP_MARGIN + height
        descent = PROTECT_DESCENDERS_MULTIPLIER * self.get_fontsize()
        self._vtab = max(self._vtab, descent)
        self._descender = HR_BOT_MARGIN
        pagewidth = self.get_pagewidth()
        if abswidth:
            width = min(1.0 * abswidth, pagewidth)
        elif percentwidth:
            width = min(1.0, percentwidth) * pagewidth
        else:
            width = pagewidth
        if self._align is ALIGN_LEFT:
            start = 0.0
        elif self._align is ALIGN_CENTER:
            start = (pagewidth - width) / 2
        else:   #  ALIGN = right
            start = pagewidth - width
        self._linefp.write('{} {} {} HR\n'.format(
                           height, start + self._margin, width))
        self.close_line()
        self._align = old_align
        self._xpos = 0.0

    def push_horiz_space(self, width):
        # `width' is in points
        if self._linestr:
            self.close_string()
        max_width = self.get_pagewidth()
        if self._xpos + width > max_width:
            self.close_line()
        self._linefp.write("{} 0 R\n".format(width))
        self._xpos = self._xpos + width

    def push_margin(self, level):
        if self._linestr:
            self.close_string()
        distance = level * self._paper.TabStop
        if self._margin != distance:
            self._margin = distance
            self._ofp.write('/grIndentMargin {} D CR\n'.format(distance))

    def push_rightmargin(self, level):
        if self._linestr:
            self.close_string()
        self._rmargin = level * self._paper.TabStop

    def push_paragraph(self, blankline, parskip):
        if blankline and self._ypos:
            self._vtab = max(self._vtab, (self._base_font_size * parskip))

    def push_label(self, bullet):
        if self._linestr:
            self.close_string()
        if isinstance(bullet, str):
            #  Simple textual bullet:
            distance = self._font.text_width(bullet) + LABEL_TAB
            self._linefp.write('gsave CR -{} 0 R ({}) S grestore\n'.format(
                               distance, cook(bullet)))
        elif isinstance(bullet, Iterable):
            #  Font-based dingbats:
            string, font = bullet
            self._linefp.write('gsave\n CR {} {} SF\n'.format(
                               font, int(self.get_fontsize())))
            self._linefp.write(' ({}) dup\n'.format(cook(string)))
            fmt = ' stringwidth pop -{} E sub 0 R S\ngrestore\n'
            self._linefp.write(fmt.format(LABEL_TAB))
        else:
            #  This had better be an EPSImage object!
            max_width = self._paper.TabStop - LABEL_TAB
            bullet.restrict(height=0.9 * self.get_fontsize())
            width, height = bullet.get_size()
            distance = width + LABEL_TAB
            xscale, yscale = bullet.get_scale()
            #  Locate new origin:
            vshift = (self.get_fontsize() - height) / 2.0
            self._linefp.write("gsave\n CR -{} {} R currentpoint translate "
                               "{} {} scale\n".format(
                               distance, vshift, xscale, yscale))
            ll_x, ll_y, ur_x, ur_y = bullet.bbox
            if ll_x or ll_y:
                #  Have to translate again to make image happy:
                self._linefp.write(' {} {} translate\n'.format(-ll_x, -ll_y))
            self._linefp.write(bullet.data)
            self._linefp.write("grestore\n")

    def push_hard_newline(self):
        self.close_line()

    def push_underline(self, flag):
        render = 'U' if flag else 'S'
        if self._render != render and self._linestr:
            self.close_string()
        self._render = render

    def push_literal(self, flag):
        if self._inliteral_p != flag and self._linestr:
            self.close_string()
        self._inliteral_p = flag

    def push_string_flowing(self, data):
        allowed_width = self.get_pagewidth()
        # special case getting it on one line:
        tw = self._font.text_width(data)
        if tw <= (allowed_width - self._xpos):
            self._linestr.append(data)
            self._xpos = self._xpos + tw
            return
        # local variable cache
        text_width = self._font.text_width
        linestr = self._linestr
        append = linestr.append
        xpos = self._xpos
        # must break line; just do it by "words" as best we understand them
        words = data.split(' ')
        wordcnt = len(words) - 1
        space_width = self._space_width
        for word in words:
            width = text_width(word)
            # Does the word fit on the current line?
            if xpos + width < allowed_width:
                append(word)
                xpos = xpos + width
            # The current line, with the additional text, is too
            # long.  We need to figure out where to break the
            # line.  If the previous text was a space, and the
            # current line width is > 75% of the page width, and
            # the current text is smaller than the page width,
            # then just break the line at the last space.
            # (Checking the last whitespace char against a tab is
            # unnecessary; data is de-tabbed before this method is
            # called.)
            elif linestr and linestr[-1] and \
                 linestr[-1][-1] == ' ' and \
                 xpos > allowed_width * 0.75 and \
                 width < allowed_width:
                #
                # output the current line data (removes trailing space)
                #
                linestr[-1] = linestr[-1][:-1]
                self._xpos = xpos - space_width
                self.close_line(linestr=linestr)
                # close_line() touches these, but we're using a
                # local variable cache, which must be updated.
                xpos = width
                linestr = [word]
                append = linestr.append
            # Try an alternative line break strategy.  If we're
            # closer than 75% of the page width to the end of the
            # line, then start a new line, print the word,
            # possibly splitting the word if it is longer than a
            # single line.
            else:
                # only force a break immediately if it buys us something:
                if width < allowed_width:
                    self._xpos = xpos
                    self.close_line(linestr=linestr)
                    # close_line() touches these, but we're using a
                    # local variable cache, which must be updated.
                    xpos = 0.0
                    linestr = []
                    append = linestr.append
                while width > allowed_width:
                    # make our best guess as to the longest bit of
                    # the word we can write on a line.
                    if self._inliteral_p:
                        append(word)
                        self._xpos = width
                        word = ''
                    else:
                        average_charwidth = width / len(word)
                        chars_on_line = int(allowed_width
                                            / average_charwidth)
                        s = word[:chars_on_line]
                        # ugly!
                        if s and s[-1].isalpha():
                            s = s + "-"
                        append(s)
                        self._xpos = text_width(s)
                        word = word[chars_on_line:]
                    # now write the word
                    self.close_line(linestr=linestr)
                    # close_line() touches these, but we're using a
                    # local variable cache, which must be updated.
                    xpos = 0.0
                    linestr = []
                    append = linestr.append
                    width = text_width(word)
                append(word)
                xpos = width
            # for every word but the last, put a space after it
            # inlining push_space() for speed
            if wordcnt > 0 and (self._inliteral_p or xpos > 0.0):
                append(' ')
                xpos = xpos + space_width
            wordcnt = wordcnt - 1
        # undo effects of caching variables:
        self._linestr = linestr
        self._xpos = xpos

    def push_string(self, data):
        lines = data.split('\n')
        linecnt = len(lines) - 1
        for line in lines:
            # do flowing text
            self.push_string_flowing(line)
            # for every line but the last, put a hard newline after it
            if linecnt:
                self.push_hard_newline()
            linecnt = linecnt - 1

    def print_page_preamble(self):
        # write the structure page convention
        pageno = self.get_pageno()
        print('%%Page:', pageno, pageno, file=self._ofp)
        print('%%BeginPageProlog', file=self._ofp)
        psfontname, size = self._line_start_font
        print("save", self._margin, psfontname, size, pageno, "NP",
            file=self._ofp)
        print('%%EndPageProlog', file=self._ofp)
        if RECT_DEBUG:
            print('gsave', 0, 0, "M", file=self._ofp)
            print(self._paper.ImageWidth, 0, "RL", file=self._ofp)
            print(0, -self._paper.ImageHeight, "RL", file=self._ofp)
            print(-self._paper.ImageWidth, 0, "RL closepath stroke newpath",
                file=self._ofp)
            print('grestore', file=self._ofp)

    def print_page_postamble(self):
        title = ''
        url = self._url_cooked
        if self.get_pageno() != 1:
            title = cook(self.get_title())
        self.prune_titles()
        self._ofp.write("({})\n({})\n{} EP\n".format(
                        url, title, self.get_pageno()))

    def push_page_end(self):
        # self._baseline could be None
        linesz = (self._baseline or 0.0) + self._descender + self._vtab
        self._ypos = self._ypos - linesz
        self.print_page_postamble()
        return linesz

    def push_page_start(self, linesz):
        self.print_page_preamble()
        self._ypos = -linesz
        self._vtab = self._leading

    def push_page_break(self):
        linesz = self.push_page_end()
        self.set_pageno(self.get_pageno() + 1)
        self.push_page_start(linesz)

    def close_line(self, linestr=None):
        if linestr is None:
            linestr = self._linestr
        if linestr:
            self.close_string(linestr)
        baseline = self._baseline
        yshift = self._yshift[-1][0]
        if baseline is None:
            baseline = self.get_fontsize() + max(yshift, 0.0)
            self._baseline = baseline
        if not self._linefp.getvalue():
            if self._ypos:
                self._vtab = self._vtab + baseline
            return
        # do we need to break the page?
        # will the line we're about to write fit on the current page?
        linesz = self._baseline + self._descender + self._vtab
##      utils.debug('ypos= {:f}, linesz= {:f}, diff= {:f}, PH= {:f}'.format(
##                  self._ypos, linesz, (self._ypos - linesz),
##                   -self._paper.ImageHeight))
        self._ypos = self._ypos - linesz
        if self._ypos <= -self._paper.ImageHeight:
            self.push_page_break()
        distance = baseline + self._vtab
        if self._align == ALIGN_CENTER:
            offset = (self.get_pagewidth() - self._xpos) / 2
        elif self._align == ALIGN_RIGHT:
            offset = self.get_pagewidth() - self._xpos
        else:
            offset = 0.0
        self._ofp.write('CR {} -{} R\n{}'.format(
                        offset, distance, self._linefp.getvalue()))
        if self._descender > 0:
            self._ofp.write('0 -{} R\n'.format(self._descender))
            self._descender = 0.0
        # reset cache
        self._line_start_font = self._font.get_font()
        self._linefp = StringIO()
        self._lineshift = yshift
        self._xpos = 0.0
        self._vtab = self._leading
        self._baseline = None

    _prev_render = _render
    def close_string(self, linestr=None):
        if linestr is None:
            linestr = self._linestr
        # handle quoted characters
        cooked = cook(''.join(linestr))
        if not cooked:
            return
        # TBD: handle ISO encodings
        #pass
        render = self._render
        # This only works if 'S' and 'U' are the only values for render:
        if self._prev_render != render and cooked[0] == ' ':
            cooked = cooked[1:]
            self._linefp.write('( ) S\n')
        self._linefp.write('({}) {}\n'.format(cooked, render))
        self._prev_render = render
        self._linestr = []
