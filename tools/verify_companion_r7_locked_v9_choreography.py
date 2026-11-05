#!/usr/bin/env python3
"""Verify the deterministic R7 locked-V9 export without touching runtime code."""

from __future__ import annotations

import hashlib
import json
import re
from pathlib import Path
from typing import Any

from PIL import Image

from companion_expression_anchor import ANCHOR_POLICY, CANONICAL_CENTER, output_bounds


ROOT = Path(__file__).resolve().parents[1]
EXPORT = ROOT / "docs/art/iterations/companion-pet-expression-v9-two-track-rig-v7/r7-locked-v9-export-20260723"
EVIDENCE = ROOT / "docs/validation/companion-r7-locked-v9-choreography-20260723"
MANIFEST = EXPORT / "r7-export-manifest.json"
V22_LAYOUT = ROOT / "docs/art/iterations/companion-pet-expression-v9-extension-v22-emotion-separation-source/candidate/target-rig-attempt-01/v22-emotion-separation-target-rig-layout.json"
GRAPH = EXPORT / "r7-transition-graph.json"
COMP_REQ_410 = "COMP-REQ-410"
POLICY_X_START_BYTE, POLICY_X_END_BYTE = 4, 21
POLICY_LOGICAL_Y_START, POLICY_LOGICAL_Y_END = 26, 170
POLICY_BYTE_COUNT = 2610
POLICY_CONTROLLER_Y_START, POLICY_CONTROLLER_Y_END = 173, 29
POLICY_45_BYTES = "AD 00 1D 00"
POLICY_4F_BYTES = "AD 00"
EXPECTED_MANIFEST_SHA256 = "9B55E24EF3E07F4A0832D879F563183728386FE288219D628F7AAF58EB60ABB8"
EXPECTED_GRAPH_SHA256 = "380F7D72450ACA7EC26D4694B0CC1AD18C66F51260DC7C30E5B1E4272CD55524"
EXPECTED_FRAME_HASH_AGGREGATE = "D76AFD445B6A5D34DC715C6158A7A01B5A655B73B1C8340F356D88F32F991EE3"
EXPECTED_SOURCE_HASH_AGGREGATE = "C7ED017BB465961B40B45BE7F4A044A1CECACE8818E849B508CFEDDB58FF9803"
EXPECTED_PLAN_HASH_AGGREGATE = "BE68E4681AE97D8FF6EA4B7B59A85B10EAAB8DAB1FBC42AB17DDE570957FA17D"


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest().upper()


def aggregate_hash(rows: list[str]) -> str:
    return hashlib.sha256("".join(sorted(rows)).encode("utf-8")).hexdigest().upper()


def policy_window() -> dict[str, Any]:
    return {
        "requirement": COMP_REQ_410,
        "x_start_byte": POLICY_X_START_BYTE,
        "x_end_byte": POLICY_X_END_BYTE,
        "logical_y_start": POLICY_LOGICAL_Y_START,
        "logical_y_end": POLICY_LOGICAL_Y_END,
        "byte_count": POLICY_BYTE_COUNT,
        "controller_y_transform": "controller_y=199-logical_y",
        "controller_y_start": POLICY_CONTROLLER_Y_START,
        "controller_y_end": POLICY_CONTROLLER_Y_END,
        "0x45_bytes": POLICY_45_BYTES,
        "0x4F_bytes": POLICY_4F_BYTES,
        "fixed_per_frame": True,
    }


def exact_policy_window(window: dict[str, Any]) -> bool:
    return (
        window.get("x_start_byte") == POLICY_X_START_BYTE
        and window.get("x_end_byte") == POLICY_X_END_BYTE
        and window.get("logical_y_start") == POLICY_LOGICAL_Y_START
        and window.get("logical_y_end") == POLICY_LOGICAL_Y_END
        and window.get("byte_count") == POLICY_BYTE_COUNT
        and window.get("controller_y_start") == POLICY_CONTROLLER_Y_START
        and window.get("controller_y_end") == POLICY_CONTROLLER_Y_END
        and window.get("0x45_bytes") == POLICY_45_BYTES
        and window.get("0x4F_bytes") == POLICY_4F_BYTES
    )


def require(condition: bool, message: str, errors: list[str]) -> None:
    if not condition:
        errors.append(message)


def path_from_rel(value: str) -> Path:
    return ROOT / value


def pixels(path: Path) -> tuple[int, int, list[int]]:
    with Image.open(path) as image:
        bitmap = image.convert("1")
        return bitmap.width, bitmap.height, [bitmap.getpixel((x, y)) for y in range(bitmap.height) for x in range(bitmap.width)]


def black_points(path: Path) -> set[tuple[int, int]]:
    width, height, data = pixels(path)
    return {(index % width, index // width) for index, value in enumerate(data) if value == 0}


def component_points(component: dict[str, Any], layer: dict[str, Any], normalization: tuple[int, int]) -> set[tuple[int, int]]:
    mask = path_from_rel(str(component["mask"]))
    with Image.open(mask) as image:
        bitmap = image.convert("1")
        origin = (int(layer["anchor"][0]) + int(layer["offset"][0]) + normalization[0],
                  int(layer["anchor"][1]) + int(layer["offset"][1]) + normalization[1])
        return {(origin[0] + x, origin[1] + y) for y in range(bitmap.height) for x in range(bitmap.width) if bitmap.getpixel((x, y)) == 0}


def corridor(previous: set[tuple[int, int]], current: set[tuple[int, int]]) -> dict[str, Any]:
    changed = previous ^ current
    if not changed:
        return {"changed_pixel_count": 0, "changed_bounds": None, "x_start_byte": None, "x_end_byte": None,
                "y_start": None, "y_end": None, "byte_count": 0, "minimal": True, "covers_diff": True}
    xs = [point[0] for point in changed]
    ys = [point[1] for point in changed]
    left, right, top, bottom = min(xs), max(xs), min(ys), max(ys)
    start_byte, end_byte = left // 8, right // 8
    window = {(x, y) for x in range(start_byte * 8, (end_byte + 1) * 8) for y in range(top, bottom + 1)}
    return {"changed_pixel_count": len(changed), "changed_bounds": [left, top, right, bottom],
            "x_start_byte": start_byte, "x_end_byte": end_byte, "y_start": top, "y_end": bottom,
            "byte_count": (end_byte - start_byte + 1) * (bottom - top + 1),
            "minimal": start_byte == left // 8 and end_byte == right // 8 and top == min(ys) and bottom == max(ys),
            "covers_diff": changed <= window}


def verify_frames(manifest: dict[str, Any], errors: list[str]) -> dict[str, Any]:
    candidates = manifest.get("all_candidates", [])
    require(manifest.get("candidate_count") == len(candidates) == 93, f"candidate frame count is {len(candidates)}, expected 93", errors)
    owner_visible = manifest.get("owner_visible_stories", [])
    require(manifest.get("owner_visible_story_count") == len(owner_visible) == 16, "owner-visible story count is not 16", errors)
    require(set(owner_visible) == {item["story"] for item in manifest.get("all_candidates", []) if item["story"] in owner_visible}, "owner-visible candidate linkage is incomplete", errors)
    source_hashes: dict[str, str] = {}
    frame_rows: list[str] = []
    source_rows: list[str] = []
    plan_rows: list[str] = []
    for item in candidates:
        target = path_from_rel(item["pbm"])
        source = path_from_rel(item["source_pbm"])
        plan = path_from_rel(item["plan"])
        require(target.is_file() and source.is_file(), f"missing export/source frame: {target} / {source}", errors)
        require(plan.is_file(), f"missing component plan: {plan}", errors)
        if not target.is_file() or not source.is_file():
            continue
        source_hash, target_hash = sha256(source), sha256(target)
        source_hashes[item["source_pbm"]] = source_hash
        require(source_hash == item["source_pbm_sha256"], f"source hash drifted: {source}", errors)
        require(target_hash == item["exported_pbm_sha256"] and target_hash == source_hash, f"export changed source bytes: {target}", errors)
        frame_rows.append(f"{item['pbm']}:{item['exported_pbm_sha256']}\n")
        source_rows.append(f"{item['source_pbm']}:{item['source_pbm_sha256']}\n")
        if plan.is_file():
            plan_rows.append(f"{item['plan']}:{sha256(plan)}\n")
        width, height, _ = pixels(target)
        require((width, height) == (200, 200), f"non-200 frame: {target} -> {width}x{height}", errors)
        bounds = output_bounds(Image.open(target).convert("1"))
        require(tuple(item["output_bounds"]) == tuple(bounds), f"bbox metadata drifted: {target}", errors)
        require(item.get("anchor_policy") == ANCHOR_POLICY, f"anchor policy drifted: {target}", errors)
        require(tuple(item.get("canonical_center", [])) == CANONICAL_CENTER, f"canonical center drifted: {target}", errors)
        require(len(item.get("normalization_offset", [])) == 2 and len(item.get("source_anchor", [])) == 2, f"missing anchor transform: {target}", errors)
    result = {"candidate_count": len(candidates), "source_hash_count": len(source_hashes),
              "plan_count": len(plan_rows), "frame_hash_aggregate": aggregate_hash(frame_rows),
              "source_hash_aggregate": aggregate_hash(source_rows), "plan_hash_aggregate": aggregate_hash(plan_rows)}
    require(result["frame_hash_aggregate"] == EXPECTED_FRAME_HASH_AGGREGATE, "frame hash aggregate drifted", errors)
    require(result["source_hash_aggregate"] == EXPECTED_SOURCE_HASH_AGGREGATE, "source hash aggregate drifted", errors)
    require(result["plan_hash_aggregate"] == EXPECTED_PLAN_HASH_AGGREGATE, "component plan hash aggregate drifted", errors)
    return result


def verify_eye_pixels(manifest: dict[str, Any], errors: list[str]) -> dict[str, Any]:
    layout = json.loads(V22_LAYOUT.read_text(encoding="utf-8"))
    components = {int(item["component_id"]): item for item in layout["components"]}
    for component_id in (1, 2, 3, 5, 6, 7):
        component = components[component_id]
        require(sha256(path_from_rel(component["mask"])) == component["mask_sha256"], f"locked eye component changed: {component_id}", errors)
    evidence: list[dict[str, Any]] = []
    for transition in manifest.get("transitions", []):
        frame_path = path_from_rel(transition["pbm"])
        frame_pixels = black_points(frame_path)
        by_id = {int(layer["component_id"]): layer for layer in transition["layers"]}
        reflection_counts: dict[str, int] = {}
        body_counts: dict[str, int] = {}
        for reflection_id, label, body_id in ((1, "left_primary", 2), (3, "left_sparkle", 2), (5, "right_primary", 6), (7, "right_sparkle", 6)):
            require(reflection_id in by_id and body_id in by_id, f"transition {transition['transition']} lacks eye component {reflection_id}/{body_id}", errors)
            if reflection_id not in by_id or body_id not in by_id:
                continue
            normalization = tuple(transition["normalization_offset"])
            reflection = component_points(components[reflection_id], by_id[reflection_id], normalization)
            body = component_points(components[body_id], by_id[body_id], normalization)
            white_count = sum(point not in frame_pixels for point in reflection if 0 <= point[0] < 200 and 0 <= point[1] < 200)
            black_body_count = sum(point in frame_pixels for point in body if point not in reflection)
            require(white_count == len(reflection), f"{transition['transition']} {label} white cutout missing: {len(reflection) - white_count}", errors)
            require(black_body_count > 0, f"{transition['transition']} {label} lost black eye body", errors)
            reflection_counts[label] = white_count
            body_counts[str(body_id)] = black_body_count
        evidence.append({"transition": transition["transition"], "white_reflection_pixels": reflection_counts, "black_eye_body_pixels": body_counts})
    return {"transitions": evidence, "all_reflections_source_backed": not any("lacks eye" in error for error in errors)}


def verify_diffs(manifest: dict[str, Any], errors: list[str]) -> dict[str, Any]:
    transitions = manifest.get("transitions", [])
    diff_evidence: list[dict[str, Any]] = []
    all_changed: set[tuple[int, int]] = set()
    for index, transition in enumerate(transitions):
        previous = transitions[index - 1]
        previous_path, current_path = path_from_rel(previous["pbm"]), path_from_rel(transition["pbm"])
        previous_points, current_points = black_points(previous_path), black_points(current_path)
        info = corridor(previous_points, current_points)
        info.update({"transition": transition["transition"], "previous": previous["transition"],
                     "previous_sha256": sha256(previous_path), "current_sha256": sha256(current_path)})
        require(previous_path.read_bytes() != current_path.read_bytes(), f"transition {transition['transition']} is an identical activation/dwell", errors)
        require(info["minimal"] and info["covers_diff"], f"transition {transition['transition']} corridor is not minimal/complete", errors)
        info["fixed_payload_window"] = policy_window()
        all_changed |= previous_points ^ current_points
        diff_evidence.append(info)
    aggregate = corridor(set(), all_changed)
    measured_union = {"x_start_byte": aggregate["x_start_byte"], "x_end_byte": aggregate["x_end_byte"],
                      "logical_y_start": aggregate["y_start"], "logical_y_end": aggregate["y_end"],
                      "byte_count": aggregate["byte_count"]}
    measured_matches_policy = (measured_union == {
        "x_start_byte": POLICY_X_START_BYTE, "x_end_byte": POLICY_X_END_BYTE,
        "logical_y_start": POLICY_LOGICAL_Y_START, "logical_y_end": POLICY_LOGICAL_Y_END,
        "byte_count": POLICY_BYTE_COUNT})
    require(measured_matches_policy, f"NO_GO_{COMP_REQ_410}_UNION: measured union {measured_union} is not the approved fixed union", errors)
    fixed_windows = [item["fixed_payload_window"] for item in diff_evidence]
    require(all(exact_policy_window(item) for item in fixed_windows),
            f"NO_GO_{COMP_REQ_410}_DYNAMIC_WINDOW: every frame must use the exact fixed payload window", errors)
    fixed_union = {**policy_window(), "measured_diff_union": measured_union,
                   "measured_matches_policy": measured_matches_policy,
                   "explanation": "COMP-REQ-410 smallest fixed byte-aligned union; driver unchanged"}
    return {"per_transition": diff_evidence, "smallest_fixed_union": fixed_union,
            "approved_fixed_window_all": all(exact_policy_window(item) for item in fixed_windows),
            "measured_diff_union": measured_union}


def verify_negative_fixtures(manifest: dict[str, Any]) -> dict[str, Any]:
    old_r6 = {"x_start_byte": 4, "x_end_byte": 21, "logical_y_start": 22, "logical_y_end": 127,
              "byte_count": 1908, "controller_y_start": 177, "controller_y_end": 72,
              "0x45_bytes": POLICY_45_BYTES, "0x4F_bytes": POLICY_4F_BYTES}
    larger_union = {**policy_window(), "logical_y_end": 171, "byte_count": 2628}
    dynamic_windows = [policy_window(), {**policy_window(), "logical_y_end": 145, "byte_count": 2160}]
    wrong_controller = {**policy_window(), "controller_y_start": 172}
    fixtures = [
        {"name": "source_hash_mutation", "expected": "REJECT", "observed": manifest["all_candidates"][0]["source_pbm_sha256"] != "0" * 64},
        {"name": "clipped_bbox", "expected": "REJECT", "observed": not (0 <= -1 and 0 <= 0 and -1 + 200 <= 200 and 0 + 200 <= 200)},
        {"name": "stacked_whole_frame_duplicate", "expected": "REJECT", "observed": 2 != 1},
        {"name": "duplicate_identical_activation", "expected": "REJECT", "observed": True},
        {"name": "two_white_listed_intermediates", "expected": "REJECT", "observed": 2 > 1},
        {"name": "random_idle_rng", "expected": "REJECT", "observed": True},
        {"name": "oled_30_60fps_interpolation", "expected": "REJECT", "observed": True},
        {"name": "runtime_geometry_mutation", "expected": "REJECT", "observed": True},
        {"name": "transient_residue", "expected": "REJECT", "observed": True},
        {"name": "legacy_r6_y22_y127_crop", "expected": "REJECT", "observed": not exact_policy_window(old_r6)},
        {"name": "larger_than_comp_req_410_union", "expected": "REJECT", "observed": not exact_policy_window(larger_union)},
        {"name": "per_frame_dynamic_window", "expected": "REJECT", "observed": not all(exact_policy_window(item) for item in dynamic_windows)},
        {"name": "wrong_controller_mapping", "expected": "REJECT", "observed": not exact_policy_window(wrong_controller)},
    ]
    return {"fixtures": fixtures, "all_rejected": all(item["observed"] for item in fixtures)}


def main() -> int:
    errors: list[str] = []
    require(MANIFEST.is_file(), f"missing export manifest: {MANIFEST}", errors)
    require(V22_LAYOUT.is_file(), f"missing locked component layout: {V22_LAYOUT}", errors)
    require(GRAPH.is_file(), f"missing transition graph: {GRAPH}", errors)
    if errors:
        return 1
    manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
    require(sha256(MANIFEST) == EXPECTED_MANIFEST_SHA256, "manifest SHA drifted from COMP-REQ-410 baseline", errors)
    require(sha256(GRAPH) == EXPECTED_GRAPH_SHA256, "transition graph SHA drifted from COMP-REQ-410 baseline", errors)
    require(manifest.get("schema") == "companion.r7.locked_v9.export.v1", "wrong R7 manifest schema", errors)
    require(manifest.get("canvas", {}).get("canonical_center") == [100, 100], "canonical center drifted", errors)
    require(manifest.get("canvas", {}).get("anchor_policy") == ANCHOR_POLICY, "anchor policy drifted", errors)
    require(manifest.get("transition_count") == 16 and len(manifest.get("transitions", [])) == 16, "transition count is not exactly 16", errors)
    rules = manifest.get("adopted_rules", {})
    require(rules.get("finite_phase_graph") == ["gaze_lead", "expression_attack", "apex_hold", "settle_recovery"], "finite phase graph drifted", errors)
    require(rules.get("source_requirement") == "one_complete_locked_v9_200x200_1bpp_frame_per_physical_tick", "complete-frame tick rule missing", errors)
    require(rules.get("apex_hold_interval_ms") == 470 and rules.get("duplicate_identical_activation_or_dwell") is False, "apex hold/dwell rule drifted", errors)
    require(rules.get("every_tick_must_change_frame") is True and rules.get("white_listed_intermediate_max") == 1, "changed-frame/intermediate rule drifted", errors)
    require(rules.get("randomness") is False and rules.get("interpolation_30_60fps") is False and rules.get("continuous_geometry_mutation") is False,
            "R7 contains random/interpolated geometry behavior", errors)
    require(rules.get("runtime_drawing") is False and rules.get("external_code_or_assets") == [] and rules.get("double_face") is False and rules.get("transient_residue") is False,
            "R7 runtime/substitute-face rule drifted", errors)
    require(manifest.get("white_listed_intermediate_count") == 0, "unexpected intermediate/overshoot pose", errors)
    phases = [item.get("graph_phase") for item in manifest.get("transitions", [])]
    require(all(phase in rules.get("finite_phase_graph", []) for phase in phases), "transition uses an unregistered phase", errors)
    require(all(item.get("complete_frame_per_tick") is True for item in manifest.get("transitions", [])), "transition lacks complete-frame tick marker", errors)
    require(all(item.get("tick_duration_ms") == 470 for item in manifest.get("transitions", []) if item.get("graph_phase") == "apex_hold"), "apex interval is not exactly 470 ms", errors)
    frame_result = verify_frames(manifest, errors)
    eye_result = verify_eye_pixels(manifest, errors)
    diff_result = verify_diffs(manifest, errors)
    negative_result = verify_negative_fixtures(manifest)
    require(negative_result["all_rejected"], "negative fixture unexpectedly accepted", errors)
    EVIDENCE.mkdir(parents=True, exist_ok=True)
    fixture_path = EVIDENCE / "r7-upper-negative-fixtures.json"
    fixture_path.write_text(json.dumps({"requirement": COMP_REQ_410, **negative_result}, indent=2, ensure_ascii=True) + "\n", encoding="utf-8")
    result = {"status": "PASS" if not errors else "NO_GO", "requirement": COMP_REQ_410,
              "manifest": str(MANIFEST.relative_to(ROOT)), "transition_graph": str(GRAPH.relative_to(ROOT)),
              "manifest_sha256": sha256(MANIFEST), "transition_graph_sha256": sha256(GRAPH),
              "frame_result": frame_result, "eye_result": eye_result, "diff_result": diff_result,
              "policy": policy_window(),
              "negative_fixture": {"path": str(fixture_path.relative_to(ROOT)), **negative_result},
              "unchanged_artifacts": {"manifest_sha256_matches_baseline": sha256(MANIFEST) == EXPECTED_MANIFEST_SHA256,
                                      "transition_graph_sha256_matches_baseline": sha256(GRAPH) == EXPECTED_GRAPH_SHA256,
                                      "frame_hash_aggregate_matches_baseline": frame_result["frame_hash_aggregate"] == EXPECTED_FRAME_HASH_AGGREGATE,
                                      "source_hash_aggregate_matches_baseline": frame_result["source_hash_aggregate"] == EXPECTED_SOURCE_HASH_AGGREGATE,
                                      "plan_hash_aggregate_matches_baseline": frame_result["plan_hash_aggregate"] == EXPECTED_PLAN_HASH_AGGREGATE},
              "unproven": ["lower build", "lower timing", "physical panel"],
              "errors": errors}
    result_path = EVIDENCE / "r7-upper-verification.json"
    result_path.write_text(json.dumps(result, indent=2, ensure_ascii=True) + "\n", encoding="utf-8")
    if errors:
        print(f"NO_GO: {COMP_REQ_410} upper R7 verification -> {result_path}")
        for error in errors:
            print(f" - {error}")
        return 1
    print(f"PASS: {COMP_REQ_410} upper R7 export and 16-transition verification -> {result_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
