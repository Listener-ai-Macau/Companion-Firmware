#!/usr/bin/env python3
"""Verify host-visible ExpressionV1 CardStatusV1 sequence integrity."""

from __future__ import annotations

import argparse
import json
import pathlib
import sys
from typing import Any


REPO_ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT / "tools"))

from companion_ble_tool import expression_decision_crc32  # noqa: E402


DEFAULT_FIXTURE = pathlib.Path("docs/validation/companion-screen-expression-host-status-sequence.json")
SCHEMA_ID = "companion.pendant.screen_expression_host_status_sequence.v1"

BLE_MATRIX = REPO_ROOT / "docs" / "validation" / "companion_ble_matrix.json"
BLE_TOOL = REPO_ROOT / "tools" / "companion_ble_tool.py"
BLE_MATRIX_VERIFIER = REPO_ROOT / "tools" / "verify_companion_ble_matrix.py"
STATUS_VERIFIER = REPO_ROOT / "tools" / "verify_expression_status_observability.py"
SCREEN_DOC = REPO_ROOT / "docs" / "companion_screen_expression_system.md"
WBA_RULES = REPO_ROOT / "docs" / "stm32wba_migration_rules.md"
BLE_CONTRACT = REPO_ROOT / "docs" / "ble_gatt_contract.md"

EXPECTED_EVENTS = [
    "boot_idle",
    "settings.display_off",
    "recording_fsm.start_request",
    "battery_charging.sample.low",
    "recording_fsm.session_finished",
    "errors.fault",
]


def rel(path: pathlib.Path) -> str:
    try:
        return path.resolve().relative_to(REPO_ROOT).as_posix()
    except ValueError:
        return path.as_posix()


def require(condition: bool, message: str, errors: list[str]) -> None:
    if not condition:
        errors.append(message)


def read(path: pathlib.Path, errors: list[str]) -> str:
    require(path.exists(), f"missing required path {rel(path)}", errors)
    if not path.exists():
        return ""
    return path.read_text(encoding="utf-8")


def load_matrix(errors: list[str]) -> dict[str, Any]:
    text = read(BLE_MATRIX, errors)
    if not text:
        return {}
    return json.loads(text)


def screen_steps(matrix: dict[str, Any]) -> list[dict[str, Any]]:
    operation = matrix.get("operation_coverage", {}).get("screen_expression_status", {})
    steps = operation.get("steps", [])
    return [step for step in steps if isinstance(step, dict)]


def build_fixture() -> dict[str, Any]:
    matrix = json.loads(BLE_MATRIX.read_text(encoding="utf-8"))
    steps = []
    for step in screen_steps(matrix):
        accepted = step.get("card_status", {})
        final = step.get("dry_run_final_status", {})
        steps.append(
            {
                "event": step.get("event"),
                "expression": step.get("expression"),
                "signal": step.get("signal"),
                "request_id": step.get("request_id"),
                "accepted_refresh_count": accepted.get("refresh_count"),
                "final_refresh_count": final.get("refresh_count"),
                "content_crc32": step.get("content_crc32"),
                "diagnostic_arg3": step.get("diagnostic_arg3"),
            }
        )
    return {
        "schema_id": SCHEMA_ID,
        "status": "PASS",
        "purpose": "Host-visible ExpressionV1 status steps keep contiguous CardStatusV1 refresh counts, stable request/content identity, deterministic expression CRCs, and diagnostic arg3 decode.",
        "sources": {
            "ble_matrix": rel(BLE_MATRIX),
            "ble_tool": rel(BLE_TOOL),
            "ble_matrix_verifier": rel(BLE_MATRIX_VERIFIER),
            "status_observability_verifier": rel(STATUS_VERIFIER),
            "screen_acceptance": rel(SCREEN_DOC),
            "wba_rules": rel(WBA_RULES),
            "ble_contract": rel(BLE_CONTRACT),
        },
        "operation": "screen_expression_status",
        "expected_events": EXPECTED_EVENTS,
        "steps": steps,
        "acceptance": {
            "accepted_final_refresh_counts_are_contiguous": True,
            "refresh_counts_are_globally_monotonic": True,
            "accepted_final_request_identity_is_stable": True,
            "accepted_final_content_crc_is_stable": True,
            "content_crc_matches_expression_decision_crc32": True,
            "diagnostic_arg3_matches_expression_and_signal_ids": True,
            "diagnostic_decode_matches_arg3": True,
            "wba_safe_host_status_sequence": True,
        },
        "validation_commands": [
            "python .\\tools\\verify_expression_host_status_sequence.py",
            "python .\\tools\\companion_ble_tool.py --self-test",
            "python .\\tools\\verify_companion_ble_matrix.py",
            "python .\\tools\\verify_expression_status_observability.py",
            "python .\\tools\\verify_expression_wba_portability.py",
        ],
    }


def parse_hex(value: Any, errors: list[str], label: str) -> int:
    try:
        return int(str(value), 16)
    except ValueError:
        errors.append(f"{label} is not a hex integer: {value!r}")
        return 0


def check_sequence(errors: list[str]) -> None:
    matrix = load_matrix(errors)
    operation = matrix.get("operation_coverage", {}).get("screen_expression_status", {})
    require(operation.get("status") == "PASS", "screen_expression_status operation must PASS", errors)
    require(
        operation.get("content_crc32_model") == "comp_epaper_expression_decision_crc32",
        "screen expression status fixture must use firmware expression CRC model",
        errors,
    )
    require(
        operation.get("diagnostic_arg3_model") == "(expression_id << 16) | signal_id",
        "screen expression status fixture must preserve diagnostic arg3 model",
        errors,
    )
    steps = screen_steps(matrix)
    require([str(step.get("event")) for step in steps] == EXPECTED_EVENTS, "screen expression event order drifted", errors)

    refresh_counts: list[int] = []
    for step in steps:
        event = str(step.get("event", "<missing>"))
        accepted = step.get("card_status", {})
        final = step.get("dry_run_final_status", {})
        require(accepted.get("render_state_name") == "accepted", f"{event} accepted render state drifted", errors)
        require(final.get("render_state_name") == "failed", f"{event} final render state drifted", errors)
        require(final.get("last_error_name") == "deferred_no_panel", f"{event} final last_error drifted", errors)
        require(
            accepted.get("request_id") == final.get("request_id") == step.get("request_id"),
            f"{event} request_id identity drifted",
            errors,
        )
        require(
            accepted.get("content_crc32") == final.get("content_crc32") == step.get("content_crc32"),
            f"{event} content_crc32 identity drifted",
            errors,
        )

        accepted_refresh = int(accepted.get("refresh_count", -1))
        final_refresh = int(final.get("refresh_count", -1))
        require(final_refresh == accepted_refresh + 1, f"{event} final refresh_count must follow accepted count", errors)
        refresh_counts.extend([accepted_refresh, final_refresh])

        expression_id = int(step.get("expression_id", -1))
        signal_id = int(step.get("signal_id", -1))
        priority = int(step.get("priority", -1))
        expected_crc = expression_decision_crc32(str(step.get("expression")), expression_id, signal_id, priority)
        require(step.get("content_crc32") == expected_crc, f"{event} expression decision CRC drifted", errors)

        expected_arg3 = (expression_id << 16) | signal_id
        actual_arg3 = parse_hex(step.get("diagnostic_arg3"), errors, f"{event} diagnostic_arg3")
        require(actual_arg3 == expected_arg3, f"{event} diagnostic_arg3 packing drifted", errors)
        decode = step.get("diagnostic_decode", {})
        require(decode.get("expression_id") == expression_id, f"{event} decoded expression_id drifted", errors)
        require(decode.get("signal_id") == signal_id, f"{event} decoded signal_id drifted", errors)

    if refresh_counts:
        expected = list(range(refresh_counts[0], refresh_counts[0] + len(refresh_counts)))
        require(refresh_counts == expected, "screen expression refresh_count sequence is not contiguous", errors)
        require(len(refresh_counts) == len(set(refresh_counts)), "screen expression refresh_count sequence contains duplicates", errors)


def check_docs(errors: list[str]) -> None:
    screen_doc = " ".join(read(SCREEN_DOC, errors).split()).lower()
    wba_rules = " ".join(read(WBA_RULES, errors).split()).lower()
    ble_contract = " ".join(read(BLE_CONTRACT, errors).split()).lower()
    for token in [
        "host ble expressionv1 status sequence integrity",
        "host_ble_expression_status_sequence",
        "companion-screen-expression-host-status-sequence.json",
        "refresh_count",
    ]:
        require(token in screen_doc, f"screen expression doc missing host status sequence anchor {token}", errors)
    for token in [
        "accepted/final cardstatusv1 pairing",
        "extended expressionv1 status coverage",
        "refresh_count",
    ]:
        require(token in wba_rules, f"WBA rules missing host status sequence anchor {token}", errors)
    for token in [
        "accepted/final cardstatusv1",
        "content_crc32",
        "(expression_id << 16) | signal_id",
    ]:
        require(token in ble_contract, f"BLE contract missing host status sequence anchor {token}", errors)


def check_fixture_file(path: pathlib.Path, expected: dict[str, Any], errors: list[str]) -> None:
    require(path.exists(), f"missing host status sequence fixture: {rel(path)}", errors)
    if not path.exists():
        return
    actual = json.loads(path.read_text(encoding="utf-8"))
    require(actual == expected, f"{rel(path)} is stale; rerun with --write-fixture", errors)


def parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--fixture", type=pathlib.Path, default=DEFAULT_FIXTURE)
    parser.add_argument("--write-fixture", action="store_true", help="Update the deterministic host status sequence fixture.")
    return parser.parse_args(argv)


def main(argv: list[str]) -> int:
    args = parse_args(argv)
    fixture_path = REPO_ROOT / args.fixture
    errors: list[str] = []
    expected = build_fixture()

    check_sequence(errors)
    check_docs(errors)

    if args.write_fixture and not errors:
        fixture_path.parent.mkdir(parents=True, exist_ok=True)
        fixture_path.write_text(json.dumps(expected, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    if not args.write_fixture:
        check_fixture_file(fixture_path, expected, errors)

    if errors:
        print("FAIL: Companion host ExpressionV1 status sequence checks failed:", file=sys.stderr)
        for error in errors:
            print(f" - {error}", file=sys.stderr)
        return 1
    print(f"PASS: Companion host ExpressionV1 status sequence verified -> {rel(fixture_path)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
