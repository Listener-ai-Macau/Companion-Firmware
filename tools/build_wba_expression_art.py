#!/usr/bin/env python3
"""Compile the WBA art candidate, never replace the accepted generation bank.

Editable full-face SVGs implement the source-referenced design. Chromium is
only the vector rasterizer; native binary compilation has no dithering/scaling.
The candidate CEMP and preview consume identical 200x200/1bpp source pixels.
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

ART = ROOT/'docs/art/iterations/companion-wba-expression-v1'
# Owner rejected this redesign. Rebuilding it must never replace the active
# native-source review page again; retain it only as historical comparison.
OUT = ROOT/'.cache/wba-visual-review/rejected-art-v1'
OLD = ROOT/'docs/art/iterations/companion-pet-expression-v9-two-track-rig-v7/candidate/wb55-browser-parity-attempt-01'
FAMILIES = {
    'calm': ('平静','calm_presence-00-calm_entry'),
    'curious': ('好奇','curious_question-03-question_hold'),
    'delighted': ('开心','delighted_presence-03-delighted_hold'),
    'warm': ('亲近','warm_presence-03-warm_hold'),
    'playful': ('顽皮','playful_presence-03-playful_hold'),
    'sleepy': ('困倦','sleepy_presence-00-sleep_entry'),
    'bashful': ('害羞','bashful_presence-03-bashful_hold'),
    'thoughtful': ('思考','thoughtful_presence-03-thoughtful_hold'),
    'focused': ('专注','focused_presence-03-focused_hold'),
    'alert': ('警觉','alert_exclamation-03-exclamation_hold'),
}

def sha(path): return hashlib.sha256(path.read_bytes()).hexdigest()
def dump(path, value): path.write_text(json.dumps(value,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
def path(d, fill='none', stroke='black', width=2.4):
    return f'<path d="{d}" fill="{fill}" stroke="{stroke}" stroke-width="{width}" stroke-linecap="round" stroke-linejoin="round"/>'

def eye(cx, family, side, phase, gaze=(0,0), closed=False):
    # A single glossy egg silhouette is retained across all open-eye families.
    # Lids are cuts INSIDE that silhouette: no detached bowl or dangling shard.
    cy=109; cx+=gaze[0]*0.35; out=[]
    if closed or (family=='playful' and side==0 and phase!='settle'):
        bend=-5 if family in ('playful','delighted') else 5
        return path(f'M {cx-10} {cy} Q {cx} {cy+bend} {cx+10} {cy}',width=2.8)
    ry=17 if family!='alert' else 18
    d=f'M {cx-1} {cy-ry} C {cx-16} {cy-ry-1} {cx-17} {cy+13} {cx-5} {cy+ry} C {cx+10} {cy+ry+3} {cx+17} {cy+3} {cx+10} {cy-11} C {cx+8} {cy-ry} {cx+4} {cy-ry-1} {cx-1} {cy-ry} Z'
    out.append(f'<defs><clipPath id="eye{side}">{path(d,"black","none",0)}</clipPath></defs>')
    out.append(f'<g clip-path="url(#eye{side})">'+path(d,'black','none',0))
    lid={'warm':102,'sleepy':112,'thoughtful':103 if side else 96,'focused':103,
         'bashful':98,'curious':95 if side else 91}.get(family,90)
    if phase=='react':
        lid+=3 if family in ('warm','sleepy','bashful') else -1
    if phase=='settle': lid+=1 if family not in ('alert','curious') else 0
    # Soft arced upper boundary rather than the rigid flat visor in older art.
    tilt=(2 if side else -2) if family=='focused' else 0
    if lid>92:
        out.append(path(f'M {cx-18} 86 H {cx+18} V {lid+tilt} Q {cx} {lid-9} {cx-18} {lid-tilt} Z','white','none',0))
    gx=cx-4+gaze[0]; gy=max(cy-8,lid+6)+gaze[1]
    gh=4.8 if lid<97 else 3.8 if lid<105 else 2.5
    out.append(f'<ellipse cx="{gx}" cy="{gy}" rx="3.8" ry="{gh}" fill="white" transform="rotate(24 {gx} {gy})"/>')
    hx=cx+5+gaze[0]*0.4; hy=cy+(2 if family=='delighted' else 6)+gaze[1]*0.4
    out.append(path(f'M {hx} {hy-2.3} L {hx+2.1} {hy} L {hx} {hy+2.3} L {hx-2.1} {hy} Z','white','none',0))
    if family=='delighted':
        bottom=121 if phase!='react' else 117
        out.append(path(f'M {cx-18} {bottom} Q {cx} {bottom-7} {cx+18} {bottom} V 135 H {cx-18} Z','white','none',0))
    out.append('</g>')
    return ''.join(out)

def brows(family,phase):
    out=[]
    for side,cx in enumerate((73,127)):
        y=80; tilt=0; arch=-4
        if family=='curious': y=80 if not side else 87;tilt=2 if side else -1
        elif family=='warm': y=88; arch=-4
        elif family=='sleepy': y=94; arch=-3
        elif family=='bashful': y=82;tilt=2 if not side else -2;arch=-2
        elif family=='thoughtful': y=81 if not side else 88;arch=-3 if not side else -2
        elif family=='focused': y=89;tilt=1 if not side else -1;arch=-3
        elif family=='alert': y=78;arch=-5
        elif family=='delighted': y=79;arch=-5
        elif family=='playful': y=82 if not side else 77;arch=-3
        if phase=='react': y+=-1 if family in ('alert','curious','delighted') else 1
        out.append(path(f'M {cx-7} {y-tilt} Q {cx} {y+arch} {cx+7} {y+tilt}',width=2.6))
    return ''.join(out)

def mouth(family,phase):
    if family=='calm': return path('M 91 133 Q 94 140 100 133 Q 106 140 109 133',width=2.3)
    if family=='bashful': return path('M 94 134 Q 103 141 107 132',width=2.3)
    if family=='warm':
        dip=142 if phase=='react' else 140
        return path(f'M 92 133 Q 100 {dip} 108 133',width=2.3)
    if family=='delighted':
        h=143 if phase=='react' else 140
        return path(f'M 92 131 Q 100 133 108 131 Q 108 {h} 100 {h} Q 92 {h} 92 131 Z','black','none',0)+path(f'M 97 {h-4} Q 100 {h-6} 103 {h-4} Q 102 {h-1} 100 {h-1} Q 98 {h-1} 97 {h-4} Z','white','none',0)
    if family=='playful': return path('M 92 134 Q 102 141 108 132',width=2.3)
    if family in ('curious','alert') or (family=='sleepy' and phase=='react'):
        rx=3.5 if family!='alert' else 4; ry=4.2 if phase!='react' else 5.3
        return f'<ellipse cx="100" cy="135" rx="{rx}" ry="{ry}" fill="none" stroke="black" stroke-width="2.1"/>'
    if family=='thoughtful': return path('M 95 135 Q 100 133 105 134',width=2.1)
    return path('M 96 134 Q 100 136 104 134',width=2.3)

def face(family,phase,gaze=(0,0),closed=False):
    if family=='bashful': gaze=(1,2)
    if family=='thoughtful': gaze=(-2,-1)
    return ('<svg xmlns="http://www.w3.org/2000/svg" width="200" height="200" viewBox="0 0 200 200">'
        '<rect width="200" height="200" fill="white"/>' +
        eye(73,family,0,phase,gaze,closed)+eye(127,family,1,phase,gaze,closed)+brows(family,phase)+
        '<ellipse cx="56" cy="130" rx="4" ry="2.2" fill="black"/>'
        '<ellipse cx="144" cy="130" rx="4" ry="2.2" fill="black"/>'+
        path('M 96 124 Q 100 121 104 124 Q 104 126 100 128 Q 96 126 96 124 Z','black','none',0)+
        mouth(family,phase)+'</svg>')

def emotion_accents():
    """New candidate registrations from traced V9 ink, separate from V45 IDs."""
    base=ROOT/'docs/art/iterations/companion-pet-expression-v9-rig-v1/candidate/rendered-200x200/components'
    directory=ART/'emotions';directory.mkdir(exist_ok=True)
    rows=[]
    specs=[('pet_heart','charm_heart.pbm','98a4aab8d4c4be9adb14f3ea4c37ed9b4ed1beb434ab76315ea6443f957bc863',
            'accepted petting reaction; never recording, charging or save success'),
           ('delight_star','charm_star.pbm','e813bf81e43559f5ae2a7642d67deb57f29ee408ed46114f2f39164c9b53da50',
            'delighted reaction accent; not a device acknowledgement')]
    for name,filename,expected,trigger in specs:
        source=base/filename
        if sha(source)!=expected:raise ValueError('V9 emotion source identity changed')
        mask=Image.open(source)
        if mask.mode!='1':raise ValueError('V9 emotion is not 1bpp')
        shutil.copy2(source,directory/filename)
        stages=[]
        for stage,y in [('entered',39),('hold',35),('exit',31)]:
            layer=Image.new('1',(200,200),1);layer.paste(mask,((200-mask.width)//2,y))
            filename_out=f'{name}-{stage}.png';layer.save(directory/filename_out)
            stages.append({'stage':stage,'outputLayerPng':filename_out,'sha256':sha(directory/filename_out)})
        rows.append({'name':name,'kind':'emotion','assetRoot':'emotions','status':'NEW_WBA_CANDIDATE_REGISTRATION_NOT_V45',
            'triggerContract':trigger,'sourcePbm':source.relative_to(ROOT).as_posix(),'sourceSha256':expected,
            'pixelPolicy':'byte-identical V9 mask; integer position changes only; withdraw after tail', 'stages':stages})
    dump(directory/'emotion-art.json',{'schema':'companion.wba.new_emotion_art.v1','events':rows})
    return rows

def native_composition():
    work=OUT/'build';work.mkdir(exist_ok=True); log=work/'build.log';log.write_text('')
    sources=[APP/n for n in ('runtime/tests/render_art_candidate.c','epaper/screen_menu.c',
        'epaper/screen_framebuffer.c','epaper/motion_coordinator.c','touch/browser_interaction_runtime.c',
        'epaper/emote_asset_pack.c','epaper/emote_player.c','epaper/asset_store.c')]
    exe=work/'render.exe'
    args=['cl.exe','/nologo','/std:c11','/W4','/WX','/utf-8','/DCOMPANION_SCREEN_COMP_REQ_638_SOURCE_PACK=1',
        *(f'/I{p}' for p in INCLUDES),*(str(p) for p in sources),f'/Fe:{exe}']
    script=work/'build.cmd'
    script.write_text(f'@echo off\ncall "{find_vsdevcmd()}" -arch=amd64 -host_arch=amd64 >nul\nif errorlevel 1 exit /b %errorlevel%\n'+subprocess.list2cmdline(args)+'\n')
    run(['cmd.exe','/d','/c',str(script)],work,log)
    result=run([str(exe),str(ART/'bin'),str(OUT/'native'),str(ART/'candidate.cemp'),str(OUT/'pack-expected.bin')],work,log);print(result,end='')
    if 'PASS_ART_CANDIDATE_COMPOSITION' not in result: raise ValueError('native compositor failed')
    return sources+[APP/'runtime/companion_renderer.c']

def main():
    for d in (ART/'svg',ART/'raster',ART/'bin',ART/'pbm',OUT/'images',OUT/'old',OUT/'native'):
        d.mkdir(parents=True,exist_ok=True)
    states={}
    for family in FAMILIES:
        for phase in ('rest','react','settle','closed'):
            name=f'{family}-{phase}';states[name]={'family':family,'phase':phase}
            (ART/'svg'/f'{name}.svg').write_text(face(family,'rest' if phase=='closed' else phase,closed=phase=='closed'),encoding='utf-8')
    for label,gaze in {'left':(-2,0),'right':(2,0),'up':(0,-2),'down':(0,2)}.items():
        name='calm-look-'+label;states[name]={'family':'calm','phase':'gaze','gaze':label}
        (ART/'svg'/f'{name}.svg').write_text(face('calm','rest',gaze=gaze),encoding='utf-8')
    subprocess.run(['node',str(ROOT/'tools/rasterize_wba_expression_art.mjs'),str(ART)],check=True)
    for name in states:
        im=Image.open(ART/'raster'/f'{name}.png').convert('L')
        if im.size!=(200,200): raise ValueError('rasterizer changed native canvas')
        im=im.point(lambda p:255 if p>=128 else 0,'1')
        raw=im.tobytes();(ART/'bin'/f'{name}.bin').write_bytes(raw)
        im.save(ART/'pbm'/f'{name}.pbm');im.save(ART/'raster'/f'{name}.png')
        if parse_p4(ART/'pbm'/f'{name}.pbm',200,200)!=raw:raise ValueError('PBM polarity differs')
        ink=im.convert('L').point(lambda p:255-p).getbbox()
        if not ink or ink[0]<50 or ink[1]<68 or ink[2]>150 or ink[3]>145:raise ValueError(f'face escapes envelope: {name} {ink}')
        if raw[:400]!=b'\xff'*400:raise ValueError('art owns status pixels')
        states[name].update(svg_sha256=sha(ART/'svg'/f'{name}.svg'),pixel_sha256=hashlib.sha256(raw).hexdigest(),ink_bounds=ink)
    (ART/'bin/frames.txt').write_text('\n'.join(states)+'\n')
    clips=[]
    def add_clip(name,frames):
        clips.append({'name':name,'loop_start':0,'loop_end':len(frames),'frames':[
            {'source':f'pbm/{n}.pbm','duration_ms':ms,'dirty':[0,16,200,184]} for n,ms in frames]})
    for family in FAMILIES:
        add_clip(family+'-presence',[(family+'-rest',1800),(family+'-react',700),(family+'-settle',900)])
        add_clip(family+'-closed',[(family+'-closed',480)])
    for label in ('left','right','up','down'):add_clip('gaze-'+label,[('calm-look-'+label,700)])
    stories={
        'hello':{'label':'打个招呼','frames':[['calm-rest',700],['curious-react',900],['warm-rest',1300],['calm-rest',1200]],'trigger':'explicit preview / interaction event, never automatic BLE connection'},
        'pet':{'label':'摸摸它','frames':[['calm-rest',500],['warm-rest',700],['warm-react',1100],['warm-closed',700],['warm-settle',1100]],'trigger':'accepted petting gesture; independent emotion ornament permitted'},
        'lift':{'label':'拿起来看看','frames':[['calm-rest',500],['curious-react',900],['calm-look-left',850],['calm-look-right',850],['curious-settle',1300]],'trigger':'IMU pickup event, not every sample'},
        'rest':{'label':'放下，慢慢安定','frames':[['curious-rest',800],['calm-rest',1000],['sleepy-rest',1800],['sleepy-react',1000],['sleepy-closed',2200]],'trigger':'quiet/low-energy scenario; setting down alone must not force sleep'},
    }
    for name,story in stories.items():add_clip('reaction-'+name,story['frames'])
    event_manifest=json.loads((ART/'events/event-art.json').read_text(encoding='utf-8'))
    event_labels={'recording_input':'录音 · 麦克风与波纹','upgrade_progress':'正在更新','error_caution':'需要留意',
        'bottom_connector_charging':'正在充电','menu_entry_notice':'打开菜单','curious_question':'好奇 · 小问号',
        'alert_exclamation':'惊讶 · 小叹号','sleep_zzz':'困了 · 小睡意','pet_heart':'喜欢摸摸 · 小心意','delight_star':'开心 · 小星光'}
    events=[]
    for event in [*event_manifest['events'],*emotion_accents()]:
        asset_root=event.get('assetRoot','events')
        layers={stage['stage']:stage['outputLayerPng'] for stage in event['stages']}
        events.append({'id':event['name'],'label':event_labels[event['name']],'kind':event['kind'],
            'triggerContract':event['triggerContract'],'layers':layers,'assetRoot':asset_root})
        overlay_frames=[]
        for stage in event['stages']:
            im=Image.open(ART/asset_root/stage['outputLayerPng'])
            if im.size!=(200,200) or im.mode!='1':raise ValueError('overlay is not native binary')
            raw=im.tobytes()
            if raw[:400]!=b'\xff'*400 or raw[68*25:]!=b'\xff'*(132*25):raise ValueError('overlay invaded status or face')
            name='ornament-'+event['name']+'-'+stage['stage']
            im.save(ART/'pbm'/f'{name}.pbm')
            overlay_frames.append({'source':f'pbm/{name}.pbm','duration_ms':700 if stage['stage']!='hold' else 1800,'dirty':[0,16,200,52]})
        clips.append({'name':'ornament-'+event['name'],'loop_start':1,'loop_end':2,'frames':overlay_frames})
    manifest={'schema':'companion.emote_asset_pack_manifest.v1','name':'wba-expression-art-candidate-v1','revision':1,'priority':0,
        'profile':{'width':200,'height':200,'stride_bytes':25,'pixel_format':'mono_1bpp_white_is_one_msb'},'encoding':'packbits','clips':clips}
    dump(ART/'cemp-manifest.json',manifest)
    data,pack=build_pack(ART/'cemp-manifest.json');(ART/'candidate.cemp').write_bytes(data)
    (OUT/'pack-expected.bin').write_bytes(b''.join(parse_p4(ART/f['source'],200,200) for clip in clips for f in clip['frames']))
    sources=native_composition()
    for p in (OUT/'native').glob('*.bin'):
        Image.frombytes('1',(200,200),p.read_bytes()).save(OUT/'images'/f'{p.stem}.png')
    for family,(_,stem) in FAMILIES.items():
        current=OUT.parent/'images'/f'family-{family}.png'
        shutil.copy2(current if current.exists() else OLD/(stem+'.png'),OUT/'old'/f'{family}.png')
    # Same bitwise black-ink union as the registered two-track material: these
    # full frames are auditable against the independently selectable UI layers.
    mixed=OUT/'mixed';mixed.mkdir(exist_ok=True)
    compositions={}
    for family in FAMILIES:
        base=(OUT/'native'/f'{family}-rest.bin').read_bytes()
        for event in events:
            for stage,layer in event['layers'].items():
                overlay=Image.open(ART/event['assetRoot']/layer).tobytes()
                merged=bytes(a&b for a,b in zip(base,overlay))
                if merged[:400]!=base[:400] or merged[68*25:]!=base[68*25:]:raise ValueError('ornament mutated face or rail')
                name=family+'-'+event['id']+'-'+stage
                Image.frombytes('1',(200,200),merged).save(mixed/f'{name}.png')
                compositions[name]=hashlib.sha256(merged).hexdigest()
    shutil.copytree(ART/'events',OUT/'events',dirs_exist_ok=True)
    shutil.copytree(ART/'emotions',OUT/'emotions',dirs_exist_ok=True)
    font=ImageFont.truetype('C:/Windows/Fonts/msyh.ttc',16)
    title=ImageFont.truetype('C:/Windows/Fonts/msyh.ttc',24)
    sheet=Image.new('RGB',(1140,1050),'#f4f1ea');draw=ImageDraw.Draw(sheet)
    draw.text((20,14),'Companion · 表情精修候选 / 原生 200×200',font=title,fill='#202721')
    draw.text((20,51),'每组上方为现有素材，下方为精修候选；表情不自带事件符号，饰品独立合成。',font=font,fill='#506054')
    for i,(family,(label,_)) in enumerate(FAMILIES.items()):
        x=20+(i%5)*224;y=94+(i//5)*462
        sheet.paste(Image.open(OUT/'old'/f'{family}.png').convert('RGB'),(x,y))
        sheet.paste(Image.open(OUT/'images'/f'{family}-rest.png').convert('RGB'),(x,y+214))
        draw.text((x,y+419),label+' · 之前 / 精修',font=font,fill='#202721')
    sheet.save(OUT/'comparison.png')
    # Template owns interaction, frame selection and independent overlay state.
    page=(ROOT/'tools/wba_expression_art_preview.html').read_text(encoding='utf-8')
    payload={'families':{n:v[0] for n,v in FAMILIES.items()},'stories':stories}
    page=page.replace('/*ART_DATA*/',json.dumps(payload,ensure_ascii=False)).replace('/*EVENT_DATA*/',json.dumps(events,ensure_ascii=False))
    (OUT/'index.html').write_text(page,encoding='utf-8')
    shutil.copy2(ART/'reference-v1.png',OUT/'reference-v1.png')
    report={'result':'PASS_ART_CANDIDATE_SOFTWARE_ONLY','hardwareAcceptance':'NOT_RUN','productionActivation':'NOT_ACTIVE',
        'generation21':'UNCHANGED; this is an independent candidate, not its missing full replacement',
        'canvas':[200,200],'pixel_format':'1bpp_white_is_one_msb','native_frames':len(states),'states':states,
        'pack':pack,'pack_sha256':sha(ART/'candidate.cemp'),'compositions':compositions,
        'sources':{p.relative_to(ROOT).as_posix():sha(p) for p in [Path(__file__),ROOT/'tools/rasterize_wba_expression_art.mjs',ROOT/'tools/wba_expression_art_preview.html',ROOT/'tools/collect_wba_event_art.py',ART/'events/event-art.json',ART/'emotions/emotion-art.json',ART/'reference-v1.png',*sources]},
        'invariants':{'face_envelope':[50,68,150,145],'face_excludes_status_and_ornament':True,'native_C_preserves_face_pixels':True,'all_families_blink_restore':True,'hold_preserves_face':True,'cemp_packbits_roundtrip':True,'production_C_decoder_bit_exact':True,'damaged_CEMP_payload_rejected':True,'independent_overlay_combinations':len(compositions)},
        'research':[{'url':'https://www.good-display.com/product/258.html','finding':'GDEY0154D67-T03: 200x200 SSD1681; published 0.3s partial refresh. Fitted suffix and hardware timings unverified.'}],
        'reference_tool':'built-in image_gen; full prompt in generation-prompt.txt; reference not directly downsampled into firmware'}
    dump(ART/'art-manifest.json',report);dump(OUT/'result.json',report)
    print(f'PASS_ART_CANDIDATE_SOFTWARE_ONLY: {len(states)} native faces, {len(clips)} candidate CEMP clips, {len(data)} bytes; NOT_ACTIVE')
    return 0

if __name__=='__main__':raise SystemExit(main())
