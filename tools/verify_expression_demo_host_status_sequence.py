#!/usr/bin/env python3
"""Verify the ExpressionV1 demo host CardStatusV1 sequence contract."""

from __future__ import annotations

import argparse
import json
import pathlib
import sys
from typing import Any


REPO_ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT / "tools"))

from companion_ble_tool import expression_decision_crc32  # noqa: E402


DEFAULT_FIXTURE = pathlib.Path("docs/validation/companion-screen-expression-demo-host-status-sequence.json")
SCHEMA_ID = "companion.pendant.screen_expression_demo_host_status_sequence.v1"

DEMO_SEQUENCE = REPO_ROOT / "docs/validation/companion-screen-expression-demo-sequence.json"
CATALOG = REPO_ROOT / "docs/validation/companion-screen-expression-catalog.json"
LEGACY_HOST_SEQUENCE = REPO_ROOT / "docs/validation/companion-screen-expression-host-status-sequence.json"
REAL_BLE_BENCH = REPO_ROOT / "docs/validation/companion-screen-real-ble-bench.json"
SCREEN_DOC = REPO_ROOT / "docs/companion_screen_expression_system.md"
WBA_RULES = REPO_ROOT / "docs/stm32wba_migration_rules.md"
BLE_CONTRACT = REPO_ROOT / "docs/ble_gatt_contract.md"
EPAPER_README = REPO_ROOT / "app/companion_pendant/epaper/README.md"

CARD_SLOT = 1
REQUEST_ID_BASE = 0xE0001000
ACCEPTED_RENDER_STATE = 1
FINAL_RENDER_STATE = 3
OK_LAST_ERROR = 0
DEFERRED_NO_PANEL_LAST_ERROR = 4
START_REFRESH_COUNT = 100


def rel(path: pathlib.Path) -> str:
    try:
        return path.resolve().relative_to(REPO_ROOT).as_posix()
    except ValueError:
        return path.as_posix()


def require(condition: bool, message: str, errors: list[str]) -> None:
    if not condition:
        errors.append(message)


def load_json(path: pathlib.Path, errors: list[str]) -> dict[str, Any]:
    require(path.exists(), f"missing required source {rel(path)}", errors)
    if not path.exists():
        return {}
    return json.loads(path.read_text(encoding="utf-8"))


def catalog_maps(catalog: dict[str, Any]) -> tuple[dict[str, dict[str, Any]], dict[str, dict[str, Any]]]:
    expressions = {
        str(item.get("name")): item
        for item in catalog.get("expressions", [])
        if isinstance(item, dict)
    }
    signals = {
        str(item.get("signal")): item
        for item in catalog.get("signals", [])
        if isinstance(item, dict)
    }
    return expressions, signals


def demo_steps(demo_sequence: dict[str, Any]) -> list[dict[str, Any]]:
    steps: list[dict[str, Any]] = []
    for demo in demo_sequence.get("demos", []):
        if not isinstance(demo, dict):
            continue
        for step in demo.get("steps", []):
            if isinstance(step, dict):
                merged = dict(step)
                merged["demo_id"] = str(demo.get("demo_id", ""))
                merged["demo_order"] = int(demo.get("order", 0))
                steps.append(merged)
    return steps


def status_pair(
    step: dict[str, Any],
    sequence_index: int,
    refresh_count: int,
    expressions: dict[str, dict[str, Any]],
    signals: dict[str, dict[str, Any]],
    errors: list[str],
) -> dict[str, Any]:
    expression = str(step.get("visible_expression", ""))
    signal = str(step.get("expression_signal", ""))
    expression_def = expressions.get(expression, {})
    signal_def = signals.get(signal, {})
    require(bool(expression_def), f"demo step references unknown expression {expression}", errors)
    require(bool(signal_def), f"demo step references unknown signal {signal}", errors)
    expression_id = int(expression_def.get("id", -1))
    signal_id = int(signal_def.get("id", -1))
    priority = int(expression_def.get("priority", -1))
    require(signal_def.get("expression") == expression, f"{step.get('demo_id')} step {step.get('index')} signal/expression drift", errors)
    content_crc32 = expression_decision_crc32(expression, expression_id, signal_id, priority)
    diagnostic_arg3 = (expression_id << 16) | signal_id
    request_id = REQUEST_ID_BASE + sequence_index
    return {
        "demo_id": str(step.get("demo_id", "")),
        "demo_order": int(step.get("demo_order", 0)),
        "step_index": int(step.get("index", 0)),
        "event": str(step.get("event", "")),
        "expression": expression,
        "expression_id": expression_id,
        "signal": signal,
        "signal_id": signal_id,
        "priority": priority,
        "request_id": request_id,
        "content_crc32": content_crc32,
        "diagnostic_arg3": f"0x{diagnostic_arg3:08x}",
        "diagnostic_decode": {
            "expression_id": expression_id,
            "signal_id": signal_id,
        },
        "card_status": {
            "schema_version": 1,
            "card_slot": CARD_SLOT,
            "request_id": request_id,
            "render_state": ACCEPTED_RENDER_STATE,
            "render_state_name": "accepted",
            "last_error": OK_LAST_ERROR,
            "last_error_name": "ok",
            "content_crc32": content_crc32,
            "refresh_count": refresh_count,
        },
        "dry_run_final_status": {
            "schema_version": 1,
            "card_slot": CARD_SLOT,
            "request_id": request_id,
            "render_state": FINAL_RENDER_STATE,
            "render_state_name": "failed",
            "last_error": DEFERRED_NO_PANEL_LAST_ERROR,
            "last_error_name": "deferred_no_panel",
            "content_crc32": content_crc32,
            "refresh_count": refresh_count + 1,
        },
    }


def build_fixture(errors: list[str]) -> dict[str, Any]:
    demo_sequence = load_json(DEMO_SEQUENCE, errors)
    catalog = load_json(CATALOG, errors)
    legacy = load_json(LEGACY_HOST_SEQUENCE, errors)
    load_json(REAL_BLE_BENCH, errors)
    if errors:
        return {"schema_id": SCHEMA_ID, "status": "FAIL", "errors": errors}

    expressions, signals = catalog_maps(catalog)
    accepted_steps: list[dict[str, Any]] = []
    held_steps: list[dict[str, Any]] = []
    refresh_count = START_REFRESH_COUNT
    sequence_index = 1
    for step in demo_steps(demo_sequence):
        if str(step.get("expected_result")) == "accept":
            accepted_steps.append(status_pair(step, sequence_index, refresh_count, expressions, signals, errors))
            sequence_index += 1
            refresh_count += 2
        else:
            held_steps.append(
                {
                    "demo_id": str(step.get("demo_id", "")),
                    "demo_order": int(step.get("demo_order", 0)),
                    "step_index": int(step.get("index", 0)),
                    "event": str(step.get("event", "")),
                    "visible_expression": str(step.get("visible_expression", "")),
                    "expression_signal": step.get("expression_signal"),
                    "expected_result": str(step.get("expected_result", "")),
                    "host_status_emitted": False,
                    "reason": str(step.get("reason", "")),
                }
            )

    demo_faces = sorted(str(face) for face in demo_sequence.get("summary", {}).get("expression_coverage", []))
    accepted_faces = sorted({str(step.get("expression")) for step in accepted_steps})
    legacy_faces = sorted({str(step.get("expression")) for step in legacy.get("steps", []) if isinstance(step, dict)})
    return {
        "schema_id": SCHEMA_ID,
        "status": "PASS",
        "purpose": (
            "Contract-only host CardStatusV1 sequence for the full screen demo order. "
            "Accepted demo steps emit accepted/final pairs; held demo steps emit no new host status."
        ),
        "operation": "screen_expression_demo_status",
        "contract_only": True,
        "hardware_collected": False,
        "sources": {
            "demo_sequence": rel(DEMO_SEQUENCE),
            "expression_catalog": rel(CATALOG),
            "legacy_host_status_sequence": rel(LEGACY_HOST_SEQUENCE),
            "real_ble_bench": rel(REAL_BLE_BENCH),
            "screen_acceptance": rel(SCREEN_DOC),
            "wba_rules": rel(WBA_RULES),
            "ble_contract": rel(BLE_CONTRACT),
            "epaper_readme": rel(EPAPER_README),
        },
        "request_id_model": "0xE0001000 + accepted_demo_sequence_index",
        "content_crc32_model": "comp_epaper_expression_decision_crc32",
        "diagnostic_arg3_model": "(expression_id << 16) | signal_id",
        "summary": {
            "demo_step_count": len(accepted_steps) + len(held_steps),
            "accepted_status_pair_count": len(accepted_steps),
            "held_no_status_count": len(held_steps),
            "demo_expression_coverage": demo_faces,
            "accepted_expression_coverage": accepted_faces,
            "legacy_six_face_coverage": legacy_faces,
            "extends_legacy_faces": sorted(set(accepted_faces) - set(legacy_faces)),
        },
        "accepted_status_steps": accepted_steps,
        "held_no_status_steps": held_steps,
        "acceptance": {
            "covers_all_demo_expression_faces": accepted_faces == demo_faces,
            "accepted_final_refresh_counts_are_contiguous": True,
            "accepted_final_request_identity_is_stable": True,
            "accepted_final_content_crc_is_stable": True,
            "content_crc_matches_expression_decision_crc32": True,
            "diagnostic_arg3_matches_expression_and_signal_ids": True,
            "held_steps_emit_no_host_status": all(step.get("host_status_emitted") is False for step in held_steps),
            "legacy_six_face_sequence_is_subset": set(legacy_faces).issubset(set(accepted_faces)),
            "wba_safe_demo_status_sequence": True,
        },
        "validation_commands": [
            "python .\\tools\\verify_expression_demo_host_status_sequence.py",
            "python .\\tools\\verify_expression_demo_sequence.py",
            "python .\\tools\\verify_expression_host_status_sequence.py",
            "python .\\tools\\verify_expression_catalog_contract.py",
            "python .\\tools\\verify_expression_wba_portability.py",
        ],
    }


def parse_hex(value: Any, errors: list[str], label: str) -> int:
    try:
        return int(str(value), 16)
    except ValueError:
        errors.append(f"{label} is not a hex integer: {value!r}")
        return 0


def validate_fixture(data: dict[str, Any], errors: list[str]) -> None:
    require(data.get("schema_id") == SCHEMA_ID, "unexpected demo host status sequence schema", errors)
    require(data.get("status") == "PASS", "demo host status sequence must be PASS", errors)
    require(data.get("operation") == "screen_expression_demo_status", "unexpected demo host status operation", errors)
    require(data.get("contract_only") is True, "demo host status sequence must be contract-only", errors)
    require(data.get("hardware_collected") is False, "demo host status sequence must not claim hardware collection", errors)
    summary = data.get("summary", {})
    require(summary.get("demo_step_count") == 37, "demo host status sequence should cover 37 demo steps", errors)
    require(summary.get("accepted_status_pair_count") == 29, "demo host status sequence should have 29 accepted pairs", errors)
    require(summary.get("held_no_status_count") == 8, "demo host status sequence should have 8 held no-status steps", errors)
    require(
        summary.get("accepted_expression_coverage") == summary.get("demo_expression_coverage"),
        "accepted demo status pairs must cover every demo expression face",
        errors,
    )
    require(
        summary.get("extends_legacy_faces") == ["happy", "listening", "speaking", "thinking"],
        "demo host status sequence should extend the legacy six-face sequence by four faces",
        errors,
    )

    refresh_counts: list[int] = []
    for step in data.get("accepted_status_steps", []):
        if not isinstance(step, dict):
            errors.append("accepted_status_steps entry is not an object")
            continue
        event = str(step.get("event", ""))
        accepted = step.get("card_status", {})
        final = step.get("dry_run_final_status", {})
        require(accepted.get("render_state_name") == "accepted", f"{event} accepted state drifted", errors)
        require(final.get("render_state_name") == "failed", f"{event} final dry-run state drifted", errors)
        require(final.get("last_error_name") == "deferred_no_panel", f"{event} final dry-run error drifted", errors)
        require(accepted.get("request_id") == final.get("request_id") == step.get("request_id"), f"{event} request identity drifted", errors)
        require(
            accepted.get("content_crc32") == final.get("content_crc32") == step.get("content_crc32"),
            f"{event} content CRC identity drifted",
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
        require(actual_arg3 == expected_arg3, f"{event} diagnostic arg3 drifted", errors)
        decode = step.get("diagnostic_decode", {})
        require(decode.get("expression_id") == expression_id, f"{event} decoded expression_id drifted", errors)
        require(decode.get("signal_id") == signal_id, f"{event} decoded signal_id drifted", errors)

    if refresh_counts:
        expected = list(range(START_REFRESH_COUNT, START_REFRESH_COUNT + len(refresh_counts)))
        require(refresh_counts == expected, "demo host status refresh_count sequence is not contiguous", errors)
    require(
        all(step.get("host_status_emitted") is False for step in data.get("held_no_status_steps", [])),
        "held demo steps must not emit host status",
        errors,
    )
    acceptance = data.get("acceptance", {})
    for key in [
        "covers_all_demo_expression_faces",
        "accepted_final_refresh_counts_are_contiguous",
        "accepted_final_request_identity_is_stable",
        "accepted_final_content_crc_is_stable",
        "content_crc_matches_expression_decision_crc32",
        "diagnostic_arg3_matches_expression_and_signal_ids",
        "held_steps_emit_no_host_status",
        "legacy_six_face_sequence_is_subset",
        "wba_safe_demo_status_sequence",
    ]:
        require(acceptance.get(key) is True, f"demo host status acceptance missing {key}", errors)


def check_docs(errors: list[str]) -> None:
    for path in [SCREEN_DOC, WBA_RULES, BLE_CONTRACT, EPAPER_README]:
        require(path.exists(), f"missing doc source {rel(path)}", errors)
        if not path.exists():
            continue
        text = path.read_text(encoding="utf-8")
        for token in [
            "screen_expression_demo_host_status_sequence",
            "screen_expression_demo_status",
            "companion-screen-expression-demo-host-status-sequence.json",
            "verify_expression_demo_host_status_sequence.py",
            "held_steps_emit_no_host_status",
        ]:
            require(token in text, f"{rel(path)} missing demo host status token {token}", errors)


def check_fixture_file(path: pathlib.Path, expected: dict[str, Any], errors: list[str]) -> None:
    require(path.exists(), f"missing demo host status sequence fixture: {rel(path)}", errors)
    if not path.exists():
        return
    actual = json.loads(path.read_text(encoding="utf-8"))
    require(actual == expected, f"{rel(path)} is stale; rerun with --write-fixture", errors)
    validate_fixture(actual, errors)


def parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--fixture", type=pathlib.Path, default=DEFAULT_FIXTURE)
    parser.add_argument("--write-fixture", action="store_true", help="Update the deterministic demo host status fixture.")
    return parser.parse_args(argv)


def main(argv: list[str]) -> int:
    args = parse_args(argv)
    fixture_path = args.fixture if args.fixture.is_absolute() else REPO_ROOT / args.fixture
    errors: list[str] = []
    expected = build_fixture(errors)
    validate_fixture(expected, errors)
    check_docs(errors)
    if args.write_fixture and not errors:
        fixture_path.parent.mkdir(parents=True, exist_ok=True)
        fixture_path.write_text(json.dumps(expected, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    if not args.write_fixture:
        check_fixture_file(fixture_path, expected, errors)
    if errors:
        print("FAIL: Companion demo host ExpressionV1 status sequence checks failed:", file=sys.stderr)
        for error in errors:
            print(f" - {error}", file=sys.stderr)
        return 1
    print(f"PASS: Companion demo host ExpressionV1 status sequence verified -> {rel(fixture_path)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
