#!/usr/bin/env python3
"""Verify the panel hardware acceptance evidence template."""

from __future__ import annotations

import argparse
import json
import pathlib
import sys
from typing import Any


REPO_ROOT = pathlib.Path(__file__).resolve().parents[1]
DEFAULT_FIXTURE = pathlib.Path("docs/validation/companion-screen-panel-evidence-template.json")
SCHEMA_ID = "companion.pendant.screen_panel_evidence_template.v1"
TEMPLATE_ID = "screen_panel_hardware_acceptance_v1"

PANEL_GATE = REPO_ROOT / "docs" / "validation" / "companion-screen-panel-hardware-gate.json"
ACCEPTANCE_INDEX = REPO_ROOT / "docs" / "validation" / "companion-screen-acceptance-index.json"
SCREEN_DOC = REPO_ROOT / "docs" / "companion_screen_expression_system.md"
WBA_RULES = REPO_ROOT / "docs" / "stm32wba_migration_rules.md"
README = REPO_ROOT / "app" / "companion_pendant" / "epaper" / "README.md"
PANEL_HEADER = REPO_ROOT / "app" / "companion_pendant" / "epaper" / "panel_adapter.h"
PANEL_SOURCE = REPO_ROOT / "app" / "companion_pendant" / "epaper" / "panel_adapter.c"
REAL_BLE_SCREEN_BENCH = REPO_ROOT / "docs" / "validation" / "companion-screen-real-ble-bench.json"
HOST_STATUS_SEQUENCE = REPO_ROOT / "docs" / "validation" / "companion-screen-expression-host-status-sequence.json"
DEMO_HOST_STATUS_SEQUENCE = (
    REPO_ROOT / "docs" / "validation" / "companion-screen-expression-demo-host-status-sequence.json"
)

REQUIRED_TARGETS = ("WB55", "WBA55", "WBA65")
REQUIRED_SECTIONS: dict[str, tuple[str, ...]] = {
    "panel_identity": (
        "controller_model",
        "panel_variant",
        "resolution_px",
        "datasheet_revision",
        "waveform_lut_source",
    ),
    "target_pin_map": (
        "target_family",
        "spi_instance_or_bus",
        "sck_pin",
        "mosi_pin",
        "cs_pin",
        "dc_pin",
        "rst_pin",
        "busy_pin",
        "power_enable_pin",
        "logic_voltage",
    ),
    "driver_timing": (
        "reset_low_ms",
        "reset_high_ms",
        "busy_timeout_ms",
        "full_refresh_sequence",
        "partial_refresh_policy",
        "sleep_or_powerdown_sequence",
    ),
    "host_observability": (
        "request_id",
        "content_crc32",
        "CardStatusV1_accepted",
        "CardStatusV1_rendered",
        "e_paper.render_request",
        "e_paper.update_result",
        "e_paper.runtime_snapshot",
        "diagnostics_bundle_artifact",
        "real_ble_bench_artifact",
    ),
    "visual_evidence": (
        "before_photo",
        "during_refresh_photo_or_video",
        "after_photo",
        "expected_expression",
        "expected_fixture_sha256",
        "evidence_sha256",
    ),
    "portability_notes": (
        "target_adapter_file",
        "portable_files_unchanged",
        "third_party_clean",
        "wba_equivalent_plan",
    ),
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


def build_template() -> dict[str, Any]:
    return {
        "schema_id": SCHEMA_ID,
        "template_id": TEMPLATE_ID,
        "status": "PASS",
        "claim_scope": "template_only_no_real_refresh",
        "unblocks_gate": "wb55_real_panel_refresh",
        "applies_to": list(REQUIRED_TARGETS),
        "purpose": (
            "Define the minimum hardware evidence required before WB55 or WBA "
            "code may replace the dry-run panel adapter with a real e-paper "
            "refresh claim."
        ),
        "evidence_sources": [
            "app/companion_pendant/epaper/panel_adapter.h",
            "app/companion_pendant/epaper/panel_adapter.c",
            "docs/companion_screen_expression_system.md",
            "docs/stm32wba_migration_rules.md",
            "docs/validation/companion-screen-real-ble-bench.json",
            "docs/validation/companion-screen-expression-host-status-sequence.json",
            "docs/validation/companion-screen-expression-demo-host-status-sequence.json",
            "docs/validation/companion-screen-runtime-diagnostics.json",
            "docs/validation/companion-screen-runtime-diagnostic-decode.json",
            "docs/validation/companion-diagnostics-fixture/summary.json",
            "docs/validation/companion-screen-panel-adapter-behavior.json",
            "docs/validation/companion-screen-panel-adapter-boundary.json",
            "docs/validation/companion-screen-panel-hardware-gate.json",
        ],
        "minimum_evidence": {
            section: {
                "required_fields": list(fields),
                "status_before_hardware": "required_but_unfilled",
            }
            for section, fields in REQUIRED_SECTIONS.items()
        },
        "host_observable_pass_criteria": {
            "accepted_status": {
                "render_state": "accepted",
                "last_error": "ok",
                "request_id": "matches_render_request",
                "content_crc32": "matches_render_request",
            },
            "final_status": {
                "render_state": "rendered",
                "last_error": "ok",
                "request_id": "same_as_accepted_status",
                "content_crc32": "same_as_accepted_status",
            },
            "diagnostic_events": [
                "e_paper.render_request",
                "e_paper.update_result",
                "e_paper.runtime_snapshot",
            ],
            "runtime_snapshot": {
                "decoded_args_required": True,
                "display_queue_pending_count": 0,
                "display_queue_dropped_count": 0,
                "panel_error_count": 0,
            },
            "diagnostics_bundle_artifact": {
                "tool": "tools/collect_companion_diagnostics.ps1",
                "summary_schema": "companion.pendant.diagnostics_bundle.v1",
                "required_summary_field": "epaper.runtime_snapshot_decoded",
                "display_queue_pending_count": 0,
                "display_queue_dropped_count": 0,
                "panel_error_count": 0,
            },
            "real_ble_bench_artifact": {
                "tool": "tools/companion_ble_real_bench.py --expect-real-panel",
                "required_operations": [
                    "screen_expression_status",
                    "screen_expression_demo_status",
                    "card_write",
                    "settings_sleepy_screen_status",
                ],
                "required_fields": [
                    "host_sequence_fixture",
                    "card_status",
                    "final_card_status",
                    "status_sequence",
                    "real_panel_refresh_claimed",
                ],
                "host_sequence_fixture": "docs/validation/companion-screen-expression-host-status-sequence.json",
                "demo_host_sequence_fixture": "docs/validation/companion-screen-expression-demo-host-status-sequence.json",
                "screen_expression_status_contract_only": True,
                "screen_expression_demo_status_contract_only": True,
            },
        },
        "adapter_rules": [
            {
                "target": "WB55",
                "adapter_file_pattern": "*_stm32wb.*",
                "rule": "Keep dry-run active until controller, pins, timing, logs, and visual evidence are recorded.",
            },
            {
                "target": "WBA55",
                "adapter_file_pattern": "*_stm32wba.*",
                "rule": "Add a WBA-specific transport without changing ExpressionV1, display_queue, or CardStatusV1 contracts.",
            },
            {
                "target": "WBA65",
                "adapter_file_pattern": "*_stm32wba.*",
                "rule": "Treat WBA65 as an expanded WBA target; keep WBA55-safe protocol and queue limits unless a capability flag exists.",
            },
        ],
        "rejection_rules": [
            "A dry-run deferred_no_panel or deferred_controller_unknown result cannot satisfy real refresh evidence.",
            "A photo without matching request_id, content_crc32, and update_result logs cannot satisfy visual evidence.",
            "A runtime snapshot with panel.error_count, pending display work, or dropped display work cannot satisfy real refresh evidence.",
            "A WB55-specific SPI/GPIO implementation cannot be placed in portable epaper files.",
            "A WBA port cannot claim parity until it has its own target adapter, build wrapper, and matching evidence record.",
        ],
        "validation_commands": [
            "python .\\tools\\verify_expression_real_ble_screen_bench.py",
            "python .\\tools\\verify_expression_panel_adapter_behavior.py",
            "python .\\tools\\verify_expression_panel_adapter_boundary.py",
            "python .\\tools\\verify_expression_panel_evidence_template.py",
            "python .\\tools\\verify_expression_panel_gate.py",
            "python .\\tools\\verify_expression_screen_runtime_diagnostics.py",
            "python .\\tools\\verify_expression_screen_runtime_diagnostic_decode.py",
            "python .\\tools\\verify_companion_diagnostics_static.py",
            "python .\\tools\\verify_expression_status_observability.py",
            "python .\\tools\\verify_expression_wba_portability.py",
            "pwsh -NoProfile -File .\\tools\\build_nucleo_bringup.ps1",
        ],
    }


def check_template_data(data: dict[str, Any], errors: list[str]) -> None:
    require(data.get("schema_id") == SCHEMA_ID, "unexpected panel evidence template schema", errors)
    require(data.get("template_id") == TEMPLATE_ID, "unexpected panel evidence template id", errors)
    require(data.get("status") == "PASS", "panel evidence template should be a PASS template item", errors)
    require(
        data.get("claim_scope") == "template_only_no_real_refresh",
        "panel evidence template must not claim real refresh",
        errors,
    )
    require(data.get("unblocks_gate") == "wb55_real_panel_refresh", "template must point at the real panel gate", errors)
    require(set(data.get("applies_to", [])) == set(REQUIRED_TARGETS), "template target coverage drifted", errors)

    sections = data.get("minimum_evidence", {})
    require(isinstance(sections, dict), "minimum_evidence must be an object", errors)
    for section, required_fields in REQUIRED_SECTIONS.items():
        entry = sections.get(section, {})
        require(isinstance(entry, dict), f"{section} evidence section missing", errors)
        fields = set(entry.get("required_fields", [])) if isinstance(entry, dict) else set()
        missing = sorted(set(required_fields) - fields)
        require(not missing, f"{section} evidence section missing fields: {', '.join(missing)}", errors)
        require(
            entry.get("status_before_hardware") == "required_but_unfilled",
            f"{section} should remain unfilled before hardware review",
            errors,
        )

    final_status = data.get("host_observable_pass_criteria", {}).get("final_status", {})
    require(final_status.get("render_state") == "rendered", "final real panel status must require rendered", errors)
    require(final_status.get("last_error") == "ok", "final real panel status must require ok", errors)
    criteria = data.get("host_observable_pass_criteria", {})
    bench = criteria.get("real_ble_bench_artifact", {})
    for operation in ["screen_expression_status", "screen_expression_demo_status", "card_write", "settings_sleepy_screen_status"]:
        require(
            operation in bench.get("required_operations", []),
            f"real BLE artifact criteria missing operation {operation}",
            errors,
        )
    for field in ["host_sequence_fixture", "card_status", "final_card_status", "status_sequence", "real_panel_refresh_claimed"]:
        require(field in bench.get("required_fields", []), f"real BLE artifact criteria missing field {field}", errors)
    require(
        bench.get("host_sequence_fixture") == "docs/validation/companion-screen-expression-host-status-sequence.json",
        "real BLE artifact criteria must link host expression status sequence fixture",
        errors,
    )
    require(
        bench.get("demo_host_sequence_fixture") == "docs/validation/companion-screen-expression-demo-host-status-sequence.json",
        "real BLE artifact criteria must link demo host expression status sequence fixture",
        errors,
    )
    require(
        bench.get("screen_expression_status_contract_only") is True,
        "real BLE artifact criteria must mark screen_expression_status as contract-only",
        errors,
    )
    require(
        bench.get("screen_expression_demo_status_contract_only") is True,
        "real BLE artifact criteria must mark screen_expression_demo_status as contract-only",
        errors,
    )
    diagnostic_events = criteria.get("diagnostic_events", [])
    require("e_paper.runtime_snapshot" in diagnostic_events, "panel evidence template must require runtime snapshot diagnostics", errors)
    runtime = criteria.get("runtime_snapshot", {})
    require(runtime.get("decoded_args_required") is True, "runtime snapshot decoded_args must be required", errors)
    require(runtime.get("panel_error_count") == 0, "runtime snapshot must require zero panel errors", errors)
    require(runtime.get("display_queue_pending_count") == 0, "runtime snapshot must require empty display queue", errors)
    require(runtime.get("display_queue_dropped_count") == 0, "runtime snapshot must require no dropped display work", errors)
    bundle = criteria.get("diagnostics_bundle_artifact", {})
    require(bundle.get("summary_schema") == "companion.pendant.diagnostics_bundle.v1", "diagnostics bundle criteria must require summary schema", errors)
    require(bundle.get("required_summary_field") == "epaper.runtime_snapshot_decoded", "diagnostics bundle criteria must require decoded epaper runtime snapshot", errors)
    require(bundle.get("panel_error_count") == 0, "diagnostics bundle criteria must require zero panel errors", errors)
    require(bundle.get("display_queue_pending_count") == 0, "diagnostics bundle criteria must require empty display queue", errors)
    require(bundle.get("display_queue_dropped_count") == 0, "diagnostics bundle criteria must require no dropped display work", errors)

    adapter_targets = {entry.get("target") for entry in data.get("adapter_rules", []) if isinstance(entry, dict)}
    require(adapter_targets == set(REQUIRED_TARGETS), "adapter rule target coverage drifted", errors)
    for rule in data.get("adapter_rules", []):
        if not isinstance(rule, dict):
            errors.append("adapter rule must be an object")
            continue
        target = str(rule.get("target", ""))
        pattern = str(rule.get("adapter_file_pattern", ""))
        if target == "WB55":
            require("stm32wb" in pattern.lower(), "WB55 adapter rule must name stm32wb", errors)
        if target.startswith("WBA"):
            require("stm32wba" in pattern.lower(), f"{target} adapter rule must name stm32wba", errors)

    rejection = "\n".join(str(rule) for rule in data.get("rejection_rules", []))
    for token in [
        "deferred_no_panel",
        "request_id",
        "content_crc32",
        "runtime snapshot",
        "panel.error_count",
        "portable epaper files",
        "target adapter",
    ]:
        require(token in rejection, f"panel evidence template rejection rules missing {token}", errors)

    for evidence in data.get("evidence_sources", []):
        require((REPO_ROOT / str(evidence)).exists(), f"panel evidence source missing {evidence}", errors)
    for command in data.get("validation_commands", []):
        if "\\tools\\" in str(command):
            tool = str(command).split("\\tools\\", 1)[1].split()[0]
            require((REPO_ROOT / "tools" / tool).exists(), f"panel evidence command references missing tool {tool}", errors)


def check_project_links(fixture_rel: str, errors: list[str]) -> None:
    panel_gate = read(PANEL_GATE, errors)
    acceptance = read(ACCEPTANCE_INDEX, errors)
    screen_doc = read(SCREEN_DOC, errors)
    wba_rules = read(WBA_RULES, errors)
    readme = read(README, errors)
    panel_header = read(PANEL_HEADER, errors)
    panel_source = read(PANEL_SOURCE, errors)

    for token in [
        "companion-screen-panel-evidence-template.json",
        "companion-screen-real-ble-bench.json",
        "companion-screen-panel-adapter-behavior.json",
        "companion-screen-panel-adapter-boundary.json",
        "panel_hardware_evidence_template",
        "verify_expression_panel_evidence_template.py",
        "verify_expression_real_ble_screen_bench.py",
        "verify_expression_panel_adapter_behavior.py",
        "verify_expression_panel_adapter_boundary.py",
        "target_adapter_file",
        "e_paper.runtime_snapshot",
        "decoded runtime diagnostics",
        "diagnostics_bundle_artifact",
        "panel_evidence_runtime_diagnostics",
        "before/during/after",
        "screen_expression_status",
        "screen_expression_demo_status",
        "companion-screen-expression-host-status-sequence.json",
        "companion-screen-expression-demo-host-status-sequence.json",
    ]:
        require(token in screen_doc, f"screen doc missing panel evidence anchor {token}", errors)
    for token in [
        "panel evidence template",
        "Panel evidence runtime diagnostics",
        "WBA55",
        "WBA65",
        "*_stm32wba.*",
        "screen_expression_status",
        "screen_expression_demo_status",
    ]:
        require(token.lower() in wba_rules.lower(), f"WBA rules missing panel evidence anchor {token}", errors)
    require("panel evidence template" in readme.lower(), "e-paper README missing panel evidence template note", errors)
    require(REAL_BLE_SCREEN_BENCH.exists(), "missing real BLE screen bench fixture", errors)
    require(HOST_STATUS_SEQUENCE.exists(), "missing host expression status sequence fixture", errors)
    require(DEMO_HOST_STATUS_SEQUENCE.exists(), "missing demo host expression status sequence fixture", errors)
    require(fixture_rel in panel_gate, "panel gate fixture must link the panel evidence template", errors)
    require(fixture_rel in acceptance, "acceptance index must link the panel evidence template", errors)
    require("COMP_EPAPER_PANEL_RESULT_DEFERRED_NO_PANEL" in panel_header, "panel adapter header missing deferred no-panel", errors)
    require("result = COMP_EPAPER_PANEL_RESULT_OK" not in panel_source, "dry-run panel adapter must not claim OK", errors)


def check_fixture_file(path: pathlib.Path, expected: dict[str, Any], errors: list[str]) -> None:
    require(path.exists(), f"missing panel evidence template fixture: {rel(path)}", errors)
    if not path.exists():
        return
    actual = json.loads(path.read_text(encoding="utf-8"))
    require(actual == expected, f"{rel(path)} is stale; rerun with --write-fixture", errors)
    check_template_data(actual, errors)


def parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--fixture", type=pathlib.Path, default=DEFAULT_FIXTURE)
    parser.add_argument("--write-fixture", action="store_true", help="Update the deterministic panel evidence template JSON.")
    return parser.parse_args(argv)


def main(argv: list[str]) -> int:
    args = parse_args(argv)
    fixture_path = REPO_ROOT / args.fixture
    fixture_rel = rel(fixture_path)
    expected = build_template()
    errors: list[str] = []

    check_template_data(expected, errors)
    if not args.write_fixture:
        check_project_links(fixture_rel, errors)

    if args.write_fixture and not errors:
        fixture_path.parent.mkdir(parents=True, exist_ok=True)
        fixture_path.write_text(json.dumps(expected, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    if not args.write_fixture:
        check_fixture_file(fixture_path, expected, errors)

    if errors:
        print("FAIL: Companion screen panel evidence template checks failed:", file=sys.stderr)
        for error in errors:
            print(f" - {error}", file=sys.stderr)
        return 1
    print(f"PASS: Companion screen panel evidence template verified -> {rel(fixture_path)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
