#!/usr/bin/env python3
"""Render the normal CEMP expression-source contact sheet.

This is the repeatable visual gate for the product rule that normal expression
assets come from the accepted generated sheet, not older procedural art.
"""

from __future__ import annotations

import argparse
import json
import pathlib
import sys
from typing import Any

from PIL import Image, ImageDraw


ROOT = pathlib.Path(__file__).resolve().parents[1]
MANIFEST = ROOT / "app/companion_pendant/epaper/assets/emote_matrix_white_200x200.json"
IMPORT_REPORT = ROOT / "docs/validation/companion-screen-generated-expression-sheet-import.json"
DEFAULT_REPORT = ROOT / "docs/validation/companion-screen-generated-expression-normal-pack-contact-sheet.json"

CELL_W = 238
CELL_H = 252
THUMB_SIZE = 160
COLS = 5


def rel(path: pathlib.Path) -> str:
    try:
        return path.resolve().relative_to(ROOT).as_posix()
    except ValueError:
        return path.as_posix()


def load_json(path: pathlib.Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def generated_outputs(report: dict[str, Any]) -> dict[str, dict[str, Any]]:
    outputs: dict[str, dict[str, Any]] = {}
    for item in report.get("outputs", []):
        pose = str(item.get("pose", ""))
        index = item.get("index")
        for file_text in item.get("files", []):
            path = pathlib.Path(str(file_text))
            outputs[path.name] = {
                "pose": pose,
                "pose_index": index,
                "import_path": path.as_posix(),
            }
    return outputs


def manifest_expression_sources(manifest: dict[str, Any]) -> list[dict[str, Any]]:
    first_seen: dict[str, dict[str, Any]] = {}
    for clip in manifest.get("clips", []):
        clip_name = str(clip.get("name", ""))
        for frame_index, frame in enumerate(clip.get("frames", [])):
            source_text = str(frame.get("source", ""))
            source = pathlib.Path(source_text)
            name = source.name
            if not name.startswith("expression_") or not name.endswith(".pbm"):
                continue
            if name not in first_seen:
                first_seen[name] = {
                    "name": name,
                    "source": source_text,
                    "first_clip": clip_name,
                    "first_frame": frame_index,
                    "uses": 0,
                }
            first_seen[name]["uses"] = int(first_seen[name]["uses"]) + 1
    return [first_seen[name] for name in sorted(first_seen)]


def wrap_label(text: str, max_chars: int = 25) -> list[str]:
    parts: list[str] = []
    current = ""
    for piece in text.replace("_", " _").split():
        candidate = (current + piece).strip()
        if len(candidate) <= max_chars:
            current = candidate
            continue
        if current:
            parts.append(current.replace(" _", "_"))
        current = piece
    if current:
        parts.append(current.replace(" _", "_"))
    return parts[:3]


def render_contact_sheet(rows: list[dict[str, Any]], output: pathlib.Path,
                         revision: int) -> None:
    row_count = (len(rows) + COLS - 1) // COLS
    image = Image.new("RGB", (COLS * CELL_W, row_count * CELL_H + 48), "white")
    draw = ImageDraw.Draw(image)
    draw.text((16, 14), f"Companion rev{revision} normal CEMP expression sources", fill="black")
    draw.text((16, 30), "All normal expression PBMs must come from generated-sheet import outputs/aliases.", fill="black")

    for index, row in enumerate(rows):
        col = index % COLS
        grid_row = index // COLS
        x = col * CELL_W + 14
        y = grid_row * CELL_H + 58
        asset = ROOT / pathlib.Path(str(row["source"]))
        if not asset.exists():
            asset = ROOT / "docs/validation/epaper" / str(row["name"])
        with Image.open(asset) as source:
            thumb = source.convert("RGB").resize((THUMB_SIZE, THUMB_SIZE), Image.Resampling.NEAREST)
        draw.rectangle((x - 4, y - 4, x + THUMB_SIZE + 4, y + THUMB_SIZE + 4), outline="black")
        image.paste(thumb, (x, y))
        label_y = y + THUMB_SIZE + 12
        draw.text((x, label_y), f"{index + 1:02d}. {row['pose']}", fill="black")
        for line_index, line in enumerate(wrap_label(str(row["name"]))):
            draw.text((x, label_y + 16 + line_index * 14), line, fill="black")
        draw.text((x, label_y + 62), f"uses={row['uses']} first={row['first_clip']}", fill="black")

    output.parent.mkdir(parents=True, exist_ok=True)
    image.save(output)


def build_report(image_path: pathlib.Path) -> tuple[dict[str, Any], list[str]]:
    manifest = load_json(MANIFEST)
    import_report = load_json(IMPORT_REPORT)
    generated = generated_outputs(import_report)
    rows = manifest_expression_sources(manifest)
    errors: list[str] = []

    for row in rows:
        name = str(row["name"])
        if name not in generated:
            errors.append(f"{name} is used by the normal CEMP manifest but missing from generated import outputs")
            row["pose"] = "MISSING"
            row["pose_index"] = None
            row["import_path"] = None
            continue
        row.update(generated[name])

    report = {
        "schema_id": "companion.screen.generated_expression_normal_pack_contact_sheet.v1",
        "status": "PASS" if not errors else "FAIL",
        "manifest": rel(MANIFEST),
        "manifest_revision": manifest.get("revision"),
        "import_report": rel(IMPORT_REPORT),
        "import_status": import_report.get("status"),
        "style_source_of_truth": import_report.get("style_source_of_truth"),
        "contact_sheet": rel(image_path),
        "expression_source_count": len(rows),
        "generated_coverage": {
            "used_by_manifest": len(rows),
            "covered_by_import": sum(1 for row in rows if row.get("import_path")),
            "missing": [row["name"] for row in rows if not row.get("import_path")],
        },
        "sources": rows,
    }
    return report, errors


def write_outputs(image_path: pathlib.Path, report_path: pathlib.Path, report: dict[str, Any]) -> None:
    render_contact_sheet(report["sources"], image_path, int(report["manifest_revision"]))
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(json.dumps(report, indent=2, ensure_ascii=False, sort_keys=True) + "\n", encoding="utf-8")


def verify_outputs(image_path: pathlib.Path, report_path: pathlib.Path, report: dict[str, Any],
                   errors: list[str]) -> None:
    if report.get("status") != "PASS":
        errors.append("normal pack contact sheet report is not PASS")
    manifest = load_json(MANIFEST)
    if report.get("manifest_revision") != manifest.get("revision"):
        errors.append("normal pack contact sheet must describe the active manifest revision")
    coverage = report.get("generated_coverage", {})
    if coverage.get("used_by_manifest") != 39 or coverage.get("covered_by_import") != 39:
        errors.append("normal pack generated coverage must remain 39/39")
    if not image_path.exists():
        errors.append(f"missing contact sheet image: {rel(image_path)}")
    if not report_path.exists():
        errors.append(f"missing contact sheet report: {rel(report_path)}")
    else:
        expected = json.dumps(report, indent=2, ensure_ascii=False, sort_keys=True) + "\n"
        if report_path.read_text(encoding="utf-8") != expected:
            errors.append(f"stale contact sheet report: {rel(report_path)}")


def parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--image", type=pathlib.Path)
    parser.add_argument("--report", type=pathlib.Path, default=DEFAULT_REPORT)
    parser.add_argument("--write", action="store_true")
    return parser.parse_args(argv)


def main(argv: list[str]) -> int:
    args = parse_args(argv)
    manifest_revision = int(load_json(MANIFEST).get("revision", 0))
    default_image = ROOT / ".cache" / "validation" / f"rev{manifest_revision}-generated-expression-normal-pack-sources.png"
    requested_image = args.image if args.image is not None else default_image
    image_path = requested_image if requested_image.is_absolute() else ROOT / requested_image
    report_path = args.report if args.report.is_absolute() else ROOT / args.report
    report, errors = build_report(image_path)
    if args.write and not errors:
        write_outputs(image_path, report_path, report)
    verify_outputs(image_path, report_path, report, errors)

    if errors:
        print("FAIL: generated expression normal-pack contact sheet check failed:", file=sys.stderr)
        for error in errors:
            print(f" - {error}", file=sys.stderr)
        return 1
    print(f"PASS: generated expression normal-pack contact sheet verified -> {rel(image_path)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
