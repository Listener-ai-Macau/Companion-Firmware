from pathlib import Path
import hashlib, json, struct

ROOT=Path(__file__).resolve().parents[2]
PAGE=ROOT/'docs/validation/companion-menu-luna-r2-machine-ready/index.html'
MANIFEST=ROOT/'docs/validation/companion-menu-luna-r2-machine-ready/machine-manifest.json'
MENU=ROOT/'docs/art/iterations/companion-menu-v7-screen-family/review-200x200'
EXP=ROOT/'docs/art/iterations/companion-pet-expression-v9-two-track-rig-v7/r7-locked-v9-export-20260723/all-candidates'
ASSETS=['en/01-home.png','en/02-voice.png','en/03-device.png','en/04-connection.png','en/05-preferences.png','zh_cn/01-home.png','zh_cn/02-voice.png','zh_cn/03-device.png','zh_cn/04-connection.png','zh_cn/05-preferences.png']
EXPRESSIONS=['calm_presence/04-calm_blink_settle.png','curious_question/03-question_hold.png','warm_presence/03-warm_hold.png']
def sha(path): return hashlib.sha256(path.read_bytes()).hexdigest().upper()
def dims(path):
    data=path.read_bytes()
    if data[:8]!=b'\x89PNG\r\n\x1a\n': raise SystemExit('NO_GO not PNG: '+str(path))
    return struct.unpack('>II',data[16:24])
def main():
    text=PAGE.read_text(encoding='utf-8'); json.loads(MANIFEST.read_text(encoding='utf-8'))
    required=['ROOTS=[\'Voice\',\'Device\',\'Connection\',\'Preferences\']','Device > UI assets','oneScreenAtATime:true','pointerdown','pointermove','pointerup','swipeMovePx:40','screen.dataset.screen=state.view','naturalWidth!==200']
    missing=[token for token in required if token not in text]
    if missing: raise SystemExit('NO_GO missing contract tokens: '+','.join(missing))
    forbidden=['debug','telemetry','arousal','valence','memory']
    if any(token in text.lower() for token in forbidden): raise SystemExit('NO_GO owner debug surface')
    records=[]
    for rel in ASSETS:
        p=MENU/rel
        if not p.exists() or dims(p)!=(200,200): raise SystemExit('NO_GO menu asset '+rel)
        records.append({'path':str(p),'sha256':sha(p),'dimensions':[200,200]})
    expressions=[]
    for rel in EXPRESSIONS:
        p=EXP/rel
        if not p.exists() or dims(p)!=(200,200): raise SystemExit('NO_GO expression asset '+rel)
        expressions.append({'path':str(p),'sha256':sha(p),'dimensions':[200,200]})
    report={'status':'PASS','page_sha256':sha(PAGE),'manifest_sha256':sha(MANIFEST),'menu_assets':records,'expression_assets':expressions,'one_screen_invariant':True,'owner_debug_controls':False,'browser_only':True}
    print(json.dumps(report,indent=2))
if __name__=='__main__': main()
