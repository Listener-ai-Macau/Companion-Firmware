#!/usr/bin/env python3
"""Verify the Companion screen feature roadmap."""

from __future__ import annotations

import argparse
import json
import pathlib
import sys
from collections import Counter
from typing import Any

from screen_runtime_candidate import current_candidate


REPO_ROOT = pathlib.Path(__file__).resolve().parents[1]
DEFAULT_FIXTURE = pathlib.Path("docs/validation/companion-screen-feature-roadmap.json")
ACCEPTANCE_INDEX = REPO_ROOT / "docs/validation/companion-screen-acceptance-index.json"
SCREEN_DOC = REPO_ROOT / "docs/companion_screen_expression_system.md"
EPAPER_README = REPO_ROOT / "app/companion_pendant/epaper/README.md"
SCHEMA_ID = "companion.pendant.screen_feature_roadmap.v1"

ROADMAP_ITEM_ID = "screen_feature_roadmap"
CANDIDATE = current_candidate()
RUNTIME_GATE_ID = f"wb55_rev{CANDIDATE.revision}_runtime_recheck"

CAPABILITIES = [
    {
        "id": "expression_artwork_and_copy",
        "title": "Expression artwork and copy",
        "user_value": "Every face has deterministic artwork and copy that fits both supported e-paper sizes.",
        "acceptance_item_ids": [
            "no_hardware_expression_renderer",
            "expression_visual_contract",
            "expression_visual_acceptance_matrix",
            "generated_art_style_contract",
            "screen_generation_swap_guard",
            "expression_layout_contract",
            "expression_catalog_contract",
            "expression_copy_contract",
            "expression_priority_matrix",
            "expression_transient_auto_recovery",
        ],
        "next_acceptance": "Keep visual/layout/copy contracts green when adding a new face or changing copy.",
    },
    {
        "id": "screen_generation_hygiene",
        "title": "Screen generation hygiene",
        "user_value": "Every generated-art prompt, menu, screen-profile, or ui_assets swap activates as one coherent product generation instead of showing mixed old and new styles.",
        "acceptance_item_ids": [
            "screen_generation_swap_guard",
            "screen_refresh_feel_contract",
            "screen_display_drain_contract",
            "display_queue_telemetry",
        ],
        "next_acceptance": "Every new prompt/art/menu/profile/ui_assets revision must prove atomic activation, stale-frame draining, current-generation-only rendering, and post-interaction panel maintenance before visual review.",
    },
    {
        "id": "portable_expression_model",
        "title": "Portable expression model",
        "user_value": "Expression priority, duplicate suppression, telemetry, and unsupported-signal guards stay HAL-free.",
        "acceptance_item_ids": [
            "firmware_expression_state",
            "expression_state_telemetry_snapshot",
            "expression_unknown_signal_guard",
            "expression_duplicate_refresh_suppression",
            "expression_host_manifest",
            "expression_input_source_matrix",
            "user_journey_expression_acceptance",
        ],
        "next_acceptance": "Append new signals only through the catalog, copy, priority, and journey fixtures.",
    },
    {
        "id": "screen_demo_acceptance_flow",
        "title": "Screen demo acceptance flow",
        "user_value": "The current screen behavior can be reviewed one feature at a time from a deterministic demo checklist and mapped to real-panel evidence.",
        "acceptance_item_ids": [
            "screen_feature_checklist",
            "screen_expression_demo_sequence",
            "screen_expression_demo_host_status_sequence",
            "screen_expression_demo_panel_handoff",
        ],
        "next_acceptance": "Use the same demo order for WB55 real-panel photos and later extend the real BLE bench until no manual visual gaps remain.",
    },
    {
        "id": "product_status_hooks",
        "title": "Product status expression hooks",
        "user_value": "Recording, settings, device, battery, OTA, interaction, and diagnostics can request visible faces.",
        "acceptance_item_ids": [
            "ble_to_expression_policy",
            "screen_settings_expression_policy",
            "wb55_settings_expression_hint",
            "wb55_device_status_expression_hint",
            "wb55_interaction_status_expression_hint",
            "wb55_battery_expression_hint",
            "battery_recovery_expression_guard",
            "recording_state_expression_hook",
            "wb55_ota_readiness_expression_hint",
            "diagnostic_event_expression_bridge",
        ],
        "next_acceptance": "Add each new product signal with a focused hook verifier and update the input source matrix.",
    },
    {
        "id": "wb55_queue_and_host_status",
        "title": "WB55 queue and host status",
        "user_value": "WB55 queues screen work outside BLE callbacks and exposes accepted/final status to the host.",
        "acceptance_item_ids": [
            "wb55_display_queue_boundary",
            "display_queue_fault_paths",
            "display_queue_telemetry",
            "screen_display_drain_contract",
            "wb55_boot_idle_expression",
            "screen_status_observability",
            "host_ble_expression_status_fixture",
            "host_ble_expression_extended_status_fixture",
            "host_ble_expression_status_sequence",
            "wb55_expression_tick_scheduler",
        ],
        "next_acceptance": "Use the same queue/status path for real-panel refresh and WBA scheduler parity.",
    },
    {
        "id": "runtime_diagnostics_and_evidence",
        "title": "Runtime diagnostics and evidence",
        "user_value": "Screen runtime health can be decoded from diagnostics, BLE artifacts, and evidence records.",
        "acceptance_item_ids": [
            "wb55_runtime_serial_capture_preflight",
            "screen_runtime_evidence_durability",
            RUNTIME_GATE_ID,
            "screen_runtime_snapshot",
            "screen_runtime_diagnostics",
            "screen_runtime_diagnostic_decode",
            "screen_runtime_diagnostics_bundle",
            "real_ble_screen_final_status_bench",
            "real_ble_expression_status_sequence_contract",
            "panel_evidence_runtime_diagnostics",
            "panel_evidence_diagnostics_bundle_validator",
            "panel_evidence_real_ble_sequence_validator",
            "screen_acceptance_runner",
        ],
        "next_acceptance": "Attach runtime snapshot and diagnostics bundle evidence to the first real-panel session.",
    },
    {
        "id": "panel_driver_readiness",
        "title": "Panel driver readiness",
        "user_value": "The panel driver boundary, evidence templates, and WB55 hardware gate are explicit.",
        "acceptance_item_ids": [
            "panel_target_ops_boundary",
            "wb55_panel_target_adapter_scaffold",
            "panel_adapter_behavior_matrix",
            "panel_adapter_telemetry_snapshot",
            "panel_hardware_evidence_template",
            "panel_evidence_record_validator",
            "panel_hardware_acceptance_plan",
            "devboard_ioc_screen_preflight",
            "wb55_screen_build_matrix",
            "panel_wiring_preflight",
            "panel_evidence_scaffold_wiring_prefill",
            "panel_hardware_session_scaffold",
            "panel_session_directory_preflight",
            "panel_hardware_facts_intake",
            "panel_hardware_facts_worksheet",
            "panel_bringup_operator_packet",
            "panel_driver_readiness_report",
            "panel_hardware_facts_bridge",
            "screen_refresh_feel_contract",
            "wb55_real_panel_refresh",
            "wb55_touch_visual_acceptance",
            "companion_screen_goal_audit",
        ],
        "next_acceptance": "Replace or cross-swap FTS02, prove solid white/black and valid PREVGH/PREVGL rails, then resume touch, gesture, language, and maintenance visual review.",
    },
    {
        "id": "wba_migration_readiness",
        "title": "WBA migration readiness",
        "user_value": "WBA55/WBA65 work has target-named scaffolds and a CubeWBA dependency gate.",
        "acceptance_item_ids": [
            "wba_pre_port_gate",
            "wba_cube_dependency_preflight",
            "wba_port_scaffold",
            "wba_panel_target_adapter_scaffold",
            "wba_refresh_intent_contract",
            "wba_display_scheduler_scaffold",
            "wba_screen_gatt_scaffold",
            "wba_screen_assets_scaffold",
            "wba_pet_behavior_user_data_scaffold",
            "target_capability_profile",
            "wba_lse_clock_contract",
        ],
        "next_acceptance": "Add a separate CubeWBA IOC/project and build wrapper before claiming WBA parity.",
    },
]


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


def aggregate_status(statuses: list[str]) -> str:
    if any(status not in {"PASS", "DEFERRED_HARDWARE", "PENDING_HUMAN"} for status in statuses):
        return "NEEDS_ATTENTION"
    if any(status == "DEFERRED_HARDWARE" for status in statuses):
        return "DEFERRED_HARDWARE"
    if any(status == "PENDING_HUMAN" for status in statuses):
        return "PENDING_HUMAN"
    return "PASS"


def build_roadmap() -> dict[str, Any]:
    index = load_json(ACCEPTANCE_INDEX)
    items = [item for item in index.get("items", []) if isinstance(item, dict)]
    by_id = {str(item.get("id")): item for item in items}

    capabilities: list[dict[str, Any]] = []
    grouped_ids: set[str] = set()
    for capability in CAPABILITIES:
        item_ids = [str(item_id) for item_id in capability["acceptance_item_ids"]]
        statuses = [str(by_id.get(item_id, {}).get("status", "MISSING")) for item_id in item_ids]
        grouped_ids.update(item_ids)
        capabilities.append(
            {
                "id": capability["id"],
                "title": capability["title"],
                "status": aggregate_status(statuses),
                "user_value": capability["user_value"],
                "acceptance_item_ids": item_ids,
                "acceptance_statuses": {
                    item_id: str(by_id.get(item_id, {}).get("status", "MISSING")) for item_id in item_ids
                },
                "next_acceptance": capability["next_acceptance"],
            }
        )

    all_item_ids = {str(item.get("id")) for item in items}
    coverage_scope = sorted(item_id for item_id in all_item_ids if item_id != ROADMAP_ITEM_ID)
    ungrouped = sorted(set(coverage_scope) - grouped_ids)
    status_counts = Counter(capability["status"] for capability in capabilities)

    return {
        "schema_id": SCHEMA_ID,
        "status": aggregate_status([capability["status"] for capability in capabilities]),
        "purpose": "Product-facing roadmap that groups the detailed screen acceptance items into small Companion screen capabilities.",
        "source_acceptance_index": rel(ACCEPTANCE_INDEX),
        "current_next_gate": index.get("summary", {}).get("next_hardware_gate"),
        "capabilities": capabilities,
        "coverage": {
            "acceptance_item_count": len(coverage_scope),
            "grouped_acceptance_item_count": len(set(coverage_scope) & grouped_ids),
            "ungrouped_acceptance_item_ids": ungrouped,
            "roadmap_item_excluded_from_coverage": ROADMAP_ITEM_ID,
        },
        "summary": {
            "capability_count": len(capabilities),
            "pass_capability_count": int(status_counts.get("PASS", 0)),
            "deferred_hardware_capability_count": int(status_counts.get("DEFERRED_HARDWARE", 0)),
            "pending_human_capability_count": int(status_counts.get("PENDING_HUMAN", 0)),
            "needs_attention_capability_count": int(status_counts.get("NEEDS_ATTENTION", 0)),
            "next_acceptance": (
                "Replace or cross-swap FTS02, prove deterministic solid white/black frames "
                "and valid positive/negative refresh rails, then resume focused visual review."
            ),
        },
        "validation_commands": [
            "python .\\tools\\verify_expression_feature_roadmap.py",
            "python .\\tools\\verify_expression_acceptance_index.py",
            "python .\\tools\\run_expression_acceptance.py --dry-run --skip-build",
        ],
    }


def validate_roadmap(data: dict[str, Any], errors: list[str]) -> None:
    require(data.get("schema_id") == SCHEMA_ID, f"roadmap schema_id must be {SCHEMA_ID}", errors)
    require(data.get("current_next_gate") == "wb55_real_panel_refresh", "roadmap must point at the current panel recovery gate", errors)
    capabilities = data.get("capabilities", [])
    require(isinstance(capabilities, list) and capabilities, "roadmap must contain capabilities", errors)
    ids = [capability.get("id") for capability in capabilities if isinstance(capability, dict)]
    require(len(ids) == len(set(ids)), "roadmap capability ids must be unique", errors)
    for required_id in [
        "expression_artwork_and_copy",
        "screen_generation_hygiene",
        "portable_expression_model",
        "screen_demo_acceptance_flow",
        "product_status_hooks",
        "wb55_queue_and_host_status",
        "runtime_diagnostics_and_evidence",
        "panel_driver_readiness",
        "wba_migration_readiness",
    ]:
        require(required_id in ids, f"roadmap missing capability {required_id}", errors)

    coverage = data.get("coverage", {})
    require(coverage.get("ungrouped_acceptance_item_ids") == [], "roadmap has ungrouped acceptance items", errors)
    require(data.get("status") == "DEFERRED_HARDWARE", "roadmap should reflect the current hardware recovery gate", errors)

    by_id = {capability.get("id"): capability for capability in capabilities if isinstance(capability, dict)}
    generation = by_id.get("screen_generation_hygiene", {})
    require(generation.get("status") == "PASS", "screen_generation_hygiene should be machine-proven before human review", errors)
    for item_id in [
        "screen_generation_swap_guard",
        "screen_refresh_feel_contract",
        "screen_display_drain_contract",
        "display_queue_telemetry",
    ]:
        require(
            item_id in generation.get("acceptance_item_ids", []),
            f"screen_generation_hygiene must include {item_id}",
            errors,
        )
    require(
        "stale-frame draining" in str(generation.get("next_acceptance", "")),
        "screen_generation_hygiene next_acceptance must name stale-frame draining",
        errors,
    )
    require(
        "prompt/art/menu/profile/ui_assets" in str(generation.get("next_acceptance", "")),
        "screen_generation_hygiene next_acceptance must cover generated-art, menu, profile, and ui_assets swaps",
        errors,
    )

    panel = by_id.get("panel_driver_readiness", {})
    require(panel.get("status") == "DEFERRED_HARDWARE", "panel_driver_readiness must reflect the current hardware blocker", errors)
    require(
        "wb55_real_panel_refresh" in panel.get("acceptance_item_ids", []),
        "panel_driver_readiness must include wb55_real_panel_refresh",
        errors,
    )
    require(
        "wb55_touch_visual_acceptance" in panel.get("acceptance_item_ids", []),
        "panel_driver_readiness must include wb55_touch_visual_acceptance",
        errors,
    )
    require(
        "panel_bringup_operator_packet" in panel.get("acceptance_item_ids", []),
        "panel_driver_readiness must include panel_bringup_operator_packet",
        errors,
    )
    require(
        "FTS02" in str(panel.get("next_acceptance", "")) and "PREVGH/PREVGL" in str(panel.get("next_acceptance", "")),
        "panel_driver_readiness next_acceptance must name FTS02 and refresh-rail recovery",
        errors,
    )


def check_docs(errors: list[str]) -> None:
    for path in [SCREEN_DOC, EPAPER_README]:
        require(path.exists(), f"missing roadmap doc source: {rel(path)}", errors)
        if not path.exists():
            continue
        text = path.read_text(encoding="utf-8")
        for token in [
            "screen_feature_roadmap",
            "companion-screen-feature-roadmap.json",
            "verify_expression_feature_roadmap.py",
            "screen_demo_acceptance_flow",
            "screen_expression_demo_host_status_sequence",
            "screen_expression_demo_panel_handoff",
        ]:
            require(token in text, f"{rel(path)} missing roadmap token {token}", errors)


def check_fixture(path: pathlib.Path, expected: dict[str, Any], errors: list[str]) -> None:
    require(path.exists(), f"missing feature roadmap fixture: {rel(path)}", errors)
    if not path.exists():
        return
    actual = load_json(path)
    require(actual == expected, f"{rel(path)} is stale; rerun with --write-fixture", errors)


def parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--fixture", type=pathlib.Path, default=DEFAULT_FIXTURE)
    parser.add_argument("--write-fixture", action="store_true", help="Update the deterministic roadmap fixture.")
    return parser.parse_args(argv)


def main(argv: list[str]) -> int:
    args = parse_args(argv)
    fixture_path = args.fixture if args.fixture.is_absolute() else REPO_ROOT / args.fixture
    errors: list[str] = []
    expected = build_roadmap()
    validate_roadmap(expected, errors)
    check_docs(errors)
    if args.write_fixture and not errors:
        fixture_path.parent.mkdir(parents=True, exist_ok=True)
        fixture_path.write_text(json.dumps(expected, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    if not args.write_fixture:
        check_fixture(fixture_path, expected, errors)

    if errors:
        print("FAIL: Companion screen feature roadmap checks failed:", file=sys.stderr)
        for error in errors:
            print(f" - {error}", file=sys.stderr)
        return 1
    print(f"PASS: Companion screen feature roadmap verified -> {rel(fixture_path)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
