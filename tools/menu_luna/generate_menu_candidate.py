from pathlib import Path
import hashlib, json, shutil

ROOT = Path(__file__).resolve().parents[2]
TEMPLATE = ROOT / "tools/menu_luna/menu_candidate_template.html"
OUT = ROOT / "docs/validation/companion-menu-luna-machine-ready/index.html"

def main():
    OUT.parent.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(TEMPLATE, OUT)
    print(json.dumps({"output": str(OUT), "sha256": hashlib.sha256(OUT.read_bytes()).hexdigest().upper()}, indent=2))

if __name__ == "__main__":
    main()
