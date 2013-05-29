#!/usr/bin/env python
"""
COZER - COmpetition organiZER
"""
"""

Copyright 2000,2001,2013 Pearu Peterson all rights reserved,
Pearu Peterson <pearu@cens.ioc.ee>          
Permission to use, modify, and distribute this software is given under the
terms of the GPL.  See http://www.fsf.org

NO WARRANTY IS EXPRESSED OR IMPLIED.  USE AT YOUR OWN RISK.
$Date: 2001/12/25 19:16:40 $
$Revision: 1.3 $
Pearu Peterson
"""

from __version__ import __version__

import os,pprint,sys,shutil

import wx

from buildmenus import buildmenus
from sub_menus import mainmenubar
from sub_nbs import nb_pages
import prefs
from prefs import *

defaulteventdata={'classes':[[]],
                  'participants':[[]],
                  'races':[[['','','']]],
                  'rules':[[]],
                  'configure':{'id_but_size':40}
                  }


class MainFrame(wx.Frame,MyDebug):
    """
eventdata - a dictionary with keys:
    title - a string
    venue - a string
    date - a string
    officer - a string
    secretary - a string
    scoringsystem - a monotonic list of numbers
    rules - a list of lists: [[<sortby>,<action>,<paragraph>,<description>]]
    classes - a list of lists: [[<sortby>,<class>,<race pattern>],..]
    participants - a list of lists: [[<sortby>,<firstname>,<surname>,<club>,<class>,<id>],..]
    races - a list of lists of lists: [[[<sortby>,<class>,<heat>],...],...]
    record - a dict of dicts of lists: {<class>:{<heat>:[(<infodict>,<recorddict>),..]}}
      <infodict> - a dict: {starttime,racetime,course}
      <recorddict> - a dict of lists of tuples: {<id>:[(<code>,<data>),...]}
      <code>: (see prefs.py)
          1=completed lap => <data>=lap time
          2=inserted lap => <data>=lap time
          3=lost lap => <data>=time,paragraph
          4=penalty lap => <data>=time,paragraph
          10=didn't start => <data>=time,paragraph
          11=interruption => <data>=time,paragraph
          12=disqualification => <data>=time,paragraph
      Negative <code>'s are ignored (enable on/off feature).
    savechecked - a dict of tuples: {(<class>,<heat>):<0|1>}
    configure - a dict: {id_but_size,language,..}
"""
    eventdata=defaulteventdata
    pagedict={}
    currentRace = -1
    filepath = 'Untitled.coz'

    def __init__(self,debug,fn=''):

        MyDebug.__init__(self,debug)
        wx.Frame.__init__(self, None, -1, "Cozer - The Competition Organizer",
                            wx.DefaultPosition, wx.Size(800,500))
        self.OpenCozFile(fn)
        buildmenus(self,mainmenubar,self,verbose=debug)
        self.statusbar = self.CreateStatusBar()
        self.CreatePages()
        wx.EVT_CLOSE(self,self.OnFileQuit)
        prefs.top_parent = self

    def CreatePages(self):
        self.nb = wx.Notebook(self,-1)
        self.nb.pages = []
        i = -1
        for p in nb_pages:
            i = i + 1
            page = p[1](self.nb,self,self.debug+(not not self.debug))
            self.nb.AddPage(page,p[0])
            self.nb.pages.append(page)
            self.pagedict[p[0]]=i
        self.nb.SetSelection(0)
        wx.EVT_NOTEBOOK_PAGE_CHANGED(self, self.nb.GetId(), self.OnPageChanged)

    def SetFilePath(self,fpath):
        self.Debug('SetFilePath fpath=',fpath)
        self.filepath = fpath
        self.SetTitle("Cozer - The Competition Organizer: %s"%(fpath))

    def OnPageChanged(self,evt):
        self.Debug('OnPageChanged')
        sel = evt.GetSelection()
        if 0<=sel<len(self.nb.pages):
            if hasattr(self.nb.pages[sel],'Entering'):
                self.statusbar.SetStatusText('',0) # clear status bar
                self.nb.pages[sel].Entering()

    def OnFileNew(self,evt,filepath='Untitled.coz'):
        self.Debug('OnFileNew, filepath=',filepath)
        self.SetFilePath(filepath)
        exec 'self.eventdata=%s'%`defaulteventdata`
        self.ResetEvent()
        return 1

    def OnFileOpen(self,evt):
        self.Debug('OnFileOpen')
        fileopen = wx.FileDialog(self,'Open Cozer event file',
                                   wildcard='Cozer events (*.coz)|*.coz',
                                   style=wx.OPEN|wx.FILE_MUST_EXIST)
        if fileopen.ShowModal() == wx.ID_OK:
            if not self.filepath == 'Untitled.coz':
                mess = wx.MessageDialog(self,
                                          "Do you wish to save current event before loading new one?",
                                          "Save current?",
                                          style=wx.YES_NO|wx.CENTRE|wx.ICON_QUESTION)
                if mess.ShowModal() == wx.ID_YES:
                    if not self.OnFileSave(evt):
                        return 0
            self.OpenCozFile(fileopen.GetPath())
            self.ResetEvent()
            return 1
        return 0

    def OnFileAppend(self,evt):
        self.Debug('OnFileAppend')
        fileopen = wx.FileDialog(self,'Append Cozer event file',
                                   wildcard='Cozer events (*.coz)|*.coz',
                                   style=wx.OPEN|wx.FILE_MUST_EXIST)
        if fileopen.ShowModal() == wx.ID_OK:
            self.AppendCozFile(fileopen.GetPath())
            self.ResetEvent()
            return 1
        return 0

    def AppendCozFile(self,fn):
        self.Debug('AppendCozFile fn=%s'%`fn`)
        if not (fn and os.path.isfile(fn)):
            self.Debug('Cannot open file.')
            return 0
        import cPickle;pickle = cPickle
        f = open(fn,'rb')
        eventdata = normalize_str(pickle.load(f))
        f.close()
        self.AppendEventData(eventdata)

    def AppendEventData(self,eventdata):
        self.Debug('AppendEventData')
        if not type(eventdata)==type({}): return 0
        for k in eventdata.keys():
            if ((not self.eventdata.has_key(k)) or (checkempty(self.eventdata[k]))):
                self.Message('Setting eventdata[%s]'%(`k`))
                self.eventdata[k] = eventdata[k]
        if eventdata.has_key('classes'):
            for l in eventdata['classes']:
                if checkempty(l): continue
                fl = 1
                for l1 in self.eventdata['classes']:
                    if l[1]==l1[1]: fl = 0; break
                if fl and l[1]:
                    self.Message('Appending class %s to the class list'%(l[1]))
                    self.eventdata['classes'].append(l)
        if eventdata.has_key('participants'):
            for l in eventdata['participants']:
                if checkempty(l): continue
                fl = 1
                for l1 in self.eventdata['participants']:
                    if l[4]==l1[4] and l[5]==l1[5]: fl = 0; break
                if fl:
                    self.Message('Appending "%s %s" class=%s id=%s to the participant list'%(l[1],l[2],l[4],l[5]))
                    self.eventdata['participants'].append(l)
        if eventdata.has_key('races'):
            for l in eventdata['races']:
                if checkempty(l): continue
                fl = 1
                ll = []
                for r in l:
                    if (not r[1]) or (not r[2]): fl=0;break 
                    ll.append(r[1]+'/'+r[2])
                for l1 in self.eventdata['races']:
                    for r in l1:
                        if r[1]+'/'+r[2] in ll: fl=0;break
                    if not fl: break
                if fl:
                    self.Message('Appending %s to the race list'%(`string.join(ll,',')`))
                    self.eventdata['races'].append(l)
        if eventdata.has_key('record'):
            for cl in eventdata['record'].keys():
                if not self.eventdata['record'].has_key(cl):
                    self.Message('Appending full record of %s to the record dict.'%(cl))
                    self.eventdata['record'][cl] = eventdata['record'][cl]
                    continue
                for h in eventdata['record'][cl].keys():
                    if (not self.eventdata['record'][cl].has_key(h)) or checkempty(self.eventdata['record'][cl][h]):
                        self.Message('Appending %s heat %s record to the record dict.'%(cl,h))
                        self.eventdata['record'][cl][h] = eventdata['record'][cl][h]
                        continue
        return 1

    def OpenCozFile(self,fn):
        self.Debug('OpenCozFile fn=%s'%`fn`)
        if not (fn and os.path.isfile(fn)):
            self.Debug('Cannot open file.')
            return 0
        self.SetFilePath(fn)
        self.Debug('New filepath is',`self.filepath`,'Loading...')
        import cPickle;pickle = cPickle
        f = open(self.filepath,'rb')
        d = pickle.load(f)
        d = normalize_str(d)
        self.eventdata = d
        f.close()
        return 1

    def OnFileSave(self,evt):
        self.Debug('OnFileSave, filepath=',self.filepath)
        if self.filepath in ['','Untitled.coz']:
            return self.OnFileSaveAs(evt)
        import cPickle;pickle = cPickle
        f = open(self.filepath,'wb')
        pickle.dump(denormalize_str(self.eventdata),f,1)
        f.close()
        return 1

    def OnFileSaveAs(self,evt):
        self.Debug('OnFileSaveAs')
        filesaveas = wx.FileDialog(self,'Save Cozer event as file',
                                     wildcard='Cozer events (*.coz)|*.coz',
                                     style=wx.SAVE|wx.OVERWRITE_PROMPT)
        if filesaveas.ShowModal() == wx.ID_OK:
            self.SetFilePath(filesaveas.GetPath())
            return self.OnFileSave(evt)
        return 0

    def OnFileImportPython(self,evt):
        self.Debug('OnFileImportPython')
        file = wx.FileDialog(self,'Import Cozer event from a Python file',
                                   wildcard='Python (*.py)|*.py',
                                   style=wx.OPEN|wx.FILE_MUST_EXIST)
        if file.ShowModal() == wx.ID_OK:
            d = eval(open(file.GetPath()).read())
            if type(d) == type({}):
                self.eventdata = d
                self.ResetEvent()
                return 1
        return 0

    def OnFileImportAppendPython(self,evt):
        self.Debug('OnFileImportAppendPython')
        file = wx.FileDialog(self,'Append Cozer event from a Python file',
                                   wildcard='Python (*.py)|*.py',
                                   style=wx.OPEN|wx.FILE_MUST_EXIST)
        if file.ShowModal() == wx.ID_OK:
            d = eval(open(file.GetPath()).read())
            if type(d) == type({}):
                self.AppendEventData(d)
                self.ResetEvent()
                return 1
        return 0

    def OnFileExportPython(self,evt):
        self.Debug('OnFileExportPython')
        file = wx.FileDialog(self,'Export Cozer event to a Python file',
                                     wildcard='Python (*.py)|*.py',
                                     style=wx.SAVE|wx.OVERWRITE_PROMPT)
        if file.ShowModal() == wx.ID_OK:
            f = open(file.GetPath(),'w')
            pp = pprint.PrettyPrinter(width=120,stream=f)
            pp.pprint(self.eventdata)
            f.close()
            return 1
        return 0

    def OnFileExportStdout(self,evt):
        self.Debug('OnFileExportStdout')
        pp = pprint.PrettyPrinter(width=120)
        pp.pprint(self.eventdata)
        return 1

    def OnFileExit(self,evt):
        self.Debug('OnFileExit')
        if self.OnFileSave(evt):
            self.OnFileQuit(evt,0)

    def OnFileQuit(self,evt,askconformation=1):
        self.Debug('OnFileQuit')
        if 1 and askconformation:
            mess = wx.MessageDialog(self,
                                      "Are you sure you want to quit Cozer without saving event?",
                                      "Quit without save?",
                                      style=wx.YES_NO|wx.CENTRE|wx.ICON_QUESTION|wx.NO_DEFAULT)
            if mess.ShowModal() == wx.ID_NO: return 0
        self.Destroy()
        return 1

    def set_language(self,language='English'):
        self.Debug('set_language')
        languages = []
        for k in dir(self):
            if k[:12] == 'FileLanguage':
                languages.append(k[12:-3])
                obj = getattr(self,k)
                if language==languages[-1]:
                    obj.Check(true)
                else:
                    obj.Check(false)
        if language not in languages:
            self.Warning('Language %s is not in %s. Using English.'%(`language`,languages))
            self.set_language()
        else:
            self.eventdata['configure']['language'] = language

    def OnFileLanguageEnglish(self,evt):
        self.Debug('OnFileLanguageEnglish')
        self.set_language('English')
        
    def OnFileLanguageEstonian(self,evt):
        self.Debug('OnFileLanguageEstonian')
        self.set_language('Estonian')

    def OnHelpAbout(self,evt):
        self.Debug('OnHelpAbout')
        from sub_help import AboutBox
        about = AboutBox(self)
        about.Show(true)

    def OnHelpReload(self,evt):
        self.Debug('OnHelpReload')
        for modulename, module in sys.modules.items():
            if not modulename.startswith('cozer'):
                continue
            if module is None:
                self.Debug('skip reloading %r (module is None)' % (modulename))
            else:
                self.Debug('reloading %r' % (module))
                reload(module)

    def ResetEvent(self):
        self.Debug('ResetEvent')
        self.nb.Destroy()
        self.CreatePages()
        try:
            language = self.eventdata['configure']['language']
        except KeyError:
            language = 'English'
        self.set_language(language)

    def Reshow(self):
        for p in self.nb.pages:
            if hasattr(p,'Reshow'):
                p.Reshow()        

    def OnViewRefresh(self,evt):
        self.Debug('OnRefresh')
        self.Reshow()
        return 1

    def GetClasses(self):
        self.Debug('GetClasses')
        try: classes = map(lambda x:x[1],self.eventdata['classes'])
        except KeyError: classes = []
        ret = []
        for i in range(len(classes)):
            if classes[i]:
                ret.append(classes[i])
        return ret

    def CrackRacePattern(self,pat,cl=''):
        """
        pat = 'NofHeats*(NofLaps*LapLength+..)+..:NofScoredHeats' or 'NofEstimatedLaps*LapLength/Hours' for endurance race
        --> list of lists [[<lap lengths for heat 1>],...], <scored heats>
        or
        --> 2-tuple [[<lap length>]*<nof estimated laps>], <hours>
        """
        self.Debug('CrackRacePattern')
        pat = pat.replace(' ','')
        if '/' in pat:
            ll,hours = pat.split('/')
            nlaps, ll = ll.split('*')
            return [[eval(ll)]*eval(nlaps)], 1, eval(hours)
        apat=string.split(pat,':')
        pat=apat[0]
        apat=apat[1:]
        ret = []
        for s in string.split(markoutercomma(pat,'+'),'@+@'):
            m=string.split(markoutercomma(s,'*'),'@*@')
            if len(m)==1: m=['1',m[0]]
            elif len(m)==2: m=[m[0],m[1]]
            else: m=[m[0],string.join(m[1:],'*')]
            m[1]=string.strip(m[1])
            if m[1][0]=='(' and m[1][-1]==')': m[1]=m[1][1:-1]
            hh=eval(m[0])
            for i in range(hh):
                ret.append([])
                for t in string.split(markoutercomma(m[1],'+'),'@+@'):
                    k=string.split(markoutercomma(t,'*'),'@*@')
                    if len(k)==1: k=['1',k[0]]
                    elif len(k)==2: k=[k[0],k[1]]
                    else: k=[k[0],string.join(k[1:],'*')]
                    ll=eval(k[0])
                    llen=eval(k[1])
                    for j in range(ll):
                        ret[-1].append(llen)
        try: sheats = eval(apat[0])
        except:
            sheats = len(ret)
            if cl: self.Warning('Scored heats for class %s is set %s'%(cl,sheats))
        return ret,sheats

    def GetAllowedHeats(self,cl):
        self.Debug('GetAllowedHeats')
        ret=[]
        rpat=None
        for l in self.eventdata['classes']:
            if l[1] and l[2] and l[1]==cl:
                r = self.CrackRacePattern(l[2])
                if len (r)==2:
                    rpat,sheats=r
                elif len (r)==3:
                    rpat,sheats,duration=r
                break
        if not rpat: return ret
        if isqclass(cl):
            return reduce(lambda x,h:x+[`h`,`h`+'q'],range(1,1+len(rpat)),[])
        elif istclass(cl):
            return reduce(lambda x,h:x+[`h`,`h`+'t'],range(1,1+len(rpat)),[])
        else:
            return reduce(lambda x,h:x+[`h`,`h`+'r', `h`+'R'],range(1,1+len(rpat)),[])
        
    def GetHeats(self,raceid):
        self.Debug('GetHeats')
        nofh={}
        sheats = {}
        allowedheats={}
        tmp={}
        restarts={}
        quals={}
        tims = {}
        for l in self.eventdata['classes']:
            if l[1] and l[2]:
                r = self.CrackRacePattern(l[2])
                nofh[l[1]]=len(r[0])
                if isqclass(l[1]):
                    allowedheats[l[1]]=map(lambda x:`x`+'q',range(1,1+nofh[l[1]]))
                    quals[l[1]]=[]
                elif istclass(l[1]):
                    allowedheats[l[1]]=map(lambda x:`x`+'t',range(1,1+nofh[l[1]]))
                    tims[l[1]]=[]
                else:
                    allowedheats[l[1]]=map(lambda x:`x`,range(1,1+nofh[l[1]]))+\
                                    map(lambda x:`x`+'r',range(1,1+nofh[l[1]]))+\
                                    map(lambda x:`x`+'R',range(1,1+nofh[l[1]]))
                    restarts[l[1]]=[]
                tmp[l[1]]=0
        
        for i in range(min(raceid,len(self.eventdata['races']))):
            for d in self.eventdata['races'][i]:
                if not d[1]: continue
                if nofh.has_key(d[1]):
                    if d[2] in allowedheats[d[1]]:
                        if d[2][-1] not in ['r','q','t','R']:
                            tmp[d[1]]=tmp[d[1]]+1
                            if not `tmp[d[1]]`==d[2]:
                                self.Warning('Expected heat %s but got %s (class=%s).'%(`tmp[d[1]]`,`d[2]`,`d[1]`))
                        elif d[2][-1] in ['r','R']:
                            restarts[d[1]].append(d[2])
                        elif d[2][-1]=='q':
                            tmp[d[1]]=tmp[d[1]]+1
                            quals[d[1]].append(d[2])
                        elif d[2][-1]=='t':
                            tmp[d[1]]=tmp[d[1]]+1
                            tims[d[1]].append(d[2])
                    else:
                        self.Warning('Heat %s is not allowed for class %s.'%(`d[2]`,`d[1]`))
        ret={}
        for k in tmp.keys():
            if isqclass(k):
                if tmp[k]<nofh[k]:
                    ret[k]=[`tmp[k]+1`+'q']
                else:
                    ret[k]=[`tmp[k]`+'q']
                if ret[k][-1] in quals[k]: del ret[k][-1]
            elif istclass(k):
                if tmp[k]<nofh[k]:
                    ret[k]=[`tmp[k]+1`+'t']
                else:
                    ret[k]=[`tmp[k]`+'t']
                if ret[k][-1] in tims[k]: del ret[k][-1]
            else:
                if 1<=tmp[k]<nofh[k]:
                    ret[k]=[`tmp[k]+1`,`tmp[k]`+'r',`tmp[k]`+'R']
                elif tmp[k]==0:
                    ret[k]=[`1`]
                else:
                    ret[k]=[`tmp[k]`+'r']
                if ret[k][-1] in restarts[k]:
                    # TODO: fix 2nd restart case
                    del ret[k][-1]
        return ret


def get_template():
    return os.path.abspath(os.path.join(__path__[0],'data','template.coz'))


class MyApp(wx.App):
    def OnInit(self):
        fn = 'Untitled'
        if len(sys.argv)>1:
            fn = sys.argv[1]
        if string.lower(fn[-4:]) != '.coz':
            fn = fn + '.coz'
        if not os.path.exists(fn):
            tmpl = get_template()
            Message('Copying %s to %s'%(tmpl,fn))
            shutil.copyfile(tmpl,fn)
        if os.path.isfile(fn):
            frame = MainFrame(debug=0,fn=fn)
        else:
            frame = MainFrame(debug=0)
        frame.Show(True)
        self.SetTopWindow(frame)
        wx.Yield()
        return True

def runcozer():
    if os.name == 'nt':
        if string.lower(os.path.basename(sys.executable))=='pythonw.exe':
            prefs.console_output = 0
            sys.stdout.write('Disabled console output')
    app = MyApp(0)
    app.MainLoop()
