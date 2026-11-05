#!/usr/bin/env python3
"""Export committed production C frames, with simulated motion/touch/panel.

This is a design preview, not hardware or touch acceptance. The default
800 ms panel model is presentation pacing, not measured hardware FPS.
"""
from pathlib import Path
import argparse, hashlib, json
from PIL import Image, ImageDraw, ImageFont
import wba_runtime_preview as preview

def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--resources',type=Path,required=True)
    parser.add_argument('--output',type=Path,required=True)
    parser.add_argument('--panel-ms',type=int,default=800,help='explicit simulated request-to-visible latency, not actual FPS')
    parser.add_argument('--host-dll',type=Path,help='reuse the already built production-C preview adapter')
    args=parser.parse_args();out=args.output.resolve();out.mkdir(parents=True,exist_ok=True)
    bank=args.resources.resolve();preview.OUT=out/'host'
    preview.INCLUDES=[bank,*preview.INCLUDES]
    if not 20<=args.panel_ms<=2000:raise ValueError('Unsupported simulated panel latency')
    dll=args.host_dll.resolve() if args.host_dll else preview.build();image=bank/'ui-partition.bin'
    profile=json.loads((bank/'profile.json').read_text())
    font=ImageFont.truetype('C:/Windows/Fonts/msyh.ttc',14)
    small=ImageFont.truetype('C:/Windows/Fonts/msyh.ttc',12)
    scenes=[]
    for name,label,action,touch in (
        ('pickup','拿起 · 期待后迎接',3,None),
        ('shake','轻晃 · 眨眼后俏皮笑',8,None),
        ('pat','摸头 · 舒服地眯眼',None,(100,60)),
        ('cheek','戳脸颊 · 害羞后偷偷看',None,(45,145)),
        ('nose','戳鼻子 · 惊喜后笑弯眼',None,(100,120)),
        ('chin','挠下巴 · 笑弯眼后眨眼',None,(100,160))):
        r=preview.Runtime(image,dll);r.lib.cp_clock(10,28);r.lib.cp_panel(args.panel_ms,0)
        r.advance(3000)
        if action:r.lib.cp_action(action)
        if touch:
            r.lib.cp_touch(1,*touch);r.advance(3100);r.lib.cp_touch(0,*touch)
        frames=[];snapshots=[];beats={}
        for tick in range(3200,14401,200):
            r.advance(tick);state=r.state(with_pixels=True);state.pop('png',None)
            frame=Image.frombytes('1',(200,200),r.raw()).convert('RGB')
            frames.append(frame);snapshots.append(state)
            if state['visibleKind']==2 and state['reply'] and (not state['replyExpression'] or state['replyPosePhase']==1):
                beats.setdefault(state['replyStep'],(frame.copy(),state))
        frames[0].save(out/f'{name}.gif',save_all=True,append_images=frames[1:],
            duration=200,loop=0,optimize=False,disposal=2)
        last_step=max(beats)
        captions=('先注意到你','眉眼回应',*(['余韵'] if last_step==3 else []),'自然回落')
        sheet=Image.new('RGB',(15+225*len(captions),294),'#efefeb');draw=ImageDraw.Draw(sheet)
        draw.text((15,9),label,font=font,fill='black')
        draw.text((15,32),'实际 C 程序画面 · 输入/屏幕为模拟，实机尚未安装',font=small,fill='#555555')
        for step,caption in enumerate(captions):
            if step not in beats:raise RuntimeError(f'{name}: preview did not display reply beat {step}')
            frame,state=beats[step];sheet.paste(frame,(15+step*225,65))
            draw.text((15+step*225,272),caption,font=small,fill='black')
        sheet.save(out/f'{name}-steps.png')
        scenes.append({'name':name,'label':label,'frames':frames,'snapshots':snapshots,
            'resourceImageSha256':hashlib.sha256(r.image).hexdigest(),
            'beats':{str(k):v[1] for k,v in beats.items()}})
    cover_size=(690,554)
    cover=Image.new('RGB',cover_size,'#efefeb');draw=ImageDraw.Draw(cover)
    draw.text((15,10),'Companion · 让回应看得懂',font=font,fill='black')
    draw.text((15,33),f'C 程序预览 · 输入/{args.panel_ms}ms屏幕为模拟 · 实机尚未安装，触摸待修',font=small,fill='#555555')
    for i,scene in enumerate(scenes):
        x=15+(i%3)*225;y=65+(i//3)*240
        cover.paste(Image.open(out/f"{scene['name']}-steps.png").crop((240,65,440,265)),(x,y))
        draw.text((x,y+210),scene['label'],font=small,fill='black')
    cover.save(out/'design-sheet.png')
    animation=[]
    for n in range(len(scenes[0]['frames'])):
        page=Image.new('RGB',cover_size,'#efefeb');draw=ImageDraw.Draw(page)
        draw.text((15,10),f'C 程序动态预览 · {args.panel_ms}ms模拟屏幕，实机尚未安装',font=font,fill='black')
        for i,scene in enumerate(scenes):
            x=15+(i%3)*225;y=65+(i//3)*240
            page.paste(scene['frames'][n],(x,y))
            draw.text((x,y+210),scene['label'],font=small,fill='black')
        animation.append(page)
    animation[0].save(out/'interaction-design.gif',save_all=True,append_images=animation[1:],
        duration=200,loop=0,optimize=False,disposal=2)
    emotion_labels=('平静 · 小闪光','好奇 · 问号','开心 · 星光','亲近 · 爱心','顽皮 · 双闪光',
                    '困倦 · 月牙与 Z','害羞 · 爱心','思考 · 三个小点','专注 · 单闪光','警觉 · 感叹号')
    gallery=Image.new('RGB',(1105,554),'#efefeb');draw=ImageDraw.Draw(gallery)
    draw.text((15,10),'Companion · 表情与小饰件',font=font,fill='black')
    draw.text((15,32),'原生 200×200 软件预览 · 实机尚未安装，触摸仍待修复',font=small,fill='#555555')
    emotion_scenes=[]
    for family,label in enumerate(emotion_labels):
        r=preview.Runtime(image,dll);r.lib.cp_clock(10,28);r.lib.cp_panel(args.panel_ms,0)
        r.advance(3000);r.lib.cp_family(family);r.advance(5600)
        x=15+(family%5)*218;y=65+(family//5)*240
        gallery.paste(Image.frombytes('1',(200,200),r.raw()).convert('RGB'),(x,y))
        draw.text((x,y+210),label,font=small,fill='black')
        snapshot=r.state(with_pixels=True);snapshot.pop('png',None)
        emotion_scenes.append({'family':family,'label':label,'snapshot':snapshot,
            'resourceImageSha256':hashlib.sha256(r.image).hexdigest()})
    gallery.save(out/'emotion-sheet.png')
    variants=profile.get('artComposition',{}).get('expressionVariants',[])
    pose_scenes=[]
    if variants:
        columns=min(5,len(variants));rows=(len(variants)+columns-1)//columns
        gallery=Image.new('RGB',(15+225*columns,74+240*rows),'#efefeb');draw=ImageDraw.Draw(gallery)
        draw.text((15,10),'Companion · 互动神态与原生饰件',font=font,fill='black')
        draw.text((15,33),'原生 200×200 C 程序画面 · 软件预览，实机尚未安装',font=small,fill='#555555')
        families=('calm','curious','delighted','warm','playful','sleepy','bashful','thoughtful','focused','alert')
        zones=('center','up','down','left','right')
        for i,pose in enumerate(variants):
            r=preview.Runtime(image,dll);r.lib.cp_clock(10,28);r.lib.cp_panel(args.panel_ms,0)
            r.advance(3000);r.lib.cp_pose(families.index(pose['family']),zones.index(pose['zone']))
            for tick in range(3100,8001,100):
                r.advance(tick);snapshot=r.state(with_pixels=True);snapshot.pop('png',None)
                if snapshot['visibleKind']==2 and snapshot['replyStep']==1 and snapshot['replyExpression'] and snapshot['replyPosePhase']==1:break
            else:raise RuntimeError('No committed pose for '+pose['state'])
            x=15+(i%columns)*225;y=65+(i//columns)*240
            gallery.paste(Image.frombytes('1',(200,200),r.raw()).convert('RGB'),(x,y))
            draw.text((x,y+210),pose['label'],font=small,fill='black')
            pose_scenes.append({**pose,'snapshot':snapshot,'scope':'EXPLICIT_HOST_ART_INSPECTION',
                'resourceImageSha256':hashlib.sha256(r.image).hexdigest()})
        gallery.save(out/'expression-variants.png')
    repeated=[]
    if profile.get('artComposition',{}).get('petPerformance'):
        sheet=Image.new('RGB',(690,554),'#efefeb');draw=ImageDraw.Draw(sheet)
        draw.text((15,10),'再来一次 · 同一种互动有不同神态',font=font,fill='black')
        draw.text((15,33),'实际 C 回应 · 模拟输入和屏幕 · 上排首次，下排再次',font=small,fill='#555555')
        for column,(name,label,action,touch) in enumerate((
            ('pickup','拿起',3,None),('shake','轻晃',8,None),('pat','摸头',None,(100,60)))):
            r=preview.Runtime(image,dll);r.lib.cp_clock(10,28);r.lib.cp_panel(args.panel_ms,0)
            r.advance(3000)
            snapshots=[]
            for occurrence,start in enumerate((3000,16000)):
                r.advance(start)
                if action:r.lib.cp_action(action)
                if touch:
                    r.lib.cp_touch(1,*touch);r.advance(start+100);r.lib.cp_touch(0,*touch)
                captured=False
                for tick in range(start+200,start+11401,200):
                    r.advance(tick);snapshot=r.state(with_pixels=True);snapshot.pop('png',None)
                    if not captured and snapshot['visibleKind']==2 and snapshot['replyStep']==1 and snapshot['replyExpression'] and snapshot['replyPosePhase']==1:
                        sheet.paste(Image.frombytes('1',(200,200),r.raw()).convert('RGB'),(15+225*column,65+240*occurrence))
                        snapshots.append(snapshot);captured=True
                if not captured:raise RuntimeError('Missing repeat reply: '+name)
                draw.text((15+225*column,275+240*occurrence),label+(' · 第一次' if occurrence==0 else ' · 再次'),font=small,fill='black')
            repeated.append({'name':name,'snapshots':snapshots,'resourceImageSha256':hashlib.sha256(r.image).hexdigest()})
        sheet.save(out/'repeat-interactions.png')
    languages=[]
    if profile.get('artComposition',{}).get('localReplyCaptions'):
        sheet=Image.new('RGB',(690,314),'#efefeb');draw=ImageDraw.Draw(sheet)
        draw.text((15,10),'表情与一句回应 · 三语原生画面',font=font,fill='black')
        draw.text((15,33),'C 程序合成的本地短句 · 非 AI 对话，实机尚未安装',font=small,fill='#555555')
        for locale,label in enumerate(('English','简体中文','繁體中文')):
            r=preview.Runtime(image,dll);r.lib.cp_clock(10,28);r.lib.cp_panel(args.panel_ms,0);r.lib.cp_language(locale)
            r.advance(3000);r.lib.cp_touch(1,100,60);r.advance(3100);r.lib.cp_touch(0,100,60)
            for tick in range(3200,10001,200):
                r.advance(tick);snapshot=r.state(with_pixels=True);snapshot.pop('png',None)
                if snapshot['visibleKind']==2 and snapshot['replyStep']==1 and snapshot['replyExpression'] and snapshot['replyPosePhase']==1:break
            else:raise RuntimeError('Missing localized caption')
            sheet.paste(Image.frombytes('1',(200,200),r.raw()).convert('RGB'),(15+225*locale,65))
            draw.text((15+225*locale,276),label,font=small,fill='black')
            languages.append({'locale':locale,'snapshot':snapshot,'resourceImageSha256':hashlib.sha256(r.image).hexdigest()})
        sheet.save(out/'local-replies-three-languages.png')
    reply_layout=profile.get('artComposition',{}).get('replyTextReserve')
    reply_mockups=[]
    if reply_layout:
        sheet=Image.new('RGB',(690,314),'#efefeb');draw=ImageDraw.Draw(sheet)
        draw.text((15,10),'屏幕回应 · 表情 + 两行短句',font=font,fill='black')
        draw.text((15,33),'原生 C 宠物画面 + 示例文字排版 · 示例不是 AI 回复，实机尚未安装',font=small,fill='#555555')
        for i,(family,lines,caption) in enumerate((
            (3,('你回来啦！','今天有什么想告诉我？'),'亲近 · 迎接'),
            (1,('我在听，慢慢说。','不用急着整理好思路。'),'期待 · 倾听'),
            (3,('要休息一下吗？','我陪你待一会儿。'),'温柔 · 陪伴'))):
            r=preview.Runtime(image,dll);r.lib.cp_clock(10,28);r.lib.cp_panel(args.panel_ms,0)
            r.advance(3000);r.lib.cp_family(family);r.advance(5600)
            snapshot=r.state(with_pixels=True);snapshot.pop('png',None)
            face=Image.frombytes('1',(200,200),r.raw()).convert('L')
            x,y,width,height=snapshot['replyTextSlot'];ink=ImageDraw.Draw(face)
            for line_index,line in enumerate(lines):
                bounds=ink.textbbox((0,0),line,font=small)
                text_width=bounds[2]-bounds[0]
                if text_width>width:raise ValueError('Reply sample exceeds reserved width')
                ink.text((x+(width-text_width)//2-bounds[0],y+line_index*reply_layout['linePitch']-bounds[1]),
                    line,font=small,fill=0)
            face=face.point(lambda value:255 if value>=160 else 0).convert('RGB')
            face.save(out/f'reply-layout-{i+1}.png')
            sheet.paste(face,(15+225*i,65));draw.text((15+225*i,276),caption,font=small,fill='black')
            reply_mockups.append({'label':caption,'exampleLines':lines,'rect':snapshot['replyTextSlot'],
                'scope':'STATIC_TEXT_LAYOUT_OVER_PRODUCTION_C_FACE','generatedAnswer':False,
                'snapshot':snapshot,'resourceImageSha256':hashlib.sha256(r.image).hexdigest()})
        sheet.save(out/'screen-reply-layout.png')
    result={'scope':'PRODUCTION_C_PET_DESIGN_PREVIEW','resources':str(bank),
        'generation':profile['generation'],
        'panelModelMs':args.panel_ms,'hardwareAcceptance':'NOT_RUN','touchHardware':'UNRESOLVED',
        'scenes':[{k:v for k,v in scene.items() if k!='frames'} for scene in scenes],
        'emotionScenes':emotion_scenes,'poseScenes':pose_scenes,'repeatScenes':repeated,
        'localCaptionScenes':languages,'replyLayoutMockups':reply_mockups}
    (out/'preview-result.json').write_text(json.dumps(result,indent=2,ensure_ascii=False)+'\n',encoding='utf-8')
    print('PET_PREVIEW_EXPORTED',out/'design-sheet.png')

if __name__=='__main__':main()
