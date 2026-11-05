#!/usr/bin/env python3
"""One source of truth: registered masks -> native C -> 5000B -> PNG/CEMP.

No browser-side artwork, fractional scaling, or generation-21 impersonation.
This candidate keeps every anatomy mask and refines their layout/choreography.
"""
from pathlib import Path
import hashlib
import json
import shutil
import subprocess
from PIL import Image, ImageDraw, ImageFont
from build_emote_asset_pack import build_pack, parse_p4
from build_wba_prehardware import run
from test_wba_runtime import ROOT, APP, INCLUDES
from verify_wba_spi_nor_adapter import find_vsdevcmd
from render_wba_visual_review import FIXTURES, FAMILIES as LABELS
from wba_native_art_components import (load_authority, expression_steps,
    render_expression_frame, verify_expression_reconstruction, write_pbm, read_pbm)

ART=ROOT/'docs/art/iterations/companion-wba-screen-art-v3'
OUT=ROOT/'.cache/wba-visual-review/art/screen-v3'
FAMILIES=dict(zip(list(FIXTURES)[:10],LABELS))
STAGES=('entered','hold','exit')
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def dump(p,v):p.write_text(json.dumps(v,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
def bounds(p):return (min(x for x,y in p),min(y for x,y in p),max(x for x,y in p),max(y for x,y in p)) if p else None
def move(p,dx,dy):return {(x+dx,y+dy) for x,y in p}
def raster(p):return bytes(b^255 for b in write_pbm(p).split(b'\n',2)[2])
def save_raw(name,p):
    if any(x<0 or x>199 or y<0 or y>199 for x,y in p):raise ValueError(f'{name} clipped')
    (OUT/'input'/f'{name}.bin').write_bytes(raster(p))
def dock(p,center=155,bottom=55):
    if not p:return set()
    l,t,r,b=bounds(p);return move(p,center-(l+r)//2,bottom-b)

def main():
    for d in ('input','native','images','old','build'):
        target=OUT/d
        if target.exists():shutil.rmtree(target)
        target.mkdir(parents=True,exist_ok=True)
    if (ART/'pbm').exists():shutil.rmtree(ART/'pbm')
    (ART/'pbm').mkdir(parents=True,exist_ok=True)
    authority=load_authority(ROOT);reconstruction=verify_expression_reconstruction(authority)
    if reconstruction['mismatches']:raise ValueError('source component reconstruction drift')
    steps={f'{track}-{i:02d}-{s["cue"]}':(track,i,s) for track,i,s in expression_steps(authority)}
    faces={};ornaments={};poses={};motions={};layout={};originals={};ornament_tracks={};default_ornaments={}
    for family in FAMILIES:
        track,rest_i,rest=steps[FIXTURES[family]]
        rest_face=render_expression_frame(authority,track,rest_i,rest,include_ornaments=False)
        originals[family]=render_expression_frame(authority,track,rest_i,rest)
        l,t,r,b=bounds(rest_face);offset=(100-(l+r)//2,114-(t+b)//2)
        layout[family]={'face_translation':list(offset),'scale':1,'original_face_bounds':[l,t,r,b],
            'anchor_policy':'same family offset for every authored step; anatomy center (100,114)'}
        family_steps=sorted((i,s) for tr,i,s in expression_steps(authority) if tr==track)
        default_ornaments[family]=rest_i
        ornament_tracks[family]=[]
        poses[family]=[]
        for i,s in family_steps:
            name=f'{family}-native-{i}';poses[family].append(name)
            faces[name]=set(render_expression_frame(authority,track,i,s,face_offset=offset,include_ornaments=False))
            ornament=dock(render_expression_frame(authority,track,i,s,include_face=False))
            ornaments[(family,i)]=ornament
            ornament_tracks[family].append({'index':i,'cue':s['cue'],'durationMs':int(s['duration_ms']),
                'pixels':len(ornament),'bounds':bounds(ornament)})
        for suffix in ('rest','blink'):
            name=f'{family}-{suffix}';faces[name]=faces[f'{family}-native-{rest_i}']
            poses[family].append(name)
        if family=='calm':motions[family]=[[f'{family}-native-{i}',900 if i in (0,4) else 700] for i in range(5)]
        else:motions[family]=[[family+'-rest',900],[family+'-native-'+str(2 if family in ('curious','alert') else 1),700],[family+'-rest',1000]]
    save_raw('blink_open',faces['calm-rest']);save_raw('blink_closed',faces['calm-native-2'])

    # Registered small masks, never crops cut out of a flattened face.
    old=ROOT/'docs/art/iterations/companion-wba-expression-v1'
    registry=json.loads((old/'events/event-art.json').read_text(encoding='utf-8'))
    components={c['componentId']:read_pbm(ROOT/c['sourcePbm'])[2] for c in registry['components']}
    specs=[('recording_input','正在录音',2),('upgrade_progress','正在更新',0),
        ('error_caution','需要留意',6),('bottom_connector_charging','正在充电',0),
        ('menu_entry_notice','打开菜单',0),('preparing','准备录音',1),('saving','正在保存',3),
        ('saved','保存完成',4),('sync','正在同步',5),('unavailable','暂不可用',7)]
    functions=[{'id':i,'label':l,'cue':c} for i,l,c in specs]
    masks={};event_meta={e['name']:e for e in registry['events']}
    for event in functions:
        for n,stage in enumerate(STAGES):
            ink=set();name=event['id']
            if name in event_meta and name!='recording_input':
                ids=event_meta[name]['stages'][n]['representativeComponentIds']
                for idx,component_id in enumerate(ids):
                    p=components[component_id]
                    if name=='bottom_connector_charging':p=dock(p,center=100,bottom=195)
                    else:p=dock(p,center=100,bottom=58)
                    ink.update(p)
            masks[(name,stage)]=ink
    # This candidate's explicit microphone/air-wave source uses the existing
    # renderer's SOURCE rectangle. The renderer places it in its safe footer.
    for n,component_id in enumerate((606,608,606)):
        microphone=move(components[605],24,157)
        wave=dock(components[component_id],center=14,bottom=173)
        save_raw(f'candidate-wave-{n}',microphone|wave)
    rows=[];frame_data={};collisions=[]
    for family,pixels in originals.items():
        save_raw('original-'+family,pixels)
        rows.append(f'original-{family} {list(FAMILIES).index(family)} 0 0 0')
    functional_variants=[('none','hold',0,0)]+[(e['id'],s,e['cue'],n) for e in functions for n,s in enumerate(STAGES)]
    for family,pose_names in poses.items():
        for pose in pose_names:
            variants=[(ornament['index'],*variant) for ornament in ornament_tracks[family] for variant in functional_variants]
            for ornament_index,function,stage,cue,wave in variants:
                ornament=ornaments[(family,ornament_index)]
                functional=set() if function=='none' else masks[(function,stage)]
                for layers,label in (((faces[pose],ornament),'face/ornament'),
                    ((faces[pose],functional),'face/functional'),((ornament,functional),'ornament/functional')):
                    overlap=layers[0]&layers[1]
                    if overlap:collisions.append([label,pose,ornament_index,function,stage,len(overlap)])
                pixels=faces[pose]|ornament|functional
                if any(y<16 or y>=172 and 2<=x<42 for x,y in pixels):
                    raise ValueError(f'{pose}/orn{ornament_index}/{function}: reserved status/wave pixels occupied')
                name=f'{pose}__orn{ornament_index}__{function}__{stage}';save_raw(name,pixels)
                rows.append(f'{name} {list(FAMILIES).index(family)} {cue} {int(pose.endswith("-blink"))} {wave}')
                frame_data[name]={'family':family,'pose':pose,'ornament_stage':ornament_index,
                    'ornament_cue':ornament_tracks[family][ornament_index]['cue'],
                    'function':function,'function_stage':stage}
    if collisions:raise ValueError(f'face/ornament collisions: {collisions[:12]}')
    (OUT/'input/frames.txt').write_text('\n'.join(rows)+'\n')
    sources=[APP/p for p in ('runtime/tests/render_screen_art.c','epaper/screen_menu.c','epaper/screen_framebuffer.c',
        'epaper/motion_coordinator.c','touch/browser_interaction_runtime.c','epaper/emote_asset_pack.c','epaper/emote_player.c','epaper/asset_store.c')]
    work=OUT/'build';exe=work/'render.exe';log=work/'build.log';log.write_text('')
    args=['cl.exe','/nologo','/std:c11','/W4','/WX','/utf-8','/DCOMPANION_SCREEN_COMP_REQ_638_SOURCE_PACK=1',
        *(f'/I{p}' for p in INCLUDES),*(str(p) for p in sources),f'/Fe:{exe}']
    cmd=work/'build.cmd';cmd.write_text(f'@echo off\ncall "{find_vsdevcmd()}" -arch=amd64 -host_arch=amd64 >nul\nif errorlevel 1 exit /b %errorlevel%\n'+subprocess.list2cmdline(args)+'\n')
    run(['cmd.exe','/d','/c',str(cmd)],work,log)
    print(run([str(exe),str(OUT/'input'),str(OUT/'native')],work,log),end='')
    for family in FAMILIES:
        Image.frombytes('1',(200,200),(OUT/'native'/f'original-{family}.bin').read_bytes()).save(OUT/'old'/f'{family}.png')
    clips=[];expected=bytearray();assets={};asset_pixels={}
    for name,meta in frame_data.items():
        raw_path=OUT/'native'/f'{name}.bin';raw=raw_path.read_bytes()
        if len(raw)!=5000:raise ValueError(f'{name}: truncated frame')
        digest=hashlib.sha256(raw).hexdigest();asset=assets.get(digest)
        if asset is not None and asset_pixels[digest]!=raw:raise ValueError('SHA-256 collision in candidate frames')
        if asset is None:
            asset=name;assets[digest]=asset;asset_pixels[digest]=raw;expected.extend(raw)
            im=Image.frombytes('1',(200,200),raw);im.save(OUT/'images'/f'{asset}.png');im.save(ART/'pbm'/f'{asset}.pbm')
            if Image.open(OUT/'images'/f'{asset}.png').tobytes()!=raw:raise ValueError('PNG changed framebuffer')
            clips.append({'name':asset,'frames':[{'source':f'pbm/{asset}.pbm','duration_ms':900}]})
        else:raw_path.unlink()
        meta['sha256']=digest;meta['asset']=asset
    manifest={'schema':'companion.emote_asset_pack_manifest.v1','name':'wba-screen-art-v3','revision':3,'priority':0,
        'profile':{'width':200,'height':200,'stride_bytes':25,'pixel_format':'mono_1bpp_white_is_one_msb'},'encoding':'packbits','clips':clips}
    dump(ART/'cemp-manifest.json',manifest);blob,pack=build_pack(ART/'cemp-manifest.json');(ART/'candidate.cemp').write_bytes(blob)
    if len(blob)>2*1024*1024:raise ValueError(f'candidate CEMP exceeds 2MiB UI bank: {len(blob)} bytes')
    shutil.copy2(ART/'candidate.cemp',OUT/'candidate.cemp')
    (OUT/'expected.bin').write_bytes(expected)
    print(run([str(exe),'--verify',str(ART/'candidate.cemp'),str(OUT/'expected.bin')],work,log),end='')
    payload={'families':FAMILIES,'motions':motions,'poses':poses,'ornaments':ornament_tracks,
        'defaultOrnaments':default_ornaments,'frames':frame_data}
    dump(OUT/'frames.json',frame_data)
    page=(ROOT/'tools/wba_screen_art_preview.html').read_text(encoding='utf-8').replace('/*ART_DATA*/',json.dumps(payload,ensure_ascii=False)).replace('/*FUNCTION_DATA*/',json.dumps(functions,ensure_ascii=False))
    (OUT/'index.html').write_text(page,encoding='utf-8')
    active=page.replace('<meta charset="utf-8">','<meta charset="utf-8"><base href="/art/screen-v3/">',1)
    pending=OUT.parent/'index.screen-v3.tmp';pending.write_text(active,encoding='utf-8');pending.replace(OUT.parent/'index.html')
    report={'result':'PASS_SCREEN_ART_SOFTWARE_PIXELS_ONLY','hardwareAcceptance':'NOT_RUN','productionAssetActivation':'NOT_ACTIVE',
        'scope':'V45 material layout + independent face/ornament/functional track calibration + native C framebuffer + browser PNG + CEMP decoder equality; not complete generation21 choreography or resource bank',
        'source_reconstruction':reconstruction,'layout':layout,'frames':len(frame_data),'unique_frame_assets':len(assets),
        'logical_frame_aliases':len(frame_data)-len(assets),'pixel_layer_collisions':len(collisions),
        'face_ornament_collisions':0,'face_function_collisions':0,'ornament_function_collisions':0,
        'all_frames_200x200_1bpp':True,'png_framebuffer_mismatches':0,'pack':pack,'pack_sha256':sha(ART/'candidate.cemp'),
        'preview_html_sha256':sha(OUT/'index.html'),
        'source_sha256':{p.relative_to(ROOT).as_posix():sha(p) for p in [Path(__file__),ROOT/'tools/wba_screen_art_preview.html',ROOT/'tools/wba_native_art_components.py',APP/'runtime/companion_renderer.c',*sources]}}
    dump(ART/'result.json',report);dump(OUT/'result.json',report);dump(ART/'layout.json',{
        'families':layout,'ornament_tracks':ornament_tracks,'default_ornaments':default_ornaments,
        'functional_statuses':functions,'frame_inputs':frame_data})
    print(f'PASS_SCREEN_ART_SOFTWARE_PIXELS_ONLY: {len(frame_data)} complete frames, orthogonal V45 ornament/recording tracks, no pixel collision')
    return 0
if __name__=='__main__':raise SystemExit(main())
