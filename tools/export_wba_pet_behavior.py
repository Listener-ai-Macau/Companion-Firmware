#!/usr/bin/env python3
"""Show production C intent variation at the original simulated panel pace."""
from pathlib import Path
import argparse,hashlib,json
from PIL import Image,ImageDraw,ImageFont
from wba_runtime_preview import Runtime

def main():
    p=argparse.ArgumentParser(description=__doc__)
    for name in ('resources','host-dll','output'):p.add_argument('--'+name,type=Path,required=True)
    args=p.parse_args();out=args.output.resolve();out.mkdir(parents=True,exist_ok=True)
    image=args.resources.resolve()/'ui-partition.bin';dll=args.host_dll.resolve()
    font=ImageFont.truetype('C:/Windows/Fonts/msyh.ttc',14)
    small=ImageFont.truetype('C:/Windows/Fonts/msyh.ttc',12)
    gallery=Image.new('RGB',(900,570),'#efefeb');gd=ImageDraw.Draw(gallery)
    gd.text((12,8),'同一个角色、同一种互动 · 神态由参数组合',font=font,fill='black')
    gd.text((12,32),'实际生产 C 绘制 · 墨水屏时延为模拟 · 未安装到设备',font=small,fill='#555555')
    cases=[]
    for panel in (480,800):
        for kind,label,touch,row in (('pat','同样摸头',(100,60),0),('cheek','同样戳左脸',(45,145),1)):
            sequences=[]
            for column,seed in enumerate((17,31,71,103)):
                r=Runtime(image,dll,seed=seed);r.lib.cp_clock(10,28);r.lib.cp_panel(panel,0)
                r.advance(2800);r.lib.cp_touch(1,*touch);r.advance(2900);r.lib.cp_touch(0,*touch)
                frames=[];commits=[];last=-1;peak=None
                for tick in range(3000,9301,100):
                    r.advance(tick);s=r.state();frame=Image.frombytes('1',(200,200),r.raw()).convert('RGB')
                    frames.append(frame)
                    if s['version']!=last:
                        last=s['version'];commits.append({k:s[k] for k in ('nowMs','version','family','reply','replyStep',
                            'replyExpression','replyPosePhase','replyPoseCount','petSeed','petInteraction','petIntensity',
                            'petRepetitions','petPeakHoldMs','eyesClosedMask')})
                    if s['visibleKind']==2 and s['replyExpression'] and s['replyStep']==1 and s['replyPosePhase']==1:
                        if peak is None:peak=(frame.copy(),s)
                if peak is None:raise RuntimeError('No committed intent peak to illustrate')
                sequences.append(frames)
                cases.append({'interaction':kind,'seed':seed,'panelModelMs':panel,'commits':commits,
                    'peakFaceSha256':hashlib.sha256(peak[0].tobytes()).hexdigest(),
                    'intent':{k:peak[1][k] for k in ('petSeed','petInteraction','petIntensity','petRepetitions','petPeakHoldMs')}})
                if panel==480:
                    x=12+column*222;y=72+row*249
                    gallery.paste(peak[0],(x,y));gd.text((x,y+208),f'{label} · {column+1}',font=small,fill='black')
            pages=[]
            for index in range(len(sequences[0])):
                page=Image.new('RGB',(900,322),'#efefeb');d=ImageDraw.Draw(page)
                d.text((12,8),f'{label} · 四个不同意图种子',font=font,fill='black')
                d.text((12,31),f'实际 C 帧 · {panel}ms模拟屏幕 · 原速，无插帧',font=small,fill='#555555')
                for column,frames in enumerate(sequences):
                    page.paste(frames[index],(12+column*222,67));d.text((12+column*222,277),f'第 {column+1} 次神态',font=small,fill='black')
                pages.append(page)
            pages[0].save(out/f'{kind}-intent-{panel}ms.gif',save_all=True,append_images=pages[1:],
                duration=100,loop=0,optimize=False,disposal=2)
    gallery.save(out/'interaction-variants.png')
    # One continuous production runtime: recent repeated contact shapes the
    # intensity and dwell rather than resetting the same prerecorded clip.
    r=Runtime(image,dll,seed=17);r.lib.cp_clock(10,28);r.lib.cp_panel(480,0);r.advance(2800)
    pages=[];trace=[];last=-1
    for tick in range(2900,17901,100):
        if tick in (3000,8000,13000):r.lib.cp_touch(1,100,60)
        if tick in (3100,8100,13100):r.lib.cp_touch(0,100,60)
        r.advance(tick);s=r.state();frame=Image.frombytes('1',(200,200),r.raw()).convert('RGB')
        page=Image.new('RGB',(440,320),'#efefeb');d=ImageDraw.Draw(page)
        d.text((12,8),'连续摸头 · 最近的互动会影响反应',font=font,fill='black')
        d.text((12,31),'实际 C · 480ms模拟屏幕 · 原速，无插帧',font=small,fill='#555555')
        page.paste(frame,(120,67));d.text((12,281),f'第 {1 if tick<8000 else 2 if tick<13000 else 3} 次摸头',font=small,fill='black')
        pages.append(page)
        if s['version']!=last:
            last=s['version'];trace.append({k:s[k] for k in ('nowMs','family','reply','replyStep','replyExpression',
                'replyPosePhase','petSeed','petIntensity','petRepetitions','petPeakHoldMs')})
    pages[0].save(out/'repeated-headpat.gif',save_all=True,append_images=pages[1:],duration=100,loop=0,optimize=False,disposal=2)
    profile=json.loads((args.resources/'profile.json').read_text())
    result={'scope':'PRODUCTION_C_PARAMETER_COMPOSITION_ARTIFACT','generation':profile['generation'],
        'resourceImageSha256':hashlib.sha256(image.read_bytes()).hexdigest(),'hostDllSha256':hashlib.sha256(dll.read_bytes()).hexdigest(),
        'hardwareAcceptance':'NOT_RUN','panelModelsMs':[480,800],'playback':'100ms sampling at original elapsed time, no interpolation',
        'algorithm':'interaction intent -> constrained family -> correlated facial knobs -> completion-driven phases',
        'cases':cases,'repeatedInteraction':trace}
    (out/'behavior-preview.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    print('PROCEDURAL_C_BEHAVIOR_PREVIEW_EXPORTED '+str(out/'interaction-variants.png'))
if __name__=='__main__':main()
