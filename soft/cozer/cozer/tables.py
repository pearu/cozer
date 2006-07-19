#!/usr/bin/env python
"""

Copyright 2000 Pearu Peterson all rights reserved,
Pearu Peterson <pearu@ioc.ee>          
Permission to use, modify, and distribute this software is given under the
terms of the LGPL.  See http://www.fsf.org

NO WARRANTY IS EXPRESSED OR IMPLIED.  USE AT YOUR OWN RISK.
$Date: 2001/12/24 20:27:13 $
Pearu Peterson
"""

__version__ = "$Revision: 1.2 $"[10:-1]

from prefs import *
from datatable import *
import string


class ClassDataTable(DataTable,MyDebug):

    def __init__(self,topparent,parent,debug):
        MyDebug.__init__(self,debug)
        DataTable.__init__(self,debug)
        self.colLabels = ['Class',#'Heats',
                          'Race pattern: NofHeats*(NofLaps*LapLenght+...)+..:Scored']
        self.dataTypes = [wxGRID_VALUE_STRING,
                          wxGRID_VALUE_STRING,
                          ]
        self.topparent = topparent
        self.parent = parent
        if not self.topparent.eventdata.has_key('classes'):
            self.topparent.eventdata['classes']=[]
        self.data = self.topparent.eventdata['classes']
        self.popup = [0,1]#,range(1,10)]

    def ValidateTable(self):
        self.Debug('ValidateTable')
        classes = []
        i=0
        def warnsappend(warns,w):
            if w not in warns: warns.append(w)
        flag=0
        for row in self.data:  #['Class','Heats','Course pattern: n1*l1+...']
            i = i + 1
            ws = []
            for j in range(self.GetNumberCols()):
                if not row[j+1]:
                    self.Warning('%s row: %s field is empty.'%(nth(i),`self.colLabels[j]`))
                    warnsappend(ws,j)
            if row[1]:
                if row[1] not in classes:
                    classes.append(row[1])
                else:
                    self.Warning('%s row: Class %s is already defined in %s row.'%(nth(i),`row[1]`,nth(classes.index(row[1])+1)))
                    warnsappend(ws,0)
            if row[2]:
                try: eval(string.split(row[2],':')[0])+5
                except:
                    self.Warning('%s row: Expected number but got %s.'%(nth(i),`row[2]`))
                    warnsappend(ws,1)
            flag=flag or ws
            for j in range(self.GetNumberCols()):
                if j in ws:
                    self.parent.SetCellBackgroundColour(i-1,j,warning_bg)
                else:
                    self.parent.SetCellBackgroundColour(i-1,j,edit_bg)
        self.parent.SetEnableEdit(flag)
        self.parent.NotifyGrid(0)


class ParticipantDataTable(DataTable,MyDebug):

    classes = []

    def __init__(self,topparent,parent,debug):
        MyDebug.__init__(self,debug)
        DataTable.__init__(self,debug)
        self.topparent = topparent
        self.parent = parent
        if not self.topparent.eventdata.has_key('participants'):
            self.topparent.eventdata['participants']=[]
        self.data = self.topparent.eventdata['participants']
        self.colLabels = ['Name','Surname','From','Class','Id']
        self.dataTypes = [wxGRID_VALUE_STRING,
                          wxGRID_VALUE_STRING,
                          wxGRID_VALUE_STRING,
                          wxGRID_VALUE_CHOICE,
                          wxGRID_VALUE_STRING,
                          ]
        self.popup = [0,0,1,self.classes,0]
        return

    def ResetDataTypes(self):
        self.Debug('ResetDataTypes')
        for i in range(len(self.classes)):
            del self.classes[-1]
        classes = self.topparent.GetClasses()
        for i in range(len(classes)):
            self.classes.append(classes[i])
        self.dataTypes[3] = wxGRID_VALUE_CHOICE+':'+string.join(self.classes,',')

    def ValidateTable(self):
        self.Debug('ValidateTable')
        cl_ids = []
        i=0
        def warnsappend(warns,w):
            if w not in warns: warns.append(w)
        flag=0
        for row in self.data:  #['Name','Surname','From','Class','Id']
            i = i + 1
            if not row: continue
            ws = []
            for j in range(self.GetNumberCols()):
                if not row[j+1]:
                    self.Warning('%s row: %s field is empty.'%(nth(i),`self.colLabels[j]`))
                    warnsappend(ws,j)
            if row[4] not in self.classes:
                self.Warning('%s row: No such class %s.'%(nth(i),`row[4]`))
                warnsappend(ws,3)
            if row[4] and row[5]:
                ci = (row[4],row[5])
                if ci not in cl_ids:
                    cl_ids.append(ci)
                else:
                    self.Warning('%s row: Id %s(%s) is already used in %s row.'%(nth(i),`ci[1]`,ci[0],nth(cl_ids.index(ci)+1)))
                    warnsappend(ws,4)
            flag=flag or ws
            
            for j in range(self.GetNumberCols()):
                if j in ws:
                    self.parent.SetCellBackgroundColour(i-1,j,warning_bg)
                else:
                    self.parent.SetCellBackgroundColour(i-1,j,edit_bg)
        self.parent.SetEnableEdit(flag)
        self.parent.NotifyGrid(0)

_raceslistmenu = [
    ('NewRace',{'menu':'New Race'}),
#    ('NewQual',{'menu':'New Qualification'}),
#    ('NewTraining',{'menu':'New Training'}),
    (),
    ('DeleteRace',{'menu':'Delete Race'}),
#    ('DeleteQual',{'menu':'Delete Qualification'}),
#    ('DeleteTraining',{'menu':'Delete Training'}),
    ]


class RacesListMenu(wxMenu,MyDebug):

    def __init__(self,parent,debug):
        MyDebug.__init__(self,debug)
        wxMenu.__init__(self,"")
        self.data = parent.data
        self.parent = parent
        buildmenus(self,_raceslistmenu,self,verbose = debug)

    def OnNewRace(self,evt):
        self.Debug('OnNewRace')
        self.data.append([['','','']])
        self.parent.currentItem = len(self.data)-1
        self.parent.SetRace()
        self.parent.FillList()

    def OnDeleteRace(self,evt):
        self.Debug('DeleteRace')
        if 0<=self.parent.currentItem<len(self.data):
            mess = wxMessageDialog(self.parent,
                                   "Are you sure you want to delete Race %s?"%(self.parent.currentItem+1),
                                   "Delete Race?",
                                   style=wxYES_NO|wxCENTRE|wxICON_QUESTION|wxNO_DEFAULT)
            if mess.ShowModal() == wxID_YES:
                del self.data[self.parent.currentItem]
                self.parent.currentItem = min(self.parent.currentItem,len(self.data)-1)
                self.parent.SetRace()
                self.parent.FillList()


class RacesList(wxPanel,MyDebug):
    currentItem = -1

    def __init__(self,parent,topparent,debug):
        MyDebug.__init__(self,debug)
        wxPanel.__init__(self,parent,-1)
        self.parent = parent
        self.topparent = topparent
        if not self.topparent.eventdata.has_key('races'):
            self.topparent.eventdata['races']=[]
        self.data = self.topparent.eventdata['races']
        
        ID = wxNewId()
        lst = wxListCtrl(self, ID,style=wxLC_REPORT|wxSUNKEN_BORDER)
        lst.InsertColumn(0,'Race List')

        self.lst = lst
        vsizer = wxBoxSizer(wxVERTICAL)
        vsizer.Add(lst,1,wxEXPAND)
        self.SetAutoLayout(true)
        self.SetSizer(vsizer)

        EVT_RIGHT_DOWN(self.lst, self.OnRightDown)
        EVT_LIST_ITEM_SELECTED(self, self.lst.GetId(), self.OnItemSelected)
        EVT_LIST_ITEM_ACTIVATED(self, self.lst.GetId(), self.OnItemActivated)
        self.FillList()

    def OnItemActivated(self,evt):
        self.Debug('OnItemActivated')
        self.currentItem = evt.m_itemIndex
        #self.SetRace()
        self.FillList()

    def OnItemSelected(self,evt):
        self.Debug('OnItemSelected, %d'%(evt.m_itemIndex))
        self.currentItem = evt.m_itemIndex
        self.SetRace()
        self.edit.RaceSelected()

    def OnRightDown(self,evt):
        self.Debug('OnRightDown')
        menu = RacesListMenu(self,self.debug+(not not self.debug))
        self.PopupMenu(menu,evt.GetPosition())
        menu.Destroy()

    def SetRace(self):
        self.topparent.currentRace = self.currentItem
        if 0<=self.currentItem<len(self.data):
            self.lst.SetItemState(self.currentItem,wxLIST_STATE_SELECTED|wxLIST_STATE_FOCUSED,
                                  wxLIST_STATE_SELECTED|wxLIST_STATE_FOCUSED)
        
    def FillList(self):
        self.Debug('FillList')
        self.lst.DeleteAllItems()
        i=-1
        for d in self.data:
            i = i + 1
            self.lst.InsertStringItem(i,'Race %d'%(i+1))
        self.lst.SetColumnWidth(0, wxLIST_AUTOSIZE)        
        if 0<=self.currentItem<len(self.data):
            self.lst.SetItemState(self.currentItem,wxLIST_STATE_SELECTED|wxLIST_STATE_FOCUSED,
                                  wxLIST_STATE_SELECTED|wxLIST_STATE_FOCUSED)


class RaceDataTable(DataTable,MyDebug):

    def __init__(self,topparent,parent,debug):
        MyDebug.__init__(self,debug)
        DataTable.__init__(self,debug)
        self.colLabels = ['Class','Heat']
        self.dataTypes = [wxGRID_VALUE_STRING,
                          wxGRID_VALUE_STRING,
                          ]
        self.topparent = topparent
        self.parent = parent
        self.data = topparent.eventdata['races'][topparent.currentRace]
        self.popup = [topparent.GetClasses(),topparent.GetHeats(topparent.currentRace)]

    def ValidateTable(self):
        self.Debug('ValidateTable')
        classes = []
        validclasses=self.topparent.GetClasses()
        i=0
        def warnsappend(warns,w):
            if w not in warns: warns.append(w)
        flag=0
        for row in self.data:  #['Class','Heat']
            i = i + 1
            ws = []
            for j in range(self.GetNumberCols()):
                if not row[j+1]:
                    self.Warning('%s row: %s field is empty.'%(nth(i),`self.colLabels[j]`))
                    warnsappend(ws,j)
            if row[1]:
                if row[1] not in validclasses:
                    self.Warning('%s row: Class %s is not defined.'%(nth(i),`row[1]`))
                    warnsappend(ws,0)
                if row[1] not in classes:
                    classes.append(row[1])
                else:
                    self.Warning('%s row: Class %s is already defined in %s row.'%(nth(i),`row[1]`,nth(classes.index(row[1])+1)))
                    warnsappend(ws,0)
            if row[2]:
                ah=self.topparent.GetAllowedHeats(row[1])
                if row[2] not in ah:
                    self.Warning('%s row: Heat %s is not valid.'%(nth(i),`row[2]`))
                    warnsappend(ws,1)
            flag=flag or ws
            for j in range(self.GetNumberCols()):
                if j in ws:
                    self.parent.SetCellBackgroundColour(i-1,j,warning_bg)
                else:
                    self.parent.SetCellBackgroundColour(i-1,j,edit_bg)
        self.parent.SetEnableEdit(flag)
        self.parent.NotifyGrid(0)


class RaceEdit(wxPanel,MyDebug):
    grid = None

    def __init__(self,parent,topparent,debug):
        MyDebug.__init__(self,debug)
        wxPanel.__init__(self,parent,-1)
        self.parent = parent
        self.topparent = topparent
        if not self.topparent.eventdata.has_key('races'):
            self.topparent.eventdata['races']=[]
        self.data = self.topparent.eventdata['races']
        self.sizer = wxBoxSizer(wxVERTICAL)
        self.SetAutoLayout(true)
        self.SetSizer(self.sizer)

    def RaceSelected(self):
        self.Debug('RaceSelected')
        if self.grid:
            self.sizer.Remove(self.grid)
            self.grid.Destroy()
        self.grid =  DataGrid(self,RaceDataTable,self.debug+(not not self.debug))
        self.sizer.Add(self.grid,1,wxEXPAND)
        self.sizer.Layout()
        self.grid.table.ValidateTable()


class RulesDataTable(DataTable,MyDebug):

    def __init__(self,topparent,parent,debug):
        MyDebug.__init__(self,debug)
        DataTable.__init__(self,debug)
        self.topparent = topparent
        self.parent = parent
        if not self.topparent.eventdata.has_key('rules'):
            self.topparent.eventdata['rules']=[]
        self.data = self.topparent.eventdata['rules']
        self.colLabels = ['Action','Paragraph','Short Description']
        self.dataTypes = [wxGRID_VALUE_CHOICE+':'+string.join(reccodemap.keys(),','),
                          wxGRID_VALUE_STRING,
                          wxGRID_VALUE_STRING,
                          ]
        self.popup = [reccodemap.keys(),0,0]

    def ValidateTable(self):
        self.Debug('ValidateTable')
        code_pars = []
        i=0
        def warnsappend(warns,w):
            if w not in warns: warns.append(w)
        flag=0
        for row in self.data:
            i = i + 1
            ws = []
            for j in range(self.GetNumberCols()):
                if not row[j+1]:
                    self.Warning('%s row: %s field is empty.'%(nth(i),`self.colLabels[j]`))
                    warnsappend(ws,j)
            if row[1] and row[2]:
                ci = (row[1],row[2])
                if ci not in code_pars:
                    code_pars.append(ci)
                else:
                    self.Warning('%s row: Rule code="%s" par="%s" is already defined in %s row.'%(nth(i),ci[0],ci[1],nth(code_pars.index(ci)+1)))
                    warnsappend(ws,1)
            flag=flag or ws
            for j in range(self.GetNumberCols()):
                if j in ws:
                    self.parent.SetCellBackgroundColour(i-1,j,warning_bg)
                else:
                    self.parent.SetCellBackgroundColour(i-1,j,edit_bg)
        self.parent.SetEnableEdit(flag)
        self.parent.NotifyGrid(0)
