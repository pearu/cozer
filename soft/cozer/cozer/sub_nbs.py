#!/usr/bin/env python
"""

Copyright 2000 Pearu Peterson all rights reserved,
Pearu Peterson <pearu@ioc.ee>          
Permission to use, modify, and distribute this software is given under the
terms of the LGPL.  See http://www.fsf.org

NO WARRANTY IS EXPRESSED OR IMPLIED.  USE AT YOUR OWN RISK.
$Date: 2002/01/04 21:22:16 $
Pearu Peterson
"""

__version__ = "$Revision: 1.4 $"[10:-1]

from prefs import *
from tables import *
from timers import *
import analyzer
import reports

_labeledit = [
    ('title','Title'),
    ('venue','Venue'),
    ('date','Date'),
    ('officer','Officer of the day'),
    ('secretary','Secretary General'),
    ]

def _getdefault(self,text,default=''):
    if not self.topparent.eventdata.has_key(text):
        self.topparent.eventdata[text] = default
    r = self.topparent.eventdata[text]
    return r

def _fixsize(container):
    cs = container.GetSizeTuple()
    font = container.GetFont()
    tc = container.GetFullTextExtent(container.GetValue(),font)
    if tc[0]+20>cs[0]<600:
        container.SetSize(wxSize(tc[0]+20,cs[1]))
    elif 20<tc[0]<cs[0]-20:
        container.SetSize(wxSize(tc[0]+20,cs[1]))        


class GeneralInformationClasses(wxPanel,MyDebug):
    def __init__(self,parent,topparent,debug):
        MyDebug.__init__(self,debug)
        wxPanel.__init__(self,parent,-1)
        self.topparent = topparent
        self.grid = DataGrid(self,ClassDataTable,debug+(not not debug))
        self.grid.AutoSizeColumn(1)
        sizer = wxBoxSizer(wxVERTICAL)
        sizer.Add(self.grid,1,wxEXPAND)
        self.SetAutoLayout(true)
        self.SetSizer(sizer)
        self.grid.table.ValidateTable()
    def Entering(self):
        self.Debug('Entering')
        self.grid.table.ValidateTable()


class GeneralInformationParticipants(wxPanel,MyDebug):
    def __init__(self,parent,topparent,debug):
        MyDebug.__init__(self,debug)
        wxPanel.__init__(self,parent,-1)
        self.topparent = topparent
        self.grid = DataGrid(self,ParticipantDataTable,debug+(not not debug))
        sizer = wxBoxSizer(wxVERTICAL)
        sizer.Add(self.grid,1,wxEXPAND)
        self.SetAutoLayout(true)
        self.SetSizer(sizer)
    def Entering(self):
        self.Debug('Entering')
        self.grid.table.ResetDataTypes()
        self.grid.table.ValidateTable()


class GeneralInformationRules(wxPanel,MyDebug):
    def __init__(self,parent,topparent,debug):
        MyDebug.__init__(self,debug)
        wxPanel.__init__(self,parent,-1)
        self.topparent = topparent
        
        self.grid = DataGrid(self,RulesDataTable,debug+(not not debug))
        self.grid.AutoSizeColumn(1)
        self.grid.AutoSizeColumn(2)
        if topparent.eventdata.has_key('scoringsystem'):
            ss = map(str,topparent.eventdata['scoringsystem'])
            ss = string.join(ss,' ')
        else:
            ss = ''
            topparent.eventdata['scoringsystem'] = []
        sstext = wxTextCtrl(self,wxNewId(),ss)
        sstext.SetBackgroundColour(edit_bg)
        EVT_TEXT(self,sstext.GetId(), self.OnSSEdit)

        hs = wxBoxSizer(wxHORIZONTAL)
        hs.Add(wxStaticText(self,-1,'Scoring System:'))
        hs.Add(sstext,1,wxEXPAND)
        sizer = wxBoxSizer(wxVERTICAL)
        sizer.Add(hs,0,wxEXPAND)
        sizer.Add(self.grid,1,wxEXPAND)
        self.SetAutoLayout(true)
        self.SetSizer(sizer)

    def OnSSEdit(self,evt):
        self.Debug('OnSSEdit')
        ss = []
        flag = -1
        for p in string.split(evt.GetString(),' '):
            if not p: continue
            try: n = eval(p)
            except:
                self.Warning('Expected numeric but got %s. Returning.'%(`p`))
                return

            if len(ss) == 1:
                flag = (n>ss[0])
                ss.append(n)
            elif ss:
                if flag==0 and n<=ss[-1]:
                    ss.append(n)
                elif flag==1 and n>=ss[-1]:
                    ss.append(n)
                else:
                    self.Warning('Scoring sequence is not monotonic (flag=%s). Returning.'%(flag))
                    return
            else:
                ss.append(n)
        self.topparent.eventdata['scoringsystem'] = ss

    def Entering(self):
        self.Debug('Entering')
        self.grid.table.ValidateTable()


class GeneralInformation(wxPanel,MyDebug):
    
    def __init__(self,parent,topparent,debug):
        MyDebug.__init__(self,debug)
        wxPanel.__init__(self,parent,-1)
        self.parent = parent
        self.topparent = topparent

        gridsizer = wxGridSizer(len(_labeledit),2,2,2)
        self.inputs=[]
        for d,l in _labeledit:
            ID = wxNewId()
            input = wxTextCtrl(self, ID, "")
            setattr(self,'%sinput'%d,input)
            input.SetBackgroundColour(edit_bg)
            gridsizer.AddMany([(wxStaticText(self,-1,l),0,wxALIGN_RIGHT),input])
            exec """def fun(self,evt):\n    self.topparent.eventdata['%s'] = evt.GetString()\n    _fixsize(self.%sinput)\n"""%(d,d)
            func = lambda evt,self=self,fun=fun:fun(self,evt)
            EVT_TEXT(self, ID, func)
            input.SetValue(_getdefault(self,d))
            self.inputs.append(input)
        vsizer = wxBoxSizer(wxVERTICAL)
        vsizer.Add(gridsizer)

        self.CreatePages()
        nbsizer = wxNotebookSizer(self.nb)
        vsizer.Add(nbsizer,1,wxEXPAND)

        self.SetAutoLayout(true)
        self.SetSizer(vsizer)

    def CreatePages(self):
        self.Debug('CreatePages')
        try: self.nb.Destroy()
        except AttributeError: pass
        self.nb = wxNotebook(self,-1)
        self.pages = []
        for p in nb_geninf_pages:
            page = p[1](self.nb,self.topparent,self.debug+(not not self.debug))
            self.pages.append(page)
            self.nb.AddPage(page,p[0])
        self.nb.SetSelection(0)
        EVT_NOTEBOOK_PAGE_CHANGED(self, self.nb.GetId(), self.OnPageChanged)

    def OnPageChanged(self,evt):
        self.Debug('OnPageChanged')
        sel = evt.GetSelection()
        if sel>=0:
            if hasattr(self.pages[sel],'Entering'):
                self.pages[sel].Entering()
        #evt.Skip()

    def Reshow(self):
        self.Debug('Reshow')
        map(_fixsize,self.inputs)


class Races(wxPanel,MyDebug):

    def __init__(self,parent,topparent,debug):
        MyDebug.__init__(self,debug)
        wxPanel.__init__(self,parent,-1)
        self.parent = parent
        self.topparent = topparent
        
        splitter = wxSplitterWindow(self,-1)

        self.racelst = RacesList(splitter,topparent,debug+(not not debug))
        topparent.pagedict['racelist'] = self.racelst
        self.raceedit = RaceEdit(splitter,topparent,debug+(not not debug))
        self.racelst.edit = self.raceedit

        splitter.SplitVertically(self.racelst,self.raceedit)
        self.splitter = splitter

        hsizer = wxBoxSizer(wxHORIZONTAL)
        hsizer.Add(splitter,1,wxEXPAND)
        self.SetAutoLayout(true)
        self.SetSizer(hsizer)
        
    def Entering(self):
        self.Debug('Entering')
        self.splitter.SetSashPosition(100)
        self.splitter.SetMinimumPaneSize(20)


class Timer(wxPanel,MyDebug):
    timerwin = None
    optwin = None

    def __init__(self,parent,topparent,debug):
        MyDebug.__init__(self,debug)
        wxPanel.__init__(self,parent,-1)
        self.parent = parent
        self.topparent = topparent
        self.sizer = wxBoxSizer(wxVERTICAL)
        self.racelst = topparent.pagedict['racelist']
        self.CreateOptWin()
        self.SetAutoLayout(true)
        self.SetSizer(self.sizer)

    def SelectRace(self,evt):
        self.Debug('SelectRace')
        if hasattr(self,'startbut') and self.startbut.GetLabel() == 'Stop':
            self.Info('You must stop the race first.')
            #evt.Skip()
            #i = -1
            #for cl,h,r in self.timerwin.race:
            #    i = i + 1
            #    self.timerwin.EmulateClicks(i,r)
            return
        self.racelst.currentItem = evt.GetSelection()
        self.racelst.SetRace()
        self.TimerWin()

    def SetButSize(self,evt):
        self.Debug('SetButSize')
        bsize = evt.GetPosition()
        setopt(self,'id_but_size',bsize)
        if self.timerwin and hasattr(self.timerwin,'buts'):
            for b in self.timerwin.buts:
                b.SetSize(wxSize(bsize,bsize))

    def SetButTextSize(self,evt):
        self.Debug('SetButTextSize')
        bsize = evt.GetPosition()
        setopt(self,'id_but_textsize',bsize)
        if self.timerwin and hasattr(self.timerwin,'buts'):
            for b in self.timerwin.buts:
                f=b.GetFont()
                f.SetPointSize(bsize)
                b.SetFont(f)

    def Entering(self):
        self.Debug('Entering')
        if not self.optwin: return
        self.racechoice.Clear()
        for c in map(self.racelst.lst.GetItemText,range(self.racelst.lst.GetItemCount())):
            self.racechoice.Append(c)
        
    def CreateOptWin(self):
        self.Debug('CreateOptWin')
        if self.optwin:
            self.sizer.Remove(self.optwin)
            self.optwin.Destroy()
        self.optwin=wxPanel(self,-1,size=wxSize(500,30))
        hsizer=wxBoxSizer(wxHORIZONTAL)
        self.optwin.SetAutoLayout(true)
        self.optwin.SetSizer(hsizer)
        self.sizer.Add(self.optwin,0,wxEXPAND)

        choice = wxChoice(self.optwin,wxNewId(),choices=map(self.racelst.lst.GetItemText,range(self.racelst.lst.GetItemCount())))
        EVT_CHOICE(self.optwin,choice.GetId(),self.SelectRace)
        hsizer.Add(choice)
        self.racechoice = choice

        # Use wxSpinCtrl
        spin = wxSpinButton(self.optwin,wxNewId(),style=wxSP_VERTICAL)
        spin.SetRange(20, 100)
        spin.SetValue(getopt(self,'id_but_size',40))
        EVT_SPIN(self.optwin, spin.GetId(), self.SetButSize)
        hsizer.Add(spin)
        
        spin = wxSpinButton(self.optwin,wxNewId(),style=wxSP_VERTICAL)
        spin.SetRange(10, 40)
        spin.SetValue(getopt(self,'id_but_textsize',14))
        EVT_SPIN(self.optwin, spin.GetId(), self.SetButTextSize)
        hsizer.Add(spin)

        self.startbut = wxButton(self.optwin,wxNewId(),'Start')
        EVT_BUTTON(self.optwin,self.startbut.GetId(),self.Start)
        hsizer.Add(self.startbut)

        if 0<=self.topparent.currentRace<len(self.topparent.eventdata['races']):
            choice.SetSelection(self.topparent.currentRace)
            #self.TimerWin()
        self.sizer.Layout()

    def Start(self,evt):
        self.Debug('Start')
        t = time.time()
        if not self.timerwin:
            return
        if self.startbut.GetLabel() == 'Stop':
            self.timerwin.CleanUp()
            i = -1
            for cl,h,r in self.timerwin.race:
                i = i + 1
                self.timerwin.allowclicks[i] = 0
            self.startbut.SetLabel('Start')
            return
        else:
            self.startbut.SetLabel('Stop')
        skip,i = [],-1
        for cl,h,r in self.timerwin.race:
            fl = 0
            i = i + 1
            for k in r.keys(): fl = fl or r[k]
            if fl:
                mess = wxMessageDialog(self,
                                       "Race record for class %s heat %s contains data!\nDo you wish to overwrite it?\nIf affirmative, old data will be lost!"%(cl,h),
                                       "Overwrite race record?",
                                       style=wxYES_NO|wxCENTRE|wxICON_QUESTION|wxNO_DEFAULT)
                if not mess.ShowModal() == wxID_YES:
                    skip.append(i)
                    continue
            self.timerwin.info[i]['starttime'] = t
            if self.timerwin.info[i].has_key('racetime'):
                del self.timerwin.info[i]['racetime']                
            for k in r.keys():
                r[k] = []

        self.TimerWin()
        i = -1
        self.timerwin.finished = {}
        self.timerwin.clicks = {}
        self.timerwin.allowclicks = {}
        for cl,h,r in self.timerwin.race:
            i = i + 1
            if i in skip:
                self.timerwin.allowclicks[i] = 0
                continue
            self.timerwin.finished[i]=[]
            self.timerwin.clicks[i]=[]
            self.timerwin.allowclicks[i] = 1

    def TimerWin(self):
        self.Debug('TimerWin')
        if not 0<=self.topparent.currentRace<len(self.topparent.eventdata['races']):
            self.Info('You must select race first.')
            return
        racedata=self.topparent.eventdata['races'][self.topparent.currentRace]
        if not self.topparent.eventdata.has_key('record'):
            self.topparent.eventdata['record']={}
        record = self.topparent.eventdata['record']

        race = []
        info = []
        for ch in racedata:
            cl,h=ch[1:]
            qcl=cl
            if isqclass(cl): qcl=cl[:-2]
            elif istclass(cl): qcl=cl[:-2]
            if not (cl and h): continue
            if not record.has_key(cl): record[cl]={}
            prevheats = record[cl].keys()
            if not record[cl].has_key(h): record[cl][h]={},{}
            for p in self.topparent.eventdata['participants']:
                if p[4]==qcl:
                    try: val=eval(p[5])
                    except: val=p[5]
                    if not record[cl][h][1].has_key(val):
                        record[cl][h][1][val]=[]
            rpat=None
            for l in self.topparent.eventdata['classes']:
                if l[1] and l[2] and l[1]==cl:
                    rpat,sheats=self.topparent.CrackRacePattern(l[2],cl)
                    break

            if h[-1] in ['r','q','t']: li = eval(h[:-1])-1
            else: li = eval(h)-1
            record[cl][h][0]['course'] = rpat[li]
            record[cl][h][0]['sheats'] = sheats
            race.append((cl,h,record[cl][h][1]))
            info.append(record[cl][h][0])
        if self.timerwin:
            self.sizer.Remove(self.timerwin)
            self.timerwin.CleanUp()
            self.timerwin.Destroy()
        self.timerwin = TimerWin1(info,race,self.topparent,self,self.debug+(not not self.debug))
        self.sizer.Add(self.timerwin,1,wxEXPAND)
        self.sizer.Layout()

    def ResetEvent(self):
        self.Debug('ResetEvent')


class EditRecord(wxPanel,MyDebug):
    editwin = None
    optwin = None
    def __init__(self,parent,topparent,debug):
        MyDebug.__init__(self,debug)
        wxPanel.__init__(self,parent,-1)
        self.parent = parent
        self.topparent = topparent
        self.sizer = wxBoxSizer(wxVERTICAL)
        if not topparent.eventdata.has_key('record'):
            topparent.eventdata['record'] = {}
        self.record = topparent.eventdata['record']
        if not topparent.eventdata.has_key('scoringsystem'):
            topparent.eventdata['scoringsystem'] = []
        self.scoringsystem = topparent.eventdata['scoringsystem']
        
        self.CreateOptWin()
        self.SetAutoLayout(true)
        self.SetSizer(self.sizer)

    def Entering(self):
        self.Debug('Entering')
        if not self.optwin: return
        self.recs = []
        self.recchoice.Clear()
        clks = self.record.keys()
        clks.sort()
        for cl in clks:
            hks = self.record[cl].keys()
            hks.sort()
            for h in hks:
                self.recs.append((cl,h))
                self.recchoice.Append('%s/%s'%(cl,h))
        
    def CreateOptWin(self):
        self.Debug('CreateOptWin')
        if self.optwin:
            self.sizer.Remove(self.optwin)
            self.optwin.Destroy()
        self.optwin=wxPanel(self,-1,size=wxSize(500,30))
        hsizer=wxBoxSizer(wxHORIZONTAL)
        self.optwin.SetAutoLayout(true)
        self.optwin.SetSizer(hsizer)
        self.sizer.Add(self.optwin,0,wxEXPAND)

        choice = wxChoice(self.optwin,wxNewId(),choices=[])
        EVT_CHOICE(self.optwin,choice.GetId(),self.SelectClassHeat)
        hsizer.Add(choice)
        self.recchoice = choice

        delbut = wxButton(self.optwin,wxNewId(),'Delete')
        EVT_BUTTON(self.optwin,delbut.GetId(),self.DeleteClassHeat)
        hsizer.Add(delbut)

        vs = wxBoxSizer(wxHORIZONTAL)
        self.starttimetext = wxStaticText(self.optwin,wxNewId(),'Start time',
                                          size=wxSize(250,-1))
        vs.Add(self.starttimetext)
        self.timetext = wxStaticText(self.optwin,wxNewId(),'Race time',
                                     size=wxSize(250,-1))
        vs.Add(self.timetext)        
        hsizer.Add(vs)

    def SelectClassHeat(self,evt):
        self.Debug('SelectClassHeat')
        cls,heat = self.recs[evt.GetSelection()]
        self.Info('Selected class %s heat %s'%(cls,heat))
        if self.editwin:
            self.sizer.Remove(self.editwin)
            self.editwin.Destroy()

        #reload(analyzer)
        
        res = analyzer.analyze(heat,self.record[cls][heat],self.scoringsystem)
        self.editwin = EditWin1(self.record[cls][heat][0],self.record[cls][heat][1],
                                res,
                                self.topparent,self,self.debug+(not not self.debug))
        self.sizer.Add(self.editwin,1,wxEXPAND)
        self.sizer.Layout()
        
    def DeleteClassHeat(self,evt):
        self.Debug('DeleteClassHeat')
        sel = self.recchoice.GetSelection()
        if sel<0:
            self.Info('Select Class/Heat first.')
            return
        cls,heat = self.recs[sel]
        mess = wxMessageDialog(self,
                                  "Are you sure that you want to delete race record of class %s heat %s"%(cls,heat),
                                  "Delete race record?",
                               style=wxYES_NO|wxCENTRE|wxICON_QUESTION|wxNO_DEFAULT)
        if mess.ShowModal() == wxID_YES:
            del self.record[cls][heat]
            self.Entering()


class Reports(wxPanel,MyDebug):
    optwin = None
    checkwin = None
    repfunc = None

    def __init__(self,parent,topparent,debug):
        MyDebug.__init__(self,debug)
        wxPanel.__init__(self,parent,-1)
        self.parent = parent
        self.topparent = topparent
        if not self.topparent.eventdata.has_key('record'):
            self.topparent.eventdata['record']={}
        self.record = self.topparent.eventdata['record']
        if not self.topparent.eventdata.has_key('savechecked'):
            self.topparent.eventdata['savechecked']={}
        self.savechecked = self.topparent.eventdata['savechecked']
        self.sizer = wxBoxSizer(wxVERTICAL)
        self.CreateOptWin()
        self.SetAutoLayout(true)
        self.SetSizer(self.sizer)

    def CreateOptWin(self):
        self.Debug('CreateOptWin')
        if self.optwin:
            self.sizer.Remove(self.optwin)
            self.optwin.Destroy()
        self.optwin=wxPanel(self,-1,size=wxSize(500,30))
        hsizer=wxBoxSizer(wxHORIZONTAL)
        self.optwin.SetAutoLayout(true)
        self.optwin.SetSizer(hsizer)
        self.sizer.Add(self.optwin,0,wxEXPAND)

        hsizer.Add(wxStaticText(self.optwin,-1,"Report: "))
        choice = wxChoice(self.optwin,wxNewId(),choices=[],size=wxSize(120,-1))
        EVT_CHOICE(self.optwin,choice.GetId(),self.SelectReportType)
        hsizer.Add(choice)

        viewbut = wxButton(self.optwin,wxNewId(),'Preview')
        EVT_BUTTON(self.optwin,viewbut.GetId(),self.Preview)
        hsizer.Add(viewbut)

        psviewbut = wxButton(self.optwin,wxNewId(),'PSPreview')
        EVT_BUTTON(self.optwin,psviewbut.GetId(),self.PSPreview)
        hsizer.Add(psviewbut)

        printbut = wxButton(self.optwin,wxNewId(),'Print')
        EVT_BUTTON(self.optwin,printbut.GetId(),self.Print)
        hsizer.Add(printbut)

        self.reps = []
        repmap = reports.report_map
        for k in repmap.keys():
            choice.Append('%s'%k)
            self.reps.append(repmap[k])
        if self.reps:
            choice.SetSelection(0)
            self.repfunc = self.reps[0]

    def SelectReportType(self,evt):
        self.Debug('SelectReportType')
        self.repfunc = self.reps[evt.GetSelection()]

    def Preview(self,evt):
        self.Debug('Preview')
        fn,opts = self.GenerateReport()
        runlatex(fn,opts)
        rundviview(fn,opts)

    def PSPreview(self,evt):
        self.Debug('Preview')
        fn,opts = self.GenerateReport()
        runlatex(fn,opts)
        rundvips(fn,opts)
        runpsview(fn,opts)

    def Print(self,evt):
        self.Debug('Print')
        fn,opts = self.GenerateReport()
        runlatex(fn,opts)
        if os.name == 'nt':
            rundvips(fn,opts)
            if not opts.has_key('gsview'):
                opts['gsview'] = ''
            opts['gsview'] = opts['gsview'] + '/P'
            runpsview(fn,opts)
        else:
            rundvips(fn,opts,'')

    def GenerateReport(self):
        self.Debug('GenerateReport')
        if not self.repfunc: return
        self.topparent.eventdata['sheats']={}
        for l in self.topparent.eventdata['classes']:
            if l[1] and l[2]:
                rpat,self.topparent.eventdata['sheats'][l[1]]=self.topparent.CrackRacePattern(l[2])
        return self.repfunc(self.checkedcls,self.checked,self.topparent.eventdata)

    def Entering(self):
        self.Debug('Entering')
        if not self.optwin: return
        win = self.CheckWin()

        vsizer = wxBoxSizer(wxVERTICAL)
        clses = map(lambda l:l[1],self.topparent.eventdata['classes'])
        self.clsidmap = {}
        self.idmap = {}
        self.checkedcls = []
        self.checked = {}
        for cl in clses:
            hsizer = wxBoxSizer(wxHORIZONTAL)
            vsizer.Add(hsizer)
            ID = wxNewId()
            clcheck = wxCheckBox(win,ID," Class %s"%cl,size=wxSize(120,-1))
            EVT_CHECKBOX(win,ID,self.Checking)
            hsizer.Add(clcheck,0)
            self.clsidmap[ID]=cl
            self.checked[cl]=[]
            if self.savechecked.has_key(cl) and self.savechecked[cl]:
                if cl not in self.checkedcls:
                    self.checkedcls.append(cl)
                clcheck.SetValue(true)
            if (not self.record.has_key(cl)) or (not self.record[cl]): continue
            hks = self.record[cl].keys()
            hks.sort()
            for h in hks:
                ID = wxNewId()
                hcheck = wxCheckBox(win,ID," Heat %s"%h,size=wxSize(-1,-1))
                EVT_CHECKBOX(win,ID,self.Checking)
                hsizer.Add(hcheck,0)
                self.idmap[ID] = cl,h
                if self.savechecked.has_key((cl,h)) and self.savechecked[cl,h]:
                    if h not in self.checked[cl]:
                        self.checked[cl].append(h)
                    hcheck.SetValue(true)
        vsizer.Layout()

    def Checking(self,evt):
        self.Debug('Checking')
        ID=evt.GetId()
        if self.clsidmap.has_key(ID):
            cl = self.clsidmap[ID]
            if evt.Checked():
                if cl not in self.checkedcls:
                    self.checkedcls.append(cl)
                self.savechecked[cl]=1
            else:
                if cl in self.checkedcls:
                    del self.checkedcls[self.checkedcls.index(cl)]
                self.savechecked[cl]=0
        elif self.idmap.has_key(ID):
            cl,h = self.idmap[ID]
            if evt.Checked():
                if h not in self.checked[cl]:
                    self.checked[cl].append(h)
                self.savechecked[cl,h]=1
            else:
                if h in self.checked[cl]:
                    del self.checked[cl][self.checked[cl].index(h)]
                self.savechecked[cl,h]=0
        else:
            self.Warning('Unknown ID=',ID)

    def CheckWin(self):
        self.Debug('CheckWin')
        if self.checkwin:
            self.sizer.Remove(self.checkwin)
            self.checkwin.Destroy()
        self.checkwin = wxScrolledWindow(self,-1,wxPoint(0, 0),style=wxSUNKEN_BORDER)
        self.checkwin.SetScrollbars(20, 20, 50, 50)
        self.sizer.Add(self.checkwin,1,wxEXPAND)
        self.sizer.Layout()
        return self.checkwin

    def ResetEvent(self):
        self.Debug('ResetEvent')

class Log(wxPanel,MyDebug):

    def __init__(self,parent,topparent,debug):
        MyDebug.__init__(self,debug)
        wxPanel.__init__(self,parent,-1)
        self.parent = parent
        self.topparent = topparent

        self.log = wxTextCtrl(self, -1,
                              style = wxTE_MULTILINE|wxTE_READONLY|wxHSCROLL)
        wxLog_SetActiveTarget(wxLogTextCtrl(self.log))

        self.sizer = wxBoxSizer(wxVERTICAL)
        self.sizer.Add(self.log,1,wxEXPAND)
        self.SetAutoLayout(true)
        self.SetSizer(self.sizer)    

    def Entering(self):
        self.Debug('Entering')
        empty_log()

nb_pages = [
    ('General Information',GeneralInformation),
    ('Timer',Timer),
    ('Edit Race Records',EditRecord),
    ('Reports',Reports),
    ('Log',Log),
    ]

nb_geninf_pages = [
    ('Classes',GeneralInformationClasses),
    ('Participants',GeneralInformationParticipants),
    ('Races',Races),
    ('Rules',GeneralInformationRules),
    ]
