#!/usr/bin/env python3
"""Verify that Denzic products use one pinned OTA core and protocol."""

from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
from dataclasses import dataclass
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
DENZIC_ROOT = REPO_ROOT.parents[1]
OUTPUT_PATH = (
    REPO_ROOT / "docs" / "validation" / "denzic-ota-product-matrix.json"
)
SUBMODULE_PATH = Path("third_party/denzic-platform")
PROTOCOL_PATH = Path("ota/protocol/ota_v1.json")


@dataclass(frozen=True)
class ProductRepo:
    name: str
    root: Path
    adapter_tokens: dict[str, tuple[str, ...]]


def require(condition: bool, message: str) -> None:
    if not condition:
        raise AssertionError(message)


def git_output(root: Path, *args: str) -> str:
    return subprocess.check_output(
        ["git", "-C", str(root), *args], text=True, stderr=subprocess.STDOUT
    ).strip()


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def index_gitlink(root: Path) -> str | None:
    output = git_output(root, "ls-files", "--stage", str(SUBMODULE_PATH).replace("\\", "/"))
    if not output:
        return None
    fields = output.split(None, 3)
    require(fields[0] == "160000", f"{root.name}: Denzic path is not a gitlink")
    return fields[1]


def verify_repo(repo: ProductRepo) -> dict:
    require(repo.root.is_dir(), f"{repo.name}: repository is missing: {repo.root}")
    submodule = repo.root / SUBMODULE_PATH
    protocol_path = submodule / PROTOCOL_PATH
    require(protocol_path.is_file(), f"{repo.name}: Denzic submodule is not initialized")

    configured_path = git_output(
        repo.root,
        "config",
        "-f",
        ".gitmodules",
        "--get",
        "submodule.third_party/denzic-platform.path",
    )
    require(
        configured_path.replace("\\", "/") == str(SUBMODULE_PATH).replace("\\", "/"),
        f"{repo.name}: unexpected Denzic submodule path",
    )

    for relative, tokens in repo.adapter_tokens.items():
        path = repo.root / relative
        require(path.is_file(), f"{repo.name}: OTA adapter file is missing: {relative}")
        content = path.read_text(encoding="utf-8")
        for token in tokens:
            require(token in content, f"{repo.name}: {relative} does not use {token!r}")

    checkout_commit = git_output(submodule, "rev-parse", "HEAD")
    staged_commit = index_gitlink(repo.root)
    return {
        "product_repo": repo.name,
        "submodule_path": str(SUBMODULE_PATH).replace("\\", "/"),
        "checkout_commit": checkout_commit,
        "index_gitlink_commit": staged_commit,
        "index_matches_checkout": staged_commit == checkout_commit,
        "protocol_sha256": sha256(protocol_path),
        "adapter_files": sorted(repo.adapter_tokens),
    }


def verify(args: argparse.Namespace) -> dict:
    repos = [
        ProductRepo(
            "companion_firmware",
            args.companion_firmware_root,
            {
                "cubeide/Companion_BLE_Ota_Loader/Makefile": (
                    "DENZIC_OTA := $(ROOT)/third_party/denzic-platform/ota/embedded/c",
                    "$(DENZIC_OTA)/src/denzic_ota_v1.c",
                    "$(DENZIC_OTA)/src/denzic_ota_v1_reorder.c",
                ),
                "cubeide/Companion_BLE_Ota_Loader/Src/companion_ota_v1.c": (
                    "denzic_ota_v1.h",
                    "denzic_ota_v1_reorder.h",
                    "DENZIC_OTA_V1_GATT_SERVICE_UUID_BYTES",
                    "DENZIC_OTA_V1_GATT_DATA_B_UUID_BYTES",
                    "denzic_ota_v1_handle_data_ordered",
                ),
            },
        ),
        ProductRepo(
            "companion_type",
            args.companion_type_root,
            {
                "apps/windows/src-tauri/src/backend/firmware_ota.rs": (
                    "denzic_ota_core",
                ),
                "apps/windows/src-tauri/src/backend/ble_bridge.rs": (
                    "ota_winrt::transfer_companion_ota_winrt",
                    "denzic_ota_core::GATT_SERVICE_UUID_U128",
                ),
                "apps/windows/src-tauri/src/backend/ota_winrt.rs": (
                    "denzic_ota_core::GATT_SERVICE_UUID_U128",
                    "denzic_ota_core::GATT_DATA_B_UUID_U128",
                    "dual_lane_available",
                    "write_data_b",
                    "TransferOptions::dual_lane_bulk",
                    "CompanionOtaWinrtTransport",
                ),
            },
        ),
        ProductRepo(
            "listener_firmware",
            args.listener_firmware_root,
            {
                "ports/esp32/ble_firmware_ota/CMakeLists.txt": (
                    "denzic_ota_v1.c",
                ),
                "ports/esp32/ble_firmware_ota/ble_firmware_ota_esp32.c": (
                    "denzic_ota_v1.h",
                ),
            },
        ),
        ProductRepo(
            "listener_type",
            args.listener_type_root,
            {
                "src-tauri/src/firmware_ota.rs": ("denzic_ota_core",),
                "src-tauri/src/embedded_ble/windows_ble/mod.rs": (
                    "GATT_DATA_B_UUID_U128",
                ),
                "src-tauri/src/embedded_ble/windows_ble/ota_transfer.rs": (
                    "prefer_dual_lane",
                    "DATA_B",
                ),
                "src/lib/firmwareOta.ts": (
                    "@denzic/ota-core",
                    "DENZIC_OTA_V1_PROTOCOL_NAME",
                    "LISTENER_OTA_V1_TRANSPORT_BOUNDARY",
                ),
            },
        ),
    ]

    products = [verify_repo(repo) for repo in repos]
    checkout_commits = {item["checkout_commit"] for item in products}
    protocol_hashes = {item["protocol_sha256"] for item in products}
    require(len(protocol_hashes) == 1, "product repositories use different OTA protocols")

    protocol = json.loads(
        (repos[0].root / SUBMODULE_PATH / PROTOCOL_PATH).read_text(encoding="utf-8")
    )
    require(protocol.get("name") == "denzic_ota_v1", "shared protocol name drift")
    require(protocol.get("control_bytes") == 20, "shared control packet size drift")
    require(protocol.get("image_identity") == "crc32_ieee", "resume identity drift")
    required_gatt = {
        "service_uuid",
        "control_uuid",
        "data_uuid",
        "data_b_uuid",
        "status_uuid",
    }
    gatt_keys = set(protocol.get("gatt", {}))
    require(
        required_gatt <= gatt_keys,
        "shared GATT profile is incomplete (need service/control/data/data_b/status)",
    )
    require(
        gatt_keys == required_gatt,
        f"shared GATT profile has unexpected keys: {sorted(gatt_keys - required_gatt)}",
    )
    dual_lane = protocol.get("dual_lane")
    require(isinstance(dual_lane, dict), "shared dual_lane contract missing")
    require(
        {
            "description",
            "recommended_reorder_slots",
            "recommended_window_chunks",
            "recommended_inactive_link_window_chunks",
        }
        <= set(dual_lane),
        "shared dual_lane contract is incomplete",
    )
    require(
        dual_lane.get("recommended_reorder_slots") == 16,
        "shared dual_lane recommended_reorder_slots drift",
    )
    require(
        dual_lane.get("recommended_window_chunks") == 400,
        "shared dual_lane recommended_window_chunks drift",
    )

    commit_aligned = len(checkout_commits) == 1
    commit_groups: dict[str, list[str]] = {}
    for item in products:
        commit_groups.setdefault(item["checkout_commit"], []).append(item["product_repo"])

    return {
        "schema": "denzic.validation.ota-product-matrix.v1",
        "result": "PASS" if commit_aligned else "NO_GO_COMMIT_DRIFT",
        "shared_core_commit": next(iter(checkout_commits)) if commit_aligned else None,
        "checkout_commit_groups": commit_groups,
        "shared_protocol": protocol["name"],
        "shared_protocol_version": protocol["version"],
        "shared_protocol_sha256": next(iter(protocol_hashes)),
        "products": products,
        "boundary": {
            "shared": "protocol, GATT identity (incl. dual-lane DATA_B), resume state machine, reorder helper, host and embedded cores",
            "per_target": "package compatibility, Flash installer, boot confirmation, rollback and resources",
            "wrong_target_policy": "reject before erase or activation",
        },
        "dual_lane": {
            "data_b_uuid": protocol.get("gatt", {}).get("data_b_uuid"),
            "recommended_reorder_slots": dual_lane.get("recommended_reorder_slots")
            if isinstance(dual_lane, dict)
            else None,
            "recommended_window_chunks": dual_lane.get("recommended_window_chunks")
            if isinstance(dual_lane, dict)
            else None,
        },
        "checks": [
            "Companion and Listener firmware/Type trees report their checked-out Denzic commits; commit drift is NO_GO until the shared platform is deliberately aligned",
            "all four trees expose byte-identical denzic_ota_v1 protocol JSON including data_b_uuid and dual_lane",
            "each product endpoint references a Denzic shared core instead of a parallel OTA protocol",
            "Companion FW/Type and Listener Type wire dual-lane DATA_B surfaces against the shared core",
            "target installers remain separate from the shared transport core",
        ],
        "no_go_reason": None
        if commit_aligned
        else "Product repositories are not pinned to the same Denzic platform checkout; hold Companion OTA/resource installer work until the Listener OTA validation branch is accepted or the shared commit alignment is deliberately updated.",
    }


def resolved(path: str) -> Path:
    return Path(path).expanduser().resolve()


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--companion-firmware-root", type=resolved, default=REPO_ROOT
    )
    parser.add_argument(
        "--companion-type-root",
        type=resolved,
        default=DENZIC_ROOT / "Companion" / "Companion-Type",
    )
    parser.add_argument(
        "--listener-firmware-root",
        type=resolved,
        default=DENZIC_ROOT / "Listener" / "Listener-Firmware",
    )
    parser.add_argument(
        "--listener-type-root",
        type=resolved,
        default=DENZIC_ROOT / "Listener" / "Listener-Type",
    )
    parser.add_argument("--write-fixture", action="store_true")
    args = parser.parse_args()
    report = verify(args)
    if args.write_fixture:
        OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
        OUTPUT_PATH.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(report, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
