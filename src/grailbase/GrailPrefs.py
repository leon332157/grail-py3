"""Functional interface to Grail user preferences.

See the Grail htdocs/info/extending/preferences.html for documentation."""

# To test, "(cd <scriptdir>; python GrailPrefs.py)".

__version__ = "$Revision: 2.33 $"

import os
import sys
from . import utils

from . import parseprefs
from collections import defaultdict

USERPREFSFILENAME = 'grail-preferences'
SYSPREFSFILENAME = os.path.join('data', 'grail-defaults')

class Preferences:
    """Get and set fields in a customization-values file."""

    # We maintain a dictionary of the established self.saved preferences,
    # self.mods changes, which are incorporated into the established on
    # self.Save(), and self.deleted, which indicates settings to be omitted
    # during save (for reversion to "factory default", ie system, settings).

    def __init__(self, filename):
        """Initiate from FILENAME."""
        self.filename = filename
        self.mods = defaultdict(dict)  # Changed settings not yet saved.
        # Settings overridden, not yet saved.
        self.deleted = defaultdict(set)
        try:
            f = open(filename)
            self.saved = parseprefs.parseprefs(f)
            f.close()
        except IOError:
            self.saved = defaultdict(dict)

    def Get(self, group, cmpnt):
        """Get preference or raise KeyError if not found."""
        if group in self.mods and cmpnt in self.mods[group]:
            return self.mods[group][cmpnt]
        elif group in self.saved and cmpnt in self.saved[group]:
            return self.saved[group][cmpnt]
        else:
            raise KeyError, "Preference %s not found" % ((group, cmpnt),)

    def Set(self, group, cmpnt, val):
        self.mods[group][cmpnt] = str(val)
        # Undelete.
        self.deleted[group].discard(cmpnt)

    def __delitem__(self, (group, cmpnt)):
        """Inhibit preference (GROUP, COMPONENT) from being seen or saved."""
        self.Get(group, cmpnt)  # Verify item existence.
        self.deleted[group].add(cmpnt)

    def items(self):
        """Return a list of ((group, cmpnt), value) tuples."""
        got = {}
        deleted = self.deleted
        # Consolidate established and changed, with changed having precedence:
        for g, comps in self.saved.items() + self.mods.items():
            for c, v in comps.items():
                if c not in deleted.get(g, ()):
                    got[(g,c)] = v
        return got.items()

    def Editable(self):
        """Ensure that the user has a graildir and it is editable."""
        if not utils.establish_dir(os.path.split(self.filename)[0]):
            return 0
        elif os.path.exists(self.filename):
            return 1
        else:
            try:
                tempf = open(self.filename, 'a')
                tempf.close()
                return 1
            except os.error:
                return 0

    def Save(self):
        """Write the preferences out to file, if possible."""
        try: os.rename(self.filename, self.filename + '.bak')
        except os.error: pass           # No file to backup.

        fp = open(self.filename, 'w')
        items = self.items()
        items.sort()
        prevgroup = None
        for (g, c), v in items:
            if prevgroup and g != prevgroup:
                fp.write('\n')
            fp.write(make_key(g, c) + ': ' + v + '\n')
            prevgroup = g
        fp.close()
        # Register that modifications are now saved:
        deleted = self.deleted
        for g, comps in self.mods.items():
            for c, v in comps.items():
                if c not in deleted.get(g, ()):
                    self.saved[g][c] = v
                elif g in self.saved:
                    # Deleted - remove from saved version:
                    self.saved[g].pop(c, None)
        # ... and reinit mods and deleted records:
        self.mods.clear()
        self.deleted.clear()

class AllPreferences:
    """Maintain the combination of user and system preferences."""
    def __init__(self):
        self.load()
        self.callbacks = {}

    def load(self):
        """Load preferences from scratch, discarding any mods and deletions."""
        self.user = Preferences(os.path.join(utils.getgraildir(),
                                             USERPREFSFILENAME))
        self.sys = Preferences(os.path.join(utils.get_grailroot(),
                                            SYSPREFSFILENAME))

    def AddGroupCallback(self, group, callback):
        """Register callback to be invoked when saving GROUP changed prefs.

        Each callback will be invoked only once per concerned group per
        save (even if multiply registered for that group), and callbacks
        within a group will be invoked in the order they were registered."""
        if group in self.callbacks:
            if callback not in self.callbacks[group]:
                self.callbacks[group].append(callback)
        else:
            self.callbacks[group] = [callback]

    def RemoveGroupCallback(self, group, callback):
        """Remove registered group-prefs callback func.

        Silently ignores unregistered callbacks."""
        try:
            self.callbacks[group].remove(callback)
        except (ValueError, KeyError):
            pass

    # Getting:

    def Get(self, group, cmpnt, factory=0):
        """Get pref GROUP, COMPONENT, trying the user then the sys prefs.

        Optional FACTORY true means get system default ("factory") value.

        Raise KeyError if not found."""
        if factory:
            return self.sys.Get(group, cmpnt)
        else:
            try:
                return self.user.Get(group, cmpnt)
            except KeyError:
                return self.sys.Get(group, cmpnt)

    def GetTyped(self, group, cmpnt, type_name, factory=0):
        """Get preference, using CONVERTER to convert to type NAME.

        Optional SYS true means get system default value.

        Raise KeyError if not found, TypeError if value is wrong type."""
        val = self.Get(group, cmpnt, factory)
        try:
            return typify(val, type_name)
        except TypeError:
            raise TypeError, ('%s should be %s: %r'
                               % (str((group, cmpnt)), type_name, val))

    def GetInt(self, group, cmpnt, factory=0):
        return self.GetTyped(group, cmpnt, "int", factory)
    def GetFloat(self, group, cmpnt, factory=0):
        return self.GetTyped(group, cmpnt, "float", factory)
    def GetBoolean(self, group, cmpnt, factory=0):
        return self.GetTyped(group, cmpnt, "Boolean", factory)

    def GetGroup(self, group):
        """Get a list of ((group,cmpnt), value) tuples in group."""
        got = []
        for it in self.items():
            if it[0][0] == group:
                got.append(it)
        return got

    def items(self):
        got = {}
        for it in self.sys.items():
            got[it[0]] = it[1]
        for it in self.user.items():
            got[it[0]] = it[1]
        return got.items()

    # Editing:

    def Set(self, group, cmpnt, val):
        """Assign GROUP,COMPONENT with VALUE."""
        if self.Get(group, cmpnt) != val:
            self.user.Set(group, cmpnt, val)

    def Editable(self):
        """Identify or establish user's prefs file, or IO error."""
        return self.user.Editable()

    def Save(self):
        """Save (only) values different than sys defaults in the users file."""
        # Callbacks are processed after the save.

        # Identify the pending callbacks before user-prefs culling:
        pending_groups = self.user.mods.keys()

        # Cull the user items to remove any settings that are identical to
        # the ones in the system defaults:
        for (g, c), v in self.user.items():
            try:
                if self.sys.Get(g, c) == v:
                    del self.user[(g, c)]
            except KeyError:
                # User file pref absent from system file - may be for
                # different version, so leave it be:
                continue

        try:
            self.user.Save()
        except IOError:
            print "Failed save of user prefs."

        # Process the callbacks:
        callbacks, did_callbacks = self.callbacks, set()
        for group in pending_groups:
            for callback in callbacks.get(group, ()):
                # Ensure each callback is invoked only once per save,
                # in order:
                if callback not in did_callbacks:
                    did_callbacks.add(callback)
                    apply(callback, ())

def make_key(group, cmpnt):
    """Produce a key from preference GROUP, COMPONENT strings."""
    return (group + '--' + cmpnt).lower()
                    

def typify(val, type_name):
    """Convert string value to specific type, or raise type err if impossible.

    Type is one of 'string', 'int', 'float', or 'Boolean' (note caps)."""
    try:
        if type_name == 'string':
            return val
        elif type_name == 'int':
            return int(val)
        elif type_name == 'float':
            return float(val)
        elif type_name == 'Boolean':
            i = int(val)
            if i not in (0, 1):
                raise TypeError, '%r should be Boolean' % val
            return i
    except ValueError:
            raise TypeError, '%r should be %s' % (val, type_name)
    
    raise ValueError, ('%r not supported - must be one of %s'
                       % (type_name, ['string', 'int', 'float', 'Boolean']))
    

def test():
    """Exercise preferences mechanisms.

    Note that this test alters and then restores a setting in the user's
    prefs  file."""
    sys.path.insert(0, "../utils")
    from testing import exercise
    
    env = sys.modules[__name__].__dict__

    # Reading the db:
    exercise("prefs = AllPreferences()", env, "Suck in the prefs")

    # Getting values:
    exercise("origin = prefs.Get('landmarks', 'grail-help-root')", env,
             "Get an existing plain component.")
    exercise("origheight = prefs.GetInt('browser', 'default-height')", env,
             "Get an existing int component.")
    exercise("if prefs.GetBoolean('browser', 'load-images') != 1:"
             + "raise SystemError, 'browser:load-images Boolean should be 1'",
             env, "Get an existing Boolean component.")
    # A few value errors:
    exercise("x = prefs.Get('grail', 'Never:no:way:no:how!')", env,
             "Ref to a non-existent component.", KeyError)
    exercise("x = prefs.GetInt('landmarks', 'grail-help-root')", env,
             "Typed ref to incorrect type.", TypeError)
    exercise("x = prefs.GetBoolean('browser', 'default-height')", env,
             "Invalid Boolean (which has complicated err handling) typed ref.",
             TypeError)
    # Editing:
    exercise("prefs.Set('browser', 'default-height', origheight + 1)", env,
             "Set a simple value")
    exercise("if prefs.GetInt('browser', 'default-height') != origheight + 1:"
             + "raise SystemError, 'Set of new height failed'", env,
             "Get the new value.")
    prefs.Save()

    exercise("prefs.Set('browser', 'default-height', origheight)", env,
             "Restore simple value")

    # Saving - should just rewrite existing user prefs file, sans comments
    # and any lines duplicating system prefs.
    exercise("prefs.Save()", env, "Save as it was originally.")
    

    print "GrailPrefs tests passed."
    return prefs

if __name__ == "__main__":

    prefs = test()
