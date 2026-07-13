#!/usr/bin/env python3
"""Verify ExpressionV1 rejects unknown signals without mutating visible state."""

from __future__ import annotations

import argparse
import json
import pathlib
import re
import sys
from typing import Any


REPO_ROOT = pathlib.Path(__file__).resolve().parents[1]
DEFAULT_FIXTURE = pathlib.Path("docs/validation/companion-screen-expression-signal-guard.json")
SCHEMA_ID = "companion.pendant.expression_signal_guard.v1"

EXPRESSION_HEADER = REPO_ROOT / "app" / "companion_pendant" / "epaper" / "expression_state.h"
EXPRESSION_SOURCE = REPO_ROOT / "app" / "companion_pendant" / "epaper" / "expression_state.c"
CATALOG_FIXTURE = REPO_ROOT / "docs" / "validation" / "companion-screen-expression-catalog.json"
FIRMWARE_STATE_FIXTURE = REPO_ROOT / "docs" / "validation" / "companion-screen-firmware-expression-state.json"
SCREEN_DOC = REPO_ROOT / "docs" / "companion_screen_expression_system.md"
WBA_RULES = REPO_ROOT / "docs" / "stm32wba_migration_rules.md"
README = REPO_ROOT / "app" / "companion_pendant" / "epaper" / "README.md"

SIGNAL_ENUM_RE = re.compile(r"COMP_EPAPER_EXPRESSION_SIGNAL_([A-Z_]+)\s*=\s*(\d+),")
SIGNAL_DEF_RE = re.compile(
    r'\{COMP_EPAPER_EXPRESSION_SIGNAL_([A-Z_]+),\s*COMP_EPAPER_EXPRESSION_([A-Z_]+),\s*(true|false),\s*"([^"]+)"\}'
)


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


def parse_signal_ids(header: str) -> dict[str, int]:
    return {
        symbol: int(value)
        for symbol, value in SIGNAL_ENUM_RE.findall(header)
        if symbol != "COUNT"
    }


def parse_signal_defs(source: str) -> dict[str, dict[str, Any]]:
    return {
        signal: {
            "expression": expression.lower(),
            "may_lower_priority": may_lower == "true",
            "reason": reason,
        }
        for signal, expression, may_lower, reason in SIGNAL_DEF_RE.findall(source)
    }


def supported_signals(header: str, source: str) -> list[dict[str, Any]]:
    ids = parse_signal_ids(header)
    defs = parse_signal_defs(source)
    return [
        {
            "id": ids[signal],
            "signal": signal,
            "expression": defs[signal]["expression"],
            "may_lower_priority": defs[signal]["may_lower_priority"],
            "reason": defs[signal]["reason"],
        }
        for signal in sorted(ids, key=lambda item: ids[item])
        if signal in defs
    ]


def build_fixture() -> dict[str, Any]:
    header = EXPRESSION_HEADER.read_text(encoding="utf-8")
    source = EXPRESSION_SOURCE.read_text(encoding="utf-8")
    signals = supported_signals(header, source)
    return {
        "schema_id": SCHEMA_ID,
        "status": "PASS",
        "purpose": "Unsupported ExpressionV1 signals are rejected before visible state or display queue work changes.",
        "sources": {
            "firmware_header": rel(EXPRESSION_HEADER),
            "firmware_source": rel(EXPRESSION_SOURCE),
            "catalog_fixture": rel(CATALOG_FIXTURE),
            "firmware_state_fixture": rel(FIRMWARE_STATE_FIXTURE),
            "screen_acceptance": rel(SCREEN_DOC),
            "wba_rules": rel(WBA_RULES),
        },
        "supported_signal_count": len(signals),
        "supported_signals": signals,
        "unsupported_signal_examples": [
            "COMP_EPAPER_EXPRESSION_SIGNAL_COUNT",
            "(comp_epaper_expression_signal_t)255u",
        ],
        "guards": {
            "preflight_api": "comp_epaper_expression_signal_is_supported",
            "decide_rejects_unknown_signal": True,
            "apply_signal_rejects_unknown_signal_before_state_mutation": True,
            "append_only_signal_catalog_guard": True,
        },
        "validation_commands": [
            "python .\\tools\\verify_expression_signal_guard.py",
            "python .\\tools\\verify_expression_catalog_contract.py",
            "python .\\tools\\verify_expression_firmware_state.py",
            "python .\\tools\\verify_expression_wba_portability.py",
        ],
    }


def check_firmware(errors: list[str]) -> None:
    header = read(EXPRESSION_HEADER, errors)
    source = read(EXPRESSION_SOURCE, errors)
    signal_ids = parse_signal_ids(header)
    signal_defs = parse_signal_defs(source)
    require(signal_ids, "expression_state.h has no signal enum IDs", errors)
    require(set(signal_ids) == set(signal_defs), "signal enum and definition table drifted", errors)
    require(
        "bool comp_epaper_expression_signal_is_supported(comp_epaper_expression_signal_t signal);" in header,
        "expression_state.h missing signal preflight API",
        errors,
    )
    require(
        "bool comp_epaper_expression_signal_is_supported(comp_epaper_expression_signal_t signal)" in source,
        "expression_state.c missing signal preflight implementation",
        errors,
    )
    require(
        "return find_signal(signal) != NULL;" in source,
        "signal preflight API must use the same signal table as decide/apply",
        errors,
    )
    require(
        "signal_def == NULL || out_decision == NULL" in source,
        "comp_epaper_expression_decide must reject unknown signals",
        errors,
    )
    require(
        "state == NULL || out_decision == NULL || signal_def == NULL" in source,
        "comp_epaper_expression_state_apply_signal must reject unknown signals before mutation",
        errors,
    )


def check_fixtures(errors: list[str]) -> None:
    catalog = json.loads(read(CATALOG_FIXTURE, errors) or "{}")
    state = json.loads(read(FIRMWARE_STATE_FIXTURE, errors) or "{}")
    expected_count = catalog.get("public_invariants", {}).get("signal_count")
    require(expected_count == 18, "catalog signal_count must include appended battery recovery signal", errors)
    require(
        len(catalog.get("signals", [])) == expected_count,
        "catalog signal table length does not match signal_count",
        errors,
    )
    require(
        len(state.get("signals", [])) == expected_count,
        "firmware state fixture signal table length does not match catalog",
        errors,
    )


def check_docs(errors: list[str]) -> None:
    screen_doc = read(SCREEN_DOC, errors)
    wba_rules = read(WBA_RULES, errors)
    readme = read(README, errors)
    screen_doc_norm = " ".join(screen_doc.split()).lower()
    wba_rules_norm = " ".join(wba_rules.split()).lower()
    readme_norm = " ".join(readme.split()).lower()
    for token in [
        "expression_unknown_signal_guard",
        "Expression unknown signal guard",
        "companion-screen-expression-signal-guard.json",
        "comp_epaper_expression_signal_is_supported",
    ]:
        require(token.lower() in screen_doc_norm, f"screen doc missing signal guard anchor {token}", errors)
    for token in [
        "unknown ExpressionV1 signals",
        "comp_epaper_expression_signal_is_supported",
        "append-only signal catalog",
    ]:
        require(token.lower() in wba_rules_norm, f"WBA rules missing signal guard anchor {token}", errors)
    for token in [
        "comp_epaper_expression_signal_is_supported",
        "unknown signal",
    ]:
        require(token.lower() in readme_norm, f"e-paper README missing signal guard anchor {token}", errors)


def check_fixture_file(path: pathlib.Path, expected: dict[str, Any], errors: list[str]) -> None:
    require(path.exists(), f"missing expression signal guard fixture: {rel(path)}", errors)
    if not path.exists():
        return
    actual = json.loads(path.read_text(encoding="utf-8"))
    require(actual == expected, f"{rel(path)} is stale; rerun with --write-fixture", errors)


def parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--fixture", type=pathlib.Path, default=DEFAULT_FIXTURE)
    parser.add_argument("--write-fixture", action="store_true", help="Update the deterministic signal guard fixture JSON.")
    return parser.parse_args(argv)


def main(argv: list[str]) -> int:
    args = parse_args(argv)
    fixture_path = REPO_ROOT / args.fixture
    errors: list[str] = []
    expected = build_fixture()

    check_firmware(errors)
    check_fixtures(errors)
    check_docs(errors)

    if args.write_fixture and not errors:
        fixture_path.parent.mkdir(parents=True, exist_ok=True)
        fixture_path.write_text(json.dumps(expected, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    if not args.write_fixture:
        check_fixture_file(fixture_path, expected, errors)

    if errors:
        print("FAIL: Companion ExpressionV1 signal guard checks failed:", file=sys.stderr)
        for error in errors:
            print(f" - {error}", file=sys.stderr)
        return 1
    print(f"PASS: Companion ExpressionV1 signal guard verified -> {rel(fixture_path)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
