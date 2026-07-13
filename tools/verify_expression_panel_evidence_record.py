#!/usr/bin/env python3
"""Validate a filled real-panel evidence record for the screen hardware gate."""

from __future__ import annotations

import argparse
import json
import pathlib
import re
import sys
import tempfile
from typing import Any


REPO_ROOT = pathlib.Path(__file__).resolve().parents[1]
DEFAULT_FIXTURE = pathlib.Path("docs/validation/companion-screen-panel-evidence-record-validator.json")
SCHEMA_ID = "companion.pendant.screen_panel_evidence_record_validator.v1"
RECORD_SCHEMA_ID = "companion.pendant.screen_panel_evidence_record.v1"

TEMPLATE = REPO_ROOT / "docs" / "validation" / "companion-screen-panel-evidence-template.json"
PANEL_GATE = REPO_ROOT / "docs" / "validation" / "companion-screen-panel-hardware-gate.json"
ACCEPTANCE_INDEX = REPO_ROOT / "docs" / "validation" / "companion-screen-acceptance-index.json"
SCREEN_DOC = REPO_ROOT / "docs" / "companion_screen_expression_system.md"
BRINGUP_STEPS = REPO_ROOT / "docs" / "bringup_steps.md"
WBA_RULES = REPO_ROOT / "docs" / "stm32wba_migration_rules.md"
README = REPO_ROOT / "app" / "companion_pendant" / "epaper" / "README.md"
EXPRESSION_FIXTURES = REPO_ROOT / "docs" / "validation" / "companion-pendant-firmware-bringup-1.6-epaper-fixtures.json"
SCAFFOLD_TOOL = REPO_ROOT / "tools" / "init_expression_panel_evidence_record.py"
SCAFFOLD_RECORD = REPO_ROOT / "docs" / "validation" / "companion-screen-panel-evidence-record-scaffold.json"
HOST_STATUS_SEQUENCE = REPO_ROOT / "docs" / "validation" / "companion-screen-expression-host-status-sequence.json"
DEMO_HOST_STATUS_SEQUENCE = (
    REPO_ROOT / "docs" / "validation" / "companion-screen-expression-demo-host-status-sequence.json"
)
PANEL_WIRING_PREFLIGHT = REPO_ROOT / "docs" / "validation" / "companion-screen-panel-wiring-preflight.json"

TARGETS = {"WB55", "WBA55", "WBA65"}
EXPECTED_STATUS_EVENTS = [
    "boot_idle",
    "settings.display_off",
    "recording_fsm.start_request",
    "battery_charging.sample.low",
    "recording_fsm.session_finished",
    "errors.fault",
]
EXPECTED_STATUS_FACES = [
    "idle",
    "sleepy",
    "recording",
    "low_battery",
    "sync_complete",
    "error",
]
EXPECTED_STATUS_FIELDS = [
    "request_id",
    "content_crc32",
    "diagnostic_arg3",
    "accepted_refresh_count",
    "final_refresh_count",
]
EXPECTED_DEMO_STATUS_FACES = [
    "error",
    "happy",
    "idle",
    "listening",
    "low_battery",
    "recording",
    "sleepy",
    "speaking",
    "sync_complete",
    "thinking",
]
EXPECTED_DEMO_STATUS_FIELDS = [
    "request_id",
    "content_crc32",
    "diagnostic_arg3",
    "card_status",
    "dry_run_final_status",
]
PLACEHOLDER_EXACT_RE = re.compile(r"^\s*(?:todo|tbd|unknown|none|null|n/a|-)?\s*$", re.IGNORECASE)
PLACEHOLDER_TOKEN_RE = re.compile(r"(?:^|[^a-z0-9])(?:todo|tbd|unknown|null|n/a)(?:[^a-z0-9]|$)", re.IGNORECASE)


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


def load_json(path: pathlib.Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def sha256_file(path: pathlib.Path) -> str:
    import hashlib

    return hashlib.sha256(path.read_bytes()).hexdigest()


def is_placeholder_text(value: str) -> bool:
    return PLACEHOLDER_EXACT_RE.match(value) is not None or PLACEHOLDER_TOKEN_RE.search(value) is not None


def required_sections() -> dict[str, list[str]]:
    data = load_json(TEMPLATE)
    sections = data.get("minimum_evidence", {})
    return {
        str(section): [str(field) for field in entry.get("required_fields", [])]
        for section, entry in sections.items()
        if isinstance(entry, dict)
    }


def non_placeholder(value: Any) -> bool:
    if value is None:
        return False
    if isinstance(value, str):
        return not is_placeholder_text(value)
    if isinstance(value, (list, tuple)):
        return bool(value) and all(non_placeholder(item) for item in value)
    if isinstance(value, dict):
        return bool(value) and all(non_placeholder(item) for item in value.values())
    return True


def resolve_evidence_path(value: Any, record_dir: pathlib.Path) -> pathlib.Path | None:
    if not isinstance(value, str) or is_placeholder_text(value):
        return None
    if re.match(r"^[a-z]+://", value, re.IGNORECASE):
        return None
    path = pathlib.Path(value)
    if path.is_absolute():
        return path
    candidate = record_dir / path
    if candidate.exists():
        return candidate
    repo_candidate = REPO_ROOT / path
    if repo_candidate.exists():
        return repo_candidate
    if path.parts and (path.parts[0] in {"visual", "diagnostics"} or path.name == "companion-ble-real-bench.json"):
        return candidate
    return repo_candidate


def parse_crc(value: Any) -> int | None:
    if isinstance(value, int):
        return value & 0xFFFFFFFF
    if isinstance(value, str):
        text = value.strip()
        try:
            return int(text, 16 if text.lower().startswith("0x") else 10) & 0xFFFFFFFF
        except ValueError:
            return None
    return None


def parse_int(value: Any) -> int | None:
    if isinstance(value, int):
        return value
    if isinstance(value, str):
        text = value.strip()
        try:
            return int(text, 16 if text.lower().startswith("0x") else 10)
        except ValueError:
            return None
    return None


def state_value(value: Any) -> str:
    if isinstance(value, str):
        return value.strip().lower()
    return {1: "accepted", 2: "rendered", 3: "failed", 4: "busy"}.get(value, str(value))


def error_value(value: Any) -> str:
    if isinstance(value, str):
        return value.strip().lower()
    return {0: "ok", 4: "deferred_no_panel", 5: "deferred_controller_unknown"}.get(value, str(value))


def check_required_fields(record: dict[str, Any], errors: list[str]) -> None:
    for section, fields in required_sections().items():
        section_value = record.get(section, {})
        require(isinstance(section_value, dict), f"evidence record section {section} must be an object", errors)
        if not isinstance(section_value, dict):
            continue
        for field in fields:
            require(field in section_value, f"evidence record missing {section}.{field}", errors)
            require(non_placeholder(section_value.get(field)), f"evidence record has placeholder {section}.{field}", errors)


def check_panel_identity(record: dict[str, Any], errors: list[str]) -> None:
    identity = record.get("panel_identity", {})
    resolution = identity.get("resolution_px")
    require(
        isinstance(resolution, list) and len(resolution) == 2 and all(isinstance(value, int) and value > 0 for value in resolution),
        "panel_identity.resolution_px must be [width, height] positive integers",
        errors,
    )


def check_pin_map(record: dict[str, Any], errors: list[str]) -> str:
    pin_map = record.get("target_pin_map", {})
    target = str(pin_map.get("target_family", ""))
    require(target in TARGETS, f"target_pin_map.target_family must be one of {sorted(TARGETS)}", errors)
    return target


def check_timing(record: dict[str, Any], errors: list[str]) -> None:
    timing = record.get("driver_timing", {})
    for field in ["reset_low_ms", "reset_high_ms", "busy_timeout_ms"]:
        require(isinstance(timing.get(field), int) and timing.get(field) > 0, f"driver_timing.{field} must be a positive integer", errors)
    for field in ["full_refresh_sequence", "sleep_or_powerdown_sequence"]:
        require(isinstance(timing.get(field), list) and timing.get(field), f"driver_timing.{field} must be a non-empty list", errors)


def check_card_status(
    label: str,
    status: Any,
    expected_state: str,
    request_id: int,
    content_crc32: int,
    errors: list[str],
) -> None:
    require(isinstance(status, dict), f"{label} must be an object", errors)
    if not isinstance(status, dict):
        return
    require(state_value(status.get("render_state")) == expected_state, f"{label}.render_state must be {expected_state}", errors)
    require(error_value(status.get("last_error")) == "ok", f"{label}.last_error must be ok", errors)
    require(parse_int(status.get("request_id")) == request_id, f"{label}.request_id must match host_observability.request_id", errors)
    crc = parse_crc(status.get("content_crc32"))
    require(crc == content_crc32, f"{label}.content_crc32 must match host_observability.content_crc32", errors)


def check_runtime_snapshot(event: Any, errors: list[str]) -> None:
    require(isinstance(event, dict), "host_observability.e_paper.runtime_snapshot must be an object", errors)
    if not isinstance(event, dict):
        return
    if "severity" in event:
        require(str(event.get("severity", "")).lower() == "info", "runtime snapshot severity must be info for real refresh evidence", errors)
    decoded = event.get("decoded_args", {})
    require(isinstance(decoded, dict), "runtime snapshot must include decoded_args", errors)
    if not isinstance(decoded, dict):
        return
    require(decoded.get("payload") == "screen_runtime_snapshot", "runtime snapshot decoded_args.payload drifted", errors)
    expression = decoded.get("expression", {})
    queue = decoded.get("display_queue", {})
    panel = decoded.get("panel", {})
    require(isinstance(expression, dict), "runtime snapshot decoded_args.expression must be an object", errors)
    require(isinstance(queue, dict), "runtime snapshot decoded_args.display_queue must be an object", errors)
    require(isinstance(panel, dict), "runtime snapshot decoded_args.panel must be an object", errors)
    if isinstance(expression, dict):
        require(parse_int(expression.get("current")) is not None, "runtime snapshot expression.current must be numeric", errors)
        require(parse_int(expression.get("last_signal")) is not None, "runtime snapshot expression.last_signal must be numeric", errors)
    if isinstance(queue, dict):
        require(parse_int(queue.get("pending_count")) == 0, "runtime snapshot display_queue.pending_count must be 0", errors)
        require(parse_int(queue.get("dropped_count")) == 0, "runtime snapshot display_queue.dropped_count must be 0", errors)
        high_water = parse_int(queue.get("high_water_count"))
        require(high_water is not None and high_water >= 1, "runtime snapshot display_queue.high_water_count must be >= 1", errors)
    if isinstance(panel, dict):
        deferred = parse_int(panel.get("deferred_count"))
        require(deferred is not None and deferred >= 0, "runtime snapshot panel.deferred_count must be >= 0", errors)
        require(parse_int(panel.get("error_count")) == 0, "runtime snapshot panel.error_count must be 0", errors)


def check_diagnostics_bundle_artifact(path: pathlib.Path, errors: list[str]) -> None:
    require(path.exists(), f"diagnostics bundle artifact missing: {path}", errors)
    if not path.exists():
        return
    summary = load_json(path)
    require(
        summary.get("schema_id") == "companion.pendant.diagnostics_bundle.v1",
        "diagnostics bundle summary schema drifted",
        errors,
    )
    require(summary.get("bounded") is True, "diagnostics bundle must be bounded", errors)
    epaper = summary.get("epaper", {})
    require(isinstance(epaper, dict), "diagnostics bundle epaper section must be an object", errors)
    runtime = epaper.get("runtime_snapshot_decoded", {}) if isinstance(epaper, dict) else {}
    require(
        isinstance(runtime, dict),
        "diagnostics bundle must include epaper.runtime_snapshot_decoded",
        errors,
    )
    if isinstance(runtime, dict):
        require(parse_int(runtime.get("expression_current")) is not None, "diagnostics bundle expression_current must be numeric", errors)
        require(parse_int(runtime.get("expression_last_signal")) is not None, "diagnostics bundle expression_last_signal must be numeric", errors)
        require(
            parse_int(runtime.get("display_queue_pending_count")) == 0,
            "diagnostics bundle display_queue_pending_count must be 0",
            errors,
        )
        require(
            parse_int(runtime.get("display_queue_dropped_count")) == 0,
            "diagnostics bundle display_queue_dropped_count must be 0",
            errors,
        )
        high_water = parse_int(runtime.get("display_queue_high_water_count"))
        require(high_water is not None and high_water >= 1, "diagnostics bundle display_queue_high_water_count must be >= 1", errors)
        deferred = parse_int(runtime.get("panel_deferred_count"))
        require(deferred is not None and deferred >= 0, "diagnostics bundle panel_deferred_count must be >= 0", errors)
        require(parse_int(runtime.get("panel_error_count")) == 0, "diagnostics bundle panel_error_count must be 0", errors)

    diag_tail = summary.get("diag_tail", {})
    require(isinstance(diag_tail, dict), "diagnostics bundle diag_tail section must be an object", errors)
    if not isinstance(diag_tail, dict):
        return
    require(diag_tail.get("bounded") is True, "diagnostics bundle diag_tail must be bounded", errors)
    runtime_events = [
        event
        for event in diag_tail.get("events", [])
        if isinstance(event, dict) and event.get("event", {}).get("name") == "e_paper.runtime_snapshot"
    ]
    require(runtime_events, "diagnostics bundle diag_tail must include e_paper.runtime_snapshot", errors)
    if not runtime_events:
        return
    decoded = runtime_events[-1].get("decoded_args", {})
    require(isinstance(decoded, dict), "diagnostics bundle runtime event must include decoded_args", errors)
    if not isinstance(decoded, dict):
        return
    require(decoded.get("payload") == "screen_runtime_snapshot", "diagnostics bundle runtime event payload drifted", errors)
    queue = decoded.get("display_queue", {})
    panel = decoded.get("panel", {})
    require(isinstance(queue, dict), "diagnostics bundle runtime event display_queue must be an object", errors)
    require(isinstance(panel, dict), "diagnostics bundle runtime event panel must be an object", errors)
    if isinstance(queue, dict):
        require(parse_int(queue.get("pending_count")) == 0, "diagnostics bundle runtime event pending_count must be 0", errors)
        require(parse_int(queue.get("dropped_count")) == 0, "diagnostics bundle runtime event dropped_count must be 0", errors)
    if isinstance(panel, dict):
        require(parse_int(panel.get("error_count")) == 0, "diagnostics bundle runtime event panel.error_count must be 0", errors)


def bench_operations(artifact: dict[str, Any]) -> dict[str, dict[str, Any]]:
    return {
        str(operation.get("operation", "")): operation
        for operation in artifact.get("operations", [])
        if isinstance(operation, dict)
    }


def check_real_ble_expression_status_sequence(operations: dict[str, dict[str, Any]], errors: list[str]) -> None:
    operation = operations.get("screen_expression_status")
    require(operation is not None, "real BLE artifact missing operation screen_expression_status", errors)
    if operation is None:
        return
    require(operation.get("status") == "PASS", "screen_expression_status operation must be PASS", errors)
    require(operation.get("contract_only") is True, "screen_expression_status operation must be contract-only", errors)
    require(operation.get("hardware_collected") is False, "screen_expression_status operation must not claim hardware collection", errors)
    require(
        operation.get("host_sequence_fixture") == rel(HOST_STATUS_SEQUENCE),
        "screen_expression_status operation must link host sequence fixture",
        errors,
    )
    require(
        operation.get("expected_events") == EXPECTED_STATUS_EVENTS,
        "screen_expression_status expected event list drifted",
        errors,
    )
    require(
        operation.get("required_faces") == EXPECTED_STATUS_FACES,
        "screen_expression_status required face list drifted",
        errors,
    )
    for field in EXPECTED_STATUS_FIELDS:
        require(
            field in operation.get("required_fields", []),
            f"screen_expression_status required_fields missing {field}",
            errors,
        )
    require(
        operation.get("content_crc32_model") == "comp_epaper_expression_decision_crc32",
        "screen_expression_status content_crc32 model drifted",
        errors,
    )
    require(
        operation.get("diagnostic_arg3_model") == "(expression_id << 16) | signal_id",
        "screen_expression_status diagnostic arg3 model drifted",
        errors,
    )


def check_real_ble_expression_demo_status_sequence(operations: dict[str, dict[str, Any]], errors: list[str]) -> None:
    operation = operations.get("screen_expression_demo_status")
    require(operation is not None, "real BLE artifact missing operation screen_expression_demo_status", errors)
    if operation is None:
        return
    require(operation.get("status") == "PASS", "screen_expression_demo_status operation must be PASS", errors)
    require(operation.get("contract_only") is True, "screen_expression_demo_status operation must be contract-only", errors)
    require(
        operation.get("hardware_collected") is False,
        "screen_expression_demo_status operation must not claim hardware collection",
        errors,
    )
    require(
        operation.get("host_sequence_fixture") == rel(DEMO_HOST_STATUS_SEQUENCE),
        "screen_expression_demo_status operation must link demo host sequence fixture",
        errors,
    )
    require(
        operation.get("required_faces") == EXPECTED_DEMO_STATUS_FACES,
        "screen_expression_demo_status required face list drifted",
        errors,
    )
    require(
        operation.get("accepted_status_pair_count") == 29,
        "screen_expression_demo_status accepted pair count drifted",
        errors,
    )
    require(
        operation.get("held_no_status_count") == 8,
        "screen_expression_demo_status held count drifted",
        errors,
    )
    require(
        operation.get("held_steps_contract") == "held_steps_emit_no_host_status",
        "screen_expression_demo_status held step contract drifted",
        errors,
    )
    for field in EXPECTED_DEMO_STATUS_FIELDS:
        require(
            field in operation.get("required_fields", []),
            f"screen_expression_demo_status required_fields missing {field}",
            errors,
        )
    require(
        operation.get("content_crc32_model") == "comp_epaper_expression_decision_crc32",
        "screen_expression_demo_status content_crc32 model drifted",
        errors,
    )
    require(
        operation.get("diagnostic_arg3_model") == "(expression_id << 16) | signal_id",
        "screen_expression_demo_status diagnostic arg3 model drifted",
        errors,
    )


def check_real_ble_artifact(path: pathlib.Path, errors: list[str]) -> None:
    require(path.exists(), f"real BLE bench artifact missing: {path}", errors)
    if not path.exists():
        return
    artifact = load_json(path)
    require(artifact.get("status") == "PASS", "real BLE bench artifact must be PASS", errors)
    operations = bench_operations(artifact)
    check_real_ble_expression_status_sequence(operations, errors)
    check_real_ble_expression_demo_status_sequence(operations, errors)
    for operation_name in ["card_write", "settings_sleepy_screen_status"]:
        operation = operations.get(operation_name)
        require(operation is not None, f"real BLE artifact missing operation {operation_name}", errors)
        if not operation:
            continue
        require(operation.get("real_panel_refresh_claimed") is True, f"{operation_name} must claim real panel refresh", errors)
        final = operation.get("final_card_status", {})
        require(isinstance(final, dict), f"{operation_name}.final_card_status must be an object", errors)
        if isinstance(final, dict):
            require(state_value(final.get("render_state")) == "rendered", f"{operation_name}.final_card_status must be rendered", errors)
            require(error_value(final.get("last_error")) == "ok", f"{operation_name}.final_card_status last_error must be ok", errors)


def check_observability(record: dict[str, Any], record_dir: pathlib.Path, errors: list[str]) -> tuple[int, int]:
    host = record.get("host_observability", {})
    request_id = int(host.get("request_id", -1)) if isinstance(host.get("request_id"), int) else -1
    content_crc32 = parse_crc(host.get("content_crc32"))
    require(request_id > 0, "host_observability.request_id must be a positive integer", errors)
    require(content_crc32 is not None, "host_observability.content_crc32 must be an integer or 0x hex string", errors)
    content_crc32_value = 0 if content_crc32 is None else content_crc32
    check_card_status("host_observability.CardStatusV1_accepted", host.get("CardStatusV1_accepted"), "accepted", request_id, content_crc32_value, errors)
    check_card_status("host_observability.CardStatusV1_rendered", host.get("CardStatusV1_rendered"), "rendered", request_id, content_crc32_value, errors)
    for label in ["e_paper.render_request", "e_paper.update_result"]:
        event = host.get(label, {})
        require(isinstance(event, dict), f"host_observability.{label} must be an object", errors)
        if isinstance(event, dict):
            require(parse_int(event.get("request_id")) == request_id, f"host_observability.{label}.request_id must match", errors)
            require(parse_crc(event.get("content_crc32")) == content_crc32_value, f"host_observability.{label}.content_crc32 must match", errors)
    check_runtime_snapshot(host.get("e_paper.runtime_snapshot"), errors)
    diagnostics_path = resolve_evidence_path(host.get("diagnostics_bundle_artifact"), record_dir)
    require(diagnostics_path is not None, "host_observability.diagnostics_bundle_artifact must be a local artifact path", errors)
    if diagnostics_path is not None:
        check_diagnostics_bundle_artifact(diagnostics_path, errors)
    artifact_path = resolve_evidence_path(host.get("real_ble_bench_artifact"), record_dir)
    require(artifact_path is not None, "host_observability.real_ble_bench_artifact must be a local artifact path", errors)
    if artifact_path is not None:
        check_real_ble_artifact(artifact_path, errors)
    return request_id, content_crc32_value


def known_fixture_hashes() -> set[str]:
    data = load_json(EXPRESSION_FIXTURES)
    return {str(item.get("sha256", "")) for item in data.get("fixtures", []) if isinstance(item, dict)}


def check_visual(record: dict[str, Any], record_dir: pathlib.Path, errors: list[str]) -> None:
    visual = record.get("visual_evidence", {})
    paths: dict[str, pathlib.Path] = {}
    for field in ["before_photo", "during_refresh_photo_or_video", "after_photo"]:
        path = resolve_evidence_path(visual.get(field), record_dir)
        require(path is not None and path.exists(), f"visual_evidence.{field} must point at an existing local file", errors)
        if path is not None and path.exists():
            paths[field] = path
    expected_hash = str(visual.get("expected_fixture_sha256", ""))
    require(expected_hash in known_fixture_hashes(), "visual_evidence.expected_fixture_sha256 must match a golden expression fixture", errors)
    if "after_photo" in paths:
        require(
            str(visual.get("evidence_sha256", "")).lower() == sha256_file(paths["after_photo"]).lower(),
            "visual_evidence.evidence_sha256 must match after_photo SHA-256",
            errors,
        )


def check_portability(record: dict[str, Any], record_dir: pathlib.Path, target: str, errors: list[str]) -> None:
    notes = record.get("portability_notes", {})
    adapter_path = resolve_evidence_path(notes.get("target_adapter_file"), record_dir)
    require(adapter_path is not None and adapter_path.exists(), "portability_notes.target_adapter_file must exist", errors)
    adapter_name = str(notes.get("target_adapter_file", "")).lower()
    if target == "WB55":
        require("stm32wb" in adapter_name, "WB55 target adapter file must be target-named with stm32wb", errors)
    if target.startswith("WBA"):
        require("stm32wba" in adapter_name, f"{target} target adapter file must be target-named with stm32wba", errors)
    require(notes.get("portable_files_unchanged") is True, "portability_notes.portable_files_unchanged must be true", errors)
    require(notes.get("third_party_clean") is True, "portability_notes.third_party_clean must be true", errors)
    require(non_placeholder(notes.get("wba_equivalent_plan")), "portability_notes.wba_equivalent_plan must be filled", errors)


def validate_record(record: dict[str, Any], record_path: pathlib.Path) -> list[str]:
    errors: list[str] = []
    record_dir = record_path.parent
    require(record.get("schema_id") == RECORD_SCHEMA_ID, f"evidence record schema_id must be {RECORD_SCHEMA_ID}", errors)
    require(record.get("status") == "PASS", "evidence record status must be PASS", errors)
    require(record.get("claim_scope") == "real_panel_refresh", "evidence record claim_scope must be real_panel_refresh", errors)
    check_required_fields(record, errors)
    check_panel_identity(record, errors)
    target = check_pin_map(record, errors)
    check_timing(record, errors)
    check_observability(record, record_dir, errors)
    check_visual(record, record_dir, errors)
    check_portability(record, record_dir, target, errors)
    return errors


def build_fixture() -> dict[str, Any]:
    template = load_json(TEMPLATE)
    return {
        "schema_id": SCHEMA_ID,
        "status": "PASS",
        "sources": {
            "template": rel(TEMPLATE),
            "scaffold_tool": rel(SCAFFOLD_TOOL),
            "scaffold_record": rel(SCAFFOLD_RECORD),
            "panel_gate": rel(PANEL_GATE),
            "acceptance_index": rel(ACCEPTANCE_INDEX),
            "screen_acceptance": rel(SCREEN_DOC),
            "bringup_steps": rel(BRINGUP_STEPS),
            "wba_rules": rel(WBA_RULES),
            "epaper_readme": rel(README),
            "host_expression_status_sequence": rel(HOST_STATUS_SEQUENCE),
            "demo_host_expression_status_sequence": rel(DEMO_HOST_STATUS_SEQUENCE),
            "panel_wiring_preflight": rel(PANEL_WIRING_PREFLIGHT),
        },
        "record_schema_id": RECORD_SCHEMA_ID,
        "template_id": template.get("template_id"),
        "unblocks_gate": "wb55_real_panel_refresh",
        "record_required_sections": required_sections(),
        "semantic_checks": [
            "all template fields are present and non-placeholder",
            "placeholder tokens such as TODO_CONTROLLER_MODEL are rejected recursively",
            "CardStatusV1 accepted/rendered statuses match request_id and content_crc32",
            "e_paper.runtime_snapshot decoded_args show zero panel errors, zero pending display work, and zero dropped display work",
            "diagnostics bundle summary carries epaper.runtime_snapshot_decoded with zero panel errors, zero pending display work, and zero dropped display work",
            "real BLE artifact contains card_write and settings_sleepy_screen_status rendered/ok final statuses",
            "real BLE artifact contains screen_expression_status six-face host sequence baseline",
            "real BLE artifact contains screen_expression_demo_status full demo host sequence baseline",
            "visual evidence files exist and after_photo SHA-256 matches evidence_sha256",
            "expected_fixture_sha256 matches a golden ExpressionV1 fixture",
            "target adapter file exists and is target-named *_stm32wb.* or *_stm32wba.*",
            "WB55 scaffold pre-fills SPI2 PA9/PC1/PC2/PA6 from the panel wiring preflight while leaving controller/DC/RST/BUSY as TODOs",
            "portable_files_unchanged and third_party_clean are true",
            "scaffold records stay DRAFT_UNFILLED and cannot satisfy the real refresh gate",
        ],
        "self_test_cases": [
            "valid_wb55_record_passes",
            "draft_record_fails",
            "placeholder_token_fails",
            "missing_required_field_fails",
            "deferred_no_panel_final_status_fails",
            "identity_drift_fails",
            "runtime_panel_error_fails",
            "runtime_pending_queue_fails",
            "diagnostics_bundle_panel_error_fails",
            "missing_visual_artifact_fails",
            "missing_screen_expression_status_fails",
            "missing_screen_expression_demo_status_fails",
        ],
        "validation_commands": [
            "python .\\tools\\init_expression_panel_evidence_record.py",
            "python .\\tools\\verify_expression_panel_evidence_record.py --self-test",
            "python .\\tools\\verify_expression_panel_evidence_template.py",
            "python .\\tools\\verify_expression_panel_gate.py",
            "python .\\tools\\verify_expression_panel_wiring_preflight.py",
            "python .\\tools\\verify_expression_real_ble_screen_bench.py",
            "python .\\tools\\verify_expression_host_status_sequence.py",
            "python .\\tools\\verify_companion_diagnostics_static.py",
        ],
    }


def write_text(path: pathlib.Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def build_self_test_record(root: pathlib.Path) -> pathlib.Path:
    media = root / "media"
    media.mkdir(parents=True, exist_ok=True)
    before = media / "before.bin"
    during = media / "during.bin"
    after = media / "after.bin"
    adapter = root / "companion_epaper_panel_stm32wb.c"
    bench = root / "real_ble_bench.json"
    diagnostics = root / "diagnostics_summary.json"
    before.write_bytes(b"before-panel")
    during.write_bytes(b"during-panel")
    after.write_bytes(b"after-panel-rendered")
    adapter.write_text("/* target-owned stm32wb panel adapter */\n", encoding="utf-8")
    content_crc32 = "0x1234abcd"
    request_id = 17
    bench.write_text(
        json.dumps(
            {
                "status": "PASS",
                "operations": [
                    {
                        "operation": "screen_expression_status",
                        "status": "PASS",
                        "contract_only": True,
                        "hardware_collected": False,
                        "host_sequence_fixture": rel(HOST_STATUS_SEQUENCE),
                        "expected_events": EXPECTED_STATUS_EVENTS,
                        "required_faces": EXPECTED_STATUS_FACES,
                        "required_fields": EXPECTED_STATUS_FIELDS,
                        "content_crc32_model": "comp_epaper_expression_decision_crc32",
                        "diagnostic_arg3_model": "(expression_id << 16) | signal_id",
                    },
                    {
                        "operation": "screen_expression_demo_status",
                        "status": "PASS",
                        "contract_only": True,
                        "hardware_collected": False,
                        "host_sequence_fixture": rel(DEMO_HOST_STATUS_SEQUENCE),
                        "required_faces": EXPECTED_DEMO_STATUS_FACES,
                        "required_fields": EXPECTED_DEMO_STATUS_FIELDS,
                        "accepted_status_pair_count": 29,
                        "held_no_status_count": 8,
                        "held_steps_contract": "held_steps_emit_no_host_status",
                        "content_crc32_model": "comp_epaper_expression_decision_crc32",
                        "diagnostic_arg3_model": "(expression_id << 16) | signal_id",
                    },
                    {
                        "operation": "card_write",
                        "real_panel_refresh_claimed": True,
                        "final_card_status": {
                            "render_state": 2,
                            "last_error": 0,
                            "request_id": request_id,
                            "content_crc32": content_crc32,
                        },
                    },
                    {
                        "operation": "settings_sleepy_screen_status",
                        "real_panel_refresh_claimed": True,
                        "final_card_status": {
                            "render_state": 2,
                            "last_error": 0,
                            "request_id": 0xE0000001,
                            "content_crc32": "0x00000001",
                        },
                    },
                ],
            },
            indent=2,
            sort_keys=True,
        )
        + "\n",
        encoding="utf-8",
    )
    diagnostics.write_text(
        json.dumps(
            {
                "schema_id": "companion.pendant.diagnostics_bundle.v1",
                "schema_version": 1,
                "bounded": True,
                "epaper": {
                    "render_state": "rendered",
                    "content_crc32": content_crc32,
                    "runtime_snapshot_decoded": {
                        "expression_current": 0,
                        "expression_last_signal": 0,
                        "display_queue_pending_count": 0,
                        "display_queue_high_water_count": 1,
                        "display_queue_dropped_count": 0,
                        "panel_deferred_count": 0,
                        "panel_error_count": 0,
                    },
                },
                "diag_tail": {
                    "bounded": True,
                    "events": [
                        {
                            "event": {"name": "e_paper.runtime_snapshot"},
                            "decoded_args": {
                                "payload": "screen_runtime_snapshot",
                                "expression": {
                                    "current": 0,
                                    "last_signal": 0,
                                },
                                "display_queue": {
                                    "pending_count": 0,
                                    "high_water_count": 1,
                                    "dropped_count": 0,
                                },
                                "panel": {
                                    "deferred_count": 0,
                                    "error_count": 0,
                                },
                            },
                        }
                    ],
                },
            },
            indent=2,
            sort_keys=True,
        )
        + "\n",
        encoding="utf-8",
    )
    fixture_hash = next(iter(known_fixture_hashes()))
    record = {
        "schema_id": RECORD_SCHEMA_ID,
        "status": "PASS",
        "claim_scope": "real_panel_refresh",
        "panel_identity": {
            "controller_model": "UC8151D",
            "panel_variant": "2.13in",
            "resolution_px": [250, 122],
            "datasheet_revision": "rev-a",
            "waveform_lut_source": "controller otp",
        },
        "target_pin_map": {
            "target_family": "WB55",
            "spi_instance_or_bus": "SPI1",
            "sck_pin": "PA5",
            "mosi_pin": "PA7",
            "cs_pin": "PB6",
            "dc_pin": "PB7",
            "rst_pin": "PB8",
            "busy_pin": "PB9",
            "power_enable_pin": "PB5",
            "logic_voltage": "3.3V",
        },
        "driver_timing": {
            "reset_low_ms": 10,
            "reset_high_ms": 10,
            "busy_timeout_ms": 5000,
            "full_refresh_sequence": ["reset", "power_on", "write_ram", "display_refresh", "wait_busy"],
            "partial_refresh_policy": "disabled until controller LUT is validated",
            "sleep_or_powerdown_sequence": ["deep_sleep"],
        },
        "host_observability": {
            "request_id": request_id,
            "content_crc32": content_crc32,
            "CardStatusV1_accepted": {
                "render_state": "accepted",
                "last_error": "ok",
                "request_id": request_id,
                "content_crc32": content_crc32,
            },
            "CardStatusV1_rendered": {
                "render_state": "rendered",
                "last_error": "ok",
                "request_id": request_id,
                "content_crc32": content_crc32,
            },
            "e_paper.render_request": {
                "request_id": request_id,
                "content_crc32": content_crc32,
            },
            "e_paper.update_result": {
                "request_id": request_id,
                "content_crc32": content_crc32,
                "panel_result": "ok",
            },
            "e_paper.runtime_snapshot": {
                "severity": "info",
                "decoded_args": {
                    "payload": "screen_runtime_snapshot",
                    "expression": {
                        "current": 0,
                        "last_signal": 0,
                    },
                    "display_queue": {
                        "pending_count": 0,
                        "high_water_count": 1,
                        "dropped_count": 0,
                    },
                    "panel": {
                        "deferred_count": 0,
                        "error_count": 0,
                    },
                },
            },
            "diagnostics_bundle_artifact": rel(diagnostics),
            "real_ble_bench_artifact": rel(bench),
        },
        "visual_evidence": {
            "before_photo": rel(before),
            "during_refresh_photo_or_video": rel(during),
            "after_photo": rel(after),
            "expected_expression": "idle",
            "expected_fixture_sha256": fixture_hash,
            "evidence_sha256": sha256_file(after),
        },
        "portability_notes": {
            "target_adapter_file": rel(adapter),
            "portable_files_unchanged": True,
            "third_party_clean": True,
            "wba_equivalent_plan": "reuse the same callback contract from a target-named stm32wba adapter",
        },
    }
    record_path = root / "panel_evidence_record.json"
    record_path.write_text(json.dumps(record, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return record_path


def run_self_test() -> list[str]:
    errors: list[str] = []
    with tempfile.TemporaryDirectory() as tmp:
        root = pathlib.Path(tmp)
        record_path = build_self_test_record(root)
        record = load_json(record_path)
        valid_errors = validate_record(record, record_path)
        require(not valid_errors, f"valid self-test record failed: {valid_errors}", errors)

        draft = json.loads(json.dumps(record))
        draft["status"] = "DRAFT_UNFILLED"
        require(validate_record(draft, record_path), "draft record self-test did not fail", errors)

        placeholder = json.loads(json.dumps(record))
        placeholder["panel_identity"]["controller_model"] = "TODO_CONTROLLER_MODEL"
        require(validate_record(placeholder, record_path), "placeholder token self-test did not fail", errors)

        placeholder_list = json.loads(json.dumps(record))
        placeholder_list["driver_timing"]["full_refresh_sequence"] = ["reset", "TODO_WRITE_RAM"]
        require(validate_record(placeholder_list, record_path), "placeholder token in list self-test did not fail", errors)

        missing = json.loads(json.dumps(record))
        del missing["panel_identity"]["controller_model"]
        require(validate_record(missing, record_path), "missing required field self-test did not fail", errors)

        deferred = json.loads(json.dumps(record))
        deferred["host_observability"]["CardStatusV1_rendered"]["render_state"] = "failed"
        deferred["host_observability"]["CardStatusV1_rendered"]["last_error"] = "deferred_no_panel"
        require(validate_record(deferred, record_path), "deferred no-panel self-test did not fail", errors)

        drift = json.loads(json.dumps(record))
        drift["host_observability"]["CardStatusV1_rendered"]["request_id"] = 99
        require(validate_record(drift, record_path), "identity drift self-test did not fail", errors)

        runtime_error = json.loads(json.dumps(record))
        runtime_error["host_observability"]["e_paper.runtime_snapshot"]["severity"] = "warn"
        runtime_error["host_observability"]["e_paper.runtime_snapshot"]["decoded_args"]["panel"]["error_count"] = 1
        require(validate_record(runtime_error, record_path), "runtime panel error self-test did not fail", errors)

        runtime_pending = json.loads(json.dumps(record))
        runtime_pending["host_observability"]["e_paper.runtime_snapshot"]["decoded_args"]["display_queue"]["pending_count"] = 1
        require(validate_record(runtime_pending, record_path), "runtime pending queue self-test did not fail", errors)

        diagnostics_error = json.loads(json.dumps(record))
        diagnostics_path = root / "diagnostics_summary_panel_error.json"
        diagnostics_artifact = load_json(root / "diagnostics_summary.json")
        diagnostics_artifact["epaper"]["runtime_snapshot_decoded"]["panel_error_count"] = 1
        diagnostics_artifact["diag_tail"]["events"][0]["decoded_args"]["panel"]["error_count"] = 1
        diagnostics_path.write_text(json.dumps(diagnostics_artifact, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        diagnostics_error["host_observability"]["diagnostics_bundle_artifact"] = rel(diagnostics_path)
        require(validate_record(diagnostics_error, record_path), "diagnostics bundle panel error self-test did not fail", errors)

        missing_visual = json.loads(json.dumps(record))
        missing_visual["visual_evidence"]["after_photo"] = "missing-after.bin"
        require(validate_record(missing_visual, record_path), "missing visual artifact self-test did not fail", errors)

        missing_sequence = json.loads(json.dumps(record))
        bench_path = root / "real_ble_bench_missing_sequence.json"
        bench_artifact = load_json(root / "real_ble_bench.json")
        bench_artifact["operations"] = [
            operation
            for operation in bench_artifact.get("operations", [])
            if operation.get("operation") != "screen_expression_status"
        ]
        bench_path.write_text(json.dumps(bench_artifact, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        missing_sequence["host_observability"]["real_ble_bench_artifact"] = rel(bench_path)
        require(validate_record(missing_sequence, record_path), "missing screen_expression_status self-test did not fail", errors)

        missing_demo_sequence = json.loads(json.dumps(record))
        demo_bench_path = root / "real_ble_bench_missing_demo_sequence.json"
        demo_bench_artifact = load_json(root / "real_ble_bench.json")
        demo_bench_artifact["operations"] = [
            operation
            for operation in demo_bench_artifact.get("operations", [])
            if operation.get("operation") != "screen_expression_demo_status"
        ]
        demo_bench_path.write_text(json.dumps(demo_bench_artifact, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        missing_demo_sequence["host_observability"]["real_ble_bench_artifact"] = rel(demo_bench_path)
        require(
            validate_record(missing_demo_sequence, record_path),
            "missing screen_expression_demo_status self-test did not fail",
            errors,
        )
    return errors


def check_fixture_data(data: dict[str, Any], errors: list[str]) -> None:
    require(data.get("schema_id") == SCHEMA_ID, "unexpected panel evidence record validator schema", errors)
    require(data.get("status") == "PASS", "panel evidence record validator fixture must be PASS", errors)
    require(data.get("record_schema_id") == RECORD_SCHEMA_ID, "fixture missing record schema id", errors)
    require(data.get("unblocks_gate") == "wb55_real_panel_refresh", "fixture must point at real panel gate", errors)
    sections = data.get("record_required_sections", {})
    for section in ["panel_identity", "target_pin_map", "driver_timing", "host_observability", "visual_evidence", "portability_notes"]:
        require(section in sections, f"fixture missing required section {section}", errors)
    for token in [
        "placeholder tokens such as TODO_CONTROLLER_MODEL are rejected recursively",
        "CardStatusV1 accepted/rendered statuses match request_id and content_crc32",
        "e_paper.runtime_snapshot decoded_args show zero panel errors, zero pending display work, and zero dropped display work",
        "diagnostics bundle summary carries epaper.runtime_snapshot_decoded with zero panel errors, zero pending display work, and zero dropped display work",
        "real BLE artifact contains card_write and settings_sleepy_screen_status rendered/ok final statuses",
        "real BLE artifact contains screen_expression_status six-face host sequence baseline",
        "real BLE artifact contains screen_expression_demo_status full demo host sequence baseline",
        "visual evidence files exist and after_photo SHA-256 matches evidence_sha256",
        "target adapter file exists and is target-named *_stm32wb.* or *_stm32wba.*",
        "WB55 scaffold pre-fills SPI2 PA9/PC1/PC2/PA6 from the panel wiring preflight while leaving controller/DC/RST/BUSY as TODOs",
    ]:
        require(token in data.get("semantic_checks", []), f"fixture missing semantic check {token}", errors)
    for case in [
        "valid_wb55_record_passes",
        "placeholder_token_fails",
        "deferred_no_panel_final_status_fails",
        "identity_drift_fails",
        "runtime_panel_error_fails",
        "runtime_pending_queue_fails",
        "diagnostics_bundle_panel_error_fails",
        "missing_screen_expression_status_fails",
        "missing_screen_expression_demo_status_fails",
    ]:
        require(case in data.get("self_test_cases", []), f"fixture missing self-test case {case}", errors)
    require("scaffold_record" in data.get("sources", {}), "fixture missing scaffold record source", errors)


def check_project_links(fixture_rel: str, errors: list[str]) -> None:
    screen_doc = read(SCREEN_DOC, errors)
    bringup = read(BRINGUP_STEPS, errors)
    wba_rules = read(WBA_RULES, errors)
    readme = read(README, errors)
    gate = read(PANEL_GATE, errors)
    index_text = read(ACCEPTANCE_INDEX, errors)
    template = read(TEMPLATE, errors)
    scaffold = read(SCAFFOLD_RECORD, errors)
    for token in [
        "init_expression_panel_evidence_record.py",
        "verify_expression_panel_evidence_record.py",
        "companion-screen-panel-evidence-record-validator.json",
        "real_ble_bench_artifact",
        "diagnostics_bundle_artifact",
        "screen_expression_status",
        "screen_expression_demo_status",
        "companion-screen-expression-host-status-sequence.json",
        "companion-screen-expression-demo-host-status-sequence.json",
    ]:
        require(token in screen_doc, f"screen doc missing panel evidence record anchor {token}", errors)
    for token in [
        "verify_expression_panel_evidence_record.py --record",
        "real_ble_bench_artifact",
        "diagnostics_bundle_artifact",
        "collect_companion_diagnostics.ps1",
        "e_paper.runtime_snapshot",
        "panel.error_count=0",
        "screen_expression_status",
        "screen_expression_demo_status",
    ]:
        require(token in bringup, f"bringup steps missing panel evidence record anchor {token}", errors)
    require("evidence record validator" in wba_rules.lower(), "WBA rules missing evidence record validator note", errors)
    require("evidence record validator" in readme.lower(), "e-paper README missing evidence record validator note", errors)
    require("real_ble_bench_artifact" in template, "panel evidence template must require real_ble_bench_artifact", errors)
    require("diagnostics_bundle_artifact" in template, "panel evidence template must require diagnostics_bundle_artifact", errors)
    require("screen_expression_status" in template, "panel evidence template must require screen_expression_status", errors)
    require("screen_expression_demo_status" in template, "panel evidence template must require screen_expression_demo_status", errors)
    require("e_paper.runtime_snapshot" in template, "panel evidence template must require runtime snapshot diagnostics", errors)
    require("runtime snapshot" in template.lower(), "panel evidence template must explain runtime snapshot checks", errors)
    require("DRAFT_UNFILLED" in scaffold, "panel evidence scaffold must stay a draft", errors)
    require("e_paper.runtime_snapshot" in scaffold, "panel evidence scaffold must include runtime snapshot placeholder", errors)
    require("diagnostics_bundle_artifact" in scaffold, "panel evidence scaffold must include diagnostics bundle placeholder", errors)
    require("companion-screen-panel-wiring-preflight.json" in scaffold, "panel evidence scaffold must link panel wiring preflight", errors)
    require("screen_expression_demo_status" in scaffold, "panel evidence scaffold must mention screen_expression_demo_status", errors)
    require('"spi_instance_or_bus": "SPI2"' in scaffold, "WB55 panel evidence scaffold must prefill SPI2", errors)
    require('"sck_pin": "PA9"' in scaffold, "WB55 panel evidence scaffold must prefill PA9 SCK", errors)
    require('"mosi_pin": "PC1"' in scaffold, "WB55 panel evidence scaffold must prefill PC1 MOSI", errors)
    require('"miso_pin": "PC2"' in scaffold, "WB55 panel evidence scaffold must prefill PC2 MISO", errors)
    require('"cs_pin": "PA6"' in scaffold, "WB55 panel evidence scaffold must prefill PA6 CS", errors)
    for token in ['"dc_pin": "TODO_DC_PIN"', '"rst_pin": "TODO_RST_PIN"', '"busy_pin": "TODO_BUSY_PIN"']:
        require(token in scaffold, f"WB55 panel evidence scaffold must keep {token} until hardware review", errors)
    require(fixture_rel in gate, "panel hardware gate must link evidence record validator fixture", errors)
    require(fixture_rel in index_text, "acceptance index must link evidence record validator fixture", errors)
    if index_text:
        index = json.loads(index_text)
        items = [item for item in index.get("items", []) if item.get("id") == "panel_evidence_record_validator"]
        require(len(items) == 1, "acceptance index must contain one panel_evidence_record_validator item", errors)
        if items:
            item = items[0]
            require(item.get("status") == "PASS", "panel_evidence_record_validator item must be PASS", errors)
            require(fixture_rel in item.get("evidence_paths", []), "panel evidence record validator item missing fixture", errors)
            require(
                "python .\\tools\\verify_expression_panel_evidence_record.py --self-test" in item.get("validation_commands", []),
                "panel evidence record validator item missing self-test command",
                errors,
            )


def check_fixture_file(path: pathlib.Path, expected: dict[str, Any], errors: list[str]) -> None:
    require(path.exists(), f"missing panel evidence record validator fixture: {rel(path)}", errors)
    if not path.exists():
        return
    actual = json.loads(path.read_text(encoding="utf-8"))
    require(actual == expected, f"{rel(path)} is stale; rerun with --write-fixture", errors)
    check_fixture_data(actual, errors)


def parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--fixture", type=pathlib.Path, default=DEFAULT_FIXTURE)
    parser.add_argument("--write-fixture", action="store_true", help="Update the deterministic validator fixture.")
    parser.add_argument("--self-test", action="store_true", help="Run built-in valid/invalid record checks.")
    parser.add_argument("--record", type=pathlib.Path, default=None, help="Filled panel evidence record JSON to validate.")
    return parser.parse_args(argv)


def main(argv: list[str]) -> int:
    args = parse_args(argv)
    fixture_path = REPO_ROOT / args.fixture
    fixture_rel = rel(fixture_path)
    errors: list[str] = []
    for path in [TEMPLATE, EXPRESSION_FIXTURES]:
        require(path.exists(), f"missing required path {rel(path)}", errors)
    expected = build_fixture() if not errors else {}
    if expected:
        check_fixture_data(expected, errors)

    if args.self_test:
        errors.extend(run_self_test())
    if args.record is not None:
        record_path = args.record if args.record.is_absolute() else REPO_ROOT / args.record
        require(record_path.exists(), f"missing panel evidence record: {rel(record_path)}", errors)
        if record_path.exists():
            errors.extend(validate_record(load_json(record_path), record_path))

    if not args.write_fixture:
        check_project_links(fixture_rel, errors)
        check_fixture_file(fixture_path, expected, errors)
    if args.write_fixture and not errors:
        fixture_path.parent.mkdir(parents=True, exist_ok=True)
        fixture_path.write_text(json.dumps(expected, indent=2, sort_keys=True) + "\n", encoding="utf-8")

    if errors:
        print("FAIL: Companion panel evidence record checks failed:", file=sys.stderr)
        for error in errors:
            print(f" - {error}", file=sys.stderr)
        return 1
    if args.record is not None:
        print(f"PASS: Companion panel evidence record validated -> {rel(record_path)}")
    else:
        print(f"PASS: Companion panel evidence record validator verified -> {rel(fixture_path)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
