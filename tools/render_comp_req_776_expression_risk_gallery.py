"""Render the four-edge risks and ten family representatives for Owner review."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

import verify_comp_req_776_expression_completeness as audit


ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / (
    ".cache/validation/comp776-component-clip-fix-20260812/"
    "source-pack-5059/source-pack-manifest.json"
)
DEFAULT_OUTPUT = ROOT / (
    ".cache/validation/comp776-component-clip-fix-20260812/"
    "expression-risk-and-ten-families.png"
)
FAMILIES = [
    "calm",
    "curious",
    "delighted",
    "warm",
    "playful",
    "sleepy",
    "bashful",
    "thoughtful",
    "focused",
    "alert",
]


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest().upper()


def image_from_p4(frame: bytes) -> Image.Image:
    result = Image.new("1", (audit.WIDTH, audit.HEIGHT), 1)
    pixels = result.load()
    for y in range(audit.HEIGHT):
        for x in range(audit.WIDTH):
            pixels[x, y] = 0 if audit.is_black(frame, x, y) else 1
    return result.convert("RGB")


def select_risks(rows: list[dict[str, object]], source_dir: Path) -> dict[str, dict[str, object]]:
    candidates: list[tuple[dict[str, object], dict[str, int | None]]] = []
    for row in rows:
        _, frame = audit.read_p4(source_dir / str(row["pbm_file"]))
        _, _, margins = audit.black_geometry(frame)
        candidates.append((row, margins))
    dimensions = {
        "TOP body below status": "top_below_status",
        "LEFT body": "left",
        "RIGHT body": "right",
        "BOTTOM body": "bottom",
    }
    selected: dict[str, dict[str, object]] = {}
    used: set[str] = set()
    for label, dimension in dimensions.items():
        ordered = sorted(
            candidates,
            key=lambda item: (
                item[1][dimension] if item[1][dimension] is not None else 10_000,
                str(item[0]["id"]),
            ),
        )
        choice = next((item for item in ordered if str(item[0]["id"]) not in used), ordered[0])
        used.add(str(choice[0]["id"]))
        selected[label] = {**choice[0], "body_margins": choice[1]}
    return selected


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--source", type=Path, default=SOURCE)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    args = parser.parse_args()

    manifest = json.loads(args.source.read_text(encoding="utf-8"))
    rows = manifest["states"]
    by_id = {row["id"]: row for row in rows}
    risk = select_risks(rows, args.source.parent)
    panels: list[tuple[str, dict[str, object]]] = list(risk.items())
    for family in FAMILIES:
        state_id = f"expression_{family}_v0_0_hold"
        panels.append((f"FAMILY {family}", by_id[state_id]))

    columns = 4
    cell_width = 440
    cell_height = 490
    rows_count = (len(panels) + columns - 1) // columns
    sheet = Image.new("RGB", (columns * cell_width, rows_count * cell_height + 80), "#ececec")
    draw = ImageDraw.Draw(sheet)
    font = ImageFont.load_default()
    draw.text((20, 16), "COMP-REQ-776: four-edge risks + ten expression families", fill="black", font=font)
    draw.text(
        (20, 38),
        "Red line = y16 status/body boundary. Frames are 200x200 strict 1bpp, shown 2x nearest-neighbor.",
        fill="#444444",
        font=font,
    )

    selection_receipt: list[dict[str, object]] = []
    for index, (label, state) in enumerate(panels):
        column = index % columns
        row_index = index // columns
        x0 = column * cell_width + 20
        y0 = row_index * cell_height + 90
        _, frame = audit.read_p4(args.source.parent / str(state["pbm_file"]))
        image = image_from_p4(frame).resize((400, 400), Image.Resampling.NEAREST)
        sheet.paste(image, (x0, y0 + 48))
        draw.rectangle((x0 - 1, y0 + 47, x0 + 400, y0 + 448), outline="#b00020", width=1)
        draw.line((x0, y0 + 48 + audit.STATUS_BAR_HEIGHT * 2, x0 + 399, y0 + 48 + audit.STATUS_BAR_HEIGHT * 2), fill="#d00000", width=2)
        _, _, margins = audit.black_geometry(frame)
        draw.text((x0, y0), label, fill="black", font=font)
        draw.text((x0, y0 + 16), str(state["id"])[:68], fill="#222222", font=font)
        draw.text((x0, y0 + 32), f"body margins {margins}", fill="#444444", font=font)
        selection_receipt.append(
            {
                "label": label,
                "state_id": state["id"],
                "kind": state["kind"],
                "pbm_sha256": state["pbm_sha256"],
                "body_margins": margins,
            }
        )

    args.output.parent.mkdir(parents=True, exist_ok=True)
    sheet.save(args.output)
    receipt = {
        "schema": "companion.comp_req_776.expression_risk_gallery.v1",
        "status": "MACHINE_READY",
        "source_state_count": len(rows),
        "panel_count": len(panels),
        "four_edge_risk_count": len(risk),
        "family_count": len(FAMILIES),
        "selection": selection_receipt,
        "png": str(args.output.relative_to(ROOT)).replace("\\", "/"),
        "png_sha256": sha256(args.output),
        "hardware_contact": 0,
    }
    receipt_path = args.output.with_suffix(".json")
    receipt_path.write_text(json.dumps(receipt, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps(receipt, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
