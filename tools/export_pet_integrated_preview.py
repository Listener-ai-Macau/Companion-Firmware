"""Export the affected P16 interaction/menu path, with simulated peripherals."""
from pathlib import Path
from datetime import datetime
import ctypes, hashlib, json, shutil
from PIL import Image, ImageDraw, ImageFont
from wba_runtime_preview import Runtime

ROOT=Path(__file__).resolve().parents[1]
BASE=ROOT/'.cache/screen-art-polish-20261011'
OUT=BASE/'studio-p16-reviewed'
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()

def main():
    if OUT.exists(): raise RuntimeError('Immutable export already exists')
    shutil.copytree(BASE/'studio-p15',OUT)
    receipt=json.loads((BASE/'preview-build-p16-final/build-result.json').read_bytes())
    runtime=Runtime(BASE/'source-p16-final/.cache/external-ui68/ui-partition.bin',
        BASE/'preview-build-p16-final/wba-runtime-preview.dll',seed=17)
    runtime.lib.cp_panel(480,0);runtime.lib.cp_language(1)
    runtime.lib.cp_power_state.argtypes=(ctypes.c_uint,)*3
    runtime.lib.cp_power_state.restype=None
    runtime.lib.cp_clock(10,28)
    # Quiet is a runtime setting, not a PCM playback API. The host speaker
    # adapter never emits audio; no real microphone/charger/link is asserted.
    frames=[];timeline=[];observations=[]
    def advance(ms):
        until=runtime.now+ms
        while runtime.now<until:
            runtime.advance(min(until,runtime.now+100))
            frames.append(Image.frombytes('1',(200,200),runtime.raw()))
            timeline.append(runtime.state())
    def tap(x,y):
        runtime.lib.cp_touch(1,x,y);advance(120)
        runtime.lib.cp_touch(0,x,y);advance(120)
    def save(name,label):
        p=OUT/(name+'.png');Image.frombytes('1',(200,200),runtime.raw()).save(p)
        observations.append(dict(name=name,label=label,file=p.name,state=runtime.state(),sha256=sha(p)))
    advance(980)
    tap(100,74);advance(600)
    active=runtime.state()
    if not active['replyPending']:raise RuntimeError('Head response not active')
    generation=active['reactionGeneration']
    tap(52,139)
    queued=runtime.state()
    if not queued['deferredPetTap'] or queued['reactionGeneration']!=generation:
        raise RuntimeError('New tap replaced active phrase instead of coalescing')
    save('queued-touch','回应期间再触摸')
    advance(13000)
    settled=runtime.state()
    if settled['replyPending'] or settled['deferredPetTap']:
        raise RuntimeError('Coalesced response did not settle')
    if settled['reactionGeneration']!=generation+1:
        raise RuntimeError('Deferred touch was not handled exactly once')
    frames[0].save(OUT/'integrated-touch-response.gif',save_all=True,append_images=frames[1:],
        duration=100,loop=0,optimize=False,disposal=2)
    frames.clear()
    runtime.lib.cp_action(5);advance(6500)
    if runtime.state()['surface']!=1:raise RuntimeError('Visible long hold did not enter menu')
    save('actual-menu','长按进入真实菜单')
    tap(90,54);advance(1600)
    save('actual-submenu','点击子菜单')
    tap(12,12);advance(1600)
    save('actual-menu-back','菜单返回')
    runtime.lib.cp_action(6);advance(2000)
    save('actual-home-return','返回宠物')
    # Each supplied flag flows through production status(), not authored PNG
    # selection. These are actual C-rendered state frames with simulated data.
    for name,label,values in [('actual-charge','充电标记',(3860,78,1<<22)),
                             ('actual-update','升级标记',(3860,78,1<<23)),
                             ('actual-unknown','无测量数据',(0,255,0))]:
        runtime.lib.cp_power_state(*values);advance(1800);save(name,label)
    if runtime.state()['failures'] or runtime.state()['missingStates']:
        raise RuntimeError('Affected native path failed to render')
    state_frames_final=runtime.state()
    # Review the two cancellation boundaries affected by the new single slot.
    def restart():
        runtime.reset();runtime.lib.cp_panel(480,0);runtime.lib.cp_language(1);advance(980)
    restart();tap(100,74);advance(600);tap(52,139)
    until=runtime.now+14000
    while runtime.state()['replyPending'] and runtime.now<until:advance(100)
    before_fresh=runtime.state()
    if not before_fresh['deferredPetTap']:raise RuntimeError('Settle gap not reached')
    tap(100,129)
    after_fresh=runtime.state()
    if after_fresh['deferredPetTap']:raise RuntimeError('Fresh tap left obsolete intent queued')
    advance(13000)
    after_settle=runtime.state()
    if after_settle['reactionGeneration']!=before_fresh['reactionGeneration']+1:
        raise RuntimeError('An obsolete queued tap replayed')
    restart();tap(100,74);advance(600);tap(52,139)
    runtime.lib.cp_action(5);advance(6500)
    menu_cancel=runtime.state()
    if menu_cancel['surface']!=1 or menu_cancel['deferredPetTap'] or menu_cancel['replyPending']:
        raise RuntimeError('Menu did not retire deferred pet intent')
    restart();tap(100,74);advance(600);tap(52,139)
    runtime.lib.cp_action(1);advance(2400)
    recording_cancel=runtime.state()
    if not recording_cancel['capturing'] or recording_cancel['deferredPetTap']:
        raise RuntimeError('Recording did not own and clear deferred intent')
    font=ImageFont.truetype('C:/Windows/Fonts/msyh.ttc',14)
    sheet=Image.new('RGB',(928,536),'#f6f3ec');draw=ImageDraw.Draw(sheet)
    for i,item in enumerate(observations):
        x=16+(i%4)*228;y=12+(i//4)*264
        sheet.paste(Image.open(OUT/item['file']).convert('RGB'),(x,y+25))
        draw.text((x,y),item['label'],fill='#293a33',font=font)
    sheet.save(OUT/'integrated-functions.png')
    result=dict(result='AFFECTED_NATIVE_C_TOUCH_QUEUE_MENU_AND_STATUS_RENDERED',
        createdAtLocal=datetime.now().isoformat(),design='P16',dllSha256=receipt['dllSha256'],
        resourceImageSha256=receipt['resourceImageSha256'],activeGeneration=generation,
        queued=queued,settled=settled,observations=observations,
        finalState=state_frames_final,scope='SIMULATED_PERIPHERALS_PRODUCTION_C',
        freshTapSupersedesQueued=dict(before=before_fresh,after=after_fresh,settled=after_settle),
        menuCancelsQueued=menu_cancel,recordingCancelsQueued=recording_cancel,
        armFirmwareBuilt=False,installed=False,boardAccess=False,audioPlayback=False,
        physicalGhosting='NOT_MODELED',sceneEmotionRouting='NOT_INTEGRATED',
        chatBackend='RESERVED_NOT_INTEGRATED',testsAdded=False,testsRun=False)
    (OUT/'integrated-review.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    (OUT/'integrated-timeline.json').write_text(json.dumps(timeline,ensure_ascii=False)+'\n',encoding='utf-8')
    print(json.dumps({k:result[k] for k in ('result','design','dllSha256')},ensure_ascii=False))

if __name__=='__main__':main()
