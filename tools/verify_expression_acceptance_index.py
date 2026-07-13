#!/usr/bin/env python3
"""Verify the Companion screen expression acceptance index."""

from __future__ import annotations

import argparse
import json
import pathlib
import sys
from typing import Any

from screen_runtime_candidate import current_candidate


REPO_ROOT = pathlib.Path(__file__).resolve().parents[1]
DEFAULT_FIXTURE = pathlib.Path("docs/validation/companion-screen-acceptance-index.json")
SCREEN_DOC = REPO_ROOT / "docs" / "companion_screen_expression_system.md"
WBA_RULES = REPO_ROOT / "docs" / "stm32wba_migration_rules.md"
SCHEMA_ID = "companion.pendant.screen_acceptance_index.v1"
WB55_MENU = REPO_ROOT / "docs/validation/companion-screen-bilingual-menu-wb55.json"
WB55_RUNTIME_LOGS = REPO_ROOT / "docs/validation/companion-screen-wb55-runtime-recheck-logs.json"
WB55_RUNTIME_PROMOTION = REPO_ROOT / "docs/validation/companion-screen-wb55-runtime-promotion.json"
CANDIDATE = current_candidate()
RUNTIME_GATE_ID = f"wb55_rev{CANDIDATE.revision}_runtime_recheck"
RUNTIME_RUN_REPORT = (CANDIDATE.run_root / "runtime-recheck-run.json").relative_to(REPO_ROOT).as_posix()
WB55_RUNTIME_PASS_STATUS = CANDIDATE.pass_status


def rel(path: pathlib.Path) -> str:
    try:
        return path.resolve().relative_to(REPO_ROOT).as_posix()
    except ValueError:
        return path.as_posix()


def require(condition: bool, message: str, errors: list[str]) -> None:
    if not condition:
        errors.append(message)


def is_wb55_runtime_recheck_proven() -> bool:
    """Return true only when first-hand active-candidate logs have been promoted."""
    try:
        menu = json.loads(WB55_MENU.read_text(encoding="utf-8"))
        logs = json.loads(WB55_RUNTIME_LOGS.read_text(encoding="utf-8"))
        promotion = json.loads(WB55_RUNTIME_PROMOTION.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return False
    return (
        menu.get("runtime_evidence", {}).get("status") == WB55_RUNTIME_PASS_STATUS
        and logs.get("status") == "PASS"
        and promotion.get("status") == "APPLIED"
    )


def item(
    item_id: str,
    title: str,
    status: str,
    summary: str,
    evidence_paths: list[str],
    validation_commands: list[str],
    wba_impact: str,
    missing_hardware_facts: list[str] | None = None,
) -> dict[str, Any]:
    return {
        "id": item_id,
        "title": title,
        "status": status,
        "summary": summary,
        "evidence_paths": evidence_paths,
        "validation_commands": validation_commands,
        "wba_impact": wba_impact,
        "missing_hardware_facts": missing_hardware_facts or [],
    }


def build_index() -> dict[str, Any]:
    wb55_runtime_proven = is_wb55_runtime_recheck_proven()
    items = [
        item(
            "no_hardware_expression_renderer",
            "No-hardware ExpressionV1 renderer",
            "PASS",
            "All ExpressionV1 faces render deterministic PBM fixtures for 2.13in and 1.54in variants.",
            [
                "app/companion_pendant/epaper/card_renderer.py",
                "docs/validation/companion-pendant-firmware-bringup-1.6-epaper-fixtures.json",
                "docs/validation/epaper/expression-preview.svg",
                "docs/validation/companion-screen-expression-preview.json",
            ],
            [
                "python .\\tools\\render_epaper_fixtures.py --self-test",
                "python .\\tools\\render_expression_preview.py",
                "python .\\tools\\verify_epaper_assets.py",
            ],
            "Portable renderer contract is reusable for WBA without STM32 platform dependencies.",
        ),
        item(
            "expression_visual_contract",
            "Expression visual contract",
            "PASS",
            "ExpressionV1 PBM fixtures expose nonblank, density-bounded, visually distinct face crops so sync-complete, happy, and other faces cannot regress into duplicate artwork.",
            [
                "app/companion_pendant/epaper/card_renderer.py",
                "tools/verify_expression_visual_contract.py",
                "docs/validation/companion-screen-expression-visual-contract.json",
                "docs/validation/companion-pendant-firmware-bringup-1.6-epaper-fixtures.json",
                "docs/validation/epaper/expression-preview.svg",
                "docs/companion_screen_expression_system.md",
                "docs/stm32wba_migration_rules.md",
                "app/companion_pendant/epaper/README.md",
            ],
            [
                "python .\\tools\\render_epaper_fixtures.py --self-test",
                "python .\\tools\\verify_expression_visual_contract.py",
                "python .\\tools\\verify_epaper_assets.py",
                "python .\\tools\\verify_expression_wba_portability.py",
            ],
            "WBA ports reuse the same PBM fixtures and must preserve visually distinct ExpressionV1 faces while replacing only target transport.",
        ),
        item(
            "expression_visual_acceptance_matrix",
            "Expression visual acceptance matrix",
            "PASS",
            "A generated per-face matrix links every ExpressionV1 visual fixture and metric to copy, source signals, policy cases, and host coverage, while explicitly leaving real panel refresh deferred.",
            [
                "tools/render_expression_visual_acceptance_matrix.py",
                "docs/validation/companion-screen-expression-visual-acceptance-matrix.json",
                "docs/validation/companion-screen-expression-visual-acceptance-matrix.md",
                "docs/validation/companion-screen-expression-visual-contract.json",
                "docs/validation/companion-screen-expression-host-manifest.json",
                "docs/validation/companion-pendant-firmware-bringup-1.6-epaper-fixtures.json",
                "docs/validation/epaper/expression-preview.svg",
                "docs/validation/epaper/expression-storyboard.svg",
                "docs/companion_screen_expression_system.md",
                "docs/stm32wba_migration_rules.md",
                "app/companion_pendant/epaper/README.md",
            ],
            [
                "python .\\tools\\render_expression_visual_acceptance_matrix.py",
                "python .\\tools\\render_expression_visual_acceptance_matrix.py --self-test",
                "python .\\tools\\verify_expression_visual_contract.py",
                "python .\\tools\\render_expression_host_manifest.py",
                "python .\\tools\\verify_epaper_assets.py",
                "python .\\tools\\verify_expression_wba_portability.py",
            ],
            "WBA ports must preserve the same per-face visual matrix, PBM hashes, copy, and host face/signal mapping before replacing only target panel transport.",
        ),
        item(
            "generated_art_style_contract",
            "Generated-art style contract",
            "PASS",
            "The generated pet/menu reference art is captured as a named style contract with machine-readable pet and menu anchors, keeping future生图 adjustments fast without scattering hard-coded coordinates or moving large art into internal Flash.",
            [
                "app/companion_pendant/epaper/pet_visual_style.h",
                "tools/generate_screen_menu_assets.py",
                "tools/render_generated_art_style_contract.py",
                "docs/validation/companion-screen-generated-art-style-contract.md",
                "docs/validation/companion-screen-generated-art-style-contract.json",
                "docs/validation/companion-screen-generated-art-style-contract.snapshot.md",
                "docs/companion_screen_expression_system.md",
                "docs/companion_screen_project_plan.md",
                "app/companion_pendant/epaper/README.md",
            ],
            [
                "python .\\tools\\render_generated_art_style_contract.py",
                "python .\\tools\\verify_pet_expression_system.py",
                "python .\\tools\\verify_screen_menu_assets.py",
                "python .\\tools\\verify_expression_wba_portability.py",
            ],
            "WBA ports reuse the same style contract and external CEMP resource policy; only target transport, storage drivers, and panel timing are replaced.",
        ),
        item(
            "screen_generation_swap_guard",
            "New/old screen generation swap guard",
            "PASS",
            "The project separates physical e-paper ghosting from old/new resource interleaving using the 2026-07-13 research note and release ledger: CEMP revisions must activate atomically, drain or discard stale queued frames, mark display_result coherent_generation, and never mix old procedural faces, old menu PBM, old sheet crops, or stale framebuffer content into the normal product path.",
            [
                "docs/companion_screen_project_plan.md",
                "docs/validation/companion-screen-generation-swap-research.md",
                "docs/validation/companion-screen-display-queue-generation-hygiene.json",
                "docs/validation/companion-screen-generation-release-ledger.json",
                "docs/validation/companion-screen-display-drain-contract.json",
                "tools/verify_screen_refresh_feel_contract.py",
                "tools/verify_display_queue_generation_hygiene.py",
                "tools/verify_expression_display_drain.py",
                "docs/validation/companion-screen-refresh-feel-contract.json",
                "docs/validation/companion-screen-generated-expression-sheet-import.json",
                "docs/validation/companion-screen-generated-expression-normal-pack-contact-sheet.json",
            ],
            [
                "python .\\tools\\verify_screen_refresh_feel_contract.py",
                "python .\\tools\\verify_display_queue_generation_hygiene.py",
                "python .\\tools\\verify_screen_generation_release_ledger.py",
                "python .\\tools\\verify_expression_display_drain.py",
                "python .\\tools\\import_generated_expression_sheet.py",
                "python .\\tools\\render_generated_expression_normal_pack_contact_sheet.py",
            ],
            "WBA55/WBA65 must preserve resource-generation activation and stale-frame draining semantics while replacing only target storage and panel transport.",
        ),
        item(
            "screen_refresh_feel_contract",
            "Screen refresh feel and ghosting contract",
            "PASS",
            "The product refresh contract records the vendor-backed e-paper tradeoff: differential partial refresh for touch interaction, one quiet maintenance cleanup after contact settles, and full refresh only for unknown baseline or fault recovery.",
            [
                "docs/companion_screen_project_plan.md",
                "tools/verify_screen_refresh_feel_contract.py",
                "docs/validation/companion-screen-refresh-feel-contract.json",
                "app/companion_pendant/epaper/refresh_policy.c",
                "app/companion_pendant/epaper/display_queue.c",
                "app/companion_pendant/epaper/panel_target_stm32wb_ssd1681.c",
            ],
            [
                "python .\\tools\\verify_screen_refresh_feel_contract.py",
                "python .\\tools\\verify_epaper_refresh_policy.py",
                "python .\\tools\\verify_screen_menu_assets.py",
            ],
            "WBA panel targets must preserve portable refresh intents and choose target waveforms without changing scene/player behavior.",
        ),
        item(
            "expression_layout_contract",
            "Expression layout contract",
            "PASS",
            "ExpressionV1 title/body/footer copy fits the 2.13in and 1.54in renderer budgets without truncation or body/footer overlap.",
            [
                "app/companion_pendant/epaper/card_renderer.py",
                "tools/verify_expression_layout_contract.py",
                "docs/validation/companion-screen-expression-layout-contract.json",
                "docs/validation/companion-screen-expression-catalog.json",
                "docs/validation/companion-screen-expression-visual-contract.json",
                "docs/companion_screen_expression_system.md",
                "docs/stm32wba_migration_rules.md",
                "app/companion_pendant/epaper/README.md",
            ],
            [
                "python .\\tools\\verify_expression_layout_contract.py",
                "python .\\tools\\verify_expression_catalog_contract.py",
                "python .\\tools\\verify_expression_visual_contract.py",
                "python .\\tools\\verify_epaper_assets.py",
                "python .\\tools\\verify_expression_wba_portability.py",
            ],
            "WBA ports must keep the same ExpressionV1 copy budget and layout safety while replacing only target transport.",
        ),
        item(
            "ble_to_expression_policy",
            "BLE/status to ExpressionV1 policy",
            "PASS",
            "Status snapshots and diagnostic event names map to visible ExpressionV1 cards.",
            [
                "app/companion_pendant/epaper/expression_policy.py",
                "docs/validation/companion-screen-expression-policy.json",
            ],
            [
                "python .\\tools\\verify_expression_policy.py",
                "python .\\tools\\verify_companion_gatt_static.py",
            ],
            "Portable policy can be reused by a WBA host/diagnostic path.",
        ),
        item(
            "wb55_display_queue_boundary",
            "WB55 display queue boundary",
            "PASS",
            "WB55 GATT callbacks enqueue card/expression work and a display task owns panel completion.",
            [
                "app/companion_pendant/epaper/display_queue.h",
                "app/companion_pendant/epaper/display_queue.c",
                "app/companion_pendant/epaper/panel_adapter.h",
                "app/companion_pendant/epaper/panel_adapter.c",
                "cubeide/Companion_Nucleo_WB55RG_Bringup/Core/Src/app_ble.c",
            ],
            [
                "python .\\tools\\verify_display_queue_static.py",
                "pwsh -NoProfile -File .\\tools\\build_nucleo_bringup.ps1 -Force",
            ],
            "WBA should add its own platform task/GATT adapter while reusing the queue contract.",
        ),
        item(
            "display_queue_fault_paths",
            "Display queue fault paths",
            "PASS",
            "Queue-full, payload-too-long, unsupported-expression, and expression enqueue rollback paths publish stable host-visible status.",
            [
                "app/companion_pendant/epaper/display_queue.h",
                "app/companion_pendant/epaper/display_queue.c",
                "cubeide/Companion_Nucleo_WB55RG_Bringup/Core/Src/app_ble.c",
                "docs/validation/companion-screen-display-queue-faults.json",
            ],
            [
                "python .\\tools\\verify_display_queue_fault_paths.py",
                "python .\\tools\\verify_display_queue_static.py",
                "pwsh -NoProfile -File .\\tools\\build_nucleo_bringup.ps1 -Force",
            ],
            "WBA must preserve the same queue fault status/error meanings and expression rollback behavior while replacing only platform scheduling.",
        ),
        item(
            "display_queue_telemetry",
            "Display queue telemetry",
            "PASS",
            "The portable display queue exposes a stats snapshot for pending, high-water, dropped, queue bounds, and sequence counters without adding platform dependencies or changing CardStatusV1.",
            [
                "app/companion_pendant/epaper/display_queue.h",
                "app/companion_pendant/epaper/display_queue.c",
                "cubeide/Companion_Nucleo_WB55RG_Bringup/Core/Src/app_ble.c",
                "docs/validation/companion-screen-display-queue-telemetry.json",
                "docs/companion_screen_expression_system.md",
                "docs/stm32wba_migration_rules.md",
            ],
            [
                "python .\\tools\\verify_display_queue_telemetry.py",
                "python .\\tools\\verify_display_queue_static.py",
                "python .\\tools\\verify_display_queue_fault_paths.py",
                "python .\\tools\\verify_expression_wba_portability.py",
                "pwsh -NoProfile -File .\\tools\\build_nucleo_bringup.ps1",
            ],
            "WBA schedulers should preserve the same queue telemetry stats snapshot so slow real-panel refresh pressure can be diagnosed without changing host-visible CardStatusV1.",
        ),
        item(
            "screen_display_drain_contract",
            "Screen display drain contract",
            "PASS",
            "WB55 display task drains one queued request per scheduler pass, records runtime diagnostics before final CardStatusV1, and reschedules only while work remains.",
            [
                "app/companion_pendant/epaper/display_queue.h",
                "app/companion_pendant/epaper/display_queue.c",
                "app/companion_pendant/epaper/panel_adapter.h",
                "app/companion_pendant/epaper/screen_runtime.h",
                "cubeide/Companion_Nucleo_WB55RG_Bringup/Core/Src/app_ble.c",
                "tools/verify_expression_display_drain.py",
                "docs/validation/companion-screen-display-drain-contract.json",
                "docs/companion_screen_expression_system.md",
                "docs/stm32wba_migration_rules.md",
                "app/companion_pendant/epaper/README.md",
            ],
            [
                "python .\\tools\\verify_expression_display_drain.py",
                "python .\\tools\\verify_display_queue_static.py",
                "python .\\tools\\verify_display_queue_telemetry.py",
                "python .\\tools\\verify_expression_screen_runtime_snapshot.py",
                "python .\\tools\\verify_expression_screen_runtime_diagnostics.py",
                "python .\\tools\\verify_expression_wba_portability.py",
                "pwsh -NoProfile -File .\\tools\\build_nucleo_bringup.ps1",
            ],
            "WBA display tasks must preserve one-request drain, target-refresh callback use, runtime diagnostics, final CardStatusV1 identity, and pending-work rescheduling.",
        ),
        item(
            "wb55_boot_idle_expression",
            "WB55 boot idle expression",
            "PASS",
            "WB55 startup enqueues the default idle ExpressionV1 card through the same display queue path.",
            [
                "cubeide/Companion_Nucleo_WB55RG_Bringup/Core/Src/app_ble.c",
                "app/companion_pendant/epaper/expression_state.h",
                "app/companion_pendant/epaper/expression_state.c",
                "docs/validation/companion-screen-firmware-expression-state.json",
            ],
            [
                "python .\\tools\\verify_expression_firmware_state.py",
                "python .\\tools\\verify_display_queue_static.py",
                "pwsh -NoProfile -File .\\tools\\build_nucleo_bringup.ps1",
            ],
            "Future WBA startup should enqueue BOOT_IDLE through its own platform scheduler while reusing the same state model.",
        ),
        item(
            "screen_status_observability",
            "Screen status observability",
            "PASS",
            "CardStatusV1 exposes stable render states, last-error codes, request identity, refresh_count, and dry-run no-panel diagnostics.",
            [
                "app/companion_pendant/gatt/companion_gatt_stm32wb.h",
                "cubeide/Companion_Nucleo_WB55RG_Bringup/Core/Src/app_ble.c",
                "docs/ble_gatt_contract.md",
                "docs/validation/companion-screen-status-observability.json",
                "docs/validation/companion_ble_matrix.json",
            ],
            [
                "python .\\tools\\verify_expression_status_observability.py",
                "python .\\tools\\verify_companion_ble_matrix.py",
                "python .\\tools\\verify_display_queue_static.py",
            ],
            "WBA must preserve CardStatusV1 numeric state/error meanings while swapping only the platform scheduler and panel driver.",
        ),
        item(
            "host_ble_expression_status_fixture",
            "Host BLE ExpressionV1 status fixture",
            "PASS",
            "The no-hardware BLE matrix correlates ExpressionV1 CardStatusV1 accepted/final states with diagnostic expression/signal payloads.",
            [
                "tools/companion_ble_tool.py",
                "tools/verify_companion_ble_matrix.py",
                "docs/validation/companion_ble_matrix.json",
                "docs/validation/companion-screen-status-observability.json",
            ],
            [
                "python .\\tools\\companion_ble_tool.py --self-test",
                "python .\\tools\\verify_companion_ble_matrix.py",
                "python .\\tools\\verify_expression_status_observability.py",
            ],
            "WBA real BLE bench should preserve this same status/diagnostic fixture shape while swapping only the platform BLE adapter.",
        ),
        item(
            "host_ble_expression_extended_status_fixture",
            "Host BLE ExpressionV1 extended status coverage",
            "PASS",
            "The no-hardware BLE matrix observes idle, sleepy, recording, low-battery, sync-complete, and error ExpressionV1 requests through CardStatusV1 and diagnostic arg3 decode.",
            [
                "tools/companion_ble_tool.py",
                "tools/verify_companion_ble_matrix.py",
                "tools/verify_expression_status_observability.py",
                "docs/validation/companion_ble_matrix.json",
                "docs/validation/companion-screen-status-observability.json",
                "docs/companion_screen_expression_system.md",
                "docs/ble_gatt_contract.md",
                "docs/stm32wba_migration_rules.md",
            ],
            [
                "python .\\tools\\companion_ble_tool.py --self-test",
                "python .\\tools\\verify_companion_ble_matrix.py",
                "python .\\tools\\verify_expression_status_observability.py",
                "python .\\tools\\verify_expression_wba_portability.py",
            ],
            "WBA real BLE benches should keep the six-face screen_expression_status fixture shape so extended ExpressionV1 status remains host-observable before panel parity is claimed.",
        ),
        item(
            "host_ble_expression_status_sequence",
            "Host BLE ExpressionV1 status sequence integrity",
            "PASS",
            "The no-hardware BLE matrix proves each ExpressionV1 accepted/final CardStatusV1 pair has contiguous refresh_count values, stable request/content identity, deterministic expression CRCs, and matching diagnostic arg3 decode.",
            [
                "tools/verify_expression_host_status_sequence.py",
                "tools/companion_ble_tool.py",
                "tools/verify_companion_ble_matrix.py",
                "tools/verify_expression_status_observability.py",
                "docs/validation/companion-screen-expression-host-status-sequence.json",
                "docs/validation/companion_ble_matrix.json",
                "docs/companion_screen_expression_system.md",
                "docs/stm32wba_migration_rules.md",
                "docs/ble_gatt_contract.md",
            ],
            [
                "python .\\tools\\verify_expression_host_status_sequence.py",
                "python .\\tools\\companion_ble_tool.py --self-test",
                "python .\\tools\\verify_companion_ble_matrix.py",
                "python .\\tools\\verify_expression_status_observability.py",
                "python .\\tools\\verify_expression_wba_portability.py",
            ],
            "WBA real BLE benches should preserve the same screen_expression_status refresh_count sequence, request/content identity, expression CRC model, and diagnostic arg3 decode before panel parity is claimed.",
        ),
        item(
            "expression_host_manifest",
            "ExpressionV1 host manifest",
            "PASS",
            "A generated host manifest lists every ExpressionV1 face with copy, priority, recovery, signals, policy cases, CardStatusV1/diagnostic observability, and legacy/demo host coverage.",
            [
                "tools/render_expression_host_manifest.py",
                "docs/validation/companion-screen-expression-host-manifest.json",
                "docs/validation/companion-screen-expression-host-manifest.md",
                "docs/validation/companion-screen-expression-catalog.json",
                "docs/validation/companion-screen-expression-policy.json",
                "docs/validation/companion-screen-expression-host-status-sequence.json",
                "docs/validation/companion-screen-expression-demo-host-status-sequence.json",
                "docs/validation/companion-screen-expression-state-telemetry.json",
                "docs/companion_screen_expression_system.md",
                "app/companion_pendant/epaper/README.md",
                "docs/stm32wba_migration_rules.md",
            ],
            [
                "python .\\tools\\render_expression_host_manifest.py",
                "python .\\tools\\render_expression_host_manifest.py --self-test",
                "python .\\tools\\verify_expression_catalog_contract.py",
                "python .\\tools\\verify_expression_policy.py",
                "python .\\tools\\verify_expression_host_status_sequence.py",
                "python .\\tools\\verify_expression_demo_host_status_sequence.py",
                "python .\\tools\\verify_expression_state_telemetry.py",
            ],
            "WBA host/status adapters must keep the same face IDs, signal IDs, diagnostic arg3 model, and CardStatusV1 meanings while replacing only platform transport.",
        ),
        item(
            "screen_expression_demo_host_status_sequence",
            "Screen expression demo host status sequence",
            "PASS",
            "The full demo sequence has a host-visible CardStatusV1 contract: 29 accepted/final pairs cover every ExpressionV1 face, while 8 held steps emit no host status.",
            [
                "tools/verify_expression_demo_host_status_sequence.py",
                "docs/validation/companion-screen-expression-demo-host-status-sequence.json",
                "docs/validation/companion-screen-expression-demo-sequence.json",
                "docs/validation/companion-screen-expression-host-status-sequence.json",
                "docs/validation/companion-screen-expression-catalog.json",
                "docs/validation/companion-screen-real-ble-bench.json",
                "tools/companion_ble_real_bench.py",
                "docs/companion_screen_expression_system.md",
                "docs/ble_gatt_contract.md",
                "docs/stm32wba_migration_rules.md",
                "app/companion_pendant/epaper/README.md",
            ],
            [
                "python .\\tools\\verify_expression_demo_host_status_sequence.py",
                "python .\\tools\\verify_expression_demo_sequence.py",
                "python .\\tools\\verify_expression_host_status_sequence.py",
                "python .\\tools\\verify_expression_catalog_contract.py",
                "python .\\tools\\verify_expression_real_ble_screen_bench.py",
                "python .\\tools\\verify_expression_wba_portability.py",
            ],
            "WBA real BLE artifacts can carry screen_expression_demo_status so every demo face stays host-observable, while held_steps_emit_no_host_status protects duplicate/lower-priority suppression.",
        ),
        item(
            "screen_settings_expression_policy",
            "Screen settings expression policy",
            "PASS",
            "Quiet hours and display-off settings map to sleepy without hiding recording, low-battery, or error faces.",
            [
                "app/companion_pendant/epaper/expression_policy.py",
                "docs/ble_gatt_contract.md",
                "docs/validation/companion-screen-settings-policy.json",
            ],
            [
                "python .\\tools\\verify_expression_settings_policy.py",
                "python .\\tools\\verify_expression_policy.py",
                "python .\\tools\\verify_expression_wba_portability.py",
            ],
            "WBA should reuse the same settings-to-expression policy while replacing only platform-specific settings transport.",
        ),
        item(
            "firmware_expression_state",
            "Firmware ExpressionV1 state path",
            "PASS",
            "Portable C state model matches renderer copy, policy priorities, and WB55 event enqueue path.",
            [
                "app/companion_pendant/epaper/expression_state.h",
                "app/companion_pendant/epaper/expression_state.c",
                "docs/validation/companion-screen-firmware-expression-state.json",
            ],
            [
                "python .\\tools\\verify_expression_firmware_state.py",
                "python .\\tools\\verify_expression_wba_portability.py",
            ],
            "Expression state is kept HAL-free and reusable under a future WBA adapter.",
        ),
        item(
            "expression_state_telemetry_snapshot",
            "Expression state telemetry snapshot",
            "PASS",
            "The portable ExpressionV1 state model exposes a stats snapshot for current face, last signal, revision, visible age, auto-recovery dwell, and duplicate suppression.",
            [
                "app/companion_pendant/epaper/expression_state.h",
                "app/companion_pendant/epaper/expression_state.c",
                "cubeide/Companion_Nucleo_WB55RG_Bringup/Core/Src/app_ble.c",
                "docs/validation/companion-screen-expression-state-telemetry.json",
                "docs/companion_screen_expression_system.md",
                "docs/stm32wba_migration_rules.md",
                "tools/verify_expression_state_telemetry.py",
            ],
            [
                "python .\\tools\\verify_expression_state_telemetry.py",
                "python .\\tools\\verify_expression_firmware_state.py",
                "python .\\tools\\verify_expression_journeys.py",
                "python .\\tools\\verify_display_queue_static.py",
                "python .\\tools\\verify_expression_wba_portability.py",
                "pwsh -NoProfile -File .\\tools\\build_nucleo_bringup.ps1",
            ],
            "WBA scheduler hooks should use the same expression state stats snapshot for current face, dwell timing, and duplicate suppression diagnostics while replacing only target timing glue.",
        ),
        item(
            "expression_catalog_contract",
            "ExpressionV1 catalog contract",
            "PASS",
            "Stable ExpressionV1 and signal numeric IDs are tied to copy, priority, auto-recovery, and diagnostic payload semantics for host/WBA reuse.",
            [
                "tools/verify_expression_catalog_contract.py",
                "docs/validation/companion-screen-expression-catalog.json",
                "app/companion_pendant/epaper/expression_state.h",
                "app/companion_pendant/epaper/expression_state.c",
                "app/companion_pendant/epaper/card_renderer.py",
                "app/companion_pendant/epaper/expression_policy.py",
                "docs/validation/companion-screen-firmware-expression-state.json",
                "docs/validation/companion_ble_matrix.json",
                "docs/companion_screen_expression_system.md",
                "docs/stm32wba_migration_rules.md",
            ],
            [
                "python .\\tools\\verify_expression_catalog_contract.py",
                "python .\\tools\\verify_expression_firmware_state.py",
                "python .\\tools\\verify_epaper_assets.py",
                "python .\\tools\\verify_expression_status_observability.py",
                "python .\\tools\\verify_expression_wba_portability.py",
            ],
            "WBA adapters and host tools must preserve the catalog's stable numeric IDs, expression card slot, request ID base, and diagnostic arg3 model.",
        ),
        item(
            "expression_copy_contract",
            "ExpressionV1 copy contract",
            "PASS",
            "ExpressionV1 title/body/footer copy is synchronized across renderer, firmware, catalog, layout, priority matrix, and generated PBM fixtures.",
            [
                "tools/verify_expression_copy_contract.py",
                "docs/validation/companion-screen-expression-copy-contract.json",
                "app/companion_pendant/epaper/card_renderer.py",
                "app/companion_pendant/epaper/expression_state.c",
                "app/companion_pendant/epaper/expression_policy.py",
                "docs/validation/companion-screen-expression-catalog.json",
                "docs/validation/companion-screen-firmware-expression-state.json",
                "docs/validation/companion-screen-expression-layout-contract.json",
                "docs/validation/companion-screen-expression-priority-matrix.json",
                "docs/validation/companion-pendant-firmware-bringup-1.6-epaper-fixtures.json",
                "docs/companion_screen_expression_system.md",
                "docs/stm32wba_migration_rules.md",
                "app/companion_pendant/epaper/README.md",
            ],
            [
                "python .\\tools\\verify_expression_copy_contract.py",
                "python .\\tools\\verify_expression_catalog_contract.py",
                "python .\\tools\\verify_expression_firmware_state.py",
                "python .\\tools\\verify_expression_layout_contract.py",
                "python .\\tools\\verify_expression_priority_matrix.py",
                "python .\\tools\\verify_epaper_assets.py",
                "python .\\tools\\verify_expression_wba_portability.py",
            ],
            "WBA adapters must reuse the same ExpressionV1 user-visible copy and must not fork title/body/footer text in target glue.",
        ),
        item(
            "expression_priority_matrix",
            "Expression priority matrix",
            "PASS",
            "Every initialized ExpressionV1 face/signal pair has a recorded apply, suppress, or block outcome, including settings sleepy and battery recovered guards.",
            [
                "app/companion_pendant/epaper/expression_state.h",
                "app/companion_pendant/epaper/expression_state.c",
                "tools/verify_expression_priority_matrix.py",
                "docs/validation/companion-screen-expression-priority-matrix.json",
                "docs/validation/companion-screen-expression-catalog.json",
                "docs/validation/companion-screen-firmware-expression-state.json",
                "docs/companion_screen_expression_system.md",
                "docs/stm32wba_migration_rules.md",
                "app/companion_pendant/epaper/README.md",
            ],
            [
                "python .\\tools\\verify_expression_priority_matrix.py",
                "python .\\tools\\verify_expression_catalog_contract.py",
                "python .\\tools\\verify_expression_firmware_state.py",
                "python .\\tools\\verify_expression_journeys.py",
                "python .\\tools\\verify_expression_wba_portability.py",
            ],
            "WBA scheduler/status adapters must preserve the same priority, duplicate, lowering, battery recovery, and transient/stable recovery matrix.",
        ),
        item(
            "expression_input_source_matrix",
            "Expression input source matrix",
            "PASS",
            "Every product input source that can request an ExpressionV1 signal is linked to a focused fixture and WBA adapter checklist entry.",
            [
                "app/companion_pendant/epaper/expression_events.h",
                "app/companion_pendant/epaper/expression_events.c",
                "cubeide/Companion_Nucleo_WB55RG_Bringup/Core/Src/app_ble.c",
                "tools/verify_expression_input_source_matrix.py",
                "docs/validation/companion-screen-expression-input-source-matrix.json",
                "docs/validation/companion-screen-expression-event-bridge.json",
                "docs/validation/companion-screen-settings-policy.json",
                "docs/validation/companion-screen-device-status-expression-hook.json",
                "docs/validation/companion-screen-battery-expression-hook.json",
                "docs/validation/companion-screen-recording-state-expression-hook.json",
                "docs/validation/companion-screen-interaction-status-expression-hook.json",
                "docs/validation/companion-screen-ota-expression-hook.json",
                "docs/companion_screen_expression_system.md",
                "docs/stm32wba_migration_rules.md",
                "app/companion_pendant/epaper/README.md",
            ],
            [
                "python .\\tools\\verify_expression_input_source_matrix.py",
                "python .\\tools\\verify_expression_event_bridge.py",
                "python .\\tools\\verify_expression_settings_policy.py",
                "python .\\tools\\verify_expression_device_status_hook.py",
                "python .\\tools\\verify_expression_battery_hook.py",
                "python .\\tools\\verify_expression_recording_state_hook.py",
                "python .\\tools\\verify_expression_interaction_status_hook.py",
                "python .\\tools\\verify_expression_ota_hook.py",
                "python .\\tools\\verify_expression_wba_portability.py",
            ],
            "WBA status adapters must preserve every boot, diagnostic, settings, status, recording, battery, interaction, and OTA expression input source.",
        ),
        item(
            "expression_unknown_signal_guard",
            "Expression unknown signal guard",
            "PASS",
            "Unsupported or future ExpressionV1 signals are rejected through a portable preflight API before visible state, duplicate counters, display queue work, or CardStatusV1 request identity changes.",
            [
                "app/companion_pendant/epaper/expression_state.h",
                "app/companion_pendant/epaper/expression_state.c",
                "app/companion_pendant/epaper/README.md",
                "tools/verify_expression_signal_guard.py",
                "docs/validation/companion-screen-expression-signal-guard.json",
                "docs/validation/companion-screen-expression-catalog.json",
                "docs/validation/companion-screen-firmware-expression-state.json",
                "docs/companion_screen_expression_system.md",
                "docs/stm32wba_migration_rules.md",
            ],
            [
                "python .\\tools\\verify_expression_signal_guard.py",
                "python .\\tools\\verify_expression_catalog_contract.py",
                "python .\\tools\\verify_expression_firmware_state.py",
                "python .\\tools\\verify_expression_wba_portability.py",
            ],
            "WBA adapters should preserve comp_epaper_expression_signal_is_supported() and the append-only signal catalog so unsupported future signals are rejected before platform glue changes display state or queue work.",
        ),
        item(
            "expression_duplicate_refresh_suppression",
            "Expression duplicate refresh suppression",
            "PASS",
            "Repeated signals, including equivalent status notifications after control events, are suppressed when they resolve to the current visible ExpressionV1 face.",
            [
                "app/companion_pendant/epaper/expression_state.h",
                "app/companion_pendant/epaper/expression_state.c",
                "tools/verify_expression_journeys.py",
                "docs/validation/companion-screen-firmware-expression-state.json",
                "docs/validation/companion-screen-expression-journeys.json",
            ],
            [
                "python .\\tools\\verify_expression_firmware_state.py",
                "python .\\tools\\verify_expression_journeys.py",
                "python .\\tools\\verify_display_queue_static.py",
            ],
            "WBA should preserve duplicate suppression in the portable state model while replacing only scheduler and panel transport code.",
        ),
        item(
            "expression_transient_auto_recovery",
            "Expression transient auto recovery",
            "PASS",
            "Transient ExpressionV1 faces recover to idle through a portable elapsed-time tick while recording, low-battery, error, idle, and sleepy remain stable.",
            [
                "app/companion_pendant/epaper/expression_state.h",
                "app/companion_pendant/epaper/expression_state.c",
                "tools/verify_expression_journeys.py",
                "docs/validation/companion-screen-firmware-expression-state.json",
                "docs/validation/companion-screen-expression-journeys.json",
            ],
            [
                "python .\\tools\\verify_expression_firmware_state.py",
                "python .\\tools\\verify_expression_journeys.py",
                "python .\\tools\\verify_expression_wba_portability.py",
            ],
            "WBA should feed elapsed time from its own scheduler into the same portable state tick API without changing expression names or priorities.",
        ),
        item(
            "wb55_expression_tick_scheduler",
            "WB55 expression tick scheduler",
            "PASS",
            "WB55 uses a single-shot HW_TS timer to wake the display task and feed elapsed time into the portable expression tick API.",
            [
                "cubeide/Companion_Nucleo_WB55RG_Bringup/Core/Src/app_ble.c",
                "app/companion_pendant/epaper/expression_state.h",
                "app/companion_pendant/epaper/expression_state.c",
                "docs/companion_screen_expression_system.md",
                "docs/validation/companion-screen-firmware-expression-state.json",
            ],
            [
                "python .\\tools\\verify_display_queue_static.py",
                "python .\\tools\\verify_expression_firmware_state.py",
                "pwsh -NoProfile -File .\\tools\\build_nucleo_bringup.ps1",
            ],
            "WBA should replace HW_TS/HAL_GetTick with its own scheduler while preserving the same portable tick and enqueue behavior.",
        ),
        item(
            "wb55_settings_expression_hint",
            "WB55 settings expression hint",
            "PASS",
            "WB55 SettingsV1 writes enqueue sleepy/recovery expression hints without hiding recording, low-battery, or error faces.",
            [
                "cubeide/Companion_Nucleo_WB55RG_Bringup/Core/Src/app_ble.c",
                "app/companion_pendant/epaper/expression_state.h",
                "app/companion_pendant/epaper/expression_state.c",
                "docs/validation/companion-screen-firmware-expression-state.json",
                "docs/validation/companion-screen-expression-journeys.json",
            ],
            [
                "python .\\tools\\verify_expression_firmware_state.py",
                "python .\\tools\\verify_expression_journeys.py",
                "python .\\tools\\verify_display_queue_static.py",
            ],
            "WBA must map SettingsV1 quiet-hours/display-off writes through the same settings sleepy signal and preserve the stable-state guard.",
        ),
        item(
            "wb55_device_status_expression_hint",
            "WB55 device status expression hint",
            "PASS",
            "WB55 DeviceStatusV1 publishes can feed fault, active-audio, and disconnected mode signals into the portable expression mapper after display scheduling is ready.",
            [
                "cubeide/Companion_Nucleo_WB55RG_Bringup/Core/Src/app_ble.c",
                "app/companion_pendant/epaper/expression_events.h",
                "app/companion_pendant/epaper/expression_events.c",
                "docs/validation/companion-screen-device-status-expression-hook.json",
            ],
            [
                "python .\\tools\\verify_expression_device_status_hook.py",
                "python .\\tools\\verify_expression_event_bridge.py",
                "pwsh -NoProfile -File .\\tools\\build_nucleo_bringup.ps1",
            ],
            "WBA device-status adapters must feed DeviceStatusV1 active_mode/fault_bitmap through the same portable expression mapper after the display scheduler exists.",
        ),
        item(
            "wb55_interaction_status_expression_hint",
            "WB55 interaction status expression hint",
            "PASS",
            "WB55 MeetingStatusV1, SpeakerStatusV1, and WakeWordStatusV1 publishes can feed interaction signals into portable expression mappers after display scheduling is ready.",
            [
                "cubeide/Companion_Nucleo_WB55RG_Bringup/Core/Src/app_ble.c",
                "app/companion_pendant/epaper/expression_events.h",
                "app/companion_pendant/epaper/expression_events.c",
                "docs/validation/companion-screen-interaction-status-expression-hook.json",
            ],
            [
                "python .\\tools\\verify_expression_interaction_status_hook.py",
                "python .\\tools\\verify_expression_event_bridge.py",
                "pwsh -NoProfile -File .\\tools\\build_nucleo_bringup.ps1",
            ],
            "WBA interaction-status adapters must feed MeetingStatusV1, SpeakerStatusV1, and WakeWordStatusV1 through the same portable expression mapper family after the display scheduler exists.",
        ),
        item(
            "wb55_battery_expression_hint",
            "WB55 battery expression hint",
            "PASS",
            "WB55 BatteryChargeV1 publishes can feed low-battery and recovered samples into the portable expression bridge after display scheduling is ready.",
            [
                "cubeide/Companion_Nucleo_WB55RG_Bringup/Core/Src/app_ble.c",
                "app/companion_pendant/epaper/expression_state.h",
                "app/companion_pendant/epaper/expression_state.c",
                "app/companion_pendant/epaper/expression_events.h",
                "app/companion_pendant/epaper/expression_events.c",
                "docs/validation/companion-screen-battery-expression-hook.json",
            ],
            [
                "python .\\tools\\verify_expression_battery_hook.py",
                "python .\\tools\\verify_expression_event_bridge.py",
                "python .\\tools\\verify_expression_firmware_state.py",
                "pwsh -NoProfile -File .\\tools\\build_nucleo_bringup.ps1",
            ],
            "WBA battery adapters must feed BatteryChargeV1 samples through the same low-battery/recovery bridge after the display scheduler exists.",
        ),
        item(
            "battery_recovery_expression_guard",
            "Battery recovery expression guard",
            "PASS",
            "Recovered battery samples clear only a visible low-battery expression and use hysteresis so near-threshold samples do not flicker the face.",
            [
                "app/companion_pendant/epaper/expression_state.h",
                "app/companion_pendant/epaper/expression_state.c",
                "app/companion_pendant/epaper/expression_events.h",
                "app/companion_pendant/epaper/expression_events.c",
                "app/companion_pendant/epaper/expression_policy.py",
                "tools/verify_expression_battery_hook.py",
                "tools/verify_expression_journeys.py",
                "docs/validation/companion-screen-battery-expression-hook.json",
                "docs/validation/companion-screen-expression-journeys.json",
                "docs/validation/companion-screen-firmware-expression-state.json",
                "docs/companion_screen_expression_system.md",
                "docs/stm32wba_migration_rules.md",
            ],
            [
                "python .\\tools\\verify_expression_battery_hook.py",
                "python .\\tools\\verify_expression_journeys.py",
                "python .\\tools\\verify_expression_firmware_state.py",
                "python .\\tools\\verify_expression_event_bridge.py",
                "python .\\tools\\verify_expression_policy.py",
                "pwsh -NoProfile -File .\\tools\\build_nucleo_bringup.ps1",
            ],
            "WBA battery adapters must preserve COMP_EPAPER_EXPRESSION_SIGNAL_BATTERY_RECOVERED and the state guard that clears only low_battery.",
        ),
        item(
            "recording_state_expression_hook",
            "Recording FSM state expression hook",
            "PASS",
            "Portable recording FSM state readback maps active, stopping, transfer, canceled, and error-recovery states into existing ExpressionV1 faces without adding platform dependencies.",
            [
                "app/companion_pendant/epaper/expression_events.h",
                "app/companion_pendant/epaper/expression_events.c",
                "app/companion_pendant/epaper/expression_policy.py",
                "app/companion_pendant/recording/recording_fsm.h",
                "tools/verify_expression_recording_state_hook.py",
                "docs/validation/companion-screen-recording-state-expression-hook.json",
                "docs/validation/companion-screen-expression-policy.json",
                "docs/validation/companion-screen-expression-event-bridge.json",
                "docs/companion_screen_expression_system.md",
                "docs/stm32wba_migration_rules.md",
                "docs/ble_gatt_contract.md",
            ],
            [
                "python .\\tools\\verify_expression_recording_state_hook.py",
                "python .\\tools\\verify_expression_policy.py",
                "python .\\tools\\verify_expression_event_bridge.py",
                "python .\\tools\\verify_expression_wba_portability.py",
            ],
            "WBA recording adapters should feed numeric recording FSM state through comp_epaper_expression_signal_from_recording_state() and keep recording headers/platform glue outside the e-paper module.",
        ),
        item(
            "wb55_ota_readiness_expression_hint",
            "WB55 OTA readiness expression hint",
            "PASS",
            "WB55 OtaReadinessV1 publishes can feed OTA blocker signals into the portable expression mapper after display scheduling is ready.",
            [
                "cubeide/Companion_Nucleo_WB55RG_Bringup/Core/Src/app_ble.c",
                "app/companion_pendant/epaper/expression_events.h",
                "app/companion_pendant/epaper/expression_events.c",
                "docs/validation/companion-screen-ota-expression-hook.json",
            ],
            [
                "python .\\tools\\verify_expression_ota_hook.py",
                "python .\\tools\\verify_expression_event_bridge.py",
                "pwsh -NoProfile -File .\\tools\\build_nucleo_bringup.ps1",
            ],
            "WBA OTA adapters must feed OtaReadinessV1 blocker maps through the same portable expression mapper after the display scheduler exists.",
        ),
        item(
            "diagnostic_event_expression_bridge",
            "Diagnostic-event expression bridge",
            "PASS",
            "Portable C mapper turns Companion diagnostic events into expression signals and ignores e_paper self loops.",
            [
                "app/companion_pendant/epaper/expression_events.h",
                "app/companion_pendant/epaper/expression_events.c",
                "docs/validation/companion-screen-expression-event-bridge.json",
            ],
            [
                "python .\\tools\\verify_expression_event_bridge.py",
                "python .\\tools\\verify_display_queue_static.py",
            ],
            "WBA can feed the same diagnostic event codes into the same expression bridge.",
        ),
        item(
            "user_journey_expression_acceptance",
            "User journey expression acceptance",
            "PASS",
            "Consecutive wake, recording, meeting, speaker, low-battery, recovery, and error flows preserve product priorities.",
            [
                "tools/verify_expression_journeys.py",
                "tools/render_expression_storyboard.py",
                "docs/validation/companion-screen-expression-journeys.json",
                "docs/validation/companion-screen-expression-storyboard.json",
                "docs/validation/epaper/expression-storyboard.svg",
            ],
            [
                "python .\\tools\\verify_expression_journeys.py",
                "python .\\tools\\render_expression_storyboard.py",
                "python .\\tools\\verify_epaper_assets.py",
            ],
            "Journey behavior is portable and should be reused unchanged on WBA.",
        ),
        item(
            "screen_expression_demo_sequence",
            "Screen expression demo sequence",
            "PASS",
            "A deterministic no-hardware demo checklist walks wake, recording, speaker, settings, low-battery, error, and transient recovery flows one item at a time.",
            [
                "tools/verify_expression_demo_sequence.py",
                "docs/validation/companion-screen-expression-demo-sequence.json",
                "docs/validation/companion-screen-expression-demo-sequence.md",
                "docs/validation/companion-screen-expression-journeys.json",
                "docs/validation/companion-screen-expression-storyboard.json",
                "docs/validation/epaper/expression-storyboard.svg",
                "docs/companion_screen_expression_system.md",
                "app/companion_pendant/epaper/README.md",
            ],
            [
                "python .\\tools\\verify_expression_demo_sequence.py",
                "python .\\tools\\verify_expression_journeys.py",
                "python .\\tools\\render_expression_storyboard.py",
            ],
            "WBA ports can reuse the same no-hardware demo order before replacing WB55 transport with WBA target glue and real panel evidence.",
        ),
        item(
            "screen_expression_demo_panel_handoff",
            "Screen expression demo panel handoff",
            "PASS",
            "The no-hardware demo checklist is mapped onto WB55, WBA55, and WBA65 real-panel evidence sessions, with manual visual gaps explicit.",
            [
                "tools/verify_expression_demo_panel_handoff.py",
                "docs/validation/companion-screen-expression-demo-panel-handoff.json",
                "docs/validation/companion-screen-expression-demo-panel-handoff.md",
                "docs/validation/companion-screen-expression-demo-sequence.json",
                "docs/validation/companion-screen-real-ble-bench.json",
                "docs/validation/companion-screen-panel-hardware-session.json",
                "docs/validation/companion-screen-panel-hardware-acceptance-plan.json",
                "docs/companion_screen_expression_system.md",
                "app/companion_pendant/epaper/README.md",
                "docs/stm32wba_migration_rules.md",
            ],
            [
                "python .\\tools\\verify_expression_demo_panel_handoff.py",
                "python .\\tools\\verify_expression_demo_sequence.py",
                "python .\\tools\\verify_expression_real_ble_screen_bench.py",
                "python .\\tools\\verify_expression_panel_hardware_session.py",
                "python .\\tools\\verify_expression_panel_hardware_acceptance_plan.py",
            ],
            "WBA ports reuse the same demo handoff order and must keep manual_visual_required_faces explicit until target real BLE/visual evidence covers every demo face.",
        ),
        item(
            "screen_acceptance_runner",
            "Screen acceptance runner",
            "PASS",
            "The aggregate runner reads the screen acceptance index, deduplicates validation commands, preserves the deferred hardware gate, and writes per-item command status.",
            [
                "tools/run_expression_acceptance.py",
                "tools/verify_expression_acceptance_runner.py",
                "tools/render_expression_acceptance_report.py",
                "docs/validation/companion-screen-acceptance-runner.json",
                "docs/validation/companion-screen-acceptance-report.md",
                "docs/validation/companion-screen-acceptance-index.json",
                "docs/companion_screen_expression_system.md",
                "docs/bringup_steps.md",
            ],
            [
                "python .\\tools\\verify_expression_acceptance_runner.py",
                "python .\\tools\\render_expression_acceptance_report.py",
                "python .\\tools\\run_expression_acceptance.py --dry-run --skip-build --output .\\.cache\\validation\\companion-screen-acceptance-dry-run.json",
            ],
            "WBA branches can reuse the same runner to prove the portable screen suite before adding target-specific hardware evidence.",
        ),
        item(
            "screen_feature_roadmap",
            "Screen feature roadmap",
            "PASS",
            "The screen roadmap groups every detailed acceptance item into product-facing capabilities and keeps the remaining WB55 human touch/visual review explicit.",
            [
                "tools/verify_expression_feature_roadmap.py",
                "docs/validation/companion-screen-feature-roadmap.json",
                "docs/validation/companion-screen-acceptance-index.json",
                "docs/companion_screen_expression_system.md",
                "app/companion_pendant/epaper/README.md",
            ],
            [
                "python .\\tools\\verify_expression_feature_roadmap.py",
                "python .\\tools\\verify_expression_acceptance_index.py",
            ],
            "WBA work can use the same feature roadmap to see which portable capabilities must stay green before target-specific panel parity is claimed.",
        ),
        item(
            "screen_feature_checklist",
            "Screen feature checklist",
            "PASS",
            "A compact generated checklist shows the current one-by-one acceptance focus, next gate, and missing panel facts.",
            [
                "tools/render_expression_feature_checklist.py",
                "docs/validation/companion-screen-feature-checklist.json",
                "docs/validation/companion-screen-feature-checklist.md",
                "docs/validation/companion-screen-feature-roadmap.json",
                "docs/validation/companion-screen-acceptance-index.json",
                "docs/validation/companion-screen-panel-driver-readiness.json",
                "docs/companion_screen_expression_system.md",
                "app/companion_pendant/epaper/README.md",
            ],
            [
                "python .\\tools\\render_expression_feature_checklist.py",
                "python .\\tools\\verify_expression_feature_roadmap.py",
                "python .\\tools\\verify_expression_acceptance_index.py",
                "python .\\tools\\verify_expression_panel_driver_readiness.py",
            ],
            "WBA ports can use the same generated checklist to keep current focus, next gate, and target-specific missing facts visible during parity work.",
        ),
        item(
            "wba_pre_port_gate",
            "WBA pre-port gate",
            "PASS",
            "Portable screen files and the WBA pre-port contract are guarded against WB55 HAL, STM32_WPAN, CPU2/FUS/IPCC/HSEM, pins, peripheral instances, and renderer visual/layout drift.",
            [
                "docs/stm32wba_migration_rules.md",
                "docs/validation/companion-screen-wba-port-contract.json",
                "docs/validation/companion-screen-expression-visual-contract.json",
                "docs/validation/companion-screen-expression-layout-contract.json",
                "tools/verify_expression_wba_portability.py",
            ],
            [
                "python .\\tools\\verify_expression_wba_portability.py",
                "python .\\tools\\verify_expression_visual_contract.py",
                "python .\\tools\\verify_expression_layout_contract.py",
                "git diff --name-only -- third_party\\STM32CubeWB third_party\\STM32CubeWBA",
            ],
            "WBA55 is the conservative baseline; WBA65 may add resources only after preserving the machine-readable portable screen contract.",
        ),
        item(
            "wba_lse_clock_contract",
            "WBA LSE/RTC/BLE sleep clock contract",
            "PASS",
            "WBA55/WBA65 production boards default to an assembled 32.768 kHz LSE crystal for BLE sleep timing, RTC continuity, timed wake-up, and low-power behavior; any no-LSE variant requires explicit radio-clock, accuracy, and power evidence before real WBA parity can be claimed.",
            [
                "tools/verify_expression_wba_lse_clock_contract.py",
                "docs/validation/companion-screen-wba-lse-clock-contract.json",
                "docs/stm32wba_migration_rules.md",
                "docs/validation/companion-screen-wba-port-contract.json",
                "docs/validation/companion-screen-wba-real-parity-gate.json",
            ],
            [
                "python .\\tools\\verify_expression_wba_lse_clock_contract.py",
                "python .\\tools\\verify_expression_wba_portability.py",
                "python .\\tools\\verify_expression_wba_real_parity_gate.py",
            ],
            "WBA hardware parity must prove LSE startup, RTC continuity across sleep, BLE advertising/connection through sleep, and timed wake-up on the selected WBA55/WBA65 board, or record an explicit no-LSE radio-clock/power exception.",
        ),
        item(
            "wba_cube_dependency_preflight",
            "WBA CubeWBA dependency preflight",
            "PASS",
            "The WBA pre-port dependency fixture records that STM32CubeWB is present, STM32CubeWBA is not yet present in this workspace, and WBA parity must stay behind DRAFT_PRE_PORT until a separate CubeWBA project and build wrapper exist.",
            [
                "tools/verify_expression_wba_cube_dependency_preflight.py",
                "docs/validation/companion-screen-wba-cube-dependency-preflight.json",
                "docs/validation/companion-workspace-submodule-policy.json",
                "docs/validation/companion-screen-wba-port-contract.json",
                "docs/validation/companion-screen-wba55-port-scaffold.json",
                "docs/stm32wba_migration_rules.md",
                "docs/companion_screen_expression_system.md",
                "app/companion_pendant/epaper/README.md",
            ],
            [
                "python .\\tools\\verify_expression_wba_cube_dependency_preflight.py",
                "python .\\tools\\verify_workspace_submodule_policy.py",
                "python .\\tools\\verify_expression_wba_portability.py",
                "python .\\tools\\init_expression_wba_port_scaffold.py --self-test",
                "git diff --name-only -- third_party\\STM32CubeWB third_party\\STM32CubeWBA",
            ],
            "WBA55/WBA65 migration now has an explicit dependency gate before CubeWBA IOC/project, build wrapper, BLE service registration, scheduler hook, or panel evidence can be treated as parity work.",
        ),
        item(
            "wba_port_scaffold",
            "WBA port scaffold",
            "PASS",
            "The WBA55 pre-port scaffold lists the first CubeWBA dependency preflight, CubeWBA project, build wrapper, WBA adapters, WBA panel target/GATT/scheduler/external-assets scaffolds, visual/layout invariants, real BLE bench, and panel evidence record required before parity can be claimed.",
            [
                "tools/init_expression_wba_port_scaffold.py",
                "tools/verify_expression_wba_cube_dependency_preflight.py",
                "tools/verify_expression_panel_target_stm32wba.py",
                "tools/verify_expression_screen_scheduler_stm32wba.py",
                "tools/verify_expression_screen_gatt_stm32wba.py",
                "tools/verify_expression_screen_assets_stm32wba.py",
                "app/companion_pendant/epaper/panel_target_stm32wba.h",
                "app/companion_pendant/epaper/panel_target_stm32wba.c",
                "app/companion_pendant/epaper/screen_scheduler_stm32wba.h",
                "app/companion_pendant/epaper/screen_scheduler_stm32wba.c",
                "app/companion_pendant/epaper/screen_gatt_stm32wba.h",
                "app/companion_pendant/epaper/screen_gatt_stm32wba.c",
                "app/companion_pendant/epaper/screen_assets_stm32wba.h",
                "app/companion_pendant/epaper/screen_assets_stm32wba.c",
                "docs/validation/companion-screen-wba55-port-scaffold.json",
                "docs/validation/companion-screen-wba-port-contract.json",
                "docs/validation/companion-screen-wba-cube-dependency-preflight.json",
                "docs/validation/companion-screen-panel-target-stm32wba.json",
                "docs/validation/companion-screen-scheduler-stm32wba.json",
                "docs/validation/companion-screen-gatt-stm32wba.json",
                "docs/validation/companion-screen-assets-stm32wba.json",
                "docs/validation/companion-screen-expression-visual-contract.json",
                "docs/validation/companion-screen-expression-layout-contract.json",
                "docs/stm32wba_migration_rules.md",
                "docs/companion_screen_expression_system.md",
            ],
            [
                "python .\\tools\\init_expression_wba_port_scaffold.py",
                "python .\\tools\\init_expression_wba_port_scaffold.py --self-test",
                "python .\\tools\\verify_expression_wba_cube_dependency_preflight.py",
                "python .\\tools\\verify_expression_panel_target_stm32wba.py",
                "python .\\tools\\verify_expression_screen_scheduler_stm32wba.py",
                "python .\\tools\\verify_expression_screen_gatt_stm32wba.py",
                "python .\\tools\\verify_expression_screen_assets_stm32wba.py",
                "python .\\tools\\verify_expression_wba_portability.py",
                "python .\\tools\\verify_expression_visual_contract.py",
                "python .\\tools\\verify_expression_layout_contract.py",
            ],
            "Future WBA branches can start from a target-specific checklist while keeping WBA55 as the safe baseline and WBA65 as an explicitly expanded target.",
        ),
        item(
            "wba_panel_target_adapter_scaffold",
            "WBA panel target adapter scaffold",
            "PASS",
            "The WBA55/WBA65 target-named panel adapter scaffold exists as dry-run code outside the WB55 build and without WB55 SPI2 pin facts.",
            [
                "app/companion_pendant/epaper/panel_target_stm32wba.h",
                "app/companion_pendant/epaper/panel_target_stm32wba.c",
                "tools/verify_expression_panel_target_stm32wba.py",
                "docs/validation/companion-screen-panel-target-stm32wba.json",
                "docs/validation/companion-screen-wba-port-contract.json",
                "docs/validation/companion-screen-wba55-port-scaffold.json",
                "docs/companion_screen_expression_system.md",
                "docs/stm32wba_migration_rules.md",
                "app/companion_pendant/epaper/README.md",
            ],
            [
                "python .\\tools\\verify_expression_panel_target_stm32wba.py",
                "python .\\tools\\verify_expression_wba_portability.py",
                "python .\\tools\\init_expression_wba_port_scaffold.py --self-test",
                "python .\\tools\\verify_expression_panel_gate.py",
                "pwsh -NoProfile -File .\\tools\\build_nucleo_bringup.ps1",
            ],
            "WBA55/WBA65 can now start from a real target-named file boundary while real transport remains behind target evidence and the WB55 build stays unchanged.",
        ),
        item(
            "wba_refresh_intent_contract",
            "WBA refresh intent contract",
            "PASS",
            "The WBA55/WBA65 pre-port contract keeps refresh_mode and 16-bit dirty rectangles in the portable display request, then maps PARTIAL_INTERACTIVE, MAINTENANCE, and FULL to concrete controller waveforms only inside panel_target_stm32wba.*.",
            [
                "app/companion_pendant/epaper/display_queue.h",
                "app/companion_pendant/epaper/panel_adapter.h",
                "app/companion_pendant/epaper/panel_target_stm32wba.h",
                "app/companion_pendant/epaper/panel_target_stm32wba.c",
                "tools/verify_expression_panel_target_stm32wba.py",
                "tools/verify_expression_wba_portability.py",
                "docs/validation/companion-screen-panel-target-stm32wba.json",
                "docs/validation/companion-screen-wba-port-contract.json",
                "docs/companion_screen_project_plan.md",
                "docs/stm32wba_migration_rules.md",
            ],
            [
                "python .\\tools\\verify_expression_panel_target_stm32wba.py",
                "python .\\tools\\verify_expression_wba_portability.py",
                "python .\\tools\\verify_screen_refresh_feel_contract.py",
            ],
            "WBA55/WBA65 ports may tune waveform/profile mapping per controller, but must not rewrite portable queue, dirty-rect, scene/player, menu touch, or pet-expression logic.",
        ),
        item(
            "wba_display_scheduler_scaffold",
            "WBA display scheduler scaffold",
            "PASS",
            "The WBA55/WBA65 display scheduler/timer scaffold exists as callback-only code outside the WB55 build and without WB55 UTIL_SEQ/HW_TS details.",
            [
                "app/companion_pendant/epaper/screen_scheduler_stm32wba.h",
                "app/companion_pendant/epaper/screen_scheduler_stm32wba.c",
                "tools/verify_expression_screen_scheduler_stm32wba.py",
                "docs/validation/companion-screen-scheduler-stm32wba.json",
                "docs/validation/companion-screen-display-drain-contract.json",
                "docs/validation/companion-screen-wba-port-contract.json",
                "docs/validation/companion-screen-wba55-port-scaffold.json",
                "docs/companion_screen_expression_system.md",
                "docs/stm32wba_migration_rules.md",
                "app/companion_pendant/epaper/README.md",
            ],
            [
                "python .\\tools\\verify_expression_screen_scheduler_stm32wba.py",
                "python .\\tools\\verify_expression_display_drain.py",
                "python .\\tools\\verify_expression_wba_portability.py",
                "python .\\tools\\init_expression_wba_port_scaffold.py --self-test",
                "pwsh -NoProfile -File .\\tools\\build_nucleo_bringup.ps1",
            ],
            "WBA55/WBA65 can wire CubeWBA scheduler/timer APIs behind this callback boundary while preserving the display drain and transient expression recovery contracts.",
        ),
        item(
            "wba_screen_gatt_scaffold",
            "WBA screen GATT scaffold",
            "PASS",
            "The WBA55/WBA65 screen GATT scaffold exists as target-named code outside the WB55 build and preserves CardWriteV1, CardStatusV1, SettingsV1, settings_sleepy_screen_status, and screen_expression_status before CubeWBA service registration is added.",
            [
                "app/companion_pendant/epaper/screen_gatt_stm32wba.h",
                "app/companion_pendant/epaper/screen_gatt_stm32wba.c",
                "tools/verify_expression_screen_gatt_stm32wba.py",
                "docs/validation/companion-screen-gatt-stm32wba.json",
                "docs/ble_gatt_contract.md",
                "docs/validation/companion-screen-real-ble-bench.json",
                "docs/validation/companion-screen-expression-host-status-sequence.json",
                "docs/validation/companion-screen-wba-port-contract.json",
                "docs/validation/companion-screen-wba55-port-scaffold.json",
                "docs/companion_screen_expression_system.md",
                "docs/stm32wba_migration_rules.md",
                "app/companion_pendant/epaper/README.md",
            ],
            [
                "python .\\tools\\verify_expression_screen_gatt_stm32wba.py",
                "python .\\tools\\verify_companion_gatt_static.py",
                "python .\\tools\\verify_expression_real_ble_screen_bench.py",
                "python .\\tools\\verify_expression_host_status_sequence.py",
                "python .\\tools\\verify_expression_wba_portability.py",
                "python .\\tools\\init_expression_wba_port_scaffold.py --self-test",
                "pwsh -NoProfile -File .\\tools\\build_nucleo_bringup.ps1",
            ],
            "WBA55/WBA65 can wire CubeWBA BLE service registration behind this boundary while keeping WB55 STM32_WPAN and companion_gatt_stm32wb details out of the WBA scaffold.",
        ),
        item(
            "wba_screen_assets_scaffold",
            "WBA screen-assets scaffold",
            "PASS",
            "The WBA55/WBA65 screen-assets scaffold binds a target-owned logical external-NOR reader to the portable asset store, rejects out-of-range partition reads, and keeps physical storage facts and activation out of the WB55 build and portable resource code.",
            [
                "app/companion_pendant/epaper/screen_assets_stm32wba.h",
                "app/companion_pendant/epaper/screen_assets_stm32wba.c",
                "tools/verify_expression_screen_assets_stm32wba.py",
                "docs/validation/companion-screen-assets-stm32wba.json",
                "docs/validation/companion-screen-wba-port-contract.json",
                "docs/validation/companion-screen-wba55-port-scaffold.json",
                "docs/companion_resource_memory_policy.md",
                "docs/companion_screen_expression_system.md",
                "docs/stm32wba_migration_rules.md",
                "app/companion_pendant/epaper/README.md",
            ],
            [
                "python .\\tools\\verify_expression_screen_assets_stm32wba.py",
                "python .\\tools\\verify_screen_resource_architecture.py",
                "python .\\tools\\verify_expression_wba_portability.py",
                "python .\\tools\\init_expression_wba_port_scaffold.py --self-test",
                "pwsh -NoProfile -File .\\tools\\build_nucleo_bringup.ps1",
            ],
            "WBA55/WBA65 can choose a target-specific storage peripheral and inactive-pack strategy without changing the portable CEMP/resource reader contract or consuming normal UI assets from constrained internal flash.",
        ),
        item(
            "wba_pet_behavior_user_data_scaffold",
            "WBA pet behavior user-data scaffold",
            "PASS",
            "The WBA55/WBA65 pet-behavior user-data scaffold persists comp_pet_behavior_memory_t through callback-only logical slots with CRC records, sequence selection, low-frequency commit gating, and explicit privacy erase, and it passes Cortex-M33 ARM GCC object compilation while keeping physical storage facts out of portable pet behavior.",
            [
                "app/companion_pendant/epaper/pet_behavior_user_data_stm32wba.h",
                "app/companion_pendant/epaper/pet_behavior_user_data_stm32wba.c",
                "tools/verify_pet_behavior_user_data_stm32wba.py",
                "docs/validation/companion-screen-pet-behavior-user-data-stm32wba.json",
                "docs/validation/companion-screen-wba-port-contract.json",
                "docs/companion_resource_memory_policy.md",
                "docs/companion_screen_expression_system.md",
                "docs/stm32wba_migration_rules.md",
                "app/companion_pendant/epaper/pet_behavior.h",
            ],
            [
                "python .\\tools\\verify_pet_behavior_user_data_stm32wba.py",
                "python .\\tools\\verify_expression_wba_portability.py",
                "python .\\tools\\verify_expression_wba_real_parity_gate.py",
            ],
            "WBA55/WBA65 can choose the real user-data partition, storage peripheral, erase geometry, and wear policy later; this scaffold preserves the portable behavior memory and OTA/privacy boundaries without claiming real WBA storage parity.",
        ),
        item(
            "target_capability_profile",
            "Target capability profile",
            "PASS",
            "WB55, WBA55, and WBA65 screen capability boundaries are captured so WBA55 remains the shared safe baseline and WBA65 expansion requires explicit capability flags.",
            [
                "tools/verify_expression_target_capabilities.py",
                "docs/validation/companion-screen-target-capabilities.json",
                "docs/validation/companion-screen-wba-port-contract.json",
                "docs/validation/companion-screen-wba55-port-scaffold.json",
                "app/companion_pendant/epaper/display_queue.h",
                "app/companion_pendant/epaper/panel_adapter.h",
                "docs/stm32wba_migration_rules.md",
                "docs/companion_screen_expression_system.md",
                "app/companion_pendant/epaper/README.md",
            ],
            [
                "python .\\tools\\verify_expression_target_capabilities.py",
                "python .\\tools\\verify_expression_wba_portability.py",
                "python .\\tools\\init_expression_wba_port_scaffold.py --self-test",
                "python .\\tools\\verify_display_queue_static.py",
                "python .\\tools\\verify_expression_display_drain.py",
                "git diff --name-only -- third_party\\STM32CubeWB third_party\\STM32CubeWBA",
            ],
            "WBA55 is the conservative baseline for shared queue/payload/protocol limits; WBA65 may add target-specific resources only behind capability flags while preserving WBA55-safe behavior.",
        ),
        item(
            "devboard_ioc_screen_preflight",
            "Devboard IOC screen preflight",
            "PASS",
            "The user-provided STM32.ioc is captured in the WB55 devboard IOC, preserving SPI2/I2C3/SAI1 board facts while keeping the product IOC separate for later target work.",
            [
                "tools/verify_devboard_ioc_import.py",
                "docs/validation/companion-devboard-ioc-import.json",
                "cubeide/Companion_Nucleo_WB55RG/Companion_Nucleo_WB55RG.ioc",
                "Companion_Pendant.ioc",
                "cubeide/Companion_Nucleo_WB55RG_Bringup/README.md",
                "docs/bringup_steps.md",
                "docs/codex_development_workflow.md",
                "docs/companion_screen_expression_system.md",
                "docs/stm32wba_migration_rules.md",
            ],
            [
                "python .\\tools\\verify_devboard_ioc_import.py",
                "python .\\tools\\verify_expression_target_capabilities.py",
                "python .\\tools\\verify_expression_panel_gate.py",
                "pwsh -NoProfile -File .\\tools\\build_nucleo_bringup.ps1",
            ],
            "WBA ports must create a separate CubeWBA IOC/project and keep board pins/peripheral instances in target files instead of copying WB55 devboard pin facts into portable screen code.",
        ),
        item(
            "panel_wiring_preflight",
            "Panel wiring preflight",
            "PASS",
            "The WB55 devboard IOC exposes the SPI2 e-paper transport candidate at PA9/PC1/PC2/PA6 while controller and DC/RST/BUSY facts remain under the real-panel hardware gate.",
            [
                "tools/verify_expression_panel_wiring_preflight.py",
                "docs/validation/companion-screen-panel-wiring-preflight.json",
                "docs/validation/companion-devboard-ioc-import.json",
                "docs/validation/companion-screen-panel-hardware-gate.json",
                "docs/validation/companion-screen-panel-hardware-acceptance-plan.json",
                "cubeide/Companion_Nucleo_WB55RG/Companion_Nucleo_WB55RG.ioc",
                "cubeide/Companion_Nucleo_WB55RG_Bringup/README.md",
                "docs/companion_screen_expression_system.md",
                "docs/stm32wba_migration_rules.md",
                "app/companion_pendant/epaper/README.md",
            ],
            [
                "python .\\tools\\verify_expression_panel_wiring_preflight.py",
                "python .\\tools\\verify_devboard_ioc_import.py",
                "python .\\tools\\verify_expression_panel_gate.py",
                "python .\\tools\\verify_expression_panel_hardware_acceptance_plan.py",
                "pwsh -NoProfile -File .\\tools\\build_nucleo_bringup.ps1",
            ],
            "WBA55/WBA65 must use a target-specific CubeWBA IOC/project and *_stm32wba.* panel adapter; WB55 SPI2 pins are devboard facts, not portable constants.",
        ),
        item(
            "panel_evidence_scaffold_wiring_prefill",
            "Panel evidence scaffold wiring prefill",
            "PASS",
            "The WB55 real-panel evidence scaffold imports the verified SPI2 wiring preflight while leaving controller, DC/RST/BUSY, timing, visual, BLE, diagnostics, and adapter facts as TODOs.",
            [
                "tools/init_expression_panel_evidence_record.py",
                "tools/verify_expression_panel_evidence_record.py",
                "tools/verify_expression_panel_wiring_preflight.py",
                "docs/validation/companion-screen-panel-evidence-record-scaffold.json",
                "docs/validation/companion-screen-panel-evidence-record-validator.json",
                "docs/validation/companion-screen-panel-wiring-preflight.json",
                "docs/validation/companion-screen-panel-evidence-template.json",
                "docs/companion_screen_expression_system.md",
                "docs/bringup_steps.md",
                "docs/stm32wba_migration_rules.md",
                "app/companion_pendant/epaper/README.md",
            ],
            [
                "python .\\tools\\init_expression_panel_evidence_record.py",
                "python .\\tools\\verify_expression_panel_evidence_record.py --self-test",
                "python .\\tools\\verify_expression_panel_wiring_preflight.py",
                "python .\\tools\\verify_epaper_assets.py",
            ],
            "WBA55/WBA65 scaffolds keep transport pins target-specific; WB55 SPI2 prefill is evidence convenience only, not a portable WBA pin assumption.",
        ),
        item(
            "panel_hardware_session_scaffold",
            "Panel hardware session scaffold",
            "PASS",
            "The WB55/WBA real-panel hardware session layout is fixed as target-specific roots, required artifacts, hardware-lock commands, diagnostics, visual evidence, and record validation.",
            [
                "tools/verify_expression_panel_hardware_session.py",
                "docs/validation/companion-screen-panel-hardware-session.json",
                "docs/validation/companion-screen-panel-hardware-acceptance-plan.json",
                "docs/validation/companion-screen-panel-hardware-gate.json",
                "docs/validation/companion-screen-panel-evidence-record-scaffold.json",
                "docs/validation/companion-screen-panel-evidence-record-validator.json",
                "docs/validation/companion-screen-panel-wiring-preflight.json",
                "docs/companion_screen_expression_system.md",
                "docs/bringup_steps.md",
                "docs/stm32wba_migration_rules.md",
                "app/companion_pendant/epaper/README.md",
            ],
            [
                "python .\\tools\\verify_expression_panel_hardware_session.py",
                "python .\\tools\\verify_expression_panel_hardware_acceptance_plan.py",
                "python .\\tools\\verify_expression_panel_hardware_facts.py --self-test",
                "python .\\tools\\verify_expression_panel_evidence_record.py --self-test",
                "python .\\tools\\verify_expression_wba_portability.py",
            ],
            "WBA55/WBA65 sessions reuse the same evidence structure with target-specific roots and *_stm32wba.* adapters, but must not inherit WB55 SPI2 pin facts.",
        ),
        item(
            "panel_session_directory_preflight",
            "Panel session directory preflight",
            "PASS",
            "A concrete generated real-panel session directory can be checked before hardware evidence is filled, its DRAFT_UNFILLED record is still rejected by the final real-panel validator, and any local operator packet must match the current renderer with quoted hardware locks and partial-failure evidence.",
            [
                "tools/verify_expression_panel_session_directory.py",
                "tools/init_expression_panel_evidence_record.py",
                "tools/render_expression_panel_bringup_packet.py",
                "tools/verify_expression_panel_hardware_facts.py",
                "tools/verify_expression_panel_evidence_record.py",
                "docs/validation/companion-screen-panel-session-directory-preflight.json",
                "docs/validation/companion-screen-panel-hardware-session.json",
                "docs/validation/companion-screen-panel-hardware-gate.json",
                "docs/companion_screen_expression_system.md",
                "docs/bringup_steps.md",
                "app/companion_pendant/epaper/README.md",
            ],
            [
                "python .\\tools\\verify_expression_panel_session_directory.py --self-test",
                "python .\\tools\\render_expression_panel_bringup_packet.py --self-test",
                "python .\\tools\\verify_expression_panel_hardware_session.py",
                "python .\\tools\\verify_expression_panel_hardware_facts.py --self-test",
                "python .\\tools\\verify_expression_panel_evidence_record.py --self-test",
            ],
            "WBA55/WBA65 concrete sessions use the same directory preflight with target-specific roots, target-specific operator packets, partial-failure evidence, and no WB55 SPI2 pin facts in WBA records.",
        ),
        item(
            "panel_hardware_facts_intake",
            "Panel hardware facts intake",
            "PASS",
            "Controller, DC/RST/BUSY, power, voltage, and driver timing facts have a target-specific intake file that can reach READY_FOR_DRIVER_FACTS without claiming real refresh.",
            [
                "tools/verify_expression_panel_hardware_facts.py",
                "docs/validation/companion-screen-panel-hardware-facts-intake.json",
                "docs/validation/companion-screen-panel-hardware-gate.json",
                "docs/validation/companion-screen-panel-evidence-template.json",
                "docs/validation/companion-screen-panel-session-directory-preflight.json",
                "docs/companion_screen_expression_system.md",
                "docs/bringup_steps.md",
                "app/companion_pendant/epaper/README.md",
            ],
            [
                "python .\\tools\\verify_expression_panel_hardware_facts.py",
                "python .\\tools\\verify_expression_panel_hardware_facts.py --self-test",
                "python .\\tools\\verify_expression_panel_gate.py",
            ],
            "WBA55/WBA65 use the same intake schema with target-specific pin maps; READY_FOR_DRIVER_FACTS still requires separate WBA target adapter evidence before parity is claimed.",
        ),
        item(
            "panel_hardware_facts_worksheet",
            "Panel hardware facts worksheet",
            "PASS",
            "A generated JSON/Markdown worksheet turns missing panel readiness fields into a fillable operator table before driver work starts.",
            [
                "tools/render_expression_panel_facts_worksheet.py",
                "docs/validation/companion-screen-panel-facts-worksheet.json",
                "docs/validation/companion-screen-panel-facts-worksheet.md",
                "docs/validation/companion-screen-panel-driver-readiness.json",
                "docs/validation/companion-screen-panel-hardware-facts-intake.json",
                "docs/companion_screen_expression_system.md",
                "docs/bringup_steps.md",
                "app/companion_pendant/epaper/README.md",
            ],
            [
                "python .\\tools\\render_expression_panel_facts_worksheet.py",
                "python .\\tools\\render_expression_panel_facts_worksheet.py --self-test",
                "python .\\tools\\verify_expression_panel_driver_readiness.py",
                "python .\\tools\\verify_expression_panel_hardware_facts.py --self-test",
            ],
            "WBA55/WBA65 can render the same worksheet from target-specific facts so WBA driver work starts from explicit missing fields rather than copied WB55 assumptions.",
        ),
        item(
            "panel_bringup_operator_packet",
            "Panel bring-up operator packet",
            "PASS",
            "A generated JSON/Markdown packet combines the WB55 session root, missing facts, readiness gate, commands, and evidence artifacts for the next real-panel bring-up.",
            [
                "tools/render_expression_panel_bringup_packet.py",
                "docs/validation/companion-screen-panel-bringup-operator-packet.json",
                "docs/validation/companion-screen-panel-bringup-operator-packet.md",
                "docs/validation/companion-screen-panel-facts-worksheet.json",
                "docs/validation/companion-screen-panel-driver-readiness.json",
                "docs/validation/companion-screen-panel-hardware-session.json",
                "docs/validation/companion-screen-panel-hardware-acceptance-plan.json",
                "docs/companion_screen_expression_system.md",
                "docs/bringup_steps.md",
                "docs/stm32wba_migration_rules.md",
                "app/companion_pendant/epaper/README.md",
            ],
            [
                "python .\\tools\\render_expression_panel_bringup_packet.py",
                "python .\\tools\\render_expression_panel_bringup_packet.py --self-test",
                "python .\\tools\\render_expression_panel_facts_worksheet.py --self-test",
                "python .\\tools\\verify_expression_panel_driver_readiness.py --self-test",
                "python .\\tools\\verify_expression_panel_hardware_session.py",
            ],
            "WBA55/WBA65 must generate separate operator packets from their own session facts instead of reusing WB55 SPI/DC/RST/BUSY evidence.",
        ),
        item(
            "panel_driver_readiness_report",
            "Panel driver readiness report",
            "PASS",
            "A target facts file reports BLOCKED_ON_HARDWARE_FACTS until controller, DC/RST/BUSY, power, voltage, timing, and refresh sequence facts are ready for driver implementation.",
            [
                "tools/verify_expression_panel_driver_readiness.py",
                "tools/verify_expression_panel_hardware_facts.py",
                "docs/validation/companion-screen-panel-driver-readiness.json",
                "docs/validation/companion-screen-panel-hardware-facts-intake.json",
                "docs/validation/companion-screen-panel-hardware-gate.json",
                "docs/validation/companion-screen-panel-session-directory-preflight.json",
                "docs/companion_screen_expression_system.md",
                "docs/bringup_steps.md",
                "docs/stm32wba_migration_rules.md",
                "app/companion_pendant/epaper/README.md",
            ],
            [
                "python .\\tools\\verify_expression_panel_driver_readiness.py",
                "python .\\tools\\verify_expression_panel_driver_readiness.py --self-test",
                "python .\\tools\\verify_expression_panel_hardware_facts.py --self-test",
                "python .\\tools\\verify_expression_panel_gate.py",
            ],
            "WBA55/WBA65 driver work must reach READY_FOR_DRIVER_IMPLEMENTATION from target-specific facts rather than inheriting WB55 SPI2 pin evidence.",
        ),
        item(
            "panel_hardware_facts_bridge",
            "Panel hardware facts bridge",
            "PASS",
            "READY_FOR_DRIVER_FACTS can be imported into panel-evidence-record.json while preserving DRAFT_UNFILLED status and final-validator rejection until BLE, diagnostics, visual, and portability evidence exist.",
            [
                "tools/apply_expression_panel_hardware_facts.py",
                "tools/verify_expression_panel_hardware_facts.py",
                "tools/verify_expression_panel_evidence_record.py",
                "docs/validation/companion-screen-panel-hardware-facts-bridge.json",
                "docs/validation/companion-screen-panel-hardware-facts-intake.json",
                "docs/validation/companion-screen-panel-evidence-record-validator.json",
                "docs/validation/companion-screen-panel-hardware-gate.json",
                "docs/companion_screen_expression_system.md",
                "docs/bringup_steps.md",
                "app/companion_pendant/epaper/README.md",
            ],
            [
                "python .\\tools\\apply_expression_panel_hardware_facts.py --self-test",
                "python .\\tools\\verify_expression_panel_hardware_facts.py --self-test",
                "python .\\tools\\verify_expression_panel_evidence_record.py --self-test",
                "python .\\tools\\verify_expression_panel_gate.py",
            ],
            "WBA55/WBA65 use the same bridge only after target-specific READY_FOR_DRIVER_FACTS are filled, and the bridge still cannot claim WBA panel parity.",
        ),
        item(
            "panel_target_ops_boundary",
            "Panel adapter target-ops boundary",
            "PASS",
            "The portable panel adapter dispatches through a target-owned refresh callback so real WB55/WBA transport can be added without moving board code into portable screen files.",
            [
                "app/companion_pendant/epaper/panel_adapter.h",
                "app/companion_pendant/epaper/panel_adapter.c",
                "docs/validation/companion-screen-panel-adapter-boundary.json",
                "docs/companion_screen_expression_system.md",
                "docs/stm32wba_migration_rules.md",
                "tools/verify_expression_panel_adapter_boundary.py",
            ],
            [
                "python .\\tools\\verify_expression_panel_adapter_boundary.py",
                "python .\\tools\\verify_display_queue_static.py",
                "python .\\tools\\verify_expression_wba_portability.py",
                "pwsh -NoProfile -File .\\tools\\build_nucleo_bringup.ps1",
            ],
            "WBA55/WBA65 should add target-specific refresh transport through the same callback field while leaving ExpressionV1, display_queue, and CardStatusV1 unchanged.",
        ),
        item(
            "wb55_panel_target_adapter_scaffold",
            "WB55 panel target adapter scaffold",
            "PASS",
            "WB55 now initializes the portable panel adapter through a target-named panel_target_stm32wb scaffold, which still delegates to dry-run until real controller, pin, and timing evidence exists.",
            [
                "app/companion_pendant/epaper/panel_target_stm32wb.h",
                "app/companion_pendant/epaper/panel_target_stm32wb.c",
                "app/companion_pendant/epaper/panel_adapter.h",
                "app/companion_pendant/epaper/panel_adapter.c",
                "cubeide/Companion_Nucleo_WB55RG_Bringup/Core/Src/app_ble.c",
                "cubeide/Companion_Nucleo_WB55RG_Bringup/Makefile",
                "docs/validation/companion-screen-panel-target-stm32wb.json",
                "docs/validation/companion-screen-panel-hardware-gate.json",
                "docs/companion_screen_expression_system.md",
                "docs/stm32wba_migration_rules.md",
                "tools/verify_expression_panel_target_stm32wb.py",
            ],
            [
                "python .\\tools\\verify_expression_panel_target_stm32wb.py",
                "python .\\tools\\verify_expression_panel_gate.py",
                "python .\\tools\\verify_expression_panel_adapter_boundary.py",
                "python .\\tools\\verify_display_queue_static.py",
                "python .\\tools\\verify_expression_wba_portability.py",
                "pwsh -NoProfile -File .\\tools\\build_nucleo_bringup.ps1",
            ],
            "WBA55/WBA65 should add a separate *_stm32wba.* target adapter with the same dry-run-to-real-evidence promotion path instead of changing portable panel files.",
        ),
        item(
            "panel_adapter_behavior_matrix",
            "Panel adapter behavior matrix",
            "PASS",
            "Dry-run, controller-unknown, missing-callback, callback OK/BUSY/deferred/error, and request identity behavior are fixed as a no-hardware contract for future panel drivers.",
            [
                "app/companion_pendant/epaper/panel_adapter.h",
                "app/companion_pendant/epaper/panel_adapter.c",
                "docs/validation/companion-screen-panel-adapter-behavior.json",
                "docs/validation/companion-screen-panel-adapter-boundary.json",
                "docs/companion_screen_expression_system.md",
                "docs/stm32wba_migration_rules.md",
                "tools/verify_expression_panel_adapter_behavior.py",
            ],
            [
                "python .\\tools\\verify_expression_panel_adapter_behavior.py",
                "python .\\tools\\verify_expression_panel_adapter_boundary.py",
                "python .\\tools\\verify_expression_status_observability.py",
                "python .\\tools\\verify_expression_wba_portability.py",
                "pwsh -NoProfile -File .\\tools\\build_nucleo_bringup.ps1",
            ],
            "WBA panel drivers must preserve the same callback result, CardStatusV1 render-state/error, and request identity behavior while replacing only transport.",
        ),
        item(
            "panel_adapter_telemetry_snapshot",
            "Panel adapter telemetry snapshot",
            "PASS",
            "The portable panel adapter exposes a stats snapshot for attempts, rendered/deferred/error counts, configuration state, and last result without adding target dependencies.",
            [
                "app/companion_pendant/epaper/panel_adapter.h",
                "app/companion_pendant/epaper/panel_adapter.c",
                "cubeide/Companion_Nucleo_WB55RG_Bringup/Core/Src/app_ble.c",
                "docs/validation/companion-screen-panel-adapter-telemetry.json",
                "docs/companion_screen_expression_system.md",
                "docs/stm32wba_migration_rules.md",
                "tools/verify_expression_panel_adapter_telemetry.py",
            ],
            [
                "python .\\tools\\verify_expression_panel_adapter_telemetry.py",
                "python .\\tools\\verify_expression_panel_adapter_behavior.py",
                "python .\\tools\\verify_expression_panel_adapter_boundary.py",
                "python .\\tools\\verify_expression_status_observability.py",
                "python .\\tools\\verify_expression_wba_portability.py",
                "pwsh -NoProfile -File .\\tools\\build_nucleo_bringup.ps1",
            ],
            "WBA panel drivers should preserve the same panel adapter stats snapshot so real-panel attempts, deferrals, busy responses, and errors can be diagnosed without changing CardStatusV1.",
        ),
        item(
            "screen_runtime_snapshot",
            "Screen runtime snapshot",
            "PASS",
            "The portable screen runtime aggregates expression state, display queue, and panel adapter telemetry snapshots so WB55 and future WBA display tasks observe the same runtime contract.",
            [
                "app/companion_pendant/epaper/screen_runtime.h",
                "app/companion_pendant/epaper/screen_runtime.c",
                "cubeide/Companion_Nucleo_WB55RG_Bringup/Core/Src/app_ble.c",
                "cubeide/Companion_Nucleo_WB55RG_Bringup/Makefile",
                "docs/validation/companion-screen-runtime-snapshot.json",
                "docs/companion_screen_expression_system.md",
                "docs/stm32wba_migration_rules.md",
                "app/companion_pendant/epaper/README.md",
                "tools/verify_expression_screen_runtime_snapshot.py",
            ],
            [
                "python .\\tools\\verify_expression_screen_runtime_snapshot.py",
                "python .\\tools\\verify_expression_state_telemetry.py",
                "python .\\tools\\verify_display_queue_telemetry.py",
                "python .\\tools\\verify_expression_panel_adapter_telemetry.py",
                "python .\\tools\\verify_display_queue_static.py",
                "python .\\tools\\verify_expression_wba_portability.py",
                "pwsh -NoProfile -File .\\tools\\build_nucleo_bringup.ps1",
            ],
            "WBA display tasks should collect runtime status through the same aggregate snapshot instead of reading private expression, queue, or panel fields directly.",
        ),
        item(
            "screen_runtime_diagnostics",
            "Screen runtime diagnostics",
            "PASS",
            "WB55 records an e_paper.runtime_snapshot diagnostic event from the aggregate screen runtime snapshot without changing CardStatusV1.",
            [
                "app/companion_pendant/diag_log/diag_log_events.h",
                "cubeide/Companion_Nucleo_WB55RG_Bringup/Core/Src/app_ble.c",
                "app/companion_pendant/epaper/screen_runtime.h",
                "app/companion_pendant/epaper/screen_runtime.c",
                "docs/validation/companion-screen-runtime-diagnostics.json",
                "docs/companion_screen_expression_system.md",
                "docs/stm32wba_migration_rules.md",
                "app/companion_pendant/epaper/README.md",
                "docs/ble_gatt_contract.md",
                "tools/verify_expression_screen_runtime_diagnostics.py",
            ],
            [
                "python .\\tools\\verify_expression_screen_runtime_diagnostics.py",
                "python .\\tools\\verify_expression_screen_runtime_snapshot.py",
                "python .\\tools\\verify_expression_status_observability.py",
                "python .\\tools\\verify_display_queue_static.py",
                "python .\\tools\\verify_expression_wba_portability.py",
                "pwsh -NoProfile -File .\\tools\\build_nucleo_bringup.ps1",
            ],
            "WBA display tasks must preserve the e_paper.runtime_snapshot event id, payload packing, and warning rule while replacing only scheduler/BLE/panel glue.",
        ),
        item(
            "screen_runtime_diagnostic_decode",
            "Screen runtime diagnostic decode",
            "PASS",
            "The host diagnostic decoder expands e_paper.runtime_snapshot packed args into expression, display-queue, and panel decoded_args fields for bring-up logs.",
            [
                "tools/decode_diag_log.py",
                "tools/verify_expression_screen_runtime_diagnostic_decode.py",
                "docs/validation/companion-screen-runtime-diagnostic-decode.json",
                "docs/validation/companion-screen-runtime-diagnostics.json",
                "app/companion_pendant/diag_log/diag_log_events.h",
                "docs/companion_screen_expression_system.md",
                "docs/stm32wba_migration_rules.md",
                "app/companion_pendant/epaper/README.md",
            ],
            [
                "python .\\tools\\verify_expression_screen_runtime_diagnostic_decode.py",
                "python .\\tools\\verify_expression_screen_runtime_diagnostics.py",
                "python .\\tools\\decode_diag_log.py --self-test",
                "python .\\tools\\verify_expression_wba_portability.py",
            ],
            "WBA bring-up logs should reuse the same decoded_args schema for e_paper.runtime_snapshot instead of inventing target-specific diagnostic parsing.",
        ),
        item(
            "screen_runtime_diagnostics_bundle",
            "Screen runtime diagnostics bundle",
            "PASS",
            "The no-hardware diagnostics bundle fixture includes e_paper.runtime_snapshot in the bounded tail with decoded_args and epaper runtime summary fields.",
            [
                "tools/collect_companion_diagnostics.ps1",
                "tools/verify_companion_diagnostics_static.py",
                "tools/decode_diag_log.py",
                "docs/validation/companion-diagnostics-fixture/summary.json",
                "docs/validation/companion-diagnostics-fixture/summary.md",
                "docs/validation/companion-diagnostics-fixture/diag_tail_raw.jsonl",
                "docs/validation/companion-diagnostics-fixture/diag_tail_decoded.json",
                "docs/validation/companion-screen-runtime-diagnostic-decode.json",
                "docs/companion_screen_expression_system.md",
                "docs/stm32wba_migration_rules.md",
                "app/companion_pendant/epaper/README.md",
            ],
            [
                "pwsh -NoProfile -File .\\tools\\collect_companion_diagnostics.ps1 -Fixture",
                "python .\\tools\\verify_companion_diagnostics_static.py",
                "python .\\tools\\verify_expression_screen_runtime_diagnostic_decode.py",
                "python .\\tools\\verify_expression_wba_portability.py",
            ],
            "WBA diagnostics bundles should keep e_paper.runtime_snapshot in bounded pulls and preserve decoded_args for host bring-up tooling.",
        ),
        item(
            "real_ble_screen_final_status_bench",
            "Real BLE screen final-status bench",
            "PASS",
            "The real BLE bench collects accepted and final CardStatusV1 records for card_write and settings_sleepy_screen_status, and --expect-real-panel requires final rendered/ok before a hardware refresh claim.",
            [
                "tools/companion_ble_real_bench.py",
                "tools/verify_expression_real_ble_screen_bench.py",
                "docs/ble_gatt_contract.md",
                "docs/bringup_steps.md",
                "docs/validation/companion-screen-real-ble-bench.json",
                "docs/companion_screen_expression_system.md",
                "docs/stm32wba_migration_rules.md",
            ],
            [
                "python .\\tools\\verify_expression_real_ble_screen_bench.py",
                "python -m py_compile .\\tools\\companion_ble_real_bench.py",
                "python .\\tools\\verify_expression_status_observability.py",
                "python .\\tools\\verify_expression_wba_portability.py",
            ],
            "WBA real BLE bench artifacts must keep the same accepted/final CardStatusV1 identity for card writes and SettingsV1-triggered ExpressionV1 updates, then use --expect-real-panel before claiming rendered/ok parity.",
        ),
        item(
            "real_ble_expression_status_sequence_contract",
            "Real BLE ExpressionV1 status sequence contract",
            "PASS",
            "The real BLE bench artifact carries the contract-only screen_expression_status operation linked to the six-face host status sequence before WB55/WBA panel parity is claimed.",
            [
                "tools/companion_ble_real_bench.py",
                "tools/verify_expression_real_ble_screen_bench.py",
                "tools/verify_expression_host_status_sequence.py",
                "docs/validation/companion-screen-real-ble-bench.json",
                "docs/validation/companion-screen-expression-host-status-sequence.json",
                "docs/ble_gatt_contract.md",
                "docs/bringup_steps.md",
                "docs/companion_screen_expression_system.md",
                "docs/stm32wba_migration_rules.md",
            ],
            [
                "python .\\tools\\verify_expression_real_ble_screen_bench.py",
                "python .\\tools\\verify_expression_host_status_sequence.py",
                "python -m py_compile .\\tools\\companion_ble_real_bench.py",
                "python .\\tools\\verify_expression_wba_portability.py",
            ],
            "WBA real BLE artifacts must include screen_expression_status with the same six-face host sequence baseline before using --expect-real-panel to claim rendered/ok parity.",
        ),
        item(
            "panel_hardware_evidence_template",
            "Panel hardware evidence template",
            "PASS",
            "The real-panel acceptance template defines the controller, pin map, timing, CardStatus/log/runtime diagnostics, real BLE artifact, visual evidence, and target-adapter facts required before any WB55 or WBA real refresh claim.",
            [
                "docs/validation/companion-screen-real-ble-bench.json",
                "docs/validation/companion-screen-runtime-diagnostics.json",
                "docs/validation/companion-screen-runtime-diagnostic-decode.json",
                "docs/validation/companion-diagnostics-fixture/summary.json",
                "docs/validation/companion-screen-panel-evidence-template.json",
                "docs/validation/companion-screen-panel-hardware-gate.json",
                "docs/companion_screen_expression_system.md",
                "docs/stm32wba_migration_rules.md",
                "tools/verify_expression_panel_evidence_template.py",
            ],
            [
                "python .\\tools\\verify_expression_real_ble_screen_bench.py",
                "python .\\tools\\verify_expression_panel_evidence_template.py",
                "python .\\tools\\verify_expression_panel_gate.py",
                "python .\\tools\\verify_expression_screen_runtime_diagnostics.py",
                "python .\\tools\\verify_expression_screen_runtime_diagnostic_decode.py",
                "python .\\tools\\verify_companion_diagnostics_static.py",
                "python .\\tools\\verify_expression_wba_portability.py",
            ],
            "WBA55/WBA65 panel work must fill the same evidence template with a target-specific *_stm32wba.* adapter record before claiming parity.",
        ),
        item(
            "panel_evidence_runtime_diagnostics",
            "Panel evidence runtime diagnostics",
            "PASS",
            "The panel evidence template, scaffold, and validator require e_paper.runtime_snapshot decoded_args with zero panel errors, zero pending display work, and zero dropped display work before a real refresh claim.",
            [
                "tools/verify_expression_panel_evidence_template.py",
                "tools/verify_expression_panel_evidence_record.py",
                "tools/init_expression_panel_evidence_record.py",
                "docs/validation/companion-screen-panel-evidence-template.json",
                "docs/validation/companion-screen-panel-evidence-record-scaffold.json",
                "docs/validation/companion-screen-panel-evidence-record-validator.json",
                "docs/validation/companion-screen-runtime-diagnostics.json",
                "docs/validation/companion-screen-runtime-diagnostic-decode.json",
                "docs/validation/companion-diagnostics-fixture/summary.json",
                "docs/companion_screen_expression_system.md",
                "docs/stm32wba_migration_rules.md",
                "app/companion_pendant/epaper/README.md",
            ],
            [
                "python .\\tools\\verify_expression_panel_evidence_template.py",
                "python .\\tools\\init_expression_panel_evidence_record.py",
                "python .\\tools\\verify_expression_panel_evidence_record.py --self-test",
                "python .\\tools\\verify_expression_screen_runtime_diagnostics.py",
                "python .\\tools\\verify_expression_screen_runtime_diagnostic_decode.py",
                "python .\\tools\\verify_companion_diagnostics_static.py",
                "python .\\tools\\verify_expression_wba_portability.py",
            ],
            "WBA real-panel evidence must include the same decoded runtime snapshot health checks in the filled *_stm32wba.* evidence record.",
        ),
        item(
            "panel_evidence_diagnostics_bundle_validator",
            "Panel evidence diagnostics bundle validator",
            "PASS",
            "Filled real-panel evidence records must point at a diagnostics bundle summary whose epaper.runtime_snapshot_decoded and decoded tail event show zero panel errors, zero pending display work, and zero dropped display work.",
            [
                "tools/collect_companion_diagnostics.ps1",
                "tools/verify_companion_diagnostics_static.py",
                "tools/verify_expression_panel_evidence_record.py",
                "tools/verify_expression_panel_evidence_template.py",
                "tools/init_expression_panel_evidence_record.py",
                "docs/validation/companion-diagnostics-fixture/summary.json",
                "docs/validation/companion-screen-panel-evidence-template.json",
                "docs/validation/companion-screen-panel-evidence-record-scaffold.json",
                "docs/validation/companion-screen-panel-evidence-record-validator.json",
                "docs/companion_screen_expression_system.md",
                "docs/bringup_steps.md",
                "docs/stm32wba_migration_rules.md",
                "app/companion_pendant/epaper/README.md",
            ],
            [
                "python .\\tools\\verify_expression_panel_evidence_template.py",
                "python .\\tools\\init_expression_panel_evidence_record.py",
                "python .\\tools\\verify_expression_panel_evidence_record.py --self-test",
                "python .\\tools\\verify_companion_diagnostics_static.py",
                "python .\\tools\\verify_expression_wba_portability.py",
            ],
            "WBA real-panel evidence must attach the same diagnostics bundle summary so a WBA port cannot claim parity without host-decoded screen runtime health.",
        ),
        item(
            "panel_evidence_record_validator",
            "Panel evidence record validator",
            "PASS",
            "The real-panel evidence validator rejects missing fields, deferred no-panel status, runtime diagnostic errors, request identity drift, missing visual artifacts, missing screen_expression_status, missing screen_expression_demo_status, and non-target-named adapters before the hardware gate can move.",
            [
                "tools/init_expression_panel_evidence_record.py",
                "tools/verify_expression_panel_evidence_record.py",
                "tools/verify_expression_host_status_sequence.py",
                "tools/verify_expression_demo_host_status_sequence.py",
                "docs/validation/companion-screen-panel-evidence-record-scaffold.json",
                "docs/validation/companion-screen-panel-evidence-record-validator.json",
                "docs/validation/companion-screen-panel-evidence-template.json",
                "docs/validation/companion-screen-real-ble-bench.json",
                "docs/validation/companion-screen-expression-host-status-sequence.json",
                "docs/validation/companion-screen-expression-demo-host-status-sequence.json",
                "docs/validation/companion-screen-runtime-diagnostics.json",
                "docs/validation/companion-screen-runtime-diagnostic-decode.json",
                "docs/validation/companion-screen-panel-hardware-gate.json",
                "docs/companion_screen_expression_system.md",
                "docs/bringup_steps.md",
                "docs/stm32wba_migration_rules.md",
            ],
            [
                "python .\\tools\\init_expression_panel_evidence_record.py",
                "python .\\tools\\verify_expression_panel_evidence_record.py --self-test",
                "python .\\tools\\verify_expression_panel_evidence_template.py",
                "python .\\tools\\verify_expression_screen_runtime_diagnostic_decode.py",
                "python .\\tools\\verify_expression_host_status_sequence.py",
                "python .\\tools\\verify_expression_demo_host_status_sequence.py",
                "python .\\tools\\verify_expression_panel_gate.py",
            ],
            "WBA panel evidence records must pass the same validator with *_stm32wba.* adapter files before claiming rendered/ok parity.",
        ),
        item(
            "panel_evidence_real_ble_sequence_validator",
            "Panel evidence real BLE sequence validator",
            "PASS",
            "Filled real-panel evidence records must point at a real BLE artifact that includes both screen_expression_status six-face and screen_expression_demo_status full-demo host sequence baselines as well as rendered/ok hardware statuses.",
            [
                "tools/verify_expression_panel_evidence_record.py",
                "tools/verify_expression_real_ble_screen_bench.py",
                "tools/verify_expression_host_status_sequence.py",
                "tools/verify_expression_demo_host_status_sequence.py",
                "docs/validation/companion-screen-panel-evidence-record-validator.json",
                "docs/validation/companion-screen-panel-evidence-template.json",
                "docs/validation/companion-screen-real-ble-bench.json",
                "docs/validation/companion-screen-expression-host-status-sequence.json",
                "docs/validation/companion-screen-expression-demo-host-status-sequence.json",
                "docs/companion_screen_expression_system.md",
                "docs/bringup_steps.md",
                "docs/stm32wba_migration_rules.md",
                "app/companion_pendant/epaper/README.md",
            ],
            [
                "python .\\tools\\verify_expression_panel_evidence_record.py --self-test",
                "python .\\tools\\verify_expression_real_ble_screen_bench.py",
                "python .\\tools\\verify_expression_host_status_sequence.py",
                "python .\\tools\\verify_expression_demo_host_status_sequence.py",
                "python .\\tools\\verify_expression_panel_evidence_template.py",
                "python .\\tools\\verify_expression_wba_portability.py",
            ],
            "WBA real-panel evidence records must reject real BLE artifacts that omit screen_expression_status or screen_expression_demo_status, keeping both host sequence baselines attached to parity evidence.",
        ),
        item(
            "panel_hardware_acceptance_plan",
            "Panel hardware acceptance plan",
            "PASS",
            "WB55 real-panel refresh is accepted; the same target-specific evidence plan keeps WBA55/WBA65 hardware parity deferred until each target supplies its own verified record.",
            [
                "tools/verify_expression_panel_hardware_acceptance_plan.py",
                "tools/verify_expression_panel_hardware_session.py",
                "docs/validation/companion-screen-panel-hardware-acceptance-plan.json",
                "docs/validation/companion-screen-panel-hardware-session.json",
                "docs/validation/companion-screen-panel-hardware-gate.json",
                "docs/validation/companion-screen-panel-evidence-template.json",
                "docs/validation/companion-screen-panel-evidence-record-validator.json",
                "docs/validation/companion-screen-panel-wiring-preflight.json",
                "docs/validation/companion-screen-real-ble-bench.json",
                "docs/validation/companion-screen-runtime-diagnostics.json",
                "docs/validation/companion-screen-runtime-diagnostic-decode.json",
                "docs/validation/companion-screen-panel-target-stm32wb.json",
                "docs/validation/companion-screen-wba-port-contract.json",
                "docs/validation/companion-screen-wba55-port-scaffold.json",
                "docs/companion_screen_expression_system.md",
                "docs/bringup_steps.md",
                "docs/stm32wba_migration_rules.md",
            ],
            [
                "python .\\tools\\verify_expression_panel_hardware_acceptance_plan.py",
                "python .\\tools\\verify_expression_panel_hardware_session.py",
                "python .\\tools\\verify_expression_panel_gate.py",
                "python .\\tools\\verify_expression_panel_target_stm32wb.py",
                "python .\\tools\\verify_expression_panel_evidence_record.py --self-test",
                "python .\\tools\\verify_expression_panel_wiring_preflight.py",
                "python .\\tools\\verify_expression_real_ble_screen_bench.py",
                "python .\\tools\\verify_expression_screen_runtime_diagnostics.py",
                "python .\\tools\\verify_expression_screen_runtime_diagnostic_decode.py",
                "python .\\tools\\verify_expression_wba_portability.py",
            ],
            "WBA55/WBA65 must use the same plan with *_stm32wba.* adapters, WBA portability checks, and target evidence records before claiming real-panel parity.",
        ),
        item(
            "wb55_screen_build_matrix",
            "WB55 screen build matrix",
            "PASS",
            "The WB55 screen firmware keeps default dry-run, explicit SSD1681 real-panel, and ScreenAssetProvision external ui_assets builds compilable, so machine pre-acceptance cannot pass on a path that only links one transport or skips the current CEMP provision image.",
            [
                "tools/verify_wb55_screen_build_matrix.py",
                "tools/build_nucleo_bringup.ps1",
                "cubeide/Companion_Nucleo_WB55RG_Bringup/Makefile",
                "cubeide/Companion_Nucleo_WB55RG_Bringup/Core/Src/main.c",
                "cubeide/Companion_Nucleo_WB55RG_Bringup/Core/Src/app_ble.c",
                "app/companion_pendant/epaper/display_queue.h",
                "app/companion_pendant/epaper/display_queue.c",
                "app/companion_pendant/epaper/panel_target_stm32wb.c",
                "app/companion_pendant/epaper/panel_target_stm32wb_ssd1681.c",
                "docs/validation/companion-screen-wb55-build-matrix.json",
                "docs/validation/companion-screen-pre-acceptance-health.json",
                ".cache/validation/wb55-build-matrix/default-build.log",
                ".cache/validation/wb55-build-matrix/ssd1681-build.log",
                ".cache/validation/wb55-build-matrix/screen-asset-provision-build.log",
            ],
            [
                "python .\\tools\\verify_wb55_screen_build_matrix.py",
                "pwsh -NoProfile -File .\\tools\\build_nucleo_bringup.ps1 -Force",
                "pwsh -NoProfile -File .\\tools\\build_nucleo_bringup.ps1 -EpaperSsd1681Bringup -Force",
                "pwsh -NoProfile -File .\\tools\\build_nucleo_bringup.ps1 -ScreenAssetProvision -Force",
                "python .\\tools\\verify_companion_screen_pre_acceptance_health.py",
            ],
            "WBA branches must add an analogous target build wrapper before claiming WBA parity; this WB55 matrix prevents portable code from silently depending on one target transport.",
        ),
        item(
            "wb55_real_panel_refresh",
            "WB55 real e-paper panel refresh",
            "PASS",
            "The physical GDEY0154D67-T03 completed SSD1681 full, partial, and fast refreshes on WB55; operator observations confirm a visible black update and upright non-mirrored orientation.",
            [
                "app/companion_pendant/epaper/panel_adapter.h",
                "app/companion_pendant/epaper/panel_adapter.c",
                "app/companion_pendant/epaper/panel_target_stm32wb.h",
                "app/companion_pendant/epaper/panel_target_stm32wb.c",
                "app/companion_pendant/epaper/panel_target_stm32wb_ssd1681.c",
                "docs/companion_screen_expression_system.md",
                "docs/validation/companion-screen-panel-hardware-gate.json",
                "docs/validation/companion-screen-wb55-ssd1681-bringup.json",
                "docs/validation/companion-screen-ssd1681-partial-refresh-wb55.json",
                "docs/validation/companion-screen-touch-ft6336-wb55.json",
            ],
            [
                "python .\\tools\\verify_expression_panel_gate.py",
                "python .\\tools\\verify_expression_panel_target_stm32wb.py",
                "python .\\tools\\verify_epaper_refresh_policy.py",
                "python .\\tools\\verify_epaper_fast_maintenance_runtime.py",
                "python .\\tools\\verify_touch_ft6336.py",
            ],
            "WBA panel work must preserve the proven portable queue, policy, presentation, and asset contracts while replacing only target backends.",
        ),
        item(
            "wb55_runtime_serial_capture_preflight",
            "WB55 runtime serial capture preflight",
            "PASS",
            f"The rev{CANDIDATE.revision} runtime recheck serial path is statically verified before any COM port is opened: capture_nucleo_serial.ps1 requires -Execute and -WorkflowLockHeld, the locked runner captures provision and normal boots for 25 s into stable raw/summary filenames, and the log verifier consumes those exact artifacts.",
            [
                "tools/render_wb55_runtime_hardware_action_card.py",
                "tools/verify_wb55_runtime_flash_preflight.py",
                "tools/verify_wb55_runtime_serial_capture_preflight.py",
                "tools/capture_nucleo_serial.ps1",
                "tools/run_wb55_screen_runtime_recheck.ps1",
                "tools/verify_wb55_screen_runtime_recheck_logs.py",
                "docs/validation/companion-screen-wb55-runtime-hardware-action-card.json",
                "docs/validation/companion-screen-wb55-runtime-hardware-action-card.md",
                "docs/validation/companion-screen-wb55-runtime-flash-preflight.json",
                "docs/validation/companion-screen-wb55-runtime-serial-capture-preflight.json",
                RUNTIME_RUN_REPORT,
            ],
            [
                "python .\\tools\\render_wb55_runtime_hardware_action_card.py",
                "python .\\tools\\verify_wb55_runtime_flash_preflight.py",
                "python .\\tools\\verify_wb55_runtime_serial_capture_preflight.py",
                "pwsh -NoProfile -File .\\tools\\run_wb55_screen_runtime_recheck.ps1 -CheckOnly",
            ],
            "WBA runtime evidence must add an analogous target-specific locked capture preflight before any WBA real-panel parity claim.",
        ),
        item(
            RUNTIME_GATE_ID,
            f"WB55 rev{CANDIDATE.revision} provision/normal runtime recheck",
            "PASS" if wb55_runtime_proven else "DEFERRED_HARDWARE",
            (
                f"The rev{CANDIDATE.revision} CEMP resource pack is first-hand runtime-proven on WB55: the locked hardware action card completed flash provision, capture provision logs, restore normal firmware, and capture normal logs; the SCR-17 release ledger and coherent_generation marker path are present and the promotion gate is applied."
                if wb55_runtime_proven else
                f"The current rev{CANDIDATE.revision} CEMP resource pack is machine-prepared but not yet first-hand runtime-proven on WB55: the locked hardware action card must flash provision, capture provision logs, restore normal firmware, capture normal logs, verify the SCR-17 release ledger and coherent_generation marker path, then the log verifier and promotion gate may advance pre-acceptance."
            ),
            [
                "tools/run_wb55_screen_runtime_recheck.ps1",
                "tools/verify_wb55_screen_runtime_recheck_logs.py",
                "tools/promote_wb55_screen_runtime_recheck.py",
                "tools/render_wb55_runtime_hardware_action_card.py",
                "tools/verify_wb55_runtime_flash_preflight.py",
                "tools/verify_wb55_runtime_serial_capture_preflight.py",
                "tools/verify_screen_generation_release_ledger.py",
                "docs/validation/companion-screen-wb55-runtime-recheck-runner.json",
                "docs/validation/companion-screen-wb55-runtime-recheck-logs.json",
                "docs/validation/companion-screen-wb55-runtime-promotion.json",
                "docs/validation/companion-screen-wb55-runtime-hardware-action-card.json",
                "docs/validation/companion-screen-wb55-runtime-hardware-action-card.md",
                "docs/validation/companion-screen-wb55-runtime-flash-preflight.json",
                "docs/validation/companion-screen-wb55-runtime-serial-capture-preflight.json",
                "docs/validation/companion-screen-generation-release-ledger.json",
                RUNTIME_RUN_REPORT,
            ],
            [
                "python .\\tools\\verify_wb55_screen_runtime_recheck_runner.py",
                "python .\\tools\\render_wb55_runtime_hardware_action_card.py",
                "python .\\tools\\verify_wb55_runtime_flash_preflight.py",
                "python .\\tools\\verify_wb55_runtime_serial_capture_preflight.py",
                "python .\\tools\\verify_screen_generation_release_ledger.py",
                "pwsh -NoProfile -File .\\tools\\run_wb55_screen_runtime_recheck.ps1 -CheckOnly",
                "python .\\tools\\verify_wb55_screen_runtime_recheck_logs.py",
                "python .\\tools\\promote_wb55_screen_runtime_recheck.py",
            ],
            "WBA ports must add the same target-specific provision/normal runtime recheck gate before WBA real-panel parity can move from scaffold to hardware evidence.",
            [] if wb55_runtime_proven else [
                f"rev{CANDIDATE.revision} provision serial raw/summary logs",
                f"rev{CANDIDATE.revision} normal serial raw/summary logs",
                "locked Companion-WB55 hardware run with normal_firmware_restored=true",
            ],
        ),
        item(
            "wb55_touch_visual_acceptance",
            "WB55 touch navigation and fast-refresh visual acceptance",
            "PENDING_HUMAN",
                f"Machine checks, physical contact/release, revision {CANDIDATE.revision} candidate generation hygiene, and the last runtime-proven external_flash mount are covered by the pre-acceptance health gate; the operator still needs to confirm daily tap/swipe pet reactions, anywhere 3 s menu entry with a 650 ms tease, a stable six-row menu-v3 home during vertical strokes, press-cue plus target-arrival partial refreshes, left-edge return, language switching, and that 0xCF maintenance is perceived as a single quiet flash.",
            [
                "tools/render_wb55_touch_visual_acceptance_packet.py",
                "tools/render_wb55_runtime_hardware_action_card.py",
                "tools/verify_wb55_runtime_flash_preflight.py",
                "tools/verify_wb55_runtime_serial_capture_preflight.py",
                "tools/render_wb55_touch_visual_review_template.py",
                "tools/verify_wb55_touch_visual_review_record.py",
                "tools/verify_companion_screen_pre_acceptance_health.py",
                "tools/verify_display_queue_generation_hygiene.py",
                "tools/verify_screen_generation_release_ledger.py",
                "docs/validation/companion-screen-pre-acceptance-health.json",
                "docs/validation/companion-screen-display-queue-generation-hygiene.json",
                "docs/validation/companion-screen-generation-release-ledger.json",
                "docs/validation/companion-screen-wb55-touch-visual-acceptance-packet.json",
                "docs/validation/companion-screen-wb55-touch-visual-acceptance-packet.md",
                "docs/validation/companion-screen-wb55-runtime-hardware-action-card.json",
                "docs/validation/companion-screen-wb55-runtime-hardware-action-card.md",
                "docs/validation/companion-screen-wb55-runtime-flash-preflight.json",
                "docs/validation/companion-screen-wb55-runtime-serial-capture-preflight.json",
                "docs/validation/companion-screen-wb55-touch-visual-review-template.json",
                "docs/validation/companion-screen-wb55-touch-visual-review-template.md",
                "docs/validation/companion-screen-wb55-touch-visual-review-record.json",
                "docs/companion_screen_project_plan.md",
                "docs/validation/companion-screen-presentation-wb55.json",
                "docs/validation/companion-screen-bilingual-menu-wb55.json",
                "docs/validation/companion-screen-touch-ft6336-wb55.json",
                "docs/validation/companion-screen-ssd1681-partial-refresh-wb55.json",
                ".cache/validation/nucleo-serial-20260712-184908/nucleo-serial-summary.json",
                ".cache/validation/nucleo-serial-20260712-184908/nucleo-serial-raw.log",
                ".cache/validation/nucleo-serial-20260712-185021/nucleo-serial-summary.json",
                ".cache/validation/nucleo-serial-20260712-185021/nucleo-serial-raw.log",
            ],
            [
                "python .\\tools\\render_wb55_touch_visual_acceptance_packet.py",
                "python .\\tools\\render_wb55_runtime_hardware_action_card.py",
                "python .\\tools\\verify_wb55_runtime_flash_preflight.py",
                "python .\\tools\\verify_wb55_runtime_serial_capture_preflight.py",
                "python .\\tools\\render_wb55_touch_visual_review_template.py",
                "python .\\tools\\verify_wb55_touch_visual_review_record.py",
                "python .\\tools\\verify_companion_screen_pre_acceptance_health.py",
                "python .\\tools\\verify_display_queue_generation_hygiene.py",
                "python .\\tools\\verify_screen_generation_release_ledger.py",
                "python .\\tools\\verify_screen_menu_assets.py",
                "python .\\tools\\verify_screen_presentation.py",
                "python .\\tools\\verify_touch_ft6336.py",
                "python .\\tools\\verify_epaper_fast_maintenance_runtime.py",
            ],
            "Repeat the same focused touch and visual acceptance after the WBA backend is available; portable gesture semantics must not change.",
        ),
        item(
            "companion_screen_goal_audit",
            "Active goal completion audit",
            "PENDING_HUMAN",
            (
                f"The full screen goal is machine-audited: WB55 wiring, refresh, rev{CANDIDATE.revision} resource generation hygiene, WB55 dry-run/SSD1681 build matrix, last-proven external resources, touch IC health, external Flash policy, pre-acceptance health, and WBA pre-port boundaries are tracked; rev{CANDIDATE.revision} provision/normal runtime recheck and screen refresh/touch machine health on the current resource pack are proved, leaving daily pet/menu human feel and future WBA real-panel parity."
                if wb55_runtime_proven else
                f"The full screen goal is machine-audited: WB55 wiring, refresh, rev{CANDIDATE.revision} resource generation hygiene, WB55 dry-run/SSD1681 build matrix, last-proven external resources, touch IC health, external Flash policy, pre-acceptance health, and WBA pre-port boundaries are tracked; the open requirements are rev{CANDIDATE.revision} provision/normal runtime recheck, screen refresh/touch machine health on the current resource pack, daily pet/menu human feel, and future WBA real-panel parity."
            ),
            [
                "tools/verify_companion_screen_goal_audit.py",
                "tools/verify_companion_screen_pre_acceptance_health.py",
                "docs/validation/companion-screen-goal-audit.json",
                "docs/validation/companion-screen-goal-audit.md",
                "docs/validation/companion-screen-pre-acceptance-health.json",
                "docs/validation/companion-screen-display-queue-generation-hygiene.json",
                "docs/validation/companion-screen-generation-release-ledger.json",
                "docs/validation/companion-screen-wb55-build-matrix.json",
                "docs/validation/companion-screen-bilingual-menu-wb55.json",
                "docs/validation/companion-screen-wb55-touch-visual-acceptance-packet.json",
                "docs/validation/companion-screen-wb55-touch-visual-review-template.json",
                "docs/validation/companion-screen-wb55-touch-visual-review-record.json",
                "docs/validation/companion-screen-wb55-runtime-hardware-action-card.json",
                "docs/validation/companion-screen-wb55-runtime-flash-preflight.json",
                "docs/validation/companion-screen-wb55-runtime-serial-capture-preflight.json",
                "docs/validation/companion-screen-wba-port-contract.json",
                "docs/validation/companion-screen-wba-lse-clock-contract.json",
            ],
            [
                "python .\\tools\\verify_companion_screen_goal_audit.py",
                "python .\\tools\\verify_companion_screen_pre_acceptance_health.py",
                "python .\\tools\\verify_display_queue_generation_hygiene.py",
                "python .\\tools\\verify_screen_generation_release_ledger.py",
                "python .\\tools\\verify_wb55_screen_build_matrix.py",
                "python .\\tools\\render_wb55_touch_visual_acceptance_packet.py",
                "python .\\tools\\render_wb55_runtime_hardware_action_card.py",
                "python .\\tools\\verify_wb55_runtime_flash_preflight.py",
                "python .\\tools\\verify_wb55_runtime_serial_capture_preflight.py",
                "python .\\tools\\render_wb55_touch_visual_review_template.py",
                "python .\\tools\\verify_wb55_touch_visual_review_record.py",
                "python .\\tools\\verify_screen_menu_assets.py",
                "python .\\tools\\verify_screen_resource_architecture.py",
                "python .\\tools\\verify_expression_wba_portability.py",
                "python .\\tools\\verify_expression_wba_lse_clock_contract.py",
            ],
            "WBA real-panel parity remains a future hardware/project gate; the audit prevents closing the shared goal on WB55-only evidence.",
        ),
    ]
    pass_count = sum(1 for entry in items if entry["status"] == "PASS")
    deferred_count = sum(1 for entry in items if entry["status"].startswith("DEFERRED"))
    pending_human_count = sum(1 for entry in items if entry["status"] == "PENDING_HUMAN")
    return {
        "schema_id": SCHEMA_ID,
        "summary": {
            "pass_count": pass_count,
            "deferred_count": deferred_count,
            "pending_human_count": pending_human_count,
            "total_count": len(items),
            "next_hardware_gate": "wba_real_panel_parity" if wb55_runtime_proven else RUNTIME_GATE_ID,
            "next_human_gate": "wb55_touch_visual_acceptance",
        },
        "items": items,
    }


def command_tools(command: str) -> list[str]:
    return [
        token.strip(".\\")
        for token in command.split()
        if token.startswith(".\\tools\\") or token.startswith("tools\\") or token.startswith("tools/")
    ]


def check_index(data: dict[str, Any], errors: list[str]) -> None:
    require(data.get("schema_id") == SCHEMA_ID, "unexpected acceptance index schema", errors)
    items = data.get("items", [])
    require(isinstance(items, list) and items, "acceptance index has no items", errors)
    ids = {entry.get("id") for entry in items if isinstance(entry, dict)}
    require("wb55_real_panel_refresh" in ids, "acceptance index missing real panel hardware gate", errors)
    require("wb55_runtime_serial_capture_preflight" in ids, "acceptance index missing WB55 runtime serial capture preflight", errors)
    require(RUNTIME_GATE_ID in ids, f"acceptance index missing {RUNTIME_GATE_ID} hardware gate", errors)
    require("wb55_touch_visual_acceptance" in ids, "acceptance index missing WB55 human interaction gate", errors)
    require("companion_screen_goal_audit" in ids, "acceptance index missing active goal completion audit", errors)
    require("wba_pre_port_gate" in ids, "acceptance index missing WBA pre-port gate", errors)
    require("wba_lse_clock_contract" in ids, "acceptance index missing WBA LSE clock contract", errors)
    require("expression_visual_contract" in ids, "acceptance index missing expression visual contract", errors)
    require("expression_visual_acceptance_matrix" in ids, "acceptance index missing expression visual acceptance matrix", errors)
    require("generated_art_style_contract" in ids, "acceptance index missing generated-art style contract", errors)
    require("screen_generation_swap_guard" in ids, "acceptance index missing screen generation swap guard", errors)
    require("screen_refresh_feel_contract" in ids, "acceptance index missing screen refresh feel contract", errors)
    require("expression_layout_contract" in ids, "acceptance index missing expression layout contract", errors)
    require("display_queue_fault_paths" in ids, "acceptance index missing display queue fault paths", errors)
    require("display_queue_telemetry" in ids, "acceptance index missing display queue telemetry", errors)
    require("screen_display_drain_contract" in ids, "acceptance index missing screen display drain contract", errors)
    require("wb55_boot_idle_expression" in ids, "acceptance index missing WB55 boot idle expression", errors)
    require("screen_status_observability" in ids, "acceptance index missing screen status observability", errors)
    require("host_ble_expression_status_fixture" in ids, "acceptance index missing host BLE expression status fixture", errors)
    require(
        "host_ble_expression_extended_status_fixture" in ids,
        "acceptance index missing host BLE expression extended status fixture",
        errors,
    )
    require(
        "host_ble_expression_status_sequence" in ids,
        "acceptance index missing host BLE expression status sequence fixture",
        errors,
    )
    require("expression_host_manifest" in ids, "acceptance index missing expression host manifest", errors)
    require(
        "screen_expression_demo_host_status_sequence" in ids,
        "acceptance index missing screen expression demo host status sequence",
        errors,
    )
    require("screen_expression_demo_sequence" in ids, "acceptance index missing screen expression demo sequence", errors)
    require(
        "screen_expression_demo_panel_handoff" in ids,
        "acceptance index missing screen expression demo panel handoff",
        errors,
    )
    require("screen_acceptance_runner" in ids, "acceptance index missing screen acceptance runner", errors)
    require("screen_feature_roadmap" in ids, "acceptance index missing screen feature roadmap", errors)
    require("screen_feature_checklist" in ids, "acceptance index missing screen feature checklist", errors)
    require("screen_settings_expression_policy" in ids, "acceptance index missing screen settings expression policy", errors)
    require("expression_catalog_contract" in ids, "acceptance index missing ExpressionV1 catalog contract", errors)
    require("expression_copy_contract" in ids, "acceptance index missing ExpressionV1 copy contract", errors)
    require("expression_priority_matrix" in ids, "acceptance index missing expression priority matrix", errors)
    require("expression_input_source_matrix" in ids, "acceptance index missing expression input source matrix", errors)
    require("expression_unknown_signal_guard" in ids, "acceptance index missing expression unknown signal guard", errors)
    require("expression_state_telemetry_snapshot" in ids, "acceptance index missing expression state telemetry snapshot", errors)
    require("wba_cube_dependency_preflight" in ids, "acceptance index missing WBA CubeWBA dependency preflight", errors)
    require("wba_port_scaffold" in ids, "acceptance index missing WBA port scaffold", errors)
    require("wba_panel_target_adapter_scaffold" in ids, "acceptance index missing WBA panel target adapter scaffold", errors)
    require("wba_refresh_intent_contract" in ids, "acceptance index missing WBA refresh intent contract", errors)
    require("wba_display_scheduler_scaffold" in ids, "acceptance index missing WBA display scheduler scaffold", errors)
    require("wba_screen_gatt_scaffold" in ids, "acceptance index missing WBA screen GATT scaffold", errors)
    require("wba_screen_assets_scaffold" in ids, "acceptance index missing WBA screen-assets scaffold", errors)
    require("wba_pet_behavior_user_data_scaffold" in ids, "acceptance index missing WBA pet behavior user-data scaffold", errors)
    require("target_capability_profile" in ids, "acceptance index missing target capability profile", errors)
    require("devboard_ioc_screen_preflight" in ids, "acceptance index missing devboard IOC screen preflight", errors)
    require("panel_wiring_preflight" in ids, "acceptance index missing panel wiring preflight", errors)
    require("panel_evidence_scaffold_wiring_prefill" in ids, "acceptance index missing panel evidence scaffold wiring prefill", errors)
    require("panel_hardware_session_scaffold" in ids, "acceptance index missing panel hardware session scaffold", errors)
    require("panel_session_directory_preflight" in ids, "acceptance index missing panel session directory preflight", errors)
    require("panel_hardware_facts_intake" in ids, "acceptance index missing panel hardware facts intake", errors)
    require("panel_hardware_facts_worksheet" in ids, "acceptance index missing panel hardware facts worksheet", errors)
    require("panel_bringup_operator_packet" in ids, "acceptance index missing panel bring-up operator packet", errors)
    require("panel_driver_readiness_report" in ids, "acceptance index missing panel driver readiness report", errors)
    require("panel_hardware_facts_bridge" in ids, "acceptance index missing panel hardware facts bridge", errors)
    require("panel_target_ops_boundary" in ids, "acceptance index missing panel target ops boundary", errors)
    require("wb55_panel_target_adapter_scaffold" in ids, "acceptance index missing WB55 panel target adapter scaffold", errors)
    require("panel_adapter_behavior_matrix" in ids, "acceptance index missing panel adapter behavior matrix", errors)
    require("panel_adapter_telemetry_snapshot" in ids, "acceptance index missing panel adapter telemetry snapshot", errors)
    require("screen_runtime_snapshot" in ids, "acceptance index missing screen runtime snapshot", errors)
    require("screen_runtime_diagnostics" in ids, "acceptance index missing screen runtime diagnostics", errors)
    require("screen_runtime_diagnostic_decode" in ids, "acceptance index missing screen runtime diagnostic decode", errors)
    require("screen_runtime_diagnostics_bundle" in ids, "acceptance index missing screen runtime diagnostics bundle", errors)
    require("real_ble_screen_final_status_bench" in ids, "acceptance index missing real BLE screen final-status bench", errors)
    require(
        "real_ble_expression_status_sequence_contract" in ids,
        "acceptance index missing real BLE expression status sequence contract",
        errors,
    )
    require("panel_hardware_evidence_template" in ids, "acceptance index missing panel hardware evidence template", errors)
    require("panel_evidence_runtime_diagnostics" in ids, "acceptance index missing panel evidence runtime diagnostics", errors)
    require(
        "panel_evidence_diagnostics_bundle_validator" in ids,
        "acceptance index missing panel evidence diagnostics bundle validator",
        errors,
    )
    require("panel_evidence_record_validator" in ids, "acceptance index missing panel evidence record validator", errors)
    require(
        "panel_evidence_real_ble_sequence_validator" in ids,
        "acceptance index missing panel evidence real BLE sequence validator",
        errors,
    )
    require("panel_hardware_acceptance_plan" in ids, "acceptance index missing panel hardware acceptance plan", errors)
    require("wb55_screen_build_matrix" in ids, "acceptance index missing WB55 screen build matrix", errors)
    require(
        "expression_duplicate_refresh_suppression" in ids,
        "acceptance index missing expression duplicate refresh suppression",
        errors,
    )
    require(
        "expression_transient_auto_recovery" in ids,
        "acceptance index missing expression transient auto recovery",
        errors,
    )
    require(
        "wb55_expression_tick_scheduler" in ids,
        "acceptance index missing WB55 expression tick scheduler",
        errors,
    )
    require(
        "wb55_settings_expression_hint" in ids,
        "acceptance index missing WB55 settings expression hint",
        errors,
    )
    require(
        "wb55_device_status_expression_hint" in ids,
        "acceptance index missing WB55 DeviceStatus expression hint",
        errors,
    )
    require(
        "wb55_interaction_status_expression_hint" in ids,
        "acceptance index missing WB55 interaction status expression hint",
        errors,
    )
    require(
        "wb55_battery_expression_hint" in ids,
        "acceptance index missing WB55 battery expression hint",
        errors,
    )
    require(
        "battery_recovery_expression_guard" in ids,
        "acceptance index missing battery recovery expression guard",
        errors,
    )
    require(
        "recording_state_expression_hook" in ids,
        "acceptance index missing recording state expression hook",
        errors,
    )
    require(
        "wb55_ota_readiness_expression_hint" in ids,
        "acceptance index missing WB55 OTA readiness expression hint",
        errors,
    )

    by_id = {str(entry.get("id")): entry for entry in items if isinstance(entry, dict)}
    build_matrix = by_id.get("wb55_screen_build_matrix", {})
    build_summary = str(build_matrix.get("summary", ""))
    for token in [
        "default dry-run",
        "SSD1681 real-panel",
        "ScreenAssetProvision",
        "current CEMP provision image",
        "only links one transport",
    ]:
        require(token in build_summary, f"wb55_screen_build_matrix summary missing token: {token}", errors)
    for path in [
        "docs/validation/companion-screen-wb55-build-matrix.json",
        "docs/validation/companion-screen-pre-acceptance-health.json",
        ".cache/validation/wb55-build-matrix/default-build.log",
        ".cache/validation/wb55-build-matrix/ssd1681-build.log",
        ".cache/validation/wb55-build-matrix/screen-asset-provision-build.log",
    ]:
        require(path in build_matrix.get("evidence_paths", []), f"wb55_screen_build_matrix missing evidence path: {path}", errors)
    for command in [
        "python .\\tools\\verify_wb55_screen_build_matrix.py",
        "pwsh -NoProfile -File .\\tools\\build_nucleo_bringup.ps1 -Force",
        "pwsh -NoProfile -File .\\tools\\build_nucleo_bringup.ps1 -EpaperSsd1681Bringup -Force",
        "pwsh -NoProfile -File .\\tools\\build_nucleo_bringup.ps1 -ScreenAssetProvision -Force",
    ]:
        require(command in build_matrix.get("validation_commands", []), f"wb55_screen_build_matrix missing command: {command}", errors)

    serial_capture = by_id.get("wb55_runtime_serial_capture_preflight", {})
    serial_summary = str(serial_capture.get("summary", ""))
    for token in [
        "statically verified",
        "capture_nucleo_serial.ps1",
        "-Execute",
        "-WorkflowLockHeld",
        "provision and normal boots",
        "25 s",
        "raw/summary filenames",
        "log verifier",
    ]:
        require(token in serial_summary, f"wb55_runtime_serial_capture_preflight summary missing token: {token}", errors)
    for path in [
        "docs/validation/companion-screen-wb55-runtime-hardware-action-card.json",
        "docs/validation/companion-screen-wb55-runtime-hardware-action-card.md",
        "docs/validation/companion-screen-wb55-runtime-flash-preflight.json",
        "docs/validation/companion-screen-wb55-runtime-serial-capture-preflight.json",
        RUNTIME_RUN_REPORT,
        "tools/render_wb55_runtime_hardware_action_card.py",
        "tools/verify_wb55_runtime_flash_preflight.py",
        "tools/capture_nucleo_serial.ps1",
        "tools/run_wb55_screen_runtime_recheck.ps1",
        "tools/verify_wb55_screen_runtime_recheck_logs.py",
    ]:
        require(path in serial_capture.get("evidence_paths", []), f"wb55_runtime_serial_capture_preflight missing evidence path: {path}", errors)
    for command in [
        "python .\\tools\\render_wb55_runtime_hardware_action_card.py",
        "python .\\tools\\verify_wb55_runtime_flash_preflight.py",
        "python .\\tools\\verify_wb55_runtime_serial_capture_preflight.py",
        "pwsh -NoProfile -File .\\tools\\run_wb55_screen_runtime_recheck.ps1 -CheckOnly",
    ]:
        require(command in serial_capture.get("validation_commands", []), f"wb55_runtime_serial_capture_preflight missing command: {command}", errors)

    runtime_recheck = by_id.get(RUNTIME_GATE_ID, {})
    wb55_runtime_proven = is_wb55_runtime_recheck_proven()
    expected_runtime_recheck_status = "PASS" if wb55_runtime_proven else "DEFERRED_HARDWARE"
    require(
        runtime_recheck.get("status") == expected_runtime_recheck_status,
        f"{RUNTIME_GATE_ID} must be {expected_runtime_recheck_status} for the current runtime evidence state",
        errors,
    )
    runtime_summary = str(runtime_recheck.get("summary", ""))
    for token in [
        f"rev{CANDIDATE.revision} CEMP resource pack",
        "locked hardware action card",
        "flash provision",
        "capture provision logs",
        "restore normal firmware",
        "capture normal logs",
        "SCR-17 release ledger",
        "coherent_generation marker",
        "promotion gate",
    ]:
        require(token in runtime_summary, f"{RUNTIME_GATE_ID} summary missing token: {token}", errors)
    for path in [
        "docs/validation/companion-screen-wb55-runtime-recheck-runner.json",
        "docs/validation/companion-screen-wb55-runtime-recheck-logs.json",
        "docs/validation/companion-screen-wb55-runtime-promotion.json",
        "docs/validation/companion-screen-wb55-runtime-hardware-action-card.json",
        "docs/validation/companion-screen-wb55-runtime-flash-preflight.json",
        "docs/validation/companion-screen-wb55-runtime-serial-capture-preflight.json",
        "docs/validation/companion-screen-generation-release-ledger.json",
    ]:
        require(path in runtime_recheck.get("evidence_paths", []), f"{RUNTIME_GATE_ID} missing evidence path: {path}", errors)
    if not wb55_runtime_proven:
        for missing in [
            f"rev{CANDIDATE.revision} provision serial raw/summary logs",
            f"rev{CANDIDATE.revision} normal serial raw/summary logs",
            "locked Companion-WB55 hardware run with normal_firmware_restored=true",
        ]:
            require(missing in runtime_recheck.get("missing_hardware_facts", []), f"{RUNTIME_GATE_ID} missing hardware fact: {missing}", errors)
    for command in [
        "python .\\tools\\verify_wb55_screen_runtime_recheck_runner.py",
        "python .\\tools\\render_wb55_runtime_hardware_action_card.py",
        "python .\\tools\\verify_wb55_runtime_flash_preflight.py",
        "python .\\tools\\verify_wb55_runtime_serial_capture_preflight.py",
        "python .\\tools\\verify_screen_generation_release_ledger.py",
        "pwsh -NoProfile -File .\\tools\\run_wb55_screen_runtime_recheck.ps1 -CheckOnly",
        "python .\\tools\\verify_wb55_screen_runtime_recheck_logs.py",
        "python .\\tools\\promote_wb55_screen_runtime_recheck.py",
    ]:
        require(command in runtime_recheck.get("validation_commands", []), f"{RUNTIME_GATE_ID} missing command: {command}", errors)

    generation_swap = by_id.get("screen_generation_swap_guard", {})
    generation_summary = str(generation_swap.get("summary", ""))
    for token in [
        "2026-07-13 research note",
        "release ledger",
        "physical e-paper ghosting",
        "old/new resource interleaving",
        "CEMP revisions",
        "activate atomically",
        "drain or discard stale queued frames",
        "coherent_generation",
        "old procedural faces",
        "old menu PBM",
        "stale framebuffer",
    ]:
        require(token in generation_summary, f"screen_generation_swap_guard summary missing token: {token}", errors)
    for path in [
        "docs/companion_screen_project_plan.md",
        "docs/validation/companion-screen-generation-swap-research.md",
        "docs/validation/companion-screen-display-queue-generation-hygiene.json",
        "docs/validation/companion-screen-generation-release-ledger.json",
        "docs/validation/companion-screen-display-drain-contract.json",
        "docs/validation/companion-screen-refresh-feel-contract.json",
    ]:
        require(path in generation_swap.get("evidence_paths", []), f"screen_generation_swap_guard missing evidence path: {path}", errors)
    require(
        "python .\\tools\\verify_screen_refresh_feel_contract.py" in generation_swap.get("validation_commands", []),
        "screen_generation_swap_guard must run refresh feel contract verifier",
        errors,
    )
    require(
        "python .\\tools\\verify_display_queue_generation_hygiene.py" in generation_swap.get("validation_commands", []),
        "screen_generation_swap_guard must run display queue generation hygiene verifier",
        errors,
    )
    require(
        "python .\\tools\\verify_screen_generation_release_ledger.py" in generation_swap.get("validation_commands", []),
        "screen_generation_swap_guard must run generation release ledger verifier",
        errors,
    )
    require(
        "python .\\tools\\verify_expression_display_drain.py" in generation_swap.get("validation_commands", []),
        "screen_generation_swap_guard must run display drain verifier",
        errors,
    )

    refresh_feel = by_id.get("screen_refresh_feel_contract", {})
    refresh_summary = str(refresh_feel.get("summary", ""))
    for token in [
        "differential partial refresh",
        "one quiet maintenance cleanup",
        "full refresh only",
        "unknown baseline",
        "fault recovery",
    ]:
        require(token in refresh_summary, f"screen_refresh_feel_contract summary missing token: {token}", errors)
    require(
        "docs/validation/companion-screen-refresh-feel-contract.json" in refresh_feel.get("evidence_paths", []),
        "screen_refresh_feel_contract must link the refresh feel fixture",
        errors,
    )
    require(
        "python .\\tools\\verify_screen_refresh_feel_contract.py" in refresh_feel.get("validation_commands", []),
        "screen_refresh_feel_contract must run its verifier",
        errors,
    )

    wba_refresh = by_id.get("wba_refresh_intent_contract", {})
    wba_refresh_text = " ".join(
        [
            str(wba_refresh.get("summary", "")),
            str(wba_refresh.get("wba_impact", "")),
            " ".join(str(path) for path in wba_refresh.get("evidence_paths", [])),
        ]
    )
    for token in [
        "refresh_mode",
        "16-bit dirty rectangles",
        "PARTIAL_INTERACTIVE",
        "MAINTENANCE",
        "FULL",
        "panel_target_stm32wba",
        "portable queue",
        "scene/player",
    ]:
        require(token in wba_refresh_text, f"wba_refresh_intent_contract missing token: {token}", errors)
    for command in [
        "python .\\tools\\verify_expression_panel_target_stm32wba.py",
        "python .\\tools\\verify_expression_wba_portability.py",
    ]:
        require(command in wba_refresh.get("validation_commands", []), f"wba_refresh_intent_contract missing command: {command}", errors)

    wba_lse = by_id.get("wba_lse_clock_contract", {})
    wba_lse_text = " ".join(
        [
            str(wba_lse.get("summary", "")),
            str(wba_lse.get("wba_impact", "")),
            " ".join(str(path) for path in wba_lse.get("evidence_paths", [])),
            " ".join(str(command) for command in wba_lse.get("validation_commands", [])),
        ]
    )
    for token in [
        "32.768 kHz LSE",
        "BLE sleep timing",
        "RTC continuity",
        "timed wake-up",
        "no-LSE variant",
        "radio-clock",
        "power evidence",
        "LSE startup",
        "BLE advertising/connection through sleep",
        "verify_expression_wba_lse_clock_contract.py",
    ]:
        require(token in wba_lse_text, f"wba_lse_clock_contract missing token: {token}", errors)
    for path in [
        "tools/verify_expression_wba_lse_clock_contract.py",
        "docs/validation/companion-screen-wba-lse-clock-contract.json",
        "docs/stm32wba_migration_rules.md",
        "docs/validation/companion-screen-wba-port-contract.json",
        "docs/validation/companion-screen-wba-real-parity-gate.json",
    ]:
        require(path in wba_lse.get("evidence_paths", []), f"wba_lse_clock_contract missing evidence path: {path}", errors)
    for command in [
        "python .\\tools\\verify_expression_wba_lse_clock_contract.py",
        "python .\\tools\\verify_expression_wba_portability.py",
        "python .\\tools\\verify_expression_wba_real_parity_gate.py",
    ]:
        require(command in wba_lse.get("validation_commands", []), f"wba_lse_clock_contract missing command: {command}", errors)

    touch_gate = by_id.get("wb55_touch_visual_acceptance", {})
    touch_summary = str(touch_gate.get("summary", ""))
    for token in [
        "daily tap/swipe pet reactions",
        "anywhere 3 s menu entry",
        "650 ms tease",
        "press-cue plus target-arrival partial refreshes",
        "language switching",
        "0xCF maintenance",
        f"revision {CANDIDATE.revision} candidate generation hygiene",
        "last runtime-proven external_flash mount",
        "pre-acceptance health gate",
    ]:
        require(token in touch_summary, f"wb55_touch_visual_acceptance summary missing current generation token: {token}", errors)
    for stale in [
        "direct visible-row entry with one refresh",
        "0xC7 maintenance",
        "swipe-left menu entry",
    ]:
        require(stale not in touch_summary, f"wb55_touch_visual_acceptance summary contains stale rule: {stale}", errors)
    require(
        "docs/validation/companion-screen-bilingual-menu-wb55.json" in touch_gate.get("evidence_paths", []),
        "wb55_touch_visual_acceptance must link the revision 48 bilingual menu fixture",
        errors,
    )
    require(
        "docs/validation/companion-screen-wb55-touch-visual-acceptance-packet.json" in touch_gate.get("evidence_paths", []),
        "wb55_touch_visual_acceptance must link the focused operator packet",
        errors,
    )
    require(
        "docs/validation/companion-screen-wb55-runtime-hardware-action-card.json" in touch_gate.get("evidence_paths", []),
        "wb55_touch_visual_acceptance must link the runtime hardware action card",
        errors,
    )
    require(
        "docs/validation/companion-screen-wb55-runtime-flash-preflight.json" in touch_gate.get("evidence_paths", []),
        "wb55_touch_visual_acceptance must link the runtime flash preflight fixture",
        errors,
    )
    require(
        "docs/validation/companion-screen-wb55-runtime-serial-capture-preflight.json" in touch_gate.get("evidence_paths", []),
        "wb55_touch_visual_acceptance must link the runtime serial capture preflight fixture",
        errors,
    )
    require(
        "docs/validation/companion-screen-wb55-touch-visual-review-template.json" in touch_gate.get("evidence_paths", []),
        "wb55_touch_visual_acceptance must link the structured review template",
        errors,
    )
    require(
        "docs/validation/companion-screen-wb55-touch-visual-review-record.json" in touch_gate.get("evidence_paths", []),
        "wb55_touch_visual_acceptance must link the filled review record validator fixture",
        errors,
    )
    require(
        "docs/validation/companion-screen-pre-acceptance-health.json" in touch_gate.get("evidence_paths", []),
        "wb55_touch_visual_acceptance must link the pre-acceptance health fixture",
        errors,
    )
    require(
        "docs/validation/companion-screen-display-queue-generation-hygiene.json" in touch_gate.get("evidence_paths", []),
        "wb55_touch_visual_acceptance must link the display queue generation hygiene fixture",
        errors,
    )
    require(
        "docs/validation/companion-screen-generation-release-ledger.json" in touch_gate.get("evidence_paths", []),
        "wb55_touch_visual_acceptance must link the generation release ledger",
        errors,
    )
    require(
        "python .\\tools\\verify_screen_menu_assets.py" in touch_gate.get("validation_commands", []),
        "wb55_touch_visual_acceptance must run the revision 48 menu verifier",
        errors,
    )
    require(
        "python .\\tools\\render_wb55_touch_visual_acceptance_packet.py" in touch_gate.get("validation_commands", []),
        "wb55_touch_visual_acceptance must run the focused operator packet verifier",
        errors,
    )
    require(
        "python .\\tools\\render_wb55_runtime_hardware_action_card.py" in touch_gate.get("validation_commands", []),
        "wb55_touch_visual_acceptance must run the runtime hardware action card verifier",
        errors,
    )
    require(
        "python .\\tools\\verify_wb55_runtime_flash_preflight.py" in touch_gate.get("validation_commands", []),
        "wb55_touch_visual_acceptance must run the runtime flash preflight verifier",
        errors,
    )
    require(
        "python .\\tools\\verify_wb55_runtime_serial_capture_preflight.py" in touch_gate.get("validation_commands", []),
        "wb55_touch_visual_acceptance must run the runtime serial capture preflight verifier",
        errors,
    )
    require(
        "python .\\tools\\render_wb55_touch_visual_review_template.py" in touch_gate.get("validation_commands", []),
        "wb55_touch_visual_acceptance must run the structured review template verifier",
        errors,
    )
    require(
        "python .\\tools\\verify_wb55_touch_visual_review_record.py" in touch_gate.get("validation_commands", []),
        "wb55_touch_visual_acceptance must run the filled review record verifier",
        errors,
    )
    require(
        "python .\\tools\\verify_companion_screen_pre_acceptance_health.py" in touch_gate.get("validation_commands", []),
        "wb55_touch_visual_acceptance must run the pre-acceptance health verifier",
        errors,
    )
    require(
        "python .\\tools\\verify_display_queue_generation_hygiene.py" in touch_gate.get("validation_commands", []),
        "wb55_touch_visual_acceptance must run the display queue generation hygiene verifier",
        errors,
    )
    require(
        "python .\\tools\\verify_screen_generation_release_ledger.py" in touch_gate.get("validation_commands", []),
        "wb55_touch_visual_acceptance must run the generation release ledger verifier",
        errors,
    )
    stale_prefix = ".cache/validation/screen-rev" + "36"
    for stale_path in (
        stale_prefix + "-provision/nucleo-serial-summary.json",
        stale_prefix + "-provision/nucleo-serial-raw.log",
        stale_prefix + "-normal/nucleo-serial-summary.json",
        stale_prefix + "-normal/nucleo-serial-raw.log",
    ):
        require(
            stale_path not in touch_gate.get("evidence_paths", []),
            f"wb55_touch_visual_acceptance still links stale rev36 evidence: {stale_path}",
            errors,
        )
    goal_audit = by_id.get("companion_screen_goal_audit", {})
    require(
        goal_audit.get("status") == "PENDING_HUMAN",
        "goal audit must keep the active goal open until human and WBA gates close",
        errors,
    )
    for token in (f"rev{CANDIDATE.revision} provision/normal runtime recheck", "screen refresh/touch machine health", "daily pet/menu human feel", "future WBA real-panel parity", f"rev{CANDIDATE.revision} resource generation hygiene", "WB55 dry-run/SSD1681 build matrix", "last-proven external resources", "pre-acceptance health"):
        require(token in str(goal_audit.get("summary", "")), f"goal audit summary missing {token}", errors)
    for path in (
        "docs/validation/companion-screen-goal-audit.json",
        "docs/validation/companion-screen-goal-audit.md",
        "docs/validation/companion-screen-pre-acceptance-health.json",
        "docs/validation/companion-screen-display-queue-generation-hygiene.json",
        "docs/validation/companion-screen-generation-release-ledger.json",
        "docs/validation/companion-screen-wb55-build-matrix.json",
        "docs/validation/companion-screen-wb55-touch-visual-review-template.json",
        "docs/validation/companion-screen-wb55-touch-visual-review-record.json",
        "docs/validation/companion-screen-wb55-runtime-hardware-action-card.json",
        "docs/validation/companion-screen-wb55-runtime-flash-preflight.json",
        "docs/validation/companion-screen-wb55-runtime-serial-capture-preflight.json",
        "docs/validation/companion-screen-wba-lse-clock-contract.json",
    ):
        require(path in goal_audit.get("evidence_paths", []), f"goal audit must link {path}", errors)
    require(
        "python .\\tools\\verify_companion_screen_goal_audit.py" in goal_audit.get("validation_commands", []),
        "goal audit must run its verifier",
        errors,
    )
    require(
        "python .\\tools\\verify_companion_screen_pre_acceptance_health.py" in goal_audit.get("validation_commands", []),
        "goal audit must run the pre-acceptance health verifier",
        errors,
    )
    require(
        "python .\\tools\\verify_display_queue_generation_hygiene.py" in goal_audit.get("validation_commands", []),
        "goal audit must run the display queue generation hygiene verifier",
        errors,
    )
    require(
        "python .\\tools\\verify_screen_generation_release_ledger.py" in goal_audit.get("validation_commands", []),
        "goal audit must run the generation release ledger verifier",
        errors,
    )
    require(
        "python .\\tools\\verify_wb55_screen_build_matrix.py" in goal_audit.get("validation_commands", []),
        "goal audit must run the WB55 screen build matrix verifier",
        errors,
    )
    require(
        "python .\\tools\\verify_wb55_touch_visual_review_record.py" in goal_audit.get("validation_commands", []),
        "goal audit must run the filled review record verifier",
        errors,
    )
    require(
        "python .\\tools\\render_wb55_runtime_hardware_action_card.py" in goal_audit.get("validation_commands", []),
        "goal audit must run the runtime hardware action card verifier",
        errors,
    )
    require(
        "python .\\tools\\verify_wb55_runtime_flash_preflight.py" in goal_audit.get("validation_commands", []),
        "goal audit must run the runtime flash preflight verifier",
        errors,
    )
    require(
        "python .\\tools\\verify_wb55_runtime_serial_capture_preflight.py" in goal_audit.get("validation_commands", []),
        "goal audit must run the runtime serial capture preflight verifier",
        errors,
    )
    require(
        "python .\\tools\\verify_expression_wba_lse_clock_contract.py" in goal_audit.get("validation_commands", []),
        "goal audit must run the WBA LSE clock contract verifier",
        errors,
    )
    require(
        "python .\\tools\\render_wb55_touch_visual_review_template.py" in goal_audit.get("validation_commands", []),
        "goal audit must run the touch/visual review template verifier",
        errors,
    )
    style_contract = by_id.get("generated_art_style_contract", {})
    require(
        "docs/validation/companion-screen-generated-art-style-contract.json" in style_contract.get("evidence_paths", []),
        "generated_art_style_contract must link its JSON snapshot",
        errors,
    )
    require(
        "python .\\tools\\render_generated_art_style_contract.py" in style_contract.get("validation_commands", []),
        "generated_art_style_contract must run its renderer verifier",
        errors,
    )

    for entry in items:
        if not isinstance(entry, dict):
            errors.append("acceptance index item is not an object")
            continue
        item_id = str(entry.get("id", ""))
        status = str(entry.get("status", ""))
        require(status in {"PASS", "DEFERRED_HARDWARE", "PENDING_HUMAN"}, f"{item_id} has invalid status {status}", errors)
        require(entry.get("title"), f"{item_id} missing title", errors)
        require(entry.get("summary"), f"{item_id} missing summary", errors)
        for evidence in entry.get("evidence_paths", []):
            path = REPO_ROOT / str(evidence)
            require(path.exists(), f"{item_id} missing evidence path {evidence}", errors)
        for command in entry.get("validation_commands", []):
            for tool in command_tools(str(command)):
                require((REPO_ROOT / tool).exists(), f"{item_id} command references missing tool {tool}", errors)
        if status == "PASS":
            require(not entry.get("missing_hardware_facts"), f"{item_id} PASS item still lists missing hardware facts", errors)
        if status == "DEFERRED_HARDWARE":
            require(entry.get("missing_hardware_facts"), f"{item_id} deferred item must list missing hardware facts", errors)
        if status == "PENDING_HUMAN":
            require(not entry.get("missing_hardware_facts"), f"{item_id} human gate must not claim missing hardware facts", errors)

    summary = data.get("summary", {})
    require(summary.get("pass_count") == sum(1 for entry in items if entry.get("status") == "PASS"), "pass_count mismatch", errors)
    require(
        summary.get("deferred_count") == sum(1 for entry in items if str(entry.get("status", "")).startswith("DEFERRED")),
        "deferred_count mismatch",
        errors,
    )
    require(
        summary.get("pending_human_count") == sum(1 for entry in items if entry.get("status") == "PENDING_HUMAN"),
        "pending_human_count mismatch",
        errors,
    )
    expected_next_hardware_gate = "wba_real_panel_parity" if is_wb55_runtime_recheck_proven() else RUNTIME_GATE_ID
    require(
        summary.get("next_hardware_gate") == expected_next_hardware_gate,
        f"next_hardware_gate must point at {expected_next_hardware_gate}",
        errors,
    )
    require(
        summary.get("next_human_gate") == "wb55_touch_visual_acceptance",
        "next_human_gate must point at WB55 touch visual acceptance",
        errors,
    )


def check_docs(errors: list[str]) -> None:
    require(SCREEN_DOC.exists(), "missing screen expression system doc", errors)
    require(WBA_RULES.exists(), "missing WBA migration rules", errors)
    if SCREEN_DOC.exists():
        text = SCREEN_DOC.read_text(encoding="utf-8")
        for token in [
            "Acceptance Index",
            "companion-screen-acceptance-index.json",
            "companion-screen-acceptance-report.md",
            "render_expression_acceptance_report.py",
            "expression-storyboard.svg",
            "companion-screen-expression-storyboard.json",
            "render_expression_storyboard.py",
            "expression_visual_contract",
            "Expression visual contract",
            "companion-screen-expression-visual-contract.json",
            "verify_expression_visual_contract.py",
            "visually duplicate faces",
            "expression_visual_acceptance_matrix",
            "Expression visual acceptance matrix",
            "companion-screen-expression-visual-acceptance-matrix.json",
            "companion-screen-expression-visual-acceptance-matrix.md",
            "render_expression_visual_acceptance_matrix.py",
            "expression_layout_contract",
            "Expression layout contract",
            "companion-screen-expression-layout-contract.json",
            "verify_expression_layout_contract.py",
            "title/body/footer",
            "screen_acceptance_runner",
            "companion-screen-acceptance-runner.json",
            "verify_expression_acceptance_runner.py",
            "run_expression_acceptance.py",
            "screen_feature_roadmap",
            "companion-screen-feature-roadmap.json",
            "verify_expression_feature_roadmap.py",
            "screen_feature_checklist",
            "companion-screen-feature-checklist.json",
            "companion-screen-feature-checklist.md",
            "render_expression_feature_checklist.py",
            "screen_expression_demo_sequence",
            "Screen expression demo sequence",
            "companion-screen-expression-demo-sequence.json",
            "companion-screen-expression-demo-sequence.md",
            "verify_expression_demo_sequence.py",
            "screen_expression_demo_panel_handoff",
            "Screen expression demo panel handoff",
            "companion-screen-expression-demo-panel-handoff.json",
            "companion-screen-expression-demo-panel-handoff.md",
            "verify_expression_demo_panel_handoff.py",
            "manual_visual_required_faces",
            "Panel driver readiness",
            "companion-screen-panel-hardware-gate.json",
            "companion-screen-status-observability.json",
            "companion-screen-settings-policy.json",
            "DEFERRED_HARDWARE",
            "screen_status_observability",
            "host_ble_expression_status_fixture",
            "host_ble_expression_extended_status_fixture",
            "Host BLE ExpressionV1 extended status coverage",
            "host_expression_status_extended_faces",
            "host_ble_expression_status_sequence",
            "Host BLE ExpressionV1 status sequence integrity",
            "host_expression_status_sequence_integrity",
            "companion-screen-expression-host-status-sequence.json",
            "expression_host_manifest",
            "ExpressionV1 host manifest",
            "companion-screen-expression-host-manifest.json",
            "companion-screen-expression-host-manifest.md",
            "render_expression_host_manifest.py",
            "screen_expression_demo_host_status_sequence",
            "Screen expression demo host status sequence",
            "screen_expression_demo_status",
            "companion-screen-expression-demo-host-status-sequence.json",
            "verify_expression_demo_host_status_sequence.py",
            "held_steps_emit_no_host_status",
            "display_queue_fault_paths",
            "display_queue_telemetry",
            "Display queue telemetry",
            "companion-screen-display-queue-telemetry.json",
            "verify_display_queue_telemetry.py",
            "high-water",
            "stats snapshot",
            "companion-screen-display-queue-faults.json",
            "expression_state_rolls_back_on_enqueue_failure",
            "screen_expression_status",
            "screen_settings_expression_policy",
            "expression_catalog_contract",
            "ExpressionV1 catalog contract",
            "expression_copy_contract",
            "ExpressionV1 copy contract",
            "companion-screen-expression-copy-contract.json",
            "verify_expression_copy_contract.py",
            "expression_unknown_signal_guard",
            "Expression unknown signal guard",
            "companion-screen-expression-signal-guard.json",
            "comp_epaper_expression_signal_is_supported",
            "expression_state_telemetry_snapshot",
            "Expression state telemetry snapshot",
            "companion-screen-expression-state-telemetry.json",
            "verify_expression_state_telemetry.py",
            "comp_epaper_expression_state_snapshot",
            "companion-screen-expression-catalog.json",
            "verify_expression_catalog_contract.py",
            "stable numeric IDs",
            "(expression_id << 16) | signal_id",
            "expression_duplicate_refresh_suppression",
            "expression_transient_auto_recovery",
            "wb55_expression_tick_scheduler",
            "wb55_settings_expression_hint",
            "wb55_device_status_expression_hint",
            "wb55_interaction_status_expression_hint",
            "wb55_battery_expression_hint",
            "battery_recovery_expression_guard",
            "Battery recovery expression guard",
            "COMP_EPAPER_EXPRESSION_SIGNAL_BATTERY_RECOVERED",
            "recording_state_expression_hook",
            "Recording FSM state expression hook",
            "companion-screen-recording-state-expression-hook.json",
            "comp_epaper_expression_signal_from_recording_state",
            "wb55_ota_readiness_expression_hint",
            "companion-screen-device-status-expression-hook.json",
            "companion-screen-interaction-status-expression-hook.json",
            "companion-screen-battery-expression-hook.json",
            "companion-screen-ota-expression-hook.json",
            "device_status_publish_feeds_expression_bridge",
            "interaction_status_publish_feeds_expression_bridge",
            "battery_charge_publish_feeds_expression_bridge",
            "battery_recovery_only_clears_low_battery",
            "ota_readiness_publish_feeds_expression_bridge",
            "settings_sleepy_hint_does_not_hide_recording",
            "duplicate_same_expression_suppressed",
            "status_notify_duplicate_suppression",
            "transient_auto_recovery_to_idle",
            "stable_recording_does_not_timeout",
            "panel_target_ops_boundary",
            "Panel adapter target-ops boundary",
            "companion-screen-panel-adapter-boundary.json",
            "verify_expression_panel_adapter_boundary.py",
            "comp_epaper_panel_refresh_fn_t",
            "wb55_panel_target_adapter_scaffold",
            "WB55 panel target adapter scaffold",
            "companion-screen-panel-target-stm32wb.json",
            "verify_expression_panel_target_stm32wb.py",
            "panel_target_stm32wb",
            "companion_epaper_panel_stm32wb_init",
            "panel_adapter_behavior_matrix",
            "companion-screen-panel-adapter-behavior.json",
            "verify_expression_panel_adapter_behavior.py",
            "callback_busy_maps_to_busy_without_error_counter",
            "dispatcher_owns_request_identity",
            "panel_adapter_telemetry_snapshot",
            "Panel adapter telemetry snapshot",
            "companion-screen-panel-adapter-telemetry.json",
            "verify_expression_panel_adapter_telemetry.py",
            "comp_epaper_panel_adapter_snapshot",
            "screen_runtime_snapshot",
            "Screen runtime snapshot",
            "companion-screen-runtime-snapshot.json",
            "verify_expression_screen_runtime_snapshot.py",
            "comp_epaper_screen_runtime_snapshot",
            "screen_runtime_diagnostics",
            "Screen runtime diagnostics",
            "companion-screen-runtime-diagnostics.json",
            "verify_expression_screen_runtime_diagnostics.py",
            "e_paper.runtime_snapshot",
            "screen_runtime_diagnostic_decode",
            "Screen runtime diagnostic decode",
            "companion-screen-runtime-diagnostic-decode.json",
            "verify_expression_screen_runtime_diagnostic_decode.py",
            "decoded_args",
            "screen_runtime_diagnostics_bundle",
            "Screen runtime diagnostics bundle",
            "collect_companion_diagnostics.ps1",
            "verify_companion_diagnostics_static.py",
            "runtime_snapshot_decoded",
            "real_ble_screen_final_status_bench",
            "companion-screen-real-ble-bench.json",
            "verify_expression_real_ble_screen_bench.py",
            "settings_sleepy_screen_status",
            "final_card_status",
            "real_panel_refresh_claimed",
            "--expect-real-panel",
            "real_ble_expression_status_sequence_contract",
            "screen_expression_status",
            "companion-screen-expression-host-status-sequence.json",
            "panel_hardware_evidence_template",
            "companion-screen-panel-evidence-template.json",
            "verify_expression_panel_evidence_template.py",
            "panel_evidence_runtime_diagnostics",
            "Panel evidence runtime diagnostics",
            "e_paper.runtime_snapshot decoded_args show zero panel errors",
            "panel_evidence_diagnostics_bundle_validator",
            "Panel evidence diagnostics bundle validator",
            "diagnostics_bundle_artifact",
            "epaper.runtime_snapshot_decoded",
            "panel_evidence_record_validator",
            "init_expression_panel_evidence_record.py",
            "companion-screen-panel-evidence-record-scaffold.json",
            "companion-screen-panel-evidence-record-validator.json",
            "verify_expression_panel_evidence_record.py",
            "real_ble_bench_artifact",
            "panel_evidence_real_ble_sequence_validator",
            "Panel evidence real BLE sequence validator",
            "screen_expression_status",
            "screen_expression_demo_status",
            "companion-screen-expression-host-status-sequence.json",
            "companion-screen-expression-demo-host-status-sequence.json",
            "panel_hardware_acceptance_plan",
            "Panel hardware acceptance plan",
            "companion-screen-panel-hardware-acceptance-plan.json",
            "verify_expression_panel_hardware_acceptance_plan.py",
            "companion-screen-wba-port-contract.json",
            "wba_port_scaffold",
            "WBA port scaffold",
            "companion-screen-wba55-port-scaffold.json",
            "init_expression_wba_port_scaffold.py",
            "wba_cube_dependency_preflight",
            "WBA CubeWBA dependency preflight",
            "companion-screen-wba-cube-dependency-preflight.json",
            "verify_expression_wba_cube_dependency_preflight.py",
            "third_party/STM32CubeWBA",
            "wba_panel_target_adapter_scaffold",
            "WBA panel target adapter scaffold",
            "panel_target_stm32wba",
            "companion_epaper_panel_stm32wba_init",
            "companion-screen-panel-target-stm32wba.json",
            "verify_expression_panel_target_stm32wba.py",
            "wba_display_scheduler_scaffold",
            "WBA display scheduler scaffold",
            "screen_scheduler_stm32wba",
            "companion_epaper_stm32wba_schedule_expression_tick",
            "companion-screen-scheduler-stm32wba.json",
            "verify_expression_screen_scheduler_stm32wba.py",
            "wba_screen_gatt_scaffold",
            "WBA screen GATT scaffold",
            "screen_gatt_stm32wba",
            "companion_epaper_stm32wba_screen_gatt_accept_card_write",
            "companion-screen-gatt-stm32wba.json",
            "verify_expression_screen_gatt_stm32wba.py",
            "wba_screen_assets_scaffold",
            "WBA screen-assets scaffold",
            "screen_assets_stm32wba",
            "companion-screen-assets-stm32wba.json",
            "verify_expression_screen_assets_stm32wba.py",
            "wba_pet_behavior_user_data_scaffold",
            "WBA pet behavior user-data scaffold",
            "pet_behavior_user_data_stm32wba",
            "companion-screen-pet-behavior-user-data-stm32wba.json",
            "verify_pet_behavior_user_data_stm32wba.py",
            "target_capability_profile",
            "Target capability profile",
            "companion-screen-target-capabilities.json",
            "verify_expression_target_capabilities.py",
            "devboard_ioc_screen_preflight",
            "Devboard IOC screen preflight",
            "companion-devboard-ioc-import.json",
            "verify_devboard_ioc_import.py",
            "panel_wiring_preflight",
            "Panel wiring preflight",
            "companion-screen-panel-wiring-preflight.json",
            "verify_expression_panel_wiring_preflight.py",
            "panel_evidence_scaffold_wiring_prefill",
            "Panel evidence scaffold wiring prefill",
            "companion-screen-panel-evidence-record-scaffold.json",
            "panel_hardware_session_scaffold",
            "Panel hardware session scaffold",
            "companion-screen-panel-hardware-session.json",
            "verify_expression_panel_hardware_session.py",
            "companion-real-panel-wb55-<timestamp>",
            "operator-notes.md",
            "panel_session_directory_preflight",
            "Panel session directory preflight",
            "companion-screen-panel-session-directory-preflight.json",
            "verify_expression_panel_session_directory.py",
            "DRAFT_UNFILLED",
            "panel_hardware_facts_intake",
            "Panel hardware facts intake",
            "companion-screen-panel-hardware-facts-intake.json",
            "verify_expression_panel_hardware_facts.py",
            "panel-hardware-facts.todo.json",
            "READY_FOR_DRIVER_FACTS",
            "panel_hardware_facts_worksheet",
            "Panel hardware facts worksheet",
            "companion-screen-panel-facts-worksheet.json",
            "companion-screen-panel-facts-worksheet.md",
            "render_expression_panel_facts_worksheet.py",
            "panel_bringup_operator_packet",
            "Panel bring-up operator packet",
            "companion-screen-panel-bringup-operator-packet.json",
            "companion-screen-panel-bringup-operator-packet.md",
            "render_expression_panel_bringup_packet.py",
            "panel_driver_readiness_report",
            "Panel driver readiness report",
            "companion-screen-panel-driver-readiness.json",
            "verify_expression_panel_driver_readiness.py",
            "BLOCKED_ON_HARDWARE_FACTS",
            "READY_FOR_DRIVER_IMPLEMENTATION",
            "panel_hardware_facts_bridge",
            "Panel hardware facts bridge",
            "companion-screen-panel-hardware-facts-bridge.json",
            "apply_expression_panel_hardware_facts.py",
            "wb55_boot_idle_expression",
            "wb55_real_panel_refresh",
        ]:
            require(token in text, f"screen doc missing acceptance index anchor {token}", errors)
    if WBA_RULES.exists():
        text = WBA_RULES.read_text(encoding="utf-8")
        require("Current Screen Adapter Split" in text, "WBA rules missing current screen adapter split", errors)


def check_fixture_file(path: pathlib.Path, expected: dict[str, Any], errors: list[str]) -> None:
    require(path.exists(), f"missing acceptance index fixture: {rel(path)}", errors)
    if not path.exists():
        return
    actual = json.loads(path.read_text(encoding="utf-8"))
    require(actual == expected, f"{rel(path)} is stale; rerun with --write-fixture", errors)


def parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--fixture", type=pathlib.Path, default=DEFAULT_FIXTURE)
    parser.add_argument("--write-fixture", action="store_true", help="Update the deterministic acceptance index JSON.")
    return parser.parse_args(argv)


def main(argv: list[str]) -> int:
    args = parse_args(argv)
    fixture_path = REPO_ROOT / args.fixture
    errors: list[str] = []
    expected = build_index()
    check_index(expected, errors)
    check_docs(errors)

    if args.write_fixture and not errors:
        fixture_path.parent.mkdir(parents=True, exist_ok=True)
        fixture_path.write_text(json.dumps(expected, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    if not args.write_fixture:
        check_fixture_file(fixture_path, expected, errors)

    if errors:
        print("FAIL: Companion screen acceptance index checks failed:", file=sys.stderr)
        for error in errors:
            print(f" - {error}", file=sys.stderr)
        return 1
    print(f"PASS: Companion screen acceptance index verified -> {rel(fixture_path)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
