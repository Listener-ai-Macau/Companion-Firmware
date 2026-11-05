#!/usr/bin/env python3
"""Machine gate for the inactive V34/V35 source-decoration component export."""

from __future__ import annotations

import argparse
import hashlib
import json
import struct
import sys
import zlib
from pathlib import Path

from PIL import Image


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))
from render_companion_v35_emotion_decoration_preview_v2 import (  # noqa: E402
    EVENTS as V35_EVENTS,
    PRESENCE_STAGES,
    SOURCES as V35_SOURCES,
    STAGE_CHANNELS,
    TRANSITION_STAGES,
    RIG_LAYOUT,
    load_rig,
    render_stage,
)


LOCKED_V9_SHA256 = "919F344957661DEF2099AD56AB1286CCA9DBA4D8F08B702617B6DF5B1A28E9DA"
V34_PRIMARY_FACE_BOXES = ((42, 112, 33, 45), (125, 112, 34, 45), (47, 85, 23, 12),
                          (132, 85, 23, 12), (94, 148, 13, 8), (86, 160, 29, 10))
LAYOUT = ROOT / "docs/art/iterations/companion-pet-expression-v9-special-decoration-rig-v1/candidate/special-decoration-component-layout.json"
EXPORT_REPORT = ROOT / "docs/validation/companion-v34-v35-special-decoration-component-export-20260720.json"
V34_RENDER = ROOT / "docs/validation/companion-v34-event-overlay-native-200-render-20260720.json"
V35_RENDER = ROOT / "docs/validation/companion-v35-emotion-decoration-native-200-v3-total-audit-render-20260720.json"


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest().upper()


def rel(path: Path) -> str:
    return path.relative_to(ROOT).as_posix()


def image_200(path: Path) -> Image.Image:
    image = Image.open(path).convert("1")
    if image.size != (200, 200):
        raise ValueError(f"{path} is not native 200x200")
    return image


def binary_mask(image: Image.Image) -> Image.Image:
    return image.convert("L").point(lambda value: 255 if value < 128 else 0, mode="L")


def added_ink(base: Image.Image, composite: Image.Image) -> Image.Image:
    result = Image.new("1", (200, 200), 1)
    base_pixels = base.load()
    composite_pixels = composite.load()
    result_pixels = result.load()
    for y in range(200):
        for x in range(200):
            if base_pixels[x, y] == 0 and composite_pixels[x, y] != 0:
                raise ValueError("candidate decoration erased a base face pixel")
            if base_pixels[x, y] != 0 and composite_pixels[x, y] == 0:
                result_pixels[x, y] = 0
    return result


def compare(image: Image.Image, expected: Image.Image, message: str) -> None:
    if image.convert("1").tobytes() != expected.convert("1").tobytes():
        raise ValueError(message)


def compose_overlay(base: Image.Image, overlay: Image.Image, restore_primary_face: bool = False) -> Image.Image:
    composite = base.copy()
    composite.paste(0, (0, 0), binary_mask(overlay))
    if restore_primary_face:
        for x, y, width, height in V34_PRIMARY_FACE_BOXES:
            composite.paste(base.crop((x, y, x + width, y + height)), (x, y))
    return composite


def verify_pack(layout: dict[str, object]) -> dict[str, object]:
    pack_info = layout.get("pack")
    components = layout.get("components")
    if not isinstance(pack_info, dict) or not isinstance(components, list):
        raise ValueError("special-decoration layout lacks pack/component metadata")
    pack = ROOT / str(pack_info.get("path"))
    data = pack.read_bytes()
    if len(data) < 80 or data[0:4] != b"CRIG":
        raise ValueError("special-decoration pack magic is invalid")
    version, header_size = struct.unpack_from("<HH", data, 4)
    total_size, revision = struct.unpack_from("<II", data, 8)
    width, height, stride = struct.unpack_from("<HHH", data, 16)
    component_count = struct.unpack_from("<H", data, 24)[0]
    index_offset, data_offset, payload_crc, index_crc = struct.unpack_from("<IIII", data, 28)
    if (version, header_size, total_size, revision, width, height, stride, component_count, index_offset) != (
            1, 80, len(data), 35, 200, 200, 25, len(components), 80):
        raise ValueError("special-decoration CRIG header drifted")
    if data[23] != 8 or data[44:76].hex().upper() != LOCKED_V9_SHA256:
        raise ValueError("special-decoration CRIG identity/safe inset drifted")
    index_size = component_count * 20
    if data_offset != index_offset + index_size or zlib.crc32(data[index_offset:data_offset]) & 0xFFFFFFFF != index_crc:
        raise ValueError("special-decoration CRIG index CRC/layout drifted")
    if zlib.crc32(data[data_offset:]) & 0xFFFFFFFF != payload_crc:
        raise ValueError("special-decoration CRIG payload CRC drifted")
    expected_components = {int(component["component_id"]): component for component in components}
    seen: set[int] = set()
    for index in range(component_count):
        offset = index_offset + index * 20
        component_id, mask_width, mask_height, mask_stride, component_offset, component_size, component_crc = struct.unpack_from(
            "<HHHHIII", data, offset)
        component = expected_components.get(component_id)
        if component is None or component_id in seen:
            raise ValueError("special-decoration CRIG has an unknown or duplicate component id")
        seen.add(component_id)
        if (mask_width, mask_height, mask_stride) != (*component["mask_size"], (component["mask_size"][0] + 7) // 8):
            raise ValueError(f"special-decoration CRIG dimensions drifted: {component['name']}")
        payload = data[component_offset:component_offset + component_size]
        expected = Image.open(ROOT / str(component["mask"])).convert("1").tobytes()
        if len(payload) != len(expected) or payload != expected or zlib.crc32(payload) & 0xFFFFFFFF != component_crc:
            raise ValueError(f"special-decoration CRIG payload differs from source component: {component['name']}")
    if seen != set(expected_components):
        raise ValueError("special-decoration CRIG component coverage is incomplete")
    return {"path": rel(pack), "sha256": sha256(pack), "component_count": component_count,
            "payload_crc32": f"{payload_crc:08X}", "index_crc32": f"{index_crc:08X}"}


def overlay_from_layout(layout: dict[str, object], event: str, phase: str, frame: int) -> Image.Image:
    entries = layout.get("reassembled_overlays", {}).get(event)
    if not isinstance(entries, list):
        raise ValueError(f"missing reassembled overlay evidence for {event}")
    for entry in entries:
        if entry.get("phase") == phase and entry.get("frame") == frame:
            path = ROOT / str(entry["overlay_pbm"])
            if sha256(path) != entry["overlay_sha256"]:
                raise ValueError(f"overlay hash drifted: {event}/{phase}/{frame}")
            return image_200(path)
    raise ValueError(f"missing reassembled overlay frame: {event}/{phase}/{frame}")


def verify_component_lineage(layout: dict[str, object]) -> list[dict[str, object]]:
    components = layout.get("components")
    if not isinstance(components, list) or not components:
        raise ValueError("layout has no components")
    results = []
    for component in components:
        source = component.get("source")
        if not isinstance(source, dict):
            raise ValueError("component source metadata is missing")
        source_path = ROOT / str(source.get("path"))
        mask_path = ROOT / str(component.get("mask"))
        position = component.get("base_position")
        size = component.get("mask_size")
        if (not source_path.is_file() or sha256(source_path) != source.get("sha256") or
                not mask_path.is_file() or sha256(mask_path) != component.get("mask_sha256") or
                not isinstance(position, list) or not isinstance(size, list) or len(position) != 2 or len(size) != 2):
            raise ValueError(f"component lineage drifted: {component.get('name')}")
        x, y = position
        width, height = size
        if x < 8 or y < 8 or x + width > 192 or y + height > 192:
            raise ValueError(f"component escapes safe inset: {component.get('name')}")
        if component.get("composite_op") != "ink" or component.get("event") not in {
                "recording_input", "bottom_connector_charging", "curious_question", "alert_exclamation", "sleepy_dream_cloud"}:
            raise ValueError(f"unregistered decoration component: {component.get('name')}")
        results.append({"component_id": component["component_id"], "name": component["name"],
                        "source_sha256": source["sha256"], "mask_sha256": component["mask_sha256"]})
    return results


def verify_v34(layout: dict[str, object]) -> dict[str, object]:
    render = json.loads(V34_RENDER.read_text(encoding="utf-8"))
    records: dict[str, object] = {}
    for event, phase in (("recording_input", "activity"), ("bottom_connector_charging", "activity")):
        event_data = render.get("overlays", {}).get(event)
        if not isinstance(event_data, dict):
            raise ValueError(f"V34 render is missing {event}")
        output = []
        for frame, frame_data in enumerate(event_data.get("frames", [])):
            daily_name = event_data["daily_micro_sequence"][frame]
            base = image_200(ROOT / render["daily_micro_bases"][daily_name]["path"])
            preview = image_200(ROOT / frame_data["png"])
            actual = overlay_from_layout(layout, event, phase, frame)
            compare(compose_overlay(base, actual, restore_primary_face=True), preview,
                    f"V34 component export does not reconstruct native preview frame: {event}/{frame}")
            output.append({"frame": frame, "overlay_pixels": sum(1 for pixel in actual.getdata() if pixel == 0)})
        records[event] = output
    return records


def verify_v35(layout: dict[str, object]) -> dict[str, object]:
    render = json.loads(V35_RENDER.read_text(encoding="utf-8"))
    rig = load_rig(RIG_LAYOUT)
    source_images = {name: Image.open(source.path).convert("1") for name, source in rig.sources.items()}
    results: dict[str, object] = {}
    for event, definition in V35_EVENTS.items():
        event_data = render.get("events", {}).get(event)
        if not isinstance(event_data, dict):
            raise ValueError(f"V35 render is missing {event}")
        transition = event_data.get("transition")
        presence = event_data.get("presence")
        if not isinstance(transition, list) or not isinstance(presence, list):
            raise ValueError(f"V35 render phases malformed for {event}")
        entry_records = []
        for source_index, stage_index in enumerate((6, 7, 8)):
            stage = TRANSITION_STAGES[stage_index]
            base, _ = render_stage(rig, source_images, definition["source_state"], definition["target_state"], stage,
                                   definition["mouth_extra"] if stage == "mouth_cheek_reply" else (0, 0))
            full = image_200(ROOT / transition[stage_index]["png"])
            actual = overlay_from_layout(layout, event, "entry", source_index)
            compare(compose_overlay(base, actual), full,
                    f"V35 entry export does not reconstruct native preview frame: {event}/{source_index}")
            entry_records.append({"frame": source_index, "overlay_pixels": sum(1 for pixel in actual.getdata() if pixel == 0)})
        presence_records = []
        for frame, stage in enumerate(PRESENCE_STAGES):
            base, _ = render_stage(rig, source_images, definition["target_state"], definition["micro_state"], stage,
                                   definition["mouth_extra"] if stage == "mouth_cheek_reply" else (0, 0))
            full = image_200(ROOT / presence[frame]["png"])
            actual = overlay_from_layout(layout, event, "presence", frame)
            compare(compose_overlay(base, actual), full,
                    f"V35 presence export does not reconstruct native preview frame: {event}/{frame}")
            presence_records.append({"frame": frame, "overlay_pixels": sum(1 for pixel in actual.getdata() if pixel == 0)})
        results[event] = {"entry": entry_records, "presence": presence_records}
    return results


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--layout", default=rel(LAYOUT))
    parser.add_argument("--write", default="docs/validation/companion-v34-v35-special-decoration-component-export-gate-20260720.json")
    args = parser.parse_args()
    layout_path = (ROOT / args.layout).resolve()
    layout = json.loads(layout_path.read_text(encoding="utf-8"))
    if (layout.get("status") != "CANDIDATE_COMPONENT_EXPORT_MACHINE_PENDING" or
            layout.get("locked_v9_source_sha256") != LOCKED_V9_SHA256 or
            layout.get("runtime_resource_activated") is not False or
            layout.get("active_candidate_binding") != "forbidden"):
        raise ValueError("special-decoration layout is not an inactive locked-V9 candidate")
    output = {
        "schema": "companion.v34_v35_special_decoration_component_export_gate.v1",
        "status": "PASS_COMPONENT_EXPORT_RUNTIME_INACTIVE",
        "authority": ["COMP-REQ-187", "COMP-REQ-189", "COMP-REQ-190", "COMP-REQ-198", "COMP-REQ-229", "COMP-REQ-230"],
        "layout": rel(layout_path),
        "layout_sha256": sha256(layout_path),
        "component_lineage": verify_component_lineage(layout),
        "crig": verify_pack(layout),
        "v34_native_preview_overlay_parity": verify_v34(layout),
        "v35_native_preview_overlay_parity": verify_v35(layout),
        "runtime": {"resource_activated": False, "active_candidate_binding": "forbidden",
                    "special_event_binding": "forbidden_until_later_browser_target_component_plan_gate"},
        "non_claims": ["no_special_event_runtime_binding", "no_firmware_flash", "no_panel_or_driver_change",
                       "no_owner_art_acceptance", "no_full_face_card"],
    }
    path = (ROOT / args.write).resolve()
    path.write_text(json.dumps(output, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(output, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
