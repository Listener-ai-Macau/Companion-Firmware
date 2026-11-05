#!/usr/bin/env python3
"""Render the real WBA compositor with retained, source-labelled character art.

This reviews status/hold/blink composition, NOT the missing complete gen21 pack.
No hand-redrawn face, browser imitation of the rail, or hardware PASS.
"""
from pathlib import Path
import hashlib
import html
import json
import subprocess
from PIL import Image, ImageDraw, ImageFont
from build_wba_prehardware import run
from test_wba_runtime import ROOT, APP, INCLUDES
from verify_wba_spi_nor_adapter import find_vsdevcmd

ART = ROOT / 'docs/art/iterations/companion-pet-expression-v9-two-track-rig-v7/candidate/wb55-browser-parity-attempt-01'
OUT = ROOT / '.cache/wba-visual-review'
FIXTURES = {
    'calm': 'calm_presence-00-calm_entry',
    'curious': 'curious_question-03-question_hold',
    'delighted': 'delighted_presence-03-delighted_hold',
    'warm': 'warm_presence-03-warm_hold',
    'playful': 'playful_presence-03-playful_hold',
    'sleepy': 'sleepy_presence-00-sleep_entry',
    'bashful': 'bashful_presence-03-bashful_hold',
    'thoughtful': 'thoughtful_presence-03-thoughtful_hold',
    'focused': 'focused_presence-03-focused_hold',
    'alert': 'alert_exclamation-03-exclamation_hold',
    'blink_open': 'calm_presence-00-calm_entry',
    'blink_closed': 'calm_presence-02-calm_blink_closed',
}
CUES = [('idle', '安静陪伴'), ('preparing', '准备录音'), ('recording', '正在录音'), ('saving', '正在保存'),
        ('saved', '已经保存'), ('sync', '正在同步'), ('error', '保存失败'), ('unavailable', '暂不可用')]
FAMILIES = ['平静', '好奇', '开心', '亲近', '顽皮', '困倦', '害羞', '思考', '专注', '警觉']

def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()

def main():
    for d in ('input', 'native', 'images'): (OUT/d).mkdir(parents=True, exist_ok=True)
    report = {'result': 'FAIL', 'hardwareAcceptance': 'NOT_RUN', 'generation21PixelAcceptance': 'NOT_RUN',
              'scope': 'production status rail, emotion-preserving hold and blink composition; retained V45 face fixtures',
              'source_sha256': {}, 'art_sources': {}, 'frames': {}}
    log = OUT/'build.log'; log.write_text('')
    try:
        for name, stem in FIXTURES.items():
            path = ART/(stem+'.png'); im = Image.open(path).convert('L')
            if im.size != (200,200) or not set(im.getdata()).issubset({0,255}):
                raise ValueError(f'non-native or non-binary art: {path}')
            # Format conversion only: keep every existing source pixel.
            (OUT/'input'/(name+'.bin')).write_bytes(im.convert('1',dither=Image.Dither.NONE).tobytes())
            report['art_sources'][name] = {'path': path.relative_to(ROOT).as_posix(), 'sha256': digest(path)}
        sources = [APP/p for p in ('runtime/tests/render_visual_review.c','epaper/screen_menu.c',
            'epaper/screen_framebuffer.c','epaper/motion_coordinator.c','touch/browser_interaction_runtime.c')]
        exe=OUT/'render.exe'
        args=['cl.exe','/nologo','/std:c11','/W4','/WX','/utf-8', '/DCOMPANION_SCREEN_COMP_REQ_638_SOURCE_PACK=1',
              *(f'/I{p}' for p in INCLUDES),*(str(p) for p in sources),f'/Fe:{exe}']
        cmd=OUT/'build.cmd'
        cmd.write_text(f'@echo off\ncall "{find_vsdevcmd()}" -arch=amd64 -host_arch=amd64 >nul\n'
                       'if errorlevel 1 exit /b %errorlevel%\n'+subprocess.list2cmdline(args)+'\n')
        run(['cmd.exe','/d','/c',str(cmd)],OUT,log)
        text=run([str(exe),str(OUT/'input'),str(OUT/'native')],OUT,log);print(text,end='')
        if 'PASS_NATIVE_VISUAL_FIXTURES' not in text: raise RuntimeError('native fixture completion absent')
        expected=[*(f'family-{n}' for n in list(FIXTURES)[:10]),*(f'family-{n}-blink' for n in list(FIXTURES)[:10]),*(f'cue-{n}' for n,_ in CUES),
                  *(f'hold-{i}' for i in range(4)),'blink-closed','blink-clock-update','blink-open']
        for name in expected:
            path=OUT/'native'/(name+'.bin'); raw=path.read_bytes()
            if len(raw)!=5000: raise ValueError('truncated native frame')
            im=Image.frombytes('1',(200,200),raw); im.save(OUT/'images'/(name+'.png'))
            report['frames'][name]={'bytes':len(raw),'sha256':digest(path)}
        base=(OUT/'native/family-curious.bin').read_bytes()
        for i in range(4):
            if (OUT/'native'/f'hold-{i}.bin').read_bytes()[400:]!=base[400:]:
                raise ValueError('hold altered the original expression')
        if (OUT/'native/blink-closed.bin').read_bytes()[400:]!=(OUT/'native/blink-clock-update.bin').read_bytes()[400:]:
            raise ValueError('status interrupted closed eyelids')
        font=ImageFont.truetype('C:/Windows/Fonts/msyh.ttc',18)
        titlefont=ImageFont.truetype('C:/Windows/Fonts/msyh.ttc',24)
        sheet=Image.new('RGB',(924,624),'#f4f1ea'); draw=ImageDraw.Draw(sheet)
        draw.text((24,18),'Companion · 安静、有回应',font=titlefont,fill='#202721')
        draw.text((24,56),'统一状态图标  /  长按保留当前表情  /  眨眼独立完成',font=font,fill='#506054')
        for i,(name,label) in enumerate(CUES):
            x=24+(i%4)*226;y=100+(i//4)*248
            sheet.paste(Image.open(OUT/'images'/f'cue-{name}.png').convert('RGB'),(x,y))
            draw.text((x,y+207),label,font=font,fill='#202721')
        draw.text((24,597),'软件合成预览 · 沿用原有 V45 素材 · 未作为实屏或 generation 21 验收',font=ImageFont.truetype('C:/Windows/Fonts/msyh.ttc',14),fill='#506054')
        sheet.save(OUT/'review.png')
        eyes=Image.new('RGB',(1140,960),'#f4f1ea'); ed=ImageDraw.Draw(eyes)
        ed.text((20,12),'眨眼精修 · 眼睑跟随当前眼睛的形状与位置',font=titlefont,fill='#202721')
        for i,(name,label) in enumerate(zip(list(FIXTURES)[:10],FAMILIES)):
            x=20+(i%5)*224;y=60+(i//5)*446
            for offset,suffix in ((0,''),(202,'-blink')):
                eyes.paste(Image.open(OUT/'images'/f'family-{name}{suffix}.png').convert('RGB'),(x,y+offset))
            ed.text((x,y+407),label+' · 睁眼 / 闭眼',font=font,fill='#202721')
        eyes.save(OUT/'blink-review.png')
        frames=[Image.open(OUT/'images'/f'hold-{i}.png') for i in range(4)]
        frames[0].save(OUT/'hold.gif',save_all=True,append_images=frames[1:],duration=600,loop=0)
        buttons=''.join(f'<button type="button" data-frame="cue-{n}">{html.escape(label)}</button>' for n,label in CUES)
        families=''.join(
            f'<figure><button type="button" class="family-choice" data-family="{n}" '
            f'data-family-label="{html.escape(label)}" aria-pressed="false">'
            f'<img src="images/family-{n}.png" width="200" height="200" '
            f'alt="{html.escape(label)}表情，原生 200×200 黑白像素帧"></button>'
            f'<figcaption>{html.escape(label)}</figcaption></figure>'
            for n,label in zip(list(FIXTURES)[:10],FAMILIES))
        page='''<!doctype html><html lang="zh-CN"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>Companion · 表情与状态预览</title><style>
*{box-sizing:border-box}html{--preview-pixels:400px}body{margin:0;background:#f4f1ea;color:#202721;font:16px/1.6 system-ui,'Microsoft YaHei',sans-serif;overflow-x:hidden}
main{max-width:1200px;margin:48px auto;padding:0 24px}h1{font-size:36px;letter-spacing:-1px;margin:8px 0}h2{font-size:22px;margin-top:40px}.tag{color:#54735f;font-weight:650}
.hero{display:grid;grid-template-columns:minmax(0,1fr) 404px;gap:48px;align-items:center}.screen-panel{min-width:0}.screen-viewport{width:100%;max-width:404px;overflow-x:auto;overscroll-behavior-inline:contain}.screen-frame{width:calc(var(--preview-pixels) + 4px);height:calc(var(--preview-pixels) + 4px);border:2px solid #9fa89f;background:#fff;overflow:hidden}.screen-frame img{display:block;width:var(--preview-pixels);height:var(--preview-pixels);max-width:none;image-rendering:pixelated}
.scale-controls{display:flex;align-items:center;gap:8px;flex-wrap:wrap;margin:0 0 12px}.scale-controls span{font-size:13px;color:#5e6c60}.scale-controls button{min-width:48px}
.art-link{display:inline-flex;align-items:center;margin:12px 0 28px;padding:10px 16px;border:2px solid #294f3a;color:#294f3a;font-weight:700;text-decoration:none}.art-link:focus-visible{outline:3px solid #719c83;outline-offset:3px}
button{font:inherit;border:1px solid #bcc8bc;background:transparent;color:inherit;border-radius:20px;padding:7px 14px;margin:4px;cursor:pointer}button[aria-pressed=true]{color:white;background:#294f3a;border-color:#294f3a}button:focus-visible{outline:3px solid #719c83;outline-offset:2px}.note{font-size:14px;color:#5e6c60}.legend{min-height:28px;color:#365b42}
.families{display:grid;grid-template-columns:repeat(auto-fit,202px);justify-content:center;gap:20px 16px}figure{margin:0;text-align:center;width:202px}.family-choice{display:block;width:202px;height:202px;margin:0;padding:0;border:1px solid #9fa89f;border-radius:0;background:#fff;overflow:hidden}.family-choice[aria-pressed=true]{outline:3px solid #294f3a;outline-offset:2px;background:#fff}.family-choice img{display:block;width:200px;height:200px;max-width:none;border:0;border-radius:0;image-rendering:pixelated}figcaption{margin-top:6px}
#art-candidate-gallery[hidden]{display:none}footer{margin:40px 0;padding-top:20px;border-top:1px solid #ccd3c7;font-size:13px;color:#5e6c60}
@media(max-width:760px){main{margin:24px auto;padding:0 20px}h1{font-size:30px}.hero{grid-template-columns:minmax(0,1fr);gap:24px}.screen-viewport{max-width:100%}.families{grid-template-columns:202px;justify-content:center}}
@media(prefers-reduced-motion:reduce){*{scroll-behavior:auto}}
</style><main><div class="tag">Companion / 第一版宠物交互</div><h1>安静陪着你，操作有回应。</h1><a class="art-link" href="./art/index.html">看本轮美术精修 / 前后对照</a><div class="hero"><section><p>保留原来的小家伙。把信息收在顶部，让表情自然地完成动作。</p><div id="cues">BUTTONS</div><p class="legend" id="label" aria-live="polite">安静陪伴</p><p>长按时，四格依次填满；当前表情保持原样。录音提示和保存结果仍能同时看见。</p><button type="button" id="hold">看长按过程（好奇）</button><button type="button" id="blink">看所选表情眨眼</button><p class="note">扬声器仍采用短促宠物叫声，无语言播报。录音时保持安静。</p></section><section class="screen-panel" aria-label="原生像素帧预览"><div class="scale-controls" aria-label="预览倍率"><strong>原生 200×200 黑白像素帧</strong><button type="button" data-scale="1" aria-pressed="false">1×</button><button type="button" data-scale="2" aria-pressed="false">2×</button><span>仅为整数像素预览，不代表屏幕物理尺寸</span></div><div class="screen-viewport" id="screenViewport"><div class="screen-frame"><img id="screen" src="images/cue-idle.png" width="200" height="200" alt="Companion 当前表情与状态栏，原生 200×200 黑白像素帧"></div></div></section></div>
<h2>原有的十种表情</h2><p class="note">缩略图保持原生 200×200；点击任一表情可在主预览中查看，再播放该表情自己的眨眼。这里没有替换已经通过的角色资源。</p><div class="families">FAMILIES</div><section id="art-candidate-gallery" data-gallery-mount="art-candidates" hidden aria-label="独立艺术候选"></section><footer>这是生产 C 渲染器输出的像素预览，采用保留的 V45 角色素材。页面只按 1× 或 2× 整数倍率显示原生 200×200 黑白帧，不表示面板物理尺寸。录音样例展示状态栏，不模拟缺失的 generation 21 音波资源。屏幕观感、残影和完整资源包尚待实板验证。</footer></main><script>
let timers=[];let selectedFamily='curious',selectedFamilyLabel='好奇';const screen=document.querySelector('#screen'),label=document.querySelector('#label'),narrow=matchMedia('(max-width:760px)');
function setScale(value){document.documentElement.style.setProperty('--preview-pixels',value===2?'400px':'200px');document.documentElement.dataset.scale=String(value);document.querySelectorAll('[data-scale]').forEach(b=>b.setAttribute('aria-pressed',String(Number(b.dataset.scale)===value)))}
setScale(narrow.matches?1:2);document.querySelectorAll('[data-scale]').forEach(b=>b.onclick=()=>setScale(Number(b.dataset.scale)));
function cancel(){timers.forEach(clearTimeout);timers=[];document.querySelectorAll('button[data-frame]').forEach(b=>b.setAttribute('aria-pressed','false'))}
function show(name,text){screen.src='images/'+name+'.png';label.textContent=text}
function selectFamily(name,text,display=true){selectedFamily=name;selectedFamilyLabel=text;document.querySelectorAll('[data-family]').forEach(b=>b.setAttribute('aria-pressed',String(b.dataset.family===name)));if(display){cancel();show('family-'+name,text+' · 睁眼')}}
document.querySelectorAll('button[data-frame]').forEach(b=>b.onclick=()=>{cancel();b.setAttribute('aria-pressed','true');show(b.dataset.frame,b.textContent)});
document.querySelectorAll('[data-family]').forEach(b=>b.onclick=()=>selectFamily(b.dataset.family,b.dataset.familyLabel));
function sequence(rows){cancel();rows.forEach(([name,text,at])=>timers.push(setTimeout(()=>show(name,text),at)))}
document.querySelector('#hold').onclick=()=>{selectFamily('curious','好奇',false);sequence([['hold-0','好奇 · 长按 1 / 4',0],['hold-1','好奇 · 长按 2 / 4',600],['hold-2','好奇 · 长按 3 / 4',1200],['hold-3','好奇 · 长按 4 / 4',1800]])};
document.querySelector('#blink').onclick=()=>{const open='family-'+selectedFamily,closed=open+'-blink',clock=selectedFamily==='curious'?'blink-clock-update':closed;sequence([[open,selectedFamilyLabel+' · 睁眼',0],[closed,selectedFamilyLabel+' · 闭眼',1000],[clock,selectedFamilyLabel+' · 时钟更新期间保持闭眼',1500],[open,selectedFamilyLabel+' · 恢复',2300]])};
document.querySelector('[data-frame="cue-idle"]').setAttribute('aria-pressed','true');selectFamily('curious','好奇',false);
</script></html>'''.replace('BUTTONS',buttons).replace('FAMILIES',families)
        (OUT/'index.html').write_text(page,encoding='utf-8')
        identities=[*sources,APP/'runtime/companion_renderer.c',Path(__file__),
                    *(ART/(stem+'.png') for stem in set(FIXTURES.values())),
                    *(p for d in INCLUDES for p in d.glob('*.h'))]
        report.update(result='PASS_PREHARDWARE_VISUAL_COMPOSITION',source_sha256={p.relative_to(ROOT).as_posix():digest(p) for p in identities},
                      invariants={'native_frames':len(expected),'hold_keeps_face_pixels':True,'clock_keeps_eyelids':True,
                                  'fixture_pixels_unmodified':True,'no_generation21_substitution':True})
    except (OSError,ValueError,RuntimeError) as e:
        report['error']=str(e);print(e)
    (OUT/'result.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    return int(report['result']=='FAIL')

if __name__=='__main__':raise SystemExit(main())
