#!/usr/bin/env python3
"""Verify the Companion no-hardware BLE validation matrix artifact."""

from __future__ import annotations

import json
import pathlib
import sys
from typing import Any


sys.dont_write_bytecode = True
REPO_ROOT = pathlib.Path(__file__).resolve().parents[1]
MATRIX_PATH = REPO_ROOT / "docs/validation/companion_ble_matrix.json"
TOOL_PATH = REPO_ROOT / "tools/companion_ble_tool.py"

REQUIRED_OPERATIONS = {
    "scan_result_parsing",
    "status_read",
    "card_write",
    "recording_list",
    "recording_pull",
    "log_pull",
    "delete",
    "ota_status",
}
REQUIRED_MATRIX_CATEGORIES = {
    "normal_use",
    "retry",
    "cancel",
    "disconnect_reconnect",
    "long_recording_metadata",
    "idle_resume",
    "log_export",
    "ota_blocked",
}
REQUIRED_FAILURES = {
    "no_device",
    "wrong_service_uuid",
    "timeout",
    "crc_mismatch",
    "low_battery",
    "no_recording",
    "transfer_canceled",
}
REQUIRED_REAL_ADAPTERS = {"python-bleak", "windows-ble-apis", "listener-type-ble-approach"}


def require(condition: bool, message: str, errors: list[str]) -> None:
    if not condition:
        errors.append(message)


def load_matrix() -> dict[str, Any]:
    if not MATRIX_PATH.exists():
        raise FileNotFoundError(f"missing matrix artifact: {MATRIX_PATH.relative_to(REPO_ROOT)}")
    return json.loads(MATRIX_PATH.read_text(encoding="utf-8"))


def verify_operation_coverage(matrix: dict[str, Any], errors: list[str]) -> None:
    operations = matrix.get("operation_coverage")
    require(isinstance(operations, dict), "operation_coverage must be an object", errors)
    if not isinstance(operations, dict):
        return
    missing = sorted(REQUIRED_OPERATIONS - set(operations))
    require(not missing, f"missing operations: {', '.join(missing)}", errors)
    for name in REQUIRED_OPERATIONS:
        item = operations.get(name, {})
        require(item.get("status") == "PASS", f"operation {name} did not PASS", errors)
    scan = operations.get("scan_result_parsing", {})
    selected_name = str(scan.get("selected_name", ""))
    require(selected_name.startswith("Companion "), "scan fixture did not select a Companion device", errors)
    require("listener" not in selected_name.lower(), "scan fixture depends on Listener device name", errors)
    require("esp" not in selected_name.lower(), "scan fixture depends on ESP device name", errors)
    recording_pull = operations.get("recording_pull", {})
    require(int(recording_pull.get("packet_count", 0)) > 1, "recording pull must include multiple packets", errors)
    require(bool(recording_pull.get("final_sha256_verified")), "recording pull must verify final SHA-256", errors)
    delete = operations.get("delete", {}).get("delete_after_sync", {})
    require(delete.get("accepted_after_length_and_sha256") == "deleted", "delete-after-sync success evidence missing", errors)
    ota = operations.get("ota_status", {})
    require(ota.get("ota_data_path_enabled") is False, "OTA status fixture must not enable an OTA data path", errors)


def verify_product_matrix(matrix: dict[str, Any], errors: list[str]) -> None:
    cases = matrix.get("product_matrix")
    require(isinstance(cases, list), "product_matrix must be a list", errors)
    if not isinstance(cases, list):
        return
    categories = {str(item.get("category")) for item in cases if isinstance(item, dict)}
    missing = sorted(REQUIRED_MATRIX_CATEGORIES - categories)
    require(not missing, f"missing matrix categories: {', '.join(missing)}", errors)
    for item in cases:
        if not isinstance(item, dict):
            errors.append("product_matrix entry is not an object")
            continue
        case_id = str(item.get("case_id", "<missing>"))
        require(item.get("result") == "PASS", f"matrix case {case_id} did not PASS", errors)
        require(bool(str(item.get("scenario", "")).strip()), f"matrix case {case_id} missing scenario", errors)
        require(bool(str(item.get("expected_host_behavior", "")).strip()), f"matrix case {case_id} missing host expectation", errors)
        artifact_requirements = item.get("artifact_requirements", [])
        require(isinstance(artifact_requirements, list) and artifact_requirements, f"matrix case {case_id} missing artifacts", errors)


def verify_actionable_failures(matrix: dict[str, Any], errors: list[str]) -> None:
    failures = matrix.get("actionable_failures")
    require(isinstance(failures, list), "actionable_failures must be a list", errors)
    if not isinstance(failures, list):
        return
    names = {str(item.get("failure")) for item in failures if isinstance(item, dict)}
    missing = sorted(REQUIRED_FAILURES - names)
    require(not missing, f"missing actionable failures: {', '.join(missing)}", errors)
    for item in failures:
        if not isinstance(item, dict):
            errors.append("actionable_failures entry is not an object")
            continue
        name = str(item.get("failure", "<missing>"))
        require(bool(str(item.get("user_action", "")).strip()), f"failure {name} missing user action", errors)
        require(bool(str(item.get("host_result", "")).strip()), f"failure {name} missing host result", errors)


def verify_adapter_and_artifact_policy(matrix: dict[str, Any], errors: list[str]) -> None:
    require(matrix.get("schema_id") == "companion.pendant.ble_fixture_matrix.v1", "unexpected schema_id", errors)
    require(matrix.get("status") == "PASS", "matrix status is not PASS", errors)
    require(matrix.get("no_hardware") is True, "matrix must declare no_hardware=true", errors)
    adapters = set(matrix.get("real_ble_adapter_plan", []))
    missing_adapters = sorted(REQUIRED_REAL_ADAPTERS - adapters)
    require(not missing_adapters, f"missing real BLE adapter compatibility plan: {', '.join(missing_adapters)}", errors)
    source_refs = matrix.get("source_refs_used", {})
    require(
        source_refs.get("depends_on_forbidden_dependencies") is False,
        "matrix must explicitly avoid Listener/HID/ESP dependencies",
        errors,
    )
    artifact_policy = matrix.get("artifact_policy", {})
    primary = str(artifact_policy.get("primary_artifact", ""))
    require(primary == "docs/validation/companion_ble_matrix.json", "primary artifact path mismatch", errors)
    require(primary.startswith("docs/validation/"), "primary artifact must live under docs/validation", errors)
    require(TOOL_PATH.exists(), "companion BLE tool is missing", errors)


def main() -> int:
    errors: list[str] = []
    try:
        matrix = load_matrix()
    except Exception as exc:  # noqa: BLE001 - compact verifier output.
        print(f"FAIL: Companion BLE matrix verification failed: {exc}", file=sys.stderr)
        return 1
    verify_adapter_and_artifact_policy(matrix, errors)
    verify_operation_coverage(matrix, errors)
    verify_product_matrix(matrix, errors)
    verify_actionable_failures(matrix, errors)
    if errors:
        print("FAIL: Companion BLE matrix verification failed:", file=sys.stderr)
        for error in errors:
            print(f"  - {error}", file=sys.stderr)
        return 1
    print(
        "PASS: Companion BLE matrix verified; "
        f"{len(REQUIRED_OPERATIONS)} operations, "
        f"{len(REQUIRED_MATRIX_CATEGORIES)} matrix categories, "
        f"{len(REQUIRED_FAILURES)} actionable failures."
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
