#!/usr/bin/env python3
"""Aggregate and verify the four COMP-REQ-775 hardware stages."""

from __future__ import annotations

import argparse
import json
from pathlib import Path


ROOTS = {"0x1FE000", "0x1FF000"}
STATIC_RESOURCE_BASE = 0x1DC000


def load(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8-sig"))


def require(condition: bool, message: str) -> None:
    if not condition:
        raise ValueError(message)


def all_true(mapping: dict) -> bool:
    return bool(mapping) and all(bool(value) for value in mapping.values())


def protected_zero(stage: dict) -> bool:
    protected = stage["protected_partitions"]
    return (
        stage["internal_flash_write_bytes"] == 0
        and stage["recording_partition_write_bytes"] == 0
        and protected["loader_internal_flash_write_bytes"] == 0
        and protected["ota_app_internal_flash_write_bytes"] == 0
        and protected["other_internal_flash_write_bytes"] == 0
        and protected["recording_partition_write_bytes"] == 0
        and protected["fus_write_bytes"] == 0
        and protected["otp_write_bytes"] == 0
        and protected["option_byte_write_bytes"] == 0
        and protected["mass_erase_calls"] == 0
    )


def ten_contiguous_data_sectors(stage: dict) -> bool:
    try:
        sectors = [
            int(value, 16) for value in stage["changed_data_sectors"]
        ]
    except (KeyError, TypeError, ValueError):
        return False
    return (
        len(sectors) == 10
        and sectors == list(range(sectors[0], sectors[0] + 0xA000, 0x1000))
        and sectors[0] % 0x1000 == 0
        and sectors[-1] + 0x1000 <= STATIC_RESOURCE_BASE
    )


def verify(
    initial: dict,
    probe: dict,
    restore: dict,
    noop: dict,
    offline: dict,
) -> dict:
    fixed_resource = offline["resource_id"]
    fixed_cemp = offline["base_cemp_sha256"]
    fixed_recording_pack = offline["firmware"][
        "recording_diagnostic_resources"
    ]["pack_sha256"]
    menu_boundary = restore.get("menu_boundary")
    if not menu_boundary or not menu_boundary.get("evidence"):
        menu_boundary = noop.get("menu_boundary")
    require(
        initial["active_generation_after"] == 1
        and initial["target_root"]["resource_id"] == fixed_resource
        and initial["cemp"]["target"]["sha256"] == fixed_cemp,
        "initial fixed-page generation is invalid",
    )
    require(
        probe["status"] == "MACHINE_READY_RESTORE_REQUIRED"
        and probe["active_generation_after"]
        == probe["active_generation_before"] + 1
        and ten_contiguous_data_sectors(probe)
        and probe["inactive_root_last"] in ROOTS
        and probe["external_flash_write_bytes"] == 45056
        and probe["external_flash_write_calls"] == 2
        and probe["partition_readback_verified"]
        and probe["ordinary_reset_performed"]
        and probe["performance_contract"]["changed_resource_under_30s"]
        and probe["timing_ms"]["total"] <= 30000,
        "registered one-frame probe failed its timing or write contract",
    )
    require(
        restore["status"]
        in {"MACHINE_READY_MENU_PENDING", "MACHINE_READY_OPERATOR_PENDING"}
        and restore["active_generation_before"]
        == probe["active_generation_after"]
        and restore["active_generation_after"]
        == restore["active_generation_before"] + 1
        and ten_contiguous_data_sectors(restore)
        and restore["inactive_root_last"] in ROOTS
        and restore["inactive_root_last"] != probe["inactive_root_last"]
        and restore["external_flash_write_bytes"] == 45056
        and restore["target_root"]["resource_id"] == fixed_resource
        and restore["cemp"]["target"]["sha256"] == fixed_cemp
        and restore["partition_readback_verified"]
        and restore["readback_partition_sha256"]
        == restore["desired_partition_sha256"]
        and all_true(restore["ordinary_reset"]["checks"]),
        "fixed-page restore evidence is invalid",
    )
    require(
        noop["active_generation_before"] == restore["active_generation_after"]
        and noop["active_generation_after"] == restore["active_generation_after"]
        and noop["noop"] is True
        and noop["changed_data_sectors"] == []
        and noop["inactive_root_last"] is None
        and noop["external_flash_write_bytes"] == 0
        and noop["external_flash_write_calls"] == 0
        and noop["internal_flash_write_bytes"] == 0
        and noop["partition_readback_verified"]
        and noop["ordinary_reset_performed"]
        and noop["performance_contract"]["same_resource_under_10s"]
        and noop["timing_ms"]["total"] <= 10000
        and noop["target_root"]["resource_id"] == fixed_resource
        and noop["cemp"]["target"]["sha256"] == fixed_cemp
        and noop["recording_resource_pack"]["current_match"]
        and noop["recording_resource_pack"]["changed_sector_count"] == 0
        and noop["recording_resource_pack"]["pack_sha256"]
        == fixed_recording_pack
        and noop["recording_resource_pack"]["readback_verified"],
        "final fixed-page no-op failed its timing or zero-write contract",
    )
    require(
        bool(menu_boundary)
        and all_true(menu_boundary["evidence"]["checks"]),
        "real menu enter/exit boundary evidence is invalid",
    )
    stages = {
        "initial": initial,
        "probe": probe,
        "restore": restore,
        "noop": noop,
    }
    require(
        all(stage["hardware_contact"] == 1 for stage in stages.values()),
        "hardware stage is missing real-contact evidence",
    )
    require(
        all(protected_zero(stage) for stage in stages.values()),
        "a protected partition reports a write",
    )
    require(
        all(
            stage["browser_contract"]["page_sha256"]
            == offline["page_sha256"]
            and stage["browser_contract"]["http_status"] == 200
            and stage["existing_app_ota"]["loader_worktree_unchanged"]
            and not stage["existing_app_ota"]["behavior_changed"]
            for stage in stages.values()
        ),
        "browser or existing App OTA contract differs across stages",
    )
    checks = {
        "initial_fixed_generation": True,
        "one_frame_under_30s": True,
        "one_frame_exact_10_data_sectors_plus_root": True,
        "one_frame_requires_restore": True,
        "restore_exact_fixed_generation": True,
        "restore_readback_sha_equal": True,
        "ordinary_reset_all_checks": True,
        "menu_boundary_all_checks": True,
        "final_noop_under_10s": True,
        "final_noop_external_and_internal_zero": True,
        "final_recording_resource_pack_exact_and_zero_write": True,
        "all_protected_partitions_zero": True,
        "fixed_browser_and_app_ota_contract_preserved": True,
    }
    return {
        "schema": "companion.comp_req_775.external_loader_acceptance.v1",
        "status": "MACHINE_READY_OPERATOR_PENDING",
        "fixed_url": offline["fixed_url"],
        "page_sha256": offline["page_sha256"],
        "base_cemp_sha256": fixed_cemp,
        "resource_id": fixed_resource,
        "checks": checks,
        "stages": stages,
        "hardware_contact": 1,
        "remaining_gate": (
            "canonical Chinese fixed-browser versus physical-screen review"
        ),
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--initial", type=Path, required=True)
    parser.add_argument("--probe", type=Path, required=True)
    parser.add_argument("--restore", type=Path, required=True)
    parser.add_argument("--noop", type=Path, required=True)
    parser.add_argument("--offline", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    try:
        summary = verify(
            load(args.initial),
            load(args.probe),
            load(args.restore),
            load(args.noop),
            load(args.offline),
        )
    except (KeyError, TypeError, ValueError) as exc:
        summary = {
            "schema": "companion.comp_req_775.external_loader_acceptance.v1",
            "status": "FAILED",
            "error": str(exc),
            "hardware_contact": 1,
        }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(summary, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    print(json.dumps(summary, indent=2, sort_keys=True))
    if summary["status"] != "MACHINE_READY_OPERATOR_PENDING":
        raise SystemExit(1)


if __name__ == "__main__":
    main()
