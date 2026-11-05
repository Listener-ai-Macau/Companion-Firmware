#!/usr/bin/env python3
"""Build the honest completion audit for COMP-REQ-775."""

from __future__ import annotations

import json
from pathlib import Path


REPO = Path(__file__).resolve().parents[2]
ROOT = REPO / ".cache/validation/comp-req-775-incremental-sync"
OUTPUT = ROOT / "COMPLETION_AUDIT.json"
RUNBOOK = ROOT / "HARDWARE_RUNBOOK.md"


def load(relative: str) -> dict:
    return json.loads((ROOT / relative).read_text(encoding="utf-8"))


def require(condition: bool, message: str) -> None:
    if not condition:
        raise AssertionError(message)


def main() -> None:
    offline = load("OFFLINE_READY.json")
    slow = load("SLOW_PATH_BASELINE.json")
    resource = load("RESOURCE_OTA_OFFLINE_READY.json")
    historical = load("hardware-run/HARDWARE_MACHINE_READY.json")
    transaction = load("STLINK_TRANSACTION_FAULT_INJECTION.json")
    boot_chain = load(
        "hardware-external-loader-acceptance/boot-chain-preflight.json"
    )
    probe = load(
        "hardware-external-loader-acceptance/02-one-frame-probe.json"
    )
    restore = load(
        "hardware-external-loader-acceptance/03-fixed-restore.json"
    )
    noop = load(
        "hardware-external-loader-acceptance/04-final-noop.json"
    )

    require(offline["status"] == "PASS_OFFLINE_HARDWARE_PENDING", "offline")
    require(slow["status"] == "PASS_SLOW_PATH_BASELINE", "slow path")
    require(resource["status"] == "MACHINE_READY_OFFLINE", "resource OTA")
    require(transaction["status"] == "MACHINE_READY", "transaction")
    require(historical["status"] == "FAILED", "historical run disposition")
    require(boot_chain["status"] == "MACHINE_READY", "boot-chain disposition")
    require(
        probe["status"] == "MACHINE_READY_RESTORE_REQUIRED"
        and probe["performance_contract"]["changed_resource_under_30s"],
        "one-frame hardware probe",
    )
    require(
        restore["status"] == "MACHINE_READY_MENU_PENDING"
        and restore["target_root"]["resource_id"] == offline["resource_id"],
        "fixed-page hardware restore",
    )
    require(
        noop["status"] == "MACHINE_READY_MENU_PENDING"
        and noop["noop"]
        and noop["performance_contract"]["same_resource_under_10s"]
        and noop["external_flash_write_bytes"] == 0
        and noop["internal_flash_write_bytes"] == 0
        and noop["recording_partition_write_bytes"] == 0
        and noop["recording_resource_pack"]["current_match"]
        and noop["recording_resource_pack"]["readback_verified"],
        "final hardware no-op",
    )

    proven = [
        "slow_path_timing_and_redundant_full_app_relinks_measured",
        "fixed_browser_and_generated_200x200_1bpp_frames_byte_equivalent",
        "same_resource_plan_writes_zero_external_and_internal_bytes",
        "single_frame_plan_is_ten_data_sectors_plus_inactive_root_last",
        "partial_write_corrupt_root_and_corrupt_blob_preserve_generation_1",
        "valid_root_last_commit_activates_generation_2",
        "external_loader_exposes_exactly_2mib_and_not_recording_partition",
        "normal_app_vector_and_end_remain_in_ota_application_range",
        "existing_ble_app_ota_loader_is_unchanged",
        "resource_ota_target_validates_crc_base_offset_and_abort",
        "product_resource_ota_is_reserved_as_a_separate_normal_app_target",
        "fixed_browser_url_returns_http_200",
        "single_command_hardware_acceptance_controller_passes_check_only",
        "one_frame_probe_has_exact_generation_5_fixed_page_restore",
        "boot_and_menu_log_verifiers_reject_wrong_order_clip_and_faults",
        "hardware_summary_rejects_slow_probe_wrong_restore_and_protected_write",
        "crrp_exact_pack_is_part_of_the_2mib_sector_plan",
        "missing_crrp_plans_33_sectors_without_ui_root_commit",
        "partial_crrp_write_preserves_active_ui_generation",
        "final_boot_gate_requires_crrp_mount_ok",
    ]
    proven_hardware = [
        {
            "item": "one_frame_probe_root_last_and_readback",
            "result": probe["status"],
            "write_bytes": probe["external_flash_write_bytes"],
            "timing_ms": probe["timing_ms"]["total"],
            "performance_pass": True,
        },
        {
            "item": "fixed_page_restore",
            "result": restore["status"],
            "write_bytes": restore["external_flash_write_bytes"],
            "timing_ms": restore["timing_ms"]["total"],
            "readback_verified": restore["partition_readback_verified"],
        },
        {
            "item": "final_fixed_page_noop",
            "result": noop["status"],
            "write_bytes": noop["external_flash_write_bytes"],
            "timing_ms": noop["timing_ms"]["total"],
            "crrp_included": True,
            "crrp_sha256": noop["recording_resource_pack"]["pack_sha256"],
            "recording_partition_write_bytes": 0,
        },
    ]
    pending_hardware = [
        "capture_real_menu_enter_and_exit_fast_full_refresh_boundaries",
        "compare_fixed_browser_first_frame_and_physical_screen",
    ]
    receipt = {
        "schema": "companion.comp_req_775.completion_audit.v1",
        "status": "HARDWARE_READY_MENU_PENDING",
        "owner_steering": {
            "development": "ST-LINK External Loader fast resource iteration",
            "product": "separate normal-App resource OTA target reserved",
            "existing_app_ota": "unchanged; do not rebuild or repurpose",
        },
        "proven_offline": proven,
        "proven_hardware": proven_hardware,
        "pending_current_hardware": pending_hardware,
        "pending_human": [
            "canonical Chinese fixed-browser versus physical-screen review"
        ],
        "product_resource_gatt": {
            "binding_enabled": False,
            "disposition": (
                "reserved target and manifest are implemented; asynchronous "
                "BLE scheduling/binding remains intentionally outside this "
                "development fast-path change"
            ),
        },
        "current_hardware_boundary": {
            "boot_chain_matches_registered_loader_and_app": True,
            "latest_preflight_read_only": True,
            "latest_external_flash_contact": 1,
            "hardware_contact": 1,
            "execute_now": True,
        },
        "next_command_for_real_menu_boundary": (
            "pwsh -NoProfile -File "
            ".\\tools\\run_comp_req_775_external_loader_acceptance.ps1 "
            "-Execute -ResumePhase menu"
        ),
        "bootstrap_if_live_base_identity_rejects_generation_1": (
            "pwsh -NoProfile -File "
            ".\\tools\\run_comp_req_775_external_loader_sync.ps1 -Execute "
            "-BootstrapImage "
            ".cache\\validation\\comp-req-775-incremental-sync\\"
            "stlink-sync\\synthetic-generation-1.bin"
        ),
        "evidence": {
            "offline": "OFFLINE_READY.json",
            "slow_path": "SLOW_PATH_BASELINE.json",
            "resource_ota": "RESOURCE_OTA_OFFLINE_READY.json",
            "transaction": "STLINK_TRANSACTION_FAULT_INJECTION.json",
            "historical_failed_run": (
                "hardware-run/HARDWARE_MACHINE_READY.json"
            ),
            "latest_boot_chain_preflight": (
                "hardware-external-loader-acceptance/"
                "boot-chain-preflight.json"
            ),
        },
        "hardware_contact": 1,
    }
    OUTPUT.write_text(
        json.dumps(receipt, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    RUNBOOK.write_text(
        "\n".join(
            [
                "# COMP-REQ-775 current hardware run",
                "",
                "Do not run while another owner or Agent uses Companion.",
                "",
                "With the registered Loader/App boot chain active, capture "
                "the remaining real menu boundary:",
                "",
                "```powershell",
                "pwsh -NoProfile -File "
                ".\\tools\\run_comp_req_775_external_loader_acceptance.ps1 "
                "-Execute -ResumePhase menu",
                "```",
                "",
                "The runner performs a generation-5 zero-write sync, then "
                "captures a physical long-press menu entry and right-swipe "
                "exit. It must observe both fast full-refresh boundaries.",
                "",
                "If the live base CEMP identity differs, the controller may "
                "fall back to the explicit initial partition bootstrap only "
                "while no active generation exists. The equivalent manual "
                "recovery command is:",
                "",
                "```powershell",
                "pwsh -NoProfile -File "
                ".\\tools\\run_comp_req_775_external_loader_sync.ps1 "
                "-Execute -BootstrapImage "
                ".cache\\validation\\comp-req-775-incremental-sync\\"
                "stlink-sync\\synthetic-generation-1.bin",
                "```",
                "",
                "Bootstrap is fail-closed when any valid active generation "
                "exists. It writes the base and generation data first and the "
                "sole generation-1 root last.",
                "",
            ]
        ),
        encoding="utf-8",
    )
    print(json.dumps(receipt, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
