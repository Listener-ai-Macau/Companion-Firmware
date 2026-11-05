#!/usr/bin/env python3
"""Export V34/V35 source art as inactive, source-addressable Rig masks.

This is intentionally an export step, not a runtime binding.  Every mask is
cropped from an already versioned generated source, then placed at the exact
native-200 coordinate used by its audited preview.  It never raster-draws a
face, an icon, or a replacement frame.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import shutil
import struct
import zlib
from collections import deque
from dataclasses import dataclass
from pathlib import Path

from PIL import Image


ROOT = Path(__file__).resolve().parents[1]
LOCKED_V9_SHA256 = "919F344957661DEF2099AD56AB1286CCA9DBA4D8F08B702617B6DF5B1A28E9DA"
V34_ROOT = ROOT / "docs/art/iterations/companion-pet-expression-v9-event-overlay-v1"
V35_ROOT = ROOT / "docs/art/iterations/companion-pet-expression-v9-emotion-decoration-kit-v1"
V34_SOURCES = {
    "recording_input": V34_ROOT / "candidate-recording-input-v1.png",
    "bottom_connector_charging": V34_ROOT / "candidate-bottom-connector-charging-v2.png",
}
V35_SOURCES = {
    "curious_question": V35_ROOT / "candidate-curious-question-v2.png",
    "alert_exclamation": V35_ROOT / "candidate-alert-exclamation-v2.png",
    "sleepy_dream_cloud": V35_ROOT / "candidate-sleepy-dream-cloud-v2.png",
}
DEFAULT_OUTPUT = ROOT / "docs/art/iterations/companion-pet-expression-v9-special-decoration-rig-v1/candidate"
DEFAULT_REPORT = ROOT / "docs/validation/companion-v34-v35-special-decoration-component-export-20260720.json"
CANVAS = (200, 200)
SAFE_INSET = 8
PACK_HEADER_BYTES = 80
PACK_INDEX_ENTRY_BYTES = 20
PACK_REVISION = 35


@dataclass(frozen=True)
class InkPart:
    area: int
    bbox: tuple[int, int, int, int]
    mask: Image.Image


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest().upper()


def rel(path: Path) -> str:
    return path.relative_to(ROOT).as_posix()


def binary_mask(image: Image.Image) -> Image.Image:
    return image.convert("L").point(lambda value: 255 if value < 128 else 0, mode="L")


def resize_mask(mask: Image.Image, size: tuple[int, int]) -> Image.Image:
    return mask.resize(size, Image.Resampling.LANCZOS).point(
        lambda value: 255 if value >= 128 else 0, mode="L")


def split_sheet(path: Path) -> list[Image.Image]:
    image = Image.open(path).convert("L")
    if image.width < 300:
        raise ValueError(f"{path} is not a three-cell generated source sheet")
    cell_width = image.width // 3
    return [image.crop((index * cell_width, 0,
                       (index + 1) * cell_width if index < 2 else image.width, image.height))
            for index in range(3)]


def connected_ink_parts(image: Image.Image) -> list[InkPart]:
    mask = binary_mask(image)
    width, height = mask.size
    pixels = mask.load()
    seen: set[tuple[int, int]] = set()
    parts: list[InkPart] = []
    for y in range(height):
        for x in range(width):
            if (x, y) in seen or pixels[x, y] == 0:
                continue
            pending: deque[tuple[int, int]] = deque([(x, y)])
            seen.add((x, y))
            points: list[tuple[int, int]] = []
            while pending:
                point_x, point_y = pending.pop()
                points.append((point_x, point_y))
                for next_x in (point_x - 1, point_x, point_x + 1):
                    for next_y in (point_y - 1, point_y, point_y + 1):
                        if (0 <= next_x < width and 0 <= next_y < height and
                                (next_x, next_y) not in seen and pixels[next_x, next_y] != 0):
                            seen.add((next_x, next_y))
                            pending.append((next_x, next_y))
            if len(points) < 64:
                continue
            min_x = min(point[0] for point in points)
            min_y = min(point[1] for point in points)
            max_x = max(point[0] for point in points) + 1
            max_y = max(point[1] for point in points) + 1
            part = Image.new("L", (max_x - min_x, max_y - min_y), 0)
            part_pixels = part.load()
            for point_x, point_y in points:
                part_pixels[point_x - min_x, point_y - min_y] = 255
            parts.append(InkPart(len(points), (min_x, min_y, max_x, max_y), part))
    return sorted(parts, key=lambda item: item.area, reverse=True)


def bottom_connector_mask(cell: Image.Image) -> tuple[Image.Image, tuple[int, int, int, int]]:
    """Select only the generated underside connector, excluding its long guide line."""
    mask = binary_mask(cell)
    bbox = mask.getbbox()
    if bbox is None:
        raise ValueError("bottom-connector source cell is empty")
    center_x = cell.width // 2
    crop_left = center_x - 50
    crop_top = bbox[1] + 55
    crop = mask.crop((crop_left, crop_top, center_x + 50, bbox[3]))
    crop_bbox = crop.getbbox()
    if crop_bbox is None:
        raise ValueError("bottom-connector source crop is empty")
    absolute = (crop_left + crop_bbox[0], crop_top + crop_bbox[1],
                crop_left + crop_bbox[2], crop_top + crop_bbox[3])
    return crop.crop(crop_bbox), absolute


def make_component(name: str, component_id: int, event: str, source: Path, source_cell: int,
                   extraction: dict[str, object], mask: Image.Image, position: tuple[int, int],
                   output_dir: Path, z_index: int = 90) -> dict[str, object]:
    x, y = position
    if x < SAFE_INSET or y < SAFE_INSET or x + mask.width > CANVAS[0] - SAFE_INSET or y + mask.height > CANVAS[1] - SAFE_INSET:
        raise ValueError(f"{name} leaves the {SAFE_INSET}px candidate safe inset")
    if sum(1 for value in mask.getdata() if value) == 0:
        raise ValueError(f"{name} has no generated source ink")
    mask_path = output_dir / "component-masks" / f"{name}.pbm"
    preview_path = output_dir / "preview-masks" / f"{name}.png"
    mask_path.parent.mkdir(parents=True, exist_ok=True)
    preview_path.parent.mkdir(parents=True, exist_ok=True)
    mono = Image.new("1", mask.size, 1)
    mono.paste(0, (0, 0), mask)
    mono.save(mask_path)
    mono.save(preview_path)
    return {
        "name": name,
        "component_id": component_id,
        "event": event,
        "source": {"path": rel(source), "sha256": sha256(source), "cell": source_cell,
                   "extraction": extraction},
        "mask": rel(mask_path),
        "preview_mask": rel(preview_path),
        "mask_sha256": sha256(mask_path),
        "base_position": [x, y],
        "mask_size": [mask.width, mask.height],
        "offset_range": {"min": [0, 0], "max": [0, 0]},
        "z_index": z_index,
        "composite_op": "ink",
        "ink_pixels": sum(1 for value in mask.getdata() if value),
    }


def render_overlay(components: list[dict[str, object]], names: list[str]) -> Image.Image:
    component_by_name = {str(component["name"]): component for component in components}
    canvas = Image.new("1", CANVAS, 1)
    for name in names:
        component = component_by_name[name]
        mask = Image.open(ROOT / str(component["mask"])).convert("1")
        x, y = component["base_position"]
        canvas.paste(0, (x, y), binary_mask(mask))
    return canvas


def save_overlay(output_dir: Path, event: str, frame: int, image: Image.Image) -> dict[str, object]:
    path = output_dir / "reassembled-overlays" / f"{event}-{frame:02d}.pbm"
    path.parent.mkdir(parents=True, exist_ok=True)
    image.save(path)
    return {"frame": frame, "overlay_pbm": rel(path), "overlay_sha256": sha256(path)}


def build_v34_components(output_dir: Path, components: list[dict[str, object]], next_id: int) -> tuple[dict[str, object], int]:
    recordings: list[dict[str, object]] = []
    recording_cells = split_sheet(V34_SOURCES["recording_input"])
    for frame, cell in enumerate(recording_cells):
        parts = connected_ink_parts(cell)
        if not parts:
            raise ValueError(f"recording source cell {frame} is empty")
        names: list[str] = []
        mic_name = f"v34_recording_mic_{frame}"
        components.append(make_component(mic_name, next_id, "recording_input", V34_SOURCES["recording_input"], frame,
                                         {"kind": "connected_component", "rank": 0, "source_bbox": list(parts[0].bbox),
                                          "resize": [9, 19]}, resize_mask(parts[0].mask, (9, 19)), (182, 127), output_dir, z_index=10))
        next_id += 1
        names.append(mic_name)
        if frame == 1:
            name = "v34_recording_inward_pulse_1"
            components.append(make_component(name, next_id, "recording_input", V34_SOURCES["recording_input"], frame,
                                             {"kind": "connected_component", "rank": 1, "source_bbox": list(parts[1].bbox),
                                              "resize": [4, 12]}, resize_mask(parts[1].mask, (4, 12)), (168, 130), output_dir, z_index=10))
            next_id += 1
            names.append(name)
        if frame == 2:
            arcs = sorted(parts[1:], key=lambda item: item.bbox[0])
            if len(arcs) < 2:
                raise ValueError("recording source cell 2 must expose at least two capture-pulse components")
            for index, (arc, size, position) in enumerate(((arcs[0], (4, 12), (163, 130)),
                                                            (arcs[1], (5, 18), (170, 127)))):
                name = f"v34_recording_inward_pulse_2_{index}"
                components.append(make_component(name, next_id, "recording_input", V34_SOURCES["recording_input"], frame,
                                                 {"kind": "connected_component", "rank_after_sort_by_left": index + 1,
                                                  "source_bbox": list(arc.bbox), "resize": list(size)},
                                                 resize_mask(arc.mask, size), position, output_dir, z_index=10))
                next_id += 1
                names.append(name)
        recordings.append({"frame": frame, "duration_ms": [700, 420, 420][frame], "components": names})

    charging: list[dict[str, object]] = []
    charging_cells = split_sheet(V34_SOURCES["bottom_connector_charging"])
    for frame, cell in enumerate(charging_cells):
        parts = connected_ink_parts(cell)
        if not parts:
            raise ValueError(f"charging source cell {frame} is empty")
        connector, connector_bbox = bottom_connector_mask(cell)
        names: list[str] = []
        name = f"v34_bottom_connector_{frame}"
        components.append(make_component(name, next_id, "bottom_connector_charging", V34_SOURCES["bottom_connector_charging"], frame,
                                         {"kind": "underside_crop", "source_bbox": list(connector_bbox), "resize": [42, 20]},
                                         resize_mask(connector, (42, 20)), (79, 172), output_dir, z_index=10))
        next_id += 1
        names.append(name)
        if frame == 1:
            name = "v34_charging_pulse_1"
            components.append(make_component(name, next_id, "bottom_connector_charging", V34_SOURCES["bottom_connector_charging"], frame,
                                             {"kind": "connected_component", "rank": 1, "source_bbox": list(parts[1].bbox),
                                              "resize": [8, 3]}, resize_mask(parts[1].mask, (8, 3)), (96, 168), output_dir, z_index=10))
            next_id += 1
            names.append(name)
        if frame == 2:
            arcs = sorted(parts[1:], key=lambda item: item.area, reverse=True)
            if len(arcs) < 2:
                raise ValueError("charging source cell 2 must expose at least two energy-pulse components")
            for index, (arc, size, position) in enumerate(((arcs[0], (16, 4), (92, 163)),
                                                            (arcs[1], (10, 3), (95, 168)))):
                name = f"v34_charging_pulse_2_{index}"
                components.append(make_component(name, next_id, "bottom_connector_charging", V34_SOURCES["bottom_connector_charging"], frame,
                                                 {"kind": "connected_component", "rank_after_sort_by_area": index + 1,
                                                  "source_bbox": list(arc.bbox), "resize": list(size)},
                                                 resize_mask(arc.mask, size), position, output_dir, z_index=10))
                next_id += 1
                names.append(name)
        charging.append({"frame": frame, "duration_ms": [700, 420, 420][frame], "components": names})
    return {"recording_input": {"activity": recordings},
            "bottom_connector_charging": {"activity": charging}}, next_id


V35_PLACEMENTS = {
    "curious_question": {"entry": [(148, 38, 14, 20), (145, 34, 17, 24), (142, 29, 20, 28)],
                         "presence": [(142, 29, 20, 28), (143, 31, 19, 27), (145, 34, 17, 24),
                                      (145, 34, 17, 24), (143, 31, 19, 27), (142, 29, 20, 28)]},
    "alert_exclamation": {"entry": [(99, 42, 7, 18), (96, 35, 10, 26), (94, 25, 13, 34)],
                          "presence": [(94, 25, 13, 34), (95, 28, 12, 31), (96, 35, 10, 26),
                                       (96, 35, 10, 26), (95, 28, 12, 31), (94, 25, 13, 34)]},
    "sleepy_dream_cloud": {"entry": [(40, 41, 23, 16), (33, 35, 30, 22), (27, 30, 38, 27)],
                            "presence": [(27, 30, 38, 27), (29, 32, 36, 26), (33, 35, 30, 22),
                                         (33, 35, 30, 22), (29, 32, 36, 26), (27, 30, 38, 27)]},
}


def build_v35_components(output_dir: Path, components: list[dict[str, object]], next_id: int) -> tuple[dict[str, object], int]:
    scores: dict[str, object] = {}
    for event, source in V35_SOURCES.items():
        cells = split_sheet(source)
        placements = V35_PLACEMENTS[event]
        source_components: list[str] = []
        for index, cell in enumerate(cells):
            mask = binary_mask(cell)
            bbox = mask.getbbox()
            if bbox is None:
                raise ValueError(f"{event} source cell {index} is empty")
            entry_x, entry_y, entry_width, entry_height = placements["entry"][index]
            name = f"v35_{event}_{index}"
            components.append(make_component(name, next_id, event, source, index,
                                             {"kind": "cell_ink_bbox", "source_bbox": list(bbox),
                                              "resize": [entry_width, entry_height]},
                                             resize_mask(mask.crop(bbox), (entry_width, entry_height)),
                                             (entry_x, entry_y), output_dir))
            next_id += 1
            source_components.append(name)
        presence: list[dict[str, object]] = []
        for frame, placement in enumerate(placements["presence"]):
            source_index = 2 if frame in {0, 5} else 1
            x, y, width, height = placement
            source_mask = binary_mask(cells[source_index])
            source_bbox = source_mask.getbbox()
            if source_bbox is None:
                raise ValueError(f"{event} source cell {source_index} is empty")
            name = f"v35_{event}_presence_{frame}"
            components.append(make_component(name, next_id, event, source, source_index,
                                             {"kind": "cell_ink_bbox", "source_bbox": list(source_bbox),
                                              "resize": [width, height]},
                                             resize_mask(source_mask.crop(source_bbox), (width, height)), (x, y), output_dir))
            next_id += 1
            presence.append({"frame": frame, "duration_ms": [900, 150, 150, 170, 190, 1100][frame],
                             "components": [name]})
        scores[event] = {
            "entry": [{"frame": index, "duration_ms": [160, 240, 960][index], "components": [name]}
                      for index, name in enumerate(source_components)],
            "presence": presence,
        }
    return scores, next_id


def build_pack(output_dir: Path, components: list[dict[str, object]]) -> dict[str, object]:
    index = bytearray()
    payload = bytearray()
    records: list[dict[str, object]] = []
    data_offset = PACK_HEADER_BYTES + PACK_INDEX_ENTRY_BYTES * len(components)
    for component in components:
        image = Image.open(ROOT / str(component["mask"])).convert("1")
        width, height = image.size
        stride = (width + 7) // 8
        data = image.tobytes()
        if len(data) != stride * height:
            raise ValueError(f"invalid PBM stride for {component['name']}")
        offset = data_offset + len(payload)
        crc = zlib.crc32(data) & 0xFFFFFFFF
        index.extend(struct.pack("<HHHHIII", int(component["component_id"]), width, height, stride,
                                 offset, len(data), crc))
        payload.extend(data)
        records.append({"component_id": component["component_id"], "name": component["name"], "width": width,
                        "height": height, "stride_bytes": stride, "data_offset": offset, "data_size": len(data),
                        "data_crc32": f"{crc:08X}"})
    header = bytearray(PACK_HEADER_BYTES)
    total_size = data_offset + len(payload)
    header[0:4] = b"CRIG"
    struct.pack_into("<H", header, 4, 1)
    struct.pack_into("<H", header, 6, PACK_HEADER_BYTES)
    struct.pack_into("<I", header, 8, total_size)
    struct.pack_into("<I", header, 12, PACK_REVISION)
    struct.pack_into("<H", header, 16, CANVAS[0])
    struct.pack_into("<H", header, 18, CANVAS[1])
    struct.pack_into("<H", header, 20, 25)
    header[22] = 1
    header[23] = SAFE_INSET
    struct.pack_into("<H", header, 24, len(components))
    struct.pack_into("<I", header, 28, PACK_HEADER_BYTES)
    struct.pack_into("<I", header, 32, data_offset)
    struct.pack_into("<I", header, 36, zlib.crc32(payload) & 0xFFFFFFFF)
    struct.pack_into("<I", header, 40, zlib.crc32(index) & 0xFFFFFFFF)
    header[44:76] = bytes.fromhex(LOCKED_V9_SHA256)
    pack = output_dir / "companion-v9-special-decoration-rig-candidate-200x200.crig"
    pack.write_bytes(bytes(header) + bytes(index) + bytes(payload))
    return {"path": rel(pack), "sha256": sha256(pack), "total_size": total_size,
            "revision": PACK_REVISION, "component_count": len(components), "components": records}


def build_artifacts(output_dir: Path) -> dict[str, object]:
    if output_dir.exists():
        shutil.rmtree(output_dir)
    output_dir.mkdir(parents=True)
    for source in [*V34_SOURCES.values(), *V35_SOURCES.values()]:
        if not source.is_file():
            raise ValueError(f"missing versioned generated source: {source}")
    components: list[dict[str, object]] = []
    v34_scores, next_id = build_v34_components(output_dir, components, 500)
    v35_scores, next_id = build_v35_components(output_dir, components, next_id)
    del next_id
    score_sets = {**v34_scores, **v35_scores}
    reassembled: dict[str, list[dict[str, object]]] = {}
    for event, phases in score_sets.items():
        records: list[dict[str, object]] = []
        for phase_name, frames in phases.items():
            for frame in frames:
                image = render_overlay(components, list(frame["components"]))
                record = save_overlay(output_dir, f"{event}-{phase_name}", int(frame["frame"]), image)
                records.append({"phase": phase_name, **frame, **record})
        reassembled[event] = records
    pack = build_pack(output_dir, components)
    layout = {
        "schema": "companion.v34_v35_special_decoration_component_layout.v1",
        "status": "CANDIDATE_COMPONENT_EXPORT_MACHINE_PENDING",
        "authority": ["COMP-REQ-187", "COMP-REQ-189", "COMP-REQ-190", "COMP-REQ-198", "COMP-REQ-229"],
        "locked_v9_source_sha256": LOCKED_V9_SHA256,
        "runtime_resource_activated": False,
        "active_candidate_binding": "forbidden",
        "component_export_scope": "source-derived special decorations only; no face component, no full-frame card",
        "sources": {name: {"path": rel(path), "sha256": sha256(path)}
                    for name, path in {**V34_SOURCES, **V35_SOURCES}.items()},
        "components": components,
        "scores": score_sets,
        "reassembled_overlays": reassembled,
        "pack": pack,
        "non_claims": ["no_special_event_runtime_binding", "no_firmware_flash", "no_panel_or_driver_change",
                       "no_owner_art_acceptance", "no_full_face_card"],
    }
    layout_path = output_dir / "special-decoration-component-layout.json"
    layout_path.write_text(json.dumps(layout, indent=2) + "\n", encoding="utf-8")
    return {"layout": rel(layout_path), "layout_sha256": sha256(layout_path), **layout}


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output-dir", default=str(DEFAULT_OUTPUT.relative_to(ROOT)))
    parser.add_argument("--report", default=str(DEFAULT_REPORT.relative_to(ROOT)))
    parser.add_argument("--check", action="store_true", help="rebuild in a temporary sibling and compare deterministic outputs")
    args = parser.parse_args()
    output_dir = (ROOT / args.output_dir).resolve()
    report_path = (ROOT / args.report).resolve()
    if args.check:
        temporary = output_dir.with_name(output_dir.name + "-check")
        built = build_artifacts(temporary)
        if not output_dir.is_dir():
            raise ValueError("cannot check before the candidate export exists")
        for path in temporary.rglob("*"):
            if path.is_file():
                expected = output_dir / path.relative_to(temporary)
                if not expected.is_file():
                    raise ValueError(f"non-deterministic special-decoration export: {path.relative_to(temporary)}")
                if path.name == "special-decoration-component-layout.json":
                    observed_text = path.read_text(encoding="utf-8").replace(rel(temporary), rel(output_dir))
                    if observed_text != expected.read_text(encoding="utf-8"):
                        raise ValueError(f"non-deterministic special-decoration layout: {path.relative_to(temporary)}")
                elif sha256(path) != sha256(expected):
                    raise ValueError(f"non-deterministic special-decoration export: {path.relative_to(temporary)}")
        shutil.rmtree(temporary)
        print(json.dumps({"status": "PASS_DETERMINISTIC_SPECIAL_DECORATION_EXPORT", "layout": built["layout"]}, indent=2))
        return 0
    built = build_artifacts(output_dir)
    report = {
        "schema": "companion.v34_v35_special_decoration_component_export.v1",
        "status": "CANDIDATE_COMPONENT_EXPORT_MACHINE_PENDING",
        "layout": built["layout"],
        "layout_sha256": built["layout_sha256"],
        "pack": built["pack"],
        "runtime_resource_activated": False,
        "active_candidate_binding": "forbidden",
        "non_claims": built["non_claims"],
    }
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(report, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
