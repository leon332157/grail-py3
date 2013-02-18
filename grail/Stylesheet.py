"""Default style sheet for Grail's Viewer widget.

Instantiate Stylesheet with the name of the sheet.  It gets the
command and sheet-specific values as, effectively, class attributes with
dictionary values suitable for feeding to the text widget for tag
configuration."""

class UndefinedStyle(Exception):
    pass

## NOTE: Link colors are taken from Netscape 1.1's X app defaults


class Stylesheet:

    def __init__(self, prefs):
        self.prefs = prefs
        self.load()

        # Arrange for reload on relevant styles groups changes:
        prefs.AddGroupCallback('styles-common', self.load)
        prefs.AddGroupCallback('styles-fonts', self.load)
        prefs.AddGroupCallback('styles', self.load)

    def load(self):
        self.attrs = {}
        self.sizename = self.prefs.Get('styles', 'size')
        self.family = self.prefs.Get('styles', 'family')
        self.size, fparms_dict = self.get_sizes()
        fparms_dict['family'] = self.get_family()
        fparms_dict['italic'] = self.get_italic()
        fparms_dict['bold'] = self.get_bold()

        self.dictify_group(self.prefs.GetGroup('styles-common'))
        self.dictify_list(['styles', 'center', 'justify', 'center'])
        self.dictify_list(['styles', 'pre', 'wrap', 'none'])

        # Map the selected font and size onto the fonts group:
        fonts = self.prefs.GetGroup('styles-fonts')
        massaged = []
        for ((g, c), v) in fonts:
            massaged.append(((g, c), v % fparms_dict))
        self.dictify_group(massaged)

    def __getattr__(self, attr):
        """Make the self.attrs dict keys look like class attributes."""
        try:
            return self.attrs[attr]
        except KeyError:
            raise AttributeError, attr

    def get_sizes(self):
        """Get the size name and a dictionary of size name/values.

        Detects unregistered sizes and uses registered default-size."""
        allsizes = self.prefs.Get('styles', 'all-sizes').split()
        sname = self.sizename
        if sname not in allsizes:
            sname = self.prefs.Get('styles', 'default-size')
            if sname not in allsizes:
                raise UndefinedStyle, ("Bad preferences file,"
                                       + " can't get valid size.")
        sdict = {}
        slist = self.prefs.Get('styles', sname + '-sizes').split()
        for k in self.prefs.Get('styles', 'size-names').split():
            sdict[k] = int(slist.pop(0))
        return sname, sdict

    def get_bold(self):
        """Get the designator for bold fonts in the family."""
        return self.prefs.Get('styles', self.family + '-bold')

    def get_italic(self):
        """Get the character for oblique fonts in the family."""
        return self.prefs.Get('styles', self.family + '-italic')

    def get_family(self):
        """Get the family name and a dictionary of size name/values.

        Detects unregistered families and uses registered default-family."""
        allfams = self.prefs.Get('styles', 'all-families').split()
        tname = self.family
        if tname not in allfams:
            tname = self.prefs.Get('styles', 'default-family')
            if tname not in allfams:
                raise UndefinedStyle, ("Bad preferences file,"
                                       + " can't get valid family.")
        return tname

    def dictify_list(self, fields):
        """Incorporate a list of fields as a style."""
        d = self.attrs
        while fields:
            f = fields[0]
            del fields[0]
            if len(fields) == 1:
                # terminal:
                d[f] = fields[0]
                break
            else:
                d = d.setdefault(f, {})

    def dictify_group(self, glist, attr=None):
        """Incorporate entries in preferences GetGroup list to self.attrs."""
        attrs = self.attrs
        for (group, composite), val in glist:
            fields = composite.split('-')
            d = attrs
            while fields:
                f = fields[0]
                del fields[0]
                if not fields:
                    # f is a terminal key:
                    d[f] = val
                else:
                    d = d.setdefault(f, {})


def test():
    from .grailbase import GrailPrefs
    prefs = GrailPrefs.AllPreferences()
    sheet = Stylesheet(prefs)
    print(sheet.styles['h5_b']['font'])
    print(sheet.styles['pre']['wrap'])
    print(sheet.styles['center']['justify'])

if __name__ == "__main__":
    test()
