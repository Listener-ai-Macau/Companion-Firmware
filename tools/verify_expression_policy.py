#!/usr/bin/env python3
"""Verify Companion ExpressionV1 event/status policy fixtures."""

from __future__ import annotations

import argparse
import json
import pathlib
import sys
from typing import Any


REPO_ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT))

from app.companion_pendant.epaper.card_renderer import (  # noqa: E402
    DISPLAY_VARIANTS,
    EXPRESSION_KINDS,
    render_card,
    sha256_hex,
)
from app.companion_pendant.epaper.expression_policy import (  # noqa: E402
    RECORDING_STATE_ERROR_RECOVERY,
    RECORDING_STATE_RECORDING,
    RECORDING_STATE_STOPPING,
    RECORDING_STATE_TRANSFER_READY,
    decide_policy_case,
    expression_from_event,
    expression_from_status,
    policy_fixture_cases,
)


DEFAULT_FIXTURE = pathlib.Path("docs/validation/companion-screen-expression-policy.json")
README = REPO_ROOT / "app" / "companion_pendant" / "epaper" / "README.md"
PLAN_DOC = REPO_ROOT / "docs" / "companion_screen_expression_system.md"
POLICY_MODULE = REPO_ROOT / "app" / "companion_pendant" / "epaper" / "expression_policy.py"
SCHEMA_ID = "companion.pendant.expression_policy.v1"


def rel(path: pathlib.Path) -> str:
    try:
        return path.resolve().relative_to(REPO_ROOT).as_posix()
    except ValueError:
        return path.as_posix()


def require(condition: bool, message: str, errors: list[str]) -> None:
    if not condition:
        errors.append(message)


def build_fixture() -> dict[str, Any]:
    cases: list[dict[str, Any]] = []
    coverage: set[str] = set()
    for case in policy_fixture_cases():
        decision = decide_policy_case(case)
        coverage.add(decision.expression)
        card = decision.as_card(card_id=str(case["case_id"]))
        render_hashes = {
            key: sha256_hex(render_card(card, variant))
            for key, variant in DISPLAY_VARIANTS.items()
        }
        cases.append(
            {
                "case_id": case["case_id"],
                "input_type": case["input_type"],
                "event_name": case.get("event_name"),
                "input": case.get("input", {}),
                "expected_expression": case["expected_expression"],
                "decision": decision.as_manifest(),
                "render_hashes": render_hashes,
            }
        )

    return {
        "schema_id": SCHEMA_ID,
        "policy": "ExpressionV1 status/event mapping",
        "fixture_source": rel(POLICY_MODULE),
        "supported_expressions": sorted(EXPRESSION_KINDS),
        "policy_coverage": sorted(coverage),
        "display_variants": {
            key: {"width": variant.width, "height": variant.height, "label": variant.label}
            for key, variant in DISPLAY_VARIANTS.items()
        },
        "cases": cases,
        "hardware_boundary": {
            "ai_testable_now": [
                "status snapshot mapping",
                "diagnostic event mapping",
                "ExpressionV1 card conversion",
                "deterministic render hashes",
            ],
            "deferred_to_hardware_gates": [
                "real BLE notification ordering",
                "display task queue timing",
                "panel refresh confirmation",
            ],
        },
    }


def check_policy_logic(errors: list[str]) -> None:
    coverage: set[str] = set()
    for case in policy_fixture_cases():
        decision = decide_policy_case(case)
        coverage.add(decision.expression)
        require(
            decision.expression == case["expected_expression"],
            f"{case['case_id']} mapped to {decision.expression}, expected {case['expected_expression']}",
            errors,
        )
        card = decision.as_card(card_id=str(case["case_id"]))
        require(card.card_type == "expression", f"{case['case_id']} did not produce an expression card", errors)
        require(card.state == decision.expression, f"{case['case_id']} card state mismatch", errors)
        for variant in DISPLAY_VARIANTS.values():
            first = render_card(card, variant)
            second = render_card(card, variant)
            require(first == second, f"{case['case_id']}/{variant.key} render is not deterministic", errors)
            require(first.startswith(b"P4\n"), f"{case['case_id']}/{variant.key} did not render PBM", errors)

    require(EXPRESSION_KINDS <= coverage, f"policy cases do not cover: {sorted(EXPRESSION_KINDS - coverage)}", errors)

    require(expression_from_event("meeting.rejected").expression == "error", "rejected events must map to error", errors)
    require(expression_from_event("battery_charging.sample", {"percent": 12}).expression == "low_battery", "low battery event mapping failed", errors)
    require(
        expression_from_event("battery_charging.sample", {"percent": 27, "millivolts": 3650, "charger_present": 0}).expression == "idle",
        "battery recovered event mapping failed",
        errors,
    )
    require(
        expression_from_event("battery_charging.sample", {"percent": 22, "millivolts": 3650, "charger_present": 0}).reason == "event has no expression override",
        "near-threshold battery samples must not recover low-battery state",
        errors,
    )
    require(
        expression_from_status({"ota_readiness": {"blocker_bitmap": 1 << 3}}).expression == "low_battery",
        "OTA low-battery blocker mapping failed",
        errors,
    )
    require(
        expression_from_status({"ota_readiness": {"blocker_bitmap": 1 << 4}}).expression == "error",
        "OTA nonzero blocker mapping failed",
        errors,
    )
    require(
        expression_from_status({"meeting_status": {"state": 0, "summary_state": 1, "sync_state": 0}}).expression == "thinking",
        "meeting summary-pending status mapping failed",
        errors,
    )
    require(
        expression_from_status({"recording_status": {"state": RECORDING_STATE_RECORDING}}).expression == "recording",
        "recording FSM active-state mapping failed",
        errors,
    )
    require(
        expression_from_status({"recording_status": {"state": RECORDING_STATE_STOPPING}}).expression == "thinking",
        "recording FSM stopping-state mapping failed",
        errors,
    )
    require(
        expression_from_status({"recording_status": {"state": RECORDING_STATE_TRANSFER_READY}}).expression == "sync_complete",
        "recording FSM transfer-state mapping failed",
        errors,
    )
    require(
        expression_from_status({"recording_status": {"state": RECORDING_STATE_ERROR_RECOVERY}}).expression == "error",
        "recording FSM error-recovery mapping failed",
        errors,
    )
    require(
        expression_from_status({"recording_status": {"state": 255}}).expression == "idle",
        "unknown recording FSM states must not override idle",
        errors,
    )
    require(
        expression_from_status({"speaker_status": {"state": 2, "last_error": 0}}).expression == "speaking",
        "speaker prompt status mapping failed",
        errors,
    )
    require(
        expression_from_status({"wake_word_status": {"armed": 1, "last_event": 2, "last_error": 0}}).expression == "listening",
        "wake detected status mapping failed",
        errors,
    )
    require(expression_from_status({"device_status": {"fault_bitmap": 1}, "meeting_status": {"state": 1}}).expression == "error", "faults must outrank recording", errors)
    require(
        expression_from_status({"battery_charge": {"percent": 12}, "meeting_status": {"state": 1}}).expression == "recording",
        "recording must remain visible over low battery",
        errors,
    )


def check_fixture_file(path: pathlib.Path, expected: dict[str, Any], errors: list[str]) -> None:
    require(path.exists(), f"missing policy fixture: {rel(path)}", errors)
    if not path.exists():
        return
    actual = json.loads(path.read_text(encoding="utf-8"))
    require(actual == expected, f"{rel(path)} is stale; rerun with --write-fixture", errors)


def check_docs(errors: list[str]) -> None:
    require(README.exists(), "missing e-paper README", errors)
    require(PLAN_DOC.exists(), "missing screen expression plan doc", errors)
    if README.exists():
        readme = README.read_text(encoding="utf-8")
        compact_readme = " ".join(readme.split())
        for token in ["ExpressionV1", "BLE callbacks", "platform code", "SPI"]:
            require(token in compact_readme, f"README missing expression policy anchor: {token}", errors)
    if PLAN_DOC.exists():
        text = PLAN_DOC.read_text(encoding="utf-8")
        compact_text = " ".join(text.split())
        for token in ["BLE-to-expression policy", "status snapshot", "diagnostic event", "ExpressionV1"]:
            require(token in compact_text, f"screen expression doc missing anchor: {token}", errors)


def check_portable_boundary(errors: list[str]) -> None:
    text = POLICY_MODULE.read_text(encoding="utf-8")
    for forbidden in ["stm32", "stml", "hal_", "gpio", "spi_", "ipcc", "hsem", "stmwpan"]:
        require(forbidden not in text.lower(), f"expression policy must stay platform-free: {forbidden}", errors)


def parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--fixture", type=pathlib.Path, default=DEFAULT_FIXTURE)
    parser.add_argument("--write-fixture", action="store_true", help="Update the deterministic policy fixture JSON.")
    return parser.parse_args(argv)


def main(argv: list[str]) -> int:
    args = parse_args(argv)
    fixture_path = REPO_ROOT / args.fixture
    errors: list[str] = []
    expected = build_fixture()

    if args.write_fixture:
        fixture_path.parent.mkdir(parents=True, exist_ok=True)
        fixture_path.write_text(json.dumps(expected, indent=2, sort_keys=True) + "\n", encoding="utf-8")

    check_policy_logic(errors)
    check_fixture_file(fixture_path, expected, errors)
    check_docs(errors)
    check_portable_boundary(errors)

    if errors:
        print("FAIL: Companion ExpressionV1 policy checks failed:", file=sys.stderr)
        for error in errors:
            print(f" - {error}", file=sys.stderr)
        return 1
    print(f"PASS: Companion ExpressionV1 policy verified -> {rel(fixture_path)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
