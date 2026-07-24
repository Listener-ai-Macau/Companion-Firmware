#!/usr/bin/env python3
"""Verify V14 sleep source reassembly uses only registered source masks."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from PIL import Image

from verify_companion_v14_sleep_zzz_component_source import REQUIRED_COMPONENTS, sha256


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_CANDIDATE = ROOT / "docs/art/iterations/companion-pet-expression-v9-extension-v14-sleep-zzz-component-repair/candidate"


def relative(path: Path) -> str:
    return path.resolve().relative_to(ROOT).as_posix()


def has_ink(image: Image.Image) -> bool:
    return any(value == 0 for value in image.convert("1").getdata())


def difference(left: Image.Image, right: Image.Image) -> int:
    if left.size != right.size:
        return -1
    return sum((a ^ b).bit_count() for a, b in zip(left.convert("1").tobytes(), right.convert("1").tobytes()))


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--candidate", type=Path, default=DEFAULT_CANDIDATE)
    parser.add_argument("--write", type=Path, required=True)
    args = parser.parse_args()
    candidate = args.candidate.resolve()
    errors: list[str] = []
    layout_path = candidate / "sleep-zzz-component-source-layout.json"
    report_path = candidate / "export-report.json"
    try:
        layout = json.loads(layout_path.read_text(encoding="utf-8"))
        export = json.loads(report_path.read_text(encoding="utf-8"))
        components = layout.get("components") if isinstance(layout, dict) else None
        errors.extend([] if isinstance(layout, dict) and
                      layout.get("status") == "CANDIDATE_SOURCE_COMPONENT_EXPORT_PENDING_OWNER_ART_REVIEW" and
                      layout.get("runtime_resource_activated") is False and
                      layout.get("active_candidate_binding") == "forbidden" else
                      ["layout is not an unbound runtime-inactive V14 candidate"])
        errors.extend([] if isinstance(export, dict) and
                      export.get("status") == "PASS_V14_SLEEP_ZZZ_COMPONENT_SOURCE_EXPORT_RUNTIME_INACTIVE" and
                      export.get("component_count") == len(REQUIRED_COMPONENTS) and
                      export.get("runtime_resource_activated") is False and
                      export.get("active_candidate_binding") == "forbidden" else
                      ["export metadata does not preserve the unbound V14 policy"])
        if not isinstance(components, list) or [item.get("name") for item in components if isinstance(item, dict)] != list(REQUIRED_COMPONENTS):
            errors.append("V14 component vocabulary drifted")
            components = []
        normalized = ROOT / str(layout.get("normalization", {}).get("normalized", ""))
        if not normalized.is_file():
            errors.append("V14 normalized source is missing")
            reference = Image.new("1", (200, 200), 1)
        else:
            reference = Image.open(normalized).convert("1")
        canvas = Image.new("1", (200, 200), 1)
        for item in components:
            if not isinstance(item, dict):
                continue
            mask = ROOT / str(item.get("mask", ""))
            position = item.get("base_position")
            if not mask.is_file() or not isinstance(position, list) or len(position) != 2:
                errors.append(f"component artifact is missing: {item.get('name')}")
                continue
            image = Image.open(mask).convert("1")
            if not has_ink(image) or item.get("mask_sha256") != sha256(mask):
                errors.append(f"component source mask drifted: {item.get('name')}")
                continue
            canvas.paste(image, (int(position[0]), int(position[1])))
        rendered = candidate / "reassembled-sleep-zzz-component-source-200x200.pbm"
        rendered_preview = candidate / "reassembled-sleep-zzz-component-source-contact.png"
        rendered.parent.mkdir(parents=True, exist_ok=True)
        canvas.save(rendered)
        canvas.convert("L").resize((1000, 1000), Image.Resampling.NEAREST).save(rendered_preview)
        pixel_difference = difference(reference, canvas)
        if pixel_difference != 0:
            errors.append("registered V14 source masks do not reassemble to the normalized sleep source")
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        errors.append(str(exc))
        pixel_difference = -1
        rendered = candidate / "reassembled-sleep-zzz-component-source-200x200.pbm"
        rendered_preview = candidate / "reassembled-sleep-zzz-component-source-contact.png"
    result = {
        "schema": "companion.v14_sleep_zzz_component_source_export_gate.v1",
        "status": "PASS_V14_SLEEP_ZZZ_COMPONENT_SOURCE_EXPORT_GATE" if not errors else "FAIL_V14_SLEEP_ZZZ_COMPONENT_SOURCE_EXPORT_GATE",
        "candidate": relative(candidate),
        "component_count": len(REQUIRED_COMPONENTS),
        "reassembled": relative(rendered),
        "reassembled_sha256": sha256(rendered) if rendered.is_file() else None,
        "reassembled_preview": relative(rendered_preview) if rendered_preview.is_file() else None,
        "pixel_difference_from_normalized_source": pixel_difference,
        "runtime_resource_activated": False,
        "active_candidate_binding": "forbidden",
        "full_face_source_card_playback": "forbidden",
        "errors": errors,
    }
    args.write.parent.mkdir(parents=True, exist_ok=True)
    args.write.write_text(json.dumps(result, indent=2) + "\n", encoding="ascii")
    if errors:
        for error in errors:
            print(f"ERROR: {error}")
        return 1
    print("PASS: V14 sleep reassembly uses exactly thirteen registered generated source masks and remains unbound.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
