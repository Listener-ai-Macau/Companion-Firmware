#!/usr/bin/env python3
"""Verify ExpressionV1 code stays portable for a future STM32WBA port."""

from __future__ import annotations

import argparse
import json
import pathlib
import re
import subprocess
import sys
from typing import Any


REPO_ROOT = pathlib.Path(__file__).resolve().parents[1]
DEFAULT_FIXTURE = pathlib.Path("docs/validation/companion-screen-wba-port-contract.json")
SCHEMA_ID = "companion.pendant.screen_wba_port_contract.v1"
EPAPER_ROOT = REPO_ROOT / "app" / "companion_pendant" / "epaper"
TOUCH_ROOT = REPO_ROOT / "app" / "companion_pendant" / "touch"
SCREEN_DOC = REPO_ROOT / "docs" / "companion_screen_expression_system.md"
WBA_RULES = REPO_ROOT / "docs" / "stm32wba_migration_rules.md"
DISPLAY_QUEUE_STATIC = REPO_ROOT / "tools" / "verify_display_queue_static.py"
DISPLAY_DRAIN_VERIFIER = REPO_ROOT / "tools" / "verify_expression_display_drain.py"
DISPLAY_DRAIN_CONTRACT = REPO_ROOT / "docs" / "validation" / "companion-screen-display-drain-contract.json"
TARGET_CAPABILITY_VERIFIER = REPO_ROOT / "tools" / "verify_expression_target_capabilities.py"
TARGET_CAPABILITY_CONTRACT = REPO_ROOT / "docs" / "validation" / "companion-screen-target-capabilities.json"
SCREEN_RUNTIME_VERIFIER = REPO_ROOT / "tools" / "verify_expression_screen_runtime_snapshot.py"
SCREEN_RUNTIME_DIAGNOSTICS_VERIFIER = REPO_ROOT / "tools" / "verify_expression_screen_runtime_diagnostics.py"
SCREEN_RUNTIME_DIAG_DECODE_VERIFIER = REPO_ROOT / "tools" / "verify_expression_screen_runtime_diagnostic_decode.py"
EXPRESSION_CATALOG_VERIFIER = REPO_ROOT / "tools" / "verify_expression_catalog_contract.py"
EXPRESSION_CATALOG = REPO_ROOT / "docs" / "validation" / "companion-screen-expression-catalog.json"
EXPRESSION_COPY_CONTRACT_VERIFIER = REPO_ROOT / "tools" / "verify_expression_copy_contract.py"
EXPRESSION_COPY_CONTRACT = REPO_ROOT / "docs" / "validation" / "companion-screen-expression-copy-contract.json"
EXPRESSION_VISUAL_CONTRACT_VERIFIER = REPO_ROOT / "tools" / "verify_expression_visual_contract.py"
EXPRESSION_VISUAL_CONTRACT = REPO_ROOT / "docs" / "validation" / "companion-screen-expression-visual-contract.json"
GENERATED_ART_STYLE_VERIFIER = REPO_ROOT / "tools" / "render_generated_art_style_contract.py"
GENERATED_ART_STYLE_CONTRACT = REPO_ROOT / "docs" / "validation" / "companion-screen-generated-art-style-contract.json"
GENERATED_ART_STYLE_DOC = REPO_ROOT / "docs" / "validation" / "companion-screen-generated-art-style-contract.md"
GENERATED_ART_PROFILE_PORTABILITY_VERIFIER = REPO_ROOT / "tools" / "verify_generated_expression_sheet_profile_portability.py"
GENERATED_ART_PROFILE_PORTABILITY_CONTRACT = REPO_ROOT / "docs" / "validation" / "companion-screen-generated-art-profile-portability.json"
EXPRESSION_LAYOUT_CONTRACT_VERIFIER = REPO_ROOT / "tools" / "verify_expression_layout_contract.py"
EXPRESSION_LAYOUT_CONTRACT = REPO_ROOT / "docs" / "validation" / "companion-screen-expression-layout-contract.json"
EXPRESSION_PRIORITY_MATRIX_VERIFIER = REPO_ROOT / "tools" / "verify_expression_priority_matrix.py"
EXPRESSION_PRIORITY_MATRIX = REPO_ROOT / "docs" / "validation" / "companion-screen-expression-priority-matrix.json"
EXPRESSION_INPUT_SOURCE_MATRIX_VERIFIER = REPO_ROOT / "tools" / "verify_expression_input_source_matrix.py"
EXPRESSION_INPUT_SOURCE_MATRIX = REPO_ROOT / "docs" / "validation" / "companion-screen-expression-input-source-matrix.json"
EXPRESSION_SIGNAL_GUARD_VERIFIER = REPO_ROOT / "tools" / "verify_expression_signal_guard.py"
EXPRESSION_RECORDING_STATE_VERIFIER = REPO_ROOT / "tools" / "verify_expression_recording_state_hook.py"
EXPRESSION_HOST_STATUS_SEQUENCE_VERIFIER = REPO_ROOT / "tools" / "verify_expression_host_status_sequence.py"
WBA_PORT_SCAFFOLD_TOOL = REPO_ROOT / "tools" / "init_expression_wba_port_scaffold.py"
WBA55_PORT_SCAFFOLD = REPO_ROOT / "docs" / "validation" / "companion-screen-wba55-port-scaffold.json"
WBA_CUBE_DEPENDENCY_VERIFIER = REPO_ROOT / "tools" / "verify_expression_wba_cube_dependency_preflight.py"
WBA_CUBE_DEPENDENCY_CONTRACT = REPO_ROOT / "docs" / "validation" / "companion-screen-wba-cube-dependency-preflight.json"
WBA_REAL_PARITY_GATE_VERIFIER = REPO_ROOT / "tools" / "verify_expression_wba_real_parity_gate.py"
WBA_REAL_PARITY_GATE = REPO_ROOT / "docs" / "validation" / "companion-screen-wba-real-parity-gate.json"
WBA_LSE_CLOCK_VERIFIER = REPO_ROOT / "tools" / "verify_expression_wba_lse_clock_contract.py"
WBA_LSE_CLOCK_CONTRACT = REPO_ROOT / "docs" / "validation" / "companion-screen-wba-lse-clock-contract.json"
WBA_ADAPTER_M33_COMPILE_VERIFIER = REPO_ROOT / "tools" / "verify_wba_adapter_m33_compile.py"
WBA_ADAPTER_M33_COMPILE_CONTRACT = (
    REPO_ROOT / "docs" / "validation" / "companion-screen-wba-adapter-m33-compile.json"
)
V9_BASELINE = REPO_ROOT / "docs" / "art" / "iterations" / "companion-pet-expression-v9" / "baseline-lock.json"
V9_WBA_VISUAL_BOUNDARY = REPO_ROOT / "docs" / "validation" / "companion-v9-wba-visual-boundary-20260717.json"
WBA_V9_CALLBACK_REPLAY = REPO_ROOT / "docs" / "validation" / "companion-wba-v9-cemp-callback-replay-20260717.json"
V9_SHA256 = "919F344957661DEF2099AD56AB1286CCA9DBA4D8F08B702617B6DF5B1A28E9DA"
APP_BLE = REPO_ROOT / "cubeide" / "Companion_Nucleo_WB55RG_Bringup" / "Core" / "Src" / "app_ble.c"
MAKEFILE = REPO_ROOT / "cubeide" / "Companion_Nucleo_WB55RG_Bringup" / "Makefile"
PANEL_TARGET_STM32WB_HEADER = EPAPER_ROOT / "panel_target_stm32wb.h"
PANEL_TARGET_STM32WB_SOURCE = EPAPER_ROOT / "panel_target_stm32wb.c"
PANEL_TARGET_STM32WBA_HEADER = EPAPER_ROOT / "panel_target_stm32wba.h"
PANEL_TARGET_STM32WBA_SOURCE = EPAPER_ROOT / "panel_target_stm32wba.c"
PANEL_TARGET_STM32WBA_VERIFIER = REPO_ROOT / "tools" / "verify_expression_panel_target_stm32wba.py"
PANEL_TARGET_STM32WBA_CONTRACT = REPO_ROOT / "docs" / "validation" / "companion-screen-panel-target-stm32wba.json"
SCREEN_SCHEDULER_STM32WBA_HEADER = EPAPER_ROOT / "screen_scheduler_stm32wba.h"
SCREEN_SCHEDULER_STM32WBA_SOURCE = EPAPER_ROOT / "screen_scheduler_stm32wba.c"
SCREEN_SCHEDULER_STM32WBA_VERIFIER = REPO_ROOT / "tools" / "verify_expression_screen_scheduler_stm32wba.py"
SCREEN_SCHEDULER_STM32WBA_CONTRACT = REPO_ROOT / "docs" / "validation" / "companion-screen-scheduler-stm32wba.json"
SCREEN_GATT_STM32WBA_HEADER = EPAPER_ROOT / "screen_gatt_stm32wba.h"
SCREEN_GATT_STM32WBA_SOURCE = EPAPER_ROOT / "screen_gatt_stm32wba.c"
SCREEN_GATT_STM32WBA_VERIFIER = REPO_ROOT / "tools" / "verify_expression_screen_gatt_stm32wba.py"
SCREEN_GATT_STM32WBA_CONTRACT = REPO_ROOT / "docs" / "validation" / "companion-screen-gatt-stm32wba.json"
SCREEN_ASSETS_STM32WBA_HEADER = EPAPER_ROOT / "screen_assets_stm32wba.h"
SCREEN_ASSETS_STM32WBA_SOURCE = EPAPER_ROOT / "screen_assets_stm32wba.c"
SCREEN_ASSETS_STM32WBA_VERIFIER = REPO_ROOT / "tools" / "verify_expression_screen_assets_stm32wba.py"
SCREEN_ASSETS_STM32WBA_CONTRACT = REPO_ROOT / "docs" / "validation" / "companion-screen-assets-stm32wba.json"
TOUCH_TARGET_STM32WBA_HEADER = TOUCH_ROOT / "touch_target_stm32wba_ft6336.h"
TOUCH_TARGET_STM32WBA_SOURCE = TOUCH_ROOT / "touch_target_stm32wba_ft6336.c"
TOUCH_TARGET_STM32WBA_VERIFIER = REPO_ROOT / "tools" / "verify_touch_target_stm32wba_ft6336.py"
TOUCH_TARGET_STM32WBA_CONTRACT = REPO_ROOT / "docs" / "validation" / "companion-screen-touch-ft6336-stm32wba.json"
PET_BEHAVIOR_USER_DATA_STM32WBA_HEADER = EPAPER_ROOT / "pet_behavior_user_data_stm32wba.h"
PET_BEHAVIOR_USER_DATA_STM32WBA_SOURCE = EPAPER_ROOT / "pet_behavior_user_data_stm32wba.c"
PET_BEHAVIOR_USER_DATA_STM32WBA_VERIFIER = REPO_ROOT / "tools" / "verify_pet_behavior_user_data_stm32wba.py"
PET_BEHAVIOR_USER_DATA_STM32WBA_CONTRACT = REPO_ROOT / "docs" / "validation" / "companion-screen-pet-behavior-user-data-stm32wba.json"

PORTABLE_FILES = [
    EPAPER_ROOT / "__init__.py",
    EPAPER_ROOT / "asset_store.c",
    EPAPER_ROOT / "asset_store.h",
    EPAPER_ROOT / "card_renderer.py",
    EPAPER_ROOT / "display_queue.c",
    EPAPER_ROOT / "display_queue.h",
    EPAPER_ROOT / "emote_asset_pack.c",
    EPAPER_ROOT / "emote_asset_pack.h",
    EPAPER_ROOT / "emote_player.c",
    EPAPER_ROOT / "emote_player.h",
    EPAPER_ROOT / "expression_asset_source.c",
    EPAPER_ROOT / "expression_asset_source.h",
    EPAPER_ROOT / "expression_events.c",
    EPAPER_ROOT / "expression_events.h",
    EPAPER_ROOT / "expression_policy.py",
    EPAPER_ROOT / "expression_state.c",
    EPAPER_ROOT / "expression_state.h",
    EPAPER_ROOT / "panel_adapter.c",
    EPAPER_ROOT / "panel_adapter.h",
    EPAPER_ROOT / "refresh_policy.c",
    EPAPER_ROOT / "refresh_policy.h",
    EPAPER_ROOT / "pet_attention.c",
    EPAPER_ROOT / "pet_attention.h",
    EPAPER_ROOT / "pet_behavior.c",
    EPAPER_ROOT / "pet_behavior.h",
    EPAPER_ROOT / "pet_expression.c",
    EPAPER_ROOT / "pet_expression.h",
    EPAPER_ROOT / "pet_performance.c",
    EPAPER_ROOT / "pet_performance.h",
    EPAPER_ROOT / "pet_performance_event_bridge.c",
    EPAPER_ROOT / "pet_performance_event_bridge.h",
    EPAPER_ROOT / "v9_candidate_resource_binding.c",
    EPAPER_ROOT / "v9_candidate_resource_binding.h",
    EPAPER_ROOT / "pet_visual_style.h",
    EPAPER_ROOT / "screen_framebuffer.c",
    EPAPER_ROOT / "screen_framebuffer.h",
    EPAPER_ROOT / "screen_menu.c",
    EPAPER_ROOT / "screen_menu.h",
    EPAPER_ROOT / "screen_presentation.c",
    EPAPER_ROOT / "screen_presentation.h",
    EPAPER_ROOT / "screen_runtime.c",
    EPAPER_ROOT / "screen_runtime.h",
    TOUCH_ROOT / "ft6336.c",
    TOUCH_ROOT / "ft6336.h",
    TOUCH_ROOT / "touch_gesture.c",
    TOUCH_ROOT / "touch_gesture.h",
]

FORBIDDEN_PORTABLE_PATTERNS = {
    "stm32 family token": re.compile(r"\bstm32\w*\b", re.IGNORECASE),
    "STM32 HAL": re.compile(r"\bHAL_[A-Za-z0-9_]+"),
    "STM32_WPAN": re.compile(r"\bSTM32_?WPAN\b", re.IGNORECASE),
    "Cube generated app header": re.compile(r'#\s*include\s+"(?:main|app_conf|app_ble)\.h"'),
    "GPIO pin macro": re.compile(r"\bGPIO(?:[A-Z]|\b)|\bGPIO_PIN_\w+"),
    "WB wireless split": re.compile(r"\b(?:CPU2|FUS|IPCC|HSEM|BLE_p2pServer)\b"),
    "board peripheral instance": re.compile(r"\b(?:QSPI|I2C[0-9]?|SAI[0-9]?|UART[0-9]?|USART[0-9]?|SPI[0-9]?)\b"),
    "sequencer": re.compile(r"\bUTIL_SEQ\b"),
}


def rel(path: pathlib.Path) -> str:
    try:
        return path.resolve().relative_to(REPO_ROOT).as_posix()
    except ValueError:
        return path.as_posix()


def read(path: pathlib.Path) -> str:
    return path.read_text(encoding="utf-8")


def require(condition: bool, message: str, errors: list[str]) -> None:
    if not condition:
        errors.append(message)


def build_fixture() -> dict[str, Any]:
    return {
        "schema_id": SCHEMA_ID,
        "status": "PASS",
        "purpose": "Machine-readable pre-port contract for moving the Companion screen expression layer from WB55 to WBA55/WBA65.",
        "targets": {
            "baseline": "STM32WBA55",
            "expanded": "STM32WBA65",
            "rule": "Design to WBA55-safe protocol, queue, and memory limits unless a target capability explicitly enables expansion.",
        },
        "sources": {
            "wba_rules": rel(WBA_RULES),
            "screen_acceptance": rel(SCREEN_DOC),
            "wba_portability_verifier": "tools/verify_expression_wba_portability.py",
            "expression_catalog": rel(EXPRESSION_CATALOG),
            "expression_catalog_verifier": rel(EXPRESSION_CATALOG_VERIFIER),
            "expression_copy_contract": rel(EXPRESSION_COPY_CONTRACT),
            "expression_copy_contract_verifier": rel(EXPRESSION_COPY_CONTRACT_VERIFIER),
            "expression_visual_contract": rel(EXPRESSION_VISUAL_CONTRACT),
            "expression_visual_contract_verifier": rel(EXPRESSION_VISUAL_CONTRACT_VERIFIER),
            "generated_art_style_contract": rel(GENERATED_ART_STYLE_CONTRACT),
            "generated_art_style_verifier": rel(GENERATED_ART_STYLE_VERIFIER),
            "generated_art_style_doc": rel(GENERATED_ART_STYLE_DOC),
            "generated_art_profile_portability_contract": rel(GENERATED_ART_PROFILE_PORTABILITY_CONTRACT),
            "generated_art_profile_portability_verifier": rel(GENERATED_ART_PROFILE_PORTABILITY_VERIFIER),
            "expression_layout_contract": rel(EXPRESSION_LAYOUT_CONTRACT),
            "expression_layout_contract_verifier": rel(EXPRESSION_LAYOUT_CONTRACT_VERIFIER),
            "expression_priority_matrix": rel(EXPRESSION_PRIORITY_MATRIX),
            "expression_priority_matrix_verifier": rel(EXPRESSION_PRIORITY_MATRIX_VERIFIER),
            "expression_input_source_matrix": rel(EXPRESSION_INPUT_SOURCE_MATRIX),
            "expression_input_source_matrix_verifier": rel(EXPRESSION_INPUT_SOURCE_MATRIX_VERIFIER),
            "expression_signal_guard_verifier": rel(EXPRESSION_SIGNAL_GUARD_VERIFIER),
            "expression_recording_state_verifier": rel(EXPRESSION_RECORDING_STATE_VERIFIER),
            "expression_host_status_sequence_verifier": rel(EXPRESSION_HOST_STATUS_SEQUENCE_VERIFIER),
            "wba_port_scaffold_tool": rel(WBA_PORT_SCAFFOLD_TOOL),
            "wba55_port_scaffold": rel(WBA55_PORT_SCAFFOLD),
            "wba_cube_dependency_preflight": rel(WBA_CUBE_DEPENDENCY_CONTRACT),
            "wba_cube_dependency_verifier": rel(WBA_CUBE_DEPENDENCY_VERIFIER),
            "wba_real_parity_gate": rel(WBA_REAL_PARITY_GATE),
            "wba_real_parity_gate_verifier": rel(WBA_REAL_PARITY_GATE_VERIFIER),
            "wba_lse_clock_contract": rel(WBA_LSE_CLOCK_CONTRACT),
            "wba_lse_clock_verifier": rel(WBA_LSE_CLOCK_VERIFIER),
            "wba_adapter_m33_compile_contract": rel(WBA_ADAPTER_M33_COMPILE_CONTRACT),
            "wba_adapter_m33_compile_verifier": rel(WBA_ADAPTER_M33_COMPILE_VERIFIER),
            "v9_baseline": rel(V9_BASELINE),
            "v9_wba_visual_boundary": rel(V9_WBA_VISUAL_BOUNDARY),
            "wba_v9_callback_replay": rel(WBA_V9_CALLBACK_REPLAY),
            "display_queue_verifier": rel(DISPLAY_QUEUE_STATIC),
            "display_drain_contract": rel(DISPLAY_DRAIN_CONTRACT),
            "display_drain_verifier": rel(DISPLAY_DRAIN_VERIFIER),
            "target_capability_profile": rel(TARGET_CAPABILITY_CONTRACT),
            "target_capability_verifier": rel(TARGET_CAPABILITY_VERIFIER),
            "screen_runtime_verifier": rel(SCREEN_RUNTIME_VERIFIER),
            "screen_runtime_diagnostics_verifier": rel(SCREEN_RUNTIME_DIAGNOSTICS_VERIFIER),
            "screen_runtime_diagnostic_decode_verifier": rel(SCREEN_RUNTIME_DIAG_DECODE_VERIFIER),
            "wb55_panel_target_adapter": rel(PANEL_TARGET_STM32WB_SOURCE),
            "wba_panel_target_adapter_scaffold": rel(PANEL_TARGET_STM32WBA_SOURCE),
            "wba_panel_target_adapter_verifier": rel(PANEL_TARGET_STM32WBA_VERIFIER),
            "wba_panel_target_adapter_contract": rel(PANEL_TARGET_STM32WBA_CONTRACT),
            "wba_display_scheduler_scaffold": rel(SCREEN_SCHEDULER_STM32WBA_SOURCE),
            "wba_display_scheduler_verifier": rel(SCREEN_SCHEDULER_STM32WBA_VERIFIER),
            "wba_display_scheduler_contract": rel(SCREEN_SCHEDULER_STM32WBA_CONTRACT),
            "wba_screen_gatt_scaffold": rel(SCREEN_GATT_STM32WBA_SOURCE),
            "wba_screen_gatt_verifier": rel(SCREEN_GATT_STM32WBA_VERIFIER),
            "wba_screen_gatt_contract": rel(SCREEN_GATT_STM32WBA_CONTRACT),
            "wba_screen_assets_scaffold": rel(SCREEN_ASSETS_STM32WBA_SOURCE),
            "wba_screen_assets_verifier": rel(SCREEN_ASSETS_STM32WBA_VERIFIER),
            "wba_screen_assets_contract": rel(SCREEN_ASSETS_STM32WBA_CONTRACT),
            "wba_touch_target_scaffold": rel(TOUCH_TARGET_STM32WBA_SOURCE),
            "wba_touch_target_verifier": rel(TOUCH_TARGET_STM32WBA_VERIFIER),
            "wba_touch_target_contract": rel(TOUCH_TARGET_STM32WBA_CONTRACT),
            "wba_pet_behavior_user_data_scaffold": rel(PET_BEHAVIOR_USER_DATA_STM32WBA_SOURCE),
            "wba_pet_behavior_user_data_verifier": rel(PET_BEHAVIOR_USER_DATA_STM32WBA_VERIFIER),
            "wba_pet_behavior_user_data_contract": rel(PET_BEHAVIOR_USER_DATA_STM32WBA_CONTRACT),
            "wb55_glue": rel(APP_BLE),
            "wb55_build": rel(MAKEFILE),
        },
        "portable_screen_files": [rel(path) for path in PORTABLE_FILES],
        "forbidden_in_portable_files": sorted(FORBIDDEN_PORTABLE_PATTERNS.keys()),
        "portable_contracts": {
            "expression_states": [
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
            ],
            "display_queue_depth": 4,
            "display_payload_max_bytes": 236,
            "display_queue_telemetry": "pending_count/high_water_count/dropped_count/next_sequence stats snapshot stays portable and platform-free.",
            "display_generation_hygiene": "WBA adapters inherit portable display_queue generation hygiene: active_resource_revision/resource_revision tag every request, comp_epaper_display_queue_set_resource_revision drains or discards stale queued requests, generation_switch_count/stale_generation_discard_count/last_stale_generation_discarded stay observable, and the first WBA ui_assets activation frame must log coherent_generation=1 with generation_switches and last_stale_discarded before visual review.",
            "display_drain_contract": "tools/verify_expression_display_drain.py guards one-request-per-pass display drain, target panel refresh, runtime diagnostics before final CardStatusV1, and pending-work reschedule behavior.",
            "target_capability_profile": "tools/verify_expression_target_capabilities.py keeps WB55 as the validation target, WBA55 as the shared safe baseline, and WBA65 expansion behind explicit target capability flags without changing common screen limits.",
            "expression_state_telemetry": "comp_epaper_expression_state_snapshot exposes current/last_signal/visible_age_ms/auto_recover_ms/suppressed_duplicate_count stats without target dependencies.",
            "signal_preflight_api": "comp_epaper_expression_signal_is_supported rejects unsupported or future ExpressionV1 signals before visible state, duplicate counters, display queue work, or CardStatusV1 request identity changes.",
            "recording_state_mapper": "comp_epaper_expression_signal_from_recording_state maps numeric Recording FSM states into ExpressionV1 signals without depending on WB55 or WBA platform glue.",
            "settings_sleepy_signal": "COMP_EPAPER_EXPRESSION_SIGNAL_SETTINGS_SLEEPY",
            "expression_request_id_base": "0xe0000000",
            "expression_card_slot": 1,
            "expression_catalog": "docs/validation/companion-screen-expression-catalog.json",
            "expression_copy_contract": "tools/verify_expression_copy_contract.py guards ExpressionV1 title/body/footer copy across renderer, firmware, catalog, layout, priority, and generated PBM fixtures so WBA target glue cannot fork user-visible text.",
            "expression_visual_contract": "tools/verify_expression_visual_contract.py guards every ExpressionV1 PBM against blank, overfilled, or visually duplicate faces before target transport changes.",
            "generated_art_style_contract": "tools/render_generated_art_style_contract.py guards genref_sheet_12_inner_faces_v5 style anchors across pet_visual_style.h and MENU_STYLE so WBA ports tune generated-art direction through portable style constants and external CEMP assets instead of target glue or internal Flash bitmaps.",
            "generated_art_profile_portability": "tools/verify_generated_expression_sheet_profile_portability.py proves the same accepted sheet can generate isolated WIDTHxHEIGHT PBM assets with a target-specific suffix, so a WBA panel profile changes CEMP input data instead of recreating the expression engine.",
            "expression_layout_contract": "tools/verify_expression_layout_contract.py guards ExpressionV1 title/body/footer copy against truncation and overlap on supported screen variants.",
            "expression_priority_matrix": "tools/verify_expression_priority_matrix.py guards every current ExpressionV1 face/signal pair, including lower-priority blocking, settings sleepy, battery recovered, duplicate suppression, and transient recovery behavior.",
            "expression_input_source_matrix": "tools/verify_expression_input_source_matrix.py guards boot, diagnostic, settings, status, battery, recording, interaction, and OTA input source coverage for WB55 and WBA adapters.",
            "diagnostic_arg3_model": "(expression_id << 16) | signal_id",
            "panel_callback": "comp_epaper_panel_refresh_fn_t",
            "wba_refresh_intent_contract": "WBA target panel callbacks receive comp_epaper_display_request_t through comp_epaper_panel_refresh_fn_t and must preserve refresh_mode plus dirty_x/dirty_y/dirty_width/dirty_height; WBA55/WBA65 target code maps COMP_EPAPER_REFRESH_PARTIAL_INTERACTIVE, COMP_EPAPER_REFRESH_MAINTENANCE, and COMP_EPAPER_REFRESH_FULL to controller waveforms inside panel_target_stm32wba.* without changing portable queue, scene, or refresh-policy code.",
            "panel_adapter_telemetry": "comp_epaper_panel_adapter_snapshot exposes attempts/rendered/deferred/error/last_result stats without target dependencies.",
            "wba_panel_target_scaffold": "WBA panel target adapter scaffold panel_target_stm32wba.h/.c defaults to dry-run through companion_epaper_panel_stm32wba_init and binds a WBA55/WBA65 target-owned refresh callback through companion_epaper_panel_stm32wba_bind without WB55 pin facts or WB55 build integration.",
            "wba_display_scheduler_scaffold": "WBA display scheduler scaffold screen_scheduler_stm32wba.h/.c provides callback-only display task wakeup, expression tick timer, and now_ms boundaries without WB55 UTIL_SEQ/HW_TS details.",
            "wba_screen_gatt_scaffold": "WBA screen GATT scaffold screen_gatt_stm32wba.h/.c preserves CardWriteV1/CardStatusV1/SettingsV1, settings clear recovery, accepted and final CardStatusV1 identity, settings_sleepy_screen_status, and screen_expression_status without WB55 STM32_WPAN or companion_gatt_stm32wb details.",
            "wba_screen_assets_scaffold": "WBA screen-assets scaffold screen_assets_stm32wba.h/.c binds a target-owned logical-partition read callback to comp_asset_store_t as external NOR, checks every read against partition_size, and keeps addresses, storage peripherals, pins, erase, and activation out of portable resource code.",
            "wba_touch_target_scaffold": "WBA FT6336 touch target scaffold touch_target_stm32wba_ft6336.h/.c binds 7-bit probe/register-read callbacks for WBA55/WBA65 and reuses comp_ft6336_decode_touch_report without CubeWBA HAL or WB55 pin facts.",
            "wba_cube_dependency_preflight": "CubeWBA dependency preflight docs/validation/companion-screen-wba-cube-dependency-preflight.json records whether third_party/STM32CubeWBA exists and keeps WBA status DRAFT_PRE_PORT until a separate CubeWBA project and WBA build wrapper land.",
            "wba_lse_clock_contract": "WBA55/WBA65 production boards default to an assembled 32.768 kHz LSE crystal and target-specific load capacitors for BLE sleep timing, RTC continuity, timed wake-up, and low-power behavior; any no-LSE variant requires explicit radio-clock, accuracy, and power evidence.",
            "wba_adapter_m33_compile_gate": "tools/verify_wba_adapter_m33_compile.py compiles every callback-only WBA panel, scheduler, GATT, external-assets, FT6336, power, and pet-memory adapter as strict freestanding Cortex-M33 C for the shared WBA55 baseline without claiming a CubeWBA project or hardware parity.",
            "screen_runtime_snapshot": "comp_epaper_screen_runtime_snapshot aggregates expression, display queue, and panel adapter stats snapshots without target dependencies.",
            "runtime_diagnostics": "e_paper.runtime_snapshot packs expression, display queue, and panel runtime stats from comp_epaper_screen_runtime_snapshot without changing CardStatusV1.",
            "runtime_diagnostic_decode": "tools/decode_diag_log.py decodes e_paper.runtime_snapshot into decoded_args for host and WBA bring-up logs.",
            "runtime_diagnostics_bundle": "tools/collect_companion_diagnostics.ps1 keeps e_paper.runtime_snapshot in a bounded diagnostics tail with epaper.runtime_snapshot_decoded summary fields.",
            "card_status_contract": "accepted/rendered/failed/busy render states and stable last_error values are host-facing.",
            "touch_protocol": "FT6336 address/report/identity decoding and gesture recognition stay portable; target I2C and pins stay in target-named adapters.",
            "pet_attention_policy": "pet_attention maps normalized logical touch coordinates to a 3x3 gaze cell and an external attention.* CEMP clip without panel, GPIO, storage, or MCU-family dependencies.",
            "pet_expression_policy": "pet_behavior and pet_expression compose ExpressionV1 state, continuous logical gaze, tap and directional-stroke semantics, valence/arousal/curiosity/affection/attachment mood, deterministic personality, low-frequency user-data memory export/import, eyelid openness, eye width, eye spacing, paired-eye tilt, highlight scale, full-face shift, brow, mouth scale, cheek, and mark parameters into the existing screen_framebuffer without panel, GPIO, storage, or MCU-family dependencies; they must not introduce full-screen static expression arrays into internal Flash.",
            "pet_behavior_user_data_contract": "comp_pet_behavior_memory_t is user-data, not ui_assets/CEMP, OTA staging, recording cache, or an MCU Flash constant. WB55/WBA targets must persist it only through a target-owned CRC-protected, wear-aware user-data adapter, preserve it across normal OTA/resource updates, allow factory/privacy erase to clear it explicitly, coalesce writes at low frequency, and keep physical address, erase size, and storage peripheral details out of pet_behavior.h/.c.",
            "host_expression_status_faces": [
                "idle",
                "sleepy",
                "recording",
                "low_battery",
                "sync_complete",
                "error",
            ],
            "host_expression_status_sequence": "screen_expression_status accepted/final CardStatusV1 pairs keep contiguous refresh_count values, stable request_id/content_crc32, expression CRCs, and diagnostic arg3 decode.",
            "real_ble_screen_operations": [
                "screen_expression_status",
                "card_write",
                "settings_sleepy_screen_status",
            ],
            "real_ble_expression_status_sequence": "real BLE artifacts must carry the six-face screen_expression_status baseline from companion-screen-expression-host-status-sequence.json before claiming panel parity.",
        },
        "current_goal_visual_boundary": {
            "active_inner_face_source": "companion-pet-expression-v9",
            "active_inner_face_sha256": V9_SHA256,
            "visual_runtime": "external CEMP through callback-only ordinary 1-1-1 SPI NOR; the v9 candidate is machine-only and inactive",
            "historical_procedural_composer": "pet_expression remains a historical host/protocol regression archive only and must not be reintroduced into a WB55 or WBA product framebuffer path",
            "runtime_resource_activation_allowed": False,
            "real_wba_panel_parity_claimed": False,
        },
        "wb55_specific_boundaries": {
            "gatt_scheduler_glue": rel(APP_BLE),
            "scheduler": "UTIL_SEQ/HW_TS stay in WB55 glue and must not move into portable screen files.",
            "panel_backend": "WB55 uses companion_epaper_panel_stm32wb_init(); the production bring-up build selects the hardware-proven SSD1681 backend while dry-run remains available for no-panel builds.",
            "panel_target_adapter": "panel_target_stm32wb.c is target-named WB55 glue; WBA must add a separate *_stm32wba.* adapter instead of modifying portable screen files.",
            "wb55_touch_identity_baseline": "address=0x38 cipher=0x64 firmware=0x01 chip=0x11 with zero I2C errors",
        },
        "future_wba_required_artifacts": [
            "Separate CubeWBA project and build wrapper; do not retarget the WB55 Cube project in place.",
            "CubeWBA dependency preflight verified by tools/verify_expression_wba_cube_dependency_preflight.py before creating or claiming a WBA build wrapper.",
            "WBA BLE/GATT adapter preserving the UUID table, payload layouts, CardStatusV1 meanings, and settings_sleepy_screen_status behavior.",
            "Initial WBA screen GATT scaffold screen_gatt_stm32wba.h/.c verified by tools/verify_expression_screen_gatt_stm32wba.py before CubeWBA BLE service integration is added.",
            "Initial WBA screen-assets scaffold screen_assets_stm32wba.h/.c verified by tools/verify_expression_screen_assets_stm32wba.py before CubeWBA storage integration is added.",
            "WBA ui_assets activation preserving display generation hygiene: active CEMP revision set through display_queue, stale queued requests discarded or drained, resource_revision preserved on every request, and first current-generation frame logs coherent_generation=1 with generation_switches and last_stale_discarded.",
            "WBA scheduler/timer hook that wakes the display task and feeds comp_epaper_expression_state_tick().",
            "Initial WBA display scheduler scaffold screen_scheduler_stm32wba.h/.c verified by tools/verify_expression_screen_scheduler_stm32wba.py before CubeWBA scheduler integration is added.",
            "WBA display task preserving the display drain contract before panel parity is claimed.",
            "Target-named WBA panel transport, for example *_stm32wba.*, wired only through comp_epaper_panel_refresh_fn_t.",
            "Initial WBA panel target adapter scaffold panel_target_stm32wba.h/.c verified by tools/verify_expression_panel_target_stm32wba.py before real transport is added.",
            "Initial WBA FT6336 touch target scaffold touch_target_stm32wba_ft6336.h/.c verified by tools/verify_touch_target_stm32wba_ft6336.py before CubeWBA I2C integration is added.",
            "Every callback-only WBA adapter passes tools/verify_wba_adapter_m33_compile.py before a CubeWBA project or target glue is promoted.",
            "Target-specific WBA port scaffold generated by tools/init_expression_wba_port_scaffold.py before copying WB55 glue.",
            "target capability profile verified by tools/verify_expression_target_capabilities.py before using WBA65-only resources or changing shared screen limits.",
            "WBA expression priority matrix passes before scheduler or status-adapter parity is claimed.",
            "WBA expression input source matrix passes before screen-expression parity is claimed.",
            "WBA no-hardware visual and layout contracts pass before target transport changes are accepted.",
            "WBA generated-art style contract passes before changing pet/menu proportions or replacing reference art.",
            "WBA panel profile changes pass tools/verify_generated_expression_sheet_profile_portability.py before the new PBM set is bound into a CEMP manifest.",
            "WBA real parity gate verified by tools/verify_expression_wba_real_parity_gate.py before any real WBA panel, BLE, or rendered/ok parity claim is accepted.",
            "Real BLE artifact carrying screen_expression_status six-face baseline before claiming panel parity.",
            "Real BLE artifact using --expect-real-panel before claiming rendered/ok parity.",
            "Completed panel evidence template with WBA controller, pin map, reset/BUSY timing, refresh policy, logs, and visual proof.",
            "Filled panel evidence record with e_paper.runtime_snapshot runtime snapshot decoded_args showing zero panel errors, zero pending display work, and zero dropped display work.",
            "WBA touch_target_stm32wba_ft6336 callback adapter plus real address, identity, corner-coordinate, and gesture evidence before touch parity is claimed.",
            "WBA LSE clock contract verified by tools/verify_expression_wba_lse_clock_contract.py; real WBA parity requires LSE startup, RTC continuity, BLE advertising/connection through sleep, and timed wake-up evidence, or an explicit no-LSE radio-clock/power exception.",
            "WBA pet-behavior user-data adapter pet_behavior_user_data_stm32wba.h/.c preserving comp_pet_behavior_memory_t outside ui_assets/CEMP, OTA staging, recording cache, and MCU Flash constants; it must be callback-only, CRC-protected, wear-aware, low-frequency/coalesced, preserved across normal OTA/resource updates, and explicitly cleared only by factory/privacy erase.",
        ],
        "blocked_until_hardware": {
            "gate": "wba_real_panel_refresh",
            "reason": "WBA real refresh still requires a CubeWBA project, target pins, timing, refresh logs, and visual evidence; WB55 real refresh is already proven.",
        },
        "validation_commands": [
            "python .\\tools\\verify_expression_wba_portability.py",
            "python .\\tools\\verify_expression_catalog_contract.py",
            "python .\\tools\\verify_expression_copy_contract.py",
            "python .\\tools\\verify_expression_visual_contract.py",
            "python .\\tools\\render_generated_art_style_contract.py",
            "python .\\tools\\verify_generated_expression_sheet_profile_portability.py",
            "python .\\tools\\verify_expression_layout_contract.py",
            "python .\\tools\\verify_expression_priority_matrix.py",
            "python .\\tools\\verify_expression_input_source_matrix.py",
            "python .\\tools\\verify_expression_signal_guard.py",
            "python .\\tools\\verify_expression_recording_state_hook.py",
            "python .\\tools\\verify_expression_host_status_sequence.py",
            "python .\\tools\\verify_expression_state_telemetry.py",
            "python .\\tools\\verify_display_queue_generation_hygiene.py",
            "python .\\tools\\verify_display_queue_telemetry.py",
            "python .\\tools\\verify_expression_display_drain.py",
            "python .\\tools\\verify_expression_wba_cube_dependency_preflight.py",
            "python .\\tools\\verify_expression_wba_real_parity_gate.py",
            "python .\\tools\\verify_expression_wba_lse_clock_contract.py",
            "python .\\tools\\verify_wba_adapter_m33_compile.py",
            "python .\\tools\\verify_wba_adapter_m33_compile.py --self-test",
            "python .\\tools\\verify_expression_target_capabilities.py",
            "python .\\tools\\verify_expression_screen_runtime_snapshot.py",
            "python .\\tools\\verify_expression_screen_runtime_diagnostics.py",
            "python .\\tools\\verify_expression_screen_runtime_diagnostic_decode.py",
            "python .\\tools\\verify_companion_diagnostics_static.py",
            "python .\\tools\\verify_expression_acceptance_index.py",
            "python .\\tools\\verify_expression_real_ble_screen_bench.py",
            "python .\\tools\\verify_expression_panel_gate.py",
            "python .\\tools\\verify_expression_panel_target_stm32wba.py",
            "python .\\tools\\verify_expression_screen_scheduler_stm32wba.py",
            "python .\\tools\\verify_expression_screen_gatt_stm32wba.py",
            "python .\\tools\\verify_expression_screen_assets_stm32wba.py",
            "python .\\tools\\verify_touch_target_stm32wba_ft6336.py",
            "python .\\tools\\verify_pet_behavior_user_data_stm32wba.py",
            "python .\\tools\\init_expression_wba_port_scaffold.py",
            "python .\\tools\\init_expression_wba_port_scaffold.py --self-test",
            "git diff --name-only -- third_party\\STM32CubeWB third_party\\STM32CubeWBA",
        ],
    }


def git_output(*args: str) -> str:
    completed = subprocess.run(
        ["git", *args],
        cwd=REPO_ROOT,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
    )
    if completed.returncode != 0:
        raise RuntimeError(completed.stderr.strip() or f"git {' '.join(args)} failed")
    return completed.stdout


def check_portable_files(errors: list[str]) -> None:
    for path in PORTABLE_FILES:
        require(path.exists(), f"missing portable expression file: {path.relative_to(REPO_ROOT)}", errors)
        if not path.exists():
            continue
        text = read(path)
        for label, pattern in FORBIDDEN_PORTABLE_PATTERNS.items():
            match = pattern.search(text)
            require(
                match is None,
                f"{path.relative_to(REPO_ROOT)} contains non-portable {label}: {match.group(0) if match else ''}",
                errors,
            )


def check_expression_contracts(errors: list[str]) -> None:
    renderer = read(EPAPER_ROOT / "card_renderer.py")
    policy = read(EPAPER_ROOT / "expression_policy.py")
    queue_header = read(EPAPER_ROOT / "display_queue.h")
    events_header = read(EPAPER_ROOT / "expression_events.h")
    events_source = read(EPAPER_ROOT / "expression_events.c")
    expression_header = read(EPAPER_ROOT / "expression_state.h")
    expression_source = read(EPAPER_ROOT / "expression_state.c")
    pet_attention_header = read(EPAPER_ROOT / "pet_attention.h")
    pet_attention_source = read(EPAPER_ROOT / "pet_attention.c")
    pet_behavior_header = read(EPAPER_ROOT / "pet_behavior.h")
    pet_behavior_source = read(EPAPER_ROOT / "pet_behavior.c")
    pet_expression_header = read(EPAPER_ROOT / "pet_expression.h")
    pet_expression_source = read(EPAPER_ROOT / "pet_expression.c")
    pet_performance_header = read(EPAPER_ROOT / "pet_performance.h")
    pet_performance_source = read(EPAPER_ROOT / "pet_performance.c")
    pet_performance_bridge_header = read(EPAPER_ROOT / "pet_performance_event_bridge.h")
    pet_performance_bridge_source = read(EPAPER_ROOT / "pet_performance_event_bridge.c")
    v9_binding_header = read(EPAPER_ROOT / "v9_candidate_resource_binding.h")
    v9_binding_source = read(EPAPER_ROOT / "v9_candidate_resource_binding.c")
    panel_source = read(EPAPER_ROOT / "panel_adapter.c")
    panel_target_source = read(PANEL_TARGET_STM32WB_SOURCE)
    panel_target_header = read(PANEL_TARGET_STM32WB_HEADER)
    wba_panel_target_source = read(PANEL_TARGET_STM32WBA_SOURCE)
    wba_panel_target_header = read(PANEL_TARGET_STM32WBA_HEADER)
    wba_scheduler_source = read(SCREEN_SCHEDULER_STM32WBA_SOURCE)
    wba_scheduler_header = read(SCREEN_SCHEDULER_STM32WBA_HEADER)
    wba_gatt_source = read(SCREEN_GATT_STM32WBA_SOURCE)
    wba_gatt_header = read(SCREEN_GATT_STM32WBA_HEADER)
    wba_assets_source = read(SCREEN_ASSETS_STM32WBA_SOURCE)
    wba_assets_header = read(SCREEN_ASSETS_STM32WBA_HEADER)
    wba_touch_source = read(TOUCH_TARGET_STM32WBA_SOURCE)
    wba_touch_header = read(TOUCH_TARGET_STM32WBA_HEADER)
    screen_runtime_header = read(EPAPER_ROOT / "screen_runtime.h")
    screen_runtime_source = read(EPAPER_ROOT / "screen_runtime.c")
    for expression in [
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
    ]:
        require(f'"{expression}"' in renderer, f"renderer missing ExpressionV1 state {expression}", errors)
        require(f'"{expression}"' in policy, f"policy missing ExpressionV1 state {expression}", errors)
        require(f'"{expression}"' in expression_source, f"firmware expression state missing ExpressionV1 state {expression}", errors)
    for token in [
        "COMP_EPAPER_EXPRESSION_SIGNAL_RECORDING_START",
        "COMP_EPAPER_EXPRESSION_SIGNAL_MEETING_FINALIZE",
        "COMP_EPAPER_EXPRESSION_SIGNAL_WAKE_DETECTED",
        "COMP_EPAPER_EXPRESSION_SIGNAL_SETTINGS_SLEEPY",
        "COMP_EPAPER_EXPRESSION_AUTO_RECOVER_HAPPY_MS",
        "visible_age_ms",
        "suppressed_duplicate_count",
        "comp_epaper_expression_state_apply_signal",
        "comp_epaper_expression_signal_is_supported",
        "comp_epaper_expression_state_tick",
        "comp_epaper_expression_auto_recover_ms",
        "comp_epaper_expression_decision_crc32",
    ]:
        require(token in expression_header, f"firmware expression state header missing {token}", errors)
    for token in [
        "decision.expression == state->current",
        "state->suppressed_duplicate_count++",
        "state->visible_age_ms += elapsed_ms",
        "COMP_EPAPER_EXPRESSION_SIGNAL_RECOVERY",
        "COMP_EPAPER_EXPRESSION_AUTO_RECOVER_SYNC_COMPLETE_MS",
        "can_apply_lower_priority_signal",
        "return find_signal(signal) != NULL;",
        "state == NULL || out_decision == NULL || signal_def == NULL",
        "state->current == COMP_EPAPER_EXPRESSION_IDLE",
    ]:
        require(token in expression_source, f"firmware expression state source missing portable state token {token}", errors)
    for token in [
        "COMP_PET_ATTENTION_CENTER",
        "comp_pet_attention_from_touch",
        "comp_pet_attention_clip_name",
        "comp_pet_attention_self_test",
    ]:
        require(token in pet_attention_header + pet_attention_source,
                f"portable pet-attention policy missing {token}", errors)
    for token in [
        "comp_pet_behavior_t",
        "comp_pet_behavior_init",
        "comp_pet_behavior_advance",
        "comp_pet_behavior_apply_expression",
        "comp_pet_behavior_note_touch",
        "comp_pet_behavior_stroke_direction",
        "comp_pet_behavior_note_stroke",
        "comp_pet_behavior_compose_expression_pose",
        "comp_pet_behavior_compose_touch_pose",
        "comp_pet_behavior_compose_stroke_pose",
        "comp_pet_behavior_mood",
        "comp_pet_behavior_export_memory",
        "comp_pet_behavior_import_memory",
        "comp_pet_behavior_self_test",
        "COMP_PET_ENGAGEMENT_ENGAGED",
        "COMP_PET_MOOD_AFFECTIONATE",
        "valence",
        "arousal",
        "attachment",
        "last_stroke",
        "stroke_energy",
        "comp_pet_behavior_memory_t",
    ]:
        require(token in pet_behavior_header + pet_behavior_source,
                f"portable pet-behavior model missing {token}", errors)
    for token in [
        "comp_pet_expression_pose_from_expression",
        "comp_pet_expression_pose_from_touch",
        "comp_pet_expression_render",
        "comp_pet_expression_self_test",
        "COMP_PET_MARK_SPARK",
        "eye_width",
        "eye_spacing",
        "eye_pair_tilt",
        "highlight_scale",
        "face_shift_x",
        "face_shift_y",
        "brow_lift",
        "mouth_scale",
        "COMP_PET_BROW_WARM",
        "COMP_EPAPER_EXPRESSION_ERROR",
    ]:
        require(token in pet_expression_header + pet_expression_source,
                f"portable pet-expression composer missing {token}", errors)
    for token in [
        "comp_pet_performance_t",
        "comp_pet_performance_begin",
        "comp_pet_performance_advance",
        "comp_pet_performance_recover_to_idle",
        "COMP_PET_PERFORMANCE_SCENE_RECORDING_SAVED",
        "COMP_PET_PERFORMANCE_SCENE_VOICE_LISTENING",
        "generation",
        "resource_family",
    ]:
        require(token in pet_performance_header + pet_performance_source,
                f"portable pet-performance contract missing {token}", errors)
    for token in [
        "comp_pet_performance_apply_expression_signal",
        "comp_pet_performance_apply_event",
        "COMP_EPAPER_EXPRESSION_SIGNAL_RECORDING_START",
        "COMP_EPAPER_EXPRESSION_SIGNAL_RECORDING_FINISHED",
        "COMP_PET_PERFORMANCE_EVENT_DAILY_SWIPE_LEFT",
        "COMP_EPAPER_EXPRESSION_SIGNAL_SPEAKER_RESULT",
    ]:
        require(token in pet_performance_bridge_header + pet_performance_bridge_source,
                f"portable pet-performance event bridge missing {token}", errors)
    for token in [
        "comp_v9_candidate_resource_resolve",
        "COMP_V9_CANDIDATE_RESOURCE_AVAILABLE_NOT_ACTIVE",
        "COMP_V9_CANDIDATE_RESOURCE_PENDING_VISUAL_BASELINE",
        "COMP_V9_CANDIDATE_RESOURCE_PENDING_MENU_VISUAL_BASELINE",
        "COMP_V9_CANDIDATE_PACK_REVISION 90u",
        "return false;",
    ]:
        require(token in v9_binding_header + v9_binding_source,
                f"portable v9 candidate binding missing {token}", errors)
    for token in [
        "comp_emote_asset_pack_mount",
        "comp_asset_store_",
        "comp_epaper_display_queue_",
        "companion_epaper_panel_",
        "HAL_",
        "STM32",
        "GPIO",
        "SPI",
        "I2C",
    ]:
        require(token not in v9_binding_header + v9_binding_source,
                f"portable v9 candidate binding leaked activation/platform token {token}", errors)
    for token in [
        "comp_epaper_expression_signal_from_diag_event",
        "comp_epaper_expression_signal_from_device_status",
        "comp_epaper_expression_signal_from_recording_state",
        "comp_epaper_expression_signal_from_meeting_status",
        "comp_epaper_expression_signal_from_speaker_status",
        "comp_epaper_expression_signal_from_wake_word_status",
        "comp_epaper_expression_signal_from_ota_readiness",
        "COMP_EPAPER_EXPRESSION_DEVICE_ACTIVE_MODE_DISCONNECTED",
        "COMP_EPAPER_EXPRESSION_RECORDING_STATE_TRANSFER_READY",
        "COMP_EPAPER_EXPRESSION_RECORDING_STATE_ERROR_RECOVERY",
        "COMP_EPAPER_EXPRESSION_MEETING_STATE_RECORDING",
        "COMP_DIAG_EVT_WAKE_WORD_DETECTED",
        "COMP_DIAG_EVT_RECORDING_FSM_SESSION_FINISHED",
        "COMP_DIAG_EVENT_SOURCE(event_code) == (uint8_t)COMP_DIAG_SRC_EPAPER",
        "COMP_EPAPER_EXPRESSION_OTA_LOW_BATTERY_BLOCKER_BIT",
    ]:
        require(token in events_header + events_source, f"firmware expression event bridge missing {token}", errors)
    require("COMP_EPAPER_DISPLAY_QUEUE_DEPTH 4u" in queue_header, "display queue depth changed from WBA-safe bound", errors)
    require(
        "COMP_EPAPER_DISPLAY_PAYLOAD_MAX_BYTES 236u" in queue_header,
        "display queue payload bound changed from ATT-safe value",
        errors,
    )
    require("COMP_EPAPER_PANEL_RESULT_DEFERRED_NO_PANEL" in panel_source, "panel adapter must preserve deferred no-panel result", errors)
    for token in [
        "comp_epaper_panel_refresh_fn_t",
        "adapter->config.refresh == NULL",
        "adapter->config.refresh(adapter->config.context",
    ]:
        require(token in panel_source + read(EPAPER_ROOT / "panel_adapter.h"), f"panel adapter missing target callback boundary {token}", errors)
    require("COMP_EPAPER_RENDER_STATE_FAILED" in panel_source, "dry-run panel adapter must not claim rendered state", errors)
    for token in [
        "companion_epaper_panel_stm32wb_init",
        "comp_epaper_panel_adapter_init_dry_run(adapter)",
    ]:
        require(token in panel_target_header + panel_target_source, f"WB55 target panel adapter missing dry-run token {token}", errors)
    for token in [
        "companion_epaper_panel_stm32wba_init",
        "companion_epaper_panel_stm32wba_target_name",
        "COMPANION_EPAPER_PANEL_STM32WBA_TARGET_WBA55",
        "COMPANION_EPAPER_PANEL_STM32WBA_TARGET_WBA65",
        "comp_epaper_panel_adapter_init_dry_run(adapter)",
        "companion_epaper_panel_stm32wba_config_t",
        "companion_epaper_panel_stm32wba_bind",
        "comp_epaper_panel_adapter_init(adapter, &panel_config)",
    ]:
        require(token in wba_panel_target_header + wba_panel_target_source, f"WBA target panel adapter missing scaffold token {token}", errors)
    for token in ["SPI2", "PA9", "PC1", "PC2", "PA6", "GPIO_PIN_", "HAL_SPI", "STM32_WPAN", "CPU2", "FUS"]:
        require(token not in wba_panel_target_header + wba_panel_target_source, f"WBA target panel adapter leaked WB55/hardware token {token}", errors)
    for token in [
        "companion_epaper_stm32wba_scheduler_t",
        "companion_epaper_stm32wba_schedule_display_task",
        "companion_epaper_stm32wba_schedule_expression_tick",
        "companion_epaper_stm32wba_now_ms",
        "start_expression_tick_timer",
        "stop_expression_tick_timer",
    ]:
        require(token in wba_scheduler_header + wba_scheduler_source, f"WBA display scheduler scaffold missing token {token}", errors)
    for token in ["UTIL_SEQ", "HW_TS", "CFG_TASK_COMPANION_DISPLAY_ID", "HAL_GetTick", "STM32_WPAN", "CPU2", "FUS", "IPCC", "HSEM"]:
        require(token not in wba_scheduler_header + wba_scheduler_source, f"WBA display scheduler scaffold leaked WB55/platform token {token}", errors)
    for token in [
        "COMPANION_EPAPER_STM32WBA_GATT_MAX_PAYLOAD_BYTES 248u",
        "COMPANION_EPAPER_STM32WBA_EXPRESSION_CARD_SLOT 1u",
        "COMPANION_EPAPER_STM32WBA_EXPRESSION_REQUEST_ID_BASE 0xe0000000u",
        "companion_epaper_stm32wba_card_write_v1_t",
        "companion_epaper_stm32wba_card_status_v1_t",
        "companion_epaper_stm32wba_settings_v1_t",
        "COMPANION_EPAPER_STM32WBA_RENDER_STATE_ACCEPTED",
        "COMPANION_EPAPER_STM32WBA_RENDER_STATE_RENDERED",
        "COMPANION_EPAPER_STM32WBA_RENDER_STATE_FAILED",
        "COMPANION_EPAPER_STM32WBA_RENDER_STATE_BUSY",
        "COMPANION_EPAPER_STM32WBA_LAST_ERROR_OK",
        "COMPANION_EPAPER_STM32WBA_LAST_ERROR_DEFERRED_NO_PANEL",
        "companion_epaper_stm32wba_screen_gatt_accept_card_write",
        "companion_epaper_stm32wba_screen_gatt_publish_card_status",
        "companion_epaper_stm32wba_screen_gatt_handle_settings",
        "companion_epaper_stm32wba_settings_wants_sleepy",
        "companion_epaper_stm32wba_is_expression_request_id",
        "gatt->config.handle_card_write != NULL",
        "gatt->config.publish_card_status",
        "gatt->config.apply_settings_expression_hint",
        "gatt->config.schedule_display_task",
        "settings->display_brightness == 0u",
        "COMPANION_EPAPER_STM32WBA_QUIET_HOURS_SLEEPY_FLAG",
        "request_id & 0xf0000000u",
        "COMPANION_EPAPER_STM32WBA_RENDER_STATE_ACCEPTED",
        "COMPANION_EPAPER_STM32WBA_LAST_ERROR_OK",
        ".refresh_count = ++gatt->refresh_count",
    ]:
        require(token in wba_gatt_header + wba_gatt_source, f"WBA screen GATT scaffold missing token {token}", errors)
    for token in ["companion_gatt_stm32wb", "STM32_WPAN", "aci_gatt", "SVCCTL", "GATT_NOTIFY_ATTRIBUTE_WRITE", "UTIL_SEQ", "CPU2", "FUS", "IPCC", "HSEM"]:
        require(token not in wba_gatt_header + wba_gatt_source, f"WBA screen GATT scaffold leaked WB55/platform token {token}", errors)
    for token in [
        "companion_screen_assets_stm32wba_read_fn_t",
        "companion_screen_assets_stm32wba_init",
        "companion_screen_assets_stm32wba_ready",
        "companion_screen_assets_stm32wba_bind",
        "COMP_ASSET_STORAGE_EXTERNAL_NOR",
        "comp_asset_store_init_reader",
        "partition_offset > adapter->config.partition_size",
        "length > adapter->config.partition_size - partition_offset",
    ]:
        require(token in wba_assets_header + wba_assets_source, f"WBA screen-assets scaffold missing token {token}", errors)
    for token in ["HAL_", "GPIO", "QSPI", "OSPI", "I2C", "SPI", "STM32_WPAN", "0x00200000"]:
        require(token not in wba_assets_header + wba_assets_source, f"WBA screen-assets scaffold leaked platform token {token}", errors)
    for token in [
        "COMPANION_TOUCH_FT6336_STM32WBA_TARGET_WBA55",
        "COMPANION_TOUCH_FT6336_STM32WBA_TARGET_WBA65",
        "companion_touch_ft6336_stm32wba_probe_fn_t",
        "companion_touch_ft6336_stm32wba_read_fn_t",
        "companion_touch_ft6336_stm32wba_poll",
        "COMP_FT6336_I2C_ADDRESS_7BIT",
        "COMP_FT6336_IDENTITY_REGISTER",
        "comp_ft6336_decode_touch_report",
        "touch->detected = false",
    ]:
        require(token in wba_touch_header + wba_touch_source, f"WBA touch scaffold missing token {token}", errors)
    for token in ["HAL_I2C", "HAL_GPIO", "GPIO_PIN_", "I2C1", "I2C3", "PC0", "PB11", "CN7", "STM32_WPAN", "UTIL_SEQ"]:
        require(token not in wba_touch_header + wba_touch_source, f"WBA touch scaffold leaked platform token {token}", errors)
    for token in [
        "comp_epaper_screen_runtime_snapshot_t",
        "comp_epaper_expression_state_snapshot_t expression;",
        "comp_epaper_display_queue_snapshot_t display_queue;",
        "comp_epaper_panel_adapter_snapshot_t panel;",
        "comp_epaper_screen_runtime_snapshot",
        "comp_epaper_expression_state_snapshot(expression_state",
        "comp_epaper_display_queue_snapshot(display_queue",
        "comp_epaper_panel_adapter_snapshot(panel_adapter",
    ]:
        require(token in screen_runtime_header + screen_runtime_source, f"screen runtime snapshot missing portable token {token}", errors)


def check_platform_isolation(errors: list[str]) -> None:
    app_ble = read(APP_BLE)
    makefile = read(MAKEFILE)
    require('#include "display_queue.h"' in app_ble, "WB app_ble.c must consume portable display queue", errors)
    require('#include "expression_events.h"' in app_ble, "WB app_ble.c must consume portable expression event bridge", errors)
    require('#include "expression_state.h"' in app_ble, "WB app_ble.c must consume portable expression state", errors)
    require('#include "pet_performance_event_bridge.h"' in app_ble, "WB app_ble.c must consume portable pet-performance event bridge", errors)
    require('#include "panel_adapter.h"' in app_ble, "WB app_ble.c must consume portable panel adapter contract", errors)
    require('#include "panel_target_stm32wb.h"' in app_ble, "WB app_ble.c must initialize panel through target-named adapter", errors)
    require('#include "screen_runtime.h"' in app_ble, "WB app_ble.c must consume portable screen runtime snapshot", errors)
    require("companion_epaper_panel_stm32wb_init(" in app_ble and "s_companion_expression_asset_source" in app_ble, "WB build must use the target-named panel adapter and portable asset-source boundary", errors)
    require("comp_epaper_display_queue_enqueue_expression" in app_ble, "WB app_ble.c must enqueue portable expression requests", errors)
    require("comp_epaper_screen_runtime_snapshot(&s_companion_expression_state" in app_ble, "WB app_ble.c must read display telemetry through screen runtime snapshot", errors)
    require("COMP_DIAG_EVT_EPAPER_RUNTIME_SNAPSHOT" in app_ble, "WB app_ble.c must record runtime snapshot diagnostics", errors)
    require("Companion_Display_RecordRuntimeSnapshot(&runtime_stats)" in app_ble, "WB app_ble.c must record runtime diagnostics from aggregate snapshot", errors)
    require("runtime_stats->panel.error_count != 0u ? COMP_DIAG_SEV_WARN" in app_ble, "WB app_ble.c must warn on runtime panel errors", errors)
    require("comp_epaper_expression_signal_from_diag_event" in app_ble, "WB app_ble.c must map diagnostic events through portable expression bridge", errors)
    require("comp_epaper_expression_signal_from_device_status" in app_ble, "WB app_ble.c must map DeviceStatus through portable expression bridge", errors)
    require("comp_epaper_expression_signal_from_meeting_status" in app_ble, "WB app_ble.c must map MeetingStatus through portable expression bridge", errors)
    require("comp_epaper_expression_signal_from_speaker_status" in app_ble, "WB app_ble.c must map SpeakerStatus through portable expression bridge", errors)
    require("comp_epaper_expression_signal_from_wake_word_status" in app_ble, "WB app_ble.c must map WakeWordStatus through portable expression bridge", errors)
    require("comp_epaper_expression_signal_from_ota_readiness" in app_ble, "WB app_ble.c must map OTA readiness through portable expression bridge", errors)
    require("comp_pet_performance_apply_expression_signal" in app_ble, "WB app_ble.c must map committed expression signals into pet-performance scenes", errors)
    require("comp_pet_performance_apply_event" in app_ble, "WB app_ble.c must map exact touch and menu events into pet-performance scenes", errors)
    require("Companion_Display_ApplySettingsExpressionHint" in app_ble, "WB app_ble.c must map SettingsV1 screen hints through portable expression state", errors)
    require("COMP_EPAPER_EXPRESSION_SIGNAL_SETTINGS_SLEEPY" in app_ble, "WB app_ble.c must use portable settings sleepy signal", errors)
    require("$(ROOT)/app/companion_pendant/epaper" in makefile, "WB Makefile must include portable epaper module path", errors)
    require(
        "panel_adapter.c" in makefile and "panel_target_stm32wb.c" in makefile and "display_queue.c" in makefile and "expression_events.c" in makefile and "expression_state.c" in makefile and "pet_performance.c" in makefile and "pet_performance_event_bridge.c" in makefile and "v9_candidate_resource_binding.c" in makefile and "screen_runtime.c" in makefile,
        "WB Makefile must compile portable epaper C modules",
        errors,
    )
    require("panel_target_stm32wba" not in app_ble, "WB app_ble.c must not include WBA panel target scaffold", errors)
    require("panel_target_stm32wba" not in makefile, "WB Makefile must not compile WBA panel target scaffold", errors)
    require("screen_scheduler_stm32wba" not in app_ble, "WB app_ble.c must not include WBA display scheduler scaffold", errors)
    require("screen_scheduler_stm32wba" not in makefile, "WB Makefile must not compile WBA display scheduler scaffold", errors)
    require("screen_gatt_stm32wba" not in app_ble, "WB app_ble.c must not include WBA screen GATT scaffold", errors)
    require("screen_gatt_stm32wba" not in makefile, "WB Makefile must not compile WBA screen GATT scaffold", errors)
    require("screen_assets_stm32wba" not in app_ble, "WB app_ble.c must not include WBA screen-assets scaffold", errors)
    require("screen_assets_stm32wba" not in makefile, "WB Makefile must not compile WBA screen-assets scaffold", errors)
    require("touch_target_stm32wba_ft6336" not in app_ble, "WB app_ble.c must not include WBA touch scaffold", errors)
    require("touch_target_stm32wba_ft6336" not in makefile, "WB Makefile must not compile WBA touch scaffold", errors)


def check_docs(errors: list[str]) -> None:
    screen_doc = " ".join(read(SCREEN_DOC).split())
    wba_rules = " ".join(read(WBA_RULES).split())
    wba_rules_lower = wba_rules.lower()
    verifier = read(DISPLAY_QUEUE_STATIC)
    for token in [
        "WBA55/WBA65 migration pass",
        "Firmware ExpressionV1 state path",
        "Display queue fault paths",
        "WB55 device status expression hint",
        "WB55 interaction status expression hint",
        "WB55 battery expression hint",
        "WB55 OTA readiness expression hint",
        "Expression duplicate refresh suppression",
        "Expression transient auto recovery",
        "WB55 expression tick scheduler",
        "WB55 settings expression hint",
        "Host BLE ExpressionV1 status fixture",
        "Screen display drain contract",
        "verify_expression_display_drain.py",
        "Target capability profile",
        "companion-screen-target-capabilities.json",
        "verify_expression_target_capabilities.py",
        "Expression visual contract",
        "Expression layout contract",
        "verify_expression_visual_contract.py",
        "verify_expression_layout_contract.py",
        "Expression priority matrix",
        "verify_expression_priority_matrix.py",
        "Expression input source matrix",
        "verify_expression_input_source_matrix.py",
        "ExpressionV1 catalog contract",
        "ExpressionV1 copy contract",
        "Expression unknown signal guard",
        "Recording FSM state expression hook",
        "Expression state telemetry snapshot",
        "companion-screen-expression-catalog.json",
        "verify_expression_catalog_contract.py",
        "companion-screen-expression-copy-contract.json",
        "verify_expression_copy_contract.py",
        "title/body/footer",
        "companion-screen-expression-signal-guard.json",
        "verify_expression_signal_guard.py",
        "companion-screen-recording-state-expression-hook.json",
        "verify_expression_recording_state_hook.py",
        "comp_epaper_expression_signal_from_recording_state",
        "comp_epaper_expression_signal_is_supported",
        "Real BLE screen final-status bench",
        "Panel adapter target-ops boundary",
        "Panel adapter behavior matrix",
        "Panel adapter telemetry snapshot",
        "WBA panel target adapter scaffold",
        "wba_panel_target_adapter_scaffold",
        "panel_target_stm32wba",
        "verify_expression_panel_target_stm32wba.py",
        "WBA display scheduler scaffold",
        "wba_display_scheduler_scaffold",
        "screen_scheduler_stm32wba",
        "verify_expression_screen_scheduler_stm32wba.py",
        "WBA screen GATT scaffold",
        "wba_screen_gatt_scaffold",
        "screen_gatt_stm32wba",
        "verify_expression_screen_gatt_stm32wba.py",
        "companion-screen-gatt-stm32wba.json",
        "companion_epaper_stm32wba_screen_gatt_accept_card_write",
        "WBA screen-assets scaffold",
        "wba_screen_assets_scaffold",
        "screen_assets_stm32wba",
        "verify_expression_screen_assets_stm32wba.py",
        "companion-screen-assets-stm32wba.json",
        "WB55 panel target adapter scaffold",
        "Screen runtime snapshot",
        "Screen runtime diagnostics",
        "companion-screen-runtime-diagnostics.json",
        "verify_expression_screen_runtime_diagnostics.py",
        "e_paper.runtime_snapshot",
        "Screen runtime diagnostic decode",
        "companion-screen-runtime-diagnostic-decode.json",
        "verify_expression_screen_runtime_diagnostic_decode.py",
        "decoded_args",
        "Screen runtime diagnostics bundle",
        "collect_companion_diagnostics.ps1",
        "verify_companion_diagnostics_static.py",
        "runtime_snapshot_decoded",
        "Panel evidence runtime diagnostics",
        "panel_evidence_runtime_diagnostics",
        "e_paper.runtime_snapshot decoded_args show zero panel errors",
        "future WBA adapter",
        "without changing ExpressionV1 state names",
        "same no-hardware fixture suite",
        "companion-screen-wba-port-contract.json",
        "companion-screen-runtime-snapshot.json",
        "WBA port scaffold",
        "companion-screen-wba55-port-scaffold.json",
        "init_expression_wba_port_scaffold.py",
        "WBA CubeWBA dependency preflight",
        "wba_cube_dependency_preflight",
        "companion-screen-wba-cube-dependency-preflight.json",
        "verify_expression_wba_cube_dependency_preflight.py",
        "third_party/STM32CubeWBA",
    ]:
        require(token in screen_doc, f"screen expression doc missing WBA anchor: {token}", errors)
    for token in [
        "STM32WBA55",
        "STM32WBA65",
        "platform adapters must name their target family",
        "separate CubeWBA build wrapper",
        "portable logic",
        "display queue fault paths",
        "display queue telemetry",
        "Display generation hygiene",
        "active CEMP revision",
        "comp_epaper_display_queue_set_resource_revision",
        "generation_switch_count",
        "last_stale_generation_discarded",
        "coherent_generation=1",
        "display drain contract",
        "verify_expression_display_drain.py",
        "target capability profile",
        "companion-screen-target-capabilities.json",
        "verify_expression_target_capabilities.py",
        "WBA65 may add target-specific resources only behind capability flags",
        "high-water",
        "expression state telemetry",
        "comp_epaper_expression_state_snapshot",
        "batterychargev1",
        "low-battery expression",
        "otareadinessv1",
        "ota blocker",
        "duplicate expressionv1 signals",
        "transient expressionv1 faces",
        "settingsv1 screen hints",
        "devicestatusv1",
        "device-status mapper",
        "meetingstatusv1",
        "speakerstatusv1",
        "wakewordstatusv1",
        "interaction-status mapper",
        "Expression visual contract",
        "Expression layout contract",
        "verify_expression_visual_contract.py",
        "verify_expression_layout_contract.py",
        "Expression priority matrix",
        "verify_expression_priority_matrix.py",
        "Expression input source matrix",
        "verify_expression_input_source_matrix.py",
        "screen_expression_status",
        "extended ExpressionV1 status coverage",
        "Host BLE ExpressionV1 status sequence integrity",
        "companion-screen-expression-host-status-sequence.json",
        "verify_expression_host_status_sequence.py",
        "ExpressionV1 catalog",
        "ExpressionV1 copy contract",
        "unknown ExpressionV1 signals",
        "recording FSM state",
        "companion-screen-expression-catalog.json",
        "verify_expression_catalog_contract.py",
        "companion-screen-expression-copy-contract.json",
        "verify_expression_copy_contract.py",
        "title/body/footer",
        "comp_epaper_expression_signal_is_supported",
        "append-only signal catalog",
        "comp_epaper_expression_signal_from_recording_state",
        "refresh_count",
        "stable numeric IDs",
        "real ble screen bench",
        "final_card_status",
        "wba scheduler/timer hook",
        "target-owned refresh callback",
        "panel_target_stm32wb",
        "panel_target_stm32wba",
        "wba_panel_target_adapter_scaffold",
        "verify_expression_panel_target_stm32wba.py",
        "screen_scheduler_stm32wba",
        "wba_display_scheduler_scaffold",
        "verify_expression_screen_scheduler_stm32wba.py",
        "screen_gatt_stm32wba",
        "wba_screen_gatt_scaffold",
        "verify_expression_screen_gatt_stm32wba.py",
        "companion-screen-gatt-stm32wba.json",
        "companion_epaper_stm32wba_screen_gatt_accept_card_write",
        "screen_assets_stm32wba",
        "wba_screen_assets_scaffold",
        "verify_expression_screen_assets_stm32wba.py",
        "companion-screen-assets-stm32wba.json",
        "panel adapter boundary",
        "panel adapter behavior matrix",
        "panel adapter telemetry",
        "comp_epaper_panel_adapter_snapshot",
        "screen runtime snapshot",
        "comp_epaper_screen_runtime_snapshot",
        "screen runtime diagnostics",
        "e_paper.runtime_snapshot",
        "companion-screen-runtime-diagnostics.json",
        "verify_expression_screen_runtime_diagnostics.py",
        "runtime diagnostic decode",
        "decoded_args",
        "companion-screen-runtime-diagnostic-decode.json",
        "verify_expression_screen_runtime_diagnostic_decode.py",
        "diagnostics bundle fixture",
        "epaper.runtime_snapshot_decoded",
        "verify_companion_diagnostics_static.py",
        "runtime snapshot",
        "panel_error_count",
        "evidence record",
        "companion-screen-wba-port-contract.json",
        "companion-screen-runtime-snapshot.json",
        "WBA port scaffold",
        "companion-screen-wba55-port-scaffold.json",
        "init_expression_wba_port_scaffold.py",
        "WBA CubeWBA dependency preflight",
        "wba_cube_dependency_preflight",
        "companion-screen-wba-cube-dependency-preflight.json",
        "verify_expression_wba_cube_dependency_preflight.py",
        "third_party/STM32CubeWBA",
        "WBA adapter M33 compile gate",
        "verify_wba_adapter_m33_compile.py",
        "Cortex-M33",
        "Resource generation switches must remain coherent",
        "comp_pet_behavior_memory_t",
        "portable user-data payload",
        "target-owned CRC/wear-aware",
        "preserve it across normal OTA",
        "physical address and erase policy",
        "pet_behavior.h/.c",
    ]:
        require(token.lower() in wba_rules_lower, f"WBA migration rules missing anchor: {token}", errors)
    for token in [
        "comp_pet_behavior_memory_t",
        "target-owned persistence data",
        "CRC-protected writes into external user-data",
        "neither knows nor writes a Flash address",
        "memory export/import round trip",
    ]:
        require(token.lower() in screen_doc.lower(), f"screen doc missing pet behavior memory anchor: {token}", errors)
    require("panel adapter contract must stay platform-free" in verifier, "display queue verifier must guard adapter portability", errors)
    require("screen runtime must stay platform-free" in verifier, "display queue verifier must guard screen runtime portability", errors)


def check_third_party_clean(errors: list[str]) -> None:
    changed_wb = git_output("diff", "--name-only", "--", "third_party/STM32CubeWB").strip()
    changed_wba = git_output("diff", "--name-only", "--", "third_party/STM32CubeWBA").strip()
    require(not changed_wb, f"third_party/STM32CubeWB modified: {changed_wb}", errors)
    require(not changed_wba, f"third_party/STM32CubeWBA modified: {changed_wba}", errors)


def check_wba_adapter_m33_compile(errors: list[str]) -> None:
    completed = subprocess.run(
        [sys.executable, str(WBA_ADAPTER_M33_COMPILE_VERIFIER)],
        cwd=REPO_ROOT,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
    )
    if completed.returncode == 0:
        return
    output = completed.stderr.strip() or completed.stdout.strip()
    errors.append(
        "WBA Cortex-M33 adapter compile gate failed: "
        + (output or f"exit {completed.returncode}")
    )


def check_current_goal_visual_boundary(errors: list[str]) -> None:
    baseline = json.loads(read(V9_BASELINE))
    boundary = json.loads(read(V9_WBA_VISUAL_BOUNDARY))
    replay = json.loads(read(WBA_V9_CALLBACK_REPLAY))

    require(
        baseline.get("status") == "OWNER_APPROVED_SOURCE_LOCKED_MACHINE_RENDER_AUTHORIZED",
        "v9 baseline is not owner-locked for WBA portability", errors,
    )
    require(
        baseline.get("accepted_source", {}).get("sha256") == V9_SHA256,
        "WBA portability v9 source hash drifted", errors,
    )
    require(
        boundary.get("status") == "PASS_V9_WBA_VISUAL_BOUNDARY_PENDING_OWNER",
        "WBA visual boundary is not pending-owner machine PASS", errors,
    )
    wba_resource = boundary.get("wba_resource_boundary", {})
    require(
        wba_resource.get("storage") == "external CEMP through callback-only external NOR adapter"
        and wba_resource.get("transport") == "ordinary 1-1-1 SPI NOR"
        and wba_resource.get("runtime_activation_allowed") is False
        and wba_resource.get("panel_parity_claimed") is False,
        "WBA visual resource boundary drifted", errors,
    )
    require(
        replay.get("status") == "PASS_CURRENT_SOURCE_MACHINE_ONLY_CALLBACK_REPLAY",
        "WBA v9 callback replay is not machine-only PASS", errors,
    )
    candidate = replay.get("candidate", {})
    require(
        candidate.get("name") == "companion-v9-expression-candidate-200x200"
        and candidate.get("revision") == 90
        and candidate.get("clips") == 13
        and candidate.get("frames") == 39
        and candidate.get("runtime_resource_activated") is False,
        "WBA v9 callback candidate drifted or permits activation", errors,
    )
    for key in (
        "real_wba_board", "external_flash_provisioned", "firmware_flashed",
        "panel_command", "owner_visual_pass", "runtime_resource_activation",
    ):
        require(replay.get("boundary", {}).get(key) is False,
                f"WBA callback replay overclaims {key}", errors)


def check_fixture_data(data: dict[str, Any], errors: list[str]) -> None:
    require(data.get("schema_id") == SCHEMA_ID, "unexpected WBA port contract schema", errors)
    require(data.get("status") == "PASS", "WBA port contract fixture must be PASS", errors)
    targets = data.get("targets", {})
    require(targets.get("baseline") == "STM32WBA55", "WBA fixture must keep WBA55 as baseline", errors)
    require(targets.get("expanded") == "STM32WBA65", "WBA fixture must mention WBA65 expanded target", errors)
    portable = data.get("portable_contracts", {})
    current_goal = data.get("current_goal_visual_boundary", {})
    wb55_boundaries = data.get("wb55_specific_boundaries", {})
    require(
        current_goal.get("active_inner_face_source") == "companion-pet-expression-v9"
        and current_goal.get("active_inner_face_sha256") == V9_SHA256,
        "WBA fixture current v9 visual baseline drifted", errors,
    )
    require(
        "external CEMP" in str(current_goal.get("visual_runtime", ""))
        and "ordinary 1-1-1 SPI NOR" in str(current_goal.get("visual_runtime", ""))
        and current_goal.get("runtime_resource_activation_allowed") is False
        and current_goal.get("real_wba_panel_parity_claimed") is False,
        "WBA fixture current external-CEMP activation boundary drifted", errors,
    )
    require(
        "historical host/protocol regression archive" in str(current_goal.get("historical_procedural_composer", "")),
        "WBA fixture does not mark the procedural composer as historical only", errors,
    )
    for key, path in (
        ("v9_baseline", V9_BASELINE),
        ("v9_wba_visual_boundary", V9_WBA_VISUAL_BOUNDARY),
        ("wba_v9_callback_replay", WBA_V9_CALLBACK_REPLAY),
    ):
        require(data.get("sources", {}).get(key) == rel(path),
                f"WBA fixture missing current-goal source {key}", errors)
    require(portable.get("display_queue_depth") == 4, "WBA fixture display queue depth drifted", errors)
    require(portable.get("display_payload_max_bytes") == 236, "WBA fixture payload bound drifted", errors)
    require(
        "high_water_count" in str(portable.get("display_queue_telemetry", "")),
        "WBA fixture missing display queue high-water telemetry",
        errors,
    )
    require(
        "stats snapshot" in str(portable.get("display_queue_telemetry", "")),
        "WBA fixture missing display queue stats snapshot",
        errors,
    )
    display_generation = str(portable.get("display_generation_hygiene", ""))
    for token in (
        "active_resource_revision",
        "resource_revision",
        "comp_epaper_display_queue_set_resource_revision",
        "stale queued requests",
        "generation_switch_count",
        "stale_generation_discard_count",
        "last_stale_generation_discarded",
        "coherent_generation=1",
        "generation_switches",
        "last_stale_discarded",
    ):
        require(token in display_generation, f"WBA fixture missing display generation hygiene token {token}", errors)
    require(
        "verify_expression_display_drain.py" in str(portable.get("display_drain_contract", "")),
        "WBA fixture missing display drain verifier",
        errors,
    )
    require(
        "pending-work reschedule" in str(portable.get("display_drain_contract", "")),
        "WBA fixture missing display drain pending-work reschedule contract",
        errors,
    )
    require(
        "verify_expression_target_capabilities.py" in str(portable.get("target_capability_profile", "")),
        "WBA fixture missing target capability verifier",
        errors,
    )
    require(
        "WBA55" in str(portable.get("target_capability_profile", "")) and "WBA65" in str(portable.get("target_capability_profile", "")),
        "WBA fixture missing WBA55/WBA65 target capability split",
        errors,
    )
    require(
        data.get("sources", {}).get("target_capability_profile") == rel(TARGET_CAPABILITY_CONTRACT),
        "WBA fixture missing target capability contract source",
        errors,
    )
    require(
        data.get("sources", {}).get("target_capability_verifier") == rel(TARGET_CAPABILITY_VERIFIER),
        "WBA fixture missing target capability verifier source",
        errors,
    )
    require(
        data.get("sources", {}).get("wba_cube_dependency_preflight") == rel(WBA_CUBE_DEPENDENCY_CONTRACT),
        "WBA fixture missing WBA Cube dependency preflight source",
        errors,
    )
    require(
        data.get("sources", {}).get("wba_cube_dependency_verifier") == rel(WBA_CUBE_DEPENDENCY_VERIFIER),
        "WBA fixture missing WBA Cube dependency verifier source",
        errors,
    )
    require(
        data.get("sources", {}).get("wba_real_parity_gate") == rel(WBA_REAL_PARITY_GATE),
        "WBA fixture missing real parity gate source",
        errors,
    )
    require(
        data.get("sources", {}).get("wba_real_parity_gate_verifier") == rel(WBA_REAL_PARITY_GATE_VERIFIER),
        "WBA fixture missing real parity gate verifier",
        errors,
    )
    require(
        data.get("sources", {}).get("wba_lse_clock_contract") == rel(WBA_LSE_CLOCK_CONTRACT),
        "WBA fixture missing LSE clock contract source",
        errors,
    )
    require(
        data.get("sources", {}).get("wba_lse_clock_verifier") == rel(WBA_LSE_CLOCK_VERIFIER),
        "WBA fixture missing LSE clock verifier source",
        errors,
    )
    require(
        data.get("sources", {}).get("wba_panel_target_adapter_scaffold") == rel(PANEL_TARGET_STM32WBA_SOURCE),
        "WBA fixture missing WBA panel target scaffold source",
        errors,
    )
    require(
        data.get("sources", {}).get("wba_panel_target_adapter_verifier") == rel(PANEL_TARGET_STM32WBA_VERIFIER),
        "WBA fixture missing WBA panel target scaffold verifier",
        errors,
    )
    require(
        data.get("sources", {}).get("wba_display_scheduler_scaffold") == rel(SCREEN_SCHEDULER_STM32WBA_SOURCE),
        "WBA fixture missing WBA display scheduler scaffold source",
        errors,
    )
    require(
        data.get("sources", {}).get("wba_display_scheduler_verifier") == rel(SCREEN_SCHEDULER_STM32WBA_VERIFIER),
        "WBA fixture missing WBA display scheduler verifier",
        errors,
    )
    require(
        data.get("sources", {}).get("wba_screen_gatt_scaffold") == rel(SCREEN_GATT_STM32WBA_SOURCE),
        "WBA fixture missing WBA screen GATT scaffold source",
        errors,
    )
    require(
        data.get("sources", {}).get("wba_screen_gatt_verifier") == rel(SCREEN_GATT_STM32WBA_VERIFIER),
        "WBA fixture missing WBA screen GATT scaffold verifier",
        errors,
    )
    require(
        data.get("sources", {}).get("wba_screen_assets_scaffold") == rel(SCREEN_ASSETS_STM32WBA_SOURCE),
        "WBA fixture missing WBA screen-assets scaffold source",
        errors,
    )
    require(
        data.get("sources", {}).get("wba_screen_assets_verifier") == rel(SCREEN_ASSETS_STM32WBA_VERIFIER),
        "WBA fixture missing WBA screen-assets scaffold verifier",
        errors,
    )
    require(
        data.get("sources", {}).get("wba_screen_assets_contract") == rel(SCREEN_ASSETS_STM32WBA_CONTRACT),
        "WBA fixture missing WBA screen-assets scaffold contract",
        errors,
    )
    require(
        data.get("sources", {}).get("wba_touch_target_scaffold") == rel(TOUCH_TARGET_STM32WBA_SOURCE),
        "WBA fixture missing WBA touch target scaffold source",
        errors,
    )
    require(
        data.get("sources", {}).get("wba_touch_target_verifier") == rel(TOUCH_TARGET_STM32WBA_VERIFIER),
        "WBA fixture missing WBA touch target verifier",
        errors,
    )
    require(
        data.get("sources", {}).get("wba_touch_target_contract") == rel(TOUCH_TARGET_STM32WBA_CONTRACT),
        "WBA fixture missing WBA touch target contract",
        errors,
    )
    require(
        data.get("sources", {}).get("wba_pet_behavior_user_data_scaffold") == rel(PET_BEHAVIOR_USER_DATA_STM32WBA_SOURCE),
        "WBA fixture missing WBA pet behavior user-data scaffold source",
        errors,
    )
    require(
        data.get("sources", {}).get("wba_pet_behavior_user_data_verifier") == rel(PET_BEHAVIOR_USER_DATA_STM32WBA_VERIFIER),
        "WBA fixture missing WBA pet behavior user-data verifier",
        errors,
    )
    require(
        data.get("sources", {}).get("wba_pet_behavior_user_data_contract") == rel(PET_BEHAVIOR_USER_DATA_STM32WBA_CONTRACT),
        "WBA fixture missing WBA pet behavior user-data contract",
        errors,
    )
    require(
        data.get("sources", {}).get("wba_adapter_m33_compile_verifier")
        == rel(WBA_ADAPTER_M33_COMPILE_VERIFIER),
        "WBA fixture missing Cortex-M33 adapter compile verifier",
        errors,
    )
    require(
        data.get("sources", {}).get("wba_adapter_m33_compile_contract")
        == rel(WBA_ADAPTER_M33_COMPILE_CONTRACT),
        "WBA fixture missing Cortex-M33 adapter compile contract",
        errors,
    )
    m33_compile = str(portable.get("wba_adapter_m33_compile_gate", ""))
    for token in (
        "verify_wba_adapter_m33_compile.py",
        "panel",
        "scheduler",
        "GATT",
        "external-assets",
        "FT6336",
        "power",
        "pet-memory",
        "Cortex-M33",
        "WBA55 baseline",
        "without claiming a CubeWBA project or hardware parity",
    ):
        require(token in m33_compile, f"WBA fixture missing M33 compile token {token}", errors)
    require(
        "comp_epaper_expression_state_snapshot" in str(portable.get("expression_state_telemetry", "")),
        "WBA fixture missing expression state telemetry snapshot",
        errors,
    )
    require(
        "comp_epaper_expression_signal_is_supported" in str(portable.get("signal_preflight_api", "")),
        "WBA fixture missing expression signal preflight API",
        errors,
    )
    require(
        "future ExpressionV1 signals" in str(portable.get("signal_preflight_api", "")),
        "WBA fixture missing future signal rejection contract",
        errors,
    )
    require(
        "comp_epaper_expression_signal_from_recording_state" in str(portable.get("recording_state_mapper", "")),
        "WBA fixture missing recording state mapper",
        errors,
    )
    require(
        portable.get("settings_sleepy_signal") == "COMP_EPAPER_EXPRESSION_SIGNAL_SETTINGS_SLEEPY",
        "WBA fixture missing settings sleepy signal",
        errors,
    )
    require(
        "panel_target_stm32wba.h/.c" in str(portable.get("wba_panel_target_scaffold", "")),
        "WBA fixture missing WBA panel target scaffold contract",
        errors,
    )
    require(
        "screen_scheduler_stm32wba.h/.c" in str(portable.get("wba_display_scheduler_scaffold", "")),
        "WBA fixture missing WBA display scheduler scaffold contract",
        errors,
    )
    require(
        "screen_gatt_stm32wba.h/.c" in str(portable.get("wba_screen_gatt_scaffold", "")),
        "WBA fixture missing WBA screen GATT scaffold contract",
        errors,
    )
    require(
        "screen_assets_stm32wba.h/.c" in str(portable.get("wba_screen_assets_scaffold", ""))
        and "partition_size" in str(portable.get("wba_screen_assets_scaffold", "")),
        "WBA fixture missing WBA screen-assets scaffold contract",
        errors,
    )
    require(
        "touch_target_stm32wba_ft6336.h/.c" in str(portable.get("wba_touch_target_scaffold", ""))
        and "comp_ft6336_decode_touch_report" in str(portable.get("wba_touch_target_scaffold", "")),
        "WBA fixture missing callback-only WBA touch scaffold contract",
        errors,
    )
    require(
        "third_party/STM32CubeWBA" in str(portable.get("wba_cube_dependency_preflight", "")),
        "WBA fixture missing CubeWBA dependency preflight contract",
        errors,
    )
    lse_clock = str(portable.get("wba_lse_clock_contract", ""))
    for token in (
        "32.768 kHz LSE",
        "BLE sleep timing",
        "RTC continuity",
        "timed wake-up",
        "no-LSE variant",
        "radio-clock",
        "power evidence",
    ):
        require(token in lse_clock, f"WBA fixture missing LSE clock contract token {token}", errors)
    require(
        "gesture recognition stay portable" in str(portable.get("touch_protocol", "")),
        "WBA fixture missing portable touch/gesture boundary",
        errors,
    )
    require(
        "address=0x38" in str(wb55_boundaries.get("wb55_touch_identity_baseline", ""))
        and "chip=0x11" in str(wb55_boundaries.get("wb55_touch_identity_baseline", "")),
        "WBA fixture missing WB55 FT6336 identity baseline",
        errors,
    )
    require(
        "CardWriteV1" in str(portable.get("wba_screen_gatt_scaffold", ""))
        and "screen_expression_status" in str(portable.get("wba_screen_gatt_scaffold", "")),
        "WBA fixture missing WBA screen GATT host contract",
        errors,
    )
    require(portable.get("expression_request_id_base") == "0xe0000000", "WBA fixture missing expression request id base", errors)
    require(portable.get("expression_card_slot") == 1, "WBA fixture missing expression card slot", errors)
    require(
        portable.get("expression_catalog") == "docs/validation/companion-screen-expression-catalog.json",
        "WBA fixture missing expression catalog",
        errors,
    )
    require(
        data.get("sources", {}).get("expression_copy_contract") == rel(EXPRESSION_COPY_CONTRACT),
        "WBA fixture missing expression copy contract source",
        errors,
    )
    require(
        data.get("sources", {}).get("expression_copy_contract_verifier") == rel(EXPRESSION_COPY_CONTRACT_VERIFIER),
        "WBA fixture missing expression copy contract verifier",
        errors,
    )
    require(
        "verify_expression_copy_contract.py" in str(portable.get("expression_copy_contract", "")),
        "WBA fixture missing expression copy contract verifier",
        errors,
    )
    require(
        "title/body/footer" in str(portable.get("expression_copy_contract", "")),
        "WBA fixture missing expression copy fields",
        errors,
    )
    require(
        "verify_expression_visual_contract.py" in str(portable.get("expression_visual_contract", "")),
        "WBA fixture missing expression visual contract verifier",
        errors,
    )
    require(
        "visually duplicate faces" in str(portable.get("expression_visual_contract", "")),
        "WBA fixture missing visual distinctness contract",
        errors,
    )
    require(
        data.get("sources", {}).get("generated_art_profile_portability_contract")
        == rel(GENERATED_ART_PROFILE_PORTABILITY_CONTRACT),
        "WBA fixture missing generated-art profile portability contract source",
        errors,
    )
    require(
        data.get("sources", {}).get("generated_art_profile_portability_verifier")
        == rel(GENERATED_ART_PROFILE_PORTABILITY_VERIFIER),
        "WBA fixture missing generated-art profile portability verifier source",
        errors,
    )
    generated_art_profile = str(portable.get("generated_art_profile_portability", ""))
    for token in (
        "verify_generated_expression_sheet_profile_portability.py",
        "WIDTHxHEIGHT",
        "target-specific suffix",
        "CEMP input data",
    ):
        require(token in generated_art_profile, f"WBA fixture missing generated-art profile token {token}", errors)
    require(
        "verify_expression_layout_contract.py" in str(portable.get("expression_layout_contract", "")),
        "WBA fixture missing expression layout contract verifier",
        errors,
    )
    require(
        "truncation and overlap" in str(portable.get("expression_layout_contract", "")),
        "WBA fixture missing layout fit/overlap contract",
        errors,
    )
    require(
        "verify_expression_priority_matrix.py" in str(portable.get("expression_priority_matrix", "")),
        "WBA fixture missing expression priority matrix verifier",
        errors,
    )
    require(
        "lower-priority blocking" in str(portable.get("expression_priority_matrix", "")),
        "WBA fixture missing lower-priority blocking contract",
        errors,
    )
    require(
        "battery recovered" in str(portable.get("expression_priority_matrix", "")),
        "WBA fixture missing battery recovered priority contract",
        errors,
    )
    require(
        "verify_expression_input_source_matrix.py" in str(portable.get("expression_input_source_matrix", "")),
        "WBA fixture missing expression input source matrix verifier",
        errors,
    )
    require(
        "input source coverage" in str(portable.get("expression_input_source_matrix", "")),
        "WBA fixture missing input source coverage contract",
        errors,
    )
    require(
        portable.get("diagnostic_arg3_model") == "(expression_id << 16) | signal_id",
        "WBA fixture missing diagnostic arg3 model",
        errors,
    )
    require(portable.get("panel_callback") == "comp_epaper_panel_refresh_fn_t", "WBA fixture missing panel callback", errors)
    refresh_intent = str(portable.get("wba_refresh_intent_contract", ""))
    for token in [
        "comp_epaper_display_request_t",
        "refresh_mode",
        "dirty_x/dirty_y/dirty_width/dirty_height",
        "COMP_EPAPER_REFRESH_PARTIAL_INTERACTIVE",
        "COMP_EPAPER_REFRESH_MAINTENANCE",
        "COMP_EPAPER_REFRESH_FULL",
        "panel_target_stm32wba.*",
        "without changing portable queue",
    ]:
        require(token in refresh_intent, f"WBA fixture missing refresh intent contract token {token}", errors)
    require(
        "comp_epaper_panel_adapter_snapshot" in str(portable.get("panel_adapter_telemetry", "")),
        "WBA fixture missing panel adapter telemetry snapshot",
        errors,
    )
    require(
        "comp_epaper_screen_runtime_snapshot" in str(portable.get("screen_runtime_snapshot", "")),
        "WBA fixture missing screen runtime snapshot",
        errors,
    )
    require(
        "e_paper.runtime_snapshot" in str(portable.get("runtime_diagnostics", "")),
        "WBA fixture missing runtime diagnostics event",
        errors,
    )
    require(
        "decoded_args" in str(portable.get("runtime_diagnostic_decode", "")),
        "WBA fixture missing runtime diagnostic decode contract",
        errors,
    )
    require(
        "runtime_snapshot_decoded" in str(portable.get("runtime_diagnostics_bundle", "")),
        "WBA fixture missing runtime diagnostics bundle contract",
        errors,
    )
    for operation in ["screen_expression_status", "card_write", "settings_sleepy_screen_status"]:
        require(
            operation in portable.get("real_ble_screen_operations", []),
            f"WBA fixture missing real BLE screen operation {operation}",
            errors,
        )
    require(
        "six-face" in str(portable.get("real_ble_expression_status_sequence", "")),
        "WBA fixture missing real BLE expression status sequence baseline",
        errors,
    )
    require(
        "companion-screen-expression-host-status-sequence.json"
        in str(portable.get("real_ble_expression_status_sequence", "")),
        "WBA fixture missing real BLE host sequence fixture reference",
        errors,
    )
    for expression in ["idle", "sleepy", "recording", "low_battery", "sync_complete", "error"]:
        require(
            expression in portable.get("host_expression_status_faces", []),
            f"WBA fixture missing host expression status face {expression}",
            errors,
        )
    require(
        "refresh_count" in str(portable.get("host_expression_status_sequence", "")),
        "WBA fixture missing host expression status refresh_count sequence contract",
        errors,
    )
    require(
        "diagnostic arg3" in str(portable.get("host_expression_status_sequence", "")),
        "WBA fixture missing host expression status diagnostic decode contract",
        errors,
    )
    require(
        "continuous logical gaze" in str(portable.get("pet_expression_policy", "")) and
        "full-face shift" in str(portable.get("pet_expression_policy", "")) and
        "eye spacing" in str(portable.get("pet_expression_policy", "")) and
        "attachment mood" in str(portable.get("pet_expression_policy", "")) and
        "memory export/import" in str(portable.get("pet_expression_policy", "")) and
        "pet_behavior" in str(portable.get("pet_expression_policy", "")) and
        "screen_framebuffer" in str(portable.get("pet_expression_policy", "")),
        "WBA fixture missing parameterized pet-expression portability contract",
        errors,
    )
    user_data_contract = str(portable.get("pet_behavior_user_data_contract", ""))
    for token in (
        "comp_pet_behavior_memory_t",
        "user-data",
        "ui_assets/CEMP",
        "OTA staging",
        "recording cache",
        "MCU Flash constant",
        "target-owned",
        "CRC-protected",
        "wear-aware",
        "preserve it across normal OTA/resource updates",
        "factory/privacy erase",
        "coalesce writes at low frequency",
        "physical address",
        "erase size",
        "storage peripheral",
        "pet_behavior.h/.c",
    ):
        require(token in user_data_contract, f"WBA fixture missing pet behavior user-data token {token}", errors)
    for path in data.get("portable_screen_files", []):
        require((REPO_ROOT / str(path)).exists(), f"WBA fixture references missing portable file {path}", errors)
    required_artifacts = " ".join(data.get("future_wba_required_artifacts", []))
    for token in [
        "CubeWBA",
        "verify_expression_wba_cube_dependency_preflight.py",
        "verify_expression_wba_real_parity_gate.py",
        "WBA BLE/GATT adapter",
        "scheduler/timer hook",
        "display drain contract",
        "display generation hygiene",
        "coherent_generation=1",
        "generation_switches",
        "last_stale_discarded",
        "target capability profile",
        "*_stm32wba.*",
        "panel_target_stm32wba",
        "screen_scheduler_stm32wba",
        "screen_gatt_stm32wba",
        "verify_expression_screen_gatt_stm32wba.py",
        "screen_assets_stm32wba",
        "verify_expression_screen_assets_stm32wba.py",
        "verify_touch_target_stm32wba_ft6336.py",
        "verify_wba_adapter_m33_compile.py",
        "port scaffold",
        "expression priority matrix",
        "expression input source matrix",
        "visual and layout contracts",
        "--expect-real-panel",
        "panel evidence template",
        "runtime snapshot",
        "screen_expression_status six-face baseline",
        "touch_target_stm32wba_ft6336",
        "verify_expression_wba_lse_clock_contract.py",
        "LSE startup",
        "RTC continuity",
        "BLE advertising/connection through sleep",
        "no-LSE radio-clock/power exception",
        "pet-behavior user-data adapter",
        "pet_behavior_user_data_stm32wba.h/.c",
        "comp_pet_behavior_memory_t",
        "outside ui_assets/CEMP",
        "OTA staging",
        "recording cache",
        "callback-only",
        "CRC-protected",
        "wear-aware",
        "low-frequency/coalesced",
        "preserved across normal OTA/resource updates",
        "factory/privacy erase",
    ]:
        require(token in required_artifacts, f"WBA fixture missing required artifact anchor {token}", errors)
    require(
        data.get("blocked_until_hardware", {}).get("gate") == "wba_real_panel_refresh",
        "WBA fixture must keep WBA real panel refresh behind its own hardware gate",
        errors,
    )


def check_fixture_file(path: pathlib.Path, expected: dict[str, Any], errors: list[str]) -> None:
    require(path.exists(), f"missing WBA port contract fixture: {rel(path)}", errors)
    if not path.exists():
        return
    actual = json.loads(path.read_text(encoding="utf-8"))
    require(actual == expected, f"{rel(path)} is stale; rerun with --write-fixture", errors)
    check_fixture_data(actual, errors)


def parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--fixture", type=pathlib.Path, default=DEFAULT_FIXTURE)
    parser.add_argument("--write-fixture", action="store_true", help="Update the deterministic WBA port contract JSON.")
    return parser.parse_args(argv)


def main(argv: list[str]) -> int:
    args = parse_args(argv)
    fixture_path = REPO_ROOT / args.fixture
    expected = build_fixture()
    errors: list[str] = []
    for path in [
        EPAPER_ROOT,
        SCREEN_DOC,
        WBA_RULES,
        DISPLAY_QUEUE_STATIC,
        DISPLAY_DRAIN_VERIFIER,
        DISPLAY_DRAIN_CONTRACT,
        TARGET_CAPABILITY_VERIFIER,
        TARGET_CAPABILITY_CONTRACT,
        SCREEN_RUNTIME_VERIFIER,
        SCREEN_RUNTIME_DIAGNOSTICS_VERIFIER,
        SCREEN_RUNTIME_DIAG_DECODE_VERIFIER,
        EXPRESSION_CATALOG_VERIFIER,
        EXPRESSION_CATALOG,
        EXPRESSION_COPY_CONTRACT_VERIFIER,
        EXPRESSION_COPY_CONTRACT,
        EXPRESSION_VISUAL_CONTRACT_VERIFIER,
        EXPRESSION_VISUAL_CONTRACT,
        EXPRESSION_LAYOUT_CONTRACT_VERIFIER,
        EXPRESSION_LAYOUT_CONTRACT,
        EXPRESSION_PRIORITY_MATRIX_VERIFIER,
        EXPRESSION_PRIORITY_MATRIX,
        EXPRESSION_INPUT_SOURCE_MATRIX_VERIFIER,
        EXPRESSION_INPUT_SOURCE_MATRIX,
        EXPRESSION_SIGNAL_GUARD_VERIFIER,
        EXPRESSION_RECORDING_STATE_VERIFIER,
        EXPRESSION_HOST_STATUS_SEQUENCE_VERIFIER,
        WBA_PORT_SCAFFOLD_TOOL,
        WBA55_PORT_SCAFFOLD,
        WBA_LSE_CLOCK_VERIFIER,
        WBA_LSE_CLOCK_CONTRACT,
        WBA_ADAPTER_M33_COMPILE_VERIFIER,
        WBA_ADAPTER_M33_COMPILE_CONTRACT,
        V9_BASELINE,
        V9_WBA_VISUAL_BOUNDARY,
        WBA_V9_CALLBACK_REPLAY,
        PANEL_TARGET_STM32WB_HEADER,
        PANEL_TARGET_STM32WB_SOURCE,
        SCREEN_ASSETS_STM32WBA_HEADER,
        SCREEN_ASSETS_STM32WBA_SOURCE,
        SCREEN_ASSETS_STM32WBA_VERIFIER,
        SCREEN_ASSETS_STM32WBA_CONTRACT,
        TOUCH_TARGET_STM32WBA_HEADER,
        TOUCH_TARGET_STM32WBA_SOURCE,
        TOUCH_TARGET_STM32WBA_VERIFIER,
        TOUCH_TARGET_STM32WBA_CONTRACT,
        PET_BEHAVIOR_USER_DATA_STM32WBA_HEADER,
        PET_BEHAVIOR_USER_DATA_STM32WBA_SOURCE,
        PET_BEHAVIOR_USER_DATA_STM32WBA_VERIFIER,
        PET_BEHAVIOR_USER_DATA_STM32WBA_CONTRACT,
        APP_BLE,
        MAKEFILE,
    ]:
        require(path.exists(), f"missing required path {path.relative_to(REPO_ROOT)}", errors)
    if not errors:
        check_fixture_data(expected, errors)
        check_portable_files(errors)
        check_expression_contracts(errors)
        check_platform_isolation(errors)
        check_docs(errors)
        check_third_party_clean(errors)
        check_wba_adapter_m33_compile(errors)
        check_current_goal_visual_boundary(errors)
        if args.write_fixture and not errors:
            fixture_path.parent.mkdir(parents=True, exist_ok=True)
            fixture_path.write_text(json.dumps(expected, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        if not args.write_fixture:
            check_fixture_file(fixture_path, expected, errors)

    if errors:
        print("FAIL: ExpressionV1 WBA portability checks failed:", file=sys.stderr)
        for error in errors:
            print(f" - {error}", file=sys.stderr)
        return 1
    print(f"PASS: ExpressionV1 portable layers are ready for a future WBA adapter boundary -> {rel(fixture_path)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
