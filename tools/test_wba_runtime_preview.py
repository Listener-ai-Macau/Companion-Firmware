#!/usr/bin/env python3
"""Host journeys through real runtime+mounted resource+renderer, simulated I/O."""
import hashlib
import json
from pathlib import Path
from wba_runtime_preview import ROOT, OUT, IMAGE, Runtime, build

def main():
    dll=build();r=Runtime(dll=dll);checks=[];frames=[]
    def advance(ms):
        r.advance(r.now+ms);s=r.state()
        assert s['missingStates']==0,s
        return s
    def tap(x,y):
        r.command({'kind':'touch','down':True,'x':x,'y':y});advance(100)
        r.command({'kind':'touch','down':False,'x':x,'y':y});return advance(1100)
    def scroll_up():
        for y in (170,145,120,95,70):
            r.command({'kind':'touch','down':True,'x':100,'y':y});advance(60)
        r.command({'kind':'touch','down':False,'x':100,'y':70});return advance(1100)
    def scroll_down():
        for y in (70,95,120,145,170):
            r.command({'kind':'touch','down':True,'x':100,'y':y});advance(60)
        r.command({'kind':'touch','down':False,'x':100,'y':170});return advance(1100)
    def capture(label):
        raw=r.raw();p=OUT/(label+'.bin');p.write_bytes(raw)
        frames.append({'label':label,'sha256':hashlib.sha256(raw).hexdigest(),'state':r.state()})
    s=advance(1000);assert s['mounted'] and s['version']>=1,s
    s=advance(60000);assert s['lifeCommits']>15 and s['blinkCommits']>=2 and s['familyChanges']>=1,s
    checks.append('real C autonomous life/family/blink for 61s, all requested states mounted')
    for family in range(10):
        r.reset();r.command({'kind':'family','family':family});s=advance(11000)
        assert s['lifeCommits']>5 and s['failures']==0,s
        capture('family-'+str(family))
    checks.append('all ten families run authored life states without source fallback or missing keys')
    r.reset();advance(1000)
    r.command({'kind':'touch','down':True,'x':100,'y':100});advance(80)
    r.command({'kind':'touch','down':True,'x':175,'y':80});s=advance(1200)
    assert 'pointer_' in s['lastState'] or 'attention' in s['lastState'] or 'gaze' in s['lastState'],s
    r.command({'kind':'cancel'});advance(1200)
    checks.append('real drag routes to mounted gaze state, cancel releases touch')
    r.reset();advance(1000);family=r.state()['targetFamily']
    assert r.command({'kind':'action','action':5});s=advance(5400)
    assert s['surface']==1 and s['menuView']==16,s
    capture('menu-home')
    # Exercise every WBA grid tile against the production touch recognizer,
    # including inert gutters, whole-page swipes and restored parent pages.
    for page,views in ((0,(17,18,24,19)),(4,(25,26,20,23))):
        for x,y in ((100,80),(50,193),(100,118)):
            s=tap(x,y);assert s['menuView']==16 and s['menuPage']==page,s
        for (x,y),view in zip(((51,80),(149,80),(51,153),(149,153)),views):
            s=tap(x,y);assert s['menuView']==view,s
            r.command({'kind':'action','action':6});s=advance(1500)
            assert s['menuView']==16 and s['menuPage']==page,s
        s=scroll_up();assert s['menuPage']==4,s
    capture('menu-home-page2')
    s=scroll_down();assert s['menuPage']==0,s
    s=scroll_down();assert s['menuPage']==0,s
    s=tap(16,29);assert s['surface']==0,s
    assert r.command({'kind':'action','action':5});s=advance(5400)
    assert s['surface']==1 and s['menuPage']==0,s
    family=s['targetFamily']
    checks.append('2x2 root: all 8 tiles route correctly; inert gutters/footer, one-swipe pages, end clamps, parent restoration and header exit')
    s=tap(51,80);assert s['surface']==1 and s['menuView']!=16,s
    capture('menu-child')
    idle_menu=r.raw()
    assert s['menuView']==17,s
    assert r.command({'kind':'action','action':1});s=advance(2200)
    assert s['capturing'] and s['recording']==2,s
    active_menu=r.raw();capture('menu-recording-active')
    assert idle_menu[61*25:75*25]!=active_menu[61*25:75*25]
    assert idle_menu[16*25:61*25]==active_menu[16*25:61*25] and idle_menu[75*25:]==active_menu[75*25:]
    assert r.command({'kind':'action','action':2});s=advance(2200)
    assert not s['capturing'] and s['recording']==5,s
    assert r.raw()[61*25:75*25]!=active_menu[61*25:75*25]
    capture('menu-recording-saved')
    checks.append('recording menu follows actual capture/save state in localized native glyphs; surrounding rows unchanged')
    r.command({'kind':'action','action':6});s=advance(1500)
    assert s['surface']==1 and s['menuView']==16 and s['targetFamily']==family,s
    s=scroll_up()
    assert s['menuPage']==4,s
    s=tap(51,80);assert s['menuView']==25 and s['menuPage']==0,s
    capture('menu-storage')
    body=r.raw()[16*25:];calls=s['menuActionCalls']
    for xx,yy in ((100,49),(100,190),(195,74),(8,74)):
        s=tap(xx,yy);assert s['menuView']==25 and s['menuPage']==0,s
        assert s['menuActionCalls']==calls and r.raw()[16*25:]==body,s
    checks.append('open four-row submenu: header gap, footer and side gutters never act')
    # The confirmation buttons follow the visible bottom layout. Body, old
    # row positions and the narrow middle gutter must never clear recordings.
    s=tap(100,145);assert s['menuView']==27,s
    capture('menu-clear-confirmation')
    before=r.raw()[110*25:135*25]
    calls=s['menuActionCalls'];recordings=s['recordingCount']
    for xx,yy in ((100,100),(150,110),(100,179),(8,179),(190,179),(145,162),(145,197)):
        s=tap(xx,yy);assert s['menuView']==27,s
        assert r.raw()[110*25:135*25]==before,(xx,yy,s)
        assert s['menuActionCalls']==calls and s['recordingCount']==recordings,s
    s=tap(51,179);assert s['menuView']==25,s
    s=tap(100,145);assert s['menuView']==27,s
    s=tap(145,179);assert s['menuView']==27,s
    assert s['menuActionCalls']==calls+1 and s['recordingCount']==0,s
    assert r.raw()[110*25:135*25]!=before,s
    capture('menu-clear-complete')
    r.command({'kind':'action','action':6});s=advance(1500)
    assert s['menuView']==25,s
    checks.append('clear confirmation: bottom cancel returns to storage; only visible confirm button changes the real runtime catalog, body/old rows/gutter inert')
    r.command({'kind':'action','action':6});s=advance(1500)
    assert s['menuView']==16 and s['menuPage']==4,s
    s=tap(51,153);assert s['menuView']==20,s
    s=scroll_up();assert s['menuView']==20 and s['menuPage']==0,s
    s=tap(100,169);assert s['menuView']==28,s
    calls=s['menuActionCalls']
    for xx,yy in ((100,100),(145,110),(100,179),(145,162),(145,197)):
        s=tap(xx,yy);assert s['menuView']==28 and s['menuActionCalls']==calls,s
    s=tap(51,179);assert s['menuView']==20 and s['menuPage']==0 and s['menuActionCalls']==calls,s
    for xx,yy in ((100,49),(100,190),(8,169)):
        s=tap(xx,yy);assert s['menuView']==20 and s['menuPage']==0 and s['menuActionCalls']==calls,s
    s=tap(100,169);assert s['menuView']==28,s
    s=tap(145,179);assert s['menuView']==28 and s['menuActionCalls']==calls+1,s
    capture('menu-restore-dispatched')
    r.command({'kind':'action','action':6});s=advance(1500)
    assert s['menuView']==20,s
    checks.append('restore confirmation: only visible confirm dispatches, cancel restores parent, empty body and gutter never dispatch')
    s=scroll_down();assert s['menuView']==20 and s['menuPage']==0,s
    s=tap(100,65);assert s['menuView']==22,s
    s=tap(100,105);assert s['language']==0,s
    capture('menu-language-en')
    r.command({'kind':'action','action':6});s=advance(1500)
    assert s['menuView']==20,s
    r.command({'kind':'action','action':6});s=advance(1500)
    assert s['menuView']==16 and s['menuPage']==4,s
    r.command({'kind':'action','action':6});s=advance(1600)
    assert s['surface']==0,s
    checks.append('actual hold/tap/scroll: storage, parent page restoration, nested language switch and return home')
    # E-paper paging uses real touch samples and committed native frames.
    # A long drag cannot skip pages; nothing follows the moving finger.
    r.reset();advance(1000)
    assert r.command({'kind':'action','action':5});advance(5400)
    s=tap(51,80);assert s['menuView']==17 and s['menuPage']==0,s
    capture('menu-paged-recording-p0')
    def paged_swipe(up=True,settle=1100):
        before=r.raw();page=r.state()['menuPage'];version=r.state()['version']
        positions=(174,145,116,87,58) if up else (58,87,116,145,174)
        for yy in positions:
            r.command({'kind':'touch','down':True,'x':100,'y':yy});s=advance(40)
            assert s['menuPage']==page and s['version']==version and r.raw()==before,s
        r.command({'kind':'touch','down':False,'x':100,'y':positions[-1]})
        return advance(settle)
    r.command({'kind':'panel','latencyMs':1000})
    old=r.raw();calls=s['menuActionCalls'];version=s['version']
    s=paged_swipe(settle=10)
    assert s['menuPage']==4 and s['panelPending'] and r.raw()==old,s
    # A contact beginning on the old page while BUSY stays invalid even if
    # it is released after the new page has visibly committed.
    r.command({'kind':'touch','down':True,'x':100,'y':74});advance(80)
    s=advance(1100);assert not s['panelPending'] and s['version']==version+1,s
    r.command({'kind':'touch','down':False,'x':100,'y':74});s=advance(200)
    assert s['menuPage']==4 and s['menuActionCalls']==calls and r.raw()!=old,s
    capture('menu-paged-recording-p4')
    final=r.raw();version=s['version']
    s=paged_swipe();assert s['menuPage']==4 and s['version']==version and r.raw()==final,s
    for xx,yy in ((100,115),(100,159),(100,190)):
        s=tap(xx,yy);assert s['menuPage']==4 and s['menuActionCalls']==calls and r.raw()==final,s
    s=paged_swipe(False);assert s['menuPage']==0,s
    r.command({'kind':'panel','latencyMs':1000,'fail':True})
    old=r.raw();failed=s['failures']
    s=paged_swipe(settle=1060)
    assert s['menuPage']==4 and s['failures']==failed+1 and r.raw()==old,s
    s=tap(100,74) # Begins before retry succeeds: must never toggle Stop on silence.
    assert s['menuActionCalls']==calls and s['menuPage']==4,s
    s=advance(1400);assert not s['panelPending'] and r.raw()!=old,s
    s=tap(100,74);assert s['menuActionCalls']==calls+1 and s['menuPage']==4,s
    capture('menu-paged-recording-setting-after-retry')
    checks.append('e-paper whole pages: no follow-finger renders, 0/4 without skipped or overlapping rows, one commit per swipe, end clamp, empty last-page targets inert, BUSY/cross-frame/failed-retry touches blocked, fresh setting works after successful retry')
    r.reset();advance(1000);assert r.command({'kind':'action','action':1});s=advance(2000)
    assert s['capturing'] and s['recording']==2,s
    families=s['familyChanges'];wave,life=s['waveCommits'],s['lifeCommits'];s=advance(60000)
    assert s['waveCommits']>wave+10 and s['lifeCommits']>life+3 and s['blinkCommits']>=2,s
    assert s['familyChanges']>families,s
    capture('recording')
    r.command({'kind':'panel','latencyMs':1000,'fail':True});s=advance(12000)
    assert s['failures']==1 and s['waveCommits']>wave+15,s
    assert r.command({'kind':'action','action':2});s=advance(3000)
    assert not s['capturing'] and s['recording']==5 and s['recordingCount']==1,s
    checks.append('60s simulated capture: independent wave/life/blink and autonomous family changes, slow-panel failed-commit recovery, stop/save')
    for latency in (500,600,1000):
        r.reset();r.command({'kind':'panel','latencyMs':latency});advance(1500)
        assert r.command({'kind':'action','action':1});s=advance(65000)
        assert s['capturing'] and s['waveCommits']>15 and s['lifeCommits']>8,s
        assert s['familyChanges']>=1 and s['blinkCommits']>=2 and s['failures']==0,s
    checks.append('500/600/1000ms panels: second-by-second recording timer cannot starve life, natural blink or family transitions')
    r.reset();s=advance(181000)
    assert s['surface']==2 and r.raw()==bytes([255])*5000,s
    r.command({'kind':'action','action':3});s=advance(1500)
    assert s['surface']==0 and r.raw()!=bytes([255])*5000,s
    checks.append('real inactivity timeout clears display and simulated pickup wakes home')
    receipt={'result':'PASS_HOST_RUNTIME_RESOURCE_JOURNEYS','hardwareAcceptance':'NOT_RUN',
        'scope':'Production C coordinator/resource mount/renderer with explicit simulated peripheral callbacks; not capture, radio, panel or full-chain acceptance',
        'checks':checks,'frames':frames,'resource_image_sha256':hashlib.sha256(IMAGE.read_bytes()).hexdigest(),
        'dll_sha256':hashlib.sha256(dll.read_bytes()).hexdigest(),
        'source_sha256':json.loads((OUT/'build-result.json').read_text())['source_sha256']}
    receipt['source_sha256'][Path(__file__).relative_to(ROOT).as_posix()]=hashlib.sha256(Path(__file__).read_bytes()).hexdigest()
    (OUT/'journey-result.json').write_text(json.dumps(receipt,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    print(receipt['result']);print('\n'.join(checks));return 0

if __name__=='__main__':raise SystemExit(main())
