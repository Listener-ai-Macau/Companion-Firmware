#!/usr/bin/env python3
"""Fault-injection checks for the ST-LINK UI generation transaction."""

from __future__ import annotations

import importlib.util
import json
import struct
from pathlib import Path


REPO = Path(__file__).resolve().parents[2]
ARTIFACTS = (
    REPO / ".cache/validation/comp-req-775-incremental-sync"
)
SYNC_PATH = REPO / "tools/sync_companion_ui_assets_stlink.py"
CURRENT_PATH = (
    ARTIFACTS / "stlink-sync/synthetic-generation-1.bin"
)
BUNDLE_PATH = ARTIFACTS / "resource-ota/generation-2.cuot"
STATIC_PACK_PATH = (
    REPO
    / ".cache/validation/comp-req-775-recording-resources/"
    "companion_recording_resources.crrp"
)
OUTPUT = ARTIFACTS / "STLINK_TRANSACTION_FAULT_INJECTION.json"
MIGRATION_CURRENT_PATH = (
    ARTIFACTS
    / "touch-five-phase-generation-7/hardware-sync/trusted-current.bin"
)
MIGRATION_BOOTSTRAP_PATH = (
    REPO
    / ".cache/validation/comp-req-775-native-cemp-catalog/"
    "bootstrap-partition-generation-8.bin"
)
COMPACTION_CURRENT_PATH = (
    REPO
    / ".cache/validation/comp-req-775-browser-device-single-source-final/"
    "generation-14/hardware/trusted-current.bin"
)
COMPACTION_BUNDLE_PATH = (
    REPO
    / ".cache/validation/comp-req-775-browser-device-single-source-final/"
    "50-generation-15-compacted/generation-15.cuot"
)
ROOT_RECOVERY_BOOTSTRAP_PATH = (
    REPO
    / ".cache/validation/comp-req-775-browser-device-single-source-final/"
    "97-recording-browser-timeline/hardware/trusted-current.bin"
)


def load_sync_module():
    spec = importlib.util.spec_from_file_location(
        "sync_companion_ui_assets_stlink", SYNC_PATH
    )
    if spec is None or spec.loader is None:
        raise RuntimeError("cannot load ST-LINK sync module")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def require(condition: bool, message: str) -> None:
    if not condition:
        raise AssertionError(message)


def generation(sync, image: bytes) -> int:
    root = sync.active_root(image)
    return int(root["generation"]) if root else 0


def apply_data_sectors(sync, image: bytes, desired: bytes, offsets: list[int]):
    result = bytearray(image)
    for offset in offsets:
        result[offset : offset + sync.SECTOR_BYTES] = desired[
            offset : offset + sync.SECTOR_BYTES
        ]
    return result


def main() -> None:
    sync = load_sync_module()
    current_without_static = bytearray(CURRENT_PATH.read_bytes())
    current_without_static[
        sync.STATIC_RESOURCE_BASE : sync.STATIC_RESOURCE_LIMIT
    ] = b"\xFF" * sync.STATIC_RESOURCE_CAPACITY
    current_without_static = bytes(current_without_static)
    static_resource = sync.parse_static_resource_pack(STATIC_PACK_PATH)
    noop_bundle = sync.parse_cuot(
        ARTIFACTS / "resource-ota/generation-1-noop.cuot"
    )
    static_install = sync.overlay_static_resource(
        sync.plan(current_without_static, noop_bundle),
        static_resource,
    )
    require(
        static_install["noop"] is False
        and static_install["root_sector"] is None
        and len(static_install["static_resource_changed_sectors"]) == 33,
        "missing static resources must plan 33 sectors without a UI root",
    )
    static_partial = apply_data_sectors(
        sync,
        current_without_static,
        bytes(static_install["desired"]),
        list(static_install["static_resource_changed_sectors"])[:16],
    )
    require(
        generation(sync, bytes(static_partial)) == 1,
        "partial static-resource write must preserve UI generation 1",
    )
    current = bytes(static_install["desired"])
    require(
        current[
            sync.STATIC_RESOURCE_BASE :
            sync.STATIC_RESOURCE_BASE + int(static_resource["bytes"])
        ]
        == bytes(static_resource["data"]),
        "installed static resource bytes must equal the source pack",
    )
    CURRENT_PATH.write_bytes(current)
    cuot = sync.parse_cuot(BUNDLE_PATH)
    transaction = sync.overlay_static_resource(
        sync.plan(current, cuot), static_resource
    )
    desired = bytes(transaction["desired"])
    data_offsets = list(transaction["changed_data_sectors"])
    root_offset = int(transaction["root_sector"])

    require(generation(sync, current) == 1, "fixture must start at generation 1")
    require(data_offsets, "generation 2 must change data sectors")

    data_only = apply_data_sectors(sync, current, desired, data_offsets)
    require(
        generation(sync, bytes(data_only)) == 1,
        "power loss before root commit must keep generation 1 active",
    )

    partial_data = apply_data_sectors(
        sync, current, desired, data_offsets[: len(data_offsets) // 2]
    )
    require(
        generation(sync, bytes(partial_data)) == 1,
        "partial data write must keep generation 1 active",
    )

    corrupt_root = bytearray(data_only)
    corrupt_root[root_offset : root_offset + sync.SECTOR_BYTES] = desired[
        root_offset : root_offset + sync.SECTOR_BYTES
    ]
    corrupt_root[root_offset + 124] ^= 0x01
    require(
        generation(sync, bytes(corrupt_root)) == 1,
        "corrupt inactive root must fall back to generation 1",
    )

    committed = bytearray(data_only)
    committed[root_offset : root_offset + sync.SECTOR_BYTES] = desired[
        root_offset : root_offset + sync.SECTOR_BYTES
    ]
    require(bytes(committed) == desired, "root-last result must equal plan")
    require(
        generation(sync, bytes(committed)) == 2,
        "valid root-last commit must activate generation 2",
    )

    corrupt_blob = bytearray(committed)
    corrupt_blob[data_offsets[0]] ^= 0x01
    require(
        generation(sync, bytes(corrupt_blob)) == 1,
        "blob CRC failure after root write must fall back to generation 1",
    )

    stale_rejected = False
    try:
        sync.plan(bytes(committed), cuot)
    except SystemExit as exc:
        stale_rejected = "expected generation is stale" in str(exc)
    require(stale_rejected, "stale generation must fail closed")

    compaction_current = COMPACTION_CURRENT_PATH.read_bytes()
    compaction_bundle = sync.parse_cuot(COMPACTION_BUNDLE_PATH)
    compaction_default_rejected = False
    try:
        sync.plan(compaction_current, compaction_bundle)
    except SystemExit as exc:
        compaction_default_rejected = (
            "planned blob offset does not match current arena" in str(exc)
        )
    require(
        compaction_default_rejected,
        "generation compaction must remain disabled by default",
    )
    compaction = sync.plan(
        compaction_current,
        compaction_bundle,
        allow_generation_compaction=True,
    )
    compaction_desired = bytes(compaction["desired"])
    compaction_root = int(compaction["root_sector"])
    require(
        compaction["generation_compaction"] is True
        and compaction["abort_preserves_active_generation"] is False
        and compaction["changed_data_sectors"]
        and compaction_root
            != int(sync.active_root(compaction_current)["root_offset"]),
        "explicit compaction must rebuild the arena through inactive root",
    )
    compaction_data = apply_data_sectors(
        sync,
        compaction_current,
        compaction_desired,
        list(compaction["changed_data_sectors"]),
    )
    compaction_committed = bytearray(compaction_data)
    compaction_committed[
        compaction_root : compaction_root + sync.SECTOR_BYTES
    ] = compaction_desired[
        compaction_root : compaction_root + sync.SECTOR_BYTES
    ]
    require(
        bytes(compaction_committed) == compaction_desired
        and generation(sync, bytes(compaction_committed)) == 15,
        "root-last compaction must activate exact generation 15",
    )

    noop = sync.overlay_static_resource(
        sync.plan(current, noop_bundle), static_resource
    )
    require(noop["noop"] is True, "same resource must be a no-op")
    require(
        noop["changed_data_sectors"] == [] and noop["root_sector"] is None,
        "same resource must plan zero sectors",
    )

    relocated_same_resource = dict(cuot)
    relocated_same_resource["resource_id"] = bytes(
        sync.active_root(current)["resource_id"]
    )
    relocated = sync.plan(current, relocated_same_resource)
    require(
        relocated["noop"] is False
        and relocated["root_sector"] is not None
        and relocated["changed_data_sectors"],
        "same resource with a different blob contract must relocate",
    )

    empty = bytes([0xFF]) * sync.PARTITION_BYTES
    bootstrap = sync.overlay_static_resource(
        sync.bootstrap_plan(current=empty, bootstrap=current),
        static_resource,
    )
    bootstrap_desired = bytes(bootstrap["desired"])
    bootstrap_data = apply_data_sectors(
        sync,
        empty,
        bootstrap_desired,
        list(bootstrap["changed_data_sectors"]),
    )
    require(
        generation(sync, bytes(bootstrap_data)) == 0,
        "bootstrap data before root must not activate generation 1",
    )
    bootstrap_root = int(bootstrap["root_sector"])
    bootstrap_committed = bytearray(bootstrap_data)
    bootstrap_committed[
        bootstrap_root : bootstrap_root + sync.SECTOR_BYTES
    ] = bootstrap_desired[
        bootstrap_root : bootstrap_root + sync.SECTOR_BYTES
    ]
    require(
        generation(sync, bytes(bootstrap_committed)) == 1,
        "bootstrap root-last must activate generation 1",
    )
    bootstrap_over_active_rejected = False
    try:
        sync.bootstrap_plan(current=current, bootstrap=current)
    except SystemExit as exc:
        bootstrap_over_active_rejected = (
            "forbidden when an active generation exists" in str(exc)
        )
    require(
        bootstrap_over_active_rejected,
        "bootstrap must refuse to overwrite an active generation",
    )

    recovery_bootstrap = ROOT_RECOVERY_BOOTSTRAP_PATH.read_bytes()
    recovery_root = sync.active_root(recovery_bootstrap)
    require(
        recovery_root is not None
        and int(recovery_root["generation"]) == 16,
        "root-recovery fixture must target generation 16",
    )
    recovery_current = bytearray(recovery_bootstrap)
    recovery_current[sync.ROOT_A : sync.ROOT_B + sync.SECTOR_BYTES] = (
        b"\xFF" * (sync.SECTOR_BYTES * 2)
    )
    recovery_blob_start = int(recovery_root["blob_offset"])
    recovery_blob_end = sync.align_sector(int(recovery_root["arena_next"]))
    recovery_current[recovery_blob_start:recovery_blob_end] = (
        b"\xFF" * (recovery_blob_end - recovery_blob_start)
    )
    recovery_default_rejected = False
    try:
        sync.bootstrap_plan(
            current=bytes(recovery_current),
            bootstrap=recovery_bootstrap,
        )
    except SystemExit as exc:
        recovery_default_rejected = (
            "must target generation 1" in str(exc)
        )
    require(
        recovery_default_rejected,
        "generation root recovery must remain disabled by default",
    )
    wrong_base_recovery_current = bytearray(MIGRATION_CURRENT_PATH.read_bytes())
    wrong_base_recovery_current[
        sync.ROOT_A : sync.ROOT_B + sync.SECTOR_BYTES
    ] = b"\xFF" * (sync.SECTOR_BYTES * 2)
    recovery_wrong_base_rejected = False
    try:
        sync.bootstrap_plan(
            current=bytes(wrong_base_recovery_current),
            bootstrap=recovery_bootstrap,
            allow_generation_root_recovery=True,
        )
    except SystemExit as exc:
        recovery_wrong_base_rejected = (
            "requires the exact current CEMP base" in str(exc)
        )
    require(
        recovery_wrong_base_rejected,
        "generation root recovery must reject a different CEMP base",
    )
    recovery = sync.bootstrap_plan(
        current=bytes(recovery_current),
        bootstrap=recovery_bootstrap,
        allow_generation_root_recovery=True,
    )
    recovery_desired = bytes(recovery["desired"])
    recovery_data_only = apply_data_sectors(
        sync,
        bytes(recovery_current),
        recovery_desired,
        list(recovery["changed_data_sectors"]),
    )
    require(
        recovery["generation_root_recovery"] is True
        and recovery["base_migration"] is False
        and generation(sync, bytes(recovery_data_only)) == 0,
        "generation recovery data must preserve generation 0 until root commit",
    )
    recovery_committed = bytearray(recovery_data_only)
    recovery_root_offset = int(recovery["root_sector"])
    recovery_committed[
        recovery_root_offset : recovery_root_offset + sync.SECTOR_BYTES
    ] = recovery_desired[
        recovery_root_offset : recovery_root_offset + sync.SECTOR_BYTES
    ]
    require(
        generation(sync, bytes(recovery_committed)) == 16
        and bytes(sync.active_root(bytes(recovery_committed))["resource_id"])
        == bytes(recovery_root["resource_id"]),
        "root-last recovery must activate the exact generation 16 identity",
    )

    migration_current = MIGRATION_CURRENT_PATH.read_bytes()
    migration_bootstrap = MIGRATION_BOOTSTRAP_PATH.read_bytes()
    migration_active = sync.active_root(migration_current)
    require(
        migration_active is not None
        and int(migration_active["generation"]) == 7,
        "base migration fixture must start at generation 7",
    )
    migration_default_rejected = False
    try:
        sync.bootstrap_plan(
            current=migration_current,
            bootstrap=migration_bootstrap,
        )
    except SystemExit as exc:
        migration_default_rejected = (
            "forbidden when an active generation exists" in str(exc)
        )
    require(
        migration_default_rejected,
        "base migration must remain disabled by default",
    )
    skipped_generation = bytearray(migration_bootstrap)
    migration_bootstrap_root = sync.active_root(migration_bootstrap)
    skipped_root_offset = int(migration_bootstrap_root["root_offset"])
    struct.pack_into(
        "<I",
        skipped_generation,
        skipped_root_offset + 8,
        9,
    )
    struct.pack_into(
        "<I",
        skipped_generation,
        skipped_root_offset + 124,
        sync.crc32(
            skipped_generation[
                skipped_root_offset : skipped_root_offset + 124
            ]
        ),
    )
    skipped_generation_rejected = False
    try:
        sync.bootstrap_plan(
            current=migration_current,
            bootstrap=bytes(skipped_generation),
            allow_base_migration=True,
        )
    except SystemExit as exc:
        skipped_generation_rejected = (
            "target exactly the next generation" in str(exc)
        )
    require(
        skipped_generation_rejected,
        "base migration must reject a skipped generation",
    )
    wrong_root = bytearray(migration_bootstrap)
    wrong_root[sync.ROOT_A : sync.ROOT_A + sync.SECTOR_BYTES] = wrong_root[
        sync.ROOT_B : sync.ROOT_B + sync.SECTOR_BYTES
    ]
    wrong_root[sync.ROOT_B : sync.ROOT_B + sync.SECTOR_BYTES] = (
        b"\xFF" * sync.SECTOR_BYTES
    )
    wrong_root_rejected = False
    try:
        sync.bootstrap_plan(
            current=migration_current,
            bootstrap=bytes(wrong_root),
            allow_base_migration=True,
        )
    except SystemExit as exc:
        wrong_root_rejected = (
            "commit through the inactive root" in str(exc)
        )
    require(
        wrong_root_rejected,
        "base migration must reject the active root",
    )
    migration = sync.bootstrap_plan(
        current=migration_current,
        bootstrap=migration_bootstrap,
        allow_base_migration=True,
    )
    migration_desired = bytes(migration["desired"])
    migration_root = int(migration["root_sector"])
    require(
        migration["base_migration"] is True
        and int(migration["generation_after"]) == 8,
        "explicit base migration must target generation 8",
    )
    require(
        migration_root
        != int(migration_active["root_offset"])
        and migration_root
        == (
            sync.ROOT_B
            if int(migration_active["root_offset"]) == sync.ROOT_A
            else sync.ROOT_A
        ),
        "base migration must select the inactive root",
    )
    migration_data_only = apply_data_sectors(
        sync,
        migration_current,
        migration_desired,
        list(migration["changed_data_sectors"]),
    )
    require(
        generation(sync, bytes(migration_data_only)) == 7,
        "base migration data before root must preserve generation 7",
    )
    migration_committed = bytearray(migration_data_only)
    migration_committed[
        migration_root : migration_root + sync.SECTOR_BYTES
    ] = migration_desired[
        migration_root : migration_root + sync.SECTOR_BYTES
    ]
    require(
        bytes(migration_committed) == migration_desired
        and generation(sync, bytes(migration_committed)) == 8,
        "base migration root-last commit must activate generation 8",
    )
    require(
        sync.base_identity(bytes(migration_committed))
        == sync.base_identity(migration_bootstrap),
        "base migration must install the exact target CEMP identity",
    )

    restore_cuot = sync.parse_cuot(
        ARTIFACTS / "resource-ota/generation-3-restore.cuot"
    )
    restore = sync.overlay_static_resource(
        sync.plan(bytes(committed), restore_cuot), static_resource
    )
    restored = bytes(restore["desired"])
    restored_root = sync.active_root(restored)
    require(
        restored_root is not None
        and int(restored_root["generation"]) == 3,
        "restore bundle must activate generation 3",
    )
    require(
        bytes(restored_root["resource_id"])
        == bytes(sync.active_root(current)["resource_id"]),
        "restore bundle must return to the fixed-page resource id",
    )
    original_blob = current[
        int(sync.active_root(current)["blob_offset"]) :
        int(sync.active_root(current)["blob_offset"])
        + int(sync.active_root(current)["blob_size"])
    ]
    restored_blob = restored[
        int(restored_root["blob_offset"]) :
        int(restored_root["blob_offset"]) + int(restored_root["blob_size"])
    ]
    require(
        restored_blob == original_blob,
        "generation 3 must restore the exact fixed-page generation blob",
    )
    final_noop_cuot = sync.parse_cuot(
        ARTIFACTS / "resource-ota/generation-3-noop.cuot"
    )
    final_noop = sync.overlay_static_resource(
        sync.plan(restored, final_noop_cuot), static_resource
    )
    require(
        final_noop["noop"] is True
        and final_noop["changed_data_sectors"] == []
        and final_noop["root_sector"] is None,
        "restored generation 3 must support a zero-sector no-op",
    )
    fixture_root = ARTIFACTS / "stlink-sync"
    fixture_root.mkdir(parents=True, exist_ok=True)
    (fixture_root / "synthetic-generation-2.bin").write_bytes(
        bytes(committed)
    )
    (fixture_root / "synthetic-generation-3-restored.bin").write_bytes(
        restored
    )

    receipt = {
        "schema": "companion.comp_req_775.stlink_transaction_test.v1",
        "status": "MACHINE_READY",
        "checks": {
            "partial_data_preserves_generation_1": True,
            "all_data_before_root_preserves_generation_1": True,
            "corrupt_root_falls_back_to_generation_1": True,
            "root_last_activates_generation_2": True,
            "corrupt_blob_falls_back_to_generation_1": True,
            "stale_generation_rejected": True,
            "generation_compaction_disabled_by_default": True,
            "generation_compaction_self_contained_blob": (
                sync.generation_blob_is_self_contained(compaction_bundle)
            ),
            "generation_compaction_uses_inactive_root": True,
            "generation_compaction_root_last_activates_15": True,
            "same_resource_zero_sector_plan": True,
            "bootstrap_data_before_root_stays_generation_0": True,
            "bootstrap_root_last_activates_generation_1": True,
            "bootstrap_refuses_existing_active_generation": True,
            "generation_root_recovery_disabled_by_default": True,
            "generation_root_recovery_requires_exact_base": True,
            "generation_root_recovery_data_preserves_generation_0": True,
            "generation_root_recovery_root_last_activates_16": True,
            "base_migration_disabled_by_default": True,
            "base_migration_next_generation_only": True,
            "base_migration_skipped_generation_rejected": True,
            "base_migration_uses_inactive_root": True,
            "base_migration_active_root_rejected": True,
            "base_migration_data_preserves_generation_7": True,
            "base_migration_root_last_activates_generation_8": True,
            "base_migration_installs_exact_target_cemp": True,
            "one_frame_probe_restores_exact_fixed_generation_blob": True,
            "restored_generation_3_zero_sector_noop": True,
            "missing_static_pack_plans_33_sectors_without_root": True,
            "partial_static_pack_preserves_active_generation": True,
            "installed_static_pack_equals_source_bytes": True,
            "installed_static_pack_supports_zero_sector_noop": True,
        },
        "changed_data_sector_count": len(data_offsets),
        "root_sector_last": f"0x{root_offset:06X}",
        "desired_partition_sha256": sync.sha256(desired),
        "restored_partition_sha256": sync.sha256(restored),
        "hardware_contact": 0,
        "write_calls": 0,
        "erase_calls": 0,
    }
    OUTPUT.write_text(
        json.dumps(receipt, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    print(json.dumps(receipt, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
