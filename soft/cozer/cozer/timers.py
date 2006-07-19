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

import time,math
from prefs import *
from buildmenus import *
from analyzer import res2str,getresorder


def calclayout(ids):
    ret = [[]]
    bydec = {}
    for i in ids:
        try: di=(int(i)/10)*10
        except:
            try: di=('%s'%i)[0]
            except: di=''
        if not bydec.has_key(di): bydec[di]=[]
        bydec[di].append(i)
    bdkeys = bydec.keys()
    bdkeys.sort()
    n = max(3,int(math.ceil(math.sqrt(len(ids)))))
    m = max(map(lambda k,b=bydec:len(b[k]),bdkeys))
    for k in bdkeys:
        if len(ret[-1])+len(bydec[k])<n:
            ret[-1]=ret[-1]+bydec[k]
        elif not ret[-1]:
            ret[-1]=ret[-1]+bydec[k][:n]
            if bydec[k][n:]:
                ret.append(bydec[k][n:])
        else:
            ret.append(bydec[k][:n])
            if bydec[k][n:]:
                ret.append(bydec[k][n:])
    return ret


class TimerWin1(wxScrolledWindow,MyDebug):
    timerbuts = None
    finished = {}
    clicks = {}
    allowclicks = {}

    def __init__(self,info,race,topparent,parent,debug):
        MyDebug.__init__(self,debug)
        wxScrolledWindow.__init__(self, parent, -1, wxPoint(0, 0),style=wxSUNKEN_BORDER)
        self.race = race
        self.info = info


        self.topparent = topparent
        self.parent = parent

        gs = self.makeGrid1()
        self.SetAutoLayout(true)
        self.SetSizer(gs)
        self.SetScrollbars(20, 20, 50, 50)

    def CleanUp(self):
        self.Debug('CleanUp')
        if self.timerbuts: 
            for k in self.timerbuts.keys():
                for tb in self.timerbuts[k]:
                    tb.Stop()
                del self.timerbuts[k]

    def makeGrid1(self):
        self.Debug('makeGrid1')
        bsize = getopt(self,'id_but_size',40)
        btsize = getopt(self,'id_but_textsize',14)
        gs=wxBoxSizer(wxHORIZONTAL)
        #gs=wxBoxSizer(wxVERTICAL)
        
        #record = topparent.eventdata['record']
        self.idmap={}
        self.invidmap={}
        i = -1
        self.buts = []
        self.lapbuts = {}
        self.timerbuts = {}
        for cl,h,r in self.race:
            i = i + 1
            lapl = self.info[i]['course']
            self.allowclicks[i] = 0
            s = wxBoxSizer(wxVERTICAL)
            s.Add(wxStaticText(self,-1,'%s heat %s'%(cl,h)))
            
            rk2 = r.keys()
            rk2.sort()
            try: rk = self.topparent.eventdata['prevorder'][cl]
            except:
                rk = r.keys()
                rk.sort()
            rkok = len(rk) == len(rk2)
            for k in rk:
                if not rkok: break
                if k not in rk2: rkok = 0; break
            if not rkok: rk = rk2
            sh=wxBoxSizer(wxHORIZONTAL)
            s.Add(sh)
            s1=wxBoxSizer(wxVERTICAL)
            s2=wxBoxSizer(wxVERTICAL)
            sh.Add(s1,0,wxEXPAND)
            sh.Add(s2)

            for row in calclayout(rk2):
                rs = wxBoxSizer(wxHORIZONTAL)
                s2.Add(rs,0)
                for k in row:
                    id=wxNewId()
                    but = wxButton(self,id,str(k),size=wxSize(bsize,bsize))
                    but.SetFont(wxFont(btsize, wxSWISS, wxNORMAL, wxNORMAL))
                    but.Connect(id,id,wxEVT_COMMAND_RIGHT_CLICK,EVT_RIGHT_DOWN)
                    EVT_BUTTON(self,id,self.OnClick)
                    EVT_RIGHT_DOWN(but,lambda evt,self=self,id=id,but=but:self.OnButtonRightDown(evt,id,but))
                    rs.Add(but,0,wxALIGN_LEFT|wxALIGN_TOP)
                    self.idmap[id]=i,k
                    self.invidmap[i,k]=id
                    self.buts.append(but)


            butparent = wxPanel(self,-1,size=wxSize(100,20*(len(rk)+len(lapl)+2)))
            s1.Add(butparent,0,wxALIGN_LEFT|wxALIGN_TOP|wxEXPAND)
            self.lapbuts[i]=[]

            id = wxNewId()
            but = wxButton(butparent,id,'Ready to Start',size=wxSize(-1,20),pos=wxPoint(0,0))
            but.SetBackgroundColour(mycolors['readymark'])
            #s1.Add(but,0,wxALIGN_LEFT|wxALIGN_TOP)
            self.lapbuts[i].append(but)
            ypos = 20
            for k in rk:
                id = self.invidmap[i,k]
                but = wxButton(butparent,id,str(k),size=wxSize(-1,20),pos=wxPoint(0,ypos))
                ypos = ypos + 20
                but.SetFont(wxFont(12, wxSWISS, wxNORMAL, wxBOLD))
                #s1.Add(but,0,wxALIGN_LEFT|wxALIGN_TOP)
                self.lapbuts[i].append(but)
            for l in range(len(lapl)-1):
                id = wxNewId()
                but = wxButton(butparent,id,'Lap %s'%(l+1),size=wxSize(-1,20),pos=wxPoint(0,ypos))
                ypos = ypos + 20
                but.SetBackgroundColour(mycolors['lapmark'])
                #s1.Add(but,0,wxALIGN_LEFT|wxALIGN_TOP)
                self.lapbuts[i].append(but)
            id = wxNewId()
            but = wxButton(butparent,id,'Finish',size=wxSize(-1,20),pos=wxPoint(0,ypos))
            but.SetBackgroundColour(mycolors['finishmark_bg'])
            but.SetForegroundColour(mycolors['finishmark_fg'])
            #s1.Add(but,0,wxALIGN_LEFT|wxALIGN_TOP)
            self.lapbuts[i].append(but)
            
            gs.Add(s,0,wxALIGN_LEFT|wxALIGN_TOP)
            pros = lambda f=self.EmulateClicks,a1=i,a2=r:f(a1,a2)
            pros()
            #PutSleep(pros,1,self.debug+(not not self.debug))
        return gs

    def EmulateClicks(self,ri,race):
        self.Debug('EmulateClicks')
        sarr = []
        stime = -1
        if self.info[ri].has_key('racetime'):
            stime = self.info[ri]['racetime']
        for k in race.keys():
            if not race[k]: continue
            tms = gettimes(race[k],stime)
            t0 = 0
            for t in tms:
                t0 = t0 + t
                sarr.append([t0,k])
        sarr.sort()
        ids = map(lambda tk,m=self.invidmap,i=ri:m[i,tk[1]],sarr)
        self.finished[ri] = []
        self.clicks[ri] = []
        map(self.ApplyClick,ids)

    def OnButtonRightDown(self,evt,id,but):
        self.Debug('OnButtonRightDown')
        i,k=self.idmap[id]
        menu = TimerButtonMenu(self,id,self.debug+(not not self.debug))
        bpos = but.GetPositionTuple()
        epos = evt.GetPositionTuple()
        self.PopupMenu(menu,wxPoint(bpos[0]+epos[0],bpos[1]+epos[1]))
        menu.Destroy()

    def OnClick(self,evt):
        self.Debug('OnClick')
        ID = evt.GetId()
        i,k=self.idmap[ID]
        cl,h,rec=self.race[i]
        if istclass(cl):
            if not hasattr(self,'inittimes'): self.inittimes = {}
            if not self.inittimes.has_key(i): self.inittimes[i] = {}
            if not self.inittimes[i].has_key(k):
                self.inittimes[i][k] = time.time()
                self.ApplyClickTT(ID,mycolors['waiting'])
            else:
                tt = time.time()
                t = tt - self.inittimes[i][k]
                self.race[i][2][k].append((1,round(t,roundopt)))
                self.ApplyClickTT(ID,mycolors['finish'])
                self.inittimes[i][k] = tt
        else:
            if not self.allowclicks[i]:
                self.Warning('Click ignored for %s. Press Start button to start the race.'%(`k`))
                return
            ot = reduce(lambda x,y:x+y,gettimes(self.race[i][2][k]),0)
            t = time.time() - self.info[i]['starttime']
            self.race[i][2][k].append((1,round(t-ot,roundopt)))
            self.ApplyClick(ID,0)

    def ApplyClickTT(self,id,color):
        self.Debug('ApplyClickTT')
        i,k=self.idmap[id]
        ids_buts=map(lambda b:b.GetId(),self.buts)
        self.buts[ids_buts.index(id)].SetBackgroundColour(color)

    def ApplyClick(self,id,skiptoggle=1):
        self.Debug('ApplyClick')
        i,k=self.idmap[id]
        self.clicks[i].append(k)
        flag = not (k in self.finished[i])
        if self.finished[i] or len(self.info[i]['course']) == self.clicks[i].count(k):
            self.finished[i].append(k)
        if self.timerbuts.has_key(id):
            for tb in self.timerbuts[id]:
                tb.Stop()
            del self.timerbuts[id]
        ids=map(lambda b:b.GetId(),self.lapbuts[i])
        ids_buts=map(lambda b:b.GetId(),self.buts)
        if flag:
            j1 = ids.index(id)
            j2 = -1
            fl = 0
            for j in ids[j1+1:]:
                if not self.idmap.has_key(j):
                    j2 = ids.index(j)
                    if fl:
                        j2 = j2 - 1
                        fl = 0
                        break
                    else: fl = 1
            if fl:
                j2 = len(ids) - 1
            for j in range(j1,j2):
                b1 = self.lapbuts[i][j]
                b2 = self.lapbuts[i][j+1]
                pos1 = b1.GetPosition()
                pos2 = b2.GetPosition()
                b1.SetPosition(pos2)
                b2.SetPosition(pos1)
                self.lapbuts[i][j] = b2
                self.lapbuts[i][j+1] = b1
        if flag and k in self.finished[i]:
            self.lapbuts[i][j2].SetBackgroundColour(mycolors['finish'])
            self.buts[ids_buts.index(id)].SetBackgroundColour(mycolors['finish'])
            return
        if k in self.finished[i]:
            return
        if skiptoggle: return
        if self.info[i].has_key('racetime'):
            stime = self.info[i]['racetime']
        else: stime = -1
        tms = gettimes(self.race[i][2][k],stime)
        ll = min(len(tms),len(self.info[i]['course'])-1)
        if 0<ll:
            lastlapspeed = self.info[i]['course'][ll-1]/tms[-1]
            et = max(self.info[i]['course'][ll]/lastlapspeed - 5,10)
            self.timerbuts[id] = [ToggleButtonTimer(self.lapbuts[i][j2],et,self.debug+(not not self.debug)),
                                  ToggleButtonTimer(self.buts[ids_buts.index(id)],et,self.debug+(not not self.debug))]


class ToggleButtonTimer(wxTimer,MyDebug):

    def __init__(self,but,tm,debug):
        MyDebug.__init__(self,debug)
        wxTimer.__init__(self)
        self.tm = tm
        self.Start(tm*1000,oneShot=true)
        self.but = but
        self.but.SetBackgroundColour(mycolors['waiting'])

    def Notify(self):
        self.Debug('Notify')
        if self.tm:
            wxBell()
            self.but.SetBackgroundColour(mycolors['coming'])
            self.Start(0.4*self.tm*1000,oneShot=true)
            self.tm = 0
        else:
            self.but.SetBackgroundColour(mycolors['late'])


class TimerButtonMenu(wxMenu,MyDebug):

    def __init__(self,parent,id,debug):
        MyDebug.__init__(self,debug)
        wxMenu.__init__(self,"")
        ri,k=parent.idmap[id]
        cl,heat,racedata = parent.race[ri]
        self.race=racedata[k]
        self.parent = parent
        #print k,self.race
        enableonoff = []
        i = -1
        for r in self.race:
            i = i + 1
            if r[0]>0: do = 'off'
            else: do = 'on'
            if len(r)==2: val = '%s'%r[1]
            elif len(r)==3: val = '%s:%s'%(r[1],r[2])
            enableonoff.append(('Item%s'%i,{'menu':'Set %s %s'%(val,do)}))
            exec 'self.OnEnableOnOffItem%s = lambda evt,i=%s,self=self:self.OnEnableOnOff(evt,i)'%(i,i)
        timerbutmenu = [('EnableOnOff',{'menu':'%s'%k,
                                        'submenu':enableonoff,
                                        })]
        if istclass(cl):
            exec 'self.OnResetTime = lambda evt,ri=ri,k=k,self=self:self.OnResetTimeApply(evt,ri,k)'
            timerbutmenu.append('ResetTime',{'menu':'Reset'})
        buildmenus(self,timerbutmenu,self,verbose = debug)

    def OnResetTimeApply(self,evt,ri,k):
        self.Debug('OnResetTimeApply')
        sp = self.parent
        if hasattr(sp,'inittimes') and sp.inittimes.has_key(ri) and sp.inittimes[ri].has_key(k):
            del self.parent.inittimes[ri][k]

    def OnEnableOnOff(self,evt,i):
        self.Debug('OnEnableOnOff')
        if len(self.race[i]) == 2:
            self.race[i] = (-self.race[i][0],self.race[i][1])
        elif len(self.race[i]) == 2:
            self.race[i] = (-self.race[i][0],self.race[i][1],self.race[i][2])
        else:
            self.Warning('Confused: i=%s race[i]=%s'%(i,`self.racep[i]`))


class EditWin1(wxScrolledWindow,MyDebug):
    width = 600
    startx = 30
    mousegrab = 0
    editysize = 40

    def __init__(self,info,rec,res,topparent,parent,debug):
        MyDebug.__init__(self,debug)
        wxScrolledWindow.__init__(self, parent, -1, wxPoint(0, 0),style=wxSUNKEN_BORDER)
        self.info = info
        self.rec = rec
        self.res = res
        self.topparent = topparent
        self.parent = parent
        self.SetScrollbars(20, 20, 50, 50)
        self.calcMaxTime()
        if not self.info.has_key('racetime'):
            self.info['racetime'] = self.maxtime/1.03
        self.SetCurTime(self.info['racetime'])

        self.VisualizeRecords()

        EVT_PAINT(self, self.OnPaint)
        EVT_LEFT_DOWN(self, self.OnLeftButtonEvent)
        EVT_LEFT_UP(self,   self.OnLeftButtonEvent)
        EVT_MOTION(self,    self.OnLeftButtonEvent)
        if self.info.has_key('starttime'):
            self.parent.starttimetext.SetLabel(' Start time = %s'%(time.ctime(self.info['starttime'])))

    def VisualizeRecords(self):
        self.Debug('VisualizeRecords')
        rks = getresorder(self.res)
        ypos = 50
        sttime = 0
        self.rec_eds = []
        for k in rks:
            header = 'Id = %s: %s'%(k,res2str(self.res[k]))
            self.rec_eds.append(\
                RecordEditor(k,header,self,self.debug+(not not self.debug),
                             pos=wxPoint(self.startx,ypos),
                             size=wxSize(self.width,self.editysize)))
            ypos = ypos + self.editysize + 5
        self.timelineheight = ypos + 25

    def OnPaint(self,evt):
        self.Debug1('OnPaint')
        val = self.curtime/float(self.maxtime)
        hpos = self.startx+val*self.width
        self.DrawTimeLine(hpos,evt is None)

    def DrawTimeLine(self,hpos,clientdc=0):
        self.Debug1('DrawTimeLine')
        if clientdc:
            dc = wxClientDC(self)
        else:
            dc = wxPaintDC(self)
        dc.Clear()
        self.PrepareDC(dc)
        dc.BeginDrawing()
        dc.SetPen(wxPen(mycolors['timeline'],width=5))
        dc.DrawLine(hpos, 0, hpos, self.timelineheight)
        dc.DrawText(' Race stopped',hpos, 20)
        dc.DrawText(' Race stopped',hpos, self.timelineheight - 10)
        dc.EndDrawing()

    def calcMaxTime(self):
        self.Debug('calcMaxTime')
        mxt = 0
        for k in self.rec.keys():
            t = 0
            for r in self.rec[k]:
                if not r: continue
                if abs(r[0]) in [1,2]: t = t + r[1]
                else: mxt = max(mxt,r[1])
            mxt = max(mxt,t)
        self.maxtime = 1 + mxt * 1.05

    def OnLeftButtonEvent(self,evt):
        self.Debug1('OnLeftButtonEvent')
        vs=self.GetViewStart()
        sp=self.GetScrollPixelsPerUnit()
        xs,ys = vs[0]*sp[0]+evt.GetX(),vs[1]*sp[1]+evt.GetY()
        if evt.LeftDown():
            val = self.curtime/float(self.maxtime)
            if abs(xs - self.startx - val*self.width) < 5:
                self.mousegrab = 1
        elif evt.Dragging():
            if self.mousegrab:
                tm = max(0,self.maxtime*(xs-self.startx)/float(self.width))
                if (tm>60 and int(tm) - int(self.curtime)) or tm<=60:
                    self.SetCurTime(tm)                    
                    self.OnPaint(None)
                    map(lambda r:r.OnPaint(None),self.rec_eds)
        elif evt.LeftUp():
            self.mousegrab = 0

    def SetCurTime(self,tm):
        self.Debug1('SetCurTime')
        self.curtime = round(tm,roundopt)
        mns = int(self.curtime/60)
        secs = self.curtime - 60*mns
        self.parent.timetext.SetLabel(' Race time = %.2d:%2.2f (%0.2f secs)'%(mns,secs,self.curtime))
        self.info['racetime'] = self.curtime


class RecordEditor(wxPanel,MyDebug):
    yline = 20

    def __init__(self,no,header,parent,debug,pos,size):
        MyDebug.__init__(self,debug)
        wxPanel.__init__(self,parent,wxNewId(),pos=pos,size=size)
        self.parent = parent
        self.rec = parent.rec[no]
        self.header = header
        self.Prepare4Paint()
        EVT_PAINT(self, self.OnPaint)
        EVT_RIGHT_DOWN(self, self.OnRightButtonEvent)

    def Prepare4Paint(self):
        self.Debug('Prepare4Paint')
        self.paint = {}

        pens = {}
        pens[0] = wxPen(wxBLACK)
        pens[1] = wxPen(wxNamedColour('BLUE'),width=10)
        pens[2] = wxPen(mycolors['lapmark'],width=5)
        pens[3] = wxPen(mycolors['lapmark_ins'],width=5)
        pens[4] = wxPen(mycolors['lapmark_disable'],width=5)
        pens[5] = wxPen(mycolors['penlap_mark'],width=5)
        pens[6] = wxPen(mycolors['disq_mark'],width=5)
        pens[7] = wxPen(mycolors['interruption_mark'],width=5)
        for k in reccodemap.keys():
            pens[k] = wxPen(reccodecolours[k],width=5)
        self.paint['pens'] = pens

        lines = []
        rectangles = []
        texts = []
        texts.append((0,(self.header,0,self.yline-20)))
        etime = 0
        dtime = 0
        coef = self.parent.width/float(self.parent.maxtime)
        self.coef = coef
        sz = 5
        for i in range(len(self.rec)):
            if self.rec[i][0] in [1,2,-1,-2]:
                t = self.rec[i][1]
                etime = etime + t
                if self.rec[i][0] == 1:
                    texts.append((0,('%s'%(t+dtime),coef*etime,self.yline+5)))
                    rectangles.append((2,(coef*etime-sz/2,self.yline-sz/2,sz,sz)))
                    dtime = 0
                elif self.rec[i][0] == 2:
                    texts.append((0,('%s'%(t+dtime),coef*etime,self.yline+5)))
                    rectangles.append((3,(coef*etime-sz/2,self.yline-sz/2,sz,sz)))
                    dtime = 0
                else:
                    rectangles.append((4,(coef*etime-sz/2,self.yline-sz/2,sz,sz)))
                    dtime = dtime + t
            else:
                t = self.rec[i][1]
                c = invreccodemap[abs(self.rec[i][0])]
                if self.rec[i][0]>0:
                    texts.append((0,('%s'%(c),coef*t-5,self.yline-10)))
                    texts.append((0,('%s'%(self.rec[i][2]),coef*t,self.yline+5)))
                    rectangles.append((c,(coef*t-sz/2,self.yline-sz/2,sz,sz)))
                else:
                    rectangles.append((4,(coef*t-sz/2,self.yline-sz/2,sz,sz)))

        lines.append((1,(0,self.yline,coef*etime,self.yline)))

        self.paint['lines'] = lines
        self.paint['rectangles'] = rectangles
        self.paint['texts'] = texts

    def OnPaint(self,evt):
        self.Debug1('OnPaint')
        if evt is None:
            dc = wxClientDC(self)
        else:
            dc = wxPaintDC(self)
        dc.Clear()
        dc.BeginDrawing()
        
        for l in self.paint['lines']:
            dc.SetPen(self.paint['pens'][l[0]])
            exec 'dc.DrawLine%s'%(`l[1]`)
        for l in self.paint['rectangles']:
            dc.SetPen(self.paint['pens'][l[0]])
            exec 'dc.DrawRectangle%s'%(`l[1]`)
        for l in self.paint['texts']:
            dc.SetPen(self.paint['pens'][l[0]])
            exec 'dc.DrawText%s'%(`l[1]`)

        dc.EndDrawing()

    def OnRightButtonEvent(self,evt):
        global _tmpREmenuflag
        self.Debug('OnRightButtonEvent')
        if evt.RightDown():
            xp,yp=evt.GetPositionTuple()
            if abs(yp - self.yline)<5:
                ct = round(xp/self.coef,roundopt)
                menu = RecordEditorMenu(self,ct,self.debug+(not not self.debug))
                self.PopupMenu(menu,wxPoint(xp,yp))
                menu.Destroy()
                i = _tmpREmenuflag[0]
                if i>=0:
                    r = self.parent.topparent.eventdata['rules'][i]
                    insertmark(self.rec,reccodemap[r[1]],ct,r[2])
                    self.Prepare4Paint()
                    self.OnPaint(None)
                self.Debug(self.rec)

_recordeditormenu = [
    ('Insert',{'menu':'Insert Mark'}),
    ('Enable',{'menu':'Enable On/Off'}),
    ('Delete',{'menu':'Delete'}),
    ]

_tmpREmenuflag = [-1]


class RecordEditorMenu(wxMenu,MyDebug):
    def __init__(self,parent,ct,debug):
        MyDebug.__init__(self,debug)
        wxMenu.__init__(self,"")
        self.parent = parent
        self.ct = ct
        _tmpREmenuflag[0] = -1
        rulesmenu = []
        if parent.parent.topparent.eventdata.has_key('rules'):
            menul = {}
            i = -1
            for r in parent.parent.topparent.eventdata['rules']:
                i = i + 1
                for k in reccodemap.keys():
                    if k == r[1]:
                        if not menul.has_key(k): menul[k] = []
                        menul[k].append(('REMpopup%s'%i,{'menu':r[3]}))
                        exec """\
def tmpfun(evt):
    global _tmpREmenuflag
    _tmpREmenuflag[0] = %s
self.On%s = tmpfun
"""%(i,'%sREMpopup%s'%(r[1],i))
                        break
            for k in menul.keys():
                rulesmenu.append((k,{'menu':reccodemenulabel[k],'submenu':menul[k]}))

        buildmenus(self,rulesmenu+_recordeditormenu,self,verbose = debug)

    def OnInsert(self,evt):
        self.Debug('OnInsert')
        et = 0
        pi,ii = -1,-1
        rec = self.parent.rec
        for i in range(len(rec)):
            if abs(rec[i][0]) in [1,2]:
                if ii<0:
                    et = et + rec[i][1]
                    if et > self.ct: ii = i; break
                    else: pi = i
        if ii>=0:
            if pi>=0: pt = rec[pi][1]
            else: pt = 0
            ct = rec[ii][1] - (et - self.ct)
            rec[ii] = (rec[ii][0],rec[ii][1] - ct)
            rec.insert(ii,(2,ct))
        else:
            ct = self.ct - et
            rec.append((2,ct))
        self.parent.Prepare4Paint()
        self.parent.OnPaint(None)

    def OnEnable(self,evt):
        self.Debug('OnEnable')
        et,ii = 0,-1
        rec = self.parent.rec
        for i in range(len(rec)):
            if abs(rec[i][0]) in [1,2]:
                et = et + rec[i][1]
                if abs(self.ct - et)*self.parent.coef < 5:
                    ii = i
                    break
            else:
                if abs(self.ct - rec[i][1])*self.parent.coef < 5:
                    ii = i
                    break
        if ii>=0:
            if len(rec[ii])==2:
                rec[ii] = (-rec[ii][0],rec[ii][1])
            elif len(rec[ii])==3:
                rec[ii] = (-rec[ii][0],rec[ii][1],rec[ii][2])
            self.parent.Prepare4Paint()
            self.parent.OnPaint(None)

    def OnDelete(self,evt):
        self.Debug('OnDelete')
        et,ii = 0,-1
        rec = self.parent.rec
        for i in range(len(rec)):
            if abs(rec[i][0]) in [1,2]:
                et = et + rec[i][1]
                if abs(self.ct - et)*self.parent.coef < 5:
                    if abs(rec[i][0])==2:
                        ii = i
                        break
                    else:
                        self.Warning('Skipping code 1 record for deletion. Use enable on/off.')
            else:
                if abs(self.ct - rec[i][1])*self.parent.coef < 5:
                    del rec[i]
                    self.parent.Prepare4Paint()
                    self.parent.OnPaint(None)
                    return
        ni = -1
        for i in range(ii+1,len(rec)):
            if abs(rec[i][0]) in [1,2]:
                ni = i
                break
        if ii>=0:
            if abs(rec[ii][0]) == 1:
                self.Warning('Deleting records saved during the timing is not allowed.\nUse enable on/off command instead.')
                return
            if ni>=0:
                rec[ni] = (rec[ni][0],rec[ni][1]+rec[ii][1])
            del rec[ii]
            self.parent.Prepare4Paint()
            self.parent.OnPaint(None)
