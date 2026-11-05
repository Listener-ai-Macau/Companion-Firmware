#!/usr/bin/env python3
"""Verify host decoding of e_paper.runtime_snapshot diagnostic payloads."""

from __future__ import annotations

import argparse
import importlib.util
import json
import pathlib
import sys
from typing import Any


REPO_ROOT = pathlib.Path(__file__).resolve().parents[1]
DEFAULT_FIXTURE = pathlib.Path("docs/validation/companion-screen-runtime-diagnostic-decode.json")
SCHEMA_ID = "companion.pendant.screen_runtime_diagnostic_decode.v1"

DECODE_TOOL = REPO_ROOT / "tools" / "decode_diag_log.py"
DIAG_EVENTS = REPO_ROOT / "app" / "companion_pendant" / "diag_log" / "diag_log_events.h"
RUNTIME_DIAGNOSTICS_FIXTURE = REPO_ROOT / "docs" / "validation" / "companion-screen-runtime-diagnostics.json"
SCREEN_DOC = REPO_ROOT / "docs" / "companion_screen_expression_system.md"
WBA_RULES = REPO_ROOT / "docs" / "stm32wba_migration_rules.md"
README = REPO_ROOT / "app" / "companion_pendant" / "epaper" / "README.md"
ACCEPTANCE_INDEX = REPO_ROOT / "docs" / "validation" / "companion-screen-acceptance-index.json"

RAW_RUNTIME_EVENT = {
    "sequence": 9001,
    "t_ms": 1234,
    "source": "e_paper",
    "event_id": 3,
    "severity": "warn",
    "arg0": (5 << 16) | 3,
    "arg1": (2 << 16) | 4,
    "arg2": 1,
    "arg3": (7 << 16) | 1,
}

EXPECTED_DECODED_ARGS = {
    "payload": "screen_runtime_snapshot",
    "expression": {
        "current": 5,
        "last_signal": 3,
    },
    "display_queue": {
        "pending_count": 2,
        "high_water_count": 4,
        "dropped_count": 1,
    },
    "panel": {
        "deferred_count": 7,
        "error_count": 1,
    },
}


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


def load_decode_tool(errors: list[str]) -> Any | None:
    require(DECODE_TOOL.exists(), f"missing decode tool {rel(DECODE_TOOL)}", errors)
    if not DECODE_TOOL.exists():
        return None
    spec = importlib.util.spec_from_file_location("decode_diag_log_for_runtime_test", DECODE_TOOL)
    if spec is None or spec.loader is None:
        errors.append("could not load decode_diag_log.py module spec")
        return None
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def build_fixture() -> dict[str, Any]:
    return {
        "schema_id": SCHEMA_ID,
        "status": "PASS",
        "purpose": "Host-side decoded payload contract for e_paper.runtime_snapshot diagnostics.",
        "sources": {
            "decode_tool": rel(DECODE_TOOL),
            "diag_events": rel(DIAG_EVENTS),
            "runtime_diagnostics_fixture": rel(RUNTIME_DIAGNOSTICS_FIXTURE),
            "screen_acceptance": rel(SCREEN_DOC),
            "wba_rules": rel(WBA_RULES),
            "epaper_readme": rel(README),
        },
        "raw_event": RAW_RUNTIME_EVENT,
        "expected_event": {
            "name": "e_paper.runtime_snapshot",
            "symbol": "RUNTIME_SNAPSHOT",
            "severity": "warn",
        },
        "expected_decoded_args": EXPECTED_DECODED_ARGS,
        "validation_commands": [
            "python .\\tools\\verify_expression_screen_runtime_diagnostic_decode.py",
            "python .\\tools\\verify_expression_screen_runtime_diagnostics.py",
            "python .\\tools\\decode_diag_log.py --self-test",
            "python .\\tools\\verify_expression_wba_portability.py",
        ],
    }


def decode_sample(errors: list[str]) -> dict[str, Any]:
    module = load_decode_tool(errors)
    if module is None:
        return {}
    schema = module.load_schema(DIAG_EVENTS)
    decoded = module.decode_events([RAW_RUNTIME_EVENT], schema)
    events = decoded.get("events", [])
    require(len(events) == 1, "runtime diagnostic sample should decode one event", errors)
    return events[0] if events else {}


def check_decode_tool(errors: list[str]) -> None:
    text = read(DECODE_TOOL, errors)
    for token in [
        "def decode_event_args",
        'event_name == "e_paper.runtime_snapshot"',
        '"payload": "screen_runtime_snapshot"',
        '"pending_count": u16_high(args["arg1"])',
        '"error_count": u16_low(args["arg3"])',
        "e_paper.runtime_snapshot",
    ]:
        require(token in text, f"decode_diag_log.py missing runtime decode token {token}", errors)


def check_decoded_sample(decoded_event: dict[str, Any], errors: list[str]) -> None:
    if not decoded_event:
        return
    require(decoded_event.get("event", {}).get("name") == "e_paper.runtime_snapshot", "decoded event name drifted", errors)
    require(decoded_event.get("event", {}).get("symbol") == "RUNTIME_SNAPSHOT", "decoded event symbol drifted", errors)
    require(decoded_event.get("severity", {}).get("name") == "warn", "decoded severity drifted", errors)
    require(
        decoded_event.get("decoded_args") == EXPECTED_DECODED_ARGS,
        "decoded runtime payload fields drifted",
        errors,
    )


def check_fixture_data(data: dict[str, Any], errors: list[str]) -> None:
    require(data.get("schema_id") == SCHEMA_ID, "unexpected runtime diagnostic decode schema", errors)
    require(data.get("status") == "PASS", "runtime diagnostic decode fixture must be PASS", errors)
    require(data.get("raw_event") == RAW_RUNTIME_EVENT, "runtime diagnostic decode raw event drifted", errors)
    require(
        data.get("expected_decoded_args") == EXPECTED_DECODED_ARGS,
        "runtime diagnostic decode expected args drifted",
        errors,
    )
    expected_event = data.get("expected_event", {})
    require(expected_event.get("name") == "e_paper.runtime_snapshot", "fixture missing decoded event name", errors)
    require(expected_event.get("symbol") == "RUNTIME_SNAPSHOT", "fixture missing decoded event symbol", errors)
    require(expected_event.get("severity") == "warn", "fixture missing decoded severity", errors)


def check_docs_and_index(errors: list[str]) -> None:
    screen_doc = read(SCREEN_DOC, errors)
    wba_rules = read(WBA_RULES, errors)
    readme = read(README, errors)
    runtime_fixture = read(RUNTIME_DIAGNOSTICS_FIXTURE, errors)
    index_text = read(ACCEPTANCE_INDEX, errors)
    for token in [
        "screen_runtime_diagnostic_decode",
        "Screen runtime diagnostic decode",
        "companion-screen-runtime-diagnostic-decode.json",
        "verify_expression_screen_runtime_diagnostic_decode.py",
        "decoded_args",
    ]:
        require(token in screen_doc, f"screen expression doc missing runtime decode anchor {token}", errors)
    for token in ["runtime diagnostic decode", "decoded_args", "e_paper.runtime_snapshot"]:
        require(token.lower() in wba_rules.lower(), f"WBA rules missing runtime decode anchor {token}", errors)
    for token in ["runtime diagnostic decode", "decoded_args", "verify_expression_screen_runtime_diagnostic_decode.py"]:
        require(token.lower() in readme.lower(), f"e-paper README missing runtime decode anchor {token}", errors)
    for token in ["verify_expression_screen_runtime_diagnostic_decode.py", "decoded_args"]:
        require(token in runtime_fixture, f"runtime diagnostics fixture missing decode anchor {token}", errors)
    if index_text:
        index = json.loads(index_text)
        items = [item for item in index.get("items", []) if isinstance(item, dict)]
        matches = [item for item in items if item.get("id") == "screen_runtime_diagnostic_decode"]
        require(len(matches) == 1, "acceptance index must contain one screen_runtime_diagnostic_decode item", errors)
        if matches:
            item = matches[0]
            require(item.get("status") == "PASS", "screen_runtime_diagnostic_decode item must be PASS", errors)
            require(
                "docs/validation/companion-screen-runtime-diagnostic-decode.json" in item.get("evidence_paths", []),
                "screen_runtime_diagnostic_decode item must link decode fixture",
                errors,
            )
            require(
                "python .\\tools\\verify_expression_screen_runtime_diagnostic_decode.py" in item.get("validation_commands", []),
                "screen_runtime_diagnostic_decode item must run decode verifier",
                errors,
            )


def check_fixture_file(path: pathlib.Path, expected: dict[str, Any], errors: list[str]) -> None:
    require(path.exists(), f"missing runtime diagnostic decode fixture: {rel(path)}", errors)
    if not path.exists():
        return
    actual = json.loads(path.read_text(encoding="utf-8"))
    require(actual == expected, f"{rel(path)} is stale; rerun with --write-fixture", errors)
    check_fixture_data(actual, errors)


def parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--fixture", type=pathlib.Path, default=DEFAULT_FIXTURE)
    parser.add_argument("--write-fixture", action="store_true", help="Update the deterministic runtime diagnostic decode fixture.")
    return parser.parse_args(argv)


def main(argv: list[str]) -> int:
    args = parse_args(argv)
    fixture_path = REPO_ROOT / args.fixture
    expected = build_fixture()
    errors: list[str] = []

    check_fixture_data(expected, errors)
    check_decode_tool(errors)
    decoded_event = decode_sample(errors)
    check_decoded_sample(decoded_event, errors)
    if not args.write_fixture:
        check_docs_and_index(errors)
        check_fixture_file(fixture_path, expected, errors)

    if args.write_fixture and not errors:
        fixture_path.parent.mkdir(parents=True, exist_ok=True)
        fixture_path.write_text(json.dumps(expected, indent=2, sort_keys=True) + "\n", encoding="utf-8")

    if errors:
        print("FAIL: Companion screen runtime diagnostic decode checks failed:", file=sys.stderr)
        for error in errors:
            print(f" - {error}", file=sys.stderr)
        return 1
    print(f"PASS: Companion screen runtime diagnostic decode verified -> {rel(fixture_path)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
