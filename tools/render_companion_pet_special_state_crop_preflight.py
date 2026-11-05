#!/usr/bin/env python3
"""Render locked special-state sources into review-only 200x200 safe-area sheets.

This is deliberately not a PBM/CEMP importer. It proves that the recorded
source crops can make safe 200x200 review frames before an owner decides
whether either pending special-state source is acceptable.
"""

from __future__ import annotations

import argparse
import hashlib
import io
import json
from dataclasses import dataclass
from pathlib import Path

from PIL import Image

from companion_expression_anchor import ANCHOR_POLICY, CANONICAL_CENTER, THRESHOLD, normalize


ROOT = Path(__file__).resolve().parents[1]
ART_DIR = ROOT / "docs" / "art" / "iterations" / "companion-pet-special-states-v1"
REVIEW_DIR = ART_DIR / "review-200x200"
REPORT = ROOT / "docs" / "validation" / "companion-pet-special-state-crop-preflight-20260717.json"
CANVAS = (200, 200)
SOURCE_SIZE = (1254, 1254)
MIN_EDGE_CLEARANCE_PX = 4


@dataclass(frozen=True)
class Candidate:
    identifier: str
    source_name: str
    source_sha256: str
    contact_name: str
    states: tuple[str, ...]


# These square source windows are scoped to the locked 1254x1254 candidate
# sheets. They preserve the complete face/charm for every cell at 200x200.
# They are review geometry only and cannot activate a product resource.
CROP_BOXES = (
    (0, 77, 330, 407),
    (340, 77, 670, 407),
    (610, 77, 940, 407),
    (924, 77, 1254, 407),
    (0, 455, 330, 785),
    (305, 455, 635, 785),
    (609, 455, 939, 785),
    (924, 455, 1254, 785),
    (0, 795, 330, 1125),
    (305, 795, 635, 1125),
    (609, 795, 939, 1125),
    (924, 795, 1254, 1125),
)

CANDIDATES = (
    Candidate(
        "special-system-v1",
        "generated_pet_special_system_v1_candidate.png",
        "AF9ADFD49C47C89DF674726D7201CC49C61ED636306013697822BB42FB1A9C82",
        "generated_pet_special_system_v1_crop_preflight_contact_sheet.png",
        (
            "voice.speaking", "recording.error", "power.charge_detected", "power.charging",
            "power.charged", "power.low_battery", "link.pairing", "link.connected",
            "link.syncing", "link.synced", "link.error", "system.error",
        ),
    ),
    Candidate(
        "special-journey-v1",
        "generated_pet_special_journey_v1_candidate.png",
        "95CC749134F169E73A2E2A99FA2B6F08AABDFE78D218677C347D2D687EA4B17F",
        "generated_pet_special_journey_v1_crop_preflight_contact_sheet.png",
        (
            "menu.open.entry", "menu.open.settle", "menu.blocked", "menu.exit",
            "upgrade.offer", "upgrade.prepare", "upgrade.transfer", "upgrade.verify",
            "upgrade.restart", "upgrade.success", "upgrade.error", "upgrade.error.recovery",
        ),
    ),
)


def repo_path(path: Path) -> str:
    return path.resolve().relative_to(ROOT).as_posix()


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest().upper()


def sha256_file(path: Path) -> str:
    return sha256_bytes(path.read_bytes())


def png_bytes(image: Image.Image) -> bytes:
    output = io.BytesIO()
    image.save(output, format="PNG", optimize=False)
    return output.getvalue()


def render_frame(source: Image.Image, crop_box: tuple[int, int, int, int]):
    reference = source.crop(crop_box).resize(CANVAS, Image.Resampling.LANCZOS)
    return normalize(reference, CANONICAL_CENTER)


def frame_metrics(image: Image.Image) -> dict[str, object]:
    bitmap = image.convert("1")
    pixels = bitmap.load()
    points = [(x, y) for y in range(bitmap.height) for x in range(bitmap.width) if pixels[x, y] == 0]
    if not points:
        raise ValueError("review frame has no visible ink")
    xs, ys = zip(*points)
    left, top, right, bottom = min(xs), min(ys), max(xs), max(ys)
    clearance = {
        "left": left,
        "top": top,
        "right": bitmap.width - 1 - right,
        "bottom": bitmap.height - 1 - bottom,
    }
    edge_ink = sum(pixels[x, 0] == 0 or pixels[x, bitmap.height - 1] == 0 for x in range(bitmap.width))
    edge_ink += sum(pixels[0, y] == 0 or pixels[bitmap.width - 1, y] == 0 for y in range(1, bitmap.height - 1))
    return {
        "ink_bbox": [left, top, right - left + 1, bottom - top + 1],
        "edge_clearance_px": clearance,
        "minimum_clearance_px": min(clearance.values()),
        "edge_ink_pixels": edge_ink,
        "ink_pixels": len(points),
    }


def contact_sheet(frames: list[Image.Image]) -> Image.Image:
    sheet = Image.new("1", (CANVAS[0] * 4, CANVAS[1] * 3), 1)
    for index, frame in enumerate(frames):
        sheet.paste(frame, ((index % 4) * CANVAS[0], (index // 4) * CANVAS[1]))
    return sheet


def candidate_result(candidate: Candidate, errors: list[str]) -> tuple[dict[str, object], bytes]:
    source_path = ART_DIR / candidate.source_name
    if not source_path.is_file():
        errors.append(f"{candidate.identifier}: source is missing")
        return {"id": candidate.identifier}, b""
    source_hash = sha256_file(source_path)
    if source_hash != candidate.source_sha256:
        errors.append(f"{candidate.identifier}: source hash drifted")
    source = Image.open(source_path).convert("L")
    if source.size != SOURCE_SIZE:
        errors.append(f"{candidate.identifier}: source size {source.size} is not {SOURCE_SIZE}")

    frames: list[Image.Image] = []
    cells: list[dict[str, object]] = []
    for index, (state, crop_box) in enumerate(zip(candidate.states, CROP_BOXES, strict=True)):
        if not (0 <= crop_box[0] < crop_box[2] <= SOURCE_SIZE[0] and 0 <= crop_box[1] < crop_box[3] <= SOURCE_SIZE[1]):
            errors.append(f"{candidate.identifier}: {state} crop is out of source bounds")
            continue
        frame, anchor = render_frame(source, crop_box)
        metrics = frame_metrics(frame)
        if int(metrics["edge_ink_pixels"]) != 0:
            errors.append(f"{candidate.identifier}: {state} has ink on a 200x200 edge")
        if int(metrics["minimum_clearance_px"]) < MIN_EDGE_CLEARANCE_PX:
            errors.append(
                f"{candidate.identifier}: {state} has only {metrics['minimum_clearance_px']} px review clearance"
            )
        frames.append(frame)
        cells.append(
            {
                "index": index,
                "state": state,
                "source_crop_box": list(crop_box),
                "anchor_policy": ANCHOR_POLICY,
                "source_anchor": list(anchor.source_anchor),
                "canonical_center": list(anchor.canonical_center),
                "normalization_offset": list(anchor.normalization_offset),
                "phase_offset": [0, 0],
                "requested_center": list(anchor.canonical_center),
                "final_output_bounds": metrics["ink_bbox"],
                **metrics,
            }
        )

    if len(frames) != 12:
        errors.append(f"{candidate.identifier}: expected 12 review frames, rendered {len(frames)}")
    sheet_bytes = png_bytes(contact_sheet(frames)) if len(frames) == 12 else b""
    contact_path = REVIEW_DIR / candidate.contact_name
    return {
        "id": candidate.identifier,
        "source": repo_path(source_path),
        "source_sha256": source_hash,
        "source_dimensions_px": list(source.size),
        "contact_sheet": repo_path(contact_path),
        "contact_sheet_sha256": sha256_bytes(sheet_bytes) if sheet_bytes else None,
        "contact_sheet_dimensions_px": [CANVAS[0] * 4, CANVAS[1] * 3],
        "frames": cells,
    }, sheet_bytes


def build_report() -> tuple[dict[str, object], dict[Path, bytes]]:
    errors: list[str] = []
    sources: list[dict[str, object]] = []
    outputs: dict[Path, bytes] = {}
    for candidate in CANDIDATES:
        result, sheet_bytes = candidate_result(candidate, errors)
        sources.append(result)
        if sheet_bytes:
            outputs[REVIEW_DIR / candidate.contact_name] = sheet_bytes

    report: dict[str, object] = {
        "schema": "companion.pet_special_state_crop_preflight.v1",
        "status": "PASS_MACHINE_SAFE_CROP_PREVIEW_NOT_IMPORTABLE" if not errors else "FAIL",
        "purpose": "Review the exact locked source crops at 200x200 before any owner decision or resource import.",
        "profile": {
            "width": CANVAS[0],
            "height": CANVAS[1],
            "threshold": THRESHOLD,
            "minimum_edge_clearance_px": MIN_EDGE_CLEARANCE_PX,
            "source_crop_policy": "explicit square windows locked to the recorded 1254x1254 source hashes",
            "anchor_policy": ANCHOR_POLICY,
        },
        "sources": sources,
        "runtime_boundary": {
            "review_png_only": True,
            "pbm_imported": False,
            "cemp_packed": False,
            "external_flash_provisioned": False,
            "firmware_flashed": False,
            "ota_behavior_changed": False,
            "owner_visual_pass": False,
        },
        "physical_limit": "This source-crop proof does not clear COMP-REQ-078. Real WB55 panel viewport, orientation, transport and lower-edge behavior remain a focused G5 physical gate.",
        "errors": errors,
    }
    return report, outputs


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--write", action="store_true", help="Write review-only contact sheets and the preflight JSON.")
    args = parser.parse_args()
    report, outputs = build_report()
    rendered = json.dumps(report, indent=2, sort_keys=True) + "\n"
    if args.write:
        REVIEW_DIR.mkdir(parents=True, exist_ok=True)
        for path, data in outputs.items():
            path.write_bytes(data)
        REPORT.write_text(rendered, encoding="ascii")
    else:
        if not REPORT.is_file() or REPORT.read_text(encoding="ascii") != rendered:
            report["errors"].append(f"stale {repo_path(REPORT)}")
        for path, data in outputs.items():
            if not path.is_file() or path.read_bytes() != data:
                report["errors"].append(f"stale {repo_path(path)}")
    if report["errors"]:
        for error in report["errors"]:
            print(f"FAIL: {error}")
        return 1
    print("PASS: all 24 pending special-state review frames retain >=4 px canvas clearance without PBM/CEMP import.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
