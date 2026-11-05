"""Author/export P13 native scene composition; simulated context, no board I/O.

P09 owns face and motion. This pure C layer places supplied functional status
and draft text at native 1bpp size, without changing timing or resource banks.
"""
from pathlib import Path
from datetime import datetime
import ctypes
import faulthandler
import hashlib
import json
import subprocess
import sys
from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parents[1]
BASE = ROOT / '.cache/screen-art-polish-20261011'
ART = ROOT / 'docs/art/iterations/companion-pet-studio-v1/p13'
BUILD = BASE / 'preview-build-p13'
PUBLIC = BASE / 'studio-p13'
FONT_PATH = Path('C:/Windows/Fonts/msyh.ttc')
GLYPH_HEIGHT = 13
GLYPH_ASCENDER_OFFSET = 2
TEXTS = dict(companion='小伙伴', record='开始录音', company='陪伴设置',
             power='电量与充电', return_='返回', listening='认真听着',
             thinking='让我想一想。', reply_one='听起来有点累了。',
             reply_two='要不要一起歇一会？', connected='已接电源',
             charging='正在充电', updating='正在更新', done='准备好啦。',
             low_one='有点困啦。', low_two='给我充一会儿电吧。')

def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()

def glyph_rows(char, font, width, height):
    # Native raster authoring. No scaled face, generated bitmap or antialias
    # pixels are imported into the proposal.
    bitmap = Image.new('1', (width, height), 1)
    draw = ImageDraw.Draw(bitmap)
    # A shared ascender origin is essential: per-glyph top alignment shifts
    # short strokes such as 一 and punctuation to the top of the text row.
    draw.text((0, -GLYPH_ASCENDER_OFFSET), char, font=font, fill=0, anchor='la')
    rows = [sum((1 << (width - 1 - x)) for x in range(width)
                if bitmap.getpixel((x, y)) == 0) for y in range(height)]
    return rows

def generate_glyphs():
    font = ImageFont.truetype(str(FONT_PATH), 12)
    chars = sorted(set(''.join(TEXTS.values())) | set('0123456789:%'))
    header = ['/* P11 native glyphs. Shared baseline, regular weight, 1px letter space. */',
              '#include <stdint.h>',
              '#define SCENE_GLYPH_HEIGHT 13u',
              'typedef struct {uint16_t code;uint8_t advance;uint16_t rows[13];} scene_glyph_t;',
              'static const scene_glyph_t scene_glyphs[]={']
    for ch in chars:
        bounds = font.getbbox(ch, anchor='la')
        if bounds[1] < GLYPH_ASCENDER_OFFSET or bounds[3] > GLYPH_ASCENDER_OFFSET + GLYPH_HEIGHT:
            raise RuntimeError('Glyph would lose strokes at the shared baseline: '+ch)
        rows = glyph_rows(ch, font, 12, GLYPH_HEIGHT)
        advance = max(1, round(font.getlength(ch))) + 1
        if advance > 13:
            raise RuntimeError('Draft glyph exceeds its native cell: '+ch)
        header.append('{%du,%du,{%s}},' % (ord(ch), advance, ','.join(str(x)+'u' for x in rows)))
    header += ['};']
    # 5x7 style used by the existing clock; explicit native rail glyphs.
    rail = {'0':['01110','10001','10011','10101','11001','10001','01110'],
            '1':['00100','01100','00100','00100','00100','00100','01110'],
            '2':['01110','10001','00001','00010','00100','01000','11111'],
            '3':['11110','00001','00001','01110','00001','00001','11110'],
            '4':['00010','00110','01010','10010','11111','00010','00010'],
            '5':['11111','10000','10000','11110','00001','00001','11110'],
            '6':['01110','10000','10000','11110','10001','10001','01110'],
            '7':['11111','00001','00010','00100','01000','01000','01000'],
            '8':['01110','10001','10001','01110','10001','10001','01110'],
            '9':['01110','10001','10001','01111','00001','00001','01110'],
            '%':['11001','11010','00100','00100','01000','10110','00110'],
            '~':['00000','00000','01000','10101','00010','00000','00000']}
    header += ['typedef struct {uint8_t code,advance,rows[7];} scene_rail_glyph_t;',
               'static const scene_rail_glyph_t scene_rail_glyphs[]={']
    for ch, rows in rail.items():
        header.append('{%du,6u,{%s}},' % (ord(ch), ','.join(str(int(x+'0', 2))+'u' for x in rows)))
    header += ['};']
    for key, phrase in TEXTS.items():
        name = key.removesuffix('_')
        header.append('static const uint16_t scene_text_%s[]={%s,0u};' %
                      (name, ','.join(str(ord(ch))+'u' for ch in phrase)))
    (ART/'scene_glyphs.h').write_text('\n'.join(header)+'\n', encoding='utf-8')
    return {key: sum(max(1, round(font.getlength(ch))) + 1 for ch in value) for key, value in TEXTS.items()}

class Scene(ctypes.Structure):
    _fields_ = [(name, ctypes.c_uint) for name in ('kind','battery_percent',
        'battery_valid','battery_estimated','progress','elapsed_seconds','menu_selection')]

def main():
    BUILD.mkdir(exist_ok=True)
    PUBLIC.mkdir(exist_ok=True)
    widths = generate_glyphs()
    if any(width > 176 for width in widths.values()):
        raise RuntimeError('Caption exceeds the existing 176px text slot')
    import companion_pet_studio as studio
    studio.DESIGN = 'P09'
    studio.DLL = BASE/'preview-build-p09/wba-runtime-preview.dll'
    parent = studio.inputs()  # validate the exact reused compiled face inputs
    preview = sys.modules['wba_runtime_preview']
    dll_path = BUILD/'pet-scene-design.dll'
    args = ['cl.exe','/nologo','/std:c11','/W4','/WX','/utf-8','/LD',
            str(ART/'scene_compositor.c'),f'/Fe:{dll_path}']
    command = BUILD/'build.cmd'
    command.write_text('@echo off\ncall "'+str(preview.find_vsdevcmd())+
        '" -arch=amd64 -host_arch=amd64 >nul\nif errorlevel 1 exit /b %errorlevel%\n'+
        subprocess.list2cmdline(args)+'\n', encoding='utf-8')
    preview.run(['cmd.exe','/d','/c',str(command)],BUILD,BUILD/'build.log')
    library = ctypes.CDLL(str(dll_path))
    library.comp_scene_design_render.argtypes = [ctypes.POINTER(ctypes.c_uint8),ctypes.POINTER(Scene)]
    library.comp_scene_design_render.restype = ctypes.c_int
    # Context and example phrases are authored inputs, not live peripherals or
    # AI conversation. The family renderer and original ornaments are P09 C.
    cases = [('home','安静陪伴',0,0,78,0), ('listen','认真听你说',1,8,78,0),
             ('think','想一想',2,7,78,0), ('reply','用文字回应',3,3,78,0),
             ('connected','接入电源',4,0,78,0), ('charge','确认正在充电',5,3,78,0),
             ('update','更新中',6,8,78,42), ('done','更新完成',7,2,78,100),
             ('menu','打开菜单',8,0,78,0), ('low','低电量',9,5,18,0)]
    samples=[]
    faulthandler.dump_traceback_later(20,exit=True)
    selected_poses=dict(listen='detail-after-focused.png',
                        think='detail-after-thoughtful.png',
                        charge='tone-warm-58.png',done='detail-after-delighted.png')
    inherited={'home','reply','connected','low'}
    for name, label, kind, family, battery, progress in cases:
        face_path=BASE/'studio-p09'/selected_poses.get(name,f'pose-{family}.png')
        frame=Image.open(face_path).convert('1')
        pose=dict(source=str(face_path.relative_to(ROOT)),sha256=sha(face_path),
                  kind='REUSED_P09_SELECTED_NATIVE_ART_POSE' if name in selected_poses else 'REUSED_P09_NATIVE_C_DAILY_POSE')
        # PIL mode 1 packs MSB first, matching the 5000-byte framebuffer.
        if name in inherited:
            (PUBLIC/f'scene-{name}.png').write_bytes((BASE/'studio-p12'/f'scene-{name}.png').read_bytes())
            print('INHERIT P12 '+name,flush=True)
        else:
            buffer=(ctypes.c_uint8*5000).from_buffer_copy(frame.tobytes())
            state=Scene(kind,battery,1,1,progress,312,0)
            print('COMPOSE '+name,flush=True)
            if not library.comp_scene_design_render(buffer,ctypes.byref(state)):
                raise RuntimeError('Scene compositor rejected its authored context')
            result=Image.frombytes('1',(200,200),bytes(buffer))
            result.save(PUBLIC/f'scene-{name}.png')
        samples.append(dict(name=name,label=label,kind=kind,family=family,
            file=f'scene-{name}.png',batteryPercentExample=battery,
            nominalBatteryEstimate=True,progressExample=progress,
            nativePose=pose,compositionSource='P12_UNCHANGED_IMAGE' if name in inherited else 'P13_NATIVE_C',
            outputSha256=sha(PUBLIC/f'scene-{name}.png'),context='AUTHOR_SUPPLIED_NOT_DEVICE_STATE',
            text='DRAFT_LOCAL_PHRASE_NOT_AI_REPLY'))
    faulthandler.cancel_dump_traceback_later()
    sheet=Image.new('RGB',(1092,584),'#f4f2eb')
    draw=ImageDraw.Draw(sheet);font=ImageFont.truetype('C:/Windows/Fonts/msyh.ttc',12)
    draw.text((18,12),'Companion · 同一个小伙伴，不同的陪伴状态',font=font,fill='#293a33')
    draw.text((18,35),'P13 · 原生 200×200 黑白 · 倾听、思考、开心与界面细节 · 状态值及短句为设计示例',font=font,fill='#65736b')
    for i, case in enumerate(samples):
        x,y=18+(i%5)*216,68+(i//5)*249
        sheet.paste(Image.open(PUBLIC/case['file']).convert('RGB'),(x,y))
        draw.text((x,y+209),case['label'],font=font,fill='#293a33')
    sheet.save(PUBLIC/'scene-library.png')
    comparison=Image.new('RGB',(916,570),'#f4f2eb');cd=ImageDraw.Draw(comparison)
    cd.text((18,12),'神态与细节 · 每组左为 P12，右为 P13 · 原生大小',font=font,fill='#293a33')
    for i,name in enumerate(('listen','think','done','menu')):
        x,y=18+(i%2)*450,55+(i//2)*255
        label=next(s['label'] for s in samples if s['name']==name)
        cd.text((x,y),label,font=font,fill='#293a33')
        comparison.paste(Image.open(BASE/'studio-p12'/f'scene-{name}.png').convert('RGB'),(x,y+24))
        comparison.paste(Image.open(PUBLIC/f'scene-{name}.png').convert('RGB'),(x+216,y+24))
    comparison.save(PUBLIC/'composition-comparison.png')
    receipt=dict(schema='companion.screen.scene-art.v1',design='P13',parentDesign='P12',
        createdAtLocal=datetime.now().isoformat(),result='NATIVE_SCENE_ART_EXPORTED',
        sceneDllSha256=sha(dll_path),reusedFaceDllSha256=parent['dllSha256'],
        sourceSha256={p.relative_to(ROOT).as_posix():sha(p) for p in
            [Path(__file__),ART/'scene_compositor.c',ART/'scene_compositor.h',ART/'scene_glyphs.h']},
        fontSha256=sha(FONT_PATH),glyphWidths=widths,frameBytes=5000,
        replySlot=[12,164,176,36],nativePixelSize=[200,200],samples=samples,
        glyphRaster=dict(fontSize=12,height=GLYPH_HEIGHT,commonAscenderOffset=GLYPH_ASCENDER_OFFSET,
            anchor='la',letterSpacing=1,replyRowOrigins=[165,181],antialias=False),
        composition=dict(faceTranslation=[0,-6],ornamentDockCenter=[151,50],
            faceScale=1,originalContoursPreserved=True,clockTranslation=[3,3],
            rightRailTranslation=[-7,3],menuSeparatorsRemoved=True,
            progressTrack=[36,187,128,6],progressFill=[38,189,124,2],
            menuSelectionOutline=[14,57,172,29],extraFrameBuffer=False),
        comparisonParents={name:sha(BASE/'studio-p12'/f'scene-{name}.png') for name in ('listen','think','done','menu')},
        inheritedScenes={name:sha(BASE/'studio-p12'/f'scene-{name}.png') for name in sorted(inherited)},
        selectedExpressionExamples=selected_poses,sceneEmotionRouting='DESIGN_EXAMPLES_NOT_INTEGRATED',
        faceAndOriginalOrnamentsChanged=False,liveMotionChanged=False,
        timingChanged=False,extraAnimationFrames=False,boardAccess=False,
        productionSourcesChanged=False,armBuilt=False,installed=False,testsRun=False,
        physicalGhosting='NOT_MODELED',actualMaximumRefresh='NOT_QUALIFIED',
        chargingState='AUTHOR_SUPPLIED_NOT_DETECTED',conversation='DRAFT_PHRASES_ONLY')
    (PUBLIC/'scene-design.json').write_text(json.dumps(receipt,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    print(json.dumps(dict(result=receipt['result'],design='P13',samples=len(samples),
        dllSha256=receipt['sceneDllSha256'],sheet=str(PUBLIC/'scene-library.png')),ensure_ascii=False))

if __name__=='__main__':main()
