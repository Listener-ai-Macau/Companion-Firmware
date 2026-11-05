#!/usr/bin/env python3
"""Render a hardware-facts worksheet for real e-paper panel bring-up."""

from __future__ import annotations

import argparse
import json
import pathlib
import sys
from typing import Any


REPO_ROOT = pathlib.Path(__file__).resolve().parents[1]
TOOLS_DIR = pathlib.Path(__file__).resolve().parent
if str(TOOLS_DIR) not in sys.path:
    sys.path.insert(0, str(TOOLS_DIR))

import init_expression_panel_evidence_record as init_record  # noqa: E402
import verify_expression_panel_driver_readiness as readiness  # noqa: E402
import verify_expression_panel_hardware_facts as hardware_facts  # noqa: E402


DEFAULT_JSON = pathlib.Path("docs/validation/companion-screen-panel-facts-worksheet.json")
DEFAULT_MARKDOWN = pathlib.Path("docs/validation/companion-screen-panel-facts-worksheet.md")
SCHEMA_ID = "companion.pendant.screen_panel_facts_worksheet.v1"

ACCEPTANCE_INDEX = REPO_ROOT / "docs/validation/companion-screen-acceptance-index.json"
DRIVER_READINESS = REPO_ROOT / "docs/validation/companion-screen-panel-driver-readiness.json"
FACTS_INTAKE = REPO_ROOT / "docs/validation/companion-screen-panel-hardware-facts-intake.json"
SCREEN_DOC = REPO_ROOT / "docs/companion_screen_expression_system.md"
EPAPER_README = REPO_ROOT / "app/companion_pendant/epaper/README.md"
BRINGUP_DOC = REPO_ROOT / "docs/bringup_steps.md"


FIELD_PROMPTS = {
    "panel_identity.controller_model": {
        "prompt": "Controller model from module docs or silkscreen.",
        "accepted_values": "Non-placeholder string, for example UC8151D.",
    },
    "panel_identity.panel_module_or_label": {
        "prompt": "Panel module name or label used for bench traceability.",
        "accepted_values": "Non-placeholder string.",
    },
    "panel_identity.datasheet_revision": {
        "prompt": "Datasheet revision used for timing/command sequence.",
        "accepted_values": "Non-placeholder string.",
    },
    "panel_identity.waveform_lut_source": {
        "prompt": "Waveform LUT source.",
        "accepted_values": "Non-placeholder string, for example controller OTP.",
    },
    "target_pin_map.dc_pin": {
        "prompt": "STM32 GPIO wired to panel DC.",
        "accepted_values": "STM32 pin like PB0.",
    },
    "target_pin_map.rst_pin": {
        "prompt": "STM32 GPIO wired to panel RST.",
        "accepted_values": "STM32 pin like PB1.",
    },
    "target_pin_map.busy_pin": {
        "prompt": "STM32 GPIO wired to panel BUSY.",
        "accepted_values": "STM32 pin like PB2.",
    },
    "target_pin_map.power_enable_pin": {
        "prompt": "Optional panel power-enable GPIO.",
        "accepted_values": "STM32 pin or not_present.",
    },
    "target_pin_map.logic_voltage": {
        "prompt": "Panel logic voltage.",
        "accepted_values": "1.8V, 3.0V, or 3.3V.",
    },
    "driver_timing.reset_low_ms": {
        "prompt": "Reset low pulse duration from datasheet.",
        "accepted_values": "Positive integer milliseconds.",
    },
    "driver_timing.reset_high_ms": {
        "prompt": "Delay after reset release from datasheet.",
        "accepted_values": "Positive integer milliseconds.",
    },
    "driver_timing.busy_timeout_ms": {
        "prompt": "Maximum BUSY wait for full refresh.",
        "accepted_values": "Positive integer milliseconds.",
    },
    "driver_timing.full_refresh_sequence": {
        "prompt": "Full refresh command sequence to implement.",
        "accepted_values": "Non-empty list of named steps.",
    },
    "driver_timing.partial_refresh_policy": {
        "prompt": "Initial partial-refresh policy.",
        "accepted_values": "Non-placeholder string; disabled is allowed until validated.",
    },
    "driver_timing.sleep_or_powerdown_sequence": {
        "prompt": "Sleep or powerdown command sequence after refresh.",
        "accepted_values": "Non-empty list of named steps.",
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


def load_json(path: pathlib.Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def nested_get(data: dict[str, Any], dotted_key: str) -> Any:
    value: Any = data
    for part in dotted_key.split("."):
        if not isinstance(value, dict):
            return None
        value = value.get(part)
    return value


def clean_md(value: object) -> str:
    if isinstance(value, list):
        return ", ".join(str(item) for item in value)
    return str(value).replace("|", "\\|").replace("\n", " ").strip()


def build_rows(facts: dict[str, Any], readiness_report: dict[str, Any]) -> list[dict[str, Any]]:
    missing_keys = {
        f"{item.get('section')}.{item.get('field')}"
        for item in readiness_report.get("missing_ready_fields", [])
        if isinstance(item, dict)
    }
    rows: list[dict[str, Any]] = []
    for dotted_key, meta in FIELD_PROMPTS.items():
        rows.append(
            {
                "field": dotted_key,
                "current_value": nested_get(facts, dotted_key),
                "required_for_ready": True,
                "status": "missing" if dotted_key in missing_keys else "filled",
                "prompt": meta["prompt"],
                "accepted_values": meta["accepted_values"],
            }
        )
    return rows


def operator_next_step(facts_path: pathlib.Path | None) -> str:
    if facts_path is not None:
        return (
            f"Fill each missing row in {rel(facts_path)}, then rerun "
            f"python .\\tools\\verify_expression_panel_driver_readiness.py --facts {rel(facts_path)} --require-ready."
        )
    return (
        "Fill each missing row in a session panel-hardware-facts.todo.json, then rerun "
        "python .\\tools\\verify_expression_panel_driver_readiness.py --facts <panel-hardware-facts.todo.json> --require-ready."
    )


def build_worksheet(facts: dict[str, Any], facts_path: pathlib.Path | None = None) -> dict[str, Any]:
    readiness_report = readiness.build_readiness_report(facts, facts_path)
    return {
        "schema_id": SCHEMA_ID,
        "status": "PASS",
        "purpose": "Operator-facing worksheet for filling real-panel hardware facts before target driver work starts.",
        "sources": {
            "worksheet_tool": "tools/render_expression_panel_facts_worksheet.py",
            "facts_intake": rel(FACTS_INTAKE),
            "driver_readiness": rel(DRIVER_READINESS),
            "screen_doc": rel(SCREEN_DOC),
            "epaper_readme": rel(EPAPER_README),
            "bringup_doc": rel(BRINGUP_DOC),
        },
        "target": facts.get("target"),
        "facts_status": facts.get("status"),
        "facts_path": rel(facts_path) if facts_path is not None else None,
        "readiness_status": readiness_report.get("readiness_status"),
        "missing_ready_field_count": readiness_report.get("missing_ready_field_count"),
        "known_transport": readiness_report.get("known_transport"),
        "worksheet_rows": build_rows(facts, readiness_report),
        "operator_next_step": operator_next_step(facts_path),
        "real_refresh_claimed": False,
        "panel_gate_must_remain": "DEFERRED_HARDWARE",
        "validation_commands": [
            "python .\\tools\\render_expression_panel_facts_worksheet.py",
            "python .\\tools\\render_expression_panel_facts_worksheet.py --self-test",
            "python .\\tools\\verify_expression_panel_driver_readiness.py",
            "python .\\tools\\verify_expression_panel_hardware_facts.py --self-test",
        ],
    }


def build_markdown(data: dict[str, Any]) -> str:
    transport = data.get("known_transport", {})
    lines = [
        "# Companion Panel Hardware Facts Worksheet",
        "",
        "This worksheet is generated. Update it with `python .\\tools\\render_expression_panel_facts_worksheet.py --write`.",
        "",
        "## Current Status",
        "",
        f"- Target: `{clean_md(data.get('target'))}`",
        f"- Facts status: `{clean_md(data.get('facts_status'))}`",
        f"- Driver readiness: `{clean_md(data.get('readiness_status'))}`",
        f"- Missing fields: `{clean_md(data.get('missing_ready_field_count'))}`",
        f"- Known transport: `{clean_md(transport.get('spi_instance_or_bus'))} SCK={clean_md(transport.get('sck_pin'))} MOSI={clean_md(transport.get('mosi_pin'))} MISO={clean_md(transport.get('miso_pin'))} CS={clean_md(transport.get('cs_pin'))}`",
        "",
        "## Fill These Fields",
        "",
        "| Status | Field | Current value | Accepted values | Prompt |",
        "|---|---|---|---|---|",
    ]
    for row in data.get("worksheet_rows", []):
        lines.append(
            "| "
            f"`{clean_md(row.get('status'))}` | `{clean_md(row.get('field'))}` | "
            f"`{clean_md(row.get('current_value'))}` | {clean_md(row.get('accepted_values'))} | "
            f"{clean_md(row.get('prompt'))} |"
        )
    lines.extend(["", f"Next step: {clean_md(data.get('operator_next_step'))}", ""])
    return "\n".join(lines)


def build_fixture() -> dict[str, Any]:
    return build_worksheet(init_record.build_hardware_facts_draft("WB55"))


def validate_worksheet(data: dict[str, Any], errors: list[str]) -> None:
    require(data.get("schema_id") == SCHEMA_ID, f"worksheet schema_id must be {SCHEMA_ID}", errors)
    require(data.get("status") == "PASS", "worksheet fixture status must be PASS", errors)
    require(data.get("real_refresh_claimed") is False, "worksheet must not claim real refresh", errors)
    require(data.get("panel_gate_must_remain") == "DEFERRED_HARDWARE", "worksheet must preserve deferred panel gate", errors)
    require(data.get("readiness_status") == "BLOCKED_ON_HARDWARE_FACTS", "fixture worksheet should reflect draft facts blocker", errors)
    rows = data.get("worksheet_rows", [])
    require(isinstance(rows, list) and len(rows) == len(FIELD_PROMPTS), "worksheet row count must match required fields", errors)
    fields = {row.get("field") for row in rows if isinstance(row, dict)}
    for field in FIELD_PROMPTS:
        require(field in fields, f"worksheet missing field {field}", errors)
    missing_count = sum(1 for row in rows if isinstance(row, dict) and row.get("status") == "missing")
    require(missing_count == data.get("missing_ready_field_count"), "worksheet missing row count must match readiness", errors)
    transport = data.get("known_transport", {})
    require(transport.get("spi_instance_or_bus") == "SPI2", "fixture worksheet must keep known WB55 SPI2 transport", errors)
    require(transport.get("sck_pin") == "PA9", "fixture worksheet must keep known WB55 SCK pin", errors)


def run_self_test() -> list[str]:
    errors: list[str] = []
    draft = build_fixture()
    validate_worksheet(draft, errors)
    require(draft.get("missing_ready_field_count") == 15, "draft worksheet should list 15 missing fields", errors)

    ready = build_worksheet(hardware_facts.build_ready_self_test_facts("WB55"))
    require(ready.get("readiness_status") == "READY_FOR_DRIVER_IMPLEMENTATION", "ready facts worksheet should report ready", errors)
    require(ready.get("missing_ready_field_count") == 0, "ready facts worksheet should have zero missing fields", errors)
    require(all(row.get("status") == "filled" for row in ready.get("worksheet_rows", [])), "ready worksheet rows should be filled", errors)
    return errors


def check_project_links(errors: list[str]) -> None:
    for path, name in [(SCREEN_DOC, "screen doc"), (EPAPER_README, "epaper README"), (BRINGUP_DOC, "bringup doc")]:
        require(path.exists(), f"missing {name}", errors)
        if not path.exists():
            continue
        text = path.read_text(encoding="utf-8")
        for token in [
            "panel_hardware_facts_worksheet",
            "companion-screen-panel-facts-worksheet.json",
            "companion-screen-panel-facts-worksheet.md",
            "render_expression_panel_facts_worksheet.py",
        ]:
            require(token in text, f"{name} missing panel facts worksheet anchor {token}", errors)

    require(ACCEPTANCE_INDEX.exists(), "missing acceptance index", errors)
    if ACCEPTANCE_INDEX.exists():
        index = load_json(ACCEPTANCE_INDEX)
        items = [item for item in index.get("items", []) if isinstance(item, dict) and item.get("id") == "panel_hardware_facts_worksheet"]
        require(len(items) == 1, "acceptance index must contain one panel_hardware_facts_worksheet item", errors)
        if items:
            item = items[0]
            require(item.get("status") == "PASS", "panel_hardware_facts_worksheet item must be PASS", errors)
            require(
                "docs/validation/companion-screen-panel-facts-worksheet.json" in item.get("evidence_paths", []),
                "panel_hardware_facts_worksheet item must link JSON fixture",
                errors,
            )


def write_outputs(json_path: pathlib.Path, markdown_path: pathlib.Path, data: dict[str, Any], markdown: str) -> None:
    json_path.parent.mkdir(parents=True, exist_ok=True)
    json_path.write_text(json.dumps(data, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    markdown_path.parent.mkdir(parents=True, exist_ok=True)
    markdown_path.write_text(markdown, encoding="utf-8")


def check_outputs(json_path: pathlib.Path, markdown_path: pathlib.Path, data: dict[str, Any], markdown: str, errors: list[str]) -> None:
    require(json_path.exists(), f"missing panel facts worksheet JSON: {rel(json_path)}", errors)
    if json_path.exists():
        require(load_json(json_path) == data, f"{rel(json_path)} is stale; rerun with --write", errors)
    require(markdown_path.exists(), f"missing panel facts worksheet Markdown: {rel(markdown_path)}", errors)
    if markdown_path.exists():
        require(markdown_path.read_text(encoding="utf-8") == markdown, f"{rel(markdown_path)} is stale; rerun with --write", errors)


def facts_path_from_args(args: argparse.Namespace) -> pathlib.Path | None:
    if args.session_root is not None:
        root = args.session_root if args.session_root.is_absolute() else REPO_ROOT / args.session_root
        return root / init_record.SESSION_FACTS_FILENAME
    if args.facts is not None:
        return args.facts if args.facts.is_absolute() else REPO_ROOT / args.facts
    return None


def parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--json", type=pathlib.Path, default=DEFAULT_JSON)
    parser.add_argument("--markdown", type=pathlib.Path, default=DEFAULT_MARKDOWN)
    parser.add_argument("--facts", type=pathlib.Path, default=None)
    parser.add_argument("--session-root", type=pathlib.Path, default=None)
    parser.add_argument("--write", action="store_true", help="Write the deterministic or requested worksheet outputs.")
    parser.add_argument("--self-test", action="store_true", help="Run draft/ready worksheet checks.")
    return parser.parse_args(argv)


def main(argv: list[str]) -> int:
    args = parse_args(argv)
    json_path = args.json if args.json.is_absolute() else REPO_ROOT / args.json
    markdown_path = args.markdown if args.markdown.is_absolute() else REPO_ROOT / args.markdown
    errors: list[str] = []

    facts_path = facts_path_from_args(args)
    if facts_path is None:
        data = build_fixture()
    else:
        if not facts_path.exists():
            data = build_fixture()
            errors.append(f"facts file missing: {rel(facts_path)}")
        else:
            data = build_worksheet(load_json(facts_path), facts_path)
    markdown = build_markdown(data)
    validate_worksheet(data, errors)
    if args.self_test:
        errors.extend(run_self_test())
    if facts_path is None and not args.write:
        check_project_links(errors)
    if args.write and not errors:
        write_outputs(json_path, markdown_path, data, markdown)
    if not args.write and facts_path is None:
        check_outputs(json_path, markdown_path, data, markdown, errors)

    if errors:
        print("FAIL: Companion panel facts worksheet checks failed:", file=sys.stderr)
        for error in errors:
            print(f" - {error}", file=sys.stderr)
        return 1
    print(f"PASS: Companion panel facts worksheet verified -> {rel(json_path)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
