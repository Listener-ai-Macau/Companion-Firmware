"""Sparse native ornament variations for one stable emotional family."""
from pathlib import Path
import hashlib,json

FAMILIES=('calm','curious','delighted','warm','playful','sleepy','bashful','thoughtful','focused','alert')

def patterns(refinement):
    result={}
    for family in FAMILIES:
        base=refinement.ornament(family)
        if family in ('sleepy','thoughtful','alert'):
            variants=(base,refinement.ornament(family,0),refinement.ornament(family,2))
        else:
            variants=(base,{(x-3,y+1) for x,y in base},{(x+2,y-2) for x,y in base})
        for variant,ink in enumerate(variants):
            if any(not(112<=x<=190 and 20<=y<=64) for x,y in ink):
                raise ValueError('Accessory variation leaves reserved dock: '+family)
            result[(family,variant)]=frozenset(ink)
    return result

def build(root,out,refinement):
    root=Path(root);out=Path(out);all_spans=[];rows=[]
    for (family,variant),ink in patterns(refinement).items():
        start=len(all_spans)
        for y in sorted({y for x,y in ink}):
            xs=sorted(x for x,py in ink if py==y);left=right=xs[0]
            for x in xs[1:]:
                if x==right+1:right=x
                else:all_spans.append((left,y,right-left+1));left=right=x
            all_spans.append((left,y,right-left+1))
        rows.append((start,len(all_spans)-start))
    lines=['/* Native family accessories; stable RNG choice, not an animation clock. */',
        '#ifndef COMPANION_PET_VARIATIONS_H','#define COMPANION_PET_VARIATIONS_H','#include <stdint.h>',
        '#define COMP_PET_VARIATION_COUNT 3u',
        'static const uint16_t comp_pet_accessory_ranges[10][3][2]={']
    for family in range(10):lines.append('  {'+','.join('{%du,%du}'%row for row in rows[family*3:family*3+3])+'},')
    lines+=['};',f'static const uint8_t comp_pet_accessory_spans[{len(all_spans)}][3]={{']
    lines+=['  {%du,%du,%du},'%span for span in all_spans]
    lines+=['};','#endif']
    path=out/'companion_pet_variations.h';path.write_text('\n'.join(lines)+'\n',encoding='ascii')
    source=Path(__file__)
    return {'variantsPerFamily':3,'families':FAMILIES,'spanCount':len(all_spans),
        'romBytes':len(all_spans)*3+len(rows)*4,'header':path.name,
        'headerSha256':hashlib.sha256(path.read_bytes()).hexdigest().upper(),
        'behavior':'hardware RNG on boot, accepted interaction and daily family boundary; held throughout reply and retry',
        'art':'one primary native family motif, restrained position variation; upper-right dock only',
        'sourceSha256':{source.relative_to(root).as_posix():hashlib.sha256(source.read_bytes()).hexdigest().upper()}}
