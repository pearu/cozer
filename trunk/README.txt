
                         COZER - COmpetition organiZER
                                    2.7

Copyright 2000,2001,2006,2009 Pearu Peterson all rights reserved,
Pearu Peterson <pearu.peterson@gmail.com>          

DISCLAIMER
==========
       NO WARRANTY IS EXPRESSED OR IMPLIED.  USE AT YOUR OWN RISK.

INTRODUCTION
============

COZER is a program for organizing competitive events. In particular,
for events of the Aquatic Motorsports according to the latest
U.I.M. Circuit Rules (2000,2001).

COZER has been succesfully used in the following events:

*** U.I.M. World Championship O-500, O-125,
    July 14-16, 2000, Lake Harku, Tallinn, Estonia

*** U.I.M. European Championship O-125
    30 June - 1 July, 2001, Lake Harku, Tallinn, Estonia

*** U.I.M. World Championships JT-250, S-550, O-125
    July 10-12, 2009, Lake Harku, Tallinn, Estonia

and in many other international and national events as well.

Comments, feedback, bug reports, suggestions, etc. should be send to
the author Pearu Peterson <pearu.peterson@gmail.com>


REQUIREMENTS
============

     Python 2.1 (other versions may work as well) <http://www.python.org>
     Python 2.3, 2.4, 2.5

     wxPython <http://www.wxpython.org>, use with ANSI string backend.
     Lastly tested to work with wx 2.8.4.
     
     latex, xdvi, dvips, gv          (on Unix)

     latex, yap, dvips, gsview32     (on Windows)

     Notes for Windows users
     -----------------------
       1) I recommend MikTeX <http://www.miktex.com> that includes
          latex, dvips, and yap in its minimal installation setup.

       2) COZER uses
            GSview <http://www.cs.wisc.edu/~ghost/gsview/get40.htm>
          for printing. GSview requires
            Ghostscript <http://www.cs.wisc.edu/~ghost/doc/AFPL/get700.htm>
          The location of the GSview program must be
            c:\Ghostgum\gsview\gsview32.exe

       3) Installing GSview and Ghostscript is optional because COZER
          generated documents can be also printed using Yap. 

INSTALLATION
============

     Unpack COZER-x.x.tar.gz, change to directory COZER-x.x, and run

       python install.py

USAGE
=====

  Run
     cozer

  On Windows, make sure that /path/to/python/scripts is added in PATH

  Or, one can always run

     python cozer.py

  on any platform in the COZER-x.x directory.

Pearu Peterson
21-25 December, 2001

CHANGES
=======
v2.7 - fixes for wx 2.8.4 support (23 June 2009)
v2.6 - added unicode support, may break Python 2.1 support (19 July 2006)
