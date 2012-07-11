#!/usr/bin/env python
"""

Copyright 2000 Pearu Peterson all rights reserved,
Pearu Peterson <pearu@ioc.ee>          
Permission to use, modify, and distribute this software is given under the
terms of the LGPL.  See http://www.fsf.org

NO WARRANTY IS EXPRESSED OR IMPLIED.  USE AT YOUR OWN RISK.
$Date: 2001/12/22 14:00:13 $
Pearu Peterson
"""

__version__ = "$Revision: 1.1.1.1 $"[10:-1]

mainmenubar = [
    ('File',{'menu':'&File',
             'submenu':[('New',{'menu':'&New',
                               'help':'Create new Cozer event',
                               'shelp':'New event'                               
                               }),
                        ('Open',{'menu':'&Open',
                                 'help':'Open Cozer event from disk',
                                 'shelp':'Open event'
                                 }),
                        ('Append',{'menu':'Append &From',
                                 'help':'Append Cozer event data from disk',
                                 'shelp':'Append event'
                                 }),
                        ('Save',{'menu':'&Save',
                                 'help':'Save Cozer event to disk',
                                 'shelp':'Save event'
                                 }),
                        ('SaveAs',{'menu':'Save &As',
                                   'help':'Save Cozer event to disk as',
                                   'shelp':'Save event as'
                                 }),
                        (),
                        ('Language',{'menu':'&Language',
                                     'help':'Select report language',
                                     'shelp':'Select language',
                                     'submenu':[('English',{'menu':'en&glish',
                                                            'check':None}),
                                                ('Estonian',{'menu':'&estonian',
                                                             'check':None}),
                                                ]
                                     }),
                        (),
                        ('Export',{'menu':'&Export',
                                   'help':'Export Cozer event to',
                                   'shelp':'Export event to',
                                   'submenu':[
                                       ('Stdout',{'menu':'to &Stdout'}),
                                       ('Python',{'menu':'to &Python'}),
                                       ]
                                 }),
                        ('Import',{'menu':'&Import',
                                   'help':'Import Cozer event from',
                                   'shelp':'Import event from',
                                   'submenu':[
                                       ('Python',{'menu':'from &Python'}),
                                       ('AppendPython',{'menu':'&Append from Python'}),
                                       ]
                                 }),
                        (),
                        ('Exit',{'menu':'E&xit',
                                 'help':'Save and Exit Cozer',
                                 'shelp':'Save and Exit'
                                 }),
                        ('Quit',{'menu':'&Quit',
                                 'help':'Quit Cozer without Save',
                                 'shelp':'Quit'
                                 })
                        ]
             }),
    ('View',{'menu':'&View',
             'submenu':[('Refresh',{'menu':'&Refresh',
                                  'help':'Refresh pages',
                                  'shelp':'Refresh'
                                  }),
                        ]}),
    ('Help',{'menu':'&Help',
             'submenu':[
    ('About',{'menu':'A&bout',
              'help':'About Cozer',
              'shelp':'About'
              }),
    ('Reload',{'menu':'R&eload',
              'help':'Reload Cozer modules',
              'shelp':'Reload'
              }),
                        ]})
    ]
