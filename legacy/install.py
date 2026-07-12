#!/usr/bin/env python
"""
Run this script to install COZER package.

Copyright 2001 Pearu Peterson all rights reserved,
Pearu Peterson <pearu@cens.ioc.ee>          
Permission to use, modify, and distribute this software is given under the
terms of the LGPL.  See http://www.fsf.org

NO WARRANTY IS EXPRESSED OR IMPLIED.  USE AT YOUR OWN RISK.
$Revision: 1.2 $
$Date: 2001/12/25 19:16:40 $
Pearu Peterson
"""

import sys,os,string

os.system(sys.executable+' ./setup.py install '+string.join(sys.argv[1:],' '))
