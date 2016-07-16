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

__version__ = "$Revision: 1.3 $"[10:-1]

import wx
try:
    from wx import USE_UNICODE
except ImportError:
    USE_UNICODE = 0
if USE_UNICODE:
    print 'Using unicode'
import sys,string,math,pprint,os,types,time,atexit
import Queue,threading

#XXX: find a way to establish this path automatically
gsview_exe = r'"c:\Program Files\Ghostgum\gsview\gsview32.exe"'

acrord_exe = r'AcroRd32.exe'
if os.name=='nt':
    import os, glob
    acrord_exe = (glob.glob (r'C:\Program Files\Adobe\*\Reader\AcroRd32.exe') or [acrord_exe])[0]
    os.environ['PATH'] += os.pathsep + os.path.dirname (acrord_exe)
    acrord_exe = os.path.basename(acrord_exe)

false = False
true = True

_log_queue = Queue.Queue(0)
if not os.path.isdir('log'):
    os.mkdir('log')
_log_file = open(time.strftime(os.path.join('log','%y%b%d_%H%M%S.log'),
                               time.localtime()),'w')
atexit.register(_log_file.close)

def put_log(mess):
    _log_queue.put_nowait(mess)

def empty_log():
    """It should be called only in one place"""
    while 1:
        try:
            mess = _log_queue.get_nowait()
        except Queue.Empty:
            break
        wx.LogMessage(mess)

console_output = 1

class MyStdIO:
    def __init__(self,rawio):
        self.rawio = rawio
        try:
            self.name = rawio.name[1:-1] + ':'
        except:
            self.name = ''
    def __getattr__(self,name):
        return getattr(self.rawio,name)
    def write(self,mess):
        global console_output
        mess = self.name + string.rstrip(mess)
        if console_output:
            self.rawio.write(mess+'\n')
            self.rawio.flush()
        _log_file.write(mess+'\n')
        _log_file.flush()
        put_log(mess)

sys.stderr = MyStdIO(sys.stderr)
sys.stdout = MyStdIO(sys.stdout)

show = pprint.pprint

debuglevel = 0 # 1
debugdetaillevel = 0

top_parent = None

edit_bg = wx.Colour(200,200,150)
warning_bg = wx.Colour(150,200,150)
disableedit_bg = wx.Colour(250,200,150)
wxYELLOW = wx.Colour(250,250,100)
grid_ln = wx.Colour(0,0,0)

roundopt = 2

mycolors = {'finish':wx.Colour(255,0,255),
            'coming':wx.GREEN,
            'late':wx.Colour(150,150,240),
            'waiting':wx.WHITE,
            'waiting0':wx.Colour(250,250,250),
            'waiting1':wx.Colour(200,200,200),
            'ignore':wx.Colour(240, 50, 50),
            'lapmark':wx.Colour(255,127,0),
            'lapmark_ins':wx.Colour(127,255,0),
            'finishmark_bg':wx.BLACK,
            'finishmark_fg':wx.WHITE,
            'readymark':wx.Colour(0,255,127),
            'timeline':wx.RED,
            'selectline':wx.GREEN,
            'lapmark_disable':wx.Colour(127,127,0),
            'penlap_mark':wx.Colour(255,255,0),
            'disq_mark':wx.RED,
            'redcard_mark':wx.RED,
            'yellowcard_mark':wxYELLOW,
            'interruption_mark':wx.BLACK,
            }

reccodemap = {'LL':3,'PL':4,'LL2':6,
              'PL5':5,'PL8':8,'PL10':9,
              'DS':10,'IR':11,'DQ':12,'YC':13,'RC':14,
              'NT':20,'Q':30,'NQ':31}
invreccodemap = {}
for k in reccodemap.keys():
    invreccodemap[reccodemap[k]] = k
reccodemenulabel = {'LL':'Lost a lap',
                    'LL2':'Lost two laps',
                    'PL':'Penalty lap',
                    'PL5':'5 penalty laps',
                    'PL8':'8 penalty laps',
                    'PL10':'10 penalty laps',
                    'DS':"Didn't start",
                    'IR':'Interruption',
                    'DQ':'Disqualif.',
                    'NT':'Note',
                    'Q':'Qualified',
                    'NQ':'Not qualified',
                    'YC':'Yellow Card',
                    'RC':'Red Card',
                    }
reccodelatexlabel = {'LL':r'\Lostalap',
                     'LL2':r'\LostTwoLaps',
                     'PL':r'\Penaltylap',
                     'PL5':r'\FivePenaltylaps',
                     'PL8':r'\EightPenaltylaps',
                     'PL10':r'\TenPenaltylaps',
                     'DS':r'\Didntstart',
                     'IR':r'\Interruption',
                     'DQ':r'\Disqualif',
                     'YC':r'\YellowCard',
                     'RC':r'\RedCard',
                     'NT':r'\Note',
                     'Q':r'\Qualified',
                     'NQ':r'\Notqualified',
                    }
reccodecolours = {'LL':wx.Colour(255,255,0),
                  'LL2':wx.Colour(255,255,0),
                  'PL':wx.Colour(255,255,127),
                  'PL5':wx.Colour(255,255,127),
                  'PL8':wx.Colour(255,255,127),
                  'PL10':wx.Colour(255,255,127),
                  'DS':wx.Colour(192,192,192),
                  'IR':wx.BLACK,
                  'DQ':wx.RED,
                  'RC':wx.RED,
                  'YC':wxYELLOW,
                  'NT':wx.Colour(159,159,95),
                  'Q':wx.Colour(0,255,0),
                  'NQ':wx.Colour(255,0,255),
                  }

def isqclass(cl):
    if cl[-2:] in ['/Q',r'\Q','/q',r'\q']: return 1
    return 0

def istclass(cl):
    if cl[-2:] in ['/T',r'\T','/t',r'\t']: return 1
    return 0

def gettclass(cl):
    if cl[-2:] in ['/T',r'\T','/t',r'\t']: return cl[:-2]
    return cl

def getqclass(cl):
    if cl[-2:] in ['/Q',r'\Q','/q',r'\q']: return cl[:-2]
    return cl

def getclass(cl):
    if isqclass(cl) or istclass(cl): return cl[:-2]
    return cl

def insertmark(rec,code,ct,mess=''):
    t = 0
    j = 0
    for j in range(len(rec)):
        if rec[j][0] in [1,2,-1,-2]:
            t = t + rec[j][1]
            if ct<t: break
        else:
            if ct<rec[j][1]:
                t = rec[j][1]
                break
    if ct<t:
        rec.insert(j,(code,ct,mess))
    else:
        rec.append((code,ct,mess))

nthmap={1:'st',2:'nd',3:'rd'}
for i in [0,11,12,13]: nthmap[i]='th'

def _nth(n):
    n = abs(int(n))
    if nthmap.has_key(n): return nthmap[n]
    nl = 10**int(math.log10(n))
    if n> nl: return _nth(n-int(n/nl)*nl)
    else: return nthmap[0]

def nth(n):
    return `n`+_nth(n)

def checkempty(obj):
    if not obj: return 1
    if type(obj)==type([]):
        for l in obj:
            if not checkempty(l): return 0
        return 1
    elif type(obj)==type({}):
        for k in obj.keys():
            if not checkempty(obj[k]): return 0
        return 1
    return 0


class MyDebug:

    def __init__(self,debug = 10):
        self.debug = debug
        self.Debug('init')

    def Debug(self,*mess):
        if 0 < self.debug <= debuglevel:
            n = str(self.__class__)
            if n[:8] == '__main__':
                n = n[8:]
            text = '%s%s:%s\n'%('  '*self.debug,n,string.join(map(str,list(mess)),' '))
            sys.stderr.write(text)

    def Debug1(self,*mess):
        if debugdetaillevel >= 1:
            exec 'self.Debug'+`mess`

    def Debug2(self,*mess):
        if debugdetaillevel >= 2:
            exec 'self.Debug'+`mess`

    def Debug3(self,*mess):
        if debugdetaillevel >= 3:
            exec 'self.Debug'+`mess`

    def Warning(self,*mess):
        n = str(self.__class__)
        if n[:8] == '__main__':
            n = n[8:]
        sys.stderr.write('WARNING:%s\n'%(string.join(map(str,list(mess)),' ')))
        wx.Bell()
    
    def Message(self,*mess):
        n = str(self.__class__)
        if n[:8] == '__main__':
            n = n[8:]
        mess = string.join(map(str,list(mess)),' ')
        sys.stdout.write('Message:%s\n'%(mess))
        wx.Bell()
            
    def Info(self,*mess):
        n = str(self.__class__)
        if n[:8] == '__main__': n = n[8:]
        mess = string.join(map(str,list(mess)),' ')
        sys.stdout.write('Info:%s\n'%(mess))
        self.topparent.statusbar.SetStatusText(mess,0)
        wx.Bell()

class PutSleep(wx.Timer,MyDebug):

    def __init__(self,pros,tm,debug):
        MyDebug.__init__(self,debug)
        wx.Timer.__init__(self)
        self.pros = pros
        self.Start(tm*1000,oneShot=true)

    def Notify(self):
        self.Debug('Notify')
        wx.Bell()
        self.pros()

def markoutercomma(line,comma=','):
    l='';f=0
    for c in line:
        if c=='(':f=f+1
        elif c==')':f=f-1
        elif c==comma and f==0: l=l+'@'+comma+'@'; continue
        l=l+c
    return l

def markouterparen(line):
    l='';f=0
    for c in line:
        if c=='(':
            f=f+1
            if f==1: l=l+'@(@'; continue
        elif c==')':
            f=f-1
            if f==0: l=l+'@)@'; continue
        l=l+c
    return l

def setopt(self,name,val):
    if not self.topparent.eventdata.has_key('configure'):
        self.topparent.eventdata['configure'] = {}
    self.topparent.eventdata['configure'][name] = val

def getopt(self,name,default):
    try:
        return self.topparent.eventdata['configure'][name]
    except:
        setopt(self,name,default)
        return default    

def flatlist(l):
    if type(l)==types.ListType:
        return reduce(lambda x,y,f=flatlist:x+f(y),l,[])
    return [l]

def replace(str,dict,defaultsep=''):
    if type(dict)==type([]):
        return map(lambda d,f=replace,sep=defaultsep,s=str:f(s,d,sep),dict)
    for k in 2*dict.keys():
        if k=='separatorsfor': continue
        if dict.has_key('separatorsfor') and dict['separatorsfor'].has_key(k):
            sep=dict['separatorsfor'][k]
        else:
            sep=defaultsep
        if type(dict[k])==type([]):
            str=string.replace(str,'#%s#'%(k),string.join(flatlist(dict[k]),sep))
        else:
            str=string.replace(str,'#%s#'%(k),dict[k])
    return str

def dictappend(rd,ar):
    if type(ar)==types.ListType:
        for a in ar: rd=dictappend(rd,a)
        return rd
    for k in ar.keys():
        if k[0]=='_': continue
        if rd.has_key(k):
            if type(rd[k])==types.StringType: rd[k]=[rd[k]]
            if type(rd[k])==types.ListType:
                if type(ar[k])==types.ListType: rd[k]=rd[k]+ar[k]
                else: rd[k].append(ar[k])
            elif type(rd[k])==types.DictType:
                if type(ar[k])==types.DictType:
                    if k=='separatorsfor':
                        for k1 in ar[k].keys():
                            if not rd[k].has_key(k1): rd[k][k1]=ar[k][k1]
                    else: rd[k]=dictappend(rd[k],ar[k])
        else: rd[k]=ar[k]
    return rd


def run_thread(command,wd=None):
    threading.Thread(target=run_command,
                     args=(command,wd),
                     ).start()

def run_command(command,wd=None):
    sys.stdout.write(command)
    if wd is not None:
        cwd = os.getcwd()
        os.chdir(wd)
    in_pipe,out_pipe = os.popen4(command)
    in_pipe.close()
    if wd is not None:
        os.chdir(cwd)
    mess = out_pipe.read()
    sys.stdout.write(mess)

def runlatex(fp,dopts = {}):
    if not fp: return
    opts = ''
    if dopts.has_key('latex'): opts = dopts['latex']
    wd = os.path.dirname(fp)
    fn = os.path.basename(fp)
    com = 'latex %s %s.tex'%(opts,fn)
    run_command(com,wd)

def rundviview(fp,dopts = {}):
    if not fp: return
    wd = os.path.dirname(fp)
    fn = os.path.basename(fp)
    opts = ''
    if os.name == 'nt':
        if dopts.has_key('yap'): opts = dopts['yap']
        com = 'yap %s %s.dvi'%(opts,fp)
    else:
        if dopts.has_key('xdvi'): opts = dopts['xdvi']
        com = 'xdvi %s %s.dvi'%(opts,fp)
    run_thread(com)

def rundvips(fp,dopts = {},outfn='-o'):
    if not fp: return
    opts = ''
    if dopts.has_key('dvips'): opts = dopts['dvips']
    wd = os.path.dirname(fp)
    fn = os.path.basename(fp)
    com = 'dvips %s %s %s'%(opts,fn,outfn)
    run_command(com,wd)

def runpsview(fp,dopts = {}):
    if not fp: return
    wd = os.path.dirname(fp)
    fn = os.path.basename(fp)
    opts = ''
    if os.name == 'nt':
        if dopts.has_key('gsview'): opts = dopts['gsview']
        com = gsview_exe + ' %s %s.ps'%(opts,fp)
    else:
        if dopts.has_key('gv'): opts = dopts['gv']
        com = 'gv %s %s.ps'%(opts,fp)
    run_thread(com)

def rundvipdfm(fp,dopts = {},outfn='-o'):
    if not fp: return
    opts = ''
    if dopts.has_key('dvipdfm'): opts = dopts['dvipdfm']
    wd = os.path.dirname(fp)
    fn = os.path.basename(fp)
    com = 'dvipdfm %s %s %s.pdf %s'%(opts,outfn,fn,fn)
    run_command(com,wd)

def runpdfview(fp,dopts = {}):
    if not fp: return
    wd = os.path.dirname(fp)
    fn = os.path.basename(fp)
    opts = ''
    if dopts.has_key('acroread'): opts = dopts['acroread']
    if os.name=='nt':
        com = '%s %s %s.pdf'%(acrord_exe, opts,fp)
    else:
        com = 'evince %s %s.pdf'%(opts,fp)
    run_thread(com)

def Warning(*mess):
    sys.stderr.write('WARNING:%s\n'%(string.join(map(str,list(mess)),' ')))
    wx.Bell()
    
def Message(*mess):
    sys.stdout.write('Message:%s\n'%(string.join(map(str,list(mess)),' ')))
    wx.Bell()

def Info(*mess):
    global top_parent
    mess = string.join(map(str,list(mess)),' ')
    sys.stdout.write('Info:%s\n'%(mess))
    if top_parent:
        top_parent.statusbar.SetStatusText(mess,0)
    wx.Bell()

def Debug(*mess):
    if debuglevel>=1:
        sys.stderr.write('Debug:%s\n'%(string.join(map(str,list(mess)),' ')))

def Debug1(*mess):
    if debuglevel>=1:
        sys.stderr.write('Debug1:%s\n'%(string.join(map(str,list(mess)),' ')))

def Debug2(*mess):
    if debuglevel>=2:
        sys.stderr.write('Debug2:%s\n'%(string.join(map(str,list(mess)),' ')))


def gettimes(race,stime=-1):
    ret = []
    dt = 0
    t = 0
    for r in race:
        if r:
            if r[0] in [1,2]:
                t = t + r[1] + dt
                if stime<0 or t<stime:
                    ret.append(r[1]+dt)
                dt = 0
            elif r[0] in [-1,-2]:
                dt = dt + r[1]
    return ret

def getlasttime(race):
    dt = 0
    t = 0
    for r in race:
        if r:
            if r[0] in [1,2]:
                t = t + r[1] + dt
                dt = 0
            elif r[0] in [-1,-2]:
                dt = dt + r[1]
    return t

def normalize_str(obj):
    if not USE_UNICODE:
        return obj
    if isinstance(obj,str):
        return obj.decode('latin-1')
    elif isinstance(obj, list):
        l = []
        flag = 0
        for item in obj:
            newitem = normalize_str(item)
            if newitem is not item:
                flag = 1
            l.append(newitem)
        if flag:
            return l
    elif isinstance(obj, dict):
        d = {}
        flag = 0
        for k,v in obj.items():
            newv = normalize_str(v)
            if newv is not v:
                flag = 1
            d[k] = newv
        if flag:
            return d
    return obj
    
def denormalize_str(obj):
    if not USE_UNICODE:
        return obj
    if isinstance(obj,unicode):
        return obj.encode('latin-1')
    elif isinstance(obj, list):
        l = []
        flag = 0
        for item in obj:
            newitem = denormalize_str(item)
            if newitem is not item:
                flag = 1
            l.append(newitem)
        if flag:
            return l
    elif isinstance(obj, dict):
        d = {}
        flag = 0
        for k,v in obj.items():
            newv = denormalize_str(v)
            if newv is not v:
                flag = 1
            d[k] = newv
        if flag:
            return d
    return obj
    
