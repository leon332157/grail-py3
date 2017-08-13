GRAIL 0.6
=========

Grail™ is a web browser written in Python, an object-oriented
scripting language.  Grail is distributed in source form.  It requires
that you have a Python interpreter and a Tcl/Tk installation, with the
Python interpreter configured for Tcl/Tk support.


Licensing issues
----------------

The license of Grail allows essentially unrestricted use and
redistribution. The full text of the license can be found in the file
LICENSE in the _grail_ directory. The sources are Copyright © CNRI
1996–1999. Grail is a registered trademark of CNRI.


Future development
------------------

Given the low usage of Grail, CNRI cannot allocate further resources
to this project. The license allows for derivative projects, so
anyone who has a need for a Python-based or easily modified Internet
browser is free to use the Grail source code as a basis for a new
project.


Installation
------------

There are three steps to take before you can use Grail:

- Install Tcl and Tk.
- Install Python 3.3 (or newer if available).
- Install the Grail preferably in Python’s module search path.

You can also choose to have a shell script named _grail_ which execs the
Python interpreter, e.g.:

    exec python -m grail "$@"

### Optional dependencies ###

Grail normally uses the Python Imaging Library (PIL) to display some image
formats. This version is tested with the “Pillow” fork. Grail also uses the
_djpeg_ command for JPEG images.

If Grail is unable to use PIL, it uses the following commands instead,
if available.

- djpeg
- xbmtopbm
- pngtopnm
- tifftopnm
- ppmtogif

The following commands are required for Telnet URLs.

- xterm
- telnet


Using Grail
-----------

Grail can be invoked by running the _grail_ module as a script:

    python3 -m grail

### Command line options ###

The “-g _geometry_” option lets you specify an initial geometry for
the first browser window in the standard X11 geometry form:
`[<width>x<height>][+<x>+<y>]`, where all dimensions are measured in
pixels.  It is also possible to set the width and height (in character
units) through the _General_ preference panel.

The “-i” option inhibits loading of images for this session.
This option can also be set via the _General_ preference panel.

The “-d _display_” option lets you override the $DISPLAY environment
variable.

Advanced users with a grailrc.py file can use “-q” to inhibit
processing of grailrc.py.  This may be useful during debugging.

### Command line arguments ###

The only positional command line argument is an optional URL of a page
to display initially.  This does not become your “home page”; use the
_General_ preference panel to change the page loaded by the _Home_ command
in the _Go_ menu, and to choose whether this page should be loaded
initially if no URL is given on the command line.


Web resources
-------------

More information on using Grail can be found through the Grail home
page, at this URL:

  <http://grail.cnri.reston.va.us/grail/>

This page is also accessible through the _Grail Home Page_ item of the
_Help_ menu.


Feedback
--------

Grail 0.6 is the last version of Grail to be released by CNRI.  If a
new project based on Grail appears, we will be glad to point to it
from the Grail Web site, but we are not prepared to respond to bug
reports.
