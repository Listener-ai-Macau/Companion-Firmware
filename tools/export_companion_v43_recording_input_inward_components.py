#!/usr/bin/env python3
"""Export the inactive V43 special-component CRIG with inward recording input art."""

from __future__ import annotations

import argparse
import hashlib
import json
import shutil
import struct
import tempfile
import zlib
from pathlib import Path
from typing import Any

from PIL import Image


ROOT = Path(__file__).resolve().parents[1]
LOCKED = "919F344957661DEF2099AD56AB1286CCA9DBA4D8F08B702617B6DF5B1A28E9DA"
V40_LAYOUT = ROOT / "docs/art/iterations/companion-pet-expression-v9-functional-decoration-rig-v2/candidate/functional-decoration-component-layout.json"
FUNCTIONAL_REQUEST = ROOT / "docs/art/iterations/companion-pet-expression-v9-extension-v42-functional-ornament-source/generation-request-v1.json"
FUNCTIONAL_SOURCE = ROOT / "docs/art/iterations/companion-pet-expression-v9-extension-v42-functional-ornament-source/candidate/attempt-01-functional-ornaments.png"
RECORDING_REQUEST = ROOT / "docs/art/iterations/companion-pet-expression-v9-recording-input-inward-source-v1/generation-request-v1.json"
RECORDING_SOURCE = ROOT / "docs/art/iterations/companion-pet-expression-v9-recording-input-inward-source-v1/candidate/attempt-01-recording-input-inward.png"
CHARGING_REQUEST = ROOT / "docs/art/iterations/companion-pet-expression-v9-extension-v42-functional-ornament-source/generation-request-v2.json"
CHARGING_SOURCE = ROOT / "docs/art/iterations/companion-pet-expression-v9-extension-v42-functional-ornament-source/candidate/attempt-02-wireless-charging-cradles.png"
EMOTION_REQUEST = ROOT / "docs/art/iterations/companion-pet-expression-v9-extension-v42-emotion-source/generation-request-v2.json"
EMOTION_SOURCE = ROOT / "docs/art/iterations/companion-pet-expression-v9-extension-v42-emotion-source/candidate/attempt-02-emotion-source.png"
LOWER_FACE_REQUEST = ROOT / "docs/art/iterations/companion-pet-expression-v9-extension-v42-emotion-source/generation-request-v5.json"
LOWER_FACE_SOURCE = ROOT / "docs/art/iterations/companion-pet-expression-v9-extension-v42-emotion-source/candidate/attempt-05-lower-face-source.png"
THOUGHTFUL_MOUTH_REQUEST = ROOT / "docs/art/iterations/companion-pet-expression-v9-extension-v42-emotion-source/generation-request-v7.json"
THOUGHTFUL_MOUTH_SOURCE = ROOT / "docs/art/iterations/companion-pet-expression-v9-extension-v42-emotion-source/candidate/attempt-07-thoughtful-mouth-source.png"
DELIGHTED_MOUTH_REQUEST = ROOT / "docs/art/iterations/companion-pet-expression-v9-extension-v42-emotion-source/generation-request-v12.json"
DELIGHTED_MOUTH_SOURCE = ROOT / "docs/art/iterations/companion-pet-expression-v9-extension-v42-emotion-source/candidate/attempt-12-delighted-mouth-source.png"
BASHFUL_REQUEST = ROOT / "docs/art/iterations/companion-pet-expression-v9-extension-v42-emotion-source/generation-request-v3.json"
BASHFUL_SOURCE = ROOT / "docs/art/iterations/companion-pet-expression-v9-extension-v42-emotion-source/candidate/attempt-03-bashful-source.png"
SLEEP_REQUEST = ROOT / "docs/art/iterations/companion-pet-expression-v9-extension-v42-sleep-zzz-source/generation-request-v1.json"
SLEEP_SOURCE = ROOT / "docs/art/iterations/companion-pet-expression-v9-extension-v42-sleep-zzz-source/candidate/attempt-01-sleep-zzz-source.png"
OUTPUT = ROOT / "docs/art/iterations/companion-pet-expression-v9-two-track-rig-v5/candidate"

CANVAS = (200, 200)
SAFE_INSET = 4
REVISION = 43
HEADER_BYTES = 80
INDEX_BYTES = 20

FUNCTIONAL_SHA = "508FC5A5D8B89F1769903062F6EAE93DCCFF013BB8340366F53D9DC6EF7CFEB7"
RECORDING_SHA = "278AE1ED5EED32F80CA09ACAD8C6F3112156ABCFB3653A5DAD3270C30FDFB4B7"
CHARGING_SHA = "4F58D263EA9E71A6C31C2C969D6FD615BBA5672023BDC08B4FC6B3A6B2BDD7FA"
EMOTION_SHA = "CE77807B4053C808D9E111CE38B8806735F56EA29DFCE2ECA807FD95964F5A03"
LOWER_FACE_SHA = "AD89593250DDAB09816AD38B8B46509ADD48726499765A5BFB6D724942C40E9B"
THOUGHTFUL_MOUTH_SHA = "1D76B69F92ED5ABD6BACA877A90F6C6FDD76A62B1EC06B6D726264A6F9FA0C67"
DELIGHTED_MOUTH_SHA = "E293FC2640A4E650DC37DC857930CA6C563A52ABBF560C0D5163FA7B66B3B5AB"
DELIGHTED_MOUTH_BOX = [551, 862, 157, 78]
DELIGHTED_MOUTH_SCALE = 0.16
BASHFUL_SHA = "6088781812BFC1F908B35876B74356D71CEDDCF93288FFF61F65163F57A0F073"
SLEEP_SHA = "C9BEC982411D22CA0031FA28F12950E27F098D09AFF626BAF0A23CAF362BD48D"
CARRIED_V40_COMPONENT_IDS = (512, 513, 514, 521, 522, 523, 539, 540, 541, 542, 543, 545, 546, 547, 563, 564, 565, 566, 567, 568)


def require(condition: bool, message: str) -> None:
    if not condition:
        raise ValueError(message)


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest().upper()


def rel(path: Path) -> str:
    return path.resolve().relative_to(ROOT).as_posix()


def load(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def write_pbm(image: Image.Image, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    image.convert("1").save(path)


def ink_pixels(image: Image.Image) -> int:
    return sum(1 for pixel in image.convert("1").getdata() if pixel == 0)


def binary(image: Image.Image) -> Image.Image:
    return image.convert("L").point(lambda value: 0 if value < 128 else 255, mode="1")


def tight_crop(image: Image.Image, name: str) -> Image.Image:
    mono = binary(image)
    inverse = mono.point(lambda value: 255 if value == 0 else 0, mode="1")
    box = inverse.getbbox()
    require(box is not None, f"V42 source crop has no ink: {name}")
    return mono.crop(box)


def grid_crop(sheet: Image.Image, index: int, columns: int, rows: int, name: str) -> tuple[Image.Image, list[int]]:
    row, column = divmod(index, columns)
    require(0 <= row < rows, f"V42 grid index outside sheet: {name}")
    left = round(column * sheet.width / columns)
    right = round((column + 1) * sheet.width / columns)
    top = round(row * sheet.height / rows)
    bottom = round((row + 1) * sheet.height / rows)
    cell = binary(sheet.crop((left, top, right, bottom)))
    inverse = cell.point(lambda value: 255 if value == 0 else 0, mode="1")
    box = inverse.getbbox()
    require(box is not None, f"V42 grid cell has no ink: {name}")
    crop = cell.crop(box)
    return crop, [left + box[0], top + box[1], crop.width, crop.height]


def source_fragment(sheet: Image.Image, box: list[int], name: str) -> Image.Image:
    x, y, width, height = box
    crop = binary(sheet.crop((x, y, x + width, y + height)))
    require(ink_pixels(crop) > 8, f"V42 source fragment is unexpectedly blank: {name}")
    return crop


def resize_mask(mask: Image.Image, scale: float, name: str) -> Image.Image:
    width = max(1, round(mask.width * scale))
    height = max(1, round(mask.height * scale))
    resized = mask.convert("L").resize((width, height), Image.Resampling.LANCZOS)
    result = binary(resized)
    require(ink_pixels(result) > 3, f"V42 component is unexpectedly thin after scaling: {name}")
    return result


def copy_v40_components(output: Path) -> list[dict[str, Any]]:
    layout = load(V40_LAYOUT)
    components = layout.get("components")
    require(layout.get("schema") == "companion.v40_functional_decoration_component_export.v1" and
            isinstance(components, list) and len(components) == 69 and
            [component.get("component_id") for component in components] == list(range(500, 569)),
            "V42 inherited V40 component namespace drifted")
    copied: list[dict[str, Any]] = []
    for component in components:
        if component["component_id"] not in CARRIED_V40_COMPONENT_IDS:
            continue
        source = ROOT / str(component["mask"])
        destination = output / "component-masks" / f"{component['name']}.pbm"
        require(source.is_file() and sha256(source) == component["mask_sha256"],
                f"V42 inherited V40 source mask drifted: {component['name']}")
        write_pbm(Image.open(source).convert("1"), destination)
        require(sha256(destination) == component["mask_sha256"],
                f"V42 inherited V40 source mask changed: {component['name']}")
        copied.append({
            **component,
            "source_pack": "v42_merged_special",
            "source": {
                "kind": "carried_forward_v40_registered_mask",
                "prior_component_id": component["component_id"],
                "prior_layout": rel(V40_LAYOUT),
                "prior_mask": component["mask"],
                "prior_mask_sha256": component["mask_sha256"],
            },
            "mask": rel(destination),
            "mask_sha256": sha256(destination),
        })
    return copied


def request_gate(request_path: Path, source: Path, expected_sha: str, name: str,
                 expected_size: tuple[int, int] = (1254, 1254)) -> dict[str, Any]:
    request = load(request_path)
    require(request.get("status") == "RECORDED_BEFORE_IMAGE_GENERATION" and
            request.get("locked_v9_reference", {}).get("sha256") == LOCKED and
            source.is_file() and sha256(source) == expected_sha,
            f"V42 {name} generation provenance drifted")
    image = Image.open(source).convert("RGB")
    require(image.size == expected_size, f"V43 {name} sheet dimensions drifted")
    return request


def delighted_native_gate(source: Path) -> None:
    """Fail closed unless the generated mouth survives the native 200x200 symmetry gate."""
    with Image.open(source) as sheet:
        fragment = source_fragment(sheet.convert("RGB"), DELIGHTED_MOUTH_BOX, "delighted_mouth_native_gate")
    mask = resize_mask(fragment, DELIGHTED_MOUTH_SCALE, "delighted_mouth_native_gate")
    ink = mask.point(lambda value: 255 if value == 0 else 0, mode="1")
    bbox = ink.getbbox()
    require(bbox is not None, "V42 Delighted mouth native crop has no ink")
    width = bbox[2] - bbox[0]
    height = bbox[3] - bbox[1]
    require(22 <= width <= 26 and 8 <= height <= 12,
            f"V42 Delighted mouth native bounds drifted: {width}x{height}")
    axis = (mask.width - 1) / 2.0
    bbox_center = (bbox[0] + bbox[2] - 1) / 2.0
    require(abs(bbox_center - axis) <= 1.0,
            f"V42 Delighted mouth native center drifted: bbox={bbox_center:.2f} axis={axis:.2f}")
    center = mask.width // 2
    pixels = mask.load()
    left = sum(1 for y in range(mask.height) for x in range(center) if pixels[x, y] == 0)
    right = sum(1 for y in range(mask.height) for x in range(center + 1, mask.width) if pixels[x, y] == 0)
    require(abs(left - right) <= 2,
            f"V42 Delighted mouth native black-pixel symmetry drifted: left={left} right={right}")


def append_generated_component(result: list[dict[str, Any]], output: Path, component_id: int, name: str,
                               role: str, source_kind: str, source_sheet: Path, request: Path,
                               source_mask: Image.Image, source_box: list[int], scale: float,
                               base: list[int], offset_range: dict[str, list[int]], z_index: int,
                               metadata: dict[str, Any]) -> None:
    mask = resize_mask(source_mask, scale, name)
    destination = output / "component-masks" / f"{name}.pbm"
    write_pbm(mask, destination)
    require(base[0] >= SAFE_INSET and base[1] >= SAFE_INSET and
            base[0] + mask.width <= CANVAS[0] - SAFE_INSET and
            base[1] + mask.height <= CANVAS[1] - SAFE_INSET,
            f"V42 component escapes the 200x200 safe inset: {name}")
    result.append({
        "component_id": component_id,
        "name": name,
        "role": role,
        "source_pack": "v42_merged_special",
        "source": {
            "kind": source_kind,
            "sheet": rel(source_sheet),
            "sheet_sha256": sha256(source_sheet),
            "request": rel(request),
            "locked_v9_sha256": LOCKED,
            "crop_box_source": source_box,
            "threshold": 128,
            "scale": scale,
            **metadata,
        },
        "mask": rel(destination),
        "mask_sha256": sha256(destination),
        "base_position": base,
        "mask_size": [mask.width, mask.height],
        "offset_range": offset_range,
        "z_index": z_index,
        "composite_op": "ink",
        "ink_pixels": ink_pixels(mask),
    })


def generated_components(output: Path) -> tuple[list[dict[str, Any]], dict[str, list[dict[str, Any]]]]:
    request_gate(RECORDING_REQUEST, RECORDING_SOURCE, RECORDING_SHA, "recording",
                 expected_size=(2172, 724))
    request_gate(CHARGING_REQUEST, CHARGING_SOURCE, CHARGING_SHA, "charging")
    request_gate(EMOTION_REQUEST, EMOTION_SOURCE, EMOTION_SHA, "emotion")
    request_gate(LOWER_FACE_REQUEST, LOWER_FACE_SOURCE, LOWER_FACE_SHA, "lower_face")
    request_gate(THOUGHTFUL_MOUTH_REQUEST, THOUGHTFUL_MOUTH_SOURCE, THOUGHTFUL_MOUTH_SHA, "thoughtful_mouth")
    request_gate(DELIGHTED_MOUTH_REQUEST, DELIGHTED_MOUTH_SOURCE, DELIGHTED_MOUTH_SHA, "delighted_mouth")
    delighted_native_gate(DELIGHTED_MOUTH_SOURCE)
    request_gate(BASHFUL_REQUEST, BASHFUL_SOURCE, BASHFUL_SHA, "bashful")
    request_gate(SLEEP_REQUEST, SLEEP_SOURCE, SLEEP_SHA, "sleep")
    recording_sheet = Image.open(RECORDING_SOURCE).convert("RGB")
    charging_sheet = Image.open(CHARGING_SOURCE).convert("RGB")
    emotion_sheet = Image.open(EMOTION_SOURCE).convert("RGB")
    lower_face_sheet = Image.open(LOWER_FACE_SOURCE).convert("RGB")
    thoughtful_mouth_sheet = Image.open(THOUGHTFUL_MOUTH_SOURCE).convert("RGB")
    delighted_mouth_sheet = Image.open(DELIGHTED_MOUTH_SOURCE).convert("RGB")
    bashful_sheet = Image.open(BASHFUL_SOURCE).convert("RGB")
    sleep_sheet = Image.open(SLEEP_SOURCE).convert("RGB")
    result: list[dict[str, Any]] = []
    evidence: dict[str, list[dict[str, Any]]] = {"recording": [], "charging": [], "emotion": [], "lower_face": [], "thoughtful_mouth": [], "delighted_mouth": [], "bashful": [], "sleep": []}

    recording_definitions = [
        (569, "v43_recording_input_inward_0", "recording_input", 0, [164, 116]),
        (570, "v43_recording_input_inward_1", "recording_input", 1, [164, 116]),
        (571, "v43_recording_input_inward_2", "recording_input", 2, [164, 116]),
    ]
    for component_id, name, event, index, base in recording_definitions:
        fragment, box = grid_crop(recording_sheet, index, 3, 1, name)
        snapshot = output / "source-fragments" / f"{name}.pbm"
        write_pbm(fragment, snapshot)
        evidence["recording"].append({"name": name, "event": event, "path": rel(snapshot),
                                        "sha256": sha256(snapshot), "crop_box_source": box,
                                        "ink_pixels": ink_pixels(fragment)})
        append_generated_component(result, output, component_id, name, "functional_charm",
                                   "imagegen_v43_recording_input_inward_grid_cell_tight_crop_scaled", RECORDING_SOURCE,
                                   RECORDING_REQUEST, fragment, box, 0.08,
                                   base, {"min": [0, 0], "max": [0, 0]}, 90,
                                   {"event": event, "cell_index": index,
                                    "wave_direction": "inward_toward_face_on_left"})

    charging_definitions = [
        (572, "v42_wireless_dock_charge_0", 0, [86, 178]),
        (573, "v42_wireless_dock_charge_1", 1, [86, 178]),
        (574, "v42_wireless_dock_charge_2", 2, [86, 178]),
    ]
    for component_id, name, index, base in charging_definitions:
        fragment, box = grid_crop(charging_sheet, index, 3, 1, name)
        snapshot = output / "source-fragments" / f"{name}.pbm"
        write_pbm(fragment, snapshot)
        evidence["charging"].append({"name": name, "event": "wireless_dock_charge", "path": rel(snapshot),
                                       "sha256": sha256(snapshot), "crop_box_source": box,
                                       "ink_pixels": ink_pixels(fragment)})
        append_generated_component(result, output, component_id, name, "functional_charm",
                                   "imagegen_v42_charging_cradle_grid_cell_tight_crop_scaled", CHARGING_SOURCE,
                                   CHARGING_REQUEST, fragment, box, 0.14, base,
                                   {"min": [0, 0], "max": [0, 0]}, 90,
                                   {"event": "wireless_dock_charge", "cell_index": index})

    emotion_definitions = [
        (575, "v42_delighted_left_brow", "delighted", "left_brow", [188, 195, 67, 38], 0.35, [45, 80]),
        (576, "v42_delighted_left_cheek", "delighted", "left_cheek", [152, 419, 43, 28], 0.35, [33, 157]),
        (577, "v42_delighted_mouth", "delighted", "mouth", [305, 429, 85, 69], 0.35, [85, 154]),
        (578, "v42_delighted_right_brow", "delighted", "right_brow", [434, 189, 71, 36], 0.35, [127, 79]),
        (579, "v42_delighted_right_cheek", "delighted", "right_cheek", [499, 419, 44, 28], 0.35, [152, 157]),
        (585, "v42_thoughtful_left_brow", "thoughtful", "left_brow", [190, 741, 74, 43], 0.35, [50, 77]),
        (586, "v42_thoughtful_left_cheek", "thoughtful", "left_cheek", [153, 965, 41, 25], 0.35, [33, 157]),
        (587, "v42_thoughtful_mouth", "thoughtful", "mouth", [330, 990, 73, 33], 0.35, [89, 162]),
        (588, "v42_thoughtful_right_brow", "thoughtful", "right_brow", [428, 802, 72, 27], 0.35, [127, 95]),
        (589, "v42_focused_left_brow", "focused", "left_brow", [788, 791, 64, 30], 0.35, [51, 95]),
        (590, "v42_focused_left_cheek", "focused", "left_cheek", [750, 976, 40, 25], 0.35, [33, 160]),
        (591, "v42_focused_mouth", "focused", "mouth", [889, 995, 76, 16], 0.35, [87, 164]),
        (592, "v42_focused_right_brow", "focused", "right_brow", [1000, 795, 61, 30], 0.35, [128, 95]),
        (593, "v42_focused_right_cheek", "focused", "right_cheek", [1063, 976, 40, 25], 0.35, [151, 160]),
    ]
    lower_face_mouths = {
        591: ([878, 997, 70, 13], 0.35, [87, 165]),
    }
    thoughtful_mouths = {
        587: ([581, 780, 112, 21], 0.25, [86, 163]),
    }
    delighted_mouths = {
        577: (DELIGHTED_MOUTH_BOX, DELIGHTED_MOUTH_SCALE, [87, 158]),
    }
    for component_id, name, emotion, role, box, scale, base in emotion_definitions:
        if component_id in delighted_mouths:
            box, scale, base = delighted_mouths[component_id]
            source_sheet, source_path, source_request = delighted_mouth_sheet, DELIGHTED_MOUTH_SOURCE, DELIGHTED_MOUTH_REQUEST
            source_kind = "imagegen_v42_delighted_mouth_v12_component_crop_scaled"
            evidence_key = "delighted_mouth"
        elif component_id in thoughtful_mouths:
            box, scale, base = thoughtful_mouths[component_id]
            source_sheet, source_path, source_request = thoughtful_mouth_sheet, THOUGHTFUL_MOUTH_SOURCE, THOUGHTFUL_MOUTH_REQUEST
            source_kind = "imagegen_v42_thoughtful_mouth_component_crop_scaled"
            evidence_key = "thoughtful_mouth"
        elif component_id in lower_face_mouths:
            box, scale, base = lower_face_mouths[component_id]
            source_sheet, source_path, source_request = lower_face_sheet, LOWER_FACE_SOURCE, LOWER_FACE_REQUEST
            source_kind = "imagegen_v42_lower_face_mouth_component_crop_scaled"
            evidence_key = "lower_face"
        else:
            source_sheet, source_path, source_request = emotion_sheet, EMOTION_SOURCE, EMOTION_REQUEST
            source_kind = "imagegen_v42_emotion_component_crop_scaled"
            evidence_key = "emotion"
        fragment = source_fragment(source_sheet, box, name)
        snapshot = output / "source-fragments" / f"{name}.pbm"
        write_pbm(fragment, snapshot)
        evidence[evidence_key].append({"name": name, "emotion": emotion, "role": role,
                                       "path": rel(snapshot), "sha256": sha256(snapshot),
                                       "crop_box_source": box, "ink_pixels": ink_pixels(fragment)})
        offset = {"min": [-1, -1], "max": [1, 1]} if "brow" in role else {"min": [0, 0], "max": [0, 0]}
        append_generated_component(result, output, component_id, name, role,
                                   source_kind, source_path, source_request,
                                   fragment, box, scale, base, offset, 20 if "brow" in role else 40 if "cheek" in role else 60,
                                   {"emotion": emotion})

    bashful_definitions = [
        (580, "v42_bashful_left_brow", "left_brow", [378, 396, 112, 49], 0.20, [50, 94]),
        (581, "v42_bashful_left_cheek", "left_cheek", [324, 731, 63, 37], 0.25, [43, 157]),
        (582, "v42_bashful_mouth", "mouth", [880, 445, 68, 26], 0.35, [89, 162]),
        (583, "v42_bashful_right_brow", "right_brow", [804, 401, 100, 47], 0.20, [129, 94]),
        (584, "v42_bashful_right_cheek", "right_cheek", [899, 731, 61, 36], 0.25, [143, 157]),
    ]
    for component_id, name, role, box, scale, base in bashful_definitions:
        source_sheet, source_path, source_request = bashful_sheet, BASHFUL_SOURCE, BASHFUL_REQUEST
        source_kind = "imagegen_v42_bashful_component_crop_scaled"
        evidence_key = "bashful"
        if component_id == 582:
            source_sheet, source_path, source_request = lower_face_sheet, LOWER_FACE_SOURCE, LOWER_FACE_REQUEST
            source_kind = "imagegen_v42_lower_face_mouth_component_crop_scaled"
            evidence_key = "lower_face"
        fragment = source_fragment(source_sheet, box, name)
        snapshot = output / "source-fragments" / f"{name}.pbm"
        write_pbm(fragment, snapshot)
        evidence[evidence_key].append({"name": name, "emotion": "bashful", "role": role,
                                       "path": rel(snapshot), "sha256": sha256(snapshot),
                                       "crop_box_source": box, "ink_pixels": ink_pixels(fragment)})
        offset = {"min": [-1, -1], "max": [1, 1]} if "brow" in role else {"min": [0, 0], "max": [0, 0]}
        append_generated_component(result, output, component_id, name, role,
                                   source_kind, source_path, source_request,
                                   fragment, box, scale, base, offset,
                                   20 if "brow" in role else 40 if "cheek" in role else 60,
                                   {"emotion": "bashful"})

    sleep_definitions = [
        (594, "v42_sleep_z_large", [256, 487, 230, 277], [94, 27], 0.08),
        (595, "v42_sleep_z_medium", [655, 595, 137, 167], [116, 42], 0.09),
        (596, "v42_sleep_z_small", [949, 660, 86, 104], [134, 54], 0.10),
    ]
    for component_id, name, box, base, scale in sleep_definitions:
        fragment = source_fragment(sleep_sheet, box, name)
        snapshot = output / "source-fragments" / f"{name}.pbm"
        write_pbm(fragment, snapshot)
        evidence["sleep"].append({"name": name, "path": rel(snapshot), "sha256": sha256(snapshot),
                                  "crop_box_source": box, "ink_pixels": ink_pixels(fragment)})
        append_generated_component(result, output, component_id, name, "sleep_charm",
                                   "imagegen_v42_sleep_zzz_detected_component_crop_scaled", SLEEP_SOURCE,
                                   SLEEP_REQUEST, fragment, box, scale, base,
                                   {"min": [0, -1], "max": [1, 1]}, 10,
                                   {"event": "sleep_zzz"})
    result.sort(key=lambda component: component["component_id"])
    require([component["component_id"] for component in result] == list(range(569, 597)),
            "V42 generated component ID coverage drifted")
    return result, evidence


def build_pack(output: Path, components: list[dict[str, Any]]) -> dict[str, Any]:
    index = bytearray()
    payload = bytearray()
    records: list[dict[str, Any]] = []
    data_offset = HEADER_BYTES + INDEX_BYTES * len(components)
    for component in components:
        image = Image.open(ROOT / str(component["mask"])).convert("1")
        width, height = image.size
        stride = (width + 7) // 8
        data = image.tobytes()
        offset = data_offset + len(payload)
        crc = zlib.crc32(data) & 0xFFFFFFFF
        require(len(data) == stride * height, f"V42 component stride drifted: {component['name']}")
        index.extend(struct.pack("<HHHHIII", component["component_id"], width, height, stride, offset, len(data), crc))
        payload.extend(data)
        records.append({"component_id": component["component_id"], "name": component["name"], "width": width,
                        "height": height, "stride_bytes": stride, "data_offset": offset,
                        "data_size": len(data), "data_crc32": f"{crc:08X}"})
    total_size = data_offset + len(payload)
    header = bytearray(HEADER_BYTES)
    header[0:4] = b"CRIG"
    struct.pack_into("<H", header, 4, 1)
    struct.pack_into("<H", header, 6, HEADER_BYTES)
    struct.pack_into("<I", header, 8, total_size)
    struct.pack_into("<I", header, 12, REVISION)
    struct.pack_into("<H", header, 16, CANVAS[0])
    struct.pack_into("<H", header, 18, CANVAS[1])
    struct.pack_into("<H", header, 20, 25)
    header[22] = 1
    header[23] = SAFE_INSET
    struct.pack_into("<H", header, 24, len(components))
    struct.pack_into("<I", header, 28, HEADER_BYTES)
    struct.pack_into("<I", header, 32, data_offset)
    struct.pack_into("<I", header, 36, zlib.crc32(payload) & 0xFFFFFFFF)
    struct.pack_into("<I", header, 40, zlib.crc32(index) & 0xFFFFFFFF)
    header[44:76] = bytes.fromhex(LOCKED)
    path = output / "companion-v9-v43-recording-input-inward-special-components-candidate-200x200.crig"
    path.write_bytes(bytes(header) + bytes(index) + bytes(payload))
    return {"path": rel(path), "sha256": sha256(path), "revision": REVISION, "component_count": len(components),
            "total_size": total_size, "components": records}


def build_artifacts() -> dict[Path, bytes]:
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    staging = Path(tempfile.mkdtemp(prefix="v42-components-", dir=OUTPUT.parent))
    inherited = copy_v40_components(staging)
    generated, evidence = generated_components(staging)
    components = inherited + generated
    expected_ids = list(CARRIED_V40_COMPONENT_IDS) + list(range(569, 597))
    require(len(components) == 48 and [component["component_id"] for component in components] == expected_ids,
            "V42 special component namespace drifted")
    require(not any("moon" in component["name"] or "cloud" in component["name"] for component in generated),
            "V42 must not generate or bind moon/cloud sleep decorations")
    pack = build_pack(staging, components)
    layout = {
        "schema": "companion.v43_special_component_export.v1",
        "status": "CANDIDATE_COMPONENT_EXPORT_MACHINE_PENDING",
        "revision": REVISION,
        "authority": ["COMP-REQ-093", "COMP-REQ-239", "COMP-REQ-240", "COMP-REQ-242", "COMP-REQ-245", "COMP-REQ-246", "COMP-REQ-247", "COMP-REQ-248", "COMP-REQ-249", "COMP-REQ-250", "COMP-REQ-251", "COMP-REQ-263"],
        "locked_v9_source": {"path": "docs/art/iterations/companion-pet-expression-v9/generated_pet_expression_sheet_v9_candidate.png", "sha256": LOCKED},
        "source_sheets": {
            "recording": {"path": rel(RECORDING_SOURCE), "sha256": RECORDING_SHA, "request": rel(RECORDING_REQUEST), "grid": [3, 1], "wave_direction": "inward_toward_face_on_left"},
            "charging": {"path": rel(CHARGING_SOURCE), "sha256": CHARGING_SHA, "request": rel(CHARGING_REQUEST), "grid": [3, 1]},
            "emotion": {"path": rel(EMOTION_SOURCE), "sha256": EMOTION_SHA, "request": rel(EMOTION_REQUEST), "grid": [2, 2]},
            "lower_face": {"path": rel(LOWER_FACE_SOURCE), "sha256": LOWER_FACE_SHA, "request": rel(LOWER_FACE_REQUEST), "grid": [2, 2]},
            "thoughtful_mouth": {"path": rel(THOUGHTFUL_MOUTH_SOURCE), "sha256": THOUGHTFUL_MOUTH_SHA, "request": rel(THOUGHTFUL_MOUTH_REQUEST), "grid": [1, 1]},
            "delighted_mouth": {"path": rel(DELIGHTED_MOUTH_SOURCE), "sha256": DELIGHTED_MOUTH_SHA, "request": rel(DELIGHTED_MOUTH_REQUEST), "grid": [1, 1]},
            "bashful": {"path": rel(BASHFUL_SOURCE), "sha256": BASHFUL_SHA, "request": rel(BASHFUL_REQUEST), "grid": [1, 1]},
            "sleep": {"path": rel(SLEEP_SOURCE), "sha256": SLEEP_SHA, "request": rel(SLEEP_REQUEST), "grid": [3, 1]},
        },
        "runtime_resource_activated": False,
        "active_candidate_binding": "forbidden",
        "component_export_scope": "20 currently used V40 masks carried byte-identically plus 3 V43 inward-facing recording ornaments, 3 V42 wireless charging cradles, 19 V42 emotion components with versioned lower-face mouth sources, separately registered Delighted and Thoughtful mouth plus Bashful brow/cheek sources, and 3 V42 ZZZ-only sleep components; unused historical V40 masks remain only in their preserved V40 evidence pack",
        "source_evidence": evidence,
        "components": components,
        "pack": pack,
        "non_claims": ["no_locked_v9_modification", "no_whole_face_card", "no_code_drawn_feature", "no_runtime_binding", "no_panel_or_driver_change", "no_human_acceptance"],
    }
    prefix = rel(staging)
    target_prefix = rel(OUTPUT)

    def rebase(value: Any) -> Any:
        if isinstance(value, str):
            return target_prefix + value[len(prefix):] if value.startswith(prefix) else value
        if isinstance(value, list):
            return [rebase(item) for item in value]
        if isinstance(value, dict):
            return {key: rebase(item) for key, item in value.items()}
        return value

    layout_path = staging / "v43-special-component-layout.json"
    layout_path.write_text(json.dumps(rebase(layout), indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    artifacts = {path.relative_to(staging): path.read_bytes() for path in staging.rglob("*") if path.is_file()}
    shutil.rmtree(staging)
    return {OUTPUT / path: data for path, data in artifacts.items()}


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()
    artifacts = build_artifacts()
    if args.check:
        drifted = [path for path, data in artifacts.items() if not path.is_file() or path.read_bytes() != data]
        if drifted:
            for path in drifted:
                print(f"ERROR: generated artifact drifted: {rel(path)}")
            return 1
    else:
        for path, data in artifacts.items():
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(data)
    print("PASS: generated inactive V43 special CRIG with 48 registered source components and inward recording-input art.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
