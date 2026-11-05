#!/usr/bin/env python3
"""Verify the callback-only WBA pet-behavior user-data adapter scaffold."""

from __future__ import annotations

import argparse
import json
import pathlib
import shutil
import subprocess
import sys
import tempfile
from typing import Any


REPO_ROOT = pathlib.Path(__file__).resolve().parents[1]
EPAPER_ROOT = REPO_ROOT / "app" / "companion_pendant" / "epaper"
HEADER = EPAPER_ROOT / "pet_behavior_user_data_stm32wba.h"
SOURCE = EPAPER_ROOT / "pet_behavior_user_data_stm32wba.c"
PET_BEHAVIOR = EPAPER_ROOT / "pet_behavior.h"
WBA_RULES = REPO_ROOT / "docs" / "stm32wba_migration_rules.md"
RESOURCE_POLICY = REPO_ROOT / "docs" / "companion_resource_memory_policy.md"
WB55_APP = REPO_ROOT / "cubeide" / "Companion_Nucleo_WB55RG_Bringup" / "Core" / "Src" / "app_ble.c"
WB55_MAKEFILE = REPO_ROOT / "cubeide" / "Companion_Nucleo_WB55RG_Bringup" / "Makefile"
DEFAULT_FIXTURE = pathlib.Path("docs/validation/companion-screen-pet-behavior-user-data-stm32wba.json")
SCHEMA_ID = "companion.pendant.pet_behavior_user_data_stm32wba.v1"


def rel(path: pathlib.Path) -> str:
    return path.resolve().relative_to(REPO_ROOT).as_posix()


def require(condition: bool, message: str, errors: list[str]) -> None:
    if not condition:
        errors.append(message)


def build_fixture() -> dict[str, Any]:
    return {
        "schema_id": SCHEMA_ID,
        "status": "PASS",
        "purpose": (
            "Callback-only STM32WBA pet-behavior user-data scaffold. It preserves "
            "comp_pet_behavior_memory_t outside ui_assets/CEMP, OTA staging, "
            "recording cache, and MCU Flash constants."
        ),
        "sources": {
            "adapter_header": rel(HEADER),
            "adapter_source": rel(SOURCE),
            "portable_pet_behavior": rel(PET_BEHAVIOR),
            "wba_rules": rel(WBA_RULES),
            "resource_policy": rel(RESOURCE_POLICY),
        },
        "contract": {
            "targets": ["WBA55", "WBA65"],
            "payload": "comp_pet_behavior_memory_t",
            "slot_model": "two_or_more_logical_slots_with_sequence",
            "integrity": "CRC32 over magic, record_version, payload_size, sequence, and payload",
            "write_policy": "low_frequency_or_forced_commit",
            "erase_policy": "explicit_factory_or_privacy_erase_callback",
            "normal_ota_policy": "preserve_user_data_across_mcu_app_and_ui_assets_updates",
            "address_model": "target_owned_logical_slots_no_physical_address",
            "hardware_parity_claimed": False,
        },
        "machine_checks": {
            "arm_cortex_m33_syntax_compile": True,
            "arm_cortex_m33_object_compile": True,
            "slot_model_scenarios": [
                "empty_slots_load_false",
                "newest_valid_sequence_wins",
                "corrupt_newer_record_is_ignored",
                "unforced_commit_waits_for_interval",
                "forced_commit_rotates_to_next_slot",
                "privacy_erase_clears_all_slots",
            ],
            "compile_flags": [
                "-std=c11",
                "-mcpu=cortex-m33",
                "-mthumb",
                "-Wall",
                "-Wextra",
                "-Werror",
                "-Wconversion",
                "-c",
            ],
        },
        "required_future_evidence": [
            "Chosen WBA package storage peripheral and user-data partition layout.",
            "Power-fail test proving one valid record survives interrupted slot write.",
            "Privacy/factory erase log proving both behavior slots are cleared.",
            "Normal MCU app OTA and ui_assets OTA logs proving pet memory is preserved.",
            "Wear budget review for the selected external NOR or target user-data store.",
        ],
        "validation_commands": [
            "python .\\tools\\verify_pet_behavior_user_data_stm32wba.py",
            "python .\\tools\\verify_expression_wba_portability.py",
        ],
    }


def crc32_update(crc: int, data: bytes) -> int:
    crc = (~crc) & 0xFFFFFFFF
    for value in data:
        crc ^= value
        for _ in range(8):
            crc = ((crc >> 1) ^ (0xEDB88320 & (0 - (crc & 1)))) & 0xFFFFFFFF
    return (~crc) & 0xFFFFFFFF


def record_crc32(record: dict[str, Any]) -> int:
    crc = 0
    for key, size in (("magic", 4), ("record_version", 2), ("payload_size", 2), ("sequence", 4)):
        crc = crc32_update(crc, int(record[key]).to_bytes(size, "little"))
    crc = crc32_update(crc, bytes(record["payload"]))
    return crc


def make_record(sequence: int, payload: bytes) -> dict[str, Any]:
    record = {
        "magic": 0x43505544,
        "record_version": 1,
        "payload_size": len(payload),
        "sequence": sequence,
        "payload": payload,
    }
    record["crc32"] = record_crc32(record)
    return record


def record_is_valid(record: dict[str, Any] | None, payload_size: int) -> bool:
    return (
        record is not None
        and record.get("magic") == 0x43505544
        and record.get("record_version") == 1
        and record.get("payload_size") == payload_size
        and record.get("crc32") == record_crc32(record)
    )


def latest_valid_slot(slots: list[dict[str, Any] | None], payload_size: int) -> tuple[int | None, dict[str, Any] | None]:
    best_slot: int | None = None
    best: dict[str, Any] | None = None
    for index, record in enumerate(slots):
        if not record_is_valid(record, payload_size):
            continue
        if best is None or int(record["sequence"]) > int(best["sequence"]):
            best_slot = index
            best = record
    return best_slot, best


def check_slot_model(errors: list[str]) -> None:
    payload_size = 16
    payload_a = bytes(range(payload_size))
    payload_b = bytes(range(1, payload_size + 1))
    payload_c = bytes(range(2, payload_size + 2))

    empty_slots: list[dict[str, Any] | None] = [None, None]
    slot, record = latest_valid_slot(empty_slots, payload_size)
    require(slot is None and record is None, "slot model empty_slots_load_false failed", errors)

    valid_old = make_record(1, payload_a)
    valid_new = make_record(2, payload_b)
    slot, record = latest_valid_slot([valid_old, valid_new], payload_size)
    require(slot == 1 and record == valid_new, "slot model newest_valid_sequence_wins failed", errors)

    corrupt_new = make_record(3, payload_c)
    corrupt_new["crc32"] ^= 0x01020304
    slot, record = latest_valid_slot([valid_old, corrupt_new], payload_size)
    require(slot == 0 and record == valid_old, "slot model corrupt_newer_record_is_ignored failed", errors)

    min_commit_ms = 60000
    last_commit_ms = 1000
    now_ms = 1000 + min_commit_ms - 1
    should_commit = (now_ms - last_commit_ms) >= min_commit_ms
    require(not should_commit, "slot model unforced_commit_waits_for_interval failed", errors)

    active_slot = 0
    logical_slot_count = 2
    next_slot = (active_slot + 1) % logical_slot_count
    forced_sequence = int(valid_old["sequence"]) + 1
    forced_record = make_record(forced_sequence, payload_b)
    slots = [valid_old, None]
    slots[next_slot] = forced_record
    slot, record = latest_valid_slot(slots, payload_size)
    require(
        next_slot == 1 and slot == 1 and record == forced_record,
        "slot model forced_commit_rotates_to_next_slot failed",
        errors,
    )

    slots = [valid_old, forced_record]
    slots = [None for _ in slots]
    slot, record = latest_valid_slot(slots, payload_size)
    require(slot is None and record is None, "slot model privacy_erase_clears_all_slots failed", errors)


def check_arm_object_compile(errors: list[str]) -> None:
    compiler = shutil.which("arm-none-eabi-gcc")
    if compiler is None:
        errors.append("missing arm-none-eabi-gcc for WBA user-data object compile")
        return
    with tempfile.TemporaryDirectory(prefix="companion_wba_user_data_") as tmp:
        object_path = pathlib.Path(tmp) / "pet_behavior_user_data_stm32wba.o"
        command = [
            compiler,
            "-std=c11",
            "-mcpu=cortex-m33",
            "-mthumb",
            "-Wall",
            "-Wextra",
            "-Werror",
            "-Wconversion",
            f"-I{EPAPER_ROOT}",
            "-c",
            str(SOURCE),
            "-o",
            str(object_path),
        ]
        completed = subprocess.run(
            command,
            cwd=REPO_ROOT,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            check=False,
        )
        if completed.returncode != 0:
            errors.append(
                "arm-none-eabi-gcc object compile failed: "
                + (completed.stderr.strip() or completed.stdout.strip() or f"exit {completed.returncode}")
            )
            return
        require(object_path.exists() and object_path.stat().st_size > 0,
                "arm-none-eabi-gcc object compile produced no object file",
                errors)


def check_code(errors: list[str]) -> None:
    for path in (HEADER, SOURCE, PET_BEHAVIOR, WBA_RULES, RESOURCE_POLICY):
        require(path.exists(), f"missing required path {rel(path)}", errors)
    if errors:
        return

    header = HEADER.read_text(encoding="utf-8")
    source = SOURCE.read_text(encoding="utf-8")
    combined = header + "\n" + source

    for token in (
        '#include "panel_target_stm32wba.h"',
        '#include "pet_behavior.h"',
        "COMP_PET_BEHAVIOR_USER_DATA_STM32WBA_MIN_SLOTS 2u",
        "comp_pet_behavior_user_data_stm32wba_read_fn_t",
        "comp_pet_behavior_user_data_stm32wba_write_fn_t",
        "comp_pet_behavior_user_data_stm32wba_erase_fn_t",
        "logical_slot_count",
        "min_commit_interval_ms",
        "comp_pet_behavior_user_data_stm32wba_load_latest",
        "comp_pet_behavior_user_data_stm32wba_should_commit",
        "comp_pet_behavior_user_data_stm32wba_save",
        "comp_pet_behavior_user_data_stm32wba_privacy_erase",
    ):
        require(token in header, f"user-data header missing {token}", errors)

    for token in (
        "COMP_PET_BEHAVIOR_USER_DATA_MAGIC",
        "COMP_PET_BEHAVIOR_USER_DATA_RECORD_VERSION",
        "COMP_PET_BEHAVIOR_USER_DATA_DEFAULT_COMMIT_MS",
        "crc32_update",
        "0xEDB88320u",
        "record_crc32",
        "record_is_valid",
        "record->crc32 == record_crc32(record)",
        "record.sequence > best.sequence",
        "adapter->config.min_commit_interval_ms",
        "adapter->has_active_record ? adapter->active_sequence + 1u : 1u",
        "adapter->active_slot + 1u",
        "adapter->config.privacy_erase",
        "COMPANION_EPAPER_PANEL_STM32WBA_TARGET_WBA55",
        "COMPANION_EPAPER_PANEL_STM32WBA_TARGET_WBA65",
    ):
        require(token in source, f"user-data source missing {token}", errors)

    for token in (
        "HAL_",
        "GPIO",
        "QSPI",
        "OSPI",
        "I2C",
        "SPI",
        "STM32_WPAN",
        "UTIL_SEQ",
        "0x00200000",
        "0x080",
        "0x900",
        "PC0",
        "PB11",
    ):
        require(token not in combined, f"user-data adapter leaked target fact {token}", errors)

    portable = PET_BEHAVIOR.read_text(encoding="utf-8")
    for token in ("HAL_", "GPIO", "QSPI", "OSPI", "I2C", "SPI", "STM32_WPAN", "0x00200000"):
        require(token not in portable, f"portable pet_behavior leaked storage target fact {token}", errors)

    wb55 = WB55_APP.read_text(encoding="utf-8") + "\n" + WB55_MAKEFILE.read_text(encoding="utf-8")
    require("pet_behavior_user_data_stm32wba" not in wb55,
            "WB55 build must not include WBA pet-behavior user-data adapter", errors)

    rules = WBA_RULES.read_text(encoding="utf-8")
    policy = RESOURCE_POLICY.read_text(encoding="utf-8")
    for token in (
        "comp_pet_behavior_memory_t",
        "target-owned",
        "CRC",
        "privacy",
        "OTA",
    ):
        require(token in rules, f"WBA rules missing user-data anchor {token}", errors)
        require(token in policy, f"resource policy missing user-data anchor {token}", errors)
    check_arm_object_compile(errors)
    check_slot_model(errors)


def main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--fixture", type=pathlib.Path, default=DEFAULT_FIXTURE)
    parser.add_argument("--write-fixture", action="store_true")
    args = parser.parse_args(argv)
    fixture = args.fixture if args.fixture.is_absolute() else REPO_ROOT / args.fixture

    expected = build_fixture()
    errors: list[str] = []
    check_code(errors)
    rendered = json.dumps(expected, indent=2, sort_keys=True) + "\n"
    if args.write_fixture and not errors:
        fixture.parent.mkdir(parents=True, exist_ok=True)
        fixture.write_text(rendered, encoding="utf-8")
    elif not args.write_fixture:
        require(fixture.exists(), f"missing fixture {rel(fixture)}", errors)
        if fixture.exists():
            require(fixture.read_text(encoding="utf-8") == rendered,
                    f"{rel(fixture)} is stale; rerun with --write-fixture",
                    errors)
    if errors:
        print("FAIL: STM32WBA pet-behavior user-data adapter checks failed:", file=sys.stderr)
        for error in errors:
            print(f" - {error}", file=sys.stderr)
        return 1
    print(f"PASS: STM32WBA pet-behavior user-data adapter verified -> {rel(fixture)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
