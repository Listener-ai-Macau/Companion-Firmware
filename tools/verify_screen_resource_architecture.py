#!/usr/bin/env python3
"""Verify the portable screen resource and external-flash product contract."""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
CONTRACT = ROOT / "docs/validation/companion-screen-resource-memory-policy.json"
POLICY = ROOT / "docs/companion_resource_memory_policy.md"
PLAN = ROOT / "docs/companion_screen_project_plan.md"
WBA_RULES = ROOT / "docs/stm32wba_migration_rules.md"
BOOT_LAYOUT = ROOT / "docs/bootloader_flash_layout.md"
EPAPER = ROOT / "app/companion_pendant/epaper"
STORE_H = EPAPER / "asset_store.h"
STORE_C = EPAPER / "asset_store.c"
PACK_H = EPAPER / "emote_asset_pack.h"
PACK_C = EPAPER / "emote_asset_pack.c"
PLAYER_H = EPAPER / "emote_player.h"
STATIC_ASSETS = EPAPER / "expression_assets_200x200.c"
SOURCE_H = EPAPER / "expression_asset_source.h"
SOURCE_C = EPAPER / "expression_asset_source.c"
PACK_BUILDER = ROOT / "tools/build_emote_asset_pack.py"
PACK_DEDUP_VERIFIER = ROOT / "tools/verify_emote_asset_pack_dedup.py"
PACK_MANIFEST = EPAPER / "assets/emote_matrix_white_200x200.json"
MAKEFILE = ROOT / "cubeide/Companion_Nucleo_WB55RG_Bringup/Makefile"
WB_STORE_H = ROOT / "cubeide/Companion_Nucleo_WB55RG_Bringup/Core/Inc/companion_screen_assets_stm32wb.h"
WB_STORE_C = ROOT / "cubeide/Companion_Nucleo_WB55RG_Bringup/Core/Src/companion_screen_assets_stm32wb.c"
MAIN_C = ROOT / "cubeide/Companion_Nucleo_WB55RG_Bringup/Core/Src/main.c"
APP_BLE_C = ROOT / "cubeide/Companion_Nucleo_WB55RG_Bringup/Core/Src/app_ble.c"
PANEL_C = EPAPER / "panel_target_stm32wb_ssd1681.c"
PET_EXPRESSION_H = EPAPER / "pet_expression.h"
PET_EXPRESSION_C = EPAPER / "pet_expression.c"
PET_BEHAVIOR_H = EPAPER / "pet_behavior.h"
PET_BEHAVIOR_C = EPAPER / "pet_behavior.c"


def read(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def require(condition: bool, message: str, errors: list[str]) -> None:
    if not condition:
        errors.append(message)


def main() -> int:
    errors: list[str] = []
    required = [
        CONTRACT,
        POLICY,
        PLAN,
        WBA_RULES,
        BOOT_LAYOUT,
        STORE_H,
        STORE_C,
        PACK_H,
        PACK_C,
        PLAYER_H,
        STATIC_ASSETS,
        SOURCE_H,
        SOURCE_C,
        PACK_BUILDER,
        PACK_DEDUP_VERIFIER,
        PACK_MANIFEST,
        MAKEFILE,
        WB_STORE_H,
        WB_STORE_C,
        MAIN_C,
        APP_BLE_C,
        PANEL_C,
        PET_EXPRESSION_H,
        PET_EXPRESSION_C,
        PET_BEHAVIOR_H,
        PET_BEHAVIOR_C,
    ]
    for path in required:
        require(path.is_file(), f"missing required file: {path.relative_to(ROOT)}", errors)
    if errors:
        for error in errors:
            print(f"ERROR: {error}")
        return 1

    contract = json.loads(read(CONTRACT))
    policy = read(POLICY)
    plan = read(PLAN)
    wba_rules = read(WBA_RULES)
    boot_layout = read(BOOT_LAYOUT)
    store = read(STORE_H) + "\n" + read(STORE_C)
    pack = read(PACK_H) + "\n" + read(PACK_C)
    player = read(PLAYER_H)
    source = read(SOURCE_H) + "\n" + read(SOURCE_C)
    builder = read(PACK_BUILDER)
    manifest = json.loads(read(PACK_MANIFEST))
    makefile = read(MAKEFILE)
    static_assets = read(STATIC_ASSETS)
    wb_store = read(WB_STORE_H) + "\n" + read(WB_STORE_C)
    main_c = read(MAIN_C)
    app_ble = read(APP_BLE_C)
    panel = read(PANEL_C)
    pet_expression = read(PET_EXPRESSION_H) + "\n" + read(PET_EXPRESSION_C)
    pet_behavior = read(PET_BEHAVIOR_H) + "\n" + read(PET_BEHAVIOR_C)

    require(
        contract.get("schema_id") == "companion.screen.resource_memory_policy.v1",
        "unexpected resource memory policy schema",
        errors,
    )
    require(contract.get("status") == "PASS", "resource memory contract must be PASS", errors)
    require(
        contract.get("principle") == "external_flash_first_internal_flash_rescue_only",
        "external-flash-first principle drifted",
        errors,
    )

    budgets = contract.get("budgets", {})
    rescue_limit = budgets.get("production_internal_rescue_ui_max_bytes")
    linked_static_bytes = budgets.get("normal_build_linked_static_expression_bytes")
    retired_static_bytes = budgets.get("retired_devboard_static_expression_baseline_bytes")
    require(rescue_limit == 16 * 1024, "production rescue UI limit must remain 16 KiB", errors)
    require(linked_static_bytes == 0, "normal build must link zero full static expression bytes", errors)
    require(retired_static_bytes == 50000, "retired static baseline must remain recorded", errors)

    forbidden_portable_tokens = (
        "stm32wbxx_hal",
        "stm32wb",
        "stm32wba",
        "HAL_",
        "GPIO_",
        "QSPI_",
        "OSPI_",
        "OCTOSPI_",
        "comp_qspi_nor",
    )
    for token in forbidden_portable_tokens:
        require(token not in store, f"portable asset store contains target token: {token}", errors)
        require(token not in pack, f"portable asset pack contains target token: {token}", errors)
        require(token not in source, f"portable expression source contains target token: {token}", errors)
        require(token not in pet_expression, f"portable pet expression contains target token: {token}", errors)
        require(token not in pet_behavior, f"portable pet behavior contains target token: {token}", errors)
    for token in ("malloc(", "calloc(", "realloc(", "free("):
        require(token not in store, f"asset store must not allocate dynamically: {token}", errors)
        require(token not in pack, f"asset pack must not allocate dynamically: {token}", errors)
        require(token not in source, f"expression source must not allocate dynamically: {token}", errors)
        require(token not in pet_expression, f"pet expression must not allocate dynamically: {token}", errors)
        require(token not in pet_behavior, f"pet behavior must not allocate dynamically: {token}", errors)

    for field in ("dirty_x", "dirty_y", "dirty_width", "dirty_height"):
        require(
            re.search(rf"uint16_t\s+{field}\s*;", player) is not None,
            f"emote player {field} must remain 16-bit",
            errors,
        )
    for field in ("width", "height", "stride_bytes", "pixel_format"):
        require(field in pack, f"asset pack screen profile missing {field}", errors)
    for token in (
        "COMP_EMOTE_ASSET_PACK_FORMAT_VERSION",
        "COMP_EMOTE_ASSET_PACK_HEADER_BYTES",
        "payload_crc32",
        "has_payload_crc32",
        "comp_emote_asset_pack_select",
        "comp_emote_asset_pack_mount",
        "comp_emote_asset_pack_verify_payload",
        "COMP_ASSET_STORAGE_EXTERNAL_NOR",
    ):
        require(token in (pack + store), f"resource architecture missing token: {token}", errors)

    for source_name in ("asset_store.c", "emote_asset_pack.c", "emote_player.c", "expression_asset_source.c"):
        require(
            f"$(ROOT)/app/companion_pendant/epaper/{source_name}" in makefile,
            f"WB55 Makefile does not compile {source_name}",
            errors,
        )
    require(
        "$(ROOT)/app/companion_pendant/epaper/pet_expression.c" in makefile,
        "WB55 Makefile does not compile the parameterized pet-expression composer",
        errors,
    )
    require(
        "$(ROOT)/app/companion_pendant/epaper/pet_behavior.c" in makefile,
        "WB55 Makefile does not compile the portable pet behavior model",
        errors,
    )
    require(
        "$(ROOT)/app/companion_pendant/epaper/expression_assets_200x200.c" not in makefile,
        "normal WB55 build must not relink the retired 50KB static expression source",
        errors,
    )
    require(
        "Core/Src/companion_screen_assets_stm32wb.c" in makefile,
        "WB55 Makefile does not compile target asset-store adapter",
        errors,
    )
    for token in ("comp_qspi_nor_read", "COMP_ASSET_STORAGE_EXTERNAL_NOR"):
        require(token in wb_store, f"WB55 target asset adapter missing {token}", errors)
    for token in (
        "FLASH_UI_ASSETS_BASE 0x00200000u",
        "FLASH_UI_ASSETS_SIZE 0x00200000u",
        "Companion_ScreenAssets_OpenExternalStore",
        "COMPANION_SCREEN_ASSET_PROVISION",
        "screen_asset_provision",
    ):
        require(token in main_c, f"WB55 ui_assets boundary missing {token}", errors)

    for token in (
        "MAGIC = b\"CEMP\"",
        "HEADER_BYTES = 80",
        "packbits",
        "decode_packbits",
        "payload_offsets",
        "deduplicated_frame_count",
        "zlib.crc32(payload_bytes)",
        "format_c_header",
    ):
        require(token in builder, f"CEMP pack builder missing {token}", errors)
    require(
        "independently seekable" in read(PACK_DEDUP_VERIFIER),
        "CEMP shared-payload verifier lost its random-access contract",
        errors,
    )
    clip_names = {
        clip.get("name") for clip in manifest.get("clips", []) if isinstance(clip, dict)
    }
    required_expression_clips = {
        "idle", "listening", "thinking", "speaking", "happy", "sleepy",
        "recording", "sync_complete", "low_battery", "error",
    }
    required_menu_clips = {
        f"menu.{view}.{language}"
        for view in (
            "home", "record", "status", "phone", "device",
            "preferences", "about",
        )
        for language in ("en", "zh")
    }
    require(
        manifest.get("schema") == "companion.emote_asset_pack_manifest.v1" and
        manifest.get("profile", {}).get("width") == 200 and
        manifest.get("encoding") == "packbits" and
        required_expression_clips <= clip_names and
        required_menu_clips <= clip_names,
        "external UI manifest lost required expression or bilingual menu clips",
        errors,
    )
    for token in (
        "COMP_EMOTE_FRAME_ENCODING_PACKBITS",
        "packbits_decode_frame",
        "packbits_reader_read",
    ):
        require(token in pack, f"portable asset pack missing PackBits decoder token: {token}", errors)
    for token in (
        '"external_pack"',
        "comp_epaper_expression_asset_source_init",
        "comp_epaper_display_queue_enqueue_expression_frame",
        "player_frame.frame_index",
        "source=external_flash",
        "comp_pet_behavior_apply_expression",
    ):
        require(token in app_ble, f"WB55 external expression integration missing {token}", errors)
    for token in (
        "comp_pet_expression_render",
        "comp_pet_behavior_compose_expression_pose",
        "screen_framebuffer",
        "COMP_EPAPER_DISPLAY_REQUEST_PET_EXPRESSION",
    ):
        require(token in pet_expression + pet_behavior + panel,
                f"parameterized pet-expression architecture missing {token}", errors)
    for token in (
        "comp_epaper_expression_asset_source_copy_expression",
        "source=external_flash",
    ):
        require(token in panel, f"SSD1681 external frame path missing {token}", errors)

    frame_arrays = re.findall(
        r"static\s+const\s+uint8_t\s+s_expression_[a-z0-9_]+"
        r"\[COMPANION_EPAPER_EXPRESSION_ASSET_BYTES\]",
        static_assets,
    )
    retired = contract.get("retired_transition", {})
    expected_frames = retired.get("frame_count")
    bytes_per_frame = retired.get("bytes_per_frame")
    require(retired.get("status") == "not_linked", "retired static source status drifted", errors)
    require(len(frame_arrays) == expected_frames, "retired static frame archive drifted", errors)
    measured_static_bytes = len(frame_arrays) * int(bytes_per_frame or 0)
    require(
        measured_static_bytes == retired_static_bytes,
        f"retired static baseline drifted to {measured_static_bytes} bytes",
        errors,
    )

    policy_tokens = (
        "外部串行 NOR Flash",
        "16 KiB",
        "50000",
        "ui_assets",
        "asset_store",
        "emote_asset_pack",
        "intro / loop / tail",
        "WBA55/WBA65",
        "参数化表情合成器",
    )
    for token in policy_tokens:
        require(token in policy, f"resource policy missing anchor: {token}", errors)
    for token in ("SCR-12", "SCR-13", "正常资源默认位于外部 Flash"):
        require(token in plan, f"screen project plan missing resource anchor: {token}", errors)
    for token in ("comp_asset_store_t", "<=16 KiB rescue UI", "WBA65 internal flash", "pet_expression", "pet_behavior"):
        require(token in wba_rules, f"WBA migration rules missing resource anchor: {token}", errors)
    for token in ("`ui_assets`", "wrong-profile", "rescue UI"):
        require(token in boot_layout, f"boot/flash layout missing resource anchor: {token}", errors)

    placement = contract.get("placement", {})
    require(
        placement.get("logical_ui_partition") == "ui_assets",
        "logical UI partition must remain ui_assets",
        errors,
    )
    wb_partition = contract.get("wb55_devboard_partition", {})
    require(wb_partition.get("base") == "0x00200000", "WB55 ui_assets base drifted", errors)
    require(wb_partition.get("size_bytes") == 2 * 1024 * 1024, "WB55 ui_assets size drifted", errors)
    wb55_evidence = contract.get("wb55_real_evidence", {})
    menu_evidence_path = ROOT / "docs/validation/companion-screen-bilingual-menu-wb55.json"
    menu_evidence = json.loads(menu_evidence_path.read_text(encoding="utf-8"))
    menu_pack = menu_evidence.get("resource_pack", {})
    runtime_status = str(menu_evidence.get("runtime_evidence", {}).get("status", ""))
    candidate_pack = contract.get("candidate_pack", {})
    if runtime_status.endswith("_RUNTIME_RECHECK_PENDING"):
        require(candidate_pack.get("revision") == menu_pack.get("revision"),
                "candidate pack revision drifted from menu evidence", errors)
        require(candidate_pack.get("clips") == menu_pack.get("clips"),
                "candidate pack clip count drifted from menu evidence", errors)
        require(candidate_pack.get("frames") == menu_pack.get("frames"),
                "candidate pack frame count drifted from menu evidence", errors)
        require(candidate_pack.get("pack_bytes") == menu_pack.get("total_bytes"),
                "candidate pack size drifted from menu evidence", errors)
        require(candidate_pack.get("pack_crc32") == menu_pack.get("pack_crc32"),
                "candidate pack CRC drifted from menu evidence", errors)
        require(candidate_pack.get("status") == "runtime_recheck_pending",
                "candidate pack must explicitly be runtime_recheck_pending", errors)
    else:
        require(wb55_evidence.get("revision") == menu_pack.get("revision"),
                "WB55 real evidence revision drifted from menu evidence", errors)
        require(wb55_evidence.get("pack_bytes") == menu_pack.get("total_bytes"),
                "WB55 real evidence pack size drifted from menu evidence", errors)
        require(wb55_evidence.get("pack_crc32") == menu_pack.get("pack_crc32"),
                "WB55 real evidence CRC drifted from menu evidence", errors)
    require(wb55_evidence.get("clips") == 33, "WB55 real evidence clip count drifted", errors)
    require(wb55_evidence.get("frames") == menu_pack.get("frames"),
            "WB55 real evidence frame count drifted from current menu evidence", errors)
    for key in ("provision_runtime_log", "normal_runtime_log", "external_render_log"):
        value = wb55_evidence.get(key)
        require(isinstance(value, str) and (ROOT / value).is_file(), f"WB55 real evidence missing {key}", errors)
    if isinstance(wb55_evidence.get("normal_runtime_log"), str):
        normal_log = read(ROOT / str(wb55_evidence["normal_runtime_log"]))
        for marker in wb55_evidence.get("required_markers", []):
            require(isinstance(marker, str) and marker in normal_log,
                    f"WB55 normal runtime log missing marker: {marker}", errors)
    portable_contract = contract.get("portable_contract", {})
    require(portable_contract.get("binary_pack_magic") == "CEMP", "binary pack magic drifted", errors)
    require(portable_contract.get("binary_pack_header_bytes") == 80, "binary pack header size drifted", errors)
    require(portable_contract.get("binary_pack_byte_order") == "little_endian", "binary pack byte order drifted", errors)
    require(
        "ui_assets" in placement.get("external_flash", []),
        "normal UI assets must remain external",
        errors,
    )
    require(
        "rescue_ui" in placement.get("internal_flash", []),
        "internal rescue UI role is missing",
        errors,
    )

    if errors:
        for error in errors:
            print(f"ERROR: {error}")
        return 1

    print("screen resource architecture: PASS")
    print(f"  normal linked full-frame static assets: {linked_static_bytes} bytes")
    print(f"  retired devboard static baseline: {measured_static_bytes} bytes (not linked)")
    print(f"  production internal rescue UI ceiling: {rescue_limit} bytes")
    print("  normal expression/font/audio/model assets: external ui_assets storage")
    print("  screen profiles and dirty rectangles: target-independent, 16-bit coordinates")
    return 0


if __name__ == "__main__":
    sys.exit(main())
