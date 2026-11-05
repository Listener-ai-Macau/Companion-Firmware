"""Rebase pet states onto family rasters within the 1 MiB UI budget.

Every final pixel and original state key remains represented. Menu base pages
and recording timeline rasters are retained. Existing CEMP/XOR/PackBits formats
remain independently seekable; no new device decoder or frame RAM is needed.
"""
from pathlib import Path
import json
from build_emote_asset_pack import build_pack

def build(base,profile,frames,out):
    base=Path(base);out=Path(out);raster={};state_clip={}
    def retained(clip):
        if clip not in raster:
            pbm=(base/'frames'/f'{clip}.pbm').read_bytes()
            raster[clip]=bytes(v^255 for v in pbm.split(b'\n',2)[2])
        return clip
    for state in sorted(frames):
        kind=state.split('_')[0]
        if state.startswith('menu_ui_') or state.startswith('recording_timeline_'):
            clip=retained(profile['states'][state]['canonicalClip'])
        else:
            if kind in ('life','expression'):family=state.split('_')[1]
            elif state.startswith('blink_'):family='calm'
            else:family=state.split('_')[2]
            clip='pet_base_'+family
            raster[clip]=frames[f'expression_{family}_v0_0_hold']
        state_clip[state]=clip
    target=out/'compact-catalog';target.mkdir(exist_ok=True)
    clips=[];indices={}
    for i,(name,raw) in enumerate(sorted(raster.items())):
        path=target/(name+'.pbm');path.write_bytes(b'P4\n200 200\n'+bytes(v^255 for v in raw))
        clips.append({'name':name,'frames':[{'source':path.name,'duration_ms':480}]});indices[name]=i
    manifest={'schema':'companion.emote_asset_pack_manifest.v1','name':'companion-wba-family-bases',
        'revision':profile['profileRevision'],'priority':0,'profile':{'width':200,'height':200,
        'stride_bytes':25,'pixel_format':'mono_1bpp_white_is_one_msb'},'encoding':'packbits','clips':clips}
    path=target/'manifest.json';path.write_text(json.dumps(manifest,indent=2)+'\n')
    cemp,metadata=build_pack(path);(out/'product.cemp').write_bytes(cemp)
    return cemp,metadata,raster,indices,state_clip
