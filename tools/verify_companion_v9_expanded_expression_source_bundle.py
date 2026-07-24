#!/usr/bin/env python3
"""Close the machine gate for the sixteen-state split V9 expression-source bundle."""

from __future__ import annotations

import argparse
import hashlib
import json
import pathlib


ROOT = pathlib.Path(__file__).resolve().parents[1]
LOCKED_V9_HASH = "919F344957661DEF2099AD56AB1286CCA9DBA4D8F08B702617B6DF5B1A28E9DA"
EXPECTED_STATES = (
    "daily_attention_left", "daily_attention_right", "daily_attention_up", "daily_attention_down",
    "calm_content", "curious_question", "alert_surprised", "joyful_spark",
    "affectionate_warm", "playful_bright", "anticipatory_notice", "puzzled_processing",
    "recording_focus", "listening_focus", "menu_thinking", "sleep_rest_no_moon",
)


def load_json(path: pathlib.Path) -> dict[str, object]:
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


def verify(manifest_path: pathlib.Path) -> dict[str, object]:
    errors: list[str] = []
    manifest = load_json(manifest_path)
    locked = manifest.get("locked_v9_source")
    if not isinstance(locked, dict) or str(locked.get("sha256", "")).upper() != LOCKED_V9_HASH:
        errors.append("expanded source bundle is not locked to the immutable V9 parent hash")
    if tuple(manifest.get("all_required_states", [])) != EXPECTED_STATES:
        errors.append("expanded source bundle does not enumerate the complete ordered sixteen-state program")
    if manifest.get("runtime_resource_activated") is not False or manifest.get("component_export_eligible") is not False:
        errors.append("expanded source bundle is not explicitly inactive before owner art review")
    if manifest.get("full_face_source_card_playback") != "forbidden":
        errors.append("expanded source bundle permits forbidden full-face source-card playback")

    sources = manifest.get("sources")
    if not isinstance(sources, list) or len(sources) != 2:
        errors.append("expanded source bundle must contain exactly the Daily strip and emotion panel")
        sources = []
    collected_states: list[str] = []
    source_evidence: list[dict[str, object]] = []
    expected_report_pairs = (
        ("PASS_OPEN_EYE_IDENTITY_GATE", "PASS_DAILY_ATTENTION_PROOF_GATE", "daily_attention_readability"),
        ("PASS_OPEN_EYE_IDENTITY_GATE", "PASS_EXPANDED_EMOTION_PANEL_GATE", "expanded_emotion_panel"),
    )
    for index, source in enumerate(sources):
        if not isinstance(source, dict):
            errors.append(f"source {index} is malformed")
            continue
        candidate_path = repo_path(source.get("candidate"), errors, f"source {index} candidate")
        request_path = repo_path(source.get("request"), errors, f"source {index} request")
        expected_hash = str(source.get("sha256", "")).upper()
        if candidate_path is not None and sha256(candidate_path) != expected_hash:
            errors.append(f"source {index} candidate hash drifted")
        if request_path is not None:
            request = load_json(request_path)
            if request.get("planned_generated_output") != source.get("candidate"):
                errors.append(f"source {index} request output drifted")
            if tuple(request.get("required_cells", [])) != tuple(source.get("states", [])):
                errors.append(f"source {index} state mapping drifted")
            if str(request.get("render_parent_iteration", "")) != str(manifest.get("render_parent_iteration", "")):
                errors.append(f"source {index} does not share the locked V9 parent iteration")
        states = source.get("states")
        if isinstance(states, list):
            collected_states.extend(str(state) for state in states)
        else:
            errors.append(f"source {index} states are malformed")
        reports = source.get("machine_reports")
        if not isinstance(reports, dict):
            errors.append(f"source {index} report map is malformed")
            continue
        eye_path = repo_path(reports.get("open_eye_identity"), errors, f"source {index} eye report")
        expected_eye, expected_second, second_key = expected_report_pairs[index]
        second_path = repo_path(reports.get(second_key), errors, f"source {index} secondary report")
        if eye_path is not None:
            eye_report = load_json(eye_path)
            if eye_report.get("status") != expected_eye or eye_report.get("candidate_sha256") != expected_hash:
                errors.append(f"source {index} eye report does not prove the declared candidate")
        if second_path is not None:
            second_report = load_json(second_path)
            if second_report.get("status") != expected_second or second_report.get("candidate_sha256") != expected_hash:
                errors.append(f"source {index} secondary report does not prove the declared candidate")
        source_evidence.append({
            "iteration_id": source.get("iteration_id"),
            "candidate": source.get("candidate"),
            "sha256": expected_hash,
            "states": states,
        })
    if tuple(collected_states) != EXPECTED_STATES:
        errors.append("Daily strip plus expanded emotion panel do not provide the exact complete sixteen-state bundle")
    return {
        "schema": "companion.v9_expanded_expression_source_bundle_gate.v1",
        "status": "PASS_EXPANDED_EXPRESSION_SOURCE_BUNDLE_GATE" if not errors else
        "FAIL_EXPANDED_EXPRESSION_SOURCE_BUNDLE_GATE",
        "manifest": rel(manifest_path),
        "locked_v9_sha256": LOCKED_V9_HASH,
        "sources": source_evidence,
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
    if result["status"] != "PASS_EXPANDED_EXPRESSION_SOURCE_BUNDLE_GATE":
        for error in result["errors"]:
            print(f"ERROR: {error}")
        return 1
    print("PASS: Daily and expanded emotion sources close the inactive sixteen-state V9 art bundle.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
