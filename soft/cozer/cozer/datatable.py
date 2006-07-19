#!/usr/bin/env python
"""

Copyright 2000 Pearu Peterson all rights reserved,
Pearu Peterson <pearu@ioc.ee>          
Permission to use, modify, and distribute this software is given under the
terms of the LGPL.  See http://www.fsf.org

NO WARRANTY IS EXPRESSED OR IMPLIED.  USE AT YOUR OWN RISK.
$Date: 2001/12/25 10:19:09 $
Pearu Peterson
"""

__version__ = "$Revision: 1.3 $"[10:-1]

from prefs import *
from buildmenus import *
from wxPython.grid import *
import string

class DataTable(wxPyGridTableBase,MyDebug):
    """
Childrens must define:
    self.colLabels
    self.dataTypes
    self.data
"""
    enableedit = 0

    def __init__(self,debug):
        MyDebug.__init__(self,debug)
        wxPyGridTableBase.__init__(self)

    def GetNumberRows(self):
        self.Debug1('GetNumberRows')
        return len(self.data)

    def GetNumberCols(self):
        self.Debug1('GetNumberCols')
        return len(self.colLabels)

    def IsEmptyCell(self, row, col):
        self.Debug1('IsEmptyCell')
        return not self.data[row][col+1]

    def GetValue(self, row, col):
        self.Debug1('GetValue, row col=',row,col)
        while len(self.data[row]) <= col+1: self.data[row].append('')
        return self.data[row][col+1]

    def SetValue(self, row, col, value):
        self.Debug1('SetValue, row col=',row,col,'value=',value)
        if col>=0 and not self.GetEnableEdit(): return
        while len(self.data[row]) <= col+1: self.data[row].append('')
        typevalue = string.split(self.GetTypeName(row,col),':')[0]
        try:
            if typevalue == 'long':
                val = int(value)
            elif typevalue == 'double':
                val = float(value)
            else:
                val = value
        except TypeError: val = value
        self.data[row][col+1] = val
        self.parent.SetCellBackgroundColour(row,col,edit_bg)

    def GetColLabelValue(self, col):
        self.Debug1('GetColLabelValue, col=',col)
        return self.colLabels[col]

    def GetTypeName(self, row, col):
        self.Debug1('GetTypeName, row col=',row,col)
        if col == -1: return wxGRID_VALUE_STRING
        return self.dataTypes[col]

    def Sort(self,col):
        self.Debug('Sort, col=',col)
        for i in range(self.GetNumberRows()):
            v = self.GetValue(i,col)
            try: v=eval(v)
            except: pass
            self.SetValue(i,-1,v)
        self.data.sort()

    def GetEnableEdit(self):
        self.Debug1('GetEnableEdit, enableedit=',self.enableedit)
        return self.enableedit


class DataGrid(wxGrid,MyDebug):
    """
    Parent must set:
    parent.topparent
    """
    sortcol = -2

    def __init__(self,parent,TableClass,debug):
        MyDebug.__init__(self,debug)
        wxGrid.__init__(self,parent,-1)
        self.table = TableClass(parent.topparent,self,debug+(not not debug))
        self.SetTable(self.table,true)
        self.data = self.table.data

        self.SetEnableEdit(not self.data)
        self.SetDefaultCellBackgroundColour({1:edit_bg,0:disableedit_bg}[self.table.enableedit])
        self.SetRowLabelSize(20)
        self.SetColLabelSize(20)
        self.SetMargins(0,0)
        EVT_GRID_LABEL_RIGHT_CLICK(self,self.OnLabelRightClick)
        EVT_GRID_LABEL_LEFT_CLICK(self,self.OnLabelLeftClick)
        EVT_GRID_CELL_RIGHT_CLICK(self,self.OnCellRightClick)
        EVT_KEY_DOWN(self, self.OnKeyDown)

    def OnKeyDown(self, evt):
        row,col=self.GetGridCursorRow(),self.GetGridCursorCol()
        self.MakeCellVisible(row,col)
        if not self.IsVisible(row,col): #wxGrid bug fix
            self.NewDataRow(0)
            self.MakeCellVisible(row,col)
        if evt.KeyCode() == WXK_DELETE:
            if col==0 and self.table.GetEnableEdit():
                self.Debug('OnKeyDown, delete')
                self.DeleteDataRow(row)
                if row>0:
                    n = min(row,self.table.GetNumberRows()-1)
                    self.SetGridCursor(n, 0)
                    self.MakeCellVisible(n, 0)
            else:
                wxBell()
            return
        if not self.table.GetEnableEdit():
            wxBell()
            return
        if evt.KeyCode() not in [WXK_RETURN,WXK_TAB] or evt.ControlDown():
            evt.Skip()
            return

        if self.GetTable().GetNumberRows() == 0:
            self.Debug('OnKeyDown, first new')
            self.NewDataRow(0)
            self.SetGridCursor(0, 0)
            self.MakeCellVisible(0, 0)
            return
        success = self.MoveCursorRight(evt.ShiftDown())
        if not success:
            newRow = row + 1
            if newRow >= self.GetTable().GetNumberRows():
                self.Debug('OnKeyDown, append new')
                self.NewDataRow(0)
            self.SetGridCursor(newRow, 0)
            self.MakeCellVisible(newRow, 0)

    def OnLabelRightClick(self,evt):
        col = evt.GetCol()
        if col == -1:
            row = evt.GetRow()
            self.Debug('OnLabelRigthClick, row=',row)
            menu = DataMenu(self,row,self.debug+(not not self.debug))
            self.PopupMenu(menu,evt.GetPosition())
            menu.Destroy()

    def OnLabelLeftClick(self,evt):
        if evt.GetRow() == -1:
            col = evt.GetCol()
            self.Debug('OnLabelLeftClick, col=',col)
            if col == self.sortcol:
                self.data.reverse()
            else:
                self.table.Sort(col)
            self.sortcol = col
            self.NotifyGrid(0)

    def OnCellRightClick(self,evt):
        global _tmpmenuflag
        row,col = evt.GetRow(),evt.GetCol()
        if min(row,col) >= 0 and hasattr(self.table,'popup') and self.table.popup[col]:
            self.Debug('OnCellRightClick, row col=',row,col)
            popup=[]
            if type(self.table.popup[col]) == type([]):
                popup = self.table.popup[col]
            elif type(self.table.popup[col]) == type({}):
                for k in range(len(self.table.popup)):
                    if not k==col:
                        val = self.table.GetValue(row,k)
                        if self.table.popup[col].has_key(val):
                            popup = self.table.popup[col][val]
                            break
            if not popup:
                for r in range(self.table.GetNumberRows()):
                    val = self.table.GetValue(r,col)
                    if val and (val not in popup):
                        popup.append(val)
            menutmpl = []
            i = -1
            for val in popup:
                i = i + 1   
                menutmpl.append(('item%d'%i,{'menu':str(val)}))
            menu = TempMenu(self,menutmpl,self.debug+(not not self.debug))
            self.PopupMenu(menu,evt.GetPosition())
            menu.Destroy()
            i = _tmpmenuflag[0]
            if i>= 0:
                self.table.SetValue(row,col,popup[i])
                for k in range(len(self.table.popup)):
                    if (not k == col) and type(self.table.popup[k])==type({}) and \
                       self.table.popup[k].has_key(popup[i]):
                        val=self.table.popup[k][popup[i]]
                        if val:
                            if type(val)==type([]): val=val[0]
                            self.table.SetValue(row,k,val)
                self.NotifyGrid(0)

    def NewDataRow(self,row):
        if not self.table.GetEnableEdit():
            wxBell()
            return
        self.Debug('NewDataRow')
        self.data.append([])
        self.NotifyGrid(1)

    def InsertDataRow(self,row):
        if not self.table.GetEnableEdit(): return
        self.Debug('InsertDataRow, row=',row)
        if row<0: row = 0
        self.data.insert(row,[])
        self.NotifyGrid(1)
        self.SetGridCursor(row, 0)
        self.MakeCellVisible(row,0)        

    def DeleteDataRow(self,row):
        if not self.table.GetEnableEdit(): return
        if not self.table.GetNumberRows():
            return
        self.Debug('DeleteDataRow, row=',row)
        del self.data[row]
        self.NotifyGrid(-1)

    def NotifyGrid(self,flag):
        self.Debug('NotifyGrid')
        msg = wxGridTableMessage(self.table,wxGRIDTABLE_NOTIFY_ROWS_APPENDED,flag)
        self.table.GetView().ProcessTableMessage(msg)

    def SetEnableEdit(self,bool):
        self.Debug('SetEnableEdit:bool=%s'%(repr(bool)))
        self.table.enableedit=not not bool
        self.SetDefaultCellBackgroundColour({1:edit_bg,0:disableedit_bg}[self.table.enableedit])


_datatablelabelm1menu = [
    ('New',{'menu':'New',
            'help':'New row',
            'shelp':'New row',
            }),
    ('Insert',{'menu':'Insert',
            'help':'Insert row',
            'shelp':'Insert row',
            }),
    (),
    ('EnableEdit',{'menu':'Enable Edit',
             'help':'Enable table',
             'shelp':'Enable table',
             }),
    (),
    ('ValidateTable',{'menu':'Validate Table',
               'help':'Validate table',
               'shelp':'Validate table',
               }),
    ]

_datatablelabelmenu = [
    ('New',{'menu':'New',
            'help':'New row',
            'shelp':'New row',
            }),
    ('Insert',{'menu':'Insert',
            'help':'Insert row',
            'shelp':'Insert row',
            }),
    ('Delete',{'menu':'Delete',
               'help':'Delete row',
               'shelp':'Delete row',
               })
    ]


class DataMenu(wxMenu,MyDebug):

    def __init__(self,parent,row,debug):
        MyDebug.__init__(self,debug)
        wxMenu.__init__(self,"Data Menu")
        self.parent = parent
        self.row = row
        if row == -1:
            _datatablelabelm1menu[3][1]['check'] = self.parent.table.enableedit 
            buildmenus(self,_datatablelabelm1menu,self,verbose = debug)
        else:
            buildmenus(self,_datatablelabelmenu,self,verbose = debug)

    def OnNew(self,evt):
        self.Debug('OnNew')
        self.parent.NewDataRow(self.row)

    def OnInsert(self,evt):
        self.Debug('OnInsert')
        self.parent.InsertDataRow(self.row)

    def OnDelete(self,evt):
        self.Debug('OnDelete')
        self.parent.DeleteDataRow(self.row)

    def OnEnableEdit(self,evt):
        self.Debug('OnEnableEdit')
        #id = self.EnableEditObj.GetId()
        #if id>=0:
        #self.parent.SetEnableEdit(self.IsChecked(id))
        if 0 and os.name == 'nt':
            self.parent.SetEnableEdit(not evt.Checked())
        else:
            self.parent.SetEnableEdit(evt.Checked())
        #self.parent.SetEnableEdit(self.IsChecked(id))
        self.parent.NotifyGrid(0)
        #else:
        #    self.Debug('OnEnableEdit, found no Enable Edit item')

    def OnValidateTable(self,evt):
        self.Debug('OnValidateTable')
        if hasattr(self.parent.table,'ValidateTable'):
            self.parent.table.ValidateTable()
        else:
            self.Debug('OnValidate, table has no ValidateTable method')


_tmpmenuflag = [-1]


class TempMenu(wxMenu,MyDebug):

    def __init__(self,parent,menutmpl,debug):
        global _tmpmenuflag
        _tmpmenuflag[0] = -1
        MyDebug.__init__(self,debug)
        wxMenu.__init__(self,"")
        i = -1
        for item in menutmpl:
            i = i + 1
            exec """def tmpfun(evt):\n    global _tmpmenuflag\n    _tmpmenuflag[0] = %s\n"""%(i)
            setattr(self,'On%s'%(item[0]),tmpfun)
        buildmenus(self,menutmpl,self,verbose = debug)
