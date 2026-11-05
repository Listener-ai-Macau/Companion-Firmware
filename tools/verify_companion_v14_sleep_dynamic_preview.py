#!/usr/bin/env python3
"""Verify V14's unbound source-mask sleep dynamics and browser-plan parity."""

from __future__ import annotations

import argparse
import hashlib
import json
import re
from pathlib import Path

from PIL import Image

from render_companion_v14_sleep_dynamic_preview import CANVAS, COMPONENTS, PHASES, compose, offsets_for, sha256


ROOT = Path(__file__).resolve().parents[1]
V14_ROOT = ROOT / "docs/art/iterations/companion-pet-expression-v9-extension-v14-sleep-zzz-component-repair"
DEFAULT_CANDIDATE = V14_ROOT / "candidate/dynamic-proof"


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


def verify_anchored_relative_motion(request: dict[str, object], request_steps: list[object], errors: list[str]) -> dict[str, object]:
    contract = request.get("motion_contract")
    if not isinstance(contract, dict) or contract.get("kind") != "anchored_relative_motion_v1":
        return {}
    anchors = contract.get("static_anchor_components")
    groups = contract.get("facial_groups")
    phase_groups = contract.get("phase_facial_group")
    if not isinstance(anchors, list) or not isinstance(groups, dict) or not isinstance(phase_groups, dict):
        errors.append("V14 anchored choreography contract is malformed")
        return {}
    facial = ("left_brow", "right_brow", "left_closed_eye", "right_closed_eye", "left_cheek", "right_cheek", "nose", "mouth")
    histories = {name: [] for name in facial}
    phase_rows: list[dict[str, object]] = []
    for index, phase in enumerate(PHASES):
        step = request_steps[index] if index < len(request_steps) and isinstance(request_steps[index], dict) else {}
        try:
            offsets = offsets_for(request, step)
        except (KeyError, ValueError) as exc:
            errors.append(f"V14 anchored choreography offset read failed: {phase}: {exc}")
            continue
        for name in facial:
            histories[name].append(offsets[name])
        active = {name for name in facial if offsets[name] != (0, 0)}
        group_name = phase_groups.get(phase)
        allowed = set(groups.get(group_name, [])) if isinstance(group_name, str) else set()
        if group_name is not None and (not isinstance(group_name, str) or not allowed):
            errors.append(f"V14 anchored choreography names an invalid facial group: {phase}")
        if not active.issubset(allowed):
            errors.append(f"V14 anchored choreography moves more than its declared local facial group: {phase}")
        if len({name for name, members in groups.items() if isinstance(members, list) and active & set(members)}) > int(contract.get("max_active_facial_groups_per_phase", 1)):
            errors.append(f"V14 anchored choreography activates too many facial groups: {phase}")
        if contract.get("forbid_shared_nonzero_facial_translation") is True and active and len(active) == len(facial) and len({offsets[name] for name in facial}) == 1:
            errors.append(f"V14 anchored choreography translates the facial set as one card: {phase}")
        phase_rows.append({"phase": phase, "declared_facial_group": group_name, "active_facial_components": sorted(active)})
    for name in anchors:
        if name not in histories or any(offset != (0, 0) for offset in histories[name]):
            errors.append(f"V14 anchored choreography moves a required facial anchor: {name}")
    distinct = len({tuple(values) for values in histories.values()})
    minimum = contract.get("min_distinct_facial_histories")
    if not isinstance(minimum, int) or distinct < minimum:
        errors.append("V14 anchored choreography lacks distinct local component histories")
    return {"contract": "anchored_relative_motion_v1", "static_anchor_components": anchors,
            "distinct_facial_histories": distinct, "phase_groups": phase_rows,
            "histories": {name: [list(offset) for offset in values] for name, values in histories.items()}}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--candidate", type=Path, default=DEFAULT_CANDIDATE)
    parser.add_argument("--write", type=Path, required=True)
    args = parser.parse_args()
    candidate = args.candidate.resolve()
    errors: list[str] = []
    layout_path = candidate / "sleep-v14-dynamic-layout.json"
    export_path = candidate / "export-report.json"
    try:
        layout = json.loads(layout_path.read_text(encoding="utf-8"))
        export = json.loads(export_path.read_text(encoding="utf-8"))
        if not isinstance(layout, dict) or layout.get("schema") != "companion.v14_sleep_zzz_unbound_dynamic_layout.v1":
            errors.append("V14 dynamic layout schema drifted")
            layout = {}
        if layout.get("status") != "CANDIDATE_UNBOUND_DYNAMIC_PROOF_PENDING_OWNER_REVIEW" or \
                layout.get("runtime_resource_activated") is not False or layout.get("active_candidate_binding") != "forbidden" or \
                layout.get("crig_mount") != "forbidden" or layout.get("full_face_source_card_playback") != "forbidden":
            errors.append("V14 dynamic layout has an illegal runtime disposition")
        if not isinstance(export, dict) or export.get("status") != "PASS_V14_UNBOUND_DYNAMIC_PROOF_EXPORT" or \
                export.get("runtime_resource_activated") is not False or export.get("active_candidate_binding") != "forbidden" or \
                export.get("crig_mount") != "forbidden":
            errors.append("V14 dynamic export metadata drifted")
        request_path = ROOT / str(layout.get("source_request", ""))
        static_path = ROOT / str(layout.get("source_static_layout", ""))
        if not request_path.is_file() or layout.get("source_request_sha256") != sha256(request_path):
            errors.append("V14 dynamic request drifted")
            request = {}
        else:
            request = json.loads(request_path.read_text(encoding="utf-8"))
        if not static_path.is_file() or layout.get("source_static_layout_sha256") != sha256(static_path):
            errors.append("V14 static source layout drifted")
            static = {}
        else:
            static = json.loads(static_path.read_text(encoding="utf-8"))
        static_components = {row.get("name"): row for row in static.get("components", []) if isinstance(row, dict)} if isinstance(static, dict) else {}
        components = layout.get("components") if isinstance(layout.get("components"), list) else []
        component_map = {row.get("name"): row for row in components if isinstance(row, dict)}
        if tuple(component_map) != COMPONENTS or tuple(static_components) != COMPONENTS:
            errors.append("V14 dynamic component vocabulary drifted")
        for name in COMPONENTS:
            row, source = component_map.get(name), static_components.get(name)
            if not isinstance(row, dict) or not isinstance(source, dict) or any(row.get(key) != source.get(key) for key in ("mask", "mask_sha256", "preview_mask", "base_position", "mask_size", "z_index", "source_sheet", "source_sheet_sha256")):
                errors.append(f"V14 dynamic component is not the exact V14 source mask: {name}")
        phase_plan = layout.get("phase_plan") if isinstance(layout.get("phase_plan"), list) else []
        request_steps = request.get("phases") if isinstance(request, dict) and isinstance(request.get("phases"), list) else []
        if [row.get("phase") for row in phase_plan if isinstance(row, dict)] != list(PHASES) or len(request_steps) != len(PHASES):
            errors.append("V14 dynamic phase order drifted")
        rendered_frames: list[Image.Image] = []
        phase_differences: dict[str, int] = {}
        for index, phase in enumerate(PHASES):
            row = phase_plan[index] if index < len(phase_plan) and isinstance(phase_plan[index], dict) else {}
            step = request_steps[index] if index < len(request_steps) and isinstance(request_steps[index], dict) else {}
            if row.get("phase") != phase or step.get("phase") != phase or row.get("visible_components") != list(COMPONENTS) or \
                    step.get("visible_components") != "all_registered_v14_masks" or not isinstance(row.get("duration_ms"), int):
                errors.append(f"V14 phase contract drifted: {phase}")
                continue
            try:
                offsets = offsets_for(request, step)
                if row.get("offsets") != {name: list(value) for name, value in offsets.items()}:
                    errors.append(f"V14 phase offsets drifted: {phase}")
                pbm = ROOT / str(row.get("target_pbm", ""))
                if not pbm.is_file() or row.get("target_pbm_sha256") != sha256(pbm):
                    errors.append(f"V14 target PBM is missing or drifted: {phase}")
                    continue
                rendered = compose(component_map, offsets)
                actual = Image.open(pbm).convert("1")
                if actual.size != CANVAS or difference(rendered, actual) != 0:
                    errors.append(f"V14 target PBM is not composed from the registered plan: {phase}")
                rendered_frames.append(actual)
            except (OSError, ValueError, KeyError) as exc:
                errors.append(f"V14 phase verification failed: {phase}: {exc}")
        if len(rendered_frames) == len(PHASES):
            entry = rendered_frames[0]
            phase_differences = {phase: difference(entry, frame) for phase, frame in zip(PHASES, rendered_frames)}
            if phase_differences["lead"] <= 0 or phase_differences["hold"] <= 80 or phase_differences["settle"] != 0:
                errors.append("V14 dynamic proof lacks the required visible lead/hold/settle motion")
            if len({hashlib.sha256(frame.tobytes()).hexdigest() for frame in rendered_frames}) < 6:
                errors.append("V14 dynamic proof does not contain enough unique component compositions")
            normalized = ROOT / str(static.get("normalization", {}).get("normalized", "")) if isinstance(static, dict) else Path()
            if not normalized.is_file() or difference(entry, Image.open(normalized).convert("1")) != 0 or \
                    difference(rendered_frames[-1], Image.open(normalized).convert("1")) != 0:
                errors.append("V14 entry/settle do not exactly reassemble the static source")
        relation_audit: dict[str, object] = {}
        if isinstance(request, dict):
            histories = {name: [] for name in ("sleep_breath_dot_left", "sleep_breath_dot_right", "sleep_z_small", "sleep_z_medium", "sleep_z_large")}
            for step in request_steps:
                if isinstance(step, dict):
                    offsets = offsets_for(request, step)
                    for name in histories:
                        histories[name].append(offsets[name])
            if any(len(set(values)) < 3 for name, values in histories.items() if name.startswith("sleep_breath")):
                errors.append("V14 breath dots do not perform a restrained multi-step breath")
            for name in ("sleep_z_small", "sleep_z_medium", "sleep_z_large"):
                values = histories[name]
                if not any(x > 0 and y < 0 for x, y in values):
                    errors.append(f"V14 {name} does not rise outward")
            relation_audit = verify_anchored_relative_motion(request, request_steps, errors)
        audit_info = layout.get("artifacts", {}).get("component_occlusion_audit", {}) if isinstance(layout.get("artifacts"), dict) else {}
        audit_path = ROOT / str(audit_info.get("path", "")) if isinstance(audit_info, dict) else Path()
        if not audit_path.is_file() or audit_info.get("sha256") != sha256(audit_path):
            errors.append("V14 component-occlusion audit drifted")
        else:
            audit = json.loads(audit_path.read_text(encoding="utf-8"))
            if audit.get("status") != "PASS_ZERO_COMPONENT_OVERLAP" or audit.get("frame_count") != 7 or \
                    any(frame.get("overlap_pixels") != 0 for frame in audit.get("frames", []) if isinstance(frame, dict)):
                errors.append("V14 dynamic source masks overlap in a phase")
        preview = candidate / "preview.html"
        if not preview.is_file():
            errors.append("V14 browser preview is missing")
        else:
            html = preview.read_text(encoding="utf-8")
            browser_components = json_script(html, "component-plan")
            browser_phases = json_script(html, "phase-plan")
            expected_browser = [{"name": row["name"], "src": "../preview-layers/" + Path(str(row["preview_mask"])).name,
                                 "x": row["base_position"][0], "y": row["base_position"][1], "width": row["mask_size"][0],
                                 "height": row["mask_size"][1], "z": row["z_index"]} for row in components if isinstance(row, dict)]
            expected_browser_phases = [{"phase": row["phase"], "duration_ms": row["duration_ms"],
                                        "visible_components": row["visible_components"], "offsets": row["offsets"]}
                                       for row in phase_plan if isinstance(row, dict)]
            if browser_components != expected_browser or browser_phases != expected_browser_phases or \
                    "target-frames" in html or "sleep-v14-dynamic-contact-sheet" in html:
                errors.append("V14 browser does not use the same component/phase plan as the target")
        if list(candidate.glob("*.crig")) or list(candidate.rglob("*.crig")):
            errors.append("V14 unbound dynamic proof illegally produced a CRIG asset")
    except (OSError, ValueError, json.JSONDecodeError, KeyError) as exc:
        errors.append(str(exc))
    result = {"schema": "companion.v14_sleep_zzz_unbound_dynamic_proof_gate.v1",
              "status": "PASS_V14_UNBOUND_DYNAMIC_PROOF_GATE" if not errors else "FAIL_V14_UNBOUND_DYNAMIC_PROOF_GATE",
              "candidate": relative(candidate), "phase_count": len(PHASES), "component_count": len(COMPONENTS),
              "entry_pixel_difference_by_phase": phase_differences, "runtime_resource_activated": False,
              "active_candidate_binding": "forbidden", "crig_mount": "forbidden", "full_face_source_card_playback": "forbidden",
              "anchored_relative_motion_audit": relation_audit, "errors": errors}
    args.write.parent.mkdir(parents=True, exist_ok=True)
    args.write.write_text(json.dumps(result, indent=2) + "\n", encoding="ascii")
    if errors:
        for error in errors:
            print(f"ERROR: {error}")
        return 1
    print("PASS: V14 browser and target share one source-mask-only seven-phase dynamic plan.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
