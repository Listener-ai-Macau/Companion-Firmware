#!/usr/bin/env python3
"""Create or verify a scaffold for a real-panel evidence record."""

from __future__ import annotations

import argparse
import json
import pathlib
import sys
from typing import Any


REPO_ROOT = pathlib.Path(__file__).resolve().parents[1]
DEFAULT_OUTPUT = REPO_ROOT / "docs/validation/companion-screen-panel-evidence-record-scaffold.json"
EXPRESSION_FIXTURES = REPO_ROOT / "docs/validation/companion-pendant-firmware-bringup-1.6-epaper-fixtures.json"
PANEL_WIRING_PREFLIGHT = REPO_ROOT / "docs/validation/companion-screen-panel-wiring-preflight.json"
RECORD_SCHEMA_ID = "companion.pendant.screen_panel_evidence_record.v1"
TARGETS = ("WB55", "WBA55", "WBA65")
SESSION_RECORD_FILENAME = "panel-evidence-record.json"
SESSION_FACTS_FILENAME = "panel-hardware-facts.todo.json"


def rel(path: pathlib.Path) -> str:
    try:
        return path.resolve().relative_to(REPO_ROOT).as_posix()
    except ValueError:
        return path.as_posix()


def load_json(path: pathlib.Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def expression_fixture(expression: str, variant: str) -> dict[str, Any]:
    data = load_json(EXPRESSION_FIXTURES)
    for item in data.get("fixtures", []):
        if not isinstance(item, dict):
            continue
        card = item.get("card", {})
        if (
            isinstance(card, dict)
            and card.get("card_type") == "expression"
            and card.get("state") == expression
            and item.get("variant") == variant
        ):
            return item
    raise ValueError(f"missing expression fixture for {expression}/{variant}")


def adapter_placeholder(target: str) -> str:
    if target == "WB55":
        return "TODO_TARGET_ADAPTER_FILE_*_stm32wb.*"
    return "TODO_TARGET_ADAPTER_FILE_*_stm32wba.*"


def target_pin_map_scaffold(target: str) -> dict[str, Any]:
    if target != "WB55":
        return {
            "target_family": target,
            "spi_instance_or_bus": "TODO_SPI_INSTANCE_OR_BUS",
            "sck_pin": "TODO_SCK_PIN",
            "mosi_pin": "TODO_MOSI_PIN",
            "cs_pin": "TODO_CS_PIN",
            "dc_pin": "TODO_DC_PIN",
            "rst_pin": "TODO_RST_PIN",
            "busy_pin": "TODO_BUSY_PIN",
            "power_enable_pin": "TODO_POWER_ENABLE_PIN_OR_NOT_PRESENT",
            "logic_voltage": "TODO_LOGIC_VOLTAGE",
        }
    preflight = load_json(PANEL_WIRING_PREFLIGHT)
    transport = preflight.get("wb55_devboard_transport", {})
    return {
        "target_family": target,
        "spi_instance_or_bus": transport.get("spi_instance"),
        "sck_pin": transport.get("sck", {}).get("pin"),
        "mosi_pin": transport.get("mosi", {}).get("pin"),
        "miso_pin": transport.get("miso", {}).get("pin"),
        "cs_pin": transport.get("chip_select_candidate", {}).get("pin"),
        "cs_label": transport.get("chip_select_candidate", {}).get("label"),
        "wiring_preflight": rel(PANEL_WIRING_PREFLIGHT),
        "dc_pin": "TODO_DC_PIN",
        "rst_pin": "TODO_RST_PIN",
        "busy_pin": "TODO_BUSY_PIN",
        "power_enable_pin": "TODO_POWER_ENABLE_PIN_OR_NOT_PRESENT",
        "logic_voltage": "TODO_LOGIC_VOLTAGE",
    }


def build_hardware_facts_draft(target: str, expression: str = "idle", variant: str = "2.13in") -> dict[str, Any]:
    fixture = expression_fixture(expression, variant)
    return {
        "schema_id": "companion.pendant.screen_panel_hardware_facts.v1",
        "status": "DRAFT_UNFILLED",
        "target": target,
        "claim_scope": "hardware_facts_only_no_real_refresh",
        "session_record": SESSION_RECORD_FILENAME,
        "panel_identity": {
            "controller_model": "TODO_CONTROLLER_MODEL",
            "panel_module_or_label": "TODO_PANEL_MODULE_OR_LABEL",
            "panel_variant": variant,
            "resolution_px": [int(fixture["width"]), int(fixture["height"])],
            "datasheet_revision": "TODO_DATASHEET_REVISION",
            "waveform_lut_source": "TODO_WAVEFORM_LUT_SOURCE",
        },
        "target_pin_map": target_pin_map_scaffold(target),
        "driver_timing": {
            "reset_low_ms": "TODO_RESET_LOW_MS_INTEGER",
            "reset_high_ms": "TODO_RESET_HIGH_MS_INTEGER",
            "busy_timeout_ms": "TODO_BUSY_TIMEOUT_MS_INTEGER",
            "full_refresh_sequence": ["TODO_FULL_REFRESH_STEP_1"],
            "partial_refresh_policy": "TODO_PARTIAL_REFRESH_POLICY",
            "sleep_or_powerdown_sequence": ["TODO_SLEEP_OR_POWERDOWN_STEP_1"],
        },
        "acceptance_guard": {
            "does_not_claim_real_refresh": True,
            "panel_gate_must_remain": "DEFERRED_HARDWARE",
            "final_evidence_record_must_stay_draft_until_ble_diagnostics_visual_evidence": True,
        },
        "operator_questions": [
            "What is the e-paper controller model printed in the module docs or silkscreen?",
            "Which target GPIOs are wired to DC, RST, BUSY, and optional power enable? Use not_present if there is no power enable pin.",
            "What reset and BUSY timing does the controller datasheet require?",
            "Which full refresh and sleep sequence should the target adapter implement?",
        ],
    }


def build_record(target: str, expression: str, variant: str) -> dict[str, Any]:
    fixture = expression_fixture(expression, variant)
    return {
        "_instructions": [
            "This scaffold is intentionally invalid until every TODO is replaced.",
            "Run python .\\tools\\verify_expression_panel_evidence_record.py --record <this-file> before moving wb55_real_panel_refresh out of DEFERRED_HARDWARE.",
            "Run tools\\companion_ble_real_bench.py with --expect-real-panel and put that JSON path in host_observability.real_ble_bench_artifact.",
            "The real BLE artifact must include the screen_expression_status contract operation linked to companion-screen-expression-host-status-sequence.json.",
            "The real BLE artifact must also include screen_expression_demo_status linked to companion-screen-expression-demo-host-status-sequence.json.",
            "Run tools\\collect_companion_diagnostics.ps1 and put summary.json in host_observability.diagnostics_bundle_artifact.",
            "Set evidence_sha256 to the SHA-256 of visual_evidence.after_photo.",
        ],
        "schema_id": RECORD_SCHEMA_ID,
        "status": "DRAFT_UNFILLED",
        "claim_scope": "real_panel_refresh",
        "panel_identity": {
            "controller_model": "TODO_CONTROLLER_MODEL",
            "panel_variant": variant,
            "resolution_px": [int(fixture["width"]), int(fixture["height"])],
            "datasheet_revision": "TODO_DATASHEET_REVISION",
            "waveform_lut_source": "TODO_WAVEFORM_LUT_SOURCE",
        },
        "target_pin_map": target_pin_map_scaffold(target),
        "driver_timing": {
            "reset_low_ms": "TODO_RESET_LOW_MS_INTEGER",
            "reset_high_ms": "TODO_RESET_HIGH_MS_INTEGER",
            "busy_timeout_ms": "TODO_BUSY_TIMEOUT_MS_INTEGER",
            "full_refresh_sequence": ["TODO_FULL_REFRESH_STEP_1"],
            "partial_refresh_policy": "TODO_PARTIAL_REFRESH_POLICY",
            "sleep_or_powerdown_sequence": ["TODO_SLEEP_OR_POWERDOWN_STEP_1"],
        },
        "host_observability": {
            "request_id": "TODO_REQUEST_ID_INTEGER",
            "content_crc32": "TODO_CONTENT_CRC32_HEX",
            "CardStatusV1_accepted": {
                "render_state": "accepted",
                "last_error": "ok",
                "request_id": "TODO_REQUEST_ID_INTEGER",
                "content_crc32": "TODO_CONTENT_CRC32_HEX",
            },
            "CardStatusV1_rendered": {
                "render_state": "rendered",
                "last_error": "ok",
                "request_id": "TODO_REQUEST_ID_INTEGER",
                "content_crc32": "TODO_CONTENT_CRC32_HEX",
            },
            "e_paper.render_request": {
                "request_id": "TODO_REQUEST_ID_INTEGER",
                "content_crc32": "TODO_CONTENT_CRC32_HEX",
            },
            "e_paper.update_result": {
                "request_id": "TODO_REQUEST_ID_INTEGER",
                "content_crc32": "TODO_CONTENT_CRC32_HEX",
                "panel_result": "ok",
            },
            "e_paper.runtime_snapshot": {
                "severity": "info",
                "decoded_args": {
                    "payload": "screen_runtime_snapshot",
                    "expression": {
                        "current": "TODO_EXPRESSION_ID_INTEGER",
                        "last_signal": "TODO_SIGNAL_ID_INTEGER",
                    },
                    "display_queue": {
                        "pending_count": 0,
                        "high_water_count": "TODO_QUEUE_HIGH_WATER_INTEGER",
                        "dropped_count": 0,
                    },
                    "panel": {
                        "deferred_count": "TODO_PANEL_DEFERRED_COUNT_INTEGER",
                        "error_count": 0,
                    },
                },
            },
            "diagnostics_bundle_artifact": "TODO_PATH_TO_COLLECT_COMPANION_DIAGNOSTICS_SUMMARY_JSON",
            "real_ble_bench_artifact": "TODO_PATH_TO_EXPECT_REAL_PANEL_REAL_BLE_BENCH_JSON",
        },
        "visual_evidence": {
            "before_photo": "TODO_PATH_TO_BEFORE_PHOTO",
            "during_refresh_photo_or_video": "TODO_PATH_TO_DURING_REFRESH_PHOTO_OR_VIDEO",
            "after_photo": "TODO_PATH_TO_AFTER_PHOTO",
            "expected_expression": expression,
            "expected_fixture_sha256": fixture["sha256"],
            "evidence_sha256": "TODO_AFTER_PHOTO_SHA256",
        },
        "portability_notes": {
            "target_adapter_file": adapter_placeholder(target),
            "portable_files_unchanged": "TODO_TRUE_AFTER_PORTABILITY_VERIFIER",
            "third_party_clean": "TODO_TRUE_AFTER_THIRD_PARTY_DIFF",
            "wba_equivalent_plan": "TODO_WBA_EQUIVALENT_PLAN",
        },
    }


def apply_session_paths(record: dict[str, Any]) -> None:
    record["_instructions"].extend(
        [
            "Session mode pre-fills relative artifact paths under the session root.",
            "Keep status DRAFT_UNFILLED until every TODO and every artifact path is replaced with real evidence.",
        ]
    )
    host = record["host_observability"]
    host["diagnostics_bundle_artifact"] = "diagnostics/summary.json"
    host["real_ble_bench_artifact"] = "companion-ble-real-bench.json"
    visual = record["visual_evidence"]
    visual["before_photo"] = "visual/before_photo.jpg"
    visual["during_refresh_photo_or_video"] = "visual/during_refresh_photo_or_video"
    visual["after_photo"] = "visual/after_photo.jpg"


def write_output(path: pathlib.Path, record: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(record, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def operator_notes_text(target: str, expression: str, variant: str) -> str:
    pin_map = target_pin_map_scaffold(target)
    known_transport = (
        f"- transport: {pin_map.get('spi_instance_or_bus')} "
        f"SCK={pin_map.get('sck_pin')} MOSI={pin_map.get('mosi_pin')} "
        f"MISO={pin_map.get('miso_pin', 'not_used')} CS={pin_map.get('cs_pin')}"
        if target == "WB55"
        else "- transport: fill target-specific WBA SPI pins; do not copy WB55 pins as WBA evidence"
    )
    return f"""# Companion Real Panel Session

Target: {target}
Expression: {expression}
Variant: {variant}

Known transport:
{known_transport}

Fill first:
- panel-hardware-facts.todo.json

Record before firmware changes:
- controller_model:
- panel_module_or_label:
- dc_pin: STM32 pin, for example PB0
- rst_pin: STM32 pin, for example PB1
- busy_pin: STM32 pin, for example PB2
- power_enable_pin: STM32 pin, or not_present if the panel has no enable pin
- logic_voltage: 1.8V, 3.0V, or 3.3V
- reset_low_ms:
- reset_high_ms:
- busy_timeout_ms:
- full_refresh_sequence:
- partial_refresh_policy:
- sleep_or_powerdown_sequence:

Artifacts to collect:
- visual/before_photo.jpg
- visual/during_refresh_photo_or_video
- visual/after_photo.jpg
- companion-ble-real-bench.json from companion_ble_real_bench.py --expect-real-panel
- diagnostics/summary.json from collect_companion_diagnostics.ps1

Acceptance notes:
- final CardStatusV1 must be rendered/ok, not deferred_no_panel.
- e_paper.runtime_snapshot must show panel_error_count=0.
- diagnostics summary must show zero pending display queue work and zero dropped display queue work.
- Fill panel-evidence-record.json and run verify_expression_panel_evidence_record.py --record.
"""


def write_session_scaffold(root: pathlib.Path, record_path: pathlib.Path, record: dict[str, Any], target: str, expression: str, variant: str) -> None:
    root.mkdir(parents=True, exist_ok=True)
    (root / "visual").mkdir(exist_ok=True)
    (root / "diagnostics").mkdir(exist_ok=True)
    write_output(record_path, record)
    facts_path = root / SESSION_FACTS_FILENAME
    if not facts_path.exists():
        write_output(facts_path, build_hardware_facts_draft(target, expression, variant))
    notes = root / "operator-notes.md"
    if not notes.exists():
        notes.write_text(operator_notes_text(target, expression, variant), encoding="utf-8")


def verify_session_output(root: pathlib.Path, record_path: pathlib.Path) -> list[str]:
    errors: list[str] = []
    if not root.exists():
        return [f"missing panel session root: {rel(root)}"]
    if not record_path.exists():
        errors.append(f"missing panel session record: {rel(record_path)}")
    if not (root / SESSION_FACTS_FILENAME).exists():
        errors.append(f"missing panel session hardware facts draft: {rel(root / SESSION_FACTS_FILENAME)}")
    for directory in ["visual", "diagnostics"]:
        if not (root / directory).is_dir():
            errors.append(f"missing panel session directory: {rel(root / directory)}")
    notes = root / "operator-notes.md"
    if not notes.exists():
        errors.append(f"missing panel session operator notes: {rel(notes)}")
    else:
        text = notes.read_text(encoding="utf-8")
        for token in [
            "controller_model",
            "dc_pin",
            "rst_pin",
            "busy_pin",
            SESSION_FACTS_FILENAME,
            "--expect-real-panel",
            "verify_expression_panel_evidence_record.py --record",
        ]:
            if token not in text:
                errors.append(f"panel session operator notes missing {token}")
    return errors


def verify_output(path: pathlib.Path, record: dict[str, Any], session_mode: bool = False) -> list[str]:
    errors: list[str] = []
    if not path.exists():
        return [f"missing panel evidence record scaffold: {rel(path)}"]
    actual = load_json(path)
    if actual != record:
        errors.append(f"stale panel evidence record scaffold: {rel(path)}")
    if actual.get("status") != "DRAFT_UNFILLED":
        errors.append("panel evidence scaffold must stay DRAFT_UNFILLED")
    if session_mode:
        host = actual.get("host_observability", {})
        visual = actual.get("visual_evidence", {})
        expected_paths = {
            "host_observability.real_ble_bench_artifact": host.get("real_ble_bench_artifact"),
            "host_observability.diagnostics_bundle_artifact": host.get("diagnostics_bundle_artifact"),
            "visual_evidence.before_photo": visual.get("before_photo"),
            "visual_evidence.during_refresh_photo_or_video": visual.get("during_refresh_photo_or_video"),
            "visual_evidence.after_photo": visual.get("after_photo"),
        }
        for label, value in expected_paths.items():
            if not isinstance(value, str) or value.startswith("TODO_"):
                errors.append(f"panel session scaffold must prefill {label}")
    else:
        if "TODO_PATH_TO_EXPECT_REAL_PANEL_REAL_BLE_BENCH_JSON" not in json.dumps(actual):
            errors.append("panel evidence scaffold must include real BLE artifact TODO")
        if "TODO_PATH_TO_COLLECT_COMPANION_DIAGNOSTICS_SUMMARY_JSON" not in json.dumps(actual):
            errors.append("panel evidence scaffold must include diagnostics bundle artifact TODO")
    if "screen_expression_status" not in json.dumps(actual):
        errors.append("panel evidence scaffold must mention screen_expression_status artifact contract")
    if "screen_expression_demo_status" not in json.dumps(actual):
        errors.append("panel evidence scaffold must mention screen_expression_demo_status artifact contract")
    if "e_paper.runtime_snapshot" not in actual.get("host_observability", {}):
        errors.append("panel evidence scaffold must include runtime snapshot TODO")
    pin_map = actual.get("target_pin_map", {})
    if actual.get("target_pin_map", {}).get("target_family") == "WB55":
        expected = {
            "spi_instance_or_bus": "SPI2",
            "sck_pin": "PA9",
            "mosi_pin": "PC1",
            "miso_pin": "PC2",
            "cs_pin": "PA6",
            "cs_label": "SPI2_CS",
            "wiring_preflight": "docs/validation/companion-screen-panel-wiring-preflight.json",
        }
        for key, value in expected.items():
            if pin_map.get(key) != value:
                errors.append(f"WB55 panel evidence scaffold {key} expected {value}, got {pin_map.get(key)}")
        for key in ["dc_pin", "rst_pin", "busy_pin"]:
            if "TODO" not in str(pin_map.get(key, "")):
                errors.append(f"WB55 panel evidence scaffold must leave {key} as a TODO until hardware review")
    return errors


def parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=pathlib.Path, default=None)
    parser.add_argument("--session-root", type=pathlib.Path, default=None)
    parser.add_argument("--target", choices=TARGETS, default="WB55")
    parser.add_argument("--expression", default="idle")
    parser.add_argument("--variant", default="2.13in")
    parser.add_argument("--write", action="store_true", help="Write the scaffold JSON.")
    parser.add_argument("--write-session", action="store_true", help="Write a real-panel session directory with notes and artifact folders.")
    return parser.parse_args(argv)


def main(argv: list[str]) -> int:
    args = parse_args(argv)
    if args.write_session and args.session_root is None:
        print("FAIL: --write-session requires --session-root", file=sys.stderr)
        return 1

    session_root = None
    if args.session_root is not None:
        session_root = args.session_root if args.session_root.is_absolute() else REPO_ROOT / args.session_root

    if args.output is None:
        output = session_root / SESSION_RECORD_FILENAME if session_root is not None else DEFAULT_OUTPUT
    else:
        output = args.output if args.output.is_absolute() else REPO_ROOT / args.output

    record = build_record(args.target, args.expression, args.variant)
    session_mode = session_root is not None
    if session_mode:
        apply_session_paths(record)
    if args.write_session:
        write_session_scaffold(session_root, output, record, args.target, args.expression, args.variant)
    elif args.write:
        write_output(output, record)
    errors = verify_output(output, record, session_mode=session_mode)
    if session_mode:
        errors.extend(verify_session_output(session_root, output))
    if errors:
        print("FAIL: Companion panel evidence record scaffold is stale:", file=sys.stderr)
        for error in errors:
            print(f" - {error}", file=sys.stderr)
        return 1
    if session_mode:
        print(f"PASS: Companion panel evidence session scaffold verified -> {rel(session_root)}")
    else:
        print(f"PASS: Companion panel evidence record scaffold verified -> {rel(output)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
