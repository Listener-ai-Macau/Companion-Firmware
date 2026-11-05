"""Compile native play/recording text labels; no face or ornament artwork."""
from pathlib import Path
import json,hashlib
from PIL import Image,ImageDraw,ImageFont
from build_wba_pet_help import packed

LABELS=(('Gaze game','眼神小游戏','眼神小遊戲',14),
        ('Tap the star; swipe to end','点旁边星星，右滑结束','點旁邊星星，右滑結束',12),
        ('Double tap to stop','双击停止','點兩下停止',14),
        ('Start recording','开始录音','開始錄音',14),
        ('Tap the nearby star','点旁边的小星星','點旁邊的小星星',12),
        ('You found me!','对啦！','對啦！',12),
        ('Round ended; tap to return','这轮结束，点按返回','這輪結束，點按返回',12),
        ('Next turn...','下一轮…','下一輪…',12))

def raster(texts,locale):
 text,size=texts[locale],texts[3]
 font_path=Path('C:/Windows/Fonts')/('segoeui.ttf' if locale==0 else 'simhei.ttf' if size>=14 else 'msyh.ttc')
 font=ImageFont.truetype(str(font_path),size)
 im=Image.new('L',(160,18),255);draw=ImageDraw.Draw(im);l,t,r,b=draw.textbbox((0,0),text,font=font)
 assert r-l<=160 and b-t<=18,text
 draw.text((-l,(18-b+t)//2-t),text,font=font,fill=0)
 return im.point(lambda v:255 if v>=160 else 0).convert('1'),r-l,font_path
def build(out):
 out=Path(out);out.mkdir(parents=True,exist_ok=True)
 data=bytearray();offsets=[];widths=[];sources={}
 for locale in range(3):
  row=[];ink_widths=[]
  for texts in LABELS:
   im,width,font_path=raster(texts,locale)
   sources[str(font_path)]=hashlib.sha256(font_path.read_bytes()).hexdigest()
   ink_widths.append(width)
   row.append(len(data));data.extend(packed(im.tobytes()))
  offsets.append(row)
  widths.append(ink_widths)
 header=['/* Text only; original complete pet artwork remains unchanged. */',
  '#ifndef COMPANION_PET_PLAY_LABELS_H','#define COMPANION_PET_PLAY_LABELS_H','#include <stdint.h>',
  f'#define COMP_PET_PLAY_LABEL_COUNT {len(LABELS)}u',
  f'static const uint16_t comp_pet_play_label_offsets[3][{len(LABELS)}] = {{']
 header += ['{'+','.join(map(str,row))+'},' for row in offsets]
 header += ['};',f'static const uint8_t comp_pet_play_label_ink_width[3][{len(LABELS)}] = {{']
 header += ['{'+','.join(map(str,row))+'},' for row in widths]
 header += ['};','static const uint8_t comp_pet_play_label_bits[] = {']
 header += [','.join(f'0x{v:02x}' for v in data[i:i+24])+',' for i in range(0,len(data),24)]
 header += ['};','#endif','']
 target=out/'companion_pet_play_labels.h';target.write_text('\n'.join(header),encoding='ascii')
 return dict(texts=LABELS,packedBytes=len(data),fontSources=sources,headerSha256=hashlib.sha256(target.read_bytes()).hexdigest(),newFaceArtwork=False)
if __name__=='__main__':
 print(json.dumps(build(Path(__file__).resolve().parents[1]/'app/companion_pendant/runtime/generated'),ensure_ascii=False))
