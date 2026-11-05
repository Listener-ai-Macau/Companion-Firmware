"""Export registered native anatomy for the procedural C face compositor."""
from pathlib import Path
import hashlib
from wba_pet_studio_art import PetStudioArt,bounds

def spans(points):
    result=[]
    for y in sorted({y for x,y in points}):
        row=sorted(x for x,py in points if py==y)
        start=last=row[0]
        for x in row[1:]:
            if x!=last+1:result.append((start,y,last-start+1));start=x
            last=x
        result.append((start,y,last-start+1))
    return result

def build(root,out,draw_frames):
    # Capture the common anchors from the actual producer's configuration.
    # No segmentation of a concept image and no AI bitmap enters firmware.
    captured=[];original=PetStudioArt.configure
    def configure(art,eyes,fixed):
        original(art,eyes,fixed);captured.append(art)
    PetStudioArt.configure=configure
    try:
        draw_frames({'expression_calm_v0_0_hold'},lively=True,reply_poses=True,
            refined_ornaments=True,richer_poses=True,performance=True,polished=True,
            studio=True,inspection=True)
    finally:PetStudioArt.configure=original
    art=captured[0];white=[];ranges=[]
    for eye in art.highlights:
        row=[]
        for group in eye:
            data=spans(group);row.append((len(white),len(data)));white.extend(data)
        if len(row)!=2:raise ValueError('The retained character has two enclosed catchlights per eye')
        ranges.append(row)
    fixed=spans(art.fixed)
    lines=['#ifndef COMPANION_PET_FACE_TEMPLATE_H','#define COMPANION_PET_FACE_TEMPLATE_H',
        '#include <stdint.h>',
        'static const uint8_t comp_pet_template_eye_boxes[2][4] = {'+
            ','.join('{'+','.join(map(str,bounds(eye)))+'}' for eye in art.eyes)+'};',
        'static const uint16_t comp_pet_template_glint_ranges[2][2][2] = {'+
            ','.join('{'+','.join('{'+','.join(map(str,r))+'}' for r in eye)+'}' for eye in ranges)+'};']
    for name,rows in (('glints',white),('fixed',fixed)):
        lines.append(f'static const uint8_t comp_pet_template_{name}[{len(rows)}][3] = {{'+
            ','.join('{'+','.join(map(str,row))+'}' for row in rows)+'};')
    lines.append('#endif')
    path=out/'companion_pet_face_template.h';path.write_text('\n'.join(lines)+'\n',encoding='ascii')
    source=Path(__file__).resolve()
    return {'header':path.name,'headerSha256':hashlib.sha256(path.read_bytes()).hexdigest().upper(),
        'eyeBoxes':[bounds(eye) for eye in art.eyes],'catchlights':'original enclosed native white masks',
        'fixedAnatomy':'original nose and cheeks','extraFrameRamBytes':0,
        'sourceSha256':{source.relative_to(root).as_posix():hashlib.sha256(source.read_bytes()).hexdigest().upper()}}
