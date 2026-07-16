# -*- coding: utf-8 -*-
# Drive legacy cozer to a notebook page and screenshot it (py2 / wx 2.8), for use
# as a visual reference when rebuilding the new-cozer GUI. Run via
# legacy/screenshot_legacy.sh (which sets up Xvfb + the env).
#
#   env: PAGE (default Timer), RACE (default 0), SHOT (output png); argv[1]=event
import os, sys
import wx
import cozer

OUT = os.environ.get('SHOT', '/tmp/cozer_page.png')
PAGE = os.environ.get('PAGE', 'Timer')
RACE = int(os.environ.get('RACE', '0'))


class App(cozer.MyApp):
    def OnInit(self):
        cozer.MyApp.OnInit(self)          # builds MainFrame, loads sys.argv[1]
        wx.CallLater(2500, self.nav)
        return True

    def nav(self):
        try:
            f = self.GetTopWindow()
            f.SetSize((1120, 650))
            if PAGE in f.pagedict:
                i = f.pagedict[PAGE]
                f.nb.SetSelection(i)
                pg = f.nb.pages[i]
                if hasattr(pg, 'Entering'):
                    pg.Entering()
                if PAGE == 'Timer' and f.eventdata.get('races'):
                    f.currentRace = RACE
                    try:
                        pg.racechoice.SetSelection(RACE)
                    except Exception:
                        pass
                    pg.TimerWin()
            f.Refresh()
            wx.SafeYield()
        except Exception, e:
            sys.stderr.write('nav error: %s\n' % e)
        wx.CallLater(2500, self.shoot)

    def shoot(self):
        os.system('import -window root %s' % OUT)
        sys.stderr.write('saved %s\n' % OUT)
        self.ExitMainLoop()


if __name__ == '__main__':
    App(0).MainLoop()
