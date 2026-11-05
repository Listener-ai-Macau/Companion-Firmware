"""Export native C pet art in motion at an explicit, unaccelerated panel model."""
from pathlib import Path
import argparse,hashlib,json
from PIL import Image,ImageDraw,ImageFont
import wba_runtime_preview as preview


def main():
    p=argparse.ArgumentParser(description=__doc__)
    for arg in ('resources','host-dll','output'):p.add_argument('--'+arg,type=Path,required=True)
    args=p.parse_args();out=args.output.resolve();out.mkdir(parents=True,exist_ok=True)
    image=args.resources.resolve()/'ui-partition.bin';dll=args.host_dll.resolve()
    font=ImageFont.truetype('C:/Windows/Fonts/msyh.ttc',16)
    small=ImageFont.truetype('C:/Windows/Fonts/msyh.ttc',14)
    sequences=[];keyframes={}
    for name,label,point in (('pat','摸头 · 舒服后看向你',(100,60)),('cheek','脸颊 · 害羞后偷偷看',(45,145))):
        r=preview.Runtime(image,dll,seed=17);r.lib.cp_clock(10,28);r.lib.cp_panel(480,0)
        r.advance(2800);frames=[];trace=[];commits=[];previous=-1;settle=None
        for tick in range(2800,12601,100):
            r.advance(tick)
            if tick==3000:r.lib.cp_touch(1,*point)
            if tick==3100:r.lib.cp_touch(0,*point)
            s=r.state();raw=r.raw();frame=Image.frombytes('1',(200,200),raw).convert('RGB')
            page=Image.new('RGB',(440,500),'#efefeb');d=ImageDraw.Draw(page)
            d.text((20,9),label,font=font,fill='black')
            d.text((20,34),'原生 200×200 · 480ms 模拟面板 · 原速',font=small,fill='#555555')
            page.paste(frame.resize((400,400),Image.Resampling.NEAREST),(20,63))
            d.text((20,473),'实际 C 绘图 · 模拟输入 · 实机未安装',font=small,fill='#555555')
            frames.append(page);trace.append(s)
            if s['version']!=previous:
                commits.append({**s,'frameSha256':hashlib.sha256(raw).hexdigest()});previous=s['version']
                if s['reply']:
                    keyframes.setdefault((name,s['replyStep'],s['replyPosePhase']),frame.copy())
            last_step=3 if name=='cheek' else 2
            if s['reply'] and not s['replyExpression'] and s['replyStep']==last_step and settle is None:settle=tick
            if settle is not None and tick>=settle+1000:break
        file=out/f'studio-{name}-motion.gif'
        frames[0].save(file,save_all=True,append_images=frames[1:],duration=100,loop=0,optimize=False,disposal=2)
        sequences.append({'name':name,'file':file.name,'durationMs':len(frames)*100,'panelModelMs':480,
            'sampleMs':100,'playbackRate':1,'displayedFrames':commits,'resourceImageSha256':hashlib.sha256(image.read_bytes()).hexdigest()})
    sheet=Image.new('RGB',(900,556),'#efefeb');d=ImageDraw.Draw(sheet)
    d.text((15,12),'一套角色线条 · 实际 C 关键画面',font=font,fill='black')
    d.text((15,37),'眉眼/嘴型与小饰件连贯；单帧均为 200×200 一位图',font=small,fill='#555555')
    picks=(('pat',0,None,'注意到你'),('pat',1,0,'慢慢收眼'),('pat',1,1,'舒服的笑'),('pat',1,2,'轻轻睁眼'),
        ('cheek',1,0,'害羞进入'),('cheek',1,1,'收敛的笑'),('cheek',2,1,'再看你一眼'),('cheek',3,None,'自然回落'))
    for i,(name,step,phase,label) in enumerate(picks):
        frame=(next((v for (n,s,p),v in keyframes.items() if n==name and s==step),None) if phase is None else
            keyframes.get((name,step,phase)))
        if frame is None:raise RuntimeError(f'Missing actual C keyframe {name}/{step}/{phase}')
        x=15+225*(i%4);y=76+235*(i//4);sheet.paste(frame,(x,y));d.text((x,y+207),label,font=small,fill='black')
    sheet.save(out/'studio-keyframes.png')
    (out/'studio-motion.json').write_text(json.dumps({'scope':'NATIVE_C_STUDIO_ART_WITH_SIMULATED_INPUT_AND_PANEL',
        'sequences':sequences,'hardwareAcceptance':'NOT_RUN','ghosting':'NOT_SIMULATED'},ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    print('NATIVE_STUDIO_MOTION_EXPORTED',out/'studio-pat-motion.gif')


if __name__=='__main__':main()
