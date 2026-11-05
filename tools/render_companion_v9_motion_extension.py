#!/usr/bin/env python3
"""Build a candidate-only v9 daily-motion CEMP from versioned source art."""

from __future__ import annotations

import argparse
import hashlib
import json
import pathlib
import sys
from dataclasses import dataclass

from PIL import Image, ImageDraw

ROOT = pathlib.Path(__file__).resolve().parents[1]
TOOLS = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(TOOLS))

from build_emote_asset_pack import build_pack  # noqa: E402
from companion_expression_anchor import (  # noqa: E402
    ANCHOR_POLICY,
    CANONICAL_CENTER,
    ink_bounds,
    normalize,
    output_bounds,
    translate,
)


CANVAS = (200, 200)
LOCKED_V9_SHA256 = "919F344957661DEF2099AD56AB1286CCA9DBA4D8F08B702617B6DF5B1A28E9DA"
PHASE_ORDER = ("entry", "sustain", "settle")
SAFE_INSET_PX = 4


@dataclass(frozen=True)
class Feature:
    name: str
    role: str
    regions: tuple[tuple[int, int, int, int], ...]
    min_changed_pixels: int


@dataclass(frozen=True)
class Phase:
    name: str
    crop_box: tuple[int, int, int, int]


@dataclass(frozen=True)
class Layout:
    path: pathlib.Path
    source: pathlib.Path
    source_sha256: str
    parent_source_sha256: str
    prompt_revision: str
    revision: int
    phases: tuple[Phase, ...]
    features: tuple[Feature, ...]


def sha256(path: pathlib.Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest().upper()


def repo_relative(path: pathlib.Path) -> str:
    return path.resolve().relative_to(ROOT).as_posix()


def require_string(value: object, name: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{name} must be a non-empty string")
    return value


def require_sha256(value: object, name: str) -> str:
    result = require_string(value, name).upper()
    if len(result) != 64 or any(char not in "0123456789ABCDEF" for char in result):
        raise ValueError(f"{name} must be a SHA-256 hex digest")
    return result


def require_int(value: object, name: str, minimum: int, maximum: int) -> int:
    if not isinstance(value, int) or isinstance(value, bool) or not minimum <= value <= maximum:
        raise ValueError(f"{name} must be an integer in [{minimum}, {maximum}]")
    return value


def require_box(value: object, name: str) -> tuple[int, int, int, int]:
    if not isinstance(value, list) or len(value) != 4:
        raise ValueError(f"{name} must be [x, y, width, height]")
    x, y, width, height = [require_int(item, name, 0, 100000) for item in value]
    if width == 0 or height == 0:
        raise ValueError(f"{name} must have non-zero width and height")
    return x, y, width, height


def require_canvas_region(value: object, name: str) -> tuple[int, int, int, int]:
    x, y, width, height = require_box(value, name)
    if x + width > CANVAS[0] or y + height > CANVAS[1]:
        raise ValueError(f"{name} must fit inside the 200x200 target canvas")
    return x, y, width, height


def load_layout(path: pathlib.Path) -> Layout:
    raw = json.loads(path.read_text(encoding="utf-8"))
    if raw.get("schema") != "companion.v9_motion_extension_layout.v1":
        raise ValueError("unsupported v9 motion extension layout schema")
    if raw.get("status") != "CANDIDATE_PENDING_OWNER_REVIEW":
        raise ValueError("layout must remain CANDIDATE_PENDING_OWNER_REVIEW")
    if raw.get("runtime_resource_activated") is not False:
        raise ValueError("motion extension layout must not activate a runtime resource")
    source_text = require_string(raw.get("source"), "source")
    source = (ROOT / source_text).resolve()
    if not source.is_file() or ROOT not in source.parents:
        raise ValueError("source must be a repository image")
    source_sha = require_sha256(raw.get("source_sha256"), "source_sha256")
    parent_sha = require_sha256(raw.get("parent_source_sha256"), "parent_source_sha256")
    if parent_sha != LOCKED_V9_SHA256:
        raise ValueError("motion extension must declare the locked v9 parent hash")
    if sha256(source) != source_sha:
        raise ValueError("motion extension source SHA-256 drifted")
    prompt_revision = require_string(raw.get("prompt_revision"), "prompt_revision")
    revision = require_int(raw.get("revision"), "revision", 91, 0xFFFFFFFF)

    profile = raw.get("profile")
    if not isinstance(profile, dict) or profile != {
        "width": 200,
        "height": 200,
        "pixel_format": "mono_1bpp_white_is_one_msb",
        "safe_inset_px": SAFE_INSET_PX,
    }:
        raise ValueError("profile must be the fixed 200x200 1-bit safe-area profile")

    phases_raw = raw.get("phases")
    if not isinstance(phases_raw, list) or len(phases_raw) != len(PHASE_ORDER):
        raise ValueError("layout must contain exactly entry, sustain, settle")
    phases: list[Phase] = []
    source_image = Image.open(source).convert("L")
    seen_phases: set[str] = set()
    for index, item in enumerate(phases_raw):
        if not isinstance(item, dict):
            raise ValueError(f"phases[{index}] must be an object")
        name = require_string(item.get("name"), f"phases[{index}].name")
        crop_box = require_box(item.get("source_crop_box"), f"phases[{index}].source_crop_box")
        x, y, width, height = crop_box
        if x + width > source_image.width or y + height > source_image.height:
            raise ValueError(f"phase {name} crop exceeds source image")
        if name in seen_phases:
            raise ValueError("phase names must be unique")
        seen_phases.add(name)
        phases.append(Phase(name, crop_box))
    if tuple(phase.name for phase in phases) != PHASE_ORDER:
        raise ValueError("phase order must be entry, sustain, settle")

    features_raw = raw.get("motion_features")
    if not isinstance(features_raw, list) or len(features_raw) < 2:
        raise ValueError("layout must declare eye/highlight and secondary motion features")
    features: list[Feature] = []
    names: set[str] = set()
    has_eye = False
    has_secondary = False
    for index, item in enumerate(features_raw):
        if not isinstance(item, dict):
            raise ValueError(f"motion_features[{index}] must be an object")
        name = require_string(item.get("name"), f"motion_features[{index}].name")
        role = require_string(item.get("role"), f"motion_features[{index}].role")
        if role not in {"eye_highlight", "secondary"}:
            raise ValueError("motion feature role must be eye_highlight or secondary")
        regions_raw = item.get("regions")
        if not isinstance(regions_raw, list) or not regions_raw:
            raise ValueError(f"motion feature {name} requires target regions")
        regions = tuple(
            require_canvas_region(region, f"motion feature {name} region")
            for region in regions_raw
        )
        minimum = require_int(item.get("min_changed_pixels"),
                              f"motion feature {name} min_changed_pixels", 1, 40000)
        if name in names:
            raise ValueError("motion feature names must be unique")
        names.add(name)
        has_eye = has_eye or role == "eye_highlight"
        has_secondary = has_secondary or role == "secondary"
        features.append(Feature(name, role, regions, minimum))
    if not has_eye or not has_secondary:
        raise ValueError("motion layout requires one eye_highlight and one secondary feature")
    return Layout(path.resolve(), source, source_sha, parent_sha, prompt_revision,
                  revision, tuple(phases), tuple(features))


def to_pbm(source: Image.Image, phase: Phase) -> tuple[Image.Image, Image.Image, object]:
    x, y, width, height = phase.crop_box
    reference = source.crop((x, y, x + width, y + height)).resize(CANVAS, Image.Resampling.LANCZOS)
    bitmap, anchor = normalize(reference, CANONICAL_CENTER)
    return reference, bitmap, anchor


def bounds_with_safe_inset(image: Image.Image) -> list[int]:
    left, top, right, bottom = ink_bounds(image)
    if left < SAFE_INSET_PX or top < SAFE_INSET_PX or right >= CANVAS[0] - SAFE_INSET_PX or bottom >= CANVAS[1] - SAFE_INSET_PX:
        raise ValueError("motion frame violates the four-pixel safe inset")
    return list(output_bounds(image))


def changed_pixels(first: Image.Image,
                   second: Image.Image,
                   regions: tuple[tuple[int, int, int, int], ...]) -> int:
    a = first.convert("1").load()
    b = second.convert("1").load()
    changes = 0
    for x, y, width, height in regions:
        for row in range(y, y + height):
            for column in range(x, x + width):
                changes += (a[column, row] == 0) != (b[column, row] == 0)
    return changes


def is_whole_frame_translation(first: Image.Image, second: Image.Image) -> bool:
    for offset_y in range(-4, 5):
        for offset_x in range(-4, 5):
            if translate(first, (offset_x, offset_y)).tobytes() == second.convert("1").tobytes():
                return True
    return False


def write_preview(frames: list[tuple[str, Image.Image]], output: pathlib.Path, title: str) -> None:
    cell_width = 260
    preview = Image.new("RGB", (cell_width * len(frames), 250), "white")
    draw = ImageDraw.Draw(preview)
    for index, (phase, frame) in enumerate(frames):
        x = index * cell_width
        thumbnail = frame.convert("RGB").resize((180, 180), Image.Resampling.NEAREST)
        preview.paste(thumbnail, (x + 40, 28))
        draw.rectangle((x + 40, 28, x + 219, 207), outline="black")
        draw.text((x + 90, 8), phase.upper(), fill="black")
        draw.text((x + 12, 220), title, fill="black")
    output.parent.mkdir(parents=True, exist_ok=True)
    preview.save(output)


def write_source_to_pbm_preview(
    frames: list[tuple[str, Image.Image, Image.Image]], output: pathlib.Path
) -> None:
    cell_width = 420
    preview = Image.new("RGB", (cell_width * len(frames), 250), "white")
    draw = ImageDraw.Draw(preview)
    for index, (phase, reference, bitmap) in enumerate(frames):
        x = index * cell_width
        source_thumb = reference.convert("RGB").resize((180, 180), Image.Resampling.LANCZOS)
        pbm_thumb = bitmap.convert("RGB").resize((180, 180), Image.Resampling.NEAREST)
        preview.paste(source_thumb, (x + 18, 36))
        preview.paste(pbm_thumb, (x + 222, 36))
        draw.rectangle((x + 18, 36, x + 197, 215), outline="black")
        draw.rectangle((x + 222, 36, x + 401, 215), outline="black")
        draw.text((x + 82, 10), f"{phase.upper()} SOURCE", fill="black")
        draw.text((x + 288, 10), "PBM", fill="black")
    output.parent.mkdir(parents=True, exist_ok=True)
    preview.save(output)


def render(layout: Layout, output_dir: pathlib.Path) -> dict[str, object]:
    source = Image.open(layout.source).convert("L")
    output_dir.mkdir(parents=True, exist_ok=True)
    pbm_dir = output_dir / "pbm"
    pbm_dir.mkdir(parents=True, exist_ok=True)
    frames: list[dict[str, object]] = []
    images: dict[str, Image.Image] = {}
    preview_frames: list[tuple[str, Image.Image]] = []
    comparison_frames: list[tuple[str, Image.Image, Image.Image]] = []
    for phase in layout.phases:
        reference, bitmap, anchor = to_pbm(source, phase)
        bounds = bounds_with_safe_inset(bitmap)
        output = pbm_dir / f"v9_motion_{phase.name}.pbm"
        bitmap.save(output)
        images[phase.name] = bitmap
        preview_frames.append((phase.name, bitmap))
        comparison_frames.append((phase.name, reference, bitmap))
        frames.append({
            "phase": phase.name,
            "source_crop_box": list(phase.crop_box),
            "path": repo_relative(output),
            "sha256": sha256(output),
            "anchor_policy": ANCHOR_POLICY,
            "source_anchor": list(anchor.source_anchor),
            "canonical_center": list(anchor.canonical_center),
            "normalization_offset": list(anchor.normalization_offset),
            "translation": [0, 0],
            "final_output_bounds": bounds,
        })

    if is_whole_frame_translation(images["entry"], images["sustain"]):
        raise ValueError("sustain is only a whole-frame translation of entry")
    feature_results = []
    eye_changed = False
    secondary_changed = False
    for feature in layout.features:
        delta = changed_pixels(images["entry"], images["sustain"], feature.regions)
        passed = delta >= feature.min_changed_pixels
        feature_results.append({
            "name": feature.name,
            "role": feature.role,
            "regions": [list(region) for region in feature.regions],
            "changed_pixels_entry_to_sustain": delta,
            "minimum_changed_pixels": feature.min_changed_pixels,
            "pass": passed,
        })
        eye_changed = eye_changed or (feature.role == "eye_highlight" and passed)
        secondary_changed = secondary_changed or (feature.role == "secondary" and passed)
    if not eye_changed or not secondary_changed:
        raise ValueError("sustain must change eyes/highlights and at least one secondary feature")

    manifest = {
        "schema": "companion.emote_asset_pack_manifest.v1",
        "name": "companion-v9-motion-extension-candidate-200x200",
        "revision": layout.revision,
        "priority": 0,
        "profile": {
            "width": 200,
            "height": 200,
            "stride_bytes": 25,
            "pixel_format": "mono_1bpp_white_is_one_msb",
        },
        "encoding": "packbits",
        "provenance": {
            "parent_source_sha256": layout.parent_source_sha256,
            "source": repo_relative(layout.source),
            "source_sha256": layout.source_sha256,
            "prompt_revision": layout.prompt_revision,
            "layout": repo_relative(layout.path),
            "runtime_resource_activated": False,
            "machine_only_candidate": True,
            "forbidden_inputs": ["legacy CEMP", "rejected art", "code-drawn face", "ball", "custom LUT"],
        },
        "clips": [{
            "name": "idle",
            "loop_start": 0,
            "loop_end": 3,
            "frames": [{
                "source": f"pbm/v9_motion_{frame['phase']}.pbm",
                "duration_ms": 3000,
                "dirty": frame["final_output_bounds"],
            } for frame in frames],
        }],
    }
    manifest_path = output_dir / "v9-motion-extension-cemp-manifest.json"
    manifest_path.write_text(json.dumps(manifest, indent=2) + "\n", encoding="ascii")
    pack, metadata = build_pack(manifest_path)
    pack_path = output_dir / "companion-v9-motion-extension-candidate-200x200.cemp"
    metadata_path = output_dir / "companion-v9-motion-extension-candidate-200x200.cemp.json"
    pack_path.write_bytes(pack)
    metadata_path.write_text(json.dumps(metadata, indent=2) + "\n", encoding="ascii")
    preview = output_dir / "v9-motion-extension-frame-contact-sheet.png"
    source_to_pbm_preview = output_dir / "v9-motion-extension-source-to-pbm.png"
    write_preview(preview_frames, preview, "200x200 PBM")
    write_source_to_pbm_preview(comparison_frames, source_to_pbm_preview)
    return {
        "schema": "companion.v9_motion_extension_render.v1",
        "status": "PASS_MACHINE_CANDIDATE_PENDING_OWNER_REVIEW",
        "layout": repo_relative(layout.path),
        "parent_source_sha256": layout.parent_source_sha256,
        "source": repo_relative(layout.source),
        "source_sha256": layout.source_sha256,
        "prompt_revision": layout.prompt_revision,
        "profile": {"width": 200, "height": 200, "safe_inset_px": SAFE_INSET_PX},
        "frames": frames,
        "feature_diffs": feature_results,
        "whole_frame_translation_only": False,
        "manifest": repo_relative(manifest_path),
        "pack": repo_relative(pack_path),
        "pack_sha256": sha256(pack_path),
        "metadata": repo_relative(metadata_path),
        "preview": repo_relative(preview),
        "source_to_pbm_preview": repo_relative(source_to_pbm_preview),
        "runtime_resource_activated": False,
        "external_flash_provisioned": False,
        "firmware_flashed": False,
        "owner_visual_pass": False,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--layout", type=pathlib.Path, required=True)
    parser.add_argument("--output-dir", type=pathlib.Path, required=True)
    parser.add_argument("--report", type=pathlib.Path, required=True)
    args = parser.parse_args()
    try:
        layout = load_layout(args.layout.resolve())
        report = render(layout, args.output_dir.resolve())
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        print(f"FAIL: {exc}")
        return 1
    args.report.parent.mkdir(parents=True, exist_ok=True)
    args.report.write_text(json.dumps(report, indent=2) + "\n", encoding="ascii")
    print("PASS: v9 daily-motion candidate passed source, feature, safe-area and deterministic CEMP checks.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
