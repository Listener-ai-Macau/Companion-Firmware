#!/usr/bin/env python3
"""Verify Companion pendant e-paper renderer fixtures and boundaries."""

from __future__ import annotations

import json
import pathlib
import re
import sys
from typing import Any


REPO_ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT))

from app.companion_pendant.epaper.card_renderer import (  # noqa: E402
    CARD_STATES,
    CARD_TYPES,
    DISPLAY_VARIANTS,
    EXPRESSION_COPY,
    EXPRESSION_KINDS,
    CardModel,
    card_from_ble_write,
    expression_fixture_cards,
    render_card,
    required_state_cards,
    sha256_hex,
)
from app.companion_pendant.epaper.expression_policy import (  # noqa: E402
    decide_policy_case,
    expression_from_event,
    expression_from_status,
    policy_fixture_cases,
)


MANIFEST = REPO_ROOT / "docs/validation/companion-pendant-firmware-bringup-1.6-epaper-fixtures.json"
POLICY_FIXTURE = REPO_ROOT / "docs/validation/companion-screen-expression-policy.json"
SETTINGS_POLICY_FIXTURE = REPO_ROOT / "docs/validation/companion-screen-settings-policy.json"
JOURNEY_FIXTURE = REPO_ROOT / "docs/validation/companion-screen-expression-journeys.json"
EXPRESSION_COPY_CONTRACT = REPO_ROOT / "docs/validation/companion-screen-expression-copy-contract.json"
ACCEPTANCE_INDEX = REPO_ROOT / "docs/validation/companion-screen-acceptance-index.json"
ACCEPTANCE_REPORT = REPO_ROOT / "docs/validation/companion-screen-acceptance-report.md"
REAL_BLE_SCREEN_BENCH = REPO_ROOT / "docs/validation/companion-screen-real-ble-bench.json"
PANEL_ADAPTER_BEHAVIOR = REPO_ROOT / "docs/validation/companion-screen-panel-adapter-behavior.json"
PANEL_ADAPTER_BOUNDARY = REPO_ROOT / "docs/validation/companion-screen-panel-adapter-boundary.json"
PANEL_GATE = REPO_ROOT / "docs/validation/companion-screen-panel-hardware-gate.json"
PANEL_RECOVERY_GATE = REPO_ROOT / "docs/validation/companion-screen-wb55-hardware-recovery-gate.json"
PANEL_EVIDENCE_TEMPLATE = REPO_ROOT / "docs/validation/companion-screen-panel-evidence-template.json"
PANEL_EVIDENCE_RECORD_VALIDATOR = REPO_ROOT / "docs/validation/companion-screen-panel-evidence-record-validator.json"
PANEL_EVIDENCE_RECORD_SCAFFOLD = REPO_ROOT / "docs/validation/companion-screen-panel-evidence-record-scaffold.json"
PANEL_HARDWARE_SESSION = REPO_ROOT / "docs/validation/companion-screen-panel-hardware-session.json"
PANEL_TARGET_STM32WBA = REPO_ROOT / "docs/validation/companion-screen-panel-target-stm32wba.json"
PANEL_TARGET_STM32WBA_HEADER = REPO_ROOT / "app/companion_pendant/epaper/panel_target_stm32wba.h"
PANEL_TARGET_STM32WBA_SOURCE = REPO_ROOT / "app/companion_pendant/epaper/panel_target_stm32wba.c"
SCREEN_SCHEDULER_STM32WBA = REPO_ROOT / "docs/validation/companion-screen-scheduler-stm32wba.json"
SCREEN_SCHEDULER_STM32WBA_HEADER = REPO_ROOT / "app/companion_pendant/epaper/screen_scheduler_stm32wba.h"
SCREEN_SCHEDULER_STM32WBA_SOURCE = REPO_ROOT / "app/companion_pendant/epaper/screen_scheduler_stm32wba.c"
SCREEN_GATT_STM32WBA = REPO_ROOT / "docs/validation/companion-screen-gatt-stm32wba.json"
SCREEN_GATT_STM32WBA_HEADER = REPO_ROOT / "app/companion_pendant/epaper/screen_gatt_stm32wba.h"
SCREEN_GATT_STM32WBA_SOURCE = REPO_ROOT / "app/companion_pendant/epaper/screen_gatt_stm32wba.c"
WBA_CUBE_DEPENDENCY_PREFLIGHT = REPO_ROOT / "docs/validation/companion-screen-wba-cube-dependency-preflight.json"
WBA55_PORT_SCAFFOLD = REPO_ROOT / "docs/validation/companion-screen-wba55-port-scaffold.json"
STATUS_OBSERVABILITY = REPO_ROOT / "docs/validation/companion-screen-status-observability.json"
DISPLAY_QUEUE_FAULTS = REPO_ROOT / "docs/validation/companion-screen-display-queue-faults.json"
DEVICE_STATUS_EXPRESSION_HOOK = REPO_ROOT / "docs/validation/companion-screen-device-status-expression-hook.json"
INTERACTION_STATUS_EXPRESSION_HOOK = REPO_ROOT / "docs/validation/companion-screen-interaction-status-expression-hook.json"
BATTERY_EXPRESSION_HOOK = REPO_ROOT / "docs/validation/companion-screen-battery-expression-hook.json"
OTA_EXPRESSION_HOOK = REPO_ROOT / "docs/validation/companion-screen-ota-expression-hook.json"
PREVIEW_REPORT = REPO_ROOT / "docs/validation/companion-screen-expression-preview.json"
PREVIEW_SVG = REPO_ROOT / "docs/validation/epaper/expression-preview.svg"
STORYBOARD_REPORT = REPO_ROOT / "docs/validation/companion-screen-expression-storyboard.json"
STORYBOARD_SVG = REPO_ROOT / "docs/validation/epaper/expression-storyboard.svg"
README = REPO_ROOT / "app/companion_pendant/epaper/README.md"
SCAN_ROOT = REPO_ROOT / "app/companion_pendant/epaper"


def require(condition: bool, message: str, errors: list[str]) -> None:
    if not condition:
        errors.append(message)


def normalized_text_sha256(path: pathlib.Path) -> str:
    text = path.read_text(encoding="utf-8").replace("\r\n", "\n").replace("\r", "\n")
    return sha256_hex(text.encode("utf-8"))


def parse_pbm_header(data: bytes, label: str) -> tuple[int, int, int]:
    tokens: list[bytes] = []
    index = 0
    while len(tokens) < 3 and index < len(data):
        if data[index:index + 1] == b"#":
            while index < len(data) and data[index:index + 1] not in {b"\n", b"\r"}:
                index += 1
            continue
        if data[index:index + 1].isspace():
            index += 1
            continue
        start = index
        while index < len(data) and not data[index:index + 1].isspace():
            index += 1
        tokens.append(data[start:index])
    if len(tokens) != 3 or tokens[0] != b"P4":
        raise ValueError(f"{label}: expected PBM P4 header")
    while index < len(data) and data[index:index + 1].isspace():
        index += 1
    return int(tokens[1]), int(tokens[2]), index


def parse_pbm_dimensions(path: pathlib.Path) -> tuple[int, int]:
    width, height, _ = parse_pbm_header(path.read_bytes(), str(path))
    return width, height


def count_pbm_black_pixels(data: bytes) -> int:
    width, height, payload_start = parse_pbm_header(data, "<rendered>")
    row_bytes = (width + 7) // 8
    payload = data[payload_start:payload_start + row_bytes * height]
    return sum(bin(byte).count("1") for byte in payload)


def load_manifest(errors: list[str]) -> dict[str, Any] | None:
    require(MANIFEST.exists(), f"missing manifest: {MANIFEST.relative_to(REPO_ROOT)}", errors)
    if not MANIFEST.exists():
        return None
    data = json.loads(MANIFEST.read_text(encoding="utf-8"))
    require(data.get("schema_id") == "companion.pendant.epaper_fixtures.v1", "unexpected manifest schema_id", errors)
    return data


def check_manifest(data: dict[str, Any], errors: list[str]) -> None:
    fixtures = data.get("fixtures", [])
    require(len(fixtures) >= 3, "expected at least three e-paper fixtures", errors)
    required_ids = {"boot_default", "recording", "sync_complete"}
    required_expression_ids = {f"expression_{expression}" for expression in EXPRESSION_KINDS}
    fixture_ids = {fixture.get("id") for fixture in fixtures}
    require(required_ids <= fixture_ids, f"missing fixture ids: {sorted(required_ids - fixture_ids)}", errors)
    require(
        required_expression_ids <= fixture_ids,
        f"missing expression fixture ids: {sorted(required_expression_ids - fixture_ids)}",
        errors,
    )
    variants = {fixture.get("variant") for fixture in fixtures}
    require({"2.13in", "1.54in"} <= variants, "fixtures must cover 2.13in and 1.54in variants", errors)

    required_types = {"expression", "mood", "name", "event", "reminder", "recording", "sync_complete", "low_battery", "error"}
    require(required_types <= set(data.get("state_card_coverage", [])), "manifest card coverage incomplete", errors)
    require(required_types <= CARD_TYPES, "renderer CARD_TYPES missing required cards", errors)
    require({"recording", "sync_complete", "low_battery", "error"} <= CARD_STATES, "renderer states incomplete", errors)
    require(EXPRESSION_KINDS <= CARD_STATES, "renderer CARD_STATES missing expression states", errors)
    require(EXPRESSION_KINDS <= set(data.get("supported_expressions", [])), "manifest expression coverage incomplete", errors)
    require(EXPRESSION_KINDS <= set(data.get("state_coverage", [])), "manifest state coverage missing expressions", errors)
    require("deterministic 4x4 Bayer" in data.get("dithering", ""), "manifest missing deterministic dithering", errors)
    require(
        "deterministic codepoint placeholder" in data.get("text_fallback", {}).get("unsupported_unicode", ""),
        "manifest missing multilingual fallback policy",
        errors,
    )

    ble_mapping = data.get("ble_card_write_mapping", {})
    require(ble_mapping.get("card_type") == "event", "BLE CardWriteV1 mapping did not preserve event card type", errors)
    require(ble_mapping.get("request_id") == 42, "BLE CardWriteV1 mapping lost request_id", errors)


def check_fixture_files(data: dict[str, Any], errors: list[str]) -> None:
    for fixture in data.get("fixtures", []):
        rel_path = pathlib.Path(str(fixture.get("path", "")))
        path = REPO_ROOT / rel_path
        require(path.exists(), f"missing fixture file: {rel_path.as_posix()}", errors)
        if not path.exists():
            continue
        variant_key = str(fixture.get("variant"))
        variant = DISPLAY_VARIANTS.get(variant_key)
        require(variant is not None, f"unknown fixture variant: {variant_key}", errors)
        if variant is None:
            continue

        width, height = parse_pbm_dimensions(path)
        require(width == variant.width and height == variant.height, f"{rel_path}: dimension mismatch", errors)
        file_hash = sha256_hex(path.read_bytes())
        require(file_hash == fixture.get("sha256"), f"{rel_path}: hash does not match manifest", errors)

        card_data = fixture.get("card", {})
        card = CardModel(**card_data)
        expected = render_card(card, variant)
        require(sha256_hex(expected) == file_hash, f"{rel_path}: renderer output is not deterministic", errors)


def check_ble_mapping(errors: list[str]) -> None:
    card = card_from_ble_write(
        {
            "request_id": 7,
            "card_slot": 1,
            "utf8_title_len": 8,
            "utf8_body_len": 12,
            "title": "Reminder",
            "body": "Hydrate soon",
            "display_flags": 0x01,
        }
    )
    require(card.card_type == "reminder", "BLE CardWriteV1 display_flags did not map to reminder", errors)
    require(card.title == "Reminder", "BLE CardWriteV1 title length mapping failed", errors)
    require(card.body == "Hydrate soon"[:12], "BLE CardWriteV1 body length mapping failed", errors)

    multibyte_card = card_from_ble_write(
        {
            "request_id": 8,
            "card_slot": 2,
            "utf8_title_len": 3,
            "utf8_body_len": 6,
            "title": list("你好XYZ".encode("utf-8")),
            "body": list("会议TAIL".encode("utf-8")),
            "display_flags": 0x02,
        }
    )
    require(multibyte_card.card_type == "event", "BLE CardWriteV1 multibyte fixture did not map to event", errors)
    require(multibyte_card.title == "你", "BLE CardWriteV1 title byte-length mapping leaked trailing bytes", errors)
    require(multibyte_card.body == "会议", "BLE CardWriteV1 body byte-length mapping leaked trailing bytes", errors)


def check_model_render_coverage(errors: list[str]) -> None:
    for card in required_state_cards():
        for variant in DISPLAY_VARIANTS.values():
            rendered = render_card(card, variant)
            require(rendered.startswith(b"P4\n"), f"{card.card_id}/{variant.key} did not render PBM", errors)


def check_expression_rendering(errors: list[str]) -> None:
    rendered_hashes: set[str] = set()
    for card in expression_fixture_cards():
        require(card.card_type == "expression", f"{card.card_id} is not an expression card", errors)
        require(card.state in EXPRESSION_KINDS, f"{card.card_id} uses unsupported expression state", errors)
        for variant in DISPLAY_VARIANTS.values():
            first = render_card(card, variant)
            second = render_card(card, variant)
            digest = sha256_hex(first)
            rendered_hashes.add(digest)
            require(first == second, f"{card.card_id}/{variant.key} expression render is not deterministic", errors)
            require(first.startswith(b"P4\n"), f"{card.card_id}/{variant.key} expression did not render PBM", errors)
            black_pixels = count_pbm_black_pixels(first)
            total_pixels = variant.width * variant.height
            require(
                black_pixels > total_pixels // 100,
                f"{card.card_id}/{variant.key} expression render is too sparse",
                errors,
            )
            require(
                black_pixels < total_pixels * 3 // 5,
                f"{card.card_id}/{variant.key} expression render is too dense",
                errors,
            )
    expected_hash_count = len(EXPRESSION_KINDS) * len(DISPLAY_VARIANTS)
    require(
        len(rendered_hashes) == expected_hash_count,
        "expression fixtures should produce unique deterministic bitmaps",
        errors,
    )


def check_expression_policy(errors: list[str]) -> None:
    require(POLICY_FIXTURE.exists(), f"missing expression policy fixture: {POLICY_FIXTURE.relative_to(REPO_ROOT)}", errors)
    require(
        SETTINGS_POLICY_FIXTURE.exists(),
        f"missing screen settings policy fixture: {SETTINGS_POLICY_FIXTURE.relative_to(REPO_ROOT)}",
        errors,
    )
    coverage: set[str] = set()
    for case in policy_fixture_cases():
        decision = decide_policy_case(case)
        coverage.add(decision.expression)
        require(
            decision.expression == case["expected_expression"],
            f"expression policy case {case['case_id']} mapped to {decision.expression}",
            errors,
        )
        card = decision.as_card(card_id=str(case["case_id"]))
        for variant in DISPLAY_VARIANTS.values():
            rendered = render_card(card, variant)
            require(rendered.startswith(b"P4\n"), f"{case['case_id']}/{variant.key} policy card did not render PBM", errors)
    require(EXPRESSION_KINDS <= coverage, "expression policy fixture coverage incomplete", errors)
    require(expression_from_event("meeting.rejected").expression == "error", "expression policy rejected-event guard failed", errors)
    require(
        expression_from_status({"device_status": {"fault_bitmap": 1}, "meeting_status": {"state": 1}}).expression == "error",
        "expression policy fault priority failed",
        errors,
    )
    require(
        expression_from_status({"device_status": {"active_mode": 2}, "settings": {"quiet_hours_active": True}}).expression == "sleepy",
        "quiet-hours settings should map to sleepy",
        errors,
    )
    require(
        expression_from_status(
            {
                "device_status": {"active_mode": 2},
                "settings": {"quiet_hours_active": True, "display_brightness": 0},
                "recording_control": {"command": 1, "privacy_flags": 0},
            }
        ).expression == "recording",
        "recording must remain visible over quiet-hours settings",
        errors,
    )
    if SETTINGS_POLICY_FIXTURE.exists():
        settings_fixture = json.loads(SETTINGS_POLICY_FIXTURE.read_text(encoding="utf-8"))
        require(settings_fixture.get("schema_id") == "companion.pendant.screen_settings_policy.v1", "unexpected settings policy schema", errors)
        acceptance = settings_fixture.get("acceptance", {})
        for token in [
            "quiet_hours_maps_to_sleepy",
            "display_off_maps_to_sleepy",
            "recording_overrides_sleepy",
            "low_battery_overrides_sleepy",
            "error_overrides_sleepy",
            "wba_safe_policy_only",
        ]:
            require(acceptance.get(token) is True, f"settings policy acceptance missing {token}", errors)


def check_expression_journeys(errors: list[str]) -> None:
    require(JOURNEY_FIXTURE.exists(), f"missing expression journey fixture: {JOURNEY_FIXTURE.relative_to(REPO_ROOT)}", errors)
    if not JOURNEY_FIXTURE.exists():
        return
    data = json.loads(JOURNEY_FIXTURE.read_text(encoding="utf-8"))
    require(data.get("schema_id") == "companion.pendant.expression_journeys.v1", "unexpected expression journey schema", errors)
    require(set(data.get("coverage", [])) == EXPRESSION_KINDS, "expression journeys must cover every ExpressionV1 state", errors)
    acceptance = data.get("acceptance", {})
    for token in [
        "all_expression_states_covered",
        "recording_not_hidden_by_low_battery",
        "display_update_no_self_loop",
        "error_overrides_lower_priority",
        "duplicate_same_expression_suppressed",
        "transient_auto_recovery_to_idle",
        "stable_recording_does_not_timeout",
        "settings_sleepy_hint_does_not_hide_recording",
        "status_notify_duplicate_suppression",
    ]:
        require(acceptance.get(token) is True, f"expression journey acceptance missing {token}", errors)

    for journey in data.get("journeys", []):
        journey_id = str(journey.get("journey_id", "journey"))
        for step in journey.get("steps", []):
            expression = str(step.get("visible_expression", ""))
            index = int(step.get("index", 0))
            require(expression in EXPRESSION_KINDS, f"{journey_id}/{index} uses unknown expression {expression}", errors)
            if expression not in EXPRESSION_KINDS:
                continue
            title, body, footer = EXPRESSION_COPY[expression]
            card = CardModel(
                card_id=f"{journey_id}_{index}",
                card_type="expression",
                state=expression,
                title=title,
                body=body,
                footer=footer,
            )
            render_hashes = step.get("render_hashes", {})
            for key, variant in DISPLAY_VARIANTS.items():
                expected = sha256_hex(render_card(card, variant))
                require(
                    render_hashes.get(key) == expected,
                    f"{journey_id}/{index}/{key} journey render hash is stale",
                    errors,
                )


def check_firmware_expression_state_fixture(errors: list[str]) -> None:
    fixture = REPO_ROOT / "docs/validation/companion-screen-firmware-expression-state.json"
    require(fixture.exists(), f"missing firmware expression state fixture: {fixture.relative_to(REPO_ROOT)}", errors)
    if not fixture.exists():
        return
    data = json.loads(fixture.read_text(encoding="utf-8"))
    require(data.get("schema_id") == "companion.pendant.firmware_expression_state.v1", "unexpected firmware expression state schema", errors)
    acceptance = data.get("acceptance", {})
    require(acceptance.get("duplicate_expression_suppressed") is True, "firmware expression state missing duplicate suppression acceptance", errors)
    require(
        acceptance.get("transient_auto_recovery_to_idle") is True,
        "firmware expression state missing transient auto recovery acceptance",
        errors,
    )
    require(
        acceptance.get("wb55_expression_tick_scheduler") is True,
        "firmware expression state missing WB55 expression tick scheduler acceptance",
        errors,
    )
    require(
        acceptance.get("wb55_settings_expression_hint") is True,
        "firmware expression state missing WB55 settings expression hint acceptance",
        errors,
    )
    state_machine = data.get("state_machine", {})
    require(
        state_machine.get("duplicate_visible_expression_suppressed") is True,
        "firmware state machine missing duplicate visible expression suppression",
        errors,
    )
    require(
        state_machine.get("auto_recovery_api") == "comp_epaper_expression_state_tick",
        "firmware state machine missing auto recovery tick API",
        errors,
    )
    wb55_tick_hook = data.get("wb55_tick_hook", {})
    require(wb55_tick_hook.get("timer_server") == "HW_TS", "firmware state fixture missing WB55 HW_TS tick hook", errors)
    require(
        wb55_tick_hook.get("recovery_enqueue_path") == "Companion_Display_EnqueueExpressionDecision",
        "firmware state fixture missing WB55 recovery enqueue path",
        errors,
    )
    wb55_settings_hook = data.get("wb55_settings_hook", {})
    require(
        wb55_settings_hook.get("sleepy_signal") == "COMP_EPAPER_EXPRESSION_SIGNAL_SETTINGS_SLEEPY",
        "firmware state fixture missing WB55 settings sleepy signal",
        errors,
    )


def check_expression_copy_contract(errors: list[str]) -> None:
    require(
        EXPRESSION_COPY_CONTRACT.exists(),
        f"missing ExpressionV1 copy contract fixture: {EXPRESSION_COPY_CONTRACT.relative_to(REPO_ROOT)}",
        errors,
    )
    if not EXPRESSION_COPY_CONTRACT.exists():
        return
    data = json.loads(EXPRESSION_COPY_CONTRACT.read_text(encoding="utf-8"))
    require(
        data.get("schema_id") == "companion.pendant.screen_expression_copy_contract.v1",
        "unexpected ExpressionV1 copy contract schema",
        errors,
    )
    require(data.get("status") == "PASS", "ExpressionV1 copy contract fixture did not PASS", errors)
    contract = data.get("copy_contract", {})
    require(contract.get("expression_count") == len(EXPRESSION_KINDS), "ExpressionV1 copy count drifted", errors)
    require(contract.get("fields") == ["title", "body", "footer"], "ExpressionV1 copy fields drifted", errors)
    require(contract.get("renderer_and_firmware_must_match") is True, "ExpressionV1 copy must match firmware", errors)
    require(contract.get("generated_fixtures_must_match_renderer") is True, "ExpressionV1 copy must match fixtures", errors)
    require(contract.get("wba_reuses_same_copy") is True, "ExpressionV1 copy must be WBA reusable", errors)
    expressions = data.get("expressions", [])
    require(len(expressions) == len(EXPRESSION_KINDS), "ExpressionV1 copy expression coverage drifted", errors)
    for entry in expressions:
        if not isinstance(entry, dict):
            errors.append("ExpressionV1 copy entry must be an object")
            continue
        expression = str(entry.get("expression", ""))
        require(expression in EXPRESSION_KINDS, f"ExpressionV1 copy fixture has unknown expression {expression}", errors)
        if expression not in EXPRESSION_KINDS:
            continue
        title, body, footer = EXPRESSION_COPY[expression]
        expected = {"title": title, "body": body, "footer": footer}
        for source_key in ["renderer", "firmware", "catalog", "firmware_fixture", "layout_fixture", "priority_matrix", "epaper_manifest"]:
            require(entry.get(source_key) == expected, f"{expression} {source_key} copy drifted", errors)


def check_acceptance_index(errors: list[str]) -> None:
    require(ACCEPTANCE_INDEX.exists(), f"missing acceptance index: {ACCEPTANCE_INDEX.relative_to(REPO_ROOT)}", errors)
    if not ACCEPTANCE_INDEX.exists():
        return
    data = json.loads(ACCEPTANCE_INDEX.read_text(encoding="utf-8"))
    require(data.get("schema_id") == "companion.pendant.screen_acceptance_index.v1", "unexpected acceptance index schema", errors)
    items = data.get("items", [])
    ids = {item.get("id") for item in items if isinstance(item, dict)}
    for required_id in [
        "no_hardware_expression_renderer",
        "ble_to_expression_policy",
        "wb55_display_queue_boundary",
        "display_queue_fault_paths",
        "wb55_boot_idle_expression",
        "screen_display_drain_contract",
        "screen_status_observability",
        "host_ble_expression_status_fixture",
        "screen_settings_expression_policy",
        "firmware_expression_state",
        "expression_copy_contract",
        "expression_priority_matrix",
        "expression_input_source_matrix",
        "expression_duplicate_refresh_suppression",
        "expression_transient_auto_recovery",
        "wb55_expression_tick_scheduler",
        "wb55_settings_expression_hint",
        "wb55_device_status_expression_hint",
        "wb55_interaction_status_expression_hint",
        "wb55_battery_expression_hint",
        "wb55_ota_readiness_expression_hint",
        "diagnostic_event_expression_bridge",
        "user_journey_expression_acceptance",
        "screen_acceptance_runner",
        "wba_pre_port_gate",
        "wba_port_scaffold",
        "wba_panel_target_adapter_scaffold",
        "wba_display_scheduler_scaffold",
        "wba_screen_gatt_scaffold",
        "wba_cube_dependency_preflight",
        "target_capability_profile",
        "devboard_ioc_screen_preflight",
        "panel_wiring_preflight",
        "panel_evidence_scaffold_wiring_prefill",
        "panel_hardware_session_scaffold",
        "panel_target_ops_boundary",
        "panel_adapter_behavior_matrix",
        "real_ble_screen_final_status_bench",
        "panel_hardware_evidence_template",
        "panel_evidence_record_validator",
        "wb55_real_panel_refresh",
    ]:
        require(required_id in ids, f"acceptance index missing {required_id}", errors)
    for item in items:
        if not isinstance(item, dict):
            continue
        status = str(item.get("status", ""))
        require(status in {"PASS", "DEFERRED_HARDWARE", "PENDING_HUMAN"}, f"acceptance item {item.get('id')} has invalid status {status}", errors)
        if item.get("id") == "wb55_real_panel_refresh":
            require(status == "DEFERRED_HARDWARE", "real panel refresh must reflect the current FTS02 fault", errors)
            require(len(item.get("missing_hardware_facts", [])) == 4, "real panel refresh must list current recovery facts", errors)
            require(
                "docs/validation/companion-screen-panel-hardware-gate.json" in item.get("evidence_paths", []),
                "real panel refresh must link the panel hardware gate fixture",
                errors,
            )
            require(
                "docs/validation/companion-screen-wb55-ssd1681-bringup.json" in item.get("evidence_paths", []),
                "real panel refresh must link the WB55 bring-up fixture",
                errors,
            )
            require(
                "docs/validation/companion-screen-ssd1681-partial-refresh-wb55.json" in item.get("evidence_paths", []),
                "real panel refresh must link the SSD1681 refresh fixture",
                errors,
            )
            require(
                "docs/validation/companion-screen-touch-ft6336-wb55.json" in item.get("evidence_paths", []),
                "real panel refresh must link the physical touch fixture",
                errors,
            )
            require(
                "docs/validation/companion-screen-wb55-hardware-recovery-gate.json" in item.get("evidence_paths", []),
                "real panel refresh must link the current hardware recovery gate",
                errors,
            )
        for evidence in item.get("evidence_paths", []):
            require((REPO_ROOT / str(evidence)).exists(), f"acceptance index evidence missing {evidence}", errors)
    check_acceptance_report(data, errors)


def check_acceptance_report(index: dict[str, Any], errors: list[str]) -> None:
    require(ACCEPTANCE_REPORT.exists(), f"missing acceptance report: {ACCEPTANCE_REPORT.relative_to(REPO_ROOT)}", errors)
    if not ACCEPTANCE_REPORT.exists():
        return
    text = ACCEPTANCE_REPORT.read_text(encoding="utf-8")
    for token in [
        "Companion Screen Acceptance Report",
        "render_expression_acceptance_report.py --write",
        "wb55_real_panel_refresh",
        "PENDING_HUMAN",
    ]:
        require(token in text, f"acceptance report missing {token}", errors)
    summary = index.get("summary", {})
    for token in [
        f"PASS: {int(summary.get('pass_count', 0))}",
        f"DEFERRED_HARDWARE: {int(summary.get('deferred_count', 0))}",
        f"TOTAL: {int(summary.get('total_count', 0))}",
    ]:
        require(token in text, f"acceptance report summary missing {token}", errors)
    for item in index.get("items", []):
        if isinstance(item, dict):
            item_id = str(item.get("id", ""))
            require(item_id in text, f"acceptance report missing item {item_id}", errors)


def check_status_observability(errors: list[str]) -> None:
    require(
        STATUS_OBSERVABILITY.exists(),
        f"missing status observability fixture: {STATUS_OBSERVABILITY.relative_to(REPO_ROOT)}",
        errors,
    )
    if not STATUS_OBSERVABILITY.exists():
        return
    data = json.loads(STATUS_OBSERVABILITY.read_text(encoding="utf-8"))
    require(data.get("schema_id") == "companion.pendant.screen_status_observability.v1", "unexpected status observability schema", errors)
    require(data.get("status") == "PASS", "status observability fixture did not PASS", errors)
    states = data.get("card_status_v1", {}).get("render_states", {})
    errors_map = data.get("card_status_v1", {}).get("last_errors", {})
    require(states.get("accepted") == 1, "CardStatusV1 accepted state drifted", errors)
    require(states.get("failed") == 3, "CardStatusV1 failed state drifted", errors)
    require(errors_map.get("deferred_no_panel") == 4, "CardStatusV1 deferred_no_panel error drifted", errors)
    acceptance = data.get("acceptance", {})
    for token in [
        "card_status_read_returns_latest_status",
        "accepted_and_final_status_preserve_request_identity",
        "dry_run_no_panel_is_observable",
        "diagnostic_events_pair_with_card_status",
        "refresh_count_is_monotonic",
        "expression_status_fixture_correlates_diag_payload",
    ]:
        require(acceptance.get(token) is True, f"status observability acceptance missing {token}", errors)


def check_display_queue_faults(errors: list[str]) -> None:
    require(
        DISPLAY_QUEUE_FAULTS.exists(),
        f"missing display queue fault fixture: {DISPLAY_QUEUE_FAULTS.relative_to(REPO_ROOT)}",
        errors,
    )
    if not DISPLAY_QUEUE_FAULTS.exists():
        return
    data = json.loads(DISPLAY_QUEUE_FAULTS.read_text(encoding="utf-8"))
    require(data.get("schema_id") == "companion.pendant.screen_display_queue_faults.v1", "unexpected display queue fault schema", errors)
    require(data.get("status") == "PASS", "display queue fault fixture did not PASS", errors)
    contract = data.get("queue_contract", {})
    require(contract.get("depth") == 4, "display queue fault fixture depth drifted", errors)
    require(contract.get("payload_max_bytes") == 236, "display queue fault fixture payload max drifted", errors)
    last_errors = contract.get("card_status_last_errors", {})
    require(last_errors.get("queue_full") == 1, "display queue fault fixture queue_full error drifted", errors)
    require(last_errors.get("payload_too_long") == 2, "display queue fault fixture payload_too_long error drifted", errors)
    require(last_errors.get("unsupported_expression") == 9, "display queue fault fixture unsupported_expression error drifted", errors)
    scenarios = {item.get("scenario"): item for item in data.get("fault_scenarios", []) if isinstance(item, dict)}
    for scenario in [
        "card_write_queue_full",
        "card_write_payload_too_long",
        "expression_queue_full_rollback",
        "expression_unsupported_rejected",
    ]:
        require(scenario in scenarios, f"display queue fault fixture missing {scenario}", errors)
    rollback = scenarios.get("expression_queue_full_rollback", {})
    require(
        rollback.get("visible_expression_after_failure") == rollback.get("previous_expression") == "idle",
        "expression queue-full rollback fixture must preserve previous visible expression",
        errors,
    )
    acceptance = data.get("acceptance", {})
    for token in [
        "queue_full_reports_busy",
        "payload_too_long_reports_failed",
        "unsupported_expression_reports_failed",
        "expression_state_rolls_back_on_enqueue_failure",
        "fault_paths_emit_update_result_diagnostics",
        "wba_safe_fault_contract",
    ]:
        require(acceptance.get(token) is True, f"display queue fault acceptance missing {token}", errors)


def check_device_status_expression_hook(errors: list[str]) -> None:
    require(
        DEVICE_STATUS_EXPRESSION_HOOK.exists(),
        f"missing DeviceStatus expression hook fixture: {DEVICE_STATUS_EXPRESSION_HOOK.relative_to(REPO_ROOT)}",
        errors,
    )
    if not DEVICE_STATUS_EXPRESSION_HOOK.exists():
        return
    data = json.loads(DEVICE_STATUS_EXPRESSION_HOOK.read_text(encoding="utf-8"))
    require(
        data.get("schema_id") == "companion.pendant.screen_device_status_expression_hook.v1",
        "unexpected DeviceStatus expression hook schema",
        errors,
    )
    require(data.get("status") == "PASS", "DeviceStatus expression hook fixture did not PASS", errors)
    active_modes = data.get("active_modes", {})
    require(active_modes.get("disconnected") == 0, "DeviceStatus disconnected active_mode drifted", errors)
    require(active_modes.get("active_audio") == 1, "DeviceStatus active-audio active_mode drifted", errors)
    require(active_modes.get("idle_link") == 2, "DeviceStatus idle-link active_mode drifted", errors)
    hook = data.get("wb55_hook", {})
    require(
        hook.get("initial_state_guard") == "Companion_Gatt_PublishDeviceStatus(false)",
        "DeviceStatus expression hook missing initial-state guard",
        errors,
    )
    require(
        hook.get("notify_read_hook") == "Companion_Gatt_PublishDeviceStatus(true)",
        "DeviceStatus expression hook missing notify/read hook",
        errors,
    )
    cases = {item.get("case_id"): item for item in data.get("cases", []) if isinstance(item, dict)}
    for case_id in [
        "idle_link_no_expression_override",
        "disconnected_maps_to_sleepy",
        "active_audio_maps_to_recording",
        "fault_bitmap_maps_to_error",
    ]:
        require(case_id in cases, f"DeviceStatus expression hook missing case {case_id}", errors)
    require(
        cases.get("active_audio_maps_to_recording", {}).get("expected_expression") == "recording",
        "DeviceStatus active-audio case must map to recording",
        errors,
    )
    require(
        cases.get("fault_bitmap_maps_to_error", {}).get("expected_expression") == "error",
        "DeviceStatus fault case must map to error",
        errors,
    )
    acceptance = data.get("acceptance", {})
    for token in [
        "device_status_publish_feeds_expression_bridge",
        "initial_state_publish_does_not_schedule_expression",
        "disconnected_maps_to_low_priority_sleepy",
        "active_audio_maps_to_recording",
        "fault_bitmap_maps_to_error",
        "fault_bitmap_takes_precedence",
        "wba_safe_device_status_hook",
    ]:
        require(acceptance.get(token) is True, f"DeviceStatus expression acceptance missing {token}", errors)


def check_interaction_status_expression_hook(errors: list[str]) -> None:
    require(
        INTERACTION_STATUS_EXPRESSION_HOOK.exists(),
        f"missing interaction status expression hook fixture: {INTERACTION_STATUS_EXPRESSION_HOOK.relative_to(REPO_ROOT)}",
        errors,
    )
    if not INTERACTION_STATUS_EXPRESSION_HOOK.exists():
        return
    data = json.loads(INTERACTION_STATUS_EXPRESSION_HOOK.read_text(encoding="utf-8"))
    require(
        data.get("schema_id") == "companion.pendant.screen_interaction_status_expression_hook.v1",
        "unexpected interaction status expression hook schema",
        errors,
    )
    require(data.get("status") == "PASS", "interaction status expression hook fixture did not PASS", errors)
    constants = data.get("constants", {})
    require(constants.get("meeting_recording") == 1, "meeting recording status value drifted", errors)
    require(constants.get("meeting_finalized") == 2, "meeting finalized status value drifted", errors)
    require(constants.get("speaker_prompt_accepted") == 2, "speaker prompt status value drifted", errors)
    require(constants.get("wake_event_detected") == 2, "wake detected event value drifted", errors)
    hook = data.get("wb55_hook", {})
    for token in [
        "Companion_Gatt_PublishMeetingStatus(false)",
        "Companion_Gatt_PublishSpeakerStatus(false)",
        "Companion_Gatt_PublishWakeWordStatus(false)",
    ]:
        require(token in hook.get("initial_state_guards", []), f"interaction status hook missing initial guard {token}", errors)
    for token in [
        "Companion_Gatt_PublishMeetingStatus(true)",
        "Companion_Gatt_PublishSpeakerStatus(true)",
        "Companion_Gatt_PublishWakeWordStatus(true)",
    ]:
        require(token in hook.get("notify_read_hooks", []), f"interaction status hook missing notify/read hook {token}", errors)
    cases = {item.get("case_id"): item for item in data.get("cases", []) if isinstance(item, dict)}
    for case_id in [
        "meeting_recording_maps_to_recording",
        "meeting_summary_pending_maps_to_thinking",
        "meeting_sync_maps_to_sync_complete",
        "speaker_prompt_maps_to_speaking",
        "wake_detected_maps_to_listening",
        "wake_error_maps_to_error",
    ]:
        require(case_id in cases, f"interaction status expression hook missing case {case_id}", errors)
    acceptance = data.get("acceptance", {})
    for token in [
        "interaction_status_publish_feeds_expression_bridge",
        "initial_state_publish_does_not_schedule_expression",
        "meeting_status_maps_to_recording_thinking_sync_error",
        "speaker_status_maps_to_speaking_error",
        "wake_word_status_maps_to_idle_listening_error",
        "duplicate_control_status_notifications_are_suppressed_by_state",
        "wba_safe_interaction_status_hook",
    ]:
        require(acceptance.get(token) is True, f"interaction status expression acceptance missing {token}", errors)


def check_battery_expression_hook(errors: list[str]) -> None:
    require(
        BATTERY_EXPRESSION_HOOK.exists(),
        f"missing battery expression hook fixture: {BATTERY_EXPRESSION_HOOK.relative_to(REPO_ROOT)}",
        errors,
    )
    if not BATTERY_EXPRESSION_HOOK.exists():
        return
    data = json.loads(BATTERY_EXPRESSION_HOOK.read_text(encoding="utf-8"))
    require(data.get("schema_id") == "companion.pendant.screen_battery_expression_hook.v1", "unexpected battery expression hook schema", errors)
    require(data.get("status") == "PASS", "battery expression hook fixture did not PASS", errors)
    thresholds = data.get("thresholds", {})
    require(thresholds.get("low_battery_percent") == 20, "battery expression low percent threshold drifted", errors)
    require(thresholds.get("low_battery_millivolts") == 3600, "battery expression low voltage threshold drifted", errors)
    require(thresholds.get("battery_recovered_percent") == 25, "battery expression recovered percent threshold drifted", errors)
    require(thresholds.get("battery_recovered_millivolts") == 3600, "battery expression recovered voltage threshold drifted", errors)
    hook = data.get("wb55_hook", {})
    require(
        hook.get("initial_state_guard") == "Companion_Gatt_PublishBatteryCharge(false)",
        "battery expression hook missing initial-state guard",
        errors,
    )
    require(
        hook.get("notify_read_hook") == "Companion_Gatt_PublishBatteryCharge(true)",
        "battery expression hook missing notify/read hook",
        errors,
    )
    cases = {item.get("case_id"): item for item in data.get("cases", []) if isinstance(item, dict)}
    for case_id in [
        "default_devboard_charging_maps_to_guarded_recovery",
        "low_percent_maps_to_low_battery",
        "low_voltage_not_charging_maps_to_low_battery",
        "low_voltage_charging_does_not_force_low_battery",
        "near_threshold_does_not_recover_low_battery",
        "recovered_percent_maps_to_battery_recovered",
        "charging_voltage_maps_to_battery_recovered",
    ]:
        require(case_id in cases, f"battery expression hook missing case {case_id}", errors)
    require(
        cases.get("low_percent_maps_to_low_battery", {}).get("expected_expression") == "low_battery",
        "battery low-percent case must map to low_battery",
        errors,
    )
    require(
        cases.get("low_voltage_charging_does_not_force_low_battery", {}).get("expected_expression") == "idle",
        "charging low-voltage case must not force low_battery",
        errors,
    )
    require(
        cases.get("default_devboard_charging_maps_to_guarded_recovery", {}).get("expected_signal") == "COMP_EPAPER_EXPRESSION_SIGNAL_BATTERY_RECOVERED",
        "default devboard charging case must map to guarded battery recovery",
        errors,
    )
    require(
        cases.get("near_threshold_does_not_recover_low_battery", {}).get("expected_signal") is None,
        "near-threshold battery case must not recover low_battery",
        errors,
    )
    acceptance = data.get("acceptance", {})
    for token in [
        "battery_charge_publish_feeds_expression_bridge",
        "initial_state_publish_does_not_schedule_expression",
        "low_percent_maps_to_low_battery",
        "low_voltage_while_not_charging_maps_to_low_battery",
        "charging_voltage_sample_does_not_force_low_battery",
        "recovered_percent_maps_to_battery_recovered",
        "charging_voltage_maps_to_battery_recovered",
        "battery_recovery_only_clears_low_battery",
        "wba_safe_battery_hook",
    ]:
        require(acceptance.get(token) is True, f"battery expression acceptance missing {token}", errors)


def check_ota_expression_hook(errors: list[str]) -> None:
    require(
        OTA_EXPRESSION_HOOK.exists(),
        f"missing OTA expression hook fixture: {OTA_EXPRESSION_HOOK.relative_to(REPO_ROOT)}",
        errors,
    )
    if not OTA_EXPRESSION_HOOK.exists():
        return
    data = json.loads(OTA_EXPRESSION_HOOK.read_text(encoding="utf-8"))
    require(data.get("schema_id") == "companion.pendant.screen_ota_expression_hook.v1", "unexpected OTA expression hook schema", errors)
    require(data.get("status") == "PASS", "OTA expression hook fixture did not PASS", errors)
    blocker_bits = data.get("blocker_bits", {})
    require(blocker_bits.get("low_battery") == 3, "OTA low-battery blocker bit drifted", errors)
    hook = data.get("wb55_hook", {})
    require(
        hook.get("initial_state_guard") == "Companion_Gatt_PublishOtaReadiness(false)",
        "OTA expression hook missing initial-state guard",
        errors,
    )
    require(
        hook.get("notify_read_hook") == "Companion_Gatt_PublishOtaReadiness(true)",
        "OTA expression hook missing notify/read hook",
        errors,
    )
    cases = {item.get("case_id"): item for item in data.get("cases", []) if isinstance(item, dict)}
    for case_id in [
        "ready_no_blockers_no_expression",
        "low_battery_blocker_maps_to_low_battery",
        "wrong_board_blocker_maps_to_error",
        "low_battery_takes_precedence_over_other_blockers",
    ]:
        require(case_id in cases, f"OTA expression hook missing case {case_id}", errors)
    require(
        cases.get("low_battery_blocker_maps_to_low_battery", {}).get("expected_expression") == "low_battery",
        "OTA low-battery blocker case must map to low_battery",
        errors,
    )
    require(
        cases.get("wrong_board_blocker_maps_to_error", {}).get("expected_expression") == "error",
        "OTA wrong-board blocker case must map to error",
        errors,
    )
    acceptance = data.get("acceptance", {})
    for token in [
        "ota_readiness_publish_feeds_expression_bridge",
        "initial_state_publish_does_not_schedule_expression",
        "low_battery_blocker_maps_to_low_battery",
        "nonzero_ota_blocker_maps_to_error",
        "low_battery_blocker_takes_precedence",
        "wba_safe_ota_hook",
    ]:
        require(acceptance.get(token) is True, f"OTA expression acceptance missing {token}", errors)


def check_panel_gate(errors: list[str]) -> None:
    require(PANEL_GATE.exists(), f"missing panel hardware gate: {PANEL_GATE.relative_to(REPO_ROOT)}", errors)
    if not PANEL_GATE.exists():
        return
    data = json.loads(PANEL_GATE.read_text(encoding="utf-8"))
    require(data.get("schema_id") == "companion.pendant.screen_panel_hardware_gate.v1", "unexpected panel gate schema", errors)
    require(data.get("gate_id") == "wb55_real_panel_refresh", "unexpected panel gate id", errors)
    require(data.get("status") == "PASS", "historical panel evidence integrity must remain PASS", errors)
    require(data.get("evidence_scope") == "historical_refresh_evidence_integrity", "panel gate must identify historical scope", errors)
    require(data.get("historical_real_refresh_claimed") is True, "historical panel evidence must retain its original refresh claim", errors)
    require(data.get("real_refresh_claim_is_historical") is True, "historical refresh scope must be explicit", errors)
    require(data.get("current_real_refresh_claimed") is False, "historical evidence must not claim current panel acceptance", errors)
    require(data.get("current_acceptance_status") == "DEFERRED_HARDWARE_FTS02_BOOST", "panel gate must link the current FTS02 blocker", errors)
    require(
        "docs/validation/companion-screen-wb55-ssd1681-bringup.json" in
        data.get("evidence_paths", []),
        "panel gate must link completed WB55 bring-up evidence",
        errors,
    )
    facts = data.get("required_hardware_facts", [])
    ids = {fact.get("id") for fact in facts if isinstance(fact, dict)}
    for fact_id in [
        "controller_model",
        "panel_model",
        "logic_voltage",
        "dc_pin",
        "rst_pin",
        "busy_pin",
        "full_refresh",
        "partial_refresh",
        "fast_maintenance",
        "operator_visual",
        "orientation",
        "touch_contact",
    ]:
        require(fact_id in ids, f"panel gate missing hardware fact {fact_id}", errors)
    for fact in facts:
        if isinstance(fact, dict):
            require(fact.get("status") == "verified", f"panel gate fact {fact.get('label')} must stay verified", errors)
            require(fact.get("evidence_paths"), f"panel gate fact {fact.get('label')} lost evidence", errors)
    require(PANEL_RECOVERY_GATE.exists(), "missing current panel recovery gate", errors)
    if PANEL_RECOVERY_GATE.exists():
        recovery = json.loads(PANEL_RECOVERY_GATE.read_text(encoding="utf-8"))
        require(recovery.get("status") == "DEFERRED_HARDWARE_FTS02_BOOST", "current panel recovery must remain deferred", errors)
        require(recovery.get("claim_scope") == "current_hardware_recovery_gate_no_panel_acceptance", "current recovery gate must not claim acceptance", errors)


def check_panel_adapter_boundary(errors: list[str]) -> None:
    require(
        PANEL_ADAPTER_BOUNDARY.exists(),
        f"missing panel adapter boundary fixture: {PANEL_ADAPTER_BOUNDARY.relative_to(REPO_ROOT)}",
        errors,
    )
    if not PANEL_ADAPTER_BOUNDARY.exists():
        return
    data = json.loads(PANEL_ADAPTER_BOUNDARY.read_text(encoding="utf-8"))
    require(
        data.get("schema_id") == "companion.pendant.screen_panel_adapter_boundary.v1",
        "unexpected panel adapter boundary schema",
        errors,
    )
    require(data.get("status") == "PASS", "panel adapter boundary fixture did not PASS", errors)
    contract = data.get("adapter_contract", {})
    require(
        contract.get("target_refresh_callback_type") == "comp_epaper_panel_refresh_fn_t",
        "panel adapter boundary missing callback type",
        errors,
    )
    require(
        contract.get("real_ok_source") == "target_refresh_callback_only",
        "panel adapter boundary must keep OK target-owned",
        errors,
    )
    acceptance = data.get("acceptance", {})
    for token in [
        "dry_run_still_deferred_no_panel",
        "known_panel_without_target_callback_is_transport_error",
        "real_refresh_ok_can_only_come_from_target_callback",
        "portable_adapter_has_no_board_dependencies",
        "wba_safe_target_ops_boundary",
    ]:
        require(acceptance.get(token) is True, f"panel adapter boundary acceptance missing {token}", errors)


def check_panel_adapter_behavior(errors: list[str]) -> None:
    require(
        PANEL_ADAPTER_BEHAVIOR.exists(),
        f"missing panel adapter behavior fixture: {PANEL_ADAPTER_BEHAVIOR.relative_to(REPO_ROOT)}",
        errors,
    )
    if not PANEL_ADAPTER_BEHAVIOR.exists():
        return
    data = json.loads(PANEL_ADAPTER_BEHAVIOR.read_text(encoding="utf-8"))
    require(
        data.get("schema_id") == "companion.pendant.screen_panel_adapter_behavior.v1",
        "unexpected panel adapter behavior schema",
        errors,
    )
    require(data.get("status") == "PASS", "panel adapter behavior fixture did not PASS", errors)
    cases = {case.get("case_id"): case for case in data.get("behavior_cases", []) if isinstance(case, dict)}
    for case_id in [
        "dry_run_no_panel",
        "known_panel_missing_callback",
        "target_callback_ok_default_bytes",
        "target_callback_ok_reported_bytes",
        "target_callback_busy",
        "target_callback_deferred_controller",
        "target_callback_transport_error",
    ]:
        require(case_id in cases, f"panel adapter behavior missing case {case_id}", errors)
    require(
        cases.get("target_callback_busy", {}).get("expected_render_state") == "busy",
        "panel adapter busy callback must map to busy",
        errors,
    )
    require(
        cases.get("target_callback_ok_default_bytes", {}).get("expected_last_error") == "ok",
        "panel adapter OK callback must map to ok",
        errors,
    )
    acceptance = data.get("acceptance", {})
    for token in [
        "known_panel_requires_target_callback",
        "callback_ok_maps_to_rendered_ok",
        "callback_busy_maps_to_busy_without_error_counter",
        "dispatcher_owns_request_identity",
        "wba_safe_behavior_matrix",
    ]:
        require(acceptance.get(token) is True, f"panel adapter behavior acceptance missing {token}", errors)


def check_real_ble_screen_bench(errors: list[str]) -> None:
    require(
        REAL_BLE_SCREEN_BENCH.exists(),
        f"missing real BLE screen bench fixture: {REAL_BLE_SCREEN_BENCH.relative_to(REPO_ROOT)}",
        errors,
    )
    if not REAL_BLE_SCREEN_BENCH.exists():
        return
    data = json.loads(REAL_BLE_SCREEN_BENCH.read_text(encoding="utf-8"))
    require(
        data.get("schema_id") == "companion.pendant.screen_real_ble_bench.v1",
        "unexpected real BLE screen bench schema",
        errors,
    )
    require(data.get("status") == "PASS", "real BLE screen bench fixture did not PASS", errors)
    bench = data.get("bench_operation", {})
    require(bench.get("final_status_field") == "final_card_status", "real BLE bench must capture final_card_status", errors)
    require(bench.get("real_panel_flag") == "--expect-real-panel", "real BLE bench must expose --expect-real-panel", errors)
    require(
        bench.get("real_panel_required_final", {}).get("render_state") == "rendered",
        "real BLE panel bench must require rendered final status",
        errors,
    )
    require(
        bench.get("real_panel_required_final", {}).get("last_error") == "ok",
        "real BLE panel bench must require ok final status",
        errors,
    )
    acceptance = data.get("acceptance", {})
    for token in [
        "real_bench_waits_for_final_card_status",
        "expect_real_panel_requires_rendered_ok",
        "accepted_final_identity_is_checked",
        "hardware_gate_can_reference_real_ble_artifact",
    ]:
        require(acceptance.get(token) is True, f"real BLE screen bench acceptance missing {token}", errors)


def check_panel_evidence_template(errors: list[str]) -> None:
    require(
        PANEL_EVIDENCE_TEMPLATE.exists(),
        f"missing panel evidence template: {PANEL_EVIDENCE_TEMPLATE.relative_to(REPO_ROOT)}",
        errors,
    )
    if not PANEL_EVIDENCE_TEMPLATE.exists():
        return
    data = json.loads(PANEL_EVIDENCE_TEMPLATE.read_text(encoding="utf-8"))
    require(
        data.get("schema_id") == "companion.pendant.screen_panel_evidence_template.v1",
        "unexpected panel evidence template schema",
        errors,
    )
    require(data.get("status") == "PASS", "panel evidence template fixture did not PASS", errors)
    require(
        data.get("claim_scope") == "template_only_no_real_refresh",
        "panel evidence template must not claim real refresh",
        errors,
    )
    require(set(data.get("applies_to", [])) == {"WB55", "WBA55", "WBA65"}, "panel evidence template target coverage drifted", errors)
    sections = data.get("minimum_evidence", {})
    for section, fields in {
        "panel_identity": {"controller_model", "panel_variant", "resolution_px", "waveform_lut_source"},
        "target_pin_map": {"target_family", "spi_instance_or_bus", "dc_pin", "rst_pin", "busy_pin"},
        "driver_timing": {"reset_low_ms", "busy_timeout_ms", "full_refresh_sequence", "partial_refresh_policy"},
        "host_observability": {
            "request_id",
            "content_crc32",
            "CardStatusV1_rendered",
            "e_paper.update_result",
            "real_ble_bench_artifact",
        },
        "visual_evidence": {"before_photo", "during_refresh_photo_or_video", "after_photo", "evidence_sha256"},
        "portability_notes": {"target_adapter_file", "portable_files_unchanged", "third_party_clean", "wba_equivalent_plan"},
    }.items():
        entry = sections.get(section, {})
        require(isinstance(entry, dict), f"panel evidence template missing section {section}", errors)
        actual_fields = set(entry.get("required_fields", [])) if isinstance(entry, dict) else set()
        require(fields <= actual_fields, f"panel evidence template section {section} missing fields", errors)
    final_status = data.get("host_observable_pass_criteria", {}).get("final_status", {})
    require(final_status.get("render_state") == "rendered", "panel evidence template final status must require rendered", errors)
    require(final_status.get("last_error") == "ok", "panel evidence template final status must require ok", errors)


def check_panel_evidence_record_validator(errors: list[str]) -> None:
    require(
        PANEL_EVIDENCE_RECORD_VALIDATOR.exists(),
        f"missing panel evidence record validator: {PANEL_EVIDENCE_RECORD_VALIDATOR.relative_to(REPO_ROOT)}",
        errors,
    )
    if not PANEL_EVIDENCE_RECORD_VALIDATOR.exists():
        return
    data = json.loads(PANEL_EVIDENCE_RECORD_VALIDATOR.read_text(encoding="utf-8"))
    require(
        data.get("schema_id") == "companion.pendant.screen_panel_evidence_record_validator.v1",
        "unexpected panel evidence record validator schema",
        errors,
    )
    require(data.get("status") == "PASS", "panel evidence record validator fixture did not PASS", errors)
    require(
        data.get("record_schema_id") == "companion.pendant.screen_panel_evidence_record.v1",
        "panel evidence record validator missing record schema",
        errors,
    )
    require(data.get("unblocks_gate") == "wb55_real_panel_refresh", "panel evidence record validator gate mismatch", errors)
    sections = data.get("record_required_sections", {})
    for section in ["panel_identity", "target_pin_map", "driver_timing", "host_observability", "visual_evidence", "portability_notes"]:
        require(section in sections, f"panel evidence record validator missing section {section}", errors)
    for token in [
        "real BLE artifact contains card_write and settings_sleepy_screen_status rendered/ok final statuses",
        "visual evidence files exist and after_photo SHA-256 matches evidence_sha256",
        "target adapter file exists and is target-named *_stm32wb.* or *_stm32wba.*",
    ]:
        require(token in data.get("semantic_checks", []), f"panel evidence record validator missing check {token}", errors)


def check_panel_evidence_record_scaffold(errors: list[str]) -> None:
    require(
        PANEL_EVIDENCE_RECORD_SCAFFOLD.exists(),
        f"missing panel evidence record scaffold: {PANEL_EVIDENCE_RECORD_SCAFFOLD.relative_to(REPO_ROOT)}",
        errors,
    )
    if not PANEL_EVIDENCE_RECORD_SCAFFOLD.exists():
        return
    data = json.loads(PANEL_EVIDENCE_RECORD_SCAFFOLD.read_text(encoding="utf-8"))
    require(
        data.get("schema_id") == "companion.pendant.screen_panel_evidence_record.v1",
        "unexpected panel evidence record scaffold schema",
        errors,
    )
    require(data.get("status") == "DRAFT_UNFILLED", "panel evidence record scaffold must stay DRAFT_UNFILLED", errors)
    text = json.dumps(data)
    for token in [
        "TODO_PATH_TO_EXPECT_REAL_PANEL_REAL_BLE_BENCH_JSON",
        "TODO_TARGET_ADAPTER_FILE_*_stm32wb.*",
        "TODO_AFTER_PHOTO_SHA256",
        "companion-screen-panel-wiring-preflight.json",
    ]:
        require(token in text, f"panel evidence record scaffold missing {token}", errors)
    pin_map = data.get("target_pin_map", {})
    require(pin_map.get("spi_instance_or_bus") == "SPI2", "WB55 panel evidence scaffold must prefill SPI2", errors)
    require(pin_map.get("sck_pin") == "PA9", "WB55 panel evidence scaffold must prefill PA9 SCK", errors)
    require(pin_map.get("mosi_pin") == "PC1", "WB55 panel evidence scaffold must prefill PC1 MOSI", errors)
    require(pin_map.get("miso_pin") == "PC2", "WB55 panel evidence scaffold must prefill PC2 MISO", errors)
    require(pin_map.get("cs_pin") == "PA6", "WB55 panel evidence scaffold must prefill PA6 CS", errors)
    for key in ["dc_pin", "rst_pin", "busy_pin"]:
        require("TODO" in str(pin_map.get(key, "")), f"WB55 panel evidence scaffold must leave {key} as TODO", errors)
    expected_hash = data.get("visual_evidence", {}).get("expected_fixture_sha256")
    fixture_hashes = {
        str(item.get("sha256", ""))
        for item in load_manifest(errors).get("fixtures", [])
        if isinstance(item, dict)
    }
    require(expected_hash in fixture_hashes, "panel evidence record scaffold expected fixture hash drifted", errors)


def check_panel_hardware_session(errors: list[str]) -> None:
    require(
        PANEL_HARDWARE_SESSION.exists(),
        f"missing panel hardware session fixture: {PANEL_HARDWARE_SESSION.relative_to(REPO_ROOT)}",
        errors,
    )
    if not PANEL_HARDWARE_SESSION.exists():
        return
    data = json.loads(PANEL_HARDWARE_SESSION.read_text(encoding="utf-8"))
    require(
        data.get("schema_id") == "companion.pendant.screen_panel_hardware_session.v1",
        "unexpected panel hardware session schema",
        errors,
    )
    require(data.get("status") == "PASS", "panel hardware session fixture did not PASS", errors)
    require(data.get("current_gate_status") == "DEFERRED_HARDWARE", "panel hardware session must preserve deferred gate", errors)
    contract = data.get("session_contract", {})
    for token in [
        "uses_workflow_hardware_lock",
        "session_record_starts_from_scaffold",
        "visual_before_during_after_required",
        "operator_notes_required",
        "wba_targets_do_not_inherit_wb55_pin_map",
    ]:
        require(contract.get(token) is True, f"panel hardware session contract missing {token}", errors)
    targets = {entry.get("target"): entry for entry in data.get("target_sessions", []) if isinstance(entry, dict)}
    require(set(targets) == {"WB55", "WBA55", "WBA65"}, "panel hardware session target coverage drifted", errors)
    for target, entry in targets.items():
        text = json.dumps(entry, sort_keys=True)
        require(f"companion-real-panel-{str(target).lower()}-<timestamp>" in text, f"{target} session root missing", errors)
        for token in [
            "panel-evidence-record.json",
            "companion-ble-real-bench.json",
            "diagnostics/summary.json",
            "visual/before_photo.jpg",
            "visual/after_photo.jpg",
            "operator-notes.md",
            "--expect-real-panel",
            "collect_companion_diagnostics.ps1",
            "verify_expression_panel_evidence_record.py --record",
        ]:
            require(token in text, f"{target} hardware session missing {token}", errors)
        if target == "WB55":
            require("*_stm32wb.*" in text, "WB55 hardware session missing *_stm32wb.* adapter rule", errors)
        else:
            require("*_stm32wba.*" in text, f"{target} hardware session missing *_stm32wba.* adapter rule", errors)
            for wb55_pin in ["PA9", "PC1", "PC2", "PA6"]:
                require(wb55_pin not in text, f"{target} hardware session leaked WB55 pin fact {wb55_pin}", errors)


def check_wba_panel_target_scaffold(errors: list[str]) -> None:
    require(
        PANEL_TARGET_STM32WBA.exists(),
        f"missing WBA panel target fixture: {PANEL_TARGET_STM32WBA.relative_to(REPO_ROOT)}",
        errors,
    )
    require(
        PANEL_TARGET_STM32WBA_HEADER.exists(),
        f"missing WBA panel target header: {PANEL_TARGET_STM32WBA_HEADER.relative_to(REPO_ROOT)}",
        errors,
    )
    require(
        PANEL_TARGET_STM32WBA_SOURCE.exists(),
        f"missing WBA panel target source: {PANEL_TARGET_STM32WBA_SOURCE.relative_to(REPO_ROOT)}",
        errors,
    )
    if not PANEL_TARGET_STM32WBA.exists() or not PANEL_TARGET_STM32WBA_HEADER.exists() or not PANEL_TARGET_STM32WBA_SOURCE.exists():
        return
    data = json.loads(PANEL_TARGET_STM32WBA.read_text(encoding="utf-8"))
    require(
        data.get("schema_id") == "companion.pendant.screen_panel_target_stm32wba.v1",
        "unexpected WBA panel target schema",
        errors,
    )
    require(data.get("status") == "PASS", "WBA panel target fixture did not PASS", errors)
    contract = data.get("contract", {})
    require(
        contract.get("current_transport") == "callback_bindable_dry_run_default",
        "WBA panel target must stay callback-bindable with a dry-run default",
        errors,
    )
    require(contract.get("real_refresh_claimed") is False,
            "WBA panel target must not claim real refresh", errors)
    require(contract.get("not_in_wb55_build") is True, "WBA panel target scaffold must stay out of WB55 build", errors)
    require(set(contract.get("targets", [])) == {"WBA55", "WBA65"}, "WBA panel target scaffold target coverage drifted", errors)
    text = PANEL_TARGET_STM32WBA_HEADER.read_text(encoding="utf-8") + PANEL_TARGET_STM32WBA_SOURCE.read_text(encoding="utf-8")
    for token in [
        "companion_epaper_panel_stm32wba_init",
        "companion_epaper_panel_stm32wba_bind",
        "COMPANION_EPAPER_PANEL_STM32WBA_TARGET_WBA55",
        "COMPANION_EPAPER_PANEL_STM32WBA_TARGET_WBA65",
        "comp_epaper_panel_adapter_init_dry_run(adapter)",
        "comp_epaper_panel_adapter_init(adapter, &panel_config)",
    ]:
        require(token in text, f"WBA panel target scaffold missing {token}", errors)
    for wb55_pin in ["SPI2", "PA9", "PC1", "PC2", "PA6", "SPI2_CS", "GPIO_PIN_", "HAL_SPI"]:
        require(wb55_pin not in text, f"WBA panel target scaffold leaked WB55/hardware token {wb55_pin}", errors)


def check_wba_display_scheduler_scaffold(errors: list[str]) -> None:
    require(
        SCREEN_SCHEDULER_STM32WBA.exists(),
        f"missing WBA display scheduler fixture: {SCREEN_SCHEDULER_STM32WBA.relative_to(REPO_ROOT)}",
        errors,
    )
    require(
        SCREEN_SCHEDULER_STM32WBA_HEADER.exists(),
        f"missing WBA display scheduler header: {SCREEN_SCHEDULER_STM32WBA_HEADER.relative_to(REPO_ROOT)}",
        errors,
    )
    require(
        SCREEN_SCHEDULER_STM32WBA_SOURCE.exists(),
        f"missing WBA display scheduler source: {SCREEN_SCHEDULER_STM32WBA_SOURCE.relative_to(REPO_ROOT)}",
        errors,
    )
    if not SCREEN_SCHEDULER_STM32WBA.exists() or not SCREEN_SCHEDULER_STM32WBA_HEADER.exists() or not SCREEN_SCHEDULER_STM32WBA_SOURCE.exists():
        return
    data = json.loads(SCREEN_SCHEDULER_STM32WBA.read_text(encoding="utf-8"))
    require(
        data.get("schema_id") == "companion.pendant.screen_scheduler_stm32wba.v1",
        "unexpected WBA display scheduler schema",
        errors,
    )
    require(data.get("status") == "PASS", "WBA display scheduler fixture did not PASS", errors)
    contract = data.get("contract", {})
    require(contract.get("not_in_wb55_build") is True, "WBA display scheduler scaffold must stay out of WB55 build", errors)
    require(contract.get("preserves_display_drain_contract") is True, "WBA display scheduler scaffold must preserve display drain", errors)
    require(contract.get("preserves_expression_tick_contract") is True, "WBA display scheduler scaffold must preserve expression tick", errors)
    text = SCREEN_SCHEDULER_STM32WBA_HEADER.read_text(encoding="utf-8") + SCREEN_SCHEDULER_STM32WBA_SOURCE.read_text(encoding="utf-8")
    for token in [
        "companion_epaper_stm32wba_scheduler_t",
        "companion_epaper_stm32wba_schedule_display_task",
        "companion_epaper_stm32wba_schedule_expression_tick",
        "companion_epaper_stm32wba_now_ms",
        "start_expression_tick_timer",
        "stop_expression_tick_timer",
    ]:
        require(token in text, f"WBA display scheduler scaffold missing {token}", errors)
    for platform_token in ["UTIL_SEQ", "HW_TS", "CFG_TASK_COMPANION_DISPLAY_ID", "HAL_GetTick", "CPU2", "FUS", "IPCC", "HSEM"]:
        require(platform_token not in text, f"WBA display scheduler scaffold leaked platform token {platform_token}", errors)


def check_wba_screen_gatt_scaffold(errors: list[str]) -> None:
    require(
        SCREEN_GATT_STM32WBA.exists(),
        f"missing WBA screen GATT fixture: {SCREEN_GATT_STM32WBA.relative_to(REPO_ROOT)}",
        errors,
    )
    require(
        SCREEN_GATT_STM32WBA_HEADER.exists(),
        f"missing WBA screen GATT header: {SCREEN_GATT_STM32WBA_HEADER.relative_to(REPO_ROOT)}",
        errors,
    )
    require(
        SCREEN_GATT_STM32WBA_SOURCE.exists(),
        f"missing WBA screen GATT source: {SCREEN_GATT_STM32WBA_SOURCE.relative_to(REPO_ROOT)}",
        errors,
    )
    if not SCREEN_GATT_STM32WBA.exists() or not SCREEN_GATT_STM32WBA_HEADER.exists() or not SCREEN_GATT_STM32WBA_SOURCE.exists():
        return
    data = json.loads(SCREEN_GATT_STM32WBA.read_text(encoding="utf-8"))
    require(
        data.get("schema_id") == "companion.pendant.screen_gatt_stm32wba.v1",
        "unexpected WBA screen GATT schema",
        errors,
    )
    require(data.get("status") == "PASS", "WBA screen GATT fixture did not PASS", errors)
    contract = data.get("contract", {})
    require(contract.get("not_in_wb55_build") is True, "WBA screen GATT scaffold must stay out of WB55 build", errors)
    require(contract.get("max_payload_bytes") == 248, "WBA screen GATT max payload drifted", errors)
    require(contract.get("expression_request_id_base") == "0xe0000000", "WBA screen GATT request id base drifted", errors)
    text = SCREEN_GATT_STM32WBA_HEADER.read_text(encoding="utf-8") + SCREEN_GATT_STM32WBA_SOURCE.read_text(encoding="utf-8")
    for token in [
        "companion_epaper_stm32wba_card_write_v1_t",
        "companion_epaper_stm32wba_card_status_v1_t",
        "companion_epaper_stm32wba_settings_v1_t",
        "companion_epaper_stm32wba_screen_gatt_accept_card_write",
        "companion_epaper_stm32wba_screen_gatt_publish_card_status",
        "companion_epaper_stm32wba_screen_gatt_handle_settings",
        "COMPANION_EPAPER_STM32WBA_RENDER_STATE_ACCEPTED",
        "COMPANION_EPAPER_STM32WBA_LAST_ERROR_OK",
        ".refresh_count = ++gatt->refresh_count",
    ]:
        require(token in text, f"WBA screen GATT scaffold missing {token}", errors)
    for platform_token in ["companion_gatt_stm32wb", "STM32_WPAN", "aci_gatt", "SVCCTL", "GATT_NOTIFY_ATTRIBUTE_WRITE", "UTIL_SEQ", "CPU2", "FUS", "IPCC", "HSEM"]:
        require(platform_token not in text, f"WBA screen GATT scaffold leaked platform token {platform_token}", errors)


def check_wba_cube_dependency_preflight(errors: list[str]) -> None:
    require(
        WBA_CUBE_DEPENDENCY_PREFLIGHT.exists(),
        f"missing WBA Cube dependency preflight fixture: {WBA_CUBE_DEPENDENCY_PREFLIGHT.relative_to(REPO_ROOT)}",
        errors,
    )
    if not WBA_CUBE_DEPENDENCY_PREFLIGHT.exists():
        return
    data = json.loads(WBA_CUBE_DEPENDENCY_PREFLIGHT.read_text(encoding="utf-8"))
    require(
        data.get("schema_id") == "companion.pendant.screen_wba_cube_dependency_preflight.v1",
        "unexpected WBA Cube dependency preflight schema",
        errors,
    )
    require(data.get("status") == "PASS", "WBA Cube dependency preflight fixture did not PASS", errors)
    state = data.get("local_state", {})
    require(state.get("stm32cubewb_present") is True, "WBA Cube dependency preflight must see STM32CubeWB", errors)
    require(
        state.get("mode") in {"missing_upstream_reference", "local_reference_available"},
        "WBA Cube dependency preflight has invalid local mode",
        errors,
    )
    contract = data.get("contract", {})
    require(contract.get("wba_parity_claim_allowed") is False, "WBA Cube dependency preflight must not claim parity", errors)
    require(
        contract.get("wba_port_status_until_dependency_lands") == "DRAFT_PRE_PORT",
        "WBA Cube dependency preflight must keep WBA status DRAFT_PRE_PORT",
        errors,
    )
    text = json.dumps(data, sort_keys=True)
    for token in [
        "third_party/STM32CubeWBA",
        "STM32CubeWBA package",
        "STM32CubeMX WBA BLE server generation flow",
        "screen_gatt_stm32wba",
        "screen_scheduler_stm32wba",
        "verify_expression_wba_cube_dependency_preflight.py",
    ]:
        require(token in text, f"WBA Cube dependency preflight missing {token}", errors)


def check_wba_port_scaffold(errors: list[str]) -> None:
    require(WBA55_PORT_SCAFFOLD.exists(), f"missing WBA port scaffold: {WBA55_PORT_SCAFFOLD.relative_to(REPO_ROOT)}", errors)
    if not WBA55_PORT_SCAFFOLD.exists():
        return
    data = json.loads(WBA55_PORT_SCAFFOLD.read_text(encoding="utf-8"))
    require(data.get("schema_id") == "companion.pendant.screen_wba_port_scaffold.v1", "unexpected WBA port scaffold schema", errors)
    require(data.get("status") == "DRAFT_PRE_PORT", "WBA port scaffold must stay DRAFT_PRE_PORT", errors)
    require(data.get("target") == "WBA55", "default WBA port scaffold must target WBA55", errors)
    invariants = data.get("portable_invariants", {})
    require(invariants.get("display_queue_depth") == 4, "WBA port scaffold queue depth drifted", errors)
    require(invariants.get("display_payload_max_bytes") == 236, "WBA port scaffold payload bound drifted", errors)
    require(
        invariants.get("settings_sleepy_signal") == "COMP_EPAPER_EXPRESSION_SIGNAL_SETTINGS_SLEEPY",
        "WBA port scaffold missing settings sleepy invariant",
        errors,
    )
    require(
        invariants.get("panel_callback") == "comp_epaper_panel_refresh_fn_t",
        "WBA port scaffold missing panel callback invariant",
        errors,
    )
    artifact_ids = {str(item.get("id")) for item in data.get("required_new_artifacts", []) if isinstance(item, dict)}
    for artifact_id in [
        "cube_project",
        "cube_wba_dependency_preflight",
        "build_wrapper",
        "ble_gatt_adapter",
        "ble_gatt_adapter_scaffold",
        "scheduler_timer_hook",
        "scheduler_timer_hook_scaffold",
        "panel_target_adapter_scaffold",
        "panel_transport_adapter",
        "real_ble_bench_artifact",
        "panel_evidence_record",
    ]:
        require(artifact_id in artifact_ids, f"WBA port scaffold missing artifact {artifact_id}", errors)
    text = json.dumps(data, sort_keys=True)
    for token in [
        "TODO_WBA_BLE_GATT_ADAPTER_*_stm32wba.*",
        "companion-screen-wba-cube-dependency-preflight.json",
        "verify_expression_wba_cube_dependency_preflight.py",
        "third_party/STM32CubeWBA",
        "screen_gatt_stm32wba.c",
        "verify_expression_screen_gatt_stm32wba.py",
        "companion_epaper_stm32wba_screen_gatt_accept_card_write",
        "TODO_WBA_PANEL_TRANSPORT_*_stm32wba.*",
        "panel_target_stm32wba.c",
        "verify_expression_panel_target_stm32wba.py",
        "screen_scheduler_stm32wba.c",
        "verify_expression_screen_scheduler_stm32wba.py",
        "settings_sleepy_screen_status",
        "--expect-real-panel",
        "verify_expression_panel_evidence_record.py --record",
    ]:
        require(token in text, f"WBA port scaffold missing anchor {token}", errors)


def check_expression_preview(data: dict[str, Any], errors: list[str]) -> None:
    require(PREVIEW_REPORT.exists(), f"missing expression preview report: {PREVIEW_REPORT.relative_to(REPO_ROOT)}", errors)
    require(PREVIEW_SVG.exists(), f"missing expression preview SVG: {PREVIEW_SVG.relative_to(REPO_ROOT)}", errors)
    if not PREVIEW_REPORT.exists() or not PREVIEW_SVG.exists():
        return

    report = json.loads(PREVIEW_REPORT.read_text(encoding="utf-8"))
    require(report.get("schema_id") == "companion.pendant.expression_preview.v1", "unexpected expression preview schema", errors)
    require(report.get("source_schema_id") == data.get("schema_id"), "expression preview source schema mismatch", errors)
    require(report.get("source_manifest_sha256") == sha256_hex(MANIFEST.read_bytes()), "expression preview source manifest hash is stale", errors)
    require(report.get("svg_sha256") == normalized_text_sha256(PREVIEW_SVG), "expression preview SVG hash mismatch", errors)
    require(set(report.get("expressions", [])) == EXPRESSION_KINDS, "expression preview coverage mismatch", errors)
    require({"2.13in", "1.54in"} <= set(report.get("variants", [])), "expression preview variant coverage mismatch", errors)
    expected_items = len(EXPRESSION_KINDS) * len(DISPLAY_VARIANTS)
    require(len(report.get("preview_items", [])) == expected_items, "expression preview item count mismatch", errors)
    svg_text = PREVIEW_SVG.read_text(encoding="utf-8")
    for expression in EXPRESSION_KINDS:
        require(f">{expression}<" in svg_text, f"expression preview SVG missing label {expression}", errors)


def check_expression_storyboard(errors: list[str]) -> None:
    require(STORYBOARD_REPORT.exists(), f"missing expression storyboard report: {STORYBOARD_REPORT.relative_to(REPO_ROOT)}", errors)
    require(STORYBOARD_SVG.exists(), f"missing expression storyboard SVG: {STORYBOARD_SVG.relative_to(REPO_ROOT)}", errors)
    require(JOURNEY_FIXTURE.exists(), f"missing expression journey fixture: {JOURNEY_FIXTURE.relative_to(REPO_ROOT)}", errors)
    if not STORYBOARD_REPORT.exists() or not STORYBOARD_SVG.exists() or not JOURNEY_FIXTURE.exists():
        return

    report = json.loads(STORYBOARD_REPORT.read_text(encoding="utf-8"))
    journey = json.loads(JOURNEY_FIXTURE.read_text(encoding="utf-8"))
    require(report.get("schema_id") == "companion.pendant.expression_storyboard.v1", "unexpected expression storyboard schema", errors)
    require(report.get("source_journey_schema_id") == journey.get("schema_id"), "expression storyboard source schema mismatch", errors)
    require(report.get("source_journey_sha256") == sha256_hex(JOURNEY_FIXTURE.read_bytes()), "expression storyboard source journey hash is stale", errors)
    require(report.get("source_fixture_manifest_sha256") == sha256_hex(MANIFEST.read_bytes()), "expression storyboard fixture manifest hash is stale", errors)
    require(report.get("svg_sha256") == normalized_text_sha256(STORYBOARD_SVG), "expression storyboard SVG hash mismatch", errors)
    require(report.get("visual_variant") == "2.13in", "expression storyboard visual variant drifted", errors)
    require(report.get("journey_count") == len(journey.get("journeys", [])), "expression storyboard journey count mismatch", errors)
    expected_steps = sum(len(item.get("steps", [])) for item in journey.get("journeys", []))
    require(report.get("step_count") == expected_steps, "expression storyboard step count mismatch", errors)
    require(set(report.get("coverage", [])) == EXPRESSION_KINDS, "expression storyboard coverage mismatch", errors)
    acceptance = report.get("acceptance", {})
    for token in [
        "all_journeys_rendered",
        "all_expression_states_covered",
        "accepted_and_suppressed_steps_visible",
        "uses_golden_expression_fixtures",
    ]:
        require(acceptance.get(token) is True, f"expression storyboard acceptance missing {token}", errors)
    svg_text = STORYBOARD_SVG.read_text(encoding="utf-8")
    for item in journey.get("journeys", []):
        journey_id = str(item.get("journey_id", ""))
        require(journey_id in svg_text, f"expression storyboard SVG missing journey {journey_id}", errors)
    for entry in report.get("storyboard_items", []):
        require((REPO_ROOT / str(entry.get("fixture_path", ""))).exists(), f"expression storyboard references missing fixture {entry.get('fixture_path')}", errors)


def check_hardware_boundary(errors: list[str]) -> None:
    require(README.exists(), "missing e-paper renderer README", errors)
    if not README.exists():
        return
    text = README.read_text(encoding="utf-8")
    for needle in [
        "AI-testable now",
        "Real e-paper SPI timing",
        "refresh waveform validation",
        "real BLE screen bench",
        "panel adapter behavior matrix",
        "panel hardware gate",
        "panel adapter boundary",
        "panel evidence template",
        "WBA port scaffold",
        "BLE `CardWriteV1`",
        "ExpressionV1",
    ]:
        require(needle in text, f"README missing hardware boundary anchor: {needle}", errors)


def check_no_external_requirement(errors: list[str]) -> None:
    patterns = [
        re.compile(r"\bsmart\s+base\b", re.IGNORECASE),
        re.compile(r"\bwi[- ]?fi\b", re.IGNORECASE),
        re.compile(r"\bwireless[- ]charging\b", re.IGNORECASE),
    ]
    for path in sorted(SCAN_ROOT.rglob("*")):
        if not path.is_file() or path.suffix.lower() not in {".py", ".md"}:
            continue
        text = path.read_text(encoding="utf-8")
        for pattern in patterns:
            require(not pattern.search(text), f"{path.relative_to(REPO_ROOT)} introduces external requirement: {pattern.pattern}", errors)


def main() -> int:
    errors: list[str] = []
    data = load_manifest(errors)
    if data is not None:
        check_manifest(data, errors)
        check_fixture_files(data, errors)
        check_expression_preview(data, errors)
        check_expression_storyboard(errors)
    check_ble_mapping(errors)
    check_model_render_coverage(errors)
    check_expression_rendering(errors)
    check_expression_policy(errors)
    check_expression_journeys(errors)
    check_firmware_expression_state_fixture(errors)
    check_expression_copy_contract(errors)
    check_acceptance_index(errors)
    check_status_observability(errors)
    check_display_queue_faults(errors)
    check_device_status_expression_hook(errors)
    check_interaction_status_expression_hook(errors)
    check_battery_expression_hook(errors)
    check_ota_expression_hook(errors)
    check_real_ble_screen_bench(errors)
    check_panel_adapter_behavior(errors)
    check_panel_adapter_boundary(errors)
    check_panel_gate(errors)
    check_panel_evidence_template(errors)
    check_panel_evidence_record_validator(errors)
    check_panel_evidence_record_scaffold(errors)
    check_panel_hardware_session(errors)
    check_wba_panel_target_scaffold(errors)
    check_wba_display_scheduler_scaffold(errors)
    check_wba_screen_gatt_scaffold(errors)
    check_wba_cube_dependency_preflight(errors)
    check_wba_port_scaffold(errors)
    check_hardware_boundary(errors)
    check_no_external_requirement(errors)

    if errors:
        print("FAIL: Companion e-paper asset checks failed:", file=sys.stderr)
        for error in errors:
            print(f" - {error}", file=sys.stderr)
        return 1
    print("PASS: Companion e-paper assets verified.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
