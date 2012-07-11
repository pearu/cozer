#!/usr/bin/env python
"""

buildmenus --- Build Menubar and Toolbar for Frame and much more.

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
import re,os

_isMenuBar=re.compile(r'.*?_wxMenuBar_?')
_isMenu=re.compile(r'.*?_wxMenu(_|\b)')
_isFrame=re.compile(r'.*?_wxFrame_?')
_isToolBar=re.compile(r'.*?_wxToolBar_?')

def isMenuBar(obj):
    return _isMenuBar.match(str(obj))
def isMenu(obj):
    return _isMenu.match(str(obj))
def isFrame(obj):
    return _isFrame.match(str(obj))
def isToolBar(obj):
    return _isToolBar.match(str(obj))

_bitmap_types={
    'bmp':wx.BITMAP_TYPE_BMP,
    'gif':wx.BITMAP_TYPE_GIF,
    'pcx':wx.BITMAP_TYPE_PCX,
    'png':wx.BITMAP_TYPE_PNG,
    #'pnm':wx.BITMAP_TYPE_PNM,
    'jpg':wx.BITMAP_TYPE_JPEG,
    'tiff':wx.BITMAP_TYPE_TIF,
    'any':wx.BITMAP_TYPE_ANY,
    }

def buildmenus(parent,patterns,topparent=None,mthname='',
               nosep=0,
               verbose=1,
               popup=0):
    """
    buildmenus()  --- builds menus and toolbars using the following rules:
            if parent is wx.Frame, a MenuBar and ToolBar will be created
            if parent is wx.MenuBar, Menus will be created
            if parent is wx.Menu, it will be filled with Items and Submenus
            if parent is wx.ToolBar, it will be filled with Tools
    topparent --- save the pointer of the top parent as the function
            buildmenus is called recursively. Internal.
    patterns --- a list of 2-tuples (name,dict). If empty tuple,
            insert a separator.
    name --- a string, is used to compose a method name mthname
    mthname --- name of the topparents method that is related
            to menu command 'id'. Internal. 
    dict --- a dictionary with the following optional keys:
            help --- help messages
            shelp --- short help messages
            menu --- label of the menu
            submenu --- has the same structure as patterns
            toolbar --- path to the tools bitmap file
            id --- menu command identifier. Internal.
            check --- the menu item is checkable and initialized to check.
            toggle --- the tool item is toggleable and initialized to toggle.
    nosep --- Internal.
    verbose --- Be verbose.
    popup --- Is dynamically created pop up menu.

    buildmenus creates additional objects/methods <name>Obj()/
    <name>[Enable,Toggle,GetState]() to the
    topparent for getting parents and id's of the menu/tool items.
    Returns 2-tuple ([have menubar],[have toolbar])
TODO:
***  support for other image files rather than bitmap; check that files exist
***  support for accelerator keys
    """
    ret = [0,0]
    if topparent is None:
        topparent = parent
    parent_this = str(parent.this)
    if isFrame(parent_this):
        mb = wx.MenuBar()
        ret = buildmenus(mb,patterns,topparent,mthname,verbose=verbose)
        if ret[0]:
            parent.SetMenuBar(mb)
        if ret[1]:
            tb = parent.CreateToolBar()
            buildmenus(tb,patterns,topparent,verbose=verbose)
    elif isMenuBar(parent_this):
        for pat in patterns:
            if not pat:
                if verbose:
                    print 'No separators for MenuBar'
                continue
            name,rules=pat
            if rules.has_key('menu'):
                menu = wx.Menu()
                parent.Append(menu,rules['menu'])
                if rules.has_key('submenu'):
                    ret2 = buildmenus(menu,rules['submenu'],topparent,mthname+name,verbose=verbose)
                    ret[1]=ret[1] or ret2[1]
                ret[0] = 1
            if rules.has_key('toolbar'): ret[1]=1
    elif isToolBar(parent_this):
        for pat in patterns:
            if not pat:
                if not nosep:
                    parent.AddSeparator()
                continue
            name,rules=pat
            help,shelp,ID,toggle = '','',-1,False
            if rules.has_key('id'): ID = rules['id']
            if rules.has_key('help'): help = rules['help']
            if rules.has_key('shelp'): shelp = rules['shelp']
            if rules.has_key('toggle'): toggle = True
            if rules.has_key('toolbar'):
                #if rules.has_key('menu') and not rules.has_key('id'):
                #    print 'buildmenus: id is needed if both menu and toolbar are specified:',mthname+name
                ext = rules['toolbar'][-3:]
                if _bitmap_types.has_key(ext):
                    bit = _bitmap_types[ext]
                else:
                    bit = _bitmap_types['any']
                tool = parent.AddSimpleTool(ID,wx.Bitmap(rules['toolbar'],bit),shelp,help,toggle=toggle)
                if toggle == True:
                    if rules['toggle']:
                        parent.ToggleTool(ID,True)
                    fmap = {'ToggleTool':['Toggle',1],'EnableTool':['Enable',1],
                            'GetToolState':['GetState',0]
                            }
                    for k in fmap.keys():
                        fk,f=fmap[k]
                        if f==0:
                            func = lambda p=getattr(parent,k),id=ID:p(id)
                        elif f==1:
                            func = lambda t,p=getattr(parent,k),id=ID:p(id,t)
                        n = '%s'%(mthname+name+fk)
                        if hasattr(topparent,n):
                            if verbose:
                                print 'buildmenus: unexpected method %s.%s'%(topparent.__class__,n)
                        else:
                            setattr(topparent,n,func)
                            if verbose:
                                print 'buildmenus: added method %s.%s'%(topparent.__class__,n)
            if rules.has_key('submenu'):
                buildmenus(parent,rules['submenu'],topparent,mthname+name,1,verbose=verbose)
                #buildmenus(parent,rules['submenu'],parent,mthname+name,1,verbose=verbose)
    elif isMenu(parent_this):
        for pat in patterns:
            if not pat:
                parent.AppendSeparator()
                continue
            name,rules=pat
            help,shelp,checkable= '','',False
            if rules.has_key('id'):
                ID = rules['id']
            else:
                ID = wx.NewId()
                rules['id'] = ID
            if rules.has_key('help'): help = rules['help']
            if rules.has_key('shelp'): shelp = rules['shelp']
            if rules.has_key('check'): checkable = True
            if rules.has_key('menu'):
                if rules.has_key('submenu'):
                    menu = wx.Menu()
                    parent.AppendMenu(ID,rules['menu'],menu,help)
                    ret2 = buildmenus(menu,rules['submenu'],topparent,mthname+name,verbose=verbose,popup=popup)
                    ret[1]=ret[1] or ret2[1]
                else:
                    parent.Append(ID,rules['menu'],help,checkable)
                    if checkable and rules['check']:
                        parent.Check(ID,True)
                    n = 'On%s'%(mthname+name)
                    if hasattr(topparent,n):
                        mth = getattr(topparent,n)
                        if os.name=='nt':
                            wx.EVT_MENU(topparent,ID,mth)
                        else:
                            if popup:
                                wx.EVT_MENU(parent,ID,mth)
                            else:
                                wx.EVT_MENU(topparent,ID,mth)
                    else:
                        if verbose:
                            print 'buildmenus: %s needs method %s'%(topparent.__class__,n)
                        
                ret[0] = 1
                if checkable:
                    n = '%sObj'%(mthname+name)
                    if hasattr(topparent,n):
                        if verbose:
                            print 'buildmenus: unexpected object %s.%s'%(topparent.__class__,n)
                    else:
                        obj = parent.FindItemById(ID)
                        setattr(topparent,n,obj)
                        if verbose:
                            print 'buildmenus: added object %s.%s'%(topparent.__class__,n)
            if rules.has_key('toolbar'): ret[1]=1
    else:
        print 'buildmenus: unrecognized parent:',parent.this
    return ret
