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

import string,pprint,sys,os,time
import glob,shutil
show=pprint.pprint
from prefs import *
import prefs
import analyzer

badnames = {'/Q':'Q','/T':'T'}

def latexworkingdir():
    folder = 'cozer_tex_'+time.strftime('%d%b%y',time.localtime())
    si,i = '',0
    while os.path.exists(folder+si) and not os.path.isdir(folder+si): i = i + 1; si = `i`
    folder = folder + si
    if not os.path.exists(folder):
        os.mkdir(folder)
    if not os.path.isdir(folder):
        raise 'Failed to create a folder %s'%(`folder`)
    data_dir = os.path.join(os.path.dirname(prefs.__file__),'data')
    for fn in glob.glob(os.path.join(data_dir,'*.tex'))+\
        glob.glob(os.path.join(data_dir,'*.sty')):
        if not os.path.exists(os.path.join(folder,os.path.basename(fn))):
            Message('Copying %s to directory %s'%(fn,folder))
            shutil.copy(fn,folder)
    return folder

def saveorder(eventdata,cl,rks):
    if not eventdata.has_key('prevorder'): eventdata['prevorder'] = {}
    if istclass(cl): cl = cl[:-2]
    elif isqclass(cl): cl = cl[:-2]
    eventdata['prevorder'][cl] = rks

parts_doc_latextmpl = r"""
\documentclass[12pt,a4paper]{article}
\input #language#_cozer
\usepackage[T1]{fontenc}
\usepackage[estonian,english]{babel}
\usepackage{a4wide}
\usepackage{longtable}
\usepackage{fancyheadings}
\pagestyle{fancy}
%\lfoot{/#officer#/\\\OfficeroftheDay}
\cfoot{\Page{} \thepage}
\rfoot{/#secretary#/\\\SecretaryoftheRace}
\rhead{#date#\\#venue#}
%\lhead{#title#}
\lhead{
\begin{minipage}[b]{.6\textwidth}
#title#
\end{minipage}
}
\headheight=36pt
\voffset=-24pt
\begin{document}

\begin{center}
\textbf{\Large \Registeredcompetitors}
\end{center}


\setlongtables
\begin{longtable}[l]{c|l|l|c}
\Class & \Name & \Country & \RaceNo\\\hline
#table#
\end{longtable}
\end{document}
"""
parts_class_latextmpl = r"""\multicolumn4{l}{\textbf{#class#}}\\"""
parts_part_latextmpl = r""" &#name# & #country# & \textbf{#id#}\\"""


inter_doc_latextmpl = r"""
\documentclass[12pt,a4paper]{article}
\input #language#_cozer
\usepackage[T1]{fontenc}
\usepackage[estonian,english]{babel}
\usepackage{a4wide}
\usepackage{longtable}
\usepackage{fancyheadings}
\pagestyle{fancy}
\lfoot{#currenttime#}
\cfoot{}
\rfoot{\SecretaryoftheRace{} /#secretary#/}
\rhead{#date#\\#venue#}
%\lhead{#title#}
\lhead{
\begin{minipage}[b]{.6\textwidth}
#title#
\end{minipage}
}
\headheight=36pt
\voffset=-24pt
\begin{document}

\begin{center}
\textbf{\Large \IntermediateResults}
\end{center}

#tables#


\end{document}
"""

inter_table1_latextmpl = r"""
\nobreak
\ifdim\pagetotal>0.75\textheight\clearpage\fi
\subsection*{\large \Class{} #class# \Heat{} #heat#}
\mbox{}\hfill\mbox{\small \Starttime: #starttime#}
\setlongtables
\begin{longtable}[l]{c|l|l|c|c|c}
\Place & \Name & \From & \No & \Res & \Pts \\\hline
#table1#
\\\hline
\multicolumn6{p{1cm}}{
\begin{minipage}{.9\textwidth}
#notes#
\end{minipage}
}
\end{longtable}

"""
inter_part1_latextmpl = r"""#place# & #name# & #from# & \textbf{#id#} & #result# & #points#"""

inter_tt_table1_latextmpl = r"""
\nobreak
\ifdim\pagetotal>0.75\textheight\clearpage\fi
\subsection*{\large \Class{} #class# \Heat{} #heat#}
\mbox{}\hfill\mbox{\small \Starttime: #starttime#}
\setlongtables
\begin{longtable}[l]{c|l|l|c|c}
\Place & \Name & \From & \No & \LapTime \\\hline
#table1#
\\\hline
\multicolumn5{p{1cm}}{
\begin{minipage}{.9\textwidth}
#notes#
\end{minipage}
}
\end{longtable}

"""
inter_tt_part1_latextmpl = r"""#place# & #name# & #from# & \textbf{#id#} & #result#"""

inter_table_latextmpl = r"""
\nobreak
\ifdim\pagetotal>0.75\textheight\clearpage\fi
\subsection*{\large \Class{} #class# \Heat{} #heat#}
\mbox{}\hfill\mbox{\small \Starttime: #starttime#}
\setlongtables
\begin{longtable}[l]{c|l|l|c|c|c||c|c}
\multicolumn6{c||}{}                      & \multicolumn2{c}{\Heats{} #heats#} \\\cline{7-8}
\Place & \Name & \From & \No & \Res & \Pts & \Res & \Pts \\\hline
#table#
\\\hline
\multicolumn8{p{1cm}}{
\begin{minipage}{.9\textwidth}
#notes#
\end{minipage}
}
\end{longtable}

"""

inter_part_latextmpl = r"""#place# & #name# & #from# & \textbf{#id#} & #result# & #points# & #bestresult# & #sumpoints#"""

endurance_full_doc_latextmpl = r"""
\documentclass[11pt,a4paper]{article}
\input #language#_cozer
\usepackage[T1]{fontenc}
\usepackage[estonian,english]{babel}
\usepackage{a4wide}
\usepackage{landscape}
\usepackage{longtable}
\usepackage{fancyheadings}
\pagestyle{fancy}
\lfoot{/#officer#/\\\OfficeroftheDay}
\cfoot{\Page{} \thepage}
\rfoot{/#secretary#/\\\SecretaryoftheRace}
\rhead{#date#\\#venue#}
%\lhead{#title#}
\lhead{
\begin{minipage}[b]{.6\textwidth}
#title#
\end{minipage}
}
\hoffset=-1cm
\headheight=36pt
\voffset=-36pt
\begin{document}
\begin{center}
\textbf{\Large #reporttitle#}
\end{center}

#tables#

\end{document}
"""

endurance_full_table_latextmpl = r"""
\nobreak
\ifdim\pagetotal>0.75\textheight\clearpage\fi
\subsection*{\Class{} #class#}
\begin{center}
\setlongtables
\begin{longtable}[l]{c|l|l|c|c|c|c|c|c}
\Place & \Name & \From & \No & Best Lap Time & Best Lap & Total Laps Time & Total Laps & Points \\\hline
#table#
\\\hline
\multicolumn{#nofcols#}{p{1cm}}{
\begin{minipage}{.9\textwidth}
#notes#
\end{minipage}
}
\end{longtable}
\end{center}

"""
endurance_full_part1_latextmpl = r"""#place# & #name# & #from# & \textbf{#id#}  & #bestlaptime# & #bestlap# & #totallapstime# & #totallaps##indices# & #points#"""

full_doc_latextmpl = r"""
\documentclass[11pt,a4paper]{article}
\input #language#_cozer
\usepackage[T1]{fontenc}
\usepackage[estonian,english]{babel}
\usepackage{a4wide}
\usepackage{landscape}
\usepackage{longtable}
\usepackage{fancyheadings}
\pagestyle{fancy}
\lfoot{/#officer#/\\\OfficeroftheDay}
\cfoot{\Page{} \thepage}
\rfoot{/#secretary#/\\\SecretaryoftheRace}
\rhead{#date#\\#venue#}
%\lhead{#title#}
\lhead{
\begin{minipage}[b]{.6\textwidth}
#title#
\end{minipage}
}
\hoffset=-1cm
\headheight=36pt
\voffset=-36pt
\begin{document}
\begin{center}
\textbf{\Large \FinalResults}
\end{center}

#tables#

\end{document}
"""
full_table_latextmpl = r"""
\nobreak
\ifdim\pagetotal>0.75\textheight\clearpage\fi
\subsection*{\Class{} #class#}
\begin{center}
\setlongtables
\begin{longtable}[l]{c|l|l|c#tablepat#||c|c}
\multicolumn4{c|}{}       #tablehead1# & \multicolumn2{c}{\Summary}\\#cline#
\Place & \Name & \From & \No #tablehead2# & \Res    & \Pts        \\\hline
#table#
\\\hline
\multicolumn{#nofcols#}{p{1cm}}{
\begin{minipage}{.9\textwidth}
#notes#
\end{minipage}
}
\end{longtable}
\end{center}

"""
full_part1_latextmpl = r"""#place# & #name# & #from# & \textbf{#id#} #heatsres# & #bestresult# & #sumpoints#"""

short_doc_latextmpl = r"""
\documentclass[12pt,a4paper]{article}
\input #language#_cozer
\usepackage[T1]{fontenc}
\usepackage[english]{babel}
\usepackage{a4wide}
%\usepackage{landscape}
\usepackage{longtable}
\usepackage{fancyheadings}
\pagestyle{fancy}
\lfoot{/#officer#/\\\OfficeroftheDay}
\cfoot{\Page{} \thepage}
\rfoot{/#secretary#/\\\SecretaryoftheRace}
\rhead{#date#\\#venue#}
%\lhead{#title#}
\lhead{
\begin{minipage}[b]{.6\textwidth}
#title#
\end{minipage}
}
%\voffset=-1cm
\headheight=36pt
\voffset=-24pt
\begin{document}
\begin{center}
\textbf{\Large \FinalResults}
\end{center}

#tables#

\end{document}
"""
short_table_latextmpl = r"""
\nobreak
\ifdim\pagetotal>0.75\textheight\clearpage\fi
\subsection*{\Class{} #class#}
\setlongtables
\begin{longtable}[l]{c|l|l|c||c|c}

\Place & \Name & \From & \No  & \Results    & \Points        \\\hline
#table#
\\\hline
\multicolumn6{p{1cm}}{
\begin{minipage}{.9\textwidth}
#notes#
\end{minipage}
}
\end{longtable}


"""
short_part1_latextmpl = r"""#place# & #name# & #from# & \textbf{#id#} & #bestresult# & #sumpoints#"""

check_doc_latextmpl = r"""
\documentclass[12pt,a4paper]{article}
\input #language#_cozer
\usepackage[T1]{fontenc}
\usepackage[english]{babel}
\usepackage{a4wide}
\usepackage{landscape}
\usepackage{longtable}
\usepackage{fancyheadings}
\pagestyle{fancy}
%\lfoot{/#officer#/\\\OfficeroftheDay}
\cfoot{\Page{} \thepage}
%\rfoot{/#secretary#/\\\SecretaryoftheRace}
\rhead{#date#\\#venue#}
%\lhead{#title#}
\lhead{
\begin{minipage}[b]{.6\textwidth}
#title#
\end{minipage}
}
%\voffset=-1cm
\headheight=36pt
\voffset=-36pt
\begin{document}
\begin{center}
\textbf{\Large \DriversMeetingChecklist}
\end{center}

#tables#

\end{document}
"""
check_table_latextmpl = r"""
\nobreak
\ifdim\pagetotal>0.75\textheight\clearpage\fi
\textbf{\large \Class{} #class#}
\setlongtables
\begin{longtable}[l]{l|l|c|c|c|c|c|}

\Name & \From & \No  & \Inspection & \Meeting{} 1 & \Meeting{} 2 & \Meeting{} 3 \\\hline
#table#
\end{longtable}


"""
check_part1_latextmpl = r"""#name# & #from# & \textbf{#id#} & & & &\\[1.5ex]\hline"""
check_part1cont_latextmpl = r"""#name# & #from# & \textbf{#id#} & & & &\\"""
check_part1contlast_latextmpl = r"""#name# & #from# & \textbf{#id#} & & & &\\\hline"""


info_doc_latextmpl = r"""
\documentclass[12pt,a4paper]{article}
\input #language#_cozer
\usepackage[T1]{fontenc}
\usepackage[english]{babel}
\usepackage{a4wide}
%\usepackage{landscape}
\usepackage{longtable}
\usepackage{fancyheadings}
\pagestyle{fancy}
%\lfoot{/#officer#/\\\OfficeroftheDay}
\cfoot{}
%\rfoot{/#secretary#/\\\SecretaryoftheRace}
\rhead{#date#\\#venue#}
\lhead{
\begin{minipage}[b]{.6\textwidth}
#title#
\end{minipage}
}
%\voffset=-1cm
\headheight=36pt
\voffset=-24pt
\begin{document}
\vspace*{1cm}

\cozerinfoletter

\end{document}
"""

registration_doc_latextmpl = r"""
\documentclass[12pt,a4paper]{article}
\input #language#_cozer
\usepackage[T1]{fontenc}
\usepackage[english]{babel}
\usepackage{a4wide}
\hoffset=-1.1cm
\voffset=-0.8cm
\begin{document}
\pagestyle{empty}
\enlargethispage{3cm}
\cozerregistrationletter{#title#}{#venue#}{#date#}
\end{document}
"""

laps_doc_latextmpl = r"""
\documentclass[12pt,a4paper]{article}
\input #language#_cozer
\usepackage[T1]{fontenc}
\usepackage[english]{babel}
\usepackage{a4wide}
%\usepackage{landscape}
\usepackage{longtable}
\usepackage{fancyheadings}
\pagestyle{fancy}
%\lfoot{/#officer#/\\\OfficeroftheDay}
\cfoot{}
%\rfoot{/#secretary#/\\\SecretaryoftheRace}
\rhead{#date#\\#venue#}
%\lhead{#title#}
\lhead{
\begin{minipage}[b]{.6\textwidth}
#title#
\end{minipage}
}
%\voffset=-1cm
\headheight=36pt
\voffset=-24pt
\begin{document}
\begin{center}
\textbf{\Large \LapsCounterProtocol}
\end{center}

\large
#tables#

\end{document}
"""
laps_table_latextmpl = r"""
\nobreak
\ifdim\pagetotal>0.75\textheight\clearpage\fi
\subsection*{\Class{} #class# #heat#}
\setlongtables
\begin{longtable}[l]{#tablepat#}
#lapshead# \\\hline
#table#\\\hline
\end{longtable}
"""
#laps_row_latextmpl = r"""#place# & #name# & #from# & \textbf{#id#} #heatsres# & #bestresult# & #sumpoints#"""

def get_fullname(first, last):
    if ';' in first and first.count(';')>last.count (';'):
        last += ';' * (first.count(';')-last.count (';'))
    if ';' in last and first.count(';')<last.count (';'):
        first += ';' * (last.count(';')-first.count (';'))
    if ';' in first and first.count(';')==last.count (';'):
        name = []
        for f1,l1 in zip (first.split (';'), last.split (';')):
            name.append ('%s %s'%(f1,l1))
        name = '; '.join(name)
    else:
        name = '%s %s'%(first, last)
    return name

def participants(clses,heat_map,eventdata):
    Debug('participants')
    parts = {}
    rks = []
    for p in eventdata['participants']:
        if not p[4] in clses: continue
        if not parts.has_key(p[4]): parts[p[4]] = []
        try: val=eval(p[5])
        except: val = p[5]
        parts[p[4]].append([val,p[1],p[2],p[3],p[5]])

    for cl in parts.keys():
        parts[cl].sort()
        saveorder(eventdata,cl,map(lambda k:k[0],parts[cl]))
    wd = latexworkingdir()
    if len(clses) == len(eventdata['classes']): fn = 'part_all'
    else: fn = 'part_%s'%(string.join(clses,'_'))
    for k in badnames.keys():
        fn = string.replace(fn,k,badnames[k])
    fn = os.path.join(wd,fn)
    f = open(fn+'.tex','w')

    rd = {}
    rd['secretary'] = eventdata['secretary']
    rd['officer'] = eventdata['officer']
    rd['title'] = eventdata['title']
    rd['date'] = eventdata['date']
    rd['venue'] = eventdata['venue']
    try: l = eventdata['configure']['language']
    except KeyError: l = 'English'
    rd['language'] = l
    rd['table'] = []
    rd['separatorsfor'] = {'table':'\n'}
    for cl in clses:
        if not parts.has_key(cl): continue
        rd['table'].append(replace(parts_class_latextmpl,{'class':cl}))
        for p in parts[cl]:
            for i, name in enumerate (get_fullname (p[1], p[2]).split (';')):
                if i:
                    d = {'name':name,'country':'', 'id':''}
                else:
                    d = {'name':name,
                         'country':p[3],
                         'id':'%s'%(p[4])}
                rd['table'].append(replace(parts_part_latextmpl,d))
    txt = replace(parts_doc_latextmpl,rd)
    f.write(denormalize_str(txt))
    f.close()
    return fn,{'latex':'--interaction nonstopmode',
               'gv':'--media=a4',
               'dvipdfm':'-p a4',
               'dvips':'-q'}

def res2latex(res,notes, istimetrial=False, isqualification=False):
    l = len(notes)
    r=''
    laps,penlapsleft,lapsleft = res['lapinfo']
    if istimetrial:
        if res['laptime']:
            r = '%.3f' % (res['laptime'])
    elif isqualification:
        r = ''
    elif res['points']>=0:
        if lapsleft:
            r='%s%.1f/%.1f/%s\\Lp'%(r,res['avgspeed'],res['maxlapspeed'],laps)
        else:
            r='%s%.1f/%.1f'%(r,res['avgspeed'],res['maxlapspeed'])
    if not res['notes']:
        if not r: return '-'
        return r
    for c in res['notes'].keys():
        if not res['notes'][c]:
            r='%s %s'%(r,c)
            continue
        l = l + 1
        if c=='DS' and 'HIDE' in res['notes'][c]:
            return None
        r='%s %s${}^{%s}$'%(r,c,l)
        notes.append('${}^{%s}$---$%s$'%(l,string.join(res['notes'][c],',')))
    return r


def intermediate(clses,heat_map,eventdata):
    Debug('intermediate')
    record = eventdata['record']
    sumres={}
    res={}
    info={}
    parts={}
    for l in eventdata['participants']:
        parts[l[4],l[5]] = [l[1],l[2],l[3]]
        parts[l[4]+'/Q',l[5]] = [l[1],l[2],l[3]]
        parts[l[4]+'/T',l[5]] = [l[1],l[2],l[3]]
    fn='inter'
    for cl in clses:
        res[cl] = {}
        for h in heat_map[cl]:
            info[cl,h]=record[cl][h][0]
            res[cl][h] = analyzer.analyze(h,record[cl][h],eventdata['scoringsystem'])
        sumres[cl] = analyzer.sumanalyze(heat_map[cl],res[cl],eventdata['sheats'][cl])
        if len(heat_map[cl])>1:
            fn='%s_%s-%s-%s'%(fn,cl,heat_map[cl][0],heat_map[cl][-1])
        else:
            if heat_map[cl]: fn='%s_%s-%s'%(fn,cl,heat_map[cl][0])
            else: fn='%s_%s'%(fn,cl)
    wd = latexworkingdir()
    for k in badnames.keys():
        fn = string.replace(fn,k,badnames[k])
    fp = os.path.join(wd,fn)
    f = open(fp+'.tex','w')

    rd = {}
    rd['title'] = eventdata['title']
    rd['date'] = eventdata['date']
    rd['venue'] = eventdata['venue']
    rd['secretary'] = eventdata['secretary']
    try: l = eventdata['configure']['language']
    except KeyError: l = 'English'
    rd['language'] = l
    rd['tables'] = []
    rd['separatorsfor'] = {'tables':'\n'}
    rd['currenttime'] = time.ctime(time.time())
    for cl in clses:
        if not heat_map[cl]: continue
        curheat = heat_map[cl][-1]
        istimetrial = curheat.endswith('t')
        isqualification = curheat.endswith('q')
        rks = analyzer.getresorder(res[cl][curheat])
        saveorder(eventdata,cl,rks)
        d = {'separatorsfor':{'table1':'\\\\\n','table':'\\\\\n',
                              'notes':'; '},
             'heats':string.join(heat_map[cl],',')}
        d['class'] = getclass(cl)
        d['heat'] = curheat
        d['table1'] = []
        d['table'] = []
        d['notes'] = [r'\ResNote']
        try: d['starttime'] = time.ctime(info[cl,curheat]['starttime'])
        except KeyError: d['starttime'] = r'\None'
        legend = []
        for id in rks:
            r = res[cl][curheat][id]
            sr = sumres[cl][id]
            lr=res2latex(r,d['notes'], istimetrial, isqualification)
            if lr is None:
                continue
            p = parts[cl,'%s'%id]
            fullnames = get_fullname(p[0],p[1]).split (';')
        
            dp = {'place':'-','id':'%s'%id,'result':lr,'points':'-',
                  'name':fullnames[0],'from':p[2],
                  'bestresult':'-','sumpoints':'-'}
            if r['place']>0:
                dp['place'] = '%s'%r['place']
                dp['points'] = '%s'%r['points']
            if sr['place']>0:
                dp['bestresult'] = '%.1f/%.1f'%(sr['avgspeed'],sr['maxlapspeed'])
                dp['sumpoints'] = '%s'%sr['points']
            if istimetrial:
                d['table1'].append(replace(inter_tt_part1_latextmpl,dp))
            else:
                d['table1'].append(replace(inter_part1_latextmpl,dp))

            d['table'].append(replace(inter_part_latextmpl,dp))
            for name in fullnames[1:]:
                for dpk in dp: dp[dpk] = ''
                dp['name'] = name
                if istimetrial:
                    d['table1'].append(replace(inter_tt_part1_latextmpl,dp))
                else:
                    d['table1'].append(replace(inter_part1_latextmpl,dp))
            if r['notes']:
                for k in r['notes'].keys():
                    if k not in legend: legend.append(k)
        for l in legend:
            d['notes'].append('%s=%s'%(l,reccodelatexlabel[l]))
        if len(heat_map[cl])>1:
            rd['tables'].append(replace(inter_table_latextmpl,d))
        else:
            if istimetrial:
                rd['tables'].append(replace(inter_tt_table1_latextmpl,d))
            else:
                rd['tables'].append(replace(inter_table1_latextmpl,d))
    f.write(denormalize_str(replace(inter_doc_latextmpl,rd)))
    f.close()

    return fp,{'latex':'--interaction nonstopmode',
               'gv':'--media=a4',
               'dvipdfm':'-p a4',
               'dvips':'-q'}

def sec2time (secs):
    if secs is None:
        return '-'
    if secs<0:
        return '- ' + sec2time (-secs)
    hours = int(secs / 3600)
    minutes = int ((secs - hours * 3600)/60)
    seconds = int ((secs - hours*3600-minutes*60))
    rest = int((secs - hours*3600-minutes*60-seconds)*1000)
    assert (hours*60*60+minutes*60+seconds+rest/1000. - secs)<0.001,`secs,hours*60*60+minutes*60+seconds+rest/1000.`
    if isinstance (secs, int):
        return '%02i:%02i:%02i' % (hours, minutes, seconds)
    return '%02i:%02i:%02i.%03d' % (hours, minutes, seconds, rest)

def fullfinal_endurance(clses,heat_map,eventdata):
    Debug('fullfinial_endurance')
    record = eventdata['record']
    res={}
    info={}
    parts={}
    for l in eventdata['participants']:
        parts[l[4],l[5]] = [l[1],l[2],l[3]]
    sumres = {}
    for cl in clses:
        res[cl] = {}
        for h in heat_map[cl]:
            info[cl,h]=record[cl][h][0]
            res[cl][h] = analyzer.analyze(h,record[cl][h],eventdata['scoringsystem'])
        #if len(heat_map[cl])>1:
        sumres[cl] = analyzer.sumanalyze(heat_map[cl],res[cl],eventdata['sheats'][cl])
        #else:
        #    sumres[cl] = {}

    wd = latexworkingdir()
    if len(clses) == len(eventdata['classes']): fn = 'endurance_full_all'
    else: fn = 'endurance_full_%s'%(string.join(clses,'_'))
    for k in badnames.keys():
        fn = string.replace(fn,k,badnames[k])
    fn = os.path.join(wd,fn)
    f = open(fn+'.tex','w')
    rd = {}
    rd['title'] = eventdata['title']
    rd['date'] = eventdata['date']
    rd['venue'] = eventdata['venue']
    rd['secretary'] = eventdata['secretary']
    rd['officer'] = eventdata['officer']
    try: l = eventdata['configure']['language']
    except KeyError: l = 'English'
    rd['language'] = l
    rd['tables'] = []
    rd['separatorsfor'] = {'tables':'\n'}
    rd['currenttime'] = time.ctime(time.time())
    rd['reporttitle'] = r'\FinalResults{}'


    for cl in clses:
        if not heat_map[cl]: continue
        try:
            info = eventdata['record'][cl][heat_map[cl][0]][0]
        except:
            info = None
        skippoints = False
        if info is not None:
            stoptime = info['starttime'] + info['racetime']
            currenttime = time.time ()
            if currenttime < stoptime:
                skippoints = True
                rd['reporttitle'] = r'\IntermediateResults{}' + ' \\small{--- %s to go}' % (sec2time(int(stoptime - currenttime)))
            else:
                rd['reporttitle'] = r'\FinalResults{}' + ' \\small{--- %s}' % (time.strftime('%y %b %d %H:%M:%S',time.localtime(currenttime)),
                                                                               )
                titlenote = ''
                if info['racetime'] >= info['duration']:
                    pass
                elif info['racetime'] >= 0.9*info['duration']:
                    titlenote = ', full points are awarded (U.I.M. 902.17)'
                elif info['racetime'] >= 0.75*info['duration']:
                    titlenote = ', 75\\% of points are awarded (U.I.M. 902.17)'
                elif info['racetime'] >= 0.5*info['duration']:
                    titlenote = ', 50\\% of points are awarded (U.I.M. 902.17)'
                elif info['racetime'] >= 0.25*info['duration']:
                    titlenote = ', 25\\% of points are awarded (U.I.M. 902.17)'
                else:
                    titlenote = ', no points are awarded (U.I.M. 902.17)'

                rd['reporttitle'] += '\\\\\\small{Race duration is %s%s}' % (sec2time (int (info['racetime'])), titlenote)
        #curheat = heat_map[cl][-1]
        rks = analyzer.getsumresorder(sumres[cl])
        saveorder(eventdata,cl,rks)
        nofh = len(heat_map[cl])
        d = {'separatorsfor':{'table':'\\\\\n','notes':'; '},
             'tablepat':nofh*'|c|c',
             'nofcols':'9',
             #'tablehead1':map(lambda s:'&\multicolumn2{c|}{\\Heat{} %s}'%s,heat_map[cl][:-1])+\
             #['&\multicolumn2{c||}{\\Heat{} %s}'%heat_map[cl][-1]],
             #'tablehead2':nofh*r'&{\small \Res}&{\small \Pts}',
             'cline':'\\cline{5-%s}'%(4+2*nofh+2),
             'table':[],
             'notes':[],
             'class':getclass(cl)
             }
        legend = []
        #rks = analyzer.getsumresorder(sumres[cl])
        notescounter = 0
        notesmap = {}
        for place, id in enumerate(rks):
            p = parts[cl,'%s'%id]
            names = get_fullname(p[0], p[1]).split (';')
            dp = {'place':'-','points':'-',
                  'name':names[0],'from':p[2],'id':'%s'%id,
                  'totallaps':'-', 'totallapstime':'-',
                  'bestlap':'-','bestlaptime':'-',
                  'indices':''
                  }
            assert len (heat_map[cl])==1,`cl, heat_map[cl]`
            h=heat_map[cl][0]
            r = res[cl][h][id]
            dp['totallaps'] = str(r['totallaps'][1] or '-')
            dp['totallapstime'] = sec2time(r['totallaps'][0])
            dp['bestlap'] = str(r['bestlap'][1] or '-')
            dp['bestlaptime'] = sec2time(r['bestlap'][0])

            if r['notes']:
                indices = []
                for mark, rules in r['notes'].items ():
                    for rule in rules:
                        index = notesmap.get ((mark, rule))
                        if index is None:
                            index = notesmap[mark, rule] = len(notesmap)+1
                        indices.append(str(index))
                dp['indices'] = '${}^{%s}$' % (', '.join (indices))

            if r['points']>0:
                if not skippoints:
                    dp['points'] = '%s'%r['points']
                dp['place'] = '%s'%(place+1)

            if r['notes']:
                for k in r['notes'].keys():
                    if k not in legend: legend.append(k)

            d['table'].append(replace(endurance_full_part1_latextmpl,dp))
            for name in names[1:]:
                for dpk in dp:
                    if isinstance (dp[dpk], list):
                        dp[dpk]=['&'*v.count ('&') for v in dp[dpk]]
                    else:
                        dp[dpk]=''
                dp['name'] = name
                d['table'].append(replace(endurance_full_part1_latextmpl,dp))
        for (mark,rule),index in notesmap.items ():
            d['notes'].append ('${}^{%s}$---%s $%s$' % (index, mark, rule))

        for l in legend:
            d['notes'].append('%s=%s'%(l,reccodelatexlabel[l]))
        rd['tables'].append(replace(endurance_full_table_latextmpl,d))

    f.write(denormalize_str(replace(endurance_full_doc_latextmpl,rd)))
    f.close()
    return fn,{'latex':'--interaction nonstopmode',
               'dvips':'-q -t landscape -t a4',
               'dvipdfm':'-l -p a4',
               'xdvi':'-paper a4r',
               'yap':'',
               'gv':'--media=a4 --swap',
               }

def fullfinal(clses,heat_map,eventdata):
    Debug('fullfinial')
    record = eventdata['record']
    sumres={}
    res={}
    info={}
    parts={}
    for l in eventdata['participants']:
        parts[l[4],l[5]] = [l[1],l[2],l[3]]
        parts[l[4]+'/Q',l[5]] = [l[1],l[2],l[3]]
        parts[l[4]+'/T',l[5]] = [l[1],l[2],l[3]]
    for cl in clses:
        res[cl] = {}
        for h in heat_map[cl]:
            info[cl,h]=record[cl][h][0]
            res[cl][h] = analyzer.analyze(h,record[cl][h],eventdata['scoringsystem'])
        #if len(heat_map[cl])>1:
        sumres[cl] = analyzer.sumanalyze(heat_map[cl],res[cl],eventdata['sheats'][cl])
        #else:
        #    sumres[cl] = {}
    wd = latexworkingdir()
    if len(clses) == len(eventdata['classes']): fn = 'full_all'
    else: fn = 'full_%s'%(string.join(clses,'_'))
    for k in badnames.keys():
        fn = string.replace(fn,k,badnames[k])
    fn = os.path.join(wd,fn)
    f = open(fn+'.tex','w')
    rd = {}
    rd['title'] = eventdata['title']
    rd['date'] = eventdata['date']
    rd['venue'] = eventdata['venue']
    rd['secretary'] = eventdata['secretary']
    rd['officer'] = eventdata['officer']
    try: l = eventdata['configure']['language']
    except KeyError: l = 'English'
    rd['language'] = l
    rd['tables'] = []
    rd['separatorsfor'] = {'tables':'\n'}
    rd['currenttime'] = time.ctime(time.time())

    for cl in clses:
        if not heat_map[cl]: continue
        #curheat = heat_map[cl][-1]
        rks = analyzer.getsumresorder(sumres[cl])
        saveorder(eventdata,cl,rks)
        nofh = len(heat_map[cl])
        d = {'separatorsfor':{'table':'\\\\\n','notes':'; '},
             'tablepat':nofh*'|c|c',
             'nofcols':str(2*nofh+6),
             'tablehead1':map(lambda s:'&\multicolumn2{c|}{\\Heat{} %s}'%s,heat_map[cl][:-1])+\
             ['&\multicolumn2{c||}{\\Heat{} %s}'%heat_map[cl][-1]],
             'tablehead2':nofh*r'&{\small \Res}&{\small \Pts}',
             'cline':'\\cline{5-%s}'%(4+2*nofh+2),
             'table':[],
             'notes':[r'\ResNote'],
             'class':getclass(cl)
             }
        legend = []
        for id in rks:
            p = parts[cl,'%s'%id]
            names = get_fullname(p[0], p[1]).split (';')
            dp = {'place':'-','bestresult':'-','sumpoints':'-',
                  'name':names[0],'from':p[2],'id':'%s'%id,
                  'heatsres':[]}
            sr = sumres[cl][id]
            if sr['place']>0:
                dp['place'] = '%s'%sr['place']
                dp['bestresult'] = '%.1f/%.1f'%(sr['avgspeed'],sr['maxlapspeed'])
                dp['sumpoints'] = '%s'%sr['points']
            for h in heat_map[cl]:
                r = res[cl][h][id]
                lr=res2latex(r,d['notes'])
                dh = {'result':lr,'points':'-'}
                if r['place']>0:
                    dh['points'] = '%s'%r['points']
                dp['heatsres'].append(replace(r'&{\small #result#}&{\small #points#}',dh))
                if r['notes']:
                    for k in r['notes'].keys():
                        if k not in legend: legend.append(k)
            d['table'].append(replace(full_part1_latextmpl,dp))
            for name in names[1:]:
                for dpk in dp:
                    if isinstance (dp[dpk], list):
                        dp[dpk]=['&'*v.count ('&') for v in dp[dpk]]
                    else:
                        dp[dpk]=''
                dp['name'] = name
                d['table'].append(replace(full_part1_latextmpl,dp))
        for l in legend:
            d['notes'].append('%s=%s'%(l,reccodelatexlabel[l]))
        rd['tables'].append(replace(full_table_latextmpl,d))

    f.write(denormalize_str(replace(full_doc_latextmpl,rd)))
    f.close()
    return fn,{'latex':'--interaction nonstopmode',
               'dvips':'-q -t landscape -t a4',
               'dvipdfm':'-l -p a4',
               'xdvi':'-paper a4r',
               'yap':'',
               'gv':'--media=a4 --swap',
               }

def shortfinal(clses,heat_map,eventdata):
    Debug('shortfinial')
    record = eventdata['record']
    sumres={}
    res={}
    info={}
    parts={}
    for l in eventdata['participants']:
        parts[l[4],l[5]] = [l[1],l[2],l[3]]
        parts[l[4]+'/Q',l[5]] = [l[1],l[2],l[3]]
        parts[l[4]+'/T',l[5]] = [l[1],l[2],l[3]]
    for cl in clses:
        res[cl] = {}
        for h in heat_map[cl]:
            info[cl,h]=record[cl][h][0]
            res[cl][h] = analyzer.analyze(h,record[cl][h],eventdata['scoringsystem'])
        sumres[cl] = analyzer.sumanalyze(heat_map[cl],res[cl],eventdata['sheats'][cl])
    wd = latexworkingdir()
    if len(clses) == len(eventdata['classes']): fn = 'short_all'
    else: fn = 'short_%s'%(string.join(clses,'_'))
    for k in badnames.keys():
        fn = string.replace(fn,k,badnames[k])
    fn = os.path.join(wd,fn)
    f = open(fn+'.tex','w')
    rd = {}
    rd['title'] = eventdata['title']
    rd['date'] = eventdata['date']
    rd['venue'] = eventdata['venue']
    rd['secretary'] = eventdata['secretary']
    rd['officer'] = eventdata['officer']
    try: l = eventdata['configure']['language']
    except KeyError: l = 'English'
    rd['language'] = l
    rd['tables'] = []
    rd['separatorsfor'] = {'tables':'\n'}
    rd['currenttime'] = time.ctime(time.time())

    for cl in clses:
        if not heat_map[cl]: continue
        rks = analyzer.getsumresorder(sumres[cl])
        saveorder(eventdata,cl,rks)
        nofh = len(heat_map[cl])
        d = {'separatorsfor':{'table':'\\\\\n','notes':'; '},
             'tablepat':nofh*'|c|c',
             'nofcols':str(2*nofh+6),
             'tablehead1':map(lambda s:'&\multicolumn2{c|}{\\Heat{} %s}'%s,heat_map[cl][:-1])+\
             ['&\multicolumn2{c||}{\\Heat{} %s}'%heat_map[cl][-1]],
             'tablehead2':nofh*r'&\Res&\Pts',
             'cline':'\\cline{5-%s}'%(4+2*nofh+2),
             'table':[],
             'notes':[r'\ResNote'],
             'class':getclass(cl)
             }
        legend = []
        for id in rks:
            p = parts[cl,'%s'%id]
            names = get_fullname (p[0],p[1]).split (';')
            dp = {'place':'-','bestresult':'-','sumpoints':'-',
                  'name':names[0],'from':p[2],'id':'%s'%id,
                  'heatsres':[]}
            sr = sumres[cl][id]
            if sr['place']>0:
                dp['place'] = '%s'%sr['place']
                dp['bestresult'] = '%.1f/%.1f'%(sr['avgspeed'],sr['maxlapspeed'])
                dp['sumpoints'] = '%s'%sr['points']
            d['table'].append(replace(short_part1_latextmpl,dp))
            for name in names[1:]:
                for dpk in dp:
                    if isinstance (dp[dpk], list):
                        dp[dpk]=['&'*v.count ('&') for v in dp[dpk]]
                    else:
                        dp[dpk]=''
                dp['name'] = name
                d['table'].append(replace(short_part1_latextmpl,dp))

        for l in legend:
            d['notes'].append('%s=%s'%(l,reccodelatexlabel[l]))
        rd['tables'].append(replace(short_table_latextmpl,d))
    txt = replace(short_doc_latextmpl,rd)
    f.write(denormalize_str(txt))
    f.close()
    return fn,{'latex':'--interaction nonstopmode',
               'dvips':'-q',
               'xdvi':'',
               'dvipdfm':'-p a4',
               'gv':'--media=a4'}



def checklist(clses,heat_map,eventdata):
    Debug('checklist')
    parts = {}
    for p in eventdata['participants']:
        if not p[4] in clses: continue
        if not parts.has_key(p[4]): parts[p[4]] = []
        try: val=eval(p[5])
        except: val = p[5]
        parts[p[4]].append([val,p[1],p[2],p[3],p[5]])
    for cl in parts.keys():
        for i in range(1,6):
            parts[cl].append([i*1000,'','','',''])
    for cl in parts.keys():
        parts[cl].sort()
    wd = latexworkingdir()
    if len(clses) == len(eventdata['classes']): fn = 'check_all'
    else: fn = 'check_%s'%(string.join(clses,'_'))
    for k in badnames.keys():
        fn = string.replace(fn,k,badnames[k])
    fn = os.path.join(wd,fn)
    f = open(fn+'.tex','w')
    rd = {}
    rd['title'] = eventdata['title']
    rd['date'] = eventdata['date']
    rd['venue'] = eventdata['venue']
    rd['secretary'] = eventdata['secretary']
    rd['officer'] = eventdata['officer']
    try: l = eventdata['configure']['language']
    except KeyError: l = 'English'
    rd['language'] = l
    rd['tables'] = []
    rd['separatorsfor'] = {'tables':'\n'}
    rd['currenttime'] = time.ctime(time.time())
    for cl in clses:
        if not parts.has_key(cl): continue
        d = {'separatorsfor':{'table':'\n'},
             'table':[],
             'class':cl
             }
        for p in parts[cl]:
            fullnames = get_fullname(p[1],p[2]).split (';')
            dp = {'name':fullnames[0],
                 'from':p[3],
                 'id':'%s'%(p[4])}
            if len (fullnames)==1:
                d['table'].append(replace(check_part1_latextmpl,dp))
            else:
                d['table'].append(replace(check_part1cont_latextmpl,dp))
                for name in fullnames[1:-1]:
                    d['table'].append(replace(check_part1cont_latextmpl,{'name':name,'from':'','id':''}))
                d['table'].append(replace(check_part1contlast_latextmpl,{'name':fullnames[-1],'from':'','id':''}))
        rd['tables'].append(replace(check_table_latextmpl,d))
    f.write(denormalize_str(replace(check_doc_latextmpl,rd)))
    f.close()
    return fn,{'latex':'--interaction nonstopmode',
               'gv':'--media=a4 --swap',
               'dvipdfm':'-p a4 -l',
               'xdvi':'-paper a4r',
               'dvips':'-q -t landscape -t a4',}

def infoletter(clses,heat_map,eventdata):
    Debug('infoletter')
    wd = latexworkingdir()
    fn = 'infoletter'
    fn = os.path.join(wd,fn)
    f = open(fn+'.tex','w')
    rd = {}
    rd['title'] = eventdata['title']
    rd['date'] = eventdata['date']
    rd['venue'] = eventdata['venue']
    rd['secretary'] = eventdata['secretary']
    rd['officer'] = eventdata['officer']
    try: l = eventdata['configure']['language']
    except KeyError: l = 'English'
    rd['language'] = l
    f.write(denormalize_str(replace(info_doc_latextmpl,rd)))
    f.close()
    return fn,{'latex':'--interaction nonstopmode',
               'dvips':'-q',
               'xdvi':'',
               'dvipdfm':'-p a4',
               'gv':'--media=a4'}

def registrationletter(clses,heat_map,eventdata):
    Debug('registrationletter')
    wd = latexworkingdir()
    fn = 'registrationletter'
    fn = os.path.join(wd,fn)
    f = open(fn+'.tex','w')
    rd = {}
    rd['title'] = eventdata['title']
    rd['date'] = eventdata['date']
    rd['venue'] = eventdata['venue']
    rd['secretary'] = eventdata['secretary']
    rd['officer'] = eventdata['officer']
    try: l = eventdata['configure']['language']
    except KeyError: l = 'English'
    rd['language'] = l
    f.write(denormalize_str(replace(registration_doc_latextmpl,rd)))
    f.close()
    return fn,{'latex':'--interaction nonstopmode',
               'dvips':'-q',
               'xdvi':'',
               'dvipdfm':'-p a4',
               'gv':'--media=a4'}

def lapsprotocol(clses,heat_map,eventdata):
    Debug('lapsprotocol')
    record = eventdata['record']
    sumres={}
    res={}
    info={}
    parts={}
    laps={}
    for l in eventdata['participants']:
        parts[l[4],l[5]] = [l[1],l[2],l[3]]
        parts[l[4]+'/Q',l[5]] = [l[1],l[2],l[3]]
        parts[l[4]+'/T',l[5]] = [l[1],l[2],l[3]]
    fn='laps'
    for cl in clses:
        if not heat_map[cl]:
            curheat = record[cl].keys()[-1]
            laps[cl] = analyzer.countlaps(-1,record[cl][curheat])
            fn='%s_%s'%(fn,cl)
        else:
            curheat = heat_map[cl][-1]
            laps[cl] = analyzer.countlaps(curheat,record[cl][curheat])
            fn='%s_%s-%s'%(fn,cl,curheat)
    wd = latexworkingdir()
    for k in badnames.keys():
        fn = string.replace(fn,k,badnames[k])
    fp = os.path.join(wd,fn)
    f = open(fp+'.tex','w')

    rd = {}
    rd['title'] = eventdata['title']
    rd['date'] = eventdata['date']
    rd['venue'] = eventdata['venue']
    rd['secretary'] = eventdata['secretary']

    try: l = eventdata['configure']['language']
    except KeyError: l = 'English'
    rd['language'] = l
    rd['tables'] = []
    rd['separatorsfor'] = {'tables':'\n'}
    rd['currenttime'] = time.ctime(time.time())
    for cl in clses:
        d = {'separatorsfor':{'table':'\\\\\\hline\n'}}
        d['class'] = getclass(cl)
        if not heat_map[cl]:
            d['heat'] = ''
        else: d['heat'] = '\\Heat{} %s'%heat_map[cl][-1]

        d['table'] = []
        noflaps = len(laps[cl][0])
        d['tablepat'] = 'c|'+(noflaps-1)*'|c'
        d['lapshead'] = [r'\Start{}']+map(lambda n:'&\\Lap{} %s'%n,range(1,noflaps))
        ffl = 1
        for row in laps[cl]:
            dp = {'row':[],'separatorsfor':{'row':'&'}}
            for id,fl in row:
                if id:
                    if fl:
                        dp['row'].append('\\textbf{%s}'%(id))
                    else:
                        dp['row'].append('%s'%(id))
                else:
                    dp['row'].append('')
            d['table'].append(replace('#row#',dp))
        rd['tables'].append(replace(laps_table_latextmpl,d))
    for cl in []: #clses:
        if not heat_map[cl]: continue
        curheat = heat_map[cl][-1]
        
        rks = analyzer.getresorder(res[cl][curheat])
        d = {'separatorsfor':{'table1':'\\\\\n','table':'\\\\\n',
                              'notes':'; '},
             'heats':string.join(heat_map[cl],',')}
        d['class'] = cl
        d['heat'] = curheat
        d['table1'] = []
        d['table'] = []
        d['notes'] = [r'\ResNote']
        try: d['starttime'] = time.ctime(info[cl,curheat]['starttime'])
        except KeyError: d['starttime'] = r'\None'
        legend = []
        for id in rks:
            r = res[cl][curheat][id]
            sr = sumres[cl][id]
            lr=res2latex(r,d['notes'])
            p = parts[cl,'%s'%id]
            dp = {'place':'-','id':'%s'%id,'result':lr,'points':'-',
                  'name':'%s %s'%(p[0],p[1]),'from':p[2],
                  'bestresult':'-','sumpoints':'-'}
            if r['place']>0:
                dp['place'] = '%s'%r['place']
                dp['points'] = '%s'%r['points']
            if sr['place']>0:
                dp['bestresult'] = '%.1f/%.1f'%(sr['avgspeed'],sr['maxlapspeed'])
                dp['sumpoints'] = '%s'%sr['points']
            d['table1'].append(replace(inter_part1_latextmpl,dp))
            d['table'].append(replace(inter_part_latextmpl,dp))
            if r['notes']:
                for k in r['notes'].keys():
                    if k not in legend: legend.append(k)
        for l in legend:
            d['notes'].append('%s=%s'%(l,reccodelatexlabel[l]))
        if len(heat_map[cl])>1:
            rd['tables'].append(replace(inter_table_latextmpl,d))
        else:
            rd['tables'].append(replace(inter_table1_latextmpl,d))
    f.write(denormalize_str(replace(laps_doc_latextmpl,rd)))
    f.close()
    return fp,{'latex':'--interaction nonstopmode',
               'gv':'--media=a4',
               'dvipdfm':'-p a4',
               'dvips':'-q'}

report_map={'Participants':participants,
            'Intermediate':intermediate,
            'Endurance Full Final':fullfinal_endurance,
            'Full Final':fullfinal,
            'Short Final':shortfinal,
            'Check List':checklist,
            'Info Letter':infoletter,
            'Registration Letter':registrationletter,
            'Laps Protocol':lapsprotocol,
            }
