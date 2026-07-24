#!/usr/bin/env python3
"""Close the machine gate for a V9 face-source plus secondary-detail art bundle."""

from __future__ import annotations

import argparse
import hashlib
import json
import pathlib
from typing import Any


ROOT = pathlib.Path(__file__).resolve().parents[1]
LOCKED_V9_HASH = "919F344957661DEF2099AD56AB1286CCA9DBA4D8F08B702617B6DF5B1A28E9DA"
EXPECTED_STATES = (
    "daily_attention_left", "daily_attention_right", "daily_attention_up", "daily_attention_down",
    "calm_content", "curious_question", "alert_surprised", "joyful_spark",
    "affectionate_warm", "playful_bright", "anticipatory_notice", "puzzled_processing",
    "recording_focus", "listening_focus", "menu_thinking", "sleep_rest_no_moon",
)
EXPECTED_DETAILS = (
    "cheek_detail_left", "cheek_detail_right", "cheek_dot_pair", "charm_sparkle",
    "charm_heart", "charm_question", "charm_exclamation", "detail_listening_arcs",
)


def load_json(path: pathlib.Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError(f"{path} must contain a JSON object")
    return value


def sha256(path: pathlib.Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest().upper()


def rel(path: pathlib.Path) -> str:
    return path.resolve().relative_to(ROOT).as_posix()


def repo_path(value: object, errors: list[str], label: str) -> pathlib.Path | None:
    if not isinstance(value, str) or not value:
        errors.append(f"{label} is missing")
        return None
    path = (ROOT / value).resolve()
    try:
        path.relative_to(ROOT)
    except ValueError:
        errors.append(f"{label} escapes the repository")
        return None
    if not path.is_file():
        errors.append(f"{label} is missing: {value}")
        return None
    return path


def verify_face_source(
    source: dict[str, Any],
    index: int,
    manifest: dict[str, Any],
    errors: list[str],
) -> dict[str, Any]:
    candidate_path = repo_path(source.get("candidate"), errors, f"face source {index} candidate")
    request_path = repo_path(source.get("request"), errors, f"face source {index} request")
    expected_hash = str(source.get("sha256", "")).upper()
    if candidate_path is not None and sha256(candidate_path) != expected_hash:
        errors.append(f"face source {index} candidate hash drifted")
    states = source.get("states")
    if request_path is not None:
        request = load_json(request_path)
        if request.get("planned_generated_output") != source.get("candidate"):
            errors.append(f"face source {index} request output drifted")
        if tuple(request.get("required_cells", [])) != tuple(states if isinstance(states, list) else []):
            errors.append(f"face source {index} state mapping drifted")
        if str(request.get("render_parent_iteration", "")) != str(manifest.get("render_parent_iteration", "")):
            errors.append(f"face source {index} does not share the locked V9 parent iteration")
    reports = source.get("machine_reports")
    if not isinstance(reports, dict):
        errors.append(f"face source {index} report map is malformed")
    else:
        expected_second_key = "daily_attention_readability" if index == 0 else "expanded_emotion_panel"
        expected_second_status = "PASS_DAILY_ATTENTION_PROOF_GATE" if index == 0 else "PASS_EXPANDED_EMOTION_PANEL_GATE"
        eye_path = repo_path(reports.get("open_eye_identity"), errors, f"face source {index} eye report")
        second_path = repo_path(reports.get(expected_second_key), errors, f"face source {index} secondary report")
        if eye_path is not None:
            eye_report = load_json(eye_path)
            if eye_report.get("status") != "PASS_OPEN_EYE_IDENTITY_GATE" or eye_report.get("candidate_sha256") != expected_hash:
                errors.append(f"face source {index} eye report does not prove the declared candidate")
        if second_path is not None:
            second_report = load_json(second_path)
            if second_report.get("status") != expected_second_status or second_report.get("candidate_sha256") != expected_hash:
                errors.append(f"face source {index} secondary report does not prove the declared candidate")
    return {
        "iteration_id": source.get("iteration_id"),
        "candidate": source.get("candidate"),
        "sha256": expected_hash,
        "states": states,
    }


def verify_detail_source(source: dict[str, Any], manifest: dict[str, Any], errors: list[str]) -> dict[str, Any]:
    candidate_path = repo_path(source.get("candidate"), errors, "detail source candidate")
    request_path = repo_path(source.get("request"), errors, "detail source request")
    expected_hash = str(source.get("sha256", "")).upper()
    components = source.get("components")
    if candidate_path is not None and sha256(candidate_path) != expected_hash:
        errors.append("detail source candidate hash drifted")
    if request_path is not None:
        request = load_json(request_path)
        if request.get("source_art_type") != "detail_component_kit":
            errors.append("detail source request is not an isolated detail component kit")
        if request.get("planned_generated_output") != source.get("candidate"):
            errors.append("detail source request output drifted")
        if tuple(request.get("required_cells", [])) != tuple(components if isinstance(components, list) else []):
            errors.append("detail source component mapping drifted")
        if str(request.get("render_parent_iteration", "")) != str(manifest.get("render_parent_iteration", "")):
            errors.append("detail source does not share the locked V9 parent iteration")
    reports = source.get("machine_reports")
    if not isinstance(reports, dict):
        errors.append("detail source report map is malformed")
    else:
        report_path = repo_path(reports.get("detail_component_kit"), errors, "detail source machine report")
        if report_path is not None:
            report = load_json(report_path)
            if report.get("status") != "PASS_DETAIL_COMPONENT_KIT_GATE" or report.get("candidate_sha256") != expected_hash:
                errors.append("detail source report does not prove the declared candidate")
    return {
        "iteration_id": source.get("iteration_id"),
        "candidate": source.get("candidate"),
        "sha256": expected_hash,
        "components": components,
    }


def verify(manifest_path: pathlib.Path) -> dict[str, Any]:
    errors: list[str] = []
    manifest = load_json(manifest_path)
    locked = manifest.get("locked_v9_source")
    if not isinstance(locked, dict) or str(locked.get("sha256", "")).upper() != LOCKED_V9_HASH:
        errors.append("full source bundle is not locked to the immutable V9 parent hash")
    if tuple(manifest.get("all_required_states", [])) != EXPECTED_STATES:
        errors.append("full source bundle does not enumerate the complete ordered sixteen-state program")
    if tuple(manifest.get("all_required_secondary_components", [])) != EXPECTED_DETAILS:
        errors.append("full source bundle does not enumerate the complete ordered secondary-detail vocabulary")
    if manifest.get("runtime_resource_activated") is not False or manifest.get("component_export_eligible") is not False:
        errors.append("full source bundle is not explicitly inactive before owner art review")
    if manifest.get("full_face_source_card_playback") != "forbidden":
        errors.append("full source bundle permits forbidden full-face source-card playback")
    face_sources = manifest.get("face_sources")
    if not isinstance(face_sources, list) or len(face_sources) != 2:
        errors.append("full source bundle must contain exactly two face-source sheets")
        face_sources = []
    source_evidence: list[dict[str, Any]] = []
    collected_states: list[str] = []
    for index, source in enumerate(face_sources):
        if not isinstance(source, dict):
            errors.append(f"face source {index} is malformed")
            continue
        source_evidence.append(verify_face_source(source, index, manifest, errors))
        states = source.get("states")
        if isinstance(states, list):
            collected_states.extend(str(state) for state in states)
        else:
            errors.append(f"face source {index} states are malformed")
    if tuple(collected_states) != EXPECTED_STATES:
        errors.append("face sources do not provide the exact complete sixteen-state bundle")
    detail_source = manifest.get("detail_source")
    detail_evidence: dict[str, Any] | None = None
    if not isinstance(detail_source, dict):
        errors.append("full source bundle detail source is malformed")
    else:
        detail_evidence = verify_detail_source(detail_source, manifest, errors)
        if tuple(detail_source.get("components", [])) != EXPECTED_DETAILS:
            errors.append("detail source does not provide the exact secondary-detail vocabulary")
    return {
        "schema": "companion.v9_full_expression_source_bundle_gate.v1",
        "status": "PASS_FULL_EXPRESSION_SOURCE_BUNDLE_GATE" if not errors else
        "FAIL_FULL_EXPRESSION_SOURCE_BUNDLE_GATE",
        "manifest": rel(manifest_path),
        "locked_v9_sha256": LOCKED_V9_HASH,
        "face_sources": source_evidence,
        "detail_source": detail_evidence,
        "runtime_resource_activated": False,
        "component_export_eligible": False,
        "full_face_source_card_playback": "forbidden",
        "errors": errors,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--manifest", type=pathlib.Path, required=True)
    parser.add_argument("--write", type=pathlib.Path, required=True)
    args = parser.parse_args()
    try:
        result = verify(args.manifest.resolve())
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        print(f"FAIL: {exc}")
        return 1
    args.write.parent.mkdir(parents=True, exist_ok=True)
    args.write.write_text(json.dumps(result, indent=2) + "\n", encoding="ascii")
    if result["status"] != "PASS_FULL_EXPRESSION_SOURCE_BUNDLE_GATE":
        for error in result["errors"]:
            print(f"ERROR: {error}")
        return 1
    print("PASS: face anchors plus secondary details close the inactive V9 art-source bundle.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
