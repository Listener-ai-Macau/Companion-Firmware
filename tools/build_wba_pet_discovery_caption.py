"""Generate native first-use text independently of the frozen UI68 source recipe."""
from pathlib import Path
import hashlib
from PIL import Image,ImageDraw,ImageFont

def build_discovery(out):
    """One native line; no face edit, new NOR arena, speaker or preview page."""
    out=Path(out);out.mkdir(parents=True,exist_ok=True)
    labels=('Try a gentle head stroke.','摸摸头，试试看。','摸摸頭，試試看。')
    font_path=Path('C:/Windows/Fonts/msyh.ttc');font_bytes=font_path.read_bytes()
    font=ImageFont.truetype(str(font_path),12)
    width,height,stride=160,13,20
    lines=['/* Native first-use caption, original pet resources are unchanged. */',
        '#ifndef COMPANION_PET_DISCOVERY_CAPTION_H','#define COMPANION_PET_DISCOVERY_CAPTION_H',
        '#include <stdint.h>',f'#define COMP_PET_DISCOVERY_WIDTH {width}u',
        f'#define COMP_PET_DISCOVERY_HEIGHT {height}u',f'#define COMP_PET_DISCOVERY_STRIDE {stride}u',
        f'static const uint8_t comp_pet_discovery_caption[3][{height*stride}] = {{']
    for label in labels:
        raster=Image.new('L',(width,height),255);draw=ImageDraw.Draw(raster)
        l,t,r,b=draw.textbbox((0,0),label,font=font)
        if r-l>width or b-t>height:raise ValueError('Discovery caption exceeds native line: '+label)
        draw.text(((width-(r-l))//2-l,(height-(b-t))//2-t),label,font=font,fill=0)
        raster=raster.point(lambda v:255 if v>=160 else 0).convert('1')
        lines.append('{'+','.join(f'0x{v:02X}' for v in raster.tobytes())+'},')
    lines+=['};','#endif','']
    header=out/'companion_pet_discovery_caption.h';header.write_text('\n'.join(lines),encoding='ascii')
    if font_path.read_bytes()!=font_bytes:raise ValueError('Discovery font changed during generation')
    return dict(labels=labels,placement=[20,181,width,height],bitmapBytes=3*height*stride,
        location='Internal const ROM, original UI68/NOR layout preserved',headerSha256=hashlib.sha256(header.read_bytes()).hexdigest(),
        fontSource=dict(path=str(font_path),sha256=hashlib.sha256(font_bytes).hexdigest()))
