#!/usr/bin/env python
"""

Copyright 2000 Pearu Peterson all rights reserved,
Pearu Peterson <pearu@ioc.ee>          
Permission to use, modify, and distribute this software is given under the
terms of the LGPL.  See http://www.fsf.org

NO WARRANTY IS EXPRESSED OR IMPLIED.  USE AT YOUR OWN RISK.
$Date: 2001/12/25 19:16:40 $
Pearu Peterson
"""

from __version__ import __version__

from wxPython.wx import *
from wxPython.html import *
import wxPython.lib.wxpTag

class AboutBox(wxDialog):
    about = '''
<html>
<body bgcolor="#AC76DE">
<center>
<table bgcolor="#458154" width="100%%" cellspacing="0" cellpadding="0" border="1">
<tr>
<td align="center"><h1>COZER '''+__version__+'''</h1></td>
</tr>
</table>
</center>

<p><b>COZER</b> - <i>The COmpetition organiZER</i> - is a <a
href="http://www.python.org/">Python</a> program that provides an
environment for organizing competitive events
according to the latest U.I.M. Circuit Rules.
COZER supports registration of participants, setting up racing programs,
time keeping, and printing various reports and letters.

<p>The author of this program is
<p><b>Pearu Peterson</b> <a href="mailto:pearu.peterson@gmail.com">&lt;pearu.peterson@gmail.com&gt;</a>) Copyright (c) 2000,2001,2006.

<center>
<p><wxp class="wxButton">
    <param name="label" value="Okay">
    <param name="id"    value="wxID_OK">
</wxp></p>
</center>
</body>
</html>
'''
    def __init__(self,parent):
        wxDialog.__init__(self, parent, -1, 'About the Cozer program',
                          size=wxSize(440, 440))
        self.html = wxHtmlWindow(self, -1, size=wxSize(440, 440))
        self.html.SetPage(self.about)
        self.CentreOnParent(wxBOTH)
