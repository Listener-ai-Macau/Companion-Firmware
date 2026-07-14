#!/usr/bin/env python3
"""Verify WB55 screen machine state before human touch/visual acceptance."""

from __future__ import annotations

import argparse
import json
import pathlib
import sys
from typing import Any

from screen_runtime_candidate import current_candidate


ROOT = pathlib.Path(__file__).resolve().parents[1]
DEFAULT_FIXTURE = ROOT / "docs/validation/companion-screen-pre-acceptance-health.json"
BILINGUAL_MENU = ROOT / "docs/validation/companion-screen-bilingual-menu-wb55.json"
TOUCH_PACKET = ROOT / "docs/validation/companion-screen-wb55-touch-visual-acceptance-packet.json"
TOUCH_REVIEW_TEMPLATE = ROOT / "docs/validation/companion-screen-wb55-touch-visual-review-template.json"
TOUCH_REVIEW_RECORD = ROOT / "docs/validation/companion-screen-wb55-touch-visual-review-record.json"
RUNTIME_ACTION_CARD = ROOT / "docs/validation/companion-screen-wb55-runtime-hardware-action-card.json"
RUNTIME_FLASH_PREFLIGHT = ROOT / "docs/validation/companion-screen-wb55-runtime-flash-preflight.json"
RUNTIME_SERIAL_CAPTURE_PREFLIGHT = ROOT / "docs/validation/companion-screen-wb55-runtime-serial-capture-preflight.json"
RUNTIME_RECHECK_LOGS = ROOT / "docs/validation/companion-screen-wb55-runtime-recheck-logs.json"
GOAL_AUDIT = ROOT / "docs/validation/companion-screen-goal-audit.json"
REFRESH_FEEL = ROOT / "docs/validation/companion-screen-refresh-feel-contract.json"
RUNTIME_PROMOTION = ROOT / "docs/validation/companion-screen-wb55-runtime-promotion.json"
BUILD_MATRIX = ROOT / "docs/validation/companion-screen-wb55-build-matrix.json"
ACCEPTANCE_INDEX = ROOT / "docs/validation/companion-screen-acceptance-index.json"
VISUAL_REFERENCE_EVIDENCE = ROOT / "docs/validation/companion-visual-reference-evidence.json"
FLASH_SCRIPT = ROOT / "tools/flash_nucleo_bringup.ps1"
SCHEMA_ID = "companion.pendant.screen_pre_acceptance_health.v1"
CANDIDATE = current_candidate()
PENDING_STATUS = CANDIDATE.pending_status
PASS_STATUS = CANDIDATE.pass_status
RUNTIME_GATE_ID = f"wb55_rev{CANDIDATE.revision}_runtime_recheck"


def rel(path: pathlib.Path) -> str:
    return path.resolve().relative_to(ROOT).as_posix()


def load_json(path: pathlib.Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def log_has(path_text: str, markers: list[str]) -> dict[str, Any]:
    if not path_text:
        return {
            "path": path_text,
            "exists": False,
            "markers": {marker: False for marker in markers},
        }
    path = ROOT / path_text
    text = path.read_text(encoding="utf-8", errors="replace") if path.is_file() else ""
    return {
        "path": path_text,
        "exists": path.is_file(),
        "markers": {marker: marker in text for marker in markers},
    }


def build_health() -> dict[str, Any]:
    menu = load_json(BILINGUAL_MENU)
    packet = load_json(TOUCH_PACKET)
    review_template = load_json(TOUCH_REVIEW_TEMPLATE)
    review_record = load_json(TOUCH_REVIEW_RECORD)
    action_card = load_json(RUNTIME_ACTION_CARD)
    flash_preflight = load_json(RUNTIME_FLASH_PREFLIGHT)
    serial_capture_preflight = load_json(RUNTIME_SERIAL_CAPTURE_PREFLIGHT)
    audit = load_json(GOAL_AUDIT)
    refresh_feel = load_json(REFRESH_FEEL)
    promotion = load_json(RUNTIME_PROMOTION)
    runtime_recheck_logs = load_json(RUNTIME_RECHECK_LOGS)
    build_matrix = load_json(BUILD_MATRIX)
    acceptance_index = load_json(ACCEPTANCE_INDEX)
    visual_reference_evidence = load_json(VISUAL_REFERENCE_EVIDENCE)
    resource = menu.get("resource_pack", {})
    runtime = menu.get("runtime_evidence", {})
    machine_state = packet.get("machine_state", {})
    runtime_status = str(runtime.get("status", ""))
    runtime_pending = runtime_status == PENDING_STATUS
    proven = runtime.get("previous_runtime_proven_revision", {}) if runtime_pending else resource
    proven_revision = proven.get("revision", resource.get("revision"))
    proven_crc32 = proven.get("pack_crc32", resource.get("pack_crc32"))
    proven_provision_log = proven.get("provision_raw_log", runtime.get("provision_raw_log", ""))
    proven_normal_log = proven.get("normal_raw_log", runtime.get("normal_raw_log", ""))

    provision_markers = [
        "mount=ok",
        f"revision={proven_revision}",
        f"clips={proven.get('clips', resource.get('clips'))} "
        f"frames={proven.get('frames', resource.get('frames'))}",
        "expression_renderer=external_pack",
        "source=external_flash",
        "pet_behavior_selftest=pass failure_code=0",
        "touch-health] detected=1 identity=1 addr=0x38",
        "refresh mode=full",
        "complete=1",
    ]
    normal_markers = [
        "mount=ok",
        f"revision={proven_revision}",
        f"clips={proven.get('clips', resource.get('clips'))} "
        f"frames={proven.get('frames', resource.get('frames'))}",
        "expression_renderer=external_pack",
        "pet_behavior_selftest=pass failure_code=0",
        "touch-health] detected=1 identity=1 addr=0x38",
        f"queue_generation revision={proven_revision}",
        "coherent_generation=1",
        "last_stale_discarded=",
        "[build] interaction_profile=quiet epaper_trace=0 touch_trace=0 ",
        "preview_started name=idle",
        "low_power_face completed=1 stop=allowed",
    ]
    provision_log = log_has(str(proven_provision_log), provision_markers)
    normal_log = log_has(str(proven_normal_log), normal_markers)
    runtime_logs_pass = runtime_recheck_logs.get("status") == "PASS"
    review_status = str(review_record.get("status", ""))
    blocking_reasons: list[str] = []
    if not runtime_logs_pass:
        blocking_reasons.append("quiet_interaction_profile_runtime_recheck")
    if review_status == "NO_GO_OPEN_REVIEW_ITEMS":
        blocking_reasons.append("open_operator_review_items")
    status = (
        "NO_GO_INTERACTION_PROFILE_RUNTIME_RECHECK_PENDING"
        if not runtime_logs_pass
        else "NO_GO_OPEN_OPERATOR_REVIEW_ITEMS"
        if review_status == "NO_GO_OPEN_REVIEW_ITEMS"
        else "PASS"
    )

    return {
        "schema_id": SCHEMA_ID,
        "status": status,
        "blocking_reasons": blocking_reasons,
        "target": "NUCLEO-WB55RG + GDEY0154D67-T03 + FT6336U",
        "purpose": (
            "Machine-only pre-acceptance health gate for the WB55 touch/visual "
            "operator packet. It does not claim human feel acceptance."
        ),
        "resource": {
            "revision": resource.get("revision"),
            "clips": resource.get("clips"),
            "frames": resource.get("frames"),
            "total_bytes": resource.get("total_bytes"),
            "pack_crc32": resource.get("pack_crc32"),
            "runtime_status": runtime.get("status"),
        },
        "last_runtime_proven_resource": {
            "revision": proven_revision,
            "pack_crc32": proven_crc32,
            "provision_log": proven_provision_log,
            "normal_log": proven_normal_log,
        },
        "flash_paths": {
            "script": rel(FLASH_SCRIPT),
            "normal_preflight": "pwsh -NoProfile -File .\\tools\\flash_nucleo_bringup.ps1 -CheckOnly",
            "provision_preflight": "pwsh -NoProfile -File .\\tools\\flash_nucleo_bringup.ps1 -ScreenAssetProvision -CheckOnly",
            "normal_hex": "Companion_Nucleo_WB55RG_Bringup.hex",
            "provision_hex": "Companion_Nucleo_WB55RG_ScreenAssetProvision.hex",
            "conflict_guard": "Use either -ScreenAssetProvision or -ImagePath, not both.",
        },
        "runtime_logs": {
            "provision": provision_log,
            "normal": normal_log,
        },
        "runtime_recheck_log_gate": {
            "path": rel(RUNTIME_RECHECK_LOGS),
            "status": runtime_recheck_logs.get("status"),
            "quiet_interaction_profile_passed": runtime_logs_pass,
        },
        "operator_packet": {
            "path": rel(TOUCH_PACKET),
            "status": packet.get("status"),
            "start_rule": packet.get("start_rule"),
            "step_count": len(packet.get("operator_steps", [])),
            "step_ids": [
                step.get("id") for step in packet.get("operator_steps", [])
                if isinstance(step, dict)
            ],
            "machine_state_matches_resource": {
                "revision": machine_state.get("resource_revision") == resource.get("revision"),
                "crc32": machine_state.get("resource_crc32") == resource.get("pack_crc32"),
                "total_bytes": machine_state.get("resource_total_bytes") == resource.get("total_bytes"),
                "normal_firmware_restored": machine_state.get("normal_firmware_restored") is True,
            },
        },
        "operator_review_template": {
            "path": rel(TOUCH_REVIEW_TEMPLATE),
            "status": review_template.get("status"),
            "claim_scope": review_template.get("claim_scope"),
            "source_packet": review_template.get("source_packet"),
            "record_count": len(review_template.get("review_records", [])),
            "records_default_non_publishable": all(
                record.get("publishable_pass_allowed") is False
                and record.get("resolution_state") == "open_requires_fix"
                and record.get("evidence_path") == ""
                for record in review_template.get("review_records", [])
            ),
        },
        "operator_review_record": {
            "path": rel(TOUCH_REVIEW_RECORD),
            "status": review_record.get("status"),
            "claim_scope": review_record.get("claim_scope"),
            "source_template": review_record.get("source_template"),
            "filled_input_path": review_record.get("filled_input_path"),
            "publishable_pass_allowed": review_record.get("publishable_pass_allowed"),
            "record_count": len(review_record.get("review_records", [])),
            "open_item_count": len(review_record.get("open_items", [])),
        },
        "goal_state": {
            "path": rel(GOAL_AUDIT),
            "status": audit.get("status"),
            "open_requirements": audit.get("open_requirements", []),
            "proved_requirements": [
                item.get("id")
                for item in audit.get("requirements", [])
                if item.get("status") == "proved"
            ],
        },
        "acceptance_index": {
            "path": rel(ACCEPTANCE_INDEX),
            "schema_id": acceptance_index.get("schema_id"),
            "summary": acceptance_index.get("summary", {}),
            "next_hardware_gate": acceptance_index.get("summary", {}).get("next_hardware_gate"),
            "next_human_gate": acceptance_index.get("summary", {}).get("next_human_gate"),
        },
        "visual_reference_evidence": {
            "path": rel(VISUAL_REFERENCE_EVIDENCE),
            "status": visual_reference_evidence.get("status"),
            "pending_owner_visual_review": visual_reference_evidence.get("pending_owner_visual_review", []),
            "rejected_history_preserved": visual_reference_evidence.get("rejected_history_preserved", []),
        },
        "refresh_feel_contract": {
            "path": rel(REFRESH_FEEL),
            "status": refresh_feel.get("status"),
            "candidate": refresh_feel.get("candidate", {}),
            "product_rules": refresh_feel.get("product_rules", {}),
            "checks": {
                key: refresh_feel.get("checks", {}).get(key)
                for key in (
                    "vendor_ghosting_research_recorded",
                    "interactive_uses_differential_waveform",
                    "maintenance_uses_single_low_flicker_waveform",
                    "full_refresh_reserved_for_baseline_or_fault",
                    "ordinary_touch_has_no_delayed_maintenance",
                    "interactive_cleanup_is_coalesced_at_five_partials",
                    "menu_drag_coalesces_to_latest_frame",
                    "art_and_refresh_axes_separate",
                )
            },
        },
        "build_matrix": {
            "path": rel(BUILD_MATRIX),
            "status": build_matrix.get("status"),
            "build_variants": build_matrix.get("build_variants", {}),
            "build_log_evidence": build_matrix.get("build_log_evidence", {}),
            "contracts": build_matrix.get("contracts", {}),
        },
        "runtime_promotion_gate": {
            "path": rel(RUNTIME_PROMOTION),
            "status": promotion.get("status"),
            "target_status": promotion.get("target_state", {}).get("status"),
            "blockers": promotion.get("blockers", []),
        },
        "runtime_hardware_action_card": {
            "path": rel(RUNTIME_ACTION_CARD),
            "status": action_card.get("status"),
            "claim_scope": action_card.get("claim_scope"),
            "workflow_lock_command": action_card.get("workflow_lock_command"),
            "step_count": len(action_card.get("hardware_steps", [])),
            "post_run_commands": action_card.get("post_run_commands", []),
            "human_acceptance_start_rule": action_card.get("human_acceptance_start_rule"),
            "quiet_interaction_profile_recheck_required": action_card.get("resource", {}).get("quiet_interaction_profile_recheck_required"),
        },
        "runtime_flash_preflight": {
            "path": rel(RUNTIME_FLASH_PREFLIGHT),
            "status": flash_preflight.get("status"),
            "normal_image_exists": flash_preflight.get("normal", {}).get("image_exists"),
            "provision_image_exists": flash_preflight.get("screen_asset_provision", {}).get("image_exists"),
            "programmer_exists": (
                flash_preflight.get("normal", {}).get("programmer_exists") is True
                and flash_preflight.get("screen_asset_provision", {}).get("programmer_exists") is True
            ),
        },
        "runtime_serial_capture_preflight": {
            "path": rel(RUNTIME_SERIAL_CAPTURE_PREFLIGHT),
            "status": serial_capture_preflight.get("status"),
            "claim_scope": serial_capture_preflight.get("claim_scope"),
            "capture_script": serial_capture_preflight.get("source_files", {}).get("capture_script"),
            "runtime_runner": serial_capture_preflight.get("source_files", {}).get("runtime_runner"),
            "runtime_run_report": serial_capture_preflight.get("source_files", {}).get("runtime_run_report"),
            "raw_log_filename": serial_capture_preflight.get("capture_script_contract", {}).get("outputs", {}).get("raw_log_filename"),
            "summary_json_filename": serial_capture_preflight.get("capture_script_contract", {}).get("outputs", {}).get("summary_json_filename"),
            "operator_rule": serial_capture_preflight.get("operator_rule"),
        },
        "validation_commands": [
            "python .\\tools\\verify_companion_screen_pre_acceptance_health.py",
            "python .\\tools\\verify_wb55_screen_runtime_recheck_runner.py",
            "python .\\tools\\verify_wb55_runtime_flash_preflight.py",
            "python .\\tools\\verify_wb55_runtime_serial_capture_preflight.py",
            "python .\\tools\\render_wb55_runtime_hardware_action_card.py",
            "python .\\tools\\render_wb55_touch_visual_acceptance_packet.py",
            "python .\\tools\\render_wb55_touch_visual_review_template.py",
            "python .\\tools\\verify_wb55_touch_visual_review_record.py",
            "python .\\tools\\verify_companion_screen_goal_audit.py",
            "python .\\tools\\verify_screen_menu_assets.py",
            "python .\\tools\\verify_visual_reference_evidence.py",
            "python .\\tools\\verify_screen_presentation.py",
            "python .\\tools\\verify_touch_ft6336.py",
            "python .\\tools\\verify_screen_refresh_feel_contract.py",
            "python .\\tools\\verify_wb55_screen_build_matrix.py",
            "python .\\tools\\promote_wb55_screen_runtime_recheck.py",
            "python .\\tools\\verify_expression_acceptance_index.py",
        ],
    }


def check_health(health: dict[str, Any], errors: list[str]) -> None:
    if health.get("schema_id") != SCHEMA_ID:
        errors.append("unexpected schema_id")
    resource = health.get("resource", {})
    runtime_status = str(resource.get("runtime_status", ""))
    runtime_pending = runtime_status == PENDING_STATUS
    runtime_log_gate = health.get("runtime_recheck_log_gate", {})
    runtime_logs_pass = runtime_log_gate.get("status") == "PASS"
    review_status = str(health.get("operator_review_record", {}).get("status", ""))
    expected_status = (
        "NO_GO_INTERACTION_PROFILE_RUNTIME_RECHECK_PENDING"
        if not runtime_logs_pass
        else "NO_GO_OPEN_OPERATOR_REVIEW_ITEMS"
        if review_status == "NO_GO_OPEN_REVIEW_ITEMS"
        else "PASS"
    )
    if health.get("status") != expected_status:
        errors.append(f"pre-acceptance status must be {expected_status}")
    if runtime_log_gate.get("path") != rel(RUNTIME_RECHECK_LOGS):
        errors.append("pre-acceptance runtime recheck log gate path drifted")
    if runtime_log_gate.get("quiet_interaction_profile_passed") is not runtime_logs_pass:
        errors.append("pre-acceptance runtime recheck quiet-profile result drifted")
    if not runtime_logs_pass and "quiet_interaction_profile_runtime_recheck" not in health.get("blocking_reasons", []):
        errors.append("pre-acceptance health must retain the quiet interaction-profile blocker")
    if review_status == "NO_GO_OPEN_REVIEW_ITEMS" and "open_operator_review_items" not in health.get("blocking_reasons", []):
        errors.append("pre-acceptance health must retain open operator-review feedback")
    if resource.get("revision") != CANDIDATE.revision:
        errors.append(f"candidate resource revision must be {CANDIDATE.revision}, got {resource.get('revision')!r}")
    if resource.get("clips") != CANDIDATE.clips or resource.get("frames") != CANDIDATE.frames:
        errors.append("resource clip/frame count drifted from candidate pack")
    if resource.get("total_bytes") != CANDIDATE.total_bytes:
        errors.append("resource byte count drifted from active candidate pack")
    if resource.get("pack_crc32") != CANDIDATE.pack_crc32:
        errors.append("resource CRC drifted from active candidate pack")
    if runtime_status not in {PENDING_STATUS, PASS_STATUS}:
        errors.append("runtime status must be active candidate pending or promoted human-visual-pending")
    proven = health.get("last_runtime_proven_resource", {})
    if runtime_pending:
        if not isinstance(proven.get("revision"), int) or proven.get("revision") >= CANDIDATE.revision:
            errors.append("last runtime-proven resource must be an earlier revision until the active candidate is flashed")
        if not str(proven.get("pack_crc32", "")).startswith("0x"):
            errors.append("last runtime-proven resource must retain its CRC while the active candidate is pending")
    else:
        if proven.get("revision") != CANDIDATE.revision or proven.get("pack_crc32") != CANDIDATE.pack_crc32:
            errors.append("promoted runtime-proven resource must match the active candidate")

    refresh_feel = health.get("refresh_feel_contract", {})
    if refresh_feel.get("status") != "PASS":
        errors.append("refresh feel contract must be PASS before human touch/visual acceptance")
    refresh_candidate = refresh_feel.get("candidate", {})
    if refresh_candidate.get("revision") != resource.get("revision"):
        errors.append("refresh feel candidate revision must match resource revision")
    if refresh_candidate.get("crc32") != resource.get("pack_crc32"):
        errors.append("refresh feel candidate CRC must match resource CRC")
    if refresh_candidate.get("runtime_status") != resource.get("runtime_status"):
        errors.append("refresh feel runtime status must match resource runtime status")
    for key, value in refresh_feel.get("checks", {}).items():
        if value is not True:
            errors.append(f"refresh feel check {key} must be true")
    visual_reference_evidence = health.get("visual_reference_evidence", {})
    if visual_reference_evidence.get("status") != "PASS_LEDGER_INTEGRITY":
        errors.append("visual reference evidence must retain a passing ledger audit")
    if not visual_reference_evidence.get("pending_owner_visual_review"):
        errors.append("visual reference evidence must expose pending owner visual gates")
    if not visual_reference_evidence.get("rejected_history_preserved"):
        errors.append("visual reference evidence must preserve rejected art history")
    promotion = health.get("runtime_promotion_gate", {})
    if promotion.get("target_status") != PASS_STATUS:
        errors.append("runtime promotion gate target status drifted")
    if runtime_pending:
        if runtime_logs_pass:
            if promotion.get("status") != "READY_TO_APPLY":
                errors.append("runtime promotion must be READY_TO_APPLY after active runtime logs pass")
            if promotion.get("blockers"):
                errors.append("READY_TO_APPLY runtime promotion must not keep blockers")
        else:
            if promotion.get("status") != "NO_GO_LOGS_NOT_PASS":
                errors.append("runtime promotion must stay NO_GO while active runtime logs are pending")
            if not promotion.get("blockers"):
                errors.append("runtime promotion gate must list blockers while active runtime logs are pending")
    else:
        if promotion.get("status") != "APPLIED":
            errors.append("runtime promotion gate must be APPLIED after active runtime logs are promoted")
    action_card = health.get("runtime_hardware_action_card", {})
    expected_action_card_status = (
        "PASS_MACHINE_RUNTIME_RECHECK_COMPLETE"
        if runtime_logs_pass else "NO_GO_WAITING_FOR_REAL_HARDWARE_RUN"
    )
    if action_card.get("status") != expected_action_card_status:
        errors.append(f"runtime hardware action card must be {expected_action_card_status}")
    if action_card.get("claim_scope") != "operator_action_card_no_hardware_claim":
        errors.append("runtime hardware action card must not claim hardware completion")
    if "Companion-WB55" not in str(action_card.get("workflow_lock_command", "")):
        errors.append("runtime hardware action card must include the Companion-WB55 lock command")
    if action_card.get("step_count") != 4:
        errors.append("runtime hardware action card must keep four machine steps")
    required_post_run_commands = (
        "python .\\tools\\verify_screen_generation_release_ledger.py",
        "python .\\tools\\verify_wb55_screen_runtime_recheck_logs.py --write",
        "python .\\tools\\verify_companion_screen_pre_acceptance_health.py",
        "python .\\tools\\verify_companion_screen_goal_audit.py",
    )
    for command in required_post_run_commands:
        if command not in action_card.get("post_run_commands", []):
            errors.append(f"runtime hardware action card missing post-run command {command}")
    quiet_profile_only_recheck = action_card.get("quiet_interaction_profile_recheck_required") is True
    promotion_command = "python .\\tools\\promote_wb55_screen_runtime_recheck.py --apply"
    if quiet_profile_only_recheck:
        if promotion_command in action_card.get("post_run_commands", []):
            errors.append("quiet-profile-only recheck must not request a duplicate resource promotion")
    elif promotion_command not in action_card.get("post_run_commands", []):
        errors.append(f"runtime hardware action card missing post-run command {promotion_command}")
    if "开始验收" not in str(action_card.get("human_acceptance_start_rule", "")):
        errors.append("runtime hardware action card must keep the explicit human start rule")
    flash_preflight = health.get("runtime_flash_preflight", {})
    if flash_preflight.get("status") != "PASS":
        errors.append("runtime flash preflight must be PASS")
    if flash_preflight.get("normal_image_exists") is not True:
        errors.append("runtime flash preflight normal image must exist")
    if flash_preflight.get("provision_image_exists") is not True:
        errors.append("runtime flash preflight provision image must exist")
    if flash_preflight.get("programmer_exists") is not True:
        errors.append("runtime flash preflight programmer must exist")
    serial_capture = health.get("runtime_serial_capture_preflight", {})
    if serial_capture.get("status") != "PASS_STATIC_SERIAL_CAPTURE_PREFLIGHT":
        errors.append("runtime serial capture preflight must be PASS_STATIC_SERIAL_CAPTURE_PREFLIGHT")
    if serial_capture.get("claim_scope") != "static_serial_capture_contract_no_hardware_claim":
        errors.append("runtime serial capture preflight must not claim hardware completion")
    if serial_capture.get("capture_script") != "tools/capture_nucleo_serial.ps1":
        errors.append("runtime serial capture preflight must point at capture_nucleo_serial.ps1")
    if serial_capture.get("runtime_runner") != "tools/run_wb55_screen_runtime_recheck.ps1":
        errors.append("runtime serial capture preflight must point at the runtime recheck runner")
    if serial_capture.get("raw_log_filename") != "nucleo-serial-raw.log":
        errors.append("runtime serial capture raw log filename drifted")
    if serial_capture.get("summary_json_filename") != "nucleo-serial-summary.json":
        errors.append("runtime serial capture summary filename drifted")
    if "does not open serial ports" not in str(serial_capture.get("operator_rule", "")):
        errors.append("runtime serial capture preflight must state it does not open serial ports")

    build_matrix = health.get("build_matrix", {})
    if build_matrix.get("status") != "PASS":
        errors.append("WB55 screen build matrix must be PASS before human touch/visual acceptance")
    variants = build_matrix.get("build_variants", {})
    for key in ("dry_run_default", "ssd1681_real_panel"):
        if key not in variants:
            errors.append(f"WB55 screen build matrix missing variant {key}")
    for key, value in build_matrix.get("contracts", {}).items():
        if value is not True:
            errors.append(f"WB55 screen build matrix contract {key} must be true")
    for key in ("dry_run_default", "ssd1681_real_panel"):
        item = build_matrix.get("build_log_evidence", {}).get(key, {})
        if item.get("exists") is not True:
            errors.append(f"WB55 screen build matrix log evidence missing {key}")
        if item.get("size") != item.get("expected_size"):
            errors.append(f"WB55 screen build matrix size evidence mismatch for {key}")
        for marker, present in item.get("required_markers", {}).items():
            if present is not True:
                errors.append(f"WB55 screen build matrix log evidence missing {key} marker {marker}")
        for marker, absent in item.get("forbidden_markers_absent", {}).items():
            if absent is not True:
                errors.append(f"WB55 screen build matrix log evidence contains forbidden {key} marker {marker}")

    flash_text = FLASH_SCRIPT.read_text(encoding="utf-8")
    required_tokens = [
        "[switch]$ScreenAssetProvision",
        "[switch]$CheckOnly",
        "Companion_Nucleo_WB55RG_Bringup.hex",
        "Companion_Nucleo_WB55RG_ScreenAssetProvision.hex",
        "Use either -ScreenAssetProvision or -ImagePath, not both.",
    ]
    for token in required_tokens:
        if token not in flash_text:
            errors.append(f"flash script missing {token}")

    for label, log in health.get("runtime_logs", {}).items():
        if not log.get("exists"):
            errors.append(f"{label} runtime log missing")
            continue
        missing = [marker for marker, present in log.get("markers", {}).items() if not present]
        if missing:
            errors.append(f"{label} runtime log missing markers: {missing}")

    packet = health.get("operator_packet", {})
    if packet.get("status") != "PENDING_HUMAN":
        errors.append("operator packet must stay PENDING_HUMAN")
    if "开始验收" not in str(packet.get("start_rule", "")):
        errors.append("operator packet must keep explicit 开始验收 start rule")
    required_operator_steps = {
        "daily_tap_social_response",
        "daily_swipe_pet_response",
        "anywhere_hold_menu_entry",
        "menu_boundary_single_clean_refresh",
        "menu_home_static_vertical_stroke",
        "row_press_and_back",
        "phone_reconnect_advertising",
        "language_switch_single_language",
        "maintenance_single_quiet_flash",
        "premium_pet_feel",
    }
    if set(packet.get("step_ids", [])) != required_operator_steps:
        errors.append("operator packet must retain the complete focused interaction coverage")
    if packet.get("step_count") != len(required_operator_steps):
        errors.append("operator packet focused step count does not match coverage")
    for key, matched in packet.get("machine_state_matches_resource", {}).items():
        if matched is not True:
            errors.append(f"operator packet machine_state mismatch: {key}")
    review_template = health.get("operator_review_template", {})
    if review_template.get("status") != "TEMPLATE_NOT_ACCEPTANCE_RESULT":
        errors.append("operator review template must not claim acceptance result")
    if review_template.get("claim_scope") != "blank_operator_review_template":
        errors.append("operator review template claim scope drifted")
    if review_template.get("source_packet") != packet.get("path"):
        errors.append("operator review template must point at the active operator packet")
    if review_template.get("record_count") != packet.get("step_count"):
        errors.append("operator review template record count must match operator packet step count")
    if review_template.get("records_default_non_publishable") is not True:
        errors.append("operator review template records must default non-publishable and open")
    review_record = health.get("operator_review_record", {})
    if review_record.get("status") not in {"NO_GO_NOT_STARTED", "NO_GO_OPEN_REVIEW_ITEMS"}:
        errors.append("operator review record must remain a non-publishable pre-acceptance state")
    if review_record.get("claim_scope") != "filled_operator_review_record_validator":
        errors.append("operator review record claim scope drifted")
    if review_record.get("source_template") != review_template.get("path"):
        errors.append("operator review record must point at the active review template")
    if review_record.get("record_count") != packet.get("step_count"):
        errors.append("operator review record count must match operator packet step count")
    if review_record.get("status") == "NO_GO_NOT_STARTED" and review_record.get("open_item_count") != packet.get("step_count"):
        errors.append("operator review record should list every step as open before review starts")
    if review_record.get("status") == "NO_GO_OPEN_REVIEW_ITEMS" and review_record.get("open_item_count", 0) < 1:
        errors.append("operator review record must retain the unresolved operator feedback")
    if review_record.get("publishable_pass_allowed") is not False:
        errors.append("operator review record must not allow publishable PASS before human review")

    goal = health.get("goal_state", {})
    if goal.get("status") != "GOAL_ACTIVE_NOT_COMPLETE":
        errors.append("goal audit must remain active until human/WBA gates close")
    for item in ("daily_pet_and_menu_human_feel", "wba55_wba65_portability_boundary"):
        if item not in goal.get("open_requirements", []):
            errors.append(f"goal open_requirements missing {item}")
    if "generated_art_handoff_and_refresh_feel_regression_guard" not in goal.get("proved_requirements", []):
        errors.append("pre-acceptance health must reference the art handoff/refresh feel goal guard")
    acceptance_index = health.get("acceptance_index", {})
    if acceptance_index.get("schema_id") != "companion.pendant.screen_acceptance_index.v1":
        errors.append("acceptance index schema drifted")
    expected_next_hardware_gate = "wba_real_panel_parity" if runtime_status == PASS_STATUS else RUNTIME_GATE_ID
    if acceptance_index.get("next_hardware_gate") != expected_next_hardware_gate:
        errors.append(f"pre-acceptance health must point next_hardware_gate at {expected_next_hardware_gate}")
    if acceptance_index.get("next_human_gate") != "wb55_touch_visual_acceptance":
        errors.append("pre-acceptance health must point next_human_gate at wb55_touch_visual_acceptance")
    summary = acceptance_index.get("summary", {})
    expected_deferred_count = 0 if runtime_status == PASS_STATUS else 1
    if summary.get("deferred_count") != expected_deferred_count:
        errors.append(f"acceptance index deferred_count must be {expected_deferred_count}")
    if summary.get("pending_human_count") != 2:
        errors.append("acceptance index pending human count drifted")
    serialized = json.dumps(health, ensure_ascii=False)
    required_tokens = [
        "operator_review_template",
        "operator_review_record",
        "runtime_hardware_action_card",
        "runtime_flash_preflight",
        "runtime_serial_capture_preflight",
        "TEMPLATE_NOT_ACCEPTANCE_RESULT",
        "NO_GO_OPEN_REVIEW_ITEMS",
        "blank_operator_review_template",
        "filled_operator_review_record_validator",
        "render_wb55_touch_visual_review_template.py",
        "verify_wb55_touch_visual_review_record.py",
        "render_wb55_runtime_hardware_action_card.py",
        "verify_wb55_runtime_flash_preflight.py",
        "verify_wb55_runtime_serial_capture_preflight.py",
        "companion-screen-acceptance-index.json",
        expected_next_hardware_gate,
        "wb55_touch_visual_acceptance",
        expected_action_card_status,
        "PASS_STATIC_SERIAL_CAPTURE_PREFLIGHT",
    ]
    for token in required_tokens:
        if token not in serialized:
            errors.append(f"pre-acceptance health missing token {token}")


def main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--write-fixture", action="store_true")
    parser.add_argument("--fixture", type=pathlib.Path, default=DEFAULT_FIXTURE)
    args = parser.parse_args(argv)

    fixture = args.fixture if args.fixture.is_absolute() else ROOT / args.fixture
    health = build_health()
    errors: list[str] = []
    check_health(health, errors)

    rendered = json.dumps(health, indent=2, ensure_ascii=False, sort_keys=True) + "\n"
    if args.write_fixture and not errors:
        fixture.parent.mkdir(parents=True, exist_ok=True)
        fixture.write_text(rendered, encoding="utf-8")
    elif not args.write_fixture:
        if not fixture.exists():
            errors.append(f"missing {rel(fixture)}")
        elif fixture.read_text(encoding="utf-8") != rendered:
            errors.append(f"stale {rel(fixture)}; rerun with --write-fixture")

    if errors:
        print("FAIL: Companion screen pre-acceptance health checks failed:", file=sys.stderr)
        for error in errors:
            print(f" - {error}", file=sys.stderr)
        return 1
    print(f"PASS: Companion screen pre-acceptance health verified -> {rel(fixture)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
