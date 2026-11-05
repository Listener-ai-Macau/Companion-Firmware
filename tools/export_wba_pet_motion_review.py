"""Native C design export: temporal eyelid acting and family variations.

The panel and entropy provider are simulated. Images contain only committed
production-C pixels; no interpolation, accelerated playback or hardware claim.
"""
from pathlib import Path
import argparse,json,hashlib
from PIL import Image,ImageDraw,ImageFont
import wba_runtime_preview as preview

def main():
    p=argparse.ArgumentParser(description=__doc__)
    for name in ('resources','host-dll','output','old-preview'):p.add_argument('--'+name,type=Path,required=True)
    args=p.parse_args();out=args.output.resolve();out.mkdir(parents=True,exist_ok=True)
    image=args.resources.resolve()/'ui-partition.bin';dll=args.host_dll.resolve()
    font=ImageFont.truetype('C:/Windows/Fonts/msyh.ttc',13)
    small=ImageFont.truetype('C:/Windows/Fonts/msyh.ttc',12)
    source=hashlib.sha256(image.read_bytes()).hexdigest();sequences=[];peaks={}
    for latency in (480,800):
        r=preview.Runtime(image,dll);r.lib.cp_clock(10,28);r.lib.cp_panel(latency,0)
        r.advance(3000);r.lib.cp_touch(1,45,145);r.advance(3100);r.lib.cp_touch(0,45,145)
        frames=[];states=[];commits=[];previous=-1;settle=None
        for tick in range(3200,12601,100):
            r.advance(tick);s=r.state();raw=r.raw();frames.append(Image.frombytes('1',(200,200),raw).convert('RGB'))
            states.append(s)
            if s['version']!=previous:
                commits.append({**s,'frameSha256':hashlib.sha256(raw).hexdigest()});previous=s['version']
            if s['replyExpression'] and s['replyPosePhase']==1:peaks.setdefault((latency,s['replyStep']),frames[-1].copy())
            if s['reply'] and not s['replyExpression'] and s['replyStep']==3 and settle is None:settle=tick
            if settle is not None and tick>=settle+600:break
        movie=[]
        for i,frame in enumerate(frames):
            page=Image.new('RGB',(232,268),'#efefeb');d=ImageDraw.Draw(page)
            d.text((16,8),f'{latency}ms 模拟面板 · 原速',font=font,fill='black')
            d.text((16,29),'C程序画面，尚未装入实机',font=small,fill='#555555')
            page.paste(frame,(16,51));movie.append(page)
        movie[0].save(out/f'cheek-motion-{latency}ms.gif',save_all=True,append_images=movie[1:],
            duration=100,loop=0,optimize=False,disposal=2)
        sequences.append({'panelModelMs':latency,'displayedFrames':commits,'sampleMs':100,'playbackRate':1,
            'resourceImageSha256':source,'scope':'SIMULATED_PANEL_AND_ENTROPY_WITH_PRODUCTION_C'})
    old=Image.open(args.old_preview/'cheek-steps.png').convert('RGB')
    compare=Image.new('RGB',(470,554),'#efefeb');draw=ImageDraw.Draw(compare)
    draw.text((15,10),'眉眼与饰件精修 · 原生 200×200',font=font,fill='black')
    draw.text((15,31),'上：旧稿   下：新稿 C 画面 · 非实屏验收',font=small,fill='#555555')
    for col,step in enumerate((1,2)):
        compare.paste(old.crop((15+225*step,65,215+225*step,265)),(15+225*col,65))
        compare.paste(peaks[(480,step)],(15+225*col,312))
        draw.text((15+225*col,524),('害羞眯眼' if step==1 else '柔和地再看你'),font=small,fill='black')
    compare.save(out/'before-after.png')
    sheet=Image.new('RGB',(690,554),'#efefeb');draw=ImageDraw.Draw(sheet)
    draw.text((15,10),'同样摸头 · 神态与饰件有变化',font=font,fill='black')
    draw.text((15,32),'连续六次 C 回应 · 模拟触摸/随机源/480ms面板',font=small,fill='#555555')
    r=preview.Runtime(image,dll);r.lib.cp_clock(10,28);r.lib.cp_panel(480,0);r.advance(3000)
    choices=[]
    for occurrence in range(6):
        start=3000+occurrence*9500;r.advance(start)
        r.lib.cp_touch(1,100,60);r.advance(start+100);r.lib.cp_touch(0,100,60)
        for tick in range(start+200,start+8001,100):
            r.advance(tick);s=r.state()
            if s['visibleKind']==2 and s['replyStep']==1 and s['replyExpression'] and s['replyPosePhase']==1:
                x=15+225*(occurrence%3);y=65+240*(occurrence//3)
                sheet.paste(Image.frombytes('1',(200,200),r.raw()).convert('RGB'),(x,y))
                draw.text((x,y+210),f'第 {occurrence+1} 次 · 同属亲近回应',font=small,fill='black')
                choices.append({**s,'resourceImageSha256':source});break
        else:raise RuntimeError('No visible head-pat pose to export')
        r.advance(start+9000)
    sheet.save(out/'family-variations.png')
    sheet=Image.new('RGB',(690,554),'#efefeb');draw=ImageDraw.Draw(sheet)
    draw.text((15,10),'开机也有不同神态',font=font,fill='black')
    draw.text((15,32),'六个模拟随机种子 · C实际首帧 · 实机尚未安装',font=small,fill='#555555')
    startup=[]
    for i,seed in enumerate((1,17,42,99,1024,7654)):
        r=preview.Runtime(image,dll,seed=seed);r.lib.cp_clock(10,28);r.lib.cp_panel(480,0);r.advance(520)
        s=r.state();x=15+225*(i%3);y=65+240*(i//3)
        sheet.paste(Image.frombytes('1',(200,200),r.raw()).convert('RGB'),(x,y))
        draw.text((x,y+210),f'首帧 · {s["family"]}',font=small,fill='black')
        startup.append({**s,'simulatedSeed':seed,'resourceImageSha256':source})
    sheet.save(out/'startup-variations.png')
    (out/'motion-review.json').write_text(json.dumps({'scope':'NATIVE_C_ART_AND_TEMPORAL_DESIGN_EXPORT',
        'sequences':sequences,'sameFamilyChoices':choices,'startupChoices':startup,
        'hardwareAcceptance':'NOT_RUN','panelGhosting':'NOT_SIMULATED'},ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    print('PET_MOTION_ART_EXPORTED',out/'before-after.png')

if __name__=='__main__':main()
