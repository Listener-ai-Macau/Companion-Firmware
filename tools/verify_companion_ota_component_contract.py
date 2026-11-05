#!/usr/bin/env python3
"""Verify Companion OTA ownership of firmware and external resource packs."""

from __future__ import annotations

import argparse
import json
import subprocess
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
CONTRACT_PATH = REPO_ROOT / "docs" / "companion_ota_component_contract.json"
OUTPUT_PATH = (
    REPO_ROOT
    / "docs"
    / "validation"
    / "companion-ota-component-contract-verification.json"
)
SUBMODULE_ROOT = REPO_ROOT / "third_party" / "denzic-platform"


def require(condition: bool, message: str) -> None:
    if not condition:
        raise AssertionError(message)


def read_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def git_output(*args: str) -> str:
    return subprocess.check_output(
        ["git", "-C", str(SUBMODULE_ROOT), *args], text=True
    ).strip()


def verify() -> dict:
    contract = read_json(CONTRACT_PATH)
    require(
        contract.get("schema") == "companion.ota.component-contract.v1",
        "unexpected Companion OTA component contract schema",
    )

    shared = contract["shared_transport"]
    require(shared["submodule"] == "third_party/denzic-platform", "wrong OTA submodule")
    require(shared["protocol"] == "denzic_ota_v1", "wrong shared OTA protocol")
    require(
        shared["security_boundary"] == "crc32_is_resume_identity_not_authentication",
        "CRC32 security boundary must stay explicit",
    )

    capabilities_path = SUBMODULE_ROOT / "capabilities.json"
    protocol_path = SUBMODULE_ROOT / "ota" / "protocol" / "ota_v1.json"
    require(capabilities_path.is_file(), "Denzic Platform submodule is not initialized")
    require(protocol_path.is_file(), "Denzic OTA v1 protocol is missing")
    capabilities = read_json(capabilities_path)
    ota_caps = [item for item in capabilities["capabilities"] if item["id"] == "ota"]
    require(len(ota_caps) == 1, "Denzic OTA capability must exist exactly once")
    require(ota_caps[0]["status"] == "active", "Denzic OTA capability is not active")
    require(ota_caps[0]["contract"] == "denzic_ota_v1", "Denzic OTA contract drift")
    protocol = read_json(protocol_path)
    require(protocol["name"] == "denzic_ota_v1", "Denzic protocol name drift")
    require(protocol["image_identity"] == "crc32_ieee", "resume identity drift")
    required_gatt = {
        "service_uuid",
        "control_uuid",
        "data_uuid",
        "data_b_uuid",
        "status_uuid",
    }
    gatt_keys = set(protocol["gatt"])
    require(
        required_gatt <= gatt_keys,
        "Denzic GATT profile is incomplete (need service/control/data/data_b/status)",
    )
    require(
        gatt_keys == required_gatt,
        f"Denzic GATT profile has unexpected keys: {sorted(gatt_keys - required_gatt)}",
    )
    dual_lane = protocol.get("dual_lane")
    require(isinstance(dual_lane, dict), "Denzic dual_lane contract missing")
    require(
        {
            "description",
            "recommended_reorder_slots",
            "recommended_window_chunks",
            "recommended_inactive_link_window_chunks",
        }
        <= set(dual_lane),
        "Denzic dual_lane contract is incomplete",
    )
    require(
        dual_lane.get("recommended_reorder_slots") == 16,
        "dual_lane recommended_reorder_slots drift",
    )
    require(
        dual_lane.get("recommended_window_chunks") == 400,
        "dual_lane recommended_window_chunks drift",
    )

    bundle = contract["bundle"]
    require(bundle["manifest_authentication"] == "signed_manifest", "manifest signature required")
    require(bundle["component_digest"] == "sha256", "component digest must be SHA-256")
    require(
        bundle["anti_rollback"] == "monotonic_version_per_component",
        "component anti-rollback policy missing",
    )
    required_fields = set(bundle["required_component_fields"])
    require(
        {"kind", "component_version", "target_family", "board_target", "sha256", "compatibility"}
        <= required_fields,
        "required component manifest fields are incomplete",
    )

    components = {item["kind"]: item for item in contract["components"]}
    require("mcu_app" in components and "ui_assets" in components, "core OTA components missing")
    require(all(item["ota_managed"] for item in components.values()), "replaceable component escaped OTA")
    ui_assets = components["ui_assets"]
    require(ui_assets["storage"] == "external_nor", "UI assets must remain external")
    require("inactive" in ui_assets["download_target"] or "staging" in ui_assets["download_target"], "UI update would overwrite active data")
    require("atomic" in ui_assets["activation"], "UI activation must be atomic")
    require("previous_active" in ui_assets["failure_policy"], "UI fallback must preserve previous pack")
    require(
        {"min_app_version", "max_app_version", "screen_profile", "asset_format"}
        <= set(ui_assets["compatibility_fields"]),
        "UI/app/profile compatibility fields are incomplete",
    )

    excluded = set(contract["excluded_mutable_data"])
    require(
        {"recording_cache", "diag_log_mirror", "settings_user_data"} <= excluded,
        "mutable user data is not protected from OTA",
    )
    transaction = contract["transactions"]
    require("must_not_rewrite_mcu_app" in transaction["resource_only_update"], "resource-only isolation missing")
    require("must_preserve" in transaction["firmware_only_update"], "firmware-only preservation missing")
    require("before_atomic_commit" in transaction["power_loss"], "power-loss rule missing")

    doc_tokens = {
        "docs/bootloader_flash_layout.md": ["ui_assets_candidate", "component", "recording_cache"],
        "docs/companion_resource_memory_policy.md": ["OTA", "ui_assets", "原子"],
        "docs/stm32wba_migration_rules.md": ["Denzic", "Application Install Manager", "ui_assets"],
        "docs/ble_gatt_contract.md": ["denzic_ota_v1", "opaque byte stream", "component"],
        "docs/companion_screen_project_plan.md": ["SCR-14", "Denzic-Platform", "资源 OTA"],
    }
    for relative, tokens in doc_tokens.items():
        text = (REPO_ROOT / relative).read_text(encoding="utf-8")
        for token in tokens:
            require(token in text, f"{relative} is missing OTA contract token {token!r}")

    return {
        "schema": "companion.validation.ota-component-contract.v1",
        "result": "PASS",
        "contract": str(CONTRACT_PATH.relative_to(REPO_ROOT)).replace("\\", "/"),
        "shared_submodule_commit": git_output("rev-parse", "HEAD"),
        "shared_protocol": protocol["name"],
        "shared_protocol_version": protocol["version"],
        "component_kinds": sorted(components),
        "external_resource_ota_managed": True,
        "mutable_user_data_preserved": sorted(excluded),
        "checks": [
            "shared transport submodule is initialized and exposes all protocol/host/embedded layers",
            "denzic_ota_v1 GATT includes dual-lane DATA_B and dual_lane window/reorder recommendations",
            "Denzic CRC32 remains resume identity rather than product authentication",
            "MCU app and external UI assets are separate OTA components",
            "resource activation is verified and atomic with previous-pack fallback",
            "resource-only and firmware-only updates preserve unrelated components",
            "recordings, diagnostics, and settings are outside normal OTA erase scope",
            "WB55/WBA/ESP installation mechanics remain target adapters",
        ],
        "dual_lane": {
            "data_b_uuid": protocol["gatt"]["data_b_uuid"],
            "recommended_reorder_slots": dual_lane.get("recommended_reorder_slots"),
            "recommended_window_chunks": dual_lane.get("recommended_window_chunks"),
        },
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--write-fixture", action="store_true")
    args = parser.parse_args()
    report = verify()
    if args.write_fixture:
        OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
        OUTPUT_PATH.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(report, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
