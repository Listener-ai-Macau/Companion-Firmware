#!/usr/bin/env python3
"""Gate V42 source lineage, owner-visible scope, and non-overlapping V9 compositions."""

from __future__ import annotations

import argparse
import hashlib
import json
from itertools import combinations
from pathlib import Path
from typing import Any

from PIL import Image

import render_companion_v34_v35_special_decoration_wb55_parity as renderer


ROOT = Path(__file__).resolve().parents[1]
LAYOUT = ROOT / "docs/art/iterations/companion-pet-expression-v9-two-track-rig-v4/candidate/two-track-layout.json"
SPECIAL = ROOT / "docs/art/iterations/companion-pet-expression-v9-two-track-rig-v4/candidate/v42-special-component-layout.json"
TRACE = ROOT / "docs/art/iterations/companion-pet-expression-v9-two-track-rig-v4/candidate/target-score-attempt-01/v42-wb55-target-profile-plan.json"
V22 = ROOT / "docs/art/iterations/companion-pet-expression-v9-extension-v22-emotion-separation-source/candidate/target-rig-attempt-01/v22-emotion-separation-target-rig-layout.json"
REPORT = ROOT / "docs/validation/companion-v42-expression-extension-layout-gate-20260721.json"
LOCKED = "919F344957661DEF2099AD56AB1286CCA9DBA4D8F08B702617B6DF5B1A28E9DA"
GAZE = ("center", "left", "right", "up", "down")
EXPECTED_ENDPOINTS = {
    "center": {"primary": [1, 0], "sparkle": [1, 0]},
    "left": {"primary": [-2, 2], "sparkle": [-5, 3]},
    "right": {"primary": [5, 2], "sparkle": [5, 3]},
    "up": {"primary": [1, -3], "sparkle": [1, -5]},
    "down": {"primary": [1, 4], "sparkle": [1, 5]},
}
NEW_EMOTIONS = ("delighted_presence", "bashful_presence", "thoughtful_presence", "focused_presence")
HIDDEN_GAZE = {f"daily_attention_{direction}" for direction in GAZE}


def require(condition: bool, message: str) -> None:
    if not condition:
        raise ValueError(message)


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest().upper()


def rel(path: Path) -> str:
    return path.resolve().relative_to(ROOT).as_posix()


def load(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    require(isinstance(value, dict), f"{path} must contain an object")
    return value


def black_overlap(left: bytes, right: bytes) -> int:
    return sum(((~first & ~second) & 0xFF).bit_count() for first, second in zip(left, right))


def find_score(scores: list[dict[str, Any]], name: str) -> dict[str, Any]:
    found = [score for score in scores if score.get("name") == name]
    require(len(found) == 1, f"missing or duplicate V42 score: {name}")
    return found[0]


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--write", type=Path, default=REPORT)
    args = parser.parse_args()
    layout = load(LAYOUT)
    special = load(SPECIAL)
    trace = load(TRACE)
    v22 = load(V22)
    require(layout.get("schema") == "companion.v42_expression_extension_two_track_layout.v1" and
            layout.get("status") == "CANDIDATE_TRACK_MODEL_VERSIONED_RUNTIME_INACTIVE" and
            layout.get("revision") == 42 and layout.get("locked_v9_source", {}).get("sha256") == LOCKED and
            layout.get("composition", {}).get("canvas") == "200x200_1bpp_white_is_one_msb" and
            layout.get("composition", {}).get("maximum_layers") == 16 and layout.get("composition", {}).get("no_mask_synthesis") is True and
            layout.get("composition", {}).get("runtime_binding") == "forbidden_until_v42_machine_audit_and_owner_review",
            "V42 layout identity or inactive component-only boundary drifted")
    require(special.get("schema") == "companion.v42_special_component_export.v1" and
            special.get("locked_v9_source", {}).get("sha256") == LOCKED and len(special.get("components", [])) == 48 and
            special.get("runtime_resource_activated") is False and special.get("active_candidate_binding") == "forbidden",
            "V42 special component export provenance drifted")
    for key, expected_hash in (("recording", "508FC5A5D8B89F1769903062F6EAE93DCCFF013BB8340366F53D9DC6EF7CFEB7"),
                               ("charging", "4F58D263EA9E71A6C31C2C969D6FD615BBA5672023BDC08B4FC6B3A6B2BDD7FA"),
                               ("emotion", "CE77807B4053C808D9E111CE38B8806735F56EA29DFCE2ECA807FD95964F5A03"),
                               ("lower_face", "AD89593250DDAB09816AD38B8B46509ADD48726499765A5BFB6D724942C40E9B"),
                               ("thoughtful_mouth", "1D76B69F92ED5ABD6BACA877A90F6C6FDD76A62B1EC06B6D726264A6F9FA0C67"),
                               ("delighted_mouth", "E293FC2640A4E650DC37DC857930CA6C563A52ABBF560C0D5163FA7B66B3B5AB"),
                               ("bashful", "6088781812BFC1F908B35876B74356D71CEDDCF93288FFF61F65163F57A0F073"),
                               ("sleep", "C9BEC982411D22CA0031FA28F12950E27F098D09AFF626BAF0A23CAF362BD48D")):
        source = special.get("source_sheets", {}).get(key, {})
        source_path = ROOT / str(source.get("path", ""))
        request = ROOT / str(source.get("request", ""))
        require(source.get("sha256") == expected_hash and source_path.is_file() and sha256(source_path) == expected_hash and
                request.is_file() and load(request).get("status") == "RECORDED_BEFORE_IMAGE_GENERATION" and
                load(request).get("locked_v9_reference", {}).get("sha256") == LOCKED,
                f"V42 {key} image-generation lineage drifted")
    components = special.get("components", [])
    component_ids = {component.get("component_id") for component in components}
    require({569, 570, 571, 572, 573, 574, 594, 595, 596}.issubset(component_ids) and
            not component_ids & {531, 532, 544} and
            not any("moon" in str(component.get("name", "")) or "cloud" in str(component.get("name", "")) for component in components),
            "V42 source pack must contain new input/dock/ZZZ art and no moon or cloud component")
    by_id = {component["component_id"]: component for component in components}
    require(all(by_id[component_id].get("source", {}).get("sheet") == special["source_sheets"]["charging"]["path"]
                for component_id in (572, 573, 574)), "V42 charging components must use the r2 cradle source")
    require(all(by_id[component_id].get("source", {}).get("sheet") == special["source_sheets"]["bashful"]["path"]
                for component_id in (580, 581, 583, 584)), "V42 Bashful brow/cheek components must use the registered Bashful source")
    require(all(by_id[component_id].get("source", {}).get("sheet") == special["source_sheets"]["lower_face"]["path"]
                for component_id in (582, 591)), "V42 lower-face emotion mouths must use the registered lower-face source")
    require(by_id[587].get("source", {}).get("sheet") == special["source_sheets"]["thoughtful_mouth"]["path"],
            "V42 Thoughtful mouth must use its separately registered source")
    require(by_id[577].get("source", {}).get("sheet") == special["source_sheets"]["delighted_mouth"]["path"],
            "V42 Delighted mouth must use its separately registered source")
    added = layout.get("expression_track", {}).get("added_performances", {})
    require(set(added) == set(NEW_EMOTIONS), "V42 added emotion vocabulary drifted")
    signatures = {name: tuple(added[name]["base_face"]) for name in NEW_EMOTIONS}
    require(all(signatures[left] != signatures[right] for left, right in combinations(NEW_EMOTIONS, 2)),
            "V42 added emotion component plans are not pairwise distinct")
    sleep = layout.get("expression_track", {}).get("sleep_zzz_only", {})
    require(sleep.get("zzz_components") == [594, 595, 596] and set(sleep.get("forbidden_components", [])) == {531, 532, 544},
            "V42 sleep is not declared ZZZ-only")
    preview = layout.get("preview_zh", {})
    metadata = preview.get("stories", {}) if isinstance(preview, dict) else {}
    require(isinstance(metadata, dict) and HIDDEN_GAZE.issubset(metadata) and
            all(metadata[name].get("owner_visible") is False for name in HIDDEN_GAZE) and
            all(metadata[name].get("owner_visible", True) is not False for name in set(metadata) - HIDDEN_GAZE),
            "V42 owner preview must hide only internal gaze demonstrations")
    require(trace.get("schema") == "companion.v42_expression_extension_wb55_target_profile_plan.v1" and
            trace.get("status") == "PASS_CANDIDATE_PROFILE_GENERATED_RUNTIME_INACTIVE" and
            trace.get("locked_v9_source_sha256") == LOCKED and trace.get("component_sources") == {"v22_face": 37, "v42_special_source": 48} and
            trace.get("runtime_resource_activated") is False and trace.get("active_candidate_binding") == "forbidden_until_v42_machine_audit_and_owner_review",
            "V42 generated target profile provenance drifted")
    scores = trace.get("scores", [])
    require(isinstance(scores, list) and len(scores) == 21 and sum(len(score.get("steps", [])) for score in scores) == 93,
            "V42 score/story coverage drifted")
    browser_components = renderer.component_map(V22, SPECIAL)
    collision_counts: dict[str, int] = {"recording": 0, "charging": 0}
    for score in scores:
        name = score.get("name")
        for step in score.get("steps", []):
            layers = step.get("layers", [])
            ids = [layer.get("component_id") for layer in layers]
            require(len(ids) == len(set(ids)) and len(ids) <= 16 and 4 in ids and
                    next(layer.get("offset") for layer in layers if layer.get("component_id") == 4) == [0, 0],
                    f"V42 score is not a legal fixed-nose source plan: {name}")
            if name == "sleepy_presence":
                require(not ({531, 532, 544} & set(ids)), "V42 sleep frame carries a forbidden moon/cloud component")
            functional_ids = {layer.get("component_id") for layer in step.get("functional_layers", [])}
            if score.get("functional_decoration_track") == "recording_input":
                require(functional_ids <= {569, 570, 571} and functional_ids, "V42 recording reused an old functional ornament")
                _, face = renderer.render_frame(browser_components, step["expression_layers"])
                _, decoration = renderer.render_frame(browser_components, step["functional_layers"])
                collision_counts["recording"] += black_overlap(face, decoration)
            if score.get("functional_decoration_track") == "bottom_connector_charging":
                require(functional_ids <= {572, 573, 574} and functional_ids, "V42 charging reused an old functional ornament")
                _, face = renderer.render_frame(browser_components, step["expression_layers"])
                _, decoration = renderer.render_frame(browser_components, step["functional_layers"])
                collision_counts["charging"] += black_overlap(face, decoration)
    require(collision_counts == {"recording": 0, "charging": 0}, "V42 functional ornament overlaps a face pixel")
    for direction, endpoint in EXPECTED_ENDPOINTS.items():
        score = find_score(scores, f"daily_attention_{direction}")
        final = score["steps"][2]["layers"]
        offsets = {layer["component_id"]: layer["offset"] for layer in final}
        require(offsets[1] == endpoint["primary"] and offsets[5] == endpoint["primary"] and
                offsets[3] == endpoint["sparkle"] and offsets[7] == endpoint["sparkle"],
                f"V42 {direction} endpoint drifted")
    output = {
        "schema": "companion.v42_expression_extension_layout_gate.v1",
        "status": "PASS_V42_EXPRESSION_EXTENSION_LAYOUT_RUNTIME_INACTIVE",
        "layout": rel(LAYOUT), "special_component_layout": rel(SPECIAL), "locked_v9_source_sha256": LOCKED,
        "component_sources": {"v22_face": 37, "v42_special_source": 48}, "added_emotions": list(NEW_EMOTIONS),
        "five_gaze_states": list(GAZE), "owner_visible_excludes": sorted(HIDDEN_GAZE),
        "functional_face_pixel_overlap": collision_counts, "sleep_zzz_only": True,
        "runtime_resource_activated": False, "active_candidate_binding": "forbidden_until_v42_machine_audit_and_owner_review",
        "non_claims": ["no_whole_face_card", "no_code_drawn_feature", "no_runtime_binding", "no_firmware_flash", "no_panel_or_driver_change"],
    }
    destination = args.write.resolve()
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_text(json.dumps(output, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print("PASS: V42 source lineage, ZZZ-only sleep, owner-visible scope, and face-ornament collision gates hold.")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (OSError, ValueError) as error:
        print(f"FAIL: {error}")
        raise SystemExit(1)
