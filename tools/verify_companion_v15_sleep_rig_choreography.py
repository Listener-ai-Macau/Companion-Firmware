#!/usr/bin/env python3
"""Verify V15 source-mask sleep choreography and browser/target plan parity."""

from __future__ import annotations

import argparse
import hashlib
import json
import re
from pathlib import Path

from PIL import Image

from render_companion_v15_sleep_rig_choreography import CANVAS, PHASES, compose, load_request, offsets_for, selected_for, sha256, timeline_for


ROOT = Path(__file__).resolve().parents[1]
V15_ROOT = ROOT / "docs/art/iterations/companion-pet-expression-v9-extension-v15-sleep-rig-pose-source"
DEFAULT_CANDIDATE = V15_ROOT / "candidate/dynamic-proof-attempt-01"


def relative(path: Path) -> str:
    return path.resolve().relative_to(ROOT).as_posix()


def difference(left: Image.Image, right: Image.Image) -> int:
    if left.size != right.size:
        return -1
    return sum((a ^ b).bit_count() for a, b in zip(left.convert("1").tobytes(), right.convert("1").tobytes()))


def json_script(html: str, identifier: str) -> object:
    match = re.search(rf'<script id="{identifier}" type="application/json">(.*?)</script>', html, flags=re.S)
    if match is None:
        raise ValueError(f"preview misses {identifier}")
    return json.loads(match.group(1))


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--candidate", type=Path, default=DEFAULT_CANDIDATE)
    parser.add_argument("--write", type=Path, required=True)
    args = parser.parse_args()
    candidate = args.candidate.resolve()
    errors: list[str] = []
    phase_differences: dict[str, int] = {}
    choreography_audit: dict[str, object] = {}
    try:
        layout_path = candidate / "sleep-v15-component-choreography-layout.json"
        export_path = candidate / "export-report.json"
        layout = json.loads(layout_path.read_text(encoding="utf-8"))
        export = json.loads(export_path.read_text(encoding="utf-8"))
        if not isinstance(layout, dict) or layout.get("schema") != "companion.v15_sleep_component_choreography_layout.v1":
            errors.append("V15 dynamic layout schema drifted")
            layout = {}
        if layout.get("status") not in {"CANDIDATE_UNBOUND_DYNAMIC_PROOF_PENDING_OWNER_REVIEW",
                                        "CANDIDATE_UNBOUND_OWNER_DIRECTION_ACCEPTED_RUNTIME_INACTIVE"} or \
                layout.get("runtime_resource_activated") is not False or layout.get("active_candidate_binding") != "forbidden" or \
                layout.get("crig_mount") != "forbidden" or layout.get("full_pose_cell_playback") != "forbidden":
            errors.append("V15 dynamic layout has an illegal runtime disposition")
        if not isinstance(export, dict) or export.get("schema") != "companion.v15_sleep_component_choreography_export.v1" or \
                export.get("status") != "PASS_V15_UNBOUND_DYNAMIC_PROOF_EXPORT" or export.get("runtime_resource_activated") is not False or \
                export.get("active_candidate_binding") != "forbidden" or export.get("crig_mount") != "forbidden":
            errors.append("V15 dynamic export metadata drifted")
        request_path = ROOT / str(layout.get("source_request", ""))
        if not request_path.is_file() or layout.get("source_request_sha256") != sha256(request_path):
            errors.append("V15 choreography request drifted")
            request, source_components, slots = {}, {}, {}
        else:
            request, source_components, slots = load_request(request_path)
            expected_layout_status = "CANDIDATE_UNBOUND_OWNER_DIRECTION_ACCEPTED_RUNTIME_INACTIVE" if \
                request.get("status") == "OWNER_DYNAMIC_DIRECTION_ACCEPTED_RUNTIME_INACTIVE" else \
                "CANDIDATE_UNBOUND_DYNAMIC_PROOF_PENDING_OWNER_REVIEW"
            if layout.get("status") != expected_layout_status:
                errors.append("V15 dynamic layout owner disposition drifted")
        source_layout_path = ROOT / str(layout.get("source_component_layout", ""))
        if not source_layout_path.is_file() or layout.get("source_component_layout_sha256") != sha256(source_layout_path):
            errors.append("V15 component source layout drifted")
            source_layout = {}
        else:
            source_layout = json.loads(source_layout_path.read_text(encoding="utf-8"))
        source_rows = source_layout.get("components", []) if isinstance(source_layout, dict) else []
        layout_rows = layout.get("components", []) if isinstance(layout.get("components"), list) else []
        source_map = {row.get("name"): row for row in source_rows if isinstance(row, dict)}
        layout_map = {row.get("name"): row for row in layout_rows if isinstance(row, dict)}
        if set(source_map) != set(source_components) or set(layout_map) != set(source_components):
            errors.append("V15 dynamic component vocabulary drifted")
        for name, source in source_components.items():
            row, expected = layout_map.get(name), source_map.get(name)
            if not isinstance(row, dict) or not isinstance(expected, dict) or any(row.get(key) != expected.get(key) for key in ("mask", "mask_sha256", "preview_mask", "base_position", "mask_size", "z_index", "source_sheet", "source_sheet_sha256")):
                errors.append(f"V15 dynamic component is not the exact V15 source mask: {name}")
        phase_plan = layout.get("phase_plan") if isinstance(layout.get("phase_plan"), list) else []
        request_steps = request.get("phases") if isinstance(request, dict) and isinstance(request.get("phases"), list) else []
        if [row.get("phase") for row in phase_plan if isinstance(row, dict)] != list(PHASES) or len(request_steps) != len(PHASES):
            errors.append("V15 dynamic phase order drifted")
        rendered_frames: list[Image.Image] = []
        phase_selections: dict[str, list[str]] = {}
        for index, phase in enumerate(PHASES):
            row = phase_plan[index] if index < len(phase_plan) and isinstance(phase_plan[index], dict) else {}
            step = request_steps[index] if index < len(request_steps) and isinstance(request_steps[index], dict) else {}
            if row.get("phase") != phase or step.get("phase") != phase or not isinstance(row.get("duration_ms"), int):
                errors.append(f"V15 phase contract drifted: {phase}")
                continue
            try:
                selected = selected_for(step, slots)
                offsets = offsets_for(request, step, selected)
                if row.get("active_components") != selected or row.get("offsets") != {name: list(value) for name, value in offsets.items()}:
                    errors.append(f"V15 phase plan drifted: {phase}")
                pbm = ROOT / str(row.get("target_pbm", ""))
                if not pbm.is_file() or row.get("target_pbm_sha256") != sha256(pbm):
                    errors.append(f"V15 target PBM is missing or drifted: {phase}")
                    continue
                rendered = compose(source_components, selected, offsets)
                actual = Image.open(pbm).convert("1")
                if actual.size != CANVAS or difference(rendered, actual) != 0:
                    errors.append(f"V15 target PBM is not composed from the registered plan: {phase}")
                rendered_frames.append(actual)
                phase_selections[phase] = selected
            except (OSError, ValueError, KeyError) as exc:
                errors.append(f"V15 phase verification failed: {phase}: {exc}")
        expected_timeline = timeline_for(request, slots) if request.get("schema") == "companion.v15_sleep_rig_component_choreography_request.v2" else []
        timeline_plan = layout.get("timeline_plan") if isinstance(layout.get("timeline_plan"), list) else []
        if expected_timeline:
            timeline_fields = ("frame_index", "frame_id", "phase", "sample_index", "sample_count", "duration_ms", "active_components", "offsets")
            if layout.get("timeline_mode") != "stepwise_component_tracks" or \
                    [{field: row.get(field) for field in timeline_fields} for row in timeline_plan if isinstance(row, dict)] != expected_timeline:
                errors.append("V15 v2 component timeline drifted")
            if len(timeline_plan) != len(expected_timeline):
                errors.append("V15 v2 component timeline frame count drifted")
            for row in timeline_plan:
                if not isinstance(row, dict):
                    errors.append("V15 v2 component timeline contains an invalid record")
                    continue
                try:
                    selected = [str(name) for name in row.get("active_components", [])]
                    offsets = {name: tuple(value) for name, value in row.get("offsets", {}).items()}
                    pbm = ROOT / str(row.get("target_pbm", ""))
                    if not pbm.is_file() or row.get("target_pbm_sha256") != sha256(pbm):
                        errors.append(f"V15 v2 timeline PBM is missing or drifted: {row.get('frame_id')}")
                        continue
                    actual = Image.open(pbm).convert("1")
                    if actual.size != CANVAS or difference(compose(source_components, selected, offsets), actual) != 0:
                        errors.append(f"V15 v2 timeline PBM is not composed from the registered plan: {row.get('frame_id')}")
                except (OSError, ValueError, KeyError, TypeError) as exc:
                    errors.append(f"V15 v2 timeline verification failed: {row.get('frame_id')}: {exc}")
        if len(rendered_frames) == len(PHASES):
            entry = rendered_frames[0]
            phase_differences = {phase: difference(entry, frame) for phase, frame in zip(PHASES, rendered_frames)}
            if phase_differences.get("lead", 0) <= 0 or phase_differences.get("response", 0) <= 80 or \
                    phase_differences.get("hold", 0) <= 120 or phase_differences.get("settle") != 0:
                errors.append("V15 choreography lacks the required source-mask phase changes")
            if len({hashlib.sha256(frame.tobytes()).hexdigest() for frame in rendered_frames}) < 6:
                errors.append("V15 choreography does not contain enough unique component compositions")
            reassembly = source_layout.get("reassembly", {}) if isinstance(source_layout, dict) else {}
            rest_path = ROOT / str(reassembly.get("reassembled", "")) if isinstance(reassembly, dict) else Path()
            if not rest_path.is_file() or difference(entry, Image.open(rest_path).convert("1")) != 0 or \
                    difference(rendered_frames[-1], Image.open(rest_path).convert("1")) != 0:
                errors.append("V15 entry/settle do not exactly reassemble the base sleep mask source")
        readability = request.get("motion_readability") if isinstance(request, dict) else None
        readability_audit: dict[str, object] = {}
        if isinstance(readability, dict):
            first_phase = readability.get("first_visible_phase")
            max_ms = readability.get("max_entry_to_first_visible_ms")
            min_response = readability.get("min_response_difference_pixels")
            min_accent = readability.get("min_accent_difference_pixels")
            min_travel = readability.get("min_secondary_travel_px")
            elapsed = 0
            for step in request_steps:
                if not isinstance(step, dict):
                    continue
                if step.get("phase") == first_phase:
                    break
                elapsed += int(step.get("duration_ms", 0))
            if first_phase not in PHASES or not isinstance(max_ms, int) or elapsed > max_ms:
                errors.append("V15 v2 does not reach its first visible phase quickly enough")
            if not isinstance(min_response, int) or phase_differences.get("response", 0) < min_response or \
                    not isinstance(min_accent, int) or phase_differences.get("accent", 0) < min_accent:
                errors.append("V15 v2 does not meet the required readable frame differences")
            breath_values: list[tuple[int, int]] = []
            zzz_values: list[tuple[int, int]] = []
            for step in request_steps:
                if isinstance(step, dict):
                    selected = selected_for(step, slots)
                    offsets = offsets_for(request, step, selected)
                    breath_values.append(offsets["sleep_breath_mark_left"])
                    zzz_values.append(offsets["sleep_zzz_cluster"])
            breath_travel = max(y for _, y in breath_values) - min(y for _, y in breath_values) if breath_values else 0
            zzz_travel = max(abs(x) + abs(y) for x, y in zzz_values) if zzz_values else 0
            if not isinstance(min_travel, int) or breath_travel < min_travel or zzz_travel < min_travel:
                errors.append("V15 v2 secondary pulse does not traverse the required visible range")
            readability_audit = {"first_visible_phase": first_phase, "entry_to_first_visible_ms": elapsed,
                                 "response_difference_pixels": phase_differences.get("response", 0),
                                 "accent_difference_pixels": phase_differences.get("accent", 0),
                                 "breath_travel_px": breath_travel, "zzz_travel_px": zzz_travel}
        anchors = {"left_closed_eye_anchor", "right_closed_eye_anchor", "nose_anchor"}
        lower_variants = {"left_cheek_breath", "right_cheek_breath", "mouth_breath"}
        for phase, selected in phase_selections.items():
            if not anchors.issubset(set(selected)):
                errors.append(f"V15 anchored sleep identity is incomplete: {phase}")
        if "left_brow_settle" not in phase_selections.get("lead", []) or "left_brow_settle" in phase_selections.get("entry", []):
            errors.append("V15 brow lead is not a source-mask variant transition")
        for phase in ("response", "accent"):
            if not lower_variants.issubset(set(phase_selections.get(phase, []))):
                errors.append(f"V15 lower-face response lacks source-mask variants: {phase}")
        if lower_variants & set(phase_selections.get("hold", [])):
            errors.append("V15 hold does not settle the lower face back to the anchor")
        secondary = {"sleep_breath_mark_left", "sleep_breath_mark_right", "sleep_zzz_cluster"}
        for step in request_steps:
            if isinstance(step, dict):
                selected = selected_for(step, slots)
                offsets = offsets_for(request, step, selected)
                if any(offset != (0, 0) for name, offset in offsets.items() if name not in secondary):
                    errors.append(f"V15 applies an illegal positional offset to a facial component: {step.get('phase')}")
        choreography_audit = {"anchors": sorted(anchors), "lead_variant": "left_brow_settle",
                               "lower_face_variants": sorted(lower_variants), "phase_active_components": phase_selections}
        audit_info = layout.get("artifacts", {}).get("component_occlusion_audit", {}) if isinstance(layout.get("artifacts"), dict) else {}
        audit_path = ROOT / str(audit_info.get("path", "")) if isinstance(audit_info, dict) else Path()
        if not audit_path.is_file() or audit_info.get("sha256") != sha256(audit_path):
            errors.append("V15 component occlusion audit drifted")
        else:
            audit = json.loads(audit_path.read_text(encoding="utf-8"))
            expected_audit_count = len(expected_timeline) if expected_timeline else len(PHASES)
            if audit.get("status") != "PASS_ZERO_COMPONENT_OVERLAP" or audit.get("frame_count") != expected_audit_count or \
                    not isinstance(audit.get("frames"), list) or len(audit["frames"]) != expected_audit_count or \
                    any(frame.get("overlap_pixels") != 0 for frame in audit.get("frames", []) if isinstance(frame, dict)):
                errors.append("V15 dynamic source masks overlap in a phase")
        if expected_timeline:
            dynamic_apng = layout.get("artifacts", {}).get("dynamic_apng", {}) if isinstance(layout.get("artifacts"), dict) else {}
            apng_path = ROOT / str(dynamic_apng.get("path", "")) if isinstance(dynamic_apng, dict) else Path()
            if not apng_path.is_file() or dynamic_apng.get("sha256") != sha256(apng_path) or dynamic_apng.get("frame_count") != len(expected_timeline):
                errors.append("V15 v2 dynamic APNG evidence drifted")
            else:
                with Image.open(apng_path) as image:
                    if getattr(image, "n_frames", 1) != len(expected_timeline):
                        errors.append("V15 v2 dynamic APNG does not contain the target component timeline")
                    if dynamic_apng.get("playback_mode") != request.get("component_timeline", {}).get("playback_mode") or \
                            image.info.get("loop") != (1 if request.get("component_timeline", {}).get("playback_mode") == "one_shot_then_static" else 0):
                        errors.append("V15 v2 dynamic APNG playback mode drifted")
        preview = candidate / "preview.html"
        if not preview.is_file():
            errors.append("V15 browser preview is missing")
        else:
            html = preview.read_text(encoding="utf-8")
            browser_components = json_script(html, "component-plan")
            browser_phases = json_script(html, "phase-plan")
            try:
                browser_timeline = json_script(html, "timeline-plan")
            except ValueError:
                browser_timeline = None
            try:
                browser_playback = json_script(html, "playback-mode")
            except ValueError:
                browser_playback = None
            expected_components = [{"name": row["name"], "src": "../component-export-attempt-01/preview-layers/" + Path(str(row["preview_mask"])).name,
                                    "x": row["base_position"][0], "y": row["base_position"][1], "width": row["mask_size"][0],
                                    "height": row["mask_size"][1], "z": row["z_index"]}
                                   for row in layout_rows if isinstance(row, dict)]
            expected_phases = [{"phase": row["phase"], "duration_ms": row["duration_ms"],
                                "active_components": row["active_components"], "offsets": row["offsets"]}
                               for row in phase_plan if isinstance(row, dict)]
            if browser_components != expected_components or browser_phases != expected_phases or \
                    "normalized-source-poses" in html or "target-frames" in html or ".cemp" in html:
                errors.append("V15 browser does not use the same component/phase plan as the target")
            if expected_timeline:
                expected_browser_timeline = [{"frame_id": row["frame_id"], "phase": row["phase"],
                                              "sample_index": row["sample_index"], "sample_count": row["sample_count"],
                                              "duration_ms": row["duration_ms"], "active_components": row["active_components"],
                                              "offsets": row["offsets"]} for row in timeline_plan if isinstance(row, dict)]
                if browser_timeline != expected_browser_timeline:
                    errors.append("V15 v2 browser does not replay the target component timeline")
                if browser_playback != request.get("component_timeline", {}).get("playback_mode") or \
                        layout.get("playback_mode") != browser_playback or \
                        (browser_playback == "one_shot_then_static" and 'playbackMode!=="loop"' not in html):
                    errors.append("V15 v2 browser playback mode does not match the target timeline")
            elif browser_timeline not in (None, [], browser_phases) or browser_playback not in (None, "loop"):
                errors.append("V15 v1 browser timeline drifted")
        if expected_timeline:
            capture_path = candidate / "browser-capture-report.json"
            if not capture_path.is_file():
                errors.append("V15 v2 browser capture is missing")
            else:
                capture = json.loads(capture_path.read_text(encoding="utf-8"))
                if capture.get("status") != "PASS_V15_SLEEP_COMPONENT_CHOREOGRAPHY_BROWSER_CAPTURE" or \
                        capture.get("playback_mode") != "one_shot_then_static" or \
                        capture.get("default_settle_phase") != "settle-01-of-01":
                    errors.append("V15 v2 browser did not prove one-shot-then-static playback")
        if list(candidate.rglob("*.crig")) or list(candidate.rglob("*.cemp")):
            errors.append("V15 unbound choreography illegally produced a runtime asset")
    except (OSError, ValueError, json.JSONDecodeError, KeyError) as exc:
        errors.append(str(exc))
    result = {"schema": "companion.v15_sleep_component_choreography_gate.v1",
              "status": "PASS_V15_UNBOUND_DYNAMIC_PROOF_GATE" if not errors else "FAIL_V15_UNBOUND_DYNAMIC_PROOF_GATE",
              "candidate": relative(candidate), "phase_count": len(PHASES), "entry_pixel_difference_by_phase": phase_differences,
              "runtime_resource_activated": False, "active_candidate_binding": "forbidden", "crig_mount": "forbidden",
              "full_pose_cell_playback": "forbidden", "component_choreography_audit": choreography_audit,
              "request_status": request.get("status") if isinstance(request, dict) else None,
              "playback_mode": request.get("component_timeline", {}).get("playback_mode") if isinstance(request, dict) and isinstance(request.get("component_timeline"), dict) else None,
              "motion_readability_audit": readability_audit, "errors": errors}
    args.write.parent.mkdir(parents=True, exist_ok=True)
    args.write.write_text(json.dumps(result, indent=2) + "\n", encoding="ascii")
    if errors:
        for error in errors:
            print(f"ERROR: {error}")
        return 1
    print("PASS: V15 browser and target share one source-mask-only choreography plan.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
