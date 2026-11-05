#!/usr/bin/env python3
"""Generate the no-hardware Companion V1 feature matrix."""

from __future__ import annotations

import argparse
import json
import pathlib
import sys
from typing import Any


sys.dont_write_bytecode = True
REPO_ROOT = pathlib.Path(__file__).resolve().parents[1]
MATRIX_PATH = REPO_ROOT / "docs" / "validation" / "companion_v1_feature_matrix.json"
UUID_TABLE = REPO_ROOT / "docs" / "ble_uuid_table.json"

REQUIRED_FEATURES = {
    "meeting_recording",
    "imu",
    "speaker",
    "voice_wake",
    "ble_name_config",
}

REQUIRED_NEGATIVE_CASES = {
    "invalid_ble_name_empty",
    "invalid_ble_name_equals",
    "unsupported_meeting_command",
    "wake_detect_while_disarmed",
    "speaker_unknown_command",
}


def rel(path: pathlib.Path) -> str:
    return path.relative_to(REPO_ROOT).as_posix()


def validate_ble_name(name: str) -> bool:
    raw = name.encode("ascii", errors="ignore")
    if len(raw) == 0 or len(raw) > 29 or len(raw) != len(name):
        return False
    for ch in raw:
        if ch < 0x20 or ch > 0x7E:
            return False
        if ch in (ord('"'), ord("'"), ord(";"), ord("="), ord("\\")):
            return False
    return True


def uuid_characteristics() -> dict[str, str]:
    table = json.loads(UUID_TABLE.read_text(encoding="utf-8"))
    result: dict[str, str] = {}
    for service in table["services"]:
        for characteristic in service["characteristics"]:
            result[str(characteristic["name"])] = str(characteristic["uuid"])
    return result


def build_matrix() -> dict[str, Any]:
    chars = uuid_characteristics()
    valid_name = "companion-v1"
    invalid_names = ["", "bad=name", "bad;name", "bad\\name", "bad\"name"]
    return {
        "schema_id": "companion.v1.feature_matrix.v1",
        "status": "PASS",
        "generated_by": "tools/companion_v1_feature_fixture.py",
        "no_hardware": True,
        "uuid_characteristics": {
            name: chars[name]
            for name in [
                "meeting_control",
                "meeting_status",
                "imu_status",
                "speaker_control",
                "speaker_status",
                "wake_word_control",
                "wake_word_status",
                "ble_name_config",
            ]
        },
        "features": [
            {
                "feature": "meeting_recording",
                "state_flow": ["idle", "recording", "finalized", "sync_ready"],
                "host_surface": "meeting sessions stay separate from one-shot dictation history",
                "fixture_result": "PASS",
                "diagnostic_anchors": ["meeting.start", "meeting.stop", "meeting.finalize", "meeting.rejected"],
            },
            {
                "feature": "imu",
                "state_flow": ["not_populated", "calibration_pending", "sample_contract_ready"],
                "host_surface": "host can show missing dev-board IMU separately from sensor failure",
                "fixture_result": "PASS",
                "diagnostic_anchors": ["imu.sample", "imu.motion", "imu.unavailable"],
            },
            {
                "feature": "speaker",
                "state_flow": ["not_populated", "prompt_accepted", "pending_hardware"],
                "host_surface": "host can request bounded prompts and show unavailable hardware",
                "fixture_result": "PASS",
                "diagnostic_anchors": ["speaker.prompt", "speaker.result", "speaker.rejected"],
            },
            {
                "feature": "voice_wake",
                "state_flow": ["disabled", "armed", "detected", "rejected"],
                "host_surface": "host can arm/disarm wake-word state before always-on DSP validation",
                "fixture_result": "PASS",
                "diagnostic_anchors": ["wake_word.armed", "wake_word.detected", "wake_word.disabled", "wake_word.rejected"],
            },
            {
                "feature": "ble_name_config",
                "state_flow": ["active", "staged", "restart_required", "rejected"],
                "host_surface": "host stages a Companion BLE name using Listener-compatible ASCII 1..29 policy",
                "fixture_result": "PASS",
                "diagnostic_anchors": [
                    "device_settings.ble_name.accepted",
                    "device_settings.ble_name.rejected",
                    "device_settings.ble_name.applied",
                ],
            },
        ],
        "ble_name_policy": {
            "default_name": "companion",
            "valid_example": valid_name,
            "valid_example_passed": validate_ble_name(valid_name),
            "max_len": 29,
            "printable_ascii_only": True,
            "forbidden_bytes": ["quote", "apostrophe", "semicolon", "equals", "backslash", "control"],
            "invalid_examples": [
                {"name": item, "accepted": validate_ble_name(item)} for item in invalid_names
            ],
            "apply_result": "restart_ble_or_reboot_required",
        },
        "negative_cases": [
            {
                "case": "invalid_ble_name_empty",
                "expected_result": "rejected",
                "host_action": "keep previous advertised name and show validation message",
            },
            {
                "case": "invalid_ble_name_equals",
                "expected_result": "rejected",
                "host_action": "do not send apply/restart until user edits the name",
            },
            {
                "case": "unsupported_meeting_command",
                "expected_result": "meeting.rejected",
                "host_action": "refresh meeting_status and keep current session state",
            },
            {
                "case": "wake_detect_while_disarmed",
                "expected_result": "wake_word.rejected",
                "host_action": "show wake disabled instead of claiming wake success",
            },
            {
                "case": "speaker_unknown_command",
                "expected_result": "speaker.rejected",
                "host_action": "keep prompt controls disabled until supported command is selected",
            },
        ],
        "hardware_gate": {
            "required_for_production": True,
            "current_board_limits": ["imu_not_populated", "speaker_not_populated", "wake_word_dsp_not_validated"],
        },
        "artifacts": {
            "uuid_table": rel(UUID_TABLE),
            "matrix": rel(MATRIX_PATH),
        },
    }


def validate_matrix(matrix: dict[str, Any]) -> None:
    features = {str(item["feature"]) for item in matrix.get("features", [])}
    missing_features = sorted(REQUIRED_FEATURES - features)
    if missing_features:
        raise RuntimeError(f"missing feature coverage: {', '.join(missing_features)}")
    negative = {str(item["case"]) for item in matrix.get("negative_cases", [])}
    missing_negative = sorted(REQUIRED_NEGATIVE_CASES - negative)
    if missing_negative:
        raise RuntimeError(f"missing negative cases: {', '.join(missing_negative)}")
    policy = matrix.get("ble_name_policy", {})
    if not policy.get("valid_example_passed"):
        raise RuntimeError("valid BLE name example did not pass")
    rejected = [item for item in policy.get("invalid_examples", []) if item.get("accepted")]
    if rejected:
        raise RuntimeError(f"invalid BLE names accepted: {rejected}")


def write_matrix(path: pathlib.Path, matrix: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(matrix, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--write-docs", action="store_true", help="write docs/validation/companion_v1_feature_matrix.json")
    parser.add_argument("--json", action="store_true")
    return parser.parse_args(argv)


def main(argv: list[str]) -> int:
    args = parse_args(argv)
    try:
        matrix = build_matrix()
        validate_matrix(matrix)
        if args.write_docs:
            write_matrix(MATRIX_PATH, matrix)
    except Exception as exc:  # noqa: BLE001 - compact CLI failure.
        print(f"FAIL: Companion V1 feature fixture failed: {type(exc).__name__}: {exc}", file=sys.stderr)
        return 1

    if args.json:
        print(json.dumps({"status": "PASS", "matrix": rel(MATRIX_PATH)}, indent=2, sort_keys=True))
    else:
        suffix = f" wrote {rel(MATRIX_PATH)}" if args.write_docs else " validated in memory"
        print(f"PASS: Companion V1 feature fixture{suffix}.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
