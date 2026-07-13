#!/usr/bin/env python3
"""Verify ExpressionV1 title/body/footer copy stays aligned across renderer, firmware, and fixtures."""

from __future__ import annotations

import argparse
import hashlib
import json
import pathlib
import re
import sys
from typing import Any


REPO_ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT))

from app.companion_pendant.epaper.card_renderer import EXPRESSION_COPY, EXPRESSION_KINDS  # noqa: E402


DEFAULT_FIXTURE = pathlib.Path("docs/validation/companion-screen-expression-copy-contract.json")
SCHEMA_ID = "companion.pendant.screen_expression_copy_contract.v1"

RENDERER = REPO_ROOT / "app" / "companion_pendant" / "epaper" / "card_renderer.py"
POLICY = REPO_ROOT / "app" / "companion_pendant" / "epaper" / "expression_policy.py"
FIRMWARE_HEADER = REPO_ROOT / "app" / "companion_pendant" / "epaper" / "expression_state.h"
FIRMWARE_SOURCE = REPO_ROOT / "app" / "companion_pendant" / "epaper" / "expression_state.c"
CATALOG_FIXTURE = REPO_ROOT / "docs" / "validation" / "companion-screen-expression-catalog.json"
FIRMWARE_FIXTURE = REPO_ROOT / "docs" / "validation" / "companion-screen-firmware-expression-state.json"
LAYOUT_FIXTURE = REPO_ROOT / "docs" / "validation" / "companion-screen-expression-layout-contract.json"
PRIORITY_FIXTURE = REPO_ROOT / "docs" / "validation" / "companion-screen-expression-priority-matrix.json"
EPAPER_FIXTURE = REPO_ROOT / "docs" / "validation" / "companion-pendant-firmware-bringup-1.6-epaper-fixtures.json"
SCREEN_DOC = REPO_ROOT / "docs" / "companion_screen_expression_system.md"
WBA_RULES = REPO_ROOT / "docs" / "stm32wba_migration_rules.md"
README = REPO_ROOT / "app" / "companion_pendant" / "epaper" / "README.md"
ACCEPTANCE_INDEX = REPO_ROOT / "docs" / "validation" / "companion-screen-acceptance-index.json"

EXPECTED_EXPRESSIONS = [
    "idle",
    "listening",
    "thinking",
    "speaking",
    "happy",
    "sleepy",
    "recording",
    "sync_complete",
    "low_battery",
    "error",
]

EXPRESSION_RE = re.compile(
    r'\{COMP_EPAPER_EXPRESSION_([A-Z_]+),\s*(\d+)u,\s*"([^"]+)",\s*"([^"]+)",\s*"([^"]+)",\s*"([^"]+)"\}'
)


def rel(path: pathlib.Path) -> str:
    try:
        return path.resolve().relative_to(REPO_ROOT).as_posix()
    except ValueError:
        return path.as_posix()


def require(condition: bool, message: str, errors: list[str]) -> None:
    if not condition:
        errors.append(message)


def read_text(path: pathlib.Path, errors: list[str]) -> str:
    require(path.exists(), f"missing required path {rel(path)}", errors)
    if not path.exists():
        return ""
    return path.read_text(encoding="utf-8")


def read_json(path: pathlib.Path, errors: list[str]) -> dict[str, Any]:
    text = read_text(path, errors)
    if not text:
        return {}
    return json.loads(text)


def copy_tuple_to_dict(copy: tuple[str, str, str]) -> dict[str, str]:
    title, body, footer = copy
    return {"title": title, "body": body, "footer": footer}


def parse_firmware_copy(source: str) -> dict[str, dict[str, str]]:
    parsed: dict[str, dict[str, str]] = {}
    for _symbol, _priority, name, title, body, footer in EXPRESSION_RE.findall(source):
        parsed[name] = {"title": title, "body": body, "footer": footer}
    return parsed


def copy_hash(expressions: list[dict[str, Any]]) -> str:
    data = [
        {
            "expression": entry["expression"],
            "title": entry["renderer"]["title"],
            "body": entry["renderer"]["body"],
            "footer": entry["renderer"]["footer"],
        }
        for entry in expressions
    ]
    encoded = json.dumps(data, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def fixture_copy_map(data: dict[str, Any], list_key: str, name_key: str = "name") -> dict[str, dict[str, str]]:
    result: dict[str, dict[str, str]] = {}
    for item in data.get(list_key, []):
        if not isinstance(item, dict):
            continue
        name = str(item.get(name_key, ""))
        if name in EXPRESSION_KINDS:
            result[name] = {
                "title": str(item.get("title", "")),
                "body": str(item.get("body", "")),
                "footer": str(item.get("footer", "")),
            }
    return result


def layout_copy_map(data: dict[str, Any]) -> dict[str, dict[str, str]]:
    result: dict[str, dict[str, str]] = {}
    for metric in data.get("metrics", []):
        if not isinstance(metric, dict):
            continue
        name = str(metric.get("expression", ""))
        if name in EXPRESSION_KINDS:
            result[name] = {
                "title": str(metric.get("title", "")),
                "body": str(metric.get("body", "")),
                "footer": str(metric.get("footer", "")),
            }
    return result


def epaper_manifest_copy_map(data: dict[str, Any]) -> dict[str, dict[str, str]]:
    result: dict[str, dict[str, str]] = {}
    for fixture in data.get("fixtures", []):
        if not isinstance(fixture, dict):
            continue
        card = fixture.get("card", {})
        if not isinstance(card, dict) or card.get("card_type") != "expression":
            continue
        name = str(card.get("state", ""))
        if name in EXPRESSION_KINDS:
            result[name] = {
                "title": str(card.get("title", "")),
                "body": str(card.get("body", "")),
                "footer": str(card.get("footer", "")),
            }
    return result


def build_contract() -> dict[str, Any]:
    firmware_copy = parse_firmware_copy(FIRMWARE_SOURCE.read_text(encoding="utf-8"))
    catalog_copy = fixture_copy_map(json.loads(CATALOG_FIXTURE.read_text(encoding="utf-8")), "expressions")
    firmware_fixture_copy = fixture_copy_map(json.loads(FIRMWARE_FIXTURE.read_text(encoding="utf-8")), "expressions")
    layout_copy = layout_copy_map(json.loads(LAYOUT_FIXTURE.read_text(encoding="utf-8")))
    priority_copy = fixture_copy_map(json.loads(PRIORITY_FIXTURE.read_text(encoding="utf-8")), "expressions")
    epaper_copy = epaper_manifest_copy_map(json.loads(EPAPER_FIXTURE.read_text(encoding="utf-8")))

    expressions: list[dict[str, Any]] = []
    for expression in EXPECTED_EXPRESSIONS:
        renderer_copy = copy_tuple_to_dict(EXPRESSION_COPY[expression])
        expressions.append(
            {
                "expression": expression,
                "renderer": renderer_copy,
                "firmware": firmware_copy.get(expression, {}),
                "catalog": catalog_copy.get(expression, {}),
                "firmware_fixture": firmware_fixture_copy.get(expression, {}),
                "layout_fixture": layout_copy.get(expression, {}),
                "priority_matrix": priority_copy.get(expression, {}),
                "epaper_manifest": epaper_copy.get(expression, {}),
            }
        )

    return {
        "schema_id": SCHEMA_ID,
        "status": "PASS",
        "purpose": "Keep ExpressionV1 user-visible title/body/footer copy synchronized across renderer, firmware, generated fixtures, and WBA adapter contracts.",
        "sources": {
            "renderer": rel(RENDERER),
            "policy": rel(POLICY),
            "firmware_header": rel(FIRMWARE_HEADER),
            "firmware_source": rel(FIRMWARE_SOURCE),
            "catalog_fixture": rel(CATALOG_FIXTURE),
            "firmware_state_fixture": rel(FIRMWARE_FIXTURE),
            "layout_fixture": rel(LAYOUT_FIXTURE),
            "priority_matrix": rel(PRIORITY_FIXTURE),
            "epaper_manifest": rel(EPAPER_FIXTURE),
            "screen_acceptance": rel(SCREEN_DOC),
            "wba_rules": rel(WBA_RULES),
            "epaper_readme": rel(README),
        },
        "copy_contract": {
            "expression_count": len(EXPECTED_EXPRESSIONS),
            "copy_locale": "en",
            "fields": ["title", "body", "footer"],
            "renderer_and_firmware_must_match": True,
            "generated_fixtures_must_match_renderer": True,
            "wba_reuses_same_copy": True,
        },
        "copy_sha256": copy_hash(expressions),
        "expressions": expressions,
        "validation_commands": [
            "python .\\tools\\verify_expression_copy_contract.py",
            "python .\\tools\\verify_expression_catalog_contract.py",
            "python .\\tools\\verify_expression_firmware_state.py",
            "python .\\tools\\verify_expression_layout_contract.py",
            "python .\\tools\\verify_expression_priority_matrix.py",
            "python .\\tools\\verify_epaper_assets.py",
        ],
    }


def check_copy_maps(data: dict[str, Any], errors: list[str]) -> None:
    expressions = data.get("expressions", [])
    require([entry.get("expression") for entry in expressions] == EXPECTED_EXPRESSIONS, "ExpressionV1 copy order drifted", errors)
    for entry in expressions:
        if not isinstance(entry, dict):
            errors.append("ExpressionV1 copy entry must be an object")
            continue
        expression = str(entry.get("expression", ""))
        expected = copy_tuple_to_dict(EXPRESSION_COPY[expression])
        for source_key in [
            "renderer",
            "firmware",
            "catalog",
            "firmware_fixture",
            "layout_fixture",
            "priority_matrix",
            "epaper_manifest",
        ]:
            require(entry.get(source_key) == expected, f"{expression} {source_key} copy drifted", errors)


def check_contract_data(data: dict[str, Any], errors: list[str]) -> None:
    require(data.get("schema_id") == SCHEMA_ID, "unexpected ExpressionV1 copy contract schema", errors)
    require(data.get("status") == "PASS", "ExpressionV1 copy contract fixture must be PASS", errors)
    contract = data.get("copy_contract", {})
    require(contract.get("expression_count") == len(EXPECTED_EXPRESSIONS), "ExpressionV1 copy expression count drifted", errors)
    require(contract.get("copy_locale") == "en", "ExpressionV1 copy locale drifted", errors)
    require(contract.get("fields") == ["title", "body", "footer"], "ExpressionV1 copy fields drifted", errors)
    for token in ["renderer_and_firmware_must_match", "generated_fixtures_must_match_renderer", "wba_reuses_same_copy"]:
        require(contract.get(token) is True, f"ExpressionV1 copy contract missing {token}", errors)
    check_copy_maps(data, errors)
    require(data.get("copy_sha256") == copy_hash(data.get("expressions", [])), "ExpressionV1 copy hash drifted", errors)


def check_code_hooks(errors: list[str]) -> None:
    renderer = read_text(RENDERER, errors)
    policy = read_text(POLICY, errors)
    firmware = read_text(FIRMWARE_SOURCE, errors)
    for token in ["EXPRESSION_COPY", "expression_fixture_cards", "render_expression_card"]:
        require(token in renderer, f"renderer missing ExpressionV1 copy hook {token}", errors)
    require("from .card_renderer import EXPRESSION_COPY" in policy, "policy must consume renderer ExpressionV1 copy", errors)
    require("out_decision->title = expression_def->title;" in firmware, "firmware decision must expose ExpressionV1 title", errors)
    require("out_decision->body = expression_def->body;" in firmware, "firmware decision must expose ExpressionV1 body", errors)
    require("out_decision->footer = expression_def->footer;" in firmware, "firmware decision must expose ExpressionV1 footer", errors)


def check_project_links(errors: list[str], allow_stale_index: bool = False) -> None:
    screen_doc = read_text(SCREEN_DOC, errors)
    wba_rules = read_text(WBA_RULES, errors)
    readme = read_text(README, errors)
    for text, name in [(screen_doc, "screen doc"), (wba_rules, "WBA rules"), (readme, "epaper README")]:
        for token in [
            "expression_copy_contract",
            "ExpressionV1 copy contract",
            "companion-screen-expression-copy-contract.json",
            "verify_expression_copy_contract.py",
            "title/body/footer",
        ]:
            require(token in text, f"{name} missing ExpressionV1 copy contract anchor {token}", errors)
    if allow_stale_index:
        return
    index = read_json(ACCEPTANCE_INDEX, errors)
    matches = [
        item
        for item in index.get("items", [])
        if isinstance(item, dict) and item.get("id") == "expression_copy_contract"
    ]
    require(len(matches) == 1, "acceptance index must contain one expression_copy_contract item", errors)
    if matches:
        item = matches[0]
        require(item.get("status") == "PASS", "expression_copy_contract item must be PASS", errors)
        require(
            "docs/validation/companion-screen-expression-copy-contract.json" in item.get("evidence_paths", []),
            "expression_copy_contract item must link its fixture",
            errors,
        )
        require(
            "python .\\tools\\verify_expression_copy_contract.py" in item.get("validation_commands", []),
            "expression_copy_contract item must run its verifier",
            errors,
        )


def check_fixture_file(path: pathlib.Path, expected: dict[str, Any], errors: list[str]) -> None:
    require(path.exists(), f"missing ExpressionV1 copy contract fixture: {rel(path)}", errors)
    if not path.exists():
        return
    actual = json.loads(path.read_text(encoding="utf-8"))
    require(actual == expected, f"{rel(path)} is stale; rerun with --write-fixture", errors)
    check_contract_data(actual, errors)


def parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--fixture", type=pathlib.Path, default=DEFAULT_FIXTURE)
    parser.add_argument("--write-fixture", action="store_true", help="Update the deterministic ExpressionV1 copy contract fixture.")
    return parser.parse_args(argv)


def main(argv: list[str]) -> int:
    args = parse_args(argv)
    fixture_path = args.fixture if args.fixture.is_absolute() else REPO_ROOT / args.fixture
    errors: list[str] = []
    for path in [
        RENDERER,
        POLICY,
        FIRMWARE_HEADER,
        FIRMWARE_SOURCE,
        CATALOG_FIXTURE,
        FIRMWARE_FIXTURE,
        LAYOUT_FIXTURE,
        PRIORITY_FIXTURE,
        EPAPER_FIXTURE,
        SCREEN_DOC,
        WBA_RULES,
        README,
    ]:
        require(path.exists(), f"missing required path {rel(path)}", errors)

    expected = build_contract() if not errors else {}
    if expected:
        check_contract_data(expected, errors)
    check_code_hooks(errors)
    check_project_links(errors, allow_stale_index=bool(args.write_fixture))

    if args.write_fixture and expected and not errors:
        fixture_path.parent.mkdir(parents=True, exist_ok=True)
        fixture_path.write_text(json.dumps(expected, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    if not args.write_fixture and expected:
        check_fixture_file(fixture_path, expected, errors)

    if errors:
        print("FAIL: Companion ExpressionV1 copy contract checks failed:", file=sys.stderr)
        for error in errors:
            print(f" - {error}", file=sys.stderr)
        return 1
    print(f"PASS: Companion ExpressionV1 copy contract verified -> {rel(fixture_path)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
