#!/usr/bin/env python3
"""Render one real final-PBM pose for each COMP-REQ-789 component stage."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont


FAMILIES = (
    "calm", "curious", "delighted", "warm", "playful",
    "bashful", "thoughtful", "focused", "alert",
)
STAGES = ("eyes_lead", "brows_reply", "lower_face_reply", "ornament_follow")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--source-pack-manifest", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    return parser.parse_args()


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest().upper()


def main() -> int:
    args = parse_args()
    manifest = json.loads(args.source_pack_manifest.read_text(encoding="utf-8"))
    root = args.source_pack_manifest.resolve().parent
    states = [state for state in manifest["states"] if state.get("kind") == "life"]
    selected: dict[tuple[str, str], dict] = {}
    for family in FAMILIES:
        family_states = [state for state in states if state.get("family") == family]
        for stage in STAGES:
            selected[(family, stage)] = next(
                (state for state in family_states if state.get("component_stage") == stage),
                family_states[0],
            )

    width = 4 * 210 + 20
    height = 58 + len(FAMILIES) * 232
    sheet = Image.new("RGB", (width, height), "#e8e8e5")
    draw = ImageDraw.Draw(sheet)
    font = ImageFont.load_default()
    draw.text((10, 10), "COMP-REQ-789 final PBM component choreography", fill="black", font=font)
    draw.text(
        (10, 29),
        "Columns: eyes lead | brows reply | lower-face reply | ornament follow",
        fill="#333333",
        font=font,
    )
    panels = []
    for row, family in enumerate(FAMILIES):
        y = 52 + row * 232
        for column, stage in enumerate(STAGES):
            state = selected[(family, stage)]
            x = 10 + column * 210
            frame = Image.open(root / state["pbm_file"]).convert("RGB")
            sheet.paste(frame, (x, y + 26))
            draw.rectangle((x, y + 26, x + 199, y + 225), outline="#777777", width=1)
            draw.text(
                (x, y),
                f"{family} / {stage.replace('_', ' ')}",
                fill="black",
                font=font,
            )
            panels.append({
                "family": family,
                "stage": stage,
                "state_id": state["id"],
                "pbm_sha256": state["pbm_sha256"],
            })

    args.output.parent.mkdir(parents=True, exist_ok=True)
    sheet.save(args.output)
    receipt = {
        "schema": "companion.comp_req_789.component_gallery.v1",
        "status": "MACHINE_READY",
        "source_pack_manifest_sha256": sha256(args.source_pack_manifest),
        "png": str(args.output),
        "png_sha256": sha256(args.output),
        "panels": panels,
    }
    receipt_path = args.output.with_suffix(".json")
    receipt_path.write_text(json.dumps(receipt, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({
        "status": receipt["status"],
        "png": receipt["png"],
        "png_sha256": receipt["png_sha256"],
        "panel_count": len(panels),
    }, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
