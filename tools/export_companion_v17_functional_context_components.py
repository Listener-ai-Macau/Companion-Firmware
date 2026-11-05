#!/usr/bin/env python3
"""Export V17 functional-context source marks as unbound 1bpp component masks."""

from __future__ import annotations

import argparse
import hashlib
import json
import shutil
from pathlib import Path
from typing import Any

from PIL import Image

from verify_companion_v17_functional_context_source import (
    INK_THRESHOLD,
    ROOT,
    connected_components,
    sha256,
    split_groups,
    valid_menu_group,
    valid_recording_group,
    valid_upgrade_group,
)


V17_ROOT = ROOT / "docs/art/iterations/companion-pet-expression-v9-extension-v17-functional-context-accents"
DEFAULT_ATTEMPT = V17_ROOT / "candidate/attempt-01-generated-functional-context-accent-panel.json"
SOURCE_GATE = ROOT / "docs/validation/companion-v9-extension-v17-functional-context-source-20260719.json"
DEFAULT_OUTPUT = V17_ROOT / "candidate/component-export-attempt-01"
TARGET_SCALE_DIVISOR = 3
TARGET_CANVAS = (200, 200)


def pbm_from_crop(source: Image.Image, crop: list[int], scale: float) -> Image.Image:
    left, top, right, bottom = crop
    source_crop = source.crop((left, top, right, bottom)).convert("L")
    mask = Image.new("1", source_crop.size, 1)
    for y in range(source_crop.height):
        for x in range(source_crop.width):
            if source_crop.getpixel((x, y)) < INK_THRESHOLD:
                mask.putpixel((x, y), 0)
    width = max(1, round(mask.width * scale))
    height = max(1, round(mask.height * scale))
    return mask.resize((width, height), Image.Resampling.NEAREST)


def transparent_preview(mask: Image.Image) -> Image.Image:
    preview = Image.new("RGBA", mask.size, (0, 0, 0, 0))
    pixels = preview.load()
    for y in range(mask.height):
        for x in range(mask.width):
            if mask.getpixel((x, y)) == 0:
                pixels[x, y] = (0, 0, 0, 255)
    return preview


def ink_count(image: Image.Image) -> int:
    return sum(pixel == 0 for pixel in image.convert("1").getdata())


def named_components(groups: dict[str, list[dict[str, Any]]], source_width: int) -> list[tuple[str, dict[str, Any], str]]:
    menu = sorted(groups["menu_active"], key=lambda item: item["center"][1])
    recording_left = sorted(
        (item for item in groups["recording_active"] if item["center"][0] < source_width / 2),
        key=lambda item: item["center"][0],
    )
    recording_right = sorted(
        (item for item in groups["recording_active"] if item["center"][0] >= source_width / 2),
        key=lambda item: item["center"][0],
    )
    horizontal = [item for item in groups["upgrade_active"]
                  if (item["crop"][2] - item["crop"][0]) > (item["crop"][3] - item["crop"][1])]
    vertical = [item for item in groups["upgrade_active"]
                if (item["crop"][2] - item["crop"][0]) <= (item["crop"][3] - item["crop"][1])]
    top, bottom = sorted(horizontal, key=lambda item: item["center"][1])
    left, right = sorted(vertical, key=lambda item: item["center"][0])
    return [
        ("menu_dot_top", menu[0], "menu_active"),
        ("menu_dot_middle", menu[1], "menu_active"),
        ("menu_dot_bottom", menu[2], "menu_active"),
        ("recording_ripple_left_outer", recording_left[0], "recording_active"),
        ("recording_ripple_left_inner", recording_left[1], "recording_active"),
        ("recording_ripple_right_inner", recording_right[0], "recording_active"),
        ("recording_ripple_right_outer", recording_right[1], "recording_active"),
        ("upgrade_segment_top", top, "upgrade_active"),
        ("upgrade_segment_right", right, "upgrade_active"),
        ("upgrade_segment_bottom", bottom, "upgrade_active"),
        ("upgrade_segment_left", left, "upgrade_active"),
    ]


def source_only_reassemblies(masks: dict[str, Image.Image]) -> dict[str, Image.Image]:
    result: dict[str, Image.Image] = {}
    menu = Image.new("1", TARGET_CANVAS, 1)
    for name, y in (("menu_dot_top", 42), ("menu_dot_middle", 68), ("menu_dot_bottom", 94)):
        mask = masks[name]
        menu.paste(mask, ((200 - mask.width) // 2, y))
    result["menu_active"] = menu
    recording = Image.new("1", TARGET_CANVAS, 1)
    for name, x, y in (
        ("recording_ripple_left_outer", 34, 72),
        ("recording_ripple_left_inner", 55, 82),
        ("recording_ripple_right_inner", 134, 82),
        ("recording_ripple_right_outer", 152, 72),
    ):
        recording.paste(masks[name], (x, y))
    result["recording_active"] = recording
    upgrade = Image.new("1", TARGET_CANVAS, 1)
    for name, x, y in (
        ("upgrade_segment_top", 88, 32),
        ("upgrade_segment_right", 130, 55),
        ("upgrade_segment_bottom", 88, 105),
        ("upgrade_segment_left", 61, 55),
    ):
        upgrade.paste(masks[name], (x, y))
    result["upgrade_active"] = upgrade
    return result


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--attempt", type=Path, default=DEFAULT_ATTEMPT)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--clean", action="store_true")
    args = parser.parse_args()
    attempt_path = args.attempt.resolve()
    output = args.output.resolve()
    try:
        gate = json.loads(SOURCE_GATE.read_text(encoding="utf-8"))
        if gate.get("status") != "PASS_V17_FUNCTIONAL_CONTEXT_SOURCE_GATE":
            raise ValueError("V17 source gate has not passed")
        attempt = json.loads(attempt_path.read_text(encoding="utf-8"))
        if attempt.get("status") != "PASS_MACHINE_SOURCE_GATE_PENDING_COMPONENT_EXPORT":
            raise ValueError("V17 attempt is not ready for component export")
        source_path = ROOT / str(attempt["generated_image"])
        source = Image.open(source_path).convert("L")
        components = connected_components(source)
        groups = split_groups(components, source.width)
        if len(components) != 11 or not valid_menu_group(groups["menu_active"]) or \
                not valid_recording_group(groups["recording_active"], source.width) or \
                not valid_upgrade_group(groups["upgrade_active"]):
            raise ValueError("V17 source component geometry drifted after its source gate")
        if args.clean and output.exists():
            shutil.rmtree(output)
        masks_dir = output / "component-masks"
        preview_dir = output / "preview-layers"
        reassembly_dir = output / "source-only-reassembly-200x200"
        for directory in (masks_dir, preview_dir, reassembly_dir):
            directory.mkdir(parents=True, exist_ok=True)
        scale = TARGET_CANVAS[0] / (source.width / TARGET_SCALE_DIVISOR)
        masks: dict[str, Image.Image] = {}
        layout_components: dict[str, Any] = {}
        for name, item, group in named_components(groups, source.width):
            mask = pbm_from_crop(source, item["crop"], scale)
            mask_path = masks_dir / f"{name}.pbm"
            preview_path = preview_dir / f"{name}.png"
            mask.save(mask_path)
            transparent_preview(mask).save(preview_path)
            masks[name] = mask
            layout_components[name] = {
                "context_group": group,
                "source_crop": item["crop"],
                "source_ink_pixels": item["ink_pixels"],
                "target_size": [mask.width, mask.height],
                "mask": mask_path.relative_to(ROOT).as_posix(),
                "mask_sha256": sha256(mask_path),
                "preview_layer": preview_path.relative_to(ROOT).as_posix(),
                "preview_layer_sha256": sha256(preview_path),
                "z_order": "unbound_secondary_context_accent",
                "legal_offset": {"x": [-2, 2], "y": [-2, 2]},
            }
        reassemblies = source_only_reassemblies(masks)
        reassembly_paths: dict[str, str] = {}
        for group, image in reassemblies.items():
            path = reassembly_dir / f"{group}-source-only.pbm"
            image.save(path)
            reassembly_paths[group] = path.relative_to(ROOT).as_posix()
        contact = Image.new("1", (600, 200), 1)
        for index, group in enumerate(("menu_active", "recording_active", "upgrade_active")):
            contact.paste(reassemblies[group], (index * 200, 0))
        contact_path = output / "functional-context-source-only-contact-sheet.png"
        contact.save(contact_path)
        layout = {
            "schema": "companion.v17_functional_context_component_source_layout.v1",
            "status": "UNBOUND_PENDING_OWNER_ART_REVIEW",
            "locked_v9_source_sha256": attempt["source_reference_sha256"],
            "generated_source": attempt["generated_image"],
            "generated_source_sha256": attempt["generated_image_sha256"],
            "canvas": list(TARGET_CANVAS),
            "source_to_target_scale": scale,
            "components": layout_components,
            "context_groups": {
                "menu_active": ["menu_dot_top", "menu_dot_middle", "menu_dot_bottom"],
                "recording_active": [
                    "recording_ripple_left_outer", "recording_ripple_left_inner",
                    "recording_ripple_right_inner", "recording_ripple_right_outer",
                ],
                "upgrade_active": [
                    "upgrade_segment_top", "upgrade_segment_right",
                    "upgrade_segment_bottom", "upgrade_segment_left",
                ],
            },
            "source_only_reassemblies": reassembly_paths,
            "contact_sheet": contact_path.relative_to(ROOT).as_posix(),
            "prohibited_before_owner_art_review": [
                "face binding", "event choreography", "external NOR CRIG export", "runtime activation",
                "whole-face card playback", "code-drawn fallback",
            ],
            "runtime_resource_activated": False,
            "active_candidate_binding": "forbidden",
        }
        layout_path = output / "v17-functional-context-component-layout.json"
        layout_path.write_text(json.dumps(layout, indent=2) + "\n", encoding="ascii")
        report = {
            "schema": "companion.v17_functional_context_component_source_export.v1",
            "status": "PASS_V17_FUNCTIONAL_CONTEXT_SOURCE_MASK_EXPORT_UNBOUND",
            "layout": layout_path.relative_to(ROOT).as_posix(),
            "component_count": len(layout_components),
            "source_only_reassembly_ink_pixels": {group: ink_count(image) for group, image in reassemblies.items()},
            "contact_sheet": contact_path.relative_to(ROOT).as_posix(),
            "runtime_resource_activated": False,
            "active_candidate_binding": "forbidden",
        }
        (output / "export-report.json").write_text(json.dumps(report, indent=2) + "\n", encoding="ascii")
    except (OSError, ValueError, json.JSONDecodeError, KeyError) as exc:
        print(f"FAIL: {exc}")
        return 1
    print("PASS: exported 11 V17 functional-context source masks; all remain unbound.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
