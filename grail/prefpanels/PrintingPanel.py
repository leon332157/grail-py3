"""General Grail preferences panel."""

__version__ = "$Revision: 1.12 $"

from .. import grailutil
from .. import PrefsPanels
import tkinter


GROUP = "printing"
LABEL_WIDTH = 16


class FontSizeVar(tkinter.StringVar):
    _default = "10.0 / 10.7"
    def get(self):
        sizes = grailutil.conv_fontsize(tkinter.StringVar.get(self))
        return "{} / {}".format(*sizes)

    def set(self, value):
        sizes = grailutil.conv_fontsize(value)
        return tkinter.StringVar.set(self, "{} / {}".format(*sizes))


class StringSetVar(tkinter.StringVar):
    def get(self):
        return tkinter.StringVar.get(self).lower()

    def set(self, value):
        value = value.capitalize()
        return tkinter.StringVar.set(self, value)


class PrintingPanel(PrefsPanels.Framework):
    """Printing preferences."""

    # Class var for help button - relative to grail-help-root.
    HELP_URL = "help/prefs/printing.html"

    def CreateLayout(self, name, frame):

        # Printer configs are simple enough to use the convenience functions
        self.PrefsEntry(frame, 'Print command: ',
                        GROUP, 'command',
                        entry_width=20, label_width=LABEL_WIDTH)
        self.PrefsCheckButton(frame, "Images: ", "Print images ",
                              GROUP, 'images',
                              label_width=LABEL_WIDTH)
        self.PrefsCheckButton(frame, " ", "Reduce images to greyscale",
                              GROUP, 'greyscale',
                              label_width=LABEL_WIDTH)
        self.PrefsCheckButton(frame, "Anchors: ", "Footnotes for anchors",
                              GROUP, 'footnote-anchors',
                              label_width=LABEL_WIDTH)
        self.PrefsCheckButton(frame, " ", "Underline anchors",
                              GROUP, 'underline-anchors',
                              label_width=LABEL_WIDTH)
        # paper size:
        var = StringSetVar()
        from ..printing import paper
        sizes = sorted(paper.paper_sizes.keys())
        sizes = list(map(str.capitalize, sizes))
        self.PrefsOptionMenu(frame, "Paper size: ", GROUP, 'paper-size',
                             sizes, label_width=LABEL_WIDTH,
                             variable=StringSetVar())
        # page orientation:
        var = StringSetVar()
        opts = sorted(paper.paper_rotations.keys())
        opts = list(map(str.capitalize, opts))
        self.PrefsOptionMenu(frame, "Orientation: ", GROUP, 'orientation',
                             opts, label_width=LABEL_WIDTH,
                             variable=StringSetVar())
        # font size and leading:
        self.PrefsEntry(frame, "Font size: ",
                        GROUP, 'font-size',
                        typename='string', entry_width=12,
                        label_width=LABEL_WIDTH, variable=FontSizeVar())

        # paragraph treatment:
        f = tkinter.Frame(frame)
        self.PrefsWidgetLabel(f, "Paragraphs:", label_width=LABEL_WIDTH)
        # Pack some preferences entries together in a frame - we use the
        # PrefsEntry 'composite' feature here, to put them together on the
        # right-hand side of the label:
        tempfr = tkinter.Frame(f, borderwidth=1)
        tempfr.pack(side=tkinter.LEFT)
        entries_frame = tkinter.Frame(
            tempfr, relief=tkinter.SUNKEN, borderwidth=1)
        self.PrefsEntry(entries_frame,
                        "Indentation:",
                        GROUP, 'paragraph-indent', 'float',
                        label_width=10, entry_width=5, composite=True)
        self.PrefsEntry(entries_frame,
                        "Vertical separation:",
                        GROUP, 'paragraph-skip', 'float',
                        label_width=16, entry_width=5, composite=True)
        f.pack(fill=tkinter.X, side=tkinter.TOP, pady='1m')
