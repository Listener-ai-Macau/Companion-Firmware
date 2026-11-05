"""Native local pet-help labels. Frozen UI68/face generators remain unchanged."""
from pathlib import Path
import hashlib
from PIL import Image,ImageDraw,ImageFont

LABELS=(
 ('Hold + move','按住移动','按住移動',12),
 ('Gently shake','轻晃逗我','輕晃逗我',12),
 ('Say hi','打招呼','打招呼',14),
 ('Volume','音量','音量',14),
 ('Pet help','互动帮助','互動說明',14),
)

def packed(raw):
 out=bytearray();i=0
 while i<len(raw):
  white=raw[i]==255;n=1
  while n<128 and i+n<len(raw) and (raw[i+n]==255)==white:n+=1
  out.append((128 if white else 0)|(n-1))
  if not white:out.extend(raw[i:i+n])
  i+=n
 return bytes(out)

def build(out):
 out=Path(out);out.mkdir(parents=True,exist_ok=True)
 chunks=[];offsets=[];raw_chunks=[];raw_offsets=[];sources={};unique={};raw_unique={}
 width,height,stride=160,18,20
 for locale in range(3):
  for labels in LABELS:
   text=labels[locale];size=labels[3]
   font_path=Path('C:/Windows/Fonts')/('segoeui.ttf' if locale==0 else 'simhei.ttf' if size>=14 else 'msyh.ttc')
   sources[str(font_path)]=hashlib.sha256(font_path.read_bytes()).hexdigest()
   font=ImageFont.truetype(str(font_path),size)
   raster=Image.new('L',(width,height),255);draw=ImageDraw.Draw(raster)
   l,t,r,b=draw.textbbox((0,0),text,font=font)
   if r-l>width or b-t>height:raise ValueError('Pet help label exceeds native line: '+text)
   draw.text((-l,(height-(b-t))//2-t),text,font=font,fill=0)
   raw=raster.point(lambda v:255 if v>=160 else 0).convert('1').tobytes()
   compact=packed(raw)
   if compact not in unique:
    unique[compact]=sum(map(len,chunks));chunks.append(compact)
   offsets.append(unique[compact])
   if raw not in raw_unique:
    raw_unique[raw]=sum(map(len,raw_chunks));raw_chunks.append(raw)
   raw_offsets.append(raw_unique[raw])
 header=['/* Native 12px guidance and 14px actions; original menu header retained. */',
  '#ifndef COMPANION_PET_HELP_LABELS_H','#define COMPANION_PET_HELP_LABELS_H','#include <stdint.h>',
  '#define COMP_PET_HELP_LABELS 5u',f'#define COMP_PET_HELP_WIDTH {width}u',
  f'#define COMP_PET_HELP_HEIGHT {height}u',f'#define COMP_PET_HELP_STRIDE {stride}u']
 for cond,parts,indices in [('#if COMPANION_WBA_RECORDING_UI_PACKED',chunks,offsets),('#else',raw_chunks,raw_offsets)]:
  data=b''.join(parts);header += [cond,'static const uint8_t comp_pet_help_bits[] = {']
  for i in range(0,len(data),24):header.append(','.join(f'0x{v:02X}' for v in data[i:i+24])+',')
  header+=['};','static const uint16_t comp_pet_help_offsets[3][5] = {']
  for locale in range(3):header.append('{'+','.join(str(v) for v in indices[locale*5:locale*5+5])+'},')
  header+=['};']
 header+=['#endif','#endif','']
 p=out/'companion_pet_help_labels.h';p.write_text('\n'.join(header),encoding='ascii')
 return dict(labels=LABELS,packedBytes=sum(map(len,chunks)),rawBytes=sum(map(len,raw_chunks)),fontSources=sources,
  originalUi68Unchanged=True,faceChanged=False,headerSha256=hashlib.sha256(p.read_bytes()).hexdigest())
