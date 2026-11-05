from pathlib import Path
import hashlib, json, struct

ROOT=Path(__file__).resolve().parents[2]
PAGE=ROOT/'docs/validation/companion-menu-luna-machine-ready/index.html'
SRC=ROOT/'docs/art/iterations/companion-menu-v7-screen-family/generated_menu_screen_family_v7_3_candidate.png'
RES=ROOT/'docs/validation/companion-menu-luna-machine-ready/resource-manifest.json'
FIX=ROOT/'docs/validation/companion-menu-luna-machine-ready/negative-fixtures'
REQ=["tapMaxMove:32","tapMaxDuration:2000","swipeMinMove:40","swipeMaxDuration:1200","axisLockMinMove:14","axisSlop:24","dominance:140","hold:650","longPress:3000","longPressMaxMove:44","finger_delta_y","Menu closed","preloadAssets","naturalWidth!==200","menu-ready"]
def sha(p): return hashlib.sha256(p.read_bytes()).hexdigest().upper()
def png_info(path):
    data=path.read_bytes()
    if data[:8]!=b'\x89PNG\r\n\x1a\n': raise SystemExit(f'NO_GO not PNG: {path}')
    width,height=struct.unpack('>II',data[16:24])
    return width,height
def main():
    if not PAGE.exists(): raise SystemExit('NO_GO missing generated page')
    text=PAGE.read_text(encoding='utf-8')
    missing=[x for x in REQ if x not in text]
    if missing: raise SystemExit('NO_GO authority missing: '+','.join(missing))
    if not all(x in text for x in ['Voice','Device','Connection','Preferences','root_opened','select(','back=exit_daily']): raise SystemExit('NO_GO menu contract missing')
    if 'expression' in text.lower() or 'double' in text.lower(): raise SystemExit('NO_GO expression/double activation surface')
    resources=json.loads(RES.read_text(encoding='utf-8'))
    if resources['canvas'] != [200,200] or len(resources['assets']) != 10: raise SystemExit('NO_GO incomplete resource manifest')
    resource_report=[]
    for rel in resources['assets']:
        path=ROOT/'docs/art/iterations/companion-menu-v7-screen-family/review-200x200'/rel
        if not path.exists(): raise SystemExit(f'NO_GO missing resource {rel}')
        dims=png_info(path)
        if list(dims)!=resources['canvas']: raise SystemExit(f'NO_GO bad resource dimensions {rel}: {dims}')
        resource_report.append({'path':str(path),'sha256':sha(path),'dimensions':list(dims)})
    fixture_expectations={
        'disappearing-content': ['preloadAssets','menu-ready','assetPath'],
        'accidental-double-activation': ['pointerup','consumed','select('],
        'out-of-bounds-swipe': ['Math.max(0','Math.min(maxScroll()','finger_delta_y'],
        'expression-menu-stacking': ['alt=""','aria-hidden="true"','data-testid="menu-browser"']
    }
    fixtures=[]
    for name,tokens in fixture_expectations.items():
        fixture=FIX/f'{name}.json'
        record=json.loads(fixture.read_text(encoding='utf-8'))
        if record.get('fixture')!=name or record.get('expected','').strip()=='' or any(token not in text for token in tokens):
            raise SystemExit(f'NO_GO fixture not asserted: {name}')
        fixtures.append({'path':str(fixture),'sha256':sha(fixture),'asserted_tokens':tokens})
    report={"status":"PASS","page_sha256":sha(PAGE),"visual_source_sha256":sha(SRC),"source_path":str(SRC),"resource_count":len(resource_report),"resources":resource_report,"bounded_trace":32,"bounds":[200,200],"threshold_authority":"app/companion_pendant/touch/touch_gesture.c defaults + app/companion_pendant/epaper/menu_v5_navigation.c/.h","negative_fixtures":fixtures}
    print(json.dumps(report,indent=2))
if __name__=='__main__': main()
