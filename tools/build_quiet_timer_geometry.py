"""Derive first-word geometry from existing UI84 labels without rebuilding art."""
from pathlib import Path
import argparse
from wba_customer_menu import TEXT

def render_quiet_timer_geometry():
    """First-word widths of unchanged UI84 glyphs, not new bitmap artwork."""
    from PIL import Image, ImageDraw
    from compact_wba_recording_ui import pack
    from wba_menu_typography import draw_text, text_width
    segments=[('QUIET',('Quiet','安静','安靜')),
              ('STANDARD',('Standard','标准','標準')),
              ('LIVELY',('Lively','活泼','活潑')),
              ('RESTORE',('Restore','恢复','恢復'))]
    rows=[]
    for key,shorts in segments:
        widths=[]
        for locale in range(3):
            size=14
            while size>=11:
                if text_width(TEXT[key][locale],size,submenu=True)<=176:
                    image=Image.new('1',(176,16),1)
                    draw_text(ImageDraw.Draw(image),(0,0),TEXT[key][locale],size,width=176,submenu=True)
                    if len(pack(image.tobytes()))<=199:break
                size-=1
            assert size>=11
            width=text_width(shorts[locale],size,submenu=True)
            # Width is geometry only. Runtime streams the original complete
            # glyph and clips its columns; it never re-rasterizes this word.
            assert 0<width<=text_width(TEXT[key][locale],size,submenu=True)
            widths.append(width)
        rows.append(widths)
    text=['/* Generated original UI84 word geometry; resource pixels unchanged. */',
          '#ifndef COMPANION_QUIET_TIMER_GEOMETRY_H',
          '#define COMPANION_QUIET_TIMER_GEOMETRY_H',
          '#include <stdint.h>',
          'static const uint8_t comp_quiet_prefix_width[4][3]={']
    text+=['{'+','.join(str(w)+'u' for w in row)+'},' for row in rows]
    text+=['};','#endif','']
    return '\n'.join(text), rows

if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output',type=Path,default=Path(__file__).resolve().parents[1]/'app/companion_pendant/runtime/generated/companion_quiet_timer_geometry.h')
    parser.add_argument('--check',action='store_true')
    args=parser.parse_args();text,rows=render_quiet_timer_geometry()
    if args.check:
        if args.output.read_text(encoding='ascii')!=text:raise SystemExit('Original label geometry differs; regenerate the matching contract')
    else:args.output.write_text(text,encoding='ascii')
    print('EXISTING_UI84_PREFIX_GEOMETRY_MATCHES' if args.check else 'UI84_PREFIX_GEOMETRY_WRITTEN')
