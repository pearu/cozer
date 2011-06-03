#!/usr/bin/env python
"""
setup.py for building/installing COZER

Usage:
   python setup.py install

Copyright 2001,2006 Pearu Peterson all rights reserved,
Pearu Peterson <pearu.peterson@gmail.com>          
Permission to use, modify, and distribute this software is given under the
terms of the LGPL.  See http://www.fsf.org

NO WARRANTY IS EXPRESSED OR IMPLIED.  USE AT YOUR OWN RISK.
$Revision: 1.3 $
$Date: 2001/12/25 19:16:40 $
Pearu Peterson
"""

__version__ = "$Id: setup.py,v 1.3 2001/12/25 19:16:40 pearu Exp $"

import sys,os,glob,re
glob = glob.glob

from distutils.core import setup
from distutils.command.install_data import install_data
from distutils.command.install_scripts import install_scripts

class my_install_data (install_data):
    def finalize_options (self):
        self.set_undefined_options ('install',
                                    ('install_lib', 'install_dir'),
                                    ('root', 'root'),
                                    ('force', 'force'),
                                    )

def cozer_bat():
    pythonw = os.path.join(os.path.dirname(sys.executable),'pythonw.exe')
    if not os.path.exists(pythonw):
        pythonw = sys.executable
    pythonw = os.path.abspath(pythonw)
    return '@echo off\n'+pythonw+' -c "import cozer;cozer.runcozer()" %1'

class my_install_scripts (install_scripts):
    def run (self):
        install_scripts.run (self)
        for file in self.get_outputs ():
            dirname,basename = os.path.dirname(file),os.path.basename(file)
            if basename == 'cozer.py':
                if os.name=='nt':
                    new_file = os.path.join(dirname,'cozer.bat')
                else:
                    new_file = os.path.join(dirname,'cozer')
                if os.path.exists(new_file):
                    self.announce("removing %s" % (new_file))
                    if not self.dry_run:
                        os.remove(new_file)
                if os.name=='nt':
                    self.announce("removing %s" % (file))
                    if not self.dry_run:
                        os.remove(file)
                    self.announce("creating %s" % (new_file))
                    if not self.dry_run:
                        f = open(new_file,'w')
                        f.write(cozer_bat())
                        f.close()
                else:
                    self.announce("renaming %s to %s" % (file, new_file))
                    if not self.dry_run:
                        os.rename (file, new_file)

svn_entries = os.path.join('.svn','entries')
if os.path.isfile(svn_entries):
    f = open(svn_entries)
    m = re.search(r'revision="(?P<revision>\d+)"',f.read())
    f.close()
    if m:
        revision = m.group('revision')
        svn_version = os.path.join('cozer','__svn_version__.py')
        f = open(svn_version,'w')
        f.write('version = %r\n' % (revision))
        f.close()

sys.path.insert(0,'cozer')
execfile(os.path.join('cozer','__version__.py'))
del sys.path[0]

if __name__ == "__main__":
    print 'COZER Version',__version__

    setup(name="COZER",
          version=__version__,
          description       = "COZER - COmpetation organiZER",
          author            = "Pearu Peterson",
          author_email      = "pearu.peterson@gmail.com",
          license           = "GPL",
          long_description  = """\
          COZER is a program for organizing competitive events. In
          particular, for events of the Aquatic Motorsports according
          to the latest U.I.M. Circuit Rules.
          """,
          url               = "http://cens.ioc.ee/~pearu/veemoto/cozer/",
          cmdclass          = {'install_data': my_install_data,
                               'install_scripts': my_install_scripts},
          scripts           = ['cozer.py'],
          packages          = ['cozer'],
          package_dir       = {'cozer':'cozer'},
          data_files        = [(os.path.join('cozer','data'),
                                glob(os.path.join('cozer','data','*.tex'))+\
                                glob(os.path.join('cozer','data','*.sty'))+\
                                glob(os.path.join('cozer','data','*.py'))+\
                                glob(os.path.join('cozer','data','*.coz'))
                                )
                               ]
          )
