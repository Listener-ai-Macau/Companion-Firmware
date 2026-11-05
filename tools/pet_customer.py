"""Use the public headless pet surface without a browser or computer automation.

Only ordinary screen contacts, public simulated physical controls and committed
native frames are available. This client never reads source/build/old feedback,
changes settings internally, captures real audio or operates a real device.
"""
import argparse
import base64
from datetime import datetime
import hashlib
import io
import json
from pathlib import Path
import time
from urllib.parse import urlsplit
from urllib.request import Request,urlopen
import uuid
from PIL import Image,ImageDraw,ImageFont


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--endpoint',default='http://127.0.0.1:8894')
    p.add_argument('--output',type=Path,required=True)
    sub=p.add_subparsers(dest='command',required=True)
    sub.add_parser('controls',help='See the ordinary public simulated controls')
    sub.add_parser('look',help='See the current native200x200 committed display')
    watch=sub.add_parser('watch',help='Observe actual successive commits, without interpolation')
    watch.add_argument('--seconds',type=float,default=3)
    touch=sub.add_parser('touch',help='Touch a coordinate chosen from the displayed screen')
    touch.add_argument('x',type=int);touch.add_argument('y',type=int)
    touch.add_argument('--hold-ms',type=int,default=100)
    touch.add_argument('--watch-seconds',type=float,default=6)
    drag=sub.add_parser('drag',help='Move an ordinary held contact, then release')
    for k in ['x0','y0','x1','y1']:drag.add_argument(k,type=int)
    drag.add_argument('--duration-ms',type=int,default=1000)
    drag.add_argument('--watch-seconds',type=float,default=6)
    press=sub.add_parser('press',help='Use a public simulated physical control by name')
    press.add_argument('control');press.add_argument('--watch-seconds',type=float,default=6)
    a=p.parse_args();url=urlsplit(a.endpoint)
    if url.scheme!='http' or url.hostname!='127.0.0.1' or url.username or url.password or url.path not in ('','/') or url.query or url.fragment:
        p.error('Only the explicitly local customer surface is supported')
    endpoint=a.endpoint.rstrip('/');out=a.output.resolve();out.mkdir(parents=True,exist_ok=True)
    def call(path,data=None):
        req=Request(endpoint+path,data=None if data is None else json.dumps(data).encode(),
                    headers={'Content-Type':'application/json'})
        with urlopen(req,timeout=5) as reply:return json.load(reply)
    if a.command=='controls':print(json.dumps(call('/controls'),ensure_ascii=False));return
    seconds=getattr(a,'seconds',getattr(a,'watch_seconds',0))
    if not 0<=seconds<=10:p.error('Observation must be0..10seconds')
    for name in ['x','y','x0','y0','x1','y1']:
        if hasattr(a,name) and not 0<=getattr(a,name)<200:p.error('Screen coordinates must be0..199')
    if hasattr(a,'hold_ms') and not 50<=a.hold_ms<=5000:p.error('Hold must be50..5000ms')
    if hasattr(a,'duration_ms') and not 100<=a.duration_ms<=5000:p.error('Drag must be100..5000ms')
    stamp=datetime.now().strftime('%Y%m%d-%H%M%S-%f')+'-'+uuid.uuid4().hex[:6]
    frames=[];last=None;session=None
    def capture():
        nonlocal last,session
        s=call('/state');key=(s['sessionId'],s['version'],s['frameSha256'])
        if session is None:session=s['sessionId']
        if session!=s['sessionId']:raise RuntimeError('Session changed; stop rather than mixing experience')
        if key==last or not s['version']:return
        png=base64.b64decode(s.pop('png'));im=Image.open(io.BytesIO(png));im.load()
        if im.size!=(200,200) or im.mode!='1':raise RuntimeError('Not a native200x200 black/white frame')
        if hashlib.sha256(im.tobytes()).hexdigest()!=s['frameSha256']:raise RuntimeError('Frame hash mismatch')
        name=f'{stamp}-{len(frames):02d}-v{s["version"]}.png'
        path=out/name;path.write_bytes(png)
        frames.append({**s,'image':str(path),'observedAtLocal':datetime.now().astimezone().isoformat(timespec='milliseconds')})
        last=key
    def observe(duration):
        end=time.monotonic()+duration
        while True:
            capture()
            remaining=end-time.monotonic()
            if remaining<=0:break
            time.sleep(min(.1,remaining))
    def contact(down,x,y):
        return call('/input',{'kind':'touch','down':down,'x':x,'y':y})
    capture();result=None
    if a.command=='touch':
        result=contact(True,a.x,a.y)
        try:observe(a.hold_ms/1000)
        finally:contact(False,a.x,a.y)
    elif a.command=='drag':
        result=contact(True,a.x0,a.y0)
        try:
            steps=max(2,a.duration_ms//50);start=time.monotonic()
            for i in range(1,steps+1):
                pause=start+a.duration_ms*i/steps/1000-time.monotonic()
                if pause>0:observe(pause)
                contact(True,round(a.x0+(a.x1-a.x0)*i/steps),round(a.y0+(a.y1-a.y0)*i/steps))
        finally:contact(False,a.x1,a.y1)
    elif a.command=='press':result=call('/input',{'kind':'control','control':a.control})
    observe(seconds)
    receipt={'scope':'Actual committed native frames; background AI customer session; simulated touch/IMU/recording/storage/panel. No browser or hardware.',
             'action':{k:v for k,v in vars(a).items() if k not in ['output','endpoint']},
             'inputAcceptance':result,'frames':frames}
    if frames:
        # Preserve every observed commit in order, full native size. Labels are
        # outside the screen; no face repaint, resize or temporal interpolation.
        cols=min(4,len(frames));rows=(len(frames)+cols-1)//cols
        sheet=Image.new('RGB',(cols*212,rows*228),'#f4f2eb');draw=ImageDraw.Draw(sheet)
        font=ImageFont.truetype('C:/Windows/Fonts/segoeui.ttf',11)
        for i,s in enumerate(frames):
            x=i%cols*212;y=i//cols*228
            sheet.paste(Image.open(s['image']).convert('RGB'),(x,y))
            draw.text((x,y+202),f'v{s["version"]} | {s["nowMs"]}ms',font=font,fill='black')
        path=out/(stamp+'-sequence.png');sheet.save(path);receipt['nativeSequence']=str(path)
    path=out/(stamp+'-experience.json');path.write_text(json.dumps(receipt,ensure_ascii=False,indent=2)+'\n',encoding='utf8')
    summary={k:v for k,v in receipt.items() if k!='frames'}
    summary.update(receipt=str(path),frames=[{k:s[k] for k in ['version','nowMs','image','frameSha256','auxiliaryStatus','waitingForDisplay']} for s in frames])
    print(json.dumps(summary,ensure_ascii=False))


if __name__=='__main__':main()
