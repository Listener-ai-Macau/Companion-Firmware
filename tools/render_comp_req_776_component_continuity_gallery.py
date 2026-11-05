"""Render the reported bashful motion sequence before and after the fix."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

import verify_comp_req_776_expression_completeness as audit


ROOT = Path(__file__).resolve().parents[1]
OLD = ROOT / (
    ".cache/validation/comp775-r33-expression-coverage-audit/"
    "source-pack/source-pack-manifest.json"
)
NEW = ROOT / (
    ".cache/validation/comp776-component-clip-fix-20260812/"
    "source-pack-5059/source-pack-manifest.json"
)
OUTPUT = ROOT / (
    ".cache/validation/comp776-component-clip-fix-20260812/"
    "bashful-motion-before-after.png"
)
PHASES = ("hold", "anticipate", "accent", "follow")


def load(path: Path) -> tuple[dict[str, dict], Path]:
    manifest = json.loads(path.read_text(encoding="utf-8"))
    return {row["id"]: row for row in manifest["states"]}, path.parent


def image(path: Path) -> Image.Image:
    _, frame = audit.read_p4(path)
    result = Image.new("1", (200, 200), 1)
    pixels = result.load()
    for y in range(200):
        for x in range(200):
            pixels[x, y] = 0 if audit.is_black(frame, x, y) else 1
    return result.convert("RGB")


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest().upper()


def main() -> int:
    old, old_dir = load(OLD)
    new, new_dir = load(NEW)
    sheet = Image.new("RGB", (4 * 420, 2 * 470 + 70), "#ececec")
    draw = ImageDraw.Draw(sheet)
    font = ImageFont.load_default()
    draw.text((18, 14), "COMP-REQ-776 bashful motion continuity: reported defect vs generation 20", fill="black", font=font)
    draw.text((18, 34), "Top = old padded erase (eye rows clipped); bottom = exact component erase (eyes and cheeks complete).", fill="#333", font=font)
    receipt = []
    for row_index, (label, states, source_dir) in enumerate((
        ("OLD / FAILED", old, old_dir),
        ("GEN 20 / FIXED", new, new_dir),
    )):
        for column, phase in enumerate(PHASES):
            state_id = f"expression_bashful_v0_0_{phase}"
            state = states[state_id]
            frame = image(source_dir / state["pbm_file"])
            x = column * 420 + 10
            y = row_index * 470 + 68
            scaled = frame.resize((400, 400), Image.Resampling.NEAREST)
            sheet.paste(scaled, (x, y + 42))
            draw.rectangle((x + 60, y + 42 + 205, x + 350, y + 42 + 315), outline="#d00000", width=3)
            draw.text((x, y), f"{label} — {phase}", fill="black", font=font)
            draw.text((x, y + 17), state_id, fill="#333", font=font)
            receipt.append({"row": label, "phase": phase, "state_id": state_id, "pbm_sha256": state["pbm_sha256"]})
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    sheet.save(OUTPUT)
    report = {
        "schema": "companion.comp_req_776.component_continuity_gallery.v1",
        "status": "MACHINE_READY",
        "phases": list(PHASES),
        "panels": receipt,
        "png": str(OUTPUT.relative_to(ROOT)).replace("\\", "/"),
        "png_sha256": sha256(OUTPUT),
    }
    OUTPUT.with_suffix(".json").write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(report, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
