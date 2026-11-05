#!/usr/bin/env python3
"""Offline fault injection for the hardware acceptance aggregator."""

from __future__ import annotations

import copy
import importlib.util
import json
from pathlib import Path


REPO = Path(__file__).resolve().parents[2]
ROOT = REPO / ".cache/validation/comp-req-775-incremental-sync"
VERIFIER = (
    REPO
    / "tools/faraday_upper_art/verify_comp_req_775_hardware_summary.py"
)
OUTPUT = ROOT / "HARDWARE_SUMMARY_VERIFIER_OFFLINE_READY.json"


def load_verifier():
    spec = importlib.util.spec_from_file_location("summary_verifier", VERIFIER)
    if spec is None or spec.loader is None:
        raise RuntimeError("cannot load summary verifier")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def load(relative: str) -> dict:
    return json.loads((ROOT / relative).read_text(encoding="utf-8"))


def stage(
    source: dict,
    *,
    status: str,
    total_ms: int,
    hardware_contact: int = 1,
) -> dict:
    value = copy.deepcopy(source)
    value["status"] = status
    value["hardware_contact"] = hardware_contact
    value["partition_readback_verified"] = True
    value["readback_partition_sha256"] = value["desired_partition_sha256"]
    value["recording_resource_pack"]["current_match"] = True
    value["recording_resource_pack"]["changed_sector_count"] = 0
    value["recording_resource_pack"]["readback_verified"] = True
    value["ordinary_reset_performed"] = True
    value["timing_ms"]["total"] = total_ms
    value["browser_contract"] = {
        "fixed_url": load("OFFLINE_READY.json")["fixed_url"],
        "http_status": 200,
        "page_sha256": load("OFFLINE_READY.json")["page_sha256"],
    }
    value["existing_app_ota"] = {
        "loader_worktree_unchanged": True,
        "behavior_changed": False,
    }
    value["ordinary_reset"] = {
        "checks": {
            "mount": True,
            "busy": True,
            "first_frame": True,
            "no_fault": True,
        }
    }
    return value


def rejected(verifier, fixtures: list[dict]) -> bool:
    try:
        verifier.verify(*fixtures)
    except (KeyError, TypeError, ValueError):
        return True
    return False


def main() -> None:
    verifier = load_verifier()
    offline = load("OFFLINE_READY.json")
    initial = stage(
        load("stlink-sync/generation-2-dry-run.json"),
        status="MACHINE_READY_MENU_PENDING",
        total_ms=15000,
    )
    initial["active_generation_before"] = 0
    initial["active_generation_after"] = 1
    initial["target_root"]["generation"] = 1
    initial["target_root"]["resource_id"] = offline["resource_id"]
    initial["cemp"]["target"]["sha256"] = offline["base_cemp_sha256"]
    probe = stage(
        load("stlink-sync/generation-2-dry-run.json"),
        status="MACHINE_READY_RESTORE_REQUIRED",
        total_ms=25000,
    )
    probe["performance_contract"]["changed_resource_under_30s"] = True
    restore = stage(
        load("stlink-sync/generation-3-restore-dry-run.json"),
        status="MACHINE_READY_OPERATOR_PENDING",
        total_ms=25000,
    )
    restore["target_root"]["resource_id"] = offline["resource_id"]
    restore["cemp"]["target"]["sha256"] = offline["base_cemp_sha256"]
    restore["menu_boundary"] = {
        "evidence": {
            "checks": {
                "enter": True,
                "exit": True,
                "busy": True,
                "no_fault": True,
            }
        }
    }
    noop = stage(
        load("stlink-sync/generation-3-noop-dry-run.json"),
        status="MACHINE_READY_MENU_PENDING",
        total_ms=5000,
    )
    noop["performance_contract"]["same_resource_under_10s"] = True
    fixtures = [initial, probe, restore, noop, offline]
    ready = verifier.verify(*fixtures)
    rebased = copy.deepcopy(fixtures)
    rebased[1]["active_generation_before"] = 3
    rebased[1]["active_generation_after"] = 4
    rebased[1]["target_root"]["generation"] = 4
    rebased[1]["changed_data_sectors"] = [
        f"0x{offset:06X}"
        for offset in range(0x14C000, 0x156000, 0x1000)
    ]
    rebased[2]["active_generation_before"] = 4
    rebased[2]["active_generation_after"] = 5
    rebased[2]["target_root"]["generation"] = 5
    rebased[2]["changed_data_sectors"] = [
        f"0x{offset:06X}"
        for offset in range(0x156000, 0x160000, 0x1000)
    ]
    rebased[3]["active_generation_before"] = 5
    rebased[3]["active_generation_after"] = 5
    rebased[3]["target_root"]["generation"] = 5
    rebased_ready = verifier.verify(*rebased)
    menu_on_noop = copy.deepcopy(fixtures)
    menu_on_noop[2]["status"] = "MACHINE_READY_MENU_PENDING"
    menu_on_noop[3]["menu_boundary"] = menu_on_noop[2].pop(
        "menu_boundary"
    )
    menu_on_noop_ready = verifier.verify(*menu_on_noop)

    slow_probe = copy.deepcopy(fixtures)
    slow_probe[1]["timing_ms"]["total"] = 30001
    wrong_restore = copy.deepcopy(fixtures)
    wrong_restore[2]["target_root"]["resource_id"] = "00" * 32
    menu_fault = copy.deepcopy(fixtures)
    menu_fault[2]["menu_boundary"]["evidence"]["checks"]["no_fault"] = False
    protected_write = copy.deepcopy(fixtures)
    protected_write[3]["protected_partitions"][
        "ota_app_internal_flash_write_bytes"
    ] = 1
    wrong_static_pack = copy.deepcopy(fixtures)
    wrong_static_pack[3]["recording_resource_pack"]["pack_sha256"] = (
        "00" * 32
    )
    checks = {
        "valid_summary_ready": (
            ready["status"] == "MACHINE_READY_OPERATOR_PENDING"
            and all(ready["checks"].values())
        ),
        "rebased_generation_summary_ready": (
            rebased_ready["status"] == "MACHINE_READY_OPERATOR_PENDING"
            and all(rebased_ready["checks"].values())
        ),
        "menu_evidence_on_final_noop_ready": (
            menu_on_noop_ready["status"]
            == "MACHINE_READY_OPERATOR_PENDING"
            and all(menu_on_noop_ready["checks"].values())
        ),
        "slow_one_frame_rejected": rejected(verifier, slow_probe),
        "wrong_restore_resource_rejected": rejected(verifier, wrong_restore),
        "menu_fault_rejected": rejected(verifier, menu_fault),
        "protected_partition_write_rejected": rejected(
            verifier, protected_write
        ),
        "wrong_recording_resource_pack_rejected": rejected(
            verifier, wrong_static_pack
        ),
    }
    receipt = {
        "schema": "companion.comp_req_775.hardware_summary_test.v1",
        "status": "MACHINE_READY" if all(checks.values()) else "FAILED",
        "checks": checks,
        "hardware_contact": 0,
    }
    OUTPUT.write_text(
        json.dumps(receipt, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    print(json.dumps(receipt, indent=2, sort_keys=True))
    if receipt["status"] != "MACHINE_READY":
        raise SystemExit(1)


if __name__ == "__main__":
    main()
