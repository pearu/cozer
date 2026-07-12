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

import wx
import wx.grid
from prefs import *
from buildmenus import *



class ClassDataTable(wx.grid.PyGridTableBase,MyDebug):
    defaultdatarow = ['internal','',0,0]
    def __init__(self,topparent,debug):
        MyDebug.__init__(self,debug)
        wx.grid.PyGridTableBase.__init__(self)
        self.colLabels = ['Class','Heats','Laps']
        self.dataTypes = [wx.grid.GRID_VALUE_STRING,
                          wx.grid.GRID_VALUE_NUMBER+':1,12',
                          wx.grid.GRID_VALUE_NUMBER+':1,12']
        self.topparent = topparent
        if not self.topparent.eventdata.has_key('classes'):
            self.topparent.eventdata['classes'] = []
        self.data = self.topparent.eventdata['classes']
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
        return self.data[row][col+1]
    def SetValue(self, row, col, value):
        self.Debug1('SetValue, row col=',row,col,'value=',value)
        self.data[row][col+1] = value
    def GetColLabelValue(self, col):
        self.Debug1('GetColLabelValue, col=',col)
        return self.colLabels[col]
    def GetTypeName(self, row, col):
        self.Debug1('GetTypeName, row col=',row,col)
        return self.dataTypes[col]
    def ResetEvent(self):
        self.Debug('ResetEvent')
        #msg = wx.grid.GridTableMessage(self,wx.grid.GRIDTABLE_NOTIFY_ROWS_APPENDED,-100)
        #self.GetView().ProcessTableMessage(msg)
    def Sort(self,col):
        self.Debug('Sort, col=',col)
        for i in range(self.GetNumberRows()):
            self.data[i][0] = self.data[i][col+1]
        self.data.sort()

    

class ClassGrid(wx.grid.Grid,MyDebug):
    def __init__(self,parent,topparent,pos,debug):
        MyDebug.__init__(self,debug)
        wx.grid.Grid.__init__(self,parent,-1,pos)
        self.classtable = ClassDataTable(topparent,debug+(not not debug))
        self.SetTable(self.classtable,true)
        self.data = self.classtable.data
        self.SetDefaultCellBackgroundColour(edit_bg)
        self.SetRowLabelSize(20)
        self.SetColLabelSize(20)
        self.SetMargins(0,0)
        wx.grid.EVT_GRID_LABEL_RIGHT_CLICK(self,self.OnLabelRightClick)
        wx.grid.EVT_GRID_LABEL_LEFT_CLICK(self,self.OnLabelLeftClick)
        wx.EVT_KEY_DOWN(self, self.OnKeyDown)
        wx.grid.EVT_GRID_COL_SIZE(self,self.ResetColsSize)
        self.ResetColsSize()
    def ResetColsSize(self,evt = None):
        self.Debug('ResetColsSize')
        sz = self.GetColLabelSize() + 20
        for i in range(self.GetNumberCols()):
            sz = sz + self.GetColSize(i)
        self.SetSize(wx.Size(sz,200))

    def OnKeyDown(self, evt):
        if evt.KeyCode == wx.WXK_DELETE:
            self.Debug('OnKeyDown, delete')
            if self.GetGridCursorCol()==0:
                row = self.GetGridCursorRow()
                self.DeleteClass(row)
                if row>0:
                    self.SetGridCursor(row-1, 0)
                    self.MakeCellVisible(row-1, 0)
            evt.Skip()
            return
        if evt.KeyCode not in [wx.WXK_RETURN,wx.WXK_TAB] or evt.ControlDown():
            evt.Skip()
            return

        if self.GetTable().GetNumberRows() == 0:
            self.Debug('OnKeyDown, first new')
            self.NewClass(0)
            self.SetGridCursor(0, 0)
            self.MakeCellVisible(0, 0)
            return
        success = self.MoveCursorRight(evt.ShiftDown())
        if not success:
            self.Debug('OnKeyDown, append new')
            newRow = self.GetGridCursorRow() + 1
            if not newRow < self.GetTable().GetNumberRows():
                self.NewClass(0)
            self.SetGridCursor(newRow, 0)
            self.MakeCellVisible(newRow, 0)

    def OnLabelRightClick(self,evt):
        if evt.GetCol() == -1:
            row = evt.GetRow()
            self.Debug('OnLabelRigthClick, row=',row)
            menu = ClassMenu(self,row,self.debug+(not not self.debug))
            self.PopupMenu(menu,evt.GetPosition())
            menu.Destroy()
            return
        if evt.GetRow() == -1:
            self.Debug('OnLabelRigthClick, data.reverse')
            self.data.reverse()
            self.Refresh(0)
    def OnLabelLeftClick(self,evt):
        if evt.GetRow() == -1:
            col = evt.GetCol()
            self.Debug('OnLabelLeftClick, col=',col)
            self.classtable.Sort(col)
            self.Refresh(0)
    def NewClass(self,row):
        self.Debug('NewClass')
        self.data.append(eval(`self.classtable.defaultdatarow`))
        self.Refresh(1)
    def InsertClass(self,row):
        self.Debug('InsertClass, row=',row)
        self.data.insert(row,eval(`self.classtable.defaultdatarow`))
        self.Refresh(1)
        self.SetGridCursor(row, 0)
    def DeleteClass(self,row):
        if not self.classtable.GetNumberRows():
            return
        self.Debug('DeleteClass, row=',row)
        del self.data[row]
        self.Refresh(-1)
    def Refresh(self,flag):
        self.Debug('Refresh')
        msg = wx.grid.GridTableMessage(self.classtable,wx.grid.GRIDTABLE_NOTIFY_ROWS_APPENDED,flag)
        self.classtable.GetView().ProcessTableMessage(msg)        
class ClassMenu(wx.Menu,MyDebug):
    def __init__(self,parent,row,debug):
        MyDebug.__init__(self,debug)
        wx.Menu.__init__(self,"Class Menu")
        self.parent = parent
        self.row = row
        if row == -1:
            buildmenus(self,classtablelabelmenu[:2],self,verbose = 1)
        else:
            buildmenus(self,classtablelabelmenu,self,verbose = 1)
    def OnNew(self,evt):
        self.Debug('OnNew')
        self.parent.NewClass(self.row)
    def OnInsert(self,evt):
        self.Debug('OnInsert')
        self.parent.InsertClass(self.row)
    def OnDelete(self,evt):
        self.Debug('OnDelete')
        self.parent.DeleteClass(self.row)


