This version of Grail has been modified to work with Python 3.  The major
changes include:

* Applets don’t work because the _rexec_ and _Bastion_ modules have been
removed.
* Requires features of Python 3.3.  The source code has been updated to use
new data types and standard library features, and support for prior Python
versions has been dropped.
* The pickle bookmarks format is not compatible with the older version.  Any
old bookmarks cache file (~/.grail/grail-bookmarks.pkl) should be removed.
This should normally be fine because the bookmarks are also saved in a
Netscape file by default.
* The modules have been incorporated into a package named _grail_.  The
package and modules within it can be invoked using the “python3 -m” option.

Notes:

* HTTPS does not work.

*******************************************************************************


GRAIL 0.6
=========

Grail™ is a web browser written in Python, an object-oriented
scripting language.  Grail is distributed in source form.  It requires
that you have a Python interpreter and a Tcl/Tk installation, with the
Python interpreter configured for Tcl/Tk support.

In this file:

- Licensing issues
- Future development
- Hardware requirements
- Installation
- Using Grail
- Web resources
- Feedback
- Epilogue


Licensing issues
----------------

The license of Grail allows essentially unrestricted use and
redistribution.  The full text of the license can be found in the file
LICENSE in the _grail_ directory.  The sources are Copyright © CNRI
1996–1999.  Grail is a registered trademark of CNRI.


Future development
------------------

Given the low usage of Grail, CNRI cannot allocate further resources
to this project.  The license allows for derivative projects, so
anyone who has a need for a Python-based or easily modified Internet
browser is free to use the Grail source code as a basis for a new
project.

The Grail development team would be happy to provide anyone seriously
interested in using Grail as the basis for a new project with a copy
of the CVS repository.  We are also able to provide pointers from the 
Grail Web site to any new projects that spring up based on Grail.


Hardware requirements
---------------------

Grail runs on most Unix systems, on Windows NT and 95, and on
Macintosh systems, provided you have enough memory and a fast enough
machine.  (For Windows, 32 Meg RAM and 90 MHz Pentium is a reasonable
minimal configuration.  For Macintosh, a 40 MHz 68k or any PPC, with
24 Meg RAM, is acceptable.)


Installation
------------

There are three steps to take before you can use Grail:

- Install Tcl and Tk.  The versions must be compatible with each other
and with the Python version you are installing in the next step;
currently, the oldest Tcl/Tk version supported is 8.0.  You can get
Tcl/Tk it at <http://www.scriptics.com/>; or try [ftp to ftp.sunlabs.com
in directory /pub/tcl/](ftp://ftp.sunlabs.com/pub/tcl/).

- Install Python 3.3 (or newer if available), configured for use with
Tk.  The URL to get Python is <http://www.python.org/>; or try [ftp to
ftp.python.org in directory
/pub/python/src/](ftp://ftp.python.org/pub/python/src/).  You must enable Tk
support.

- Install the Grail sources in a convenient place, preferably in Python’s
module search path.  If you are using the /usr/local hierarchy, the _grail_
package could be installed in /usr/local/lib/site-python/.

You can also choose to have a shell script named _grail_ which execs the
Python interpreter, e.g.:

    exec python3 -m grail "$@"

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

Refer to the Grail Web site to determine if any derived projects have
been started.


Epilogue
--------

“Everything should be made as simple as possible, but no simpler.”

  —Albert Einstein

“Nothing is as simple as we hope it will be.”

  —Jim Horning

“Simple is as simple does.”

  —Forrest Gump
