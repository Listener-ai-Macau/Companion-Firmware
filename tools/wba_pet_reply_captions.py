"""Small three-language authored replies, not generated chat or microphone state."""
from pathlib import Path
import hashlib
from PIL import Image,ImageDraw,ImageFont

LABELS=(
    ('Here. A little closer.','在呢，靠近一点。','在呢，靠近一點。'),
    ('Hi there!','嘿，见面啦。','嘿，見面啦。'),
    ('Hehe, you got me.','嘿嘿，逗到我啦。','嘿嘿，逗到我啦。'),
    ('Happy to be with you.','今天也想陪着你。','今天也想陪著你。'),
    ("Mmm, that's nice.",'唔，好舒服。','唔，好舒服。'),
    ('A tiny bit closer.','再靠近一点点。','再靠近一點點。'),
    ('Feeling a little shy.','有一点点害羞。','有一點點害羞。'),
    ('Just a little peek.','偷偷看你一眼。','偷偷看你一眼。'),
    ('Oh?','咦？','咦？'),
    ('Hehe, that tickles!','哈哈，好痒！','哈哈，好癢！'),
    ('Yawn... a little rest.','哈啊，小歇一下。','哈啊，小歇一下。'),
    ('Gentle... I like that.','轻轻的，真舒服。','輕輕的，真舒服。'),
)
# Existing family/zone values; no new gesture, affect counter, or CEMP key.
LOOKUP=((1,1,0),(1,3,0),(3,0,1),(4,4,2),(4,3,2),(4,0,3),
        (3,1,4),(3,2,5),(3,3,11),(6,2,6),(6,3,7),(2,1,8),(2,0,9),(5,0,10))

def build(root,out):
    root=Path(root);out=Path(out)
    font_path=Path('C:/Windows/Fonts/msyh.ttc');font_bytes=font_path.read_bytes()
    font=ImageFont.truetype(str(font_path),12)
    # Native 12px glyphs need a 13px raster for English descenders. One local
    # line fits the existing 26px reply strip without cropping or scaling.
    width,height,stride=160,13,20
    lines=['/* Authored input replies. No AI answer, speech recognition, or listening state. */',
        '#ifndef COMPANION_PET_REPLY_CAPTIONS_H','#define COMPANION_PET_REPLY_CAPTIONS_H','#include <stdint.h>',
        f'#define COMP_PET_REPLY_CAPTION_COUNT {len(LABELS)}u',
        f'#define COMP_PET_REPLY_CAPTION_HEIGHT {height}u',f'#define COMP_PET_REPLY_CAPTION_WIDTH {width}u',
        f'#define COMP_PET_REPLY_CAPTION_STRIDE {stride}u',f'#define COMP_PET_REPLY_CAPTION_LOOKUP_COUNT {len(LOOKUP)}u',
        'static const uint8_t comp_pet_reply_caption_lookup[][3] = {']
    lines.extend('{'+','.join(f'{value}u' for value in row)+'},' for row in LOOKUP)
    lines+=['};',f'static const uint8_t comp_pet_reply_captions[3][{len(LABELS)}][{height*stride}] = {{']
    for locale in range(3):
        lines.append('{')
        for labels in LABELS:
            label=labels[locale];image=Image.new('L',(width,height),255);draw=ImageDraw.Draw(image)
            l,t,r,b=draw.textbbox((0,0),label,font=font)
            if r-l>width or b-t>height:raise ValueError('Caption exceeds its native line: '+label)
            draw.text(((width-(r-l))//2-l,(height-(b-t))//2-t),label,font=font,fill=0)
            image=image.point(lambda value:255 if value>=160 else 0).convert('1')
            lines.append('{'+','.join(f'0x{value:02X}' for value in image.tobytes())+'},')
        lines.append('},')
    lines+=['};','#endif','']
    header=out/'companion_pet_reply_captions.h';header.write_text('\n'.join(lines),encoding='ascii')
    if font_path.read_bytes()!=font_bytes:raise ValueError('Caption font changed during generation')
    return {'scope':'AUTHORED_LOCAL_INPUT_REPLIES','chatBackend':'NOT_IMPLEMENTED',
        'languages':['en','zh_cn','zh_tw'],'labels':LABELS,'lookup':LOOKUP,
        'placement':[20,181,width,height],'onlyDuring':'visible expressive beats; absent during idle, recording and menus',
        'header':header.name,'headerSha256':hashlib.sha256(header.read_bytes()).hexdigest().upper(),
        'bitmapBytes':3*len(LABELS)*height*stride,
        'fontSource':{'path':str(font_path),'sha256':hashlib.sha256(font_bytes).hexdigest().upper()},
        'sourceSha256':{Path(__file__).relative_to(root).as_posix():hashlib.sha256(Path(__file__).read_bytes()).hexdigest().upper()}}
