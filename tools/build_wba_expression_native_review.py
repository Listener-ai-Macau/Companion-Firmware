#!/usr/bin/env python3
"""Restore the actual retained native art; no redraw, resize or re-anchoring.

The owner rejected the SVG redesign. Source pixels are now authoritative.
All rest poses must be identical to the preceding 'original' panel below the
status rail. This tool makes a restoration review, not an art-acceptance claim.
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
from render_wba_visual_review import ART as SOURCE, FIXTURES, FAMILIES as LABELS

ART=ROOT/'docs/art/iterations/companion-wba-expression-native-v2'
OUT=ROOT/'.cache/wba-visual-review/art/native-v2'
FAMILIES=dict(zip(list(FIXTURES)[:10],LABELS))

def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def dump(p,value):p.write_text(json.dumps(value,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')

def main():
    for d in ('bin','pbm'):(ART/d).mkdir(parents=True,exist_ok=True)
    for d in ('images','old','native','build'):(OUT/d).mkdir(parents=True,exist_ok=True)
    mapping={}; motions={}
    for family in FAMILIES:
        base=FIXTURES[family];prefix=base.split('-00-')[0] if '-00-' in base else base.split('-03-')[0]
        original=sorted(SOURCE.glob(prefix+'-0[0-4]-*.png'))
        if len(original)!=5:raise ValueError(f'{family} native score incomplete')
        mapping[family+'-rest']=SOURCE/(base+'.png')
        mapping[family+'-react']=original[2 if family in ('curious','alert') else 1]
        mapping[family+'-settle']=mapping[family+'-rest']
        motions[family]=[]
        for i,p in enumerate(original):
            name=family+'-native-'+str(i);mapping[name]=p
            motions[family].append([name,900 if i in (0,4) else 700])
        if family!='calm':motions[family]=[[family+'-rest',900],[family+'-react',700],[family+'-rest',900]]
    mapping['calm-closed']=SOURCE/(FIXTURES['blink_closed']+'.png')
    provenance={}
    for name,p in mapping.items():
        im=Image.open(p)
        if im.size!=(200,200) or not set(im.convert('L').getdata()).issubset({0,255}):raise ValueError('source is not native 1bpp')
        raw=im.convert('1',dither=Image.Dither.NONE).tobytes()
        (ART/'bin'/f'{name}.bin').write_bytes(raw);im.convert('1').save(ART/'pbm'/f'{name}.pbm')
        if parse_p4(ART/'pbm'/f'{name}.pbm',200,200)!=raw:raise ValueError('format conversion changed native pixels')
        provenance[name]={'source':p.relative_to(ROOT).as_posix(),'source_sha256':sha(p),'pixel_sha256':hashlib.sha256(raw).hexdigest()}
    (ART/'bin/frames.txt').write_text('\n'.join(mapping)+'\n')
    clips=[{'name':family+'-native','loop_start':0,'loop_end':len(score),'frames':[
        {'source':f'pbm/{name}.pbm','duration_ms':ms,'dirty':[0,16,200,184]} for name,ms in score]} for family,score in motions.items()]
    clips.extend({'name':family+'-rest','frames':[{'source':f'pbm/{family}-rest.pbm','duration_ms':1800}]} for family in FAMILIES)
    manifest={'schema':'companion.emote_asset_pack_manifest.v1','name':'wba-native-restoration-review-v2','revision':2,'priority':0,
        'profile':{'width':200,'height':200,'stride_bytes':25,'pixel_format':'mono_1bpp_white_is_one_msb'},'encoding':'packbits','clips':clips}
    dump(ART/'cemp-manifest.json',manifest)
    blob,pack=build_pack(ART/'cemp-manifest.json');(ART/'candidate.cemp').write_bytes(blob)
    (OUT/'expected.bin').write_bytes(b''.join(parse_p4(ART/f['source'],200,200) for clip in clips for f in clip['frames']))
    sources=[APP/p for p in ('runtime/tests/render_art_candidate.c','epaper/screen_menu.c','epaper/screen_framebuffer.c',
        'epaper/motion_coordinator.c','touch/browser_interaction_runtime.c','epaper/emote_asset_pack.c','epaper/emote_player.c','epaper/asset_store.c')]
    work=OUT/'build';exe=work/'render.exe';log=work/'build.log';log.write_text('')
    args=['cl.exe','/nologo','/std:c11','/W4','/WX','/utf-8','/DCOMPANION_SCREEN_COMP_REQ_638_SOURCE_PACK=1',
        *(f'/I{p}' for p in INCLUDES),*(str(p) for p in sources),f'/Fe:{exe}']
    cmd=work/'build.cmd';cmd.write_text(f'@echo off\ncall "{find_vsdevcmd()}" -arch=amd64 -host_arch=amd64 >nul\nif errorlevel 1 exit /b %errorlevel%\n'+subprocess.list2cmdline(args)+'\n')
    run(['cmd.exe','/d','/c',str(cmd)],work,log)
    result=run([str(exe),str(ART/'bin'),str(OUT/'native'),str(ART/'candidate.cemp'),str(OUT/'expected.bin')],work,log);print(result,end='')
    if 'PASS_ART_CANDIDATE_COMPOSITION' not in result:raise ValueError('production compositor failed')
    for name in [*mapping,*(f+'-rest-blink' for f in FAMILIES)]:
        raw=(OUT/'native'/f'{name}.bin').read_bytes()
        Image.frombytes('1',(200,200),raw).save(OUT/'images'/f'{name}.png')
    # Closed holds reuse the actual production blink result for THAT family.
    for family in FAMILIES:shutil.copy2(OUT/'images'/f'{family}-rest-blink.png',OUT/'images'/f'{family}-closed.png')
    fidelity={}
    for family in FAMILIES:
        p=OUT.parent/'old'/f'{family}.png'
        expected=Image.open(p).convert('1').tobytes()
        actual=(OUT/'native'/f'{family}-rest.bin').read_bytes()
        changed=sum((a^b).bit_count() for a,b in zip(expected[400:],actual[400:]))
        if changed:raise ValueError(f'restoration changed {family}: {changed} source pixels')
        shutil.copy2(p,OUT/'old'/f'{family}.png')
        fidelity[family]={'reference_sha256':sha(p),'face_changed_pixels':changed,'source_shape_resize':False,'source_anchor_translation':False}
    previous=ROOT/'docs/art/iterations/companion-wba-expression-v1'
    event_data=json.loads((previous/'events/event-art.json').read_text(encoding='utf-8'))['events']
    event_data+=json.loads((previous/'emotions/emotion-art.json').read_text(encoding='utf-8'))['events']
    labels={'recording_input':'录音 · 麦克风与波纹','upgrade_progress':'正在更新','error_caution':'需要留意','bottom_connector_charging':'正在充电',
        'menu_entry_notice':'打开菜单','curious_question':'小问号','alert_exclamation':'小叹号','sleep_zzz':'小睡意','pet_heart':'摸摸 · 小心意','delight_star':'小星光'}
    events=[{'id':e['name'],'label':labels[e['name']],'kind':e['kind'],'assetRoot':e.get('assetRoot','events'),
        'layers':{s['stage']:s['outputLayerPng'] for s in e['stages']}} for e in event_data]
    for d in ('events','emotions'):shutil.copytree(previous/d,OUT/d,dirs_exist_ok=True)
    payload={'families':FAMILIES,'motions':motions,'stories':{'pet':{'label':'摸摸当前这只','frames':[]}}}
    page=(ROOT/'tools/wba_expression_native_preview.html').read_text(encoding='utf-8')
    page=page.replace('/*ART_DATA*/',json.dumps(payload,ensure_ascii=False)).replace('/*EVENT_DATA*/',json.dumps(events,ensure_ascii=False))
    (OUT/'index.html').write_text(page,encoding='utf-8')
    # Publish last with a versioned base so a cached v1 image can never appear
    # in the restored page. Preserve the rejected directory and immutable ZIP.
    active=page.replace('<meta charset="utf-8">','<meta charset="utf-8"><base href="/art/native-v2/">',1)
    pending=OUT.parent/'index.native-v2.tmp';pending.write_text(active,encoding='utf-8');pending.replace(OUT.parent/'index.html')
    report={'result':'PASS_NATIVE_SOURCE_RESTORATION_ONLY','artAcceptance':'NOT_CLAIMED','hardwareAcceptance':'NOT_RUN','productionActivation':'NOT_ACTIVE',
        'rejectedDirection':'companion-wba-expression-v1','native_source_frames':len(mapping),'restoredFamilies':fidelity,'provenance':provenance,
        'pack':pack,'pack_sha256':sha(ART/'candidate.cemp'),'sources':{p.relative_to(ROOT).as_posix():sha(p) for p in [Path(__file__),ROOT/'tools/wba_expression_native_preview.html',APP/'runtime/companion_renderer.c',*sources]}}
    dump(ART/'restoration-result.json',report);dump(OUT/'result.json',report)
    print('PASS_NATIVE_SOURCE_RESTORATION_ONLY: ten rest poses match original pixels; no art acceptance claim')
    return 0

if __name__=='__main__':raise SystemExit(main())
