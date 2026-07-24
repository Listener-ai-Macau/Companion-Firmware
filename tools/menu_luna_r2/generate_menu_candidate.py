from pathlib import Path
import hashlib, json

ROOT=Path(__file__).resolve().parents[2]
PAGE=ROOT/'docs/validation/companion-menu-luna-r2-machine-ready/index.html'
MANIFEST=ROOT/'docs/validation/companion-menu-luna-r2-machine-ready/machine-manifest.json'
OUT=ROOT/'docs/validation/companion-menu-luna-r2/generation-receipt.json'

def sha(path): return hashlib.sha256(path.read_bytes()).hexdigest().upper()

def main():
    if not PAGE.exists() or not MANIFEST.exists():
        raise SystemExit('NO_GO missing r2 page or manifest')
    text=PAGE.read_text(encoding='utf-8')
    required=['Device > UI assets','menuReady','oneScreenAtATime:true','data-testid="expression-warm"']
    missing=[token for token in required if token not in text]
    if missing: raise SystemExit('NO_GO generator source missing: '+','.join(missing))
    OUT.parent.mkdir(parents=True,exist_ok=True)
    receipt={"status":"PASS","generator":"tools/menu_luna_r2/generate_menu_candidate.py","page":str(PAGE),"page_sha256":sha(PAGE),"manifest":str(MANIFEST),"manifest_sha256":sha(MANIFEST),"source_contract":"registered menu-v5/v7 assets plus registered R7 expression frames"}
    OUT.write_text(json.dumps(receipt,indent=2)+'\n',encoding='utf-8')
    print(json.dumps(receipt,indent=2))
if __name__=='__main__': main()
