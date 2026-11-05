#!/usr/bin/env python3
"""Archive the reviewed screen candidate without activating product resources."""
from pathlib import Path
import hashlib
import json
import zipfile
from PIL import Image

ROOT=Path(__file__).resolve().parents[1]
ART=ROOT/'docs/art/iterations/companion-wba-screen-art-v3'
PREVIEW=ROOT/'.cache/wba-visual-review/art/screen-v3'
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()

def main():
    report=json.loads((ART/'result.json').read_text(encoding='utf-8'))
    if report['result']!='PASS_SCREEN_ART_SOFTWARE_PIXELS_ONLY':raise ValueError('Candidate check failed')
    for name,expected in report['source_sha256'].items():
        if sha(ROOT/name)!=expected:raise ValueError(f'Stale candidate source: {name}')
    if sha(ART/'candidate.cemp')!=report['pack_sha256']:raise ValueError('Candidate pack changed')
    files={name:ART/name for name in ('candidate.cemp','cemp-manifest.json','layout.json','result.json')}
    files.update({f'source/{name}':ROOT/name for name in report['source_sha256']})
    for name in ('index.html','frames.json','result.json','candidate.cemp'):
        files[f'preview/{name}']=PREVIEW/name
    frames=json.loads((PREVIEW/'frames.json').read_text(encoding='utf-8'))
    if len(frames)!=report['frames']:raise ValueError('Frame inventory differs from candidate receipt')
    for name,meta in frames.items():
        asset=meta.get('asset',name)
        native=PREVIEW/'native'/f'{asset}.bin'
        png=PREVIEW/'images'/f'{asset}.png'
        if native.stat().st_size!=5000 or sha(native)!=meta['sha256']:
            raise ValueError(f'Native frame identity differs: {name}')
        with Image.open(png) as im:
            if im.size!=(200,200) or im.mode!='1' or im.tobytes()!=native.read_bytes():
                raise ValueError(f'PNG differs from native frame: {name}')
        for p in (native,png):files[f'preview/{p.relative_to(PREVIEW).as_posix()}']=p
    for family in sorted({meta['family'] for meta in frames.values()}):
        native=PREVIEW/'native'/f'original-{family}.bin'
        png=PREVIEW/'old'/f'{family}.png'
        with Image.open(png) as im:
            if im.size!=(200,200) or im.mode!='1' or im.tobytes()!=native.read_bytes():
                raise ValueError(f'Original comparison differs: {family}')
        for p in (native,png):files[f'preview/{p.relative_to(PREVIEW).as_posix()}']=p
    # The independent browser receipt is included if available and must match
    # the page being shipped. Hardware/owner acceptance is never inferred.
    browser=PREVIEW/'screen-browser-result.json'
    if not browser.exists():raise ValueError('Independent browser check is missing')
    browser_report=json.loads(browser.read_text(encoding='utf-8'))
    if not browser_report.get('result','').startswith('PASS_'):raise ValueError('Browser check failed')
    if browser_report.get('preview_html_sha256')!=sha(PREVIEW/'index.html'):raise ValueError('Browser page evidence is stale')
    for name,expected in browser_report.get('sourceSha256',{}).items():
        if sha(ROOT/name)!=expected:raise ValueError(f'Browser check source is stale: {name}')
    if browser_report.get('logicalFrames')!=len(frames):raise ValueError('Browser frame inventory differs')
    files['preview/screen-browser-result.json']=browser
    for p in PREVIEW.glob('screen-*.png'):files[f'preview/{p.name}']=p
    files['source/tools/check_wba_screen_art.mjs']=ROOT/'tools/check_wba_screen_art.mjs'
    files['source/tools/package_wba_screen_art.py']=Path(__file__)
    name='screen-art-v3-'+report['pack_sha256'][:12]
    archive=ROOT/'.cache/wba-visual-review'/f'{name}.zip'
    manifest={'role':'SCREEN_ART_CANDIDATE_NOT_ACTIVE','hardwareAcceptance':'NOT_RUN',
        'productionAssetActivation':'NOT_ACTIVE','pixelFormat':'200x200 1bpp white-is-one MSB; 5000 bytes',
        'files':{name:sha(p) for name,p in files.items()}}
    with zipfile.ZipFile(archive,'w',zipfile.ZIP_DEFLATED) as z:
        for name,p in files.items():z.write(p,name)
        z.writestr('manifest.json',json.dumps(manifest,ensure_ascii=False,indent=2)+'\n')
        z.writestr('README.txt','Companion 屏幕美术候选 v3\n\n打开 preview/index.html 查看完整屏幕帧。PNG 与 native/*.bin 像素一致。\n候选 CEMP 已通过实际 C 解码器逐字节核对。五官来自原生注册部件。\n这不是完整 generation 21 资源库，也未激活到设备；不得直接作为正式资源升级包。\n软件核对与浏览器报告随包，硬件显示/刷新/方向仍待新板确认。\n源码修改需在 Companion-Firmware 仓库内用 tools/build_wba_screen_art.py 重建。\n')
    receipt={'status':'SCREEN_ART_CANDIDATE_READY','archive':str(archive),'archive_sha256':sha(archive),
        'preview':'http://127.0.0.1:8876/art/','pack_sha256':report['pack_sha256'],
        'frames':report['frames'],'hardwareAcceptance':'NOT_RUN','productionAssetActivation':'NOT_ACTIVE'}
    (ROOT/'.cache/wba-visual-review/art-review-current.json').write_text(json.dumps(receipt,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    print(json.dumps(receipt,ensure_ascii=False))
if __name__=='__main__':main()
