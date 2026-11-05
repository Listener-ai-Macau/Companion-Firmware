#!/usr/bin/env python3
"""Quick source-art review before building the full resource bank."""
from pathlib import Path
import argparse,json
from PIL import Image,ImageDraw,ImageFont
from build_wba_product_resources import make_frames

def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--output',type=Path,required=True);p.add_argument('--studio',action='store_true')
    args=p.parse_args();out=args.output;out.mkdir(parents=True,exist_ok=True)
    keys=('tap_local_bashful_down','tap_local_bashful_left','tap_local_warm_up','tap_local_playful_right')
    states=set(keys)|{f'pet_motion_{key.removeprefix("tap_local_")}_{phase}' for key in keys for phase in ('arrive','release')}
    frames,metadata,quality=make_frames(states,lively=True,reply_poses=True,refined_ornaments=True,
        richer_poses=True,performance=True,polished=True,studio=args.studio,inspection=True)
    font=ImageFont.truetype('C:/Windows/Fonts/msyh.ttc',13)
    sheet=Image.new('RGB',(900,540),'#efefeb');draw=ImageDraw.Draw(sheet)
    draw.text((12,8),'原生表情精修 · 单饰件与柔和眼睑',font=font,fill='black')
    draw.text((12,29),'生产资源绘图源 · 美术研究稿，非实屏或硬件验收',font=font,fill='#555555')
    for i,key in enumerate(keys):
        image=Image.frombytes('1',(200,200),frames[key]).convert('RGB');image.save(out/(key+'.png'))
        sheet.paste(image,(12+i*220,62));draw.text((12+i*220,267),key.removeprefix('tap_local_'),font=font,fill='black')
    for i,key in enumerate((f'pet_motion_bashful_down_arrive','tap_local_bashful_down',f'pet_motion_bashful_left_arrive','tap_local_bashful_left')):
        sheet.paste(Image.frombytes('1',(200,200),frames[key]).convert('RGB'),(12+i*220,304))
    sheet.save(out/'pose-study.png')
    (out/'art-study.json').write_text(json.dumps({'scope':'NATIVE_SOURCE_ART_STUDY','metadata':metadata,
        'quality':quality,'hardware':'NOT_RUN'},indent=2,ensure_ascii=False),encoding='utf-8')
    print(out/'pose-study.png')
if __name__=='__main__':main()
