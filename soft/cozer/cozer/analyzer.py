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
import string,pprint,sys
from prefs import *

def res2str(res):
    ret = '%s/%s A/M=%s/%s km/h'%\
           (nth(res['place']),res['points'],res['avgspeed'],res['maxlapspeed'])
    laps,penlapsleft,lapsleft = res['lapinfo']
    ret = ret + ' Laps/Pen/Left=%s/%s/%s'%res['lapinfo']
    if res['notes']:
        for k in res['notes'].keys():
            n = string.join(res['notes'][k],',')
            if n: ret = ret + ' %s(%s)'%(k,n)
            else: ret = ret + ' %s'%(k)                
    return ret

def getresorder(res):
    rks = []
    for k in res.keys():
        if res[k]['place']>0: rks.append([res[k]['place'],k])
        else: rks.append([99999,k])
    rks.sort()
    rks = map(lambda i:i[1],rks)
    return rks

def getsumresorder(res):
    ids = []
    for id in res.keys():
        ids.append([res[id]['points'],res[id]['avgspeed'],res[id]['maxlapspeed'],id])
    ids.sort()
    ids.reverse()
    return map(lambda i:i[3],ids)

def sumanalyze(heats,res,sheats):
    invres = {}
    for h in heats:
        for id in res[h].keys():
            if not invres.has_key(id): invres[id]={}
            invres[id][h] = res[h][id]
    sumres = {}
    for id in invres.keys():
        points = []
        bestavg = -1
        bestmax = -1
        for h in heats:
            r = invres[id][h]
            if r['place']>0:
                points.append(r['points'])
                bestavg = max(bestavg,r['avgspeed'])
                bestmax = max(bestmax,r['maxlapspeed'])
        sumpoints = -1
        if points:
            points.sort()
            points.reverse()
            sumpoints = reduce(lambda x,y:x+y,points[:sheats],0)
        sumres[id] = {'points':sumpoints,'avgspeed':bestavg,'maxlapspeed':bestmax}
    i = 0
    for id in getsumresorder(sumres):
        if sumres[id]['points']>=0:
            i = i + 1
            sumres[id]['place'] = i
        else:
            sumres[id]['place'] = -1
    return sumres

def analyze(heat,record,scoringsystem = []):
    """
    Input:
      info = {racetime:<float>,course:[<lap1len>,..]}
      rec = {id1:[(<code>,<time/laptime>,..),..]}
      <code> = 1,2:laptime; 3:interruption; 10:penlap; 11:disqualification
    Output:

    """
    info,rec = record
    course = info['course']
    if not info.has_key('racetime'):
        racetime = 1
        for id in rec.keys():
            t = 0
            for m in rec[id]:
                if abs(m[0]) in [1,2]:
                    t = t + m[1]
                else:
                    racetime = max(racetime,m[1])
            racetime = max(racetime,t)
        info['racetime'] = 1.05 * racetime
    racetime = info['racetime']

    isrestarted = (heat and heat[-1]=='r')
    isqualification = (heat and heat[-1]=='q')
    istimetrial = (heat and heat[-1]=='t')
    preres = []
    for id in rec.keys():
        penlaps = 0
        stopind = -1
        t = 0
        laps = 0
        ignorelaps = 0
        interruption = 0
        disqualification = 0
        qualification = 3
        didntstart = 0
        notes = {}
        for m in rec[id]:
            if m[0]==4:
                if m[1] <= racetime:
                    penlaps = penlaps + 1
                    n = string.strip(m[2])
                    k = invreccodemap[m[0]]
                    if not notes.has_key(k): notes[k] = []
                    if n: notes[k].append(n)
        lapsrequired = len(course)
        maxlapspeed = 0
        avgspeed = 0
        distcovered = 0
        lapslost = 0
        penlapsleft = penlaps
        pastafterstoppage = 0
        esttime = 0
        lapstime = []
        dt = 0
        for m in rec[id]:
            if abs(m[0]) in [1,2]:
                if (not ignorelaps) and t + m[1] <= racetime and laps<lapsrequired + penlaps:
                    t = t + m[1]
                    if m[0]<0:
                        dt = dt + m[1]
                        continue
                    elif dt: dt = dt + m[1]
                    else: dt = m[1]
                    if lapslost:
                        lapslost = lapslost - 1
                    else:
                        laps = laps + 1
                        li = min(len(course),laps)-1
                        if penlaps and laps > lapsrequired:
                            penlapsleft = penlapsleft - 1
                        else:
                            distcovered = distcovered + course[li]
                        lapspeed = round(3.6*course[li]/float(dt),roundopt)
                        if lapspeed>maxlapspeed:
                            maxlapspeed = lapspeed
                        esttime = round(3.6*course[min(len(course)-1,li+1)]/float(maxlapspeed),roundopt)
                        lapstime.append(t)
                    dt = 0
                else:
                    pastafterstoppage = 1
                    ignorelaps = 1
            elif m[0]==3:
                if m[1] <= racetime and laps<lapsrequired + penlaps:
                    lapslost = lapslost + 1
                    n = string.strip(m[2]) 
                    k = invreccodemap[m[0]]
                    if not notes.has_key(k): notes[k] = []
                    if n: notes[k].append(n)
            elif m[0]==4: # penalty lap
                pass
            elif m[0]==10:
                didntstart = 1
                n = string.strip(m[2]) 
                k = invreccodemap[m[0]]
                if not notes.has_key(k): notes[k] = []
                if n and n not in notes[k]:
                    notes[k].append(n)
            elif m[0]==11:
                if m[1] <= racetime:
                    interruption = 1
                    n = string.strip(m[2])
                    k = invreccodemap[m[0]]
                    if not notes.has_key(k): notes[k] = []
                    if n and n not in notes[k]:
                        notes[k].append(n)
            elif m[0]==12:
                disqualification = 1
                n = string.strip(m[2]) 
                k = invreccodemap[m[0]]
                if not notes.has_key(k): notes[k] = []
                if n and n not in notes[k]:
                    notes[k].append(n)
            elif m[0]==13: # yellow card
                n = string.strip(m[2]) 
                if n:
                    k = invreccodemap[m[0]]
                    if not notes.has_key(k): notes[k] = []
                    if n not in notes[k]:
                        notes[k].append(n)
            elif m[0]==14: # red card
                disqualification = 1
                n = string.strip(m[2]) 
                k = invreccodemap[m[0]]
                if not notes.has_key(k): notes[k] = []
                if n and n not in notes[k]:
                    notes[k].append(n)
            elif m[0]==20:
                n = string.strip(m[2]) 
                if n:
                    k = invreccodemap[m[0]]
                    if not notes.has_key(k): notes[k] = []
                    if n not in notes[k]:
                        notes[k].append(n)
            elif m[0]==30:
                qualification = 1
                n = string.strip(m[2]) 
                k = invreccodemap[m[0]]
                if not notes.has_key(k): notes[k] = []
                if n and n not in notes[k]:
                    notes[k].append(n)
            elif m[0]==31:
                qualification = 2
                n = string.strip(m[2]) 
                k = invreccodemap[m[0]]
                if not notes.has_key(k): notes[k] = []
                if n and n not in notes[k]:
                    notes[k].append(n)
            else:
                print 'analyzer.analyze: unused code',m[0]
                
        if laps:
            avgspeed = round(3.6*distcovered/float(t),roundopt)
        if penlapsleft:
            penlapavgspeed = round(3.6*(distcovered-penlapsleft*course[li])/float(t),roundopt)
        else:
            penlapavgspeed = avgspeed
        lapsleft = lapsrequired - laps + penlaps
        code = 10*didntstart+interruption+100*disqualification
        if lapsleft and (not pastafterstoppage) and (code==0):
            if t+2.5*esttime<racetime and not istimetrial:
                if laps:
                    Warning('Appended IR mark for %s'%id)
                    code = 1
                    insertmark(rec[id],11,t+2.5*esttime,'')
                    k = invreccodemap[11]
                    if not notes.has_key(k): notes[k] = []
                else:
                    Warning('Appended DS mark for %s'%id)
                    code = 10
                    insertmark(rec[id],10,t+2.5*esttime,'')
                    k = invreccodemap[10]
                    if not notes.has_key(k): notes[k] = []
        #0,1,10,11,100,101,110,111
        preres.append((code,
                       qualification,
                       lapsleft,-penlapavgspeed,
                       -avgspeed,-maxlapspeed,lapstime,
                       (pastafterstoppage,penlapsleft,laps),
                       id,notes))
    preres.sort()
    
    requiredlapscoef = 0.70           # U.I.M. 2000 311.02.1
    restartrequiredlapscoef = 0.35    # U.I.M. 2000 311.02.7
    requiredlaps4pointscoef = 0.75     # U.I.M. 2000 318.02_1, must cross the lane
    minrequiredlaps = requiredlapscoef * len(course)
    minrestartrequiredlaps = restartrequiredlapscoef * len(course)
    leaderlaps = preres[0][7][2] - preres[0][7][1]
    leadertime = 0
    if preres[0][6]:
        leadertime = preres[0][6][-1]
    minlaps4points = max(1,requiredlaps4pointscoef*leaderlaps)
    
    if 1:
        minrequiredlaps,minrestartrequiredlaps,minlaps4points=int(minrequiredlaps),int(minrestartrequiredlaps),int(minlaps4points)
    else: # Exception in EC2001
        import math
        minrequiredlaps,minrestartrequiredlaps=int(minrequiredlaps),int(minrestartrequiredlaps)
        minlaps4points = int(math.ceil(minlaps4points))

    needsrestart = (not isrestarted) and leaderlaps < minrequiredlaps
    if needsrestart:
        Info('Restart is required by U.I.M. rule 311.02.1: leaderslaps,minrequiredlaps=',leaderlaps,minrequiredlaps)

    res = {}
    i = -1
    for item in preres:
        i = i + 1
        ip = min(i,len(scoringsystem)-1)
        code,qualification,lapsleft,penlapavgspeed,avgspeed,maxlapspeed,lapstime,(pastafterstoppage,penlapsleft,laps),id,notes = item
        penlapavgspeed,avgspeed,maxlapspeed=-penlapavgspeed,-avgspeed,-maxlapspeed
        points = -1
        place = -1
        ll = 0
        lasttime = 0
        if lapstime:
            lasttime = lapstime[-1]
            for t in lapstime:
                ll = ll + 1
                if t>leadertime:
                    lasttime = t
                    break
            if ll<len(lapstime):
                laps = laps - (len(lapstime)-ll)
                lapsleft = lapsleft + (len(lapstime)-ll)
                Info('You must disable last %s lapmarks for %s'%(len(lapstime)-ll,id))
        totallaps = laps - penlapsleft
        getspoints = (not lapsleft) or (pastafterstoppage) or (lasttime>leadertime)
        if isqualification:
            if qualification==3 and code==0:
                Info("Check %s for qualification or nonqualification or didn't start."%(id))
            if (code==0 and getspoints):
                place = i+1
        elif code==0:
            if getspoints:
                place = i+1
                points = 0
                if isrestarted:
                    if totallaps >= minlaps4points:
                        if totallaps >= minrestartrequiredlaps:
                            points = scoringsystem[ip]
                        elif totallaps > 0:
                            points = 0.5*scoringsystem[ip]
                else:
                    if totallaps >= minlaps4points:
                        points = scoringsystem[ip]
            else:
                if lapsleft:
                    Info('Check %s for interruption or insert a lapmark after stoppage.'%(id))                
        res[id] = {}
        if istimetrial or isqualification:
            res[id]['points'] = 0
        else:
            res[id]['points'] = points
        res[id]['place'] = place
        res[id]['avgspeed'] = avgspeed
        res[id]['maxlapspeed'] = maxlapspeed
        res[id]['lapinfo'] = laps,penlapsleft,lapsleft
        res[id]['notes'] = notes

    return res

def transpose(l):
    o=[]
    for i in range(len(l)):
        for j in range(len(l[i])):
            try: o[j].append(l[i][j])
            except: o.append([l[i][j]])
    return o

def countlaps(heat,record):
    """
    Input:
      info = {racetime:<float>,course:[<lap1len>,..]}
      rec = {id1:[(<code>,<time/laptime>,..),..]}
      <code> = 1,2:laptime; 3:interruption; 10:penlap; 11:disqualification
    Output:

    """
    info,rec = record
    course = info['course']
    if heat == -1:
        rks = rec.keys()
        rks.sort()
        laps = [map(lambda k:(k,1),rks)]
        for i in range(len(course)):
            laps.append(map(lambda k:(0,0),rks))
        return transpose(laps)
    if not info.has_key('racetime'):
        racetime = 1
        for id in rec.keys():
            t = 0
            for m in rec[id]:
                if abs(m[0]) in [1,2]:
                    t = t + m[1]
                else:
                    racetime = max(racetime,m[1])
            racetime = max(racetime,t)
        racetime = 1.05 * racetime
    else:
        racetime = info['racetime']
    sarr = []
    rks = rec.keys()
    rks.sort()
    for id in rks:
        t0 = 0
        for t in gettimes(rec[id]):
            t0 = t0 + t
            sarr.append([t0,id])
    sarr.sort()
    idseq = map(lambda s:s[1],sarr)
    
    laps = [map(lambda k:(k,1),rks)]
    i = -1
    for id in idseq:
        i = i + 1
        fl = sarr[i][0]<=racetime
        flag = 1
        for l in laps:
            if ((id,1) not in l) and ((id,0) not in l):
                l.append((id,fl))
                flag = 0
                break
        if flag:
            laps.append([(id,fl)])
    for i in range(1,len(laps)):
        laps[i] = laps[i] + map(lambda i:(0,0),range(len(laps[0])-len(laps[i])))
    return transpose(laps)
    
